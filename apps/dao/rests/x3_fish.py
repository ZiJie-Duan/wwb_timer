"""濠梁观鱼：《庄子·秋水》“庄子与惠子游于濠梁之上。庄子曰：‘鯈鱼出游从容，是鱼之乐也。’
惠子曰：‘子非鱼，安知鱼之乐？’庄子曰：‘子非我，安知我不知鱼之乐？’……庄子曰：‘请循其本……我知之濠上也。’”

入场：从桥上俯看：石栏从下面升上来，水面的波纹渐渐平了，几尾鯈鱼从四边游进来。
持续：一池静水，几片荷叶（有缺口、有叶脉）、一枝荷苞；五尾细长的鯈鱼从容地游，摆尾、转弯，游到荷叶下就看不见。
      石栏上隔一阵浮出一句濠梁之辩：庄子的话靠左，惠子的话靠右，一来一回。
      小事件：一片落叶飘到水上，鱼都凑过去啄，叶子一颤一颤，又散开；蜻蜓落在荷苞上歇一会；鱼偶尔浮上来吐个泡。
退场：鱼一摆尾都散了，水纹荡开，画面淡去。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, smoothstep, span
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import ctext, ptext, every

RAIL = 50
N_FISH = 5
PADS = [(16, 13, 11, 0.6), (100, 10, 10, 2.2), (114, 36, 8, 4.0), (44, 38, 7, 1.2)]  # x, y, r, 缺口方向
BUD = (70, 22)
TALK = [  # (说话人 0=庄子 1=惠子, 句子)
    (0, "鯈鱼出游从容"), (0, "是鱼之乐也"), (1, "子非鱼"), (1, "安知鱼之乐"), (0, "子非我"),
    (0, "安知我不知鱼之乐"), (0, "请循其本"), (0, "我知之濠上也"),
]
TALK_P, TALK_D = 28.0, 13.0
LEAF_P, LEAF_D = 61.0, 22.0


@register
class HaoBridgeFish(Rest):
    id = "x3.fish"
    name = "濠梁观鱼"
    desc = "从濠水桥上俯看一池荷叶，鯈鱼从容游动；石栏上浮出庄子与惠子的对话，一左一右；落叶引鱼来啄"
    T = {"enter": 2.6, "exit": 1.2}

    def setup(self):
        r = self.rng
        self.fp = [(r.uniform(20, 108), r.uniform(10, 42), r.uniform(0.07, 0.13), r.uniform(0.1, 0.17),
                    r.uniform(0, 6.28), r.uniform(0, 6.28), r.uniform(6, 8.5)) for _ in range(N_FISH)]

    # ------------------------------------------------------------ 鱼

    def path(self, i: int, t: float) -> tuple[float, float]:
        cx, cy, w1, w2, p1, p2, _ = self.fp[i]
        x = cx + 46 * math.sin(t * w1 + p1) + 12 * math.sin(t * w1 * 2.3 + p2)
        y = cy + 12 * math.sin(t * w2 + p2) + 5 * math.sin(t * w2 * 2.7 + p1)
        return x, clamp(y, 4, RAIL - 6)

    def fish_pos(self, i: int, t: float, leaf=None, scatter: float = 0.0):
        x, y = self.path(i, t)
        if leaf is not None:  # 被落叶吸引过去
            lx, ly, pull = leaf
            a = i / N_FISH * 2 * math.pi + t * 0.2
            tx, ty = lx + math.cos(a) * 7, ly + math.sin(a) * 5
            x, y = lerp(x, tx, pull), lerp(y, ty, pull)
        if scatter > 0:
            a = i / N_FISH * 2 * math.pi + 0.7
            x += math.cos(a) * scatter * 80
            y += math.sin(a) * scatter * 50
        return x, y

    def fish(self, g: Gfx, x: float, y: float, dx: float, dy: float, t: float, i: int, speed: float):
        """一尾鯈鱼（俯看）：尖头、身子前粗后细、尾巴随游速摆动"""
        ln = math.hypot(dx, dy)
        if ln < 1e-4:
            dx, dy, ln = 1.0, 0.0, 1.0
        ux, uy = dx / ln, dy / ln
        px_, py_ = -uy, ux
        L = self.fp[i][6] + 2
        wag = math.sin(t * (5 + speed * 3) + i) * (0.25 + min(speed, 3) * 0.12)
        # 身子：沿脊线取几点，每点按宽度往两边扩，脊线后段随摆尾弯
        left, right = [], []
        for k, wd in ((0.0, 0.0), (0.12, 1.3), (0.3, 1.6), (0.55, 1.1), (0.78, 0.5)):
            bend = wag * 3.2 * k * k
            cx, cy = x - ux * L * k + px_ * bend, y - uy * L * k + py_ * bend
            left.append((cx + px_ * wd, cy + py_ * wd))
            right.append((cx - px_ * wd, cy - py_ * wd))
        g.d.polygon(left + right[::-1], fill=1)
        bend = wag * 3.2
        tail = (x - ux * L + px_ * bend, y - uy * L + py_ * bend)
        root = ((left[-1][0] + right[-1][0]) / 2, (left[-1][1] + right[-1][1]) / 2)
        tx, ty = tail[0] - root[0], tail[1] - root[1]
        tl = math.hypot(tx, ty) or 1
        tx, ty = tx / tl, ty / tl
        for sgn in (-1, 1):  # 尾鳍分叉
            g.d.line((root, (tail[0] - ty * 1.8 * sgn, tail[1] + tx * 1.8 * sgn)), fill=1)
        g.px(x - ux * 2 + px_ * 0.7, y - uy * 2 + py_ * 0.7, 0)  # 眼

    def school(self, g: Gfx, t: float, leaf=None, scatter: float = 0.0, enter: float = 1.0):
        for i in range(N_FISH):
            x, y = self.fish_pos(i, t, leaf, scatter)
            x2, y2 = self.fish_pos(i, t - 0.15, leaf, scatter * 0.9 if scatter else 0)
            if enter < 1:  # 入场：从四边游进来
                a = i / N_FISH * 2 * math.pi + 0.7
                k = 1 - ease_out(enter)
                x += math.cos(a) * k * 90
                y += math.sin(a) * k * 60
                x2 += math.cos(a) * k * 92
                y2 += math.sin(a) * k * 62
            sp = math.hypot(x - x2, y - y2) / 0.15
            self.fish(g, x, y, x - x2, y - y2, t, i, sp / 10)

    # ------------------------------------------------------------ 水、荷

    def water(self, g: Gfx, t: float, calm: float = 1.0):
        for j in range(14):  # 水面的微光：短横线慢慢漂
            x = (rand(j, 2) * 150 + t * (0.6 + rand(j, 3) * 0.8)) % 150 - 10
            y = 3 + rand(j, 4) * (RAIL - 8)
            if noise(t * 0.5 + j * 2.3, 6) > 0.4:
                g.d.line((x, y, x + 2 + (j % 3), y), fill=1)
        if calm < 1:  # 入场时水面的波纹
            for k in range(2):
                r = (1 - calm) * 22 + k * 8
                g.d.ellipse((64 - r * 1.6, 26 - r * 0.7, 64 + r * 1.6, 26 + r * 0.7), outline=1)

    def pads(self, g: Gfx, t: float, nibble: tuple | None = None):
        for i, (x, y, r, gap) in enumerate(PADS):
            bob = math.sin(t * 0.6 + i) * 0.4
            x += bob
            a0 = math.degrees(gap) - 18
            g.d.pieslice((x - r, y - r * 0.85, x + r, y + r * 0.85), a0 + 36, a0 + 360, fill=0, outline=1)
            for k in range(4):  # 叶脉（从叶心放射，只画一半长）
                a = gap + 1.0 + k * 1.3
                g.d.line((x + math.cos(a) * r * 0.25, y + math.sin(a) * r * 0.2, x + math.cos(a) * r * 0.65,
                          y + math.sin(a) * r * 0.55), fill=1)
            g.px(x, y)
        bx, by = BUD  # 荷苞：一枝尖苞（俯看是个尖桃形）
        g.d.polygon([(bx, by - 5), (bx + 3, by), (bx, by + 3), (bx - 3, by)], fill=0, outline=1)
        g.d.line((bx, by - 3, bx, by + 2), fill=1)

    def dragonfly(self, g: Gfx, t: float):
        ev = every(t, 89.0, 20.0, 33.0)
        if not ev:
            return
        k, lt = ev
        bx, by = BUD[0], BUD[1] - 5
        if lt < 2.0:
            p = ease_out(lt / 2.0)
            x, y = lerp(-8, bx, p), lerp(10, by, p) + math.sin(lt * 9) * 2 * (1 - p)
            flap = int(t * 20) % 2
        elif lt < 17.5:
            x, y = bx, by
            flap = 1 if (lt % 5) < 0.3 else 0
        else:
            p = ease_in((lt - 17.5) / 2.5)
            x, y = lerp(bx, 140, p), lerp(by, -10, p)
            flap = int(t * 20) % 2
        g.d.line((x - 4, y, x + 4, y), fill=1)          # 身
        wy = 1 + flap
        g.d.line((x - 1, y - wy, x - 1, y + wy), fill=1)  # 翅（俯看是十字）
        g.d.line((x + 1, y - wy - 1, x + 1, y + wy + 1), fill=1)
        g.px(x + 4, y)

    def leaf_event(self, g: Gfx, t: float):
        """落叶：飘下来落在水上，鱼凑过去啄，叶子一颤一颤；返回 (x, y, 吸引程度) 或 None"""
        ev = every(t, LEAF_P, LEAF_D, 15.0)
        if not ev:
            return None
        k, lt = ev
        lx = 30 + rand(k, 5) * 70
        ly = 14 + rand(k, 6) * 24
        if lt < 2.0:  # 飘落（俯看：从大到小，左右翻）
            p = lt / 2.0
            x = lx + math.sin(lt * 4) * 6 * (1 - p)
            s = 1 + (1 - p) * 2
            g.d.ellipse((x - 2 * s, ly - s, x + 2 * s, ly + s), outline=1)
            return None
        dt = lt - 2.0
        nib = math.sin(dt * 9) * 0.8 if 5 < dt < 15 else 0
        for kk in range(2):  # 落水的圈
            r = (dt - kk * 0.5) * 8
            if 0 < r < 22:
                g.d.ellipse((lx - r * 1.4, ly - r * 0.8, lx + r * 1.4, ly + r * 0.8), outline=1)
        g.d.ellipse((lx - 3, ly - 1.5 + nib, lx + 3, ly + 1.5 + nib), fill=1)
        g.d.line((lx - 3, ly + nib, lx + 3, ly + nib), fill=0)
        g.d.line((lx + 3, ly + nib, lx + 5, ly - 1 + nib), fill=1)
        pull = smoothstep(span(dt, 1.0, 5.0)) * (1 - smoothstep(span(dt, 15.0, LEAF_D - 2.0)))
        return lx, ly, pull * 0.85

    def bubbles(self, g: Gfx, t: float):
        ev = every(t, 19.0, 1.6, 4.0)
        if not ev:
            return
        k, lt = ev
        i = k % N_FISH
        x, y = self.path(i, t - lt)
        r = 1 + lt * 3
        g.d.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), outline=1)
        if lt < 0.4:
            g.px(x, y - 2)

    # ------------------------------------------------------------ 桥栏

    def rail(self, g: Gfx, t: float, dy: float = 0.0):
        y0 = RAIL + dy
        y1 = y0 + 63 - RAIL
        g.d.rectangle((0, y0, 127, y1), fill=0)
        g.d.line((0, y0, 127, y0), fill=1)
        g.d.line((0, y0 + 2, 127, y0 + 2), fill=1)
        for x in range(4, 128, 30):  # 望柱
            g.d.rectangle((x, y0 - 3, x + 5, y1), fill=0, outline=1)
            g.d.rectangle((x + 1, y0 - 4, x + 4, y0 - 3), fill=1)
        self.talk(g, t, y0)

    def talk(self, g: Gfx, t: float, y0: float):
        ev = every(t, TALK_P, TALK_D, 4.0)
        if not ev:
            return
        k, lt = ev
        who, s = TALK[k % len(TALK)]
        n = int(round(clamp(lt * 4 / len(s)) * len(s) * (1 - span(lt, TALK_D - 1.5, TALK_D))))
        if n <= 0:
            return
        from ..engine.gfx import text_width
        w = text_width(s)
        x = 12 if who == 0 else 116 - w
        g.d.rectangle((x - 2, y0 + 3, x + w + 1, y0 + 13), fill=0)
        ptext(g, x, y0 + 3, s, n)

    def mx(self, g: Gfx, t: float):
        # 一尾鱼在点阵里游来游去
        p = (t / 7.0) % 2
        right = p < 1
        q = p if right else p - 1
        x = lerp(-3, 10, q) if right else lerp(10, -3, q)
        y = 3 + math.sin(t * 0.9) * 1.5
        body = [(0, 0), (-1, 0), (-2, 0), (-3, -1 if int(t * 6) % 2 else 1)] if right else \
            [(0, 0), (1, 0), (2, 0), (3, -1 if int(t * 6) % 2 else 1)]
        for dx, dy in body:
            g.mx_set(int(round(x + dx)), int(round(y + dy)))
        r = (t % 3.0) * 1.6  # 泡泡涟漪
        for a in range(0, 360, 45):
            g.mx_set(int(round(5 + math.cos(math.radians(a)) * r)), int(round(6 + math.sin(math.radians(a)) * r * 0.6)))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        tt = t - T
        self.water(g, tt, calm=span(t, 0, 2.0))
        self.school(g, tt, enter=span(t, 0.4, T))
        self.pads(g, tt)
        self.rail(g, tt - 999, dy=(1 - ease_out(span(t, 0, 1.0))) * 16)
        self.mx(g, t)

    def hold(self, g: Gfx, t: float):
        self.water(g, t)
        leaf = self.leaf_event(g, t)
        self.school(g, t, leaf)
        self.bubbles(g, t)
        self.pads(g, t)
        self.dragonfly(g, t)
        self.rail(g, t)
        self.mx(g, t)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        tt = self.hold_t + t   # 接着持续阶段最后的样子
        self.water(g, tt, calm=1 - span(t, 0.1, T))
        self.school(g, tt, scatter=ease_in(span(t, 0, 0.8)))
        self.pads(g, tt)
        self.rail(g, tt)
        g.fade(1 - ease_in(span(t, 0.3, T)))
        self.mx(g, t)
        cols = int(t / T * 8)
        if cols:
            g.mx[:, 8 - cols:] = False
