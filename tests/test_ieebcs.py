"""The BCS head-to-head (PROTOCOL_IEEBCS.md): the two builder-made schemas and their row variants, the prompts (the
pre-registered ones unchanged), the manifest, the mask on the real masked pages, the scorer, and a mocked dry run of
the runner on 2 forms. No network, no model."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from twohands import REPO, gate, mask, reader, run, schema

sys.path.insert(0, str(REPO / "scripts"))
import ieebcs_score as SC  # noqa: E402

LAYOUTS = {"mx_bcs_dl_2024": 14, "mx_bcs_dl_2024@sin_pes": 13, "mx_bcs_ayto_2024": 13, "mx_bcs_ayto_2024@sin_ml": 12}
PROMPTS = {"mx_bcs_dl_2024": "58a92aec76c67218fbd5039f5de24aebcaefb3194e474fd20490962945dbd8bc",
           "mx_bcs_dl_2024@sin_pes": "74421b7ccc76172a909628236b5082370361bd02e542feb451270252b7820f40",
           "mx_bcs_ayto_2024": "b1de37ef0251c40483758350cd9ced844b895561c67ff7d476bbf676d2e3498e",
           "mx_bcs_ayto_2024@sin_ml": "9f430ae43c4c6a33999774e60fb7b0b7ef6ebd854e6b466c59af792ab18f9693"}
PRES_PROMPT_SHA = "3664253035b912184e24a205852e7b8e686f0abb36a4340e91834d60dc71193f"
SEN_PROMPT_SHA = "3c28a07a32a8f88110273fe578b3b25def064bc3ef664e61963b89910b1bf80f"
MAN = REPO / "results" / "manifest_ieebcs300.json"
OFF = REPO / "results" / "ieebcs" / "official.json"
MASKED = REPO / "data" / "masked" / "ieebcs"
PAGES = sorted(MASKED.glob("*.jpg")) if MASKED.is_dir() else []
EDGE = 0.662


def items():
    return json.loads(MAN.read_text(encoding="utf-8"))["items"]


# ------------------------------------------------------------------ schemas
@pytest.mark.parametrize("name", LAYOUTS)
def test_fields_are_the_count_and_vote_boxes_only(name):
    s = schema.load(name)
    assert len(s["fields"]) == LAYOUTS[name] and s["form"] == name
    head = ["SOBRANTES", "VOTARON", "REPRESENTANTES", "PERSONAS_Y_REP", "SACADOS"]
    assert s["keys"][:5] == head and s["keys"][-3:] == ["NO_REGISTRADOS", "NULOS", "TOTAL"]
    assert [f["key"] for f in s["fields"] if not f.get("csv")] == ["PERSONAS_Y_REP"]   # section 5: no PREP column
    for f in s["fields"]:
        for b in (f["box"], f["words_box"]):
            assert 0 <= b[0] < b[2] <= EDGE and 0 <= b[1] < b[3] <= 1, (name, f["key"])
    rows = [f for f in s["fields"] if f["key"] not in head]
    assert all(a["box"][3] == b["box"][1] for a, b in zip(rows, rows[1:]))           # contiguous section-6 rows
    assert [i["name"] for i in s["identities"]] == [i["name"] for i in schema.load()["identities"]]


def test_variants_drop_the_missing_party_row_and_keep_the_frame():
    dl, dl8 = schema.load("mx_bcs_dl_2024"), schema.load("mx_bcs_dl_2024@sin_pes")
    ay, ay7 = schema.load("mx_bcs_ayto_2024"), schema.load("mx_bcs_ayto_2024@sin_ml")
    assert set(dl["keys"]) - set(dl8["keys"]) == {"PES"} and set(ay["keys"]) - set(ay7["keys"]) == {"ML"}
    assert dl8["layout"]["canonical"] == dl["layout"]["canonical"] and dl8["layout"]["mask"] == dl["layout"]["mask"]
    assert dl8["layout"]["landmarks"] != dl["layout"]["landmarks"]                    # its own rectification assets
    with pytest.raises(KeyError):
        schema.load("mx_bcs_dl_2024@nope")


def test_made_with_the_builder_byte_for_byte():
    """schemas/<slug>.yaml is the builder's own output (schemas/user/<slug>.yaml), and the builder re-writes it
    identically from what it loads (no information lost)."""
    from app import builder
    for slug in ("mx_bcs_dl_2024", "mx_bcs_ayto_2024"):
        a = (REPO / "schemas" / f"{slug}.yaml").read_bytes()
        assert a == (REPO / "schemas" / "user" / f"{slug}.yaml").read_bytes()
        s = builder.load_yaml(REPO / "schemas" / f"{slug}.yaml")
        assert builder.to_yaml(s).encode("utf-8") == a.replace(b"\r\n", b"\n")


def test_prompts_frozen_and_the_preregistered_ones_unchanged():
    assert reader.prompt_sha256(schema.load()) == PRES_PROMPT_SHA
    assert reader.prompt_sha256(schema.load("mx_senado_2024")) == SEN_PROMPT_SHA
    for name, sha in PROMPTS.items():
        s = schema.load(name)
        assert reader.prompt_sha256(s) == sha, name
        p = reader.build_prompt(s)
        assert p.startswith("This is a Mexican IEEBCS 2024 'Acta de Escrutinio y Computo de Casilla de la eleccion de ")
        assert f"Section 6 has exactly {len(s['fields']) - 5} rows" in p


def test_assets_have_the_mask_area_zeroed():
    for name in LAYOUTS:
        s = schema.load(name)
        for k in ("template", "reference", "landmarks"):
            a = np.load(Path(s["_dir"]) / s["layout"][k]).astype(np.float32)
            assert np.abs(a[:, int(np.ceil(EDGE * a.shape[1])) + 1:]).max() == 0, (name, k)
            assert a[:, : int(0.6 * a.shape[1])].std() > 0
        fr = np.asarray(Image.open(schema.feature_ref_path(s)).convert("L"), dtype=float)
        assert fr[:, int(0.665 * fr.shape[1]):].mean() < 8


# ------------------------------------------------------------------ manifest
def test_manifest_300_stratified_by_election_and_municipality():
    man = json.loads(MAN.read_text(encoding="utf-8"))
    its = man["items"]
    assert man["seed"] == 20261020 and man["n"] == 300 and len(its) == 300
    assert len({i["clave"] for i in its}) == 300 and len({i["image_id"] for i in its}) == 300
    assert sum(v["n"] for v in man["strata"].values()) == 300
    assert {i["stratum"].split("|")[0] for i in its} == {"dip", "ayun"}
    pop = man["population"]
    assert pop["with_image"] == 2020 and sum(pop["by_election"].values()) == 2020
    n_dip = sum(i["election"] == "diputaciones locales" for i in its)
    assert abs(n_dip - 300 * pop["by_election"]["diputaciones locales"] / 2020) <= 2   # in their proportion
    for i in its:
        base = i["schema"].split("@")[0]
        assert base == ("mx_bcs_dl_2024" if i["election"] == "diputaciones locales" else "mx_bcs_ayto_2024")
        assert i["covered"] == (i["tipo_acta"] not in ("05", "06", "07"))
        assert i["url"].endswith(f"/{i['image_id']}.jpeg")


def test_official_values_cover_every_item():
    off = json.loads(OFF.read_text(encoding="utf-8"))
    assert set(off) == {i["clave"] for i in items()}
    for i in items():
        o = off[i["clave"]]
        s = schema.load(i["schema"])
        assert set(o["prep_raw"]) == {f["key"] for f in s["fields"] if f.get("csv")}


# ------------------------------------------------------------------ mask on the real masked pages
@pytest.mark.skipif(not PAGES, reason="masked BCS pages not present (data/masked/ieebcs is local)")
def test_mask_black_and_fields_tiles_outside_it():
    man = {i["clave"]: i for i in items()}
    for p in PAGES:
        it = man[p.stem]
        s = schema.load(it["schema"])
        im = Image.open(p).convert("L")
        a = np.asarray(im, dtype=float)
        H, W = a.shape
        assert (W, H) == tuple(s["layout"]["canonical"]["size"])
        assert a[:, int(np.ceil(EDGE * W)) + 2:].max() < 40, p.name                    # names and signatures gone
        assert a[:, : int(0.65 * W)].mean() > 120
        for t in s["layout"]["tiles"]:
            assert t["box"][2] <= EDGE
        tiles = mask.tiles(im.convert("RGB"), s)
        assert len(tiles) == 4
        ink = sum(a[int(f["box"][1] * H):int(f["box"][3] * H), int(f["box"][0] * W):int(f["box"][2] * W)].min() < 140
                  for f in s["fields"])
        assert ink >= len(s["fields"]) - 3, (p.name, ink)                             # the boxes land on ink


@pytest.mark.skipif(not PAGES, reason="masked BCS pages not present")
def test_prepare_log_matches_the_masked_pages():
    log = {r["clave"]: r for r in run.jsonl(REPO / "results" / "ieebcs" / "prepare.jsonl")}
    assert set(log) == {i["clave"] for i in items()}
    ok = {k for k, r in log.items() if r["status"] == "ok"}
    assert ok == {p.stem for p in PAGES}
    assert all(r["status"] == "not_covered" for k, r in log.items() if not man_item(k)["covered"])


def man_item(k):
    return next(i for i in items() if i["clave"] == k)


# ------------------------------------------------------------------ gate on published values
def test_gate_accepts_the_published_values_when_they_add_up():
    off = json.loads(OFF.read_text(encoding="utf-8"))
    n_ok = 0
    for i in items():
        if not i["covered"]:
            continue
        s = schema.load(i["schema"])
        v = off[i["clave"]]["prep"]
        if any(v.get(k) is None for k in s["keys"] if k != "PERSONAS_Y_REP"):
            continue
        vals = []
        for f in s["fields"]:
            n = v["VOTARON"] + v["REPRESENTANTES"] if f["key"] == "PERSONAS_Y_REP" else v[f["key"]]
            lab = "+".join(f["label"]["parties"]) if "parties" in f["label"] else " ".join(f["label"]["keywords"])
            vals.append({"label": lab, "n": n, "w": n})
        g = gate.gate({"values": vals}, s)
        sums = sum(v[k] for k in s["vote_keys"]) == v["TOTAL"] == v["SACADOS"] == v["VOTARON"] + v["REPRESENTANTES"]
        assert g.accepted == sums, (i["clave"], g.reasons)
        n_ok += g.accepted
    assert n_ok > 50


# ------------------------------------------------------------------ runner dry run + scorer
@pytest.mark.skipif(not PAGES, reason="masked BCS pages not present")
def test_dry_run_two_forms_with_a_mocked_client(tmp_path, monkeypatch):
    out = tmp_path / "dry"
    out.mkdir()
    (out / "prepare.jsonl").write_bytes((REPO / "results" / "ieebcs" / "prepare.jsonl").read_bytes())  # no download
    monkeypatch.setattr(run, "LOG", out / "run.log")
    rc = run.main(["--schema", "mx_bcs_dl_2024,mx_bcs_ayto_2024", "--manifest", str(MAN), "--models", "gemma",
                   "--mock", "--limit", "2", "--out", str(out)])
    assert rc == 0
    rows = run.jsonl(out / "calls_gemma.jsonl")
    assert len(rows) == 2
    for r in rows:
        it = man_item(r["clave"])
        assert r["schema"] == it["schema"] and r["prompt_sha256"] == PROMPTS[it["schema"]]
        assert r["parsed_ok"] and not r["error"]
    # the scorer on the dry run: a reader that echoes the published values matches every numeric field it read
    monkeypatch.setattr(SC, "RES", out)
    (out / "official.json").write_bytes(OFF.read_bytes())
    sc = SC.score("gemma")
    assert sc["a_raw"]["pct"] < 100                       # the 298 actas not read count as unmatched
    assert sc["a_raw"]["second_fields_of_located_pages"]["fields"] > sc["a_raw"]["matched"] > 0
    assert len([1 for r in rows if not r.get("no_call")]) * 11 <= sc["a_raw"]["matched"]


def test_runner_refuses_a_manifest_for_other_forms(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "LOG", tmp_path / "run.log")
    assert run.main(["--schema", "mx_bcs_dl_2024", "--manifest", str(MAN), "--models", "gemma", "--mock",
                     "--limit", "1", "--out", str(tmp_path)]) == 3


def test_score_template_until_the_run():
    if not (REPO / "results" / "ieebcs" / "calls_gemma.jsonl").is_file():
        assert SC.score("gemma") is None
        assert SC.main(["--check"]) == 0
