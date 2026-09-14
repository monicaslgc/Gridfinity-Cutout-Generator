from __future__ import annotations
import re
from typing import Optional

import requests

from .types import DimensionsResult

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SEARCH_ENDPOINT = "https://www.wikidata.org/w/api.php"
HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "GridfinityCutoutGenerator/0.1 (https://github.com/monicaslgc/Gridfinity-Cutout-Generator)",
}

_QID_RE = re.compile(r"^Q\d+$")

# Wikidata properties: P2043 length, P2049 width, P2048 height.
_SPARQL_TEMPLATE = """
SELECT ?itemLabel ?length ?width ?height WHERE {{
  BIND(wd:{qid} AS ?item)
  OPTIONAL {{ ?item wdt:P2043 ?length. }}
  OPTIONAL {{ ?item wdt:P2049 ?width. }}
  OPTIONAL {{ ?item wdt:P2048 ?height. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}} LIMIT 1
"""


def search_wikidata_qid(query: str) -> Optional[str]:
    """Resolve free text to a Wikidata QID via the wbsearchentities API."""
    if not query or not query.strip():
        return None
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "format": "json",
        "limit": 1,
        "type": "item",
    }
    try:
        resp = requests.get(SEARCH_ENDPOINT, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    results = data.get("search") or []
    if results and results[0].get("id"):
        return results[0]["id"]
    return None


def _as_mm(raw_value: Optional[str]) -> Optional[float]:
    """Wikidata's truthy `wdt:` properties return a bare numeric literal
    with no attached unit. P2043/P2049/P2048 are conventionally recorded
    in metres for larger objects and in centimetres/millimetres for small
    ones, so - same heuristic used elsewhere in this codebase before this
    package existed - treat a raw value under 10 as metres (multiply by
    1000) and anything else as already being in millimetres. This is an
    approximation, not a guarantee; a fuller fix would query the unit via
    the `psv:`/`wikibase:quantityUnit` statement-value node instead.
    """
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return value * 1000 if value < 10 else value


def fetch_wikidata_dimensions(qid: Optional[str]) -> Optional[DimensionsResult]:
    """Look up L/W/H for a Wikidata QID via SPARQL. Returns None if `qid`
    isn't a well-formed QID, the query fails, or no dimensions are found.
    """
    if not qid or not _QID_RE.match(qid):
        return None

    params = {"query": _SPARQL_TEMPLATE.format(qid=qid), "format": "json"}
    try:
        resp = requests.get(SPARQL_ENDPOINT, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    bindings = data.get("results", {}).get("bindings", [])
    if not bindings:
        return None
    row = bindings[0]

    def get(key: str) -> Optional[str]:
        return row[key]["value"] if key in row else None

    dims = {}
    length_mm = _as_mm(get("length"))
    width_mm = _as_mm(get("width"))
    height_mm = _as_mm(get("height"))
    if length_mm is not None:
        dims["L"] = length_mm
    if width_mm is not None:
        dims["W"] = width_mm
    if height_mm is not None:
        dims["H"] = height_mm
    if not dims:
        return None

    return DimensionsResult(
        item_id=qid,
        name=get("itemLabel") or qid,
        dims_mm=dims,
        source="Wikidata",
        source_url=f"https://www.wikidata.org/wiki/{qid}",
        confidence=0.9 if len(dims) == 3 else 0.6,
        evidence=[f"Wikidata {qid}: P2043/P2049/P2048"],
        raw=row,
    )
