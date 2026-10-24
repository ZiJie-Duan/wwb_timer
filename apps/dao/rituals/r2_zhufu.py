"""朱砂画符：黄符展开，朱笔按“符头（三清）→ 敕令 → 符身 → 符胆 → 符脚”逐笔写出。

依据：符箓的一般结构（符头多为三清讳、敕令二字，符胆为符之灵，符脚收尾）；画符前以咒敕笔，
“笔点灵朱光，邪魔走茫茫”（敕笔咒）；画毕“以笔头撞符纸三次”，再剑指敕符、盖印。
"""
from __future__ import annotations

import math

from ..engine.anim import (blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp,
                           noise, rand, span)
from ..engine.cn import cn_num
from ..engine.fx import flame, smoke_wisp, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import brush, glyph_reveal, mx_fu, paper, point_hand, poly_len, polyline_part, rays, spiral

PX0, PY0, PX1, PY1 = 46, 2, 82, 61     # 符纸
CX = 64
DISH = (28, 56)                         # 朱砂碟
REST = (30, 54, -1.3)                  # 笔搁在碟里：笔尖、笔杆角度
CANDLE_X = 98
LEAD = 5.0                              # 每轮开头（续符过渡 / 空白符纸）
SLOT = 23.0                             # 每一笔的时间槽
RENEW = 4.5


def _hook(c):
    return [(c - 1, 5), (c + 1, 6.5), (c, 8.5), (c - 1, 10.5), (c + 1, 12.5)]


def _curl(x, flip):
    s = -1 if flip else 1
    return [(x + s, 15), (x - s, 18), (x + s, 22), (x - s, 26), (x + s, 30), (x - s, 34), (x + 2 * s, 37)]


# 笔画：(类型, 数据, 线宽)。"line" = 折线，"char" = 一个字 (字, x, y)
STROKES = [
    ("line", _hook(57), 1),                 # 符头：三清（三勾）
    ("line", _hook(64), 1),
    ("line", _hook(71), 1),
    ("char", ("敕", 58, 14), 1),
    ("char", ("令", 58, 26), 1),
    ("line", _curl(51, False), 1),          # 左右护法纹
    ("line", _curl(77, True), 1),
    ("line", [(64, 38), (58, 40), (70, 42), (58, 44), (64, 46.5)], 1),   # 符身：雷纹
    ("line", spiral(64, 50.5, 4.0, turns=2.0, start=-math.pi / 2), 1),  # 符胆
    ("line", [(64, 54.5), (64, 57), (59, 58.5), (71, 59)], 2),           # 符脚
]
N = len(STROKES)
DONE_AT = LEAD + N * SLOT                # 写完
SEAL = (69, 49, 79, 59)                  # 盖印处
PHRASES = ("笔点灵朱光", "邪魔走茫茫")


def _start(s):
    if s[0] == "char":
        ch, x, y = s[1]
        return x + 6, y
    return s[1][0]


def _dur(s):
    if s[0] == "char":
        return 2.4
    return clamp(poly_len(s[1]) / 12, 1.0, 2.6)


@register
class ZhuFu(Ritual):
    id = "r2.zhufu"
    name = "朱砂画符"
    desc = "黄符垂下，朱笔逐笔写出三清符头、敕令、符胆、符脚，撞笔三下、剑指敕符、盖印，符成放光"
    T = {"enter": 4.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.0}
    CYCLE = 300.0

    def setup(self):
        self.glint_seed = self.rng.randrange(1000)

    # ------------------------------------------------------------ 状态

    def state(self, u: float):
        """一轮内 u 秒时：(已完成笔数, 当前笔进度 or None, 笔尖 x, y, 角度)"""
        rx, ry, ra = REST
        if u < LEAD:
            return 0, None, rx, ry, ra
        if u >= DONE_AT:
            return N, None, rx, ry, ra
        i = int((u - LEAD) // SLOT)
        k = (u - LEAD) - i * SLOT
        s = STROKES[i]
        d = _dur(s)
        sx, sy = _start(s)
        if k < 1.0:  # 从碟子提笔到起笔处
            p = ease_in_out(k)
            x, y = lerp(rx, sx, p), lerp(ry, sy, p) - math.sin(p * math.pi) * 10
            return i, None, x, y, lerp(ra, -1.15, p)
        if k < 1.0 + d:  # 行笔
            p = (k - 1.0) / d
            return i, p, None, None, -1.15 + 0.12 * math.sin(p * 9)
        k2 = k - 1.0 - d
        if k2 < 1.0:  # 回碟
            ex, ey = self.stroke_end(s)
            p = ease_in_out(k2)
            return i + 1, None, lerp(ex, rx, p), lerp(ey, ry, p) - math.sin(p * math.pi) * 10, lerp(-1.15, ra, p)
        if k2 < 2.0:  # 蘸朱砂：点两下
            dip = abs(math.sin((k2 - 1.0) * 2 * math.pi)) * 3
            return i + 1, None, rx, ry - dip, ra
        return i + 1, None, rx, ry, ra

    def stroke_end(self, s):
        if s[0] == "char":
            ch, x, y = s[1]
            return x + 6, y + 11
        return s[1][-1]

    # ------------------------------------------------------------ 画面零件

    def draw_fu(self, g: Gfx, done: int, cur: float | None, dx: float = 0, dy: float = 0):
        """画符纸上已写的笔画；cur = 当前笔进度。返回行笔时的笔尖"""
        tip = None
        for i in range(min(done + (cur is not None), N)):
            s = STROKES[i]
            p = cur if (i == done and cur is not None) else 1.0
            if s[0] == "char":
                ch, x, y = s[1]
                tx, ty = glyph_reveal(g, x + dx, y + dy, ch, p)
                if p < 1:
                    tip = (tx, ty)
            else:
                pts = [(x + dx, y + dy) for x, y in s[1]]
                part, end = polyline_part(pts, p)
                if len(part) > 1:
                    g.d.line(part, fill=1, width=s[2], joint="curve")
                if p < 1:
                    tip = end
        return tip

    def dish(self, g: Gfx, dx: float = 0):
        x, y = DISH[0] + dx, DISH[1]
        g.d.ellipse((x - 11, y - 4, x + 11, y + 4), outline=1, fill=0)
        g.d.ellipse((x - 7, y - 2, x + 7, y + 2), fill=1)
        g.d.line((x - 4, y - 1, x + 2, y - 1), fill=0)  # 朱砂的高光
        g.d.line((x - 8, y + 5, x + 8, y + 5), fill=1)  # 碟足

    def candle(self, g: Gfx, t: float, lit: float = 1.0):
        x = CANDLE_X
        g.d.rectangle((x - 3, 46, x + 3, 61), outline=1, fill=0)
        g.d.line((x - 5, 61, x + 5, 61), fill=1)
        g.d.line((x - 1, 47, x - 1, 50), fill=1)  # 烛泪
        g.d.line((x, 45, x, 43), fill=1)
        if lit > 0.05:
            flame(g, x, 43, 4 * lit + 1, 9 * lit, t, self.seed % 97 + 3)
            if lit > 0.8:
                smoke_wisp(g, x, 32, 10, t, self.seed, sway=1.5, speed=4)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0, left: str | None = None):
        n = int(e // self.CYCLE) + 1
        if left is None:
            u = e % self.CYCLE
            left = "急急如律令" if u >= DONE_AT else PHRASES[int(max(u - LEAD, 0) // (SLOT * 5)) % 2]
        k = int(round(a * len(left)))
        g.vtext(2, 2, left[:k])
        r = right if right is not None else f"第{cn_num(n)}道"
        g.vtext(113, 4, r[:max(0, int(round(a * len(r))))])

    def glints(self, g: Gfx, u: float, t: float, done: int):
        """朱砂未干的闪点：已写笔画上随机亮一个小十字"""
        if done <= 0:
            return
        j = int(t / 1.7)
        ph = (t / 1.7) % 1
        if ph > 0.35:
            return
        s = STROKES[int(rand(j, self.glint_seed) * done)]
        if s[0] == "char":
            x, y = s[1][1] + 2 + rand(j + 5, 3) * 8, s[1][2] + 2 + rand(j + 9, 3) * 7
        else:
            x, y = s[1][int(rand(j + 5, 3) * len(s[1]))]
        r = 2 if ph < 0.18 else 1
        g.d.line((x - r, y, x + r, y), fill=1)
        g.d.line((x, y - r, x, y + r), fill=1)

    def seal(self, g: Gfx, p: float = 1.0):
        """盖印：p<1 时印从上方压下"""
        x0, y0, x1, y1 = SEAL
        if p < 1:
            s = 1 + (1 - ease_in(p)) * 1.5
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 - (1 - ease_in(p)) * 14
            hw = (x1 - x0) / 2 * s
            g.d.rectangle((cx - hw, cy - hw, cx + hw, cy + hw), fill=0, outline=1)
            g.d.rectangle((cx - hw + 2, cy - hw + 2, cx + hw - 2, cy + hw - 2), outline=1)
            return
        g.d.rectangle(SEAL, fill=1)
        g.d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), outline=0)
        # 印文（阴刻四格）
        g.d.line((x0 + 3, y0 + 3, x0 + 4, y0 + 3), fill=0)
        g.d.line((x0 + 3, y0 + 3, x0 + 3, y0 + 4), fill=0)
        g.d.line((x1 - 3, y0 + 3, x1 - 4, y0 + 4), fill=0)
        g.d.line((x0 + 3, y1 - 3, x0 + 4, y1 - 4), fill=0)
        g.d.line((x1 - 4, y1 - 3, x1 - 3, y1 - 3), fill=0)
        g.d.line((x1 - 3, y1 - 4, x1 - 3, y1 - 3), fill=0)

    def roll(self, g: Gfx, p: float):
        """符纸自下而上卷起 p（0..1），露出卷轴"""
        if p <= 0.01:
            return
        ry = lerp(PY1, PY0 + 16, p)
        g.d.rectangle((PX0 - 1, ry + 1, PX1 + 1, PY1 + 1), fill=0)
        g.d.rectangle((PX0 - 2, ry - 1, PX1 + 2, ry + 3), fill=1, outline=1)
        g.d.line((PX0, ry + 1, PX1, ry + 1), fill=0)
        g.d.rectangle((PX0 - 4, ry - 1, PX0 - 3, ry + 3), fill=1)
        g.d.rectangle((PX1 + 3, ry - 1, PX1 + 4, ry + 3), fill=1)

    def mx(self, g: Gfx, done: int, writing: bool, t: float):
        rows = done / N * 8
        mx_fu(g, rows, int(rows) if writing and blink(t, 0.3) else None)

    def scene(self, g: Gfx, t: float, u: float, e: float, candle: float = 1.0, brush_override=None):
        """持续阶段一帧（一轮内 u 秒）；返回 (done, writing)"""
        paper(g, PX0, PY0, PX1, PY1, tone=True)
        done, cur, bx, by, ba = self.state(u)
        tip = self.draw_fu(g, done, cur)
        self.dish(g)
        self.candle(g, t, candle)
        if u >= DONE_AT:
            self.finish(g, t, u - DONE_AT)
        else:
            self.glints(g, u, t, done)
        if tip is not None:
            bx, by = tip
            # 行笔时的朱砂飞点
            if rand(int(t * 20), 7) < 0.25:
                g.px(bx + (rand(int(t * 20), 8) - 0.5) * 6, by + 2)
        if brush_override is not None:
            bx, by, ba = brush_override(bx, by, ba)
        if bx is not None:
            brush(g, bx, by, ba, 30)
        return done, cur is not None

    def finish(self, g: Gfx, t: float, k: float):
        """写完之后：撞笔三下、剑指敕符、盖印、放光（k = 写完后的秒数）"""
        if k < 3.4:  # 笔头撞符纸三次（笔倒过来，笔头朝下点）
            p = span(k, 0, 0.6)
            n_tap = int(clamp((k - 0.6) / 0.8, 0, 2.99))
            tk = ((k - 0.6) / 0.8) % 1 if k > 0.6 else 0
            y = lerp(40, 28, ease_out(p)) + (abs(math.sin(tk * math.pi)) * -6 if k > 0.6 else 0)
            brush(g, CX, y, -1.57, 26)
            if k > 0.6 and tk < 0.25 and k < 3.0:
                rays(g, CX, y + 1, 4, 8, 8, phase=n_tap)
        if 3.6 < k < 7.5:  # 剑指从右下来，指符
            p = ease_out_back(span(k, 3.6, 4.4))
            q = ease_in(span(k, 6.6, 7.5))
            hx = lerp(130, PX1 + 4, p) + q * 50
            hy = lerp(44, 30, p) + q * 20
            point_hand(g, hx, hy)
            if 4.4 < k < 6.6:  # 指尖一点光注入符中
                f = (k - 4.4) / 2.2
                for j in range(3):
                    r = ((f * 3 + j / 3) % 1) * 30 + 8
                    rays(g, CX, 31, r, r + 3, 12, phase=j * 0.26, sy=1.3)
                g.d.line((hx - 2, hy, hx - 2 - 4 * (1 - f), hy), fill=1)
        if 7.6 < k:
            self.seal(g, span(k, 7.6, 8.2))
            if k < 8.6 and k > 8.2:
                rays(g, (SEAL[0] + SEAL[2]) / 2, (SEAL[1] + SEAL[3]) / 2, 8, 12, 8)
        if k > 9.0:  # 符成：每隔几秒放一圈光
            ph = (k - 9.0) % 4.0
            if ph < 1.2:
                r = 20 + ph * 14
                rays(g, CX, 31, r, r + 4, 14, phase=k * 0.1, sy=1.3)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        p = ease_out_bounce(span(t, 0, 1.4))
        y1 = lerp(PY0 + 2, PY1, p)
        paper(g, PX0, PY0, PX1, y1, edge=p > 0.95)
        g.d.rectangle((PX0 - 2, y1, PX1 + 2, y1 + 2), fill=1)  # 卷轴木杆
        if t >= 1.4:
            g.d.rectangle((PX0 - 2, y1, PX1 + 2, y1 + 2), fill=0)
            paper(g, PX0, PY0, PX1, PY1)
        g.d.line((PX0 - 4, PY0 - 1, PX1 + 4, PY0 - 1), fill=1)  # 上方挂杆
        dx = -50 * (1 - ease_out(span(t, 0.9, 1.9)))
        self.dish(g, dx)
        lit = ease_out_back(span(t, 2.6, 3.1))
        self.candle(g, t, lit)
        if t > 1.8:
            p = ease_out(span(t, 1.8, 3.0))
            rx, ry, ra = REST
            bx, by = lerp(118, rx, p), lerp(-30, ry, p)
            dip = abs(math.sin(span(t, 3.0, 4.0) * 2 * math.pi)) * 3
            brush(g, bx, by - dip, lerp(-0.6, ra, p), 30)
            if 3.0 < t < 3.3:  # 朱砂溅起
                for j in range(5):
                    a = math.pi + rand(j, 3) * math.pi
                    g.px(DISH[0] + math.cos(a) * 9 * span(t, 3.0, 3.3), DISH[1] - 3 + math.sin(a) * 5)
        self.texts(g, 0, a=span(t, 2.4, 4.0))
        mx_fu(g, 0)
        g.mx_level = 4 if 2.6 < t < 2.8 else 1

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, e)
            return
        self.texts(g, e)
        done, writing = self.scene(g, t, u, e)
        self.mx(g, done, writing, t)
        if u >= DONE_AT + 9.0:
            g.mx_level = 1 + int(2 * (((u - DONE_AT - 9.0) % 4.0) < 0.5))

    def _renew(self, g: Gfx, t: float, u: float, e: float):
        """一道符成：旧符飞走，新符纸垂下"""
        self.dish(g)
        self.candle(g, t)
        rx, ry, ra = REST
        brush(g, rx, ry, ra, 30)
        if u < 1.6:  # 旧符离纸，向上飞走
            p = ease_in(span(u, 0.2, 1.6))
            dy = -p * 70
            paper(g, PX0, PY0 + dy, PX1, PY1 + dy)
            self.draw_fu(g, N, None, 0, dy)
            for j in range(10):  # 尾迹
                yy = PY1 + dy + 2 + rand(j, 4) * 20 * p
                g.px(PX0 + rand(j, 5) * (PX1 - PX0), yy)
            g.d.line((PX0 - 4, PY0 - 1, PX1 + 4, PY0 - 1), fill=1)
            self.texts(g, e - u - 1)
            mx_fu(g, 8 * (1 - p))
            g.mx_level = 1 + int(3 * (1 - p))
            return
        p = ease_out_bounce(span(u, 1.8, 3.2))
        y1 = lerp(PY0 + 2, PY1, p)
        g.d.line((PX0 - 4, PY0 - 1, PX1 + 4, PY0 - 1), fill=1)
        if u > 1.8:
            paper(g, PX0, PY0, PX1, y1, edge=p > 0.95)
            if p < 0.99:
                g.d.rectangle((PX0 - 2, y1, PX1 + 2, y1 + 2), fill=1)
        self.texts(g, e)
        mx_fu(g, 0)

    def interrupt(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        T = self.T["interrupt"]
        rx, ry, ra = REST
        back = ease_in_out(span(t, 0, 0.8))

        def ov(bx, by, ba):
            if bx is None:
                return rx, ry, ra
            return lerp(bx, rx, back), lerp(by, ry, back) - math.sin(back * math.pi) * 6, lerp(ba, ra, back)

        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        lit = 1 - ease_in(span(t, 0.5, 1.1))
        done, _ = self.scene(g, t, u, e, candle=lit, brush_override=ov)
        self.roll(g, ease_in_out(span(t, 0.5, 1.4)))
        if 1.0 < t:  # 烛灭后的一缕烟
            smoke_wisp(g, CANDLE_X, 42, 14 * (1 - span(t, 1.0, T) * 0.6), t, 5, sway=2)
        self.texts(g, e, right="停笔")
        mx_fu(g, done / N * 8)

    def resume(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        rx, ry, ra = REST
        k = ease_in_out(span(t, 1.1, 1.8))

        def ov(bx, by, ba):
            if bx is None:
                return rx, ry, ra
            return lerp(rx, bx, k), lerp(ry, by, k), lerp(ra, ba, k)

        lit = ease_out_back(span(t, 0.2, 0.7))
        done, writing = self.scene(g, t, u, e, candle=lit, brush_override=ov)
        self.roll(g, 1 - ease_out_bounce(span(t, 0.2, 1.2)))
        if t < 0.7:  # 火星引燃
            g.px(CANDLE_X + (1 - t / 0.7) * 8, 43 - (1 - t / 0.7) * 6)
        self.texts(g, e, a=1.0)
        self.mx(g, done, writing, t)
        g.mx_level = 3 if 0.4 < t < 0.6 else 1

    def complete(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        done0, cur0, *_ = self.state(max(u, LEAD))
        start = done0 + (cur0 or 0)
        # 0–1.6s：余下的笔画一气呵成
        prog = lerp(start, N, ease_in_out(span(t, 0, 1.6)))
        done = int(prog)
        cur = prog - done if done < N else None
        if t > 3.0:
            lift = ease_in_out(span(t, 3.0, 3.8)) * -2
        else:
            lift = 0
        paper(g, PX0, PY0 + lift, PX1, PY1 + lift)
        tip = self.draw_fu(g, done, cur, 0, lift)
        self.dish(g)
        self.candle(g, t)
        if t < 1.7 and tip is not None:
            brush(g, tip[0], tip[1], -1.15 + 0.2 * math.sin(t * 20), 30)
        elif t < 2.6:  # 撞笔三下
            k = span(t, 1.7, 2.6)
            y = 28 - abs(math.sin(k * 3 * math.pi)) * 6
            brush(g, CX, y, -1.57, 26)
            if (k * 3) % 1 < 0.3:
                rays(g, CX, y + 1, 4, 8, 8)
        else:
            rx, ry, ra = REST
            brush(g, rx, ry, ra, 30)
        if t > 2.6:
            self.seal(g, span(t, 2.6, 3.0))
        if t > 3.0:  # 符放金光
            k = t - 3.0
            for j in range(3):
                r = ((k * 22 + j * 14) % 42) + 20
                rays(g, CX, 31, r, r + 5, 16, phase=j * 0.2, sy=1.2)
            if k < 0.25:
                g.invert((PX0, PY0, PX1 + 1, PY1 + 1))
        left = PHRASES[0] if t < 1.6 else "急急如律令"
        g.vtext(2, 2, left)
        if t < 3.2:
            self.texts(g, e, left="")
        else:
            g.vtext(113, 4, "符成"[:int(clamp((t - 3.2) * 4, 0, 2))])
        mx_fu(g, min(8, prog / N * 8))
        if t > 3.0:
            r = (t - 3.0) * 4
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - r) < 0.8:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(5 * (1 - span(t, 3.0, 4.5)))
