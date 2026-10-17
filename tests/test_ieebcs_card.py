"""The IEEBCS head-to-head placement (PROTOCOL_IEEBCS.md section 10) and the plumbing check helper (section 11)."""
import json
import re

import pytest
from fastapi.testclient import TestClient

from app import ieebcs_card as C
from app.main import app

client = TestClient(app)


def score(pct, matched=None, fields=10000):
    m = round(fields * pct / 100) if matched is None else matched
    return {"model": "gemma", "n_actas": 300,
            "theirs": {"fields": 23077, "matched": 14501, "pct": 62.84, "source": "IEEBCS, Informe final, p. 19"},
            "a_raw": {"matched": m, "fields": fields, "pct": pct, "wilson95": [pct - 1, pct + 1], "pages_read": 280,
                      "pages_located": 290,
                      "second_fields_of_located_pages": {"matched": m, "fields": fields - 400, "pct": round(100 * m / (fields - 400), 2)}}}


@pytest.fixture
def scorefile(tmp_path, monkeypatch):
    f = tmp_path / "score.json"
    monkeypatch.setattr(C, "RESULT", f)
    return f


def _text(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h))


def test_reads_the_file_the_scorer_writes():
    import importlib.util
    spec = importlib.util.spec_from_file_location("ieebcs_score", C.REPO / "scripts" / "ieebcs_score.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert C.RESULT == mod.RES / "score.json"
    P = C.placement()
    assert P == {"home_threshold": 0.90, "buyer_section_threshold": 0.80, "metric": "strict_per_field_match"}


def test_hidden_until_the_score_file_exists(scorefile):
    assert C.load() is None and all(C.card(s) is None for s in ("home", "buyer", "results"))
    assert 'id="buyer"' not in client.get("/").text and 'id="buyer-benchmark"' not in client.get("/").text
    assert 'id="ieebcs"' not in client.get("/results").text


@pytest.mark.parametrize("pct,home,buyer", [(93.0, True, True), (90.0, True, True), (85.5, False, True),
                                            (80.0, False, True), (79.99, False, False), (61.0, False, False)])
def test_three_variants_by_the_strict_figure(scorefile, pct, home, buyer):
    scorefile.write_text(json.dumps(score(pct)))
    assert (C.card("home") is not None) == home and (C.card("buyer") is not None) == buyer
    r = C.card("results")
    assert r is not None and r["ours_pct"] == pct                  # Results shows it in every case (section 8)
    assert (r["why"] is not None) == (not buyer)                   # below 80%: the reading of why
    h, res = client.get("/").text, client.get("/results").text
    assert ('id="buyer"' in h) == home and ('id="buyer-benchmark"' in h) == buyer and 'id="ieebcs"' in res
    for c in filter(None, (C.card("home"), C.card("buyer"), r)):
        assert c["footnote"] == C.FOOTNOTE
    assert C.FOOTNOTE in _text(res).replace("&#39;", "'").replace("&quot;", '"')
    if home:
        t = _text(h).replace("&#39;", "'")
        assert f"{pct}% of all fields" in t and "62.84%" in t and C.FOOTNOTE in t
        assert h.index('id="rcard"') < h.index('id="strip"') < h.index('class="f-actions"') < h.index('id="buyer"')


def test_reading_of_why_adds_up(scorefile):
    d = score(70.0, matched=7000)
    scorefile.write_text(json.dumps(d))
    why = C.card("results")["why"]
    assert "3,000 unmatched fields" in why and "400 are on the 10 of 300 pages" in why and "2,600 on the 290" in why
    assert "10 of which were not read or not parsed" in why and "PROTOCOL_IEEBCS.md section 10" in why


def test_strict_figure_is_the_headline(scorefile):
    d = score(88.0)
    d["a_raw"]["second_fields_of_located_pages"]["pct"] = 95.0       # the located-page share must not place it
    scorefile.write_text(json.dumps(d))
    assert C.card("home") is None and C.card("buyer")["tier"] == "buyer"
    assert C.card("buyer")["text"].index("88.0%") < C.card("buyer")["text"].index("95.0%")


def test_plumbing_check_lists_the_first_five_located_actas(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("ieebcs_plumbing", C.REPO / "scripts" / "ieebcs_plumbing.py")
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    if not (P.RES / "official.json").is_file():
        pytest.skip("no official.json")
    items = P.first_located(5)
    man = json.loads(P.MAN.read_text(encoding="utf-8"))["items"]
    order = [it["clave"] for it in man]
    assert len(items) == 5 and [order.index(i["clave"]) for i in items] == sorted(order.index(i["clave"]) for i in items)
    text, rows = P.build("no_such_model", 5)
    assert text.count("\n## ") == 5 and "no read yet" in text and rows
    from twohands import schema
    for it in items:   # no party name in the human-readable file: vote rows by public code (Option NN) only
        s = schema.load(it["schema"])
        for f in s["fields"]:
            if f["key"] in (s.get("vote_keys") or []) and f["public"]["code"] != f["key"]:
                assert f["key"] not in text and (f.get("csv") or "-") not in text
