"""Station requests from the site (/station): <worker dir>/priority.json lists stations a visitor asked to have read
live; the worker takes them before its normal queue order, in request order. Only stations already in the queue can
be prioritised, and every read still goes through the worker's budget guard and rate limiter."""
from __future__ import annotations

import json
from pathlib import Path


def requested(root: Path) -> list[str]:
    try:
        d = json.loads((Path(root) / "priority.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for x in (d.get("items") or []) if isinstance(d, dict) else []:
        k = x.get("clave") if isinstance(x, dict) else None
        if isinstance(k, str) and k not in out:
            out.append(k)
    return out


def prioritized(todo: list[dict], root: Path) -> list[dict]:
    """``todo`` (queue order) with the requested stations moved to the front, in request order."""
    want = requested(root)
    if not want:
        return todo
    pos = {k: i for i, k in enumerate(want)}
    front = sorted((it for it in todo if it["clave"] in pos), key=lambda it: pos[it["clave"]])
    if not front:
        return todo
    return front + [it for it in todo if it["clave"] not in pos]
