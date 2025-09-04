from __future__ import annotations
dims[out_key] = mm


# size as QuantitativeValue or string
size = product.get("size")
if size:
if isinstance(size, dict):
mm = qv_to_mm(size)
if mm is not None:
dims.setdefault("L", mm)
elif isinstance(size, str):
parsed = normalize_dims_from_text(size)
if parsed:
dims = {**parsed, **dims}


# additionalProperty entries sometimes contain dimensions
add_props = product.get("additionalProperty") or []
if isinstance(add_props, dict):
add_props = [add_props]
for ap in add_props:
name = (ap.get("name") or "").lower()
val = ap.get("value")
if not val:
continue
parsed = normalize_dims_from_text(str(val))
if parsed:
dims = {**parsed, **dims}


return dims




async def fetch_schema_org(url: str) -> Optional[DimensionsResult]:
if extruct is None:
return None
async with httpx.AsyncClient(headers=_HEADERS, timeout=20, follow_redirects=True) as client:
r = await client.get(url)
r.raise_for_status()
html = r.text
data = extruct.extract(html, syntaxes=["json-ld", "microdata", "rdfa"]) # type: ignore


candidates: List[Dict[str, Any]] = []
for blob in data.get("json-ld", []):
# normalize to dict
if isinstance(blob, dict):
types = blob.get("@type")
if types == "Product" or (isinstance(types, list) and "Product" in types):
candidates.append(blob)
elif isinstance(blob, list):
for b in blob:
if isinstance(b, dict):
types = b.get("@type")
if types == "Product" or (isinstance(types, list) and "Product" in types):
candidates.append(b)


dims: Dict[str, float] = {}
for prod in candidates:
extracted = _extract_from_product(prod)
dims.update(extracted)


if not dims:
return None


return DimensionsResult(
dims_mm=dims,
source="schema.org",
source_url=url,
confidence=0.9 if url else 0.85, # manufacturer pages typically high
evidence=[f"schema.org Product fields from {url}"],
raw=data,
)

