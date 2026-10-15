"""The keyed CSV of the sample audit: the official first capture (PREP 2024) of the 300 pre-registered forms.

    python scripts/build_audit_sample.py      -> app/data/audit_sample_prep300.csv

One row per form, one column per keyed field, INE's own column names and raw cell values ("Ilegible", "Sin dato",
blank) exactly as published, so the audit's column auto-mapping is exercised on the real file. Machine file: INE
column names stay; every page and export of the audit shows "Option NN". No model call.
Input (read-only, never committed): data/raw/prep/PRES_2024.csv.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, schema  # noqa: E402
from twohands.sample import PREP_CSV, load_rows  # noqa: E402

OUT = REPO / "app" / "data" / "audit_sample_prep300.csv"


def main() -> int:
    s = schema.load()
    cols = [f["csv"] for f in s["fields"] if f.get("csv")]
    man = json.loads((REPO / "results" / "manifest.json").read_text(encoding="utf-8"))
    claves = [it["clave"] for it in man["items"]]
    rows = {r["CLAVE_CASILLA"]: r for r in load_rows(PREP_CSV) if r["CLAVE_CASILLA"] in set(claves)}
    missing = [k for k in claves if k not in rows]
    assert not missing, missing
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["CLAVE_CASILLA"] + cols)
        for k in claves:
            w.writerow([k] + [(rows[k].get(c) or "").strip() for c in cols])
    print(f"{OUT.relative_to(REPO)}: {len(claves)} forms x {len(cols)} fields")
    return 0


if __name__ == "__main__":
    sys.exit(main())
