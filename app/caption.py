"""Plain-English captions for crops that show Spanish number words, so nobody needs Spanish to judge a receipt.

    caption(clave, key_or_code) -> 'words: "ciento ochenta" = 180 · boxes: 1 8 0' (or None)

The words and the boxes come from the adjudication's evidence (results/adjudication/verdicts.json), as transcribed
from the photo; the number after "=" is computed from the words by es_to_int(), never typed. Words that do not parse
as one clean number are shown as written, without a number.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from typing import Optional

from twohands import REPO

UNITS = {"cero": 0, "uno": 1, "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7,
         "ocho": 8, "nueve": 9}
TEENS = {"diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
         "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidos": 22,
         "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
         "veintiocho": 28, "veintinueve": 29}
TENS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
HUNDREDS = {"cien": 100, "ciento": 100, "doscientos": 200, "trescientos": 300, "cuatrocientos": 400,
            "quinientos": 500, "seiscientos": 600, "setecientos": 700, "ochocientos": 800, "novecientos": 900}
# common hand spellings on the forms
FIX = [(r"\bdos cientos\b", "doscientos"), (r"\bd[o]s?cientos\b", "doscientos"), (r"\bdosientos\b", "doscientos"),
       (r"\btre[s]?[c]?ientos\b", "trescientos"), (r"\bcuatroscientos\b", "cuatrocientos"),
       (r"\bkatorce\b", "catorce"), (r"\bveinti (\w+)", r"veinti\1"), (r"\bdiez y (seis|siete|ocho|nueve)\b", r"dieci\1"),
       (r"\bveinte y (\w+)", r"veinti\1")]

# The helper shown beside "Judge this verdict yourself"
HELPER = [("uno", 1), ("dos", 2), ("tres", 3), ("cuatro", 4), ("cinco", 5), ("seis", 6), ("siete", 7), ("ocho", 8),
          ("nueve", 9), ("diez", 10), ("once … quince", "11 … 15"), ("dieci-", "16 … 19"), ("veinte / veinti-", "20 / 21 … 29"),
          ("treinta", 30), ("cuarenta", 40), ("cincuenta", 50), ("sesenta", 60), ("setenta", 70), ("ochenta", 80),
          ("noventa", 90), ("cien / ciento", 100), ("doscientos", 200), ("trescientos", 300), ("cuatrocientos", 400),
          ("quinientos", 500), ("seiscientos", 600), ("setecientos", 700), ("ochocientos", 800),
          ("novecientos", 900), ("y", "and"), ("cero", 0)]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[.,;:]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for a, b in FIX:
        s = re.sub(a, b, s)
    return s


def es_to_int(words: str) -> Optional[int]:
    """Spanish number words (0-999) to an int; None unless they form one clean number: [hundreds] [tens [y unit] |
    teen | unit]."""
    toks = _norm(words or "").split()
    if not toks or any(not re.fullmatch(r"[a-z]+", t) for t in toks):
        return None
    if toks == ["cero"]:
        return 0
    n, i = 0, 0
    if i < len(toks) and toks[i] in HUNDREDS:
        if toks[i] == "cien" and len(toks) > 1:
            return None
        n += HUNDREDS[toks[i]]
        i += 1
    if i < len(toks) and toks[i] in TENS:
        n += TENS[toks[i]]
        i += 1
        if i < len(toks) and toks[i] == "y":
            if i + 1 < len(toks) and toks[i + 1] in UNITS and toks[i + 1] != "cero":
                n += UNITS[toks[i + 1]]
                i += 2
            else:
                return None
    elif i < len(toks) and toks[i] in TEENS:
        n += TEENS[toks[i]]
        i += 1
    elif i < len(toks) and toks[i] in UNITS and toks[i] != "cero":
        n += UNITS[toks[i]]
        i += 1
    if i != len(toks) or n == 0:
        return None
    return n


_WORDS = re.compile(r'words[^"]{0,24}?"([^"]+)"', re.I)
_BOXES = re.compile(r"boxes ((?:[0-9_?](?: |$|(?=[;,)(])))+)")


def parse_evidence(ev: str) -> dict:
    w = _WORDS.search(ev or "")
    b = _BOXES.search(ev or "")
    return {"words": w.group(1).strip() if w else None, "boxes": b.group(1).strip() if b else None}


def text(words: Optional[str], boxes: Optional[str]) -> Optional[str]:
    parts = []
    if words:
        n = es_to_int(words)
        parts.append(f'words: "{words}"' + (f" = {n}" if n is not None else ""))
    if boxes:
        parts.append(f"boxes: {boxes}")
    return " · ".join(parts) or None


@lru_cache(maxsize=1)
def _verdicts() -> dict:
    try:
        return json.loads((REPO / "results" / "adjudication" / "verdicts.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def caption(clave: str, key_or_code: str) -> Optional[str]:
    """The English caption of one adjudicated field, by INE key (MORENA) or public code (OPT07); None if unknown."""
    from app import store as storemod
    key = key_or_code if f"{clave}__{key_or_code}" in _verdicts() else (storemod.key_of(key_or_code) or key_or_code)
    v = _verdicts().get(f"{clave}__{key}")
    if not v:
        return None
    p = parse_evidence(v.get("evidence", ""))
    return text(p["words"], p["boxes"])
