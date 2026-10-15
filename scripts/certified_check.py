"""Certified confirmation of the adjudicated verdicts: for every model_right (and, separately, capture_right) field,
look up the certified Computos Distritales value for that field and compare it with the paper value from adjudication.

    python scripts/certified_check.py    # -> results/adjudication/CERTIFIED.md (+ certified.json)

Computos certify the 17 vote rows (incl. no registrados, nulos) and TOTAL_VOTOS_CALCULADOS (their sum; compared with
the acta's written TOTAL). Sections 2-5 and 7 (SOBRANTES, VOTARON, REPRESENTANTES, SACADOS) are not in Computos.
A Computos value after a recount (OBSERVACIONES "Recuento") is a NEW count of the ballots, not a reading of this paper.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, schema
from twohands.adjudicate import label, load_comp, num

OUT = REPO / "results" / "adjudication"
COLS = {"PAN": "PAN", "PRI": "PRI", "PRD": "PRD", "PVEM": "PVEM", "PT": "PT", "MC": "MC", "MORENA": "MORENA",
        "PAN_PRI_PRD": "PAN_PRI_PRD", "PAN_PRI": "PAN_PRI", "PAN_PRD": "PAN_PRD", "PRI_PRD": "PRI_PRD",
        "PVEM_PT_MORENA": "PVEM_PT_MORENA", "PVEM_PT": "PVEM_PT", "PVEM_MORENA": "PVEM_MORENA", "PT_MORENA": "PT_MORENA",
        "NO_REGISTRADAS": "CANDIDATO/A NO REGISTRADO/A", "NULOS": "VOTOS NULOS", "TOTAL": "TOTAL_VOTOS_CALCULADOS"}


def main() -> dict:
    V = json.loads((OUT / "verdicts.json").read_text(encoding="utf-8"))
    ledger = {}
    for line in (OUT / "adjudication.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            ledger[f"{r['clave']}__{r['field']}"] = r
    comp = load_comp({v["form_id"] for v in V.values()})
    res = {}
    for cls in ("model_right", "capture_right"):
        rows = []
        for key, v in sorted(V.items()):
            if v["verdict"] != cls:
                continue
            k, f = v["form_id"], v["field"]
            c = comp.get(k)
            col = COLS.get(f)
            cval = num(c.get(col)) if (c and col) else None
            obs = (c.get("OBSERVACIONES") or "").strip() if c else "no Computos row"
            paper = v.get("paper")
            pnum = paper if isinstance(paper, int) else None
            covered = cval is not None
            rows.append({"clave": k, "field": f, "model": ledger.get(key, {}).get("model_n"),
                         "prep": ledger.get(key, {}).get("prep_raw"), "paper": paper, "computos": cval,
                         "computos_col": col, "obs": obs, "covered": covered,
                         "agrees": covered and pnum is not None and pnum == cval, "recount": "Recuento" in obs})
        res[cls] = rows
    (OUT / "certified.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    mr = res["model_right"]
    X = sum(r["covered"] for r in mr)
    Y = sum(r["agrees"] for r in mr)
    L = ["# Certified confirmation of the adjudicated capture errors",
         "", "Secondary analysis (Amendment 2 b). For every field adjudicated `model_right` (paper shows the model's value: the",
         "PREP capture mis-keyed) and, separately, `capture_right` (the model misread), the certified Computos Distritales value of",
         "the same field (`data/raw/computos/PRES_2024.csv`, cut 08/06/2024) is compared with the paper value from adjudication.",
         "Computos certify the 17 vote rows and the vote total (TOTAL_VOTOS_CALCULADOS, compared with the written TOTAL); they do",
         "not cover SOBRANTES, VOTARON, REPRESENTANTES or SACADOS. A value marked Recuento is a recount of the ballots, so a",
         "difference there need not mean the paper was misread. Code: `scripts/certified_check.py`.",
         "Vote rows are named Option 01 to Option 15 in printed order; `certified.json` keeps INE's column names.", "",
         f"> the first capture mis-keyed 52 of 6,358 fields; the certified count later covers {X} of them and agrees with the image on {Y}",
         ""]
    nt = [r for r in mr if r["covered"] and r["field"] != "TOTAL"]
    L += [f"Of the {X} covered, {X - len(nt)} are TOTAL (compared with the certified calculated total); the vote rows alone: "
          f"{len(nt)} covered, {sum(r['agrees'] for r in nt)} agree. Every covered field where the certified value differs from "
          f"the paper was recounted: {sum(r['recount'] for r in mr if r['covered'] and not r['agrees'])} of {X - Y}.", ""]
    for cls in ("model_right", "capture_right"):
        rows = res[cls]
        cov = [r for r in rows if r["covered"]]
        ag = [r for r in cov if r["agrees"]]
        rc = [r for r in cov if not r["agrees"] and r["recount"]]
        L += [f"## {cls}: {len(rows)} fields", "",
              f"- covered by the certified count: **{len(cov)}** (not covered: {len(rows) - len(cov)}, fields Computos does not certify"
              f" or no Computos row)",
              f"- of those, certified == paper value: **{len(ag)}**; differ: {len(cov) - len(ag)}"
              f" ({len(rc)} of the differing ones after a recount)", "",
              "| clave | field | model | PREP | paper | Computos | Computos note | covered | certified = paper |",
              "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            L.append(f"| {r['clave']} | {label(r['field'])} | {r['model']} | {r['prep']} | {r['paper']} | "
                     f"{'-' if r['computos'] is None else r['computos']} | {r['obs']} | {'yes' if r['covered'] else 'no'} | "
                     f"{('yes' if r['agrees'] else 'NO') if r['covered'] else '-'} |")
        L.append("")
    (OUT / "CERTIFIED.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(L[10]); print(L[12])
    for cls in res:
        cov = [r for r in res[cls] if r["covered"]]
        print(cls, len(res[cls]), "covered", len(cov), "agree", sum(r["agrees"] for r in cov))
    return res


if __name__ == "__main__":
    main()
