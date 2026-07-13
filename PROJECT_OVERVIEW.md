# Project Overview

## What this project is

An academic data-quality and analytics web application for a university program (MECE-style academic reporting). Staff upload raw Excel exports (grades, enrollment, surveys) and the system automatically:

- Checks the data for quality problems (missing values, duplicates, inconsistent entries, anomalies, schema drift between uploads)
- Produces academic performance analytics (enrollment, excellence/failure rates, GPA per course, volatility, high-risk courses)
- Runs simple ML-style predictions (data quality degradation risk, course risk probabilities)
- Generates ready-to-share outputs: dashboards, PowerPoint reports, Word program reports, and survey visualizations
- Offers a Q&A chatbot over the data

In short: it turns messy raw Excel gradebooks/surveys into validated, visualized, and reportable academic intelligence — with minimal manual cleanup.

## Where things live

```
backend/            FastAPI application (Python)
  app.py               Main API app, upload endpoint(s), static frontend mount
  excel_reader.py       Reads/parses uploaded .xlsx files
  schema_inference.py    Infers column roles (Course, Student ID, Grade, Semester...), detects schema drift
  quality.py             Data quality KPIs (missing ratio, duplicates, precision, consistency, anomaly detection, drift/PSI, reliability index)
  academic_analytics.py  Top-20 enrollment/excellence/failure/GPA, volatility, high-risk courses
  kpis.py                Core academic KPI formulas (excellence/failure rate, GPA estimate, GPA variance)
  ml_models.py           Quality-degradation prediction, course risk probabilities
  alerts.py              Threshold + predictive alert generation
  course_matching.py     Normalizes/merges course names across sheets (fuzzy matching)
  course_plans.py, course_report_docx.py, program_report_docx.py
                          Generate Word (.docx) program/course reports
  statistics_course.py, statistics_cross.py, statistics_program.py, statistics_quality.py
                          Deeper statistical breakdowns used in reports
  survey_dashboard.py    Survey Excel -> dashboard image + PPTX generation
  strategic_analysis.py  Higher-level strategic/summary analysis
  chatbot.py              Q&A chatbot over uploaded academic data
  grade_utils.py, merge_excel_stats.py, extract_data.py
                          Supporting utilities for grade parsing and stat merging
  db.py                   Shared SQLite connection helper for accreditation-support data
  indicators.py           Standard 7 (Quality Assurance & Program Evaluation) indicators tracker —
                          status/evidence per accreditation indicator + append-only closing-the-loop log
  sheets_sync.py           Pulls status/responsible/evidence/due-date from a shared Google Sheet
                          (public XLSX export, no credentials) into the indicators tracker
  curriculum_mapping.py   Standard 2 (Program Design) curriculum mapping — ILOs CRUD, course list
                          (manual or de-duplicated Excel import via course_matching.py), coverage matrix,
                          zero/low-coverage and heavy-duplication analysis
  curriculum_map_report.py  Curriculum map DOCX export (matrix + findings)
  governance.py            Standard 1 (Mission & Program Management) — versioned mission/goals text,
                          council/committee document register, stakeholder-participation log
  faculty_data.py          Standard 5 (Faculty & Supporting Staff) — roster, teaching load, publication
                          log; load-imbalance flags (z-score) and specialization-gap flags
  tests/                  Backend test suite
  exports/                Generated report/output files, incl. exports/governance_documents/ (uploaded minutes etc.)
  data/                   SQLite file for accreditation-support data (git-ignored, created at runtime)

frontend/            Static web UI served by the backend
  index.html            Home page (entry point, links to the tools below)
  dashboard.html         Main data-quality + academic analytics dashboard (Excel upload, KPI cards, charts)
  survey-dashboard.html  Survey Excel upload -> dashboard image / PPTX / ZIP export
  course-report.html     Course-level report viewer
  program-report.html    Program-level report viewer
  qa-chat.html            Chatbot interface
  indicators-tracker.html Accreditation indicators tracker (Standard 7), grouped by standard, inline-editable,
                          with a "Sync from Google Sheet" button
  curriculum-mapping.html Curriculum mapping (Standard 2): ILOs, course list/import, coverage matrix, findings
  governance.html         Governance (Standard 1): mission version history, document register, stakeholder log
  faculty-dashboard.html  Faculty dashboard (Standard 5): roster, teaching load, publications, load/gap flags
  css/, js/               Styling and client-side logic (Chart.js-based visualizations)

ARCHITECTURE.md            Detailed technical architecture (data flow, KPI formulas, component table)
Program_Analytics_Report.md Generated/example analytics report output
SURVEY_DASHBOARD_README.md  How-to for the survey dashboard feature
TODO.md                     Active work notes (currently: course-name normalization/matching layer)

Source data files (root):
  MECE Program Report *.docx        Underlying program report documents (input/reference material)
  probability course report *.pdf    Course-level reference report
  *.xlsx (Arabic-named)              Raw grade/estimate spreadsheets used as real input data
```

## Why the project exists / what problem it solves

University program reporting (e.g. accreditation/quality-assurance reports like MECE) traditionally requires manually:

1. Collecting raw grade and survey spreadsheets from multiple sources/semesters
2. Manually checking them for errors, missing data, and inconsistent course naming
3. Computing KPIs (failure rates, GPA, excellence rates) by hand or in ad-hoc spreadsheets
4. Building charts and writing up Word/PowerPoint reports for stakeholders

This is slow, error-prone, and hard to repeat consistently across semesters. This project automates that pipeline end-to-end:

- **Data trust first**: before any analytics are shown, the system quantifies how reliable the uploaded data is (quality/reliability score, drift vs. previous upload) so decisions aren't made on bad data.
- **Consistency**: the same KPI formulas and thresholds are applied every time, removing manual spreadsheet variance between reporting cycles.
- **Speed**: upload an Excel file and get dashboards, risk flags, and draft reports in seconds instead of days.
- **Stakeholder-ready output**: results aren't just on-screen — they're exported as Word/PowerPoint/PNG artifacts suitable for accreditation bodies or program leadership.
- **Early warning**: predictive/ML-style scoring on course risk and data-quality degradation is meant to surface problems (e.g., a course trending toward high failure rate) before they show up in a final report.

## Current state

Core pipeline (upload → quality checks → academic analytics → charts → reports) is implemented per [ARCHITECTURE.md](ARCHITECTURE.md). Per [TODO.md](TODO.md), the course-name normalization/matching layer is implemented and live-verified against real uploaded files (2026-07-13).

The app is being extended to support Egypt's NAQAAE-style 7-standard accreditation process (see "Accreditation Support" in [ARCHITECTURE.md](ARCHITECTURE.md)). Phase 1 (Standard 7 — the indicators tracker) is done: `backend/indicators.py` + `frontend/indicators-tracker.html`, backed by a new SQLite persistence layer (`backend/db.py`) since accreditation data needs to survive restarts unlike the core analytics pipeline. Phase 2 (Standard 2 — curriculum mapping) is also done: `backend/curriculum_mapping.py` + `frontend/curriculum-mapping.html`, which imports a de-duplicated course list straight from an uploaded grades workbook (reusing `course_matching.py`), lets staff mark a courses x ILOs coverage matrix, and can mark the relevant Standard 2 indicator complete in the Phase 1 tracker with the exported DOCX as evidence. Phase 3 (Standard 1 — governance) is done: `backend/governance.py` + `frontend/governance.html`, a document-register-style page (not analytics-heavy) for versioned mission/goals text, council/committee meeting minutes, and a stakeholder-consultation log, wired into the Phase 1 tracker the same way. Phase 4 (Standard 5 — faculty data) is done: `backend/faculty_data.py` + `frontend/faculty-dashboard.html`, tracking the faculty roster, teaching load, and publications, with load-imbalance and specialization-gap flags computed using the same z-score/normalization patterns as the core `quality.py` and `course_matching.py` modules. Every later accreditation phase (resources, alumni) will register its evidence against indicators the same way.

The indicators tracker also syncs against a team-facing Google Sheet (`backend/sheets_sync.py`): team members fill in status/evidence/responsible/due-date per indicator in a shared Sheet (one tab per standard), and the coordinator clicks "Sync from Google Sheet" on the tracker page to pull it in — the coordinator only ever needs to look at the site's roll-up progress view, not the raw Sheet. The sync also replaced the tracker's English placeholder indicator text with the real official Arabic wording the team had already written into the Sheet.
