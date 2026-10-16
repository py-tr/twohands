import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

REPO = Path(__file__).resolve().parent.parent

# Real state that live processes (the run chain, the worker, the web app) share. No test may write to it: the
# autouse fixture below points every writer at tmp copies, and the audit hook turns any write that still slips
# through into an immediate PermissionError naming the test (instead of fake rows in the real ledger).
PROTECTED = [REPO / "cache", REPO / "app" / "state", REPO / "results" / "endpoint_health.jsonl", REPO / "live_audit"]
PROTECTED = [p.resolve() for p in PROTECTED]
_GUARD = {"on": False}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def _protected(p) -> bool:
    try:
        rp = Path(os.fsdecode(p)).resolve()
    except Exception:  # noqa: BLE001
        return False
    return any(rp == q or q in rp.parents for q in PROTECTED)


def _audit(event, args):
    if not _GUARD["on"]:
        return
    if event == "open":
        path, mode, flags = args
        if path is None or isinstance(path, int):
            return
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or bool((flags or 0) & _WRITE_FLAGS)
        target = path
    elif event in ("os.remove", "os.rename", "os.replace", "os.mkdir", "os.rmdir", "shutil.rmtree"):
        writing, target = True, args[0]
    else:
        return
    if writing and not isinstance(target, int) and _protected(target):
        _GUARD["on"] = False   # no re-entry while the error is built
        try:
            raise PermissionError(f"test wrote to real state: {target} ({os.environ.get('PYTEST_CURRENT_TEST')})")
        finally:
            _GUARD["on"] = True


sys.addaudithook(_audit)


def _copy(src: Path, dst: Path) -> Path:
    """dst = a private copy of src (file or directory) when src exists; the parent is created either way."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    elif src.is_file():
        shutil.copyfile(src, dst)
    return dst


@pytest.fixture(autouse=True)
def _isolate_state(monkeypatch, tmp_path_factory):
    """Every state file a test could write lives in a private tmp dir: the spend ledger, the cross-process rate limiter, the
    endpoint log (a private copy, so tests still read the real windows), app/state (the small files and the live
    reads copied; audits / uploads / timestamps start empty) and the live-audit worker dir. Env overrides reach
    subprocesses too."""
    st = tmp_path_factory.mktemp("state")   # not tmp_path: tests that list their own tmp_path see only their files
    monkeypatch.setenv("TWOHANDS_SPEND_FILE", str(st / "spend.jsonl"))       # fake costs never reach cache/spend.jsonl
    monkeypatch.setenv("TWOHANDS_RATE_FILE", str(st / "ratelimit.json"))     # never wait behind the real run's pace
    from twohands import amd, ratelimit
    health = _copy(REPO / "results" / "endpoint_health.jsonl", st / "endpoint_health.jsonl")
    monkeypatch.setenv("TWOHANDS_HEALTH_FILE", str(health))
    monkeypatch.setattr(amd, "HEALTH", health)
    if "app.health" in sys.modules:
        monkeypatch.setattr(sys.modules["app.health"], "HEALTH", health)
    ratelimit.reset_shared(None)
    monkeypatch.setenv("TWOHANDS_WORKER_DIR", str(st / "live_audit"))
    state = st / "app_state"
    _copy(REPO / "app" / "state" / "live", state / "live")
    for f in ("spotcheck.json", "review.json", "public_verdicts.jsonl", "live_budget.json"):
        _copy(REPO / "app" / "state" / f, state / f)
    targets = {"app.store": {"STATE": state}, "app.capture_audit": {"AUDITS": state / "audits", "TIMESTAMPS": state / "timestamps"},
               "app.live": {"LIVE_DIR": state / "live", "BUDGET_FILE": state / "live_budget.json"},
               "app.request": {"REQUESTS": state / "requests.jsonl"}, "app.review": {"FILE": state / "review.json"},
               "app.upload": {"UPLOADS": state / "uploads"}, "app.builder": {"TESTS_DIR": state / "uploads" / "builder"},
               "app.judge": {"FILE": state / "public_verdicts.jsonl"}, "app.spotcheck": {"FILE": state / "spotcheck.json"},
               "evolus.case": {"STATE_RUNS": state / "evolus_runs.jsonl", "CALLBACKS": state / "evolus_callbacks.jsonl"}}
    import importlib
    for mod in ("app.store", "app.capture_audit", "app.live", "app.request", "app.review", "app.upload", "app.judge",
                "app.spotcheck"):
        importlib.import_module(mod)   # patched even when a test imports it only inside its body
    for mod, attrs in targets.items():
        m = sys.modules.get(mod)
        for name, val in attrs.items():
            # only a path that still points at real state: a module-scoped fixture's own tmp path is kept
            if m is not None and hasattr(m, name) and _protected(getattr(m, name)):
                monkeypatch.setattr(m, name, val)
    _GUARD["on"] = True
    try:
        yield
    finally:
        _GUARD["on"] = False
        ratelimit.reset_shared(None)


@pytest.fixture(autouse=True)
def _offline_model_list(monkeypatch, _isolate_state):
    """No test reaches GET /models on the real endpoint: the list says both models are offered, nothing is logged."""
    monkeypatch.setenv("TWOHANDS_OTS", "0")   # no test submits a report root to the OpenTimestamps calendars
    from app import livemodel
    c = livemodel.chooser
    monkeypatch.setattr(c, "fetch", lambda: ["Gemma-4-31B-IT", "Qwen3.8-27B"])
    monkeypatch.setattr(c, "record", lambda *a, **k: None)
    monkeypatch.setattr(c, "_listed", None)
    monkeypatch.setattr(c, "_at", -1e18)
    monkeypatch.setattr(c, "_refreshing", False)
    from app import health
    health._cache.update(at=0.0, v=None, key=None)
    yield
