"""刘海戏金蟾：刘海提着一串铜钱逗三足金蟾。

依据：刘海蟾（刘操，号海蟾子），全真道奉为北五祖之一；民间传说他以钱串为饵，从井中钓出三足金蟾，
      “刘海戏金蟾，步步钓金钱”是明清以来常见的吉祥图样。（Liu Haichan，Wikipedia；UCSD 中国民间故事 279）
入场：刘海扛着竹竿从左边蹦跳进来，竿梢挂着一串铜钱；金蟾从右边一跳一跳地蹦到石头前坐好。
持续：刘海握竿轻晃，竿梢垂下的钱串（方孔铜钱）像钟摆一样摆，金蟾的眼珠跟着钱转，喉囊一鼓一鼓；
      身边一只小飞虫绕圈，金蟾不时伸舌头一卷，没卷着（舌头弹回）。
      每 30 秒：刘海把竿一挑，金蟾蓄力一跃咬住最下面的铜钱，被提着悠两下，松口落地弹一弹，钱串叮当闪光，
      上方写出“步步钓金钱”。
收场：金蟾一跳跳出画面，刘海收起钱串追过去。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Bake, art, mx_sprite

G = 62
TIP = (58, 6)            # 钓竿梢
CORD = 17                 # 竿梢到第一枚钱的绳长
TX = 66                  # 金蟾（贴图左端）
EV0, EV_P = 16.0, 30.0

LIUHAI = art("""
......#####......
....##.....##....
...#.........#...
..#.#.#.#.#.#.#..
..##.#.#.#.#.##..
..#...........#..
..#..##...##..#..
..#.#..#.#..#.#..
..#...........#..
...#...###...#...
....#.......#....
.....#######.....
......#...#......
...####...####...
..#...#...#...#..
.#....#...#....#.
.#.....#.#.....#.
.#......#......#.
..#############..
..#.....#.....#..
..#.....#.....#..
.#......#......#.
.#.....#.#.....#.
.#....#...#....#.
..#..#.....#..#..
..####.....####..
.##..#.....#..##.
.####.......####.
""")


def _toad() -> Sprite:
    """三足金蟾（侧前方，朝左）：宽 40，高 26。前面两条前腿，后面一条后腿"""
    b = Bake(40, 26)
    b.poly([(27, 12), (36, 10), (39, 18), (37, 25), (24, 25), (30, 21)], 0.0)   # 唯一的后腿（大腿 + 后脚）
    b.line([(24, 25), (19, 25)])
    b.line([(21, 24), (19, 23)])
    b.ellipse((5, 6, 36, 25), 0.25)                                         # 金色身子（抖动）
    b.ellipse((3, 2, 13, 11), 0.0)                                          # 鼓眼
    b.ellipse((13, 0, 23, 9), 0.0)
    b.line([(1, 14), (5, 17), (13, 18), (20, 16)])                         # 阔嘴
    b.poly([(1, 12), (6, 9), (14, 10), (20, 15), (13, 17), (5, 16), (1, 14)], 0.0, outline=False)
    b.line([(1, 12), (6, 9), (13, 9)])
    b.line([(1, 14), (5, 17), (13, 18), (20, 16)])
    for x, y in ((24, 9), (29, 12), (20, 12), (26, 16), (32, 17), (17, 19)):  # 疣
        b.ellipse((x - 1, y - 1, x + 1, y + 1), 1.0)
    b.poly([(8, 18), (11, 18), (8, 24), (2, 25), (4, 23)], 0.0)              # 前腿（近）
    b.line([(1, 25), (4, 25)])
    b.poly([(18, 19), (21, 19), (20, 25), (14, 25), (17, 23)], 0.0)          # 前腿（远）
    b.line([(13, 25), (16, 25)])
    return b.sprite()


TOAD = _toad()
COIN = Sprite("""
 .###.
 #...#
 #.#.#
 #...#
 .###.
""")
MX_COIN = """
..####..
.#....#.
#..##..#
#.#..#.#
#.#..#.#
#..##..#
.#....#.
..####..
"""
MX_TOAD = """
.##..##.
#..##..#
#.#..#.#
.######.
#.####.#
.######.
##.##.##
........
"""


@register
class LiuHaiToad(Rest):
    id = "x4.toad"
    name = "刘海戏金蟾"
    desc = "刘海晃着一串方孔铜钱，三足金蟾眼珠跟着转、伸舌头卷虫；每隔一阵一跃咬住铜钱被钓起来悠两下"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ncoin = self.rng.choice((4, 5))

    # ------------------------------------------------------------ 零件

    def liuhai(self, g: Gfx, x: float, t: float, lift: float = 0.0, hop: float = 0.0):
        """刘海（额前一排刘海、笑眯眯）双手握一根竹竿往右上挑：x 为贴图左端；lift 竿梢抬高；返回竿梢位置"""
        y = G - LIUHAI.h - hop
        sw = math.sin(t * 1.6) * 2
        tipx, tipy = TIP[0] + x - 4 + sw, TIP[1] - lift - hop
        butt = (x + 8, y + 22)
        g.d.line((butt[0], butt[1], tipx, tipy), fill=1)            # 竹竿
        for u in (0.3, 0.55, 0.8):                                    # 竹节
            px, py = lerp(butt[0], tipx, u), lerp(butt[1], tipy, u)
            g.px(px - 1, py)
        g.blit(LIUHAI, x, y)
        # 双臂握竿
        h1 = (lerp(butt[0], tipx, 0.12), lerp(butt[1], tipy, 0.12))
        h2 = (lerp(butt[0], tipx, 0.22), lerp(butt[1], tipy, 0.22))
        g.d.line((x + 3, y + 15, x + 5, y + 19, h1[0], h1[1]), fill=1)
        g.d.line((x + 13, y + 14, h2[0], h2[1]), fill=1)
        g.d.rectangle((h1[0] - 1, h1[1] - 1, h1[0] + 1, h1[1] + 1), fill=1)
        g.d.rectangle((h2[0] - 1, h2[1] - 1, h2[0] + 1, h2[1] + 1), fill=1)
        # 两只小髻随身子晃
        b = math.sin(t * 3) * 1
        g.d.ellipse((x + 3 + b, y - 3, x + 6 + b, y), fill=1)
        g.d.ellipse((x + 11 + b, y - 3, x + 14 + b, y), fill=1)
        return tipx, tipy

    def string(self, g: Gfx, hx: float, hy: float, ang: float, n: int, bite: tuple | None = None):
        """钱串：从手垂下的绳子 + n 枚方孔钱。bite=(x, y)：最下面那枚被金蟾咬住拉着"""
        dx, dy = math.sin(ang), math.cos(ang)
        ex, ey = hx + dx * (CORD + n * 4), hy + dy * (CORD + n * 4)
        if bite:
            ex, ey = bite
        g.d.line((hx, hy, ex, ey), fill=1)
        for i in range(n):
            u = (CORD + i * 4) / (CORD + n * 4)
            cx, cy = lerp(hx, ex, u), lerp(hy, ey, u)
            g.blit(COIN, cx - 2, cy - 2)
        return ex, ey

    def toad(self, g: Gfx, x: float, y: float, t: float, look: tuple, throat: float, tongue: tuple | None = None,
             squash: float = 0.0):
        """金蟾：(x, y) 贴图左上角；look=(lx, ly) 眼珠看向的点；throat 喉囊鼓起 0..1"""
        g.blit(TOAD, x, y + squash)
        for ex, ey in ((x + 8, y + 6 + squash), (x + 18, y + 4 + squash)):
            a = math.atan2(look[1] - ey, look[0] - ex)
            g.d.rectangle((ex + math.cos(a) * 2 - 1, ey + math.sin(a) * 2 - 1, ex + math.cos(a) * 2,
                           ey + math.sin(a) * 2), fill=1)
        if throat > 0:   # 喉囊
            r = 2 + throat * 3
            g.d.ellipse((x + 8 - r, y + 19 - r * 0.6 + squash, x + 8 + r, y + 19 + r * 0.6 + squash), fill=0, outline=1)
        if tongue:       # 舌头：从嘴角弹出去
            mx_, my_ = x + 2, y + 14 + squash
            tx, ty = tongue
            g.d.line((mx_, my_, tx, ty), fill=1)
            g.d.ellipse((tx - 1, ty - 1, tx + 1, ty + 1), fill=1)

    def fly(self, t: float):
        a = t * 1.7
        return 60 + math.cos(a) * 14 + math.sin(a * 2.3) * 4, 34 + math.sin(a) * 8

    # ------------------------------------------------------------ 一帧

    def frame(self, g: Gfx, t: float, lx: float = 0.0, tx: float = TX, text: float = 1.0, show_fly: bool = True):
        # 地面与石头
        g.d.line((0, G, 127, G), fill=1)
        g.d.arc((tx + 22, G - 6, tx + 52, G + 6), 180, 360, fill=1)
        for i, x in enumerate((50, 58, 112, 120)):
            g.d.line((x, G, x - 1, G - 3), fill=1)
            g.d.line((x + 2, G, x + 3, G - 4), fill=1)
        k = (t - EV0) % EV_P if t >= EV0 else -1.0
        n = self.ncoin
        lift, hop, ang = 0.0, 0.0, math.sin(t * 1.6) * 0.35 - 0.15
        ty, squash, bite, tongue = G - 26, 0.0, None, None
        title = "刘海戏金蟾"
        sparkle = False
        if 0 <= k < 7.0:   # 一提、一跃、咬住悠两下、落地
            title = "步步钓金钱"
            if k < 1.0:                       # 刘海提起钱串，金蟾蹲下蓄力
                lift = ease_out(k) * 10
                squash = ease_out(k) * 2
                ang = lerp(ang, 0.0, ease_out(k))
            elif k < 1.6:                     # 跃起
                p = (k - 1.0) / 0.6
                lift = 10
                ang = 0.0
                ty = lerp(G - 26 + 2, TIP[1] - 10 + CORD + self.ncoin * 4 - 13, ease_out(p))
                tx = lerp(TX, TIP[0] - 6, ease_out(p))
            elif k < 4.4:                     # 咬住铜钱被提着悠
                q = (k - 1.6) / 2.8
                lift = 10 + math.sin(q * math.pi) * 4
                ang = math.sin(q * math.pi * 3) * 0.35 * (1 - q)
                sparkle = True
            elif k < 5.6:                     # 松口落地（弹两下）
                p = (k - 4.4) / 1.2
                lift = 10 * (1 - p)
                ang = math.sin(p * 9) * 0.3 * (1 - p)
                ty = lerp(TIP[1] - 10 + CORD + self.ncoin * 4 - 13, G - 26, ease_out_bounce(p))
                tx = lerp(TIP[0] - 6, TX, ease_out(p))
            else:
                squash = (1 - span(k, 5.6, 6.2)) * 2
        hx, hy = self.liuhai(g, lx, t, lift, hop)
        dx, dy = math.sin(ang), math.cos(ang)
        ex, ey = hx + dx * (CORD + n * 4), hy + dy * (CORD + n * 4)
        if 1.6 <= k < 4.4:                    # 金蟾咬住最下面的铜钱，挂在钱串下面
            ty = ey - 13
            txx = ex - 2
        else:
            txx = tx
        self.string(g, hx, hy, ang, n)
        if 1.6 <= k < 4.4:
            g.d.line((ex, ey, ex, ey + 2), fill=1)
        # 飞虫与舌头
        fk = (t + 5) % 11
        fx, fy = self.fly(t)
        if show_fly and k < 0 or k >= 7.0:
            if fk < 0.5 and show_fly:          # 舌头一卷（没卷着，虫子一躲）
                p = math.sin(fk / 0.5 * math.pi)
                tongue = (lerp(txx + 2, fx, p), lerp(ty + 14, fy, p))
                fx += p * 6
                fy -= p * 5
            if show_fly:
                g.d.line((fx - 1, fy - 1 - int(t * 12) % 2, fx + 1, fy - 1 - int(t * 12 + 1) % 2), fill=1)
                g.px(fx, fy)
        look = (ex, ey) if not (k < 0 or k >= 7.0) or (t % 7 < 4) else (fx, fy)
        throat = max(0.0, math.sin(t * 2.4)) if (k < 0 or k >= 7.0) else 0.0
        self.toad(g, txx, ty, t, look, throat, tongue, squash)
        if sparkle:   # 钱串叮当闪光
            for i in range(6):
                if blink(t + i * 0.21, 0.5, 0.4):
                    a = rand(i, 4) * 2 * math.pi
                    g.px(ex + math.cos(a) * (6 + i), ey - 8 + math.sin(a) * (5 + i))
        if text > 0:
            s = title
            if title == "步步钓金钱":
                typewriter(g, 124, 1, s, k, cps=5, align="right")
            else:
                g.text(124, 1, s[:int(round(text * len(s)))], align="right")
        # 点阵：铜钱（转动）/ 金蟾
        if sparkle or (0 <= k < 7.0):
            mx_sprite(g, MX_COIN)
            g.mx_level = 3 if sparkle and blink(t, 0.3) else 1
        else:
            mx_sprite(g, MX_TOAD)
            if throat > 0.5:
                g.mx[6, 3] = g.mx[6, 4] = True
                g.mx[7, 2:6] = True
        return k

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        lx = lerp(-30, 0, ease_out(span(t, 0, 1.6)))
        # 金蟾一跳一跳进来：三跳
        p = span(t, 0.6, 2.8)
        hops = 3
        seg = min(hops - 1, int(p * hops))
        u = p * hops - seg
        x0 = lerp(130, TX, seg / hops)
        x1 = lerp(130, TX, (seg + 1) / hops)
        tx = lerp(x0, x1, u) if p < 1 else TX
        g.d.line((0, G, 127, G), fill=1)
        g.d.arc((TX + 22, G - 6, TX + 52, G + 6), 180, 360, fill=1)
        hx, hy = self.liuhai(g, lx, t, 0, abs(math.sin(t * 6)) * 3 * (1 - span(t, 1.2, 1.6)))
        self.string(g, hx, hy, math.sin(t * 1.6) * 0.35 - 0.15, self.ncoin)
        hop_h = math.sin(u * math.pi) * 10 if p < 1 else 0
        self.toad(g, tx, G - 26 - hop_h, t, (hx, hy + 30), 0.0)
        g.text(124, 1, "刘海戏金蟾"[:int(span(t, 1.5, T) * 5 + 0.5)], align="right")
        mx_sprite(g, MX_TOAD)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        p = span(t, 0, T)
        # 金蟾跳走（往右两跳），刘海追过去
        u = (p * 2) % 1
        tx = TX + ease_in(p) * 70
        hop = math.sin(u * math.pi) * 8
        g.d.line((0, G, 127, G), fill=1)
        g.d.arc((TX + 22, G - 6, TX + 52, G + 6), 180, 360, fill=1)
        lx = ease_in(span(t, 0.3, T)) * 80
        hx, hy = self.liuhai(g, lx, t0 + t, 0, abs(math.sin(t * 8)) * 2)
        self.string(g, hx, hy, math.sin((t0 + t) * 1.6) * 0.35 - 0.15 - p * 0.6, self.ncoin)
        self.toad(g, tx, G - 26 - hop, t0 + t, (tx + 40, G - 30), 0.0)
        mx_sprite(g, MX_TOAD, dx=round(p * 8))
        g.fade(1 - span(t, T * 0.6, T))
