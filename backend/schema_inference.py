"""
Schema inference and validation for academic Excel data.
Infers column roles: Course, Student ID, Grade, Semester, Department.
Logs schema for drift detection.
"""
import re
from typing import Any

import pandas as pd


# Keywords (English / Arabic) to infer column roles
ROLE_PATTERNS = {
    "course": [
        "course", "مقرر", "مادة", "subject", "كورس",
        "coursename", "اسم المقرر", "المقرر",
    ],
    "student_id": [
        "student", "id", "رقم", "كود", "code", "طالب",
        "studentid", "student_id", "الطالب", "الرقم",
    ],
    "grade": [
        "grade", "درجة", "درجات", "result", "ناتج",
        "gpa", "التقدير", "الدرجة", "النتيجة",
    ],
    "semester": [
        "semester", "فصل", "ترم", "term", "الفصل",
        "sem", "التيرم",
    ],
    "department": [
        "department", "قسم", "كلية", "dept", "القسم",
        "faculty", "الكلية",
    ],
}


def _normalize(s: str) -> str:
    return re.sub(r"[\s_]", "", str(s).lower())


def infer_column_role(col_name: str) -> str | None:
    """Infer role from column name. Returns one of: course, student_id, grade, semester, department."""
    n = _normalize(col_name)
    for role, keywords in ROLE_PATTERNS.items():
        if any(kw in n or n in _normalize(kw) for kw in keywords):
            return role
    return None


def infer_schema(df: pd.DataFrame) -> dict[str, Any]:
    """
    Infer schema and column roles for a sheet.
    Returns: { columns: [...], roles: { col_name: role }, inferred_roles: { role: col_name } }
    """
    columns = list(df.columns.astype(str))
    roles = {}
    inferred_roles = {}
    for col in columns:
        role = infer_column_role(col)
        if role:
            roles[col] = role
            if role not in inferred_roles:
                inferred_roles[role] = col
    return {
        "columns": columns,
        "roles": roles,
        "inferred_roles": inferred_roles,
    }


def validate_schema(schema: dict, required_roles: list[str] | None = None) -> list[str]:
    """
    Validate inferred schema. Returns list of validation messages (empty if OK).
    required_roles: e.g. ['course', 'grade'] to warn if missing.
    """
    messages = []
    if required_roles is None:
        required_roles = ["course", "grade"]
    ir = schema.get("inferred_roles", {})
    for r in required_roles:
        if r not in ir:
            messages.append(f"Missing inferred role: {r}")
    return messages


def detect_schema_changes(previous_schema: dict | None, current_schema: dict) -> list[str]:
    """Compare previous and current schema for drift. Returns list of change descriptions."""
    if not previous_schema:
        return []
    changes = []
    prev_cols = set(previous_schema.get("columns") or [])
    curr_cols = set(current_schema.get("columns") or [])
    if prev_cols != curr_cols:
        added = curr_cols - prev_cols
        removed = prev_cols - curr_cols
        if added:
            changes.append(f"Columns added: {', '.join(sorted(added)[:5])}{'...' if len(added) > 5 else ''}")
        if removed:
            changes.append(f"Columns removed: {', '.join(sorted(removed)[:5])}{'...' if len(removed) > 5 else ''}")
    return changes
