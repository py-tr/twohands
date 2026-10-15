"""Be the second keyer (/keyer): a public demo. A visitor keys 5 fields from masked crops, blind, then sees per field
their value next to the official capture, the model's read with the gate's verdict, and the photo-based truth.

The 5 fields are drawn at random (a seed in the URL, so a round can be shared) from the adjudicated set
(results/adjudication: every field where the model and the official capture disagreed, settled on the photo):
2 or 3 real capture errors (verdict model_right) and the rest easy fields where the official capture was right
(capture_right), all with a number on the paper. Nothing is stored: the answers travel in the reveal URL.
The crop URL names only the round and the slot, never the form or the field, so the page gives nothing away.
Crops are the adjudication crops, cut from MASKED pages (the same images /check shows).
"""
from __future__ import annotations

import random
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app import spotcheck as sc

N = 5
router = APIRouter()


def pools() -> tuple[list[str], list[str]]:
    """(capture errors, easy fields): adjudicated items with a number on the paper, sorted (deterministic)."""
    V = sc.load_verdicts()
    err = sorted(k for k, v in V.items() if v["verdict"] == "model_right" and isinstance(v.get("paper"), int))
    easy = sorted(k for k, v in V.items() if v["verdict"] == "capture_right" and isinstance(v.get("paper"), int))
    return err, easy


def draw(seed: int) -> list[str]:
    """The 5 items of round `seed`: 2 or 3 capture errors, the rest easy, shuffled."""
    err, easy = pools()
    rng = random.Random(seed)
    k = rng.choice((2, 3))
    items = rng.sample(err, k) + rng.sample(easy, N - k)
    rng.shuffle(items)
    return items


def _seed(s) -> int:
    try:
        v = int(s)
    except (TypeError, ValueError):
        raise HTTPException(404, "unknown round")
    if not 0 < v < 10 ** 9:
        raise HTTPException(404, "unknown round")
    return v


def _stored_row(clave: str) -> Optional[dict]:
    from app.capture_audit import stored_reads
    return stored_reads().get(clave)


def reveal(seed: int, answers: list[str]) -> dict:
    """Per field: the visitor's value, the official capture, the model's read and the gate's verdict, the paper."""
    from app.store import name_of, neutralize
    led = sc.load_ledger()
    V = sc.load_verdicts()
    rows = []
    for j, item in enumerate(draw(seed)):
        v, r = V[item], led.get(item) or {}
        clave, key = item.split("__", 1)
        raw = answers[j] if j < len(answers) else ""
        a = str(raw or "").strip().lower()
        you = "blank" if a in ("b", "-", "blank") else (sc.as_int(a) if a not in ("", "?") else None)
        paper = v.get("paper")
        prep = r.get("prep")
        accepted = bool(r.get("form_accepted"))
        row = _stored_row(clave) or {}
        own_field = key in (row.get("failing_fields") or [])
        rows.append({
            "slot": j, "form": clave, "field": name_of(key), "verdict": v["verdict"],
            "you": you, "you_raw": "can't tell" if a == "?" else ("" if you is None else str(you)),
            "official": prep if prep is not None else ("illegible" if str(r.get("prep_raw", "")).lower().startswith("ileg")
                                                       else "no data"),
            "model_n": r.get("model_n"), "model_w": r.get("model_w"),
            "gate": "accepted" if accepted else "routed",
            "gate_why": ("every identity on the paper holds with the model's read" if accepted else
                         ("this field breaks one of the paper's identities" if own_field else
                          "the form fails a check of the paper's arithmetic")),
            "paper": paper, "evidence": neutralize(v.get("evidence", "")),
            "you_ok": you is not None and str(you) == str(paper),
            "official_ok": prep is not None and str(prep) == str(paper),
            "model_ok": r.get("model_n") is not None and str(r.get("model_n")) == str(paper),
        })
    n = len(rows)
    score = {"n": n, "you": sum(x["you_ok"] for x in rows), "official": sum(x["official_ok"] for x in rows),
             "accepted": sum(x["gate"] == "accepted" for x in rows), "routed": sum(x["gate"] == "routed" for x in rows)}
    score["line"] = (f"You matched the paper on {score['you']} of {n}; the official capture matched on "
                     f"{score['official']}; the model plus the paper's arithmetic accepted {score['accepted']} and "
                     f"routed {score['routed']} to a person.")
    return {"seed": seed, "rows": rows, "score": score}


def _t():
    from app.main import templates
    return templates


@router.get("/keyer", response_class=HTMLResponse)
def keyer(request: Request, s: Optional[str] = None):
    if s is None:
        return RedirectResponse(f"/keyer?s={secrets.randbelow(10 ** 9 - 1) + 1}", status_code=302)
    seed = _seed(s)
    from app.store import name_of
    items = [{"slot": j, "field": name_of(k.split("__", 1)[1])} for j, k in enumerate(draw(seed))]
    return _t().TemplateResponse(request, "keyer.html", {"nav": "keyer", "seed": seed, "items": items, "R": None})


@router.get("/keyer/reveal", response_class=HTMLResponse)
def keyer_reveal(request: Request, s: str, a: Optional[list[str]] = Query(None)):
    seed = _seed(s)
    R = reveal(seed, list(a or []))
    return _t().TemplateResponse(request, "keyer.html", {"nav": "keyer", "seed": seed, "items": None, "R": R})


@router.get("/keyer/img/{s}/{j}.jpg")
def keyer_img(s: str, j: int):
    seed = _seed(s)
    if not 0 <= j < N:
        raise HTTPException(404)
    p = sc._crop_path(draw(seed)[j])  # cut from the MASKED page by twohands.adjudicate (never a raw image)
    if not p.is_file():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
