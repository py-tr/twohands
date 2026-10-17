"""Command line for the Evolus integration (run from the twohands/ folder).

    python -m evolus setup [--model M]         find or create agent, extractor, library, workflow -> evolus/ids.json
    python -m evolus check                     which blocks are configured; lists agents, AI Tools, library docs
    python -m evolus fields                    the extractor field list to paste into the Evolus extractor editor
    python -m evolus run --forms A,B,C         run the intake case on these masked forms -> results/evolus_runs.jsonl
    python -m evolus run --pick 2,3            pick 2 accepted + 3 routed forms (by the measured read) and run them
    python -m evolus audit [--audit ID]        open the strong-evidence fields of an audit (default: a new sample
                                               audit) as Evolus audit cases -> results/evolus_audit_runs.jsonl
    python -m evolus routed --plan r300:100,colima:50
                                               routed fields of real reads as "Audit finding" cases, paced and
                                               idempotent -> results/evolus/executions.jsonl (--dry-run: list only)
    python -m evolus mcp-register --url U      print the steps to connect the Two Hands MCP server to the agent;
        [--server-id ID --apply]               with --apply, attach the server (once added in Evolus) to the agent

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
    from evolus.setup import ensure_user_blocks
    if ensure_user_blocks(c, log=print):
        print("EVOLUS_USER_KEY found: extractor and library built")
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


def cmd_audit(a) -> int:
    from app import capture_audit as ca
    from evolus import audit as auditmod
    from evolus.setup import ensure_user_blocks
    s = Settings.load()
    c = EvolusClient(s)
    if ensure_user_blocks(c, log=print):
        print("EVOLUS_USER_KEY found: extractor and library built")
    au = ca.load(a.audit) if a.audit else ca.sample()
    if au is None:
        print("unknown audit")
        return 1
    R = ca.run(au)
    strong = [d for d in R["disputes"] if d["tier"] == "strong"]
    print(f"audit {au['id']}: {R['disputed']} disputed fields, {len(strong)} with strong evidence")
    r = auditmod.AuditRunner(c, au, max_cases=a.max, poll_every=a.poll_every, poll_s=a.poll,
                             log=print, results=Path(a.out))
    try:
        done = r.run(R["disputes"])
    except NotConfigured as e:
        print("error:", e)
        return 1
    back = [x for x in done if x.get("finding")]
    print(f"{len(done)} cases finished this call ({r.amd_calls} newly sent), {len(back)} with a drafted finding")
    print(f"Evolus API calls: {len(c.calls)}; AMD model calls through Evolus: {r.amd_calls} (shared limiter tokens taken)")
    print(f"report: /audit/{au['id']}/report ; records appended to {a.out}")
    return 0


MCP_STEPS = """Connect the Two Hands MCP server to the Evolus agent

The Evolus API attaches an MCP server that already exists in one of the application's MCP collections to an agent
(POST /api/v1/agents/{{agentId}}/mcpserver/{{mcpServerId}}, docs/evolus-openapi.json); it has no endpoint to create
the server entry itself, and Evolus connects to the server from its own cloud, so the server must be reachable on
a public HTTPS URL first.

1. Run the server on a host Evolus can reach (streamable HTTP; model reads stay off unless --allow-reads):
     twohands mcp --http --host 127.0.0.1 --port 8765 --public-host {host}
   behind HTTPS (a reverse proxy, or a tunnel such as `cloudflared tunnel --url http://127.0.0.1:8765`).
   Check it from outside: an MCP client listing tools at {url} shows read_form, gate, audit_capture, verify_receipt.
2. In the Evolus workspace (py_tr): the Connectors page -> add a custom MCP server by hand:
     name: Two Hands   transport: Streamable HTTP   url: {url}   auth: none (read-only tools; model reads off)
   Copy the new server's id (a UUID).
3. Attach it to the agent (agent {agent}):
     python -m evolus mcp-register --url {url} --server-id <that id> --apply
   which calls POST /api/v1/agents/{agent}/mcpserver/<id> and reads the agent back to show it in mcpServers.
4. Ask the agent: "gate these values: ..." or "audit the sample capture from stored reads".
"""


def cmd_mcp_register(a) -> int:
    from urllib.parse import urlparse
    from evolus.config import load_ids
    agent_id = a.agent or str(load_ids().get("agent_id") or "")
    agent = agent_id or "<agent id: python -m evolus setup>"
    u = urlparse(a.url)
    host = u.hostname or "<public host>"
    print(MCP_STEPS.format(url=a.url, host=host, agent=agent))
    if not a.apply:
        print("(dry run: nothing was sent to Evolus; add --server-id and --apply to attach)")
        return 0
    if u.scheme != "https" or host in ("localhost", "127.0.0.1", "::1") or host.startswith(("10.", "192.168.")):
        print("refused: Evolus must reach the server on a public https URL (not localhost or a private address)")
        return 2
    if not a.server_id or not agent_id:
        print("refused: --server-id (from step 2) and an agent id (evolus/ids.json or --agent) are needed")
        return 2
    c = EvolusClient(Settings.load())
    try:
        c.rest("POST", f"/api/v1/agents/{agent}/mcpserver/{a.server_id}",
               "POST /api/v1/agents/{agentId}/mcpserver/{mcpServerId}")
        ag = c.rest("GET", f"/api/v1/agents/{agent}", "GET /api/v1/agents/{agentId}")
    except (EvolusError, NotConfigured) as e:
        print("error:", redact(str(e)))
        return 1
    finally:
        print("calls:", json.dumps(c.calls))
    names = [m.get("name") or m.get("id") for m in (ag or {}).get("mcpServers") or []]
    ok = a.server_id in [m.get("id") for m in (ag or {}).get("mcpServers") or []]
    print(f"agent {agent} MCP servers: {names}")
    print("attached" if ok else "not attached: check the server id belongs to this application's MCP collection")
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m evolus")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    sub.add_parser("fields").set_defaults(fn=cmd_fields)
    su = sub.add_parser("setup")
    from evolus.config import load_ids
    cur = str(load_ids().get("model_key") or "").split("/", 1)[-1]
    su.add_argument("--model", default=cur or "Gemma-4-31B-IT",
                    help="the connected model (Your models); default: the agents' current model (evolus/ids.json)")
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
    au = sub.add_parser("audit")
    au.add_argument("--audit", default="", help="audit id (default: create the sample audit of the 300 forms)")
    au.add_argument("--max", type=int, default=18, help="at most this many fields (= AMD calls)")
    au.add_argument("--poll", type=float, default=360.0, help="per-case timeout in seconds (then status 'timeout')")
    au.add_argument("--poll-every", type=float, default=8.0)
    au.add_argument("--out", default=str(storemod.RESULTS / "evolus_audit_runs.jsonl"))
    au.set_defaults(fn=cmd_audit)
    ro = sub.add_parser("routed", help="routed fields of real reads as 'Audit finding' cases (ledger, paced)")
    ro.add_argument("--plan", default="r300:100,colima:50", help="source:count,... (sources: r300, colima)")
    ro.add_argument("--cap", type=int, default=150, help="at most this many executions in this call")
    ro.add_argument("--interval", type=float, default=25.0, help="seconds between two starts")
    ro.add_argument("--in-flight", type=int, default=4)
    ro.add_argument("--after-pid", type=int, default=0, help="wait (polling every 10 min) until this process ends")
    ro.add_argument("--wait-max", type=int, default=7200, help="give up waiting for --after-pid after this many s")
    ro.add_argument("--dry-run", action="store_true", help="build and check the cases; send nothing")
    ro.set_defaults(fn=lambda a: __import__("evolus.routed", fromlist=["main"]).main(a))
    mr = sub.add_parser("mcp-register", help="connect the Two Hands MCP server to the agent (steps; --apply)")
    mr.add_argument("--url", required=True, help="the public https URL of the MCP endpoint, e.g. https://h/mcp")
    mr.add_argument("--server-id", default="", help="the MCP server id Evolus gave it (step 2)")
    mr.add_argument("--agent", default="", help="agent id (default: evolus/ids.json agent_id)")
    mr.add_argument("--apply", action="store_true", help="send the attach call (default: print the steps only)")
    mr.set_defaults(fn=cmd_mcp_register)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
