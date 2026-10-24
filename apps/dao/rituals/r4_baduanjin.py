"""八段锦：道观院子里，小道士一式一式练健身气功八段锦。

歌诀：两手托天理三焦、左右开弓似射雕、调理脾胃须单举、五劳七伤往后瞧、摇头摆尾去心火、两手攀足固肾腰、
攒拳怒目增气力、背后七颠百病消。动作按健身气功八段锦要领：托天提踵、马步开弓（一手八字掌推出、一手拉弦）、
一手上撑一手下按、转头后瞧、马步俯身摇摆、俯身攀足、马步冲拳瞪目、提踵下颠。
入场：小道士从左边走进院子，站定拱手，起势（两臂前平举、屈膝下按）。
持续：一遍八式，每式 60 秒，按 e 推进；每式开头，上方逐字出现歌诀。开弓时手里一张气凝的弓，拉满一放，
      一道光箭飞出，天上一只雕盘旋；后瞧有目光点线；攒拳出拳带拳风、震屏；七颠落地扬尘。
      每隔一阵院子里有小事件：飞鸟掠过、松针飘落。续：收势调息，左上“第几遍”加一，从头再练。
中断：两手落下叠于丹田，“收势”。  恢复：起势，接回当前动作。
圆满：收势，周身放光一圈圈散开，闪白，“功行圆满”。
点阵：下排 8 格是八式进度（当前一格闪），上面是当前一式的小图标。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, lerp, span
from ..engine.chars import daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import (P, Clock, bird, counter, courtyard, dao, label, leaf_fall, mx_art, mx_ring, pop_title, ring,
                     seq, star)

FLOOR = 58
DX = 50
FORM = 60.0
VERSES = ["两手托天理三焦", "左右开弓似射雕", "调理脾胃须单举", "五劳七伤往后瞧",
          "摇头摆尾去心火", "两手攀足固肾腰", "攒拳怒目增气力", "背后七颠百病消"]

N = P()                                                     # 自然站立
HOLD_DT = P(b=(120, 20, "palm"), f=(60, 160, "palm"))       # 两手叠于丹田
CHEST = P(legs="horse", b=(130, -40, "palm"), f=(50, -140, "palm"))   # 两手交叉胸前

F1 = [(0, N), (1.2, P(b=(120, 30, "palm"), f=(60, 150, "palm"))),
      (2.4, P(b=(150, -80, "palm"), f=(30, -100, "palm"))),
      (3.4, P(legs="tiptoe", rise=2, b=(-125, -105, "palm"), f=(-55, -75, "palm"))),
      (4.6, P(legs="tiptoe", rise=2, b=(-125, -105, "palm"), f=(-55, -75, "palm"))),
      (5.8, P(b=(110, 100, "palm"), f=(70, 80, "palm"))), (6.4, N)]

F2 = [(0, N), (1.0, CHEST), (2.4, P(legs="horse", b=(180, 0, "fist"), f=(0, 0, "sword"))),
      (3.6, P(legs="horse", b=(180, 0, "fist"), f=(0, 0, "sword"))),
      (3.9, P(legs="horse", b=(180, 140, "palm"), f=(0, 0, "sword"))), (5.0, N)]

F3 = [(0, N), (1.0, P(b=(120, 20, "palm"), f=(60, 160, "palm"))),
      (2.4, P(b=(100, 95, "down"), f=(-45, -70, "palm"))), (3.6, P(b=(100, 95, "down"), f=(-45, -70, "palm"))),
      (4.6, P(b=(120, 20, "palm"), f=(60, 160, "palm"))),
      (6.0, P(b=(-120, -100, "palm"), f=(80, 85, "down"))), (7.2, P(b=(-120, -100, "palm"), f=(80, 85, "down"))),
      (8.2, P(b=(120, 20, "palm"), f=(60, 160, "palm"))), (9.0, N)]

F4 = [(0, N), (1.2, P(b=(130, 120, "palm"), f=(50, 60, "palm"))),
      (2.2, P(b=(130, 120, "palm"), f=(50, 60, "palm"), flip_head=True)),
      (3.8, P(b=(130, 120, "palm"), f=(50, 60, "palm"), flip_head=True)),
      (4.6, P(b=(110, 100, "palm"), f=(70, 80, "palm"))), (5.4, N)]

F5 = [(0, P(legs="horse", b=(120, 70, "palm"), f=(60, 80, "palm"))),
      (1.5, P(legs="horse", lean=24, b=(110, 60, "palm"), f=(50, 70, "palm"), face="sleep")),
      (3.0, P(legs="horse", lean=-10, b=(130, 80, "palm"), f=(70, 90, "palm"))),
      (4.5, P(legs="horse", lean=24, b=(110, 60, "palm"), f=(50, 70, "palm"), face="sleep")),
      (6.0, P(legs="horse", b=(120, 70, "palm"), f=(60, 80, "palm")))]

UP2 = P(b=(-115, -100, "palm"), f=(-65, -80, "palm"))
F6 = [(0, N), (1.2, UP2), (2.0, UP2), (3.4, P(lean=45, b=(100, 90, "palm"), f=(80, 85, "palm"))),
      (4.6, P(lean=48, b=(95, 88, "palm"), f=(78, 82, "palm"), face="sleep")),
      (5.8, UP2), (6.6, UP2), (7.6, N)]

WAIST = P(legs="horse", b=(120, 0, "fist"), f=(110, 0, "fist"), face="angry")
F7 = [(0, WAIST), (0.6, WAIST), (0.8, P(legs="horse", b=(120, 0, "fist"), f=(0, 0, "fist"), face="angry")),
      (1.6, P(legs="horse", b=(120, 0, "fist"), f=(0, 0, "fist"), face="angry")), (2.0, WAIST), (2.6, WAIST),
      (2.8, P(legs="horse", b=(20, 0, "fist"), f=(110, 0, "fist"), face="angry")),
      (3.6, P(legs="horse", b=(20, 0, "fist"), f=(110, 0, "fist"), face="angry")), (4.0, WAIST)]

F8 = [(0, P(b=(100, 95, "palm"), f=(80, 85, "palm"))),
      (1.0, P(legs="tiptoe", rise=3, b=(100, 95, "palm"), f=(80, 85, "palm"))),
      (1.6, P(legs="tiptoe", rise=3, b=(100, 95, "palm"), f=(80, 85, "palm"))),
      (1.75, P(b=(100, 95, "palm"), f=(80, 85, "palm"), face="happy")),
      (2.4, P(b=(100, 95, "palm"), f=(80, 85, "palm")))]

FORMS = [F1, F2, F3, F4, F5, F6, F7, F8]

QISHI = [(0, N), (1.2, P(b=(30, 10, "down"), f=(20, 0, "down"))),
         (2.4, P(legs="wide", b=(60, 30, "down"), f=(50, 20, "down"))), (3.2, HOLD_DT)]

ICONS = ["""
.#...#.
..#.#..
...#...
..###..
...#...
..#.#..
""", """
...#...
.#####.
#..#..#
...#...
..#.#..
.#...#.
""", """
.....#.
...#.#.
..####.
.#.#...
#..#...
..#.#..
""", """
..#....
.##....
..#....
.###...
..#....
.#.#...
""", """
.......
...#...
.####..
#.#.#..
..#.#..
.#...#.
""", """
.......
..##...
.#..#..
#...#..
#...#..
..#.#..
""", """
...#...
..####.
.#.#...
...#...
..#.#..
.#...#.
""", """
...#...
..###..
.#.#.#.
...#...
..#.#..
..#.#..
"""]

EAGLE = pix.frames("""
##     ##
 ### ###
   ###
    #
---
   ###
 #######
#   #   #
    #
""")


@register
class Baduanjin(Ritual):
    id = "r4.baduanjin"
    name = "八段锦"
    desc = "道观院子里小道士一式一式练八段锦：托天、开弓射雕、单举、后瞧、摇头摆尾、攀足、攒拳、七颠"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 2.0, "complete": 5.5}
    CYCLE = 480.0

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()

    # ------------------------------------------------------------ 动作

    def pose_at(self, k: float):
        """一遍里第 k 秒：(姿势, 第几式, 式内秒数, 朝向翻转)"""
        i = min(int(k // FORM), 7)
        u = k - i * FORM
        keys = FORMS[i]
        flip = False
        if i == 1:  # 开弓：左右交替（右开弓后转身左开弓）
            L = keys[-1][0]
            flip = int(u // L) % 2 == 1
        if u < 0.8 and i > 0:  # 两式之间回到自然站立
            return seq(keys, 0.0), i, u, flip
        return seq(keys, u), i, u, flip

    def scene(self, g: Gfx, t: float, e: float):
        courtyard(g, t)
        # 小事件：飞鸟掠过 / 松针飘落（按 e）
        slot, ph = int(e // 23), (e % 23) / 6.0
        if ph < 1:
            if slot % 2 == 0:
                bird(g, lerp(134, -6, ph), 20 + math.sin(ph * 9) * 3, t)
            else:
                leaf_fall(g, 108, 26, ph)

    def draw_form(self, g: Gfx, t: float, e: float, dt: float, k: float):
        pose, i, u, flip = self.pose_at(k)
        h = dao(g, DX, FLOOR, pose, t, flip=flip)
        L = FORMS[i][-1][0]
        uu = u % L
        if i == 1:
            self.eagle(g, t)
            if 2.0 < uu < 3.9:  # 气凝的弓 + 弦
                hx, hy = h["hf"]
                bx, by = h["hb"]
                s = -1 if flip else 1
                cx = hx - s * 2
                if s > 0:
                    g.d.arc((cx - 5, hy - 8, cx + 5, hy + 8), -75, 75, fill=1)
                else:
                    g.d.arc((cx - 5, hy - 8, cx + 5, hy + 8), 105, 255, fill=1)
                tips = [(cx + s * 1, hy - 8), (cx + s * 1, hy + 8)]
                for tx, ty in tips:
                    g.px(tx - s, ty + (1 if ty < hy else -1) * 0)
                pull = (bx, by) if uu < 3.6 else (cx + s, hy)
                for a in tips:
                    pix.dotted(g, a[0], a[1], pull[0], pull[1], 1 if uu > 2.4 else 2)
            if 3.6 < uu < 4.6:  # 放箭：一道光箭飞出
                q = span(uu, 3.6, 4.4)
                s = -1 if flip else 1
                ax = h["hf"][0] + s * q * 70
                ay = h["hf"][1] - q * 6
                g.d.line((ax - s * 6, ay, ax, ay), fill=1)
                g.px(ax + s, ay), g.px(ax - s * 5, ay - 1), g.px(ax - s * 5, ay + 1)
                if abs(uu - 3.6) < dt:
                    self.sparks.burst(h["hf"][0], h["hf"][1], 8, 18, life=0.4, gravity=0)
        elif i == 2 and (abs(uu - 2.4) < dt or abs(uu - 6.0) < dt):
            hx, hy = h["hf"] if uu < 4 else h["hb"]
            self.sparks.burst(hx, hy - 3, 6, 14, up=8, life=0.4, gravity=10)
        elif i == 3 and pose["flip_head"]:  # 目光点线
            mx_, my = h["nose"]
            s = 1 if flip else -1
            pix.dotted(g, mx_ + s * 2, my - 1, mx_ + s * 22, my + 2, 3, int(t * 8))
        elif i == 4:  # 摇摆的动势线
            if pose["lean"] > 10:
                hx, hy = h["head"]
                g.d.arc((hx - 14, hy - 12, hx + 10, hy + 12), 200, 250, fill=1)
        elif i == 5 and pose["lean"] > 40:
            hx, hy = h["hf"]
            if int(t * 4) % 2:
                star(g, hx + 2, FLOOR - 3, 1)
        elif i == 6:
            for key, at_ in (("hf", 0.8), ("hb", 2.8)):
                if 0 < uu - at_ < 0.5:  # 拳风
                    hx, hy = h[key]
                    q = (uu - at_) / 0.5
                    s = -1 if flip else 1
                    for j in (-2, 0, 2):
                        pix.dotted(g, hx + s * (3 + q * 4), hy + j, hx + s * (8 + q * 10), hy + j, 2, int(q * 6))
                if abs(uu - at_) < dt:
                    self.puffs.emit(h[key][0] + 6, h[key][1], vx=20, vy=0, life=0.4, rmax=2, spread=0)
                if 0 < uu - at_ < 0.12:
                    pix.shake(g, t, 0.8)
        elif i == 7 and abs(uu - 1.75) < dt:  # 下颠：落地扬尘
            for s in (-1, 1):
                self.puffs.emit(DX + s * 8, FLOOR - 1, vx=s * 10, vy=-3, life=0.6, rmax=1.6, spread=1)
            self.sparks.burst(DX, FLOOR - 1, 6, 14, up=10, life=0.4, gravity=60)
        if i == 7 and 1.75 < uu < 1.9:
            pix.shake(g, t, 1.0)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        return h, i, u

    def eagle(self, g: Gfx, t: float):
        a = t * 0.5
        x, y = 64 + math.cos(a) * 46, 14 + math.sin(a) * 5
        spr = pix.anim(EAGLE, t, 3)
        pix.blit(g, spr if math.sin(a) < 0 else spr.flip() if False else spr, x - 4, y - 2, flip=math.sin(a) > 0)

    def mx(self, g: Gfx, t: float, i: int, done_all: bool = False):
        mx_art(g, ICONS[i], 0, 0)
        for c in range(8):
            if c < i or done_all:
                g.mx[7, c] = True
            elif c == i:
                g.mx[7, c] = (t * 3) % 1 < 0.6

    def texts(self, g: Gfx, e: float, i: int, u: float):
        n = int(e // self.CYCLE) + 1
        if i == 0 and e >= self.CYCLE:  # 续之后第一式：前 6 秒被收势起势占了，歌诀往后挪
            u -= 6.0
        if 0 <= u < 8.0:  # 歌诀逐字出现
            s = VERSES[i]
            m = min(len(s), int(u / 0.25) + 1)
            label(g, 64 - 42, 2, s[:m] + "", 12, "left", box=False, pad=1)
        else:
            counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")

    # ------------------------------------------------------------ 阶段

    def qishi(self, g: Gfx, t: float, x=DX):
        return dao(g, x, FLOOR, seq(QISHI, t, loop=False), t)

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        self.scene(g, t, 3.0)
        if t < 2.0:
            daoshi(g, lerp(-12, DX, ease_out(span(t, 0, 2.0))), FLOOR, "walk", t)
        elif t < 2.8:
            daoshi(g, DX, FLOOR, "bow" if 2.3 < t < 2.7 else "gongshou", t)
        else:
            self.qishi(g, t - 2.8)
            if abs(t - 2.8) < dt:
                self.sparks.burst(DX, FLOOR - 20, 10, 18, life=0.5, gravity=0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, 0)
        if t > 3.2:
            label(g, 64, 4, "八段锦", 12, "center", box=True)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        self.scene(g, t, e)
        if e >= self.CYCLE and k < 6.0:  # 续：收势调息 → 起势
            if k < 2.4:
                dao(g, DX, FLOOR, seq([(0, N), (1.2, HOLD_DT), (2.4, HOLD_DT)], k, loop=False), t)
                if 1.2 < k < 2.4:  # 调息：丹田一圈光
                    ring(g, DX + 1, FLOOR - 9, 3 + (k - 1.2) * 10, dotted=2, ry=(3 + (k - 1.2) * 10) * 0.5)
            else:
                self.qishi(g, (k - 2.4) * 3.2 / 3.6)
            self.sparks.step(dt)
            self.sparks.draw(g)
            self.mx(g, t, 0, done_all=k < 2.4)
            n = int(e // self.CYCLE) + 1
            pop_title(g, 64, 3, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍", span(k, 0.2, 0.6), t)
            return
        h, i, u = self.draw_form(g, t, e, dt, k)
        self.mx(g, t, i)
        self.texts(g, e, i, u)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        self.scene(g, t, e)
        pose, i, u, flip = self.pose_at(k)
        q = ease_out(span(t, 0, 1.0))
        dao(g, DX, FLOOR, P(**{**pose}) if q <= 0 else _mix(pose, HOLD_DT, q), t, flip=flip and q < 0.5)
        if t > 1.0:
            ring(g, DX + 1, FLOOR - 9, 3 + (t - 1.0) * 8, dotted=2, ry=(3 + (t - 1.0) * 8) * 0.5)
        self.mx(g, t, i)
        if t > 0.5:
            label(g, 64, 4, "收势", 12, "center", box=True)
        else:
            self.texts(g, e, i, 99)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        self.scene(g, t, e)
        pose, i, u, flip = self.pose_at(k)
        if t < 1.2:
            self.qishi(g, t * 3.2 / 1.2)
        else:
            q = ease_out(span(t, 1.2, 2.0))
            dao(g, DX, FLOOR, _mix(HOLD_DT, pose, q), t, flip=flip and q > 0.5)
        if abs(t - 1.2) < dt:
            self.sparks.burst(DX, FLOOR - 14, 10, 18, life=0.5, gravity=0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, i)
        self.texts(g, e, i, 99)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        self.scene(g, t, e)
        if t < 1.4:
            dao(g, DX, FLOOR, seq([(0, N), (1.2, HOLD_DT), (1.4, HOLD_DT)], t, loop=False), t)
        else:
            dao(g, DX, FLOOR, P(b=(120, 20, "palm"), f=(60, 160, "palm"), face="happy" if t > 2.2 else "sleep"), t)
        if t > 1.4:  # 周身放光：一圈圈散开
            for j in range(3):
                r = ((t - 1.4) * 14 + j * 9) % 30
                ring(g, DX, FLOOR - 18, r + 4, dotted=2)
        if abs(t - 1.6) < dt:
            pix.flash(g)
            self.sparks.burst(DX, FLOOR - 20, 24, 38, up=10, life=1.0, gravity=20)
        if 1.6 < t < 1.9:
            pix.shake(g, t, 1.2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, 7, done_all=True)
        if t > 1.6:
            mx_ring(g, (t - 1.6) * 4 % 5)
            g.mx_level = 1 + int(6 * (1 - span(t, 1.6, 3.0)))
        if t > 2.0:
            pop_title(g, 64, 3, "功行圆满", span(t, 2.0, 2.4), t)


def _mix(p, q, k):
    from .r4_kit import mix
    return mix(p, q, k)
