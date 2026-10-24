"""r5 批（易象·星斗·雷法·风水）共用的小工具。不登记场景。"""
from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image, ImageDraw

from ..engine.gfx import BAYER, H, W, Gfx


def cloud_blobs(cx: float, cy: float, w: float, h: float, seed: int, n: int = 5):
    """一团云的若干椭圆（确定性）"""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        k = (i + 0.5) / n
        bw = w * (0.3 + rng.random() * 0.2)
        bh = h * (0.55 + rng.random() * 0.45) * math.sin(math.pi * (0.15 + 0.7 * k)) + h * 0.25
        bx = cx - w / 2 + k * w
        out.append((bx - bw / 2, cy - bh / 2 + h * 0.1, bx + bw / 2, cy + bh / 2 + h * 0.1))
    out.append((cx - w / 2, cy, cx + w / 2, cy + h / 2))
    return out


def mist(g: Gfx, blobs, level: float = 0.3, outline: bool = True, erase: bool = True):
    """把一组椭圆合成一团抖动灰度的云：内部清空后铺 level 灰度，外缘一道轮廓"""
    m = Image.new("1", (W, H))
    md = ImageDraw.Draw(m)
    for b in blobs:
        md.ellipse(b, fill=1)
    mask = np.array(m, dtype=bool)
    if not mask.any():
        return
    a = g.array()
    pat = BAYER < int(round(max(min(level, 1), 0) * 16))
    if erase:
        a[mask] = pat[mask]
    else:
        a[mask] |= pat[mask]
    if outline:
        edge = mask.copy()
        inner = mask[1:-1, 1:-1] & mask[:-2, 1:-1] & mask[2:, 1:-1] & mask[1:-1, :-2] & mask[1:-1, 2:]
        edge[1:-1, 1:-1] &= ~inner
        a |= edge
    g.put(a)


def arrow_head(g: Gfx, x: float, y: float, ang: float, s: float = 3.0):
    """箭头：尖在 (x, y)，指向 ang（弧度，0 = 向右）"""
    for da in (2.6, -2.6):
        g.d.line((x, y, x + math.cos(ang + da) * s, y + math.sin(ang + da) * s), fill=1)


def mx_line(g: Gfx, x0: float, y0: float, x1: float, y1: float):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        k = i / max(n, 1)
        g.mx_set(int(round(x0 + (x1 - x0) * k)), int(round(y0 + (y1 - y0) * k)))
