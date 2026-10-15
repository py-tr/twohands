"""The reader: masked page + 4 masked tiles -> one request -> every value with the printed row label beside it.

The prompt is built from the schema and FROZEN for the pre-registered run (``prompt_sha256``). Section 6
rows are deliberately NOT named in the prompt: the model must report the logos / text it sees on each row,
so a skipped or doubled row shows up as a label mismatch instead of a silent column shift.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import time
from pathlib import Path

from PIL import Image

from twohands import mask as maskmod
from twohands import schema as schemamod

MODELS = {"gemma": "Gemma-4-31B-IT", "qwen": "Qwen3.8-27B"}
MAX_TOKENS = {"gemma": 2000, "qwen": 6000}
B64_MAXSIDE = 2400
B64_QUALITY = 88

SYS = ("You are a meticulous election-records transcriber. You copy exactly what is printed and handwritten on the "
       "form, digit by digit. You never correct, infer, or recompute a value; if the paper is inconsistent, you "
       "transcribe the inconsistency.")


def build_prompt(s: dict) -> str:
    tiles = s["layout"]["tiles"]
    imgs = " ".join(f"Image {i + 2} zooms {t['says']}." for i, t in enumerate(tiles))
    head = [f for f in s["fields"] if not f.get("vote") and f["key"] != "TOTAL"]
    nrows = len(s["fields"]) - len(head)
    sec = "\n".join(f"  {i + 1}. {f['where']}" for i, f in enumerate(head))
    return f"""This is a Mexican INE 2024 'Acta de Escrutinio y Computo de Casilla de la eleccion de Presidencia' (federal form, type 2).
Image 1 is the whole form; its right-hand column is blacked out for privacy (ignore it). {imgs} Tiles overlap; use image 1 to keep every row aligned.
Every quantity is written twice: in words ('Con letra') and in digit boxes ('Con numero'). Transcribe BOTH, independently.
Return ONLY a JSON object {{"values": [...]}} with exactly {len(head) + nrows} items, in this order:
First the {len(head)} section totals:
{sec}
Then the {nrows} rows of section 6 'Resultados de la votacion', top to bottom, ending with the TOTAL row.
Each item is {{"label": the printed label of that line, "n": integer from the digit boxes or null if the boxes are empty/illegible, "w": integer meaning of the words or null if empty/illegible}}.
The label: for a section total, its printed section title; for a section 6 row, the party logos printed at the left of that row joined with '+' (e.g. "PAN", "PRI+PRD"), or the printed text when the row has no logo (e.g. "VOTOS NULOS"). In the coalition rows the logos sit in fixed slots and some slots are empty, so the rows differ: list only the logos actually printed on that row. Report the label you SEE on that row; do not assume it.
Important: (1) Section 6 has exactly {nrows} rows; count them, never skip, merge or repeat a row.
(2) Digit boxes are often written faintly or in thin pen; a faint '0 0 0' is 0, not null. Use null only when the boxes are truly blank.
(3) Read the words independently of the digits; if they disagree, report both as written (do not make them agree). Leading zeros in boxes (0 6 9) mean 69.
(4) If a value is crossed out and rewritten, use the final value and add "fix": true to that item.
Example item: {{"label": "PAN", "n": 69, "w": 69}}"""


def prompt_sha256(s: dict | None = None) -> str:
    s = s or schemamod.load()
    return hashlib.sha256((SYS + "\n---\n" + build_prompt(s)).encode("utf-8")).hexdigest()


def b64(im: Image.Image) -> str:
    im = im.convert("RGB")
    im.thumbnail((B64_MAXSIDE, B64_MAXSIDE))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=B64_QUALITY)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_body(model: str, page: Image.Image, s: dict | None = None) -> dict:
    """Request body. No response_format (it breaks Gemma with images); Qwen reasoning_effort low."""
    s = s or schemamod.load()
    imgs = [page] + maskmod.tiles(page, s)
    content = [{"type": "image_url", "image_url": {"url": b64(x)}} for x in imgs]
    content.append({"type": "text", "text": build_prompt(s)})
    body = {"model": MODELS[model], "messages": [{"role": "system", "content": SYS},
                                                  {"role": "user", "content": content}],
            "max_tokens": MAX_TOKENS[model], "temperature": 0}
    if model == "qwen":
        body["reasoning_effort"] = "low"
    return body


def parse(s: str):
    """The FIRST complete JSON object that holds a 'values' list (or any dict of >= 5 keys); trailing garbage
    (degenerate tails), think blocks, code fences and leading zeros ("n": 003) are tolerated."""
    s = re.sub(r"<think>.*?</think>", "", s or "", flags=re.S)
    s = re.sub(r"```(?:json)?", "", s)
    s = re.sub(r"(:\s*)0+(\d)", r"\1\2", s)
    dec = json.JSONDecoder()
    i = s.find("{")
    while i != -1:
        try:
            obj, _ = dec.raw_decode(s, i)
            if isinstance(obj, dict) and (isinstance(obj.get("values"), list) or len(obj) >= 5):
                return obj
        except ValueError:
            pass
        i = s.find("{", i + 1)
    return None


def read(model: str, page_path: str | Path, s: dict | None = None, chat=None) -> dict:
    """One call. Returns a log row (no key, no image bytes)."""
    from twohands import amd
    chat = chat or amd.chat
    s = s or schemamod.load()
    page = Image.open(page_path)
    body = build_body(model, page, s)
    t = time.time()
    row: dict = {"model": MODELS[model]}
    try:
        r, attempts = chat(body)
        ch = r["choices"][0]
        msg = ch.get("message") or {}
        row.update(content=msg.get("content") or "", finish_reason=ch.get("finish_reason"),
                   usage=r.get("usage", {}), attempts=attempts)
    except Exception as e:  # noqa: BLE001
        row.update(error=f"{type(e).__name__}: {str(e)[:200]}", content="")
    row["secs"] = round(time.time() - t, 1)
    row["parsed"] = parse(row["content"])
    return row
