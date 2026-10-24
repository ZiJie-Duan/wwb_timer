"""从 U8g2 库源码中取出固件用到的 6 个字体，生成 web/js/fonts.js（base64）。

    python web/tools/gen_fonts.py        # 需要先在 firmware/ 里 pio run 过，U8g2 库才会被下载

字体编号与 firmware/src/main.cpp 的 FONTS[] 一致。
"""
import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "firmware/.pio/libdeps/c3/U8g2/src/clib/u8g2_fonts.c"
OUT = ROOT / "web/js/fonts.js"
FONTS = ["6x10_tf", "9x15_tf", "logisoso16_tr", "logisoso24_tn", "logisoso32_tn", "wqy12_t_gb2312b"]
ESC = {"n": 10, "t": 9, "r": 13, "\\": 92, '"': 34, "'": 39, "?": 63, "a": 7, "b": 8, "f": 12, "v": 11}


def c_string_bytes(lit: str) -> bytes:
    out, i = bytearray(), 0
    while i < len(lit):
        ch = lit[i]
        if ch != "\\":
            out.append(ord(ch))
            i += 1
            continue
        m = re.match(r"[0-7]{1,3}", lit[i + 1:])
        if m:
            out.append(int(m.group(), 8))
            i += 1 + len(m.group())
        else:
            out.append(ESC[lit[i + 1]])
            i += 2
    return bytes(out)


def extract(src: str, name: str) -> bytes:
    m = re.search(r"u8g2_font_%s\[(\d+)\][^=]*=\s*((?:\"(?:[^\"\\]|\\.)*\"\s*)+);" % name, src)
    if not m:
        sys.exit(f"找不到字体 {name}")
    data = b"".join(c_string_bytes(s) for s in re.findall(r"\"((?:[^\"\\]|\\.)*)\"", m.group(2)))
    assert len(data) == int(m.group(1)) - 1, (name, len(data), m.group(1))
    return data


def main():
    src = SRC.read_text(encoding="latin-1")
    lines = ["// 由 web/tools/gen_fonts.py 从 U8g2 源码生成，勿手改。顺序与固件 FONTS[] 一致",
             "window.WWB = window.WWB || {};", "WWB.FONT_DATA = ["]
    for name in FONTS:
        data = extract(src, name)
        lines.append(f'  ["{name}", "{base64.b64encode(data).decode()}"],')
        print(f"{name}: {len(data)} B")
    lines.append("];")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"已写入 {OUT}")


if __name__ == "__main__":
    main()
