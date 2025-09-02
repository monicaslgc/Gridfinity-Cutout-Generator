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
