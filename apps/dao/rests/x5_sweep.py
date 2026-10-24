"""扫叶（像素风）：院里一棵老银杏，扇形的叶子一片片打着旋落下来；小道士握着竹扫帚，一推一收，
把落在跟前的叶子推进右边的叶堆，叶堆越扫越高，每一推扬起一点尘土。
一轮约 70 秒：扫满一阵后起一阵风，整堆叶子卷上天——他抬袖挡脸，风过了眯眼一笑：“以至于无为”。
彩蛋：约每 37 秒一片叶子正落在他发髻上，头上冒个感叹号，他晃晃脑袋甩下来；石灯笼里偶尔爬出一只壁虎。
左侧竖写“损之又损”（《道德经》四十八章：为学日益，为道日损。损之又损，以至于无为）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import BANG, Clock, cyc, event, fade_out, mark, scroll, worker

FLOOR = 57
DX = 44
TEXT_X = 3
P = 1.8                  # 一推一收
H0, H1 = 58, 76          # 扫帚头推的起止
PILE = 86                # 叶堆中心
BIG = 72.0
SWEEP = 60.0
FALL = 2.1               # 平均几秒落一片
TRUNK = 110

LEAF = pix.frames("""
#.#.#
#####
 ###
  #
---
 ##
####
 ###.
  ##
   #
---
#####
  #
---
  #
 ###
#####
#.#.#
---
 ##
####
.###
 ##
 #
""")
GROUND_LEAF = [Sprite("#.#\n###"), Sprite("##\n.##"), Sprite("###\n.#")]

# 扫帚头（竹枝扎成一把）：推的时候枝梢往后拖，收的时候直着
BROOM = pix.frames("""
       ##
      ####
     #.##.
   ##.#.#.#
  #.#.#.#.##
 #.#.#.#.#.#
#.#.#.#.#.#.#
---
      ##
     ####
    #.##.#
   #.#.#.#
  #.#.#.#.#
 #.#.#.#.#.#
 # # # # # #
""")

BROOM_UP = BROOM[1].rot90(1)   # 扛在肩上（预先转好）

LANTERN = Sprite("""
   ###
  #####
#########
 #.....#
 #.#.#.#
 #.....#
#########
  #####
   ###
   #.#
   #.#
  #####
 #######
""")

GECKO = pix.frames("""
#   #
 ###
  ##
  ###
 #  #
---
 #  #
  ###
  ##
 ###
#   #
""")


def stroke(t: float):
    """→ (扫帚头 x, 抬起高度, 是否在推)"""
    k = (t % P) / P
    if k < 0.5:
        return lerp(H0, H1, ease_in_out(k / 0.5)), 0, True
    q = (k - 0.5) / 0.5
    return lerp(H1, H0, ease_in_out(q)), math.sin(q * math.pi) * 3, False


def leaf_fall(i: int, n: int, seed: int):
    """第 n 轮第 i 片叶：(开始落的时刻（轮内秒）, 起点 x, 落地 x, 落多久)"""
    t0 = i * FALL + rand(i + n * 100, seed) * FALL * 0.8
    i = i + n * 100
    x0 = 70 + rand(i, seed + 1) * 50
    dur = 4.5 + rand(i, seed + 2) * 2.5
    x1 = x0 - 6 - rand(i, seed + 3) * 34
    return t0, x0, x1, dur


@register
class Sweep(Rest):
    id = "x5.sweep"
    name = "扫叶"
    desc = "银杏树下扫落叶：竹扫帚一推一收，叶子扫成堆，一阵风又全卷走——损之又损，以至于无为"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.puffs = pix.Puffs(self.seed)
        self.s = self.seed * 13 + 5

    # ------------------------------------------------ 背景

    def tree(self, g: Gfx, t: float, wind: float = 0.0):
        x = TRUNK
        # 树干：根部外撇，树皮竖裂纹，一个树洞
        g.d.polygon([(x - 4, FLOOR), (x + 11, FLOOR), (x + 8, FLOOR - 3), (x + 7, 12), (x + 2, 12), (x + 1, FLOOR - 3)],
                    fill=1)
        for xx, y0, y1 in ((x + 3, 16, 27), (x + 5, 30, 44), (x + 3, 40, 52), (x + 6, 18, 24)):
            g.d.line((xx, y0, xx, y1), fill=0)
        g.d.ellipse((x + 3, 31, x + 5, 35), fill=0)
        g.d.line((x - 3, FLOOR - 1, x - 1, FLOOR - 1), fill=0)
        g.d.line((x + 2, 17, x - 10, 9), fill=1, width=2)   # 伸向左边的枝
        sway = int(round(math.sin(t * 0.9) * 0.6 + wind))
        for cx, cy, rx, ry in ((96, 6, 13, 7), (113, 4, 15, 7), (123, 11, 7, 6), (104, 11, 9, 5)):
            g.d.ellipse((cx - rx + sway, cy - ry, cx + rx + sway, cy + ry), fill=1)
        for j in range(30):                              # 扇形叶纹（挖暗）
            lx = 84 + int(rand(j, 3) * 44) + sway
            ly = int(rand(j, 4) * 14)
            g.px(lx, ly, 0), g.px(lx + 2, ly, 0), g.px(lx + 1, ly + 1, 0)
        for j, lx in enumerate(range(85, 128, 4)):       # 树冠下沿垂着一把把扇叶
            ly = 14 + int(rand(j, 6) * 3) - (2 if lx < 92 else 0)
            g.d.line((lx + sway, ly, lx + 2 + sway, ly), fill=1)
            g.px(lx + 1 + sway, ly + 1)
            g.px(lx + 1 + sway, ly - 1, 0)

    def yard(self, g: Gfx, t: float, wind: float = 0.0):
        g.d.line((19, FLOOR, 127, FLOOR), fill=1)
        for x in range(19, 128, 14):  # 石板缝
            g.d.line((x, FLOOR + 1, x - 3, 63), fill=1)
        pix.checker(g, (19, FLOOR + 2, 128, 64), 0.125)
        pix.blit(g, LANTERN, 22, FLOOR - 13)
        if int(t * 1.3) % 5:  # 灯笼里一点烛光
            g.px(26, FLOOR - 9)
        self.tree(g, t, wind)

    # ------------------------------------------------ 叶子

    def leaves(self, g: Gfx, t: float, k: float, n: int, hx: float, pushing: bool, gust: float | None):
        """k = 本轮秒数。落叶确定性计算：落在扫帚路线上的被推进叶堆。返回叶堆里的片数"""
        base = n * BIG
        pile = 0
        i0 = int(max(k - 8, 0) / FALL) - 1
        imax = int(min(k, SWEEP) / FALL) + 1
        drawn = 0
        for i in range(0, imax):
            t0, x0, x1, dur = leaf_fall(i, n, self.s)
            if t0 > SWEEP or t0 > k:
                continue
            land = t0 + dur
            if k < land:  # 还在空中：打着旋、左右摆
                if gust is not None or i < i0:
                    continue
                q = (k - t0) / dur
                x = lerp(x0, x1, q) + math.sin((k - t0) * 2.2 + i) * 4
                y = lerp(14, FLOOR - 4, q)
                pix.blit(g, pix.anim(LEAF, k - t0 + i * 0.3, 5), x - 2, y)
                drawn += 1
                continue
            # 落地了：在扫帚路线上 → 下一推推进叶堆
            if H0 - 2 <= x1 <= PILE + 6:
                if x1 >= H1 - 1:
                    pile += 1
                    continue
                # 落地后第一次“推”到它的时刻
                c = math.floor((base + land) / P)
                push_t = c * P if ((base + land) % P) / P < 0.5 else (c + 1) * P
                reach = push_t + P * 0.5 * span(x1, H0, H1) - base
                if k >= push_t + P * 0.5 - base:
                    pile += 1
                    continue
                x = max(x1, hx + 6) if (k >= reach and pushing) else x1
                if gust is None:
                    pix.blit(g, GROUND_LEAF[i % 3], x - 1, FLOOR - 2, outline=False)
            elif gust is None:
                pix.blit(g, GROUND_LEAF[i % 3], x1 - 1, FLOOR - 2, outline=False)
        return pile

    def pile(self, g: Gfx, n: int):
        if n <= 0:
            return
        h = min(2 + n // 2, 9)
        w = 6 + h * 2
        g.d.pieslice((PILE - w // 2, FLOOR - h, PILE + w // 2, FLOOR + h), 180, 360, fill=1)
        for j in range(n):  # 叶堆上的扇叶纹
            a = rand(j, 9) * math.pi
            r = rand(j, 10) * (h - 1)
            px = PILE + math.cos(a) * r * w / (2 * h)
            py = FLOOR - math.sin(a) * r
            g.px(px, py - 1, 0), g.px(px + 2, py - 1, 0), g.px(px + 1, py, 0)
        g.d.line((PILE - w // 2, FLOOR, PILE + w // 2, FLOOR), fill=1)

    # ------------------------------------------------ 主循环

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        dt = self.clock.tick(t)
        n, k = cyc(t, BIG)
        gust = (k - SWEEP) if k >= SWEEP else None
        wind = 0.0
        if gust is not None:
            wind = math.sin(span(gust, 0, 6) * math.pi) * 3
        self.yard(g, t, wind)
        hx, lift, pushing = stroke(t)
        if gust is not None and gust < 8:  # 起风：停手
            hx, lift, pushing = H0 + 4, 0, False
        p = self.leaves(g, t, k, n, hx, pushing, gust)
        if gust is not None:
            self.blow(g, gust, p)
        else:
            self.pile(g, p)
        # 小道士与扫帚
        egg = event(t, 37.0, 5.0, self.s + 2) if gust is None else None
        shake = 0
        face = "normal"
        if egg and 2.6 < egg[1] < 3.6:
            shake = 1 if int(egg[1] * 14) % 2 else -1
            face = "sleep"
        hand2 = None
        bx, by = hx, FLOOR - 1 - lift
        hand = (bx - 9, FLOOR - 13 - lift * 0.5)
        hand2 = (hand[0] - 4, hand[1] - 5)
        guard = gust is not None and 0.5 < gust < 7.5
        if guard:  # 抬袖挡风
            hand = (DX + 8, FLOOR - 27)
            hand2 = None
            face = "sleep"
            bx, by = DX + 13, FLOOR - 1
        if gust is not None and gust >= 7.5:
            face = "happy" if gust < 11 else "normal"

        def broom(gg, h1, h2):
            top = (h2 if h2 else (DX + 4, FLOOR - 30))
            if guard:
                top = (DX + 8, FLOOR - 28)
            # 竹竿：两像素宽，每隔几格一个竹节（竿子画在身后，上半截被身子挡住）
            gg.d.line((top[0] - 6, top[1] - 8, bx, by - 5), fill=1, width=2)
            for j in range(1, 4):
                qx, qy = lerp(top[0], bx, j / 4), lerp(top[1], by - 5, j / 4)
                gg.px(qx, qy, 0)
            fr = BROOM[0] if pushing and not guard else BROOM[1]
            pix.blit(gg, fr, bx - 6, by - 6)

        worker(g, DX + shake, FLOOR, t, hand=hand, hand2=hand2, back_tool=broom, face=face, fist=not guard)
        if gust is None and self.clock.crossed(t, (t - t % P) + P * 0.48):
            self.puffs.emit(H1 + 3, FLOOR - 2, vx=6, vy=-2, life=0.5, rmax=1.4, spread=2)
        self.puffs.step(dt)
        self.puffs.draw(g)
        if egg:
            self.head_leaf(g, egg[1], shake)
        if gust is not None and gust < 8:
            for j in range(7):  # 风：一道道点线往右刮
                y = 16 + j * 6 + (j % 2) * 2
                x = (gust * 90 + j * 37) % 150 - 20
                pix.dotted(g, x, y, x + 14, y, step=2, phase=j)
        gk = event(t, 53.0, 6.0, self.s + 5)
        if gk and gust is None:  # 石灯笼里爬出一只壁虎，爬上去又溜走
            q = gk[1]
            y = FLOOR - 6 - q * 6 if q < 3 else FLOOR - 24 + (q - 3) * 0
            x = 27 + (0 if q < 3 else (q - 3) * 12)
            if q < 4.5:
                pix.blit(g, pix.anim(GECKO, q, 6), x, y)
        self.matrix(g, t, k, p, gust)
        txt = "以至于无为" if gust is not None and gust > 6.5 else "损之又损"
        scroll(g, TEXT_X, txt, y=3 if len(txt) == 4 else 2, k=text_k, side="left")

    def head_leaf(self, g: Gfx, q: float, shake: int):
        top = (DX + 1, FLOOR - 36)
        if q < 1.4:
            x = lerp(DX + 20, top[0], ease_out(q / 1.4)) + math.sin(q * 5) * 3
            y = lerp(8, top[1], q / 1.4)
            pix.blit(g, pix.anim(LEAF, q, 5), x - 2, y)
        elif q < 2.6:
            pix.blit(g, LEAF[0], top[0] - 2, top[1] - 2)
            if q > 1.6:
                mark(g, BANG, DX + 10, FLOOR - 44 - (1 if q < 1.75 else 0))
        elif q < 3.6:
            pix.blit(g, LEAF[0], top[0] - 2 + shake * 2, top[1] - 2)
        elif q < 5.0:
            qq = (q - 3.6) / 1.4
            pix.blit(g, pix.anim(LEAF, q, 6), top[0] + 6 + qq * 10, lerp(top[1], FLOOR - 4, ease_out(qq)))

    def blow(self, g: Gfx, gust: float, n: int):
        """整堆叶子被风卷起来，打着旋飞出右上方"""
        left = n
        for j in range(max(n, 6)):
            d = j * 0.18
            q = gust - 0.6 - d
            if q < 0:
                continue
            left -= 1
            x = PILE - 4 + rand(j, 1) * 8 + q * (38 + rand(j, 2) * 20)
            y = FLOOR - 3 - q * (14 + rand(j, 3) * 10) + math.sin(q * 6 + j) * 4
            if x < 132 and y > -6:
                pix.blit(g, pix.anim(LEAF, q + j * 0.2, 9), x, y)
        self.pile(g, max(left, 0) if gust < 4 else 0)

    def matrix(self, g: Gfx, t: float, k: float, p: int, gust):
        """点阵：一片银杏叶左右摇着落下，落到底部的叶堆上（叶堆随片数变高）；起风时一行行横扫"""
        if gust is not None and gust < 8:
            for y in range(8):
                x0 = int(gust * 12 + y * 3) % 12 - 2
                for x in range(x0, x0 + 3):
                    g.mx_set(x, y)
            return
        h = min(1 + p // 6, 3)
        for y in range(8 - h, 8):
            w = 2 + (y - (8 - h)) * 2
            for x in range(4 - w // 2, 4 + w // 2):
                g.mx_set(x, y)
        q = (t % 4.0) / 4.0
        lx = 3 + int(round(math.sin(t * 2.5) * 2))
        ly = int(q * (8 - h))
        if ly < 8 - h:
            g.mx_set(lx - 1, ly), g.mx_set(lx + 1, ly), g.mx_set(lx, ly), g.mx_set(lx, ly + 1)

    def enter(self, g: Gfx, t: float):
        """扛着扫帚从左边走进来，放下扫帚，题字逐字写出"""
        dt = self.clock.tick(t)
        self.yard(g, t)
        x = lerp(10, DX, ease_out(span(t, 0, 2.0)))
        if t < 2.0:
            def broom(gg, h1, h2):
                gg.d.line((h1[0] + 6, h1[1] - 10, h1[0] - 12, h1[1] + 6), fill=1, width=2)
                pix.blit(gg, BROOM_UP, h1[0] + 3, h1[1] - 18)
            worker(g, x, FLOOR, t, hand=(x + 7, FLOOR - 24), legs="walk", tool=broom, fist=True)
        else:
            q = ease_in_out(span(t, 2.0, 2.8))
            bx = lerp(DX + 6, H0, q)
            by = FLOOR - 1 - (1 - q) * 14
            hand = (lerp(DX + 7, bx - 9, q), lerp(FLOOR - 24, FLOOR - 13, q))

            def broom(gg, h1, h2):
                top = (h1[0] - 4, h1[1] - 5)
                gg.d.line((top[0] - 6, top[1] - 8, bx, by - 5), fill=1, width=2)
                pix.blit(gg, BROOM[1], bx - 6, by - 6)
            worker(g, DX, FLOOR, t, hand=hand, hand2=(hand[0] - 4, hand[1] - 5), back_tool=broom, fist=True)
        self.matrix(g, t, 0, 0, None)
        scroll(g, TEXT_X, "损之又损", k=span(t, 0.4, 2.6), side="left")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
