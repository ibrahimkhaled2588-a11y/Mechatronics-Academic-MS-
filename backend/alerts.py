"""
Alert system: generates human-readable alert strings and detailed severity-leveled alerts.
"""
from __future__ import annotations

from config import get_alert_thresholds

_defaults = get_alert_thresholds()

_VOLATILITY_THRESHOLD = 0.8   # GPA volatility index above this is flagged
_EXCELLENCE_LOW_THRESHOLD = 10.0  # excellence rate below this triggers alert
_GPA_CRITICAL_THRESHOLD = 2.0    # GPA below this is critical


def generate_alerts(
    kpis: dict,
    predictions: dict,
    thresholds: dict | None = None,
    academic_analytics: dict | None = None,
    course_risk: dict | None = None,
    schema_changes: dict | None = None,
) -> list[str]:
    """Return human-readable alert strings (backward-compatible)."""
    return [a["message"] for a in generate_alerts_detailed(
        kpis, predictions, thresholds, academic_analytics, course_risk, schema_changes
    )]


def generate_alerts_detailed(
    kpis: dict,
    predictions: dict,
    thresholds: dict | None = None,
    academic_analytics: dict | None = None,
    course_risk: dict | None = None,
    schema_changes: dict | None = None,
) -> list[dict]:
    """
    Return list of alert dicts with severity, category, message, metric, value.
    severity: "critical" | "warning" | "info"
    """
    t = thresholds or {}
    dup_th = float(t.get("duplicate_rate", _defaults.duplicate_rate))
    anomaly_th = float(t.get("anomaly_density", _defaults.anomaly_density))
    quality_th = float(t.get("quality_score", _defaults.quality_score))
    drift_th = float(t.get("drift_score", _defaults.drift_score))
    risk_th = float(t.get("predicted_risk_pct", _defaults.predicted_risk_pct))
    failure_th = float(t.get("failure_rate", _defaults.failure_rate))

    alerts: list[dict] = []

    def _add(severity: str, category: str, message: str, metric: str = "", value: float | None = None) -> None:
        alerts.append({
            "severity": severity,
            "category": category,
            "message": message,
            "metric": metric,
            "value": value,
        })

    # --- Data quality alerts per sheet ---
    for sheet, vals in (kpis or {}).items():
        pred = (predictions or {}).get(sheet, {})
        dr = vals.get("duplicate_rate") or 0
        if dr > dup_th:
            _add("warning", "data_quality",
                 f"High duplicate rate ({dr:.1f}%) in sheet '{sheet}'",
                 "duplicate_rate", dr)

        ad = vals.get("anomaly_density") or 0
        if ad > anomaly_th:
            _add("warning", "data_quality",
                 f"High anomaly density ({ad*100:.1f}% of numeric cells) in sheet '{sheet}'",
                 "anomaly_density", ad)

        rel = vals.get("composite_reliability_index") or 1.0
        if rel < quality_th:
            sev = "critical" if rel < 0.6 else "warning"
            _add(sev, "data_quality",
                 f"Low reliability index ({rel:.2f}) in sheet '{sheet}' — review data quality",
                 "composite_reliability_index", rel)

        drift = vals.get("data_drift_score") or 0
        if drift > drift_th:
            _add("warning", "drift",
                 f"Data distribution drift detected in sheet '{sheet}' (PSI={drift:.3f})",
                 "data_drift_score", drift)

        pred_quality = pred.get("predicted_quality_score", 1.0) or 1.0
        if pred_quality < quality_th:
            sev = "critical" if pred_quality < 0.6 else "warning"
            _add(sev, "prediction",
                 f"Predicted quality degradation for sheet '{sheet}' (score={pred_quality:.2f})",
                 "predicted_quality_score", pred_quality)

        risk_pct = float(pred.get("risk_probability") or 0) * 100
        if risk_pct > risk_th:
            _add("critical" if risk_pct > 70 else "warning", "prediction",
                 f"High degradation risk ({risk_pct:.0f}%) predicted for sheet '{sheet}'",
                 "risk_probability", risk_pct)

    # --- Academic performance alerts per course ---
    for sheet, data in (academic_analytics or {}).items():
        # Use all_courses when available; fall back to top20_failure_rate
        all_courses = data.get("all_courses") or []
        failure_list = data.get("top20_failure_rate") or []
        gpa_list = {r["course"]: r for r in (data.get("top20_gpa_per_course") or [])}
        excel_list = {r["course"]: r for r in (data.get("top20_excellence_rate") or [])}

        source = all_courses if all_courses else failure_list

        for item in source:
            course = item.get("course", "")
            fr = item.get("failure_rate") or 0
            gpa = item.get("gpa_estimate") or gpa_list.get(course, {}).get("gpa_estimate")
            exc = item.get("excellence_rate") or excel_list.get(course, {}).get("excellence_rate")
            vol = item.get("volatility_index") or gpa_list.get(course, {}).get("volatility_index") or 0
            enr = item.get("enrollment") or 0
            spike = item.get("abnormal_spike", False)

            if fr > failure_th:
                sev = "critical" if fr > 40 else "warning"
                _add(sev, "academic",
                     f"High failure rate {fr:.1f}% in course '{course}' (sheet '{sheet}')",
                     "failure_rate", fr)

            if gpa is not None and gpa < _GPA_CRITICAL_THRESHOLD:
                _add("critical", "academic",
                     f"Critical GPA {gpa:.2f} in course '{course}' (sheet '{sheet}')",
                     "gpa_estimate", gpa)
            elif gpa is not None and gpa < 2.5:
                _add("warning", "academic",
                     f"Low GPA {gpa:.2f} in course '{course}' (sheet '{sheet}')",
                     "gpa_estimate", gpa)

            if exc is not None and exc < _EXCELLENCE_LOW_THRESHOLD and enr > 10:
                _add("info", "academic",
                     f"Very low excellence rate {exc:.1f}% in course '{course}' (sheet '{sheet}')",
                     "excellence_rate", exc)

            if vol > _VOLATILITY_THRESHOLD:
                _add("warning", "academic",
                     f"High GPA volatility (σ={vol:.2f}) in course '{course}' — inconsistent outcomes",
                     "volatility_index", vol)

            if spike and enr > 0:
                _add("info", "enrollment",
                     f"Abnormal enrollment spike in course '{course}' ({enr} students, sheet '{sheet}')",
                     "enrollment", enr)

    # --- Schema change alerts ---
    for sheet, changes in (schema_changes or {}).items():
        if changes:
            summary = "; ".join(changes[:3])
            _add("info", "schema",
                 f"Schema change detected in sheet '{sheet}': {summary}",
                 "schema_change")

    # Deduplicate by message (same message from multiple sources)
    seen: set[str] = set()
    unique: list[dict] = []
    for a in alerts:
        if a["message"] not in seen:
            seen.add(a["message"])
            unique.append(a)

    # Sort: critical first, then warning, then info
    order = {"critical": 0, "warning": 1, "info": 2}
    unique.sort(key=lambda a: order.get(a["severity"], 3))
    return unique
