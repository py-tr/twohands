"""The live audit, as the site shows it: /live (status page), /about-data, a small block the Overview can include, and
read-only JSON (status, one receipt with its Merkle path).

Everything comes from the worker's directory (twohands/worker.py; TWOHANDS_WORKER_DIR, default live_audit/). Nothing
here calls a model or writes a file. The numbers are counts of forms and of disputed fields; no vote total is ever
summed or shown, and vote rows appear only as "Option NN". The worker's numbers are separate from the pre-registered
results (they are never read by twohands.eval).
"""
from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse

from app import store as storemod
from twohands import worker as W

router = APIRouter()
STOPPED_AFTER_S = 900          # no heartbeat for 15 minutes: the worker is shown as not running
NOT_OFFICIAL = "Not an official INE product; the certified count is the official result."
_CODE = re.compile(r"^[0-9]{6}[A-Z][0-9]{4}$")
_FIELD = re.compile(r"^[A-Z0-9_]{2,16}$")
_cache: dict = {"key": None, "v": None}
_lock = threading.Lock()


def worker_dir() -> Path:
    return W.WORKER_DIR


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def _rows(P: W.Paths) -> list[dict]:
    out, seen = [], set()
    for r in W.read_jsonl(P.results):
        if r.get("status") in W.TERMINAL and r.get("clave") not in seen:
            seen.add(r.get("clave"))
            out.append(r)
    return out


def _status_text(st: dict, hb: dict) -> dict:
    """The one status line the page shows: running, paused (with the reason), complete, or not running."""
    age = time.time() - float(hb.get("t", 0) or 0)
    s = st.get("status")
    if s == "complete":
        return {"kind": "ok", "text": "Complete: every form in the queue has been audited"}
    if s == "paused" and age < STOPPED_AFTER_S:
        return {"kind": "warn", "text": st.get("pause_text") or "Paused", "resume_at": st.get("resume_at")}
    if s == "running" and age < STOPPED_AFTER_S:
        return {"kind": "live", "text": "Running: auditing tally sheets on AMD now"}
    last = hb.get("ts") or st.get("ts")
    return {"kind": "idle", "text": "Not running at the moment" + (f" (last active {last.replace('T', ' ').replace('Z', ' UTC')})" if last else "")}


def summary() -> Optional[dict]:
    """All the page needs, cached until a worker file changes. None when the worker has never written a row."""
    P = W.Paths(worker_dir())
    key = (str(P.root), _mtime(P.results), _mtime(P.state), _mtime(P.heartbeat))
    with _lock:
        if _cache["key"] == key and _cache["v"] is not None:
            v = dict(_cache["v"])
            v["status"] = _status_text(W.read_json(P.state, {}) or {}, W.read_json(P.heartbeat, {}) or {})
            return v
    q = W.load_queue(P.queue)
    rows = _rows(P)
    if q is None or not rows:
        return None
    st = W.read_json(P.state, {}) or {}
    hb = W.read_json(P.heartbeat, {}) or {}
    roots = W.read_json(P.roots, {}) or {}
    audited = [r for r in rows if r["status"] == "audited"]
    disputes = [dict(d, clave=r["clave"], state=r["state"], reader=r.get("reader"), ts=r["ts"], ent=r["ent"])
                for r in audited for d in r.get("disputes", [])]
    states = []
    for ent, s in q["states"].items():
        done = sum(1 for r in rows if str(r["ent"]) == ent)
        if not done:
            continue
        n_aud = sum(1 for r in audited if str(r["ent"]) == ent)
        rt = roots.get(ent, {})
        states.append({"ent": ent, "name": s["name"], "done": done, "queue": s["queue"], "audited": n_aud,
                       "complete": done >= s["queue"], "pct": round(100.0 * done / max(1, s["queue"]), 1),
                       "root": rt.get("root"), "leaves": rt.get("leaves", 0),
                       "measured_skipped": s.get("measured_skipped", 0)})
    latest = None
    if disputes:
        d = disputes[-1]
        latest = {"clave": d["clave"], "state": d["state"], "code": d["code"], "name": storemod.name_of(storemod.key_of(d["code"]) or d["code"]),
                  "paper": d["paper"], "words": d["words"], "capture": d["capture"], "certified": d["certified"],
                  "label": d["label"], "label_text": W.LABELS[d["label"]], "reader": d["reader"], "ts": d["ts"],
                  "weak": bool(d.get("weak")),
                  "crop": f"/live/crop/{d['clave']}/{d['code']}.jpg",
                  "receipt": f"/api/live-audit/receipt/{d['clave']}/{d['code']}"}
    nxt = None
    if st.get("status") != "complete":
        done_set = {r["clave"] for r in rows}
        for it in q["items"]:
            if it["clave"] not in done_set:
                nxt = q["states"][str(it["ent"])]["name"]
                break
    v = {"audited": len(audited), "disputes": len(disputes),
         "confirmed": sum(1 for d in disputes if d["label"] == "confirmed"),
         "model_misread": sum(1 for d in disputes if d["label"] == "model_misread"),
         "unconfirmed": sum(1 for d in disputes if d["label"] == "unconfirmed"),
         "weak": sum(1 for d in disputes if d.get("weak")),
         "weak_confirmed": sum(1 for d in disputes if d.get("weak") and d["label"] == "confirmed"),
         "weak_text": W.WEAK,
         "not_read": len(rows) - len(audited),
         "not_compared": sum(1 for r in audited if {"shape", "label"} & set(r.get("route_codes") or [])),
         "readers": sorted({r.get("reader") for r in audited if r.get("reader")}),
         "reader_now": st.get("reader"), "states": states, "next_state": nxt, "latest": latest,
         "recent": [{"clave": d["clave"], "state": d["state"], "code": d["code"],
                     "name": storemod.name_of(storemod.key_of(d["code"]) or d["code"]), "label_text": W.LABELS[d["label"]],
                     "label": d["label"], "weak": bool(d.get("weak")), "paper": d["paper"], "capture": d["capture"], "certified": d["certified"],
                     "reader": d["reader"], "crop": f"/live/crop/{d['clave']}/{d['code']}.jpg",
                     "receipt": f"/api/live-audit/receipt/{d['clave']}/{d['code']}"} for d in disputes[-12:][::-1]],
         "queue_total": len(q["items"]), "queue_states": len(q["states"]),
         "updated": (hb.get("ts") or st.get("ts") or rows[-1]["ts"]),
         "status": _status_text(st, hb), "not_official": NOT_OFFICIAL}
    with _lock:
        _cache.update(key=key, v=v)
    return v


def receipt(clave: str, code: str) -> Optional[dict]:
    """One dispute's receipt: its leaf record, the leaf hash, the path to its state's root (final when the state is
    complete, the running root otherwise). Checkable offline with ``python -m twohands.verify_receipt``."""
    from twohands import merkle
    P = W.Paths(worker_dir())
    q = W.load_queue(P.queue)
    rows = _rows(P)
    hit = next((r for r in rows if r["clave"] == clave), None)
    if hit is None or q is None:
        return None
    ent = str(hit["ent"])
    recs = [d["leaf"] for r in rows if str(r["ent"]) == ent and r["status"] == "audited" for d in r.get("disputes", [])]
    leaves = [merkle.leaf_hash(x) for x in recs]
    idx = next((i for i, x in enumerate(recs) if x["form"] == clave and x["field"] == code), None)
    if idx is None:
        return None
    done = sum(1 for r in rows if str(r["ent"]) == ent)
    return {"leaf": recs[idx], "leaf_hash": leaves[idx], "proof": merkle.proof(leaves, idx), "root": merkle.root(leaves),
            "state": q["states"][ent]["name"], "state_complete": done >= q["states"][ent]["queue"],
            "root_kind": "final" if done >= q["states"][ent]["queue"] else "running",
            "leaves": len(leaves), "index": idx, "label_text": W.LABELS.get(W.label_of_tier(recs[idx]["tier"])),
            "evidence": W.WEAK if W.WEAK in recs[idx]["tier"] else "row labels confirmed",
            "verify": "python -m twohands.verify_receipt receipt.json --crop crop.jpg"}


def block() -> Optional[dict]:
    """The three numbers for the Overview's small block (None hides it)."""
    try:
        v = summary()
    except Exception:  # noqa: BLE001 - the block must never break the Overview
        return None
    return None if v is None else {k: v[k] for k in ("audited", "disputes", "confirmed", "status")}


def _templates(request: Request):
    from app.main import templates
    return templates


@router.get("/live", response_class=HTMLResponse)
def live_page(request: Request):
    v = summary()
    return _templates(request).TemplateResponse(request, "live_audit.html", {"nav": "live", "v": v, "LABELS": W.LABELS,
                                                                           "NOT_OFFICIAL": NOT_OFFICIAL,
                                                                           "cap": W.DAILY_USD, "reserve": W.RESERVE_USD})


@router.get("/about-data", response_class=HTMLResponse)
def about_data(request: Request):
    return _templates(request).TemplateResponse(request, "about_data.html", {"nav": "live", "NOT_OFFICIAL": NOT_OFFICIAL,
                                                                           "UA": W.USER_AGENT, "page_kb": W.PAGE_KB,
                                                                           "cap": W.DAILY_USD, "reserve": W.RESERVE_USD,
                                                                           "LABELS": W.LABELS, "WEAK": W.WEAK})


@router.get("/api/live-audit/status")
def api_status():
    v = summary()
    if v is None:
        return {"audited": 0, "disputes": 0, "confirmed": 0, "status": {"kind": "idle", "text": "Not started"},
                "not_official": NOT_OFFICIAL}
    return storemod.public(v)


@router.get("/api/live-audit/receipt/{clave}/{code}")
def api_receipt(clave: str, code: str):
    if not _CODE.match(clave) or not _FIELD.match(code):
        raise HTTPException(404, "unknown receipt")
    r = receipt(clave, code)
    if r is None:
        raise HTTPException(404, "unknown receipt")
    return r


@router.get("/live/crop/{clave}/{code}.jpg")
def live_crop(clave: str, code: str):
    """A dispute's crop (cut from the masked page; left of the privacy mask, without the printed row label)."""
    if not _CODE.match(clave) or not _FIELD.match(code):
        raise HTTPException(404, "no crop")
    P = W.Paths(worker_dir())
    p = (P.crops / f"{clave}__{code}.jpg")
    if not p.is_file() or P.crops.resolve() not in p.resolve().parents:
        raise HTTPException(404, "no crop")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})


def fmt_ts(ts: Optional[str]) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%d %b %H:%M UTC")
    except ValueError:
        return ts
