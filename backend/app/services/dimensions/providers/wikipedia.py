from __future__ import annotations
from typing import Optional

import requests

from ..types import DimensionsResult
from ..parse import normalize_dims_from_text

API_ENDPOINT = "https://en.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "GridfinityCutoutGenerator/0.1 (https://github.com/monicaslgc/Gridfinity-Cutout-Generator)"
}


def fetch_wikipedia_dimensions(title: str) -> Optional[DimensionsResult]:
    """Best-effort fallback: pull the plain-text extract of a Wikipedia
    article and regex out an "L x W x H" style dimensions string. Much less
    reliable than Wikidata or schema.org, so it gets a lower confidence.
    """
    if not title or not title.strip():
        return None

    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "titles": title,
        "format": "json",
    }
    try:
        resp = requests.get(API_ENDPOINT, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    pages = data.get("query", {}).get("pages", {})
    text = ""
    for page in pages.values():
        text = page.get("extract") or ""
        break

    dims = normalize_dims_from_text(text)
    if not dims:
        return None

    return DimensionsResult(
        name=title,
        dims_mm=dims,
        source="Wikipedia (text extract)",
        source_url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
        confidence=0.4,
        evidence=[f"Regex-matched dimensions string in Wikipedia extract for {title!r}"],
        raw={"matched_text": text[:200]},
    )
