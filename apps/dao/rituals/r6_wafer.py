"""晶圆炼丹：太上老君的八卦炉里放的不是铅汞，是一片晶圆。炉火（点环）里光刻光斑一格格曝光芯片，
一轮炼满一片，切割出片，再放一片——“九转”变成第几片晶圆。

依据：外丹术“九转还丹”（《抱朴子·金丹》：“九转之丹，服之三日得仙”），八卦炉见《西游记》第七回老君炼丹。
入场：八卦一卦一卦亮起合成炉，炉火点燃，晶圆从左边推进炉心，光斑对准第一颗芯片。
持续：光斑按蛇形顺序逐颗曝光（一轮 10 分钟曝光完一整片），八卦炉缓缓转，炉火明灭；右下读数“已曝光/总数”。
      一片曝满：切割线扫过晶圆，整片推出炉外，新晶圆推进来，“第几转”加一。
中断：八卦炉减速停转，炉火熄，两片快门从两侧合上盖住晶圆，“封炉”。
恢复：快门打开，炉火重燃，光斑归位继续曝光。
圆满：剩下的芯片一口气曝完，整片一闪，其余芯片散去，中间一颗长成带引脚的芯片“丹”，炉散开放光，“九转丹成”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from .r6_common import num as cn_num, vlabel
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import bagua_ring
from .r6_common import glow_rays, tiny

CX, CY = 64, 32
WR = 16          # 晶圆半径
RENEW = 5.0


def _dies():
    out = []
    for j in range(-3, 4):
        row = []
        for i in range(-3, 4):
            if math.hypot(abs(i * 4) + 2, abs(j * 4) + 2) <= WR - 0.5:
                row.append((i * 4, j * 4))
        if j % 2:
            row.reverse()  # 蛇形扫描
        out += row
    return out


DIES = _dies()
N = len(DIES)


def wafer(g: Gfx, x: float, y: float, done: float, cut: float = 0.0, flash: bool = False):
    """晶圆：done = 已曝光颗数（小数）；cut：切割线进度"""
    g.d.ellipse((x - WR, y - WR, x + WR, y + WR), outline=1, fill=1 if flash else 0)
    g.d.polygon([(x - 2, y + WR), (x + 2, y + WR), (x, y + WR - 2)], fill=0)  # 缺口
    if flash:
        return
    k = int(done)
    for n, (dx, dy) in enumerate(DIES):
        cx, cy = x + dx, y + dy
        lit = n < k
        if cut > 0 and abs((dx + dy) / 8 + 3 - cut * 8) < 0.7:  # 出炉前一道光波扫过
            lit = not lit
        if lit:
            g.d.rectangle((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
        else:
            g.px(cx, cy)


def crosshair(g: Gfx, x: float, y: float, t: float, r: float = 4):
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        g.d.line((x + sx * r, y + sy * r, x + sx * (r - 2), y + sy * r), fill=1)
        g.d.line((x + sx * r, y + sy * r, x + sx * r, y + sy * (r - 2)), fill=1)
    if blink(t, 0.5, 0.25):  # 曝光闪
        g.d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=1)


def chip(g: Gfx, x: float, y: float, s: float):
    """方形封装芯片（QFP）+ 引脚，中间“丹”"""
    h = 11 * s
    g.d.rectangle((x - h, y - h, x + h, y + h), fill=0, outline=1)
    n = 5
    for i in range(n):
        o = (i - (n - 1) / 2) * h * 2 / (n + 0.5)
        L = 4 * s
        g.d.line((x + o, y - h - L, x + o, y - h - 1), fill=1)
        g.d.line((x + o, y + h + 1, x + o, y + h + L), fill=1)
        g.d.line((x - h - L, y + o, x - h - 1, y + o), fill=1)
        g.d.line((x + h + 1, y + o, x + h + L, y + o), fill=1)
    if s > 0.8:
        g.d.ellipse((x - h + 2, y + h - 5, x - h + 4, y + h - 3), fill=1)  # 1 脚标记
        g.text(x, y - 6, "丹", align="center")


@register
class Wafer(Ritual):
    id = "r6.wafer"
    name = "晶圆炼丹"
    desc = "八卦炉里放一片晶圆，光斑逐颗曝光芯片，一片炼满切割出炉再放一片，圆满时炼出一颗芯片“丹”"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.8, "complete": 5.2}
    CYCLE = 600.0

    def setup(self):
        self.rot0 = self.rng.random() * math.pi * 2

    def done(self, e: float) -> float:
        return (e % self.CYCLE) / self.CYCLE * N

    def rot(self, t: float, e: float) -> float:
        return self.rot0 + e * 0.05 + t * 0.0

    def furnace(self, g: Gfx, t: float, e: float, fire: float = 1.0, rot: float | None = None, show=None,
                r: float = 21):
        bagua_ring(g, CX, CY, r, rot=self.rot(t, e) if rot is None else rot, w=9, show=show)
        if fire > 0:  # 炉火：明灭的点环
            n = 40
            for i in range(n):
                a = i / n * 2 * math.pi + t * 0.7
                if noise(t * 4 + i * 1.3, self.seed + i) < 1 - fire * 0.75:
                    continue
                rr = 18.5 + noise(t * 3 + i, self.seed) * 1.5
                g.px(CX + math.cos(a) * rr, CY + math.sin(a) * rr)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        left = "九转金丹"
        g.vtext(3, 4, left[:int(round(a * 4))])
        n = int(e // self.CYCLE) + 1
        r = right if right is not None else vlabel(n, "转")
        g.vtext(113, 4, r[:int(round(a * len(r)))])

    def readout(self, g: Gfx, done: float):
        tiny(g, 126, 58, f"{int(done)}/{N}", align="right")

    def mx(self, g: Gfx, done: float, t: float, cursor: bool = True):
        # 点阵：6×6 的小晶圆，按比例点亮
        cells = [(x, y) for y in range(1, 7) for x in range(1, 7) if not ((x in (1, 6)) and (y in (1, 6)))]
        k = int(done / N * len(cells))
        for i, (x, y) in enumerate(cells):
            if i < k:
                g.mx[y, x] = True
            elif i == k and cursor:
                g.mx[y, x] = blink(t, 0.5, 0.5)
        g.mx[0, 2:6] = g.mx[7, 2:6] = True
        g.mx[2:6, 0] = g.mx[2:6, 7] = True

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, e: float, cursor: bool = True):
        d = self.done(e)
        self.furnace(g, t, e)
        wafer(g, CX, CY, d)
        if cursor and int(d) < N:
            dx, dy = DIES[int(d)]
            crosshair(g, CX + dx, CY + dy, t)
        self.texts(g, e)
        self.readout(g, d)
        self.mx(g, d, t)

    def enter(self, g: Gfx, t: float):
        k = span(t, 0.0, 1.6)
        self.furnace(g, t, 0, fire=ease_out(span(t, 1.4, 2.0)), rot=self.rot(0, 0) - (1 - ease_out(k)) * 2,
                     show=lambda i: i < k * 8.5)
        wx = lerp(-20, CX, ease_out_back(span(t, 2.0, 3.0)))
        if t > 2.0:
            wafer(g, wx, CY, 0)
        if t > 3.0:
            dx, dy = DIES[0]
            crosshair(g, CX + dx, CY + dy, t, r=4 + 6 * (1 - ease_out(span(t, 3.0, 3.5))))
            self.readout(g, 0)
        self.texts(g, 0, a=span(t, 2.6, 3.8))
        g.mx[0, 2:6] = g.mx[7, 2:6] = k > 0.5
        g.mx[2:6, 0] = g.mx[2:6, 7] = k > 0.9
        if t > 3.0:
            self.mx(g, 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, e, t)
            return
        self.frame(g, t, e)

    def _renew(self, g: Gfx, k: float, e: float, t: float):
        n = int(e // self.CYCLE)
        self.furnace(g, t, e)
        if k < 2.4:
            out = ease_in(span(k, 1.2, 2.4))
            wafer(g, CX + out * 90, CY, N, cut=span(k, 0.0, 1.0))
            self.texts(g, e, right=vlabel(n, "转"))
            self.readout(g, N)
            self.mx(g, N, t, cursor=False)
            g.mx_level = 3 if k < 1.0 and blink(k, 0.2, 0.5) else 1
        else:
            wx = lerp(-20, CX, ease_out_back(span(k, 2.6, 3.6)))
            wafer(g, wx, CY, 0)
            if k > 3.8:
                dx, dy = DIES[0]
                crosshair(g, CX + dx, CY + dy, t, r=4 + 6 * (1 - ease_out(span(k, 3.8, 4.4))))
            self.texts(g, e)
            self.readout(g, 0)
            self.mx(g, 0, t, cursor=k > 3.8)

    def _shut(self, g: Gfx, t: float, e: float, c: float, fire: float, spin: float):
        d = self.done(e)
        self.furnace(g, t, e, fire=fire, rot=self.rot(0, e) + spin)
        wafer(g, CX, CY, d)
        if c > 0:  # 炉盖从上面落下盖住晶圆
            y = lerp(-WR - 4, CY, c)
            r = WR + 1
            g.d.ellipse((CX - r, y - r, CX + r, y + r), fill=0, outline=1)
            g.d.ellipse((CX - r + 2, y - r + 2, CX + r - 2, y + r - 2), outline=1)
            g.d.ellipse((CX - 8, y - 8, CX + 8, y + 8), outline=1)
            for i in range(8):
                a = i / 8 * 2 * math.pi + 0.39
                g.d.line((CX + math.cos(a) * 9, y + math.sin(a) * 9, CX + math.cos(a) * 13, y + math.sin(a) * 13),
                         fill=1)
            g.d.ellipse((CX - 3, y - 3, CX + 3, y + 3), fill=1)  # 炉钮
        self.readout(g, d)
        return d

    def interrupt(self, g: Gfx, t: float, e: float):
        T = self.T["interrupt"]
        spin = 0.6 * ease_out(span(t, 0.0, 1.0))
        from ..engine.anim import ease_out_bounce
        d = self._shut(g, t, e, ease_out_bounce(span(t, 0.3, 1.1)), 1 - span(t, 0.0, 0.8), spin)
        if t < 0.4 and int(d) < N:
            dx, dy = DIES[int(d)]
            crosshair(g, CX + dx, CY + dy, t)
        self.texts(g, e, right="封炉")
        self.mx(g, d, t, cursor=False)
        if t > 1.2:
            g.mx[1:7, 1:7] = False
            g.mx[1:7, 3:5] = True

    def resume(self, g: Gfx, t: float, e: float):
        c = 1 - ease_in(span(t, 0.0, 0.7))
        d = self._shut(g, t, e, c, span(t, 0.6, 1.4), 0.6 * (1 - ease_in_out(span(t, 0.4, 1.8))))
        if t > 1.0 and int(d) < N:
            dx, dy = DIES[int(d)]
            crosshair(g, CX + dx, CY + dy, t, r=4 + 6 * (1 - ease_out(span(t, 1.0, 1.5))))
        self.texts(g, e)
        self.mx(g, d, t, cursor=t > 1.0)

    def complete(self, g: Gfx, t: float, e: float):
        d0 = self.done(e)
        d = lerp(d0, N, ease_in(span(t, 0.0, 1.0)))
        spread = ease_in(span(t, 2.2, 4.0))
        self.furnace(g, t, e, fire=1 - span(t, 1.0, 2.0), rot=self.rot(0, e) + t * t * 0.6, r=21 + spread * 40)
        if t < 1.3:
            wafer(g, CX, CY, d, flash=1.0 < t < 1.15)
            if t < 1.0 and int(d) < N:
                dx, dy = DIES[int(d)]
                crosshair(g, CX + dx, CY + dy, t * 3)
        elif t < 2.2:  # 其余芯片散开、淡去，中间一颗留下
            k = ease_in(span(t, 1.3, 2.2))
            for n, (dx, dy) in enumerate(DIES):
                if dx == 0 and dy == 0:
                    continue
                x, y = CX + dx * (1 + k * 3), CY + dy * (1 + k * 3) + k * k * 20
                if rand(n, 3) > k:
                    g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
            g.d.ellipse((CX - WR, CY - WR, CX + WR, CY + WR), outline=1) if k < 0.3 else None
            g.d.rectangle((CX - 1, CY - 1, CX + 1, CY + 1), fill=1)
        if t >= 2.0:
            s = ease_out_back(span(t, 2.0, 3.0))
            cy = CY - 4 * span(t, 3.0, 3.6)
            if t > 2.6:
                glow_rays(g, CX, cy, 20, 20 + 8 * ease_out(span(t, 2.6, 3.4)), 16, t * 0.6)
            chip(g, CX, cy, max(s, 0.1))
        if t < 1.6:
            self.texts(g, e, a=1 - span(t, 1.0, 1.6))
            self.readout(g, d)
        if t > 3.4:
            g.d.rectangle((30, 49, 98, 62), fill=0)
            typewriter(g, CX, 50, "九转丹成", t - 3.4, cps=5, align="center")
        # 点阵
        if t < 2.0:
            self.mx(g, d, t)
            g.mx_level = 6 if 1.0 < t < 1.3 else 1
        else:
            g.mx_rows([0b00100100, 0b01111110, 0b11000011, 0b01011010, 0b01011010, 0b11000011, 0b01111110,
                       0b00100100])
            g.mx_level = 1 + int(4 * (1 - span(t, 2.4, 4.0)))
