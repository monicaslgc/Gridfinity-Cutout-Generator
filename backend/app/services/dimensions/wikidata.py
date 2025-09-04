from __future__ import annotations
rows = data.get("results", {}).get("bindings", [])
if not rows:
return None


dims: Dict[str, float] = {}
refs_total = 0
official = None
label = None
for b in rows:
prop = b["prop"]["value"]
amt = float(b["amount"]["value"]) # raw unit
unit_uri = b.get("unit", {}).get("value")
mm = to_mm(amt, unit_uri)
if mm is None:
continue
if prop == "height":
dims["H"] = mm
elif prop == "width":
dims["W"] = mm
elif prop in ("length", "depth"):
# Prefer length over depth if both appear; keep first occurrence
dims.setdefault("L", mm)
elif prop == "thickness":
dims["T"] = mm
elif prop == "diameter":
dims["DIAMETER"] = mm
refs = int(b.get("refs", {}).get("value", "0")) if b.get("refs") else 0
refs_total += refs
if b.get("official"):
official = b["official"]["value"]
if b.get("label"):
label = b["label"]["value"]


if not dims:
return None


base_conf = 0.8 # Wikidata baseline
if refs_total > 0:
base_conf += 0.1
return DimensionsResult(
item_id=qid,
name=label,
dims_mm=dims,
source="Wikidata",
source_url=f"https://www.wikidata.org/wiki/{qid}",
confidence=min(base_conf, 0.95),
evidence=[f"SPARQL rows={len(rows)} refs_total={refs_total}"],
raw=rows,
), official
