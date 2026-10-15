"""Two Hands as an MCP server (the official `mcp` Python SDK): four tools, over stdio or streamable HTTP.

    python -m twohands.mcp_server                       # stdio (an AI model Desktop, a coding assistant, any local MCP client)
    python -m twohands.mcp_server --http --port 8765    # streamable HTTP at http://127.0.0.1:8765/mcp
    twohands mcp [--http]                               # the same, from the installed command

Tools (each a thin wrapper over twohands.cli, which reuses the core and app.capture_audit):
  read_form       a masked page (path or base64) -> values, words and labels by field, the gate's verdict
  gate            values + schema -> every identity (lhs, rhs, ok) and the verdict (frozen gate, or v2 / v2b)
  audit_capture   keyed CSV + stored or new reads -> disputes summary, the first disputes, report and CSV paths
  verify_receipt  an audit receipt (JSON or path) [+ crop] [+ root] -> each check and VERIFIED / NOT VERIFIED

Safety: file paths must lie under the repository, the working directory or TWOHANDS_MCP_ROOTS (os.pathsep list).
Over HTTP, tools that would call the model (read_form, audit_capture without stored reads) are refused unless the
server was started with --allow-reads: a public endpoint must not spend the model budget for anyone who finds it.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from twohands import REPO
from twohands import cli

NAME = "two-hands"
INSTRUCTIONS = ("Two Hands checks numbers keyed from self-checking paper forms against the paper. read_form reads one "
                "privacy-masked page; gate checks a read against the form's own arithmetic; audit_capture compares a "
                "keyed CSV with the reads and lists every disputed field by strength of evidence; verify_receipt "
                "checks a disputed field's Merkle receipt. A disputed field is a lead for a person, not a finding.")
STATE = {"allow_reads": True}


class ToolRefused(Exception):
    pass


def _roots() -> list[Path]:
    env = os.environ.get("TWOHANDS_MCP_ROOTS")
    roots = [Path(p) for p in env.split(os.pathsep) if p] if env else [REPO, Path.cwd()]
    return [r.resolve() for r in roots]


def _safe(p: str) -> Path:
    q = Path(p).expanduser()
    q = (q if q.is_absolute() else Path.cwd() / q).resolve()
    if not any(q == r or r in q.parents for r in _roots()):
        raise ToolRefused(f"path outside the allowed folders: {p}")
    return q


def _need_reads(what: str) -> None:
    if not STATE["allow_reads"]:
        raise ToolRefused(f"{what} would call the model; this server was started without --allow-reads")


# ------------------------------------------------------------------------------------------------ the tools
def read_form(image_path: Optional[str] = None, image_base64: Optional[str] = None,
              schema: str = cli.DEFAULT_SCHEMA, model: str = "gemma", masked: bool = True,
              layout: str = "movil") -> dict:
    """Read one form. Give a privacy-masked page (image_path, or image_base64 of a JPEG/PNG). With masked=false
    the image is first located, straightened and masked (the right-hand column with names and signatures is
    blacked out) before anything is sent. One request to the configured model endpoint; the gate then checks
    words against digits and the form's own sums. Returns values by field (vote rows as Option NN), words,
    printed labels, accepted (true = no person needed), the reasons a person is needed, and the identities."""
    _need_reads("read_form")
    if bool(image_path) == bool(image_base64):
        raise ToolRefused("give exactly one of image_path or image_base64")
    img: Any = _safe(image_path) if image_path else base64.b64decode(image_base64.split(",", 1)[-1])
    r = cli.read_form(img, schema, model, masked, layout)
    r.pop("parsed", None)
    return r


def gate(values: Any, schema: str = cli.DEFAULT_SCHEMA, variant: str = "v1") -> dict:
    """The gate on one read. values: the reader's JSON ({"values": [{label, n, w}, ...]}) or a mapping field ->
    number (or -> {"n", "w"}), fields named by schema key, code (OPT07) or name (Option 07). variant: v1 = the
    frozen, pre-registered gate; v2 / v2b = post-hoc variants. Returns accepted, the reasons, every identity
    with both sides and whether it holds, and the failing fields."""
    return cli.gate_values(values, schema, variant)


def audit_capture(keyed_csv_path: Optional[str] = None, keyed_csv_text: Optional[str] = None,
                  scans_dir: Optional[str] = None, from_stored: bool = True, strict: bool = False,
                  out_dir: Optional[str] = None, max_disputes: int = 20) -> dict:
    """Audit a keyed capture: compare every keyed field with the paper's read. keyed_csv_path or keyed_csv_text:
    one row per form (INE PREP column names are detected). from_stored=true uses the stored pre-registered reads
    and calls no model (on the sample, app/data/audit_sample_prep300.csv, it gives the 267 disputed fields and the
    published Merkle root); from_stored=false reads forms without a read from scans_dir (images named
    <form id>.jpg). Returns the summary (forms, fields checked, disputed, tiers, Merkle root), the first disputes
    in report order, and the paths of the report (HTML and CSV)."""
    if bool(keyed_csv_path) == bool(keyed_csv_text):
        raise ToolRefused("give exactly one of keyed_csv_path or keyed_csv_text")
    if not from_stored:
        _need_reads("audit_capture with from_stored=false")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out = _safe(out_dir) if out_dir else REPO / "out" / "mcp" / f"audit-{stamp}"
    if keyed_csv_text:
        out.mkdir(parents=True, exist_ok=True)
        keyed = out / "keyed.csv"
        keyed.write_text(keyed_csv_text, encoding="utf-8")
    else:
        keyed = _safe(keyed_csv_path)
    S = cli.audit(keyed, _safe(scans_dir) if scans_dir else None, out=out, from_stored=from_stored,
                  strict=strict, log=lambda *a: None)
    D = S.pop("_disputes")
    keep = ("pos", "form", "code", "name", "keyed", "model", "words", "tier", "score")
    S["disputes"] = [{k: d.get(k) for k in keep} | {"signals": [s["text"] for s in d["signals"]]}
                     for d in D[:max(0, int(max_disputes))]]
    S["line"] = cli.summary_line(S)
    S["report_path"] = str(out / "report.html")
    S["csv_path"] = str(out / "report.csv")
    return S


def verify_receipt(receipt: Optional[dict] = None, receipt_path: Optional[str] = None,
                   crop_base64: Optional[str] = None, root: Optional[str] = None) -> dict:
    """Check one audit receipt (what /audit/<id>/receipt/<key> or `twohands audit --receipts` gives): recompute
    the leaf from its record, check the crop's SHA-256 when the crop is given, walk the proof path to the root,
    and compare that root with one you hold (root). Returns each check and verified."""
    from twohands import verify_receipt as vr
    if bool(receipt) == bool(receipt_path):
        raise ToolRefused("give exactly one of receipt or receipt_path")
    rc = receipt if receipt else json.loads(_safe(receipt_path).read_text(encoding="utf-8"))
    crop = base64.b64decode(crop_base64.split(",", 1)[-1]) if crop_base64 else None
    res = vr.check(rc, crop, root)
    rec = rc["leaf"]
    return {"verified": all(ok for _, ok, _ in res), "root": rc["root"],
            "field": {k: rec.get(k) for k in ("form", "field", "keyed", "model", "words", "tier")},
            "checks": [{"check": c, "ok": ok, "hash": h} for c, ok, h in res]}


TOOLS = (read_form, gate, audit_capture, verify_receipt)


# ------------------------------------------------------------------------------------------------ the server
def build(host: str = "127.0.0.1", port: int = 8765, allow_reads: bool = True, public_hosts: tuple = ()):
    """The MCP server with the four tools (mcp 1.x FastMCP; mcp 2.x MCPServer). ``public_hosts``: the host names a
    tunnel or reverse proxy forwards (e.g. twohands-mcp.example.org), accepted in the Host header besides localhost
    (the SDK's DNS-rebinding protection stays on)."""
    STATE["allow_reads"] = allow_reads
    try:
        from mcp.server.fastmcp import FastMCP
        kw = {}
        if public_hosts:
            from mcp.server.transport_security import TransportSecuritySettings
            kw["transport_security"] = TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", *public_hosts],
                allowed_origins=["http://127.0.0.1:*", "http://localhost:*", *(f"https://{h}" for h in public_hosts)])
        srv = FastMCP(NAME, instructions=INSTRUCTIONS, host=host, port=port, **kw)
    except ImportError:  # mcp >= 2: FastMCP was renamed MCPServer; host and port go to run()
        from mcp.server.mcpserver import MCPServer
        srv = MCPServer(NAME, instructions=INSTRUCTIONS)
    for fn in TOOLS:
        srv.add_tool(fn, name=fn.__name__, description=fn.__doc__)
    srv._twohands = {"host": host, "port": port}
    return srv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m twohands.mcp_server", description=__doc__.split("\n\n")[0])
    ap.add_argument("--http", action="store_true", help="streamable HTTP at http://HOST:PORT/mcp (default: stdio)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--allow-reads", action="store_true", help="over HTTP, allow tools that call the model")
    ap.add_argument("--public-host", action="append", default=[],
                    help="a public host name forwarded to this server (tunnel / reverse proxy); repeatable")
    a = ap.parse_args(argv)
    srv = build(a.host, a.port, allow_reads=(a.allow_reads or not a.http), public_hosts=tuple(a.public_host))
    if not a.http:
        srv.run("stdio")
        return 0
    print(f"Two Hands MCP server: http://{a.host}:{a.port}/mcp (model reads "
          f"{'allowed' if STATE['allow_reads'] else 'refused; --allow-reads to allow'})", file=sys.stderr)
    try:
        srv.run("streamable-http")
    except TypeError:  # mcp >= 2
        srv.run("streamable-http", host=a.host, port=a.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
