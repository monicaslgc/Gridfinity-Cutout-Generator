import math
import os
import uuid
import time
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import cadquery as cq

app = FastAPI(title="Gridfinity Cutout Generator API")

# The Next.js dev server (localhost:3000) calls this API directly from the
# browser, which needs CORS enabled or every request gets blocked silently.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

GRID_UNIT_XY = 42.0   # mm, standard Gridfinity baseplate unit
GRID_UNIT_Z = 7.0     # mm, standard Gridfinity height unit
WALL_THICKNESS = 2.0  # mm, also doubles as the floor thickness (see shell() below)


def cleanup_temp_files():
    """Delete files older than 5 minutes in TEMP_DIR."""
    now = time.time()
    for filename in os.listdir(TEMP_DIR):
        path = os.path.join(TEMP_DIR, filename)
        if os.path.isfile(path) and now - os.path.getmtime(path) > 300:
            os.remove(path)


# ---------------------------------------------------------------------------
# Mock item catalog
#
# /identify and /dimensions don't call a real LLM or a real web lookup yet
# (see the README's Development Roadmap). This small local catalog stands in
# for both, so the rest of the pipeline (/proposals, /stl) has real data to
# work with end to end without needing any external API or key. Swap this
# out for a real LLM call + dimension lookup later without touching the
# endpoints' request/response shape.
# ---------------------------------------------------------------------------
MOCK_CATALOG = {
    "nintendo-switch-pro-controller": {
        "name": "Nintendo Switch Pro Controller",
        "keywords": ["nintendo", "switch", "pro", "controller", "gamepad"],
        "dims_mm": {"L": 152, "W": 106, "H": 60},
        "source": "mock catalog (approximate manufacturer spec)",
    },
    "dji-mini-drone": {
        "name": "DJI Mini Drone",
        "keywords": ["dji", "mini", "drone", "quadcopter"],
        "dims_mm": {"L": 138, "W": 81, "H": 58},
        "source": "mock catalog (approximate manufacturer spec)",
    },
    "airpods-pro-case": {
        "name": "AirPods Pro Case",
        "keywords": ["airpods", "pro", "earbuds", "earbud", "case"],
        "dims_mm": {"L": 61, "W": 46, "H": 22},
        "source": "mock catalog (approximate manufacturer spec)",
    },
    "steel-tape-measure-8m": {
        "name": "Steel Tape Measure (8m)",
        "keywords": ["tape", "measure"],
        "dims_mm": {"L": 78, "W": 78, "H": 45},
        "source": "mock catalog (approximate manufacturer spec)",
    },
    "usb-c-hub": {
        "name": "USB-C Hub",
        "keywords": ["usb-c", "usb", "c", "hub", "dock", "adapter"],
        "dims_mm": {"L": 100, "W": 40, "H": 15},
        "source": "mock catalog (approximate manufacturer spec)",
    },
}

DEFAULT_ITEM_ID = "generic-small-item"
DEFAULT_DIMS = {"L": 100, "W": 70, "H": 40}


class IdentifyRequest(BaseModel):
    input: str


class Dimensions(BaseModel):
    L: float
    W: float
    H: float


class ProposalOptions(BaseModel):
    lip: bool = True
    magnets: bool = False
    screws: bool = False


class ProposalsRequest(BaseModel):
    item_id: Optional[str] = None
    dims_mm: Dimensions
    options: ProposalOptions = ProposalOptions()


class Proposal(BaseModel):
    type: str
    x_slots: int
    y_slots: int
    z_units: int
    clearance: float
    compartments: Optional[int] = None


class STLRequest(BaseModel):
    item_id: Optional[str] = None
    dims_mm: Dimensions
    proposal: Proposal
    options: ProposalOptions = ProposalOptions()
    label: Optional[str] = None


def score_candidate(query_words: set, entry: dict) -> float:
    keywords = set(entry["keywords"])
    if not keywords:
        return 0.0
    overlap = len(query_words & keywords)
    return overlap / len(keywords)


@app.post("/identify")
def identify_item(req: IdentifyRequest):
    """
    Match free-text input against a small local catalog.

    Stands in for the real LLM-based identification described in the README
    until that's built (see Development Roadmap) - this is deliberately
    simple keyword overlap, not an actual model call.
    """
    query = req.input.lower().strip()
    query_words = set(query.replace("-", " ").split())

    scored = []
    for item_id, entry in MOCK_CATALOG.items():
        score = score_candidate(query_words, entry)
        if score > 0:
            scored.append((score, item_id, entry))

    scored.sort(key=lambda t: t[0], reverse=True)

    if scored:
        candidates = [
            {
                "id": item_id,
                "name": entry["name"],
                "confidence": round(min(0.95, 0.5 + score * 0.5), 2),
            }
            for score, item_id, entry in scored[:3]
        ]
    else:
        # Nothing matched - fall back to a generic placeholder so the rest
        # of the flow (dimensions -> proposals -> STL) still works end to
        # end instead of dead-ending on an empty candidate list.
        candidates = [
            {
                "id": DEFAULT_ITEM_ID,
                "name": req.input.strip() or "Unknown item",
                "confidence": 0.2,
            }
        ]

    return {"item": req.input, "candidates": candidates}


@app.get("/dimensions")
def get_dimensions(id: str = Query(...)):
    entry = MOCK_CATALOG.get(id)
    if entry:
        return {
            "id": id,
            "name": entry["name"],
            "dims_mm": entry["dims_mm"],
            "source": entry["source"],
            "confidence": 0.9,
        }
    # Unknown id (e.g. the generic fallback from /identify, or a "manual"
    # entry typed directly into the frontend): return sane generic
    # dimensions instead of a 404, so the flow can continue.
    return {
        "id": id,
        "name": "Generic item",
        "dims_mm": DEFAULT_DIMS,
        "source": "default estimate (item not in catalog)",
        "confidence": 0.3,
    }


def slots_for(length_mm: float, clearance_mm: float) -> int:
    return max(1, math.ceil((length_mm + 2 * clearance_mm) / GRID_UNIT_XY))


def z_units_for(height_mm: float, top_clearance_mm: float = 6.0) -> int:
    return max(1, math.ceil((height_mm + top_clearance_mm) / GRID_UNIT_Z))


@app.post("/proposals")
def generate_proposals(req: ProposalsRequest):
    """
    Real Gridfinity slot math (not mocked): given a real-world footprint,
    compute three container proposals sized to the 42mm / 7mm Gridfinity grid.
    """
    L, W, H = req.dims_mm.L, req.dims_mm.W, req.dims_mm.H

    snug_clearance = 0.5
    easy_clearance = 2.5
    multi_clearance = 1.5

    proposals = [
        Proposal(
            type="snug",
            x_slots=slots_for(L, snug_clearance),
            y_slots=slots_for(W, snug_clearance),
            z_units=z_units_for(H),
            clearance=snug_clearance,
        ),
        Proposal(
            type="easy",
            x_slots=slots_for(L, easy_clearance),
            y_slots=slots_for(W, easy_clearance),
            z_units=z_units_for(H),
            clearance=easy_clearance,
        ),
        Proposal(
            type="multi",
            x_slots=slots_for(L, multi_clearance) + 1,  # extra room for a divider
            y_slots=slots_for(W, multi_clearance),
            z_units=z_units_for(H),
            clearance=multi_clearance,
            compartments=2,
        ),
    ]

    return {"proposals": [p.model_dump() for p in proposals]}


def build_gridfinity_bin(x_slots: int, y_slots: int, z_units: int, lip: bool, magnets: bool, screws: bool):
    """
    Build a simplified Gridfinity-style bin: a hollow box sized to the grid,
    with an optional chamfered top edge (a lightweight nod to the Gridfinity
    stacking lip - not the full interlocking lip profile) and optional
    magnet/screw holes at the base corners.

    This is close enough for a portfolio demo but is NOT a byte-for-byte
    match to the official Gridfinity spec. Swap in a proper parametric
    Gridfinity library (or the full lip profile) if these need to actually
    interlock with real Gridfinity baseplates/bins.
    """
    outer_w = x_slots * GRID_UNIT_XY - 0.5
    outer_d = y_slots * GRID_UNIT_XY - 0.5
    outer_h = z_units * GRID_UNIT_Z

    body = cq.Workplane("XY").box(outer_w, outer_d, outer_h, centered=(True, True, False))

    # Hollow it into an open-top container; wall thickness doubles as floor
    # thickness here, which is the standard shell() behavior.
    body = body.faces(">Z").shell(-WALL_THICKNESS)

    if lip:
        chamfer_mm = min(1.2, WALL_THICKNESS * 0.5)
        try:
            body = body.edges("|Z and >Z").chamfer(chamfer_mm)
        except Exception:
            # Chamfer can fail on degenerate/too-small edges for unusual
            # sizes; skip it rather than break STL generation entirely.
            pass

    if magnets or screws:
        inset = 8.0
        hx = outer_w / 2 - inset
        hy = outer_d / 2 - inset
        corner_points = [(hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]

        if magnets:
            body = (
                body.faces("<Z")
                .workplane()
                .pushPoints(corner_points)
                .hole(6.5, 2.4)
            )
        if screws:
            body = (
                body.faces("<Z")
                .workplane()
                .pushPoints(corner_points)
                .hole(3.2)
            )

    return body


@app.post("/stl")
def generate_stl(req: STLRequest):
    """
    Generate a real STL file for the chosen proposal with CadQuery - this
    part isn't mocked, it's actual parametric geometry sized from real
    /proposals output.
    """
    cleanup_temp_files()

    p = req.proposal
    result = build_gridfinity_bin(
        x_slots=p.x_slots,
        y_slots=p.y_slots,
        z_units=p.z_units,
        lip=req.options.lip,
        magnets=req.options.magnets,
        screws=req.options.screws,
    )

    token = str(uuid.uuid4())
    file_path = os.path.join(TEMP_DIR, f"{token}.stl")
    cq.exporters.export(result, file_path)

    return {
        "files": [
            {
                "type": p.type,
                "url": f"/download/{token}?filetype=stl",
            }
        ]
    }


@app.get("/generate")
def generate_container(width: int = Query(42, gt=0), length: int = Query(42, gt=0), height: int = Query(20, gt=0), filetype: str = Query("stl", pattern="^(stl|step)$")):
    """
    Generate a simple parametric box and return a download URL.
    Kept for backwards compatibility / quick manual testing.
    Parameters: width (mm), length (mm), height (mm), filetype ('stl' or 'step')
    """
    cleanup_temp_files()
    token = str(uuid.uuid4())
    ext = "step" if filetype == "step" else "stl"
    file_path = os.path.join(TEMP_DIR, f"{token}.{ext}")

    result = cq.Workplane("XY").box(width, length, height)
    cq.exporters.export(result, file_path)

    return {"download_url": f"/download/{token}?filetype={ext}"}


@app.get("/download/{token}")
def download_file(token: str, filetype: str = Query("stl", pattern="^(stl|step)$")):
    file_path = os.path.join(TEMP_DIR, f"{token}.{filetype}")
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found or expired."}, status_code=404)
    if time.time() - os.path.getmtime(file_path) > 300:
        os.remove(file_path)
        return JSONResponse({"error": "File expired."}, status_code=410)
    return FileResponse(file_path, filename=f"gridfinity_container_{token}.{filetype}")
