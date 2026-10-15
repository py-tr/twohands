"""The Senate acta (third measured form type, PROTOCOL_SENADO.md): schema, prompt, sampler, mask on the real masked
pages, official values, and a mocked dry run of the runner. No network, no model."""
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from twohands import REPO, gate, mask, reader, run, sample, schema

S = schema.load("mx_senado_2024")
P = schema.load()
SRC = schema.source(S)
L = S["layout"]
MAN = REPO / "results" / "manifest_senado100.json"
MASKED = REPO / SRC["masked_dir"]
PAGES = sorted(MASKED.glob("*.jpg")) if MASKED.is_dir() else []
SEN_PROMPT_SHA = "3c28a07a32a8f88110273fe578b3b25def064bc3ef664e61963b89910b1bf80f"
PRES_PROMPT_SHA = "3664253035b912184e24a205852e7b8e686f0abb36a4340e91834d60dc71193f"


def inter(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


# ------------------------------------------------------------------ schema
def test_rows_labels_identities_match_the_presidential_acta():
    """Same 23 fields (keys, INE columns, vote flags, row labels), same identities, mask, tiles and gate regions:
    the frozen gate and the app's evaluation apply unchanged."""
    strip = lambda f: {k: v for k, v in f.items() if k != "public"}  # noqa: E731
    assert [strip(f) for f in S["fields"]] == [strip(f) for f in P["fields"]]
    assert S["identities"] == P["identities"]
    assert S["party_aliases"] == P["party_aliases"]
    for k in ("canonical", "mask", "tiles", "field_regions"):
        assert L[k] == P["layout"][k], k


def test_public_names_option_codes_for_vote_rows_plain_names_otherwise():
    from app.store import code_of, name_of
    n = 0
    for f in S["fields"]:
        pub = f["public"]
        assert pub["code"] == code_of(f["key"]) and pub["name"] == name_of(f["key"])
        if f.get("vote") and f["key"] not in ("NO_REGISTRADAS", "NULOS"):
            n += 1
            assert pub == {"code": f"OPT{n:02d}", "name": f"Option {n:02d}"}
    assert n == 15


def test_own_rectification_assets_and_mask_zeroed():
    for name in ("template", "reference", "landmarks"):
        a = np.load(Path(S["_dir"]) / L[name]).astype(np.float32)
        h, w = a.shape
        assert np.abs(a[:, int(np.ceil(0.657 * w)) + 1:]).max() == 0, name     # nothing right of the mask edge
        assert a[:, : int(0.6 * w)].std() > 0, name
    assert schema.feature_ref_path(S).name == "mx_senado_2024.feature_ref.jpg"
    assert schema.feature_ref_path(P).name == "mx_presidencia_2024.feature_ref.jpg"   # the presidency is unchanged
    fr = np.asarray(Image.open(schema.feature_ref_path(S)).convert("L"), dtype=float)
    assert fr[:, int(0.66 * fr.shape[1]):].mean() < 8                             # the reference scan is masked


def test_prompt_names_the_senate_form_and_the_presidential_prompt_is_unchanged():
    assert reader.prompt_sha256(P) == PRES_PROMPT_SHA
    assert reader.prompt_sha256(S) == SEN_PROMPT_SHA
    a, b = reader.build_prompt(P).splitlines(), reader.build_prompt(S).splitlines()
    assert a[1:] == b[1:]                                                          # only the first line differs
    assert "Senadurias" in b[0] and "type 3" in b[0]


def test_frozen_gate_accepts_a_consistent_senate_read():
    off = json.loads((REPO / "app" / "data" / "official_senado.json").read_text(encoding="utf-8"))
    chat = run.mock_chat(S, off)
    k = next(k for k, v in off.items() if None not in v["prep"].values()
             and sum(v["prep"][f["key"]] for f in S["fields"] if f.get("vote")) == v["prep"]["TOTAL"]
             == v["prep"]["SACADOS"] == v["prep"]["VOTARON"] + v["prep"]["REPRESENTANTES"])
    run._CUR.clave = k
    r, _ = chat({})
    g = gate.gate(reader.parse(r["choices"][0]["message"]["content"]), S)
    assert g.accepted, g.reasons


# ------------------------------------------------------------------ sampler
def _row(**kw):
    r = {"CLAVE_CASILLA": "010001B0100", "TIPO_ACTA": "3", "TIPO_CASILLA": "B", "ID_ENTIDAD": "1",
         "TIPO_DOCUMENTO": "Acta PREP", "DIGITALIZACION": "Escáner"}
    r.update(kw)
    return r


def test_eligibility_special_stations_variants_and_reuse():
    rows = [_row(), _row(CLAVE_CASILLA="010002S0100", TIPO_CASILLA="S"),                 # special, TIPO_ACTA 3
            _row(CLAVE_CASILLA="010003S0100", TIPO_CASILLA="S", TIPO_ACTA="3EMR"),       # special MR acta
            _row(CLAVE_CASILLA="010003S0100", TIPO_CASILLA="S", TIPO_ACTA="3ERP"),       # its RP twin
            _row(CLAVE_CASILLA="200004B0100", ID_ENTIDAD="20"),                           # a layout-variant state
            _row(CLAVE_CASILLA="010005B0100")]                                            # used in a presidential sample
    el, why = sample.eligible(rows, {"010005B0100"}, tipo="3", special_rule=True, exclude_states={20},
                              exclude_reason="used")
    assert [r["CLAVE_CASILLA"] for r in el] == ["010001B0100"]
    assert why["used"] == 1 and sum(why.values()) == 5


def test_presidential_eligibility_unchanged():
    rows = [_row(TIPO_ACTA="2"), _row(CLAVE_CASILLA="010002S0100", TIPO_ACTA="2", TIPO_CASILLA="S"),
            _row(CLAVE_CASILLA="010003B0100")]
    el, why = sample.eligible(rows, set())
    assert len(el) == 2 and why == {"not a presidential casilla acta (TIPO_ACTA != 2)": 1}


@pytest.mark.skipif(not MAN.is_file(), reason="manifest not drawn")
def test_manifest_matches_protocol_and_excludes_presidential_stations():
    m = json.loads(MAN.read_text(encoding="utf-8"))
    proto = (REPO / "PROTOCOL_SENADO.md").read_text(encoding="utf-8")
    import hashlib
    assert hashlib.sha256(MAN.read_bytes()).hexdigest() in proto
    assert schema.sha256("mx_senado_2024") in proto and m["schema_sha256"] == schema.sha256("mx_senado_2024")
    assert SEN_PROMPT_SHA in proto
    assert m["schema"] == "mx_senado_2024" and m["seed"] == 20261019 and len(m["items"]) == 100
    claves = {i["clave"] for i in m["items"]}
    R = REPO / "results"
    used = set()
    for p in ("manifest.json", "manifest_confirm100.json", "calibration_manifest.json"):
        used |= {i["clave"] for i in json.loads((R / p).read_text(encoding="utf-8"))["items"]}
    used |= {r["clave"] for r in run.jsonl(R / "prepare_state06.jsonl")}
    used |= {p["clave"] for p in json.loads((R / "senado" / "pilot.json").read_text(encoding="utf-8"))["pages"]}
    assert not claves & used
    assert not {i["id_entidad"] for i in m["items"]} & set(SRC["exclude_states"])
    assert all("/senadurias_mr/" in i["url"] and "S" not in i["clave"][6] for i in m["items"])
    off = json.loads((REPO / "app" / "data" / "official_senado.json").read_text(encoding="utf-8"))
    assert set(off) == claves and all(set(v["prep"]) == {f["key"] for f in S["fields"] if f["csv"]} for v in off.values())


# ------------------------------------------------------------------ mask on the real masked Senate pages
@pytest.mark.skipif(not PAGES, reason="no masked Senate pages (scripts/senado_draw.py prepare)")
def test_masked_senate_pages_black_mask_and_visible_gate_regions():
    lay = {i["clave"]: i["layout"] for i in json.loads(MAN.read_text(encoding="utf-8"))["items"]}
    for p in PAGES:
        a = np.asarray(Image.open(p).convert("L"), dtype=float)
        H, W = a.shape
        assert (W, H) == tuple(L["canonical"]["size"]), p.name
        for x0, y0, x1, y1 in schema.mask_rects(S, lay[p.stem]):
            blk = a[int(y0 * H) + 2:int(y1 * H) - 2, int(x0 * W) + 2:int(x1 * W) - 2]
            assert blk.mean() < 8 and blk.max() < 60, p.name                      # the mask is fully black
        for name, reg in L["field_regions"].items():
            for m in schema.mask_rects(S, lay[p.stem]):
                assert inter(reg, m) == 0, name                                    # gate regions outside the mask
            x0, y0, x1, y1 = reg
            r = a[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
            assert (r < np.median(r) - 50).mean() > 0.01, (p.name, name)          # ink present (relative: light photos)
            assert (r < 8).mean() < 0.02, (p.name, name)                           # not blacked out
        for t in mask.tiles(Image.open(p), S):
            assert (np.asarray(t.convert("L")) < 8).mean() < 0.05, p.name           # tiles carry no mask


@pytest.mark.skipif(not PAGES, reason="no masked Senate pages")
def test_prepare_log_accounts_for_all_100():
    rows = {r["clave"]: r for r in run.jsonl(REPO / SRC["results_dir"] / "prepare.jsonl")}
    man = [i["clave"] for i in json.loads(MAN.read_text(encoding="utf-8"))["items"]]
    assert set(man) <= set(rows)
    ok = {k for k in man if rows[k]["status"] == "ok"}
    assert ok == {p.stem for p in PAGES}
    assert not list((REPO / "data" / "raw" / "img").glob("senpilot_*"))


# ------------------------------------------------------------------ runner dry run (mocked client)
@pytest.mark.skipif(not PAGES, reason="no masked Senate pages")
def test_mocked_dry_run_on_three_forms(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "LOG", run.LOG)
    calls = []
    monkeypatch.setattr(run.amd, "usage", lambda: calls.append("usage") or {})
    rc = run.main(["--schema", "mx_senado_2024", "--manifest", "results/manifest_senado100.json", "--models", "gemma",
                   "--mock", "--limit", "3", "--out", str(tmp_path)])
    assert rc == 0 and not calls
    recs = run.jsonl(tmp_path / "calls_gemma.jsonl")
    assert len(recs) == 3 and all(r["schema"] == "mx_senado_2024" for r in recs)
    assert all(r["prompt_sha256"] == SEN_PROMPT_SHA for r in recs if not r["no_call"])
    assert all(r["image"].startswith("data/masked/senado/") for r in recs if not r["no_call"])
    assert (tmp_path / "prepare.jsonl").is_file() and (tmp_path / "run.log").is_file()


def test_runner_refuses_other_readers_and_wrong_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "LOG", run.LOG)
    man = tmp_path / "m.json"
    man.write_text(json.dumps({"schema": "mx_senado_2024", "items": []}), encoding="utf-8")
    assert run.main(["--schema", "mx_senado_2024", "--manifest", str(man), "--models", "qwen", "--mock",
                     "--out", str(tmp_path)]) == 3
    man.write_text(json.dumps({"items": []}), encoding="utf-8")                   # a presidential manifest
    assert run.main(["--schema", "mx_senado_2024", "--manifest", str(man), "--models", "gemma", "--mock",
                     "--out", str(tmp_path)]) == 3
