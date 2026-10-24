"""推磨（像素风）：豆腐坊里一盘石磨架在木台上，磨杠横伸出去，小道士推着磨杠绕磨走圈（7 秒一圈）：
前半圈在磨前往左走，后半圈绕到磨后往右走——被磨挡住只露出上半身，位置略高（伪透视）。
上扇磨盘的竖纹随转动横移，磨眼里一把黄豆，豆浆从磨嘴一滴滴流进木桶，桶里浆面慢慢升高。
推满 8 圈（56 秒）桶满：松开磨杠，提着满桶走出右边，提个空桶回来放好，接着推。
彩蛋：约每 43 秒一只小老鼠从左边溜进来，闻一闻，叼走地上一粒掉落的豆子跑掉。
左侧竖写“周行而不殆”（《道德经》二十五章：独立而不改，周行而不殆）；相传豆腐始于淮南王刘安。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import Clock, cyc, event, fade_out, scroll, worker

FLOOR = 57
TEXT_X = 3
MX = 70                  # 磨的中心
L = 30                   # 磨杠长
LAP = 7.0
NLAP = 8
SWAP = 12.0
BIG = NLAP * LAP + SWAP
BAR_Y = 35

STAND = Sprite("""
######################################
#.##################################.#
#.#                                #.#
#.#                                #.#
#.#                                #.#
#.#                                #.#
#.#                                #.#
#.#                                #.#
###                                ###
""")

BUCKET = Sprite("""
 ###########
##.........##
#############
#.#.##.##.#.#
#############
#.#.##.##.#.#
#.#.##.##.#.#
#############
 ###########
""")

MOUSE = pix.frames("""
    ##
 ######.
#######
  # #
---
    ##
 ######.
#######
 #   #
""")


def bar_end(th: float):
    """磨杠头：屏幕 x、深度（正 = 在磨前）"""
    return MX + math.cos(th) * L, math.sin(th)


@register
class Mill(Rest):
    id = "x5.mill"
    name = "推磨"
    desc = "豆腐坊推石磨：推着磨杠绕磨一圈圈走，绕到磨后只露出上半身；豆浆一滴滴流进木桶，满了提出去换空桶"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()

    def stones(self, g: Gfx, rot: float, th: float, level: float):
        """木台、下扇、上扇（竖纹随转动横移）、磨眼里的豆、磨嘴"""
        pix.blit(g, STAND, MX - 19, FLOOR - 9)
        # 下扇：带一圈接浆的槽
        g.d.rectangle((MX - 19, FLOOR - 16, MX + 18, FLOOR - 10), fill=1)
        g.d.line((MX - 19, FLOOR - 13, MX + 18, FLOOR - 13), fill=0)
        for x in range(MX - 16, MX + 18, 7):
            g.d.line((x, FLOOR - 12, x, FLOOR - 11), fill=0)
        pix.checker(g, (MX + 11, FLOOR - 12, MX + 19, FLOOR - 9), 0.5, fill=0)
        # 磨嘴（朝前）
        g.d.polygon([(MX - 3, FLOOR - 11), (MX + 3, FLOOR - 11), (MX + 1, FLOOR - 7), (MX - 1, FLOOR - 7)], fill=1)
        g.px(MX, FLOOR - 9, 0)
        # 上扇
        y0, y1 = FLOOR - 26, FLOOR - 17
        g.d.rectangle((MX - 16, y0, MX + 15, y1), fill=1)
        g.d.ellipse((MX - 16, y0 - 4, MX + 15, y0 + 4), fill=1)
        g.d.ellipse((MX - 14, y0 - 3, MX + 13, y0 + 3), outline=0)
        g.d.ellipse((MX - 5, y0 - 2, MX + 4, y0 + 1), fill=0)          # 磨眼
        for j in range(3):  # 一把黄豆
            g.px(MX - 3 + j * 3, y0 - 1 + (j % 2))
        for j in range(10):  # 竖纹：随转动横移（圆柱的投影）
            a = rot + j * math.pi / 5
            if math.sin(a) > 0:
                x = MX - 0.5 + math.cos(a) * 15
                g.d.line((x, y0 + 4, x, y1 - 1), fill=0)
        pix.checker(g, (MX + 9, y0 + 3, MX + 16, y1 + 1), 0.5, fill=0)
        g.d.line((MX - 16, y1, MX + 15, y1), fill=0)

    def bar(self, g: Gfx, th: float):
        ex, depth = bar_end(th)
        px = MX + math.cos(th) * 15
        y = BAR_Y + depth * 3
        g.d.line((px, BAR_Y, ex, y), fill=1, width=2)
        g.d.rectangle((ex - 1, y - 1, ex + 1, y + 1), fill=1)

    def bucket(self, g: Gfx, x: float, y: float, level: float):
        pix.blit(g, BUCKET, x - 6, y - 9)
        if level > 0.05:  # 浆面
            g.d.line((x - 4, y - 8 + 0, x + 4, y - 8), fill=1)

    def room(self, g: Gfx, t: float):
        g.d.line((19, FLOOR, 127, FLOOR), fill=1)
        pix.checker(g, (19, FLOOR + 2, 128, 64), 0.125)
        # 墙上挂着的豆腐板、一串辣椒似的干葫芦
        g.d.line((19, 10, 127, 10), fill=1)
        for x in range(22, 128, 9):
            g.d.line((x, 7, x + 4, 7), fill=1)
        g.d.rectangle((104, 16, 122, 24), outline=1)
        g.d.line((106, 20, 120, 20), fill=1)
        g.d.ellipse((26, 14, 40, 26), outline=1)   # 墙上挂的豆腐箩
        g.d.ellipse((28, 16, 38, 24), outline=1)
        for x in range(30, 38, 2):
            g.d.line((x, 17, x, 23), fill=1)
        g.d.line((33, 11, 33, 14), fill=1)

    # ------------------------------------------------ 主循环

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        self.clock.tick(t)
        n, k = cyc(t, BIG)
        self.room(g, t)
        pushing = k < NLAP * LAP
        th = 2 * math.pi * (k / LAP) if pushing else 0.0
        rot = th
        level = min(k / (NLAP * LAP), 1.0) if pushing else 1.0
        # 小道士的位置
        if pushing:
            ex, depth = bar_end(th)
            x = ex + math.sin(th) * 9
            behind = depth < -0.15
            flip = math.sin(th + 0.25) > 0
            feet = FLOOR - round(max(0.0, -depth) * 8)
            hand = (ex, BAR_Y + depth * 3)
            legs, carry, bx, by = "walk", False, MX, FLOOR
        else:
            x, flip, behind, feet, hand, legs, carry, bx, by, level = self.swap(k - NLAP * LAP)
        bucket_drawn = False

        def draw_man():
            def tool(gg, h1, h2):
                if carry and h1:
                    self.bucket(gg, h1[0] + (-2 if flip else 2), h1[1] + 10, level)
            worker(g, x, feet, t, hand=hand, legs=legs, flip=flip, tool=tool, fist=pushing)

        if pushing and behind:
            self.bar(g, th)
            draw_man()
        self.stones(g, rot, th, level)
        if not (pushing and behind):
            self.bar(g, th)
        if bx is not None:
            self.bucket(g, bx, by, level)
            bucket_drawn = True
        if pushing:  # 豆浆一滴滴流进桶
            for j in range(2):
                q = (t * 1.4 + j * 0.5) % 1
                g.px(MX, FLOOR - 7 + q * 3)
        if not (pushing and behind):
            draw_man()
        mouse = event(t, 43.0, 7.0, self.seed * 3 + 1)
        if mouse:
            self.mouse(g, mouse[1])
        elif int(t / BIG) % 1 == 0:
            g.px(40, FLOOR - 1)  # 地上一粒掉落的豆子
        self.matrix(g, th, t)
        scroll(g, TEXT_X, "周行而不殆", y=2, k=text_k, side="left")

    def swap(self, k: float):
        """桶满了：松杠 → 走到桶前提起来 → 走出右边 → 提空桶回来放好 → 回到杠头"""
        ex = MX + L
        if k < 1.5:
            q = ease_in_out(k / 1.5)
            return lerp(ex, MX + 12, q), True, False, FLOOR, None, "walk", False, MX, FLOOR, 1.0
        if k < 2.2:
            return MX + 12, True, False, FLOOR, (MX + 4, FLOOR - 10 + 3 * span(k, 1.5, 2.0)), "stand", False, MX, FLOOR, 1.0
        if k < 5.5:
            q = (k - 2.2) / 3.3
            x = lerp(MX + 12, 140, ease_in_out(q))
            return x, False, False, FLOOR, (x + 9, FLOOR - 13), "walk", True, None, None, 1.0
        if k < 9.0:
            q = (k - 5.5) / 3.5
            x = lerp(140, MX + 12, ease_out(q))
            if q < 1:
                return x, True, False, FLOOR, (x - 9, FLOOR - 13), "walk", True, None, None, 0.0
        if k < 10.0:
            return MX + 12, True, False, FLOOR, (MX + 4, FLOOR - 7), "stand", False, MX, FLOOR, 0.0
        q = span(k, 10.0, 12.0)
        return lerp(MX + 12, ex, ease_in_out(q)), False, False, FLOOR, (lerp(MX + 12, ex, q) + 2, BAR_Y), \
            "walk" if q < 1 else "stand", False, MX, FLOOR, 0.0

    def mouse(self, g: Gfx, q: float):
        bean = (40, FLOOR - 1)
        if q < 2.0:
            x = lerp(14, bean[0] - 8, ease_out(q / 2.0))
            pix.blit(g, pix.anim(MOUSE, q, 10), x, FLOOR - 4)
            g.px(*bean)
        elif q < 4.0:  # 闻一闻
            sniff = int(q * 8) % 2
            pix.blit(g, MOUSE[0], bean[0] - 8 + sniff, FLOOR - 4)
            g.px(*bean)
        else:  # 叼着豆子跑掉
            x = bean[0] - 8 - (q - 4.0) * 30
            pix.blit(g, pix.anim(MOUSE, q, 14), x, FLOOR - 4, flip=True)
            g.px(x - 1, FLOOR - 2)

    def matrix(self, g: Gfx, th: float, t: float):
        """点阵：俯看石磨——一圈磨盘、磨眼，磨杠随转动绕圈"""
        for a in range(0, 360, 30):
            r = math.radians(a)
            g.mx_set(round(3.5 + math.cos(r) * 2.5), round(3.5 + math.sin(r) * 2.5))
        g.mx_set(3, 3), g.mx_set(4, 4)
        for d in (3.0, 3.6):
            g.mx_set(round(3.5 + math.cos(th) * d), round(3.5 + math.sin(th) * d))

    def enter(self, g: Gfx, t: float):
        """从右边走过来，握住磨杠"""
        self.clock.tick(t)
        self.room(g, t)
        self.stones(g, 0, 0, 0)
        self.bar(g, 0)
        self.bucket(g, MX, FLOOR, 0)
        x = lerp(140, MX + L, ease_out(span(t, 0, 2.4)))
        hand = (x - 9, FLOOR - 15) if t < 2.4 else (MX + L, BAR_Y)
        worker(g, x, FLOOR, t, hand=hand, legs="walk" if t < 2.4 else "stand", flip=True, fist=t >= 2.4)
        self.matrix(g, 0, t)
        scroll(g, TEXT_X, "周行而不殆", y=2, k=span(t, 0.4, 2.6), side="left")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
