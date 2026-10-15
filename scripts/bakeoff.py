"""Amendment 6 (PROTOCOL.md): the open-model bake-off on AMD Token Factory. Secondary analysis; the primary is unchanged.

    python scripts/bakeoff.py order     # the fixed, capture-stratified shuffled order of the 300 -> results/bakeoff_order.json
    python scripts/bakeoff.py probe     # ONE call per vision model on a pilot page -> results/bakeoff_probe.jsonl (not results)
    python scripts/bakeoff.py plan      # params + per-model spend caps from the probes -> results/bakeoff_plan.json
    python scripts/bakeoff.py run       # resumable reads -> results/calls_<model id, lower case>.jsonl
    python scripts/bakeoff.py report    # -> app/data/bakeoff_300.json + results/bakeoff_300.md (no model call)

Every read: the same masked page + 6 tiles, the same frozen prompt (sha256 checked), temperature 0, the same parser and
frozen gate (twohands.run.record). The shared limiter (cache/ratelimit.json) paces every request. Budget: this run's own
spend per reset day (16:00 UTC) is capped at DAILY_USD; /usage is read before every batch and the run sleeps to the
reset if over; reads stop at STOP_UTC. The API key is never read here (the core client twohands.amd does it).
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from twohands import reader, schema as schemamod  # noqa: E402

R = REPO / "results"
ORDER = R / "bakeoff_order.json"
PROBE = R / "bakeoff_probe.jsonl"
PLAN = R / "bakeoff_plan.json"
LOG = R / "bakeoff_run.log"
OUT_JSON = REPO / "app" / "data" / "bakeoff_300.json"
OUT_MD = R / "bakeoff_300.md"
VB = R / "adjudication" / "verdicts_bakeoff.json"
SEED = "20261019:bakeoff"
PILOT_PAGE = REPO / "data" / "masked" / "spike" / "010441C0100.jpg"
DONE = {"Gemma-4-31B-IT": "gemma", "Qwen3.8-27B": "qwen"}  # read on the 300 before Amendment 6: reused, not re-read
BASE_PARAMS = {"temperature": 0, "max_tokens": 6000, "reasoning_effort": "low"}  # Qwen's frozen params (section 4)
DAILY_USD = 0.40
TOTAL_USD = 0.75
ENDPOINT_DAILY_CEILING = 0.90  # never push the shared key's day past this (its limit is 1.00)
STOP_UTC = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
CONCURRENCY = 4
_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"{now()} {msg}"
    with _lock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def slug(model: str) -> str:
    return model.lower()


def calls_path(model: str) -> Path:
    if model in DONE:
        return R / f"calls_{DONE[model]}.jsonl"
    return R / f"calls_{slug(model)}.jsonl"


def jsonl(p: Path) -> list:
    out = []
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def last_rows(p: Path) -> dict:
    return {r["clave"]: r for r in jsonl(p)}


def manifest() -> list:
    return json.loads((R / "manifest.json").read_text(encoding="utf-8"))["items"]


# ------------------------------------------------------------------ order
def make_order(items: list) -> list:
    """Capture-stratified shuffle: each capture type sorted by clave and shuffled with Random(SEED:<type>), then merged so
    every prefix holds the two types in proportion (at each step, the type furthest below its share goes next)."""
    groups = {}
    for lay in sorted({it["layout"] for it in items}):
        g = sorted(it["clave"] for it in items if it["layout"] == lay)
        random.Random(f"{SEED}:{lay}").shuffle(g)
        groups[lay] = g
    n = len(items)
    taken = {k: 0 for k in groups}
    out = []
    for i in range(1, n + 1):
        lay = max((k for k in groups if taken[k] < len(groups[k])),
                  key=lambda k: (i * len(groups[k]) / n - taken[k], k))
        out.append(groups[lay][taken[lay]])
        taken[lay] += 1
    return out


def cmd_order(_a) -> int:
    order = make_order(manifest())
    h = hashlib.sha256("\n".join(order).encode()).hexdigest()
    ORDER.write_text(json.dumps({"seed": SEED, "sha256_of_newline_joined": h, "n": len(order), "order": order}, indent=1)
                     + "\n", encoding="utf-8")
    print(len(order), h)
    return 0


# ------------------------------------------------------------------ calls
def body_for(model: str, page_path: Path, params: dict, s: dict) -> dict:
    from PIL import Image
    b = reader.build_body("qwen", Image.open(page_path), s)  # same content: page + 6 tiles + frozen prompt
    b["model"] = model
    b.pop("reasoning_effort", None)
    b.update(params)
    return b


def call(model: str, page_path: Path, params: dict, s: dict, retries: int = 6) -> dict:
    from twohands import amd
    body = body_for(model, page_path, params, s)
    t, timing = time.time(), {}
    row = {"model": model}
    try:
        r, attempts = amd.chat(body, retries=retries, log=lambda m: log(f"{model}: {m}"), kind="bakeoff", timing=timing)
        ch = r["choices"][0]
        msg = ch.get("message") or {}
        row.update(content=msg.get("content") or "", finish_reason=ch.get("finish_reason"), usage=r.get("usage", {}),
                   attempts=attempts)
    except Exception as e:  # noqa: BLE001
        row.update(error=f"{type(e).__name__}: {str(e)[:200]}", content="")
    row["secs"] = timing.get("http_s", round(time.time() - t, 1))
    row["wall_s"] = round(time.time() - t, 1)
    row["parsed"] = reader.parse(row["content"])
    return row


def vision_models() -> list:
    from twohands import amd
    m = amd._req("/models", timeout=60)
    out = []
    for x in m.get("data", m):
        p = (x.get("providers") or [{}])[0]
        mods = (x.get("architecture") or {}).get("input_modalities") or []
        out.append({"id": x["id"], "vision": bool(p.get("vision")) or "image" in mods, "input": mods,
                    "output": x.get("output"), "pricing": p.get("pricing"), "ocr": p.get("ocr")})
    return out


def cmd_probe(a) -> int:
    s = schemamod.load()
    have = {r["model"]: r for r in jsonl(PROBE) if r.get("final")}
    listed = vision_models()
    for x in listed:
        mid = x["id"]
        if mid in have and not a.force:
            continue
        rec = {"ts": now(), "model": mid, "listed_input": x["input"], "listed_output": x["output"],
               "pricing": x["pricing"], "page": PILOT_PAGE.relative_to(REPO).as_posix(),
               "prompt_sha256": reader.prompt_sha256(s)}
        if not x["vision"]:
            rec.update(final=True, compatible=False, reason="not vision-capable on /models (no image input)", tries=[])
            with open(PROBE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
            continue
        if mid in DONE:
            rec.update(final=True, compatible=True, reason="read on the 300 before Amendment 6; reads reused", tries=[])
            with open(PROBE, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")
            continue
        params, tries = dict(BASE_PARAMS), []
        while True:
            row = call(mid, PILOT_PAGE, params, s, retries=4)
            p = row["parsed"]
            u = row.get("usage") or {}
            tries.append({"params": dict(params), "error": row.get("error"), "finish_reason": row.get("finish_reason"),
                          "parsed": isinstance((p or {}).get("values"), list),
                          "n_values": len(p["values"]) if p and isinstance(p.get("values"), list) else None,
                          "cost": u.get("cost"), "prompt_tokens": u.get("prompt_tokens"),
                          "completion_tokens": u.get("completion_tokens"), "secs": row["secs"],
                          "content_head": (row.get("content") or "")[:300]})
            err = row.get("error") or ""
            if "HTTP 400" in err and "reasoning" in err.lower() and "reasoning_effort" in params:
                params.pop("reasoning_effort")  # the API rejects the parameter: drop it, record it
                continue
            break
        t = tries[-1]
        ok = t["parsed"] and not t["error"]
        reason = ("accepts the 7-image request and returns parseable JSON" if ok else
                  (f"request refused: {t['error'][:160]}" if t["error"] else
                   f"reply not parseable as {{\"values\": [...]}} (finish_reason {t['finish_reason']})"))
        rec.update(final=True, compatible=bool(ok), reason=reason, params=params, tries=tries)
        with open(PROBE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(mid, "OK" if ok else "NOT COMPATIBLE", reason, t.get("n_values"), t.get("cost"), t.get("secs"))
    return 0


def cmd_plan(_a) -> int:
    """Per-model spend caps from the probe cost (water-filling TOTAL_USD, 15% margin), decided before any read."""
    probes = {r["model"]: r for r in jsonl(PROBE) if r.get("final")}
    run = {m: r for m, r in probes.items() if r["compatible"] and m not in DONE}
    est = {m: (r["tries"][-1]["cost"] or 0.0) for m, r in run.items()}
    need = {m: 300 * c * 1.15 for m, c in est.items()}
    left, caps, todo = TOTAL_USD, {}, sorted(run, key=lambda m: (need[m], m))
    while todo:
        share = left / len(todo)
        m = todo.pop(0)
        caps[m] = round(min(need[m], share), 4)
        left -= caps[m]
    plan = {"ts": now(), "order_sha256": json.loads(ORDER.read_text(encoding="utf-8"))["sha256_of_newline_joined"],
            "daily_usd": DAILY_USD, "total_usd": TOTAL_USD, "endpoint_daily_ceiling": ENDPOINT_DAILY_CEILING,
            "stop_utc": STOP_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"), "prompt_sha256": reader.prompt_sha256(),
            "models": {m: {"params": run[m]["params"], "probe_cost_usd": est[m],
                           "est_full_300_usd": round(300 * est[m], 4), "cap_usd": caps[m],
                           "calls_file": calls_path(m).relative_to(REPO).as_posix()} for m in sorted(run)},
            "not_compatible": {m: r["reason"] for m, r in sorted(probes.items()) if not r["compatible"]},
            "reused": {m: calls_path(m).relative_to(REPO).as_posix() for m in DONE}}
    PLAN.write_text(json.dumps(plan, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(plan, indent=1))
    return 0


# ------------------------------------------------------------------ run
def period_start(t: datetime) -> datetime:
    r = t.replace(hour=16, minute=0, second=0, microsecond=0)
    return r if t >= r else r - timedelta(days=1)


def own_spend_since(start: datetime, models) -> float:
    tot = 0.0
    for m in models:
        for r in jsonl(calls_path(m)):
            if r.get("ts", "") >= start.strftime("%Y-%m-%dT%H:%M:%SZ"):
                tot += r.get("cost_usd") or 0.0
    for r in jsonl(PROBE):
        if r.get("ts", "") >= start.strftime("%Y-%m-%dT%H:%M:%SZ"):
            tot += sum((t.get("cost") or 0.0) for t in r.get("tries", []))
    return tot


def model_spend(m: str) -> float:
    return sum((r.get("cost_usd") or 0.0) for r in jsonl(calls_path(m)))


def cmd_run(a) -> int:
    from twohands import amd, run as runmod
    from twohands.run import committed_clean
    if not a.dry and "Amendment 6" not in (REPO / "PROTOCOL.md").read_text(encoding="utf-8"):
        print("REFUSING: Amendment 6 is not in PROTOCOL.md")
        return 3
    if not a.dry and not (committed_clean("PROTOCOL.md") and committed_clean(PLAN.relative_to(REPO).as_posix())):
        print("REFUSING: PROTOCOL.md and results/bakeoff_plan.json must be committed and unchanged")
        return 3
    s = schemamod.load()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert plan["prompt_sha256"] == reader.prompt_sha256(s)
    order = json.loads(ORDER.read_text(encoding="utf-8"))["order"]
    items = {it["clave"]: it for it in manifest()}
    prepared = {r["clave"]: r for r in jsonl(R / "prepare.jsonl") if r.get("status") in ("ok", "not_located", "unreadable")}
    models = [m for m in plan["models"] if (not a.only or m in a.only.split(","))]
    for m in models:  # reader.MODELS is patched in this process only (record() names the model from it)
        reader.MODELS[slug(m)] = m
    spent_lock = threading.Lock()
    usage_state = {"n": 0}

    def gate_budget(extra: str = "") -> None:
        with spent_lock:
            while True:
                t = datetime.now(timezone.utc)
                if t >= STOP_UTC:
                    raise SystemExit("stop time reached")
                mine = own_spend_since(period_start(t), plan["models"])
                total = None
                try:
                    total = float(amd.usage().get("daily_cost_used_usd") or 0)
                except Exception as e:  # noqa: BLE001
                    log(f"usage read failed: {type(e).__name__}")
                if mine < DAILY_USD and (total is None or total < ENDPOINT_DAILY_CEILING):
                    return
                reset = period_start(t) + timedelta(days=1)
                wait = (reset - t).total_seconds() + 180
                log(f"budget: this run {mine:.3f} USD today, endpoint {total} USD: sleeping {wait / 3600:.1f} h to {reset:%H:%M} UTC")
                time.sleep(wait)

    for pas in range(6):
        done = {m: {k for k, r in last_rows(calls_path(m)).items() if not r.get("error")} for m in models}
        tasks = []
        for i, k in enumerate(order):
            for m in models:
                if k not in done[m]:
                    tasks.append((i, m, k))
        if not tasks:
            break
        log(f"pass {pas + 1}: {len(tasks)} reads to do; " + ", ".join(f"{m} {len(done[m])}/300" for m in models))
        stopped = set()

        def work(t):
            i, m, k = t
            with spent_lock:
                if m in stopped:
                    return
                if model_spend(m) >= plan["models"][m]["cap_usd"]:
                    stopped.add(m)
                    log(f"{m}: spend cap {plan['models'][m]['cap_usd']} USD reached at order position {i}: n = {i}")
                    return
                usage_state["n"] += 1
                check = usage_state["n"] % 8 == 1
            if check:
                gate_budget()
            elif datetime.now(timezone.utc) >= STOP_UTC:
                raise SystemExit("stop time reached")
            it, prep = items[k], prepared.get(k, {"status": "missing"})
            if prep.get("status") != "ok":
                rec = runmod.record(it, prep, slug(m), s, None)
            else:
                row = call(m, REPO / prep["image"], plan["models"][m]["params"], s)
                rec = runmod.record(it, prep, slug(m), s, row)
                rec["wall_s"] = row.get("wall_s")
                rec["params"] = plan["models"][m]["params"]
            rec["order_pos"] = i
            with _lock:
                with open(calls_path(m), "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log(f"{m} #{i} {k} {'ACCEPT' if rec['accepted'] else 'route'} {rec.get('finish_reason')} "
                f"{rec.get('latency_s')}s ${rec.get('cost_usd') or 0:.5f} err={bool(rec.get('error'))}")

        if a.dry:
            print(len(tasks), "tasks;", tasks[:6])
            return 0
        try:
            with ThreadPoolExecutor(CONCURRENCY) as ex:
                list(ex.map(work, tasks))
        except SystemExit as e:
            log(str(e))
            return 0
        if all(m in stopped for m in models):
            break
    log("run complete")
    return 0


# ------------------------------------------------------------------ report
def num(v):
    v = ("" if v is None else str(v)).strip().replace(",", "")
    return int(v) if v.isdigit() else None


def load_verdicts() -> tuple[dict, dict]:
    V = json.loads((R / "adjudication" / "verdicts.json").read_text(encoding="utf-8"))
    B = json.loads(VB.read_text(encoding="utf-8")) if VB.is_file() else {}
    return V, B


def truth(k: str, f: str, prep_val, V: dict, B: dict):
    """(status, paper): status known | undecided | capture (no verdict: the capture is the reference)."""
    v = V.get(f"{k}__{f}") or B.get(f"{k}__{f}")
    if v:
        if v["verdict"] not in ("model_right", "capture_right", "neither", "paper"):
            return "undecided", None
        p = v.get("paper")
        return "known", (None if p == "blank" else p)
    return "capture", prep_val


def compute() -> dict:
    from twohands.gate import gate
    from twohands.tiers import capture_gate, digits, usable, words
    s = schemamod.load()
    keys = s["keys"]
    graded = [f for f in s["fields"] if f.get("csv")]
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    order = json.loads(ORDER.read_text(encoding="utf-8"))["order"]
    with (REPO / "app" / "data" / "audit_sample_prep300.csv").open(encoding="utf-8", newline="") as fh:
        prep = {r["CLAVE_CASILLA"]: r for r in csv.DictReader(fh)}
    V, B = load_verdicts()
    prompt = reader.prompt_sha256(s)
    models = list(DONE) + sorted(plan["models"])
    rows = {m: last_rows(calls_path(m)) for m in models}
    every = {m: jsonl(calls_path(m)) for m in models}
    # n per model: the longest prefix of the fixed order with a final row for every form (a read or a routed no-read)
    n_of = {}
    for m in models:
        n = 0
        while n < len(order) and order[n] in rows[m] and not rows[m][order[n]].get("error"):
            n += 1
        n_of[m] = n
    for m in models:  # a form whose every attempt failed counts as a routed no-read (PROTOCOL 2.3)
        pass

    def accepted(m, k):
        r = rows[m].get(k)
        return bool(r) and bool(r.get("accepted")) and not r.get("error")

    def judge_fields(m, k, vals):
        res = collections.Counter()
        wrong, pending = [], []
        for f in graded:
            pv = num(prep[k][f["csv"]]) if k in prep else None
            st, paper = truth(k, f["key"], pv, V, B)
            mv = vals[f["key"]]
            if st == "undecided":
                res["undecided"] += 1
            elif st == "known":
                if mv == paper:
                    res["right"] += 1
                else:
                    res["wrong"] += 1
                    wrong.append(f"{k}__{f['key']}")
            elif mv == pv:
                res["right"] += 1
            else:
                res["pending"] += 1
                pending.append(f"{k}__{f['key']}")
        return res, wrong, pending

    def block(m, forms):
        R_ = rows[m]
        usable_forms = [k for k in forms if usable(R_.get(k))]
        agree = graded_n = 0
        for k in usable_forms:
            d = digits(R_[k], keys)
            for f in graded:
                pv = num(prep[k][f["csv"]]) if k in prep else None
                if pv is None:
                    continue
                graded_n += 1
                agree += d[f["key"]] == pv
        acc = [k for k in forms if accepted(m, k)]
        tot, wrong, pending = collections.Counter(), [], []
        for k in acc:
            r_, w_, p_ = judge_fields(m, k, digits(R_[k], keys))
            tot += r_
            wrong += w_
            pending += p_
        sent = [k for k in forms if R_.get(k) and not R_[k].get("no_call")]
        costs = [R_[k].get("cost_usd") or 0.0 for k in sent]
        lat = [R_[k].get("latency_s") for k in sent if R_[k].get("latency_s") is not None and usable(R_[k])]
        fs = set(forms)
        spend_all = sum((r.get("cost_usd") or 0.0) for r in every[m] if r["clave"] in fs)
        fr = collections.Counter(str(R_[k].get("finish_reason")) for k in sent)
        return {"n": len(forms), "sent": len(sent), "parsed": len(usable_forms),
                "field_agreement": agree, "graded_fields": graded_n,
                "field_agreement_pct": round(100 * agree / graded_n, 2) if graded_n else None,
                "accepted": len(acc), "accepted_pct": round(100 * len(acc) / len(forms), 1) if forms else None,
                "accepted_fields": sum(tot.values()), "accepted_wrong": tot["wrong"], "accepted_undecided": tot["undecided"],
                "accepted_pending": tot["pending"], "wrong_fields": wrong, "pending_fields": pending,
                "cost_per_1000_usd": round(1000 * spend_all / len(forms), 4) if forms else None,
                "mean_latency_s": round(sum(lat) / len(lat), 1) if lat else None,
                "finish_reason": dict(sorted(fr.items())),
                "prompt_frozen": all(R_[k].get("prompt_sha256") == prompt for k in sent)}

    out = {"prompt_sha256": prompt, "order_sha256": plan["order_sha256"], "models": {}, "pairs": [],
           "not_compatible": plan["not_compatible"], "params": {m: v["params"] for m, v in plan["models"].items()}}
    for m in models:
        forms = order[: n_of[m]]
        b = block(m, forms)
        b["reused"] = m in DONE
        if n_of[m] < len(order):  # on a subset: Gemma and Qwen on the same first-n forms, for a like-for-like line
            b["same_n_reference"] = {d: {kk: block(d, forms)[kk] for kk in ("field_agreement_pct", "accepted", "accepted_wrong")}
                                     for d in DONE}
        out["models"][m] = b

    for i, a_ in enumerate(models):
        for b_ in models[i + 1:]:
            n = min(n_of[a_], n_of[b_])
            forms = order[:n]
            acc, tot, wrong, pending = [], collections.Counter(), [], []
            for k in forms:
                ra, rb = rows[a_].get(k), rows[b_].get(k)
                if not (usable(ra) and usable(rb)):
                    continue
                da, db = digits(ra, keys), digits(rb, keys)
                if da != db:
                    continue
                ok, _ = capture_gate(da, (words(ra, keys), words(rb, keys)), s)
                if not ok:
                    continue
                acc.append(k)
                r_, w_, p_ = judge_fields(a_, k, da)
                tot += r_
                wrong += w_
                pending += p_
            out["pairs"].append({"a": a_, "b": b_, "n": n, "accepted": len(acc),
                                 "accepted_pct": round(100 * len(acc) / n, 1) if n else None,
                                 "accepted_fields": sum(tot.values()), "accepted_wrong": tot["wrong"],
                                 "accepted_undecided": tot["undecided"], "accepted_pending": tot["pending"],
                                 "wrong_fields": wrong, "pending_fields": pending})
    out["pairs"].sort(key=lambda p: (p["accepted_wrong"] + p["accepted_pending"], -(p["accepted"] / p["n"] if p["n"] else 0)))
    out["total_bakeoff_spend_usd"] = round(sum(model_spend(m) for m in plan["models"])
                                           + sum(sum((t.get("cost") or 0.0) for t in r.get("tries", [])) for r in jsonl(PROBE)), 4)
    return out


def short(m: str) -> str:
    return m


def markdown(d: dict) -> str:
    M = d["models"]
    lb = sorted(M.items(), key=lambda kv: (-(kv[1]["field_agreement_pct"] or 0)))
    best = lb[0][0] if lb else None
    pair = d["pairs"][0] if d["pairs"] else None
    L = ["# Which open model on AMD reads handwriting best, and which pair is the safest second keyer", "",
         "Open-model bake-off on AMD Token Factory (PROTOCOL.md Amendment 6; secondary analysis, the primary is unchanged). "
         "Generated by `python scripts/bakeoff.py report`; recomputed independently by `make eval`. No model call.", "",
         f"Every reader got the same masked page + 6 tiles and the same frozen prompt (sha256 `{d['prompt_sha256'][:12]}...`), "
         "temperature 0, the same parser and the same frozen gate. Forms are taken in a fixed capture-stratified shuffled order "
         f"(sha256 `{d['order_sha256'][:12]}...`); a model with n < 300 read the first n forms of that order (budget rule, "
         "Amendment 6). Accepted-field errors are judged against the paper where a verdict exists (the Amendment 2 adjudication, "
         "the certified count where it applies, or the AI adjudicator on the crops), otherwise against the official capture.", ""]
    if best:
        L += [f"**Best reader by field agreement: {best} ({M[best]['field_agreement_pct']}% of graded fields equal to the capture, "
              f"n = {M[best]['n']}).**" + (f" **Safest pair: {pair['a']} + {pair['b']}: {pair['accepted']} of {pair['n']} forms "
                                            f"accepted, {pair['accepted_wrong']} wrong accepted fields.**" if pair else ""), ""]
    L += ["| model | n | field agreement with the capture | accepted forms (frozen gate) | accepted-field errors | "
          "cost per 1,000 forms | mean latency |", "|---|---|---|---|---|---|---|"]
    for m, b in lb:
        err = f"{b['accepted_wrong']} of {b['accepted_fields']:,}"
        if b["accepted_undecided"]:
            err += f" ({b['accepted_undecided']} undecided)"
        if b["accepted_pending"]:
            err += f" ({b['accepted_pending']} not adjudicated)"
        L.append(f"| {m}{' (reads from the 300 run)' if b['reused'] else ''} | {b['n']} | {b['field_agreement_pct']}% "
                 f"({b['field_agreement']:,} / {b['graded_fields']:,}) | {b['accepted']} ({b['accepted_pct']}%) | {err} | "
                 f"${b['cost_per_1000_usd']:.2f} | {b['mean_latency_s']} s |")
    for m, why in d["not_compatible"].items():
        L.append(f"| {m} | - | not compatible: {why} | - | - | - | - |")
    L += ["", "Latency: bake-off models, the server time of the answered request; Gemma and Qwen, the time per form as recorded "
          "in the 300 run (includes waiting for the shared limiter, 2 in flight). Cost: every attempt on the n forms, "
          "per 1,000 forms. Gemma-4-31B-IT was withdrawn from Token Factory on 2026-10-15; its row uses its reads of the 300.", "",
          "## Two readers (both read the form, all 23 digit values agree, every digit read, words = digits where read, "
          "rows sum to TOTAL; Amendment 2 d)", "",
          "| pair | n | accepted forms | accepted-field errors |", "|---|---|---|---|"]
    for p in d["pairs"]:
        e = f"{p['accepted_wrong']} of {p['accepted_fields']:,}"
        if p["accepted_undecided"]:
            e += f" ({p['accepted_undecided']} undecided)"
        if p["accepted_pending"]:
            e += f" ({p['accepted_pending']} not adjudicated)"
        L.append(f"| {p['a']} + {p['b']} | {p['n']} | {p['accepted']} ({p['accepted_pct']}%) | {e} |")
    L += ["", "Pairs are sorted by accepted-field errors (fewest first), then by accepted share.", "",
          "## Per-model parameters", ""]
    for m, prm in d["params"].items():
        L.append(f"- {m}: `{json.dumps(prm)}`")
    L += ["- Gemma-4-31B-IT: `{\"temperature\": 0, \"max_tokens\": 2000}` (section 4)",
          "- Qwen3.8-27B: `{\"temperature\": 0, \"max_tokens\": 6000, \"reasoning_effort\": \"low\"}` (section 4)", "",
          "## Wrong accepted fields", ""]
    for m, b in M.items():
        if b["wrong_fields"] or b["pending_fields"]:
            L.append(f"- {m}: wrong {', '.join(b['wrong_fields']) or 'none'}"
                     + (f"; not adjudicated {', '.join(b['pending_fields'])}" if b["pending_fields"] else ""))
    L += ["", f"Total bake-off spend (probes + reads): ${d['total_bakeoff_spend_usd']:.4f}.", ""]
    return "\n".join(L)


def cmd_report(_a) -> int:
    d = compute()
    OUT_JSON.write_text(json.dumps(d, indent=1) + "\n", encoding="utf-8")
    OUT_MD.write_text(markdown(d), encoding="utf-8")
    for m, b in d["models"].items():
        print(f"{m:32s} n={b['n']:3d} agree {b['field_agreement_pct']}% acc {b['accepted']} wrong {b['accepted_wrong']} "
              f"pending {b['accepted_pending']} undec {b['accepted_undecided']} $/1k {b['cost_per_1000_usd']} lat {b['mean_latency_s']}")
    for p in d["pairs"][:5]:
        print("pair", p["a"], "+", p["b"], p["n"], p["accepted"], p["accepted_wrong"], p["accepted_pending"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["order", "probe", "plan", "run", "report"])
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    return {"order": cmd_order, "probe": cmd_probe, "plan": cmd_plan, "run": cmd_run, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
