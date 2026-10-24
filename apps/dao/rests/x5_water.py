"""挑水（像素风）：小道士挑着扁担、两只箍了铁箍的木桶走山路。画面横向卷动：远山、松树、路边石子草茎各按视差后退，
路边轮流出现竹管引泉的石槽、山神小庙、一块大青石。扁担随步子一颤一颤，前后两只桶带着相位差晃，桶里水面跟着倾斜晃荡，
颠得狠时溅出一滴。
彩蛋：约每 47 秒一只青蛙从前桶里探出头来，他头上冒个感叹号，青蛙“噗”地跳到路上，被甩在身后；
约每 71 秒一只小鸟落在后扁担头上搭一段顺风车，啄两下又飞走。
右侧竖写“上善若水”（《道德经》八章：上善若水，水善利万物而不争）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_out, lerp, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import BANG, Clock, event, fade_out, mark, scroll, worker

FLOOR = 55
DX = 52
TEXT_X = 114
STAGE = 110
SPEED = 13.0
POLE = 21                # 扁担半长
ROPE = 9

BUCKET = Sprite("""
   #####
   #   #
  ##   ##
###########
#.........#
###########
#.##.#.##.#
#.##.#.##.#
###########
#.##.#.##.#
 #########
""")

PINE = Sprite("""
    #
   ###
  #.#.#
   ###
  #####
 #.#.#.#
  #####
 #######
#.#.#.#.#
 #######
    #
    #
   ###
""")

ROCK = Sprite("""
     ######
   ##......##
  #..#####...#
 #.##.....##..#
#.#..........#.#
#..#.#.......#.#
#...........#..#
################
""")

SHRINE = Sprite("""
     #####
  ###########
#####.....#####
  #.........#
  #.#######.#
  #.#.....#.#
  #.#.###.#.#
  #.#.#.#.#.#
  ###########
 #############
""")

SPRING = Sprite("""
##
##########
##.......
##
##
##
##    ##########
##    #........#
##    ##########
##     #.#  #.#
""")

FROG = pix.frames("""
 #.#
#####
#.#.#
---
 #.# .
##### .
 ####
#   #
---
#.#
###
""")

BIRD = pix.frames("""
  ##
 #.##
####.#
 ####
  # #
---
#     #
##   ##
 #.##.
 ####
""")

DROP = Sprite("#\n#")

CLOUD = Sprite("""
    ####
 ###....##
#..........#
 ##########
""")


def ridge(x: float) -> int:
    return int(14 + 6 * math.sin(x * 0.045) + 3 * math.sin(x * 0.11 + 1.3))


@register
class Water(Rest):
    id = "x5.water"
    name = "挑水"
    desc = "挑着扁担两只木桶走山路：远山松树往后退，扁担一颤一颤、桶里水面晃荡；青蛙从桶里跳出来，小鸟落在扁担头"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.s = self.seed * 17 + 1

    # ------------------------------------------------ 背景（视差）

    def scenery(self, g: Gfx, sc: float):
        far = sc * 0.15
        for x in range(0, STAGE, 2):  # 远山：山脊线 + 稀网点
            y = ridge(x + far)
            g.px(x, y)
            g.px(x + 1, ridge(x + 1 + far))
        for x in range(0, STAGE, 3):  # 山脊下一道阴影点、几处积雪
            y = ridge(x + far)
            g.px(x, y + 3 + (x // 3) % 2)
        for x in range(0, STAGE, 2):  # 更远的一道山（虚线）
            if (x // 2) % 2 == 0:
                g.px(x, 22 + int(4 * math.sin((x + far * 0.5) * 0.07 + 2)))
        cl = sc * 0.05
        for i in range(-1, 3):  # 云
            wx = (math.floor(cl / 70) + i) * 70
            cx = wx - cl + 20
            if -16 < cx < STAGE:
                pix.blit(g, CLOUD, cx, 3 + int(rand(int(wx), 9) * 4))
        mid = sc * 0.5
        for i in range(-1, 6):  # 中景松树
            wx = (math.floor(mid / 32) + i) * 32
            sx = wx - mid + int(rand(int(wx), 3) * 14)
            if -10 < sx < STAGE:
                pix.blit(g, PINE, sx, FLOOR - 19 - int(rand(int(wx), 4) * 4))
        # 地标：引泉石槽 / 山神庙 / 大青石
        near = sc
        for i in range(-1, 2):
            wx = (math.floor(near / 230) + i) * 230 + 120
            sx = wx - near
            if -30 < sx < STAGE + 2:
                kind = int(wx // 230) % 3
                if kind == 0:
                    pix.blit(g, SPRING, sx, FLOOR - 10)
                    for j in range(3):  # 竹管里流出的水，落进石槽
                        ph = (near * 0.0 + j) % 3
                        g.px(sx + 10 + (j % 2), FLOOR - 7 + j)
                elif kind == 1:
                    pix.blit(g, SHRINE, sx, FLOOR - 10)
                else:
                    pix.blit(g, ROCK, sx, FLOOR - 8)
        # 路面：一道线、石子、草茎
        g.d.line((0, FLOOR, STAGE, FLOOR), fill=1)
        for i in range(-1, 12):
            wx = (math.floor(near / 12) + i) * 12
            sx = wx - near
            r = rand(int(wx), 7)
            if 0 <= sx < STAGE - 2:
                if r < 0.35:
                    g.d.rectangle((sx, FLOOR + 2 + int(r * 10), sx + 2, FLOOR + 3 + int(r * 10)), fill=1)
                elif r < 0.6:
                    g.d.line((sx, FLOOR - 1, sx, FLOOR - 3), fill=1)
                    g.px(sx - 1, FLOOR - 2), g.px(sx + 1, FLOOR - 4)
                else:
                    g.px(sx, FLOOR + 3 + int(r * 6))
        pix.checker(g, (0, FLOOR + 6, STAGE, 64), 0.125)

    # ------------------------------------------------ 担子

    def load(self, g: Gfx, x: float, t: float, walking: bool, frog_q=None, bird_q=None):
        """扁担与两桶（画在身后）；返回 (前桶口, 后桶口, 水面倾斜)"""
        sh_y = FLOOR - 17 - ((int(t * 8) % 4) % 2 if walking else 0)
        flex = math.sin(t * math.pi * 4 - 0.8) * 1.6 if walking else math.sin(t * 2) * 0.4
        ends = []
        for side in (1, -1):
            ex = x + side * POLE
            ey = sh_y + flex
            ends.append((ex, ey))
        # 扁担：微弯（两头往下坠）
        (fx, fy), (bx, by) = ends
        pts = [(lerp(bx, fx, k / 8), lerp(by, fy, k / 8) - math.sin(k / 8 * math.pi) * (1.5 - flex * 0.5))
               for k in range(9)]
        g.d.line(pts, fill=1, width=2)
        g.d.line((bx - 1, by - 1, bx - 1, by + 1), fill=1)
        g.d.line((fx + 1, fy - 1, fx + 1, fy + 1), fill=1)
        tops = []
        for j, (ex, ey) in enumerate(ends):
            sw = math.sin(t * 2.6 + j * 1.9) * (2.2 if walking else 0.6)
            cx, cy = ex + sw, ey + ROPE
            g.d.line((ex, ey + 1, cx - 2, cy), fill=1)       # 两股绳
            g.d.line((ex, ey + 1, cx + 2, cy), fill=1)
            pix.blit(g, BUCKET, cx - 5, cy)
            tilt = -sw * 0.5
            for k in range(1, 10):  # 水面：波光往晃的方向挤，偶尔一道浪拍到桶沿
                lit = (k + int(t * 7) + j * 2) % 4 == 0 or (tilt > 0.5 and k > 7) or (tilt < -0.5 and k < 3)
                if lit:
                    g.px(cx - 5 + k, cy + 4)
            tops.append((cx, cy + 3))
        if bird_q is not None:  # 小鸟搭在后扁担头上
            bx, by = ends[1]
            self.bird(g, bird_q, bx - 1, by - 5)
        return tops, flex

    def bird(self, g: Gfx, q: float, x, y):
        if q < 1.2:
            k = ease_out(q / 1.2)
            pix.blit(g, pix.anim(BIRD[::-1], q, 10), lerp(x - 40, x, k), lerp(y - 26, y, k))
        elif q < 7.0:
            peck = (q * 1.7) % 1 < 0.15
            pix.blit(g, BIRD[0], x - 1 + (1 if peck else 0), y + (1 if peck else 0))
        else:
            k = q - 7.0
            pix.blit(g, pix.anim(BIRD[::-1], k, 12), x + k * 30, y - k * 30)

    # ------------------------------------------------ 主循环

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        self.clock.tick(t)
        sc = t * SPEED
        self.scenery(g, sc)
        frog = event(t, 47.0, 7.0, self.s)
        bird = event(t, 71.0, 8.5, self.s + 3)
        face = "normal"
        if frog and 1.2 < frog[1] < 2.6:
            face = "wow"
        elif frog and 2.6 <= frog[1] < 4.0:
            face = "happy"
        tops = {}

        def back(gg, h1, h2):
            tp, flex = self.load(gg, DX, t, True, bird_q=bird[1] if bird else None)
            tops["t"] = tp
            tops["f"] = flex

        worker(g, DX, FLOOR, t, hand=(DX + 9, FLOOR - 18), legs="walk", back_tool=back, face=face, fist=True)
        tp = tops["t"]
        # 颠得狠时，从前桶泼出一滴
        k = t % 2.3
        if k < 0.5:
            fx, fy = tp[0]
            pix.blit(g, DROP, fx + 5 + k * 10, fy - 3 + k * k * 40, outline=False)
        if frog:
            self.frog(g, frog[1], tp[0], sc)
        self.matrix(g, t, tops["f"])
        scroll(g, TEXT_X, "上善若水", k=text_k, side="right")

    def frog(self, g: Gfx, q: float, top, sc: float):
        fx, fy = top
        if q < 1.0:  # 从桶里慢慢探出头
            pix.blit(g, FROG[2], fx - 1, fy - 1 - int(q * 2))
        elif q < 2.4:
            pix.blit(g, FROG[0], fx - 2, fy - 4)
            mark(g, BANG, DX + 10, FLOOR - 44)
        elif q < 3.2:  # 跳到路上
            k = (q - 2.4) / 0.8
            x = lerp(fx - 2, fx + 14, k)
            y = lerp(fy - 4, FLOOR - 3, k) - math.sin(k * math.pi) * 10
            pix.blit(g, FROG[1], x, y)
        else:  # 落在路上，跳两下，被甩在身后
            k = q - 3.2
            land = fx + 14 - k * SPEED
            hop = abs(math.sin(k * 3.0)) * 4 if k < 2 else 0
            pix.blit(g, FROG[1] if hop > 1 else FROG[0], land + min(k, 2) * 6, FLOOR - 3 - hop)

    def matrix(self, g: Gfx, t: float, flex: float):
        """点阵：水桶剖面，水面随晃动倾斜，水里一个亮点流动"""
        for y in range(2, 8):
            g.mx_set(0, y), g.mx_set(7, y)
        for x in range(8):
            g.mx_set(x, 7)
        tilt = math.sin(t * 2.6) * 1.2
        for x in range(1, 7):
            h = 3 + int(round((x - 3.5) / 3.5 * tilt))
            g.mx_set(x, h)
        bx = 1 + int(t * 3) % 6
        g.mx_set(bx, 5)

    def enter(self, g: Gfx, t: float):
        """挑着担子从左边走进来，题字逐字写出"""
        self.clock.tick(t)
        self.scenery(g, 0)
        x = lerp(-28, DX, ease_out(span(t, 0, 2.6)))

        def back(gg, h1, h2):
            self.load(gg, x, t, True)

        worker(g, x, FLOOR, t, hand=(x + 9, FLOOR - 18), legs="walk", back_tool=back, fist=True)
        self.matrix(g, t, 0)
        scroll(g, TEXT_X, "上善若水", k=span(t, 0.5, 2.6), side="right")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
