"""The blind check of 200 agreeing fields (/check?set=agree200) and the wording it gates."""
import json

from app import numbers, spotcheck


def test_agree200_queue_is_the_seeded_draw_and_blind():
    q = spotcheck.queue("agree200")
    v = spotcheck.load_verdicts("agree200")
    assert len(q) == 200 == len(set(q)) and set(q) == set(v)
    assert all(x["verdict"] == "agree" for x in v.values())


def test_wording_switches_only_when_all_200_are_answered(tmp_path, monkeypatch):
    f = tmp_path / "spotcheck_agree200.json"
    monkeypatch.setattr(spotcheck, "FILE_A200", f)
    v = spotcheck.load_verdicts("agree200")
    assert "were not individually checked" in numbers.checked_line()
    keys = sorted(v)
    ans = {k: {"digits": v[k]["paper"]} for k in keys[:199]}
    f.write_text(json.dumps(ans))
    assert "were not individually checked" in numbers.checked_line()
    ans[keys[199]] = {"digits": -1}          # one read differently
    f.write_text(json.dumps(ans))
    assert numbers.checked_line().endswith("a random 200 agreeing fields were checked by a person: 199 agreed")
