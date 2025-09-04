from __future__ import annotations
from typing import Optional
import httpx
import re
from ..types import DimensionsResult
from ..parse import normalize_dims_from_text


_HEADERS = {"User-Agent": "GridfinityCutoutBot/1.0 (+dimensions)"}


_DIM_ROW_RE = re.compile(r"<tr>\s*<th[^>]*>\s*Dimensions\s*</th>\s*<td[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)


async def fetch_wikipedia_dimensions(page_title: str) -> Optional[DimensionsResult]:
# English Wikipedia only for now
url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
async with httpx.AsyncClient(headers=_HEADERS, timeout=15) as client:
r = await client.get(url)
if r.status_code != 200:
return None
html = r.text
m = _DIM_ROW_RE.search(html)
if not m:
return None
cell = re.sub(r"<[^>]+>", " ", m.group(1))
cell = re.sub(r"\s+", " ", cell).strip()
parsed = normalize_dims_from_text(cell)
if not parsed:
return None
return DimensionsResult(
dims_mm=parsed,
source="Wikipedia infobox",
source_url=url,
confidence=0.6,
evidence=[f"Infobox cell: {cell}"],
raw=cell,
)

