"""The cost of the problem, from INE's own 2024 files (presidential). No model call.

    python scripts/national_counts.py           # -> app/data/national_counts.json + results/national_counts.md
    python scripts/national_counts.py --check   # recompute; exit 1 if the committed files differ (make eval)

Inputs (read-only): data/raw/prep/PRES_2024.csv (PREP final cut, 03/06/2024 20:05,
https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip) and data/raw/computos/PRES_2024.csv (Cómputos
Distritales, cut 08/06/2024 20:30). Ported from notes/bv-brainstorm/scripts4/prep_counts.py and cotejo_diff.py.

Measures:
- "Ilegible" fields (17 vote fields + 4 count fields + total) and the actas carrying at least one, on captured actas;
- on the polling stations the district councils did NOT recount (Cómputos OBSERVACIONES starts "Cotejo"), the actas where
  the PREP capture and the certified count differ on at least one vote field: a number that differs, "Ilegible" in the
  PREP where the count is a number, or "Sin dato" in the PREP where the count is non-zero.
A difference says two captures (or two copies of the paper) disagree, not which one is right. Clerical only: no party,
no totals, no outcome.
"""
from __future__ import annotations

import collections
import csv
import io
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PREP = REPO / "data" / "raw" / "prep" / "PRES_2024.csv"
COMP = REPO / "data" / "raw" / "computos" / "PRES_2024.csv"
OUT_JSON = REPO / "app" / "data" / "national_counts.json"
OUT_MD = REPO / "results" / "national_counts.md"

VOTE = ["PAN", "PRI", "PRD", "PVEM", "PT", "MC", "MORENA", "PAN-PRI-PRD", "PAN-PRI", "PAN-PRD", "PRI-PRD", "PVEM_PT_MORENA",
        "PVEM_PT", "PVEM_MORENA", "PT_MORENA", "NO_REGISTRADAS", "NULOS"]
CVOTE = ["PAN", "PRI", "PRD", "PVEM", "PT", "MC", "MORENA", "PAN_PRI_PRD", "PAN_PRI", "PAN_PRD", "PRI_PRD", "PVEM_PT_MORENA",
         "PVEM_PT", "PVEM_MORENA", "PT_MORENA", "CANDIDATO/A NO REGISTRADO/A", "VOTOS NULOS"]
TOP = ["TOTAL_BOLETAS_SOBRANTES", "TOTAL_PERSONAS_VOTARON", "TOTAL_REP_PARTIDO_CI_VOTARON", "TOTAL_VOTOS_SACADOS"]


def rows(path: Path, delim: str):
    raw = path.read_bytes()
    try:
        txt = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        txt = raw.decode("latin-1")
    lines = txt.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    i = next(k for k, line in enumerate(lines) if line.startswith("CLAVE_CASILLA"))
    r = csv.reader(io.StringIO("\n".join(lines[i:])), delimiter=delim)
    h = next(r)
    for row in r:
        if len(row) == len(h):
            yield dict(zip(h, row))


def as_int(v):
    try:
        return int(v)
    except ValueError:
        return None


def compute() -> dict:
    c = collections.Counter()
    ALL = list(rows(PREP, ","))
    for d in ALL:
        vals = [d[k].strip() for k in VOTE + TOP + ["TOTAL_VOTOS_ASENTADO"]]
        if all(v == "-" for v in vals[:3]):
            continue
        c["captured"] += 1
        il = sum(v.lower() == "ilegible" for v in vals)
        c["ilegible_fields"] += il
        c["actas_with_ilegible"] += bool(il)
    P = [d for d in ALL if d["TIPO_ACTA"].strip() == "2"]
    cm = {d["CLAVE_CASILLA"].strip("'"): d for d in rows(COMP, "|") if d["TIPO_ACTA"].strip() == "2"}
    for d in P:
        if d["PAN"].strip() == "-":
            continue
        e = cm.get(d["CLAVE_CASILLA"].strip("'"))
        if not e or not e["OBSERVACIONES"].startswith("Cotejo"):
            continue
        c["not_recounted"] += 1
        kinds = set()
        for a, b in zip(VOTE, CVOTE):
            q = as_int(e[b].strip())
            if q is None:
                continue
            p = d[a].strip()
            pi = as_int(p)
            if pi is not None:
                if pi != q:
                    kinds.add("num")
                    c["fields_number_differs"] += 1
            elif p.lower() == "ilegible":
                kinds.add("ileg")
                c["fields_ilegible_count_nonzero"] += q != 0
            elif p.lower() == "sin dato" and q != 0:
                kinds.add("sd")
                c["fields_sindato_count_nonzero"] += 1
        c["not_recounted_differ"] += bool(kinds)
    out = dict(sorted(c.items()))
    out["not_recounted_differ_pct"] = round(100 * c["not_recounted_differ"] / c["not_recounted"], 1)
    out["sources"] = {"prep": "data/raw/prep/PRES_2024.csv (PREP 2024 final cut, "
                              "https://prep2024.ine.mx/publicacion/nacional/assets/20240603_2005_PREP.zip)",
                      "computos": "data/raw/computos/PRES_2024.csv (Cómputos Distritales 2024, presidential)"}
    return out


def line(d: dict) -> str:
    return (f"On the {d['not_recounted']:,} polling stations that were not recounted, INE's two official records of the "
            f"same paper, the preliminary capture and the certified count, disagree on at least one vote field in "
            f"{d['not_recounted_differ']:,} ({d['not_recounted_differ_pct']}%).")


def report(d: dict) -> str:
    return "\n".join([
        "# The cost of the problem, from INE's own 2024 files", "",
        "Built by `scripts/national_counts.py`; `make eval` recomputes it (`--check`). No model call. Presidential file; "
        f"\"Ilegible\" counted on every captured row, the comparison with the certified count on TIPO_ACTA 2. Sources: {d['sources']['prep']}; {d['sources']['computos']}.", "",
        "| Measure | Value |", "|---|---|",
        f"| Captured actas in the PREP | {d['captured']:,} |",
        f"| Fields recorded \"Ilegible\" (vote, count and total fields) | {d['ilegible_fields']:,} on {d['actas_with_ilegible']:,} actas |",
        f"| Not recounted (certified count by cotejo), captured | {d['not_recounted']:,} |",
        f"| of which the PREP capture and the certified count differ on at least one vote field | **{d['not_recounted_differ']:,} ({d['not_recounted_differ_pct']}%)** |",
        f"| fields: numbers that differ | {d['fields_number_differs']:,} |",
        f"| fields: \"Ilegible\" in the PREP, non-zero in the count | {d['fields_ilegible_count_nonzero']:,} |",
        f"| fields: \"Sin dato\" in the PREP, non-zero in the count | {d['fields_sindato_count_nonzero']:,} |", "",
        "A difference says two captures disagree, not which one is right; the photo does. The preliminary count is "
        "preliminary by design; the certified count is the official result. No party, no totals, no outcome.", "",
        "## Line", "", f"> {line(d)}", ""])


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not (PREP.is_file() and COMP.is_file()):   # data/raw/ is not committed (gitignored, ~130 MB)
        ok = OUT_JSON.is_file() and OUT_MD.is_file() and OUT_MD.read_text(encoding="utf-8") == report(
            json.loads(OUT_JSON.read_text(encoding="utf-8")))
        print("national_counts --check: raw CSVs absent (download them per docs/NUMBERS.md B); committed json and md "
              + ("agree" if ok else "DISAGREE"))
        return 0 if ok else 1
    d = compute()
    md, js = report(d), json.dumps(d, indent=1, ensure_ascii=False)
    if "--check" in argv:
        mism = []
        if not OUT_JSON.is_file() or json.loads(OUT_JSON.read_text(encoding="utf-8")) != json.loads(js):
            mism.append("app/data/national_counts.json")
        if not OUT_MD.is_file() or OUT_MD.read_text(encoding="utf-8") != md:
            mism.append("results/national_counts.md")
        print(f"national_counts --check: {len(mism)} mismatches" + (f" ({', '.join(mism)})" if mism else ""))
        return 1 if mism else 0
    OUT_JSON.write_text(js + "\n", encoding="utf-8")
    OUT_MD.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
