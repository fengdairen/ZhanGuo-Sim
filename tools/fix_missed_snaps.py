"""修补"端点和目标重合却没有链接"的四处（体检报告里的漏吸附）。

- r032 丹水   首端压在 睢水(r031) 上 → 记 branch（岔出）
- r053 芍陂西水道 末端压在 芍陂(l011) → 记 mouth(lake)
- r054 芍陂东水道 末端压在 芍陂(l011) → 记 mouth(lake)
- r063 苕水   末端压在 五湖(l016) → 记 mouth(lake)

用法  python tools/fix_missed_snaps.py        # 只打印
      python tools/fix_missed_snaps.py --apply
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "map" / "rivers" / "river_segments.json"

RIVER_FIX = [("r032", "r031")]
LAKE_FIX = [("r053", "l011"), ("r054", "l011"), ("r063", "l016")]


def main():
    apply = "--apply" in sys.argv
    lakes_only = "--lakes-only" in sys.argv
    d = json.loads(SRC.read_text(encoding="utf-8-sig"))
    seg = {s["id"]: s for s in d["segments"]}
    lake = {l["id"]: l for l in d["lakes"]}

    changes = []

    for sid, tid in ([] if lakes_only else RIVER_FIX):
        s, t = seg[sid], seg[tid]
        for at in (0, len(s["pts"]) - 1):
            if any(L.get("at") == at for L in (s.get("links") or [])):
                continue
            best = None
            for i, q in enumerate(t["pts"]):
                dd = math.hypot(q[0] - s["pts"][at][0], q[1] - s["pts"][at][1])
                if best is None or dd < best[0]:
                    best = (dd, i)
            if best and best[0] <= 0.5:
                changes.append((s, at, {"at": at, "kind": "branch", "river": t["river"],
                                        "seg": t["id"], "idx": best[1]},
                                f"{at} 端 ← {t.get('name')} 第 {best[1]+1} 点"))

    for sid, lid in LAKE_FIX:
        s, l = seg[sid], lake[lid]
        mouth = 0 if s.get("flow") == -1 else len(s["pts"]) - 1
        if any(L.get("at") == mouth for L in (s.get("links") or [])):
            continue
        best = None
        for i, q in enumerate(l["pts"][:-1]):
            dd = math.hypot(q[0] - s["pts"][mouth][0], q[1] - s["pts"][mouth][1])
            if best is None or dd < best[0]:
                best = (dd, i)
        if best and best[0] <= 0.5:
            changes.append((s, mouth, {"at": mouth, "kind": "mouth", "lake": l["id"], "idx": best[1]},
                            f"河口端 ← {l.get('name')} 第 {best[1]+1} 点"))

    for s, at, link, desc in changes:
        print(f"{s['id']} {s.get('name')}  {desc}")

    if not changes:
        print("没有需要修补的")
        return
    if not apply:
        print("\n（只看不改；加 --apply 才会写回）")
        return

    shutil.copy2(SRC, SRC.parent / "_backup"
                 / f"river_segments-{time.strftime('%Y%m%d-%H%M%S')}-beforesnapfix.json")
    for s, at, link, desc in changes:
        s.setdefault("links", []).append(link)
        s["links"].sort(key=lambda L: L["at"])
        # 焊到目标顶点
        if link.get("lake"):
            q = lake[link["lake"]]["pts"][link["idx"]]
        else:
            q = seg[link["seg"]]["pts"][link["idx"]]
        s["pts"][at] = [q[0], q[1]]

    tmp = SRC.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, SRC)
    print(f"\n已写回 {len(changes)} 处")


if __name__ == "__main__":
    main()
