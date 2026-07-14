# Enterprise Predictive Data Precision & Academic Analytics – Architecture

## System Overview

The system monitors **data quality**, detects **anomalies**, evaluates **reliability**, and **predicts degradation** before it impacts reporting. It is integrated with an **Academic Performance Intelligence Dashboard**.

---

## High-Level Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              WEB APPLICATION                                  │
├─────────────────────────────────┬───────────────────────────────────────────┤
│   Frontend (Two-Page UI)        │   Backend API (FastAPI)                    │
│   • Home Page (Logo + CTA)      │   • Data Ingestion Engine                  │
│   • Work Page (Dashboard)       │   • Data Profiling / Schema Inference      │
│   • Excel Upload Section        │   • Quality Engine (KPIs, Drift, Reliability)│
│   • Data Quality Results        │   • Academic Analytics Engine             │
│   • Academic Visualizations     │   • ML Engine (Quality & Course Risk)     │
│   • Predictive Risk Indicators  │   • Alert System                           │
│   • Charts (Chart.js)          │   • Metadata Storage (in-memory / DB)      │
└─────────────────────────────────┴───────────────────────────────────────────┘
                    │                                    │
                    │  HTTP (same origin)                 │  Excel (.xlsx)
                    └────────────────────────────────────┘
```

---

## End-to-End Workflow

1. **User** opens Home Page → clicks “Start Analysis” → lands on **Dashboard**.
2. **User** uploads an Excel file (.xlsx) via the upload interface.
3. **Backend** receives file:
   - **Validate** format (.xlsx only).
   - **Read all sheets** dynamically (no hardcoded files).
   - **Infer schema** (column roles: Course, Student ID, Grade, Semester, Department).
   - **Schema validation** and **schema change detection** vs previous upload (drift).
   - **Store metadata** (timestamp, version, file history count).
4. **Quality Engine** runs:
   - Missing ratio, duplicate rate, precision, consistency, completeness, uniqueness.
   - Anomaly density (Z-score and IQR).
   - Data drift score (PSI on numeric columns when previous upload exists).
   - Composite reliability index (configurable weights).
5. **Academic Analytics Engine** runs (per sheet):
   - Top 20 enrollment (with abnormal spike detection).
   - Top 20 excellence rate, Top 20 failure rate (high-risk flag).
   - Top 20 GPA per course (GPA variance, volatility index).
6. **ML Engine** runs:
   - Predicted quality score and risk probability per sheet.
   - Course risk probabilities (from failure rate and GPA).
   - Feature importance (placeholder).
7. **Alert System** triggers alerts (quality, failure rate, drift, predicted risk %).
8. **Response** returns metadata, KPIs, academic analytics, predictions, course risk, alerts.
9. **Frontend** renders: alerts, quality cards, bar charts (enrollment, excellence, failure, GPA), tables, predictive risk cards.

---

## Core Components

| Component | Responsibility |
|-----------|-----------------|
| **Data Ingestion** | Accept Excel upload, validate format, read all sheets, pass to profiling and quality. |
| **Data Profiling / Schema** | Infer column roles, validate schema, detect schema changes for drift. |
| **Quality Engine** | Compute KPIs (missing, duplicate, precision, consistency, completeness, uniqueness, anomaly Z-score/IQR, drift PSI, composite reliability). |
| **Academic Analytics** | Top 20 enrollment/excellence/failure/GPA, GPA variance, volatility, high-risk courses. |
| **ML Engine** | Predict quality degradation, course risk probabilities; feature importance (extensible to ARIMA, RF/XGBoost, Isolation Forest). |
| **Alert System** | Threshold-based and predictive alerts (quality, failure rate, GPA, drift, risk %). |
| **Visualization** | Dashboard with cards, bar charts (Chart.js), tables; responsive layout. |
| **Metadata Storage** | In-memory list of uploads + last DataFrame per sheet for drift; production would use a database. |

---

## Secure File Handling & Scalability

- **Secure file handling**: Only .xlsx accepted; file read in memory (no arbitrary path access). For production: limit file size, virus scan, store in temp with cleanup.
- **Version comparison**: Previous upload’s schema and DataFrame (per sheet) used for drift and schema change detection.
- **BI / ETL**: API returns structured JSON (metadata, KPIs, academic, predictions); can be consumed by BI tools or ETL pipelines.
- **Cloud scalability**: Stateless API; metadata and history would move to a database (e.g. PostgreSQL) and object storage for large files.

---

## KPI Formulas (Summary)

- **Missing Ratio** = (Missing / Total) × 100  
- **Duplicate Rate** = (Duplicate Rows / Total Rows) × 100  
- **Precision** = Valid Records / Total Records  
- **Consistency** = Consistent Entries / Total Entries  
- **Anomaly Density** = Outliers / Total Records (Z-score or IQR)  
- **Data Drift Score** = PSI (or KL divergence) on numeric columns  
- **Composite Reliability** = w1×Precision + w2×Consistency + w3×Completeness − w4×Anomaly Density (weights configurable)  
- **Excellence Rate** = (Excellent Grades / Total) × 100  
- **Failure Rate** = (Failed Students / Total) × 100  
- **GPA** = Σ(Grade Value × Count) / Total (A=4, B=3, C=2, D=1, F=0)  

---

## File Layout

- `backend/app.py` – FastAPI app, upload endpoint, static frontend mount.  
- `backend/quality.py` – KPIs, drift (PSI), reliability index.  
- `backend/schema_inference.py` – Column role inference, schema validation, schema change detection.  
- `backend/academic_analytics.py` – Top 20 enrollment/excellence/failure/GPA, volatility.  
- `backend/kpis.py` – Excellence rate, failure rate, GPA estimate, GPA variance.  
- `backend/ml_models.py` – Quality prediction, course risk probabilities.  
- `backend/alerts.py` – Alert generation from thresholds.  
- `backend/db.py` – Shared SQLite connection helper for accreditation-support data (see below).  
- `backend/indicators.py` – Standard 7 accreditation indicators tracker (list/status/evidence, closing-the-loop log); integration point for the other accreditation-support modules as they land.  
- `backend/curriculum_mapping.py` – Standard 2 curriculum mapping: ILOs CRUD, course list (manual entry or de-duplicated import via `course_matching.py`), courses x ILOs coverage matrix, and coverage-gap/duplication analysis.  
- `backend/curriculum_map_report.py` – Curriculum map DOCX export (matrix + findings), built from scratch with python-docx following `course_report_docx.py`'s pattern.  
- `backend/governance.py` – Standard 1 governance: versioned mission/goals text, a council/committee document register (files on disk under `backend/exports/governance_documents/`, metadata in SQLite), and an append-only stakeholder-participation log.  
- `backend/faculty_data.py` – Standard 5 faculty data: roster (specialization/degree/rank), teaching load per semester, research/publication log; load-imbalance flags (z-score, same statistical pattern as `quality.py`'s anomaly detection) and specialization-gap flags (course vs. instructor specialization token overlap, reusing `course_matching.py`'s normalization).  
- `backend/resources.py` – Standard 6 resources & facilities: lab/equipment inventory with status + next maintenance date, library holdings counts, annual budget entries; a maintenance-due view (overdue/due-within-N-days) derived from the equipment table.  
- `frontend/` – Home, Dashboard, CSS (White + Blue + Orange), Chart.js, dashboard_logic.js.  
- `frontend/indicators-tracker.html` + `frontend/js/indicators_tracker.js` – Accreditation indicators tracker UI (grouped by standard, inline edit, closing-the-loop log, Google Sheet sync button).  
- `frontend/curriculum-mapping.html` + `frontend/js/curriculum_mapping.js` – Curriculum mapping UI (ILOs, course list + Excel import, coverage matrix checkboxes, findings, Standard 2 indicator sync).  
- `frontend/governance.html` + `frontend/js/governance.js` – Governance UI (mission version history, document register with upload/filter, stakeholder log, Standard 1 indicator sync).  
- `frontend/faculty-dashboard.html` + `frontend/js/faculty_dashboard.js` – Faculty dashboard UI (roster, teaching load, publications, load-balance KPI cards, imbalance/specialization-gap flag tables, Standard 5 indicator sync).  
- `frontend/resources.html` + `frontend/js/resources.js` – Resources dashboard UI (KPI cards, maintenance-due list, equipment/library/budget registers, Standard 6 indicator sync).  

---

## Accreditation Support (NAQAAE-style, 7 Standards)

Extending the core analytics app to support Egypt's academic program
accreditation process. Standard 3 (Teaching, Learning & Assessment) is
already substantially covered by `academic_analytics.py`/`kpis.py`/
`statistics_course.py`; Standard 4 (Students & Graduates) is partially
covered by `survey_dashboard.py`. New modules land per standard:

| Standard | Module | Status |
|----------|--------|--------|
| 7. Quality Assurance & Program Evaluation | `backend/indicators.py` | Done (Phase 1) — built first since every other standard registers evidence here |
| 2. Program Design | `backend/curriculum_mapping.py`, `backend/curriculum_map_report.py` | Done (Phase 2) |
| 1. Mission & Program Management | `backend/governance.py` | Done (Phase 3) |
| 5. Faculty & Supporting Staff | `backend/faculty_data.py` | Done (Phase 4) |
| 6. Resources & Learning Facilities | `backend/resources.py` | Done (Phase 5) |
| 4. Students & Graduates (alumni) | `backend/alumni.py` | Planned |
| Final integration | `backend/ssr_report.py` (or extend `program_report_docx.py`) | Planned |

**Persistence**: unlike the core analytics pipeline (in-memory, request-scoped
— see `_upload_history` in `app.py`), accreditation data must survive a
server restart. It lives in a single SQLite file
(`backend/data/accreditation.db`, path configurable via
`ACCREDITATION_DB_PATH`) accessed through `backend/db.py`. Each domain
module owns its own tables via idempotent `CREATE TABLE IF NOT EXISTS`
statements called from its own `init_db()`.

**Google Sheet sync for indicators**: `backend/sheets_sync.py` lets the
coordinator pull team-filled status/responsible/evidence/due-date straight
from a shared Google Sheet into the indicators tracker
(`POST /api/indicators/sync-sheet`), so the team can work in a familiar
Sheet while the coordinator only looks at the website's roll-up progress
view. No Google API credentials — it reads the sheet's public XLSX export,
so the sheet must be shared as "Anyone with the link can view". Matching
is positional (row N in a standard's tab → the Nth indicator already
stored for that standard), not text-based, since the sheet holds the real
official indicator wording while the tracker starts out seeded with
placeholder text — a sync also overwrites `indicator_text`, which is how
the placeholders get replaced with the real wording. The tracker's own
inline editor stays fully editable too (per product decision, both the
site and the Sheet can write status) — a later sync simply overwrites
whichever fields the sheet has non-blank values for.
