"""Gate v2 (PROTOCOL.md Amendment 3). The frozen gate (``twohands.gate``) is not changed; v2 runs it and adds:

  (a) every field that appears in NO arithmetic identity of the schema (for the presidential acta: SOBRANTES) is
      accepted only if its digits AND words were both read and agree; otherwise the form routes (code "unchecked").
      Two-reader variant (``second=`` the other reader's digits): such a field is also accepted when the second
      reader's digits for it equal the primary's.
  (b) the row-label check is unchanged in "v2". In "v2b" (secondary) the label check on LOGO rows is relaxed: a logo
      row fails only if its label is empty, or it belongs to a run of >= 2 adjacent logo rows that each fit the
      same-direction neighbour (i-1 or i+1) strictly better than their own row (the trace of a skipped / doubled
      row). Text rows keep their keyword rule.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from twohands import schema as schemamod
from twohands.gate import GateResult, gate, label_ok, parties_in, party_score

VARIANTS = ("v2", "v2b")


def identity_keys(s: dict) -> set[str]:
    out: set[str] = set()
    for idt in s.get("identities", []):
        out |= set(s["vote_keys"] if idt["sum"] == "@vote" else idt["sum"])
        out |= set(idt["equals"])
    return out


def unchecked_fields(s: dict) -> list[str]:
    """Fields outside every arithmetic identity, in schema order."""
    ids = identity_keys(s)
    return [f["key"] for f in s["fields"] if f["key"] not in ids]


def shift_dirs(i: int, label: Any, fields: list, aliases: dict) -> set[int]:
    """Directions (-1 / +1) whose neighbouring logo row fits this row's label strictly better than its own row."""
    read = parties_in(label, aliases)
    own = party_score(read, set(fields[i]["label"]["parties"]))
    return {d for d in (-1, 1) if 0 <= i + d < len(fields) and "parties" in fields[i + d]["label"]
            and party_score(read, set(fields[i + d]["label"]["parties"])) > own}


def relaxed_label_failures(labels: dict, s: dict) -> list[str]:
    """v2b row-label rule. Returns the keys that fail, in schema order."""
    fields, aliases = s["fields"], s.get("party_aliases", {})
    bad, dirs = [], {}
    for i, f in enumerate(fields):
        lab = labels.get(f["key"])
        if "parties" not in f["label"]:
            if not label_ok(lab, f["label"], aliases):
                bad.append(f["key"])
        elif lab is None or not str(lab).strip():
            bad.append(f["key"])
        else:
            dirs[i] = shift_dirs(i, lab, fields, aliases)
    for i, ds in dirs.items():
        if any(ds & dirs.get(j, set()) for j in (i - 1, i + 1)):
            bad.append(fields[i]["key"])
    order = {f["key"]: n for n, f in enumerate(fields)}
    return sorted(set(bad), key=order.get)


@dataclass
class GateV2Result:
    accepted: bool
    variant: str
    v1: GateResult
    reasons: list[str] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)
    unchecked: dict[str, str] = field(default_factory=dict)  # key -> "words" | "second" | "fail"

    @property
    def values(self) -> dict:
        return self.v1.values

    def to_dict(self) -> dict:
        return {"accepted": self.accepted, "variant": self.variant, "reasons": self.reasons, "codes": self.codes,
                "unchecked": self.unchecked, "v1_accepted": self.v1.accepted}


def gate_v2(parsed: Any, s: Optional[dict] = None, variant: str = "v2",
            second: Optional[dict] = None) -> GateV2Result:
    """``variant``: "v2" or "v2b". ``second``: the second reader's digits by key (two-reader variant), else None."""
    if variant not in VARIANTS:
        raise ValueError(variant)
    s = s or schemamod.load()
    v1 = gate(parsed, s)
    r = GateV2Result(accepted=False, variant=variant, v1=v1)
    pairs = list(zip(v1.codes, v1.reasons))
    if "shape" not in v1.codes:
        if variant == "v2b":
            pairs = [p for p in pairs if p[0] != "label"]
            pairs += [("label", f"row label mismatch (v2b) at {k}: read {v1.labels.get(k)!r}")
                      for k in relaxed_label_failures(v1.labels, s)]
        for k in unchecked_fields(s):
            n, w = v1.values.get(k), v1.words.get(k)
            if n is not None and w is not None and n == w:
                r.unchecked[k] = "words"
            elif n is not None and second is not None and second.get(k) is not None and second.get(k) == n:
                r.unchecked[k] = "second"
            else:
                r.unchecked[k] = "fail"
                extra = f", second reader {second.get(k)}" if second is not None else ""
                pairs.append(("unchecked", f"{k} is in no identity and its digits are not confirmed "
                                           f"(digits {n}, words {w}{extra})"))
    r.codes = [c for c, _ in pairs]
    r.reasons = [m for _, m in pairs]
    r.accepted = not pairs
    return r
