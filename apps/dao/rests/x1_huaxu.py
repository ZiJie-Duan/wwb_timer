"""华胥梦游：卧在一朵祥云上，神游华胥氏之国——仙山、云海一层层从身边流过，白鹤相伴，
不时飞过一座写着“华胥”的牌坊。

依据：《列子·黄帝》：“（黄帝）昼寝，而梦游于华胥氏之国。华胥氏之国在弇州之西，台州之北，不知斯齐国几千万里，
盖非舟车足力之所及，神游而已。其国无帅长，自然而已；其民无嗜欲，自然而已。”后以“华胥梦”称美梦、梦境。
"""
from __future__ import annotations

import math

from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import stars, typewriter, xiangyun
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_chentuan import CRANE_R
from .x1_common import Pen, breathe, ev, halo, iris, mx_zzz, zzz

V = 9.0            # 前景流速（像素/秒）
RIDE = (22, 13)    # 祥云左上角
SW = 256           # 远景条带宽


class Strip:
    """可循环平移的一条风景（透明处不盖底）"""

    def __init__(self, pen: Pen):
        self.spr = pen.sprite()
        self.w = self.spr.w

    def draw(self, g: Gfx, off: float, y: int = 0):
        x = -int(off) % self.w
        g.blit(self.spr, x - self.w, y)
        if x < 128:
            g.blit(self.spr, x, y)


def _far() -> Strip:
    """远景：浮在云海上的仙山，山上有亭"""
    p = Pen(SW, 40)
    for i, (x, w, h) in enumerate(((20, 30, 22), (92, 22, 16), (150, 40, 28), (214, 26, 18))):
        top = 34 - h
        pts = [(x, 34), (x + w * 0.2, top + 6), (x + w * 0.4, top), (x + w * 0.55, top + 4), (x + w * 0.7, top + 2),
               (x + w, 34)]
        p.poly(pts, fill=0.12)
        if i % 2 == 0:  # 山顶小亭
            cx = x + w * 0.4
            p.poly([(cx - 5, top - 1), (cx, top - 5), (cx + 5, top - 1)], fill=1)
            p.line([(cx - 3, top - 1), (cx - 3, top + 1)])
            p.line([(cx + 3, top - 1), (cx + 3, top + 1)])
    # 云海
    for x in range(0, SW, 16):
        p.arc((x, 30, x + 16, 40), 180, 360)
    p.line([(0, 35), (SW, 35)], 0)
    return Strip(p)


def _sea() -> Strip:
    """近一层的云海：卷云纹"""
    p = Pen(SW, 14)
    p.rect((0, 6, SW - 1, 13), fill=0, outline=None)
    for x in range(0, SW, 24):
        p.arc((x, 2, x + 24, 12), 180, 360)
        p.arc((x + 8, 4, x + 16, 10), 0, 300)
    for x in range(6, SW, 12):
        p.px(x, 10)
    return Strip(p)


def _cloud() -> Sprite:
    """坐骑：一朵祥云"""
    p = Pen(64, 18)
    p.blob([(2, 6, 22, 17), (14, 2, 36, 16), (30, 4, 50, 17), (44, 7, 62, 17)], fill=0)
    for x, y in ((12, 11), (28, 8), (44, 11)):
        p.arc((x - 4, y - 3, x + 4, y + 3), 160, 470)
    p.line([(4, 15), (60, 15)], 0)
    return p.sprite()


def _sleeper() -> Sprite:
    """侧卧在云上的人：头枕臂，宽袍"""
    p = Pen(46, 14)
    y0 = 13
    p.poly([(10, 6), (18, 3), (30, 2), (38, 4), (44, 9), (45, y0), (10, y0)], fill=0.25)
    p.line([(24, 3), (23, y0)])
    p.poly([(14, 5), (26, 4), (30, 8), (18, 10)], fill=0)        # 搭在身上的袖
    p.ellipse((1, 2, 11, 12), fill=0)                             # 头
    p.ellipse((0, 0, 5, 5), fill=1)                               # 发髻
    p.line([(4, 7), (6, 7)])                                      # 合眼
    p.rect((41, 9, 45, y0), fill=1)                               # 鞋
    return p.sprite()


GATE_W = 44


def _gate() -> Sprite:
    """牌坊：两柱一额，额上“华胥”"""
    p = Pen(GATE_W, 34)
    p.poly([(0, 6), (6, 0), (38, 0), (44, 6)], fill=1)            # 屋檐
    p.line([(4, 6), (40, 6)], 0)
    p.rect((12, 7, 32, 18), fill=0)                               # 匾
    for x in (6, 36):
        p.rect((x - 2, 7, x + 2, 33), fill=0.5)
    p.line([(2, 22), (42, 22)])
    return p.sprite()


_A = {}


def _assets():
    if not _A:
        _A.update(far=_far(), sea=_sea(), cloud=_cloud(), man=_sleeper(), gate=_gate())


@register
class Huaxu(Rest):
    id = "x1.huaxu"
    name = "华胥梦游"
    desc = "卧在祥云上神游华胥国：仙山云海层层流过，白鹤伴飞，偶有“华胥”牌坊迎面掠过"
    T = {"enter": 3.0, "exit": 1.3}
    PRE = 0.7      # 入场结束时已经走过的“距离”（秒）

    def setup(self):
        _assets()
        self._ht = 0.0

    # ------------------------------------------------------------ 零件

    def world(self, g: Gfx, pos: float, t: float):
        """pos：走过的距离（以前景秒计）"""
        stars(g, t, self.seed, n=12, box=(0, 0, 128, 34), twinkle=0.45)
        g.d.ellipse((104, 3, 114, 13), outline=1)                     # 月
        g.d.arc((106, 5, 112, 11), 100, 200, fill=1)
        _A["far"].draw(g, pos * V * 0.25, 22)
        _A["sea"].draw(g, pos * V * 0.6, 50)

    def streaks(self, g: Gfx, pos: float):
        """掠过的风/云丝"""
        for i in range(5):
            y = 6 + int(rand(i, 3) * 44)
            x = (rand(i, 4) * 200 - pos * V * (1.4 + rand(i, 5))) % 200 - 40
            g.d.line((x, y, x + 8 + i * 2, y), fill=1)

    def rider(self, g: Gfx, t: float, x: float = RIDE[0], y: float | None = None, ribbon: float = 1.0):
        bob = math.sin(t * 0.9) * 1.5
        y = (RIDE[1] if y is None else y) + bob
        # 飘带：从身后往后飘
        for k in range(2):
            pts = []
            for i in range(9):
                q = i / 8
                pts.append((x + 14 - q * 24 * ribbon, y + 6 + k * 3 + math.sin(t * 3 + q * 5 + k) * 2.5 * q))
            g.d.line(pts, fill=1)
        g.blit(_A["cloud"], x - 6, y + 9)
        g.blit(_A["man"], x + 2, y + (0 if breathe(t) > 0.5 else 1) - 3)

    def gate(self, g: Gfx, u: float, t: float):
        """牌坊从右边飘近、掠过（u = 事件内秒数，共 11 秒）"""
        x = lerp(132, -GATE_W - 4, u / 11)
        y = 20 + math.sin(u * 0.8) * 1.5
        g.blit(_A["gate"], x, y)
        g.text(x + 22, y + 9, "华胥", size=8, align="center")

    def mx_flow(self, g: Gfx, pos: float):
        off = int(pos * 3)
        for x in range(8):
            g.mx[6, x] = (x + off) % 4 != 0
            g.mx[7, x] = (x + off // 2) % 3 != 0
        mx_zzz(g, pos)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        """云载着人从左边飘进来，然后起风前行"""
        ramp = span(t, 1.6, 3.0)
        pos = (t - 1.6) ** 2 / 2.8 if t > 1.6 else 0.0
        self.world(g, pos, t)
        if ramp > 0:
            self.streaks(g, pos)
        k = ease_out(span(t, 0, 1.6))
        self.rider(g, t, x=lerp(-60, RIDE[0], k), ribbon=0.3 + 0.7 * ramp)
        if t > 1.8:
            zzz(g, RIDE[0] + 8, RIDE[1] - 2, t - 1.8, self.seed, rise=14, drift=-10, s0=1, s1=4)
        self.mx_flow(g, pos)
        if t < 0.5:
            iris(g, 64, 32, ease_out(t / 0.5) * 150, 0.6)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        pos = t + self.PRE
        te = t + self.T["enter"]          # 氛围动作接着入场的时间走，不跳
        self.world(g, pos, te)
        gate = ev(t, 83.0, 11.0, 30.0)
        if gate:
            self.gate(g, gate[1], t)
        self.streaks(g, pos)
        crane = ev(t, 47.0, 14.0, 10.0)        # 白鹤赶上来，伴飞一程
        if crane:
            u = crane[1]
            if u < 3:
                cx = lerp(-20, 78, ease_out(u / 3))
            elif u < 10:
                cx = 78 + math.sin(u) * 4
            else:
                cx = lerp(78, 140, ease_in((u - 10) / 4))
            cy = 4 + math.sin(u * 1.7) * 3
            g.blit(CRANE_R[int(te * 4) % 2], cx, cy)
        self.rider(g, te)
        zzz(g, RIDE[0] + 8, RIDE[1] - 2, te - 1.8, self.seed, rise=14, drift=-10, s0=1, s1=4)
        txt = ev(t, 110.0, 8.0, 55.0)
        if txt:
            g.d.rectangle((62, 0, 127, 13), fill=0)
            typewriter(g, 126, 1, "神游而已", txt[1], cps=4, align="right")
        elif gate and 4.0 < gate[1] < 11.0:
            g.d.rectangle((62, 0, 127, 13), fill=0)
            typewriter(g, 126, 1, "自然而已", gate[1] - 4.0, cps=4, align="right")
        self.mx_flow(g, pos)

    def exit(self, g: Gfx, t: float):
        """醒来：风停，云散，人往下一沉，画面收拢"""
        h = self._ht + self.T["enter"]
        slow = 1 - ease_out(span(t, 0, 0.6))
        pos = self._ht + self.PRE + t * slow
        self.world(g, pos, h + t)
        sink = ease_in(span(t, 0.2, 1.0)) * 10
        self.rider(g, h + t, y=RIDE[1] + sink, ribbon=0.3 + 0.7 * slow)
        hx, hy = RIDE[0] + 6, RIDE[1] + sink + 4
        if t > 0.3:  # 睁眼
            g.d.rectangle((hx, hy - 1, hx + 1, hy), fill=1)
        self.mx_flow(g, pos)
        iris(g, hx, hy, lerp(130, 0, ease_in_out(span(t, 0.35, self.T["exit"] - 0.05))), 0.8)
