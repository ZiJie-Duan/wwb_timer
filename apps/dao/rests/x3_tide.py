"""观潮：钱塘江潮。苏轼《催试官考较戏作》“八月十八潮，壮观天下无”；潘阆《酒泉子》“弄潮儿向涛头立，手把红旗旗不湿”。
出处：<https://cn-poetry.com/su-shi-poems/written-to-examiners.html>

站在江边鱼鳞石塘上隔江远望：对岸月轮山上一座七层六和塔，远山一抹；江面平时碎光漂动；
小道士站在塘上看潮，呼吸眨眼，偶尔手搭凉棚。
每 75 秒一潮：天边先出一道白线（一线潮），斜着横过江面、从右往左推过来，越近越高、越宽；
潮头一道白练，前面飞沫，后面一片翻涌的网点；扫到石塘时浪花溅过塘顶，小道士往后一缩、惊叫；
潮快到时他伸手一指。每潮大小不同；三成多的潮头上立着弄潮儿，手举旗子在风里翻。
题句：潮来时“八月十八潮”、过后“壮观天下无”，有弄潮儿时“弄潮儿向涛头立”。小事件：江鸥掠过（41s）。
入场：石塘从下面升上来，江面淡入。  退场：最后一道大潮从右边漫过整幅画面。
点阵：底行江岸、细浪；潮来时一道浪墙从右往左推过点阵，高度随潮的大小。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bake, bird, every, glints, mountain, plate, ridge

FAR = 30           # 对岸
NEAR = 50          # 石塘顶
DX = 58
PERIOD, OFF = 75.0, 20.0
CROSS = 16.0       # 潮头从右到左走完的秒数


def _pagoda():
    """六和塔：七层，层层出檐两角上翘，塔身开窗，塔刹"""
    def draw(g):
        cx, y = 20, 25
        for i in range(7):
            w = 7 - i * 0.7
            h = 3
            g.d.rectangle((cx - w + 2, y - h, cx + w - 2, y), fill=0, outline=1)
            g.px(cx, y - 1 - (i % 2), 0) if False else g.px(cx, y - 2, 0)
            g.d.line((cx - w - 1, y - h - 1, cx + w + 1, y - h - 1), fill=1)  # 檐
            g.px(cx - w - 2, y - h - 2), g.px(cx + w + 2, y - h - 2)
            y -= h + 1
        g.d.line((cx, y - 4, cx, y), fill=1)
        g.px(cx - 1, y - 2), g.px(cx + 1, y - 2)
    return bake(draw)


def _wall():
    """鱼鳞石塘：错缝条石一层层往下收，塘顶一道压顶石"""
    def draw(g):
        g.d.rectangle((0, NEAR, 127, 63), fill=0)
        g.d.line((0, NEAR, 127, NEAR), fill=1)
        g.d.line((0, NEAR + 1, 127, NEAR + 1), fill=1)
        for row, y in enumerate(range(NEAR + 4, 64, 4)):
            g.d.line((0, y, 127, y), fill=1)
            for x in range((row % 2) * 5, 128, 10):
                g.d.line((x, y - 3, x, y - 1), fill=1)
            for x in range(2 + (row % 2) * 5, 128, 10):
                g.px(x + 1, y - 2)
    return bake(draw, solid=lambda d: d.rectangle((0, NEAR, 127, 63), fill=1))


_C: dict = {}


def parts():
    if not _C:
        hills = mountain(ridge([(16, 16, 22), (60, 24, 18), (104, 21, 26)], 51, base=FAR + 2, rough=0.8, round_top=True),
                         lit=((0.25, 2),), shade=((0.125, 1),), outline=1)
        _C.update(hills=hills, pagoda=_pagoda(), wall=_wall())
    return _C


ROWER = pix.frames("""
 ##
 .#
 ###
 ##
 # #
---
 ##
 #.
 ###
 ##
 # #
""")


@register
class TideWatch(Rest):
    id = "x3.tide"
    name = "观潮"
    desc = "站在钱塘江鱼鳞石塘上看潮：一线潮从天边斜推过江面，越近越高，扫到塘下浪花溅起；三成潮头上立着举旗的弄潮儿"
    T = {"enter": 2.8, "exit": 1.3}

    def setup(self):
        self.P = parts()

    def tide(self, t: float):
        """当前这一潮：返回 (n, lt, size, rower)；lt = 潮头出现后的秒数"""
        if t < OFF:
            n, lt = -1, t - OFF + PERIOD
        else:
            n, lt = int((t - OFF) // PERIOD), (t - OFF) % PERIOD
        size = 0.6 + 0.4 * rand(n, self.seed)
        rower = rand(n + 50, self.seed) < 0.36
        return n, lt, size, rower

    def front_x(self, lt: float, y: float) -> float:
        """潮头在第 y 行的 x（远端落后，近端在前）"""
        k = ease_in_out(clamp(lt / CROSS)) * 0.6 + clamp(lt / CROSS) * 0.4
        x = lerp(150, -40, k)
        return x + (NEAR - y) * 1.6

    def river(self, g: Gfx, t: float, lt: float, size: float, rower: bool, over: float = 0.0):
        g.d.rectangle((0, FAR + 1, 127, NEAR - 1), fill=0)
        for x in range(0, 128, 3):
            g.px(x, FAR + 1)
        glints(g, 0, 128, FAR + 4, NEAR - 1, t, 9, n=16, speed=2.5, far=1, near=5, blink=0.45, rows=3)
        if not 0 <= lt < CROSS + 4:
            return None
        k = clamp(lt / CROSS)
        for y in range(FAR + 2, NEAR):
            depth = (y - FAR) / (NEAR - FAR)
            xf = self.front_x(lt, y)
            w = int(1 + (2 + 4 * depth) * size * (0.4 + 0.6 * k))
            g.d.line((xf, y, xf + w, y), fill=1)                     # 潮头白练
            for x in range(int(xf + w + 1), int(xf + w + 6 + depth * 10)):  # 身后翻涌
                if (x + y + int(t * 6)) % 2 == 0 and 0 <= x < 128:
                    g.px(x, y)
            if (y + int(t * 10)) % 3 == 0:                          # 前面的飞沫
                g.px(xf - 2 - (y % 4), y - 1)
        crest = self.front_x(lt, FAR + 10)
        hh = int(2 + 5 * size * k)
        for i in range(0, 18, 2):                                    # 潮头上沿的浪花
            x = self.front_x(lt, FAR + 2 + i) + 1
            yy = FAR + 2 + i - hh * (0.4 + 0.6 * i / 18) + math.sin(t * 9 + i) * 0.8
            g.px(x, yy), g.px(x + 1, yy + 1)
        if rower and 0.15 < k < 0.95:                               # 弄潮儿
            rx = self.front_x(lt, FAR + 9) + 1
            ry = FAR + 9 - hh * 0.7
            spr = ROWER[int(t * 4) % 2]
            pix.blit(g, spr, rx - 2, ry - spr.h)
            fx, fy = rx + 1, ry - spr.h - 5
            g.d.line((fx, fy, fx, fy + 5), fill=1)
            wav = int(t * 8) % 2
            g.d.polygon([(fx + 1, fy), (fx + 5, fy + 1 + wav), (fx + 1, fy + 3)], fill=1)
        return self.front_x(lt, NEAR - 1)

    def spray(self, g: Gfx, t: float, xn: float, size: float):
        """潮头扫到石塘：浪花溅过塘顶（沿潮头身后一段）"""
        for j in range(5):
            x = xn + 2 + j * 5
            if not -4 < x < 132:
                continue
            ph = (t * 1.7 + j * 0.37) % 1
            top = (6 + 12 * size) * (1 - j / 6)
            for i in range(5):
                q = (ph + i * 0.2) % 1
                y = NEAR - 1 - (4 * q - 4 * q * q) * top
                g.px(x + (i - 2) * 1.5 + q * 3, y)
            g.d.chord((x - 3, NEAR - 3, x + 3, NEAR + 1), 180, 360, fill=1)

    def world(self, g: Gfx, t: float, wall_dy: float = 0.0):
        P = self.P
        n, lt, size, rower = self.tide(t)
        g.blit(P["hills"], 0, 0)
        pix.blit(g, P["pagoda"], 0, -3)
        gl = every(t, 41, 6, 8)
        if gl:  # 江鸥
            k = gl[1] / 6
            bird(g, lerp(-6, 134, k), 12 + math.sin(k * 7) * 3, gl[1], fps=6)
        xn = self.river(g, t, lt, size, rower)
        g.blit(P["wall"], 0, wall_dy)
        # 小道士的反应
        face, pose, dx = "normal", "idle", DX
        if xn is not None:
            if DX + 12 < xn < DX + 70:
                pose = "point"
            if DX - 14 < xn <= DX + 12:
                face, dx = "wow", DX - 2
            elif DX - 40 < xn <= DX - 14:
                face = "happy"
        elif (t % 19) > 15:
            pose = "raise"
        daoshi(g, dx, NEAR + wall_dy, pose, t, face=face)
        if xn is not None and xn < 132:
            self.spray(g, t, xn, size)
        return lt, size, rower, xn

    def label(self, g: Gfx, lt: float, rower: bool):
        if 0 <= lt < 12:
            plate(g, 82, 3, "弄潮儿向涛头立" if rower else "八月十八潮", align="center")
        elif 14 < lt < 26:
            plate(g, 82, 3, "壮观天下无", align="center")

    def mx(self, g: Gfx, t: float, lt: float, size: float):
        g.mx[7, :] = True
        for x in range(8):
            if (x + int(t * 3)) % 4 == 0:
                g.mx[6, x] = True
        if 0 <= lt < CROSS:
            k = clamp(lt / CROSS)
            col = int(round(lerp(8, -1, k)))
            h = int(1 + size * 4 * (0.5 + k * 0.5))
            for c in (col, col + 1):
                if 0 <= c < 8:
                    for y in range(7 - h, 7):
                        g.mx[y, c] = True
            for c in range(col + 2, 8):
                if (c + int(t * 6)) % 2:
                    g.mx[5, c] = True

    def hold(self, g: Gfx, t: float):
        lt, size, rower, _ = self.world(g, t)
        self.label(g, lt, rower)
        self.mx(g, t, lt, size)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        tw = t - T
        dy = (1 - ease_out(span(t, 0, 1.6))) * 16
        lt, size, rower, _ = self.world(g, tw, wall_dy=dy)
        g.fade(span(t, 0, 0.8))
        if t > 1.6:
            plate(g, 82, 3, "八月十八潮", align="center")
        self.mx(g, tw, lt, size)

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        lt, size, rower, _ = self.world(g, tt)
        k = ease_in(span(t, 0, self.T["exit"]))
        x = lerp(132, -20, k)  # 最后一道大潮漫过整幅画面
        g.d.rectangle((x + 4, 0, 127, 63), fill=0)
        for y in range(0, 64):
            xx = x + math.sin(y * 0.5 + t * 10) * 2
            g.d.line((xx, y, xx + 3, y), fill=1)
            if (y + int(t * 20)) % 2 == 0:
                g.d.line((xx + 5, y, xx + 9, y), fill=1)
        pix.checker(g, (x + 12, 0, 128, 64), 0.125)
        self.mx(g, tt, lt, size)
        g.mx[:, max(0, 8 - int(k * 9)):] = False
