"""ONE source of truth for every judge-facing number of the pre-registered 300-form run. No model call.

    python scripts/build_headline.py
      -> app/data/headline.json                 (read by the web app: Overview, Inbox, Audit, Results)
      -> results/adjudication/SUMMARY.md        (the adjudication summary, Option NN names)
      -> results/adjudication/RECALL.md         (the recall bound on forms settled by comparison)

Inputs (read-only): results/manifest.json, results/calls_gemma.jsonl (last row per form), the PREP 2024 CSV and the
Computos 2024 CSV (data/raw, never committed), results/adjudication/verdicts.json + adjudication.jsonl +
certified.json (run scripts/certified_check.py first). Docs quote these numbers; tests/test_headline.py checks that
the app and this file agree.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, schema  # noqa: E402
from twohands.adjudicate import crop_name, label, load_comp, num  # noqa: E402
from twohands.run import jsonl  # noqa: E402
from twohands.sample import PREP_CSV, load_rows  # noqa: E402
from twohands.score import wilson  # noqa: E402

R = REPO / "results"
ADJ = R / "adjudication"
OUT = REPO / "app" / "data" / "headline.json"
CERT_COLS = {"NO_REGISTRADAS": "CANDIDATO/A NO REGISTRADO/A", "NULOS": "VOTOS NULOS", "TOTAL": "TOTAL_VOTOS_CALCULADOS",
             "PAN_PRI_PRD": "PAN_PRI_PRD", "PAN_PRI": "PAN_PRI", "PAN_PRD": "PAN_PRD", "PRI_PRD": "PRI_PRD"}
RECEIPT = ("050815B0100", "MORENA")      # model right, capture mis-keyed, certified by comparison (Cotejo)
FEATURED = "250767B0100"                 # the capture shifted sections 2-5 by one field
TYPES = [("wrong_value", "Wrong value keyed"),
         ("marked_illegible", "Legible field marked illegible"),
         ("keyed_blank", "Value keyed where the paper is blank"),
         ("other", "Other (legible field captured as \"no data\")")]


def one_in(k: int, n: int) -> int:
    return round(n / k) if k else 0


def classify(prep_raw: str, paper) -> str:
    p = (prep_raw or "").strip()
    if paper == "blank":
        return "keyed_blank"
    if p.lower().startswith("ilegible"):
        return "marked_illegible"
    if num(p) is not None:
        return "wrong_value"
    return "other"


def main() -> dict:
    s = schema.load()
    man = json.loads((R / "manifest.json").read_text(encoding="utf-8"))
    claves = [it["clave"] for it in man["items"]]
    layout = {it["clave"]: it["layout"] for it in man["items"]}
    G = {}
    n_rows = collections.Counter()
    for r in jsonl(R / "calls_gemma.jsonl"):
        G[r["clave"]] = r
        n_rows[r["clave"]] += 1
    prep = {r["CLAVE_CASILLA"]: r for r in load_rows(PREP_CSV) if r["CLAVE_CASILLA"] in set(claves)}
    comp = load_comp(set(claves))
    V = json.loads((ADJ / "verdicts.json").read_text(encoding="utf-8"))
    ledger = {f"{r['clave']}__{r['field']}": r for r in jsonl(ADJ / "adjudication.jsonl")}
    cert = json.loads((ADJ / "certified.json").read_text(encoding="utf-8"))
    graded = [f for f in s["fields"] if f.get("csv")]

    read_ok = [k for k in claves if k in G and G[k].get("parsed_ok") and not G[k].get("no_call") and k in prep]
    unread = [k for k in claves if k not in read_ok]
    accepted = [k for k in claves if k in G and G[k].get("accepted")]
    fields = len(read_ok) * len(graded)
    dis = []
    for k in read_ok:
        F = G[k].get("fields") or {}
        for f in graded:
            m, p = (F.get(f["key"]) or {}).get("n"), num(prep[k][f["csv"]])
            if m != p:
                dis.append((k, f["key"]))
    assert {f"{k}__{f}" for k, f in dis} == set(V), "verdicts.json does not cover exactly the disagreements"
    vc = collections.Counter(V[f"{k}__{f}"]["verdict"] for k, f in dis)
    acc_set = set(accepted)
    acc_dis = [(k, f) for k, f in dis if k in acc_set]
    vacc = collections.Counter(V[f"{k}__{f}"]["verdict"] for k, f in acc_dis)
    model_wrong = vc["capture_right"] + vc["neither"]
    acc_fields = len([k for k in accepted if k in read_ok]) * len(graded)
    acc_model_wrong = vacc["capture_right"] + vacc["neither"]

    # the 52 (model right = the first capture mis-keyed), with type and certified confirmation
    cert_by = {f"{c['clave']}__{c['field']}": c for c in cert["model_right"]}
    mr = []
    for k, f in sorted(dis):
        v = V[f"{k}__{f}"]
        if v["verdict"] != "model_right":
            continue
        lg = ledger.get(f"{k}__{f}", {})
        c = cert_by.get(f"{k}__{f}", {})
        mode = "Cotejo" if "Cotejo" in (c.get("obs") or "") else ("Recuento" if "Recuento" in (c.get("obs") or "") else None)
        mr.append({"clave": k, "field": f, "name": label(f), "crop": crop_name(k, f), "model": lg.get("model_n"),
                   "prep": lg.get("prep_raw"), "paper": v.get("paper"), "evidence": v.get("evidence", ""),
                   "type": classify(lg.get("prep_raw"), v.get("paper")), "accepted": k in acc_set,
                   "certified": c.get("computos"), "covered": bool(c.get("covered")), "cert_agrees": bool(c.get("agrees")),
                   "cert_mode": mode})
    by_type = collections.Counter(x["type"] for x in mr)
    cov = [x for x in mr if x["covered"]]
    agree = [x for x in cov if x["cert_agrees"]]
    differ = [x for x in cov if not x["cert_agrees"]]

    # recall bound: forms the certified count settled by comparison (Cotejo), vote rows + TOTAL
    rk = s["vote_keys"] + ["TOTAL"]
    csv_of = {f["key"]: f["csv"] for f in s["fields"]}
    E = C = 0
    cotejo_forms, e_list = [], []
    for k in read_ok:
        cp = comp.get(k)
        if not cp or "Cotejo" not in (cp.get("OBSERVACIONES") or "") or "Recuento" in (cp.get("OBSERVACIONES") or ""):
            continue
        cotejo_forms.append(k)
        F = G[k].get("fields") or {}
        for f in rk:
            cv = num(cp.get(CERT_COLS.get(f, f)))
            if cv is None:
                continue
            pv = num(prep[k][csv_of[f]])
            if cv == pv:
                continue
            E += 1
            m = (F.get(f) or {}).get("n")
            disputed = m != pv
            C += disputed
            vv = V.get(f"{k}__{f}", {})
            e_list.append({"clave": k, "field": f, "name": label(f), "prep": prep[k][csv_of[f]], "certified": cv,
                           "model": m, "disputed": disputed, "verdict": vv.get("verdict")})
    ci = wilson(C, E) if E else None

    # label gate cost (Amendment 2): label-routed forms whose read matches the paper on every graded field
    def form_right(k):
        return all(V[f"{kk}__{f}"]["verdict"] == "model_right" for kk, f in dis if kk == k)
    lab = [k for k in read_ok if "label" in (G[k].get("route_codes") or [])]
    lab_only = [k for k in lab if set(G[k].get("route_codes") or []) == {"label"}]
    lab_right = [k for k in lab if form_right(k)]
    lab_only_right = [k for k in lab_only if form_right(k)]

    # the receipt and the featured column shift
    rc = next(x for x in mr if (x["clave"], x["field"]) == RECEIPT)
    feat = [x for x in mr if x["clave"] == FEATURED]
    order = {"SOBRANTES": 0, "VOTARON": 1, "REPRESENTANTES": 2}
    feat.sort(key=lambda x: order.get(x["field"], 9))

    # cost and latency of the Gemma pass, and the endpoint-outage re-reads (appendix)
    lat = [G[k]["latency_s"] for k in read_ok if G[k].get("latency_s")]
    cost = [G[k]["cost_usd"] for k in read_ok if G[k].get("cost_usd")]
    tin = [(G[k].get("usage") or {}).get("prompt_tokens") for k in read_ok]
    tout = [(G[k].get("usage") or {}).get("completion_tokens") for k in read_ok]
    tin, tout = [x for x in tin if x], [x for x in tout if x]
    rereads = sorted(k for k in claves if n_rows[k] > 1)
    h010 = (G.get("010469C0400", {}).get("fields") or {}).get("SOBRANTES") or {}

    pct = lambda a, b, d=1: round(100 * a / b, d) if b else None  # noqa: E731
    H = {
        "about": "Pre-registered random sample of 300 INE 2024 tally sheets, Gemma-4-31B-IT on AMD, frozen gate. "
                 "Built by scripts/build_headline.py from results files; every page and doc quotes this file.",
        "forms": len(claves), "read": len(read_ok), "unread": len(unread), "unread_claves": unread,
        "graded_per_form": len(graded), "fields": fields,
        "disagree": len(dis), "disagree_forms": len({k for k, _ in dis}), "agree": fields - len(dis),
        "agree_pct": round(100 * (fields - len(dis)) / fields, 2), "flag_pct": pct(len(dis), fields),
        "accepted": len(accepted), "accepted_pct": round(100 * len(accepted) / len(claves)),
        "accepted_pct1": pct(len(accepted), len(claves)),
        "accepted_movil": sum(layout[k] == "movil" for k in accepted),
        "accepted_escaner": sum(layout[k] == "escaner" for k in accepted),
        "routed": len(claves) - len(accepted), "acc_fields": acc_fields, "acc_disagree": len(acc_dis),
        "acc_model_wrong": acc_model_wrong, "acc_model_right": vacc["model_right"],
        "acc_wrong_ci": wilson(acc_model_wrong, acc_fields),
        "verdicts": {k: vc.get(k, 0) for k in ("model_right", "capture_right", "neither", "paper_ambiguous",
                                               "unreadable", "crop_wrong")},
        "verdicts_accepted": {k: vacc.get(k, 0) for k in ("model_right", "capture_right", "neither", "paper_ambiguous",
                                                         "unreadable", "crop_wrong")},
        "model_wrong": model_wrong, "model_one_in": one_in(model_wrong, fields),
        "acc_one_in": one_in(acc_model_wrong, acc_fields),
        "keying_errors": len(mr), "keying_forms": len({x["clave"] for x in mr}),
        "cert_covered": len(cov), "cert_agree": len(agree), "cert_differ": len(differ),
        "cert_differ_recount": sum(x["cert_mode"] == "Recuento" for x in differ),
        "yield_one_in": one_in(len(mr), len(dis)), "yield_pct": pct(len(mr), len(dis)),
        "random_one_in": one_in(len(mr), fields), "yield_x": round(fields / len(dis), 1),
        "yield_x_int": round(fields / len(dis)),
        "by_type": [{"type": t, "label": lab_, "n": by_type.get(t, 0)} for t, lab_ in TYPES],
        "recall": {"forms": len(cotejo_forms), "E": E, "C": C, "ci": ci,
                   "fields": "17 vote rows + TOTAL (TOTAL compared with the certified calculated total)",
                   "list": e_list},
        "label_gate": {"routed": len(lab), "label_only": len(lab_only), "read_right": len(lab_right),
                       "label_only_right": len(lab_only_right)},
        "harmonised": {"clave": "010469C0400", "field": "SOBRANTES", "name": label("SOBRANTES"),
                       "digits": h010.get("n"), "words": h010.get("w"), "paper": V["010469C0400__SOBRANTES"]["paper"]},
        "receipt": rc, "featured": {"clave": FEATURED, "fields": feat},
        "keying_list": mr,
        "gemma": {"mean_secs": round(sum(lat) / len(lat), 1) if lat else None,
                  "cost_per_form": sum(cost) / len(cost) if cost else None, "reads": len(read_ok),
                  "stop": sum(G[k].get("finish_reason") == "stop" for k in read_ok),
                  "tokens_in": round(sum(tin) / len(tin)) if tin else None,
                  "tokens_out": round(sum(tout) / len(tout)) if tout else None},
        "rereads": {"forms": len(rereads), "rows": sum(n_rows.values()),
                    "note": "forms whose first call failed during endpoint outages (HTTP 503) and were re-read later "
                            "with the same frozen prompt; the last read of each form counts"},
    }
    OUT.write_text(json.dumps(H, indent=1, ensure_ascii=False), encoding="utf-8")
    write_summary(H, dis, V, ledger, acc_set)
    write_recall(H)
    print(json.dumps({k: H[k] for k in ("read", "fields", "disagree", "agree_pct", "accepted", "acc_fields",
                                         "acc_model_wrong", "model_wrong", "model_one_in", "acc_one_in", "keying_errors",
                                         "cert_covered", "cert_agree", "cert_differ", "yield_one_in", "random_one_in",
                                         "yield_x", "verdicts")}, indent=0))
    print("by type", [(t["type"], t["n"]) for t in H["by_type"]])
    print("recall", {k: v for k, v in H["recall"].items() if k != "list"})
    print("label gate", H["label_gate"])
    return H


def _vline(v: dict) -> str:
    s = (f"model right {v['model_right']}, capture right {v['capture_right']}, ambiguous {v['paper_ambiguous']}, "
         f"unreadable {v['unreadable']}")
    if v["neither"]:
        s += f"; plus neither {v['neither']} (paper shows a third value: model wrong, capture also off)"
    if v["crop_wrong"]:
        s += f", crop to redo {v['crop_wrong']}"
    return s


def write_summary(H, dis, V, ledger, acc_set) -> None:
    def row(k, f):
        v, lg = V[f"{k}__{f}"], ledger.get(f"{k}__{f}", {})
        c = lg.get("computos")
        return (f"| {k} | {label(f)} | {lg.get('model_n')} | {lg.get('prep_raw')} | {'-' if c is None else c} | "
                f"{v['verdict']} | {v.get('evidence', '').replace('|', '/')} | [crop]({crop_name(k, f)}) |")
    head = ["| clave | field | model | PREP | Computos | verdict | evidence (what is written on the paper) | crop |",
            "|---|---|---|---|---|---|---|---|"]
    vt = H["verdicts"]
    va = H["verdicts_accepted"]
    routed_v = {k: vt[k] - va[k] for k in vt}
    acc_d = [(k, f) for k, f in dis if k in acc_set]
    L = ["# Second-keyer adjudication: Gemma vs the official PREP capture (Amendment 2 b)", "",
         "**Adjudicated by a reviewer looking at the published crops; every crop is in results/adjudication/ for anyone to check.**",
         "Secondary analysis (Amendment 2). Crops are cut from masked pages only. The verdict is decided from what is written on the",
         "paper (digit boxes and words); the certified Computos value is shown only as a secondary note and never overrides the paper.",
         "Per-field verdicts and evidence: `verdicts.json`, `adjudication.jsonl`, `SHEET.md`. Vote rows are named Option 01 to",
         "Option 15 in printed order; the machine files keep INE's column names. Generated by `scripts/build_headline.py`.", "",
         "## Totals", "",
         f"- Gemma reads in the final pass: {H['forms']} forms; parseable and matched to PREP: **{H['read']} forms**, "
         f"{H['graded_per_form']} graded fields each = **{H['fields']} fields read**.",
         f"  ({H['unread']} forms had no usable read: {', '.join(H['unread_claves'])}.)",
         f"- Fields where Gemma's digits differ from the PREP capture: **{H['disagree']}** ({H['flag_pct']}%) on "
         f"{H['disagree_forms']} forms; agreement {H['agree']}/{H['fields']} = {H['agree_pct']:.2f}%.", "",
         "## Verdicts", "", "| verdict | fields | meaning |", "|---|---|---|",
         f"| model_right | {vt['model_right']} | paper shows the model's value: the official capture mis-keyed (or marked a legible field Ilegible / keyed a blank field) |",
         f"| capture_right | {vt['capture_right']} | paper shows the capture's value: the model misread |",
         f"| neither | {vt['neither']} | paper shows a third value: model wrong, capture also off (mostly capture marked Ilegible) |",
         f"| paper_ambiguous | {vt['paper_ambiguous']} | words and digit boxes disagree on the paper, a correction makes both defensible, or a blank row (blank vs 0) |",
         f"| unreadable | {vt['unreadable']} | the crop does not let a careful person decide |",
         f"| crop_wrong | {vt['crop_wrong']} | the crop does not show the written value (the 3 crops of 151606C0100 were redone lower and judged: capture right) |",
         "", "## The second-keyer line", "", "All forms with a parseable read (accepted or routed):", "",
         f"> On {H['read']} forms ({H['fields']} fields) the model agreed with the official capture on all but {H['disagree']}; "
         f"the image settled {H['disagree']}: {_vline(vt)}.", "",
         "Accepted (touchless) forms only:", "",
         f"> On {H['accepted']} forms ({H['acc_fields']} fields) the model agreed with the official capture on all but "
         f"{H['acc_disagree']}; the image settled {H['acc_disagree']}: {_vline(va)}.", "",
         "Routed forms only:", "",
         f"> On {H['read'] - H['accepted']} forms ({H['fields'] - H['acc_fields']} fields) the model agreed with the official "
         f"capture on all but {H['disagree'] - H['acc_disagree']}; the image settled {H['disagree'] - H['acc_disagree']}: "
         f"{_vline(routed_v)}.", "",
         "## Rates", "",
         f"- The model alone is wrong (paper shows it wrong) on {H['model_wrong']} of {H['fields']} fields "
         f"({vt['capture_right']} capture right + {vt['neither']} neither): about 1 in {H['model_one_in']}.",
         f"- On the {H['accepted']} forms the gate accepted ({H['accepted_pct']}% of {H['forms']}): {H['acc_model_wrong']} of "
         f"{H['acc_fields']} fields wrong, about 1 in {H['acc_one_in']}.",
         f"- Of the {H['disagree']} fields the model disputes, {H['keying_errors']} are confirmed keying errors "
         f"({H['yield_pct']}%, about 1 in {H['yield_one_in']}); at random it would be {H['keying_errors']} of {H['fields']} "
         f"(about 1 in {H['random_one_in']}): up to {H['yield_x_int']}x the yield. Recall is bounded in `RECALL.md`.", "",
         f"## Disagreements on ACCEPTED forms ({H['acc_disagree']} fields on {len({k for k, _ in acc_d})} of {H['accepted']} accepted forms)", ""]
    L += head + [row(k, f) for k, f in acc_d] + [""]
    L += [f"## The {H['keying_errors']} keying errors by type", "", "| type | fields |", "|---|---|"]
    L += [f"| {t['label']} | {t['n']} |" for t in H["by_type"]] + [""]
    L += [f"Certified count: covers {H['cert_covered']} of the {H['keying_errors']}, agrees with the image on "
          f"{H['cert_agree']}; all {H['cert_differ']} differences were recounts (`CERTIFIED.md`).", ""]
    L += [f"## All model_right cases (A = {H['keying_errors']}: capture errors found by the model)", ""] + head
    L += [row(x["clave"], x["field"]) for x in H["keying_list"]] + [""]
    lg_ = H["label_gate"]
    L += ["## Label-gate false alarms", "",
          f"Forms routed by the row-label check: **{lg_['routed']}** ({lg_['label_only']} where the label was the only cause).", "",
          f"- Read matches the paper on every graded field after adjudication (every disagreement is model_right): "
          f"**{lg_['read_right']}** of {lg_['routed']} ({lg_['label_only_right']} of {lg_['label_only']} label-only).", ""]
    (ADJ / "SUMMARY.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def write_recall(H) -> None:
    r = H["recall"]
    ci = r["ci"] or [0, 0]
    L = ["# Recall bound: how many capture errors does the model dispute?", "",
         "**A bound, not a measurement.** Secondary analysis (Amendment 2), computed by `scripts/build_headline.py`.", "",
         f"Forms: the {r['forms']} of the {H['read']} read forms whose certified count (Computos Distritales 2024) was settled "
         "by comparison with the tally sheet (OBSERVACIONES \"Cotejo\"), not by a recount of the ballots.",
         f"Fields: {r['fields']}. E = fields where the certified value differs from the first capture (PREP, including "
         "fields PREP marked Ilegible or left without data). C = how many of those E the model disputed (its digits differ "
         "from PREP).", "",
         f"> On the forms the certified count settled without a recount, the model had disputed {r['C']} of the {r['E']} "
         f"fields where the certified count disagrees with the first capture "
         f"({100 * r['C'] / r['E']:.0f}%, Wilson 95% {100 * ci[0]:.0f}% to {100 * ci[1]:.0f}%)." if r["E"] else "> No such field.",
         "",
         "Why only a bound: a certified value can differ from the first capture for reasons other than a keying error (the "
         "district council can correct a sheet during the comparison, and TOTAL is compared with the certified CALCULATED "
         "total, which differs from the written total whenever the paper's rows do not add up). E is therefore an upper "
         "bound on the keying errors among these fields, and C/E a lower bound on the share the model would surface.", "",
         "| clave | field | PREP | certified | model | disputed | verdict |", "|---|---|---|---|---|---|---|"]
    for x in r["list"]:
        L.append(f"| {x['clave']} | {x['name']} | {x['prep']} | {x['certified']} | {x['model']} | "
                 f"{'yes' if x['disputed'] else 'no'} | {x['verdict'] or '-'} |")
    (ADJ / "RECALL.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
