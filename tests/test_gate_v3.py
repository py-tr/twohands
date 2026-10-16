"""Gate v3 (Amendment 7): ballot-stock check and field-level routing of SOBRANTES."""
import json
import subprocess
import sys

import pytest

from twohands import REPO, schema
from twohands.gate_v3 import BANDS, E_MAX, calibrate, gate_v3, nearest_rank, residuals, stock_check
from tests.test_gate import good

S = schema.load()
# good(): SOBRANTES 250, VOTARON 290, REPRESENTANTES 10 -> used + left = 550. A casilla with lista 520 and an
# allowance of 30 representatives' ballots: E = 30, D = 0.
LN, A = 520, 30


def v3(p, **kw):
    kw.setdefault("tipo", "B")
    kw.setdefault("lista_nominal", LN)
    kw.setdefault("allowance", A)
    kw.setdefault("second", 250)
    return gate_v3(p, S, **kw)


def test_residuals_use_votaron_plus_representatives():
    assert residuals(250, 290, 10, LN, A) == (30, 0)
    assert residuals(None, 290, 10, LN, A) == (None, None)
    assert residuals(250, 290, 10, LN, None) == (30, None)


def test_clean_read_with_agreeing_second_read_is_touchless():
    r = v3(good())
    assert r.others_accepted and r.sobrantes_accepted and r.touchless, r.sobrantes_reasons
    assert r.checks == {"words": True, "second": True, "stock": True}
    assert len(r.accepted_keys(S["keys"])) == 23


def test_no_second_read_routes_sobrantes_only():
    r = v3(good(), second=None)
    assert r.others_accepted and not r.sobrantes_accepted
    assert r.accepted_keys(S["keys"]) == [k for k in S["keys"] if k != "SOBRANTES"]
    r = v3(good(), second=251)
    assert r.others_accepted and not r.sobrantes_accepted and "second 251" in r.sobrantes_reasons[0]


def test_missing_words_routes_sobrantes_only():
    p = good()
    p["values"][0]["w"] = None
    r = v3(p)
    assert r.others_accepted and not r.sobrantes_accepted
    assert r.checks["words"] is False


def test_sobrantes_words_mismatch_no_longer_routes_the_form():
    """v1 routes the whole form when SOBRANTES digits != words; v3 routes SOBRANTES alone."""
    p = good()
    p["values"][0]["w"] = 255
    r = v3(p)
    assert not r.v1.accepted
    assert r.others_accepted and not r.sobrantes_accepted


def test_misread_outside_the_band_is_caught_and_inside_passes():
    lo, hi = BANDS["C"]
    # both reads agree on the same misread (the case two reads cannot catch): only the stock check stands
    for delta, caught in ((hi + 1, True), (lo - 1, True), (hi, False), (lo, False), (5, False)):
        p = good()
        p["values"][0]["n"] = p["values"][0]["w"] = 250 + delta
        r = v3(p, tipo="C", second=250 + delta)
        assert r.others_accepted
        assert r.sobrantes_accepted is (not caught), (delta, r.sobrantes_reasons)
    # 212668C0300: paper 379, read 300 -> D = -79
    assert stock_check("C", 300, 326, 9, 680, 34)[0] is False
    assert stock_check("C", 379, 326, 9, 680, 34)[0] is True
    # 010469C0400: paper 234, read 239 -> D = +5, inside the band: the stock check alone cannot catch it
    assert stock_check("C", 239, 407, 1, 614, 28)[0] is True


def test_stock_check_needs_official_list_and_routes_especial():
    assert v3(good(), lista_nominal=None).sobrantes_accepted is False
    assert v3(good(), lista_nominal=0).sobrantes_accepted is False
    assert v3(good(), allowance=None).sobrantes_accepted is False
    r = v3(good(), tipo="S")
    assert r.others_accepted and not r.sobrantes_accepted and "no fixed lista" in r.sobrantes_reasons[0]


def test_emax_mode_is_the_literal_secondary():
    assert stock_check("B", 250, 290, 10, LN, A, mode="emax")[0] is True          # E = 30
    assert stock_check("B", 250 + E_MAX["B"], 290, 10, LN, A, mode="emax")[0] is False
    assert stock_check("B", 200, 290, 10, LN, A, mode="emax")[0] is False          # E = -20


def test_other_v1_failures_still_route_the_whole_form():
    p = good()
    p["values"][6]["n"] += 1                       # vote row 2 off by one: rows no longer sum to TOTAL
    p["values"][6]["w"] += 1
    r = v3(p)
    assert not r.others_accepted and not r.sobrantes_accepted and r.accepted_keys(S["keys"]) == []
    assert "identity" in r.v1.codes and r.sobrantes_reasons[0] == "the form routes"


def test_component_switches():
    p = good()
    p["values"][0]["w"] = None
    assert v3(p, require_words=False, second=None, require_second=False).sobrantes_accepted
    assert v3(good(), second=None, require_second=False).sobrantes_accepted
    assert v3(good(), lista_nominal=None, require_stock=False).sobrantes_accepted


def _row(tipo, s, v, rp, ln, a, clave="X"):
    return {"CLAVE_CASILLA": clave, "TIPO_ACTA": "2", "CONTABILIZADA": "1", "TIPO_CASILLA": tipo,
            "TOTAL_BOLETAS_SOBRANTES": str(s), "TOTAL_PERSONAS_VOTARON": str(v), "TOTAL_REP_PARTIDO_CI_VOTARON": str(rp),
            "TOTAL_VOTOS_SACADOS": str(v + rp), "TOTAL_VOTOS_ASENTADO": str(v + rp), "LISTA_NOMINAL": str(ln),
            "REPRESENTANTES_PP_CI": str(a)}


def test_calibrate_nearest_rank_and_filters():
    assert nearest_rank(list(range(100)), 0.01) == 0 and nearest_rank(list(range(100)), 0.99) == 98
    rows = [_row("B", 250 + d, 290, 10, LN, A, clave=f"k{d}") for d in range(-50, 50)]
    rows.append(_row("B", 9999, 290, 10, LN, A, clave="excluded"))
    bad = _row("B", 9999, 290, 10, LN, A)
    bad["TOTAL_VOTOS_SACADOS"] = "1"               # capture inconsistent -> not in the population
    rows.append(bad)
    c = calibrate(rows, exclude={"excluded"})
    assert c["B"]["n"] == 100 and c["B"]["band"] == (-50, 48)


@pytest.mark.skipif(not (REPO / "data" / "raw" / "prep" / "PRES_2024.csv").is_file(), reason="PREP CSV not present")
def test_frozen_bands_match_the_csv():
    from twohands.sample import load_rows
    ex = set()
    for f in ("manifest.json", "manifest_confirm100.json", "manifest_ext3000.json"):
        ex |= {it["clave"] for it in json.loads((REPO / "results" / f).read_text(encoding="utf-8"))["items"]}
    c = calibrate(load_rows(), ex)
    assert {t: c[t]["band"] for t in BANDS} == BANDS
    assert {t: c[t]["e_max"] for t in E_MAX} == E_MAX


@pytest.mark.skipif(not (REPO / "data" / "raw" / "prep" / "PRES_2024.csv").is_file(), reason="PREP CSV not present")
def test_committed_report_recomputes():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "ballot_stock.py"), "--check"], capture_output=True,
                       text=True, cwd=REPO)
    assert r.returncode == 0, r.stdout + r.stderr
