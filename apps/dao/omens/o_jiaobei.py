"""掷筊（博杯）。

台闽庙宇问神的掷筊：一对新月形木筊，一面平（阳）、一面凸（阴）。小道士双手合捧一对筊（合起来像一轮满月），
举到额前默祷一拜，扬手掷出；筊在空中翻滚，落地——平面朝上的那只凸面着地，前后摇晃好一阵；
凸面朝上的那只“咚”地趴稳。一平一凸为圣筊，两平为笑筊，两凸为阴筊。
本作约定（游戏化，非传统）：笑筊 = 老阳 9，阴筊 = 老阴 6；圣筊：左筊平面朝上 = 少阳 7，右筊平面朝上 = 少阴 8。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, lerp, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import mx_hexagram
from .o_common import FLOOR, REVEAL, YAO_NAME, Base, arm, blit_center, floor, rotated, star4, tally

REST_X = (66, 92)
NAMES = {6: "阴筊", 7: "圣筊", 8: "圣筊", 9: "笑筊"}
T0 = 0.9
DUR = (0.9, 0.74, 0.74, 0.74, 0.74, 0.95)
STARTS = [T0 + sum(DUR[:i]) for i in range(6)]
END = STARTS[-1] + DUR[-1]
R0 = END + 0.2
DAO_X = 20


def REL(i):
    return 0.42 if i == 0 else 0.3


def AIR(i):
    return 0.36


def LAND(i):
    return REL(i) + AIR(i) + 0.04


LABELS = [(STARTS[j] + LAND(j) + 0.05, STARTS[j + 1] + REL(j + 1) if j < 5 else R0) for j in range(6)]


# ---------------------------------------------------------------- 筊杯（侧视 15×6）

def _block(flat_up: bool):
    """19×8。平面朝上：上沿一条平直的亮面（木纹），下面圆弧着地；凸面朝上：倒过来，弧面有高光与网点"""
    p = Part(19, 8)
    p.shape("chord", (0, -8, 18, 7), 0, 180, fill=1)        # 半月：平边在上
    p.d.line((1, 1, 17, 1), fill=0)                           # 平面与弧面之间的阴线
    for x in (3, 6, 10, 14):                                  # 平面上的木纹
        p.px(x, 0, 0)
    p.d.arc((3, -5, 15, 5), 20, 160, fill=0)                  # 弧面上一道刻线
    p.dither([(11, 2), (18, 1), (15, 6), (9, 7)], 0.5, 0)     # 背光
    p.px(4, 2, 1), p.px(5, 3, 1)                              # 高光
    s = p.sprite()
    return s if flat_up else s.flipv()


def _pair():
    """合捧时的一对筊：一轮满月 9×7（中间一道缝）"""
    p = Part(9, 8)
    p.shape("ellipse", (0, 0, 8, 7), fill=1)
    p.d.line((0, 4, 8, 4), fill=0)
    p.px(2, 2, 0), p.px(6, 6, 0), p.px(7, 6, 0)
    return p.sprite()


SPR = {}


def spr(name):
    if "flat" not in SPR:
        SPR.update(flat=_block(True), dome=_block(False), pair=_pair())
    return SPR[name]


def _lantern():
    """灯笼 11×14：上下木盖、鼓腹、竹骨三道、右侧网点"""
    p = Part(11, 14)
    p.shape("rectangle", (3, 0, 7, 1), fill=1)
    p.shape("ellipse", (0, 2, 10, 11), fill=1)
    p.shape("rectangle", (3, 12, 7, 13), fill=1)
    p.d.line((3, 1, 7, 1), fill=0)
    p.d.arc((2, 2, 8, 11), 100, 260, fill=0)
    p.d.arc((2, 2, 8, 11), 280, 80, fill=0)
    p.d.line((5, 3, 5, 10), fill=0)
    p.dither([(7, 3), (10, 5), (10, 9), (7, 11)], 0.5, 0)
    p.px(2, 5, 1), p.px(2, 6, 1)
    return p.sprite()


def lantern(g: Gfx, t: float):
    """顶上一盏摇晃的灯笼"""
    if "lan" not in SPR:
        SPR["lan"] = _lantern()
    a = math.sin(t * 2.2) * 0.1
    x0 = 46
    x = x0 + math.sin(a) * 8
    g.d.line((x0, 0, x, 4), fill=1)
    pix.blit(g, SPR["lan"], x - 5, 5)
    cx = int(round(x))
    for k in range(3):  # 穗
        g.d.line((cx - 1 + k, 20, cx - 1 + k, 21 + (k + int(t * 4)) % 2), fill=1)


def shrine(g: Gfx):
    """右边的神龛：歇山顶、两柱、牌位、供台"""
    x0, x1 = 108, 127
    g.d.polygon([(x0 - 3, 24), (x1 + 3, 24), (x1, 20), (x0, 20)], fill=1)
    g.d.line((x0 - 1, 22, x1 + 1, 22), fill=0)
    g.px(x0 - 3, 23), g.px(x1 + 3, 23)
    for x in (x0 + 1, x1 - 2):
        g.d.rectangle((x, 25, x + 1, 44), fill=1)
    g.d.rectangle((x0 + 6, 28, x1 - 7, 43), fill=1)
    g.d.rectangle((x0 + 7, 29, x1 - 8, 42), outline=0)
    for y in range(31, 41, 3):
        g.d.line((x0 + 9, y, x1 - 10, y), fill=0)
    g.d.rectangle((x0 - 2, 45, x1 + 2, 47), fill=1)
    g.d.line((x0 - 1, 46, x1 + 1, 46), fill=0)
    g.d.rectangle((x0, 48, x1, FLOOR - 1), outline=1)
    pix.checker(g, (x0 + 1, 49, x1, FLOOR - 1), 0.25)


@register
class JiaobeiOmen(Base):
    id = "o.jiaobei"
    name = "掷筊"
    desc = "小道士合捧一对新月木筊额前一拜，扬手掷出，筊翻滚落地摇晃；圣筊、笑筊、阴筊定爻，六掷成卦"
    T = {"play": R0 + REVEAL}

    def init(self):
        self.flat = []
        for v in self.lines:  # 由爻反推两只筊的朝向（与传统概率一致：笑 1/4、阴 1/4、圣 1/2）
            self.flat.append({9: (True, True), 6: (False, False), 7: (True, False), 8: (False, True)}[v])
        self.spin = [[(2 + self.rng.randrange(2)) * (1 if j else -1) for j in range(2)] for _ in range(6)]

    def throw_at(self, t):
        for i in range(5, -1, -1):
            if t >= STARTS[i]:
                return i, t - STARTS[i]
        return -1, t

    def block(self, g: Gfx, j: int, i: int, x: float, y: float, deg: float):
        s = spr("flat" if self.flat[i][j] else "dome")
        if j == 1:
            s = pix.flipped(s)
        blit_center(g, rotated(s, deg), x, y)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        if t < R0:
            shrine(g)
            lantern(g, t)
        floor(g, "tile")
        i, u = self.throw_at(t)
        done = i if t < R0 else 6
        # ---------------- 小道士
        hand = None
        if t >= R0:
            k = t - R0
            daoshi(g, DAO_X, FLOOR, "kneel" if 0.3 < k < 1.0 else "idle", t, face="happy")
        elif i < 0:  # 开场：拾起一对筊，合捧，举额一拜
            if t < 0.35:
                a, at = arm("reach")
                hand = figure(g, DAO_X, FLOOR, t, arm=a, arm_at=at, head="bow")["hand"]
            elif t < 0.6:
                hand = daoshi(g, DAO_X, FLOOR, "gongshou", t)["hand"]
            else:
                hand = daoshi(g, DAO_X, FLOOR, "bow", t)["hand"]
        elif u < REL(i):
            bow = i == 0 and u < 0.2
            hand = daoshi(g, DAO_X, FLOOR, "bow" if bow else "gongshou", t)["hand"]
        elif u < REL(i) + 0.16:
            a, at = arm("toss")
            figure(g, DAO_X, FLOOR, t, arm=a, arm_at=at, bob=False)
        else:
            daoshi(g, DAO_X, FLOOR, "idle", t, face="wow" if u < LAND(i) + 0.1 else "normal")
        # ---------------- 筊
        if i < 0:
            if t < 0.35:  # 地上一对筊，被拾起
                for j in range(2):
                    blit_center(g, spr("flat"), lerp(36 + j * 8, hand[0], span(t, 0.15, 0.35)), FLOOR - 4)
            elif hand:
                blit_center(g, spr("pair"), hand[0] + 1, hand[1] - 1)
                if t > 0.6 and int(t * 8) % 2 == 0:
                    star4(g, hand[0] + 6, hand[1] - 6, 1)
        else:
            rel, air = REL(i), AIR(i)
            hx, hy = DAO_X + 13, FLOOR - 21
            if u < rel:
                q = span(u, 0, 0.13)
                if i > 0 and q < 1:  # 上一掷的筊飞回手里
                    for j in range(2):
                        qq = ease_in_out(q)
                        x, y = lerp(REST_X[j], hx, qq), lerp(FLOOR - 4, hy, qq) - math.sin(qq * math.pi) * 8
                        self.block(g, j, i - 1, x, y, qq * 360 * (1 if j else -1))
                        pix.dotted(g, x, y, lerp(REST_X[j], hx, max(qq - 0.3, 0)), y + 1, 2)
                elif hand:
                    blit_center(g, spr("pair"), hand[0] + 1, hand[1] - 1)
            else:
                k = u - rel
                for j in range(2):
                    st = j * 0.04
                    q = span(k, st, st + air)
                    tx = REST_X[j]
                    flat = self.flat[i][j]
                    if q < 1:
                        x = lerp(hx, tx, q)
                        y = lerp(hy, FLOOR - 4, q) - math.sin(q * math.pi) * (30 + j * 4 + (8 if i == 5 else 0))
                        self.block(g, j, i, x, y, (1 - q) * self.spin[i][j] * 360)
                    else:
                        b = k - st - air
                        if flat:  # 凸面着地：前后摇晃，越摇越小
                            deg = math.sin(b * 22) * 28 * math.exp(-b * 5)
                            yy = FLOOR - 4 - (2 if b < 0.06 else 0)
                        else:     # 凸面朝上：咚一声趴稳，小弹一下
                            deg = 0
                            yy = FLOOR - 4 - (math.sin(b / 0.12 * math.pi) * 3 if b < 0.12 else 0)
                        self.block(g, j, i, tx, yy, deg)
                    if self.hit(t, STARTS[i] + rel + st + air):
                        self.impact(g, tx, FLOOR - 1, 1.3 if i == 5 else 0.7)
                if self.hit(t, STARTS[i] + rel + 0.04 + air):
                    pix.shake(g, t, 1.5)
                    if i == 5:
                        pix.flash(g)
                elif rel + air + 0.04 < u < rel + air + 0.14:
                    pix.shake(g, t, 1.0)
                if u > LAND(i):
                    done = i + 1
        for j, (on, off) in enumerate(LABELS):
            if on <= t < off:
                v = self.lines[j]
                self.pop(72, 26, f"{NAMES[v]}·{YAO_NAME[v]}", t - on)
        self.particles(g)
        if t < R0:
            gl = (u - LAND(i)) / 0.3 if i >= 0 else -1
            tally(g, self.lines, done, glint=gl)
            mx_hexagram(g, self.lines, done)
            if i >= 0 and u > LAND(i) - 0.04:  # 底行：两块筊（平面朝上一横，凸面朝上一点）
                for j in range(2):
                    x0 = 1 + j * 4
                    if self.flat[i][j]:
                        g.mx[7, x0:x0 + 3] = True
                    else:
                        g.mx[7, x0 + 1] = True
            elif i >= 0 and REL(i) <= u:
                g.mx[0, int((u - REL(i)) / AIR(i) * 8) % 8] = True
        else:
            self.reveal(g, t, R0)
        self.flush(g)
