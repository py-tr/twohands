"""Audit your capture (/audit/new, app/capture_audit.py): column auto-mapping, dispute order, the sample audit
reproducing the 267 disputes of results/adjudication, the auditor's marks and exports, live reads for forms without
one (mocked reader, no request reaches AMD), and a ZIP of scans that stores only masked pages."""
import csv
import io
import json
import tempfile
import zipfile

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app import capture_audit as ca
from app import live as livemod
from app import store as storemod
from app.main import app
from tests.test_app_live import drain
from tests.test_app_neutral import _clean

client = TestClient(app)
ADJ = storemod.RESULTS / "adjudication"


@pytest.fixture(autouse=True)
def audits(tmp_path, monkeypatch):
    monkeypatch.setattr(ca, "AUDITS", tmp_path / "audits")
    return tmp_path / "audits"


def _sample_headers():
    with ca.SAMPLE_CSV.open(encoding="utf-8") as f:
        return next(csv.reader(f))


# ------------------------------------------------------------------ column auto-mapping
def test_automap_detects_every_ine_prep_column():
    h = _sample_headers()
    m = ca.automap(h)
    assert h[m["id"]] == "CLAVE_CASILLA"
    assert all(v is not None for v in m["fields"].values()) and len(m["fields"]) == 22
    assert set(m["how"].values()) == {"INE PREP column"}
    assert h[m["fields"]["OPT08"]] == "PAN-PRI-PRD" and h[m["fields"]["TOTAL"]] == "TOTAL_VOTOS_ASENTADO"
    assert h[m["fields"]["SOBRANTES"]] == "TOTAL_BOLETAS_SOBRANTES"


def test_automap_site_names_spacing_and_the_computed_total_is_not_the_keyed_total():
    h = ["form_id", "Option 01", "opt02", "Unused ballots", "pan - pri - prd", "TOTAL_VOTOS_CALCULADOS", "notes"]
    m = ca.automap(h)
    assert m["id"] == 0
    assert m["fields"]["OPT01"] == 1 and m["fields"]["OPT02"] == 2 and m["fields"]["SOBRANTES"] == 3
    assert m["fields"]["OPT08"] == 4                       # INE name with other separators
    assert m["fields"]["TOTAL"] is None                    # the computed total is not what was keyed
    assert m["fields"]["NULOS"] is None


def test_parse_csv_with_ine_preamble_pipes_and_quoted_ids():
    text = ("PRESIDENCIA 2024\nfecha: 2024-06-03\n"
            "CLAVE_CASILLA|PAN|TOTAL_VOTOS_ASENTADO\n'010469C0400'|51|408\n'010477C0300'|Ilegible|400\n")
    h, rows = ca.parse_csv(text)
    assert h == ["CLAVE_CASILLA", "PAN", "TOTAL_VOTOS_ASENTADO"] and len(rows) == 2
    m = ca.automap(h)
    assert m["fields"]["OPT01"] == 1 and m["fields"]["TOTAL"] == 2
    assert ca.keyed_value("Ilegible") == (None, "illegible") and ca.keyed_value("Sin dato") == (None, "no_data")
    assert ca.keyed_value("1,204") == (1204, "number") and ca.keyed_value("") == (None, "blank")


def test_column_names_are_shown_neutrally():
    for h in _sample_headers():
        _clean(ca.display_header(h), h)
    assert ca.display_header("PAN") == "Option 01 (INE)"


# ------------------------------------------------------------------ order
def _view(**over):
    s = storemod.schema()
    vals = {k: 0 for k in s["keys"]}
    vals.update({"PAN": 100, "PRI": 50, "TOTAL": 150, "VOTARON": 148, "REPRESENTANTES": 2, "PERSONAS_Y_REP": 150,
                 "SACADOS": 150, "SOBRANTES": 200})
    vals.update(over)
    return ca.View(vals, dict(vals), True, "test", None)


def test_ranking_strong_when_words_agree_and_keyed_value_breaks_an_identity():
    ev = ca.evidence("PAN", 10, "number", _view())
    assert ev["tier"] == "strong" and ev["score"] >= 6
    assert any("breaks rows sum to TOTAL" in s["text"] for s in ev["signals"])


def test_ranking_weak_when_model_saw_blank_against_a_keyed_zero_and_when_model_breaks_the_sum():
    v = _view(PRD=None)
    v.words["PRD"] = None
    weak = ca.evidence("PRD", 0, "number", v)
    assert weak["tier"] == "weak"
    v2 = _view(PAN=110)                      # model read 110, the keyed 100 satisfies the sum, the model's does not
    v2.words["PAN"] = 101
    bad = ca.evidence("PAN", 100, "number", v2)
    assert bad["tier"] == "weak" and any("the model's breaks it" in s["text"] for s in bad["signals"])
    assert ca.evidence("PAN", 10, "number", _view())["score"] > bad["score"] > -99


def test_disputes_are_sorted_by_evidence():
    R = ca.run(ca.sample())
    sc = [d["score"] for d in R["disputes"]]
    assert sc == sorted(sc, reverse=True)
    assert [d["pos"] for d in R["disputes"]] == list(range(1, len(sc) + 1))
    tiers = [d["tier"] for d in R["disputes"]]
    assert tiers.index("weak") > tiers.index("medium") > tiers.index("strong") == 0


# ------------------------------------------------------------------ the sample audit reproduces 267
def test_sample_audit_reproduces_the_adjudicated_267():
    j = client.post("/api/audit/sample").json()
    a = ca.load(j["id"])
    R = ca.run(a)
    V = json.loads((ADJ / "verdicts.json").read_text(encoding="utf-8"))
    H = json.loads((storemod.DATA / "headline.json").read_text(encoding="utf-8"))
    assert R["forms_keyed"] == 300 and R["forms_read"] == H["read"] == 289
    assert R["checked"] == H["fields"] == 6358
    assert R["disputed"] == H["disagree"] == len(V) == 267
    got = {f"{d['form']}__{storemod.key_of(d['code'])}" for d in R["disputes"]}
    assert got == set(V)
    assert R["adjudicated"] == 267
    assert sum(t["errors"] for t in R["order_check"]) == H["keying_errors"] == 52
    assert len(R["unread"]) == 11 and not any(p["queueable"] for p in R["unread"])
    assert {p["form"] for p in R["unread"]} == set(H["unread_claves"])


def test_audit_pages_marks_and_exports(audits):
    aid = client.post("/api/audit/sample").json()["id"]
    html = client.get(f"/audit/{aid}").text
    assert "267 disputed fields in 6,358 checked" in html and html.count('data-mark="confirmed"') == 267
    assert "label=0" in html  # crops start right of the printed row label: no logo
    k = "080310B0100__SOBRANTES"
    assert client.post(f"/api/audit/{aid}/mark", json={"key": k, "mark": "confirmed"}).json()["mark"] == "confirmed"
    assert client.post(f"/api/audit/{aid}/mark", json={"key": k, "mark": "bogus"}).status_code == 422
    rep = client.get(f"/audit/{aid}/report").text
    assert "<title>Audit report: 6,358 fields checked, 267 disputed</title>" in rep
    assert "each with its photo" in rep and "1 in 5" in rep and "52 of those 267" in rep
    assert "Recall caveat" in rep and "not total recall" in rep and "Confirmed capture error" in rep
    rows = [r for r in csv.DictReader(io.StringIO(client.get(f"/audit/{aid}/report.csv").text))
            if not r["position"].startswith("#")]  # the report fingerprint and input hashes close the file
    assert len(rows) == 267 and rows[0]["position"] == "1"
    assert sum(r["auditor mark"] == "Confirmed capture error" for r in rows) == 1
    assert client.get("/audit/aZZZ/report").status_code == 404 and client.get("/audit/a0123456789ab").status_code == 404


def test_upload_csv_proposes_a_mapping_and_runs():
    body = ca.SAMPLE_CSV.read_bytes()
    j = client.post("/api/audit?name=prep.csv", content=body, headers={"Content-Type": "text/csv"}).json()
    assert j["rows"] == 300 and len(j["how"]) == 22
    _clean(json.dumps(j), "proposal")
    fields = dict(j["mapping"])
    fields["TOTAL"] = None                   # the auditor un-maps one field
    r = client.post(f"/api/audit/{j['id']}/mapping", json={"id_col": j["id_col"], "fields": fields})
    assert r.status_code == 200
    R = ca.run(ca.load(j["id"]))
    assert R["fields_mapped"] == 21 and R["checked"] == 289 * 21 and not any(d["code"] == "TOTAL" for d in R["disputes"])
    bad = client.post(f"/api/audit/{j['id']}/mapping", json={"id_col": j["id_col"], "fields": {}})
    assert bad.status_code == 422
    assert client.post("/api/audit", content=b"just one line", headers={"Content-Type": "text/csv"}).status_code == 422


# ------------------------------------------------------------------ live reads for forms without one
def test_forms_without_a_read_queue_through_the_live_path(tmp_path, monkeypatch):
    s = storemod.get_store()
    have = set(ca.stored_reads()) | set(s.live)
    fid = next((p.stem for p in sorted(storemod.MASKED.rglob("*.jpg")) if p.stem not in have), None)
    if fid is None:
        pytest.skip("every masked page has a read")
    monkeypatch.setattr(livemod, "BUDGET_FILE", tmp_path / "budget.json")
    src = s.runs["spike-gemma-v2"]["reads"]["211294C0100"]
    items = [{"label": None, "n": src.values[f["key"]], "w": src.words[f["key"]]} for f in storemod.schema()["fields"]]
    pages = []
    m = livemod.LiveManager(reader_fn=lambda model, page: pages.append(page) or {"parsed": {"values": items}, "secs": 1.0,
                                                                               "usage": {"cost": 0.0001}},
                            usage_fn=lambda: {"daily_cost_remaining_usd": 0.9}, reveal_delay=0)
    old = app.state.live
    app.state.live = m
    try:
        a = ca.create(f"form_id,PAN,TOTAL_VOTOS_ASENTADO\n{fid},1,2\n")
        ca.set_mapping(a, 0, a["mapping"])
        R = ca.run(a)
        assert R["forms_read"] == 0 and R["unread"][0]["queueable"]
        j = client.post(f"/api/audit/{a['id']}/read").json()
        assert j["queued"] == [fid] and j["refused"] is None
        drain(m)
        assert pages and str(pages[0]).startswith(str(storemod.MASKED))         # only a masked page is sent
        assert (ca.adir(a["id"]) / "reads" / f"{fid}.read.json").is_file()
        R = ca.run(ca.load(a["id"]))
        assert R["forms_read"] == 1 and R["checked"] == 2 and R["disputed"] == 2
        assert client.post(f"/api/audit/{a['id']}/read").json()["queued"] == []  # read once
    finally:
        app.state.live = old


# ------------------------------------------------------------------ ZIP of scans: only masked pages are stored
def _jpeg(im):
    b = io.BytesIO()
    im.convert("RGB").save(b, "JPEG", quality=92)
    return b.getvalue()


def test_zip_of_scans_stores_only_masked_pages(audits, tmp_path, monkeypatch):
    p = storemod.get_store().masked_image("211294C0100")
    if p is None:
        pytest.skip("no masked page")
    tmpd = tmp_path / "tmp"
    tmpd.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmpd))
    im = Image.open(p).convert("RGB")
    W, H = im.size
    d = ImageDraw.Draw(im)
    d.rectangle([int(0.70 * W), int(0.05 * H), int(0.97 * W), int(0.95 * H)], fill=(255, 255, 255))
    for i in range(12):  # fake handwriting in the private column
        y = int((0.1 + 0.07 * i) * H)
        d.line([int(0.72 * W), y, int(0.95 * W), y + 15], fill=(20, 20, 160), width=6)
    raw = _jpeg(im)
    blank = _jpeg(Image.new("RGB", (1600, 1200), (250, 250, 250)))
    z = io.BytesIO()
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("scans/FORMA1.jpg", raw)
        zf.writestr("scans/FORMB2.jpg", blank)         # cannot be located: nothing stored
        zf.writestr("scans/OTHER.jpg", raw)            # not in the keyed file: not even opened
        zf.writestr("readme.txt", b"hello")
    a = ca.create("CLAVE_CASILLA,PAN,TOTAL_VOTOS_ASENTADO\nFORMA1,61,262\nFORMB2,1,1\n")
    client.post(f"/api/audit/{a['id']}/mapping", json={"id_col": 0, "fields": a["mapping"], "scans": "zip"})
    r = client.post(f"/api/audit/{a['id']}/scans", content=z.getvalue(), headers={"Content-Type": "application/zip"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["masked"] == 1 and j["not_located"] == 1 and j["unmatched"] == 1
    files = sorted(str(x.relative_to(audits / a["id"])).replace("\\", "/") for x in (audits / a["id"]).rglob("*") if x.is_file())
    assert files == ["audit.json", "keyed.csv", "pages/FORMA1.jpg"]
    assert list(tmpd.iterdir()) == []
    for x in (audits / a["id"]).rglob("*"):
        if x.is_file():
            assert x.read_bytes() != raw and raw[:4096] not in x.read_bytes()
    saved = Image.open(audits / a["id"] / "pages" / "FORMA1.jpg").convert("L")
    sw, sh = saved.size
    assert max(saved.crop((int(0.657 * sw) + 4, 0, sw, sh)).getextrema()) < 40, "names column must be black"
    # the audit's own crop route serves crops of that masked page only
    assert client.get(f"/audit/{a['id']}/crop/FORMA1/TOTAL.jpg").status_code == 200
    assert client.get(f"/audit/{a['id']}/crop/FORMB2/TOTAL.jpg").status_code == 404
    assert client.get(f"/audit/{a['id']}/crop/FORMA1/PAN.jpg").status_code == 404
    R = ca.run(ca.load(a["id"]))
    pend = {x["form"]: x for x in R["unread"]}
    assert pend["FORMA1"]["queueable"] and not pend["FORMB2"]["queueable"]
    bad = client.post(f"/api/audit/{a['id']}/scans", content=b"not a zip", headers={"Content-Type": "application/zip"})
    assert bad.status_code == 422
