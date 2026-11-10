# -*- coding: utf-8 -*-
"""PSD/PSB 图层记录解析（版本感知：PSB 用 8 字节长度）。
只读图层信息段，不读像素。
"""
import json
import struct
from pathlib import Path

SRC = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台\ditu.psd")
OUT = Path(r"D:\Files\HUST_OFFLINE\ds工作站\战国演义数据台\tools\_psd_layers.json")

b = SRC.read_bytes()


def u16(p): return struct.unpack_from(">H", b, p)[0]
def i16(p): return struct.unpack_from(">h", b, p)[0]
def u32(p): return struct.unpack_from(">I", b, p)[0]
def i32(p): return struct.unpack_from(">i", b, p)[0]
def u64(p): return struct.unpack_from(">Q", b, p)[0]


assert b[:4] == b"8BPS"
version = u16(4)                       # 1 = PSD, 2 = PSB
channels, height, width = u16(12), u32(14), u32(18)
depth, mode = u16(22), u16(24)
pos = 26

cm_len = u32(pos); pos += 4 + cm_len
ir_len = u32(pos); pos += 4 + ir_len

if version == 2:
    lm_start = pos
    lm_len = u64(pos); pos += 8
    layer_info_len = u64(pos); pos += 8
    layer_count = abs(i32(pos)); pos += 4
else:
    lm_start = pos
    lm_len = u32(pos); pos += 4
    layer_info_len = u32(pos); pos += 4
    layer_count = abs(i16(pos)); pos += 2

layers, errors = [], []

for idx in range(layer_count):
    try:
        top, left, bottom, right = i32(pos), i32(pos + 4), i32(pos + 8), i32(pos + 12)
        pos += 16
        nch = u16(pos); pos += 2
        for _ in range(nch):
            pos += 2                       # channel id
            pos += 8 if version == 2 else 4  # channel data length
        pos += 8                           # blend mode signature '8BIM' + key 'norm'
        opacity = b[pos]; pos += 1
        clipping = b[pos]; pos += 1
        flags = b[pos]; pos += 1
        pos += 1
        extra_len = u32(pos); pos += 4
        extra_start = pos

        mask_len = u32(pos); pos += 4 + mask_len
        blend_len = u32(pos); pos += 4 + blend_len
        name_len = b[pos]; pos += 1
        raw_name = b[pos:pos + name_len]
        pos += name_len
        pos = (pos + 3) & ~3

        uni_name, section, blocks = None, None, []
        while pos + 12 <= extra_start + extra_len:
            sig = b[pos:pos + 4]
            if sig not in (b"8BIM", b"8B64"):
                break
            key = b[pos + 4:pos + 8]
            ln = u32(pos + 8)
            data = b[pos + 12:pos + 12 + ln]
            blocks.append(key.decode("latin-1"))
            if key == b"luni" and len(data) >= 4:
                n = struct.unpack_from(">I", data, 0)[0]
                uni_name = data[4:4 + n * 2].decode("utf-16-be", "ignore")
            if key == b"lsct" and len(data) >= 4:
                section = struct.unpack_from(">I", data, 0)[0]
            pos += 12 + ln
            if ln % 2:
                pos += 1

        name = uni_name or raw_name.decode("gbk", "ignore") or raw_name.decode("utf-8", "ignore")
        layers.append({
            "i": idx, "name": name,
            "bbox": [left, top, right, bottom],
            "w": right - left, "h": bottom - top,
            "visible": (flags & 2) == 0,
            "section": section,
            "blocks": blocks,
        })
        pos = extra_start + extra_len
    except Exception as e:
        errors.append({"i": idx, "err": repr(e)})
        break

OUT.write_text(json.dumps({
    "canvas": {"w": width, "h": height, "depth": depth, "mode": mode, "psd_version": version},
    "declared_layer_count": layer_count,
    "parsed": len(layers),
    "layers": layers,
    "errors": errors,
}, ensure_ascii=False, indent=1), encoding="utf-8")

print("version", version, "canvas", width, height, "declared", layer_count, "parsed", len(layers), "errors", len(errors))
for l in layers:
    print(f"  [{l['i']:4}] {l['name'][:40]:<40} {l['w']}x{l['h']:<6} sec={l['section']} vis={l['visible']}")
