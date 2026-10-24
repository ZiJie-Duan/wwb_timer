"""x1（睡与梦）批次共用的小工具：画像素画、预渲染背景、打呼的 Z、梦泡、圆形收拢、定时事件。

只给 x1_*.py 用（不登记场景）。
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine.anim import clamp, noise, rand
from ..engine.gfx import BAYER, H, W, Gfx, Sprite

_YY, _XX = np.mgrid[0:H, 0:W].astype(np.float32)


# ---------------------------------------------------------------- 画像素画（只在 setup / 模块加载时用）

class Pen:
    """在一块小画布上用直线、多边形、椭圆画像素画，最后变成 Sprite（或整屏背景 Image）。

    fill=None 透明，fill=0 涂黑（不透明），0<fill<=1 抖动灰度（不透明）；outline=1 描边。
    """

    def __init__(self, w: int = W, h: int = H):
        self.w, self.h = w, h
        self.on = np.zeros((h, w), dtype=bool)
        self.mask = np.zeros((h, w), dtype=bool)

    def _shape(self, kind: str, args, kw) -> np.ndarray:
        m = Image.new("1", (self.w, self.h))
        getattr(ImageDraw.Draw(m), kind)(*args, **kw)
        return np.array(m, dtype=bool)

    def _paint(self, region: np.ndarray, fill):
        if fill is None:
            return
        self.mask |= region
        if fill <= 0:
            self.on[region] = False
        elif fill >= 1:
            self.on[region] = True
        else:
            pat = np.tile(BAYER[:4, :4], (self.h // 4 + 1, self.w // 4 + 1))[: self.h, : self.w]
            self.on[region] = pat[region] < int(round(fill * 16))

    def poly(self, pts, fill=0, outline: int | None = 1):
        self._paint(self._shape("polygon", (pts,), {"fill": 1}), fill)
        if outline is not None:
            self.line(list(pts) + [pts[0]], outline)

    def ellipse(self, box, fill=0, outline: int | None = 1):
        self._paint(self._shape("ellipse", (box,), {"fill": 1}), fill)
        if outline is not None:
            r = self._shape("ellipse", (box,), {"outline": 1})
            self.mask |= r
            self.on[r] = bool(outline)

    def blob(self, boxes, fill=0.3, outline: int | None = 1):
        """几个椭圆并成一团（树冠、云），只描外轮廓"""
        reg = np.zeros((self.h, self.w), dtype=bool)
        for b in boxes:
            reg |= self._shape("ellipse", (b,), {"fill": 1})
        self._paint(reg, fill)
        if outline is not None:
            inner = reg.copy()
            inner[1:, :] &= reg[:-1, :]
            inner[:-1, :] &= reg[1:, :]
            inner[:, 1:] &= reg[:, :-1]
            inner[:, :-1] &= reg[:, 1:]
            edge = reg & ~inner
            self.on[edge] = bool(outline)

    def chord(self, box, a0, a1, fill=0, outline: int | None = 1):
        self._paint(self._shape("chord", (box, a0, a1), {"fill": 1}), fill)
        if outline is not None:
            r = self._shape("arc", (box, a0, a1), {"fill": 1})
            self.mask |= r
            self.on[r] = bool(outline)

    def arc(self, box, a0, a1, v: int = 1):
        r = self._shape("arc", (box, a0, a1), {"fill": 1})
        self.mask |= r
        self.on[r] = bool(v)

    def rect(self, box, fill=0, outline: int | None = 1):
        self._paint(self._shape("rectangle", (box,), {"fill": 1}), fill)
        if outline is not None:
            r = self._shape("rectangle", (box,), {"outline": 1})
            self.mask |= r
            self.on[r] = bool(outline)

    def line(self, pts, v: int = 1, width: int = 1):
        r = self._shape("line", (pts,), {"fill": 1, "width": width})
        self.mask |= r
        self.on[r] = bool(v)

    def px(self, x, y, v: int = 1):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.mask[y, x] = True
            self.on[y, x] = bool(v)

    def blit(self, spr: Sprite, x: int, y: int):
        h, w = spr.h, spr.w
        ys, xs = slice(max(0, y), min(self.h, y + h)), slice(max(0, x), min(self.w, x + w))
        sy, sx = slice(ys.start - y, ys.stop - y), slice(xs.start - x, xs.stop - x)
        m = spr.mask[sy, sx]
        self.mask[ys, xs] |= m
        self.on[ys, xs] = np.where(m, spr.on[sy, sx], self.on[ys, xs])

    def sprite(self) -> Sprite:
        return Sprite(on=self.on.copy(), mask=self.mask.copy())

    def image(self) -> Image.Image:
        """整屏背景（透明处 = 暗）"""
        return Image.fromarray(self.on.copy())


def backdrop(g: Gfx, img: Image.Image):
    """贴预渲染的整屏背景（比每帧画快得多）"""
    g.img.paste(img)


# ---------------------------------------------------------------- 打呼

def z_glyph(g: Gfx, x: float, y: float, s: int):
    """一个 Z，左上角 (x, y)，边长 s"""
    x, y = int(round(x)), int(round(y))
    g.d.line((x, y, x + s, y), fill=1)
    g.d.line((x + s, y, x, y + s), fill=1)
    g.d.line((x, y + s, x + s, y + s), fill=1)


def zzz(g: Gfx, x: float, y: float, t: float, seed: int = 0, every: float = 1.4, life: float = 4.2,
        rise: float = 22, drift: float = 12, s0: int = 2, s1: int = 5, on: float = 1.0):
    """从 (x, y) 不断冒出的 Z，往右上飘、变大、渐散。on<1 时少冒（入场/醒来时用）"""
    n = int(life / every) + 1
    k0 = int(t // every)
    for j in range(n):
        k = k0 - j
        if k < 0:
            continue
        age = t - k * every
        p = age / life
        if p >= 1 or rand(k, seed + 3) > on:
            continue
        if p > 0.7 and rand(int(t * 8) + k, seed) < (p - 0.7) * 3:
            continue
        s = int(round(s0 + (s1 - s0) * p))
        xx = x + drift * p + math.sin(age * 2.2 + k) * 2
        yy = y - rise * p
        z_glyph(g, xx, yy - s, s)


def mx_zzz(g: Gfx, t: float, every: float = 1.4):
    """点阵：小 Z 从左下往右上飘"""
    for j in range(2):
        k = int(t // every) - j
        p = (t - k * every) / (every * 2)
        if not 0 <= p < 1:
            continue
        x = int(-1 + p * 6)
        y = int(5 - p * 6)
        for dx in range(3):
            g.mx_set(x + dx, y)
            g.mx_set(x + dx, y + 2)
        g.mx_set(x + 1, y + 1)


# ---------------------------------------------------------------- 遮罩

def iris(g: Gfx, cx: float, cy: float, r: float, aspect: float = 1.0):
    """圆形收拢：只留 (cx, cy) 半径 r 内的画面（aspect<1 横向更扁）"""
    if r >= 160:
        return
    a = g.array()
    a &= ((_XX - cx) * aspect) ** 2 + (_YY - cy) ** 2 <= r * r
    g.put(a)


def clip_ellipse(g: Gfx, box, keep_outside: np.ndarray | None = None):
    """把 box 矩形内、椭圆外的亮点清掉（梦泡里的画面不溢出）"""
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, max((x1 - x0) / 2, 1), max((y1 - y0) / 2, 1)
    a = g.array()
    ys, xs = slice(max(0, int(y0)), min(H, int(y1) + 1)), slice(max(0, int(x0)), min(W, int(x1) + 1))
    inside = ((_XX[ys, xs] - cx) / rx) ** 2 + ((_YY[ys, xs] - cy) / ry) ** 2 <= 1
    a[ys, xs] &= inside
    g.put(a)


def wipe(g: Gfx, box):
    g.d.rectangle(box, fill=0)


# ---------------------------------------------------------------- 时间

def ev(t: float, period: float, dur: float, phase: float = 0.0):
    """周期性小事件：t 落在第 k 次事件里 → (k, 事件内秒数)；否则 None"""
    if t < phase:
        return None
    k, u = divmod(t - phase, period)
    if u < dur:
        return int(k), u
    return None


def breathe(t: float, period: float = 4.2) -> float:
    """呼吸：0（呼尽）..1（吸满），吸快呼慢"""
    p = (t % period) / period
    return math.sin(p / 0.4 * math.pi / 2) if p < 0.4 else 0.5 + 0.5 * math.cos((p - 0.4) / 0.6 * math.pi)


def sway(t: float, seed: int, amp: float = 1.0, speed: float = 0.4) -> float:
    return (noise(t * speed, seed) - 0.5) * 2 * amp


def blink_eye(t: float, seed: int = 0) -> bool:
    """醒着时偶尔眨眼"""
    return (t + rand(int(t / 3.1), seed) * 2) % 3.1 < 0.12


def dither_fill(level: float) -> int:
    return int(round(clamp(level) * 16))


def halo(spr: Sprite, r: int = 1) -> Sprite:
    """给像素画加一圈暗边（在杂乱背景上更清楚）"""
    on = np.pad(spr.on, r)
    m = np.pad(spr.mask, r)
    grow = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            grow |= np.roll(np.roll(m, dy, 0), dx, 1)
    return Sprite(on=on, mask=grow)
