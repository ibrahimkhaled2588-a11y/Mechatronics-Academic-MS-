"""
Centralised configuration for the analytics backend.
All magic numbers, thresholds, and environment-driven settings live here.
Override any value via environment variables (e.g. MAX_UPLOAD_MB=100).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Alert thresholds
# ---------------------------------------------------------------------------

@dataclass
class AlertThresholds:
    """Thresholds used by alerts.py.  All values are in natural units (%, fraction, …)."""
    duplicate_rate: float = 5.0        # percent
    anomaly_density: float = 0.10      # fraction 0-1
    quality_score: float = 0.80        # fraction 0-1
    drift_score: float = 0.20          # PSI value
    predicted_risk_pct: float = 50.0   # percent
    failure_rate: float = 30.0         # percent
    high_risk_failure_rate: float = 20.0  # percent; flag course as high-risk


# ---------------------------------------------------------------------------
# Academic constants
# ---------------------------------------------------------------------------

@dataclass
class AcademicConstants:
    """Grade-mapping and academic thresholds shared across modules."""
    # Standard 4-point GPA scale
    gpa_map: dict[str, float] = field(default_factory=lambda: {
        "A+": 4.0, "A": 4.0, "A-": 3.7,
        "B+": 3.3, "B": 3.0, "B-": 2.7,
        "C+": 2.3, "C": 2.0, "C-": 1.7,
        "D+": 1.3, "D": 1.0, "F": 0.0,
    })
    gpa_scale: float = 4.0
    high_risk_failure_threshold: float = 30.0   # percent → flag in analytics
    excellence_grade_letters: tuple = ("A", "A+", "A-")

    # Monte-Carlo / simulation parameters
    mc_n_simulations: int = 1000
    mc_n_periods: int = 3
    stress_n_simulations: int = 500

    # Anomaly detection parameters (quality.py)
    z_score_threshold: float = 3.0
    iqr_multiplier: float = 1.5
    psi_bins: int = 10

    # Composite reliability weights (must sum to 1.0)
    reliability_w_precision: float = 0.4
    reliability_w_consistency: float = 0.3
    reliability_w_completeness: float = 0.2
    reliability_w_anomaly: float = 0.1


# ---------------------------------------------------------------------------
# Server / API settings
# ---------------------------------------------------------------------------

@dataclass
class ServerSettings:
    port: int = int(os.environ.get("PORT", 8000))
    max_upload_mb: int = int(os.environ.get("MAX_UPLOAD_MB", 50))
    max_upload_history: int = int(os.environ.get("MAX_UPLOAD_HISTORY", 100))
    # Explicit origins only — never use wildcard with credentials
    allowed_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in os.environ.get(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000",
        ).split(",")
        if o.strip()
    ])
    # Allowed frontend page names (whitelist for path traversal prevention)
    allowed_pages: frozenset[str] = field(default_factory=lambda: frozenset({
        "index.html",
        "dashboard.html",
        "course-report.html",
        "program-report.html",
        "survey-dashboard.html",
        "indicators-tracker.html",
        "curriculum-mapping.html",
        "governance.html",
        "faculty-dashboard.html",
        "resources.html",
        "login.html",
        "qa-chat.html",
    }))
    # SQLite database file for accreditation-support data (indicators, ILOs,
    # governance docs, faculty/resources/alumni registries). Separate from the
    # in-memory upload history above, which stays request-scoped by design.
    accreditation_db_path: str = os.environ.get(
        "ACCREDITATION_DB_PATH",
        os.path.join(os.path.dirname(__file__), "data", "accreditation.db"),
    )
    # Base directory for generated/uploaded files (survey PPTX/PNG exports,
    # governance document register). Point this at a persistent disk mount
    # in production (see DEPLOYMENT.md) — without one, anything written here
    # is lost on every redeploy.
    exports_dir: str = os.environ.get(
        "EXPORTS_DIR",
        os.path.join(os.path.dirname(__file__), "exports"),
    )
    # Optional: pre-fills the "Sync from Google Sheet" input on the
    # indicators tracker for every visitor, not just whoever last typed it
    # into their own browser's localStorage.
    default_indicators_sheet_url: str = os.environ.get("DEFAULT_INDICATORS_SHEET_URL", "")
    # Session cookie for the indicators-tracker team login (see auth.py).
    # Secure=True requires HTTPS (Fly/Render both terminate TLS in front of
    # the app) — disable only for local http:// testing via COOKIE_SECURE=false.
    cookie_secure: bool = os.environ.get("COOKIE_SECURE", "true").lower() == "true"


# ---------------------------------------------------------------------------
# Singleton accessors
# ---------------------------------------------------------------------------

_alert_thresholds = AlertThresholds()
_academic = AcademicConstants()
_server = ServerSettings()


def get_alert_thresholds() -> AlertThresholds:
    return _alert_thresholds


def get_academic() -> AcademicConstants:
    return _academic


def get_server() -> ServerSettings:
    return _server
