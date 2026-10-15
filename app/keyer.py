"""Be the second keyer (/keyer): a public demo. A visitor keys 5 fields from masked crops, blind, then sees per field
their value next to the official capture, the model's read with the gate's verdict, and the paper's value.

Each round shows the real mix of the pre-registered 300-form run (stored Gemma reads, official first capture):
  * 2 fields on ACCEPTED forms where the model agrees with the capture: the common case, "accepted, nobody needs
    to key it" (the paper's value is the one both agree on, and every identity on the form holds);
  * 1 field on an accepted form from the adjudicated set (the model and the capture disagreed there; settled on
    the photo), else another accepted agreement;
  * 2 ROUTED fields from the adjudicated set, at least one a confirmed capture error (verdict model_right).
The seed is per session (a cookie, and in the URL so a round can be shared and reproduced). Nothing is stored:
the answers travel in the reveal URL. The crop URL names only the round and the slot, never the form or field.
Every crop is cut from a MASKED page (the adjudication crops, or the masked page via app.main._crop_bytes).
"""
from __future__ import annotations

import random
import secrets
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

from app import spotcheck as sc

N = 5
COOKIE = "keyer_seed"
router = APIRouter()


@lru_cache(maxsize=1)
def capture() -> dict:
    """The official first capture of the 300 pre-registered forms: {clave: {key: int|None}}."""
    from app import capture_audit as ca
    from app.store import key_of
    h, rows = ca.parse_csv(ca.SAMPLE_CSV.read_text(encoding="utf-8"))
    m = ca.automap(h)
    out = {}
    for r in rows:
        c = r[m["id"]].strip().strip("'")
        out[c] = {key_of(code): ca.keyed_value(r[i])[0] for code, i in m["fields"].items() if i is not None and i < len(r)}
    return out


def _model_n(row: dict, key: str):
    from app.store import iv
    return iv(((row.get("fields") or {}).get(key) or {}).get("n"))


@lru_cache(maxsize=1)
def pools() -> dict:
    """Deterministic (sorted) pools of items 'clave__KEY'."""
    from app.capture_audit import stored_reads
    from app.store import get_store
    V, led = sc.load_verdicts(), sc.load_ledger()
    R, cap, s = stored_reads(), capture(), get_store()
    agree = sorted(f"{c}__{k}" for c, row in R.items() if row.get("accepted") and c in cap and s.masked_image(c)
                   for k, v in cap[c].items() if v is not None and _model_n(row, k) == v and f"{c}__{k}" not in V)
    num = {k for k, v in V.items() if isinstance(v.get("paper"), int)}
    acc_adj = sorted(k for k in num if (led.get(k) or {}).get("form_accepted"))
    routed = [k for k in num if not (led.get(k) or {}).get("form_accepted")]
    err = sorted(k for k in routed if V[k]["verdict"] == "model_right")
    other = sorted(k for k in routed if V[k]["verdict"] in ("model_right", "capture_right"))
    return {"agree": agree, "accepted_adjudicated": acc_adj, "routed_error": err, "routed": other}


def draw(seed: int) -> list[str]:
    """The 5 items of round `seed`: 2 accepted agreements, 1 accepted adjudicated field (else another agreement),
    2 routed fields of which at least one is a confirmed capture error; shuffled."""
    P = pools()
    rng = random.Random(seed)
    items = rng.sample(P["agree"], 3 if not P["accepted_adjudicated"] else 2)
    if P["accepted_adjudicated"]:
        items.append(rng.choice(P["accepted_adjudicated"]))
    e = rng.choice(P["routed_error"])
    items += [e, rng.choice([k for k in P["routed"] if k != e])]
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


def _row(item: str) -> dict:
    """What is known about one item: capture, model, gate, paper and its source."""
    from app.capture_audit import stored_reads
    from app.store import name_of, neutralize
    V, led = sc.load_verdicts(), sc.load_ledger()
    clave, key = item.split("__", 1)
    if item in V:
        v, r = V[item], led.get(item) or {}
        prep = r.get("prep")
        accepted = bool(r.get("form_accepted"))
        own = key in ((stored_reads().get(clave) or {}).get("failing_fields") or [])
        return {"form": clave, "field": name_of(key), "kind": "error" if v["verdict"] == "model_right" else "right",
                "official": prep if prep is not None else
                ("illegible" if str(r.get("prep_raw", "")).lower().startswith("ileg") else "no data"),
                "official_n": prep, "model_n": r.get("model_n"), "model_w": r.get("model_w"),
                "gate": "accepted" if accepted else "routed",
                "gate_why": ("every identity on the paper holds with the model's read" if accepted else
                             "this field breaks one of the paper's identities" if own else
                             "the form fails a check of the paper's arithmetic"),
                "paper": v.get("paper"), "evidence": neutralize(v.get("evidence", "")), "source": "photo"}
    row = stored_reads()[clave]
    val = capture()[clave][key]
    w = ((row.get("fields") or {}).get(key) or {}).get("w")
    return {"form": clave, "field": name_of(key), "kind": "agree", "official": val, "official_n": val,
            "model_n": _model_n(row, key), "model_w": w, "gate": "accepted",
            "gate_why": "every identity on the paper holds with the model's read: nobody needs to key it",
            "paper": val, "evidence": "the official capture and the model agree, and every identity on the form holds",
            "source": "agreement"}


def reveal(seed: int, answers: list[str]) -> dict:
    """Per field: the visitor's value, the official capture, the model's read and the gate's verdict, the paper."""
    rows = []
    for j, item in enumerate(draw(seed)):
        x = _row(item)
        raw = answers[j] if j < len(answers) else ""
        a = str(raw or "").strip().lower()
        you = "blank" if a in ("b", "-", "blank") else (sc.as_int(a) if a not in ("", "?") else None)
        paper = x["paper"]
        rows.append({**x, "slot": j, "you": you,
                     "you_raw": "can't tell" if a == "?" else ("" if you is None else str(you)),
                     "you_ok": you is not None and str(you) == str(paper),
                     "official_ok": x["official_n"] is not None and str(x["official_n"]) == str(paper),
                     "model_ok": x["model_n"] is not None and str(x["model_n"]) == str(paper)})
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
def keyer(request: Request, s: Optional[str] = None, new: int = 0):
    """No seed: this session's seed (cookie), or a new one (?new=1 or first visit)."""
    if s is None:
        c = request.cookies.get(COOKIE)
        seed = int(c) if (c and c.isdigit() and 0 < int(c) < 10 ** 9 and not new) else secrets.randbelow(10 ** 9 - 1) + 1
        r = RedirectResponse(f"/keyer?s={seed}", status_code=302)
        r.set_cookie(COOKIE, str(seed), max_age=12 * 3600, samesite="lax", httponly=True)
        return r
    seed = _seed(s)
    from app.store import name_of
    items = [{"slot": j, "field": name_of(k.split("__", 1)[1])} for j, k in enumerate(draw(seed))]
    resp = _t().TemplateResponse(request, "keyer.html", {"nav": "keyer", "seed": seed, "items": items, "R": None})
    resp.set_cookie(COOKIE, str(seed), max_age=12 * 3600, samesite="lax", httponly=True)
    return resp


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
    item = draw(seed)[j]
    if item in sc.load_verdicts():
        p = sc._crop_path(item)  # cut from the MASKED page by twohands.adjudicate (never a raw image)
        if not p.is_file():
            raise HTTPException(404)
        return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    from app.main import _crop_bytes
    from app.store import get_store
    clave, key = item.split("__", 1)
    p = get_store().masked_image(clave)  # the masked page only
    if p is None:
        raise HTTPException(404)
    data = _crop_bytes(str(p), p.stat().st_mtime, key, 0.004, False)
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
