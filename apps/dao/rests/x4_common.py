"""x4 批（仙踪与灵兽）共用的小工具：把 PIL 画好的小图烘成 Sprite（带抖动灰度），省得每帧整屏 numpy。"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine.gfx import BAYER4, Gfx, Sprite


class Bake:
    """在一块小画布上画，最后 .sprite() 得到 Sprite。

    poly / ellipse 填充区域会变成“不透明”（盖住背景），内部按 level 抖动出灰度，轮廓画亮。
    line / point 只画亮。坐标都是小画布里的。
    """

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.on = Image.new("1", (w, h))
        self.mask = Image.new("1", (w, h))
        self.do = ImageDraw.Draw(self.on)
        self.dm = ImageDraw.Draw(self.mask)
        tile = np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]
        self._bayer = tile

    def _fill(self, shape_fn, level: float):
        m = Image.new("1", (self.w, self.h))
        shape_fn(ImageDraw.Draw(m))
        mm = np.array(m, dtype=bool)
        on = np.array(self.on, dtype=bool)
        on[mm] = self._bayer[mm] < int(round(level * 16))
        self.on = Image.fromarray(on)
        self.do = ImageDraw.Draw(self.on)
        shape_fn(self.dm)

    def poly(self, pts, level: float = 0.0, outline: bool = True):
        self._fill(lambda d: d.polygon(pts, fill=1), level)
        if outline:
            self.do.polygon(pts, outline=1)
            self.dm.polygon(pts, outline=1)

    def ellipse(self, box, level: float = 0.0, outline: bool = True):
        self._fill(lambda d: d.ellipse(box, fill=1), level)
        if outline:
            self.do.ellipse(box, outline=1)

    def line(self, pts, fill: int = 1, width: int = 1):
        self.do.line(pts, fill=fill, width=width)
        self.dm.line(pts, fill=1, width=width)

    def point(self, x, y, fill: int = 1):
        self.do.point((x, y), fill=fill)
        self.dm.point((x, y), fill=1)

    def clear(self, pts):
        """挖成透明"""
        self.do.polygon(pts, fill=0)
        self.dm.polygon(pts, fill=0)

    def sprite(self) -> Sprite:
        return Sprite(on=np.array(self.on, dtype=bool), mask=np.array(self.mask, dtype=bool))


def sound_arcs(g: Gfx, x: float, y: float, k: float, n: int = 3, gap: float = 4, right: bool = True, spread=0.7):
    """声波：从 (x, y) 向一侧扩散的几道弧，k 0..1 推进"""
    for i in range(n):
        r = (k * n - i) * gap + 2
        if r <= 2 or r > n * gap + 2:
            continue
        a0 = -spread if right else math.pi - spread
        a1 = spread if right else math.pi + spread
        steps = max(3, int(r * 1.2))
        pts = [(x + math.cos(a0 + (a1 - a0) * j / steps) * r, y + math.sin(a0 + (a1 - a0) * j / steps) * r)
               for j in range(steps + 1)]
        g.d.line(pts, fill=1)


def wave_line(g: Gfx, y: float, t: float, amp: float = 1.0, x0: int = 0, x1: int = 128, wl: float = 10.0,
              speed: float = 1.0, dotted: int = 1, seed: int = 0):
    """水面线（正弦），dotted>1 时隔点"""
    prev = None
    for x in range(x0, x1, dotted):
        yy = y + math.sin(x / wl * 2 * math.pi + t * speed + seed) * amp
        if dotted > 1:
            g.px(x, round(yy))
        else:
            if prev is not None:
                g.d.line((x - 1, prev, x, yy), fill=1)
            prev = yy


def mx_sprite(g: Gfx, rows: str, dx: int = 0, dy: int = 0):
    """点阵贴图：rows 用 '#' '.'，每行 8 字"""
    for y, ln in enumerate(rows.strip("\n").split("\n")):
        ln = ln.strip()
        for x, ch in enumerate(ln):
            if ch == "#":
                g.mx_set(x + dx, y + dy)


def art(s: str) -> "Sprite":
    """像素画，但每行第一个 '#' 之前、最后一个 '#' 之后的 '.' 当透明（省得手写空格）"""
    rows = []
    for ln in s.strip("\n").split("\n"):
        ln = ln.strip()
        i0, i1 = ln.find("#"), ln.rfind("#")
        rows.append("".join(" " if (x < i0 or x > i1) else ch for x, ch in enumerate(ln)))
    return Sprite("\n".join(rows))
