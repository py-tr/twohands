"""INE's 2024 acceptance metric as we read it (results/ine_metric_DEFINITION.md, committed before this script). No model call.

    python scripts/ine_metric.py           # -> results/ine_metric.md + app/data/ine_metric.json
    python scripts/ine_metric.py --check   # recompute; exit 1 if the committed files differ (make eval)

Per field (primary): the words read AND the digits read both equal the PREP capture. Strict denominator: all 300 x 22
graded fields; failed/unlocated reads, unread words or digits, and "Ilegible"/"Sin dato" captures count as not agreeing.
Inputs (read-only): results/manifest.json, results/calls_gemma.jsonl (last row per form),
app/data/audit_sample_prep300.csv, results/adjudication/verdicts.json.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from twohands import schema as schemamod  # noqa: E402
from twohands.score import wilson  # noqa: E402
from twohands.tiers import digits, usable, words  # noqa: E402

R = REPO / "results"
OUT_JSON = REPO / "app" / "data" / "ine_metric.json"
OUT_MD = R / "ine_metric.md"
LABEL = ("INE's 2024 acceptance metric as we read it from the report, computed on our existing reads after they were "
         "made; the definition was committed before computation; not the same test set or conditions as INE's trial.")
SOURCE = ("https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/176400/"
          "ccoe-10se-26-08-2024-p17-1.pdf")


def num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    return int(v) if v.isdigit() else None


def last(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        out[r["clave"]] = r
    return out


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n) if n else (None, None)
    return {"k": k, "n": n, "pct": round(100 * k / n, 2) if n else None,
            "ci": [round(100 * lo, 2), round(100 * hi, 2)] if n else None}


def compute() -> dict:
    s = schemamod.load()
    keys = s["keys"]
    graded = [f for f in s["fields"] if f.get("csv")]
    claves = [it["clave"] for it in json.loads((R / "manifest.json").read_text(encoding="utf-8"))["items"]]
    G = last(R / "calls_gemma.jsonl")
    with (REPO / "app" / "data" / "audit_sample_prep300.csv").open(encoding="utf-8", newline="") as fh:
        prep = {r["CLAVE_CASILLA"]: r for r in csv.DictReader(fh)}
    V = json.loads((R / "adjudication" / "verdicts.json").read_text(encoding="utf-8"))

    def paper(k, f, cap):
        v = V.get(f"{k}__{f}")
        if not v:
            return cap
        if v["verdict"] not in ("model_right", "capture_right", "neither"):
            return "undecided"
        p = v.get("paper")
        return None if p == "blank" else p

    n_all = both = w_only = d_only = cond_n = cond_k = paper_k = 0
    actas_all = 0
    blanks = {"Ilegible": 0, "Sin dato": 0}
    for k in claves:
        r = G.get(k)
        ok = usable(r)
        d, w = (digits(r, keys), words(r, keys)) if ok else ({}, {})
        acta_ok = True
        for f in graded:
            n_all += 1
            raw = (prep.get(k) or {}).get(f["csv"], "")
            if raw in blanks:
                blanks[raw] += 1
            cap = num(raw)
            dv, wv = d.get(f["key"]), w.get(f["key"])
            dm = cap is not None and dv == cap
            wm = cap is not None and wv == cap
            both += dm and wm
            d_only += dm
            w_only += wm
            acta_ok = acta_ok and dm and wm
            if ok and cap is not None:
                cond_n += 1
                cond_k += dm and wm
            t = paper(k, f["key"], cap)
            paper_k += t is not None and t != "undecided" and dv == t and wv == t
        actas_all += acta_ok
    return {
        "label": LABEL, "source": SOURCE, "definition": "results/ine_metric_DEFINITION.md",
        "forms": len(claves), "usable_reads": sum(usable(G.get(k)) for k in claves), "fields_per_form": len(graded),
        "capture_not_a_number": blanks,
        "primary_per_field_words_and_digits": rate(both, n_all),
        "words_only": rate(w_only, n_all), "digits_only": rate(d_only, n_all),
        "conditional_per_field": rate(cond_k, cond_n),
        "per_acta_strict": rate(actas_all, len(claves)),
        "vs_paper_per_field": rate(paper_k, n_all),
    }


def fmt(x: dict) -> str:
    return f"{x['pct']:.1f}% ({x['k']:,} of {x['n']:,}; Wilson 95% {x['ci'][0]:.1f}-{x['ci'][1]:.1f}%)"


def line(res: dict) -> str:
    p = res["primary_per_field_words_and_digits"]
    return f"{p['pct']:.1f}% of fields agree in words and digits ({p['k']:,} of {p['n']:,})"


def report(res: dict) -> str:
    L = ["# INE's 2024 acceptance metric, as we read it, on the pre-registered 300", "",
         f"*{res['label']}*", "",
         "Built by `scripts/ine_metric.py`; `make eval` recomputes it (`--check`). No model call. Definition, committed "
         f"before this computation: `{res['definition']}`. Source of the metric: INE CCOE report, p. 5, {res['source']}", "",
         f"Forms: {res['forms']} (Gemma reads usable on {res['usable_reads']}); {res['fields_per_form']} graded fields per "
         f"form. Captures with no number: \"Ilegible\" {res['capture_not_a_number']['Ilegible']}, \"Sin dato\" "
         f"{res['capture_not_a_number']['Sin dato']} (count as not agreeing in the strict rows).", "",
         "| Row | Result |", "|---|---|",
         f"| **Primary: per field, words AND digits = the PREP capture, strict (all fields)** | **{fmt(res['primary_per_field_words_and_digits'])}** |",
         f"| Words only = capture, strict | {fmt(res['words_only'])} |",
         f"| Digits only = capture, strict | {fmt(res['digits_only'])} |",
         f"| Per field, conditional (usable read, capture is a number) | {fmt(res['conditional_per_field'])} |",
         f"| Per acta, strict (all 22 fields agree) | {fmt(res['per_acta_strict'])} |",
         f"| Per field vs the paper where adjudicated, strict | {fmt(res['vs_paper_per_field'])} |", "",
         "The reference here is the official capture, which itself has errors (52 confirmed on the 300), so a model that "
         "reads the paper right can still count as not agreeing. This is a different measure from the accepted-set "
         "result, shown beside it: 0 wrong of 1,958 accepted fields (two readers, `results/two_reader_300.md`).", "",
         "## Line", "", f"> {line(res)}. {res['label']}", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    res = compute()
    md, js = report(res), json.dumps(res, indent=1, ensure_ascii=False)
    if "--check" in argv:
        mism = []
        if not OUT_JSON.is_file() or json.loads(OUT_JSON.read_text(encoding="utf-8")) != json.loads(js):
            mism.append("app/data/ine_metric.json")
        if not OUT_MD.is_file() or OUT_MD.read_text(encoding="utf-8") != md:
            mism.append("results/ine_metric.md")
        print(f"ine_metric --check: {len(mism)} mismatches" + (f" ({', '.join(mism)})" if mism else ""))
        return 1 if mism else 0
    OUT_JSON.write_text(js + "\n", encoding="utf-8")
    OUT_MD.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
