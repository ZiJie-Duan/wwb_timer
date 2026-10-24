"""卧数星斗：夏夜山坡上，小道士仰卧枕草、一膝立起，抬手指天数北斗。

依据：北斗七星天枢、天璇、天玑、天权、玉衡、开阳、摇光；道教《太上玄灵北斗本命延生真经》奉北斗七星君；
开阳旁的小星“辅星”（Alcor）；《鹖冠子·环流》“斗柄东指，天下皆春”。

入场：一片黑里星星一颗颗亮出来，草坡和远处道观屋脊浮现，小道士抬手指天。
持续（一轮 100 秒）：指着北斗一颗颗数（每颗 3 秒）——星闪成十字、连线接上一颗、左上牌子写星名、头上冒“一”“二”……
      斗勺连成；再随便数“八”“九”“十”……越数越慢，“十二…”，手垂下、睡着冒 Z；一颗流星划过，惊醒“！”，
      旧连线一段段散掉，从头再数。北斗随时间微微转动；萤火虫在草上飞；每 5 分钟一次睡着时开阳旁闪出“辅星”。
退场：七星一齐亮起连成斗，小道士睁眼，画面收拢到他脸上。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, lerp, rand, span
from ..engine.chars import Part
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x1_common import bang, cached, ev, iris, mx_z, plate, say, supine, twinkle, zzz

FLOOR = 57
MAN_X = 10                      # 后脑着地处
CYCLE = 100.0
NAMES = ["天枢", "天璇", "天玑", "天权", "玉衡", "开阳", "摇光"]
DIPPER = [(0, 0), (1, 9), (12, 11), (14, 3), (24, 1), (32, 3), (42, 9)]   # 斗勺四星 + 斗柄三星
D_CX, D_CY = 86, 17             # 北斗中心（绕它微微转）
COUNT_AT = [3.0 * i for i in range(7)]
EXTRA = [(24.0, 8), (28.5, 9), (34.0, 10), (40.5, 11), (47.5, 12)]   # 越数越慢
SLEEP_AT = 52.0
METEOR = 88.0
WAKE = 90.0
BG_STARS = [(int(rand(i, 11) * 124) + 2, int(rand(i, 12) * 30) + 1) for i in range(70)]
BG_STARS = [(x, y) for x, y in BG_STARS if not (56 < x < 116 and 2 < y < 32) and not (x < 40 and y < 20)]
PICK = [BG_STARS[i] for i in (2, 5, 8, 11, 14)]   # “八”之后随手数的几颗


def dipper(t: float):
    """北斗七星当前位置：绕中心微微转（斗柄缓缓指向四方的意思）"""
    a = math.sin(t / 90.0) * 0.12
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for x, y in DIPPER:
        x, y = x - 21, y - 5
        x, y = x * 1.25, y * 1.25
        out.append((D_CX + x * ca - y * sa, D_CY + x * sa + y * ca))
    return out


# ---------------------------------------------------------------- 道具

PAGODA = pix.sprite("""
       #
       #
      ###
 #   #####   #
  ###########
   .........
    ##.#.##
 #  #######  #
  ###########
   .........
    ##.#.##
 #  #######  #
  ###########
   .........
    ##...##
    ##.#.##
   #########
""")

PINE = pix.sprite("""
    #
   ###
  ##.##
   ###
  #####
 ##.#.##
  #####
 #######
##.###.##
 #######
#########
   .#.
    #
""")

GOURD = pix.sprite("""
  #
 ###
 #.#
 ###
#####
##.##
#####
 ###
""")


TUFT = pix.frames("""
# #
## #
 ##
---
 # #
# ##
 ##
""")

FLY = pix.frames("""
.#.
###
.#.
---
#
""")

METEOR_SPR = pix.frames("""
##
##
""")


def hill(g: Gfx, t: float):
    """草坡：远山一道起伏线，山顶小塔、两棵松；近处地面线、稀疏网点、草丛（随风两帧），身边一只酒葫芦"""
    pts = [(58, FLOOR), (72, 51), (88, 47), (100, 45), (112, 47), (127, 50)]
    pix.blit(g, PAGODA, 94, 45 - PAGODA.h + 1)
    pix.blit(g, PINE, 79, 49 - PINE.h + 1)
    pix.blit(g, PINE, 115, 48 - PINE.h + 1)
    g.d.line(pts, fill=1)
    pix.checker(g, (0, FLOOR + 2, 128, 64), 0.125)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for i, x in enumerate((2, 64, 76, 92, 108, 121)):
        pix.blit(g, pix.anim(TUFT, t * 0.8 + i * 0.3, 1), x, FLOOR - 3, outline=False)
    pix.blit(g, GOURD, 58, FLOOR - GOURD.h)


def sky(g: Gfx, t: float, appear: float = 1.0):
    """背景星：固定位置，按出现的进度依次亮；几颗会闪"""
    n = int(len(BG_STARS) * appear)
    for i, (x, y) in enumerate(BG_STARS[:n]):
        twinkle(g, x, y, t * 0.6, i, big=(i % 7 == 0))


def fireflies(g: Gfx, t: float):
    """两只萤火虫在草上慢飞，一亮一灭"""
    for i in range(2):
        x = 60 + i * 30 + math.sin(t * 0.37 + i * 2) * 14
        y = 46 + math.sin(t * 0.61 + i) * 5
        k = (t * 0.5 + i * 0.5) % 1
        if k < 0.45:
            pix.blit(g, FLY[0] if k < 0.3 else FLY[1], x - 1, y - 1, outline=False)


def star(g: Gfx, x, y, lit: float, t: float, i: int):
    """北斗的星：没数到时一个点 + 偶尔闪；数到时十字（刚数到那一下更大）"""
    x, y = int(round(x)), int(round(y))
    if lit <= 0:
        g.px(x, y)
        if (t * 0.4 + i * 0.13) % 1 < 0.1:
            g.px(x + 1, y), g.px(x - 1, y)
        return
    if lit < 0.5:   # 刚数到：大十字、四角点
        g.d.line((x - 3, y, x + 3, y), fill=1), g.d.line((x, y - 3, x, y + 3), fill=1)
        g.px(x, y, 0)
        for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
            g.px(x + dx, y + dy)
    else:
        g.d.line((x - 1, y, x + 1, y), fill=1), g.d.line((x, y - 1, x, y + 1), fill=1)
        if (t * 0.6 + i * 0.29) % 1 < 0.12:
            g.px(x - 2, y), g.px(x + 2, y), g.px(x, y - 2), g.px(x, y + 2)


@register
class StarsRest(Rest):
    id = "x1.stars"
    name = "卧数星斗"
    desc = "夏夜山坡上小道士仰卧，抬手指着北斗一颗颗数，星名、数字一个个冒出来；数着数着睡着，流星划过又惊醒"
    T = {"enter": 2.8, "exit": 1.3}

    def setup(self):
        self.phase = self.rng.random() * 0.0

    # ------------------------------------------------------------ 状态（只依赖 t）

    def state(self, t: float):
        k = t % CYCLE
        n_cycle = int(t // CYCLE)
        counted = sum(1 for a in COUNT_AT if k >= a)
        extra = [n for a, n in EXTRA if k >= a]
        asleep = SLEEP_AT <= k < WAKE
        return k, n_cycle, counted, extra, asleep

    def scene(self, g: Gfx, t: float, appear: float = 1.0, all_lit: float = 0.0):
        k, nc, counted, extra, asleep = self.state(t)
        sky(g, t, appear)
        pts = dipper(t)
        # 连线：数到的星依次连起来；醒来后旧线一段段散掉
        fade = span(k, WAKE + 1.0, CYCLE - 0.5) if k >= WAKE and all_lit <= 0 else 0.0
        nl = counted if all_lit <= 0 else 7
        for i in range(1, nl):
            if fade and i <= int(fade * 7):
                continue
            (x0, y0), (x1, y1) = pts[i - 1], pts[i]
            if all_lit > 0 or k < COUNT_AT[i] + 0.6:
                q = 1.0 if all_lit > 0 else span(k, COUNT_AT[i], COUNT_AT[i] + 0.6)
                x1, y1 = lerp(x0, x1, q), lerp(y0, y1, q)
            pix.dotted(g, x0, y0, x1, y1, 2, 0)
        if all_lit > 0 or (counted == 7 and not fade):   # 斗勺闭合
            if all_lit > 0 or k >= COUNT_AT[6] + 0.6:
                pix.dotted(g, *pts[3], *pts[0], 2, 0)
        for i, (x, y) in enumerate(pts):
            on = all_lit > 0 or (i < counted and not (fade and i < int(fade * 7)))
            lit = 0.0
            if on:
                lit = 1.0 if all_lit > 0 else (0.3 if k - COUNT_AT[i] < 0.8 else 1.0)
            star(g, x, y, lit, t, i)
        for j, n in enumerate(extra):   # 随手数的星
            if WAKE <= k:
                break
            x, y = PICK[j]
            a = EXTRA[j][0]
            star(g, x, y, 0.3 if k - a < 0.8 else 1.0, t, j + 7)
        # 辅星：每 5 分钟，睡着的时候开阳旁边闪出一颗小星
        fu = ev(t, 300.0, 258.0, 10.0)
        if fu is not None:
            x, y = pts[5]
            if fu > 0.5 and (fu < 9.5 or int(fu * 8) % 2):
                g.px(x + 3, y - 2)
                if 0.5 < fu < 1.5 or int(fu * 2) % 3 == 0:
                    g.px(x + 2, y - 2), g.px(x + 4, y - 2), g.px(x + 3, y - 3), g.px(x + 3, y - 1)
        # 流星
        mk = span(k, METEOR, METEOR + 1.2)
        if 0 < mk < 1:
            for s in range(14):
                q = max(ease_in(mk) - s * 0.02, 0)
                tx, ty = lerp(128, 60, q), lerp(0, 34, q)
                if s == 0:
                    g.d.rectangle((tx - 1, ty - 1, tx, ty), fill=1)
                elif s < 5 or s % 2 == 0:
                    g.px(tx, ty)
        hill(g, t)
        fireflies(g, t)
        return k, nc, counted, extra, asleep, pts

    def man(self, g: Gfx, t: float, k: float, asleep: bool, pts, face=None, arm=None):
        if face is None:
            if asleep:
                face = "snore" if (t / 3.6) % 1 < 0.5 else "sleep"
            elif WAKE <= k < WAKE + 2.5:
                face = "wow"
            elif k >= EXTRA[3][0] or (t % 4.1) < 0.15:
                face = "sleep" if (k >= EXTRA[3][0] and (t % 1.6) < 0.7) or (t % 4.1) < 0.15 else "open"
            else:
                face = "open"
        if arm is None:
            arm = "belly" if asleep or (WAKE <= k < WAKE + 3.0) else "raise"
        return supine(g, MAN_X, FLOOR, t, face=face, knee=True, arm=arm)

    def sight(self, g: Gfx, h: dict, k: float, counted: int, pts):
        """数星时从指尖到星一条虚线（刚数到的 1 秒里）"""
        if "hand" not in h:
            return
        tgt = None
        for i, a in enumerate(COUNT_AT):
            if a <= k < a + 1.0:
                tgt = pts[i]
        for j, (a, n) in enumerate(EXTRA):
            if a <= k < a + 1.0:
                tgt = PICK[j]
        if tgt:
            hx, hy = h["hand"]
            pix.dotted(g, hx + 2, hy - 2, tgt[0], tgt[1] + 2, 3, int(k * 10))

    def words(self, g: Gfx, t: float, k: float, counted: int, extra, asleep: bool, h: dict):
        """最后画字：左上星名牌；头顶的数（一次只有一个）"""
        hx = MAN_X + 26
        if counted and k < COUNT_AT[6] + 3.0:
            i = counted - 1
            plate(g, 6, 4, NAMES[i], k=span(k, COUNT_AT[i], COUNT_AT[i] + 0.3))
        num = None
        if counted and k < 22.0:
            i = counted - 1
            num, a = cn_num(i + 1), COUNT_AT[i]
        elif extra and not asleep and k < WAKE:
            num, a = cn_num(extra[-1]), EXTRA[len(extra) - 1][0]
            if extra[-1] == 12:
                num += "…" if int(k * 2) % 2 else ""
        if num is not None and k - a < 2.6:
            say(g, 4, 28, num, span(k, a, a + 0.25))
        if WAKE <= k < WAKE + 2.0:
            bang(g, MAN_X + 4, 30)

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        k, nc, counted, extra, asleep, pts = self.scene(g, t)
        h = self.man(g, t, k, asleep, pts)
        self.sight(g, h, k, counted, pts)
        if asleep:
            mx, my = h["mouth"]
            zzz(g, mx + 2, my - 6, t, on=span(k, SLEEP_AT, SLEEP_AT + 2.0) * 2)
        self.words(g, t, k, counted, extra, asleep, h)
        self.matrix(g, t, k, counted, asleep)

    def matrix(self, g: Gfx, t: float, k: float, counted: int, asleep: bool, all_lit: bool = False):
        cells = [(0, 2), (0, 5), (3, 6), (3, 3), (5, 2), (6, 3), (7, 5)]
        for i, (x, y) in enumerate(cells):
            on = all_lit or i < counted
            g.mx[y, x] = True if on else (t * 1.5 + i * 0.3) % 1 < 0.5
        if asleep:
            mx_z(g, t, 0, 0)

    def enter(self, g: Gfx, t: float):
        ap = span(t, 0.2, 2.2)
        self.scene(g, 0.0, appear=ap)
        arm = "raise" if t > 2.0 else "belly"
        self.man(g, t, 0.0, False, dipper(0.0), face="open" if t > 1.2 else "sleep", arm=arm)
        g.mx[:] = False
        for i, (x, y) in enumerate([(0, 2), (0, 5), (3, 6), (3, 3), (5, 2), (6, 3), (7, 5)]):
            if ap * 7 > i:
                g.mx[y, x] = True
        r = lerp(4, 150, ease_out(span(t, 0.0, 1.6)))
        iris(g, MAN_X + 12, FLOOR - 8, r)

    def exit(self, g: Gfx, t: float):
        h0 = self.hold_t
        k, nc, counted, extra, asleep, pts = self.scene(g, h0, all_lit=1.0)
        h = self.man(g, h0 + t, k, False, pts, face="happy" if t > 0.3 else "open", arm="raise")
        self.matrix(g, h0 + t, k, 7, False, all_lit=True)
        g.mx_level = 4 if t < 0.3 else 1
        r = lerp(140, 0, ease_out(span(t, 0.3, self.T["exit"] - 0.05)))
        iris(g, MAN_X + 13, FLOOR - 9, r)
