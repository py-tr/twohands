"""The live strip on Home: what the live audit on AMD has done so far, and the receipts the card rotates through.

    status() -> {forms_audited, disputes, certified_confirmed, updated_at, updated_min_ago, states_complete,
                 reader_model, latest_receipts[], kind, label}

The three numbers count every form read on AMD: the measured samples (samples(), from their computed summaries) plus
the live worker (app/live_audit.summary(), from twohands/worker.py's directory), disputes and certified-confirmed
fields summed the same way; twohands.eval recomputes the sum. Never invented numbers.

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


def samples() -> list[dict]:
    """The measured samples the strip counts, each from its computed summary. Today the pre-registered 300
    (app/data/headline.json); a further run (confirmation, Senate, ...) joins here once it has a computed summary with
    forms, disputes and certified-confirmed fields."""
    H = numbersmod.headline() or {}
    out = []
    if H:
        out.append({"name": "pre-registered sample", "forms": H["forms"], "disputes": H["disagree"],
                    "confirmed": H["cert_agree"], "reader": READER_MEASURED})
    return out


def live_part() -> Optional[dict]:
    """The live worker's share: forms audited, disputes, certified-confirmed, since when, updated when."""
    v = _summary()
    if not v or not v.get("audited"):
        return None
    try:
        from app import stations
        first = min((r["ts"] for r in stations.all_live_rows().values() if r.get("status") == "audited"), default=None)
    except Exception:  # noqa: BLE001
        first = None
    states = v.get("states") or []
    done = [s["name"] for s in states if s.get("complete")]
    cur = next((s for s in states if not s.get("complete")), None)
    return {"forms": v["audited"], "disputes": v["disputes"], "confirmed": v["confirmed"], "since": first,
            "since_text": _day(first), "updated_at": v.get("updated"), "updated_min_ago": _ago(v.get("updated")),
            "reader": v.get("reader_now") or (v.get("readers") or [None])[-1],
            "running": (v.get("status") or {}).get("kind") == "live", "status": v.get("status"),
            "states_complete": (f"{len(done)} of {v.get('queue_states') or 32} states complete"
                                + (f", {cur['name']} {cur['pct']:g}%" if cur else "")), "v": v}


def _day(ts: Optional[str]) -> Optional[str]:
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None
    return f"{d.day} {d.strftime('%b')}"


def status(st: Optional[storemod.Store] = None) -> dict:
    """The strip: every form read on AMD, across the measured samples and the live worker, with disputes and
    certified-confirmed fields summed the same way."""
    st = st or storemod.get_store()
    S = samples()
    L = live_part()
    parts = S + ([{"name": "live", **{k: L[k] for k in ("forms", "disputes", "confirmed")}}] if L else [])
    readers = []
    for s in S:
        readers.append(f"{s['reader']} (sample)")
    if L and L["reader"]:
        readers.append(f"{L['reader']} (live)")
    rs = _measured_receipts(st)
    if L:
        rs = _live_receipts(L["v"]) + rs
    return {"kind": "live" if L else "measured", "label": "measured sample and live audit" if L else "measured sample",
            "forms_audited": sum(x["forms"] for x in parts), "disputes": sum(x["disputes"] for x in parts),
            "certified_confirmed": sum(x["confirmed"] for x in parts), "parts": parts, "samples": S,
            "live": {k: L[k] for k in L if k != "v"} if L else None,
            "updated_at": L["updated_at"] if L else None, "updated_min_ago": L["updated_min_ago"] if L else None,
            "states_complete": L["states_complete"] if L else None, "reader_model": ", ".join(readers),
            "running": bool(L and L["running"]), "latest_receipts": order_receipts(rs)}


def public(s: dict) -> dict:
    return storemod.public({k: s[k] for k in ("kind", "label", "forms_audited", "disputes", "certified_confirmed",
                                              "parts", "live", "updated_at", "updated_min_ago", "states_complete",
                                              "reader_model", "running", "latest_receipts")})
