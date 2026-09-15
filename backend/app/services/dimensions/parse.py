from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from .units import to_mm

_UNIT_ALT = (
    r"mm|millimetre|millimeter|cm|centimetre|centimeter|m|metre|meter"
    r"|in|inch|inches|ft|foot|feet|″|′"
)

# The unit group used to be optional ((?P<unit>...)?), which let this match
# a bare "2 x 2 x 2" anywhere in an article with no attached unit at all -
# found for real against the "Rubik's Cube" Wikipedia article, where the
# regex matched an unrelated "2x2x2" mention (the Pocket Cube variant, not
# a measurement) and normalize_dims_from_text() then silently treated it
# as "2mm x 2mm x 2mm" (defaulting a missing unit to mm). That fed a
# physically absurd ~2mm item size all the way through to a "successful"
# /dimensions response, and downstream to a corrupt 46-byte STL file - a
# functional test walking the real pipeline caught this, not a code
# review. A bare number triplet with no unit is far too likely to be a
# move count, model number, grid size, or anything else - requiring an
# attached unit for a match is a cheap, real reduction in false positives.
_TRIPLET_RE = re.compile(
    r"(?P<a>\d{1,4}(?:[.,]\d{1,3})?)\s*[x×*]\s*"
    r"(?P<b>\d{1,4}(?:[.,]\d{1,3})?)\s*[x×*]\s*"
    r"(?P<c>\d{1,4}(?:[.,]\d{1,3})?)\s*"
    r"(?P<unit>" + _UNIT_ALT + r")",
    re.IGNORECASE,
)

_SINGLE_RE = re.compile(
    r"(?P<val>\d{1,4}(?:[.,]\d{1,3})?)\s*(?P<unit>" + _UNIT_ALT + r")",
    re.IGNORECASE,
)


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def parse_triplet(text: str) -> Optional[Tuple[float, float, float, Optional[str]]]:
    """Match a "152 x 106 x 60 mm" style triplet anywhere in `text`.

    A unit suffix is required for a match - see the note above _TRIPLET_RE
    for why a unit-less "N x N x N" is deliberately not treated as a
    dimensions string.
    """
    match = _TRIPLET_RE.search(text)
    if not match:
        return None
    a = _to_float(match.group("a"))
    b = _to_float(match.group("b"))
    c = _to_float(match.group("c"))
    return a, b, c, match.group("unit")


def parse_single(text: str) -> Optional[Tuple[float, Optional[str]]]:
    """Match a single "45 cm" style measurement anywhere in `text`."""
    match = _SINGLE_RE.search(text)
    if not match:
        return None
    return _to_float(match.group("val")), match.group("unit")


def normalize_dims_from_text(text: str) -> Optional[Dict[str, float]]:
    """Best-effort parse of a free-text dimensions string like
    "152 x 106 x 60 mm" into {"L", "W", "H"} millimetre values.

    Why: many sites and articles describe dimensions as plain text rather
    than structured data, so this is the fallback of last resort.
    """
    triple = parse_triplet(text)
    if not triple:
        return None
    a, b, c, unit = triple
    factor = to_mm(1.0, (unit or "mm").lower()) or 1.0
    return {"L": a * factor, "W": b * factor, "H": c * factor}
