"""
extract_data.py — standalone script for parsing raw academic Excel files.
This module is a utility script (not imported by the API).
Run it directly: python extract_data.py [new_file] [old_file]
"""
from __future__ import annotations

import logging
import os
import sys

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

GPA_MAP = {
    'أ+': 4.0, 'أ': 4.0, 'أ-': 3.7,
    'ب+': 3.3, 'ب': 3.0, 'ب-': 2.7,
    'ج+': 2.3, 'ج': 2.0, 'ج-': 1.7,
    'د+': 1.3, 'د': 1.0, 'ر': 0.0,
    'A+': 4.0, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'F': 0.0,
}

# Normalized column indices based on debug_norm_head CSV:
# 0=م, 1=كود, 2=اسم, 3=المدرس, 4=المسجلين, 
# 9=دخول الامتحان, 11=حضور, 13=غياب,
# 19=نجاح(count), 20=نجاح(ratio), 21=رسوب(count), 22=رسوب(ratio)
# 23=أ+(count), 25=أ(count), 27=أ-(count), 29=ب+(count), 31=ب(count), 33=ب-(count)
# 35=ج+(count), 37=ج(count), 39=ج-(count), 41=د+(count), 43=د(count), 45=ر(count)

GRADE_COLS_IDX = [25, 27, 29, 31, 33, 35, 37, 39, 41, 43, 45, 47]
GRADE_NAMES = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']
GRADE_GPA = [4.0, 4.0, 3.7, 3.3, 3.0, 2.7, 2.3, 2.0, 1.7, 1.3, 1.0, 0.0]

def parse_sheet(xl, shname):
    raw = xl.parse(shname, header=None)
    # find header row containing course code column
    hr = None
    for i, row in raw.iterrows():
        vals = [str(v) for v in row.values]
        if any('كود' in v or 'Code' in v for v in vals):
            hr = i
            break
    if hr is None:
        return None
    
    # data starts 2 rows after header (skip the عدد/نسبة subheader)
    data_start = hr + 2
    courses = []
    for i in range(data_start, len(raw)):
        row = raw.iloc[i]
        vals = list(row.values)
        if len(vals) < 25:
            continue
        try:
            row_num = vals[0]
            if pd.isna(row_num) or str(row_num).strip() == '':
                continue
            code = str(vals[1]).strip() if not pd.isna(vals[1]) else ''
            name = str(vals[2]).strip() if not pd.isna(vals[2]) else ''
            if not code or code == 'nan':
                continue
            enrolled = vals[4]
            enrolled = int(float(enrolled)) if not pd.isna(enrolled) and str(enrolled) not in ['-','nan'] else 0
            
            # pass count at index 21 (نجاح), fail count at index 23 (رسوب)
            pass_n = vals[21] if len(vals)>21 else 0
            fail_n = vals[23] if len(vals)>23 else 0
            pass_n = int(float(pass_n)) if not pd.isna(pass_n) and str(pass_n) not in ['-','nan','-%'] else 0
            fail_n = int(float(fail_n)) if not pd.isna(fail_n) and str(fail_n) not in ['-','nan','-%'] else 0
            
            grade_counts = []
            for idx in GRADE_COLS_IDX:
                v = vals[idx] if len(vals)>idx else 0
                try:
                    v = int(float(v)) if not pd.isna(v) and str(v) not in ['-','nan','-%'] else 0
                except:
                    v = 0
                grade_counts.append(v)
            
            total_graded = sum(grade_counts)
            gpa = 0.0
            if total_graded > 0:
                gpa = sum(g * c for g, c in zip(GRADE_GPA, grade_counts)) / total_graded
            
            failure_rate = (fail_n / enrolled * 100) if enrolled > 0 else 0
            excellence_rate = ((grade_counts[0] + grade_counts[1]) / enrolled * 100) if enrolled > 0 else 0
            
            courses.append({
                'code': code,
                'name': name,
                'enrolled': enrolled,
                'pass': pass_n,
                'fail': fail_n,
                'failure_rate': round(failure_rate, 2),
                'excellence_rate': round(excellence_rate, 2),
                'gpa': round(gpa, 3),
                'grades': dict(zip(GRADE_NAMES, grade_counts)),
            })
        except Exception as e:
            pass
    return courses

def _default_path(name: str) -> str:
    """Resolve file path relative to project root or current directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, name),
        os.path.join(script_dir, "..", name),
        name,
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return name  # return as-is; caller will get a clear FileNotFoundError


def main():
    new_file = sys.argv[1] if len(sys.argv) > 1 else _default_path('إحصائية تقديرات المواد حديثة.xlsx')
    old_file = sys.argv[2] if len(sys.argv) > 2 else _default_path('إحصائية تقديرات المواد سابقة.xlsx')

    if not os.path.isfile(new_file):
        logger.error("New file not found: %s", new_file)
        sys.exit(1)
    if not os.path.isfile(old_file):
        logger.error("Old file not found: %s", old_file)
        sys.exit(1)

    xl_new = pd.ExcelFile(new_file)
    xl_old = pd.ExcelFile(old_file)

    print("=== NEW FILE SHEETS ===")
    print(xl_new.sheet_names)
    print("=== OLD FILE SHEETS ===")
    print(xl_old.sheet_names)

    all_new = {}
    for sh in xl_new.sheet_names:
        courses = parse_sheet(xl_new, sh)
        if courses:
            all_new[sh] = courses
            print(f"\n--- NEW Sheet: {sh} ({len(courses)} courses) ---")
            for c in courses:
                code = str(c.get('code', ''))[:15]
                name = str(c.get('name', ''))[:30]
                print(f"  {code:15} {name:30} enrolled={c['enrolled']:3} "
                      f"fail_rate={c['failure_rate']:5.1f}% gpa={c['gpa']:.2f} "
                      f"excellence={c['excellence_rate']:.1f}%")

    all_old = {}
    for sh in xl_old.sheet_names:
        courses = parse_sheet(xl_old, sh)
        if courses:
            all_old[sh] = courses
            print(f"\n--- OLD Sheet: {sh} ({len(courses)} courses) ---")
            for c in courses:
                code = str(c.get('code', ''))[:15]
                name = str(c.get('name', ''))[:30]
                print(f"  {code:15} {name:30} enrolled={c['enrolled']:3} "
                      f"fail_rate={c['failure_rate']:5.1f}% gpa={c['gpa']:.2f}")

    return all_new, all_old


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
