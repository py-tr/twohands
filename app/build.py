"""Snapshot the spike's numbers into the app so it is self-contained (numbers only; no images, no names).

    python -m app.build            (run from twohands/)

Writes app/data/spike_runs.json (every spike read, as returned by the model) and app/data/official.json
(per form: the official PREP capture, the certified Computos values, adjudicated fields, sample stratum).
Inputs are the in-repo pilot copies (data/pilot/tally-witness, results/pilot/tally-witness; data/pilot/SOURCES.md).
If the PREP / Computos CSVs are in data/raw/ (python -m twohands.sample downloads PREP), official values are
also added for every clave that appears in results/*.jsonl, so a new run gets its official numbers by
re-running this command; no code change.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

from twohands import PILOT_DATA, PILOT_RESULTS, REPO
from twohands import schema as schemamod

OUT = REPO / "app" / "data"
PREP_CSV = REPO / "data" / "raw" / "prep" / "PRES_2024.csv"
COMP_CSV = REPO / "data" / "raw" / "computos" / "PRES_2024.csv"

SPIKE_RUNS = [
    # id, directory, file prefix, model, label, method note
    ("spike-gemma-v2", "results_v2", "gemma__", "Gemma-4-31B-IT", "Gemma-4-31B-IT, page + 4 tiles (spike v2)",
     "pilot reader v2 (docs/sources/tally-witness-pilot.md §2); frozen reader v2"),
    ("spike-qwen", "results", "qwen__", "Qwen3.8-27B", "Qwen3.8-27B, page + 3 tiles (spike)",
     "pilot reader v1 (docs/sources/tally-witness-pilot.md §2); reasoning low"),
    ("spike-gemma-v1", "results", "gemma__", "Gemma-4-31B-IT", "Gemma-4-31B-IT, page + 3 tiles (spike v1)",
     "pilot reader v1 (docs/sources/tally-witness-pilot.md §2)"),
]

CERT_COL = {"TOTAL": "TOTAL_VOTOS_CALCULADOS"}


def num(v):
    v = (v or "").strip().replace(",", "").strip("'").replace('="', "").replace('"', "")
    return int(v) if v.isdigit() else None


def official_from_rows(prep: dict, comp: dict | None, s: dict) -> dict:
    o = {"prep": {}, "cert": {}, "cert_mode": None, "dig": None, "entidad": prep.get("ENTIDAD")}
    for f in s["fields"]:
        if f.get("csv"):
            o["prep"][f["key"]] = num(prep.get(f["csv"]))
        if comp and (f.get("vote") or f["key"] in CERT_COL):
            col = CERT_COL.get(f["key"], f.get("csv"))
            o["cert"][f["key"]] = num(comp.get(col))
    d = (prep.get("DIGITALIZACION") or "").strip()
    o["dig"] = "M" if d.startswith("M") else ("E" if d.startswith("E") else None)
    if comp:
        obs = (comp.get("OBSERVACIONES") or "")
        o["cert_mode"] = "Recuento" if "Recuento" in obs else ("Cotejo" if "Cotejo" in obs else obs.strip() or None)
    return o


def _csv_rows(path: Path, sep: str, header_key: str):
    t = path.read_bytes().decode("utf-8-sig", "replace").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = next(k for k, l in enumerate(t) if l.startswith(header_key))
    return csv.DictReader(io.StringIO("\n".join(t[i:])), delimiter=sep)


def _comp_fix(r: dict) -> dict:
    r = dict(r)
    for a, b in (("PAN-PRI-PRD", "PAN_PRI_PRD"), ("PAN-PRI", "PAN_PRI"), ("PAN-PRD", "PAN_PRD"), ("PRI-PRD", "PRI_PRD"),
                 ("NO_REGISTRADAS", "CANDIDATO/A NO REGISTRADO/A"), ("NULOS", "VOTOS NULOS")):
        r.setdefault(a, r.get(b))
    return r


def result_claves() -> set[str]:
    out = set()
    for p in (REPO / "results").glob("*.jsonl"):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
                k = row.get("clave") if any(x in row for x in ("values", "fields", "parsed", "not_located", "no_call")) else None
            except ValueError:
                continue
            if k:
                out.add(str(k))
    return out


def main() -> int:
    s = schemamod.load()
    OUT.mkdir(parents=True, exist_ok=True)
    sample = {x["clave"]: x for x in json.loads((PILOT_DATA / "sample.json").read_text(encoding="utf-8"))}
    truth = json.loads((PILOT_DATA / "truth_rows.json").read_text(encoding="utf-8"))
    adj = {k: v for k, v in json.loads((PILOT_DATA / "adjudicate.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}

    official = {}
    for k, tr in truth.items():
        o = official_from_rows(tr["prep"], _comp_fix(tr["computos"]) if tr.get("computos") else None, s)
        o["stratum"] = sample.get(k, {}).get("stratum")
        o["adjudicated"] = adj.get(k, {})
        o["source"] = "data/pilot/tally-witness/truth_rows.json"
        official[k] = o

    missing = result_claves() - set(official)
    if missing and PREP_CSV.is_file():
        print(f"loading official values for {len(missing)} new forms from the PREP / Computos CSVs ...")
        prep = {r["CLAVE_CASILLA"].strip("'"): r for r in _csv_rows(PREP_CSV, ",", "CLAVE_CASILLA")
                if r["CLAVE_CASILLA"].strip("'") in missing and r.get("TIPO_ACTA", "").strip() == "2"}
        comp = {}
        if COMP_CSV.is_file():
            for r in _csv_rows(COMP_CSV, "|", "CLAVE_CASILLA"):
                k = r["CLAVE_CASILLA"].strip("'")
                if k in missing:
                    comp[k] = _comp_fix(r)
        for k, r in prep.items():
            o = official_from_rows(r, comp.get(k), s)
            o.update(stratum=None, adjudicated=adj.get(k, {}), source="PREP 2024 CSV + Computos 2024 CSV")
            official[k] = o
    elif missing:
        print(f"{len(missing)} forms in results/*.jsonl have no official values (PREP CSV not found)")

    runs = []
    for rid, d, prefix, model, label, method in SPIKE_RUNS:
        rows = []
        for x in json.loads((PILOT_DATA / "sample.json").read_text(encoding="utf-8")):
            p = PILOT_RESULTS / d / f"{prefix}{x['clave']}.json"
            if not p.is_file():
                continue
            o = json.loads(p.read_text(encoding="utf-8"))
            u = o.get("usage") or {}
            rows.append({"clave": x["clave"], "parsed": o.get("parsed"), "secs": o.get("secs"),
                         "finish": o.get("finish"), "cost": u.get("cost"),
                         "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens")})
        runs.append({"id": rid, "model": model, "label": label, "method": method, "kind": "spike",
                     "source": f"results/pilot/tally-witness/{d}/{prefix}*.json", "rows": rows})
    (OUT / "spike_runs.json").write_text(json.dumps(runs, ensure_ascii=False), encoding="utf-8")
    (OUT / "official.json").write_text(json.dumps(official, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"official values for {len(official)} forms; spike runs: " + ", ".join(f"{r['id']}={len(r['rows'])}" for r in runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
