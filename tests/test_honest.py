"""What a skeptical reader would ask, answered on the page: the 52's confirmation breakdown, Judge this verdict
yourself, the tiers in the regulation's words, the honest model line, the live counter and the buyer-card slot."""
import html as htmlmod
import json
import re

import pytest
from fastapi.testclient import TestClient

from app import honest, judge
from app import live_status as LS
from app import numbers as numbersmod
from app import spotcheck
from app.main import app
from twohands import worker as W

client = TestClient(app)
H = numbersmod.headline()


def _text(h):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))).strip()


@pytest.fixture
def votes(tmp_path, monkeypatch):
    monkeypatch.setattr(judge, "FILE", tmp_path / "public_verdicts.jsonl")
    monkeypatch.setattr(judge, "_seen", set())
    monkeypatch.setattr(judge, "_recent", judge.defaultdict(judge.deque))
    monkeypatch.setattr(judge, "_cache", {"mt": None, "c": {}})
    return tmp_path / "public_verdicts.jsonl"


@pytest.fixture
def no_spotcheck(tmp_path, monkeypatch):
    monkeypatch.setattr(spotcheck, "FILE", tmp_path / "spotcheck.json")


# ------------------------------------------------------------------------------------------------ (b) the 52
def test_confirmation_breakdown_is_computed_and_pending_without_a_person(no_spotcheck):
    c = honest.confirmation(H)
    n_cert = sum(1 for x in H["keying_list"] if x["cert_agrees"])
    assert (c["total"], c["certified"], c["person"], c["ai_only"]) == (H["keying_errors"], n_cert, 0, H["keying_errors"] - n_cert)
    assert c["certified"] == H["cert_agree"] and c["state"] == "pending"
    line = (f"{H['cert_agree']} confirmed by the certified count · {H['keying_errors'] - H['cert_agree']} judged from "
            f"the photo by the AI adjudicator (person check in progress at /check)")
    assert c["text"] == line and "0 checked" not in c["readme"]
    for u in ("/", "/audit"):
        t = _text(client.get(u).text)
        assert line in t, u


def test_confirmation_counts_a_persons_blind_reading(tmp_path, monkeypatch):
    rest = [x for x in H["keying_list"] if not x["cert_agrees"]]
    V = spotcheck.load_verdicts()
    a, b = rest[0], rest[1]
    ans = {f"{a['clave']}__{a['field']}": {"digits": V[f"{a['clave']}__{a['field']}"]["paper"]
                                           if isinstance(V[f"{a['clave']}__{a['field']}"]["paper"], int) else None,
                                           "blank": V[f"{a['clave']}__{a['field']}"]["paper"] == "blank"},
           f"{b['clave']}__{b['field']}": {"digits": 99999}}
    c = honest.confirmation(H, answers=ans)
    assert (c["person"], c["person_disagree"], c["ai_only"]) == (1, 1, len(rest) - 2)
    assert c["state"] == "in_progress" and f"(checked by a person: 2 of {len(rest)}, 1 agree, 1 read differently)" in c["text"]
    c2 = honest.confirmation(H, answers={**ans, f"{b['clave']}__{b['field']}": {"digits": None, "cant_tell": True}})
    assert f"(checked by a person: 2 of {len(rest)}, 1 agree, 1 unreadable to the person)" in c2["text"]
    assert "judged from the photo by the AI adjudicator" in c["text"]   # the label stays for the fields not yet checked


# ------------------------------------------------------------------------------------------------ judge this verdict
def test_judge_flow_blind_then_reveal_then_counts(votes):
    x = next(x for x in H["keying_list"] if x["cert_agrees"] and isinstance(x["paper"], int))
    code = numbersmod.storemod.code_of(x["field"])
    url = f"/judge/{x['clave']}/{code}"
    h = client.get(url).text
    t = _text(h)
    # blind: the crop and the field name, none of the values
    assert "/crop/" in h and "What does the paper say?" in t
    body = t.split("What does the paper say?")[1]
    # the Spanish number-word helper is the same on every judge page (it reveals nothing about this field)
    assert "Spanish number words, in English" in body
    body = re.sub(r"Spanish number words, in English.*?Your answer", "", body, flags=re.S)
    for v in (str(x["paper"]), str(x["prep"])):
        assert not re.search(rf"(?<!\d){re.escape(v)}(?!\d)", body.replace(x["clave"], "")), v
    # reveal
    r = client.post(f"/api/judge/{x['clave']}/{code}", json={"digits": str(x["paper"])}).json()
    assert (r["agree"], r["paper"], r["capture"], r["certified"], r["verdict"]) == (True, x["paper"], x["prep"], x["certified"], "model_right")
    assert r["recorded"] == "recorded" and r["count_text"] is None
    # the same visitor twice is not counted twice
    assert client.post(f"/api/judge/{x['clave']}/{code}", json={"digits": "1"}).json()["recorded"] == "already"
    lines = [json.loads(s) for s in votes.read_text(encoding="utf-8").splitlines()]
    assert lines == [{"ts": lines[0]["ts"], "item": f"{x['clave']}__{code}", "agree": True}]   # anonymous
    # counts show from 3 visitors, on the reveal and on Findings
    judge.record("v2", f"{x['clave']}__{code}", True)
    judge.record("v3", f"{x['clave']}__{code}", False)
    assert judge.count_text(f"{x['clave']}__{code}") == "3 visitors checked this verdict, 2 agreed"
    assert "3 visitors checked this verdict, 2 agreed" in _text(client.get("/audit").text)


def test_every_findings_dispute_has_the_button(votes):
    h = client.get("/audit").text
    n_img = sum(1 for x in H["keying_list"] if numbersmod.storemod.get_store().masked_image(x["clave"]))
    assert h.count(">Judge this verdict yourself</a>") == n_img > 0


def test_judge_rate_limit_and_unknown(votes):
    for i in range(judge.PER_HOUR):
        assert judge.record("same", f"item{i}", True, now=1000.0 + i) == "recorded"
    assert judge.record("same", "one-more", True, now=1000.0 + judge.PER_HOUR) == "limited"
    assert judge.record("same", "later", True, now=1000.0 + 3700 + judge.PER_HOUR) == "recorded"
    assert client.get("/judge/000000X0000/TOTAL").status_code == 404
    assert client.get("/judge/202451B0100/NOPE").status_code == 404


# ------------------------------------------------------------------------------------------------ (a) tiers
def test_tiers_in_the_regulations_words():
    t = _text(client.get("/").text)
    assert "accepted at second capture" in t
    for bad in ("no person", "touchless"):
        assert bad not in t.lower()
    assert "no person" not in _text(client.get("/inbox").text).lower()
    assert "no person" not in honest.gate_label(numbersmod.lines(H))
    first = re.search(r'<section class="first".*?</section>', client.get("/").text, flags=re.S).group(0)
    assert honest.REG_LINE in _text(first)
    assert f"1 disputed field in {H['yield_one_in']} is a confirmed capture error ({H['keying_errors']} of {H['disagree']})" in t


def test_no_touchless_in_any_title():
    x = H["keying_list"][0]
    for u in ("/", "/audit", "/inbox", "/results", f"/judge/{x['clave']}/{numbersmod.storemod.code_of(x['field'])}"):
        h = client.get(u).text
        title = re.search(r"<title>(.*?)</title>", h, flags=re.S).group(1)
        heads = " ".join(re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", h, flags=re.S))
        assert "touchless" not in (title + heads).lower() and "no person" not in (title + heads).lower(), u


# ------------------------------------------------------------------------------------------------ (c) model line
def _windows_from_log(model, path):
    """Independent recomputation: each span from a 400 on a probe / live read to the next 200 (any kind)."""
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("model") == model and r.get("ts"):
            rows.append(r)
    out, start = [], None
    for r in sorted(rows, key=lambda r: r["ts"]):
        if start is None and r.get("status") == 400 and r.get("kind") in ("probe", "live"):
            start = r["ts"]
        elif start is not None and r.get("status") == 200:
            out.append((start, r["ts"]))
            start = None
    return out + ([(start, None)] if start else [])


def test_outage_window_is_computed_from_the_endpoint_log(tmp_path):
    from twohands import amd
    ws = honest.outage_windows("Gemma-4-31B-IT", amd.HEALTH)
    assert [(w["start"], w["end"]) for w in ws] == _windows_from_log("Gemma-4-31B-IT", amd.HEALTH)
    # the withdrawal of 2026-10-15 is in the committed log, whatever windows the log gains after it
    assert ("2026-10-15T15:41:09Z", "2026-10-16T02:06:46Z") in [(w["start"], w["end"]) for w in ws]
    w0 = next(w for w in ws if w["start"] == "2026-10-15T15:41:09Z")
    assert w0["start_text"] == "2026-10-15 15:41 UTC" and w0["end_text"] == "2026-10-16 02:06 UTC"
    assert honest.outage_text().startswith("Gemma-4-31B-IT unavailable on the AMD Token Factory from 2026-10-15 15:41 UTC "
                                           "(first HTTP 400) to 2026-10-16 02:06 UTC (first 200 again)")
    for w in ws:
        assert w["start_text"] in honest.outage_text()
    log = tmp_path / "h.jsonl"     # a 400 on a batch read is one bad request, not an outage; an open window says so
    rows = [{"ts": "2026-10-17T01:00:00Z", "model": "M", "status": 400, "kind": "read"},
            {"ts": "2026-10-17T02:00:00Z", "model": "M", "status": 400, "kind": "probe"},
            {"ts": "2026-10-17T02:30:00Z", "model": "M", "status": "withdrawn", "kind": "models"}]
    log.write_text("".join(json.dumps(r) + chr(10) for r in rows))
    w = honest.outage_windows("M", log)
    assert len(w) == 1 and w[0]["start"] == "2026-10-17T02:00:00Z" and w[0]["end"] is None
    assert "since 2026-10-17 02:00 UTC" in honest.outage_text("M", log)


def test_reader_now_names_the_current_model_on_amd():
    assert honest.reader_now() == "reader now: Gemma-4-31B-IT on AMD Token Factory"   # conftest: Gemma is listed
    h = client.get("/").text
    assert "reader now: Gemma-4-31B-IT on AMD Token Factory" in _text(h[h.index('id="amd"'):h.index('id="any-form"')])


def test_model_line_names_an_open_outage_and_omits_the_bench_until_it_ran(tmp_path, monkeypatch):
    monkeypatch.setattr(honest, "RESULTS", tmp_path)
    s = honest.model_line()
    ws = honest.outage_windows("Gemma-4-31B-IT")
    opened = [w for w in ws if not w["end"]]
    w = opened[-1] if opened else max(ws, key=lambda w: (w["hours"], w["start"]))   # still out, else the longest
    if w["end"]:
        assert s == ("Measured on Gemma-4-31B-IT on the AMD Token Factory. Live reads use Gemma when it is listed, and "
                     "fall back to Qwen3.8-27B otherwise; every receipt names its reader.")   # a closed window: not narrated
    else:
        assert f"is unavailable on the AMD Token Factory since {w['start_text']}" in s
    assert "MI300X" not in s
    (tmp_path / "bench_mi300x_20261016T000000Z.json").write_text(json.dumps({"meta": {"model": "gemma"}, "levels": [{"ok": 0}]}))
    assert "MI300X" not in honest.model_line()          # a run with no answered request is not a bench
    (tmp_path / "bench_mi300x_20261017T000000Z.json").write_text(
        json.dumps({"meta": {"model": "google/gemma-4-31b-it"}, "levels": [{"ok": 4}]}))
    assert honest.model_line().endswith("; benchmarked on self-hosted Gemma on an AMD Instinct MI300X.")


def test_readme_first_screen_matches_the_computed_lines(no_spotcheck):
    readme = re.sub(r"\s+", " ", (honest.REPO / "README.md").read_text(encoding="utf-8"))
    first = readme[:readme.index("## Contents")]
    # the first screen is the proof bullets and the business table; the computed lines follow under ## Contents
    assert honest.model_line() in readme                      # the real results dir: with or without the bench clause
    if not honest.bench_ran():
        assert "MI300X" not in readme
    assert honest.REG_LINE in readme
    assert honest.confirmation_in_doc(readme, H)          # the 52's AI-adjudicated part and its person check
    assert "no person" not in first and "touchless" not in first.lower()


def test_model_line_in_the_amd_box():
    h = client.get("/").text
    box = h[h.index('id="amd"'):h.index('id="any-form"')]
    assert honest.model_line() in _text(box)


# ------------------------------------------------------------------------------------------------ (d) the counter
FAKE = {"audited": 41, "disputes": 9, "confirmed": 3, "updated": "2026-10-16T00:00:00Z", "reader_now": "Qwen3.8-27B",
        "states": [{"name": "Colima", "complete": True, "pct": 100.0, "done": 982, "queue": 982},
                   {"name": "Baja California Sur", "complete": False, "pct": 12.5, "done": 100, "queue": 800}],
        "queue_states": 32, "queue_total": 153358, "status": {"kind": "live", "text": "Running"}, "recent": []}


def test_counter_never_shows_a_national_fraction_or_the_queue(monkeypatch):
    monkeypatch.setattr(LS, "_summary", lambda: FAKE)
    from app import live_audit
    monkeypatch.setattr(live_audit, "summary", lambda: FAKE)
    rows = [{"status": "audited", "cost_usd": 0.0005, "latency_s": 100.0}] * 4
    monkeypatch.setattr(honest, "_worker_rows", lambda: rows)
    h = client.get("/").text
    strip = re.search(r'<div class="strip card".*?</p>\s*</div>', h, flags=re.S).group(0)
    t = _text(strip)
    n = min(int(W.DAILY_USD / 0.0005), int(W.CONCURRENCY * 86400 / 100.0))
    for s in ("1 states complete", "12.5 % of Baja California Sur so far", f"+{n:,} a day for ${W.DAILY_USD:.2f} on AMD",
              f"{H['forms'] + 41} audited in total"):
        assert s in t, s
    first = _text(re.search(r'<section class="first".*?</section>', h, flags=re.S).group(0))
    for bad in ("of 32", "153,358", "153358", "169,005", "% of the country", "% of Mexico", "nationwide"):
        assert bad not in first, bad
    assert not re.search(r"\b\d+ of \d+ states\b", first)
    # order: the receipt card, then (the buyer slot), then the strip
    assert h.index('id="rcard"') < h.index('id="strip"')


def test_buyer_slot_hidden_until_result_clears_the_threshold(tmp_path, monkeypatch):
    P = honest.placement()
    assert P and P["home_threshold"] == 0.90   # PROTOCOL_IEEBCS.md's ```placement block
    from app import ieebcs_card
    assert ieebcs_card.RESULT == honest.REPO / "results" / "ieebcs" / "score.json"   # the file ieebcs_score.py writes
    f = tmp_path / "score.json"
    monkeypatch.setattr(ieebcs_card, "RESULT", f)
    assert honest.buyer_card() is None and 'id="buyer"' not in client.get("/").text
    res = {"model": "gemma", "n_actas": 300, "theirs": {"fields": 23077, "matched": 14501, "pct": 62.84, "source": "p. 19"},
           "a_raw": {"matched": 8000, "fields": 10000, "pct": 80.0, "wilson95": [79.2, 80.8], "pages_located": 290,
                     "pages_read": 288, "second_fields_of_located_pages": {"matched": 8000, "fields": 9700, "pct": 82.47}}}
    f.write_text(json.dumps(res))
    assert honest.buyer_card() is None and 'id="buyer"' not in client.get("/").text   # below 90%: not on Home
    res["a_raw"].update(matched=9300, pct=93.0)
    f.write_text(json.dumps(res))
    b = honest.buyer_card()
    assert b and b["ours_pct"] == 93.0
    h = client.get("/").text
    assert h.index('id="rcard"') < h.index('id="strip"') < h.index('class="f-actions"') < h.index('id="buyer"')


def test_judge_from_an_audit_report(votes, tmp_path, monkeypatch):
    from app import capture_audit as ca
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    aid = client.post("/api/audit/sample").json()["id"]
    rep = client.get(f"/audit/{aid}/report").text
    links = re.findall(r'href="(/judge/[^"]+\?a=' + aid + ')"', rep)
    assert links and len(links) == rep.count(">Judge this verdict yourself</a>")
    # a dispute the sample shares with the adjudicated 267: same item, same verdict as on Findings
    x = next(x for x in H["keying_list"] if x["cert_agrees"] and isinstance(x["paper"], int))
    code = numbersmod.storemod.code_of(x["field"])
    u = f"/judge/{x['clave']}/{code}?a={aid}"
    assert client.get(u).status_code == 200
    r = client.post(f"/api/judge/{x['clave']}/{code}?a={aid}", json={"digits": "0"}).json()
    assert (r["agree"], r["paper"], r["verdict"], r["adjudicated"]) == (False, x["paper"], "model_right", True)
    assert json.loads(votes.read_text(encoding="utf-8").splitlines()[0])["item"] == f"{x['clave']}__{code}"
    assert client.get(f"/judge/{x['clave']}/{code}?a=a0123456789ab").status_code == 404
