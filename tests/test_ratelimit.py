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
