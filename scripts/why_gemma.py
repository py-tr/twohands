"""The "why Gemma" block (lead sentence + Gemma vs the other readers on the same forms, same gate) and the Gemma
misreads the arithmetic caught, generated from app/data/bakeoff_300.json and the stored reads (app/why_gemma.py).
No model call, no network.

    python scripts/why_gemma.py           # writes the blocks into the docs below, and the masked crops in docs/caught/
    python scripts/why_gemma.py --check   # the docs carry the current blocks and the crops exist (make eval)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from app import why_gemma as W  # noqa: E402

# doc -> the marked blocks it carries
DOCS = {"README.md": ("why-gemma",), "submission/lablab.md": ("why-gemma",),
        "docs/GEMMA.md": ("why-gemma", "caught", "same-model")}


def blocks() -> dict:
    return {"why-gemma": "\n" + W.block_md() + "\n", "caught": "\n" + W.caught_md(),
            "same-model": W.same_model_line() or ""}


def _re(name: str) -> re.Pattern:
    return re.compile(rf"(<!-- {name}:start -->)(.*?)(<!-- {name}:end -->)", re.S)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    B = blocks()
    bad = []
    for doc, names in DOCS.items():
        p = REPO / doc
        s = p.read_text(encoding="utf-8")
        new = s
        for n in names:
            m = _re(n).search(new)
            if not m:
                bad.append(f"{doc}: no <!-- {n}:start --> ... <!-- {n}:end --> block")
                continue
            if m.group(2) != B[n]:
                bad.append(f"{doc}: the {n} block differs from the data")
            new = new[:m.start(2)] + B[n] + new[m.end(2):]
        if not a.check and new != s:
            p.write_text(new, encoding="utf-8")
    if not a.check:
        crops = W.write_crops()
        print(f"why_gemma: wrote the blocks into {', '.join(DOCS)}; {len(crops)} crops in docs/caught/")
        return 0
    for c in W.caught():
        if not (REPO / "docs" / c["crop"]).is_file():
            bad.append(f"docs/{c['crop']} missing (run python scripts/why_gemma.py)")
    print(f"why_gemma --check: {len(bad)} mismatches" + "".join(f"\n  - {b}" for b in bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
