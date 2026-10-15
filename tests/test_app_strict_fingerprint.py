"""Audit report: strict mode (a field is strong only if two readers, Gemma and Qwen, both read the same value that
differs from the keyed one; stored Qwen reads where present, "second reader not available" where not) and the report
fingerprint (SHA-256 of the report's content plus the input file hashes, on the report and in the CSV export).
The second reader's file is a temporary file here: results/calls_qwen.jsonl is only ever read."""
import csv
import hashlib
import io
import json
import re

import pytest
from fastapi.testclient import TestClient

from app import capture_audit as ca
from app.main import app
from app.store import key_of
from tests.test_app_neutral import _clean

client = TestClient(app)


@pytest.fixture(autouse=True)
def audits(tmp_path, monkeypatch):
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    return tmp_path / "audits"


def _second(tmp_path, monkeypatch, rows, name="calls_qwen.jsonl"):
    p = tmp_path / name
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    monkeypatch.setattr(ca, "SECOND_RUN", p)
    return p


def _gemma_rows():
    return [json.loads(json.dumps(r)) for r in ca.stored_reads().values()]


def test_strict_mode_needs_two_readers(tmp_path, monkeypatch):
    a = ca.load(client.post("/api/audit/sample").json()["id"])
    std = ca.run(a)
    strong = {d["key"] for d in std["disputes"] if d["tier"] == "strong"}
    assert strong and std["second"] is None and "second" not in std["disputes"][0]
    # a second reader that reads every form exactly as Gemma did: strict keeps every strong field
    _second(tmp_path, monkeypatch, _gemma_rows())
    R = ca.run(a, strict=True)
    assert {d["key"] for d in R["disputes"] if d["tier"] == "strong"} == strong
    assert R["second"]["demoted"] == 0
    # half the forms have no second read; on the rest the second reader saw something else on one strong field
    rows = _gemma_rows()
    keep = {r["clave"] for r in rows[::2]}
    first = next(d for d in std["disputes"] if d["tier"] == "strong" and d["form"] in keep)
    changed = []
    for r in rows:
        if r["clave"] not in keep:
            continue
        if r["clave"] == first["form"]:
            r["fields"][key_of(first["code"])]["n"] = (first["model"] or 0) + 1
        changed.append(r)
    _second(tmp_path, monkeypatch, changed, "half.jsonl")
    R = ca.run(a, strict=True)
    by = {d["key"]: d for d in R["disputes"]}
    for d in R["disputes"]:
        if d["tier"] == "strong":
            assert d["second"]["available"] and d["second"]["agrees"]
            assert d["second"]["value"] == d["model"] != d["keyed_n"]
        if d["form"] not in keep:
            assert d["second"]["text"] == "second reader not available" and d["tier"] != "strong"
    assert by[first["key"]]["tier"] == "medium" and by[first["key"]].get("demoted")
    assert by[first["key"]]["second"]["text"].startswith("second reader (Qwen) read ")
    assert R["second"]["missing"] == sum(d["form"] not in keep for d in R["disputes"]) > 0
    assert {d["key"] for d in R["disputes"] if d["tier"] == "strong"} < strong
    # strict lists by tier: every strong field before every medium one before every weak one
    tiers = [d["tier"] for d in R["disputes"]]
    assert tiers == sorted(tiers, key=["strong", "medium", "weak"].index)
    assert [d["pos"] for d in R["disputes"]] == list(range(1, len(tiers) + 1))
    # no second reader file at all: nothing is strong, and every field says why
    monkeypatch.setattr(ca, "SECOND_RUN", tmp_path / "missing.jsonl")
    R = ca.run(a, strict=True)
    assert R["tiers"]["strong"] == 0
    assert all(d["second"]["text"] == "second reader not available" for d in R["disputes"])


def test_strict_report_page_and_csv(tmp_path, monkeypatch):
    rows = _gemma_rows()
    _second(tmp_path, monkeypatch, rows[: len(rows) // 2])
    aid = client.post("/api/audit/sample").json()["id"]
    html = client.get(f"/audit/{aid}/report?strict=1").text
    assert "Strict mode." in html and "Second reader not available" in html and 'aria-checked="true"' in html
    assert "Both readers read" in html
    _clean(html, "strict report")
    std = client.get(f"/audit/{aid}/report").text
    assert 'aria-checked="false"' in std and "Strict mode." not in std and f"/audit/{aid}/report?strict=1" in std
    text = client.get(f"/audit/{aid}/report.csv?strict=1").text
    _clean(text, "strict csv")
    rs = [r for r in csv.DictReader(io.StringIO(text)) if not r["position"].startswith("#")]
    assert len(rs) == 267 and all(r["second reader (Qwen)"] for r in rs)
    assert any(r["second reader (Qwen)"] == "second reader not available" for r in rs)


def _fp_html(html):
    return re.search(r'id="fingerprint">([0-9a-f]{64})<', html).group(1)


def _fp_csv(text):
    return next(r[1] for r in csv.reader(io.StringIO(text)) if r and r[0] == "# report fingerprint (SHA-256)")


def test_report_fingerprint(tmp_path, monkeypatch):
    _second(tmp_path, monkeypatch, _gemma_rows()[:100])
    aid = client.post("/api/audit/sample").json()["id"]
    a = ca.load(aid)
    for q in ("", "?strict=1"):
        h1 = _fp_html(client.get(f"/audit/{aid}/report{q}").text)
        assert h1 == _fp_html(client.get(f"/audit/{aid}/report{q}").text)  # deterministic
        assert _fp_csv(client.get(f"/audit/{aid}/report.csv{q}").text) == h1  # report and CSV print the same one
    std, strict = (_fp_html(client.get(f"/audit/{aid}/report{q}").text) for q in ("", "?strict=1"))
    assert std != strict
    # the fingerprint is the hash of the content hash and the input hashes, all printed
    fp = ca.fingerprint(a, ca.run(a, strict=True))
    assert fp["sha256"] == strict
    assert [i["file"] for i in fp["inputs"]] == ["keyed.csv", "calls_gemma.jsonl", "calls_qwen.jsonl", "verdicts.json"]
    assert fp["inputs"][0]["sha256"] == hashlib.sha256((ca.adir(aid) / "keyed.csv").read_bytes()).hexdigest()
    assert fp["inputs"][2]["sha256"] == hashlib.sha256(ca.SECOND_RUN.read_bytes()).hexdigest()
    top = hashlib.sha256(json.dumps({"content": fp["content_sha256"],
                                     "inputs": [[i["file"], i["sha256"]] for i in fp["inputs"]]},
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert top == fp["sha256"]
    csvt = client.get(f"/audit/{aid}/report.csv?strict=1").text
    html = client.get(f"/audit/{aid}/report?strict=1").text
    for i in fp["inputs"]:
        assert i["sha256"] in csvt and i["sha256"] in html
    assert fp["content_sha256"] in csvt and fp["content_sha256"] in html
    assert "calls_qwen.jsonl" not in client.get(f"/audit/{aid}/report.csv").text  # standard mode: one reader
    # a mark changes the content, so the fingerprint; so does a changed input file
    client.post(f"/api/audit/{aid}/mark", json={"key": "080310B0100__SOBRANTES", "mark": "confirmed"})
    assert _fp_html(client.get(f"/audit/{aid}/report").text) != std
    marked = _fp_html(client.get(f"/audit/{aid}/report?strict=1").text)
    _second(tmp_path, monkeypatch, _gemma_rows()[:101], "more.jsonl")
    after = _fp_html(client.get(f"/audit/{aid}/report?strict=1").text)
    assert after != marked
