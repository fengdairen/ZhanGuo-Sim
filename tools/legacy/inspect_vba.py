# -*- coding: utf-8 -*-
"""看控件与 VBA 结构。"""
import zipfile, re
from pathlib import Path

SRC = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台\备份.xlsm")
L = []
def p(*a): L.append(" ".join(str(x) for x in a))

with zipfile.ZipFile(SRC) as z:
    names = z.namelist()

    p("=== CtrlProps ===")
    for n in sorted(names):
        if n.startswith("xl/ctrlProps/"):
            data = z.read(n).decode("utf-8", "ignore")
            vals = re.findall(r'<formControlPr[^>]*>', data)
            p(f"  {n}: {vals[:1]}")

    p("\n=== VML drawing 中的控件文本 ===")
    for n in sorted(names):
        if n.endswith(".vml"):
            data = z.read(n).decode("utf-8", "ignore")
            texts = re.findall(r"<v:textbox[^>]*>.*?</v:textbox>", data, re.S)
            p(f"  {n}: textboxes={len(texts)}")
            for t in texts[:6]:
                plain = re.sub(r"<[^>]+>", " ", t)
                plain = re.sub(r"\s+", " ", plain).strip()
                if plain:
                    p(f"      «{plain[:120]}»")

    p("\n=== VBA 模块名（从 bin 里找可读的模块/过程名） ===")
    bin_data = z.read("xl/vbaProject.bin")
    p("  vbaProject.bin size:", len(bin_data))
    # UTF-16LE 字符串
    u16 = re.findall(rb"(?:[\x20-\x7e]\x00){4,}", bin_data)
    seen = []
    for s in u16:
        try:
            t = s.decode("utf-16-le")
        except Exception:
            continue
        if t not in seen:
            seen.append(t)
    p("  可读 UTF-16 串（前 120 个）:")
    for t in seen[:120]:
        p("    ", repr(t))
    # ASCII 串
    asc = re.findall(rb"[\x20-\x7e]{5,}", bin_data)
    p("\n  可读 ASCII 串（前 80 个）:")
    for s in asc[:80]:
        p("    ", s.decode("ascii", "ignore"))

Path("tools/_vba_report.txt").write_text("\n".join(L), encoding="utf-8")
print("ok", len(L))
