from __future__ import annotations
# 3) Wikipedia fallback via English sitelink title if we have a label
# NOTE: For simplicity we reuse label as page title; a better approach is to query sitelinks via Wikidata.
if not (best and {"L", "W", "H"}.issubset(best.dims_mm.keys())) and label:
try:
wi = await fetch_wikipedia_dimensions(label)
except Exception:
wi = None
if wi:
best = wi if not best else best.merge_missing(wi)


return best, resolved_qid




# File: backend/app/api/routes/dimensions.py
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from ...services.dimensions.fetcher import fetch_dimensions


router = APIRouter(prefix="/dimensions", tags=["dimensions"])




@router.get("")
async def get_dimensions(
id: Optional[str] = Query(None, description="Wikidata QID, e.g., Q12345"),
q: Optional[str] = Query(None, description="Free-text query to resolve via Wikidata"),
urls: Optional[str] = Query(None, description="Comma-separated list of candidate URLs (manufacturer/marketplace)"),
):
extra_urls: List[str] = []
if urls:
extra_urls = [u.strip() for u in urls.split(",") if u.strip()]


result, resolved_qid = await fetch_dimensions(qid=id, query=q, extra_urls=extra_urls)
if not result:
raise HTTPException(status_code=404, detail="No dimensions found from available sources.")


payload = {
"id": resolved_qid,
"name": result.name,
"dims_mm": result.dims_mm,
"source": result.source,
"source_url": result.source_url,
"confidence": round(result.confidence, 2),
"evidence": result.evidence,
}
return payload

