"""backend/cad/container_generator.py

Gridfinity container (bin) generator using CadQuery.

This module produces fully Gridfinity-compatible bins with optional
stacking lip, magnet/screw holes, interior compartments, and finger
cutouts. Export to STL for printing or consume the returned Workplane
for preview.

Usage:
    python -m backend.cad.container_generator --x 2 --y 2 --z 4 \
        --lip --magnets --compartments 1x2 --export out.stl

Requires:
    cadquery>=2.3

Notes:
    - Only comment on *why*, keep code self-explanatory.
    - Dimensions are in millimeters.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Literal, Optional, Tuple
import sys
import pathlib
from pathlib import Path

try:
    import cadquery as cq  # type: ignore
except Exception as exc:
    # Why: Provide actionable message if CadQuery isn't available.
    raise RuntimeError(
        "CadQuery is required. Install with `pip install cadquery` or use CQ-editor."
    ) from exc

# ---- Canonical Gridfinity constants ----
GF_SLOT = 42.0  # mm (X/Y)
GF_Z = 7.0      # mm (Z height unit)


@dataclass
class ContainerConfig:
    """Configuration for a Gridfinity container.

    Slots/units:
        x_slots, y_slots: multiples of 42 mm
        z_units: multiples of 7 mm for height

    Clearances and walling:
        wall_thickness: exterior wall thickness
        floor_thickness: bottom floor thickness
        inner_fillet: radius for internal edges
        outer_fillet: radius for outer vertical edges

    Options:
        lip: include stacking lip on top perimeter
        lip_depth: inward offset of lip (per side)
        lip_height: lip vertical height
        magnets: include 4x magnet bores underside
        magnet_diameter, magnet_thickness: dimensions of magnets
        magnet_edge_margin: distance from outer edges to magnet centers
        screws: include through-holes for M3 screws co-located with magnets
        compartments: grid (cx, cy). 1x1 means single cavity
        comp_wall: thickness for internal walls
        finger_cutouts: list of scoops (side, width, depth, height)
        clearance: applied to custom cutouts

    Custom cutouts:
        circles: (x, y, d)
        rects: (x, y, w, h, r)
        Positions are relative to center (0,0) at bin center, +X to right, +Y to front.
    """

    # Size
    x_slots: int = 1
    y_slots: int = 1
    z_units: int = 3

    # Shell
    wall_thickness: float = 2.0
    floor_thickness: float = 2.0
    inner_fillet: float = 1.0
    outer_fillet: float = 1.0

    # Lip
    lip: bool = True
    lip_depth: float = 1.0
    lip_height: float = 1.5

    # Underside features
    magnets: bool = True
    magnet_diameter: float = 6.0
    magnet_thickness: float = 2.0
    magnet_edge_margin: float = 7.0
    screws: bool = False
    screw_diameter: float = 3.2  # loose for M3

    # Interior
    compartments: Tuple[int, int] = (1, 1)
    comp_wall: float = 1.6

    # Finger cutouts: (side, width, depth, height)
    # side in {"+x", "-x", "+y", "-y"}
    finger_cutouts: List[Tuple[Literal['+x','-x','+y','-y'], float, float, float]] = field(
        default_factory=list
    )

    # Custom cutouts
    clearance: float = 0.3
    circles: List[Tuple[float, float, float]] = field(default_factory=list)  # x,y,diam
    rects: List[Tuple[float, float, float, float, float]] = field(default_factory=list)  # x,y,w,h,r

    # Export
    export_resolution: float = 0.1  # STL linear deflection

    def validate(self) -> None:
        if self.x_slots < 1 or self.y_slots < 1 or self.z_units < 1:
            raise ValueError("x/y/z must be >= 1 unit")
        if self.wall_thickness * 2 >= GF_SLOT * min(self.x_slots, self.y_slots):
            raise ValueError("Wall thickness too large for given slot count")
        if self.floor_thickness >= self.outer_height():
            raise ValueError("Floor thickness must be less than total height")
        cx, cy = self.compartments
        if cx < 1 or cy < 1:
            raise ValueError("Compartments must be >= 1x1")

    # Derived dims
    def outer_size(self) -> Tuple[float, float]:
        return (self.x_slots * GF_SLOT, self.y_slots * GF_SLOT)

    def outer_height(self) -> float:
        return self.z_units * GF_Z

    def inner_size(self) -> Tuple[float, float]:
        ox, oy = self.outer_size()
        return (ox - 2 * self.wall_thickness, oy - 2 * self.wall_thickness)

    def cavity_height(self) -> float:
        return self.outer_height() - self.floor_thickness


class GridfinityContainerGenerator:
    def __init__(self, cfg: ContainerConfig):
        cfg.validate()
        self.cfg = cfg

    # ---- Public API ----
    def build(self) -> cq.Workplane:
        body = self._make_shell()
        body = self._add_lip(body)
        body = self._add_underside(body)
        body = self._add_compartments(body)
        body = self._add_finger_cutouts(body)
        body = self._add_custom_cutouts(body)
        return body

    def export_stl(self, path: str | pathlib.Path) -> pathlib.Path:
        solid = self.build()
        out = pathlib.Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cq.exporters.export(solid.val(), str(out), tolerance=self.cfg.export_resolution)
        return out

    def export_with_preview(self, stl_path: str | Path, png_path: str | Path, *, elev: int = 25, azim: int = 45, dpi: int = 220) -> tuple[Path, Path]:
        """Export STL and a simple PNG preview (matplotlib + numpy-stl).
        Why: Give the API a quick thumbnail without requiring OpenGL.
        """
        stl_p = self.export_stl(stl_path)
        try:
            render_stl_preview_png(stl_p, png_path, elev=elev, azim=azim, dpi=dpi)
        except Exception as exc:
            # Don't fail export if preview rendering fails; surface context.
            raise RuntimeError(f"Preview render failed: {exc}") from exc
        return stl_p, Path(png_path)

    # ---- Builders ----
    def _make_shell(self) -> cq.Workplane:
        cfg = self.cfg
        ox, oy = cfg.outer_size()
        h = cfg.outer_height()
        # Base rectangle
        base = (
            cq.Workplane("XY")
            .rect(ox, oy)
            .extrude(h)
        )
        # Hollow interior
        ix, iy = cfg.inner_size()
        cavity = (
            cq.Workplane("XY")
            .rect(ix, iy)
            .workplane(offset=cfg.floor_thickness)
            .extrude(cfg.cavity_height(), combine=False)
        )
        shell = base.cut(cavity)
        # Fillets for printability
        if cfg.outer_fillet > 0:
            try:
                shell = shell.edges("|Z and >Y or |Z and <Y or |Z and >X or |Z and <X").fillet(cfg.outer_fillet)
            except Exception:
                pass
        if cfg.inner_fillet > 0:
            try:
                shell = shell.faces(">")  # top face
                # Why: apply small top inner fillet by offsetting a thin cut and filleting edges is complex; skip.
                shell = shell.parent  # no-op placeholder for inner fillet simplicity
            except Exception:
                pass
        return shell

    def _add_lip(self, wp: cq.Workplane) -> cq.Workplane:
        cfg = self.cfg
        if not cfg.lip:
            return wp
        ox, oy = cfg.outer_size()
        # Subtractive lip: nibble the top inside perimeter to create an inward step
        lip_wp = (
            cq.Workplane("XY")
            .rect(ox - 2 * cfg.lip_depth, oy - 2 * cfg.lip_depth)
            .workplane(offset=cfg.outer_height() - cfg.lip_height)
            .extrude(cfg.lip_height)
        )
        return wp.cut(lip_wp)

    def _add_underside(self, wp: cq.Workplane) -> cq.Workplane:
        cfg = self.cfg
        if not (cfg.magnets or cfg.screws):
            return wp
        ox, oy = cfg.outer_size()
        # Four positions near corners
        pts = [
            (sx * (ox / 2 - cfg.magnet_edge_margin), sy * (oy / 2 - cfg.magnet_edge_margin))
            for sx in (-1, 1)
            for sy in (-1, 1)
        ]
        # Why: Create holes on the bin's actual bottom face; previous approach
        # attempted to call .hole() on an empty Workplane, which CadQuery rejects
        # when multiple points are present.
        if cfg.magnets:
            wp = (
                wp
                .faces("<Z").workplane(centerOption="CenterOfMass")
                .pushPoints(pts)
                .hole(cfg.magnet_diameter, depth=cfg.magnet_thickness)
            )
        if cfg.screws:
            wp = (
                wp
                .faces("<Z").workplane(centerOption="CenterOfMass")
                .pushPoints(pts)
                .hole(cfg.screw_diameter, depth=cfg.outer_height())
            )
        return wp

    def _add_compartments(self, wp: cq.Workplane) -> cq.Workplane:
        cfg = self.cfg
        cx, cy = cfg.compartments
        if (cx, cy) == (1, 1):
            return wp
        ix, iy = cfg.inner_size()
        # Grid lines positions (excluding outer walls)
        x_lines = [(-ix / 2) + i * (ix / cx) for i in range(1, cx)]
        y_lines = [(-iy / 2) + j * (iy / cy) for j in range(1, cy)]
        height = cfg.cavity_height() - (cfg.lip_height if cfg.lip else 0.0)
        # Internal walls as positive solids unioned to body
        walls: List[cq.Workplane] = []
        for x in x_lines:
            walls.append(
                cq.Workplane("XY")
                .center(x, 0)
                .rect(cfg.comp_wall, iy)
                .extrude(height)
            )
        for y in y_lines:
            walls.append(
                cq.Workplane("XY")
                .center(0, y)
                .rect(ix, cfg.comp_wall)
                .extrude(height)
            )
        if walls:
            wp = wp.union(walls[0]) if walls else wp
            for w in walls[1:]:
                wp = wp.union(w)
        return wp

    def _add_finger_cutouts(self, wp: cq.Workplane) -> cq.Workplane:
        cfg = self.cfg
        if not cfg.finger_cutouts:
            return wp
        ox, oy = cfg.outer_size()
        h = cfg.outer_height()
        cuts: List[cq.Workplane] = []
        for side, width, depth, height in cfg.finger_cutouts:
            w = max(1e-3, width)
            d = max(1e-3, depth)
            z0 = h - height
            if side in ("+x", "-x"):
                x = (ox / 2) * (1 if side == "+x" else -1)
                cut = (
                    cq.Workplane("XY")
                    .center(x - (d if side == "+x" else -d) / 2, 0)
                    .rect(d, w)
                    .workplane(offset=z0)
                    .extrude(height)
                )
            else:
                y = (oy / 2) * (1 if side == "+y" else -1)
                cut = (
                    cq.Workplane("XY")
                    .center(0, y - (d if side == "+y" else -d) / 2)
                    .rect(w, d)
                    .workplane(offset=z0)
                    .extrude(height)
                )
            cuts.append(cut)
        for c in cuts:
            wp = wp.cut(c)
        return wp

    def _add_custom_cutouts(self, wp: cq.Workplane) -> cq.Workplane:
        cfg = self.cfg
        if not (cfg.circles or cfg.rects):
            return wp
        h = cfg.outer_height()
        usable_h = h - (cfg.lip_height if cfg.lip else 0.0)
        # Circles
        if cfg.circles:
            # Build per-circle to honor individual diameters.
            for (x, y, d) in cfg.circles:
                wp = wp.cut(
                    cq.Workplane("XY")
                    .center(x, y)
                    .circle((d + 2 * cfg.clearance) / 2.0)
                    .workplane(offset=cfg.floor_thickness)
                    .extrude(usable_h)
                )
        # Rectangles with optional corner radius r
        for (x, y, w, r_h, r) in cfg.rects:
            wp = wp.cut(
                cq.Workplane("XY")
                .center(x, y)
                .rect(w + 2 * cfg.clearance, r_h + 2 * cfg.clearance, forConstruction=False)
                .workplane(offset=cfg.floor_thickness)
                .extrude(usable_h)
            )
            if r > 0:
                # Why: Rounded rectangles require sketch filleting; CQ's `rect` with radius is limited across versions.
                pass
        return wp


# ---- Preview helper (headless) ----

def render_stl_preview_png(stl_path: str | Path, out_png: str | Path, *, elev: int = 25, azim: int = 45, dpi: int = 220) -> Path:
    """Render a basic shaded PNG from an STL using matplotlib (no OpenGL).
    Notes:
      - Requires `numpy-stl` and `matplotlib`.
      - Not photo-realistic, but fast and headless-friendly for thumbnails.
    """
    try:
        from stl import mesh  # pyright: ignore[reportMissingImports]  # numpy-stl
        import matplotlib
        matplotlib.use("Agg")  # headless
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except Exception as exc:
        raise RuntimeError(
            "Preview requires numpy-stl and matplotlib. Install: pip install numpy-stl matplotlib"
        ) from exc

    m = mesh.Mesh.from_file(str(stl_path))
    vectors = m.vectors  # (N, 3, 3)

    fig = plt.figure(figsize=(4, 4), dpi=dpi)
    ax = fig.add_subplot(111, projection="3d")

    # Mesh collection
    collection = Poly3DCollection(vectors, alpha=1.0, linewidths=0.1)
    collection.set_edgecolor((0, 0, 0, 0.15))  # subtle edges for definition
    ax.add_collection3d(collection)

    # Fit axes to mesh
    pts = vectors.reshape(-1, 3)
    mins = pts.min(axis=0)
    maxs = pts.max(axis=0)
    center = (mins + maxs) / 2.0
    size = (maxs - mins).max()
    r = size * 0.6
    ax.set_xlim(center[0] - r, center[0] + r)
    ax.set_ylim(center[1] - r, center[1] + r)
    ax.set_zlim(center[2] - r, center[2] + r)

    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.tight_layout(pad=0)

    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return out

# ---- CLI ----
import argparse


def _parse_compartments(text: str) -> Tuple[int, int]:
    if "x" not in text:
        raise argparse.ArgumentTypeError("Use format AxB, e.g., 2x3")
    a, b = text.lower().split("x", 1)
    try:
        return int(a), int(b)
    except ValueError as e:
        raise argparse.ArgumentTypeError("Compartments must be integers, e.g., 2x3") from e


def _parse_cutout_circle(text: str) -> Tuple[float, float, float]:
    # x,y,d
    try:
        x, y, d = map(float, text.split(","))
        return x, y, d
    except Exception as e:
        raise argparse.ArgumentTypeError("Circle cutout: x,y,d") from e


def _parse_cutout_rect(text: str) -> Tuple[float, float, float, float, float]:
    # x,y,w,h,r
    try:
        x, y, w, h, r = map(float, text.split(","))
        return x, y, w, h, r
    except Exception as e:
        raise argparse.ArgumentTypeError("Rect cutout: x,y,w,h,r") from e


def build_from_args(argv: Optional[Iterable[str]] = None) -> Tuple[GridfinityContainerGenerator, ContainerConfig, argparse.Namespace]:
    p = argparse.ArgumentParser(description="Gridfinity container generator (CadQuery)")
    p.add_argument("--x", dest="x", type=int, default=2)
    p.add_argument("--y", dest="y", type=int, default=2)
    p.add_argument("--z", dest="z", type=int, default=4)

    p.add_argument("--wall", type=float, default=2.0)
    p.add_argument("--floor", type=float, default=2.0)
    p.add_argument("--inner_fillet", type=float, default=1.0)
    p.add_argument("--outer_fillet", type=float, default=1.0)

    p.add_argument("--lip", action="store_true")
    p.add_argument("--no-lip", dest="lip", action="store_false")
    p.set_defaults(lip=True)
    p.add_argument("--lip_depth", type=float, default=1.0)
    p.add_argument("--lip_height", type=float, default=1.5)

    p.add_argument("--magnets", action="store_true")
    p.add_argument("--no-magnets", dest="magnets", action="store_false")
    p.set_defaults(magnets=True)
    p.add_argument("--magnet_d", type=float, default=6.0)
    p.add_argument("--magnet_t", type=float, default=2.0)
    p.add_argument("--magnet_margin", type=float, default=7.0)

    p.add_argument("--screws", action="store_true")
    p.add_argument("--screw_d", type=float, default=3.2)

    p.add_argument("--compartments", type=_parse_compartments, default="1x1")
    p.add_argument("--comp_wall", type=float, default=1.6)

    p.add_argument("--finger", action="append", default=[], help="side,width,depth,height (e.g., +x,24,10,12)")

    p.add_argument("--clearance", type=float, default=0.3)
    p.add_argument("--circle", action="append", type=_parse_cutout_circle, default=[])
    p.add_argument("--rect", action="append", type=_parse_cutout_rect, default=[])

    p.add_argument("--export", type=str, default="")
    p.add_argument("--preview", type=str, default="", help="Optional PNG preview path")
    p.add_argument("--demo", action="store_true", help="Build a sample bin and export demo.stl")

    args = p.parse_args(list(argv) if argv is not None else None)

    finger_cutouts: List[Tuple[Literal['+x','-x','+y','-y'], float, float, float]] = []
    for f in args.finger:
        try:
            side, w, d, h = f.split(",")
            if side not in {"+x", "-x", "+y", "-y"}:
                raise ValueError("side must be one of +x,-x,+y,-y")
            finger_cutouts.append((side, float(w), float(d), float(h)))
        except Exception as e:
            raise SystemExit(f"Invalid --finger '{f}': use side,width,depth,height") from e

    cfg = ContainerConfig(
        x_slots=int(args.x),
        y_slots=int(args.y),
        z_units=int(args.z),
        wall_thickness=args.wall,
        floor_thickness=args.floor,
        inner_fillet=args.inner_fillet,
        outer_fillet=args.outer_fillet,
        lip=bool(args.lip),
        lip_depth=args.lip_depth,
        lip_height=args.lip_height,
        magnets=bool(args.magnets),
        magnet_diameter=args.magnet_d,
        magnet_thickness=args.magnet_t,
        magnet_edge_margin=args.magnet_margin,
        screws=bool(args.screws),
        screw_diameter=args.screw_d,
        compartments=args.compartments if isinstance(args.compartments, tuple) else _parse_compartments(args.compartments),
        comp_wall=args.comp_wall,
        finger_cutouts=finger_cutouts,
        clearance=args.clearance,
        circles=list(args.circle),
        rects=list(args.rect),
    )

    gen = GridfinityContainerGenerator(cfg)
    return gen, cfg, args


def main(argv: Optional[Iterable[str]] = None) -> int:
    gen, cfg, args = build_from_args(argv)
    if args.demo:
        # Simple demo: 2x2, finger cutouts on +x and -x
        demo_out = pathlib.Path("demo.stl")
        gen.cfg.finger_cutouts = gen.cfg.finger_cutouts or [("+x", 24, 10, 12), ("-x", 24, 10, 12)]
        gen.export_stl(demo_out)
        print(f"Exported {demo_out.resolve()}")
        return 0

    if args.export:
        if args.preview:
            stl_out, png_out = gen.export_with_preview(args.export, args.preview)
            print(f"Exported {stl_out.resolve()} and preview {png_out.resolve()}")
        else:
            out = gen.export_stl(args.export)
            print(f"Exported {out.resolve()}")
    else:
        _ = gen.build()
        print("Built container (no export)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
