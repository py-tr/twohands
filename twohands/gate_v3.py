"""Gate v3 (PROTOCOL Amendment 7): gate v2 plus the ballot-stock check, with field-level routing of SOBRANTES.

SOBRANTES (unused ballots) is the one field of the presidential acta (type 2) that sits in no identity printed on the
form. It is tied to the official record by the ballot stock. A casilla receives (Reglamento de Elecciones art. 178,
numeral 1): one ballot per person on its lista nominal, plus additional ballots for the accredited party / independent
representatives, plus, where applicable, ballots for citizens with a favourable TEPJF ruling. Every ballot received
is either used (people who voted + representatives who voted) or left over (SOBRANTES), so

    E = SOBRANTES + VOTARON + REPRESENTANTES - LISTA_NOMINAL        (ballots received beyond the list)
    D = E - REPRESENTANTES_PP_CI                                     (beyond the list AND the representatives' ballots)

VOTARON is "personas de la lista nominal que votaron" and EXCLUDES representatives (the acta's own identity is
VOTARON + REPRESENTANTES = PERSONAS_Y_REP), so the sum above counts each used ballot once. LISTA_NOMINAL and
REPRESENTANTES_PP_CI come from the official PREP CSV, never from the read. On the PREP CSV D is exactly 0 on most
identity-consistent actas (scripts/ballot_stock.py); the band below is that distribution's 1st..99th percentile.

Gate v3, per form (a read that fails the frozen gate on any check that is not about SOBRANTES alone routes the whole
form, as in v1/v2):
  - the other 22 fields are accepted iff the frozen gate passes, ignoring failures that concern SOBRANTES alone
    (SOBRANTES digits empty, or SOBRANTES digits != words);
  - SOBRANTES is accepted iff the other fields are accepted AND
      (1) words and digits were both read and agree, AND
      (2) an independent second read (another model, or a second tiling of the same model) gives the same digits, AND
      (3) the ballot-stock residual D lies in the frozen band for the casilla type (needs the official lista nominal
          and representatives count; especial casillas have no lista and always route SOBRANTES);
    otherwise SOBRANTES alone is shown to a person while the other fields stay accepted.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from twohands import schema as schemamod
from twohands.gate import GateResult, gate, iv
from twohands.gate_v2 import unchecked_fields

# FROZEN by Amendment 7 (scripts/ballot_stock.py recomputes them from the PREP CSV and fails if they differ).
# D = SOBRANTES + VOTARON + REPRESENTANTES - LISTA_NOMINAL - REPRESENTANTES_PP_CI, nearest-rank 1st and 99th
# percentiles over calibration_row() rows of the PREP CSV, excluding the 300, the 100 and the 3,000 (calibrate()).
BANDS: dict[str, tuple[int, int]] = {"B": (-15, 20), "C": (-11, 20), "E": (-9, 16)}
# Secondary (literal "E in [0, E_max]" form, reported for comparison only): E_max = nearest-rank 99th percentile of E.
E_MAX: dict[str, int] = {"B": 53, "C": 53, "E": 50}
TYPES = ("B", "C", "E")
CSV_COLS = {"SOBRANTES": "TOTAL_BOLETAS_SOBRANTES", "VOTARON": "TOTAL_PERSONAS_VOTARON",
            "REPRESENTANTES": "TOTAL_REP_PARTIDO_CI_VOTARON", "SACADOS": "TOTAL_VOTOS_SACADOS",
            "TOTAL": "TOTAL_VOTOS_ASENTADO", "LN": "LISTA_NOMINAL", "A": "REPRESENTANTES_PP_CI"}


def residuals(sobrantes, votaron, representantes, lista_nominal, allowance) -> tuple[Optional[int], Optional[int]]:
    """(E, D); None where an input is missing."""
    if None in (sobrantes, votaron, representantes, lista_nominal):
        return None, None
    e = sobrantes + votaron + representantes - lista_nominal
    return e, (e - allowance if allowance is not None else None)


def tipo_of(clave: str) -> str:
    """TIPO_CASILLA from CLAVE_CASILLA (EE SSSS T NN CC): B, C, E, S, ..."""
    return clave[6]


def nearest_rank(sorted_vals: list[int], p: float) -> int:
    """Nearest-rank percentile (p in (0, 1]): the value at 1-indexed rank ceil(p * N)."""
    return sorted_vals[max(1, math.ceil(p * len(sorted_vals))) - 1]


def calibration_row(r: dict) -> Optional[dict]:
    """A PREP CSV row in the calibration population, as ints, else None: presidential acta type 2, contabilizada,
    casilla type B / C / E, lista nominal > 0, every ballot field numeric, and the acta's own identities hold in the
    capture (VOTARON + REPRESENTANTES = SACADOS = TOTAL), i.e. the forms a gate can accept."""
    if r.get("TIPO_ACTA") != "2" or r.get("CONTABILIZADA") != "1" or r.get("TIPO_CASILLA") not in TYPES:
        return None
    v = {k: iv(str(r.get(c, "")).strip()) for k, c in CSV_COLS.items()}
    if None in v.values() or v["LN"] <= 0:
        return None
    if not (v["VOTARON"] + v["REPRESENTANTES"] == v["SACADOS"] == v["TOTAL"]):
        return None
    v["E"], v["D"] = residuals(v["SOBRANTES"], v["VOTARON"], v["REPRESENTANTES"], v["LN"], v["A"])
    v["tipo"] = r["TIPO_CASILLA"]
    return v


def calibrate(rows: Iterable[dict], exclude: set = frozenset()) -> dict:
    """{tipo: {"n", "band": (lo, hi), "e_max"}} from PREP rows, excluding the claves in ``exclude``."""
    D: dict[str, list[int]] = {t: [] for t in TYPES}
    E: dict[str, list[int]] = {t: [] for t in TYPES}
    for r in rows:
        if r.get("CLAVE_CASILLA") in exclude:
            continue
        v = calibration_row(r)
        if v:
            D[v["tipo"]].append(v["D"])
            E[v["tipo"]].append(v["E"])
    out = {}
    for t in TYPES:
        if not D[t]:
            continue
        d, e = sorted(D[t]), sorted(E[t])
        out[t] = {"n": len(d), "band": (nearest_rank(d, 0.01), nearest_rank(d, 0.99)), "e_max": nearest_rank(e, 0.99)}
    return out


def stock_check(tipo: str, sobrantes, votaron, representantes, lista_nominal, allowance,
                mode: str = "band") -> tuple[bool, str]:
    """mode "band" (primary): D in BANDS[tipo]. mode "emax" (secondary): E in [0, E_MAX[tipo]]."""
    if tipo not in BANDS:
        return False, f"casilla type {tipo!r} has no fixed lista nominal: no ballot-stock check"
    if not lista_nominal:
        return False, "no official lista nominal for this casilla"
    e, d = residuals(sobrantes, votaron, representantes, lista_nominal, allowance)
    if e is None:
        return False, "ballot stock not computable (a field is missing)"
    if mode == "emax":
        ok = 0 <= e <= E_MAX[tipo]
        return ok, f"E = {e} {'in' if ok else 'outside'} [0, {E_MAX[tipo]}]"
    if d is None:
        return False, "no official representatives count for this casilla"
    lo, hi = BANDS[tipo]
    ok = lo <= d <= hi
    return ok, f"D = {d} {'in' if ok else 'outside'} [{lo}, {hi}] (E = {e}, allowance {allowance})"


@dataclass
class GateV3Result:
    others_accepted: bool               # the 22 fields other than SOBRANTES
    sobrantes_accepted: bool
    v1: GateResult
    reasons: list[str] = field(default_factory=list)            # whole-form routing reasons
    sobrantes_reasons: list[str] = field(default_factory=list)  # why SOBRANTES alone goes to a person
    checks: dict[str, Optional[bool]] = field(default_factory=dict)  # words / second / stock

    @property
    def touchless(self) -> bool:
        return self.others_accepted and self.sobrantes_accepted

    def accepted_keys(self, keys: list[str]) -> list[str]:
        if not self.others_accepted:
            return []
        return [k for k in keys if k not in UNCHECKED or self.sobrantes_accepted]

    def to_dict(self) -> dict:
        return {"others_accepted": self.others_accepted, "sobrantes_accepted": self.sobrantes_accepted,
                "touchless": self.touchless, "reasons": self.reasons, "sobrantes_reasons": self.sobrantes_reasons,
                "checks": self.checks, "v1_accepted": self.v1.accepted}


UNCHECKED = ("SOBRANTES",)


def gate_v3(parsed: Any, s: Optional[dict] = None, *, tipo: str, lista_nominal: Optional[int],
            allowance: Optional[int], second: Optional[int] = None, mode: str = "band",
            require_words: bool = True, require_second: bool = True, require_stock: bool = True) -> GateV3Result:
    """``second``: the independent second read's SOBRANTES digits (None = no usable second read).
    ``mode``: "band" (primary) or "emax" (secondary). ``require_words`` / ``require_second`` / ``require_stock`` = False
    only for the component breakdown in the post-hoc report; the pre-registered v3 requires all three."""
    s = s or schemamod.load()
    unchecked = unchecked_fields(s)
    assert tuple(unchecked) == UNCHECKED, unchecked
    v1 = gate(parsed, s)
    own = lambda msg: any(msg.startswith(f"{k} digits") for k in unchecked)  # noqa: E731
    form = [m for c, m in zip(v1.codes, v1.reasons) if not (c in ("empty", "words") and own(m))]
    r = GateV3Result(others_accepted=not form, sobrantes_accepted=False, v1=v1, reasons=form)
    k = unchecked[0]
    n, w = v1.values.get(k), v1.words.get(k)
    if require_words:
        r.checks["words"] = n is not None and w is not None and n == w
    if require_words and not r.checks["words"]:
        r.sobrantes_reasons.append(f"{k} words and digits not both read and equal (digits {n}, words {w})")
    if require_second:
        r.checks["second"] = n is not None and second is not None and second == n
        if not r.checks["second"]:
            r.sobrantes_reasons.append(f"{k} not confirmed by an independent second read (digits {n}, second {second})")
    if require_stock:
        ok, msg = stock_check(tipo, n, v1.values.get("VOTARON"), v1.values.get("REPRESENTANTES"),
                              lista_nominal, allowance, mode)
        r.checks["stock"] = ok
        if not ok:
            r.sobrantes_reasons.append(f"ballot stock: {msg}")
    r.sobrantes_accepted = r.others_accepted and not r.sobrantes_reasons
    if not r.others_accepted:
        r.sobrantes_reasons.insert(0, "the form routes")
    return r
