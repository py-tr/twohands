"""Every gate tier on the 300 in one table (Results), from computed files only:
app/data/two_reader_300.json (scripts/two_reader_300.py, recomputed by `make eval`) and results/posthoc_v2_300.json
(post-hoc gate variants, recomputed by `make eval`)."""
from __future__ import annotations

from app import numbers as numbersmod
from app import store as storemod
from twohands import REPO

POSTHOC = REPO / "results" / "posthoc_v2_300.json"
ROWS = [  # (source, key, label, gate, readers, post_hoc)
    ("T", "gemma", "Gemma, full gate (primary)", "full: words, rows, sections, row labels", "one", False),
    ("T", "gemma_capture", "Gemma, light gate (Amendment 2 c)", "light: words = digits, rows = TOTAL", "one", False),
    ("T", "qwen", "Qwen, full gate", "full", "one", False),
    ("T", "two_reader", "Two readers, light gate (Amendment 2 d)", "light, both readers agree on all 23 digits", "two", False),
    ("T", "two_reader_s7", "Two readers, both full gates", "full on both, same digits", "two", False),
    ("P", "v2", "Gate v2", "post-hoc", "one", True),
    ("P", "v2b (relaxed label, secondary)", "Gate v2b (relaxed label)", "post-hoc", "one", True),
    ("T", "v2_2r", "Gate v2-2R (unused ballots confirmed by words or Qwen)", "post-hoc", "two", True),
    ("T", "v2_2r_strict", "Gate v2-2R strict (only if Qwen agrees)", "post-hoc", "two", True),
]


def table() -> dict | None:
    T = numbersmod.tiers()
    if not T or "tiers" not in T:
        return None
    P = storemod._jload(POSTHOC, {}) or {}
    n = T["forms"]
    rows = []
    for src, key, label, gate, readers, ph in ROWS:
        t = (T["tiers"] if src == "T" else P).get(key)
        if not t:
            continue
        rows.append({"key": key, "label": label, "gate": gate, "readers": readers, "post_hoc": ph,
                     "accepted": t["accepted"], "accepted_pct": round(100 * t["accepted"] / n), "fields": t["fields"],
                     "errors": t["errors"], "undecided": t.get("undecided", 0),
                     "err_pct": round(100 * t["errors"] / t["fields"], 2) if t["fields"] else None})
    by = {r["key"]: r for r in rows}
    full, light, two = by.get("gemma"), by.get("gemma_capture"), by.get("two_reader")
    take = None
    if full and light and two:
        take = (f"Dropping the section checks takes one reader from {full['accepted']} to {light['accepted']} forms with no "
                f"person ({light['accepted'] / full['accepted']:.1f} times as many), but errors rise to {light['errors']} in "
                f"{light['fields']:,} fields ({light['err_pct']:.2f}%): the bookkeeping identities catch real misreads, not "
                f"only inconsistent paper. With two readers the lighter gate is safe ({two['errors']} in {two['fields']:,}); "
                f"with one reader it is not. Either way the paper decides, and every tier is published.")
    return {"forms": n, "rows": rows, "takeaway": take}
