import cadquery as cq

# Gridfinity standard parameters (can be changed as needed)
CELL_SIZE = 42           # mm, size of each gridfinity cell
BASE_HEIGHT = 7          # mm, standard base height
LIP_HEIGHT = 1           # mm, stacking lip height
MAGNET_DIAMETER = 6      # mm, for 6x2.5mm magnets
MAGNET_DEPTH = 2.5       # mm, for 6x2.5mm magnets
MAGNET_OFFSET = 7        # mm, from corners
CORNER_CHAMFER = 2       # mm, optional

def gridfinity_base(
    x_cells=1,
    y_cells=1,
    base_height=BASE_HEIGHT,
    lip_height=LIP_HEIGHT,
    add_magnet_holes=True,
    magnet_diameter=MAGNET_DIAMETER,
    magnet_depth=MAGNET_DEPTH,
    magnet_offset=MAGNET_OFFSET,
    corner_chamfer=CORNER_CHAMFER
):
    length = x_cells * CELL_SIZE
    width = y_cells * CELL_SIZE

    # Main base
    base = cq.Workplane("XY").box(length, width, base_height)

    # Add stacking lip
    base = base.faces(">Z").workplane().rect(length, width).extrude(lip_height)

    # Add optional chamfer to bottom corners
    if corner_chamfer > 0:
        base = base.edges("|Z and <Y and <X or <Y and >X or >Y and <X or >Y and >X").chamfer(corner_chamfer)

    # Add magnet holes in the four corners
    if add_magnet_holes:
        for i in [0, x_cells-1]:
            for j in [0, y_cells-1]:
                cx = -length / 2 + magnet_offset + i * (length - 2 * magnet_offset)
                cy = -width / 2 + magnet_offset + j * (width - 2 * magnet_offset)
                base = base.faces("<Z").workplane(centerOption="CenterOfBoundBox").center(cx, cy).hole(magnet_diameter, magnet_depth)
    return base

# Example: create a 1x1 base and export as STL
if __name__ == "__main__":
    result = gridfinity_base(x_cells=1, y_cells=1)
    cq.exporters.export(result, 'gridfinity_base_1x1.stl')
