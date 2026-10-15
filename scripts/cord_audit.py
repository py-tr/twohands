"""CORD v2 label audit (PROTOCOL_CORD.md). Run with ``python -I`` (the parquet is downloaded, untrusted data):

    python -I scripts/cord_audit.py labels     # identities on CORD's own test labels -> results/cord_label_audit.json
    python -I scripts/cord_audit.py manifest   # seeded draw -> results/manifest_cord100.json (+ sha256)
    python -I scripts/cord_audit.py run --after-qwen-and-confirm100   # the model pass (NOT before the gates below)

The run refuses unless (1) the flag is given, (2) the frozen prompt hash and manifest hash match the protocol,
(3) it is before the kill deadline. Reads go through twohands.amd.chat (the shared rate limiter).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))  # -I drops the script dir from sys.path

from twohands import receipts  # noqa: E402

PARQUET = REPO / "data" / "raw" / "cord" / "test.parquet"
PARQUET_URL = ("https://huggingface.co/datasets/naver-clova-ix/cord-v2/resolve/7f0115a4b758a71d6473b8d085751692da2fef98/"
               "data/test-00000-of-00001-9c204eb3f4e11791.parquet")
PARQUET_SHA = "51c65f1788faff392abe2a0b55b023eb23e9be551c509138eaa3a832514224e7"
SEED = 20261016
N = 100
MANIFEST = REPO / "results" / "manifest_cord100.json"
LABEL_AUDIT = REPO / "results" / "cord_label_audit.json"
CALLS = REPO / "results" / "calls_cord_gemma.jsonl"
DEADLINE = datetime(2026, 10, 16, 22, 0, tzinfo=timezone.utc)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def rows():
    import pyarrow.parquet as pq
    if sha(PARQUET.read_bytes()) != PARQUET_SHA:
        raise SystemExit("test parquet sha256 mismatch")
    t = pq.read_table(PARQUET)
    imgs, gts = t.column("image").to_pylist(), t.column("ground_truth").to_pylist()
    for i, (im, gt) in enumerate(zip(imgs, gts)):
        yield i, im["bytes"], json.loads(gt), gt


def labels() -> dict:
    per, n_viol, n_viol_exact, n_checkable = [], 0, 0, 0
    by_identity: dict = {}
    for i, _, gt, _ in rows():
        rec = receipts.from_cord(gt["gt_parse"])
        ids = receipts.identities(rec)
        exact = receipts.violations(rec, tol=None)
        v = [r for r in ids if r["ok"] is False]
        n_checkable += any(r["ok"] is not None for r in ids)
        n_viol += bool(v)
        n_viol_exact += bool(exact)
        for r in ids:
            d = by_identity.setdefault(r["name"], {"checkable": 0, "violated": 0})
            d["checkable"] += r["ok"] is not None
            d["violated"] += r["ok"] is False
        per.append({"index": i, "image_id": gt["meta"]["image_id"], "violations": v,
                    "violations_exact": len(exact)})
    out = {"split": "test", "receipts": len(per), "receipts_with_a_checkable_identity": n_checkable,
           "receipts_violating_an_identity": n_viol, "receipts_violating_exact_tolerance": n_viol_exact,
           "tolerance": receipts.load()["tolerance"], "by_identity": by_identity,
           "note": "Counts on CORD's own labels. A violation is a label inconsistency OR a receipt that does not add up "
                   "as printed OR an unlabelled term (e.g. a rounding line); only the image decides which.",
           "receipts_detail": [p for p in per if p["violations"]]}
    LABEL_AUDIT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def manifest() -> str:
    all_rows = list(rows())
    order = sorted(range(len(all_rows)), key=lambda i: all_rows[i][2]["meta"]["image_id"])
    random.Random(f"{SEED}:cord-test").shuffle(order)
    items = []
    for i in order[:N]:
        _, img, gt, raw = all_rows[i]
        rec = receipts.from_cord(gt["gt_parse"])
        items.append({"index": i, "image_id": gt["meta"]["image_id"], "image_sha256": sha(img),
                      "ground_truth_sha256": sha(raw.encode("utf-8")),
                      "label_violations": [r["name"] for r in receipts.violations(rec)]})
    m = {"protocol": "PROTOCOL_CORD.md", "seed": SEED, "n": len(items),
         "source": {"dataset": "naver-clova-ix/cord-v2", "licence": "CC-BY-4.0",
                    "card": "https://huggingface.co/datasets/naver-clova-ix/cord-v2",
                    "revision": "7f0115a4b758a71d6473b8d085751692da2fef98", "file": PARQUET_URL,
                    "file_sha256": PARQUET_SHA, "split": "test", "split_size": len(all_rows)},
         "exclusions": [], "prompt_sha256": receipts.prompt_sha256(),
         "schema_sha256": sha((REPO / "schemas" / "cord_receipt.yaml").read_bytes()),
         "order": "test rows sorted by meta.image_id, shuffled with random.Random('20261016:cord-test'); read in this order",
         "items": items}
    MANIFEST.write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8", newline="\n")
    return sha(MANIFEST.read_bytes())


def run(args) -> None:
    import re
    from twohands import amd
    if not args.after_qwen_and_confirm100:
        raise SystemExit("refusing: run only after the Qwen pass and the 100-form INE confirmation (shared rate limit)")
    if datetime.now(timezone.utc) >= DEADLINE:
        raise SystemExit("refusing: past the kill deadline (2026-10-16 22:00 UTC); the audit is not shown anywhere")
    proto = (REPO / "PROTOCOL_CORD.md").read_text(encoding="utf-8")
    want_p = re.search(r"Prompt sha256: `([0-9a-f]{64})`", proto).group(1)
    want_m = re.search(r"Manifest sha256: `([0-9a-f]{64})`", proto).group(1)
    if receipts.prompt_sha256() != want_p or sha(MANIFEST.read_bytes()) != want_m:
        raise SystemExit("refusing: prompt or manifest hash differs from PROTOCOL_CORD.md")
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    done = set()
    if CALLS.is_file():
        for line in CALLS.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                if not r.get("error"):
                    done.add(r["index"])
            except (ValueError, KeyError):
                pass
    imgs = {i: (img, gt) for i, img, gt, _ in rows()}
    for it in m["items"]:
        if it["index"] in done:
            continue
        img, gt = imgs[it["index"]]
        row = receipts.read(receipts.MODEL, img, chat=amd.chat)
        g = receipts.gate(row["parsed"])
        row.update(index=it["index"], image_id=it["image_id"], gate={k: g[k] for k in
                   ("accepted", "reasons", "accepted_fields", "unverified_fields")},
                   identities=g["identities"], ts=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        with open(CALLS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(it["index"], "accepted" if g["accepted"] else "routed", row.get("error") or "", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["labels", "manifest", "run"])
    ap.add_argument("--after-qwen-and-confirm100", action="store_true")
    a = ap.parse_args()
    if a.cmd == "labels":
        o = labels()
        print({k: o[k] for k in ("receipts", "receipts_with_a_checkable_identity", "receipts_violating_an_identity",
                                 "receipts_violating_exact_tolerance", "by_identity")})
    elif a.cmd == "manifest":
        print("manifest sha256", manifest())
    else:
        run(a)


if __name__ == "__main__":
    main()
