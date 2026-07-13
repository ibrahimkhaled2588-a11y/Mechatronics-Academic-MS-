import sys
import re
from pathlib import Path

import pandas as pd

from excel_reader import read_excel_adaptive


def _safe_name(name: str) -> str:
    """Sanitize sheet name for filesystem use."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(name))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python debug_inspect_excel.py <path_to_excel>")
        sys.exit(1)
    path = sys.argv[1]

    # Raw view
    xls = pd.ExcelFile(path)
    print("Sheets:", xls.sheet_names)
    out_dir = Path(".")
    for sheet in xls.sheet_names:
        print("\n=== Sheet:", sheet, "=== RAW ===")
        df = xls.parse(sheet)
        print("Columns:")
        for c in df.columns:
            print(" -", repr(c))
        # Save head to CSV (UTF-8) so we can inspect it safely in Cursor
        raw_csv = out_dir / f"debug_raw_head_{_safe_name(sheet)}.csv"
        df.head(10).to_csv(raw_csv, index=False, encoding="utf-8-sig")
        print(f"Saved raw head to {raw_csv}")

    # Normalized view via read_excel_adaptive
    print("\n=== Normalized via read_excel_adaptive ===")
    dfs = read_excel_adaptive(path)
    for sheet, df_norm in dfs.items():
        print("\n--- Sheet:", sheet, "normalized ---")
        norm_csv = out_dir / f"debug_norm_head_{_safe_name(sheet)}.csv"
        df_norm.head(10).to_csv(norm_csv, index=False, encoding="utf-8-sig")
        # Avoid printing full column names to prevent Windows console encoding issues
        print(f"Saved normalized head to {norm_csv}")


if __name__ == "__main__":
    main()


