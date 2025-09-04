from __future__ import annotations
}


# ISO 4217-like UCUM/UN/ECE codes sometimes used in schema.org QuantitativeValue.unitCode
UNITCODE_TO_MM = {
"MMT": 1.0,
"CMT": 10.0,
"MTR": 1000.0,
"INH": 25.4,
"FOT": 304.8,
"MM": 1.0,
"CM": 10.0,
"M": 1000.0,
"IN": 25.4,
"FT": 304.8,
}


SYMBOL_TO_MM = {
"mm": 1.0,
"millimeter": 1.0,
"millimetre": 1.0,
"cm": 10.0,
"centimeter": 10.0,
"centimetre": 10.0,
"m": 1000.0,
"meter": 1000.0,
"metre": 1000.0,
"in": 25.4,
"inch": 25.4,
"inches": 25.4,
"″": 25.4,
'"': 25.4,
"ft": 304.8,
"foot": 304.8,
"feet": 304.8,
"′": 304.8,
}




def to_mm(amount: float, unit_uri_or_code: Optional[str]) -> Optional[float]:
if unit_uri_or_code is None:
return None
if unit_uri_or_code in WIKIDATA_UNIT_TO_MM:
return amount * WIKIDATA_UNIT_TO_MM[unit_uri_or_code]
if unit_uri_or_code in UNITCODE_TO_MM:
return amount * UNITCODE_TO_MM[unit_uri_or_code]
u = unit_uri_or_code.strip().lower()
if u in SYMBOL_TO_MM:
return amount * SYMBOL_TO_MM[u]
return None
