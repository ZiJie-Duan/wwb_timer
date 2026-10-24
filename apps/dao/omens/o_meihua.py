"""梅花易数·观梅占。

邵雍观梅，见二雀争枝坠地，以年月日时起卦。《梅花易数·卷一》“年月日时起例”：
年月日为上卦，年月日加时总数为下卦，又以年月日时总数取爻；
年以地支数（子一……亥十二），时以时支数，以八除之余数作卦（先天数：乾一兑二离三震四巽五坎六艮七坤八），
以六除之余数作动爻。
本作取上位机本地时间；月、日用公历数代替农历（没有农历历法表）。
"""
from __future__ import annotations

import math
import time

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import DIZHI, TIANGAN, cn_num, shichen
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite, text_width
from ..engine.scene import Omen, register
from ..engine.symbols import draw_trigram, mx_trigram
from .o_common import REVEAL, hexa, lines_of, reveal
from .o_data import NUM_TRIGRAM

SPARROW = Sprite("""
     ##
    #.###
##  ###
 #######
  ######
   ####
   #  #
""").scale(2)
BRANCH = [(128, 46), (104, 37), (80, 33), (56, 26), (30, 21), (4, 10)]
TWIGS = [[(104, 37), (96, 48), (90, 55)], [(80, 33), (86, 21), (84, 13)], [(56, 26), (47, 37)],
         [(30, 21), (23, 31)], [(56, 26), (60, 13)], [(104, 37), (114, 26)]]
BLOSSOMS = [(6, 10), (24, 32), (18, 16), (47, 38), (60, 12), (84, 12), (88, 23), (90, 54), (114, 25), (100, 46),
            (122, 43), (38, 22)]
SEG = ((56, 26), (80, 33))  # 二雀所立的一段枝


def blossom(g: Gfx, cx: float, cy: float, s: float):
    if s <= 0:
        return
    r = 2.6 * s
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        g.d.ellipse((px - 1.4 * s, py - 1.4 * s, px + 1.4 * s, py + 1.4 * s), fill=1)
    if s > 0.7:
        g.px(cx, cy, 0)


def polyline_part(g: Gfx, pts, p: float, width: int = 1):
    """按长度比例画出折线的前 p 部分"""
    segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    total = sum(segs)
    left = total * clamp(p)
    for (a, b), L in zip(zip(pts, pts[1:]), segs):
        if left <= 0:
            break
        k = min(1.0, left / L)
        g.d.line((a[0], a[1], lerp(a[0], b[0], k), lerp(a[1], b[1], k)), fill=1, width=width)
        left -= L


@register
class MeihuaOmen(Omen):
    id = "o.meihua"
    name = "观梅占"
    desc = "梅枝开花，二雀争枝坠地；以此刻年月日时起数，八除定上下卦、六除定动爻"
    T = {"play": 6.0 + REVEAL}

    def setup(self):
        lt = time.localtime()
        y, self.mon, self.day, hour = lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour
        self.year_name = TIANGAN[(y - 4) % 10] + DIZHI[(y - 4) % 12]
        self.yn = (y - 4) % 12 + 1
        self.sc = shichen(hour)
        self.hn = DIZHI.index(self.sc[0]) + 1
        self.s1 = self.yn + self.mon + self.day
        self.s2 = self.s1 + self.hn
        self.up = NUM_TRIGRAM[self.s1 % 8 or 8]
        self.lo = NUM_TRIGRAM[self.s2 % 8 or 8]
        self.mv = self.s2 % 6 or 6
        self.lines = lines_of(self.up, self.lo, self.mv)

    def branch(self, g: Gfx, t: float, dx: float = 0.0):
        grow = ease_out(span(t, 0, 0.9))
        pts = [(x + dx, y) for x, y in BRANCH]
        polyline_part(g, pts, grow, width=2)
        for j, tw in enumerate(TWIGS):
            polyline_part(g, [(x + dx, y) for x, y in tw], ease_out(span(t, 0.4 + j * 0.12, 1.0 + j * 0.12)))
        for j, (bx, by) in enumerate(BLOSSOMS):
            s = ease_out_back(span(t, 0.6 + j * 0.07, 0.95 + j * 0.07))
            blossom(g, bx + dx, by, s)

    def sparrows(self, g: Gfx, t: float):
        if t < 0.9 or t > 3.4:
            return
        # 二雀立于枝上（106,33 ~ 116,47 之间），相向跳斗 → 1.7s 扭打坠地 → 2.6s 惊飞
        for j in range(2):
            base = -0.05 + j * 1.0
            bx = lerp(SEG[0][0], SEG[1][0], base)
            by = lerp(SEG[0][1], SEG[1][1], base)
            if t < 1.8:
                fight = span(t, 1.15, 1.8)
                hop = abs(math.sin(t * 14 + j)) * 3 * (fight > 0)
                x = bx + (1 - 2 * j) * fight * 6
                y = by - hop
                spr = SPARROW if j == 0 else SPARROW.flip()
                if fight > 0 and int(t * 16 + j) % 2:  # 扑翅
                    g.d.line((x, y - 6, x + (2 - 4 * j), y - 14), fill=1, width=2)
                g.blit(spr, x - 6, y - 11)
            elif t < 2.25:
                p = ease_in(span(t, 1.8, 2.25))
                x = bx + (1 - 2 * j) * 6 + math.sin(t * 30 + j) * 2
                y = lerp(by, 58, p)
                g.blit(SPARROW.flipv() if int(t * 20 + j) % 2 else SPARROW, x - 6, y - 11)
            else:
                p = ease_in(span(t, 2.3, 2.9))
                x = bx + (1 - 2 * j) * 6 + p * (40 if j else -30)
                y = 58 - p * 60 - (abs(math.sin(t * 10 + j)) * 2 if t < 2.6 else 0)
                if p > 0 and int(t * 18 + j) % 2:
                    g.d.line((x - 7, y - 8, x, y - 3), fill=1, width=2)
                    g.d.line((x + 7, y - 8, x, y - 3), fill=1, width=2)
                    g.d.ellipse((x - 2, y - 4, x + 2, y), fill=1)
                else:
                    g.blit(SPARROW if j == 0 else SPARROW.flip(), x - 6, y - 11)
        # 坠地时惊落的花瓣
        if t > 1.8:
            for k in range(8):
                p = (t - 1.8) * (0.6 + rand(k, 3) * 0.5)
                if p > 1.2:
                    continue
                x = 54 + rand(k, 4) * 34 + math.sin(t * 4 + k) * 3
                y = 14 + rand(k, 5) * 20 + p * 44
                if y < 63:
                    g.px(x, y)

    def calc(self, g: Gfx, t: float):
        """左侧算式：干支时辰、月日 → 上卦 → 下卦 → 动爻"""
        typewriter(g, 2, 2, f"{self.year_name}年 {self.sc}", t - 2.5, cps=14)
        typewriter(g, 2, 16, f"{self.mon}月{self.day}日", t - 2.9, cps=14)
        rows = [(31, 3.3, f"{self.yn}+{self.mon}+{self.day}={self.s1}", f"÷8余{self.s1 % 8}", self.up),
                (43, 4.1, f"+{self.hn}={self.s2}", f"÷8余{self.s2 % 8}", self.lo)]
        for y, t0, a, b, tri in rows:
            if t < t0:
                continue
            k = t - t0
            g.text(18, y + 1, a, size=8)
            if k > 0.35:
                g.text(20 + text_width(a, 8), y + 1, b, size=8)
            if k > 0.65:
                p = ease_out_back(span(k, 0.65, 0.9))
                draw_trigram(g, 2, y, tri, w=12, h=2, step=3)
                g.text(lerp(124, 102, p), y - 1, f"{tri}")
                g.text(118, y + 1, "上" if y < 40 else "下", size=8)
        if t > 4.9:
            k = t - 4.9
            g.text(18, 56, f"{self.s2}÷6余{self.s2 % 6}", size=8)
            if k > 0.35:
                g.text(64, 56, f"{cn_num(self.mv)}爻动", size=8)

    def play(self, g: Gfx, t: float):
        T = self.T["play"]
        R0 = T - REVEAL
        if t >= R0:
            k = t - R0
            blossom(g, 112 + ease_in(span(k, 0, 0.3)) * 30, 9, 1.6)
            hexa(g, self.lines, clamp(k / 0.45) * 6)
            reveal(g, self.lines, k, show_hexa=False)
            return
        if t < 2.9:
            self.branch(g, t)
            self.sparrows(g, t)
            if 1.8 < t < 2.5:
                g.d.line((40, 62, 100, 62), fill=1)
            if t > 2.4:
                g.fade(1 - span(t, 2.4, 2.9))
        else:
            blossom(g, 112, 9, ease_out_back(span(t, 2.9, 3.2)) * 1.6)
            self.calc(g, t)
        # 点阵：一朵梅花 → 上卦 → 下卦
        if t < 3.3 + 0.65:
            s = ease_out_back(span(t, 0.3, 0.8))
            if s > 0.3:
                for x, y in ((3, 1), (4, 1), (1, 3), (6, 3), (2, 6), (5, 6), (3, 0), (4, 0), (0, 3), (7, 3),
                             (1, 4), (6, 4), (1, 6), (6, 6), (2, 7), (5, 7)):
                    g.mx_set(x, y)
                g.mx[3:5, 3:5] = 1.8 < t < 2.3
        elif t < 4.1 + 0.65:
            mx_trigram(g, self.up)
        else:
            mx_trigram(g, self.lo)
            if t > 4.9 and int(t * 6) % 2:
                g.mx[0, :] = True
        g.mx_level = 3 if 1.8 < t < 1.95 else 1
