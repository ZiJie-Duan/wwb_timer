"""罗盘定向。

方形地盘上圆形天盘：天池磁针（南端为箭头，传统图南在上）、后天八卦一层、二十四山刻度一层，
天心十道（十字红线）固定。磁针晃动后定于子午；天盘两度转动，十字线正上方所对之卦为上卦、下卦，
再以先天数（乾一兑二离三震四巽五坎六艮七坤八）上下卦数之和除六取余为动爻（梅花易数取爻法）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.cn import cn_num
from ..engine.fx import ring
from ..engine.gfx import Gfx
from ..engine.scene import Omen, register
from ..engine.symbols import HOUTIAN, bagua_ring, draw_trigram, mx_trigram
from .o_common import REVEAL, hexa, lines_of, reveal
from .o_data import XIANTIAN_NUM

CX, CY = 38, 32
DIRS = {"离": "南", "坤": "西南", "兑": "西", "乾": "西北", "坎": "北", "艮": "东北", "震": "东", "巽": "东南"}
SPIN = ((1.15, 2.55), (2.95, 4.35))


@register
class LuopanOmen(Omen):
    id = "o.luopan"
    name = "罗盘"
    desc = "方盘圆盘，磁针定子午；天盘两度旋转，十字线所指之卦为上下卦，先天数定动爻"
    T = {"play": 5.0 + REVEAL}

    def setup(self):
        self.idx = [self.rng.randrange(8), self.rng.randrange(8)]
        self.tri = [HOUTIAN[i] for i in self.idx]
        self.turns = [2 + self.rng.random(), 1.5 + self.rng.random()]
        up, lo = self.tri
        self.mv = (XIANTIAN_NUM[up] + XIANTIAN_NUM[lo]) % 6 or 6
        self.lines = lines_of(up, lo, self.mv)
        # 天盘角度关键帧
        self.rots = [0.0]
        cur = 0.0
        for i, turns in zip(self.idx, self.turns):
            end = -i * math.pi / 4
            while end > cur - turns * 2 * math.pi:
                end -= 2 * math.pi
            self.rots.append(end)
            cur = end

    def rot(self, t: float) -> float:
        r = self.rots[0]
        for k, (a, b) in enumerate(SPIN):
            if t >= a:
                r = lerp(self.rots[k], self.rots[k + 1], ease_out(span(t, a, b)))
        return r

    def compass(self, g: Gfx, cx: float, cy: float, s: float, rot: float, needle: float, grow: float = 1.0,
                detail: bool = True):
        R = 29 * s
        if detail:  # 方形地盘 + 天心十道
            g.d.rectangle((cx - R - 2, cy - R - 2, cx + R + 2, cy + R + 2), outline=1)
            for k in (3, 5):
                g.px(cx - R - 2 + k, cy - R - 2 + k)
                g.px(cx + R + 2 - k, cy - R - 2 + k)
                g.px(cx - R - 2 + k, cy + R + 2 - k)
                g.px(cx + R + 2 - k, cy + R + 2 - k)
        if grow > 0:
            g.d.ellipse((cx - R * grow, cy - R * grow, cx + R * grow, cy + R * grow), outline=1, fill=0)
        if grow > 0.4:
            r2 = 25 * s * grow
            g.d.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), outline=1)
            for j in range(24):  # 二十四山
                a = rot + (j + 0.5) * math.pi / 12
                ux, uy = math.sin(a), -math.cos(a)
                l0 = 25.5 * s if j % 2 else 26.5 * s
                g.d.line((cx + ux * l0, cy + uy * l0, cx + ux * 28 * s, cy + uy * 28 * s), fill=1)
        if grow > 0.7 and detail:
            bagua_ring(g, cx, cy, 14 * s, rot, HOUTIAN, w=int(8 * s), step=2.6 * s)
        r3 = 11 * s * min(1, grow * 1.4)
        if r3 > 1:
            g.d.ellipse((cx - r3, cy - r3, cx + r3, cy + r3), outline=1, fill=0)
        if grow > 0.9:  # 磁针：南端箭头朝上
            ux, uy = math.sin(needle), -math.cos(needle)
            tx, ty = -uy, ux
            L = 9 * s
            tip = (cx + ux * L, cy + uy * L)
            g.d.polygon([tip, (cx + tx * 2, cy + ty * 2), (cx - tx * 2, cy - ty * 2)], fill=1)
            g.d.line((cx, cy, cx - ux * L, cy - uy * L), fill=1)
            g.d.rectangle((cx - 1, cy - 1, cx + 1, cy + 1), fill=0, outline=1)
        if detail:  # 十字线（虚）
            for y in range(int(cy - R - 2), int(cy + R + 3), 3):
                g.px(cx, y)
            for x in range(int(cx - R - 2), int(cx + R + 3), 3):
                g.px(x, cy)

    def panel(self, g: Gfx, t: float):
        for k, (y, word) in enumerate(((3, "上卦"), (33, "下卦"))):
            a, b = SPIN[k]
            if t < a - 0.2:
                continue
            g.text(76, y, word)
            if t >= b:
                p = ease_out_back(span(t, b, b + 0.25))
                tri = self.tri[k]
                draw_trigram(g, 106, y + 1, tri, w=max(6, int(14 * min(p, 1.1))), h=2, step=4)
                if t > b + 0.15:
                    g.text(76, y + 14, f"{tri}·{DIRS[tri]}")
            else:  # 转动中：滚动的卦名
                tri = HOUTIAN[int(-self.rot(t) / (math.pi / 4) + 0.5) % 8]
                g.text(110, y, tri, align="center")

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        rot = self.rot(t)
        wob = 0.0
        if t > 0.35:
            q = t - 0.35
            wob = 1.2 * math.exp(-q * 3.2) * math.sin(q * 13)
        if t >= R0:
            k = t - R0
            p = ease_in_out(span(k, 0, 0.4))
            cx, cy, s = lerp(CX, 114, p), lerp(CY, 15, p), lerp(1, 0.42, p)
            self.compass(g, cx, cy, s, rot, wob, detail=p < 0.15)
            hexa(g, self.lines, clamp((k - 0.25) / 0.35) * 6)
            reveal(g, self.lines, k, name_x=40, show_hexa=False)
            return
        grow = ease_out(span(t, 0, 0.6))
        self.compass(g, CX, CY, 1, rot, wob + (1 - grow) * 3, grow)
        # 顶上指标：停盘时闪
        flash = any(b <= t < b + 0.3 for _, b in SPIN)
        g.d.polygon([(CX - 3, 0), (CX + 3, 0), (CX, 3)], fill=1)
        if flash:
            k = min(t - b for _, b in SPIN if t >= b)
            ring(g, CX, CY - 19, 3 + k * 20, density=2)
        self.panel(g, t)
        # 点阵：转动时一根旋转的指针，停下时显示所得之卦
        stopped = [k for k, (a, b) in enumerate(SPIN) if t >= b]
        spinning = any(a <= t < b for a, b in SPIN)
        if spinning or not stopped:
            a = rot if spinning else wob
            for r in range(4):
                g.mx_set(int(round(3.5 + math.sin(a) * r)), int(round(3.5 - math.cos(a) * r)))
            g.mx[0, 3:5] = True
        else:
            mx_trigram(g, self.tri[stopped[-1]])
        g.mx_level = 4 if flash else 1
