"""Web app: routes, precomputed viewer, verdict rendering, image safety, spike numbers reproduced."""
import re

import pytest
from fastapi.testclient import TestClient

from app import store as storemod
from app.crops import field_boxes, mask_left_edge
from app.main import app

client = TestClient(app)
PAGES = ["/", "/forms", "/form/211294C0100", "/form/201720E0100", "/form/156723B0100", "/ledger/BALCOMBE-GABLES__03",
         "/review", "/audit", "/results"]


@pytest.mark.parametrize("url", PAGES)
def test_pages_200(url):
    r = client.get(url)
    assert r.status_code == 200, r.text[:500]
    assert "<title>" in r.text


def test_every_form_and_sheet_renders():
    s = storemod.get_store()
    for k in s.ine_claves():
        assert client.get(f"/form/{k}").status_code == 200, k
        for rid in s.runs:
            if k in s.runs[rid]["reads"]:
                assert client.get(f"/form/{k}?run={rid}").status_code == 200, (k, rid)
    for sh in s.ledger["sheets"]:
        assert client.get(f"/ledger/{sh['id']}").status_code == 200, sh["id"]


def test_unknown_404():
    assert client.get("/form/NOPE").status_code == 404
    assert client.get("/ledger/NOPE").status_code == 404


def test_viewer_routed_verdict_from_precomputed():
    html = client.get("/form/211294C0100").text
    assert "Routed: TOTAL digits 262, words 162, rows sum 262" in html
    assert 'src="/masked/211294C0100.jpg"' in html


def test_viewer_accepted_verdict():
    html = client.get("/form/201720E0100").text
    assert "Accepted: 0 fields to key" in html


def test_viewer_without_masked_image_shows_placeholder():
    s = storemod.get_store()
    k = next((k for k in s.ine_claves() if s.masked_image(k) is None), None)
    if k is None:
        pytest.skip("every form is masked")
    html = client.get(f"/form/{k}").text
    assert "Masked page not prepared yet" in html and f"/masked/{k}" not in html


def test_spike_numbers_reproduced():
    s = storemod.get_store()
    g = s.run_metrics("spike-gemma-v2")
    assert (g["forms"], g["accepted"], g["acc_fields"], g["acc_wrong_raw"], g["acc_wrong_adj"]) == (43, 21, 462, 5, 0)
    q = s.run_metrics("spike-qwen")
    assert (q["forms"], q["accepted"], q["acc_fields"], q["acc_wrong_adj"]) == (43, 22, 484, 0)
    lm = s.ledger_metrics()
    assert (lm["cells"], lm["cols"], lm["acc_cols"], lm["acc_cells"], lm["acc_ok"]) == (4915, 380, 306, 3976, 3976)


def test_keying_errors_on_accepted_forms():
    s = storemod.get_store()
    acc = [e for e in s.keying_errors() if e["status"] == "confirmed" and e["accepted_by"]]
    assert len(acc) == 6 and len({e["clave"] for e in acc}) == 5
    assert all(e["image_value"] != e["official"] for e in acc)


def _read(vals, words=None, labels=None):
    s = storemod.schema()
    v = {k: vals.get(k, 0) for k in s["keys"]}
    w = {k: (words or {}).get(k, v[k]) for k in s["keys"]}
    return storemod.Read("X", "t", v, w, labels or {}, [], bool(labels))


def test_gate_verdict_rendering():
    s = storemod.schema()
    vals = {k: 0 for k in s["keys"]}
    vals.update(PAN=10, MORENA=5, TOTAL=15, VOTARON=14, REPRESENTANTES=1, PERSONAS_Y_REP=15, SACADOS=15)
    ev = storemod.evaluate(_read(vals))
    assert ev["accepted"] and ev["line"] == "Accepted: 0 fields to key"
    ev = storemod.evaluate(_read(vals, words={"TOTAL": 25}))
    assert not ev["accepted"] and ev["line"] == "Routed: TOTAL digits 15, words 25, rows sum 15"
    assert ev["failing"] == ["TOTAL"]
    bad = dict(vals, PAN=11)
    ev = storemod.evaluate(_read(bad, words={"PAN": 11}))
    assert "rows sum to TOTAL (16 vs 15)" in ev["line"]
    # a reviewer's value settles the field and the identities re-check
    assert storemod.evaluate(_read(vals, words={"TOTAL": 25}), overrides={"TOTAL": 15})["accepted"]


def test_label_check_applies_to_reads_with_labels():
    s = storemod.schema()
    vals = {k: 0 for k in s["keys"]}
    labels = {f["key"]: "PAN" for f in s["fields"]}  # every row claims to be PAN
    ev = storemod.evaluate(_read(vals, labels=labels))
    assert not ev["accepted"] and any(f["status"] == "label" for f in ev["fields"])


def test_core_jsonl_adapter_matches_core_gate():
    """A results/*.jsonl row that only carries the raw reader output is gated by the core gate."""
    from twohands import gate as gatemod
    s = storemod.schema()
    items = [{"label": "x", "n": 1, "w": 1} for _ in s["fields"]]
    r = storemod.read_from_core("Z", "run", {"clave": "Z", "parsed": {"values": items}})
    assert r.stored_accepted == gatemod.gate({"values": items}, s).accepted is False


# ------------------------------------------------------------------ images: masked only
def test_masked_route_only_serves_from_masked_dir():
    s = storemod.get_store()
    for k in s.ine_claves():
        p = s.masked_image(k)
        if p is not None:
            assert storemod.MASKED in p.resolve().parents
    for bad in ["/masked/..%2F..%2Fschemas%2Fx.jpg", "/masked/../app/main.jpg", "/masked/%2e%2e%2fraw.jpg",
                "/crop/..%2F..%2Fx/TOTAL.jpg"]:
        assert client.get(bad).status_code in (404, 403, 422), bad
    k = next((k for k in s.ine_claves() if s.masked_image(k) is None), None)
    if k:
        assert client.get(f"/masked/{k}.jpg").status_code == 404
        assert client.get(f"/crop/{k}/TOTAL.jpg").status_code == 404


def test_rendered_images_only_masked_crop_or_static():
    for url in PAGES:
        html = client.get(url).text
        for src in re.findall(r'<img[^>]+src="([^"]+)"', html):
            assert src.startswith(("/masked/", "/crop/", "/static/")), (url, src)


def test_crop_boxes_stay_left_of_privacy_mask():
    s = storemod.schema()
    edge = mask_left_edge(s)
    boxes = field_boxes(s)
    assert set(boxes) == set(s["keys"])
    assert all(b[2] < edge for b in boxes.values())


def test_crop_is_jpeg_when_masked_page_exists():
    s = storemod.get_store()
    k = next((k for k in s.ine_claves() if s.masked_image(k)), None)
    if k is None:
        pytest.skip("no masked page yet")
    r = client.get(f"/crop/{k}/TOTAL.jpg")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and r.content[:2] == b"\xff\xd8"
    assert client.get(f"/crop/{k}/NOT_A_FIELD.jpg").status_code == 404
