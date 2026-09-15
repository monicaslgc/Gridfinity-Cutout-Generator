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
    """Look up L/W/H for a Wikidata QID via SPARQL.

    Returns None only if `qid` isn't a well-formed QID, the query fails
    outright, or Wikidata has no English label for the item at all (so
    there is nothing usable to hand back even as a fallback label).

    IMPORTANT (bug fix): this used to return None whenever none of
    P2043/P2049/P2048 were populated - which discarded the item's
    `itemLabel` along with the missing dimensions. That silently broke
    the Wikipedia fallback in fetcher.py for the normal `/dimensions?id=`
    flow (the one /identify -> /dimensions actually uses): fetcher.py's
    label fallback is `(best.name if best else None) or query`, and with
    `best` coming back None and no free-text `query` given (callers pass
    a QID, not text, once an item has been identified), `label` ended up
    None and the Wikipedia lookup was never attempted at all - regardless
    of whether Wikipedia's article actually had the dimensions in text.
    A functional test against 13 real, well-known items (credit card, A4
    paper, Nintendo Switch, iPhone 15, Rubik's Cube, etc.) found this:
    every single one resolved to a real Wikidata QID and then 404'd on
    /dimensions, because none of them happen to have all of P2043/P2049/
    P2048 filled in on Wikidata - a very common situation for consumer
    products - and the Wikipedia fallback that should have caught most of
    them never ran.

    Now, whenever the SPARQL query returns a row at all (i.e. the QID
    resolves to a real, labeled Wikidata item), a DimensionsResult is
    returned even if dims_mm ends up empty - with confidence 0.0 so it
    never outranks a real measurement via merge_missing, but carrying the
    item's name so fetcher.py has something to search Wikipedia with.
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

    name = get("itemLabel") or qid

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
        # No dimension properties on Wikidata for this item - still hand
        # back the resolved name (confidence 0.0) so callers can fall
        # back to Wikipedia/schema.org with real search text instead of
        # giving up outright.
        return DimensionsResult(
            item_id=qid,
            name=name,
            dims_mm={},
            source="Wikidata",
            source_url=f"https://www.wikidata.org/wiki/{qid}",
            confidence=0.0,
            evidence=[f"Wikidata {qid}: no P2043/P2049/P2048 found"],
            raw=row,
        )

    return DimensionsResult(
        item_id=qid,
        name=name,
        dims_mm=dims,
        source="Wikidata",
        source_url=f"https://www.wikidata.org/wiki/{qid}",
        confidence=0.9 if len(dims) == 3 else 0.6,
        evidence=[f"Wikidata {qid}: P2043/P2049/P2048"],
        raw=row,
    )
