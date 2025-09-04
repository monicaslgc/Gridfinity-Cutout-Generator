from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List

try:
    import cadquery as cq
except Exception as e:  # pragma: no cover
    cq = None

from ..models import STLRequest, STLFile, Proposal


@dataclass
class GFParams:
    grid_xy: float = 42.0
    grid_z: float = 7.0
    wall: float = 2.0
    base: float = 3.0
    lip_h: float = 1.6


def _bin_outer_dims(p: Proposal, g: GFParams) -> tuple[float, float, float]:
    x = p.x_slots * g.grid_xy
    y = p.y_slots * g.grid_xy
    z = p.z_units * g.grid_z
    return x, y, z


def _make_bin(p: Proposal, label: str | None, options: dict, g: GFParams) -> "cq.Workplane":
    assert cq is not None, "CadQuery is required to generate STL"
    x, y, z = _bin_outer_dims(p, g)

    wp = cq.Workplane("XY")
    body = (
        wp.box(x, y, z)  # outer block
        .faces(">Z").workplane().rect(x - 2 * g.wall, y - 2 * g.wall).cutBlind(-(z - g.base))
    )

    # lip
    if options.get("lip", True):
        lip = (
            cq.Workplane("XY")
            .box(x, y, g.lip_h)
            .translate((0, 0, z / 2 + g.lip_h / 2))
        )
        body = body.union(lip)

    # basic cutout based on item dims
    # NOTE(why): clearance handled by proposal; use a centered pocket in the floor
    cut_L = max(1.0, p.clearance + options.get("extra_clearance", 0))
    body = (
        body.faces("<Z").workplane(offset=g.base + 0.2)
        .rect(x - 2 * g.wall - 2.0, y - 2 * g.wall - 2.0)
        .cutBlind(- (z - g.base - 0.4))
    )

    # TODO: magnets/screws (stub for now)
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
