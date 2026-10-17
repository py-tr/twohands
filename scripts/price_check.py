"""The price and the buyer lines, from ONE config (app/pricing.py, app/buyer.py), in every doc that states them. No model call.

    python scripts/price_check.py --check   # exit 1 on any mismatch (make eval)
    python scripts/price_check.py --sync-person   # write the current person-check count into README and lablab.md

Checks: the measured inputs in app/pricing.py equal app/data/headline.json; each doc states the current price lines word
for word and no stale price (one price: no per-error option); the "Business at a glance" table is the same in the README
and lablab.md, and every measured number in it and in their opening lines is recomputed from the raw results; the
INE-metric score is labelled, shown beside the accepted-set result, and never in one sentence with the 2024 entrant's
75%; no forbidden overclaim.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from app import buyer, pricing  # noqa: E402

DOCS = {
    "docs/BUSINESS.md": ("price_long", "anchor", "ex_morelos", "fx", "self_serve"),
    "slides/slides.md": ("price_long", "anchor", "ex_morelos_short", "ex_morelos", "ex_largest", "ex_federal"),
    "README.md": ("price_long", "ex_morelos_short", "ex_morelos"),
    "docs/NUMBERS.md": ("price_long", "fx"),
    "submission/lablab.md": ("price_long", "ex_morelos_short"),
}
STALE = ["$100 per 1,000", "per 1,000 forms audited", "about $100 to $2,100", "0.05% of", "ABBYY page costs",
         "we would have won", "We would have won", "passed INE's test", "recount savings will", "gross margin", " margin ",
         "per confirmed capture error, $0", "$5 per confirmed", "Line 2", "line 2", "contingency", "per form audited"]
GLANCE = ("README.md", "submission/lablab.md")   # the "Business at a glance" table, identical in both


def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def measured_lines(H: dict) -> list[str]:
    """The measured numbers of the README first screen and lablab.md, each recomputed from the raw results here:
    sheets read = distinct parsed sheets of the random 300 and of Colima; capture errors confirmed by the certified count
    = the 300's (headline.json) + Colima's (app/colima.py); crops per sheet = disputed / read (app/pricing.py, checked
    against headline.json above); fields per sheet = graded fields per form; hours = Colima's sheets at the best
    measured rate of the throughput sweep; Morelos's cost and its share of the PREP: app/pricing.py."""
    from app import colima
    from scripts import throughput_sweep
    sheets = set()
    for p in (REPO / "results" / "calls_gemma.jsonl", REPO / "results" / "colima" / "calls_gemma.jsonl"):
        sheets |= {r["form_id"] for r in _jsonl(p) if r.get("parsed_ok")}
    F = colima.facts()
    confirmed = H["cert_agree"] + (F or {}).get("cert_capture", 0)
    sw = throughput_sweep.summarize()
    fpm = min(sw["best_forms_per_min"], sw["rpm_limit"])
    colima_h = F["read"] / fpm / 60 if F else float("nan")
    morelos_h = pricing.MORELOS["actas"] / fpm / 60
    day = "about a day" if 18 <= morelos_h <= 36 else f"about {morelos_h:.0f} hours"
    T = pricing.texts()
    return [
        f"Gemma on AMD read {len(sheets):,} real handwritten tally sheets",
        f"{confirmed} capture errors confirmed by the certified count",
        (f"About one photo crop per sheet to look at ({T['crops_per_sheet']} measured: fields where the read and the "
         f"capture disagree), instead of re-keying about {H['graded_per_form']} fields."),
        (f"One shared AMD key audits Colima's {F['read'] if F else '?'} sheets in about {colima_h:.1f} hours and "
         f"Morelos's {pricing.MORELOS['actas']:,} in {day}."),
        T["ex_morelos_short"],
    ]


def sheets_parts() -> str:
    """What the sheets-read count is made of, in the words every doc uses: the parsed sheets of the random 300, the
    parsed sheets of Colima, and the sheets in both (counted once in the total)."""
    a = {r["form_id"] for r in _jsonl(REPO / "results" / "calls_gemma.jsonl") if r.get("parsed_ok")}
    b = {r["form_id"] for r in _jsonl(REPO / "results" / "colima" / "calls_gemma.jsonl") if r.get("parsed_ok")}
    k = len(a & b)
    both = {0: "none in both", 1: "one sheet in both"}.get(k, f"{k} sheets in both")
    return f"{len(a)} of a random 300 and Colima's {len(b):,}, {both}"


def first_screen(H: dict) -> dict:
    """The proof lines of the README's first screen (bullets "Real data", "Against the incumbent", "Checked") and of
    lablab.md's "Proof in three lines", composed from the same computed pieces: sheets read and certified-confirmed
    errors (measured_lines) with what the sheets are made of (sheets_parts; lablab's short description too), the BCS head-to-head (results/ieebcs/score.json via scripts/ieebcs_score.short_line /
    proof_line), the Colima recall (app/colima.recall_checked / recall_proof) and the person's blind re-read of the
    AI-judged disputes (app/honest.reread_expected: data-driven, or the doc's committed state on a fresh clone).
    Returns {doc: [required line, ...]}; a None piece makes the line unsatisfiable (reported as missing)."""
    from app import colima, honest
    from scripts import ieebcs_score
    sheets, confirmed = measured_lines(H)[:2]
    sheets = sheets.rsplit(" read ", 1)[1].split(" ", 1)[0]          # "1,270"
    confirmed = confirmed.split(" ", 1)[0]                           # "49"
    sc = json.loads((REPO / "results" / "ieebcs" / "score.json").read_text(encoding="utf-8"))
    out = {}
    for doc, key in (("README.md", "readme"), ("submission/lablab.md", "lablab")):
        rr = honest.reread_expected((REPO / doc).read_text(encoding="utf-8"), H, key) or "(person re-read not complete)"
        if key == "readme":
            out[doc] = [
                (f"Real data: Gemma on AMD read {sheets} real handwritten tally sheets ({sheets_parts()}); "
                 f"{confirmed} capture errors confirmed by the certified count, each with its photo."),
                f"Against the incumbent: {ieebcs_score.short_line(sc)}.",
                f"Checked: {colima.recall_checked()}; {rr}.",
            ]
        else:
            out[doc] = [(f"Gemma on AMD read {sheets} real handwritten tally sheets ({sheets_parts()}): {confirmed} "
                         f"capture errors confirmed by the certified count, each with its photo."),
                        (f"Proof in three lines. {sheets} real tally sheets read on AMD; {confirmed} capture errors "
                         f"confirmed by the certified count. {ieebcs_score.proof_line(sc)} {colima.recall_proof()}; "
                         f"{rr}.")]
    return out


def glance_table(text: str) -> list[str]:
    t = text.replace("\r\n", "\n")
    i = t.find("**Business at a glance.**")
    if i < 0:
        return []
    rows = []
    for ln in t[i:].split("\n")[1:]:
        if ln.startswith("|"):
            rows.append(ln.strip())
        elif rows:
            break
    return rows
SCAN = list(DOCS) + ["templates/home.html", "templates/_background.html", "templates/audit_request.html", "templates/audit_report.html"]


def sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+|\n\s*\n|\n- |\n\d+\. ", " ".join(text.split("\n ")))


def check() -> list[str]:
    bad = []
    H = json.loads((REPO / "app" / "data" / "headline.json").read_text(encoding="utf-8"))
    if (pricing.CONFIRMED, pricing.READ_FORMS, pricing.DISPUTED) != (H["keying_errors"], H["read"], H["disagree"]):
        bad.append("app/pricing.py measured inputs != app/data/headline.json")
    if pricing.texts()["crops_per_sheet"] != f"{H['disagree'] / H['read']:.2f}":
        bad.append("crops per sheet != disputed / read in app/data/headline.json")
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
        # OFFER_2027 and forms_line: BUSINESS.md (and the site); the README and lablab carry the glance table instead
        more = (buyer.OFFER_2027, buyer.forms_line()) if doc == "docs/BUSINESS.md" else ()
        for m in (buyer.contact_line(),) + more:
            if " ".join(m.split()) not in s:
                bad.append(f"{doc}: missing the current '{m[:50]}...'")
    tables = {doc: glance_table((REPO / doc).read_text(encoding="utf-8")) for doc in GLANCE}
    if not all(tables.values()) or len({tuple(v) for v in tables.values()}) != 1:
        bad.append("README.md and submission/lablab.md: the 'Business at a glance' table is missing or differs")
    from app import honest
    for doc in GLANCE:   # the 52's AI-adjudicated part and its blind person check (app/state/spotcheck.json), computed
        if not honest.confirmation_in_doc((REPO / doc).read_text(encoding="utf-8"), H):
            bad.append(f"{doc}: the 52's AI-adjudicator / person-check line is not the current one "
                       f"('{(honest.confirmation(H) or {}).get('doc_tail', '')}')")
    for doc in GLANCE:
        s = " ".join((REPO / doc).read_text(encoding="utf-8").replace("**", "").split())
        for m in measured_lines(H):
            if " ".join(m.split()) not in s:
                bad.append(f"{doc}: missing the measured line '{m[:70]}...'")
    for doc, must in first_screen(H).items():   # the first-screen proof lines, composed from computed pieces
        s = " ".join((REPO / doc).read_text(encoding="utf-8").replace("**", "").split())
        bad += [f"{doc}: missing the first-screen proof line '{m}'" for m in must if " ".join(m.split()) not in s]
    from app import colima   # the Amendment 9 recall line (app/colima.recall_pitch) and the first-screen clause
    bad += [f"{m} (app/colima recall lines)" for m in colima.recall_doc_mismatches()]
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


def sync_person() -> list[str]:
    """Rewrite the 52's person-check phrase in README.md and submission/lablab.md from app/state/spotcheck.json
    (app/honest.person_phrase): "person check in progress at /check", then "checked by a person: N of 30, M agree"."""
    from app import honest, numbers
    H = numbers.headline()
    c = honest.confirmation(H)
    pat = re.compile(r"(which could\s+see both values; )" + honest.PERSON_RE.format(n=c["ai_total"]).replace(" ", r"\s+") + r"\)")
    done = []
    for doc in GLANCE:
        p = REPO / doc
        raw = p.read_bytes().decode("utf-8")
        new, k = pat.subn(lambda m: m.group(1) + c["person_phrase"] + ")", raw)
        if k == 1 and new != raw:
            p.write_bytes(new.encode("utf-8"))
            done.append(doc)
    return done


def main(argv=None) -> int:
    if "--sync-person" in (argv if argv is not None else sys.argv[1:]):
        print(f"price_check --sync-person: updated {sync_person() or 'nothing'}")
    bad = check()
    print(f"price_check --check: {len(bad)} mismatches" + ("".join(f"\n  - {b}" for b in bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
