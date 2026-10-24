"""烧火（像素风）：斋堂的砖灶，大铁锅扣着木锅盖，锅盖缝冒白汽，烟囱冒烟；灶门里火苗一跳一跳。
小道士跪坐在灶前的蒲墩上，一段 12 秒：转身从柴堆抽一根柴，转回来送进灶膛（火一旺、火星迸出）；
拿吹火筒对着灶门鼓腮吹三口，每口火苗都往上蹿；然后守着火，仰头打个哈欠。
彩蛋：约三成的轮次第三口吹完倒烟——一团黑烟从灶门扑到脸上，熏成花脸、头上转金星，冒出“咳咳”；
约每 53 秒水开得太猛，锅盖噗噗直跳、白汽喷一圈。
左侧竖写“若烹小鲜”（《道德经》六十章：治大国，若烹小鲜）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import lerp, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import STARS, Clock, cyc, event, fade_out, keys, scroll, worker

FLOOR = 56
TEXT_X = 3
DX = 52
S0, S1, TOP = 68, 108, 32          # 灶台左右、台面
DOOR = (72, 43, 84, 55)            # 灶门
CYC = 12.0

FLAME = pix.frames("""
   #
  ##  #
  ### #
 #.## #
 #..###
##...##
#.....#
---
  #
  #  #
 ### #
 #.###
##..##
#...###
#.....#
---
    #
 #  #
 #  ##
 ##.##
##..##
#...###
#.....#
""")
EMBER = Sprite("""
#.#.#.#.#
.#.#.#.#.
""")

STICK = Sprite("""
.#
############
##.#.###.##
""")

TUBE = Sprite("""
################
#.##.###.##.###.
################
""")

PIECE = Sprite("""
  ####
 #....#
#..##..#
#.#..#.#
########
""")

LID = Sprite("""
         ###
        #...#
         ###
   ###############
 ####.#########.####
#####.#########.#####
#####################
""")

MATCH_FIRE = Sprite(" #\n###\n #")

STOOL = Sprite("""
##############
#.##########.#
 #          #
 #          #
""")


@register
class Cook(Rest):
    id = "x5.cook"
    name = "烧火"
    desc = "斋堂砖灶前跪坐烧火：抽柴送进灶膛、拿吹火筒鼓腮吹三口，火苗蹿高；偶尔倒烟熏成花脸，锅盖噗噗直跳"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.puffs = pix.Puffs(self.seed)        # 烟囱的烟、锅上的汽
        self.soot = pix.Puffs(self.seed + 1)     # 倒烟
        self.sparks = pix.Sparks(self.seed + 2)
        self.s = self.seed * 31 + 3

    # ------------------------------------------------ 灶台

    def stove(self, g: Gfx, t: float, heat: float, boil: float | None):
        # 后墙：一个挂勺的钉、一扇小窗
        g.d.rectangle((30, 8, 46, 22), outline=1)
        g.d.line((38, 8, 38, 22), fill=1)
        g.d.line((30, 15, 46, 15), fill=1)
        g.d.line((19, FLOOR, 127, FLOOR), fill=1)
        pix.checker(g, (19, FLOOR + 2, 128, 64), 0.125)
        # 烟囱
        g.d.rectangle((S1 - 9, 6, S1 - 2, TOP), fill=1)
        g.d.rectangle((S1 - 11, 4, S1, 6), fill=1)
        for y in range(9, TOP, 4):
            g.d.line((S1 - 9, y, S1 - 2, y), fill=0)
            g.px(S1 - 6 + (y // 4) % 2 * 2, y + 1, 0), g.px(S1 - 6 + (y // 4) % 2 * 2, y + 2, 0)
        # 灶身：砖缝
        g.d.rectangle((S0, TOP, S1, FLOOR), fill=1)
        g.d.rectangle((S0 - 2, TOP - 2, S1 + 2, TOP), fill=1)
        g.d.line((S0 - 2, TOP + 1, S1 + 2, TOP + 1), fill=0)
        for r, y in enumerate(range(TOP + 5, FLOOR, 4)):
            g.d.line((S0, y, S1, y), fill=0)
            for x in range(S0 + 3 + (r % 2) * 4, S1, 8):
                g.d.line((x, y - 3, x, y - 1), fill=0)
        pix.checker(g, (S1 - 6, TOP + 2, S1 + 1, FLOOR), 0.5, fill=0)
        # 灶门：拱形开口，里面火
        x0, y0, x1, y1 = DOOR
        g.d.rectangle((x0 - 2, y0 - 1, x1 + 2, y1), fill=1)
        g.d.pieslice((x0, y0 - 4, x1, y0 + 6), 180, 360, fill=0)
        g.d.rectangle((x0, y0 + 1, x1, y1), fill=0)
        g.d.line((x0 - 2, y0 - 4, x1 + 2, y0 - 4), fill=0)
        pix.blit(g, EMBER, x0 + 2, y1 - 2, outline=False)
        fr = pix.anim(FLAME, t + heat * 0.3, 8 + heat * 6)
        sc = 1.0 + heat * 0.5
        spr = pix.stretch(fr, 1.0, sc)
        pix.blit(g, spr, x0 + 2, y1 - 2 - spr.h, outline=False)
        if heat > 0.4:
            fr2 = pix.anim(FLAME, t + 0.4, 9)
            pix.blit(g, fr2, x0 + 5, y1 - 2 - fr2.h, outline=False)
        # 锅盖（水开得猛时噗噗跳）
        jump = 0
        if boil is not None and boil < 5.0:
            jump = 2 if int(boil * 7) % 2 == 0 else 0
        pix.blit(g, LID, 77, TOP - 9 - jump)
        g.d.line((76, TOP - 2, 101, TOP - 2), fill=1)

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        dt = self.clock.tick(t)
        n, k = cyc(t, CYC)
        back = rand(n, self.s) < 0.3
        boil = event(t, 53.0, 6.0, self.s + 1)
        boil_q = boil[1] if boil else None
        # 火势
        heat = 0.0
        if 2.4 < k < 3.6:
            heat = 1 - span(k, 2.6, 3.6)
        for m in range(3):
            pk = 4.0 + m * 1.1
            if pk < k < pk + 0.9:
                heat = max(heat, math.sin(span(k, pk, pk + 0.9) * math.pi))
        self.stove(g, t, heat, boil_q)
        # 柴堆
        for x, y in ((21, 51), (29, 51), (25, 46)):
            pix.blit(g, PIECE, x, y)
        pix.blit(g, STOOL, DX - 7, FLOOR - 4)
        st = self.pose(k)
        if back and 7.2 < k < 11.5:
            st["face"] = "sleep"

        def tool(gg, h1, h2):
            if st["stick"] == "hand" and h1:
                pix.blit(gg, STICK, h1[0] - 6, h1[1] - 1)
            if st["tube"] and h1:
                mx, my = DX + 7, FLOOR - 24
                tx, ty = DOOR[0] + 1, DOOR[1] + 6
                gg.d.line((mx + 1, my + 1, tx, ty), fill=1, width=3)
                for j in range(1, 4):  # 竹节
                    gg.px(lerp(mx, tx, j / 4), lerp(my, ty, j / 4) + 1, 0)

        worker(g, DX, FLOOR, t, hand=st["hand"], legs="kneel", flip=st["flip"], face=st["face"], tool=tool,
               head=st["head"], bob=False)
        if st["stick"] == "door":  # 柴推进灶膛
            q = span(k, 2.0, 2.6)
            pix.blit(g, STICK, lerp(DOOR[0] - 10, DOOR[0] + 1, q), DOOR[3] - 6)
        if st["cheek"]:  # 鼓腮：脸颊鼓出一圈
            g.d.ellipse((DX + 6, FLOOR - 25, DX + 10, FLOOR - 21), fill=1)
            g.d.ellipse((DX + 7, FLOOR - 24, DX + 9, FLOOR - 22), fill=0)
        # 打击：送柴、每口气
        if self.clock.crossed(t, t - k + 2.6):
            self.sparks.burst(DOOR[0] + 6, DOOR[1] + 4, 8, 22, up=20, life=0.6, gravity=30)
        for m in range(3):
            if self.clock.crossed(t, t - k + 4.0 + m * 1.1 + 0.15):
                self.sparks.burst(DOOR[0] + 6, DOOR[1] + 2, 5 + m * 2, 26, up=24, life=0.7, gravity=25)
        if back and self.clock.crossed(t, t - k + 6.6):
            for j in range(7):
                self.soot.emit(DOOR[0] - 2 - j, DOOR[1] + 4 - j, vx=-9 - j * 1.5, vy=-7 - j, life=1.6 + j * 0.1,
                               rmax=3.6, spread=3)
        # 烟囱冒烟、锅盖缝冒汽
        if int(t * 1.6) != int((t - dt) * 1.6):
            self.puffs.emit(S1 - 5, 2, vx=4, vy=-6, life=1.6, rmax=2.0, spread=1)
        if int(t * 2.2) != int((t - dt) * 2.2):
            self.puffs.emit(78 + (int(t * 2.2) % 2) * 22, TOP - 5, vy=-7, life=1.3, rmax=1.5, spread=1)
        if boil_q is not None and boil_q < 5.0 and int(t * 8) != int((t - dt) * 8):
            self.puffs.emit(89 + (int(t * 8) % 3 - 1) * 9, TOP - 10, vx=(int(t * 8) % 3 - 1) * 10, vy=-10,
                            life=0.9, rmax=2.5, spread=2)
        self.puffs.step(dt, wind=2)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.soot.step(dt)
        self.soot.draw(g, hollow_after=0.9)
        cough = back and 7.0 < k < 11.5
        if cough:  # 花脸：脸上几块黑；头上转金星
            for x, y in ((DX + 2, FLOOR - 23), (DX + 5, FLOOR - 21), (DX - 1, FLOOR - 20), (DX + 6, FLOOR - 26)):
                g.px(x, y, 0), g.px(x + 1, y, 0)
            pix.blit(g, pix.anim(STARS, t, 6), DX - 4, FLOOR - 42)
        self.matrix(g, t, heat, back and 6.6 < k < 8.0)
        if cough and int((k - 7.0) * 2.5) % 2 == 0:
            g.d.rectangle((DX + 10, 6, DX + 31, 16), fill=0)
            g.text(DX + 12, 8, "咳咳", size=8)
        scroll(g, TEXT_X, "若烹小鲜", k=text_k, side="left")

    def pose(self, k: float) -> dict:
        st = dict(hand=None, flip=False, face="normal", head="up", stick=None, tube=False, cheek=False)
        if k < 1.2:  # 转身抽一根柴
            st["flip"] = True
            st["hand"] = keys(k, [(0, (DX - 9, FLOOR - 12)), (0.6, (36, FLOOR - 7)), (1.2, (DX - 9, FLOOR - 14))])
            if k > 0.6:
                st["stick"] = "hand"
            return st
        if k < 2.6:  # 转回来送进灶膛
            st["hand"] = keys(k, [(1.2, (DX + 10, FLOOR - 14)), (2.0, (DX + 14, FLOOR - 8)),
                                  (2.6, (DOOR[0] - 4, DOOR[3] - 5))])
            st["stick"] = "hand" if k < 2.0 else "door"
            return st
        if k < 3.8:
            st["hand"] = keys(k, [(2.6, (DOOR[0] - 4, DOOR[3] - 5)), (3.4, (DX + 12, FLOOR - 17))])
            return st
        if k < 7.4:  # 吹火筒：三口
            st["tube"] = True
            st["hand"] = (DX + 12, FLOOR - 19)
            for m in range(3):
                pk = 4.0 + m * 1.1
                if pk - 0.45 < k < pk:
                    st["cheek"] = True
            st["face"] = "sleep" if any(4.0 + m * 1.1 <= k < 4.6 + m * 1.1 for m in range(3)) else "normal"
            return st
        if 9.0 < k < 10.6:  # 打哈欠：手捂嘴
            st["hand"] = keys(k, [(9.0, (DX + 9, FLOOR - 14)), (9.4, (DX + 9, FLOOR - 21)), (10.2, (DX + 9, FLOOR - 21)),
                                  (10.6, (DX + 9, FLOOR - 14))])
            st["face"] = "wow"
            return st
        st["face"] = "happy" if 7.4 < k < 8.6 else "normal"
        return st

    def matrix(self, g: Gfx, t: float, heat: float, smoke: bool):
        """点阵：一排炭上的火苗，随火势跳，火旺时偶尔蹦火星；倒烟时是一团烟"""
        if smoke:
            g.mx_rows([0x00, 0x3C, 0x7E, 0xDB, 0xFF, 0x7E, 0x3C, 0x00])
            return
        g.mx_rows([0, 0, 0, 0, 0, 0, 0, 0xFF])
        for x in range(8):
            h = 1 + int((math.sin(t * 9 + x * 1.7) * 0.5 + 0.5) * (2 + heat * 4))
            for y in range(7 - h, 7):
                g.mx_set(x, y)
        if heat > 0.6:
            g.mx_set(int(t * 13) % 8, int(t * 7) % 2)
            g.mx_level = 3

    def enter(self, g: Gfx, t: float):
        """跪坐在灶前，划火柴点着灶膛：火苗从无到有，锅上开始冒汽"""
        dt = self.clock.tick(t)
        heat = span(t, 1.2, 2.4)
        self.stove(g, t, 0.0, None)
        if heat < 1:  # 火还没起来时灶门里是黑的：盖住火苗
            x0, y0, x1, y1 = DOOR
            g.d.rectangle((x0, y0 + 1, x1, y1 - 3), fill=0)
            if heat > 0:
                fr = pix.anim(FLAME, t, 10)
                spr = pix.stretch(fr, 1.0, max(0.3, heat))
                pix.blit(g, spr, x0 + 2, y1 - 2 - spr.h, outline=False)
        for x, y in ((21, 51), (29, 51), (25, 46)):
            pix.blit(g, PIECE, x, y)
        pix.blit(g, STOOL, DX - 7, FLOOR - 4)
        hand = keys(t, [(0, (DX + 9, FLOOR - 14)), (0.6, (DX + 12, FLOOR - 16)), (1.0, (DX + 16, FLOOR - 14)),
                        (1.3, (DOOR[0] - 2, DOOR[3] - 4)), (2.0, (DOOR[0] - 2, DOOR[3] - 4)), (2.6, (DX + 9, FLOOR - 14))])
        worker(g, DX, FLOOR, t, hand=hand, legs="kneel", bob=False, face="happy" if t > 2.0 else "normal")
        if 0.8 < t < 1.6:  # 火柴头一点火
            hx, hy = hand
            g.d.line((hx + 1, hy, hx + 4, hy - 1), fill=1)
            if t > 1.0:
                pix.blit(g, MATCH_FIRE, hx + 4, hy - 4)
        if self.clock.crossed(t, 1.3):
            self.sparks.burst(DOOR[0] + 5, DOOR[3] - 4, 8, 20, up=16, life=0.6, gravity=30)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.matrix(g, t, heat * 0.5, False)
        if heat <= 0:
            g.mx[:] = False
            g.mx[7, :] = True
        scroll(g, TEXT_X, "若烹小鲜", k=span(t, 0.4, 2.4), side="left")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
