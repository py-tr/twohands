"""Write the submission links from submission/links.json into README.md and submission/lablab.md.

Usage:  python scripts/fill_links.py           # rewrite the blocks between <!-- links:start --> and <!-- links:end -->
        python scripts/fill_links.py --check   # exit 1 if a block is out of date

links.json is the only place the links are typed; a link left empty is written as "add at submission".
It also rewrites the closing slide's one links line in slides/slides.md (Marp treats HTML comments as speaker notes,
so that file has no block); rebuild the PDF afterwards.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LINKS = REPO / "submission" / "links.json"
TARGETS = (REPO / "README.md", REPO / "submission" / "lablab.md")
BLOCK = re.compile(r"(<!-- links:start -->\n)(.*?)(<!-- links:end -->)", re.S)
PENDING = "add at submission"
SLIDES = REPO / "slides" / "slides.md"
SLIDES_LINE = re.compile(r"^\*\*Live demo:\*\* .*$", re.M)


def _bare(url: str) -> str:
    return re.sub(r"^https?://", "", url).rstrip("/") if url else PENDING


def render_slides(links: dict) -> str:
    g = lambda k: (links.get(k) or "").strip()  # noqa: E731
    return f"**Live demo:** {_bare(g('demo'))} · **Video:** {_bare(g('video'))} · **Repo:** {_bare(g('repo'))}"


def _link(url: str, text: str | None = None) -> str:
    return f"[{text or url}]({url})" if url else PENDING


def render(links: dict, target: Path) -> str:
    g = lambda k: (links.get(k) or "").strip()  # noqa: E731
    if target.name == "README.md":
        return (
            f"**Live demo:** {_link(g('demo'))} · **Video:** {_link(g('video'))} · "
            f"**Repository:** {_link(g('repo'))} ·\n"
            f"**Audit report sample:** {_link(g('audit_report_sample'))} "
            "(in the repo: [the 52, each with its crop](results/adjudication/SUMMARY.md)) ·\n"
            "**How to reproduce:** [`make eval`](#reproduce-every-number) ·\n"
            "**Report:** [technical report (PDF)](report/two-hands-report.pdf), source [`docs/REPORT.md`](docs/REPORT.md)\n"
            "(links are kept in [`submission/links.json`](submission/links.json))\n"
        )
    return (
        f"Live demo: {g('demo') or PENDING} · Video: {g('video') or PENDING} · Repository: {g('repo') or PENDING} · "
        f"Audit report sample: {g('audit_report_sample') or PENDING} · Slides (PDF): {g('slides_pdf') or PENDING} · "
        "How to reproduce: `make eval` in the repo\n"
    )


def main(argv: list[str]) -> int:
    links = json.loads(LINKS.read_text(encoding="utf-8"))
    stale = []
    for t in TARGETS:
        text = t.read_text(encoding="utf-8")
        if not BLOCK.search(text):
            print(f"{t.name}: no links block", file=sys.stderr)
            return 2
        new = BLOCK.sub(lambda m: m.group(1) + render(links, t) + m.group(3), text, count=1)
        if new != text:
            stale.append(t.name)
            if "--check" not in argv:
                t.write_text(new, encoding="utf-8", newline="")
    if SLIDES.is_file():
        text = SLIDES.read_text(encoding="utf-8")
        if len(SLIDES_LINE.findall(text)) != 1:
            print(f"{SLIDES.name}: expected one '**Live demo:**' line", file=sys.stderr)
            return 2
        new = SLIDES_LINE.sub(lambda m: render_slides(links), text, count=1)
        if new != text:
            stale.append(SLIDES.name)
            if "--check" not in argv:
                SLIDES.write_text(new, encoding="utf-8", newline="")
    if "--check" in argv and stale:
        print("out of date: " + ", ".join(stale) + " (run python scripts/fill_links.py)", file=sys.stderr)
        return 1
    print(("updated: " + ", ".join(stale)) if stale and "--check" not in argv else "links blocks in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
