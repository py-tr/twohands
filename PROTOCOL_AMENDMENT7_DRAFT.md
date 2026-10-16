<!-- DRAFT, NOT MERGED. The main session appends the text below at the end of PROTOCOL.md (append only: no existing
line changes), fills the [brackets], and commits it BEFORE gate v3 is computed on any read of the 100-form confirmation
or the 3,000-form extension (and before any model call on either, if none has been made yet). Delete this file once
merged. -->

## Amendment 7 (2026-10-1[6] [hh:mm] UTC, before any gate-v3 read of the 100 or the 3,000): gate v3, the ballot-stock check

**Why, and what was seen.** SOBRANTES (unused ballots, section 2 of the acta) is the only field of the presidential acta
(type 2) that sits in no identity printed on the form, and **every accepted-field error on the 300 was SOBRANTES**: Gemma
010469C0400 (read 239, paper 234) and 212668C0300 (read 300, paper 379) under v1, and Qwen 090955C0200 (read 200, paper
206). Gate v3 was designed **after** seeing those reads and their adjudication; its numbers on the 300 are **post-hoc**
and labelled so (`results/ballot_stock.md` section 3). The tests of v3 are the 100-form confirmation (Amendment 3) and
the 3,000-form extension (Amendment 5), on reads that no one has gated under v3 when this amendment is committed
[state here which reads of the 100 / the 3,000 exist at commit time, if any, and that no v3 number on them was computed].

**The official identity.** A casilla receives one ballot per person on its lista nominal, plus additional ballots for
the accredited party / independent-candidate representatives, plus, where applicable, ballots for citizens with a
favourable TEPJF ruling (Reglamento de Elecciones art. 178, numeral 1, incisos a, c, d); every ballot received is either
used or left over (TEPJF Sala Superior, SUP-JIN-57/2012: boletas recibidas minus boletas sobrantes against the people
who voted / the ballots taken out of the urn). Both sources are quoted with pages in `results/ballot_stock.md`. On the
acta, VOTARON excludes the representatives (PERSONAS_Y_REP = VOTARON + REPRESENTANTES), so with LISTA_NOMINAL and
REPRESENTANTES_PP_CI (accredited representatives) taken from the **official PREP CSV**, never from the read:

    E = SOBRANTES + VOTARON + REPRESENTANTES - LISTA_NOMINAL,   D = E - REPRESENTANTES_PP_CI   (expected D = 0).

On the PREP CSV, over the identity-consistent presidential actas (VOTARON + REPRESENTANTES = SACADOS = TOTAL in the
capture; the forms a gate can accept), D = 0 exactly on 82% (básica), 78% (contigua) and 88% (extraordinaria) of actas,
while E itself sits at the allowance (median 31-34), so a literal "E in [0, k]" check would route almost every correct
form (E in [0, 20] holds for about 1% or fewer). The check is therefore made on D.

**Gate v3** (`twohands/gate_v3.py`; the frozen gate and gate v2 are not changed). Per form:
1. **The other 22 fields** are accepted iff the read passes every check of the frozen gate (section 5) except the two
   that concern SOBRANTES alone (SOBRANTES digits empty; SOBRANTES digits != words). Any other failure routes the
   whole form, as under v1 / v2.
2. **SOBRANTES** is accepted iff the other 22 fields are accepted **and all three** hold:
   - (a) **words and digits** were both read and are equal;
   - (b) **two independent reads agree**: the second reader's SOBRANTES digits equal the primary's. Second reader, in
     this order: Qwen3.8-27B's read of the same form (the second reader of Amendments 3-5); for an arm with no Qwen
     pass (Amendment 5's Gemma-only fallback), a second Gemma read of the same page on a different tiling, if one is
     run (its tiling stated in the report). No usable second read = (b) fails;
   - (c) **ballot stock**: D lies in the frozen band for the casilla type, with LISTA_NOMINAL and REPRESENTANTES_PP_CI
     from the PREP CSV: **básica [-15, 20], contigua [-11, 20], extraordinaria [-9, 16]**. A missing lista nominal or
     representatives count, or an especial casilla (no lista; none in either arm), fails (c).
   Otherwise **SOBRANTES alone is shown to a person**; the form's other 22 fields stay accepted.
3. The bands are the nearest-rank 1st and 99th percentiles of D over the identity-consistent, contabilizada,
   type-2 presidential actas of the PREP CSV (cut 2024-06-03 20:05), by casilla type, **excluding the 300, the 100 and
   the 3,000** (n = 30,407 / 33,040 / 4,288). `scripts/ballot_stock.py --check` recomputes them and fails if they move.
   By construction about 2% of correct, consistent SOBRANTES fall outside and go to a person.
4. **Secondary (reported, not the primary):** v3-emax, identical except (c) is the literal E in [0, E_max] with E_max =
   the 99th percentile of E (básica 53, contigua 53, extraordinaria 50); and the three components of v3 alone.

**Primary reader and arms.** Gemma-4-31B-IT primary, Qwen3.8-27B second, as in Amendments 3-5: (i) the 100-form
confirmation; (ii) the 3,000-form extension, as far as it was read on the box (its n reported). The same masked pages,
prompt, schema, decoding and adjudication rules as those amendments; no new read is made for v3.

**Metrics** (each arm, Gemma primary; the Qwen-primary mirror reported alongside):
- **accepted-field error rate after adjudication** (primary; criterion below): wrong / graded fields accepted under
  v3, where a routed SOBRANTES is not an accepted field; Wilson 95% CI;
- forms with the other 22 fields accepted; **touchless forms** (all 23 accepted); unlocated pages and failed reads in
  every denominator; by capture type;
- **SOBRANTES shown to a person**, split after adjudication into wrong reads caught and **correct reads routed (the
  false-alarm cost)**, and by which of (a) (b) (c) failed;
- the same for v1, v2, v2-2R strict and v3-emax, on the same reads.
Truth: as Amendment 2 / section 6. Every SOBRANTES that v3 routes and where Gemma != PREP is adjudicated on the crop,
like every disagreement on an accepted field; with no verdict, a read equal to PREP counts as correct.

**Success criterion (pre-registered):** v3's accepted-field error rate after adjudication is **<= 0.5%** in each arm
(point estimate, with its Wilson 95% CI). Reported whatever it shows: touchless forms and the SOBRANTES false-alarm
cost. If v3 fails the criterion, that is the result; nothing in this amendment changes v2's own test (Amendment 3).

**What it cannot catch, said on the site.** "Every accepted field is checked by the paper's own arithmetic, and the one
field the paper cannot check is checked against the official voter list and ballot allowance; a misread smaller than
that check's tolerance (at most 20 ballots) can still pass on that field alone." (On the 300, post-hoc: the band alone
catches 300 vs 379 and lets 239 vs 234 and Qwen's 200 vs 206 through; the two-read rule catches 239 vs 234.)

**Post-hoc on the 300 (labelled, not a test):** `results/ballot_stock.md` section 3 / `results/ballot_stock.json`.
Gemma primary: v3 accepts 22 fields on 56 forms, 38 touchless (v2: 47, v1: 55), 1,214 accepted graded fields (v2:
1,034), 0 errors; 3 wrong SOBRANTES caught (212668C0300, 010469C0400, 154383E0100), 15 correct SOBRANTES sent to a
person. The band alone: catches 212668C0300 only, 0 correct SOBRANTES routed.
