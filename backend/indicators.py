"""
Standard 7 (Quality Assurance & Program Evaluation) — Accreditation Indicators Tracker.

Every other accreditation-support module (curriculum mapping, governance,
faculty data, resources, alumni) registers its evidence here as it's built,
so this tracker is the integration point across all 7 NAQAAE-style standards.

Persistence: SQLite via db.py (see ARCHITECTURE.md for why this app moved
off pure in-memory storage for accreditation data).
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import Any

from db import get_connection, init_schema

logger = logging.getLogger(__name__)

VALID_STATUSES = ("missing", "partial", "complete")

STANDARDS: dict[int, str] = {
    1: "Mission & Program Management",
    2: "Program Design",
    3: "Teaching, Learning & Assessment",
    4: "Students & Graduates",
    5: "Faculty & Supporting Staff",
    6: "Resources & Learning Facilities",
    7: "Quality Assurance & Program Evaluation",
}

# Official NAQAAE 2022 modified accreditation-standards indicator wording
# (34 indicators total, unevenly split 4/4/8/3/6/4/5 across the 7 standards
# — that split is the real official structure, not an artifact worth
# "balancing"). Replaced the original placeholder text once the official
# document became available; see git history for the placeholder wording
# this superseded.
_SEED_INDICATORS: dict[int, list[str]] = {
    1: [  # المعيار 1: رسالة وإدارة البرنامج (4 مؤشرات)
        "للبرنامج رسالة واضحة ومعتمدة ومعلنة، تتسق مع رسالة المؤسسة ومع احتياجات المجتمع، اشترك في اعدادها الأطراف المعنية، وتتم مراجعتها وتحديثها بشكل دوري لمواكبة المستجدات",
        "للبرنامج قيادة مؤهلة يتم اختيارها طبقًا لمعايير معتمدة ومعلنة ويتم تقييم أدائها دوريًا، تدير البرنامج بالاشتراك مع المجالس واللجان المعنية والمحددة الاختصاصات وفقًا للهيكل التنظيمي للمؤسسة",
        "يستخدم البرنامج وسائل متنوعة لإتاحة معلومات شاملة عنه تبرز سماته التنافسية وتعمل على التسويق له محليًا وإقليميًا ودوليًا",
        "في حالة وجود اتفاقيات أو شراكات للبرنامج مع مؤسسات دولية، يتم تحديد الأدوار والمسئوليات للطرفين، ويتم رصد أوجه الاستفادة",
    ],
    2: [  # المعيار 2: تصميم البرنامج (4 مؤشرات)
        "يتبنى البرنامج المعايير الأكاديمية القومية المرجعية NARS أو أية معايير مرجعية أخرى، وفق إجراءات معتمدة من خلال المجالس الرسمية، ويتم التوعية بالمعايير المتبناة لجميع الأطراف المعنية",
        "يحقق هيكل البرنامج: التكامل بين مكوناته من مقررات وأنشطة تتسق مع بعضها وتعكس المستجدات العلمية والمهنية في مجال التخصص، والتوازن بين المحتوى النظري والتطبيقي (التدريب العملي/الميداني)، والتوافق بين المتطلبات العامة ومتطلبات التخصص، بما يحقق أهداف البرنامج",
        "للبرنامج توصيف معتمد ومعلن طبقًا للائحته المعتمدة",
        "لمقررات البرنامج توصيف معتمد ومعلن طبقًا للائحته المعتمدة",
    ],
    3: [  # المعيار 3: التعليم والتعلم والتقييم (8 مؤشرات)
        "يطبق البرنامج طرقًا متنوعة للتعليم والتعلم تحقق المخرجات التعليمية للمقررات",
        "يتم تطبيق طرق للتعليم والتعلم تشجع الطالب على أخذ دور فعال في عملية تعلمهم وتدعم التعلم الذاتي وتنمية مهارات التفكير العليا ومهارات التوظف وريادة الأعمال",
        "يتم تنفيذ التدريب الميداني بالمشاركة مع الجهات المعنية وجهات التوظيف الملائمة لضمان تحقق التوجيه المهني للطالب، من خلال خطة وآليات وإجراءات واضحة ومعتمدة ومعلنة تنظم عملية التدريب والإشراف عليه وتقييمه",
        "يتم تقييم الطالب باستخدام أساليب متنوعة (تحريري وعملي وشفهي وإكلينيكي وميداني، ومشروعات وتكليفات، ودراسات حالة وملف إنجاز وغيرها)، وتتوازن الدرجات المخصصة لأساليب التقييم المختلفة",
        "للبرنامج آلية معتمدة لوضع الامتحانات المختلفة، وإجراءات للتحقق من تغطيتها للمحتوى العلمي للمقررات، ومن توافقها واستيفائها للمخرجات التعليمية/الجدارات للبرنامج التعليمي والمقررات الدراسية",
        "للبرنامج آليات معتمدة ومعلنة للتأكد من عدالة تقييم الطالب من خلال: نظم إدارة وإجراءات التقييمات المختلفة، ونظم عمل الكنترول، وتوثيق نتائج الامتحانات، وقواعد ضمان السرية والعدالة",
        "يتم تحليل نتائج تقييم الطالب، ومناقشتها في المجالس واللجان المختصة، والاستفادة منها في تطوير البرنامج",
        "يتم تقديم التغذية الراجعة للطالب عن أدائهم في التعلم والتقييم بما يدعم تعلمهم",
    ],
    4: [  # المعيار 4: الطلاب والخريجون (3 مؤشرات)
        "يوجد نظام معلن ومفعل للدعم الأكاديمي لجميع الطلاب المقيدين بالبرنامج (الإرشاد الأكاديمي/الريادة العلمية)، يتضمن آليات وإجراءات لمتابعة تقدمهم الدراسي، وتحديد ودعم الطلاب المتفوقين والموهوبين والمتعثرين، ويتم تقييم فعاليته دوريًا وتطويره في ضوء نتائج التقييم",
        "يشجع البرنامج اشتراك الطلاب في أنشطة طلابية متنوعة تتضمن فرص التعرض المبكر والمستمر لاكتسابهم خبرات بحثية ومجتمعية، وتتوافر بيانات عن أعداد الطلاب المشاركين بهذه الأنشطة، كما يوفر البرنامج خدمات الإرشاد والتوجيه المهني للطلاب",
        "توجد إجراءات مفعلة للتواصل مع الخريجين ودعمهم ومتابعة تقدمهم المهني",
    ],
    5: [  # المعيار 5: أعضاء هيئة التدريس والهيئة المعاونة (6 مؤشرات)
        "يتوافر للبرنامج الأعداد الكافية من أعضاء هيئة التدريس التي تسمح بتنفيذ الأنشطة التعليمية بصورة فعالة لضمان جودة التعليم والاعتماد، وبما يسمح بعبء وظيفي مناسب تبعًا للوائح والقوانين",
        "يتوافر للبرنامج الأعداد الكافية من الهيئة المعاونة التي تسمح بتنفيذ الأنشطة التعليمية بصورة فعالة طبقًا للمعدلات المرجعية للهيئة القومية للجودة، وبما يسمح بعبء وظيفي مناسب تبعًا للوائح والقوانين",
        "تتناسب مؤهلات وخبرات وكفاءات أعضاء هيئة التدريس والهيئة المعاونة بالبرنامج، مع المقررات التي يقومون بتدريسها بالبرنامج",
        "يوجد معايير معتمدة ومعلنة وإجراءات عادلة وشفافة لاختيار أعضاء هيئة التدريس والهيئة المعاونة وبما يضمن جذب الكفاءات، ويتم تحديد حالات الفائض أو العجز بصفة دورية واتخاذ الإجراءات الرسمية والمعتمدة للتعامل معها",
        "يشارك أعضاء هيئة التدريس والهيئة المعاونة بالبرنامج بشكل دوري في أنشطة التنمية المهنية المستمرة وذلك لضمان مواكبة الاتجاهات الحديثة للتعليم والتعلم والتقييم والبحث العلمي ومستجدات التخصص المهني، ويتم توثيق ذلك في قواعد بيانات البرنامج",
        "يشارك أعضاء الهيئة التدريسية بالبرنامج في الأنشطة البحثية (الإشراف على الرسائل العلمية/النشر المحلي والدولي/المؤتمرات والندوات/المشروعات البحثية/البعثات والمنح الدراسية/وغيرها) و/أو في الأنشطة المجتمعية والمهنية، ويتم توثيق ذلك في قواعد البيانات",
    ],
    6: [  # المعيار 6: الموارد ومصادر التعلم والتسهيلات الداعمة (4 مؤشرات)
        "تتوفر للبرنامج الموارد المالية الكافية والمتنوعة لتحقيق رسالته وأهدافه طبقًا لطبيعة نشاطه وأعداد الطلاب",
        "تتوفر للبرنامج الأماكن والتسهيلات الداعمة الملائمة لطبيعة البرنامج ولأنشطة التدريس والتعلم المطبقة ولأعداد الطلاب، وذلك بما يتوافق مع المواصفات المرجعية للهيئة",
        "تتوافر متطلبات وتجهيزات الأمن والصحة والسلامة المهنية بما يتوافق مع طبيعة البرنامج واحتياجات الطلاب، ويتم تطبيق الإجراءات الاحترازية تبعًا للظروف الطارئة",
        "تتوفر للبرنامج بنية رقمية (تقنية/تكنولوجية) مناسبة وكافية لاحتياجاته ولأعداد الهيئة التدريسية وأعداد الطلاب",
    ],
    7: [  # المعيار 7: ضمان الجودة وتقييم البرنامج (5 مؤشرات)
        "توجد تغذية راجعة دورية من الطلاب والهيئة التدريسية لقياس رضاهم عن البرنامج والعملية التعليمية، يتم تحليلها والاستفادة منها في التطوير المستمر",
        "توجد تغذية راجعة دورية من الخريجين وجهات التوظيف عن ملائمة البرنامج لتلبية متطلبات سوق العمل، يتم الاستفادة منها في تعديل وتحديث البرنامج",
        "يوجد تقارير دورية للمقررات الدراسية توضح الالتزام بالتوصيف المعلن للمقررات، وتتضمن تحليل نتائج الامتحانات ونسب النجاح ودلالاتها وتحليل نتائج التغذية الراجعة من الطلاب وخطط للتحسين والتطوير",
        "يوجد تقارير سنوية للبرنامج تتضمن: التحقق من تنفيذ توصيف البرنامج، قياس اكتساب الطلاب للمعارف والمهارات والجدارات المحددة بالبرنامج، الخطط السنوية للتعزيز والتطوير بمشاركة الأطراف المعنية",
        "يتم مناقشة ومتابعة مردود عملية التعزيز والتحسين بالبرنامج وتحديد أوجه الاستفادة من عملية التقييم الذاتي بصفة دورية",
    ],
}

_INDICATORS_TABLE = """
CREATE TABLE IF NOT EXISTS indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_number INTEGER NOT NULL CHECK (standard_number BETWEEN 1 AND 7),
    indicator_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'missing' CHECK (status IN ('missing', 'partial', 'complete')),
    responsible_person TEXT,
    evidence_link TEXT,
    due_date TEXT,
    last_updated TEXT NOT NULL
)
"""

_LOOP_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS closing_the_loop_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL REFERENCES indicators(id) ON DELETE CASCADE,
    weakness_identified TEXT NOT NULL,
    action_taken TEXT,
    entry_status TEXT,
    entry_date TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def init_db() -> None:
    init_schema(_INDICATORS_TABLE, _LOOP_LOG_TABLE)


def _now_iso() -> str:
    return datetime.datetime.now().isoformat()


def seed_defaults(force: bool = False) -> int:
    """Seed the 34 official indicators per standard if the table is empty.

    Returns the number of rows inserted. Idempotent unless force=True.
    force=True wipes any existing indicators (and their closing-the-loop
    log entries) first — see backend/scripts/migrate_to_real_indicators.py
    for the one-off migration that decides whether that's safe to do
    against a database that already has real work logged against it.
    """
    init_db()
    with get_connection() as conn:
        if not force:
            count = conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
            if count > 0:
                return 0
        else:
            conn.execute("DELETE FROM closing_the_loop_log")
            conn.execute("DELETE FROM indicators")

        now = _now_iso()
        rows = [
            (standard_number, text, "missing", None, None, None, now)
            for standard_number, texts in _SEED_INDICATORS.items()
            for text in texts
        ]
        conn.executemany(
            """
            INSERT INTO indicators
                (standard_number, indicator_text, status, responsible_person, evidence_link, due_date, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)


def _row_to_dict(row) -> dict[str, Any]:
    d = dict(row)
    d["standard_name"] = STANDARDS.get(d["standard_number"], "Unknown")
    return d


def list_indicators(
    standard_number: int | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT * FROM indicators WHERE 1=1"
    params: list[Any] = []
    if standard_number is not None:
        query += " AND standard_number = ?"
        params.append(standard_number)
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY standard_number, id"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_indicator(indicator_id: int) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM indicators WHERE id = ?", (indicator_id,)).fetchone()
        if row is None:
            return None
        result = _row_to_dict(row)
        log_rows = conn.execute(
            "SELECT * FROM closing_the_loop_log WHERE indicator_id = ? ORDER BY id",
            (indicator_id,),
        ).fetchall()
        result["closing_the_loop_log"] = [dict(r) for r in log_rows]
        return result


def create_indicator(
    standard_number: int,
    indicator_text: str,
    responsible_person: str | None = None,
    evidence_link: str | None = None,
    due_date: str | None = None,
) -> dict[str, Any]:
    if standard_number not in STANDARDS:
        raise ValueError(f"standard_number must be 1-7, got {standard_number}")
    if not indicator_text or not indicator_text.strip():
        raise ValueError("indicator_text is required")
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO indicators
                (standard_number, indicator_text, status, responsible_person, evidence_link, due_date, last_updated)
            VALUES (?, ?, 'missing', ?, ?, ?, ?)
            """,
            (standard_number, indicator_text.strip(), responsible_person, evidence_link, due_date, _now_iso()),
        )
        new_id = cur.lastrowid
    return get_indicator(new_id)  # type: ignore[return-value]


def update_indicator(indicator_id: int, **fields: Any) -> dict[str, Any] | None:
    """Update any subset of status/responsible_person/evidence_link/due_date."""
    allowed = {"status", "responsible_person", "evidence_link", "due_date", "indicator_text"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}")
    if not updates:
        return get_indicator(indicator_id)

    init_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [_now_iso(), indicator_id]
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE indicators SET {set_clause}, last_updated = ? WHERE id = ?",
            params,
        )
        if cur.rowcount == 0:
            return None
    return get_indicator(indicator_id)


def add_log_entry(
    indicator_id: int,
    weakness_identified: str,
    action_taken: str | None = None,
    entry_status: str | None = None,
    entry_date: str | None = None,
) -> dict[str, Any] | None:
    """Append a closing-the-loop entry (append-only, never edited or deleted)."""
    if not weakness_identified or not weakness_identified.strip():
        raise ValueError("weakness_identified is required")
    init_db()
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM indicators WHERE id = ?", (indicator_id,)).fetchone()
        if exists is None:
            return None
        conn.execute(
            """
            INSERT INTO closing_the_loop_log
                (indicator_id, weakness_identified, action_taken, entry_status, entry_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                indicator_id,
                weakness_identified.strip(),
                action_taken,
                entry_status,
                entry_date or _now_iso(),
                _now_iso(),
            ),
        )
    return get_indicator(indicator_id)


@dataclass(frozen=True)
class StandardSummary:
    standard_number: int
    standard_name: str
    total: int
    missing: int
    partial: int
    complete: int


def summarize_by_standard() -> list[StandardSummary]:
    indicators = list_indicators()
    summaries: list[StandardSummary] = []
    for num, name in STANDARDS.items():
        subset = [i for i in indicators if i["standard_number"] == num]
        summaries.append(
            StandardSummary(
                standard_number=num,
                standard_name=name,
                total=len(subset),
                missing=sum(1 for i in subset if i["status"] == "missing"),
                partial=sum(1 for i in subset if i["status"] == "partial"),
                complete=sum(1 for i in subset if i["status"] == "complete"),
            )
        )
    return summaries
