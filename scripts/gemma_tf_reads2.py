"""PROTOCOL.md Amendment 8 (read B: Gemma page + 4 tiles on the 300) and Amendment 8b (Colima, whole state), on the
AMD Token Factory, and their scoring.

    python scripts/gemma_tf_reads2.py b4             # read B -> results/calls_gemma_b4.jsonl (resumable by clave)
    python scripts/gemma_tf_reads2.py colima         # Colima -> results/colima/calls_gemma.jsonl (resumable by clave)
    python scripts/gemma_tf_reads2.py score-b4       # -> results/gemma_b4_300.json + .md (no model call)
    python scripts/gemma_tf_reads2.py score-colima   # -> results/colima/colima_audit.json + .md + audit report (no model call)

Reads refuse to start unless the amendment is committed at HEAD with PROTOCOL.md unchanged (they wait up to 2 h for a
clean working copy, since another session may be editing it). Budget: twohands.amd.chat's bulk share
(TWOHANDS_BULK_DAILY_USD) and run.Budget's whole-key cap (TWOHANDS_MAX_DAILY_USD, default 0.80, as twohands.run).
Calls with an API error are retried in later passes (up to 12), as twohands.run does. Log: results/gemma_tf_runs2.log.

Scoring never calls a model. A disagreement with the capture on an accepted field that no verdict covers is settled by
the certified count where it applies (vote row or TOTAL, Computos cotejo, not a recount; recorded automatically with
"by": "certified count"); the rest get a crop of the masked page and are listed as pending for the AI adjudicator
(results/adjudication/amendment8_pending.json; results/colima/pending.json). Verdicts written by the adjudicator go to
results/adjudication/verdicts_amendment8.json and results/colima/verdicts.json ("by": "AI adjudicator" | "person" |
"certified count"); re-run the score afterwards. No error count is called final while anything is pending.
"""
from __future__ import annotations

import argparse
import collections
import copy
import csv
import io
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from twohands import reader, run, schema as schemamod  # noqa: E402
from twohands.gate import gate, iv  # noqa: E402
from twohands.gate_v2 import gate_v2  # noqa: E402
from twohands.gate_v3 import gate_v3  # noqa: E402
from twohands.score import wilson  # noqa: E402
from twohands.tiers import digits, two_reader, usable  # noqa: E402

R = REPO / "results"
LOG = R / "gemma_tf_runs2.log"
B4 = R / "calls_gemma_b4.jsonl"
COLIMA = R / "colima"
TILES_B = 4
ADJ = R / "adjudication"
V8 = ADJ / "verdicts_amendment8.json"
CERT_COLS = {"NO_REGISTRADAS": "CANDIDATO/A NO REGISTRADO/A", "NULOS": "VOTOS NULOS", "TOTAL": "TOTAL_VOTOS_CALCULADOS"}
KNOWN = ("model_right", "capture_right", "neither", "paper")
_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now()} {msg}"
    with _lock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def schema_b4() -> dict:
    s = copy.deepcopy(schemamod.load())
    s["layout"]["tiles"] = s["layout"]["tiles"][:TILES_B]
    return s


def last(path: Path) -> dict:
    return {r["clave"]: r for r in run.jsonl(path) if r.get("clave")}


def jload(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else default


def committed(needle: str) -> bool:
    try:
        head = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:PROTOCOL.md"], capture_output=True, check=True).stdout
        dirty = subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", "HEAD", "--", "PROTOCOL.md"]).returncode != 0
    except Exception:  # noqa: BLE001
        return False
    return needle.encode() in head and not dirty


def wait_committed(needle: str) -> bool:
    for i in range(13):
        if committed(needle):
            return True
        log(f"waiting: PROTOCOL.md at HEAD must contain {needle!r} with no uncommitted edits ({i + 1}/13)")
        time.sleep(600)
    return False


# ------------------------------------------------------------------------------------------------------------ reads
def read_all(tag: str, items: list[dict], prepared: dict, s: dict, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    budget = run.Budget(float(os.environ.get("TWOHANDS_MAX_DAILY_USD", "0.80")))
    budget.check(force=True)
    workers = int(os.environ.get("TWOHANDS_WORKERS", "2"))
    log(f"{tag}: start, {len(items)} forms, prompt {reader.prompt_sha256(s)}, tiles {len(s['layout']['tiles'])}, "
        f"out {path.relative_to(REPO).as_posix()}, pid {os.getpid()}")
    todo: list = []
    for p in range(12):
        have = {r["clave"] for r in run.jsonl(path) if not r.get("error")}
        todo = [it for it in items if it["clave"] not in have]
        if not todo:
            break
        log(f"{tag}: pass {p + 1}, {len(have)} done, {len(todo)} to read")
        n = {"i": 0}
        t0 = time.time()

        def work(it, todo=todo, n=n, t0=t0):
            prep = prepared.get(it["clave"]) or {"status": "missing", "reason": "no prepare row"}
            if prep.get("status") != "ok":
                rec = run.record(it, prep, "gemma", s, None)
            else:
                budget.check()
                rec = run.record(it, prep, "gemma", s, reader.read("gemma", REPO / prep["image"], s))
            run.append(path, rec)
            with _lock:
                n["i"] += 1
                i = n["i"]
            eta = (time.time() - t0) / i * (len(todo) - i) / 3600
            log(f"{tag} {it['clave']} {'ACCEPT' if rec['accepted'] else 'route'} {rec.get('finish_reason')} "
                f"{rec.get('latency_s')}s err={bool(rec.get('error'))} [{i}/{len(todo)}, eta {eta:.1f} h]")
            if rec.get("error"):
                time.sleep(300)

        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(work, todo))
    have = {r["clave"] for r in run.jsonl(path) if not r.get("error")}
    left = [it["clave"] for it in items if it["clave"] not in have]
    log(f"{tag}: complete, {len(have)} rows, {len(left)} not read{(': ' + ' '.join(left[:20])) if left else ''}")
    return 0 if not left else 4


def cmd_b4(_a) -> int:
    if not wait_committed("## Amendment 8 ("):
        log("b4: REFUSING, Amendment 8 not committed")
        return 3
    man = jload(R / "manifest.json", {})["items"]
    prepared = last(R / "prepare.jsonl")
    return read_all("gemma_b4", man, prepared, schema_b4(), B4)


def colima_prepared() -> dict:
    return last(R / "prepare_state06.jsonl")


def cmd_colima(_a) -> int:
    if not wait_committed("## Amendment 8b ("):
        log("colima: REFUSING, Amendment 8b not committed")
        return 3
    prepared = {k: r for k, r in colima_prepared().items() if r.get("status") == "ok"}
    items = [{"clave": k, "layout": (r.get("info") or {}).get("layout") or "unknown",
              "stratum": f"state06|{(r.get('info') or {}).get('layout') or 'unknown'}"} for k, r in sorted(prepared.items())]
    return read_all("colima", items, prepared, schemamod.load(), COLIMA / "calls_gemma.jsonl")


# ---------------------------------------------------------------------------------------------------------- scoring
def paper_of(v: dict):
    """(status, paper) of a verdict: known | undecided."""
    if v["verdict"] not in KNOWN:
        return "undecided", None
    p = v.get("paper")
    if p == "blank":
        return "known", None
    if isinstance(p, int):
        return "known", p
    return "undecided", None


class Truth:
    """Truth per (clave, field): a verdict (in the order of ``sources``), else the capture (read == capture = right)."""

    def __init__(self, sources: list[dict], prep: dict, s: dict):
        self.sources, self.prep = sources, prep
        self.csv = {f["key"]: f["csv"] for f in s["fields"] if f.get("csv")}

    def capture(self, k, f):
        return iv(str((self.prep.get(k) or {}).get(self.csv[f], "")).strip())

    def verdict(self, k, f):
        for src in self.sources:
            v = src.get(f"{k}__{f}")
            if v:
                return v
        return None

    def judge(self, k, f, value) -> str:
        v = self.verdict(k, f)
        if v:
            st, p = paper_of(v)
            if st == "undecided":
                return "undecided"
            return "right" if value == p else "wrong"
        return "right" if value == self.capture(k, f) else "pending"


def settle(pending: set, T: Truth, s: dict, store: dict, page_of, crop_dir: Path, reads_of) -> list[dict]:
    """Certified count for what it covers (written to ``store``), crops for the AI adjudicator for the rest."""
    from twohands.adjudicate import COMP_ALIAS, boxes, crop, crop_name, load_comp
    comp = load_comp({x.split("__")[0] for x in pending})
    fs = {f["key"]: f for f in s["fields"]}
    bx = boxes(s)
    out = []
    for x in sorted(pending):
        k, f = x.split("__")
        cp = comp.get(k) or {}
        col = CERT_COLS.get(f, COMP_ALIAS.get(fs[f]["csv"], fs[f]["csv"])) if (fs[f].get("vote") or f == "TOTAL") else None
        cval = iv(str(cp.get(col, "")).strip()) if (cp and col) else None
        obs = (cp.get("OBSERVACIONES") or "").strip()
        reads = reads_of(k, f)
        if cval is not None and "Recuento" not in obs:
            store[x] = {"form_id": k, "field": f, "verdict": "paper", "paper": cval, "by": "certified count",
                        "evidence": f"Computos {col} = {cval} ({obs or 'cotejo'}); capture {T.capture(k, f)}; reads {reads}"}
            continue
        page = page_of(k)
        cpath = crop_dir / crop_name(k, f)
        if page and page.is_file() and not cpath.exists():
            cpath.parent.mkdir(parents=True, exist_ok=True)
            crop(page, bx[f], cpath)
        out.append({"key": x, "crop": cpath.relative_to(REPO).as_posix(), "capture": T.capture(k, f),
                    "computos": cval, "computos_obs": obs, "reads": reads})
    return out


def tier_errors(acc: list, src: dict, T: Truth, graded: list, keys: list) -> dict:
    n, res, wrong, pend = 0, collections.Counter(), [], []
    for k in acc:
        d = digits(src[k], keys)
        for f in graded:
            n += 1
            j = T.judge(k, f, d[f])
            res[j] += 1
            if j == "wrong":
                wrong.append(f"{k}__{f} read {d[f]}, capture {T.capture(k, f)}")
            elif j == "pending":
                pend.append(f"{k}__{f}")
    return {"fields": n, "errors": res["wrong"], "undecided": res["undecided"], "pending": len(pend),
            "ci": list(wilson(res["wrong"], n)) if n else None, "wrong": wrong, "pending_fields": pend}


def cmd_score_b4(_a) -> int:
    s = schemamod.load()
    keys = s["keys"]
    graded = [f["key"] for f in s["fields"] if f.get("csv")]
    man = jload(R / "manifest.json", {})["items"]
    claves = [it["clave"] for it in man]
    layout = {it["clave"]: it["layout"] for it in man}
    A, B, Q = last(R / "calls_gemma.jsonl"), last(B4), last(R / "calls_qwen.jsonl")
    with (REPO / "app" / "data" / "audit_sample_prep300.csv").open(encoding="utf-8", newline="") as fh:
        prep = {r["CLAVE_CASILLA"]: r for r in csv.DictReader(fh)}
    store = jload(V8, {})
    T = Truth([jload(ADJ / "verdicts.json", {}), jload(ADJ / "verdicts_bakeoff.json", {}), store], prep, s)

    def frozen(r):
        return bool(usable(r) and r.get("accepted"))

    rules = {"gemma_gemma": (A, lambda k: two_reader(A.get(k), B.get(k), s)[0]),
             "gemma_qwen": (A, lambda k: two_reader(A.get(k), Q.get(k), s)[0]),
             "gemma_6tiles_alone": (A, lambda k: frozen(A.get(k))),
             "gemma_4tiles_alone": (B, lambda k: frozen(B.get(k)))}

    def compute():
        out = {}
        for name, (src, rule) in rules.items():
            acc = [k for k in claves if rule(k)]
            out[name] = {"accepted": len(acc), "movil": sum(layout[k] == "movil" for k in acc),
                         "escaner": sum(layout[k] == "escaner" for k in acc), "forms": acc,
                         **tier_errors(acc, src, T, graded, keys)}
        return out

    tiers = compute()
    want = set()
    for t in tiers.values():
        want |= set(t["pending_fields"])
    pending = settle(want, T, s, store, lambda k: REPO / "data" / "masked" / f"{k}.jpg", ADJ,
                     lambda k, f: {"A_6tiles": digits(A.get(k), keys).get(f), "B_4tiles": digits(B.get(k), keys).get(f),
                                   "qwen": digits(Q.get(k), keys).get(f) if usable(Q.get(k)) else None})
    V8.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ADJ / "amendment8_pending.json").write_text(json.dumps(pending, indent=1) + "\n", encoding="utf-8")
    tiers = compute()

    def shared(X, Y):
        both_wrong_same, one_wrong, pend_same = [], 0, 0
        for k in claves:
            if not (usable(X.get(k)) and usable(Y.get(k))):
                continue
            dx, dy = digits(X[k], keys), digits(Y[k], keys)
            for f in graded:
                jx, jy = T.judge(k, f, dx[f]), T.judge(k, f, dy[f])
                if jx == "wrong" and jy == "wrong" and dx[f] == dy[f]:
                    both_wrong_same.append(f"{k}__{f} both read {dx[f]}")
                elif (jx == "wrong") != (jy == "wrong") and "pending" not in (jx, jy):
                    one_wrong += 1
                elif jx == jy == "pending" and dx[f] == dy[f]:
                    pend_same += 1
        return {"both_wrong_same_value": len(both_wrong_same), "list": both_wrong_same, "only_one_wrong": one_wrong,
                "both_same_vs_capture_not_adjudicated": pend_same}

    def agreement(X, forms):
        n = agree = 0
        for k in forms:
            d = digits(X[k], keys)
            for f in graded:
                c = T.capture(k, f)
                if c is None:
                    continue
                n += 1
                agree += d[f] == c
        return {"fields": n, "agree": agree, "rate": agree / n if n else None}

    pa = [k for k in claves if usable(A.get(k))]
    pb = [k for k in claves if usable(B.get(k))]
    both = [k for k in pa if k in set(pb)]

    def cost_lat(X):
        rows = [X[k] for k in claves if k in X and not X[k].get("no_call")]
        lat = [r["latency_s"] for r in rows if r.get("latency_s")]
        return {"cost_usd": round(sum(r.get("cost_usd") or 0 for r in rows), 5),
                "mean_latency_s": round(sum(lat) / len(lat), 1) if lat else None}

    res = {"amendment": "PROTOCOL.md Amendment 8 (secondary; the primary is unchanged)", "ts": now(),
           "prompt_sha256": {"A_6tiles": reader.prompt_sha256(s), "B_4tiles": reader.prompt_sha256(schema_b4())},
           "rows": {"A": sum(k in A for k in claves), "B": sum(k in B for k in claves), "B_parsed": len(pb),
                    "A_parsed": len(pa), "B_missing": [k for k in claves if k not in B]},
           "a_two_reader": {"gemma_gemma": tiers["gemma_gemma"], "gemma_qwen": tiers["gemma_qwen"],
                            "reported_gemma_qwen": "89 forms, 0 wrong of 1,958 (results/two_reader_300.md)",
                            "shared_mistakes": {"gemma_gemma": shared(A, B), "gemma_qwen": shared(A, Q)}},
           "b_tiling": {"agreement_both_parsed": {"A_6tiles": agreement(A, both), "B_4tiles": agreement(B, both),
                                                  "forms": len(both)},
                        "agreement_own_parsed": {"A_6tiles": agreement(A, pa), "B_4tiles": agreement(B, pb)},
                        "A_6tiles": tiers["gemma_6tiles_alone"], "B_4tiles": tiers["gemma_4tiles_alone"],
                        "cost_latency": {"A_6tiles": cost_lat(A), "B_4tiles": cost_lat(B)}},
           "pending_adjudication": len(pending)}
    (R / "gemma_b4_300.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (R / "gemma_b4_300.md").write_text(md_b4(res), encoding="utf-8")
    print(md_b4(res).split("\n\n")[1])
    return 0


def _t(t: dict) -> str:
    ci = f"{100 * t['ci'][0]:.2f}% to {100 * t['ci'][1]:.2f}%" if t.get("ci") else "-"
    return (f"| {t['accepted']} | {t['movil']} / {t['escaner']} | {t['fields']:,} | {t['errors']} ({ci}) | "
            f"{t['pending']} | {t['undecided']} |")


def md_b4(d: dict) -> str:
    a, b = d["a_two_reader"], d["b_tiling"]
    gg, gq = a["gemma_gemma"], a["gemma_qwen"]
    sm = a["shared_mistakes"]["gemma_gemma"]
    head = (f"**Gemma+Gemma (page + 6 / page + 4 tiles): {gg['accepted']} forms, {gg['errors']} wrong of {gg['fields']:,} "
            f"accepted fields{' (' + str(gg['pending']) + ' awaiting adjudication: not final)' if gg['pending'] else ''}; "
            f"Gemma+Qwen: {gq['accepted']} forms, {gq['errors']} wrong of {gq['fields']:,}.**")
    L = ["# Two Gemma reads as the two hands, and the tiling ablation (PROTOCOL.md Amendment 8, secondary)", "", head, "",
         "A secondary analysis, pre-registered before read B existed; the primary is unchanged; reported whatever it shows.",
         f"Read A = the stored Gemma-4-31B-IT reads of the 300 (page + 6 tiles, prompt `{d['prompt_sha256']['A_6tiles'][:12]}`); "
         f"read B = Gemma-4-31B-IT on the Token Factory, page + 4 tiles, temperature 0 (prompt `{d['prompt_sha256']['B_4tiles'][:12]}`). "
         f"Rows: A {d['rows']['A']} ({d['rows']['A_parsed']} parsed), B {d['rows']['B']} ({d['rows']['B_parsed']} parsed).", "",
         "## (a) Two-reader tier (Amendment 2 d)", "",
         "| tier | accepted | Movil / Escaner | accepted fields | wrong (Wilson 95%) | awaiting adjudication | paper does not settle |",
         "|---|---|---|---|---|---|---|",
         "| Gemma+Gemma (A + B) " + _t(gg), "| Gemma+Qwen (A + Qwen) " + _t(gq), "",
         f"As reported before: {a['reported_gemma_qwen']}.", "",
         f"Shared mistakes (both reads wrong with the same value): Gemma+Gemma {sm['both_wrong_same_value']}, "
         f"Gemma+Qwen {a['shared_mistakes']['gemma_qwen']['both_wrong_same_value']}; only one read wrong: Gemma+Gemma "
         f"{sm['only_one_wrong']}, Gemma+Qwen {a['shared_mistakes']['gemma_qwen']['only_one_wrong']}.",
         ("**Same-model reads share mistakes**: " + "; ".join(sm["list"])) if sm["both_wrong_same_value"] else
         "No shared same-value mistake between the two Gemma reads among adjudicated fields.", "",
         "## (b) Tiling ablation: page + 4 vs page + 6 tiles, same forms", "",
         "| read | field agreement with the capture (both parsed) | accepted, frozen gate | accepted fields | wrong (Wilson 95%) | awaiting | cost | mean latency |",
         "|---|---|---|---|---|---|---|---|"]
    for k, lab in (("A_6tiles", "page + 6 tiles (A)"), ("B_4tiles", "page + 4 tiles (B)")):
        ag, t, cl = b["agreement_both_parsed"][k], b[k], b["cost_latency"][k]
        rate = f"{100 * ag['rate']:.2f}%" if ag["rate"] is not None else "-"
        ci = f"{100 * t['ci'][0]:.2f}% to {100 * t['ci'][1]:.2f}%" if t.get("ci") else "-"
        L.append(f"| {lab} | {ag['agree']:,} / {ag['fields']:,} ({rate}) | {t['accepted']} / 300 | {t['fields']:,} | "
                 f"{t['errors']} ({ci}) | {t['pending']} | ${cl['cost_usd']} | {cl['mean_latency_s']} s |")
    L += ["", f"Forms both reads parsed: {b['agreement_both_parsed']['forms']}. Pending adjudication: "
          f"{d['pending_adjudication']} fields (`results/adjudication/amendment8_pending.json`); the AI adjudicator's verdicts "
          "go to `results/adjudication/verdicts_amendment8.json`, labelled by who decided.", ""]
    return "\n".join(L)


def cmd_score_colima(a) -> int:
    s = schemamod.load()
    keys = s["keys"]
    graded = [f["key"] for f in s["fields"] if f.get("csv")]
    prepared = colima_prepared()
    G = last(COLIMA / "calls_gemma.jsonl")
    from twohands.sample import PREP_CSV, load_rows
    rows = [r for r in load_rows(PREP_CSV) if r["CLAVE_CASILLA"].strip("'")[:2] == "06"
            and str(r.get("TIPO_ACTA", "")).strip() == "2"]
    prep = {r["CLAVE_CASILLA"].strip("'"): r for r in rows}
    ok = sorted(k for k, r in prepared.items() if r.get("status") == "ok")
    layout = {k: (prepared[k].get("info") or {}).get("layout") or "unknown" for k in ok}
    read = [k for k in ok if usable(G.get(k))]
    store = jload(COLIMA / "verdicts.json", {})
    T = Truth([store], prep, s)
    others = set()
    for name in ("manifest.json", "manifest_confirm100.json"):
        others |= {it["clave"] for it in jload(R / name, {}).get("items", [])}

    def parsed(k):
        F = G[k].get("fields") or {}
        return {"values": [{"label": (F.get(x) or {}).get("label"), "n": (F.get(x) or {}).get("n"),
                            "w": (F.get(x) or {}).get("w")} for x in keys]}

    def v3(k):
        pr = prep.get(k, {})
        g = gate_v3(parsed(k), s, tipo=k[6], lista_nominal=iv(str(pr.get("LISTA_NOMINAL", "")).strip()),
                    allowance=iv(str(pr.get("REPRESENTANTES_PP_CI", "")).strip()), second=None)
        return g.others_accepted, g.sobrantes_accepted

    gates = {"v1 (frozen gate, primary)": lambda k: (gate(parsed(k), s).accepted,) * 2,
             "v2 (Amendment 3)": lambda k: (gate_v2(parsed(k), s, "v2").accepted,) * 2,
             "v3 (Amendment 7; no second reader, so SOBRANTES always to a person)": v3}

    def compute():
        out = {}
        for name, fn in gates.items():
            o = {"forms_accepted": 0, "touchless": 0, "movil": 0, "escaner": 0, "fields": 0, "errors": [],
                 "pending": [], "undecided": 0, "route_causes": collections.Counter()}
            for k in read:
                oth, sob = fn(k)
                if not oth:
                    for c in G[k].get("route_codes") or []:
                        o["route_causes"][c] += 1
                    continue
                o["forms_accepted"] += 1
                o["touchless"] += bool(sob)
                o[layout[k]] = o.get(layout[k], 0) + 1
                d = digits(G[k], keys)
                for f in graded:
                    if f == "SOBRANTES" and not sob:
                        continue
                    o["fields"] += 1
                    j = T.judge(k, f, d[f])
                    if j == "wrong":
                        o["errors"].append(f"{k}__{f} read {d[f]}, capture {T.capture(k, f)}")
                    elif j == "pending":
                        o["pending"].append(f"{k}__{f}")
                    elif j == "undecided":
                        o["undecided"] += 1
            o["ci"] = list(wilson(len(o["errors"]), o["fields"])) if o["fields"] else None
            o["route_causes"] = dict(o["route_causes"].most_common())
            out[name] = o
        return out

    # every disagreement with the capture on a graded field of a read form, labelled
    dis = {f"{k}__{f}" for k in read for f in graded if digits(G[k], keys)[f] != T.capture(k, f)}
    pending = settle({x for x in dis if x not in store}, T, s, store,
                     lambda k: REPO / (prepared[k].get("image") or ""), COLIMA / "crops",
                     lambda k, f: {"gemma": digits(G.get(k), keys).get(f)})
    COLIMA.mkdir(parents=True, exist_ok=True)
    (COLIMA / "verdicts.json").write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (COLIMA / "pending.json").write_text(json.dumps(pending, indent=1) + "\n", encoding="utf-8")
    labels = collections.Counter()
    for x in dis:
        v = store.get(x)
        if not v:
            labels["awaiting the AI adjudicator"] += 1
            continue
        by = v.get("by", "AI adjudicator")
        st, p = paper_of(v)
        if st == "undecided":
            labels["paper ambiguous or unreadable"] += 1
            continue
        k, f = x.split("__")
        side = "model right (capture error)" if digits(G[k], keys)[f] == p else (
            "capture right (model misread)" if T.capture(k, f) == p else "neither")
        lab = {"certified count": "confirmed by the certified count", "person": "confirmed by a person"}.get(
            by, "AI adjudicator's reading")
        labels[f"{lab}: {side}"] += 1
    res = {"amendment": "PROTOCOL.md Amendment 8b", "ts": now(), "prep_rows": len(prep), "located": len(ok),
           "rows": sum(k in G for k in ok), "read": len(read), "not_read": [k for k in ok if k not in G],
           "no_image_or_not_located": sorted(k for k in prep if k not in set(ok)),
           "also_in_other_sets": sorted(k for k in ok if k in others),
           "disagreements": len(dis), "labels": dict(sorted(labels.items())), "gates": compute(),
           "complete": all(k in G for k in ok)}
    if not a.no_report:
        try:
            res["audit_report"] = audit_report(prep, rows)
        except Exception as e:  # noqa: BLE001
            res["audit_report"] = {"error": f"{type(e).__name__}: {e}"}
    (COLIMA / "colima_audit.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (COLIMA / "colima_audit.md").write_text(md_colima(res), encoding="utf-8")
    print(md_colima(res).split("\n\n")[1])
    return 0


def audit_report(prep: dict, rows: list[dict]) -> dict:
    """The /audit/new report generator on Colima: PREP's first capture as the keyed CSV, Gemma's Colima reads as the
    stored reads (app.capture_audit.STORED_RUN pointed at results/colima/calls_gemma.jsonl for this process only)."""
    from fastapi.testclient import TestClient
    from app import capture_audit as ca
    from app.main import app
    ca.STORED_RUN = COLIMA / "calls_gemma.jsonl"
    s = schemamod.load()
    cols = [f["csv"] for f in s["fields"] if f.get("csv")]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["CLAVE_CASILLA"] + cols)
    for k in sorted(prep):
        w.writerow([k] + [(prep[k].get(c) or "").strip() for c in cols])
    (COLIMA / "keyed_prep_colima.csv").write_text(buf.getvalue(), encoding="utf-8")
    au = ca.create(buf.getvalue(), name="PREP 2024, Colima, every presidential casilla acta", source="colima")
    au = ca.set_mapping(au, au["id_col"], au["mapping"], "stored")
    c = TestClient(app)
    out = {"audit_id": au["id"]}
    for path, name in ((f"/audit/{au['id']}/report", "audit_report.html"),
                       (f"/audit/{au['id']}/report.csv", "audit_report.csv")):
        r = c.get(path)
        out[name] = r.status_code
        if r.status_code == 200:
            (COLIMA / name).write_bytes(r.content)
    R_ = ca.run(au)
    out.update({k: R_[k] for k in ("forms_keyed", "forms_read", "checked", "disputed", "disputed_forms", "tiers")})
    out["unread"] = len(R_["unread"])
    return out


def md_colima(d: dict) -> str:
    v1 = d["gates"]["v1 (frozen gate, primary)"]
    head = (f"**Colima, {'whole state' if d['complete'] else 'PARTIAL (' + str(d['rows']) + ' of ' + str(d['located']) + ' read)'}: "
            f"{v1['forms_accepted']} of {d['prep_rows']} presidential actas accepted under the frozen gate "
            f"({d['located']} located), {len(v1['errors'])} wrong of {v1['fields']:,} accepted fields"
            f"{' (' + str(len(v1['pending'])) + ' awaiting adjudication: not final)' if v1['pending'] else ''}.**")
    L = ["# Colima, complete-state audit on the AMD Token Factory (PROTOCOL.md Amendment 8b)", "", head, "",
         "Gemma-4-31B-IT, frozen prompt, page + 6 tiles, temperature 0. Gates as pre-registered: v1 primary, v2, v3.", "",
         "| gate | forms accepted | touchless | Movil / Escaner | accepted fields | wrong (Wilson 95%) | awaiting adjudication |",
         "|---|---|---|---|---|---|---|"]
    for name, o in d["gates"].items():
        ci = f"{100 * o['ci'][0]:.2f}% to {100 * o['ci'][1]:.2f}%" if o.get("ci") else "-"
        L.append(f"| {name} | {o['forms_accepted']} | {o['touchless']} | {o.get('movil', 0)} / {o.get('escaner', 0)} | "
                 f"{o['fields']:,} | {len(o['errors'])} ({ci}) | {len(o['pending'])} |")
    L += ["", f"Disagreements with the first capture on graded fields: {d['disagreements']}, by label:", ""]
    L += [f"- {k}: {v}" for k, v in d["labels"].items()]
    L += ["", f"PREP rows {d['prep_rows']}; located {d['located']}; not located or no image "
          f"{len(d['no_image_or_not_located'])} (routed, never replaced); also in other sets (flagged, not double-counted): "
          f"{len(d['also_in_other_sets'])}.", ""]
    ar = d.get("audit_report") or {}
    if ar:
        L += [f"Report from the /audit/new generator: `results/colima/audit_report.html` / `.csv` (audit {ar.get('audit_id')}): "
              f"{ar.get('forms_read')} forms read, {ar.get('checked')} fields checked, {ar.get('disputed')} disputed on "
              f"{ar.get('disputed_forms')} forms; tiers {ar.get('tiers')}." if "error" not in ar else
              f"Audit report generator failed: {ar['error']}", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("b4", "colima", "score-b4", "score-colima"))
    ap.add_argument("--no-report", action="store_true", help="score-colima: skip the /audit/new report")
    a = ap.parse_args(argv)
    return {"b4": cmd_b4, "colima": cmd_colima, "score-b4": cmd_score_b4, "score-colima": cmd_score_colima}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
