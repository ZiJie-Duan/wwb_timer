"""观瀑：李白《望庐山瀑布》“日照香炉生紫烟，遥看瀑布挂前川。飞流直下三千尺，疑是银河落九天。”

两道黑色断崖夹着一条瀑布：远处香炉峰顶飘着几团像素烟；左崖顶一棵探身松；
瀑布是一道道往下冲的水纹（每一列速度、断点不同，逐帧滚动），崖口水头翻过来一道白弧；
潭底白沫翻滚、水珠抛物线四溅、水雾点点往上飘，潭面涟漪往两边荡开。
小道士坐在潭边石上看瀑布，呼吸眨眼，时而闭目。
小事件：一片落叶漂到崖口翻下去，在潭里打个转漂走（53s）；燕子穿过水雾（71s）；
        水雾里出一道三重的虹，从左到右画出来，小道士惊喜地举手一指（130s）；“飞流直下”竖题在左边（70s 一次）。
入场：崖口先渗水，水头坠下，砸进潭里溅起一圈水花。  退场：水断，最后一截水尾落进潭里，水雾散尽。
点阵：两边崖壁，中间水列往下冲，底部溅花。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_out, lerp, noise, rand, span
from ..engine.chars import daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bake, bird, cloud, every, glints, mountain, pine_pad, ridge, rock, ring, tri, vplate

FX0, FX1 = 70, 86      # 瀑布左右
LIP = 11               # 崖口
POOL = 51              # 潭面
DX = 21                # 小道士


def _cliffs():
    left = [(44, 64), (46, 40), (50, 30), (55, 20), (58, 14), (63, 10), (FX0 + 1, LIP), (FX0, 30), (FX0 + 1, 46),
            (FX0 - 2, POOL), (60, POOL), (52, 64)]
    right = [(FX1 - 1, LIP), (90, 6), (96, 2), (104, -1), (128, -1), (128, POOL + 2), (100, POOL), (FX1 + 2, POOL),
             (FX1, 40), (FX1 - 1, 24)]

    def draw(g):
        for pts in (left, right):
            g.d.polygon(pts, fill=0, outline=1)
        # 斧劈皴：短斜线
        for x, y in ((56, 28), (61, 38), (54, 44)):
            g.d.line((x, y, x + 2, y + 3, x + 1, y + 5), fill=1)
        for x, y in ((100, 8), (96, 24), (118, 18), (108, 34), (94, 40), (120, 42)):
            g.d.line((x, y, x - 2, y + 3, x - 1, y + 5), fill=1)
        # 受光面网点（左崖朝左上，右崖崖顶）
        for y in range(14, POOL):
            x0 = {14: 57, 20: 54, 30: 49}.get(y, None)
        for (xa, ya), (xb, yb) in zip(left[1:6], left[2:7]):   # 左崖受光边：一条 2 像素宽的网点带
            n = int(max(abs(xb - xa), abs(yb - ya)))
            for i in range(n):
                x = xa + (xb - xa) * i / n
                y = ya + (yb - ya) * i / n
                for d in (2, 3):
                    if (int(x) + d + int(y)) % 2 == 0:
                        g.px(x + d, y + 1)
        pix.checker(g, (106, 1, 128, 5), 0.25)
        # 苔点
        for x, y in ((57, 15), (60, 12), (93, 5), (98, 3), (110, 1)):
            g.px(x, y - 1)
        # 崖下靠水一侧的背光
        for y in range(LIP + 4, POOL):
            g.px(FX0 - 2, y) if y % 2 else None
            g.px(FX1 + 2, y) if y % 2 == 0 else None

    def solid(d):
        d.polygon(left, fill=1)
        d.polygon(right, fill=1)

    return bake(draw, solid=solid)


def _pine():
    """崖顶探身松：一段斜干伸向瀑布，三簇松盖"""
    def draw(g):
        g.d.line((58, 14, 62, 9, 68, 6, 74, 5), fill=1, width=2)
        g.d.line((63, 9, 61, 5), fill=1)
        for x, y in ((60, 11), (66, 8), (71, 6)):
            g.px(x, y + 1, 0)
    return bake(draw)


_C: dict = {}


def parts():
    if not _C:
        far = mountain(ridge([(34, 7, 16), (18, 18, 14), (4, 24, 10)], 11, base=44, rough=0.8, power=0.9, round_top=True),
                       lit=((0.5, 1), (0.25, 2)), shade=((0.125, 2),), outline=1)
        _C.update(cliffs=_cliffs(), pine=_pine(), far=far, rock=rock(30, 10, 3),
                  pads=[pine_pad(9, 1), pine_pad(11, 2), pine_pad(8, 3)], smoke=[cloud(9, 5, 31), cloud(12, 6, 32)])
    return _C


LEAF = pix.frames("""
 ##
###.
 ##
---
 #
###
.#
---
##
.##
 ##
---
 #.
###
 #
""")


@register
class FallsWatch(Rest):
    id = "x3.falls"
    name = "观瀑"
    desc = "两道断崖夹着瀑布，水纹往下冲、潭底白沫翻滚水珠四溅；小道士坐在潭边石上看，落叶翻下崖口、燕子穿雾、水雾里出虹"
    T = {"enter": 2.6, "exit": 1.3}

    def setup(self):
        self.P = parts()

    def water(self, g: Gfx, t: float, top: float = LIP, bottom: float = POOL, flow: float = 1.0):
        """瀑布：每列一条滚动的虚线（速度、断点各不同），两边稀、中间密"""
        if bottom <= top:
            return
        g.d.rectangle((FX0 + 1, top, FX1 - 1, bottom), fill=0)
        for c, x in enumerate(range(FX0 + 1, FX1)):
            edge = min(x - FX0, FX1 - x)
            per = 6 + int(rand(c, 3) * 6)
            on = (per - 2 if c % 2 == 0 else 1) if edge > 1 else 1
            sp = 46 + rand(c, 4) * 22
            off = int(t * sp + rand(c, 5) * per)
            for y in range(int(top), int(bottom)):
                if (y - off) % per < on:
                    g.px(x, y)
        # 崖口：水头翻过来一道白弧
        if top <= LIP + 1:
            g.d.line((FX0 + 1, LIP, FX1 - 1, LIP), fill=1)
            g.d.line((FX0 + 2, LIP - 1, FX1 - 2, LIP - 1), fill=1)
            for x in range(FX0 + 2, FX1 - 1, 3):
                g.px(x + int(t * 6) % 3, LIP + 1, 0)

    def pool(self, g: Gfx, t: float, power: float = 1.0):
        g.d.rectangle((40, POOL, 127, 63), fill=0)
        g.d.line((40, POOL, 127, POOL), fill=1)
        glints(g, 42, 127, POOL + 3, 63, t, 7, n=18, speed=0, far=2, near=5, blink=0.45)
        cx = (FX0 + FX1) / 2
        for i in range(4):  # 潭纹往两边荡开：一道道短弧线
            k = ((t * 0.45 + i / 4) % 1)
            for s in (-1, 1):
                x = cx + s * (10 + k * 34)
                y = POOL + 2 + k * 8
                if k < 0.9:
                    g.d.line((x - 2, y, x + 2, y), fill=1)
                    g.px(x - s * 3, y - 1)
        if power <= 0:
            return
        for i in range(9):  # 白沫：一团团鼓起
            x = FX0 - 2 + i * 2.3
            ph = t * 3 + i * 1.7
            r = (1.5 + 2.2 * noise(ph, i)) * power
            y = POOL - 1 - r * 0.6
            g.d.ellipse((x - r, y - r, x + r, y + r), fill=1 if i % 3 else 0, outline=1)
        for i in range(14):  # 水珠抛物线
            per = 0.9 + rand(i, 8) * 0.5
            k = ((t + rand(i, 9) * per) % per) / per
            vx = (rand(i + int((t + rand(i, 9) * per) / per) * 17, 10) - 0.5) * 34
            x = cx + vx * k
            y = POOL - 2 - (18 * k - 22 * k * k) * (0.6 + rand(i, 11)) * power
            if y < POOL:
                g.px(x, y)
        for i in range(16):  # 水雾往上飘
            k = ((t * 0.18 + rand(i, 12)) % 1)
            x = cx + (rand(i, 13) - 0.5) * 40 + math.sin(t * 0.7 + i) * 3
            y = POOL - 3 - k * 22
            if k < 0.8 * power and (i + int(t * 3)) % 4:
                g.px(x, y)

    def rainbow(self, g: Gfx, t: float):
        ev = every(t, 130, 14, 45)
        if not ev:
            return None
        lt = ev[1]
        draw_k = span(lt, 0, 3.0)
        gone = span(lt, 11, 14)
        cx, cy = (FX0 + FX1) / 2, POOL + 6
        for j, r in enumerate((24, 21, 18)):
            for a in range(190, 351, 2):
                k = (a - 190) / 160
                if k > draw_k or k < gone:
                    continue
                if j == 1 and a % 4:
                    continue
                g.px(cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r * 0.85)
        return lt

    def leaf(self, g: Gfx, t: float):
        ev = every(t, 53, 12, 15)
        if not ev:
            return
        lt = ev[1]
        if lt < 2:  # 沿崖口水面漂来
            x, y = lerp(FX0 + 2, FX0 + 7, lt / 2), LIP - 2
        elif lt < 3.2:  # 翻下去
            k = ease_in(span(lt, 2, 3.2))
            x, y = FX0 + 7 + math.sin(lt * 9) * 2, lerp(LIP, POOL - 3, k)
        else:  # 潭里打转漂走
            k = span(lt, 3.2, 12)
            a = lt * 3
            x = FX1 + 4 + k * 40 + math.cos(a) * 3 * (1 - k)
            y = POOL + 3 + k * 6 + math.sin(a) * 1.5 * (1 - k)
        g.blit(LEAF[int(lt * 8) % 4], x - 2, y - 1)

    def world(self, g: Gfx, t: float, top: float = LIP, bottom: float = POOL, power: float = 1.0):
        P = self.P
        g.blit(P["far"], 0, 0)
        for j, (x0, y0) in enumerate(((22, 0), (30, -3))):  # 香炉峰顶的烟
            k = ((t * 0.08 + j * 0.5) % 1)
            spr = P["smoke"][j]
            x = x0 + k * 14 + math.sin(t * 0.5 + j) * 1.5
            y = y0 + 4 - k * 6
            pix.blit(g, spr if k < 0.7 else _fade(spr, 1 - span(k, 0.7, 1)), x, y)
        g.blit(P["cliffs"], 0, 0)
        g.blit(P["pine"], 0, 0)
        sway = math.sin(t * 0.9) * 0.6
        for (x, y), pad in zip(((58, 7), (65, 4), (72, 2)), P["pads"]):
            pix.blit(g, pad, x - pad.w // 2 + sway, y)
        self.water(g, t, top, bottom)
        self.pool(g, t, power)
        lt = self.rainbow(g, t)
        sw = every(t, 71, 3.0, 30)
        if sw:  # 燕子穿过水雾
            k = sw[1] / 3
            bird(g, lerp(130, 30, k), POOL - 14 - math.sin(k * math.pi * 2) * 6, sw[1], fps=12, flip=True)
        self.leaf(g, t)
        pix.blit(g, P["rock"], DX - 15, POOL - 4)
        g.d.rectangle((0, POOL + 6, 40, 63), fill=0)
        g.d.line((0, POOL + 6, 40, POOL + 6), fill=1)
        for x in range(2, 40, 5):
            g.px(x, POOL + 8 + (x // 5) % 2 * 2)
        if lt is not None and 2.0 < lt < 9:
            figure(g, DX, POOL - 3, t, legs="sit", arm="raise", face="wow" if lt < 4 else "happy")
        else:
            ph = t % 29
            daoshi(g, DX, POOL - 3, "meditate" if 18 < ph < 24 else "sit", t)

    def poem(self, g: Gfx, t: float):
        ev = every(t, 70, 12, 20)
        if ev:
            vplate(g, 112, 6, "飞流直下", n=int(ev[1] / 0.35) + 1)

    def mx(self, g: Gfx, t: float, flow: float = 1.0):
        for y in range(8):
            g.mx[y, 0] = g.mx[y, 7] = True
            if y < 3:
                g.mx[y, 1] = True
        g.mx[0, 6] = True
        if flow > 0:
            for col, sp in ((3, 9), (4, 12), (5, 10)):
                for y in range(7):
                    if (y - int(t * sp)) % 3 == 0:
                        g.mx[y, col] = True
            if int(t * 6) % 2:
                g.mx[6, 2] = g.mx[6, 6] = True
        g.mx[7, 1:7] = True

    def hold(self, g: Gfx, t: float):
        self.world(g, t)
        self.poem(g, t)
        self.mx(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        tw = t - T
        if t < 0.5:
            bottom = LIP + 2
        else:
            bottom = LIP + 2 + ease_in(span(t, 0.5, 1.4)) * (POOL - LIP - 2)
        hit = span(t, 1.4, 2.6)
        self.world(g, tw, LIP, bottom, power=hit)
        if 1.4 < t < 2.0:  # 砸进潭里：一圈水花
            k = span(t, 1.4, 2.0)
            cx = (FX0 + FX1) / 2
            for i in range(10):
                a = math.pi * (0.1 + 0.8 * i / 9)
                g.px(cx - math.cos(a) * (6 + k * 16), POOL - math.sin(a) * (10 * k - 8 * k * k) * 2)
            if t < 1.55:
                pix.shake(g, t, 1)
        g.fade(span(t, 0, 0.6))
        if t > 1.2:
            vplate(g, 112, 6, "飞流直下", n=int((t - 1.2) / 0.3) + 1)
        self.mx(g, tw, flow=float(t > 1.0))

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        k = span(t, 0, 0.9)
        top = LIP + ease_in(k) * (POOL - LIP)
        self.world(g, tt, top, POOL, power=1 - span(t, 0.3, 1.1))
        g.fade(1 - span(t, 0.8, 1.3))
        self.mx(g, tt, flow=float(k < 0.6))


def _fade(spr, k):
    from .x3_lib import faded
    return faded(spr, k)
