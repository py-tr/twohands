"""Check one audit receipt without the app: recompute the leaf from its record, check the crop's hash (when the crop
is given), and walk the proof path to the root.

    python -m twohands.verify_receipt receipt.json [--crop crop.jpg] [--root <hex>]

receipt.json is what /audit/<id>/receipt/<key> returns. --root checks the root against one you hold from elsewhere
(the printed report, results/sample_audit_root.txt). Exit 0 when every check passes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from twohands import merkle


def check(receipt: dict, crop: bytes | None = None, root: str | None = None) -> list[tuple[str, bool, str]]:
    rec = receipt["leaf"]
    out = []
    leaf = merkle.leaf_hash(rec)
    out.append(("leaf recomputed from the record", leaf == receipt.get("leaf_hash"), leaf))
    if crop is not None:
        h = hashlib.sha256(crop).hexdigest()
        out.append(("crop SHA-256 matches the record", h == rec.get("crop_sha256"), h))
    top = merkle.walk(leaf, receipt["proof"])
    out.append((f"path of {len(receipt['proof'])} steps reaches the receipt's root", top == receipt["root"], top))
    if root is not None:
        out.append(("receipt's root matches the root given", receipt["root"] == root.strip().lower(), receipt["root"]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m twohands.verify_receipt", description=__doc__.split("\n\n")[0])
    ap.add_argument("receipt")
    ap.add_argument("--crop", help="the crop image (JPEG) the receipt's record hashes")
    ap.add_argument("--root", help="a root you hold from elsewhere, to compare with the receipt's")
    a = ap.parse_args(argv)
    try:
        receipt = json.loads(Path(a.receipt).read_text(encoding="utf-8"))
        res = check(receipt, Path(a.crop).read_bytes() if a.crop else None, a.root)
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"FAIL  could not read the receipt: {e}")
        return 1
    rec = receipt["leaf"]
    print(f"form {rec['form']} field {rec['field']}: keyed {rec['keyed']}, model {rec['model']}, tier {rec['tier']}")
    for label, ok, h in res:
        print(f"{'ok  ' if ok else 'FAIL'}  {label}  {h[:16]}")
    ok = all(r[1] for r in res)
    print(f"{'VERIFIED' if ok else 'NOT VERIFIED'}  root {receipt['root']}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
