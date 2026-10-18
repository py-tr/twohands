"""The sheet page's story (/form/<clave>): the stored AMD read with its run metadata, one verdict sentence, the
official-capture line kept apart from it, the disputed fields of the sample audit with their crop and decision, and
the receipt check. Everything comes from stored data: the read (app/store.py), results/adjudication/verdicts.json and
certified.json (the 267 disputes of the 300), app/data/headline.json, and the sample audit's Merkle receipts."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Optional

from app import store as storemod
from twohands import REPO

ADJ = REPO / "results" / "adjudication"
ROOT_FILE = REPO / "results" / "sample_audit_root.txt"
REPO_URL = "https://github.com/py-tr/twohands"   # submission/links.json "repo" wins when filled
# The pilot's reads (spike runs) were made on 2026-10-14 (docs/sources/tally-witness-pilot.md, "Tally Witness: spike")
PILOT_DATE = "2026-10-14"
IDENT_SAY = {"rows sum to TOTAL": ("Rows sum to {l}", "TOTAL says {r}"),
             "votaron + representantes = section 5": ("Voters plus representatives give {l}", "section 5 says {r}"),
             "section 5 = section 7": ("Section 5 says {l}", "section 7 says {r}"),
             "section 7 = TOTAL": ("Section 7 says {l}", "TOTAL says {r}")}
VERDICT_SAY = {"model_right": "the official capture does not match the paper",
               "capture_right": "Gemma misread it; the official capture matches the paper",
               "neither": "neither matches the paper", "paper_ambiguous": "the paper itself is ambiguous",
               "unreadable": "the field cannot be read on the photo", "crop_wrong": "the crop must be redone"}
CERT_MODE = {"Cotejo": "by comparison", "Recuento": "by recount"}


def repo_url() -> str:
    from app import links
    return links.load().get("repo") or REPO_URL


def run_meta(s: storemod.Store, r: storemod.Read) -> dict:
    """Measured on AMD: model, date, seconds and cost of the stored read."""
    run = s.runs.get(r.run_id, {})
    ts = (r.raw or {}).get("ts") or ""
    date = ts[:10] if ts else (PILOT_DATE if str(run.get("kind")) == "spike" else None)
    return {"model": (r.raw or {}).get("model") or run.get("model") or "Gemma-4-31B-IT", "date": date,
            "secs": r.secs, "cost": r.cost}


def verdict(ev: dict) -> dict:
    """One sentence: accepted, or the first broken check in plain numbers."""
    if ev.get("accepted"):
        return {"ok": True, "line": "Every check holds: accepted, nothing to key"}
    bad = [i for i in ev.get("identities", []) if i.get("ok") is False]
    if bad:
        i = bad[0]
        a, b = IDENT_SAY.get(i["name"], (i["name"] + ": {l}", "expected {r}"))
        return {"ok": False, "line": f"{a.format(l=i['lhs'])}, {b.format(r=i['rhs'])}: this field goes to a person, "
                                     f"with its photo"}
    f = next((f for f in ev.get("fields", []) if f.get("status") != "ok"), None)
    if f:
        return {"ok": False, "line": f"{f['name']}: {f.get('msg') or 'not consistent'}: this field goes to a person, "
                                     f"with its photo"}
    return {"ok": False, "line": storemod.neutralize(ev.get("line", "Routed to a person"))}


@lru_cache(maxsize=1)
def _adjudication() -> tuple[dict, dict]:
    v = json.loads((ADJ / "verdicts.json").read_text(encoding="utf-8"))
    c = json.loads((ADJ / "certified.json").read_text(encoding="utf-8"))
    cert = {(x["clave"], x["field"]): x for lst in c.values() if isinstance(lst, list) for x in lst}
    return v, cert


@lru_cache(maxsize=1)
def _keyed() -> dict:
    """The sample's keyed file (the official first capture of the 300), {clave: {field key: value}}."""
    from app import capture_audit as ca
    headers, rows = ca.parse_csv(ca.SAMPLE_CSV.read_text(encoding="utf-8"))
    m = ca.automap(headers)
    out = {}
    for row in rows:
        if m["id"] is None or len(row) <= m["id"]:
            continue
        fid = row[m["id"]].strip().strip("'")
        out[fid] = {storemod.key_of(code): row[i].strip() for code, i in m["fields"].items()
                    if i is not None and i < len(row) and storemod.key_of(code)}
    return out


def capture_lines(s: storemod.Store, clave: str) -> list[dict]:
    """Where the official typed record (PREP) disagrees with the paper: the pre-registered 300 (headline.json), and the
    pilot's eye-checked capture errors."""
    from app import numbers as numbersmod
    out, seen = [], set()
    for x in (numbersmod.headline() or {}).get("keying_list", []):
        if x["clave"] != clave or not isinstance(x.get("paper"), int) or str(x.get("prep")).strip() == str(x["paper"]):
            continue
        seen.add(x["field"])
        out.append({"code": storemod.code_of(x["field"]), "name": storemod.name_of(x["field"]), "keyed": x["prep"],
                    "paper": x["paper"], "certified": x.get("certified") if x.get("cert_agrees") else None})
    for e in s.keying_errors():
        if e["clave"] == clave and e.get("kind") == "keying" and e["field"] not in seen:
            out.append({"code": e["code"], "name": e["name"], "keyed": e["official"], "paper": e["image_value"],
                        "certified": e.get("certified") if e.get("cert_agrees") else None})
    return out


def _decision(clave: str, key: str, cert: Optional[dict], review: Optional[dict]) -> str:
    if review and review.get("status"):
        return f"review desk: {review['status']}"
    if cert and cert.get("covered") and cert.get("agrees"):
        mode = next((v for k, v in CERT_MODE.items() if str(cert.get("obs", "")).startswith(k)), None)
        return "confirmed by the certified count" + (f", {mode}" if mode else "")
    from app import live_status as LS
    from app import spotcheck
    try:
        a, v = spotcheck.load().get(f"{clave}__{key}"), spotcheck.load_verdicts().get(f"{clave}__{key}")
        if a and v and spotcheck.agrees(a, v):
            return "confirmed by a person, blind, from the photo"
    except (OSError, ValueError):
        pass
    return LS.AI_LABEL


def disputes(s: storemod.Store, clave: str, r: storemod.Read, ev: dict, review: Optional[dict] = None) -> list[dict]:
    """This sheet's disputed fields in the sample audit of the 300 (the model's read vs the official capture), each with
    its crop, the decision on the photo, a what-if on the broken check, and its receipt route."""
    V, C = _adjudication()
    keyed = _keyed().get(clave, {})
    bad = [i for i in ev.get("identities", []) if i.get("ok") is False]
    out = []
    for v in V.values():
        if v.get("form_id") != clave:
            continue
        key, code = v["field"], storemod.code_of(v["field"])
        cert = C.get((clave, key))
        model = r.values.get(key)
        paper = v.get("paper") if isinstance(v.get("paper"), int) else None
        whatif = None
        if paper is not None and model is not None and len(bad) == 1:
            d, i = paper - model, bad[0]
            if d and (i["lhs"] + d == i["rhs"] or i["rhs"] + d == i["lhs"]):
                n = max(i["lhs"], i["rhs"]) if d > 0 else min(i["lhs"], i["rhs"])
                whatif = f"With the paper's {paper}, {i['name']} gives {n} = {n}."
        out.append({"key": key, "code": code, "name": storemod.name_of(key), "model": model, "words": r.words.get(key),
                    "keyed": (cert or {}).get("prep") or keyed.get(key), "paper": v.get("paper"),
                    "verdict": VERDICT_SAY.get(v.get("verdict"), v.get("verdict")),
                    "model_wrong": v.get("verdict") != "model_right",
                    "decision": _decision(clave, key, cert, review), "whatif": whatif,
                    "crop": f"/crop/{clave}/{code}.jpg?pad=0.02&label=0" if s.masked_image(clave) else None,
                    "verify": f"/verify/{clave}/{code}", "check": f"/api/receipt/{clave}/{code}"})
    out.sort(key=lambda d: (not d["model_wrong"], d["code"]))
    return out


_checked: dict = {}


def receipt_check(clave: str, code: str) -> Optional[dict]:
    """Verify one field's receipt in the sample audit as python -m twohands.verify_receipt does: the leaf from its
    record, the crop's SHA-256, the proof path to the root, and the root against results/sample_audit_root.txt."""
    from app import audit_web
    from app import capture_audit as ca
    from twohands import verify_receipt as vr
    key = storemod.key_of(code)
    if key is None:
        return None
    aid = audit_web._sample_audit_id()
    if (aid, clave, code) in _checked:
        return _checked[(aid, clave, code)]
    a = ca.load(aid)
    if a is None:
        return None
    R = ca.run(a)
    k = next((k for k in (f"{clave}__{code}", f"{clave}__{key}") if any(d["key"] == k for d in R["disputes"])), None)
    if k is None:
        return None
    d = next(d for d in R["disputes"] if d["key"] == k)
    rc = ca.receipt(a, R, k)
    if rc is None:
        return None
    root = ROOT_FILE.read_text(encoding="utf-8").split()[0]
    checks = vr.check(rc, ca.crop_of(a, d), root)
    out = {"form": clave, "field": code, "root": rc["root"], "n_leaves": rc.get("n_leaves"),
           "checks": [{"label": lab, "ok": ok, "hash": h[:16]} for lab, ok, h in checks],
           "verified": all(ok for _, ok, _ in checks), "receipt": f"/verify/{clave}/{code}"}
    _checked[(aid, clave, code)] = out
    return out
