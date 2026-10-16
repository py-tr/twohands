"""No test touches the real shared state (tests/conftest.py): the spend ledger, the rate limiter, the endpoint log,
app/state and live_audit point at tmp copies, and a write that slips through fails loudly."""
import json

import pytest

from twohands import REPO, amd, budgets, ratelimit


def test_state_paths_are_private():
    for p in (budgets.spend_file(), ratelimit.shared().path, amd.HEALTH):
        assert REPO not in p.resolve().parents, p
    from app import live, store
    assert REPO not in store.STATE.resolve().parents and REPO not in live.BUDGET_FILE.resolve().parents


def test_a_write_to_real_state_fails_loudly():
    with pytest.raises(PermissionError, match="test wrote to real state"):
        open(REPO / "cache" / "spend.jsonl", "a").close()


def test_test_rows_and_quarantined_rows_are_not_counted(tmp_path, monkeypatch):
    led = tmp_path / "spend.jsonl"
    monkeypatch.setenv("TWOHANDS_SPEND_FILE", str(led))
    real = {"day": budgets.budget_day(), "role": "bulk", "usd": 0.01, "ts": 1.0, "pid": 7}
    fake = {"day": budgets.budget_day(), "role": "bulk", "usd": 0.001, "ts": 2.0, "pid": 8}
    tagged = dict(fake, ts=3.0, test=True)
    led.write_text("".join(json.dumps(r) + "\n" for r in (real, fake, tagged)))
    budgets.quarantine_file(led).write_text(json.dumps({"note": "x"}) + "\n" + json.dumps(fake) + "\n")
    assert budgets.spent("bulk") == pytest.approx(0.01)           # tagged and quarantined rows are skipped
    budgets.record("bulk", 0.5)                                   # written from a test: tagged, so never counted
    assert json.loads(led.read_text().splitlines()[-1])["test"] is True and budgets.spent("bulk") == pytest.approx(0.01)
