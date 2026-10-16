"""Inbox (operations view), export of captured records, API page, Overview hero data."""
import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

from app import hero as heromod
from app import inbox as inboxmod
from app import review as reviewmod
from app import store as storemod
from app.main import app
from tests.test_app_neutral import _clean

client = TestClient(app)


@pytest.fixture
def tmp_review(tmp_path, monkeypatch):
    f = tmp_path / "review.json"
    monkeypatch.setattr(reviewmod, "FILE", f)
    return f


def test_inbox_lists_every_form_with_one_status(tmp_review):
    s = storemod.get_store()
    rs = inboxmod.rows(s)
    assert {r["clave"] for r in rs} == {k for k in s.ine_claves() if s.default_read(k)}
    assert all(r["status"] in {x[0] for x in inboxmod.STATUSES} for r in rs)
    k = inboxmod.kpis(rs)
    assert sum(k[x[0]] for x in inboxmod.STATUSES) == k["n"] == len(rs)
    html = client.get("/inbox").text
    assert "Export CSV" in html and "Export JSON" in html and "Paper inconsistency" in html
    for r in rs[:20]:
        assert f'href="/form/{r["clave"]}"' in html
    _clean(html, "/inbox")


def test_inbox_statuses_known_forms(tmp_review):
    by = {r["clave"]: r for r in inboxmod.rows(storemod.get_store())}
    assert by["201720E0100"]["status"] == "accepted" and by["201720E0100"]["to_key"] == 0
    # every field read right, but the paper's TOTAL words and digits disagree: a paper inconsistency
    assert by["211294C0100"]["status"] == "paper"


def test_resolved_review_shows_in_inbox_and_export(tmp_review):
    j = client.post("/api/review/211294C0100", json={"values": {"TOTAL": "262"}})
    assert j.status_code == 200 and j.json()["status"] == "resolved"
    by = {r["clave"]: r for r in inboxmod.rows(storemod.get_store())}
    assert by["211294C0100"]["status"] == "resolved"
    rec = next(x for x in client.get("/api/export.json").json()["records"] if x["form_id"] == "211294C0100")
    assert rec["final"] is True and rec["values"]["TOTAL"] == 262
    j = client.post("/api/review/141097C0100", json={"action": "escalate", "note": "rows do not add up on paper"})
    assert {r["clave"]: r for r in inboxmod.rows(storemod.get_store())}["141097C0100"]["status"] == "escalated"


def test_export_csv_is_neutral_and_complete(tmp_review):
    r = client.get("/api/export.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    _clean(r.text, "export.csv")
    rows = list(csv.reader(io.StringIO(r.text)))
    head = rows[0]
    assert "Option 01" in head and "Option 15" in head and "Option 16" not in head and "TOTAL" in head
    assert len(rows) - 1 == len(inboxmod.rows(storemod.get_store()))
    acc = client.get("/api/export.csv?status=accepted").text
    body = list(csv.reader(io.StringIO(acc)))[1:]
    assert body and all(x[1] == "accepted" for x in body)


def test_export_json_is_neutral(tmp_review):
    r = client.get("/api/export.json")
    assert r.status_code == 200
    _clean(r.text, "export.json")
    j = r.json()
    assert j["fields"]["OPT01"] == "Option 01"
    rec = j["records"][0]
    assert set(rec["values"]) == set(j["fields"])
    assert all(k.startswith("OPT") or k in storemod.PLAIN_NAMES for k in rec["values"])


def test_api_page_and_openapi():
    html = client.get("/api").text
    assert 'href="/docs"' in html
    assert html.count("curl -s") >= 3 and "/api/gate" in html and "/api/jobs/" in html and "/api/export.csv" in html
    _clean(html, "/api")
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json")
    assert spec.status_code == 200
    _clean(spec.text, "openapi")


def test_hero_loop_is_a_real_read_with_one_red_field():
    d = heromod.loop_data(storemod.get_store())
    if d is None:
        pytest.skip("no masked hero page")
    assert len(d["fields"]) == len(storemod.schema()["fields"])
    bad = [f for f in d["fields"] if not f["ok"]]
    assert [f["code"] for f in bad] == ["TOTAL"]
    assert all(0 <= f["box"][0] and f["box"][0] + f["box"][2] <= 100.5 for f in d["fields"])
    assert not d["accepted"] and all(i["ok"] for i in d["identities"][:-1]) and d["identities"][-1]["ok"] is False
    html = client.get("/").text
    assert 'id="loopData"' not in html   # the replay hero was cut from Home (tests/test_cut.py); the data stays for scripts
    _clean(html, "/")


def test_no_raw_file_paths_in_judge_copy():
    """Source paths live in small 'source' tooltips (and on Results), not in the visible copy."""
    import re
    for url in ["/", "/inbox", "/try", "/api", "/form/211294C0100", "/forms"]:
        html = client.get(url).text
        visible = re.sub(r'<span class="tip">.*?</span>', "", html, flags=re.S)
        visible = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", visible, flags=re.S)
        visible = re.sub(r"<[^>]+>", " ", visible)
        for pat in ("spikes/", "results/", ".jsonl", "docs/NUMBERS", "data/masked", "spike v2"):
            assert pat not in visible, (url, pat)


def test_social_preview_and_favicon():
    html = client.get("/").text
    assert 'property="og:image"' in html and "static/og.jpg" in html
    assert client.get("/static/og.jpg").status_code == 200
    assert client.get("/favicon.ico").headers["content-type"] == "image/png"


def _row(kind, status, lat, mins_ago, now):
    import time as _t
    return {"ts": _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(now - 60 * mins_ago)), "kind": kind, "status": status,
            "latency_s": lat, "model": "Gemma-4-31B-IT"}


def test_amd_chip_ignores_batch_503s_and_uses_probes_only():
    import time as _t
    from app import health
    now = _t.time()
    batch_503s = [_row("read", 500, 30, 1, now) for _ in range(8)]
    # healthy probe, batch failing: still "AMD live"
    v = health.classify([_row("probe", 200, 4.2, 3, now)] + batch_503s, now)
    assert v["state"] == "up" and v["label"] == "AMD live"
    # last probe slow (> 60 s): amber
    v = health.classify([_row("probe", 200, 4, 9, now), _row("probe", 200, 75, 2, now)], now)
    assert v["state"] == "busy" and v["label"] == "AMD slow"
    # one failed probe is "slow", not "down"
    v = health.classify([_row("probe", 200, 4, 9, now), _row("probe", "TimeoutError", 300, 2, now)], now)
    assert v["label"] == "AMD slow"
    # last two probes failed: down
    v = health.classify([_row("probe", 200, 4, 12, now), _row("probe", 503, 3, 8, now), _row("probe", "TimeoutError", 300, 2, now)] + batch_503s, now)
    assert v["state"] == "down" and v["label"] == "AMD down, showing stored reads"
    # a successful live read counts like a probe
    assert health.classify([_row("probe", 503, 3, 8, now), _row("live", 200, 33, 1, now)], now)["label"] == "AMD live"
    # probes older than 15 min do not count; batch alone says nothing
    assert health.classify([_row("probe", 503, 3, 20, now), _row("probe", 503, 3, 18, now)] + batch_503s, now)["state"] == "quiet"


def test_inbox_kpis_lead_with_fields_and_agreement(tmp_review):
    s = storemod.get_store()
    rs = inboxmod.rows(s)
    k = inboxmod.kpis(rs)
    a = inboxmod.agreement(s, rs)
    assert k["fields_read"] > 0 and 0 < a["agree"] <= a["compared"]
    assert k["routed_fields"] >= k["routed_forms"] > 0
    html = client.get("/inbox").text
    strip = html[html.index('<div class="kpis">'):html.index('<div class="toolbar">')]
    order = [strip.index(x) for x in ("Forms in", "Fields read", "Agree with official capture", "Accepted at second capture",
                                     "Capture errors found", "Routed to review", "Paper inconsistencies", "AMD cost so far")]
    assert order == sorted(order)
    assert "fields to key" in html and "Waiting for a person" not in html
    # the measured rates come from the one computed summary (the same numbers as Overview and Results)
    from app.numbers import headline
    H = headline()
    assert f"{H['agree_pct']}%" in strip and f"{H['accepted']} of {H['forms']} forms" in strip
    assert f"{H['agree']:,} of {H['fields']:,} fields" in strip


def test_null_digits_are_worded_blank_or_faint():
    from app.store import Read, evaluate
    sch = storemod.schema()
    vals = {f["key"]: 1 for f in sch["fields"]}
    words = dict(vals)
    vals["SACADOS"], words["SACADOS"] = None, None
    vals["NULOS"], words["NULOS"] = None, 7
    ev = evaluate(Read("x", "t", vals, words, {}, [], False))
    msg = {f["code"]: f["msg"] for f in ev["fields"]}
    assert msg["SACADOS"] == "not read: blank or too faint on the page"
    assert msg["NULOS"].startswith("digit boxes not read (blank or faint); words say 7")
    assert "illegible" not in " ".join(ev["reasons"]) and not ev["accepted"]
