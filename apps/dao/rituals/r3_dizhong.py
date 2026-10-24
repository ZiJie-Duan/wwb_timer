"""摇帝钟：右手执帝钟（三清铃）摇动，钟声一圈圈荡开，沿九重天一层层往上传，传到天门则门开。

帝钟又名三清铃、法铃，铜制，柄端作三叉（“山”字形，象征三清），摇之以召神、驱邪。
九重天：古人谓天有九重（《楚辞·天问》“圜则九重，孰营度之”）。
圆满句“声闻于天”出自《诗经·小雅·鹤鸣》“鹤鸣于九皋，声闻于天”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r3_kit import capsule, ocapsule, rot, round_of, side_text, sleeve, sparkle

PX, PY = 36, 17           # 握柄处（摆动支点）
LAD_X = 106               # 九天之梯中心
RUNG_Y = [58 - j * 5.6 for j in range(9)]
NINE = [f"{d}重天" for d in "一二三四五六七八九"]
GATE_Y = 1
PERIOD = 1.3              # 摆一个来回的秒数
AMP = 0.42
RENEW = 4.0

BODY = [(-3, 3), (3, 3), (7, 5), (9, 8), (10, 13), (11, 18), (14, 22), (-14, 22), (-11, 18), (-10, 13), (-9, 8),
        (-7, 5)]
SHADE = [(2, 4), (7, 5), (9, 8), (10, 13), (11, 18), (14, 22), (4, 22), (4, 8)]


def bell(g: Gfx, ang: float, clap: float, x: float = PX, y: float = PY):
    """帝钟：支点 (x, y) 在握柄中部；ang 钟身摆角，clap 钟舌相对钟身的摆角"""
    # 三叉柄头（山字）
    for pts in ([(0, -4), (0, -16)], [(-4, -11), (-4, -14), (0, -12), (4, -14), (4, -11)], [(0, -16), (0, -18)]):
        g.d.line(rot(pts, x, y, ang), fill=1, width=1)
    for sx in (-4, 4):
        (cx, cy), = rot([(sx, -15)], x, y, ang)
        g.d.ellipse((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
    (cx, cy), = rot([(0, -19)], x, y, ang)
    g.d.ellipse((cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5), fill=1)
    g.d.polygon(rot([(-2, -6), (2, -6), (2, 3), (-2, 3)], x, y, ang), fill=0, outline=1)  # 握柄
    # 钟身
    g.d.polygon(rot(BODY, x, y, ang), fill=0, outline=1)
    g.shade_poly(rot(SHADE, x, y, ang), 0.3, outline=None)   # 钟身右侧暗面
    g.d.polygon(rot(BODY, x, y, ang), outline=1)
    g.d.line(rot([(-8, 8), (8, 8)], x, y, ang), fill=1)
    g.d.line(rot([(-12, 20), (12, 20)], x, y, ang), fill=1)
    g.d.line(rot([(-6, 10), (-8, 17)], x, y, ang), fill=1)   # 高光
    # 钟舌
    a2 = ang + clap
    (lx, ly), = rot([(0, 21)], x, y, a2, 0, 0)
    (ox, oy), = rot([(0, 5)], x, y, ang)
    g.d.line((ox, oy, lx, ly), fill=1)
    g.d.ellipse((lx - 1.5, ly - 1.5, lx + 1.5, ly + 1.5), fill=1)


def fist(g: Gfx, x: float, y: float):
    """握柄的拳（拳心朝左，袖子往右上）"""
    sleeve(g, x + 6, y - 2, -0.55, length=60, w0=12, w1=30, shade=0.25)
    g.d.rounded_rectangle((x - 5, y - 6, x + 7, y + 5), radius=3, fill=0, outline=1)
    for k in range(3):
        g.d.line((x - 4, y - 3 + k * 3, x - 1, y - 3 + k * 3), fill=1)
    g.d.line((x + 1, y - 6, x + 1, y - 2), fill=1)  # 拇指


@register
class SanqingBell(Ritual):
    id = "r3.dizhong"
    name = "摇帝钟"
    desc = "右手摇三清铃，钟声一圈圈荡开，沿九重天逐层上达，传到天门则门开"
    T = {"enter": 3.4, "interrupt": 1.4, "resume": 1.6, "complete": 5.5}
    CYCLE = 540.0

    # ------------------------------------------------------------ 零件

    def swing(self, t: float, amp: float = 1.0) -> tuple[float, float, float]:
        """→ (钟身角, 钟舌相对角, 上次敲击后的秒数)"""
        w = 2 * math.pi / PERIOD
        a = AMP * amp * math.sin(w * t)
        clap = -AMP * amp * 0.9 * math.sin(w * t - 0.9)
        since = (t - PERIOD / 4) % (PERIOD / 2)  # 摆到两端时钟舌敲响
        return a, clap, since

    def mouth(self, ang: float) -> tuple[float, float]:
        return rot([(0, 22)], PX, PY, ang)[0]

    def ripples(self, g: Gfx, t: float, amp: float = 1.0, n: int = 4, upto: float | None = None):
        """最近几次敲击的声波"""
        if amp <= 0:
            return
        half = PERIOD / 2
        last = math.floor((t - PERIOD / 4) / half)
        for j in range(n):
            k = last - j
            ts = k * half + PERIOD / 4
            age = t - ts
            if age < 0 or (upto is not None and ts > upto):
                continue
            r = 6 + age * 24
            if r > 56:
                continue
            side = 1 if k % 2 else -1
            cx, cy = self.mouth(AMP * amp * side)
            dens = 1 if age < 0.4 else 2 if age < 1.0 else 3
            nn = max(8, int(2 * math.pi * r))
            for i in range(0, nn, dens):
                a = i / nn * 2 * math.pi
                x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.75
                if x < LAD_X - 13 and PY - 2 < y < 64 and not (abs(x - PX) < 15 and y < PY + 24):
                    g.px(x, y)

    def ladder(self, g: Gfx, level: float, t: float, gate: float = 0.0, show: float = 1.0):
        """九重天：level 0..9（已到达几层，可带小数 = 正在上升）"""
        for j, y in enumerate(RUNG_Y):
            if j >= show * 9:
                break
            w = 9 if j % 2 else 7
            x0 = LAD_X - w + (2 if j % 2 else -2)
            if j < int(level):
                g.d.line((x0, y, x0 + 2 * w, y), fill=1)
                g.px(x0 - 1, y - 1)
                g.px(x0 + 2 * w + 1, y - 1)
            else:
                for x in range(int(x0), int(x0 + 2 * w + 1), 3):
                    g.px(x, y)
        # 正在上升的声光
        j = int(level)
        if j < 9:
            f = level - j
            y0 = 64 if j == 0 else RUNG_Y[j - 1]
            y = lerp(y0, RUNG_Y[j], ease_in_out(f))
            x = LAD_X + math.sin(t * 3) * 2
            if level > 0.02 and show >= 1:
                g.d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=1)
                if blink(t, 0.6):
                    sparkle(g, x, y, 2)
            name = NINE[j]
            if show >= 1:
                ty = min(RUNG_Y[j] - 4, 54)
                g.d.rectangle((LAD_X - 40, ty - 1, LAD_X - 13, ty + 7), fill=0)
                g.text(LAD_X - 14, ty, name, size=8, align="right")
        self.gate(g, gate, show)

    def gate(self, g: Gfx, op: float, show: float = 1.0):
        """天门：两柱一顶，op 0..1 门开的程度（门扇往两边收，门里放光）"""
        if show < 1:
            return
        x, y = LAD_X, GATE_Y
        g.d.line((x - 11, y, x + 11, y), fill=1)
        g.d.line((x - 9, y + 2, x + 9, y + 2), fill=1)
        g.d.line((x - 8, y + 2, x - 8, y + 10), fill=1)
        g.d.line((x + 8, y + 2, x + 8, y + 10), fill=1)
        w = 7 * (1 - op)
        if w >= 1:
            g.d.rectangle((x - 7, y + 3, x - 7 + w, y + 10), fill=0, outline=1)
            g.d.rectangle((x + 7 - w, y + 3, x + 7, y + 10), fill=0, outline=1)
        if op > 0.2:
            for i in range(5):
                a = math.pi / 2 + (i - 2) * 0.35
                r = 4 + 10 * op
                g.d.line((x, y + 6, x + math.cos(a) * r * 1.3, y + 6 + math.sin(a) * r), fill=1)

    def mx_bell(self, g: Gfx, ang: float, since: float | None):
        s = 0 if abs(ang) < 0.15 else (1 if ang < 0 else -1)
        cx = 3 + s
        g.mx_set(3, 0)
        g.mx_set(3 + (s if abs(ang) > 0.3 else 0), 1)
        for x in range(cx - 1, cx + 2):
            g.mx_set(x, 2)
        for x in range(cx - 2, cx + 3):
            g.mx_set(x, 3)
            g.mx_set(x, 4)
        for x in range(cx - 3, cx + 4):
            g.mx_set(x, 5)
        g.mx_set(cx, 6)
        if since is not None and since < 0.35:  # 敲响
            side = 7 if ang > 0 else 0
            g.mx_set(side, 3)
            g.mx_set(side, 5)
            g.mx_set(side + (-1 if side else 1), 4)

    def level(self, e: float) -> float:
        _, _, p = round_of(e, self.CYCLE)
        return p * 9

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        drop = ease_out_back(span(t, 0, 1.1))
        oy = lerp(-50, 0, drop)
        amp = span(t, 1.3, 2.3)
        a, clap, since = self.swing(t - 1.3, amp) if t > 1.3 else (0.0, 0.0, 9.0)
        if t > 1.6:
            self.ripples(g, t - 1.3, amp)
        self.ladder(g, 0, t, show=span(t, 1.8, 3.0))
        bell(g, a, clap, PX, PY + oy)
        fist(g, PX, PY + oy - 1)
        self.mx_bell(g, a, since if t > 1.6 else None)
        g.mx_level = 4 if t > 1.6 and since < 0.12 else 1

    def hold(self, g: Gfx, t: float, e: float):
        n, k, _ = round_of(e, self.CYCLE)
        tt = t + 3.4 - 1.3  # 与入场的摆动相位接上
        a, clap, since = self.swing(tt)
        self.ripples(g, tt)
        if n > 1 and k < RENEW:
            # 续：天门开，一道光落回钟上，九天重新暗下
            op = 1 - span(k, 2.4, RENEW)
            self.ladder(g, 9 * (1 - span(k, 0.6, 2.6)), t, gate=op)
            if k < 2.4:
                f = span(k, 0.3, 1.6)
                x0, y0 = LAD_X, GATE_Y + 8
                mx, my = self.mouth(a)
                x1, y1 = lerp(x0, PX, ease_in(f)), lerp(y0, PY - 18, ease_in(f))
                g.d.line((x0, y0, x1, y1), fill=1)
                if f >= 1 and k < 2.0:
                    for i in range(8):
                        q = i / 8 * 2 * math.pi
                        g.d.line((PX + math.cos(q) * 22, PY + 4 + math.sin(q) * 18,
                                  PX + math.cos(q) * 27, PY + 4 + math.sin(q) * 22), fill=1)
        else:
            self.ladder(g, self.level(e), t)
        bell(g, a, clap)
        fist(g, PX, PY - 1)
        self.mx_bell(g, a, since)
        g.mx_level = 3 if since < 0.08 else 1

    def interrupt(self, g: Gfx, t: float, e: float):
        T = self.T["interrupt"]
        damp = 1 - ease_out(span(t, 0, 1.0))
        a, clap, since = self.swing(t, damp)
        clap *= damp
        self.ripples(g, t + 10, 1 - span(t, 0, 0.8), upto=None) if t < 0.8 else None
        self.ladder(g, self.level(e), t)
        bell(g, a, clap)
        fist(g, PX, PY - 1)
        if t > 0.6:  # 左手掌按住钟口
            y = PY + 26 - 4 * ease_out(span(t, 0.6, 1.0))
            g.d.rounded_rectangle((PX - 13, y, PX + 13, y + 6), radius=3, fill=0, outline=1)
            for x in (-8, -3, 2, 7):
                g.d.line((PX + x, y + 1, PX + x, y + 5), fill=1)
        self.mx_bell(g, a, None)

    def resume(self, g: Gfx, t: float, e: float):
        amp = span(t, 0.2, 1.3)
        tt = t + 3.4 - 1.3
        a, clap, since = self.swing(tt, amp)
        if t > 0.5:
            self.ripples(g, tt, amp)
        self.ladder(g, self.level(e), t)
        bell(g, a, clap)
        fist(g, PX, PY - 1)
        if t < 0.4:
            y = PY + 22 + 30 * ease_in(span(t, 0, 0.4))
            g.d.rounded_rectangle((PX - 13, y, PX + 13, y + 6), radius=3, fill=0, outline=1)
        self.mx_bell(g, a, since if t > 0.5 else None)

    def complete(self, g: Gfx, t: float, e: float):
        lv = self.level(e)
        amp = 1 + 0.4 * span(t, 0, 0.6)
        a, clap, since = self.swing(t * 1.6, amp)
        rise = lerp(lv, 9, ease_in_out(span(t, 0.2, 2.2)))
        op = ease_out(span(t, 2.2, 3.0))
        if t < 3.0:
            self.ripples(g, t * 1.6, amp * (1 - span(t, 2.4, 3.0)))
            self.ladder(g, rise, t, gate=op)
            bell(g, a * (1 - span(t, 2.2, 3.0)), clap * (1 - span(t, 2.2, 3.0)))
            fist(g, PX, PY - 1)
            self.mx_bell(g, a, since)
            g.mx_level = 3 if since < 0.1 else 1
            return
        # 天门大开，光芒铺满，题字
        self.ladder(g, 9, t, gate=1)
        r = ease_out(span(t, 3.0, 4.0))
        for i in range(9):
            q = math.pi / 2 + (i - 4) * 0.3
            ln = (24 + 10 * (i % 2)) * r
            g.d.line((LAD_X + math.cos(q) * 8, GATE_Y + 8 + math.sin(q) * 6, LAD_X + math.cos(q) * (8 + ln) * 1.3,
                      GATE_Y + 8 + math.sin(q) * (6 + ln)), fill=1)
        bell(g, 0, 0)
        fist(g, PX, PY - 1)
        g.d.rectangle((2, 44, 82, 62), fill=0)
        typewriter(g, 42, 48, "声闻于天", t - 3.4, cps=5, align="center")
        for j in range(6):
            if blink(t + j * 0.17, 0.5, 0.3):
                g.px(60 + rand(j, 3) * 40, 10 + rand(j, 4) * 30)
        g.mx[0, 2:6] = True
        g.mx[1, 3:5] = True
        rr = (t - 3.0) * 4
        for y in range(8):
            for x in range(8):
                if abs(math.hypot(x - 3.5, y) - rr) < 0.7:
                    g.mx[y, x] = True
        g.mx_level = 1 + int(5 * (1 - span(t, 3.0, 4.5)))
