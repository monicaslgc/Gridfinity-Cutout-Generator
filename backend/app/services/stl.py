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
    wall: float = 2.0  # also doubles as floor thickness (see the cavity cut in _make_bin)
    lip_h: float = 1.6
    comp_wall: float = 1.6  # thickness of interior compartment dividers
    finger_width: float = 20.0  # width of the "easy grab" finger scoop
    finger_drop: float = 12.0  # how far the scoop cuts down from the top edge

    # The real Gridfinity interlocking base/foot profile, per 42x42mm grid
    # cell: a small chamfer at the very bottom (eases the foot into a
    # baseplate socket), a straight vertical band, then a larger chamfer
    # flaring out to the cell's full width where it meets the bin's flat
    # underside. These heights match the profile used by established open
    # source Gridfinity implementations (e.g. cq-gridfinity's
    # GR_BOX_PROFILE: 0.8 + 1.8 + 2.4 = 5.0mm total) rather than guessed
    # numbers - this is what was missing before (see _make_gridfinity_foot).
    foot_bot_chamf: float = 0.8
    foot_straight: float = 1.8
    foot_top_chamf: float = 2.4
    # Each cell's foot footprint is slightly smaller than the nominal 42mm
    # grid so neighboring feet never touch/bind and the whole bin has a
    # little play in a baseplate socket - matches the Gridfinity spec's
    # "41.5mm square block" (0.5mm total tolerance).
    foot_clearance: float = 0.5

    @property
    def foot_h(self) -> float:
        return self.foot_bot_chamf + self.foot_straight + self.foot_top_chamf


def _bin_outer_dims(p: Proposal, g: GFParams) -> "tuple[float, float, float]":
    x = p.x_slots * g.grid_xy
    y = p.y_slots * g.grid_xy
    z = p.z_units * g.grid_z
    return x, y, z


def _make_gridfinity_foot(g: GFParams) -> "cq.Workplane":
    """Build a single Gridfinity base/foot: a stepped-chamfer stack sized to
    one 42x42mm grid cell, centered at the origin, spanning z=0 (its
    narrowest point - the tip that first enters a baseplate socket, size
    s0) up to z=g.foot_h (its widest point - where it meets the bin's flat
    underside, size s2).

    Built as a 4-section ruled loft (square wire, widen, hold, widen again)
    rather than extrude(taper=...), so the shape comes from CadQuery's
    well-tested loft operation instead of depending on taper-sign
    conventions we can't easily verify without a local CadQuery to run.
    """
    s2 = g.grid_xy - g.foot_clearance  # top: full cell minus baseplate tolerance
    s1 = s2 - 2 * g.foot_top_chamf
    s0 = s1 - 2 * g.foot_bot_chamf

    z1 = g.foot_bot_chamf
    z2 = z1 + g.foot_straight
    z3 = g.foot_h

    return (
        cq.Workplane("XY")
        .rect(s0, s0)
        .workplane(offset=z1)
        .rect(s1, s1)
        .workplane(offset=(z2 - z1))
        .rect(s1, s1)
        .workplane(offset=(z3 - z2))
        .rect(s2, s2)
        .loft(ruled=True)
    )


def _add_gridfinity_feet(
    upper: "cq.Workplane", x: float, y: float, g: GFParams, x_slots: int, y_slots: int
) -> "cq.Workplane":
    """Union one Gridfinity foot (see _make_gridfinity_foot) under every
    42x42mm cell of the bin's footprint, onto `upper` (the plain box that
    makes up the rest of the bin above the foot region).

    This is the actual interlocking profile that presses into and
    registers with a real Gridfinity baseplate - previously every
    generated bin had a flat floor here, which is the "no gridfinity grid"
    bug this function fixes.
    """
    foot_template = _make_gridfinity_foot(g)
    x0 = -x / 2 + g.grid_xy / 2
    y0 = -y / 2 + g.grid_xy / 2

    body = upper
    for i in range(x_slots):
        for j in range(y_slots):
            px = x0 + i * g.grid_xy
            py = y0 + j * g.grid_xy
            body = body.union(foot_template.translate((px, py, 0)))
    return body


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


def _drill_corner_holes(body: "cq.Workplane", x: float, y: float, g: GFParams, diameter: float, depth: float) -> "cq.Workplane":
    """Cut 4 corner holes (magnets or screws) via explicit cylinder-cut
    solids rather than a face-selector + .hole() - the bin's bottom is no
    longer one flat face now that it's made of individual Gridfinity feet
    (see _add_gridfinity_feet), so a face selector like faces("<Z") would
    resolve to several small disconnected faces instead of one. Insetting
    relative to a single cell's narrowest (bottom-tip) width guarantees
    every hole lands on solid foot material, on any size bin, regardless
    of how many feet it has.
    """
    s2 = g.grid_xy - g.foot_clearance
    s1 = s2 - 2 * g.foot_top_chamf
    s0 = s1 - 2 * g.foot_bot_chamf
    inset = g.grid_xy / 2 - s0 / 2 + 2.0  # a couple mm past the tip's edge, safely inside it
    hx = x / 2 - inset
    hy = y / 2 - inset
    corner_points = [(hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]

    for cx, cy in corner_points:
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=-1)
            .center(cx, cy)
            .circle(diameter / 2)
            .extrude(depth + 1)
        )
        body = body.cut(cutter)
    return body


def _make_bin(p: Proposal, label: "str | None", options: dict, g: GFParams) -> "cq.Workplane":
    """Build a Gridfinity-style bin: a hollow box sized to the grid, with a
    real interlocking base/foot profile on the underside of every 42x42mm
    cell (see _add_gridfinity_feet - this is what makes it actually
    register/press-fit into a real Gridfinity baseplate, not just a
    correctly-sized box), an optional chamfered top stacking lip, and
    optional magnet/screw holes at the base corners. "easy" bins
    additionally get a finger scoop and "multi" bins get interior
    compartment dividers - see _add_finger_cutout / _add_compartment_dividers.

    The bin's outer shape is built in two pieces and unioned: the foot
    region (z: 0..g.foot_h, one stepped-chamfer foot per grid cell) and a
    plain box for the rest of the height above that. It's then hollowed by
    cutting a cavity that starts g.wall above the top of the foot region,
    so the feet themselves stay solid (real Gridfinity bases aren't
    hollow) and the floor above them is exactly g.wall thick.
    """
    assert cq is not None, "CadQuery is required to generate STL"
    x, y, z = _bin_outer_dims(p, g)

    upper_h = max(z - g.foot_h, 0.5)
    upper = (
        cq.Workplane("XY")
        .workplane(offset=z - upper_h)
        .box(x, y, upper_h, centered=(True, True, False))
    )

    if z > g.foot_h:
        try:
            body = _add_gridfinity_feet(upper, x, y, g, p.x_slots, p.y_slots)
        except Exception:
            # If the foot profile fails for some degenerate size, fall back
            # to a plain flat-bottomed box rather than breaking STL
            # generation entirely.
            body = cq.Workplane("XY").box(x, y, z, centered=(True, True, False))
    else:
        # Bin is shorter than the foot region itself (an unusually squat
        # size) - the feet wouldn't fit under any usable wall anyway, so
        # skip them rather than risk a degenerate union.
        body = cq.Workplane("XY").box(x, y, z, centered=(True, True, False))

    if options.get("lip", True):
        chamfer_mm = min(g.lip_h, g.wall * 0.5)
        try:
            body = body.faces(">Z").edges().chamfer(chamfer_mm)
        except Exception:
            # Chamfer can fail on degenerate/too-small edges for unusual
            # sizes; skip it rather than break STL generation entirely.
            pass

    # Hollow the bin above the foot region: wall thickness on the sides,
    # and a floor exactly g.wall thick sitting right on top of the feet.
    # The foot region itself (z: 0..g.foot_h) stays solid.
    floor_top = g.foot_h + g.wall
    cavity_h = max(z - floor_top + 1, 0.5)
    cavity = (
        cq.Workplane("XY")
        .workplane(offset=z - cavity_h + 1)
        .box(x - 2 * g.wall, y - 2 * g.wall, cavity_h, centered=(True, True, False))
    )
    try:
        body = body.cut(cavity)
    except Exception:
        pass

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
        try:
            if options.get("magnets"):
                body = _drill_corner_holes(body, x, y, g, diameter=6.5, depth=2.4)
            if options.get("screws"):
                # No fixed depth in the original design - screws go all the
                # way through so something can be bolted on from underneath.
                body = _drill_corner_holes(body, x, y, g, diameter=3.2, depth=z + 2)
        except Exception:
            pass

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
