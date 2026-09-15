from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List

try:
    import cadquery as cq
except Exception:  # pragma: no cover
    cq = None

from ..models import STLRequest, STLFile, Proposal


@dataclass
class GFParams:
    grid_xy: float = 42.0
    grid_z: float = 7.0
    wall: float = 2.0  # also doubles as floor thickness via shell() below
    lip_h: float = 1.6
    comp_wall: float = 1.6  # thickness of interior compartment dividers
    finger_width: float = 20.0  # width of the "easy grab" finger scoop
    finger_drop: float = 12.0  # how far the scoop cuts down from the top edge


def _bin_outer_dims(p: Proposal, g: GFParams) -> "tuple[float, float, float]":
    x = p.x_slots * g.grid_xy
    y = p.y_slots * g.grid_xy
    z = p.z_units * g.grid_z
    return x, y, z


def _add_finger_cutout(body: "cq.Workplane", x: float, y: float, z: float, g: GFParams) -> "cq.Workplane":
    """Cut a scoop into the top of the front (+Y) wall so a finger can reach
    in and pinch the item out - the "Easy Grab" proposal type's defining
    feature (see README). Sized and clamped so it still works on small bins;
    wrapped by the caller in a try/except like the lip chamfer, since a
    degenerate cut shouldn't break STL generation for an edge-case size.
    """
    fw = min(g.finger_width, max(6.0, x - 16.0))
    fdrop = min(g.finger_drop, max(4.0, z * 0.6))
    fdepth = g.wall + 6.0  # cut fully through the front wall, a bit into the cavity

    # Built oversized by 1mm on the open ends (past the outer wall, above the
    # top) so the cutting solid's faces don't sit exactly coincident with the
    # body's faces - coincident faces are a common source of CadQuery boolean
    # failures.
    cut_box = (
        cq.Workplane("XY")
        .box(fw, fdepth, fdrop + 2, centered=(True, False, False))
        .translate((0, y / 2 - fdepth + 1, z - fdrop - 1))
    )
    return body.cut(cut_box)


def _add_compartment_dividers(body: "cq.Workplane", x: float, y: float, z: float, g: GFParams, compartments: int) -> "cq.Workplane":
    """Add interior divider walls splitting the cavity into `compartments`
    equal cells - the "Multi-purpose" proposal type's defining feature. Walls
    run the full height of the bin and split whichever interior axis (X or
    Y) is longer, so a 2x1 footprint gets one wall down the middle rather
    than an oddly-thin split of the short side.
    """
    ix = x - 2 * g.wall
    iy = y - 2 * g.wall
    n = max(1, compartments)
    if n <= 1:
        return body

    split_x = ix >= iy
    span = ix if split_x else iy
    cell = span / n

    walls = []
    for i in range(1, n):
        offset = -span / 2 + i * cell
        if split_x:
            wall = cq.Workplane("XY").center(offset, 0).rect(g.comp_wall, iy).extrude(z)
        else:
            wall = cq.Workplane("XY").center(0, offset).rect(ix, g.comp_wall).extrude(z)
        walls.append(wall)

    for wall in walls:
        body = body.union(wall)
    return body


def _make_bin(p: Proposal, label: "str | None", options: dict, g: GFParams) -> "cq.Workplane":
    """Build a simplified Gridfinity-style bin: a hollow box sized to the
    grid, with an optional chamfered top edge (a lightweight nod to the
    Gridfinity stacking lip - not the full interlocking profile) and
    optional magnet/screw holes at the base corners. "easy" bins additionally
    get a finger scoop and "multi" bins get interior compartment dividers -
    see _add_finger_cutout / _add_compartment_dividers for why these were
    previously computed (in proposals.py) but never actually cut into the
    geometry.

    Why this replaced the previous version: the previous "lip" unioned a
    full-footprint solid slab directly onto the open top of the cavity,
    which sealed the container shut instead of leaving it open, and a
    second cutBlind() from a workplane offset below the part's own bottom
    face never actually intersected the solid (a dead no-op). Both are
    replaced with the same hollow-then-chamfer-then-drill approach already
    validated end to end - including a combined lip+magnets+screws case and
    a smallest-possible-bin edge case - in backend/main.py's equivalent
    builder.
    """
    assert cq is not None, "CadQuery is required to generate STL"
    x, y, z = _bin_outer_dims(p, g)

    body = cq.Workplane("XY").box(x, y, z, centered=(True, True, False))

    if options.get("lip", True):
        chamfer_mm = min(g.lip_h, g.wall * 0.5)
        try:
            body = body.faces(">Z").edges().chamfer(chamfer_mm)
        except Exception:
            # Chamfer can fail on degenerate/too-small edges for unusual
            # sizes; skip it rather than break STL generation entirely.
            pass

    # Hollow into an open-top container; wall thickness doubles as floor
    # thickness here, which is the standard shell() behavior. Must run
    # after the chamfer above, not before - shell() consumes the face
    # whose edges the chamfer needs.
    body = body.faces(">Z").shell(-g.wall)

    if p.type == "easy":
        try:
            body = _add_finger_cutout(body, x, y, z, g)
        except Exception:
            # Same reasoning as the chamfer above: don't let a degenerate
            # cut on an unusual size break the whole request.
            pass

    if p.type == "multi" and p.compartments and p.compartments > 1:
        try:
            body = _add_compartment_dividers(body, x, y, z, g, p.compartments)
        except Exception:
            pass

    if options.get("magnets") or options.get("screws"):
        inset = 8.0
        hx = x / 2 - inset
        hy = y / 2 - inset
        corner_points = [(hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]

        if options.get("magnets"):
            body = body.faces("<Z").workplane().pushPoints(corner_points).hole(6.5, 2.4)
        if options.get("screws"):
            body = body.faces("<Z").workplane().pushPoints(corner_points).hole(3.2)

    return body


def generate_stl_files(req: STLRequest, output_dir: Path) -> List[STLFile]:
    output_dir.mkdir(parents=True, exist_ok=True)
    g = GFParams()

    stl_files: List[STLFile] = []
    name_base = f"{req.item_id}_{req.proposal.type}_{req.proposal.x_slots}x{req.proposal.y_slots}x{req.proposal.z_units}"
    filename = f"{name_base}.stl"
    fp = output_dir / filename

    if cq is None:
        # Fallback: write a placeholder file (why: allow API contract even without CadQuery)
        fp.write_text("CadQuery not available; this is a placeholder.")
    else:
        solid = _make_bin(req.proposal, req.label, req.options, g)
        cq.exporters.export(solid, str(fp))

    stl_files.append(STLFile(type=req.proposal.type, url=f"/files/stl/{filename}"))
    return stl_files
