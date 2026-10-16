"""The person check of the 100-form confirmation's disagreements (/check?set=confirm100) and the wording it drives."""
import json
import sys

import pytest
from fastapi.testclient import TestClient

from app import confirm100 as c100
from app import spotcheck
from twohands import REPO

V = json.loads((REPO / "results" / "adjudication_confirm100" / "verdicts.json").read_text(encoding="utf-8"))


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def _agreeing() -> dict:
    return {k: {"digits": v["paper"], "words": None, "blank": False, "cant_tell": False, "differ": False}
            for k, v in V.items()}


def test_queue_is_exactly_the_disagreements():
    q = spotcheck.queue("confirm100")
    assert sorted(q) == sorted(V) and len(q) == 3
    assert not set(q) & set(spotcheck.queue())          # the main queue is untouched


def test_answers_stored_apart(client, tmp_path):
    main_before = spotcheck.load()
    r = client.post("/api/check/0?set=confirm100", json={"digits": "5"})
    assert r.status_code == 200 and r.json()["n"] == 3
    assert spotcheck.FILE_C100.is_file()
    assert spotcheck.queue("confirm100")[0] in spotcheck.load("confirm100")
    assert spotcheck.load() == main_before


def test_page_is_blind_and_keeps_the_set(client):
    h = client.get("/check?set=confirm100").text
    assert "/api/check/" in h and "set=confirm100" in h
    for v in V.values():                                 # no AI evidence or paper value on the page
        assert v["evidence"] not in h
    assert client.get("/check/img/0.jpg?set=confirm100").status_code == 200
    assert client.get("/check?set=nope").status_code == 404


def test_wording_switches_on_stored_answers():
    pending = c100.texts(answers={})
    assert "adjudicated from crops by the AI adjudicator (person check pending)" in pending["para"]
    assert not pending["person"]["checked"]
    one = dict(list(_agreeing().items())[:1])
    assert "checked by a person" not in c100.texts(answers=one)["para"]
    done = c100.texts(answers=_agreeing())
    assert "3 disagreements adjudicated from crops and checked by a person." in done["para"]
    assert "pending" not in done["para"]
    wrong = _agreeing()
    k = next(iter(wrong))
    wrong[k] = {**wrong[k], "digits": 999}
    assert "checked by a person" not in c100.texts(answers=wrong)["para"]


def test_numbers_from_data():
    t = c100.texts(answers={})
    assert "The fixed gate (v2) accepted 22 forms; 0 of their 484 fields were wrong" in t["para"]
    assert "(Wilson upper bound 0.79%)" in t["para"]
    assert "1 wrong field in 1,518 accepted, of which 1,034 are a post-hoc re-score of the 300 and 484" in t["para"]
    assert "the model read 3114 where the paper says 314, a digit inserted" in t["held"]
    assert t["v3_line"].startswith("v3 on the 100: 0 wrong of 504 accepted;")
    assert [m["text"] for m in t["modes"]][-1] == "digit insertion (3114 for 314)"
    assert t["chip"] == "fix confirmed on 100 fresh forms: 0 wrong of 484"


def test_the_named_v2_rule_is_what_blocked_3114():
    sys.path.insert(0, str(REPO / "scripts"))
    from confirm100_score import last, parsed_of
    from twohands import schema
    from twohands.gate_v2 import gate_v2
    s = schema.load()
    r = last(REPO / "results" / "calls_confirm100_gemma.jsonl")["070212B0100"]
    g = gate_v2(parsed_of(r, [f["key"] for f in s["fields"]]), s)
    assert g.v1.accepted and not g.accepted
    assert g.codes == ["unchecked"] and g.unchecked == {"SOBRANTES": "fail"}
    assert r["fields"]["SOBRANTES"]["n"] == 3114 and r["fields"]["SOBRANTES"]["w"] is None
    assert '"a field in no identity needs its digits and words both read and equal"' in c100.V2_RULE
    assert 'blocked it' in c100.texts(answers={})["held"] and c100.V2_RULE in c100.texts(answers={})["held"]


def test_pages_show_it(client):
    h = client.get("/results").text
    assert 'id="confirm100"' in h and "tier-c100-v3" in h and "tier-v2-pooled" in h and "post-hoc" in h
    assert "digit insertion (3114 for 314)" in h
    home = client.get("/").text
    assert "fix confirmed on 100 fresh forms: 0 wrong of 484" in home
    assert "1,518" not in home                           # the pooled figure is never a headline
