"""邀月：李白《月下独酌》“花间一壶酒，独酌无相亲。举杯邀明月，对影成三人……我歌月徘徊，我舞影零乱”；
李白曾于齐州紫极宫受道箓，与道士吴筠、元丹丘交游。

月夜，左上一枝梅花探进来，右上一轮满月（环形山网点、一圈虚光晕）。小道士坐在石头上，脚边一只酒葫芦；
月光把他投成地上的影子（按画出来的人形实时投影：网点、压扁、往左下斜，动作同步）。
入场：月亮从右下升起，梅枝从左上探进来，小道士在石上弹出坐定，影子随之出现。
持续：每 12 秒举杯向月（杯里映出一点月光）→ 仰头饮尽 → 放下，隔一次在右下题一句诗；
      花瓣偶尔飘落，薄云慢慢掠过月面，星星闪。
      彩蛋每 48 秒：起身且歌且舞，长袖翻飞，月亮左右“徘徊”，地上影子乱舞——“我歌月徘徊”“我舞影零乱”。
退场：收圆。
点阵：一轮满月，云影掠过；跳舞时月亮在点阵上也左右挪。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x2_common import TUFT, Clock, iris, label, put_arm, rock, win

FLOOR = 52
DX, DF = 44, 46               # 小道士坐在石上
MOON = (104, 15)
TOAST = 12.0
DANCE = 48.0
LINES = ["举杯邀明月", "对影成三人", "花间一壶酒", "独酌无相亲"]


def _moon():
    """满月 21×21：圆盘 + 环形山（网点小块）+ 左下一道暗边"""
    p = Part(21, 21)
    p.shape("ellipse", (0, 0, 20, 20), fill=1)
    p.dither([(3, 7), (9, 5), (12, 9), (8, 12), (3, 11)], 0.5, 0)      # 月海（一大片）
    p.dither([(11, 13), (15, 12), (16, 16), (12, 17)], 0.5, 0)
    p.d.ellipse((14, 4, 16, 6), outline=0)                                # 一个小环形山
    p.d.arc((1, 1, 19, 19), 120, 190, fill=0)
    p.px(16, 3), p.px(17, 4)                                              # 亮边
    return p.sprite()


def _gourd():
    """酒葫芦 7×11：系绳、上小下大、高光"""
    p = Part(7, 11)
    p.shape("rectangle", (3, 0, 3, 1), fill=1)
    p.shape("ellipse", (1, 1, 5, 5), fill=1)
    p.shape("ellipse", (0, 4, 6, 10), fill=1)
    p.d.line((1, 5, 5, 5), fill=0)                 # 束腰的绳
    p.px(2, 2, 0), p.px(1, 7, 0)
    p.dither((4, 6, 6, 10), 0.5, 0)
    return p.sprite()


def _cloud():
    p = Part(26, 5)
    p.shape("ellipse", (0, 1, 14, 4), fill=1)
    p.shape("ellipse", (8, 0, 25, 4), fill=1)
    p.dither((0, 0, 26, 5), 0.5, 0)
    p.d.line((2, 4, 23, 4), fill=1)
    return p.sprite()


BLOSSOM = pix.frames("""
 #
#.#
 #
---
 ##
#..#
 ##
""")

PETAL = pix.frames("""
#
---
##
---
 #
#
""")


def _branch():
    """梅枝 46×22：从左上画外伸进来的老枝，折角分叉，枝头几朵梅花和花苞"""
    p = Part(48, 24)
    main = [(0, 3), (8, 6), (14, 5), (21, 10), (30, 11), (37, 16), (45, 17)]
    p.shape("line", main[:4], fill=1, width=2)
    p.shape("line", main[3:], fill=1)
    p.shape("line", ((14, 5), (19, 1), (24, 0)), fill=1)
    p.shape("line", ((21, 10), (22, 17), (26, 21)), fill=1)
    p.shape("line", ((30, 11), (34, 7)), fill=1)
    for x, y in ((5, 4), (17, 7)):
        p.px(x, y, 0)
    for x, y in ((23, 0), (24, 20), (33, 6), (44, 16), (12, 3), (28, 12)):
        p.shape("rectangle", (x, y, x + 1, y + 1), fill=1)
    return p.sprite()


_P: dict = {}


def prop(name):
    if not _P:
        _P.update(moon=_moon(), gourd=_gourd(), cloud=_cloud(), branch=_branch())
    return _P[name]


FLOWERS = [(10, 1), (20, 3), (27, 17), (35, 3), (40, 12), (47, 14)]


@register
class Moon(Rest):
    id = "x2.moon"
    name = "邀月"
    desc = "月下梅边，小道士坐石独酌，举杯邀明月、对影成三人（影子实时投在地上）；不时起舞，月徘徊、影零乱"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0
        self.clock = Clock()
        self.sh = Gfx()

    # ------------------------------------------------------------ 小道士（姿势函数）

    def pose(self, t: float):
        """→ (legs, x, y, arm 参数 (dx, dy, over), face, 拿杯, 跳舞)"""
        kd, _ = win(t, DANCE, 10.0, DANCE - 12.0)
        if kd is not None:     # 起身且歌且舞
            k = kd
            if k < 0.6:
                return "stand", DX, FLOOR, None, "normal", False, 0.0, k
            ph = (k - 0.6) / 0.55
            frame = int(ph) % 4
            arms = [(-3, -14, False), (11, -9, False), (9, 3, False), (4, -16, False)][frame]
            x = DX + 6 + math.sin(k * 1.4) * 8
            return "dance", x, FLOOR, arms, "happy" if frame % 2 else "sleep", False, 1.0, k
        k = t % TOAST
        if k < 1.0:            # 举杯向月
            q = ease_in_out(span(k, 0, 1.0))
            return "sit", DX, DF, (lerp(7, 13, q), lerp(6, -11, q), False), "normal", True, 0.0, k
        if k < 2.8:
            return "sit", DX, DF, (13, -11, False), "happy" if k > 1.6 else "normal", True, 0.0, k
        if k < 3.6:            # 拿到嘴边
            q = ease_in_out(span(k, 2.8, 3.6))
            return "sit", DX, DF, (lerp(13, 4, q), lerp(-11, -3, q), q > 0.5), "normal", True, 0.0, k
        if k < 5.2:            # 仰头饮尽
            return "sit", DX, DF, (4, -4, True), "sleep", True, 0.0, k
        q = ease_in_out(span(k, 5.2, 6.2))
        return "sit", DX, DF, (lerp(4, 7, q), lerp(-3, 6, q), q < 0.4), "normal", True, 0.0, k

    def draw_man(self, g: Gfx, t: float, legs, x, y, arm_p, face, cup):
        if arm_p is None:
            spr, at = "down", None
        else:
            spr, at = put_arm(arm_p[0], arm_p[1], "fist", over=arm_p[2])
        if legs == "dance":
            h = figure(g, x, y, t, legs="walk", arm=spr, arm_at=at, face=face)
        else:
            h = figure(g, x, y, t, legs=legs, arm=spr, arm_at=at, face=face)
        if cup:
            hx, hy = h["hand"]
            g.d.rectangle((hx - 1, hy - 3, hx + 2, hy - 1), fill=1)
            g.px(hx, hy - 2, 0)
            g.px(hx, hy)
        return h

    # ------------------------------------------------------------ 画面

    def scene(self, g: Gfx, t: float, enter: float = 1.0):
        dt = self.clock.dt(t)
        on = enter >= 1
        e3 = enter * self.T["enter"]
        legs, x, y, arm_p, face, cup, dancing, k = self.pose(t) if on else ("sit", DX, DF, (7, 6, False), "normal",
                                                                             True, 0.0, 0.0)
        # 星
        for i in range(10):
            sx, sy = int(rand(i, 7) * 124) + 2, int(rand(i, 8) * 34) + 2
            if (t * 0.8 + i * 0.37) % 2.5 > 0.2 and not (40 < sx < 60 and sy > 10):
                g.px(sx, sy)
        # 月（徘徊）
        rise = ease_out(span(e3, 0, 1.4)) if not on else 1.0
        mx_ = MOON[0] + (math.sin((k - 0.6) * 1.4) * 6 if dancing else 0)
        my = MOON[1] + (1 - rise) * 40
        for i in range(0, 32, 2):                                  # 光晕
            a = i / 32 * 2 * math.pi + t * 0.05
            g.px(mx_ + math.cos(a) * 14, my + math.sin(a) * 14)
        pix.blit(g, prop("moon"), mx_ - 10, my - 10)
        cx = (t * 2.2) % 220 - 40                                  # 薄云
        if 60 < cx < 140:
            pix.blit(g, prop("cloud"), cx, MOON[1] + 2 + math.sin(t * 0.2) * 2, outline=False)
        # 地面、石、葫芦
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        for i in range(14):                                         # 地上零星的草点
            gx, gy = int(rand(i, 21) * 126), FLOOR + 3 + int(rand(i, 22) * 9)
            g.px(gx, gy), g.px(gx + 1, gy - 1)
        for gx in (8, 70, 92, 118):
            pix.blit(g, TUFT[(gx // 3) % 3], gx, FLOOR - 2, outline=False)
        pix.blit(g, rock(22, 7), DX - 11, FLOOR - 6)
        pix.blit(g, prop("gourd"), DX + 14, FLOOR - 11)
        # 梅枝、花瓣
        bx = -48 + 48 * ease_out(span(e3, 0.3, 1.3)) if not on else 0
        pix.blit(g, prop("branch"), bx, 0)
        for i, (fx, fy) in enumerate(FLOWERS):
            pix.blit(g, BLOSSOM[i % 2], bx + fx - 1, fy - 1)
        for i in range(3):                                          # 飘落的花瓣
            pk = ((t + i * 5.3) % 16) / 6.0
            if pk < 1:
                fx, fy = FLOWERS[(i * 2 + int((t + i * 5.3) // 16)) % len(FLOWERS)]
                px_ = bx + fx + pk * 14 + math.sin(pk * 9 + i) * 3
                py_ = fy + pk * (FLOOR - fy - 2)
                pix.blit(g, PETAL[int(pk * 6) % 3], px_, py_, outline=False)
        # 人与影
        pop = ease_out_back(span(e3, 0.9, 1.5)) if not on else 1.0
        if pop > 0.05:
            yy = y + (1 - pop) * 8
            self.shadow(g, t, legs, x, yy, arm_p, face, cup, span(e3, 1.2, 2.2) if not on else 1.0)
            h = self.draw_man(g, t, legs, x, yy, arm_p, face, cup)
            if cup and arm_p and arm_p[1] < -9 and not dancing:   # 杯中映月
                hx, hy = h["hand"]
                if int(t * 6) % 2:
                    g.px(hx + 1, hy - 5), g.px(hx, hy - 6), g.px(hx + 2, hy - 6), g.px(hx + 1, hy - 7)
        # 字（右下，地面上）
        if on:
            if dancing:
                if 1.0 < k < 9.6:
                    label(g, 126, FLOOR - 1, "我歌月徘徊" if k < 5.3 else "我舞影零乱", align="right")
            else:
                n = int(t // TOAST)
                kk = t % TOAST
                if n % 2 == 1 and 5.4 < kk < 11.5:
                    label(g, 126, FLOOR - 1, LINES[(n // 2) % len(LINES)], align="right")
        return dancing, mx_

    def shadow(self, g: Gfx, t, legs, x, y, arm_p, face, cup, a: float):
        """月在右上：影子往左下投——把人形画到暂存画布，上下翻转、压扁、斜切，铺成网点"""
        if a <= 0:
            return
        s = self.sh
        s.clear()
        self.draw_man(s, t, legs, x, y, arm_p, face, cup)
        m = s.array()
        y0 = max(0, int(y) - 40)
        sub = m[y0:int(y) + 1]
        if not sub.any():
            return
        rows = sub[::-1][::2]                       # 翻转 + 压扁一半
        out = np.zeros_like(m)
        for i, row in enumerate(rows):
            yy = FLOOR + 1 + i
            if yy >= 64:
                break
            shift = -int(i * 2.2) - 3
            if shift < 0:
                out[yy, :shift] = row[-shift:]
        if a < 1:
            out &= (np.arange(128)[None, :] % 4) < int(a * 4 + 1)
        pat = (np.add.outer(np.arange(64), np.arange(128)) % 2 == 0)
        img = g.array()
        img[out] = False
        img[out & pat] = True
        g.put(img)

    def mx(self, g: Gfx, t: float, dancing: bool, mxx: float):
        off = int(round((mxx - MOON[0]) / 4)) if dancing else 0
        for yy in range(8):
            for xx in range(8):
                if (xx - 3.5 - off) ** 2 + (yy - 3.5) ** 2 < 11.5:
                    g.mx_set(xx, yy)
        g.mx_set(2 + off, 2, False), g.mx_set(5 + off, 4, False)
        cx = (t * 2.2) % 220 - 40
        if 60 < cx < 140:                           # 云影掠过
            c = int((cx - 60) / 10)
            for xx in range(c - 2, c + 1):
                g.mx_set(xx, 4, False), g.mx_set(xx + 1, 5, False)

    def enter(self, g: Gfx, t: float):
        self.scene(g, t, min(t / self.T["enter"], 0.999))
        self.mx(g, t, False, MOON[0])
        if t < 1.0:
            g.mx[: int(8 - t * 8)] = False

    def hold(self, g: Gfx, t: float):
        self.ht = t
        d, mxx = self.scene(g, t)
        self.mx(g, t, d, mxx)

    def exit(self, g: Gfx, t: float):
        tt = self.ht + t
        d, mxx = self.scene(g, tt)
        self.mx(g, tt, d, mxx)
        iris(g, t / self.T["exit"], MOON[0], MOON[1] + 4)
