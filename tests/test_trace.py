"""/trace and docs/TRACE.md: two real forms, request to receipt, from stored data (scripts/build_trace.py)."""
import json
import re

from fastapi.testclient import TestClient

from app.main import app
from twohands import REPO

client = TestClient(app)
T = json.loads((REPO / "app" / "data" / "trace.json").read_text(encoding="utf-8"))


def test_trace_page_shows_both_forms_and_verified_receipts():
    h = client.get("/trace").text
    a, b = T["forms"]
    assert (a["kind"], b["kind"]) == ("accepted", "routed") and b["form"] == "122655C0100"
    for f in T["forms"]:
        assert f["receipt"]["verified"] and f["receipt"]["leaf_hash"] in h and f["crop_site"].replace("&", "&amp;") in h
    assert "VERIFIED" in h and T["request"]["prompt_sha256"] in h and "AMD Token Factory" in h
    assert b["gate"]["accepted"] is False and a["gate"]["accepted"] is True


def test_trace_names_no_party_no_key_and_no_fraud():
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    import build_trace
    md = (REPO / "docs" / "TRACE.md").read_text(encoding="utf-8")
    h = client.get("/trace").text
    for text in (md, re.sub(r"<[^>]+>", " ", h)):
        assert build_trace.leaks(text) == []
        assert "AMD_KEY" not in text and "Bearer" not in text
    assert 'href="/trace"' in client.get("/results").text
