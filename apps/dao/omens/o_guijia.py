"""龟卜（灼龟观兆）。

商周卜法：龟腹甲背面先施钻凿，以燃着的荆木（楚焞）灼其钻处，正面爆出“卜”形裂纹（兆）——
直的一道为兆干，横出的一枝为兆枝，“卜”字即象其形。
本作沿千里路（中缝）两侧自下而上灼六处，以兆枝定爻：一枝直出为阳、枝分两岔为阴，
再生碎纹者为变（老阳/老阴）。六兆成卦。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import Particles, flame, smoke_wisp
from ..engine.gfx import Gfx
from ..engine.scene import Omen, register
from ..engine.symbols import cast_coins, changing, mx_hexagram, yang
from .o_common import REVEAL, YAO_NAME, hexa, label, reveal

MX = 88  # 千里路
SHELL = [(76, 2), (100, 2), (104, 7), (106, 16), (111, 22), (111, 40), (106, 46), (104, 56), (98, 62), (78, 62),
         (72, 56), (70, 46), (65, 40), (65, 22), (70, 16), (72, 7)]
SEAMS = [(12, 1), (24, -1), (40, 1), (51, -1)]
T0, D = 1.05, 0.62
BURN = 0.32


def pit_pos(i: int) -> tuple[float, float]:
    return (MX - 10 if i % 2 == 0 else MX + 10), 55 - i * 9


@register
class GuijiaOmen(Omen):
    id = "o.guijia"
    name = "龟卜"
    desc = "龟腹甲施钻凿，荆火逐一灼之，爆出“卜”形兆纹：枝直为阳、分岔为阴、碎纹为变"
    T = {"play": T0 + 6 * D + 0.25 + REVEAL}

    def setup(self):
        self.lines = cast_coins(self.rng)

    def shell(self, g: Gfx, dx: float = 0.0):
        pts = [(x + dx, y) for x, y in SHELL]
        g.d.polygon(pts, fill=0, outline=1)
        # 千里路（微曲）与盾纹
        prev = None
        for y in range(3, 62, 3):
            x = MX + dx + (noise(y * 0.2, 5) - 0.5) * 1.5
            if prev:
                g.d.line((prev[0], prev[1], x, y), fill=1)
            prev = (x, y)
        for y, s in SEAMS:  # 盾纹（虚线）
            for x in range(67, 110, 2):
                g.px(x + dx, y + s * 2 * abs(x - MX) / 21)

    def pit(self, g: Gfx, i: int, p: float, burnt: bool, dx: float = 0.0):
        """钻凿：长槽（凿）+ 圆窝（钻）"""
        if p <= 0:
            return
        x, y = pit_pos(i)
        x += dx
        h = 3.5 * min(1, p)
        g.d.rectangle((x - 1, y - h, x + 1, y + h), fill=1 if burnt else 0, outline=1)
        side = -1 if i % 2 == 0 else 1
        g.d.ellipse((x + side * 4 - 2, y - 2, x + side * 4 + 2, y + 2), outline=1, fill=1 if burnt else 0)

    def crack(self, g: Gfx, i: int, p: float, dx: float = 0.0):
        """“卜”形兆：兆干沿凿上下裂开，兆枝向外横出"""
        if p <= 0:
            return
        x, y = pit_pos(i)
        x += dx
        v = self.lines[i]
        side = -1 if i % 2 == 0 else 1
        trunk = ease_out(clamp(p * 2))
        g.d.line((x, y - 3 - 2 * trunk, x + rand(i, 3) - 0.5, y + 3 + 2 * trunk), fill=1)
        b = ease_out(clamp(p * 2 - 0.6))
        if b > 0:
            ex, ey = x - side * (2 + 11 * b), y - 2 - 2 * b
            mx_, my_ = x - side * (2 + 6 * b), y - 1 - b
            if yang(v):
                g.d.line((x, y - 1, mx_, my_, ex, ey), fill=1)
            else:
                g.d.line((x, y - 1, mx_, my_), fill=1)
                if b > 0.5:
                    q = (b - 0.5) * 2
                    g.d.line((mx_, my_, mx_ - side * 5 * q, my_ - 4 * q), fill=1)
                    g.d.line((mx_, my_, mx_ - side * 5 * q, my_ + 3 * q), fill=1)
            if changing(v) and b > 0.7:  # 碎纹
                q = (b - 0.7) / 0.3
                for k in range(3):
                    a = rand(i * 7 + k, 9) * 2 * math.pi
                    L = 2 + 3 * q * rand(i * 7 + k, 10)
                    sx, sy = lerp(x, ex, 0.4 + 0.3 * k / 2), lerp(y, ey, 0.4 + 0.3 * k / 2)
                    g.d.line((sx, sy, sx + math.cos(a) * L, sy + math.sin(a) * L), fill=1)

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        if t >= R0:
            k = t - R0
            dx = ease_in(span(k, 0, 0.4)) * 80
            if dx < 70:
                self.shell(g, dx)
                for i in range(6):
                    self.pit(g, i, 1, True, dx)
                    self.crack(g, i, 1, dx)
            reveal(g, self.lines, k)
            return
        dx = (1 - ease_out(span(t, 0, 0.55))) * 70
        self.shell(g, dx)
        # 钻凿逐一凿出
        for i in range(6):
            tb = T0 + i * D
            self.pit(g, i, span(t, 0.5 + i * 0.06, 0.62 + i * 0.06), t >= tb + BURN, dx)
            self.crack(g, i, span(t, tb + BURN, tb + D - 0.05))
        if t < 0.9:
            g.vtext(115, 6, "灼龟观兆"[: int(span(t, 0.3, 0.9) * 4 + 0.5)])
        else:
            g.vtext(115, 6, "灼龟观兆")
        # 荆火：移到当前钻处，灼烧
        i = int((t - T0) // D)
        if 0 <= i < 6:
            u = t - T0 - i * D
            x, y = pit_pos(i)
            side = -1 if i % 2 == 0 else 1
            hx, hy = x + side * 4, y
            if u < BURN:
                come = ease_out(clamp(u / 0.12))
                fx, fy = lerp(hx + side * 30, hx, come), lerp(hy + 20, hy + 1, come)
                g.d.line((fx, fy, fx + side * 26, fy + 24), fill=1, width=2)
                flame(g, fx, fy, 4, 7, t, i)
                smoke_wisp(g, fx, fy - 6, 10, t, i, sway=2)
                if u > 0.12:  # 灼热的红晕：钻窝闪亮
                    g.d.ellipse((hx - 2, hy - 2, hx + 2, hy + 2), fill=1 if int(u * 30) % 2 else 0, outline=1)
            elif u < BURN + 0.12:  # 爆裂：一圈白光、火棍抽开
                k = (u - BURN) / 0.12
                for j in range(8):
                    a = j / 8 * 2 * math.pi
                    r = 3 + k * 9
                    g.px(x + math.cos(a) * r, y + math.sin(a) * r)
                fx, fy = hx + side * (6 + k * 20), hy + 4 + k * 10
                g.d.line((fx, fy, fx + side * 26, fy + 24), fill=1, width=2)
            if u > BURN + 0.08:
                v = self.lines[i]
                label(g, 22, 46, YAO_NAME[v], u - BURN - 0.08)
        done = 0.0
        for n in range(6):
            land = T0 + n * D + BURN + 0.2
            if t >= land:
                done = n + clamp((t - land) / 0.25)
        hexa(g, self.lines, done)
        # 点阵：爆裂时显示“卜”形，其余时候显示已成之爻
        if 0 <= i < 6 and BURN <= t - T0 - i * D < BURN + 0.35:
            g.mx[:, 3] = True
            if yang(self.lines[i]):
                g.mx[3, 4:7] = True
            else:
                g.mx[3, 4] = True
                g.mx[2, 5:7] = True
                g.mx[4, 5:7] = True
            g.mx_level = 6 if t - T0 - i * D < BURN + 0.08 else 2
        else:
            mx_hexagram(g, self.lines, int(done))
            if 0 <= i < 6 and t - T0 - i * D < BURN:
                g.mx[7, int(t * 20) % 8] = True
            elif done < 1:
                g.mx[7, 2:6] = True
