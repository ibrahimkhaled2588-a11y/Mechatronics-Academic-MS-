"""
Academic Analytics Chatbot — rule-based, fully offline.
Senior QA mindset: analytical, decisive, data-driven, conversational.
Supports multi-turn history and open-ended questions.
"""
from __future__ import annotations

import re
import random
from typing import Any


# ── Utility ─────────────────────────────────────────────────────────────────

def _esc(s: Any) -> str:
    return str(s) if s is not None else "—"

def _fmt(v: Any, d: int = 2, sfx: str = "") -> str:
    return f"{v:.{d}f}{sfx}" if v is not None else "N/A"

def _icon(v: float, good: float, warn: float, invert: bool = False) -> str:
    if invert:
        v = 1.0 - v / 100 if v > 1 else 1.0 - v
    if v >= good: return "✅"
    if v >= warn: return "⚠️"
    return "🔴"

def _weighted_avg(courses: list[dict], key: str) -> float | None:
    tw = tv = 0.0
    for c in courses:
        r = c.get(key)
        w = c.get("total") or c.get("enrollment") or 0
        if r is not None and w > 0:
            fv = r / 100 if key not in ("gpa_estimate",) else r
            tv += fv * w
            tw += w
    if not tw:
        vals = [c[key] for c in courses if c.get(key) is not None]
        return sum(vals) / len(vals) if vals else None
    result = tv / tw
    return result if key not in ("failure_rate", "excellence_rate", "pass_rate") else result * 100


# ── Intent detection ─────────────────────────────────────────────────────────

_INTENTS = [
    ("greeting",        r"\b(hello|hi|hey|good\s*(morning|afternoon|evening)|howdy|مرحبا|أهلا|سلام|صباح|مساء)\b"),
    ("thanks",          r"\b(thank|thanks|appreciate|شكرا|شكراً|ممتاز|عظيم)\b"),
    ("help",            r"\b(help|what can you|what do you|how do (i|you)|capabilities|features|كيف|ماذا تعرف|مساعدة|قدرات)\b"),
    ("about",           r"\b(who are you|what are you|introduce|tell me about yourself|من أنت|عرفني بنفسك)\b"),
    ("summary",         r"\b(summar|overview|overall|big picture|general|status|state|health|ملخص|نظرة|تقرير|الوضع|الحالة)\b"),
    ("gpa",             r"\b(gpa|grade point|average grade|academic average|mean gpa|معدل|المعدل|متوسط الدرجات)\b"),
    ("failure",         r"\b(fail|failure|failing|failed|drop|didn.t pass|رسوب|راسب|فشل|الرسوب|سقط)\b"),
    ("excellence",      r"\b(excell|distinc|honor|outstand|top student|high achiev|best student|تميز|امتياز|متفوق|ممتاز)\b"),
    ("pass",            r"\b(pass rate|passing|passed|success rate|نجاح|ناجح|معدل النجاح)\b"),
    ("enrollment",      r"\b(enroll|student count|how many student|number of student|registr|عدد الطلاب|تسجيل|طلاب|كم طالب)\b"),
    ("quality",         r"\b(quality|reliab|data quality|integrity|clean|جودة|موثوقية|البيانات|نظافة البيانات)\b"),
    ("risk",            r"\b(risk|danger|high.?risk|at.?risk|concern|flagged|خطر|مخاطر|عالي الخطورة|مثير للقلق)\b"),
    ("alerts",          r"\b(alert|warning|critical|issue|problem|flag|anomal|تنبيه|تحذير|حرج|مشكلة|انتباه)\b"),
    ("forecast",        r"\b(forecast|predict|next semester|next period|future|project|expect|trend.*(next|future)|توقع|مستقبل|الفصل القادم|تنبؤ)\b"),
    ("cohort",          r"\b(cohort|retention|dropout|attrition|persist|تسرب|احتفاظ|الاستمرارية|استبقاء)\b"),
    ("variance",        r"\b(variance|inequal|gini|gap|dispersion|spread|decomp|تباين|لامساواة|فجوة|تشتت)\b"),
    ("bayesian",        r"\b(bayesian|posterior|accredit|certif|reliab.*(score|index)|اعتماد|بيزي|مصداقية|شهادة)\b"),
    ("montecarlo",      r"\b(monte.?carlo|simulat|percentile|scenario|stress.?test|محاكاة|احتمال|سيناريو)\b"),
    ("recommendations", r"\b(recommend|action|plan|improve|suggest|what should|what to do|next step|fix|address|توصية|خطة|تحسين|اقتراح|ماذا نفعل|ما العمل)\b"),
    ("trend",           r"\b(trend|growth|momentum|longitudinal|over time|progress|trajectory|اتجاه|نمو|تطور|مسار)\b"),
    ("compare",         r"\b(compar|vs|versus|better|worse|rank|best|worst|top|bottom|مقارنة|مقابل|أفضل|أسوأ|ترتيب)\b"),
    ("course_lookup",   r"\b(course|subject|class|module|مقرر|مادة|كورس|وحدة)\b"),
    ("general_qa",      r"\b(what is|what.?s|define|explain|meaning|how does|why (is|are|do)|ما هو|ما هي|اشرح|وضح|لماذا)\b"),
]
_COMPILED = [(n, re.compile(p, re.IGNORECASE)) for n, p in _INTENTS]


def _detect(question: str) -> str:
    q = question.lower()
    for name, pat in _COMPILED:
        if pat.search(q):
            return name
    return "unknown"


# ── Data extraction helpers ──────────────────────────────────────────────────

def _sheets(ctx: dict) -> list[str]:
    return list((ctx.get("academic_analytics") or {}).keys())

def _all_courses(ctx: dict) -> list[dict]:
    seen: set = set()
    out = []
    for data in (ctx.get("academic_analytics") or {}).values():
        for c in (data.get("all_courses") or []):
            name = c.get("course", "")
            if name and name not in seen:
                seen.add(name)
                out.append(c)
    return out

def _kpis(ctx: dict) -> dict:
    return (ctx.get("metadata") or {}).get("kpis") or {}

def _prog_stats(ctx: dict) -> dict:
    return ctx.get("program_statistics") or {}

def _cross(ctx: dict) -> dict:
    return ctx.get("cross_module_executive") or {}

def _fc(ctx: dict) -> dict:
    return ctx.get("trend_forecast") or {}

def _find_course(q: str, courses: list[dict]) -> dict | None:
    ql = q.lower()
    for c in sorted(courses, key=lambda x: len(x.get("course","") ), reverse=True):
        name = c.get("course", "")
        if name and name.lower() in ql:
            return c
    for c in courses:
        name = c.get("course", "")
        parts = [p for p in re.split(r"[\s\-/]+", name) if len(p) > 3]
        if parts and all(p.lower() in ql for p in parts[:2]):
            return c
    return None


# ── QA utility phrases (adds professional variety) ───────────────────────────

def _qa_opening(level: str = "neutral") -> str:
    if level == "good":
        return random.choice([
            "The data tells a positive story here.",
            "From a QA standpoint, this is an encouraging picture.",
            "Good news on this front —",
            "This indicator is trending in the right direction.",
        ])
    if level == "concern":
        return random.choice([
            "This deserves attention.",
            "A senior QA analyst would flag this immediately.",
            "The data raises a concern here —",
            "This is worth escalating.",
        ])
    if level == "critical":
        return random.choice([
            "This is a red-flag situation.",
            "From an accreditation perspective, this needs immediate action.",
            "The numbers are clear — this cannot be ignored.",
            "Any QA review board would escalate this at once.",
        ])
    return random.choice([
        "Let me walk you through what the data shows.",
        "Here is my read on this:",
        "Breaking this down analytically —",
        "Based on the available evidence:",
    ])


# ── Response handlers ────────────────────────────────────────────────────────

def _h_greeting(q, ctx, history):
    has_data = bool(ctx)
    courses = _all_courses(ctx) if ctx else []
    n_sheets = len(_sheets(ctx)) if ctx else 0

    lines = [
        "Hello — I'm your **Senior Academic QA Analyst**.",
        "",
        "I think analytically, speak plainly, and give you decisions — not just data.",
        "Ask me anything about your academic reports: performance trends, risks, forecasts,",
        "data quality, course-level deep dives, or what actions your department should take.",
        "",
    ]
    if has_data:
        lines.append(f"I can see **{n_sheets} sheet(s)** and **{len(courses)} course(s)** are currently loaded.")
        lines.append("What would you like to explore?")
    else:
        lines.append("No analysis is loaded yet — upload your Excel file on the dashboard, course report,")
        lines.append("or program report page first. Once loaded, I can give you a full QA assessment.")
    return "\n".join(lines)


def _h_thanks(q, ctx, history):
    return random.choice([
        "Glad I could help. What else would you like to examine?",
        "Of course. Any other aspect of the report you'd like me to analyse?",
        "Happy to assist. Keep pushing the questions — that's how quality improves.",
        "That's what I'm here for. Anything else on your mind?",
    ])


def _h_about(q, ctx, history):
    return (
        "I'm an **Academic QA Intelligence Assistant** built specifically for this platform.\n\n"
        "I approach every question with a **senior quality assurance mindset** — meaning:\n"
        "- I don't just report numbers, I interpret what they mean for academic health\n"
        "- I flag risks clearly and suggest specific actions, not vague advice\n"
        "- I hold data quality to the same standard as academic outcomes\n"
        "- I think in terms of accreditation, institutional risk, and continuous improvement\n\n"
        "I can discuss GPA trends, failure rates, cohort dynamics, data reliability,\n"
        "forecast scenarios, course-level profiles, and department-wide strategic decisions.\n\n"
        "What's on your agenda today?"
    )


def _h_help(q, ctx, history):
    return (
        "**Here is what I can do for you:**\n\n"
        "**📊 Performance Analysis**\n"
        "Ask about GPA, failure rates, excellence rates, pass rates — overall or per course.\n"
        "I'll tell you what the numbers mean, not just what they are.\n\n"
        "**⚠️ Risk & Alerts**\n"
        "Which courses are in danger? What does the alert system say?\n"
        "I'll prioritise and explain the severity of each flag.\n\n"
        "**🔬 Advanced Analytics**\n"
        "Cohort retention, dropout risk, Monte Carlo simulations, variance decomposition,\n"
        "Bayesian quality scoring — I can explain and interpret all of it.\n\n"
        "**📈 Trend Forecasting**\n"
        "Where is the program heading next semester? Is it improving or declining?\n"
        "I'll give you a QA verdict with specific actions.\n\n"
        "**📋 Course Deep Dives**\n"
        "Name any course and I'll give you a full QA profile with recommendations.\n\n"
        "**💡 General QA Questions**\n"
        "You can also ask me about academic quality assurance principles, what metrics mean,\n"
        "or how to interpret any part of the report.\n\n"
        "Just ask — no special commands needed."
    )


def _h_summary(q, ctx, history):
    if not ctx:
        return _no_data_response("overall summary")
    courses = _all_courses(ctx)
    sheets = _sheets(ctx)
    gpa = _weighted_avg(courses, "gpa_estimate")
    fail = _weighted_avg(courses, "failure_rate")
    exc = _weighted_avg(courses, "excellence_rate")
    alerts = ctx.get("alerts_detailed") or []
    critical = sum(1 for a in alerts if a.get("severity") == "critical")
    warnings = sum(1 for a in alerts if a.get("severity") == "warning")
    ci = _prog_stats(ctx).get("cohort_intelligence") or {}
    fc = _fc(ctx)
    kpis = _kpis(ctx)
    avg_rel = None
    if kpis:
        rels = [v.get("composite_reliability_index") for v in kpis.values() if v.get("composite_reliability_index") is not None]
        avg_rel = sum(rels) / len(rels) if rels else None

    # QA level
    qa_level = "good"
    if (fail or 0) > 35 or critical > 2 or (gpa or 4) < 2.3:
        qa_level = "critical"
    elif (fail or 0) > 20 or critical > 0 or (gpa or 4) < 2.7:
        qa_level = "concern"

    lines = [
        f"**Program QA Overview — {len(sheets)} semester(s) · {len(courses)} courses**\n",
        f"{_qa_opening(qa_level)}\n",
    ]

    # Core metrics
    if gpa is not None:
        gpa_note = "above standard" if gpa >= 3.0 else "marginal — needs monitoring" if gpa >= 2.5 else "BELOW ACCEPTABLE THRESHOLD"
        lines.append(f"**GPA:** {gpa:.2f} / 4.00 — {gpa_note}")
    if fail is not None:
        fail_note = "within target" if fail <= 15 else "elevated — monitor closely" if fail <= 30 else "CRITICAL — immediate action required"
        lines.append(f"**Failure rate:** {fail:.1f}% — {fail_note}")
    if exc is not None:
        lines.append(f"**Excellence rate:** {exc:.1f}%")
    if avg_rel is not None:
        rel_note = "strong" if avg_rel >= 0.8 else "acceptable" if avg_rel >= 0.6 else "poor — data integrity concern"
        lines.append(f"**Data reliability:** {avg_rel:.2f} / 1.00 — {rel_note}")

    # Cohort
    if ci.get("cohort_retention_rate") is not None:
        ret = ci["cohort_retention_rate"] * 100
        lines.append(f"**Student retention:** {ret:.1f}%")
    if ci.get("dropout_risk_probability") is not None:
        dr = ci["dropout_risk_probability"] * 100
        lines.append(f"**Dropout risk:** {dr:.1f}%")

    # Forecast
    if fc.get("available"):
        gf = fc.get("gpa_forecast") or {}
        nv = (gf.get("predicted_next") or [None])[0]
        if nv is not None:
            dir_ = gf.get("trend_direction", "stable")
            arrow = "↑" if dir_ == "improving" else "↓" if dir_ in ("declining","worsening") else "→"
            lines.append(f"**GPA forecast (next period):** {nv:.2f} {arrow} {dir_}")

    # Alerts summary
    lines.append("")
    if critical:
        lines.append(f"🔴 **{critical} critical alert(s)** — these require immediate attention.")
    if warnings:
        lines.append(f"🟠 **{warnings} warning(s)** — review before next semester.")
    if not critical and not warnings:
        lines.append("✅ No critical or warning alerts. Program is operating within QA thresholds.")

    # QA recommendation
    lines.append("")
    if qa_level == "critical":
        lines.append("**My QA assessment:** This program needs a formal intervention plan. I'd recommend convening a department QA review within the next 30 days.")
    elif qa_level == "concern":
        lines.append("**My QA assessment:** The program is functional but has visible weak spots. Prioritise the high-failure courses and review your data quality pipeline.")
    else:
        lines.append("**My QA assessment:** Overall healthy picture. Focus energy on sustaining the excellence rate and closing the gap on borderline courses.")

    lines.append("\nWant me to go deeper on any specific area?")
    return "\n".join(lines)


def _h_gpa(q, ctx, history):
    if not ctx:
        return _no_data_response("GPA breakdown")
    courses = _all_courses(ctx)
    match = _find_course(q, courses)
    if match:
        return _course_profile(match, ctx)
    avg = _weighted_avg(courses, "gpa_estimate")
    valid = [c for c in courses if c.get("gpa_estimate") is not None]
    best  = max(valid, key=lambda c: c["gpa_estimate"]) if valid else None
    worst = min(valid, key=lambda c: c["gpa_estimate"]) if valid else None

    level = "good" if (avg or 0) >= 3.0 else "concern" if (avg or 0) >= 2.5 else "critical"
    lines = [f"{_qa_opening(level)}\n",
             f"**Weighted average GPA: {_fmt(avg)} / 4.00**\n"]

    # Per-sheet
    for sheet, data in (ctx.get("academic_analytics") or {}).items():
        sc = data.get("all_courses") or []
        sg = _weighted_avg(sc, "gpa_estimate")
        if sg is not None:
            lines.append(f"  • {sheet}: **{sg:.2f}**")

    if best:
        lines.append(f"\n⭐ **Strongest course:** {best['course']} ({best['gpa_estimate']:.2f})")
    if worst:
        lines.append(f"🔴 **Weakest course:** {worst['course']} ({worst['gpa_estimate']:.2f})")

    # QA interpretation
    lines.append("")
    if (avg or 0) < 2.5:
        lines.append("**QA read:** A program GPA below 2.5 is a serious red flag for any accreditation review. The gap between strongest and weakest courses needs immediate investigation — this level of disparity usually points to inconsistent assessment standards or inadequate student support.")
    elif (avg or 0) < 3.0:
        lines.append("**QA read:** GPA is in the marginal zone. Not a crisis, but not comfortable either. I'd focus on the bottom quartile of courses — getting those above 2.7 will move the program average meaningfully.")
    else:
        lines.append("**QA read:** A solid GPA. The main QA concern at this level is maintaining consistency across all courses — high averages can sometimes mask grade inflation. Worth validating that assessment rigour is uniform.")

    return "\n".join(lines)


def _h_failure(q, ctx, history):
    if not ctx:
        return _no_data_response("failure rate analysis")
    courses = _all_courses(ctx)
    match = _find_course(q, courses)
    if match:
        return _course_profile(match, ctx)
    avg = _weighted_avg(courses, "failure_rate")
    ranked = sorted([c for c in courses if c.get("failure_rate") is not None],
                    key=lambda c: c["failure_rate"], reverse=True)
    level = "critical" if (avg or 0) > 35 else "concern" if (avg or 0) > 20 else "good"
    lines = [f"{_qa_opening(level)}\n",
             f"**Overall failure rate: {_fmt(avg, 1)}%**\n",
             "**Ranked by failure rate:**"]
    for c in ranked[:12]:
        fr = c["failure_rate"]
        lo = c.get("failure_rate_ci_lower")
        hi = c.get("failure_rate_ci_upper")
        ci_str = f" [95% CI: {lo:.1f}–{hi:.1f}%]" if lo is not None else ""
        icon = "🔴" if fr > 40 else "🟠" if fr > 25 else "🟡" if fr > 15 else "✅"
        lines.append(f"{icon} **{c['course']}**: {fr:.1f}%{ci_str}")

    fc = _fc(ctx)
    if fc.get("available"):
        ff = fc.get("failure_rate_forecast") or {}
        nv = (ff.get("predicted_next") or [None])[0]
        if nv is not None:
            dir_ = ff.get("trend_direction","stable")
            lines.append(f"\n📈 **Forecast next period:** {nv:.1f}% (trend: {dir_})")

    lines.append("")
    if (avg or 0) > 35:
        lines.append("**QA read:** A program-wide failure rate above 35% is a systemic problem, not isolated underperformance. The intervention must be at the program level — course-by-course patching won't solve this. Review assessment design, teaching methodology, and student readiness simultaneously.")
    elif (avg or 0) > 20:
        lines.append("**QA read:** Above the 20% mark, failure is no longer an individual student problem — it becomes a program quality signal. Identify which courses are driving this and whether they share common instructors, assessment formats, or prerequisite gaps.")
    else:
        lines.append("**QA read:** Failure rate is within a manageable range. Focus on the red-flagged courses above — they are outliers that need individual attention rather than a program-wide intervention.")
    return "\n".join(lines)


def _h_excellence(q, ctx, history):
    if not ctx:
        return _no_data_response("excellence rate data")
    courses = _all_courses(ctx)
    match = _find_course(q, courses)
    if match:
        return _course_profile(match, ctx)
    avg = _weighted_avg(courses, "excellence_rate")
    ranked = sorted([c for c in courses if c.get("excellence_rate") is not None],
                    key=lambda c: c["excellence_rate"], reverse=True)
    lines = [f"**Excellence rate — program average: {_fmt(avg, 1)}%**\n",
             "**Top courses by excellence:**"]
    for c in ranked[:10]:
        exc = c["excellence_rate"]
        lo = c.get("excellence_ci_lower")
        hi = c.get("excellence_ci_upper")
        ci_str = f" [95% CI: {lo:.1f}–{hi:.1f}%]" if lo is not None else ""
        lines.append(f"⭐ **{c['course']}**: {exc:.1f}%{ci_str}")
    if ranked:
        worst_exc = ranked[-1]
        lines.append(f"\n🔴 **Lowest excellence:** {worst_exc['course']} ({worst_exc['excellence_rate']:.1f}%)")

    fc = _fc(ctx)
    if fc.get("available"):
        ef = fc.get("excellence_rate_forecast") or {}
        nv = (ef.get("predicted_next") or [None])[0]
        if nv is not None:
            lines.append(f"\n📈 **Forecast next period:** {nv:.1f}% (trend: {ef.get('trend_direction','stable')})")

    lines.append("")
    if (avg or 0) < 10:
        lines.append("**QA read:** An excellence rate below 10% is concerning from an academic talent pipeline perspective. The program is not producing enough high achievers. Examine whether course design provides sufficient challenge and reward for strong students, or whether the grading scale is too compressed.")
    elif (avg or 0) < 20:
        lines.append("**QA read:** A moderate excellence rate. Not alarming, but there's clear room to improve. Look at the courses with strong excellence rates and ask what they're doing differently — then spread those practices.")
    else:
        lines.append("**QA read:** A healthy excellence rate. The main risk to watch here is grade inflation — make sure high achievement reflects real mastery and not lowered assessment standards.")
    return "\n".join(lines)


def _h_pass(q, ctx, history):
    if not ctx:
        return _no_data_response("pass rate data")
    courses = _all_courses(ctx)
    ranked = sorted([c for c in courses if c.get("pass_rate") is not None],
                    key=lambda c: c["pass_rate"])
    avg = _weighted_avg(courses, "pass_rate")
    lines = [f"**Program pass rate: {_fmt(avg, 1)}%**\n"]
    if ranked:
        lines.append("**Lowest pass rates (most concerning):**")
        for c in ranked[:8]:
            pr = c["pass_rate"]
            lo = c.get("pass_rate_ci_lower")
            hi = c.get("pass_rate_ci_upper")
            ci_str = f" [95% CI: {lo:.1f}–{hi:.1f}%]" if lo is not None else ""
            icon = "🔴" if pr < 60 else "🟠" if pr < 75 else "✅"
            lines.append(f"{icon} **{c['course']}**: {pr:.1f}%{ci_str}")
    lines.append("")
    lines.append("**QA read:** Pass rate is the inverse of failure — but the 95% CI ranges matter here. A course with a 70% pass rate and a wide CI (e.g. 62–78%) has less reliable data than one with a tight CI. Prioritise investigation of courses with both low pass rates AND wide confidence intervals.")
    return "\n".join(lines)


def _h_enrollment(q, ctx, history):
    if not ctx:
        return _no_data_response("enrollment data")
    courses = _all_courses(ctx)
    total = sum((c.get("total") or c.get("enrollment") or 0) for c in courses)
    ranked = sorted(courses, key=lambda c: c.get("total") or c.get("enrollment") or 0, reverse=True)
    lines = [f"**Total student-course registrations: {total:,}**",
             f"**Number of courses: {len(courses)}**\n",
             "**Largest courses (by enrollment):**"]
    for c in ranked[:10]:
        enr = c.get("total") or c.get("enrollment") or 0
        fr = c.get("failure_rate")
        fr_str = f" — failure rate: {fr:.1f}%" if fr is not None else ""
        lines.append(f"• **{c['course']}**: {enr:,} students{fr_str}")
    lines.append("")
    lines.append("**QA read:** Large enrollment courses deserve proportionally more QA attention — a 30% failure rate in a 500-student course means 150 students failing, which is a very different scale of impact than the same rate in a 30-student elective. Always weight your concern by enrollment volume.")
    return "\n".join(lines)


def _h_quality(q, ctx, history):
    if not ctx:
        return _no_data_response("data quality metrics")
    kpis = _kpis(ctx)
    lines = [f"{_qa_opening()}\n", "**Data Quality Assessment — Sheet by Sheet:**\n"]
    for sheet, kpi in kpis.items():
        rel = kpi.get("composite_reliability_index")
        miss = kpi.get("missing_ratio")
        drift = kpi.get("data_drift_score")
        dup = kpi.get("duplicate_rate")
        icon = "✅" if (rel or 0) >= 0.8 else "⚠️" if (rel or 0) >= 0.6 else "🔴"
        lines.append(f"{icon} **{sheet}**")
        if rel is not None:
            verdict = "reliable" if rel >= 0.8 else "acceptable" if rel >= 0.6 else "unreliable — treat results with caution"
            lines.append(f"   Reliability: **{rel:.3f}** ({verdict})")
        if miss is not None:
            lines.append(f"   Missing data: {miss:.2f}%{'  ⚠️' if miss > 5 else ''}")
        if dup is not None:
            lines.append(f"   Duplicates: {dup:.2f}%{'  ⚠️' if dup > 2 else ''}")
        if drift is not None:
            drift_note = "significant — check for data pipeline issues" if drift > 0.2 else "mild" if drift > 0.05 else "stable"
            lines.append(f"   Drift: {drift:.3f} ({drift_note})")

    cm = _cross(ctx)
    bq = cm.get("bayesian_quality") or {}
    if bq.get("posterior_mean"):
        pm = bq["posterior_mean"]
        lines.append(f"\n**Bayesian reliability posterior: {pm*100:.1f}%** (±{bq.get('posterior_std',0)*100:.1f}%)")
    if cm.get("accreditation_readiness_probability") is not None:
        ar = cm["accreditation_readiness_probability"]
        icon = "✅" if ar >= 0.75 else "⚠️" if ar >= 0.55 else "🔴"
        lines.append(f"{icon} **Accreditation readiness: {ar*100:.1f}%**")

    lines.append("")
    lines.append("**QA read:** Data quality is often the silent killer of academic analytics. If your reliability index is below 0.7, I'd treat every derived metric — GPA, failure rates, risk scores — with a margin of scepticism. Fix the data before acting on the conclusions.")
    return "\n".join(lines)


def _h_risk(q, ctx, history):
    if not ctx:
        return _no_data_response("risk analysis")
    all_risks: list[dict] = []
    for sheet, data in (ctx.get("course_risk") or {}).items():
        for course, risk in (data.get("course_risk") or {}).items():
            all_risks.append({"course": course, "risk": (risk or 0) * 100})
    all_risks.sort(key=lambda x: x["risk"], reverse=True)
    high = [r for r in all_risks if r["risk"] >= 60]
    med  = [r for r in all_risks if 35 <= r["risk"] < 60]
    low  = [r for r in all_risks if r["risk"] < 35]

    level = "critical" if len(high) > 3 else "concern" if high else "good"
    lines = [f"{_qa_opening(level)}\n"]

    if high:
        lines.append(f"🔴 **{len(high)} HIGH-RISK course(s)** — these need immediate attention:\n")
        for r in high[:10]:
            lines.append(f"  • **{r['course']}**: {r['risk']:.1f}% risk score")
    else:
        lines.append("✅ No courses exceed the 60% high-risk threshold.\n")
    if med:
        lines.append(f"\n🟠 **{len(med)} MODERATE-RISK course(s)** — monitor closely:\n")
        for r in med[:6]:
            lines.append(f"  • **{r['course']}**: {r['risk']:.1f}% risk score")
    lines.append(f"\n✅ **{len(low)} low-risk course(s)** operating normally.")

    ci = _prog_stats(ctx).get("cohort_intelligence") or {}
    if ci.get("dropout_risk_probability") is not None:
        dr = ci["dropout_risk_probability"] * 100
        lines.append(f"\n**Program-wide dropout risk: {dr:.1f}%**")

    lines.append("")
    if high:
        lines.append(f"**QA read:** {len(high)} high-risk courses is not a coincidence — it's a pattern. Before diving into individual course fixes, I'd look for what these courses have in common: same instructor pool? Same semester? Same student cohort? Pattern recognition here is more valuable than isolated interventions.")
    else:
        lines.append("**QA read:** Risk scores are healthy. The real task now is early detection — make sure your monitoring catches emerging problems before they become high-risk. Monthly failure rate spot-checks would be my recommendation.")
    return "\n".join(lines)


def _h_alerts(q, ctx, history):
    if not ctx:
        return _no_data_response("alert data")
    alerts = ctx.get("alerts_detailed") or []
    if not alerts:
        plain = ctx.get("alerts") or []
        if plain:
            lines = ["**Alerts:**"]
            for a in plain[:10]:
                lines.append(f"• {a}")
            return "\n".join(lines)
        return "✅ **No alerts generated.** All metrics are within acceptable thresholds.\n\n**QA read:** A clean alert board is good news, but don't mistake silence for safety. Make sure your thresholds are calibrated — overly lenient thresholds produce false comfort."

    crit = [a for a in alerts if a.get("severity") == "critical"]
    warn = [a for a in alerts if a.get("severity") == "warning"]
    info = [a for a in alerts if a.get("severity") == "info"]
    lines = [f"**{len(alerts)} alert(s) — {len(crit)} critical · {len(warn)} warning · {len(info)} info**\n"]

    if crit:
        lines.append("🔴 **CRITICAL — Requires immediate action:**")
        for a in crit[:8]:
            lines.append(f"  • {a['message']}")
    if warn:
        lines.append("\n🟠 **WARNINGS — Action before next semester:**")
        for a in warn[:8]:
            lines.append(f"  • {a['message']}")
    if info:
        lines.append("\n🔵 **INFORMATIONAL — Be aware:**")
        for a in info[:4]:
            lines.append(f"  • {a['message']}")

    lines.append("")
    if crit:
        lines.append(f"**QA read:** {len(crit)} critical alert(s) means this report cannot be filed and forgotten. Each critical flag should have a named owner and a resolution date assigned before this week is out. Unresolved critical alerts at the next review cycle is a governance failure.")
    else:
        lines.append("**QA read:** No critical alerts is a good position. Clear the warnings systematically — each one is a crack in the foundation that becomes structural if left too long.")
    return "\n".join(lines)


def _h_forecast(q, ctx, history):
    if not ctx:
        return _no_data_response("forecast data")
    fc = _fc(ctx)
    if not fc.get("available"):
        reason = fc.get("reason") or "requires at least 2 semester sheets"
        return (
            f"**Forecast not available** — {reason}\n\n"
            "Upload data from 2 or more semesters to enable OLS trend forecasting.\n\n"
            "**QA note:** Operating without forecast data is like driving without a windscreen. Even two data points give you directional information. Prioritise getting multi-semester data into the system."
        )

    sheets = fc.get("sheet_count", "?")
    lines = [f"**Trend Forecast — QA Action Decisions** _(OLS across {sheets} semester(s))_\n"]
    bad_count = 0

    def _qa_gpa(val, dir_):
        if dir_ in ("declining","worsening"):
            if val < 2.0: return "CRITICAL", "🔴", "Immediate escalation. GPA below minimum threshold — emergency committee review required."
            if val < 2.5: return "HIGH RISK", "🔴", "Trigger departmental intervention. Assign advisors to at-risk cohorts and schedule progress reviews."
            return "WATCH", "🟠", "Place on QA watch-list. Notify department head and review teaching effectiveness scores."
        if dir_ == "stable":
            if val >= 3.0: return "ACCEPTABLE", "✅", "No action required. Maintain current approach and schedule routine end-of-semester review."
            return "BORDERLINE", "🟠", "Marginal but stable. Issue a precautionary advisory and increase monitoring to bi-weekly."
        if val >= 3.0: return "STRONG", "✅", "Above benchmark. Document current practices as templates for other programs."
        return "IMPROVING", "✅", "Positive trajectory. Reinforce current support structures and audit contributing factors."

    def _qa_fail(val, dir_):
        if dir_ in ("worsening","increasing"):
            if val > 50: return "CRITICAL", "🔴", "Program integrity at risk. Halt new enrolments pending full audit. Escalate to accreditation officer."
            if val > 35: return "HIGH RISK", "🔴", "Red zone. Mandate supplementary sessions, review assessment design, implement early-warning protocol."
            if val > 20: return "ELEVATED", "🟠", "Rising beyond acceptable band. Formal quality alert issued. Coordinators submit remediation plan within 14 days."
            return "WATCH", "🟠", "Log in QA register. Schedule targeted course review at semester end."
        if dir_ == "stable":
            if val <= 15: return "ACCEPTABLE", "✅", "Stable within target range. Continue standard monitoring."
            return "BORDERLINE", "🟠", "Stable but above preferred ceiling. Heightened monitoring. Include in next quality report."
        if val <= 10: return "EXCELLENT", "✅", "Healthy and improving. Validate against grade inflation risk — confirm assessment rigour."
        return "IMPROVING", "✅", "Declining — interventions are working. Document and continue current strategy."

    def _qa_exc(val, dir_):
        if dir_ in ("declining","worsening"):
            if val < 5: return "CRITICAL", "🔴", "Near-zero excellence. Review assessment design — may be suppressing high achievement."
            if val < 10: return "CONCERN", "🟠", "Excellence pipeline thinning. Introduce enrichment tracks and engage high-potential students."
            return "WATCH", "🟠", "Declining trend logged. Advisory to teaching staff. Review stretch goals and top-performer support."
        if dir_ == "stable":
            if val >= 20: return "STRONG", "✅", "High and stable. No action required. Document academic culture factors."
            return "ACCEPTABLE", "✅", "Stable and typical. No action required."
        if val >= 20: return "EXCELLENT", "✅", "High and improving. Consider nominating for institutional recognition."
        return "IMPROVING", "✅", "Trending upward. Reinforce practices and share as a model for underperforming programs."

    for key, label, unit, fn in [
        ("gpa_forecast", "GPA", "/ 4.00", _qa_gpa),
        ("failure_rate_forecast", "Failure Rate", "%", _qa_fail),
        ("excellence_rate_forecast", "Excellence Rate", "%", _qa_exc),
    ]:
        fd = fc.get(key) or {}
        nv = (fd.get("predicted_next") or [None])[0]
        if nv is None:
            continue
        dir_ = fd.get("trend_direction","stable")
        r2   = fd.get("r_squared")
        status, sev_icon, action = fn(nv, dir_)
        if status in ("CRITICAL","HIGH RISK","ELEVATED","WATCH","BORDERLINE","CONCERN"):
            bad_count += 1
        r2s = f" · R²={r2:.2f}" if r2 is not None else ""
        fmt_val = f"{nv:.2f} {unit}" if label == "GPA" else f"{nv:.1f}{unit}"
        lines += [
            f"{sev_icon} **{label}: {fmt_val}** · Trend: {dir_}{r2s}",
            f"   Status: **{status}**",
            f"   Action: {action}",
            "",
        ]

    # Verdict
    if bad_count == 0:
        lines.append("✅ **QA VERDICT: PASS** — All indicators within bounds. Standard monitoring continues.")
    elif bad_count == 1:
        lines.append("🟠 **QA VERDICT: CONDITIONAL PASS** — One indicator needs attention before the next review cycle.")
    elif bad_count == 2:
        lines.append("🔴 **QA VERDICT: REQUIRES INTERVENTION** — Two indicators off-track. Escalate to department head within 30 days.")
    else:
        lines.append("🚨 **QA VERDICT: PROGRAM UNDER REVIEW** — All indicators signal deterioration. Emergency board session required.")

    return "\n".join(lines)


def _h_cohort(q, ctx, history):
    if not ctx:
        return _no_data_response("cohort data")
    ci = _prog_stats(ctx).get("cohort_intelligence") or {}
    if not ci:
        return "Cohort intelligence data is not available for this dataset."
    lines = [f"{_qa_opening()}\n", "**Cohort Intelligence Analysis:**\n"]
    ret  = ci.get("cohort_retention_rate")
    drop = ci.get("dropout_risk_probability")
    rec  = ci.get("academic_recovery_rate")
    curve = ci.get("cohort_performance_curve") or []

    if ret  is not None: lines.append(f"{'✅' if ret>=0.8 else '🟠' if ret>=0.65 else '🔴'} **Retention rate: {ret*100:.1f}%**")
    if drop is not None: lines.append(f"{'✅' if drop<0.15 else '🟠' if drop<0.3 else '🔴'} **Dropout risk: {drop*100:.1f}%**")
    if rec  is not None: lines.append(f"{'✅' if rec>=0.7 else '🟠' if rec>=0.5 else '🔴'} **Academic recovery rate: {rec*100:.1f}%**")
    if len(curve) > 1:
        lines.append(f"\nPerformance curve: {' → '.join(f'{g:.2f}' for g in curve)}")
        trend = "improving" if curve[-1] > curve[0] else "declining" if curve[-1] < curve[0] else "stable"
        lines.append(f"Overall cohort trajectory: **{trend}**")

    lines.append("")
    if (drop or 0) > 0.3:
        lines.append("**QA read:** A dropout risk above 30% is an institutional alarm bell. Students don't drop out for one reason — this is usually a convergence of academic struggle, financial pressure, and disengagement. The academic recovery rate tells you whether your support systems are working. If it's below 50%, they're not.")
    elif (ret or 1) < 0.7:
        lines.append("**QA read:** Retention below 70% means you're losing a significant portion of your student body. Before attributing this to academic performance alone, investigate whether student support services, advisory systems, and early-intervention triggers are functioning as intended.")
    else:
        lines.append("**QA read:** Cohort metrics are in a reasonable range. The performance curve direction is what I'd watch most closely — a consistently declining curve across semesters signals a systemic issue that course-level fixes won't resolve.")
    return "\n".join(lines)


def _h_variance(q, ctx, history):
    if not ctx:
        return _no_data_response("variance data")
    ineq = _prog_stats(ctx).get("inequality_balance") or {}
    vd   = ineq.get("variance_decomposition") or {}
    if not ineq:
        return "Variance decomposition data is not available for this dataset."
    lines = [f"{_qa_opening()}\n", "**Academic Inequality & Variance Analysis:**\n"]
    if ineq.get("gpa_inequality_index") is not None:
        gi = ineq["gpa_inequality_index"]
        gi_note = "highly equal" if gi < 0.2 else "moderate inequality" if gi < 0.4 else "significant inequality — equity concern"
        lines.append(f"• **Gini inequality index: {gi:.3f}** — {gi_note}")
    if ineq.get("course_difficulty_dispersion") is not None:
        lines.append(f"• Course difficulty dispersion: **{ineq['course_difficulty_dispersion']:.2f}**")
    if ineq.get("academic_equity_score") is not None:
        eq = ineq["academic_equity_score"]
        lines.append(f"{'✅' if eq>=0.7 else '🟠' if eq>=0.5 else '🔴'} **Academic equity score: {eq:.3f}**")
    if vd.get("between_course_variance") is not None:
        bv = vd["between_course_variance"]
        wv = vd.get("within_course_variance", 0) or 0
        tot = (bv + wv) or 1
        lines.append(f"\n• Between-course variance: **{bv:.4f}** ({bv/tot*100:.1f}% of total)")
        lines.append(f"• Within-course variance:  **{wv:.4f}** ({wv/tot*100:.1f}% of total)")
        if bv > wv:
            lines.append("\n_Between-course variance dominates — course selection and difficulty calibration is the primary equity issue._")
        else:
            lines.append("\n_Within-course variance dominates — student preparation and individual support is the primary concern._")

    lines.append("")
    lines.append("**QA read:** High between-course variance often signals inconsistent assessment standards or wildly different course difficulty levels. From an accreditation perspective, this is a programme coherence issue. High within-course variance, by contrast, points to student-level heterogeneity — which requires different interventions.")
    return "\n".join(lines)


def _h_bayesian(q, ctx, history):
    if not ctx:
        return _no_data_response("Bayesian quality data")
    cm = _cross(ctx)
    bq = cm.get("bayesian_quality") or {}
    if not bq:
        return "Bayesian quality data is not available for this dataset."
    lines = [f"{_qa_opening()}\n", "**Bayesian Data Quality Assessment:**\n"]
    if bq.get("posterior_mean") is not None:
        pm = bq["posterior_mean"]
        ps = bq.get("posterior_std", 0) or 0
        verdict = "highly reliable" if pm >= 0.85 else "acceptable" if pm >= 0.7 else "questionable — proceed with caution"
        lines.append(f"{'✅' if pm>=0.8 else '🟠' if pm>=0.65 else '🔴'} **Posterior reliability: {pm*100:.1f}% ± {ps*100:.1f}%** — {verdict}")
        lines.append(f"  Prior belief: {bq.get('prior_mean',0)*100:.0f}%  →  Observed: {bq.get('observed_mean',0)*100:.1f}%  →  Updated posterior: {pm*100:.1f}%")
    if cm.get("accreditation_readiness_probability") is not None:
        ar = cm["accreditation_readiness_probability"]
        lines.append(f"\n{'✅' if ar>=0.75 else '🟠' if ar>=0.55 else '🔴'} **Accreditation readiness: {ar*100:.1f}%**")
    if cm.get("institutional_stability_certificate_score") is not None:
        sc = cm["institutional_stability_certificate_score"]
        lines.append(f"• Institutional stability score: **{sc:.1f} / 100**")
    if cm.get("risk_confidence_statement"):
        lines.append(f"\n_{cm['risk_confidence_statement']}_")

    lines.append("")
    lines.append("**QA read:** The Bayesian posterior is the most honest data quality signal we have — it combines our prior expectations with actual observed data. A large gap between prior and posterior means the data surprised us, which is either good news (better than expected) or a red flag (worse than expected). The direction matters as much as the value.")
    return "\n".join(lines)


def _h_montecarlo(q, ctx, history):
    if not ctx:
        return _no_data_response("Monte Carlo simulation data")
    mc = _prog_stats(ctx).get("monte_carlo_simulation") or {}
    if not mc:
        return "Monte Carlo simulation data is not available for this dataset."
    lines = [f"{_qa_opening()}\n", "**Monte Carlo Simulation — 1,000 Scenarios:**\n"]
    if mc.get("simulated_mean_final_gpa") is not None:
        lines.append(f"• **Mean simulated GPA: {mc['simulated_mean_final_gpa']:.2f}**")
    if mc.get("percentile_5") is not None:
        lines.append(f"• **Pessimistic scenario (5th percentile): {mc['percentile_5']:.2f}**")
    if mc.get("percentile_95") is not None:
        lines.append(f"• **Optimistic scenario (95th percentile): {mc['percentile_95']:.2f}**")
    if mc.get("p_below_2") is not None:
        p = mc["p_below_2"] * 100
        lines.append(f"{'🔴' if p>15 else '🟠' if p>5 else '✅'} **Probability of GPA < 2.0: {p:.1f}%**")
    if mc.get("p_above_3") is not None:
        lines.append(f"• **Probability of GPA ≥ 3.0: {mc['p_above_3']*100:.1f}%**")
    st = mc.get("stress_test") or {}
    wc = st.get("stress_percentile_95") or st.get("worst_case_overall_failure_pct")
    if wc is not None:
        lines.append(f"• **Stress test (worst-case failure): {wc:.1f}%**")

    lines.append("")
    spread = None
    if mc.get("percentile_5") and mc.get("percentile_95"):
        spread = mc["percentile_95"] - mc["percentile_5"]
    if spread is not None:
        if spread > 1.0:
            lines.append(f"**QA read:** A spread of {spread:.2f} GPA points between the 5th and 95th percentile scenarios tells you this program is highly sensitive to variation. Small changes in input conditions produce very different outcomes. That's an inherently fragile system — it needs more structural consistency to narrow that band.")
        else:
            lines.append(f"**QA read:** A {spread:.2f}-point spread across 1,000 simulations suggests the program is relatively stable and predictable. Even in bad-luck scenarios, outcomes don't deviate dramatically. That's a sign of structural resilience — the foundation is solid.")
    else:
        lines.append("**QA read:** The Monte Carlo spread between optimistic and pessimistic scenarios is your resilience indicator. A narrow spread means structural stability; a wide spread means you're one bad semester away from a significant quality dip.")
    return "\n".join(lines)


def _h_recommendations(q, ctx, history):
    if not ctx:
        return _no_data_response("action plan data")
    plans = ctx.get("course_plans") or {}
    if not plans:
        return "No action plans are available. Upload your analysis file to generate course-specific recommendations."
    flat: dict[str, dict] = {}
    for sp in plans.values():
        for p in sp:
            name = p.get("course","")
            if name and (name not in flat or (p.get("risk_percent",0) > flat[name].get("risk_percent",0))):
                flat[name] = p
    top = sorted(flat.values(), key=lambda p: p.get("risk_percent",0), reverse=True)
    high = [p for p in top if p.get("risk_level") in ("high","medium")][:6]
    if not high:
        return "✅ **No high or medium-risk courses with pending action plans.**\n\nAll courses appear within acceptable risk ranges. My recommendation: maintain current monitoring cadence and review again after the next assessment cycle."

    lines = [f"**Priority Action Plans — Top {len(high)} At-Risk Courses:**\n"]
    for i, p in enumerate(high, 1):
        risk = p.get("risk_percent", 0)
        lvl = p.get("risk_level","").upper()
        icon = "🔴" if lvl == "HIGH" else "🟠"
        lines.append(f"{icon} **{i}. {p['course']}** — {lvl} risk ({risk:.0f}%)")
        for a in (p.get("action_plan") or [])[:3]:
            lines.append(f"   → {a}")
        lines.append("")

    lines.append("**QA read:** Action plans only matter if they get implemented. Each item above should have a named responsible person, a timeline, and a follow-up review date. A plan without accountability is just documentation.")
    return "\n".join(lines)


def _h_trend(q, ctx, history):
    if not ctx:
        return _no_data_response("trend and longitudinal data")
    long = _prog_stats(ctx).get("longitudinal_growth") or {}
    fc = _fc(ctx)
    lines = [f"{_qa_opening()}\n", "**Longitudinal Growth & Momentum:**\n"]
    has_data = False
    if long.get("cagr_gpa") is not None:
        cagr = long["cagr_gpa"] * 100
        lines.append(f"{'📈' if cagr>0 else '📉'} GPA CAGR per semester: **{cagr:+.2f}%**")
        has_data = True
    if long.get("growth_rate_excellence") is not None:
        gr = long["growth_rate_excellence"] * 100
        lines.append(f"• Excellence growth rate: **{gr:+.1f}%**")
    if long.get("failure_trend_acceleration") is not None:
        acc = long["failure_trend_acceleration"]
        lines.append(f"{'🔴' if acc>0 else '✅'} Failure trend acceleration: **{acc:+.3f}** ({'rising' if acc>0 else 'falling'})")
    if long.get("program_momentum_score") is not None:
        mom = long["program_momentum_score"]
        lines.append(f"{'✅' if mom>=0.6 else '🟠' if mom>=0.4 else '🔴'} Program momentum score: **{mom:.2f} / 1.00**")

    if fc.get("available"):
        lines.append("\n**OLS Forecast (next period):**")
        for key, lbl, unit in [("gpa_forecast","GPA","/ 4.00"),("failure_rate_forecast","Failure","%"),("excellence_rate_forecast","Excellence","%")]:
            fd = fc.get(key) or {}
            nv = (fd.get("predicted_next") or [None])[0]
            if nv is not None:
                lines.append(f"  • {lbl}: **{nv:.2f} {unit}** (trend: {fd.get('trend_direction','N/A')})")
    elif len(_sheets(ctx)) < 2:
        lines.append("\n_Upload 2+ semesters to enable OLS trend forecasting._")

    if not has_data:
        return "Longitudinal growth data requires data from multiple semesters. Upload at least 2 semester files."

    lines.append("")
    mom = long.get("program_momentum_score")
    acc = long.get("failure_trend_acceleration", 0) or 0
    if (mom or 0) < 0.4 or acc > 0.05:
        lines.append("**QA read:** Low momentum combined with rising failure acceleration is the academic equivalent of a vehicle losing speed while heading toward a cliff. The time to intervene is now — not after the next data cycle. What's driving the deceleration needs to be diagnosed immediately.")
    elif (mom or 0) >= 0.7:
        lines.append("**QA read:** Strong momentum is genuinely good news, but don't coast. Programs that stop improving tend to start declining. Channel this momentum into raising the floor for underperforming courses rather than celebrating the ceiling.")
    else:
        lines.append("**QA read:** Moderate momentum — the program is moving, but not at a pace that would satisfy a rigorous QA review. Identify the two or three interventions with the highest potential impact and pursue them deliberately this semester.")
    return "\n".join(lines)


def _h_compare(q, ctx, history):
    if not ctx:
        return _no_data_response("comparison data")
    courses = _all_courses(ctx)
    if not courses:
        return "No course data is available to compare."
    by_gpa  = sorted([c for c in courses if c.get("gpa_estimate") is not None], key=lambda c: c["gpa_estimate"], reverse=True)
    by_fail = sorted([c for c in courses if c.get("failure_rate") is not None], key=lambda c: c["failure_rate"], reverse=True)
    lines = ["**Course Rankings — QA Comparative View:**\n",
             "**Top 5 by GPA:**"]
    for c in by_gpa[:5]:
        lines.append(f"  ⭐ {c['course']}: **{c['gpa_estimate']:.2f}**")
    lines.append("\n**Bottom 5 by GPA:**")
    for c in by_gpa[-5:]:
        lines.append(f"  🔴 {c['course']}: **{c['gpa_estimate']:.2f}**")
    lines.append("\n**Top 5 by failure rate:**")
    for c in by_fail[:5]:
        lines.append(f"  🔴 {c['course']}: **{c['failure_rate']:.1f}%**")
    gap = by_gpa[0]["gpa_estimate"] - by_gpa[-1]["gpa_estimate"] if len(by_gpa) > 1 else 0
    lines.append("")
    lines.append(f"**QA read:** The GPA gap between your best and worst courses is **{gap:.2f} points**. "
                 + ("That's a wide disparity — accreditors will notice this. Investigate whether it reflects genuine curriculum differences or inconsistent assessment standards." if gap > 1.0
                    else "That's a manageable spread. Focus on closing the bottom tier rather than worrying about the overall range."))
    return "\n".join(lines)


def _h_course_lookup(q, ctx, history):
    if not ctx:
        return _no_data_response("course data")
    courses = _all_courses(ctx)
    match = _find_course(q, courses)
    if not match:
        names = sorted({c.get("course","") for c in courses if c.get("course")})
        sample = names[:15]
        more = f" (+{len(names)-15} more)" if len(names) > 15 else ""
        return ("I couldn't identify a specific course in your question.\n\n"
                "Available courses:\n• " + "\n• ".join(sample) + more +
                "\n\nTry: _'Tell me about [course name]'_ or just type the course name.")
    return _course_profile(match, ctx)


def _h_general_qa(q, ctx, history):
    q_lower = q.lower()
    # GPA definition
    if "what is gpa" in q_lower or "gpa mean" in q_lower or "gpa stand" in q_lower:
        return ("**GPA (Grade Point Average)** is a numerical summary of academic performance, typically on a 4.0 scale.\n\n"
                "In a QA context, GPA serves as a proxy for programme-level learning outcomes. A GPA below 2.5 programme-wide "
                "typically signals a systemic problem — it's the aggregate outcome of hundreds of individual course-level decisions on grading, "
                "assessment design, and student support. Always interpret GPA alongside failure rates and data quality scores.")
    if "what is failure rate" in q_lower or "failure rate mean" in q_lower:
        return ("**Failure rate** is the percentage of enrolled students who did not achieve a passing grade in a course or programme.\n\n"
                "From a QA perspective:\n"
                "- Below 15%: acceptable range\n"
                "- 15–25%: elevated — warrants monitoring\n"
                "- 25–40%: concerning — formal review recommended\n"
                "- Above 40%: critical — immediate intervention required\n\n"
                "Context matters enormously. A 35% failure rate in a known high-difficulty gateway course is very different from 35% in an introductory elective.")
    if "confidence interval" in q_lower or "what is ci" in q_lower or "95%" in q_lower:
        return ("A **95% confidence interval (CI)** means: if you repeated this measurement many times, 95% of the resulting intervals would contain the true value.\n\n"
                "In academic analytics, wide CIs mean small sample sizes — the result is less reliable. "
                "Narrow CIs mean more data and higher confidence.\n\n"
                "**QA read:** Always look at the CI width, not just the point estimate. "
                "A course with a 28% failure rate [CI: 15–41%] is very different from one with 28% [CI: 25–31%]. "
                "The first might be fine or catastrophic depending on reality. The second is reliably concerning.")
    if "what is gini" in q_lower or "gini index" in q_lower or "gini coeffic" in q_lower:
        return ("The **Gini index** (0 to 1) measures inequality in a distribution.\n\n"
                "In academic analytics: a Gini index near 0 means all courses have similar GPA outcomes (equal). "
                "Near 1 means extreme concentration — some courses perform far better than others.\n\n"
                "**QA read:** A high Gini index in academic performance usually signals two things: "
                "either the curriculum has very deliberate difficulty stratification (intentional), "
                "or assessment standards vary widely across courses (a quality problem).")
    if "accredit" in q_lower:
        return ("**Accreditation** is the formal process by which an external body evaluates whether a programme meets defined quality standards.\n\n"
                "From a QA analyst's perspective, accreditation readiness depends on:\n"
                "- Consistent learning outcomes across courses\n"
                "- Data quality and integrity of reporting\n"
                "- Evidence of systematic improvement processes\n"
                "- Failure and retention rates within acceptable thresholds\n"
                "- Documentation of interventions and their outcomes\n\n"
                "The accreditation readiness score in this system is a composite probabilistic estimate based on these factors.")
    if "monte carlo" in q_lower:
        return ("**Monte Carlo simulation** is a computational technique that runs thousands of randomised scenarios to estimate the probability distribution of outcomes.\n\n"
                "In academic analytics: we simulate 1,000 different possible futures for the programme's GPA by introducing controlled randomness into the model. "
                "This gives us a range — the 5th percentile is a pessimistic scenario, the 95th percentile is an optimistic one.\n\n"
                "**QA read:** The spread between these percentiles is your resilience indicator. A wide spread means the programme's outcomes are highly sensitive to variation — a fragile system.")
    if "bayesian" in q_lower:
        return ("**Bayesian statistics** updates beliefs based on new evidence, starting from a prior belief (what we expected) and adjusting toward a posterior (what the data shows).\n\n"
                "In data quality assessment: we start with a prior expectation about data reliability, observe the actual data characteristics (missing rates, drift, duplicates), "
                "and compute a posterior reliability estimate.\n\n"
                "**QA read:** The posterior is more trustworthy than either the prior or the raw observed rate alone — it balances expectation with evidence. "
                "A large gap between prior and posterior means the data significantly surprised us.")
    # Generic QA principles
    return ("That's a good question. Let me give you my analytical take:\n\n"
            "In quality assurance, the principle is always: **measure, interpret, act, verify**.\n\n"
            "If you have specific data loaded, I can give you a concrete answer grounded in your numbers. "
            "If you're asking about a general QA concept, try rephrasing with more specifics — "
            "for example: _'What does a high Gini index mean?'_ or _'How should I interpret a confidence interval?'_\n\n"
            "What would you like to dig into?")


def _h_unknown(q, ctx, history):
    if history and len(history) > 2:
        return ("I want to make sure I give you a useful answer here.\n\n"
                "Could you rephrase that? I can discuss:\n"
                "- Specific metrics: GPA, failure rates, excellence, pass rates, enrollment\n"
                "- Risk and alerts: which courses are flagged and why\n"
                "- Forecast and trends: where the program is heading\n"
                "- Data quality: reliability, drift, Bayesian quality scoring\n"
                "- Cohort dynamics: retention, dropout risk, recovery\n"
                "- Advanced analytics: Monte Carlo, variance decomposition, Bayesian quality\n"
                "- Any specific course by name\n\n"
                "What would you like to explore?")
    return ("I didn't catch that. I can give you a deep analytical answer on:\n\n"
            "**Performance:** GPA · failure rates · excellence · pass rates · enrollment\n"
            "**Risk:** high-risk courses · alerts · dropout risk · intervention plans\n"
            "**Analytics:** forecasts · cohort trends · Monte Carlo · variance · Bayesian quality\n"
            "**Course profiles:** just type the course name\n"
            "**QA concepts:** ask me to explain any metric or methodology\n\n"
            "Try asking something like: _'Which courses are in the most danger?'_ "
            "or _'What does the forecast say about next semester?'_")


# ── Course profile ───────────────────────────────────────────────────────────

def _course_profile(c: dict, ctx: dict) -> str:
    name = c.get("course","?")
    lines = [f"**QA Profile: {name}**\n"]

    fr = c.get("failure_rate")
    gpa = c.get("gpa_estimate")
    exc = c.get("excellence_rate")
    pr = c.get("pass_rate")
    enr = c.get("total") or c.get("enrollment")
    vol = c.get("volatility_index")

    if gpa is not None:
        lines.append(f"• **GPA:** {gpa:.2f} / 4.00")
    if fr is not None:
        lo, hi = c.get("failure_rate_ci_lower"), c.get("failure_rate_ci_upper")
        ci_str = f" [95% CI: {lo:.1f}–{hi:.1f}%]" if lo is not None else ""
        icon = "🔴" if fr > 40 else "🟠" if fr > 25 else "🟡" if fr > 15 else "✅"
        lines.append(f"{icon} **Failure rate:** {fr:.1f}%{ci_str}")
    if exc is not None:
        lo, hi = c.get("excellence_ci_lower"), c.get("excellence_ci_upper")
        ci_str = f" [95% CI: {lo:.1f}–{hi:.1f}%]" if lo is not None else ""
        lines.append(f"• **Excellence rate:** {exc:.1f}%{ci_str}")
    if pr is not None:
        lines.append(f"• **Pass rate:** {pr:.1f}%")
    if enr:
        lines.append(f"• **Enrollment:** {enr:,} students")
    if vol is not None:
        vol_note = "high — inconsistent performance" if vol > 0.5 else "moderate" if vol > 0.2 else "stable"
        lines.append(f"• **GPA volatility:** {vol:.3f} — {vol_note}")
    if c.get("high_risk"):
        lines.append("• ⚠️ **Flagged as HIGH RISK**")
    if c.get("abnormal_spike"):
        lines.append("• ⚠️ **Abnormal enrollment spike detected**")

    gd = c.get("grade_distribution")
    if gd:
        order = ["A+","A","A-","B+","B","B-","C+","C","C-","D+","D","F"]
        parts = [f"{g}: {gd[g]:.0f}%" for g in order if g in gd and gd[g] is not None]
        if parts:
            lines.append(f"\n**Grade distribution:** {' | '.join(parts)}")

    # Action plan
    for sp in (ctx.get("course_plans") or {}).values():
        for p in sp:
            if (p.get("course") or "").lower() == name.lower():
                acts = p.get("action_plan") or []
                if acts:
                    lines.append("\n**Recommended actions:**")
                    for a in acts[:4]:
                        lines.append(f"  → {a}")
                break

    # QA verdict
    lines.append("\n**QA assessment:**")
    if (fr or 0) > 40:
        lines.append("🔴 This course is in a critical state. It should be the top priority in any departmental review. The failure rate alone justifies an immediate deep-dive into assessment design, teaching approach, and student prerequisites.")
    elif (fr or 0) > 25 or (gpa or 4) < 2.5:
        lines.append("🟠 This course needs attention. The numbers are not at crisis level, but they're trending in a concerning direction. I'd recommend a targeted review within the next 4 weeks.")
    elif c.get("high_risk"):
        lines.append("⚠️ Risk-flagged despite acceptable headline numbers. Check the volatility and confidence intervals — surface metrics can look fine while underlying instability builds.")
    else:
        lines.append("✅ This course is performing within acceptable QA parameters. Monitor the excellence rate — there may be room to stretch the top performers without compromising overall outcomes.")

    return "\n".join(lines)


def _no_data_response(topic: str) -> str:
    return (f"I don't have {topic} loaded right now.\n\n"
            "Please upload your Excel file on the Dashboard, Course Report, or Program Report page first. "
            "Once the analysis runs, I'll be able to give you a full QA assessment of this topic.\n\n"
            "In the meantime, feel free to ask me about QA concepts, methodology, or how to interpret specific metrics.")


# ── Dispatch table ───────────────────────────────────────────────────────────

_DISPATCH = {
    "greeting":        _h_greeting,
    "thanks":          _h_thanks,
    "about":           _h_about,
    "help":            _h_help,
    "summary":         _h_summary,
    "gpa":             _h_gpa,
    "failure":         _h_failure,
    "excellence":      _h_excellence,
    "pass":            _h_pass,
    "enrollment":      _h_enrollment,
    "quality":         _h_quality,
    "risk":            _h_risk,
    "alerts":          _h_alerts,
    "forecast":        _h_forecast,
    "cohort":          _h_cohort,
    "variance":        _h_variance,
    "bayesian":        _h_bayesian,
    "montecarlo":      _h_montecarlo,
    "recommendations": _h_recommendations,
    "trend":           _h_trend,
    "compare":         _h_compare,
    "course_lookup":   _h_course_lookup,
    "general_qa":      _h_general_qa,
    "unknown":         _h_unknown,
}


# ── Public API ───────────────────────────────────────────────────────────────

def answer_question(question: str, context: dict | None, history: list | None = None) -> str:
    q = (question or "").strip()
    if not q:
        return "Please type a question."
    intent = _detect(q)
    fn = _DISPATCH.get(intent, _h_unknown)
    return fn(q, context or {}, history or [])
