"""净心神咒：月下一池水。每念一句《净心神咒》，字写在夜空里、倒映在水中，水波一句比一句平，
念到“魄无丧倾”时水平如镜，咒句与明月的倒影清清楚楚。

依据：《净心神咒》（正一日诵早晚课）：“太上台星，应变无停。驱邪缚魅，保命护身。智慧明净，心神安宁。
三魂永久，魄无丧倾。急急如律令。”取“心如止水”之意。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import cloud, stars
from ..engine.gfx import BAYER, Gfx
from ..engine.scene import Ritual, register
from .r2_common import glyph, glyph_reveal, rays

PHRASES = ["太上台星", "应变无停", "驱邪缚魅", "保命护身", "智慧明净", "心神安宁", "三魂永久", "魄无丧倾"]
LAST = "急急如律令"
SLOT = 52.0
HZ = 32                  # 水平线
MOON = (102, 12)
TXC = 46                 # 咒句中心
RENEW = 3.5


@register
class JingXin(Ritual):
    id = "r2.jingxin"
    name = "净心神咒"
    desc = "月下池水：《净心神咒》一句句写在夜空、倒映水中，水波随诵念渐平，终至水平如镜"
    T = {"enter": 4.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.0}
    CYCLE = SLOT * len(PHRASES) + 34.0   # 450 秒

    def setup(self):
        self.s = self.rng.randrange(1000)
        self.hills = [HZ - 2 - 4 * noise(i * 0.09, self.s) - 2 * noise(i * 0.3, self.s + 1) for i in range(129)]

    # ------------------------------------------------------------ 零件

    def calm(self, u: float) -> float:
        """水波幅度：一遍开头 3.5，念完 0.2"""
        p = clamp(u / (SLOT * len(PHRASES)))
        return lerp(3.5, 0.15, ease_out(p))

    def sky(self, g: Gfx, t: float, moon_y: float = MOON[1], moon_a: float = 1.0):
        stars(g, t, self.s, n=14, box=(0, 0, 128, HZ - 6), twinkle=0.3)
        mx, my = MOON
        if moon_a > 0:
            g.d.ellipse((mx - 7, moon_y - 7, mx + 7, moon_y + 7), fill=1)
            for dx, dy, r in ((-2, -2, 1.6), (3, 1, 1.2), (-1, 3, 1.0)):  # 月面暗斑
                g.d.ellipse((mx + dx - r, moon_y + dy - r, mx + dx + r, moon_y + dy + r), fill=0)
        # 远山剪影
        g.d.polygon([(0, HZ)] + [(i, self.hills[i]) for i in range(0, 129, 4)] + [(128, HZ)], fill=0)
        g.d.line([(i, self.hills[i]) for i in range(0, 129, 4)], fill=1)

    def phrase(self, g: Gfx, s: str, k: float):
        """写一句：每字 0.6 秒自上而下写出（k = 本句经过秒数）"""
        w = len(s) * 13 - 1
        x0 = TXC - w / 2
        for i, ch in enumerate(s):
            p = (k - i * 0.6) / 0.6
            if p <= 0:
                break
            glyph_reveal(g, x0 + i * 13, 8, ch, p)

    def reflect(self, g: Gfx, amp: float, t: float, dim: float = 0.5):
        """把水平线以上的画面倒映到水里：逐行按波纹错位，用抖动变暗"""
        a = g.array()
        n = 64 - HZ - 1
        src = a[HZ - 1:HZ - 1 - n:-1]   # 第 HZ-1 行起往上
        out = np.zeros_like(src)
        for i in range(n):
            k = i / n
            dx = int(round(amp * (0.4 + k) * math.sin(i * 0.9 + t * 2.6 + noise(t * 0.7 + i * 0.2, self.s) * 3)))
            out[i] = np.roll(src[i], dx)
        keep = BAYER[HZ + 1:64] < int(round(dim * 16))
        if amp > 0.6:  # 波大时，隔几行断开（水波的暗纹）
            ph = int(t * 6)
            gap = np.array([((i + ph) % 4 == 0) for i in range(n)])[:, None]
            keep &= ~gap
        a[HZ + 1:64] = out & keep
        g.put(a)
        # 水平线：断续的亮点
        for x in range(0, 128, 3):
            if noise(x * 0.2 + t, self.s) > 0.3:
                g.px(x, HZ)

    def ripple(self, g: Gfx, x: float, age: float):
        if 0 <= age < 3:
            r = age * 14
            n = 40
            for i in range(0, n, 2 if age < 1 else 3):
                a = i / n * 2 * math.pi
                g.px(x + math.cos(a) * r, HZ + 6 + math.sin(a) * r * 0.18)

    def mx(self, g: Gfx, amp: float, t: float, moon: bool = True):
        if moon:
            g.mx_rows([0b00011000, 0b00111100, 0b00111100, 0b00011000, 0, 0, 0, 0])
        g.mx[4, :] = True
        for row, w in ((5, 2), (6, 3), (7, 1)):
            sh = int(round(amp * 0.6 * math.sin(t * 2.6 + row)))
            for x in range(4 - w // 2 - 1, 4 + w // 2 + 1):
                if moon:
                    g.mx_set(x + sh, row)

    def scene(self, g: Gfx, t: float, u: float, amp: float | None = None, text: bool = True, moon_y=None):
        amp = self.calm(u) if amp is None else amp
        self.sky(g, t, MOON[1] if moon_y is None else moon_y)
        idx = int(u // SLOT)
        if text:
            if idx < len(PHRASES):
                self.phrase(g, PHRASES[idx], u - idx * SLOT)
            else:
                self.phrase(g, LAST, (u - idx * SLOT) * 0.5)
        self.reflect(g, amp, t)
        # 每句开头一圈涟漪（一念落下）
        k = u - idx * SLOT
        self.ripple(g, TXC, k)
        return amp

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        my = lerp(HZ + 9, MOON[1], ease_out(span(t, 0, 2.2)))
        self.sky(g, t, my)
        if t > 2.2:
            self.phrase(g, PHRASES[0], (t - 2.2) * 1.3)
        self.reflect(g, lerp(1.5, 3.5, span(t, 0, 3)), t)
        self.mx(g, 3.5, t, moon=t > 0.8)
        g.mx[4, :] = True

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, e)
            return
        amp = self.scene(g, t, u)
        self.mx(g, amp, t)
        idx = int(u // SLOT)
        if idx >= len(PHRASES):  # 念完最后一句：月光一闪一闪
            k = u - idx * SLOT
            if (k % 6) < 1.2:
                rays(g, MOON[0], MOON[1], 10, 13 + (k % 6) * 2, 10, phase=0.3)

    def _renew(self, g: Gfx, t: float, u: float, e: float):
        """又起一阵风：水面重新起波，再从头念"""
        gust = math.sin(span(u, 0, RENEW) * math.pi)
        amp = lerp(0.2, 3.5, ease_out(span(u, 0, 1.5)))
        self.sky(g, t)
        if u < 1.6:
            g.text(TXC, 8, LAST, align="center")
            g.fade(1 - span(u, 0.2, 1.6), (0, 0, 128, HZ))
        else:
            self.phrase(g, PHRASES[0], (u - 1.6) * 2)
        self.reflect(g, amp + gust * 2, t)
        for j in range(4):  # 风线
            y = 6 + j * 7
            x0 = -30 + span(u, 0, 2.2) * 190 - j * 14
            g.d.line((x0, y, x0 + 16, y), fill=1)
        self.mx(g, amp, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        """浮云遮月，咒句隐去"""
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        f = ease_in_out(span(t, 0, 1.3))
        amp = self.calm(u)
        self.sky(g, t)
        idx = int(u // SLOT)
        s = PHRASES[idx] if idx < len(PHRASES) else LAST
        g.text(TXC, 8, s, align="center")
        g.fade(1 - f, (0, 0, 100, HZ - 6))
        cx = lerp(150, MOON[0], f)
        cloud(g, cx, MOON[1] + 1, 34, 14, seed=self.s, fill=1)
        cloud(g, cx, MOON[1] + 1, 32, 12, seed=self.s, fill=0, outline=1)
        if t > 1.1:
            g.text(TXC, 10, "暂歇"[:int(clamp((t - 1.1) * 6, 0, 2))], align="center")
        self.reflect(g, amp, t, dim=0.5 - 0.25 * f)
        self.mx(g, amp, t, moon=t < 1.0)
        g.mx[4, :] = True

    def resume(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        f = ease_in_out(span(t, 0, 1.4))
        amp = self.calm(u)
        self.sky(g, t)
        idx = int(u // SLOT)
        s = PHRASES[idx] if idx < len(PHRASES) else LAST
        if t > 0.8:
            if idx < len(PHRASES):
                self.phrase(g, s, (t - 0.8) * 4)
            else:
                g.text(TXC, 8, s, align="center")
        cx = lerp(MOON[0], -30, f)
        cloud(g, cx, MOON[1] + 1, 34, 14, seed=self.s, fill=1)
        cloud(g, cx, MOON[1] + 1, 32, 12, seed=self.s, fill=0, outline=1)
        self.reflect(g, amp, t, dim=0.25 + 0.25 * f)
        self.mx(g, amp, t, moon=t > 0.7)
        g.mx[4, :] = True

    def complete(self, g: Gfx, t: float, e: float):
        """水平如镜：月与咒句的倒影一丝不乱，月华大放"""
        u = e % self.CYCLE
        amp = lerp(self.calm(u), 0.0, ease_out(span(t, 0, 1.5)))
        self.sky(g, t)
        if t < 1.5:
            idx = int(u // SLOT)
            s = PHRASES[idx] if idx < len(PHRASES) else LAST
            g.text(TXC, 8, s, align="center")
            g.fade(1 - span(t, 0.6, 1.5), (0, 0, 100, HZ - 6))
        else:
            self.phrase(g, "心神安宁", (t - 1.5) * 1.6)
        if t > 2.6:
            k = t - 2.6
            for j in range(2):
                r = ((k * 10 + j * 8) % 16) + 9
                rays(g, MOON[0], MOON[1], r, r + 3, 12, phase=j * 0.26)
        self.reflect(g, amp, t, dim=lerp(0.5, 0.75, span(t, 1.5, 3.0)))
        self.mx(g, amp, t)
        if t > 2.6:
            g.mx_level = 1 + int(4 * (1 - span(t, 2.6, 4.5)))
            if blink(t, 0.5):
                g.mx[0, 1] = g.mx[0, 6] = g.mx[3, 1] = g.mx[3, 6] = True
