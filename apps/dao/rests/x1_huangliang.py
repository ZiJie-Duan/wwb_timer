"""黄粱一梦：邯郸旅舍，卢生枕着吕翁给的青瓷枕睡去，梦里登第、出将、入相、封公、年逾八十；
梦泡一破，惊醒——灶上的黄粱还没蒸熟。躺下，又是一梦。

依据：唐·沈既济《枕中记》：“翁乃探囊中枕以授之，曰：‘子枕吾枕，当令子荣适如志。’”“时主人方蒸黍。”
“卢生欠伸而悟，见其身方偃于邸舍，吕翁坐其傍，主人蒸黍未熟，触类如故。”后世吕翁附会为吕洞宾。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.fx import flame, smoke_wisp, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Pen, backdrop, breathe, clip_ellipse, ev, iris, zzz

FLOOR = 58
COUCH = 47                 # 榻面
PILLOW = (6, COUCH - 7)    # 青瓷枕左上角
HEADP = (10, COUCH - 15)   # 头（左上角）
POT = (104, 33)            # 釜口中心
BUB = (16, 1, 80, 33)      # 梦泡
BC = ((BUB[0] + BUB[2]) / 2, (BUB[1] + BUB[3]) / 2)
VIG = 6.0                  # 每段梦
DREAM = 5 * VIG            # 一生
CYCLE = DREAM + 10.0       # 加上醒来、躺回、再入梦


def _bg():
    p = Pen()
    # 墙上的窗（直棂窗）
    p.rect((44, 18, 66, 32), fill=0)
    for x in range(47, 66, 4):
        p.line([(x, 19), (x, 31)])
    p.line([(44, 25), (66, 25)], 0)
    # 灶台（砖）
    p.rect((86, 36, 124, FLOOR), fill=0)
    for y in range(40, FLOOR, 4):
        p.line([(87, y), (123, y)])
        off = 0 if (y // 4) % 2 else 4
        for x in range(88 + off, 123, 8):
            p.line([(x, y - 3), (x, y - 1)])
    p.chord((96, 44, 112, 58), 180, 360, fill=0)  # 灶门（拱）
    p.rect((96, 51, 112, FLOOR - 1), fill=0, outline=None)
    p.line([(96, 51), (96, FLOOR)])
    p.line([(112, 51), (112, FLOOR)])
    # 釜
    p.chord((90, 26, 118, 44), 0, 180, fill=0.5)
    p.line([(91, 35), (117, 35)])
    p.rect((114, 0, 119, 36), fill=0.4)           # 烟囱
    # 地面
    p.line([(0, FLOOR), (128, FLOOR)])
    # 榻
    p.rect((2, COUCH, 66, COUCH + 3), fill=0.5)
    p.rect((4, COUCH + 4, 7, FLOOR - 1), fill=0)
    p.rect((61, COUCH + 4, 64, FLOOR - 1), fill=0)
    p.line([(8, COUCH + 6), (60, COUCH + 6)])
    return p.image()


def _pillow() -> Sprite:
    """青瓷枕：长方形瓷枕，两头有窍"""
    p = Pen(16, 8)
    p.poly([(0, 2), (2, 0), (15, 0), (15, 7), (0, 7)], fill=0.6)
    p.line([(2, 0), (2, 7)])
    p.ellipse((5, 2, 9, 5), fill=0)
    return p.sprite()


def _lying() -> Sprite:
    """仰卧：头在左，鼻子朝上，脚翘在右"""
    p = Pen(56, 16)
    y0 = 15
    p.poly([(12, 8), (20, 6), (34, 6), (44, 8), (52, 8), (54, 3), (56, 4), (56, y0), (12, y0)], fill=0.22)
    p.line([(30, 6), (30, y0)])                     # 腰带
    p.line([(32, 6), (32, y0)])
    p.poly([(16, 9), (28, 8), (30, 12), (16, 13)], fill=0)   # 手搭在肚子上
    p.ellipse((1, 4, 13, 15), fill=0)               # 头
    p.poly([(2, 5), (6, 0), (11, 1), (13, 6), (8, 5)], fill=1)   # 幞头
    p.line([(7, 9), (9, 9)])                         # 闭眼
    p.px(12, 8)                                      # 鼻
    return p.sprite()


def _sitting() -> Sprite:
    """坐起：上身竖起，腿还在榻上"""
    p = Pen(56, 30)
    y0 = 29
    p.poly([(10, 14), (20, 14), (24, 22), (50, 22), (54, 18), (56, 19), (56, y0), (8, y0)], fill=0.22)
    p.line([(26, 22), (26, y0)])
    p.poly([(18, 15), (24, 17), (30, 24), (24, 26), (18, 21)], fill=0)      # 胳膊
    p.ellipse((9, 2, 21, 14), fill=0)                                     # 头
    p.poly([(9, 5), (12, -1), (20, 0), (22, 5)], fill=1)                  # 幞头
    p.rect((16, 6, 17, 8), fill=1)                                        # 睁眼
    p.px(21, 9)
    p.ellipse((15, 10, 18, 12), fill=0)                                   # 张嘴
    return p.sprite()


_A = {}


def _assets():
    if not _A:
        _A.update(bg=_bg(), pillow=_pillow(), lie=_lying(), sit=_sitting())


# ---------------------------------------------------------------- 梦里的一生

def v_scroll(g: Gfx, u: float):
    """登第：金榜展开，“甲科”"""
    w = 4 + ease_out(span(u, 0.3, 1.6)) * 30
    x0, y0 = BC[0] - w / 2 - 11, BC[1] - 8
    g.d.rectangle((x0, y0, x0 + w, y0 + 13), fill=0, outline=1)
    g.d.rectangle((x0 - 2, y0 - 1, x0, y0 + 14), fill=1)
    g.d.rectangle((x0 + w, y0 - 1, x0 + w + 2, y0 + 14), fill=1)
    if w > 20:
        g.text(x0 + w / 2, y0 + 3, "甲科", size=8, align="center")
    return "登第"


def v_flag(g: Gfx, u: float):
    """出将：帅旗猎猎"""
    x0, y0 = BC[0] - 18, BC[1] - 11
    g.d.line((x0, y0, x0, y0 + 22), fill=1)
    g.d.polygon([(x0 - 1, y0 - 2), (x0 + 1, y0 - 4), (x0 + 2, y0 - 1)], fill=1)
    pts_top, pts_bot = [], []
    for i in range(9):
        x = x0 + 1 + i * 2.6
        dy = math.sin(u * 6 - i * 0.7) * 1.5 * (i / 8)
        pts_top.append((x, y0 + dy))
        pts_bot.append((x, y0 + 14 + dy))
    g.d.polygon(pts_top + pts_bot[::-1], fill=0, outline=1)
    g.text(x0 + 6 + math.sin(u * 6 - 3) * 0.7, y0 + 4, "将", size=8)
    return "出将"


def v_hat(g: Gfx, u: float):
    """入相：乌纱帽，两翅颤颤"""
    cx, cy = BC[0] - 6, BC[1] + 1
    bob = math.sin(u * 5) * 1.2
    g.d.chord((cx - 7, cy - 12, cx + 7, cy + 2), 180, 360, fill=1)
    g.d.rectangle((cx - 9, cy - 5, cx + 9, cy + 2), fill=1)
    g.d.line((cx - 9, cy - 1, cx + 9, cy - 1), fill=0)
    for s in (-1, 1):
        g.d.line((cx + s * 9, cy - 2, cx + s * 18, cy - 4 + bob * s), fill=1, width=2)
        g.d.ellipse((cx + s * 18 - 2, cy - 6 + bob * s, cx + s * 18 + 2, cy - 2 + bob * s), fill=1)
    return "入相"


def v_gold(g: Gfx, u: float):
    """封公：元宝一个个落下摞起"""
    spots = [(-12, 6), (0, 6), (-6, 0)]
    for i, (dx, dy) in enumerate(spots):
        k = ease_out_bounce(span(u, 0.3 + i * 0.6, 1.0 + i * 0.6))
        if k <= 0:
            continue
        x, y = BC[0] + dx - 6, lerp(BUB[1] + 2, BC[1] + dy - 2, k)
        g.d.ellipse((x - 3, y - 4, x + 3, y + 1), fill=1)
        g.d.polygon([(x - 7, y - 3), (x - 4, y), (x + 4, y), (x + 7, y - 3), (x + 5, y + 4), (x - 5, y + 4)],
                    fill=1)
        g.d.line((x - 4, y, x + 4, y), fill=0)
    return "封公"


def v_candle(g: Gfx, u: float, t: float):
    """年逾八十：蜡烛烧短"""
    h = lerp(16, 4, ease_in_out(span(u, 0.3, 5.5)))
    x, base = BC[0] - 6, BC[1] + 9
    g.d.rectangle((x - 3, base - h, x + 3, base), fill=0, outline=1)
    g.d.line((x - 6, base + 1, x + 6, base + 1), fill=1)
    g.d.line((x, base - h, x, base - h - 2), fill=1)
    flame(g, x, base - h - 2, 4, 7, t, 3)
    return "八十"


VIGNETTES = (v_scroll, v_flag, v_hat, v_gold, v_candle)


@register
class Huangliang(Rest):
    id = "x1.huangliang"
    name = "黄粱一梦"
    desc = "旅舍里卢生枕青瓷枕而眠，梦泡里一生荣华走马灯似的过；梦破惊醒，灶上黄粱犹未熟，躺下再梦"
    T = {"enter": 3.4, "exit": 1.3}

    def setup(self):
        _assets()
        self._ht = 0.0

    # ------------------------------------------------------------ 零件

    def stove(self, g: Gfx, t: float, lid: bool = True):
        flame(g, 104, FLOOR - 1, 9, 9, t, self.seed)
        flame(g, 100, FLOOR - 1, 5, 6, t + 3, self.seed + 1)
        jig = ev(t, 7.3, 0.6)              # 锅盖被蒸汽顶得一跳一跳
        dy = -1 if jig and int(jig[1] * 10) % 2 else 0
        g.d.chord((95, POT[1] - 5 + dy, 113, POT[1] + 3 + dy), 180, 360, fill=0, outline=1)
        g.d.rectangle((103, POT[1] - 7 + dy, 105, POT[1] - 5 + dy), fill=1)
        for i in range(2):
            smoke_wisp(g, 99 + i * 9, POT[1] - 5, 22, t, self.seed + i, sway=2.5, speed=5, drift=-6 + i * 4)

    def mx_pot(self, g: Gfx, t: float):
        g.mx_rows([0, 0, 0, 0x7E, 0xFF, 0x7E, 0x3C, 0])
        for i, col in enumerate((2, 5)):
            y = 2 - int((t * 2.5 + i * 0.7) % 3)
            g.mx_set(col + (int(t * 2 + i) % 2), y)

    def luo(self, g: Gfx, t: float, sit: bool = False):
        g.blit(_A["pillow"], *PILLOW)
        if sit:
            g.blit(_A["sit"], HEADP[0] - 2, COUCH - 30)
        else:
            g.blit(_A["lie"], HEADP[0] - 1, COUCH - 16 + (0 if breathe(t) > 0.5 else 0))
            if breathe(t) > 0.5:  # 吸气时肚子鼓一下
                g.d.line((HEADP[0] + 21, COUCH - 11, HEADP[0] + 33, COUCH - 11), fill=1)

    def bubble(self, g: Gfx, s: float, wob: float = 0.0, t: float = 0.0):
        """梦泡（s = 大小 0..1）及连到头上的三个小泡"""
        for i, (dx, dy, r) in enumerate(((16, -6, 1.5), (20, -11, 2.2), (25, -17, 3))):
            if s > i * 0.2:
                x, y = HEADP[0] + dx, HEADP[1] + dy + 4
                g.d.ellipse((x - r, y - r, x + r, y + r), outline=1, fill=0)
        if s <= 0.5:
            return None
        k = ease_out_back((s - 0.5) / 0.5)
        rx = (BUB[2] - BUB[0]) / 2 * k + math.sin(t * 9) * wob
        ry = (BUB[3] - BUB[1]) / 2 * k + math.cos(t * 11) * wob
        box = (BC[0] - rx, BC[1] - ry, BC[0] + rx, BC[1] + ry)
        g.d.ellipse(box, outline=1, fill=0)
        return box

    def dream(self, g: Gfx, u: float, t: float, wob: float = 0.0):
        box = self.bubble(g, 1.0, wob, t)
        i = min(int(u // VIG), len(VIGNETTES) - 1)
        v = u - i * VIG
        fn = VIGNETTES[i]
        cap = fn(g, v, t) if fn is v_candle else fn(g, v)
        a = span(v, 0.5, 1.2) * (1 - span(v, VIG - 0.5, VIG))
        if a > 0:
            g.text(BC[0] + 13, BC[1] - 4, cap[: max(1, int(len(cap) * a + 0.5))], size=8)
        clip_ellipse(g, (box[0] + 1, box[1] + 1, box[2] - 1, box[3] - 1))
        g.d.ellipse(box, outline=1)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        backdrop(g, _A["bg"])
        self.stove(g, t)
        self.mx_pot(g, t)
        if t < 1.3:  # 吕翁探囊取枕，递过来
            g.blit(_A["sit"], HEADP[0] - 2, COUCH - 30)
            k = ease_out(span(t, 0, 0.8))
            drop = ease_out_bounce(span(t, 0.8, 1.3))
            px, py = lerp(40, PILLOW[0], k), lerp(-10, PILLOW[1] - 14, k) + drop * 14
            g.blit(_A["pillow"], px, py)
            if t < 0.9:  # 吕翁递枕的手与袖
                hx, hy = px + 15, py + 3
                sl = [(hx + 3, hy - 4), (hx + 16, hy - 14), (hx + 90, hy - 60), (hx + 120, hy - 30), (hx + 6, hy + 5)]
                g.d.polygon(sl, fill=0)
                g.shade_poly(sl, 0.3)
                g.d.line((hx + 7, hy - 6, hx + 9, hy + 5), fill=1)
                g.d.ellipse((hx - 3, hy - 3, hx + 5, hy + 4), fill=0, outline=1)
        elif t < 1.9:
            self.luo(g, 0, sit=t < 1.5)
        else:
            self.luo(g, 0)
            s = span(t, 1.9, 3.3)
            if s >= 1:
                self.dream(g, 0.0, t)
            else:
                self.bubble(g, s)
            zzz(g, HEADP[0] + 12, HEADP[1] + 4, t - 1.9, self.seed, rise=10, drift=-8, s0=1, s1=3, on=0.0)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        backdrop(g, _A["bg"])
        self.stove(g, t)
        u = t % CYCLE
        n = int(t // CYCLE)
        if u < DREAM:                         # 梦
            self.luo(g, t)
            self.dream(g, u, t, wob=0.6 if u > DREAM - 1.5 else 0.0)
            self.mx_pot(g, t)
            if u > DREAM - 2.0:              # 将醒：梦泡发抖
                g.mx_level = 2
        elif u < DREAM + 0.6:                # 梦泡破了
            self.luo(g, t)
            k = (u - DREAM) / 0.6
            for j in range(16):
                a = j / 16 * 2 * math.pi + n
                r = 8 + k * 26 + rand(j, n) * 6
                g.px(BC[0] + math.cos(a) * r * 1.2, BC[1] + math.sin(a) * r * 0.6)
            g.mx_rows([0x18, 0x18, 0x18, 0x18, 0x18, 0, 0x18, 0x18])
            g.mx_level = 5
        elif u < DREAM + 7.0:                # 惊坐起：主人蒸黍未熟
            v = u - DREAM - 0.6
            self.luo(g, t, sit=True)
            if v < 1.2:
                g.text(HEADP[0] + 22, HEADP[1] - 18, "!", size=12)
            if v > 0.8:
                g.d.rectangle((38, 1, 113, 15), fill=0)
                typewriter(g, 40, 3, "主人蒸黍未熟", v - 0.8, cps=5)
            g.mx_rows([0x18, 0x18, 0x18, 0x18, 0x18, 0, 0x18, 0x18] if v < 1.2 else [0] * 8)
            if v >= 1.2:
                self.mx_pot(g, t)
        else:                                # 躺回去，梦泡再起
            v = u - DREAM - 7.0
            self.luo(g, t, sit=v < 0.5)
            s = span(v, 0.6, 2.8)
            if s >= 1:
                self.dream(g, 0.0, t)
            else:
                self.bubble(g, s)
            self.mx_pot(g, t)

    def exit(self, g: Gfx, t: float):
        """醒来：梦泡破掉，坐起，画面收拢到卢生身上"""
        h = self._ht
        backdrop(g, _A["bg"])
        self.stove(g, h + t)
        u = h % CYCLE
        dreaming = u < DREAM or u > DREAM + 7.5
        if dreaming and t < 0.35:
            self.luo(g, h)
            k = t / 0.35
            for j in range(16):
                a = j / 16 * 2 * math.pi
                r = 8 + k * 26
                g.px(BC[0] + math.cos(a) * r * 1.2, BC[1] + math.sin(a) * r * 0.6)
        else:
            self.luo(g, h, sit=True)
            g.text(HEADP[0] + 22, HEADP[1] - 18, "!", size=12)
        g.mx_rows([0x18, 0x18, 0x18, 0x18, 0x18, 0, 0x18, 0x18])
        iris(g, HEADP[0] + 10, COUCH - 20, lerp(120, 0, ease_in_out(span(t, 0.35, self.T["exit"] - 0.05))), 0.8)
