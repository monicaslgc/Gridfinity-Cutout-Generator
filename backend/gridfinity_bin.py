import cadquery as cq

def make_gridfinity_bin(
    x_slots=1,
    y_slots=1,
    z_units=3,
    lip=True,
    magnets=True,
    screws=False,
    wall=2.4
):
    SLOT = 42.0
    UNIT = 7.0
    BASE = 3.5
    LIP_HEIGHT = 1.5
    LIP_THICKNESS = 1.0
    MAGNET_D = 6.2
    MAGNET_DEPTH = 2.2
    SCREW_D = 3.2

    x = x_slots * SLOT
    y = y_slots * SLOT
    z = BASE + z_units * UNIT + (LIP_HEIGHT if lip else 0)

    # Main bin body
    bin = (
        cq.Workplane("XY")
        .box(x, y, z)
        .faces(">Z")
        .workplane()
        .rect(x - 2*wall, y - 2*wall)
        .cutBlind(-z + BASE)
    )

    # Add lip
    if lip:
        lip_geom = (
            cq.Workplane("XY")
            .box(x + 2*LIP_THICKNESS, y + 2*LIP_THICKNESS, LIP_HEIGHT)
            .translate((0, 0, z/2 - LIP_HEIGHT/2))
        )
        bin = bin.union(lip_geom)

    # Add magnet holes
    hole_pts = []
    for ix in [-1, 1]:
        for iy in [-1, 1]:
            hole_pts.append((ix*x/4, iy*y/4))

    if magnets:
        bin = (
            bin.faces("<Z")
            .workplane(centerOption="CenterOfBoundBox")
            .pushPoints(hole_pts)
            .hole(MAGNET_D, MAGNET_DEPTH)
        )
    if screws:
        bin = (
            bin.faces("<Z")
            .workplane(centerOption="CenterOfBoundBox")
            .pushPoints(hole_pts)
            .hole(SCREW_D, BASE)
        )

    return bin
