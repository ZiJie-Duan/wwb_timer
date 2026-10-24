"""抱瓮灌园（像素风）：井边立着一架桔槔（吊杆、坠石、吊桶），小道士偏不用它——蹲在井口把瓦瓮沉下去舀满，
抱着走到菜畦，一棵棵倾瓮浇水：水成一道弧落下，溅起水花，浇过的菜叶一挺。菜随趟数从两片叶的小苗长成大白菜。
一趟走完擦把汗。约四成的趟数刮一阵风，桔槔吱呀吱呀晃起来，他看它一眼、摇摇头、眯眼一笑——“羞而不为”。
彩蛋：约每 53 秒一只蝴蝶飞来停在菜叶上，扇两下翅膀又飞走。
右侧竖写“抱瓮灌园”（《庄子·天地》汉阴丈人：凿隧而入井，抱瓮而出灌……吾非不知，羞而不为也）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import SWEAT, Clock, blit_rot, cyc, event, fade_out, keys, scroll, worker

FLOOR = 56
TEXT_X = 114
WELL = 17                # 井口中心
WELL_TOP = FLOOR - 11
AT_WELL = 36
PLANTS = (68, 85, 102)
TRIP = 16.0

JAR = Sprite("""
  #####
  #...#
   ###
 #######
##.###.##
#########
#.#######
#.#######
##.######
 #######
  #####
""")
JAR_PIV = (4, 6)

PLANT = [
    Sprite("""
#   #
##.##
 ###
  #
"""),
    Sprite("""
 #   #
###.###
 ##.##
#.###.#
  ###
"""),
    Sprite("""
  #  #
 ##.###
###.####
#.#.#.##
 ##.###
#.#####.#
  #####
"""),
    Sprite("""
   ####
  #.##.#
 ##.##.##
 #.####.#
##.####.##
#.######.#
##.####.##
 #.####.#
#.##..##.#
 ########
"""),
]

BUTTERFLY = pix.frames("""
##.##
#.#.#
 .#.
---
 #.#
 .#.
""")


def well(g: Gfx):
    """石砌井台：井口（暗）、井沿一圈条石、侧面砖缝"""
    x0, x1 = WELL - 10, WELL + 10
    g.d.rectangle((x0, WELL_TOP, x1, FLOOR), fill=1)
    g.d.ellipse((x0, WELL_TOP - 3, x1, WELL_TOP + 3), fill=1)
    g.d.ellipse((x0 + 2, WELL_TOP - 2, x1 - 2, WELL_TOP + 1), fill=0)
    g.d.line((x0, WELL_TOP + 3, x1, WELL_TOP + 3), fill=0)
    for r, y in enumerate(range(WELL_TOP + 6, FLOOR, 3)):
        g.d.line((x0, y, x1, y), fill=0)
        for x in range(x0 + 2 + (r % 2) * 3, x1, 6):
            g.d.line((x, y - 2, x, y - 1), fill=0)
    pix.checker(g, (x1 - 3, WELL_TOP + 4, x1 + 1, FLOOR), 0.5, fill=0)


def shadoof(g: Gfx, ang: float):
    """桔槔：立柱 + 横杆（左端坠石，右端吊桶悬在井口上方）"""
    px, py = 4, 18
    g.d.rectangle((px - 1, py, px, FLOOR), fill=1)
    g.d.line((px - 3, py - 3, px - 1, py), fill=1)
    g.d.line((px + 2, py - 3, px, py), fill=1)
    c, s = math.cos(ang), math.sin(ang)
    lx, ly = px - 6 * c, py - 6 * s
    rx, ry = px + 15 * c, py + 15 * s
    g.d.line((lx, ly, rx, ry), fill=1, width=2)
    g.d.ellipse((lx - 3, ly - 1, lx + 2, ly + 4), fill=1)         # 坠石
    g.px(lx - 1, ly + 1, 0)
    bx, by = rx, ry + 11
    g.d.line((rx, ry, bx, by - 3), fill=1)
    g.d.rectangle((bx - 2, by - 3, bx + 2, by + 1), fill=1)       # 吊桶
    g.d.line((bx - 2, by - 1, bx + 2, by - 1), fill=0)


def stream(g: Gfx, x0, y0, x1, y1, t):
    """倒出来的水：一道弧，水点往下走"""
    for j in range(10):  # 出口水平、越落越快
        k = ((t * 3 + j / 10) % 1)
        x, y = lerp(x0, x1, k), y0 + (y1 - y0) * k * k
        g.px(x, y)
        if j % 2 == 0:
            g.px(x, y + 1)


@register
class Garden(Rest):
    id = "x5.garden"
    name = "抱瓮灌园"
    desc = "井边桔槔不用，小道士蹲下沉瓮舀水、抱瓮浇菜，菜一趟趟长大；风吹桔槔吱呀，他摇摇头——羞而不为"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.s = self.seed * 23 + 7

    def scene_bg(self, g: Gfx, t: float, creak: float | None):
        g.d.line((0, FLOOR, 110, FLOOR), fill=1)
        pix.checker(g, (0, FLOOR + 2, 111, 64), 0.125)
        # 菜畦：一道垄，土上网点、垄沟
        g.d.polygon([(60, FLOOR), (63, FLOOR - 3), (106, FLOOR - 3), (109, FLOOR)], fill=1)
        pix.checker(g, (62, FLOOR - 2, 108, FLOOR), 0.5, fill=0)
        # 远处篱笆
        for x in range(58, 111, 9):
            g.d.line((x, FLOOR - 24, x, FLOOR - 14), fill=1)
            g.px(x, FLOOR - 25)
        g.d.line((56, FLOOR - 21, 110, FLOOR - 21), fill=1)
        g.d.line((56, FLOOR - 17, 110, FLOOR - 17), fill=1)
        # 桔槔：平时吊桶端翘起；风来了吱呀晃
        ang = -0.35
        if creak is not None:
            ang += math.sin(creak * 5) * 0.25 * (1 - span(creak, 2.5, 4.0))
        shadoof(g, ang)
        well(g)
        # 太阳
        g.d.ellipse((40, 4, 48, 12), outline=1)
        for a in range(0, 360, 45):
            r = math.radians(a + t * 8)
            g.px(44 + math.cos(r) * 7, 8 + math.sin(r) * 7)

    def plants(self, g: Gfx, stage: int, perk: dict, t: float):
        for i, x in enumerate(PLANTS):
            spr = PLANT[stage]
            dy = -1 if perk.get(i, 0) > 0 else 0
            sway = int(round(math.sin(t * 1.3 + i) * 0.6))
            pix.blit(g, spr, x - spr.w // 2 + sway, FLOOR - 3 - spr.h + dy)

    def trip(self, k: float, n: int):
        """一趟里的状态"""
        st = dict(x=AT_WELL, legs="stand", flip=True, hand=None, jar=None, tilt=0, face="normal", head="up",
                  pour=None, full=False, perk={}, wipe=False)
        if k < 2.0:  # 蹲下沉瓮、提上来
            st["legs"] = "kneel" if 0.2 < k < 1.8 else "stand"
            dip = math.sin(span(k, 0.4, 1.6) * math.pi)
            st["hand"] = (WELL + 4, WELL_TOP - 3 + dip * 6)
            st["jar"] = "hand" if dip < 0.5 else None
            st["full"] = k > 1.0
            return st
        st["full"] = True
        if k < 4.4:  # 抱瓮走到菜畦
            q = span(k, 2.0, 4.4)
            st.update(x=lerp(AT_WELL, PLANTS[0] - 19, ease_in_out(q)), legs="walk" if q < 1 else "stand", flip=False)
            st["hand"] = (st["x"] + 9, FLOOR - 12)
            st["jar"] = "hug"
            return st
        if k < 10.0:  # 浇三棵
            j = min(int((k - 4.4) / 1.9), 2)
            q = (k - 4.4) - j * 1.9
            px = PLANTS[j] - 19
            prev = PLANTS[j - 1] - 19 if j else px
            x = lerp(prev, px, ease_in_out(span(q, 0, 0.4))) if j else px
            st.update(x=x, legs="walk" if j and q < 0.4 else "stand", flip=False)
            tilt = span(q, 0.45, 0.75) - span(q, 1.45, 1.75)
            st["tilt"] = tilt
            st["hand"] = (x + 9, FLOOR - 12 - tilt * 2)
            st["jar"] = "hug"
            if tilt > 0.9:
                st["pour"] = (j, q - 0.75)
            for i in range(3):
                done = 4.4 + i * 1.9 + 1.2
                if k > done:
                    st["perk"][i] = max(0.0, 1 - (k - done) / 0.4)
            st["full"] = k < 9.6
            return st
        st["perk"] = {}
        if k < 13.0:  # 走回井边
            q = span(k, 10.0, 13.0)
            st.update(x=lerp(PLANTS[2] - 19, AT_WELL, ease_in_out(q)), legs="walk" if q < 1 else "stand", flip=True,
                      full=False)
            st["hand"] = (st["x"] - 9, FLOOR - 12)
            st["jar"] = "hug"
            return st
        st.update(flip=True, full=False)  # 歇口气：瓮放在脚边，擦汗
        st["jar"] = "ground"
        q = k - 13.0
        st["hand"] = keys(q, [(0, (AT_WELL - 9, FLOOR - 12)), (0.5, (AT_WELL - 13, FLOOR - 28)),
                              (0.9, (AT_WELL - 11, FLOOR - 32)), (1.3, (AT_WELL - 13, FLOOR - 28)),
                              (1.8, (AT_WELL - 9, FLOOR - 14))])
        st["face"] = "sleep" if q < 1.8 else "normal"
        st["wipe"] = q < 1.8
        return st

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        dt = self.clock.tick(t)
        n, k = cyc(t, TRIP)
        st = self.trip(k, n)
        creak = None
        if rand(n, self.s) < 0.4 and k >= 13.0:
            creak = k - 13.0
        self.scene_bg(g, t, creak)
        stage = min((n // 2) % 5, 3)
        self.plants(g, stage, st["perk"], t)
        if creak is not None:  # 看桔槔一眼、摇摇头、眯眼笑
            st["hand"] = None
            st["face"] = "wow" if creak < 1.0 else "happy"
            st["wipe"] = False
            if 1.2 < creak < 2.2:
                st["flip"] = int(creak * 8) % 2 == 0
        if st["jar"] == "ground":
            pix.blit(g, JAR, AT_WELL - 15, FLOOR - 11)

        def tool(gg, h1, h2):
            if st["jar"] == "hand" and h1:
                pix.blit(gg, JAR, h1[0] - 4, h1[1])
            elif st["jar"] == "hug" and h1:
                deg = st["tilt"] * 75 * (-1 if st["flip"] else 1)
                cx, cy = h1[0] + (-3 if st["flip"] else 3), h1[1] - 3
                blit_rot(gg, JAR, cx, cy, deg, *JAR_PIV)
                st["mouth"] = (cx + math.sin(math.radians(deg)) * 7, cy - math.cos(math.radians(deg)) * 6)

        worker(g, st["x"], FLOOR, t, hand=st["hand"], legs=st["legs"], flip=st["flip"], face=st["face"],
               head=st["head"], tool=tool)
        if st["jar"] == "hand" and k < 2.0 and st["hand"][1] > WELL_TOP:
            well(g)  # 瓮沉进井口：井沿压在瓮上
        if st["pour"] is not None and "mouth" in st:
            j, q = st["pour"]
            mx, my = st["mouth"]
            stream(g, mx + 1, my, PLANTS[j], FLOOR - 4 - PLANT[min((n // 2) % 5, 3)].h, t)
            if int(t * 10) % 3 == 0:
                self.sparks.burst(PLANTS[j] - 2, FLOOR - 5, 2, 14, up=12, life=0.35, gravity=80)
        if k < 2.0 and 1.2 < k:  # 提上来的瓮滴水
            for j in range(2):
                q = ((k - 1.2) * 2 + j * 0.5) % 1
                g.px(WELL + 1 + j * 4, WELL_TOP + 2 + q * 8)
        if st["wipe"]:
            q = (k - 13.0) % 1
            pix.blit(g, SWEAT, st["x"] - 14 - q * 6, FLOOR - 34 + q * q * 14)
        self.sparks.step(dt)
        self.sparks.draw(g, trail=False)
        bf = event(t, 53.0, 9.0, self.s + 1)
        if bf:
            self.butterfly(g, bf[1], t)
        self.matrix(g, t, stage, st)
        shy = creak is not None and creak > 1.0
        scroll(g, TEXT_X, "羞而不为" if shy else "抱瓮灌园", k=text_k, side="right")

    def butterfly(self, g: Gfx, q: float, t: float):
        lx, ly = PLANTS[1] + 1, FLOOR - 16
        if q < 3.0:
            k = q / 3.0
            x = lerp(-6, lx, ease_out(k)) + math.sin(q * 3) * 4
            y = lerp(12, ly, ease_out(k)) + math.sin(q * 7) * 3
            pix.blit(g, pix.anim(BUTTERFLY, q, 8), x - 2, y)
        elif q < 6.5:
            pix.blit(g, BUTTERFLY[0] if (q * 2) % 1 < 0.15 else BUTTERFLY[1], lx - 2, ly)
        else:
            k = q - 6.5
            pix.blit(g, pix.anim(BUTTERFLY, q, 8), lx - 2 + k * 14, ly - k * 12 + math.sin(q * 7) * 3)

    def matrix(self, g: Gfx, t: float, stage: int, st):
        """点阵：一株菜苗（随长势变大）；浇水时上面落水滴、叶子一挺"""
        h = 3 + stage
        perk = 1 if any(v > 0 for v in st["perk"].values()) else 0
        for y in range(8 - h, 8):
            g.mx_set(3, y), g.mx_set(4, y)
        for j in range(stage + 1):
            y = 7 - j * 2 - perk
            w = 1 + (j + 1) // 2 + (1 if stage == 3 else 0)
            for x in range(3 - w, 3):
                g.mx_set(x, y)
            for x in range(5, 5 + w):
                g.mx_set(x, y)
        if st["pour"] is not None:
            for x in (2, 5):
                g.mx_set(x, int(t * 10 + x) % (8 - h))
            g.mx_level = 2

    def enter(self, g: Gfx, t: float):
        """抱着空瓮从右边走过菜畦，来到井边"""
        self.clock.tick(t)
        self.scene_bg(g, t, None)
        self.plants(g, 0, {}, t)
        x = lerp(104, AT_WELL, ease_out(span(t, 0, 2.6)))

        def tool(gg, h1, h2):
            blit_rot(gg, JAR, h1[0] - 3, h1[1] - 4, 0, *JAR_PIV)
        worker(g, x, FLOOR, t, hand=(x - 9, FLOOR - 12), legs="walk" if t < 2.6 else "stand", flip=True, tool=tool)
        self.matrix(g, t, 0, dict(perk={}, pour=None))
        scroll(g, TEXT_X, "抱瓮灌园", k=span(t, 0.4, 2.4), side="right")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
