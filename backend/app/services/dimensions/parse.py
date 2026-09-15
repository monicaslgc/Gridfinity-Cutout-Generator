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

# A 2-number "L by W unit" / "L x W unit" pair - the conventional way
# Wikipedia prose states the size of flat/2D items. Confirmed against real
# articles while chasing why the functional test's 13 candidate items all
# failed to resolve dimensions: the "Credit card" article states its size
# in prose as "85.60 by 53.98 millimeters (3+3/8 in x 2+1/8 in)" -
# ISO/IEC 7810 ID-1 - never as a 3-number triplet. "by" is the dominant
# separator for this pattern on Wikipedia (x/× is also accepted since it's
# used interchangeably in some articles), and a unit is required for the
# same false-positive-avoidance reason as _TRIPLET_RE above.
#
# IMPORTANT: this intentionally yields only L/W, never a guessed H. A
# prior fix this session (see _MIN/MAX_PLAUSIBLE_MM below) exists because
# fabricating numbers from thin evidence produced physically wrong,
# silently "successful" results before - the same discipline applies
# here: a flat item's thickness is not implied by its length and width,
# so this does not invent one. normalize_dims_from_text() below returns a
# partial {"L", "W"} dict in this case; callers that need is_complete()
# (all three axes) still correctly require a third source for H rather
# than getting a fabricated value from here.
_PAIR_RE = re.compile(
    r"(?P<a>\d{1,4}(?:[.,]\d{1,3})?)\s*(?:by|[x×*])\s*"
    r"(?P<b>\d{1,4}(?:[.,]\d{1,3})?)\s*"
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
    dimensions string. Returns the *first* match with no plausibility
    check; normalize_dims_from_text() below is what applies the sanity
    bound and tries multiple matches, so prefer that for real use - this
    is kept simple/direct for callers (and tests) that just want the raw
    first match.
    """
    match = _TRIPLET_RE.search(text)
    if not match:
        return None
    a = _to_float(match.group("a"))
    b = _to_float(match.group("b"))
    c = _to_float(match.group("c"))
    return a, b, c, match.group("unit")


def parse_pair(text: str) -> Optional[Tuple[float, float, Optional[str]]]:
    """Match a "85.60 by 53.98 millimetres" style 2D pair anywhere in
    `text` - see the note above _PAIR_RE for why this exists and why it
    deliberately does not also return a height. Returns the *first* match
    with no plausibility check, same division of labour as parse_triplet
    vs. normalize_dims_from_text.
    """
    match = _PAIR_RE.search(text)
    if not match:
        return None
    a = _to_float(match.group("a"))
    b = _to_float(match.group("b"))
    return a, b, match.group("unit")


def parse_single(text: str) -> Optional[Tuple[float, Optional[str]]]:
    """Match a single "45 cm" style measurement anywhere in `text`."""
    match = _SINGLE_RE.search(text)
    if not match:
        return None
    return _to_float(match.group("val")), match.group("unit")


# Plausibility bound for normalize_dims_from_text's regex matches, in mm.
# Requiring a unit (see _TRIPLET_RE above) rules out plainly unit-less
# false positives, but a real functional test against the "Rubik's Cube"
# Wikipedia article found the regex *still* latching onto unrelated
# numbers that happen to have a unit-like word nearby: first a "2×2×2"
# mention of the Pocket Cube variant (read as 2mm), then - after
# requiring a unit - a "21×21×21" giant-cube-variant mention that
# happened to sit next to the word "in" from "weighing in", misread as
# 21 inches = 533.4mm. Neither is remotely close to a real ~57mm cube.
# There's no cheap way to make free-text extraction fully reliable, but
# rejecting matches outside a sane range for something meant to fit in a
# Gridfinity bin is a real, defensible improvement: it would have caught
# both false positives above, at the cost of also rejecting genuinely
# tiny (<3mm) or large (>400mm) items via this fallback path - an
# acceptable trade for a last-resort, low-confidence (0.4) source. The
# same bound is applied to 2D pair matches below for the same reason.
_MIN_PLAUSIBLE_MM = 3.0
_MAX_PLAUSIBLE_MM = 400.0


def normalize_dims_from_text(text: str) -> Optional[Dict[str, float]]:
    """Best-effort parse of a free-text dimensions string into millimetre
    values.

    Tries every unit-tagged 3-number triplet in the text first (e.g.
    "152 x 106 x 60 mm") and returns the first one where all three axes
    land within a plausible range - see _MIN_PLAUSIBLE_MM/_MAX_PLAUSIBLE_MM.

    If no triplet passes, falls back to a 2-number "L by W unit" pair
    (e.g. "85.60 by 53.98 millimetres") - the way Wikipedia conventionally
    states the size of flat/2D items like cards and paper, which a 3-axis
    regex can never match. This returns only {"L", "W"}, never a guessed
    "H" - see the note above _PAIR_RE for why fabricating a thickness
    would repeat the same mistake the plausibility bound above was added
    to fix. A partial {"L", "W"} result is still useful to a caller that
    merges evidence from multiple sources (see
    dimensions/types.py:merge_missing) and can pick up "H" elsewhere;
    callers that require all three axes correctly still treat this alone
    as incomplete.
    """
    for match in _TRIPLET_RE.finditer(text):
        a = _to_float(match.group("a"))
        b = _to_float(match.group("b"))
        c = _to_float(match.group("c"))
        unit = match.group("unit")
        factor = to_mm(1.0, (unit or "mm").lower()) or 1.0
        dims = (a * factor, b * factor, c * factor)
        if all(_MIN_PLAUSIBLE_MM <= d <= _MAX_PLAUSIBLE_MM for d in dims):
            return {"L": dims[0], "W": dims[1], "H": dims[2]}

    for match in _PAIR_RE.finditer(text):
        a = _to_float(match.group("a"))
        b = _to_float(match.group("b"))
        unit = match.group("unit")
        factor = to_mm(1.0, (unit or "mm").lower()) or 1.0
        dims = (a * factor, b * factor)
        if all(_MIN_PLAUSIBLE_MM <= d <= _MAX_PLAUSIBLE_MM for d in dims):
            return {"L": dims[0], "W": dims[1]}

    return None
