"""Command line for the Evolus integration (run from the twohands/ folder).

    python -m evolus setup [--model M]         find or create agent, extractor, library, workflow -> evolus/ids.json
    python -m evolus check                     which blocks are configured; lists agents, AI Tools, library docs
    python -m evolus fields                    the extractor field list to paste into the Evolus extractor editor
    python -m evolus run --forms A,B,C         run the intake case on these masked forms -> results/evolus_runs.jsonl
    python -m evolus run --pick 2,3            pick 2 accepted + 3 routed forms (by the measured read) and run them

Never prints a key: settings are reported as set / not set.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import store as storemod  # noqa: E402
from evolus import case as casemod  # noqa: E402
from evolus.client import EvolusClient, EvolusError, NotConfigured  # noqa: E402
from evolus.config import Settings, redact  # noqa: E402


def cmd_check(_a) -> int:
    s = Settings.load()
    print("configured:", json.dumps(s.configured()))
    c = EvolusClient(s)
    try:
        ms = c.models()
        print(f"agents (GET /v1/models): {[m.get('id') for m in ms] or 'none yet'}")
        if s.app_id:
            cat = c.ai_tools()
            tools = cat if isinstance(cat, list) else (cat or {}).get("tools") or (cat or {}).get("data") or cat
            names = [t.get("slug") or t.get("id") or t.get("name") for t in tools] if isinstance(tools, list) else str(tools)[:300]
            print("AI Tools (GET /api/v1/ai-tools):", names)
            print("translate options picked:", casemod.translate_options(cat))
        if s.app_id and s.library_id:
            docs = c.list_documents(s.library_id)
            print("library documents:", str(redact(docs))[:400])
    except (EvolusError, NotConfigured) as e:
        print("error:", redact(str(e)))
        return 1
    finally:
        print("calls:", json.dumps(c.calls))
    return 0


def cmd_setup(a) -> int:
    from evolus.setup import Setup
    c = EvolusClient(Settings.load())
    try:
        ids = Setup(c, model=a.model, model_key=a.model_key, reviewer_email=a.reviewer_email, rebuild=a.rebuild).run()
    except (EvolusError, NotConfigured) as e:
        print("error:", redact(str(e)))
        print("calls:", len(c.calls))
        return 1
    print("ids saved to evolus/ids.json:", json.dumps({k: v for k, v in ids.items() if k != "names"}))
    print(f"Evolus API calls: {len(c.calls)} (no model calls)")
    return 0


def cmd_fields(_a) -> int:
    print(json.dumps(casemod.extractor_fields(), indent=1, ensure_ascii=False))
    return 0


def pick(n_acc: int, n_rout: int) -> list[str]:
    st = storemod.get_store()
    acc, rout = [], []
    for k in st.ine_claves():
        r = st.default_read(k)
        if r is None or st.masked_image(k) is None or r.not_located:
            continue
        ev = storemod.evaluate(r)
        (acc if ev["accepted"] else rout).append((k, ev))
    # routed: prefer one words/digits mismatch and one identity-only failure, so the hand-off differs
    words = [k for k, ev in rout if any(f["status"] == "words" for f in ev["fields"])]
    ident = [k for k, ev in rout if not ev["failing"]]
    others = [k for k, _ in rout]
    chosen_r = list(dict.fromkeys(words[:1] + ident[:1] + others))[:n_rout]
    return [k for k, _ in acc][:n_acc] + chosen_r


def cmd_run(a) -> int:
    forms = [x.strip() for x in a.forms.split(",") if x.strip()] if a.forms else pick(*map(int, a.pick.split(",")))
    s = Settings.load()
    c = EvolusClient(s)
    out = Path(a.out)
    total_amd = 0
    for k in forms:
        try:
            rec = casemod.Case(k, c, poll_s=a.poll).run()
        except ValueError as e:
            print("skip:", e)
            continue
        casemod.save(rec, out)
        total_amd += rec.get("amd_calls_via_evolus", 0)
        print(f"{k}: {rec['decision']} - {rec['decision_reason'][:100]}")
        for st in rec["steps"]:
            print(f"   [{st['status']:>7}] {st['block']}: {st.get('summary', '')[:110]}")
    print(f"Evolus API calls: {len(c.calls)}; AMD model calls triggered through Evolus agent chat: {total_amd}")
    print(f"records appended to {out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m evolus")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("fields").set_defaults(fn=cmd_fields)
    su = sub.add_parser("setup")
    su.add_argument("--model", default="Qwen3.8-27B", help="the connected model (Your models), e.g. Gemma-4-31B-IT")
    su.add_argument("--model-key", default="", help="exact Evolus model key, e.g. own/<alias>, if the guess fails")
    su.add_argument("--reviewer-email", default=Settings.load().reviewer_email, help="adds an Email hand-off step")
    su.add_argument("--rebuild", action="store_true", help="delete and recreate the workflow")
    su.set_defaults(fn=cmd_setup)
    r = sub.add_parser("run")
    r.add_argument("--forms", default="")
    r.add_argument("--pick", default="2,3", help="accepted,routed counts when --forms is not given")
    r.add_argument("--out", default=str(casemod.RUNS_FILE))
    r.add_argument("--poll", type=float, default=240.0, help="seconds to wait for each workflow run")
    r.set_defaults(fn=cmd_run)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
