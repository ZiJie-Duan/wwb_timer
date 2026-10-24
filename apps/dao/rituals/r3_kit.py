"""r3 批次（手诀·法器·步罡）共用的小工具：粗线描边、旋转、道袍袖、轮次。

不登记场景，只被 r3_*.py 导入。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp
from ..engine.cn import cn_num
from ..engine.gfx import Gfx


def rot(pts, cx: float, cy: float, a: float, ox: float = 0.0, oy: float = 0.0):
    """把局部坐标 pts 绕原点转 a 弧度（顺时针为正，屏幕坐标），再平移到 (cx, cy)"""
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x + ox) * c - (y + oy) * s, cy + (x + ox) * s + (y + oy) * c) for x, y in pts]


def capsule(g: Gfx, x0: float, y0: float, x1: float, y1: float, w: float, fill: int = 1):
    """圆头粗线段"""
    r = w / 2
    g.d.line((x0, y0, x1, y1), fill=fill, width=int(round(w)))
    g.d.ellipse((x0 - r + 0.5, y0 - r + 0.5, x0 + r - 0.5, y0 + r - 0.5), fill=fill)
    g.d.ellipse((x1 - r + 0.5, y1 - r + 0.5, x1 + r - 0.5, y1 + r - 0.5), fill=fill)


def ocapsule(g: Gfx, x0: float, y0: float, x1: float, y1: float, w: float):
    """描边圆头粗线段（外白内黑），能盖住后面的东西 —— 像素手指"""
    capsule(g, x0, y0, x1, y1, w, 1)
    capsule(g, x0, y0, x1, y1, w - 2, 0)


def sleeve(g: Gfx, wx: float, wy: float, ang: float, length: float = 70, w0: float = 10, w1: float = 30,
           shade: float = 0.25, cuff: bool = True):
    """道袍宽袖：从手腕 (wx, wy) 朝 ang 方向（弧度，0 = 向右）伸出画外，口宽 w0 → 根宽 w1。抖动灰度 + 袖口镶边"""
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    pts = [(wx + nx * w0 / 2, wy + ny * w0 / 2), (wx + ux * length + nx * w1 / 2, wy + uy * length + ny * w1 / 2),
           (wx + ux * length - nx * w1 / 2, wy + uy * length - ny * w1 / 2), (wx - nx * w0 / 2, wy - ny * w0 / 2)]
    g.d.polygon(pts, fill=0)
    g.shade_poly(pts, shade)
    if cuff:  # 袖口两道镶边
        for k in (2, 4):
            a = (wx + ux * k + nx * (w0 / 2 + k * (w1 - w0) / length / 2),
                 wy + uy * k + ny * (w0 / 2 + k * (w1 - w0) / length / 2))
            b = (wx + ux * k - nx * (w0 / 2 + k * (w1 - w0) / length / 2),
                 wy + uy * k - ny * (w0 / 2 + k * (w1 - w0) / length / 2))
            g.d.line((a, b), fill=1 if k == 2 else 0)


def round_of(e: float, cycle: float) -> tuple[int, float, float]:
    """→ (第几轮 1.., 本轮已过秒数 k, 本轮进度 p 0..1)"""
    n = int(e // cycle)
    k = e - n * cycle
    return n + 1, k, clamp(k / cycle)


def side_text(g: Gfx, x: float, y: float, s: str, a: float = 1.0, size: int = 12):
    """竖排文字，a 为显现比例（逐字）"""
    k = int(round(clamp(a) * len(s)))
    if k:
        g.vtext(x, y, s[:k], size=size)


def nth(n: int, unit: str) -> str:
    return f"第{cn_num(n)}{unit}"


def sparkle(g: Gfx, x: float, y: float, r: int = 2):
    """十字闪光"""
    g.d.line((x - r, y, x + r, y), fill=1)
    g.d.line((x, y - r, x, y + r), fill=1)
