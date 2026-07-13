"""
دمج إحصائية تقديرات المواد من ملفين إكسل.
يقرأ الملفين، يطابق المواد حسب الكود أو اسم المادة، يجمع الأرقام للمتطابقات،
والمواد غير المتطابقة تبقى كما هي.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

# استيراد قارئ الإكسل الموجود في المشروع
from excel_reader import read_excel_adaptive

# أعمدة التقديرات المعروفة (أرقام تُجمع)
GRADE_COLS = ["A", "A-", "A+", "B", "B-", "B+", "C", "C-", "C+", "D", "D+", "F"]


def _normalize_key(val) -> str:
    """توحيد القيمة للمقارنة (كود أو اسم مادة)."""
    if pd.isna(val):
        return ""
    return str(val).strip()


def _find_key_columns(df: pd.DataFrame) -> list[str]:
    """
    إيجاد أعمدة المفتاح: كود المقرر أو اسم المقرر.
    نرجع أول عمود يحتوي كود وأول عمود يحتوي اسم إن وُجدا.
    """
    key_cols = []
    seen = set()
    for c in df.columns:
        name = str(c).strip().lower()
        if c in seen:
            continue
        # كود
        if any(t in name for t in ["كود", "code"]):
            key_cols.append(c)
            seen.add(c)
        # اسم المقرر / المادة
        elif any(t in name for t in ["اسم المقرر", "المقرر", "المادة", "course", "title", "مادة"]):
            key_cols.append(c)
            seen.add(c)
        if len(key_cols) >= 2:
            break
    if not key_cols:
        for c in df.columns:
            if str(c).upper() not in GRADE_COLS:
                key_cols.append(c)
            if len(key_cols) >= 2:
                break
    if not key_cols:
        key_cols = list(df.columns[:2]) if len(df.columns) >= 2 else list(df.columns)
    return key_cols


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    """أعمدة رقمية يمكن جمعها (تقديرات A, B, C... وغيرها)."""
    out = []
    for c in df.columns:
        if str(c).upper() in GRADE_COLS:
            out.append(c)
            continue
        # Use numpy subtype check instead of fragile string comparison
        if pd.api.types.is_numeric_dtype(df[c]):
            out.append(c)
        elif _is_numeric_series(df[c]):
            out.append(c)
    return out


def _is_numeric_series(s: pd.Series) -> bool:
    converted = pd.to_numeric(s, errors="coerce")
    # Consider numeric only if majority of values converted successfully
    return converted.notna().sum() > len(s) * 0.5


def _make_row_key(row: pd.Series, key_cols: list[str]) -> str:
    """مفتاح صف واحد من أعمدة المفتاح."""
    parts = [_normalize_key(row.get(c, "")) for c in key_cols]
    return "|".join(parts)


def merge_sheet(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """
    دمج جدولين بنفس الهيكل:
    - نفس الكود/المادة → صف واحد مع جمع الأرقام.
    - مختلف → الصف يبقى لوحده بكل بياناته.
    """
    if df1.empty and df2.empty:
        return pd.DataFrame()
    if df1.empty:
        return df2.copy()
    if df2.empty:
        return df1.copy()

    key_cols = [c for c in _find_key_columns(df1) if c in df2.columns]
    if not key_cols:
        key_cols = [c for c in df1.columns if c in df2.columns][:2]
    if not key_cols:
        key_cols = list(df1.columns[:2]) if len(df1.columns) >= 2 else list(df1.columns)

    num1 = set(_numeric_columns(df1))
    num2 = set(_numeric_columns(df2))
    numeric_cols = [c for c in df1.columns if c in df2.columns and c in num1 and c in num2]
    non_numeric = [c for c in df1.columns if c not in numeric_cols]

    # بناء قاموس: مفتاح -> بيانات مجمعة
    merged = {}
    for _, row in df1.iterrows():
        k = _make_row_key(row, key_cols)
        merged[k] = row.to_dict()

    for _, row in df2.iterrows():
        k = _make_row_key(row, key_cols)
        if k in merged:
            for c in numeric_cols:
                v1 = merged[k].get(c)
                v2 = row.get(c)
                v1 = pd.to_numeric(v1, errors="coerce")
                v2 = pd.to_numeric(v2, errors="coerce")
                merged[k][c] = (v1 if pd.notna(v1) else 0) + (v2 if pd.notna(v2) else 0)
        else:
            merged[k] = row.to_dict()

    # تحويل إلى DataFrame مع ترتيب الأعمدة كـ df1
    out = pd.DataFrame(list(merged.values()))
    if not out.empty and list(df1.columns):
        # ترتيب الأعمدة مثل الملف الأول
        cols = [c for c in df1.columns if c in out.columns]
        extra = [c for c in out.columns if c not in cols]
        out = out[cols + extra]
    return out


def merge_excel_files(path1: str | Path, path2: str | Path, output_path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """
    قراءة ملفي إكسل ودمج كل شيت مع نظيره بالاسم.
    يُرجع dict اسم الشيت -> DataFrame مدمج.
    """
    path1 = Path(path1)
    path2 = Path(path2)
    if not path1.exists():
        raise FileNotFoundError(f"الملف الأول غير موجود: {path1}")
    if not path2.exists():
        raise FileNotFoundError(f"الملف الثاني غير موجود: {path2}")

    sheets1 = read_excel_adaptive(path1)
    sheets2 = read_excel_adaptive(path2)

    result = {}
    all_sheet_names = sorted(set(sheets1.keys()) | set(sheets2.keys()))

    for name in all_sheet_names:
        df1 = sheets1.get(name, pd.DataFrame())
        df2 = sheets2.get(name, pd.DataFrame())
        if df1.empty and df2.empty:
            continue
        result[name] = merge_sheet(df1, df2)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(output_path, engine="openpyxl") as w:
            for sheet_name, df in result.items():
                df.to_excel(w, sheet_name=sheet_name, index=False)
        print("Saved:", output_path)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Merge two subject-grade Excel stats (old + new) by course code/name."
    )
    parser.add_argument(
        "file_old",
        nargs="?",
        default="إحصائية تقديرات المواد سابقة.xlsx",
        help="Old stats file path",
    )
    parser.add_argument(
        "file_new",
        nargs="?",
        default="إحصائية تقديرات المواد حديثة.xlsx",
        help="New stats file path",
    )
    parser.add_argument(
        "-o", "--output",
        default="إحصائية تقديرات المواد مدمجة.xlsx",
        help="Output merged file path",
    )
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    path1 = Path(args.file_old)
    path2 = Path(args.file_new)
    if not path1.is_absolute():
        path1 = base / path1
        if not path1.exists():
            path1 = base.parent / args.file_old
    if not path2.is_absolute():
        path2 = base / path2
        if not path2.exists():
            path2 = base.parent / args.file_new
    out = Path(args.output)
    if not out.is_absolute():
        out = base / out

    try:
        merge_excel_files(path1, path2, out)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
