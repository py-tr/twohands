"""Request an audit (/audit/request): a short form, stored in app/state/requests.jsonl, a confirmation with a request id.

The operator is emailed ONLY when SMTP_HOST, SMTP_USER, SMTP_PASS and NOTIFY_TO are all set (SMTP_PORT optional:
587 with STARTTLS, 465 with TLS). Their values are never logged or stored; a failed send records only the error
class. Without them the request is stored and the page says "received". No payment is taken.

Spam guard: a honeypot field (hidden from people; a filled one gets the normal confirmation and nothing is stored)
and a per-IP limit (RATE_N requests per RATE_WINDOW_S seconds).
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import secrets
import smtplib
import ssl
import threading
import time
from datetime import date, datetime, timezone
from email.message import EmailMessage
from typing import Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app import numbers as numbersmod
from app import pricing as pricingmod
from app import store as storemod

router = APIRouter()
log = logging.getLogger("twohands.request")

REQUESTS = storemod.STATE / "requests.jsonl"
PRICE_PER_FORM = pricingmod.PRICE_PER_FORM_USD    # $1 per sheet audited (app/pricing.py, the one config value)
TURNAROUND = "report within 24 hours"
RATE_N, RATE_WINDOW_S = 5, 3600
MAX_FORMS = 10_000_000
MAX_BODY = 16 * 1024
SMTP_VARS = ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "NOTIFY_TO")
BACKGROUND = True          # tests set False to send in-line
HONEYPOT = "website"

FORM_TYPES = (("tally", "Tally sheets (hand-filled count forms)"), ("senate", "Senate tally sheets"),
              ("receipts", "Printed receipts"), ("other", "Another paper form"))
WHERE = (("upload", "I will upload them (keyed CSV + ZIP of scans; scans are masked on arrival)"),
         ("link", "They are at a link (shared folder or download)"))
_EMAIL = re.compile(r"^[^@\s<>,;\"']{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,24}$")
_URL = re.compile(r"^https?://[^\s<>\"']{3,500}$")
_RID = re.compile(r"^R-\d{8}-[0-9a-f]{6}$")
_lock = threading.Lock()
_hits: dict[str, list[float]] = {}


def _t():
    from app.main import templates
    return templates


def price(forms: int) -> int:
    """$ for a request of `forms` forms: PRICE_PER_FORM per form, rounded up to the dollar."""
    return pricingmod.quote(forms)


def smtp_configured() -> bool:
    return all(os.environ.get(k) for k in SMTP_VARS)


def allow(ip: str, now: Optional[float] = None) -> bool:
    """Per-IP limit: at most RATE_N accepted submissions in any RATE_WINDOW_S seconds."""
    now = time.time() if now is None else now
    with _lock:
        h = [t for t in _hits.get(ip, []) if now - t < RATE_WINDOW_S]
        if len(h) >= RATE_N:
            _hits[ip] = h
            return False
        h.append(now)
        _hits[ip] = h
        if len(_hits) > 10_000:  # bounded memory
            for k in [k for k, v in _hits.items() if not v or now - v[-1] >= RATE_WINDOW_S]:
                _hits.pop(k, None)
        return True


def _one_line(s: str, n: int) -> str:
    return re.sub(r"[\r\n\t]+", " ", (s or "").strip())[:n]


def validate(f: dict) -> tuple[dict, dict]:
    """The form fields -> (clean record, errors by field)."""
    err = {}
    org = _one_line(f.get("org", ""), 200)
    if len(org) < 2:
        err["org"] = "Name the organisation."
    email = _one_line(f.get("email", ""), 254)
    if not _EMAIL.match(email):
        err["email"] = "Enter an email address I can reply to."
    raw = re.sub(r"[\s,._]", "", f.get("forms", ""))
    forms = int(raw) if raw.isdigit() else 0
    if not 1 <= forms <= MAX_FORMS:
        err["forms"] = f"Enter the number of forms (1 to {MAX_FORMS:,})."
    ftype = f.get("form_type", "")
    if ftype not in dict(FORM_TYPES):
        err["form_type"] = "Choose the form type."
    where = f.get("where", "")
    link = _one_line(f.get("link", ""), 500)
    if where not in dict(WHERE):
        err["where"] = "Say where the capture and scans are."
    elif where == "link" and not _URL.match(link):
        err["link"] = "Paste the link (https://...)."
    try:
        deadline = date.fromisoformat(f.get("deadline", ""))
        if deadline < datetime.now(timezone.utc).date():
            err["deadline"] = "The deadline is in the past."
    except ValueError:
        deadline = None
        err["deadline"] = "Choose a deadline."
    notes = (f.get("notes") or "").strip()[:1000]
    rec = {"org": org, "email": email, "forms": forms, "form_type": ftype, "where": where,
           "link": link if where == "link" else "", "deadline": deadline.isoformat() if deadline else "",
           "notes": notes}
    return rec, err


def store(rec: dict) -> None:
    REQUESTS.parent.mkdir(parents=True, exist_ok=True)
    with _lock, REQUESTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load(rid: str) -> Optional[dict]:
    if not _RID.match(rid or ""):
        return None
    try:
        lines = REQUESTS.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for ln in reversed(lines):
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("id") == rid:
            return r
    return None


def message(rec: dict) -> EmailMessage:
    m = EmailMessage()
    m["Subject"] = f"Two Hands audit request {rec['id']}: {rec['forms']:,} forms, {rec['org']}"[:200]
    m["From"] = os.environ["SMTP_USER"]
    m["To"] = os.environ["NOTIFY_TO"]
    m["Reply-To"] = rec["email"]
    m.set_content("\n".join([
        f"Request {rec['id']} received {rec['at']}",
        f"Organisation: {rec['org']}", f"Contact: {rec['email']}",
        f"Forms: {rec['forms']:,} ({dict(FORM_TYPES)[rec['form_type']]})",
        f"Capture and scans: {dict(WHERE)[rec['where']]}" + (f" {rec['link']}" if rec["link"] else ""),
        f"Deadline: {rec['deadline']}", f"Quoted: ${rec['price_usd']:,} ({TURNAROUND})", "",
        rec["notes"] or "(no notes)"]))
    return m


def send(rec: dict) -> None:
    """Email the operator. Never logs the SMTP settings; on failure logs only the error class."""
    host, port = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT") or 587)
    try:
        ctx = ssl.create_default_context()
        if port == 465:
            s = smtplib.SMTP_SSL(host, port, timeout=15, context=ctx)
        else:
            s = smtplib.SMTP(host, port, timeout=15)
            s.starttls(context=ctx)
        with s:
            s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
            s.send_message(message(rec))
        log.info("audit request %s: operator notified", rec["id"])
    except Exception as e:  # noqa: BLE001 - the request is already stored
        log.warning("audit request %s: notification failed (%s)", rec["id"], type(e).__name__)


def notify(rec: dict) -> bool:
    if not smtp_configured():
        return False
    if BACKGROUND:
        threading.Thread(target=send, args=(rec,), daemon=True).start()
    else:
        send(rec)
    return True


def _ctx(**kw) -> dict:
    return {"nav": "auditnew", "FORM_TYPES": FORM_TYPES, "WHERE": WHERE, "PRICE": PRICE_PER_FORM, "PT": pricingmod.texts(),
            "TURNAROUND": TURNAROUND, "today": datetime.now(timezone.utc).date().isoformat(), **kw}


@router.get("/audit/request", response_class=HTMLResponse)
def request_form(request: Request):
    return _t().TemplateResponse(request, "audit_request.html", _ctx(f={}, err={}))


@router.post("/audit/request", response_class=HTMLResponse)
async def request_submit(request: Request):
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(413, "too large")
    f = {k: v[0] for k, v in parse_qs(body.decode("utf-8", "replace"), keep_blank_values=True).items()}
    if f.get(HONEYPOT):  # a bot: the usual confirmation, nothing stored, nobody emailed
        fake = {"id": f"R-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(3)}", "forms": 0}
        return _t().TemplateResponse(request, "audit_request.html", _ctx(done=fake, notified=False))
    rec, err = validate(f)
    if err:
        return _t().TemplateResponse(request, "audit_request.html", _ctx(f=f, err=err), status_code=422)
    ip = request.client.host if request.client else "?"
    if not allow(ip):
        return _t().TemplateResponse(request, "audit_request.html",
                                     _ctx(f=f, err={"_": "Too many requests from this address; try again in an hour, "
                                                         "or write to me."}), status_code=429)
    now = datetime.now(timezone.utc)
    rec = {"id": f"R-{now:%Y%m%d}-{secrets.token_hex(3)}", "at": now.isoformat(timespec="seconds"), **rec,
           "price_usd": price(rec["forms"]), "price_basis": pricingmod.texts()["price"],
           "turnaround": TURNAROUND, "status": "received"}
    store(rec)
    notified = notify(rec)
    return _t().TemplateResponse(request, "audit_request.html", _ctx(done=rec, notified=notified))

