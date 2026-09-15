# Backend – Gridfinity Cutout Generator

This is the backend service for the Gridfinity Cutout Generator project. It
provides the API for identifying items, fetching dimensions, generating
container proposals, and producing STL files – all with Gridfinity-compatible
parametric models built with CadQuery.

There are two backend entrypoints in this folder:

- **`app/main.py`** – the real backend. `/identify` resolves an item to a
  Wikidata QID, `/dimensions` pulls real measurements from Wikidata,
  manufacturer schema.org product markup, and Wikipedia (merging whichever
  sources have data). This is what Docker Compose and the Dockerfile run.
- **`main.py`** – a small mock-catalog backend. `/identify` and `/dimensions`
  do keyword matching against a short local list instead of a real lookup.
  Useful for local frontend development without hitting external APIs.

Both share the same `/proposals` and `/stl` behavior: real Gridfinity slot
math and real CadQuery-generated STL files, including the stacking lip,
magnet/screw holes, an "Easy Grab" finger scoop, and "Multi-purpose"
compartment dividers.

---

## Getting Started

### Prerequisites

- Python 3.10+
- (Optional) Docker & Docker Compose

### Installation

```bash
cd backend
pip install -r requirements.txt
```

### Running the Server

```bash
# Real backend (Wikidata/schema.org/Wikipedia lookup)
uvicorn app.main:app --reload

# or, the mock-catalog backend
uvicorn main:app --reload
```

- The API will be available at [http://localhost:8000](http://localhost:8000)
- Interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

- `GET /health`
- `POST /identify` – identify an item from text (or `POST /identify-image` from a photo; still a placeholder in `app.main`)
- `GET /dimensions` – fetch `L`/`W`/`H` in mm for an item
- `POST /proposals` – generate Snug/Easy Grab/Multi-purpose bin proposals for a set of dimensions
- `POST /stl` – generate an STL file for a chosen proposal

See the top-level [README](../README.md) for full request/response examples.

---

## Tests

```bash
cd backend
pip install -r requirements.txt pytest httpx
pytest -v
```

`tests/test_api.py` covers the mock backend, `tests/test_app_main.py` and
`tests/test_dimensions_package.py` cover the real backend end to end
(network calls mocked), and `tests/test_stl_geometry.py` covers the STL
geometry differences between proposal types.

---

## See Also

- [Project Overview & Architecture](../README.md)
- [Frontend Setup](../frontend/README.md)

---

## License

MIT
