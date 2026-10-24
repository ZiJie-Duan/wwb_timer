"""丹青：一支笔在立轴上画出一幅山水；每第三幅画一条云中龙，点睛即飞去。

右侧竖写的画诀出自传为王维的《山水论》：“远山无石……远树无枝，远人无目……远水无波”；
画成后题“澄怀观道”“卧以游之”（宗炳语，见《宋书·隐逸传》）。
点睛彩蛋：张彦远《历代名画记》记张僧繇画安乐寺四白龙不点眼睛，“每云点睛即飞去”，人以为妄诞，
固请点之，“须臾雷电破壁，两龙乘云腾去上天，二龙未点眼者见在”。

入场：立轴从上往下展开，笔从左边砚台旁起身。
持续：一幅 64 秒：远山（虚线）→ 主峰勾勒与披麻皴 → 飞瀑 → 松 → 远水与渔舟 → 飞鸟 → 题款钤印；
      画成后画中活了：瀑布流动、渔舟漂移、鸟扇翅；然后画轴卷起、再展开一张新纸。
      每第三幅把渔舟飞鸟换成云中之龙：最后点上眼睛——一道闪电，龙破纸而出、腾空飞走，只留下空空的云。
退场：画轴卷起。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import lightning, xiangyun
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import iris

X0, X1 = 40, 88           # 画心左右
Y0, Y1 = 5, 58            # 画心上下
CYC = 64.0
FAR = [(41, 30), (46, 25), (50, 27), (56, 19), (61, 24), (66, 21), (72, 27), (78, 22), (83, 26), (87, 24)]
NEAR = [(41, 55), (44, 44), (48, 37), (51, 33), (55, 29), (58, 32), (61, 28), (64, 34), (68, 40), (71, 47),
        (75, 53), (78, 56)]
HATCH = [((47, 41), (50, 47)), ((50, 36), (52, 43)), ((53, 33), (55, 41)), ((56, 33), (57, 39)),
         ((60, 32), (61, 38)), ((63, 36), (64, 44)), ((66, 42), (66, 48)), ((45, 47), (47, 53)),
         ((52, 45), (53, 52)), ((57, 42), (58, 50)), ((69, 47), (70, 52)), ((61, 44), (62, 51))]
FALL_X = 61
SAYINGS = {"far": "远山无石", "near": "隐隐如眉", "pine": "远树无枝", "boat": "远人无目", "water": "远水无波",
           "dragon": "点睛即飞去"}

BRUSH = Sprite("""
  .##.
  .##.
  .##.
  .##.
  .##.
  .##.
  .##.
  .##.
 .####.
 ######
 #.##.#
 .####.
  .##.
  .#.
""")


def partial(g: Gfx, pts, p: float, dotted: bool = False):
    """按比例 p 画折线的前一段；返回笔尖位置"""
    if p <= 0:
        return pts[0]
    seg = (len(pts) - 1) * clamp(p)
    n = int(seg)
    sub = pts[:n + 1]
    if n < len(pts) - 1:
        (ax, ay), (bx, by) = pts[n], pts[n + 1]
        f = seg - n
        sub = sub + [(ax + (bx - ax) * f, ay + (by - ay) * f)]
    if dotted:
        for (ax, ay), (bx, by) in zip(sub, sub[1:]):
            ln = max(1, int(math.hypot(bx - ax, by - ay)))
            for i in range(0, ln, 2):
                g.px(ax + (bx - ax) * i / ln, ay + (by - ay) * i / ln)
    elif len(sub) > 1:
        g.d.line(sub, fill=1)
    return sub[-1]


def dragon_pts(t: float, dx: float = 0.0, dy: float = 0.0, wav: float = 1.0):
    """云中之龙：一条波浪形的身子（右端是头）"""
    out = []
    for i in range(22):
        k = i / 21
        x = 44 + k * 36 + dx
        y = 12 + math.sin(k * 7 + t * wav * 2) * 3.5 * (0.4 + 0.6 * k) + dy
        out.append((x, y))
    return out


def draw_dragon(g: Gfx, pts, p: float = 1.0, eyes: int = 0, t: float = 0.0):
    n = max(2, int(len(pts) * clamp(p)))
    body = pts[:n]
    g.d.line(body, fill=1, width=3)
    for i in range(1, len(body) - 1, 2):  # 鳞：身上一串暗点
        g.px(body[i][0], body[i][1], 0)
    for i in range(3, len(body) - 2, 6):  # 爪
        x, y = body[i]
        g.d.line((x, y + 1, x - 1, y + 4), fill=1)
        g.d.line((x - 1, y + 4, x + 1, y + 5), fill=1)
    if p >= 1:
        hx, hy = pts[-1]
        g.d.ellipse((hx - 2, hy - 3, hx + 4, hy + 2), fill=1)          # 头
        g.d.line((hx + 3, hy - 1, hx + 7, hy - 2), fill=1)              # 吻
        g.d.line((hx, hy - 3, hx - 3, hy - 7), fill=1)                  # 角
        g.d.line((hx + 2, hy - 3, hx + 1, hy - 7), fill=1)
        g.d.line((hx + 3, hy + 1, hx + 8, hy + 3 + math.sin(t * 5)), fill=1)  # 须
        if eyes:
            g.d.rectangle((hx + 1, hy - 2, hx + 2, hy - 1), fill=0)
            g.px(hx + 1, hy - 2)
        else:
            g.d.rectangle((hx + 1, hy - 2, hx + 2, hy - 1), fill=0)  # 空眼眶


@register
class Paint(Rest):
    id = "x2.paint"
    name = "丹青"
    desc = "笔在立轴上画出远山、皴峰、飞瀑、松、渔舟，画成后画中活了；每三幅画一条龙，点睛即破纸飞去"
    T = {"enter": 2.6, "exit": 1.3}

    def setup(self):
        self.ht = 0.0
        self.n0 = self.rng.randrange(3)

    def is_dragon(self, t: float) -> bool:
        return (int(t // CYC) + self.n0) % 3 == 2

    # ------------------------------------------------------------ 画轴

    def scroll(self, g: Gfx, open_: float):
        """立轴：天杆、地杆、画心（open_ 0..1 展开程度），返回画心底边"""
        yb = lerp(Y0 + 1, Y1, open_)
        g.d.rectangle((X0 - 4, 1, X1 + 4, yb + 3), fill=0, outline=1)
        g.d.rectangle((X0 - 1, Y0, X1 + 1, yb), outline=1)
        g.d.rectangle((X0 - 7, 0, X1 + 7, 2), fill=1)                       # 天杆
        g.d.line((64, 0, 58, -6), fill=1)
        g.d.rectangle((X0 - 7, yb + 3, X1 + 7, yb + 6), fill=1)             # 地杆
        g.d.rectangle((X0 - 9, yb + 3, X0 - 7, yb + 6), fill=0, outline=1)  # 轴头
        g.d.rectangle((X1 + 7, yb + 3, X1 + 9, yb + 6), fill=0, outline=1)
        return yb

    def tools(self, g: Gfx):
        """左下角：砚台、笔洗"""
        g.d.rounded_rectangle((6, 52, 28, 60), 2, fill=0, outline=1)
        g.d.ellipse((9, 54, 20, 58), fill=1)
        g.d.ellipse((4, 40, 20, 48), outline=1)  # 笔洗（俯视的水盂）
        g.d.arc((7, 42, 17, 46), 0, 180, fill=1)

    # ------------------------------------------------------------ 一幅画

    def painting(self, g: Gfx, s: float, t: float, dragon: bool):
        """画到第 s 秒时的画面；返回 (笔尖, 画诀键, 龙的状态)"""
        tip = None
        say = None
        dstate = None
        # 远山（虚线，淡）
        p = span(s, 2.5, 8.0)
        if p > 0:
            e = partial(g, FAR if not dragon else [(x, y + 3) for x, y in FAR], p, dotted=True)
            if p < 1:
                tip, say = e, "far"
        # 主峰：先勾轮廓，再一笔笔披麻皴
        p = span(s, 8.0, 11.0)
        if p > 0:
            e = partial(g, NEAR, p)
            if p < 1:
                tip, say = e, "near"
        p = span(s, 11.0, 16.0)
        n = int(p * len(HATCH))
        for i in range(n):
            (ax, ay), (bx, by) = HATCH[i]
            g.d.line((ax, ay, bx, by), fill=1)
        if 0 < p < 1:
            tip, say = HATCH[min(n, len(HATCH) - 1)][1], "near"
        # 飞瀑
        p = span(s, 16.0, 20.0)
        if p > 0:
            yb = lerp(29, 50, p)
            g.d.line((FALL_X - 1, 29, FALL_X - 1, yb), fill=0)
            g.d.line((FALL_X + 1, 29, FALL_X + 1, yb), fill=0)
            g.d.rectangle((FALL_X - 1, 29, FALL_X + 1, yb), fill=0)
            for y in range(29, int(yb)):
                if (y + int(t * 12 if s > 38 else 0)) % 3:
                    g.px(FALL_X, y)
            if p < 1:
                tip, say = (FALL_X, yb), "water"
            elif s > 20:  # 潭里的水花
                for j in range(3):
                    g.px(FALL_X - 3 + j * 3, 51 - (int(t * 6 + j) % 2))
        # 松
        p = span(s, 20.0, 26.0)
        if p > 0:
            trunk = [(47, 57), (48, 50), (46, 44), (48, 38)]
            e = partial(g, trunk, span(p, 0, 0.4))
            g.d.line([(x + 1, y) for x, y in trunk[:max(1, int(span(p, 0, 0.4) * 4))]], fill=1)
            for j, (cx, cy, w) in enumerate(((48, 38, 6), (44, 45, 5), (51, 47, 5))):
                k = span(p, 0.4 + j * 0.2, 0.6 + j * 0.2)
                if k > 0:
                    sw = math.sin(t * 0.8 + j) * 0.6 if s > 38 else 0
                    for i in range(int(7 * k)):
                        a = math.pi * (1.1 + 0.8 * i / 6)
                        g.d.line((cx + sw, cy, cx + sw + math.cos(a) * w, cy + math.sin(a) * w * 0.6), fill=1)
                    g.d.line((cx - w + sw, cy, cx + w * k + sw, cy), fill=1)
                    if k < 1:
                        e = (cx + w * k, cy)
            if p < 1:
                tip, say = e, "pine"
        if not dragon:
            # 远水 + 渔舟
            p = span(s, 26.0, 31.0)
            if p > 0:
                for j, (y, x0, x1) in enumerate(((54, 66, 87), (56, 72, 87), (52, 76, 86))):
                    k = span(p, j * 0.2, 0.3 + j * 0.2)
                    if k > 0:
                        g.d.line((x0, y, lerp(x0, x1, k), y), fill=1)
                k = span(p, 0.6, 1.0)
                if k > 0:
                    bx = 80 - (math.sin(t * 0.2) * 3 if s > 38 else 0)
                    g.d.line((bx - 4, 50, bx - 4 + 8 * k, 50), fill=1)
                    g.d.line((bx - 3, 51, bx - 3 + 6 * k, 51), fill=1)
                    if k > 0.5:  # 渔人 + 竿
                        g.d.line((bx, 49, bx, 46), fill=1)
                        g.px(bx, 45)
                        g.d.line((bx, 47, bx - 7, 43), fill=1)
                if p < 1:
                    tip, say = ((lerp(66, 87, p), 54) if p < 0.6 else (80, 50)), ("water" if p < 0.6 else "boat")
            # 飞鸟
            p = span(s, 31.0, 34.0)
            for j, (bx, by) in enumerate(((70, 13), (76, 10))):
                k = span(p, j * 0.5, j * 0.5 + 0.5)
                if k > 0:
                    f = 1 if (s > 38 and int(t * 3 + j) % 2) else 0
                    g.d.line((bx - 3 * k, by - 1 + f, bx, by + 1), fill=1)
                    g.d.line((bx, by + 1, bx + 3 * k, by - 1 + f), fill=1)
            if 0 < p < 1:
                tip = (70 + p * 6, 12)
        else:
            # 云 + 龙
            p = span(s, 26.0, 31.0)
            if p > 0:
                xiangyun(g, 50, 24, 0.8 * min(1, p * 3))
                if p > 0.3:
                    xiangyun(g, 72, 21, 0.7)
            fly = span(s, 33.2, 36.5)
            if p > 0 and fly <= 0:
                pts = dragon_pts(t if s > 31 else 0, wav=0.5)
                dp = span(p, 0.15, 1.0)
                draw_dragon(g, pts, dp, eyes=int(s > 32.4) + int(s > 32.9), t=t)
                if p < 1:
                    tip = pts[max(0, int(len(pts) * dp) - 1)]
                elif s < 33.2:
                    hx, hy = pts[-1]
                    tip = (hx + 1, hy - 2)
                say = "dragon"
            if 0 < fly < 1:
                say = None
                dstate = fly
        # 题款 + 钤印
        p = span(s, 34.0, 38.0)
        if p > 0:
            word = "溪山" if not dragon else "云龙"
            n = int(clamp(p * 2.5, 0, 2))
            g.vtext(81, 7, word[:n], size=8)
            if p > 0.8:
                g.d.rectangle((81, 25, 87, 31), fill=1)
                g.d.rectangle((83, 27, 85, 29), fill=0)
            if p < 0.8:
                tip = (84, 7 + n * 8)
        return tip, say, dstate

    def frame(self, g: Gfx, t: float, open_override: float | None = None):
        s = t % CYC
        dragon = self.is_dragon(t)
        if open_override is not None:
            open_ = open_override
        elif s < 2.5:
            open_ = ease_in_out(s / 2.5)
        elif s > 56:
            open_ = 1 - ease_in_out(span(s, 56, 60))
        else:
            open_ = 1.0
        self.tools(g)
        yb = self.scroll(g, open_)
        tip = say = dstate = None
        if open_ > 0.05:
            tip, say, dstate = self.painting(g, s, t, dragon)
            if open_ < 1:  # 卷起：地杆以下不显示
                g.d.rectangle((X0 - 3, yb + 1, X1 + 3, 63), fill=0)
                g.d.rectangle((X0 - 4, yb + 1, X0 - 4, yb + 2), fill=1)
                g.d.rectangle((X1 + 4, yb + 1, X1 + 4, yb + 2), fill=1)
                self.scroll_rods(g, yb)
        # 画诀（右侧竖排）
        if say:
            g.vtext(112, 3, SAYINGS[say])
        elif 38 < s < 56:
            g.vtext(112, 3, "澄怀观道" if (int(t // CYC) % 2 == 0) else "卧以游之")
        # 笔
        if tip is not None:
            bx, by = tip
        else:
            bx, by = 12, 44  # 搁在笔洗里
        g.blit(BRUSH, bx - 3, by - BRUSH.h + 1)
        if dstate is not None:
            self.dragon_flight(g, t, dstate)
        self.mx(g, t, s, dragon, dstate)

    def scroll_rods(self, g: Gfx, yb: float):
        g.d.rectangle((X0 - 7, yb + 3, X1 + 7, yb + 6), fill=1)

    def dragon_flight(self, g: Gfx, t: float, k: float):
        """点睛：雷电破壁，龙乘云腾去"""
        if k < 0.12:  # 闪光
            g.invert((X0 - 1, Y0, X1 + 2, Y1 + 1))
        if k < 0.35:
            lightning(g, 100, -2, 70, 14, seed=int(t * 7), jag=4)
        pts = dragon_pts(t, dx=ease_in(k) * 95, dy=-math.sin(k * math.pi) * 6 + ease_in(k) * 4, wav=2.0)
        draw_dragon(g, pts, 1.0, eyes=2, t=t)
        if k < 0.6:  # 纸上留一道裂痕
            g.d.line((70, 8, 74, 14, ), fill=0)
            g.d.line((74, 14, 72, 20), fill=0)

    def mx(self, g: Gfx, t: float, s: float, dragon: bool, dstate):
        if dstate is not None:
            col = int(dstate * 12) - 2
            for x in range(8):
                y = 3 + round(math.sin(x * 0.9 + t * 8) * 2)
                if 0 <= x - col < 6:
                    g.mx_set(x, y)
            g.mx_level = 6 if dstate < 0.12 else 1
            return
        g.mx[0, :] = True       # 画轴
        g.mx[7, :] = True
        p = span(s, 2.5, 38.0) * (1 - span(s, 56, 60))
        heights = [2, 4, 5, 3, 5, 6, 4, 2]
        for x in range(8):
            h = heights[x] if p * 8 > x else 0
            for y in range(7 - h, 7):
                if y > 0:
                    g.mx[y, x] = (x + y) % 2 == 0 or y == 7 - h

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.frame(g, 0.0, open_override=0.0)
        g.d.rectangle((0, 8, 34, 63), fill=0)
        self.tools(g)
        p = ease_out_back(span(t, 1.4, 2.6))
        g.blit(BRUSH, 9, lerp(64, 44 - BRUSH.h + 1, p))
        if t < 1.4:
            g.d.rectangle((X0 - 10, 0, X1 + 10, 63), fill=0)
            k = ease_out(span(t, 0.0, 1.0))
            w = (X1 - X0 + 14) * k / 2
            g.d.rectangle((64 - w, 0, 64 + w, 2), fill=1)  # 画轴从中间伸展开
            g.d.rectangle((64 - w, 4, 64 + w, 7), fill=1)
        else:
            self.scroll(g, 0.0)
        g.mx[:] = False
        g.mx[0, :] = [abs(x - 3.5) < t * 3 for x in range(8)]
        g.mx[7, :] = g.mx[0, :]

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        s = self.ht % CYC
        open_ = 1.0 if 2.5 <= s <= 56 else None
        p = ease_in_out(span(t, 0.0, 1.0))
        cur = (open_ if open_ is not None else 1.0) * (1 - p)
        self.frame(g, self.ht + t * 0.2, open_override=cur)
        iris(g, span(t, 0.6, self.T["exit"]), 64, 8)
        if t > 0.9:
            g.mx[:] = False
