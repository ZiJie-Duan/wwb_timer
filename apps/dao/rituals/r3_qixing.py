"""七星剑：右手持七星剑，剑身七星随计时逐一点亮，与天上北斗一一相应；时而挽一个剑花。

七星剑是道教法剑，剑身嵌北斗七星，用以召将、斩邪。北斗七星：天枢、天璇、天玑、天权、玉衡、开阳、摇光，
道经称其星君为贪狼、巨门、禄存、文曲、廉贞、武曲、破军（《北斗七星延命经》）。
圆满句“气冲斗牛”化用《晋书·张华传》：斗牛之间常有紫气，乃宝剑之精上彻于天。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r3_kit import rot, round_of, side_text, sleeve, sparkle

GX, GY = 24, 50                  # 握剑处
BASE = -0.43                     # 剑的指向（弧度）
STAR_NAMES = ["贪狼", "巨门", "禄存", "文曲", "廉贞", "武曲", "破军"]
SKY = [(10, 5), (7, 16), (19, 19), (22, 9), (32, 7), (41, 9), (50, 16)]   # 天上北斗（天枢→摇光）
BLADE_STARS = [(14, -1), (22, 1), (30, 1), (37, -1), (47, 0), (57, -1), (67, 1)]  # 剑身七星（沿剑, 横向）
MXS = [(1, 0), (0, 3), (2, 4), (3, 1), (5, 1), (6, 2), (7, 5)]
SWIRL = 24.0                     # 每隔多少秒挽一个剑花
RENEW = 4.0

BLADE = [(8, -3), (74, -3), (82, 0), (74, 3), (8, 3)]
GUARD = [(5, -8), (8, -8), (8, 8), (5, 8)]
GRIP = [(-8, -2), (5, -2), (5, 2), (-8, 2)]


def sword(g: Gfx, ang: float, lit: int, t: float, x: float = GX, y: float = GY, glint: float = -1.0,
          flare: float = 0.0):
    """七星剑：(x, y) 为握处，ang 剑尖方向；lit = 已亮的星数"""
    g.d.polygon(rot(BLADE, x, y, ang), fill=0, outline=1)
    g.d.line(rot([(10, 0), (75, 0)], x, y, ang), fill=1)              # 剑脊
    for i in range(len(BLADE_STARS) - 1):                               # 星间连线（淡）
        if i + 1 < lit:
            a, b = rot([BLADE_STARS[i], BLADE_STARS[i + 1]], x, y, ang)
            g.d.line((a, b), fill=1)
    for i, (u, v) in enumerate(BLADE_STARS):
        (sx, sy), = rot([(u, v)], x, y, ang)
        if i < lit:
            g.d.polygon([(sx, sy - 3), (sx + 3, sy), (sx, sy + 3), (sx - 3, sy)], fill=0)
            g.d.polygon([(sx, sy - 2), (sx + 2, sy), (sx, sy + 2), (sx - 2, sy)], fill=1)
            if flare > 0 or noise(t * 2 + i * 1.7, i) > 0.82:
                sparkle(g, sx, sy, 3 + int(flare * 2))
        else:
            g.d.rectangle((sx - 1, sy - 1, sx + 1, sy + 1), fill=0, outline=1)
    if 0 <= glint <= 1:  # 一道流光沿剑身划过
        (sx, sy), = rot([(lerp(10, 80, glint), 0)], x, y, ang)
        sparkle(g, sx, sy, 3)
    g.d.polygon(rot(GUARD, x, y, ang), fill=1)
    g.d.polygon(rot(GRIP, x, y, ang), fill=0, outline=1)
    (px, py), = rot([(-10, 0)], x, y, ang)
    g.d.ellipse((px - 2, py - 2, px + 2, py + 2), fill=0, outline=1)    # 剑首
    # 握剑的拳 + 袖
    sleeve(g, x - 3, y + 4, 2.45, length=40, w0=11, w1=28, shade=0.25)
    hx, hy = x, y
    g.d.rounded_rectangle((hx - 4, hy - 4, hx + 4, hy + 5), radius=3, fill=0, outline=1)
    g.d.line((hx - 3, hy, hx + 3, hy - 1), fill=1)
    g.d.line((hx - 3, hy + 3, hx + 3, hy + 2), fill=1)


@register
class SevenStarSword(Ritual):
    id = "r3.qixing"
    name = "七星剑"
    desc = "持七星剑，剑身七星随时间逐一点亮，天上北斗一一相应，时而挽剑花；七星齐明则剑指北斗"
    T = {"enter": 3.2, "interrupt": 1.4, "resume": 1.6, "complete": 5.5}
    CYCLE = 630.0

    # ------------------------------------------------------------ 零件

    def lit_at(self, e: float) -> tuple[int, float]:
        """→ (已亮几星, 最近一颗亮起后的秒数)"""
        _, k, _ = round_of(e, self.CYCLE)
        step = self.CYCLE / 7.4
        n = min(7, int((k - step * 0.3) // step) + 1) if k >= step * 0.3 else 0
        since = k - (step * 0.3 + (n - 1) * step) if n else 99.0
        return n, since

    def swirl(self, e: float) -> tuple[float, float]:
        """剑花：→ (角度偏移, 剑花进度 -1 = 不在挽)"""
        u = (e + 12.0) % SWIRL
        if u < 1.4:
            f = u / 1.4
            return -2 * math.pi * ease_in_out(f), f
        return 0.0, -1

    def sky(self, g: Gfx, lit: int, t: float, show: float = 1.0, lines: bool = True):
        for i, (x, y) in enumerate(SKY):
            if i >= show * 7 + 0.01:
                break
            if i < lit:
                g.d.rectangle((x, y, x + 1, y + 1), fill=1)
                if noise(t * 1.5 + i * 2.3, 5) > 0.8:
                    sparkle(g, x, y, 2)
                if lines and i > 0:
                    a, b = SKY[i - 1], SKY[i]
                    g.d.line((a[0] + 1, a[1] + 1, b[0], b[1]), fill=1)
            elif noise(t * 2 + i, 9) > 0.3:
                g.px(x, y)
        if lit >= 4 and lines:  # 斗魁闭合（天权→天枢）
            g.d.line((SKY[3][0], SKY[3][1], SKY[0][0] + 1, SKY[0][1] + 1), fill=1)

    def beam(self, g: Gfx, i: int, since: float, ang: float):
        """新亮的星：天上那颗星落一道光到剑上"""
        if since > 1.2 or i < 0:
            return
        f = ease_in(clamp(since / 0.6))
        x0, y0 = SKY[i]
        (x1, y1), = rot([BLADE_STARS[i]], GX, GY, ang)
        xx, yy = lerp(x0, x1, f), lerp(y0, y1, f)
        g.d.line((x0, y0, xx, yy), fill=1)
        if since > 0.6:
            r = (since - 0.6) * 14
            from ..engine.fx import ring
            ring(g, x1, y1, r, 2)

    def label(self, g: Gfx, lit: int, a: float = 1.0, right: str | None = None, e: float = 0.0):
        name = right if right is not None else (STAR_NAMES[lit - 1] if lit else "七星")
        side_text(g, 114, 3, name, a)

    def mx(self, g: Gfx, lit: int, t: float):
        for i, (x, y) in enumerate(MXS):
            if i < lit:
                g.mx_set(x, y)
            elif i == lit:
                g.mx_set(x, y, blink(t, 1.0, 0.25))
        # 剑
        for k in range(5):
            g.mx_set(2 + k, 7 - int(k * 0.6))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        p = ease_out_back(span(t, 0, 1.3))
        ang = lerp(BASE + 1.6, BASE, p)
        x, y = lerp(-10, GX, ease_out(span(t, 0, 1.0))), lerp(80, GY, ease_out(span(t, 0, 1.0)))
        self.sky(g, 0, t, show=span(t, 1.2, 2.4))
        sword(g, ang, 0, t, x, y, glint=span(t, 1.5, 2.3) if 1.5 < t < 2.3 else -1)
        self.label(g, 0, span(t, 2.4, 3.0))
        self.mx(g, 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        n, k, _ = round_of(e, self.CYCLE)
        if n > 1 and k < RENEW:
            self._renew(g, k, e, t)
            return
        lit, since = self.lit_at(e)
        off, sw = self.swirl(e)
        ang = BASE + off
        if sw >= 0:  # 剑花残影：剑尖划过的弧
            for j in range(16):
                q = sw - j * 0.025
                if q < 0:
                    break
                a = BASE - 2 * math.pi * ease_in_out(q)
                tx, ty = GX + math.cos(a) * 80, GY + math.sin(a) * 80
                tx2, ty2 = GX + math.cos(a) * 60, GY + math.sin(a) * 60
                if j % 2 == 0:
                    g.d.line((tx2, ty2, tx, ty), fill=1)
        self.sky(g, lit, t)
        self.beam(g, lit - 1, since, ang)
        glint = ((e % 7.0) / 1.2) if (e % 7.0) < 1.2 and sw < 0 else -1
        sword(g, ang, lit, t, glint=glint)
        self.label(g, lit, e=e)
        self.mx(g, lit, t)
        g.mx_level = 4 if since < 0.5 else 1

    def _renew(self, g: Gfx, k: float, e: float, t: float):
        """七星齐明：剑指北斗，七颗星飞上天融入北斗，剑身星暗，再从头"""
        up = ease_in_out(span(k, 0, 0.8)) * (1 - ease_in_out(span(k, 2.8, 3.8)))
        ang = lerp(BASE, -1.25, up)
        fly = span(k, 0.8, 2.2)
        self.sky(g, 7 if k < 2.8 else 0, t)
        if 0.8 < k < 2.2:
            for i, (u, v) in enumerate(BLADE_STARS):
                (x0, y0), = rot([(u, v)], GX, GY, ang)
                x1, y1 = SKY[i]
                q = ease_in(clamp(fly * 1.3 - i * 0.04))
                g.d.rectangle((lerp(x0, x1, q) - 1, lerp(y0, y1, q) - 1, lerp(x0, x1, q) + 1, lerp(y0, y1, q) + 1),
                              fill=1)
        if 2.2 < k < 2.8:
            for x, y in SKY:
                sparkle(g, x, y, 3)
        sword(g, ang, 7 if k < 0.8 else 0, t)
        self.label(g, 7 if k < 2.8 else 0, e=e)
        self.mx(g, 7 if k < 2.8 else 0, t)
        g.mx_level = 5 if 2.2 < k < 2.6 else 1

    def interrupt(self, g: Gfx, t: float, e: float):
        lit, _ = self.lit_at(e)
        p = ease_in_out(span(t, 0, 1.1))
        ang = lerp(BASE, -0.02, p)
        self.sky(g, lit, t, lines=t < 0.6)
        sword(g, ang, lit, t, y=GY + 2 * p)
        g.fade(1 - 0.5 * span(t, 0.4, 1.2), (0, 0, 60, 26))
        self.label(g, lit, right="按剑" if t > 0.5 else None, e=e)
        self.mx(g, lit, t)

    def resume(self, g: Gfx, t: float, e: float):
        lit, _ = self.lit_at(e)
        p = ease_out_back(span(t, 0.1, 1.2))
        ang = lerp(-0.02, BASE, p)
        self.sky(g, lit, t, lines=t > 1.0)
        sword(g, ang, lit, t, y=GY + 2 * (1 - p), glint=span(t, 1.0, 1.6) if t > 1.0 else -1)
        if t < 0.8:
            g.fade(0.5 + 0.5 * span(t, 0, 0.8), (0, 0, 60, 26))
        self.label(g, lit, e=e)
        self.mx(g, lit, t)

    def complete(self, g: Gfx, t: float, e: float):
        lit, _ = self.lit_at(e)
        # 0–1.5：余星依次补亮；1.6–2.6：七道星光从剑上直射北斗；之后北斗大放光明
        n = max(lit, min(7, lit + int(span(t, 0, 1.5) * (8 - lit))))
        up = ease_out_back(span(t, 1.3, 1.9))
        ang = lerp(BASE, BASE - 0.25, up)
        self.sky(g, n, t)
        if t > 1.6:
            f = ease_in(span(t, 1.6, 2.3))
            for i, (u, v) in enumerate(BLADE_STARS):
                (x0, y0), = rot([(u, v)], GX, GY, ang)
                x1, y1 = SKY[i]
                if t < 3.2 or blink(t + i * 0.1, 0.3, 0.6):
                    g.d.line((x0, y0, lerp(x0, x1, f), lerp(y0, y1, f)), fill=1)
            if t > 2.3:
                r = ease_out(span(t, 2.3, 3.2))
                for x, y in SKY:
                    sparkle(g, x, y, 1 + int(3 * r))
        sword(g, ang, n, t, flare=span(t, 1.6, 2.2) if t > 1.6 else 0)
        if t > 2.6:
            g.d.rectangle((74, 44, 127, 58), fill=0)
            typewriter(g, 100, 46, "气冲斗牛", t - 2.7, cps=5, align="center")
        else:
            self.label(g, n, e=e)
        self.mx(g, n, t)
        if t > 2.3:
            g.mx[:] = False
            for mx_, my_ in MXS:
                g.mx_set(mx_, my_)
            if blink(t, 0.3):
                for k in range(5):
                    g.mx_set(2 + k, 7 - int(k * 0.6))
            g.mx_level = 1 + int(6 * (1 - span(t, 2.3, 4.0)))
