"""The live strip on Home: what the live audit on AMD has done so far, and the receipts the card rotates through.

    status() -> {forms_audited, disputes, certified_confirmed, updated_at, updated_min_ago, states_complete,
                 reader_model, latest_receipts[], kind, label}

kind "live": the worker's numbers (app/live_audit.summary(), from twohands/worker.py's directory).
kind "measured": until the worker has audited a form, the measured 300-form sample (app/data/headline.json), labelled
"measured sample". Never invented numbers.

Receipts are disputes the certified count confirmed (paper == certified != first capture), on any measured sample or
the live audit. The first is 202451B0100 TOTAL when our data has it as paper 271 / capture 272 / certified 271; then
TOTAL, SACADOS and VOTARON before any Option row. Vote rows are "Option NN"; crops never include the printed row label.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from app import numbers as numbersmod
from app import stations as stationsmod
from app import store as storemod

DEFAULT_RECEIPT = ("202451B0100", "TOTAL", 271, 272, 271)
CODE_ORDER = {"TOTAL": 0, "SACADOS": 1, "VOTARON": 2}
READER_MEASURED = "Gemma-4-31B-IT"


def _ival(x) -> Optional[int]:
    try:
        return int(str(x).strip())
    except (TypeError, ValueError):
        return None


def _field_order(code: str) -> int:
    if code in CODE_ORDER:
        return CODE_ORDER[code]
    return 9 if code.startswith("OPT") else 5


def _measured_receipts(st: storemod.Store) -> list[dict]:
    """Certified-confirmed capture errors in our measured samples: the pilot's adjudicated fields (app/data/official.json)
    and the 300 run's capture errors (app/data/headline.json)."""
    out, seen = [], set()

    def add(clave, key, paper, capture, certified, sample):
        p, c, ce = _ival(paper), capture, _ival(certified)
        if p is None or ce is None or p != ce or str(capture).strip() == str(p):
            return
        code = storemod.code_of(key)
        if (clave, code) in seen or st.masked_image(clave) is None:
            return
        seen.add((clave, code))
        out.append({"clave": clave, "code": code, "name": storemod.name_of(key), "paper": p, "capture": str(c),
                    "certified": ce, "state": stationsmod.state_name(clave), "sample": sample, "source": "measured",
                    "img": f"/crop/{clave}/{code}.jpg?pad=0.012&label=0", "href": f"/station?c={clave}"})

    for clave, off in st.official.items():
        for key, paper in (off.get("adjudicated") or {}).items():
            cap = (off.get("prep") or {}).get(key)
            if cap is not None and _ival(cap) != _ival(paper):
                add(clave, key, paper, cap, (off.get("cert") or {}).get(key), "pilot, 43 forms")
    for x in (numbersmod.headline() or {}).get("keying_list", []):
        if x.get("covered"):
            add(x["clave"], x["field"], x.get("paper"), x.get("prep"), x.get("certified"), "pre-registered 300")
    return out


def _live_receipts(v: dict) -> list[dict]:
    out = []
    for d in v.get("recent") or []:
        if d.get("label") != "confirmed":
            continue
        out.append({"clave": d["clave"], "code": d["code"], "name": d["name"], "paper": d["paper"],
                    "capture": str(d["capture"]), "certified": d["certified"], "state": d.get("state"),
                    "sample": "live audit", "source": "live", "img": d["crop"], "href": f"/station?c={d['clave']}",
                    "reader": d.get("reader")})
    return out


def order_receipts(rs: list[dict]) -> list[dict]:
    """The default receipt first (when present with its expected values), then TOTAL, SACADOS, VOTARON before other
    fields and Option rows last; live receipts before measured ones of the same field order."""
    first = [r for r in rs if (r["clave"], r["code"], r["paper"], _ival(r["capture"]), r["certified"]) == DEFAULT_RECEIPT]
    rest = [r for r in rs if r not in first]
    rest.sort(key=lambda r: (_field_order(r["code"]), r["source"] != "live", r["clave"]))
    return first + rest


def _ago(ts: Optional[str]) -> Optional[int]:
    if not ts:
        return None
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp()
    except ValueError:
        return None
    return max(0, int((time.time() - t) // 60))


def _summary() -> Optional[dict]:
    try:
        from app import live_audit
        return live_audit.summary()
    except Exception:  # noqa: BLE001 - the strip must never break Home
        return None


def status(st: Optional[storemod.Store] = None) -> dict:
    st = st or storemod.get_store()
    v = _summary()
    measured = _measured_receipts(st)
    if v and v.get("audited"):
        states = v.get("states") or []
        done = [s["name"] for s in states if s.get("complete")]
        cur = next((s for s in states if not s.get("complete")), None)
        sc = (f"{len(done)} of {v.get('queue_states') or 32} states complete"
              + (f", {cur['name']} {cur['pct']:g}%" if cur else ""))
        return {"kind": "live", "label": "live audit", "forms_audited": v["audited"], "disputes": v["disputes"],
                "certified_confirmed": v["confirmed"], "updated_at": v.get("updated"),
                "updated_min_ago": _ago(v.get("updated")), "states_complete": sc,
                "reader_model": v.get("reader_now") or (v.get("readers") or [None])[-1],
                "running": (v.get("status") or {}).get("kind") == "live", "status": v.get("status"),
                "latest_receipts": order_receipts(_live_receipts(v) + measured)}
    H = numbersmod.headline() or {}
    return {"kind": "measured", "label": "measured sample", "forms_audited": H.get("read", 0),
            "disputes": H.get("disagree", 0), "certified_confirmed": H.get("cert_agree", 0),
            "certified_covered": H.get("cert_covered", 0), "forms_drawn": H.get("forms", 0),
            "updated_at": None, "updated_min_ago": None,
            "states_complete": f"pre-registered random sample of {H.get('forms', 0)} forms", "reader_model": READER_MEASURED,
            "running": False, "status": (v or {}).get("status"), "latest_receipts": order_receipts(measured)}


def public(s: dict) -> dict:
    return storemod.public({k: s[k] for k in ("kind", "label", "forms_audited", "disputes", "certified_confirmed",
                                              "updated_at", "updated_min_ago", "states_complete", "reader_model",
                                              "running", "latest_receipts")})
