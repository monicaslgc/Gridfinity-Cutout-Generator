"""Guess a basic cutout cavity shape for an item from its name.

Why a heuristic and not real shape recognition: the reference tool Monica
pointed at (gridfinitygenerator.com/en/cutout) builds custom-fitted cutouts
from an imported STL of the item. That's not workable as the *default* path
here - most real-world items (a random Amazon listing, a household object)
don't have a public 3D model to import, and this project's /identify-image
endpoint is still a placeholder (no real photo-based shape extraction
exists). So instead of a plain rectangular cavity for every item regardless
of its actual shape, this does a pragmatic keyword guess - box / rounded
box / cylinder - from the item's name, which is data the pipeline already
has for every item. It's a real improvement over "always a flat box", not a
substitute for a true custom fit; STL import and/or photo-based shape
extraction remain open roadmap items for a better fit.
"""
from __future__ import annotations

_CYLINDER_KEYWORDS = (
    "bottle", "can", "tube", "cylinder", "cylindrical", "thermos", "flask",
    "canister", "roll", "spool", "jar", "tumbler", "mug", "cup", "flashlight",
    "torch", "marker", "pen", "battery", "lipstick", "candle",
)

_ROUNDED_BOX_KEYWORDS = (
    "controller", "remote", "phone", "smartphone", "wallet", "card",
    "mouse", "pod", "earbud", "case", "cartridge", "power bank",
    "powerbank", "charger", "router", "speaker", "camera", "watch",
)


def classify_shape(label: "str | None") -> str:
    """Return "cylinder", "rounded_box", or "box" (the default/fallback)
    based on keywords found in an item's name. Case-insensitive substring
    match against short keyword lists; first match wins, cylinder checked
    before rounded_box since a round item is the bigger geometric mismatch
    if a plain box is used instead.
    """
    if not label:
        return "box"
    text = label.lower()
    if any(kw in text for kw in _CYLINDER_KEYWORDS):
        return "cylinder"
    if any(kw in text for kw in _ROUNDED_BOX_KEYWORDS):
        return "rounded_box"
    return "box"
