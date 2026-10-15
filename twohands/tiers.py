"""Amendment 2 (c)-(d) primitives: the capture gate and the two-reader tier (strict mode). No model call.

(c) capture gate: every digit field read; words = digits on every field whose words were read (the frozen gate's rule
    4); the vote rows sum to TOTAL. No section-5 = section-7 identity, no row-label check.
(d) two-reader tier: Gemma's digits = Qwen's digits on every one of the 23 fields, plus the capture gate on that
    agreed read, with BOTH readers' words checked against the agreed digits.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from twohands.gate import iv

ROWS_IDENTITY = "rows sum to TOTAL"


def digits(row: Optional[dict], keys: list) -> dict:
    F = (row or {}).get("fields") or {}
    return {k: iv((F.get(k) or {}).get("n")) for k in keys}


def words(row: Optional[dict], keys: list) -> dict:
    F = (row or {}).get("fields") or {}
    return {k: iv((F.get(k) or {}).get("w")) for k in keys}


def usable(row: Optional[dict]) -> bool:
    return bool(row) and bool(row.get("parsed_ok")) and not row.get("no_call")


def capture_gate(values: dict, word_reads: Iterable[dict], s: dict) -> tuple[bool, str]:
    """(passes, cause): cause is "" or one of "empty" | "words" | "rows"."""
    keys = s["keys"]
    if any(values.get(k) is None for k in keys):
        return False, "empty"
    for w in word_reads:
        if any(w.get(k) is not None and w[k] != values[k] for k in keys):
            return False, "words"
    idt = next(i for i in s["identities"] if i["name"] == ROWS_IDENTITY)
    lhs = s["vote_keys"] if idt["sum"] == "@vote" else idt["sum"]
    if sum(values[k] for k in lhs) != sum(values[k] for k in idt["equals"]):
        return False, "rows"
    return True, ""


def two_reader(g: Optional[dict], q: Optional[dict], s: dict) -> tuple[bool, str]:
    """Amendment 2 (d) on one form's last Gemma and Qwen rows. Cause: "no read" | "differ" | a capture-gate cause."""
    if not (usable(g) and usable(q)):
        return False, "no read"
    keys = s["keys"]
    a, b = digits(g, keys), digits(q, keys)
    if a != b:
        return False, "differ"
    return capture_gate(a, (words(g, keys), words(q, keys)), s)


def judge(value: Any, k: str, f: str, prep_value: Optional[int], V: dict) -> str:
    """One accepted field of one reader: "right" | "wrong" | "undecided" (a verdict exists, the paper does not settle
    it) | "unadjudicated" (reader != capture and nobody has looked at the paper). Truth = the paper where a verdict
    in verdicts.json read it, else the capture (PROTOCOL.md section 6)."""
    v = V.get(f"{k}__{f}")
    if v:
        if v["verdict"] not in ("model_right", "capture_right", "neither"):
            return "undecided"
        p = v.get("paper")
        return "right" if value == (None if p == "blank" else p) else "wrong"
    return "right" if value == prep_value else "unadjudicated"
