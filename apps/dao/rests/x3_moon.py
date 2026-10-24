"""望月：苏轼《水调歌头》“明月几时有”“千里共婵娟”；张九龄《望月怀远》“海上生明月”；李白《静夜思》“举头望明月”；
杜甫《月夜忆舍弟》“月是故乡明”；李白《月下独酌》“举杯邀明月”。

月相按真实日期算（朔望月 29.530588853 天，以 2000-01-06 18:14 UTC 的朔为起点）：盈月亮在右、亏月亮在左；
亮面上几块网点月海，暗面只留隐约的隔点轮廓；月外一圈虚线月晕。（本批唯一读系统时钟的地方。）
江边石矶上一座小亭（翘角攒尖、宝顶、两柱、栏杆），小道士在亭里凭栏坐着望月；
星星一闪一闪（偶尔亮成小十字），远山一抹，江上月影是一条碎银，越近越宽、随波闪动，亮度随月相。
小事件：举杯邀月（60s）；一缕云从右往左掠过月面（97s）；一行雁从月前飞过（151s）；月影里跳起一尾鱼（67s）；
        月相名常在月下；诗句每两分钟在江面浮现一句。
入场：月亮从远山后升起，月影一道道铺开。  退场：云从右边合拢，月光收尽。
点阵：今晚真实的月相（朔月时只留一圈虚线），角上偶有星闪。
"""
from __future__ import annotations

import math
import time

import numpy as np

from ..engine import pix
from ..engine.anim import clamp, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import BAYER4, Gfx, Sprite
from ..engine.scene import Rest, register
from .x3_lib import bake, bird, cloud, every, glints, mountain, plate, ridge, ring, star

SYNODIC = 29.530588853
NEW_MOON_JD = 2451550.1        # 2000-01-06 18:14 UTC 的朔
MX0, MY0, R = 98, 14, 10       # 月亮
WATER = 42
FLOOR = 53                     # 亭子地面
DX = 24
LINES = ["明月几时有", "海上生明月", "举头望明月", "千里共婵娟", "月是故乡明"]
PHASES = [(1.5, "朔月"), (6.4, "蛾眉月"), (8.9, "上弦月"), (13.8, "盈凸月"), (15.8, "望月"), (20.8, "亏凸月"),
          (23.4, "下弦月"), (28.0, "残月"), (99, "朔月")]


def moon_age(now: float | None = None) -> float:
    jd = (now if now is not None else time.time()) / 86400 + 2440587.5
    return (jd - NEW_MOON_JD) % SYNODIC


def phase_name(age: float) -> str:
    for lim, name in PHASES:
        if age < lim:
            return name
    return "朔月"


def illum(age: float) -> float:
    return (1 - math.cos(2 * math.pi * age / SYNODIC)) / 2


def moon_sprite(age: float, r: int) -> Sprite:
    """月亮：亮面实白 + 几块规则网点的月海；暗面不透明（挡星），只有一圈隔点轮廓"""
    n = 2 * r + 3
    c = n / 2 - 0.5
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = xs - c, ys - c
    inside = dx * dx + dy * dy <= r * r + 0.5
    w = np.sqrt(np.clip(r * r - dy * dy, 0, None))
    k = math.cos(2 * math.pi * age / SYNODIC)
    lit = (dx >= k * w) if age < SYNODIC / 2 else (dx <= -k * w)
    lit &= inside
    mare = np.zeros_like(inside)
    for mx, my, mr in ((-0.38, -0.28, 0.24), (0.12, -0.38, 0.15), (0.34, -0.02, 0.17), (-0.5, 0.22, 0.14),
                       (0.05, 0.42, 0.11), (0.55, 0.3, 0.1)):
        mare |= (dx / r - mx) ** 2 + (dy / r - my) ** 2 < mr * mr
    on = lit & ~(mare & ((xs + ys) % 2 == 0))
    edge = inside & ~((dx * dx + dy * dy) <= (r - 1) ** 2)
    on |= edge & ~lit & ((xs + ys) % 2 == 0)
    return Sprite(on=on, mask=inside)


def mx_moon(g: Gfx, age: float):
    k = math.cos(2 * math.pi * age / SYNODIC)
    for y in range(8):
        for x in range(8):
            dx, dy = x - 3.5, y - 3.5
            if dx * dx + dy * dy > 13.5:
                continue
            w = math.sqrt(max(13.5 - dy * dy, 0))
            if (dx >= k * w) if age < SYNODIC / 2 else (dx <= -k * w):
                g.mx[y, x] = True
    if not g.mx.any():
        for y in range(8):
            for x in range(8):
                if 9 < (x - 3.5) ** 2 + (y - 3.5) ** 2 <= 14 and (x + y) % 2:
                    g.mx[y, x] = True


def _pavilion():
    """小亭（侧视）：攒尖顶两角上翘、宝顶；两根柱；石矶台基"""
    roof = [(2, 17), (6, 14), (16, 9), (24, 3), (32, 9), (42, 14), (47, 17), (44, 18), (24, 13), (5, 18)]
    base = [(0, FLOOR), (48, FLOOR), (52, 57), (54, 64), (0, 64)]

    def draw(g):
        g.d.polygon(roof, fill=0, outline=1)
        g.d.line((6, 16, 24, 10, 42, 16), fill=1)            # 瓦垄
        for x in range(9, 41, 3):
            y = 10 + abs(x - 24) * 6 / 18
            g.d.line((x, y + 1, x, y + 3), fill=1)
        g.d.ellipse((22, 0, 26, 4), fill=1)                  # 宝顶
        g.px(24, 1, 0)
        g.px(1, 16), g.px(48, 16)                            # 翘角
        g.d.line((5, 19, 43, 19), fill=1)                   # 额枋
        for x in range(8, 41, 4):
            g.px(x, 20)
        for x in (6, 41):                                   # 柱
            g.d.rectangle((x, 19, x + 2, FLOOR), fill=1)
            g.d.line((x + 1, 21, x + 1, FLOOR - 1), fill=0)
        g.d.polygon(base, fill=0, outline=1)
        g.d.line((0, FLOOR + 1, 48, FLOOR + 1), fill=1)
        for x0, y0 in ((6, 58), (20, 60), (34, 57), (44, 61)):
            g.d.line((x0, y0, x0 + 5, y0), fill=1)
        pix.checker(g, (46, FLOOR + 3, 54, 64), 0.25)

    return bake(draw, solid=lambda d: (d.polygon(roof, fill=1), d.polygon(base, fill=1)))


def _railing():
    def draw(g):
        g.d.rectangle((8, FLOOR - 9, 41, FLOOR - 8), fill=1)    # 扶手
        g.d.line((8, FLOOR - 3, 41, FLOOR - 3), fill=1)          # 下枋
        for x in range(10, 41, 5):                              # 望柱与花格
            g.d.line((x, FLOOR - 7, x, FLOOR - 1), fill=1)
            g.px(x + 2, FLOOR - 5), g.px(x + 3, FLOOR - 6), g.px(x + 3, FLOOR - 4)
    return bake(draw)


_C: dict = {}


def parts(age: float):
    key = round(age * 4)
    if key not in _C:
        far = mountain(ridge([(60, 33, 18), (86, 36, 16), (120, 31, 20)], 8, base=WATER + 4, rough=0.7,
                             round_top=True), lit=((0.25, 2),), shade=(), outline=1)
        p = Part(9, 15)  # 举杯的手：手臂斜上
        p.shape("polygon", [(0, 14), (3, 14), (7, 4), (5, 2)], fill=1)
        p.shape("polygon", [(2, 12), (5, 6), (5, 11), (3, 14)], fill=1)
        p.dither([(3, 12), (5, 9), (5, 11), (3, 14)], 0.5, 0)
        p.shape("rectangle", (5, 0, 7, 2), fill=1)
        arm = p.sprite()
        arm.hand = (6, 0)
        arm.over_head = False
        _C[key] = dict(moon=moon_sprite(age, R), far=far, pav=_pavilion(), rail=_railing(), arm=arm,
                       cloud=cloud(30, 7, 41, lumps=5), bank=[cloud(26, 12, 50 + i, lumps=3) for i in range(3)])
    return _C[key]


STARS = [(int(rand(i, 77) * 126) + 1, int(rand(i, 78) * 32) + 1) for i in range(34)]


@register
class MoonGaze(Rest):
    id = "x3.moon"
    name = "望月"
    desc = "江边小亭里小道士凭栏望月，月相按今晚真实的月龄画；星闪、月影碎银，举杯邀月，薄云掠月，雁过月前"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.age = moon_age()
        self.P = parts(self.age)
        self.pname = phase_name(self.age)
        self.lum = illum(self.age)

    def sky(self, g: Gfx, t: float, my: float = MY0):
        for i, (x, y) in enumerate(STARS):
            if (x - MX0) ** 2 + (y - MY0) ** 2 < (R + 6) ** 2 or x < 50 and y < 20:
                continue
            star(g, x, y, t, i, 7)
        if self.lum > 0.3:  # 月晕：一圈虚线
            r = R + 4
            for a in range(0, 360, 12):
                g.px(MX0 + math.cos(math.radians(a + t * 3)) * r, my + math.sin(math.radians(a + t * 3)) * r)
        pix.blit(g, self.P["moon"], MX0 - R - 1, my - R - 1, outline=False)

    def water(self, g: Gfx, t: float, my: float = MY0, strength: float = 1.0):
        g.d.rectangle((0, WATER, 127, 63), fill=0)
        g.d.line((50, WATER, 127, WATER), fill=1)
        glints(g, 50, 128, WATER + 3, 63, t, 3, n=10, speed=1.2, far=1, near=3, blink=0.55, rows=3)
        if my > WATER + 2:
            return
        s = (0.3 + 0.7 * self.lum) * strength
        for i, y in enumerate(range(WATER + 2, 64, 2)):  # 月影：碎银，越近越宽
            k = (y - WATER) / (64 - WATER)
            half = (2 + k * 9) * s
            for j in range(3):
                seg = rand(i * 7 + j + int(t * 2.5 + i * 0.3) * 13, 5)
                if seg < 0.35 + 0.4 * s:
                    x0 = MX0 + (rand(i * 11 + j + int(t * 2.5) * 3, 6) - 0.5) * half * 2
                    ln = 1 + int(seg * 4 * (0.4 + k))
                    g.d.line((x0 - ln / 2, y, x0 + ln / 2, y), fill=1)

    def events(self, g: Gfx, t: float):
        ev = every(t, 67, 3, 22)  # 鱼跃月影
        if ev:
            lt = ev[1]
            x0 = MX0 - 8
            if lt < 0.9:
                k = lt / 0.9
                x, y = x0 + k * 10, WATER + 8 - math.sin(k * math.pi) * 9
                g.d.line((x - 2, y + 1, x + 1, y - 1), fill=1)
                g.px(x + 2, y - 1)
                g.px(x - 3, y + 2)
            ring(g, x0, WATER + 8, span(lt, 0, 1.2), rmax=5, flat=0.3)
            ring(g, x0 + 10, WATER + 8, span(lt, 0.9, 2.6), rmax=6, flat=0.3)
        ev = every(t, 151, 10, 80)  # 一行雁
        if ev:
            k = ev[1] / 10
            for j, (ox, oy) in enumerate(((0, 0), (6, 3), (12, 6), (6, -3), (12, -6))):
                bird(g, lerp(140, -20, k) + ox, 13 + oy + math.sin(k * 6) * 1, ev[1], fps=5, flip=True, ph=j * 0.3)

    def passing_cloud(self, g: Gfx, t: float):
        ev = every(t, 97, 16, 40)
        if ev:
            k = ev[1] / 16
            pix.blit(g, self.P["cloud"], lerp(132, -34, k), MY0 - 2 + math.sin(k * 3) * 2)

    def figure(self, g: Gfx, t: float):
        ev = every(t, 60, 6, 30)
        if ev and 0.5 < ev[1] < 5.5:
            h = figure(g, DX, FLOOR, t, legs="sit", arm=self.P["arm"], arm_at=(1, -31), face="happy" if ev[1] > 2 else "normal")
            hx, hy = h["hand"]
            g.d.rectangle((hx - 1, hy - 3, hx + 1, hy - 1), fill=1)
            g.px(hx, hy - 2, 0)
            if 2 < ev[1] < 4:
                for a in range(4):
                    if int(t * 6 + a) % 2:
                        g.px(hx + 3 + a, hy - 4 - a)
        else:
            ph = t % 22
            daoshi(g, DX, FLOOR, "meditate" if 13 < ph < 18 else "sit", t)

    def labels(self, g: Gfx, t: float):
        ev = every(t, 120, 12, 50)
        if ev:
            plate(g, 88, 50, LINES[(ev[0] + self.seed) % len(LINES)], align="center")
        else:
            plate(g, MX0, MY0 + R + 5, self.pname, size=8, align="center", frame=False)

    def scene(self, g: Gfx, t: float, my: float = MY0, strength: float = 1.0):
        self.sky(g, t, my)
        self.events(g, t)
        self.passing_cloud(g, t)
        g.blit(self.P["far"], 0, 0)
        self.water(g, t, my, strength)
        pix.blit(g, self.P["pav"], 0, 0)
        self.figure(g, t)
        g.blit(self.P["rail"], 0, 0)

    def mx(self, g: Gfx, t: float):
        mx_moon(g, self.age)
        if (t % 7) < 0.4:
            g.mx[0, 0] = True

    def hold(self, g: Gfx, t: float):
        self.scene(g, t)
        self.labels(g, t)
        self.mx(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        k = ease_out(span(t, 0, 2.4))
        my = lerp(WATER + 8, MY0, k)
        self.scene(g, t - T, my, strength=span(t, 1.2, T))
        g.fade(span(t, 0, 0.7))
        if t > 2.2:
            plate(g, MX0, MY0 + R + 5, self.pname, size=8, align="center", frame=False)
        mx_moon(g, self.age)
        rows = int(k * 8)
        g.mx[: 8 - rows] = False
        if rows < 8:
            g.mx[:] = np.roll(g.mx, 8 - rows, axis=0) & (np.arange(8)[:, None] >= 8 - rows)

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        k = ease_in_out(span(t, 0, self.T["exit"]))
        self.scene(g, tt, strength=1 - k)
        x = lerp(130, -20, k)  # 云从右边合拢
        g.d.rectangle((x + 10, 0, 127, 63), fill=0)
        for j in range(5):
            spr = self.P["bank"][j % 3]
            pix.blit(g, spr, x + (j % 2) * 6, -4 + j * 13)
        self.mx(g, tt)
        g.mx[:, max(0, 8 - int(k * 9)):] = False
