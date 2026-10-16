"""The technical report (docs/REPORT.md) is generated from the results files and in sync with them; every gate variant
is in it; the site links it."""
import importlib.util

import pytest
from fastapi.testclient import TestClient

from app.main import app
from twohands import REPO

spec = importlib.util.spec_from_file_location("build_report", REPO / "scripts" / "build_report.py")
br = importlib.util.module_from_spec(spec)
spec.loader.exec_module(br)


@pytest.fixture(scope="module")
def text():
    if br.ev.git("rev-parse", "--git-dir") is None:
        pytest.skip("no git history")
    return br.render(br.gather())


def test_report_in_sync_with_the_results(text):
    assert br.OUT_MD.read_text(encoding="utf-8").replace("\r\n", "\n") == text
    assert br.main(["--check"]) == 0


def test_every_gate_variant_in_one_table(text):
    table = text.split("### 4.2")[1].split("###")[0]
    for row in ("| 55 (18.3%) | 27 / 28 | 1,210 | 2 |", "| 47 (15.7%) | 24 / 23 | 1,034 | 1 |",
                "| 62 (20.7%) | 39 / 23 | 1,364 | 1 |", "| 54 (18.0%) | 27 / 27 | 1,188 | 1 |",
                "| 45 (15.0%) | 19 / 26 | 990 | 0 |", "| 89 (29.7%) | 51 / 38 | 1,958 | 0 |"):
        assert row in table, row
    assert table.count("POST-HOC") == 4


def test_key_numbers_and_framing(text):
    for s in ("267 of 6,358", "**52**", "1 in 5", "n = 7", "65% to 100%", "239 in digits", "234 in both",
              "covers 31 of the 52", "f85ca1f", "ddfabe9", "56fe2e1", "693451b"):
        assert s in text, s
    for line in text.splitlines():
        if line.startswith("#"):
            assert "election" not in line.lower(), line


def test_site_links_the_report():
    c = TestClient(app)
    assert 'href="/report.pdf">Report<' in c.get("/").text
    r = c.get("/report.pdf")
    if (REPO / "report" / "two-hands-report.pdf").is_file():
        assert r.status_code == 200 and r.content[:5] == b"%PDF-"
    else:
        assert r.status_code == 404
