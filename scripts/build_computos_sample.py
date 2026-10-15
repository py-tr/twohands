"""The certified count (Computos Distritales 2024) of the 300 pre-registered forms, as committed input for `make eval`.

    python scripts/build_computos_sample.py      -> app/data/computos_sample300.csv

One row per form of results/manifest.json that has a Computos row: CLAVE_CASILLA, the certified vote rows, NO
REGISTRADOS, NULOS, TOTAL_VOTOS_CALCULADOS and OBSERVACIONES ("Cotejo" / "Recuento ..."), raw cell values exactly as
published, INE's own column names (a machine file). With app/data/audit_sample_prep300.csv (the first capture) it lets
`python -m twohands.eval` recompute the certified confirmation and the recall bound without the raw CSVs. No model call.
Input (read-only, never committed): data/raw/computos/PRES_2024.csv.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, schema  # noqa: E402
from twohands.adjudicate import COMP_CSV, load_comp  # noqa: E402

OUT = REPO / "app" / "data" / "computos_sample300.csv"
CERT_COLS = {"NO_REGISTRADAS": "CANDIDATO/A NO REGISTRADO/A", "NULOS": "VOTOS NULOS", "TOTAL": "TOTAL_VOTOS_CALCULADOS"}


def columns() -> list[str]:
    s = schema.load()
    return [CERT_COLS.get(k, k) for k in s["vote_keys"] + ["TOTAL"]] + ["OBSERVACIONES"]


def main() -> int:
    assert COMP_CSV.is_file(), f"needs {COMP_CSV.relative_to(REPO)} (not committed)"
    man = json.loads((REPO / "results" / "manifest.json").read_text(encoding="utf-8"))
    claves = [it["clave"] for it in man["items"]]
    comp = load_comp(set(claves))
    cols = columns()
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["CLAVE_CASILLA"] + cols)
        for k in claves:
            if k in comp:
                w.writerow([k] + [(comp[k].get(c) or "").strip() for c in cols])
    print(f"{OUT.relative_to(REPO)}: {sum(k in comp for k in claves)} of {len(claves)} forms x {len(cols)} columns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
