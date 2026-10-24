"""r1 批（香火·供奉·科仪）共用的小零件：宽袖手臂、竖排渐显文字、闪光、点阵小工具。

本文件不登记场景，只被 r1_*.py 导入。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, rand
from ..engine.gfx import Gfx, Sprite

FIST = Sprite("""
 .####.
#.....#
#.###.#
#.....#
#.###.#
.#...#.
 .###.
""")

OPEN_HAND = Sprite("""
 .#.#.#.
 .#.#.#.
.#.#.#.#.
#.......#
#.......#
.#.....#.
 .#####.
""")


def sleeve(g: Gfx, hx: float, hy: float, ang: float, fist: bool = True, level: float = 0.25, wide: float = 1.0):
    """道袍宽袖手臂：手在 (hx, hy)，手臂朝 ang（弧度，0 = 向右，-π/2 = 向上）方向伸出画外。
    袖子是抖动灰度的布，袖口一道镶边"""
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    def p(d, w):
        return (hx + ux * d + nx * w, hy + uy * d + ny * w)
    # 手腕
    wrist = [p(2, -3), p(9, -4), p(9, 4), p(2, 3)]
    g.d.polygon(wrist, fill=0, outline=1)
    cuff_a, cuff_b = 9, 13
    body = [p(cuff_a, -8 * wide), p(160, -22 * wide), p(160, 26 * wide), p(cuff_a, 9 * wide)]
    g.d.polygon(body, fill=0)
    g.shade_poly(body, level)
    g.d.line((*p(cuff_a, -8 * wide), *p(cuff_a, 9 * wide)), fill=1)
    g.d.line((*p(cuff_b, -9 * wide), *p(cuff_b, 10 * wide)), fill=1)
    g.d.line((*p(cuff_a + 1, -8 * wide), *p(cuff_b - 1, -9 * wide)), fill=0)
    g.d.line((*p(30, 2), *p(70, 8)), fill=0)  # 衣褶
    spr = FIST if fist else OPEN_HAND
    g.blit(spr, hx - spr.w // 2, hy - spr.h // 2)


def vreveal(g: Gfx, x: float, y: float, s: str, a: float = 1.0, size: int = 12):
    """竖排文字，a（0..1）= 显示前几个字"""
    k = int(round(clamp(a) * len(s)))
    if k > 0:
        g.vtext(x, y, s[:k], size=size)


def sparkles(g: Gfx, cx: float, cy: float, rx: float, ry: float, t: float, n: int = 8, seed: int = 0):
    """周围一圈一闪一闪的小星（十字）"""
    for j in range(n):
        if blink(t + j * 0.137, 0.55, 0.35):
            a = rand(j, seed) * 2 * math.pi
            r = 0.4 + 0.6 * rand(j + 50, seed)
            x, y = cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r
            g.px(x, y)
            if rand(j + 99, seed) < 0.4:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    g.px(x + dx, y + dy)


def rays(g: Gfx, cx: float, cy: float, r0: float, r1: float, n: int = 12, rot: float = 0.0, sy: float = 1.0,
         a0: float = 0.0, a1: float = 2 * math.pi):
    """放射线；a0..a1 只画这一段角度（弧度，0 = 向右，-π/2 = 向上）"""
    full = abs(a1 - a0 - 2 * math.pi) < 1e-6
    for i in range(n):
        a = a0 + ((i / n * (a1 - a0) + rot) % (a1 - a0) if not full else i / n * 2 * math.pi + rot)
        g.d.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0 * sy, cx + math.cos(a) * r1,
                  cy + math.sin(a) * r1 * sy), fill=1)


def arc_dots(g: Gfx, cx: float, cy: float, r: float, a0: float, a1: float, step: int = 2, sy: float = 1.0):
    """点状圆弧（声波、水纹），角度弧度"""
    n = max(4, int(abs(a1 - a0) * r))
    for i in range(0, n + 1, step):
        a = a0 + (a1 - a0) * i / n
        g.px(round(cx + math.cos(a) * r), round(cy + math.sin(a) * r * sy))


def mx_ring(g: Gfx, r: float, cx: float = 3.5, cy: float = 3.5, w: float = 0.7):
    for y in range(8):
        for x in range(8):
            if abs(math.hypot(x - cx, y - cy) - r) < w:
                g.mx[y, x] = True
