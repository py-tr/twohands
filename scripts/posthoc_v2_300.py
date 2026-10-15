"""POST-HOC (Amendment 3): gate v2 / v2b applied to the STORED Gemma reads of the 300. No model call.

    python scripts/posthoc_v2_300.py      # -> results/posthoc_v2_300.md (+ .json)

Truth per graded field on an accepted form: a verdict in results/adjudication/verdicts.json decides
(model_right = correct; capture_right / neither = error; paper_ambiguous / unreadable / crop_wrong = undecided);
with no verdict, model digits == PREP = correct, and model != PREP is FLAGGED for adjudication.
"""
import collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, schema
from twohands.gate import gate
from twohands.gate_v2 import gate_v2
from twohands.run import jsonl
from twohands.sample import PREP_CSV, load_rows
from twohands.score import num, wilson

R = REPO / "results"


def parsed_of(r: dict, s: dict):
    if not r or r.get("no_call") or not r.get("parsed_ok"):
        return None
    F = r.get("fields") or {}
    return {"values": [{"label": (F.get(k) or {}).get("label"), "n": (F.get(k) or {}).get("n"),
                        "w": (F.get(k) or {}).get("w")} for k in s["keys"]]}


def last(path: Path) -> dict:
    out = {}
    for r in jsonl(path):
        out[r["clave"]] = r
    return out


def main() -> dict:
    s = schema.load()
    man = json.loads((R / "manifest.json").read_text(encoding="utf-8"))
    claves = [it["clave"] for it in man["items"]]
    layout = {it["clave"]: it["layout"] for it in man["items"]}
    prep = {r["CLAVE_CASILLA"]: r for r in load_rows(PREP_CSV) if r["CLAVE_CASILLA"] in set(claves)}
    V = json.loads((R / "adjudication" / "verdicts.json").read_text(encoding="utf-8"))
    G, Q = last(R / "calls_gemma.jsonl"), last(R / "calls_qwen.jsonl")
    qwen_ok = {k for k, r in Q.items() if r.get("parsed_ok")}
    graded = [f for f in s["fields"] if f.get("csv")]

    def qvals(k):
        if k not in qwen_ok:
            return None
        return {f: (Q[k].get("fields", {}).get(f) or {}).get("n") for f in s["keys"]}

    tiers = {"v1 (frozen gate)": lambda p, k: gate(p, s).accepted,
             "v2": lambda p, k: gate_v2(p, s, "v2").accepted,
             "v2-2R (Qwen confirms SOBRANTES)": lambda p, k: gate_v2(p, s, "v2", second=qvals(k) or {}).accepted,
             "v2b (relaxed label, secondary)": lambda p, k: gate_v2(p, s, "v2b").accepted}
    out, mism = {}, 0
    for name, fn in tiers.items():
        acc = []
        for k in claves:
            p = parsed_of(G.get(k), s)
            ok = fn(p, k) if p is not None else False
            if name.startswith("v1") and p is not None and bool(G[k].get("accepted")) != ok:
                mism += 1
            if ok:
                acc.append(k)
        fields_n, err, und, flag, err_list, und_list = 0, 0, 0, [], [], []
        for k in acc:
            for f in graded:
                fields_n += 1
                m = (G[k]["fields"].get(f["key"]) or {}).get("n")
                pv = num(prep[k][f["csv"]]) if k in prep else None
                v = V.get(f"{k}__{f['key']}")
                if v:
                    if v["verdict"] in ("capture_right", "neither"):
                        err += 1
                        err_list.append(f"{k} {f['key']}: model {m}, PREP {prep[k][f['csv']]}, paper {v.get('paper')} ({v['verdict']})")
                    elif v["verdict"] != "model_right":
                        und += 1
                        und_list.append(f"{k} {f['key']}: {v['verdict']}")
                elif m != pv:
                    flag.append(f"{k} {f['key']}: model {m}, PREP {prep[k][f['csv']] if k in prep else '-'}")
        lo, hi = wilson(err, fields_n) if fields_n else (0, 0)
        out[name] = {"accepted": len(acc), "movil": sum(layout[k] == "movil" for k in acc),
                     "escaner": sum(layout[k] == "escaner" for k in acc), "fields": fields_n, "errors": err,
                     "undecided": und, "flagged": flag, "error_list": err_list, "undecided_list": und_list,
                     "err_rate": err / fields_n if fields_n else None, "ci": [lo, hi], "forms": acc}
    out["_meta"] = {"qwen_parsed_reads": len(qwen_ok), "v1_recompute_mismatches": mism}
    (R / "posthoc_v2_300.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    L = ["# POST-HOC: gate v2 / v2b re-scored on the stored Gemma reads of the 300",
         "", "**Post-hoc.** Gate v2 was designed after seeing these 300 reads and their adjudication (PROTOCOL.md Amendment 3).",
         "These numbers are NOT a test of v2; the pre-registered test is the fresh 100-form draw (`results/manifest_confirm100.json`).",
         "No model was called: the stored Gemma reads (`results/calls_gemma.jsonl`, last row per form) are re-gated.",
         "Truth: a verdict in `results/adjudication/verdicts.json` decides; with no verdict, model = PREP counts as correct and",
         "model != PREP is flagged for adjudication. Graded fields: the 22 with a PREP column.", "",
         f"Recomputed v1 vs the stored `accepted` flag: {mism} mismatches.",
         f"Qwen reads available for v2-2R: {len(qwen_ok)} of 300 (the Qwen pass is still running; a form without a Qwen read",
         "cannot be confirmed by Qwen, so v2-2R is a lower bound until the pass ends).", "",
         "| gate | touchless forms (/300) | Movil / Escaner | accepted fields | errors | error rate (Wilson 95%) | undecided | flagged |",
         "|---|---|---|---|---|---|---|---|"]
    for name, o in out.items():
        if name.startswith("_"):
            continue
        rate = f"{100 * o['err_rate']:.2f}% ({100 * o['ci'][0]:.2f}-{100 * o['ci'][1]:.2f}%)" if o["fields"] else "-"
        L.append(f"| {name} | {o['accepted']} | {o['movil']} / {o['escaner']} | {o['fields']} | {o['errors']} | {rate} | "
                 f"{o['undecided']} | {len(o['flagged'])} |")
    L.append("")
    for name, o in out.items():
        if name.startswith("_"):
            continue
        L.append(f"## {name}")
        L.append(f"- errors: " + ("; ".join(o["error_list"]) or "none"))
        L.append(f"- undecided (ambiguous/unreadable/crop): " + ("; ".join(o["undecided_list"]) or "none"))
        L.append(f"- flagged for adjudication (model != PREP, no verdict): " + ("; ".join(o["flagged"]) or "none"))
        L.append("")
    v1, v2, v2b = out["v1 (frozen gate)"], out["v2"], out["v2b (relaxed label, secondary)"]
    L.append("## Lines")
    for nm, o in (("v2", v2), ("v2b", v2b)):
        L.append(f"> POST-HOC {nm} on the 300: {o['accepted']} touchless forms (v1: {v1['accepted']}), {o['fields']} accepted "
                 f"fields, {o['errors']} errors ({100 * (o['err_rate'] or 0):.2f}%), {len(o['flagged'])} flagged for adjudication.")
    (R / "posthoc_v2_300.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[-3:]))
    return out


if __name__ == "__main__":
    main()
