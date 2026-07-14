"""
Self-Study Report (SSR) generator — final integration across all 7 standards.

Builds one Word document with a section per NAQAAE-style standard, pulling
automatically from each phase's own storage:

  Standard 1  governance.py            mission text, document register, stakeholder log
  Standard 2  curriculum_mapping.py    ILOs, coverage-matrix findings
  Standard 3  academic_analytics/kpis  KPI figures, via the same derivation program_report_docx.py
                                       already uses (reused here, not reimplemented)
  Standard 4  alumni.py                graduate roster stats (+ a pointer to the survey dashboard,
                                       since survey responses are anonymous/aggregate — see alumni.py)
  Standard 5  faculty_data.py          roster, load-imbalance / specialization-gap flags
  Standard 6  resources.py             equipment/library/budget, maintenance-due
  Standard 7  indicators.py            per-standard status + closing-the-loop log

Built from scratch with python-docx, following the same helper pattern as
course_report_docx.py and curriculum_map_report.py (not the XML-template
approach in program_report_docx.py, since there's no fixed NAQAAE SSR
template to fill in here — only its KPI-derivation helper is reused).
"""
from __future__ import annotations

from typing import Any

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

import alumni
import curriculum_mapping
import faculty_data
import governance
import indicators
import resources

_HEADER_BLUE = RGBColor(0x1E, 0x3A, 0x5F)
_LIGHT_GREY = "D9D9D9"


# ---------------------------------------------------------------------------
# Shared docx helpers (same pattern as course_report_docx.py / curriculum_map_report.py)
# ---------------------------------------------------------------------------

def _shade_cell(cell, hex_color: str) -> None:
    shd = cell._tc.get_or_add_tcPr().makeelement(qn("w:shd"), {
        qn("w:val"): "clear", qn("w:color"): "auto", qn("w:fill"): hex_color,
    })
    cell._tc.get_or_add_tcPr().append(shd)


def _bold(cell, text: str, size: int | None = None) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(text)
    run.bold = True
    if size is not None:
        run.font.size = Pt(size)


def _standard_heading(doc: Document, number: int, title: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(20)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(f"Standard {number} — {title}")
    run.bold = True
    run.font.size = Pt(16)
    run.font.color.rgb = _HEADER_BLUE


def _subheading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(11.5)


def _bullet_list(doc: Document, items: list[str], empty_text: str) -> None:
    if not items:
        doc.add_paragraph().add_run(empty_text).italic = True
        return
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def _simple_table(doc: Document, headers: list[str], rows: list[list[str]], empty_text: str) -> None:
    if not rows:
        doc.add_paragraph().add_run(empty_text).italic = True
        return
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        _bold(hdr[i], h, size=9.5)
        _shade_cell(hdr[i], _LIGHT_GREY)
    for row_vals in rows:
        cells = table.add_row().cells
        for i, v in enumerate(row_vals):
            cells[i].text = str(v)


# ---------------------------------------------------------------------------
# Section builders — one per standard
# ---------------------------------------------------------------------------

def _build_standard_1(doc: Document) -> None:
    _standard_heading(doc, 1, "Mission & Program Management")

    _subheading(doc, "Program Mission")
    mission = governance.get_current_mission()
    doc.add_paragraph(mission["mission_text"] if mission else "No mission text has been recorded yet.")
    versions = governance.list_mission_versions()
    if len(versions) > 1:
        doc.add_paragraph(f"({len(versions)} versions on record; most recent shown above.)").italic = True

    _subheading(doc, "Council / Committee Document Register")
    docs = governance.list_documents()
    _simple_table(
        doc,
        ["Title", "Committee", "Date"],
        [[d["title"], d.get("committee_name") or "", d.get("document_date") or ""] for d in docs],
        "No governance documents have been registered yet.",
    )

    _subheading(doc, "Stakeholder Participation Log")
    log = governance.list_stakeholder_log()
    _simple_table(
        doc,
        ["Stakeholder", "Role", "Date", "Topic"],
        [[e["stakeholder_name"], e.get("stakeholder_role") or "", e["consulted_on"], e["topic"]] for e in log],
        "No stakeholder consultations have been logged yet.",
    )


def _build_standard_2(doc: Document) -> None:
    _standard_heading(doc, 2, "Program Design")

    ilos = curriculum_mapping.list_ilos()
    courses = curriculum_mapping.list_courses()
    summary = curriculum_mapping.compute_coverage_summary()

    doc.add_paragraph(
        f"{len(ilos)} Program Intended Learning Outcomes (ILOs) mapped across {len(courses)} courses. "
        f"Full courses x ILOs coverage matrix is available via the Curriculum Mapping page's DOCX export."
    )

    _subheading(doc, "Program Intended Learning Outcomes")
    _simple_table(
        doc,
        ["Code", "Text"],
        [[i.get("ilo_code") or f"ILO{i['id']}", i["ilo_text"]] for i in ilos],
        "No ILOs have been entered yet.",
    )

    _subheading(doc, "Coverage Findings")
    doc.add_paragraph("ILOs with zero coverage:")
    _bullet_list(
        doc,
        [f"{i.get('ilo_code') or ('ILO' + str(i['id']))}: {i['ilo_text']}" for i in summary["zero_coverage_ilos"]],
        "None — every ILO is addressed by at least one course.",
    )
    doc.add_paragraph("Courses with no mapped ILOs:")
    _bullet_list(
        doc,
        [c["course_name"] for c in summary["courses_without_ilos"]],
        "None — every course is mapped to at least one ILO.",
    )


def _build_standard_3(doc: Document, analysis: dict[str, Any] | None) -> None:
    _standard_heading(doc, 3, "Teaching, Learning & Assessment")

    if not analysis:
        doc.add_paragraph(
            "No analytics data was supplied for this report. Generate this section by uploading a "
            "grades workbook on the Quality Dashboard and re-running the SSR export with that analysis "
            "attached."
        ).italic = True
        return

    from program_report_docx import _derive_program_metrics, _fmt_gpa, _fmt_number, _fmt_percent

    metrics = _derive_program_metrics(analysis)
    _simple_table(
        doc,
        ["Metric", "Value"],
        [
            ["Courses analyzed", _fmt_number(metrics["course_count"])],
            ["Total enrollment", _fmt_number(metrics["total_enrollment"])],
            ["Average GPA", _fmt_gpa(metrics["avg_gpa"])],
            ["Average failure rate", _fmt_percent(metrics["failure_rate"])],
            ["Average excellence rate", _fmt_percent(metrics["excellence_rate"])],
            ["Courses with failure rate > 20%", _fmt_number(metrics["courses_over_20_failure"])],
        ],
        "No KPI data available.",
    )


def _build_standard_4(doc: Document) -> None:
    _standard_heading(doc, 4, "Students & Graduates")

    summary = alumni.get_registry_summary()
    _simple_table(
        doc,
        ["Metric", "Value"],
        [
            ["Alumni registered", str(summary["total_alumni"])],
            ["Employment rate", f"{summary['employment_rate']}%"],
            ["Survey participation rate", f"{summary['survey_participation_rate']}%"],
        ],
        "No alumni data available.",
    )
    doc.add_paragraph(
        "Note: survey responses collected via the Survey Dashboard are anonymous and aggregate-only, "
        "so they cannot be joined to individual alumni records here. Attach the Survey Dashboard's "
        "satisfaction results (PPTX/PNG export) separately as supporting evidence for this standard."
    ).italic = True


def _build_standard_5(doc: Document) -> None:
    _standard_heading(doc, 5, "Faculty & Supporting Staff")

    summary = faculty_data.get_dashboard_summary()
    _simple_table(
        doc,
        ["Metric", "Value"],
        [
            ["Faculty members", str(summary["total_faculty"])],
            ["Average teaching load (hours/semester)", str(summary["average_load_hours"])],
            ["Overloaded flags", str(summary["overloaded_count"])],
            ["Underloaded flags", str(summary["underloaded_count"])],
            ["Specialization gaps", str(summary["specialization_gap_count"])],
        ],
        "No faculty data available.",
    )

    _subheading(doc, "Specialization Gaps")
    _bullet_list(
        doc,
        [f"{g['course_name']} ({g['semester']}) — {g['faculty_name']}" for g in summary["specialization_gap_flags"]],
        "None detected.",
    )


def _build_standard_6(doc: Document) -> None:
    _standard_heading(doc, 6, "Resources & Learning Facilities")

    summary = resources.get_dashboard_summary()
    _simple_table(
        doc,
        ["Metric", "Value"],
        [
            ["Equipment items", str(summary["total_equipment"])],
            ["Needing repair", str(summary["needs_repair_count"])],
            ["Out of service", str(summary["out_of_service_count"])],
            ["Maintenance due (30 days)", str(summary["maintenance_due_count"])],
            ["Library items", f"{summary['total_library_items']} ({summary['total_library_titles']} titles)"],
            ["Total budget recorded", str(summary["total_budget_amount"])],
        ],
        "No resource data available.",
    )

    _subheading(doc, "Maintenance Due")
    _simple_table(
        doc,
        ["Equipment", "Location", "Due Date", "Status"],
        [
            [e["name"], e.get("location") or "", e["next_maintenance_date"], "Overdue" if e["overdue"] else "Due soon"]
            for e in summary["maintenance_due"]
        ],
        "Nothing due for maintenance in the next 30 days.",
    )


def _build_standard_7(doc: Document) -> None:
    _standard_heading(doc, 7, "Quality Assurance & Program Evaluation")

    _subheading(doc, "Indicator Status by Standard")
    standard_summaries = indicators.summarize_by_standard()
    _simple_table(
        doc,
        ["Standard", "Total", "Complete", "Partial", "Missing"],
        [
            [f"{s.standard_number}. {s.standard_name}", str(s.total), str(s.complete), str(s.partial), str(s.missing)]
            for s in standard_summaries
        ],
        "No indicators found.",
    )

    _subheading(doc, "Closing the Loop")
    all_indicators = indicators.list_indicators()
    loop_rows: list[list[str]] = []
    for ind in all_indicators:
        full = indicators.get_indicator(ind["id"])
        for entry in full.get("closing_the_loop_log", []):
            loop_rows.append([
                f"Std {ind['standard_number']}: {ind['indicator_text'][:60]}",
                entry["weakness_identified"],
                entry.get("action_taken") or "",
                entry["entry_date"],
                entry.get("entry_status") or "",
            ])
    _simple_table(
        doc,
        ["Indicator", "Weakness Identified", "Action Taken", "Date", "Status"],
        loop_rows,
        "No closing-the-loop entries have been logged yet.",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_ssr_docx(analysis: dict[str, Any] | None = None) -> bytes:
    import io

    doc = Document()
    style = doc.styles["Normal"]
    style.font.size = Pt(10.5)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Self-Study Report")
    run.bold = True
    run.font.size = Pt(22)
    run.font.color.rgb = _HEADER_BLUE

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run(
        "Auto-assembled from the program's accreditation-support modules "
        "(governance, curriculum mapping, faculty, resources, alumni, and the indicators tracker)."
    ).italic = True

    _build_standard_1(doc)
    _build_standard_2(doc)
    _build_standard_3(doc, analysis)
    _build_standard_4(doc)
    _build_standard_5(doc)
    _build_standard_6(doc)
    _build_standard_7(doc)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
