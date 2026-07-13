"""
Shared, safe grade → GPA conversion utilities.
Replaces 4+ copies of the same fragile inline pattern across the codebase.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import get_academic

_GPA_MAP: dict[str, float] = get_academic().gpa_map

# Canonical set for quick membership checks
_VALID_GRADES: frozenset[str] = frozenset(_GPA_MAP.keys())

# Arabic letter grades → canonical English
ARABIC_GRADE_ALIASES: dict[str, str] = {
    "أ+": "A+", "أ": "A", "أ-": "A-",
    "ب+": "B+", "ب": "B", "ب-": "B-",
    "ج+": "C+", "ج": "C", "ج-": "C-",
    "د+": "D+", "د": "D",
    "ر": "F",
}


def grade_to_gpa(raw: object) -> float:
    """
    Convert any grade representation to a GPA point value.

    Accepts:
      - Standard letter grades: "A", "A+", "B-", …
      - Arabic letter grades:   "أ+", "ب", "ر", …
      - Mixed-case:             "a", "b+", …
      - NaN / None / empty     → 0.0

    Returns 0.0 for unrecognised values (never raises).
    """
    if raw is None:
        return 0.0
    if isinstance(raw, float) and (np.isnan(raw) or np.isinf(raw)):
        return 0.0

    g = str(raw).strip()
    if not g or g.upper() in {"NAN", "NONE", "N/A", "-", ""}:
        return 0.0

    # Try Arabic aliases first
    arabic = ARABIC_GRADE_ALIASES.get(g)
    if arabic is not None:
        return _GPA_MAP.get(arabic, 0.0)

    upper = g.upper()

    # Exact match
    if upper in _GPA_MAP:
        return _GPA_MAP[upper]

    # First-character fallback (e.g. "A1" → "A"), only for A-F
    if upper and upper[0] in "ABCDF":
        return _GPA_MAP.get(upper[0], 0.0)

    return 0.0


def grades_to_gpa_series(series: pd.Series) -> pd.Series:
    """
    Vectorised grade → GPA conversion for an entire Series.
    ~10-50x faster than .apply(grade_to_gpa) on large frames.
    """
    # Normalise to string
    normed = series.astype(str).str.strip().str.upper()

    # Map exact matches first
    result = normed.map(_GPA_MAP)

    # Fill unmatched with Arabic alias resolution
    unmatched_mask = result.isna()
    if unmatched_mask.any():
        ar_upper = {k.upper(): v for k, v in ARABIC_GRADE_ALIASES.items()}
        arabic_gpa = {k: _GPA_MAP[v] for k, v in ar_upper.items() if v in _GPA_MAP}
        result[unmatched_mask] = normed[unmatched_mask].map(arabic_gpa)

    # Fill remaining with first-character fallback
    still_unmatched = result.isna()
    if still_unmatched.any():
        first_char = normed[still_unmatched].str[:1]
        result[still_unmatched] = first_char.map(_GPA_MAP)

    return result.fillna(0.0)


def is_valid_grade(raw: object) -> bool:
    """Return True if raw is a recognised grade letter."""
    if raw is None:
        return False
    g = str(raw).strip().upper()
    return g in _GPA_MAP or g.upper() in {k.upper() for k in ARABIC_GRADE_ALIASES}
