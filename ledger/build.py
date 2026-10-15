"""Snapshot the rainfall-ledger spike (spikes/ledger-rescue) into ledger/ledger.json: our extracted values, the
volunteers' values and the per-year checksum, per sheet. Values only: the sheet images are NOT copied (the source
repo has no licence file); the viewer links to the public PDF page instead.

    python -m ledger.build        (run from twohands/)

Uses the spike's own scorer (evaluate.load / col_ok) so the numbers are exactly the spike's.
Reader: Gemma-4-31B-IT, whole sheet + 3 zoomed strips ("gemmatile"), no re-reads.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from twohands import REPO

LR = REPO.parent / "spikes" / "ledger-rescue"
OUT = REPO / "ledger" / "ledger.json"
RAW = "https://raw.githubusercontent.com/ed-hawkins/rainfall-rescue/master/DATA"
MODEL = "gemmatile"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main() -> int:
    cwd = os.getcwd()
    os.chdir(LR)
    sys.path.insert(0, str(LR))
    try:
        import evaluate as ev  # spike scorer
        sheets = []
        for f in ev.SHEETS:
            name = ev.NAME(f)
            station, idx = name.split("__")
            res = json.load(open(f"results/{MODEL}__{name}.json"))
            g = ev.load(MODEL, f)
            t = ev.truth(f)
            cols = []
            for i, y in enumerate(t["years"]):
                tm = [t["months"][m][i] for m in range(12)]
                tt = t["totals"][i]
                if all(v is None for v in tm) and tt is None:
                    continue
                mv, tv = g.get(y, ([None] * 12, None))
                state = ev.col_state(g, y) if y in g else "missing"
                accepted = y in g and tv is not None and ev.col_ok(mv, tv)
                rsum = round(sum(v for v in mv if v is not None), 2) if any(v is not None for v in mv) else None
                cols.append({"year": y, "read": mv, "read_total": tv, "read_sum": rsum, "truth": tm, "truth_total": tt,
                             "accepted": bool(accepted), "state": state})
            u = res.get("usage") or {}
            sheets.append({"id": name, "station": station, "page": int(idx) + 1, "csv": t["file"],
                           "pdf": f"{RAW}/{station}/{station}.pdf", "years": [c["year"] for c in cols], "cols": cols,
                           "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens")})
    finally:
        os.chdir(cwd)
    meta = {"model": "Gemma-4-31B-IT", "reader": "whole sheet + 3 zoomed strips (spikes/ledger-rescue/tile.py)",
            "truth": "Rainfall Rescue volunteer transcription (source CSVs, github.com/ed-hawkins/rainfall-rescue)",
            "tolerance_in": 0.005, "months": MONTHS,
            "price_per_token": {"in": 3.5e-8, "out": 7e-8, "source": "spikes/ledger-rescue/evaluate.py (usd formula)"}}
    sc = json.loads((LR / "scores.json").read_text(encoding="utf-8"))["models"].get("gemma", {})
    meta["single_image"] = {k: sc.get(k) for k in ("sheets", "cells", "cell_acc", "acc_cols", "cols", "acc_col_cells", "acc_col_exact")}
    meta["single_image"]["source"] = "spikes/ledger-rescue/scores.json (models.gemma: one image per sheet, no tiles)"
    OUT.write_text(json.dumps({"meta": meta, "sheets": sheets}), encoding="utf-8")
    nc = sum(len(s["cols"]) for s in sheets)
    na = sum(c["accepted"] for s in sheets for c in s["cols"])
    print(f"{len(sheets)} sheets, {nc} year-columns, {na} accepted -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
