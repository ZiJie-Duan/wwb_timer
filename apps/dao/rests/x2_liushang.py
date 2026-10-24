"""曲水流觞：王羲之《兰亭集序》“引以为流觞曲水，列坐其次……一觞一咏，亦足以畅叙幽情”。

入场：一道清溪从右上方蜿蜒流进画面，三位雅士在溪边依次坐定。
持续：羽觞（两耳的椭圆酒杯）每 8 秒放下一只，随水漂流、轻轻打转。每三只里有一只停在某位雅士面前：
      他伸手取觞、仰头饮尽，然后——多半提笔赋诗（左上角写出一句王羲之《兰亭诗》），
      偶尔作不出来，“罚酒三觥”，连饮三杯、脑袋晃晃。左下修竹摇曳，水纹一直流。
退场：画面收拢成一个圆。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import iris

# 溪流中线（Catmull-Rom 控制点），从右上流到左下
CTRL = [(150, 14), (134, 13), (106, 12), (84, 18), (74, 30), (80, 41), (70, 52), (44, 56), (20, 50), (-10, 48),
        (-24, 48)]
HALF = 5.0                       # 溪宽一半
LAUNCH = 8.0                     # 每只觞相隔秒数
TRAVEL = 26.0                    # 一只觞流完全程的秒数
POEMS = ["仰视碧天际", "俯瞰渌水滨", "寓目理自陈", "一觞一咏", "畅叙幽情"]


def _catmull(pts, n=10):
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(n):
            u = k / n
            u2, u3 = u * u, u * u * u
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * u + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u3) for j in range(2)))
    out.append(pts[-2])
    return out


PATH = _catmull(CTRL)
_LEN = [0.0]
for _a, _b in zip(PATH, PATH[1:]):
    _LEN.append(_LEN[-1] + math.hypot(_b[0] - _a[0], _b[1] - _a[1]))
TOTAL = _LEN[-1]


def at(u: float):
    """溪中线上弧长比例 u（0..1）处的点与法向"""
    d = clamp(u) * TOTAL
    lo, hi = 0, len(_LEN) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if _LEN[mid] <= d:
            lo = mid
        else:
            hi = mid
    seg = _LEN[hi] - _LEN[lo] or 1
    k = (d - _LEN[lo]) / seg
    (ax, ay), (bx, by) = PATH[lo], PATH[hi]
    tx, ty = bx - ax, by - ay
    ln = math.hypot(tx, ty) or 1
    return ax + tx * k, ay + ty * k, -ty / ln, tx / ln


BANK_L = [(x + nx * HALF, y + ny * HALF) for x, y, nx, ny in (at(i / 120) for i in range(121))]
BANK_R = [(x - nx * HALF, y - ny * HALF) for x, y, nx, ny in (at(i / 120) for i in range(121))]

SCHOLAR = Sprite("""
     .##.
    .####.
   .######.
    #....#
    #...#.#
    #.....#
     #...#
   .##...##.
  #.........#
 #..#........#
 #..#.....#..#
 #...#...#...#
 #....###....#
#.............#
###############
""")
SCHOLAR_L = SCHOLAR.flip()
# 雅士：坐处（脚下中点）、取觞点（溪上 u）、朝向
SEATS = [((96, 40), 0.44, -1), ((60, 30), 0.40, 1), ((27, 45), 0.76, 1)]


def cup(g: Gfx, x: float, y: float, a: float = 0.0, full: bool = True):
    """羽觞：椭圆杯 + 两侧耳（羽），a 为打转角度"""
    ca, sa = math.cos(a), math.sin(a)
    g.d.ellipse((x - 3, y - 2, x + 3, y + 2), fill=1 if full else 0, outline=1)
    for s in (-1, 1):
        ex, ey = x + ca * 4.5 * s, y + sa * 2 * s
        g.d.line((ex - 1, ey, ex + 1, ey), fill=1)
    if full:
        g.px(x, y, 0)


def bamboo(g: Gfx, t: float, seed: int):
    """右下角几竿修竹（“茂林修竹”），竹叶随风摇"""
    for i, (x0, h) in enumerate(((119, 46), (126, 34))):
        sw = (noise(t * 0.5 + i, seed) - 0.5) * 3
        top = 63 - h
        g.d.line((x0, 63, x0 + sw, top), fill=1, width=2 if i == 0 else 1)
        for j in range(1, h // 8):  # 竹节
            y = 63 - j * 8
            xx = x0 + sw * (63 - y) / h
            g.d.line((xx - 1, y, xx + 2, y), fill=0)
        for j in range(2):  # 竹叶：小枝上一组“个”字形的叶
            y = top + 2 + j * 9
            xx = x0 + sw * (63 - y) / h
            d = -1 if (i + j) % 3 else 1
            g.d.line((xx, y, xx + d * 4, y - 2), fill=1)
            for k, (lx, ly) in enumerate(((7, 1), (6, 4), (4, 6))):
                ex = xx + d * 4 + d * lx + sw * 0.5
                g.d.line((xx + d * 4, y - 2, ex, y - 2 + ly), fill=1)


@register
class Liushang(Rest):
    id = "x2.liushang"
    name = "曲水流觞"
    desc = "清溪蜿蜒，羽觞随水漂流，停在谁面前谁就饮酒赋诗，赋不出罚酒三觥"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0

    # ------------------------------------------------------------ 觞

    def cups(self, t: float):
        """当前在水里的觞：[(k, u, 是否停下)]；以及正在饮酒的雅士 (k, seat, 已过秒数)"""
        out = []
        drinker = None
        k1 = int(t // LAUNCH)
        for k in range(max(0, k1 - 4), k1 + 1):
            age = t - k * LAUNCH
            if age < 0:
                continue
            u = age / TRAVEL
            if k % 3 == 1:  # 这只要停在某位雅士面前
                seat = (k // 3) % 3
                us = SEATS[seat][1]
                ta = us * TRAVEL  # 到达用时
                if age < ta:
                    out.append((k, u, False))
                elif age < ta + 1.6:
                    out.append((k, us, True))
                elif age < ta + 16:
                    drinker = (k, seat, age - ta - 1.6)
                continue
            if u < 1:
                out.append((k, u, False))
        return out, drinker

    # ------------------------------------------------------------ 画面

    def stream(self, g: Gfx, t: float, front: float = 1.0):
        n = int(120 * front)
        if n < 2:
            return
        g.d.line(BANK_L[:n + 1], fill=1)
        g.d.line(BANK_R[:n + 1], fill=1)
        for i in range(0, n, 9):  # 岸边小石
            x, y = BANK_L[i]
            if rand(i, 3) < 0.5:
                g.d.ellipse((x - 1, y - 1, x + 2, y + 1), fill=1)
        for j in range(16):  # 水纹：沿流向移动的短划
            u = ((t * 0.05 + j / 16) % 1.0)
            if u > front:
                continue
            x, y, nx, ny = at(u)
            off = (rand(j, 7) - 0.5) * HALF * 1.2
            x, y = x + nx * off, y + ny * off
            x2, y2, _, _ = at(u + 0.012)
            g.d.line((x, y, x2 + nx * off, y2 + ny * off), fill=1)

    def scholar(self, g: Gfx, seat: int, drink: float | None, t: float, dy: float = 0.0):
        """雅士；drink 为取觞饮酒后的秒数（None = 闲坐）"""
        (sx, sy), us, face = SEATS[seat]
        spr = SCHOLAR if face > 0 else SCHOLAR_L
        x, y = sx - SCHOLAR.w // 2, sy - SCHOLAR.h + 1 + dy
        g.d.line((sx - 7, sy + 1, sx + 7, sy + 1), fill=1)   # 席
        nod = 0
        if drink is not None:
            fail = self.fails(seat, drink)
            if fail and 6.0 < drink < 11.0:
                nod = int(math.sin(drink * 8) * 1.5)  # 罚酒后摇头晃脑
        g.blit(spr, x + nod, y)
        hx, hy = sx + face * 4, y + 9  # 手
        if drink is None:
            return
        cx, cy, _, _ = at(us)
        if drink < 1.0:  # 伸手取觞
            p = ease_out(drink)
            ex, ey = lerp(hx, cx, p), lerp(hy, cy, p)
            g.d.line((hx, hy, ex, ey), fill=1)
            cup(g, ex, ey)
        elif drink < 3.0:  # 举觞仰饮
            p = ease_in_out(span(drink, 1.0, 1.8))
            ex, ey = lerp(cx, sx + face * 5, p), lerp(cy, y + 4, p)
            g.d.line((hx, hy, ex, ey), fill=1)
            cup(g, ex, ey, a=p * 1.2 * face, full=drink < 2.4)
        elif self.fails(seat, drink):  # 罚酒三觥：连饮三杯
            if drink < 10.5:
                q = ((drink - 3.0) / 2.5) % 1
                up = math.sin(q * math.pi)
                ex, ey = sx + face * lerp(9, 5, up), lerp(y + 10, y + 4, up)
                g.d.line((hx, hy, ex, ey), fill=1)
                cup(g, ex, ey, a=up * face, full=up < 0.7)
        else:  # 提笔赋诗：膝前一张纸，笔尖移动
            if drink < 12.0:
                px0 = sx + face * 9 - 4
                g.d.rectangle((px0, sy - 3, px0 + 8, sy), fill=0, outline=1)
                bx = px0 + 1 + ((drink * 3) % 1) * 6
                g.d.line((hx, hy, bx, sy - 2), fill=1)
                g.d.line((bx, sy - 2, bx + 2, sy - 7), fill=1)
                for i in range(int(clamp((drink - 3) / 6) * 4)):
                    g.d.line((px0 + 2 + i * 2, sy - 2, px0 + 2 + i * 2, sy - 1), fill=1)

    def fails(self, seat: int, drink: float) -> bool:
        return False if drink is None else rand(int(self._k), self.seed + 17) < 0.3

    def frame(self, g: Gfx, t: float, front: float = 1.0, pop=(1.0, 1.0, 1.0)):
        cups, drinker = self.cups(t)
        self._k = drinker[0] if drinker else 0
        bamboo(g, t, self.seed)
        self.stream(g, t, front)
        for k, u, stopped in cups:
            x, y, nx, ny = at(u)
            bob = math.sin(t * 3 + k) * 0.6
            cup(g, x + nx * bob, y + ny * bob, a=0 if stopped else t * 1.2 + k)
        for i in range(3):
            if pop[i] <= 0.02:
                continue
            d = drinker[2] if drinker and drinker[1] == i else None
            self.scholar(g, i, d, t, dy=(1 - pop[i]) * 10)
        if drinker:  # 左上角的字
            k, seat, d = drinker
            if 3.0 < d < 14.5:
                if self.fails(seat, d):
                    typewriter(g, 2, 1, "罚酒三觥", d - 3.0, cps=3)
                else:
                    line = POEMS[(k // 3 + self.seed) % len(POEMS)]
                    typewriter(g, 2, 1, line, d - 3.5, cps=2)
        self.mx(g, t, cups)

    def mx(self, g: Gfx, t: float, cups):
        path = [(7, 0), (6, 0), (5, 1), (4, 2), (4, 3), (4, 4), (3, 5), (2, 6), (1, 6), (0, 6)]
        for i, (x, y) in enumerate(path):  # 溪水：流动的虚线
            if (i - int(t * 4)) % 3:
                g.mx_set(x, y)
        for k, u, stopped in cups:
            i = int(u * (len(path) - 1) + 0.5)
            x, y = path[min(i, len(path) - 1)]
            g.mx_set(x, y - 1)
            g.mx_set(x, y)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        front = ease_in_out(span(t, 0.0, 1.6))
        pops = tuple(ease_out_back(span(t, 1.4 + i * 0.35, 1.9 + i * 0.35)) for i in range(3))
        self.frame(g, 0.0, front, pops)
        if t < 2.2:
            g.mx[:] = False
            for i in range(int(front * 8)):
                g.mx_set(7 - i, min(7, i))

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.ht + t)
        iris(g, span(t, 0.0, self.T["exit"]), 70, 36)
        if t > 0.8:
            g.mx[:] = False
