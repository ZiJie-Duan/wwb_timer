"""天地重开：芯片清零时播放。

白光一闪（清零）→ 混沌：噪点卷成漩涡，“有物混成”（《道德经》二十五章）→
清浊分离：一半的气轻清上升为天（“阳清为天”），一半重浊下沉为地（“阴浊为地”，《三五历纪》）→
一道横光劈开天地 → 天上星辰流云，地上群山，“天地重开”。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import brush_reveal, cloud, stars
from ..engine.gfx import Gfx
from ..engine.scene import Special, register

N = 110
SPLIT = (1.9, 3.3)   # 清浊分离
CUT = 3.25           # 劈开的一瞬
SKY = 3.5            # 天地成形
RIDGE = [(0, 50), (10, 46), (18, 48), (30, 43), (40, 45), (50, 44), (62, 48), (74, 42), (86, 46), (96, 45),
         (108, 48), (118, 43), (128, 46)]


def ridge_y(x: float) -> float:
    for (x0, y0), (x1, y1) in zip(RIDGE, RIDGE[1:]):
        if x0 <= x <= x1:
            return lerp(y0, y1, (x - x0) / (x1 - x0))
    return 48


@register
class Reset(Special):
    id = "s.reset"
    name = "天地重开"
    desc = "白光清零，混沌噪点卷成漩涡；清气上升浊气下沉，一道横光判开天地，星云群山，“天地重开”"
    T = {"play": 5.8}

    def setup(self):
        s = self.seed
        self.pts = []
        for k in range(N):
            r = 3 + rand(k, s) ** 0.7 * 34
            a0 = rand(k + 500, s) * 2 * math.pi
            light = rand(k + 900, s) < 0.5
            tx = rand(k + 1300, s) * 128
            ty = 2 + rand(k + 1700, s) * 26 if light else 0.0
            if not light:
                ty = ridge_y(tx) + 1 + rand(k + 2100, s) * (62 - ridge_y(tx))
            self.pts.append((r, a0, light, tx, ty, rand(k + 2500, s) * 0.5))

    def vortex(self, k: int, t: float) -> tuple[float, float]:
        r, a0, *_ = self.pts[k]
        rr = r * (1 - 0.25 * math.sin(t * 2 + k))
        a = a0 + t * (5.0 / (1 + r / 8)) + rr * 0.08
        return 64 + math.cos(a) * rr * 1.5, 32 + math.sin(a) * rr * 0.75

    def play(self, g: Gfx, t: float):
        # 白光：清零
        if t < 0.25:
            g.d.rectangle((0, 0, 127, 63), fill=1)
            if t > 0.1:
                g.fade(1 - span(t, 0.1, 0.25))
            g.mx[:] = True
            g.mx_level = 8
            return
        # 地：浊气沉积（抖动灰度逐渐加深）+ 山脊
        earth = ease_in_out(span(t, SPLIT[0] + 0.4, SKY + 0.4))
        if earth > 0:
            pts = [(x, lerp(64, y, earth)) for x, y in RIDGE] + [(128, 64), (0, 64)]
            g.shade_poly(pts, 0.15 + 0.35 * earth, outline=1 if earth > 0.6 else None)
        # 气：漩涡 → 分离
        for k, (r, a0, light, tx, ty, delay) in enumerate(self.pts):
            x, y = self.vortex(k, t)
            p = ease_in_out(span(t, SPLIT[0] + delay, SPLIT[1] + delay * 0.5))
            if p > 0:
                x, y = lerp(x, tx, p), lerp(y, ty, p)
            if not light and p >= 1:
                continue  # 已沉入大地
            if light and t > SKY and noise(t * 3 + k, 7) < 0.3:
                continue  # 星光闪烁
            g.px(x, y)
            if p < 0.2 and r < 10:  # 漩涡中心浓密
                g.px(x + 1, y)
        # 漩涡的旋臂
        if t < SPLIT[0] + 0.5:
            fade = 1 - span(t, SPLIT[0], SPLIT[0] + 0.5)
            for arm in range(3):
                pts = []
                for i in range(14):
                    rr = i * 2.6 * fade
                    a = t * 3.2 + arm * 2.094 - i * 0.35
                    pts.append((64 + math.cos(a) * rr * 1.5, 32 + math.sin(a) * rr * 0.75))
                g.d.line(pts, fill=1)
        # 文字
        if 0.5 < t < SPLIT[0] + 0.1:
            k = span(t, 0.5, 1.3)
            n = int(k * 4 + 0.5)
            if n:
                w = n * 12
                g.d.rectangle((64 - w / 2 - 2, 52, 64 + w / 2 + 1, 63), fill=0)
                g.text(64, 52, "有物混成"[:n], align="center")
        if SPLIT[0] + 0.2 < t < CUT:
            g.d.rectangle((2, 1, 51, 12), fill=0)
            g.text(4, 1, "阳清为天"[: int(span(t, SPLIT[0] + 0.2, SPLIT[0] + 0.6) * 4 + 0.5)])
            if t > SPLIT[0] + 0.6:
                g.d.rectangle((76, 51, 126, 63), fill=0)
                g.text(124, 52, "阴浊为地"[: int(span(t, SPLIT[0] + 0.6, SPLIT[0] + 1.0) * 4 + 0.5)],
                       align="right")
        # 一道横光判开天地
        c = span(t, CUT - 0.15, CUT + 0.25)
        if 0 < c < 1:
            x1 = 128 * ease_out(clamp(c * 2.5))
            hw = 2 * (1 - c)
            g.d.rectangle((0, 33 - hw, x1, 33 + hw), fill=1)
            for j in range(10):
                xx = rand(j, 3) * x1
                g.d.line((xx, 33 - 3 - rand(j, 4) * 6 * (1 - c), xx, 33 + 3 + rand(j, 5) * 6 * (1 - c)), fill=1)
        # 天：流云、新月；中央“天地重开”
        if t > SKY:
            k = t - SKY
            drift = k * 6
            cloud(g, 20 + drift, 9, 20, 6, seed=3)
            cloud(g, 84 - drift * 0.7, 12, 16, 5, seed=8)
            m = ease_out(span(k, 0, 0.6))
            g.d.ellipse((108, 2 + (1 - m) * 10, 118, 12 + (1 - m) * 10), fill=1)
            g.d.ellipse((111, 1 + (1 - m) * 10, 121, 11 + (1 - m) * 10), fill=0)
            if k > 0.3:
                p = span(k, 0.3, 1.5)
                g.d.rectangle((14, 17, 113, 41), fill=0)
                brush_reveal(g, 16, 18, "天地重开", p, size=12, scale=2)
        # 点阵：混沌噪点 → 上清下浊 → 天地
        if t < SPLIT[0]:
            f = int(t * 30)
            for i in range(64):
                if rand(i + f * 64, 11) < 0.4:
                    g.mx[i // 8, i % 8] = True
        else:
            p = span(t, SPLIT[0], SPLIT[1])
            f = int(t * 30)
            for i in range(64):
                y, x = divmod(i, 8)
                keep = rand(i + f * 64, 11) < 0.4
                if y < 4:
                    keep = keep and rand(i, 12) > p * 0.8
                else:
                    keep = keep or rand(i, 13) < p
                g.mx[y, x] = keep
            if t > CUT:
                g.mx[:4] = False
                for i in range(5):
                    if noise(t * 2 + i * 3, 5) > 0.35:
                        g.mx_set(int(rand(i, 14) * 8), int(rand(i, 15) * 3))
                g.mx[5:] = True
                g.mx[4, 1:3] = True
                g.mx[4, 5:8] = True
        g.mx_level = 8 if CUT - 0.1 < t < CUT + 0.15 else 1
