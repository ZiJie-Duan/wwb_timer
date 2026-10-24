"""罗盘定向。

方形地盘上圆形天盘：天池磁针（南端为箭头，传统图南在上）、后天八卦一层、二十四山刻度一层，
天心十道（十字线）固定。磁针乱转后晃定于子午；小道士剑指一拨，天盘飞转（边上火星飞溅），
“咔”地停下，顶上指标所对之卦为上卦；再拨一次得下卦。
再以先天数（乾一兑二离三震四巽五坎六艮七坤八）上下卦数之和除六取余为动爻（梅花易数取爻法）。
揭晓时罗盘缩小飞回小道士手里。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import HOUTIAN, bagua_ring, draw_trigram, mx_trigram
from .o_common import FLOOR, REVEAL, Base, floor, lines_of, star4
from .o_data import XIANTIAN_NUM

DAO_X = 18
CX, CY = 88, 31
SPIN = ((1.35, 2.65), (3.15, 4.45))
R0 = 5.2


def _mini():
    """手里的小罗盘 9×9"""
    p = Part(9, 9)
    p.shape("rectangle", (0, 0, 8, 8), fill=1)
    p.d.ellipse((1, 1, 7, 7), fill=0)
    p.d.line((4, 2, 4, 6), fill=1)
    p.px(3, 3), p.px(5, 3)
    return p.sprite()


SPR = {}


@register
class LuopanOmen(Base):
    id = "o.luopan"
    name = "罗盘"
    desc = "大罗盘磁针乱转后定子午；小道士剑指两拨，天盘飞转火星四溅，咔地停住，指标所对得上卦、下卦"
    T = {"play": R0 + REVEAL}

    def init(self):
        self.idx = [self.rng.randrange(8), self.rng.randrange(8)]
        self.tri = [HOUTIAN[i] for i in self.idx]
        up, lo = self.tri
        self.mv = (XIANTIAN_NUM[up] + XIANTIAN_NUM[lo]) % 6 or 6
        self.lines = lines_of(up, lo, self.mv)
        self.rots = [0.0]
        cur = 0.0
        for i in self.idx:
            turns = 1.5 + self.rng.random()
            end = -i * math.pi / 4
            while end > cur - turns * 2 * math.pi:
                end -= 2 * math.pi
            self.rots.append(end)
            cur = end

    def rot(self, t: float) -> float:
        r = self.rots[0]
        for k, (a, b) in enumerate(SPIN):
            if t >= a:
                q = span(t, a, b)
                r = lerp(self.rots[k], self.rots[k + 1], ease_out(q) if q < 0.97 else 1.0)
        return r

    def needle(self, t: float) -> float:
        """磁针：先乱转，再晃几下定于子午（0 = 南端朝上）"""
        return (1 - ease_out(span(t, 0, 1.1))) * 14 + math.sin(t * 13) * 0.7 * math.exp(-t * 2.2)

    def compass(self, g: Gfx, cx: float, cy: float, rot: float, nd: float, t: float, s: float = 1.0):
        """s = 缩放（入场弹出 / 揭晓时缩小）"""
        R = 22 * s
        H = 25 * s
        # 地盘：方形木板，双线框、四角铜钉、木纹网点
        g.d.rectangle((cx - H, cy - H, cx + H, cy + H), fill=0, outline=1)
        g.d.rectangle((cx - H + 2, cy - H + 2, cx + H - 2, cy + H - 2), outline=1)
        if s > 0.6:
            for sx in (-1, 1):  # 四角：云头角花（实心三角 + 网点）+ 铜钉
                for sy in (-1, 1):
                    x0, y0 = cx + sx * (H - 2), cy + sy * (H - 2)
                    g.d.polygon([(x0, y0), (x0 - sx * 9, y0), (x0, y0 - sy * 9)], fill=1)
                    pix.checker(g, (min(x0, x0 - sx * 5), min(y0, y0 - sy * 5), max(x0, x0 - sx * 5) + 1,
                                    max(y0, y0 - sy * 5) + 1), 0.5, 0)
                    x, y = cx + sx * (H - 5), cy + sy * (H - 5)
                    g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=0)
                    g.px(x, y)
        # 天盘
        g.d.ellipse((cx - R - 2, cy - R - 2, cx + R + 2, cy + R + 2), fill=0)
        g.d.ellipse((cx - R - 1, cy - R - 1, cx + R + 1, cy + R + 1), outline=1)
        g.d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=1)
        if s > 0.6:
            for j in range(24):  # 二十四山刻度
                a = rot + j * math.pi / 12
                r0 = R - (4 if j % 3 == 0 else 2)
                g.d.line((cx + math.sin(a) * r0, cy - math.cos(a) * r0, cx + math.sin(a) * (R - 1),
                          cy - math.cos(a) * (R - 1)), fill=1)
            g.d.ellipse((cx - R + 5, cy - R + 5, cx + R - 5, cy + R - 5), outline=1)
            bagua_ring(g, cx, cy, 9.5 * s, rot, HOUTIAN, w=6, step=2)
        # 天池 + 磁针
        r = 6 * s
        g.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0, outline=1)
        ux, uy = math.sin(nd), -math.cos(nd)
        L = 5 * s
        g.d.line((cx - ux * L, cy - uy * L, cx + ux * L, cy + uy * L), fill=1)
        hx, hy = cx + ux * L, cy + uy * L  # 南端箭头
        g.d.polygon([(hx, hy), (hx - ux * 2 - uy * 1.5, hy - uy * 2 + ux * 1.5),
                     (hx - ux * 2 + uy * 1.5, hy - uy * 2 - ux * 1.5)], fill=1)
        g.px(cx, cy, 0)
        # 天心十道（固定的十字线）+ 顶上指标
        if s > 0.6:
            pix.dotted(g, cx, cy - H + 1, cx, cy - r - 1, 2)
            pix.dotted(g, cx, cy + r + 1, cx, cy + H - 1, 2)
            pix.dotted(g, cx - H + 1, cy, cx - r - 1, cy, 2)
            pix.dotted(g, cx + r + 1, cy, cx + H - 1, cy, 2)
            g.d.polygon([(cx - 3, cy - H - 4), (cx + 3, cy - H - 4), (cx, cy - H - 1)], fill=1)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        floor(g, "stone")
        rot = self.rot(t)
        spinning = any(a <= t < b - 0.15 for a, b in SPIN)
        # ---------------- 小道士
        if t >= R0:
            k = t - R0
            h = daoshi(g, DAO_X, FLOOR, "offer", t, face="happy")["hand"]
        else:
            flick = any(a - 0.25 <= t < a + 0.2 for a, b in SPIN)
            daoshi(g, DAO_X, FLOOR, "point" if flick else "idle", t,
                   face="wow" if spinning or t < 0.9 else "happy" if any(b <= t < b + 0.4 for a, b in SPIN) else "normal")
        # ---------------- 罗盘
        if t < R0:
            s = ease_out_back(span(t, 0, 0.35))
            if s > 0.05:
                self.compass(g, CX, CY, rot, self.needle(t), t, s)
            if spinning:  # 边缘火星 + 速度弧
                for a, b in SPIN:
                    if a <= t < b:
                        sp = 1 - span(t, a, b)
                        if int(t * 30) % 2 == 0:
                            ang = rot + 0.3
                            self.sparks.burst(CX + math.sin(ang) * 23, CY - math.cos(ang) * 23, 2, 30 * sp + 5,
                                              life=0.3, gravity=40)
                        for j in range(3):
                            a0 = rot * 180 / math.pi + j * 120
                            g.d.arc((CX - 27, CY - 27, CX + 27, CY + 27), a0, a0 + 25 * sp + 5, fill=1)
            for k2, (a, b) in enumerate(SPIN):
                if self.hit(t, a):  # 一拨：剑指射出一道光
                    self.sparks.burst(DAO_X + 18, FLOOR - 19, 6, 25, life=0.3, gravity=0)
                if self.hit(t, b - 0.1):  # 咔：停盘
                    pix.shake(g, t, 2)
                    self.sparks.burst(CX, CY - 29, 10, 30, up=10, life=0.5, gravity=50)
                if b - 0.1 < t < b + 0.3:  # 指标闪光
                    if int(t * 14) % 2 == 0:
                        star4(g, CX, CY - 31, 3)
        else:  # 揭晓：罗盘缩小飞回手里
            if "mini" not in SPR:
                SPR["mini"] = _mini()
            q = ease_in(span(t, R0, R0 + 0.25))
            if q < 1:
                s = lerp(1, 0.2, q)
                self.compass(g, lerp(CX, h[0], q), lerp(CY, h[1], q), rot, 0, t, s)
            else:
                pix.blit(g, SPR["mini"], h[0] - 3, h[1] - 8)
        self.particles(g)
        # ---------------- 上卦 / 下卦（左上角）
        if t < R0:
            for k2, (a, b) in enumerate(SPIN):
                if t >= b - 0.05:
                    tri = self.tri[k2]
                    x = 2 + k2 * 30
                    self.say(x, 2, ("上" if k2 == 0 else "下") + tri, plate=True)
                    if t >= b + 0.1:
                        draw_trigram(g, x + 3, 16, tri, w=18, h=2, step=3)
            # 点阵：转动时一根旋转的指针；停下时显示所得三爻卦
            last = None
            for k2, (a, b) in enumerate(SPIN):
                if t >= b - 0.1:
                    last = self.tri[k2]
            if spinning or last is None:
                a = -rot if spinning else self.needle(t)
                for r in range(4):
                    x, y = int(round(3.5 + math.sin(a) * r)), int(round(3.5 - math.cos(a) * r))
                    g.mx[max(0, min(7, y)), max(0, min(7, x))] = True
            else:
                mx_trigram(g, last)
            g.mx_level = 6 if any(b - 0.1 <= t < b + 0.05 for a, b in SPIN) else 1
        else:
            self.reveal(g, t, R0)
        self.flush(g)
