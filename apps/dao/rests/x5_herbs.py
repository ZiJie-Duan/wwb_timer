"""采药（像素风）：悬崖半腰一块石台，崖边一棵老松探向云海，远峰露尖，云海缓缓流动，偶尔一只鹤远远飞过。
小道士背着竹篓，一段 9 秒：走到石缝前跪下，举药锄刨三下（碎石溅出、屏幕一颤），伸手连根拔起，
往肩后一甩丢进背篓（篓里露出的药草越来越多），然后站起来望一会儿云。三处石缝轮流采，采过的慢慢长回来；
约四分之一的时候石缝里是一朵闪光的灵芝（拔起时一闪）。
彩蛋：约每 47 秒一团厚云从左边涌过来把他整个吞没，字换成“云深不知处”，几秒后云散。
左侧竖写“只在此山中”（贾岛《寻隐者不遇》：松下问童子，言师采药去。只在此山中，云深不知处）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import Clock, arc_pt, blit_rot, cyc, event, fade_out, scroll, worker

FLOOR = 50
TEXT_X = 3
EDGE = 98               # 石台右沿
CRACKS = (62, 74, 86)
CYC = 9.0

HOE = Sprite("""
          ###
###########.
###########.
          ###
          ####
           ###
""")
HOE_GRIP = (2, 1)

HERB = Sprite("""
  ###
  #.#
  ###
   #
##.#.##
 #.#.#
  .#.
 ##.##
  .#.
   #
""")
ROOTS = Sprite("""
   #
  #.#
 # # #
#  #  #
""")
SPROUT = Sprite("""
#.#
.#.
 #
""")
LINGZHI = Sprite("""
  #####
 #.....#
#.#####.#
#########
 .##.##.
   ##
   ##
  ####
""")

BASKET = Sprite("""
#########
#.#.#.#.#
##.#.#.##
#.#.#.#.#
 #.#.#.#
 ##.#.##
 #.#.#.#
  #.#.#
  #####
""")

PADS = [Sprite("""
   ######
 ##.#.#.###
###########
 .........
"""), Sprite("""
  #####
#########
 .......
""")]

CRANE = pix.frames("""
##      ##
 ##    ##
  #########
       #
---
     ######
 ###########
           #
""")

CHIP = [Sprite("#"), Sprite("##"), Sprite("#\n#")]


@register
class Herbs(Rest):
    id = "x5.herbs"
    name = "采药"
    desc = "悬崖石台上背篓采药：药锄刨石缝、连根拔起甩进背篓，偶得灵芝；一团云涌来把他吞没——云深不知处"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.s = self.seed * 29 + 11

    # ------------------------------------------------ 背景

    def sea(self, g: Gfx, t: float, x0: int = 19):
        """云海：一排慢慢往左流的云头，下面实心"""
        base = 46
        for i in range(-1, 10):
            w = 14
            cx = x0 + i * w - (t * 2.5) % w + 4
            r = 4 + int(rand(i + int(t * 2.5 // w), 5) * 3)
            g.d.ellipse((cx - r, base - r, cx + r, base + r), fill=1)
            g.d.arc((cx - r + 2, base - r + 2, cx + r - 1, base + r), 200, 290, fill=0)
        g.d.rectangle((x0, base, 127, 63), fill=1)
        for i in range(8):  # 云海里几道流动的暗纹
            y = base + 4 + (i % 4) * 4
            x = (i * 23 - t * 4 * (1 + i % 3)) % 120 + x0
            g.d.line((x, y, x + 6, y), fill=0)

    def backdrop(self, g: Gfx, t: float):
        # 远峰（露出云海的山尖）
        g.d.polygon([(100, 46), (110, 22), (114, 28), (118, 18), (127, 34), (127, 46)], fill=0, outline=1)
        g.d.line((110, 22, 108, 30), fill=1)
        g.d.line((118, 18, 120, 26), fill=1)
        cr = event(t, 31.0, 7.0, self.s + 4)
        if cr:  # 鹤远远飞过
            q = cr[1] / 7.0
            pix.blit(g, pix.anim(CRANE, cr[1], 3), lerp(130, 10, q), 8 + math.sin(q * 6) * 2)
        for i in range(3):  # 石台后面远远几缕云
            y = 8 + i * 6
            x = 22 + (i * 31 + t * (1.5 + i * 0.5)) % 60
            g.d.line((x, y, x + 9 - i * 2, y), fill=1)
            g.d.line((x + 3, y - 1, x + 6, y - 1), fill=1)
        self.sea(g, t, EDGE - 8)

    def cliff(self, g: Gfx, t: float):
        # 石台：顶面一道线，石块缝、崖壁暗纹
        g.d.polygon([(19, FLOOR), (EDGE, FLOOR), (EDGE + 3, FLOOR + 3), (EDGE, 58), (EDGE + 2, 63), (19, 63)],
                    fill=0, outline=1)
        g.d.line((19, FLOOR, EDGE, FLOOR), fill=1)
        pix.checker(g, (20, FLOOR + 6, EDGE - 1, 64), 0.125)
        for x, y, l in ((30, 53, 6), (52, 55, 9), (70, 52, 5), (84, 56, 7), (40, 59, 6)):
            g.d.line((x, y, x + l, y), fill=1)
            g.d.line((x + l, y, x + l + 1, y + 2), fill=1)
        # 老松：从石台右沿斜伸向云海
        g.d.line((EDGE - 3, FLOOR, EDGE + 2, 36), fill=1, width=3)
        g.d.line((EDGE + 2, 36, EDGE + 10, 24), fill=1, width=2)
        g.d.line((EDGE + 1, 40, EDGE + 12, 36), fill=1, width=2)
        g.d.line((EDGE - 1, 44, EDGE - 1, 46), fill=0)
        sway = int(round(math.sin(t * 0.8)))
        pix.blit(g, PADS[0], EDGE + 3 + sway, 18)
        pix.blit(g, PADS[1], EDGE + 9 + sway, 31)
        pix.blit(g, PADS[1], EDGE - 9, 24)
        g.d.line((EDGE - 1, 30, EDGE + 3, 34), fill=1)

    # ------------------------------------------------ 一段采药

    def state(self, k: float, n: int):
        j = n % 3
        cx = CRACKS[j]
        spot = cx - 14
        prev = CRACKS[(n - 1) % 3] - 14
        st = dict(x=spot, legs="stand", hand=None, hoe=None, face="normal", pull=None, toss=None, hit=None,
                  up=False)
        if k < 1.0:
            q = ease_in_out(k)
            st["x"] = lerp(prev, spot, q)
            st["legs"] = "walk" if 0.05 < k < 0.95 and prev != spot else "stand"
            st["flip"] = spot < prev
            st["hoe"] = ((st["x"] + 9, FLOOR - 13), -60)
            return st
        st["flip"] = False
        if k < 3.5:  # 跪下，刨三下
            st["legs"] = "kneel" if k > 1.15 else "stand"
            if k < 1.4:
                st["hoe"] = ((spot + 9, FLOOR - 11), -60)
            else:
                q = ((k - 1.4) % 0.7) / 0.7
                up = ((spot + 6, FLOOR - 24), -100)
                down = ((spot + 10, FLOOR - 10), 15)
                if q < 0.55:
                    a = ease_in_out(q / 0.55)
                    st["hoe"] = ((lerp(down[0][0], up[0][0], a), lerp(down[0][1], up[0][1], a)),
                                 lerp(down[1], up[1], a))
                    st["up"] = a > 0.6
                else:
                    a = span(q, 0.55, 0.75)
                    st["hoe"] = ((lerp(up[0][0], down[0][0], a), lerp(up[0][1], down[0][1], a)), lerp(up[1], down[1], a))
                    if q >= 0.75:
                        st["hit"] = q - 0.75
            return st
        if k < 4.4:  # 伸手拔
            st["legs"] = "kneel"
            q = span(k, 3.5, 4.4)
            st["hand"] = (cx - 1, FLOOR - 4 - ease_out(span(q, 0.4, 1)) * 7)
            st["pull"] = span(q, 0.4, 1)
            st["hoe_ground"] = True
            return st
        if k < 5.2:  # 往肩后一甩
            q = span(k, 4.4, 5.2)
            st["hand"] = (lerp(cx - 1, spot - 2, ease_out(q)), lerp(FLOOR - 11, FLOOR - 34, ease_out(q)))
            st["toss"] = q
            st["hoe_ground"] = True
            st["up"] = q > 0.4
            return st
        st["hoe"] = ((spot + 9, FLOOR - 13), -60)   # 望云
        st["face"] = "happy" if k < 6.5 else "normal"
        return st

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        dt = self.clock.tick(t)
        n, k = cyc(t, CYC)
        st = self.state(k, n)
        self.backdrop(g, t)
        self.cliff(g, t)
        j = n % 3
        ling = rand(n, self.s) < 0.25
        for i, cx in enumerate(CRACKS):  # 石缝里的草药
            g.d.line((cx - 3, FLOOR, cx + 3, FLOOR), fill=0)
            g.px(cx - 2, FLOOR + 1), g.px(cx + 1, FLOOR + 1), g.px(cx, FLOOR + 2)
            if i == j:
                if st["pull"] is None and st["toss"] is None and k < 4.0:
                    spr = LINGZHI if ling else HERB
                    pix.blit(g, spr, cx - spr.w // 2, FLOOR - spr.h)
                    if ling and int(t * 4) % 3 == 0:
                        g.px(cx + 5, FLOOR - 9), g.px(cx - 5, FLOOR - 6)
            elif i == (n - 1) % 3:
                pix.blit(g, SPROUT, cx - 1, FLOOR - 3)
            else:
                pix.blit(g, HERB, cx - 3, FLOOR - HERB.h)
        in_basket = min(1 + (n % 8) // 2 + (1 if st["toss"] is not None and st["toss"] > 0.8 or k > 5.2 else 0), 4)

        def back(gg, h1, h2):
            bx = st["x"] - 15 if not st.get("flip") else st["x"] + 6
            by = FLOOR - 20 + (3 if st["legs"] == "kneel" else 0)
            for i in range(in_basket):  # 篓口露出的药草
                hx = bx + 2 + i * 2
                gg.d.line((hx, by, hx - 1 + (i % 2) * 2, by - 3 - (i % 2)), fill=1)
                gg.px(hx - 1, by - 4 - (i % 2))
            pix.blit(gg, BASKET, bx, by)
            if st["hoe"] is not None and st["up"]:
                (hx, hy), deg = st["hoe"]
                blit_rot(gg, HOE, h1[0] if h1 else hx, h1[1] if h1 else hy, deg, *HOE_GRIP)

        def tool(gg, h1, h2):
            if st["hoe"] is not None and not st["up"]:
                (hx, hy), deg = st["hoe"]
                blit_rot(gg, HOE, h1[0], h1[1], deg, *HOE_GRIP)
            if st["pull"] is not None and h1:
                spr = LINGZHI if ling else HERB
                pix.blit(gg, spr, h1[0] - spr.w // 2 + 1, h1[1] - spr.h + 2)
                if st["pull"] > 0.3:
                    pix.blit(gg, ROOTS, h1[0] - 2, h1[1] + 2)

        hand = st["hand"] if st["hand"] is not None else (st["hoe"][0] if st["hoe"] else None)
        if st.get("hoe_ground"):
            blit_rot(g, HOE, st["x"] + 6, FLOOR - 1, 170, *HOE_GRIP)
        worker(g, st["x"], FLOOR, t, hand=hand, legs=st["legs"], flip=st.get("flip", False), face=st["face"],
               tool=tool, back_tool=back, fist=st["hoe"] is not None, behind_head=st["up"],
               bob=st["legs"] == "stand")
        if st["toss"] is not None and 0.5 < st["toss"] < 1.0:  # 甩过肩的药草
            q = span(st["toss"], 0.5, 1.0)
            x, y = arc_pt((st["x"] - 2, FLOOR - 36), (st["x"] - 11, FLOOR - 30), q, 6)
            pix.blit(g, HERB if not ling else LINGZHI, x - 3, y - 4)
        for m in range(3):  # 每一锄：碎石溅出
            if self.clock.crossed(t, t - k + 1.4 + m * 0.7 + 0.525):
                self.sparks.burst(CRACKS[j] - 2, FLOOR - 1, 7, 26, up=18, life=0.5, gravity=110)
        if st["hit"] is not None and st["hit"] < 0.08:
            pix.shake(g, t, 0.8, seed=2)
        if ling and st["pull"] is not None and 0.3 < st["pull"] < 0.6:
            pix.flash(g)
        self.sparks.step(dt)
        for x, y, vx, vy, age, life, grav in self.sparks.p:
            pix.blit(g, CHIP[int(x) % 3], x, y, outline=False)
        cloud = event(t, 47.0, 9.0, self.s + 2)
        if cloud:
            self.engulf(g, cloud[1], t)
        self.matrix(g, t, st, ling, cloud)
        deep = cloud is not None and 2.0 < cloud[1] < 8.0
        scroll(g, TEXT_X, "云深不知处" if deep else "只在此山中", y=2, k=text_k, side="left")

    def engulf(self, g: Gfx, q: float, t: float):
        """一团厚云从左边涌来，把石台上的人整个吞没，再慢慢散开"""
        front = lerp(-30, 110, ease_out(span(q, 0, 2.5)))
        thin = span(q, 6.5, 9.0)
        for i in range(14):
            cx = front - (i % 7) * 13 - (i // 7) * 6
            cy = 18 + (i // 7) * 16 + math.sin(t * 0.8 + i) * 2
            r = (9 + (i * 5) % 6) * (1 - thin * 0.9)
            if cx + r < 19 or r < 1:
                continue
            g.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=1)
            g.d.arc((cx - r + 2, cy - r + 2, cx + r - 1, cy + r - 1), 200, 280, fill=0)
        if thin < 0.5 and front > 30:
            g.d.rectangle((19, 22, min(front - 4, 110), 50), fill=1)
            for i in range(6):
                y = 26 + i * 4
                x = 22 + (i * 17 + t * 6) % 80
                if x + 6 < front:
                    g.d.line((x, y, x + 6, y), fill=0)
        g.d.rectangle((0, 0, 18, 63), fill=0)

    def matrix(self, g: Gfx, t: float, st, ling: bool, cloud):
        """点阵：一株草药（拔起时上移露出根）；灵芝；被云吞没时是流动的云"""
        if cloud and 1.0 < cloud[1] < 8.0:
            for y in range(8):
                for x in range(8):
                    g.mx[y, x] = math.sin(x * 0.9 + t * 3 + math.sin(y * 1.3 + t)) > 0.2
            return
        lift = int((st["pull"] or 0) * 3) + (3 if st["toss"] is not None else 0)
        if ling:
            rows = [0x3C, 0x7E, 0xFF, 0x18, 0x18, 0x3C]
            top = 1
        else:
            rows = [0x24, 0x5A, 0x18, 0x99, 0x5A, 0x3C]
            top = 0
        rows = rows + [0x24, 0x42] if lift else rows + [0x00, 0x00]
        for i, r in enumerate(rows):
            y = top + i - lift + 0
            if 0 <= y < 8:
                for x in range(8):
                    if r & (0x80 >> x):
                        g.mx[y, x] = True
        if ling and lift and lift < 3:
            g.mx_level = 5

    def enter(self, g: Gfx, t: float):
        """满屏的云从右往左退开，露出石台上的人；题字逐字写出"""
        self.clock.tick(t)
        self.backdrop(g, t)
        self.cliff(g, t)
        for cx in CRACKS:
            pix.blit(g, HERB, cx - 3, FLOOR - HERB.h)
        x = CRACKS[-1] - 14
        worker(g, x, FLOOR, t, hand=(x + 9, FLOOR - 13), tool=lambda gg, h1, h2: blit_rot(gg, HOE, h1[0], h1[1], -60, *HOE_GRIP),
               back_tool=lambda gg, h1, h2: pix.blit(gg, BASKET, x - 15, FLOOR - 20), fist=True, face="happy")
        q = ease_in_out(span(t, 0.2, 2.6))
        edge = lerp(0, 140, q)
        g.d.rectangle((edge + 6, 0, 128, 64), fill=1)  # 退开的云墙：边上一排云头，里面几道云纹
        for i in range(10):
            cy = i * 7
            cx = edge + (i % 3) * 4
            g.d.ellipse((cx - 8, cy - 6, cx + 8, cy + 6), fill=1)
            g.d.arc((cx - 6, cy - 4, cx + 7, cy + 5), 200, 280, fill=0)
        for i in range(9):
            x = edge + 14 + (i * 29) % 90
            y = 5 + (i * 17) % 56
            g.d.arc((x, y, x + 14, y + 8), 200, 340, fill=0)
        g.d.rectangle((0, 0, 18, 63), fill=0)
        self.matrix(g, t, dict(pull=None, toss=None), False, None)
        scroll(g, TEXT_X, "只在此山中", y=2, k=span(t, 0.5, 2.6), side="left")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
