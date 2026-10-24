"""求签：摇签筒，一支签慢慢探出、跳出落地；拾起一看，“第几签”，以签号对文王卦序定卦。

六十四卦签：签号 1-64 即文王卦序（如第十八签 = 蛊），签只有本卦，不出变爻。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Omen, register
from ..engine.symbols import HEXAGRAMS, mx_hexagram
from .o_common import REVEAL, hexa, lines_of, reveal

BX, BY = 88, 61         # 签筒底心（旋转支点）
TW, TH = 11, 30         # 半宽、高
N_STICK = 9
PICK = 4                # 被摇出的那支
SHAKE0, SHAKE1 = 0.45, 2.7
FALL0, FALL1 = 2.7, 3.3
ZOOM0, ZOOM1 = 3.45, 3.9


def rot(px, py, a, ox=BX, oy=BY):
    c, s = math.cos(a), math.sin(a)
    return ox + px * c - py * s, oy + px * s + py * c


@register
class QianOmen(Omen):
    id = "o.qian"
    name = "求签"
    desc = "摇签筒，一支签越探越高、跳出落地；拾起看签号，第几签即第几卦"
    T = {"play": 5.0 + REVEAL}

    def setup(self):
        self.n = self.rng.randint(1, 64)
        name, up, lo = HEXAGRAMS[self.n - 1]
        self.lines = lines_of(up, lo)
        self.tops = [6 + rand(k, self.seed) * 8 for k in range(N_STICK)]

    # ------------------------------------------------------------ 零件

    def tube(self, g: Gfx, a: float, t: float, rise: float, pick_out: bool, dx: float = 0.0, dy: float = 0.0):
        ox = BX + dx
        P = lambda x, y: rot(x, y, a, ox, BY + dy)
        # 签（先画，筒身盖住下半）
        for k in range(N_STICK):
            if k == PICK and pick_out:
                continue
            x = -TW + 2.5 + k * 2.2
            top = -TH - self.tops[k] - (noise(t * 9 + k * 3, self.seed) * 3 if SHAKE0 < t < SHAKE1 else 0)
            if k == PICK:
                top -= rise
            g.d.line((*P(x, -TH + 4), *P(x, top)), fill=1)
            if k == PICK and rise > 6:  # 签头一点朱红（亮点）
                g.d.line((*P(x, top), *P(x, top + 2)), fill=1, width=2)
        body = [P(-TW, 0), P(TW, 0), P(TW, -TH), P(-TW, -TH)]
        g.d.polygon(body, fill=0, outline=1)
        for yy in (-5, -TH + 5):  # 竹节箍
            g.d.line((*P(-TW, yy), *P(TW, yy)), fill=1)
        g.d.line((*P(-TW + 1, -TH - 1), *P(TW - 1, -TH - 1)), fill=1)  # 筒口
        # 筒身竹纹 + 中间一块签牌
        for xx in (-7, 7):
            g.d.line((*P(xx, -8), *P(xx, -TH + 8)), fill=1)
        lab = [P(-3, -9), P(3, -9), P(3, -TH + 9), P(-3, -TH + 9)]
        g.d.polygon(lab, fill=1)
        for yy in (-12, -15, -18, -21):
            g.d.point(P(0, yy), fill=0)

    def big_stick(self, g: Gfx, cx: float, p: float):
        """拾起的签：竖放，写着“第几签”"""
        h = 62 * p
        if h < 4:
            return
        y0 = 63 - h
        g.d.rectangle((cx - 8, y0, cx + 8, 63), fill=0, outline=1)
        g.d.line((cx - 7, y0 + 1, cx + 7, y0 + 1), fill=1)
        if p >= 0.98:
            s = f"第{cn_num(self.n)}签"
            g.vtext(cx - 6, 4 if len(s) >= 5 else 6 + (5 - len(s)) * 2, s, gap=0 if len(s) >= 5 else 1)

    # ------------------------------------------------------------ 演出

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        if t >= R0:
            k = t - R0
            cx = lerp(64, 150, ease_in(span(k, 0, 0.4)))
            if cx < 140:
                self.big_stick(g, cx, 1.0)
            hexa(g, self.lines, clamp(k / 0.5) * 6)
            reveal(g, self.lines, k, show_hexa=False)
            return
        g.d.line((30, 63, 127, 63), fill=1)
        if t < ZOOM0:
            # 签筒：入场弹起 → 前倾摇动 → 停
            pop = ease_out_back(span(t, 0, 0.4))
            shake = span(t, SHAKE0, SHAKE1)
            a = 0.0
            if 0 < shake < 1:
                env = math.sin(shake * math.pi) ** 0.5
                a = -0.45 * ease_in_out(clamp(shake * 4)) + math.sin(t * 38) * 0.16 * env
            elif shake >= 1:
                a = -0.45 * (1 - ease_out(span(t, FALL0, FALL1)))
            rise = ease_in(shake) * 16
            out = t >= FALL0
            slide = ease_in(span(t, 3.1, ZOOM0)) * 50
            self.tube(g, a, t, rise, out, dx=slide, dy=(1 - pop) * 50)
            if SHAKE0 < t < FALL0:  # 摇动的“哗哗”声线
                for j in range(3):
                    if int(t * 12 + j) % 2:
                        x0, y0 = rot(-TW - 4 - j * 3, -TH + 4 + j * 6, a)
                        g.d.line((x0, y0, x0 - 4, y0 + 1), fill=1)
            if out:  # 签跳出、翻落在筒前
                p = span(t, FALL0, FALL1)
                sx0, sy0 = rot(-TW + 2.5 + PICK * 2.2, -TH - self.tops[PICK] - 10, -0.45)
                x = lerp(sx0, 48, p)
                y = lerp(sy0, 61, ease_out_bounce(p)) - math.sin(p * math.pi) * 10
                ang = lerp(-0.45, -math.pi / 2 - 0.1, ease_out(p)) + math.sin(p * 9) * 0.15 * (1 - p)
                L = 26
                c, s = math.sin(ang), -math.cos(ang)
                g.d.line((x, y, x + c * L, y + s * L), fill=1)
                g.d.line((x, y, x + c * 2, y + s * 2), fill=1, width=2)
                if 0.6 < p < 0.9:
                    for dx in (-3, 3, 9):
                        g.px(x + dx + 10, 62 - (p - 0.6) * 10)
            if t < 2.4:
                g.vtext(8, 6, "诚心求签"[: max(0, int(span(t, 0.3, 1.0) * 4 + 0.5))])
        else:
            # 拾签：签从地上立起，放大到整屏高
            p = ease_out_back(span(t, ZOOM0, ZOOM1))
            self.big_stick(g, 64, clamp(p, 0, 1.05) if p < 1 else 1.0)
            if t > ZOOM1:
                k = t - ZOOM1
                for j in range(6):  # 签旁一闪
                    a = j / 6 * math.pi * 2 + k * 2
                    r = 14 + k * 10
                    if k < 0.6:
                        g.px(64 + math.cos(a) * r, 32 + math.sin(a) * r * 0.9)
        # 点阵
        if t < FALL0:
            sh = int(math.sin(t * 38) * 1.5) if SHAKE0 < t < SHAKE1 else 0
            for x in range(2, 6):
                g.mx[4:8, x + sh // 2 if 0 <= x + sh // 2 < 8 else x] = True
            for k, x in enumerate((2, 3, 4, 5)):
                hh = 1 + (k == 1) * int(span(t, SHAKE0, SHAKE1) * 3) + (k % 2)
                for y in range(4 - hh, 4):
                    g.mx_set(x + sh // 2, y)
        elif t < ZOOM0:
            g.mx[7, :] = True
            g.mx[6, 1:7] = True
        else:
            g.mx[:, 3:5] = True
            g.mx[1, 3:5] = False
            g.mx[3, 3:5] = False
            g.mx_level = 3 if t - ZOOM1 < 0.1 and t > ZOOM1 else 1
