"""喂鸡（像素风）：院角竹篱、鸡舍，小道士端着葫芦瓢，抓一把谷子往后一蓄、一扬，谷粒成弧撒在地上；
三只母鸡一只公鸡各奔离自己近的谷粒，一粒粒啄（头一点一点），啄到哪粒哪粒就没了；吃完左右张望、刨两下地，
一轮快完时溜达到下一轮的位置。
彩蛋：约每 37 秒公鸡伸脖子打鸣（声波一圈圈）；约每 61 秒公鸡忽然定住不动，头上慢慢冒出三个点，
字换成“望之似木鸡”，过一阵才回过神来。
左侧竖写“鸡犬相闻”（《道德经》八十章“鸡犬之声相闻”；《庄子·达生》纪渻子养斗鸡“望之似木鸡矣，其德全矣”）。
"""
from __future__ import annotations

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import Clock, arc_pt, cyc, event, fade_out, keys, scroll, worker

FLOOR = 56
TEXT_X = 3
DX = 34
R = 11.0                 # 一轮
NG = 9                   # 一把撒几粒
SPEED = 16.0
PECK = 0.7

HEN = pix.frames("""
         #.#
        #####
       ###.##
       ########
#      #####.#
##    ######
###.#########
##.##.#######
#.##.##.####
 ##.......##
  #########
    #   #
    #   #
   ##  ##
---
         #.#
        #####
       ###.##
       ########
#      #####.#
##    ######
###.#########
##.##.#######
#.##.##.####
 ##.......##
  #########
    #  #
   #    #
  ##    ##
---





#
##
###.#######
##.##.######
#.##.##.##### #.#
 ##.......#######
  ##########.###.
    #   #   ####
    #   #     .
   ##  ##
""")

ROOSTER = pix.frames("""
          #.#.#
          #####
         ###.##
         ########
 ##      #####.#
#..#    ######
#.#.#   #####
 #.#.#.######
#.#.#.#######
 #.#.##.#####
  ##.#......##
   ##########
     #   #
     #   #
    ##  ##
---
          #.#.#
          #####
         ###.##
         ########
 ##      #####.#
#..#    ######
#.#.#   #####
 #.#.#.######
#.#.#.#######
 #.#.##.#####
  ##.#......##
   ##########
     #  #
    #    #
   ##    ##
---





#
##
###.#######
##.##.######
#.##.##.##### #.#
 ##.......#######
  ##########.###.
    #   #   ####
    #   #     .
   ##  ##
---
            #.#.#
            #####
           ###.## ##
           ######.#
 ##        #####
#..#      #####
#.#.#   ######
 #.#.#.######
#.#.#.#######
 #.#.##.#####
  ##.#......##
   ##########
     #   #
     #   #
    ##  ##

""")

LADLE = Sprite("""
#......#
 ######.##
  ####   ##
""")

COOP = Sprite("""
      #####
    ##.....##
  ##.#######.##
##.###########.##
 ##############
 #.....##.....#
 #.###.##.###.#
 #.#.#.##.#.#.#
 #.###.##.###.#
 #.....##.....#
 #....####....#
 ##############
""")

BOWL = Sprite("""
#.......#
 #######
""")


def chick_plan(n: int, seed: int):
    """第 n 轮：谷粒位置、每只鸡的起点，以及每只鸡吃哪几粒（按就近排）"""
    grains = [50 + (i + rand(n * 31 + i, seed)) * 54 / NG for i in range(NG)]
    slots = sorted(range(4), key=lambda c: rand(n * 7 + c, seed + 2))
    homes = [52 + slots[c] * 16 + (rand(n * 7 + c, seed + 1) - 0.5) * 6 for c in range(4)]
    left = list(range(NG))
    order = {c: [] for c in range(4)}
    pos = list(homes)
    for step in range(NG):  # 轮流：每只鸡挑离自己最近的一粒
        c = step % 4
        if not left:
            break
        i = min(left, key=lambda i: abs(grains[i] - pos[c]))
        left.remove(i)
        order[c].append(i)
        pos[c] = grains[i]
    return grains, homes, order


@register
class Hens(Rest):
    id = "x5.hens"
    name = "喂鸡"
    desc = "端着葫芦瓢撒谷子，三只母鸡一只公鸡跑来一粒粒啄；公鸡伸脖子打鸣，或者定住成了木鸡"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.s = self.seed * 37 + 5
        self._plans: dict = {}

    def plan(self, n):
        p = self._plans.get(n)
        if p is None:
            if len(self._plans) > 6:
                self._plans.clear()
            p = self._plans[n] = chick_plan(n, self.s)
        return p

    # ------------------------------------------------ 背景

    def yard(self, g: Gfx, t: float):
        for x in range(21, 100, 8):  # 竹篱
            g.d.line((x, FLOOR - 30, x, FLOOR - 18), fill=1)
            g.px(x, FLOOR - 31)
            g.px(x, FLOOR - 24, 0)
        g.d.line((19, FLOOR - 27, 99, FLOOR - 27), fill=1)
        g.d.line((19, FLOOR - 21, 99, FLOOR - 21), fill=1)
        pix.blit(g, COOP, 108, FLOOR - 12)
        g.d.line((106, FLOOR, 112, FLOOR - 4), fill=1)    # 斜坡
        g.d.line((19, FLOOR, 127, FLOOR), fill=1)
        pix.checker(g, (19, FLOOR + 2, 128, 64), 0.125)
        pix.blit(g, BOWL, 98, FLOOR - 2)
        g.d.line((99, FLOOR - 2, 105, FLOOR - 2), fill=1)
        if int(t * 1.5) % 4 == 0:
            g.px(101 + int(t * 3) % 4, FLOOR - 3)

    # ------------------------------------------------ 鸡

    def chicken(self, c: int, n: int, k: float):
        """第 c 只鸡在第 n 轮第 k 秒：(x, 朝右?, 动作 stand/walk/peck, 吃掉的谷粒 {i: 时刻})"""
        grains, homes, order = self.plan(n)
        nxt = self.plan(n + 1)[1]
        x = homes[c]
        face = rand(n * 5 + c, self.s + 9) > 0.5
        eaten = {}
        tt = 2.7 + c * 0.15
        if k < tt:  # 撒之前：张望、偶尔啄地
            ph = (k + c) % 3.0
            return x, face, ("peck" if 1.0 < ph < 1.35 else "stand"), eaten
        for i in order[c]:
            gx = grains[i]
            walk = abs(gx - 3 - x) / SPEED if gx > x else abs(gx + 3 - x) / SPEED
            tx = gx - 3 if gx > x else gx + 3
            if k < tt + walk:
                q = (k - tt) / max(walk, 1e-3)
                return lerp(x, tx, q), tx > x, "walk", eaten
            face = tx > x if abs(tx - x) > 0.5 else face
            x = tx
            tt += walk
            if k < tt + PECK:
                ph = (k - tt) / PECK
                return x, face, ("peck" if ph % 0.5 < 0.3 else "stand"), eaten
            tt += PECK
            eaten[i] = tt
        if k < R - 1.6:
            ph = (k + c * 0.7) % 2.2
            act = "peck" if 0.6 < ph < 0.9 else "stand"
            if 1.4 < ph < 1.6:
                face = not face  # 左右张望
            return x, face, act, eaten
        q = span(k, R - 1.6, R)
        tx = nxt[c]
        return lerp(x, tx, ease_in_out(q)), tx > x if abs(tx - x) > 1 else face, "walk" if abs(tx - x) > 1 else "stand", eaten

    def draw_chicken(self, g: Gfx, c: int, x: float, face: bool, act: str, t: float, crow=None, frozen=False):
        fr = ROOSTER if c == 0 else HEN
        if c == 0 and crow is not None:
            spr = fr[3]
        elif frozen:
            spr = fr[0]
        elif act == "walk":
            spr = fr[int(t * 8 + c) % 2]
        elif act == "peck":
            spr = fr[2]
        else:
            spr = fr[0]
        pix.blit(g, spr, x - spr.w // 2, FLOOR - spr.h, flip=not face)
        return spr

    # ------------------------------------------------ 主循环

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        self.clock.tick(t)
        n, k = cyc(t, R)
        self.yard(g, t)
        grains, homes, order = self.plan(n)
        crow = event(t, 37.0, 3.0, self.s + 1)
        wood = event(t, 61.0, 12.0, self.s + 2)
        states = [self.chicken(c, n, k) for c in range(4)]
        eaten = {}
        for st in states:
            eaten.update(st[3])
        # 地上的谷粒（落地后才画；被啄掉就没了）
        if k > 2.5:
            for i, gx in enumerate(grains):
                if i not in eaten:
                    g.px(gx, FLOOR - 1)
                    if i % 3 == 0:
                        g.px(gx + 1, FLOOR - 1)
        # 鸡（按 y 不分前后，后画的在前）
        rooster = None
        for c in (1, 2, 3, 0):
            x, face, act, _ = states[c]
            frozen = False
            if c == 0 and wood:
                q = wood[1]
                fx, fface, _, _ = self.chicken(0, n, k - q) if k - q >= 0 else (x, face, None, None)
                if q < 10.0:
                    x, face, frozen = fx, fface, True
                else:
                    x = lerp(fx, x, ease_in_out(span(q, 10.0, 12.0)))
            spr = self.draw_chicken(g, c, x, face, act, t, crow[1] if (c == 0 and crow and not wood) else None,
                                    frozen)
            if c == 0:
                rooster = (x, face, spr, frozen)
        # 小道士：抓、蓄、扬
        hand, face, fling = self.toss(k)

        def tool(gg, h1, h2):
            pix.blit(gg, LADLE, DX + 3, FLOOR - 15)
            if fling is not None and h1 and fling < 0.25:
                gg.px(h1[0] + 1, h1[1] - 1), gg.px(h1[0] - 1, h1[1])

        worker(g, DX, FLOOR, t, hand=hand, face=face, tool=tool, fist=fling is None and 0.3 < k < 1.6)
        if fling is not None:  # 谷粒成弧飞出去
            for i, gx in enumerate(grains):
                q = span(fling, i * 0.03, 0.6 + i * 0.03)
                if 0 < q < 1:
                    x, y = arc_pt((DX + 14, FLOOR - 26), (gx, FLOOR - 1), q, 9 + (i % 3) * 2)
                    g.px(x, y)
        # 公鸡：打鸣的声波 / 木鸡的三个点
        rx, rface, rspr, frozen = rooster
        top = FLOOR - rspr.h
        if crow and not wood:
            q = crow[1]
            bx = rx + (6 if rface else -6)
            for j in range(3):
                r = ((q * 1.6 + j / 3) % 1) * 12 + 2
                if q < 2.4:
                    a0, a1 = (-60, 10) if rface else (170, 240)
                    g.d.arc((bx - r, top - r + 1, bx + r, top + r + 1), a0, a1, fill=1)
        if wood and wood[1] < 10.0:
            dots = min(int(wood[1] / 1.2), 3)
            for j in range(dots):
                g.d.rectangle((rx - 4 + j * 3, top - 5, rx - 3 + j * 3, top - 4), fill=1)
        self.matrix(g, t, k, crow and not wood, wood is not None and wood[1] < 10)
        txt = "望之似木鸡" if wood and 3.6 < wood[1] < 11.0 else "鸡犬相闻"
        scroll(g, TEXT_X, txt, y=2 if len(txt) == 5 else 3, k=text_k, side="left")

    def toss(self, k: float):
        """→ (手, 表情, 撒出去以后的秒数)"""
        if k < 0.9:  # 手伸进瓢里抓一把
            return keys(k, [(0, (DX + 9, FLOOR - 15)), (0.5, (DX + 8, FLOOR - 13)), (0.9, (DX + 6, FLOOR - 14))]), \
                "normal", None
        if k < 1.6:  # 往后一蓄
            return keys(k, [(0.9, (DX + 6, FLOOR - 14)), (1.6, (DX - 6, FLOOR - 16))]), "normal", None
        if k < 1.9:  # 一扬
            return keys(k, [(1.6, (DX - 6, FLOOR - 16)), (1.9, (DX + 14, FLOOR - 27))], ease=ease_out), "happy", None
        if k < 3.2:
            return keys(k, [(1.9, (DX + 14, FLOOR - 27)), (3.2, (DX + 9, FLOOR - 15))]), "happy", k - 1.9
        return (DX + 9, FLOOR - 15), ("happy" if 5.0 < k < 6.0 else "normal"), None

    def matrix(self, g: Gfx, t: float, k: float, crow: bool, frozen: bool):
        """点阵：一只鸡，啄米时头点下去、打鸣时伸脖子张嘴"""
        body = [0x00, 0x00, 0x00, 0xC6, 0xFE, 0x7C, 0x28, 0x6C]
        if crow:
            g.mx_rows([0x0B, 0x06, 0x04, 0xCC, 0xFC, 0x78, 0x28, 0x6C])
            return
        peck = not frozen and (t * 1.6) % 1 < 0.3
        g.mx_rows(body)
        if peck:
            g.mx_rows([0x00, 0x00, 0x00, 0xC0, 0xFE, 0x7F, 0x2B, 0x6C])
        else:
            g.mx_set(5, 1), g.mx_set(6, 1), g.mx_set(5, 2), g.mx_set(6, 2), g.mx_set(7, 2), g.mx_set(5, 0)
        if peck and k > 2.6:
            g.mx_set(7, 7)

    def enter(self, g: Gfx, t: float):
        """端着瓢从左边走出来，鸡一只只从鸡舍里跑出来"""
        self.clock.tick(t)
        self.yard(g, t)
        grains, homes, order = self.plan(0)
        for c in (1, 2, 3, 0):
            q = span(t, 0.3 + c * 0.45, 1.6 + c * 0.45)
            if q <= 0:
                continue
            x = lerp(112, homes[c], ease_out(q))
            self.draw_chicken(g, c, x, False if q < 1 else rand(c, self.s + 9) > 0.5, "walk" if q < 1 else "stand", t)
        x = lerp(4, DX, ease_out(span(t, 0, 2.2)))

        def tool(gg, h1, h2):
            pix.blit(gg, LADLE, x + 3, FLOOR - 15)
        worker(g, x, FLOOR, t, hand=(x + 9, FLOOR - 15), legs="walk" if t < 2.2 else "stand", tool=tool)
        self.matrix(g, t, 0, False, False)
        scroll(g, TEXT_X, "鸡犬相闻", k=span(t, 0.4, 2.4), side="left")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
