"""金钱课（三钱法 / 火珠林法）。

小道士双手合拢摇响三枚方孔钱，一扬手抛起；铜钱在空中翻转（正面→侧棱→背面），落地弹跳、火星迸溅、震屏。
看“背”“字”：一背为单（少阳 7）、两背为拆（少阴 8）、三背为重（老阳 9）、三字为交（老阴 6）。
六掷自下而上成卦，记在左上角卦牌；最后一掷抛得最高。揭晓时卦象砸下。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, lerp, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import mx_hexagram
from .o_common import FLOOR, REVEAL, YAO_NAME, Base, arm, floor, speed_lines, tally

COIN_X = (65, 84, 103)          # 落点（钱心）
CALL = {6: "交", 7: "单", 8: "拆", 9: "重"}
T0 = 0.45
DUR = (1.05, 0.74, 0.74, 0.74, 0.74, 1.15)
STARTS = [T0 + sum(DUR[:i]) for i in range(6)]
END = STARTS[-1] + DUR[-1]
DAO_X = 20


def REL(i):   # 出手（相对本掷开始）
    return DUR[i] * (0.4 if i == 5 else 0.36)


def AIR(i):
    return DUR[i] * (0.45 if i == 5 else 0.42)


def LAND(i):  # 三枚都落地
    return REL(i) + AIR(i) + 0.06


R0 = END + 0.15
LABELS = [(STARTS[j] + LAND(j) + 0.08, STARTS[j + 1] + REL(j + 1) if j < 5 else R0) for j in range(6)]


# ---------------------------------------------------------------- 方孔钱（13×13，逐像素）

def _coin(back: bool):
    p = Part(13, 13)
    p.shape("ellipse", (0, 0, 12, 12), fill=1)
    p.d.ellipse((1, 1, 11, 11), outline=0)          # 外郭内侧的阴线
    p.d.rectangle((5, 5, 7, 7), fill=0)             # 方孔
    if back:  # 背：钱肉网点（暗），方孔四周内郭亮，左右两个满文似的勾
        p.dither((2, 2, 10, 10), 0.5, 0)
        p.d.rectangle((4, 4, 8, 8), outline=1)
        p.d.rectangle((5, 5, 7, 7), fill=0)
        for x in (2, 9):
            p.px(x, 5), p.px(x + 1, 6), p.px(x, 7)
    else:     # 字：钱肉亮，上下左右四个字（暗笔画）
        p.d.line((5, 2, 7, 2), fill=0), p.px(6, 3, 0)            # 上
        p.d.line((5, 10, 7, 10), fill=0), p.px(6, 9, 0)          # 下
        p.d.line((2, 5, 2, 7), fill=0), p.px(3, 6, 0)            # 左
        p.d.line((10, 5, 10, 7), fill=0), p.px(9, 5, 0), p.px(9, 7, 0)  # 右
        p.px(3, 3, 0), p.px(9, 9, 0)                             # 高光边的暗点
    p.px(3, 2, 1), p.px(2, 3, 1)                                 # 左上高光
    return p.sprite()


def _edge():
    p = Part(3, 13)
    p.shape("rectangle", (0, 1, 2, 11), fill=1)
    p.px(1, 0), p.px(1, 12)
    p.d.line((1, 2, 1, 10), fill=0)
    p.px(1, 6, 1)
    return p.sprite()


def _mini():
    """手里的三枚小钱 7×5"""
    p = Part(9, 6)
    for x in (0, 2, 4):
        p.shape("ellipse", (x, x // 2, x + 4, x // 2 + 4), fill=1)
        p.px(x + 2, x // 2 + 2, 0)
    return p.sprite()


SPR = {}


def spr(name):
    if name not in SPR:
        SPR.update(zi=_coin(False), bei=_coin(True), edge=_edge(), mini=_mini())
    return SPR[name]


def coin(g: Gfx, cx: float, cy: float, phi: float, sq: float = 1.0):
    """phi = 翻转角：cos>0 字面、cos<0 背面；|cos| 小时侧棱。sq < 1 落地压扁"""
    c = math.cos(phi)
    a = abs(c)
    if a < 0.22:
        s = spr("edge")
    else:
        face = spr("zi" if c > 0 else "bei")
        s = pix.stretch(face, 1.0 if a > 0.8 else 0.6 if a > 0.5 else 0.3, 1.0)
    if sq != 1:
        s = pix.stretch(s, 2 - sq, sq)
    pix.blit(g, s, cx - s.w / 2, cy - s.h / 2 + (13 - s.h) / 2)


def mountains(g: Gfx):
    """远山与一棵松（背景，很淡）"""
    pts = [(0, 44), (14, 38), (26, 42), (44, 33), (60, 40), (74, 36), (92, 42), (110, 34), (128, 41)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        pix.dotted(g, x0, y0, x1, y1, 2)
    # 松
    x = 120
    g.d.line((x, 30, x, FLOOR - 1), fill=1)
    for k, (y, w) in enumerate(((22, 3), (27, 5), (32, 6))):
        g.d.polygon([(x - w, y + 3), (x + w, y + 3), (x, y - 2)], fill=1)
        g.d.line((x - w + 1, y + 3, x + w - 1, y + 3), fill=0)
        pix.checker(g, (x + 1, y, x + w + 1, y + 3), 0.5, 0)


@register
class CoinsOmen(Base):
    id = "o.coins"
    name = "金钱课"
    desc = "小道士摇响三枚方孔钱一扬手抛起，铜钱翻转落地弹跳迸火星；看背字定单拆重交，六掷成卦"
    T = {"play": END + 0.15 + REVEAL}

    def init(self):
        # 每掷哪几枚是背（背数 = 爻 - 6）
        self.backs = []
        for v in self.lines:
            idx = [0, 1, 2]
            self.rng.shuffle(idx)
            nb = v - 6
            self.backs.append([i in idx[:nb] for i in range(3)])
        self.spin = [[3 + self.rng.randrange(3) for _ in range(3)] for _ in range(6)]

    def throw_at(self, t):
        for i in range(5, -1, -1):
            if t >= STARTS[i]:
                return i, t - STARTS[i]
        return -1, t

    def play(self, g: Gfx, t: float):
        self.tick(t)
        if t < R0:
            mountains(g)
        floor(g, "stone")
        i, u = self.throw_at(t)
        D = DUR[i] if i >= 0 else 1
        big = i == 5
        rel, air = (REL(i), AIR(i)) if i >= 0 else (0, 0)
        done = min(i, 6) if t < R0 else 6              # 已成之爻（本掷落地后 +1）
        hand = None
        # ---------------- 小道士
        if t >= R0:
            k = t - R0
            pose = "raise" if 0.25 < k < 0.9 else "gongshou" if k < 0.25 else "idle"
            daoshi(g, DAO_X, FLOOR - (2 if 0.25 < k < 0.4 else 0), pose, t, face="happy" if k > 0.25 else "wow")
        elif i < 0:   # 开场：拱手一礼
            daoshi(g, DAO_X, FLOOR, "gongshou" if u < 0.3 else "bow", t)
        elif u < rel:  # 合掌摇钱（手上下抖）
            bob = -1 if int(u * 18) % 2 else 0
            hand = figure(g, DAO_X, FLOOR, t, arm="offer", dy=0, bob=False)["hand"]
            hand = (hand[0], hand[1] + bob)
        elif u < rel + 0.18:  # 出手
            a, at = arm("toss")
            figure(g, DAO_X, FLOOR, t, arm=a, arm_at=at, face="wow" if big else "normal", bob=False)
        else:
            land_all = u > rel + air + 0.1
            daoshi(g, DAO_X, FLOOR, "idle", t, face="happy" if land_all and big else "wow" if not land_all else "normal")
        # ---------------- 铜钱
        if i >= 0:
            backs = self.backs[i]
            hx, hy = DAO_X + 13, FLOOR - 21
            if u < rel:
                zip_back = span(u, 0, 0.14)
                if i > 0 and zip_back < 1:  # 上一掷的钱飞回手里
                    for j in range(3):
                        q = ease_in_out(zip_back)
                        x = lerp(COIN_X[j], hx, q)
                        y = lerp(FLOOR - 7, hy, q) - math.sin(q * math.pi) * 6
                        pix.dotted(g, x, y, lerp(COIN_X[j], hx, max(q - 0.25, 0)), y + 2, 2)
                        coin(g, x, y, math.pi * (q * 4 + j))
                else:
                    pix.blit(g, spr("mini"), hand[0] - 3, hand[1] - 4)
                    speed_lines(g, hand[0] + 4, hand[1] - 1, 1, u)
                    speed_lines(g, hand[0] - 7, hand[1] - 1, -1, u + 0.1)
            else:
                k = u - rel
                for j in range(3):
                    st = j * 0.03
                    q = span(k, st, st + air)
                    fin = 0.0 if not backs[j] else math.pi
                    peak = (42 if not big else 52) + j * 3
                    if q < 1:
                        x = lerp(hx, COIN_X[j], q)
                        y = lerp(hy, FLOOR - 7, q) - math.sin(q * math.pi) ** 0.8 * peak * 0.8
                        phi = fin + (1 - q) * self.spin[i][j] * math.pi * 2 + 0.6
                        coin(g, x, y, phi)
                        if q > 0.05 and int(t * 30) % 2 == 0:
                            g.px(x - (COIN_X[j] - hx) * 0.04, y + 6)
                    else:
                        b = k - st - air
                        h = 0
                        if b < 0.16:
                            h = math.sin(b / 0.16 * math.pi) * (4 if not big else 7)
                        elif b < 0.26:
                            h = math.sin((b - 0.16) / 0.1 * math.pi) * 1.5
                        sq = 0.7 if b < 0.05 or 0.16 <= b < 0.2 else 1.0
                        coin(g, COIN_X[j], FLOOR - 7 - h, fin, sq)
                    if self.hit(t, STARTS[i] + rel + st + air):
                        self.impact(g, COIN_X[j], FLOOR - 1, 1.6 if big else 0.8)
                        if j == 2:
                            pix.shake(g, t, 1.0)
                land = rel + air + 0.06
                if land <= u < land + 0.12:
                    pix.shake(g, t, 2.0 if big else 1.0)
                if u > land + 0.08:
                    done = i + 1
                if big and self.hit(t, STARTS[i] + land):
                    pix.flash(g)
        for j, (on, off) in enumerate(LABELS):  # “单·少阳”标签：落地后弹出，到下一掷出手时收起
            if on <= t < off:
                v = self.lines[j]
                self.pop(84, 19, f"{CALL[v]}·{YAO_NAME[v]}", t - on)
        self.particles(g)
        # ---------------- 卦牌 / 揭晓
        if t < R0:
            gl = -1.0
            if i >= 0:
                land = rel + air + 0.14
                gl = (u - land) / 0.3
            tally(g, self.lines, done, glint=gl)
            # 点阵：已成之爻；钱在空中时顶行一个跑点，摇钱时底行三点跳动
            mx_hexagram(g, self.lines, done)
            if i >= 0 and rel <= u < rel + air:
                g.mx[0, int((u - rel) / air * 8) % 8] = True
            elif i >= 0 and u < rel:
                for j in range(3):
                    g.mx[7, 1 + j * 3] = True
                    g.mx[7, 2 + j * 3 - 1] = int(u * 18 + j) % 2 == 0
            if i >= 0 and u > rel + air:
                g.mx_level = 4 if u < rel + air + 0.15 else 1
        else:
            self.reveal(g, t, R0)
        self.flush(g)
