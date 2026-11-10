# -*- coding: utf-8 -*-
"""结构探查：不修改原文件，只读。"""
import sys, zipfile, json
from pathlib import Path
import openpyxl

SRC = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台\备份.xlsm")
out = []

def p(*a):
    s = " ".join(str(x) for x in a)
    out.append(s)

p("FILE:", SRC, SRC.stat().st_size, "bytes")

with zipfile.ZipFile(SRC) as z:
    names = z.namelist()
p("\n=== ZIP PARTS ===")
for n in names:
    p(" ", n, z.getinfo(n).file_size if False else "")
p("has vbaProject:", any("vbaProject" in n for n in names))

wb = openpyxl.load_workbook(SRC, data_only=False, keep_vba=True)
p("\n=== SHEETS ===")
for ws in wb.worksheets:
    p(f"  {ws.title!r:32} state={ws.sheet_state:8} dims={ws.dimensions:12} max_row={ws.max_row} max_col={ws.max_column}")

p("\n=== DEFINED NAMES ===")
for name, dn in wb.defined_names.items():
    try:
        p(f"  {name} -> {dn.attr_text}")
    except Exception as e:
        p(f"  {name} -> <err {e}>")

p("\n=== PER SHEET SAMPLE (first 15 rows, non-empty only) ===")
for ws in wb.worksheets:
    p(f"\n--- {ws.title} ---")
    n = 0
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 30)):
        vals = [(c.coordinate, c.value) for c in row if c.value is not None]
        if not vals:
            continue
        p("  ", " | ".join(f"{k}={v}" for k, v in vals)[:400])
        n += 1
        if n > 14:
            break
    p(f"   merged: {[str(m) for m in ws.merged_cells.ranges][:12]}")

p("\n=== FORMULA COUNT ===")
total_f = 0
for ws in wb.worksheets:
    fc = 0
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and c.value.startswith("="):
                fc += 1
    total_f += fc
    if fc:
        p(f"  {ws.title}: {fc} formulas")
p("  TOTAL:", total_f)

text = "\n".join(out)
Path("tools/_wb_report.txt").write_text(text, encoding="utf-8")
print(text[:12000])
print("\n[full report] tools/_wb_report.txt")
