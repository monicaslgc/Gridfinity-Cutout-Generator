from fastapi import FastAPI
from .routers import identify, dimensions, proposals, stl

app = FastAPI(title="Gridfinity Cutout Generator")

app.include_router(identify.router, prefix="/identify", tags=["identify"])
app.include_router(dimensions.router, prefix="/dimensions", tags=["dimensions"])
app.include_router(proposals.router, prefix="/proposals", tags=["proposals"])
app.include_router(stl.router, prefix="/stl", tags=["stl"])
