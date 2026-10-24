"""五禽戏：林间空地上，小道士学虎、鹿、熊、猿、鸟（鹤）练五禽戏，每戏那只禽兽跑来蹲在右边跟着做。

依据：华佗五禽戏（《三国志·华佗传》“吾有一术，名五禽之戏：一曰虎，二曰鹿，三曰熊，四曰猿，五曰鸟”；
陶弘景《养性延命录》载其动作）；按健身气功五禽戏十式：虎举、虎扑、鹿抵、鹿奔、熊运、熊晃、猿提、猿摘、鸟伸、鸟飞。
入场：虎、鹿、熊、猿、鹤从右往左奔过空地，小道士走来站定，“五禽戏”。
持续：一遍十式，每式 60 秒（按 e）。每戏开头那只禽兽跑进来蹲在右边，跟着节拍做动作帧，两式练完跑出去。
      虎举虎爪上托下拉、虎扑弓步前扑（震屏扬尘、虎张口）；鹿抵鹿角手转腰后瞧、鹿奔弓步弓背；熊运揉腹画圈、
      熊晃沉步晃身（一步一震）；猿提踮脚缩肩转头、猿摘手搭凉棚摘头顶枝上的桃（桃到手里，下一轮又长出来）；
      鸟伸举臂后撩腿、鸟飞提膝展翅（白鹤跟着扇翅）。式名在右上角出现；桃枝上不时飘下花瓣，飞鸟掠过。
      续：五禽一齐跑过，左上“第几遍”加一。
中断：小道士收势，禽兽趴下打盹冒 z，“收势”。  恢复：禽兽一跳醒来，小道士起势接着练。
圆满：虎熊从左、鹿猿从右围上来，白鹤从天上落下，周身放光，闪白，“五禽戏毕”。
点阵：当前禽兽的头像（虎王字纹、鹿角、熊圆耳、猿脸、鹤顶）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_beasts import BEASTS
from .r4_kit import (P, Clock, bird, cached, counter, dao, grass, label, mix, mx_art, mx_ring, pop_title, ring,
                     seq, star)

FLOOR = 58
DX = 42
AX = 104                 # 禽兽蹲的位置（中心）
MOVE = 60.0
PEACH = (55, 19)         # 枝上的桃

N = P()
HOLD_DT = P(b=(120, 20, "palm"), f=(60, 160, "palm"))
DOWN = P(b=(110, 100, "palm"), f=(70, 80, "palm"))

UPCLAW = P(legs="tiptoe", rise=2, b=(-125, -105, "claw"), f=(-55, -75, "claw"), face="angry")
POUNCE = P(legs="bow", lean=28, b=(30, 40, "claw"), f=(15, 25, "claw"), face="angry")
DEER_T = P(legs="bow", lean=-8, b=(160, 170, "horn"), f=(-150, -170, "horn"), flip_head=True)
WINGUP = P(legs="knee", b=(200, 210, "wing"), f=(-20, -30, "wing"))
WINGDN = P(b=(130, 140, "wing"), f=(50, 40, "wing"))

MOVES = [
    ("虎举", [(0, N), (1.0, HOLD_DT), (2.4, UPCLAW), (3.4, UPCLAW),
             (4.4, P(b=(130, -40, "fist"), f=(50, -140, "fist"), face="angry")), (5.4, DOWN), (6.0, N)],
     [(2.4, 3.6)]),
    ("虎扑", [(0, N), (1.0, P(b=(-125, -105, "claw"), f=(-55, -75, "claw"))), (2.0, POUNCE), (3.0, POUNCE),
             (3.6, P(legs="horse", b=(130, -40, "claw"), f=(50, -140, "claw"))), (4.6, POUNCE), (5.4, POUNCE),
             (6.0, N)], [(2.0, 3.0), (4.6, 5.4)]),
    ("鹿抵", [(0, N), (1.2, DEER_T), (2.6, DEER_T), (4.0, N)], [(1.2, 2.6)]),
    ("鹿奔", [(0, N), (1.2, P(legs="bow", lean=10, b=(10, 0, "horn"), f=(0, -10, "horn"))),
             (2.4, P(legs="bowl", lean=22, b=(20, 10, "horn"), f=(10, 0, "horn"), head="bow")),
             (3.6, P(legs="bowl", lean=22, b=(20, 10, "horn"), f=(10, 0, "horn"), head="bow")),
             (4.6, P(legs="bow", lean=10, b=(10, 0, "horn"), f=(0, -10, "horn"))), (6.0, N)], [(1.2, 2.2), (4.6, 5.6)]),
    ("熊运", [(0, P(b=(120, 40, "fist"), f=(60, 140, "fist"))),
             (1.5, P(lean=15, b=(110, 20, "fist"), f=(50, 120, "fist"), face="sleep")),
             (3.0, P(lean=-5, b=(130, 60, "fist"), f=(70, 160, "fist"))),
             (4.5, P(lean=15, b=(110, 20, "fist"), f=(50, 120, "fist"), face="sleep")),
             (6.0, P(b=(120, 40, "fist"), f=(60, 140, "fist")))], [(1.0, 2.0), (4.0, 5.0)]),
    ("熊晃", [(0, P(legs="bow", lean=8, b=(150, 120, "fist"), f=(40, 60, "fist"))),
             (1.0, P(b=(110, 90, "fist"), f=(70, 90, "fist"))),
             (2.0, P(legs="bowl", lean=-8, b=(140, 110, "fist"), f=(30, 50, "fist"))),
             (3.0, P(b=(110, 90, "fist"), f=(70, 90, "fist"))),
             (4.0, P(legs="bow", lean=8, b=(150, 120, "fist"), f=(40, 60, "fist")))], [(0, 0.5), (2.0, 2.5)]),
    ("猿提", [(0, N), (0.6, P(legs="tiptoe", rise=3, b=(140, -60, "hook"), f=(40, -120, "hook"), face="wow")),
             (1.4, P(legs="tiptoe", rise=3, b=(140, -60, "hook"), f=(40, -120, "hook"), flip_head=True)),
             (2.6, P(legs="tiptoe", rise=3, b=(140, -60, "hook"), f=(40, -120, "hook"), flip_head=True)),
             (3.4, DOWN), (5.0, N)], [(0.6, 2.8)]),
    ("猿摘", [(0, N), (1.2, P(legs="bowl", f=(-30, -170, "palm"), b=(120, 100, "hook"))),
             (2.6, P(legs="tiptoe", rise=3, f=(-50, -60, "hook"), b=(120, 100, "palm"))),
             (3.6, P(legs="tiptoe", rise=3, f=(-50, -60, "hook"), b=(120, 100, "palm"))),
             (4.6, P(f=(30, -40, "palm"), b=(110, 100, "palm"), face="happy")),
             (6.0, P(f=(30, -40, "palm"), b=(110, 100, "palm"), face="happy")), (7.0, N)], [(2.6, 4.2)]),
    ("鸟伸", [(0, N), (1.2, P(b=(-120, -100, "palm"), f=(-60, -80, "palm"))),
             (2.4, P(legs="back", lean=14, b=(170, 165, "wing"), f=(155, 150, "wing"))),
             (3.6, P(legs="back", lean=14, b=(170, 165, "wing"), f=(155, 150, "wing"))), (4.6, DOWN), (6.0, N)],
     [(2.4, 3.8)]),
    ("鸟飞", [(0, WINGDN), (0.75, WINGUP), (1.5, WINGDN), (2.25, WINGUP), (3.0, WINGDN)], [(0.4, 1.1), (1.9, 2.6)]),
]
ORDER = ["tiger", "deer", "bear", "monkey", "crane"]
HEADS = {
    "tiger": """
#......#
########
#.#..#.#
########
#.#..#.#
.######.
.#.##.#.
..####..
""", "deer": """
#.#..#.#
.##..##.
..#..#..
.######.
.#.##.#.
.######.
..####..
...##...
""", "bear": """
##....##
########
########
#.#..#.#
########
##.##.##
.######.
..####..
""", "monkey": """
..####..
.#....#.
##.##.##
#.#..#.#
#......#
.#.##.#.
..#..#..
...##...
""", "crane": """
....##..
...#.#..
...####.
....#...
....#...
.####...
######..
.#..#...
"""}


def _branch():
    """头顶伸进来的桃枝 56×14：枝条、叶子（叶脉一道暗线）、两朵桃花"""
    p = Part(56, 14)
    p.shape("line", (0, 2, 20, 5), fill=1, width=2)
    p.shape("line", (20, 5, 40, 4), fill=1, width=2)
    p.shape("line", (40, 4, 55, 1), fill=1, width=1)
    p.shape("line", (24, 5, 25, 10), fill=1)
    for x, y, d in ((8, 5, 1), (15, 6, -1), (30, 6, 1), (36, 2, -1), (46, 4, 1), (51, 1, -1)):
        p.shape("ellipse", (x - 2, y - 1 + d, x + 2, y + 1 + d), fill=1)
        p.px(x - 1, y + d, 0), p.px(x, y + d, 0)
    for x, y in ((12, 1), (43, 7)):  # 桃花
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            p.px(x + dx, y + dy)
        p.px(x, y, 0)
    return p.sprite()


PEACH_SPR = pix.frames("""
 .#.
#####
##.##
#####
 ###
""")

ZZZ = pix.frames("""
###
 #
###
""")


def glade(g: Gfx, t: float, e: float):
    """林间空地：远山、地面、草丛、几块石头、头顶桃枝"""
    for x in range(0, 128, 2):
        y = 34 - 6 * math.sin(x * 0.05 + 0.4) - 2 * math.sin(x * 0.17)
        g.px(x, y)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    for x in range(-10, 140, 26):
        g.d.line((x, FLOOR + 2, x + 8, FLOOR + 2), fill=1)
    for x in (6, 24, 74, 120):
        grass(g, x, FLOOR - 1, t)
    g.d.ellipse((12, FLOOR - 4, 20, FLOOR + 1), fill=1)       # 石头
    g.d.line((14, FLOOR - 3, 17, FLOOR - 3), fill=0)
    pix.blit(g, cached(("wq", "branch"), _branch), 30, 0)
    g.d.line((PEACH[0], 9, PEACH[0], PEACH[1]), fill=1)       # 桃柄
    # 花瓣飘落（按 e）
    ph = (e % 17) / 5.0
    if ph < 1:
        x = 44 + math.sin(ph * 8) * 5 + ph * 10
        g.px(x, 6 + ph * (FLOOR - 8))


@register
class Wuqinxi(Ritual):
    id = "r4.wuqinxi"
    name = "五禽戏"
    desc = "林间空地上小道士练五禽戏，虎鹿熊猿鹤轮流跑来蹲在旁边跟着做；虎扑震地、猿摘摘桃、鸟飞展翅"
    T = {"enter": 6.5, "interrupt": 1.6, "resume": 1.8, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()

    # ------------------------------------------------------------ 零件

    def at(self, k: float):
        i = min(int(k // MOVE), 9)
        u = k - i * MOVE
        name, keys, peaks = MOVES[i]
        L = keys[-1][0]
        flip = False
        if i == 2:  # 鹿抵左右交替
            flip = int(u // L) % 2 == 1
        uu = u % L
        pose = seq(keys, uu) if u > 0.8 else seq(keys, 0.0)
        peak = any(a <= uu <= b for a, b in peaks)
        return i, u, uu, pose, flip, peak

    def beast(self, g: Gfx, t: float, i: int, u: float, peak: bool, sleep: float = 0.0):
        """当前禽兽：跑进来 → 蹲在右边跟着做 → 跑出去"""
        name = ORDER[i // 2]
        fr = BEASTS[name]
        s = u + (MOVE if i % 2 else 0)      # 本戏第几秒（两式 120 秒）
        x = AX
        running = False
        if s < 3.0:
            x = lerp(150, AX, ease_out(s / 3.0))
            running = True
        elif s > 117.0:
            x = lerp(AX, 150, ease_in((s - 117.0) / 3.0))
            running = True
        if running:
            spr = fr[2] if len(fr) > 2 else fr[int(t * 6) % 2]
            hop = abs(math.sin(t * 10)) * 2
        else:
            spr = fr[1] if peak and sleep == 0 else fr[0]
            hop = 0
            if name == "monkey" and peak:
                hop = abs(math.sin(t * 8)) * 3
        if sleep > 0:  # 趴下打盹
            spr = fr[0]
            hop = -1
        pix.blit(g, spr, x - spr.w // 2, FLOOR - spr.h - hop, flip=True)
        if sleep > 0:
            for j in range(2):
                q = ((t * 0.6 + j * 0.5) % 1)
                pix.blit(g, ZZZ[0], x - 6 - q * 4 + j * 2, FLOOR - spr.h - 4 - q * 10, outline=False)
        return x, spr

    def peach_hand(self, i, uu):
        """猿摘：桃在枝上（None）还是在手里（True）"""
        return i == 7 and 3.4 <= uu < 6.6

    def draw(self, g: Gfx, t: float, e: float, dt: float, k: float, pose=None, sleep: float = 0.0, flip=None):
        i, u, uu, p, fl, peak = self.at(k)
        if pose is not None:
            p = pose
        if flip is not None:
            fl = flip
        self.beast(g, t, i, u, peak, sleep)
        h = dao(g, DX, FLOOR, p, t, flip=fl)
        in_hand = self.peach_hand(i, uu) and pose is None
        if not in_hand:
            pix.blit(g, PEACH_SPR[0], PEACH[0] - 2, PEACH[1])
        else:
            hx, hy = h["hf"]
            pix.blit(g, PEACH_SPR[0], hx - 2, hy - 5)
            if abs(uu - 3.4) < dt:
                self.sparks.burst(PEACH[0], PEACH[1] + 2, 8, 16, life=0.5, gravity=30)
        if pose is None and sleep == 0:
            self.effects(g, t, dt, i, uu, p, h, fl)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        return i, u, h

    def effects(self, g, t, dt, i, uu, p, h, fl):
        s = -1 if fl else 1
        if i == 1 and (abs(uu - 2.0) < dt or abs(uu - 4.6) < dt):     # 虎扑落地
            for d in (-1, 1):
                self.puffs.emit(DX + d * 10, FLOOR - 1, vx=d * 12, vy=-3, life=0.6, rmax=1.8)
            self.sparks.burst(h["hf"][0] + 3, h["hf"][1], 8, 20, life=0.4, gravity=10)
        if i == 1 and (2.0 < uu < 2.15 or 4.6 < uu < 4.75):
            pix.shake(g, t, 1.2)
        if i in (0, 1) and p["face"] == "angry":                      # 虎爪划痕
            hx, hy = h["hf"]
            if i == 1 and (2.0 < uu < 2.6 or 4.6 < uu < 5.2):
                for j in range(3):
                    g.d.line((hx + 4 + j * 2, hy - 3 + j, hx + 7 + j * 2, hy + 3 + j), fill=1)
        if i == 4:                                                    # 熊运：腹前画圈
            a = uu / 6.0 * 2 * math.pi * 2
            cx, cy = DX + 1, FLOOR - 11
            for j in range(6):
                aa = a - j * 0.35
                if j % 2 == 0:
                    g.px(cx + math.cos(aa) * 8, cy + math.sin(aa) * 4)
        if i == 5 and (abs(uu - 0.0) < dt or abs(uu - 2.0) < dt):     # 熊晃：一步一震
            self.puffs.emit(DX + (8 if uu < 1 else -8), FLOOR - 1, vx=0, vy=-4, life=0.6, rmax=1.8)
        if i == 5 and (uu < 0.15 or 2.0 < uu < 2.15):
            pix.shake(g, t, 0.8)
        if i == 9:                                                    # 鸟飞：翅下的风
            if WINGUP["legs"] == p["legs"]:
                hx, hy = h["hf"]
                pix.dotted(g, hx - 2, hy + 6, hx + 4, hy + 10, 2, int(t * 10))
        if i == 3 and p["head"] == "bow":
            g.d.arc((DX - 10, FLOOR - 36, DX + 4, FLOOR - 16), 200, 280, fill=1)

    def mx(self, g: Gfx, t: float, i: int):
        mx_art(g, HEADS[ORDER[i // 2]])
        if ORDER[i // 2] == "tiger" and (t * 2) % 1 < 0.1:
            g.mx[2, 2] = g.mx[2, 5] = True

    def texts(self, g: Gfx, e: float, i: int, u: float):
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")
        if u < 10.0:
            label(g, 124, 3, MOVES[i][0], 12, "right", box=True)
        else:
            counter(g, MOVES[i][0], right=True)

    def parade(self, g: Gfx, t: float, q: float):
        """五禽一齐从右往左跑过（q ∈ [0,1]）"""
        for j, name in enumerate(ORDER):
            fr = BEASTS[name]
            spr = fr[2] if len(fr) > 2 else fr[int(t * 6 + j) % 2]
            x = lerp(140 + j * 26, -40 + j * 26, q) - 40
            hop = abs(math.sin(t * 10 + j)) * 2
            y = FLOOR - spr.h - hop if name != "crane" else FLOOR - 30 - spr.h + math.sin(t * 6) * 2
            pix.blit(g, spr, x, y, flip=True)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        glade(g, t, 3.0)
        if t < 3.0:
            self.parade(g, t, t / 3.0)
        if 2.0 < t < 4.5:
            daoshi(g, lerp(-12, DX, ease_out(span(t, 2.0, 4.5))), FLOOR, "walk", t)
        elif t >= 4.5:
            daoshi(g, DX, FLOOR, "gongshou" if t < 5.6 else "idle", t)
        if abs(t - 4.5) < dt:
            self.sparks.burst(DX, FLOOR - 20, 10, 18, life=0.5, gravity=0)
        pix.blit(g, PEACH_SPR[0], PEACH[0] - 2, PEACH[1])
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, int(t / 0.6) % 5 * 2 if t < 5.5 else 0)
        if 4.5 < t < 5.6:
            pop_title(g, 64, 3, "五禽戏", span(t, 4.5, 4.9), t)
        elif t >= 5.6:
            self.texts(g, 0.0, 0, 0.0)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        glade(g, t, e)
        if e >= self.CYCLE and k < 5.0:  # 续：五禽一齐跑过
            daoshi(g, DX, FLOOR, "gongshou" if k < 3.5 else "idle", t)
            pix.blit(g, PEACH_SPR[0], PEACH[0] - 2, PEACH[1])
            self.parade(g, t, k / 5.0)
            self.mx(g, t, int(k / 1.0) % 5 * 2)
            n = int(e // self.CYCLE) + 1
            pop_title(g, 64, 3, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍", span(k, 0.3, 0.7), t)
            return
        # 小事件：飞鸟
        ph = (e % 29) / 7.0
        if ph < 1 and int(e // 29) % 2 == 0:
            bird(g, lerp(-6, 134, ph), 22 + math.sin(ph * 7) * 3, t)
        i, u, h = self.draw(g, t, e, dt, k)
        self.mx(g, t, i)
        self.texts(g, e, i, u)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        glade(g, t, e)
        i, u, uu, p, fl, peak = self.at(k)
        q = ease_out(span(t, 0, 1.0))
        self.draw(g, t, e, dt, k, pose=mix(p, HOLD_DT, q), sleep=1.0 if t > 0.6 else 0.0, flip=fl and q < 0.5)
        self.mx(g, t, i)
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")
        if t > 0.5:
            label(g, 124, 3, "收势", 12, "right", box=True)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        glade(g, t, e)
        i, u, uu, p, fl, peak = self.at(k)
        q = ease_out(span(t, 0.6, 1.6))
        sleep = 1.0 if t < 0.5 else 0.0
        if 0.5 <= t < 0.8:  # 一跳醒来
            pass
        self.draw(g, t, e, dt, k, pose=mix(HOLD_DT, p, q), sleep=sleep, flip=fl and q > 0.5)
        if abs(t - 0.5) < dt:
            self.sparks.burst(AX, FLOOR - 16, 10, 20, up=10, life=0.5, gravity=40)
        self.mx(g, t, i)
        self.texts(g, e, i, 99)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        glade(g, t, e)
        cx = 60
        spots = {"tiger": (0, 1, False), "bear": (24, 1, False), "deer": (75, -1, True), "monkey": (93, -1, True)}
        for name, (x1, d, fl) in spots.items():
            fr = BEASTS[name]
            q = ease_out(span(t, 0.3 + (0.3 if name in ("bear", "monkey") else 0), 2.0))
            x0 = -40 if d > 0 else 160
            x = lerp(x0, x1, q)
            spr = fr[2] if (q < 1 and len(fr) > 2) else fr[1 if (q >= 1 and int(t * 3) % 2) else 0]
            pix.blit(g, spr, x, FLOOR - spr.h - (abs(math.sin(t * 10)) * 2 if q < 1 else 0), flip=fl)
        # 白鹤从天上落下
        cq = ease_out(span(t, 1.0, 2.6))
        cr = BEASTS["crane"]
        pix.blit(g, cr[1] if cq < 1 or int(t * 4) % 2 else cr[0], 107, lerp(-24, FLOOR - cr[0].h, cq), flip=True)
        dao(g, cx, FLOOR, HOLD_DT if t < 2.6 else P(b=(120, 20, "palm"), f=(60, 160, "palm"), face="happy"), t)
        if t > 2.6:
            for j in range(3):
                r = ((t - 2.6) * 14 + j * 9) % 28
                ring(g, cx, FLOOR - 18, r + 4, dotted=2)
        if abs(t - 2.6) < dt:
            pix.flash(g)
            self.sparks.burst(cx, FLOOR - 20, 24, 38, up=10, life=1.0, gravity=20)
        if 2.6 < t < 2.9:
            pix.shake(g, t, 1.2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, int(t / 0.5) % 5 * 2)
        if t > 2.6:
            g.mx[:] = False
            mx_ring(g, (t - 2.6) * 4 % 5)
            g.mx[3:5, 3:5] = True
            g.mx_level = 1 + int(6 * (1 - span(t, 2.6, 4.0)))
        if t > 3.0:
            pop_title(g, 64, 3, "五禽戏毕", span(t, 3.0, 3.4), t)
