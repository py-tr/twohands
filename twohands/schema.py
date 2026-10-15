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


def feature_ref_path(s: dict):
    """The masked reference scan for SIFT registration (Amendment 1 locator). A schema names it in
    ``layout.feature_ref``; without it, the presidential reference (as committed for Amendment 1)."""
    name = s["layout"].get("feature_ref")
    return Path(s["_dir"]) / name if name else REPO / "schemas" / "mx_presidencia_2024.feature_ref.jpg"


def source(s: dict) -> dict:
    """Where a form type's data lives (PREP CSV, TIPO_ACTA, district image index, output dirs). Paths are
    relative to the repo. Without a ``source`` block: the presidential acta's (the pre-registered 300 run)."""
    d = {"prep_csv": "data/raw/prep/PRES_2024.csv", "tipo_acta": "2",
         "district_url": "https://prep2024.ine.mx/publicacion/nacional/assets/presidencia/entidad/{ent}_{dist}.json",
         "district_cache": "data/raw/districts", "computos_csv": "data/raw/computos/PRES_2024.csv",
         "results_dir": "results", "masked_dir": "data/masked", "protocol": "PROTOCOL.md"}
    d.update(s.get("source") or {})
    return d


def sha256(name: str = DEFAULT) -> str:
    import hashlib
    p = Path(name) if str(name).endswith(".yaml") else REPO / "schemas" / f"{name}.yaml"
    return hashlib.sha256(p.read_bytes()).hexdigest()
