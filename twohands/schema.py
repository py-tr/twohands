"""Load a form schema (one YAML per form type)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from twohands import REPO

DEFAULT = "mx_presidencia_2024"


@lru_cache(maxsize=None)
def load(name: str = DEFAULT) -> dict:
    p = Path(name) if str(name).endswith(".yaml") else REPO / "schemas" / f"{name}.yaml"
    s = yaml.safe_load(p.read_text(encoding="utf-8"))
    s["_dir"] = str(p.parent)
    s["keys"] = [f["key"] for f in s["fields"]]
    s["vote_keys"] = [f["key"] for f in s["fields"] if f.get("vote")]
    return s


def template(s: dict):
    p = Path(s["_dir"]) / s["layout"]["template"]
    return np.load(p) if p.exists() else None


def mask_rects(s: dict, layout_kind: str) -> list[list[float]]:
    m = s["layout"]["mask"]
    return m.get(layout_kind) or m.get("escaner")


def reference(s: dict):
    p = Path(s["_dir"]) / s["layout"].get("reference", "")
    return np.load(p) if p.is_file() else None


def landmark_ref(s: dict):
    p = Path(s["_dir"]) / s["layout"].get("landmarks", "")
    return np.load(p).astype(np.float32) if p.is_file() else None
