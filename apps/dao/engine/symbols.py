"""易与道的符号：八卦、六十四卦、太极、八卦盘（OLED 与点阵两种画法）。

爻的表示：一卦 6 爻，列表从初爻（最下）到上爻（最上）。每爻用占筮的数：
6 = 老阴（变）、7 = 少阳、8 = 少阴、9 = 老阳（变）；也可以直接用 True/False（阳/阴）。
"""
from __future__ import annotations

import math
import random

import numpy as np

from .gfx import Gfx

# 八卦：名、自然象、符号、三爻（自下而上，1 = 阳）
TRIGRAMS = {
    "乾": ("天", "☰", (1, 1, 1)),
    "兑": ("泽", "☱", (1, 1, 0)),
    "离": ("火", "☲", (1, 0, 1)),
    "震": ("雷", "☳", (1, 0, 0)),
    "巽": ("风", "☴", (0, 1, 1)),
    "坎": ("水", "☵", (0, 1, 0)),
    "艮": ("山", "☶", (0, 0, 1)),
    "坤": ("地", "☷", (0, 0, 0)),
}
# 八卦盘：从正上方（南）起顺时针。传统图南在上
XIANTIAN = ["乾", "巽", "坎", "艮", "坤", "震", "离", "兑"]  # 先天八卦（伏羲）
HOUTIAN = ["离", "坤", "兑", "乾", "坎", "艮", "震", "巽"]   # 后天八卦（文王）

# 六十四卦（文王序）：(卦名, 上卦, 下卦)
HEXAGRAMS = [
    ("乾", "乾", "乾"), ("坤", "坤", "坤"), ("屯", "坎", "震"), ("蒙", "艮", "坎"), ("需", "坎", "乾"),
    ("讼", "乾", "坎"), ("师", "坤", "坎"), ("比", "坎", "坤"), ("小畜", "巽", "乾"), ("履", "乾", "兑"),
    ("泰", "坤", "乾"), ("否", "乾", "坤"), ("同人", "乾", "离"), ("大有", "离", "乾"), ("谦", "坤", "艮"),
    ("豫", "震", "坤"), ("随", "兑", "震"), ("蛊", "艮", "巽"), ("临", "坤", "兑"), ("观", "巽", "坤"),
    ("噬嗑", "离", "震"), ("贲", "艮", "离"), ("剥", "艮", "坤"), ("复", "坤", "震"), ("无妄", "乾", "震"),
    ("大畜", "艮", "乾"), ("颐", "艮", "震"), ("大过", "兑", "巽"), ("坎", "坎", "坎"), ("离", "离", "离"),
    ("咸", "兑", "艮"), ("恒", "震", "巽"), ("遁", "乾", "艮"), ("大壮", "震", "乾"), ("晋", "离", "坤"),
    ("明夷", "坤", "离"), ("家人", "巽", "离"), ("睽", "离", "兑"), ("蹇", "坎", "艮"), ("解", "震", "坎"),
    ("损", "艮", "兑"), ("益", "巽", "震"), ("夬", "兑", "乾"), ("姤", "乾", "巽"), ("萃", "兑", "坤"),
    ("升", "坤", "巽"), ("困", "兑", "坎"), ("井", "坎", "巽"), ("革", "兑", "离"), ("鼎", "离", "巽"),
    ("震", "震", "震"), ("艮", "艮", "艮"), ("渐", "巽", "艮"), ("归妹", "震", "兑"), ("丰", "震", "离"),
    ("旅", "离", "艮"), ("巽", "巽", "巽"), ("兑", "兑", "兑"), ("涣", "巽", "坎"), ("节", "坎", "兑"),
    ("中孚", "巽", "兑"), ("小过", "震", "艮"), ("既济", "坎", "离"), ("未济", "离", "坎"),
]
_BY_BITS = {TRIGRAMS[lo][2] + TRIGRAMS[up][2]: i + 1 for i, (_, up, lo) in enumerate(HEXAGRAMS)}


def yang(v) -> bool:
    return v in (7, 9) if isinstance(v, int) and not isinstance(v, bool) and v > 1 else bool(v)


def changing(v) -> bool:
    return v in (6, 9)


def changed(lines) -> list[int]:
    """变卦：老阴变阳、老阳变阴"""
    return [7 if v == 6 else 8 if v == 9 else v for v in lines]


def cast_coins(rng: random.Random) -> list[int]:
    """三钱法（火珠林）：每爻掷三枚铜钱，背面记 3、字面记 2，和为 6/7/8/9（三背老阳、三字老阴）"""
    return [sum(rng.choice((2, 3)) for _ in range(3)) for _ in range(6)]


def hexagram(lines) -> tuple[int, str, str, str]:
    """→ (文王序 1-64, 卦名, 上卦名, 下卦名)"""
    bits = tuple(1 if yang(v) else 0 for v in lines)
    n = _BY_BITS[bits]
    name, up, lo = HEXAGRAMS[n - 1]
    return n, name, up, lo


def full_name(lines) -> str:
    """如“水雷屯”“乾为天”"""
    n, name, up, lo = hexagram(lines)
    if up == lo:
        return f"{name}为{TRIGRAMS[up][0]}"
    return f"{TRIGRAMS[up][0]}{TRIGRAMS[lo][0]}{name}"


# ---------------------------------------------------------------- OLED

def draw_line(g: Gfx, x: int, y: int, w: int, h: int, is_yang: bool, gap: int | None = None, fill: int = 1):
    """一爻：阳爻实线，阴爻中间断开"""
    if is_yang:
        if w > 0 and h > 0:
            g.d.rectangle((x, y, x + w - 1, y + h - 1), fill=fill)
    else:
        gap = gap if gap is not None else max(2, w // 4)
        half = (w - gap) // 2
        if half <= 0 or h <= 0:
            return
        g.d.rectangle((x, y, x + half - 1, y + h - 1), fill=fill)
        g.d.rectangle((x + w - half, y, x + w - 1, y + h - 1), fill=fill)


def draw_hexagram(g: Gfx, x: int, y: int, lines, w: int = 24, h: int = 2, step: int = 4, count: int = 6,
                  mark: bool = False):
    """自下而上画 count 爻（count<6 时只画前几爻，起卦动画用）；(x, y) 为上爻左上角。
    mark：变爻右侧点一个点"""
    for i in range(min(count, len(lines))):
        yy = y + (5 - i) * step
        draw_line(g, x, yy, w, h, yang(lines[i]))
        if mark and changing(lines[i]):
            g.d.rectangle((x + w + 2, yy, x + w + 2 + h - 1, yy + h - 1), fill=1)


def draw_trigram(g: Gfx, x: int, y: int, name: str, w: int = 12, h: int = 2, step: int = 4):
    bits = TRIGRAMS[name][2]
    for i in range(3):
        draw_line(g, x, y + (2 - i) * step, w, h, bool(bits[i]))


def _taiji_mask(n: int, r: float, cx: float, cy: float, angle: float) -> tuple[np.ndarray, np.ndarray]:
    """n×n 网格上的太极：返回 (阳, 圆内)"""
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = xs - cx, ys - cy
    c, s = math.cos(-angle), math.sin(-angle)
    u, v = dx * c - dy * s, dx * s + dy * c
    inside = dx * dx + dy * dy <= r * r
    up = u * u + (v + r / 2) ** 2 <= (r / 2) ** 2
    lo = u * u + (v - r / 2) ** 2 <= (r / 2) ** 2
    white = (u > 0) & ~lo | up
    dot = r / 6.5
    white &= ~(u * u + (v + r / 2) ** 2 <= dot * dot)
    white |= u * u + (v - r / 2) ** 2 <= dot * dot
    return white & inside, inside


_TAIJI_CACHE: dict = {}


def _taiji_imgs(r: float, angle: float):
    """(阳鱼遮罩, 阴鱼遮罩, 边长)，按角度量化缓存（每圈 96 档）"""
    from PIL import Image
    q = int(round(angle / (2 * math.pi) * 96)) % 96
    key = (round(r * 2) / 2, q)
    hit = _TAIJI_CACHE.get(key)
    if hit is None:
        n = int(2 * key[0] + 3)
        white, inside = _taiji_mask(n, key[0], n / 2, n / 2, q / 96 * 2 * math.pi)
        hit = (Image.fromarray(white), Image.fromarray(inside & ~white), n)
        if len(_TAIJI_CACHE) > 600:
            _TAIJI_CACHE.clear()
        _TAIJI_CACHE[key] = hit
    return hit


def taiji(g: Gfx, cx: float, cy: float, r: float, angle: float = 0.0, outline: bool = True):
    """太极图：阳鱼亮、阴鱼暗（有外圈）；angle 弧度，正值顺时针"""
    white, dark, n = _taiji_imgs(r, angle)
    x0, y0 = int(round(cx - n / 2)), int(round(cy - n / 2))
    g.img.paste(1, (x0, y0), white)
    g.img.paste(0, (x0, y0), dark)
    if outline:
        g.d.ellipse((cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1), outline=1)


def bagua_ring(g: Gfx, cx: float, cy: float, r: float, rot: float = 0.0, order=XIANTIAN, w: int = 9,
               step: float = 3.0, show=None):
    """八卦盘：8 个三爻卦围成一圈，初爻朝内。rot 弧度（顺时针）；show(i) → 是否画第 i 个"""
    for i, name in enumerate(order):
        if show is not None and not show(i):
            continue
        a = rot + i * math.pi / 4
        ux, uy = math.sin(a), -math.cos(a)  # 半径方向（0 = 正上方）
        tx, ty = -uy, ux                    # 切向
        for k, bit in enumerate(TRIGRAMS[name][2]):
            rr = r + k * step
            px, py = cx + ux * rr, cy + uy * rr
            hw = w / 2
            if bit:
                g.d.line((px - tx * hw, py - ty * hw, px + tx * hw, py + ty * hw), fill=1)
            else:
                g1 = 1.4
                g.d.line((px - tx * hw, py - ty * hw, px - tx * g1, py - ty * g1), fill=1)
                g.d.line((px + tx * g1, py + ty * g1, px + tx * hw, py + ty * hw), fill=1)


# ---------------------------------------------------------------- 点阵

def mx_hexagram(g: Gfx, lines, count: int = 6):
    """点阵上的卦：第 1-6 行，上爻在上；阳爻 8 点，阴爻中间空 2 点"""
    for i in range(min(count, len(lines))):
        row = 6 - i
        for x in range(8):
            g.mx[row, x] = yang(lines[i]) or x not in (3, 4)


def mx_trigram(g: Gfx, name: str, y: int = 1, step: int = 2):
    bits = TRIGRAMS[name][2]
    for i in range(3):
        row = y + (2 - i) * step
        for x in range(8):
            g.mx[row, x] = bool(bits[i]) or x not in (3, 4)


def mx_taiji(g: Gfx, angle: float = 0.0):
    white, inside = _taiji_mask(8, 3.9, 3.5, 3.5, angle)
    g.mx[:] = white | (inside & ~_taiji_mask(8, 2.9, 3.5, 3.5, angle)[1])
