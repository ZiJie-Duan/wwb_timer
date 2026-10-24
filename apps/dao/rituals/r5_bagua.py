"""先天后天：小道士手持拂尘，把八卦从先天方位一卦一卦请到后天方位。

依据：先天八卦（伏羲）乾南坤北、离东坎西；后天八卦（文王）离南坎北、震东兑西（图南在上）。
《说卦传》“帝出乎震，齐乎巽，相见乎离，致役乎坤，说言乎兑，战乎乾，劳乎坎，成言乎艮”；“天地定位……八卦相错”。

画面：右边一面八角卦盘（双线八角框、角上铜钉），中心太极，内圈是先天八卦，外圈是后天位；
左边小道士持拂尘站着。
入场：卦盘弹出，太极转起，先天八卦一卦卦从中心弹出排成内圈，左上“帝出乎震”。
持续：一轮分八段（每段 75 秒），按“帝出乎震……成言乎艮”的次序：段首小道士剑指一点，这一卦从内圈的先天位
      带着光尾沿弧线飞到外圈的后天位（变大），落定时一闪；左上写这一句。其余时间他甩拂尘、作揖，
      太极慢转、内外圈之间一圈点线随 e 走满一周。
      续：八卦一齐旋回先天位，太极急转、闪光，“天地定位”。
中断：太极减速停住，诸卦暗下，“暂歇”。  恢复：太极复转，诸卦亮回。
圆满：其余诸卦一齐飞到后天位，外圈转一周，太极变大放光，“八卦相错”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import HOUTIAN, TRIGRAMS, XIANTIAN, mx_taiji, mx_trigram, taiji
from .r5_util import Clock, arm, cached, label, mx_ring, pop_box, ring, sparkle

FLOOR = 60
DX = 20
CX, CY = 88, 31
R_IN, R_OUT, R_OCT = 10, 19, 29
ORDER = ["震", "巽", "离", "坤", "兑", "乾", "坎", "艮"]
PHRASE = ["帝出乎震", "齐乎巽", "相见乎离", "致役乎坤", "说言乎兑", "战乎乾", "劳乎坎", "成言乎艮"]
SEG = 75.0
FLY = 4.0
RENEW = 5.0


def angle_of(order, name) -> float:
    return order.index(name) * math.pi / 4


def tri(g: Gfx, name: str, ang: float, r: float, w: float, step: float, fill: int = 1):
    """一卦：三爻沿切向，初爻朝内；ang 从正上方顺时针"""
    ux, uy = math.sin(ang), -math.cos(ang)
    tx, ty = -uy, ux
    hw = w / 2
    for k, bit in enumerate(TRIGRAMS[name][2]):
        rr = r + k * step
        px, py = CX + ux * rr, CY + uy * rr
        if bit:
            g.d.line((px - tx * hw, py - ty * hw, px + tx * hw, py + ty * hw), fill=fill)
        else:
            gap = max(1.2, w * 0.14)
            g.d.line((px - tx * hw, py - ty * hw, px - tx * gap, py - ty * gap), fill=fill)
            g.d.line((px + tx * gap, py + ty * gap, px + tx * hw, py + ty * hw), fill=fill)


def board(g: Gfx, t: float, k: float = 1.0):
    """八角卦盘：双线八角框、八个角上的铜钉、内外圈之间的细圈"""
    if k <= 0:
        return
    R = R_OCT * ease_out_back(k)
    pts = [(CX + math.sin(math.pi / 8 + i * math.pi / 4) * R, CY - math.cos(math.pi / 8 + i * math.pi / 4) * R)
           for i in range(8)]
    g.d.polygon(pts, fill=0, outline=1)
    R2 = R - 2
    pts2 = [(CX + math.sin(math.pi / 8 + i * math.pi / 4) * R2, CY - math.cos(math.pi / 8 + i * math.pi / 4) * R2)
            for i in range(8)]
    g.d.polygon(pts2, outline=1)
    for x, y in pts:
        g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
        g.px(x, y, 0)


def _whisk():
    """拂尘：木柄 + 一束马尾（三缕，末梢分叉）"""
    p = Part(6, 14)
    p.shape("line", (1, 0, 1, 4), fill=1)
    p.px(0, 0), p.px(2, 0)
    p.shape("polygon", [(0, 5), (3, 5), (5, 13), (1, 13)], fill=1)
    p.d.line((2, 6, 3, 12), fill=0)
    p.px(1, 13, 0), p.px(3, 13, 0)
    return p.sprite()


def whisk():
    return cached(("r5bagua", "whisk"), _whisk)


@register
class BaGua(Clock, Ritual):
    id = "r5.bagua"
    name = "先天后天"
    desc = "八角卦盘上，八卦按《说卦传》“帝出乎震……成言乎艮”的次序，一卦卦从先天位飞到后天位；小道士持拂尘剑指相送"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 1.6, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)

    # ------------------------------------------------------------ 状态

    def state(self, e: float):
        """→ (轮 c, 轮内 k, 已飞完的卦数 n, 正在飞的第 n 卦进度 q)"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        off = RENEW if c >= 1 else 0.0
        kk = k - off
        n = 0
        q = 0.0
        for i in range(8):
            s = i * SEG + 1.0
            if kk >= s + FLY:
                n = i + 1
            elif kk >= s:
                q = (kk - s) / FLY
        return c, k, n, q

    # ------------------------------------------------------------ 画

    def trigrams(self, g: Gfx, n: int, q: float, t: float, dim: float = 1.0, show=None):
        """已飞的在外圈后天位，没飞的在内圈先天位，正在飞的在半路（带光尾）"""
        for i, name in enumerate(ORDER):
            if show is not None and not show(i):
                continue
            a0, a1 = angle_of(XIANTIAN, name), angle_of(HOUTIAN, name)
            if i < n:
                tri(g, name, a1, R_OUT, 9, 2.5)
            elif i == n and q > 0:
                d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                p = ease_in_out(q)
                a = a0 + d * p
                r = lerp(R_IN, R_OUT, p) + math.sin(p * math.pi) * 6
                for m in range(1, 6):                       # 光尾
                    pp = max(p - m * 0.05, 0)
                    aa, rr = a0 + d * pp, lerp(R_IN, R_OUT, pp) + math.sin(pp * math.pi) * 6
                    g.px(CX + math.sin(aa) * (rr + 2), CY - math.cos(aa) * (rr + 2))
                g.d.ellipse((CX + math.sin(a) * (r + 2) - 5, CY - math.cos(a) * (r + 2) - 5,
                             CX + math.sin(a) * (r + 2) + 5, CY - math.cos(a) * (r + 2) + 5), fill=0)
                tri(g, name, a, r, lerp(7, 9, p), lerp(2, 2.5, p))
            else:
                tri(g, name, a0, R_IN, 7, 2)
        if dim < 1:
            g.fade(dim, (CX - R_OCT, CY - R_OCT, CX + R_OCT + 1, CY + R_OCT + 1))

    def progress(self, g: Gfx, k: float):
        """内外圈之间一圈点线随 e 走满一周"""
        r = (R_IN + 5 + R_OUT) / 2 + 0.5
        n = int(64 * k / self.CYCLE)
        for j in range(n):
            a = j / 64 * 2 * math.pi
            if j % 2 == 0:
                g.px(CX + math.sin(a) * r, CY - math.cos(a) * r)

    def core(self, g: Gfx, ang: float, r: float = 6):
        g.d.ellipse((CX - r - 1, CY - r - 1, CX + r + 1, CY + r + 1), fill=0)
        taiji(g, CX, CY, r, ang)

    def actor(self, g: Gfx, e: float, t: float, q: float, n: int, k: float):
        """飞卦时剑指相送；平时持拂尘，隔一阵甩一下、作个揖"""
        if 0 < q < 1:
            h = daoshi(g, DX, FLOOR, "point", t, face="wow" if q < 0.5 else "normal")
            hx, hy = h["hand"]
            if (t * 6) % 1 < 0.5:
                sparkle(g, hx + 2, hy, 0.5)
            return
        ph = e % 24
        if 14 < ph < 16.5:
            daoshi(g, DX, FLOOR, "bow" if 15 < ph < 16 else "gongshou", t)
            return
        swish = 6 < ph < 7.2
        lift = 2 if swish and (t * 5) % 1 < 0.5 else 0
        h = figure(g, DX, FLOOR, t, arm=arm("hold"), arm_at=(-3, -16 - lift))
        hx, hy = h["hand"]
        w = whisk()
        if swish and (t * 5) % 1 < 0.5:
            pix.blit(g, w.rot90(1), hx - 2, hy - 7)
        else:
            pix.blit(g, w, hx - 1, hy - 1)

    def caption(self, g: Gfx, i: int):
        label(g, 5, 4, PHRASE[i])

    def mx(self, g: Gfx, name: str, t: float, flying: bool):
        mx_trigram(g, name)
        if flying and (t * 6) % 1 < 0.5:
            g.mx[0, :] = True

    def scene(self, g: Gfx, t: float, e: float, dt: float):
        c, k, n, q = self.state(e)
        board(g, t)
        renew = c >= 1 and k < RENEW
        if renew:
            p = ease_in_out(span(k, 0.3, 3.0))
            for i, name in enumerate(ORDER):                  # 八卦一齐旋回先天位
                a0, a1 = angle_of(HOUTIAN, name), angle_of(XIANTIAN, name)
                d = (a1 - a0) % (2 * math.pi)
                a = a0 + d * p
                tri(g, name, a, lerp(R_OUT, R_IN, p), lerp(9, 7, p), lerp(2.5, 2, p))
            self.core(g, t * 0.8 + ease_in_out(span(k, 0, 4)) * 25, 6 + 2 * math.sin(span(k, 2.8, 4.0) * math.pi))
            if 3.0 <= k < 3.07:
                pix.flash(g)
            if 3.0 <= k < 3.0 + dt:
                self.sparks.burst(CX, CY, 20, 34, life=0.7, gravity=0)
            daoshi(g, DX, FLOOR, "raise" if k < 3.4 else "gongshou", t, face="happy")
        else:
            self.progress(g, k)
            self.trigrams(g, n, q, t)
            self.core(g, t * 0.8)
            if 0 < n and 0 < (k - (RENEW if c >= 1 else 0) - ((n - 1) * SEG + 1 + FLY)) < 0.6:
                name = ORDER[n - 1]                              # 落定一闪
                a = angle_of(HOUTIAN, name)
                sparkle(g, CX + math.sin(a) * (R_OUT + 8), CY - math.cos(a) * (R_OUT + 8),
                        span(k - (RENEW if c >= 1 else 0) - ((n - 1) * SEG + 1 + FLY), 0, 0.6))
            self.actor(g, e, t, q, n, k)
        self.sparks.step(dt)
        self.sparks.draw(g)
        return c, k, n, q, renew

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        board(g, t, span(t, 0, 0.6))
        if t > 0.5:
            self.core(g, t * 1.5, 6 * ease_out_back(span(t, 0.5, 0.9)))
        for i, name in enumerate(XIANTIAN):                # 先天八卦一卦卦弹出
            p = ease_out_back(span(t, 1.0 + i * 0.22, 1.4 + i * 0.22))
            if p > 0:
                tri(g, name, angle_of(XIANTIAN, name), R_IN * p, 7 * min(p, 1.1), 2 * min(p, 1))
        x = lerp(-12, DX, ease_out(span(t, 0, 1.8)))
        if t < 1.8:
            figure(g, x, FLOOR, t, legs="walk")
        else:
            daoshi(g, DX, FLOOR, "gongshou" if t < 3.2 else "idle", t)
        if t > 3.2:
            self.caption(g, 0)
        mx_taiji(g, t * 2)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, n, q, renew = self.scene(g, t, e, dt)
        if renew:
            if k > 1.0:
                label(g, 5, 4, "天地定位")
            mx_taiji(g, t * 6)
            return
        i = n if 0 < q < 1 else max(n - 1, 0)
        if n == 0 and q == 0:
            i = 0
        self.caption(g, i)
        self.mx(g, ORDER[i], t, 0 < q < 1)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, n, q = self.state(e)
        board(g, t)
        self.progress(g, k)
        self.trigrams(g, n, q, t, dim=1 - 0.7 * span(t, 0.2, 1.2))
        self.core(g, 0.8 * ease_out(span(t, 0, 1.2)) * 1.5)
        daoshi(g, DX, FLOOR, "gongshou", t)
        label(g, 5, 4, "暂歇")
        mx_trigram(g, ORDER[min(n, 7)])

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, n, q = self.state(e)
        board(g, t)
        self.progress(g, k)
        self.trigrams(g, n, q, t, dim=0.3 + 0.7 * span(t, 0.2, 1.2))
        self.core(g, ease_in(span(t, 0, 1.2)) * 1.5 + t * 0.8)
        daoshi(g, DX, FLOOR, "point" if t < 1.2 else "idle", t)
        if t > 0.3:
            self.caption(g, max(n - 1, 0) if not (0 < q < 1) else n)
        self.mx(g, ORDER[max(n - 1, 0)], t, False)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, n, q = self.state(e)
        if c >= 1 and k < RENEW:
            n, q = 0, 0.0
        board(g, t)
        p = ease_in_out(span(t, 0.3, 1.8))
        spin = ease_in_out(span(t, 1.8, 3.4)) * 2 * math.pi
        for i, name in enumerate(ORDER):
            a0, a1 = angle_of(XIANTIAN, name), angle_of(HOUTIAN, name)
            if i < n:
                a, r, w, s = a1, R_OUT, 9, 2.5
            else:
                d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
                a = a0 + d * p
                r, w, s = lerp(R_IN, R_OUT, p), lerp(7, 9, p), lerp(2, 2.5, p)
            tri(g, name, a + spin, r, w, s)
        rr = 6 + 3 * ease_out_back(span(t, 3.4, 3.9))
        self.core(g, t * 3, rr)
        if 3.4 <= t < 3.47:
            pix.flash(g)
        if 3.4 <= t < 3.4 + dt:
            self.sparks.burst(CX, CY, 30, 44, life=0.9, gravity=10)
        if t > 3.4:
            for j in range(2):
                r = ((t - 3.4) * 26 + j * 13) % 26 + rr
                ring(g, CX, CY, r)
        self.sparks.step(dt)
        self.sparks.draw(g)
        pose = "point" if t < 1.8 else ("raise" if t < 3.6 else ("bow" if 4.2 < t < 5.0 else "gongshou"))
        daoshi(g, DX, FLOOR, pose, t, face="happy" if t > 3.4 else "normal")
        if t > 3.8:
            y = pop_box(g, 30, 4, "八卦相错", t, 3.8, stars=False)
            g.text(30, y, "八卦相错", align="center")
        if t < 3.4:
            mx_taiji(g, t * 3)
        else:
            mx_ring(g, (t - 3.4) * 4 % 6)
            g.mx_level = 1 + int(5 * (1 - span(t, 3.4, 5)))
