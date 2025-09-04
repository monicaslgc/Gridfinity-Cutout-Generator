from __future__ import annotations
from .units import to_mm


_DIM_RE = re.compile(
r"(?P<a>\d{1,4}(?:[\.,]\d{1,3})?)\s*[×xX*]\s*(?P<b>\d{1,4}(?:[\.,]\d{1,3})?)\s*[×xX*]\s*(?P<c>\d{1,4}(?:[\.,]\d{1,3})?)\s*(?P<unit>mm|millimetre|millimeter|cm|centimetre|centimeter|m|metre|meter|in|inch|inches|″|"|ft|foot|feet|′)?",
re.IGNORECASE,
)
_NUM_UNIT_RE = re.compile(
r"(?P<val>\d{1,4}(?:[\.,]\d{1,3})?)\s*(?P<unit>mm|millimetre|millimeter|cm|centimetre|centimeter|m|metre|meter|in|inch|inches|″|"|ft|foot|feet|′)",
re.IGNORECASE,
)




def _to_float(s: str) -> float:
return float(s.replace(",", "."))




def parse_triplet(text: str) -> Optional[Tuple[float, float, float, Optional[str]]]:
m = _DIM_RE.search(text)
if not m:
return None
a = _to_float(m.group("a"))
b = _to_float(m.group("b"))
c = _to_float(m.group("c"))
unit = m.group("unit")
return a, b, c, unit




def parse_single(text: str) -> Optional[Tuple[float, Optional[str]]]:
m = _NUM_UNIT_RE.search(text)
if not m:
return None
return _to_float(m.group("val")), m.group("unit")




def normalize_dims_from_text(text: str) -> Optional[Dict[str, float]]:
"""Try to parse common dimension strings like "152 × 106 × 60 mm".
Why: many sites serialize dimensions as free text.
"""
triple = parse_triplet(text)
if triple:
a, b, c, unit = triple
factor = to_mm(1.0, unit) or 1.0
return {"L": a * factor, "W": b * factor, "H": c * factor}
one = parse_single(text)
if one: # Could be diameter, thickness, etc. Caller must map.
val, unit = one
factor = to_mm(1.0, unit) or 1.0
return {"L": val * factor}
return None

