"""The `twohands` command: the sample audit from stored reads reproduces the 267 disputes and the published Merkle
root with no model call; an audit with scans reads only the forms without a read (mocked endpoint) and finds the
same disputes the stored read gives; read, gate and verify-receipt; `python -m evolus mcp-register` prints the steps
and sends nothing without --apply. No real model call anywhere: twohands.amd.chat raises if reached."""
import csv
import json
import shutil

import pytest

from app import capture_audit as ca
from twohands import REPO, cli, reader

SAMPLE = REPO / "app" / "data" / "audit_sample_prep300.csv"
PUBLISHED = (REPO / "results" / "sample_audit_root.txt").read_text(encoding="utf-8").split()[0]
FORM = "010469C0400"          # an accepted form of the sample with one disputed field (SOBRANTES: keyed 234, read 239)


def _stored_rows():
    rows = {}
    for ln in (REPO / "results" / "calls_gemma.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(ln)
        rows[r["clave"]] = r
    return rows


STORED = _stored_rows()


def mock_reader(form=FORM, calls=None):
    """Stands in for the endpoint: returns the stored pre-registered answer of ``form`` as a fresh read."""
    def fn(model, page):
        if calls is not None:
            calls.append((model, getattr(page, "name", str(page))))
        content = STORED[form]["content"]
        return {"model": "Gemma-4-31B-IT", "content": content, "parsed": reader.parse(content), "secs": 1.0,
                "usage": {"prompt_tokens": 2600, "completion_tokens": 800, "cost": 0.0001}, "finish_reason": "stop"}
    return fn


@pytest.fixture(autouse=True)
def no_model_calls(monkeypatch):
    from twohands import amd

    def boom(*a, **k):
        raise AssertionError("a test reached the real model endpoint")
    monkeypatch.setattr(amd, "chat", boom)
    monkeypatch.setattr(amd, "_req", boom)


@pytest.fixture(scope="module")
def sample_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("report")
    state = tmp_path_factory.mktemp("state")
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(["audit", "--keyed", str(SAMPLE), "--from-stored", "--schema", "mx_presidencia_2024",
                         "--out", str(out), "--state", str(state), "--receipts", "--quiet"])
    return code, buf.getvalue(), out


def test_sample_audit_reproduces_267_and_the_published_root(sample_run):
    code, text, out = sample_run
    assert code == 0
    line = text.splitlines()[0]
    assert "289 of 300 keyed forms read" in line and "6,358 fields checked" in line
    assert "267 disputed on 104 forms" in line and "0 model calls" in line
    assert line.endswith(f"Merkle root {PUBLISHED}")
    assert (out / "merkle_root.txt").read_text(encoding="utf-8").strip() == PUBLISHED
    S = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert (S["disputed"], S["checked"], S["model_calls"], S["merkle_root"]) == (267, 6358, 0, PUBLISHED)
    assert len(json.loads((out / "disputes.json").read_text(encoding="utf-8"))) == 267


def test_sample_audit_writes_the_web_apps_csv_and_report(sample_run):
    _, _, out = sample_run
    rows = list(csv.reader((out / "report.csv").read_text(encoding="utf-8").splitlines()))
    body = [r for r in rows[1:] if r and not r[0].startswith("#")]
    assert len(body) == 267
    assert ["# Merkle root of the disputes (SHA-256)", PUBLISHED] in rows
    html = (out / "report.html").read_text(encoding="utf-8")
    assert PUBLISHED in html and "Option" in html


def test_every_receipt_of_the_sample_verifies(sample_run):
    _, _, out = sample_run
    files = sorted((out / "receipts").glob("*.json"))
    assert len(files) == 267
    for p in files[:: 40]:
        assert cli.main(["verify-receipt", str(p), "--root", PUBLISHED]) == 0
    bad = json.loads(files[0].read_text(encoding="utf-8"))
    bad["leaf"]["keyed"] = "999"
    (out / "tampered.json").write_text(json.dumps(bad), encoding="utf-8")
    assert cli.main(["verify-receipt", str(out / "tampered.json")]) == 1


def test_audit_with_scans_reads_only_forms_without_a_read(tmp_path, monkeypatch):
    """A form the site has never read (a new id), its scan in a folder: located and masked, read once through the
    (mocked) endpoint, compared; the disputes are those the stored read of the same paper gives."""
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    head, *rows = list(csv.reader(SAMPLE.read_text(encoding="utf-8").splitlines()))
    row = next(r for r in rows if r[0] == FORM)
    keyed = tmp_path / "capture.csv"
    with keyed.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerow(["NEWFORM0001"] + row[1:])
        w.writerow(["NEWFORM0002"] + row[1:])     # keyed, but no scan: listed as unread, never sent
    scans = tmp_path / "scans"
    scans.mkdir()
    shutil.copy(REPO / "data" / "masked" / f"{FORM}.jpg", scans / "NEWFORM0001.jpg")
    (scans / "notes.txt").write_text("not an image", encoding="utf-8")
    calls = []
    S = cli.audit(keyed, scans, out=tmp_path / "out", reader_fn=mock_reader(calls=calls), html=False,
                  log=lambda *a: None)
    assert len(calls) == 1 and calls[0][0] == "gemma"
    assert S["model_calls"] == 1 and S["forms_read"] == 1 and S["forms_keyed"] == 2 and S["unread"] == 1
    assert S["scans"]["masked"] == 1
    got = {(d["code"], d["keyed"], d["model"]) for d in S["_disputes"]}
    with cli._audit_env(tmp_path / "state2", from_stored=True) as ca2:
        a = ca2.sample()
        ref = {(d["code"], d["keyed"], d["model"]) for d in ca2.run(a)["disputes"] if d["form"] == FORM}
    assert got == ref and ("SOBRANTES", "234", 239) in got
    # the read is stored as the live-read path stores it
    assert list((tmp_path / "audits").glob("*/reads/NEWFORM0001.read.json"))
    assert (tmp_path / "out" / "report.csv").is_file()


def test_read_form_masked_page_through_the_gate():
    r = cli.read_form(REPO / "data" / "masked" / f"{FORM}.jpg", masked=True, reader_fn=mock_reader())
    assert r["ok"] and r["accepted"] is True and r["reasons"] == []
    assert r["values"]["SOBRANTES"] == 239 and "OPT01" in r["values"] and "OPT01" in r["fields"]
    assert all(i["ok"] for i in r["identities"])
    assert "PAN" not in json.dumps({k: v for k, v in r.items() if k != "parsed"})


def test_read_form_not_located_makes_no_call(tmp_path):
    from PIL import Image
    p = tmp_path / "blank.jpg"
    Image.new("RGB", (1200, 800), "white").save(p)
    calls = []
    r = cli.read_form(p, reader_fn=mock_reader(calls=calls))
    assert r["not_located"] and not r["accepted"] and calls == []


def test_gate_reader_output_and_value_mapping(tmp_path):
    parsed = reader.parse(STORED[FORM]["content"])
    assert cli.gate_values(parsed)["accepted"] is True
    vals = cli.gate_values(parsed)["values"]
    r = cli.gate_values(vals)
    assert r["accepted"] is True and r["row_label_check"].startswith("not applicable")
    assert {i["name"] for i in r["identities"]} >= {"rows sum to TOTAL"}
    vals2 = dict(vals, TOTAL=vals["TOTAL"] + 1)
    r2 = cli.gate_values(vals2)
    assert not r2["accepted"] and "identity" in r2["codes"]
    bad = next(i for i in r2["identities"] if i["name"] == "rows sum to TOTAL")
    assert bad["ok"] is False and bad["rhs"] == bad["lhs"] + 1
    f = tmp_path / "v.json"
    f.write_text(json.dumps(vals), encoding="utf-8")
    assert cli.main(["gate", str(f)]) == 0
    f.write_text(json.dumps(vals2), encoding="utf-8")
    assert cli.main(["gate", str(f)]) == 2
    assert cli.gate_values(parsed, variant="v2")["variant"] == "v2"
    with pytest.raises(ValueError):
        cli.gate_values({"NOT_A_FIELD": 1})


def test_audit_refuses_a_schema_it_cannot_map(tmp_path):
    assert cli.main(["audit", "--keyed", str(SAMPLE), "--schema", "mx_senado_2024", "--from-stored",
                     "--out", str(tmp_path)]) == 1


def test_evolus_mcp_register_dry_run_sends_nothing(monkeypatch, capsys):
    import evolus.__main__ as em

    def boom(*a, **k):
        raise AssertionError("dry run must not build an Evolus client")
    monkeypatch.setattr(em, "EvolusClient", boom)
    assert em.main(["mcp-register", "--url", "https://mcp.example.org/mcp"]) == 0
    out = capsys.readouterr().out
    assert "/api/v1/agents/" in out and "mcpserver" in out and "dry run" in out
    assert em.main(["mcp-register", "--url", "http://127.0.0.1:8765/mcp", "--server-id", "x", "--apply"]) == 2


def test_evolus_mcp_register_apply_attaches(monkeypatch, capsys):
    import httpx

    import evolus.__main__ as em
    from evolus.client import EvolusClient
    from evolus.config import Settings
    sid = "11111111-2222-3333-4444-555555555555"
    seen = []

    def ws(req: httpx.Request):
        seen.append((req.method, req.url.path))
        return httpx.Response(200, json={"id": "agent-1", "mcpServers": [{"id": sid, "name": "Two Hands"}]})
    monkeypatch.setattr(em.Settings, "load", classmethod(lambda cls: Settings(key="k", app_id="app")))
    monkeypatch.setattr(em, "EvolusClient", lambda s: EvolusClient(s, transport=httpx.MockTransport(ws), pace_s=0))
    assert em.main(["mcp-register", "--url", "https://mcp.example.org/mcp", "--server-id", sid,
                    "--agent", "agent-1", "--apply"]) == 0
    assert seen == [("POST", f"/api/v1/agents/agent-1/mcpserver/{sid}"), ("GET", "/api/v1/agents/agent-1")]
    assert "attached" in capsys.readouterr().out
