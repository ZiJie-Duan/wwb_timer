"""五禽戏：华佗五禽戏，虎、鹿、熊、猿、鸟依次上场，小人学着它的样子做两式。

入场：五只禽兽从右往左奔过林间空地，小人现身，“五禽戏”。
持续：一遍五戏（每戏 100 秒，两式各 50 秒）：虎举/虎扑、鹿抵/鹿奔、熊运/熊晃、猿提/猿摘、鸟伸/鸟飞。
      每戏开头那只动物从右边跑进来蹲在一旁，跟着小人一起起伏；猿摘时树上有桃，鸟飞时白鹤扇翅。
      五戏练完：动物们一齐跑过，“第几遍”加一。
中断：小人收势、动物趴下打盹（冒 z）。
恢复：动物抬头，小人接着练。
圆满：五只动物围成一圈，小人当中收势放光，“五禽戏毕”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r4_kit import blend, figure, mirror, mx_icon, pose, seq

GROUND = 60
FX = 46            # 小人
AX = 100           # 动物蹲的位置（中心）
PART = 100.0       # 一戏
INTRO = 4.0
RENEW = 4.0

TIGER = Sprite("""
 #   #
 #####                  ##
##.#.##                #  #
#######                   #
#.###.##################  #
 #####.#..#..#...#..#..####
  ###.#..#..#...#..#..###
   ######################
    ##  ##         ##  ##
    ##  ##         ##  ##
   ###  ##        ###  ##
""")
DEER = Sprite("""
  # #  # #
   # ## #
    ####
    ##.#
   ######
  ##   ##
       ###########  #
       #############
       ############
       ###     ###
       # #     # #
       # #     # #
       # #     # #
      ## #    ## #
""")
BEAR = Sprite("""
         ########
  ##   ############
 #####################
#.####################
######################
 ##.#################
  ###################
    ####  #####  ####
    ####  ####   ####
   #####  ####  #####
""")
MONKEY = Sprite("""
  ####
 #....#
 #.#.#.#
 #....#
  ####   #
  ######  #
 ## #####  #
#   ######  #
    ######  #
     ####  #
    ##  ###
   ##    ##
  ###   ###
""")
CRANE = Sprite("""
   ##
#####
   ##
    #
    #
     #
     ##
      #######
     #########
     ##########
       #######.#
         #  #
         #  #
         #  #
        ## ##
""")
PEACH = Sprite("""
  ##
 #.
###
####
 ##
""")

CLAW = dict(lh=2, rh=2)
LUNGE = dict(lth=30, lsh=5, rth=-25, rsh=-25)
SIDE = dict(shw=2.5, hipw=0.6, face=1, lth=2, lsh=0, rth=-2, rsh=0)
NN = pose(lua=-12, lfa=-8, rua=12, rfa=8)
BELLYF = pose(lua=-22, lfa=85, rua=22, rfa=-85, lh=1, rh=1)

# 动物：精灵、名、两式（关键帧、周期、式名）、点阵图标
ANIMALS = [
    (TIGER, "虎", [
        ([pose(CLAW), pose(lua=-32, lfa=160, rua=32, rfa=-160, lh=2, rh=2),
          pose(lua=-172, lfa=-178, rua=172, rfa=178, lift=1, lh=2, rh=2),
          pose(lua=-172, lfa=-178, rua=172, rfa=178, lift=1, lh=2, rh=2),
          pose(lua=-35, lfa=150, rua=35, rfa=-150, lh=1, rh=1)], 8.0, "虎举"),
        ([pose(SIDE, CLAW, lua=178, lfa=178, rua=176, rfa=176),
          pose(SIDE, CLAW, tor=55, lth=35, lsh=-15, rth=30, rsh=-18, lua=95, lfa=100, rua=92, rfa=98),
          pose(SIDE, CLAW, tor=55, lth=35, lsh=-15, rth=30, rsh=-18, lua=95, lfa=100, rua=92, rfa=98),
          pose(SIDE, CLAW, tor=10, lua=20, lfa=60, rua=15, rfa=60)], 7.0, "虎扑"),
    ], """
        #....#..
        ########
        #.#..#.#
        ########
        #.####.#
        ##.##.##
        .#....#.
        ..####..
    """),
    (DEER, "鹿", [
        ([pose(lth=-25, lsh=-6, rth=20, rsh=5),
          pose(tor=-15, tilt=-6, face=-1, lth=-25, lsh=-6, rth=20, rsh=5, lua=-120, lfa=150, rua=120, rfa=-150,
               lh=4, rh=4),
          pose(tor=-15, tilt=-6, face=-1, lth=-25, lsh=-6, rth=20, rsh=5, lua=-120, lfa=150, rua=120, rfa=-150,
               lh=4, rh=4),
          pose(lth=-20, lsh=-5, rth=25, rsh=6),
          pose(tor=15, tilt=6, face=1, lth=-20, lsh=-5, rth=25, rsh=6, lua=-120, lfa=150, rua=120, rfa=-150,
               lh=4, rh=4),
          pose(tor=15, tilt=6, face=1, lth=-20, lsh=-5, rth=25, rsh=6, lua=-120, lfa=150, rua=120, rfa=-150,
               lh=4, rh=4)], 9.0, "鹿抵"),
        ([pose(SIDE),
          pose(SIDE, LUNGE, tor=-8, lua=70, lfa=95, rua=75, rfa=100, lh=4, rh=4),
          pose(SIDE, LUNGE, tor=25, tilt=15, lua=80, lfa=90, rua=85, rfa=95, lh=4, rh=4),
          pose(SIDE, LUNGE, tor=25, tilt=15, lua=80, lfa=90, rua=85, rfa=95, lh=4, rh=4)], 7.0,
         "鹿奔"),
    ], """
        #.#..#.#
        .#....#.
        ..####..
        ..#..#..
        ..####..
        ...##...
        ..#..#..
        ........
    """),
    (BEAR, "熊", [
        ([BELLYF, pose(tor=-12, tilt=-6, lua=-30, lfa=80, rua=15, rfa=-90, lh=1, rh=1), BELLYF,
          pose(tor=12, tilt=6, lua=-15, lfa=90, rua=30, rfa=-80, lh=1, rh=1)], 6.0, "熊运"),
        ([pose(tor=-8, lth=-15, lsh=15, rth=6, rsh=2, lua=-15, lfa=-20, rua=20, rfa=10, lh=1, rh=1),
          pose(tor=0, lua=-10, lfa=-8, rua=10, rfa=8, lh=1, rh=1),
          pose(tor=8, rth=15, rsh=-15, lth=-6, lsh=-2, lua=-20, lfa=-10, rua=15, rfa=20, lh=1, rh=1),
          pose(tor=0, lua=-10, lfa=-8, rua=10, rfa=8, lh=1, rh=1)], 5.0, "熊晃"),
    ], """
        ##....##
        ########
        ########
        #.####.#
        ########
        ##.##.##
        .######.
        ..####..
    """),
    (MONKEY, "猿", [
        ([NN, pose(lua=-30, lfa=155, rua=30, rfa=-155, lh=3, rh=3, lift=3, face=-1),
          pose(lua=-30, lfa=155, rua=30, rfa=-155, lh=3, rh=3, lift=3, face=1), NN], 6.0, "猿提"),
        ([pose(lth=-10, lsh=-4, rth=20, rsh=6, lua=-120, lfa=55, rua=40, rfa=20, face=1),
          pose(lth=-10, lsh=-4, rth=20, rsh=6, lua=-120, lfa=55, rua=150, rfa=165, rh=2, face=1, lift=2),
          pose(lth=-10, lsh=-4, rth=20, rsh=6, lua=-120, lfa=55, rua=150, rfa=165, rh=1, face=1, lift=2),
          pose(lth=-6, lsh=-2, rth=8, rsh=3, lua=-25, lfa=60, rua=30, rfa=-120, rh=1, face=0)], 8.0, "猿摘"),
    ], """
        ..####..
        .#....#.
        #.#..#.#
        #......#
        .#.##.#.
        ..#..#..
        ...##...
        ........
    """),
    (CRANE, "鸟", [
        ([NN, pose(lua=-176, lfa=176, rua=176, rfa=-176, lift=1),
          pose(lua=-125, lfa=-120, rua=60, rfa=50, wing=1, lth=-40, lsh=-40, rth=0, rsh=0),
          NN,
          pose(lua=-176, lfa=176, rua=176, rfa=-176, lift=1),
          pose(lua=-60, lfa=-50, rua=125, rfa=120, wing=1, rth=40, rsh=40, lth=0, lsh=0)], 10.0, "鸟伸"),
        ([pose(lua=-30, lfa=-25, rua=30, rfa=25, wing=1),
          pose(lua=-120, lfa=-140, rua=120, rfa=140, wing=1, lth=-55, lsh=5, rth=0, rsh=0),
          pose(lua=-30, lfa=-25, rua=30, rfa=25, wing=1),
          pose(lua=-120, lfa=-140, rua=120, rfa=140, wing=1, rth=55, rsh=-5, lth=0, lsh=0)], 5.0, "鸟飞"),
    ], """
        ...##...
        ..#..#..
        ...##...
        ....#...
        .######.
        ########
        ..#..#..
        ..#..#..
    """),
]
ROUND = PART * len(ANIMALS)


@register
class Wuqinxi(Ritual):
    id = "r4.wuqinxi"
    name = "五禽戏"
    desc = "林间空地上，虎鹿熊猿鸟依次上场，小人照着禽兽的样子做虎举虎扑、鹿抵鹿奔、熊运熊晃、猿提猿摘、鸟伸鸟飞"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = ROUND + RENEW

    # ------------------------------------------------------------ 进度

    def where(self, e: float):
        """→ (遍数, 是否在“续”, 第几戏 a, 第几式 m, 本式内秒数 u, 本戏内秒数 w)"""
        n = int(e // self.CYCLE) + 1
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return n, True, 0, 0, k, k
        if e >= self.CYCLE:
            k -= RENEW
        a = min(len(ANIMALS) - 1, int(k // PART))
        w = k - a * PART
        m = 0 if w < PART / 2 else 1
        return n, False, a, m, w - m * PART / 2, w

    def pose_at(self, e: float) -> dict:
        n, renew, a, m, u, w = self.where(e)
        if renew:
            return NN
        keys, per, _ = ANIMALS[a][2][m]
        if u < INTRO:
            return blend(NN, keys[0], ease_in_out(span(u, 0.8, INTRO)))
        p = seq(keys, u - INTRO, per)
        return blend(p, NN, ease_in_out(span(u, PART / 2 - 1.8, PART / 2 - 0.3)))

    # ------------------------------------------------------------ 画面零件

    def glade(self, g: Gfx, e: float):
        d = g.d
        d.line((0, GROUND, 127, GROUND), fill=1)
        for i in range(9):  # 草
            x = 8 + i * 14 + int(rand(i, self.seed) * 6)
            d.line((x, GROUND - 1, x - 1, GROUND - 3), fill=1)
            d.line((x + 1, GROUND - 1, x + 2, GROUND - 4), fill=1)
        for x in range(2, 128, 6):
            g.px(x, GROUND + 2 + (x // 6) % 2)

    def animal(self, g: Gfx, a: int, x: float, t: float, bob: float = 0.0, sleep: float = 0.0, run: bool = False):
        spr = ANIMALS[a][0]
        y = GROUND - spr.h + 1 + bob
        if run:
            y -= abs(math.sin(t * 14)) * 2
        g.blit(spr, x - spr.w / 2, y)
        if sleep > 0:  # 打盹：冒 z
            for j in range(3):
                k = ((t * 0.7 + j / 3) % 1)
                if k < sleep:
                    g.text(x - spr.w / 2 + 2 + j * 4 + k * 6, y - 6 - k * 10, "z", size=8)

    def animal_x(self, w: float) -> float:
        """每戏开头动物跑进来；最后几秒跑出去"""
        if w < 3.0:
            return lerp(150, AX, ease_out(span(w, 0, 3.0)))
        if w > PART - 2.5:
            return lerp(AX, -40, ease_in(span(w, PART - 2.5, PART)))
        return AX

    def texts(self, g: Gfx, e: float, a: float = 1.0, right: str | None = None):
        n, renew, ai, m, u, w = self.where(e)
        left = "五禽" if renew else ANIMALS[ai][2][m][2]
        g.vtext(2, 3, left[:int(round(len(left) * a))])
        r = right if right is not None else f"第{cn_num(n)}遍"
        if a > 0:
            g.text(126, 1, r[:int(round(len(r) * a))], align="right")

    def extras(self, g: Gfx, b, p: dict, e: float, t: float):
        n, renew, a, m, u, w = self.where(e)
        if renew:
            return
        if a == 3 and m == 1:  # 猿摘：树枝上挂个桃，摘下来就在手里
            d = g.d
            d.line((22, 8, 86, 13), fill=1)
            d.line((40, 9, 46, 5), fill=1)
            d.line((70, 12, 76, 16), fill=1)
            hx, hy = b.rhand
            took = int(((u - INTRO) % 8.0) // 2) in (2, 3) and u > INTRO
            if not took:
                g.blit(PEACH, 56, 11)
            else:
                g.blit(PEACH, hx - 1, hy - 4)
        if a == 0 and m == 1 and abs(p["tor"]) > 40:  # 虎扑：扑出的风
            hx, hy = b.rhand
            for j in range(3):
                g.d.line((hx + 4 + j * 2, hy - 3 + j * 3, hx + 9 + j * 3, hy - 3 + j * 3), fill=1)

    def mx(self, g: Gfx, e: float, t: float):
        n, renew, a, m, u, w = self.where(e)
        if renew:
            a = int(t * 3) % 5
        mx_icon(g, ANIMALS[a][3])
        if not renew and int(t * 2) % 6 == 0:  # 偶尔眨眼
            g.mx[2, 2] = g.mx[2, 5] = True if a != 3 else g.mx[2, 2]

    def bob(self, e: float) -> float:
        n, renew, a, m, u, w = self.where(e)
        if renew or u < INTRO:
            return 0.0
        per = ANIMALS[a][2][m][1]
        return round(math.sin((u - INTRO) / per * 4 * math.pi))

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float, e: float):
        n, renew, a, m, u, w = self.where(e)
        self.glade(g, e)
        p = self.pose_at(e)
        if renew:  # 五只禽兽一齐跑过
            for j in range(5):
                x = lerp(150 + j * 34, -40 - (4 - j) * 0, ease_in_out(span(u, 0, RENEW))) - j * 0
                x = 150 + j * 34 - span(u, 0, RENEW) * (190 + 34 * 4)
                self.animal(g, j, x, t + j, run=True)
        else:
            self.animal(g, a, self.animal_x(w), t + a, bob=self.bob(e), run=w < 3.0 or w > PART - 2.5)
            if a == 4 and m == 1 and u > INTRO:  # 白鹤跟着扇翅
                fl = math.sin((u - INTRO) / ANIMALS[4][2][1][1] * 2 * math.pi)
                x0 = self.animal_x(w) - 1
                g.d.line((x0, GROUND - 7, x0 - 4, GROUND - 10 - fl * 5), fill=1)
                g.d.line((x0 + 2, GROUND - 7, x0 + 1, GROUND - 11 - fl * 6), fill=1)
        b = figure(g, p, FX, GROUND)
        self.extras(g, b, p, e, t)
        self.texts(g, e)
        self.mx(g, e, t)

    def enter(self, g: Gfx, t: float):
        self.glade(g, 0)
        for j in range(5):  # 五禽奔过
            x = 150 + j * 30 - t * 95
            if -40 < x < 160:
                self.animal(g, j, x, t + j, run=True)
        k = span(t, 2.4, 3.6)
        if k > 0:
            figure(g, NN, FX, GROUND)
            if k < 1:
                g.fade(ease_in_out(k), (FX - 14, 0, FX + 14, 64))
        if t > 2.4:
            typewriter(g, 74, 18, "五禽戏", t - 2.4, cps=4, align="center")
            if t > 3.8:
                g.fade(1 - span(t, 3.8, 4.5), (50, 16, 100, 31))
        self.texts(g, 0, a=span(t, 3.6, 4.5))
        mx_icon(g, ANIMALS[min(4, int(t / 0.5))][3] if t < 2.5 else ANIMALS[0][3])

    def interrupt(self, g: Gfx, t: float, e: float):
        n, renew, a, m, u, w = self.where(e)
        self.glade(g, e)
        k = ease_in_out(span(t, 0, 1.2))
        p = blend(self.pose_at(e), BELLYF, k)
        ai = a if not renew else 0
        self.animal(g, ai, AX, t, bob=round(k * 2), sleep=span(t, 0.8, 1.6))
        figure(g, p, FX, GROUND)
        self.texts(g, e, right="收势")
        self.mx(g, e, 0)

    def resume(self, g: Gfx, t: float, e: float):
        n, renew, a, m, u, w = self.where(e)
        self.glade(g, e)
        k = ease_in_out(span(t, 0.4, 1.8))
        p = blend(BELLYF, self.pose_at(e), k)
        if renew:
            self.hold(g, t, e)
            return
        x = self.animal_x(w)
        self.animal(g, a, x, t, bob=round((1 - span(t, 0, 0.6)) * 2) if x == AX else self.bob(e),
                    sleep=1 - span(t, 0, 0.5))
        b = figure(g, p, FX, GROUND)
        if k >= 1:
            self.extras(g, b, p, e, t)
        self.texts(g, e, right="收势" if t < 0.6 else None)
        self.mx(g, e, t)

    def complete(self, g: Gfx, t: float, e: float):
        self.glade(g, e)
        k = ease_in_out(span(t, 0, 1.2))
        p = blend(self.pose_at(e), BELLYF, k)
        n, renew, a, m, u, w = self.where(e)
        # 当前的动物退下，五禽从两边围上来
        if t < 1.2 and not renew:
            self.animal(g, a, lerp(self.animal_x(w), 150, ease_in(span(t, 0, 1.2))), t, run=True)
        slots = [16, 116, 41, 97, 82]  # 虎 鹿 熊 猿 鹤
        cx = 64
        for j in range(5):
            kk = ease_out(span(t, 1.0 + j * 0.3, 1.9 + j * 0.3))
            if kk <= 0:
                continue
            sx = slots[j]
            if j == 4:  # 白鹤从天上落下来
                spr = ANIMALS[4][0]
                x = lerp(140, sx, ease_out(span(t, 2.2, 3.2)))
                y = lerp(-20, GROUND - spr.h + 1, ease_out_bounce(span(t, 2.2, 3.2)))
                g.blit(spr, x - spr.w / 2, y)
                if t < 3.0:
                    fl = math.sin(t * 18) * 5
                    g.d.line((x, y + 8, x + 5, y + 4 - fl), fill=1)
                    g.d.line((x + 2, y + 8, x + 8, y + 5 - fl), fill=1)
                continue
            start = -30 if sx < 64 else 160
            self.animal(g, j, lerp(start, sx, kk), t + j, run=kk < 1)
        b = figure(g, p, cx if False else FX + (cx - FX) * ease_in_out(span(t, 0.6, 1.6)), GROUND)
        if t > 2.8:
            for j in range(12):
                aa = j / 12 * 2 * math.pi + t * 0.8
                r0 = 22
                r1 = 22 + 5 * (0.6 + 0.4 * math.sin(t * 6 + j))
                hx, hy = b.hip[0], b.hip[1] - 6
                if blink(t + j * 0.1, 0.5, 0.7):
                    g.d.line((hx + math.cos(aa) * r0, hy + math.sin(aa) * r0 * 0.8, hx + math.cos(aa) * r1,
                              hy + math.sin(aa) * r1 * 0.8), fill=1)
        if t < 1.2:
            self.texts(g, e, a=1 - span(t, 0.2, 1.2))
        else:
            typewriter(g, 64, 1, "五禽戏毕", t - 3.0, cps=5, align="center")
        i = int(t * 2.5) % 5
        mx_icon(g, ANIMALS[i][3])
        g.mx_level = 4 if t > 3.0 and t < 3.4 else 1
