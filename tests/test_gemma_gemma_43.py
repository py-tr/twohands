"""scripts/gemma_gemma_43.py on a mocked endpoint: read A (page + 4 tiles) and read B (page + 6 tiles) per form, the
Gemma+Gemma and Gemma+Qwen two-reader tiers, and the shared-mistake count. No model call."""
import json

from PIL import Image

from scripts import gemma_gemma_43 as GG
from twohands import schema

S = schema.load()
KEYS = S["keys"]
BASE = {k: 0 for k in KEYS} | {"SOBRANTES": 5, "VOTARON": 10, "PERSONAS_Y_REP": 10, "SACADOS": 10, "PAN": 10, "TOTAL": 10}
# what each read returns, per form: k2 both reads wrong the same way; k3 read A wrong alone
READS = {("k1", "A"): {}, ("k1", "B"): {}, ("k2", "A"): {"SOBRANTES": 6}, ("k2", "B"): {"SOBRANTES": 6},
         ("k3", "A"): {"PAN": 9}, ("k3", "B"): {}}


def content(vals):
    return json.dumps({"values": [{"label": f["key"], "n": vals[f["key"]], "w": vals[f["key"]]} for f in S["fields"]]})


def test_reads_both_tilings_and_scores_tiers(tmp_path):
    for k in ("k1", "k2", "k3"):
        Image.new("RGB", (1200, 776), "white").save(tmp_path / f"{k}.jpg")
    seen = []

    def chat(body):
        imgs = sum(1 for c in body["messages"][1]["content"] if c["type"] == "image_url")
        rid = "A" if imgs == 5 else "B"
        text = body["messages"][1]["content"][-1]["text"]
        k = next(c for c in ("k1", "k2", "k3") if (c, rid) not in seen)
        seen.append((k, rid))
        assert body["temperature"] == 0 and ("Image 6" in text) == (rid == "B")
        return {"choices": [{"message": {"content": content(BASE | READS[(k, rid)])}, "finish_reason": "stop"}],
                "usage": {}}, 1

    out = GG.do_read(1, chat=chat, claves=["k1", "k2", "k3"], pages=tmp_path, out=tmp_path / "gg.jsonl")
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    assert sorted((r["clave"], r["read"], r["tiles"]) for r in rows) == [
        ("k1", "A", 4), ("k1", "B", 6), ("k2", "A", 4), ("k2", "B", 6), ("k3", "A", 4), ("k3", "B", 6)]
    assert len({r["prompt_sha256"] for r in rows if r["read"] == "A"} | {r["prompt_sha256"] for r in rows if r["read"] == "B"}) == 2
    assert all(r["parsed_ok"] for r in rows)

    R = {"claves": ["k1", "k2", "k3"], "truth": {k: dict(BASE) for k in ("k1", "k2", "k3")}, "graded": KEYS}
    Q = {k: {"clave": k, "parsed_ok": True, "fields": {f: {"n": v, "w": v} for f, v in BASE.items()}} for k in ("k1", "k2", "k3")}
    c = GG.compare(rows, Q, R, qwen_label="mock")
    t = c["tiers"]
    assert t["gemma_gemma"]["forms_accepted"] == ["k1", "k2"] and t["gemma_gemma"]["errors"] == 1
    assert t["gemma_gemma"]["error_list"] == [{"clave": "k2", "field": "SOBRANTES", "read": 6, "truth": 5}]
    assert t["gemma_qwen"]["forms_accepted"] == ["k1", "k3"] and t["gemma_qwen"]["errors"] == 0
    assert c["shared_gemma_gemma"]["both_wrong_same_value"] == 1 and c["shared_gemma_gemma"]["only_first_wrong"] == 1
    assert c["shared_gemma_qwen"]["both_wrong_same_value"] == 0
    line = GG.row_text(c)
    assert "SHARE mistakes" in line and "Gemma+Gemma: 2/3 accepted, 1 of 46" in line


def test_truncated_reply_is_not_a_read():
    r = GG.rec("k", "B", {"parsed": {"values": []}, "finish_reason": "length", "content": "{"}, S, S)
    assert r["parsed_ok"] is False and r["fields"] == {}


def test_read_refuses_without_switch(monkeypatch):
    monkeypatch.delenv("TWOHANDS_BASE_URL", raising=False)
    import pytest
    with pytest.raises(SystemExit):
        GG.do_read(1, claves=["k1"])
