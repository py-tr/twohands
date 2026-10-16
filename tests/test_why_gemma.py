"""The Gemma table, its lead sentence and the misreads the arithmetic caught: computed from the committed data,
carried word for word by the docs and the results page."""
from __future__ import annotations

from fastapi.testclient import TestClient
from PIL import Image

from app import why_gemma as W
from app.main import app
from scripts import why_gemma as script

client = TestClient(app)


def test_lead_is_derived_from_the_bakeoff():
    d = W.load()
    g, q = d["models"][W.GEMMA], d["models"][W.QWEN]
    assert W.lead(d) == (
        f"Same 300 forms, same gate, on AMD: Gemma accepts {g['accepted'] / q['accepted']:.1f}x the forms Qwen3.8-27B "
        f"does at the same error rate, {q['cost_per_1000_usd'] / g['cost_per_1000_usd']:.1f}x cheaper and "
        f"{q['mean_latency_s'] / g['mean_latency_s']:.1f}x faster, with no truncated answers. Every zero-error "
        "two-reader pair includes Gemma; the only pair without it made errors (2 of 814).")
    assert "1.8x" in W.lead(d) and "4.6x" in W.lead(d) and "2.8x" in W.lead(d)
    rows = {r["who"]: r for r in W.rows(d)}
    assert rows[W.GEMMA]["acc"] == "55 of 300 (18%)" and rows[W.GEMMA]["wrong"] == "2 of 1,210"
    assert rows[W.QWEN]["wrong"] == "1 of 682 (+2 undecided)" and rows[W.QWEN]["time"] == "241 s"
    assert rows[f"{W.GEMMA} + {W.QWEN}"]["wrong"] == "0 of 1,958"
    assert not any("DeepSeek" in r for r in rows)   # halted after 2 forms: not compared


def test_the_same_error_rate_wording_needs_the_rates_to_be_close():
    d = W.load()
    d["models"][W.GEMMA] = dict(d["models"][W.GEMMA], accepted_wrong=12)
    assert "same error rate" not in W.lead(d)


def test_docs_carry_the_current_blocks():
    assert script.main(["--check"]) == 0


def test_caught_misreads_are_digit_misreads_only_a_sum_caught():
    cs = W.caught()
    assert len(cs) == 2
    for c in cs:
        assert c["n"] == c["w"] != c["paper"] == c["prep"] == c["certified"]   # words agreed with the misread digits
        assert c["lhs"] != c["rhs"] and c["fixed"] == c["rhs"]
        assert c["name"].startswith("Option ") and c["url"].endswith("?label=0")
        line = W.caught_line(c)
        assert f"{c['lhs']} ≠ {c['rhs']}" in line and "fraud" not in line.lower()


def test_caught_crops_are_masked_crops_without_the_logo_column():
    from app import crops, store
    edge = crops.mask_left_edge(store.schema())
    for c in W.caught():
        r = client.get(c["url"])
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        im = Image.open(script.REPO / "docs" / c["crop"])
        page = Image.open(script.REPO / "data" / "masked" / f"{c['clave']}.jpg")
        # cut from the masked page: starts right of the logo column, ends left of the privacy mask
        assert im.size[0] <= int((edge - crops.LABEL_X1) * page.size[0]) + 1


def test_results_page_shows_the_table_and_the_caught_misreads():
    h = client.get("/results").text
    s = h[h.index('id="gemma"'):]
    assert W.lead() in s and "Wrong of accepted fields" in s and "0 of 1,958" in s
    for c in W.caught():
        assert c["url"].replace("&", "&amp;") in s or c["url"] in s
    assert "Gemma vs the other readers" in client.get("/").text
