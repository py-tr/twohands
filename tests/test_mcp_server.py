"""The MCP server, in-process (no subprocess, no network, no model call): the four tools are listed with their
schemas, and each answers through a real MCP client session (the SDK's in-memory transport) as it would over
stdio or streamable HTTP."""
import asyncio
import json

import pytest

# the MCP SDK is an optional extra (pip install -e ".[mcp]"), not in requirements.txt: skip without it
pytest.importorskip("mcp")

from app import capture_audit as ca
from twohands import REPO, cli, reader
from twohands import mcp_server as M

PUBLISHED = (REPO / "results" / "sample_audit_root.txt").read_text(encoding="utf-8").split()[0]
FORM = "010469C0400"
TOOLS = ["read_form", "gate", "audit_capture", "verify_receipt"]


def _content(form):
    for ln in reversed((REPO / "results" / "calls_gemma.jsonl").read_text(encoding="utf-8").splitlines()):
        r = json.loads(ln)
        if r["clave"] == form:
            return r["content"]


@pytest.fixture(autouse=True)
def env(monkeypatch, tmp_path):
    from twohands import amd

    def boom(*a, **k):
        raise AssertionError("a test reached the real model endpoint")
    monkeypatch.setattr(amd, "chat", boom)
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    monkeypatch.setenv("TWOHANDS_MCP_ROOTS", f"{REPO}{__import__('os').pathsep}{tmp_path}")
    content = _content(FORM)
    monkeypatch.setattr(cli, "default_reader", lambda base_url=None: (
        lambda model, page: {"model": "Gemma-4-31B-IT", "content": content, "parsed": reader.parse(content),
                             "secs": 1.0, "usage": {}}))
    yield
    M.STATE["allow_reads"] = True


def session_call(server, name, args):
    """One tool call through a real client session over the SDK's in-memory transport."""
    from mcp.shared.memory import create_connected_server_and_client_session

    async def go():
        async with create_connected_server_and_client_session(server._mcp_server) as s:
            tools = await s.list_tools()
            res = await s.call_tool(name, args)
            return [t.name for t in tools.tools], res
    return asyncio.run(go())


def payload(res):
    if getattr(res, "structuredContent", None):
        sc = res.structuredContent
        return sc.get("result", sc)
    return json.loads(res.content[0].text)


def test_tools_listed_with_schemas():
    srv = M.build()
    tools = asyncio.run(srv.list_tools())
    assert [t.name for t in tools] == TOOLS
    by = {t.name: t for t in tools}
    assert "image_path" in by["read_form"].inputSchema["properties"]
    assert "values" in by["gate"].inputSchema["required"]
    assert "from_stored" in by["audit_capture"].inputSchema["properties"]
    assert all(t.description for t in tools)


def test_gate_tool_over_a_session():
    vals = cli.gate_values(reader.parse(_content(FORM)))["values"]
    names, res = session_call(M.build(), "gate", {"values": vals})
    assert names == TOOLS and not res.isError
    r = payload(res)
    assert r["accepted"] is True and all(i["ok"] for i in r["identities"])
    _, res2 = session_call(M.build(), "gate", {"values": dict(vals, TOTAL=vals["TOTAL"] + 2)})
    r2 = payload(res2)
    assert r2["accepted"] is False and "rows sum to TOTAL" in " ".join(r2["reasons"])


def test_audit_capture_sample_from_stored_and_verify_a_receipt(tmp_path):
    out = tmp_path / "mcp-audit"
    _, res = session_call(M.build(allow_reads=False), "audit_capture",
                          {"keyed_csv_path": str(REPO / "app" / "data" / "audit_sample_prep300.csv"),
                           "from_stored": True, "out_dir": str(out), "max_disputes": 5})
    assert not res.isError
    S = payload(res)
    assert (S["disputed"], S["checked"], S["model_calls"], S["merkle_root"]) == (267, 6358, 0, PUBLISHED)
    assert len(S["disputes"]) == 5 and S["disputes"][0]["pos"] == 1
    assert S["report_path"].endswith("report.html") and (out / "report.csv").is_file()
    # a receipt for the first disputed field, checked by the verify_receipt tool against the published root
    with cli._audit_env(None, from_stored=True) as c:
        a = c.sample()
        R = c.run(a)
        rc = c.receipt(a, R, R["disputes"][0]["key"])
    _, res = session_call(M.build(), "verify_receipt", {"receipt": rc, "root": PUBLISHED})
    v = payload(res)
    assert v["verified"] is True and len(v["checks"]) == 3
    rc["leaf"]["model"] = 1
    _, res = session_call(M.build(), "verify_receipt", {"receipt": rc})
    assert payload(res)["verified"] is False


def test_read_form_tool_and_the_http_guard():
    page = str(REPO / "data" / "masked" / f"{FORM}.jpg")
    _, res = session_call(M.build(), "read_form", {"image_path": page})
    r = payload(res)
    assert not res.isError and r["accepted"] is True and r["values"]["SOBRANTES"] == 239
    _, res = session_call(M.build(allow_reads=False), "read_form", {"image_path": page})
    assert res.isError and "allow-reads" in res.content[0].text
    _, res = session_call(M.build(), "read_form", {"image_path": "C:/Windows/win.ini"})
    assert res.isError and "outside the allowed folders" in res.content[0].text
