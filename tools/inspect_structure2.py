# -*- coding: utf-8 -*-
"""补充结构：备用页全文、隐藏行列、保护、跨表标签一致性、是否有回合/年份字段。"""
from pathlib import Path
import openpyxl
from openpyxl.utils import get_column_letter

SRC = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台\备份.xlsm")
wb = openpyxl.load_workbook(SRC, data_only=False, keep_vba=True)
L = []
def p(*a): L.append(" ".join(str(x) for x in a))

p("=== 工作表保护 / 隐藏行列 ===")
for ws in wb.worksheets:
    hid_r = [r for r, d in ws.row_dimensions.items() if d.hidden]
    hid_c = [c for c, d in ws.column_dimensions.items() if d.hidden]
    p(f"  {ws.title}: protected={ws.protection.sheet} hidden_rows={hid_r[:20]} hidden_cols={hid_c[:20]} freeze={ws.freeze_panes}")

p("\n=== 备用页 全文 ===")
ws = wb["备用页"]
for r in range(1, ws.max_row + 1):
    cells = []
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=r, column=c).value
        if v is not None:
            cells.append(f"{get_column_letter(c)}{r}={v!r}")
    if cells:
        p(f"  R{r}: " + " ; ".join(cells))

p("\n=== 各表 A2 / AH2 / B1 内容（合并区锚点）===")
for ws in wb.worksheets:
    p(f"  {ws.title}: A1={ws['A1'].value!r} A2={ws['A2'].value!r} AH2={ws['AH2'].value!r} B1={ws['B1'].value!r} B40={ws['B40'].value!r}")

p("\n=== 是否有 年/月/回合/时间 字段 ===")
import re
pat = re.compile(r"(年|月|回合|季度|时间|轮|岁)")
for ws in wb.worksheets:
    hits = []
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and pat.search(cell.value) and len(cell.value) < 30:
                hits.append(f"{cell.coordinate}={cell.value}")
    if hits:
        p(f"  {ws.title}: {hits[:15]}")

p("\n=== 各行标签（B列）一致性：以鲁国为基准 ===")
base = wb["鲁国"]
base_labels = {}
for r in range(1, 60):
    v = base.cell(row=r, column=2).value
    if isinstance(v, str) and not v.startswith("="):
        base_labels[r] = v
for ws in wb.worksheets:
    if ws.title in ("备用页",):
        continue
    diff = []
    for r, lbl in base_labels.items():
        v = ws.cell(row=r, column=2).value
        if v != lbl:
            diff.append(f"R{r}: {lbl!r} -> {v!r}")
    p(f"  {ws.title}: diff={diff if diff else '无'}")

Path("tools/_structure2.txt").write_text("\n".join(L), encoding="utf-8")
print("ok", len(L))
