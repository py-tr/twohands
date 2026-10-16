"""Cross-process limiter: two limiters on one state file share the pace."""
import time

from twohands.ratelimit import FileRateLimiter


def test_two_limiters_share_one_pace(tmp_path):
    f = tmp_path / "rl.json"
    a, b = FileRateLimiter(f, rpm=600), FileRateLimiter(f, rpm=600)  # 0.1 s apart
    t0 = time.time()
    for lim in (a, b, a, b):
        lim.acquire()
    assert time.time() - t0 >= 0.28


def test_pause_is_shared(tmp_path):
    f = tmp_path / "rl.json"
    a, b = FileRateLimiter(f, rpm=6000), FileRateLimiter(f, rpm=6000)
    a.pause(0.3, jitter=0)
    t0 = time.time()
    b.acquire()
    assert time.time() - t0 >= 0.25


def test_live_lane_is_reserved(tmp_path):
    """Total 600/min with 300 reserved for live: bulk starts are 0.2 s apart; a live start does not wait for them."""
    f = tmp_path / "rl.json"
    bulk, live = FileRateLimiter(f, rpm=600, live_rpm=300), FileRateLimiter(f, rpm=600, live_rpm=300)
    t0 = time.time()
    bulk.acquire()
    bulk.acquire()
    assert time.time() - t0 >= 0.18           # the bulk lane is 300/min
    t1 = time.time()
    live.acquire(live=True)
    assert time.time() - t1 < 0.1             # the live lane was free


def test_role_shares_and_spend_ledger(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from twohands import budgets
    monkeypatch.setenv("TWOHANDS_SPEND_FILE", str(tmp_path / "spend.jsonl"))
    assert budgets.share("worker") + budgets.share("bulk") + budgets.share("live") <= budgets.KEY_DAILY_USD + 1e-9
    assert (budgets.share("worker"), budgets.share("bulk"), budgets.share("live")) == (0.60, 0.30, 0.10)
    assert budgets.RPM_TOTAL >= 16 and budgets.LIVE_RPM >= 4
    assert budgets.role_of("read") == "bulk" and budgets.role_of("live") == "live" and budgets.role_of("worker") == "worker"
    now = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
    budgets.record("bulk", 0.29, now)
    budgets.record("worker", 0.5, now)
    assert not budgets.over("bulk", now)
    budgets.record("bulk", 0.02, now)
    assert budgets.over("bulk", now) and not budgets.over("worker", now)
    assert not budgets.over("bulk", datetime(2026, 10, 16, 16, 1, tzinfo=timezone.utc))   # a new budget day
    slept = []
    clock = iter([now, now, datetime(2026, 10, 16, 16, 4, tzinfo=timezone.utc)])
    budgets.wait_for_share("bulk", log=lambda *a: None, sleep=slept.append, now=lambda: next(clock))
    assert len(slept) == 1 and slept[0] >= 6 * 3600
