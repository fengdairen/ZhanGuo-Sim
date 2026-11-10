# -*- coding: utf-8 -*-
"""把单个国家表完整摊开：所有非空单元格 + 合并区 + 批注。"""
import sys
from pathlib import Path
import openpyxl
from openpyxl.utils import get_column_letter

SRC = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台\备份.xlsm")
SHEET = sys.argv[1] if len(sys.argv) > 1 else "鲁国"
OUT = Path(f"tools/_sheet_{SHEET}.txt")

wb = openpyxl.load_workbook(SRC, data_only=False, keep_vba=True)
ws = wb[SHEET]
L = []
def p(*a): L.append(" ".join(str(x) for x in a))

p(f"### SHEET {SHEET}  dims={ws.dimensions}")
p(f"### merged: {sorted(str(m) for m in ws.merged_cells.ranges)}")
p("")
for r in range(1, ws.max_row + 1):
    cells = []
    for c in range(1, ws.max_column + 1):
        cell = ws.cell(row=r, column=c)
        v = cell.value
        if v is None and not cell.comment:
            continue
        coord = f"{get_column_letter(c)}{r}"
        if cell.comment:
            cells.append(f"{coord}={v!r}[注:{cell.comment.text}]")
        else:
            cells.append(f"{coord}={v!r}")
    if cells:
        p(f"R{r:>3}: " + " ; ".join(cells))

# 批注单独列
p("\n### 所有批注")
for r in range(1, ws.max_row + 1):
    for c in range(1, ws.max_column + 1):
        cell = ws.cell(row=r, column=c)
        if cell.comment:
            p(f"  {get_column_letter(c)}{r}: {cell.comment.text}")

# 数据验证
p("\n### 数据验证")
for dv in ws.data_validations.dataValidation:
    p(f"  {dv.type} {dv.formula1} -> {dv.sqref}")

OUT.write_text("\n".join(L), encoding="utf-8")
print("wrote", OUT, len(L), "lines")
