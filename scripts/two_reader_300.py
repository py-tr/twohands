"""Amendment 2 tiers on the pre-registered 300, now that both readers have read all of them. No model call.

    python scripts/two_reader_300.py   # -> app/data/two_reader_300.json (the app reads it) + results/two_reader_300.md

Inputs (read-only): results/manifest.json, results/calls_gemma.jsonl and results/calls_qwen.jsonl (last row per form),
results/adjudication/verdicts.json, app/data/audit_sample_prep300.csv. `make eval` (twohands/eval.py) recomputes every
number here independently and fails on any difference.

Tiers (accepted / 300; unlocated pages and failed reads count in the denominator):
  gemma         Gemma alone, frozen gate (the primary, PROTOCOL.md section 5), for reference
  qwen          Qwen alone, frozen gate (section 7)
  two_reader    Amendment 2 (d), strict mode: Gemma = Qwen on all 23 digit values + the capture gate of (c) on the
                agreed read (every digit read, words = digits wherever either reader read words, rows sum to TOTAL)
  two_reader_s7 section 7's two-reader tier: both readers' frozen gates pass and their 23 digit values agree
  v2_2r         POST-HOC (Amendment 3): gate v2 on Gemma, SOBRANTES confirmed by Gemma's words or by Qwen's digits
  v2_2r_strict  POST-HOC (not in any amendment): gate v2 on Gemma, SOBRANTES accepted only if Qwen's digits equal Gemma's
Per accepted field: truth = the paper where results/adjudication/verdicts.json read it, else the capture (section 6).
"""
from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from twohands import schema as schemamod  # noqa: E402
from twohands.gate import gate  # noqa: E402
from twohands.gate_v2 import gate_v2  # noqa: E402
from twohands.score import wilson  # noqa: E402
from twohands.tiers import capture_gate, digits, judge, two_reader, usable, words  # noqa: E402

R = REPO / "results"
OUT_JSON = REPO / "app" / "data" / "two_reader_300.json"
OUT_MD = R / "two_reader_300.md"
LABELS = {
    "gemma": "Gemma alone (frozen gate, primary)",
    "gemma_capture": "Gemma alone, capture gate (Amendment 2 c: words = digits, rows = TOTAL)",
    "qwen": "Qwen alone (frozen gate)",
    "two_reader": "Two readers, strict mode (Amendment 2 d)",
    "two_reader_s7": "Two readers, both frozen gates (section 7)",
    "v2_2r": "POST-HOC v2-2R (Amendment 3: unused ballots confirmed by words or Qwen)",
    "v2_2r_strict": "POST-HOC v2-2R strict (unused ballots only if Qwen agrees)",
}


def num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    return int(v) if v.isdigit() else None


def last(path: Path) -> dict:
    out = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            out[r["clave"]] = r
    return out


def parsed(r, keys):
    if not usable(r):
        return None
    F = r.get("fields") or {}
    return {"values": [{"label": (F.get(k) or {}).get("label"), "n": (F.get(k) or {}).get("n"),
                        "w": (F.get(k) or {}).get("w")} for k in keys]}


def compute() -> dict:
    from app.store import code_of
    s = schemamod.load()
    keys = s["keys"]
    graded = [f for f in s["fields"] if f.get("csv")]
    man = json.loads((R / "manifest.json").read_text(encoding="utf-8"))
    claves = [it["clave"] for it in man["items"]]
    layout = {it["clave"]: it["layout"] for it in man["items"]}
    G, Q = last(R / "calls_gemma.jsonl"), last(R / "calls_qwen.jsonl")
    with (REPO / "app" / "data" / "audit_sample_prep300.csv").open(encoding="utf-8", newline="") as fh:
        prep = {r["CLAVE_CASILLA"]: r for r in csv.DictReader(fh)}
    V = json.loads((R / "adjudication" / "verdicts.json").read_text(encoding="utf-8"))

    def frozen(r):
        p = parsed(r, keys)
        return p is not None and gate(p, s).accepted

    def v2(k, strict):
        p = parsed(G.get(k), keys)
        if p is None:
            return False
        second = digits(Q.get(k), keys) if usable(Q.get(k)) else None
        return gate_v2(p, s, "v2", second=second, second_required=strict).accepted

    tr = {k: two_reader(G.get(k), Q.get(k), s) for k in claves}
    rules = {"gemma": (G, lambda k: frozen(G.get(k))),
             "gemma_capture": (G, lambda k: usable(G.get(k)) and capture_gate(digits(G[k], keys), (words(G[k], keys),), s)[0]),
             "qwen": (Q, lambda k: frozen(Q.get(k))),
             "two_reader": (G, lambda k: tr[k][0]),
             "two_reader_s7": (G, lambda k: frozen(G.get(k)) and frozen(Q.get(k))
                               and digits(G[k], keys) == digits(Q[k], keys)),
             "v2_2r": (G, lambda k: v2(k, False)),
             "v2_2r_strict": (G, lambda k: v2(k, True))}
    out = {"forms": len(claves), "qwen_reads": sum(usable(Q.get(k)) for k in claves),
           "gemma_reads": sum(usable(G.get(k)) for k in claves),
           "agree_all_23": sum(usable(G.get(k)) and usable(Q.get(k)) and digits(G[k], keys) == digits(Q[k], keys)
                               for k in claves),
           "two_reader_causes": dict(sorted(collections.Counter(c for ok, c in tr.values() if not ok).items())),
           "tiers": {}}
    for name, (reader, rule) in rules.items():
        acc = [k for k in claves if rule(k)]
        n, res, dis = 0, collections.Counter(), []
        for k in acc:
            d = digits(reader[k], keys)
            for f in graded:
                n += 1
                pv = num(prep[k][f["csv"]]) if k in prep else None
                j = judge(d[f["key"]], k, f["key"], pv, V)
                res[j] += 1
                if d[f["key"]] != pv:
                    v = V.get(f"{k}__{f['key']}") or {}
                    dis.append({"clave": k, "field": code_of(f["key"]), "reader": d[f["key"]],
                                "prep": prep[k][f["csv"]] if k in prep else None, "verdict": v.get("verdict"),
                                "paper": v.get("paper"), "judged": j})
        err = res["wrong"]
        out["tiers"][name] = {
            "label": LABELS[name], "post_hoc": name.startswith("v2"), "accepted": len(acc),
            "movil": sum(layout[k] == "movil" for k in acc), "escaner": sum(layout[k] == "escaner" for k in acc),
            "fields": n, "disagree": len(dis), "capture_errors": sum(x["verdict"] == "model_right" and x["judged"] == "right"
                                                                      for x in dis),
            "errors": err, "undecided": res["undecided"], "unadjudicated": res["unadjudicated"],
            "ci": list(wilson(err, n)) if n else None, "disagreements": dis, "forms_accepted": acc}
    return out


def pct(ci):
    return f"{100 * ci[0]:.2f}% to {100 * ci[1]:.2f}%" if ci else "-"


def line(d: dict) -> str:
    t = d["tiers"]["two_reader"]
    return f"With two readers: {t['accepted']} forms, {t['errors']} wrong fields in {t['fields']:,}."


def markdown(d: dict) -> str:
    T = d["tiers"]
    L = ["# Amendment 2 tiers on the pre-registered 300: Qwen alone and the two-reader tier", "",
         "Generated by `python scripts/two_reader_300.py`; recomputed independently by `make eval`. No model call. Inputs: "
         "`results/calls_gemma.jsonl`, `results/calls_qwen.jsonl` (last row per form), `results/adjudication/verdicts.json`, "
         "`app/data/audit_sample_prep300.csv`.", "",
         f"Reads: Gemma {d['gemma_reads']} of {d['forms']}, Qwen {d['qwen_reads']} of {d['forms']} (complete). Secondary analyses "
         "(PROTOCOL.md Amendment 2, committed before any Qwen read of the 300 and before any adjudication); the primary and "
         "the headline rule are unchanged. Rows marked POST-HOC use gate v2, designed after seeing these reads "
         "(Amendment 3); they are not a test of anything.", "",
         "Accepted fields are judged against the paper where an adjudication verdict read it, otherwise against the "
         "official capture (PREP). Every accepted field where a reader differs from the capture already had a verdict on "
         "the paper; no new adjudication was needed.", "",
         f"**{line(d)}**", "",
         "| tier | accepted (/300) | Movil / Escaner | accepted fields | differ from capture | of which capture errors | "
         "wrong vs the paper (Wilson 95%) | undecided | not adjudicated |",
         "|---|---|---|---|---|---|---|---|---|"]
    for t in T.values():
        L.append(f"| {t['label']} | {t['accepted']} | {t['movil']} / {t['escaner']} | {t['fields']:,} | {t['disagree']} | "
                 f"{t['capture_errors']} | {t['errors']} ({pct(t['ci'])}) | {t['undecided']} | {t['unadjudicated']} |")
    c = d["two_reader_causes"]
    L += ["", f"Two-reader tier: the readers agree on all 23 digit values on {d['agree_all_23']} forms; the tier routes "
          + ", ".join(f"{v} for {k}" for k, v in c.items()) + " (no read = either reader has no usable read; differ = "
          "the two readers' digits differ somewhere; empty = a digit field unread by both; words = words differ from "
          "the agreed digits; rows = the vote rows do not sum to TOTAL).", "",
          "Undecided: a field where the reader equals the capture but the paper was judged ambiguous when Gemma disputed "
          "it. The two-reader tier drops the row-label check and the section identities of the frozen gate and relies on "
          "the two readers' agreement instead, which is why it accepts more forms than either reader alone.", ""]
    for t in T.values():
        L.append(f"## {t['label']}")
        if not t["disagreements"]:
            L += ["- no accepted field differs from the capture", ""]
            continue
        for x in t["disagreements"]:
            L.append(f"- {x['clave']} {x['field']}: reader {x['reader']}, capture {x['prep']}, paper {x['paper']} "
                     f"({x['verdict']}; reader {x['judged']}); crop `results/adjudication/{x['clave']}__{x['field']}.jpg`")
        L.append("")
    return "\n".join(L)


def main() -> int:
    d = compute()
    OUT_JSON.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    OUT_MD.write_text(markdown(d), encoding="utf-8")
    for t in d["tiers"].values():
        print(f"{t['label']:58s} {t['accepted']:4d} forms {t['fields']:5d} fields  differ {t['disagree']}  wrong {t['errors']}"
              f"  undecided {t['undecided']}  unadjudicated {t['unadjudicated']}")
    print(line(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
