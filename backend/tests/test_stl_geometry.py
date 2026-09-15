"""Tests that generated bins have real, distinguishing geometry: the
"easy" and "multi" proposal types actually differ from a plain box, and -
the subject of the newer tests below - every bin actually has the real
Gridfinity interlocking base/foot profile on its underside, not a flat
floor.

Background: proposals.py has always computed a `compartments` count for the
"multi" type and a looser `clearance` for "easy", but app/services/stl.py's
_make_bin() never read either field - every proposal type produced an
identical hollow box, just sized differently. That silently broke the
feature the README promises ("Easy Grab - finger cutouts", "Multi-purpose -
divided compartments"). Those tests exercise the fix directly against
_make_bin(), comparing solid volume against an equivalently-sized "snug"
bin as a plain box baseline: a finger cutout must remove material (lower
volume), and compartment dividers must add material (higher volume).

Separately, _make_bin() never implemented the actual Gridfinity base/foot
profile at all - the underside of every bin was just a flat floor, so
generated bins would not register or press-fit into a real Gridfinity
baseplate, no matter how correctly sized they were. The
test_bin_foot_profile_* tests below cover that fix (_make_gridfinity_foot /
_add_gridfinity_feet): the foot must actually widen from its bottom tip to
where it meets the bin body, and a multi-cell bin's bottom must be made up
of one separate foot per grid cell rather than a single flat face.
"""
from __future__ import annotations

from app.models import Proposal
from app.services.stl import GFParams, _make_bin, _make_gridfinity_foot


def _volume(proposal: Proposal, options: dict | None = None) -> float:
    g = GFParams()
    body = _make_bin(proposal, None, options or {"lip": False}, g)
    return body.val().Volume()


def _same_size_proposal(kind: str, **extra) -> Proposal:
    return Proposal(
        type=kind,
        x_slots=3,
        y_slots=2,
        z_units=4,
        clearance=0.3,
        **extra,
    )


def test_easy_bin_removes_material_for_finger_cutout():
    snug_volume = _volume(_same_size_proposal("snug"))
    easy_volume = _volume(_same_size_proposal("easy"))
    assert easy_volume < snug_volume


def test_multi_bin_adds_material_for_compartment_dividers():
    snug_volume = _volume(_same_size_proposal("snug"))
    multi_volume = _volume(_same_size_proposal("multi", compartments=2))
    assert multi_volume > snug_volume


def test_multi_bin_with_one_compartment_is_unchanged():
    # compartments=1 (or None) means "don't split" - no dividers should be
    # added, so this should match the plain snug-shaped baseline exactly.
    snug_volume = _volume(_same_size_proposal("snug"))
    multi_volume = _volume(_same_size_proposal("multi", compartments=1))
    assert multi_volume == snug_volume


def test_easy_bin_smallest_possible_size_does_not_crash():
    g = GFParams()
    proposal = Proposal(type="easy", x_slots=1, y_slots=1, z_units=1, clearance=0.3)
    body = _make_bin(proposal, None, {"lip": True, "magnets": True, "screws": True}, g)
    assert body.val().Volume() > 0


def test_multi_bin_smallest_possible_size_does_not_crash():
    g = GFParams()
    proposal = Proposal(type="multi", x_slots=1, y_slots=1, z_units=1, clearance=0.3, compartments=2)
    body = _make_bin(proposal, None, {"lip": True, "magnets": True, "screws": True}, g)
    assert body.val().Volume() > 0


def test_foot_profile_widens_from_bottom_tip_to_top():
    # The foot must actually be a tapered stack - narrow at z=0 (the tip
    # that enters a baseplate socket), wider at z=foot_h (where it meets
    # the bin body). A flat-floored bin (the bug being fixed here) would
    # have no such taper at all.
    g = GFParams()
    foot = _make_gridfinity_foot(g)
    bb = foot.val().BoundingBox()
    assert bb.zmin == 0
    assert abs(bb.zmax - g.foot_h) < 1e-6

    bottom_area = foot.faces("<Z").val().Area()
    top_area = foot.faces(">Z").val().Area()
    assert bottom_area < top_area


def test_bin_bottom_has_one_foot_per_grid_cell_not_a_flat_floor():
    # This is the concrete "does it have the gridfinity grid" check: a
    # multi-cell bin's underside should be made of one separate foot per
    # 42x42mm cell (this bin is 3x2 slots -> 6 feet), not a single flat
    # face spanning the whole footprint.
    g = GFParams()
    proposal = _same_size_proposal("snug")  # 3x2 slots
    body = _make_bin(proposal, None, {"lip": False}, g)
    bottom_faces = body.faces("<Z").vals()
    assert len(bottom_faces) == proposal.x_slots * proposal.y_slots


def test_bin_with_magnets_and_screws_still_builds_with_feet():
    # Corner holes are drilled relative to a single foot's narrowest point
    # now (see _drill_corner_holes), not a flat face selector - make sure
    # that still produces valid, non-empty geometry for a normal-sized bin.
    g = GFParams()
    proposal = _same_size_proposal("snug")
    body = _make_bin(proposal, None, {"lip": True, "magnets": True, "screws": True}, g)
    assert body.val().Volume() > 0
