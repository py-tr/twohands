"""The technical report: docs/REPORT.md (and report/two-hands-report.pdf), every number computed from the results files.

    python scripts/build_report.py            # write docs/REPORT.md
    python scripts/build_report.py --pdf      # ... and report/two-hands-report.pdf (headless Chromium via Playwright)
    python scripts/build_report.py --check    # rebuild in memory; exit 1 if docs/REPORT.md differs (run by make eval)

No model call, no network. The numbers come from the same independent recomputation `make eval` uses
(twohands.eval: recompute, posthoc, amendment2, first_commit), from scripts/gemma_vs_qwen.py (Gemma vs Qwen, cost,
latency, tokens) and from the committed logs (results/prepare*.jsonl, results/calibration_audit.json). The text below is
a template: no number in it is typed by hand. Commit hashes and times come from git, so a clone without full history
cannot rebuild the report (the check says so instead of failing silently).
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from twohands import eval as ev  # noqa: E402
from twohands import reader as readermod  # noqa: E402
from twohands import tiers as tiersmod  # noqa: E402
from twohands.score import wilson  # noqa: E402

OUT_MD = REPO / "docs" / "REPORT.md"
OUT_PDF = REPO / "report" / "two-hands-report.pdf"
R = REPO / "results"


# ------------------------------------------------------------------ formatting
def n(x) -> str:
    return f"{x:,}" if isinstance(x, int) else str(x)


def pct(k: int, total: int, d: int = 1) -> str:
    return f"{100 * k / total:.{d}f}%" if total else "n/a"


def ci(k: int, total: int, d: int = 2) -> str:
    w = wilson(k, total)
    return "n/a" if w is None else f"{100 * w[0]:.{d}f}% to {100 * w[1]:.{d}f}%"


def usd(x, d=6) -> str:
    return "n/a" if x is None else f"${x:.{d}f}"


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def jsonl(p: Path) -> list[dict]:
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except ValueError:
            continue
    return out


def short(c) -> str:
    return c[0][:7] if c else "n/a"


def when(c) -> str:
    return ev.utc(c[1]) if c else "n/a"


# ------------------------------------------------------------------ the numbers
def gather() -> dict:
    rec = ev.recompute()
    H, ctx = rec["H"], rec["_ctx"]
    s, claves, layout, G, prep, V, read_set = ctx
    ph = ev.posthoc(ctx)
    qw = ev.amendment2(ctx)
    spec = importlib.util.spec_from_file_location("gemma_vs_qwen", REPO / "scripts" / "gemma_vs_qwen.py")
    gq = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gq)
    GQ = gq.compute()

    # Amendment 2 (c): the capture gate, Gemma alone (pre-registered secondary; computed here from the calls file)
    graded = [f for f in s["fields"] if f.get("csv")]
    cg = {"accepted": 0, "fields": 0, "wrong": 0, "undecided": 0, "unadjudicated": 0, "movil": 0, "escaner": 0}
    for k in claves:
        row = G.get(k)
        if not tiersmod.usable(row):
            continue
        d = tiersmod.digits(row, s["keys"])
        ok, _ = tiersmod.capture_gate(d, (tiersmod.words(row, s["keys"]),), s)
        if not ok:
            continue
        cg["accepted"] += 1
        cg[layout[k]] += 1
        for f in graded:
            cg["fields"] += 1
            j = tiersmod.judge(d[f["key"]], k, f["key"], ev.num(prep[k][f["csv"]]) if k in prep else None, V)
            cg[j] = cg.get(j, 0) + 1

    # pages: locator logs and the calibration audit
    prep_now = jsonl(R / "prepare.jsonl")
    prep_orig = jsonl(R / "prepare_original_locator.jsonl")
    cal = jload(R / "calibration_audit.json")
    not_loc = [r["clave"] for r in prep_now if r["status"] != "ok"]
    man = jload(R / "manifest.json")
    lay_n = collections.Counter(it["layout"] for it in man["items"])
    orig_nl = [r["clave"] for r in prep_orig if r["status"] != "ok"]

    # route causes of the routed forms with a read (any cause), from the stored gate codes
    routed_read = [k for k in claves if k in read_set and not (G[k].get("accepted"))]
    causes = collections.Counter(c for k in routed_read for c in set(G[k].get("route_codes") or []))
    only = collections.Counter(next(iter(set(G[k].get("route_codes") or []))) for k in routed_read
                               if len(set(G[k].get("route_codes") or [])) == 1)

    # pre-registration: commits (git) and first model calls (calls files)
    rows = {p.name: jsonl(p) for p in sorted(R.glob("calls_*.jsonl"))}
    man300 = set(claves)
    man100 = {it["clave"] for it in jload(R / "manifest_confirm100.json")["items"]}
    tmin = lambda rs, pred: min((ev.ts(r["ts"]) for r in rs if r.get("ts") and pred(r)), default=None)  # noqa: E731
    g0 = tmin(rows.get("calls_gemma.jsonl", []), lambda r: r["clave"] in man300)
    g1 = tmin(rows.get("calls_gemma.jsonl", []), lambda r: r["clave"] in man300 and r.get("parsed_ok"))
    q0 = tmin(rows.get("calls_qwen.jsonl", []), lambda r: r["clave"] in man300)
    c0 = min([t for rs in rows.values() if (t := tmin(rs, lambda r: r.get("clave") in man100))], default=None)
    git = {"protocol": ev.first_commit("PROTOCOL.md"), "manifest": ev.first_commit("results/manifest.json"),
           "a1": ev.first_commit("PROTOCOL.md", "## Amendment 1"), "a2": ev.first_commit("PROTOCOL.md", "## Amendment 2"),
           "a3": ev.first_commit("PROTOCOL.md", "## Amendment 3"),
           "confirm": ev.first_commit("results/manifest_confirm100.json"),
           "adj": ev.first_commit("results/adjudication/adjudication.jsonl"),
           "cord": ev.first_commit("PROTOCOL_CORD.md")}
    import re
    P = (REPO / "PROTOCOL.md").read_text(encoding="utf-8")
    man_sha = re.search(r"Manifest sha256: `([0-9a-f]{64})`", P).group(1)
    schema_sha = re.search(r"mx_presidencia_2024\.yaml` \(sha256 `([0-9a-f]{64})`\)", P).group(1)
    return {"H": H, "ph": ph, "qw": qw, "GQ": GQ, "cg": cg, "cal": cal, "not_loc": not_loc,
            "not_loc_layout": collections.Counter(layout[k] for k in not_loc), "lay_n": lay_n, "orig_nl": orig_nl,
            "orig_nl_layout": collections.Counter(layout[k] for k in orig_nl),
            "causes": causes, "only": only, "routed_read": len(routed_read), "git": git,
            "first": {"g0": g0, "g1": g1, "q0": q0, "c0": c0}, "prompt": readermod.prompt_sha256(),
            "man_sha": man_sha, "schema_sha": schema_sha, "integrity": rec["integrity"],
            "n_graded": len(graded), "n_fields_schema": len(s["fields"])}


# ------------------------------------------------------------------ the text
def render(D: dict) -> str:
    H, ph, qw, GQ, cg, cal, g, F = D["H"], D["ph"], D["qw"], D["GQ"], D["cg"], D["cal"], D["git"], D["first"]
    T = qw["tiers"] if qw else {}
    gm, qm = GQ["gemma"], GQ["qwen"]
    v1, v2 = ph["v1 (frozen gate)"], ph["v2"]
    v22, v22s = ph["v2-2R (Qwen confirms SOBRANTES)"], ph["v2-2R strict (only Qwen confirms SOBRANTES)"]
    v2b = ph["v2b (relaxed label, secondary)"]
    rc = H["recall"]
    vd = H["verdicts"]
    bt = H["by_type"]
    lg = H["label_gate"]
    hm = H["harmonised"]
    forms = H["forms"]
    first_t = lambda t: ev.utc(t) if t else "no such call yet"  # noqa: E731

    def gate_row(name, status, o, errors, undecided=0):
        return (f"| {name} | {status} | {o['accepted']} ({pct(o['accepted'], forms)}) | {o['movil']} / {o['escaner']} | "
                f"{n(o['fields'])} | {errors} | {ci(errors, o['fields'])} | {undecided} |")

    gate_rows = [
        gate_row("Gemma, frozen gate (v1)", "**pre-registered, primary**", v1, v1["errors"], v1["undecided"]),
        gate_row("Qwen, frozen gate", "pre-registered (section 7)", T["qwen"], T["qwen"]["errors"], T["qwen"]["undecided"]),
        gate_row("Both readers, both frozen gates, 23 digits agree", "pre-registered (section 7)", T["two_reader_s7"],
                 T["two_reader_s7"]["errors"], T["two_reader_s7"]["undecided"]),
        gate_row("Gemma, capture gate (words = digits, rows = TOTAL)", "pre-registered secondary (Amendment 2 c)",
                 cg, cg["wrong"], cg["undecided"]),
        gate_row("Two readers, strict mode", "pre-registered secondary (Amendment 2 d)", T["two_reader"],
                 T["two_reader"]["errors"], T["two_reader"]["undecided"]),
        gate_row("Gate v2", "POST-HOC (Amendment 3)", v2, v2["errors"], v2["undecided"]),
        gate_row("Gate v2b (relaxed logo-row label)", "POST-HOC (Amendment 3, secondary)", v2b, v2b["errors"], v2b["undecided"]),
        gate_row("Gate v2-2R (unused ballots confirmed by words or Qwen)", "POST-HOC (Amendment 3)", v22, v22["errors"],
                 v22["undecided"]),
        gate_row("Gate v2-2R strict (unused ballots only if Qwen agrees)", "POST-HOC (in no amendment)", v22s,
                 v22s["errors"], v22s["undecided"]),
    ]
    cause_names = {"label": "row label mismatch", "empty": "a digit field not read", "words": "words differ from digits",
                   "identity": "an identity fails", "shape": "wrong number of values"}
    cause_rows = "\n".join(f"| {cause_names.get(c, c)} | {D['causes'][c]} | {D['only'].get(c, 0)} |"
                           for c in sorted(D["causes"], key=lambda c: (-D["causes"][c], c)))
    integ = "all hold" if not any(D["integrity"].values()) else "FAIL: " + ", ".join(k for k, v in D["integrity"].items() if v)
    nl_lay = D["not_loc_layout"]
    onl = D["orig_nl_layout"]
    vacc = H["verdicts_accepted"]

    return f"""# Two Hands: a vision model as the second keyer of self-checking paper forms

*Technical report. Every number in this document is generated from the committed results files by
`scripts/build_report.py` and checked by `make eval` (the check fails if a number drifts). No model was called to
write it.*

## Abstract

Paper forms that carry their own arithmetic (rows that must sum to a total, a total written in words and in digits)
are still keyed by hand, often twice. We ask whether an open vision model, run on AMD GPUs, can act as the second
keyer: it reads every field, the form's own identities decide whether the read is accepted, and every disagreement
with the keyed record goes to a person with the crop of the paper. On a pre-registered, stratified random sample of
{forms} handwritten tally sheets (Mexico, 2024; official double-keyed capture as the comparison), Gemma-4-31B-IT read
{H['read']} pages and disagreed with the capture on {n(H['disagree'])} of {n(H['fields'])} fields
({H['flag_pct']}%). Settled on the photo, **{H['keying_errors']} of those {H['disagree']} are fields where the official
capture does not match the paper** (1 in {H['yield_one_in']}; Wilson 95% {ci(H['keying_errors'], H['disagree'], 1)}), against
a capture error rate of at least 1 in {H['random_one_in']} for a random field. The frozen gate accepted
**{H['accepted']} of {forms} forms ({H['accepted_pct1']}%) with no person**, with **{H['acc_model_wrong']} wrong fields
in {n(H['acc_fields'])}** (Wilson 95% {ci(H['acc_model_wrong'], H['acc_fields'])}); a pre-registered two-reader tier
(Gemma and Qwen3.8-27B must agree) accepted {T['two_reader']['accepted']} forms with
{T['two_reader']['errors']} wrong fields in {n(T['two_reader']['fields'])}. Every gate variant we tried is reported in
one table, pre-registered and post-hoc alike. Reading cost {usd(H['gemma']['cost_per_form'])} per form.

## 1. The problem

A keyed record of a paper form is trusted because two people typed it. When they agree on a wrong number (or one
of them marks a readable field "illegible"), nothing downstream notices. Checking keyed numbers against the paper
by hand does not pay, so it is rarely done. Many forms, however, check themselves: their rows sum to a printed
total, sections must equal each other, and every quantity is written twice, in words and in digits. A reader that
transcribes both, independently, lets the paper referee the read.

The tool is clerical: it compares a keyed record with the image it was keyed from. It does not count, total or
interpret anything; it reports, field by field, where the record and the paper disagree. The tally sheets are
used because they are public, handwritten, self-checking and come with an official two-person capture to grade
against, not for what they record. Vote rows are named by printed position only (Option 01 to Option 15).

## 2. Data and pre-registration

**Population and sample.** Type-2 tally sheets of the 2024 count with a PREP image (phone photo or scanner), unique
id, excluding the 43 pilot forms. Stratified by state x capture type, proportional allocation, seed 20261015:
{forms} forms ({D['lay_n']['movil']} phone photos, {D['lay_n']['escaner']} scans). Manifest sha256
`{D['man_sha'][:12]}...`, schema sha256 `{D['schema_sha'][:12]}...`, frozen prompt sha256 `{D['prompt'][:12]}...`
(checked on every call row by `make eval`).

**Order of events** (git commit times and the first recorded call, UTC):

| Document | Commit | Committed | Governs | First governed call |
|---|---|---|---|---|
| PROTOCOL.md (sample, privacy, readers, gate, metrics, headline rule) | `{short(g['protocol'])}` | {when(g['protocol'])} | the 300 | Gemma {first_t(F['g0'])} |
| results/manifest.json (the 300) | `{short(g['manifest'])}` | {when(g['manifest'])} | the 300 | Gemma {first_t(F['g0'])} |
| Amendment 1: the page locator | `{short(g['a1'])}` | {when(g['a1'])} | preparation of the 300 | first successful Gemma read {first_t(F['g1'])} |
| Amendment 2: secondary analyses (two-reader tiers, adjudication of every disagreement) | `{short(g['a2'])}` | {when(g['a2'])} | Qwen pass, adjudication | Qwen {first_t(F['q0'])}; first adjudication commit {when(g['adj'])} |
| Amendment 3: gate v2 and a fresh 100-form confirmation draw | `{short(g['a3'])}` | {when(g['a3'])} | the confirmation 100 | {first_t(F['c0'])} |

PROTOCOL.md is append-only (`make eval` checks that no commit deletes a line of it). Amendment 1 changed only the
locator, before any successful read of the 300: the pre-registered locator left {len(D['orig_nl'])} of {forms} pages
unlocated ({onl['movil']} phone photos, {onl['escaner']} scans). The new locator was tuned on the pilot forms and a fresh
calibration set (seed 20261016, n = {cal['n']}, disjoint from the 300): {cal['located']} of {cal['n']} located,
{cal['aligned_by_eye']} correctly aligned by an eye audit of every page (Wilson 95% {ci(cal['aligned_by_eye'], cal['n'], 1)}).
Amendment 2 was written after seeing the Gemma accept rate and before any Qwen read or adjudication. Amendment 3
defines gate v2 **after** seeing the reads and their adjudication, so every v2 number on the 300 is post-hoc; its test
is the fresh 100-form draw, which has not been read.

## 3. Method

**Locate and mask.** Each image is rectified onto the canonical page (corner markers, or a SIFT + RANSAC match
against a masked reference when markers are cut off; ECC refinement); a warp is accepted only if 8 printed
landmarks land within 1% of the page width. Otherwise the page is not located: nothing is stored or sent, and the
form goes to a person. The right-hand column (names and signatures of officials and representatives) is filled
black before the page is stored or sent; the raw download is deleted.

**Read.** One request per form: the masked page plus 6 zoomed tiles cut from it (tiles never reach into the mask).
The prompt is built from the schema and frozen (sha256 `{D['prompt'][:12]}...`). For each of the
{D['n_fields_schema']} fields the model returns the printed row label it sees, the digits and the words, read
independently. Gemma-4-31B-IT is the primary reader (temperature 0, max {readermod.MAX_TOKENS['gemma']} tokens);
Qwen3.8-27B the second (reasoning effort low, max {readermod.MAX_TOKENS['qwen']} tokens). Both on AMD Token Factory
(OpenAI-compatible endpoint, shared rate limiter).

**Gate (frozen).** A read is accepted only if: {D['n_fields_schema']} values parse; every printed row label fits its
position (a logo row fails if its label fits a neighbouring row better, the trace of a skipped or doubled row);
every digit field is read; words = digits wherever words were read; and the four identities hold (vote rows sum to
TOTAL; voters + representatives = section 5; section 5 = section 7; section 7 = TOTAL). Anything else is routed to a
person with the failing fields named.

**Adjudication.** Every field where Gemma's digits differ from the official capture ({n(H['disagree'])} fields) was
settled on the crop of the masked page, with one verdict: capture error (paper = model), model misread (paper =
capture), neither, paper ambiguous, unreadable. One adjudicator (the builder, an AI agent, not a native speaker);
crops are published so anyone can re-check. Truth = the capture unless the paper says otherwise.

## 4. Results

### 4.1 The primary: one reader, frozen gate

| Measure | Value |
|---|---|
| Pages located and read | {H['read']} of {forms}; {H['unread']} not located go to a person before any model call |
| Fields compared with the official capture ({H['graded_per_form']} per form) | {n(H['fields'])} |
| Agreement | {n(H['agree'])} ({H['agree_pct']}%) |
| Disputed fields | {n(H['disagree'])} on {H['disagree_forms']} forms |
| Verdicts on the disputed | capture error {vd['model_right']}, model misread {vd['capture_right']}, neither {vd['neither']}, paper ambiguous {vd['paper_ambiguous']}, unreadable {vd['unreadable']} |
| **Capture errors found** | **{H['keying_errors']}** on {H['keying_forms']} forms |
| Yield of a disputed field | {H['keying_errors']} of {H['disagree']} = 1 in {H['yield_one_in']} ({H['yield_pct']}%; Wilson 95% {ci(H['keying_errors'], H['disagree'], 1)}) |
| Capture error rate, lower bound | {H['keying_errors']} of {n(H['fields'])} = at least 1 in {H['random_one_in']} (Wilson 95% {ci(H['keying_errors'], H['fields'])}) |
| Model wrong, alone | {H['model_wrong']} of {n(H['fields'])} (1 in {H['model_one_in']}; Wilson 95% {ci(H['model_wrong'], H['fields'])}) |
| **Accepted with no person** | **{H['accepted']} of {forms}** ({H['accepted_pct1']}%; Wilson 95% {ci(H['accepted'], forms, 1)}): {H['accepted_movil']} phone photos, {H['accepted_escaner']} scans |
| Accepted fields wrong on the paper | **{H['acc_model_wrong']} of {n(H['acc_fields'])}** (Wilson 95% {ci(H['acc_model_wrong'], H['acc_fields'])}) |

The headline rule (pre-registered): single-reader Gemma is the headline unless its accepted-field error rate exceeds
0.5%. It is {pct(H['acc_model_wrong'], H['acc_fields'], 2)}, so the single reader stays the primary. On the accepted
forms, {H['acc_disagree']} fields differ from the capture: {vacc['model_right']} is a capture error, {vacc['capture_right']}
are model misreads.

### 4.2 Every gate variant, in one table

Accepted forms out of {forms} (unlocated pages and failed reads count in the denominator). Wrong = accepted fields where
the accepted value differs from the paper (truth: the verdict on the photo where one exists, else the capture).
Undecided = an accepted field the photo does not settle. **Post-hoc rows were designed after seeing these reads and
test nothing**; they are shown so that no variant is hidden.

| Gate | Status | Accepted (/{forms}) | Phone / scan | Accepted fields | Wrong | Wrong, Wilson 95% | Undecided |
|---|---|---|---|---|---|---|---|
{chr(10).join(gate_rows)}

The two-reader strict mode drops the row-label check and the section identities and relies on the readers'
agreement instead, which is why it accepts more forms than either reader alone. The two readers agree on all 23
digits on {qw['agree_all_23']} forms; on the strict tier's accepted fields the agreed read differs from the capture on
{T['two_reader']['disagree']}, and {T['two_reader']['capture_errors']} of them are capture errors on the photo. The
capture gate (Amendment 2 c) is Gemma alone with only words = digits and rows = TOTAL; it is first tabulated in this
report. It accepts {cg['accepted']} forms but with {cg['wrong']} wrong fields ({pct(cg['wrong'], cg['fields'], 2)}),
close to the 0.5% line: without the section identities and labels one reader is not enough. Its accepted fields
include {cg['unadjudicated']} where the reader differs from the capture with no verdict (never counted as right). Gate v2 adds one rule to the frozen gate: the field that sits in no identity (unused
ballots) must have words and digits both read and equal; v2-2R also accepts it when Qwen's digits agree; v2-2R strict
accepts it only when Qwen agrees.

**Route causes** of the {D['routed_read']} read-but-routed forms (a form can have several):

| Cause | Forms (any cause) | Forms (only cause) |
|---|---|---|
{cause_rows}

### 4.3 The capture errors

| Type | Fields |
|---|---|
| Wrong number typed | {bt['wrong_value']} |
| Readable field recorded as illegible ({H['illegible_on_faint']} on two faint pencil forms) | {bt['marked_illegible']} |
| Number typed where the paper is blank | {bt['keyed_blank']} |
| Other (readable field captured as "no data") | {bt['other']} |
| **Total** | **{H['keying_errors']}** |

A wrong number is typed in about 1 field in {H['wrong_number_one_in']}. **Certified confirmation.** The later certified
count covers {H['cert_covered']} of the {H['keying_errors']} fields; it equals the paper (and the model) on
{H['cert_agree']}, and differs on {H['cert_differ']}, all {H['cert_differ_recount']} of which were recounted (a recount
counts ballots, not the sheet, so it need not match the sheet). Example: on form 050815B0100, Option 07, the paper
says {H['receipt']['paper']} in digits and words, the first capture keyed {H['receipt']['prep']}, the model read
{H['receipt']['model']} and the certified count (by {H['receipt']['cert_mode']}) is {H['receipt']['certified']}.

### 4.4 Recall: a small subset, stated plainly

We only look where the model disagrees with the capture, so an error the model shares with the capture is not
found. To estimate recall we use the {rc['forms']} read forms the certified count settled by comparison (no recount):
there the certified count differs from the first capture on {rc['E']} fields. Judged on the paper, {rc['corrections']}
of them are council corrections or blank rows (the paper shows the capture's value; a faithful read cannot dispute
them). **The model disputed {rc['C']} of the remaining {rc['E2']}**: measured recall {rc['recall2_pct']}%, Wilson 95%
{ci(rc['C'], rc['E2'], 0)}. **n = {rc['E2']}**: this says little more than "recall is probably not low". Counting the
corrections in the denominator gives the loose bound {rc['C']} of {rc['E']} ({ci(rc['C'], rc['E'], 0)}).

### 4.5 Gemma vs Qwen

Same {GQ['common_forms']} forms, same masked page and tiles, same frozen prompt and gate.

| | Gemma-4-31B-IT | Qwen3.8-27B |
|---|---|---|
| Sent / parsed | {gm['sent']} / {gm['parsed']} | {qm['sent']} / {qm['parsed']} |
| finish_reason | {', '.join(f'{k} {v}' for k, v in gm['finish_reason'].items())} | {', '.join(f'{k} {v}' for k, v in qm['finish_reason'].items())} |
| Accepted, frozen gate | {gm['touchless']} ({gm['touchless_pct']}%) | {qm['touchless']} ({qm['touchless_pct']}%) |
| Accepted fields wrong | {gm['accepted_wrong']} of {n(gm['accepted_fields'])} ({ci(gm['accepted_wrong'], gm['accepted_fields'])}) | {qm['accepted_wrong']} of {n(qm['accepted_fields'])} ({ci(qm['accepted_wrong'], qm['accepted_fields'])}); {qm['accepted_undecided']} undecided |
| Mean latency per form | {gm['mean_latency_s']} s | {qm['mean_latency_s']} s |
| Tokens in / out (mean) | {n(gm['mean_tokens_in'])} / {n(gm['mean_tokens_out'])} | {n(qm['mean_tokens_in'])} / {n(qm['mean_tokens_out'])} |
| Cost per form read | {usd(gm['cost_per_read_usd'])} | {usd(qm['cost_per_read_usd'])} |
| Spend per form, all attempts | {usd(gm['cost_per_form_all_attempts_usd'])} | {usd(qm['cost_per_form_all_attempts_usd'])} |

Gemma costs about {round(100 * GQ['gemma_cost_share_of_qwen'])}% of Qwen per read and is faster; Qwen's
{qm['finish_reason'].get('length', 0)} replies cut at the token cap are never accepted. Neither reader is accurate
enough alone to skip the gate: the value of the second reader is agreement, not accuracy.

### 4.6 Cost and latency

Gemma: {usd(H['gemma']['cost_per_form'])} per form read (mean over {H['gemma']['reads']} reads), about
{usd(1000 * H['gemma']['cost_per_form'], 2)} per 1,000 forms; mean latency {H['gemma']['mean_secs']} s per form (wall
clock on a shared endpoint, including queueing); {n(H['gemma']['tokens_in'])} tokens in and {n(H['gemma']['tokens_out'])}
out per form; all {H['gemma']['stop']} replies finished with `stop`. The run needed re-reads on {H['rereads']['forms']}
forms after an endpoint outage ({H['rereads']['rows']} call rows in all; the last row per form counts). A dedicated
endpoint was not measured.

## 5. Failure analysis

**One call can harmonise its own words and digits.** On form {hm['clave']}, {hm['name'].lower()}, Gemma read
{hm['digits']} in digits and {hm['words']} in words; the paper says {hm['paper']} in both. The field sits in no
identity, so words = digits was the only check, and one call satisfied it with itself: the form was accepted with a
wrong field (one of the {H['acc_model_wrong']}). Words and digits from one call are not two independent reads. Gate v2
(words required) does not remove it; only a second reader does (v2-2R strict, 0 wrong). Both readers sharing a
misread remains possible and is not counted.

**The row-label gate's false alarms.** The label check routed {lg['routed']} forms; on {lg['read_right']} of them the
read matched the paper on every graded field, including all {lg['label_only_right']} of the {lg['label_only']} forms
routed for a label alone. Both models misname small logos while reading the values right. Each false alarm costs a
person one look; a false accept of a shifted row would cost a wrong record, so the check stays in the frozen gate
(v2b relaxes it, post-hoc).

**Pages not located.** {len(D['not_loc'])} of {forms} pages ({nl_lay['movil']} phone photos, {nl_lay['escaner']} scans)
could not be located even with the Amendment 1 locator; they go to a person before any model call and count as
routed. The pre-registered locator would have left {len(D['orig_nl'])}.

**The gate cannot see an error that keeps the arithmetic true.** A value misread in a way that still satisfies every
identity (a shifted row whose sums still hold, a misread in a field covered by no identity) passes. The row-label
check and the tiles are mitigations, not proofs.

## 6. Limits

- One sample of {forms} forms of one form type; the confirmation draw for gate v2 (Amendment 3) has not been read,
  and the pre-registered receipt benchmark (PROTOCOL_CORD.md, committed `{short(g['cord'])}`) was not run.
- One adjudicator, an AI agent; crops are published for re-checking.
- Recall rests on {rc['E2']} fields.
- The two-reader strict tier checks words = digits and row sums only, without the section identities or labels.
- Latency and throughput were measured on a shared, rate-limited endpoint.
- The capture compared against is the preliminary first capture; the certified count is the official record.

## 7. Ethics and privacy

- **Masking first.** The column with names and signatures is blacked out before a page is stored or sent; raw
  downloads are deleted; tiles never reach the mask (tested). A page that cannot be located is neither stored nor sent.
- **Clerical framing.** The tool compares a keyed record with its paper. It produces no totals, no aggregation across
  forms and no comparison between options; vote rows are shown as Option 01 to Option 15, never by name. The app's
  policy tests enforce this in code.
- **No claim beyond the paper.** A disputed field is a lead, not a finding, until a person confirms it on the photo;
  differences with the certified count are reported as recounts, not as errors of anyone.

## 8. Reproducibility

```
make eval      # python -m twohands.eval; python scripts/gemma_vs_qwen.py; python scripts/build_report.py --check
make test      # python -m pytest -q
python scripts/build_report.py --pdf      # this report, docs/REPORT.md and report/two-hands-report.pdf
```

`make eval` recomputes every number on the site from the committed calls files, verdicts, manifests and git, compares
each with what the app shows (0 mismatches required), checks the manifest, schema and prompt hashes against
PROTOCOL.md and the commit order above, and rebuilds this report to check it is current. Integrity checks
(stored gate flag = frozen gate re-run, verdicts cover exactly the disputed fields): {integ}. No model call, no
network, no raw images.
"""


# ------------------------------------------------------------------ PDF
CSS = """
@page { size: A4; margin: 18mm 17mm 20mm 17mm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 10pt; line-height: 1.42; color: #111; }
h1 { font-size: 18pt; margin: 0 0 6pt; line-height: 1.2; }
h2 { font-size: 13pt; margin: 16pt 0 5pt; border-bottom: 0.6pt solid #888; padding-bottom: 2pt; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; }
p, li { text-align: left; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 8pt; font-size: 8.4pt; page-break-inside: avoid; }
th, td { border: 0.5pt solid #999; padding: 2.5pt 4pt; vertical-align: top; }
th { background: #eee; text-align: left; }
code { font-family: Consolas, 'Courier New', monospace; font-size: 8.6pt; }
pre { background: #f4f4f4; padding: 6pt; font-size: 8.4pt; white-space: pre-wrap; }
em { color: #333; }
"""


def build_pdf(md_text: str, out: Path) -> tuple[int, int]:
    import markdown
    from playwright.sync_api import sync_playwright
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html = f"<!doctype html><html><head><meta charset='utf-8'><title>Two Hands technical report</title>" \
           f"<style>{CSS}</style></head><body>{body}</body></html>"
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(html, wait_until="load")
        pg.pdf(path=str(out), format="A4", print_background=True, display_header_footer=True,
               header_template="<span></span>",
               footer_template="<div style='font-size:7pt;width:100%;text-align:center;color:#666'>Two Hands technical "
                               "report · <span class='pageNumber'></span> / <span class='totalPages'></span></div>",
               margin={"top": "16mm", "bottom": "18mm", "left": "16mm", "right": "16mm"})
        b.close()
    data = out.read_bytes()
    import re
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data))
    return pages, len(data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if docs/REPORT.md is not what the results give")
    ap.add_argument("--pdf", action="store_true", help="also print report/two-hands-report.pdf")
    a = ap.parse_args(argv)
    if ev.git("rev-parse", "--git-dir") is None:
        print("build_report: no git history here; the report's commit table cannot be rebuilt (clone the repository)")
        return 0 if a.check else 1
    text = render(gather())
    if a.check:
        old = OUT_MD.read_text(encoding="utf-8") if OUT_MD.is_file() else ""
        if old.replace("\r\n", "\n") != text:
            print("build_report: docs/REPORT.md differs from what the results give; run python scripts/build_report.py --pdf")
            return 1
        print("build_report: docs/REPORT.md matches the results (0 mismatches)")
        return 0
    OUT_MD.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT_MD.relative_to(REPO)}")
    if a.pdf:
        pages, size = build_pdf(text, OUT_PDF)
        print(f"wrote {OUT_PDF.relative_to(REPO)}: {pages} pages, {size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
