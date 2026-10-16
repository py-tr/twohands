import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture(autouse=True)
def _offline_model_list(monkeypatch, tmp_path):
    """No test reaches GET /models on the real endpoint: the list says both models are offered, nothing is logged."""
    monkeypatch.setenv("TWOHANDS_OTS", "0")   # no test submits a report root to the OpenTimestamps calendars
    monkeypatch.setenv("TWOHANDS_SPEND_FILE", str(tmp_path / "spend.jsonl"))   # fake costs never reach cache/spend.jsonl
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
