"""Framing rules, enforced by grep: no 'election' in page titles or headings, no aggregation or ranking by party."""
import re

from fastapi.testclient import TestClient

from app.main import app
from twohands import REPO

client = TestClient(app)
APP_CODE = list((REPO / "app").glob("*.py")) + list((REPO / "templates").glob("*.html")) + \
    list((REPO / "static").glob("*.js")) + list((REPO / "ledger").glob("*.py"))


def test_no_election_in_titles_or_headings():
    for url in ["/", "/forms", "/form/211294C0100", "/ledger/BALCOMBE-GABLES__03", "/review", "/audit", "/results",
                "/try", "/inbox", "/api"]:
        html = client.get(url).text
        for tag in ("title", "h1", "h2", "h3"):
            for t in re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", html, flags=re.S | re.I):
                assert "election" not in t.lower(), (url, tag, t)
    assert "election" not in app.title.lower()


def test_no_party_aggregation_or_ranking_code():
    forbidden = [r"\bgroupby\b", r"by_party", r"party_total", r"per_party", r"\brank(ed|ing|s)?\b",
                 r"winner", r"leaderboard", r"Counter\("]
    assert APP_CODE
    for p in APP_CODE:
        text = p.read_text(encoding="utf-8")
        for pat in forbidden:
            assert not re.search(pat, text, flags=re.I), (p.name, pat)


def test_vote_rows_only_summed_inside_the_form_identity():
    """The only sum over the vote rows is the schema identity, evaluated per form; no row is summed across forms."""
    text = (REPO / "app" / "store.py").read_text(encoding="utf-8")
    assert text.count('s["vote_keys"]') == 1
    assert "vote_keys" not in (REPO / "app" / "numbers.py").read_text(encoding="utf-8")


def test_party_names_only_used_for_the_row_label_check():
    for p in APP_CODE:
        for line in p.read_text(encoding="utf-8").splitlines():
            if "aliases" in line:
                assert p.name == "store.py" and ("label_ok(" in line or 'get("party_aliases"' in line), (p.name, line)
