"""Gate v2 (Amendment 3): unchecked-field confirmation, two-reader variant, v2b relaxed label rule."""
import pytest

from twohands import schema
from twohands.gate import gate
from twohands.gate_v2 import gate_v2, relaxed_label_failures, unchecked_fields
from tests.test_gate import LABELS, good

S = schema.load()


def test_only_sobrantes_is_outside_every_identity():
    assert unchecked_fields(S) == ["SOBRANTES"]


def test_clean_read_accepted_in_both_variants():
    for v in ("v2", "v2b"):
        r = gate_v2(good(), S, v)
        assert r.accepted, r.reasons
        assert r.unchecked == {"SOBRANTES": "words"}


def test_sobrantes_without_words_routes_under_v2_but_not_v1():
    p = good()
    p["values"][0]["w"] = None
    assert gate(p, S).accepted
    r = gate_v2(p, S)
    assert not r.accepted and r.codes == ["unchecked"] and r.unchecked["SOBRANTES"] == "fail"


def test_two_reader_variant_accepts_on_agreement_only():
    p = good()
    p["values"][0]["w"] = None
    assert gate_v2(p, S, second={"SOBRANTES": 250}).accepted
    r = gate_v2(p, S, second={"SOBRANTES": 251})
    assert not r.accepted and "second reader 251" in r.reasons[0]
    assert not gate_v2(p, S, second={"SOBRANTES": None}).accepted


def test_v1_failures_still_route_in_v2():
    p = good()
    p["values"][22]["n"] = 299
    p["values"][22]["w"] = 299
    r = gate_v2(p, S)
    assert not r.accepted and "identity" in r.codes


def test_isolated_misnamed_logo_routes_v2_but_passes_v2b():
    p = good()
    i = LABELS.index("VERDE+PT+morena")
    p["values"][i]["label"] = "VERDE+PT"   # fits the next row better: an isolated misnaming
    assert not gate_v2(p, S, "v2").accepted
    r = gate_v2(p, S, "v2b")
    assert r.accepted, r.reasons


def test_run_of_shifted_rows_routes_v2b():
    p = good()
    v = p["values"]
    i = LABELS.index("VERDE+PT")
    v[i]["label"] = LABELS[i + 1]          # two adjacent rows each carry the next row's label
    v[i + 1]["label"] = LABELS[i + 2]
    r = gate_v2(p, S, "v2b")
    assert not r.accepted and "label" in r.codes
    labels = {f["key"]: x["label"] for f, x in zip(S["fields"], v)}
    assert relaxed_label_failures(labels, S) == ["PVEM_PT", "PVEM_MORENA"]


def test_v2b_keeps_text_row_and_empty_label_rules():
    p = good()
    p["values"][21]["label"] = "TOTAL"     # NULOS row reads TOTAL
    assert not gate_v2(p, S, "v2b").accepted
    p = good()
    p["values"][6]["label"] = ""           # empty logo label
    assert not gate_v2(p, S, "v2b").accepted


def test_no_read_routes():
    r = gate_v2(None, S)
    assert not r.accepted and r.codes == ["shape"]
    with pytest.raises(ValueError):
        gate_v2(good(), S, "v3")


def test_strict_two_reader_variant_needs_the_second_reader_even_when_words_agree():
    p = good()  # SOBRANTES read with words = digits
    assert gate_v2(p, S, second={"SOBRANTES": 251}).accepted          # Amendment 3: words confirm it
    r = gate_v2(p, S, second={"SOBRANTES": 251}, second_required=True)
    assert not r.accepted and r.unchecked["SOBRANTES"] == "fail"
    n = p["values"][0]["n"]
    assert gate_v2(p, S, second={"SOBRANTES": n}, second_required=True).unchecked == {"SOBRANTES": "second"}
    assert not gate_v2(p, S, second_required=True).accepted
