"""Ballot stock: the one check SOBRANTES can get (PROTOCOL Amendment 7, gate v3). No model call.

    python scripts/ballot_stock.py           # -> results/ballot_stock.md + results/ballot_stock.json
    python scripts/ballot_stock.py --check   # recompute; exit 1 if the frozen bands or the committed json differ

1. The residual E = SOBRANTES + VOTARON + REPRESENTANTES - LISTA_NOMINAL, and D = E - REPRESENTANTES_PP_CI, over every
   fully captured presidential acta (type 2) in the PREP CSV, by casilla type.
2. The frozen gate-v3 bands (twohands/gate_v3.py) recomputed from the CSV (excluding the 300, the 100, the 3,000).
3. POST-HOC on the 300: gate v3 on the stored reads (Gemma primary, Qwen second; and the reverse).
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO, schema  # noqa: E402
from twohands.gate import gate, iv  # noqa: E402
from twohands.gate_v2 import gate_v2  # noqa: E402
from twohands.gate_v3 import BANDS, CSV_COLS, E_MAX, TYPES, calibrate, gate_v3, residuals  # noqa: E402
from twohands.run import jsonl  # noqa: E402
from twohands.sample import PREP_CSV, load_rows  # noqa: E402

R = REPO / "results"
OUT_MD, OUT_JSON = R / "ballot_stock.md", R / "ballot_stock.json"
NAMES = {"B": "básica", "C": "contigua", "E": "extraordinaria", "S": "especial"}
KS = (0, 5, 10, 20, 30, 50)
QS = (0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)
ARMS = ("manifest.json", "manifest_confirm100.json", "manifest_ext3000.json")


def q(sorted_vals, p):
    import math
    return sorted_vals[max(1, math.ceil(p * len(sorted_vals))) - 1]


def full_rows(rows):
    """Fully captured presidential actas: type 2 / 2E, contabilizada, every ballot field and the lista numeric."""
    for r in rows:
        if r.get("TIPO_ACTA") not in ("2", "2E") or r.get("CONTABILIZADA") != "1":
            continue
        v = {k: iv(str(r.get(c, "")).strip()) for k, c in CSV_COLS.items()}
        if None in (v["SOBRANTES"], v["VOTARON"], v["REPRESENTANTES"], v["LN"]):
            continue
        v["E"], v["D"] = residuals(v["SOBRANTES"], v["VOTARON"], v["REPRESENTANTES"], v["LN"], v["A"])
        v["tipo"] = r["TIPO_CASILLA"]
        v["consistent"] = (v["SACADOS"] is not None and v["TOTAL"] is not None
                           and v["VOTARON"] + v["REPRESENTANTES"] == v["SACADOS"] == v["TOTAL"])
        yield v


def dist(vals):
    s = sorted(vals)
    n = len(s)
    return {"n": n, "q": {str(p): q(s, p) for p in QS}, "min": s[0], "max": s[-1],
            "in_0_k": {str(k): round(100 * sum(0 <= x <= k for x in s) / n, 2) for k in KS},
            "abs_le_k": {str(k): round(100 * sum(abs(x) <= k for x in s) / n, 2) for k in KS},
            "zero": round(100 * sum(x == 0 for x in s) / n, 2), "neg": round(100 * sum(x < 0 for x in s) / n, 2)}


def distributions(rows) -> dict:
    by = collections.defaultdict(list)
    for v in full_rows(rows):
        by[v["tipo"]].append(v)
    out = {}
    for t, L in sorted(by.items()):
        o = {"n": len(L), "E_all": dist([v["E"] for v in L])}
        if t in TYPES:  # TIPO_CASILLA S (especial, acta 2E) never reaches here: its ballot fields are not numeric
            o["D_all"] = dist([v["D"] for v in L if v["D"] is not None])
            C = [v for v in L if v["consistent"]]
            o["E_consistent"] = dist([v["E"] for v in C])
            o["D_consistent"] = dist([v["D"] for v in C if v["D"] is not None])
        out[t] = o
    S = [r for r in rows if r.get("TIPO_CASILLA") == "S" and r.get("CONTABILIZADA") == "1"]
    out["S"] = {"n_contabilizada": len(S), "lista_nominal_zero": sum(str(r["LISTA_NOMINAL"]).strip() == "0" for r in S),
                "rep_votaron_not_numeric": sum(iv(str(r["TOTAL_REP_PARTIDO_CI_VOTARON"]).strip()) is None for r in S),
                "acta_types": dict(collections.Counter(r["TIPO_ACTA"] for r in S))}
    return out


def arms_claves() -> set:
    ex = set()
    for f in ARMS:
        ex |= {it["clave"] for it in json.loads((R / f).read_text(encoding="utf-8"))["items"]}
    return ex


# ---------- post-hoc on the 300 ----------

def last(path: Path) -> dict:
    out = {}
    for r in jsonl(path):
        out[r["clave"]] = r
    return out


def parsed_of(r, keys):
    if not r or r.get("no_call") or not r.get("parsed_ok"):
        return None
    F = r.get("fields") or {}
    return {"values": [{"label": (F.get(k) or {}).get("label"), "n": (F.get(k) or {}).get("n"),
                        "w": (F.get(k) or {}).get("w")} for k in keys]}


def posthoc(prep: dict) -> dict:
    s = schema.load()
    keys = s["keys"]
    graded = [f for f in s["fields"] if f.get("csv")]
    # human-readable files never name a party: vote rows are shown by their position
    shown = {k: f"vote row {i + 1}" for i, k in enumerate(s["vote_keys"])}
    claves = [it["clave"] for it in json.loads((R / "manifest.json").read_text(encoding="utf-8"))["items"]]
    V = json.loads((R / "adjudication" / "verdicts.json").read_text(encoding="utf-8"))
    G, Q = last(R / "calls_gemma.jsonl"), last(R / "calls_qwen.jsonl")

    def paper_of(k, f):
        """The paper's value for a field: ("v", int|None) decided, ("undecided", None), or ("prep", PREP value) when no
        verdict exists (then model = PREP counts as correct, model != PREP is flagged). Verdicts were written against
        Gemma's read: capture_right = the paper equals PREP, model_right = the paper equals Gemma's read."""
        pv = iv(str(prep[k][f["csv"]]).strip()) if k in prep else None
        v = V.get(f"{k}__{f['key']}")
        if not v:
            return "prep", pv
        if v["verdict"] == "capture_right":
            return "v", (v["paper"] if isinstance(v.get("paper"), int) else pv)
        if v["verdict"] == "model_right":
            if isinstance(v.get("paper"), int) or v.get("paper") == "blank":
                return "v", (v["paper"] if isinstance(v["paper"], int) else None)
            return "v", ((G[k].get("fields") or {}).get(f["key"]) or {}).get("n")
        if v["verdict"] == "neither" and isinstance(v.get("paper"), int):
            return "v", v["paper"]
        return "undecided", None

    def truth(k, f, m):
        """True / False / None (undecided) / "flag" (read != PREP, no verdict)."""
        kind, pv = paper_of(k, f)
        if kind == "undecided":
            return None
        if kind == "v":
            return m == pv
        return True if m == pv else "flag"

    def run(P, S2, label):
        tiers = {
            "v1 (frozen gate)": lambda p, k, sec: (lambda g: (g.accepted, g.accepted))(gate(p, s)),
            "v2": lambda p, k, sec: (lambda g: (g.accepted, g.accepted))(gate_v2(p, s, "v2")),
            "v2-2R strict": lambda p, k, sec: (lambda g: (g.accepted, g.accepted))(
                gate_v2(p, s, "v2", second={"SOBRANTES": sec}, second_required=True)),
        }

        def v3(**kw):
            def fn(p, k, sec):
                pr = prep.get(k, {})
                g = gate_v3(p, s, tipo=k[6], lista_nominal=iv(str(pr.get("LISTA_NOMINAL", "")).strip()),
                            allowance=iv(str(pr.get("REPRESENTANTES_PP_CI", "")).strip()), second=sec, **kw)
                return g.others_accepted, g.sobrantes_accepted
            return fn
        tiers["v3 part: stock band only"] = v3(require_words=False, require_second=False)
        tiers["v3 part: words + stock band"] = v3(require_second=False)
        tiers["v3 part: words + two reads"] = v3(require_stock=False)
        tiers["v3 (pre-registered: words + two reads + stock band)"] = v3()
        tiers["v3-emax (secondary: E in [0, E_max])"] = v3(mode="emax")
        out = {}
        for name, fn in tiers.items():
            o = {"forms_others_accepted": 0, "touchless": 0, "fields": 0, "errors": [], "undecided": [], "flagged": [],
                 "sob_to_person": 0, "sob_to_person_correct": [], "sob_to_person_wrong": []}
            for k in claves:
                p = parsed_of(P.get(k), keys)
                if p is None:
                    continue
                sr = P.get(k)
                sec = None
                q2 = S2.get(k)
                if q2 and q2.get("parsed_ok"):
                    sec = ((q2.get("fields") or {}).get("SOBRANTES") or {}).get("n")
                others, sob = fn(p, k, sec)
                if not others:
                    continue
                o["forms_others_accepted"] += 1
                o["touchless"] += bool(sob)
                for f in graded:
                    m = ((sr.get("fields") or {}).get(f["key"]) or {}).get("n")
                    t = truth(k, f, m)
                    if f["key"] == "SOBRANTES" and not sob:
                        o["sob_to_person"] += 1
                        (o["sob_to_person_wrong"] if t is False else o["sob_to_person_correct"]).append(
                            f"{k} (read {m}, PREP {prep[k][f['csv']] if k in prep else '-'})")
                        continue
                    o["fields"] += 1
                    pv = prep[k][f["csv"]] if k in prep else "-"
                    fk = shown.get(f["key"], f["key"])
                    if t is False:
                        o["errors"].append(f"{k} {fk}: read {m}, PREP {pv}")
                    elif t is None:
                        o["undecided"].append(f"{k} {fk}")
                    elif t == "flag":
                        o["flagged"].append(f"{k} {fk}: read {m}, PREP {pv}")
            out[name] = o
        return {"label": label, "tiers": out}

    # every SOBRANTES error on a v1-accepted form, with its ballot-stock residuals
    def stock_row(k, m, reader):
        pr = prep[k]
        g = lambda c: iv(str(pr[c]).strip())  # noqa: E731
        e_true, d_true = residuals(g("TOTAL_BOLETAS_SOBRANTES"), g("TOTAL_PERSONAS_VOTARON"),
                                   g("TOTAL_REP_PARTIDO_CI_VOTARON"), g("LISTA_NOMINAL"), g("REPRESENTANTES_PP_CI"))
        e_read, d_read = residuals(m, g("TOTAL_PERSONAS_VOTARON"), g("TOTAL_REP_PARTIDO_CI_VOTARON"),
                                   g("LISTA_NOMINAL"), g("REPRESENTANTES_PP_CI"))
        t = k[6]
        return {"clave": k, "reader": reader, "tipo": t, "read": m, "paper": paper_of(k, SOB)[1],
                "lista_nominal": g("LISTA_NOMINAL"), "allowance": g("REPRESENTANTES_PP_CI"),
                "E_paper": e_true, "D_paper": d_true, "E_read": e_read, "D_read": d_read, "band": list(BANDS[t]),
                "caught_by_band": not (BANDS[t][0] <= d_read <= BANDS[t][1]),
                "caught_by_emax": not (0 <= e_read <= E_MAX[t])}

    SOB = next(f for f in graded if f["key"] == "SOBRANTES")
    errs = []
    for P, reader in ((G, "Gemma-4-31B-IT"), (Q, "Qwen3.8-27B")):
        for k in claves:
            p = parsed_of(P.get(k), keys)
            if p is None or not gate(p, s).accepted:
                continue
            m = ((P[k].get("fields") or {}).get("SOBRANTES") or {}).get("n")
            if truth(k, SOB, m) is False:
                errs.append(stock_row(k, m, reader))
    return {"gemma_primary": run(G, Q, "Gemma primary, Qwen second"),
            "qwen_primary": run(Q, G, "Qwen primary, Gemma second"), "sobrantes_errors": errs}


# ---------- report ----------

CITES = r"""
## The two sources (fetched 2026-10-16 and read)

**TEPJF, Sala Superior, SUP-JIN-57/2012** (juicio de inconformidad, 24 August 2012; PDF
`https://www.te.gob.mx/media/SentenciasN/pdf/Superior/SUP-JIN-0057-2012.pdf`, 151 pages). The identity is used by the
court and by the parties, but always as boletas recibidas *minus* sobrantes against the people who voted / ballots taken
out of the urn:

> "...resulta necesario relacionar los rubros de TOTAL DE CIUDADANOS QUE VOTARON CONFORME A LA LISTA NOMINAL, TOTAL DE
> BOLETAS EXTRAÍDAS DE LA URNA, VOTACIÓN EMITIDA Y DEPOSITADA EN LA URNA, según corresponda, con el de NÚMERO DE BOLETAS
> SOBRANTES, para confrontar su resultado final con el número de boletas entregadas..." (p. 97, quoting the Sala
> Superior's own criterion)

> "...al restar las cantidades asentadas en los rubros boletas recibidas y boletas sobrantes resulta que la diferencia
> obtenida consiste en una cantidad igual o equivalente a la que existe en los rubros suma de los rubros 3 y 4 del acta
> (total de personas que votaron) y resultados de la votación de presidente (total)..." (pp. 140-141, casilla 900 E1)

The same ruling is also the caveat: the court calls the ballot rubros *accesorios* and holds that a mismatch there
alone does not show a miscount of votes, because poll workers make ballot-count mistakes:

> "...cuando las diferencias numéricas se localizan únicamente en las cifras relativas a boletas recibidas o boletas
> sobrantes, esto resulta insuficiente para considerar que se ha producido la causa de nulidad en comento." (p. 111)

So the identity is real and official, and it is also violated on real paper; the tails below are that.

**Reglamento de Elecciones del INE, art. 178, numeral 1.** Primary text (DOF, the CG reform that set inciso b),
`https://dof.gob.mx/nota_detalle_popup.php?codigo=5597009`):

> "Artículo 178. 1. Al término del conteo y sellado del total de boletas, éstas se agruparán de manera consecutiva por
> tipo de elección y siguiendo el procedimiento descrito en el anexo referido, conforme a los criterios siguientes:
> ( ... ) b) Para el caso de casillas especiales en elecciones concurrentes o no concurrentes, se asignarán hasta 1,500
> boletas por casilla para cada una de las elecciones federales, y otro tanto igual por cada tipo de elecciones
> locales. El número exacto de boletas deberá ser definido por el Consejo General a más tardar en el mes de febrero
> del año de la Jornada Electoral."

The DOF reform note prints only the amended inciso. Incisos a), c), d) as transcribed in a 2024 electoral-authority
agreement (Instituto Electoral del Estado de Querétaro, IEEQ/CD03/A/008/24, considerando 13,
`https://ieeq.mx/contenido/convocatorias/archivos/AnxCD030505241000E-2.pdf`; the consolidated INE text itself could
not be downloaded from here, diputados.gob.mx did not answer):

> "a) Total de personas electoras de cada casilla inscritas en el listado nominal. [...] c) Las boletas adicionales por
> cada partido político y, en su caso, candidaturas independientes, para que sus representantes acreditados ante la
> mesa directiva de casilla puedan ejercer su derecho de voto. d) En su caso, las boletas necesarias para que vote la
> ciudadanía que obtuvo resolución favorable del Tribunal Electoral que le faculte emitir su sufragio."

The same agreement (considerando 14) records that INE/CG293/24 gave each especial casilla 1,000 ballots in 2024.

**Column definitions (the INE CSV's own `LEEME.txt`).** TOTAL_PERSONAS_VOTARON = "Total de personas que votaron";
TOTAL_REP_PARTIDO_CI_VOTARON = representatives "que votaron"; LISTA_NOMINAL = the casilla's lista ("Para el caso de
casillas especiales no se tienen listas nominales, por lo que el valor es 0"); REPRESENTANTES_PP_CI = "Número de las y
los representantes acreditados de los Partidos Políticos y Candidaturas Independientes ante cada mesa directiva de
casilla". On the acta, PERSONAS_Y_REP = VOTARON + REPRESENTANTES (an identity the gate already checks), so **VOTARON
excludes the representatives** and the right sum is SOBRANTES + VOTARON + REPRESENTANTES. By art. 178 the casilla
receives LISTA_NOMINAL + the representatives' ballots (+ any TEPJF ballots), so E should equal REPRESENTANTES_PP_CI,
and D = E - REPRESENTANTES_PP_CI should be 0. The CSV confirms it: D = 0 exactly on most consistent actas.
"""

SENTENCE = ("Every accepted field is checked by the paper's own arithmetic, and the one field the paper cannot check "
            "is checked against the official voter list and ballot allowance; a misread smaller than that check's "
            "tolerance (at most 20 ballots) can still pass on that field alone.")


def pct_row(d, which):
    return " | ".join(f"{d[which][str(k)]:.2f}%" for k in KS)


def report(D: dict, cal: dict, PH: dict) -> str:
    L = ["# Ballot stock: checking SOBRANTES against the official lista nominal (gate v3)", "",
         "No model was called. Source: the INE PREP CSV `data/raw/prep/PRES_2024.csv` (cut 2024-06-03 20:05 UTC-6) and its",
         "`LEEME.txt`. Built by `scripts/ballot_stock.py`; `--check` recomputes everything here.", "",
         "**E** = SOBRANTES + VOTARON + REPRESENTANTES - LISTA_NOMINAL (CSV: TOTAL_BOLETAS_SOBRANTES +",
         "TOTAL_PERSONAS_VOTARON + TOTAL_REP_PARTIDO_CI_VOTARON - LISTA_NOMINAL): ballots the casilla had beyond its list.",
         "**D** = E - REPRESENTANTES_PP_CI: beyond the list and the representatives' allowance. Expected: D = 0.",
         "Population: every presidential acta (TIPO_ACTA 2 / 2E) with CONTABILIZADA = 1 and the four ballot fields",
         "numeric. *Consistent* = the capture's own identities hold (VOTARON + REPRESENTANTES = SACADOS = TOTAL), the",
         "only forms a gate can accept.", ""]
    L += ["## 1. The distribution", "",
          "| casilla | population | n | E 1% | 5% | 25% | 50% | 75% | 95% | 99% | E in [0,0] | [0,5] | [0,10] | [0,20] | [0,30] | [0,50] |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t, o in D.items():
        if t not in TYPES:
            continue
        for pop in ("E_all", "E_consistent"):
            if pop not in o:
                continue
            d = o[pop]
            qq = " | ".join(str(d["q"][str(p)]) for p in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99))
            L.append(f"| {NAMES.get(t, t)} ({t}) | {'all' if pop == 'E_all' else 'consistent'} | {d['n']} | {qq} | "
                     f"{pct_row(d, 'in_0_k')} |")
    L += ["", "E sits at the representatives' allowance (28-44 per casilla in 2024), not at 0, so E in [0, 20] holds",
          "for only about 1% of actas. Subtracting the allowance:", "",
          "| casilla | population | n | D 1% | 5% | 10% | 50% | 90% | 95% | 99% | D = 0 | abs(D) <= 5 | <= 10 | <= 20 | <= 30 | <= 50 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t, o in D.items():
        if t not in TYPES:
            continue
        for pop in ("D_all", "D_consistent"):
            if pop not in o:
                continue
            d = o[pop]
            qq = " | ".join(str(d["q"][str(p)]) for p in (0.01, 0.05, 0.1, 0.5, 0.9, 0.95, 0.99))
            ab = " | ".join(f"{d['abs_le_k'][str(k)]:.2f}%" for k in (5, 10, 20, 30, 50))
            L.append(f"| {NAMES[t]} ({t}) | {'all' if pop == 'D_all' else 'consistent'} | {d['n']} | {qq} | "
                     f"{d['zero']:.2f}% | {ab} |")
    if "S" in D:
        sd = D["S"]
        L += ["", f"Especial (S): {sd['n_contabilizada']} contabilizada actas (types {sd['acta_types']}); LISTA_NOMINAL is 0 on "
              f"{sd['lista_nominal_zero']} of them (no list: the LEEME says so) and TOTAL_REP_PARTIDO_CI_VOTARON is not numeric "
              f"on {sd['rep_votaron_not_numeric']}, so E is undefined. Especial casillas are **excluded**: under v3 their "
              "SOBRANTES always goes to a person. None of the 300, the 100 or the 3,000 is an especial casilla."]
    L += ["", "## 2. The frozen bands (gate v3)", "",
          "Nearest-rank 1st and 99th percentile of D over the consistent actas of each type, **excluding** the 300, the",
          "100 and the 3,000 (so no form that v3 will be scored on calibrates it). Frozen in `twohands/gate_v3.py`.", "",
          "| casilla | n | D band [1%, 99%] | secondary: E_max (99% of E) | recomputed = frozen |", "|---|---|---|---|---|"]
    for t in TYPES:
        c = cal[t]
        ok = tuple(c["band"]) == BANDS[t] and c["e_max"] == E_MAX[t]
        L.append(f"| {NAMES[t]} ({t}) | {c['n']} | [{c['band'][0]}, {c['band'][1]}] | {c['e_max']} | {'yes' if ok else 'NO'} |")
    L += ["", "By construction about 2% of correct, consistent SOBRANTES fall outside the band and go to a person.",
          "A misread SOBRANTES passes the band when it moves D by less than the band's margin: by up to "
          f"{min(BANDS[t][1] for t in TYPES)}-{max(BANDS[t][1] for t in TYPES)} upward or "
          f"{min(-BANDS[t][0] for t in TYPES)}-{max(-BANDS[t][0] for t in TYPES)} downward from a paper whose D is 0."]
    L += [CITES]
    L += ["## 3. POST-HOC on the 300 (not a test of v3)", "",
          "**Post-hoc.** v3 was designed after seeing these 300 reads and their adjudication; numbers here are NOT a test of",
          "v3. The pre-registered tests are the 100-form confirmation and the 3,000 extension (Amendment 7). Stored reads",
          "re-gated, no model call. Truth as in `results/posthoc_v2_300.md` (verdict decides; with no verdict model = PREP",
          "is correct). Lista nominal and allowance from the PREP CSV. Field-level: under v3 a routed SOBRANTES is shown to a",
          "person and is not an accepted field; the form's other fields stay accepted.", "",
          "Every accepted-field error on the 300 (v1-accepted forms, either reader), all SOBRANTES:", "",
          "| form | reader | read | paper | lista | allowance | D on paper | D read | band | caught by band | caught by [0, E_max] |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for e in PH["sobrantes_errors"]:
        L.append(f"| {e['clave']} | {e['reader']} | {e['read']} | {e['paper']} | {e['lista_nominal']} | {e['allowance']} | "
                 f"{e['D_paper']} | {e['D_read']} | [{e['band'][0]}, {e['band'][1]}] | {'yes' if e['caught_by_band'] else 'no'} | "
                 f"{'yes' if e['caught_by_emax'] else 'no'} |")
    for key in ("gemma_primary", "qwen_primary"):
        blk = PH[key]
        L += ["", f"### {blk['label']}", "",
              "| gate | forms, other fields accepted | touchless (all 23) | accepted graded fields | errors | SOBRANTES to a person: correct read (false alarm) | wrong read (caught) | flagged |",
              "|---|---|---|---|---|---|---|---|"]
        for name, o in blk["tiers"].items():
            L.append(f"| {name} | {o['forms_others_accepted']} | {o['touchless']} | {o['fields']} | {len(o['errors'])} | "
                     f"{len(o['sob_to_person_correct'])} | {len(o['sob_to_person_wrong'])} | {len(o['flagged'])} |")
        L.append("")
        for name, o in blk["tiers"].items():
            L.append(f"- **{name}**: errors: " + ("; ".join(o["errors"]) or "none")
                     + ". SOBRANTES to a person (wrong read, caught): " + ("; ".join(o["sob_to_person_wrong"]) or "none")
                     + (f". Undecided: {'; '.join(o['undecided'])}" if o["undecided"] else "")
                     + (f". Flagged: {'; '.join(o['flagged'])}" if o["flagged"] else "") + ".")
    v1 = PH["gemma_primary"]["tiers"]["v1 (frozen gate)"]
    so = PH["gemma_primary"]["tiers"]["v3 part: stock band only"]
    v3 = PH["gemma_primary"]["tiers"]["v3 (pre-registered: words + two reads + stock band)"]
    v2 = PH["gemma_primary"]["tiers"]["v2"]
    L += ["", "## Lines", "",
          f"> POST-HOC, Gemma primary: the ballot-stock band alone catches {len(so['sob_to_person_wrong'])} of the "
          f"{sum(e['reader'].startswith('Gemma') for e in PH['sobrantes_errors'])} wrong SOBRANTES Gemma read on "
          f"v1-accepted forms ({'; '.join(e['clave'] + ' read ' + str(e['read']) + ' vs paper ' + str(e['paper']) + (' caught' if e['caught_by_band'] else ' not caught') for e in PH['sobrantes_errors'] if e['reader'].startswith('Gemma'))}) "
          f"and sends {len(so['sob_to_person_correct'])} correct SOBRANTES to a person "
          f"(of {so['forms_others_accepted']} forms whose other fields are accepted).", "",
          f"> POST-HOC, Gemma primary, full v3 (words + two reads + band): {v3['forms_others_accepted']} forms with the other 22 "
          f"fields accepted, {v3['touchless']} touchless (v2: {v2['accepted'] if 'accepted' in v2 else v2['touchless']}, "
          f"v1: {v1['touchless']}), {v3['fields']} accepted graded fields (v2: {v2['fields']}), {len(v3['errors'])} errors, "
          f"{len(v3['sob_to_person_wrong'])} wrong SOBRANTES caught and {len(v3['sob_to_person_correct'])} correct "
          "SOBRANTES sent to a person (the false-alarm cost, mostly from the two-read and words rules).", "",
          f"> Site sentence: \"{SENTENCE}\""]
    return "\n".join(L) + "\n"


def compute() -> dict:
    rows = load_rows(PREP_CSV)
    D = distributions(rows)
    cal = calibrate(rows, arms_claves())
    man = {it["clave"] for it in json.loads((R / "manifest.json").read_text(encoding="utf-8"))["items"]}
    prep = {r["CLAVE_CASILLA"]: r for r in rows if r["CLAVE_CASILLA"] in man}
    PH = posthoc(prep)
    return {"distributions": D, "calibration": {t: {"n": c["n"], "band": list(c["band"]), "e_max": c["e_max"]}
                                                for t, c in cal.items()},
            "frozen": {"bands": {t: list(b) for t, b in BANDS.items()}, "e_max": E_MAX}, "posthoc_300": PH,
            "sentence": SENTENCE}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    from twohands.sample import PREP_CSV
    if "--check" in argv and not PREP_CSV.is_file():   # data/raw/ is not committed (gitignored, ~130 MB)
        ok = OUT_JSON.is_file() and OUT_MD.is_file()
        print("ballot_stock --check: raw PREP CSV absent (download it per docs/NUMBERS.md B to recompute); committed "
              + ("results/ballot_stock.json and .md present, not recomputed" if ok else "files MISSING"))
        return 0 if ok else 1
    out = compute()
    bad = [t for t in TYPES if out["calibration"][t]["band"] != list(BANDS[t]) or out["calibration"][t]["e_max"] != E_MAX[t]]
    md = report(out["distributions"], out["calibration"], out["posthoc_300"])
    js = json.dumps(out, indent=1, ensure_ascii=False)
    if "--check" in argv:
        mism = bad[:]
        if not OUT_JSON.is_file() or json.loads(OUT_JSON.read_text(encoding="utf-8")) != json.loads(js):
            mism.append("results/ballot_stock.json")
        if not OUT_MD.is_file() or OUT_MD.read_text(encoding="utf-8") != md:
            mism.append("results/ballot_stock.md")
        print(f"ballot_stock --check: {len(mism)} mismatches" + (f" ({', '.join(mism)})" if mism else ""))
        return 1 if mism else 0
    if bad:
        print(f"frozen bands differ from the CSV for {bad}: fix twohands/gate_v3.py", file=sys.stderr)
        return 1
    OUT_JSON.write_text(js + "\n", encoding="utf-8")
    OUT_MD.write_text(md, encoding="utf-8")
    print(md.split("## Lines")[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
