"""Blind spot-check of the AI adjudication by a person (additive; /check and /check/results).

One masked crop at a time. The page shows NO AI verdict, NO model value and NO PREP value: the person types the
number in the digit boxes and the number the words say (or ticks blank / can't tell / digits and words differ).
Answers go to app/state/spotcheck.json. /check/results then compares them with the AI verdicts.

Queue (deterministic): all model_right verdicts + 20 drawn with random.Random(7) from the other classes (crop_wrong
excluded: its crop does not show the written value) + every verdict on an accepted form; deduplicated, then shuffled
with random.Random(SHUFFLE_SEED).
"""
from __future__ import annotations

import json
import random
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from twohands import REPO

ADJ = REPO / "results" / "adjudication"
FILE = REPO / "app" / "state" / "spotcheck.json"
OTHER_N, OTHER_SEED, SHUFFLE_SEED = 20, 7, 20261015
AMBIG = ("paper_ambiguous", "unreadable")
_lock = threading.Lock()
router = APIRouter()


# ------------------------------------------------------------------ data
def load_verdicts() -> dict:
    return json.loads((ADJ / "verdicts.json").read_text(encoding="utf-8"))


def load_ledger() -> dict:
    out = {}
    p = ADJ / "adjudication.jsonl"
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[f"{r['clave']}__{r['field']}"] = r
    return out


def build_queue(verdicts: dict, ledger: dict) -> list[str]:
    mr = sorted(k for k, v in verdicts.items() if v["verdict"] == "model_right")
    pool = sorted(k for k, v in verdicts.items() if v["verdict"] not in ("model_right", "crop_wrong"))
    other = random.Random(OTHER_SEED).sample(pool, min(OTHER_N, len(pool)))
    acc = sorted(k for k in verdicts if (ledger.get(k) or {}).get("form_accepted"))
    q = list(dict.fromkeys(mr + other + acc))
    random.Random(SHUFFLE_SEED).shuffle(q)
    return q


def queue() -> list[str]:
    return build_queue(load_verdicts(), load_ledger())


def load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_answer(item: str, ans: dict) -> None:
    with _lock:
        d = load()
        d[item] = ans
        FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(FILE)


def as_int(x) -> Optional[int]:
    s = re.sub(r"[\s,.]", "", str(x if x is not None else ""))
    return int(s) if s.isdigit() else None


def clean_answer(raw: dict) -> dict:
    """Normalise a submitted answer. Typing 'b' or '-' in the digits box = blank; '?' = can't tell."""
    d, w = str(raw.get("digits") or "").strip(), str(raw.get("words") or "").strip()
    blank, cant, differ = bool(raw.get("blank")), bool(raw.get("cant_tell")), bool(raw.get("differ"))
    if d.lower() in ("b", "-"):
        blank, d = True, ""
    if d == "?":
        cant, d = True, ""
    di, wi = as_int(d), as_int(w)
    if di is not None and wi is not None and di != wi:
        differ = True
    if di is None and not (blank or cant or differ):
        raise ValueError("type the digits, or tick blank / can't tell / differ")
    return {"digits": di, "words": wi, "blank": blank, "cant_tell": cant, "differ": differ,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


# ------------------------------------------------------------------ agreement
def person_value(a: dict):
    if a.get("digits") is not None:
        return a["digits"]
    return "blank" if a.get("blank") else None


def person_ambiguous(a: dict) -> bool:
    return bool(a.get("cant_tell") or a.get("differ"))


def agrees(a: dict, v: dict) -> bool:
    """agree = the person's digit value equals the AI's paper value, or both say ambiguous/unreadable."""
    pv, paper = person_value(a), v.get("paper")
    if pv is not None and paper is not None and str(pv) == str(paper):
        return True
    return person_ambiguous(a) and v["verdict"] in AMBIG


def score(answers: dict, q: list[str], verdicts: dict) -> dict:
    rows, by = [], {}
    for k in q:
        a = answers.get(k)
        if not a:
            continue
        v = verdicts[k]
        ok = agrees(a, v)
        rows.append({"item": k, "verdict": v["verdict"], "ai_paper": v.get("paper"), "person": person_value(a),
                     "person_words": a.get("words"), "person_ambiguous": person_ambiguous(a), "agree": ok,
                     "evidence": v.get("evidence", "")})
        b = by.setdefault(v["verdict"], [0, 0])
        b[0] += ok
        b[1] += 1
    n, k = len(rows), sum(r["agree"] for r in rows)
    mr = by.get("model_right", [0, 0])
    return {"answered": n, "queue": len(q), "agree": k, "rate": (k / n) if n else None,
            "by_verdict": {c: {"agree": x[0], "n": x[1]} for c, x in sorted(by.items())},
            "model_right": {"agree": mr[0], "n": mr[1]}, "disagreements": [r for r in rows if not r["agree"]]}


# ------------------------------------------------------------------ routes
def _templates(request: Request):
    from app.main import templates
    return templates


def _field_of(item: str) -> str:
    return item.split("__", 1)[1].replace("_", " ")


@router.get("/check", response_class=HTMLResponse)
def check(request: Request, i: Optional[int] = None):
    q, ans = queue(), load()
    if i is None:
        i = next((n for n, k in enumerate(q) if k not in ans), len(q))
    if i >= len(q):
        return _templates(request).TemplateResponse(request, "check.html", {"nav": "check", "done": True, "n": len(q),
                                                                          "answered": sum(k in ans for k in q)})
    if i < 0:
        raise HTTPException(404)
    item = q[i]
    prev = ans.get(item) or {}
    return _templates(request).TemplateResponse(request, "check.html", {
        "nav": "check", "done": False, "i": i, "n": len(q), "answered": sum(k in ans for k in q),
        "field": _field_of(item), "prev": prev})


@router.get("/check/img/{i}.jpg")
def check_img(i: int):
    q = queue()
    if not 0 <= i < len(q):
        raise HTTPException(404)
    p = ADJ / f"{q[i]}.jpg"  # cut from the MASKED page by twohands.adjudicate (never a raw image)
    if not p.is_file():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/api/check/{i}")
async def check_answer(i: int, request: Request):
    q = queue()
    if not 0 <= i < len(q):
        raise HTTPException(404)
    try:
        a = clean_answer(await request.json())
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    save_answer(q[i], a)
    ans = load()
    nxt = next((n for n in list(range(i + 1, len(q))) + list(range(0, i)) if q[n] not in ans), len(q))
    return {"ok": True, "next": nxt, "answered": sum(k in ans for k in q), "n": len(q)}


@router.get("/check/results", response_class=HTMLResponse)
def check_results(request: Request):
    q = queue()
    res = score(load(), q, load_verdicts())
    return _templates(request).TemplateResponse(request, "check_results.html", {"nav": "check", "r": res})


@router.get("/api/check/results")
def check_results_json():
    q = queue()
    return score(load(), q, load_verdicts())
