from __future__ import annotations
import json
import re
from typing import Any, Dict, List, Optional

import requests

from ..types import DimensionsResult
from ..units import to_mm

HEADERS = {
    "User-Agent": "GridfinityCutoutGenerator/0.1 (https://github.com/monicaslgc/Gridfinity-Cutout-Generator)"
}

_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def extract_json_ld_blocks(html: str) -> List[Dict[str, Any]]:
    """Pull every <script type="application/ld+json"> block out of `html`
    and parse it as JSON. Malformed blocks are skipped rather than raising,
    since real-world pages often ship slightly invalid JSON-LD.
    """
    blocks: List[Dict[str, Any]] = []
    for raw in _JSONLD_RE.findall(html):
        try:
            parsed = json.loads(raw.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, list):
            blocks.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            graph = parsed.get("@graph")
            if isinstance(graph, list):
                blocks.extend(item for item in graph if isinstance(item, dict))
            else:
                blocks.append(parsed)
    return blocks


def find_product_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter JSON-LD blocks down to ones that look like schema.org Product."""
    products = []
    for block in blocks:
        block_type = block.get("@type")
        types = block_type if isinstance(block_type, list) else [block_type]
        if any(isinstance(t, str) and t.lower() == "product" for t in types):
            products.append(block)
    return products


def _quantitative_value_to_mm(value: Any) -> Optional[float]:
    """schema.org QuantitativeValue can appear as {"value": n, "unitCode": ..}
    or as a bare number/string (assumed millimetres)."""
    if isinstance(value, dict):
        amount = value.get("value")
        unit = value.get("unitCode") or value.get("unitText")
        if amount is None:
            return None
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return None
        return to_mm(amount, unit)
    if isinstance(value, (int, float, str)):
        try:
            return to_mm(float(value), "mm")
        except (TypeError, ValueError):
            return None
    return None


def fetch_schema_org_dimensions(url: str) -> Optional[DimensionsResult]:
    """Fetch `url` and look for schema.org Product JSON-LD with
    depth/width/height fields, to pull real manufacturer-published
    dimensions off a product page.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception:
        return None

    products = find_product_blocks(extract_json_ld_blocks(html))
    if not products:
        return None

    product = products[0]
    dims: Dict[str, float] = {}

    length_mm = _quantitative_value_to_mm(product.get("depth") or product.get("length"))
    width_mm = _quantitative_value_to_mm(product.get("width"))
    height_mm = _quantitative_value_to_mm(product.get("height"))
    if length_mm is not None:
        dims["L"] = length_mm
    if width_mm is not None:
        dims["W"] = width_mm
    if height_mm is not None:
        dims["H"] = height_mm
    if not dims:
        return None

    return DimensionsResult(
        name=product.get("name") or url,
        dims_mm=dims,
        source="schema.org Product markup",
        source_url=url,
        confidence=0.85 if len(dims) == 3 else 0.5,
        evidence=[f"schema.org Product JSON-LD on {url}"],
        raw=product,
    )
