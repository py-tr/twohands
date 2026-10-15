"""Be the second keyer (/keyer): 5 fields drawn from the adjudicated set (2 or 3 real capture errors, the rest easy),
keyed blind from masked crops; the reveal shows per field the visitor's value, the official capture, the model's read
and the gate's verdict, and the photo-based truth, and ends with a one-line score. Nothing is stored; /check (the
person's spot-check) is unchanged."""
import re

from fastapi.testclient import TestClient

from app import keyer
from app import spotcheck as sc
from app.main import app

client = TestClient(app)


def test_draw_mixes_capture_errors_and_easy_fields_deterministically():
    V = sc.load_verdicts()
    seen = set()
    for s in range(1, 60):
        items = keyer.draw(s)
        assert items == keyer.draw(s) and len(items) == 5 == len(set(items))
        errs = sum(V[k]["verdict"] == "model_right" for k in items)
        assert errs in (2, 3)
        assert all(V[k]["verdict"] in ("model_right", "capture_right") and isinstance(V[k]["paper"], int) for k in items)
        seen.add(tuple(items))
    assert len(seen) > 50  # random across rounds


def test_keyer_page_is_blind():
    r = client.get("/keyer", follow_redirects=False)
    assert r.status_code == 302 and re.match(r"^/keyer\?s=\d+$", r.headers["location"])
    html = client.get("/keyer?s=7").text
    items = keyer.draw(7)
    V = sc.load_verdicts()
    assert html.count('name="a"') == 5 and 'action="/keyer/reveal"' in html
    for j, k in enumerate(items):
        clave = k.split("__")[0]
        assert clave not in html  # neither the form ...
        assert f"/keyer/img/7/{j}.jpg" in html  # the crop URL names the round and slot only
        assert V[k]["evidence"] not in html
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
    for word in ("Official capture", "Routed to a person", "model_right", "capture_right", "PREP keyed"):
        assert word not in body  # ... nor any capture, model or verdict before the reveal
    for j in range(5):
        r = client.get(f"/keyer/img/7/{j}.jpg")
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
        assert r.content == sc._crop_path(items[j]).read_bytes()  # the adjudication crop, cut from the masked page
    assert client.get("/keyer/img/7/5.jpg").status_code == 404
    assert client.get("/keyer/img/abc/0.jpg").status_code == 404 and client.get("/keyer?s=-3").status_code == 404


def test_reveal_scores_against_the_paper():
    s = 11
    items = keyer.draw(s)
    V = sc.load_verdicts()
    led = sc.load_ledger()
    papers = [str(V[k]["paper"]) for k in items]
    answers = papers[:3] + ["99999", "?"]
    R = keyer.reveal(s, answers)
    S = R["score"]
    assert S["you"] == 3 and S["n"] == 5
    assert S["official"] == sum(led[k]["prep"] == V[k]["paper"] for k in items)
    assert S["official"] == sum(V[k]["verdict"] == "capture_right" for k in items)  # capture errors are the misses
    assert S["accepted"] == sum(bool(led[k]["form_accepted"]) for k in items) and S["accepted"] + S["routed"] == 5
    assert S["line"] == (f"You matched the paper on 3 of 5; the official capture matched on {S['official']}; the model "
                         f"plus the paper's arithmetic accepted {S['accepted']} and routed {S['routed']} to a person.")
    for row, k in zip(R["rows"], items):
        assert row["paper"] == V[k]["paper"] and row["model_n"] == led[k]["model_n"]
    assert R["rows"][4]["you_raw"] == "can't tell" and not R["rows"][4]["you_ok"]
    q = "&".join(f"a={x}" for x in ["%3F" if a == "?" else a for a in answers])
    html = client.get(f"/keyer/reveal?s={s}&{q}").text
    assert S["line"].replace("'", "&#39;") in html
    for word in ("Official capture", "Model read", "Gate", "The paper, from the photo", "Play another five"):
        assert word in html
    assert html.count('class="crop"') == 5
    # blank and missing answers are fine
    assert client.get(f"/keyer/reveal?s={s}&a=b").status_code == 200
    assert client.get(f"/keyer/reveal?s={s}").status_code == 200


def test_overview_links_the_keyer_and_check_is_unchanged():
    assert 'href="/keyer"' in client.get("/").text and "Try being the second keyer" in client.get("/").text
    html = client.get("/check?i=0").text
    assert "Spot check" in html and "/check/img/0.jpg" in html and "keyer" not in html
