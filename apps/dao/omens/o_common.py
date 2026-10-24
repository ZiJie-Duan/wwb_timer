"""起卦共用：成卦（逐爻长出）、揭晓（卦名、卦序、卦辞、点阵）、由三爻组卦。

标准版式：卦象在左（x=6，上爻 y=6，6 爻 步距 6，爻厚 3），卦名在右上，卦辞在底行。
各起卦场景过程画在右侧，卦象在左边自下而上长出，最后 ~1.7 秒揭晓。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_out, ease_out_back, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, text_width
from ..engine.symbols import TRIGRAMS, changing, full_name, hexagram, mx_hexagram, yang
from .o_data import CI

HX, HY, HW, HH, HS = 6, 6, 28, 3, 6
REVEAL = 1.7  # 揭晓时长

YAO_NAME = {6: "老阴", 7: "少阳", 8: "少阴", 9: "老阳"}


def lines_of(upper: str, lower: str, moving: int = 0) -> list[int]:
    """上卦、下卦 → 6 爻（7/8）；moving = 1-6 时该爻为变爻（9/6）"""
    bits = TRIGRAMS[lower][2] + TRIGRAMS[upper][2]
    out = [7 if b else 8 for b in bits]
    if 1 <= moving <= 6:
        out[moving - 1] = 9 if out[moving - 1] == 7 else 6
    return out


def yao(g: Gfx, x: float, y: float, w: float, h: int, v, grow: float = 1.0, mark: bool = True):
    """一爻，grow 0..1 从中间向两边长出；变爻右侧一个小方点"""
    grow = clamp(grow)
    if grow <= 0:
        return
    cx = x + w / 2
    hw = w / 2 * grow
    if hw < 1:
        return
    if yang(v):
        g.d.rectangle((cx - hw, y, cx + hw - 1, y + h - 1), fill=1)
    else:
        gap = max(2, w // 4) / 2
        if hw > gap + 1:
            g.d.rectangle((cx - hw, y, cx - gap - 1, y + h - 1), fill=1)
            g.d.rectangle((cx + gap, y, cx + hw - 1, y + h - 1), fill=1)
    if mark and grow >= 1 and isinstance(v, int) and changing(v):
        g.d.rectangle((x + w + 2, y, x + w + 2 + h - 2, y + h - 1), fill=1)


def hexa(g: Gfx, lines, count: float = 6, x: float = HX, y: float = HY, w: int = HW, h: int = HH,
         step: int = HS):
    """count 可为小数：第 int(count) 爻正在长出"""
    n = int(count)
    for i in range(min(6, n + 1)):
        grow = 1.0 if i < n else ease_out_back(count - n)
        if grow > 0:
            yao(g, x, y + (5 - i) * step, w, h, lines[i], grow)


def mx_partial(g: Gfx, lines, count: float):
    mx_hexagram(g, lines, int(count))


def reveal(g: Gfx, lines, k: float, name_x: float = 44, name_y: float = 8, ci_y: float = 50,
           show_hexa: bool = True, rule: bool = True):
    """揭晓（k = 揭晓开始后的秒数）：卦象、卦名、第几卦、卦辞，点阵亮一下"""
    n, name, up, lo = hexagram(lines)
    if show_hexa:
        hexa(g, lines)
    typewriter(g, name_x, name_y, full_name(lines), k, cps=12)
    if k > 0.25:
        g.text(name_x, name_y + 15, f"第{cn_num(n)}卦", fill=1)
    if rule:
        p = ease_out(span(k, 0.15, 0.6))
        if p > 0:
            half = 60 * p
            for xx in range(int(64 - half), int(64 + half), 2):
                g.px(xx, ci_y - 4)
    s = CI[n]
    if k > 0.35:
        typewriter(g, 64, ci_y, s, k - 0.35, cps=18, align="center")
    mx_hexagram(g, lines)
    g.mx_level = 5 if k < 0.12 else 1


def burst(g: Gfx, cx: float, cy: float, k: float, n: int = 10, r0: float = 4, r1: float = 18, seed: int = 0):
    """一圈放射闪光（k 0..1）"""
    if not 0 < k < 1:
        return
    p = ease_out(k)
    for i in range(n):
        a = i / n * 2 * math.pi + seed
        ra, rb = r0 + (r1 - r0) * p * 0.6, r0 + (r1 - r0) * p
        g.d.line((cx + math.cos(a) * ra, cy + math.sin(a) * ra, cx + math.cos(a) * rb, cy + math.sin(a) * rb),
                 fill=1)


def label(g: Gfx, x: float, y: float, s: str, k: float):
    """一个弹出的小标签（k = 出现后秒数）：先放大的框，再定住"""
    if k <= 0:
        return
    p = ease_out_back(span(k, 0, 0.18))
    w = text_width(s) + 4
    cx = x
    hw = w / 2 * p
    g.d.rectangle((cx - hw - 1, y - 2, cx + hw, y + 12), fill=0)
    if p > 0.9:
        g.text(cx, y, s, align="center")
