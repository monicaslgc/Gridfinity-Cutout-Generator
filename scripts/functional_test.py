"""End-to-end functional test for the running docker compose stack.

Unlike the docker-build CI job's health-check step (which only proves the
backend and frontend containers boot and respond to *some* request), this
walks the actual user-facing pipeline the README promises: identify an
item by name -> look up its real dimensions -> generate container
proposals -> generate a real STL file -> download it and sanity-check the
bytes. That's the feature this whole project exists to provide, and
nothing before this test actually exercised it end-to-end against a live
running stack.

/dimensions depends on real external lookups (Wikidata, manufacturer
schema.org, Wikipedia), so not every item name will resolve - this tries
a short list of common, well-documented objects and uses the first one
that resolves to real dimensions, rather than hard-coding a single item
that might stop resolving if its Wikidata entry changes.

Uses only the standard library (urllib) so it needs no extra pip install
step in CI.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"

# Ordinary, well-known objects likely to have a Wikidata entry with
# physical dimensions (height/width/length/diameter properties).
CANDIDATE_ITEMS = [
    "Rubik's Cube",
    "iPhone 15",
    "Zippo lighter",
    "Nintendo Switch",
    "Post-it Note",
    "AA battery",
    "Golf ball",
    "Hydro Flask water bottle",
    "Nintendo Switch Pro Controller",
    "Tennis ball",
]


def call(method: str, path: str, body: dict | None = None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def fail(msg: str) -> None:
    print(f"FUNCTIONAL TEST FAILED: {msg}")
    sys.exit(1)


def main() -> None:
    dims = None
    item_id = None
    item_name = None

    for name in CANDIDATE_ITEMS:
        status, resp = call("POST", "/identify", {"input": name})
        print(f"identify({name!r}) -> {status}: {resp}")
        if status != 200 or not resp.get("candidates"):
            continue
        cid = resp["candidates"][0]["id"]

        dstatus, dresp = call("GET", f"/dimensions?id={cid}")
        print(f"dimensions(id={cid}) -> {dstatus}: {dresp}")
        if dstatus == 200 and dresp.get("dims_mm"):
            dims = dresp["dims_mm"]
            item_id = cid
            item_name = name
            break

    if dims is None:
        fail("no candidate item resolved to real dimensions via /identify + /dimensions")

    print(f"\nResolved {item_name!r} -> id={item_id}, dims_mm={dims}\n")

    pstatus, presp = call(
        "POST",
        "/proposals",
        {
            "item_id": item_id,
            "dims_mm": dims,
            "options": {"lip": True, "magnets": False, "screws": False},
        },
    )
    print(f"proposals -> {pstatus}: {presp}")
    if pstatus != 200 or not presp.get("proposals"):
        fail("/proposals did not return any proposals")

    proposal = presp["proposals"][0]

    sstatus, sresp = call(
        "POST",
        "/stl",
        {
            "item_id": item_id,
            "dims_mm": dims,
            "proposal": proposal,
            "options": {"lip": True, "magnets": False, "screws": False},
            "label": item_name,
        },
    )
    print(f"stl -> {sstatus}: {sresp}")
    if sstatus != 200 or not sresp.get("files"):
        fail("/stl did not return any files")

    file_url = sresp["files"][0]["url"]
    if file_url.startswith("/"):
        file_url = BASE + file_url

    print(f"downloading {file_url}")
    with urllib.request.urlopen(file_url, timeout=30) as r:
        content = r.read()
    print(f"downloaded {len(content)} bytes")

    if len(content) < 500:
        fail(f"downloaded STL is suspiciously small ({len(content)} bytes)")

    print(
        "\nFUNCTIONAL TEST PASSED: "
        f"item={item_name!r} proposal_type={proposal['type']} "
        f"stl_bytes={len(content)}"
    )


if __name__ == "__main__":
    main()
