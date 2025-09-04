from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional




@dataclass
class DimensionsResult:
"""Normalized dimensions payload.


All linear dimensions are millimetres.
Use keys L, W, H when a rectangular prism is implied.
Use DIAMETER for circular objects; T for thickness if only thickness provided.
"""
item_id: Optional[str] = None
name: Optional[str] = None
dims_mm: Dict[str, float] = field(default_factory=dict)
source: str = ""
source_url: Optional[str] = None
confidence: float = 0.0
evidence: List[str] = field(default_factory=list)
raw: Any = None


def merge_missing(self, other: "DimensionsResult") -> "DimensionsResult":
"""Fill missing dims from another result; keep higher confidence & append evidence.
Why: provider fallback should enhance, not overwrite trusted data.
"""
merged = DimensionsResult(
item_id=self.item_id or other.item_id,
name=self.name or other.name,
dims_mm={**other.dims_mm, **self.dims_mm} if self.confidence >= other.confidence else {**self.dims_mm, **other.dims_mm},
source=self.source if self.confidence >= other.confidence else other.source,
source_url=self.source_url if self.confidence >= other.confidence else other.source_url,
confidence=max(self.confidence, other.confidence),
evidence=[*self.evidence, *other.evidence],
raw={"primary": self.raw, "secondary": other.raw},
)
return merged
