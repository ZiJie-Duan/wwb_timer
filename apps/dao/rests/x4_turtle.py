"""曳尾涂中：宁做泥里拖着尾巴的活龟，不做庙堂上供着的死龟壳。

依据：《庄子·秋水》“庄子钓于濮水，楚王使大夫二人往先焉……庄子持竿不顾，曰：‘吾闻楚有神龟，死已三千岁矣，
王巾笥而藏之庙堂之上。此龟者，宁其死为留骨而贵乎？宁其生而曳尾于涂中乎？’……‘往矣！吾将曳尾于涂中。’”
入场：左边濮水里冒出一串泡，乌龟探头爬上泥岸；画外伸进一根钓竿，浮漂落水。
持续：乌龟在泥滩上一步一步慢慢往右爬（约两分钟爬过一屏），尾巴在泥里拖出一道弯弯的痕、两边是脚印；
      爬出右边后又从水里爬上来。浮漂随水轻晃，偶尔一沉；芦苇摆。
      每 50 秒：乌龟头上冒出念头——庙堂上巾笥里供着的龟壳；它缩头、摇头，念头破掉，上方写出“宁其生而曳尾于涂中”。
收场：乌龟缩进壳里，钓竿收走，画面收拢。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_out, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Bake, mx_sprite, wave_line

GY = 50            # 泥滩地面
SHORE = 30         # 水与泥的分界
CRAWL = 1.25       # px/s
LOOP = 112.0       # 爬一趟的秒数（从水里爬上来，到爬出右边）
EV0, EV_P = 18.0, 50.0


def _shell() -> Sprite:
    """龟壳（侧面，朝右）：宽 30，高 14。椎盾一排、肋盾一排、缘盾一圈"""
    b = Bake(30, 14)
    cx, by = 15, 11

    def arc(rx, ry, a0=0, a1=180, n=16):
        return [(cx + math.cos(math.radians(a0 + (a1 - a0) * i / n)) * rx,
                 by - math.sin(math.radians(a0 + (a1 - a0) * i / n)) * ry) for i in range(n + 1)]

    outer = arc(14.5, 11)
    b.poly(outer + [(0, 13), (29, 13)], 0.0)
    inner = arc(9, 6.5, 20, 160)
    b.line(inner)
    b.line([(1, 11), (28, 11)])                                   # 缘盾上沿
    for x in range(3, 28, 4):                                     # 缘盾
        b.line([(x, 11), (x, 13)])
    for ang in (55, 90, 125):                                     # 椎盾分隔（上排）
        r = math.radians(ang)
        b.line([(cx + math.cos(r) * 9, by - math.sin(r) * 6.5), (cx + math.cos(r) * 14, by - math.sin(r) * 10.5)])
    for ang in (35, 72, 108, 145):                                # 肋盾分隔（下排，错开）
        r = math.radians(ang)
        b.line([(cx + math.cos(r) * 9.5, by - math.sin(r) * 6.5), (cx + math.cos(r) * 11.5, by)])
    for i, (x, y) in enumerate(((10, 6), (15, 4), (20, 6), (6, 9), (12, 8), (18, 8), (24, 9))):   # 盾片纹点
        b.point(x, y)
    return b.sprite()


def _mud() -> Sprite:
    """泥滩：岸坡 + 稀疏泥点"""
    b = Bake(128, 64 - GY + 8)
    pts = [(SHORE - 8, 64 - GY + 8), (SHORE, 8), (128, 8), (128, 64 - GY + 8)]
    b.poly(pts, 0.0, outline=False)
    b.line([(SHORE - 8, 64 - GY + 8), (SHORE, 8), (127, 8)])
    import random
    r = random.Random(7)
    for _ in range(70):
        x, y = r.randrange(SHORE, 128), r.randrange(11, 64 - GY + 8)
        if r.random() < 0.5:
            b.point(x, y)
        else:
            b.line([(x, y), (x + 1, y)])
    return b.sprite()


SHELL = _shell()
MUD = _mud()
SHRINE = Sprite("""
 #...................#
 .###################.
 ...###############...
 ....#...........#....
 ....#....###....#....
 ....#...#.#.#...#....
 ....#..#######..#....
 ....#.#########.#....
 ....#.#.......#.#....
 ....#.#########.#....
 ....#..#.....#..#....
 #####################
""")

MX_TURTLE = """
...##...
..####..
##.##.##
.######.
.##..##.
.######.
##.##.##
...##...
"""


def turtle(g: Gfx, x: float, t: float, walk: float = 1.0, head: float = 1.0, shake: float = 0.0, tail: bool = True,
           dy: float = 0):
    """侧面的乌龟：x = 龟壳左端，脚站在 GY。head 0 = 缩进壳里，1 = 伸出；shake 摇头"""
    x = round(x)
    gy = GY + round(dy)
    ph = t * 2.2
    bob = round(abs(math.sin(ph)) * walk * 0.8)
    sy = gy - 17 - bob
    # 腿（四条，近侧两条画粗）：交替前后
    for lx, p0, near in ((9, math.pi, 0), (25, 0.0, 0), (5, 0.0, 1), (21, math.pi, 1)):
        sw = math.sin(ph + p0) * 2 * walk
        lift = max(0.0, math.cos(ph + p0)) * 1.5 * walk
        fx, fy = x + lx + sw, gy - lift
        if near:   # 近侧的腿：粗短、带爪
            g.d.polygon([(x + lx - 2, sy + 11), (x + lx + 3, sy + 11), (fx + 2, fy - 1), (fx - 2, fy - 1)], fill=0,
                        outline=1)
            g.d.line((fx - 2, fy, fx + 3, fy), fill=1)
            g.px(fx + 3, fy - 1)
        else:
            g.d.line((x + lx, sy + 12, fx, fy), fill=1)
            g.d.line((fx, fy, fx + 2, fy), fill=1)
    # 尾巴：拖在泥里
    if tail:
        g.d.line((x + 1, sy + 11, x - 4, gy, x - 7, gy + 3), fill=1)
    # 头颈：从壳前伸出
    if head > 0:
        hx = x + 27 + head * 8 + shake * 2
        hy = sy + 6 - head * 2 + (abs(shake) * 1)
        g.d.polygon([(x + 25, sy + 6), (hx - 2, hy), (hx - 2, hy + 5), (x + 25, sy + 12)], fill=0, outline=1)
        g.d.ellipse((hx - 4, hy - 1, hx + 4, hy + 5), fill=0, outline=1)
        g.px(hx + 1, hy + 1)                      # 眼
        g.d.line((hx + 2, hy + 3, hx + 4, hy + 3), fill=1)   # 嘴
    g.blit(SHELL, x, sy)


@register
class Turtle(Rest):
    id = "x4.turtle"
    name = "曳尾涂中"
    desc = "乌龟在濮水泥滩上慢慢爬、拖着尾巴；不时想起庙堂里供着的龟壳，缩头摇头，宁其生而曳尾于涂中"
    T = {"enter": 3.2, "exit": 1.2}

    def setup(self):
        self.phase0 = self.rng.uniform(0, 30)

    # ------------------------------------------------------------ 布景

    def water(self, g: Gfx, t: float):
        wave_line(g, GY - 2, t, 0.6, 0, SHORE - 2, wl=9, speed=1.5)
        for i in range(3):
            x = (rand(i, 5) * 22 + t * 2) % 24
            g.d.line((x, GY + 4 + i * 4, x + 3, GY + 4 + i * 4), fill=1)

    def reeds(self, g: Gfx, t: float):
        for i, (x, h) in enumerate(((112, 20), (116, 26), (120, 18), (124, 23))):
            sw = math.sin(t * 0.7 + i * 1.3) * 2
            g.d.line((x, GY, x + sw * 0.5, GY - h * 0.5, x + sw, GY - h), fill=1)
            if i % 2:
                g.d.rectangle((x + sw - 1, GY - h - 4, x + sw, GY - h), fill=1)   # 蒲棒

    def rod(self, g: Gfx, t: float, a: float = 1.0):
        """庄子的钓竿（人在画外）：竿梢从左上伸进来，浮漂在水里"""
        tipx, tipy = lerp(-6, 16, a), lerp(-10, 3, a)
        g.d.line((-4, 14 + (1 - a) * 20, tipx, tipy), fill=1)
        k = (t + 7) % 37
        dip = 2 if k < 0.8 else 0
        fy = GY - 4 + math.sin(t * 1.4) * 0.6 + dip
        if a >= 1:
            g.d.line((tipx, tipy, 15, fy - 2), fill=1)
            g.d.rectangle((14, fy - 3, 16, fy), fill=1)
            if k < 2.0:
                r = k * 4
                g.d.arc((15 - r, fy - r * 0.3 + 1, 15 + r, fy + r * 0.3 + 1), 0, 360, fill=1)

    # ------------------------------------------------------------ 爬

    def pos(self, t: float):
        """返回 (x, 爬上岸了没, 本趟开始的 x)"""
        u = (t + self.phase0) % LOOP
        return SHORE - 36 + u * CRAWL, u

    def trail(self, g: Gfx, x: float):
        """尾巴拖出的痕 + 两边的脚印（从岸边到龟尾）"""
        x0 = SHORE + 2
        prev = None
        for xx in range(int(x0), int(x - 6), 2):
            y = GY + 3 + round(math.sin(xx * 0.35) * 1.2)
            if prev is not None:
                g.d.line((xx - 2, prev, xx, y), fill=1)
            prev = y
            if xx % 8 == 0:   # 脚印
                g.d.line((xx + 3, GY + 7, xx + 4, GY + 7), fill=1)
                g.d.line((xx + 7, GY + 1, xx + 8, GY + 1), fill=1)

    # ------------------------------------------------------------ 念头事件

    def event(self, g: Gfx, t: float, tx: float):
        """返回 (head, shake)"""
        if t < EV0:
            return 1.0, 0.0
        k = (t - EV0) % EV_P
        if k > 12:
            return 1.0, 0.0
        bx = clamp(tx + 10, 30, 90)
        if k < 5.5:   # 念头冒出来：三个小泡 + 云框里的庙堂巾笥
            n = min(3, int(k / 0.3))
            for i in range(n):
                g.d.ellipse((tx + 34 - i * 2 + i * 3, GY - 22 - i * 4, tx + 36 + i * 3, GY - 20 - i * 4 + i), outline=1)
            if k > 1.0:
                p = ease_out(span(k, 1.0, 1.6))
                w, h = 34 * p, 22 * p
                cx, cy = bx + 22, 14
                g.d.ellipse((cx - w / 2 - 3, cy - h / 2, cx + w / 2 + 3, cy + h / 2), fill=0, outline=1)
                if p >= 1:   # 庙堂之上，巾笥里供着神龟的壳
                    g.blit(SHRINE, cx - 10, cy - 6)
        elif k < 6.0:  # 念头破掉
            p = (k - 5.5) / 0.5
            cx, cy = bx + 22, 14
            for i in range(10):
                a = i / 10 * 2 * math.pi
                g.px(cx + math.cos(a) * (16 + p * 8), cy + math.sin(a) * (9 + p * 5))
        if k > 6.0:
            typewriter(g, 71, 0, "宁其生而曳尾于涂中", k - 6.0, cps=4, align="center")
        # 头：念头出来时缩一下，然后摇头
        if 1.6 < k < 3.2:
            return 1 - ease_out(span(k, 1.6, 2.0)) + ease_out(span(k, 2.6, 3.2)), 0.0
        if 3.4 < k < 5.6:
            return 1.0, math.sin((k - 3.4) * 9) * (1 - span(k, 5.0, 5.6))
        return 1.0, 0.0

    def draw_turtle(self, g: Gfx, x: float, t: float, walk: float, head: float, shake: float = 0.0, tail=True):
        """在水里时身子低、被水面遮住；爬上岸后正常"""
        sink = clamp((SHORE + 2 - (x + 28)) / 10) * 14
        turtle(g, x, t, walk, head, shake, tail, dy=sink)
        if sink > 0:  # 水面以下的部分盖掉，重画水
            g.d.polygon([(0, GY - 1), (SHORE - 1, GY - 1), (SHORE - 9, 64), (0, 64)], fill=0)
            g.d.line((SHORE, GY, SHORE - 8, 64), fill=1)
            self.water(g, t)

    def mx(self, g: Gfx, t: float, head: float, walk: float = 1.0):
        mx_sprite(g, MX_TURTLE)
        if head < 0.5:
            g.mx[0, 3] = g.mx[0, 4] = False
        if walk and int(t * 2.2 / math.pi) % 2:   # 腿交替
            g.mx[2, 0] = g.mx[6, 7] = False
            g.mx[2, 7] = g.mx[6, 0] = False
            g.mx_set(1, 1)
            g.mx_set(6, 7)

    # ------------------------------------------------------------ 阶段

    def scene(self, g: Gfx, t: float, x: float, u: float, walk: float = 1.0, head: float | None = None):
        self.water(g, t)
        g.blit(MUD, 0, GY - 8)
        self.reeds(g, t)
        self.rod(g, t)
        if x > SHORE:
            self.trail(g, x)

    def hold(self, g: Gfx, t: float):
        x, u = self.pos(t)
        self.scene(g, t, x, u)
        head, shake = self.event(g, t, x)
        thinking = t >= EV0 and (t - EV0) % EV_P < 6
        walk = 0.0 if thinking else 1.0
        self.draw_turtle(g, x, t, walk, head, shake)
        self.mx(g, t, head, walk)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        x, u = self.pos(0)
        self.water(g, t - T)
        g.blit(MUD, 0, GY - 8)
        self.reeds(g, t - T)
        self.rod(g, t - T, ease_out(span(t, 1.6, 2.8)))
        if x > SHORE:
            self.trail(g, x)
        # 乌龟：头从缩着慢慢伸出来，开始爬
        head = ease_out(span(t, 0.3, 1.6))
        self.draw_turtle(g, x, t - T, span(t, 1.6, T), head)
        for i in range(3):  # 水里冒泡
            k = (t * 1.5 + i * 0.33) % 1
            if t < 1.6:
                g.px(8 + i * 5, GY + 8 - k * 10)
        self.mx(g, t, head, 0)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        x, u = self.pos(t0)
        self.water(g, t0 + t)
        g.blit(MUD, 0, GY - 8)
        self.reeds(g, t0 + t)
        self.rod(g, t0 + t, 1 - ease_in(span(t, 0, 0.8)))
        if x > SHORE:
            self.trail(g, x)
        self.draw_turtle(g, x, t0, 0, 1 - ease_out(span(t, 0, 0.5)), tail=t < 0.5)
        self.mx(g, t, 0, 0)
        g.fade(1 - span(t, T * 0.5, T))
