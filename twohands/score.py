"""Score the pre-registered run (PROTOCOL.md section 7).

    python -m twohands.score            # -> results/scores.json + printed table

Truth: PREP capture of the same image; adjudicated truth = PREP overridden by results/adjudication.json
({clave: {KEY: int, "_note": ...}}). Two-reader tier: both gates pass and all 23 digit values agree.
"""
from __future__ import annotations

import json
import math
from collections import Counter

from twohands import REPO, schema
from twohands.run import jsonl
from twohands.sample import PREP_CSV, load_rows

RESULTS = REPO / "results"


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 5), round(min(1, c + h), 5)]


def num(v):
    v = (v or "").strip().replace(",", "")
    return int(v) if v.isdigit() else None


def last_rows(model_key: str) -> dict:
    out = {}
    for r in jsonl(RESULTS / f"calls_{model_key}.jsonl"):
        out[r["clave"]] = r  # the last row per clave wins (resume)
    return out


def main() -> dict:
    s = schema.load()
    man = json.loads((RESULTS / "manifest.json").read_text(encoding="utf-8"))
    claves = [it["clave"] for it in man["items"]]
    layout = {it["clave"]: it["layout"] for it in man["items"]}
    prep = {r["CLAVE_CASILLA"]: r for r in load_rows(PREP_CSV) if r["CLAVE_CASILLA"] in set(claves)}
    adj_path = RESULTS / "adjudication.json"
    ADJ = json.loads(adj_path.read_text(encoding="utf-8")) if adj_path.exists() else {}
    graded = [f for f in s["fields"] if f.get("csv")]
    truth_prep = {k: {f["key"]: num(prep[k][f["csv"]]) for f in graded} for k in claves if k in prep}
    truth_adj = {k: {f: ADJ.get(k, {}).get(f, v) for f, v in t.items()} for k, t in truth_prep.items()}
    G, Q = last_rows("gemma"), last_rows("qwen")

    def vals(r):
        return {f: (r.get("fields", {}).get(f) or {}).get("n") for f in s["keys"]}

    tiers = {
        "gemma": {k: (G.get(k, {}).get("accepted", False), vals(G.get(k, {}))) for k in claves if k in G},
        "qwen": {k: (Q.get(k, {}).get("accepted", False), vals(Q.get(k, {}))) for k in claves if k in Q},
        "two_reader": {k: (bool(G[k].get("accepted") and Q[k].get("accepted") and vals(G[k]) == vals(Q[k])),
                           vals(G[k])) for k in claves if k in G and k in Q},
    }
    rep = {}
    for name, T in tiers.items():
        acc = [k for k, (a, _) in T.items() if a]
        n_f = ok_p = ok_a = ungr = 0
        wrong_adj, prep_err = [], []
        for k in acc:
            v = T[k][1]
            for f in graded:
                tp, ta = truth_prep[k][f["key"]], truth_adj[k][f["key"]]
                if ta is None:
                    ungr += 1
                    continue
                n_f += 1
                ok_p += v[f["key"]] == tp
                ok_a += v[f["key"]] == ta
                if v[f["key"]] != ta:
                    wrong_adj.append((k, f["key"], v[f["key"]], ta))
                if tp != ta and v[f["key"]] == ta:
                    prep_err.append((k, f["key"], tp, ta))
        allright = sum(all(T[k][1][f["key"]] == truth_adj[k][f["key"]] for f in graded
                           if truth_adj[k][f["key"]] is not None) for k in acc)
        rows = G if name != "qwen" else Q
        reasons = Counter(c for k in T if not T[k][0] for c in (rows.get(k, {}).get("route_codes") or ["disagree"]))
        err = (n_f - ok_a) / n_f if n_f else None
        rep[name] = {"forms": len(T), "accepted": len(acc), "accept_rate": round(len(acc) / len(claves), 4),
                     "accept_by_layout": dict(Counter(layout[k] for k in acc)),
                     "fields_accepted_gradable": n_f, "ungradable_vs_prep": ungr,
                     "right_vs_prep": ok_p, "right_vs_adjudicated": ok_a,
                     "error_rate_adjudicated": None if err is None else round(err, 5),
                     "error_rate_ci95": wilson(n_f - ok_a, n_f), "accepted_forms_all_right": allright,
                     "wrong_after_adjudication": wrong_adj, "prep_keying_errors_caught": prep_err,
                     "route_codes": dict(reasons)}
    for m, R in (("gemma", G), ("qwen", Q)):
        rr = list(R.values())
        rep[m]["finish_reason"] = dict(Counter(r.get("finish_reason") for r in rr))
        rep[m]["parse_failures"] = sum(1 for r in rr if not r.get("no_call") and not r.get("parsed_ok"))
        lat = [r["latency_s"] for r in rr if r.get("latency_s")]
        rep[m]["mean_latency_s"] = round(sum(lat) / len(lat), 1) if lat else None
        cost = sum((r.get("cost_usd") or 0) for r in rr)
        rep[m]["cost_usd"] = round(cost, 6)
        rep[m]["cost_per_form_usd"] = round(cost / max(1, len(rr)), 7)
    g = rep.get("gemma", {})
    rep["headline"] = ("gemma" if g.get("error_rate_adjudicated") is not None and g["error_rate_adjudicated"] <= 0.005
                       else "two_reader")
    (RESULTS / "scores.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    for name in tiers:
        r = rep[name]
        print(f"{name:11s} accepted {r['accepted']}/{len(claves)}  fields {r['right_vs_adjudicated']}/{r['fields_accepted_gradable']}"
              f" (vs PREP {r['right_vs_prep']})  err {r['error_rate_adjudicated']} CI {r['error_rate_ci95']}"
              f"  PREP errors caught {len(r['prep_keying_errors_caught'])}")
    print("headline:", rep["headline"])
    return rep


if __name__ == "__main__":
    main()
