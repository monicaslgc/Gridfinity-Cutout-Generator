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
import re

# Single words are matched as whole tokens (see _matches) so a keyword like
# "roll" doesn't false-positive inside an unrelated word that happens to
# contain those letters (e.g. "controller" contains "roll" as a raw
# substring - caught by a real test failure in CI, not guessed). Entries
# with a space are phrases and are matched as substrings instead, since a
# multi-word phrase is in practice never an accidental substring collision.
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


def _matches(text: str, words: "set[str]", keywords: "tuple[str, ...]") -> bool:
    for kw in keywords:
        if " " in kw:
            if kw in text:
                return True
        elif kw in words:
            return True
    return False


def classify_shape(label: "str | None") -> str:
    """Return "cylinder", "rounded_box", or "box" (the default/fallback)
    based on keywords found in an item's name. Single-word keywords must
    match a whole word in the (lowercased) name, not just appear as a raw
    substring; multi-word keyword phrases are matched as substrings of the
    full name. Cylinder is checked before rounded_box since a round item
    is the bigger geometric mismatch if a plain box cavity is used instead.
    """
    if not label:
        return "box"
    text = label.lower()
    words = set(re.findall(r"[a-z0-9]+", text))
    if _matches(text, words, _CYLINDER_KEYWORDS):
        return "cylinder"
    if _matches(text, words, _ROUNDED_BOX_KEYWORDS):
        return "rounded_box"
    return "box"
