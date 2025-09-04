# Gridfinity Cutout Generator (LLM + CAD)

This project is an automatic generator of Gridfinity containers with custom cutouts for specific items.  
Users can describe an object (or upload a photo), and the system:

1. Identifies the item via an LLM (multimodal text + image).  
2. Fetches exact dimensions from online sources (manufacturer, Wikidata, marketplaces).  
3. Generates three container proposals:  
   - **Snug Fit** – tight fit, minimal clearance  
   - **Easy Grab** – looser fit with finger cutouts for quick access  
   - **Multi-purpose** – divided compartments for the item and accessories  
4. Outputs STL files ready for 3D printing.


![backend](https://github.commonicaslgc/Gridfinity-Cutout-Generator/actions/workflows/backend.yml/badge.svg)
![frontend](https://github.commonicaslgc/Gridfinity-Cutout-Generator/actions/workflows/frontend.yml/badge.svg)

---

## Key Features
- Fully Gridfinity compatible (X/Y multiples of 42 mm, Z multiples of 7 mm)  
- Optional stacking lip, magnet holes (Ø6 × 2 mm), and screw holes (M3)  
- Automatic cutout generation with FDM-appropriate tolerances  
- Web interface for input (text/image) and STL preview  
- Backend powered by FastAPI, CadQuery, and an LLM toolchain

---

## Architecture
| Component      | Description |
|----------------|-------------|
| Frontend       | Next.js + React + Tailwind CSS + three.js STL viewer |
| Backend        | FastAPI (Python) |
| LLM Tools      | Entity linking, web dimension lookup, image-based scale estimation |
| CAD Engine     | CadQuery (or build123d) with Gridfinity parametric models |
| Storage        | S3-compatible bucket for STL files and thumbnails |
| Deployment     | Docker Compose (frontend + backend) + CDN for FAST static delivery |

---

## Getting Started

### Prerequisites
- Docker & Docker Compose  
- Python 3.10+ (for backend development without Docker)  
- Node.js 18+ (for frontend development)

### Running with Docker
```bash
git clone https://github.com/<your-org>/<your-repo>.git
cd <your-repo>
docker compose up --build
```

- Backend: `http://localhost:8000`  
- Frontend: `http://localhost:3000`

### Local Development
**Backend only**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend only**
```bash
cd frontend
npm install
npm run dev
```

---

## API Reference

The backend includes automatic API documentation via Swagger UI and ReDoc:
- Swagger UI: `http://localhost:8000/docs`  
- ReDoc: `http://localhost:8000/redoc`

### POST /identify
Identifies an item from a text string or image upload.

**Request (text)**
```json
{ "input": "Nintendo Switch Pro Controller" }
```

**Request (image)**
Includes a file in `multipart/form-data`:  
`file=@photo.jpg`

**Response**
```json
{
  "item": "Nintendo Switch Pro Controller",
  "candidates": [
    {
      "id": "Q123456",
      "name": "Nintendo Switch Pro Controller",
      "confidence": 0.94
    }
  ]
}
```

### GET /dimensions
Fetches dimensions (length × width × height) for a known item.

**Request**
```
GET /dimensions?id=Q123456
```

**Response**
```json
{
  "id": "Q123456",
  "name": "Nintendo Switch Pro Controller",
  "dims_mm": { "L": 152, "W": 106, "H": 60 },
  "source": "Nintendo official site",
  "confidence": 0.91
}
```

### POST /proposals
Generates three container proposals based on the item’s dimensions and options.

**Request**
```json
{
  "item_id": "Q123456",
  "dims_mm": { "L": 152, "W": 106, "H": 60 },
  "options": { "lip": true, "magnets": true, "screws": false }
}
```

**Response**
```json
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
Generates STL files corresponding to a selected container proposal.

**Request**
```json
{
  "proposal_id": "easy",
  "format": "stl"
}
```

**Response**
```json
{
  "files": [
    {
      "type": "snug",
      "url": "https://cdn.example.com/stl/snug.stl"
    },
    {
      "type": "easy",
      "url": "https://cdn.example.com/stl/easy.stl"
    },
    {
      "type": "multi",
      "url": "https://cdn.example.com/stl/multi.stl"
    }
  ]
}
```

---

## Project Structure
```
/frontend      → Next.js app (UI + STL preview)
/backend       → FastAPI app (LLM + CAD + API)
/cad           → CadQuery scripts for Gridfinity bins
/docs          → Documentation and diagrams
```

---

## Development Roadmap
- [ ] MVP: Text-based item lookup and STL generation  
- [ ] Image-based item recognition with scale reference  
- [ ] User customization (wall thickness, lip, labels, etc.)  
- [ ] Design gallery and shareable links  
- [ ] Cloud deployment + CDN hosting of generated STL files

---

## Contributing
1. Fork the repository and create a feature branch  
2. Make commits with clear messages  
3. Open a Pull Request

Feel free to raise issues or request features via GitHub Issues.

---

## License
MIT License — free to use, modify, and contribute
