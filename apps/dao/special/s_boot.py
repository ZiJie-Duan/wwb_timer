"""开坛：程序启动（控制器接管）时播放。

无极一点 → 化为一圈 → 太极旋生（“无极而太极”）→ 八卦自外飞入成盘、外圈二十四点 →
金光一闪，坛成；八卦盘移到左边慢转，右边写出 dao timer、境界与道行。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx, text_width
from ..engine.scene import Special, register
from ..engine.symbols import XIANTIAN, bagua_ring, mx_taiji, taiji

R_TAI = 12
R_GUA = 16


@register
class Boot(Special):
    id = "s.boot"
    name = "开坛"
    desc = "无极一点化圈，太极旋生，八卦飞入成盘，金光一闪；盘移左侧，右书 dao timer、境界、道行"
    T = {"play": 3.6}

    def disc(self, g: Gfx, cx: float, cy: float, t: float):
        spin = ease_out(span(t, 0.35, 1.6)) * 4 * math.pi + t * 0.6
        rt = R_TAI * ease_out_back(span(t, 0.35, 1.0))
        if rt > 1.5:
            taiji(g, cx, cy, rt, spin)
        # 八卦自外飞入（逆着旋转方向落位）
        rot = -t * 0.25
        for i in range(8):
            p = ease_out(span(t, 0.75 + i * 0.07, 1.25 + i * 0.07))
            if p <= 0:
                continue
            r = lerp(60, R_GUA, p)
            a = rot + (1 - p) * 1.2
            bagua_ring(g, cx, cy, r, a, XIANTIAN, w=8, step=2.6, show=lambda k, i=i: k == i)
        # 外圈：点环（二十四点）+ 实线圈
        o = ease_out(span(t, 1.3, 1.8))
        if o > 0:
            rr = R_GUA + 9 + (1 - o) * 10
            for j in range(24):
                a = j / 24 * 2 * math.pi - rot * 2
                g.px(cx + math.cos(a) * rr, cy + math.sin(a) * rr)
            if o > 0.6:
                g.d.ellipse((cx - rr - 3, cy - rr - 3, cx + rr + 3, cy + rr + 3), outline=1)

    def play(self, g: Gfx, t: float):
        slide = ease_in_out(span(t, 2.0, 2.6))
        cx, cy = lerp(64, 31, slide), 32
        # 无极：一点 → 一圈
        if t < 0.55:
            p = span(t, 0, 0.55)
            if p < 0.4:
                s = 1 + int(p * 6) % 2
                g.d.rectangle((cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), fill=1)
            else:
                r = ease_out((p - 0.4) / 0.6) * (R_TAI + 1)
                g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
        self.disc(g, cx, cy, t)
        # 金光一闪
        f = span(t, 1.75, 2.15)
        if 0 < f < 1:
            for j in range(16):
                a = j / 16 * 2 * math.pi
                r0, r1 = 28 + f * 6, 28 + f * 6 + 10 * (1 - f)
                g.d.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * r1,
                          cy + math.sin(a) * r1), fill=1)
            ring(g, cx, cy, 30 + f * 40, density=2)
        # 右边题字
        if t > 2.3:
            x = 66
            typewriter(g, x, 4, "dao timer", t - 2.3, cps=24)
            w = text_width("dao timer")
            p = ease_out(span(t, 2.55, 2.9))
            g.d.line((x, 18, x + (w + 4) * p, 18), fill=1)
            if t > 2.75:
                typewriter(g, x, 24, f"境界 {self.ctx.realm()}", t - 2.75, cps=16)
            if t > 3.0:
                typewriter(g, x, 40, f"道行 {self.ctx.completed}", t - 3.0, cps=16)
            if t > 3.15:  # 落款一枚朱印“道”
                q = ease_out_back(span(t, 3.15, 3.4))
                s = 6 * q
                g.d.rectangle((119 - s, 55 - s, 119 + s, 55 + s), fill=1)
                if q > 0.9:
                    g.text(119, 52, "道", size=8, fill=0, align="center")
        # 点阵：一点 → 太极旋转；闪光时最亮
        if t < 0.4:
            g.mx[3:5, 3:5] = int(t * 12) % 2 == 0
        else:
            mx_taiji(g, ease_out(span(t, 0.35, 1.6)) * 4 * math.pi + t * 0.6)
        g.mx_level = 8 if 1.75 < t < 1.95 else 3 if 1.95 <= t < 2.2 else 1
