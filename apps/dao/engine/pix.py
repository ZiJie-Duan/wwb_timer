"""像素画工具（清晰的 1 位像素风，参考《元气骑士》《Minit》）：逐像素手绘的精灵 + 逐帧动画 + 打击感特效。

精灵用字符画写：'#' 亮、'.' 暗（不透明，会盖住底下）、' ' 透明。多帧用一行 '---' 隔开：

    DAOSHI = frames('''
      .###.
      #...#
    ---
      .###.
      #.#.#
    ''')

    blit(g, spr, x, y, flip=False, outline=True)   outline：精灵外围描 1 像素黑边，压在别的东西上也分得清
    anim(frames, t, fps)                         按时间取帧
    Puffs / Sparks                               像素烟团、火星（有状态，每帧 step）
    shake(g, t, amp) / flash(g, k)               屏幕震动、闪白（整帧反色）
    checker(g, box, level)                       规则网点阴影（25% / 50% / 75%）
"""
from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image

from .gfx import H, W, Gfx, Sprite


def frames(art: str) -> list[Sprite]:
    """多帧字符画 → 精灵列表（帧之间用只含 --- 的行隔开）"""
    out, cur = [], []
    for ln in art.strip("\n").split("\n"):
        if ln.strip() == "---":
            out.append(Sprite("\n".join(cur)))
            cur = []
        else:
            cur.append(ln)
    if cur:
        out.append(Sprite("\n".join(cur)))
    return out


def sprite(art: str) -> Sprite:
    return Sprite(art)


_OUTLINE: dict[int, Image.Image] = {}


def _outline_img(spr: Sprite) -> Image.Image:
    key = id(spr)
    im = _OUTLINE.get(key)
    if im is None:
        m = np.pad(spr.mask, 1)
        grown = m.copy()
        grown[1:, :] |= m[:-1, :]
        grown[:-1, :] |= m[1:, :]
        grown[:, 1:] |= m[:, :-1]
        grown[:, :-1] |= m[:, 1:]
        im = _OUTLINE[key] = Image.fromarray(grown & ~m)
    return im


_FLIPS: dict[int, Sprite] = {}


def flipped(spr: Sprite) -> Sprite:
    f = _FLIPS.get(id(spr))
    if f is None:
        f = _FLIPS[id(spr)] = spr.flip()
    return f


def blit(g: Gfx, spr: Sprite, x: float, y: float, flip: bool = False, outline: bool = True, invert: bool = False):
    """贴精灵（左上角 x, y）。outline：外围一圈黑边（把背后的东西切开）"""
    s = flipped(spr) if flip else spr
    x, y = int(round(x)), int(round(y))
    if outline:
        g.img.paste(0, (x - 1, y - 1), _outline_img(s))
    g.blit(s, x, y, invert=invert)


def blit_c(g: Gfx, spr: Sprite, cx: float, by: float, **kw):
    """以底边中点 (cx, by) 定位（角色站在地上用）"""
    blit(g, spr, cx - spr.w / 2, by - spr.h, **kw)


def anim(fr: list[Sprite], t: float, fps: float = 6.0, loop: bool = True) -> Sprite:
    i = int(t * fps)
    return fr[i % len(fr)] if loop else fr[min(i, len(fr) - 1)]


def stretch(spr: Sprite, sx: float = 1.0, sy: float = 1.0) -> Sprite:
    """挤压拉伸（落地压扁、起跳拉长）：最近邻缩放，按 0.1 档缓存"""
    sx, sy = round(sx, 1), round(sy, 1)
    if sx == 1 and sy == 1:
        return spr
    key = (id(spr), sx, sy)
    s = _STRETCH.get(key)
    if s is None:
        w, h = max(1, int(round(spr.w * sx))), max(1, int(round(spr.h * sy)))
        on = np.array(Image.fromarray(spr.on).resize((w, h), Image.NEAREST))
        mk = np.array(Image.fromarray(spr.mask).resize((w, h), Image.NEAREST))
        s = _STRETCH[key] = Sprite(on=on, mask=mk)
    return s


_STRETCH: dict = {}

# ---------------------------------------------------------------- 网点与线

PATTERNS = {
    0.125: np.array([[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 0]], bool),
    0.25: np.array([[1, 0], [0, 0]], bool),
    0.5: np.array([[1, 0], [0, 1]], bool),
    0.75: np.array([[1, 1], [1, 0]], bool),
}


def checker(g: Gfx, box, level: float = 0.5, fill: int = 1):
    """规则网点（像素画的阴影 / 材质）：level 取 0.125 / 0.25 / 0.5 / 0.75。fill=0 在亮处挖暗点"""
    x0, y0, x1, y1 = (int(v) for v in box)
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return
    pat = PATTERNS[min(PATTERNS, key=lambda k: abs(k - level))]
    ph, pw = pat.shape
    m = np.tile(pat, ((H + ph - 1) // ph, (W + pw - 1) // pw))[y0:y1, x0:x1]
    im = Image.fromarray(m)
    g.img.paste(1 if fill else 0, (x0, y0), im)


def checker_mask(g: Gfx, mask: np.ndarray, level: float = 0.5, fill: int = 1):
    """在任意形状（整屏 bool 掩码）里铺网点"""
    pat = PATTERNS[min(PATTERNS, key=lambda k: abs(k - level))]
    ph, pw = pat.shape
    m = np.tile(pat, ((H + ph - 1) // ph, (W + pw - 1) // pw))[:H, :W] & mask
    g.img.paste(1 if fill else 0, (0, 0), Image.fromarray(m))


def dotted(g: Gfx, x0, y0, x1, y1, step: int = 2, phase: int = 0, v: int = 1):
    """虚线（光线、气流、轨迹）"""
    n = int(max(abs(x1 - x0), abs(y1 - y0)))
    for i in range(n + 1):
        if (i + phase) % step == 0:
            k = i / max(n, 1)
            g.px(x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, v)


# ---------------------------------------------------------------- 粒子

class Puffs:
    """像素烟团：小圆从 1 像素长到 r、再缩小消失，边飘边往上（经典像素烟）"""

    def __init__(self, seed: int = 0):
        self.p: list[list[float]] = []  # x, y, vx, vy, age, life, rmax
        self.rng = random.Random(seed)

    def emit(self, x, y, vx=0.0, vy=-8.0, life=1.6, rmax=2.0, spread=2.0):
        r = self.rng
        self.p.append([x + (r.random() - 0.5) * spread, y, vx + (r.random() - 0.5) * 3, vy * (0.8 + r.random() * 0.4),
                       0.0, life * (0.8 + r.random() * 0.4), rmax * (0.7 + r.random() * 0.5)])

    def step(self, dt, wind=0.0):
        keep = []
        for q in self.p:
            q[4] += dt
            if q[4] < q[5]:
                q[0] += (q[2] + wind) * dt
                q[1] += q[3] * dt
                q[3] *= 1 - 0.6 * dt
                keep.append(q)
        self.p = keep

    def draw(self, g: Gfx, hollow_after: float = 0.6):
        for x, y, vx, vy, age, life, rmax in self.p:
            k = age / life
            r = rmax * math.sin(math.pi * min(k * 1.2, 1.0))
            ix, iy = int(round(x)), int(round(y))
            if r < 0.7:
                g.px(ix, iy)
            elif k > hollow_after:  # 快散时变成空心圈，再变成几个点
                if k > 0.85:
                    for a in range(0, 360, 90):
                        g.px(ix + round(math.cos(math.radians(a + age * 90)) * r), iy + round(math.sin(math.radians(a)) * r))
                else:
                    g.d.ellipse((ix - r, iy - r, ix + r, iy + r), outline=1)
            else:
                g.d.ellipse((ix - r, iy - r, ix + r, iy + r), fill=1)

    def __len__(self):
        return len(self.p)


class Sparks:
    """火星 / 碎屑：带重力的点，可留 1 像素拖尾"""

    def __init__(self, seed: int = 0):
        self.p: list[list[float]] = []
        self.rng = random.Random(seed)

    def burst(self, x, y, n=8, speed=30.0, up=0.0, life=0.6, gravity=60.0):
        for _ in range(n):
            a = self.rng.random() * 2 * math.pi
            v = speed * (0.4 + self.rng.random() * 0.8)
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v - up, 0.0, life * (0.6 + self.rng.random() * 0.6),
                           gravity])

    def step(self, dt):
        keep = []
        for q in self.p:
            q[4] += dt
            if q[4] < q[5]:
                q[3] += q[6] * dt
                q[0] += q[2] * dt
                q[1] += q[3] * dt
                keep.append(q)
        self.p = keep

    def draw(self, g: Gfx, trail: bool = True):
        for x, y, vx, vy, age, life, grav in self.p:
            g.px(x, y)
            if trail and age < life * 0.6:
                g.px(x - vx * 0.03, y - vy * 0.03)


# ---------------------------------------------------------------- 特效

def shake(g: Gfx, t: float, amp: float = 1.0, seed: int = 0):
    """屏幕震动：设 g.offset，合成时整帧平移"""
    if amp <= 0:
        return
    r = random.Random(int(t * 30) * 7 + seed)
    g.offset = (int(round((r.random() - 0.5) * 2 * amp)), int(round((r.random() - 0.5) * 2 * amp)))


def flash(g: Gfx, on: bool = True):
    """整帧反色一下（命中 / 雷光 / 圆满的闪白）"""
    if on:
        g.invert_all = True
