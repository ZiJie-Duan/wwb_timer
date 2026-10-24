"""掷筊（博杯）。

一对新月形筊杯，一面平、一面凸。合掌一拜，抛起，落地摇晃：
一平一凸为圣筊、两平为笑筊、两凸为阴筊（怒杯）。
本作把筊象记作爻：笑筊（两平）= 老阳 9，阴筊（两凸）= 老阴 6，
圣筊：左杯平面朝上 = 少阳 7，右杯平面朝上 = 少阴 8。六掷成卦。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, span
from ..engine.gfx import Gfx
from ..engine.scene import Omen, register
from ..engine.symbols import mx_hexagram
from .o_common import REVEAL, YAO_NAME, hexa, label, reveal

REST_X = (66, 106)
FLOOR = 57
T0, D = 0.35, 0.9
HOLD, AIR = 0.18, 0.42  # 合掌、空中
NAMES = {6: "阴筊", 7: "圣筊", 8: "圣筊", 9: "笑筊"}


def _crescent(rx=14.0, ry=11.0, rx2=9.0, ry2=5.0, n=10):
    pts = []
    for i in range(n + 1):
        a = math.pi * i / n
        pts.append((rx * math.cos(a), 3 - ry * math.sin(a)))
    for i in range(n, -1, -1):
        a = math.pi * i / n
        pts.append((rx2 * math.cos(a), 3 - ry2 * math.sin(a)))
    return pts


CRESCENT = _crescent()


def block(g: Gfx, cx: float, cy: float, rot: float, phi: float, mirror: bool = False):
    """一只筊杯：rot 平面内旋转，phi 翻转角（cos>0 平面朝上 = 空心；cos<0 凸面朝上 = 实心带高光）"""
    c = math.cos(phi)
    sy = max(abs(c), 0.12)
    cr, sr = math.cos(rot), math.sin(rot)
    pts = []
    for x, y in CRESCENT:
        x = -x if mirror else x
        y *= sy
        pts.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
    if c >= 0:
        g.d.polygon(pts, fill=0, outline=1)
        if abs(c) > 0.6:  # 平面上的木纹
            for r0 in (11.5, 10.5):  # 平面上的木纹：沿弧一道细线
                arc = [(cx + (r0 * math.cos(a)) * cr - (3 - (r0 - 3) * 0.75 * math.sin(a)) * sy * sr,
                        cy + (r0 * math.cos(a)) * sr + (3 - (r0 - 3) * 0.75 * math.sin(a)) * sy * cr)
                       for a in (0.5, 1.0, 1.57, 2.1, 2.64)]
                if r0 == 11.5:
                    g.d.line(arc, fill=1)
    else:
        g.d.polygon(pts, fill=1, outline=1)
        if abs(c) > 0.5:  # 凸面高光
            arc = [(cx + (11.5 * math.cos(a)) * cr - (3 - 6.5 * math.sin(a)) * sy * sr,
                    cy + (11.5 * math.cos(a)) * sr + (3 - 6.5 * math.sin(a)) * sy * cr)
                   for a in (1.3, 1.8, 2.3, 2.7)]
            g.d.line(arc, fill=0)


@register
class JiaobeiOmen(Omen):
    id = "o.jiaobei"
    name = "掷筊"
    desc = "一对新月筊杯合掌抛起，翻转落地摇晃：圣筊、笑筊、阴筊，六掷成卦"
    T = {"play": T0 + 6 * D + 0.25 + REVEAL}

    def setup(self):
        self.flat = [[self.rng.random() < 0.5 for _ in range(2)] for _ in range(6)]
        self.lines = []
        for a, b in self.flat:
            self.lines.append(9 if a and b else 6 if not a and not b else 7 if a else 8)
        self.tilt = [[(self.rng.random() - 0.5) * 0.5 for _ in range(2)] for _ in range(6)]

    def _blocks(self, g: Gfx, t: float, drop: float = 0.0):
        i = min(5, max(0, int((t - T0) // D)))
        u = t - T0 - i * D
        if t < T0:
            i, u = -1, 9.0
        for j in range(2):
            mirror = j == 1
            prev = self.flat[i - 1][j] if i >= 1 else True
            prev_rot = self.tilt[i - 1][j] if i >= 1 else 0.0
            cur = self.flat[i][j] if i >= 0 else True
            rot_end = self.tilt[i][j] if i >= 0 else 0.0
            end = 0.0 if cur else math.pi
            x0 = REST_X[j]
            if u < HOLD:  # 拾起、合在一起（两杯相对成一轮满月）
                p = ease_in_out(u / HOLD)
                x = lerp(x0, 86 + (5 if mirror else -5), p)
                y = lerp(FLOOR, 30, p)
                phi = lerp(0.0 if prev else math.pi, 0.0, p)
                block(g, x, y, lerp(prev_rot, 0, p) + (math.pi * 0.5 if mirror else -math.pi * 0.5) * p, phi, mirror)
            elif u < HOLD + AIR:
                s = (u - HOLD) / AIR
                x = lerp(86, x0, s) + (math.sin(s * math.pi) * (8 if mirror else -8))
                y = lerp(30, FLOOR, s) - math.sin(s * math.pi) * 22
                spin = 2 * math.pi * (2 + j * 0.5)
                phi = end + (1 - s) * spin
                rot = lerp(math.pi * 0.5 if mirror else -math.pi * 0.5, rot_end, s) + (1 - s) * (3 if mirror else -3)
                block(g, x, y, rot, phi, mirror)
            else:
                b = span(u, HOLD + AIR, HOLD + AIR + 0.3)
                rock = 0.0
                if 0 < b < 1:  # 落地摇晃（凸面着地的那只摇得更久）
                    amp = 0.35 if cur else 0.15
                    rock = amp * math.sin(b * 20) * (1 - b)
                hop = math.sin(clamp(b * 3) * math.pi) * 3 if b < 0.34 else 0
                block(g, x0, FLOOR - hop + drop, rot_end + rock, end, mirror)
                if 0 < b < 0.25:
                    for dx in (-14, 14):
                        g.px(x0 + dx, FLOOR + 5 + drop)
        return i, u

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        if t >= R0:
            k = t - R0
            self._blocks(g, T0 + 5 * D + D - 0.01, drop=ease_in(span(k, 0, 0.35)) * 22)
            reveal(g, self.lines, k)
            return
        g.d.line((44, 63, 127, 63), fill=1)
        for x in range(48, 127, 16):  # 地砖缝
            g.d.line((x, 61, x - 2, 63), fill=1)
        i, u = self._blocks(g, t)
        done = 0.0
        for n in range(6):
            land = T0 + n * D + HOLD + AIR + 0.1
            if t >= land:
                done = n + clamp((t - land) / 0.25)
        hexa(g, self.lines, done)
        if i >= 0 and u >= HOLD + AIR + 0.08:
            v = self.lines[i]
            label(g, 86, 12, f"{NAMES[v]}·{YAO_NAME[v]}", u - HOLD - AIR - 0.08)
        elif t < T0:
            g.text(86, 12, "掷筊", align="center")
        mx_hexagram(g, self.lines, int(done))
        if i >= 0 and u >= HOLD + AIR:
            for j in range(2):
                if self.flat[i][j]:
                    g.mx[7, 1 + j * 4:4 + j * 4] = True
                else:
                    g.mx[7, 2 + j * 4] = True
        elif i >= 0:
            g.mx[0, 3:5] = True
        g.mx_level = 3 if i >= 0 and HOLD + AIR <= u < HOLD + AIR + 0.08 else 1
