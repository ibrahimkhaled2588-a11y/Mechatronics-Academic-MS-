"""Academic KPI helper formulas."""
from __future__ import annotations

import statistics as _statistics

from grade_utils import grade_to_gpa
from config import get_academic

_cfg = get_academic()

# GPA scale exported for backwards-compat imports elsewhere
GPA_VALUES: dict[str, float] = _cfg.gpa_map


def excellence_rate(excellent_count: int, total: int) -> float:
    return (excellent_count / total) * 100 if total > 0 else 0.0


def failure_rate(fail_count: int, total: int) -> float:
    return (fail_count / total) * 100 if total > 0 else 0.0


def gpa_estimate(grade_counts: dict[str, int | float]) -> float:
    """Weighted average GPA from a dict of {grade_letter: count}."""
    total = sum(grade_counts.values())
    if total == 0:
        return 0.0
    score = sum(grade_to_gpa(g) * c for g, c in grade_counts.items())
    return score / total


def gpa_variance(grade_counts: dict[str, int | float]) -> float:
    """Population variance of GPA points across all grade entries."""
    grades: list[float] = []
    for g, c in grade_counts.items():
        val = grade_to_gpa(g)
        count = max(0, int(c))
        grades.extend([val] * count)
    if len(grades) <= 1:
        return 0.0
    return _statistics.pvariance(grades)
