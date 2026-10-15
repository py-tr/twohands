"""`make eval`: every number a judge sees, recomputed from the committed raw results, then checked against the app.

    make eval                      # or, without make:
    python -m twohands.eval [--out results/eval_report.md]

Inputs (committed, read-only; no model call, no network, no data/raw):
  results/manifest.json (+ the confirm100, CORD and calibration manifests), results/calls_gemma.jsonl (last row per
  form), results/calls_qwen.jsonl (Qwen alone and the two-reader tiers of Amendment 2, compared with
  app/data/two_reader_300.json from scripts/two_reader_300.py), results/adjudication/verdicts.json
  (the verdict per disputed field), results/adjudication/recall_judged.json (the undisputed recall fields, judged on
  the paper), app/data/audit_sample_prep300.csv (the official first capture, PREP 2024) and
  app/data/computos_sample300.csv (the certified count, Computos 2024), schemas/, PROTOCOL.md, PROTOCOL_CORD.md, git.

This is a second, independent computation: it shares only primitives (schema, the frozen gate, gate v2, Wilson) with
scripts/build_headline.py and scripts/posthoc_v2_300.py, which write what the app displays. Every recomputed number is
compared with what the app reads (app/data/headline.json, results/posthoc_v2_300.json) and the sentences the pages
render are rebuilt from the recomputed numbers and compared word for word. Then the protocol checks: manifest and
schema sha256s against PROTOCOL.md, the frozen prompt on every call, and PROTOCOL.md and each amendment committed
before the first model read it governs (git commit times vs the first timestamps in the calls files).

Prints a table, writes results/eval_report.md, exits 1 on any mismatch.
"""
from __future__ import annotations

import argparse
import collections
import copy
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from twohands import REPO, schema as schemamod
from twohands.gate import gate
from twohands.gate_v2 import gate_v2
from twohands.score import wilson

R = REPO / "results"
ADJ = R / "adjudication"
DATA = REPO / "app" / "data"
REPORT = R / "eval_report.md"

FAINT = ("070207C0100", "093831B0100")      # the two faint-pencil forms
RECEIPT = ("050815B0100", "MORENA")          # the hero's red card
HARMONISED = ("010469C0400", "SOBRANTES")    # words and digits harmonised in one call
TYPES = ("wrong_value", "marked_illegible", "keyed_blank", "other")
VERDICTS = ("model_right", "capture_right", "neither", "paper_ambiguous", "unreadable", "crop_wrong")
CERT_COL = {"NO_REGISTRADAS": "CANDIDATO/A NO REGISTRADO/A", "NULOS": "VOTOS NULOS", "TOTAL": "TOTAL_VOTOS_CALCULADOS"}


# ------------------------------------------------------------------ inputs
def num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    return int(v) if v.isdigit() else None


def jsonl_last(path: Path) -> tuple[dict, collections.Counter, list]:
    """Last row per clave (resumed runs append), the row count per clave, and every row's ts."""
    last, n, ts = {}, collections.Counter(), []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # a half-written last line of a running pass
            last[r["clave"]] = r
            n[r["clave"]] += 1
            ts.append(r.get("ts"))
    return last, n, ts


def csv_rows(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as f:
        return {r["CLAVE_CASILLA"]: r for r in csv.DictReader(f)}


def jload(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def one_in(k, n):
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


def parsed_of(r: dict, keys: list):
    if not r or r.get("no_call") or not r.get("parsed_ok"):
        return None
    F = r.get("fields") or {}
    return {"values": [{"label": (F.get(k) or {}).get("label"), "n": (F.get(k) or {}).get("n"),
                        "w": (F.get(k) or {}).get("w")} for k in keys]}


# ------------------------------------------------------------------ recompute
def recompute() -> dict:
    s = schemamod.load()
    graded = [f for f in s["fields"] if f.get("csv")]
    man = jload(R / "manifest.json")
    claves = [it["clave"] for it in man["items"]]
    layout = {it["clave"]: it["layout"] for it in man["items"]}
    G, n_rows, _ = jsonl_last(R / "calls_gemma.jsonl")
    prep = csv_rows(DATA / "audit_sample_prep300.csv")
    comp = csv_rows(DATA / "computos_sample300.csv")
    V = jload(ADJ / "verdicts.json")
    judged = jload(ADJ / "recall_judged.json")
    gv = lambda k, f: (((G[k].get("fields") or {}).get(f) or {}).get("n"))  # noqa: E731

    read = [k for k in claves if k in G and G[k].get("parsed_ok") and not G[k].get("no_call") and k in prep]
    read_set = set(read)
    unread = [k for k in claves if k not in read_set]
    # the touchless count: the frozen gate re-run on every stored read, checked against the stored flag
    v1 = {k: (gate(p, s).accepted if (p := parsed_of(G.get(k), s["keys"])) is not None else False) for k in claves}
    stored = {k: bool(G.get(k, {}).get("accepted")) for k in claves}
    gate_mism = [k for k in claves if v1[k] != stored[k]]
    accepted = [k for k in claves if v1[k]]
    acc = set(accepted)

    fields = len(read) * len(graded)
    dis = [(k, f["key"]) for k in read for f in graded if gv(k, f["key"]) != num(prep[k][f["csv"]])]
    missing_v = sorted({f"{k}__{f}" for k, f in dis} ^ set(V))
    vof = lambda k, f: V.get(f"{k}__{f}", {})  # noqa: E731
    vc = collections.Counter(vof(k, f).get("verdict") for k, f in dis)
    acc_dis = [(k, f) for k, f in dis if k in acc]
    vacc = collections.Counter(vof(k, f).get("verdict") for k, f in acc_dis)
    model_wrong = vc["capture_right"] + vc["neither"]
    acc_fields = len([k for k in accepted if k in read_set]) * len(graded)
    acc_model_wrong = vacc["capture_right"] + vacc["neither"]

    # the 52: paper shows the model's value, the first capture does not
    csv_of = {f["key"]: f["csv"] for f in s["fields"] if f.get("csv")}
    mr = []
    for k, f in sorted(dis):
        v = vof(k, f)
        if v.get("verdict") != "model_right":
            continue
        c = comp.get(k)
        col = CERT_COL.get(f, f) if f in s["vote_keys"] + ["TOTAL"] else None
        cval = num(c.get(col)) if (c and col) else None
        obs = (c or {}).get("OBSERVACIONES") or ""
        paper = v.get("paper")
        mr.append({"clave": k, "field": f, "prep": prep[k][csv_of[f]], "model": gv(k, f), "paper": paper,
                   "type": classify(prep[k][csv_of[f]], paper), "certified": cval, "covered": cval is not None,
                   "agrees": cval is not None and isinstance(paper, int) and paper == cval,
                   "mode": "Cotejo" if "Cotejo" in obs else ("Recuento" if "Recuento" in obs else None)})
    by_type = collections.Counter(x["type"] for x in mr)
    cov = [x for x in mr if x["covered"]]
    differ = [x for x in cov if not x["agrees"]]

    # recall on the forms the certified count settled by comparison (Cotejo, no recount): vote rows + TOTAL
    E = C = 0
    cot, elist = [], []
    for k in read:
        obs = (comp.get(k) or {}).get("OBSERVACIONES") or ""
        if "Cotejo" not in obs or "Recuento" in obs:
            continue
        cot.append(k)
        for f in s["vote_keys"] + ["TOTAL"]:
            cv = num(comp[k].get(CERT_COL.get(f, f)))
            pv = num(prep[k][csv_of[f]])
            if cv is None or cv == pv:
                continue
            E += 1
            d = gv(k, f) != pv
            C += d
            elist.append((k, f, d))
    undisputed = [f"{k}__{f}" for k, f, d in elist if not d]
    unjudged = [x for x in undisputed if x not in judged]
    corrections = sum(judged.get(x, {}).get("paper_shows") == "capture" for x in undisputed)
    missed = sum(judged.get(x, {}).get("paper_shows") == "certified" for x in undisputed)
    E2 = E - corrections
    dv = collections.Counter(vof(k, f).get("verdict") or "-" for k, f, d in elist if d)

    # row-label gate false alarms
    def form_right(k):
        return all(vof(kk, f).get("verdict") == "model_right" for kk, f in dis if kk == k)
    lab = [k for k in read if "label" in (G[k].get("route_codes") or [])]
    lab_only = [k for k in lab if set(G[k].get("route_codes") or []) == {"label"}]

    # the faint-pencil forms: every field the capture recorded as illegible
    fl = [(k, f["key"]) for k in FAINT if k in read_set for f in graded
          if (prep[k][f["csv"]] or "").strip().lower().startswith("ilegible") and (k, f["key"]) in set(dis)]
    fv = collections.Counter(vof(k, f).get("verdict") for k, f in fl)
    fc = [x for x in mr if (x["clave"], x["field"]) in set(fl) and x["covered"]]

    rc = next((x for x in mr if (x["clave"], x["field"]) == RECEIPT), {})
    hk, hf = HARMONISED
    hF = ((G.get(hk) or {}).get("fields") or {}).get(hf) or {}

    lat = [G[k]["latency_s"] for k in read if G[k].get("latency_s")]
    cost = [G[k]["cost_usd"] for k in read if G[k].get("cost_usd")]
    tin = [x for x in ((G[k].get("usage") or {}).get("prompt_tokens") for k in read) if x]
    tout = [x for x in ((G[k].get("usage") or {}).get("completion_tokens") for k in read) if x]

    from app.store import name_of
    H = {
        "forms": len(claves), "read": len(read), "unread": len(unread), "unread_claves": unread,
        "graded_per_form": len(graded), "fields": fields, "disagree": len(dis),
        "disagree_forms": len({k for k, _ in dis}), "agree": fields - len(dis),
        "agree_pct": round(100 * (fields - len(dis)) / fields, 2), "flag_pct": round(100 * len(dis) / fields, 1),
        "accepted": len(accepted), "accepted_pct": round(100 * len(accepted) / len(claves)),
        "accepted_pct1": round(100 * len(accepted) / len(claves), 1),
        "accepted_movil": sum(layout[k] == "movil" for k in accepted),
        "accepted_escaner": sum(layout[k] == "escaner" for k in accepted),
        "routed": len(claves) - len(accepted), "acc_fields": acc_fields, "acc_disagree": len(acc_dis),
        "acc_model_wrong": acc_model_wrong, "acc_model_right": vacc["model_right"],
        "acc_wrong_ci": wilson(acc_model_wrong, acc_fields),
        "verdicts": {v: vc.get(v, 0) for v in VERDICTS}, "verdicts_accepted": {v: vacc.get(v, 0) for v in VERDICTS},
        "model_wrong": model_wrong, "model_one_in": one_in(model_wrong, fields),
        "acc_one_in": one_in(acc_model_wrong, acc_fields),
        "keying_errors": len(mr), "keying_forms": len({x["clave"] for x in mr}),
        "cert_covered": len(cov), "cert_agree": len(cov) - len(differ), "cert_differ": len(differ),
        "cert_differ_recount": sum(x["mode"] == "Recuento" for x in differ),
        "yield_one_in": one_in(len(mr), len(dis)), "yield_pct": round(100 * len(mr) / len(dis), 1),
        "random_one_in": one_in(len(mr), fields), "yield_x": round(fields / len(dis), 1),
        "yield_x_int": round(fields / len(dis)),
        "wrong_number_one_in": round(fields / (by_type.get("wrong_value") or 1)),
        "by_type": {t: by_type.get(t, 0) for t in TYPES},
        "illegible_on_faint": sum(1 for x in mr if x["type"] == "marked_illegible" and x["clave"] in FAINT),
        "recall": {"forms": len(cot), "E": E, "C": C, "ci": wilson(C, E) if E else None, "corrections": corrections,
                   "missed": missed, "E2": E2, "ci2": wilson(C, E2) if E2 else None,
                   "recall2_pct": round(100 * C / E2) if E2 else None, "disputed_verdicts": dict(dv)},
        "label_gate": {"routed": len(lab), "label_only": len(lab_only), "read_right": sum(map(form_right, lab)),
                       "label_only_right": sum(map(form_right, lab_only))},
        "faint": {"illegible": len(fl), "model_read": fv.get("model_right", 0), "verdicts": dict(fv),
                  "covered": len(fc), "agree": sum(x["agrees"] for x in fc),
                  "differ_recount": sum((not x["agrees"]) and x["mode"] == "Recuento" for x in fc)},
        "receipt": {"paper": rc.get("paper"), "prep": rc.get("prep"), "certified": rc.get("certified"),
                    "cert_mode": rc.get("mode"), "model": rc.get("model")},
        "harmonised": {"clave": hk, "field": hf, "name": name_of(hf), "digits": hF.get("n"), "words": hF.get("w"),
                       "paper": vof(hk, hf).get("paper")},
        "gemma": {"mean_secs": round(sum(lat) / len(lat), 1) if lat else None,
                  "cost_per_form": sum(cost) / len(cost) if cost else None, "reads": len(read),
                  "stop": sum(G[k].get("finish_reason") == "stop" for k in read),
                  "tokens_in": round(sum(tin) / len(tin)) if tin else None,
                  "tokens_out": round(sum(tout) / len(tout)) if tout else None},
        "rereads": {"forms": sum(1 for k in claves if n_rows[k] > 1), "rows": sum(n_rows.values())},
    }
    integrity = {"stored gate flag = frozen gate re-run": gate_mism,
                 "verdicts.json covers exactly the disputed fields": missing_v,
                 "every undisputed recall field judged on the paper": unjudged,
                 "every verdict is a known verdict": sorted(x for x, v in V.items() if v.get("verdict") not in VERDICTS)}
    return {"H": H, "integrity": integrity, "_ctx": (s, claves, layout, G, prep, V, read_set)}


def qwen_rows(claves) -> dict:
    Q, _, _ = jsonl_last(R / "calls_qwen.jsonl")
    return {k: r for k, r in Q.items() if k in set(claves)}


def posthoc(ctx) -> dict:
    """Gate v1 / v2 / v2-2R / v2-2R strict / v2b (Amendment 3, post-hoc on the 300): touchless forms, accepted fields,
    errors, flagged."""
    s, claves, layout, G, prep, V, read_set = ctx
    graded = [f for f in s["fields"] if f.get("csv")]
    Q = qwen_rows(claves)
    qv = lambda k: ({x: ((Q[k].get("fields") or {}).get(x) or {}).get("n") for x in s["keys"]}  # noqa: E731
                    if k in Q and Q[k].get("parsed_ok") else {})
    tiers = {"v1 (frozen gate)": lambda p, k: gate(p, s).accepted, "v2": lambda p, k: gate_v2(p, s, "v2").accepted,
             "v2-2R (Qwen confirms SOBRANTES)": lambda p, k: gate_v2(p, s, "v2", second=qv(k)).accepted,
             "v2-2R strict (only Qwen confirms SOBRANTES)":
                 lambda p, k: gate_v2(p, s, "v2", second=qv(k), second_required=True).accepted,
             "v2b (relaxed label, secondary)": lambda p, k: gate_v2(p, s, "v2b").accepted}
    out = {}
    for name, fn in tiers.items():
        acc = [k for k in claves if (p := parsed_of(G.get(k), s["keys"])) is not None and fn(p, k)]
        n = err = und = flag = 0
        for k in acc:
            for f in graded:
                n += 1
                v = V.get(f"{k}__{f['key']}")
                m = ((G[k].get("fields") or {}).get(f["key"]) or {}).get("n")
                if v:
                    err += v["verdict"] in ("capture_right", "neither")
                    und += v["verdict"] not in ("capture_right", "neither", "model_right")
                elif k not in prep or m != num(prep[k][f["csv"]]):
                    flag += 1
        out[name] = {"accepted": len(acc), "movil": sum(layout[k] == "movil" for k in acc),
                     "escaner": sum(layout[k] == "escaner" for k in acc), "fields": n, "errors": err,
                     "undecided": und, "flagged": flag, "err_rate": err / n if n else None}
    return out


A2_KEYS = ("accepted", "movil", "escaner", "fields", "disagree", "capture_errors", "errors", "undecided", "unadjudicated")


def amendment2(ctx) -> dict | None:
    """Amendment 2 tiers with the second reader (PROTOCOL.md section 7 and Amendment 2 c-d), plus the post-hoc v2-2R
    pair, recomputed here without twohands/tiers.py or scripts/two_reader_300.py. Accepted field truth: the paper where
    a verdict read it, else the capture; reader != capture with no verdict = not adjudicated (never counted right)."""
    s, claves, layout, G, prep, V, read_set = ctx
    Q = qwen_rows(claves)
    if not Q:
        return None
    graded = [f for f in s["fields"] if f.get("csv")]
    keys, votes = s["keys"], s["vote_keys"]
    ok = lambda r: bool(r) and bool(r.get("parsed_ok")) and not r.get("no_call")  # noqa: E731
    dig = lambda r, w="n": {k: num(((r.get("fields") or {}).get(k) or {}).get(w)) for k in keys}  # noqa: E731
    gate_ok = lambda r: (p := parsed_of(r, keys)) is not None and gate(p, s).accepted  # noqa: E731

    def strict(k):  # Amendment 2 (d): 23 digits agree; every digit read; words = digits where read; rows = TOTAL
        if not (ok(G.get(k)) and ok(Q.get(k))):
            return False
        d = dig(G[k])
        if d != dig(Q[k]) or None in d.values():
            return False
        if any(w is not None and w != d[x] for r in (G[k], Q[k]) for x, w in dig(r, "w").items()):
            return False
        return sum(d[x] for x in votes) == d["TOTAL"]

    def v22(k, req):
        p = parsed_of(G.get(k), keys)
        return p is not None and gate_v2(p, s, "v2", second=dig(Q[k]) if ok(Q.get(k)) else None,
                                         second_required=req).accepted

    rules = {"gemma": (G, lambda k: gate_ok(G.get(k))), "qwen": (Q, lambda k: gate_ok(Q.get(k))),
             "two_reader": (G, strict),
             "two_reader_s7": (G, lambda k: gate_ok(G.get(k)) and gate_ok(Q.get(k)) and dig(G[k]) == dig(Q[k])),
             "v2_2r": (G, lambda k: v22(k, False)), "v2_2r_strict": (G, lambda k: v22(k, True))}
    tiers = {}
    for name, (rd, rule) in rules.items():
        acc = [k for k in claves if rule(k)]
        o = dict.fromkeys(A2_KEYS, 0)
        o.update(accepted=len(acc), movil=sum(layout[k] == "movil" for k in acc),
                 escaner=sum(layout[k] == "escaner" for k in acc))
        for k in acc:
            d = dig(rd[k])
            for f in graded:
                o["fields"] += 1
                pv = num(prep[k][f["csv"]]) if k in prep else None
                v = V.get(f"{k}__{f['key']}")
                if d[f["key"]] != pv:
                    o["disagree"] += 1
                if v and v["verdict"] in ("model_right", "capture_right", "neither"):
                    paper = None if v.get("paper") == "blank" else v.get("paper")
                    o["errors"] += d[f["key"]] != paper
                    o["capture_errors"] += d[f["key"]] != pv and d[f["key"]] == paper and v["verdict"] == "model_right"
                elif v:
                    o["undecided"] += 1
                elif d[f["key"]] != pv:
                    o["unadjudicated"] += 1
        tiers[name] = o
    parsed = [k for k in claves if ok(Q.get(k))]
    cost = [Q[k]["cost_usd"] for k in parsed if Q[k].get("cost_usd")]
    lat = [Q[k]["latency_s"] for k in parsed if Q[k].get("latency_s")]
    return {"tiers": tiers, "reads": len(Q), "parsed": len(parsed), "complete": len(Q) == len(claves),
            "agree_all_23": sum(ok(G.get(k)) and ok(Q.get(k)) and dig(G[k]) == dig(Q[k]) for k in claves),
            "cost_per_form": sum(cost) / len(cost) if cost else None,
            "mean_secs": round(sum(lat) / len(lat), 1) if lat else None}


# ------------------------------------------------------------------ protocol
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args) -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else None


def first_commit(path: str, pickaxe: str | None = None) -> tuple[str, datetime] | None:
    out = git("log", "--reverse", "--format=%H %cI", *(["-S", pickaxe] if pickaxe else []), "--", path)
    if not out or not out.strip():
        return None
    h, t = out.splitlines()[0].split()
    return h, datetime.fromisoformat(t)


def ts(x: str) -> datetime:
    return datetime.fromisoformat(x.replace("Z", "+00:00"))


def utc(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def protocol_checks() -> list[tuple[str, bool | None, str]]:
    """(check, ok, detail); ok None = skipped (no git history, e.g. a zip download or a shallow clone)."""
    P = (REPO / "PROTOCOL.md").read_text(encoding="utf-8")
    PC = (REPO / "PROTOCOL_CORD.md").read_text(encoding="utf-8")
    out = []

    def shacheck(name, path, text, pattern):
        m = re.search(pattern, text, re.S)
        want = m.group(1) if m else None
        got = sha256(REPO / path)
        out.append((f"sha256 {path}", want == got, f"{got[:12]}... vs pre-registered {(want or 'not found')[:12]}..."))

    shacheck("manifest", "results/manifest.json", P, r"Manifest sha256: `([0-9a-f]{64})`")
    shacheck("calibration", "results/calibration_manifest.json", P, r"calibration_manifest\.json`, sha256 `([0-9a-f]{64})`")
    shacheck("confirm100", "results/manifest_confirm100.json", P, r"manifest_confirm100\.json`.*?sha256 `([0-9a-f]{64})`")
    shacheck("cord100", "results/manifest_cord100.json", PC, r"Manifest sha256: `([0-9a-f]{64})`")

    prompt = re.search(r"\*\*sha256 `([0-9a-f]{64})`\*\* \(`reader\.prompt_sha256\(\)`\)", P).group(1)
    from twohands import reader
    out.append(("frozen prompt = reader.prompt_sha256()", reader.prompt_sha256() == prompt, prompt[:12] + "..."))
    calls = sorted(R.glob("calls_*.jsonl"))
    bad = []
    rows = {}
    for p in calls:
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.setdefault(p.name, []).append(r)
            if not r.get("no_call") and r.get("prompt_sha256") != prompt:
                bad.append(f"{p.name}:{r.get('clave')}")
    out.append(("every model call used the frozen prompt", not bad,
                f"{sum(map(len, rows.values()))} rows in {', '.join(rows)}" + (f"; off: {bad[:5]}" if bad else "")))

    if git("rev-parse", "--git-dir") is None or (git("rev-parse", "--is-shallow-repository") or "").strip() == "true":
        out.append(("protocol commit order", None, "skipped: no full git history here (clone the repository)"))
        return out
    schema_want = re.search(r"mx_presidencia_2024\.yaml` \(sha256 `([0-9a-f]{64})`\)", P).group(1)
    base = first_commit("PROTOCOL.md")
    at_base = git("show", f"{base[0]}:schemas/mx_presidencia_2024.yaml") if base else None
    out.append(("schema as pre-registered (at the protocol commit)",
                at_base is not None and hashlib.sha256(at_base.encode("utf-8")).hexdigest() == schema_want,
                f"{schema_want[:12]}... at {base[0][:7] if base else '?'}"))
    for path in ("PROTOCOL.md", "PROTOCOL_CORD.md", "results/manifest.json", "results/manifest_confirm100.json",
                 "schemas/mx_presidencia_2024.yaml", "twohands/gate.py", "twohands/reader.py"):
        dirty = git("status", "--porcelain", "--", path)
        out.append((f"{path} committed as on disk", dirty is not None and not dirty.strip(), dirty.strip() or "clean"))
    # append-only: every later commit to PROTOCOL.md only adds lines (an amendment), never edits the frozen text
    edits, h = [], None
    for line in (git("log", "--format=@%h", "--numstat", "--", "PROTOCOL.md") or "").splitlines():
        if line.startswith("@"):
            h = line[1:]
        elif line.count("\t") >= 2 and line.split("\t")[1] != "0":
            edits.append(f"{h} deletes {line.split(chr(9))[1]} lines")
    out.append(("PROTOCOL.md is append-only (amendments add, never edit)", not edits, "; ".join(edits) or "no deletions"))

    man300 = {it["clave"] for it in jload(R / "manifest.json")["items"]}
    man100 = {it["clave"] for it in jload(R / "manifest_confirm100.json")["items"]}
    first = lambda pred: min((ts(r["ts"]) for rs in rows.values() for r in rs if r.get("ts") and pred(r)), default=None)  # noqa: E731
    g0 = min((ts(r["ts"]) for r in rows.get("calls_gemma.jsonl", []) if r.get("ts") and r["clave"] in man300), default=None)
    g1 = min((ts(r["ts"]) for r in rows.get("calls_gemma.jsonl", []) if r.get("ts") and r["clave"] in man300
              and r.get("parsed_ok")), default=None)
    q0 = min((ts(r["ts"]) for r in rows.get("calls_qwen.jsonl", []) if r.get("ts") and r["clave"] in man300), default=None)
    c0 = first(lambda r: r.get("clave") in man100)
    adj0 = first_commit("results/adjudication/adjudication.jsonl")
    sched = [("PROTOCOL.md (pre-registration)", base, "first recorded Gemma call on the 300", g0),
             ("results/manifest.json", first_commit("results/manifest.json"), "first recorded Gemma call on the 300", g0),
             ("Amendment 1 (locator)", first_commit("PROTOCOL.md", "## Amendment 1"), "first recorded Gemma call on the 300", g0),
             ("Amendment 1 (locator)", first_commit("PROTOCOL.md", "## Amendment 1"), "first successful Gemma read", g1),
             ("Amendment 2 (secondary analyses)", first_commit("PROTOCOL.md", "## Amendment 2"), "first Qwen call on the 300", q0),
             ("Amendment 2 (secondary analyses)", first_commit("PROTOCOL.md", "## Amendment 2"), "first adjudication commit",
              adj0[1] if adj0 else None),
             ("Amendment 3 (confirm100 draw)", first_commit("PROTOCOL.md", "## Amendment 3"), "first call on the confirm100", c0),
             ("results/manifest_confirm100.json", first_commit("results/manifest_confirm100.json"), "first call on the confirm100", c0),
             ("PROTOCOL_CORD.md", first_commit("PROTOCOL_CORD.md"), "first CORD call",
              first(lambda r: "cord" in str(r.get("schema", "")).lower()))]
    for what, c, before, t in sched:
        if c is None:
            out.append((f"{what} committed before {before}", False, "not committed"))
        elif t is None:
            out.append((f"{what} committed before {before}", True, f"{c[0][:7]} {utc(c[1])}; no such call yet"))
        else:
            out.append((f"{what} committed before {before}", c[1] < t,
                        f"{c[0][:7]} {utc(c[1])} < {utc(t)}"))
    return out


# ------------------------------------------------------------------ compare with what the app displays
def same(a, b) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    return a == b


def fmt(x) -> str:
    if isinstance(x, float):
        return f"{x:.7f}".rstrip("0") if abs(x) < 0.01 else f"{x:g}"
    if isinstance(x, list) and len(x) > 4:
        return f"[{len(x)} items]"
    return json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else str(x)


# (label shown in the table, key path in the recomputed H, key path in headline.json)
ROWS = [
    ("Forms in the pre-registered sample", "forms"), ("Forms read (parseable, matched to the capture)", "read"),
    ("Forms with no usable read", "unread"), ("  which ones", "unread_claves"),
    ("Graded fields per form", "graded_per_form"), ("Fields compared with the official capture", "fields"),
    ("Fields where model and capture disagree", "disagree"), ("  on forms", "disagree_forms"),
    ("Fields in agreement", "agree"), ("Agreement %", "agree_pct"), ("Fields flagged %", "flag_pct"),
    ("Touchless forms (frozen gate)", "accepted"), ("Touchless %", "accepted_pct"), ("Touchless % (1 dp)", "accepted_pct1"),
    ("  phone photos (Movil)", "accepted_movil"), ("  scanner (Escaner)", "accepted_escaner"), ("Routed to a person", "routed"),
    ("Accepted fields", "acc_fields"), ("Disputed accepted fields", "acc_disagree"),
    ("Accepted fields the model got wrong", "acc_model_wrong"), ("  Wilson 95%", "acc_wrong_ci"),
    ("Verdicts on the disputed fields", "verdicts"), ("Verdicts on accepted forms", "verdicts_accepted"),
    ("Model wrong, alone (capture right + neither)", "model_wrong"), ("Model alone: 1 in N", "model_one_in"),
    ("Gate-accepted: 1 in N", "acc_one_in"), ("Capture errors found (model right)", "keying_errors"),
    ("  on forms", "keying_forms"), ("  by type", "by_type"), ("  illegible on the faint forms", "illegible_on_faint"),
    ("Capture typed a wrong number: 1 in N", "wrong_number_one_in"),
    ("Certified count covers", "cert_covered"), ("  confirms the paper", "cert_agree"), ("  differs", "cert_differ"),
    ("  differs after a recount", "cert_differ_recount"), ("Yield: 1 in N disputed is a capture error", "yield_one_in"),
    ("Yield %", "yield_pct"), ("Capture error rate at least 1 in N", "random_one_in"), ("Yield x random", "yield_x"),
    ("Yield x random (int)", "yield_x_int"),
    ("Recall: Cotejo forms", "recall.forms"), ("Recall: E (certified != capture)", "recall.E"),
    ("Recall: C (model disputed)", "recall.C"), ("Recall: loose Wilson 95%", "recall.ci"),
    ("Recall: council corrections / blank rows", "recall.corrections"), ("Recall: missed", "recall.missed"),
    ("Recall: E2", "recall.E2"), ("Recall: measured %", "recall.recall2_pct"), ("Recall: Wilson 95%", "recall.ci2"),
    ("Recall: verdicts of the disputed", "recall.disputed_verdicts"),
    ("Label gate: routed", "label_gate.routed"), ("Label gate: label only", "label_gate.label_only"),
    ("Label gate: read right", "label_gate.read_right"), ("Label gate: label only, read right", "label_gate.label_only_right"),
    ("Faint forms: illegible fields", "faint.illegible"), ("Faint forms: model read", "faint.model_read"),
    ("Faint forms: verdicts", "faint.verdicts"), ("Faint forms: certified covers", "faint.covered"),
    ("Faint forms: certified agrees", "faint.agree"), ("Faint forms: differ after recount", "faint.differ_recount"),
    ("Hero receipt: paper", "receipt.paper"), ("Hero receipt: first capture", "receipt.prep"),
    ("Hero receipt: certified", "receipt.certified"), ("Hero receipt: certified by", "receipt.cert_mode"),
    ("Hero receipt: model", "receipt.model"),
    ("Harmonised read: digits", "harmonised.digits"), ("Harmonised read: words", "harmonised.words"),
    ("Harmonised read: paper", "harmonised.paper"),
    ("Gemma: cost per form (USD)", "gemma.cost_per_form"), ("Gemma: mean latency (s)", "gemma.mean_secs"),
    ("Gemma: reads", "gemma.reads"), ("Gemma: replies 'stop'", "gemma.stop"),
    ("Gemma: tokens in", "gemma.tokens_in"), ("Gemma: tokens out", "gemma.tokens_out"),
    ("Outage re-reads: forms", "rereads.forms"), ("Calls rows", "rereads.rows"),
]


def get(d, path):
    for p in path.split("."):
        if not isinstance(d, dict) or p not in d:
            return KeyError
        d = d[p]
    return d


def displayed(Hd: dict, path: str):
    if path == "by_type":
        return {t["type"]: t["n"] for t in Hd.get("by_type", [])}
    return get(Hd, path)


def sample_audit_root() -> str:
    """The Merkle root of the sample audit's report (standard mode, every disputed field), rebuilt from scratch in a
    temporary directory over the stored pre-registered Gemma reads only (a live read on this machine is ignored),
    with each crop cut from the committed masked page. Published in results/sample_audit_root.txt."""
    import shutil
    import tempfile
    from app import capture_audit as ca
    old_dir, old_find = ca.AUDITS, ca.find_read
    tmp = Path(tempfile.mkdtemp(prefix="twohands-eval-"))

    def stored_only(a, fid):
        v, page = old_find(a, fid)
        return (v, page) if v is None or v.source.startswith("stored read") else (None, page)
    try:
        ca.AUDITS, ca.find_read = tmp / "audits", stored_only
        a = ca.sample()
        return ca.merkle_tree(a, ca.run(a))["root"]
    finally:
        ca.AUDITS, ca.find_read = old_dir, old_find
        shutil.rmtree(tmp, ignore_errors=True)


SAMPLE_ROOT = R / "sample_audit_root.txt"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(REPORT), help="where to write the markdown report")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    say = (lambda *x: None) if a.quiet else print

    rec = recompute()
    H = rec["H"]
    Hd = jload(DATA / "headline.json")
    PH = jload(R / "posthoc_v2_300.json")
    ph = posthoc(rec["_ctx"])
    qw = amendment2(rec["_ctx"])
    T2 = jload(DATA / "two_reader_300.json") if (DATA / "two_reader_300.json").is_file() else None
    proto = protocol_checks()

    table, bad = [], []
    for label, path in ROWS:
        got, shown = get(H, path), displayed(Hd, path)
        ok = shown is not KeyError and same(got, shown)
        table.append((label, fmt(got), "(missing)" if shown is KeyError else fmt(shown), "app/data/headline.json", ok))
        bad += [] if ok else [f"{label}: recomputed {fmt(got)}, app shows {fmt(shown)}"]
    for name, o in ph.items():
        shown = PH.get(name) or {}
        for k in ("accepted", "movil", "escaner", "fields", "errors", "undecided", "flagged"):
            sv = len(shown[k]) if k == "flagged" and isinstance(shown.get(k), list) else shown.get(k, KeyError)
            ok = same(o[k], sv)
            table.append((f"POST-HOC {name}: {k}", fmt(o[k]), fmt(sv), "results/posthoc_v2_300.json", ok))
            bad += [] if ok else [f"POST-HOC {name} {k}: recomputed {o[k]}, file shows {sv}"]
    if qw:
        for name, o in qw["tiers"].items():
            shown = ((T2 or {}).get("tiers") or {}).get(name) or {}
            for k in A2_KEYS:
                sv = shown.get(k, KeyError)
                ok = same(o[k], sv)
                table.append((f"Amendment 2 tier {name}: {k}", fmt(o[k]), fmt(sv), "app/data/two_reader_300.json", ok))
                bad += [] if ok else [f"Amendment 2 tier {name} {k}: recomputed {o[k]}, app shows {sv}"]
        sv = (T2 or {}).get("agree_all_23", KeyError)
        ok = same(qw["agree_all_23"], sv)
        table.append(("Two readers agree on all 23 digits", fmt(qw["agree_all_23"]), fmt(sv), "app/data/two_reader_300.json", ok))
        bad += [] if ok else [f"agree_all_23: recomputed {qw['agree_all_23']}, app shows {sv}"]
        for k in ("reads", "parsed", "cost_per_form", "mean_secs"):
            table.append((f"Qwen: {k}", fmt(qw[k]), "not displayed", "results/calls_qwen.jsonl", None))

    # the sentences the pages render, rebuilt from the recomputed numbers, word for word
    from app.numbers import lines
    H2 = copy.deepcopy(Hd)
    for _, path in ROWS:
        v = get(H, path)
        if path == "by_type":
            for t in H2["by_type"]:
                t["n"] = v[t["type"]]
            continue
        d, *ks = [H2] + path.split(".")
        for p in ks[:-1]:
            d = d[p]
        d[ks[-1]] = v
    T3 = None
    if T2 and qw:  # the second-reader sentences, rebuilt from the recomputed tiers
        T3 = copy.deepcopy(T2)
        T3["agree_all_23"] = qw["agree_all_23"]
        for name, o in qw["tiers"].items():
            T3["tiers"].setdefault(name, {}).update({k: o[k] for k in A2_KEYS})
    L1, L2 = lines(Hd, T2), lines(H2, T3)
    for k in L1:
        ok = L1[k] == L2[k]
        table.append((f"Rendered sentence '{k}'", "rebuilt", "as rendered", "app/numbers.py lines()", ok))
        bad += [] if ok else [f"rendered sentence '{k}' differs when rebuilt from recomputed numbers"]

    root = sample_audit_root()
    try:
        pub = SAMPLE_ROOT.read_text(encoding="utf-8").split()[0]
    except (OSError, IndexError):
        pub = "(missing)"
    ok = root == pub
    table.append(("Sample audit Merkle root", root[:16], pub[:16], "results/sample_audit_root.txt", ok))
    bad += [] if ok else [f"sample audit Merkle root: recomputed {root}, published {pub}"]

    for k, v in rec["integrity"].items():
        table.append((k, "ok" if not v else f"{len(v)} off", "", "integrity", not v))
        bad += [] if not v else [f"{k}: {v[:5]}"]
    for k, ok, detail in proto:
        table.append((k, detail, "", "protocol", ok))
        bad += [] if ok is not False else [f"protocol: {k} ({detail})"]

    secs = time.perf_counter() - t0
    checked = sum(1 for r in table if r[4] is not None)
    say(f"{'number':58s} {'recomputed':>26s}  {'app shows':>26s}  ok")
    for label, got, shown, src, ok in table:
        mark = "ok" if ok else ("--" if ok is None else "MISMATCH")
        if src == "protocol":
            say(f"{label[:70]:70s} {got}  {mark}")
        else:
            say(f"{label[:58]:58s} {got[:26]:>26s}  {shown[:26]:>26s}  {mark}")
    say(f"\n{checked} checks, {len(bad)} mismatches, {secs:.1f} s")
    for b in bad:
        say("  MISMATCH", b)

    L = ["# `make eval`: every number on the site, recomputed from the raw results", "",
         "Generated by `python -m twohands.eval` (`make eval`). No model call, no network, no data/raw: inputs are the",
         "committed calls files, the adjudication verdicts, the manifests, the official first capture and certified count",
         "of the 300 forms (`app/data/`), and git. Each number is recomputed independently of the scripts that wrote what",
         "the app reads, then compared with it.", "",
         f"**{checked} checks, {len(bad)} mismatches.** Exit code {'1' if bad else '0'}.", "",
         "| number | recomputed | app shows | source | check |", "|---|---|---|---|---|"]
    for label, got, shown, src, ok in table:
        mark = "ok" if ok else ("info" if ok is None else "**MISMATCH**")
        esc = lambda x: x.replace("|", "/")  # noqa: E731
        L.append(f"| {esc(label.strip())} | {esc(got)} | {esc(shown)} | {src} | {mark} |")
    if qw:
        L += ["", f"Second reader: {qw['reads']} of 300 Qwen rows present"
              + ("" if qw["complete"] else " (the second-reader pass is still running; these tiers are not final)") + "."]
    if bad:
        L += ["", "## Mismatches", ""] + [f"- {b}" for b in bad]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    say(f"wrote {out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
