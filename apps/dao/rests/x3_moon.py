"""望月：月相按真实日期算（今晚天上是什么月，画面里就是什么月）。

苏轼《水调歌头》“明月几时有”“千里共婵娟”，李白“举头望明月”，杜甫“月是故乡明”，张九龄“海上生明月”，
李清照《一剪梅》“雁字回时，月满西楼”。

入场：月亮从江面尽头升起，江上的月影一道道铺开。
持续：月悬江上（带月海的暗斑，未照亮的部分隐约可见“地照”），江心一条碎银似的月影随波闪动；
      左岸小亭里有人凭栏望月。星星闪烁。
      小事件：一缕薄云慢慢掠过月面；一行雁排成“人”字从月前飞过；月影里偶尔跳起一尾鱼。
      题诗隔一阵换一句；月相名（上弦月、望月……）写在月下。
退场：云幕从右边合拢，月光收尽。
"""
from __future__ import annotations

import math
import random
import time

import numpy as np

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import stars
from ..engine.gfx import Gfx, Sprite, BAYER4
from ..engine.scene import Rest, register
from .x3_lib import Cloud, bird, every, halo, layer, peaks, ptext, vpoem

SYNODIC = 29.530588853
NEW_MOON_JD = 2451550.1        # 2000-01-06 18:14 UTC 的朔
MX0, MY0, R = 86, 14, 11       # 月亮
WATER = 40
LINES = ["明月几时有", "海上生明月", "举头望明月", "千里共婵娟", "月是故乡明"]
PHASES = [(1.5, "朔月"), (6.4, "蛾眉月"), (8.9, "上弦月"), (13.8, "盈凸月"), (15.8, "望月"), (20.8, "亏凸月"),
          (23.4, "下弦月"), (28.0, "残月"), (99, "朔月")]

FIGURE = halo(Sprite("""
  .##.
  ####
  .##.
  ###.
  ####
  ####
"""))


def moon_age(now: float | None = None) -> float:
    jd = (now if now is not None else time.time()) / 86400 + 2440587.5
    return (jd - NEW_MOON_JD) % SYNODIC


def phase_name(age: float) -> str:
    for lim, name in PHASES:
        if age < lim:
            return name
    return "朔月"


def moon_sprite(age: float, r: int) -> Sprite:
    """月亮：亮面（带月海暗斑）+ 暗面的“地照”（极稀的点）+ 隐约的轮廓"""
    n = 2 * r + 3
    c = n / 2 - 0.5
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = xs - c, ys - c
    inside = dx * dx + dy * dy <= r * r
    w = np.sqrt(np.clip(r * r - dy * dy, 0, None))
    k = math.cos(2 * math.pi * age / SYNODIC)
    if age < SYNODIC / 2:          # 盈：右边亮
        lit = dx >= k * w
    else:                          # 亏：左边亮
        lit = dx <= -k * w
    lit &= inside
    # 月海：几块暗斑（隔点）
    mare = np.zeros_like(inside)
    for mx, my, mr in ((-0.32, -0.28, 0.3), (0.22, -0.3, 0.2), (0.12, 0.05, 0.22), (-0.15, 0.4, 0.18)):
        mare |= (dx / r - mx) ** 2 + (dy / r - my) ** 2 < mr * mr
    bay = np.tile(BAYER4, (n // 4 + 1, n // 4 + 1))[:n, :n]
    on = lit & ~(mare & (bay < 4))
    earth = inside & ~lit & (bay < 1)                      # 地照
    edge = inside & ~(((dx * dx + dy * dy) <= (r - 1) ** 2))
    on |= earth | (edge & ~lit & ((xs + ys) % 3 == 0))
    return Sprite(on=on, mask=inside)


def mx_moon(g: Gfx, age: float):
    k = math.cos(2 * math.pi * age / SYNODIC)
    for y in range(8):
        for x in range(8):
            dx, dy = x - 3.5, y - 3.5
            if dx * dx + dy * dy > 13.5:
                continue
            w = math.sqrt(max(13.5 - dy * dy, 0))
            lit = dx >= k * w if age < SYNODIC / 2 else dx <= -k * w
            if lit:
                g.mx[y, x] = True
    if not g.mx.any():  # 朔：只留一圈
        for y in range(8):
            for x in range(8):
                if 9 < (x - 3.5) ** 2 + (y - 3.5) ** 2 <= 14 and (x + y) % 2:
                    g.mx[y, x] = True


@register
class MoonGaze(Rest):
    id = "x3.moon"
    name = "望月"
    desc = "江上月升，月相按今晚真实的月龄画；月影碎银闪动，亭中人望月，薄云掠月，雁过月前"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        s = self.seed
        self.age = moon_age()
        self.build()
        self.hills = layer(peaks(128, WATER, [(8, 26, 22), (38, 30, 20), (64, 33, 18), (120, 31, 16)], s, 1.0), 0.18,
                           outline=1, fog=8, floor=0.0, solid=True)
        self.cloud = Cloud(random.Random(s * 9), 34, 8, lumps=5)

    def build(self):
        self.moon = moon_sprite(self.age, R)
        self.illum = (1 - math.cos(2 * math.pi * self.age / SYNODIC)) / 2
        self.pname = phase_name(self.age)

    # ------------------------------------------------------------ 零件

    def sky(self, g: Gfx, t: float, my: float = MY0):
        stars(g, t, self.seed, n=26, box=(0, 0, 128, WATER - 6), twinkle=0.3)
        g.d.ellipse((MX0 - R - 3, my - R - 3, MX0 + R + 3, my + R + 3), fill=0)   # 月旁不见星
        g.blit(self.moon, MX0 - R - 1, my - R - 1)

    def water(self, g: Gfx, t: float, my: float = MY0, strength: float = 1.0):
        g.d.rectangle((0, WATER, 127, 63), fill=0)
        g.d.line((0, WATER, 127, WATER), fill=1)
        vis = clamp((WATER - my) / 22) * strength * (0.35 + 0.65 * self.illum)
        for j in range(11):  # 月影：越近越宽、碎成一段段
            y = WATER + 2 + j * 2
            half = (2 + j * 1.4) * (0.4 + 0.6 * vis)
            for seg in range(3):
                ph = noise(t * 1.3 + j * 0.7 + seg * 3.1, self.seed + seg)
                if ph < 1 - vis * 0.9:
                    continue
                x0 = MX0 + (seg - 1) * half * 0.8 + (noise(t * 0.9 + j + seg, 5) - 0.5) * half
                ln = 1 + half * 0.5 * ph
                g.d.line((x0 - ln / 2, y, x0 + ln / 2, y), fill=1)
        for j in range(5):  # 其他地方的淡波
            y = WATER + 4 + j * 4
            x = (rand(j, 3) * 128 + t * (2 + j)) % 150 - 20
            if abs(x - MX0) > 20:
                g.d.line((x, y, x + 3 + j, y), fill=1)

    def pavilion(self, g: Gfx, t: float):
        """左岸小亭：翘角攒尖顶，两根柱，亭中人凭栏"""
        x, y = 22, 46          # 亭基中心
        g.d.polygon([(0, 50), (6, 44), (16, 43), (34, 45), (42, 50), (44, 63), (0, 63)], fill=0, outline=1)
        g.d.line((x - 9, y - 3, x - 9, y - 13), fill=1)
        g.d.line((x + 9, y - 3, x + 9, y - 13), fill=1)
        g.d.line((x - 10, y - 3, x + 10, y - 3), fill=1)   # 亭基
        g.d.line((x - 9, y - 7, x + 9, y - 7), fill=1)     # 栏杆
        for xx in range(x - 7, x + 9, 3):
            g.d.line((xx, y - 7, xx, y - 4), fill=1)
        roof = [(x - 15, y - 16), (x - 11, y - 15), (x, y - 23), (x + 11, y - 15), (x + 15, y - 16),
                (x + 12, y - 13), (x - 12, y - 13)]
        g.d.polygon(roof, fill=0, outline=1)
        g.d.line((x, y - 23, x, y - 26), fill=1)           # 宝顶
        g.blit(FIGURE, x + 1, y - 7 - FIGURE.h + 3)
        g.px(x + 3, y - 12 - (1 if int(t / 9) % 4 == 0 else 0))   # 偶尔抬头

    def passing_cloud(self, g: Gfx, t: float):
        ev = every(t, 97.0, 36.0, 28.0)
        if not ev:
            return
        k, lt = ev
        x = lerp(150, -30, lt / 36.0)
        y = MY0 + (rand(k, 4) - 0.5) * 10
        self.cloud.draw(g, x, y, 1.0, 1.0)

    def geese(self, g: Gfx, t: float):
        """雁字回时，月满西楼"""
        ev = every(t, 151.0, 14.0, 63.0)
        if not ev:
            return
        k, lt = ev
        x = lerp(136, -30, lt / 14.0)
        y = MY0 - 4 + math.sin(lt * 0.5) * 2 + (rand(k, 2) - 0.5) * 8
        n = 5 + int(rand(k, 3) * 3)
        for i in range(n):  # 人字形
            row = (i + 1) // 2
            side = 1 if i % 2 else -1
            g.d.rectangle((x + row * 4 - 3, y + side * row * 2.5 - 2, x + row * 4 + 3, y + side * row * 2.5 + 1), fill=0)
            bird(g, x + row * 4, y + side * row * 2.5, lt + i * 0.3, s=0.8, flap=7)

    def fish(self, g: Gfx, t: float):
        ev = every(t, 67.0, 2.5, 41.0)
        if not ev:
            return
        k, lt = ev
        x0 = MX0 + (rand(k, 6) - 0.5) * 24
        if lt < 0.7:
            p = lt / 0.7
            x = x0 + p * 6
            y = WATER + 10 - math.sin(p * math.pi) * 6
            g.d.line((x - 2, y + (1 - p) * 2, x + 2, y - (1 - p) * 2 + p * 3), fill=1)
        r = max(0, lt - 0.6) * 6
        if r > 0:
            g.d.ellipse((x0 + 6 - r * 1.6, WATER + 10 - r * 0.4, x0 + 6 + r * 1.6, WATER + 10 + r * 0.4), outline=1)

    def poem(self, g: Gfx, t: float, k: float, idx: int):
        if k <= 0:
            return
        g.d.rectangle((113, 0, 127, WATER - 1), fill=0)
        vpoem(g, 115, 2, LINES[idx % len(LINES)], k)

    def name_tag(self, g: Gfx, k: float):
        if k <= 0:
            return
        s = self.pname[: int(round(k * len(self.pname)))]
        if s:
            from ..engine.gfx import text_width
            w = text_width(self.pname)
            g.d.rectangle((MX0 - w / 2 - 1, MY0 + R + 2, MX0 + w / 2 + 1, MY0 + R + 14), fill=0)
            ptext(g, MX0 - w / 2, MY0 + R + 3, self.pname, len(s))

    def mx(self, g: Gfx, t: float):
        mx_moon(g, self.age)
        if int(t * 1.7) % 7 == 0:
            g.mx_set(0, 0, True)
        if int(t * 1.1) % 9 == 3:
            g.mx_set(7, 1, True)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        my = lerp(WATER + R + 2, MY0, ease_out(span(t, 0, 2.4)))
        self.sky(g, t, my)
        g.blit(self.hills, 0, 0)
        self.water(g, t, my)
        self.pavilion(g, t)
        self.name_tag(g, span(t, 2.2, T))
        self.poem(g, t, span(t, 1.0, T), 0)
        self.mx(g, t)
        rows = int((1 - span(t, 0, 2.4)) * 8)
        if rows:  # 点阵上的月亮也从下面升起来
            g.mx[rows:, :] = g.mx[: 8 - rows, :].copy()
            g.mx[:rows, :] = False

    def hold(self, g: Gfx, t: float):
        self.sky(g, t)
        self.passing_cloud(g, t)
        self.geese(g, t)
        g.blit(self.hills, 0, 0)
        self.water(g, t, strength=1.0)
        self.fish(g, t)
        self.pavilion(g, t)
        if t < 20:
            k, idx = 1 - span(t, 17, 20), 0
            self.name_tag(g, k)
        else:
            ev = every(t, 120.0, 26.0, 80.0)
            k, idx = (span(ev[1], 0, 2.5) * (1 - span(ev[1], 23, 26)), ev[0] + 1) if ev else (0, 0)
            self.name_tag(g, k)
        self.poem(g, t, k, idx)
        self.mx(g, t)

    def exit(self, g: Gfx, t: float):
        """云幕从右边合拢，月光收尽"""
        T = self.T["exit"]
        self.hold(g, self.hold_t + t)   # 接着持续阶段最后的样子
        p = ease_in_out(t / T)
        front = lerp(132, -20, p)
        pts = [(front + math.sin(y * 0.3 + t * 3) * 3 + noise(y * 0.15, 4) * 5, y) for y in range(-2, 67, 3)]
        g.d.polygon(pts + [(140, 66), (140, -2)], fill=0)
        g.d.line(pts, fill=1)
        cols = int(round(p * 8))
        if cols:
            g.mx[:, 8 - cols:] = False
