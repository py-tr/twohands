"""The paper decides: a read is accepted only if the form's own redundancy agrees with it.

Checks, in order (all failures are reported; any failure routes the form to a person):
  1. shape        - a JSON object with exactly len(schema.fields) items
  2. row label    - the printed label the model reported at each position matches the schema's expectation
                    at that position -> else "row label mismatch". Text labels must match exactly (keywords);
                    logo rows fail when the label is empty or fits a NEIGHBOURING row better than its own
                    (evidence of a skipped / doubled / shifted row). Pilot reads showed both models misname
                    single small logos (PRD read as "MC", MC as "PVEM") while the values were right, so a
                    strict logo-identity rule would route correct reads; the shift rule does not.
  3. completeness - every digit field read
  4. words=digits - per field, when the words were read
  5. identities   - the schema's arithmetic (rows sum to TOTAL, section identities)
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional

from twohands import schema as schemamod


def norm(text: Any) -> str:
    t = unicodedata.normalize("NFKD", str(text or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).upper()
    return " " + re.sub(r"[^A-Z0-9]+", " ", t).strip() + " "


def parties_in(label: Any, aliases: dict) -> set[str]:
    t = norm(label)
    found = set()
    for party, names in aliases.items():
        for a in names:
            if " " + norm(a).strip() + " " in t:
                found.add(party)
                break
    return found


def label_ok(label: Any, expect: dict, aliases: dict) -> bool:
    if label is None or not str(label).strip():
        return False
    if "parties" in expect:
        return parties_in(label, aliases) == set(expect["parties"])
    t = norm(label)
    kws = [norm(k).strip() for k in expect.get("keywords", [])]
    bad = [norm(k).strip() for k in expect.get("none", [])]
    # keywords match as word prefixes ("SACAD" matches "SACADOS"); 'none' words likewise
    has = lambda k: re.search(r"\b" + re.escape(k), t) is not None
    if parties_in(label, aliases) and not kws:
        return False
    return all(has(k) for k in kws) and not any(has(b) for b in bad)


def party_score(read: set, expect: set) -> int:
    """How well a read logo set fits an expected row: shared logos + 1 if the logo COUNT matches
    (counting logos is reliable; telling small logos apart is not)."""
    return len(read & expect) + (1 if len(read) == len(expect) else 0)


def label_consistent(i: int, label: Any, fields: list, aliases: dict) -> bool:
    """Position check for row labels. Text labels (section titles, NULOS, TOTAL...) must match their keyword rule.
    Logo rows (``parties``) fail only on evidence of a row shift: an empty label, or a label that fits the
    neighbouring logo row (position i-1 or i+1) strictly better than its own position."""
    exp = fields[i]["label"]
    if "parties" not in exp:
        return label_ok(label, exp, aliases)
    if label is None or not str(label).strip():
        return False
    read = parties_in(label, aliases)
    own = party_score(read, set(exp["parties"]))
    for j in (i - 1, i + 1):
        if 0 <= j < len(fields) and "parties" in fields[j]["label"]:
            if party_score(read, set(fields[j]["label"]["parties"])) > own:
                return False
    return True


def iv(x) -> Optional[int]:
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        return int(x) if float(x).is_integer() and x >= 0 else None
    s = str(x).replace(",", "").strip()
    return int(s) if s.isdigit() else None


@dataclass
class GateResult:
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)       # shape | label | empty | words | identity
    values: dict[str, Optional[int]] = field(default_factory=dict)   # digits, by schema key (position)
    words: dict[str, Optional[int]] = field(default_factory=dict)
    labels: dict[str, Any] = field(default_factory=dict)
    fixes: list[str] = field(default_factory=list)
    identities: list[dict] = field(default_factory=list)  # [{name, ok (None = not computable), lhs, rhs}]
    failing_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def items_of(parsed: Any) -> Optional[list]:
    if isinstance(parsed, dict) and isinstance(parsed.get("values"), list):
        return parsed["values"]
    if isinstance(parsed, list):
        return parsed
    return None


def gate(parsed: Any, s: Optional[dict] = None) -> GateResult:
    s = s or schemamod.load()
    fields = s["fields"]
    aliases = s.get("party_aliases", {})
    r = GateResult(accepted=False)

    def fail(code: str, msg: str, keys=()):
        r.codes.append(code)
        r.reasons.append(msg)
        for k in keys:
            if k not in r.failing_fields:
                r.failing_fields.append(k)

    items = items_of(parsed)
    if items is None:
        fail("shape", "no parseable read")
        return r
    if len(items) != len(fields):
        fail("shape", f"read has {len(items)} values, form has {len(fields)}")
    for i, f in enumerate(fields):
        it = items[i] if i < len(items) and isinstance(items[i], dict) else {}
        k = f["key"]
        r.values[k], r.words[k], r.labels[k] = iv(it.get("n")), iv(it.get("w")), it.get("label")
        if it.get("fix"):
            r.fixes.append(k)
    # 2. row labels
    for i, f in enumerate(fields):
        if i < len(items) and not label_consistent(i, r.labels[f["key"]], fields, aliases):
            fail("label", f"row label mismatch at position {i + 1} ({f['key']}): read '{r.labels[f['key']]}'", [f["key"]])
    # 3-4. per field
    for f in fields:
        k = f["key"]
        n, w = r.values[k], r.words[k]
        if n is None:
            fail("empty", f"{k} digits empty", [k])
        elif w is not None and n != w:
            fail("words", f"{k} digits {n} != words {w}", [k])
    # 5. identities
    for idt in s.get("identities", []):
        lhs = s["vote_keys"] if idt["sum"] == "@vote" else idt["sum"]
        a = [r.values.get(k) for k in lhs]
        b = [r.values.get(k) for k in idt["equals"]]
        if None in a or None in b:
            r.identities.append({"name": idt["name"], "ok": None})
            continue  # already reported as empty
        ok = sum(a) == sum(b)
        r.identities.append({"name": idt["name"], "ok": ok, "lhs": sum(a), "rhs": sum(b)})
        if not ok:
            fail("identity", f"{idt['name']}: {sum(a)} != {sum(b)}", list(lhs) + list(idt["equals"]))
    r.accepted = not r.reasons
    return r
