"""Static mirror (app/export_static.py): relative links that work from a sub-path, masked images only, dynamic
parts switched off, banner on every page. Renders a few pages, not the whole mirror."""
import re

from app import export_static as ex
from app import main as mainmod


def test_targets_and_relative_links():
    assert ex.target("/") == "index.html"
    assert ex.target("/forms") == "forms/index.html"
    assert ex.target("/form/211294C0100?run=calls_gemma") == "form/211294C0100/run/calls_gemma/index.html"
    assert ex.target("/static/style.css?v=10") == "static/style.css"
    assert ex.target("/crop/211294C0100/TOTAL.jpg?pad=0.014&label=0") == "crop/211294C0100/TOTAL.label0.pad0.014.jpg"
    for dynamic in ("/try", "/check", "/api/live/211294C0100", "/upload/x.jpg", "/docs", "/api/export.csv?status=a"):
        assert ex.target(dynamic) is None, dynamic
    assert ex.rel("form/X/index.html", "audit/index.html") == "../../audit/"
    assert ex.rel("index.html", "index.html") == "./"
    assert ex.rel("form/X/index.html", "index.html") == "../../"
    assert ex.rel("forms/index.html", "masked/X.jpg") == "../masked/X.jpg"


def test_render_form_page(tmp_path):
    e = ex.Exporter(tmp_path, "https://main.example")
    before = mainmod.templates.env.globals["amd_status"]
    e.enqueue("/form/211294C0100")
    e.render("/form/211294C0100", e.pages["/form/211294C0100"])
    assert mainmod.templates.env.globals["amd_status"] is before   # the mirror chip does not leak into the app
    html = (tmp_path / "form/211294C0100/index.html").read_text(encoding="utf-8")
    assert ex.BANNER in html and "https://main.example" in html
    assert not re.search(r'\b(href|src|data-start)="/(?!/)', html)            # no root-absolute link survives
    assert 'href="https://main.example/try"' in html                          # dynamic pages go to the main site
    assert "window.TH_BASE=\"../../\"" in html
    assert all(f.startswith(("static/", "masked/", "crop/", "api/export.")) for f in e.assets.values())
    assert "/masked/211294C0100.jpg" in e.assets and any(u.startswith("/crop/211294C0100/") for u in e.assets)
