"""劈柴（像素风）：后院木墩，小道士从圆木堆搬一段立上木墩，双手抡斧——举过头顶、一顿、劈下：
震屏、木屑四溅，两半飞开，一半落上柴垛，另一半他弯腰捡起来扔上去。
六段劈完歇一歇：袖子擦汗、解葫芦喝水、伸个懒腰；抱走整垛柴，再抱一摞新圆木回来。
彩蛋：偶尔一斧卡在木头里，连斧带木举起来再砸一次（闪白）；一只麻雀落在柴垛上啄来啄去，劈的时候吓得飞走。
右侧竖写“依乎天理”，歇的时候换成“因其固然”（《庄子·养生主》庖丁解牛：依乎天理，批大郤，导大窾，因其固然）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import (NOTE, SWEAT, Clock, arc_pt, blit_rot, cyc, event, fade_out, keys, mark, scroll, tip,
                        worker)

FLOOR = 57
DX = 40                 # 小道士站位
BX = 62                 # 木墩中心
BLOCK_TOP = FLOOR - 10
LOG_TOP = BLOCK_TOP + 3 - 14 + 1
CP = 6.0                # 劈一段
NCH = 6
REST = 22.0
BIG = NCH * CP + REST
TEXT_X = 114

# 圆木堆（端面朝外，精灵左上角）：先拿上面的
SUPPLY = [(3, 48), (12, 48), (21, 48), (7, 40), (16, 40), (12, 32)]
# 柴垛：劈开的半爿，从下往上码（精灵左上角）
RICK = [(x, y) for y in (52, 47, 42) for x in (76, 84, 92, 100)]

# ---------------------------------------------------------------- 精灵（逐像素）

BLOCK = Sprite("""
     ############
   ##............##
  #..############..#
 #..##....##....##..#
 #...############...#
 ##................##
 ####################
 ##.###.####.###.##.#
 #.###.##.##.###.#..#
 ##.##.##.###.##.#.##
##.###.###.##.##.#.###
""")

LOG = Sprite("""
  ########
 #........#
#.########.#
#.###..###.#
#.########.#
##........##
############
###.###.##.#
###.##..#..#
##.###.#.#.#
##.###..##.#
##.####.##.#
###.###.##.#
 ##########
""")

HALF_L = Sprite("""
  ####
 #....
#.####
#.###.
#.####
##....
######
###.##
###.##
##.###
##.###
##.###
###.##
 #####
""")
HALF_R = HALF_L.flip()
HALVES = (HALF_L, HALF_R)
# 翻跟头的帧（预先转好：pix 的描边 / 翻转缓存按对象 id 存，不能每帧新建精灵）
SPIN_R = [HALF_R, HALF_R.rot90(-1), HALF_R.rot90(2), HALF_R.rot90(1)]
SPIN_L = [HALF_L, HALF_L.rot90(1), HALF_L.rot90(2), HALF_L.rot90(3)]

END = Sprite("""
  #####
 #.....#
#..###..#
#.#...#.#
#.#.#.#.#
#.#...#.#
#..###..#
 #.....#
  #####
""")

PIECE = Sprite("""
  ####
 #....#
#..##..#
#.#..#.#
########
""")

AXE = Sprite("""
            ####
           ######
################.#
#.##############.#
           #######
           ########
          #########
          #.......#
          #########
""")
AXE_GRIP = (2, 2)       # 握点（柄尾往里一点）

GOURD = Sprite("""
  .#.
  ###
 #####
 ##.##
  ###
 #####
######.
###.###
 #####
""")

SPARROW = pix.frames("""
  ##
 #.##
####.#
 #####
  ###
  # #
---
  ##
 #.##
 ##.##
 #####
  ###.
  # #
---
#     #
##   ##
 #.##.
 ####
  ##
""")

HAT = Sprite("""
     #
    ###
   #.#.#
  ##.#.##
 #.#.#.#.#
###########
 .........
""")

CHIPS = [Sprite("##"), Sprite("#\n#"), Sprite("#.\n.#"), Sprite("#")]

AXE_REST = ((51, 42), 105)            # 斧靠在木墩左边：握点、角度
AXE_HIGH = ((DX - 3, FLOOR - 37), -160)
AXE_HIT = ((49, 29), 10)
AXE_STUCK = ((49, 31), 10)
AXE_BITE = ((49, 40), 10)
AXE_SHOULDER = ((DX + 9, FLOOR - 15), -75)   # 入场时提在手里
MX_AXE = [0x00, 0x0E, 0x1F, 0x3F, 0x26, 0x40, 0x80, 0x00]


def axe(g: Gfx, x, y, deg):
    blit_rot(g, AXE, x, y, deg, *AXE_GRIP)


def edge(x, y, deg):
    """斧刃中点"""
    return tip(x, y, deg, 14, 6.5)


# ---------------------------------------------------------------- 场景

@register
class Chop(Rest):
    id = "x5.chop"
    name = "劈柴"
    desc = "后院劈柴：搬木、抡斧、一顿、劈下，木屑飞溅、两半飞上柴垛；劈完擦汗喝水，再扛一捆回来"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.s = self.seed * 7 + 3

    # ------------------------------------------------ 背景与堆

    def yard(self, g: Gfx):
        # 院墙：瓦檐一排筒瓦，墙面几道砖缝，墙根石条
        g.d.line((0, 12, 109, 12), fill=1)
        for x in range(0, 110, 5):
            g.d.rectangle((x, 13, x + 3, 15), fill=1)
            g.px(x + 1, 14, 0)
        g.d.line((0, 17, 109, 17), fill=1)
        # 墙上一扇小格窗、木钉上挂着斗笠
        g.d.rectangle((8, 22, 25, 35), outline=1)
        g.d.rectangle((10, 24, 23, 33), outline=1)
        for x in (14, 19):
            g.d.line((x, 24, x, 33), fill=1)
        g.d.line((10, 28, 23, 28), fill=1)
        g.d.line((8, 36, 25, 36), fill=1)
        pix.blit(g, HAT, 82, 22)
        g.d.line((0, FLOOR - 5, 109, FLOOR - 5), fill=1)
        pix.checker(g, (0, FLOOR - 4, 110, FLOOR), 0.125)
        g.d.line((0, FLOOR, 109, FLOOR), fill=1)
        for x in range(-6, 110, 11):  # 地上散的木屑
            g.d.line((x, FLOOR + 3, x + 2, FLOOR + 3), fill=1)
            g.px(x + 6, FLOOR + 5)
        g.d.rectangle((74, 38, 75, FLOOR - 1), fill=1)   # 柴垛两头的木桩
        g.d.rectangle((108, 38, 109, FLOOR - 1), fill=1)

    def supply(self, g: Gfx, n: int, drop: float = 1.0):
        for i, (x, y) in enumerate(SUPPLY[:n]):
            pix.blit(g, END, x, y - (1 - drop) * (8 + i * 3))

    def rick(self, g: Gfx, n: int):
        for x, y in RICK[:n]:
            pix.blit(g, PIECE, x, y)

    # ------------------------------------------------ 一段劈柴

    def chop_state(self, k: float, idx: int, stuck: bool) -> dict:
        st = dict(hand=None, hand2=None, legs="stand", flip=False, head="up", face="normal", axe=AXE_REST,
                  held=False, log=False, carry=False, halves=None, swing=None, hit=None, up=False, pick=None)
        take = SUPPLY[-1 - idx]
        if k < 1.5:  # 转身蹲下拿木头，起身立到木墩上
            if k < 0.8:
                st.update(flip=True, legs="kneel" if 0.12 < k else "stand")
                st["hand"] = keys(k, [(0.12, (DX - 6, FLOOR - 8)), (0.5, (take[0] + 5, take[1] + 4))])
                st["carry"] = k > 0.55
            else:
                st["hand"] = keys(k, [(0.8, (DX + 9, FLOOR - 15)), (1.15, (DX + 13, FLOOR - 17)),
                                      (1.42, (BX - 6, LOG_TOP + 5))])
                st["carry"] = k < 1.42
                st["log"] = not st["carry"]
            return st
        st["log"] = True
        if k < 1.9:  # 弯腰握住斧柄
            st["hand"] = keys(span(k, 1.5, 1.9), [(0, (DX + 10, FLOOR - 15)), (1, AXE_REST[0])])
            st["head"] = "bow" if k > 1.7 else "up"
            return st
        hit1 = 3.12
        if k < 3.0:  # 举过头顶，一顿
            q = ease_in_out(span(k, 1.9, 2.75))
            (x0, y0), a0 = AXE_REST
            (x1, y1), a1 = AXE_HIGH
            st["axe"] = ((lerp(x0, x1, q), lerp(y0, y1, q)), lerp(a0, a1 + 360, q))
            st["up"] = q > 0.55
            return self._grip(st)
        if k < hit1:  # 劈下
            q = ease_in(span(k, 3.0, hit1))
            st["axe"] = self._swing(q, AXE_STUCK if stuck else AXE_HIT)
            st["swing"] = q
            st["up"] = q < 0.4
            return self._grip(st)
        hit = hit1
        if stuck:  # 卡住：连斧带木举起来再砸一次
            hit = 3.7
            if k < 3.55:
                q = ease_in_out(span(k, hit1 + 0.1, 3.55))
                (x0, y0), a0 = AXE_STUCK
                (x1, y1), a1 = AXE_HIGH
                st["axe"] = ((lerp(x0, x1 + 3, q), lerp(y0, y1 + 4, q)), lerp(a0, a1 + 20, q))
                st["log"] = "axe"
                st["face"] = "wow" if k < 3.4 else "normal"
                st["up"] = q > 0.55
                return self._grip(st)
            if k < hit:
                q = ease_in(span(k, 3.55, hit))
                st["axe"] = self._swing(q, AXE_HIT, start=((AXE_HIGH[0][0] + 3, AXE_HIGH[0][1] + 4), AXE_HIGH[1] + 20))
                st["log"] = "axe"
                st["swing"] = q
                st["up"] = q < 0.4
                return self._grip(st)
        st["log"] = False
        st["hit"] = k - hit
        st["halves"] = k - hit
        if k < hit + 0.5:  # 斧刃咬在木墩上
            st["axe"] = AXE_BITE
            return self._grip(st)
        if k < hit + 1.1:  # 晃两下拔出来，靠回木墩
            q = span(k, hit + 0.5, hit + 1.1)
            (x0, y0), a0 = AXE_BITE
            (x1, y1), a1 = AXE_REST
            if q < 0.45:
                st["axe"] = ((x0, y0 - 1), a0 + math.sin(q * 40) * 8)
                return self._grip(st)
            qq = ease_in_out(span(q, 0.45, 1))
            st["axe"] = ((lerp(x0, x1, qq), lerp(y0, y1, qq) - math.sin(qq * math.pi) * 4), lerp(a0, a1, qq))
            return self._grip(st, two=False)
        q = k - (hit + 1.1)   # 弯腰捡起左半爿，扔上柴垛
        st["pick"] = q
        left = (BX - 13, FLOOR - 4)
        if q < 0.45:
            st["head"] = "bow" if q > 0.15 else "up"
            st["hand"] = keys(q, [(0, (DX + 10, FLOOR - 15)), (0.4, left)])
        elif q < 0.95:
            st["hand"] = keys(q, [(0.45, left), (0.7, (DX + 6, FLOOR - 24)), (0.82, (DX + 10, FLOOR - 34)),
                                  (0.95, (DX + 13, FLOOR - 28))], ease=ease_out)
        else:
            st["face"] = "happy" if q < 1.5 else "normal"
        return st

    @staticmethod
    def _grip(st, two=True):
        (gx, gy), deg = st["axe"]
        st["held"] = True
        st["hand"] = (gx, gy)
        if two:
            st["hand2"] = tip(gx, gy, deg, 4)
        return st

    @staticmethod
    def _swing(q, end, start=AXE_HIGH):
        (x0, y0), a0 = start
        (x1, y1), a1 = end
        return ((lerp(x0, x1, q), lerp(y0, y1, q) - math.sin(q * math.pi) * 4), lerp(a0, a1, q))

    def draw_chop(self, g: Gfx, t: float, k: float, idx: int, stuck: bool):
        st = self.chop_state(k, idx, stuck)
        hv = st["halves"]
        pick = st["pick"]
        n = idx * 2 + (hv is not None and hv > 0.45) + (pick is not None and pick > 1.4)
        self.rick(g, n)
        self.supply(g, len(SUPPLY) - idx - (1 if k > 0.55 else 0))
        pix.blit(g, BLOCK, BX - 11, BLOCK_TOP)
        if st["log"] is True:
            pix.blit(g, LOG, BX - 6, LOG_TOP - (1 - span(k, 1.42, 1.5)) * 2)
        if hv is not None:
            self.draw_halves(g, hv, pick, idx)
        if not st["held"]:
            axe(g, *st["axe"][0], st["axe"][1])

        def tool(gg, h1, h2):
            if st["held"] and h1:
                deg = st["axe"][1]
                if st["swing"] is not None and st["swing"] > 0.15:  # 挥动的残影：两道弧线
                    for j, back in ((1, 0.18), (2, 0.36)):
                        pg, pa = self._swing(max(st["swing"] - back, 0), AXE_HIT)
                        e0, e1 = edge(pg[0], pg[1], pa), edge(h1[0], h1[1], deg)
                        pix.dotted(gg, e0[0], e0[1], e1[0], e1[1], step=2, phase=j)
                axe(gg, h1[0], h1[1], deg)
                if st["log"] == "axe":  # 木头卡在斧刃上
                    ex, ey = edge(h1[0], h1[1], deg)
                    pix.blit(gg, LOG, ex - 6, ey - 3)
            if st["carry"] and h1:
                pix.blit(gg, LOG, h1[0] - 5, h1[1] - 9)
            if pick is not None and 0.42 < pick < 0.8 and h1:
                pix.blit(gg, HALF_L, h1[0] - 3, h1[1] - 10)

        worker(g, DX, FLOOR, t, hand=st["hand"], hand2=st["hand2"], legs=st["legs"], flip=st["flip"],
               head=st["head"], face=st["face"], tool=tool, bob=st["legs"] == "stand" and not st["held"],
               behind_head=st["up"], fist=st["held"])
        # 打击：木屑、尘土、震屏
        t0 = t - k
        hit = 3.7 if stuck else 3.12
        if self.clock.crossed(t, t0 + hit):
            self.sparks.burst(BX, LOG_TOP + 2, 22 if stuck else 14, 40, up=26, life=0.9, gravity=110)
            for sx in (-1, 1):
                self.puffs.emit(BX + sx * 10, FLOOR - 2, vx=sx * 9, vy=-4, life=0.7, rmax=2.2, spread=2)
        if stuck and self.clock.crossed(t, t0 + 3.12):
            self.sparks.burst(BX, LOG_TOP + 2, 4, 14, up=8, life=0.4, gravity=80)
        if self.clock.crossed(t, t0 + 1.45):
            self.puffs.emit(BX - 4, BLOCK_TOP + 2, vx=-4, vy=-2, life=0.5, rmax=1.5, spread=1)
            self.puffs.emit(BX + 4, BLOCK_TOP + 2, vx=4, vy=-2, life=0.5, rmax=1.5, spread=1)
        if st["hit"] is not None and st["hit"] < 0.22:
            pix.shake(g, t, 2.0 if stuck else 1.3, seed=3)
            if stuck and st["hit"] < 0.07:
                pix.flash(g)
        if stuck and 3.12 < k < 3.3:
            pix.shake(g, t, 0.8, seed=4)
        if (not stuck and 2.75 < k < 3.0) or (stuck and 3.15 < k < 3.45):  # 一顿：一滴汗
            q = span(k, 2.75, 3.0) if not stuck else span(k, 3.15, 3.45)
            pix.blit(g, SWEAT, DX + 8, FLOOR - 36 + int(q * 4))
        return st, hit

    def draw_halves(self, g: Gfx, hv: float, pick, idx: int):
        if hv < 0.45:  # 右半：翻着跟头飞上柴垛
            dst = RICK[min(idx * 2, len(RICK) - 1)]
            q = hv / 0.45
            x, y = arc_pt((BX + 1, LOG_TOP), (dst[0], dst[1] - 9), ease_out(q), 14)
            spr = SPIN_R[int(q * 6) % 4]
            pix.blit(g, spr, x, y)
        if pick is None or pick < 0.42:  # 左半：倒在木墩左边，弹一下
            q = min(hv / 0.3, 1)
            lying = SPIN_L[1]
            if q < 1:
                x, y = arc_pt((BX - 7, LOG_TOP), (BX - 17, FLOOR - 6), q, 4)
                pix.blit(g, HALF_L if q < 0.5 else lying, x, y)
            else:
                b = abs(math.sin(min((hv - 0.3) * 9, math.pi))) * 2
                pix.blit(g, lying, BX - 17, FLOOR - 6 - b)
        elif 0.8 < pick < 1.4:  # 扔出去，在空中翻转
            q = span(pick, 0.8, 1.4)
            dst = RICK[min(idx * 2 + 1, len(RICK) - 1)]
            x, y = arc_pt((DX + 12, FLOOR - 38), (dst[0], dst[1] - 9), q, 9)
            pix.blit(g, SPIN_L[int(q * 8) % 4], x, y)

    # ------------------------------------------------ 歇一歇、换柴

    def draw_rest(self, g: Gfx, t: float, k: float):
        """k ∈ [0, REST)：擦汗 → 喝水 → 伸懒腰 → 抱走柴垛 → 扛新木回来"""
        x, legs, flip, hand, hand2, face, head, up = DX, "stand", False, None, None, "normal", "up", False
        rick_n, sup_n, sup_drop, armful, bundle = len(RICK), 0, 1.0, False, False
        if k < 2.0:  # 袖子擦汗
            hand = keys(k, [(0, (DX + 9, FLOOR - 15)), (0.4, (DX + 9, FLOOR - 29)), (0.8, (DX + 3, FLOOR - 31)),
                            (1.2, (DX + 9, FLOOR - 29)), (1.6, (DX + 3, FLOOR - 31)), (2.0, (DX + 9, FLOOR - 15))])
            face = "sleep"
        elif k < 6.0:  # 解下葫芦喝水
            q = k - 2.0
            hand = keys(q, [(0, (DX + 9, FLOOR - 15)), (0.6, (DX + 10, FLOOR - 24)), (3.4, (DX + 10, FLOOR - 24)),
                            (4.0, (DX + 9, FLOOR - 15))])
            face = "sleep" if 0.7 < q < 3.3 else "happy" if q >= 3.3 else "normal"
        elif k < 7.5:  # 伸懒腰
            q = k - 6.0
            hand = keys(q, [(0, (DX + 9, FLOOR - 15)), (0.45, (DX + 3, FLOOR - 40)), (1.05, (DX + 3, FLOOR - 40)),
                            (1.5, (DX + 9, FLOOR - 15))])
            hand2 = keys(q, [(0, (DX - 3, FLOOR - 12)), (0.45, (DX - 5, FLOOR - 39)), (1.05, (DX - 5, FLOOR - 39)),
                             (1.5, (DX - 3, FLOOR - 12))])
            up = 0.2 < q < 1.3
            face = "happy"
        elif k < 15.0:  # 去柴垛抱柴，往左走出去
            q = k - 7.5
            if q < 1.6:
                x, legs = lerp(DX, 72, ease_in_out(q / 1.6)), "walk"
            elif q < 2.6:
                x, legs = 72, "kneel"
                hand = (84, FLOOR - 7)
                rick_n = len(RICK) - int(span(q, 1.7, 2.5) * len(RICK))
            else:
                rick_n = 0
                x, legs, flip = lerp(72, -24, (q - 2.6) / 4.9), "walk", True
                armful = True
                hand = (x - 9, FLOOR - 19)
        else:  # 抱着一摞新圆木从左边回来，卸到木堆上
            q = k - 15.0
            rick_n = 0
            if q < 4.0:
                x, legs, bundle = lerp(-24, 32, ease_out(q / 4.0)), "walk", True
                hand = (x + 12, FLOOR - 12)
            elif q < 4.6:
                x, bundle, flip = 32, q < 4.3, q >= 4.3
                hand = (x + 12, FLOOR - 12) if q < 4.3 else (x - 12, FLOOR - 18)
                sup_n, sup_drop = len(SUPPLY), span(q, 4.3, 4.6)
                if q < 4.3:
                    sup_n = 0
            else:
                x = lerp(32, DX, ease_in_out(span(q, 4.6, 5.6)))
                legs = "walk" if q < 5.6 else "stand"
                sup_n = len(SUPPLY)
                face = "happy" if q > 5.6 else "normal"
            if 4.6 <= q < 4.85:
                pix.shake(g, t, 1.0, seed=5)
        self.rick(g, rick_n)
        self.supply(g, sup_n, ease_out(sup_drop))
        pix.blit(g, BLOCK, BX - 11, BLOCK_TOP)
        axe(g, *AXE_REST[0], AXE_REST[1])

        def tool(gg, h1, h2):
            if 2.0 <= k < 6.0 and h1:
                pix.blit(gg, GOURD, h1[0] - 3, h1[1] - 7)
            if bundle and h1:  # 怀里抱着一摞圆木
                for ox, oy in ((-8, -8), (-1, -8), (-4, -15)):
                    pix.blit(gg, END, h1[0] + ox, h1[1] + oy)
            if armful and h1:
                for ox, oy in ((-6, -4), (-4, -8), (-7, -12)):
                    pix.blit(gg, PIECE, h1[0] + ox, h1[1] + oy)

        worker(g, x, FLOOR, t, hand=hand, hand2=hand2, legs=legs, flip=flip, face=face, head=head, tool=tool,
               bob=legs == "stand", behind_head=up)
        if k < 2.0:  # 甩出的汗珠
            for j in range(3):
                q = (k * 1.4 + j * 0.33) % 1
                pix.blit(g, SWEAT, DX + 10 + q * 12, FLOOR - 38 + q * q * 20)
        if 2.8 < k < 5.3 and int(k * 3) % 2 == 0:  # 咕咚咕咚
            g.d.ellipse((DX + 14, FLOOR - 33, DX + 16, FLOOR - 31), outline=1)
        if self.ctx.finished and 5.6 < k < 7.6:  # 上一场圆满：哼个小曲
            mark(g, NOTE, DX + 11, FLOOR - 46 + math.sin(k * 5) * 2)

    # ------------------------------------------------ 主循环

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        dt = self.clock.tick(t)
        self.yard(g)
        n, k = cyc(t, BIG)
        hitinfo = None
        if k < NCH * CP:
            idx, kk = int(k // CP), k % CP
            stuck = rand(n * 10 + idx, self.s) < 0.2
            st, hit = self.draw_chop(g, t, kk, idx, stuck)
            hitinfo = (kk, hit, stuck)
            rick_top = RICK[idx * 2 - 1][1] if idx else FLOOR
        else:
            self.draw_rest(g, t, k - NCH * CP)
            rick_top = RICK[-1][1] if k - NCH * CP < 9.2 else FLOOR
        bird = event(t, 43.0, 8.5, self.s + 1)
        if bird and rick_top < FLOOR:
            scared = hitinfo is not None and 0 < hitinfo[0] - hitinfo[1] < 2.0
            self.sparrow(g, bird[1], rick_top, hitinfo if scared else None)
        self.sparks.step(dt)
        self.puffs.step(dt)
        for x, y, vx, vy, age, life, grav in self.sparks.p:   # 木屑：小片翻飞
            pix.blit(g, CHIPS[int(age * 12 + x) % 4], x, y, outline=False)
        self.puffs.draw(g)
        self.matrix(g, hitinfo)
        rest = k >= NCH * CP + 7.5
        scroll(g, TEXT_X, "因其固然" if rest else "依乎天理", k=text_k, side="right")

    def sparrow(self, g: Gfx, q: float, top: int, scared):
        x0 = 94
        y0 = top - 6
        if scared:  # 吓飞：往右上飞走
            q2 = scared[0] - scared[1]
            pix.blit(g, pix.anim([SPARROW[2], SPARROW[1]], q2, 14), x0 + q2 * 40, y0 - q2 * 34)
            return
        if q < 1.0:
            x, y = lerp(130, x0, ease_out(q)), lerp(4, y0, ease_out(q))
            pix.blit(g, pix.anim([SPARROW[2], SPARROW[1]], q, 12), x, y)
        elif q < 7.5:
            hop = int((q - 1) / 1.6)
            ph = ((q - 1) % 1.6) / 1.6
            x = x0 - hop * 4 - ease_in_out(span(ph, 0, 0.25)) * 4 + 4
            y = y0 - math.sin(span(ph, 0, 0.25) * math.pi) * 3
            peck = 0.4 < ph < 0.55 or 0.7 < ph < 0.85
            pix.blit(g, SPARROW[1] if peck else SPARROW[0], x, y)
        else:
            q2 = q - 7.5
            pix.blit(g, pix.anim([SPARROW[2], SPARROW[1]], q2, 12), x0 - 12 + q2 * 50, y0 - q2 * 40)

    def matrix(self, g: Gfx, s):
        """点阵：没立木头时是斧；立上木头是端面年轮；劈下一道亮缝、两半分开；歇的时候是葫芦"""
        if s is None:
            g.mx_rows([0x18, 0x18, 0x3C, 0x24, 0x18, 0x3C, 0x7E, 0x3C])
            return
        kk, hit, stuck = s
        rings = [0x3C, 0x42, 0x99, 0xA5, 0xA5, 0x99, 0x42, 0x3C]
        if kk < hit:
            g.mx_rows(MX_AXE if kk < 1.45 else rings)
            if 2.75 < kk:
                g.mx_level = 2
            return
        q = kk - hit
        if q < 0.12:  # 一道亮缝
            g.mx_rows(rings)
            g.mx[:, 3:5] = True
        else:         # 两半分开
            g.mx_rows([0x66, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0xA5, 0x66] if q < 1.2 else MX_AXE)
        if q < 0.3:
            g.mx_level = 7 if stuck else 4

    def enter(self, g: Gfx, t: float):
        """扛着斧子走进来，把斧子靠到木墩上；题字逐字出现"""
        self.clock.tick(t)
        self.yard(g)
        self.supply(g, len(SUPPLY))
        pix.blit(g, BLOCK, BX - 11, BLOCK_TOP)
        if t < 2.0:
            x = lerp(-14, DX, ease_out(t / 2.0))
            (gx, gy), deg = AXE_SHOULDER

            def tool(gg, h1, h2):
                axe(gg, h1[0], h1[1], deg)
            worker(g, x, FLOOR, t, hand=(x + 9, gy), legs="walk", tool=tool, fist=True)
        else:
            q = ease_in_out(span(t, 2.0, 2.7))
            if q < 1:
                (x0, y0), a0 = AXE_SHOULDER
                (x1, y1), a1 = AXE_REST
                gp = (lerp(x0, x1, q), lerp(y0, y1, q) - math.sin(q * math.pi) * 3)
                deg = lerp(a0, a1, q)

                def tool(gg, h1, h2):
                    axe(gg, h1[0], h1[1], deg)
                worker(g, DX, FLOOR, t, hand=gp, tool=tool)
            else:
                axe(g, *AXE_REST[0], AXE_REST[1])
                worker(g, DX, FLOOR, t)
        g.mx_rows(MX_AXE)
        scroll(g, TEXT_X, "依乎天理", k=span(t, 0.5, 2.5), side="right")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
