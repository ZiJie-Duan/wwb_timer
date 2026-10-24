"""辰州符·赶尸：月夜山路，赶尸匠摇着摄魂铃在前领路，后面两位额上压着黄符、头戴高筒毡帽的“客人”
一蹦一跳地跟着。一程走完路过义庄歇脚，再上路；圆满时到家：“魂归故里”。

依据：湘西民间传说“赶尸”（与“放蛊”“辰州符”并称湘西三大谜）；传说中尸体“头戴高筒毡帽，额上压着几张
书写符咒的黄纸垂在脸上”，赶尸匠“不打灯笼，手中摇着摄魂铃”，夜行晓宿。属民俗传说，非正统科仪。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import stars, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register

ROAD = 58
LEAD_X = 94
KE_X = (66, 42)          # 两位“客人”
SPEED = 4.0              # 背景每秒卷动的像素
HOP = 0.85               # 一跳的秒数
RENEW = 6.0
MOON = (58, 10)


@register
class GanShi(Ritual):
    id = "r2.ganshi"
    name = "辰州赶尸"
    desc = "月夜山路，赶尸匠摇摄魂铃领路，两位额压黄符的客人一蹦一跳跟着；一程一程地走，圆满时魂归故里"
    T = {"enter": 4.5, "interrupt": 1.5, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.s = self.rng.randrange(1000)

    # ------------------------------------------------------------ 背景

    def backdrop(self, g: Gfx, t: float, scroll: float):
        stars(g, t, self.s, n=12, box=(0, 0, 128, 28), twinkle=0.3)
        mx, my = MOON
        g.d.ellipse((mx - 5, my - 5, mx + 5, my + 5), fill=1)
        g.d.ellipse((mx - 2, my - 6, mx + 7, my + 3), fill=0)
        # 远山（慢）
        far = scroll * 0.15
        pts = [(x, 34 - 12 * noise((x + far) * 0.03, self.s) - 5 * noise((x + far) * 0.11, self.s + 3))
               for x in range(0, 129, 4)]
        g.d.polygon([(0, 50)] + pts + [(128, 50)], fill=0)
        g.d.line(pts, fill=1)
        # 近处的松树（快）
        gap = 46
        off = scroll % gap
        for j in range(-1, 4):
            idx = int(scroll // gap) + j
            x = j * gap - off + 20 + rand(idx, self.s) * 14
            if rand(idx + 50, self.s) < 0.35:
                continue
            h = 14 + rand(idx + 9, self.s) * 10
            self.pine(g, x, ROAD, h)
        # 路与石子
        g.d.line((0, ROAD + 1, 127, ROAD + 1), fill=1)
        for j in range(12):
            x = (j * 23 - scroll) % 140 - 6 + rand(j, 7) * 6
            g.px(x, ROAD + 3 + (j % 3))
        # 里程石：每 150 秒的路程一块
        stone_gap = 150 * SPEED
        sx = 140 - (scroll % stone_gap)
        if -10 < sx < 130:
            g.d.rectangle((sx, ROAD - 9, sx + 5, ROAD), fill=0, outline=1)
            g.d.line((sx + 2, ROAD - 7, sx + 2, ROAD - 3), fill=1)

    def pine(self, g: Gfx, x: float, base: float, h: float):
        g.d.line((x, base, x, base - h), fill=1)
        for k in range(3):
            y = base - h + 3 + k * h * 0.25
            w = 3 + k * 2.5
            g.d.polygon([(x, y - 5), (x - w, y + 1), (x + w, y + 1)], fill=0, outline=1)

    # ------------------------------------------------------------ 人物

    def ke(self, g: Gfx, cx: float, hop: float, sw: float, t: float, i: int):
        """客人：hop = 离地高度（像素），sw = 符纸被风掀起的程度（0..1）"""
        y = ROAD - hop
        g.d.line((cx - 1, y - 8, cx - 1, y), fill=1)          # 并拢的双脚
        g.d.line((cx + 1, y - 8, cx + 1, y), fill=1)
        robe = [(cx - 4, y - 22), (cx + 4, y - 22), (cx + 5, y - 6), (cx - 5, y - 6)]
        g.d.polygon(robe, fill=0)
        g.shade_poly(robe, 0.5)
        g.d.rectangle((cx + 1, y - 21, cx + 13, y - 18), fill=0, outline=1)   # 平伸的双臂（袖）
        g.d.line((cx + 13, y - 21, cx + 15, y - 21), fill=1)                # 手指
        g.d.line((cx + 13, y - 18, cx + 15, y - 18), fill=1)
        g.d.rectangle((cx - 3, y - 28, cx + 3, y - 22), fill=0, outline=1)  # 头
        g.d.rectangle((cx - 3, y - 37, cx + 3, y - 29), fill=0, outline=1)  # 高筒毡帽
        g.d.line((cx - 5, y - 29, cx + 5, y - 29), fill=1)
        # 额上的黄符：上沿压在帽檐下，下沿随跳动飘
        lift = sw * 6
        top = y - 29
        pts = [(cx + 1, top), (cx + 5, top), (cx + 5 + lift, top + 9 - lift * 0.6), (cx + 1 + lift, top + 9 - lift * 0.6)]
        g.d.polygon(pts, fill=0, outline=1)
        g.d.line((cx + 3 + lift * 0.4, top + 2, cx + 3 + lift * 0.8, top + 7 - lift * 0.5), fill=1)

    def lead(self, g: Gfx, x: float, t: float, walk: float, ring: float, bell_up: float = 1.0):
        """赶尸匠：斗笠、道袍，右手高举摄魂铃。walk = 步伐相位，ring = 摇铃（0..1）"""
        y = ROAD
        a = math.sin(walk * math.pi * 2) * 4
        g.d.line((x, y - 9, x - a, y), fill=1)                     # 腿
        g.d.line((x, y - 9, x + a, y), fill=1)
        robe = [(x - 3, y - 24), (x + 3, y - 24), (x + 6, y - 7), (x - 6, y - 7)]
        g.d.polygon(robe, fill=0)
        g.shade_poly(robe, 0.25)
        g.d.line((x - 3, y - 24, x + 1, y - 16), fill=1)            # 交领
        g.d.ellipse((x - 3, y - 30, x + 3, y - 24), fill=0, outline=1)
        g.d.polygon([(x - 10, y - 29), (x + 10, y - 29), (x, y - 36)], fill=0, outline=1)   # 斗笠
        g.d.line((x - 10, y - 29, x + 10, y - 29), fill=1)
        # 举铃的手
        sx, sy = x + 3, y - 21
        hx, hy = lerp(x + 7, x + 9, bell_up), lerp(y - 14, y - 32, bell_up)
        g.d.line((sx, sy, hx, hy), fill=1)
        g.d.line((sx + 1, sy, hx + 1, hy), fill=1)
        sw = math.sin(ring * math.pi * 4) * 0.6 * (1 - ring) if ring > 0 else 0
        bx, by = hx + math.sin(sw) * 4, hy + 2 + math.cos(sw) * 3
        g.d.line((hx, hy, bx, by), fill=1)
        g.d.polygon([(bx - 2, by), (bx + 2, by), (bx + 3, by + 4), (bx - 3, by + 4)], fill=1)
        if 0 < ring < 0.8:  # 叮——声波
            r = 3 + ring * 10
            for k in (0, 1):
                rr = r + k * 4
                g.d.arc((bx - rr, by + 2 - rr, bx + rr, by + 2 + rr), -50, 50, fill=1)

    def hop(self, t: float, i: int, moving: bool = True) -> tuple[float, float]:
        if not moving:
            return 0.0, 0.0
        ph = (t / HOP + i * 0.42) % 1
        h = math.sin(ph * math.pi) * 7
        sw = clamp(math.sin(ph * math.pi) * 1.1 - 0.1) if ph < 0.6 else clamp(1 - (ph - 0.6) * 2.5) * 0.4
        return h, sw

    def bell_ring(self, t: float) -> float:
        """每 2 秒摇一下"""
        k = t % 2.0
        return k / 0.9 if k < 0.9 else 0.0

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        left = "辰州符"
        g.vtext(2, 2, left[:int(round(a * 3))])
        r = right if right is not None else f"第{cn_num(n)}程"
        g.vtext(115, 2, r[:int(round(a * len(r)))])

    def mx(self, g: Gfx, hop: float, sw: float, ring: float):
        y = 1 - int(round(hop / 7))
        rows = ["..##....", "..##....", ".####...", "..######", "..##....", "..##....", "..#.#..."]
        for r, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    g.mx_set(x, r + y)
        g.mx_set(4, 2 + y, sw > 0.3)
        if 0 < ring < 0.5:
            g.mx_set(7, 0)
            g.mx_set(6, 1)

    def procession(self, g: Gfx, t: float, moving: bool = True, ring_t: float | None = None, bell_up: float = 1.0):
        ring = self.bell_ring(t) if ring_t is None else ring_t
        hs = []
        for i, x in enumerate(KE_X):
            h, sw = self.hop(t, i, moving)
            self.ke(g, x, h, sw, t, i)
            hs.append((h, sw))
        self.lead(g, LEAD_X, t, t * 0.7 if moving else 0.25, ring, bell_up)
        return hs, ring

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.backdrop(g, t, (t - self.T["enter"]) * SPEED)
        # 三人从左边雾里依次跳进来
        k = span(t, 0, 3.4)
        for i, x in enumerate(KE_X):
            xi = lerp(-20 - i * 18, x, ease_out(span(k, 0.1 * i, 0.75 + 0.1 * i)))
            h, sw = self.hop(t, i)
            self.ke(g, xi, h, sw, t, i)
        lx = lerp(-10, LEAD_X, ease_out(span(k, 0, 0.7)))
        self.lead(g, lx, t, t * 0.7, self.bell_ring(t))
        for j in range(18):  # 雾
            x = (j * 9 + t * 6) % 70 - 10
            if rand(j, 3) > span(t, 1.5, 4.0):
                g.d.line((x, 40 + j % 5 * 4, x + 8, 40 + j % 5 * 4), fill=1)
        self.texts(g, 0, a=span(t, 3.0, 4.5))
        h, sw = self.hop(t, 0)
        self.mx(g, h, sw, self.bell_ring(t))

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, e)
            return
        self.backdrop(g, t, e * SPEED)
        hs, ring = self.procession(g, t)
        self.texts(g, e)
        self.mx(g, hs[0][0], hs[0][1], ring)

    def yizhuang(self, g: Gfx, x: float, lit: bool, t: float, name: str = "义庄"):
        """路边的义庄：屋檐、门、门上匾"""
        g.d.rectangle((x, 30, x + 34, ROAD), fill=0, outline=1)
        g.d.polygon([(x - 6, 31), (x + 4, 22), (x + 30, 22), (x + 40, 31)], fill=0, outline=1)
        for xx in range(int(x) - 2, int(x) + 37, 3):
            g.d.line((xx, 31, xx + 2, 26), fill=1)
        g.d.rectangle((x + 11, 40, x + 23, ROAD), fill=0, outline=1)
        if lit:
            g.d.rectangle((x + 12, 41, x + 22, ROAD - 1), fill=1)
            g.d.line((x + 17, 41, x + 17, ROAD - 1), fill=0)
        g.text(x + 17, 32, name, size=8, align="center")
        g.d.ellipse((x + 2, 36, x + 7, 42), fill=1 if blink(t, 1.3, 0.8) else 0, outline=1)  # 灯笼

    def _renew(self, g: Gfx, t: float, u: float, e: float):
        """一程走完：路过义庄，门里亮着灯，铃响三下，再上路"""
        self.backdrop(g, t, e * SPEED)
        x = lerp(130, -40, u / RENEW)
        self.yizhuang(g, x, True, t)
        hs, ring = self.procession(g, t)
        n = int(e // self.CYCLE) + 1
        self.texts(g, e - (u if u < RENEW / 2 else 0))
        if RENEW / 2 - 0.3 < u < RENEW / 2 + 0.3:
            g.d.rectangle((113, 2, 127, 40), fill=0)
            if blink(u, 0.15):
                self.texts(g, e)
        self.mx(g, hs[0][0], hs[0][1], ring)

    def interrupt(self, g: Gfx, t: float, e: float):
        """铃一按，众“客人”落地站定"""
        self.backdrop(g, t, e * SPEED)
        # 跳到一半的落下来
        f = ease_in(span(t, 0, 0.4))
        for i, x in enumerate(KE_X):
            h, sw = self.hop(t, i)
            self.ke(g, x, h * (1 - f), sw * (1 - span(t, 0.3, 1.0)), t, i)
        self.lead(g, LEAD_X, t, 0.25, 0.0, bell_up=1 - ease_in_out(span(t, 0.3, 1.0)))
        if 0.4 < t < 0.6:  # 落地扬尘
            for i, x in enumerate(KE_X):
                for d in (-1, 1):
                    g.px(x + d * (3 + (t - 0.4) * 30), ROAD - 1)
        self.texts(g, e, right="暂歇")
        self.mx(g, 0, 0, 0)

    def resume(self, g: Gfx, t: float, e: float):
        """铃响三声，再上路"""
        self.backdrop(g, t, e * SPEED)
        up = ease_out_back(span(t, 0, 0.5))
        ring = (t - 0.4) % 0.45 / 0.45 if 0.4 < t < 1.75 else 0.0
        moving = t > 1.2
        for i, x in enumerate(KE_X):
            h, sw = self.hop(t, i, moving)
            self.ke(g, x, h, sw, t, i)
        self.lead(g, LEAD_X, t, t * 0.7 if moving else 0.25, ring, bell_up=up)
        self.texts(g, e)
        h, sw = self.hop(t, 0, moving)
        self.mx(g, h, sw, ring)

    def complete(self, g: Gfx, t: float, e: float):
        """到家：村口人家亮着灯，客人停下——魂归故里"""
        stop = span(t, 0, 2.2)
        scroll = e * SPEED + ease_out(stop) * 40
        self.backdrop(g, t, scroll)
        x = lerp(130, 98, ease_out(stop))
        self.yizhuang(g, x, True, t, name="故里")
        moving = t < 2.0
        hs = []
        for i, kx in enumerate(KE_X):
            h, sw = self.hop(t, i, moving)
            self.ke(g, kx, h, sw, t, i)
            hs.append(h)
        lx = lerp(LEAD_X, LEAD_X - 6, ease_out(stop))
        self.lead(g, lx, t, t * 0.7 if moving else 0.25, self.bell_ring(t) if t < 2.5 else 0.0,
                  bell_up=1 - ease_in_out(span(t, 2.5, 3.2)))
        if t > 2.6:  # 门里的光洒出来
            for j in range(6):
                yy = 42 + j * 3
                g.d.line((x + 10, yy, x + 10 - span(t, 2.6, 3.4) * (16 + j * 3), yy + 2), fill=1)
            g.d.rectangle((14, 2, 102, 15), fill=0)
            typewriter(g, 58, 3, "魂归故里", t - 2.8, cps=4, align="center")
        self.texts(g, e, right="到家" if t > 2.6 else None)
        self.mx(g, hs[0] if moving else 0, 0, 0)
        if t > 2.6:
            g.mx_level = 1 + int(3 * (1 - span(t, 2.6, 4.0)))
