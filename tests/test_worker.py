"""The live audit worker (twohands/worker.py) and its pages, offline: a mocked INE source and a mocked AMD endpoint.

Ordering, the daily budget guard, the automatic labels, the Merkle receipts, the pause states, that no unmasked image
is ever stored, that no party name appears, and that the worker's numbers stay out of the pre-registered results."""
import io
import json
import re
from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app import live_audit as la
from app.main import app
from twohands import REPO, merkle, schema, verify_receipt
from twohands import worker as W
from twohands.gate import GateResult

S = schema.load()
CAP_KEYS = [f["key"] for f in S["fields"] if f.get("csv")]
CERT_KEYS = S["vote_keys"] + ["TOTAL"]
PARTY = re.compile(r"(?<![A-Za-z0-9])(PAN|PRI|PRD|PVEM|PT|MC|MORENA)(?![A-Za-z0-9])")
PARTY_CI = re.compile(r"(?<![A-Za-z0-9])(morena|pvem|verde)(?![A-Za-z0-9])", re.I)
RED = (255, 0, 0)


# ------------------------------------------------------------------------------------------------ fixtures
def paper_values(seed: int) -> dict:
    """A self-consistent form: vote rows sum to TOTAL, sections agree."""
    votes = {k: (seed * 7 + i * 3) % 40 for i, k in enumerate(S["vote_keys"])}
    tot = sum(votes.values())
    return votes | {"TOTAL": tot, "SACADOS": tot, "VOTARON": tot - 2, "REPRESENTANTES": 2, "PERSONAS_Y_REP": tot,
                    "SOBRANTES": 100 + seed}


def reply(vals: dict) -> dict:
    items = []
    for f in S["fields"]:
        lab = f["label"]
        label = "+".join(lab["parties"]) if "parties" in lab else (f.get("where") or " ".join(lab["keywords"]))
        n = vals[f["key"]]
        items.append({"label": label.split(" ", 2)[-1] if label.startswith("section ") else label, "n": n, "w": n})
    return {"choices": [{"message": {"content": json.dumps({"values": items})}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.003}}


def raw_image() -> bytes:
    """A real (masked) page with the private column painted red: stands in for an unmasked INE photo."""
    im = Image.open(REPO / "data" / "masked" / "060079C0300.jpg").convert("RGB")
    W_, H_ = im.size
    d = ImageDraw.Draw(im)
    for x0, y0, x1, y1 in S["layout"]["mask"]["escaner"]:
        d.rectangle([int(x0 * W_) + 10, int(y0 * H_) + 10, int(x1 * W_) - 10, int(y1 * H_) - 10], fill=RED)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    return buf.getvalue()


RAW = raw_image()


def item(clave, ent, mode, cap, cert):
    return {"clave": clave, "ent": ent, "dist": 1, "layout": "escaner", "mode": mode,
            "cap": [cap[k] for k in CAP_KEYS], "cert": [cert[k] for k in CERT_KEYS] if cert else None}


def make_queue(root, items, states):
    P = W.Paths(root)
    W.save_queue({"built": "t", "schema": S["form"], "states": states, "items": items}, P.queue)
    by = {}
    for it in items:
        by.setdefault((it["ent"], it["dist"]), {})[it["clave"]] = f"https://prep.example.test/{it['clave']}.jpg"
    for (e, d), m in by.items():
        P.urls.mkdir(parents=True, exist_ok=True)
        (P.urls / f"{e}_{d}.json").write_text(json.dumps(m), encoding="utf-8")
    return P


class Endpoint:
    """Mocked AMD endpoint: replies with per-form values; counts calls; /usage and /models are scripted."""

    def __init__(self, answers: dict, used=0.0, remaining=0.9, models=("Qwen3.8-27B",)):
        self.answers, self.calls, self.used, self.remaining, self.models = answers, [], used, remaining, list(models)

    def chat(self, body):
        self.calls.append(body["model"])
        k = self.current
        return reply(self.answers[k]), 1

    def usage(self):
        return {"daily_cost_used_usd": self.used, "daily_cost_remaining_usd": self.remaining,
                "daily_reset_at": "2099-01-01T16:00:00Z"}


class Ine:
    def __init__(self, codes=None):
        self.codes, self.urls = list(codes or []), []

    def get(self, url):
        self.urls.append(url)
        if self.codes:
            c = self.codes.pop(0)
            if c != 200:
                return c, b"", {"Retry-After": "120"}
        return 200, RAW, {}


class Halt(Exception):
    """Raised by the test's sleep: a pause was entered (its status is already written)."""


def halt(_s):
    raise Halt()


def make_worker(root, ep, ine, **kw):
    w = W.Worker(root, chat=None, usage=ep.usage, list_models=lambda: ep.models, http_get=ine.get,
                 sleep=halt, **kw)
    w.source.sleep = lambda s: None
    orig = w.process

    def process(it):
        ep.current = it["clave"]
        return orig(it)
    w.process = process
    w.chat = ep.chat
    return w


@pytest.fixture
def three(tmp_path):
    """Two Colima forms (comparison: one capture error the certified count confirms, one model misread) and one form
    of a larger state (recount)."""
    a, b, c = "060001B0100", "060002B0100", "030001B0100"
    pa, pb, pc = paper_values(1), paper_values(2), paper_values(3)
    k1, k2 = S["vote_keys"][0], S["vote_keys"][3]
    cap_a = dict(pa, **{k1: pa[k1] + 10})                # capture mis-keyed; certified = paper
    cert_a = {k: pa[k] for k in CERT_KEYS}
    read_b = dict(pb, **{k2: pb[k2] + 1, "TOTAL": pb["TOTAL"] + 1, "SACADOS": pb["SACADOS"] + 1,
                         "PERSONAS_Y_REP": pb["PERSONAS_Y_REP"] + 1, "VOTARON": pb["VOTARON"] + 1})
    cert_b = {k: pb[k] for k in CERT_KEYS}               # model misread k2 (and the totals with it)
    cap_c = dict(pc, SOBRANTES=pc["SOBRANTES"] + 5)       # a section the certified count does not cover
    items = [item(c, 3, "recount", cap_c, {k: pc[k] for k in CERT_KEYS}),
             item(b, 6, "comparison", pb, cert_b), item(a, 6, "comparison", cap_a, cert_a)]
    states = {"6": {"name": "Colima", "size": 2, "queue": 2, "measured_skipped": 0},
              "3": {"name": "Baja California Sur", "size": 5, "queue": 1, "measured_skipped": 0}}
    items = W.order_items(items, {6: 2, 3: 5})
    P = make_queue(tmp_path, items, states)
    ep = Endpoint({a: pa, b: read_b, c: pc})
    return {"P": P, "ep": ep, "claves": (a, b, c), "keys": (k1, k2)}


# ------------------------------------------------------------------------------------------------ ordering
def test_order_smallest_state_first_then_comparison_then_clave():
    its = [{"clave": "030002B0100", "ent": 3, "mode": "comparison"}, {"clave": "060009B0100", "ent": 6, "mode": "recount"},
           {"clave": "060005B0100", "ent": 6, "mode": None}, {"clave": "060007B0100", "ent": 6, "mode": "comparison"},
           {"clave": "060001B0100", "ent": 6, "mode": "recount"}, {"clave": "060008B0100", "ent": 6, "mode": "comparison"}]
    out = [i["clave"] for i in W.order_items(its, {6: 1021, 3: 1101})]
    assert out == ["060007B0100", "060008B0100", "060001B0100", "060009B0100", "060005B0100", "030002B0100"]


def test_cert_mode_from_observations():
    assert W.cert_mode("Cotejo (Levantada en Casilla)") == "comparison"
    assert W.cert_mode("Recuento (Para recuento-SRA)") == "recount"
    assert W.cert_mode("Paquete no recibido") is None and W.cert_mode(None) is None


def test_build_queue_skips_measured_forms_and_orders(tmp_path):
    cap_cols = [f["csv"] for f in S["fields"] if f.get("csv")]
    head = ("CLAVE_CASILLA,CLAVE_ACTA,ID_ENTIDAD,ENTIDAD,ID_DISTRITO_FEDERAL,TIPO_ACTA,DIGITALIZACION,TIPO_DOCUMENTO,"
            + ",".join(cap_cols))
    rows = [("'060001B0100'", 6, "COLIMA", "Escáner"), ("'060002B0100'", 6, "COLIMA", "Móvil"),
            ("'060003B0100'", 6, "COLIMA", "Escáner"), ("'030001B0100'", 3, "BAJA CALIFORNIA SUR", "Escáner"),
            ("'030002B0100'", 3, "BAJA CALIFORNIA SUR", "Escáner"), ("'030003B0100'", 3, "BAJA CALIFORNIA SUR", "Escáner")]
    lines = ["PRESIDENCIA", head]
    for k, e, n, dig in rows:
        lines.append(",".join([k, k, str(e), n, "1", "2", dig, "Acta PREP"] + ["5"] * len(cap_cols)))
    lines.append(",".join(["'060004B0100'", "x", "6", "COLIMA", "1", "2", "Escáner", "Acta PREP"] + ["5"] * len(cap_cols)))
    prep = tmp_path / "prep.csv"
    prep.write_text("\n".join(lines), encoding="utf-8")
    ccols = ["CLAVE_CASILLA", "OBSERVACIONES"] + [{"NO_REGISTRADAS": "CANDIDATO/A NO REGISTRADO/A", "NULOS": "VOTOS NULOS",
                                                   "TOTAL": "TOTAL_VOTOS_CALCULADOS"}.get(k, k) for k in CERT_KEYS]
    obs = {"060001B0100": "Recuento (Para recuento-SRA)", "060002B0100": "Cotejo (Levantada en Casilla)",
           "060003B0100": "Cotejo (Levantada en Casilla)", "030001B0100": "Cotejo (Levantada en Casilla)",
           "030002B0100": "Cotejo (Levantada en Casilla)"}
    cl = ["sep=|", "|".join(ccols)] + ["|".join([f"'{k}'", o] + ["5"] * len(CERT_KEYS)) for k, o in obs.items()]
    comp = tmp_path / "comp.csv"
    comp.write_text("\n".join(cl), encoding="utf-8")
    q = W.build_queue(prep, comp, measured={"060003B0100"})
    order = [i["clave"] for i in q["items"]]
    # Colima has 4 presidential rows, BCS 3 -> BCS first; inside: comparison, then recount, then no certified row
    assert order == ["030001B0100", "030002B0100", "030003B0100", "060002B0100", "060001B0100", "060004B0100"]
    assert q["states"]["6"]["measured_skipped"] == 1 and "060003B0100" not in order
    assert q["items"][0]["layout"] == "escaner" and q["items"][3]["layout"] == "movil"
    assert q["items"][2]["cert"] is None and q["items"][2]["mode"] is None


def test_measured_claves_cover_the_pre_registered_sample():
    m = W.measured_claves()
    man = json.loads((REPO / "results" / "manifest.json").read_text(encoding="utf-8"))
    assert {it["clave"] for it in man["items"]} <= m


# ------------------------------------------------------------------------------------------------ labels
def test_labels():
    ck = set(CERT_KEYS)
    k = S["vote_keys"][0]
    assert W.label_for(k, 50, 40, 50, "comparison", ck) == "confirmed"
    assert W.label_for(k, 50, 40, 40, "comparison", ck) == "model_misread"
    assert W.label_for(k, 50, 40, 45, "comparison", ck) == "unconfirmed"
    assert W.label_for(k, 50, 40, 50, "recount", ck) == "unconfirmed"
    assert W.label_for(k, 50, 40, None, "comparison", ck) == "unconfirmed"
    assert W.label_for("TOTAL", 300, 310, 300, "comparison", ck) == "confirmed"
    assert W.label_for("SOBRANTES", 30, 40, None, "comparison", ck) == "unconfirmed"


def test_disputes_need_words_equal_digits_and_aligned_rows():
    k = S["vote_keys"][0]
    g = GateResult(accepted=True, values={k: 50}, words={k: 50})
    assert [d["label"] for d in W.disputes_of(g, {k: 40}, {k: 50}, "comparison", S)] == ["confirmed"]
    g2 = GateResult(accepted=False, values={k: 50}, words={k: 51})
    assert W.disputes_of(g2, {k: 40}, {k: 50}, "comparison", S) == []
    g3 = GateResult(accepted=False, codes=["label"], values={k: 50}, words={k: 50})
    assert W.disputes_of(g3, {k: 40}, {k: 50}, "comparison", S) == []


# ------------------------------------------------------------------------------------------------ the run
def test_run_labels_receipts_and_state(three, monkeypatch):
    P, ep = three["P"], three["ep"]
    a, b, c = three["claves"]
    ine = Ine()
    w = make_worker(P.root, ep, ine)
    assert w.run() == 3
    rows = W.read_jsonl(P.results)
    assert [r["clave"] for r in rows] == [a, b, c]                     # Colima (smaller) first, then by clave
    assert all(r["reader"] == "Qwen3.8-27B" for r in rows)            # Gemma not listed -> Qwen, recorded
    by = {r["clave"]: r for r in rows}
    da = by[a]["disputes"]
    assert [(d["code"], d["label"]) for d in da] == [("OPT01", "confirmed")]
    assert da[0]["paper"] != da[0]["capture"] and da[0]["certified"] == da[0]["paper"]
    labs = {d["code"]: d["label"] for d in by[b]["disputes"]}
    assert labs["OPT04"] == "model_misread" and labs["TOTAL"] == "model_misread"
    assert labs["VOTARON"] == "unconfirmed"
    assert [d["label"] for d in by[c]["disputes"]] == ["unconfirmed"]  # SOBRANTES on a recounted form
    # polite: one request per image, named User-Agent constant
    assert len(ine.urls) == 3 and W.USER_AGENT == "two-hands-audit (contact: see README)"
    # receipts: one root per state; Colima complete
    roots = json.loads(P.roots.read_text(encoding="utf-8"))
    assert roots["6"]["complete"] and roots["6"]["leaves"] == len(by[a]["disputes"]) + len(by[b]["disputes"])
    monkeypatch.setattr(W, "WORKER_DIR", P.root)
    rc = la.receipt(a, "OPT01")
    assert rc["root"] == roots["6"]["root"] and rc["root_kind"] == "final"
    assert rc["leaf"]["reader"] == "Qwen3.8-27B" and rc["leaf"]["tier"] == "confirmed"
    crop = (P.crops / f"{a}__OPT01.jpg").read_bytes()
    assert all(ok for _, ok, _ in verify_receipt.check(rc, crop, roots["6"]["root"]))
    tampered = dict(rc, leaf=dict(rc["leaf"], keyed=rc["leaf"]["keyed"] + 1))
    assert not all(ok for _, ok, _ in verify_receipt.check(tampered))
    st = json.loads(P.state.read_text(encoding="utf-8"))
    assert st["status"] == "complete"


def test_switches_to_gemma_when_listed_again(three):
    P, ep = three["P"], three["ep"]
    ep.models = ["Gemma-4-31B-IT", "Qwen3.8-27B"]
    w = make_worker(P.root, ep, Ine())
    w.run(limit=1)
    assert ep.calls == ["Gemma-4-31B-IT"] and W.read_jsonl(P.results)[0]["reader"] == "Gemma-4-31B-IT"


def test_resumes_after_a_crash_mid_write(three):
    P, ep = three["P"], three["ep"]
    make_worker(P.root, ep, Ine()).run(limit=1)
    with open(P.results, "ab") as fh:
        fh.write(b'{"clave": "060001B0100", "status": "aud')     # killed mid-line
    ep.calls.clear()
    w2 = make_worker(P.root, ep, Ine())
    assert len(w2.rows) == 1
    w2.run()
    rows = W.read_jsonl(P.results)
    assert len(rows) == 3 and len({r["clave"] for r in rows}) == 3 and len(ep.calls) == 2


# ------------------------------------------------------------------------------------------------ budget
def test_budget_guard_trips_on_cap_reserve_and_own_spend():
    now = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
    reset = datetime(2026, 10, 16, 16, 3, tzinfo=timezone.utc).timestamp()
    ok = W.Budget(lambda: {"daily_cost_used_usd": 0.30, "daily_cost_remaining_usd": 0.70}, now=lambda: now)
    ok.check()
    for u, own in (({"daily_cost_used_usd": 0.60, "daily_cost_remaining_usd": 0.40}, 0.0),   # the key's spend cap
                   ({"daily_cost_used_usd": 0.10, "daily_cost_remaining_usd": 0.205}, 0.0),  # the live-read reserve
                   ({}, 0.60)):                                                            # /usage down: own spend
        b = W.Budget(lambda u=u: u, own_today=lambda own=own: own, now=lambda: now)
        with pytest.raises(W.BudgetPaused) as e:
            b.check()
        assert e.value.until == reset
    late = datetime(2026, 10, 16, 17, 0, tzinfo=timezone.utc)
    b = W.Budget(lambda: {"daily_cost_used_usd": 0.7}, now=lambda: late)
    with pytest.raises(W.BudgetPaused) as e:
        b.check()
    assert e.value.until == datetime(2026, 10, 17, 16, 3, tzinfo=timezone.utc).timestamp()
    assert W.budget_day(datetime(2026, 10, 16, 15, 59, tzinfo=timezone.utc)) == "2026-10-15"
    assert W.budget_day(datetime(2026, 10, 16, 16, 0, tzinfo=timezone.utc)) == "2026-10-16"


def test_budget_pause_stops_reads_and_shows_on_live(three, monkeypatch):
    P, ep = three["P"], three["ep"]
    ep.used = 0.65
    w = make_worker(P.root, ep, Ine())
    with pytest.raises(Halt):
        w.run(max_steps=1)
    assert ep.calls == [] and not P.results.exists()
    assert not list(P.pages.glob("*.jpg")) if P.pages.exists() else True   # nothing kept for an unread form
    st = json.loads(P.state.read_text(encoding="utf-8"))
    assert st["pause"] == "budget" and st["pause_text"] == "Paused: daily AMD budget reached; resumes 16:00 UTC"
    # with one audited form, the page shows the pause
    ep.used = 0.0
    make_worker(P.root, ep, Ine()).run(limit=1)
    ep.used = 0.65
    with pytest.raises(Halt):
        make_worker(P.root, ep, Ine()).run(max_steps=1)
    monkeypatch.setattr(W, "WORKER_DIR", P.root)
    html = TestClient(app).get("/live").text
    assert "Paused: daily AMD budget reached; resumes 16:00 UTC" in html


def test_live_reads_and_worker_share_one_rate_limiter():
    from app import live
    from twohands import amd, ratelimit
    assert "shared()" in open(amd.__file__, encoding="utf-8").read()          # every chat goes through shared()
    assert "amd.chat" in open(live.__file__, encoding="utf-8").read()
    assert "amd.chat" in open(W.__file__, encoding="utf-8").read()
    assert isinstance(ratelimit.shared(), ratelimit.FileRateLimiter)          # cross-process: one file for all


# ------------------------------------------------------------------------------------------------ source pauses
def test_source_429_pauses_the_source_and_survives_restart(three, monkeypatch):
    P, ep = three["P"], three["ep"]
    t = {"now": 1000.0}
    ine = Ine(codes=[429])
    w = make_worker(P.root, ep, ine)
    w.source.clock = lambda: t["now"]
    w.clock = lambda: t["now"]
    with pytest.raises(Halt):
        w.run(max_steps=1)
    st = json.loads(P.state.read_text(encoding="utf-8"))
    assert st["pause"] == "source" and st["pause_text"] == "Paused: source unavailable"
    assert ep.calls == [] and len(ine.urls) == 1
    src = json.loads(P.sources.read_text(encoding="utf-8"))
    assert src["paused_until"] >= 1000.0 + 1800.0
    # a restarted worker keeps the pause and does not touch the source
    w2 = make_worker(P.root, ep, ine)
    w2.source.clock = lambda: t["now"] + 60
    with pytest.raises(W.SourcePaused):
        w2.source.fetch("https://prep.example.test/x.jpg")
    assert len(ine.urls) == 1


def test_source_is_polite_one_request_per_second_and_retries():
    waits, now = [], {"t": 0.0}

    def sleep(s):
        waits.append(s)
        now["t"] += s
    calls = []

    def get(url):
        calls.append(now["t"])
        return (503, b"", {}) if len(calls) < 3 else (200, b"img", {})
    import tempfile, pathlib
    src = W.Source(pathlib.Path(tempfile.mkdtemp()) / "s.json", get=get, clock=lambda: now["t"], sleep=sleep,
                   interval_s=0.2)
    assert src.interval_s == 1.0                          # never faster than one request per second
    assert src.fetch("u") == b"img"
    assert all(b - a >= 1.0 for a, b in zip(calls, calls[1:]))
    src.fetch("u2")
    assert calls[-1] - calls[-2] >= 1.0
    src2 = W.Source(pathlib.Path(tempfile.mkdtemp()) / "s.json", get=lambda u: (403, b"", {}), clock=lambda: now["t"],
                    sleep=sleep)
    with pytest.raises(W.SourcePaused):
        src2.fetch("u")


def test_endpoint_down_pauses_without_writing_a_row(three):
    P, ep = three["P"], three["ep"]
    w = make_worker(P.root, ep, Ine())

    def down(body):
        raise RuntimeError("HTTP 503")
    w.chat = down
    with pytest.raises(Halt):
        w.run(max_steps=1)
    st = json.loads(P.state.read_text(encoding="utf-8"))
    assert st["pause"] == "endpoint" and not P.results.exists()


# ------------------------------------------------------------------------------------------------ privacy
def _red(im):
    a = np.asarray(im.convert("RGB")).astype(int)
    return int(((a[..., 0] > 180) & (a[..., 1] < 80) & (a[..., 2] < 80)).sum())


def test_no_unmasked_image_is_ever_stored(three):
    P, ep = three["P"], three["ep"]
    assert _red(Image.open(io.BytesIO(RAW))) > 10000            # the stand-in raw image has its private column
    make_worker(P.root, ep, Ine(), page_kb=150).run()
    files = [p for p in P.root.rglob("*") if p.is_file()]
    for p in files:
        assert RAW[:4096] not in p.read_bytes()                  # the raw bytes are nowhere on disk
        assert p.suffix in (".jsonl", ".json", ".gz", ".jpg", ".log") or p.name.endswith(".lock"), p
    pages = list(P.pages.glob("*.jpg"))
    assert len(pages) == 3
    for p in pages:
        assert p.stat().st_size <= 150 * 1024
        im = Image.open(p)
        x0 = S["layout"]["mask"]["escaner"][0][0]
        W_, H_ = im.size
        right = im.crop((int(x0 * W_) + 4, 0, W_, H_))
        assert _red(right) == 0 and np.asarray(right.convert("L")).mean() < 12   # blacked out
    for p in P.crops.glob("*.jpg"):
        assert _red(Image.open(p)) == 0


def test_disk_cap_stops_storing_pages(three):
    P, ep = three["P"], three["ep"]
    make_worker(P.root, ep, Ine(), disk_cap_mb=0.0001).run()
    rows = W.read_jsonl(P.results)
    assert len(rows) == 3 and all(r["page"] is None for r in rows) and not list(P.pages.glob("*.jpg"))


# ------------------------------------------------------------------------------------------------ pages
def test_live_page_numbers_and_neutrality(three, monkeypatch):
    P, ep = three["P"], three["ep"]
    make_worker(P.root, ep, Ine()).run()
    monkeypatch.setattr(W, "WORKER_DIR", P.root)
    c = TestClient(app)
    html = c.get("/live").text
    for t in ("forms audited on AMD so far", "disputes", "confirmed by the certified count", "Colima: complete",
              "Not an official INE product; the certified count is the official result", "Latest receipt",
              "Qwen3.8-27B", "/about-data"):
        assert t in html, t
    main = html.split("<footer")[0].lower()             # the site footer is shared by every page
    assert "errors found" not in main and "fraud" not in main
    st = c.get("/api/live-audit/status").json()
    assert st["audited"] == 3 and st["confirmed"] == 1
    a = three["claves"][0]
    assert c.get(f"/live/crop/{a}/OPT01.jpg").status_code == 200
    assert c.get("/live/crop/..%2F..%2Fx/OPT01.jpg").status_code == 404
    rc = c.get(f"/api/live-audit/receipt/{a}/OPT01").json()
    home = c.get("/").text
    from jinja2 import Environment, FileSystemLoader       # the includable block renders the three numbers
    env = Environment(loader=FileSystemLoader(str(REPO / "templates")))
    env.globals["live_audit_block"] = la.block
    block = env.get_template("_live_audit_block.html").render()
    assert "Live audit on AMD" in block and "confirmed by the certified count" in block
    about = c.get("/about-data").text
    for text, where in ((html.split("<footer")[0], "/live"), (json.dumps(st), "status"), (json.dumps(rc), "receipt"),
                        (about.split("<footer")[0], "about"), (block, "overview block"), (P.results.read_text(encoding="utf-8"), "results.jsonl"),
                        (P.disputes.read_text(encoding="utf-8"), "disputes.jsonl")):
        m = PARTY.search(text) or PARTY_CI.search(text)
        assert m is None, (where, text[max(0, m.start() - 60):m.end() + 60])
        assert PARTY.search(home) is None
        assert "fraud" not in text.lower() and "errors found" not in text.lower()
    for t in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", html + about, flags=re.S):
        assert "election" not in t.lower()


def test_live_page_before_any_row(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "WORKER_DIR", tmp_path)
    c = TestClient(app)
    html = c.get("/live").text
    assert "Not started yet" in html and "the certified count is the official result" in html
    assert c.get("/api/live-audit/status").json()["audited"] == 0
    assert 'class="la-block"' not in c.get("/").text


# ------------------------------------------------------------------------------------------------ separation
def test_worker_numbers_never_feed_the_pre_registered_results():
    ev = (REPO / "twohands" / "eval.py").read_text(encoding="utf-8")
    assert "live_audit" not in ev and "twohands.worker" not in ev
    src = (REPO / "twohands" / "worker.py").read_text(encoding="utf-8")
    assert 'REPO / "results" /' not in src and "RESULTS" not in src
    assert W.WORKER_DIR.name == "live_audit" or W.WORKER_DIR != REPO / "results"


def test_watchdog_and_healthcheck(tmp_path):
    P = W.Paths(tmp_path)
    assert W.main(["check", "--dir", str(tmp_path)]) == 1
    P.heartbeat.write_text(json.dumps({"t": __import__("time").time()}), encoding="utf-8")
    assert W.main(["check", "--dir", str(tmp_path)]) == 0
    assert W.acquire_lock(P) and not W.acquire_lock(P)
    W.release_lock(P)
    assert W.acquire_lock(P)
    W.release_lock(P)


def test_merkle_accepts_exactly_the_two_leaf_shapes():
    r = merkle.leaf_record_live("060001B0100", "OPT01", 1, 2, 2, "confirmed", None, "Qwen3.8-27B", 2)
    merkle.leaf_hash(r)
    with pytest.raises(ValueError):
        merkle.leaf_hash({**r, "extra": 1})
    with pytest.raises(ValueError):
        merkle.leaf_hash({k: v for k, v in r.items() if k != "certified"})
