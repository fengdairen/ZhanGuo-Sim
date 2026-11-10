# -*- coding: utf-8 -*-
"""量化：每个国家表里，哪些格子是"人工输入"，哪些是"公式自动"，以及经济模型的数值校验。"""
from pathlib import Path
import openpyxl

SRC = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台\备份.xlsm")
wbf = openpyxl.load_workbook(SRC, data_only=False, keep_vba=True)
wbv = openpyxl.load_workbook(SRC, data_only=True, keep_vba=True)
L = []
def p(*a): L.append(" ".join(str(x) for x in a))

COUNTRIES = [ws.title for ws in wbf.worksheets if ws.title != "备用页"]

p("=== 每表：常量格 vs 公式格（分区块）===")
blocks = {
    "顶部国力(行4-21)": range(4, 22),
    "军队表(行25-37)": range(25, 38),
    "人群表(行42-199)": range(42, 200),
    "制度表(AB-AD)": None,
}
for name in COUNTRIES:
    ws = wbf[name]
    p(f"\n--- {name} ---")
    for bname, rows in blocks.items():
        const = form = 0
        if rows is None:
            for r in range(2, 38):
                for col in ("AB", "AC", "AD", "AE"):
                    v = ws[f"{col}{r}"].value
                    if v is None: continue
                    if isinstance(v, str) and v.startswith("="): form += 1
                    else: const += 1
        else:
            for r in rows:
                for c in range(1, 43):
                    v = ws.cell(row=r, column=c).value
                    if v is None: continue
                    if isinstance(v, str) and v.startswith("="): form += 1
                    else: const += 1
        p(f"  {bname:22} 常量={const:4}  公式={form:4}")

p("\n=== 鲁国经济模型实测（data_only 缓存值）===")
wsv = wbv["鲁国"]
for coord in ["B5","C12","D12","E12","C13","C14","C15","C16","C18","C20","H20","E20","C43","H43","L43","N26"]:
    p(f"  {coord:5} = {wsv[coord].value!r}")

p("\n=== 军费公式展开校验（鲁国 中军）===")
p("  N26 公式:", wbf['鲁国']['N26'].value)
p("  N26 值  :", wsv['N26'].value)

p("\n=== 各国关键指标对比 ===")
p(f"  {'国':4} {'人口合计':>10} {'总税收':>10} {'军事开支':>10} {'行政开支':>10} {'国库':>10} {'结余':>10} {'腐化':>6} {'行政建设':>8}")
for name in COUNTRIES:
    ws = wbv[name]
    def g(c):
        v = ws[c].value
        return v if isinstance(v, (int, float)) else 0
    p(f"  {name:4} {g('B5'):>10.0f} {g('C16'):>10.0f} {g('C18'):>10.0f} {g('C20'):>10.0f} {g('H20'):>10.0f} {g('E20'):>10.0f} {g('G5'):>6.2f} {g('E5'):>8.2f}")

p("\n=== 制度等级分布 ===")
for name in COUNTRIES:
    ws = wbf[name]
    lv = []
    for r in range(2, 38):
        v = ws[f"AD{r}"].value
        if isinstance(v, str) and v.strip() in ("I","II","III","IV"):
            lv.append(v.strip())
    from collections import Counter
    p(f"  {name}: {dict(Counter(lv))}  改革点标记AE: {[ws[f'AE{r}'].value for r in range(2,38) if ws[f'AE{r}'].value]}")

Path("tools/_quant.txt").write_text("\n".join(L), encoding="utf-8")
print("ok", len(L))
