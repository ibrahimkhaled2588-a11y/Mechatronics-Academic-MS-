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
- `frontend/` – Home, Dashboard, CSS (White + Blue + Orange), Chart.js, dashboard_logic.js.  
