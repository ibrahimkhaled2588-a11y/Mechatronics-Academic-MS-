"""
Advanced Statistical Intelligence for Quality Dashboard.
Additive layer: distribution diagnostics, variability, multivariate analysis,
anomaly scoring, predictive uncertainty. Graceful fallback if scipy/sklearn missing.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.neighbors import LocalOutlierFactor
    from sklearn.covariance import EmpiricalCovariance
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def _safe_float(x: Any) -> float | None:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _numeric_matrix(df: pd.DataFrame) -> np.ndarray | None:
    num = df.select_dtypes(include=[np.number])
    if num.empty or len(num) < 3:
        return None
    arr = num.dropna(how="all").fillna(num.median()).values
    if arr.size < 4:
        return None
    return arr


# ----- 1) Data Distribution Diagnostics -----

def _shapiro_wilk(series: pd.Series) -> dict[str, Any]:
    if not HAS_SCIPY or series.dropna().size < 3:
        return {"statistic": None, "p_value": None, "normality": None}
    try:
        s = series.dropna().astype(float)
        if len(s) < 3:
            return {"statistic": None, "p_value": None, "normality": None}
        stat, p = scipy_stats.shapiro(s)
        return {
            "statistic": float(stat),
            "p_value": float(p),
            "normality": "Normal" if p > 0.05 else "Non-normal",
        }
    except Exception:
        return {"statistic": None, "p_value": None, "normality": None}


def _ks_test(series: pd.Series) -> dict[str, Any]:
    if not HAS_SCIPY or series.dropna().size < 3:
        return {"statistic": None, "p_value": None}
    try:
        s = series.dropna().astype(float)
        if len(s) < 3:
            return {"statistic": None, "p_value": None}
        mean, std = s.mean(), s.std()
        if std == 0:
            return {"statistic": None, "p_value": None}
        stat, p = scipy_stats.kstest(s, "norm", args=(mean, std))
        return {"statistic": float(stat), "p_value": float(p)}
    except Exception:
        return {"statistic": None, "p_value": None}


def _anderson_darling(series: pd.Series) -> dict[str, Any]:
    if not HAS_SCIPY or series.dropna().size < 5:
        return {"statistic": None, "critical_values": None}
    try:
        s = series.dropna().astype(float)
        if len(s) < 5:
            return {"statistic": None, "critical_values": None}
        res = scipy_stats.anderson(s, dist="norm")
        # critical_values is a NumPy array; significance_level is a parallel array of floats
        crit = {
            str(level): float(val)
            for level, val in zip(res.significance_level, res.critical_values)
        }
        return {
            "statistic": float(res.statistic),
            "critical_values": crit,
        }
    except Exception:
        return {"statistic": None, "critical_values": None}


def _distribution_fitting(series: pd.Series) -> dict[str, Any]:
    if not HAS_SCIPY:
        return {"best_fit": None, "scores": {}}
    try:
        s = series.dropna().astype(float)
        if len(s) < 5:
            return {"best_fit": None, "scores": {}}
        s_positive = s[s > 0]
        scores = {}
        if len(s_positive) >= 3:
            try:
                _, p_norm = scipy_stats.normaltest(s)
                scores["normal"] = float(p_norm)
            except Exception:
                scores["normal"] = 0.0
            try:
                ln = np.log(s_positive)
                _, p_ln = scipy_stats.normaltest(ln)
                scores["log_normal"] = float(p_ln)
            except Exception:
                scores["log_normal"] = 0.0
            try:
                shape, loc, scale = scipy_stats.gamma.fit(s_positive, floc=0)
                # Use KS-test p-value against fitted gamma as the score
                _, p_gamma = scipy_stats.kstest(s_positive, "gamma", args=(shape, loc, scale))
                scores["gamma"] = float(p_gamma)
            except Exception:
                scores["gamma"] = 0.0
        best = max(scores, key=scores.get) if scores else None
        return {"best_fit": best, "scores": scores}
    except Exception:
        return {"best_fit": None, "scores": {}}


def _symmetry_score(series: pd.Series) -> float | None:
    try:
        s = series.dropna().astype(float)
        if len(s) < 4:
            return None
        med = s.median()
        left = (s < med).sum()
        right = (s > med).sum()
        n = len(s)
        if n == 0:
            return None
        balance = 1 - abs(left - right) / n
        return float(np.clip(balance, 0, 1))
    except Exception:
        return None


def _heavy_tail_detection(series: pd.Series) -> dict[str, Any]:
    try:
        s = series.dropna().astype(float)
        if len(s) < 10:
            return {"kurtosis": None, "heavy_tail": None}
        kurt = float(scipy_stats.kurtosis(s)) if HAS_SCIPY else float(s.kurtosis())
        return {
            "kurtosis": kurt,
            "heavy_tail": "Yes" if kurt > 3 else "No",
        }
    except Exception:
        return {"kurtosis": None, "heavy_tail": None}


def compute_distribution_diagnostics(df: pd.DataFrame) -> dict[str, Any]:
    out = {"by_column": {}, "summary": {}}
    num = df.select_dtypes(include=[np.number])
    if num.empty:
        return out
    for col in num.columns:
        ser = num[col].dropna()
        if len(ser) < 3:
            continue
        out["by_column"][col] = {
            "shapiro_wilk": _shapiro_wilk(ser),
            "kolmogorov_smirnov": _ks_test(ser),
            "anderson_darling": _anderson_darling(ser),
            "distribution_fitting": _distribution_fitting(ser),
            "symmetry_score": _safe_float(_symmetry_score(ser)),
            "heavy_tail": _heavy_tail_detection(ser),
        }
    if out["by_column"]:
        sym_vals = [v.get("symmetry_score") for v in out["by_column"].values() if v.get("symmetry_score") is not None]
        out["summary"]["mean_symmetry_score"] = float(np.mean(sym_vals)) if sym_vals else None
    return out


# ----- 2) Variability & Stability Metrics -----

def coefficient_of_variation(series: pd.Series) -> float | None:
    s = series.dropna()
    if len(s) < 2 or s.mean() == 0:
        return None
    return float(s.std() / abs(s.mean()) * 100)


def interquartile_dispersion(series: pd.Series) -> float | None:
    try:
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        if q1 == q3:
            return 0.0
        return float((q3 - q1) / (q3 + q1)) if (q3 + q1) != 0 else None
    except Exception:
        return None


def rolling_stability_index(series: pd.Series, window: int = 5) -> float | None:
    if len(series) < window * 2:
        return None
    try:
        roll = series.rolling(window=window, min_periods=1).std()
        roll_mean = series.rolling(window=window, min_periods=1).mean()
        cv_roll = np.where(roll_mean != 0, roll / np.abs(roll_mean), np.nan)
        cv_roll = pd.Series(cv_roll).dropna()
        if len(cv_roll) == 0:
            return None
        stability = 1 - np.minimum(cv_roll.mean(), 1.0)
        return float(np.clip(stability, 0, 1))
    except Exception:
        return None


def volatility_ratio(series: pd.Series) -> float | None:
    if len(series) < 3:
        return None
    try:
        s = series.dropna()
        if len(s) < 3:
            return None
        std = s.std()
        mean_abs_diff = np.abs(s.diff()).mean()
        if mean_abs_diff == 0:
            return None
        return float(std / mean_abs_diff)
    except Exception:
        return None


def cusum_change_points(series: pd.Series, threshold: float = 2.0) -> list[int]:
    """CUSUM-based change point indices (0-based)."""
    if len(series) < 4:
        return []
    try:
        s = series.dropna().values
        mean = np.mean(s)
        cusum = np.cumsum(s - mean)
        std = np.std(s)
        if std == 0:
            return []
        cusum_norm = np.abs(cusum) / (std * np.sqrt(np.arange(1, len(s) + 1)))
        cp = np.where(cusum_norm > threshold)[0]
        return cp.tolist()
    except Exception:
        return []


def compute_variability_metrics(df: pd.DataFrame) -> dict[str, Any]:
    out = {"by_column": {}, "summary": {}}
    num = df.select_dtypes(include=[np.number])
    if num.empty:
        return out
    cvs, iqrs, stabs, vol_ratios = [], [], [], []
    for col in num.columns:
        ser = num[col]
        cv = coefficient_of_variation(ser)
        iqr = interquartile_dispersion(ser)
        stab = rolling_stability_index(ser)
        vol = volatility_ratio(ser)
        cps = cusum_change_points(ser)
        out["by_column"][col] = {
            "coefficient_of_variation_pct": _safe_float(cv),
            "interquartile_coefficient_dispersion": _safe_float(iqr),
            "rolling_stability_index": _safe_float(stab),
            "volatility_ratio": _safe_float(vol),
            "change_point_indices": cps,
        }
        if cv is not None:
            cvs.append(cv)
        if iqr is not None:
            iqrs.append(iqr)
        if stab is not None:
            stabs.append(stab)
        if vol is not None:
            vol_ratios.append(vol)
    out["summary"] = {
        "mean_cv_pct": float(np.mean(cvs)) if cvs else None,
        "mean_iqr_dispersion": float(np.mean(iqrs)) if iqrs else None,
        "mean_rolling_stability": float(np.mean(stabs)) if stabs else None,
        "mean_volatility_ratio": float(np.mean(vol_ratios)) if vol_ratios else None,
    }
    return out


# ----- 3) Multivariate Quality Analysis -----

def compute_multivariate_quality(df: pd.DataFrame) -> dict[str, Any]:
    out = {
        "pca": {},
        "explained_variance_ratio": [],
        "feature_correlation_strength": None,
        "vif_available": False,
        "vif": {},
        "cluster_stability_index": None,
    }
    X = _numeric_matrix(df)
    if X is None or X.shape[1] < 2:
        return out
    try:
        corr = pd.DataFrame(X).corr()
        strength = np.abs(corr.values).mean()
        out["feature_correlation_strength"] = float(strength)
    except Exception:
        pass
    if not HAS_SKLEARN:
        return out
    try:
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)
        n_components = min(5, Xs.shape[1], Xs.shape[0] - 1)
        if n_components < 1:
            return out
        pca = PCA(n_components=n_components)
        pca.fit(Xs)
        out["pca"]["n_components"] = n_components
        out["explained_variance_ratio"] = [float(x) for x in pca.explained_variance_ratio_]
        out["pca"]["explained_variance_total"] = float(np.sum(pca.explained_variance_ratio_))
    except Exception:
        pass
    # Simple VIF via correlation matrix: VIF_j = 1/(1-R^2_j) where R^2 from regressing j on others
    try:
        if X.shape[1] >= 2 and X.shape[0] > X.shape[1]:
            from numpy.linalg import inv
            Xc = X - X.mean(axis=0)
            cov = np.cov(Xc.T)
            if np.linalg.det(cov) != 0:
                inv_cov = inv(cov)
                vif = np.diag(inv_cov) * np.diag(cov)
                num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                for i, c in enumerate(num_cols):
                    if i < len(vif):
                        out["vif"][c] = float(vif[i])
                out["vif_available"] = True
                if out["vif"]:
                    out["multicollinearity_detected"] = any(v > 5 for v in out["vif"].values())
    except Exception:
        pass
    # Cluster stability: run k-means twice and compare labels (rand index or similar)
    try:
        from sklearn.cluster import KMeans
        n_clusters = min(3, X.shape[0] // 3, X.shape[1])
        if n_clusters >= 2:
            km1 = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            km2 = KMeans(n_clusters=n_clusters, random_state=43, n_init=10)
            l1 = km1.fit_predict(X)
            l2 = km2.fit_predict(X)
            agree = (l1 == l2).mean()
            out["cluster_stability_index"] = float(agree)
    except Exception:
        pass
    return out


# ----- 4) Advanced Anomaly Scoring -----

def compute_anomaly_scoring(df: pd.DataFrame) -> dict[str, Any]:
    out = {
        "mahalanobis_distance": {},
        "lof_scores": {},
        "density_anomaly_score": None,
        "anomaly_severity_level": "Low",
        "anomaly_summary": {},
    }
    X = _numeric_matrix(df)
    if X is None or len(X) < 4:
        return out
    n, p = X.shape
    if not HAS_SKLEARN:
        return out
    try:
        cov = EmpiricalCovariance().fit(X)
        md = cov.mahalanobis(X)
        md_mean = np.mean(md)
        md_std = np.std(md)
        out["mahalanobis_distance"] = {
            "mean": float(md_mean),
            "max": float(np.max(md)),
            "std": float(md_std) if md_std > 0 else None,
        }
        # Severity by share of points with high MD
        high_md = (md > md_mean + 2 * md_std).sum() if md_std and md_std > 0 else 0
        pct_high = high_md / n * 100
        if pct_high > 10:
            out["anomaly_severity_level"] = "High"
        elif pct_high > 5:
            out["anomaly_severity_level"] = "Medium"
    except Exception:
        pass
    try:
        n_neighbors = min(20, n - 1, p + 1)
        if n_neighbors < 2:
            return out
        lof = LocalOutlierFactor(n_neighbors=n_neighbors)
        lof.fit(X)
        scores = -lof.negative_outlier_factor_
        out["lof_scores"] = {
            "mean": float(np.mean(scores)),
            "max": float(np.max(scores)),
        }
        out["density_anomaly_score"] = float(np.mean(scores))
        if out["anomaly_severity_level"] == "Low" and np.mean(scores) > 1.5:
            out["anomaly_severity_level"] = "Medium"
        if np.mean(scores) > 2.0:
            out["anomaly_severity_level"] = "High"
    except Exception:
        pass
    out["anomaly_summary"] = {
        "severity": out["anomaly_severity_level"],
        "n_observations": n,
    }
    return out


# ----- 5) Predictive Uncertainty Layer -----

def compute_predictive_uncertainty(kpis: dict, predictions: dict) -> dict[str, Any]:
    """Model error metrics and intervals (placeholder: derived from KPIs/predictions)."""
    out = {
        "confidence_interval_95": {},
        "prediction_interval_width": None,
        "mae": None,
        "rmse": None,
        "mape": None,
        "r_squared": None,
    }
    if not predictions or not kpis:
        return out
    try:
        rel_scores = []
        for sheet in kpis:
            r = kpis[sheet].get("composite_reliability_index")
            if r is not None:
                rel_scores.append(r)
        if rel_scores:
            mean_rel = np.mean(rel_scores)
            std_rel = np.std(rel_scores) if len(rel_scores) > 1 else 0.05
            out["confidence_interval_95"] = {
                "lower": float(max(0, mean_rel - 1.96 * std_rel)),
                "upper": float(min(1, mean_rel + 1.96 * std_rel)),
            }
            out["prediction_interval_width"] = float(2 * 1.96 * std_rel)
        pred_qual = [predictions[s].get("predicted_quality_score") for s in predictions if predictions[s].get("predicted_quality_score") is not None]
        if pred_qual and rel_scores and len(pred_qual) == len(rel_scores):
            pred_qual = np.array(pred_qual)
            actual = np.array(rel_scores[: len(pred_qual)])
            err = actual - pred_qual
            out["mae"] = float(np.abs(err).mean())
            out["rmse"] = float(np.sqrt((err ** 2).mean()))
            out["mape"] = float(np.abs(err / np.clip(actual, 1e-6, None)).mean() * 100) if actual.min() > 0 else None
            ss_res = (err ** 2).sum()
            ss_tot = ((actual - actual.mean()) ** 2).sum()
            out["r_squared"] = float(1 - ss_res / ss_tot) if ss_tot > 0 else None
    except Exception:
        pass
    return out


def compute_quality_dashboard_statistics(
    df: pd.DataFrame,
    kpis: dict | None = None,
    predictions: dict | None = None,
) -> dict[str, Any]:
    """Single entry: run all quality-dashboard advanced statistics for one sheet."""
    out = {
        "distribution_diagnostics": {},
        "variability_metrics": {},
        "multivariate_quality": {},
        "anomaly_scoring": {},
        "predictive_uncertainty": {},
    }
    try:
        out["distribution_diagnostics"] = compute_distribution_diagnostics(df)
    except Exception:
        pass
    try:
        out["variability_metrics"] = compute_variability_metrics(df)
    except Exception:
        pass
    try:
        out["multivariate_quality"] = compute_multivariate_quality(df)
    except Exception:
        pass
    try:
        out["anomaly_scoring"] = compute_anomaly_scoring(df)
    except Exception:
        pass
    if kpis and predictions:
        try:
            out["predictive_uncertainty"] = compute_predictive_uncertainty(kpis, predictions)
        except Exception:
            pass
    return out
