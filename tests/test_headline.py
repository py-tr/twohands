"""One source of truth: the pre-registered 300 summary (app/data/headline.json) is what every judge-facing page and
doc shows, to the digit; no placeholders or 'pending' anywhere judge-facing; published files name no party."""
import glob
import re

from fastapi.testclient import TestClient

from app.main import app
from app.numbers import headline, lines
from twohands import REPO

client = TestClient(app)
H = headline()
L = lines(H)
JUDGE_DOCS = ["README.md", "docs/EVALUATION.md", "docs/BUSINESS.md", "docs/AMD.md", "docs/GEMMA.md", "docs/NUMBERS.md", "docs/ARCHITECTURE.md",
              "slides/slides.md", "slides/video-script.md"]


def test_summary_numbers_are_consistent():
    v = H["verdicts"]
    assert H["fields"] == H["read"] * H["graded_per_form"]
    assert sum(v.values()) == H["disagree"] and v["model_right"] == H["keying_errors"]
    assert H["agree"] + H["disagree"] == H["fields"]
    assert H["model_wrong"] == v["capture_right"] + v["neither"]
    assert H["cert_agree"] + H["cert_differ"] == H["cert_covered"] and H["cert_differ_recount"] == H["cert_differ"]
    assert sum(t["n"] for t in H["by_type"]) == H["keying_errors"]
    assert H["acc_one_in"] == round(H["acc_fields"] / H["acc_model_wrong"])
    assert H["model_one_in"] == round(H["fields"] / H["model_wrong"])
    assert 0 <= H["recall"]["C"] <= H["recall"]["E"]


def _text(url):
    html = client.get(url).text
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    import html as htmlmod
    return htmlmod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))


def test_overview_inbox_results_audit_agree_to_the_digit():
    home, inbox, res, aud = (_text(u) for u in ("/", "/inbox", "/results", "/audit"))
    for t in (home, res, aud, inbox):
        assert "keying error" not in t.lower()
    for t in (home, res, aud):
        assert L["breakdown"] in t
    assert L["honest"] in home and L["preliminary"] in home and L["receipt"] in home
    for k in ("keying", "rate", "yield"):
        assert L[k]["label"] in home and (L[k]["small"] or "") in home
    assert L["keying"]["small2"] in home and L["faint"] in aud
    assert "1 in 5 disputed fields is a confirmed capture error (52 of 267). The capture's overall error rate is at least 1 in 122 (52 of 6,358 found so far)." in home
    assert "x the yield" not in home and "24" not in L["yield"]["label"]
    assert L["recall"] in home and L["recall"] in res
    assert f"{H['agree_pct']}%" in inbox and f"{H['agree_pct']}%" in res
    assert f"{H['accepted']} of {H['forms']} forms" in inbox and f"{H['accepted']} of {H['forms']} forms" in res
    assert f"{H['acc_model_wrong']} of {H['acc_fields']:,} fields wrong" in res
    assert L["qwen"] in res and L["qwen"] not in home and "Second-reader pass" not in home
    assert L["label_cost"] in res and L["harmonised"] in res
    rc = H["receipt"]
    assert (rc["paper"], rc["prep"], rc["certified"], rc["cert_mode"]) == (175, "75", 175, "Cotejo")


def test_docs_quote_the_summary():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    ev = (REPO / "docs" / "EVALUATION.md").read_text(encoding="utf-8")
    slides = (REPO / "slides" / "slides.md").read_text(encoding="utf-8")
    for doc in (readme, ev, slides):
        assert L["honest"].replace("\n", " ") in re.sub(r"\s+", " ", doc.replace("**", ""))
        assert f"{H['fields']:,}" in doc and f"1 in {H['acc_one_in']}" in doc
    for doc in (readme, ev):
        assert L["recall"] in re.sub(r"\s+", " ", doc)
        assert f"{H['label_gate']['read_right']} of them" in doc
    for doc in (readme, ev, slides):
        assert L["breakdown"] in re.sub(r"\s+", " ", doc) and "keying error" not in doc.lower()
    assert "about 12 to 24 times" in ev


def test_no_placeholders_or_pending_judge_facing():
    for u in ("/", "/inbox", "/results", "/audit", "/forms", "/review", "/try", "/api", "/check", "/check/results"):
        html = client.get(u).text
        assert not re.search(r"\{\{\s*[A-Za-z_]", html), u   # an unrendered template placeholder
        assert "{{" not in _text(u), u
        assert "pending" not in html.lower(), u
    for f in JUDGE_DOCS:
        t = (REPO / f).read_text(encoding="utf-8")
        assert "{{" not in t and "pending" not in t.lower(), f
    for f in glob.glob(str(REPO / "templates" / "*.html")):
        assert "pending" not in open(f, encoding="utf-8").read().lower(), f


PARTY = re.compile(r"(?<![A-Za-z0-9])(PAN|PRI|PRD|PVEM|PT|MC|MORENA)(?![A-Za-z0-9])")
PARTY_CI = re.compile(r"(?<![A-Za-z0-9])(morena|pvem|verde)(?![A-Za-z0-9])", re.I)


def test_published_human_readable_files_name_no_party():
    """Machine files (yaml, jsonl, verdicts.json keys) keep INE's column names; PROTOCOL.md is frozen as committed."""
    files = glob.glob(str(REPO / "results" / "adjudication" / "*.md")) + glob.glob(str(REPO / "results" / "*.md")) + \
        [str(REPO / f) for f in JUDGE_DOCS] + glob.glob(str(REPO / "results" / "adjudication" / "*.jpg"))
    for f in files:
        name = f.replace("\\", "/").rsplit("/", 1)[-1]
        assert not PARTY.search(name) and not PARTY_CI.search(name), name
        if f.endswith(".md"):
            t = open(f, encoding="utf-8").read()
            m = PARTY.search(t) or PARTY_CI.search(t)
            assert m is None, (name, t[max(0, m.start() - 60):m.end() + 60] if m else "")
