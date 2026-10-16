import json
import subprocess
import sys

from app import links
from twohands import REPO


def test_links_file_is_the_one_place_and_blocks_are_in_sync():
    data = json.loads((REPO / "submission" / "links.json").read_text(encoding="utf-8"))
    assert {"repo", "demo", "video", "audit_report_sample", "slides_pdf"} <= set(data)
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "fill_links.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_published_skips_empty_and_keeps_order(tmp_path):
    f = tmp_path / "links.json"
    f.write_text(json.dumps({"_note": "x", "repo": "https://r.example", "demo": " ", "video": "https://v.example"}))
    assert links.published(f) == [("Video", "https://v.example"), ("Source code", "https://r.example")]
    assert links.published(tmp_path / "missing.json") == []
