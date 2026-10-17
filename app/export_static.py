"""Static mirror of every public page, for GitHub Pages or any file host.

    python -m app.export_static out/ [--main-url https://twohands.example]     (or env TWOHANDS_MAIN_URL)

Renders the pages through the app itself (no server, no model call), rewrites every internal link to a RELATIVE
one (so the mirror works from a sub-path such as https://user.github.io/<repo>/), and copies only what the pages
reference: static assets, masked pages and field crops cut from masked pages. Nothing from data/raw can be reached:
images are fetched through the app's /masked and /crop routes, which refuse anything outside data/masked.

The dynamic parts (live read on AMD, photo upload, spot-check, review-desk edits) are switched off; their links go
to the main site, and every page carries the banner "Static mirror: live reading on AMD runs on the main site".
"""
from __future__ import annotations

import argparse
import html
import json
import os
import posixpath
import re
import shutil
import sys
from collections import deque
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

PAGE_RE = re.compile(r"^/(forms|audit|review|inbox|results|api|form/[A-Za-z0-9]+|ledger/[A-Za-z0-9_\-]+)?$")
ASSET_RE = re.compile(r"^/(static/[\w.\-]+|masked/[A-Za-z0-9]+\.jpg|crop/[A-Za-z0-9]+/[A-Za-z0-9_]+\.jpg|"
                      r"api/export\.(json|csv)|results/colima/(report\.html|report\.csv|colima_audit\.md|SHEET\.md))$")
ATTR_RE = re.compile(r'\b(href|src|data-start)="([^"]*)"')
JSON_URL_RE = re.compile(r'"(/(?:masked|crop|static)/[^"\s<>]*)"')
SEEDS = ["/", "/forms", "/audit", "/review", "/inbox", "/results", "/api"]
BANNER = "Static mirror: live reading on AMD runs on the main site"


def target(url: str) -> str | None:
    """Site-relative URL -> file path inside out/ (posix), or None if it is not part of the mirror."""
    sp = urlsplit(url)
    path, q = sp.path, parse_qs(sp.query)
    if PAGE_RE.match(path):
        if path.startswith("/form/") and q.get("run"):
            run = re.sub(r"[^\w\-]", "_", q["run"][0])
            return f"{path.strip('/')}/run/{run}/index.html"
        if sp.query and not path.startswith("/form/"):
            return None
        return (path.strip("/") + "/index.html").lstrip("/")
    if ASSET_RE.match(path):
        if path.startswith("/crop/") and sp.query:
            tag = ".".join(f"{k}{v[0]}" for k, v in sorted(q.items()) if k in ("pad", "label"))
            return path.lstrip("/")[:-4] + (f".{tag}" if tag else "") + ".jpg"
        if path.startswith("/api/") and sp.query:
            return None
        return path.lstrip("/")
    return None


def rel(frm: str, to: str, frag: str = "") -> str:
    d = posixpath.dirname(frm) or "."
    if to.endswith("index.html"):
        r = posixpath.relpath(posixpath.dirname(to) or ".", d)
        r = "./" if r == "." else r + "/"
    else:
        r = posixpath.relpath(to, d)
    return r + (f"#{frag}" if frag else "")


def root_prefix(frm: str) -> str:
    depth = frm.count("/")
    return "../" * depth or "./"


def shim(main_url: str, base: str) -> tuple[str, str, str]:
    """(head snippet, body-top banner + end-of-body script) injected into every mirrored page."""
    m = html.escape(main_url)
    head = (f'<script>window.TH_BASE={json.dumps(base)};window.TH_STATIC=true;'
            f'window.TH_MAIN={json.dumps(main_url)};</script>\n'
            '<style>.static-banner{background:#fff4d6;color:#4a3700;border-bottom:1px solid #e8d49a;padding:8px 16px;'
            'font:500 14px/1.4 Inter,system-ui,sans-serif;text-align:center}.static-banner a{color:inherit;'
            'font-weight:650}[data-act]{display:none!important}</style>')
    link = f' <a href="{m}">{m}</a>' if main_url else ""
    banner = f'<div class="static-banner" id="static-mirror" role="note">{BANNER}{link}.</div>'
    tail = """<script>
(function () {
  var M = window.TH_MAIN;
  document.querySelectorAll('[data-live]').forEach(function (el) {
    var a = el.querySelector('.live-act'), c = el.dataset.clave;
    if (a) a.innerHTML = M ? '<a class="btn primary" href="' + M + '/form/' + encodeURIComponent(c) + '">Read live on the main site</a>'
                         : '<span class="muted">Live reading runs on the main site.</span>';
    var n = el.querySelector('.note'); if (n) n.textContent = 'This is a static mirror: it shows the measured read. Live reading on AMD runs on the main site.';
  });
  document.querySelectorAll('.rv input, .rv textarea, .rv button').forEach(function (e) { e.disabled = true; });
  document.querySelectorAll('.rv').forEach(function (f) {
    var p = document.createElement('p'); p.className = 'tiny muted';
    p.textContent = 'Read-only in the static mirror; resolving a form runs on the main site.'; f.appendChild(p);
  });
})();
</script>"""
    return head, banner, tail


class Exporter:
    def __init__(self, out: Path, main_url: str):
        from fastapi.testclient import TestClient
        from app import main as mainmod
        self.env = mainmod.templates.env
        self.client = TestClient(mainmod.app, base_url=main_url or "http://static.invalid")
        self.out, self.main = out, main_url.rstrip("/")
        self.pages: dict[str, str] = {}      # url -> file
        self.assets: dict[str, str] = {}
        self.queue: deque[str] = deque()

    def seeds(self) -> list[str]:
        from app import store as storemod
        s = storemod.get_store()
        ledger = [f"/ledger/{sh['id']}" for sh in s.ledger.get("sheets", [])]
        return SEEDS + [f"/form/{k}" for k in s.ine_claves()] + ledger

    def enqueue(self, url: str) -> None:
        t = target(url)
        if t is None:
            return
        if t.endswith("index.html"):
            if url not in self.pages:
                self.pages[url] = t
                self.queue.append(url)
        else:
            self.assets.setdefault(url, t)

    def outside(self, url: str) -> str:
        """A link the mirror does not carry: the main site, or the banner when there is no main site."""
        return self.main + url if self.main else "#static-mirror"

    def rewrite(self, page_file: str, text: str) -> str:
        def fix(url: str) -> str:
            u = html.unescape(url).replace("\\u0026", "&")
            if not u.startswith("/") or u.startswith("//"):
                return url
            base, _, frag = u.partition("#")
            t = target(base) if base else page_file
            if t is None:
                return html.escape(self.outside(u), quote=True)
            self.enqueue(base) if base else None
            return html.escape(rel(page_file, t, frag), quote=True)

        text = ATTR_RE.sub(lambda m: f'{m.group(1)}="{fix(m.group(2))}"', text)
        text = JSON_URL_RE.sub(lambda m: '"' + html.unescape(fix(m.group(1))) + '"', text)
        return text

    def get(self, url: str):
        """GET through the app, with the header's AMD chip saying this is a mirror (restored afterwards)."""
        g = self.env.globals
        old = g["amd_status"]
        g["amd_status"] = lambda: {"state": "idle", "label": "AMD (static mirror)",
                                   "detail": "This copy serves stored reads only; live reading on AMD runs on the main site."}
        try:
            return self.client.get(url)
        finally:
            g["amd_status"] = old

    def render(self, url: str, f: str) -> None:
        r = self.get(url)
        if r.status_code != 200:
            raise RuntimeError(f"{url}: HTTP {r.status_code}")
        text = r.text
        head, banner, tail = shim(self.main, root_prefix(f))
        if url.startswith("/form/"):  # the viewer's "crop" buttons load /crop/<clave>/<code>.jpg from form.js
            clave = urlsplit(url).path.split("/")[2]
            for code in re.findall(r'data-crop="([A-Za-z0-9_]+)"', text):
                self.enqueue(f"/crop/{clave}/{code}.jpg")
        text = self.rewrite(f, text)
        text = text.replace("</head>", head + "\n</head>", 1)
        text = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + "\n" + banner, text, count=1)
        text = text.replace("</body>", tail + "\n</body>", 1)
        p = self.out / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def run(self) -> dict:
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        for u in self.seeds():
            self.enqueue(u)
        while self.queue:
            u = self.queue.popleft()
            self.render(u, self.pages[u])
        for u, f in sorted(self.assets.items()):
            r = self.client.get(u)
            if r.status_code != 200:
                raise RuntimeError(f"{u}: HTTP {r.status_code}")
            p = self.out / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(r.content)
        (self.out / ".nojekyll").write_text("", encoding="utf-8")
        nbytes = sum(p.stat().st_size for p in self.out.rglob("*") if p.is_file())
        return {"pages": len(self.pages), "assets": len(self.assets), "bytes": nbytes,
                "masked": sum(1 for f in self.assets.values() if f.startswith("masked/")),
                "crops": sum(1 for f in self.assets.values() if f.startswith("crop/"))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--main-url", default=os.environ.get("TWOHANDS_MAIN_URL", ""),
                    help="the live site (banner link, and where live read / upload / spot-check links go)")
    a = ap.parse_args(argv)
    st = Exporter(a.out, a.main_url.strip()).run()
    print(f"static mirror: {st['pages']} pages, {st['assets']} files ({st['masked']} masked pages, {st['crops']} crops), "
          f"{st['bytes'] / 1e6:.1f} MB -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
