"""Review desk: routed forms wait here; a person types the value of the named field, the form's identities
re-check, and the form is marked resolved. Stored in a local JSON file (app/state/review.json), not a DB."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Optional

from app import store as storemod

FILE = storemod.STATE / "review.json"
_lock = threading.Lock()


def load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(d: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def queue(st: storemod.Store) -> list[dict]:
    """Routed forms of the default reader, with what the person has to look at."""
    done = load()
    out = []
    for k in st.ine_claves():
        r = st.default_read(k)
        if r is None:
            continue
        ev = storemod.evaluate(r)
        if ev["accepted"]:
            continue
        keys = list(dict.fromkeys(ev["failing"]))
        if not keys:  # identity-only: the fields that take part in the failing identity, smallest first
            bad = [i for i in ev["identities"] if i["ok"] is False]
            bad.sort(key=lambda i: len(i["keys"]))
            keys = list(dict.fromkeys(bad[0]["keys"])) if bad else []
        fmap = {f["key"]: f for f in ev["fields"]}
        rv = done.get(k)
        typed = (rv or {}).get("values", {})
        items = [{"code": fmap[x]["code"], "name": fmap[x]["name"], "n": fmap[x]["n"], "w": fmap[x]["w"],
                  "typed": typed.get(fmap[x]["code"], "")} for x in keys]
        out.append({"clave": k, "run": r.run_id, "line": ev["line"], "items": items, "reasons": ev["reasons"],
                    "has_labels_issue": any(f["status"] == "label" for f in ev["fields"]),
                    "has_image": st.masked_image(k) is not None, "review": rv})
    out.sort(key=lambda x: (not x["has_image"], x["clave"]))
    return out


def resolve(st: storemod.Store, clave: str, values: dict, action: str = "resolve", note: str = "",
            labels_confirmed: bool = False) -> dict:
    r = st.default_read(clave)
    if r is None:
        raise KeyError(clave)
    clean = {}  # by schema key (internal)
    for code, v in (values or {}).items():
        k = storemod.key_of(code)
        if k is None or v in (None, ""):
            continue
        iv = storemod.iv(v)
        if iv is None:
            raise ValueError(f"{storemod.name_of(k)}: '{v}' is not a whole number")
        clean[k] = iv
    ev = storemod.evaluate(r, overrides=clean, labels_confirmed=labels_confirmed)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if action == "escalate":
        status = "escalated"
    else:
        status = "resolved" if ev["accepted"] else "open"
    rec = {"status": status, "values": {storemod.code_of(k): v for k, v in clean.items()}, "note": (note or "")[:500], "at": now, "run": r.run_id,
           "recheck": {"accepted": ev["accepted"], "reasons": ev["reasons"], "line": ev["line"]},
           "labels_confirmed": bool(labels_confirmed)}
    with _lock:
        d = load()
        if status != "open":
            d[clave] = rec
            _save(d)
    return rec


def reset(clave: Optional[str] = None) -> None:
    with _lock:
        d = load()
        if clave is None:
            d = {}
        else:
            d.pop(clave, None)
        _save(d)
