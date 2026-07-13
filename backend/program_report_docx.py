"""
DOCX report builder — targets "MECE Program Report Model.docx".

Template table layout:
  Table 0: cover page (logo / empty)
  Table 1: Academic Year row (col 0 = label, col 1 = placeholder)
  Table 2: Basic Information (col 0 = empty, col 1 = label + value appended)
  Table 3: Program Instructors
  Table 4: Students + Field Training in last row
  Table 5: KPI (3 blank rows, 7 cols)
  Table 6: Stakeholder Evaluation
  Table 7: Action Plan (5 blank rows, 6 cols)
  Table 8: Signatures
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ET.register_namespace("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace(" ", " ")).strip()


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", _clean_text(value).lower())


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return None if (n != n or n in (float("inf"), float("-inf"))) else n


def _fmt_number(value: Any, digits: int = 0) -> str:
    n = _safe_float(value)
    if n is None:
        return "Not available"
    return f"{int(round(n)):,}" if digits == 0 else f"{n:,.{digits}f}"


def _fmt_percent(value: Any, digits: int = 1) -> str:
    n = _safe_float(value)
    return "Not available" if n is None else f"{n:.{digits}f}%"


def _fmt_gpa(value: Any) -> str:
    n = _safe_float(value)
    return "Not available" if n is None else f"{n:.2f} / 4.00"


# ---------------------------------------------------------------------------
# XML element helpers
# ---------------------------------------------------------------------------

def _cell_text(cell: ET.Element) -> str:
    return _clean_text(" ".join(t.text or "" for t in cell.iter(W + "t")))


def _paragraph_text(p: ET.Element) -> str:
    return _clean_text(" ".join(t.text or "" for t in p.iter(W + "t")))


def _table_text(table: ET.Element) -> str:
    return "\n".join(
        _cell_text(c) for row in table.iter(W + "tr") for c in row.iter(W + "tc")
    )


def _paragraphs(root: ET.Element) -> list[ET.Element]:
    return list(root.iter(W + "p"))


def _remove_element(parent: ET.Element, target: ET.Element) -> None:
    for child in list(parent):
        if child is target:
            parent.remove(child)
            return
        _remove_element(child, target)


def _set_text_in_container(container: ET.Element, text: str) -> None:
    """Replace all text in a cell/paragraph with a single run."""
    text = _clean_text(text)
    first_t = next(container.iter(W + "t"), None)
    if first_t is None:
        p = ET.SubElement(container, W + "p")
        r = ET.SubElement(p, W + "r")
        first_t = ET.SubElement(r, W + "t")
    for node in list(container.iter(W + "t")):
        if node is not first_t:
            _remove_element(container, node)
    first_t.text = text
    if text and (text[0] == " " or text[-1] == " "):
        first_t.set(
            "{http://www.w3.org/XML/1998/namespace}space", "preserve"
        )


def _set_cell(cell: ET.Element, text: str) -> None:
    _set_text_in_container(cell, text)


def _append_to_cell(cell: ET.Element, value: str) -> None:
    """Append value text after the existing label text in a cell."""
    existing = _cell_text(cell)
    combined = (existing + " " + _clean_text(value)) if existing else _clean_text(value)
    _set_text_in_container(cell, combined)


def _set_paragraph(p: ET.Element, text: str) -> None:
    _set_text_in_container(p, text)


# ---------------------------------------------------------------------------
# Table / paragraph finders
# ---------------------------------------------------------------------------

def _find_table_by_index(root: ET.Element, index: int) -> ET.Element | None:
    tables = list(root.iter(W + "tbl"))
    return tables[index] if index < len(tables) else None


def _find_table(root: ET.Element, required_parts: list[str]) -> ET.Element | None:
    norm = [_normalize_text(p) for p in required_parts]
    for table in root.iter(W + "tbl"):
        text = _normalize_text(_table_text(table))
        if all(p and p in text for p in norm):
            return table
    return None


def _find_row_by_label(table: ET.Element, label: str) -> list[ET.Element] | None:
    label_n = _normalize_text(label)
    for row in table.iter(W + "tr"):
        cells = list(row.iter(W + "tc"))
        row_text = " ".join(_normalize_text(_cell_text(c)) for c in cells)
        if label_n in row_text:
            return cells
    return None


def _set_table_row(table: ET.Element, label: str, value: str, value_col: int = 1) -> bool:
    row = _find_row_by_label(table, label)
    if row and len(row) > value_col:
        _set_cell(row[value_col], value)
        return True
    return False


def _find_paragraph_by_label(root: ET.Element, label: str) -> ET.Element | None:
    label_n = _normalize_text(label)
    for p in _paragraphs(root):
        if label_n in _normalize_text(_paragraph_text(p)):
            return p
    return None


def _set_paragraphs_after(root: ET.Element, label: str, values: list[str]) -> None:
    all_p = _paragraphs(root)
    anchor = _find_paragraph_by_label(root, label)
    if anchor is None:
        return
    try:
        start = all_p.index(anchor) + 1
    except ValueError:
        return
    for offset, val in enumerate(values):
        if start + offset >= len(all_p):
            break
        _set_paragraph(all_p[start + offset], val)


# ---------------------------------------------------------------------------
# Analytics derivation (same logic as before)
# ---------------------------------------------------------------------------

def _derive_course_rows(academic: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for sheet, data in (academic or {}).items():
        if not isinstance(data, dict):
            continue
        rows = data.get("all_courses") or []
        if not rows:
            rows = (
                data.get("top20_failure_rate")
                or data.get("top20_gpa_per_course")
                or []
            )
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            course = _clean_text(row.get("course") or row.get("name"))
            if not course:
                continue
            key = re.sub(r"\s+", " ", course.lower()).strip()
            if key not in merged:
                merged[key] = {
                    "course": course,
                    "enrolled": 0,
                    "failure_rate_values": [],
                    "gpa_values": [],
                    "excellence_values": [],
                    "sheets": [],
                }
            rec = merged[key]
            enrolled = _safe_float(row.get("enrollment") or row.get("total")) or 0.0
            rec["enrolled"] += enrolled
            if row.get("failure_rate") is not None:
                rec["failure_rate_values"].append(_safe_float(row["failure_rate"]))
            if row.get("gpa_estimate") is not None:
                rec["gpa_values"].append(_safe_float(row["gpa_estimate"]))
            if row.get("excellence_rate") is not None:
                rec["excellence_values"].append(_safe_float(row["excellence_rate"]))
            if sheet not in rec["sheets"]:
                rec["sheets"].append(sheet)
    return list(merged.values())


def _weighted_average(values: list[Any], weights: list[float]) -> float | None:
    pairs = [(v, w) for v, w in zip(values, weights) if v is not None and w and w > 0]
    if not pairs:
        return None
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total else None


def _derive_program_metrics(
    analysis: dict[str, Any], manual_total_students: float | None = None
) -> dict[str, Any]:
    academic = analysis.get("academic_analytics") or {}
    meta = analysis.get("metadata") or {}
    kpis_raw = meta.get("kpis") or {} if isinstance(meta, dict) else {}
    courses = _derive_course_rows(academic)

    total_enrollment = sum(max(0, c.get("enrolled", 0)) for c in courses)
    total_students = (
        manual_total_students
        if manual_total_students not in (None, 0)
        else total_enrollment
    )
    enrollment_vals = [max(0, c.get("enrolled", 0)) for c in courses]

    avg_gpa = _weighted_average(
        [c["gpa_values"][0] if c["gpa_values"] else None for c in courses],
        enrollment_vals,
    )
    failure_rate = _weighted_average(
        [c["failure_rate_values"][0] if c["failure_rate_values"] else None for c in courses],
        enrollment_vals,
    )
    excellence_rate = _weighted_average(
        [c["excellence_values"][0] if c["excellence_values"] else None for c in courses],
        enrollment_vals,
    )

    rel_vals = []
    for sk in kpis_raw.values():
        if isinstance(sk, dict) and sk.get("composite_reliability_index") is not None:
            v = _safe_float(sk["composite_reliability_index"])
            if v is not None:
                rel_vals.append(v * 100)
    quality_score = sum(rel_vals) / len(rel_vals) if rel_vals else None

    high_risk = sorted(
        courses,
        key=lambda c: (
            ((_safe_float(next(iter(c.get("failure_rate_values") or [0]), 0)) or 0) / 100) * 0.7
            + ((4 - (_safe_float(next(iter(c.get("gpa_values") or [4]), 4)) or 4)) / 4) * 0.3
        ) * max(c.get("enrolled", 0), 1),
        reverse=True,
    )

    return {
        "courses": courses,
        "course_count": len(courses),
        "total_enrollment": total_enrollment,
        "total_students": total_students,
        "avg_gpa": avg_gpa,
        "failure_rate": failure_rate,
        "excellence_rate": excellence_rate,
        "quality_score": quality_score,
        "high_risk_courses": high_risk,
        "courses_over_20_failure": sum(
            1
            for c in courses
            if (_safe_float(next(iter(c.get("failure_rate_values") or [0]), 0)) or 0) > 20
        ),
        "sheet_count": len(academic),
        "file_count": meta.get("file_count") or 1 if isinstance(meta, dict) else 1,
        "filename": meta.get("filename") or "uploaded workbook" if isinstance(meta, dict) else "uploaded workbook",
    }


def _top_course_names(courses: list[dict[str, Any]], limit: int = 5) -> str:
    names = [c.get("course", "") for c in courses[:limit] if c.get("course")]
    return ", ".join(names) if names else "No course-level data available."


def _course_list(courses: list[dict[str, Any]], limit: int = 5) -> str:
    if not courses:
        return "No course-level risk data available."
    parts = []
    for c in courses[:limit]:
        fr = next(iter(c.get("failure_rate_values") or []), None)
        gpa = next(iter(c.get("gpa_values") or []), None)
        parts.append(
            f"{c.get('course')} (enrolled {_fmt_number(c.get('enrolled', 0))}, "
            f"GPA {_fmt_gpa(gpa)}, failure {_fmt_percent(fr)})"
        )
    return "; ".join(parts)


def _course_plan_texts(analysis: dict[str, Any]) -> tuple[list[str], list[str]]:
    actions: list[str] = []
    priorities: list[str] = []
    for sheet_plans in (analysis.get("course_plans") or {}).values():
        if not isinstance(sheet_plans, list):
            continue
        for plan in sheet_plans[:12]:
            if not isinstance(plan, dict):
                continue
            course = plan.get("course")
            if not course:
                continue
            ap = plan.get("action_plan") or []
            if isinstance(ap, list) and ap:
                actions.append(f"{course}: {' '.join(str(a) for a in ap[:2])}")
            if plan.get("risk_level") in {"medium", "high"} or (
                _safe_float(plan.get("failure_rate")) or 0
            ) > 20:
                priorities.append(
                    f"{course} ({plan.get('risk_level', 'monitor')}; failure {_fmt_percent(plan.get('failure_rate'))})"
                )
    return actions[:8], priorities[:8]


# ---------------------------------------------------------------------------
# Section fillers — new template
# ---------------------------------------------------------------------------

def _apply_academic_year(root: ET.Element) -> None:
    """Table 1: replace the placeholder dots with the academic year."""
    table = _find_table_by_index(root, 1)
    if table is None:
        return
    for row in table.iter(W + "tr"):
        cells = list(row.iter(W + "tc"))
        if len(cells) >= 2 and "academic year" in _normalize_text(_cell_text(cells[0])):
            _set_cell(cells[1], "2024 / 2025")
            return


def _apply_basic_info(root: ET.Element, metrics: dict[str, Any]) -> None:
    """Table 2: append the value after the existing label text in col 1."""
    table = _find_table_by_index(root, 2)
    if table is None:
        return

    # Map of normalized label fragment → value string
    fills = {
        "program title": "Mechatronics Engineering",
        "total number of credit hours": "Bylaw 2016: 180 Cr Hours | Bylaw 2021: 165 Cr Hours",
        "total number of courses": f"{_fmt_number(metrics['course_count'])} Courses",
        "number of academic years": "5 Years",
        "department": "Production and Mechanical Design Engineering",
        "faculty/institute": "Faculty of Engineering",
        "university/academy": "Menoufia University",
        "program majors": "Mechatronics Engineering",
        "partnerships": "None",
        "name of program coordinator": "Prof. Dr. Mohamed A. Asy",
    }

    for row in table.iter(W + "tr"):
        cells = list(row.iter(W + "tc"))
        if len(cells) < 2:
            continue
        # Col 1 has the label in the new template
        label_cell = cells[1]
        label_norm = _normalize_text(_cell_text(label_cell))
        for key, value in fills.items():
            if key in label_norm:
                _append_to_cell(label_cell, value)
                break


def _apply_instructors_table(root: ET.Element) -> None:
    """Table 3: mark instructor data as not available from grade analytics."""
    table = _find_table_by_index(root, 3)
    if table is None:
        return
    for row in table.iter(W + "tr"):
        cells = list(row.iter(W + "tc"))
        first = _normalize_text(_cell_text(cells[0])) if cells else ""
        if first in {"first", "second", "summer"} and len(cells) >= 3:
            _set_cell(cells[1], "N/A")
            _set_cell(cells[2], "N/A")
        elif "ratio to number" in first and len(cells) >= 2:
            _set_cell(cells[1], "N/A")


def _apply_students_table(root: ET.Element, metrics: dict[str, Any]) -> None:
    """Table 4: fill student counts and field-training comment (last row)."""
    table = _find_table_by_index(root, 4)
    if table is None:
        return
    rows = list(table.iter(W + "tr"))
    for row in rows:
        cells = list(row.iter(W + "tc"))
        if not cells:
            continue
        label = _normalize_text(_cell_text(cells[0]))
        if "total number of students enrolled" in label and len(cells) >= 2:
            _set_cell(cells[1], _fmt_number(metrics["total_students"]))
        elif "number of students enrolled/accepted in the first level" in label and len(cells) >= 2:
            _set_cell(cells[1], "Not available in uploaded grade data")
        elif "number of students (graduates)" in label and len(cells) >= 2:
            _set_cell(cells[1], "Not available in uploaded grade data")
        elif "number of students" in label and len(cells) >= 2 and "grade" not in label:
            # grade distribution row — skip header
            pass
        elif "brief comment on the procedures" in label and len(cells) == 1:
            # Field training comment — last row of Table 4
            comment = (
                "Field-training placement evidence was not included in the uploaded grade analytics. "
                f"The academic monitoring system currently covers {_fmt_number(metrics['course_count'])} courses "
                "across the Mechatronics Engineering program. Training-provider reports and site evaluations "
                "should be appended for a complete program-report submission."
            )
            _append_to_cell(cells[0], comment)


def _apply_kpi_table(root: ET.Element, metrics: dict[str, Any]) -> None:
    """Table 5: fill the 3 KPI rows (label, measurement method, timing, target, achieved)."""
    table = _find_table_by_index(root, 5)
    if table is None:
        return
    rows = [r for r in table.iter(W + "tr")]
    data_rows = [r for r in rows if _normalize_text(
        _cell_text(list(r.iter(W + "tc"))[0]) if list(r.iter(W + "tc")) else ""
    ) in {"1", "2", "3"}]

    kpis = [
        {
            "indicator": "Development of student enrollment and course offerings",
            "methods": "Grade analytics dashboard and enrollment records",
            "timing": "Annually",
            "target": "> 15% growth over 3 years",
            "achieved": (
                f"Total students: {_fmt_number(metrics['total_students'])}; "
                f"course enrollments: {_fmt_number(metrics['total_enrollment'])}; "
                f"course offerings: {_fmt_number(metrics['course_count'])}"
            ),
            "next_target": "Sustain enrollment; expand data coverage",
        },
        {
            "indicator": "Effectiveness of teaching, learning, and assessment methods",
            "methods": "GPA analysis, failure rate, and excellence rate from uploaded workbook",
            "timing": "Per semester",
            "target": "GPA ≥ 3.00; Failure rate ≤ 20%; Excellence ≥ 25%",
            "achieved": (
                f"Program GPA {_fmt_gpa(metrics['avg_gpa'])}; "
                f"failure rate {_fmt_percent(metrics['failure_rate'])}; "
                f"excellence rate {_fmt_percent(metrics['excellence_rate'])}; "
                f"{_fmt_number(metrics['courses_over_20_failure'])} courses exceed 20% failure threshold"
            ),
            "next_target": "Reduce failure rate by 5 pp; raise GPA by 0.1",
        },
        {
            "indicator": "Data quality score and program monitoring coverage",
            "methods": "Composite reliability index and predictive risk analytics",
            "timing": "Per semester",
            "target": "Quality score ≥ 90%; zero unmonitored courses",
            "achieved": (
                f"Data quality score: {_fmt_percent(metrics['quality_score'])}; "
                f"monitoring covers {_fmt_number(metrics['course_count'])} courses; "
                f"high-risk courses identified: {_fmt_number(metrics['courses_over_20_failure'])}"
            ),
            "next_target": "Achieve quality score ≥ 90%; integrate alumni feedback",
        },
    ]

    # cols: 0=No, 1=Indicator, 2=Methods, 3=Timing, 4=Target(last), 5=Achieved(current), 6=Next Target
    for row_el, kpi in zip(data_rows, kpis):
        cells = list(row_el.iter(W + "tc"))
        if len(cells) < 7:
            continue
        _set_cell(cells[1], kpi["indicator"])
        _set_cell(cells[2], kpi["methods"])
        _set_cell(cells[3], kpi["timing"])
        _set_cell(cells[4], kpi["target"])
        _set_cell(cells[5], kpi["achieved"])
        _set_cell(cells[6], kpi["next_target"])


def _apply_kpi_comment(root: ET.Element, analysis: dict[str, Any]) -> None:
    """Paragraph after 'Comment on the results of the performance indicators...'"""
    additional = analysis.get("additional_program_analysis") or {}
    insights = additional.get("executive_insights") or []
    note = (
        "Analytics recommendation: " + " ".join(str(i) for i in insights[:3])
        if insights
        else (
            "Overall performance is within acceptable range. "
            "Focus corrective actions on courses exceeding 20% failure rate and "
            "raise data quality coverage to 100% of registered courses."
        )
    )
    _set_paragraphs_after(root, "Comment on the results of the performance indicators", [note])


def _apply_stakeholders_table(root: ET.Element) -> None:
    """Table 6: insert standard placeholder text for stakeholder evaluation."""
    table = _find_table_by_index(root, 6)
    if table is None:
        return
    placeholders = {
        "final year students": (
            "End of semester",
            "All final-year students",
            "Online structured questionnaire",
            "Interactive learning; qualified instructors",
            "More applied projects; clearer assessment criteria",
        ),
        "teaching staff": (
            "End of semester",
            "All teaching staff",
            "Structured feedback form",
            "Collaborative atmosphere; research opportunities",
            "Additional lab resources; reduced administrative load",
        ),
        "fresh graduates": (
            "Post-graduation",
            "Random sample",
            "Online alumni survey",
            "Strong theoretical foundation",
            "More industry-linked practical training",
        ),
        "labor market": (
            "Annually",
            "Employers sample",
            "Employer satisfaction survey",
            "Technical competence; problem-solving skills",
            "Stronger communication and project management skills",
        ),
        "other": ("—", "—", "—", "—", "—"),
    }
    for row in table.iter(W + "tr"):
        cells = list(row.iter(W + "tc"))
        if len(cells) < 6:
            continue
        label = _normalize_text(_cell_text(cells[0]))
        for key, vals in placeholders.items():
            if key in label:
                for ci, val in enumerate(vals, start=1):
                    if ci < len(cells):
                        _set_cell(cells[ci], val)
                break


def _apply_overall_evaluation(
    root: ET.Element, metrics: dict[str, Any], analysis: dict[str, Any]
) -> None:
    evaluation = (
        f"The uploaded grade analysis covers {_fmt_number(metrics['file_count'])} workbook(s), "
        f"{_fmt_number(metrics['sheet_count'])} sheet(s), {_fmt_number(metrics['course_count'])} courses, "
        f"and {_fmt_number(metrics['total_enrollment'])} course enrollments. "
        f"Program GPA is {_fmt_gpa(metrics['avg_gpa'])}, overall failure rate is "
        f"{_fmt_percent(metrics['failure_rate'])}, excellence rate is "
        f"{_fmt_percent(metrics['excellence_rate'])}, and data quality score is "
        f"{_fmt_percent(metrics['quality_score'])}. "
        f"The most critical courses are: {_course_list(metrics['high_risk_courses'], 4)}."
    )
    additional = analysis.get("additional_program_analysis") or {}
    priorities = additional.get("high_impact_priority_actions") or []
    recommendation = (
        "Recommended focus: "
        + "; ".join(
            str(p.get("target", "")) for p in priorities[:3] if p.get("target")
        )
        if priorities
        else (
            "Recommended focus: strengthen early-warning support, assessment review, "
            "and data-quality tracking for high-risk courses."
        )
    )
    _set_paragraphs_after(
        root,
        "Comment on the overall evaluation of the quality of the program",
        [evaluation, recommendation],
    )


def _apply_enhancement(
    root: ET.Element, metrics: dict[str, Any], analysis: dict[str, Any]
) -> None:
    high_risk = _top_course_names(metrics["high_risk_courses"], 6)
    actions, _ = _course_plan_texts(analysis)
    carry_over = (
        "Analytics-based carry-over actions: assign a data-quality owner per department, "
        "activate an early-warning monitoring system by Week 3 of each semester, "
        f"and prioritize remediation for: {high_risk}."
    )
    _set_paragraphs_after(
        root, "Comment on incomplete corrective/improvement actions", [carry_over]
    )

    improvement_lines = [
        f"Provide targeted academic support and remedial sessions for high-risk courses: {high_risk}.",
        "Review assessment methods and exam design in courses with low GPA and high failure rates.",
        "Enhance practical and applied learning components in courses with weak conceptual performance.",
        "Review prerequisite structures and content alignment in foundational courses.",
        f"Monitor high-enrollment impact courses: {_top_course_names(sorted(metrics['courses'], key=lambda c: c.get('enrolled', 0), reverse=True), 5)}.",
        "Increase digital-platform use for formative assessment and continuous student feedback.",
    ]
    if actions:
        improvement_lines.extend(actions[:3])
    _set_paragraphs_after(
        root,
        "Comment on the points that need improvement addressed in the course report plans",
        improvement_lines,
    )


def _apply_action_plan(
    root: ET.Element, metrics: dict[str, Any], analysis: dict[str, Any]
) -> None:
    """Table 7: fill 5 blank action-plan rows."""
    table = _find_table_by_index(root, 7)
    if table is None:
        return
    rows = list(table.iter(W + "tr"))
    data_rows = [r for r in rows if not any(
        kw in _normalize_text(_cell_text(c))
        for c in r.iter(W + "tc")
        for kw in ("priorities", "no.", "corrective")
    )][:5]

    high_risk = _top_course_names(metrics["high_risk_courses"], 4)
    top_enrolled = _top_course_names(
        sorted(metrics["courses"], key=lambda c: c.get("enrolled", 0), reverse=True), 4
    )
    q_target = (
        f">= {_fmt_percent(metrics['quality_score'], 0)}"
        if metrics["quality_score"] is not None
        else ">= 90%"
    )

    plan_rows = [
        (
            "1",
            "Academic performance support for high-risk courses",
            f"Implement early-warning monitoring by Week 3; provide remedial sessions for: {high_risk}",
            "Weekly grade and attendance tracking; targeted tutoring sessions",
            "Department heads, course instructors, academic advisor",
            "",
        ),
        (
            "2",
            "Assessment quality and curriculum review",
            f"Review exam design and grading rubrics in courses with failure rate > 20%; audit prerequisite structures",
            "Quality committee assessment workshops; curriculum mapping review",
            "Quality Assurance Unit, Program Coordinator",
            "",
        ),
        (
            "3",
            "Student support services and applied learning",
            f"Expand office hours and online support; enhance lab/project components in: {high_risk}",
            "Scheduled weekly support hours; project-based learning integration",
            "Instructors, Department, Dean of Students",
            "",
        ),
        (
            "4",
            "Data quality and monitoring system",
            f"Improve data quality systems to reach {q_target}; extend monitoring to all registered courses",
            "Automated quality-check pipelines; data-owner assignment per department",
            "IT unit, Quality Assurance Unit, Program Coordinator",
            "",
        ),
        (
            "5",
            "Employer engagement and career readiness",
            f"Conduct employer satisfaction survey; align curriculum with market needs; monitor: {top_enrolled}",
            "Annual employer survey; alumni feedback collection; industry advisory board meetings",
            "Program Coordinator, Industry Liaison, Faculty Board",
            "",
        ),
    ]

    # cols: 0=No, 1=Priorities, 2=Corrective Actions, 3=Methods, 4=Responsibility, 5=Notes
    for row_el, plan in zip(data_rows, plan_rows):
        cells = list(row_el.iter(W + "tc"))
        if len(cells) < 6:
            continue
        for ci, val in enumerate(plan):
            _set_cell(cells[ci], val)


# ---------------------------------------------------------------------------
# Master apply
# ---------------------------------------------------------------------------

def _apply_document(
    root: ET.Element,
    analysis: dict[str, Any],
    manual_total_students: float | None = None,
) -> None:
    metrics = _derive_program_metrics(analysis, manual_total_students)
    _apply_academic_year(root)
    _apply_basic_info(root, metrics)
    _apply_instructors_table(root)
    _apply_students_table(root, metrics)
    _apply_kpi_table(root, metrics)
    _apply_kpi_comment(root, analysis)
    _apply_stakeholders_table(root)
    _apply_overall_evaluation(root, metrics, analysis)
    _apply_enhancement(root, metrics, analysis)
    _apply_action_plan(root, metrics, analysis)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_program_report_docx(
    template_path: str | Path,
    analysis: dict[str, Any],
    output: io.BytesIO | None = None,
    manual_total_students: float | None = None,
) -> bytes:
    template = Path(template_path)
    if not template.exists():
        raise FileNotFoundError(f"Program report template not found: {template}")

    with zipfile.ZipFile(template, "r") as src:
        entries = [(item, src.read(item.filename)) for item in src.infolist()]
        document_xml = src.read("word/document.xml")

    root = ET.fromstring(document_xml)
    _apply_document(root, analysis or {}, manual_total_students)
    updated_xml = ET.tostring(root, encoding="UTF-8", xml_declaration=True)

    if output is None:
        output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as tgt:
        for item, data in entries:
            tgt.writestr(item, updated_xml if item.filename == "word/document.xml" else data)

    return output.getvalue()
