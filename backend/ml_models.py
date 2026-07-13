"""
ML layer: predict quality degradation, course risk, and academic trend forecasting.

NOTE: The degradation predictor and risk scorer are rule-based heuristics.
      forecast_academic_trends() uses Ordinary Least Squares regression over
      multi-sheet data (treating each sheet as a time point).
"""
from __future__ import annotations

import numpy as np
from typing import Any

_STATIC_WEIGHTS = {
    "precision": 0.35,
    "consistency": 0.25,
    "completeness": 0.20,
    "anomaly": 0.20,
}

_OUTLOOK_HIGH_RISK = 0.50
_OUTLOOK_STABLE = 0.85
_OUTLOOK_MODERATE = 0.70

_COURSE_RISK_FAILURE_WEIGHT = 1.2
_COURSE_RISK_HIGH_RISK_BONUS = 0.3
_GPA_SCALE = 4.0


def predict_quality_degradation(kpis: dict) -> dict:
    """Heuristic quality-degradation predictor."""
    results = {}
    for sheet, vals in (kpis or {}).items():
        score = float(vals.get("precision_score", 0) or 0)
        rel = float(vals.get("composite_reliability_index", score) or score)
        pred_score = float(np.clip((score + rel) / 2.0, 0.0, 1.0))
        risk = float(np.clip(1.0 - rel, 0.0, 1.0))

        if risk > _OUTLOOK_HIGH_RISK:
            outlook = "Quality may degrade; recommend closer monitoring and data checks."
        elif pred_score >= _OUTLOOK_STABLE:
            outlook = "Quality expected to remain stable; maintain current practices."
        elif pred_score >= _OUTLOOK_MODERATE:
            outlook = "Moderate quality; watch for drift and consider minor improvements."
        else:
            outlook = "Below target quality; recommend intervention and data quality review."

        results[sheet] = {
            "predicted_quality_score": pred_score,
            "risk_probability": risk,
            "outlook": outlook,
            "static_feature_weights": _STATIC_WEIGHTS,
        }
    return results


def course_risk_probabilities(academic_analytics: dict) -> dict[str, dict]:
    """Heuristic course-risk scorer combining failure rate and GPA."""
    out = {}
    for sheet, data in (academic_analytics or {}).items():
        failure_list: list[dict] = data.get("top20_failure_rate") or []
        gpa_list: list[dict] = data.get("top20_gpa_per_course") or []
        all_courses: list[dict] = data.get("all_courses") or []
        course_risk: dict[str, float] = {}

        # Use all_courses when available (no Top 20 truncation)
        source = all_courses if all_courses else failure_list
        for item in source:
            course = item.get("course", "")
            if not course:
                continue
            fr = float(item.get("failure_rate") or 0) / 100.0
            high = 1.0 if item.get("high_risk") else 0.5
            # Also incorporate volatility: higher volatility → higher risk
            vol = float(item.get("volatility_index") or 0)
            risk = float(np.clip(
                fr * _COURSE_RISK_FAILURE_WEIGHT + high * _COURSE_RISK_HIGH_RISK_BONUS + vol * 0.1,
                0.0, 1.0,
            ))
            course_risk[course] = risk

        # GPA-based fallback for courses not in failure list
        for item in gpa_list:
            course = item.get("course", "")
            if not course or course in course_risk:
                continue
            gpa = float(item.get("gpa_estimate") or 2.5)
            vol = float(item.get("volatility_index") or 0)
            course_risk[course] = float(np.clip(1.0 - gpa / _GPA_SCALE + vol * 0.1, 0.0, 1.0))

        top_risk = sorted(course_risk.items(), key=lambda x: -x[1])[:10]
        out[sheet] = {"course_risk": course_risk, "top_risk_courses": top_risk}
    return out


def forecast_academic_trends(
    academic_analytics: dict[str, Any],
    n_forecast: int = 2,
) -> dict[str, Any]:
    """
    Linear OLS regression over sheets (treated as time points) to forecast
    program-level GPA and failure rate for the next n_forecast periods.

    Requires at least 2 sheets to fit a line.
    """
    sheets = list(academic_analytics.keys())
    n_sheets = len(sheets)

    if n_sheets < 2:
        return {
            "available": False,
            "reason": "At least 2 uploaded sheets are needed for trend forecasting.",
            "sheet_count": n_sheets,
        }

    gpa_means: list[float] = []
    fail_means: list[float] = []
    excellence_means: list[float] = []

    for sheet in sheets:
        data = academic_analytics[sheet]
        gpa_data = data.get("top20_gpa_per_course") or []
        fail_data = data.get("top20_failure_rate") or []
        excel_data = data.get("top20_excellence_rate") or []

        # Use all_courses when available for more accurate program-level means
        all_courses = data.get("all_courses") or []
        if all_courses:
            gpas = [c["gpa_estimate"] for c in all_courses if c.get("gpa_estimate") is not None]
            fails = [c["failure_rate"] for c in all_courses if c.get("failure_rate") is not None]
            excels = [c["excellence_rate"] for c in all_courses if c.get("excellence_rate") is not None]
        else:
            gpas = [r["gpa_estimate"] for r in gpa_data if r.get("gpa_estimate") is not None]
            fails = [r["failure_rate"] for r in fail_data if r.get("failure_rate") is not None]
            excels = [r["excellence_rate"] for r in excel_data if r.get("excellence_rate") is not None]

        gpa_means.append(float(np.mean(gpas)) if gpas else float("nan"))
        fail_means.append(float(np.mean(fails)) if fails else float("nan"))
        excellence_means.append(float(np.mean(excels)) if excels else float("nan"))

    def _ols_forecast(values: list[float], n_ahead: int) -> dict[str, Any] | None:
        arr = np.array(values, dtype=float)
        mask = ~np.isnan(arr)
        n_valid = int(mask.sum())
        if n_valid < 2:
            return None
        x = np.arange(len(arr))[mask]
        y = arr[mask]
        coeffs = np.polyfit(x, y, 1)  # [slope, intercept]
        slope, intercept = float(coeffs[0]), float(coeffs[1])
        y_pred_hist = np.polyval(coeffs, x)
        ss_res = float(np.sum((y - y_pred_hist) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r_sq = float(1 - ss_res / ss_tot) if ss_tot > 0 else None
        predicted = [round(float(np.polyval(coeffs, len(arr) + i)), 3) for i in range(n_ahead)]
        return {
            "slope": round(slope, 4),
            "intercept": round(intercept, 3),
            "r_squared": round(r_sq, 3) if r_sq is not None else None,
            "trend_direction": "improving" if slope > 0.005 else ("declining" if slope < -0.005 else "stable"),
            "predicted_next": predicted,
        }

    gpa_forecast = _ols_forecast(gpa_means, n_forecast)
    fail_forecast = _ols_forecast(fail_means, n_forecast)
    excellence_forecast = _ols_forecast(excellence_means, n_forecast)

    # Flip trend direction for failure rate (slope > 0 means worsening, not improving)
    if fail_forecast:
        s = fail_forecast["slope"]
        fail_forecast["trend_direction"] = "worsening" if s > 0.1 else ("improving" if s < -0.1 else "stable")

    return {
        "available": True,
        "sheet_count": n_sheets,
        "sheets_used": sheets,
        "historical_gpa_means": [round(v, 3) if not np.isnan(v) else None for v in gpa_means],
        "historical_fail_means": [round(v, 3) if not np.isnan(v) else None for v in fail_means],
        "historical_excellence_means": [round(v, 3) if not np.isnan(v) else None for v in excellence_means],
        "gpa_forecast": gpa_forecast,
        "failure_rate_forecast": fail_forecast,
        "excellence_rate_forecast": excellence_forecast,
        "n_forecast_periods": n_forecast,
    }
