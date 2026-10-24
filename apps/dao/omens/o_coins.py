"""铜钱六爻（三钱法 / 火珠林法）。

三枚方孔钱一齐抛起、翻转、落地弹跳，看“背”“字”：
一背为单（少阳 7）、两背为拆（少阴 8）、三背为重（老阳 9）、三字为交（老阴 6）。
六次自下而上成卦，卦象在左边逐爻长出。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_out, span
from ..engine.gfx import Gfx
from ..engine.scene import Omen, register
from .o_common import REVEAL, YAO_NAME, hexa, label, reveal

COIN_X = (60, 84, 108)
GROUND = 55          # 落地时钱心
R = 7
T0, D = 0.25, 0.85   # 第一次抛的时刻、每爻间隔
AIR = 0.55           # 空中时长
CALL = {6: "交", 7: "单", 8: "拆", 9: "重"}


def coin(g: Gfx, cx: float, cy: float, phi: float, r: float = R):
    """方孔钱：phi 为翻转角，cos>0 见“字”面（四字为四点），cos<0 见“背”面（实心）"""
    c = math.cos(phi)
    rw = abs(c) * r
    if rw < 1.2:
        g.d.line((cx, cy - r, cx, cy + r), fill=1)
        return
    box = (cx - rw, cy - r, cx + rw, cy + r)
    hole = max(1, rw * 0.28)
    if c < 0:  # 背：实心，挖方孔，内郭一圈暗线
        g.d.ellipse(box, fill=1)
        if rw > 3:
            g.d.ellipse((cx - rw + 2, cy - r + 2, cx + rw - 2, cy + r - 2), outline=0)
        g.d.rectangle((cx - hole, cy - 2, cx + hole, cy + 2), fill=0)
    else:      # 字：空心，方孔外框，上下左右四个字
        g.d.ellipse(box, outline=1, fill=0)
        g.d.rectangle((cx - hole - 1, cy - 3, cx + hole + 1, cy + 3), outline=1)
        if rw > 3.5:
            k = rw / r
            for dx, dy in ((0, -4.5), (0, 4.5), (-4.5, 0), (4.5, 0)):
                x, y = cx + dx * k, cy + dy
                g.d.rectangle((x - 0.5, y - 0.5, x + 0.5, y + 0.5), fill=1)


@register
class CoinsOmen(Omen):
    id = "o.coins"
    name = "金钱课"
    desc = "三枚方孔钱抛起翻转落地，六掷成卦：单拆重交，卦象自下而上长出"
    T = {"play": T0 + 6 * D + 0.2 + REVEAL}

    def setup(self):
        # 每掷三枚：True = 背（记 3），False = 字（记 2）
        self.toss = [[self.rng.random() < 0.5 for _ in range(3)] for _ in range(6)]
        self.lines = [sum(3 if b else 2 for b in tr) for tr in self.toss]

    def _coins(self, g: Gfx, t: float, sink: float = 0.0):
        i = min(5, max(0, int((t - T0) // D)))
        u = t - T0 - i * D
        if t < T0:
            i, u = -1, 9.0  # 开场：钱静静躺着（字面朝上）
        for j, x in enumerate(COIN_X):
            back = self.toss[i][j] if i >= 0 else False
            end = math.pi if back else 0.0
            uj = u - j * 0.05
            if 0 <= uj < AIR:
                s = uj / AIR
                y = GROUND - 36 * 4 * s * (1 - s)
                spin = (2 * math.pi) * (3 + j * 0.5)
                phi = end + (1 - s) * spin
                xx = x + math.sin(s * math.pi) * (j - 1) * 4
                coin(g, xx, y, phi)
            else:
                b = span(uj, AIR, AIR + 0.18)
                hop = math.sin(b * math.pi) * 3 if 0 < b < 1 else 0
                wob = 0.35 * math.sin(b * 18) * (1 - b) if 0 < b < 1 else 0
                coin(g, x, GROUND - hop + sink, end + wob)
                if 0 < b < 0.4:  # 落地一点尘
                    g.px(x - R - 2, GROUND + R - 1 + sink)
                    g.px(x + R + 2, GROUND + R - 1 + sink)
        return i, u

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        if t >= R0:
            k = t - R0
            self._coins(g, T0 + 5 * D + 0.8, sink=ease_in(span(k, 0, 0.35)) * 20)
            reveal(g, self.lines, k)
            return
        g.d.line((44, 63, 127, 63), fill=1)
        for x in range(46, 127, 6):  # 桌布纹
            g.px(x, 62)
        i, u = self._coins(g, t)
        # 左边卦象：落地后 0.1 秒长出
        done = 0.0
        for n in range(6):
            land = T0 + n * D + AIR + 0.12
            if t >= land:
                done = n + clamp((t - land) / 0.25)
        hexa(g, self.lines, done)
        if i >= 0 and u >= AIR + 0.1:
            v = self.lines[i]
            label(g, 84, 22, f"{CALL[v]}·{YAO_NAME[v]}", u - AIR - 0.1)
        elif t < T0 + 0.2:
            g.text(84, 22, "金钱课", align="center")
        # 点阵：已成之爻 + 底行三钱（背亮）+ 空中时顶行闪
        from ..engine.symbols import mx_hexagram
        mx_hexagram(g, self.lines, int(done))
        if i >= 0:
            if u < AIR:
                g.mx[0, int(u * 20) % 8] = True
            else:
                for j in range(3):
                    if self.toss[i][j]:
                        g.mx[7, 1 + j * 2:3 + j * 2] = True
        g.mx_level = 3 if i >= 0 and AIR <= u < AIR + 0.08 else 1
