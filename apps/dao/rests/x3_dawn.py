"""紫气东来：《列仙传》“老子西游，关令尹喜望见有紫气浮关，而老子果乘青牛而过也。”（函谷关）

清晨的云海：太阳从东边（右）云海里升起，十二道光芒长短相间、慢慢转动；
三层云海（像素云头一排排，远小慢、近大快）往左流；群峰露出云海，西边山头上一座关楼（城台、门洞、垛口、两重檐）；
三缕“紫气”是三道往西流动的波浪虚线，从日边一路流进亮着的门洞。
小道士站在近处山石上，朝着日出拱手作揖，衣袖随风。
小事件：日光一亮、光芒伸长（43s）；三只飞鸟掠过日前（59s）；每 300 秒一位老者骑青牛从东边的云头上慢慢走进关门，
        走到关前“紫气东来”四字浮现。
入场：太阳从云海里升起，光芒散开，紫气伸向关楼；题“紫气东来”。  退场：日光大盛，画面从西往东褪去，最后太阳收成一点。
点阵：底行云海，上面一轮日，光芒旋转，日光一亮时外圈变大。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import daoshi
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bake, bird, every, mountain, plate, ridge, rock

SUN = (106, 30)
SR = 7
GATE = (24, 36)      # 关楼门洞中心（地面）
DX, FLOOR = 76, 58


def _gate():
    """函谷关：城台（砖缝、门洞、垛口）+ 关楼（两重檐、翘角、柱）"""
    x0, x1, base = 8, 40, GATE[1] + 4
    wall = [(x0, base), (x0 + 2, base - 12), (x1 - 2, base - 12), (x1, base)]

    def draw(g):
        g.d.polygon(wall, fill=0, outline=1)
        for x in range(x0 + 2, x1 - 1, 3):                       # 垛口
            g.d.rectangle((x, base - 14, x + 1, base - 13), fill=1)
        for y in range(base - 9, base, 3):                       # 砖缝
            for x in range(x0 + 3 + (y % 2) * 2, x1 - 2, 5):
                g.d.line((x, y, x + 2, y), fill=1)
        cx = GATE[0]
        g.d.rectangle((cx - 3, base - 7, cx + 3, base), fill=0)  # 门洞（拱）
        g.d.chord((cx - 3, base - 10, cx + 3, base - 4), 180, 360, fill=0)
        g.d.arc((cx - 4, base - 11, cx + 4, base - 3), 180, 360, fill=1)
        g.d.line((cx - 4, base - 7, cx - 4, base), fill=1)
        g.d.line((cx + 4, base - 7, cx + 4, base), fill=1)
        ty = base - 14
        g.d.rectangle((cx - 9, ty - 6, cx + 9, ty - 1), fill=0, outline=1)  # 楼身
        for x in range(cx - 7, cx + 8, 4):
            g.d.line((x, ty - 5, x, ty - 2), fill=1)
        for w, y in ((14, ty - 7), (10, ty - 13)):                 # 两重檐
            pts = [(cx - w - 2, y - 1), (cx - w, y), (cx + w, y), (cx + w + 2, y - 1), (cx + w - 3, y - 4),
                   (cx - w + 3, y - 4)]
            g.d.polygon(pts, fill=0, outline=1)
            g.d.line((cx - w + 2, y - 2, cx + w - 2, y - 2), fill=1)
        g.d.rectangle((cx - 6, ty - 12, cx + 6, ty - 8), fill=0, outline=1)
        g.d.line((cx, ty - 20, cx, ty - 18), fill=1)

    return bake(draw, solid=lambda d: (d.polygon(wall, fill=1), d.rectangle((GATE[0] - 15, GATE[1] - 30, GATE[0] + 15,
                                                                              GATE[1] - 10), fill=1)))


OX = pix.frames("""
      #.
    ####
    #.#.
  .######
 #########.
###########
 ## #  # ##
 #  #   # #
---
      #.
    ####
    #.#.
  .######
 #########.
###########
 ## #  # ##
  # #  ## #
""")

SAGE = pix.sprite("""
 #  .##.
 #  ####
 #  #.##
 # .###.
 ######
 # #####
 # ####.
 #  ##
""")

_C: dict = {}


def parts():
    if not _C:
        peaks = mountain(ridge([(24, 30, 18), (52, 23, 13), (66, 31, 8), (124, 34, 10)], 31, base=56, rough=1.2, power=1.0),
                         lit=((0.5, 1), (0.25, 2)), shade=((0.125, 2),), outline=1)
        _C.update(peaks=peaks, gate=_gate(), rock=rock(30, 9, 5))
    return _C


def scallops(g: Gfx, y: float, t: float, r: int, speed: float, seed: int, fill_below: float = 0.0):
    """一排云头：一串半圆鼓包往左流，下面黑（盖住后面），鼓包里一道卷纹"""
    step = r * 2 - 1
    off = (t * speed) % step
    g.d.rectangle((0, y, 127, 63), fill=0)
    i0 = int(t * speed // step)
    for j in range(-1, 128 // step + 3):
        x = j * step - off
        hh = r + (rand(j + i0, seed) - 0.5) * 2
        g.d.chord((x - r, y - hh, x + r, y + hh), 180, 360, fill=0, outline=1)
        if r >= 4:
            g.d.arc((x - r + 2, y - hh + 2, x + r - 2, y + hh - 2), 200, 270, fill=1)
    g.d.line((0, y, 127, y), fill=0)
    if fill_below:
        pix.checker(g, (0, int(y) + 2, 128, int(y) + 4), fill_below)


@register
class DawnQi(Rest):
    id = "x3.dawn"
    name = "紫气东来"
    desc = "云海日出，光芒旋转，三缕紫气从日边流进西边的函谷关；小道士在山石上朝日拱手；不时老子骑青牛走进关门"
    T = {"enter": 3.4, "exit": 1.4}

    def setup(self):
        self.P = parts()

    def sun(self, g: Gfx, t: float, sy: float = SUN[1], power: float = 1.0):
        sx = SUN[0]
        fl = every(t, 43, 3, 20)
        boost = math.sin(fl[1] / 3 * math.pi) if fl else 0.0
        a0 = t * 0.12
        for i in range(12):
            a = a0 + i * math.pi / 6
            r0 = SR + 3
            r1 = SR + (9 if i % 2 else 14) * power + boost * 5
            for k in range(int(r0), int(r1), 2):
                g.px(sx + math.cos(a) * k, sy + math.sin(a) * k)
        g.d.ellipse((sx - SR, sy - SR, sx + SR, sy + SR), fill=1)
        g.d.ellipse((sx - SR + 2, sy - SR + 2, sx + SR - 2, sy + SR - 2), outline=0)  # 日轮里一圈
        if boost > 0.3:
            g.d.ellipse((sx - SR - 2, sy - SR - 2, sx + SR + 2, sy + SR + 2), outline=1)

    def qi(self, g: Gfx, t: float, reach: float = 1.0):
        """三缕紫气：从日边弯向关楼的波浪虚线，点往西流"""
        gx, gy = GATE[0] + 10, GATE[1] - 26
        for j in range(3):
            n = 70
            for i in range(n):
                k = i / n
                if k > reach:
                    break
                x = lerp(SUN[0] - SR - 3, gx, k)
                y = lerp(SUN[1] - 4 - j * 3, gy + j * 3, k) - math.sin(k * math.pi) * (8 + j * 2)
                y += math.sin(k * 14 - t * 3 + j * 2) * 1.2
                if (i + int(t * 8)) % 3 == 0:
                    g.px(x, y)

    def ox(self, g: Gfx, t: float):
        ev = every(t, 300, 40, 120)
        if not ev:
            return None
        lt = ev[1]
        k = span(lt, 0, 30)
        x = lerp(132, GATE[0] + 6, ease_in_out(k))
        y = lerp(43, GATE[1] + 3, k)
        if lt > 31:
            return lt
        f = OX[int(lt * 3) % 2]
        pix.blit(g, f, x - 5, y - 8, flip=True)
        # 骑在牛背上的老者：白须、拄杖
        pix.blit(g, SAGE, x - 2, y - 17, flip=True)
        return lt

    def world(self, g: Gfx, t: float, sy: float = SUN[1], reach: float = 1.0, power: float = 1.0):
        P = self.P
        self.sun(g, t, sy, power)
        scallops(g, 41, t, 3, 1.2, 1)
        g.blit(P["peaks"], 0, 0)
        g.blit(P["gate"], 0, 0)
        # 门洞亮着
        gx, gy = GATE[0], GATE[1] + 4
        for y in range(gy - 6, gy):
            for x in range(gx - 2, gx + 3):
                if (x + y) % 2 == 0:
                    g.px(x, y)
        self.qi(g, t, reach)
        b = every(t, 59, 5, 10)
        if b:
            k = b[1] / 5
            for j in range(3):
                bird(g, lerp(130, 60, k) + j * 7, SUN[1] - 6 + j * 3 - k * 6, b[1], fps=9, flip=True, ph=j * 0.4)
        lt = self.ox(g, t)
        scallops(g, 50, t, 5, 3.0, 2, fill_below=0.125)
        pix.blit(g, P["rock"], DX - 15, FLOOR - 4)
        scallops(g, 61, t, 7, 6.0, 3)
        ph = t % 24
        pose = "gongshou" if 15 < ph < 18 else "bow" if 18 <= ph < 20 else "idle"
        daoshi(g, DX, FLOOR - 3, pose, t, face="happy" if lt and lt > 28 else "normal")
        return lt

    def mx(self, g: Gfx, t: float, power: float = 1.0):
        g.mx[7, :] = True
        for x in range(8):
            if (x + int(t * 2)) % 3 == 0:
                g.mx[6, x] = True
        cx, cy = 3.5, 3.5
        for y in range(2, 6):
            for x in range(2, 6):
                if (x - cx) ** 2 + (y - cy) ** 2 < 3:
                    g.mx[y, x] = True
        fl = every(t, 43, 3, 20)
        r = 3.4 if fl else 2.8
        a0 = t * 1.2
        for i in range(4):
            a = a0 + i * math.pi / 2
            x, y = int(round(cx + math.cos(a) * r * power)), int(round(cy + math.sin(a) * r * power))
            if 0 <= x < 8 and 0 <= y < 6:
                g.mx[y, x] = True

    def hold(self, g: Gfx, t: float):
        lt = self.world(g, t)
        if lt and lt > 26:
            plate(g, 64, 3, "紫气东来", align="center")
        self.mx(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        sy = lerp(52, SUN[1], ease_out(span(t, 0, 2.0)))
        self.world(g, t - T, sy, reach=span(t, 1.6, 3.0), power=span(t, 0.8, 2.2))
        g.fade(span(t, 0, 0.6))
        if t > 2.0:
            plate(g, 64, 3, "紫气东来", align="center")
        self.mx(g, t - T, power=span(t, 0.8, 2.2))

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        k = span(t, 0, self.T["exit"])
        self.world(g, tt, power=1 + k)
        edge = lerp(-4, 132, ease_in_out(k))  # 从西往东褪去
        g.d.rectangle((0, 0, edge, 63), fill=0)
        for y in range(0, 64, 2):
            g.px(edge + 1 + (y // 2) % 3, y)
        if k > 0.85:
            g.d.rectangle((0, 0, 127, 63), fill=0)
            g.px(SUN[0], SUN[1])
        self.mx(g, tt)
        g.mx[:, : int(k * 8)] = False
