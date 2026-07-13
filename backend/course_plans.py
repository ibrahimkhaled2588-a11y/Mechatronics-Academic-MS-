"""
Course-level action plans with data-driven, metric-specific recommendations.
Actions reference actual numbers (failure rate, GPA, enrollment) for specificity.
"""
from __future__ import annotations

from typing import Any


def _risk_level(risk_pct: float) -> str:
    if risk_pct >= 60:
        return "high"
    if risk_pct >= 35:
        return "medium"
    return "low"


def _trend_label(quality_score: float, risk_prob: float) -> str:
    if risk_prob > 0.5:
        return "down"
    if quality_score >= 0.85:
        return "stable"
    if quality_score >= 0.7:
        return "watch"
    return "down"


def _build_actions(
    course: str,
    fr: float | None,
    gpa: float | None,
    excellence: float,
    total: int,
    risk_pct: float,
    vol: float,
    fr_ci_lo: float | None,
    fr_ci_hi: float | None,
) -> list[str]:
    actions: list[str]= []

    if fr is not None:
        if fr > 40:
            ci_note = f" (95% CI: {fr_ci_lo:.1f}%–{fr_ci_hi:.1f}%)" if fr_ci_lo is not None else ""
            actions.append(
                f"Critical failure rate {fr:.1f}%{ci_note}: immediately schedule intensive remedial sessions "
                f"and alert the department head for '{course}'."
            )
        elif fr > 30:
            ci_note = f" (95% CI: {fr_ci_lo:.1f}%–{fr_ci_hi:.1f}%)" if fr_ci_lo is not None else ""
            actions.append(
                f"High failure rate {fr:.1f}%{ci_note}: schedule weekly review sessions "
                "and review exam alignment with course objectives."
            )
        elif fr > 20:
            actions.append(
                f"Elevated failure rate {fr:.1f}%: identify struggling students by Week 4 "
                "and offer targeted tutoring before mid-semester."
            )

    if gpa is not None:
        if gpa < 2.0:
            actions.append(
                f"Critical GPA {gpa:.2f}/4.00: refer to curriculum committee for full review "
                "of content, prerequisites, and assessment design."
            )
        elif gpa < 2.5:
            actions.append(
                f"Low GPA {gpa:.2f}/4.00: review teaching methods and provide supplementary "
                "learning materials or worked examples."
            )

    if vol > 0.8:
        actions.append(
            f"High GPA volatility (σ={vol:.2f}): inconsistent outcomes suggest assessment "
            "fairness issues — review grading rubrics and standardize scoring."
        )

    if excellence < 10 and total > 10:
        actions.append(
            f"Very low excellence rate {excellence:.1f}%: consider introducing challenge problems, "
            "honors components, or differentiated instruction to stretch high achievers."
        )
    elif excellence < 20 and total > 15:
        actions.append(
            f"Below-average excellence rate {excellence:.1f}%: provide enrichment activities "
            "and recognize top performers to motivate higher achievement."
        )

    if risk_pct >= 70:
        actions.append(
            f"Very high predicted risk score {risk_pct:.0f}%: assign an experienced instructor "
            "and request a department-level structured improvement plan."
        )
    elif risk_pct >= 50:
        actions.append(
            f"Elevated risk score {risk_pct:.0f}%: monitor attendance and performance weekly; "
            "escalate if failure rate rises mid-semester."
        )

    if not actions:
        actions.append(
            "Performance within acceptable range: maintain current approach "
            "and continue routine monitoring."
        )

    return actions[:5]


def generate_course_plans(
    academic_analytics: dict,
    course_risk: dict,
    predictions: dict,
) -> dict[str, list[dict[str, Any]]]:
    out = {}
    for sheet, data in academic_analytics.items():
        failure_list = data.get("top20_failure_rate", [])
        gpa_list = {x["course"]: x for x in data.get("top20_gpa_per_course", [])}
        excellence_list = {x["course"]: x for x in data.get("top20_excellence_rate", [])}
        all_courses = {x["course"]: x for x in (data.get("all_courses") or [])}
        risk_data = course_risk.get(sheet, {})
        course_risks = risk_data.get("course_risk", {})
        pred = predictions.get(sheet, {})
        quality_score = pred.get("predicted_quality_score", 0.8) or 0.8
        risk_prob = pred.get("risk_probability", 0.2) or 0.2

        plans = []
        seen: set[str] = set()

        # Priority source: all_courses (no Top 20 truncation); fall back to top20 failure list
        source_courses = list(all_courses.values()) if all_courses else failure_list

        # Sort by risk descending
        source_courses = sorted(
            source_courses,
            key=lambda c: (course_risks.get(c.get("course", ""), 0) or 0),
            reverse=True,
        )

        for item in source_courses[:30]:
            course = item.get("course", "")
            if not course or course in seen:
                continue
            seen.add(course)
            fr = item.get("failure_rate")
            gpa_info = gpa_list.get(course) or item
            excel_info = excellence_list.get(course) or item
            full_info = all_courses.get(course) or item

            gpa = gpa_info.get("gpa_estimate")
            excel = excel_info.get("excellence_rate", 0) or full_info.get("excellence_rate", 0)
            total = item.get("enrollment") or item.get("total") or 0
            risk_pct = (course_risks.get(course, 0) or 0) * 100
            vol = gpa_info.get("volatility_index") or full_info.get("volatility_index") or 0
            fr_lo = full_info.get("failure_rate_ci_lower")
            fr_hi = full_info.get("failure_rate_ci_upper")

            actions = _build_actions(course, fr, gpa, excel, total, risk_pct, vol, fr_lo, fr_hi)
            trend = _trend_label(quality_score, risk_prob)

            plans.append({
                "course": course,
                "risk_level": _risk_level(risk_pct),
                "risk_percent": round(risk_pct, 1),
                "failure_rate": fr,
                "failure_rate_ci_lower": fr_lo,
                "failure_rate_ci_upper": fr_hi,
                "gpa_estimate": gpa,
                "excellence_rate": excel,
                "volatility_index": vol,
                "predicted_trend": trend,
                "action_plan": actions,
            })

        # Fill remaining from GPA list if not yet covered
        for item in data.get("top20_gpa_per_course", [])[:15]:
            course = item.get("course", "")
            if not course or course in seen:
                continue
            seen.add(course)
            gpa = item.get("gpa_estimate", 2.5)
            risk_pct = (course_risks.get(course, 0) or 0) * 100
            excel = (excellence_list.get(course) or {}).get("excellence_rate", 0)
            vol = item.get("volatility_index") or 0
            actions = _build_actions(course, None, gpa, excel, 0, risk_pct, vol, None, None)
            trend = _trend_label(quality_score, risk_prob)
            plans.append({
                "course": course,
                "risk_level": _risk_level(risk_pct),
                "risk_percent": round(risk_pct, 1),
                "failure_rate": None,
                "failure_rate_ci_lower": None,
                "failure_rate_ci_upper": None,
                "gpa_estimate": gpa,
                "excellence_rate": excel,
                "volatility_index": vol,
                "predicted_trend": trend,
                "action_plan": actions,
            })

        out[sheet] = plans[:30]
    return out
