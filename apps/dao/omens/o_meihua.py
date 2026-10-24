"""梅花易数·观梅占。

邵雍观梅，见二雀争枝坠地，以年月日时起卦。《梅花易数·卷一》“年月日时起例”：
年月日为上卦，年月日加时总数为下卦，又以年月日时总数取爻；
年以地支数（子一……亥十二），时以时支数，以八除之余数作卦（先天数：乾一兑二离三震四巽五坎六艮七坤八），
以六除之余数作动爻。本作取上位机本地时间；月、日用公历数代替农历（没有农历历法表）。

画面：老梅横枝，花开点点、花瓣飘落；小道士坐在树下赏梅。两只麻雀飞来落在枝上，相向跳斗、扑翅互啄，
扭作一团坠地（花瓣震落、尘起、屏幕一震），小道士吓得一蹦，麻雀惊飞。
小道士剑指一掐：左上写出“丙午年 子时”与算式，再写“上乾 下兑”，然后揭晓。
"""
from __future__ import annotations

import math
import time

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.cn import DIZHI, TIANGAN, shichen
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import draw_trigram, mx_trigram
from .o_common import FLOOR, REVEAL, Base, blit_center, floor, rotated, star4
from .o_data import NUM_TRIGRAM

DAO_X = 20
FIGHT = (1.2, 2.3)
FALL = (2.3, 2.75)
FLEE = (3.0, 3.6)
CALC1, CALC2 = 3.4, 4.5
R0 = 5.7
PERCH = (68, 82)      # 两雀落脚处（枝上）

def _sparrow(wing: str):
    """麻雀 16×13（朝右）：圆头、短喙、黑眼、背部网点、白肚、短尾；wing = fold 收翅 / up 上扬 / down 下扑"""
    p = Part(16, 13)
    oy = 3
    p.shape("polygon", [(0, oy + 2), (4, oy + 4), (4, oy + 6), (0, oy + 5)], fill=1)   # 尾
    p.shape("ellipse", (2, oy + 2, 12, oy + 8), fill=1)                                 # 身
    p.shape("ellipse", (8, oy - 1, 14, oy + 4), fill=1)                                 # 头
    p.shape("polygon", [(14, oy + 1), (15, oy + 2), (14, oy + 3)], fill=1)               # 喙
    p.px(14, oy + 2, 0)
    p.px(11, oy + 1, 0)                                                                 # 眼
    p.d.line((9, oy + 3, 12, oy + 4), fill=0)                                           # 颊纹
    p.dither([(3, oy + 2), (10, oy + 2), (10, oy + 5), (3, oy + 5)], 0.5, 0)           # 背羽
    if wing == "fold":
        p.d.arc((3, oy + 2, 11, oy + 7), 200, 340, fill=0)
    elif wing == "up":
        p.shape("polygon", [(4, oy + 3), (9, oy + 3), (6, oy - 3), (3, oy - 3)], fill=1)
        p.d.line((5, oy - 2, 7, oy + 2), fill=0)
    else:
        p.shape("polygon", [(4, oy + 4), (9, oy + 4), (7, oy + 9), (4, oy + 9)], fill=1)
        p.d.line((5, oy + 5, 6, oy + 8), fill=0)
    p.px(6, oy + 9), p.px(6, oy + 10), p.px(9, oy + 9), p.px(9, oy + 10)                 # 脚
    return p.sprite()


SPARROW = [_sparrow("fold"), _sparrow("up"), _sparrow("down")]  # 立、翅上扬、翅下扑


def _blossom():
    p = Part(7, 7)
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        x, y = 3 + math.cos(a) * 2.2, 3 + math.sin(a) * 2.2
        p.shape("rectangle", (round(x) - 1 if x < 3 else round(x), round(y) - 1 if y < 3 else round(y),
                              round(x) if x < 3 else round(x) + 1, round(y) if y < 3 else round(y) + 1), fill=1)
    p.shape("rectangle", (2, 2, 4, 4), fill=1)
    p.px(3, 3, 0)
    return p.sprite()


def _bud():
    p = Part(3, 3)
    p.shape("ellipse", (0, 0, 2, 2), fill=1)
    return p.sprite()


SPR = {}

# 树：主干（右）+ 一根横枝伸向左上；花的位置
BRANCH = [(116, 46), (104, 34), (92, 28), (80, 27), (68, 26), (60, 20), (56, 14)]
TWIGS = [[(92, 28), (96, 16), (102, 9)], [(104, 34), (114, 24), (124, 20)], [(60, 20), (57, 30)],
         [(80, 27), (84, 36)]]
FLOWERS = [(56, 13), (57, 31), (96, 16), (102, 8), (114, 24), (124, 19), (84, 37), (92, 27), (108, 31)]
BUDS = [(62, 22), (99, 12), (110, 28), (120, 22), (88, 33)]


def spr(name):
    if not SPR:
        SPR.update(blossom=_blossom(), bud=_bud())
    return SPR[name]


def tree(g: Gfx, t: float, shake: float = 0.0):
    """老梅：虬曲的主干（树皮纹、背光网点）+ 横枝 + 花与花苞（随风微颤）"""
    g.d.polygon([(110, FLOOR), (124, FLOOR), (121, 50), (122, 40), (116, 32), (108, 34), (113, 44)], fill=1)
    g.d.line((116, 38, 118, 50), fill=0)
    g.d.line((119, 44, 120, 54), fill=0)
    pix.checker(g, (118, 34, 125, FLOOR), 0.5, 0)
    g.d.line((106, FLOOR, 128, FLOOR), fill=1)
    sx = math.sin(t * 25) * shake
    pts = [(x + sx * (1 - (x - 56) / 60), y) for x, y in BRANCH]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        w = 3 if x0 > 90 else 2
        g.d.line((x0, y0, x1, y1), fill=1, width=w)
    for tw in TWIGS:
        q = [(x + sx * 0.5, y) for x, y in tw]
        for (x0, y0), (x1, y1) in zip(q, q[1:]):
            g.d.line((x0, y0, x1, y1), fill=1)
    for j, (x, y) in enumerate(BUDS):
        pix.blit(g, spr("bud"), x - 1 + sx * 0.5, y - 1)
    for j, (x, y) in enumerate(FLOWERS):
        wob = 1 if (t * 1.3 + j * 0.37) % 2 < 0.15 else 0
        pix.blit(g, spr("blossom"), x - 3 + sx * 0.6, y - 3 - wob)


@register
class MeihuaOmen(Base):
    id = "o.meihua"
    name = "观梅占"
    desc = "老梅花开，小道士树下赏梅；二雀争枝扭打坠地惊飞，小道士掐指以年月日时起数，八除定卦、六除定爻"
    T = {"play": R0 + REVEAL}

    def init(self):
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
        from .o_common import lines_of
        self.lines = lines_of(self.up, self.lo, self.mv)
        self.petals = []  # 飘落的花瓣 [x, y, vx, vy, age]

    def petal_rain(self, g: Gfx, t: float, rate: float):
        r = self.rng
        if r.random() < rate * self.dt:
            fx, fy = FLOWERS[r.randrange(len(FLOWERS))]
            self.petals.append([fx, fy, -4 - r.random() * 6, 6 + r.random() * 6, 0.0])
        keep = []
        for p in self.petals:
            p[4] += self.dt
            p[0] += (p[2] + math.sin(p[4] * 5 + p[1]) * 6) * self.dt
            p[1] += p[3] * self.dt
            if p[1] < FLOOR - 1 and p[4] < 6:
                keep.append(p)
                x, y = int(p[0]), int(p[1])
                g.px(x, y)
                if int(p[4] * 6) % 2 == 0:
                    g.px(x + 1, y)
                else:
                    g.px(x, y + 1)
        self.petals = keep

    def bird(self, g: Gfx, x, y, frame, flip=False, deg=0.0):
        s = SPARROW[frame]
        if flip:
            s = pix.flipped(s)
        if deg:
            s = rotated(s, deg, 30)
        blit_center(g, s, x, y)

    def birds(self, g: Gfx, t: float):
        if t < 0.5 or t > FLEE[1]:
            return
        for j in range(2):
            px, py = PERCH[j], 21 if j == 0 else 22
            flip = j == 1  # 左雀朝右、右雀朝左
            if t < 1.1:  # 从右上飞来
                q = ease_out(span(t, 0.5 + j * 0.12, 1.1))
                x = lerp(140 + j * 10, px, q)
                y = lerp(-6, py, q) - math.sin(q * math.pi) * 6
                self.bird(g, x, y, 1 + int(t * 14) % 2, flip=True)
            elif t < FIGHT[0]:
                self.bird(g, px, py, 0, flip)
            elif t < FIGHT[1]:  # 跳斗：相向跳、扑翅、互啄
                k = t - FIGHT[0]
                ph = (k * 5 + j * 0.5) % 1
                hop = math.sin(ph * math.pi) * 4 if ph < 0.5 else 0
                close = ease_in_out(span(t, FIGHT[0], FIGHT[1] - 0.2)) * 3
                x = px + (close if j == 0 else -close)
                self.bird(g, x, py - hop, 1 + int(k * 16) % 2 if hop else 0, flip)
                if int(k * 8) % 4 == j * 2:  # 互啄的火星与羽毛
                    star4(g, (PERCH[0] + PERCH[1]) / 2, py - 9, 2)
                if self.hit(t, FIGHT[0] + 0.5 + j * 0.2):
                    self.puffs.emit((PERCH[0] + PERCH[1]) / 2, py - 2, vy=-3, life=0.4, rmax=1.5, spread=4)
            elif t < FALL[1]:  # 扭作一团坠地（翻滚）
                q = span(t, FALL[0], FALL[1])
                x = lerp((PERCH[0] + PERCH[1]) / 2 + (-5 if j == 0 else 5), 72 + j * 14, q)
                y = lerp(py, FLOOR - 6, ease_in(q))
                self.bird(g, x, y, 1, flip, deg=q * 540 * (1 if j else -1))
            elif t < FLEE[0]:  # 地上愣住
                self.bird(g, 72 + j * 14, FLOOR - 6, 0, not flip)
            else:  # 惊飞
                q = ease_in(span(t, FLEE[0] + j * 0.1, FLEE[1]))
                x = lerp(72 + j * 14, 140 + j * 6, q)
                y = lerp(FLOOR - 6, -10 - j * 6, q)
                self.bird(g, x, y, 1 + int(t * 16) % 2, flip=False)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        k_fall = span(t, FALL[1], FALL[1] + 0.4)
        if t < R0:
            tree(g, t, shake=1.5 if FIGHT[0] < t < FALL[1] else 0)
        floor(g, "earth")
        # ---------------- 小道士：坐着赏梅 → 一蹦 → 掐指起数
        if t < FALL[1]:
            daoshi(g, DAO_X, FLOOR, "sit", t, face="wow" if t > FIGHT[0] else "normal")
        elif t < CALC1:
            hop = math.sin(span(t, FALL[1], FALL[1] + 0.3) * math.pi) * 5
            daoshi(g, DAO_X, FLOOR - hop, "idle", t, face="wow")
        elif t < R0:
            daoshi(g, DAO_X, FLOOR, "point", t)
        else:
            k = t - R0
            daoshi(g, DAO_X, FLOOR, "raise" if 0.2 < k < 0.8 else "gongshou", t, face="happy")
        self.birds(g, t)
        if self.hit(t, FALL[1]):
            for x in (72, 86):
                self.impact(g, x, FLOOR - 1, 1.0)
            pix.shake(g, t, 2)
        elif FALL[1] < t < FALL[1] + 0.12:
            pix.shake(g, t, 1)
        rate = 1.2 if t < FIGHT[0] else 14 if t < FALL[1] + 0.3 else 2
        if t < R0:
            self.petal_rain(g, t, rate)
        self.particles(g)
        # ---------------- 起数（左上角）
        if CALC1 <= t < R0:
            if t < CALC2:
                s = f"{self.year_name}年 {self.sc}"
                m = int(min(1, (t - CALC1) * 14 / len(s)) * len(s))
                self.say(2, 2, s[:m])
                if t > CALC1 + 0.45:
                    expr = f"{self.yn}+{self.mon}+{self.day}+{self.hn}"
                    self.say(2, 16, expr[:int((t - CALC1 - 0.45) * 30)], size=8)
            else:
                k = t - CALC2
                for row, (lab, tri) in enumerate((("上", self.up), ("下", self.lo))):
                    if k > row * 0.35:
                        x = 2 + row * 32
                        self.say(x, 2, lab + tri)
                        if k > row * 0.35 + 0.15:
                            draw_trigram(g, x + 3, 16, tri, w=18, h=2, step=3)
            if self.hit(t, CALC2):
                self.sparks.burst(30, 10, 10, 30, life=0.4, gravity=20)
        # ---------------- 点阵
        if t < R0:
            if t < CALC2:  # 一朵梅花（坠地时花心闪）
                rows = ["00100100", "01111110", "11111111", "01100110", "11111111", "01111110", "00100100", "00000000"]
                for y, row in enumerate(rows):
                    for x, c in enumerate(row):
                        g.mx[y, x] = c == "1"
                g.mx[3, 3] = g.mx[3, 4] = FALL[1] <= t < FALL[1] + 0.3 and int(t * 12) % 2 == 0
                g.mx_level = 6 if FALL[1] <= t < FALL[1] + 0.15 else 1
            else:
                mx_trigram(g, self.up if (t - CALC2) % 1.2 < 0.6 else self.lo)
        else:
            self.reveal(g, t, R0)
        self.flush(g)
