from __future__ import annotations
import json
import urllib.parse
import urllib.request
from typing import Optional
from ..models import DimensionsResponse, Dimensions

# Simple fallback catalog (why: ensure demo works offline)
FALLBACK = {
    "Qnintendo_switch_pro": DimensionsResponse(
        id="Qnintendo_switch_pro",
        name="Nintendo Switch Pro Controller",
        dims_mm=Dimensions(L=152, W=106, H=60),
        source="fallback",
        confidence=0.7,
    )
}

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "GridfinityCutout/0.1 (https://example.com)"
}


def _sparql_for_item(qid: str) -> str:
    return f"""
    SELECT ?item ?itemLabel ?length ?width ?height WHERE {{
      BIND(wd:{qid} AS ?item)
      OPTIONAL {{ ?item wdt:P2043 ?length. }}
      OPTIONAL {{ ?item wdt:P2049 ?width. }}
      OPTIONAL {{ ?item wdt:P2048 ?height. }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }} LIMIT 1
    """


async def fetch_dimensions(qid: str) -> Optional[DimensionsResponse]:
    # try fallback match
    if qid in FALLBACK:
        return FALLBACK[qid]
    # try Wikidata when qid looks like Q12345
    if qid and qid[0] == "Q" and qid[1:].isdigit():
        try:
            q = _sparql_for_item(qid)
            url = SPARQL_ENDPOINT + "?" + urllib.parse.urlencode({"query": q})
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            b = data["results"]["bindings"]
            if b:
                first = b[0]
                def getv(k):
                    return float(first[k]["value"]) if k in first else None
                L = getv("length")
                W = getv("width")
                H = getv("height")
                if all(v is not None for v in (L, W, H)):
                    return DimensionsResponse(
                        id=qid,
                        name=first.get("itemLabel", {}).get("value", qid),
                        dims_mm=Dimensions(L=L * 1000 if L < 10 else L,  # mm heuristic
                                          W=W * 1000 if W < 10 else W,
                                          H=H * 1000 if H < 10 else H),
                        source="Wikidata",
                        confidence=0.9,
                    )
        except Exception:
            pass
    return None
