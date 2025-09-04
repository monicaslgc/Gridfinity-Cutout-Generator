import os
import uuid
import time
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
import cadquery as cq

app = FastAPI()
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

def cleanup_temp_files():
    """Delete files older than 5 minutes in TEMP_DIR."""
    now = time.time()
    for filename in os.listdir(TEMP_DIR):
        path = os.path.join(TEMP_DIR, filename)
        if os.path.isfile(path) and now - os.path.getmtime(path) > 300:
            os.remove(path)

@app.get("/generate")
def generate_container(width: int = Query(42, gt=0), length: int = Query(42, gt=0), height: int = Query(20, gt=0), filetype: str = Query("stl", pattern="^(stl|step)$")):
    """
    Generate a Gridfinity-style box and return a download URL.
    Parameters: width (mm), length (mm), height (mm), filetype ('stl' or 'step')
    """
    cleanup_temp_files()
    token = str(uuid.uuid4())
    ext = "step" if filetype == "step" else "stl"
    file_path = os.path.join(TEMP_DIR, f"{token}.{ext}")

    # Example: a simple parametric box (replace with actual Gridfinity logic)
    result = cq.Workplane("XY").box(width, length, height)
    if ext == "stl":
        cq.exporters.export(result, file_path)
    else:
        cq.exporters.export(result, file_path)

    return {"download_url": f"/download/{token}?filetype={ext}"}

@app.get("/download/{token}")
def download_file(token: str, filetype: str = Query("stl", pattern="^(stl|step)$")):
    file_path = os.path.join(TEMP_DIR, f"{token}.{filetype}")
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found or expired."}, status_code=404)
    if time.time() - os.path.getmtime(file_path) > 300:
        os.remove(file_path)
        return JSONResponse({"error": "File expired."}, status_code=410)
    return FileResponse(file_path, filename=f"gridfinity_container_{token}.{filetype}")
