"""`make eval` recomputes every judge-facing number from the committed raw results and agrees with the app; and it
really fails when a displayed number drifts."""
import json

from twohands import eval as ev


def test_make_eval_recomputes_every_number_and_matches_the_app(tmp_path):
    out = tmp_path / "eval_report.md"
    assert ev.main(["--out", str(out), "--quiet"]) == 0, out.read_text(encoding="utf-8")
    t = out.read_text(encoding="utf-8")
    assert "0 mismatches" in t and "MISMATCH" not in t
    for row in ("| Capture errors found (model right) | 52 |", "| Model alone: 1 in N | 37 |",
                "| Gate-accepted: 1 in N | 605 |", "| Capture typed a wrong number: 1 in N | 374 |",
                "| Yield: 1 in N disputed is a capture error | 5 |", "| Capture error rate at least 1 in N | 122 |",
                "| confirms the paper | 22 |", "| Certified count covers | 31 |", "| Recall: C (model disputed) | 7 |",
                "| Recall: E2 | 7 |", "| Touchless forms (frozen gate) | 55 |", "| POST-HOC v2: accepted | 47 |",
                "| Amendment 2 tier qwen: accepted | 31 |", "| Amendment 2 tier qwen: errors | 1 |",
                "| Amendment 2 tier two_reader: accepted | 89 |", "| Amendment 2 tier two_reader: errors | 0 |",
                "| Amendment 2 tier two_reader: unadjudicated | 0 |", "| Two readers agree on all 23 digits | 147 |",
                "| POST-HOC v2-2R (Qwen confirms SOBRANTES): accepted | 54 |",
                "| POST-HOC v2-2R strict (only Qwen confirms SOBRANTES): errors | 0 |"):
        assert row in t, row


def test_make_eval_fails_on_a_drifted_number(tmp_path, monkeypatch):
    real = ev.jload

    def tampered(path):
        d = real(path)
        if path.name == "headline.json":
            d = json.loads(json.dumps(d))
            d["cert_agree"] += 1
        return d
    monkeypatch.setattr(ev, "jload", tampered)
    out = tmp_path / "eval_report.md"
    assert ev.main(["--out", str(out), "--quiet"]) == 1
    assert "confirms the paper: recomputed 22, app shows 23" in out.read_text(encoding="utf-8")


def test_make_eval_fails_when_a_two_reader_number_drifts(tmp_path, monkeypatch):
    real = ev.jload

    def tampered(path):
        d = real(path)
        if path.name == "two_reader_300.json":
            d = json.loads(json.dumps(d))
            d["tiers"]["two_reader"]["errors"] += 1
        return d
    monkeypatch.setattr(ev, "jload", tampered)
    out = tmp_path / "eval_report.md"
    assert ev.main(["--out", str(out), "--quiet"]) == 1
    t = out.read_text(encoding="utf-8")
    assert "Amendment 2 tier two_reader errors: recomputed 0, app shows 1" in t
