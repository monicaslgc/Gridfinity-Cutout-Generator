from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal


class IdentifyCandidate(BaseModel):
    id: str
    name: str
    confidence: float = Field(ge=0, le=1)


class IdentifyTextRequest(BaseModel):
    input: str = Field(..., min_length=1)


class IdentifyResponse(BaseModel):
    item: str
    candidates: List[IdentifyCandidate]


class Dimensions(BaseModel):
    L: float
    W: float
    H: float


class DimensionsResponse(BaseModel):
    id: str
    name: str
    dims_mm: Dimensions
    source: str
    confidence: float


# Placeholder to avoid Literal forward issues in some tooling
Options = BaseModel.model_construct  # type: ignore[assignment]


class Proposal(BaseModel):
    type: Literal["snug", "easy", "multi"]
    x_slots: int
    y_slots: int
    z_units: int
    clearance: float
    compartments: Optional[int] = None


class ProposalsRequest(BaseModel):
    item_id: str
    dims_mm: Dimensions
    options: Dict[str, bool] = Field(default_factory=dict)


class ProposalsResponse(BaseModel):
    proposals: List[Proposal]


class STLRequest(BaseModel):
    item_id: str
    dims_mm: Dimensions
    proposal: Proposal
    options: Dict[str, bool] = Field(default_factory=dict)
    label: Optional[str] = None


class STLFile(BaseModel):
    type: str
    url: str
    preview_url: Optional[str] = None  # Optional preview PNG URL


class STLFilesResponse(BaseModel):
    files: List[STLFile]