"""r6 赛博道法：本批共用的小工具（不登记场景）。

tiny(g, x, y, s)   3×5 点阵小字（数字、大写字母、常用符号），读数、终端、G 代码用
bitsmoke(...)      “数字烟”：从 (x, y) 往上飘的像素方块与 0/1，越高越碎
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

from ..engine.anim import noise, rand
from ..engine.gfx import Gfx

_F = {
    "0": "### #.# #.# #.# ###", "1": ".#. ##. .#. .#. ###", "2": "### ..# ### #.. ###",
    "3": "### ..# ### ..# ###", "4": "#.# #.# ### ..# ..#", "5": "### #.. ### ..# ###",
    "6": "### #.. ### #.# ###", "7": "### ..# ..# .#. .#.", "8": "### #.# ### #.# ###",
    "9": "### #.# ### ..# ###",
    "A": ".#. #.# ### #.# #.#", "B": "##. #.# ##. #.# ##.", "C": ".## #.. #.. #.. .##",
    "D": "##. #.# #.# #.# ##.", "E": "### #.. ##. #.. ###", "F": "### #.. ##. #.. #..",
    "G": ".## #.. #.# #.# .##", "H": "#.# #.# ### #.# #.#", "I": "### .#. .#. .#. ###",
    "J": "..# ..# ..# #.# .#.", "K": "#.# #.# ##. #.# #.#", "L": "#.. #.. #.. #.. ###",
    "M": "#.# ### ### #.# #.#", "N": "##. #.# #.# #.# #.#", "O": ".#. #.# #.# #.# .#.",
    "P": "##. #.# ##. #.. #..", "Q": ".#. #.# #.# ##. .##", "R": "##. #.# ##. #.# #.#",
    "S": ".## #.. .#. ..# ##.", "T": "### .#. .#. .#. .#.", "U": "#.# #.# #.# #.# ###",
    "V": "#.# #.# #.# #.# .#.", "W": "#.# #.# ### ### #.#", "X": "#.# #.# .#. #.# #.#",
    "Y": "#.# #.# .#. .#. .#.", "Z": "### ..# .#. #.. ###",
    "%": "#.# ..# .#. #.. #.#", ".": "... ... ... ... .#.", ":": "... .#. ... .#. ...",
    "-": "... ... ### ... ...", "+": "... .#. ### .#. ...", "/": "..# ..# .#. #.. #..",
    "=": "... ### ... ### ...", "(": ".#. #.. #.. #.. .#.", ")": ".#. ..# ..# ..# .#.",
    "<": "..# .#. #.. .#. ..#", ">": "#.. .#. ..# .#. #..", "_": "... ... ... ... ###",
    "#": "#.# ### #.# ### #.#", "!": ".#. .#. .#. ... .#.", "?": "##. ..# .#. ... .#.",
    "[": "##. #.. #.. #.. ##.", "]": ".## ..# ..# ..# .##", ",": "... ... ... .#. #..",
    "*": "... #.# .#. #.# ...", "^": ".#. #.# ... ... ...", "'": ".#. .#. ... ... ...",
    "|": ".#. .#. .#. .#. .#.", "$": ".## ##. .#. .## ##.", "~": "... .## ##. ... ...",
    " ": "... ... ... ... ...",
}
_MASK: dict[str, Image.Image] = {}
for _k, _v in _F.items():
    _a = np.array([[c == "#" for c in row] for row in _v.split()], dtype=bool)
    _MASK[_k] = Image.fromarray(_a)
_MASK["{"] = _MASK["("]
_MASK["}"] = _MASK[")"]


def tiny_w(s: str) -> int:
    return max(0, len(s) * 4 - 1)


def tiny(g: Gfx, x: float, y: float, s: str, fill: int = 1, align: str = "left") -> int:
    """3×5 小字；y 为字顶。返回宽度"""
    w = tiny_w(s)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    x, y = int(round(x)), int(round(y))
    for i, ch in enumerate(s.upper()):
        m = _MASK.get(ch)
        if m is not None and ch != " ":
            g.img.paste(fill, (x + i * 4, y), m)
    return w


def bitsmoke(g: Gfx, x: float, y: float, height: float, t: float, seed: int = 0, n: int = 3, speed: float = 7.0,
             sway: float = 3.0, drift: float = 0.0, amount: float = 1.0):
    """数字烟：一缕量化成 2 像素台阶的“8 位烟”，往上越来越碎，顶上飘出几个 0/1。amount 0..1 控制高度/浓度"""
    if height <= 2 or amount <= 0:
        return
    hh = height * amount
    for i in range(0, int(hh), 2):
        k = i / max(height, 1)
        ph = (i + t * speed) * 0.12
        dx = (noise(ph, seed) - 0.5) * 2 * sway * (0.3 + k) + math.sin(ph * 1.7 + seed) * sway * 0.4 * k
        xx = int(round((x + dx + drift * k * k) / 2) * 2)
        yy = int(y - i)
        if k > 0.45 and rand(int(i + t * speed), seed) < (k - 0.45) * 2.0:
            continue
        if k < 0.3:
            g.d.line((xx, yy - 1, xx, yy), fill=1)
        else:
            g.d.rectangle((xx, yy - 1, xx + 1, yy), fill=1)
    for j in range(n):  # 飘起来的 0/1
        ph = (t * speed / height * 0.8 + j / n + rand(j, seed) * 0.3) % 1.0
        if ph < 0.35 or ph * height > hh + 4:
            continue
        cyc = int(t * speed / height * 0.8 + j / n + rand(j, seed) * 0.3)
        if ph > 0.8 and rand(int(t * 10) + j, seed) < (ph - 0.8) * 4:
            continue
        k = ph
        side = 1 if (cyc + j) % 2 else -1
        xx = x + drift * k * k + side * (3 + 4 * k) + (noise(k * 4, seed + j) - 0.5) * 4
        tiny(g, int(xx) - 1, int(y - k * height) - 2, "1" if rand(cyc * 7 + j, seed) > 0.5 else "0")


def glow_rays(g: Gfx, cx: float, cy: float, r0: float, r1: float, n: int = 12, phase: float = 0.0, sy: float = 1.0):
    """放射光芒"""
    for i in range(n):
        a = i / n * 2 * math.pi + phase
        g.d.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0 * sy, cx + math.cos(a) * r1,
                  cy + math.sin(a) * r1 * sy), fill=1)


def mx_bar(g: Gfx, col: int, h: int, bottom: int = 6):
    for r in range(bottom, bottom - h, -1):
        g.mx_set(col, r)


_TXT: dict[tuple, tuple] = {}


def ctext(g: Gfx, x: float, y: float, s: str, size: int = 12, fill: int = 1, align: str = "left") -> int:
    """带缓存的 g.text（同一串字只栅格化一次，之后直接贴图；比 g.text 快很多）"""
    from PIL import ImageDraw
    from ..engine.gfx import _FONT_FILES, font
    g.texts.append((s, size))
    key = (s, size)
    hit = _TXT.get(key)
    if hit is None:
        f = font(size)
        w = max(1, int(f.getlength(s)))
        hh = size + 4
        m = Image.new("1", (w, hh))
        dr = ImageDraw.Draw(m)
        dr.fontmode = "1"
        dr.text((0, -_FONT_FILES[size][1]), s, font=f, fill=1)
        hit = (m, w)
        if len(_TXT) > 600:
            _TXT.clear()
        _TXT[key] = hit
    m, w = hit
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    g.img.paste(fill, (int(round(x)), int(round(y))), m)
    return w


def cvtext(g: Gfx, x: float, y: float, s: str, size: int = 12, fill: int = 1, gap: int = 1) -> int:
    from ..engine.gfx import _FONT_FILES, text_width
    step = _FONT_FILES[size][2] + gap
    for i, ch in enumerate(s):
        cw = text_width(ch, size)
        ctext(g, x + (size - cw) / 2, y + i * step, ch, size, fill)
    return len(s) * step - gap


def num(n: int) -> str:
    """轮数：一百以内用中文数字，再大用阿拉伯数字（免得竖排/面板放不下）"""
    from ..engine.cn import cn_num
    return cn_num(n) if n < 100 else str(n)


def vlabel(n: int, unit: str) -> str:
    """竖排的轮数标签：“第十二炷”；过百改成“432炷”（竖排放得下）"""
    return f"第{num(n)}{unit}" if n < 100 else f"{n}{unit}"
