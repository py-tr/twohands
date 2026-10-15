"""Merkle receipts for an audit report: one leaf per disputed field, one root per report.

    leaf      = SHA-256(0x00 || canonical JSON of the leaf record)
    node      = SHA-256(0x01 || left || right)
    odd node  = carried up unchanged to the next level (never paired with itself)
    no leaves = SHA-256 of the empty string

The leaf record is {"form", "field", "keyed", "model", "words", "tier", "crop_sha256"}: the form id, the field code,
the keyed value as listed, the model's digits and words, the evidence tier, and the SHA-256 of the crop image bytes
(null when the field has no crop). Canonical JSON: sorted keys, no spaces, UTF-8. The 0x00 / 0x01 prefixes keep a
leaf from ever being read as a node. Standard library only, so a receipt can be checked without the app
(``python -m twohands.verify_receipt``).
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable, Optional

LEAF_KEYS = ("form", "field", "keyed", "model", "words", "tier", "crop_sha256")


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def leaf_record(form: str, field: str, keyed, model, words, tier: str, crop_sha256: Optional[str]) -> dict:
    return {"form": form, "field": field, "keyed": keyed, "model": model, "words": words, "tier": tier,
            "crop_sha256": crop_sha256}


def leaf_hash(record: dict) -> str:
    if set(record) != set(LEAF_KEYS):
        raise ValueError(f"a leaf record has exactly the keys {', '.join(LEAF_KEYS)}")
    return hashlib.sha256(b"\x00" + canonical(record)).hexdigest()


def node_hash(left: str, right: str) -> str:
    return hashlib.sha256(b"\x01" + bytes.fromhex(left) + bytes.fromhex(right)).hexdigest()


def levels(leaves: list[str]) -> list[list[str]]:
    lv = [list(leaves)]
    while len(lv[-1]) > 1:
        cur, nxt = lv[-1], []
        for i in range(0, len(cur), 2):
            nxt.append(node_hash(cur[i], cur[i + 1]) if i + 1 < len(cur) else cur[i])
        lv.append(nxt)
    return lv


def root(leaves: Iterable[str]) -> str:
    leaves = list(leaves)
    if not leaves:
        return hashlib.sha256(b"").hexdigest()
    return levels(leaves)[-1][0]


def proof(leaves: list[str], index: int) -> list[dict]:
    """The path from leaf ``index`` to the root: each step is the sibling hash and the side it sits on."""
    if not 0 <= index < len(leaves):
        raise IndexError(index)
    out = []
    for cur in levels(leaves)[:-1]:
        sib = index ^ 1
        if sib < len(cur):
            out.append({"side": "left" if sib < index else "right", "hash": cur[sib]})
        index //= 2
    return out


def walk(leaf: str, path: list[dict]) -> str:
    h = leaf
    for step in path:
        if step["side"] == "left":
            h = node_hash(step["hash"], h)
        elif step["side"] == "right":
            h = node_hash(h, step["hash"])
        else:
            raise ValueError(f"bad side {step['side']!r}")
    return h


def verify(record: dict, path: list[dict], expected_root: str) -> bool:
    return walk(leaf_hash(record), path) == expected_root
