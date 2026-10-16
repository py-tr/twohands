"""The blind check of the AGREEING fields: a seeded random 200 of the accepted fields where the model and the official
capture agree, on the forms the two-reader tier accepts (Amendment 2 d). No model call.

    python scripts/build_agree200.py            # writes results/adjudication_agree200/ (crops, verdicts.json, README.md)
    python scripts/build_agree200.py --check    # the draw and the files match (make eval)

Why: "0 wrong of 1,958" is judged against the official capture. The 3 accepted fields that differ from the capture
were checked on the photo; the 1,955 where the model and the capture agree were not. A person reads 200 of them
blind at /check?set=agree200 (no model value, no capture value shown); the wording on the site switches to "a random
200 agreeing fields were checked by a person: N agreed" only once all 200 are answered (app/numbers.checked_line).

The draw: every (form, field) pair in the pool, sorted, then random.Random(SEED).sample(pool, 200). The pool and the
seed are fixed here and the drawn list is written to verdicts.json with the pool size and its sha256.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from twohands import schema as schemamod  # noqa: E402

SEED, N = 20261016, 200
OUT = REPO / "results" / "adjudication_agree200"
TIERS = REPO / "app" / "data" / "two_reader_300.json"
PREP = REPO / "app" / "data" / "audit_sample_prep300.csv"
CALLS = REPO / "results" / "calls_gemma.jsonl"


def num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    return int(v) if v.isdigit() else None


def pool() -> tuple[list[tuple[str, str, int]], dict]:
    s = schemamod.load(schemamod.DEFAULT)
    T = json.loads(TIERS.read_text(encoding="utf-8"))
    acc = T["tiers"]["two_reader"]["forms_accepted"]
    rows = {}
    for line in CALLS.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        rows[r["clave"]] = r
    with PREP.open(encoding="utf-8", newline="") as f:
        prep = {r["CLAVE_CASILLA"]: r for r in csv.DictReader(f)}
    out = []
    for k in sorted(acc):
        r = rows[k]
        for f in s["fields"]:
            if not f.get("csv"):
                continue
            m = ((r.get("fields") or {}).get(f["key"]) or {}).get("n")
            if m is not None and m == num(prep[k][f["csv"]]):
                out.append((k, f["key"], m))
    return out, rows


def draw() -> dict:
    P, rows = pool()
    picked = random.Random(SEED).sample(P, N)
    sha = hashlib.sha256("\n".join(f"{k}__{f}={v}" for k, f, v in P).encode()).hexdigest()
    items = {f"{k}__{f}": {"form_id": k, "field": f, "verdict": "agree", "paper": v,
                           "evidence": "model and official capture agree (value hidden on the blind page)"}
             for k, f, v in sorted(picked)}
    return {"meta": {"seed": SEED, "n": N, "pool": len(P), "pool_sha256": sha,
                     "pool_rule": "accepted forms of the two-reader tier (Amendment 2 d); graded fields where the "
                                  "model's digits equal the official capture (PREP 2024)"},
            "items": items, "_rows": rows}


def write(d: dict) -> None:
    from twohands.adjudicate import boxes, crop, crop_name
    s = schemamod.load(schemamod.DEFAULT)
    bx = boxes(s)
    OUT.mkdir(parents=True, exist_ok=True)
    for key, it in d["items"].items():
        r = d["_rows"][it["form_id"]]
        crop(REPO / r["image"], bx[it["field"]], OUT / crop_name(it["form_id"], it["field"]))
    (OUT / "verdicts.json").write_text(json.dumps(d["items"], ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "draw.json").write_text(json.dumps(d["meta"], indent=1), encoding="utf-8")
    m = d["meta"]
    (OUT / "README.md").write_text("\n".join([
        "# Blind check of 200 agreeing fields", "",
        f"Pool: {m['pool_rule']}: **{m['pool']:,} fields** (pool sha256 `{m['pool_sha256'][:16]}...`). Drawn: "
        f"`random.Random({m['seed']}).sample(pool, {m['n']})` by `scripts/build_agree200.py`. No model call.", "",
        "Each crop is cut from the masked page (never a raw image). A person reads them blind at `/check?set=agree200`: "
        "the page shows no model value and no capture value. Answers go to `app/state/spotcheck_agree200.json`; "
        "`/check/results?set=agree200` compares them with the agreed value.", "",
        "Until all 200 are answered, every page says: fields where the model and the capture agree were not "
        "individually checked.", ""]), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    d = draw()
    if a.check:
        bad = []
        try:
            stored = json.loads((OUT / "verdicts.json").read_text(encoding="utf-8"))
        except OSError:
            stored = None
        if stored != json.loads(json.dumps(d["items"], ensure_ascii=False)):
            bad.append("results/adjudication_agree200/verdicts.json differs from the seeded draw")
        from twohands.adjudicate import crop_name
        miss = [k for k, it in d["items"].items() if not (OUT / crop_name(it["form_id"], it["field"])).is_file()]
        if miss:
            bad.append(f"{len(miss)} crops missing")
        print(f"agree200 --check: {len(bad)} mismatches (pool {d['meta']['pool']:,}, drawn {N})"
              + "".join(f"\n  - {b}" for b in bad))
        return 1 if bad else 0
    write(d)
    print(f"agree200: pool {d['meta']['pool']:,} agreeing fields, drew {N} -> {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
