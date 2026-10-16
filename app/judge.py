"""Judge this verdict yourself (additive): /judge/{clave}/{code}[?a=<audit id>] and POST /api/judge/{clave}/{code}.

The visitor sees the masked crop and the field's neutral name only (as /check): no paper value, no capture, no model
read, no verdict. They type what the paper says; then the page reveals the paper value as adjudicated, the capture,
the certified value and our verdict. Each first answer per visitor and verdict appends one anonymous line to
app/state/public_verdicts.jsonl ({ts, item, agree}; no IP, no reading text). Rate-limited in memory by a salted hash
of the client address (never stored). Counts are shown as "N visitors checked this verdict, M agreed" once N >= 3.

Items: a dispute of the pre-registered run with a verdict (results/adjudication/verdicts.json) is "<clave>__<code>",
shared by Findings and any audit report that lists it; a dispute of an uploaded audit with no adjudication is
"a:<audit id>:<clave>__<code>", judged against our read of the paper (labelled "not adjudicated").
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app import caption as captionmod
from app import numbers as numbersmod
from app import spotcheck
from app import store as storemod
from twohands import REPO

FILE = REPO / "app" / "state" / "public_verdicts.jsonl"
SHOW_FROM = 3
PER_HOUR = 30                      # answers a visitor may record per hour
MAX_FILE_BYTES = 5 * 1024 * 1024   # the log stops growing past this (answers still get their reveal)
_SALT = os.urandom(16)
_lock = threading.Lock()
_recent: dict[str, deque] = defaultdict(deque)
_seen: set[tuple[str, str]] = set()
_cache: dict = {"mt": None, "c": {}}
router = APIRouter()

VERDICT_TEXT = {
    "model_right": "Capture error: the paper shows the value the model read, not the keyed one.",
    "capture_right": "No capture error: the paper shows the keyed value; the model misread.",
    "neither": "Neither the capture nor the model matches the paper.",
    "paper_ambiguous": "The paper does not settle it.",
    "unreadable": "Unreadable on the photo.",
}


# ------------------------------------------------------------------ the item behind a dispute
def _keying(clave: str, key: str) -> Optional[dict]:
    for x in (numbersmod.headline() or {}).get("keying_list", []):
        if x["clave"] == clave and x["field"] == key:
            return x
    return None


def _audit_dispute(request: Request, aid: str, clave: str, code: str) -> Optional[dict]:
    from app import audit_web, capture_audit as ca
    a = ca.load(aid)
    if a is None:
        return None
    R = audit_web._run(request, a)
    return next((d for d in R["disputes"] if d["form"] == clave and d["code"] == code), None)


def resolve(request: Request, clave: str, code: str, aid: Optional[str] = None) -> dict:
    """{item, clave, code, name, img, paper, capture, certified, verdict, verdict_text, adjudicated}; 404 if the
    field is not a dispute we list."""
    key = storemod.key_of(code)
    if key is None:
        raise HTTPException(404, "unknown field")
    V = spotcheck.load_verdicts()
    vk = f"{clave}__{key}"
    k = _keying(clave, key)
    d = _audit_dispute(request, aid, clave, code) if aid else None
    if aid and d is None:
        raise HTTPException(404, "not a dispute of this audit")
    if vk in V and (d is None or d.get("adjudicated")):
        v = V[vk]
        capture = k["prep"] if k else (d["keyed"] if d else None)
        if capture is None:
            raise HTTPException(404, "not a listed dispute")
        img = (d or {}).get("img") or (f"/crop/{clave}/{code}.jpg?pad=0.014&label=0"
                                       if storemod.get_store().masked_image(clave) else None)
        return {"item": f"{clave}__{code}", "clave": clave, "code": code, "name": storemod.name_of(key), "img": img,
                "paper": v.get("paper"), "capture": capture, "certified": (k or {}).get("certified"),
                "verdict": v["verdict"], "verdict_text": VERDICT_TEXT.get(v["verdict"], v["verdict"]),
                "adjudicated": True, "audit": aid}
    if d is None:
        raise HTTPException(404, "not a listed dispute")
    return {"item": f"a:{aid}:{clave}__{code}", "clave": clave, "code": code, "name": d["name"], "img": d.get("img"),
            "paper": d["model"] if d["model"] is not None else "blank", "capture": d["keyed"], "certified": None,
            "verdict": "unadjudicated",
            "verdict_text": (f"Not adjudicated: our read of the paper, {d['tier']} evidence that the keyed value is wrong. "
                             "The value above is the model's read, not a person's."),
            "adjudicated": False, "audit": aid}


# ------------------------------------------------------------------ counts and the log
def counts() -> dict:
    """{item: {"n", "agree"}} over app/state/public_verdicts.jsonl, cached until the file changes."""
    try:
        mt = FILE.stat().st_mtime_ns
    except OSError:
        return {}
    with _lock:
        if _cache["mt"] == mt:
            return _cache["c"]
        c: dict = {}
        for line in FILE.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            x = c.setdefault(r.get("item"), {"n": 0, "agree": 0})
            x["n"] += 1
            x["agree"] += bool(r.get("agree"))
        _cache.update(mt=mt, c=c)
        return c


def count_text(item: str) -> Optional[str]:
    c = counts().get(item)
    if not c or c["n"] < SHOW_FROM:
        return None
    return f"{c['n']} visitors checked this verdict, {c['agree']} agreed"


def _who(request: Request) -> str:
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
    return hashlib.sha256(_SALT + ip.encode()).hexdigest()[:20]


def record(who: str, item: str, agree: bool, now: Optional[float] = None) -> str:
    """'recorded', 'already' (this visitor answered this verdict before) or 'limited' (rate or size limit)."""
    now = time.time() if now is None else now
    with _lock:
        if (who, item) in _seen:
            return "already"
        q = _recent[who]
        while q and now - q[0] > 3600:
            q.popleft()
        if len(q) >= PER_HOUR:
            return "limited"
        try:
            if FILE.stat().st_size > MAX_FILE_BYTES:
                return "limited"
        except OSError:
            pass
        q.append(now)
        _seen.add((who, item))
        FILE.parent.mkdir(parents=True, exist_ok=True)
        with FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "item": item,
                                 "agree": bool(agree)}) + "\n")
        return "recorded"


# ------------------------------------------------------------------ routes
@router.get("/judge/{clave}/{code}", response_class=HTMLResponse)
def judge_page(clave: str, code: str, request: Request, a: Optional[str] = None):
    it = resolve(request, clave, code, a)
    from app.main import templates
    back = f"/audit/{a}/report" if a else "/audit"
    return templates.TemplateResponse(request, "judge.html", {
        "nav": "audit", "clave": clave, "code": code, "name": it["name"], "img": it["img"], "audit": a, "back": back,
        "helper": captionmod.HELPER})


@router.post("/api/judge/{clave}/{code}")
async def judge_answer(clave: str, code: str, request: Request, a: Optional[str] = None):
    it = resolve(request, clave, code, a)
    try:
        ans = spotcheck.clean_answer(await request.json())
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    agree = spotcheck.agrees(ans, {"verdict": it["verdict"], "paper": it["paper"]})
    status = record(_who(request), it["item"], agree)
    c = counts().get(it["item"], {"n": 0, "agree": 0})
    return storemod.public({
        "reading": spotcheck.person_value(ans) if spotcheck.person_value(ans) is not None else "can't tell",
        "agree": agree, "recorded": status, "paper": it["paper"], "capture": it["capture"],
        "certified": it["certified"], "verdict": it["verdict"], "verdict_text": it["verdict_text"],
        "adjudicated": it["adjudicated"], "n": c["n"], "agreed": c["agree"],
        "caption": captionmod.caption(clave, code),
        "count_text": count_text(it["item"]), "show_from": SHOW_FROM})
