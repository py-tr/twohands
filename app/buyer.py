"""The buyer section, the cost of the problem and the next markets: every sentence with its source, stated once here and
rendered by the home page; `scripts/price_check.py --check` (make eval) checks BUSINESS.md and the slides say the same.

Rules kept here (docs/BUSINESS.md): the INE-metric score is shown beside, never instead of, the accepted-set result and
never in one sentence with the 2024 entrant's 75%; no "we would have won"; INE's budget is INE's, not our revenue.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app import pricing
from app import store as storemod

REPO = Path(__file__).resolve().parents[1]
INE_URL = ("https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/176400/"
           "ccoe-10se-26-08-2024-p17-1.pdf")
INE_SRC = f"INE, PREP PEF 2023-2024, 'Captura Automática' report, CCOE 10th session 26-08-2024, {INE_URL}"
MORELOS_URL = "https://impepac.mx/wp-content/uploads/2024/07/Informe%20Final%20PREP_23-24_V_2.0.pdf"
BCS_URL = "https://www.ieebcs.org.mx/documentos/acuerdos/INFORME_FINAL_PREP_PLE_2023-2024.pdf"
GRO_URL = "https://www.iepcgro.mx/principal/uploads/gaceta/2026/7ord/acuerdo057.pdf"
ANEXO3_URL = ("https://repositoriodocumental.ine.mx/xmlui/bitstream/handle/123456789/166144/"
              "ccoe-1so-23-02-2024-p19-a3.pdf")
UAM_URL = "https://ine.mx/wp-content/uploads/2024/06/2024-PREP-InformeFinalAuditoriav1.pdf"
ONPE_URL = "https://elperuano.pe/noticia/297403-onpe-conozca-el-procedimiento-que-se-sigue-durante-el-computo-de-los-votos"

INE_TITLE = "Institutes already tried to buy machine reading"
INE_LINES = [
    ("INE put MXN 9.5M in its 2024 draft budget for an automated first capture service (PTO numeral 30), a different "
     "step from our check, and bought none (last line).", "p. 4"),
    ("IPN quoted MXN 19.9M for the service.", "p. 4"),
    ("The acceptance bar was 80% agreement on words and digits.", "p. 5"),
    ("The best entrant reached 75%; INE declined it as untested in a real election, and its advisers (COTAPREP) "
     "recommended a pilot.", "pp. 5, 10"),
]
PILOT = ("Our engine is an automated capture with a referee. For 2027 we offer an independent check of a finished "
         "capture, which needs no rule change; the capture inside the loop is the pilot COTAPREP requested, offered as a "
         "pilot on 2024's own forms.")

# ------------------------------------------------------------------ one product, one buyer, for 2027
OFFER_2027 = ("Who pays in 2027: the PREP's outside auditor or its contracted operator, for an independent check of a "
              "finished capture, field by field against the photo. It needs no rule change: it is an outside check, "
              "which is what we measured. A model as the regulated second capture (PTO numeral 33) needs the "
              "institute's governing body to approve it after INE's opinion (RE art. 339); that is the longer-term "
              "path, not the 2027 product.")
MARKET_SIZE = ("How big (our estimate): about 170,000 federal actas (169,005 presidential "
               "sheets in 2024, one per polling station) plus the local actas of the 32 local processes, two to three "
               "per polling station where a state elects two or three local offices (Morelos 2024: 7,802 local actas "
               "for three offices), so roughly 500,000 to 700,000 actas in a concurrent year. Mexico's PREPs are the "
               "beachhead; the same field-level check "
               "applies wherever keyed values must match paper.")
MARKET_SIZE_SRC = ("PREP 2024 CSV (169,005 presidential sheets); IMPEPAC Informe Final PREP 23-24, pp. 3-4 (Morelos "
                   "local actas); INE Central Electoral 2026-07-30 (32 concurrent local processes). The 2-3 local actas "
                   "per polling station is our estimate.")

# ------------------------------------------------------------------ contact status: ONE flag, flipped by the user
CONTACT = {"contacted": False, "date": None, "who": None}   # set contacted=True, date="YYYY-MM-DD", who="..." once sent


def contact_line() -> str:
    """Empty until the user flips CONTACT; then one dated, factual line (a proposal sent is not a sale)."""
    if not CONTACT["contacted"]:
        return ""
    return f"Status: first proposal sent on {CONTACT['date']} to {CONTACT['who']}."


def forms_line() -> str:
    """Which form the buyer processes, and the status of our local-acta evidence (the BCS head-to-head)."""
    from app import ieebcs_card
    try:
        d = ieebcs_card.load()
    except Exception:  # noqa: BLE001
        d = None
    local = ("Our local evidence is the Baja California Sur head-to-head on local actas (PROTOCOL_IEEBCS.md): scored "
             "(the head-to-head card)." if d else
             "Local actas are next: a pre-registered head-to-head on Baja California Sur's 2024 local actas, read on "
             "AMD (PROTOCOL_IEEBCS.md).")
    return ("Which form: state institutes (OPLEs) process local actas (governor, local deputies, municipalities). The "
            "presidential forms we measured (and the Senate forms we read) are federal, processed by INE. " + local)
METRIC_LABEL = ("INE's 2024 acceptance metric as we read it from the report, computed on our existing reads after they "
                "were made; the definition was committed before computation; not the same test set or conditions as "
                "INE's trial.")


def _colima() -> Optional[dict]:
    """The Colima complete-state audit (PROTOCOL Amendment 8b), only once its finished report exists. report.json is
    written by score-colima from app/colima.py (its card line), and checked by score-colima --check."""
    d = storemod._jload(REPO / "results" / "colima" / "report.json", None)
    if not d or not d.get("finished") or not d.get("forms"):
        return None
    return {"text": d.get("card") or f"Here it is: Colima, {d['forms']:,} forms, audited, with receipts.",
            "href": d.get("href") or "/results#colima"}


def ine_metric() -> Optional[dict]:
    return storemod._jload(storemod.DATA / "ine_metric.json", None)


def ine_card() -> dict:
    m = ine_metric()
    T = storemod._jload(storemod.DATA / "two_reader_300.json", None) or {}
    t2 = (T.get("tiers") or {}).get("two_reader") or {}
    score = None
    if m:
        p = m["primary_per_field_words_and_digits"]
        score = (f"On that metric as we read it, Gemma's existing reads of our pre-registered 300 agree with the "
                 f"official capture in words and digits on {p['pct']:.1f}% of fields ({p['k']:,} of {p['n']:,}; failed "
                 f"reads and blank or illegible captures count against us).")
    from app.numbers import checked_line
    beside = (f"Beside it, the result that decides acceptance: {t2['errors']} wrong of {t2['fields']:,} accepted fields "
              f"(two readers, the paper's sums as referee), judged {checked_line()}." if t2 else None)
    return {"title": INE_TITLE, "lines": INE_LINES, "source": INE_SRC, "url": INE_URL, "pilot": PILOT,
            "colima": _colima(), "score": score, "label": METRIC_LABEL, "beside": beside,
            "def_src": "results/ine_metric_DEFINITION.md (committed before computation); results/ine_metric.md"}


def market_lines() -> list[dict]:
    """The business section, in order after the INE card: Morelos, BCS, the window, the channel."""
    t = pricing.texts()
    M = pricing.MORELOS
    return [
        {"k": "morelos",
         "text": (f"Morelos paid MXN {M['prep_mxn'] / 1e6:.1f}M for its 2024 PREP: {M['actas']:,} actas expected, 110 "
                  f"capture-and-verification posts, and an MXN {M['audit_mxn'] / 1e6:.1f}M outside audit of the system, "
                  f"which by rule checks the software, not the keyed values against the paper. We check every value for "
                  f"${pricing.PRICE_PER_FORM_USD} per acta, {t['morelos_audit']}."),
         "source": f"IMPEPAC, Informe Final PREP 23-24 v2.0, p. 56, {MORELOS_URL}; audit scope: RE art. 347 numeral 1; "
                   f"INE's 2024 audit (UAM-I), PDF p. 7, {UAM_URL}"},
        {"k": "bcs",
         "text": ("Baja California Sur bought an AI first capture by direct award (Google Document AI, MXN 93,834.49); "
                  "it matched the human capture on 2.88% of actas and 62.84% of fields. A machine already keys; the "
                  "question is who referees it."),
         "source": f"IEEBCS, Informe final del PREP 2023-2024, pp. 19 and 31, {BCS_URL}"},
        {"k": "window",
         "text": ("Every state institute decides whether to run its PREP alone or with a third party at least six months "
                  "before election day: for 6 June 2027, by about 6 December 2026. Guerrero has already decided: "
                  "in-house, \"con acompañamiento de un ente especializado\"."),
         "source": f"Anexo 13 numeral 33 punto 7, as cited in IEPC Guerrero Acuerdo 057/SO/16-07-2026, considerando XI "
                   f"and XXVI-XXVII, {GRO_URL}"},
        {"k": "channel",
         "text": ("The 2027 buyer is the outside auditor or the contracted PREP operator, paid by the state institute "
                  "(OPLE). "
                  "At least 13 of the 17 outsourced 2024 state PREPs went to three firms: Informática Electoral S.C. "
                  "(at least 8 states), Grupo Proisi (4) and PoderNet (1)."),
         "source": f"INE UTSI, Anexo 3 'Terceros que auxiliarán a los OPL', Feb 2024, {ANEXO3_URL}; Morelos: IMPEPAC "
                   f"monthly PREP report, March 2024, p. 19; Campeche: Por Esto, 12 Mar 2024 (press)"},
    ]


def cost_lines(H: dict) -> Optional[dict]:
    """The cost of the problem (never the hero): app/data/national_counts.json + the 300's certified-count check."""
    d = storemod._jload(storemod.DATA / "national_counts.json", None)
    if not d or not H:
        return None
    from app.numbers import CITED
    b = CITED["base_rate"]
    return {
        "main": (f"On the {d['not_recounted']:,} polling stations that were not recounted, INE's two official records of "
                 f"the same paper, the preliminary capture and the certified count, disagree on at least one vote field "
                 f"in {d['not_recounted_differ']:,} ({d['not_recounted_differ_pct']}%). A difference says two captures "
                 f"disagree, not which one is right; the photo does. On our 300, the photo sided with the certified "
                 f"count on {H['cert_agree']} of the {H['cert_covered']} it covered."),
        "preliminary": "The preliminary count is preliminary by design; the certified count is the official result.",
        "rowsum": (f"{b['text']} ({b['num']} of {b['den']}) of fully captured national forms fail their own row sum in "
                   f"the official capture."),
        "illegible": (f"The official capture recorded {d['ilegible_fields']:,} fields as \"Ilegible\" on "
                      f"{d['actas_with_ilegible']:,} actas."),
        "source": ("results/national_counts.md (scripts/national_counts.py, PREP 2024 CSV and Cómputos Distritales "
                   "2024 CSV); the 300: results/adjudication/CERTIFIED.md; row sums: " + b["source"]),
    }


def synthesis(H: dict) -> Optional[str]:
    d = storemod._jload(storemod.DATA / "national_counts.json", None)
    if not d:
        return None
    from app.numbers import CITED
    return (f"The problem: INE's two official captures of the same paper disagree on {d['not_recounted_differ_pct']}% "
            f"of the polling stations that were not recounted, and {CITED['base_rate']['text']} of captured forms fail "
            f"their own row sum. The gap: the mandated audit checks the software, not the keyed values. The appetite: INE "
            f"tried to buy an automated first capture in 2024 (an MXN 9.5M draft line, unspent), set an 80% bar that no "
            f"entrant met, and its advisers asked for a pilot.")


NEXT_MARKETS = [
    {"k": "hmis",
     "text": ("Health facility monthly reports (HMIS / DHIS2): WHO's Data Quality Review recounts the paper source "
              "documents against what was keyed into the national database, and DHIS2 is the national health data "
              "system in 80+ low- and middle-income countries; the monthly forms carry their own totals (Kenya MOH 711A: "
              "new + re-visits = total)."),
     "source": ("WHO, Data Quality Review Module 3 (2020), https://cdn.who.int/media/docs/default-source/data-quality-"
                "pages/2021_dqa_module-3_site-assessment-framework.pdf; https://dhis2.org/about/; MOH 711A, "
                "https://tciurbanhealth.org/wp-content/uploads/2017/06/M2_-_MOH_711A_Facility_integrated_Form-3.pdf")},
    {"k": "mortgage",
     "text": ("US mortgage post-closing QC: Fannie Mae's Selling Guide makes lenders re-check at least 10% of the loans "
              "they close (or a statistical sample) every month, plus targeted selections, against the source "
              "documents; 4.4 million closed-end originations in 2023."),
     "source": ("Fannie Mae Selling Guide D1-3-01 and D1-3-02 (04/01/2026), https://selling-guide.fanniemae.com/sel/d1-3-01/"
                "lender-post-closing-quality-control-review-process; CFPB, https://www.consumerfinance.gov/data-research/"
                "hmda/summary-of-2023-data-on-mortgage-lending/")},
    {"k": "sdv",
     "text": ("Clinical-trial source data verification: a 7,000-trial analysis found it corrects 1.1% of site-entered "
              "data, while monitoring and verification take 15-30% of trial costs; pointing the monitor at the fields "
              "the paper disputes is the mechanism we measured on election forms."),
     "source": ("Medidata/TransCelerate, Clinical Leader Nov 2014, https://www.clinicalleader.com/doc/medidata-"
                "transcelerate-biopharma-inc-clinical-trial-0001; Lindblad et al., Clinical Trials 2014; 11: 205-217")},
]

PERU = ("Peru: ONPE's 2026 rule keys every acta twice, one of them by a virtual assistant (\"una de ellas, por un "
        "asistente virtual\"); same process, second country, by regulation; not measured by us.")
PERU_SRC = f"ONPE directive, Resolución Jefatural 000093-2026, as reported by El Peruano, 6 Jun 2026, {ONPE_URL}"
