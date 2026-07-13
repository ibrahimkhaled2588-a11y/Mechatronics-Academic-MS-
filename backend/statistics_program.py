"""
Strategic & Institutional-Level Statistics for Program Report.
Additive: inequality & balance, longitudinal growth, Monte Carlo simulation,
cohort intelligence (placeholder), institutional benchmarking.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _safe_float(x: Any) -> float | None:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ----- 1) Program Inequality & Balance -----

def gpa_inequality_index(gpa_by_course: list[float]) -> float | None:
    """Gini coefficient over course-level GPAs."""
    if not gpa_by_course or len(gpa_by_course) < 2:
        return None
    x = np.array(gpa_by_course)
    x = np.sort(x)
    n = len(x)
    cum = np.cumsum(x)
    if cum[-1] == 0:
        return None
    gini = (2 * np.sum((np.arange(1, n + 1) * x)) - (n + 1) * cum[-1]) / (n * cum[-1])
    return float(np.clip(gini, 0, 1))


def course_difficulty_dispersion(failure_rates: list[float]) -> float | None:
    """Standard deviation of failure rates across courses."""
    if not failure_rates or len(failure_rates) < 2:
        return None
    return float(np.std(failure_rates))


def academic_equity_score(gpa_by_course: list[float], failure_rates: list[float]) -> float | None:
    """Higher when GPA spread is low and failure spread is low (0-1)."""
    if not gpa_by_course:
        return None
    gpa_std = np.std(gpa_by_course)
    eq_gpa = 1 - np.minimum(gpa_std / 1.0, 1.0)
    if failure_rates:
        fail_std = np.std(failure_rates) / 100.0
        eq_fail = 1 - np.minimum(fail_std / 0.5, 1.0)
        return float((eq_gpa + eq_fail) / 2)
    return float(np.clip(eq_gpa, 0, 1))


def variance_decomposition(
    sheet_course_gpas: dict[str, list[tuple[str, float]]],
) -> dict[str, Any]:
    """Within-course vs between-course variance."""
    out = {"within_course_variance": None, "between_course_variance": None, "total_variance": None}
    all_gpas = []
    course_means = []
    for sheet, pairs in sheet_course_gpas.items():
        for _course, gpa in pairs:
            all_gpas.append(gpa)
        if pairs:
            course_means.append(np.mean([p[1] for p in pairs]))
    if len(all_gpas) < 2:
        return out
    total = float(np.var(all_gpas))
    out["total_variance"] = total
    if course_means:
        out["between_course_variance"] = float(np.var(course_means))
        out["within_course_variance"] = float(max(0, total - out["between_course_variance"]))
    return out


# ----- 2) Longitudinal Academic Growth -----

def cagr_gpa(gpa_series: list[float]) -> float | None:
    """Compound annual growth rate of GPA (interpret as trend)."""
    if not gpa_series or len(gpa_series) < 2:
        return None
    gpa_series = np.array(gpa_series)
    n = len(gpa_series) - 1
    if n <= 0 or gpa_series[0] <= 0:
        return None
    return float((gpa_series[-1] / gpa_series[0]) ** (1 / n) - 1.0)


def growth_rate_excellence(excellence_series: list[float]) -> float | None:
    if not excellence_series or len(excellence_series) < 2:
        return None
    e = np.array(excellence_series)
    return float((e[-1] - e[0]) / (e[0] + 1e-6))


def failure_trend_acceleration(failure_series: list[float]) -> float | None:
    """Second derivative (acceleration) of failure rate over time."""
    if not failure_series or len(failure_series) < 3:
        return None
    f = np.array(failure_series)
    d1 = np.diff(f)
    d2 = np.diff(d1)
    return float(np.mean(d2))


def program_momentum_score(gpa_trend: list[float], failure_trend: list[float]) -> float | None:
    """Positive when GPA rising and failure falling (0-1)."""
    if not gpa_trend or len(gpa_trend) < 2:
        return None
    gpa_slope = (gpa_trend[-1] - gpa_trend[0]) / (len(gpa_trend) - 1) if len(gpa_trend) > 1 else 0
    fail_slope = 0
    if failure_trend and len(failure_trend) >= 2:
        fail_slope = (failure_trend[-1] - failure_trend[0]) / (len(failure_trend) - 1)
    momentum = (gpa_slope * 2 - fail_slope / 50) / 2
    return float(np.clip(0.5 + momentum, 0, 1))


# ----- 3) Monte Carlo Simulation -----

def monte_carlo_gpa(
    current_mean_gpa: float,
    current_std: float,
    n_simulations: int | None = None,
    n_periods: int | None = None,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Simulate future GPA scenarios; estimate P(exceed failure threshold)."""
    from config import get_academic
    _cfg = get_academic()
    _n_sim = n_simulations if n_simulations is not None else _cfg.mc_n_simulations
    _n_per = n_periods if n_periods is not None else _cfg.mc_n_periods
    _std = max(current_std, 0.01)  # avoid zero std
    # Use a seeded Generator for reproducibility without global state mutation
    _rng = rng if rng is not None else np.random.default_rng(42)
    paths = np.zeros((_n_sim, _n_per + 1))
    paths[:, 0] = current_mean_gpa
    for t in range(1, _n_per + 1):
        paths[:, t] = paths[:, t - 1] + _rng.normal(0, _std * 0.5, _n_sim)
        paths[:, t] = np.clip(paths[:, t], 0, 4)
    final_gpas = paths[:, -1]
    return {
        "simulated_mean_final_gpa": float(np.mean(final_gpas)),
        "simulated_std_final_gpa": float(np.std(final_gpas)),
        "p_below_2": float(np.mean(final_gpas < 2.0)),
        "p_below_1_5": float(np.mean(final_gpas < 1.5)),
        "p_above_3": float(np.mean(final_gpas >= 3.0)),
        "percentile_5": float(np.percentile(final_gpas, 5)),
        "percentile_95": float(np.percentile(final_gpas, 95)),
    }


def stress_test_worst_case(
    current_failure_rates: list[float],
    n_simulations: int | None = None,
    rng: np.random.Generator | None = None,
) -> dict[str, Any]:
    """Worst-case semester: assume each course's failure rate spikes."""
    if not current_failure_rates:
        return {"worst_case_overall_failure_pct": None, "stress_percentile_95": None}
    from config import get_academic
    _cfg = get_academic()
    _n_sim = n_simulations if n_simulations is not None else _cfg.stress_n_simulations
    _rng = rng if rng is not None else np.random.default_rng(43)
    rates = np.array(current_failure_rates)
    stressed = rates * _rng.uniform(1.2, 1.8, size=(_n_sim, len(rates)))
    stressed = np.clip(stressed, 0, 100)
    overall = stressed.mean(axis=1)
    p95 = float(np.percentile(overall, 95))
    return {
        "worst_case_overall_failure_pct": p95,
        "stress_percentile_95": p95,
    }


# ----- 4) Cohort Intelligence (computed from grade data) -----

def compute_cohort_intelligence(
    gpa_by_sheet: list[float],
    failure_by_sheet: list[float],
    gpa_list: list[float],
    failure_list: list[float],
) -> dict[str, Any]:
    """
    Derive cohort-level estimates from grade distribution data.
    - cohort_retention_rate: estimated from enrollment-weighted pass rate
    - dropout_risk_probability: estimated from failure rate distribution
    - academic_recovery_rate: fraction of courses with failure rate < 15%
    """
    out: dict[str, Any] = {
        "cohort_retention_rate": None,
        "cohort_performance_curve": [],
        "dropout_risk_probability": None,
        "academic_recovery_rate": None,
        "note": "Estimated from grade distribution; no explicit student-tracking data.",
    }
    if not failure_list:
        return out

    avg_failure = float(np.mean(failure_list))
    # Retention proxy: fraction of students NOT failing on average
    retention = max(0.0, min(1.0, 1.0 - avg_failure / 100.0))
    out["cohort_retention_rate"] = round(retention, 3)

    # Dropout risk: heavier penalty when many courses exceed 30% failure
    high_fail_fraction = sum(1 for f in failure_list if f > 30) / len(failure_list)
    avg_fail_norm = avg_failure / 100.0
    dropout_risk = float(np.clip(avg_fail_norm * 0.6 + high_fail_fraction * 0.4, 0.0, 1.0))
    out["dropout_risk_probability"] = round(dropout_risk, 3)

    # Academic recovery: fraction of courses with failure rate < 15%
    recovery = sum(1 for f in failure_list if f < 15) / len(failure_list)
    out["academic_recovery_rate"] = round(recovery, 3)

    # Performance curve over sheets (GPA trend)
    if gpa_by_sheet:
        out["cohort_performance_curve"] = [round(g, 3) for g in gpa_by_sheet]

    return out


# ----- 5) Institutional Benchmarking -----

def z_score_benchmark(current: float, historical_mean: float, historical_std: float) -> float | None:
    if historical_std == 0:
        return None
    return float((current - historical_mean) / historical_std)


def percentile_ranking(value: float, all_values: list[float]) -> float | None:
    if not all_values:
        return None
    return float(100 * sum(1 for v in all_values if v <= value) / len(all_values))


def relative_performance_index(current_gpa: float, program_mean_gpa: float, program_std_gpa: float) -> float | None:
    """RPI: (current - mean) / std; positive = above average."""
    if program_std_gpa == 0:
        return 0.0
    return float((current_gpa - program_mean_gpa) / program_std_gpa)


def compute_program_statistics(
    academic: dict[str, Any],
    kpis: dict[str, Any] | None = None,
    historical_means: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Aggregate program-level advanced statistics from academic_analytics (and optional KPIs)."""
    out = {
        "inequality_balance": {},
        "longitudinal_growth": {},
        "monte_carlo_simulation": {},
        "cohort_intelligence": {},
        "benchmarking": {},
    }

    gpa_list = []
    failure_list = []
    excellence_list = []
    gpa_by_sheet = []
    failure_by_sheet = []
    sheet_course_gpas: dict[str, list[tuple[str, float]]] = {}

    for sheet, data in academic.items():
        gpa_data = data.get("top20_gpa_per_course") or []
        fail_data = data.get("top20_failure_rate") or []
        excel_data = data.get("top20_excellence_rate") or []
        for r in gpa_data:
            g = r.get("gpa_estimate")
            c = r.get("course")
            if g is not None and c:
                gpa_list.append(g)
                if sheet not in sheet_course_gpas:
                    sheet_course_gpas[sheet] = []
                sheet_course_gpas[sheet].append((c, g))
        for r in fail_data:
            if r.get("failure_rate") is not None:
                failure_list.append(r["failure_rate"])
        for r in excel_data:
            if r.get("excellence_rate") is not None:
                excellence_list.append(r["excellence_rate"])
        if gpa_data:
            sheet_gpa_mean = np.mean([x.get("gpa_estimate") for x in gpa_data if x.get("gpa_estimate") is not None])
            gpa_by_sheet.append(sheet_gpa_mean)
        if fail_data:
            sheet_fail_mean = np.mean([x.get("failure_rate") for x in fail_data if x.get("failure_rate") is not None])
            failure_by_sheet.append(sheet_fail_mean)

    # Inequality & balance
    out["inequality_balance"] = {
        "gpa_inequality_index": _safe_float(gpa_inequality_index(gpa_list)),
        "course_difficulty_dispersion": _safe_float(course_difficulty_dispersion(failure_list)),
        "academic_equity_score": _safe_float(academic_equity_score(gpa_list, failure_list)),
        "variance_decomposition": variance_decomposition(sheet_course_gpas),
    }

    # Longitudinal (fallbacks when single sheet: no trend, neutral momentum)
    cagr = cagr_gpa(gpa_by_sheet)
    if cagr is None and gpa_by_sheet:
        cagr = 0.0  # no change with single period
    growth_exc = growth_rate_excellence(excellence_list[:20])
    fail_acc = failure_trend_acceleration(failure_by_sheet)
    momentum = program_momentum_score(gpa_by_sheet, failure_by_sheet)
    if momentum is None and (gpa_by_sheet or failure_by_sheet):
        momentum = 0.5  # neutral when single sheet
    out["longitudinal_growth"] = {
        "cagr_gpa": _safe_float(cagr),
        "growth_rate_excellence": _safe_float(growth_exc),
        "failure_trend_acceleration": _safe_float(fail_acc),
        "program_momentum_score": _safe_float(momentum),
    }

    # Cohort intelligence — computed from grade data
    out["cohort_intelligence"] = compute_cohort_intelligence(
        gpa_by_sheet, failure_by_sheet, gpa_list, failure_list
    )

    # Monte Carlo
    mean_gpa = float(np.mean(gpa_list)) if gpa_list else 2.5
    std_gpa = float(np.std(gpa_list)) if len(gpa_list) > 1 else 0.4
    out["monte_carlo_simulation"] = {
        **monte_carlo_gpa(mean_gpa, std_gpa),
        "stress_test": stress_test_worst_case(failure_list),
    }

    # Benchmarking (z_score = 0 when no historical data = current is reference)
    out["benchmarking"] = {}
    if gpa_list:
        prog_mean = float(np.mean(gpa_list))
        prog_std = float(np.std(gpa_list)) or 0.4
        out["benchmarking"]["program_mean_gpa"] = prog_mean
        out["benchmarking"]["program_std_gpa"] = prog_std
        if historical_means:
            out["benchmarking"]["z_score_vs_historical"] = _safe_float(
                z_score_benchmark(prog_mean, historical_means.get("gpa", prog_mean), prog_std)
            )
        else:
            out["benchmarking"]["z_score_vs_historical"] = 0.0  # current period = reference

    return out
