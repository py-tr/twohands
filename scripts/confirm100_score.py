"""Score the PRE-REGISTERED confirmation (PROTOCOL.md Amendment 3; gate v3 per Amendment 7) on the stored Gemma reads
of the 100 fresh forms. No model call.

    python scripts/confirm100_score.py           # -> results/confirm100.md + results/confirm100.json
    python scripts/confirm100_score.py --check   # recompute; exit 1 if the committed files differ (make eval)

Reads: results/calls_confirm100_gemma.jsonl (last row per form). Second reader: results/calls_confirm100_qwen.jsonl if it
exists; with no Qwen read, v2-2R reduces to v2 and gate v3's two-read rule (b) fails on every form (Amendment 7: "No
usable second read = (b) fails"), so every SOBRANTES goes to a person under v3.
Truth per graded field on an accepted form (Amendment 2 / section 6): a verdict in
results/adjudication_confirm100/verdicts.json decides (model_right = correct; capture_right / neither = error;
paper_ambiguous / unreadable / crop_wrong = undecided); with no verdict, read == PREP counts as correct and read != PREP
is FLAGGED (the criterion is not called while anything is flagged).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, schema  # noqa: E402
from twohands.gate import gate, iv  # noqa: E402
from twohands.gate_v2 import gate_v2  # noqa: E402
from twohands.gate_v3 import gate_v3  # noqa: E402
from twohands.run import jsonl  # noqa: E402
from twohands.sample import PREP_CSV, load_rows  # noqa: E402
from twohands.score import wilson  # noqa: E402

R = REPO / "results"
OUT_MD, OUT_JSON = R / "confirm100.md", R / "confirm100.json"
ADJ = R / "adjudication_confirm100"
EVAL_MD = REPO / "docs" / "EVALUATION.md"
CRITERION = 0.005
PRIMARY = "v2 (primary, Amendment 3)"
V3 = "v3 (Amendment 7: words + two reads + stock band)"


def last(path: Path) -> dict:
    out = {}
    for r in jsonl(path):
        out[r["clave"]] = r
    return out


def parsed_of(r, keys):
    if not r or r.get("no_call") or not r.get("parsed_ok"):
        return None
    F = r.get("fields") or {}
    return {"values": [{"label": (F.get(k) or {}).get("label"), "n": (F.get(k) or {}).get("n"),
                        "w": (F.get(k) or {}).get("w")} for k in keys]}


def pct(a, b):
    return f"{100 * a / b:.2f}%" if b else "-"


def verdict_word(o: dict) -> str:
    if o["criterion_met"] is None:
        return "criterion not yet decidable (flagged fields await adjudication)"
    return "criterion met" if o["criterion_met"] else "criterion not met"


def compute() -> dict:
    s = schema.load()
    keys = s["keys"]
    graded = [f for f in s["fields"] if f.get("csv")]
    shown = {k: f"vote row {i + 1}" for i, k in enumerate(s["vote_keys"])}
    man = json.loads((R / "manifest_confirm100.json").read_text(encoding="utf-8"))
    claves = [it["clave"] for it in man["items"]]
    layout = {it["clave"]: it["layout"] for it in man["items"]}
    prep = {r["CLAVE_CASILLA"]: r for r in load_rows(PREP_CSV)
            if r["CLAVE_CASILLA"] in set(claves) and r["TIPO_ACTA"].strip() == "2"}
    vj = ADJ / "verdicts.json"
    V = json.loads(vj.read_text(encoding="utf-8")) if vj.is_file() else {}
    G = last(R / "calls_confirm100_gemma.jsonl")
    Q = last(R / "calls_confirm100_qwen.jsonl")
    qwen_ok = {k for k, r in Q.items() if r.get("parsed_ok")}

    def paper_of(k, f):
        pv = iv(str(prep[k][f["csv"]]).strip()) if k in prep else None
        v = V.get(f"{k}__{f['key']}")
        if not v:
            return "prep", pv
        if v["verdict"] == "capture_right":
            return "v", (v["paper"] if isinstance(v.get("paper"), int) else pv)
        if v["verdict"] == "model_right":
            if isinstance(v.get("paper"), int) or v.get("paper") == "blank":
                return "v", (v["paper"] if isinstance(v["paper"], int) else None)
            return "v", ((G[k].get("fields") or {}).get(f["key"]) or {}).get("n")
        if v["verdict"] == "neither" and isinstance(v.get("paper"), int):
            return "v", v["paper"]
        return "undecided", None

    def truth(k, f, m):
        kind, pv = paper_of(k, f)
        if kind == "undecided":
            return None
        if kind == "v":
            return m == pv
        return True if m == pv else "flag"

    def sec_of(k):
        if k not in qwen_ok:
            return None
        return ((Q[k].get("fields") or {}).get("SOBRANTES") or {}).get("n")

    def qvals(k):
        if k not in qwen_ok:
            return None
        return {f: ((Q[k].get("fields") or {}).get(f) or {}).get("n") for f in keys}

    def whole(g):
        return g.accepted, g.accepted

    def v3(**kw):
        def fn(p, k):
            pr = prep.get(k, {})
            g = gate_v3(p, s, tipo=k[6], lista_nominal=iv(str(pr.get("LISTA_NOMINAL", "")).strip()),
                        allowance=iv(str(pr.get("REPRESENTANTES_PP_CI", "")).strip()), second=sec_of(k), **kw)
            return g.others_accepted, g.sobrantes_accepted
        return fn

    tiers = {
        "v1 (frozen gate, section 5)": lambda p, k: whole(gate(p, s)),
        PRIMARY: lambda p, k: whole(gate_v2(p, s, "v2")),
        "v2-2R (Qwen digits may confirm SOBRANTES)": lambda p, k: whole(gate_v2(p, s, "v2", second=qvals(k))),
        "v2b (relaxed logo-row labels, secondary)": lambda p, k: whole(gate_v2(p, s, "v2b")),
        V3: v3(),
        "v3-emax (secondary: E in [0, E_max])": v3(mode="emax"),
        "v3 part: words + stock band (no two-read rule)": v3(require_second=False),
    }
    out, mism = {}, 0
    for name, fn in tiers.items():
        o = {"forms_accepted": 0, "touchless": 0, "movil": 0, "escaner": 0, "fields": 0, "errors": [],
             "undecided": [], "flagged": [], "sob_to_person": 0, "sob_to_person_correct": [], "sob_to_person_wrong": [],
             "sob_to_person_unknown": [], "forms": []}
        for k in claves:
            p = parsed_of(G.get(k), keys)
            if p is None:
                continue
            if name.startswith("v1") and bool(G[k].get("accepted")) != gate(p, s).accepted:
                mism += 1
            others, sob = fn(p, k)
            if not others:
                continue
            o["forms_accepted"] += 1
            o["forms"].append(k)
            o[layout[k]] += 1
            o["touchless"] += bool(sob)
            for f in graded:
                m = ((G[k].get("fields") or {}).get(f["key"]) or {}).get("n")
                t = truth(k, f, m)
                pv = prep[k][f["csv"]] if k in prep else "-"
                if f["key"] == "SOBRANTES" and not sob:
                    o["sob_to_person"] += 1
                    lst = {False: "sob_to_person_wrong", True: "sob_to_person_correct"}.get(t, "sob_to_person_unknown")
                    o[lst].append(f"{k} (read {m}, PREP {pv})")
                    continue
                o["fields"] += 1
                fk = shown.get(f["key"], f["key"])
                if t is False:
                    o["errors"].append(f"{k} {fk}: read {m}, PREP {pv}, paper {paper_of(k, f)[1]}")
                elif t is None:
                    o["undecided"].append(f"{k} {fk}")
                elif t == "flag":
                    o["flagged"].append(f"{k} {fk}: read {m}, PREP {pv}")
        n_err = len(o["errors"])
        o["err_rate"] = n_err / o["fields"] if o["fields"] else None
        o["ci"] = list(wilson(n_err, o["fields"])) if o["fields"] else [0, 0]
        o["criterion_met"] = None if o["flagged"] else (o["err_rate"] is not None and o["err_rate"] <= CRITERION)
        out[name] = o
    counts: dict = {}
    for v in V.values():
        counts[v["verdict"]] = counts.get(v["verdict"], 0) + 1
    meta = {"n": len(claves), "gemma_rows": sum(1 for k in claves if k in G),
            "gemma_parsed": sum(1 for k in claves if parsed_of(G.get(k), keys)),
            "unlocated": sorted(k for k in claves if (G.get(k) or {}).get("no_call")),
            "movil": sum(layout[k] == "movil" for k in claves), "escaner": sum(layout[k] == "escaner" for k in claves),
            "qwen_parsed": len(qwen_ok), "v1_recompute_mismatches": mism, "verdicts": len(V),
            "verdict_counts": dict(sorted(counts.items()))}
    res = {"meta": meta, "tiers": out}
    res["lines"] = {"v2": line(res), "v3": line_v3(res)}
    return res


def line(res: dict) -> str:
    o = res["tiers"][PRIMARY]
    return (f"the pre-registered confirmation on 100 fresh forms: gate v2 accepted {o['forms_accepted']} forms, "
            f"{len(o['errors'])} of {o['fields']} accepted fields wrong; {verdict_word(o)}")


def line_v3(res: dict) -> str:
    o = res["tiers"][V3]
    return (f"gate v3 (Amendment 7, pre-registered before these reads) accepted the other 22 fields on "
            f"{o['forms_accepted']} forms ({o['touchless']} touchless), {len(o['errors'])} of {o['fields']} accepted "
            f"fields wrong; {verdict_word(o)}; {o['sob_to_person']} SOBRANTES sent to a person"
            + (" (no second reader was run, so the two-read rule routes every SOBRANTES)" if not res["meta"]["qwen_parsed"] else
               f" ({len(o['sob_to_person_wrong'])} of them wrong reads caught)"))


def report(res: dict) -> str:
    M, T = res["meta"], res["tiers"]
    vc = ", ".join(f"{k} {v}" for k, v in M["verdict_counts"].items()) or "none"
    L = ["# Pre-registered confirmation: gate v2 on 100 fresh forms (Amendment 3), gate v3 (Amendment 7)", "",
         "Built by `scripts/confirm100_score.py`; `make eval` recomputes it (`--check`). No model call: the stored Gemma reads",
         "(`results/calls_confirm100_gemma.jsonl`, last row per form) are gated by the frozen gate, gate v2 / v2b",
         "(`twohands/gate_v2.py`) and gate v3 (`twohands/gate_v3.py`), all committed before any read of the 100.",
         f"Manifest `results/manifest_confirm100.json` (seed 20261017; {M['movil']} Movil, {M['escaner']} Escaner).",
         f"Gemma-4-31B-IT read {M['gemma_rows']} of {M['n']}: {M['gemma_parsed']} parsed, {len(M['unlocated'])} pages "
         f"unlocated ({', '.join(M['unlocated']) or 'none'}; routed, never replaced). Unlocated pages and failed reads stay "
         "in every denominator.",
         f"Recomputed v1 vs the stored `accepted` flag: {M['v1_recompute_mismatches']} mismatches.",
         (f"Qwen3.8-27B reads: {M['qwen_parsed']} parsed." if M["qwen_parsed"] else
          "Qwen3.8-27B reads: **none** (the Qwen pass of Amendment 3 was not run). So v2-2R equals v2 here, and under "
          "gate v3 the two-read rule (b) fails on every form (\"No usable second read = (b) fails\"): **every SOBRANTES "
          "goes to a person under v3**; v3 accepts only the other 22 fields."), "",
         "**Truth (Amendment 2 / section 6).** Every graded field on an accepted form (any gate above) where Gemma",
         "disagrees with the PREP capture was adjudicated on its masked crop (`results/adjudication_confirm100/`: SHEET.md,",
         "the crops, `verdicts.json`; the certified Computos count is shown where it exists). **Adjudicator: an AI (an AI model)",
         "looking at the published crops, labelled as such**; every crop is committed for anyone to re-judge. With no",
         f"verdict, read = PREP counts as correct. Verdicts: {M['verdicts']} ({vc}).", "",
         f"**Success criterion (pre-registered, primary = Gemma single-reader v2): accepted-field error rate after "
         f"adjudication <= {100 * CRITERION:.1f}%** (Amendment 3; the same bar for v3, Amendment 7).", "",
         "| gate | forms accepted (/100) | touchless (all 23) | Movil / Escaner | accepted graded fields | errors | "
         "error rate (Wilson 95%) | undecided | flagged | SOBRANTES to a person (wrong / correct) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for name, o in T.items():
        rate = f"{100 * o['err_rate']:.2f}% ({100 * o['ci'][0]:.2f}-{100 * o['ci'][1]:.2f}%)" if o["fields"] else "-"
        L.append(f"| {name} | {o['forms_accepted']} | {o['touchless']} | {o['movil']} / {o['escaner']} | {o['fields']} | "
                 f"{len(o['errors'])} | {rate} | {len(o['undecided'])} | {len(o['flagged'])} | "
                 f"{o['sob_to_person']} ({len(o['sob_to_person_wrong'])} / {len(o['sob_to_person_correct'])}) |")
    L.append("")
    for name, o in T.items():
        L.append(f"## {name}")
        L.append("- errors: " + ("; ".join(o["errors"]) or "none"))
        L.append("- undecided (ambiguous / unreadable / crop): " + ("; ".join(o["undecided"]) or "none"))
        L.append("- flagged (read != PREP, no verdict): " + ("; ".join(o["flagged"]) or "none"))
        if o["sob_to_person_wrong"]:
            L.append("- wrong SOBRANTES caught (sent to a person): " + "; ".join(o["sob_to_person_wrong"]))
        L.append("")
    L += ["## Lines", "", f"> Confirmation: {line(res)}.", f"> Also: {line_v3(res)}.", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    res = compute()
    md, js = report(res), json.dumps(res, indent=1, ensure_ascii=False)
    if "--check" in argv:
        mism = []
        if not OUT_JSON.is_file() or json.loads(OUT_JSON.read_text(encoding="utf-8")) != json.loads(js):
            mism.append("results/confirm100.json")
        if not OUT_MD.is_file() or OUT_MD.read_text(encoding="utf-8") != md:
            mism.append("results/confirm100.md")
        if res["lines"]["v2"].lower() not in " ".join(EVAL_MD.read_text(encoding="utf-8").replace("*", "").split()).lower():
            mism.append("docs/EVALUATION.md (the confirmation line)")
        print(f"confirm100 --check: {len(mism)} mismatches" + (f" ({', '.join(mism)})" if mism else ""))
        return 1 if mism else 0
    OUT_JSON.write_text(js + "\n", encoding="utf-8")
    OUT_MD.write_text(md, encoding="utf-8")
    print(md.split("## Lines")[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
