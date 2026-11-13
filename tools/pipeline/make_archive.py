"""给当前河网做一份存档快照。

产物 data/map/rivers/_archive/河网定稿-YYYY-MM-DD/
  river_segments.json   权威数据
  rivers_meta.json      派生：河段类型/等级/长度
  lakes_drawn.json      派生：湖泽多边形
  coast_drawn.json      派生：海岸线
  sea_from_coast.json   派生：海面多边形
  MANIFEST.txt          清单 + 校验和 + 恢复方法

用法  python tools/make_archive.py [标签]
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "map" / "rivers" / "river_segments.json"
VEC = ROOT / "data" / "map" / "vector"
FILES = ["rivers_meta.json", "lakes_drawn.json", "coast_drawn.json", "sea_from_coast.json"]


def sha(p):
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()[:16]


def seglen(pts):
    import math
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "河网定稿"
    d = json.loads(SRC.read_text(encoding="utf-8-sig"))
    meta = json.loads((VEC / "rivers_meta.json").read_text(encoding="utf-8"))

    day = time.strftime("%Y-%m-%d")
    dest = SRC.parent / "_archive" / f"{tag}-{day}"
    dest.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SRC, dest / "river_segments.json")
    for f in FILES:
        p = VEC / f
        if p.exists():
            shutil.copy2(p, dest / f)

    segs = d["segments"]
    lakes = d.get("lakes") or []
    coasts = d.get("coasts") or []
    labels = collections.Counter(s["label"] for s in meta["sections"])

    L = []
    L.append(f"河网存档 · {tag} · {day}")
    L.append("=" * 52)
    L.append("")
    L.append(f"河段 {len(segs)}　河流 {len({s['river'] for s in segs})}　"
             f"湖泽 {len(lakes)}　海岸线 {len(coasts)}")
    L.append(f"河网总长 {sum(seglen(s['pts']) for s in segs):,.0f} px")
    L.append("")
    L.append("类型分布")
    for k, v in labels.most_common():
        L.append(f"  {k:<16} {v}")
    L.append("")
    L.append("命名")
    L.append(f"  已命名河段 {sum(1 for s in segs if s.get('name'))} / {len(segs)}")
    L.append(f"  已命名湖泽 {sum(1 for l in lakes if l.get('name'))} / {len(lakes)}")
    L.append("")
    L.append("文件（sha256 前 16 位）")
    for f in sorted(dest.iterdir()):
        if f.name == "MANIFEST.txt":
            continue
        L.append(f"  {f.name:<24} {f.stat().st_size:>9,} B  {sha(f)}")
    L.append("")
    L.append("恢复")
    L.append("  把 river_segments.json 拷回 data/map/rivers/，覆盖当前文件，")
    L.append("  再双击仓库根目录的 重建地图.cmd 重新生成派生层与地图。")
    L.append("")
    L.append("管线")
    L.append("  sync_river_editor.py → rivers_from_editor.py →")
    L.append("  build_sea_from_coast.py → make_vector_map.py")

    (dest / "MANIFEST.txt").write_text("\n".join(L), encoding="utf-8")
    print("存档 →", dest)
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
