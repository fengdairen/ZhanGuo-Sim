# -*- coding: utf-8 -*-
"""把 tools/ 下每个脚本的首行说明汇总成表，供 31-工具链.md 使用。"""
import re
from pathlib import Path

ROOT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台")
rows = []
for p in sorted((ROOT / "tools").iterdir()):
    if not p.is_file() or p.suffix not in (".py", ".ps1", ".js"):
        continue
    if p.name.startswith("_"):
        continue
    head = ""
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'"""(.*?)"""', text, re.S)
        if m:
            head = m.group(1).strip().splitlines()[0]
        else:
            for line in text.splitlines():
                s = line.strip()
                if s.startswith("#") and not s.startswith("#!"):
                    head = s.lstrip("# ").strip()
                    break
    except Exception:
        pass
    rows.append(f"{p.name}\t{head}")

(ROOT / "tools" / "_toolslist.txt").write_text("\n".join(rows), encoding="utf-8")
print(f"{len(rows)} 个脚本")
