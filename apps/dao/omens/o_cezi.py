"""测字（一字占）。

宣纸展开，毛笔写下一个字；一刀竖分左右，数笔画。《梅花易数·卷一》一字占：
“如楷书，则取其字画……居左者看几数，取为上卦；居右者看几数，取为下卦。又以一字之阴阳，全画取爻。”
本作以字的左右两部分笔画数（简体）各除八取余定上下卦（先天数），全字笔画数除六取余为动爻。
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.cn import cn_num
from ..engine.fx import brush_reveal
from ..engine.gfx import Gfx, _FONT_FILES, font, text_width
from ..engine.scene import Omen, register
from ..engine.symbols import draw_trigram, mx_trigram
from .o_common import REVEAL, hexa, lines_of, reveal
from .o_data import NUM_TRIGRAM

# 字：(左笔画, 右笔画, 左右分界在字宽的比例)
CHARS = {
    "明": (4, 4, 0.42), "林": (4, 4, 0.5), "好": (3, 3, 0.45), "和": (5, 3, 0.55), "信": (2, 7, 0.3),
    "福": (4, 9, 0.4), "禄": (4, 8, 0.4), "静": (8, 6, 0.5), "清": (3, 8, 0.3), "神": (4, 5, 0.42),
    "仙": (2, 3, 0.3), "时": (4, 3, 0.42), "炉": (4, 4, 0.42), "松": (4, 4, 0.42), "卦": (6, 2, 0.6),
    "悟": (3, 7, 0.3), "根": (4, 6, 0.42), "缘": (3, 9, 0.33), "证": (2, 5, 0.3), "情": (3, 8, 0.3),
}
SC = 3                      # 放大倍数
PX, PY = 8, 6               # 纸左上
CW = 12 * SC                # 字宽
CXL, CYT = 14, 16           # 字左上
WRITE = (0.55, 2.0)
CUT = (2.2, 2.75)
COUNT = (2.9, 4.6)


def mx_char(ch: str) -> np.ndarray:
    img = Image.new("1", (8, 8))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((0, -_FONT_FILES[8][1] + 0), ch, font=font(8), fill=1)
    return np.array(img, dtype=bool)


@register
class CeziOmen(Omen):
    id = "o.cezi"
    name = "测字"
    desc = "宣纸展开，毛笔写一个字；一刀分左右，数笔画：左为上卦、右为下卦，全画取动爻"
    T = {"play": 5.2 + REVEAL}

    def setup(self):
        self.ch = self.rng.choice(sorted(CHARS))
        self.nl, self.nr, self.cut = CHARS[self.ch]
        self.total = self.nl + self.nr
        self.up = NUM_TRIGRAM[self.nl % 8 or 8]
        self.lo = NUM_TRIGRAM[self.nr % 8 or 8]
        self.mv = self.total % 6 or 6
        self.lines = lines_of(self.up, self.lo, self.mv)
        self.mx = mx_char(self.ch)

    def paper(self, g: Gfx, p: float):
        """一张竖幅宣纸，上下两根轴，从中间往上下展开"""
        h = 52 * ease_out(p)
        cy = 32
        y0, y1 = cy - h / 2, cy + h / 2
        g.d.rectangle((PX, y0, PX + 46, y1), fill=0, outline=1)
        for y in (y0 - 2, y1 + 1):
            g.d.rectangle((PX - 3, y, PX + 49, y + 1), fill=1)
        return y0, y1

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        sep = ease_out_back(span(t, CUT[0] + 0.3, CUT[1])) * 5
        if t >= R0:
            sep = 5
        self.paper(g, span(t, 0, 0.5))
        if t >= WRITE[0]:
            p = span(t, *WRITE)
            if p < 1:
                brush_reveal(g, CXL, CYT, self.ch, p, size=12, scale=SC)
                # 笔杆：从笔尖往右上
                tipy = CYT + 12 * SC * p
                tipx = CXL + CW * (0.3 + 0.4 * math.sin(p * 9))
                g.d.line((tipx, tipy, tipx + 18, tipy - 28), fill=1, width=2)
                g.d.polygon([(tipx, tipy), (tipx + 3, tipy - 5), (tipx - 1, tipy - 4)], fill=1)
            else:
                g.text(CXL, CYT, self.ch, scale=SC)
                if sep > 0:  # 左右分开
                    a = g.array()
                    cx = int(CXL + CW * self.cut)
                    s = int(round(sep))
                    box = a[CYT - 2:CYT + 12 * SC + 2, CXL - 2:CXL + CW + 2].copy()
                    a[CYT - 2:CYT + 12 * SC + 2, CXL - 6:CXL + CW + 7] = False
                    k = cx - (CXL - 2)
                    a[CYT - 2:CYT + 12 * SC + 2, CXL - 2 - s:CXL - 2 - s + k] = box[:, :k]
                    a[CYT - 2:CYT + 12 * SC + 2, cx + s:cx + s + box.shape[1] - k] = box[:, k:]
                    g.put(a)
        # 一刀：竖线从上划到下
        if CUT[0] <= t < CUT[1] + 0.2:
            q = ease_in(span(t, CUT[0], CUT[0] + 0.3))
            cx = CXL + CW * self.cut
            g.d.line((cx, CYT - 4, cx, CYT - 4 + (12 * SC + 8) * q), fill=1)
            if q < 1:
                g.d.polygon([(cx - 2, CYT - 4 + (12 * SC + 8) * q - 6), (cx + 2, CYT - 4 + (12 * SC + 8) * q - 6),
                             (cx, CYT - 4 + (12 * SC + 8) * q)], fill=1)
        if t >= R0:
            k = t - R0
            g.fade(1 - span(k, 0, 0.3))
            hexa(g, self.lines, clamp((k - 0.2) / 0.35) * 6)
            reveal(g, self.lines, k, show_hexa=False)
            return
        # 右侧：数笔画 → 上下卦 → 动爻
        cx = CXL + CW * self.cut
        if t >= COUNT[0]:
            cl = min(self.nl, int(span(t, COUNT[0], COUNT[0] + 0.6) * self.nl + 0.999))
            cr = min(self.nr, int(span(t, COUNT[0] + 0.5, COUNT[0] + 1.1) * self.nr + 0.999))
            g.text((CXL + cx) / 2 - sep, 50, str(cl), size=8, align="center")
            if t >= COUNT[0] + 0.5:
                g.text((cx + CXL + CW) / 2 + sep, 50, str(cr), size=8, align="center")
            rows = [(4, "上", self.nl, self.up, COUNT[0] + 0.6), (20, "下", self.nr, self.lo, COUNT[0] + 1.1)]
            for y, w, n, tri, t0 in rows:
                if t < t0:
                    continue
                p = ease_out_back(span(t, t0, t0 + 0.25))
                g.text(64, y, f"{w}{cn_num(n)}")
                draw_trigram(g, 96, y + 2, tri, w=max(6, int(10 * min(p, 1.1))), h=2, step=3)
                g.text(110, y, tri)
            if t > COUNT[1] - 0.4:
                g.text(64, 38, f"共{cn_num(self.total)}画")
                if t > COUNT[1] - 0.15:
                    g.text(64, 52, f"{cn_num(self.mv)}爻动")
        # 点阵：字 → 分开 → 上卦/下卦
        if t < CUT[0]:
            if t >= WRITE[0]:
                rows = int(span(t, *WRITE) * 8 + 0.999)
                g.mx[:rows] = self.mx[:rows]
        elif t < COUNT[0] + 0.6:
            c = int(round(8 * self.cut))
            s = 1 if t > CUT[0] + 0.3 else 0
            for x in range(8):
                nx = x - s if x < c else x + s
                if 0 <= nx < 8:
                    g.mx[:, nx] = self.mx[:, x]
        elif t < COUNT[0] + 1.1:
            mx_trigram(g, self.up)
        else:
            mx_trigram(g, self.lo)
        g.mx_level = 4 if CUT[0] + 0.25 < t < CUT[0] + 0.35 else 1
