# -*- coding: utf-8 -*-
"""把参考位图矢量化成画布坐标下的折线/多边形（全分辨率走线版）。

输入（全部 9101x8509 全画布，偏移 0,0）：
  底图河道湖泊.png   红(255,0,0)=河 蓝(0,42,255)=湖 棕(101,55,0)=边界
  底图海岸线.png     黑=海岸线
  ditu.png           仅用于取海面色块（导出海的多边形）

关键经验：这几张图在原分辨率下已经是 1px 线条，**不能降采样**——
1/2 尺度 max 池化会把 1px 撑成 2px，8 邻接度直方图从「全是 2」变成
「3 和 4 占一半」，Zhang-Suen 细化随即卡死，走线被切碎。

输出 data/map/vector/*.json，坐标单位=画布像素，y 向下。
湖的特殊处理：每个湖都被一圈红线包着（那是湖岸不是河），
先把蓝块膨胀后覆盖的红像素剔掉，湖岸交给湖多边形自己描边。
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

W, H = 9101, 8509
S_SEA = 2                      # 只有海多边形降采样（轮廓长，全分辨率太慢）
ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "data" / "map" / "vector"
REPORT = ROOT / "tools" / "_vec_report.txt"
lines = []


def log(m):
    lines.append(str(m))


def load_rgb(name):
    return np.array(Image.open(ROOT / name).convert("RGB")).astype(np.int16)


# ---------------- 掩膜 ----------------
riv = load_rgb("底图河道湖泊.png")
red = (riv[..., 0] > 200) & (riv[..., 1] < 80) & (riv[..., 2] < 80)
blue = (riv[..., 2] > 200) & (riv[..., 0] < 80) & (riv[..., 1] < 80)
brown = (np.abs(riv[..., 0] - 101) <= 30) & (np.abs(riv[..., 1] - 55) <= 30) & (riv[..., 2] <= 45)
del riv
coa_rgb = load_rgb("底图海岸线.png")
coast = coa_rgb.max(axis=2) < 60
del coa_rgb
ditu = load_rgb("ditu.png")
water = ((np.abs(ditu[..., 0] - 199) <= 5) & (np.abs(ditu[..., 1] - 154) <= 5)
         & (np.abs(ditu[..., 2] - 102) <= 5))
del ditu
log(f"掩膜: 河 {int(red.sum())}  湖 {int(blue.sum())}  边界 {int(brown.sum())}  海岸 {int(coast.sum())}")


def dilate(m, n=1):
    out = m.copy()
    for _ in range(n):
        p = np.zeros_like(out)
        p[1:, :] |= out[:-1, :]
        p[:-1, :] |= out[1:, :]
        p[:, 1:] |= out[:, :-1]
        p[:, :-1] |= out[:, 1:]
        out |= p
    return out


def thin(img, max_iter=20):
    p = img.copy()
    for _ in range(max_iter):
        changed = False
        for step in (0, 1):
            pad = np.pad(p, 1)
            p2 = pad[:-2, 1:-1]
            p3 = pad[:-2, 2:]
            p4 = pad[1:-1, 2:]
            p5 = pad[2:, 2:]
            p6 = pad[2:, 1:-1]
            p7 = pad[2:, :-2]
            p8 = pad[1:-1, :-2]
            p9 = pad[:-2, :-2]
            B = (p2.astype(np.uint8) + p3 + p4 + p5 + p6 + p7 + p8 + p9)
            seq = (p2, p3, p4, p5, p6, p7, p8, p9, p2)
            A = np.zeros_like(B)
            for k in range(8):
                A += ((~seq[k]) & seq[k + 1]).astype(np.uint8)
            if step == 0:
                c1 = ~(p2 & p4 & p6)
                c2 = ~(p4 & p6 & p8)
            else:
                c1 = ~(p2 & p4 & p8)
                c2 = ~(p2 & p6 & p8)
            rem = p & (B >= 2) & (B <= 6) & (A == 1) & c1 & c2
            if rem.any():
                p &= ~rem
                changed = True
        if not changed:
            break
    return p


# 湖岸红线剔除
# 河线 = 红芯 ∪ 棕色描边：线条细的地方只有描边没有红芯，
# 只取红色会得到断断续续的虚线。
blue_d = dilate(blue, 3)
# 每条河在源图里的深色描边是一个「闭合环」（沿左岸出去、沿右岸回来）。
# 走这条环得到一条闭合折线，再用 collapse_hairpins 对折成河心线。
# 不能直接用红水面：水面在变窄处被描边盖住，会断成一串虚线。
red_clean = brown & ~blue_d
log(f"河用深色描边环 {int(red_clean.sum())}（稍后对折成中线；红水面 {int(red.sum())}）")


# ---------------- 走线 ----------------
def trace_skeleton(sk):
    Hh, Ww = sk.shape
    idx = np.flatnonzero(sk.ravel()).tolist()
    ptset = set(idx)
    adj = {}
    for i in idx:
        y, x = divmod(i, Ww)
        nb = []
        for dy in (-1, 0, 1):
            yy = y + dy
            if yy < 0 or yy >= Hh:
                continue
            base = yy * Ww
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                xx = x + dx
                if not (0 <= xx < Ww):
                    continue
                # 斜向台阶会形成三角形：若两条正交边都存在，跳过这条对角边
                if dy != 0 and dx != 0:
                    if (base + x) in ptset and (yy * Ww + xx) in ptset:
                        continue
                j = base + xx
                if j in ptset:
                    nb.append(j)
        adj[i] = nb
    deg = {i: len(v) for i, v in adj.items()}
    nodes = {i for i in idx if deg[i] != 2}

    # 按「像素」记访问，每条链只走一次。
    # 早期版本按「边」记访问，结果同一段骨架会被走两遍，
    # 渲染成两条几乎重合的粗线，放大后河中央露出一条发丝浅缝。
    visited = set()
    paths = []

    def walk(start, first):
        path = [start, first]
        visited.add(first)
        prev, cur = start, first
        while cur not in nodes:
            nxt = [k for k in adj[cur] if k != prev]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            if cur in visited:
                # 回到走过的点：收尾成环
                path.append(cur)
                return path, True
            path.append(cur)
            visited.add(cur)
        return path, False

    # ① 从节点射出的链
    for n in nodes:
        for m in adj[n]:
            if m in visited:
                continue
            visited.add(n)
            p, closed = walk(n, m)
            paths.append((p, closed))

    # ② 剩下的纯环 / 孤立链
    for i in idx:
        if i in visited:
            continue
        if not adj[i]:
            visited.add(i)
            continue
        visited.add(i)
        head, closed_h = walk(i, adj[i][0])
        if closed_h:
            paths.append((head, True))
            continue
        # 反向再走一段
        rest = [k for k in adj[i] if k not in visited]
        tail = []
        if rest:
            p2, _ = walk(i, rest[0])
            tail = p2[1:]
        paths.append((list(reversed(tail)) + head, False))

    out = []
    covered = 0
    for path, closed in paths:
        xy = [(int(p % Ww), int(p // Ww)) for p in path]
        covered += len(path)
        # 相邻像素必然是 8 邻接。一旦出现跨越，说明这条折线在拼接时接错了地方
        # （会把两段相距很远的河连成一条直线），在这里断开。
        seg = [xy[0]] if xy else []
        for k in range(1, len(xy)):
            if max(abs(xy[k][0] - xy[k - 1][0]), abs(xy[k][1] - xy[k - 1][1])) > 1:
                if len(seg) >= 2:
                    out.append((seg, False))
                seg = [xy[k]]
            else:
                seg.append(xy[k])
        if len(seg) >= 2:
            out.append((seg, closed))
    log(f"  走线 {len(out)} 段，覆盖 {covered}/{len(idx)} 像素（{covered / max(1, len(idx)) * 100:.0f}%）")
    return out


def rdp(points, eps):
    if len(points) < 3:
        return list(points)
    keep = np.zeros(len(points), dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    pts = np.asarray(points, dtype=np.float64)
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        seg = pts[b] - pts[a]
        ln = math.hypot(seg[0], seg[1])
        sub = pts[a + 1:b]
        if ln < 1e-9:
            d = np.hypot(sub[:, 0] - pts[a][0], sub[:, 1] - pts[a][1])
        else:
            d = np.abs(seg[0] * (sub[:, 1] - pts[a][1]) - seg[1] * (sub[:, 0] - pts[a][0])) / ln
        k = int(np.argmax(d))
        if d[k] > eps:
            keep[a + 1 + k] = True
            stack.append((a, a + 1 + k))
            stack.append((a + 1 + k, b))
    return [points[i] for i in range(len(points)) if keep[i]]


def prune(paths, min_len):
    out = []
    for xy, closed in paths:
        if len(xy) < 2:
            continue
        L = sum(math.hypot(xy[i + 1][0] - xy[i][0], xy[i + 1][1] - xy[i][1])
                for i in range(len(xy) - 1))
        if closed or L >= min_len:
            out.append((xy, closed, L))
    return out


def collapse_hairpins(paths, max_width=26.0, min_pts=24):
    """把「一去一回」的闭合环对折成一条中线。

    源图里每条河的深色描边是一个闭合环：沿左岸出去、沿右岸回来。
    直接按折线描粗，会得到两条岸线中间夹一道缝（玩家看到的"河中央劈缝"）。
    这种环有个好性质：第 i 个点和第 n-1-i 个点正是两岸的对应点，
    取中点就还原出河心线。

    判定：**按几何闭合**（首尾点相距很近）而不是看走线器的 closed 标记——
    走线器从节点出发时会把这个环切成一条首尾几乎重合的"开口"折线。
    再加两条：点数够、对折距离 <= max_width。
    """
    out = []
    folded = 0
    for xy, closed, L in paths:
        n = len(xy)
        geo_closed = n > 3 and math.hypot(xy[0][0] - xy[-1][0], xy[0][1] - xy[-1][1]) <= max_width
        if not (closed or geo_closed) or n < min_pts:
            out.append((xy, closed, L))
            continue
        ds = []
        for i in range(1, n // 2):
            j = n - 1 - i
            ds.append(math.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]))
        if not ds:
            out.append((xy, closed, L))
            continue
        ds_sorted = sorted(ds)
        med = ds_sorted[len(ds_sorted) // 2]
        ok = med <= 16.0 and ds_sorted[int(len(ds_sorted) * 0.9)] <= 28.0
        mid = None
        if ok:
            mid = [xy[0]]
            for i in range(1, n // 2):
                j = n - 1 - i
                mid.append(((xy[i][0] + xy[j][0]) / 2.0, (xy[i][1] + xy[j][1]) / 2.0))
            # 对折后必须仍是平滑曲线：出现大跳变说明这两半不是同一条河的两岸
            for i in range(len(mid) - 1):
                if math.hypot(mid[i + 1][0] - mid[i][0], mid[i + 1][1] - mid[i][1]) > 30.0:
                    ok = False
                    break
        if ok and mid:
            L2 = sum(math.hypot(mid[i + 1][0] - mid[i][0], mid[i + 1][1] - mid[i][1])
                     for i in range(len(mid) - 1))
            out.append((mid, False, L2))
            folded += 1
        else:
            out.append((xy, closed, L))
    log(f"闭合环对折：{folded} 条（一去一回的描边环 → 单条中线）")
    return out


def simplify(paths, eps):
    out = []
    for xy, closed, _ in paths:
        simp = rdp(xy, eps)
        if closed and simp[0] != simp[-1]:
            simp = simp + [simp[0]]
        if len(simp) >= 2:
            out.append(simp)
    return out


def dedup_parallel(polys, radius=9.0, cover=0.85, len_tol=0.35, end_tol=14.0):
    """去掉「同一条线被走了两遍」的重复折线。

    实测：走线器偶尔会把同一段骨架走两次，得到两条长度完全相同、
    平均距离 0.0–0.3px 的折线。两条几乎重合的描边叠在一起，
    浏览器抗锯齿边缘会露出一条发丝般的浅缝——玩家看到的就是"河里劈缝"。

    判据（三条同时成立才算重复）：
      1. 两端各自靠近（同向或反向都算）；
      2. 长度相当（|ΔL|/max < len_tol）；
      3. 抽样点到对方的最近距离，cover 以上 <= radius，且平均距离 < 1.2px
         （平均距离大于 1.2 的是真正的双岸线，另案处理）。
    """

    def length(p):
        return sum(math.hypot(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1])
                   for i in range(len(p) - 1))

    def near_stats(p, q, step):
        qs = q[::max(1, len(q) // 200)] or q
        ok = 0
        total = 0.0
        n = 0
        for x, y in p[::step]:
            d = min((x - qx) ** 2 + (y - qy) ** 2 for qx, qy in qs) ** 0.5
            total += d
            n += 1
            if d <= radius:
                ok += 1
        return ok / max(1, n), total / max(1, n)

    def close(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= end_tol

    lens = [length(p) for p in polys]
    order = sorted(range(len(polys)), key=lambda i: -lens[i])
    kept = []
    dropped = 0
    merged_pts = 0
    for i in order:
        p = polys[i]
        step = max(1, len(p) // 40)
        dup = False
        for j in kept:
            q = polys[j]
            if abs(lens[i] - lens[j]) / max(1.0, max(lens[i], lens[j])) > len_tol:
                continue
            if not ((close(p[0], q[0]) and close(p[-1], q[-1]))
                    or (close(p[0], q[-1]) and close(p[-1], q[0]))):
                continue
            cov, mean = near_stats(p, q, step)
            if cov >= cover and mean < 1.2:
                dup = True
                merged_pts += len(p)
                break
        if dup:
            dropped += 1
        else:
            kept.append(i)
    log(f"重复走线去重：原有 {len(polys)} 段，去掉重复 {dropped} 段（{merged_pts} 点），保留 {len(kept)} 段")
    return [polys[i] for i in kept]


print("thin + trace ...")
riv_sk = thin(red_clean)
log(f"骨架像素 河 {int(riv_sk.sum())}")
riv_paths = prune(trace_skeleton(riv_sk), 6)
del riv_sk
bor_sk = thin(brown)
log(f"骨架像素 边界 {int(bor_sk.sum())}")
bor_paths = prune(trace_skeleton(bor_sk), 8)
del bor_sk
coa_sk = thin(coast)
log(f"骨架像素 海岸 {int(coa_sk.sum())}")
coa_paths = prune(trace_skeleton(coa_sk), 8)
del coa_sk

log(f"折线数 河 {len(riv_paths)}  边界 {len(bor_paths)}  海岸 {len(coa_paths)}")

# riv_paths = collapse_hairpins(riv_paths)
rivers = simplify(riv_paths, 1.8)
borders = simplify(bor_paths, 2.2)
coast_lines = simplify(coa_paths, 1.5)
log(f"简化后 河 {len(rivers)} 段/{sum(len(p) for p in rivers)} 点")
log(f"       边界 {len(borders)} 段/{sum(len(p) for p in borders)} 点")
log(f"       海岸 {len(coast_lines)} 段/{sum(len(p) for p in coast_lines)} 点")
rivers = dedup_parallel(rivers)
log(f"去重后 河 {len(rivers)} 段/{sum(len(p) for p in rivers)} 点")


# ---------------- 连通域与轮廓 ----------------
def label_runs(mask):
    Hh, Ww = mask.shape
    runs = []
    span = []
    for y in range(Hh):
        row = mask[y]
        if not row.any():
            span.append((len(runs), len(runs)))
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        st = np.flatnonzero(d == 1)
        en = np.flatnonzero(d == -1) - 1
        b = len(runs)
        span.append((b, b + len(st)))
        runs.extend((y, int(x0), int(x1)) for x0, x1 in zip(st, en))
    par = list(range(len(runs)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    for y in range(1, Hh):
        a0, a1 = span[y - 1]
        b0, b1 = span[y]
        i, j = a0, b0
        while i < a1 and j < b1:
            _, ax0, ax1 = runs[i]
            _, bx0, bx1 = runs[j]
            if ax0 - 1 <= bx1 and bx0 - 1 <= ax1:
                ra, rb = find(i), find(j)
                if ra != rb:
                    par[rb] = ra
            if ax1 < bx1:
                i += 1
            else:
                j += 1
    return runs, find


def comp_masks(mask, min_area):
    runs, find = label_runs(mask)
    groups = {}
    for k, (y, x0, x1) in enumerate(runs):
        groups.setdefault(find(k), []).append((y, x0, x1))
    out = []
    for rs in groups.values():
        area = sum(x1 - x0 + 1 for _, x0, x1 in rs)
        if area < min_area:
            continue
        y0 = min(t[0] for t in rs)
        y1 = max(t[0] for t in rs)
        x0 = min(t[1] for t in rs)
        x1 = max(t[2] for t in rs)
        m = np.zeros((y1 - y0 + 3, x1 - x0 + 3), dtype=bool)
        for y, a, b in rs:
            m[y - y0 + 1, a - x0 + 1:b - x0 + 2] = True
        out.append((m, x0 - 1, y0 - 1, area))
    out.sort(key=lambda t: -t[3])
    return out


def trace_contour(m):
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        return []
    start = (int(ys[0]), int(xs[0]))
    dirs = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    Hh, Ww = m.shape

    def inside(y, x):
        return 0 <= y < Hh and 0 <= x < Ww and m[y, x]

    contour = [start]
    cur = start
    backtrack = (start[0], start[1] - 1)
    for _ in range(int(m.sum()) * 8 + 20):
        di = dirs.index((backtrack[0] - cur[0], backtrack[1] - cur[1]))
        found = None
        for k in range(1, 9):
            d = dirs[(di + k) % 8]
            ny, nx = cur[0] + d[0], cur[1] + d[1]
            if inside(ny, nx):
                nb = dirs[(di + k - 1) % 8]
                found = ((ny, nx), (cur[0] + nb[0], cur[1] + nb[1]))
                break
        if found is None:
            break
        cur, backtrack = found
        contour.append(cur)
        if cur == start and len(contour) > 3:
            break
    return [(x, y) for y, x in contour]


print("lakes ...")
lakes = []
for m, ox, oy, area in comp_masks(blue, 60):
    c = trace_contour(m)
    if len(c) < 8:
        continue
    pts = [(x + ox, y + oy) for x, y in c]
    pts = rdp(pts, 1.6)
    if len(pts) >= 4:
        lakes.append(pts)
log(f"湖泊 {len(lakes)} 个")

print("sea ...")
sea_small = water[: (H // S_SEA) * S_SEA, : (W // S_SEA) * S_SEA]
sea_small = sea_small.reshape(H // S_SEA, S_SEA, W // S_SEA, S_SEA).max(axis=(1, 3))
sea_comps = comp_masks(sea_small, 2000)
sea_polys = []
if sea_comps:
    m, ox, oy, area = sea_comps[0]
    c = trace_contour(m)
    pts = [((x + ox) * S_SEA, (y + oy) * S_SEA) for x, y in c]
    sea_polys.append(rdp(pts, 2.2))
    log(f"海多边形 {len(sea_polys[0])} 点  面积 {area * S_SEA * S_SEA}")

islands = [p for p in coast_lines if len(p) > 8 and p[0] == p[-1]]
log(f"闭合环/岛 {len(islands)}")


# ---------------- 输出 ----------------
OUTDIR.mkdir(parents=True, exist_ok=True)


def _js(o):
    return int(o) if float(o).is_integer() else float(o)


def dump(name, obj):
    p = OUTDIR / name
    p.write_text(json.dumps(obj, separators=(",", ":"), default=_js), encoding="utf-8")
    log(f"{name}: {p.stat().st_size / 1024:.0f} KB")


dump("rivers.json", rivers)
dump("lakes.json", lakes)
dump("borders.json", borders)
dump("coast.json", {"lines": coast_lines, "sea": sea_polys, "islands": islands})
REPORT.write_text("\n".join(lines), encoding="utf-8")
print("done")
