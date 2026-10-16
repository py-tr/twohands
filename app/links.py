"""Submission links (repo, live demo, video, sample audit report, slides) from the one file that holds them.

submission/links.json is filled once at submission; scripts/fill_links.py copies it into README.md and
submission/lablab.md, and the site footer reads it here. Empty values are links not published yet and are skipped.
"""
from __future__ import annotations

import json
from pathlib import Path

from twohands import REPO

FILE = REPO / "submission" / "links.json"
LABELS = (
    ("demo", "Live demo"),
    ("video", "Video"),
    ("repo", "Source code"),
    ("audit_report_sample", "Audit report sample"),
    ("slides_pdf", "Slides (PDF)"),
)


def load(path: Path = FILE) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v.strip() for k, v in data.items() if not k.startswith("_") and isinstance(v, str) and v.strip()}


def published(path: Path = FILE) -> list[tuple[str, str]]:
    """[(label, url)] for every link that is filled, in display order."""
    got = load(path)
    return [(label, got[key]) for key, label in LABELS if key in got]
