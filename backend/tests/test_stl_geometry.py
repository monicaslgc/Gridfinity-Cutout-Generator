"""Tests that the "easy" and "multi" proposal types actually produce
different geometry, not just a differently-sized plain box.

Background: proposals.py has always computed a `compartments` count for the
"multi" type and a looser `clearance` for "easy", but app/services/stl.py's
_make_bin() never read either field - every proposal type produced an
identical hollow box, just sized differently. That silently broke the
feature the README promises ("Easy Grab - finger cutouts", "Multi-purpose -
divided compartments"). These tests exercise the fix directly against
_make_bin(), comparing solid volume against an equivalently-sized "snug"
bin as a plain box baseline: a finger cutout must remove material (lower
volume), and compartment dividers must add material (higher volume).
"""
from __future__ import annotations

from app.models import Proposal
from app.services.stl import GFParams, _make_bin


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
