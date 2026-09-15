"""Tests for the keyword-based cutout shape heuristic (app/services/shape.py).

See that module's docstring for why this is a keyword guess rather than
real shape recognition: no STL import or photo-based silhouette pipeline
exists, so this is what stands in for the project's namesake "cutout"
feature - a rough shape guess from the item's name, using data the
pipeline already has for every item.
"""
from __future__ import annotations

from app.services.shape import classify_shape


def test_classifies_bottle_as_cylinder():
    assert classify_shape("Hydro Flask Water Bottle") == "cylinder"


def test_classifies_flashlight_as_cylinder():
    assert classify_shape("Maglite LED Flashlight") == "cylinder"


def test_classifies_controller_as_rounded_box():
    assert classify_shape("Nintendo Switch Pro Controller") == "rounded_box"


def test_classifies_power_bank_as_rounded_box():
    assert classify_shape("Belkin BoostCharge Power Bank 10000mAh") == "rounded_box"


def test_classifies_unknown_item_as_box():
    assert classify_shape("Mystery Widget") == "box"


def test_classifies_missing_label_as_box():
    assert classify_shape(None) == "box"
    assert classify_shape("") == "box"


def test_is_case_insensitive():
    assert classify_shape("STAINLESS STEEL BOTTLE") == "cylinder"


def test_cylinder_keyword_takes_priority_over_rounded_box_keyword():
    # A word for each list appearing together shouldn't crash or pick
    # arbitrarily based on dict/set ordering - cylinder is checked first,
    # deliberately, since a round item is the bigger geometric mismatch if
    # a plain box is used instead.
    assert classify_shape("Camera battery cylinder cell") == "cylinder"
