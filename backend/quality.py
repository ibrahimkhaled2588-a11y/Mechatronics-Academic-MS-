from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import numpy as np

from config import get_academic

_cfg = get_academic()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core quality functions
# ---------------------------------------------------------------------------

def missing_ratio(df: pd.DataFrame) -> float:
    total = df.size
    missing = df.isnull().sum().sum()
    return (missing / total) * 100 if total > 0 else 0


def duplicate_rate(df: pd.DataFrame) -> float:
    total = len(df)
    dup = df.duplicated().sum()
    return (dup / total) * 100 if total > 0 else 0


def precision_score(df: pd.DataFrame) -> float:
    total = len(df)
    valid = df.dropna().shape[0]
    return valid / total if total > 0 else 0


def consistency_index(df: pd.DataFrame) -> float:
    total = df.size
    consistent = df.notnull().sum().sum()
    return consistent / total if total > 0 else 0


def anomaly_density(df: pd.DataFrame, threshold: float | None = None) -> float:
    """Fraction of numeric cells identified as outliers via Z-score."""
    num = df.select_dtypes(include="number")
    if num.empty:
        return 0.0
    z_threshold = threshold if threshold is not None else _cfg.z_score_threshold
    std = num.std(ddof=0)
    valid_cols = std[std > 0].index
    if valid_cols.empty:
        return 0.0
    sub = num[valid_cols]
    z = ((sub - sub.mean()) / std[valid_cols]).abs()
    outliers = int((z > z_threshold).sum().sum())
    total = sub.size
    return outliers / total if total > 0 else 0.0


def completeness_score(df: pd.DataFrame) -> float:
    mr = missing_ratio(df) / 100.0
    return 1.0 - mr


def uniqueness_score(df: pd.DataFrame) -> float:
    dr = duplicate_rate(df) / 100.0
    return 1.0 - dr


def anomaly_density_iqr(df: pd.DataFrame, k: float | None = None) -> float:
    """Anomaly density using IQR method."""
    num = df.select_dtypes(include="number")
    if num.empty:
        return 0.0
    multiplier = k if k is not None else _cfg.iqr_multiplier
    q1 = num.quantile(0.25)
    q3 = num.quantile(0.75)
    iqr = q3 - q1
    valid_cols = iqr[iqr > 0].index
    if valid_cols.empty:
        return 0.0
    sub = num[valid_cols]
    low = q1[valid_cols] - multiplier * iqr[valid_cols]
    high = q3[valid_cols] + multiplier * iqr[valid_cols]
    outliers = int(((sub < low) | (sub > high)).sum().sum())
    total = sub.size
    return outliers / total if total > 0 else 0.0


_PSI_EPSILON = 1e-6


def psi_score(series_old: pd.Series, series_new: pd.Series, bins: int | None = None) -> float:
    """Population Stability Index. >0.2 suggests significant drift."""
    n_bins = bins if bins is not None else _cfg.psi_bins
    try:
        o = series_old.dropna()
        n = series_new.dropna()
        if len(o) < 2 or len(n) < 2:
            return 0.0
        edges = np.percentile(np.concatenate([o.values, n.values]), np.linspace(0, 100, n_bins + 1))
        edges = np.unique(edges)
        if len(edges) < 2:
            return 0.0
        p_old = np.histogram(o, bins=edges)[0] / len(o)
        p_new = np.histogram(n, bins=edges)[0] / len(n)
        p_old = np.clip(p_old, _PSI_EPSILON, None)
        p_new = np.clip(p_new, _PSI_EPSILON, None)
        return float(np.sum((p_new - p_old) * np.log(p_new / p_old)))
    except Exception:
        logger.debug("PSI calculation failed", exc_info=True)
        return 0.0


def data_drift_score(df_old: pd.DataFrame, df_new: pd.DataFrame) -> float:
    """Average PSI across shared numeric columns."""
    num_old = df_old.select_dtypes(include="number")
    num_new = df_new.select_dtypes(include="number")
    if num_old.empty or num_new.empty:
        return 0.0
    shared = [c for c in num_old.columns if c in num_new.columns]
    if not shared:
        return 0.0
    psi_values = [psi_score(num_old[c], num_new[c]) for c in shared]
    return float(np.mean(psi_values)) if psi_values else 0.0


def composite_reliability_index(
    precision: float,
    consistency: float,
    completeness: float,
    anomaly_density_val: float,
    w1: float | None = None,
    w2: float | None = None,
    w3: float | None = None,
    w4: float | None = None,
) -> float:
    """
    Reliability = w1*Precision + w2*Consistency + w3*Completeness + w4*(1 - Anomaly).
    All four weights sum to 1.0 so the maximum output is 1.0.
    Result clamped to [0, 1].
    """
    _w1 = w1 if w1 is not None else _cfg.reliability_w_precision     # 0.40
    _w2 = w2 if w2 is not None else _cfg.reliability_w_consistency   # 0.30
    _w3 = w3 if w3 is not None else _cfg.reliability_w_completeness  # 0.20
    _w4 = w4 if w4 is not None else _cfg.reliability_w_anomaly       # 0.10
    # Treat anomaly as negative contribution: (1 - anomaly) is the quality factor
    r = _w1 * precision + _w2 * consistency + _w3 * completeness + _w4 * (1.0 - anomaly_density_val)
    return float(np.clip(r, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Per-column quality profile (new)
# ---------------------------------------------------------------------------

def column_quality_profile(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return per-column quality summary: missing %, dtype, outlier count, unique count."""
    profile = []
    n_rows = len(df)
    if n_rows == 0:
        return profile
    for col in df.columns:
        series = df[col]
        missing_pct = round(series.isna().sum() / n_rows * 100, 2)
        unique_count = int(series.nunique(dropna=True))
        outlier_count = 0
        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            if len(clean) > 1:
                std = clean.std()
                if std > 0:
                    z = ((clean - clean.mean()) / std).abs()
                    outlier_count = int((z > _cfg.z_score_threshold).sum())
        profile.append({
            "column": str(col),
            "dtype": str(series.dtype),
            "missing_pct": missing_pct,
            "unique_count": unique_count,
            "outlier_count": outlier_count,
        })
    return profile


# ---------------------------------------------------------------------------
# Compute KPIs (extended)
# ---------------------------------------------------------------------------

def compute_kpis(
    df: pd.DataFrame,
    df_previous: pd.DataFrame | None = None,
    reliability_weights: dict | None = None,
) -> dict:
    mr = missing_ratio(df)
    dr = duplicate_rate(df)
    ps = precision_score(df)
    ci = consistency_index(df)
    ad = anomaly_density(df)
    comp = completeness_score(df)
    uniq = uniqueness_score(df)
    ad_iqr = anomaly_density_iqr(df)
    drift = data_drift_score(df_previous, df) if df_previous is not None else 0.0
    weights = reliability_weights or {}
    rel = composite_reliability_index(
        ps, ci, comp, ad,
        w1=weights.get("w1"),
        w2=weights.get("w2"),
        w3=weights.get("w3"),
        w4=weights.get("w4"),
    )
    return {
        "missing_ratio": mr,
        "duplicate_rate": dr,
        "precision_score": ps,
        "consistency_index": ci,
        "anomaly_density": ad,
        "anomaly_density_iqr": ad_iqr,
        "completeness": comp,
        "uniqueness": uniq,
        "data_drift_score": drift,
        "composite_reliability_index": rel,
        "column_profile": column_quality_profile(df),
    }
