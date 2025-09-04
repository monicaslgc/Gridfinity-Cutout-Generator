from __future__ import annotations
import math
from ..models import ProposalsRequest, ProposalsResponse, Proposal

GRID_XY = 42.0
GRID_Z = 7.0
DEFAULT_CLEARANCE_SNUG = 0.3
DEFAULT_CLEARANCE_EASY = 0.8
WALL = 2.0
BASE = 3.0


def _slots(size_mm: float, clearance: float) -> int:
    needed = size_mm + clearance + 2 * WALL
    return max(1, math.ceil(needed / GRID_XY))


def _z_units(height_mm: float, clearance: float) -> int:
    needed = height_mm + clearance + BASE
    return max(1, math.ceil(needed / GRID_Z))


def generate_proposals(req: ProposalsRequest) -> ProposalsResponse:
    L, W, H = req.dims_mm.L, req.dims_mm.W, req.dims_mm.H

    snug = Proposal(
        type="snug",
        x_slots=_slots(L, DEFAULT_CLEARANCE_SNUG),
        y_slots=_slots(W, DEFAULT_CLEARANCE_SNUG),
        z_units=_z_units(H, DEFAULT_CLEARANCE_SNUG),
        clearance=DEFAULT_CLEARANCE_SNUG,
    )

    easy = Proposal(
        type="easy",
        x_slots=_slots(L, DEFAULT_CLEARANCE_EASY),
        y_slots=_slots(W, DEFAULT_CLEARANCE_EASY),
        z_units=_z_units(H, DEFAULT_CLEARANCE_EASY),
        clearance=DEFAULT_CLEARANCE_EASY,
    )

    multi = Proposal(
        type="multi",
        x_slots=max(snug.x_slots, 2),
        y_slots=max(snug.y_slots, 2),
        z_units=snug.z_units,
        clearance=DEFAULT_CLEARANCE_EASY,
        compartments=2,
    )

    return ProposalsResponse(proposals=[snug, easy, multi])
