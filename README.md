# Gridfinity Cutout Generator (LLM + CAD)

This project is an automatic generator of Gridfinity containers with custom cutouts for specific items.  
Users can describe an object (or upload a photo), and the system:

1. Identifies the item via an LLM (multimodal text + image).  
2. Fetches exact dimensions from online sources (manufacturer, Wikidata, marketplaces).  
3. Generates three container proposals:  
   - Snug Fit – tight fit, minimal clearance  
   - Easy Grab – looser fit with finger cutouts for quick access  
   - Multi-purpose – divided compartments for the item and accessories  
4. Outputs STL files ready for 3D printing.  

---

## Key Features
- Fully Gridfinity compatible (X/Y multiples of 42 mm, Z multiples of 7 mm).  
- Optional stacking lip, magnet holes (Ø6×2 mm), and screw holes (M3).  
- Automatic cutout generation with correct tolerances for FDM printing.  
- Web interface for uploading text/image and previewing STL proposals.  
- Backend powered by FastAPI, CadQuery, and an LLM toolchain.  

---

## Architecture
- Frontend: Next.js + React + Tailwind + three.js STL viewer  
- Backend: FastAPI (Python)  
- LLM Tools: Entity linking, web dimension lookup, image-based scale estimation  
- CAD Engine: CadQuery (or build123d) parametric Gridfinity models  
- Storage: S3-compatible bucket for STL files and thumbnails  
- Deployment: Docker Compose (frontend + backend), CDN for static delivery  

---

## Getting Started

### Prerequisites
- Docker & Docker Compose installed  
- Python 3.10+ (for local development without Docker)  
- Node.js 18+ (for frontend development)

### Running with Docker
```bash
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>
docker compose up --build
``` 

Backend: http://localhost:8000

Frontend: http://localhost:3000

### Local Development

Backend only:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
``` 

Frontend only:
```bash
cd frontend
npm install
npm run dev
```

### API Reference

The backend exposes a REST API. It also provides Swagger UI at http://localhost:8000/docs and ReDoc at http://localhost:8000/redoc.

### POST /identify

Identify an item from text or image.

Request (text):
```bash
{ "input": "Nintendo Switch Pro Controller" }
```

Request (image):
```bash
multipart/form-data with field file=@photo.jpg
```

Response:
```bash
{
  "item": "Nintendo Switch Pro Controller",
  "candidates": [
    { "id": "Q123456", "name": "Nintendo Switch Pro Controller", "confidence": 0.94 }
  ]
}
```

###  GET /dimensions

Fetch dimensions (length × width × height) of a known item.

Request:
```bash
GET /dimensions?id=Q123456
```

Response:
```bash
{
  "id": "Q123456",
  "name": "Nintendo Switch Pro Controller",
  "dims_mm": { "L": 152, "W": 106, "H": 60 },
  "source": "Nintendo official site",
  "confidence": 0.91
}
```
### POST /proposals

Generate three design proposals for the identified item.

Request:
```bash
{
  "item_id": "Q123456",
  "dims_mm": { "L": 152, "W": 106, "H": 60 },
  "options": { "lip": true, "magnets": true, "screws": false }
}
```

Response:
```bash
{
  "proposals": [
    {
      "type": "snug",
      "x_slots": 2,
      "y_slots": 2,
      "z_units": 4,
      "clearance": 0.3
    },
    {
      "type": "easy",
      "x_slots": 2,
      "y_slots": 2,
      "z_units": 4,
      "clearance": 0.8
    },
    {
      "type": "multi",
      "x_slots": 3,
      "y_slots": 2,
      "z_units": 4,
      "compartments": 2
    }
  ]
}
```
### POST /stl

Generate STL files for the proposals.

Request:
```bash
{
  "proposal_id": "easy",
  "format": "stl"
}
```

Response:
```bash
{
  "files": [
    { "type": "snug", "url": "https://cdn.example.com/stl/snug.stl" },
    { "type": "easy", "url": "https://cdn.example.com/stl/easy.stl" },
    { "type": "multi", "url": "https://cdn.example.com/stl/multi.stl" }
  ]
}
```
### Project Structure

/frontend      → Next.js app (UI + STL preview)
/backend       → FastAPI app (LLM + CAD + API)
/cad           → CadQuery scripts for Gridfinity bins
/docs          → Documentation and diagrams

### Development Roadmap

- MVP: Text-based item lookup → 3 STL proposals
- Image-based item recognition with scale reference
- User parameter overrides (wall thickness, lip, labels, etc.)
- Shared links and design gallery
- Cloud deployment and CDN distribution of STLs

### Contributing

1. Fork the repo and create your feature branch.
2. Commit your changes with clear messages.
3. Submit a pull request.

Issues and feature requests are welcome in the GitHub Issues section.

### License
MIT License – free to use, modify, and contribute.
