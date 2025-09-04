from __future__ import annotations
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional, List, Dict
from pathlib import Path
import uvicorn

from .models import (
    IdentifyTextRequest,
    IdentifyResponse,
    DimensionsResponse,
    ProposalsRequest,
    ProposalsResponse,
    STLRequest,
    STLFilesResponse,
)
from .services.identification import identify_from_text, identify_from_image
from .services.proposals import generate_proposals
from .services.stl import generate_stl_files

# NEW aggregator that pulls dimensions from Wikidata, manufacturer schema.org, and Wikipedia
from .services.dimensions.fetcher import fetch_dimensions

DATA_DIR = Path("data")
(DATA_DIR / "stl").mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Gridfinity Cutout Generator API", version="0.1.0")

# CORS (why: enable local dev UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/files", StaticFiles(directory=str(DATA_DIR)), name="files")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/identify", response_model=IdentifyResponse)
async def identify_text(req: IdentifyTextRequest) -> IdentifyResponse:
    item = await identify_from_text(req.input)
    return item


@app.post("/identify-image", response_model=IdentifyResponse)
async def identify_image(file: UploadFile = File(...)) -> IdentifyResponse:
    # NOTE(why): separate image route for form-data UX
    content = await file.read()
    item = await identify_from_image(content)
    return item


@app.get("/dimensions", response_model=DimensionsResponse)
async def dimensions(
    id: Optional[str] = None,
    q: Optional[str] = None,
    urls: Optional[str] = None,
) -> DimensionsResponse:
    """Fetch exact dimensions from online sources.

    Supports:
    - `id`: Wikidata QID (e.g., Q12345)
    - `q`: free-text query resolved to a QID via Wikidata search
    - `urls`: comma-separated manufacturer/marketplace URLs to parse schema.org data
    """
    extra_urls: List[str] = []
    if urls:
        extra_urls = [u.strip() for u in urls.split(",") if u.strip()]

    result, resolved_qid = await fetch_dimensions(qid=id, query=q, extra_urls=extra_urls)
    if not result:
        raise HTTPException(status_code=404, detail="Dimensions not found")

    return DimensionsResponse(
        id=resolved_qid or id,
        name=result.name,
        dims_mm=result.dims_mm,
        source=result.source,
        source_url=result.source_url,
        confidence=round(result.confidence, 2),
        evidence=result.evidence,
    )


@app.post("/proposals", response_model=ProposalsResponse)
async def proposals(req: ProposalsRequest) -> ProposalsResponse:
    return generate_proposals(req)


@app.post("/stl", response_model=STLFilesResponse)
async def stl(req: STLRequest) -> STLFilesResponse:
    urls = generate_stl_files(req, output_dir=DATA_DIR / "stl")
    return STLFilesResponse(files=urls)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
