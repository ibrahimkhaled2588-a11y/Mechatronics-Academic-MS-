"""
Cross-Module Advanced Analytics & Executive-Level Additions.
Bayesian updating, HMM placeholder, SHAP/feature impact, significance statements,
effect size, risk confidence, institutional stability, accreditation readiness.
"""
from __future__ import annotations

from typing import Any

import numpy as np


def _safe_float(x: Any) -> float | None:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ----- Bayesian Updating for Quality Scores -----

def bayesian_quality_update(
    prior_mean: float,
    prior_std: float,
    observed_mean: float,
    observed_std: float,
    n_obs: int,
) -> dict[str, Any]:
    """Posterior mean and std for quality score (normal prior, normal likelihood)."""
    if prior_std <= 0:
        prior_std = 0.3
    if n_obs <= 0 or observed_std <= 0:
        return {"posterior_mean": prior_mean, "posterior_std": prior_std}
    prec_prior = 1 / (prior_std ** 2)
    prec_data = n_obs / (observed_std ** 2)
    prec_post = prec_prior + prec_data
    post_std = 1 / np.sqrt(prec_post)
    post_mean = (prec_prior * prior_mean + prec_data * observed_mean) / prec_post
    return {
        "posterior_mean": float(post_mean),
        "posterior_std": float(post_std),
        "prior_mean": prior_mean,
        "observed_mean": observed_mean,
    }


# ----- Hidden Markov Model (placeholder) -----

def hmm_performance_states_placeholder() -> dict[str, Any]:
    """Placeholder: would infer latent states (improving/stable/declining) over time."""
    return {
        "states_inferred": False,
        "message": "HMM requires longitudinal sequence; enable with time-series data.",
    }


# ----- SHAP / Feature Impact (simplified) -----

def feature_impact_waterfall(
    feature_importance: dict[str, float],
    baseline: float = 0.5,
) -> list[dict[str, Any]]:
    """Ordered list of feature contributions (waterfall)."""
    if not feature_importance:
        return []
    items = [{"name": k, "impact": v, "cumulative": None} for k, v in feature_importance.items()]
    items.sort(key=lambda x: -abs(x["impact"]))
    cum = baseline
    for i, it in enumerate(items):
        cum = cum + it["impact"] * 0.2
        it["cumulative"] = float(np.clip(cum, 0, 1))
    return items


# ----- Statistical Significance & Effect Size -----

def cohens_d(group1: list[float], group2: list[float]) -> float | None:
    """Effect size: (mean1 - mean2) / pooled_std."""
    if not group1 or not group2:
        return None
    a, b = np.array(group1), np.array(group2)
    n1, n2 = len(a), len(b)
    s1, s2 = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2)) if (n1 + n2 - 2) > 0 else 0
    if pooled == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / pooled)


def effect_size_interpretation(d: float | None) -> str:
    if d is None:
        return "N/A"
    ad = abs(d)
    if ad < 0.2:
        return "Negligible"
    if ad < 0.5:
        return "Small"
    if ad < 0.8:
        return "Medium"
    return "Large"


# ----- Executive-Level Additions -----

def statistical_significance_statement(p_value: float | None) -> str:
    if p_value is None:
        return "Statistical significance not computed."
    if p_value < 0.001:
        return "p < 0.001 (highly significant)."
    if p_value < 0.05:
        return f"p = {p_value:.3f} (significant at α = 0.05)."
    if p_value < 0.10:
        return f"p = {p_value:.3f} (marginal)."
    return f"p = {p_value:.3f} (not significant at α = 0.05)."


def risk_confidence_statement(risk_probability: float, quality_score: float) -> str:
    """Risk confidence: high when risk is high and quality is low."""
    if risk_probability >= 0.6 and quality_score < 0.7:
        return "High confidence in elevated risk; recommend immediate review."
    if risk_probability >= 0.4:
        return "Moderate confidence in risk; recommend monitoring."
    return "Low risk confidence; data quality supports stability."


def institutional_stability_certificate_score(
    reliability_scores: list[float],
    drift_scores: list[float],
) -> float | None:
    """0-100: high when reliability is high and drift is low."""
    if not reliability_scores:
        return None
    rel = np.mean(reliability_scores)
    drift = np.mean(drift_scores) if drift_scores else 0
    score = rel * 100 - drift * 50
    return float(np.clip(score, 0, 100))


def accreditation_readiness_probability(
    quality_score: float,
    stability_score: float | None,
    equity_score: float | None,
) -> float:
    """Placeholder: probability that program meets accreditation data-quality bar."""
    p = quality_score * 0.5
    if stability_score is not None:
        p += (stability_score / 100.0) * 0.3
    if equity_score is not None:
        eq = equity_score if 0 <= equity_score <= 1 else equity_score / 100.0
        p += eq * 0.2
    return float(np.clip(p, 0, 1))


def compute_cross_module_and_executive(
    kpis: dict[str, Any],
    predictions: dict[str, Any],
    quality_stats: dict[str, Any] | None = None,
    program_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate cross-module analytics and executive-level statements."""
    out = {
        "bayesian_quality": {},
        "hmm_placeholder": hmm_performance_states_placeholder(),
        "feature_impact_waterfall": [],
        "statistical_significance": {},
        "effect_size": {},
        "risk_confidence_statement": None,
        "institutional_stability_certificate_score": None,
        "accreditation_readiness_probability": None,
    }

    # Bayesian update on reliability
    rel_scores = []
    for sheet, kpi in kpis.items():
        r = kpi.get("composite_reliability_index")
        if r is not None:
            rel_scores.append(r)
    if rel_scores:
        obs_mean = float(np.mean(rel_scores))
        obs_std = float(np.std(rel_scores)) if len(rel_scores) > 1 else 0.1
        out["bayesian_quality"] = bayesian_quality_update(0.8, 0.15, obs_mean, obs_std, len(rel_scores))

    # Feature impact — use static_feature_weights (the actual key name in predictions)
    for sheet, pred in (predictions or {}).items():
        fi = pred.get("static_feature_weights") or pred.get("feature_importance") or {}
        if fi:
            out["feature_impact_waterfall"] = feature_impact_waterfall(fi, baseline=float(np.mean(rel_scores)) if rel_scores else 0.5)
            break

    # Statistical significance & effect size between first and last sheet
    sheet_names = list(kpis.keys())
    if len(sheet_names) >= 2 and predictions:
        # Collect reliability scores per sheet to compare
        first_sheet = sheet_names[0]
        last_sheet = sheet_names[-1]
        first_rel = [kpis[first_sheet].get("composite_reliability_index", 0)]
        last_rel = [kpis[last_sheet].get("composite_reliability_index", 0)]
        d = cohens_d(first_rel, last_rel)
        out["effect_size"] = {
            "cohens_d": _safe_float(d),
            "interpretation": effect_size_interpretation(d),
            "first_sheet": first_sheet,
            "last_sheet": last_sheet,
            "first_reliability": round(float(first_rel[0]), 3),
            "last_reliability": round(float(last_rel[0]), 3),
            "direction": "improving" if (last_rel[0] - first_rel[0]) > 0 else "declining" if (last_rel[0] - first_rel[0]) < 0 else "unchanged",
        }

    # Normality test using scipy if available
    try:
        from scipy import stats as scipy_stats
        if rel_scores and len(rel_scores) >= 4:
            stat, p = scipy_stats.normaltest(rel_scores)
            out["statistical_significance"] = {
                "normality_p_value": round(float(p), 4),
                "statement": statistical_significance_statement(float(p)),
                "test": "D'Agostino-Pearson",
            }
        else:
            out["statistical_significance"] = {
                "normality_p_value": None,
                "statement": "Insufficient data points for normality test (need ≥ 4 sheets).",
            }
    except ImportError:
        out["statistical_significance"] = {
            "normality_p_value": None,
            "statement": "Statistical significance not computed (scipy not available).",
        }

    # Risk confidence
    if predictions and kpis:
        risk_probs = [p.get("risk_probability") for p in predictions.values() if p.get("risk_probability") is not None]
        qual_scores = [p.get("predicted_quality_score") for p in predictions.values() if p.get("predicted_quality_score") is not None]
        if risk_probs and qual_scores:
            out["risk_confidence_statement"] = risk_confidence_statement(
                float(np.mean(risk_probs)),
                float(np.mean(qual_scores)),
            )

    # Stability certificate
    if kpis:
        rel = [k.get("composite_reliability_index") for k in kpis.values() if k.get("composite_reliability_index") is not None]
        drift = [k.get("data_drift_score") for k in kpis.values() if k.get("data_drift_score") is not None]
        out["institutional_stability_certificate_score"] = _safe_float(
            institutional_stability_certificate_score(rel, drift)
        )

    # Accreditation readiness
    qual = np.mean(rel) if rel else 0.8
    out["accreditation_readiness_probability"] = accreditation_readiness_probability(
        qual,
        out.get("institutional_stability_certificate_score"),
        program_stats.get("inequality_balance", {}).get("academic_equity_score") if program_stats else None,
    )

    return out
