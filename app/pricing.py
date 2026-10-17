"""THE price. One config value per line; every page, the request form, BUSINESS.md, the README and the slides state it
from here. `scripts/price_check.py --check` (make eval) fails if a doc states anything else.

Proposal, not measured. Sources for each anchor are in SOURCES; the FX rate is the one rate used for every MXN <-> USD
conversion in the entry.
"""
from __future__ import annotations

import math

# ------------------------------------------------------------------ the config
PRICE_PER_FORM_USD = 1                 # the one price: per sheet audited (proposed)
SELF_SERVE_PER_FORM_USD = 0.10         # footnote only: CLI / MCP, the client reviews its own disputes
FX_MXN_PER_USD = 18.3835               # ECB reference rate, 2026-10-16
FX_DATE = "2026-10-16"

# ------------------------------------------------------------------ measured / cited inputs
CONFIRMED, READ_FORMS, DISPUTED = 52, 289, 267          # app/data/headline.json (keying_errors, read, disagree)
COMPUTE_PER_FORM_USD = 0.000144                         # mean over 289 Gemma reads, results/calls_gemma.jsonl
REVIEW_SECONDS_PER_CROP = 20                            # GUESS (no citable per-field time)
REVIEW_WAGE_USD_H = (18, 25)                            # in-house US data-entry operator, Outsource Accelerator
INE_LINE_MXN, INE_ACTAS = 9_500_000, 170_648            # INE CCOE report p. 4; PREP 2024 CSV header ACTAS_ESPERADAS
MORELOS = {"actas": 7_802, "prep_mxn": 26_598_000, "audit_mxn": 1_508_000}   # IMPEPAC Informe Final PREP 23-24, p. 56
LARGEST = ("Estado de México", 20_908)                  # PREP 2024 CSV, presidential sheets per state
NATIONAL = 169_005                                      # PREP 2024 CSV, presidential tally sheets
CEILING_MXN = (309_000, 1_145_000)                      # federal direct-award ceilings excl. VAT, PEF 2026 Anexo 9

SOURCES = {
    "fx": "https://api.frankfurter.app/latest?from=USD&to=MXN (ECB reference rate, fetched 2026-10-16)",
    "ine": "INE CCOE 10th session 26-08-2024, 'Captura Automática' report, p. 4, https://repositoriodocumental.ine.mx/xmlui/"
           "bitstream/handle/123456789/176400/ccoe-10se-26-08-2024-p17-1.pdf; actas expected: PREP 2024 CSV header",
    "morelos": "IMPEPAC, Informe Final PREP 23-24 v2.0, p. 56 'Resumen de los Costos', https://impepac.mx/wp-content/"
               "uploads/2024/07/Informe%20Final%20PREP_23-24_V_2.0.pdf",
    "wage": "https://www.outsourceaccelerator.com/glossary/data-entry/ ($18 to $25 an hour, in-house US operator)",
    "ceiling": "PEF 2026 art. 2 fr. X and Anexo 9, https://dof.gob.mx/2025/SHCP/PEF_2026.html",
    "precision": "app/data/headline.json; notes/bv-brainstorm/3-model.md section 3 (1 in 5.1 disputed fields confirmed, "
                 "180 per 1,000 forms read)",
}


# ------------------------------------------------------------------ derived (never typed by hand anywhere else)
def confirmed_per_form() -> float:
    return CONFIRMED / READ_FORMS


def mxn(usd: float) -> float:
    return usd * FX_MXN_PER_USD


def quote(forms: int) -> int:
    """$ for `forms` forms at the price, rounded up to the dollar."""
    return math.ceil(forms * PRICE_PER_FORM_USD)


def review_per_form() -> tuple[float, float]:
    h = DISPUTED / READ_FORMS * REVIEW_SECONDS_PER_CROP / 3600
    return h * REVIEW_WAGE_USD_H[0], h * REVIEW_WAGE_USD_H[1]


def ceiling_note(usd: float) -> str:
    m = mxn(usd)
    if m <= CEILING_MXN[0]:
        return "under the lowest federal direct-award ceiling"
    if m <= CEILING_MXN[1]:
        return "over the lowest federal direct-award ceiling, under the highest"
    return "over every federal direct-award ceiling: a tender"


def texts() -> dict:
    """The sentences every surface states, word for word."""
    per_acta_mxn = INE_LINE_MXN / INE_ACTAS
    r0, r1 = review_per_form()
    mor = quote(MORELOS["actas"])
    big = quote(LARGEST[1])
    nat = quote(NATIONAL)
    return {
        "price": f"${PRICE_PER_FORM_USD} per sheet audited (proposed)",
        "price_long": f"${PRICE_PER_FORM_USD} per sheet audited (proposed); first step: a paid shadow-mode pilot",
        "anchor": (f"INE's own line was MXN {INE_LINE_MXN / 1e6:.1f}M for ~{round(INE_ACTAS, -4):,} actas, about MXN "
                   f"{per_acta_mxn:.0f} (~${per_acta_mxn / FX_MXN_PER_USD:.0f}) per acta for a first capture alone"),
        "compute": f"AMD compute ${COMPUTE_PER_FORM_USD:.5f} per form (measured)",
        "review": (f"review labour for routed fields about ${r0:.2f} to ${r1:.2f} per form "
                   f"(estimate: {REVIEW_SECONDS_PER_CROP} s per disputed crop, {DISPUTED / READ_FORMS:.2f} crops per form "
                   f"measured, ${REVIEW_WAGE_USD_H[0]} to ${REVIEW_WAGE_USD_H[1]} an hour)"),
        "fx": f"MXN {FX_MXN_PER_USD} per USD (ECB, {FX_DATE})",
        "self_serve": f"Self-serve (CLI / MCP, you review your own disputes): ${SELF_SERVE_PER_FORM_USD:.2f} per form.",
        "ex_morelos": (f"Morelos, {MORELOS['actas']:,} forms: about ${round(mor, -2):,.0f} (MXN {mxn(mor) / 1e3:,.0f}k), "
                       f"{ceiling_note(mor)}"),
        "ex_largest": (f"the largest state ({LARGEST[0]}), {LARGEST[1]:,} forms: about ${round(big, -2):,.0f} "
                       f"(MXN {mxn(big) / 1e3:,.0f}k), {ceiling_note(big)}"),
        "ex_federal": (f"the federal count, {NATIONAL:,} forms: about ${round(nat, -3):,.0f} (MXN {mxn(nat) / 1e6:.1f}M), "
                       f"{ceiling_note(nat)}; INE's own line was MXN {INE_LINE_MXN / 1e6:.1f}M"),
        "ex_morelos_short": (f"Morelos paid MXN {MORELOS['prep_mxn'] / 1e6:.1f}M to run its 2024 PREP "
                             f"({MORELOS['actas']:,} sheets), including an MXN {MORELOS['audit_mxn'] / 1e6:.1f}M audit of "
                             f"the software, not of the keyed values. Our check of every sheet: about MXN "
                             f"{mxn(mor) / 1e3:,.0f}k (${round(mor, -2):,.0f}), "
                             f"{100 * mxn(mor) / MORELOS['prep_mxn']:.1f}% of that."),
        "crops_per_sheet": f"{DISPUTED / READ_FORMS:.2f}",
        "morelos_audit": (f"about {100 * mxn(mor) / MORELOS['audit_mxn']:.1f}% of "
                          f"Morelos's audit line and {100 * mxn(PRICE_PER_FORM_USD) / (MORELOS['prep_mxn'] / MORELOS['actas']):.1f}% "
                          f"of its PREP cost per acta (MXN {MORELOS['prep_mxn'] / MORELOS['actas']:,.0f}, "
                          f"~${MORELOS['prep_mxn'] / MORELOS['actas'] / FX_MXN_PER_USD:.0f})"),
    }
