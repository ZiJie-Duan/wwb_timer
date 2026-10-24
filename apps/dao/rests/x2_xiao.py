"""吹箫引凤：刘向《列仙传·萧史》。

“萧史者，秦穆公时人也，善吹箫，能致孔雀、白鹤于庭。穆公有女字弄玉，好之，公遂以女妻焉。
日教弄玉作凤鸣，居数年，吹似凤声，凤凰来止其屋。公为作凤台，夫妇止其上，不下数年。一旦，皆随凤凰飞去。”

入场：凤台（飞檐、立柱、栏杆）从右边移入，云从左边飘来，吹箫人显形，第一道箫声荡开。
持续：箫声一圈圈向左荡开，指头在箫孔上起落；云慢慢飘。
      每 45 秒：一只凤凰拖着长尾从左边飞来，绕一圈，落在栏杆头上（“吹似凤声”“凤凰来止”），
      歇一会儿、点点头，再展翅飞走。两次凤凰之间，远处偶尔飞过一只白鹤（“能致孔雀白鹤于庭”）。
退场：画面收拢成一个圆。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import cloud, typewriter, xiangyun
from ..engine.gfx import BAYER, Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import iris, win

DECK = 57            # 台面
RAIL = 49            # 栏杆扶手
PX, PY = 94, DECK    # 吹箫人脚下
PERCH = (63, RAIL - 2)
EV_P = 45.0

PLAYER = Sprite("""
        .####.
       .######.
        .####.
       .######.
       #......#.
      #.......#
      #..#....#
       #......#
       .#....#.
        .#..#.
      .##....##.
     #..........#
    #....#.......#
    #...#.#......#
    #..#...#.....#
    #..#....#....#
    #...#........#
    #....#.......#
    #............#
    ##############
    #............#
    #............#
    #............#
     #..........#
     #..........#
     #..........#
     #..........#
    #............#
    #............#
   #..............#
   #..............#
  #................#
  ##################
""")


def pavilion(g: Gfx, dx: float = 0.0):
    """凤台：飞檐（瓦垄）、立柱、台面、栏杆"""
    d = g.d
    roof = [(64 + dx, 0), (128 + dx, 0), (128 + dx, 9), (76 + dx, 9), (68 + dx, 5), (62 + dx, 3)]
    g.shade_poly(roof, 0.35)
    for x in range(76, 128, 5):  # 瓦垄
        d.line((x + dx, 1, x + dx, 8), fill=1)
    d.line((70 + dx, 10, 128 + dx, 10), fill=1)
    d.line((62 + dx, 3, 60 + dx, 0), fill=1)  # 檐角上翘
    d.rectangle((120 + dx, 11, 123 + dx, DECK), fill=0, outline=1)  # 柱
    d.line((60 + dx, DECK, 128 + dx, DECK), fill=1)
    d.rectangle((60 + dx, DECK + 1, 128 + dx, DECK + 5), fill=0, outline=1)
    for x in range(63, 128, 6):  # 台基砖纹
        d.line((x + dx, DECK + 2, x + dx, DECK + 4), fill=1)


def railing(g: Gfx, dx: float = 0.0):
    d = g.d
    d.line((61 + dx, RAIL, 128 + dx, RAIL), fill=1, width=2)
    d.line((61 + dx, RAIL + 5, 128 + dx, RAIL + 5), fill=1)
    for x in range(63, 128, 11):  # 望柱
        d.rectangle((x - 1 + dx, RAIL - 2, x + 1 + dx, DECK - 1), fill=0, outline=1)
        d.rectangle((x + dx, RAIL - 3, x + dx, RAIL - 3), fill=1)
    for x in range(66, 128, 11):  # 栏板花格
        d.line((x + dx, RAIL + 5, x + 3 + dx, DECK - 1), fill=1)
        d.line((x + 6 + dx, RAIL + 5, x + 3 + dx, DECK - 1), fill=1)


def phoenix(g: Gfx, x: float, y: float, t: float, d: int = 1, flap: float = 1.0, perched: bool = False):
    """凤凰：冠羽、尖喙、扇动的翅、三根带“眼”的长尾羽。d=1 朝右，-1 朝左"""
    # 尾羽：在身后飘
    for j in range(3):
        pts = []
        for i in range(9):
            k = i / 8
            wave = math.sin(t * 4 + k * 4 + j) * (1.5 + k * 2) * (0.4 if perched else 1)
            tx = x - d * (5 + k * (18 - j * 3))
            ty = y + 1 + (j - 1) * k * 4 + wave + (k * k * 10 if perched else 0)
            pts.append((tx, ty))
        g.d.line(pts, fill=1)
        ex, ey = pts[-1]
        g.d.ellipse((ex - 1.5, ey - 1.5, ex + 1.5, ey + 1.5), fill=0, outline=1)
    # 身
    g.d.ellipse((x - 5, y - 2, x + 4, y + 3), fill=1)
    # 颈、头、冠、喙
    hx, hy = x + d * 6, y - 4
    g.d.line((x + d * 3, y, hx, hy), fill=1, width=2)
    g.d.ellipse((hx - 2, hy - 2, hx + 2, hy + 2), fill=1)
    g.px(hx + d, hy - 1, 0)
    g.d.line((hx + d * 2, hy, hx + d * 5, hy + 1), fill=1)
    for c in range(3):
        g.px(hx - d * c, hy - 3 - (c % 2))
    # 翅
    if perched:
        g.d.polygon([(x - d * 4, y - 1), (x + d * 3, y - 2), (x - d * 9, y + 4)], fill=0, outline=1)
    else:
        up = math.sin(flap)
        tip = (x - d * 4, y - 2 - up * 10)
        g.d.polygon([(x - d * 3, y - 1), (x + d * 3, y - 1), tip], fill=0, outline=1)
        g.d.line((x - d * 1, y - 1, tip[0] + d * 2, tip[1] + 3), fill=1)


def crane(g: Gfx, x: float, y: float, t: float):
    """远处的白鹤：长颈伸直，腿拖在后，翅膀缓缓扇"""
    up = math.sin(t * 5) * 3
    g.d.line((x - 6, y, x + 6, y), fill=1)
    g.d.line((x + 6, y, x + 9, y - 1), fill=1)
    g.d.line((x - 6, y, x - 11, y + 1), fill=1)
    g.d.line((x - 2, y, x - 5, y - up - 2), fill=1)
    g.d.line((x - 5, y - up - 2, x - 9, y - up), fill=1)


@register
class Xiao(Rest):
    id = "x2.xiao"
    name = "吹箫引凤"
    desc = "凤台上吹箫，箫声荡开；凤凰拖着长尾飞来落在栏杆上，歇一歇再飞走，远处偶有白鹤"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0
        self.off = self.rng.uniform(8, 14)

    # ------------------------------------------------------------ 零件

    def player(self, g: Gfx, t: float):
        x, y = PX - 8, PY - PLAYER.h
        sway = noise(t * 0.4, self.seed) - 0.5
        g.blit(PLAYER, x + round(sway), y)
        mx, my = x + 6 + round(sway), y + 7           # 嘴
        ex, ey = mx - 15, my + 19                       # 箫尾
        g.d.line((mx, my, ex, ey), fill=1, width=2)
        for i in range(5):  # 箫孔：随旋律开合
            k = 0.3 + i * 0.12
            hx, hy = lerp(mx, ex, k), lerp(my, ey, k)
            if noise(t * 3 + i * 2.1, self.seed) > 0.5:
                g.px(hx, hy, 0)
        for k in (0.45, 0.75):  # 两只手 + 袖
            hx, hy = lerp(mx, ex, k), lerp(my, ey, k)
            g.d.ellipse((hx - 1, hy - 1, hx + 2, hy + 1), fill=1)
            g.d.line((hx + 2, hy, x + 9, y + 14), fill=1, width=2)
        return ex, ey

    def sound(self, g: Gfx, t: float, ex: float, ey: float, amt: float = 1.0):
        """箫声：一道道向左荡开的弧，越远越淡"""
        for j in range(4):
            r = (t * 10 + j * 13) % 52
            if r < 3 or r > 52 * amt:
                continue
            n = int(r * 1.2)
            dens = 1 + int(r / 14)
            for i in range(0, n, dens):
                a = math.pi * (0.78 + 0.44 * i / max(n - 1, 1))
                g.px(ex + math.cos(a) * r, ey - 4 + math.sin(a) * r * 0.8)

    def clouds(self, g: Gfx, t: float, dx: float = 0.0):
        """台下云海：几朵卷云慢慢飘，底下一道云带"""
        for j, (y, s, sp) in enumerate(((44, 1.0, 1.2), (54, 1.3, 2.0), (30, 0.8, 0.7))):
            x = (j * 41 + t * sp + self.off * 3) % 100 - 16 + dx
            xiangyun(g, x, y, s, flip=j % 2 == 1)
        pts = [(x + dx, 61 + math.sin(x * 0.12 + t * 0.8) * 1.5) for x in range(0, 66, 3)]
        g.d.line(pts, fill=1)

    # ------------------------------------------------------------ 画面

    def frame(self, g: Gfx, t: float):
        k, n = win(t, EV_P, 21.0, offset=self.off)
        ck, _ = win(t, EV_P, 10.0, offset=self.off + 24.0)
        self.clouds(g, t)
        if ck is not None:  # 远处白鹤
            crane(g, lerp(-12, 70, ck / 10.0), 22 + math.sin(ck) * 2, t)
        pavilion(g)
        ex, ey = self.player(g, t)
        railing(g)
        self.sound(g, t, ex, ey, 0.6 if k is not None and 7 < k < 17 else 1.0)
        bird = None
        if k is not None:
            bird = self.phoenix_path(g, t, k)
        self.mx(g, t, bird)

    def phoenix_path(self, g: Gfx, t: float, k: float):
        if k < 6.0:  # 飞来：一个大弧，再绕一圈
            if k < 3.5:
                p = k / 3.5
                x, y = lerp(-20, 40, ease_out(p)), 30 - math.sin(p * math.pi) * 14
            else:
                a = (k - 3.5) / 2.5 * 2 * math.pi
                x, y = 40 + math.sin(a) * 14, 22 - math.cos(a) * 8 + 8
            if k > 5.0:
                p = ease_in_out(span(k, 5.0, 6.0))
                x, y = lerp(x, PERCH[0], p), lerp(y, PERCH[1] - 4, p)
            phoenix(g, x, y, t, 1, flap=t * 10)
            if 0.8 < k < 5.0:
                typewriter(g, 2, 2, "吹似凤声", k - 0.8, cps=3)
            return "fly"
        if k < 17.0:  # 落在栏杆头上，歇一歇，点头
            bob = 1 if (k % 3) < 0.25 else 0
            land = ease_out(span(k, 6.0, 6.5))
            phoenix(g, PERCH[0], PERCH[1] - 4 + bob + (1 - land) * -2, t, 1, flap=0, perched=land >= 1)
            if 7 < k < 16:
                typewriter(g, 2, 2, "凤凰来止", k - 7, cps=3)
            return "perch"
        p = (k - 17.0) / 4.0  # 展翅飞走（往左上）
        x, y = lerp(PERCH[0], -24, ease_in(p)), lerp(PERCH[1] - 4, -6, ease_in_out(p)) - math.sin(p * 3) * 4
        phoenix(g, x, y, t, -1, flap=t * 12)
        return "fly"

    def mx(self, g: Gfx, t: float, bird):
        if bird == "fly":  # 点阵：扇翅的凤
            g.mx_rows([0x00, 0x18, 0x3C, 0x7E, 0xDB, 0x18, 0x24, 0x42] if int(t * 6) % 2 else
                      [0x00, 0x00, 0x18, 0x99, 0xFF, 0x3C, 0x24, 0x42])
            return
        if bird == "perch":
            g.mx_rows([0x0C, 0x1E, 0x0C, 0x3C, 0x7C, 0x38, 0x6C, 0xC6])
            if int(t * 1.3) % 3 == 0:
                g.mx_level = 2
            return
        for j in range(3):  # 箫声：右下角往左上荡开的弧
            r = (t * 2.5 + j * 2.7) % 8
            for i in range(9):
                a = math.pi * (1.0 + 0.5 * i / 8)
                g.mx_set(round(7 + math.cos(a) * r), round(7 + math.sin(a) * r))
        g.mx_set(7, 7)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dx = (1 - ease_out(span(t, 0.0, 1.2))) * 70
        self.clouds(g, 0.0, dx=-(1 - ease_out(span(t, 0.6, 2.0))) * 90)
        pavilion(g, dx)
        if t > 1.4:
            before = g.array()
            ex, ey = self.player(g, 0.0)
            railing(g, dx)
            m = BAYER < int(span(t, 1.4, 2.4) * 16)
            g.put(np.where(m, g.array(), before))
            if t > 2.4:
                self.sound(g, (t - 2.4) * 0.3, ex, ey, span(t, 2.4, 3.0))
        else:
            railing(g, dx)
        g.mx_set(7, 7)
        if t > 2.4:
            self.mx(g, 0.0, None)

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.ht + t)
        iris(g, span(t, 0.0, self.T["exit"]), PX - 4, 36)
        if t > 0.8:
            g.mx[:] = False
