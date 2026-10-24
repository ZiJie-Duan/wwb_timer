"""长明灯：琉璃盏里一汪灯油，浮芯上一朵火，油随计时慢慢浅下去，灯焰也跟着沉。

依据：宫观殿前供长明灯（五供“香花灯水果”之灯），昼夜不熄，执事随时添油。
《庄子·养生主》：“指穷于为薪，火传也，不知其尽也。”

入场：一只宽袖手执引火棒从左边伸来，点着浮芯，灯晕一圈圈亮开。
持续：灯油随 e 下降（一轮 10 分钟），火苗随油面下沉，油快尽时火变小；光晕呼吸，偶尔一只飞蛾绕灯。
      油尽：右上方一只手提油壶倾倒，油线注入，油面回升，火苗被托上来（“添油”），右侧“第几盏”加一。
中断：捻小灯芯，火缩成一粒豆火，光晕收拢（长明灯不灭）。
恢复：豆火重新长高，光晕再起。
圆满：灯焰暴涨放光，一点火星升出画面，“火传也 / 不知其尽也”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, pulse, span
from ..engine.cn import cn_num
from ..engine.fx import flame, ring
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import rays, sleeve, sparkles, vreveal

CX = 64
TOP, BOT = 19, 45          # 琉璃盏口沿 / 盏底
HW_TOP, HW_BOT = 18, 8     # 半宽
OIL_FULL, OIL_EMPTY = 23, 41
RENEW = 6.0


def cup_hw(y: float) -> float:
    k = clamp((y - TOP) / (BOT - TOP))
    return lerp(HW_TOP, HW_BOT, k * k)


def lamp_body(g: Gfx, oil_y: float | None):
    """琉璃盏 + 灯柱 + 莲座；oil_y：油面（None = 不画油）"""
    d = g.d
    left, right = [], []
    for i in range(14):
        y = TOP + (BOT - TOP) * i / 13
        hw = cup_hw(y)
        left.append((CX - hw, y))
        right.append((CX + hw, y))
    if oil_y is not None:
        poly = [(CX - cup_hw(oil_y) + 1, oil_y)] + [p for p in left if p[1] > oil_y]
        poly = [(x + 1, y) for x, y in poly]
        rp = [(x - 1, y) for x, y in right if y > oil_y][::-1] + [(CX + cup_hw(oil_y) - 1, oil_y)]
        poly += rp
        if len(poly) >= 3:
            g.shade_poly(poly, 0.25, outline=None)
            d.line((CX - cup_hw(oil_y) + 1, oil_y, CX + cup_hw(oil_y) - 1, oil_y), fill=1)
    d.line(left, fill=1)
    d.line(right, fill=1)
    d.line((CX - HW_TOP - 2, TOP, CX - HW_TOP + 2, TOP), fill=1)   # 口沿外翻
    d.line((CX + HW_TOP - 2, TOP, CX + HW_TOP + 2, TOP), fill=1)
    d.line((CX - HW_BOT, BOT, CX + HW_BOT, BOT), fill=1)
    # 琉璃高光
    d.line((CX - HW_TOP + 4, TOP + 4, CX - HW_TOP + 6, TOP + 12), fill=1)
    # 灯柱、节、莲座
    d.rectangle((CX - 2, BOT + 1, CX + 2, 56), fill=0, outline=1)
    d.ellipse((CX - 5, 49, CX + 5, 52), fill=0, outline=1)
    d.polygon([(CX - 14, 62), (CX + 14, 62), (CX + 9, 57), (CX - 9, 57)], fill=0, outline=1)
    for x in (-8, -3, 2, 7):  # 莲瓣
        d.arc((CX + x - 3, 57, CX + x + 3, 63), 180, 360, fill=1)


def float_wick(g: Gfx, y: float):
    g.d.line((CX - 3, y, CX + 3, y), fill=1)
    g.d.line((CX, y - 1, CX, y - 2), fill=1)


def oil_pot(g: Gfx, x: float, y: float, tilt: float):
    """油壶：(x, y) 为壶嘴尖，tilt 0 = 平放，1 = 倾倒"""
    a = -0.1 - tilt * 0.55  # 壶身绕嘴尖旋转
    ca, sa = math.cos(a), math.sin(a)

    def P(u, v):  # 局部坐标：嘴尖为原点，壶身在右（u>0），v 向下
        return (x + u * ca - v * sa, y + u * sa + v * ca)

    body = [P(18 + 10 * math.cos(k / 16 * 2 * math.pi), 6 + 7 * math.sin(k / 16 * 2 * math.pi)) for k in range(16)]
    g.d.polygon(body, fill=0, outline=1)
    g.d.line((*P(0, 0), *P(9, 5)), fill=1)        # 壶嘴
    g.d.line((*P(1, 1), *P(10, 8)), fill=1)
    g.d.line((*P(13, -2), *P(23, -2)), fill=1)    # 口
    g.shade_poly(body, 0.12, outline=1)
    g.d.line([P(26, 1), P(31, 0), P(32, 6), P(27, 10)], fill=1)  # 把手
    return P(32, 4)  # 手握处


def moth(g: Gfx, t: float, fy: float, seed: int):
    """飞蛾：每 23 秒来绕灯飞 6 秒"""
    k = (t + seed % 7) % 23
    if k > 6:
        return
    a = k * 2.4
    r = 16 + 3 * math.sin(k * 3)
    x, y = CX + math.cos(a) * r, fy - 2 + math.sin(a) * r * 0.55 - (6 - k) * 0.5 if k < 1 else fy - 2 + math.sin(a) * r * 0.55
    if k < 1:
        x += (1 - k) * 60
    if k > 5:
        x -= (k - 5) * 60
        y -= (k - 5) * 20
    up = int(t * 12) % 2
    g.px(x, y)
    g.px(x - 1, y - up)
    g.px(x + 1, y - up)
    g.px(x - 2, y - up * 2 + 1)
    g.px(x + 2, y - up * 2 + 1)


@register
class EternalLamp(Ritual):
    id = "r1.lamp"
    name = "长明灯"
    desc = "琉璃盏长明灯，油随计时变浅、火苗下沉；油尽提壶添油，火又被托起"
    T = {"enter": 4.0, "interrupt": 1.6, "resume": 1.6, "complete": 5.0}
    CYCLE = 600.0

    def oil(self, e: float) -> float:
        p = (e % self.CYCLE) / self.CYCLE
        return lerp(OIL_FULL, OIL_EMPTY, p)

    def fsize(self, e: float) -> float:
        """油快尽时火变小"""
        p = (e % self.CYCLE) / self.CYCLE
        return 1 - 0.4 * span(p, 0.85, 1.0)

    # ------------------------------------------------------------ 零件

    def fire(self, g: Gfx, oil_y: float, t: float, s: float = 1.0, halo: float = 1.0):
        fy = oil_y - 2
        if s > 0.25:
            flame(g, CX, fy, 7 * s, 15 * s, t, self.seed)
        elif s > 0:
            g.d.ellipse((CX - 1, fy - 3, CX + 1, fy), fill=1)
        if halo > 0:
            r = (11 + 2 * pulse(t, 2.6)) * halo
            ring(g, CX, fy - 6 * s, r, density=3, phase=t * 0.3)
            if halo > 0.6:
                ring(g, CX, fy - 6 * s, r + 5, density=6, phase=-t * 0.2)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        vreveal(g, 3, 4, "长明灯", a)
        vreveal(g, 113, 4, right if right is not None else f"第{cn_num(n)}盏", a)

    def mx(self, g: Gfx, oil_p: float, t: float, s: float = 1.0):
        """点阵：小灯盏，火苗跳，油位"""
        g.mx_rows([0, 0, 0, 0b01111110, 0b01000010, 0b00111100, 0b00011000, 0b01111110])
        if oil_p > 0.5:
            g.mx[4, 2:6] = True
        if s <= 0:
            return
        if s < 0.3:
            g.mx[2, 3 + int(t * 3) % 2] = True
            return
        lean = 1 if noise(t * 5, self.seed + 9) > 0.55 else 0
        g.mx[2, 2:6] = True
        g.mx[1, 3 + lean:5 + lean - (1 if s < 0.8 else 0)] = True
        if s >= 0.8 and blink(t, 0.4, 0.6):
            g.mx[0, 3 + lean] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        lamp_body(g, OIL_FULL)
        fy = OIL_FULL - 2
        lit = t > 1.7
        float_wick(g, OIL_FULL)
        if lit:
            grow = ease_out_back(span(t, 1.7, 2.3))
            self.fire(g, OIL_FULL, t, grow, ease_out(span(t, 2.2, 3.4)))
            if t < 2.0:  # 点着的一闪
                ring(g, CX, fy - 3, (t - 1.7) * 40, density=2)
        # 引火棒：手从左下伸来，棒尖碰灯芯，再收回
        if t < 3.0:
            if t < 1.7:
                p = ease_out(span(t, 0.2, 1.5))
            else:
                p = 1 - ease_in(span(t, 1.9, 3.0))
            tipx, tipy = lerp(-30, CX - 2, p), lerp(fy + 18, fy - 1, p)
            hx, hy = tipx - 26, tipy + 12
            g.d.line((hx + 2, hy - 2, tipx, tipy), fill=1)
            g.d.line((hx + 2, hy - 1, tipx, tipy + 1), fill=1)
            if t < 1.9:
                flame(g, tipx, tipy, 4, 6, t, self.seed + 3)
            else:
                g.px(tipx, tipy - 1)
            sleeve(g, hx, hy, math.pi * 0.86)
        self.texts(g, 0, a=span(t, 2.6, 3.8))
        self.mx(g, 1.0, t, ease_out(span(t, 1.7, 2.3)) if lit else 0)
        if abs(t - 1.75) < 0.1:
            g.mx_level = 5

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        oil = self.oil(e)
        s = self.fsize(e)
        lamp_body(g, oil)
        float_wick(g, oil)
        self.fire(g, oil, t, s)
        moth(g, t, oil - 8, self.seed)
        self.texts(g, e)
        self.mx(g, 1 - k / self.CYCLE, t, s)

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """油尽添油：提壶倾倒，油面回升"""
        fill = ease_in_out(span(k, 1.8, 4.4))
        oil = lerp(OIL_EMPTY, OIL_FULL, fill)
        s = lerp(0.6, 1.0, fill)
        lamp_body(g, oil)
        float_wick(g, oil)
        self.fire(g, oil, t, s, halo=0.5 + 0.5 * fill)
        # 壶：进 0-1.2，倾 1.2-1.8，倒到 4.4，回正 4.4-4.9，走 4.9-6
        if k < 1.2:
            p = ease_out(span(k, 0, 1.2))
            px, py = lerp(150, CX + 19, p), lerp(-20, 13, p)
            tilt = 0
        elif k < 4.9:
            px, py = CX + 19, 13
            tilt = ease_in_out(span(k, 1.2, 1.8)) * (1 - ease_in_out(span(k, 4.4, 4.9)))
        else:
            p = ease_in(span(k, 4.9, RENEW))
            px, py = lerp(CX + 19, 150, p), lerp(13, -20, p)
            tilt = 0
        hand = oil_pot(g, px, py, tilt)
        sleeve(g, hand[0] + 3, hand[1], -0.35)
        if tilt > 0.9:  # 油线
            x0, y0 = px - 1, py + 1
            for j in range(0, int(oil - y0)):
                yy = y0 + j
                xx = x0 - j * 0.35 * (1 - j / 40)
                if (j + int(t * 30)) % 4:
                    g.px(xx, yy)
        self.texts(g, e if k > 3 else e - k - 1)
        self.mx(g, fill, t, s)

    def interrupt(self, g: Gfx, t: float, e: float):
        oil = self.oil(e)
        p = ease_in_out(span(t, 0.1, 1.2))
        s = lerp(self.fsize(e), 0.2, p)
        lamp_body(g, oil)
        float_wick(g, oil)
        self.fire(g, oil, t, s, halo=1 - p)
        self.texts(g, e, right="微火" if t > 0.8 else None)
        self.mx(g, 1 - (e % self.CYCLE) / self.CYCLE, t, s)

    def resume(self, g: Gfx, t: float, e: float):
        oil = self.oil(e)
        p = ease_out_back(span(t, 0.2, 1.2))
        s = lerp(0.2, self.fsize(e), p)
        lamp_body(g, oil)
        float_wick(g, oil)
        self.fire(g, oil, t, s, halo=ease_out(span(t, 0.6, 1.6)))
        self.texts(g, e)
        self.mx(g, 1 - (e % self.CYCLE) / self.CYCLE, t, s)
        if abs(t - 0.5) < 0.1:
            g.mx_level = 3

    def complete(self, g: Gfx, t: float, e: float):
        oil = self.oil(e)
        s0 = self.fsize(e)
        flare = ease_out(span(t, 0.2, 1.2)) * (1 - 0.4 * ease_in_out(span(t, 2.4, 3.4)))
        s = s0 + flare * 0.35
        lamp_body(g, oil)
        float_wick(g, oil)
        fy = oil - 2
        self.fire(g, oil, t, s, halo=1 + flare * 0.4)
        if t > 0.6:
            rays(g, CX, fy - 6, 15 + flare * 3, 17 + flare * 10, n=9, rot=t * 0.5, a0=-math.pi - 0.25, a1=0.25)
            sparkles(g, CX, fy - 8, 34, 26, t, n=10, seed=self.seed)
        # 一点火星升出画面
        if 1.2 < t < 3.2:
            k = span(t, 1.2, 3.2)
            sy = lerp(fy - 18 * s, -6, ease_in(k))
            sx = CX + math.sin(k * 9) * 3
            g.d.rectangle((sx - 1, sy - 1, sx, sy), fill=1)
            g.px(sx, sy + 3)
            g.px(sx, sy + 6)
        if t < 1.2:
            self.texts(g, e, a=1 - span(t, 0.2, 1.0))
        else:
            vreveal(g, 113, 4, "火传也", span(t, 1.6, 2.6))
            vreveal(g, 3, 2, "不知其尽也", span(t, 2.6, 4.2))
        self.mx(g, 1.0, t, 1.0)
        if t > 0.2:
            from .r1_common import mx_ring
            if t < 2.0:
                mx_ring(g, (t - 0.2) * 3.5, 3.5, 2)
            g.mx_level = 1 + int(5 * (1 - span(t, 0.3, 2.0)))
