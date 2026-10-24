"""示波太极：示波器切到 X-Y 模式，CH1 接“阳”（sin）、CH2 接“阴”（cos），李萨如图形是一个圆——
电子束在荧光屏上一笔一笔把太极画出来。

依据：周敦颐《太极图说》：“无极而太极。太极动而生阳……静而生阴……分阴分阳，两仪立焉。”
《易·系辞上》：“一阴一阳之谓道。”
持续（一轮 10 分钟，四段）：
  无极：电子束绕圈，余辉越拖越长，直到一个完整的圆。
  太极：圆里画出 S 形分界。
  生阳：两个鱼眼出现，阳鱼被扫描线一行行填亮（行距越来越密）。
  两仪：完整的太极图，慢慢转起来，越转越快。
  一轮满：太极越转越快，缩成一个亮点（复归无极），再从亮点涨回一个圆，“第几周”加一。
  右侧面板：两路通道的小波形（阳 sin、阴 cos）在走，阶段名，周数。
入场：屏幕开机一条亮线横扫，格子亮起，亮点出现开始绕圈。
中断：STOP，电子束停住，余辉渐暗成灰。
恢复：RUN，余辉亮回来，电子束继续。
圆满：太极填满、急转，上移缩小，下方“一阴一阳之谓道”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, span
from .r6_common import num as cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import mx_taiji, taiji
from .r6_common import tiny

SX1 = 93                 # 屏幕右边界
CX, CY, R = 47, 32, 26
RENEW = 5.0
STAGES = ("无极", "太极", "生阳", "两仪")


def circle_pts(r: float, n: int = 96):
    return [(math.cos(-math.pi / 2 + i / n * 2 * math.pi) * r, math.sin(-math.pi / 2 + i / n * 2 * math.pi) * r)
            for i in range(n + 1)]


def s_pts(r: float, n: int = 48):
    """S 形分界（未旋转，u 右 v 下）：上小圆左半弧（自顶到心），下小圆右半弧（自心到底）"""
    h = r / 2
    pts = []
    for i in range(n // 2 + 1):
        a = -math.pi / 2 - i / (n // 2) * math.pi       # 顶 → 左 → 心
        pts.append((math.cos(a) * h, -h + math.sin(a) * h))
    for i in range(1, n // 2 + 1):
        a = -math.pi / 2 + i / (n // 2) * math.pi       # 心 → 右 → 底
        pts.append((math.cos(a) * h, h + math.sin(a) * h))
    return pts


CIRC = circle_pts(R)
SPTS = s_pts(R)


def _yang_spans():
    """阳鱼（未旋转）每一行的亮段 [(v, u0, u1), ...]"""
    out = []
    h = R / 2
    dot = R / 6.5
    for v in range(-R, R + 1):
        run = None
        for u in range(-R, R + 2):
            inside = u * u + v * v <= R * R
            up = u * u + (v + h) ** 2 <= h * h
            lo = u * u + (v - h) ** 2 <= h * h
            w = inside and ((u > 0 and not lo) or up)
            w = w and not (u * u + (v + h) ** 2 <= dot * dot)
            if w and run is None:
                run = u
            elif not w and run is not None:
                out.append((v, run, u - 1))
                run = None
    return out


SPANS = _yang_spans()


def rot(pts, a: float, cx: float = CX, cy: float = CY, s: float = 1.0):
    c, sn = math.cos(a), math.sin(a)
    return [(cx + (u * c - v * sn) * s, cy + (u * sn + v * c) * s) for u, v in pts]


@register
class Scope(Ritual):
    id = "r6.scope"
    name = "示波太极"
    desc = "示波器 X-Y 模式，电子束从无极一圈画出太极：分界、鱼眼、阳鱼扫描填亮、两仪旋转，一周满归无极"
    T = {"enter": 3.6, "interrupt": 1.5, "resume": 1.6, "complete": 5.2}
    CYCLE = 600.0

    def setup(self):
        self.freq = self.rng.choice((50, 60, 100, 440, 1000))

    # ------------------------------------------------------------ 零件

    def bezel(self, g: Gfx, on: float = 1.0):
        g.d.rectangle((0, 0, SX1, 63), outline=1)
        if on <= 0:
            return
        for x in range(CX - 40, CX + 41, 10):          # 格点
            for y in range(CY - 30, CY + 31, 10):
                if 1 <= x < SX1 and on > abs(x - CX) / 50:
                    g.px(x, y)
        for x in range(3, SX1 - 1, 2):                  # 中轴刻度
            if on > abs(x - CX) / 50:
                g.px(x, CY)
        for y in range(2, 63, 2):
            if on > 0.5:
                g.px(CX, y)

    def panel(self, g: Gfx, t: float, stage: str, n: int, run: bool = True):
        tt = t if run else 0.0
        g.text(96, 2, "阳", size=8)
        g.text(96, 12, "阴", size=8)
        prev = prev2 = None
        for i in range(22):
            x = 105 + i
            y1 = 5 + 3 * math.sin(i * 0.45 - tt * 6)
            y2 = 15 + 3 * math.cos(i * 0.45 - tt * 6)
            if prev is not None:
                g.d.line((x - 1, prev, x, y1), fill=1)
            if i % 2 == 0:
                g.px(x, y2)
            prev = y1
        g.d.line((95, 22, 127, 22), fill=1)
        g.text(111, 26, stage, align="center")
        g.text(111, 42, f"第{cn_num(n)}周", size=8, align="center")
        tiny(g, 111, 56, "X-Y", align="center")

    def trace(self, g: Gfx, pts, upto: float, head: bool, t: float, solid: float = 0.25):
        """余辉：已画部分点状（越旧越稀），最近 solid 比例实线；head：电子束亮点"""
        n = len(pts) - 1
        k = int(clamp(upto) * n)
        for i in range(k):
            age = (k - i) / max(n, 1)
            if age < solid:
                g.d.line((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]), fill=1)
            elif i % 2 == 0:
                g.px(*pts[i])
        if head and k <= n:
            x, y = pts[k]
            g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)

    def beam_circle(self, g: Gfx, t: float, length: float, angle: float, head: bool = True, s: float = 1.0):
        """电子束绕圆：长度 length（0..1 圈）的余辉尾巴，头在 t 决定的角度"""
        n = 96
        hd = int(t * 40) % n
        L = int(length * n)
        pts = rot(CIRC, angle, s=s)
        for j in range(L):
            i = (hd - j) % n
            age = j / n
            if age < 0.25:
                g.d.line((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]), fill=1)
            elif i % 2 == 0:
                g.px(*pts[i])
        if head:
            x, y = pts[hd]
            g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)

    def figure(self, g: Gfx, p: float, t: float, run: bool = True, s: float = 1.0, cx: float = CX,
               cy: float = CY, extra_rot: float = 0.0):
        """按一轮进度 p 画出当前的图形，返回阶段名"""
        tt = t if run else 0.0
        st = min(3, int(p * 4))
        k = p * 4 - st
        if st == 0:
            self.beam_circle(g, tt, 0.3 + 0.7 * k, 0, head=run, s=s)
            return STAGES[0]
        a = 0.0
        if st == 3:
            a = (k * k) * 6.0 + extra_rot
        cpts = rot(CIRC, a, cx, cy, s)
        if st == 3:
            taiji(g, cx, cy, R * s, angle=a, outline=False)
            g.d.ellipse((cx - R * s - 1, cy - R * s - 1, cx + R * s + 1, cy + R * s + 1), outline=1)
            if run:
                hd = int(tt * 40) % 96
                x, y = cpts[hd]
                g.d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=1)
            return STAGES[3]
        self.trace(g, cpts, 1.0, False, tt, solid=1.0)
        sp = rot(SPTS, a, cx, cy, s)
        if st == 1:
            self.trace(g, sp, k, run, tt, solid=0.3)
            return STAGES[1]
        # 生阳：鱼眼 + 扫描线填阳鱼
        self.trace(g, sp, 1.0, False, tt, solid=1.0)
        h = R / 2
        g.d.ellipse((cx - 2, cy - h - 2, cx + 2, cy - h + 2), outline=1)
        g.d.ellipse((cx - 2, cy + h - 2, cx + 2, cy + h + 2), fill=1)
        step = max(1, int(round(lerp(7, 1.5, k))))
        scan = int(tt * 30) % (2 * R + 1) - R if run else None
        for v, u0, u1 in SPANS:
            if (v + R) % step == 0:
                g.d.line((cx + u0, cy + v, cx + u1, cy + v), fill=1)
        if scan is not None:  # 扫描束
            for v, u0, u1 in SPANS:
                if v == scan:
                    g.d.line((cx + u0, cy + v, cx + u1, cy + v), fill=1)
                    g.d.rectangle((cx + u1 - 1, cy + v - 1, cx + u1 + 1, cy + v + 1), fill=1)
        return STAGES[2]

    def mx(self, g: Gfx, t: float, amp: float = 3.0, run: bool = True):
        tt = t if run else 0.0
        for x in range(8):
            y = int(round(3.5 + amp * math.sin(x * 0.8 - tt * 5)))
            g.mx_set(x, y)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        on = ease_out(span(t, 0.0, 1.2))
        self.bezel(g, on)
        if t < 0.8:  # 开机亮线
            w = ease_out(span(t, 0.1, 0.8)) * 44
            g.d.line((CX - w, CY, CX + w, CY), fill=1)
        if t > 1.2:
            self.panel(g, t, "无极", 1)
            g.fade(span(t, 1.2, 2.0), (94, 0, 128, 64))
        if t > 1.8:
            dot = ease_out_back(span(t, 1.8, 2.3))
            if t < 2.3:
                g.d.ellipse((CX - 2 * dot, CY - R - 2 * dot, CX + 2 * dot, CY - R + 2 * dot), fill=1)
            else:
                self.beam_circle(g, t - 2.3 + 0.0, 0.3 * ease_out(span(t, 2.3, 3.6)), 0)
        if t < 1.8:
            g.mx[3, :int(on * 8)] = True
        else:
            self.mx(g, t, amp=3 * span(t, 1.8, 3.0))

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n = int(e // self.CYCLE) + 1
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, t, n)
            return
        p = k / self.CYCLE
        self.bezel(g)
        stage = self.figure(g, p, t)
        self.panel(g, t, stage, n)
        if p >= 0.75:
            mx_taiji(g, (p - 0.75) * 4 * ((p - 0.75) * 4) * 6.0 + t * 0.0)
        else:
            self.mx(g, t, amp=1 + p * 3)

    def _renew(self, g: Gfx, k: float, t: float, n: int):
        self.bezel(g)
        if k < 3.2:  # 越转越快、缩成一点
            a = 6.0 + k * k * 3.0
            s = 1 - ease_in(span(k, 1.6, 3.2))
            if s > 0.08:
                taiji(g, CX, CY, max(R * s, 2), angle=a, outline=False)
                g.d.ellipse((CX - R * s - 1, CY - R * s - 1, CX + R * s + 1, CY + R * s + 1), outline=1)
            else:
                g.d.ellipse((CX - 2, CY - 2, CX + 2, CY + 2), fill=1)
            self.panel(g, t, "两仪" if k < 1.6 else "归一", n - 1)
            mx_taiji(g, a)
            if k > 2.6:
                g.mx[:, :] = False
                g.mx[3:5, 3:5] = True
                g.mx_level = 4
        else:
            # 亮点涨回一个圆（无极）
            s = ease_out_back(span(k, 3.2, 4.2))
            if s < 0.99:
                g.d.ellipse((CX - R * s, CY - R * s, CX + R * s, CY + R * s), outline=1)
            self.beam_circle(g, t, 0.3 * span(k, 3.8, 5.0), 0, head=k > 3.8) if k > 3.8 else None
            self.panel(g, t, "无极", n)
            self.mx(g, t, amp=span(k, 3.2, 5.0) * 1.0)

    def interrupt(self, g: Gfx, t: float, e: float):
        p = (e % self.CYCLE) / self.CYCLE
        n = int(e // self.CYCLE) + 1
        self.bezel(g)
        stage = self.figure(g, p, 0.0, run=False)
        lv = 1 - 0.6 * ease_out(span(t, 0.2, 1.2))
        if lv < 1:
            g.fade(lv, (1, 1, SX1, 63))
        self.panel(g, 0.0, stage, n, run=False)
        if blink(t, 0.6, 0.6) or t > 1.2:
            g.d.rectangle((3, 3, 21, 9), fill=1)
            tiny(g, 12, 4, "STOP", fill=0, align="center")
        self.mx(g, 0.0, amp=1 + p * 3, run=False)

    def resume(self, g: Gfx, t: float, e: float):
        p = (e % self.CYCLE) / self.CYCLE
        n = int(e // self.CYCLE) + 1
        self.bezel(g)
        run = t > 0.5
        stage = self.figure(g, p, t - 0.5 if run else 0.0, run=run)
        lv = 0.4 + 0.6 * ease_in(span(t, 0.2, 1.0))
        if lv < 1:
            g.fade(lv, (1, 1, SX1, 63))
        self.panel(g, t, stage, n, run=run)
        if t < 1.2:
            g.d.rectangle((3, 3, 21, 9), fill=1)
            tiny(g, 12, 4, "RUN", fill=0, align="center")
        if p >= 0.75:
            mx_taiji(g, 0)
        else:
            self.mx(g, t, amp=1 + p * 3, run=run)

    def complete(self, g: Gfx, t: float, e: float):
        p0 = (e % self.CYCLE) / self.CYCLE
        n = int(e // self.CYCLE) + 1
        if t < 2.8:
            self.bezel(g, 1 - span(t, 2.0, 2.8))
        # 0–1.0 补完到“两仪”，1.0–2.4 急转，2.0–3.0 上移缩小，3.0– 字
        p = lerp(p0, 0.999, ease_in_out(span(t, 0.0, 1.0)))
        mv = ease_in_out(span(t, 2.0, 3.0))
        s = lerp(1.0, 0.62, mv)
        cy = lerp(CY, 19, mv)
        a_extra = ease_in(span(t, 1.0, 2.4)) * 10 + ease_out(span(t, 2.4, 4.0)) * 4
        if t < 1.0:
            stage = self.figure(g, p, t)
        else:
            stage = self.figure(g, 0.999, t, run=t < 2.0, s=s, cy=cy, extra_rot=a_extra)
        if t < 2.6:
            self.panel(g, t, stage, n)
            if t > 2.0:
                g.fade(1 - span(t, 2.0, 2.6), (94, 0, 128, 64))
        if t > 3.0:
            g.d.rectangle((0, 45, 127, 63), fill=0)
            typewriter(g, 64, 48, "一阴一阳之谓道", t - 3.0, cps=6, align="center")
        mx_taiji(g, a_extra + p * 6)
        if t < 1.0 and p0 < 0.75:
            g.mx[:, :] = False
            self.mx(g, t, amp=3)
        g.mx_level = 1 + int(4 * span(t, 1.0, 2.0) * (1 - span(t, 2.4, 4.0)))
