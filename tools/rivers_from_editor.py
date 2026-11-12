# -*- coding: utf-8 -*-
"""把河流描迹器导出的 river_segments.json 转成矢量地图用的河网数据。

输入：data/map/rivers/river_segments.json（描迹器 / sync_river_editor.py 生成）
输出：
  data/map/vector/rivers.json       折线点列（[[x,y],...]）
  data/map/vector/rivers_w.json     [[线宽, x1,y1,x2,y2, ...], ...]
  data/map/vector/rivers_meta.json  [{id, river, name, rank, water, len}]  供后续标注/玩法使用
  tools/_rivers_report.txt          统计

线宽 = 等级基准宽 × 水量系数：
  等级基准：1 干流 9.0 / 2 一级 5.5 / 3 二级 3.2 / 4 运河 4.0
  水量系数：0.85 + 0.06 × 水量（水量 1→0.91，3→1.03，5→1.15）
与描迹器里的显示公式一致，保证「画的时候看到的」=「地图上呈现的」。

写入采用临时文件 + 原子替换。
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "map" / "rivers" / "river_segments.json"
VEC = ROOT / "data" / "map" / "vector"
REPORT = ROOT / "tools" / "_rivers_report.txt"

# 线宽只由水量决定（与描迹器 WATER_WIDTH 一致）：等级只表示「谁汇入谁」
WATER_WIDTH = {1: 2.4, 2: 3.6, 3: 5.2, 4: 7.4, 5: 10.0}
RANK_NAME = {1: "干流", 2: "一级支流", 3: "二级支流", 4: "运河"}


def width_of(water):
    return WATER_WIDTH[max(1, min(5, int(water or 3)))]


def atomic_write(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main():
    if not SRC.exists():
        print(f"缺少描迹文件：{SRC}")
        sys.exit(2)

    data = json.loads(SRC.read_text(encoding="utf-8-sig"))
    segs = data.get("segments", [])
    lines, pts_flat, meta, anchors = [], [], [], []

    # ---- 类型判定（与编辑器同一套规则）----
    CN = ["", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

    def src_link(seg):
        pts = seg.get("pts") or []
        if not pts:
            return None
        # flow=-1 时河口在首点，源头在末点；否则反过来
        at = (len(pts) - 1) if seg.get("flow") == -1 else 0
        for L in (seg.get("links") or []):
            if L.get("at") == at:
                return L
        return None

    def mouth_river_link(seg):
        pts = seg.get("pts") or []
        if not pts:
            return None
        at = len(pts) - 1 if seg.get("flow") != -1 else 0
        for L in (seg.get("links") or []):
            if L.get("at") == at and L.get("river"):
                return L
        return None

    first_of_river = {}
    for sg in data.get("segments") or []:
        first_of_river.setdefault(sg.get("river"), sg)

    def river_level(rid, seen=None):
        if not rid:
            return 0
        seen = seen or set()
        if rid in seen:
            return 0
        seen.add(rid)
        sg = first_of_river.get(rid)
        if not sg:
            return 0
        return classify(sg, seen)[1] or 0

    def lv_name(lv):
        return (CN[lv] if lv <= 10 else str(lv)) + "级支流"

    def classify(seg, seen=None):
        """→ (kind, level, label)；label 已含"·次级"后缀"""
        if seg.get("nature") == "artificial":
            return ("canal", None, "运河")
        L = src_link(seg)
        m = mouth_river_link(seg)
        if L and L.get("lake"):
            lv = (river_level(m.get("river"), seen) + 1) if m else None
            return ("channel", lv, "天然水道" + ("·" + lv_name(lv) if m else ""))
        if L and L.get("river"):
            base = (river_level(m.get("river"), seen) if m
                    else river_level(L.get("river"), seen))
            lv = base + 1
            return ("dist", lv, "岔流·" + lv_name(lv))
        if m:
            lv = river_level(m.get("river"), seen) + 1
            return ("trib", lv, lv_name(lv))
        return ("main", 0, "干流")

    stat = {r: [0, 0.0] for r in (1, 2, 3, 4)}
    rivers = {}
    bad = 0
    for s in segs:
        pts = s.get("pts") or []
        if len(pts) < 2:
            bad += 1
            continue
        rank = int(s.get("rank", 1))
        water = int(s.get("water", 3) or 3)
        w = width_of(water)
        clean = [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in pts]
        L = sum(((clean[i + 1][0] - clean[i][0]) ** 2 + (clean[i + 1][1] - clean[i][1]) ** 2) ** 0.5
                for i in range(len(clean) - 1))
        stat[rank][0] += 1
        stat[rank][1] += L
        pts_flat.append(clean)
        lines.append([w] + [c for xy in clean for c in xy])
        meta.append({
            "id": s.get("id"), "river": s.get("river"),
            "name": s.get("name") or "", "section": s.get("section") or "",
            "rank": rank, "water": water, "width": w, "len": round(L),
            "kind": classify(s)[0], "level": classify(s)[1], "label": classify(s)[2],
            "flow": int(s.get("flow", 1)),
            "parent": s.get("parent") or None,
        })
        # 供标注用：记下这一段的几何中点
        mid = clean[len(clean) // 2]
        anchors.append({
            "id": s.get("id"), "river": s.get("river"),
            "name": s.get("name") or "", "rank": rank, "water": water,
            "x": mid[0], "y": mid[1], "len": L,
        })
        key = s.get("river") or s.get("id")
        r = rivers.setdefault(key, {"name": s.get("name") or "", "rank": rank, "sections": 0, "len": 0.0})
        r["sections"] += 1
        r["len"] += L
        if not r["name"] and s.get("name"):
            r["name"] = s["name"]

    if not lines:
        print("描迹文件里没有有效河段（每条至少 2 个点）")
        sys.exit(3)

    VEC.mkdir(parents=True, exist_ok=True)
    atomic_write(VEC / "rivers.json", json.dumps(pts_flat, separators=(",", ":")))
    atomic_write(VEC / "rivers_w.json", json.dumps(lines, separators=(",", ":")))
    atomic_write(VEC / "rivers_meta.json",
                 json.dumps({"rivers": rivers, "sections": meta}, ensure_ascii=False, separators=(",", ":")))

    # 每条命名河流取最长的一段作为标注锚点
    best = {}
    for a in anchors:
        if not a["name"]:
            continue
        cur = best.get(a["river"])
        if cur is None or a["len"] > cur["len"]:
            best[a["river"]] = a
    labels = [{"name": v["name"], "x": v["x"], "y": v["y"], "rank": v["rank"],
               "water": v["water"], "len": round(v["len"])} for v in best.values()]
    labels.sort(key=lambda t: -t["len"])
    atomic_write(VEC / "river_labels.json",
                 json.dumps(labels, ensure_ascii=False, separators=(",", ":")))

    # 描迹海岸线 → 矢量层
    coasts = []
    for c in (data.get("coasts") or []):
        pts = c.get("pts") or []
        if len(pts) < 2:
            continue
        clean = [[round(float(q[0]), 1), round(float(q[1]), 1)] for q in pts]
        closed = bool(c.get("closed"))
        if closed and clean[0] != clean[-1]:
            clean.append(list(clean[0]))
        coasts.append({"id": c.get("id"), "closed": closed,
                       "pts": [v for xy in clean for v in xy]})
    atomic_write(VEC / "coast_drawn.json",
                 json.dumps(coasts, ensure_ascii=False, separators=(",", ":")))

    # 描迹湖泽 → 矢量层（闭合多边形）
    lakes_drawn = []
    for l in (data.get("lakes") or []):
        pts = l.get("pts") or []
        if len(pts) < 3:
            continue
        clean = [[round(float(q[0]), 1), round(float(q[1]), 1)] for q in pts]
        if clean[0] != clean[-1]:
            clean.append(list(clean[0]))
        body = clean[:-1] if clean[0] == clean[-1] else clean
        cx = sum(p[0] for p in body) / len(body)
        cy = sum(p[1] for p in body) / len(body)
        lakes_drawn.append({"id": l.get("id"), "name": l.get("name") or "",
                            "cx": round(cx, 1), "cy": round(cy, 1),
                            "pts": [v for xy in clean for v in xy]})
    atomic_write(VEC / "lakes_drawn.json",
                 json.dumps(lakes_drawn, ensure_ascii=False, separators=(",", ":")))

    rep = []
    rep.append(f"源文件 {SRC.name}  版本 {data.get('version')}  导出时间 {data.get('exportedAt', '?')}")
    rep.append(f"河段 {len(lines)} 条（无效/过短跳过 {bad} 条），河流 {len(rivers)} 条")
    for r in (1, 2, 3, 4):
        n, L = stat[r]
        rep.append(f"  {RANK_NAME[r]}: {n} 段，总长 {L:.0f} px" + (f"（均长 {L / n:.0f} px）" if n else ""))
    total = sum(v[1] for v in stat.values())
    rep.append(f"合计 {total:.0f} px")
    rep.append(f"海岸线 {len(coasts)} 条（其中闭合环 {sum(1 for c in coasts if c['closed'])} 条）")
    rep.append(f"湖泽 {len(lakes_drawn)} 处")
    rep.append("")
    named = {k: v for k, v in rivers.items() if v["name"]}
    if named:
        rep.append("已命名河流：")
        for k, v in named.items():
            rep.append(f"  {v['name']}（{RANK_NAME[v['rank']]}）× {v['sections']} 段，{v['len']:.0f} px")
    else:
        rep.append("尚未命名任何河流。")
    REPORT.write_text("\n".join(rep), encoding="utf-8")

    print(f"OK 河段 {len(lines)} / 河流 {len(rivers)} → {VEC/'rivers_w.json'}")
    print(f"报告 → {REPORT}")


if __name__ == "__main__":
    main()
