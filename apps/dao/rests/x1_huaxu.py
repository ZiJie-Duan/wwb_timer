"""华胥梦游：夜里，小道士侧卧支颐在一朵祥云上睡着，飘带往后扬，梦游到华胥氏之国。

依据：《列子·黄帝》：“（黄帝）昼寝，而梦游于华胥氏之国。华胥氏之国在弇州之西，台州之北，不知斯齐国几千万里；
盖非舟车足力之所及，神游而已。其国无帅长，自然而已；其民无嗜欲，自然而已。”后以“华胥梦”称梦境。

入场：一朵祥云载着侧卧的小道士从左边飘进来，起风，飘带往后扬，风景开始流动。
持续：夜空、弯月、星；三层视差：远处浮在云海上的仙山（山顶小亭、松）慢慢后退，近处卷云纹云海快些，风丝最快；
      他卧在祥云上轻轻起伏、飘带翻飞、冒 Z。
      小事件（每 150 秒一轮）：白鹤赶上来伴飞一程再飞走（47s）；一座写着“华胥”的牌坊迎面飘来，从身边掠过，
      “自然而已”（83s）；“神游而已”（110s）。
退场：风停，飘带垂下，云往下一沉，睁眼，画面收拢。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x1_common import cached, crane_fly, ev, iris, plate, recline, twinkle, zzz

RIDE_X, RIDE_Y = 26, 44     # 祥云顶面左端
EV = 150.0


def _ride_cloud():
    """载人的祥云 60×13：白底，几团云头，暗线卷云纹，左边拖一条云尾，底边一排网点"""
    p = Part(60, 13)
    for b in ((0, 5, 12, 12), (8, 1, 24, 12), (20, 0, 38, 12), (34, 2, 50, 12), (46, 4, 59, 12)):
        p.shape("ellipse", b, fill=1)
    for cx, cy in ((16, 6), (29, 5), (42, 6)):
        p.d.arc((cx - 3, cy - 3, cx + 3, cy + 3), 160, 470, fill=0)
        p.px(cx, cy, 0)
    p.d.arc((50, 6, 56, 12), 180, 330, fill=0)
    p.d.line((2, 10, 57, 10), fill=0)
    p.dither([(3, 11), (57, 11), (57, 12), (3, 12)], 0.5, 0)
    return p.sprite()


def _island():
    """浮在云上的仙山 34×26：两座尖峰，峰顶一座小亭（攒尖顶），崖边一棵斜松，山脚收成倒锥，挂着几缕云"""
    p = Part(34, 26)
    p.shape("polygon", [(0, 17), (6, 9), (10, 11), (16, 2), (21, 8), (25, 6), (33, 17), (26, 22), (18, 25), (11, 22)],
            fill=0)
    p.d.line([(0, 17), (6, 9), (10, 11), (16, 2), (21, 8), (25, 6), (33, 17)], fill=1)
    p.d.line([(0, 17), (11, 22), (18, 25), (26, 22), (33, 17)], fill=1)
    p.d.line((16, 4, 15, 12), fill=1), p.d.line((25, 8, 26, 13), fill=1), p.d.line((7, 11, 8, 15), fill=1)
    p.dither([(4, 18), (30, 18), (18, 24)], 0.25, 1)
    # 小亭
    p.shape("polygon", [(12, 0), (16, -3), (20, 0)], fill=1)
    p.shape("rectangle", (13, 0, 19, 0), fill=1)
    p.d.line((16, -4, 16, -3), fill=1)
    p.shape("line", (14, 1, 14, 3), fill=1), p.shape("line", (18, 1, 18, 3), fill=1)
    # 斜松
    p.d.line((27, 9, 31, 5), fill=1)
    p.shape("polygon", [(29, 4), (34, 3), (33, 6)], fill=1)
    p.shape("polygon", [(27, 6), (31, 6), (30, 8)], fill=1)
    # 山腰的云带
    p.shape("ellipse", (2, 14, 14, 19), fill=1)
    p.shape("ellipse", (9, 15, 20, 20), fill=1)
    p.d.line((4, 18, 18, 18), fill=0)
    return p.sprite()


def _arch():
    """牌坊 46×34：两根柱、夹杆石，两层檐（檐角起翘、瓦垄），中间一块匾（留空写“华胥”）"""
    p = Part(46, 34)
    for x in (6, 37):
        p.shape("rectangle", (x, 8, x + 3, 33), fill=1)
        p.d.line((x + 2, 10, x + 2, 31), fill=0)
        p.shape("rectangle", (x - 2, 28, x + 5, 33), fill=1)
        p.d.line((x - 1, 30, x + 4, 30), fill=0)
    p.shape("polygon", [(0, 3), (3, 4), (42, 4), (45, 3), (44, 7), (1, 7)], fill=1)   # 上檐
    for x in range(4, 42, 3):
        p.px(x, 5, 0), p.px(x, 6, 0)
    p.shape("rectangle", (16, 0, 29, 3), fill=1)                                       # 正脊
    p.px(16, 0, 0), p.px(29, 0, 0)
    p.shape("rectangle", (4, 8, 41, 9), fill=1)                                        # 额枋
    p.shape("rectangle", (7, 10, 38, 24), fill=0)                                      # 匾
    p.d.rectangle((7, 10, 38, 24), outline=1)
    p.px(7, 10, 0), p.px(38, 10, 0), p.px(7, 24, 0), p.px(38, 24, 0)
    p.shape("rectangle", (4, 25, 41, 26), fill=1)
    return p.sprite()


def ribbon(g: Gfx, x: float, y: float, t: float, wind: float = 1.0, n: int = 16):
    """飘带：从肩后拖出的两股带子，随风翻飞（wind 0 垂下 → 1 平飞）"""
    for k in range(2):
        pts = []
        for i in range(n):
            q = i / (n - 1)
            px = x - i * 1.6 * (0.3 + 0.7 * wind) + (0 if wind > 0.5 else q * 2)
            py = y + k * 2 + math.sin(t * 6 - i * 0.6 + k) * (0.4 + q * 2.4) * wind + q * q * 14 * (1 - wind)
            pts.append((px, py))
        g.d.line(pts, fill=1)


@register
class HuaXuRest(Rest):
    id = "x1.huaxu"
    name = "华胥梦游"
    desc = "夜空里小道士侧卧在祥云上睡着，飘带翻飞，云海和浮在云上的仙山往后流；白鹤伴飞、华胥牌坊迎面掠过"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.ph = self.rng.random() * 100

    # ------------------------------------------------------------ 景

    def sky(self, g: Gfx, t: float):
        g.d.ellipse((102, 3, 112, 13), fill=1)               # 弯月
        g.d.ellipse((99, 1, 109, 11), fill=0)
        for i in range(16):
            x = int(rand(i, 61) * 128)
            y = int(rand(i, 62) * 24) + 1
            if not (96 < x < 116 and y < 16):
                twinkle(g, x, y, t, i, big=i % 5 == 0)

    def far(self, g: Gfx, t: float, speed: float = 1.0):
        """远处的仙山（慢）"""
        isl = cached("isl", _island)
        for i in range(2):
            x = (i * 90 - (t + self.ph) * 2.2 * speed) % 180 - 40
            pix.blit(g, isl, x, 8 + i * 5)

    def sea(self, g: Gfx, t: float, speed: float = 1.0):
        """近处的云海（快）：一排卷云头往左流，底下网点"""
        off = ((t + self.ph) * 9 * speed) % 24
        pix.checker(g, (0, 57, 128, 64), 0.25)
        for i in range(-1, 7):
            x = i * 24 - off
            g.d.ellipse((x - 2, 50, x + 16, 62), fill=0, outline=1)
            g.d.arc((x + 3, 53, x + 9, 59), 180, 470, fill=1)
            g.px(x + 6, 56)
        g.d.rectangle((0, 58, 127, 63), fill=0)
        pix.checker(g, (0, 59, 128, 64), 0.25)

    def wind(self, g: Gfx, t: float, k: float = 1.0):
        """风丝（最快）"""
        for i in range(5):
            y = 14 + int(rand(i, 71) * 40)
            x = 140 - ((t * 60 + rand(i, 72) * 200) % 200)
            ln = int(6 + rand(i, 73) * 8 * k)
            if k > 0.1:
                g.d.line((x, y, x + ln, y), fill=1)

    def rider(self, g: Gfx, t: float, face: str = "sleep", wind: float = 1.0, dip: float = 0.0):
        bob = math.sin(t * 0.9) * 1.5 + dip
        x, y = RIDE_X, RIDE_Y + bob
        h = recline(g, x + 4, y + 1, t, face=face)
        ribbon(g, x + 18, y - 17, t, wind)
        pix.blit(g, cached("ride", _ride_cloud), x - 2, y - 1)
        return h

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        self.sky(g, t)
        self.far(g, t)
        arch = ev(t, EV, 83.0, 12.0)
        ax = None
        if arch is not None:   # 牌坊从右边迎面飘来，掠过身边
            ax = lerp(132, -50, arch / 7.0)
            if arch < 7.0:
                pix.blit(g, cached("arch", _arch), ax, 14)
        self.sea(g, t)
        h = self.rider(g, t)
        zzz(g, h["mouth"][0] + 4, h["mouth"][1] - 4, t, n=3, period=2.8, dx=14, dy=-12)
        c = ev(t, EV, 47.0, 14.0)
        if c is not None:      # 白鹤赶上来伴飞，再飞到前面去
            if c < 3:
                q = ease_out(c / 3)
                x, y = lerp(-20, 92, q), lerp(30, 22, q)
            elif c < 10:
                x, y = 92 + math.sin(c * 0.8) * 3, 22 + math.sin(c * 1.3) * 2
            else:
                q = ease_in((c - 10) / 4)
                x, y = lerp(92, 150, q), lerp(22, 6, q)
            crane_fly(g, x, y, t)
        self.wind(g, t)
        if arch is not None and arch < 7.0 and ax is not None and -10 <= ax <= 92 and (ax + 8 > 84 or ax + 37 < 20):
            g.d.rectangle((ax + 8, 14 + 11, ax + 37, 14 + 23), fill=0)    # 匾心（牌坊画在 y=14）
            g.text(ax + 23, 14 + 12, "华胥", align="center")
        if arch is not None and 3.0 < arch < 12.0:
            plate(g, 125, 3, "自然而已", k=span(arch, 3.0, 3.4), align="right")
        w = ev(t, EV, 110.0, 8.0)
        if w is not None:
            plate(g, 125, 3, "神游而已", k=span(w, 0, 0.4), align="right")
        self.matrix(g, t)

    def matrix(self, g: Gfx, t: float, speed: float = 1.0):
        off = int(t * 4 * speed)
        for x in range(8):
            g.mx[7, x] = True
            g.mx[6, x] = (x + off) % 4 != 0
            g.mx[5, x] = (x + off) % 4 == 1
        g.mx[3, 2:6] = True                      # 云上的人
        g.mx[2, 2] = g.mx[2, 3] = True
        k = (t / 2.8) % 1
        zx, zy = 4 + int(k * 3), 1 - int(k * 2)
        g.mx_set(zx, zy), g.mx_set(zx + 1, zy)

    def enter(self, g: Gfx, t: float):
        """祥云载着他从左边飘进来，起风"""
        k = ease_out(span(t, 0, 2.4))
        st = t - self.T["enter"]          # 景的时间：入场最后一帧正好接上 hold(0)
        self.sky(g, st)
        self.far(g, st)
        self.sea(g, st)
        global RIDE_X
        x0 = RIDE_X
        RIDE_X = int(lerp(-70, x0, k))
        try:
            self.rider(g, st, wind=span(t, 1.0, 2.6))
        finally:
            RIDE_X = x0
        self.wind(g, st, span(t, 1.2, 2.6))
        self.matrix(g, t, k)
        iris(g, 60, 32, lerp(8, 150, ease_out(span(t, 0, 1.0))))

    def exit(self, g: Gfx, t: float):
        """风停，飘带垂下，云一沉，睁眼"""
        h0 = self.hold_t
        self.sky(g, h0 + t)
        self.far(g, h0)
        self.sea(g, h0)
        w = 1 - span(t, 0, 0.5)
        h = self.rider(g, h0 + t, face="normal" if t > 0.4 else "sleep", wind=w,
                       dip=math.sin(span(t, 0.2, 0.7) * math.pi) * 2)
        self.matrix(g, h0)
        ex, ey = h["eye"]
        iris(g, ex, ey, lerp(140, 0, ease_in_out(span(t, 0.45, self.T["exit"] - 0.05))))
