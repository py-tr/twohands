"""Schema builder (/builder): the identity parser, the YAML writer, the round trip of our real schema, the bundled
timesheet sample end to end (register, mask, gate), and the live-test path with a mocked reader and endpoint.
No request reaches the real AMD endpoint from these tests."""
import io
import json
import time

import numpy as np
import pytest
import yaml
from fastapi.testclient import TestClient
from PIL import Image

from app import builder as B
from app import live as livemod
from app.main import app
from twohands import REPO
from twohands import gate as gatemod
from twohands import reader
from twohands import schema as schemamod

client = TestClient(app)
KEYS = ["A", "B", "C", "OPT01", "OPT02", "OPT03", "NULOS", "NO_REG", "TOTAL"]


@pytest.fixture
def userdir(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "USER_DIR", tmp_path / "user")
    monkeypatch.setattr(B, "TESTS_DIR", tmp_path / "tests")
    monkeypatch.setattr(livemod, "BUDGET_FILE", tmp_path / "budget.json")
    return tmp_path


# ------------------------------------------------------------------------------------------------ parser
def test_parser_sum_range_and_terms():
    r = B.parse_identity("sum(OPT01..OPT03, NULOS, NO_REG) == TOTAL", KEYS)
    assert r["sum"] == ["OPT01", "OPT02", "OPT03", "NULOS", "NO_REG"] and r["equals"] == ["TOTAL"]
    r = B.parse_identity("parts: A + B == C", KEYS)
    assert r == {"kind": "sum", "name": "parts", "sum": ["A", "B"], "equals": ["C"]}
    r = B.parse_identity("C - B == A", KEYS)  # '-' moves a term across: C == A + B
    assert r["sum"] == ["C"] and r["equals"] == ["A", "B"]
    assert B.parse_identity("words == digits", KEYS)["kind"] == "words"
    assert B.parse_identity("   ", KEYS) is None and B.parse_identity("# note", KEYS) is None


def test_parser_vote_shorthand():
    r = B.parse_identity("sum(OPT01..OPT03) == TOTAL", KEYS, vote_keys=["OPT01", "OPT02", "OPT03"])
    assert r["sum"] == "@vote"
    assert B.parse_identity("sum(@vote) == TOTAL", KEYS, ["OPT01", "OPT02", "OPT03"])["sum"] == "@vote"


@pytest.mark.parametrize("line,needle", [
    ("A + D == C", "unknown field 'D'"),
    ("TOTL == A", "did you mean TOTAL"),
    ("A + 3 == C", "number"),
    ("A = C", "use =="),
    ("A == B == C", "only one '=='"),
    ("sum(OPT03..OPT01) == TOTAL", "runs backwards"),
    ("A + B == A", "both sides"),
    ("A + A == C", "counted twice"),
    ("== C", "left side is empty"),
    ("A + B ==", "right side is empty"),
    ("A + B", "needs '=='"),
    ("A * B == C", "unexpected '*'"),
    ("sum(A, B == C", "')'"),
    ("__import__('os') == A", "unexpected"),
])
def test_parser_errors_are_readable(line, needle):
    with pytest.raises(B.ExprError) as e:
        B.parse_identity(line, KEYS)
    assert needle in e.value.msg


def test_parser_reports_the_column():
    with pytest.raises(B.ExprError) as e:
        B.parse_identity("x: A + D == C", KEYS)
    assert e.value.col == "x: A + D == C".index("D")


def test_validate_endpoint():
    r = client.post("/api/builder/validate", json={"fields": [{"key": k} for k in KEYS],
                                                    "identities": ["A + B == C", "A + Q == C", "", "words == digits"]})
    out = r.json()["lines"]
    assert out[0]["ok"] and out[0]["text"] == "A + B = C"
    assert not out[1]["ok"] and "unknown field 'Q'" in out[1]["error"]
    assert out[2].get("blank") and out[3]["kind"] == "words" and out[3]["warn"]


# ------------------------------------------------------------------------------------------------ round trip
def _boxes_close(a, b, tol=1e-3):
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(np.ravel(a), np.ravel(b)))


def test_round_trip_of_the_real_schema(userdir):
    orig = schemamod.load()
    st = client.get("/api/builder/sample/ine").json()["state"]
    st = json.loads(json.dumps(st))  # as the browser sends it back
    r = client.post("/api/builder/save", json=st)
    assert r.status_code == 200, r.text
    saved = B.load_yaml(userdir / "user" / "mx_presidencia_2024.yaml")
    assert r.json()["yaml"] == (userdir / "user" / "mx_presidencia_2024.yaml").read_text(encoding="utf-8")
    # same fields: every original attribute, same order (the builder adds the measured per-field boxes)
    assert saved["keys"] == orig["keys"] and saved["vote_keys"] == orig["vote_keys"]
    for a, b in zip(orig["fields"], saved["fields"]):
        assert {k: v for k, v in b.items() if k not in ("box", "words_box")} == a
        assert len(b["box"]) == 4
    # boxes within 0.001
    lo, ls = orig["layout"], saved["layout"]
    assert ls["canonical"]["size"] == lo["canonical"]["size"]
    assert _boxes_close(ls["canonical"]["markers"], lo["canonical"]["markers"])
    assert abs(ls["canonical"]["marker_size"] - lo["canonical"]["marker_size"]) <= 1e-3
    for k in lo["mask"]:
        assert _boxes_close(ls["mask"][k], lo["mask"][k])
    assert [t["name"] for t in ls["tiles"]] == [t["name"] for t in lo["tiles"]]
    assert [t["says"] for t in ls["tiles"]] == [t["says"] for t in lo["tiles"]]
    for a, b in zip(lo["tiles"], ls["tiles"]):
        assert _boxes_close(a["box"], b["box"])
    for k, v in lo["field_regions"].items():
        assert _boxes_close(ls["field_regions"][k], v)
    for k in ("template", "landmarks", "reference"):
        assert ls[k] == lo[k]
    # same identities, same party aliases
    assert saved["identities"] == orig["identities"]
    assert saved["party_aliases"] == orig["party_aliases"]
    # and saving the saved one again is a fixed point
    s2, errs, _ = B.state_to_schema(B.schema_to_state(saved))
    assert not errs and B.to_yaml(s2) == r.json()["yaml"]


def _stored_reads(n=40):
    last = {}
    with (REPO / "results" / "calls_gemma.jsonl").open(encoding="utf-8") as fh:
        for ln in fh:
            row = json.loads(ln)
            last[row["clave"]] = row
    rows = [r for r in last.values() if r.get("parsed_ok")]
    acc = [r for r in rows if r.get("accepted")][: n // 2]
    rej = [r for r in rows if not r.get("accepted")][: n // 2]
    return acc + rej


def test_saved_schema_gives_the_same_verdict_on_stored_reads(userdir):
    orig = schemamod.load()
    st = B.ine_state()
    s, errs, _ = B.state_to_schema(st)
    assert not errs
    B.save_schema(s)
    saved = B.load_yaml(userdir / "user" / "mx_presidencia_2024.yaml")
    rows = _stored_reads()
    assert any(r["accepted"] for r in rows) and any(not r["accepted"] for r in rows)
    for r in rows:
        parsed = reader.parse(r["content"])
        a, b = gatemod.gate(parsed, orig), gatemod.gate(parsed, saved)
        assert (a.accepted, a.codes, a.reasons, a.identities) == (b.accepted, b.codes, b.reasons, b.identities)
        assert b.accepted == r["accepted"], r["clave"]


def test_gate_stored_read_endpoint(userdir):
    client.post("/api/builder/save", json=B.ine_state())
    d = client.post("/api/builder/gate/mx_presidencia_2024").json()
    assert d["accepted"] == d["recorded_accepted"]
    assert len(d["fields"]) == 23


# ------------------------------------------------------------------------------------------------ save errors
def test_save_refuses_a_broken_schema(userdir):
    st = B.timesheet_state()
    st["identities"] = ["sum(MON..SUNDAY) == TOTAL"]
    st["markers"] = st["markers"][:3]
    st["fields"][0]["box"] = st["mask"][0]
    r = client.post("/api/builder/save", json=st)
    assert r.status_code == 422
    errs = " | ".join(r.json()["errors"])
    assert "unknown field 'SUNDAY'" in errs and "four corner markers" in errs and "inside the privacy mask" in errs
    assert not (userdir / "user").exists() or not any((userdir / "user").iterdir())


def test_slug_cannot_escape_the_user_dir(userdir):
    st = B.timesheet_state()
    st["form"] = "../../twohands/evil"
    r = client.post("/api/builder/save", json=st)
    assert r.status_code == 200 and r.json()["slug"] == "twohands_evil"
    assert (userdir / "user" / "twohands_evil.yaml").is_file()
    assert client.get("/api/builder/schema/..%2Fx.yaml").status_code == 404


# ------------------------------------------------------------------------------------------------ timesheet sample
def _ts_parsed(vals, total, total_w=None):
    labels = B.TS_DAYS + ["WEEKLY TOTAL"]
    items = [{"label": labels[i], "n": v, "w": v} for i, v in enumerate(vals)]
    items.append({"label": labels[-1], "n": total, "w": total if total_w is None else total_w})
    return {"values": items}


def test_timesheet_schema_is_engine_format(userdir):
    r = client.post("/api/builder/save", json=B.timesheet_state())
    assert r.status_code == 200, r.text
    p = userdir / "user" / "weekly_timesheet.yaml"
    s = schemamod.load(str(p))  # the engine's own loader reads it
    assert s["keys"] == B.TS_KEYS + ["TOTAL"]
    assert s["identities"] == [{"name": "days add up to the week", "sum": B.TS_KEYS, "equals": ["TOTAL"]}]
    assert all(f["words_box"] for f in s["fields"]) and len(s["layout"]["canonical"]["markers"]) == 4
    assert gatemod.gate(_ts_parsed(B.TS_GOOD, 38), s).accepted
    bad = gatemod.gate(_ts_parsed(B.TS_GOOD, 40), s)
    assert not bad.accepted and bad.codes == ["identity"]
    words = gatemod.gate(_ts_parsed(B.TS_GOOD, 38, total_w=40), s)
    assert "words" in words.codes
    prompt = B.build_prompt(s)
    assert "exactly 8 items" in prompt and "MONDAY" in prompt and "INE" not in prompt


def test_timesheet_photo_is_registered_by_its_markers_and_masked(userdir):
    client.post("/api/builder/save", json=B.timesheet_state())
    s = B.schema_for("weekly_timesheet")
    photo = Image.open(io.BytesIO(B.sample_png("timesheet_filled")))
    page, info = B.prepare(photo, s)
    assert info["locator"] == "corner markers" and page.size == (B.TS_W, B.TS_H)
    a = np.asarray(page.convert("L"))
    x0, y0, x1, y1 = s["layout"]["mask"]["movil"][0]
    W, H = page.size
    assert a[int(y0 * H) + 3:int(y1 * H) - 3, int(x0 * W) + 3:int(x1 * W) - 3].max() < 40  # signature blacked out
    # the TOTAL digit box landed where the schema says: dark ink inside, white page around
    bx = s["fields"][-1]["box"]
    crop = a[int(bx[1] * H):int(bx[3] * H), int(bx[0] * W):int(bx[2] * W)]
    assert (crop < 100).mean() > 0.04


def test_whole_image_mode(userdir):
    st = B.timesheet_state()
    st["whole_image"] = True
    s, errs, _ = B.state_to_schema(st)
    assert not errs and s["layout"]["canonical"].get("whole_image") and "markers" not in s["layout"]["canonical"]
    page, info = B.prepare(Image.open(io.BytesIO(B.sample_png("timesheet_blank"))), s)
    assert info["locator"] == "whole image"


# ------------------------------------------------------------------------------------------------ live test path
def _drain(m, job_id, timeout=5.0):
    t = time.time() + timeout
    while not m.jobs[job_id].done and time.time() < t:
        time.sleep(0.02)


def test_live_test_queues_one_read_and_gates_it(userdir):
    calls = []

    def fake_read(model, page, s):
        calls.append((model, str(page), s["form"]))
        return {"parsed": _ts_parsed(B.TS_GOOD, 40), "secs": 0.5, "usage": {"cost": 0.0001}}

    main = livemod.LiveManager(usage_fn=lambda: {"daily_cost_remaining_usd": 0.9})
    app.state.builder_live = B.BuilderLive(main, read_fn=fake_read)
    try:
        client.post("/api/builder/save", json=B.timesheet_state())
        r = client.post("/api/builder/test/weekly_timesheet/sample/timesheet_wrong")
        d = r.json()
        assert d["ok"] and d["job"], d
        _drain(app.state.builder_live, d["job"])
        j = client.get(d["status_url"]).json()
        ver = next(e for e in j["events"] if e["type"] == "verdict")
        assert ver["accepted"] is False and ver["codes"] == ["identity"]
        assert ver["identities"][0] == {"name": "days add up to the week", "ok": False, "lhs": 38, "rhs": 40}
        assert len(calls) == 1 and calls[0][2] == "weekly_timesheet"
        # only the masked page (and small JSON notes) were stored
        files = sorted(p.name for p in (userdir / "tests").iterdir())
        assert files == [f"{d['id']}.jpg", f"{d['id']}.json", f"{d['id']}.read.json"]
        assert client.get(d["masked_url"]).status_code == 200
        budget = json.loads((userdir / "budget.json").read_text())
        assert list(budget.values())[0]["reads"] == 1  # the shared daily allowance counts builder reads
    finally:
        app.state.builder_live = None


def test_live_test_endpoint_down_is_honest(userdir):
    def boom():
        raise TimeoutError("no answer")

    main = livemod.LiveManager(usage_fn=boom)
    app.state.builder_live = B.BuilderLive(main, read_fn=lambda *a: pytest.fail("must not read"))
    try:
        client.post("/api/builder/save", json=B.timesheet_state())
        png = B.sample_png("timesheet_filled")
        d = client.post("/api/builder/test/weekly_timesheet", content=png, headers={"Content-Type": "image/png"}).json()
        assert d["ok"] and d["refused"] == "endpoint" and "not answering" in d["message"]
        assert "job" not in d
    finally:
        app.state.builder_live = None


def test_unregistered_photo_stores_nothing(userdir):
    client.post("/api/builder/save", json=B.timesheet_state())
    buf = io.BytesIO()
    Image.new("RGB", (900, 600), "white").save(buf, "PNG")
    r = client.post("/api/builder/test/weekly_timesheet", content=buf.getvalue(), headers={"Content-Type": "image/png"})
    assert r.status_code == 422 and r.json()["code"] == "not_located" and "whole image" in r.json()["message"]
    assert not (userdir / "tests").exists() or not any((userdir / "tests").iterdir())


# ------------------------------------------------------------------------------------------------ pages
def test_builder_page_and_samples():
    r = client.get("/builder")
    assert r.status_code == 200 and "A tool for any self-checking form" in r.text and "synthetic sample" in r.text
    assert client.get("/builder/sample/timesheet_blank.png").headers["content-type"] == "image/png"
    assert client.get("/builder/sample/ine_blank.jpg").status_code == 200
    assert client.get("/builder/sample/nope.png").status_code == 404
    st = client.get("/api/builder/sample/ine").json()["state"]
    assert len(st["fields"]) == 23 and all(f.get("box") for f in st["fields"]) and len(st["markers"]) == 4
    assert st["identities"][0] == "rows sum to TOTAL: sum(PAN..NULOS) == TOTAL"
