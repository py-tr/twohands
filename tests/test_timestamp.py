"""OpenTimestamps anchoring of report roots: the .ots format, the calendar client (mocked), the web report's line and
proof route, the CLI's --timestamp, and the committed proof of the sample audit's root. No network."""
import hashlib
import os
from pathlib import Path

import pytest

from twohands import timestamp as ots

REPO = Path(__file__).resolve().parent.parent
SAMPLE = REPO / "results" / "sample_audit_root.txt"


def fake_calendar(calls=None, fail=()):
    """A calendar answer as the real ones give it: append a nonce, sha256, then a pending attestation (its URI)."""
    def post(cal, digest):
        if calls is not None:
            calls.append((cal, digest))
        if cal in fail:
            raise OSError("connection refused")
        uri = cal.replace("pool", "calendar").encode()
        return (bytes([ots.OP_APPEND]) + ots._varbytes(os.urandom(8)) + bytes([ots.OP_SHA256])
                + b"\x00" + ots.TAG_PENDING + ots._varbytes(ots._varbytes(uri)))
    return post


def test_stamp_sends_only_a_salted_hash_and_parses_back():
    calls = []
    data = b"e56a8ef4f011b9e5a3b7bd91dd708580fe1a8912e3bd65f51d780a6dd5898721\n"
    nonce = b"\x07" * 16
    proof, ok = ots.stamp_bytes(data, post=fake_calendar(calls), nonce=nonce)
    assert ok == list(ots.CALENDARS)
    sent = {d for _, d in calls}
    assert sent == {hashlib.sha256(hashlib.sha256(data).digest() + nonce).digest()}   # not the file's own hash
    i = ots.info(proof)
    assert i["file_sha256"] == hashlib.sha256(data).hexdigest()
    assert len(i["pending"]) == len(ots.CALENDARS) and i["bitcoin"] == []


def test_one_calendar_down_is_enough_all_down_raises():
    proof, ok = ots.stamp_bytes(b"x", post=fake_calendar(fail=ots.CALENDARS[:3]))
    assert ok == [ots.CALENDARS[3]] and len(ots.info(proof)["pending"]) == 1
    with pytest.raises(OSError):
        ots.stamp_bytes(b"x", post=fake_calendar(fail=ots.CALENDARS))
    with pytest.raises(OSError):   # an answer that is not a timestamp counts as a failure
        ots.stamp_bytes(b"x", post=lambda c, d: b"<html>bad gateway</html>")


def test_bitcoin_attestation_is_read():
    ans = bytes([ots.OP_SHA256]) + b"\x00" + ots.TAG_BITCOIN + ots._varbytes(ots._varuint(918_000))
    proof, _ = ots.stamp_bytes(b"y", calendars=("https://c",), post=lambda c, d: ans)
    assert ots.info(proof)["bitcoin"] == [918_000]


def test_reference_client_reads_our_file():
    core = pytest.importorskip("opentimestamps.core.timestamp")
    ser = pytest.importorskip("opentimestamps.core.serialize")
    proof, _ = ots.stamp_bytes(b"z", post=fake_calendar())
    d = core.DetachedTimestampFile.deserialize(ser.BytesDeserializationContext(proof))
    assert d.file_digest == hashlib.sha256(b"z").digest()
    assert len(list(d.timestamp.all_attestations())) == len(ots.CALENDARS)


def test_stamp_file_and_status(tmp_path):
    f = tmp_path / "merkle_root.txt"
    f.write_bytes(b"ab" * 32 + b"\n")
    meta = ots.stamp_file(f, post=fake_calendar())
    st = ots.status(f)
    assert st["matches"] and st["date"] == meta["submitted"][:10] and len(st["pending"]) == 4
    f.write_bytes(b"cd" * 32 + b"\n")            # the file changed: the proof no longer matches it
    assert ots.status(f)["matches"] is False
    assert ots.status(tmp_path / "none.txt") is None


def test_committed_sample_proof_matches_the_published_root():
    st = ots.status(SAMPLE)
    assert st is not None and st["matches"], "results/sample_audit_root.txt.ots must commit to the committed file"
    assert st["pending"] or st["bitcoin"]


def _app(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app import capture_audit as ca
    from app.main import app
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    monkeypatch.setattr(ca, "TIMESTAMPS", tmp_path / "timestamps")
    monkeypatch.setattr(ca, "_STAMPING", {})
    return ca, TestClient(app)


def test_report_shows_the_sample_anchor_and_serves_the_proof(tmp_path, monkeypatch):
    ca, c = _app(tmp_path, monkeypatch)
    root = SAMPLE.read_text(encoding="utf-8").split()[0]
    a = ca.sample()
    monkeypatch.setattr(ca, "fingerprint", lambda *x, **k: {"sha256": "0" * 64, "content_sha256": "0" * 64,
                                                            "inputs": [], "merkle_root": root, "merkle_n": 1})
    page = c.get(f"/audit/{a['id']}/report").text
    assert "Anchored in time: 20" in page and "OpenTimestamps calendars" in page and f"/timestamp/{root}.ots" in page
    r = c.get(f"/timestamp/{root}.ots")
    assert r.status_code == 200 and r.content == (SAMPLE.parent / (SAMPLE.name + ".ots")).read_bytes()
    assert c.get(f"/timestamp/{root}.txt").content == SAMPLE.read_bytes()
    assert c.get("/timestamp/" + "f" * 64 + ".ots").status_code == 404
    assert c.get("/timestamp/../../etc.ots").status_code == 404


def test_new_report_root_is_stamped_once(tmp_path, monkeypatch):
    ca, c = _app(tmp_path, monkeypatch)
    root = "ab" * 32
    assert ca.ensure_stamped(root) == "off"          # tests run with TWOHANDS_OTS=0
    monkeypatch.setenv("TWOHANDS_OTS", "1")
    calls = []
    assert ca.ensure_stamped(root, post=fake_calendar(calls), background=False) == "stamped"
    assert (tmp_path / "timestamps" / f"{root}.txt").read_bytes() == (root + "\n").encode()
    assert ca.timestamp_of(root)["proof"] == f"/timestamp/{root}.ots"
    assert ca.ensure_stamped(root, post=fake_calendar(calls), background=False) == "stamped"
    assert len(calls) == len(ots.CALENDARS)          # one submission per calendar, not per render
    assert c.get(f"/timestamp/{root}.ots").status_code == 200


def test_failed_stamp_is_not_retried_at_once(tmp_path, monkeypatch):
    ca, _ = _app(tmp_path, monkeypatch)
    monkeypatch.setenv("TWOHANDS_OTS", "1")
    root = "cd" * 32
    down = fake_calendar(fail=ots.CALENDARS)
    assert ca.ensure_stamped(root, post=down, background=False) == "pending"
    assert ca.timestamp_of(root) is None
    assert ca.ensure_stamped(root, post=down, background=False) == "pending"   # inside the retry window
    assert ca.ensure_stamped("not-a-root") == "invalid"


def test_cli_timestamp_flag(tmp_path, monkeypatch):
    from twohands import cli
    keyed = REPO / "app" / "data" / "audit_sample_prep300.csv"
    S = cli.audit(keyed, out=tmp_path / "out", from_stored=True, state=tmp_path / "state", html=False,
                  stamp=True, stamp_post=fake_calendar(), log=lambda *x: None)
    st = ots.status(tmp_path / "out" / "merkle_root.txt")
    assert st["matches"] and S["timestamp"]["proof"] == "merkle_root.txt.ots"
    assert (tmp_path / "out" / "merkle_root.txt").read_text().strip() == S["merkle_root"]
