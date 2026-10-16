"""Try it with your own photo: located and masked in memory by the core, ONLY the masked page is stored, the raw
upload never touches the disk, a page that cannot be located stores nothing, and a live read is queued through the
same live-read path. No request reaches AMD (mocked reader and usage)."""
import io
import json
import re
import os
import tempfile
import threading
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app import live as livemod
from app import store as storemod
from app import upload as uploadmod
from app.main import app
from tests.test_app_live import drain
from tests.test_app_neutral import _clean

client = TestClient(app)
SAMPLE = uploadmod.SAMPLES["problem"]["clave"]


def _jpeg(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", quality=92)
    return b.getvalue()


def _files(d):
    return sorted(p.name for p in d.rglob("*") if p.is_file()) if d.exists() else []


@pytest.fixture
def env(tmp_path, monkeypatch):
    up = tmp_path / "uploads"
    monkeypatch.setattr(uploadmod, "UPLOADS", up)
    monkeypatch.setattr(livemod, "LIVE_DIR", tmp_path / "live")
    monkeypatch.setattr(livemod, "BUDGET_FILE", tmp_path / "budget.json")
    tmpd = tmp_path / "tmp"
    tmpd.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmpd))  # anything spooled to a temp file would land here
    gate = threading.Event()
    calls = []

    def reader(model, page):
        calls.append(str(page))
        gate.wait(5)
        r = storemod.get_store().runs["spike-gemma-v2"]["reads"][SAMPLE]
        items = [{"label": None, "n": r.values[f["key"]], "w": r.words[f["key"]]} for f in storemod.schema()["fields"]]
        return {"parsed": {"values": items}, "secs": 1.0,
                "usage": {"cost": 0.0001, "prompt_tokens": 2609, "completion_tokens": 804}}

    m = livemod.LiveManager(reader_fn=reader, usage_fn=lambda: {"daily_cost_remaining_usd": 0.9}, reveal_delay=0)
    old = app.state.live
    app.state.live = m
    yield {"up": up, "tmp": tmpd, "mgr": m, "gate": gate, "calls": calls}
    gate.set()
    drain(m)
    app.state.live = old


def _masked_page():
    p = storemod.get_store().masked_image(SAMPLE)
    if p is None:
        pytest.skip("no masked sample page")
    return p


def test_not_located_stores_nothing(env):
    raw = _jpeg(Image.new("RGB", (1600, 1200), (250, 250, 250)))
    r = client.post("/api/upload", content=raw, headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 422
    j = r.json()
    assert j["code"] == "not_located" and "nothing was stored" in j["message"]
    assert _files(env["up"]) == [] and _files(env["tmp"]) == []
    assert env["calls"] == [] and not env["mgr"].status()["busy"]


def test_not_a_photo(env):
    r = client.post("/api/upload", content=b"hello, not an image", headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 422 and r.json()["code"] == "not_a_photo"
    assert _files(env["up"]) == []


def test_upload_stores_only_the_masked_page_and_queues_a_read(env):
    """A 'photo' whose right-hand column (names and signatures) is NOT masked: the stored page must have it black,
    and the raw bytes must not be anywhere on disk."""
    im = Image.open(_masked_page()).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle([int(0.70 * W), int(0.05 * H), int(0.97 * W), int(0.95 * H)], fill=(255, 255, 255))
    for i in range(12):  # fake handwriting in the private column
        y = int((0.1 + 0.07 * i) * H)
        d.line([int(0.72 * W), y, int(0.95 * W), y + 15], fill=(20, 20, 160), width=6)
    raw = _jpeg(im)
    r = client.post("/api/upload", content=raw, headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 200, r.text
    j = r.json()
    uid = j["id"]
    assert uploadmod.valid_id(uid) and j["job"] and j["page_url"] == f"/try/{uid}"
    # only the masked page and its small note are stored; no temp file, no raw copy
    assert _files(env["up"]) == sorted([f"{uid}.jpg", f"{uid}.json"])
    assert _files(env["tmp"]) == []
    for p in env["up"].iterdir():
        assert p.read_bytes() != raw
    saved = Image.open(env["up"] / f"{uid}.jpg").convert("L")
    sw, sh = saved.size
    edge = int(0.657 * sw) + 4
    col = saved.crop((edge, 0, sw, sh))
    assert max(col.getextrema()) < 40, "the names-and-signatures column must be black in the stored page"
    # the live read went to the masked page, not to anything else
    for _ in range(100):
        if env["calls"]:
            break
        time.sleep(0.02)
    assert env["calls"] and os.path.samefile(env["calls"][0], env["up"] / f"{uid}.jpg")
    env["gate"].set()
    with client.stream("GET", f"/api/live/events/{j['job']}") as resp:
        evs = [json.loads(x[6:]) for x in resp.iter_lines() if x.startswith("data: ")]
    assert any(e["type"] == "verdict" for e in evs)
    assert (env["up"] / f"{uid}.read.json").exists()
    assert "live" not in [p.name for p in env["up"].parent.iterdir()] or not (env["up"].parent / "live" / f"{uid}.json").exists()
    # the result page renders from what was stored, and stays neutral
    html = client.get(f"/try/{uid}").text
    assert f"/upload/{uid}.jpg" in html and "Read again" in html
    # the receipt next to the gate verdict: model, endpoint, tokens in/out, latency, cost of this call
    rc = re.search(r'<span class="small" data-receipt>(.*?)</span>', html, flags=re.S).group(1)
    assert "on AMD Token Factory" in rc and "2,609 tokens in / 804 out" in rc and "1.0 s" in rc and "$0.000100" in rc
    _clean(html, "try result")
    assert client.get(f"/upload/{uid}.jpg").status_code == 200


def test_sample_photo_goes_through_the_same_pipeline(env):
    _masked_page()
    r = client.post("/api/upload/sample/problem")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["fallback"] == SAMPLE and j["job"]
    assert _files(env["up"]) == sorted([f"{j['id']}.jpg", f"{j['id']}.json"])
    assert json.loads((env["up"] / f"{j['id']}.json").read_text())["sample_of"] == SAMPLE
    assert client.post("/api/upload/sample/nope").status_code == 404
    env["gate"].set()


def test_upload_busy_endpoint_keeps_the_masked_page_and_says_so(env):
    _masked_page()
    env["mgr"].usage_fn = lambda: (_ for _ in ()).throw(TimeoutError("x"))
    r = client.post("/api/upload/sample/clean")
    assert r.status_code == 200
    j = r.json()
    assert j["refused"] == "endpoint" and "AMD endpoint busy" in j["message"] and "job" not in j
    assert _files(env["up"]) == sorted([f"{j['id']}.jpg", f"{j['id']}.json"])


def test_upload_ids_are_validated(env):
    for bad in ["..%2F..%2Fapp%2Fmain", "u123", "uZZZZZZZZZZZZ", "u0123456789ab.."]:
        assert client.get(f"/upload/{bad}.jpg").status_code == 404, bad
        assert client.get(f"/try/{bad}").status_code == 404, bad
    assert client.post("/api/upload/u0123456789ab/read").status_code == 404


def test_try_page_renders_and_is_neutral():
    html = client.get("/try").text
    assert "Take a photo" in html and 'capture="environment"' in html and "Use a sample photo" in html
    assert "What a good photo looks like" in html
    _clean(html, "/try")


# ------------------------------------------------------------------ manual four-corner pick (locator missed the page)
def _photo_with_known_corners():
    """A synthetic 'phone photo': a page whose names-and-signatures column is NOT masked (fake handwriting drawn
    in), warped in perspective onto a cluttered background, with no corner markers the locator could find (they
    are painted over). Returns (jpeg bytes, the four marker centres in photo pixels, in a shuffled order)."""
    import cv2
    import numpy as np
    from twohands import schema as schemamod
    im = Image.open(_masked_page()).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle([int(0.70 * W), int(0.05 * H), int(0.97 * W), int(0.95 * H)], fill=(255, 255, 255))
    for i in range(12):
        y = int((0.1 + 0.07 * i) * H)
        d.line([int(0.72 * W), y, int(0.95 * W), y + 15], fill=(20, 20, 160), width=6)
    mk = np.array(schemamod.load()["layout"]["canonical"]["markers"]) * [W, H]
    for x, y in mk:  # grey the markers: the automatic locator cannot use them
        d.rectangle([x - 40, y - 40, x + 40, y + 40], fill=(150, 150, 150))
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    dst = np.float32([[310, 190], [2690, 400], [2610, 1880], [240, 1720]])
    Hm = cv2.getPerspectiveTransform(src, dst)
    photo = cv2.warpPerspective(np.asarray(im), Hm, (3000, 2200), borderValue=(70, 60, 50))
    pts = cv2.perspectiveTransform(mk.reshape(-1, 1, 2).astype(np.float32), Hm).reshape(-1, 2)
    pts = pts[[2, 0, 3, 1]] + np.float32([[6, -5], [-4, 7], [5, 4], [-6, -3]])  # any order, a few px off
    return _jpeg(Image.fromarray(photo)), [[float(x), float(y)] for x, y in pts]


def test_core_registers_from_given_corners():
    from twohands import corners, register
    raw, pts = _photo_with_known_corners()
    img = uploadmod.decode(raw)
    page, info = corners.prepare(img, pts)
    assert info["locator"] == "manual_corners" and page.size == (2400, 1552)
    col = page.convert("L").crop((int(0.657 * 2400) + 4, 0, 2400, 1552))
    assert max(col.getextrema()) < 40, "the same privacy mask as the locator's"
    ref = Image.open(_masked_page()).convert("L").resize(page.size)
    import numpy as np
    assert np.abs(np.asarray(page.convert("L"), float) - np.asarray(ref, float)).mean() < 20  # lands on the page
    with pytest.raises(register.NotLocated):
        corners.prepare(img, [[1, 1], [2, 2], [3, 3], [4, 4]])
    with pytest.raises(register.NotLocated):
        corners.prepare(img, [[1, 1], [2, 2], [3, 3]])


def test_manual_corners_upload_stores_only_the_masked_page(env, monkeypatch):
    from twohands import mask, register
    raw, pts = _photo_with_known_corners()

    def miss(*a, **k):  # the automatic locator misses this page (its SIFT fallback would otherwise find it)
        raise register.NotLocated("corner markers not found")
    monkeypatch.setattr(mask, "prepare", miss)
    r = client.post("/api/upload", content=raw, headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 422 and r.json()["code"] == "not_located" and r.json()["manual"] is False
    assert _files(env["up"]) == [] and _files(env["tmp"]) == []
    # bad points: nothing stored either
    q = "1,1,2,2,3,3,4,4"
    r = client.post(f"/api/upload?corners={q}", content=raw, headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 422 and r.json()["manual"] is True
    assert client.post("/api/upload?corners=1,2,3", content=raw, headers={"Content-Type": "image/jpeg"}).status_code == 422
    assert _files(env["up"]) == [] and _files(env["tmp"]) == []
    # the clicked corners: registered, masked, only the masked page and its note stored, a live read queued
    q = ",".join(f"{v:.1f}" for p in pts for v in p)
    r = client.post(f"/api/upload?corners={q}", content=raw, headers={"Content-Type": "image/jpeg"})
    assert r.status_code == 200, r.text
    j = r.json()
    uid = j["id"]
    assert j["job"] and j["locator"]["locator"] == "manual_corners"
    assert _files(env["up"]) == sorted([f"{uid}.jpg", f"{uid}.json"]) and _files(env["tmp"]) == []
    for p in env["up"].iterdir():
        assert p.read_bytes() != raw
    saved = Image.open(env["up"] / f"{uid}.jpg").convert("L")
    assert saved.size == (2400, 1552)
    col = saved.crop((int(0.657 * 2400) + 4, 0, 2400, 1552))
    assert max(col.getextrema()) < 40, "no unmasked page is written"
    env["gate"].set()


def test_try_page_has_the_corner_picker():
    html = client.get("/try").text
    assert "Click the four corner markers" in html and "createObjectURL" in html and "corners=" in html
