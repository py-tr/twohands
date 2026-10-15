"""Merkle receipts on the audit report: a root over the disputed fields (leaf = canonical JSON of form, field, keyed
value, model digits and words, tier, crop SHA-256), a receipt per field (/audit/<id>/receipt/<key>) checked by
python -m twohands.verify_receipt, and the published root of the sample audit (results/sample_audit_root.txt)."""
import copy
import hashlib
import json
import re

import pytest
from fastapi.testclient import TestClient

from app import capture_audit as ca
from app.main import app
from twohands import REPO, merkle
from twohands import verify_receipt as vr

client = TestClient(app)
PUBLISHED = (REPO / "results" / "sample_audit_root.txt").read_text(encoding="utf-8").split()[0]


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    mp.setattr(ca, "AUDITS", tmp_path_factory.mktemp("s") / "audits")
    aid = client.post("/api/audit/sample").json()["id"]
    html = client.get(f"/audit/{aid}/report").text
    yield aid, html, mp
    mp.undo()


def _rec(i):
    return merkle.leaf_record(f"F{i}", "TOTAL", str(i), i + 1, i + 1, "strong", hashlib.sha256(bytes([i])).hexdigest())


@pytest.mark.parametrize("n", [1, 2, 3, 5, 8, 13])
def test_every_leaf_proves_to_the_root(n):
    recs = [_rec(i) for i in range(n)]
    leaves = [merkle.leaf_hash(r) for r in recs]
    root = merkle.root(leaves)
    for i, r in enumerate(recs):
        p = merkle.proof(leaves, i)
        assert merkle.verify(r, p, root)
        assert not merkle.verify(_rec(i + 100), p, root)


def test_leaf_is_domain_separated_and_strict():
    r = _rec(1)
    assert merkle.leaf_hash(r) == hashlib.sha256(b"\x00" + merkle.canonical(r)).hexdigest()
    assert merkle.root([]) == hashlib.sha256(b"").hexdigest()
    with pytest.raises(ValueError):
        merkle.leaf_hash({**r, "extra": 1})


def test_report_shows_root_and_receipt_links(sample):
    aid, html, mp = sample
    root = re.search(r'id="merkleroot">([0-9a-f]{64})<', html).group(1)
    assert root == PUBLISHED
    assert 'id="fingerprint"' in html
    links = re.findall(rf'href="(/audit/{aid}/receipt/[^"]+)"', html)
    assert len(links) == 267
    csv = client.get(f"/audit/{aid}/report.csv").text
    assert f"# Merkle root of the disputes (SHA-256),{root}" in csv


def test_receipt_verifies_with_its_crop_and_tamper_fails(sample, tmp_path, capsys):
    aid, html, _ = sample
    key = re.findall(rf'href="/audit/{aid}/receipt/([^"]+)"', html)[0]
    r = client.get(f"/audit/{aid}/receipt/{key}")
    assert r.status_code == 200
    rc = r.json()
    assert rc["root"] == PUBLISHED and rc["key"] == key and rc["position"] == 1
    assert set(rc["leaf"]) == set(merkle.LEAF_KEYS)
    crop = client.get(rc["crop"]).content
    assert hashlib.sha256(crop).hexdigest() == rc["leaf"]["crop_sha256"]
    p, c = tmp_path / "receipt.json", tmp_path / "crop.jpg"
    p.write_text(json.dumps(rc), encoding="utf-8")
    c.write_bytes(crop)
    assert vr.main([str(p), "--crop", str(c), "--root", PUBLISHED]) == 0
    assert "VERIFIED" in capsys.readouterr().out
    # a changed keyed value: the leaf no longer matches, nor does the path reach the root
    bad = copy.deepcopy(rc)
    bad["leaf"]["keyed"] = str(int(bad["leaf"]["keyed"]) + 1)
    p.write_text(json.dumps(bad), encoding="utf-8")
    assert vr.main([str(p)]) == 1
    # ... even if the forger also recomputes the leaf hash: the path then misses the root
    bad["leaf_hash"] = merkle.leaf_hash(bad["leaf"])
    p.write_text(json.dumps(bad), encoding="utf-8")
    assert vr.main([str(p)]) == 1
    # a changed crop fails the crop check
    p.write_text(json.dumps(rc), encoding="utf-8")
    c.write_bytes(crop[:-10] + b"0123456789")
    assert vr.main([str(p), "--crop", str(c)]) == 1
    # a different root fails
    assert vr.main([str(p), "--root", "0" * 64]) == 1
    out = capsys.readouterr().out
    assert "FAIL  crop SHA-256" in out and "NOT VERIFIED" in out


def test_receipts_follow_the_report_view(sample):
    aid, _, _ = sample
    std = client.get(f"/audit/{aid}/report").text
    strict = client.get(f"/audit/{aid}/report?strict=1").text
    rs = re.search(r'id="merkleroot">([0-9a-f]{64})<', strict).group(1)
    assert f"/audit/{aid}/receipt/" in strict and "?strict=1" in re.search(r'href="(/audit/[^"]+/receipt/[^"]+)"', strict).group(1)
    key = re.search(rf'/audit/{aid}/receipt/([^"?]+)\?strict=1', strict).group(1)
    assert client.get(f"/audit/{aid}/receipt/{key}?strict=1").json()["root"] == rs
    assert client.get(f"/audit/{aid}/receipt/nope__TOTAL").status_code == 404
    assert std != strict


def test_a_changed_tier_or_value_changes_the_root(sample):
    aid, _, _ = sample
    a = ca.load(aid)
    R = ca.run(a)
    T = ca.merkle_tree(a, R)
    assert T["root"] == PUBLISHED and T["n"] == 267
    R2 = copy.deepcopy(R)
    R2["disputes"][5]["tier"] = "weak" if R2["disputes"][5]["tier"] != "weak" else "strong"
    assert ca.merkle_tree(a, R2)["root"] != PUBLISHED


def test_published_sample_root_is_what_eval_rebuilds():
    from twohands.eval import sample_audit_root
    assert sample_audit_root() == PUBLISHED
