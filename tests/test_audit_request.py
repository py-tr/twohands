"""Request an audit (/audit/request): the form, price and turnaround shown; a valid request stored with an id; the
operator emailed only when the SMTP settings are all present (a fake SMTP here: no real email is ever sent); the
SMTP settings never logged or stored; a honeypot and a per-IP limit against spam."""
import json
import logging
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import request as rq
from app.main import app
from tests.test_app_neutral import _clean

client = TestClient(app)
SECRET = "s3cret-pass-do-not-log"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(rq, "REQUESTS", tmp_path / "requests.jsonl")
    monkeypatch.setattr(rq, "_hits", {})
    monkeypatch.setattr(rq, "BACKGROUND", False)
    from app import capture_audit as ca
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    for k in (*rq.SMTP_VARS, "SMTP_PORT"):
        monkeypatch.delenv(k, raising=False)

    class Forbidden:
        def __init__(self, *a, **k):
            raise AssertionError("no real SMTP connection in tests")
    monkeypatch.setattr(rq.smtplib, "SMTP", Forbidden)
    monkeypatch.setattr(rq.smtplib, "SMTP_SSL", Forbidden)
    return tmp_path / "requests.jsonl"


def _form(**kw):
    f = {"org": "Instituto Estatal de Prueba", "email": "auditor@example.org", "forms": "2,500", "form_type": "tally",
         "where": "link", "link": "https://files.example.org/share/abc", "deadline": (date.today() + timedelta(days=7)).isoformat(),
         "notes": "Two districts.", "website": ""}
    f.update(kw)
    return f


def _stored(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []


def test_form_shows_fields_price_and_turnaround():
    r = client.get("/audit/request")
    assert r.status_code == 200
    h = r.text
    for name in ("org", "email", "forms", "form_type", "where", "link", "deadline", 'name="website"'):
        assert f'name="{name}"' in h or name in h
    assert "$1" in h and "per form audited" in h and "Report within 24 hours" in h
    _clean(h, "/audit/request")


def test_linked_from_report_and_overview():
    assert 'href="/audit/request"' in client.get("/").text
    aid = client.post("/api/audit/sample").json()["id"]
    assert 'href="/audit/request"' in client.get(f"/audit/{aid}/report").text


def test_valid_request_is_stored_with_id_and_no_email_without_smtp(isolated):
    r = client.post("/audit/request", data=_form())
    assert r.status_code == 200
    rows = _stored(isolated)
    assert len(rows) == 1
    rec = rows[0]
    assert rec["id"] in r.text and rq._RID.match(rec["id"])
    assert rec["forms"] == 2500 and rec["price_usd"] == 2500 and rec["status"] == "received"
    assert rec["link"].startswith("https://") and rec["form_type"] == "tally"
    assert "Request received" in r.text and "$2,500" in r.text and "notified by email" not in r.text
    assert rq.load(rec["id"]) == rec


def test_price_is_pro_rata_rounded_up():
    assert rq.price(1000) == 1000 and rq.price(2500) == 2500 and rq.price(1) == 1 and rq.price(1017) == 1017


def test_invalid_request_is_not_stored(isolated):
    r = client.post("/audit/request", data=_form(email="nope", forms="0", deadline="2001-01-01", where="link", link=""))
    assert r.status_code == 422
    assert "Enter an email" in r.text and "number of forms" in r.text and "in the past" in r.text and "Paste the link" in r.text
    assert _stored(isolated) == []
    # an upload request needs no link; a header-injection attempt in the organisation is flattened to one line
    r = client.post("/audit/request", data=_form(where="upload", link="", org="Org\r\nBcc: x@evil.test"))
    assert r.status_code == 200
    rec = _stored(isolated)[0]
    assert rec["link"] == "" and "\n" not in rec["org"] and "\r" not in rec["org"]


def test_honeypot_gets_a_confirmation_but_nothing_is_stored(isolated):
    r = client.post("/audit/request", data=_form(website="http://spam.example"))
    assert r.status_code == 200 and "Request received" in r.text
    assert _stored(isolated) == []


def test_per_ip_rate_limit(isolated):
    for _ in range(rq.RATE_N):
        assert client.post("/audit/request", data=_form()).status_code == 200
    r = client.post("/audit/request", data=_form())
    assert r.status_code == 429 and "Too many requests" in r.text
    assert len(_stored(isolated)) == rq.RATE_N
    # the window slides: an hour later the address may ask again
    assert rq.allow("10.0.0.9", now=0) and rq.allow("10.0.0.9", now=rq.RATE_WINDOW_S + 1)


def test_operator_emailed_only_when_smtp_configured(isolated, monkeypatch, caplog):
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            self.host, self.port = host, port

        def starttls(self, context=None):
            pass

        def login(self, user, pw):
            assert pw == SECRET
            self.user = user

        def send_message(self, m):
            sent.append(m)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(rq.smtplib, "SMTP", FakeSMTP)
    # three of the four settings: still no email
    monkeypatch.setenv("SMTP_HOST", "smtp.example.org")
    monkeypatch.setenv("SMTP_USER", "ops@example.org")
    monkeypatch.setenv("SMTP_PASS", SECRET)
    client.post("/audit/request", data=_form())
    assert sent == []
    monkeypatch.setenv("NOTIFY_TO", "operator@example.org")
    caplog.set_level(logging.DEBUG)
    r = client.post("/audit/request", data=_form(forms="1017"))
    assert r.status_code == 200 and "notified by email" in r.text
    assert len(sent) == 1
    m = sent[0]
    rec = _stored(isolated)[-1]
    assert m["To"] == "operator@example.org" and m["Reply-To"] == "auditor@example.org" and rec["id"] in m["Subject"]
    assert "1,017" in m.get_content() and "$1,017" in m.get_content()
    # the SMTP settings are never logged or stored
    assert SECRET not in caplog.text and "smtp.example.org" not in caplog.text
    assert SECRET not in isolated.read_text(encoding="utf-8")


def test_failed_send_keeps_the_request_and_logs_no_secret(isolated, monkeypatch, caplog):
    class Down:
        def __init__(self, *a, **k):
            raise OSError(f"connection refused to {SECRET}")
    monkeypatch.setattr(rq.smtplib, "SMTP", Down)
    for k, v in {"SMTP_HOST": "smtp.example.org", "SMTP_USER": "u", "SMTP_PASS": SECRET, "NOTIFY_TO": "o@example.org"}.items():
        monkeypatch.setenv(k, v)
    caplog.set_level(logging.DEBUG)
    assert client.post("/audit/request", data=_form()).status_code == 200
    assert len(_stored(isolated)) == 1
    assert "notification failed (OSError)" in caplog.text and SECRET not in caplog.text
