"""大衍筮法（蓍草揲蓍）。

《周易·系辞上》：“大衍之数五十，其用四十有九。分而为二以象两，挂一以象三，揲之以四以象四时，
归奇于扐以象闰。”三变成一爻：每变去掉 挂一 + 两边余数，三变后余 36/32/28/24 根，
以四除得 9/8/7/6（老阳/少阴/少阳/老阴）。十八变成卦。
第一变逐步演示，其余十七变快进，卦象在左边长出。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Omen, register
from ..engine.symbols import mx_hexagram
from .o_common import REVEAL, YAO_NAME, hexa, label, reveal

X0, DX = 15, 2          # 第一变：蓍草横排
Y0, Y1 = 24, 50
HANG = (6, 54)          # 挂一 / 归奇 的位置（左下）
QUOTES = [(0.0, "大衍之数五十"), (0.7, "其用四十有九"), (1.25, "分而为二以象两"), (1.75, "挂一以象三"),
          (2.15, "揲之以四以象四时"), (3.15, "归奇于扐以象闰")]
DETAIL = 3.9            # 第一变演示结束
NUM = {6: "六", 7: "七", 8: "八", 9: "九"}


def one_change(n: int, rng) -> tuple[int, int, int, int]:
    """一变：返回 (左把数, 左余, 右余, 变后数)"""
    left = int(round(rng.gauss(n / 2, n / 9)))
    left = max(2, min(n - 3, left))
    right = n - left - 1  # 挂一（取自右把）
    rl = left % 4 or 4
    rr = right % 4 or 4
    return left, rl, rr, n - 1 - rl - rr


@register
class DayanOmen(Omen):
    id = "o.dayan"
    name = "大衍筮"
    desc = "五十根蓍草，取一不用；分二、挂一、揲四、归奇，十八变成卦"
    T = {"play": 6.3 + REVEAL}

    def setup(self):
        self.changes = []  # 18 个 (变前数, 左把, 左余, 右余, 变后数)
        self.lines = []
        for _ in range(6):
            n = 49
            for _ in range(3):
                left, rl, rr, m = one_change(n, self.rng)
                self.changes.append((n, left, rl, rr, m))
                n = m
            self.lines.append(n // 4)

    # ------------------------------------------------------------ 第一变（逐步）

    def detail(self, g: Gfx, t: float):
        n0, left, rl, rr, n1 = self.changes[0]
        q = [s for t0, s in QUOTES if t >= t0]
        t0 = max(t0 for t0, s in QUOTES if t >= t0)
        typewriter(g, 64, 3, q[-1], t - t0, cps=16, align="center")
        appear = span(t, 0.0, 0.5)
        split = ease_in_out(span(t, 1.25, 1.6))
        hang = ease_in_out(span(t, 1.75, 2.1))
        # 揲四：左把在 2.15–2.65 去掉，右把在 2.65–3.15 去掉；归奇 3.15–3.6
        gl = (left - rl) // 4
        right = n0 - left - 1
        gr = (right - rr) // 4
        back = ease_in_out(span(t, 3.15, 3.6))
        pile = 0  # 归奇处已有的根数（挂一 + 余）
        for i in range(50):
            x = X0 + i * DX
            if i / 50 > appear:
                break
            if i == 49:  # 取一不用：升起，横置于右下
                p = ease_in_out(span(t, 0.7, 1.15))
                if p <= 0:
                    g.d.line((x, Y0, x, Y1), fill=1)
                else:
                    cx, cy = lerp(x, 112, p), lerp((Y0 + Y1) / 2, 58, p)
                    a = p * math.pi / 2
                    L = 13 - p * 1
                    g.d.line((cx - math.sin(a) * L, cy - math.cos(a) * L, cx + math.sin(a) * L,
                              cy + math.cos(a) * L), fill=1)
                continue
            y0, y1 = Y0, Y1
            if i < left:
                x -= split * 5
                k = (left - 1 - i) // 4  # 从右往左数第几组
                is_rem = i < rl
                if not is_rem:
                    p = span(t, 2.15 + k * 0.5 / max(gl, 1), 2.15 + (k + 1) * 0.5 / max(gl, 1))
                    if p >= 1:
                        continue
                    y0 += ease_in(p) * 20
                    y1 += ease_in(p) * 20
                elif back > 0:
                    x = lerp(x, HANG[0] + 2 + i, back)
                    y0, y1 = lerp(Y0, HANG[1] - 10, back), lerp(Y1, HANG[1] + 8, back)
                elif t > 2.65:
                    y0 -= 3
                    y1 -= 3
            else:
                x += split * 5
                j = i - left
                if j == 0:  # 挂一
                    if hang > 0:
                        x = lerp(x, HANG[0], hang)
                        y0, y1 = lerp(Y0, HANG[1] - 10, hang), lerp(Y1, HANG[1] + 8, hang)
                else:
                    jj = j - 1
                    is_rem = jj >= right - rr
                    k = jj // 4
                    if not is_rem:
                        p = span(t, 2.65 + k * 0.5 / max(gr, 1), 2.65 + (k + 1) * 0.5 / max(gr, 1))
                        if p >= 1:
                            continue
                        y0 += ease_in(p) * 20
                        y1 += ease_in(p) * 20
                    elif back > 0:
                        x = lerp(x, HANG[0] + 6 + (jj - (right - rr)), back)
                        y0, y1 = lerp(Y0, HANG[1] - 10, back), lerp(Y1, HANG[1] + 8, back)
                    elif t > 3.15 - 0.01:
                        y0 -= 3
                        y1 -= 3
            g.d.line((x, y0, x, y1), fill=1)
        if t > 3.6:
            g.text(64, 54, f"{n0}-{1 + rl + rr}={n1}", size=8, align="center")
        # 点阵：一捆蓍草
        cols = 8 if t < 1.25 else 7
        for x in range(cols):
            if x / 8 <= appear:
                gx = x if t < 1.25 or x < 3 else x + 1
                if gx < 8:
                    g.mx[1:7, gx] = True

    # ------------------------------------------------------------ 其余十七变（快进）

    def fast(self, g: Gfx, t: float):
        R0 = self.T["play"] - REVEAL
        per = (R0 - DETAIL - 0.3) / 17
        x = (t - DETAIL) / per + 1          # 第几变（小数）
        c = min(17, int(x))
        u = 1.0 if x >= 18 else x - c
        n, left, rl, rr, m = self.changes[c]
        # 爻 i 在第 3i+2 变的 u=0.5 处完成
        yao_done = 0.0
        last = -1
        for i in range(6):
            tc = 3 * i + 2 + 0.5
            if x >= tc:
                yao_done = i + clamp((x - tc) * per / 0.22)
                last = i
        hexa(g, self.lines, yao_done)
        # 右边：一捆蓍草，前半分成两把，后半去掉 挂一 + 余数
        cur = n if u < 0.5 else m
        bx0, bx1 = 46, 124
        sp = (bx1 - bx0 - 6) / 48
        for i in range(cur):
            xx = bx0 + i * sp + (6 if i >= left and u < 0.5 else 0)
            g.d.line((xx, 18, xx, 40), fill=1)
        g.text(85, 44, str(cur), size=8, align="center")
        g.text(85, 3, f"第{cn_num(min(5, c // 3) + 1)}爻", align="center")
        if last >= 0:
            v = self.lines[last]
            tc = DETAIL + (3 * last + 2 + 0.5 - 1) * per
            label(g, 85, 51, f"{NUM[v]}·{YAO_NAME[v]}", t - tc)
        mx_hexagram(g, self.lines, int(yao_done))
        g.mx[7, : max(1, int(cur / 49 * 8))] = True

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        if t >= R0:
            reveal(g, self.lines, t - R0)
            return
        if t < DETAIL:
            self.detail(g, t)
            if t > DETAIL - 0.25:
                g.fade(1 - span(t, DETAIL - 0.25, DETAIL))
        else:
            self.fast(g, t)
