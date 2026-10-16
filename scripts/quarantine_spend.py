"""Quarantine fake test rows in the spend ledger WITHOUT rewriting it (twohands/budgets.py).

    python scripts/quarantine_spend.py            # dry run: list what would be quarantined
    python scripts/quarantine_spend.py --apply    # append them to <ledger>.quarantine.jsonl

The ledger (cache/spend.jsonl, or TWOHANDS_SPEND_FILE) is append-only and live processes append to it, so it is never
rewritten here. Instead, the selected rows are copied verbatim into the quarantine file next to it, after a ``note``
line, and budgets.spent() skips every row listed there. Undo = delete the quarantine file.

Selection (deliberately narrow; the 2026-10-16 incident): rows of ONE process id whose every row costs exactly the given
amount (a fake per-call cost from a test double, e.g. tests/test_orchestrate.py's 0.001), within a given time window.
A real process's costs vary call to call, so a pid with a constant cost over hundreds of rows is not a real reader.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import budgets  # noqa: E402


def select(rows: list[dict], pid: int, usd: float, t0: float, t1: float) -> list[dict]:
    mine = [r for r in rows if r.get("pid") == pid]
    if not mine or any(r.get("usd") != usd for r in mine):
        raise SystemExit(f"pid {pid}: not every row costs exactly {usd}; refusing (this is not the fake-cost pattern)")
    return [r for r in mine if t0 <= float(r.get("ts") or 0) <= t1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, default=60888)
    ap.add_argument("--usd", type=float, default=0.001)
    ap.add_argument("--from-ts", type=float, default=1792142700.0)   # 2026-10-16 09:25:00 UTC
    ap.add_argument("--to-ts", type=float, default=1792142760.0)     # 2026-10-16 09:26:00 UTC
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    led = budgets.spend_file()
    rows = []
    for line in led.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    sel = select(rows, a.pid, a.usd, a.from_ts, a.to_ts)
    have = budgets.quarantined(led)
    new = [r for r in sel if budgets.row_key(r) not in have]
    days = sorted({r["day"] for r in sel})
    print(f"ledger {led}: {len(rows)} rows; selected {len(sel)} (pid {a.pid}, usd {a.usd} each, "
          f"sum {sum(r['usd'] for r in sel):.3f}, budget days {days}); {len(new)} not yet quarantined")
    for role in ("bulk", "worker", "live"):
        print(f"  {role} spent today now: {budgets.spent(role):.6f}")
    if not a.apply or not new:
        print("dry run" if not a.apply else "nothing to add")
        return 0
    q = budgets.quarantine_file(led)
    note = {"note": f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}: {len(new)} fake rows from a pytest run "
                    f"(pid {a.pid}, every row ${a.usd}: the test double's usage.cost in tests/test_orchestrate.py) written "
                    "into the real ledger before tests/conftest.py isolated TWOHANDS_SPEND_FILE. Copied here verbatim; "
                    "budgets.spent() skips them. The ledger itself is not rewritten. Undo: delete this file.",
            "pid": a.pid, "usd_each": a.usd, "n": len(new)}
    with open(q, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(note) + "\n")
        for r in new:
            fh.write(json.dumps(r) + "\n")
    print(f"appended {len(new)} rows to {q}")
    for role in ("bulk", "worker", "live"):
        print(f"  {role} spent today after: {budgets.spent(role):.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
