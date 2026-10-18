"""Budgets and pacing for the one shared AMD Token Factory key: who may spend what, and how fast.

The key's daily cap (TWOHANDS_KEY_DAILY_USD, $1.00; it resets at 16:00 UTC) is split by role:

    role     share   who                                                     enforced where
    worker   $0.60   the live audit worker (twohands/worker.py)              worker.Budget: own spend today >= share
    bulk     $0.30   anything launched by twohands.run, scripts/             amd.chat: before each request, the role's
                     confirm_read.py                                         spend today (spend ledger) >= share ->
                     (every amd.chat call that is not worker or live)        sleep until the reset (+3 min)
    live     $0.10   the site's live-read button (app/live.py)               LiveManager.check_budget: its own daily
                                                                             dollars (LIVE_MAX_USD_PER_DAY) >= share
                                                                             -> refused; the worker keeps the live
                                                                             share as its reserve (RESERVE_USD)

Every answered request's cost (usage.cost) is appended to the spend ledger (cache/spend.jsonl, or TWOHANDS_SPEND_FILE)
with its role and budget day, so separate bulk processes (a run, then the next in a chain) share the bulk share.
Rows written while pytest runs (PYTEST_CURRENT_TEST set) carry ``"test": true`` and are never counted, and rows listed
in the quarantine file next to the ledger (<ledger>.quarantine.jsonl: a ``note`` line, then the quarantined rows
verbatim) are skipped too; the ledger itself is append-only and never rewritten (scripts/quarantine_spend.py).

Pacing (twohands/ratelimit.py, cross-process): TWOHANDS_RPM total request starts per minute (16) of which
TWOHANDS_LIVE_RPM (4) are always reserved for live reads: worker and bulk processes start at most RPM - LIVE_RPM
(12) a minute between them; a live read may take its own lane or any free slot.

Env overrides: TWOHANDS_KEY_DAILY_USD, TWOHANDS_WORKER_DAILY_USD, TWOHANDS_BULK_DAILY_USD, LIVE_MAX_USD_PER_DAY,
TWOHANDS_RPM, TWOHANDS_LIVE_RPM, TWOHANDS_SPEND_FILE.
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

RESET_HOUR_UTC = 16
KEY_DAILY_USD = float(os.environ.get("TWOHANDS_KEY_DAILY_USD", "1.00"))
SHARES = {"worker": float(os.environ.get("TWOHANDS_WORKER_DAILY_USD", "0.60")),
          "bulk": float(os.environ.get("TWOHANDS_BULK_DAILY_USD", "0.30")),
          "live": float(os.environ.get("LIVE_MAX_USD_PER_DAY", "0.10"))}
RPM_TOTAL = float(os.environ.get("TWOHANDS_RPM", "16"))
LIVE_RPM = float(os.environ.get("TWOHANDS_LIVE_RPM", "4"))
_lock = threading.Lock()


def share(role: str) -> float:
    return SHARES[role]


def role_of(kind: str) -> str:
    """amd.chat's ``kind`` -> the budget role: 'live' and 'worker' are themselves; every other call is a bulk run."""
    return kind if kind in ("live", "worker") else "bulk"


def budget_day(now: Optional[datetime] = None) -> str:
    """The budget window a moment belongs to (16:00 UTC to 16:00 UTC), named by its start date."""
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(hours=RESET_HOUR_UTC)).strftime("%Y-%m-%d")


def next_reset(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    r = now.replace(hour=RESET_HOUR_UTC, minute=0, second=0, microsecond=0)
    return r if r > now else r + timedelta(days=1)


def spend_file() -> Path:
    p = os.environ.get("TWOHANDS_SPEND_FILE")
    return Path(p) if p else Path(__file__).resolve().parent.parent / "cache" / "spend.jsonl"


def record(role: str, usd, now: Optional[datetime] = None) -> None:
    """Append one answered request's cost to the spend ledger (never raises; zero or missing costs are skipped)."""
    try:
        usd = float(usd or 0)
    except (TypeError, ValueError):
        return
    if usd <= 0:
        return
    row = {"day": budget_day(now), "role": role, "usd": round(usd, 8), "ts": time.time(), "pid": os.getpid()}
    if os.environ.get("PYTEST_CURRENT_TEST"):
        row["test"] = True   # a fake cost from a test: never counted, even if it reaches the real ledger
    try:
        f = spend_file()
        f.parent.mkdir(parents=True, exist_ok=True)
        with _lock, open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass


def quarantine_file(ledger: Optional[Path] = None) -> Path:
    f = ledger or spend_file()
    return f.with_name(f.stem + ".quarantine.jsonl")


def row_key(r: dict) -> tuple:
    """Identity of a ledger row (pid, ts, role, usd): what the quarantine file matches on."""
    return (r.get("pid"), r.get("ts"), r.get("role"), r.get("usd"))


def quarantined(ledger: Optional[Path] = None) -> set:
    try:
        lines = quarantine_file(ledger).read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    out = set()
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if "note" not in r:
            out.add(row_key(r))
    return out


def spent(role: str, now: Optional[datetime] = None) -> float:
    """The role's spend in the current budget day, from the ledger (a half-written line is skipped; test rows and
    quarantined rows are not counted)."""
    day, tot = budget_day(now), 0.0
    try:
        lines = spend_file().read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0.0
    skip = quarantined()
    for line in lines:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("test") or row_key(r) in skip:
            continue
        if r.get("day") == day and r.get("role") == role:
            tot += float(r.get("usd") or 0)
    return tot


def over(role: str, now: Optional[datetime] = None) -> bool:
    return spent(role, now) >= share(role)


def wait_for_share(role: str = "bulk", log: Callable[[str], None] = print,
                   sleep: Callable[[float], None] = time.sleep, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> float:
    """Block while the role has spent its share today: sleep until the reset + 3 min. Returns seconds slept."""
    slept = 0.0
    while over(role, now()):
        t = now()
        wait = max(60.0, (next_reset(t) - t).total_seconds() + 180)
        log(f"{role} spend today {spent(role, t):.3f} >= its {share(role):.2f} USD share: sleeping {wait / 3600:.1f} h "
            f"until after the 16:00 UTC reset")
        sleep(wait)
        slept += wait
    return slept
