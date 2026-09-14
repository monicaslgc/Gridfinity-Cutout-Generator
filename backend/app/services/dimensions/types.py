from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DimensionsResult:
    """Normalized dimensions payload.

    All linear dimensions are millimetres. Use keys L, W, H when a
    rectangular prism is implied.
    """

    item_id: Optional[str] = None
    name: Optional[str] = None
    dims_mm: Dict[str, float] = field(default_factory=dict)
    source: str = ""
    source_url: Optional[str] = None
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    raw: Any = None

    def is_complete(self) -> bool:
        return {"L", "W", "H"}.issubset(self.dims_mm.keys())

    def merge_missing(self, other: "DimensionsResult") -> "DimensionsResult":
        """Combine this result with a lower-priority fallback result.

        Why: provider fallback should enhance, not overwrite trusted data -
        the higher-confidence side wins on any key both sides have, but
        either side can fill in dims the other is missing.
        """
        if self.confidence >= other.confidence:
            primary, secondary = self, other
        else:
            primary, secondary = other, self

        return DimensionsResult(
            item_id=primary.item_id or secondary.item_id,
            name=primary.name or secondary.name,
            dims_mm={**secondary.dims_mm, **primary.dims_mm},
            source=primary.source,
            source_url=primary.source_url or secondary.source_url,
            confidence=max(self.confidence, other.confidence),
            evidence=[*self.evidence, *other.evidence],
            raw={"primary": primary.raw, "secondary": secondary.raw},
        )
