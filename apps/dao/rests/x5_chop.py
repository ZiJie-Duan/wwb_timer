"""劈柴：木墩上立一段圆木，小道士抡斧——预备、举过头顶、一顿、劈下，木头一分为二飞开。
左边那半落在脚边，他捡起来扔上右边的柴垛；再转身从身后的木堆搬下一段。
五段劈完：喝口葫芦里的水、擦汗，抱起整垛柴走出画面，扛着新木头回来。
右侧竖写“依乎天理”（《庄子·养生主》庖丁解牛：依乎天理，批大郤，导大窾，因其固然）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_bounce, lerp, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import daoshi, dpoly, fade_box, note, phase, sweat

GY = 58
X0 = 44              # 道士劈柴的站位
FETCH = 36           # 去木堆拿木头的站位
SX = 68              # 木墩中心
STUMP_TOP = 49
LOG_H = 11
CP = 7.0             # 劈一段
NCH = 5              # 一垛劈几段
BR = 15.0            # 歇息 + 搬柴
BIG = NCH * CP + BR
L_AXE = 14

SUPPLY = [(12, 54), (19, 54), (26, 54), (15.5, 47.5), (22.5, 47.5)]   # 圆木堆（后放的在上面）
HEAP = [(89, 55.5), (96, 55.5), (103, 55.5), (110, 55.5), (92.5, 51.5), (99.5, 51.5), (106.5, 51.5), (96, 47.5),
        (103, 47.5), (99.5, 43.5)]

# 斧子关键帧：握点、柄的角度（握点 → 斧头）
STUCK = ((57.2, 37.0), 0.6)
IMPACT = ((54.0, 32.0), 0.0)
RAISED = ((40.0, 21.0), -2.5)
GOURD = Sprite("""
 .#.
 ###
 .#.
 ###
#.##
####
.##.
""")


def axe(g: Gfx, gx: float, gy: float, b: float):
    """斧：握点 (gx, gy)，柄朝 b 方向伸出 L_AXE，斧刃在柄的“下侧”（劈的方向）"""
    ux, uy = math.cos(b), math.sin(b)
    nx, ny = -uy, ux
    hx, hy = gx + ux * L_AXE, gy + uy * L_AXE
    g.d.line((gx - ux * 4, gy - uy * 4, hx, hy), fill=1)
    blade = [(hx - ux * 1.5 - nx * 2, hy - uy * 1.5 - ny * 2), (hx + ux * 1.5 - nx * 2, hy + uy * 1.5 - ny * 2),
             (hx + ux * 3 + nx * 5, hy + uy * 3 + ny * 5), (hx - ux * 2.5 + nx * 5, hy - uy * 2.5 + ny * 5)]
    g.d.polygon(blade, fill=1)
    g.d.line((hx - ux * 2.5 + nx * 5, hy - uy * 2.5 + ny * 5, hx + ux * 3 + nx * 5, hy + uy * 3 + ny * 5), fill=1)
    return hx + nx * 5, hy + ny * 5


def axe_at(k: float):
    """一段内（劈的部分）斧子位置：(握点, 角)"""
    def mix(a, b, q):
        return ((lerp(a[0][0], b[0][0], q), lerp(a[0][1], b[0][1], q)), lerp(a[1], b[1], q))
    if k < 4.0:
        return STUCK
    if k < 5.0:
        return mix(STUCK, RAISED, ease_in_out(span(k, 4.0, 5.0)))
    if k < 5.25:
        return RAISED
    if k < 5.4:
        return mix(RAISED, IMPACT, ease_in(span(k, 5.25, 5.4)))
    return mix(IMPACT, STUCK, ease_out(span(k, 5.4, 5.48)))


def rround(g: Gfx, x: float, y: float, r: float = 3.5):
    """圆木端面：年轮"""
    g.d.ellipse((x - r, y - r, x + r, y + r), fill=0, outline=1)
    g.d.ellipse((x - r + 2, y - r + 2, x + r - 2, y + r - 2), outline=1)


def piece(g: Gfx, x: float, y: float, ang: float = 0.0, w: float = 7, h: float = 4):
    """一块劈好的柴（半圆木）：中心 (x, y)，ang=0 时躺着、弧面朝上"""
    c, s = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(7):  # 弧面
        a = math.pi + i / 6 * math.pi
        px, py = math.cos(a) * w / 2, h / 2 + math.sin(a) * h
        pts.append((x + px * c - py * s, y + px * s + py * c))
    g.d.polygon(pts, fill=0, outline=1)
    g.px(x + (-0.5 * s), y + 0.5 * c)


def half_log(g: Gfx, x: float, y: float, ang: float, side: int):
    """飞出去的半段立木：中心 (x, y)，side=-1 左半 / 1 右半，劈开的平面朝里"""
    c, s = math.cos(ang), math.sin(ang)
    w, h = 5, LOG_H
    pts = []
    for px, py in ((0, -h / 2), (side * w, -h / 2 + 1), (side * (w + 0.5), 0), (side * w, h / 2 - 1), (0, h / 2)):
        px -= side * w / 2
        pts.append((x + px * c - py * s, y + px * s + py * c))
    g.d.polygon(pts, fill=0, outline=1)
    g.d.line((x - side * w / 2 * c, y - side * w / 2 * s, x + side * 1 * c, y + side * 1 * s), fill=1)


def arc_pos(a, b, u, height):
    return lerp(a[0], b[0], u), lerp(a[1], b[1], u) - math.sin(math.pi * clamp(u)) * height


@register
class Chop(Rest):
    id = "x5.chop"
    name = "劈柴"
    desc = "抡斧劈柴、码柴垛，劈完一垛喝口水，抱走柴再扛新木头回来"
    T = {"enter": 3.2, "exit": 1.3}

    def setup(self):
        self.s = self.rng.randrange(1000)
        self._ht = 0.0

    # ------------------------------------------------------------ 场景零件

    def stump(self, g: Gfx):
        d = g.d
        d.polygon([(SX - 7, STUMP_TOP), (SX + 7, STUMP_TOP), (SX + 8, GY - 1), (SX + 10, GY), (SX - 10, GY),
                   (SX - 8, GY - 1)], fill=0, outline=1)
        d.ellipse((SX - 7, STUMP_TOP - 2, SX + 7, STUMP_TOP + 2), fill=0, outline=1)
        d.arc((SX - 4, STUMP_TOP - 1, SX + 4, STUMP_TOP + 1), 0, 360, fill=1)
        for x in (SX - 4, SX + 1, SX + 5):
            d.line((x, STUMP_TOP + 4, x, GY - 2), fill=1)

    def log(self, g: Gfx, x: float, bottom: float):
        """立着的圆木，底在 bottom"""
        top = bottom - LOG_H
        g.d.rectangle((x - 5, top, x + 5, bottom), fill=0, outline=1)
        g.d.ellipse((x - 5, top - 2, x + 5, top + 2), fill=0, outline=1)
        g.px(x, top)
        g.d.line((x - 3, top + 4, x - 3, bottom - 2), fill=1)
        g.d.line((x + 2, top + 6, x + 2, bottom - 1), fill=1)

    def ground(self, g: Gfx):
        g.d.line((0, GY, 127, GY), fill=1)
        for i in range(9):
            x = rand(i, 41) * 120
            g.d.line((x, GY + 2 + (i % 3), x + 2, GY + 2 + (i % 3)), fill=1)
        # 木屑
        for i in range(7):
            g.px(SX - 14 + rand(i, 43) * 28, GY - 1)

    def text(self, g: Gfx, a: float = 1.0):
        s = "依乎天理"
        n = int(round(len(s) * clamp(a)))
        g.vtext(115, 2, s[:n])

    # ------------------------------------------------------------ 状态（全是 t 的函数）

    def state(self, t: float):
        big, k = phase(t, BIG)
        if k < NCH * CP:
            i, c = phase(k, CP)
            return "chop", big, i, c
        return "break", big, NCH, k - NCH * CP

    def draw(self, g: Gfx, t: float, hold_pose: bool = True, freeze: float | None = None):
        mode, big, i, c = self.state(t)
        self.ground(g)
        self.stump(g)
        self.text(g)
        if mode == "chop":
            self.chop(g, t, i, c)
        else:
            self.rest_break(g, t, c)

    def supply_left(self, i: int, c: float) -> int:
        """木堆里还剩几段（第 i 段在 1.9 秒被拿走）"""
        return NCH - i - (1 if c >= 1.9 else 0)

    def heap_count(self, i: int, c: float) -> int:
        n = 2 * i
        if c >= 6.1:
            n += 1          # 右半落到垛上
        return n

    def chop(self, g: Gfx, t: float, i: int, c: float):
        n_sup = self.supply_left(i, c)
        for j in range(n_sup):
            rround(g, *SUPPLY[j])
        n_heap = self.heap_count(i, c)
        for j in range(n_heap):
            piece(g, *HEAP[j])
        blink = "closed" if (t % 3.7) < 0.14 else "open"
        mxs = "log"
        # ---------------- 人与手
        hold = None    # 手里拿的东西：("log", x, y) / ("half", x, y, ang)
        f, X, crouch, lean, step = 1, X0, 0.0, 0.0, None
        hands = [None, None]
        axe_in_hand = False
        log_on_stump = c >= 3.6 and c < 5.4
        if c < 0.5 and i > 0:  # 刚扔完柴，站直
            crouch = lerp(0.6, 0, ease_out(span(c, 0, 0.5)))
            lean = lerp(3, 0, ease_out(span(c, 0, 0.5)))
        elif c < 1.2:  # 转身走到木堆
            f = -1
            X = lerp(X0, FETCH, ease_in_out(span(c, 0.5, 1.2)))
            step = c * 12
        elif c < 1.9:  # 蹲下够木头
            f, X = -1, FETCH
            q = ease_in_out(span(c, 1.2, 1.9))
            crouch, lean = 0.8 * q, 4 * q
            tgt = SUPPLY[n_sup - 1] if n_sup > 0 else SUPPLY[0]
            hands = [(lerp(FETCH - 4, tgt[0] + 2, q), lerp(48, tgt[1], q)), (lerp(FETCH - 2, tgt[0] - 1, q), lerp(48, tgt[1], q))]
        elif c < 2.4:  # 抱起
            f, X = -1, FETCH
            q = ease_in_out(span(c, 1.9, 2.4))
            crouch, lean = 0.8 * (1 - q), 4 * (1 - q)
            tgt = SUPPLY[n_sup]
            hx, hy = lerp(tgt[0] + 1, FETCH - 5, q), lerp(tgt[1], 44, q)
            hands = [(hx + 2, hy), (hx - 2, hy)]
            hold = ("round", hx, hy)
        elif c < 3.1:  # 转回来走向木墩
            X = lerp(FETCH, X0, ease_in_out(span(c, 2.4, 3.1)))
            step = c * 12
            hands = [(X + 7, 44), (X + 4, 45)]
            hold = ("round", X + 6, 44)
        elif c < 3.6:  # 俯身把木头立到木墩上
            q = ease_in_out(span(c, 3.1, 3.6))
            lean = 3 * math.sin(q * math.pi)
            lx, ly = lerp(X0 + 6, SX, q), lerp(44, STUMP_TOP - 6, q) - math.sin(q * math.pi) * 4
            hands = [(lx - 4, ly), (lx - 6, ly + 1)]
            hold = ("log", lx, ly + LOG_H / 2)
        elif c < 4.0:  # 握住斧柄，拔出来
            q = ease_in_out(span(c, 3.6, 4.0))
            gx, gy = STUCK[0]
            hands = [(lerp(X0 + 6, gx, q), lerp(46, gy, q)), (lerp(X0 + 4, gx - 3, q), lerp(47, gy + 1, q))]
            lean = 2 * q
        elif c < 6.0:  # 举斧、劈
            axe_in_hand = True
            lean = 2 if c < 4.6 or c >= 5.3 else lerp(2, -1, span(c, 4.6, 5.0))
        elif c < 6.4:  # 松手，弯腰捡脚边那半块
            q = ease_in_out(span(c, 6.0, 6.4))
            crouch, lean = 0.7 * q, 4 * q
            hands = [(lerp(STUCK[0][0], 56, q), lerp(STUCK[0][1], 54, q)), None]
        else:  # 起身往柴垛上一扔
            q = ease_out(span(c, 6.4, 6.65))
            crouch, lean = 0.7 * (1 - q * 0.2), 4 - q * 3
            hands = [(lerp(56, 60, q), lerp(54, 36, q)), None]
        # ---------------- 画
        if log_on_stump:
            self.log(g, SX, STUMP_TOP)
        pz = daoshi(g, X, GY, f, hands=hands if not axe_in_hand else self._axe_hands(c), lean=lean, crouch=crouch,
                    step=step, eye=blink if not (5.25 < c < 5.6) else "closed")
        # 斧
        if axe_in_hand:
            (gx, gy), b = axe_at(c)
            axe(g, gx, gy, b)
            g.d.rectangle((gx - 1, gy - 1, gx + 1, gy + 1), fill=1)
        else:
            (gx, gy), b = STUCK
            axe(g, gx, gy, b)
        if hold:
            if hold[0] == "round":
                rround(g, hold[1], hold[2])
            else:
                self.log(g, hold[1], hold[2])
        # 劈开：两半飞出去
        if c >= 5.4:
            u = span(c, 5.4, 6.1)
            if u < 1:  # 右半 → 柴垛
                x, y = arc_pos((SX + 2.5, STUMP_TOP - 6), HEAP[2 * i], u, 14)
                if u < 0.92:
                    half_log(g, x, y, u * 4.2, 1)
            u2 = span(c, 5.4, 5.85)
            lx, ly = arc_pos((SX - 2.5, STUMP_TOP - 6), (57, 55.5), u2, 6)
            if c < 6.2:  # 左半 → 脚边（躺下）
                if u2 < 1:
                    half_log(g, lx, ly, -u2 * math.pi / 2, -1)
                else:
                    piece(g, 57, 55.5)
            elif c < 6.45:  # 在手里
                piece(g, *pz.near, ang=-0.3)
            else:  # 扔上柴垛
                u3 = span(c, 6.45, 7.0)
                if u3 < 1:
                    x, y = arc_pos(pz.near if c < 6.5 else (60, 36), HEAP[2 * i + 1], ease_in_out(u3) * 0.3 + u3 * 0.7,
                                   10)
                    piece(g, x, y, ang=u3 * 7)
            # 木屑、闪光
            if c < 5.9:
                q = span(c, 5.4, 5.9)
                for j in range(8):
                    a = -math.pi * rand(j, self.s) - 0.2
                    r = 4 + q * (10 + rand(j + 9, self.s) * 12)
                    g.px(SX + math.cos(a) * r, STUMP_TOP - 8 + math.sin(a) * r * 0.8 + q * q * 14)
            if c < 5.5:
                for a in range(0, 360, 45):
                    rr = 3 + (c - 5.4) * 60
                    g.px(SX + math.cos(math.radians(a)) * rr, STUMP_TOP - 10 + math.sin(math.radians(a)) * rr * 0.6)
            mxs = "split"
        if 4.95 < c < 5.25:  # 举到顶，一顿
            g.px(pz.head[0] + 7, pz.head[1] - 6)
        if 5.0 < c < 5.25 or 5.85 < c < 6.0:
            sweat(g, pz.head[0] - 2, pz.head[1] - 2, span(c, 5.85, 6.0))
        self.mx(g, t, mxs, span(c, 5.4, 5.9), c)

    def _axe_hands(self, c: float):
        (gx, gy), b = axe_at(c)
        return [(gx, gy), (gx - math.cos(b) * 3, gy - math.sin(b) * 3)]

    def rest_break(self, g: Gfx, t: float, c: float):
        """劈完一垛：喝水、擦汗，抱走柴，扛新木头回来"""
        n_heap = 2 * NCH
        n_sup = 0
        f, X, crouch, lean, step = 1, X0, 0.0, 0.0, None
        hands = [None, None]
        eye, look = "open", 0.0
        carry = None
        if c < 4.5:  # 解下葫芦喝一口，擦汗
            if c < 0.6:
                q = ease_in_out(span(c, 0, 0.6))
                hands = [(lerp(STUCK[0][0], X0 + 3, q), lerp(STUCK[0][1], 46, q)), None]
            elif c < 2.6:
                q = ease_in_out(span(c, 0.6, 1.1)) * (1 - ease_in_out(span(c, 2.2, 2.6)))
                hands = [(X0 + 3 + q * 3, lerp(46, 29, q)), None]
                look = -2 * q
                eye = "closed" if q > 0.5 else "open"
            else:  # 袖子擦汗
                q = math.sin(span(c, 2.6, 3.8) * math.pi)
                hands = [(X0 + 3 + q * 4, lerp(46, 28, q)), None]
                eye = "closed" if 0.2 < q else "open"
            pz = daoshi(g, X, GY, f, hands=hands, look=look, eye=eye)
            hx, hy = pz.near
            if 0.6 <= c < 2.6:
                g.blit(GOURD, hx - 1, hy - 5)
            elif c < 0.6 or c > 3.8:
                pass
            if 3.6 < c < 4.4:
                sweat(g, pz.head[0] - 4, pz.head[1] - 2, span(c, 3.6, 4.2))
            if c > 1.4 and (self.ctx.finished or c > 3.9):
                note(g, X + 9, 20 - (c % 1.5) * 3)
            for j in range(n_heap):
                piece(g, *HEAP[j])
            (gx, gy), b = STUCK
            axe(g, gx, gy, b)
            self.mx(g, t, "gourd", 0, c)
            return
        if c < 6.0:  # 走到柴垛前，蹲下抱柴
            q = span(c, 4.5, 5.4)
            X = lerp(X0, 92, ease_in_out(q))
            step = c * 12 if q < 1 else None
            q2 = ease_in_out(span(c, 5.4, 6.0))
            crouch, lean = 0.6 * math.sin(q2 * math.pi), 3 * math.sin(q2 * math.pi)
            if c >= 5.7:
                n_heap = 0
                carry = 1
            hands = [(X + 7, lerp(44, 52, math.sin(q2 * math.pi))), (X + 4, lerp(45, 52, math.sin(q2 * math.pi)))]
        elif c < 8.0:  # 抱着走出画面
            X = lerp(92, 150, ease_in(span(c, 6.0, 8.0)))
            step = c * 12
            n_heap, carry = 0, 1
            hands = [(X + 7, 44), (X + 4, 45)]
        elif c < 9.0:
            n_heap = 0
            X = 999
        elif c < 12.0:  # 扛着新木头从右边走回来，走到木堆
            n_heap = 0
            f = -1
            X = lerp(150, FETCH, ease_out(span(c, 9.0, 12.0)))
            step = c * 12 if c < 11.8 else None
            carry = 2
            hands = [(X - 3, 33), (X + 1, 34)]
        elif c < 13.0:  # 卸下：木头滚进木堆
            n_heap = 0
            f, X = -1, FETCH
            q = span(c, 12.0, 12.6)
            crouch, lean = 0.4 * math.sin(q * math.pi), 2 * math.sin(q * math.pi)
            n_sup = NCH
        else:  # 转身回位
            n_heap, n_sup = 0, NCH
            X = lerp(FETCH, X0, ease_in_out(span(c, 13.0, 14.2)))
            step = c * 12 if c < 14.2 else None
        # 木堆（新木头落下）
        for j in range(n_sup):
            if c < 13.0:
                u = span(c, 12.0 + j * 0.08, 12.5 + j * 0.08)
                x0, y0 = X - 4 + j * 2, 30
                x, y = SUPPLY[j]
                rround(g, lerp(x0, x, u), lerp(y0, y, ease_out_bounce(u)))
            else:
                rround(g, *SUPPLY[j])
        for j in range(n_heap):
            piece(g, *HEAP[j])
        (gx, gy), b = STUCK
        axe(g, gx, gy, b)
        if X < 140:
            pz = daoshi(g, X, GY, f, hands=hands, crouch=crouch, lean=lean, step=step,
                        eye="closed" if (t % 3.7) < 0.14 else "open")
            if carry == 1:  # 一抱柴
                hx, hy = pz.near
                for j in range(6):
                    piece(g, hx - 2 + (j % 3) * 4, hy - 1 - (j // 3) * 4)
            elif carry == 2:  # 肩上一捆圆木
                hx, hy = pz.near
                for j in range(NCH):
                    rround(g, hx + 1 + (j % 3) * 6 - 6, hy - 4 - (j // 3) * 6)
        self.mx(g, t, "log", 0, c)

    def mx(self, g: Gfx, t: float, kind: str, u: float, c: float):
        if kind == "gourd":
            g.mx_blit(GOURD, 2, 1)
            return
        # 圆木端面，劈开时裂成两半向两边分开
        sep = int(round(ease_out(u) * 2)) if kind == "split" else 0
        for y in range(8):
            for x in range(8):
                r = math.hypot(x - 3.5, y - 3.5)
                ring = abs(r - 3.3) < 0.6 or abs(r - 1.4) < 0.5
                if not ring:
                    continue
                xx = x - sep if x < 4 else x + sep
                g.mx_set(xx, y)
        if kind == "split" and u < 0.3:
            g.mx_level = 6
            for y in range(8):
                g.mx_set(3, y)
                g.mx_set(4, y)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        """扛着斧头走进来，把斧头劈进木墩（落在 hold(0) 的样子：斧在墩上，人站直）"""
        T = self.T["enter"]
        self.ground(g)
        self.stump(g)
        for j in range(NCH):
            rround(g, *SUPPLY[j])
        self.text(g, span(t, 1.5, T - 0.3))
        if t < 1.9:
            X = lerp(-12, X0, ease_out(span(t, 0, 1.9)))
            pz = daoshi(g, X, GY, 1, hands=[(X + 4, 30), (X + 1, 32)], step=t * 12 if t < 1.8 else None)
            axe(g, X + 4, 30, -2.3)
        else:
            q = span(t, 1.9, 2.8)
            if q < 0.5:
                gb = lerp(-2.3, RAISED[1], ease_in_out(q * 2))
                gp = (lerp(X0 + 4, RAISED[0][0], ease_in_out(q * 2)), lerp(30, RAISED[0][1], ease_in_out(q * 2)))
            else:
                qq = ease_in(span(q, 0.5, 0.75)) if q < 0.75 else 1
                gp = (lerp(RAISED[0][0], STUCK[0][0], qq), lerp(RAISED[0][1], STUCK[0][1], qq))
                gb = lerp(RAISED[1], STUCK[1], qq)
            if t > 2.8:
                r = ease_out(span(t, 2.8, T))
                hands = [(lerp(STUCK[0][0], X0 + 2.1, r), lerp(STUCK[0][1], 49.6, r)), None]
                gp, gb = STUCK
            else:
                hands = [gp, (gp[0] - math.cos(gb) * 3, gp[1] - math.sin(gb) * 3)]
            daoshi(g, X0, GY, 1, hands=hands)
            axe(g, gp[0], gp[1], gb)
            if 2.3 < t < 2.5:
                for a in range(0, 360, 60):
                    g.px(SX + math.cos(math.radians(a)) * 6, STUMP_TOP + math.sin(math.radians(a)) * 3)
        self.mx(g, t, "log", 0, 0)
        if 2.3 < t < 2.45:
            g.mx_level = 4

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.draw(g, t)

    def exit(self, g: Gfx, t: float):
        self.draw(g, self._ht)
        fade_box(g, 1 - ease_in(span(t, 0.1, self.T["exit"])))
        if t > 0.6:
            g.mx[:] = False
            g.mx[7, 1:7] = True
