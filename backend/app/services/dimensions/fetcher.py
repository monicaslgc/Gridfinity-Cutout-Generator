from __future__ import annotations
from typing import List, Optional, Tuple

from .types import DimensionsResult
from .wikidata import search_wikidata_qid, fetch_wikidata_dimensions
from .providers.schema_org import fetch_schema_org_dimensions
from .providers.wikipedia import fetch_wikipedia_dimensions


async def fetch_dimensions(
    qid: Optional[str] = None,
    query: Optional[str] = None,
    extra_urls: Optional[List[str]] = None,
) -> Tuple[Optional[DimensionsResult], Optional[str]]:
    """Aggregate real-world dimensions for an item from Wikidata, manufacturer
    schema.org product pages, and Wikipedia, in that order of trust - each
    later source only fills in whatever the earlier ones are missing.

    Why sync HTTP calls inside an async function: the underlying requests
    all go through `requests` rather than an async HTTP client, which is
    the simplest option at this project's scale (no extra dependency for a
    handful of infrequent lookups), at the cost of briefly blocking the
    event loop per call.
    """
    extra_urls = extra_urls or []
    resolved_qid = qid

    if not resolved_qid and query:
        resolved_qid = search_wikidata_qid(query)

    best: Optional[DimensionsResult] = None
    if resolved_qid:
        best = fetch_wikidata_dimensions(resolved_qid)

    for url in extra_urls:
        if best and best.is_complete():
            break
        candidate = fetch_schema_org_dimensions(url)
        if candidate:
            best = candidate if not best else best.merge_missing(candidate)

    if not (best and best.is_complete()):
        label = (best.name if best else None) or query
        if label:
            wiki = fetch_wikipedia_dimensions(label)
            if wiki:
                best = wiki if not best else best.merge_missing(wiki)

    return best, resolved_qid
