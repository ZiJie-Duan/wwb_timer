"""河图洛书：点数一组一组浮现。

依据：《系辞上》“河出图，洛出书，圣人则之”。河图：一六居下、二七居上、三八居左、四九居右、五十居中，
奇数为白点（阳、天数）、偶数为黑点（阴、地数）；《青囊经》“一六共宗，二七同道，三八为朋，四九为友，五十同途”。
洛书：“戴九履一，左三右七，二四为肩，六八为足，以五居中”，纵横斜皆十五。

入场：水面起波，一块图版从水中升起，水珠滴落。
持续：一轮 10 分钟，单数轮演河图（1→10 依次浮现），双数轮演洛书（1→9，画在龟甲九宫里）；
      新出的一组点闪动，右边竖写对应的口诀，点阵显示这个数。一轮满：波纹扫过，点沉下去，换另一张图。
中断：图版沉入水中一半，水波荡漾。
恢复：图版浮起。
圆满：其余各组一齐浮现，生成之数两两相连，“圣人则之”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.fx import ring
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register

CX, CY = 64, 32
RENEW = 5.0


def _row(n, x0, y, dx):
    return [(x0 + i * dx, y) for i in range(n)]


def _col(n, x, y0, dy):
    return [(x, y0 + i * dy) for i in range(n)]


def _centered_row(n, y, d=5):
    return _row(n, CX - (n - 1) * d / 2, y, d)


def _centered_col(n, x, d=5):
    return _col(n, x, CY - (n - 1) * d / 2, d)


# 河图：每个数的点位
HETU = {
    1: [(CX, 47)],
    6: _centered_row(6, 56, 6),
    2: _centered_row(2, 16),
    7: _centered_row(7, 8, 6),
    3: _centered_col(3, 49, 6),
    8: _centered_col(8, 38),
    4: _centered_col(4, 79, 6),
    9: _centered_col(9, 90),
    5: [(CX, CY), (CX - 5, CY), (CX + 5, CY), (CX, CY - 5), (CX, CY + 5)],
    10: _centered_row(5, 23, 5) + _centered_row(5, 41, 5),
}
HETU_PAIRS = [(1, 6), (2, 7), (3, 8), (4, 9), (5, 10)]
HETU_SAY = ["一六共宗", "二七同道", "三八为朋", "四九为友", "五十同途"]

# 洛书：九宫（戴九履一，左三右七，二四为肩，六八为足，以五居中）
LUO_GRID = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]
DICE = {
    1: [(1, 1)], 2: [(0, 2), (2, 0)], 3: [(0, 2), (1, 1), (2, 0)], 4: [(0, 0), (0, 2), (2, 0), (2, 2)],
    5: [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)], 6: [(0, 0), (1, 0), (2, 0), (0, 2), (1, 2), (2, 2)],
    7: [(0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 2), (2, 2)],
    8: [(r, c) for r in range(3) for c in range(3) if (r, c) != (1, 1)],
    9: [(r, c) for r in range(3) for c in range(3)],
}
CELL_W, CELL_H = 22, 21
GX0, GY0 = CX - CELL_W * 1.5, 0
LUO = {}
for _r, _row_ in enumerate(LUO_GRID):
    for _c, _n in enumerate(_row_):
        _cx, _cy = GX0 + (_c + 0.5) * CELL_W, GY0 + (_r + 0.5) * CELL_H
        LUO[_n] = [(_cx + (c - 1) * 5.5, _cy + (r - 1) * 5.5) for r, c in DICE[_n]]
LUO_SAY = {1: "戴九履一", 9: "戴九履一", 3: "左三右七", 7: "左三右七", 2: "二四为肩", 4: "二四为肩",
           6: "六八为足", 8: "六八为足", 5: "以五居中"}


def dot(g: Gfx, x: float, y: float, odd: bool, s: float = 1.0):
    """白点（奇，空心）/ 黑点（偶，实心）"""
    if s < 0.4:
        return
    x, y = int(round(x)), int(round(y))
    if s < 0.8:
        g.px(x, y)
        return
    if odd:
        g.d.rectangle((x - 1, y - 2, x + 1, y + 2), fill=0)
        g.d.rectangle((x - 2, y - 1, x + 2, y + 1), fill=0)
        g.d.line((x - 1, y - 2, x + 1, y - 2), fill=1)
        g.d.line((x - 1, y + 2, x + 1, y + 2), fill=1)
        g.d.line((x - 2, y - 1, x - 2, y + 1), fill=1)
        g.d.line((x + 2, y - 1, x + 2, y + 1), fill=1)
    else:
        g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)


@register
class Hetu(Ritual):
    id = "r5.hetu"
    name = "河图洛书"
    desc = "河图、洛书的点数一组一组浮现，单数轮河图双数轮洛书；入水起版，满轮换图"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.6, "complete": 5.0}
    CYCLE = 600.0

    # ------------------------------------------------------------ 状态

    def which(self, e: float) -> str:
        return "luo" if int(e // self.CYCLE) % 2 else "he"

    def count(self, e: float) -> tuple[int, float]:
        """→ (已浮现的组数, 最新一组浮现后过了几秒)"""
        n = 10 if self.which(e) == "he" else 9
        k = e % self.CYCLE
        L = self.CYCLE / n
        c = min(int(k // L) + 1, n)
        return c, k - (c - 1) * L

    # ------------------------------------------------------------ 画面

    def board(self, g: Gfx, kind: str, dy: float = 0.0):
        d = g.d
        x0, x1 = 31, 97
        d.rectangle((x0, 0 + dy, x1, 63 + dy), outline=1)
        if kind == "he":
            d.rectangle((x0 + 2, 2 + dy, x1 - 2, 61 + dy), outline=1)
            for sx, sy in ((x0 + 2, 2), (x1 - 2, 2), (x0 + 2, 61), (x1 - 2, 61)):
                d.rectangle((sx - 1, sy - 1 + dy, sx + 1, sy + 1 + dy), fill=1)
        else:  # 龟甲九宫：格线与甲缘
            for c in (1, 2):
                x = GX0 + c * CELL_W
                for y in range(0, 64, 2):
                    g.px(x, y + dy)
            for r in (1, 2):
                y = GY0 + r * CELL_H
                for x in range(x0 + 1, x1, 2):
                    g.px(x, y + dy)
            for x in (x0 - 2, x1 + 2):
                d.line((x, 4 + dy, x, 59 + dy), fill=1)

    def group(self, g: Gfx, kind: str, n: int, dy: float = 0.0, pop: float = 1.0, lines: bool = True,
              blink_on: bool = True):
        pts = (HETU if kind == "he" else LUO)[n]
        m = len(pts)
        shown = pts[:max(0, min(m, int(math.ceil(pop * m))))]
        if lines and len(shown) > 1 and kind == "he" and n != 5:
            chains = [shown[:5], shown[5:]] if n == 10 else [shown]
            for ch in chains:
                if len(ch) > 1:
                    g.d.line([(x, y + dy) for x, y in ch], fill=1)
        for i, (x, y) in enumerate(shown):
            q = clamp(pop * m - i)
            s = ease_out_back(q) if pop < 1 else 1.0
            if blink_on:
                dot(g, x, y + dy, n % 2 == 1, s)

    def ghost(self, g: Gfx, kind: str, c: int, dy: float = 0.0):
        """还没浮现的各组：只留一个暗点"""
        total = 10 if kind == "he" else 9
        for n in range(c + 1, total + 1):
            for x, y in (HETU if kind == "he" else LUO)[n]:
                g.px(round(x), round(y + dy))

    def say(self, g: Gfx, kind: str, n: int, a: float = 1.0):
        g.d.rectangle((0, 0, 15, 63), fill=0)
        g.d.rectangle((112, 0, 127, 63), fill=0)
        g.vtext(2, 4, ("河图" if kind == "he" else "洛书")[:int(round(a * 2))])
        if n:
            s = HETU_SAY[(n - 1) % 5] if kind == "he" else LUO_SAY[n]
            g.vtext(114, 4, s[:int(round(a * len(s)))])

    def water(self, g: Gfx, level: float, t: float):
        """水面：level = 水面 y"""
        if level >= 64:
            return
        pts = [(x, level + math.sin(x * 0.18 + t * 3) * 1.5) for x in range(0, 129, 4)]
        g.d.polygon(pts + [(128, 64), (0, 64)], fill=0)
        g.d.line(pts, fill=1)
        g.shade((0, int(level) + 3, 128, 64), 0.12)

    def mx_num(self, g: Gfx, n: int):
        if n == 10:  # 四、二、四
            for x in (0, 2, 5, 7):
                g.mx_set(x, 1)
                g.mx_set(x, 6)
            for x in (2, 5):
                g.mx_set(x, 3)
                g.mx_set(x, 4)
            return
        for r, c in DICE[n]:
            g.mx[r * 3:r * 3 + 2, c * 3:c * 3 + 2] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        rise = ease_out(span(t, 0.8, 2.6))
        dy = lerp(70, 0, rise)
        self.board(g, "he", dy)
        self.ghost(g, "he", 1 if t > 2.8 else 0, dy)
        if t > 2.6:
            self.group(g, "he", 1, 0, span(t, 2.8, 3.2))
        # 版上滴落的水珠
        if 1.6 < t < 3.4:
            for j in range(8):
                x = 34 + rand(j, 7) * 60
                y0 = dy + rand(j + 9, 7) * 30
                y = y0 + ((t - 1.6) * 40 + j * 7) % 40
                if y < 60:
                    g.px(x, y)
        self.water(g, lerp(52, 72, span(t, 2.4, 3.4)), t)
        if t < 1.4:
            ring(g, CX, 58, t * 30, 2)
        self.say(g, "he", 1 if t > 3.0 else 0, span(t, 2.6, 3.8))
        if t > 2.8:
            self.mx_num(g, 1)
        else:
            g.mx[7, :] = True
            g.mx[6, int(t * 6) % 8] = True

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        kind = self.which(e)
        c, since = self.count(e)
        self.board(g, kind)
        self.ghost(g, kind, c)
        for n in range(1, c + 1):
            newest = n == c
            pop = span(since, 0, 2.0) if newest else 1.0
            self.group(g, kind, n, pop=pop, blink_on=not (newest and pop >= 1 and not blink(t, 1.2, 0.75)))
        if since < 2.5:
            pts = (HETU if kind == "he" else LUO)[c]
            x, y = pts[len(pts) // 2]
            ring(g, x, y, 3 + since * 8, 2)
            g.mx_level = 3
        self.say(g, kind, c)
        self.mx_num(g, c)

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """波纹扫过，旧图的点沉下去，换另一张图"""
        prev = "he" if self.which(e) == "luo" else "luo"
        kind = self.which(e)
        wave = ease_in_out(span(k, 0, 3.0)) * 180 - 30
        old_n = 10 if prev == "he" else 9
        if k < 2.0:
            self.board(g, prev)
            for n in range(1, old_n + 1):
                pts = (HETU if prev == "he" else LUO)[n]
                for i, (x, y) in enumerate(pts):
                    if x > wave - 40:
                        dot(g, x, y, n % 2 == 1)
                    elif rand(i + n * 20, 5) < 0.4:
                        g.px(x, y + (wave - x) * 0.1)
        else:
            self.board(g, kind)
            self.ghost(g, kind, 1 if k > 3.2 else 0)
            if k > 3.2:
                self.group(g, kind, 1, pop=span(k, 3.2, 4.4))
        for j in range(3):  # 波纹
            x = wave - j * 14
            g.d.arc((x - 30, -10, x + 10, 74), 300, 60, fill=1)
        self.say(g, kind if k > 2.0 else prev, 1 if k > 3.2 else 0)
        if k > 3.2:
            self.mx_num(g, 1)
        else:
            col = int(k * 3) % 8
            g.mx[:, col] = True

    def interrupt(self, g: Gfx, t: float, e: float):
        kind = self.which(e)
        c, since = self.count(e)
        sink = ease_in_out(span(t, 0, 1.3)) * 30
        self.board(g, kind, sink)
        self.ghost(g, kind, c, sink)
        for n in range(1, c + 1):
            self.group(g, kind, n, sink)
        self.water(g, lerp(70, 40, ease_out(span(t, 0, 1.0))), t)
        self.say(g, kind, c)
        self.mx_num(g, c)
        g.mx[7, :] = True

    def resume(self, g: Gfx, t: float, e: float):
        kind = self.which(e)
        c, since = self.count(e)
        sink = (1 - ease_out_back(span(t, 0.1, 1.4))) * 30
        self.board(g, kind, sink)
        self.ghost(g, kind, c, sink)
        for n in range(1, c + 1):
            self.group(g, kind, n, sink)
        self.water(g, lerp(40, 72, ease_in_out(span(t, 0.6, 1.6))), t)
        if t < 1.0:
            for j in range(6):
                x = 34 + rand(j, 3) * 60
                y = 30 + ((t * 40 + j * 9) % 30)
                g.px(x, y)
        self.say(g, kind, c)
        self.mx_num(g, c)

    def complete(self, g: Gfx, t: float, e: float):
        kind = self.which(e)
        c, since = self.count(e)
        total = 10 if kind == "he" else 9
        self.board(g, kind)
        # 余下各组一齐浮现
        for n in range(1, total + 1):
            if n <= c:
                self.group(g, kind, n)
            else:
                self.group(g, kind, n, pop=span(t, 0.2 + (n - c) * 0.12, 1.0 + (n - c) * 0.12))
        # 生成之数两两相连 / 洛书纵横斜
        if t > 1.8:
            if kind == "he":
                for i, (a, b) in enumerate(HETU_PAIRS):
                    q = span(t, 1.8 + i * 0.2, 2.2 + i * 0.2)
                    if q > 0:
                        pa, pb = HETU[a][len(HETU[a]) // 2], HETU[b][len(HETU[b]) // 2]
                        g.d.line((pa[0], pa[1], lerp(pa[0], pb[0], q), lerp(pa[1], pb[1], q)), fill=1)
            else:
                lines = [((0, 0), (2, 2)), ((0, 2), (2, 0)), ((1, 0), (1, 2)), ((0, 1), (2, 1))]
                for i, ((r0, c0), (r1, c1)) in enumerate(lines):
                    q = span(t, 1.8 + i * 0.25, 2.2 + i * 0.25)
                    if q > 0:
                        x0, y0 = GX0 + (c0 + 0.5) * CELL_W, GY0 + (r0 + 0.5) * CELL_H
                        x1, y1 = GX0 + (c1 + 0.5) * CELL_W, GY0 + (r1 + 0.5) * CELL_H
                        for j in range(int(q * 20)):
                            g.px(lerp(x0, x1, j / 20), lerp(y0, y1, j / 20))
        if t > 3.0:
            g.d.rectangle((CX - 33, 0, CX + 33, 63), outline=1 if blink(t, 0.3) else 0)
        g.vtext(2, 4, "河图" if kind == "he" else "洛书")
        right = "圣人则之"
        if t < 1.6:
            self.say(g, kind, c)
        else:
            g.vtext(114, 4, right[:int(span(t, 1.6, 2.8) * 4 + 0.99)])
        if t < 1.6:
            self.mx_num(g, min(total, c + int(span(t, 0.2, 1.4) * (total - c))))
        else:
            r = (t - 1.6) * 4 % 6
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.8:
                        g.mx[yy, xx] = True
            g.mx_level = 1 + int(4 * (1 - span(t, 1.6, 3.2)))
