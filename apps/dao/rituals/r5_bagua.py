"""先天后天：八卦由先天方位逐一移到后天方位。

依据：先天八卦（伏羲）乾南坤北、离东坎西，《说卦传》“天地定位，山泽通气，雷风相薄，水火不相射，八卦相错”；
后天八卦（文王）离南坎北、震东兑西，《说卦传》“帝出乎震，齐乎巽，相见乎离，致役乎坤，说言乎兑，战乎乾，
劳乎坎，成言乎艮”。图南在上。

入场：太极出现，先天八卦依次从中心弹出排成内圈。
持续：一轮 10 分钟分八段，按“帝出乎震……成言乎艮”的次序，每段一卦从内圈（先天位）飞到外圈（后天位），
      右边竖写这一句；一圈点线随计时走满一周。八卦俱到后天位后：八卦一起旋回先天位（“天地定位”），再一轮。
中断：太极停转，八卦暗下，“暂歇”。
恢复：八卦亮回，太极再转。
圆满：其余诸卦一齐飞到后天位，外圈转一周，“八卦相错”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.fx import ring
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import HOUTIAN, TRIGRAMS, XIANTIAN, mx_taiji, mx_trigram, taiji

CX, CY = 64, 32
ORDER = ["震", "巽", "离", "坤", "兑", "乾", "坎", "艮"]
PHRASE = ["帝出乎震", "齐乎巽", "相见乎离", "致役乎坤", "说言乎兑", "战乎乾", "劳乎坎", "成言乎艮"]
INNER = (11.5, 7, 2.4)    # 半径、宽、爻距
OUTER = (21.0, 12, 3.0)
FLY = 4.0                 # 一卦飞过去的秒数（按 e）
RENEW = 5.0


def tri(g: Gfx, name: str, ang: float, r: float, w: float, step: float, cx: float = CX, cy: float = CY):
    """在 ang（0 = 正上，顺时针）方向、半径 r 处画一个三爻卦，初爻朝内"""
    ux, uy = math.sin(ang), -math.cos(ang)
    tx, ty = -uy, ux
    hw = w / 2
    gap = max(1.2, w * 0.13)
    for k, bit in enumerate(TRIGRAMS[name][2]):
        rr = r + k * step
        px, py = cx + ux * rr, cy + uy * rr
        if bit:
            g.d.line((px - tx * hw, py - ty * hw, px + tx * hw, py + ty * hw), fill=1)
        else:
            g.d.line((px - tx * hw, py - ty * hw, px - tx * gap, py - ty * gap), fill=1)
            g.d.line((px + tx * gap, py + ty * gap, px + tx * hw, py + ty * hw), fill=1)


def slot(name: str, outer: bool):
    order = HOUTIAN if outer else XIANTIAN
    return order.index(name) * math.pi / 4, OUTER if outer else INNER


def tri_at(g: Gfx, name: str, p: float, bump: float = 0.0):
    """p：0 = 先天位（内圈），1 = 后天位（外圈）；中间沿弧线飞"""
    a0, (r0, w0, s0) = slot(name, False)
    a1, (r1, w1, s1) = slot(name, True)
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    q = ease_in_out(p)
    r = lerp(r0, r1, q) + math.sin(math.pi * q) * 6 + bump
    tri(g, name, a0 + da * q, r, lerp(w0, w1, q), lerp(s0, s1, q))


@register
class Bagua(Ritual):
    id = "r5.bagua"
    name = "先天后天"
    desc = "八卦按“帝出乎震”的次序，一卦一卦从先天方位飞到后天方位，一轮满再旋回先天"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.5, "complete": 5.0}
    CYCLE = 600.0

    def seg(self, e: float):
        """→ (当前第几卦 0..7, 本段已过秒数)"""
        k = e % self.CYCLE
        L = self.CYCLE / 8
        i = min(int(k // L), 7)
        return i, k - i * L

    def frame(self, g: Gfx, done: int, cur_p: float, t: float, spin: float, hi: int | None = None):
        """done：已到后天位的卦数；cur_p：第 done 卦的飞行进度"""
        taiji(g, CX, CY, 6, spin)
        for j, name in enumerate(ORDER):
            if j < done:
                tri_at(g, name, 1.0)
            elif j == done:
                tri_at(g, name, cur_p)
            else:
                tri_at(g, name, 0.0)
        if hi is not None and blink(t, 1.2, 0.5):
            a, (r, w, s) = slot(ORDER[hi], True)
            ux, uy = math.sin(a), -math.cos(a)
            x, y = CX + ux * (r + s * 2 + 4), CY + uy * (r + s * 2 + 4)
            g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)

    def progress(self, g: Gfx, e: float):
        """一圈点线（r=18）随计时走满一周"""
        p = (e % self.CYCLE) / self.CYCLE
        n = int(p * 40)
        for i in range(n + 1):
            a = i / 40 * 2 * math.pi
            g.px(round(CX + math.sin(a) * 18), round(CY - math.cos(a) * 18))

    def side(self, g: Gfx, right: str, a: float = 1.0):
        g.vtext(2, 4, "先天"[:int(round(a * 2))])
        if a >= 1:
            g.d.line((8, 30, 8, 36), fill=1)
            g.d.line((6, 34, 8, 36), fill=1)
            g.d.line((10, 34, 8, 36), fill=1)
        g.vtext(2, 39, "后天"[:int(round(a * 2))])
        r = right[:int(round(a * len(right)))]
        g.vtext(114, 2, r)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        s = ease_out_back(span(t, 0, 0.8))
        if s > 0:
            taiji(g, CX, CY, max(1, 6 * s), t * 2)
        for j, name in enumerate(XIANTIAN):
            q = span(t, 0.8 + j * 0.15, 1.3 + j * 0.15)
            if q > 0:
                a, (r, w, st) = slot(name, False)
                tri(g, name, a, r * ease_out_back(q), w, st)
        self.side(g, PHRASE[0], span(t, 2.4, 3.6))
        if t > 3.0:
            self.progress(g, 0)
        idx = min(7, int(span(t, 0.8, 2.0) * 8))
        if t < 0.8:
            mx_taiji(g, t * 2)
        else:
            mx_trigram(g, XIANTIAN[idx])

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k)
            return
        i, sec = self.seg(e)
        p = self.fly_p(e)
        self.frame(g, i, p, t, t * 0.6, hi=i if p >= 1 else None)
        if 0 < p < 1:
            a, (r, w, s) = slot(ORDER[i], True)
            g.mx_level = 3
        self.progress(g, e)
        self.side(g, PHRASE[i])
        mx_trigram(g, ORDER[i])
        if p < 1:
            g.mx[0, :] = blink(t, 0.2)

    def _renew(self, g: Gfx, t: float, k: float):
        """八卦一齐旋回先天位"""
        back = ease_in_out(span(k, 0.5, 3.5))
        taiji(g, CX, CY, 6, t * 0.6 + back * 8)
        for name in ORDER:
            a0, (r0, w0, s0) = slot(name, True)
            a1, (r1, w1, s1) = slot(name, False)
            da = (a1 - a0) % (2 * math.pi)  # 一律顺时针转回
            tri(g, name, a0 + da * back, lerp(r0, r1, back) + math.sin(math.pi * back) * 4, lerp(w0, w1, back),
                lerp(s0, s1, back))
        if 3.5 < k < 4.5:
            ring(g, CX, CY, 8 + (k - 3.5) * 30, 2)
            g.mx_level = 4
        self.side(g, "天地定位" if k > 0.5 else PHRASE[7])
        if k > 4.0:
            self.progress(g, 0)
        mx_taiji(g, k * 3)

    def fly_p(self, e: float) -> float:
        i, sec = self.seg(e)
        d = RENEW if (i == 0 and e >= self.CYCLE) else 0
        return span(sec, d, FLY + d)

    def interrupt(self, g: Gfx, t: float, e: float):
        i, sec = self.seg(e)
        p = self.fly_p(e)
        spin = 0.6 * (t - 0.5 * t * t / 1.5) if t < 1.5 else 0.45
        self.frame(g, i, p, t, spin)
        g.fade(1 - 0.55 * span(t, 0.2, 1.3), (16, 0, 112, 64))
        self.progress(g, e)
        self.side(g, "暂歇" if t > 0.6 else PHRASE[i])
        mx_trigram(g, ORDER[i])

    def resume(self, g: Gfx, t: float, e: float):
        i, sec = self.seg(e)
        p = self.fly_p(e)
        self.frame(g, i, p, t, t * 0.6 * span(t, 0, 1.5))
        if t < 1.2:
            g.fade(0.45 + 0.55 * span(t, 0.2, 1.2), (16, 0, 112, 64))
        self.progress(g, e)
        self.side(g, "暂歇" if t < 0.5 else PHRASE[i])
        mx_trigram(g, ORDER[i])

    def complete(self, g: Gfx, t: float, e: float):
        i, sec = self.seg(e)
        fly = span(t, 0.2, 1.6)
        spin = ease_in_out(span(t, 1.6, 3.6)) * 2 * math.pi
        taiji(g, CX, CY, 6 + 2 * ease_out(span(t, 1.6, 2.4)), t * 0.6 + spin * 2)
        for j, name in enumerate(ORDER):
            p = 1.0 if j < i else clamp(fly * 1.3 - (j - i) * 0.05)
            if p < 1:
                tri_at(g, name, p)
            else:
                a, (r, w, s) = slot(name, True)
                tri(g, name, a + spin, r, w, s)
        if t > 3.6:
            ring(g, CX, CY, 12 + ((t - 3.6) * 25) % 30, 2)
        right = PHRASE[i] if t < 1.6 else "八卦相错"
        self.side(g, right, 1.0 if t < 1.6 else span(t, 1.6, 2.6))
        if t < 1.6:
            mx_trigram(g, ORDER[min(7, i + int(fly * (8 - i)))])
        else:
            mx_taiji(g, t * 3)
            g.mx_level = 1 + int(4 * (1 - span(t, 1.6, 3.0)))
