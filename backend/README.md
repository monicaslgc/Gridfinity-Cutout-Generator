# Backend – Gridfinity Cutout Generator

This is the backend service for the Gridfinity Cutout Generator project.  
It provides the API for identifying items, fetching dimensions, generating container proposals, and producing STL/STEP files – all with Gridfinity-compatible parametric models.

---

## Features

- REST API for generating custom Gridfinity containers
- Parametric CAD generation with CadQuery
- Temporary download links for STL/STEP files (auto-expire)
- Ready for integration with the Next.js frontend

---

## Getting Started

### Prerequisites

- Python 3.10+ (recommended: use [`conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/))
- (Optional) Docker & Docker Compose

### Installation

**With Conda:**
```bash
cd backend
conda env create -f environment.yml
conda activate gridfinity
```

**Or with pip:**
```bash
cd backend
pip install -r requirements.txt
```

### Running the Server

```bash
uvicorn main:app --reload
```

- The API will be available at [http://localhost:8000](http://localhost:8000)
- Interactive API docs at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

### `GET /generate`

Generate a parametric container and receive a temporary download link.

**Query Parameters:**
- `width` (mm)
- `length` (mm)
- `height` (mm)
- `filetype` (`stl` or `step`)

**Example:**
```
/generate?width=42&length=42&height=20&filetype=stl
```

**Response:**
```json
{
  "download_url": "/download/1234abcd?filetype=stl"
}
```

### `GET /download/{token}`

Download the generated file by token (valid for 5 minutes after creation).

---

## Development Notes

- Temporary files are stored in `backend/temp_files/`. They are auto-deleted after 5 minutes.
- Replace the sample box-generation in `main.py` with the full Gridfinity container logic as you upgrade the project.
- Add your LLM/image/dimension lookup integration as needed.

---

## Project Structure

```
backend/
  main.py                 # FastAPI app entrypoint
  requirements.txt
  environment.yml
  temp_files/             # (auto-created, ignored by git)
```

---

## See Also

- [Project Overview & Architecture](../README.md)
- [Frontend Setup](../frontend/README.md)

---

## License

MIT
