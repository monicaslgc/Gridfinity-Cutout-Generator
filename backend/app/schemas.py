from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class IdentifyTextRequest(BaseModel):
    input: str = Field(..., description="Item description")

class IdentifyImageResponseCandidate(BaseModel):
    id: str
    name: str
    confidence: float

class IdentifyResponse(BaseModel):
    item: str
    candidates: List[IdentifyImageResponseCandidate]

class Dims(BaseModel):
    L: float
    W: float
    H: float

class DimensionsResponse(BaseModel):
    id: str
    name: str
    dims_mm: Dims
    source: str
    confidence: float

class Proposal(BaseModel):
    type: Literal["snug", "easy", "multi"]
    x_slots: int
    y_slots: int
    z_units: int
    clearance: Optional[float] = None
    compartments: Optional[int] = None

class ProposalsRequest(BaseModel):
    item_id: str
    dims_mm: Dims
    options: dict = {}

class ProposalsResponse(BaseModel):
    proposals: List[Proposal]

class STLRequest(BaseModel):
    proposal_id: str
    format: Literal["stl"] = "stl"

class STLFile(BaseModel):
    type: str
    url: str

class STLResponse(BaseModel):
    files: List[STLFile]
