# -*- coding: utf-8 -*-
"""把描迹数据同步进编辑器目录，生成 dist/river-editor/river_data.js。

用途：编辑器打开时自动带上当前数据（浏览器里 file:// 不能 fetch JSON，
所以用 <script> 注入 window.RIVER_SEED）。

同时做数据迁移（v1 → v2）：
  v1 的河段只有 id/rank/name/pts/joins
  v2 增加 river（同一条河的分段共用）、water（1–5）
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "data" / "map" / "rivers" / "river_segments.json"
FALLBACK = ROOT / "river_segments.json"      # 用户直接导出到根目录时
OUT = ROOT / "dist" / "river-editor" / "river_data.js"


def migrate(segs):
    out = []
    for s in segs:
        pts = s.get("pts") or []
        if len(pts) < 2:
            continue
        rank = s.get("rank") if s.get("rank") in (1, 2, 3, 4) else 1
        water = min(5, max(1, int(s.get("water") or 3)))
        # flow: 1 = 沿 pts 顺序流（末点河口），-1 = 反向。老数据按 joins 推。
        if s.get("flow") in (1, -1):
            flow = int(s["flow"])
        elif s.get("parent") and (s.get("joins") or []):
            flow = -1 if (s["joins"][0].get("at") == 0) else 1
        else:
            flow = 1
        # links：每条河可挂 0–2 个端；老数据用 parent/joins 推
        links = []
        mouth_at = 0 if flow == -1 else len(pts) - 1
        for L in (s.get("links") or []):
            at = 0 if L.get("at") == 0 else len(pts) - 1
            if L.get("kind") == "sea":
                links.append({"at": at, "kind": "sea", "coast": L.get("coast"), "idx": int(L.get("idx") or 0)})
                continue
            if L.get("lake"):
                links.append({"at": at, "kind": L.get("kind") if L.get("kind") in ("mouth", "branch") else "mouth",
                              "lake": L.get("lake"), "idx": int(L.get("idx") or 0)})
                continue
            kind = L.get("kind") if L.get("kind") in ("mouth", "branch") else ("mouth" if at == mouth_at else "branch")
            links.append({
                "at": at, "kind": kind,
                "river": L.get("river"), "seg": L.get("seg"), "idx": int(L.get("idx") or 0),
            })
        if not links and s.get("parent") and (s.get("joins") or []):
            j = s["joins"][0]
            links.append({
                "at": 0 if j.get("at") == 0 else len(pts) - 1, "kind": "mouth",
                "river": s["parent"].get("river"), "seg": s["parent"].get("seg"),
                "idx": int(s["parent"].get("idx") or 0),
            })
        links.sort(key=lambda L: L["at"])
        mouth_links = [L for L in links if L.get("kind") == "mouth" and L.get("river")]
        if rank == 4:
            parent = None
        elif s.get("parent"):
            parent = s["parent"]
        elif mouth_links:
            parent = {"river": mouth_links[0]["river"], "seg": mouth_links[0]["seg"], "idx": mouth_links[0]["idx"]}
        else:
            parent = None

        out.append({
            "id": s.get("id") or f"r{len(out)+1:03d}",
            "river": s.get("river") or "R_" + str(s.get("id") or len(out) + 1),
            "rank": rank,
            "name": s.get("name") or "",
            "section": s.get("section") or "",
            "water": water,
            "flow": flow,
            "links": links,
            "parent": parent,
            "pts": [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in pts],
            "joins": s.get("joins") or [],
        })
    return out


def pick_src():
    if CANON.exists():
        d = json.loads(CANON.read_text(encoding="utf-8-sig"))
        if d.get("segments"):
            return CANON, d
    if FALLBACK.exists():
        d = json.loads(FALLBACK.read_text(encoding="utf-8-sig"))
        return FALLBACK, d
    return None, None


def main():
    src, d = pick_src()
    if not src:
        print("没有找到描迹数据")
        sys.exit(2)

    segs = migrate(d.get("segments", []))
    payload = {
        "version": 5,
        "canvas": [9101, 8509],
        "exportedAt": d.get("exportedAt"),
        "coasts": d.get("coasts") or [],
        "lakes": d.get("lakes") or [],
        "segments": segs,
    }

    # 1) 写回规范位置（临时文件 + 原子替换）
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    tmp = CANON.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, CANON)

    # 2) 生成注入用 JS
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.RIVER_SEED = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
                   encoding="utf-8")

    by = {}
    for s in segs:
        by[s["rank"]] = by.get(s["rank"], 0) + 1
    names = {}
    for s in segs:
        if s["name"]:
            names[s["name"]] = names.get(s["name"], 0) + 1
    print(f"源 {src.name} → {CANON.relative_to(ROOT)} / {OUT.relative_to(ROOT)}")
    print(f"河段 {len(segs)}  等级分布 {by}  命名河流 {list(names)}")


if __name__ == "__main__":
    main()
