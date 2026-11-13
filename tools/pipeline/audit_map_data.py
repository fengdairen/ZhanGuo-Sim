"""体检：河流 / 湖泽 / 海岸线 数据一致性。

用法  python tools/audit_map_data.py
产物  tools/_audit.txt
"""
from __future__ import annotations

import collections
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "map" / "rivers" / "river_segments.json"
REPORT = ROOT / "tools" / "_audit.txt"

CW, CH = 9101, 8509


def seglen(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def area_of(ring):
    a = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def main():
    d = json.loads(SRC.read_text(encoding="utf-8-sig"))
    segs = d.get("segments") or []
    lakes = d.get("lakes") or []
    coasts = d.get("coasts") or []

    by_id = {s["id"]: s for s in segs}
    by_river = collections.defaultdict(list)
    for s in segs:
        by_river[s.get("river")].append(s)

    out = []
    W = out.append

    W("== 规模 ==")
    W(f"河段 {len(segs)}，河流 {len(by_river)}，湖泽 {len(lakes)}，海岸线 {len(coasts)}")
    W(f"河网总长 {sum(seglen(s['pts']) for s in segs):,.0f} px")
    W(f"湖泽总面积 {sum(area_of(l['pts']) for l in lakes):,.0f} px²")
    W("")

    # ---------- 河流 ----------
    W("== 河流：结构 ==")
    probs = []

    for s in segs:
        pts = s.get("pts") or []
        if len(pts) < 2:
            probs.append(f"{s['id']} 点数不足 {len(pts)}")
        for i in range(len(pts) - 1):
            if pts[i][0] == pts[i + 1][0] and pts[i][1] == pts[i + 1][1]:
                probs.append(f"{s['id']} 第 {i} 点与下一点重合")
                break
        L = seglen(pts) if len(pts) > 1 else 0
        if L < 25:
            probs.append(f"{s['id']} {s.get('name') or '(无名)'} 太短：{L:.0f} px")
        w = s.get("water")
        if w not in (1, 2, 3, 4, 5):
            probs.append(f"{s['id']} 水量异常 {w}")

    # 链接目标
    for s in segs:
        pts = s.get("pts") or []
        n = len(pts)
        for L in (s.get("links") or []):
            if L.get("at") not in (0, n - 1):
                probs.append(f"{s['id']} 链接端 at={L.get('at')} 不是端点（共 {n} 点）")
            if L.get("lake"):
                if L["lake"] not in {l["id"] for l in lakes}:
                    probs.append(f"{s['id']} 指向不存在的湖泽 {L['lake']}")
            elif L.get("coast"):
                if L["coast"] not in {c["id"] for c in coasts}:
                    probs.append(f"{s['id']} 指向不存在的海岸线 {L['coast']}")
            elif L.get("seg"):
                t = by_id.get(L["seg"])
                if not t:
                    probs.append(f"{s['id']} 指向不存在的河段 {L['seg']}")
                else:
                    if t["river"] == s["river"]:
                        probs.append(f"{s['id']} 挂在自己身上")
                    if not (0 <= L.get("idx", -1) < len(t["pts"])):
                        probs.append(f"{s['id']} → {L['seg']} 顶点越界 idx={L.get('idx')}")
            else:
                probs.append(f"{s['id']} 有无法识别的链接 {L}")

    # 一河多段：链是否连通
    for rid, g in by_river.items():
        if len(g) < 2:
            continue
        ends = []
        for s in g:
            pts = s["pts"]
            ends.append((s["id"], 0, (round(pts[0][0], 1), round(pts[0][1], 1))))
            ends.append((s["id"], len(pts) - 1, (round(pts[-1][0], 1), round(pts[-1][1], 1))))
        cnt = collections.Counter(k for _, _, k in ends)
        free = [e for e in ends if cnt[e[2]] == 1]
        if len(free) != 2:
            probs.append(f"河 {rid}（{g[0].get('name')}）自由端 {len(free)} 个，应为 2（切段没接上？）")
        for k, c in cnt.items():
            if c > 2:
                probs.append(f"河 {rid}（{g[0].get('name')}）有 {c} 段共用同一端点 {k}")

    # parent 与 links 一致性
    for s in segs:
        mouth_at = 0 if s.get("flow") == -1 else len(s["pts"]) - 1
        mouth_river = None
        for L in (s.get("links") or []):
            if L.get("at") == mouth_at and L.get("river"):
                mouth_river = L
        p = s.get("parent")
        if p is not None and not (p.get("river") and p.get("seg")):
            probs.append(f"{s['id']} parent 缺字段 {p}")
        if s.get("nature") == "artificial":
            continue          # 运河 parent 恒为 null，是设计
        if (p is None) != (mouth_river is None):
            probs.append(f"{s['id']} parent 与 links 不一致")
        elif p and mouth_river and (p.get("seg") != mouth_river.get("seg") or p.get("idx") != mouth_river.get("idx")):
            probs.append(f"{s['id']} parent 与 links 指向不同顶点")

    if probs:
        W(f"发现 {len(probs)} 条：")
        for p in probs:
            W("  - " + p)
    else:
        W("无结构问题")
    W("")

    # ---------- 命名 ----------
    W("== 河流：命名 ==")
    unnamed = [s for s in segs if not (s.get("name") or "").strip()]
    W(f"未命名河段 {len(unnamed)}" + ("：" + "、".join(s["id"] for s in unnamed[:12]) if unnamed else ""))
    names = collections.Counter(s["name"] for s in segs if s.get("name"))
    dup = {n: c for n, c in names.items() if c > 1}
    W(f"同名河（正常：同一条河的分段）{len(dup)} 个；跨 river 重名：", )
    cross = []
    name2river = collections.defaultdict(set)
    for s in segs:
        if s.get("name"):
            name2river[s["name"]].add(s["river"])
    for n, rs in name2river.items():
        if len(rs) > 1:
            cross.append(f"{n} × {len(rs)} 条河")
    W("  " + ("、".join(cross) if cross else "无"))
    W("")

    # ---------- 类型 ----------
    W("== 河流：类型分布 ==")
    # 与编辑器同规则（简化版：只看链两端）
    def mi(s):
        return 0 if s.get("flow") == -1 else len(s["pts"]) - 1
    def si(s):
        return len(s["pts"]) - 1 if s.get("flow") == -1 else 0
    def link_at(s, at):
        for L in (s.get("links") or []):
            if L.get("at") == at:
                return L
        return None

    def chain(rid):
        g = by_river[rid]
        if len(g) == 1:
            return (g[0], si(g[0]), g[0], mi(g[0]))
        ends = []
        for s in g:
            pts = s["pts"]
            ends.append((s, 0, (round(pts[0][0], 1), round(pts[0][1], 1))))
            ends.append((s, len(pts) - 1, (round(pts[-1][0], 1), round(pts[-1][1], 1))))
        cnt = collections.Counter(k for _, _, k in ends)
        free = [e for e in ends if cnt[e[2]] == 1]
        if len(free) != 2:
            return None
        mouth = src = None
        for e in free:
            L = link_at(e[0], e[1])
            if not L:
                continue
            if L.get("kind") in ("mouth", "sea"):
                mouth = mouth or e
            else:
                src = src or e
        if not mouth and not src:
            mouth = next((e for e in free if e[1] == mi(e[0])), free[0])
        if mouth:
            src = src or next((e for e in free if e is not mouth), None)
        if not mouth or not src:
            return None
        return (src[0], src[1], mouth[0], mouth[1])

    def level(rid, seen=None):
        seen = seen or set()
        if not rid or rid in seen:
            return 0
        seen.add(rid)
        return classify(rid, seen)[1] or 0

    def classify(rid, seen=None):
        g = by_river.get(rid) or []
        if not g:
            return ("main", 0)
        if any(s.get("nature") == "artificial" for s in g):
            return ("canal", None)
        ch = chain(rid)
        if not ch:
            return ("unknown", None)
        sseg, sat, mseg, mat = ch
        srcL, mouthL = link_at(sseg, sat), link_at(mseg, mat)
        if srcL and srcL.get("lake"):
            return ("channel", (level(mouthL.get("river"), seen) + 1) if (mouthL and mouthL.get("river")) else None)
        if srcL and srcL.get("river"):
            base = level(mouthL.get("river"), seen) if (mouthL and mouthL.get("river")) else level(srcL.get("river"), seen)
            return ("dist", base + 1)
        if mouthL and mouthL.get("river"):
            return ("trib", level(mouthL.get("river"), seen) + 1)
        return ("main", 0)

    kinds = collections.Counter()
    deep = []
    for rid, g in by_river.items():
        k, lv = classify(rid)
        kinds[k] += 1
        if k == "unknown":
            deep.append(g[0].get("name") or rid)
        if lv and lv > 4:
            deep.append(f"{g[0].get('name') or rid}（{k} {lv} 级）")
    W("  " + " / ".join(f"{k} {v}" for k, v in kinds.most_common()))
    if deep:
        W("  需要留意：" + "、".join(deep))
    W("")

    # ---------- 湖泽 ----------
    W("== 湖泽 ==")
    lp = []
    lake_names = collections.Counter(l.get("name") or "" for l in lakes)
    for l in lakes:
        pts = l.get("pts") or []
        if len(pts) < 4:
            lp.append(f"{l['id']} 点数不足 {len(pts)}")
            continue
        a = area_of(pts)
        if a < 120:
            lp.append(f"{l['id']} {l.get('name') or '(无名)'} 面积过小 {a:.0f} px²")
        if pts[0] != pts[-1]:
            lp.append(f"{l['id']} 环没有闭合")
        for pc in (l.get("pieces") or []):
            if pc.get("kind") == "river":
                f, t = pc.get("from") or {}, pc.get("to") or {}
                for tag, ref in (("from", f), ("to", t)):
                    sg = by_id.get(ref.get("seg"))
                    if not sg:
                        lp.append(f"{l['id']} 的河段引用 {tag} 指向不存在的河段 {ref.get('seg')}")
                    elif not (0 <= ref.get("idx", -1) < len(sg["pts"])):
                        lp.append(f"{l['id']} 的河段引用 {tag} 顶点越界")
            elif pc.get("kind") == "free":
                if len(pc.get("pts") or []) < 2:
                    lp.append(f"{l['id']} 有手绘段少于 2 点")
            else:
                lp.append(f"{l['id']} 未知段类型 {pc.get('kind')}")
    dupl = [n for n, c in lake_names.items() if c > 1 and n]
    if dupl:
        lp.append("重名湖泽：" + "、".join(dupl))
    if lp:
        W(f"发现 {len(lp)} 条：")
        for x in lp:
            W("  - " + x)
    else:
        W("无问题")
    areas = sorted(((area_of(l['pts']), l.get('name') or l['id']) for l in lakes if len(l.get('pts') or []) > 3))
    W("  最小 5 个：" + "、".join(f"{n} {a:.0f}" for a, n in areas[:5]))
    W("  最大 5 个：" + "、".join(f"{n} {a:.0f}" for a, n in areas[-5:]))
    W("")

    # ---------- 海岸线 ----------
    W("== 海岸线 ==")
    cp = []
    for c in coasts:
        pts = c.get("pts") or []
        L = seglen(pts)
        gap = math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) if len(pts) > 1 else -1
        closed = bool(c.get("closed"))
        W(f"  {c['id']}  {len(pts)} 点  长 {L:,.0f} px  首尾距 {gap:.1f}  {'闭合' if closed else '开放'}")
        if closed and gap > 0.5:
            cp.append(f"{c['id']} 标为闭合但首尾差 {gap:.1f}px")
        if not closed:
            # 开放岸线的端点应在图幅边附近，海面推导依赖这个
            for e in (pts[0], pts[-1]):
                near = min(abs(e[0]), abs(e[0] - CW), abs(e[1]), abs(e[1] - CH))
                if near > 30:
                    cp.append(f"{c['id']} 开放端 {e} 离图幅边 {near:.0f}px，会影响海面推导")
    if cp:
        W(f"发现 {len(cp)} 条：")
        for x in cp:
            W("  - " + x)
    else:
        W("  无问题")
    W("")

    # ---------- 跨层 ----------
    W("== 跨层检查 ==")
    # 河口/源头落在海面里却没接海岸线
    sea_path = ROOT / "data" / "map" / "vector" / "sea_from_coast.json"
    xp = []
    if sea_path.exists():
        sea = json.loads(sea_path.read_text(encoding="utf-8"))[0]

        def in_poly(p, poly):
            x, y = p
            c = False
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]
                if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                    c = not c
            return c

        for s in segs:
            for L in (s.get("links") or []):
                if L.get("kind") == "sea":
                    break
            else:
                for at in (0, len(s["pts"]) - 1):
                    if in_poly(s["pts"][at], sea):
                        xp.append(f"{s['id']} {s.get('name') or ''} 端点在海上但没有接海岸线")
                        break
    if xp:
        W(f"发现 {len(xp)} 条：")
        for x in xp[:20]:
            W("  - " + x)
        if len(xp) > 20:
            W(f"  …… 共 {len(xp)} 条")
    else:
        W("无问题")

    # ---------- 漏吸附 / 孤立 ----------
    W("")
    W("== 端点是否漏吸附 ==")
    miss = []
    for s in segs:
        pts = s["pts"]
        for at in (0, len(pts) - 1):
            if link_at(s, at):
                continue
            p0 = pts[at]
            best = None
            for t in segs:
                if t["river"] == s["river"]:
                    continue
                # 对方已经挂到本河上就不算漏接（链接只存一侧）
                if any((L.get("river") == s["river"]) for L in (t.get("links") or [])):
                    continue
                for q in t["pts"]:
                    dd = math.hypot(q[0] - p0[0], q[1] - p0[1])
                    if best is None or dd < best[0]:
                        best = (dd, t["id"])
            for l in lakes:
                if any((L.get("lake") == l["id"]) for sg in segs
                       for L in (sg.get("links") or []) if sg["river"] == s["river"]):
                    continue
                for q in l["pts"][:-1]:
                    dd = math.hypot(q[0] - p0[0], q[1] - p0[1])
                    if best is None or dd < best[0]:
                        best = (dd, l["id"])
            if best and best[0] <= 6:
                miss.append(f"{s['id']} {s.get('name') or ''} 的 {'首' if at == 0 else '末'}端离 {best[1]} 只有 {best[0]:.1f}px 却没接")
    if miss:
        W(f"发现 {len(miss)} 条（可能是漏吸附）：")
        for x in miss[:20]:
            W("  - " + x)
        if len(miss) > 20:
            W(f"  …… 共 {len(miss)} 条")
    else:
        W("无")

    W("")
    W("== 孤立要素 ==")
    solo = [f"{s['id']} {s.get('name') or ''}" for s in segs if not (s.get("links") or [])]
    W(f"两端都没接的河段：{len(solo)}" + ("（" + "、".join(solo[:10]) + "）" if solo else ""))
    dry = [l.get("name") or l["id"] for l in lakes
           if not any((L.get("lake") == l["id"]) for s in segs for L in (s.get("links") or []))]
    W(f"没有河接进来的湖泽：{len(dry)}" + ("（" + "、".join(dry[:10]) + "）" if dry else ""))

    REPORT.write_text("\n".join(out), encoding="utf-8")
    print("报告 →", REPORT)


if __name__ == "__main__":
    main()
