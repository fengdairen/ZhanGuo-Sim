# -*- coding: utf-8 -*-
"""
把 备份.xlsm 导出成纯数据结构 (JSON)，与显示层彻底解耦。

产出：
  data/state.json             —— 权威状态（纯数据，无公式、无坐标）
  data/excel_reference.json   —— Excel 缓存值，用于公式复现校验
"""
import json
import re
import sys
from pathlib import Path
import openpyxl

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
SRC = ROOT / "备份.xlsm"
OUT_DIR = ROOT / "data"
OUT_DIR.mkdir(exist_ok=True)

SHEETS = ["鲁国", "齐国", "宋国", "魏国", "韩国", "赵国", "秦国", "越国", "楚国"]
ID_MAP = {"鲁国": "lu", "齐国": "qi", "宋国": "song", "魏国": "wei", "韩国": "han",
          "赵国": "zhao", "秦国": "qin", "越国": "yue", "楚国": "chu"}

wbv = openpyxl.load_workbook(SRC, data_only=True, keep_vba=True)   # 值
wbf = openpyxl.load_workbook(SRC, data_only=False, keep_vba=True)  # 公式


def num(v, default=0.0):
    if v is None or isinstance(v, str):
        try:
            return float(v) if v not in (None, "") else default
        except (TypeError, ValueError):
            return default
    return float(v)


def txt(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


LEVEL_MAP = {"I": 1, "II": 2, "III": 3, "IV": 4}


def parse_group_range(formula, ws_name):
    """从 C12 之类的公式里解析出税基对应的人群行号集合。"""
    if not isinstance(formula, str):
        return []
    m = re.search(r"SUM\(\s*L(\d+)\s*:\s*L(\d+)\s*\)", formula)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return list(range(a, b + 1))
    m = re.search(r"^=\s*L(\d+)\s*$", formula)
    if m:
        return [int(m.group(1))]
    return []


nations = []
reference = {}

for sheet in SHEETS:
    nid = ID_MAP[sheet]
    wsf = wbf[sheet]
    wsv = wbv[sheet]

    # ---------- 人群 ----------
    groups = []
    for r in range(43, 200):
        name = txt(wsf.cell(row=r, column=2).value)
        if name is None:
            continue
        rowvals = {
            "id": f"g{r}",
            "name": name,
            "du": num(wsf.cell(row=r, column=3).value),
            "cheng": num(wsf.cell(row=r, column=4).value),
            "yi": num(wsf.cell(row=r, column=5).value),
            "wild": num(wsf.cell(row=r, column=6).value),
            "adjustment": num(wsf.cell(row=r, column=7).value),
            "development": num(wsf.cell(row=r, column=9).value),
            "household": num(wsf.cell(row=r, column=10).value),
            "base": num(wsf.cell(row=r, column=11).value),
            # 权重是逐行不同的（例如魏国的邑权重有 30/25/20 三种），必须按行导出
            "weightDu": num(wsf.cell(row=r, column=16).value, 120),
            "weightCheng": num(wsf.cell(row=r, column=17).value, 60),
            "weightYi": num(wsf.cell(row=r, column=18).value, 30),
            "coreCity": txt(wsf.cell(row=r, column=13).value),
            "popType": txt(wsf.cell(row=r, column=14).value),
            "note": txt(wsf.cell(row=r, column=15).value),
            "_row": r,
        }
        groups.append(rowvals)

    row_to_gid = {g["_row"]: g["id"] for g in groups}

    # ---------- 税目 ----------
    taxes = []
    for col in range(3, 12):  # C..K
        tname = txt(wsf.cell(row=8, column=col).value)
        if tname is None:
            continue
        base_formula = wsf.cell(row=12, column=col).value
        rows = parse_group_range(base_formula, sheet)
        gids = [row_to_gid[r] for r in rows if r in row_to_gid]
        taxes.append({
            "id": f"t{col}",
            "name": tname,
            "baseLabel": txt(wsf.cell(row=10, column=col).value),
            "groupIds": gids,
            "amount": num(wsf.cell(row=13, column=col).value),
            "efficiency": num(wsf.cell(row=14, column=col).value),
        })

    # ---------- 开支 ----------
    expenses = []
    for r, kind in ((17, "Project"), (19, "Modifier")):
        for col in range(5, 12):  # E..K
            ename = txt(wsf.cell(row=r - 1, column=col).value)
            if ename is None:
                continue
            expenses.append({
                "id": f"e{col}{r}",
                "name": ename,
                "kind": kind,
                "amount": num(wsf.cell(row=r, column=col).value),
            })

    # ---------- 军队 ----------
    armies = []
    for r in (26, 28, 30, 32, 34, 36):
        aname = txt(wsf.cell(row=r, column=2).value)
        if aname is None:
            continue
        note = txt(wsf.cell(row=r, column=10).value)

        # 维护费公式逐兵种不同，且同兵种可能逐国不同（越国水师 250，别国 300）。
        # 因此把“单位成本系数”解析出来存成数据，而不是写死在代码里。
        maint = str(wsf.cell(row=r, column=14).value or "")
        def unit_cost(letter, default):
            m = re.search(rf"{letter}{r}\*([0-9]+(?:\.[0-9]+)?)", maint)
            return float(m.group(1)) if m else 0.0

        armies.append({
            "id": f"a{r}",
            "name": aname,
            "infantry": num(wsf.cell(row=r, column=3).value),
            "elite": num(wsf.cell(row=r, column=4).value),
            "cavalry": num(wsf.cell(row=r, column=5).value),
            "chariots": num(wsf.cell(row=r, column=6).value),
            "training": num(wsf.cell(row=r, column=7).value),
            "station": txt(wsf.cell(row=r, column=8).value),
            "commander": txt(wsf.cell(row=r, column=9).value),
            "note": note,
            "readiness": num(wsf.cell(row=r, column=12).value),
            "supply": num(wsf.cell(row=r, column=13).value),
            "costInfantry": unit_cost("C", 60),
            "costElite": unit_cost("D", 150),
            "costCavalry": unit_cost("E", 180),
            "costChariots": unit_cost("F", 300),
            "upkeepFormula": maint,
        })

    # ---------- 制度 ----------
    institutions = []
    for r in range(2, 38):
        iname = txt(wsf.cell(row=r, column=28).value)  # AB
        if iname is None or iname == "制度条目":
            continue
        lvl_raw = txt(wsf.cell(row=r, column=30).value)  # AD
        institutions.append({
            "id": f"i{r}",
            "name": iname,
            "description": txt(wsf.cell(row=r, column=29).value),  # AC
            "level": LEVEL_MAP.get(lvl_raw, 1) if lvl_raw else 1,
            "reformPoint": txt(wsf.cell(row=r, column=31).value),  # AE
        })

    # ---------- 国家时局 ----------
    situations = []
    for r in range(26, 38):
        sname = txt(wsf.cell(row=r, column=16).value)  # P
        if sname is None or sname == "国家时局":
            continue
        situations.append({
            "id": f"s{r}",
            "name": sname,
            "description": txt(wsf.cell(row=r, column=18).value),  # R
        })

    # ---------- 国力 ----------
    nation = {
        "id": nid,
        "name": txt(wsf.cell(row=2, column=2).value),
        "reserve": num(wsf.cell(row=5, column=4).value),
        "adminLevel": num(wsf.cell(row=5, column=5).value),
        "militaryDiscipline": num(wsf.cell(row=5, column=6).value),
        "corruption": num(wsf.cell(row=5, column=7).value),
        "treasury": num(wsf.cell(row=20, column=8).value),
        "weights": {
            "du": num(wsf.cell(row=43, column=16).value, 120),
            "cheng": num(wsf.cell(row=43, column=17).value, 60),
            "yi": num(wsf.cell(row=43, column=18).value, 30),
        },
        "populationGroups": [{k: v for k, v in g.items() if k != "_row"} for g in groups],
        "taxes": taxes,
        "expenses": expenses,
        "armies": armies,
        "institutions": institutions,
        "situations": situations,
    }
    nations.append(nation)

    # ---------- 参考值（Excel 缓存） ----------
    ref = {
        "population": num(wsv.cell(row=5, column=2).value),
        "totalTax": num(wsv.cell(row=16, column=3).value),
        "militaryExpense": num(wsv.cell(row=18, column=3).value),
        "adminExpense": num(wsv.cell(row=20, column=3).value),
        "balance": num(wsv.cell(row=20, column=5).value),
        "treasury": num(wsv.cell(row=20, column=8).value),
        "taxBase": [num(wsv.cell(row=12, column=c).value) for c in range(3, 3 + len(taxes))],
        "taxPaid": [num(wsv.cell(row=15, column=c).value) for c in range(3, 3 + len(taxes))],
        "groupPopulation": [num(wsv.cell(row=g["_row"], column=8).value) for g in groups],
        "groupOutput": [num(wsv.cell(row=g["_row"], column=12).value) for g in groups],
        "armyUpkeep": [num(wsv.cell(row=r, column=14).value) for r in (26, 28, 30, 32, 34, 36)],
    }
    reference[nid] = ref

state = {
    "version": 1,
    "turn": 0,
    "year": -1,
    "season": 0,
    "nations": nations,
}

(OUT_DIR / "state.json").write_text(
    json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT_DIR / "excel_reference.json").write_text(
    json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8")

print("nations:", len(nations))
for n in nations:
    print(f"  {n['name']}: groups={len(n['populationGroups'])} taxes={len(n['taxes'])} "
          f"expenses={len(n['expenses'])} armies={sum(1 for a in n['armies'] if a['note'] != '未建设')} "
          f"inst={len(n['institutions'])} sit={len(n['situations'])}")
