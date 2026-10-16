"""Blind spot-check of the AI adjudication by a person (additive; /check and /check/results).

One masked crop at a time. The page shows NO AI verdict, NO model value and NO PREP value: the person types the
number in the digit boxes and the number the words say (or ticks blank / can't tell / digits and words differ).
Answers go to app/state/spotcheck.json. /check/results then compares them with the AI verdicts.

Queue (deterministic): all model_right verdicts + 20 drawn with random.Random(7) from the other classes (crop_wrong
excluded: its crop does not show the written value) + every verdict on an accepted form; deduplicated, then shuffled
with random.Random(SHUFFLE_SEED).

Second queue (?set=confirm100, additive): exactly the disagreement crops of the pre-registered 100-form confirmation
(results/adjudication_confirm100/verdicts.json), shuffled with random.Random(SHUFFLE_SEED), the same blind page;
answers go apart, to app/state/spotcheck_confirm100.json (app/confirm100.py turns them into the Results wording).

Third queue (?set=agree200, additive): a seeded random 200 of the accepted fields where the model and the official
capture AGREE, on the forms the two-reader tier accepts (results/adjudication_agree200/, scripts/build_agree200.py).
The same blind page; answers go to app/state/spotcheck_agree200.json. agree200_result() feeds
app/numbers.checked_line(), which states the result only once all 200 are answered.
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
from fastapi.responses import Response, FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from twohands import REPO

ADJ = REPO / "results" / "adjudication"
FILE = REPO / "app" / "state" / "spotcheck.json"
OTHER_N, OTHER_SEED, SHUFFLE_SEED = 20, 7, 20261015
AMBIG = ("paper_ambiguous", "unreadable")
ADJ_C100 = REPO / "results" / "adjudication_confirm100"
FILE_C100 = REPO / "app" / "state" / "spotcheck_confirm100.json"
ADJ_A200 = REPO / "results" / "adjudication_agree200"
FILE_A200 = REPO / "app" / "state" / "spotcheck_agree200.json"
SETS = ("main", "confirm100", "agree200")
_lock = threading.Lock()
router = APIRouter()


# ------------------------------------------------------------------ data
def _set(set_: Optional[str]) -> str:
    s = set_ or "main"
    if s not in SETS:
        raise HTTPException(404)
    return s


def adj_dir(set_: Optional[str] = None) -> Path:
    return {"confirm100": ADJ_C100, "agree200": ADJ_A200}.get(_set(set_), ADJ)


def answers_file(set_: Optional[str] = None) -> Path:
    return {"confirm100": FILE_C100, "agree200": FILE_A200}.get(_set(set_), FILE)


def load_verdicts(set_: Optional[str] = None) -> dict:
    return json.loads((adj_dir(set_) / "verdicts.json").read_text(encoding="utf-8"))


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


def build_queue_c100(verdicts: dict) -> list[str]:
    """Every disagreement crop of the 100-form confirmation, nothing else, in a fixed shuffled order."""
    q = sorted(verdicts)
    random.Random(SHUFFLE_SEED).shuffle(q)
    return q


def queue(set_: Optional[str] = None) -> list[str]:
    if _set(set_) in ("confirm100", "agree200"):
        return build_queue_c100(load_verdicts(set_))
    return build_queue(load_verdicts(), load_ledger())


def load(set_: Optional[str] = None) -> dict:
    try:
        return json.loads(answers_file(set_).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_answer(item: str, ans: dict, set_: Optional[str] = None) -> None:
    f = answers_file(set_)
    with _lock:
        d = load(set_)
        d[item] = ans
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(f)


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


def agree200_result(answers: Optional[dict] = None) -> Optional[dict]:
    """The blind check of 200 agreeing fields: answered, queue size, and how many the person read as the agreed value
    (a ticked blank counts as agreeing with 0). None when the set is not built."""
    try:
        verdicts = load_verdicts("agree200")
    except (OSError, ValueError):
        return None
    answers = load("agree200") if answers is None else answers
    q = sorted(verdicts)
    got = [k for k in q if answers.get(k)]
    ok = sum(1 for k in got if agrees(answers[k], verdicts[k])
             or (answers[k].get("blank") and str(verdicts[k].get("paper")) == "0"))
    return {"queue": len(q), "answered": len(got), "agree": ok}


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
    """Neutral caption: 'Option NN' for vote rows (never a party name), plain English for the rest."""
    from app.store import name_of
    return name_of(item.split("__", 1)[1])


def _crop_path(item: str, set_: Optional[str] = None) -> Path:
    from twohands.adjudicate import crop_name
    clave, key = item.split("__", 1)
    return adj_dir(set_) / crop_name(clave, key)


def _qs(set_: Optional[str]) -> dict:
    """Query-string pieces that keep the page on its queue: ('?set=confirm100', '&set=confirm100') or ('', '')."""
    s = _set(set_)
    return {"qset": s, "qs": "" if s == "main" else f"?set={s}", "qa": "" if s == "main" else f"&set={s}"}


@router.get("/check", response_class=HTMLResponse)
def check(request: Request, i: Optional[int] = None, set: Optional[str] = None):  # noqa: A002 (the query name)
    q, ans, Q = queue(set), load(set), _qs(set)
    if i is None:
        i = next((n for n, k in enumerate(q) if k not in ans), len(q))
    if i >= len(q):
        return _templates(request).TemplateResponse(request, "check.html", {"nav": "check", "done": True, "n": len(q),
                                                                          "answered": sum(k in ans for k in q), **Q})
    if i < 0:
        raise HTTPException(404)
    item = q[i]
    prev = ans.get(item) or {}
    return _templates(request).TemplateResponse(request, "check.html", {
        "nav": "check", "done": False, "i": i, "n": len(q), "answered": sum(k in ans for k in q),
        "field": _field_of(item), "prev": prev, **Q})


@router.get("/check/img/{i}.jpg")
def check_img(i: int, enh: int = 0, set: Optional[str] = None):  # noqa: A002
    q = queue(set)
    if not 0 <= i < len(q):
        raise HTTPException(404)
    p = _crop_path(q[i], set)  # cut from the MASKED page by twohands.adjudicate (never a raw image)
    if not p.is_file():
        raise HTTPException(404)
    if enh:
        return Response(_enhanced(p), media_type="image/jpeg", headers={"Cache-Control": "no-store"})
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


def _enhanced(p: Path) -> bytes:
    """Display-only darkening for faint pencil: grayscale, autocontrast, gamma 3. The stored crop is unchanged."""
    import io
    from PIL import Image, ImageOps
    im = ImageOps.autocontrast(Image.open(p).convert("L"), cutoff=(1, 5))
    im = im.point([int(255 * (v / 255) ** 3.0) for v in range(256)])
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


@router.post("/api/check/{i}")
async def check_answer(i: int, request: Request, set: Optional[str] = None):  # noqa: A002
    q = queue(set)
    if not 0 <= i < len(q):
        raise HTTPException(404)
    try:
        a = clean_answer(await request.json())
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    save_answer(q[i], a, set)
    ans = load(set)
    nxt = next((n for n in list(range(i + 1, len(q))) + list(range(0, i)) if q[n] not in ans), len(q))
    return {"ok": True, "next": nxt, "answered": sum(k in ans for k in q), "n": len(q)}


@router.get("/check/results", response_class=HTMLResponse)
def check_results(request: Request, set: Optional[str] = None):  # noqa: A002
    q = queue(set)
    res = _neutral(score(load(set), q, load_verdicts(set)))
    return _templates(request).TemplateResponse(request, "check_results.html", {"nav": "check", "r": res, **_qs(set)})


@router.get("/api/check/results")
def check_results_json(set: Optional[str] = None):  # noqa: A002
    q = queue(set)
    return _neutral(score(load(set), q, load_verdicts(set)))


def _neutral(res: dict) -> dict:
    """Items and evidence shown with neutral field names (Option NN), never a party name."""
    from app.store import neutralize
    for d in res.get("disagreements", []):
        clave, key = d["item"].split("__", 1)
        d["item"] = f"{clave} · {_field_of(d['item'])}"
        d["evidence"] = neutralize(d.get("evidence", ""))
    return res
