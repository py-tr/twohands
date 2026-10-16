"""Schema builder (/builder): a tool for any self-checking form.

Draw a new form's schema on a blank page and save it in the SAME YAML format the engine runs
(schemas/mx_presidencia_2024.yaml is the reference): page geometry (corner markers or the whole image, the privacy
mask, zoomed tiles), the ordered fields, and the form's own identities. Then test it on a filled photo: the photo is
registered and masked in memory (only the masked page is stored, under app/state/uploads/builder/, git-ignored),
read once on AMD through the live-read path (same budget guard, same daily allowance, one read at a time), and
the core gate (twohands.gate.gate) checks the identities.

Identities are typed as one-line expressions and parsed by a small tokenizer + recursive-descent parser (no eval):

    rows sum to TOTAL: sum(PAN..NULOS) == TOTAL       name: expression (the name is optional)
    VOTARON + REPRESENTANTES == PERSONAS_Y_REP          '+' and '-' between fields; '-' moves a term across
    words == digits                                     per field, where a words box is drawn (the gate always
                                                        checks words against digits when the words were read)

The engine's identity format is "sum of these fields == sum of those fields" ({name, sum, equals}); an expression
that cannot be written that way (numbers, '*', a field on both sides) is refused with a readable error.
"""
from __future__ import annotations

import difflib
import functools
import io
import json
import math
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from PIL import Image, ImageDraw, ImageFont, ImageOps

from app import live as livemod
from app import store as storemod
from app import upload as uploadmod
from twohands import REPO
from twohands import gate as gatemod
from twohands import mask as maskmod
from twohands import register
from twohands import schema as schemamod

router = APIRouter()

CORE = schemamod.DEFAULT
USER_DIR = REPO / "schemas" / "user"
TESTS_DIR = uploadmod.UPLOADS / "builder"       # masked test pages only (git-ignored with app/state/uploads/)
INE_BLANK = "010469C0400"                         # a masked page from data/masked, the stand-in "blank"
_SLUG = re.compile(r"^[a-z0-9][a-z0-9_]{0,47}$")
_TID = re.compile(r"^b[0-9a-f]{12}$")
_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,39}$")
ROUND = 4


# =============================================================================================== identity expressions
class ExprError(ValueError):
    def __init__(self, msg: str, col: Optional[int] = None):
        super().__init__(msg)
        self.msg, self.col = msg, col


_TOK = re.compile(r"\s*(?:(?P<range>\.\.)|(?P<eq>==)|(?P<op>[+\-(),])|(?P<name>@?[A-Za-z_][A-Za-z0-9_]*)"
                  r"|(?P<num>\d+(?:\.\d+)?)|(?P<bad>=|\S))")


def tokenize(text: str) -> list[tuple[str, str, int]]:
    out, i = [], 0
    while i < len(text):
        m = _TOK.match(text, i)
        if not m or m.end() == i:
            break
        kind = m.lastgroup
        if kind is None:  # trailing whitespace
            break
        val = m.group(kind)
        col = m.start(kind)
        if kind == "num":
            raise ExprError(f"'{val}' is a number; an identity compares sums of fields only (e.g. A + B == C)", col)
        if kind == "bad":
            hint = " (use == to compare)" if val == "=" else ""
            raise ExprError(f"unexpected '{val}'{hint}; only field names, sum(...), '..', '+', '-' and '==' are allowed", col)
        out.append(("op" if kind in ("op", "eq", "range") else kind, val, col))
        i = m.end()
    return out


def _unknown(name: str, keys: list[str], col: int) -> ExprError:
    near = difflib.get_close_matches(name, keys, n=1) or difflib.get_close_matches(name.upper(), keys, n=1)
    return ExprError(f"unknown field '{name}'" + (f"; did you mean {near[0]}?" if near else
                                                 "; draw it as a field first"), col)


class _Parser:
    def __init__(self, toks, keys, vote_keys):
        self.t, self.i, self.keys, self.vote_keys = toks, 0, keys, vote_keys

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("end", "", None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, val, what):
        k, v, c = self.take()
        if v != val:
            raise ExprError(f"expected {what}" + (f", found '{v}'" if v else " at the end"), c)

    def item(self) -> list[str]:
        k, v, c = self.take()
        if k != "name":
            raise ExprError("expected a field name" + (f", found '{v}'" if v else " at the end"), c)
        if v.lower() == "@vote":
            if not self.vote_keys:
                raise ExprError("@vote means the fields marked as vote rows; this form has none", c)
            return list(self.vote_keys)
        if v not in self.keys:
            raise _unknown(v, self.keys, c)
        if self.peek()[1] == "..":
            self.take()
            k2, v2, c2 = self.take()
            if k2 != "name":
                raise ExprError("a range needs a last field: FIRST..LAST", c2)
            if v2 not in self.keys:
                raise _unknown(v2, self.keys, c2)
            a, b = self.keys.index(v), self.keys.index(v2)
            if b < a:
                raise ExprError(f"range {v}..{v2} runs backwards: {v2} comes before {v} on the form", c)
            return self.keys[a:b + 1]
        return [v]

    def term(self) -> list[str]:
        k, v, c = self.peek()
        if k == "name" and v.lower() == "sum" and self.i + 1 < len(self.t) and self.t[self.i + 1][1] == "(":
            self.take(); self.take()
            got = self.item()
            while self.peek()[1] in (",", "+"):
                self.take()
                got += self.item()
            self.expect(")", "')' to close sum(")
            return got
        return self.item()

    def side(self) -> tuple[list[str], list[str]]:
        pos, neg = [], []
        sign = 1
        if self.peek()[1] in ("+", "-"):
            sign = -1 if self.take()[1] == "-" else 1
        while True:
            (pos if sign > 0 else neg).extend(self.term())
            nxt = self.peek()[1]
            if nxt in ("+", "-"):
                sign = 1 if self.take()[1] == "+" else -1
                continue
            return pos, neg


def default_name(lhs, rhs) -> str:
    return f"{' + '.join(lhs)} == {' + '.join(rhs)}"


def parse_identity(line: str, keys: list[str], vote_keys: Optional[list[str]] = None) -> Optional[dict]:
    """One line -> {"kind": "words"} | {"kind": "sum", "name", "sum" (list or "@vote"), "equals"} | None (blank or
    a '#' comment). Raises ExprError with a readable message and the 0-based column inside the line."""
    raw = line
    if not line.strip() or line.strip().startswith("#"):
        return None
    name, off = None, 0
    if ":" in line:
        name, expr = line.rsplit(":", 1)
        off = len(name) + 1
        name = name.strip()
        if not name:
            raise ExprError("a name before ':' cannot be empty", 0)
    else:
        expr = line
    if re.fullmatch(r"\s*words\s*==\s*digits\s*", expr, flags=re.I):
        return {"kind": "words", "name": name or "words == digits"}
    try:
        toks = tokenize(expr)
    except ExprError as e:
        raise ExprError(e.msg, None if e.col is None else e.col + off)
    if not toks:
        raise ExprError("empty expression", off)
    eqs = [t for t in toks if t[1] == "=="]
    if not eqs:
        raise ExprError("an identity needs '==' between two sides (e.g. A + B == C)", len(raw.rstrip()))
    if len(eqs) > 1:
        raise ExprError("only one '==' per line; write a second identity on its own line", eqs[1][2] + off)
    vk = list(vote_keys or [])
    p = _Parser(toks, list(keys), vk)
    try:
        if p.peek()[1] == "==":
            raise ExprError("the left side is empty", p.peek()[2])
        lp, ln = p.side()
        p.expect("==", "'+', '-' or '=='")
        if p.peek()[0] == "end":
            raise ExprError("the right side is empty", len(expr.rstrip()))
        rp, rn = p.side()
        if p.peek()[0] != "end":
            k, v, c = p.peek()
            raise ExprError(f"unexpected '{v}'; join terms with '+' or '-'", c)
    except ExprError as e:
        raise ExprError(e.msg, None if e.col is None else e.col + off)
    lhs, rhs = lp + rn, rp + ln
    if not lhs or not rhs:
        raise ExprError("each side needs at least one field added (not only subtracted)", off)
    both = sorted(set(lhs) & set(rhs), key=list(keys).index)
    if both:
        raise ExprError(f"{', '.join(both)} on both sides cancels out; remove it from one side", off)
    dup = [k for k in dict.fromkeys(lhs + rhs) if (lhs + rhs).count(k) > 1]
    if dup:
        raise ExprError(f"{', '.join(dup)} is counted twice", off)
    out_sum: Any = "@vote" if vk and lhs == vk else lhs
    return {"kind": "sum", "name": name or default_name(lhs, rhs), "sum": out_sum, "equals": rhs}


def _side_text(ks: list[str], keys: list[str]) -> str:
    if len(ks) >= 4 and all(k in keys for k in ks):
        i = keys.index(ks[0])
        if keys[i:i + len(ks)] == ks:
            return f"sum({ks[0]}..{ks[-1]})"
    return " + ".join(ks)


def render_identity(idt: dict, keys: list[str], vote_keys: list[str]) -> str:
    """Engine identity -> the one-line expression the builder shows (parse_identity reads it back identically)."""
    lhs = list(vote_keys) if idt["sum"] == "@vote" else list(idt["sum"])
    if idt["sum"] == "@vote":
        left = _side_text(lhs, keys) if _side_text(lhs, keys).startswith("sum(") else "sum(@vote)"
    else:
        left = _side_text(lhs, keys)
    expr = f"{left} == {_side_text(list(idt['equals']), keys)}"
    name = idt.get("name")
    return expr if not name or name == default_name(lhs, list(idt["equals"])) else f"{name}: {expr}"


def validate_lines(lines: list[str], keys: list[str], vote_keys: list[str], has_words: bool) -> list[dict]:
    out = []
    for ln in lines:
        try:
            r = parse_identity(ln, keys, vote_keys)
        except ExprError as e:
            out.append({"ok": False, "error": e.msg, "col": e.col})
            continue
        if r is None:
            out.append({"ok": True, "blank": True})
        elif r["kind"] == "words":
            out.append({"ok": True, "kind": "words", "note": "checked on every field with a words box" if has_words
                        else "no field has a words box yet: select a field and draw one with the Words tool",
                        "warn": not has_words})
        else:
            lhs = vote_keys if r["sum"] == "@vote" else r["sum"]
            out.append({"ok": True, "kind": "sum", "name": r["name"], "sum": r["sum"], "equals": r["equals"],
                        "text": f"{' + '.join(lhs)} = {' + '.join(r['equals'])}"})
    return out


# =============================================================================================== state <-> schema
_TOP = ("form", "title", "layout", "fields", "identities")
_LAY = ("canonical", "mask", "tiles")
_CAN = ("size", "markers", "marker_size", "whole_image")
_COMPUTED = ("_dir", "keys", "vote_keys")


def _r(x: float) -> float:
    return round(float(x), ROUND)


def _box(b) -> list[float]:
    return [_r(v) for v in b]


def load_yaml(p: Path) -> dict:
    """schema.load without its cache (a saved schema may be re-saved under the same path)."""
    s = yaml.safe_load(Path(p).read_text(encoding="utf-8"))
    s["_dir"] = str(Path(p).parent)
    s["keys"] = [f["key"] for f in s["fields"]]
    s["vote_keys"] = [f["key"] for f in s["fields"] if f.get("vote")]
    return s


def is_core_like(s: dict) -> bool:
    """Same fields, in the same order, as the core INE schema: the core reader's frozen prompt applies."""
    try:
        return [f["key"] for f in s["fields"]] == schemamod.load(CORE)["keys"]
    except Exception:  # noqa: BLE001
        return False


def schema_to_state(s: dict, field_boxes: Optional[dict] = None) -> dict:
    lay, can = s["layout"], s["layout"]["canonical"]
    W, H = can["size"]
    markers = []
    if can.get("markers") and not can.get("whole_image"):
        M = [(x * W, y * H) for x, y in can["markers"]]
        fl = math.dist(M[0], M[1])
        side = float(can.get("marker_size", 0.02)) * fl
        markers = [[(x - side / 2) / W, (y - side / 2) / H, (x + side / 2) / W, (y + side / 2) / H] for x, y in M]
    fb = field_boxes or {}
    fields = []
    for f in s["fields"]:
        g = {k: v for k, v in f.items()}
        if "box" not in g and f["key"] in fb:
            g["box"] = _box(fb[f["key"]])
        fields.append(g)
    keys = [f["key"] for f in s["fields"]]
    vote = [f["key"] for f in s["fields"] if f.get("vote")]
    lines = [render_identity(i, keys, vote) for i in s.get("identities", [])]
    if any(f.get("words_box") for f in s["fields"]) or is_core_like(s):
        lines.append("words == digits")
    mask = s["layout"].get("mask") or {}
    rects = (mask.get("movil") or mask.get("escaner") or []) if isinstance(mask, dict) else list(mask)
    return {
        "form": s.get("form", ""), "title": s.get("title", ""), "size": [W, H],
        "whole_image": bool(can.get("whole_image") or not can.get("markers")), "markers": markers,
        "mask": [list(r) for r in rects], "tiles": [dict(t) for t in lay.get("tiles", [])],
        "fields": fields, "identities": lines,
        "keep": {"top": {k: v for k, v in s.items() if k not in _TOP and k not in _COMPUTED},
                 "layout": {k: v for k, v in lay.items() if k not in _LAY},
                 "canonical": {k: v for k, v in can.items() if k not in _CAN},
                 "mask_layouts": list(mask.keys()) if isinstance(mask, dict) else ["movil", "escaner"]},
    }


def _check_box(b, what: str, errs: list) -> Optional[list[float]]:
    try:
        b = [float(v) for v in b]
    except (TypeError, ValueError):
        errs.append(f"{what}: not a box"); return None
    if len(b) != 4 or not all(-1e-9 <= v <= 1 + 1e-9 for v in b) or b[0] >= b[2] or b[1] >= b[3]:
        errs.append(f"{what}: the box must lie on the page (fractions 0..1, x0 < x1, y0 < y1)")
        return None
    return _box([min(1.0, max(0.0, v)) for v in b])


def _inside(a, m) -> bool:
    """Box a overlaps rectangle m by more than half of a's area."""
    ix = max(0.0, min(a[2], m[2]) - max(a[0], m[0]))
    iy = max(0.0, min(a[3], m[3]) - max(a[1], m[1]))
    return ix * iy > 0.5 * (a[2] - a[0]) * (a[3] - a[1])


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")[:48].strip("_")
    return s


def state_to_schema(st: dict) -> tuple[Optional[dict], list[str], list[str]]:
    """Builder state -> engine schema dict (same format as schemas/mx_presidencia_2024.yaml), errors, warnings."""
    errs, warns = [], []
    form = slugify(st.get("form") or st.get("title"))
    if not form or not _SLUG.match(form):
        errs.append("Give the form an id (letters, digits, underscores).")
    keep = st.get("keep") or {}
    try:
        W, H = [int(v) for v in st.get("size") or []]
        assert 50 <= W <= 10000 and 50 <= H <= 10000
    except (ValueError, TypeError, AssertionError):
        errs.append("The page size is missing: load a blank form first."); W, H = 0, 0
    can: dict = {"size": [W, H]}
    if st.get("whole_image"):
        can["whole_image"] = True
    else:
        ms = [b for b in (_check_box(m, f"corner marker {i + 1}", errs) for i, m in enumerate(st.get("markers") or [])) if b]
        if len(ms) != 4:
            errs.append(f"Draw all four corner markers ({len(ms)} drawn), or tick 'use whole image'.")
        elif W:
            cs = sorted([((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b) for b in ms], key=lambda c: c[1])
            top, bot = sorted(cs[:2]), sorted(cs[2:])
            order = [top[0], top[1], bot[1], bot[0]]  # TL, TR, BR, BL
            fl = math.dist((order[0][0] * W, order[0][1] * H), (order[1][0] * W, order[1][1] * H))
            side = float(np.mean([((b[2] - b[0]) * W + (b[3] - b[1]) * H) / 2 for _, _, b in order]))
            can["markers"] = [[_r(x), _r(y)] for x, y, _ in order]
            can["marker_size"] = _r(side / fl) if fl else 0.02
    can.update(keep.get("canonical") or {})
    mask = [b for b in (_check_box(m, f"mask {i + 1}", errs) for i, m in enumerate(st.get("mask") or [])) if b]
    if not mask:
        warns.append("No privacy mask: nothing will be blacked out before the page is stored and read.")
    tiles = []
    for i, t in enumerate(st.get("tiles") or []):
        b = _check_box(t.get("box"), f"tile {i + 1}", errs)
        if b:
            nm = slugify(t.get("name")) or f"tile_{i + 1}"
            tiles.append({k: v for k, v in t.items() if k not in ("name", "box", "says")} |
                         {"name": nm, "box": b, "says": str(t.get("says") or nm.replace("_", " "))})
    fields, seen = [], set()
    for i, f in enumerate(st.get("fields") or []):
        k = str(f.get("key") or "").strip()
        if not _KEY.match(k):
            errs.append(f"Field {i + 1}: '{k}' is not a valid name (letters, digits, underscore; not starting with a digit)."); continue
        if k in seen:
            errs.append(f"Field {k} appears twice."); continue
        seen.add(k)
        g = {kk: v for kk, v in f.items() if not kk.startswith("_")}
        g["key"] = k
        if f.get("box") is not None:
            g["box"] = _check_box(f["box"], f"field {k}", errs)
        elif not f.get("label") or "parties" not in (f.get("label") or {}):
            pass
        if f.get("words_box") is not None:
            g["words_box"] = _check_box(f["words_box"], f"words box of {k}", errs)
        lab = f.get("label")
        if not isinstance(lab, dict):
            g["label"] = {"keywords": [w for w in re.split(r"[\s,]+", str(lab or "").upper()) if w]}
        for b in (g.get("box"), g.get("words_box")):
            if b and any(_inside(b, m) for m in mask):
                errs.append(f"Field {k} lies inside the privacy mask: it would be blacked out before reading.")
                break
        if g.get("box") is None:
            g.pop("box", None)
        if g.get("words_box") is None:
            g.pop("words_box", None)
        # keep the engine's key order (key first), then the rest as given
        fields.append({"key": k} | {kk: v for kk, v in g.items() if kk != "key"})
    if not fields:
        errs.append("Draw at least one field.")
    keys = [f["key"] for f in fields]
    vote = [f["key"] for f in fields if f.get("vote")]
    idents, has_words = [], any(f.get("words_box") for f in fields)
    for n, ln in enumerate(st.get("identities") or []):
        try:
            r = parse_identity(ln, keys, vote)
        except ExprError as e:
            errs.append(f"Identity line {n + 1}: {e.msg}"); continue
        if r and r["kind"] == "sum":
            idents.append({"name": r["name"], "sum": r["sum"], "equals": r["equals"]})
        elif r and r["kind"] == "words" and not has_words and not is_core_like({"fields": fields}):
            warns.append("'words == digits' is listed but no field has a words box.")
    if not idents and not has_words:
        warns.append("No identities: the gate can only check that every field was read.")
    layout = {"canonical": can}
    kl = dict(keep.get("layout") or {})
    for k in ("template", "landmarks", "reference"):
        if k in kl:
            layout[k] = kl.pop(k)
    layouts = (keep.get("mask_layouts") or ["movil", "escaner"])
    layout["mask"] = {lk: [list(m) for m in mask] for lk in layouts}
    layout.update(kl)
    layout["tiles"] = tiles
    s = {"form": form, "title": str(st.get("title") or form), "layout": layout, "fields": fields}
    top = dict(keep.get("top") or {})
    s.update(top)
    s["identities"] = idents
    if errs:
        return None, errs, warns
    return s, errs, warns


class _Dumper(yaml.SafeDumper):
    """Mappings in block style; lists of scalars (boxes, sizes, keyword lists) in flow style."""


def _repr_list(d, data):
    return d.represent_sequence("tag:yaml.org,2002:seq", data,
                                flow_style=all(not isinstance(x, (dict, list)) for x in data) or
                                all(isinstance(x, list) and all(not isinstance(y, (dict, list)) for y in x) for x in data))


def _repr_dict(d, data):
    return d.represent_mapping("tag:yaml.org,2002:map", data.items(), flow_style=False)


_Dumper.add_representer(list, _repr_list)
_Dumper.add_representer(dict, _repr_dict)


def to_yaml(s: dict) -> str:
    """Engine schema dict -> YAML text in the house style (one field / tile / identity per line)."""
    flow = lambda o: yaml.safe_dump(o, default_flow_style=True, width=100000, allow_unicode=True, sort_keys=False).strip()
    block = lambda o: yaml.dump(o, Dumper=_Dumper, width=120, allow_unicode=True, sort_keys=False)
    lay = dict(s["layout"])
    tiles = lay.pop("tiles", [])
    out = [
        f"# Form schema: {s.get('title') or s['form']}",
        "# Made with the Two Hands schema builder (/builder). Same format as schemas/mx_presidencia_2024.yaml:",
        "# page geometry (markers or the whole image, privacy mask, tiles), the ordered fields, the form's identities.",
        "# All coordinates are fractions of the canonical page: [x0, y0, x1, y1].",
        block({"form": s["form"], "title": s["title"]}).rstrip(),
        "",
        "layout:",
        "\n".join("  " + ln for ln in block(lay).rstrip().splitlines()),
        "  tiles:" + ("" if tiles else " []"),
        *[f"    - {flow(t)}" for t in tiles],
        "",
        "fields:",
        *[f"  - {flow(f)}" for f in s["fields"]],
    ]
    for k, v in s.items():
        if k not in ("form", "title", "layout", "fields", "identities") and k not in _COMPUTED:
            out += ["", block({k: v}).rstrip()]
    out += ["", "identities:" + ("" if s["identities"] else " []"), *[f"  - {flow(i)}" for i in s["identities"]], ""]
    text = "\n".join(out)
    clean = {k: v for k, v in s.items() if k not in _COMPUTED}
    assert yaml.safe_load(text) == clean, "YAML writer lost information"
    return text


def user_path(slug: str) -> Optional[Path]:
    if not _SLUG.match(slug or ""):
        return None
    return USER_DIR / f"{slug}.yaml"


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(p)


def save_schema(s: dict) -> tuple[str, Path, str]:
    slug = s["form"]
    p = user_path(slug)
    if p is None:
        raise ValueError("bad slug")
    text = to_yaml(s)
    USER_DIR.mkdir(parents=True, exist_ok=True)
    livemod._write_atomic(p, text)
    return slug, p, text


def schema_for(slug: str) -> dict:
    p = user_path(slug)
    if p is None or not p.is_file():
        raise HTTPException(404, "unknown schema: save it first")
    return load_yaml(p)


# =============================================================================================== bundled samples
def _font(size: int, hand: bool = False):
    names = (["segoepr.ttf", "segoesc.ttf", "Comic.ttf", "comic.ttf", "DejaVuSans-Oblique.ttf"] if hand else
             ["arialbd.ttf" if size >= 30 else "arial.ttf", "DejaVuSans-Bold.ttf" if size >= 30 else "DejaVuSans.ttf",
              "LiberationSans-Regular.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


TS_W, TS_H = 1800, 1240
TS_DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
TS_KEYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
_TS = {"x0": 130, "x_digits": 470, "box": 64, "x_words": 720, "x1": 1670, "y_head": 268, "row": 74, "mk": 46}
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
        "seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def words_en(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])
    return _ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + words_en(n % 100))


def _ts_rows():
    g = _TS
    rows = []
    for i, k in enumerate(TS_KEYS + ["TOTAL"]):
        y0 = g["y_head"] + 52 + i * g["row"] + (14 if k == "TOTAL" else 0)
        rows.append((k, y0, y0 + g["row"]))
    return rows


def timesheet(values: Optional[list[int]] = None, total: Optional[int] = None, total_words: Optional[int] = None,
              name: str = "") -> Image.Image:
    """The synthetic timesheet: days x hours rows plus a weekly total, digits AND words, a signature line (the mask),
    four corner markers. With values it is filled in a handwriting-like font."""
    g = _TS
    im = Image.new("RGB", (TS_W, TS_H), "white")
    d = ImageDraw.Draw(im)
    m = g["mk"]
    for x, y in ((40, 40), (TS_W - 40 - m, 40), (TS_W - 40 - m, TS_H - 40 - m), (40, TS_H - 40 - m)):
        d.rectangle([x, y, x + m, y + m], fill="black")
    d.text((g["x0"], 92), "WEEKLY TIMESHEET", font=_font(46), fill="#14161b")
    d.text((g["x0"], 156), "Synthetic sample form, generated for the Two Hands schema builder", font=_font(24), fill="#5f6673")
    d.text((1180, 104), "Week no.", font=_font(26), fill="#14161b")
    d.rectangle([1310, 96, 1500, 140], outline="#14161b", width=2)
    hy = g["y_head"]
    hf = _font(22)
    d.text((g["x0"] + 10, hy + 14), "DAY", font=hf, fill="#2c3039")
    d.text((g["x_digits"], hy + 14), "HOURS (digits)", font=hf, fill="#2c3039")
    d.text((g["x_words"] + 10, hy + 14), "HOURS (in words)", font=hf, fill="#2c3039")
    d.line([g["x0"], hy + 50, g["x1"], hy + 50], fill="#14161b", width=3)
    lf, bf = _font(28), _font(32)
    hand = _font(40, hand=True)
    for i, (k, y0, y1) in enumerate(_ts_rows()):
        tot = k == "TOTAL"
        if tot:
            d.line([g["x0"], y0 - 7, g["x1"], y0 - 7], fill="#14161b", width=3)
        d.text((g["x0"] + 10, y0 + 20), "WEEKLY TOTAL" if tot else TS_DAYS[i], font=bf if tot else lf, fill="#14161b")
        for j in range(3):
            bx = g["x_digits"] + j * (g["box"] + 6)
            d.rectangle([bx, y0 + 6, bx + g["box"], y1 - 6], outline="#14161b", width=3 if tot else 2)
        d.line([g["x_words"], y1 - 12, g["x1"], y1 - 12], fill="#9aa0aa", width=2)
        d.line([g["x0"], y1, g["x1"], y1], fill="#d0d0ca", width=1)
        v = (total if tot else (values[i] if values else None)) if values else None
        if v is not None:
            s = str(v)
            for j, ch in enumerate(s.rjust(3)):
                if ch != " ":
                    bx = g["x_digits"] + j * (g["box"] + 6)
                    d.text((bx + 18, y0 + 6), ch, font=hand, fill="#1a3c8c")
            wv = (total_words if total_words is not None else v) if tot else v
            d.text((g["x_words"] + 20, y0 + 4), words_en(wv), font=hand, fill="#1a3c8c")
    sy = 1010
    d.text((g["x0"], sy), "Employee name and signature", font=_font(22), fill="#2c3039")
    d.line([g["x0"], sy + 110, 1060, sy + 110], fill="#14161b", width=2)
    d.text((1160, sy), "Approved (initials)", font=_font(22), fill="#2c3039")
    d.rectangle([1160, sy + 40, 1400, sy + 110], outline="#14161b", width=2)
    if name:
        d.text((g["x0"] + 30, sy + 44), name, font=_font(48, hand=True), fill="#1a3c8c")
    return im


def as_photo(page: Image.Image, angle: float = 2.2) -> Image.Image:
    """Put a page on a table, slightly rotated: a stand-in for a phone photo (exercises the marker registration)."""
    W, H = page.size
    bg = Image.new("RGB", (W + 260, H + 220), (118, 104, 92))
    rot = page.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(118, 104, 92))
    bg.paste(rot, ((bg.width - rot.width) // 2, (bg.height - rot.height) // 2))
    return bg


TS_GOOD = [8, 8, 7, 9, 6, 0, 0]


@functools.lru_cache(maxsize=8)
def sample_png(name: str) -> bytes:
    if name == "timesheet_blank":
        im = timesheet()
    elif name == "timesheet_filled":
        im = as_photo(timesheet(TS_GOOD, sum(TS_GOOD), name="J. Example"))
    elif name == "timesheet_wrong":
        im = as_photo(timesheet(TS_GOOD, 40, total_words=40, name="J. Example"), angle=-1.6)
    else:
        raise KeyError(name)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def ine_blank_path() -> Path:
    return REPO / "data" / "masked" / f"{INE_BLANK}.jpg"


def timesheet_state() -> dict:
    g = _TS
    W, H = TS_W, TS_H
    fx = lambda x: _r(x / W)
    fy = lambda y: _r(y / H)
    m = g["mk"]
    markers = [[fx(x), fy(y), fx(x + m), fy(y + m)]
               for x, y in ((40, 40), (TS_W - 40 - m, 40), (TS_W - 40 - m, TS_H - 40 - m), (40, TS_H - 40 - m))]
    fields = []
    for i, (k, y0, y1) in enumerate(_ts_rows()):
        lab = "TOTAL" if k == "TOTAL" else TS_DAYS[i]
        fields.append({"key": k, "type": "integer", "label": {"keywords": [lab]},
                       "box": [fx(g["x_digits"] - 4), fy(y0 + 2), fx(g["x_digits"] + 3 * g["box"] + 16), fy(y1 - 2)],
                       "words_box": [fx(g["x_words"]), fy(y0 + 2), fx(g["x1"]), fy(y1 - 2)]})
    rows = _ts_rows()
    return {
        "form": "weekly_timesheet", "title": "Weekly timesheet (synthetic sample)", "size": [W, H], "whole_image": False,
        "markers": markers,
        "mask": [[fx(g["x0"] - 10), fy(1000), fx(1080), fy(1135)]],
        "tiles": [{"name": "days", "box": [fx(g["x0"] - 10), fy(rows[0][1] - 60), fx(g["x1"] + 10), fy(rows[4][2] + 6)],
                   "says": "Monday to Friday"},
                  {"name": "weekend_total", "box": [fx(g["x0"] - 10), fy(rows[5][1] - 6), fx(g["x1"] + 10), fy(rows[7][2] + 8)],
                   "says": "Saturday, Sunday and the weekly total"}],
        "fields": fields,
        "identities": ["days add up to the week: sum(MON..SUN) == TOTAL", "words == digits"],
        "keep": {"top": {}, "layout": {}, "canonical": {}, "mask_layouts": ["movil", "escaner"]},
    }


def ine_state() -> dict:
    from app.crops import field_boxes
    s = schemamod.load(CORE)
    return schema_to_state(s, field_boxes(s))


SAMPLES = {
    "timesheet": {"label": "Weekly timesheet", "tag": "synthetic sample", "state": timesheet_state,
                  "blank": "/builder/sample/timesheet_blank.png",
                  "filled": [{"name": "timesheet_filled", "label": "Filled timesheet (adds up)"},
                             {"name": "timesheet_wrong", "label": "Filled timesheet (total is wrong)"}]},
    "ine": {"label": "INE tally sheet, type 2", "tag": "real schema", "state": ine_state,
            "blank": f"/builder/sample/ine_blank.jpg",
            "note": "A masked page from our measured set stands in for the blank; the boxes are the ones our engine runs.",
            "filled": [{"name": "ine_filled", "label": "A masked tally sheet"}]},
}


# =============================================================================================== register + mask
class NotRegistered(Exception):
    pass


def _layout_arrays(s: dict):
    out = []
    for k in ("template", "reference", "landmarks"):
        v = s["layout"].get(k)
        arr = None
        if v:
            for base in (Path(s.get("_dir") or REPO / "schemas"), REPO / "schemas"):
                p = (base / v)
                if p.is_file() and p.suffix == ".npy":
                    arr = np.load(p)
                    break
        out.append(arr)
    return out


def prepare(img: Image.Image, s: dict) -> tuple[Image.Image, dict]:
    """Photo (in memory) -> masked canonical page, per the schema. Raises NotRegistered (nothing is stored)."""
    can = s["layout"]["canonical"]
    W, H = [int(v) for v in can["size"]]
    img = ImageOps.exif_transpose(img).convert("RGB")
    if can.get("whole_image") or not can.get("markers"):
        page, info = img.resize((W, H), Image.LANCZOS), {"locator": "whole image"}
    else:
        tpl, ref, lm = _layout_arrays(s)
        try:
            if tpl is not None and ref is not None and lm is not None:
                loc = register.rectify_v2(img, s["layout"], tpl, ref, lm.astype(np.float32))
                info = {"locator": "corner markers + landmarks (engine locator)"}
            else:
                loc = register.rectify(img, s["layout"], None)
                info = {"locator": "corner markers"}
        except register.NotLocated as e:
            raise NotRegistered(f"The four corner markers were not found ({e}). Retake the photo with all four "
                                "corners in the frame, or tick 'use whole image' if the photo is already cropped to the page.")
        page = loc.image
        info["markers_found"] = loc.markers_found
    page = maskmod.apply_mask(page, schemamod.mask_rects(s, "movil") or [])
    info["size"] = [W, H]
    return page, info


def _new_tid() -> str:
    return "b" + uuid.uuid4().hex[:12]


def masked_test_page(tid: str) -> Optional[Path]:
    if not _TID.match(tid or ""):
        return None
    p = TESTS_DIR / f"{tid}.jpg"
    return p if p.is_file() else None


# =============================================================================================== the read
SYS = ("You are a meticulous transcriber of paper forms. You copy exactly what is printed and handwritten on the form, "
       "digit by digit. You never correct, infer, or recompute a value; if the paper is inconsistent, you transcribe "
       "the inconsistency.")


def build_prompt(s: dict) -> str:
    tiles = s["layout"].get("tiles") or []
    imgs = " ".join(f"Image {i + 2} zooms {t['says']}." for i, t in enumerate(tiles))
    lines = []
    for i, f in enumerate(s["fields"]):
        kw = " ".join((f.get("label") or {}).get("keywords") or [])
        bits = [f"  {i + 1}. {f['key']}"]
        if kw:
            bits.append(f"(printed label: {kw})")
        if f.get("where"):
            bits.append(f"- {f['where']}")
        if f.get("box"):
            x0, y0, x1, y1 = f["box"]
            bits.append(f"- digits at about x {x0:.0%}-{x1:.0%}, y {y0:.0%}-{y1:.0%} of image 1")
        bits.append("- also written in words" if f.get("words_box") else "- no words")
        lines.append(" ".join(bits))
    n = len(s["fields"])
    return f"""This is a paper form: '{s.get('title') or s['form']}'.
Image 1 is the whole page; black rectangles are blacked out for privacy (ignore them). {imgs}
Return ONLY a JSON object {{"values": [...]}} with exactly {n} items, in this order:
{chr(10).join(lines)}
Each item is {{"label": the label printed next to that value, as printed, "n": integer from the digits or null if blank/illegible, "w": the integer meaning of the value written in words, or null when it has no words}}.
Read the words independently of the digits; if they disagree, report both as written (do not make them agree).
If a value is crossed out and rewritten, use the final value and add "fix": true to that item.
Example item: {{"label": "MONDAY", "n": 8, "w": 8}}"""


def default_read(model: str, page: Path, s: dict) -> dict:
    """One request on AMD through the core client (its shared rate limiter), short retry budget as live reads."""
    from twohands import amd, reader

    def chat(body):
        return amd.chat(body, retries=livemod.LIVE_RETRIES, log=lambda *a, **k: None, kind="live")
    if is_core_like(s):  # the core reader itself, its frozen prompt
        return reader.read(model, page, s=s, chat=chat)
    with Image.open(page) as im:
        im.load()
        pg = im.copy()
    content = [{"type": "image_url", "image_url": {"url": reader.b64(x)}} for x in [pg] + maskmod.tiles(pg, s)]
    content.append({"type": "text", "text": build_prompt(s)})
    body = {"model": reader.MODELS[model], "messages": [{"role": "system", "content": SYS},
                                                        {"role": "user", "content": content}],
            "max_tokens": reader.MAX_TOKENS[model], "temperature": 0}
    if model == "qwen":
        body["reasoning_effort"] = "low"
    t = time.time()
    row: dict = {"model": reader.MODELS[model]}
    try:
        r, attempts = chat(body)
        ch = r["choices"][0]
        msg = ch.get("message") or {}
        row.update(content=msg.get("content") or "", finish_reason=ch.get("finish_reason"), usage=r.get("usage", {}),
                   attempts=attempts)
    except Exception as e:  # noqa: BLE001
        row.update(error=f"{type(e).__name__}: {str(e)[:200]}", content="")
    row["secs"] = round(time.time() - t, 1)
    row["parsed"] = reader.parse(row["content"])
    return row


def gate_view(g: gatemod.GateResult, s: dict) -> dict:
    return {"accepted": g.accepted, "reasons": [storemod.neutralize(x) for x in g.reasons], "codes": g.codes,
            "fields": [{"key": f["key"], "n": g.values.get(f["key"]), "w": g.words.get(f["key"]),
                        "label": g.labels.get(f["key"]), "ok": f["key"] not in g.failing_fields} for f in s["fields"]],
            "identities": g.identities}


class BuilderLive(livemod.LiveManager):
    """The live-read path for builder tests: the LiveManager's queue, budget guard (same daily allowance file,
    same /usage floor) and model chooser; it waits while the main live read is busy, so one read runs at a time."""

    def __init__(self, main: Optional[livemod.LiveManager] = None, read_fn: Optional[Callable] = None,
                 wait_main_s: float = 180.0):
        main = main or livemod.LiveManager()
        super().__init__(usage_fn=main.usage_fn, chooser=main.chooser)
        self.main = main
        self.read_fn = read_fn or default_read
        self.schemas: dict[str, dict] = {}
        self.wait_main_s = wait_main_s

    def start_test(self, tid: str, page: Path, s: dict) -> livemod.Job:
        self.schemas[tid] = s
        return self.start(tid, page, kind="builder", out_dir=TESTS_DIR, fallback=None)

    def _main_busy(self) -> bool:
        try:
            with self.main._lock:
                return self.main._running() is not None or bool(self.main._queue)
        except Exception:  # noqa: BLE001
            return False

    def _run(self, job: livemod.Job) -> None:  # noqa: C901
        try:
            try:
                self.check_budget()
            except livemod.Refused as e:
                self._fail(job, "endpoint_busy" if e.code == "endpoint" else e.code, e.message)
                return
            t0 = time.time()
            if self._main_busy():
                job.emit(type="stage", stage="wait", msg="Waiting for the read in progress on the shared endpoint")
            while self._main_busy() and time.time() - t0 < self.wait_main_s:
                time.sleep(0.5)
            pick = self.chooser.choose(block=True)
            if pick["fallback"]:
                job.emit(type="notice", code="model_withdrawn", model=pick["model"], msg=pick["banner_try"])
            s = self.schemas[job.clave]
            job.emit(type="stage", stage="send", msg=f"Sent to {pick['model']} on AMD, one request")
            row = self.read_fn(pick["key"], job.page, s)
            u = row.get("usage") if isinstance(row.get("usage"), dict) else {}
            cost = (u or {}).get("cost") or 0.0
            self._spend(cost)
            if row.get("error") and livemod.endpoint_busy(row.get("error")):
                self._fail(job, "endpoint_busy", "AMD endpoint busy (503 or timeout); your masked page is kept, retry in a minute.")
                return
            if row.get("error") or not row.get("parsed"):
                self._fail(job, "read", "The model did not return a readable answer"
                           + (f" ({storemod.neutralize(row.get('error'))[:120]})." if row.get("error") else "."))
                return
            g = gatemod.gate(row["parsed"], s)
            view = gate_view(g, s)
            out = {"id": job.clave, "schema": s["form"], "model": pick["model"], "secs": row.get("secs"), "cost": cost,
                   "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "parsed": row["parsed"], **view}
            TESTS_DIR.mkdir(parents=True, exist_ok=True)
            (TESTS_DIR / f"{job.clave}.read.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
            job.state = "done"
            job.emit(type="verdict", model=pick["model"], secs=row.get("secs"), cost=cost, **view)
        except Exception as e:  # noqa: BLE001
            self._fail(job, "internal", f"Live read failed ({type(e).__name__}).")
        finally:
            job.emit(type="done")
            job.finish()


_BL_LOCK = threading.Lock()


def builder_live(request: Request) -> BuilderLive:
    st = request.app.state
    with _BL_LOCK:
        if getattr(st, "builder_live", None) is None:
            st.builder_live = BuilderLive(getattr(st, "live", None))
        return st.builder_live


# =============================================================================================== routes
def _t():
    from app.main import templates
    return templates


@router.get("/builder", response_class=HTMLResponse)
def builder_page(request: Request):
    samples = [{"id": k, "label": v["label"], "tag": v["tag"], "note": v.get("note"), "filled": v["filled"]}
               for k, v in SAMPLES.items()]
    third = (REPO / "schemas" / "mx_senado_2024.yaml").is_file()
    return _t().TemplateResponse(request, "builder.html", {"nav": "builder", "samples": samples,
                                                           "live": request.app.state.live.status(),
                                                           "third": third})


@router.get("/builder/sample/{name}")
def builder_sample_image(name: str):
    if name == "ine_blank.jpg" or name == "ine_filled.jpg":
        p = ine_blank_path() if name == "ine_blank.jpg" else REPO / "tests" / "fixtures" / "masked_escaner.jpg"
        if not p.is_file():
            raise HTTPException(404, "sample page missing")
        return Response(p.read_bytes(), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"})
    stem = name.rsplit(".", 1)[0]
    try:
        data = sample_png(stem)
    except KeyError:
        raise HTTPException(404, "unknown sample")
    return Response(data, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})


@router.get("/api/builder/sample/{sid}")
def builder_sample_state(sid: str):
    if sid not in SAMPLES:
        raise HTTPException(404, "unknown sample")
    v = SAMPLES[sid]
    return {"state": v["state"](), "blank": v["blank"], "label": v["label"], "tag": v["tag"], "note": v.get("note"),
            "filled": v["filled"]}


@router.post("/api/builder/validate")
async def builder_validate(request: Request):
    """Body {fields: [{key, vote, words_box}], identities: [line, ...]} -> one result per line (live validation)."""
    b = await request.json()
    fields = b.get("fields") or []
    keys = [str(f.get("key") or "") for f in fields]
    vote = [str(f.get("key")) for f in fields if f.get("vote")]
    has_words = any(f.get("words_box") for f in fields) or is_core_like({"fields": fields})
    return {"lines": validate_lines([str(x) for x in (b.get("identities") or [])], keys, vote, has_words)}


@router.post("/api/builder/save")
async def builder_save(request: Request):
    """Body: the builder state. Writes schemas/user/<slug>.yaml in the engine's format; returns the YAML."""
    st = await request.json()
    s, errs, warns = state_to_schema(st)
    if errs:
        return JSONResponse({"ok": False, "errors": errs, "warnings": warns}, status_code=422)
    slug, p, text = save_schema(s)
    return {"ok": True, "slug": slug, "path": _rel(p), "yaml": text,
            "warnings": warns, "download": f"/api/builder/schema/{slug}.yaml"}


@router.get("/api/builder/schema/{slug}.yaml")
def builder_download(slug: str):
    p = user_path(slug)
    if p is None or not p.is_file():
        raise HTTPException(404, "unknown schema")
    return Response(p.read_text(encoding="utf-8"), media_type="application/x-yaml; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={slug}.yaml"})


@router.get("/api/builder/state/{slug}")
def builder_state(slug: str):
    return {"state": schema_to_state(schema_for(slug))}


def _queue_test(request: Request, slug: str, img: Image.Image) -> JSONResponse | dict:
    s = schema_for(slug)
    try:
        page, info = prepare(img, s)
    except NotRegistered as e:
        return JSONResponse({"ok": False, "code": "not_located", "message": str(e)}, status_code=422)
    tid = _new_tid()
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    maskmod.save(page, TESTS_DIR / f"{tid}.jpg")
    (TESTS_DIR / f"{tid}.json").write_text(json.dumps({"id": tid, "schema": slug, "info": info,
                                                       "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}),
                                           encoding="utf-8")
    out = {"ok": True, "id": tid, "masked_url": f"/builder/test/{tid}.jpg", "info": info}
    m = builder_live(request)
    try:
        job = m.start_test(tid, TESTS_DIR / f"{tid}.jpg", s)
        out.update(job=job.id, position=m.position(job), status_url=f"/api/builder/job/{job.id}")
    except livemod.Refused as e:
        out.update(refused=e.code, message=e.message)
    return out


@router.post("/api/builder/test/{slug}")
async def builder_test(slug: str, request: Request):
    """Body: the filled photo itself (bytes, never written). Registered and masked in memory per the saved schema;
    only the masked page is stored; one live read is queued and the gate runs the schema's identities."""
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > uploadmod.MAX_BYTES:
            return JSONResponse({"ok": False, "code": "not_a_photo", "message": "The photo is larger than 20 MB."},
                                status_code=413)
    try:
        img = uploadmod.decode(bytes(data))
    except uploadmod.NotAPhoto as e:
        return JSONResponse({"ok": False, "code": "not_a_photo", "message": str(e)}, status_code=422)
    del data
    return _queue_test(request, slug, img)


@router.post("/api/builder/test/{slug}/sample/{name}")
def builder_test_sample(slug: str, name: str, request: Request):
    if name == "ine_filled":
        img = Image.open(REPO / "tests" / "fixtures" / "masked_escaner.jpg").convert("RGB")
    else:
        try:
            img = Image.open(io.BytesIO(sample_png(name))).convert("RGB")
        except KeyError:
            raise HTTPException(404, "unknown sample")
    return _queue_test(request, slug, img)


@router.get("/builder/test/{tid}.jpg")
def builder_test_image(tid: str):
    p = masked_test_page(tid)
    if p is None:
        raise HTTPException(404, "unknown test page")
    return Response(p.read_bytes(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get("/api/builder/job/{job_id}")
def builder_job(job_id: str, request: Request):
    m = builder_live(request)
    job = m.jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    return {"state": job.state, "position": m.position(job), "done": job.done,
            "elapsed_s": round(time.time() - job.created, 1),
            "events": [e for e in job.events if e.get("type") != "field"]}


def stored_read(clave: str = INE_BLANK) -> Optional[dict]:
    """The last recorded Gemma read of a page in our measured run (results/calls_gemma.jsonl)."""
    p = REPO / "results" / "calls_gemma.jsonl"
    last = None
    try:
        with p.open(encoding="utf-8") as fh:
            for ln in fh:
                if f'"{clave}"' in ln:
                    r = json.loads(ln)
                    if r.get("clave") == clave:
                        last = r
    except OSError:
        return None
    return last


@router.post("/api/builder/gate/{slug}")
async def builder_gate_stored(slug: str, request: Request):
    """Gate a stored read (no model call): the recorded read of the INE stand-in page, checked with the SAVED
    schema, next to the verdict recorded in the measured run with the original schema."""
    from twohands import reader
    s = schema_for(slug)
    r = stored_read()
    if r is None:
        raise HTTPException(404, "no stored read")
    g = gatemod.gate(reader.parse(r.get("content") or ""), s)
    return {"clave": r["clave"], "model": r.get("model"), "recorded_accepted": r.get("accepted"), **gate_view(g, s)}
