"""
Adaptive Excel reader for academic templates.
Supports: multi-row headers (e.g. row 4 = Code, Course Title; row 5 = grade letters), data from row 6.
Normalizes to a single DataFrame per sheet with clear column names.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd


# Grade column names (wide format)
GRADE_COLS_WIDE = ["A", "A-", "A+", "B", "B-", "B+", "C", "C-", "C+", "D", "D+", "F"]


def _is_unnamed(cols: list) -> bool:
    return all(
        str(c).startswith("Unnamed") or (isinstance(c, (int, float)) and pd.isna(c))
        for c in cols
    )


def _row_has_grade_letters(row: pd.Series) -> bool:
    """Check if row contains grade letters like A, A-, B, F."""
    seen = set()
    for v in row.dropna():
        s = str(v).strip().upper()
        if re.match(r"^[A-F][+-]?$", s):
            seen.add(s)
    return len(seen) >= 3


def _row_has_code_course(row: pd.Series) -> bool:
    """
    Check if a header-like row contains course code + course name.
    Supports English (Code / Course / Title) and Arabic headers such as
    \"كود المقرر\" و\"اسم المقرر\".
    """
    cells = [str(v).strip().lower() for v in row.astype(str)]
    if not cells:
        return False

    def _contains_any(token_list: list[str]) -> bool:
        return any(any(tok in c for tok in token_list) for c in cells)

    # English patterns
    has_code_en = _contains_any(["code"])
    has_course_en = _contains_any(["course", "title"])

    # Arabic patterns: كود المقرر / كود / مقرر / مادة / اسم المقرر
    has_code_ar = _contains_any(["كود", "code"])
    has_course_ar = _contains_any(["المقرر", "مقرر", "المادة", "اسم المقرر"])

    return (has_code_en and has_course_en) or (has_code_ar and has_course_ar)


def read_sheet_adaptive(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Given a sheet read with header=0 (so possibly Unnamed columns), detect header/data rows
    and return a clean DataFrame with proper column names and data only.
    """
    if df_raw.empty or len(df_raw) < 6:
        return df_raw

    cols = list(df_raw.columns)
    # If already named and not all Unnamed, assume standard read
    if not _is_unnamed(cols):
        return df_raw

    # Find header row (Code, Course Title) and grade row (A, A-, A+, ...)
    header_row = None
    grade_row = None
    for i in range(min(8, len(df_raw))):
        row = df_raw.iloc[i]
        if _row_has_code_course(row):
            header_row = i
        if _row_has_grade_letters(row):
            grade_row = i
            if header_row is None and i > 0:
                header_row = i - 1
            break

    if grade_row is None:
        # Fallback: if we already detected a header row (e.g. Arabic \"كود المقرر\" / \"اسم المقرر\"),
        # assume the grade row is immediately after it. Otherwise, fall back to rows 4 and 5.
        if header_row is None:
            header_row = 4 if len(df_raw) > 5 else 0
        candidate = header_row + 1
        grade_row = candidate if len(df_raw) > candidate else header_row

    data_start = max(header_row or 0, grade_row or 0) + 1
    if data_start >= len(df_raw):
        return df_raw

    # Build column names from header_row and grade_row
    h = df_raw.iloc[header_row].astype(str).str.strip()
    g = df_raw.iloc[grade_row].astype(str).str.strip()
    new_cols = []
    for j in range(len(df_raw.columns)):
        gj = g.iloc[j] if j < len(g) else ""
        hj = h.iloc[j] if j < len(h) else ""
        if gj and re.match(r"^[A-F][+-]?$", gj.upper()):
            new_cols.append(gj.upper())
        elif hj and hj not in ("nan", ""):
            new_cols.append(hj)
        else:
            new_cols.append(f"Col_{j}")

    out = df_raw.iloc[data_start:].copy()
    out.columns = new_cols
    out = out.reset_index(drop=True)
    # Drop completely empty rows
    out = out.dropna(how="all")
    return out


def read_excel_adaptive(path_or_buffer: Any) -> dict[str, pd.DataFrame]:
    """
    Read Excel file; for each sheet, if columns are Unnamed, apply adaptive header detection.
    Returns dict sheet_name -> DataFrame.
    """
    xls = pd.ExcelFile(path_or_buffer)
    result = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        if _is_unnamed(list(df.columns)) and len(df) >= 6:
            df = read_sheet_adaptive(df)
        result[sheet] = df
    return result


_SEMESTER_PATTERNS = [
    (("الأول", "الاول"), "First / Fall"),
    (("الثاني", "الثانى"), "Second / Spring"),
    (("صيفي", "الصيفي", "صيفى"), "Summer"),
]

_YEAR_RE = re.compile(r"(\d{4})\s*[-/]\s*(\d{4})")


def extract_sheet_title_metadata(path_or_buffer: Any) -> dict[str, dict[str, str | None]]:
    """
    Best-effort extraction of academic year / semester / program title that Egyptian
    academic-report workbooks typically embed as free-text banner rows above the data
    table (e.g. "إحصائية تقديرات 2025-2026 فصل دراسي الأول" / "برنامج الميكاترونيات
    لائحة حديثة"). Returns sheet_name -> {academic_year, semester, program_title}.
    Values are None when nothing recognizable is found — never guessed.
    """
    result: dict[str, dict[str, str | None]] = {}
    try:
        xls = pd.ExcelFile(path_or_buffer)
    except Exception:
        return result

    for sheet in xls.sheet_names:
        info: dict[str, str | None] = {"academic_year": None, "semester": None, "program_title": None}
        try:
            raw = xls.parse(sheet, header=None, nrows=6)
        except Exception:
            result[sheet] = info
            continue

        for _, row in raw.iterrows():
            for cell in row:
                if pd.isna(cell):
                    continue
                text = re.sub(r"\s+", " ", str(cell)).strip()
                if not text or text.lower().startswith("unnamed"):
                    continue

                if info["academic_year"] is None:
                    m = _YEAR_RE.search(text)
                    if m:
                        info["academic_year"] = f"{m.group(1)}/{m.group(2)}"

                if info["semester"] is None:
                    for tokens, label in _SEMESTER_PATTERNS:
                        if any(tok in text for tok in tokens):
                            info["semester"] = label
                            break

                if info["program_title"] is None and ("برنامج" in text or "لائحة" in text):
                    info["program_title"] = text

        result[sheet] = info

    return result
