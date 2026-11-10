# -*- coding: utf-8 -*-
"""清理 OCR 把「城池图例小方框」误认成汉字的问题，并合并用户勘误。

规则：
  1) 用户勘误优先（correction 列，"-" 表示清空）；
  2) 去掉首尾的方框类字符（口 囗 回 〇 ロ ㅁ）——那是图例；
  3) 中间出现方框 → 说明两个名字（或城名+水名）被粘在一起：
     拆成多段，优先取 1–2 字且不以「水/山/泽/原」结尾的段；
     这类全部记为「多段存疑」，进待办让人复核。
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
BOX = "口囗回〇ロㅁ"
GEO = ("水", "山", "泽", "原", "池", "川")

# 1) 用户勘误
fix = {}
rp = ROOT / "data" / "map" / "review_todo.csv"
if rp.exists():
    for r in csv.DictReader(rp.open(encoding="utf-8-sig")):
        c = (r.get("correction") or "").strip()
        if c:
            fix[r["id"]] = "" if c in ("-", "—", "空") else c
print("用户勘误", len(fix))

rows = list(csv.DictReader((ROOT / "data" / "map" / "nodes.csv").open(encoding="utf-8-sig")))
suspect = []

for r in rows:
    if r["id"] in fix:
        r["name"] = fix[r["id"]]
        continue

    name = r["name"]
    if not name:
        continue
    if not any(ch in name for ch in BOX):
        continue

    segs = [s for s in re.split(f"[{BOX}]+", name) if s]
    if not segs:
        r["name"] = ""
        continue
    if len(segs) == 1:
        r["name"] = segs[0]
        continue

    # 多段：优先 1–2 字且不像地物
    def score(s):
        pen = 10 if s.endswith(GEO) else 0
        return (pen, 0 if 1 <= len(s) <= 2 else 1, len(s))

    segs_sorted = sorted(segs, key=score)
    pick = segs_sorted[0]
    r["name"] = pick
    suspect.append({"id": r["id"], "raw": name, "pick": pick, "segs": segs})

print("清理后仍是方框？", sum(1 for r in rows if any(ch in r["name"] for ch in BOX)))
print("多段存疑", len(suspect))

with (ROOT / "data" / "map" / "nodes.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["id", "name", "kind", "x", "y"])
    for r in rows:
        w.writerow([r["id"], r["name"], r["kind"], r["x"], r["y"]])

(ROOT / "tools" / "_suspect.json").write_text(json.dumps(suspect, ensure_ascii=False), encoding="utf-8")

named = sum(1 for r in rows if r["name"])
print(f"已命名 {named}/{len(rows)}")
