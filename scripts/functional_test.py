"""End-to-end functional test for the running docker compose stack.

Unlike the docker-build CI job's health-check step (which only proves the
backend and frontend containers boot and respond to *some* request), this
walks the actual user-facing pipeline the README promises: identify an
item by name -> look up its real dimensions -> generate container
proposals -> generate a real STL file -> download it and sanity-check the
bytes. That's the feature this whole project exists to provide, and
nothing before this test actually exercised it end-to-end against a live
running stack.

/dimensions only succeeds when the resolved Wikidata item has all three
of P2043 (length), P2049 (width), and P2048 (height) populated - see
backend/app/services/dimensions/wikidata.py. Most everyday consumer
items on Wikidata do NOT have these three specific properties filled in
(this test found that out the hard way against "Rubik's Cube" and
"iPhone 15", which both resolve to a real QID but 404 on /dimensions),
so this tries a list of items chosen because their Wikidata entries are
likely to carry precise physical dimensions (ISO-standardised formats,
well-documented consumer electronics), and uses the first one that
actually resolves to real dimensions rather than hard-coding a single
item that might stop resolving if Wikidata's data changes.

Uses only the standard library (urllib) so it needs no extra pip install
step in CI.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://localhost:8000"

CANDIDATE_ITEMS = [
    "Credit card",
    "A4 paper",
    "US Letter paper",
    "Nintendo Switch",
    "PlayStation 5",
    "iPad",
    "MacBook Air",
    "Xbox Series X",
    "Business card",
    "Playing card",
    "Rubik's Cube",
    "iPhone 15",
    "Nintendo Switch Pro Controller",
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

        # cid isn't always a bare Wikidata QID - identify_from_text can
        # return a synthetic "unresolved:<text>" id when it can't resolve
        # one, which contains spaces/colons and must be URL-encoded or
        # urllib raises InvalidURL outright (found the hard way in the
        # first version of this script).
        encoded_id = urllib.parse.quote(cid, safe="")
        dstatus, dresp = call("GET", f"/dimensions?id={encoded_id}")
        print(f"dimensions(id={cid!r}) -> {dstatus}: {dresp}")
        if dstatus == 200 and dresp.get("dims_mm"):
            dims = dresp["dims_mm"]
            item_id = cid
            item_name = name
            break

    if dims is None:
        fail(
            "no candidate item resolved to real dimensions via /identify + "
            "/dimensions (tried: " + ", ".join(CANDIDATE_ITEMS) + ")"
        )

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
