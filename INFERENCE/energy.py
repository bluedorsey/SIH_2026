"""Energy estimation and the SIF threshold gate.

Numbers stated in the text always win; defaults from the knowledge base fill the gaps and are
reported with their basis, so nothing is silently invented.
"""
from __future__ import annotations

import re

from .config import GRAVITY, THRESHOLDS
from .knowledge import DEFAULT_HEIGHT_M, DEFAULT_MASS_KG, default_for

_NUM = r"(\d+(?:[.,]\d+)?)"
_MASS_RE = re.compile(rf"{_NUM}\s?(kg|kilo|kgs|ton|tonne|t\b)", re.I)
_HEIGHT_RE = re.compile(rf"{_NUM}\s?(m\b|meter|metre|mtr|ft\b|feet|foot)", re.I)
_VOLT_RE = re.compile(rf"{_NUM}\s?(kv|volt|v\b)", re.I)
_PRESS_RE = re.compile(rf"{_NUM}\s?(bar|psi|kg/cm2|kpa|mpa)", re.I)
_TEMP_RE = re.compile(rf"{_NUM}\s?(deg|°)?\s?c\b", re.I)


def _f(v: str) -> float:
    return float(v.replace(",", "."))


def _first(rx: re.Pattern, text: str):
    m = rx.search(text)
    return (m, _f(m.group(1)), m.group(2).lower() if m.lastindex and m.lastindex >= 2 else "") if m else (None, None, "")


def estimate(text: str, energy_type: str | None) -> dict:
    """Return the energy block of the response: value, inputs, basis, threshold and gate."""
    out: dict = {"type": energy_type, "estimate_j": None, "range_j": None, "basis": None,
                 "formula": None, "inputs": {}, "threshold_j": None, "gate": "UNKNOWN"}

    if energy_type == "electrical":
        m, val, unit = _first(_VOLT_RE, text)
        if m:
            volts = val * 1000 if unit == "kv" else val
            out.update(type="electrical", estimate_j=None, basis="stated", formula=None,
                       inputs={"voltage_v": {"value": volts, "basis": "stated"}},
                       threshold_j=None,
                       gate="EXCEEDS" if volts >= THRESHOLDS["electrical_v"] else "BELOW")
            out["threshold_v"] = THRESHOLDS["electrical_v"]
        return out

    if energy_type == "pressure":
        m, val, unit = _first(_PRESS_RE, text)
        if m:
            bar = val / 14.5038 if unit == "psi" else (val / 100 if unit == "kpa" else
                                                       (val * 10 if unit == "mpa" else val))
            out.update(type="pressure", basis="stated",
                       inputs={"pressure_bar": {"value": round(bar, 2), "basis": "stated"}},
                       gate="EXCEEDS" if bar >= THRESHOLDS["pressure_bar"] else "BELOW")
            out["threshold_bar"] = THRESHOLDS["pressure_bar"]
        return out

    if energy_type == "thermal":
        m, val, _ = _first(_TEMP_RE, text)
        if m:
            out.update(type="thermal", basis="stated",
                       inputs={"temperature_c": {"value": val, "basis": "stated"}},
                       gate="EXCEEDS" if val >= THRESHOLDS["temperature_c"] else "BELOW")
            out["threshold_c"] = THRESHOLDS["temperature_c"]
        return out

    if energy_type != "gravity":
        return out

    # ---- gravity: m * g * h, stated numbers first, then knowledge-base defaults
    mm, mass, munit = _first(_MASS_RE, text)
    if mass is not None and munit.startswith(("ton", "t")):
        mass *= 1000
    mass_basis = "stated" if mass is not None else None
    if mass is None:
        d = default_for(text, DEFAULT_MASS_KG)
        if d:
            mass_basis, mass = d

    hm, height, hunit = _first(_HEIGHT_RE, text)
    if height is not None and hunit.startswith(("ft", "fe", "fo")):
        height *= 0.3048
    height_basis = "stated" if height is not None else None
    if height is None:
        d = default_for(text, DEFAULT_HEIGHT_M)
        if d:
            height_basis, height = d

    if mass is None or height is None:
        out.update(type="gravity", basis="insufficient", formula="m*g*h")
        if mass is not None:
            out["inputs"]["mass_kg"] = {"value": round(mass, 2), "basis": mass_basis}
        if height is not None:
            out["inputs"]["height_m"] = {"value": round(height, 2), "basis": height_basis}
        return out

    joules = mass * GRAVITY * height
    drops = drops_fatal(mass, height)
    both_stated = mass_basis == "stated" and height_basis == "stated"
    # a defaulted input is an estimate, so widen the interval to +-30 % on that side
    lo = mass * GRAVITY * height * (1.0 if both_stated else 0.7)
    hi = mass * GRAVITY * height * (1.0 if both_stated else 1.4)
    out.update(type="gravity", estimate_j=round(joules), range_j=[round(lo), round(hi)],
               basis="stated" if both_stated else "inferred", formula="m*g*h",
               inputs={"mass_kg": {"value": round(mass, 2), "basis": mass_basis},
                       "height_m": {"value": round(height, 2), "basis": height_basis}},
               threshold_j=THRESHOLDS["dropped_object_j"],
               drops_fatal=drops,
               gate="EXCEEDS" if (joules >= THRESHOLDS["dropped_object_j"] or drops) else "BELOW",
               gate_basis="drops_matrix" if (drops and joules < THRESHOLDS["dropped_object_j"])
                          else "joules")
    return out


# DROPS (Dropped Objects Prevention Scheme) practice: fatality potential is a mass-BY-height
# matrix, not a single joule figure. A 1.2 kg spanner from 20 m is 238 J - below a flat 680 J
# gate - yet squarely lethal. Anything at or above these heights for its mass band is treated as
# SIF-capable regardless of the joule count.
_DROPS_FATAL_HEIGHT_M = [   # (mass_kg at least, height_m at which it can kill)
    (10.0, 2.0),
    (5.0, 3.0),
    (2.0, 6.0),
    (1.0, 10.0),
    (0.5, 15.0),
    (0.1, 25.0),
]


def drops_fatal(mass_kg: float | None, height_m: float | None) -> bool:
    """True when a falling object of this mass from this height can kill a person below."""
    if mass_kg is None or height_m is None:
        return False
    for m_min, h_min in _DROPS_FATAL_HEIGHT_M:
        if mass_kg >= m_min:
            return height_m >= h_min
    return height_m >= 30.0          # very light objects still hurt from great height


def person_fall_exceeds(text: str) -> bool | None:
    """A PERSON falling is gated on height (1.2 m), not on joules."""
    m, height, unit = _first(_HEIGHT_RE, text)
    if m is None:
        return None
    if unit.startswith(("ft", "fe", "fo")):
        height *= 0.3048
    return height >= THRESHOLDS["gravity_fall_m"]
