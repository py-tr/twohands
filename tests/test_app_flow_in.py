"""A new run in the core's record format (results/calls_<model>.jsonl, run.record) flows into the app without code
changes, and takes over the headline once it is large enough. Uses a temporary results directory."""
import json

from fastapi.testclient import TestClient

from app import store as storemod
from app.main import app


def _record(clave, r, s):
    ev = storemod.evaluate(r)
    return {"form_id": clave, "clave": clave, "layout": "movil", "stratum": "x", "schema": s["form"],
            "model": "Gemma-4-31B-IT", "model_key": "gemma", "no_call": False, "accepted": ev["accepted"],
            "routed": not ev["accepted"], "route_reasons": ev["reasons"], "route_codes": [],
            "fields": {k: {"label": None, "n": r.values[k], "w": r.words[k], "fix": False} for k in s["keys"]},
            "latency_s": 50.0, "cost_usd": 0.0001, "error": None}


def test_calls_jsonl_flows_in_and_takes_headline(tmp_path, monkeypatch):
    s = storemod.schema()
    spike = storemod.get_store().runs["spike-gemma-v2"]["reads"]
    rows = [_record(k, r, s) for k, r in spike.items()]
    rows.append({"clave": "000000X0000", "no_call": True, "accepted": False, "route_reasons": ["form not located: x"],
                 "fields": {}, "model": "Gemma-4-31B-IT"})
    rows.append({"clave": "122838C0100", "status": "ok", "image": "data/masked/x.jpg"})  # a prepare row, not a read
    (tmp_path / "calls_gemma.jsonl").write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    (tmp_path / "prepare.jsonl").write_text(json.dumps({"clave": "122838C0100", "status": "ok"}), encoding="utf-8")
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(storemod, "RESULTS", tmp_path)
    monkeypatch.setattr(storemod, "HEADLINE_MIN_FORMS", 40)
    monkeypatch.setattr(storemod, "_STORE", None)
    st = storemod.get_store()
    assert "calls_gemma" in st.runs and "prepare" not in st.runs
    m = st.run_metrics("calls_gemma")
    assert m["forms"] == 44 and m["not_located"] == 1 and m["graded_forms"] == 43
    # stored row labels are None here, so the label check routes everything with labels: the stored verdict
    # (from the core gate) is what counts in the metrics
    assert m["accepted"] == sum(1 for r in rows[:43] if r["accepted"])
    assert st.headline_run() == "calls_gemma"
    # viewer verdict agrees with the stored core verdict
    for r in rows[:43]:
        assert storemod.evaluate(st.runs["calls_gemma"]["reads"][r["clave"]])["accepted"] == r["accepted"]
    trunc = storemod.Read("T", "x", dict(spike["201720E0100"].values), dict(spike["201720E0100"].words), {}, [], False,
                          stored_accepted=False, stored_reasons=["reply truncated (finish_reason=length)"])
    ev = storemod.evaluate(trunc)
    assert not ev["accepted"] and "truncated" in ev["line"]
    assert "pre-registered random run" in st.runs["calls_gemma"]["label"]
    c = TestClient(app)
    assert "calls_gemma.jsonl" in c.get("/results").text
    assert c.get("/form/000000X0000").status_code == 200
    monkeypatch.setattr(storemod, "_STORE", None)
