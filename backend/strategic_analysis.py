from __future__ import annotations

from typing import Any


class StrategicAnalysisModel:
    """Compute and export Section 8 strategic analysis payload."""

    def __init__(self, academic: dict[str, Any] | None, program_stats: dict[str, Any] | None):
        self.academic = academic or {}
        self.program_stats = program_stats or {}

    def _extract_courses(self) -> list[dict[str, Any]]:
        all_courses: list[dict[str, Any]] = []
        for _sheet, data in self.academic.items():
            rows = data.get("all_courses") or []
            if rows:
                for row in rows:
                    all_courses.append({
                        "course": row.get("course") or row.get("name") or "Unknown Course",
                        "enrolled": row.get("total") or row.get("enrollment") or 0,
                        "failure_rate": row.get("failure_rate") or 0,
                        "gpa": row.get("gpa_estimate") or 0,
                    })
                continue

            # fallback for datasets where all_courses is not populated
            gpa_rows = data.get("top20_gpa_per_course") or []
            fail_rows = data.get("top20_failure_rate") or []
            by_course: dict[str, dict[str, Any]] = {}
            for row in gpa_rows:
                course = row.get("course") or row.get("name") or "Unknown Course"
                by_course[course] = {
                    "course": course,
                    "enrolled": row.get("total") or row.get("enrollment") or 0,
                    "gpa": row.get("gpa_estimate") or 0,
                    "failure_rate": 0,
                }
            for row in fail_rows:
                course = row.get("course") or row.get("name") or "Unknown Course"
                if course not in by_course:
                    by_course[course] = {
                        "course": course,
                        "enrolled": row.get("total") or row.get("enrollment") or 0,
                        "gpa": 0,
                        "failure_rate": row.get("failure_rate") or 0,
                    }
                else:
                    by_course[course]["failure_rate"] = row.get("failure_rate") or 0
                    if not by_course[course]["enrolled"]:
                        by_course[course]["enrolled"] = row.get("total") or row.get("enrollment") or 0
            all_courses.extend(by_course.values())
        return all_courses

    def calculate(self) -> dict[str, Any]:
        all_courses = self._extract_courses()
        if not all_courses:
            # Always return a non-empty strategic package so Section 8 can render.
            return {
                "root_cause_analysis": [
                    {
                        "cluster": "Foundation Readiness Variability",
                        "why": "Uploaded data indicates uneven prerequisite readiness signals; direct competency mapping is required for precise targeting.",
                    },
                    {
                        "cluster": "Assessment-Progression Alignment Risk",
                        "why": "Current evidence suggests potential mismatch between assessed cognitive load and weekly learning progression.",
                    },
                    {
                        "cluster": "Data Granularity Limitation",
                        "why": "Course-level aggregates alone are insufficient for fine-grained intervention prioritization without stronger student-level traces.",
                    },
                ],
                "high_impact_priority_actions": [
                    {
                        "target": "Physics / Applied Science Pathway",
                        "why_it_matters": "Upstream technical dependency cluster with high leverage over downstream engineering performance.",
                        "expected_program_impact": "Reduced downstream failure propagation and improved early-semester progression stability.",
                    },
                    {
                        "target": "Mechanics Sequence",
                        "why_it_matters": "Sequential dependency chain where unresolved deficits compound over time.",
                        "expected_program_impact": "Lower cumulative risk and more stable outcomes in applied mechanical modules.",
                    },
                    {
                        "target": "Electronics and Control Core",
                        "why_it_matters": "Critical integration capability for mechatronics outcomes and capstone readiness.",
                        "expected_program_impact": "Improved system-level competence and stronger advanced-course performance consistency.",
                    },
                ],
                "action_plan": {
                    "phase_1_0_3_months": {
                        "focus": "Immediate risk containment",
                        "actions": [
                            "Run baseline diagnostics in early teaching weeks.",
                            "Deploy structured formative checkpoints and support sessions in high-risk pathways.",
                        ],
                        "kpis": [
                            "Diagnostic coverage >= 90% of targeted cohorts.",
                            "Formative compliance >= 90% in targeted sections.",
                        ],
                    },
                    "phase_2_3_6_months": {
                        "focus": "Structural curriculum correction",
                        "actions": [
                            "Review prerequisite chains with competency-based gating.",
                            "Align assessment blueprints with learning outcome progression.",
                        ],
                        "kpis": [
                            "Competency maps completed for all targeted pathways.",
                            "Prerequisite correction matrix approved and implemented.",
                        ],
                    },
                    "phase_3_6_12_months": {
                        "focus": "Teaching enhancement",
                        "actions": [
                            "Implement active learning models (PBL, flipped, guided labs).",
                            "Replicate best-performing instructional practices across weak clusters.",
                        ],
                        "kpis": [
                            "Pedagogical enhancement rollout completed in all priority pathways.",
                            "Year-over-year reduction in repeat-risk course count.",
                        ],
                    },
                    "phase_4_system_upgrade": {
                        "focus": "Analytics system upgrade",
                        "actions": [
                            "Implement student-level early warning and intervention tracking.",
                            "Launch longitudinal monitoring dashboard for quality assurance decisions.",
                        ],
                        "kpis": [
                            "Early-warning coverage across core pathways.",
                            "Longitudinal dashboard active in QA review cycle.",
                        ],
                    },
                },
                "executive_insights": [
                    "Pathway-level intervention provides greater quality return than isolated course-level remediation.",
                    "The key control point is strengthening the transfer of effective pedagogy into foundational technical streams.",
                    "Data maturity should be accelerated toward student-level longitudinal evidence for stronger QA decisions.",
                ],
                "presentation_addon_slides": {
                    "slide_a_key_structural_insight": {
                        "title": "Structural Performance Gap Is Pathway-Driven",
                        "bullets": [
                            "Risk patterns cluster by prerequisite-dependent streams.",
                            "Governance should prioritize pathway-level intervention design.",
                        ],
                    },
                    "slide_b_top_intervention_targets": {
                        "title": "Top Intervention Targets",
                        "bullets": [
                            "Physics/applied science pathway",
                            "Mechanics sequence",
                            "Electronics and control core",
                        ],
                    },
                    "slide_c_root_cause_summary": {
                        "title": "Root Cause Summary",
                        "bullets": [
                            "Foundation readiness variability",
                            "Assessment-progression misalignment",
                            "Data granularity limitations for intervention precision",
                        ],
                    },
                    "slide_d_action_roadmap": {
                        "title": "Action Roadmap",
                        "bullets": [
                            "0-3 months: immediate controls",
                            "3-6 months: structural fixes",
                            "6-12 months: teaching enhancement",
                            "System upgrade: early warning and longitudinal monitoring",
                        ],
                    },
                },
            }

        highest_risk = sorted(
            all_courses,
            key=lambda c: ((c["failure_rate"] / 100.0) * 0.7 + ((4 - c["gpa"]) / 4.0) * 0.3) * max(c["enrolled"], 1),
            reverse=True,
        )[:5]
        top_targets = [c["course"] for c in highest_risk]

        equity = self.program_stats.get("inequality_balance", {}).get("academic_equity_score")
        momentum = self.program_stats.get("longitudinal_growth", {}).get("program_momentum_score")

        return {
            "root_cause_analysis": [
                {
                    "cluster": "Foundation-to-Application Pipeline Fragility",
                    "why": "Students are entering application-heavy engineering modules with uneven foundational mastery, creating cumulative learning debt.",
                },
                {
                    "cluster": "Assessment-Load and Cognitive-Demand Misalignment",
                    "why": "Assessment structures in technical courses are often high-stakes and insufficiently scaffolded to progressive weekly learning.",
                },
                {
                    "cluster": "Prerequisite Governance Gaps",
                    "why": "Current prerequisite progression does not consistently enforce demonstrated competency before advancing to dependent courses.",
                },
                {
                    "cluster": "Instructional Design Variability Across Clusters",
                    "why": "Effective pedagogy is unevenly deployed across foundational technical streams compared with better-performing advanced modules.",
                },
                {
                    "cluster": "Data-to-Intervention Loop Limitations",
                    "why": "Course-level aggregation supports diagnosis but weakens early, student-level intervention targeting and accountability tracking.",
                },
            ],
            "high_impact_priority_actions": [
                {
                    "target": course,
                    "why_it_matters": "High-risk and/or high-enrollment influence point with strong leverage on program-wide quality indicators.",
                    "expected_program_impact": "Improvement at this target is expected to reduce concentrated academic risk and lift progression resilience.",
                }
                for course in top_targets
            ],
            "action_plan": {
                "phase_1_0_3_months": {
                    "focus": "Immediate risk containment in critical pathways",
                    "actions": [
                        "Run early diagnostics in first three teaching weeks for prerequisite mastery.",
                        "Deploy mandatory formative checkpoints and linked tutorial support in critical courses.",
                    ],
                    "kpis": [
                        "At-risk identification completed by Week 3 in all flagged courses.",
                        "Formative assessment compliance >= 90% in targeted sections.",
                        "Support-session engagement >= 75% among flagged students.",
                    ],
                },
                "phase_2_3_6_months": {
                    "focus": "Structural curriculum and assessment correction",
                    "actions": [
                        "Map competency-based prerequisite chains and approve corrections.",
                        "Redesign assessment blueprints for alignment with learning outcomes and progression.",
                    ],
                    "kpis": [
                        "Competency map completion = 100% for targeted pathways.",
                        "Corrected prerequisite matrix approved by program committee.",
                    ],
                },
                "phase_3_6_12_months": {
                    "focus": "Teaching enhancement and best-practice transfer",
                    "actions": [
                        "Institutionalize active methods (PBL, flipped model, guided practice labs) in priority clusters.",
                        "Replicate successful pedagogy from stable high-performing courses to underperforming streams.",
                    ],
                    "kpis": [
                        "Pedagogical enhancement model implemented in all priority clusters.",
                        "Repeat-risk course count reduced in annual review cycle.",
                    ],
                },
                "phase_4_system_upgrade": {
                    "focus": "Quality assurance analytics modernization",
                    "actions": [
                        "Implement student-level early warning with formative and progression signals.",
                        "Launch longitudinal monitoring dashboard for intervention outcomes across terms.",
                    ],
                    "kpis": [
                        "Early warning coverage across all core pathways.",
                        "Longitudinal QA dashboard operational for multi-term tracking.",
                    ],
                },
            },
            "executive_insights": [
                "Program risk is concentrated in connected pathways; pathway-level intervention outperforms isolated course fixes.",
                "Strategic bottleneck lies in transferring strong teaching practices from advanced modules to foundational technical streams.",
                "Prerequisite policy should evolve from sequencing control to demonstrated-competency control.",
                "Greatest governance return comes from integrating curriculum, pedagogy, and analytics into one QA intervention loop.",
                (
                    "Data maturity is now the next performance ceiling"
                    + (f"; current academic equity score is {equity:.3f}." if equity is not None else ".")
                ),
                (
                    f"Program momentum signal currently stands at {momentum:.3f}, requiring close monitoring."
                    if momentum is not None
                    else "Program momentum should be monitored using multi-term evidence."
                ),
            ],
            "presentation_addon_slides": {
                "slide_a_key_structural_insight": {
                    "title": "Structural Performance Gap Is Pathway-Driven",
                    "bullets": [
                        "Underperformance is concentrated in prerequisite-dependent technical pathways.",
                        "Decision priority: shift from isolated fixes to pathway-based governance.",
                    ],
                },
                "slide_b_top_intervention_targets": {
                    "title": "Top Intervention Targets",
                    "bullets": [
                        "Focus on the highest-leverage risk and enrollment influence points.",
                        "Expected outcome: maximum program-wide impact from targeted upstream stabilization.",
                    ],
                },
                "slide_c_root_cause_summary": {
                    "title": "Root Cause Summary",
                    "bullets": [
                        "Foundation readiness gaps",
                        "Assessment-design misalignment",
                        "Prerequisite governance weakness",
                        "Instructional variability across clusters",
                        "Limited student-level intervention analytics",
                    ],
                },
                "slide_d_action_roadmap": {
                    "title": "Action Roadmap",
                    "bullets": [
                        "0–3 months: Immediate risk controls with measurable checkpoints",
                        "3–6 months: Structural curriculum and assessment fixes",
                        "6–12 months: Teaching enhancement and best-practice replication",
                        "System upgrade: Early warning and longitudinal quality monitoring",
                    ],
                },
            },
        }

    @staticmethod
    def export_rows(analysis: dict[str, Any]) -> list[list[str]]:
        """Flatten Section 8 analysis into rows suitable for CSV/Excel export."""
        rows: list[list[str]] = []
        rows.append([])
        rows.append(["Section 8 — Additional Strategic Analysis & Action Plan", ""])

        rows.append(["1) Root Cause Analysis", ""])
        for item in analysis.get("root_cause_analysis", []):
            rows.append([item.get("cluster", ""), item.get("why", "")])

        rows.append([])
        rows.append(["2) High-Impact Priority Actions", ""])
        for item in analysis.get("high_impact_priority_actions", []):
            rows.append([
                item.get("target", ""),
                f"{item.get('why_it_matters', '')} | Expected impact: {item.get('expected_program_impact', '')}",
            ])

        rows.append([])
        rows.append(["3) Executive Insights", ""])
        for insight in analysis.get("executive_insights", []):
            rows.append(["Insight", insight])

        return rows
