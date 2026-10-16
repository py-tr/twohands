"""The price and the buyer lines, from ONE config (app/pricing.py, app/buyer.py), in every doc that states them. No model call.

    python scripts/price_check.py --check   # exit 1 on any mismatch (make eval)

Checks: the measured inputs in app/pricing.py equal app/data/headline.json; the contingency is derived, not typed; each
doc states the current price lines word for word and no stale price; the INE-metric score is labelled, shown beside
the accepted-set result, and never in one sentence with the 2024 entrant's 75%; no forbidden overclaim.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from app import buyer, pricing  # noqa: E402

DOCS = {
    "docs/BUSINESS.md": ("price_long", "anchor", "contingency", "contingency_basis", "ex_morelos", "fx", "self_serve"),
    "slides/slides.md": ("price_long", "anchor", "contingency", "ex_morelos", "ex_largest", "ex_federal"),
    "README.md": ("price_long", "contingency", "ex_morelos"),
    "docs/NUMBERS.md": ("price_long", "contingency", "fx"),
    "submission/lablab.md": ("price_long", "contingency", "ex_morelos"),
}
STALE = ["$100 per 1,000", "per 1,000 forms audited", "about $100 to $2,100", "0.05% of", "ABBYY page costs",
         "we would have won", "We would have won", "passed INE's test", "recount savings will", "gross margin", " margin "]
SCAN = list(DOCS) + ["templates/home.html", "templates/audit_request.html", "templates/audit_report.html"]


def sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+|\n\s*\n|\n- |\n\d+\. ", " ".join(text.split("\n ")))


def check() -> list[str]:
    bad = []
    H = json.loads((REPO / "app" / "data" / "headline.json").read_text(encoding="utf-8"))
    if (pricing.CONFIRMED, pricing.READ_FORMS, pricing.DISPUTED) != (H["keying_errors"], H["read"], H["disagree"]):
        bad.append("app/pricing.py measured inputs != app/data/headline.json")
    if pricing.contingency_usd() != math.floor(pricing.PRICE_PER_FORM_USD * H["read"] / H["keying_errors"]):
        bad.append("contingency not derived from the measured precision")
    cpf = (H.get("gemma") or {}).get("cost_per_form")
    if cpf is not None and round(cpf, 6) != pricing.COMPUTE_PER_FORM_USD:
        bad.append(f"compute per form {pricing.COMPUTE_PER_FORM_USD} != headline {cpf}")
    T = pricing.texts()
    for doc, keys in DOCS.items():
        s = " ".join((REPO / doc).read_text(encoding="utf-8").split())
        for k in keys:
            if " ".join(T[k].split()) not in s:
                bad.append(f"{doc}: missing the current '{k}' line")
    for doc in ("docs/BUSINESS.md", "slides/slides.md"):
        s = " ".join((REPO / doc).read_text(encoding="utf-8").split())
        IC = buyer.ine_card()
        must = [IC["title"], IC["pilot"], IC["label"], IC["score"], IC["beside"]] + [t for t, _ in IC["lines"]]
        must += [m["text"] for m in buyer.NEXT_MARKETS] + [buyer.PERU] + [m["text"] for m in buyer.market_lines()]
        CL = buyer.cost_lines(H)
        must += [CL["main"], CL["preliminary"]] if CL else ["(app/data/national_counts.json missing)"]
        for m in must:
            if " ".join(m.split()) not in s:
                bad.append(f"{doc}: missing '{m[:60]}...'")
    for doc in ("docs/BUSINESS.md", "README.md", "submission/lablab.md"):   # one product, one buyer; the contact flag
        s = " ".join((REPO / doc).read_text(encoding="utf-8").replace("**", "").split())
        for m in (buyer.OFFER_2027, buyer.contact_line(), buyer.forms_line()):
            if " ".join(m.split()) not in s:
                bad.append(f"{doc}: missing the current '{m[:50]}...'")
    if " ".join(buyer.MARKET_SIZE.split()) not in " ".join((REPO / "docs/BUSINESS.md").read_text(encoding="utf-8").split()):
        bad.append("docs/BUSINESS.md: missing the market-size line")
    m = buyer.ine_metric()
    pct = f"{m['primary_per_field_words_and_digits']['pct']:.1f}%" if m else None
    for doc in SCAN:
        text = (REPO / doc).read_text(encoding="utf-8")
        for st in STALE:
            if st in text and not (st == " margin " and doc.startswith("templates")):
                bad.append(f"{doc}: stale or forbidden '{st.strip()}'")
        if pct:
            for sen in sentences(text):
                if "75%" in sen and pct in sen:
                    bad.append(f"{doc}: the INE-metric score and the entrant's 75% in one sentence")
    return bad


def main(argv=None) -> int:
    bad = check()
    print(f"price_check --check: {len(bad)} mismatches" + ("".join(f"\n  - {b}" for b in bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
