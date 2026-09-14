from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_identify_known_item():
    res = client.post("/identify", json={"input": "Nintendo Switch Pro Controller"})
    assert res.status_code == 200
    data = res.json()
    assert data["candidates"]
    assert data["candidates"][0]["id"] == "nintendo-switch-pro-controller"


def test_identify_unknown_item_falls_back():
    res = client.post("/identify", json={"input": "some totally unrecognizable object xyz"})
    assert res.status_code == 200
    data = res.json()
    assert data["candidates"]
    assert data["candidates"][0]["id"] == "generic-small-item"


def test_dimensions_known_item():
    res = client.get("/dimensions", params={"id": "nintendo-switch-pro-controller"})
    assert res.status_code == 200
    data = res.json()
    assert data["dims_mm"] == {"L": 152, "W": 106, "H": 60}


def test_dimensions_unknown_item_returns_default():
    res = client.get("/dimensions", params={"id": "not-a-real-id"})
    assert res.status_code == 200
    data = res.json()
    assert "dims_mm" in data


def test_proposals_real_math():
    res = client.post(
        "/proposals",
        json={
            "item_id": "nintendo-switch-pro-controller",
            "dims_mm": {"L": 152, "W": 106, "H": 60},
            "options": {},
        },
    )
    assert res.status_code == 200
    proposals = res.json()["proposals"]
    assert len(proposals) == 3
    assert {p["type"] for p in proposals} == {"snug", "easy", "multi"}
    for p in proposals:
        assert p["x_slots"] >= 1
        assert p["y_slots"] >= 1
        assert p["z_units"] >= 1


def test_stl_generates_a_downloadable_file():
    proposals_res = client.post(
        "/proposals",
        json={
            "item_id": "nintendo-switch-pro-controller",
            "dims_mm": {"L": 152, "W": 106, "H": 60},
            "options": {},
        },
    )
    proposal = proposals_res.json()["proposals"][0]

    stl_res = client.post(
        "/stl",
        json={
            "item_id": "nintendo-switch-pro-controller",
            "dims_mm": {"L": 152, "W": 106, "H": 60},
            "proposal": proposal,
            "options": {"lip": True, "magnets": False, "screws": False},
        },
    )
    assert stl_res.status_code == 200
    files = stl_res.json()["files"]
    assert files
    download_url = files[0]["url"]
    assert download_url.startswith("/download/")

    download_res = client.get(download_url)
    assert download_res.status_code == 200
    assert len(download_res.content) > 0


def test_stl_with_lip_magnets_and_screws_together():
    # This exercises every optional geometry branch at once (chamfer +
    # magnet holes + screw holes) - the highest-risk part of the CAD code,
    # since it wasn't possible to run CadQuery locally before pushing.
    stl_res = client.post(
        "/stl",
        json={
            "item_id": "airpods-pro-case",
            "dims_mm": {"L": 61, "W": 46, "H": 22},
            "proposal": {
                "type": "snug",
                "x_slots": 2,
                "y_slots": 2,
                "z_units": 4,
                "clearance": 0.5,
            },
            "options": {"lip": True, "magnets": True, "screws": True},
        },
    )
    assert stl_res.status_code == 200
    files = stl_res.json()["files"]
    download_res = client.get(files[0]["url"])
    assert download_res.status_code == 200
    assert len(download_res.content) > 0


def test_stl_smallest_possible_bin_does_not_crash():
    # 1x1x1 grid unit is the edge case most likely to make shell()/chamfer()
    # fail (walls could exceed the available space).
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
                "clearance": 0.5,
            },
            "options": {"lip": True, "magnets": True, "screws": True},
        },
    )
    assert stl_res.status_code == 200
