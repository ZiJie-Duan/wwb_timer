"""测字（一字占）。

《梅花易数·卷一》一字占：“如楷书，则取其字画……居左者看几数，取为上卦；居右者看几数，取为下卦。
又以一字之阴阳，全画取爻。”本作以字的左右两部分笔画数（简体）各除八取余定上下卦（先天数），
全字笔画数除六取余为动爻。

画面：一幅立轴从上往下展开；小道士抡起一支大笔，在纸上写下一个大字（笔尖跟着走，墨点飞溅）；
换剑指一划，一道剑光自上而下劈开，“锵”地一震，字分成左右两半；两半下面各弹出笔画数，
右边写出“上震”“下离”与卦象；揭晓时立轴卷起。
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_back, lerp, noise, span
from ..engine.chars import daoshi, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, _FONT_FILES, font, text_image
from ..engine.scene import register
from ..engine.symbols import draw_trigram, mx_trigram
from .o_common import FLOOR, REVEAL, Base, arm, floor, lines_of
from .o_data import NUM_TRIGRAM

# 字：(左笔画, 右笔画, 左右分界在字宽的比例)
CHARS = {
    "明": (4, 4, 0.42), "林": (4, 4, 0.5), "好": (3, 3, 0.45), "和": (5, 3, 0.55), "信": (2, 7, 0.3),
    "福": (4, 9, 0.4), "禄": (4, 8, 0.4), "静": (8, 6, 0.5), "清": (3, 8, 0.3), "神": (4, 5, 0.42),
    "仙": (2, 3, 0.3), "时": (4, 3, 0.42), "炉": (4, 4, 0.42), "松": (4, 4, 0.42), "卦": (6, 2, 0.6),
    "悟": (3, 7, 0.3), "根": (4, 6, 0.42), "缘": (3, 9, 0.33), "证": (2, 5, 0.3), "情": (3, 8, 0.3),
}
SC = 3
DAO_X = 15
PX0, PX1 = 42, 88            # 立轴左右
PY0, PY1 = 3, 57             # 立轴上下
GH = 11 * SC + 1             # 字形实际高度
GX, GY = 47, 7               # 字左上
UNROLL = (0.0, 0.45)
WRITE = (0.55, 2.15)
CUT = 2.5
SEP = (2.55, 2.8)
COUNT = (2.9, 3.4)
TRI = (3.7, 4.2)
R0 = 4.9


def mx_char(ch: str) -> np.ndarray:
    img = Image.new("1", (8, 8))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    d.text((0, -_FONT_FILES[8][1]), ch, font=font(8), fill=1)
    return np.array(img, dtype=bool)


def scroll(g: Gfx, p: float):
    """立轴：天杆（两头轴头）、宣纸（左右细边）、地杆，p = 展开程度"""
    y1 = lerp(PY0 + 3, PY1, ease_out(p))
    g.d.rectangle((PX0, PY0, PX1, y1), fill=0, outline=1)
    g.d.line((PX0 + 2, PY0 + 2, PX0 + 2, y1 - 2), fill=1)
    g.d.line((PX1 - 2, PY0 + 2, PX1 - 2, y1 - 2), fill=1)
    for y, h in ((PY0 - 2, 2), (y1, 2)):
        g.d.rectangle((PX0 - 3, y, PX1 + 3, y + h), fill=1)
        g.d.line((PX0 - 2, y + 1, PX1 + 2, y + 1), fill=0)
        for x in (PX0 - 5, PX1 + 4):
            g.d.rectangle((x, y - 1, x + 1, y + h + 1), fill=1)
    g.px((PX0 + PX1) // 2, PY0 - 3), g.d.line(((PX0 + PX1) // 2 - 4, PY0 - 3, (PX0 + PX1) // 2 + 4, PY0 - 3), fill=1)
    return y1


@register
class CeziOmen(Base):
    id = "o.cezi"
    name = "测字"
    desc = "立轴展开，小道士抡大笔写一个字；剑光一劈字分左右，数笔画：左为上卦、右为下卦，全画取动爻"
    T = {"play": R0 + REVEAL}

    def init(self):
        self.ch = self.rng.choice(sorted(CHARS))
        self.nl, self.nr, self.cut = CHARS[self.ch]
        self.total = self.nl + self.nr
        self.up = NUM_TRIGRAM[self.nl % 8 or 8]
        self.lo = NUM_TRIGRAM[self.nr % 8 or 8]
        self.mv = self.total % 6 or 6
        self.lines = lines_of(self.up, self.lo, self.mv)
        self.mx = mx_char(self.ch)
        self.glyph = text_image(self.ch, 12, SC)

    def char(self, g: Gfx, p: float, sep: float):
        """写到 p（自上而下），sep = 左右分开的距离"""
        gl = self.glyph
        w, h = gl.size
        cut_y = int(GH * p) if p < 1 else h
        if cut_y <= 0:
            return
        img = gl.crop((0, 0, w, cut_y))
        if sep <= 0:
            g.img.paste(1, (GX, GY), img)
            return
        c = int(w * self.cut)
        s = int(round(sep))
        g.img.paste(1, (GX - s, GY), img.crop((0, 0, c, cut_y)))
        g.img.paste(1, (GX + c + s, GY), img.crop((c, 0, w, cut_y)))

    def tip(self, p: float):
        """笔尖：自上而下，左右游走"""
        w = self.glyph.size[0]
        return GX + w * (0.2 + 0.6 * noise(p * 14, 3)), GY + GH * p

    def brush(self, g: Gfx, hand, tip, t: float):
        """大笔：笔杆从手里斜伸到纸上，笔头一撮（狼毫）"""
        hx, hy = hand
        tx, ty = tip
        top = (tx + 5, ty - 8)
        g.d.line((hx, hy, top[0], top[1]), fill=1, width=2)
        g.d.rectangle((top[0] - 1, top[1] - 2, top[0] + 2, top[1] + 1), fill=1)   # 笔斗
        g.d.polygon([(top[0] - 1, top[1] + 1), (top[0] + 2, top[1] + 1), (tx, ty)], fill=1)  # 笔头
        g.px(top[0] + 1, top[1] + 2, 0)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        floor(g, "tile")
        p_un = span(t, *UNROLL)
        sep = ease_out_back(span(t, *SEP)) * 4
        if t < R0 + 0.3:  # 揭晓时立轴卷起
            roll = ease_in(span(t, R0, R0 + 0.3))
            if roll < 1:
                y1 = scroll(g, p_un * (1 - roll))
                if roll == 0 and t >= WRITE[0]:
                    self.char(g, span(t, *WRITE), sep)
        # ---------------- 小道士
        if t >= R0:
            k = t - R0
            daoshi(g, DAO_X, FLOOR, "raise" if 0.2 < k < 0.8 else "gongshou", t, face="happy")
        elif t < WRITE[0]:
            daoshi(g, DAO_X, FLOOR, "gongshou" if t < 0.3 else "idle", t)
        elif t < WRITE[1] + 0.1:
            p = span(t, *WRITE)
            a, at = arm("toss")
            hand = figure(g, DAO_X, FLOOR, t, arm=a, arm_at=at, bob=False)["hand"]
            tp = self.tip(p)
            self.brush(g, hand, tp, t)
            if int(t * 30) % 4 == 0 and p < 1:  # 墨点飞溅
                self.sparks.burst(tp[0], tp[1], 1, 25, up=8, life=0.3, gravity=80)
        elif t < CUT + 0.4:
            daoshi(g, DAO_X, FLOOR, "point" if t > CUT - 0.2 else "idle", t, face="normal")
        else:
            daoshi(g, DAO_X, FLOOR, "idle", t, face="wow" if t < COUNT[1] else "happy")
        # ---------------- 剑光一劈
        cx = GX + self.glyph.size[0] * self.cut
        if CUT - 0.15 <= t < CUT + 0.25:
            q = ease_in(span(t, CUT - 0.15, CUT))
            y0 = PY0 + 2
            y = lerp(y0, PY1 - 2, q)
            g.d.line((cx, y0, cx, y), fill=1, width=1 if t < CUT else 3)
            if q < 1:
                g.d.polygon([(cx - 2, y - 6), (cx + 2, y - 6), (cx, y + 1)], fill=1)
        if self.hit(t, CUT):
            pix.flash(g)
            pix.shake(g, t, 2.5)
            for y in range(PY0 + 6, PY1, 8):
                self.sparks.burst(cx, y, 2, 30, life=0.4, gravity=30)
        elif CUT < t < CUT + 0.15:
            pix.shake(g, t, 1.5)
        self.particles(g)
        # ---------------- 数笔画、上下卦
        if COUNT[0] <= t < R0:
            w = self.glyph.size[0]
            lx = GX - sep + w * self.cut / 2
            rx = GX + sep + w * self.cut + w * (1 - self.cut) / 2
            self.pop(lx, 43, cn_num(self.nl), t - COUNT[0])
            self.pop(rx, 43, cn_num(self.nr), t - COUNT[0] - 0.3)
            if self.hit(t, COUNT[0]) or self.hit(t, COUNT[0] + 0.3):
                self.sparks.burst(lx if t < COUNT[0] + 0.2 else rx, 47, 6, 20, life=0.3, gravity=20)
        if TRI[0] <= t < R0:
            for row, (lab, tri, t0) in enumerate((("上", self.up, TRI[0]), ("下", self.lo, TRI[1]))):
                if t >= t0:
                    y = 4 + row * 27
                    self.say(95, y, lab + tri)
                    if t >= t0 + 0.12:
                        q = ease_out_back(span(t, t0 + 0.12, t0 + 0.35))
                        draw_trigram(g, 97, y + 14, tri, w=max(4, int(20 * min(q, 1.1))), h=2, step=3)
        # ---------------- 点阵：字逐行写出 → 左右分开 → 上卦 / 下卦
        if t < R0:
            if t < CUT:
                rows = int(span(t, *WRITE) * 8 + 0.999)
                g.mx[:rows] = self.mx[:rows]
            elif t < TRI[0]:
                c = int(round(8 * self.cut))
                s = 1 if t > SEP[0] else 0
                for x in range(8):
                    nx = x - s if x < c else x + s
                    if 0 <= nx < 8:
                        g.mx[:, nx] = self.mx[:, x]
            else:
                mx_trigram(g, self.up if t < TRI[1] else self.lo)
            g.mx_level = 7 if CUT <= t < CUT + 0.12 else 1
        else:
            self.reveal(g, t, R0)
        self.flush(g)
