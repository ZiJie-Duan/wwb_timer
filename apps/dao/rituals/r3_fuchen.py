"""挥拂尘：右手执拂尘，一拂一扫，蒙在太极上的尘埃一点点被拂去，太极渐明。

拂尘（麈尾、云帚）是道士随身的法器，取“拂去尘埃、清净自守”之意。
文字取《太上老君说常清静经》：“人能常清静，天地悉皆归。”
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
import numpy as np

from ..engine.gfx import BAYER, Gfx, Sprite
from ..engine.symbols import mx_taiji, taiji
from ..engine.scene import Ritual, register
from .r3_kit import capsule, round_of, side_text, sleeve, sparkle

HX, HY = 103, 50         # 握柄的手
TJ = (50, 31, 16)        # 太极
SW = 6.0                 # 一拂的周期（秒）
REST, UP, LEFT = -2.05, -1.55, -3.05
DOWN = -3 * math.pi / 2  # 毛垂向左下
N_DUST = 46
RENEW = 3.5


def phi_at(u: float) -> float:
    """一拂之内（u = 周期内秒数）拂尘柄的指向"""
    if u < 0.5:
        return lerp(REST, UP, ease_in_out(u / 0.5))
    if u < 1.3:
        return lerp(UP, LEFT, ease_in_out((u - 0.5) / 0.8))
    if u < 3.0:
        return lerp(LEFT, REST, ease_in_out((u - 1.3) / 1.7))
    return REST + math.sin((u - 3.0) * 2.1) * 0.04


def whisk(g: Gfx, hx: float, hy: float, phi_fn, s: float, seed: int, droop_k: float = 1.0):
    """拂尘：phi_fn(s) 给出柄的指向；毛有滞后、会下垂"""
    phi = phi_fn(s)
    tx, ty = hx + math.cos(phi) * 21, hy + math.sin(phi) * 21
    # 毛：每一节的滞后角与下垂程度对所有毛相同，先算好
    segs = []
    for j in range(8):
        sj = s - 0.045 * (j + 1)
        pj = phi_fn(sj)
        speed = abs(phi_fn(sj + 0.04) - phi_fn(sj - 0.04)) / 0.08
        droop = clamp(0.88 - speed * 0.22) * droop_k
        segs.append(lerp(pj, DOWN, clamp(droop * (j + 1) / 3.5)))
    for i in range(9):
        off = (i - 4) * 0.06
        x, y = tx + math.cos(phi + math.pi / 2) * (i - 4) * 0.4, ty + math.sin(phi + math.pi / 2) * (i - 4) * 0.4
        pts = [(x, y)]
        wob = (noise(s * 1.5 + i * 3, seed) - 0.5) * 0.15
        for j in range(8):
            a = segs[j] + off * (1 + j * 0.2) + wob * (1 + j * 0.15)
            x += math.cos(a) * 4.6
            y += math.sin(a) * 4.6
            pts.append((x, y))
        g.d.line(pts, fill=1)
    # 柄
    g.d.line((hx, hy, tx, ty), fill=1, width=3)
    g.d.line((hx + math.cos(phi) * 2, hy + math.sin(phi) * 2, tx, ty), fill=0, width=1)
    g.d.ellipse((tx - 2, ty - 2, tx + 2, ty + 2), fill=1)
    bx, by = hx - math.cos(phi) * 3, hy - math.sin(phi) * 3
    g.d.ellipse((bx - 1.5, by - 1.5, bx + 1.5, by + 1.5), fill=1)
    # 手
    sleeve(g, hx + 5, hy + 3, 0.55, length=50, w0=12, w1=30, shade=0.25)
    g.d.rounded_rectangle((hx - 4, hy - 4, hx + 5, hy + 5), radius=3, fill=0, outline=1)
    g.d.line((hx - 3, hy - 1, hx + 1, hy - 1), fill=1)
    g.d.line((hx - 3, hy + 2, hx + 1, hy + 2), fill=1)


TJ_STEPS = 128
TJ_HALF = TJ[2] + 2
_tj_cache: dict = {}


def tj_sprite(aq: int, lq: int) -> Sprite:
    """太极（按转角、亮度量化后缓存成像素画，免得每帧整屏 numpy）"""
    key = (aq, lq)
    if key not in _tj_cache:
        n = TJ_HALF * 2 + 1
        g2 = Gfx()
        taiji(g2, TJ_HALF, TJ_HALF, TJ[2], angle=aq / TJ_STEPS * 2 * math.pi)
        a = g2.array()[:n, :n]
        a &= BAYER[:n, :n] < lq
        ys, xs = np.mgrid[0:n, 0:n]
        inside = (xs - TJ_HALF) ** 2 + (ys - TJ_HALF) ** 2 <= (TJ[2] + 1.5) ** 2
        _tj_cache[key] = Sprite(on=a, mask=inside | a)
    return _tj_cache[key]


@register
class Whisk(Ritual):
    id = "r3.fuchen"
    name = "挥拂尘"
    desc = "执拂尘一拂一扫，蒙在太极上的尘埃逐渐拂净，太极由暗转明；一轮扫净后尘又起"
    T = {"enter": 3.0, "interrupt": 1.5, "resume": 1.6, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.dust = []
        sweeps = int(self.CYCLE / SW)
        for i in range(N_DUST):
            a = rand(i, self.seed) * 2 * math.pi
            r = math.sqrt(rand(i + 50, self.seed)) * 26
            x = TJ[0] + math.cos(a) * r * 1.35
            y = TJ[1] + math.sin(a) * r * 0.95
            k = 1 + int(rand(i + 100, self.seed) * (sweeps - 2))
            self.dust.append((x, y, k, rand(i + 200, self.seed) < 0.3))

    # ------------------------------------------------------------ 零件

    def cleared(self, e: float) -> float:
        _, k, _ = round_of(e, self.CYCLE)
        sw = k / SW
        return sum(1 for d in self.dust if d[2] < sw) / N_DUST

    def draw_dust(self, g: Gfx, t: float, e: float, fly_in: float = 1.0, all_gone_after: float | None = None):
        _, k, _ = round_of(e, self.CYCLE)
        cur = int(k // SW)
        u = k - cur * SW
        for i, (x, y, kk, big) in enumerate(self.dust):
            if all_gone_after is not None:
                f = clamp((all_gone_after - rand(i + 300, self.seed) * 0.4) / 1.0)
            elif kk < cur:
                continue
            elif kk == cur:
                f = span(u, 0.55 + (x - 20) / 200, 1.6)
            else:
                f = 0.0
            if f >= 1:
                continue
            dx = (noise(t * 0.4 + i, self.seed) - 0.5) * 3
            dy = (noise(t * 0.3 + i * 2, self.seed + 1) - 0.5) * 2
            xx = x + dx - ease_in(f) * 110
            yy = y + dy - math.sin(f * math.pi) * 8
            if fly_in < 1:
                q = clamp(fly_in * 1.4 - rand(i + 400, self.seed) * 0.4)
                xx = lerp(-10 - rand(i, 7) * 30, xx, ease_out(q))
                if q <= 0:
                    continue
            g.px(xx, yy)
            if big:
                g.px(xx + 1, yy)
                g.px(xx, yy + 1)

    def draw_taiji(self, g: Gfx, t: float, bright: float):
        x, y, r = TJ
        aq = int(t * 0.15 / (2 * math.pi) * TJ_STEPS) % TJ_STEPS
        lq = int(round((0.3 + 0.7 * clamp(bright)) * 16))
        g.blit(tj_sprite(aq, lq), x - TJ_HALF, y - TJ_HALF)

    def texts(self, g: Gfx, e: float, a: float = 1.0, right: str | None = None):
        side_text(g, 3, 3, "常清静", a)
        n = int(e // self.CYCLE) + 1
        s = right if right is not None else f"{cn_num(n)}拂"
        if a >= 1:
            g.text(3, 51, s)

    def mx(self, g: Gfx, e: float, t: float, sweeping: float = -1):
        _, k, _ = round_of(e, self.CYCLE)
        sw = k / SW
        for i, (x, y, kk, big) in enumerate(self.dust):
            if kk >= sw:
                g.mx_set(int(rand(i, 11) * 6), int(rand(i, 12) * 8))
        # 拂尘小图标（右下）
        for x, y in ((7, 7), (6, 6), (5, 5)):
            g.mx_set(x, y)
        for x, y in ((4, 4), (4, 5), (3, 5), (4, 6), (3, 6)):
            g.mx_set(x, y)
        if sweeping >= 0:
            col = 7 - int(sweeping * 9)
            for r in range(8):
                g.mx_set(col, r)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.draw_taiji(g, t, span(t, 0, 0.8) * 0.0)
        self.draw_dust(g, t, 0, fly_in=span(t, 0.0, 1.6))
        p = ease_out(span(t, 0.6, 2.0))
        hx, hy = lerp(150, HX, p), lerp(70, HY, p)
        whisk(g, hx, hy, lambda s: REST + (1 - p) * 0.8 + math.sin(s * 3) * 0.1 * (1 - p), t, self.seed)
        self.texts(g, 0, span(t, 2.0, 2.8))
        self.mx(g, 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        n, k, _ = round_of(e, self.CYCLE)
        if n > 1 and k < RENEW:
            # 续：一阵风又把尘吹来，太极重新蒙尘
            self.draw_taiji(g, t, 1 - span(k, 0.5, 2.8))
            self.draw_dust(g, t, e, fly_in=span(k, 0.3, 3.0))
            for j in range(4):
                y = 10 + j * 13
                x0 = -30 + k / RENEW * 190 - j * 14
                g.d.line((x0, y, x0 + 16, y), fill=1)
            whisk(g, HX, HY, lambda s: REST + math.sin(s * 4) * 0.12, e, self.seed)
            self.texts(g, e)
            self.mx(g, e, t)
            return
        u = (e % self.CYCLE) % SW
        self.draw_taiji(g, t, self.cleared(e))
        self.draw_dust(g, t, e)
        whisk(g, HX, HY, lambda s: phi_at(s % SW), u, self.seed)
        self.texts(g, e)
        self.mx(g, e, t, span(u, 0.5, 1.3) if 0.5 < u < 1.3 else -1)
        g.mx_level = 2 if 0.6 < u < 1.0 else 1

    def interrupt(self, g: Gfx, t: float, e: float):
        u = (e % self.CYCLE) % SW
        p = ease_in_out(span(t, 0, 1.2))
        self.draw_taiji(g, t, self.cleared(e))
        self.draw_dust(g, t, e)
        start = phi_at(u)
        whisk(g, HX, HY + 6 * p, lambda s: lerp(start, -1.75, p), t, self.seed)
        self.texts(g, e, right="暂歇")
        self.mx(g, e, t)

    def resume(self, g: Gfx, t: float, e: float):
        u = (e % self.CYCLE) % SW
        p = ease_in_out(span(t, 0.2, 1.4))
        self.draw_taiji(g, t, self.cleared(e))
        self.draw_dust(g, t, e)
        end = phi_at(u)
        whisk(g, HX, HY + 6 * (1 - p), lambda s: lerp(-1.75, end, p), t, self.seed)
        self.texts(g, e)
        self.mx(g, e, t)

    def complete(self, g: Gfx, t: float, e: float):
        # 两大拂：0–1.6 第一拂，1.6–3.0 第二拂扫净；然后太极放光
        c = self.cleared(e)
        bright = lerp(c, 1, span(t, 0.6, 2.8))
        self.draw_taiji(g, t * 3 if t > 3 else t, bright)
        if t < 2.8:
            self.draw_dust(g, t, e, all_gone_after=(t - 0.5) * 0.9)
        if t < 3.0:
            u = t % 1.5
            whisk(g, HX, HY, lambda s: phi_at(0.3 + (s % 1.5) * 0.9), u, self.seed)
            self.texts(g, e)
            self.mx(g, e, t, span(u, 0.25, 1.1))
            return
        whisk(g, HX, HY, lambda s: REST + 0.4 * ease_out(span(t, 3.0, 3.6)), t, self.seed)
        r = ease_out(span(t, 3.0, 4.0))
        x, y, rr = TJ
        for i in range(12):
            a = i / 12 * 2 * math.pi + t * 0.4
            g.d.line((x + math.cos(a) * (rr + 4), y + math.sin(a) * (rr + 4),
                      x + math.cos(a) * (rr + 4 + 8 * r), y + math.sin(a) * (rr + 4 + 8 * r)), fill=1)
        side_text(g, 3, 3, "常清静")
        g.d.rectangle((64, 2, 126, 14), fill=0)
        typewriter(g, 95, 3, "天地悉皆归", t - 3.3, cps=5, align="center")
        g.mx[:] = False
        rr = (t - 3.0) * 3.5
        if rr > 4.5:
            mx_taiji(g, t * 0.6)
        for yy in range(8):
            for xx in range(8):
                if abs(math.hypot(xx - 3.5, yy - 3.5) - rr) < 0.7:
                    g.mx[yy, xx] = True
        g.mx_level = 1 + int(5 * (1 - span(t, 3.0, 4.5)))
