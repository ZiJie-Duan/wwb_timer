"""扶乩（扶鸾）。

沙盘铺沙，正副鸾生扶着丁字形桃木乩笔；乩笔先颤动（“乩动”），然后在沙上自下而上划出六爻，
变爻旁按六爻记法补一笔：老阳记“○”（重）、老阴记“×”（交）。写毕提笔，乩示卦名。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Omen, register
from ..engine.symbols import cast_coins, changing, mx_hexagram, yang
from .o_common import REVEAL, reveal

LX, LW = 10, 36                 # 沙上卦：左、宽
def LY(i): return 8 + (5 - i) * 7   # 第 i 爻的 y
W0 = 1.25                       # 开始写
PER = 0.62                      # 每爻
MOVE = 0.12                     # 换行提笔


def _sand(seed: int) -> Sprite:
    rng = np.random.default_rng(seed)
    on = rng.random((64, 128)) < 0.045
    on[:3, :] = on[-3:, :] = False
    on[:, :3] = on[:, -3:] = False
    return Sprite(on=on, mask=on.copy())


SAND = _sand(7)


@register
class FujiOmen(Omen):
    id = "o.fuji"
    name = "扶乩"
    desc = "沙盘上桃木乩笔颤动降笔，自下而上划出六爻，变爻旁补○×，乩示卦名"
    T = {"play": W0 + 6 * PER + 0.55 + REVEAL}

    def setup(self):
        self.lines = cast_coins(self.rng)

    # ------------------------------------------------------------ 零件

    def tray(self, g: Gfx, a: float = 1.0):
        g.blit(SAND, 0, 0)
        g.d.rectangle((0, 0, 127, 63), outline=1)
        g.d.rectangle((2, 2, 125, 61), outline=1)

    def pen(self, g: Gfx, x: float, y: float, lift: float = 0.0):
        """丁字桃木乩笔（俯视）：笔尖在 (x, y)，杆向右上，横木两端由两人扶着"""
        jx, jy = x + 12, y - 14 - lift * 2
        ends = ((jx - 10, jy - 26), (jx + 30, jy - 4))
        for w, f in ((5, 0), (2, 1)):
            g.d.line((x, y - lift, jx, jy), fill=f, width=w)
            for ex, ey in ends:
                g.d.line((jx, jy, ex, ey), fill=f, width=w)
        for ex, ey in ends:  # 两只扶笔的手
            g.d.ellipse((ex - 4, ey - 3, ex + 4, ey + 3), fill=0, outline=1)
        g.d.rectangle((x - 1, y - lift - 1, x + 1, y - lift + 1), fill=1)
        if lift < 0.5:  # 着沙处扬起的细沙
            g.px(x - 2, y + 2)
            g.px(x + 3, y + 1)

    def groove(self, g: Gfx, x0: float, x1: float, y: float):
        if x1 <= x0:
            return
        g.d.rectangle((x0 - 1, y - 2, x1 + 1, y + 3), fill=0)
        g.d.rectangle((x0, y, x1, y + 1), fill=1)

    def mark(self, g: Gfx, i: int, p: float):
        """变爻记号：老阳 ○，老阴 ×"""
        if p <= 0:
            return
        cx, cy = LX + LW + 6, LY(i) + 1
        g.d.rectangle((cx - 4, cy - 4, cx + 4, cy + 4), fill=0)
        if yang(self.lines[i]):
            n = int(12 * p)
            for k in range(n):
                a = k / 12 * 2 * math.pi
                g.px(cx + math.cos(a) * 3, cy + math.sin(a) * 3)
        else:
            g.d.line((cx - 3, cy - 3, cx - 3 + 6 * min(1, p * 2), cy - 3 + 6 * min(1, p * 2)), fill=1)
            if p > 0.5:
                q = (p - 0.5) * 2
                g.d.line((cx + 3, cy - 3, cx + 3 - 6 * q, cy - 3 + 6 * q), fill=1)

    def written(self, g: Gfx, t: float):
        """画出到 t 为止沙上的笔画，返回笔尖 (x, y, lift)"""
        tip = None
        for i in range(6):
            t0 = W0 + i * PER
            if t < t0:
                break
            k = (t - t0 - MOVE) / (PER - MOVE)
            y = LY(i) + 1
            ch = changing(self.lines[i])
            draw_k = clamp(k / (0.75 if ch else 1.0))
            xe = LX + LW * draw_k
            if yang(self.lines[i]):
                self.groove(g, LX, xe, y)
            else:
                gap0, gap1 = LX + LW * 0.38, LX + LW * 0.62
                self.groove(g, LX, min(xe, gap0), y)
                if xe > gap1:
                    self.groove(g, gap1, xe, y)
            if ch:
                self.mark(g, i, clamp((k - 0.75) / 0.25))
            if k < 0:  # 提笔移到下一爻起点
                p = ease_in_out(clamp((t - t0) / MOVE))
                px = lerp(LX + LW if i else 90, LX, p)
                py = lerp(LY(i - 1) + 1 if i else 30, y, p)
                tip = (px, py, 4 * math.sin(p * math.pi))
            elif k <= 1:
                if ch and k > 0.75:
                    cx, cy = LX + LW + 6, LY(i) + 1
                    a = (k - 0.75) / 0.25 * 2 * math.pi
                    tip = (cx + math.cos(a) * 3, cy + math.sin(a) * 3, 0)
                else:
                    lift = 0.0
                    if not yang(self.lines[i]) and LX + LW * 0.36 < xe < LX + LW * 0.64:
                        lift = 3
                    tip = (xe, y + (noise(t * 20, i) - 0.5), lift)
            else:
                tip = (LX + LW, y, 2)
        return tip

    # ------------------------------------------------------------ 演出

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        self.tray(g)
        if t < 0.45:
            g.fade(span(t, 0, 0.45))
        tip = self.written(g, min(t, W0 + 6 * PER))
        if t >= R0:
            k = t - R0
            g.d.rectangle((58, 5, 124, 37), fill=0)
            g.d.rectangle((3, 46, 124, 61), fill=0)
            reveal(g, self.lines, k, name_x=62, show_hexa=False)
            return
        if t < W0:  # 乩笔从右上移入，颤动画圈（悬空）
            p = ease_out(span(t, 0.3, 0.9))
            x = lerp(150, 90, p) + math.cos(t * 17) * 3 * (t > 0.7)
            y = lerp(-20, 30, p) + math.sin(t * 17) * 3 * (t > 0.7)
            self.pen(g, x, y, lift=4)
            if t > 0.95:  # 降笔：一圈光点
                r = (t - 0.95) * 40
                for j in range(10):
                    a = j / 10 * 2 * math.pi
                    g.px(x + math.cos(a) * r, y + math.sin(a) * r * 0.7)
        elif t < W0 + 6 * PER:
            x, y, lift = tip
            self.pen(g, x, y, lift)
        else:  # 提笔离去
            p = ease_in(span(t, W0 + 6 * PER, R0))
            self.pen(g, lerp(LX + LW, 140, p), lerp(LY(5) + 1, -30, p), lift=4)
        # 点阵：已写的爻 + 笔尖
        done = sum(1 for i in range(6) if t >= W0 + (i + 1) * PER)
        mx_hexagram(g, self.lines, done)
        if tip and t < W0 + 6 * PER:
            g.mx_set(int((tip[0] - LX) / LW * 7.99), 6 - done)
        elif t < W0:
            g.mx_set(int(4 + math.cos(t * 17) * 2), int(4 + math.sin(t * 17) * 2))
