"""Generate real Gridfinity container STLs for a given item's real-world
dimensions, using the actual generate_proposals + generate_stl_files
pipeline - the same code the /proposals and /stl API endpoints call.

This exists to let anyone (no server, no frontend, just this repo's own
CI) produce a real, downloadable set of STL files for a real product
without running the full stack. Also doubles as end-to-end proof that the
pipeline works for arbitrary real dimensions, not just the values baked
into the test suite.

Usage:
    python -m scripts.generate_demo_container \\
        --item-id B0DJFH3NLS --name "Belkin BoostCharge 10000mAh" \\
        --l 100.7 --w 64 --h 24 --out demo_output
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from app.models import Dimensions, ProposalsRequest, STLRequest
from app.services.proposals import generate_proposals
from app.services.stl import generate_stl_files


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--item-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--l", type=float, required=True, help="length (longest horizontal dim), mm")
    p.add_argument("--w", type=float, required=True, help="width, mm")
    p.add_argument("--h", type=float, required=True, help="height, mm")
    p.add_argument("--out", default="demo_output")
    args = p.parse_args()

    dims = Dimensions(L=args.l, W=args.w, H=args.h)
    proposals_res = generate_proposals(
        ProposalsRequest(item_id=args.item_id, dims_mm=dims, options={})
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for proposal in proposals_res.proposals:
        stl_req = STLRequest(
            item_id=args.item_id,
            dims_mm=dims,
            proposal=proposal,
            options={"lip": True, "magnets": True, "screws": True},
            label=args.name,
        )
        files = generate_stl_files(stl_req, output_dir=out_dir)
        for f in files:
            fp = out_dir / Path(f.url).name
            summary.append(
                {
                    "type": proposal.type,
                    "grid_slots": f"{proposal.x_slots}x{proposal.y_slots}x{proposal.z_units}",
                    "compartments": proposal.compartments,
                    "file": str(fp),
                    "size_bytes": fp.stat().st_size if fp.exists() else None,
                }
            )

    print(
        json.dumps(
            {
                "item": args.name,
                "item_id": args.item_id,
                "dims_mm": {"L": args.l, "W": args.w, "H": args.h},
                "proposals": summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
