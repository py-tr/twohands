"""Write the submission links from submission/links.json into README.md and submission/lablab.md.

Usage:  python scripts/fill_links.py           # rewrite the blocks between <!-- links:start --> and <!-- links:end -->
        python scripts/fill_links.py --check   # exit 1 if a block is out of date

links.json is the only place the links are typed; a link left empty is written as "add at submission".
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
    if "--check" in argv and stale:
        print("out of date: " + ", ".join(stale) + " (run python scripts/fill_links.py)", file=sys.stderr)
        return 1
    print(("updated: " + ", ".join(stale)) if stale and "--check" not in argv else "links blocks in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
