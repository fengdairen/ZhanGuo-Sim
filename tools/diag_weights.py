# -*- coding: utf-8 -*-
"""诊断：各国人群行的 P/Q/R 权重是否逐行不同，以及 H 公式实际引用。"""
from pathlib import Path
import openpyxl

SRC = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台\备份.xlsm")
wbv = openpyxl.load_workbook(SRC, data_only=True, keep_vba=True)
wbf = openpyxl.load_workbook(SRC, data_only=False, keep_vba=True)

SHEETS = ["鲁国", "齐国", "宋国", "魏国", "韩国", "赵国", "秦国", "越国", "楚国"]
L = []
for s in SHEETS:
    ws = wbf[s]
    L.append(f"--- {s} ---")
    L.append(f"{'行':>4} {'名称':<10} {'C':>4} {'D':>4} {'E':>4} {'F':>4} {'G':>5} {'H式':<28} {'P':>5} {'Q':>5} {'R':>5}")
    for r in range(43, 60):
        name = ws.cell(row=r, column=2).value
        if not name:
            continue
        def v(c):
            x = ws.cell(row=r, column=c).value
            return "" if x is None else x
        L.append(f"{r:>4} {str(name):<10} {v(3):>4} {v(4):>4} {v(5):>4} {v(6):>4} {v(7):>5} {str(v(8)):<28} {v(16):>5} {v(17):>5} {v(18):>5}")
    L.append("")

Path("tools/_weights_diag.txt").write_text("\n".join(L), encoding="utf-8")
print("ok")
