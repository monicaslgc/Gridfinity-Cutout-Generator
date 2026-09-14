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


def _bin_outer_dims(p: Proposal, g: GFParams) -> "tuple[float, float, float]":
    x = p.x_slots * g.grid_xy
    y = p.y_slots * g.grid_xy
    z = p.z_units * g.grid_z
    return x, y, z


def _make_bin(p: Proposal, label: "str | None", options: dict, g: GFParams) -> "cq.Workplane":
    """Build a simplified Gridfinity-style bin: a hollow box sized to the
    grid, with an optional chamfered top edge (a lightweight nod to the
    Gridfinity stacking lip - not the full interlocking profile) and
    optional magnet/screw holes at the base corners.

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
