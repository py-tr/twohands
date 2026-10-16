"""The live strip on Home: what the live audit on AMD has done so far, and the receipts the card rotates through.

    status() -> {forms_audited, disputes, certified_confirmed, updated_at, updated_min_ago, states_complete,
                 reader_model, latest_receipts[], kind, label}

The three numbers count every form read on AMD: the measured samples (samples(), from their computed summaries) plus
the live worker (app/live_audit.summary(), from twohands/worker.py's directory), disputes and certified-confirmed
fields summed the same way; twohands.eval recomputes the sum. Never invented numbers.

Receipts come from the pre-registered random 300 only (app/data/headline.json's keying_list), never the pilot and
never the live worker: capture errors whose paper value the certified count confirms ("certified count, by recount" /
"by comparison", INE's own Computos note), or a person's blind reading (app/state/spotcheck.json), or else labelled
"AI adjudicator, from the photo (person check pending)". Certified ones come first: 050815B0100 Option 07 (crisp
digits; keyed 75, paper 175, certified 175), then 070207C0100 TOTAL (faint pencil, shown "enhanced for display"; capture
"Ilegible", paper 416, certified 416); then 250767B0100 VOTARON and 080310B0100 SOBRANTES;
then the other certified fields, one per form. Vote rows are "Option NN"; crops never include the printed row label.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from app import caption as captionmod
from app import numbers as numbersmod
from app import stations as stationsmod
from app import store as storemod

DEFAULT_RECEIPT = ("050815B0100", "OPT07", 175, "75", 175)
# The rotation's named receipts, in order (all in results/manifest.json, the random 300). Values come from the data.
# 050815B0100 Option 07 leads: crisp digits 1 7 5, keyed 75, certified 175 (readable without Spanish). The faint-pencil
# 070207C0100 TOTAL is second, shown enhanced for display.
FEATURED = [("050815B0100", "OPT07"), ("070207C0100", "TOTAL"), ("250767B0100", "VOTARON"), ("080310B0100", "SOBRANTES")]
ENHANCED = {"070207C0100", "093831B0100"}     # the two faint pencil forms of the 52
CODE_ORDER = {"TOTAL": 0, "SACADOS": 1, "VOTARON": 2}
CONF_RANK = {"certified": 0, "person": 1, "ai": 2}
CERT_MODE = {"Recuento": "certified count, by recount", "Cotejo": "certified count, by comparison"}
AI_LABEL = "AI adjudicator, from the photo (person check pending)"
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


def _confirmation(x: dict, answers: dict, verdicts: dict) -> tuple[str, str]:
    """(kind, label) for one capture error of the 300: the certified count when it covers the field and agrees with the
    paper (INE's Computos note says recount or comparison), else a person's blind reading that agrees, else the AI
    adjudicator alone. Never "confirmed by a person" unless app/state/spotcheck.json says so."""
    if x.get("covered") and x.get("cert_agrees"):
        return "certified", CERT_MODE.get(x.get("cert_mode"), "certified count")
    k = f"{x['clave']}__{x['field']}"
    a, v = answers.get(k), verdicts.get(k)
    if a and v:
        from app import spotcheck
        if spotcheck.agrees(a, v):
            return "person", "confirmed by a person, blind, from the photo"
        return "ai", "AI adjudicator, from the photo (a person read it differently)"
    return "ai", AI_LABEL


def _measured_receipts(st: storemod.Store, answers: Optional[dict] = None, include_pilot: bool = False) -> list[dict]:
    """Capture errors of the pre-registered random 300 (app/data/headline.json's keying_list) with a readable paper
    value, each with its strongest confirmation. The pilot is never a source for Home; a station page of a pilot form
    (include_pilot=True) also lists its certified-confirmed pilot fields, labelled as the pilot."""
    from app import spotcheck
    answers = spotcheck.load() if answers is None else answers
    try:
        verdicts = spotcheck.load_verdicts()
    except (OSError, ValueError):
        verdicts = {}
    out, seen = [], set()
    for x in (numbersmod.headline() or {}).get("keying_list", []):
        p = _ival(x.get("paper"))
        if p is None or str(x.get("prep")).strip() == str(p):
            continue
        code = storemod.code_of(x["field"])
        if (x["clave"], code) in seen or st.masked_image(x["clave"]) is None:
            continue
        seen.add((x["clave"], code))
        kind, label = _confirmation(x, answers, verdicts)
        out.append({"clave": x["clave"], "code": code, "name": storemod.name_of(x["field"]), "paper": p,
                    "capture": str(x.get("prep")), "certified": _ival(x.get("certified")) if kind == "certified" else None,
                    "confirmation": kind, "conf_label": label, "state": stationsmod.state_name(x["clave"]),
                    "sample": "pre-registered random 300", "source": "measured",
                    "img": (f"/crop/enhanced/{x['clave']}/{code}.jpg?pad=0.012" if x["clave"] in ENHANCED
                            else f"/crop/{x['clave']}/{code}.jpg?pad=0.012&label=0"),
                    "enhanced": x["clave"] in ENHANCED, "caption": captionmod.caption(x["clave"], x["field"]),
                    "href": f"/station?c={x['clave']}", "verify": f"/verify/{x['clave']}/{code}"})
    if include_pilot:
        for clave, off in st.official.items():
            for key, paper in (off.get("adjudicated") or {}).items():
                cap, ce, p = (off.get("prep") or {}).get(key), _ival((off.get("cert") or {}).get(key)), _ival(paper)
                code = storemod.code_of(key)
                if (cap is None or p is None or ce != p or _ival(cap) == p or (clave, code) in seen
                        or st.masked_image(clave) is None):
                    continue
                seen.add((clave, code))
                mode = off.get("cert_mode")
                mode = mode.get(key) if isinstance(mode, dict) else mode
                out.append({"clave": clave, "code": code, "name": storemod.name_of(key), "paper": p, "capture": str(cap),
                            "certified": ce, "confirmation": "certified",
                            "conf_label": CERT_MODE.get(mode, "certified count") + " (pilot, 43 forms)",
                            "state": stationsmod.state_name(clave), "sample": "pilot, 43 forms", "source": "measured",
                            "img": f"/crop/{clave}/{code}.jpg?pad=0.012&label=0", "href": f"/station?c={clave}",
                            "verify": None})
    return out


def order_receipts(rs: list[dict], limit: int = 8) -> list[dict]:
    """The named receipts first (FEATURED, certified-confirmed before person- and AI-only ones), then the other
    certified ones, one per form, TOTAL, SACADOS and VOTARON before Option rows."""
    named = {key: i for i, key in enumerate(FEATURED)}
    first = [r for r in rs if (r["clave"], r["code"]) in named]
    first.sort(key=lambda r: (CONF_RANK[r["confirmation"]], named[(r["clave"], r["code"])]))
    rest, forms = [], {r["clave"] for r in first}
    for r in sorted((r for r in rs if r not in first and r["confirmation"] != "ai"),
                    key=lambda r: (CONF_RANK[r["confirmation"]], _field_order(r["code"]), r["clave"], r["code"])):
        if r["clave"] not in forms:
            forms.add(r["clave"])
            rest.append(r)
    return (first + rest)[:limit]


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
