"""Pick any polling station: /station.

Search by station id (clave) with autocomplete, or pick state -> district -> station. For a form we have (a measured
sample, the live audit's audited forms, a staged masked page) the answer is instant: the masked page and its receipts.
For any other form in the live audit's queue: "not audited yet", with a button that puts it at the front of the
worker's queue (<worker dir>/priority.json; the worker reads it, under its own budget guard) and shows its place.

Masked images only; vote rows as Option NN; nothing is totalled across forms.
"""
from __future__ import annotations

import bisect
import gzip
import json
import re
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from app import store as storemod
from twohands import REPO

router = APIRouter()
INDEX = REPO / "app" / "data" / "stations.json.gz"
CLAVE = re.compile(r"^[0-9]{6}[A-Z][0-9]{4}$")
MAX_PENDING = 50          # at most this many station requests wait at the front of the worker's queue
_lock = threading.Lock()


# ------------------------------------------------------------------------------------------------ index
@lru_cache(maxsize=1)
def index() -> dict:
    try:
        return json.loads(gzip.decompress(INDEX.read_bytes()).decode("utf-8"))
    except (OSError, ValueError, EOFError):
        return {"n": 0, "states": {}}


@lru_cache(maxsize=1)
def _flat() -> tuple[list[str], dict]:
    keys, where = [], {}
    for e, s in index()["states"].items():
        for d, dd in s["d"].items():
            for k in dd["c"]:
                keys.append(k)
                where[k] = (e, d)
    keys.sort()
    return keys, where


def state_name(clave: str) -> Optional[str]:
    s = index()["states"].get(str(int(clave[:2]))) if clave[:2].isdigit() else None
    return s["name"] if s else None


def locate(clave: str) -> Optional[dict]:
    w = _flat()[1].get(clave)
    if w is None:
        return None
    s = index()["states"][w[0]]
    return {"ent": w[0], "state": s["name"], "dist": w[1], "district": s["d"][w[1]]["name"]}


def search(q: str, limit: int = 12) -> list[str]:
    q = re.sub(r"[^0-9A-Za-z]", "", q or "").upper()
    if not q:
        return []
    keys = _flat()[0]
    i = bisect.bisect_left(keys, q)
    out = []
    while i < len(keys) and keys[i].startswith(q) and len(out) < limit:
        out.append(keys[i])
        i += 1
    return out


# ------------------------------------------------------------------------------------------------ the worker
def _worker():
    from twohands import worker as W
    return W


def worker_paths():
    W = _worker()
    return W.Paths(W.WORKER_DIR)


def priority_file() -> Path:
    return worker_paths().root / "priority.json"


def read_priority() -> list[dict]:
    try:
        d = json.loads(priority_file().read_text(encoding="utf-8"))
        return [x for x in d.get("items", []) if isinstance(x, dict) and CLAVE.match(str(x.get("clave", "")))]
    except (OSError, ValueError, AttributeError):
        return []


@lru_cache(maxsize=2)
def _queue_claves(path: str, mtime: float) -> frozenset:
    q = _worker().load_queue(Path(path))
    return frozenset(it["clave"] for it in (q or {}).get("items", []))


def in_worker_queue(clave: str) -> bool:
    p = worker_paths().queue
    try:
        mt = p.stat().st_mtime
    except OSError:
        return False
    return clave in _queue_claves(str(p), mt)


@lru_cache(maxsize=4)
def _live_rows(path: str, mtime: float, size: int) -> dict:
    W = _worker()
    out = {}
    for r in W.read_jsonl(Path(path)):
        if r.get("status") in W.TERMINAL and r.get("clave") not in out:
            out[r["clave"]] = r
    return out


def all_live_rows() -> dict:
    p = worker_paths().results
    try:
        s = p.stat()
    except OSError:
        return {}
    return _live_rows(str(p), s.st_mtime, s.st_size)


def live_row(clave: str) -> Optional[dict]:
    return all_live_rows().get(clave)


def pending() -> list[str]:
    """Station requests not yet audited, in the order the worker will take them."""
    out = []
    for x in read_priority():
        k = x["clave"]
        if k not in out and live_row(k) is None:
            out.append(k)
    return out


def worker_state() -> dict:
    W = _worker()
    P = worker_paths()
    st = W.read_json(P.state, {}) or {}
    hb = W.read_json(P.heartbeat, {}) or {}
    age = time.time() - float(hb.get("t", 0) or 0)
    return {"running": st.get("status") in ("running", "paused") and age < 900, "status": st.get("status"),
            "pause": st.get("pause"), "pause_text": st.get("pause_text"), "resume_at": st.get("resume_at"),
            "reader": st.get("reader")}


def enqueue(clave: str) -> dict:
    """Put a station at the front of the worker's queue (after earlier requests). Idempotent."""
    W = _worker()
    with _lock:
        live = [x for x in read_priority() if live_row(x["clave"]) is None]
        if not any(x["clave"] == clave for x in live):
            if len(live) >= MAX_PENDING:
                return {"queued": False, "refused": "full",
                        "message": f"{MAX_PENDING} stations are already waiting for a live read; try again later."}
            live.append({"clave": clave, "ts": W.iso()})
            priority_file().parent.mkdir(parents=True, exist_ok=True)
            W.write_atomic(priority_file(), json.dumps({"items": live}, indent=1))
    order = pending()
    return {"queued": True, "clave": clave, "position": order.index(clave) + 1 if clave in order else None,
            "waiting": len(order), "worker": worker_state()}


# ------------------------------------------------------------------------------------------------ one answer
def answer(clave: str, st: Optional[storemod.Store] = None) -> dict:
    """What we have for one station: measured / live / live_unread / staged / queued / not_audited / not_queueable /
    unknown."""
    st = st or storemod.get_store()
    loc = locate(clave)
    base = {"clave": clave, "loc": loc}
    r = st.default_read(clave)
    has_img = st.masked_image(clave) is not None
    if r is not None and has_img and r.error is None:
        from app import live_status
        ev = storemod.evaluate(r)
        rcs = [x for x in live_status._measured_receipts(st, include_pilot=True) if x["clave"] == clave]
        errs = [{"code": e["code"], "name": e["name"], "paper": e.get("paper"), "capture": e.get("prep"),
                 "certified": e.get("certified"), "img": f"/crop/{clave}/{e['code']}.jpg?pad=0.012&label=0"}
                for e in _keying(clave) if not any(x["code"] == e["code"] for x in rcs)]
        run = st.runs[r.run_id]
        return base | {"kind": "measured", "img": f"/masked/{clave}.jpg", "line": ev["line"], "accepted": ev["accepted"],
                       "run": run.get("label"), "model": run.get("model"), "receipts": rcs, "errors": errs,
                       "viewer": f"/form/{clave}"}
    lr = live_row(clave)
    if lr is not None:
        W = _worker()
        if lr.get("status") != "audited":
            return base | {"kind": "live_unread", "why": lr.get("why") or lr.get("status"), "ts": lr.get("ts")}
        P = worker_paths()
        ds = [{"code": d["code"], "name": storemod.name_of(storemod.key_of(d["code"]) or d["code"]),
               "paper": d["paper"], "capture": d["capture"], "certified": d["certified"], "label": d["label"],
               "label_text": W.LABELS.get(d["label"], d["label"]), "img": f"/live/crop/{clave}/{d['code']}.jpg",
               "receipt": f"/api/live-audit/receipt/{clave}/{d['code']}"} for d in lr.get("disputes", [])]
        ds.sort(key=lambda d: (d["label"] != "confirmed", d["code"].startswith("OPT"), d["code"]))
        return base | {"kind": "live", "img": f"/station/page/{clave}.jpg" if (P.pages / f"{clave}.jpg").is_file() else None,
                       "accepted": lr.get("accepted"), "reader": lr.get("reader"), "ts": lr.get("ts"),
                       "disputes": ds, "cert_mode": lr.get("cert_mode")}
    if has_img:
        order = pending()
        return base | {"kind": "staged", "img": f"/masked/{clave}.jpg", "queueable": in_worker_queue(clave),
                       "position": order.index(clave) + 1 if clave in order else None, "waiting": len(order),
                       "worker": worker_state()}
    if loc is None:
        return base | {"kind": "unknown"}
    if not in_worker_queue(clave):
        return base | {"kind": "not_queueable"}
    order = pending()
    if clave in order:
        return base | {"kind": "queued", "position": order.index(clave) + 1, "waiting": len(order),
                       "worker": worker_state()}
    return base | {"kind": "not_audited", "waiting": len(order), "worker": worker_state()}


def _keying(clave: str) -> list[dict]:
    """This form's capture errors in the pre-registered 300 (app/data/headline.json)."""
    from app import numbers as numbersmod
    out = []
    for x in (numbersmod.headline() or {}).get("keying_list", []):
        if x["clave"] == clave:
            out.append({**x, "code": storemod.code_of(x["field"]), "name": storemod.name_of(x["field"])})
    return out


# ------------------------------------------------------------------------------------------------ routes
def _templates():
    from app.main import templates
    return templates


@router.get("/station", response_class=HTMLResponse)
def station_page(request: Request, c: Optional[str] = None):
    c = re.sub(r"[^0-9A-Za-z]", "", c or "").upper()
    a = answer(c) if CLAVE.match(c) else None
    states = [{"ent": e, "name": s["name"]} for e, s in index()["states"].items()]
    return _templates().TemplateResponse(request, "station.html", {"nav": "station", "a": a, "q": c, "states": states,
                                                                   "N": index().get("n", 0),
                                                                   "examples": _examples()})


def _examples() -> list[dict]:
    """Three stations to click: a certified-confirmed receipt, a live-audited form (if any), a station not read yet."""
    from app import live_status
    st = storemod.get_store()
    out = []
    rs = live_status.order_receipts(live_status._measured_receipts(st))
    if rs:
        out.append({"clave": rs[0]["clave"], "what": "a measured form with a receipt"})
    keys = _flat()[0]
    rows = all_live_rows()
    lv = next((k for k, r in rows.items() if r.get("status") == "audited"), None)
    if lv:
        out.append({"clave": lv, "what": "audited live on AMD"})
    nxt = next((k for k in keys[len(keys) // 3:] if in_worker_queue(k) and k not in rows), None)
    if nxt:
        out.append({"clave": nxt, "what": "not audited yet"})
    return out


@router.get("/api/station/search")
def api_search(q: str = ""):
    return {"q": q, "results": [{"clave": k, **(locate(k) or {})} for k in search(q)]}


@router.get("/api/station/states")
def api_states():
    return {"states": [{"ent": e, "name": s["name"]} for e, s in index()["states"].items()]}


@router.get("/api/station/states/{ent}")
def api_districts(ent: str):
    s = index()["states"].get(ent)
    if s is None:
        raise HTTPException(404, "unknown state")
    return {"ent": ent, "name": s["name"], "districts": [{"dist": d, "name": dd["name"], "n": len(dd["c"])}
                                                         for d, dd in sorted(s["d"].items(), key=lambda kv: int(kv[0]))]}


@router.get("/api/station/states/{ent}/{dist}")
def api_stations(ent: str, dist: str):
    s = index()["states"].get(ent)
    if s is None or dist not in s["d"]:
        raise HTTPException(404, "unknown district")
    have = set(storemod.get_store().ine_claves())
    out = [{"clave": k, "have": "measured" if k in have else ("live" if live_row(k) else None)} for k in s["d"][dist]["c"]]
    return {"ent": ent, "dist": dist, "district": s["d"][dist]["name"], "stations": out}


@router.get("/api/station/{clave}")
def api_answer(clave: str):
    clave = clave.upper()
    if not CLAVE.match(clave):
        raise HTTPException(404, "unknown station")
    a = answer(clave)
    if a["kind"] == "unknown":
        raise HTTPException(404, "unknown station")
    return storemod.public(a)


@router.post("/api/station/{clave}/queue")
def api_queue(clave: str):
    clave = clave.upper()
    if not CLAVE.match(clave):
        raise HTTPException(404, "unknown station")
    a = answer(clave)
    if a["kind"] == "unknown":
        raise HTTPException(404, "unknown station")
    if a["kind"] in ("measured", "live", "live_unread") or (a["kind"] == "staged" and not a["queueable"]):
        return {"queued": False, "already": a["kind"], "message": "This station already has an answer."}
    if a["kind"] == "not_queueable":
        return JSONResponse({"queued": False, "refused": "not_in_queue",
                             "message": "This station has no PREP image in the live audit's queue."}, status_code=409)
    res = enqueue(clave)
    return JSONResponse(res, status_code=200 if res.get("queued") else 429)


@router.get("/station/page/{clave}.jpg")
def station_page_image(clave: str):
    """A live-audited form's stored page (masked in memory before it was written, downscaled)."""
    if not CLAVE.match(clave):
        raise HTTPException(404, "no page")
    P = worker_paths()
    p = P.pages / f"{clave}.jpg"
    if not p.is_file() or P.pages.resolve() not in p.resolve().parents:
        raise HTTPException(404, "no page")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})
