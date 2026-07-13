"""
Deep Academic Statistical Profiling for Course Report.
Additive: grade distribution deep metrics, performance segmentation,
fairness indicators, risk modeling, behavioral correlations.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from grade_utils import grade_to_gpa, grades_to_gpa_series

logger = logging.getLogger(__name__)

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from sklearn.cluster import KMeans
    from sklearn.mixture import GaussianMixture
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# GPA mapping for grade letters (same as kpis.py)
GPA_VALUES = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "F": 0.0,
}


def _get_grade_numeric_series(df: pd.DataFrame, course_col: str, grade_col: str, course_name: str) -> np.ndarray | None:
    grp = df[df[course_col].astype(str) == str(course_name)]
    if grp.empty:
        return None
    vals = grades_to_gpa_series(grp[grade_col].dropna())
    arr = vals.values
    return arr if len(arr) > 0 else None


def _get_course_grade_cols(df: pd.DataFrame, schema: dict) -> tuple[str | None, str | None]:
    ir = schema.get("inferred_roles", {})
    course_col = ir.get("course")
    grade_col = ir.get("grade")
    if course_col and course_col in df.columns:
        course_col = str(course_col)
    else:
        course_col = None
    if grade_col and grade_col in df.columns:
        grade_col = str(grade_col)
    else:
        grade_col = None
    if not grade_col:
        for c in df.columns:
            if df[c].dtype == object or pd.api.types.is_string_dtype(df[c]):
                sample = df[c].dropna().astype(str).str.upper()
                if sample.isin(GPA_VALUES.keys()).any() or sample.str.match(r"^[A-F]$").any():
                    grade_col = c
                    break
    if not course_col and len(df.columns) >= 2:
        course_col = df.columns[0]
    return course_col, grade_col


# ----- Wide format (same course labels as academic_analytics) -----
WIDE_GRADE_PATTERN = ("A", "A-", "A+", "B", "B-", "B+", "C", "C-", "C+", "D", "D+", "F")
ARABIC_GRADE_ALIASES = {"أ+": "A+", "أ": "A", "أ-": "A-", "ب+": "B+", "ب": "B", "ب-": "B-", "ج+": "C+", "ج": "C", "ج-": "C-", "د+": "D+", "د": "D", "ر": "F"}


def _get_wide_grade_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in df.columns:
        raw = str(c).strip()
        s = raw.upper()
        if s in WIDE_GRADE_PATTERN or (len(s) <= 2 and s and s[0] in "ABCDEF"):
            cols.append(c)
        elif raw in ARABIC_GRADE_ALIASES:
            cols.append(c)
    return cols


def _is_wide_format(df: pd.DataFrame) -> bool:
    return len(_get_wide_grade_columns(df)) >= 3


def _wide_course_label(row: pd.Series, course_cols: list[str]) -> str:
    parts = []
    for c in course_cols:
        if c in row.index:
            v = row[c]
            if pd.notna(v) and str(v).strip():
                parts.append(str(v).strip())
    return " / ".join(parts) if parts else "Unknown"


def _grade_counts_from_wide_row(row: pd.Series, grade_cols: list[str]) -> dict[str, int]:
    """Map column name to canonical grade key and count."""
    counts = {}
    for c in grade_cols:
        v = row.get(c)
        if pd.isna(v):
            v = 0
        try:
            cnt = int(float(v))
        except (TypeError, ValueError):
            cnt = 0
        if cnt <= 0:
            continue
        raw = str(c).strip().upper()
        key = ARABIC_GRADE_ALIASES.get(str(c).strip(), raw)
        if len(key) <= 2 and key[0] in "ABCDEF":
            counts[key] = counts.get(key, 0) + cnt
    return counts


def _gpa_values_from_grade_counts(grade_counts: dict[str, int]) -> np.ndarray | None:
    """Expand grade counts to list of GPA values for MAD/trimmed mean/Gini."""
    vals = []
    for g, cnt in grade_counts.items():
        gpa = grade_to_gpa(g)
        vals.extend([gpa] * max(0, int(cnt)))
    return np.array(vals) if vals else None


# ----- 1) Grade Distribution Deep Metrics -----

def median_absolute_deviation(x: np.ndarray) -> float | None:
    if x is None or len(x) < 2:
        return None
    med = np.median(x)
    return float(np.median(np.abs(x - med)))


def trimmed_mean(x: np.ndarray, trim_frac: float) -> float | None:
    if x is None or len(x) < 2:
        return None
    k = int(len(x) * trim_frac)
    if k >= len(x) // 2:
        return None
    sx = np.sort(x)
    sx = sx[k : len(sx) - k]
    return float(np.mean(sx)) if len(sx) > 0 else None


def mode_frequency_pct(x: np.ndarray) -> float | None:
    if x is None or len(x) == 0:
        return None
    vals, counts = np.unique(x, return_counts=True)
    max_count = counts.max()
    return float(max_count / len(x) * 100)


def grade_concentration_ratio(x: np.ndarray, top_frac: float = 0.5) -> float | None:
    """Share of total grade mass held by top fraction of grades (by value)."""
    if x is None or len(x) == 0:
        return None
    sx = np.sort(x)[::-1]
    k = max(1, int(len(sx) * top_frac))
    return float(sx[:k].sum() / sx.sum()) if sx.sum() != 0 else None


def gini_coefficient(x: np.ndarray) -> float | None:
    """Inequality index for grade distribution (0 = equal, 1 = max inequality)."""
    if x is None or len(x) < 2:
        return None
    x = np.sort(np.clip(x, 0, 4))
    n = len(x)
    cum = np.cumsum(x)
    return float((2 * np.sum((np.arange(1, n + 1) * x)) - (n + 1) * cum[-1]) / (n * cum[-1])) if cum[-1] != 0 else None


def grade_distribution_deep_metrics(gpa_values: np.ndarray | None) -> dict[str, Any]:
    out = {
        "median_absolute_deviation": None,
        "trimmed_mean_5": None,
        "trimmed_mean_10": None,
        "mode_frequency_pct": None,
        "grade_concentration_ratio": None,
        "inequality_index_gini": None,
    }
    if gpa_values is None or len(gpa_values) < 2:
        return out
    out["median_absolute_deviation"] = _safe_float(median_absolute_deviation(gpa_values))
    out["trimmed_mean_5"] = _safe_float(trimmed_mean(gpa_values, 0.05))
    out["trimmed_mean_10"] = _safe_float(trimmed_mean(gpa_values, 0.10))
    out["mode_frequency_pct"] = _safe_float(mode_frequency_pct(gpa_values))
    out["grade_concentration_ratio"] = _safe_float(grade_concentration_ratio(gpa_values))
    out["inequality_index_gini"] = _safe_float(gini_coefficient(gpa_values))
    return out


def _safe_float(x: Any) -> float | None:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ----- 2) Performance Segmentation -----

def segment_students_kmeans(gpa_by_student: np.ndarray, n_segments: int = 4) -> tuple[np.ndarray, list[str]]:
    """Returns labels 0..n_segments-1 and segment names."""
    if not HAS_SKLEARN or gpa_by_student is None or len(gpa_by_student) < n_segments:
        return np.array([]), []
    X = gpa_by_student.reshape(-1, 1)
    n = min(n_segments, len(np.unique(X)))
    if n < 2:
        return np.zeros(len(X), dtype=int), ["All"]
    km = KMeans(n_clusters=n, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    centers = sorted(km.cluster_centers_.ravel())
    names = []
    for c in centers:
        if c >= 3.5:
            names.append("High Achievers")
        elif c >= 2.5:
            names.append("Stable Performers")
        elif c >= 1.5:
            names.append("At-Risk Students")
        else:
            names.append("Critical Risk Students")
    return labels, names[:n]


def performance_segmentation(df: pd.DataFrame, schema: dict) -> dict[str, Any]:
    """Per-sheet segmentation by student (if student_id exists) or by course mean GPA."""
    out = {"by_student": {}, "by_course": {}, "segment_transition_rate": None, "performance_mobility_index": None}
    course_col, grade_col = _get_course_grade_cols(df, schema)
    if not course_col or not grade_col:
        return out
    student_col = schema.get("inferred_roles", {}).get("student_id")
    if student_col and student_col in df.columns and HAS_SKLEARN:
        grp = df.groupby(student_col)[grade_col].apply(grades_to_gpa_series)
        student_gpa = grp.groupby(level=0).mean().dropna()
        if len(student_gpa) >= 4:
            arr = student_gpa.values
            labels, names = segment_students_kmeans(arr)
            out["by_student"] = {
                "segment_labels": labels.tolist(),
                "segment_names": names,
                "student_gpa_mean": float(np.mean(arr)),
            }
    # By course: use mean GPA per course as "profile"
    course_means = df.groupby(course_col)[grade_col].apply(
        lambda s: grades_to_gpa_series(s.dropna()).mean()
    ).dropna()
    if HAS_SKLEARN and len(course_means) >= 2:
        arr = course_means.values.reshape(-1, 1)
        n = min(4, len(arr))
        km = KMeans(n_clusters=n, random_state=42, n_init=10)
        labels = km.fit_predict(arr)
        out["by_course"] = {
            "segment_labels": labels.tolist(),
            "course_names": course_means.index.astype(str).tolist(),
        }
    return out


# ----- 3) Assessment Fairness Indicators -----

def grade_inflation_deflation_index(course_gpa: float, program_mean_gpa: float) -> dict[str, Any]:
    """Inflation > 0 when course mean above program; deflation when below."""
    diff = course_gpa - program_mean_gpa
    return {
        "grade_inflation_index": float(diff) if diff > 0 else 0.0,
        "grade_deflation_index": float(-diff) if diff < 0 else 0.0,
        "z_score_vs_program": (diff / 0.5) if 0.5 != 0 else 0.0,
    }


def difficulty_index(failure_rate_pct: float) -> float:
    """Difficulty: higher failure rate = higher difficulty."""
    return failure_rate_pct / 100.0


def inter_course_grading_bias(course_gpas: list[float], program_mean: float, program_std: float) -> list[float]:
    """Z-scores of each course mean vs program."""
    if program_std == 0:
        return [0.0] * len(course_gpas)
    return [(g - program_mean) / program_std for g in course_gpas]


# ----- 4) Risk Modeling -----

def logistic_failure_prediction(X: np.ndarray, y_binary: np.ndarray) -> dict[str, Any]:
    """Logistic regression for failure (y=1). Returns coefficients, odds ratio interpretation."""
    out = {"coefficients": None, "odds_ratio_interpretation": None, "intercept": None}
    if not HAS_SKLEARN or X is None or y_binary is None or len(X) < 10 or X.shape[1] >= len(X):
        return out
    try:
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        lr = LogisticRegression(max_iter=500, random_state=42)
        lr.fit(X, y_binary)
        out["coefficients"] = lr.coef_.ravel().tolist()
        out["intercept"] = float(lr.intercept_[0])
        if len(lr.coef_.ravel()) > 0:
            exp_c = np.exp(lr.coef_.ravel())
            out["odds_ratio_interpretation"] = [float(x) for x in exp_c]
        return out
    except Exception:
        return out


def survival_hazard_placeholder(failure_rate_pct: float, n_students: int) -> dict[str, Any]:
    """Placeholder: probability of passing over time; hazard ratio for failure."""
    p_fail = failure_rate_pct / 100.0
    p_pass = 1.0 - p_fail
    return {
        "probability_passing": float(p_pass),
        "hazard_ratio_failure": float(p_fail / 0.2) if 0.2 != 0 else 0.0,
    }


# ----- 5) Behavioral Correlations -----

def correlation_matrix(df: pd.DataFrame, course_col: str, grade_col: str, schema: dict) -> dict[str, Any]:
    """Pearson, Spearman, Kendall between courses (student-level grades); requires student_id in schema."""
    out = {"pearson": {}, "spearman": {}, "kendall": {}, "partial_correlation_available": False}
    if course_col not in df.columns or grade_col not in df.columns:
        return out
    student_col = (schema.get("inferred_roles") or {}).get("student_id")
    if not student_col or student_col not in df.columns:
        return out
    try:
        def to_gpa(g):
            v = grade_to_gpa(g)
            return v if v > 0 or g in {"F", "ر"} else np.nan
        gpa_series = df[grade_col].map(to_gpa)
        df = df.copy()
        df["_gpa_num"] = gpa_series
        pivot = df.pivot_table(index=student_col, columns=course_col, values="_gpa_num", aggfunc="first")
        if pivot is None or pivot.shape[1] < 2 or pivot.shape[0] < 3:
            return out
        pivot = pivot.dropna(how="all")
        if pivot.shape[0] < 3:
            return out
        if HAS_SCIPY:
            out["pearson"] = _corr_dict(pivot, "pearson")
            out["spearman"] = _corr_dict(pivot, "spearman")
            out["kendall"] = _corr_dict(pivot, "kendall")
        return out
    except Exception:
        return out


def _corr_dict(pivot: pd.DataFrame, method: str) -> dict[str, Any]:
    try:
        c = pivot.corr(method=method)
        return {str(a): {str(b): float(c.loc[a, b]) for b in c.columns} for a in c.index}
    except Exception:
        return {}


def _compute_course_statistics_wide(df: pd.DataFrame) -> dict[str, Any]:
    """Wide format: one row per course, grade columns = counts. Same course labels as academic_analytics."""
    out = {
        "grade_distribution_deep": {},
        "performance_segmentation": {},
        "fairness_indicators": {},
        "risk_modeling": {},
        "correlations": {},
    }
    grade_cols = _get_wide_grade_columns(df)
    if not grade_cols:
        return out
    all_cols = list(df.columns)
    non_grade = [c for c in all_cols if c not in grade_cols]
    course_cols = [c for c in non_grade if "code" in str(c).lower() or "course" in str(c).lower() or "title" in str(c).lower()]
    if not course_cols:
        course_cols = non_grade[:3]
    if not course_cols:
        course_cols = [all_cols[0]] if all_cols else []

    all_gpas = []
    course_gpa_list = []
    course_fail_list = []
    for _idx, row in df.iterrows():
        course_label = _wide_course_label(row, course_cols)
        if not course_label or course_label == "Unknown":
            continue
        grade_counts = _grade_counts_from_wide_row(row, grade_cols)
        total = sum(grade_counts.values())
        if total < 2:
            continue
        gpa_vals = _gpa_values_from_grade_counts(grade_counts)
        if gpa_vals is None or len(gpa_vals) < 2:
            continue
        out["grade_distribution_deep"][course_label] = grade_distribution_deep_metrics(gpa_vals)
        gpa_mean = float(np.mean(gpa_vals))
        fail_pct = float((gpa_vals == 0).sum() / len(gpa_vals) * 100)
        all_gpas.extend(gpa_vals.tolist())
        course_gpa_list.append((course_label, gpa_mean))
        course_fail_list.append((course_label, fail_pct))

    program_mean = float(np.mean(all_gpas)) if all_gpas else None
    for course_name, gpa_mean in course_gpa_list:
        fail_pct = next((f[1] for f in course_fail_list if f[0] == course_name), 0)
        if program_mean is not None:
            out["fairness_indicators"][course_name] = {
                **grade_inflation_deflation_index(gpa_mean, program_mean),
                "difficulty_index": difficulty_index(fail_pct),
            }
        out["risk_modeling"][course_name] = survival_hazard_placeholder(fail_pct, 100)
    return out


def compute_course_statistics_for_sheet(
    df: pd.DataFrame,
    schema: dict,
    academic_sheet: dict,
) -> dict[str, Any]:
    """Per-sheet course-level deep statistics. Supports long and wide format."""
    out = {
        "grade_distribution_deep": {},
        "performance_segmentation": {},
        "fairness_indicators": {},
        "risk_modeling": {},
        "correlations": {},
    }
    if _is_wide_format(df):
        return _compute_course_statistics_wide(df)

    course_col, grade_col = _get_course_grade_cols(df, schema)
    if not course_col or not grade_col:
        return out

    courses = df[course_col].dropna().unique().astype(str).tolist()
    all_gpas = []
    course_gpa_list = []
    course_fail_list = []
    for course_name in courses:
        gpa_vals = _get_grade_numeric_series(df, course_col, grade_col, course_name)
        if gpa_vals is None or len(gpa_vals) < 2:
            continue
        out["grade_distribution_deep"][course_name] = grade_distribution_deep_metrics(gpa_vals)
        all_gpas.extend(gpa_vals.tolist())
        course_gpa_list.append((course_name, float(np.mean(gpa_vals))))
        course_fail_list.append((course_name, float((gpa_vals == 0).sum() / len(gpa_vals) * 100)))

    program_mean = float(np.mean(all_gpas)) if all_gpas else None
    program_std = float(np.std(all_gpas)) if all_gpas and len(all_gpas) > 1 else 0.5

    for course_name, gpa_mean in course_gpa_list:
        fail_pct = next((f[1] for f in course_fail_list if f[0] == course_name), 0)
        if program_mean is not None:
            out["fairness_indicators"][course_name] = {
                **grade_inflation_deflation_index(gpa_mean, program_mean),
                "difficulty_index": difficulty_index(fail_pct),
            }
        out["risk_modeling"][course_name] = survival_hazard_placeholder(fail_pct, 100)

    out["performance_segmentation"] = performance_segmentation(df, schema)
    try:
        out["correlations"] = correlation_matrix(df, course_col, grade_col, schema)
    except Exception:
        pass
    return out
