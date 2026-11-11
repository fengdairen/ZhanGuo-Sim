# -*- coding: utf-8 -*-
"""校验：文档内所有相对链接是否可达；汇总每份文档的首行标题与体量。"""
import re
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
L = []
def p(*a): L.append(" ".join(str(x) for x in a))

md_files = sorted(ROOT.glob("*.md")) + sorted((ROOT / "docs").rglob("*.md"))
p("=== 文件清单 ===")
for f in md_files:
    rel = f.relative_to(ROOT)
    lines = f.read_text(encoding="utf-8").splitlines()
    title = next((x for x in lines if x.startswith("# ")), "(无标题)")
    p(f"  {str(rel):48} {f.stat().st_size/1024:6.1f}KB {len(lines):4}行  {title}")

p("\n=== 链接校验 ===")
bad = 0
total = 0
for f in md_files:
    text = f.read_text(encoding="utf-8")
    for m in re.finditer(r"\[([^\]]+)\]\(([^)\s]+)\)", text):
        target = m.group(2)
        if target.startswith(("http://", "https://", "#")):
            continue
        total += 1
        # 去掉锚点
        path_part = target.split("#")[0]
        if not path_part:
            continue
        resolved = (f.parent / path_part).resolve()
        if not resolved.exists():
            bad += 1
            p(f"  [BROKEN] {f.relative_to(ROOT)} -> {target}")
p(f"  相对链接共 {total} 条，断链 {bad} 条")

p("\n=== 旧文件名残留检查 ===")
for f in md_files:
    t = f.read_text(encoding="utf-8")
    if "00-README-索引" in t:
        p(f"  仍引用旧索引: {f.relative_to(ROOT)}")
p("  完成")

(ROOT / "tools" / "_doc_check.txt").write_text("\n".join(L), encoding="utf-8")
print("ok")

