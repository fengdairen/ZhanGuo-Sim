# -*- coding: utf-8 -*-
"""给河网折线算"上游汇流长度"，据此定线宽（主干粗、支流细）。

难点：矢量化时折线在交点处会被切开，而同一交点的像素可能落在相邻几格，
直接按坐标相等建图会退化成几千个孤立片段。所以先把端点按距离聚类。

步骤：
  1. 端点吸附到 4px 网格，再对网格键做距离<=8px 的并查集聚类；
  2. 按聚类后的节点建图，边权=折线长度；
  3. 从"河口"（贴近海岸线的端点）BFS 求图距离，据此定上下游方向；
  4. 按距离降序累加上游长度 acc[v] = Σ(acc[u]+len)；
  5. 线宽 = 1.3 + 2.2*log10(1+acc/250)，夹在 [1.3, 12]。

输入 data/map/vector/rivers.json + coast.json -> 输出 rivers_w.json:
  [[width, x1,y1,x2,y2, ...], ...]
"""
import json
import math
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VEC = ROOT / "data" / "map" / "vector"
GRID = 4
LINK = 2          # 网格步数（LINK*GRID=8px 内视为同一交点）

rivers = json.loads((VEC / "rivers.json").read_text(encoding="utf-8"))
coast = json.loads((VEC / "coast.json").read_text(encoding="utf-8"))


def snap(p):
    return (round(p[0] / GRID), round(p[1] / GRID))


# 海岸栅格，用于找河口
coast_pts = []
for line in coast["lines"]:
    coast_pts.extend(line)
CS = 60
coast_cells = set((int(x // CS), int(y // CS)) for x, y in coast_pts)


def near_coast(x, y, rad=2):
    cx, cy = int(x // CS), int(y // CS)
    for dx in range(-rad, rad + 1):
        for dy in range(-rad, rad + 1):
            if (cx + dx, cy + dy) in coast_cells:
                return True
    return False


# 1. 端点聚类
raw = []
for pts in rivers:
    if len(pts) < 2:
        continue
    raw.append((snap(pts[0]), snap(pts[-1]), pts))

keys = set()
for a, b, _ in raw:
    keys.add(a)
    keys.add(b)
parent = {k: k for k in keys}


def find(k):
    while parent[k] != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k


def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[rb] = ra


for k in keys:
    for dx in range(-LINK, LINK + 1):
        for dy in range(-LINK, LINK + 1):
            other = (k[0] + dx, k[1] + dy)
            if other in parent:
                union(k, other)

print(f"端点 {len(keys)} -> 聚类 {len({find(k) for k in keys})}")

# 2. 建图
edges = []
loops = []          # 起终点重合的环：不进图，但也不能丢
vpos = {}
deg = defaultdict(int)
for a, b, pts in raw:
    a, b = find(a), find(b)
    L = sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1))
    if a == b:
        if L >= 20:            # 太短的多是端点吸附进来的碎屑
            loops.append((L, pts))
        continue
    vpos.setdefault(a, (*pts[0],))
    vpos.setdefault(b, (*pts[-1],))
    edges.append((a, b, L, pts))
    deg[a] += 1
    deg[b] += 1

adj = defaultdict(list)
for ei, (a, b, L, _) in enumerate(edges):
    adj[a].append((b, ei))
    adj[b].append((a, ei))
print(f"边 {len(edges)}  点 {len(vpos)}")

# 3. 河口与图距离
mouths = [v for v in vpos if near_coast(vpos[v][0], vpos[v][1])]
if not mouths:
    mouths = [v for v in vpos if deg[v] == 1]
print(f"河口 {len(mouths)}")

dist = {}
q = deque()
for m in mouths:
    dist[m] = 0.0
    q.append(m)
while q:
    v = q.popleft()
    for w, ei in adj[v]:
        nd = dist[v] + edges[ei][2]
        if w not in dist or nd < dist[w] - 1e-6:
            dist[w] = nd
            q.append(w)
for v in vpos:
    dist.setdefault(v, 0.0)

# 4. 上游长度累加
order = sorted(dist.items(), key=lambda t: -t[1])
incoming = defaultdict(list)
for a, b, L, _ in edges:
    if dist[a] > dist[b]:
        incoming[b].append((a, L))
    elif dist[b] > dist[a]:
        incoming[a].append((b, L))
    else:
        incoming[max(a, b)].append((min(a, b), L))

acc = defaultdict(float)
for v, _ in order:
    s = 0.0
    for u, L in incoming[v]:
        s += acc.get(u, 0.0) + L
    acc[v] = s

# 5. 输出
out = []
for a, b, L, pts in edges:
    up = max(acc.get(a, 0.0), acc.get(b, 0.0))
    width = 1.3 + 3.2 * math.log10(1 + up / 120.0)
    width = max(1.3, min(12.0, width))
    out.append([round(width, 2)] + [round(c, 1) for xy in pts for c in xy])

# 环：不进图算汇流，按自身长度给个中等线宽，绝不能丢（丢了就是河道缺一段）
for L, pts in loops:
    width = max(1.3, min(9.0, 1.3 + 2.2 * math.log10(1 + L / 160.0)))
    out.append([round(width, 2)] + [round(c, 1) for xy in pts for c in xy])

(VEC / "rivers_w.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
ws = [e[0] for e in out]
print(f"线宽 {min(ws):.1f}–{max(ws):.1f}，段 {len(out)}（其中环 {len(loops)}），{(VEC / 'rivers_w.json').stat().st_size / 1024:.0f} KB")
