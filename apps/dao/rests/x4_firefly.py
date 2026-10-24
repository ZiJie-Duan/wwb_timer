"""腐草为萤：夏夜草丛里飞出萤火虫，一明一灭；不时聚成离卦。

依据：《礼记·月令》季夏之月“腐草为萤”（古人以为萤火虫由腐草化生，七十二候之一）；
      《易·说卦》“离为火”，萤是草间之火，聚成 ☲ 离卦。
入场：草叶从地面长起来，萤火虫一只只从草里亮起，飞出来。
持续：十几只萤火虫在夜空里慢慢游荡，各自呼吸似地明灭（亮时带十字光芒）；草叶随风摆，远山一线，几颗星。
      小事件：每 21 秒有一只落到草尖上，草被压弯，它在那儿慢慢闪；
      每 55 秒萤火聚成离卦三爻（上下实、中间断），定住发光，然后散开。
收场：萤火一齐往上飞散、熄灭。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, pulse, rand, span
from ..engine.fx import stars
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x4_common import mx_sprite

N = 14
G = 63
EV0, EV_P = 25.0, 55.0     # 聚成离卦
LAND_P = 21.0              # 落草尖
# 离卦 ☲：三爻（自上而下：阳、阴、阳），每爻的萤火位置
LI = [(x, 16) for x in (46, 55, 64, 73, 82)] + [(x, 26) for x in (46, 53, 75, 82)] + \
     [(x, 36) for x in (46, 55, 64, 73, 82)]
MX_LI = """
########
........
###..###
........
########
"""


@register
class Firefly(Rest):
    id = "x4.firefly"
    name = "腐草为萤"
    desc = "夏夜草丛飞起萤火，一明一灭；偶有一只落上草尖，每隔一阵萤火聚成离卦再散开"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.blades = []
        for i in range(28):
            x = i * 4.6 + self.rng.uniform(-1.5, 1.5)
            mid = 34 < x < 96 or x < 16
            h = self.rng.uniform(3, 8) if mid else self.rng.uniform(6, 18)
            self.blades.append((x, h, self.rng.uniform(-4, 4), self.rng.uniform(0, 6)))
        self.periods = [self.rng.uniform(2.2, 4.0) for _ in range(N + len(LI))]

    # ------------------------------------------------------------ 布景

    def grass(self, g: Gfx, t: float, grow: float = 1.0, bend: dict | None = None):
        for i, (x, h, lean, ph) in enumerate(self.blades):
            sw = math.sin(t * 0.7 + ph) * 1.2 + (noise(t * 0.3, 5) - 0.5) * 2
            hh = h * grow
            if bend and i == bend["i"]:
                sw += bend["b"] * 3
                hh -= bend["b"] * 2
            tip = (x + lean + sw, G - hh)
            g.d.line((x, G, (x + tip[0]) / 2 + lean * 0.2, G - hh * 0.55, tip[0], tip[1]), fill=1)

    def hills(self, g: Gfx):
        for x in range(0, 128, 3):
            y = 46 - noise(x / 30, self.seed + 1) * 9
            g.px(x, y)

    def glow(self, g: Gfx, x: float, y: float, b: float):
        """一只萤火：b 0..1 亮度"""
        if b < 0.15:
            return
        g.px(x, y)
        if b > 0.55:
            g.px(x + 1, y)
            g.px(x, y + 1)
            g.px(x + 1, y + 1)
        if b > 0.85:   # 十字光芒
            for dx, dy in ((-1, 0), (2, 0), (0, -1), (1, -1), (0, 2), (1, 2)):
                g.px(x + dx, y + dy)
            g.px(x - 2, y)
            g.px(x + 3, y)

    # ------------------------------------------------------------ 萤火的位置

    def wander(self, i: int, t: float):
        s = self.seed * 31 + i * 7
        x = 64 + (noise(t * 0.06 + i * 3.1, s) - 0.5) * 150
        y = 30 + (noise(t * 0.08 + i * 5.7, s + 1) - 0.5) * 50
        return clamp(x, 2, 125), clamp(y, 4, 56)

    def bright(self, i: int, t: float) -> float:
        p = self.periods[i]
        k = (t + rand(i, self.seed) * p) % p
        return math.sin(math.pi * clamp(k / (p * 0.55))) if k < p * 0.55 else 0.0

    def li_state(self, t: float):
        """离卦聚散：返回 (聚拢进度 0..1, 本次 k)"""
        if t < EV0:
            return 0.0, -1.0
        k = (t - EV0) % EV_P
        if k < 3.0:
            return ease_in_out(k / 3.0), k
        if k < 9.0:
            return 1.0, k
        if k < 11.0:
            return 1 - ease_in_out((k - 9.0) / 2.0), k
        return 0.0, -1.0

    def landing(self, t: float):
        """落草尖：返回 (萤火编号, 进度 0..1, 草编号) 或 None"""
        if t < 8:
            return None
        k = (t - 8) % LAND_P
        if k > 12:
            return None
        n = int((t - 8) // LAND_P)
        i = int(rand(n, self.seed + 3) * N)
        bi = 2 + int(rand(n, self.seed + 4) * (len(self.blades) - 4))
        return i, k, bi

    def draw(self, g: Gfx, t: float, grow: float = 1.0, alive: float = 1.0, rise: float = 0.0):
        stars(g, t, self.seed, n=12, box=(0, 0, 128, 30), twinkle=0.35)
        self.hills(g)
        gather, gk = self.li_state(t)
        land = self.landing(t)
        bend = None
        if land:
            i, k, bi = land
            b = span(k, 2.5, 3.2) * (1 - span(k, 9.5, 10.5))
            bend = dict(i=bi, b=b)
        self.grass(g, t, grow, bend)
        mxp = []
        if gather > 0.9:   # 聚成卦时，同一爻的萤火之间连出一道淡淡的光
            a = (gather - 0.9) * 10
            for y0, segs in ((16, ((46, 82),)), (26, ((46, 53), (75, 82))), (36, ((46, 82),))):
                for x0, x1 in segs:
                    for x in range(x0 + 2, x1, 2):
                        if rand(x + y0, int(t * 4)) < a * 0.8:
                            g.px(x, y0)
        for i in range(N + (len(LI) - N if gather > 0 else 0)):
            if rand(i, 77) > alive:
                continue
            x, y = self.wander(i, t)
            b = self.bright(i, t)
            if gather > 0 and i < len(LI):   # 飞向离卦的位置，越近越稳定地亮
                tx, ty = LI[i]
                if i >= N:                   # 多出来的几只从草里飞上来
                    x, y = 20 + i * 6, G - 4
                x, y = lerp(x, tx, gather), lerp(y, ty, gather)
                b = lerp(b, 0.8 + 0.2 * math.sin(t * 3 + i), gather)
            elif land and i == land[0]:      # 落到草尖上
                _, k, bi = land
                bx, bh, lean, ph = self.blades[bi]
                sw = math.sin(t * 0.7 + ph) * 1.2 + (noise(t * 0.3, 5) - 0.5) * 2 + bend["b"] * 3
                tx, ty = bx + lean + sw, G - bh * grow + bend["b"] * 2 - 2
                p = ease_in_out(span(k, 0, 2.5)) * (1 - ease_in_out(span(k, 10, 12)))
                x, y = lerp(x, tx, p), lerp(y, ty, p)
                if 2.5 < k < 10:
                    b = pulse(k, 2.2)
            y -= rise * (40 + rand(i, 9) * 30)
            x += rise * (rand(i, 8) - 0.5) * 30
            self.glow(g, x, y, b)
            mxp.append((x, y, b))
        return gather, mxp

    def mx(self, g: Gfx, t: float, gather: float, mxp):
        if gather > 0.85:
            mx_sprite(g, MX_LI, dy=1)
            g.mx_level = 2
            return
        for i, (x, y, b) in enumerate(mxp[:6]):   # 点阵里也有几点萤火在飘
            if b > 0.3:
                g.mx_set(int(x / 16), int(y / 8))
        g.mx[7, :] = [bool(int(t * 0.5 + i * 2.7) % 3) for i in range(8)]   # 草

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        gather, mxp = self.draw(g, t)
        _, k = self.li_state(t)
        if 3.6 < k < 9.0:     # 萤火聚成离卦时，下面写“离为火”
            s = "离为火"
            g.text(64, 41, s[:int(span(k, 3.6, 4.6) * 3 + 0.5)], align="center")
        self.mx(g, t, gather, mxp)
        g.vtext(2, 2, "腐草为萤")

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        grow = ease_out(span(t, 0, 1.2))
        stars(g, t - T, self.seed, n=int(12 * span(t, 0, 1)), box=(0, 0, 128, 30), twinkle=0.35)
        self.hills(g)
        self.grass(g, t - T, grow)
        mxp = []
        for i in range(N):   # 一只只从草里亮起来，飞到游荡的位置
            st = 0.8 + i * 0.12
            p = ease_out(span(t, st, st + 1.2))
            if p <= 0:
                continue
            x, y = self.wander(i, t - T)
            sx = x
            x, y = lerp(sx, x, p), lerp(G - 4, y, p)
            b = max(self.bright(i, t - T), 1 - p) if p < 1 else self.bright(i, t - T)
            self.glow(g, x, y, b)
            mxp.append((x, y, b))
        g.vtext(2, 2, "腐草为萤"[:int(span(t, 1.5, T) * 4 + 0.5)])
        self.mx(g, t - T, 0, mxp)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        p = ease_in(span(t, 0, T))
        gather, mxp = self.draw(g, t0 + t, alive=1 - span(t, 0.4, T), rise=p)
        g.vtext(2, 2, "腐草为萤"[:int(round((1 - span(t, 0, 0.8)) * 4))])
        self.mx(g, t0 + t, 0, mxp)
        g.fade(1 - span(t, T * 0.6, T))
