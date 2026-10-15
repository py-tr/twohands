"""Two Hands on printed receipts: an audit of the CORD v2 benchmark's own labels (PROTOCOL_CORD.md).

A receipt has no words-vs-digits redundancy (a till prints every amount once), so the only check is its
arithmetic (``schemas/cord_receipt.yaml`` identities). This module holds:

- ``num``             CORD / printed amount string -> int (thousands separators, 'Rp', '@', signs, cents);
- ``from_cord``       CORD ``gt_parse`` -> the same record shape the reader returns (so labels and reads share code);
- ``identities``      the four identities with the stated rounding tolerance;
- ``gate``            accepted fields / touchless receipt, from a read;
- ``SYS`` / ``build_prompt`` / ``prompt_sha256``  the FROZEN receipt prompt;
- ``build_body`` / ``read``  one call per receipt through the core client (``amd.chat``: shared rate limiter,
                      429/5xx backoff) and the core parser (``reader.parse``); the core is imported, never edited;
- ``score`` / ``disagreements`` / ``crop_box``  scoring and adjudication stubs (no model call).

No function here is run against the model until the protocol, schema, code, tests and manifest are committed.
"""
from __future__ import annotations

import hashlib
import io
import re
import time
from typing import Any, Optional

from PIL import Image

from twohands import reader
from twohands import schema as schemamod

SCHEMA = "cord_receipt"
AMOUNT_FIELDS = ["subtotal", "tax", "service", "discount", "total", "cash", "card", "emoney", "change"]
MODEL = "gemma"            # pre-registered reader (PROTOCOL_CORD.md section 4)


def load() -> dict:
    return schemamod.load(SCHEMA)


# ---------------------------------------------------------------- numbers
def num(x: Any) -> Optional[int]:
    """'60.000' -> 60000, '24,000' -> 24000, '45,000.00' -> 45000, '9.500,00' -> 9500, 'Rp. 111,000' -> 111000,
    '-2 600' -> -2600, '(0)' -> 0, 'x2' / '2X' / '1.00xITEMs' -> 2 / 2 / 1. A trailing separator followed by one or
    two digits is a decimal part (dropped when zero, rounded otherwise); any other '.' or ',' is a thousands
    separator. Text with no digit -> None. Ints pass through; floats are rounded."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return int(round(x))
    s = str(x).strip()
    if not re.search(r"\d", s):
        return None
    neg = s.startswith("-") or s.startswith("(") and s.endswith(")") and not s.startswith("(Qty")
    m = re.search(r"\d[\d.,\s]*", s)          # first run of digits / separators
    t = re.sub(r"\s", "", m.group(0)).rstrip(".,")
    frac = 0.0
    p = max(t.rfind("."), t.rfind(","))
    if p != -1 and len(t) - p - 1 in (1, 2):       # decimal part
        frac = float("0." + t[p + 1:])
        t = t[:p]
    digits = re.sub(r"[.,]", "", t)
    if not digits:
        return None
    v = int(round(int(digits) + frac))
    return -v if neg else v


def amount(x: Any) -> Optional[int]:
    """An amount as a non-negative number (discounts are printed '-60.000' or '(0)'; the sign is the identity's).
    A list (CORD labels a field printed on two lines): the same amount repeated (cash ['100,000', '100,000'], printed
    twice) is that amount; different amounts (tax ['6,818', '0']) are summed."""
    if isinstance(x, list):
        vals = [v for v in (amount(y) for y in x) if v is not None]
        if not vals:
            return None
        return vals[0] if len(set(vals)) == 1 else sum(vals)
    v = num(x)
    return None if v is None else abs(v)


# ---------------------------------------------------------------- CORD labels -> record
def _as_list(v) -> list:
    return v if isinstance(v, list) else ([v] if isinstance(v, dict) else [])


def from_cord(gt_parse: dict) -> dict:
    """CORD ``gt_parse`` -> {"items": [{name, count, unit_price, price, discount, subs:[{name,count,price}]}],
    subtotal, tax, service, discount, total, cash, card, emoney, change}. Absent -> None. Discounts positive."""
    items = []
    for it in _as_list(gt_parse.get("menu")):
        subs = [{"name": sb.get("nm"), "count": amount(sb.get("cnt")), "price": amount(sb.get("price"))}
                for sb in _as_list(it.get("sub"))]
        disc = it.get("discountprice")
        items.append({"name": it.get("nm"), "count": amount(it.get("cnt")), "unit_price": amount(it.get("unitprice")),
                      "price": amount(it.get("price")),
                      "discount": None if disc is None or "%" in str(disc) else amount(disc), "subs": subs})
    st, tt = gt_parse.get("sub_total") or {}, gt_parse.get("total") or {}
    if isinstance(st, list):
        st = st[0] if st else {}
    if isinstance(tt, list):
        tt = tt[0] if tt else {}
    return {"items": items,
            "subtotal": amount(st.get("subtotal_price")), "tax": amount(st.get("tax_price")),
            "service": amount(st.get("service_price")), "discount": amount(st.get("discount_price")),
            "total": amount(tt.get("total_price")), "cash": amount(tt.get("cashprice")),
            "card": amount(tt.get("creditcardprice")), "emoney": amount(tt.get("emoneyprice")),
            "change": amount(tt.get("changeprice"))}


# ---------------------------------------------------------------- identities
def agree(a: int, b: int, tol: Optional[dict]) -> bool:
    if tol is None:
        return a == b
    return abs(a - b) <= max(tol.get("abs_min", 0), tol.get("rel", 0.0) * max(abs(a), abs(b)))


def _z(v):
    return v or 0


def identities(rec: dict, tol: Optional[dict] = "schema") -> list[dict]:
    """Each identity: {name, ok (True / False / None = not checkable: a needed term not printed), lhs, rhs, fields}.
    ``tol="schema"`` uses the stated tolerance; ``tol=None`` is exact."""
    if tol == "schema":
        tol = load().get("tolerance")
    out = []
    items = rec.get("items") or []
    # 1. line prices (+ add-on lines - line discounts) sum to subtotal
    prices = [it.get("price") for it in items]
    if items and rec.get("subtotal") is not None and None not in prices:
        lhs = sum(_z(it.get("price")) + sum(_z(sb.get("price")) for sb in it.get("subs") or [])
                  - _z(it.get("discount")) for it in items)
        out.append({"name": "line prices sum to subtotal", "ok": agree(lhs, rec["subtotal"], tol), "lhs": lhs,
                    "rhs": rec["subtotal"], "fields": ["items.price", "subtotal"]})
    else:
        out.append({"name": "line prices sum to subtotal", "ok": None})
    # 2. subtotal + tax + service - discount = total (or tax already included)
    if rec.get("subtotal") is not None and rec.get("total") is not None:
        base = rec["subtotal"] + _z(rec.get("service")) - _z(rec.get("discount"))
        lhs = base + _z(rec.get("tax"))
        ok = agree(lhs, rec["total"], tol) or (rec.get("tax") is not None and agree(base, rec["total"], tol))
        out.append({"name": "subtotal + tax + service - discount = total", "ok": ok, "lhs": lhs, "rhs": rec["total"],
                    "fields": ["subtotal", "tax", "service", "discount", "total"]})
    else:
        out.append({"name": "subtotal + tax + service - discount = total", "ok": None})
    # 3. paid - total = change
    if None not in (rec.get("cash"), rec.get("total"), rec.get("change")):
        lhs = rec["cash"] + _z(rec.get("card")) + _z(rec.get("emoney")) - rec["total"]
        out.append({"name": "paid - total = change", "ok": agree(lhs, rec["change"], tol), "lhs": lhs,
                    "rhs": rec["change"], "fields": ["cash", "card", "emoney", "total", "change"]})
    else:
        out.append({"name": "paid - total = change", "ok": None})
    # 4. count x unit price = price, per line where all three are printed
    for i, it in enumerate(items):
        if None not in (it.get("count"), it.get("unit_price"), it.get("price")):
            lhs = it["count"] * it["unit_price"]
            out.append({"name": "count x unit price = price", "item": i, "ok": agree(lhs, it["price"], tol),
                        "lhs": lhs, "rhs": it["price"],
                        "fields": [f"items[{i}].count", f"items[{i}].unit_price", f"items[{i}].price"]})
    return out


def violations(rec: dict, tol: Optional[dict] = "schema") -> list[dict]:
    return [r for r in identities(rec, tol) if r["ok"] is False]


# ---------------------------------------------------------------- the gate
def read_fields(rec: dict) -> list[str]:
    """Every amount the read printed (not null): receipt-level keys and items[i].<key>."""
    out = [k for k in AMOUNT_FIELDS if rec.get(k) is not None]
    for i, it in enumerate(rec.get("items") or []):
        out += [f"items[{i}].{k}" for k in ("count", "unit_price", "price", "discount") if it.get(k) is not None]
        out += [f"items[{i}].subs[{j}].price" for j, sb in enumerate(it.get("subs") or []) if sb.get("price") is not None]
    return out


def gate(parsed: Any, tol: Optional[dict] = "schema") -> dict:
    """{accepted (touchless receipt), routed, reasons, identities, accepted_fields, unverified_fields}.

    A field is ACCEPTED when it is a term of at least one checkable identity that holds, on a receipt where no
    checkable identity fails. The receipt is TOUCHLESS when the read parsed, a total was read, no identity failed
    and every amount read is an accepted field. Fields covered by no identity that held are 'unverified'
    (reported, never counted as accepted). Any failed identity routes the whole receipt."""
    rec = coerce(parsed)
    if rec is None:
        return {"accepted": False, "routed": True, "reasons": ["no parseable read"], "identities": [],
                "accepted_fields": [], "unverified_fields": []}
    ids = identities(rec, tol)
    reasons = [f"{r['name']}{' (line %d)' % (r['item'] + 1) if 'item' in r else ''}: {r['lhs']} != {r['rhs']}"
               for r in ids if r["ok"] is False]
    covered = set()
    if not reasons:
        for r in ids:
            if r["ok"]:
                for f in r["fields"]:
                    if f == "items.price":
                        for i, it in enumerate(rec["items"]):
                            covered.add(f"items[{i}].price")
                            covered.update(f"items[{i}].subs[{j}].price" for j in range(len(it.get("subs") or [])))
                            if it.get("discount") is not None:
                                covered.add(f"items[{i}].discount")
                    else:
                        covered.add(f)
    rf = read_fields(rec)
    acc = [f for f in rf if f in covered]
    unv = [f for f in rf if f not in covered]
    if rec.get("total") is None:
        reasons.append("total not read")
    if unv and not reasons:
        reasons.append(f"{len(unv)} amount(s) in no identity that held")
    touchless = not reasons
    return {"accepted": touchless, "routed": not touchless, "reasons": reasons, "identities": ids,
            "accepted_fields": acc if not any(r["ok"] is False for r in ids) else [], "unverified_fields": unv}


def coerce(parsed: Any) -> Optional[dict]:
    """A model reply (already JSON-decoded by ``reader.parse``) -> a record with integer amounts, or None."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), list):
        return None
    items = []
    for it in parsed["items"]:
        if not isinstance(it, dict):
            continue
        items.append({"name": it.get("name"), "count": amount(it.get("count")),
                      "unit_price": amount(it.get("unit_price")), "price": amount(it.get("price")),
                      "discount": amount(it.get("discount")),
                      "subs": [{"name": sb.get("name"), "count": amount(sb.get("count")), "price": amount(sb.get("price"))}
                               for sb in (it.get("subs") or []) if isinstance(sb, dict)]})
    out = {"items": items}
    for k in AMOUNT_FIELDS:
        out[k] = amount(parsed.get(k))
    return out


# ---------------------------------------------------------------- the reader (FROZEN for PROTOCOL_CORD.md)
SYS = ("You are a meticulous receipt transcriber. You copy exactly what is printed on the receipt, digit by digit. "
       "You never correct, infer, or recompute a value; if the receipt's arithmetic is inconsistent, you transcribe "
       "the inconsistency.")


def build_prompt(s: Optional[dict] = None) -> str:
    return """Image 1 is a photo of a printed shop or restaurant receipt (Indonesia; amounts in rupiah). Any further images zoom overlapping horizontal bands of the same receipt, top to bottom; use image 1 to keep every line in order.
Return ONLY a JSON object with exactly these keys:
{"items": [...], "subtotal": ..., "tax": ..., "service": ..., "discount": ..., "total": ..., "cash": ..., "card": ..., "emoney": ..., "change": ...}
"items": one object per purchased line, top to bottom, never skipped, merged or repeated:
  {"name": the item text as printed, "count": quantity as printed or null, "unit_price": the per-unit price if printed or null, "price": the line amount as printed or null, "discount": a discount printed for that line or null, "subs": [add-on / modifier lines printed under the item, each {"name", "count", "price"}] or []}
Receipt-level amounts, each as printed or null when the receipt does not print it:
  "subtotal" (subtotal before tax/service), "tax" (tax / PPN / PB1), "service" (service charge), "discount" (bill-level discount or voucher), "total" (the amount due), "cash" (cash tendered), "card" (paid by card), "emoney" (paid by e-money / QR), "change" (kembali / change).
Rules: (1) Every amount is an integer in rupiah with thousands separators removed: "60.000" and "60,000" are 60000; "45,000.00" is 45000. (2) Write discounts as positive numbers even when printed with a minus sign or brackets. (3) null means not printed; never 0 for a missing amount, never a value you computed. (4) Copy what is printed even if it does not add up.
Example: {"items": [{"name": "ICED TEA", "count": 2, "unit_price": 8000, "price": 16000, "discount": null, "subs": []}], "subtotal": 16000, "tax": 1600, "service": null, "discount": null, "total": 17600, "cash": 20000, "card": null, "emoney": null, "change": 2400}"""


def prompt_sha256() -> str:
    return hashlib.sha256((SYS + "\n---\n" + build_prompt()).encode("utf-8")).hexdigest()


def tiles(img: Image.Image) -> list[Image.Image]:
    """Long receipts: overlapping horizontal bands, each about 1.2x as tall as the image is wide (25% overlap),
    at most 4. A receipt no taller than 1.6x its width gets no tiles."""
    w, h = img.size
    if h <= 1.6 * w:
        return []
    n = min(4, max(2, round(h / (1.2 * w))))
    band = h / n * 1.25
    step = (h - band) / (n - 1)
    return [img.crop((0, int(i * step), w, int(min(h, i * step + band)))) for i in range(n)]


def build_body(model: str, img: Image.Image) -> dict:
    """Request body (same conventions as the core reader: no response_format, temperature 0, Qwen effort low)."""
    imgs = [img] + tiles(img)
    content = [{"type": "image_url", "image_url": {"url": reader.b64(x)}} for x in imgs]
    content.append({"type": "text", "text": build_prompt()})
    body = {"model": reader.MODELS[model], "messages": [{"role": "system", "content": SYS},
                                                         {"role": "user", "content": content}],
            "max_tokens": reader.MAX_TOKENS[model], "temperature": 0}
    if model == "qwen":
        body["reasoning_effort"] = "low"
    return body


def read(model: str, image: Image.Image | bytes, chat=None) -> dict:
    """One call through the core client (shared limiter). Returns a log row (no key, no image bytes)."""
    from twohands import amd
    chat = chat or amd.chat
    img = Image.open(io.BytesIO(image)) if isinstance(image, (bytes, bytearray)) else image
    body = build_body(model, img.convert("RGB"))
    t = time.time()
    row: dict = {"model": reader.MODELS[model], "prompt_sha256": prompt_sha256()}
    try:
        r, attempts = chat(body)
        ch = r["choices"][0]
        msg = ch.get("message") or {}
        row.update(content=msg.get("content") or "", finish_reason=ch.get("finish_reason"),
                   usage=r.get("usage", {}), attempts=attempts)
    except Exception as e:  # noqa: BLE001
        row.update(error=f"{type(e).__name__}: {str(e)[:200]}", content="")
    row["secs"] = round(time.time() - t, 1)
    row["parsed"] = reader.parse(row["content"])
    return row


# ---------------------------------------------------------------- scoring and adjudication (stubs; no model call)
def _nm(x) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(x or "").upper())


def align_items(read_items: list, label_items: list) -> list[tuple[Optional[int], Optional[int]]]:
    """Pair read lines with label lines in order: by index when the counts agree, else a monotone match on the
    normalised name (longest common subsequence). Unpaired lines are (i, None) / (None, j)."""
    if len(read_items) == len(label_items):
        return [(i, i) for i in range(len(read_items))]
    a, b = [_nm(x.get("name")) for x in read_items], [_nm(x.get("name")) for x in label_items]
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            L[i][j] = L[i + 1][j + 1] + 1 if a[i] and a[i] == b[j] else max(L[i + 1][j], L[i][j + 1])
    out, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] and a[i] == b[j]:
            out.append((i, j)); i += 1; j += 1
        elif L[i + 1][j] >= L[i][j + 1]:
            out.append((i, None)); i += 1
        else:
            out.append((None, j)); j += 1
    out += [(k, None) for k in range(i, n)] + [(None, k) for k in range(j, m)]
    return out


def field_pairs(read_rec: dict, label_rec: dict) -> list[dict]:
    """Every graded amount, as {field, read, label}. Item fields use the label's index (alignment above)."""
    out = [{"field": k, "read": read_rec.get(k), "label": label_rec.get(k)} for k in AMOUNT_FIELDS]
    for ri, li in align_items(read_rec.get("items") or [], label_rec.get("items") or []):
        r = read_rec["items"][ri] if ri is not None else {}
        lab = label_rec["items"][li] if li is not None else {}
        idx = li if li is not None else f"extra{ri}"
        for k in ("count", "unit_price", "price", "discount"):
            out.append({"field": f"items[{idx}].{k}", "read": r.get(k), "label": lab.get(k)})
    return [p for p in out if not (p["read"] is None and p["label"] is None)]


def disagreements(read_rec: dict, label_rec: dict, accepted_fields: Optional[list] = None) -> list[dict]:
    """Fields where the read and the CORD label differ (exactly; adjudication decides who is right). With
    ``accepted_fields``, only those (the primary metric's denominator)."""
    out = []
    for p in field_pairs(read_rec, label_rec):
        if accepted_fields is not None and p["field"] not in accepted_fields:
            continue
        if p["read"] != p["label"]:
            out.append(p)
    return out


VERDICTS = ("model_right", "label_right", "both_wrong", "ambiguous", "unreadable")


def score(rows: list[dict]) -> dict:
    """rows: one per receipt {gate, pairs: field_pairs, verdicts: {field: VERDICT}} (verdicts only on adjudicated
    disagreements). Truth = the CORD label unless the adjudicated image says otherwise. Returns the PROTOCOL_CORD
    section 6 metrics (counts; Wilson intervals are added by the report)."""
    acc_n = acc_right = label_errors = model_errors = touchless = 0
    for r in rows:
        touchless += bool(r["gate"]["accepted"])
        accf = set(r["gate"]["accepted_fields"])
        for p in r["pairs"]:
            v = r.get("verdicts", {}).get(p["field"])
            if p["read"] != p["label"] and v == "model_right":
                label_errors += 1
            if p["field"] not in accf:
                continue
            acc_n += 1
            right = p["read"] == p["label"] if v is None else v == "model_right"
            acc_right += right
            model_errors += not right
    return {"receipts": len(rows), "touchless": touchless, "accepted_fields": acc_n,
            "accepted_fields_right": acc_right, "accepted_field_errors": model_errors,
            "label_errors_found": label_errors}


def crop_box(ground_truth: dict, category: str, nth: int = 0, image_size: Optional[tuple] = None,
             pad: int = 12) -> Optional[tuple[int, int, int, int]]:
    """The pixel box of the nth CORD line labelled ``category`` (e.g. 'total.total_price'), from ``valid_line`` quads,
    scaled from ``meta.image_size`` to ``image_size`` when they differ, padded. For adjudication crops."""
    lines = [ln for ln in ground_truth.get("valid_line", []) if ln.get("category") == category]
    if nth >= len(lines):
        return None
    xs = [w["quad"][f"x{i}"] for w in lines[nth]["words"] for i in range(1, 5)]
    ys = [w["quad"][f"y{i}"] for w in lines[nth]["words"] for i in range(1, 5)]
    sx = sy = 1.0
    meta = (ground_truth.get("meta") or {}).get("image_size") or {}
    if image_size and meta.get("width"):
        sx, sy = image_size[0] / meta["width"], image_size[1] / meta["height"]
    return (int(min(xs) * sx) - pad, int(min(ys) * sy) - pad, int(max(xs) * sx) + pad, int(max(ys) * sy) + pad)
