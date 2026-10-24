"""三献酒：供桌上三只青铜爵，执壶一献一献斟满（初献、亚献、终献），一巡献毕酹酒于地，再斟一巡。

依据：祭礼“三献”（初献、亚献、终献），道教斋醮的献供亦行三献；“酹”= 以酒浇地而祭；
“爵”为三足、双柱、前流后尾的古酒器。

入场：三只爵依次从上落到供桌，左上“初献”、右上“第一巡”。
持续：一轮 600 秒，分三献（第 3、200、400 秒）：一只宽袖手提执壶从右上来，悬在爵上倾倒，酒线注入、爵中酒面升起；
      斟满的爵上有一缕酒香、酒面上一点光游走。一巡结束：三只爵前倾，把酒酹在地上（溅起酒花），再从初献斟起。
中断：手提执壶来，放在供桌右端（“暂歇”），酒香散去。
恢复：手把执壶提走，酒香复起。
圆满：三爵齐酹，地上溅起酒花，“礼成”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, \
    span
from ..engine.cn import cn_num
from ..engine.fx import smoke_wisp
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import sleeve, sparkles

CUPS = (24, 55, 86)
FLOOR = 57
POURS = (3.0, 200.0, 400.0)
POUR_T = 7.0
NAMES = ("初献", "亚献", "终献")
POT_REST = (104, 40)   # 执壶放在桌上时的壶嘴尖
LIB = 2.6              # 酹酒时长


def rot(x, y, a):
    ca, sa = math.cos(a), math.sin(a)

    def P(u, v):
        return (x + u * ca - v * sa, y + u * sa + v * ca)
    return P


def jue(g: Gfx, x: float, wine: float = 0.0, tilt: float = 0.0, t: float = 0.0, seed: int = 0, drop: float = 0.0):
    """爵：(x, FLOOR) 为三足着地中心；wine 0..1 酒面；tilt 前倾角（弧度，向左倾）"""
    P = rot(x - 8, FLOOR - drop, -tilt)  # 以前足为支点
    def Q(u, v):
        return P(u + 8, v)
    d = g.d
    for a, b in (((-4, -12), (-9, 0)), ((4, -12), (9, 0)), ((0, -11), (0, -1))):  # 三足（刀形，外撇）
        d.line((*Q(*a), *Q(*b)), fill=1)
        d.line((*Q(a[0] + (1 if a[0] >= 0 else -1) * 0, a[1]), *Q(b[0] + (1 if b[0] > 0 else -1 if b[0] < 0 else 1), b[1])),
               fill=1)
    body = [Q(-6, -23), Q(6, -23), Q(7, -19), Q(6, -15), Q(3, -12), Q(-3, -12), Q(-6, -15), Q(-7, -19)]
    d.polygon(body, fill=0, outline=1)
    if wine > 0 and tilt < 0.05:
        top = lerp(-13, -22, clamp(wine))
        poly = [Q(-6, top), Q(6, top), Q(6, -16), Q(3, -13), Q(-3, -13), Q(-6, -16)]
        g.shade_poly(poly, 0.45, outline=None)
        d.line((*Q(-6, top), *Q(6, top)), fill=1)
        gx = (t * 3 + seed) % 8 - 4  # 酒面上游走的一点光
        d.point(Q(round(gx), top + 2), fill=0)
    else:
        d.line((*Q(-5, -17), *Q(5, -17)), fill=1)  # 腹带（空爵时看得见）
    d.polygon([Q(-6, -23), Q(-15, -27), Q(-14, -25), Q(-6, -20)], fill=0, outline=1)  # 流
    d.polygon([Q(6, -23), Q(11, -27), Q(6, -21)], fill=0, outline=1)  # 尾
    for u in (-4, -1):  # 双柱（立在流口两侧）
        d.line((*Q(u, -23), *Q(u, -28)), fill=1)
        d.line((*Q(u - 1, -29), *Q(u + 1, -29)), fill=1)
    d.line([Q(7, -20), Q(9, -19), Q(9, -15), Q(6, -14)], fill=1)  # 鋬
    return Q(-15, -27)  # 流口


def ewer(g: Gfx, x: float, y: float, tilt: float):
    """执壶：(x, y) 为壶嘴尖；tilt 0 = 直立，1 = 倾倒。返回握把处"""
    P = rot(x, y, -tilt * 0.6)
    d = g.d
    body = [P(14 + 7 * math.cos(k / 14 * 2 * math.pi), 13 + 7 * math.sin(k / 14 * 2 * math.pi)) for k in range(14)]
    neck = [P(11, 7), P(17, 7), P(16, 1), P(12, 1)]
    d.polygon(body, fill=0, outline=1)
    d.polygon(neck, fill=0, outline=1)
    d.line((*P(10, 0), *P(18, 0)), fill=1)
    d.ellipse((P(14, -2)[0] - 1, P(14, -2)[1] - 1, P(14, -2)[0] + 1, P(14, -2)[1] + 1), fill=1)
    d.line([P(8, 14), P(3, 6), P(0, 0)], fill=1)       # 壶流
    d.line([P(9, 11), P(4, 4), P(1, 0)], fill=1)
    d.line([P(17, 2), P(24, 5), P(23, 13), P(19, 17)], fill=1)  # 把
    d.line((*P(10, 13), *P(18, 13)), fill=1)
    for u in (11, 14, 17):
        g.px(*P(u, 16))
    return P(24, 9)


@register
class ThreeLibations(Ritual):
    id = "r1.wine"
    name = "三献酒"
    desc = "三只青铜爵，执壶初献亚献终献一一斟满；一巡献毕前倾酹酒于地，再斟一巡"
    T = {"enter": 3.5, "interrupt": 1.6, "resume": 1.4, "complete": 5.0}
    CYCLE = 600.0

    # ------------------------------------------------------------ 状态

    def levels(self, k: float) -> list:
        out = []
        for s in POURS:
            out.append(ease_in_out(span(k, s + 1.8, s + 4.8)))
        return out

    def stage(self, k: float) -> int:
        return max([i for i, s in enumerate(POURS) if k >= s] + [0])

    def pour_pose(self, i: int, u: float):
        """第 i 献，u = 开始后秒数 → (壶嘴 x, y, 倾角, 出画)"""
        cx = CUPS[i]
        tx, ty = cx + 1, 17
        if u < 1.2:
            p = ease_out(u / 1.2)
            return lerp(150, tx, p), lerp(-25, ty, p), 0.0
        if u < 5.4:
            return tx, ty, ease_in_out(span(u, 1.2, 1.8)) * (1 - ease_in_out(span(u, 4.8, 5.4)))
        p = ease_in(span(u, 5.4, POUR_T))
        return lerp(tx, 150, p), lerp(ty, -25, p), 0.0

    # ------------------------------------------------------------ 零件

    def texts(self, g: Gfx, e: float, k: float, a: float = 1.0, left: str | None = None, right: bool = True):
        n = int(e // self.CYCLE) + 1
        s = left if left is not None else NAMES[self.stage(k)]
        r = f"第{cn_num(n)}巡"
        g.text(2, 2, s[:int(round(clamp(a) * len(s)))])
        if right:  # 执壶在右上时不写（被袖子挡住）
            g.text(126, 2, r[:int(round(clamp(a) * len(r)))], align="right")

    def table(self, g: Gfx):
        g.d.line((0, FLOOR + 1, 127, FLOOR + 1), fill=1)
        g.shade((0, FLOOR + 3, 128, 64), 0.15)

    def cups(self, g: Gfx, lv: list, t: float, aroma: float = 1.0):
        for i, x in enumerate(CUPS):
            jue(g, x, lv[i], t=t, seed=i * 3)
            if lv[i] >= 1 and aroma > 0:
                smoke_wisp(g, x, FLOOR - 24, 9 * aroma, t, self.seed + i, sway=1.5, speed=4)

    def stream(self, g: Gfx, x0: float, y0: float, y1: float, t: float, dx: float = 0.0):
        n = int(y1 - y0)
        for j in range(max(n, 0)):
            if (j + int(t * 40)) % 5:
                g.px(x0 + dx * j / max(n, 1), y0 + j)

    def splash(self, g: Gfx, x: float, q: float):
        """地上溅起的酒花：q 0..1"""
        if not 0 < q < 1:
            return
        for j in range(5):
            a = math.pi * (0.15 + 0.7 * j / 4)
            r = q * 7
            g.px(x + math.cos(a) * r * 1.4, FLOOR - math.sin(a) * r * (1 - q) * 1.5)
        g.d.line((x - q * 9, FLOOR, x + q * 9, FLOOR), fill=1)

    def libation(self, g: Gfx, k: float, t: float, full: list):
        """三爵前倾酹酒于地：k 0..LIB"""
        tilt = 0.38 * ease_in_out(span(k, 0.0, 0.6)) * (1 - ease_in_out(span(k, 1.9, LIB)))
        for i, x in enumerate(CUPS):
            lip = jue(g, x, full[i] if tilt < 0.05 else 0.0, tilt=tilt, t=t, seed=i * 3)
            if 0.5 < k < 1.9 and full[i] > 0:
                self.stream(g, lip[0], lip[1] + 1, FLOOR, t, dx=-1)
                self.splash(g, lip[0] - 1, ((k - 0.6) * 1.6) % 1.0)
        return tilt

    def mx(self, g: Gfx, lv: list, t: float, pouring: bool = False):
        g.mx_rows([0b00100100, 0b11111111, 0b01000010, 0b01000010, 0b00111100, 0b00100100, 0b01001010, 0b10000101])
        filled = sum(1 for v in lv if v >= 1)
        cur = max(lv) if lv else 0
        if filled >= 1 or cur > 0.3:
            g.mx[3, 2:6] = True
        if filled >= 2 or cur > 0.7:
            g.mx[2, 2:6] = True
        if pouring:
            g.mx[0, 3 + int(t * 8) % 2] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.table(g)
        for i, x in enumerate(CUPS):
            p = ease_out_bounce(span(t, 0.2 + i * 0.35, 1.0 + i * 0.35))
            if p > 0:
                jue(g, x, drop=lerp(70, 0, p))
        self.texts(g, 0, 0, a=span(t, 2.0, 3.0))
        self.mx(g, [0, 0, 0], t)
        n = int(span(t, 0.2, 1.9) * 8)  # 爵从上往下“落”进点阵
        if n < 8:
            g.mx[:8 - n, :] = False

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        lv = self.levels(k)
        self.table(g)
        if e >= self.CYCLE and k < LIB:  # 一巡献毕：酹酒
            self.libation(g, k, t, [1, 1, 1])
            self.texts(g, e - k - 1, self.CYCLE - 1, left="酹酒")
            self.mx(g, [1, 1, 1] if k < 1.2 else [0, 0, 0], t)
            return
        pouring = False
        busy = False
        for i, s in enumerate(POURS):
            u = k - s
            if 0 <= u < POUR_T:
                self.cups(g, lv, t)
                x, y, tilt = self.pour_pose(i, u)
                busy = True
                self.texts(g, e, k, right=False)
                hand = ewer(g, x, y, tilt)
                sleeve(g, hand[0] + 2, hand[1], -0.45)
                if tilt > 0.9:
                    top = FLOOR - lerp(12, 21, lv[i]) - 1
                    self.stream(g, x, y + 1, top, t)
                    pouring = True
                break
        else:
            self.cups(g, lv, t)
        if not busy:
            self.texts(g, e, k)
        self.mx(g, lv, t, pouring)

    def _rest_pot(self, g: Gfx, p: float, hand: bool):
        """把执壶从画外送到桌右端（p 1 = 放稳）"""
        rx, ry = POT_REST
        x, y = lerp(150, rx, ease_out(p)), lerp(-30, ry, ease_out(p))
        h = ewer(g, x, y, 0.0)
        if hand:
            sleeve(g, h[0] + 2, h[1], -0.45)

    def interrupt(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        lv = self.levels(k)
        self.table(g)
        self.cups(g, lv, t, aroma=1 - ease_out(span(t, 0, 1.0)))
        if t < 1.0:
            self._rest_pot(g, span(t, 0, 0.9), True)
        else:
            rx, ry = POT_REST
            ewer(g, rx, ry, 0.0)
            if t < 1.6:
                p = ease_in(span(t, 1.0, 1.6))
                h = (rx + 24, ry + 9)
                sleeve(g, lerp(h[0] + 2, 160, p), lerp(h[1], -30, p), -0.45)
        self.texts(g, e, k, left="暂歇" if t > 0.8 else None)
        self.mx(g, lv, t)

    def resume(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        lv = self.levels(k)
        self.table(g)
        self.cups(g, lv, t, aroma=ease_out(span(t, 0.6, 1.4)))
        if t < 0.5:
            rx, ry = POT_REST
            ewer(g, rx, ry, 0.0)
            p = ease_out(span(t, 0, 0.5))
            sleeve(g, lerp(160, rx + 26, p), lerp(-30, ry + 9, p), -0.45)
        else:
            self._rest_pot(g, 1 - span(t, 0.5, 1.3), True)
        self.texts(g, e, k, left="暂歇" if t < 0.5 else None)
        self.mx(g, lv, t)

    def complete(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        lv = self.levels(k)
        self.table(g)
        if t < LIB:
            self.libation(g, t, t, [1 if v > 0.3 else 0 for v in lv])
            self.texts(g, e, k, a=1 - span(t, 0.2, 1.2))
        else:
            for x in CUPS:
                jue(g, x, 0)
            p = ease_out_back(span(t, LIB, LIB + 0.6))
            if p > 0:
                g.text(64, 4 + (1 - p) * 8, "礼成", scale=2, align="center")
            sparkles(g, 64, 14, 52, 12, t, n=10, seed=self.seed)
        self.mx(g, lv if t < 1.2 else [0, 0, 0], t)
        if t > LIB:
            g.mx_level = 1 + int(4 * (1 - span(t, LIB, LIB + 1.5)))
