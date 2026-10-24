"""补衲：夜里一盏油灯，小道士盘腿坐着补道袍（近景，人放大）。一针下去、一针上来，线拉得老长；
补丁四周的针脚一针针多起来。补完：低头咬断线头，把道袍举起来对着灯照一照，满意。再换一处破洞，
先眯着眼对着灯穿针——线头戳偏两次才穿进去。飞蛾绕着灯打转。窗外一弯月。
右侧竖写“大成若缺”（《道德经》四十五章：大成若缺，其用不弊）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import flame, ring
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x5_common import daoshi, dpoly, fade_box, near_arm, phase

S = 1.6          # 人放大
X = 30
SEAT = 61
LAMP = (96, 38)  # 灯盏
STITCH = 2.0
NST = 14         # 一块补丁几针
THREAD_T = 6.0   # 穿针
SHOW_T = 6.0     # 咬线、举起来看
BIG = THREAD_T + NST * STITCH + SHOW_T


@register
class Mend(Rest):
    id = "x5.mend"
    name = "补衲"
    desc = "油灯下补道袍：穿针、一针针缝、咬断线头举起来照——大成若缺"
    T = {"enter": 3.0, "exit": 1.4}

    def setup(self):
        self.s = self.rng.randrange(1000)
        self._ht = 0.0

    # ------------------------------------------------------------ 景

    def window(self, g: Gfx):
        x0, y0, x1, y1 = 52, 4, 80, 26
        g.d.rectangle((x0, y0, x1, y1), outline=1)
        g.d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), outline=1)
        # 一弯月（大圆减小圆）
        g.d.ellipse((66, 8, 75, 17), fill=1)
        g.d.ellipse((63, 6, 72, 15), fill=0)
        for x in range(x0 + 7, x1, 7):   # 窗棂
            g.d.line((x, y0 + 1, x, y1 - 1), fill=1)
        g.d.line((x0 + 1, (y0 + y1) // 2, x1 - 1, (y0 + y1) // 2), fill=1)

    def lamp(self, g: Gfx, t: float, lit: float = 1.0, flick: float = 0.0):
        x, y = LAMP
        d = g.d
        d.line((x, y + 2, x, SEAT - 1), fill=1)
        d.line((x + 1, y + 2, x + 1, SEAT - 1), fill=1)
        d.polygon([(x - 5, SEAT), (x + 6, SEAT), (x + 3, SEAT - 3), (x - 2, SEAT - 3)], fill=1)
        d.chord((x - 6, y - 2, x + 7, y + 4), 0, 180, fill=0, outline=1)
        d.line((x - 6, y + 1, x + 7, y + 1), fill=1)
        if lit > 0:
            h = (7 + flick * 3) * lit
            flame(g, x + 1, y, 4 * lit + 1, h, t * (1 + flick * 3), 7)
            for r, dens in ((13, 3), (18, 4)):
                rr = r + noise(t * 2, 3) * 1.5
                ring(g, x + 1, y - 4, rr * lit, dens, t * 0.2)

    def moth(self, g: Gfx, t: float):
        a = t * 1.7
        r = 9 + 4 * math.sin(t * 0.43)
        x = LAMP[0] + 1 + math.cos(a) * r
        y = LAMP[1] - 6 + math.sin(a) * r * 0.6 + math.sin(t * 5) * 1
        wing = int(t * 14) % 2
        g.px(x, y)
        g.px(x - 1, y - wing)
        g.px(x + 1, y - wing)
        return math.hypot(x - LAMP[0], y - LAMP[1] + 6) < 7

    def floor(self, g: Gfx):
        g.d.line((0, SEAT + 1, 127, SEAT + 1), fill=1)
        g.d.ellipse((X - 18, SEAT - 3, X + 22, SEAT + 4), outline=1)   # 蒲团

    # ------------------------------------------------------------ 衣与针

    def robe(self, g, lift: float, patch: int, stitches: int, hold_pts):
        """膝上摊着的道袍（从腰前一直垂到地上）：lift 0..1 双手举起来"""
        (ax, ay), (bx, by) = hold_pts
        base = SEAT - 1
        # 摊着时：上沿搭在膝上，前沿垂地，下摆有几道褶
        p0 = (lerp(X + 4, ax - 2, lift), lerp(SEAT - 17, ay, lift))
        p1 = (lerp(X + 33, bx + 2, lift), lerp(SEAT - 18, by - 1, lift))
        p2 = (lerp(X + 42, bx + 5, lift), lerp(base, by + 22, lift))
        p3 = (lerp(X + 8, ax - 5, lift), lerp(base, ay + 24, lift))
        hem = []
        for j in range(5):  # 下沿起伏
            u = j / 4
            hem.append((lerp(p2[0], p3[0], u), lerp(p2[1], p3[1], u) - (1.5 if j % 2 else 0)))
        pts = [p0, p1] + hem
        cx = lerp((p0[0] + p1[0]) / 2, (p2[0] + p3[0]) / 2, 0.42) + (patch % 3 - 1) * 2
        cy = lerp((p0[1] + p1[1]) / 2, (p2[1] + p3[1]) / 2, 0.42)
        w, h = 6, 4
        per = self.stitch_points(cx, cy, w, h)
        if g is None:
            return per
        dpoly(g, pts, 0.25)
        for j in (1, 3):  # 褶
            u = j / 4
            x0, y0 = lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u)
            x1, y1 = hem[4 - j]
            g.d.line((lerp(x0, x1, 0.55), lerp(y0, y1, 0.55), x1, y1), fill=0)
        g.d.rectangle((cx - w, cy - h, cx + w, cy + h), fill=0, outline=1)
        g.d.line((cx - w + 2, cy - h + 2, cx + w - 2, cy - h + 2), fill=1)   # 补丁布纹
        for i in range(min(stitches, NST)):
            px, py = per[i]
            g.px(px, py)
            g.px(px + (1 if i < 4 or 7 <= i < 11 else 0), py + (0 if i < 4 or 7 <= i < 11 else 1))
        return per

    @staticmethod
    def stitch_points(cx, cy, w, h):
        pts = []
        for i in range(NST):
            u = i / NST * 4
            side, k = int(u), u - int(u)
            if side == 0:
                pts.append((cx - w + 2 * w * k, cy - h - 2))
            elif side == 1:
                pts.append((cx + w + 2, cy - h + 2 * h * k))
            elif side == 2:
                pts.append((cx + w - 2 * w * k, cy + h + 2))
            else:
                pts.append((cx - w - 2, cy + h - 2 * h * k))
        return pts

    # ------------------------------------------------------------ 主画面

    def draw(self, g: Gfx, t: float, lit: float = 1.0):
        big, k = phase(t, BIG)
        self.window(g)
        self.floor(g)
        near_moth = self.moth(g, t) if lit > 0.5 else False
        self.lamp(g, t, lit, 1.0 if near_moth else 0.0)
        far_hand = (X + 13, SEAT - 13)
        lift = 0.0
        stitches = 0
        hand = (X + 18, SEAT - 14)
        eye = "closed" if (t % 4.6) < 0.14 else "open"
        look = 1.0
        lean = 2.0
        needle_at = None
        thread_from = None
        if k < THREAD_T:  # 穿针：举到灯前，眯眼
            stitches = 0
            q = ease_in_out(span(k, 0, 1.0)) * (1 - ease_in_out(span(k, 5.2, 6.0)))
            hand = (lerp(X + 18, X + 27, q), lerp(SEAT - 14, SEAT - 32, q))
            far_hand = (lerp(X + 13, X + 22, q), lerp(SEAT - 13, SEAT - 30, q))
            look = -0.5 * q
            eye = "closed" if 1.0 < k < 4.6 else eye
            lean = 2 + q * 2
        elif k < THREAD_T + NST * STITCH:
            kk = k - THREAD_T
            i, c = phase(kk, STITCH)
            stitches = i
            lift = 0.0
        else:  # 咬线头，举起来照
            stitches = NST
            kk = k - THREAD_T - NST * STITCH
            if kk < 1.6:  # 低头咬
                q = math.sin(span(kk, 0, 1.6) * math.pi)
                lean = 2 + q * 4
                look = 1 + q * 1.5
                hand = (X + 18 - q * 3, SEAT - 14 - q * 4)
            else:
                q = ease_in_out(span(kk, 1.6, 2.6)) * (1 - ease_in_out(span(kk, 5.0, 6.0)))
                lift = q
                hand = (lerp(X + 18, X + 30, q), lerp(SEAT - 14, SEAT - 38, q))
                far_hand = (lerp(X + 13, X + 14, q), lerp(SEAT - 13, SEAT - 38, q))
                look = 1 - q * 2.5
                eye = "closed" if 3.0 < kk < 4.8 else eye
                lean = 2 - q * 2
        # 衣服的位置（先算出针脚，好知道手在哪）
        hold_pts = (far_hand, hand)
        per = self.robe(None, lift, big, stitches, hold_pts)
        if THREAD_T <= k < THREAD_T + NST * STITCH:
            kk = k - THREAD_T
            i, c = phase(kk, STITCH)
            sp = per[min(i, NST - 1)]
            nxt = per[min(i + 1, NST - 1)]
            if c < 0.5:  # 针扎下去
                q = ease_in(c / 0.5)
                needle_at = (lerp(sp[0] + 3, sp[0], q), lerp(sp[1] - 4, sp[1], q))
            elif c < 0.7:  # 从下一针的位置冒出来
                needle_at = (nxt[0], nxt[1])
            else:  # 拉线：一条长弧，再落回来
                q = ease_out(span(c, 0.7, 1.5))
                back = ease_in_out(span(c, 1.5, STITCH))
                top = (X + 42, SEAT - 46)
                needle_at = (lerp(lerp(nxt[0], top[0], q), nxt[0] + 3, back),
                             lerp(lerp(nxt[1], top[1], q), nxt[1] - 4, back))
            hand = (needle_at[0] + 1, needle_at[1] - 1)
            thread_from = sp if c < 0.5 else nxt
        # 人（先画，近手臂留到最后），再画搭在膝上的衣服，再画近手臂
        pz = daoshi(g, X, SEAT, 1, hands=[hand, far_hand], lean=lean, crouch=0.75, s=S, sit=True, eye=eye,
                    look=look, draw_near=False)
        self.robe(g, lift, big, stitches, hold_pts)
        pz.near = near_arm(g, pz, hand)
        if k < THREAD_T:
            # 穿针：针竖着，线头一点点凑近针眼，偏了两次
            nx, ny = hand[0] + 1, hand[1] - 3
            g.d.line((nx, ny, nx, ny - 6), fill=1)
            g.px(nx, ny - 5)  # 针眼
            g.d.point((nx, ny - 5))
            tx_, ty_ = far_hand[0] + 2, far_hand[1] - 4
            tries = [(1.2, 2.2, 3), (2.4, 3.4, -3), (3.6, 4.6, 0)]
            ex, ey = tx_, ty_
            for a, b, miss in tries:
                if k >= a:
                    q = ease_in_out(span(k, a, b - 0.3))
                    back = ease_in(span(k, b - 0.25, b)) if miss else 0
                    ex = lerp(tx_, nx + miss * 0.7, q * (1 - back))
                    ey = lerp(ty_, ny - 5 + miss * 0.3, q * (1 - back))
            g.d.line((far_hand[0], far_hand[1], ex, ey), fill=1)
            if 4.4 < k < 5.0:  # 穿过去了：一闪
                g.px(nx + 3, ny - 8)
                g.px(nx - 3, ny - 8)
                g.px(nx, ny - 10)
        if needle_at:
            nx, ny = needle_at
            g.d.line((nx, ny, nx + 2, ny - 4), fill=1)
            if thread_from:
                # 线：从布上的针脚到针尾，稍微下垂
                mx_, my_ = (thread_from[0] + nx) / 2, max(thread_from[1], ny) + 3
                g.d.line((thread_from[0], thread_from[1], mx_, my_ - 2, nx + 2, ny - 4), fill=1)
        if not (THREAD_T <= k < THREAD_T + NST * STITCH) and k >= THREAD_T:
            kk = k - THREAD_T - NST * STITCH
            if 0.6 < kk < 1.0:  # 咬断：一点线头飞走
                g.px(pz.head[0] + 6 + (kk - 0.6) * 15, pz.head[1] + 4 - (kk - 0.6) * 10)
            if 3.0 < kk < 4.8:  # 举起来照灯：补丁边闪一下
                for j in range(4):
                    a = kk * 3 + j * 1.57
                    g.px(X + 26 + math.cos(a) * 12, SEAT - 26 + math.sin(a) * 8)
        self.text(g)
        self.mx(g, t, k, stitches)

    def text(self, g: Gfx, a: float = 1.0):
        s = "大成若缺"
        g.vtext(115, 2, s[:int(round(len(s) * clamp(a)))])

    def mx(self, g: Gfx, t: float, k: float, stitches: int):
        # 补丁一圈针脚：随针数一格格亮起（隔一格一针）
        cells = [(x, 0) for x in range(8)] + [(7, y) for y in range(1, 8)] + [(x, 7) for x in range(6, -1, -1)] + \
                [(0, y) for y in range(6, 0, -1)]
        n = int(len(cells) * stitches / NST)
        for i in range(min(n, len(cells))):
            if i % 2 == 0:
                g.mx_set(*cells[i])
        # 中间：针一上一下
        y = 2 + int(abs(math.sin(t * math.pi / STITCH)) * 3)
        g.mx_set(4, y)
        g.mx_set(4, y + 1)
        g.mx_set(3, y + 2)
        if stitches >= NST and THREAD_T + NST * STITCH + 3 < k < THREAD_T + NST * STITCH + 4.8:
            g.mx_level = 3

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        """黑暗里划着火柴点灯，屋里亮起来"""
        T = self.T["enter"]
        lit = ease_out(span(t, 1.0, 1.6))
        self.draw(g, 0.0, lit)
        fade_box(g, 0.15 + 0.85 * ease_in_out(span(t, 1.0, 2.6)))
        if t < 1.3:  # 火柴
            x, y = LAMP[0] + 8 - span(t, 0.3, 1.0) * 6, LAMP[1] - 6 + span(t, 0.3, 1.0) * 4
            g.d.line((x, y, x + 8, y + 6), fill=1)
            if t > 0.3:
                flame(g, x, y, 3, 5, t, 2)
        g.d.rectangle((113, 0, 127, 63), fill=0)
        self.text(g, span(t, 1.8, T - 0.2))

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.draw(g, t)

    def exit(self, g: Gfx, t: float):
        """吹灯：火苗一歪就灭，屋里暗下去"""
        T = self.T["exit"]
        lit = 1 - ease_in(span(t, 0.2, 0.6))
        self.draw(g, self._ht, lit)
        if 0.1 < t < 0.6:  # 吹的一口气
            for j in range(3):
                y = LAMP[1] - 6 + j * 3
                x0 = LAMP[0] - 16 + span(t, 0.1, 0.6) * 14
                g.d.line((x0, y, x0 + 5, y), fill=1)
        if 0.6 < t < 1.1:  # 一缕青烟
            from ..engine.fx import smoke_wisp
            smoke_wisp(g, LAMP[0] + 1, LAMP[1] - 1, 10 * span(t, 0.6, 1.0), t, 3)
        fade_box(g, 1 - ease_in(span(t, 0.5, T)))
        if t > 0.6:
            g.mx[:] = False
            g.mx_set(4, 7)
