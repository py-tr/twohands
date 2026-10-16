"""Snapshot the rainfall-ledger pilot into ledger/ledger.json: our extracted values, the volunteers' values and the
per-year checksum, per sheet. Values only: the sheet images are NOT copied (the source repo has no licence file); the
viewer links to the public PDF page instead.

    python -m ledger.build        (run from twohands/)

Inputs are in-repo copies of the spike's files (data/pilot/SOURCES.md): data/pilot/ledger-rescue/ (sheet list, picked
sheets, the volunteers' CSVs, the spike's scores.json) and results/pilot/ledger-rescue/ (the Gemma reads). The scoring
functions below are the spike's own (the ledger pilot's score.py + evaluate.py, docs/sources/ledger-rescue-pilot.md), copied verbatim in logic, so the
numbers are exactly the spike's. Reader: Gemma-4-31B-IT, whole sheet + 3 zoomed strips ("gemmatile"), no re-reads.
"""
from __future__ import annotations

import csv
import json
import re
import sys

from twohands import REPO

DATA = REPO / "data" / "pilot" / "ledger-rescue"
READS = REPO / "results" / "pilot" / "ledger-rescue"
OUT = REPO / "ledger" / "ledger.json"
RAW = "https://raw.githubusercontent.com/ed-hawkins/rainfall-rescue/master/DATA"
MODEL = "gemmatile"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TOL = 0.0051  # spike score.py


def NAME(f: str) -> str:  # spike evaluate.NAME; the sheet list stores Windows paths, so split on both separators
    return re.split(r"[\\/]", f)[-1].rsplit(".", 1)[0]


def fnum(v):  # spike score.fnum
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    s = str(v).strip().replace("·", ".").replace(",", ".").replace(" ", "")
    if s in ("", "-", "null", "None"):
        return None
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def grid(parsed) -> dict:  # spike score.grid: {year: (months[12], total)}
    out = {}
    if not parsed or "years" not in parsed:
        return out
    ys = parsed.get("years") or []
    ms = parsed.get("months") or []
    ts = parsed.get("totals") or []
    for i, y in enumerate(ys):
        try:
            y = int(y)
        except (TypeError, ValueError):
            continue
        mv = [fnum(ms[m][i]) if m < len(ms) and isinstance(ms[m], list) and i < len(ms[m]) else None for m in range(12)]
        tv = fnum(ts[i]) if i < len(ts) else None
        out[y] = (mv, tv)
    return out


def truth(f: str) -> dict:  # spike score.truth
    st, idx = NAME(f).split("__")
    picked = json.loads((DATA / "picked.json").read_text(encoding="utf-8"))
    sheet = [x for x in picked if x["station"] == st][0]["sheets"][int(idx)]
    with open(DATA / "csv" / f"{st}__{sheet}", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    years = [int(float(v)) for v in rows[4][1:] if v.strip()]

    def num(v):
        v = v.strip()
        try:
            x = round(float(v), 2)
            return None if x <= -99 else x
        except ValueError:
            return None
    months = [[num(rows[5 + m][1 + i]) for i in range(len(years))] for m in range(12)]
    totals = [num(rows[17][1 + i]) for i in range(len(years))]
    return {"years": years, "months": months, "totals": totals, "file": sheet}


def load(model: str, f: str) -> dict | None:  # spike evaluate.load (no re-reads)
    fn = READS / f"{model}__{NAME(f)}.json"
    if not fn.is_file():
        return None
    g = grid(json.loads(fn.read_text(encoding="utf-8")).get("parsed"))
    ty = truth(f)["years"]
    if g and len(set(g) & set(ty)) < len(ty) / 2 and len(g) >= len(ty) - 1:  # misread year header: align by position
        g = {ty[i]: g[y] for i, y in enumerate(sorted(g)) if i < len(ty)}
    return g


def col_ok(mv, tv) -> bool:  # spike evaluate.col_ok
    vals = [v for v in mv if v is not None]
    if not vals and tv is None:
        return True
    if tv is None or not vals:
        return False
    return abs(sum(vals) - tv) <= TOL


def col_state(g, y) -> str:  # spike evaluate.col_state
    if y not in g:
        return "missing"
    return "pass" if col_ok(*g[y]) else "fail"


def main() -> int:
    sheets = []
    for f in json.loads((DATA / "sheets40.json").read_text(encoding="utf-8")):
        name = NAME(f)
        station, idx = name.split("__")
        res = json.loads((READS / f"{MODEL}__{name}.json").read_text(encoding="utf-8"))
        g = load(MODEL, f)
        t = truth(f)
        cols = []
        for i, y in enumerate(t["years"]):
            tm = [t["months"][m][i] for m in range(12)]
            tt = t["totals"][i]
            if all(v is None for v in tm) and tt is None:
                continue
            mv, tv = g.get(y, ([None] * 12, None))
            state = col_state(g, y) if y in g else "missing"
            accepted = y in g and tv is not None and col_ok(mv, tv)
            rsum = round(sum(v for v in mv if v is not None), 2) if any(v is not None for v in mv) else None
            cols.append({"year": y, "read": mv, "read_total": tv, "read_sum": rsum, "truth": tm, "truth_total": tt,
                         "accepted": bool(accepted), "state": state})
        u = res.get("usage") or {}
        sheets.append({"id": name, "station": station, "page": int(idx) + 1, "csv": t["file"],
                       "pdf": f"{RAW}/{station}/{station}.pdf", "years": [c["year"] for c in cols], "cols": cols,
                       "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens")})
    meta = {"model": "Gemma-4-31B-IT", "reader": "whole sheet + 3 zoomed strips (page + 3 strips, docs/sources/ledger-rescue-pilot.md §3)",
            "truth": "Rainfall Rescue volunteer transcription (source CSVs, github.com/ed-hawkins/rainfall-rescue)",
            "tolerance_in": 0.005, "months": MONTHS,
            "price_per_token": {"in": 3.5e-8, "out": 7e-8, "source": "docs/sources/ledger-rescue-pilot.md, appendix (usd formula)"}}
    sc = json.loads((DATA / "scores.json").read_text(encoding="utf-8"))["models"].get("gemma", {})
    meta["single_image"] = {k: sc.get(k) for k in ("sheets", "cells", "cell_acc", "acc_cols", "cols", "acc_col_cells", "acc_col_exact")}
    meta["single_image"]["source"] = "data/pilot/ledger-rescue/scores.json (models.gemma: one image per sheet, no tiles)"
    OUT.write_text(json.dumps({"meta": meta, "sheets": sheets}), encoding="utf-8")
    nc = sum(len(s["cols"]) for s in sheets)
    na = sum(c["accepted"] for s in sheets for c in s["cols"])
    print(f"{len(sheets)} sheets, {nc} year-columns, {na} accepted -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
