"""
Academic Performance Analytics.
Supports both long format (one row per student, Grade column) and wide format
(one row per course, columns A/A-/A+/B/.../F with counts).

New in this version:
- Grade distribution breakdown (% per grade level) per course
- Wilson 95% confidence intervals on failure, excellence, and pass rates
- Consistent A/A+/A- excellence counting in long format
- all_courses list populated for long format too
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from kpis import excellence_rate, failure_rate, gpa_estimate, gpa_variance
from schema_inference import infer_schema
from config import get_academic

_HIGH_RISK_FAILURE_THRESHOLD = get_academic().high_risk_failure_threshold

GRADE_MAP = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}

FULL_GRADE_LABELS = ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F")

FULL_GRADE_VALUES = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "F": 0.0,
}

WIDE_GRADE_PATTERN = ("A", "A-", "A+", "B", "B-", "B+", "C", "C-", "C+", "D", "D+", "F")

ARABIC_GRADE_ALIASES = {
    "أ+": "A+", "أ": "A", "أ-": "A-",
    "ب+": "B+", "ب": "B", "ب-": "B-",
    "ج+": "C+", "ج": "C", "ج-": "C-",
    "د+": "D+", "د": "D", "ر": "F",
}


# ---------------------------------------------------------------------------
# Wilson 95% CI for a proportion
# ---------------------------------------------------------------------------

def _wilson_ci(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Return (lower%, upper%) Wilson confidence interval for a proportion."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(max(0.0, center - margin) * 100, 2), round(min(100.0, center + margin) * 100, 2)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_name(name: Any) -> str:
    return str(name).strip().lower().replace(" ", "").replace("_", "")


def _find_col_by_keywords(columns: list[str], keywords: list[str]) -> str | None:
    norm_cols = {c: _normalize_name(c) for c in columns}
    norm_keywords = [_normalize_name(k) for k in keywords]
    for col, norm in norm_cols.items():
        for kw in norm_keywords:
            if kw and kw in norm:
                return col
    return None


def _normalize_grade(val: Any) -> str | None:
    if pd.isna(val):
        return None
    s = str(val).strip().upper()
    if s in FULL_GRADE_VALUES:
        return s
    if s in GRADE_MAP:
        return s
    # Handle simple letter without +/-
    if len(s) == 1 and s in "ABCDF":
        return s
    return None


def _grade_counts_for_series(series: pd.Series) -> dict[str, int]:
    """Count all grade levels including +/- variants."""
    counts: dict[str, int] = {g: 0 for g in FULL_GRADE_LABELS}
    for v in series:
        raw = str(v).strip() if pd.notna(v) else None
        if raw is None:
            continue
        # Try Arabic alias first
        canonical = ARABIC_GRADE_ALIASES.get(raw)
        if canonical is None:
            upper = raw.upper()
            canonical = ARABIC_GRADE_ALIASES.get(upper) or upper
        if canonical in counts:
            counts[canonical] += 1
    return counts


def _grade_distribution_pct(grade_counts: dict[str, int], total: int) -> dict[str, float]:
    """Return % distribution across all grade levels."""
    if total == 0:
        return {g: 0.0 for g in FULL_GRADE_LABELS}
    return {
        g: round(grade_counts.get(g, 0) / total * 100, 2)
        for g in FULL_GRADE_LABELS
    }


def _gpa_from_full_counts(grade_counts: dict[str, int]) -> float:
    """Compute GPA using the full 12-level grade map."""
    total = sum(grade_counts.values())
    if total == 0:
        return 0.0
    weighted = sum(FULL_GRADE_VALUES.get(g, 0.0) * c for g, c in grade_counts.items())
    return weighted / total


def _gpa_variance_from_full_counts(grade_counts: dict[str, int], mean_gpa: float) -> float:
    total = sum(grade_counts.values())
    if total == 0:
        return 0.0
    return sum(
        grade_counts.get(g, 0) * (FULL_GRADE_VALUES.get(g, 0.0) - mean_gpa) ** 2
        for g in FULL_GRADE_LABELS
    ) / total


def _get_course_and_grade_columns(df: pd.DataFrame, schema: dict) -> tuple[str | None, str | None]:
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
                sample = df[c].dropna().astype(str).str.strip().str.upper()
                if sample.isin(FULL_GRADE_VALUES.keys()).any() or sample.str.match(r"^[A-F][+-]?$").any():
                    grade_col = c
                    break
    if not course_col and len(df.columns) >= 2:
        course_col = df.columns[0]
    return course_col, grade_col


# ---------------------------------------------------------------------------
# Long-format analytics
# ---------------------------------------------------------------------------

def top20_enrollment(df: pd.DataFrame, schema: dict) -> list[dict]:
    course_col, _ = _get_course_and_grade_columns(df, schema)
    if not course_col:
        return []
    counts = df[course_col].value_counts()
    top = counts.head(20)
    arr = counts.values
    mean_c = arr.mean()
    std_c = arr.std() if len(arr) > 1 else 0
    if std_c == 0:
        std_c = 1
    result = []
    for name, cnt in top.items():
        z = (cnt - mean_c) / std_c if std_c else 0
        result.append({
            "course": str(name),
            "enrollment": int(cnt),
            "abnormal_spike": bool(z > 2),
        })
    return result


def top20_excellence(df: pd.DataFrame, schema: dict) -> list[dict]:
    """Excellence Rate = (A + A+ + A-) / Total × 100. Top 20 descending."""
    course_col, grade_col = _get_course_and_grade_columns(df, schema)
    if not course_col or not grade_col:
        return []
    rates = []
    for course, grp in df.groupby(course_col):
        grade_counts = _grade_counts_for_series(grp[grade_col])
        total = sum(grade_counts.values())
        excellent = grade_counts.get("A", 0) + grade_counts.get("A+", 0) + grade_counts.get("A-", 0)
        rate = excellence_rate(excellent, total)
        rates.append({"course": str(course), "excellence_rate": round(rate, 2), "total": total})
    rates.sort(key=lambda x: -x["excellence_rate"])
    return rates[:20]


def top20_failure_rate(df: pd.DataFrame, schema: dict) -> list[dict]:
    course_col, grade_col = _get_course_and_grade_columns(df, schema)
    if not course_col or not grade_col:
        return []
    threshold = _HIGH_RISK_FAILURE_THRESHOLD
    rates = []
    for course, grp in df.groupby(course_col):
        grade_counts = _grade_counts_for_series(grp[grade_col])
        total = sum(grade_counts.values())
        failed = grade_counts.get("F", 0)
        fr = failure_rate(failed, total)
        ci_lo, ci_hi = _wilson_ci(failed, total)
        rates.append({
            "course": str(course),
            "failure_rate": round(fr, 2),
            "failure_rate_ci_lower": ci_lo,
            "failure_rate_ci_upper": ci_hi,
            "total": total,
            "high_risk": fr > threshold,
        })
    rates.sort(key=lambda x: -x["failure_rate"])
    return rates[:20]


def top20_gpa_per_course(df: pd.DataFrame, schema: dict) -> list[dict]:
    course_col, grade_col = _get_course_and_grade_columns(df, schema)
    if not course_col or not grade_col:
        return []
    result = []
    for course, grp in df.groupby(course_col):
        grade_counts = _grade_counts_for_series(grp[grade_col])
        gpa = _gpa_from_full_counts(grade_counts)
        var = _gpa_variance_from_full_counts(grade_counts, gpa)
        volatility = math.sqrt(var) if var >= 0 else 0.0
        result.append({
            "course": str(course),
            "gpa_estimate": round(gpa, 2),
            "gpa_variance": round(var, 4),
            "volatility_index": round(volatility, 4),
            "total": sum(grade_counts.values()),
        })
    result.sort(key=lambda x: -x["gpa_estimate"])
    return result[:20]


def _build_all_courses_long(df: pd.DataFrame, schema: dict) -> list[dict]:
    """Build full all_courses list for long format (same as wide format output)."""
    course_col, grade_col = _get_course_and_grade_columns(df, schema)
    if not course_col or not grade_col:
        return []
    threshold = _HIGH_RISK_FAILURE_THRESHOLD
    result = []
    n_all = len(df)
    all_enrollments = df[course_col].value_counts().values
    mean_enr = all_enrollments.mean() if len(all_enrollments) > 0 else 0
    std_enr = all_enrollments.std() if len(all_enrollments) > 1 else 0

    for course, grp in df.groupby(course_col):
        grade_counts = _grade_counts_for_series(grp[grade_col])
        total = sum(grade_counts.values())
        if total == 0:
            continue
        excellent = grade_counts.get("A", 0) + grade_counts.get("A+", 0) + grade_counts.get("A-", 0)
        failed = grade_counts.get("F", 0)
        fr = failure_rate(failed, total)
        exc_rate = excellence_rate(excellent, total)
        gpa = _gpa_from_full_counts(grade_counts)
        var = _gpa_variance_from_full_counts(grade_counts, gpa)
        volatility = math.sqrt(var) if var >= 0 else 0.0
        fr_lo, fr_hi = _wilson_ci(failed, total)
        exc_lo, exc_hi = _wilson_ci(excellent, total)
        passed = total - failed
        pr = max(0.0, 100.0 - fr)
        pr_lo, pr_hi = _wilson_ci(passed, total)
        grade_dist = _grade_distribution_pct(grade_counts, total)
        z_enr = (total - mean_enr) / std_enr if std_enr > 0 else 0
        result.append({
            "course": str(course),
            "enrollment": total,
            "abnormal_spike": bool(z_enr > 2),
            "excellence_rate": round(exc_rate, 2),
            "excellence_ci_lower": exc_lo,
            "excellence_ci_upper": exc_hi,
            "failure_rate": round(fr, 2),
            "failure_rate_ci_lower": fr_lo,
            "failure_rate_ci_upper": fr_hi,
            "pass_rate": round(pr, 2),
            "pass_rate_ci_lower": pr_lo,
            "pass_rate_ci_upper": pr_hi,
            "gpa_estimate": round(gpa, 2),
            "gpa_variance": round(var, 4),
            "volatility_index": round(volatility, 4),
            "high_risk": fr > threshold,
            "grade_distribution": grade_dist,
        })
    return result


# ---------------------------------------------------------------------------
# Wide-format analytics
# ---------------------------------------------------------------------------

def _get_wide_grade_columns(df: pd.DataFrame) -> list[str]:
    cols = []
    for c in df.columns:
        raw = str(c).strip()
        s = raw.upper()
        if s in WIDE_GRADE_PATTERN or (len(s) <= 2 and s and s[0] in "ABCDF"):
            cols.append(c)
            continue
        if raw in ARABIC_GRADE_ALIASES:
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


def compute_academic_analytics_wide(df: pd.DataFrame) -> dict[str, Any]:
    grade_cols = _get_wide_grade_columns(df)
    if not grade_cols:
        return {k: [] for k in (
            "top20_enrollment", "top20_excellence_rate", "top20_failure_rate",
            "top20_gpa_per_course", "top20_pass_rate_external",
            "top20_registered_external", "pass_rate_consistency", "all_courses",
        )}
    all_cols = list(df.columns)
    non_grade = [c for c in all_cols if c not in grade_cols]
    course_cols = [c for c in non_grade if any(
        kw in str(c).lower() for kw in ("code", "course", "title", "كود", "مقرر", "المادة")
    )]
    if not course_cols:
        course_cols = non_grade[:3]
    if not course_cols:
        course_cols = [all_cols[0]] if all_cols else []

    pass_rate_col = _find_col_by_keywords(non_grade, ["نسبة النجاح", "نسبةالنجاح", "success%", "pass%", "passrate"])
    fail_rate_col = _find_col_by_keywords(non_grade, ["نسبة الرسوب", "نسبةالرسوب", "fail%", "failure%", "failrate"])
    fail_count_col = _find_col_by_keywords(non_grade, ["رسوب", "راسب", "فشل", "failcount", "failed"])
    registered_col = _find_col_by_keywords(non_grade, [
        "عدد الطلاب", "عددالطلاب", "إجمالي", "اجمالي", "totalstudents", "registrationcount", "enrollment",
        "المسجلين", "مسجل", "المقيدين",
    ])
    # Course code / title / instructor, extracted separately so the course-report
    # generator can auto-fill Basic Information without manual entry.
    code_col = _find_col_by_keywords(non_grade, ["كود", "code"])
    title_col = _find_col_by_keywords(
        [c for c in course_cols if c != code_col], ["اسم المقرر", "اسم", "مقرر", "المادة", "title", "course"]
    ) or next((c for c in course_cols if c != code_col), None)
    instructor_col = _find_col_by_keywords(non_grade, [
        "القائم بالتدريس", "استاذ المقرر", "أستاذ المقرر", "مدرس المقرر", "استاذ", "مدرس",
        "instructor", "teacher", "lecturer", "coordinator",
    ])

    enrollment_list: list[dict[str, Any]] = []
    excellence_list: list[dict[str, Any]] = []
    failure_list: list[dict[str, Any]] = []
    gpa_list: list[dict[str, Any]] = []
    all_courses: list[dict[str, Any]] = []
    pass_rate_list: list[dict[str, Any]] = []
    registered_list: list[dict[str, Any]] = []
    consistency_list: list[dict[str, Any]] = []

    all_enrollments = []
    for _, row in df.iterrows():
        gc: dict[str, int] = {}
        for c in grade_cols:
            v = row.get(c)
            if pd.isna(v):
                v = 0
            try:
                cnt = int(float(v))
            except (TypeError, ValueError):
                cnt = 0
            if cnt > 0:
                raw_label = str(c).strip()
                upper_label = raw_label.upper()
                canonical = ARABIC_GRADE_ALIASES.get(raw_label) or ARABIC_GRADE_ALIASES.get(upper_label) or upper_label
                gc[canonical] = gc.get(canonical, 0) + cnt
        total = sum(gc.values())
        if total > 0:
            all_enrollments.append(total)
    mean_enr = float(pd.Series(all_enrollments).mean()) if all_enrollments else 0
    std_enr = float(pd.Series(all_enrollments).std()) if len(all_enrollments) > 1 else 0

    for idx, row in df.iterrows():
        try:
            course_label = _wide_course_label(row, course_cols)
            if not course_label or course_label == "Unknown":
                continue
            course_code_val = str(row.get(code_col)).strip() if code_col and pd.notna(row.get(code_col)) else None
            course_title_val = str(row.get(title_col)).strip() if title_col and pd.notna(row.get(title_col)) else None
            instructor_val = str(row.get(instructor_col)).strip() if instructor_col and pd.notna(row.get(instructor_col)) else None
            if instructor_val in ("", "nan", "None"):
                instructor_val = None
            grade_counts: dict[str, int] = {}
            for c in grade_cols:
                v = row.get(c)
                if pd.isna(v):
                    v = 0
                try:
                    cnt = int(float(v))
                except (TypeError, ValueError):
                    cnt = 0
                if cnt > 0:
                    raw_label = str(c).strip()
                    upper_label = raw_label.upper()
                    canonical = ARABIC_GRADE_ALIASES.get(raw_label) or ARABIC_GRADE_ALIASES.get(upper_label) or upper_label
                    grade_counts[canonical] = grade_counts.get(canonical, 0) + cnt
            total = sum(grade_counts.values())
            if total == 0:
                continue

            z_enr = (total - mean_enr) / std_enr if std_enr > 0 else 0
            enrollment_list.append({
                "course": course_label,
                "enrollment": total,
                "abnormal_spike": bool(z_enr > 2),
            })

            excellent = grade_counts.get("A", 0) + grade_counts.get("A+", 0) + grade_counts.get("A-", 0)
            exc_rate = excellence_rate(excellent, total)
            exc_lo, exc_hi = _wilson_ci(excellent, total)
            excellence_list.append({
                "course": course_label,
                "excellence_rate": round(exc_rate, 2),
                "excellence_ci_lower": exc_lo,
                "excellence_ci_upper": exc_hi,
                "total": total,
            })

            failed = grade_counts.get("F", 0)
            if fail_count_col and fail_count_col in row.index:
                try:
                    fc = int(float(row[fail_count_col]))
                    if fc >= 0:
                        failed = fc
                except (TypeError, ValueError):
                    pass
            fr = failure_rate(failed, total)
            fr_lo, fr_hi = _wilson_ci(failed, total)
            failure_list.append({
                "course": course_label,
                "failure_rate": round(fr, 2),
                "failure_rate_ci_lower": fr_lo,
                "failure_rate_ci_upper": fr_hi,
                "total": total,
                "high_risk": fr > _HIGH_RISK_FAILURE_THRESHOLD,
            })

            gpa = _gpa_from_full_counts(grade_counts)
            var = _gpa_variance_from_full_counts(grade_counts, gpa)
            vol = math.sqrt(var) if var >= 0 else 0.0
            gpa_list.append({
                "course": course_label,
                "gpa_estimate": round(gpa, 2),
                "gpa_variance": round(var, 4),
                "volatility_index": round(vol, 4),
                "total": total,
            })

            pr = max(0.0, 100.0 - fr)
            pr_lo, pr_hi = _wilson_ci(total - failed, total)
            grade_dist = _grade_distribution_pct(grade_counts, total)

            all_courses.append({
                "course": course_label,
                "course_code": course_code_val,
                "course_title": course_title_val,
                "instructor": instructor_val,
                "enrollment": total,
                "abnormal_spike": bool(z_enr > 2),
                "excellence_rate": round(exc_rate, 2),
                "excellence_ci_lower": exc_lo,
                "excellence_ci_upper": exc_hi,
                "failure_rate": round(fr, 2),
                "failure_rate_ci_lower": fr_lo,
                "failure_rate_ci_upper": fr_hi,
                "pass_rate": round(pr, 2),
                "pass_rate_ci_lower": pr_lo,
                "pass_rate_ci_upper": pr_hi,
                "gpa_estimate": round(gpa, 2),
                "gpa_variance": round(var, 4),
                "volatility_index": round(vol, 4),
                "high_risk": fr > _HIGH_RISK_FAILURE_THRESHOLD,
                "grade_distribution": grade_dist,
            })

            # External pass/fail/registered columns
            reported_pass_pct = None
            reported_total = None
            if pass_rate_col and pass_rate_col in row.index:
                try:
                    val = float(row[pass_rate_col])
                    reported_pass_pct = round(val * 100, 2) if 0 <= val <= 1 else round(val, 2)
                except (TypeError, ValueError):
                    pass
            if registered_col and registered_col in row.index:
                try:
                    reported_total = int(float(row[registered_col]))
                except (TypeError, ValueError):
                    pass
            if reported_pass_pct is not None:
                pass_rate_list.append({"course": course_label, "pass_rate_external": reported_pass_pct, "total_reported": reported_total})
            if reported_total is not None:
                registered_list.append({"course": course_label, "total_reported": reported_total, "total_computed": total})
            if reported_pass_pct is not None:
                pass_calc = max(0.0, 100.0 - fr)
                diff = abs(pass_calc - reported_pass_pct)
                consistency_list.append({"course": course_label, "pass_rate_external": reported_pass_pct, "pass_rate_computed": round(pass_calc, 2), "delta_abs": round(diff, 2)})
        except Exception:
            continue

    enrollment_list.sort(key=lambda x: -x["enrollment"])
    excellence_list.sort(key=lambda x: -x["excellence_rate"])
    failure_list.sort(key=lambda x: -x["failure_rate"])
    gpa_list.sort(key=lambda x: -x["gpa_estimate"])
    pass_rate_list.sort(key=lambda x: -(x.get("pass_rate_external") or 0))
    registered_list.sort(key=lambda x: -(x.get("total_reported") or 0))
    consistency_list.sort(key=lambda x: -x["delta_abs"])

    return {
        "top20_enrollment": enrollment_list[:20],
        "top20_excellence_rate": excellence_list[:20],
        "top20_failure_rate": failure_list[:20],
        "top20_gpa_per_course": gpa_list[:20],
        "top20_pass_rate_external": pass_rate_list[:20],
        "top20_registered_external": registered_list[:20],
        "pass_rate_consistency": consistency_list[:20],
        "all_courses": all_courses,
    }


def compute_academic_analytics(df: pd.DataFrame, schema: dict) -> dict[str, Any]:
    """Auto-detect wide vs long format and compute analytics."""
    if _is_wide_format(df):
        return compute_academic_analytics_wide(df)
    # Long format — compute all standard lists plus all_courses
    all_courses = _build_all_courses_long(df, schema)
    return {
        "top20_enrollment": top20_enrollment(df, schema),
        "top20_excellence_rate": top20_excellence(df, schema),
        "top20_failure_rate": top20_failure_rate(df, schema),
        "top20_gpa_per_course": top20_gpa_per_course(df, schema),
        "top20_pass_rate_external": [],
        "top20_registered_external": [],
        "pass_rate_consistency": [],
        "all_courses": all_courses,
    }
