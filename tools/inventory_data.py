# -*- coding: utf-8 -*-
"""列出 data 目录下各表的行数，供文档引用。"""
import json
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
L = []
for p in sorted((ROOT / "data" / "map").glob("*.csv")):
    n = p.name
    if n.startswith("_") or "review" in n:
        continue
    try:
        with p.open(encoding="utf-8-sig") as f:
            cnt = sum(1 for _ in f) - 1
    except Exception:
        cnt = -1
    kb = p.stat().st_size / 1024
    L.append(f"{n}\t{cnt}\t{kb:.1f}KB")

st = ROOT / "data" / "state.json"
L.append(f"state.json\t-\t{st.stat().st_size/1024:.1f}KB")

(ROOT / "tools" / "_datainv.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
