"""The gate: row labels, words = digits, rows sum to TOTAL, section identities."""
import copy

import pytest

from twohands import schema
from twohands.gate import gate, label_ok, parties_in
from twohands.reader import parse

S = schema.load()
AL = S["party_aliases"]
LABELS = ["BOLETAS SOBRANTES", "PERSONAS DE LA LISTA NOMINAL QUE VOTARON", "REPRESENTACIONES PARTIDISTAS QUE VOTARON",
          "TOTAL DE PERSONAS Y REPRESENTANTES QUE VOTARON", "TOTAL DE VOTOS SACADOS DE LAS URNAS",
          "PAN", "PRI", "PRD", "VERDE", "PT", "MOVIMIENTO CIUDADANO", "morena",
          "PAN+PRI+PRD", "PAN+PRI", "PAN+PRD", "PRI+PRD", "VERDE+PT+morena", "VERDE+PT", "VERDE+morena", "PT+morena",
          "CANDIDATOS/AS NO REGISTRADOS/AS", "VOTOS NULOS", "TOTAL"]
# a consistent acta: 17 vote rows sum to 300; votaron 290 + rep 10 = 300 = sacados = total
VOTES = [60, 20, 5, 10, 8, 30, 120, 3, 2, 1, 1, 15, 4, 6, 5, 0, 10]
NUMS = [250, 290, 10, 300, 300] + VOTES + [300]


def good():
    return {"values": [{"label": l, "n": n, "w": n} for l, n in zip(LABELS, NUMS)]}


def test_schema_is_consistent():
    assert len(S["fields"]) == 23 and len(S["vote_keys"]) == 17
    assert sum(VOTES) == 300


def test_clean_read_accepted():
    r = gate(good())
    assert r.accepted, r.reasons
    assert r.values["PVEM_PT"] == 4


def test_row_shift_is_a_label_mismatch():
    """Model skipped the PVEM_PT row and pulled the rest up; it repeated PT_MORENA's value to keep 23 items.
    The numbers still sum (we force it), but the labels at the shifted positions do not match."""
    p = good()
    v = p["values"]
    i = LABELS.index("VERDE+PT")
    v[i] = dict(v[i + 1])                    # position PVEM_PT now carries VERDE+morena's label + value
    v[i + 1] = dict(v[i + 2])                # PVEM_MORENA position carries PT+morena
    r = gate(p)
    assert not r.accepted
    assert "label" in r.codes
    assert any("row label mismatch" in x and "PVEM_PT" in x for x in r.reasons)


def test_label_mismatch_alone_routes_even_when_arithmetic_passes():
    p = good()
    p["values"][5]["label"] = "PRI"          # PAN row reported as PRI; numbers untouched
    r = gate(p)
    assert not r.accepted and r.codes == ["label"]


def test_missing_label_is_mismatch():
    p = good()
    p["values"][22]["label"] = None
    assert gate(p).codes == ["label"]


@pytest.mark.parametrize("label,key,ok", [
    ("Partido Verde Ecologista de México + PT + MORENA", "PVEM_PT_MORENA", True),
    ("VERDE+PT", "PVEM_PT_MORENA", False),
    ("PRI + PRD", "PRI_PRD", True),
    ("PAN, PRI", "PAN_PRD", False),
    ("Movimiento Ciudadano", "MC", True),
    ("Votos nulos", "NULOS", True),
    ("TOTAL", "NULOS", False),
    ("Total", "TOTAL", True),
    ("VOTOS NULOS", "TOTAL", False),
    ("Total de votos sacados de las urnas", "TOTAL", False),
    ("Total de votos sacados de las urnas", "SACADOS", True),
    ("Total de personas y representantes que votaron", "PERSONAS_Y_REP", True),
    ("Representaciones partidistas que votaron", "REPRESENTANTES", True),
    ("Total de personas y representantes que votaron", "REPRESENTANTES", False),
    ("Personas de la lista nominal que votaron", "VOTARON", True),
    ("Candidatos/as no registrados/as", "NO_REGISTRADAS", True),
    ("PANAL", "PAN", False),
])
def test_label_rules(label, key, ok):
    f = next(f for f in S["fields"] if f["key"] == key)
    assert label_ok(label, f["label"], AL) is ok


def test_parties_in():
    assert parties_in("VERDE+PT+morena", AL) == {"PVEM", "PT", "MORENA"}
    assert parties_in("Partido del Trabajo", AL) == {"PT"}


def test_words_digits_mismatch():
    p = good()
    p["values"][22]["w"] = 200
    r = gate(p)
    assert not r.accepted and "words" in r.codes


def test_rows_must_sum_to_total():
    p = good()
    p["values"][5]["n"] = p["values"][5]["w"] = 61
    r = gate(p)
    assert not r.accepted and any("rows sum to TOTAL" in x for x in r.reasons)


@pytest.mark.parametrize("idx,name", [(1, "votaron + representantes = section 5"), (3, "section 5 = section 7"),
                                      (4, "section 7 = TOTAL")])
def test_section_identities(idx, name):
    p = good()
    p["values"][idx]["n"] = p["values"][idx]["w"] = p["values"][idx]["n"] + 1
    r = gate(p)
    assert not r.accepted and any(name in x for x in r.reasons)


def test_empty_digits_and_wrong_count():
    p = good(); p["values"][7]["n"] = None
    assert "empty" in gate(p).codes
    p = good(); p["values"].pop()
    assert "shape" in gate(p).codes
    assert gate(None).codes == ["shape"]


def test_fix_flag_recorded():
    p = good(); p["values"][6]["fix"] = True
    assert gate(p).fixes == ["PRI"]


def test_parser_first_object_and_tails():
    obj = good()
    import json
    s = "```json\n" + json.dumps(obj).replace('"n": 5,', '"n": 005,') + "\n```\n}}}} garbage {\"values\": []}"
    p = parse(s)
    assert gate(p).accepted
    assert parse("<think>{\"values\": [1]}</think> nothing") is None


from twohands.gate import label_consistent  # noqa: E402

F = S["fields"]
POS = {f["key"]: i for i, f in enumerate(F)}


@pytest.mark.parametrize("key,label,ok", [
    ("PRD", "MC", True),                 # misnamed single logo, no shift evidence (Qwen pilot read)
    ("PRI", "PRI+PRD", True),            # ties with neighbour PRD: not a shift
    ("MC", "PVEM", True),                # neighbours are PT and MORENA
    ("PAN_PRI_PRD", "PAN+PRI+MC", True), # right logo count, 2 of 3 named
    ("PRI", "PRD", False),               # fits the next row better: shift evidence
    ("PVEM_PT", "VERDE+morena", False),  # the classic coalition-2 shift
    ("PAN_PRI", "PAN+PRI+PRD", False),   # repeating the row above
    ("PT_MORENA", "VERDE+morena", False),
    ("PT_MORENA", "", False),
    ("NULOS", "VOTOS NULOS", True),
    ("NULOS", "TOTAL", False),           # text rows stay strict
])
def test_label_consistent(key, label, ok):
    assert label_consistent(POS[key], label, F, AL) is ok
