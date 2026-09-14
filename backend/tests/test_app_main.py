"""End-to-end tests for app.main - the real (previously import-broken)
Wikidata/schema.org/Wikipedia-backed backend, as opposed to the separate
mocked-catalog backend in backend/main.py covered by test_api.py.

Network-touching pieces (Wikidata search, dimension lookup) are mocked;
/proposals and /stl run for real, including real CadQuery generation - the
same kind of check that caught the sealed-lid and dead-cutBlind() bugs in
the old app/services/stl.py.
"""
from __future__ import annotations
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.dimensions.types import DimensionsResult

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_identify_resolves_to_real_qid_when_found():
    with patch("app.services.identification.search_wikidata_qid", return_value="Q19842071"):
        res = client.post("/identify", json={"input": "Nintendo Switch Pro Controller"})
    assert res.status_code == 200
    data = res.json()
    assert data["candidates"][0]["id"] == "Q19842071"


def test_identify_falls_back_when_no_wikidata_match():
    with patch("app.services.identification.search_wikidata_qid", return_value=None):
        res = client.post("/identify", json={"input": "some made up gadget xyz"})
    assert res.status_code == 200
    data = res.json()
    assert data["candidates"][0]["id"].startswith("unresolved:")


def test_identify_image_placeholder():
    res = client.post(
        "/identify-image",
        files={"file": ("photo.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["candidates"][0]["id"] == "unresolved:unknown"


def test_dimensions_returns_404_when_nothing_found():
    with patch("app.main.fetch_dimensions", new=AsyncMock(return_value=(None, "Q1"))):
        res = client.get("/dimensions", params={"id": "Q1"})
    assert res.status_code == 404


def test_dimensions_returns_result_when_found():
    result = DimensionsResult(
        name="Nintendo Switch Pro Controller",
        dims_mm={"L": 152, "W": 106, "H": 60},
        source="Wikidata",
        source_url="https://www.wikidata.org/wiki/Q19842071",
        confidence=0.9,
        evidence=["test"],
    )
    with patch("app.main.fetch_dimensions", new=AsyncMock(return_value=(result, "Q19842071"))):
        res = client.get("/dimensions", params={"id": "Q19842071"})
    assert res.status_code == 200
    data = res.json()
    assert data["dims_mm"] == {"L": 152, "W": 106, "H": 60}
    assert data["source_url"] == "https://www.wikidata.org/wiki/Q19842071"
    assert data["evidence"] == ["test"]


def test_full_flow_proposals_and_stl_with_real_cadquery():
    proposals_res = client.post(
        "/proposals",
        json={
            "item_id": "Q19842071",
            "dims_mm": {"L": 152, "W": 106, "H": 60},
            "options": {},
        },
    )
    assert proposals_res.status_code == 200
    proposal = proposals_res.json()["proposals"][0]

    stl_res = client.post(
        "/stl",
        json={
            "item_id": "Q19842071",
            "dims_mm": {"L": 152, "W": 106, "H": 60},
            "proposal": proposal,
            "options": {"lip": True, "magnets": True, "screws": True},
            "label": "Nintendo Switch Pro Controller",
        },
    )
    assert stl_res.status_code == 200
    files = stl_res.json()["files"]
    assert files
    download_res = client.get(files[0]["url"])
    assert download_res.status_code == 200
    assert len(download_res.content) > 0


def test_stl_smallest_possible_bin_does_not_crash():
    stl_res = client.post(
        "/stl",
        json={
            "item_id": "manual",
            "dims_mm": {"L": 10, "W": 10, "H": 5},
            "proposal": {
                "type": "snug",
                "x_slots": 1,
                "y_slots": 1,
                "z_units": 1,
                "clearance": 0.3,
            },
            "options": {"lip": True, "magnets": True, "screws": True},
        },
    )
    assert stl_res.status_code == 200
