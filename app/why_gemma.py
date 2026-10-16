"""Why Gemma: the single-reader comparison and the pairs, from app/data/bakeoff_300.json, and two Gemma misreads
the arithmetic caught, from the stored reads. One source for the README, submission/lablab.md, docs/GEMMA.md and
the results page; scripts/why_gemma.py writes the docs blocks and checks them (make eval). No model call.

The misreads are fixed by field id (picked once: a digit misread, words read the same way so only the arithmetic
can catch it, the only reason the form was routed, and the certified count agrees with the paper). Everything shown
about them is recomputed from results/calls_gemma.jsonl and results/adjudication/certified.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[1]
BAKEOFF = REPO / "app" / "data" / "bakeoff_300.json"
CALLS = REPO / "results" / "calls_gemma.jsonl"
CERTIFIED = REPO / "results" / "adjudication" / "certified.json"
GEMMA, QWEN = "Gemma-4-31B-IT", "Qwen3.8-27B"
CAUGHT = ("122655C0100__OPT02", "110922C0100__OPT04")   # form__code (codes are neutral: Option NN)
CROP_DIR = REPO / "docs" / "caught"


def load() -> Optional[dict]:
    try:
        return json.loads(BAKEOFF.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _x(a: float, b: float) -> str:
    return f"{a / b:.1f}x"


def _pct(a: int, n: int) -> str:
    return f"{round(100 * a / n)}%"


def facts(d: dict) -> dict:
    M = d["models"]
    g, q = M[GEMMA], M[QWEN]
    pairs = [p for p in d["pairs"] if p["n"] and not p.get("halted")]
    clean = [p for p in pairs if p["accepted_wrong"] == 0 and p["accepted_unadjudicated"] == 0]
    without = [p for p in pairs if GEMMA not in (p["a"], p["b"])]
    rate_g, rate_q = g["accepted_wrong"] / g["accepted_fields"], q["accepted_wrong"] / q["accepted_fields"]
    return {
        "n": g["n"], "acc": _x(g["accepted"], q["accepted"]), "cost": _x(q["cost_per_1000_usd"], g["cost_per_1000_usd"]),
        "speed": _x(q["mean_latency_s"], g["mean_latency_s"]),
        # "the same error rate": both below 0.2% of accepted fields and within 0.05 points of each other
        "same_rate": max(rate_g, rate_q) < 0.002 and abs(rate_g - rate_q) < 0.0005,
        "no_cut": g["finish_reason"].get("length", 0) == 0,
        "every_clean_has_gemma": bool(clean) and all(GEMMA in (p["a"], p["b"]) for p in clean),
        "without": without, "pairs": pairs,
    }


def lead(d: Optional[dict] = None) -> Optional[str]:
    d = d or load()
    if not d:
        return None
    f = facts(d)
    s = (f"Same {f['n']} forms, same gate, on AMD: Gemma accepts {f['acc']} the forms {QWEN} does"
         + (" at the same error rate" if f["same_rate"] else "")
         + f", {f['cost']} cheaper and {f['speed']} faster" + (", with no truncated answers." if f["no_cut"] else "."))
    bad = [p for p in f["without"] if p["accepted_wrong"]]
    if f["every_clean_has_gemma"] and len(f["without"]) == 1 and bad:
        s += (f" Every zero-error two-reader pair includes Gemma; the only pair without it made errors "
              f"({bad[0]['accepted_wrong']} of {bad[0]['accepted_fields']:,}).")
    return s


def rows(d: Optional[dict] = None) -> list[dict]:
    """The table: the single readers that read the forms (not halted), then the pairs. Cells as shown."""
    d = d or load()
    if not d:
        return []
    M = d["models"]
    singles = [m for m in (GEMMA, QWEN) if m in M] + sorted(
        m for m, b in M.items() if m not in (GEMMA, QWEN) and b["n"] and not b.get("halted"))
    out = []
    for m in singles:
        b = M[m]
        und = f" (+{b['accepted_undecided']} undecided)" if b["accepted_undecided"] else ""
        out.append({"who": m, "gemma": m == GEMMA, "pair": False,
                    "acc": f"{b['accepted']} of {b['n']} ({_pct(b['accepted'], b['n'])})",
                    "wrong": f"{b['accepted_wrong']} of {b['accepted_fields']:,}{und}",
                    "cost": f"${b['cost_per_1000_usd']:.2f}", "time": f"{round(b['mean_latency_s'])} s",
                    "cut": f"{b['finish_reason'].get('length', 0)} of {b['sent']}"})
    for p in facts(d)["pairs"]:
        und = f" (+{p['accepted_undecided']} undecided)" if p["accepted_undecided"] else ""
        cost = M[p["a"]]["cost_per_1000_usd"] + M[p["b"]]["cost_per_1000_usd"]
        out.append({"who": f"{p['a']} + {p['b']}", "gemma": GEMMA in (p["a"], p["b"]), "pair": True,
                    "acc": f"{p['accepted']} of {p['n']} ({_pct(p['accepted'], p['n'])})",
                    "wrong": f"{p['accepted_wrong']} of {p['accepted_fields']:,}{und}",
                    "cost": f"${cost:.2f}", "time": "–", "cut": "–"})
    return out


HEAD = ("Reader", "Forms accepted", "Wrong of accepted fields", "$ per 1,000 forms", "Mean time per read")
def note(d: Optional[dict] = None) -> str:
    d = d or load()
    part = [f"{m}: first {b['n']} forms (budget rule)" for m, b in d["models"].items()
            if b["n"] and not b.get("halted") and b["n"] < d["models"][GEMMA]["n"]]
    return ("Pairs: all 23 digits agree, lighter gate (secondary). " + "; ".join(part)
            + (". " if part else "") + "Source: app/data/bakeoff_300.json.")


def block_md(d: Optional[dict] = None) -> str:
    """The docs block: the lead sentence, the table, the note."""
    d = d or load()
    return "\n\n".join([lead(d), table_md(d), f"*{note(d)}*"])


def table_md(d: Optional[dict] = None) -> str:
    def cell(r, k):
        v = r[k]
        bold = r["gemma"] and (k == "wrong" if r["pair"] else k in ("who", "acc"))
        return f"**{v}**" if bold else v
    lines = ["| " + " | ".join(HEAD) + " |", "|" + "---|" * len(HEAD)]
    for r in rows(d):
        lines.append("| " + " | ".join(cell(r, k) for k in ("who", "acc", "wrong", "cost", "time")) + " |")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------- caught misreads
def _last_reads() -> dict:
    last = {}
    with CALLS.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            last[r["clave"]] = r
    return last


def caught() -> list[dict]:
    """Each CAUGHT field: Gemma's digits and words, the paper, the official capture, the certified count, the identity
    that failed (as the gate logged it) and the same identity with the paper's value."""
    from app import store as storemod
    last = _last_reads()
    cert = json.loads(CERTIFIED.read_text(encoding="utf-8"))
    cert = {(c["clave"], c["field"]): c for grp in cert.values() for c in grp}
    out = []
    for fid in CAUGHT:
        clave, code = fid.split("__")
        key = storemod.key_of(code)
        r = last[clave]
        f = r["fields"][key]
        c = cert[(clave, key)]
        bad = [i for i in r["identities"] if i["ok"] is False]
        assert len(bad) == 1 and r["route_codes"] == ["identity"], fid   # the identity was the only reason
        i = bad[0]
        fixed = i["lhs"] - f["n"] + c["paper"]
        assert fixed == i["rhs"], fid                                    # the paper's value balances it
        out.append({"clave": clave, "code": code, "name": storemod.name_of(key), "n": f["n"], "w": f["w"],
                    "paper": c["paper"], "prep": int(c["prep"]), "certified": c["computos"],
                    "identity": i["name"], "lhs": i["lhs"], "rhs": i["rhs"], "fixed": fixed,
                    "crop": f"caught/{clave}_{code}.jpg", "url": f"/crop/{clave}/{code}.jpg?label=0"})
    return out


def caught_line(c: dict) -> str:
    return (f"Form {c['clave']}, {c['name']}: Gemma read {c['n']} in the digits and {c['w']} in the words; the paper "
            f"says {c['paper']} (the official capture keyed {c['prep']}, the certified count says {c['certified']}). "
            f"The gate refused the form: {c['identity']}, {c['lhs']} ≠ {c['rhs']}; with the paper's {c['paper']} it is "
            f"{c['fixed']} = {c['rhs']}.")


def caught_md() -> str:
    parts = []
    for c in caught():
        parts += [f"![{c['name']} on form {c['clave']}, masked page, right of the logo column]({c['crop']})", "",
                  caught_line(c), ""]
    return "\n".join(parts).rstrip() + "\n"


def write_crops() -> list[Path]:
    """The crops for docs/GEMMA.md, cut from the masked page by the app's own crop code (no logo column)."""
    from app import crops, store as storemod
    CROP_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for c in caught():
        p = storemod.get_store().masked_image(c["clave"])
        assert p is not None and storemod.MASKED in p.resolve().parents
        data = crops.crop_bytes(str(p), p.stat().st_mtime, storemod.key_of(c["code"]), 0.0, False)
        dst = REPO / "docs" / c["crop"]
        dst.write_bytes(data)
        out.append(dst)
    return out
