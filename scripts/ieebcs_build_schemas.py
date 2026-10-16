"""PROTOCOL_IEEBCS: the two BCS acta schemas, made WITH the schema builder (/builder), through its HTTP API.

    python scripts/ieebcs_build_schemas.py      # POST /api/builder/save twice -> schemas/user/<slug>.yaml,
                                                #   then copied byte for byte to schemas/<slug>.yaml (engine path)

The builder state below is what one draws in /builder: the canonical page (2400x1562, the four printed corner
markers), the privacy mask (the whole right column: incidents, names and signatures of the mesa directiva and of
the party representatives), four zoom tiles, the ordered fields (digit box + words box per count / vote line,
measured on rectified pilot pages), and the form's identities as one-line expressions. Everything the builder has
no widget for travels in the state's ``keep`` block, which the builder writes through unchanged (see BUILDER GAPS in
PROTOCOL_IEEBCS.md 3.2): the PREP CSV column per field, the public "Option NN" codes, the row labels, the party
aliases, the prompt wording, the data source, and the layout variants (districts / municipalities whose acta prints
one row fewer). No model call; no image is read.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from twohands import REPO  # noqa: E402

W, H = 2400, 1562
MARKERS = [[0.0158, 0.0243], [0.9850, 0.0243], [0.9850, 0.9768], [0.0158, 0.9768]]
SIDE = 57  # px at 2400: marker side 0.0245 of the frame's long side
MASK = [0.662, 0.0, 1.0, 1.0]
TILES = [
    {"name": "left_column", "box": [0.0, 0.50, 0.335, 1.0], "says": "the left column (sections 2-5)"},
    {"name": "rows_top", "box": [0.325, 0.07, 0.662, 0.43], "says": "the upper rows of section 6"},
    {"name": "rows_bottom", "box": [0.325, 0.38, 0.662, 0.84],
     "says": "the lower rows of section 6 (NO REGISTRADOS/AS, VOTOS NULOS, TOTAL) and section 7"},
    {"name": "logos", "box": [0.330, 0.10, 0.395, 0.66], "says": "the logo cells of section 6, enlarged (for the labels)"},
]
LEFT_DIG, LEFT_WORDS = (0.262, 0.322), (0.012, 0.262)
ROW_LOGO_WORDS, ROW_DIG = (0.392, 0.590), (0.590, 0.658)
LEFT_Y = {"SOBRANTES": (0.594, 0.630), "VOTARON": (0.700, 0.738), "REPRESENTANTES": (0.818, 0.856),
          "PERSONAS_Y_REP": (0.912, 0.950)}
SACADOS_Y = {"dl": (0.784, 0.820), "ayto": (0.762, 0.798)}
# section-6 row tops, measured on rectified pilot pages (horizontal rules), then the TOTAL row's bottom
ROWS = {"dl": [0.116, 0.1831, 0.2497, 0.3169, 0.3841, 0.4513, 0.5186, 0.5858, 0.6527, 0.7200],          # 8 rows + TOTAL
        "dl@sin_pes": [0.1172, 0.1924, 0.2670, 0.3415, 0.4161, 0.4910, 0.5656, 0.6399, 0.7145],       # 7 rows + TOTAL
        "ayto": [0.123, 0.1959, 0.2682, 0.3409, 0.4136, 0.4859, 0.5583, 0.6309, 0.7036],               # 7 rows + TOTAL
        "ayto@sin_ml": [0.123, 0.2061, 0.2891, 0.3720, 0.4545, 0.5378, 0.6204, 0.7036]}               # 6 rows + TOTAL
HEAD = [
    ("SOBRANTES", "TOTAL_BOLETAS_SOBRANTES", "Unused ballots", "section 2 Boletas sobrantes", {"keywords": ["SOBRANTE"]}),
    ("VOTARON", "TOTAL_PERSONAS_VOTARON", "Voters on the list", "section 3 Personas de la lista nominal que votaron",
     {"keywords": ["LISTA"], "none": ["REPRESENTA"]}),
    ("REPRESENTANTES", "TOTAL_REP_PARTIDO_CI_VOTARON", "Representatives who voted",
     "section 4 Representaciones partidistas que votaron", {"keywords": ["REPRESENTA"], "none": ["TOTAL", "LISTA"]}),
    ("PERSONAS_Y_REP", None, "Voters + representatives", "section 5 Total de personas y representantes que votaron",
     {"keywords": ["TOTAL", "PERSONAS"]}),
    ("SACADOS", "TOTAL_VOTOS_SACADOS", "Ballots taken from the boxes", "section 7 Total de votos sacados de las urnas",
     {"keywords": ["SACAD"]}),
]
VOTE = {
    "dl": [("CC_PAN_PRI_PRD_PRS_PHBCS", "CC_PAN-PRI-PRD-PRS-PHBCS", ["JUNTOS"]),
           ("CC_PT_PVEM_MORENA_NABCS", "CC_PT-PVEM-MORENA-NABCS", ["MORENA_CC"]),
           ("MC", "MC", ["MC"]), ("FXM", "FXM", ["FXM"]), ("ML", "ML", ["ML"]), ("PES", "PES", ["PES"])],
    "ayto": [("CC_PAN_PRI_PRD_PRS_PHBCS", "CC_PAN-PRI-PRD-PRS-PHBCS", ["JUNTOS"]),
             ("CC_PT_PVEM_MORENA_NABCS", "CC_PT-PVEM-MORENA-NABCS", ["MORENA_CC"]),
             ("MC", "MC", ["MC"]), ("FXM", "FXM", ["FXM"]), ("ML", "ML", ["ML"])],
}
TAIL = [("NO_REGISTRADOS", "NO_REGISTRADOS", "Unregistered candidates", {"keywords": ["REGISTRAD"]}, True),
        ("NULOS", "NULOS", "Null votes", {"keywords": ["NULO"]}, True),
        ("TOTAL", "TOTAL_VOTOS_ASENTADO", "TOTAL", {"keywords": ["TOTAL"], "none": ["NULO", "SACAD", "PERSONAS", "REGISTRAD"]}, False)]
ALIASES = {"JUNTOS": ["JUNTOS", "JUNTOS POR BCS", "PAN", "PRI", "PRD", "PRS", "PHBCS"],
           "MORENA_CC": ["MORENA", "PT", "PVEM", "VERDE", "NABCS", "NUEVA ALIANZA"],
           "MC": ["MC", "MOVIMIENTO CIUDADANO"], "FXM": ["FXM", "FUERZA POR MEXICO", "FUERZA MEXICO"],
           "ML": ["ML", "MOVIMIENTO LABORISTA", "LABORISTA"], "PES": ["PES", "ENCUENTRO SOLIDARIO"]}
TITLE = {"dl": "Diputaciones Locales", "ayto": "Ayuntamiento"}
TIPO = {"dl": "02", "ayto": "03"}


def rows_of(t: str, var: str = "") -> dict:
    tops = ROWS[t + (f"@{var}" if var else "")]
    keys = [k for k, _, _ in VOTE[t] if not (var == "sin_pes" and k == "PES") and not (var == "sin_ml" and k == "ML")]
    keys += [k for k, *_ in TAIL]
    assert len(keys) == len(tops) - 1, (t, var)
    return {k: [tops[i], tops[i + 1]] for i, k in enumerate(keys)}


def state(t: str) -> dict:
    slug = f"mx_bcs_{t}_2024"
    markers = [[x - SIDE / 2 / W, y - SIDE / 2 / H, x + SIDE / 2 / W, y + SIDE / 2 / H] for x, y in MARKERS]
    fields = []
    for key, col, name, where, lab in HEAD:
        y = SACADOS_Y[t] if key == "SACADOS" else LEFT_Y[key]
        xd, xw = (ROW_DIG, ROW_LOGO_WORDS) if key == "SACADOS" else (LEFT_DIG, LEFT_WORDS)
        if key == "SACADOS":
            xw = (0.335, 0.590)
        fields.append({"key": key, "csv": col, "public": {"code": key, "name": name}, "where": where, "label": lab,
                       "box": [xd[0], y[0], xd[1], y[1]], "words_box": [xw[0], y[0], xw[1], y[1]]})
    rows = rows_of(t)
    n = 0
    for key, col, parties in VOTE[t]:
        n += 1
        y = rows[key]
        fields.append({"key": key, "csv": col, "vote": True, "public": {"code": f"OPT{n:02d}", "name": f"Option {n:02d}"},
                       "label": {"parties": parties}, "box": [ROW_DIG[0], y[0], ROW_DIG[1], y[1]],
                       "words_box": [ROW_LOGO_WORDS[0], y[0], ROW_LOGO_WORDS[1], y[1]]})
    for key, col, name, lab, vote in TAIL:
        y = rows[key]
        f = {"key": key, "csv": col}
        if vote:
            f["vote"] = True
        f |= {"public": {"code": key, "name": name}, "label": lab, "box": [ROW_DIG[0], y[0], ROW_DIG[1], y[1]],
              "words_box": [ROW_LOGO_WORDS[0], y[0], ROW_LOGO_WORDS[1], y[1]]}
        fields.append(f)
    var = "sin_pes" if t == "dl" else "sin_ml"
    drop = "PES" if t == "dl" else "ML"
    elec = "diputaciones locales" if t == "dl" else "ayuntamientos"
    top = {
        "prompt_form": f"'Acta de Escrutinio y Computo de Casilla de la eleccion de {TITLE[t]}' "
                       f"(Baja California Sur local form, type {int(TIPO[t])})",
        "prompt_issuer": "IEEBCS",
        "source": {"election": elec, "tipo_acta": TIPO[t],
                   "prep_zip": "https://prep2024.ieebcs.org.mx/bdatos/20240603_2001_PREP_BCS.zip",
                   "prep_csv": "data/raw/ieebcs/bdatos/" + ("20240603_2001_PREP_DIP_LOC_BCS/BCS_DIP_LOC_2024.csv" if t == "dl"
                                                            else "20240603_2001_PREP_AYUN_BCS/BCS_AYUN_2024.csv"),
                   "results_dir": "results/ieebcs", "masked_dir": "data/masked/ieebcs", "protocol": "PROTOCOL_IEEBCS.md",
                   "official": "results/ieebcs/official.json", "readers": ["gemma", "qwen"], "computos_csv": None},
        "party_aliases": ALIASES,
        "variants": {var: {"why": f"the {('districts' if t == 'dl' else 'municipalities')} with no {drop} candidacy print "
                                  f"one section-6 row fewer (taller rows, same frame); PREP shows '-' in the {drop} column",
                           "drop": [drop], "rows": rows_of(t, var),
                           "layout": {k: f"{slug}.{var}.{ext}" for k, ext in
                                      (("template", "template.npy"), ("reference", "reference.npy"),
                                       ("landmarks", "landmarks.npy"), ("feature_ref", "feature_ref.jpg"))}}},
    }
    return {
        "form": slug, "title": f"IEEBCS 2024 Acta de Escrutinio y Computo de Casilla, {TITLE[t]} (Baja California Sur)",
        "size": [W, H], "whole_image": False, "markers": markers, "mask": [MASK], "tiles": TILES, "fields": fields,
        "identities": ["rows sum to TOTAL: sum(@vote) == TOTAL",
                       "votaron + representantes = section 5: VOTARON + REPRESENTANTES == PERSONAS_Y_REP",
                       "section 5 = section 7: PERSONAS_Y_REP == SACADOS",
                       "section 7 = TOTAL: SACADOS == TOTAL",
                       "words == digits"],
        "keep": {"top": top,
                 "layout": {"template": f"{slug}.template.npy", "landmarks": f"{slug}.landmarks.npy",
                            "reference": f"{slug}.reference.npy", "feature_ref": f"{slug}.feature_ref.jpg",
                            "field_regions": {"left_column_sec2_5": [0.0, 0.58, 0.33, 0.96],
                                              "section6_rows": [0.333, 0.116, 0.658, 0.72],
                                              "section7_sacados": [0.335, 0.76, 0.658, 0.82]}},
                 "canonical": {}, "mask_layouts": ["movil", "escaner"]},
    }


def main() -> int:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app import builder
    app = FastAPI()
    app.include_router(builder.router)
    c = TestClient(app)
    log = []
    for t in ("dl", "ayto"):
        st = state(t)
        t0 = time.time()
        v = c.post("/api/builder/validate", json={"fields": st["fields"], "identities": st["identities"]}).json()
        bad = [ln for ln in v["lines"] if not ln.get("ok", True)]
        assert not bad, bad
        r = c.post("/api/builder/save", json=st)
        assert r.status_code == 200, r.text
        j = r.json()
        dst = REPO / "schemas" / f"{j['slug']}.yaml"
        shutil.copyfile(REPO / j["path"], dst)
        back = c.get(f"/api/builder/state/{j['slug']}").json()["state"]      # the builder reopens what it saved
        assert [f["key"] for f in back["fields"]] == [f["key"] for f in st["fields"]]
        log.append({"slug": j["slug"], "builder_path": j["path"], "engine_path": f"schemas/{j['slug']}.yaml",
                    "warnings": j["warnings"], "api_secs": round(time.time() - t0, 2)})
        print(j["slug"], "saved by the builder ->", j["path"], "-> schemas/", j["warnings"])
    print(json.dumps(log, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
