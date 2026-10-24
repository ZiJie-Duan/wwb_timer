"""代码符箓：左边一道黄符，右边是编辑器。每敲完一行代码，符上就画出对应的一部分（符头、敕令、符胆、符脚、法印），
写完编译，“急急如律令”，符自燃化灰。

符的结构取自符箓派常见格式：符头（三清讳/三勾）→ 敕令 → 符胆 → 符脚，末尾盖法印；“急急如律令”本是汉代公文结语，
后为道教咒语、符文通用的结尾。
入场：符纸从上往下展开，编辑器窗口弹开，状态栏“-- INSERT --”。
持续：代码一个字一个字敲出来（一轮 10 分钟，前 80% 打字，后面编译进度条，最后 0 ERROR），
      符上随之画出对应部分；每隔几秒一道扫描线扫过符（语法检查）。
      一轮结束：大字“急急如律令”盖下，符向上飞走燃尽，换一张新符纸，状态栏“第几道”加一。
中断：状态栏敲 :wq，编辑器淡暗，“已保存”。
恢复：状态栏敲 vim 符.c，编辑器亮回来，接着打。
圆满：编译进度条拉满，0 ERROR，“急急如律令”盖印，符从底部燃起，化灰飘散。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from .r6_common import num as cn_num
from ..engine.fx import flame
from ..engine.gfx import Gfx, text_width
from ..engine.scene import Ritual, register
from .r6_common import _TXT, ctext, cvtext, tiny

FX0, FY0, FX1, FY1 = 3, 1, 41, 62   # 符纸
FCX = (FX0 + FX1) // 2
EX0 = 45                            # 编辑器左边
LINE_Y = (10, 19, 28, 37, 46)
CODE_X = 54
TYPE_END = 0.8                      # 打字占一轮的比例
BUILD_END = 0.96
RENEW = 5.0

CODES = [
    ["#include<雷部>", "敕令(五雷);", "if(邪)斩(邪);", "印(本命);", "return 律令;"],
    ["import 雷部", "def 敕令():", "  召(五雷)", "  斩(邪祟)", "敕令()#律令"],
    ["$ sudo 敕令", "> 召 雷部", "> 斩 邪祟", "> 护 本命", "> 急急如律令"],
]


def poly_partial(g: Gfx, pts, frac: float, width: int = 1):
    """按长度比例画折线的前 frac 部分；返回笔尖位置"""
    if frac <= 0:
        return None
    segs = [(pts[i], pts[i + 1], math.dist(pts[i], pts[i + 1])) for i in range(len(pts) - 1)]
    total = sum(s[2] for s in segs) or 1
    left = total * clamp(frac)
    tip = pts[0]
    for a, b, ln in segs:
        if left <= 0:
            break
        k = min(1.0, left / ln) if ln else 1.0
        tip = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)
        g.d.line((a[0], a[1], tip[0], tip[1]), fill=1, width=width)
        left -= ln
    return tip


def _spiral():
    """符胆：方形回纹（雷纹）"""
    cx, cy = FCX - 1, 47
    pts = [(cx, cy)]
    r = 1
    d = 0
    x, y = cx, cy
    for i in range(8):
        dx, dy = ((1, 0), (0, 1), (-1, 0), (0, -1))[d % 4]
        x, y = x + dx * r * 2, y + dy * r * 2
        pts.append((x, y))
        d += 1
        if i % 2 == 1:
            r += 1
    return pts


HEAD = [[(FCX - 9, 4), (FCX - 9, 9), (FCX - 11, 11)], [(FCX, 3), (FCX, 9), (FCX - 2, 11)],
        [(FCX + 9, 4), (FCX + 9, 9), (FCX + 7, 11)], [(FCX - 13, 14), (FCX + 13, 14)]]
SPIRAL = _spiral()
LEGS = [[(FCX - 3, 56), (FCX - 10, 60)], [(FCX, 56), (FCX, 61)], [(FCX + 3, 56), (FCX + 10, 60)],
        [(FCX - 14, 55), (FCX - 9, 57), (FCX - 14, 59)], [(FCX + 14, 55), (FCX + 9, 57), (FCX + 14, 59)]]


@register
class CodeFu(Ritual):
    id = "r6.codefu"
    name = "代码符箓"
    desc = "符纸配编辑器：一行行敲代码，符上随之画出符头、敕令、符胆、符脚，编译通过急急如律令，符自燃"
    T = {"enter": 4.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.2}
    CYCLE = 600.0

    def setup(self):
        self.code = CODES[self.rng.randrange(len(CODES))]
        self.total = sum(len(s) for s in self.code)

    # ------------------------------------------------------------ 零件

    def typed(self, p: float) -> float:
        """一轮里的进度 → 敲了多少字（小数）"""
        return clamp(p / TYPE_END) * self.total

    def line_fracs(self, n: float) -> list[float]:
        out = []
        for s in self.code:
            out.append(clamp(n / len(s)))
            n -= len(s)
        return out

    def paper(self, g: Gfx, h: float = 1.0, x_off: float = 0.0, y_off: float = 0.0):
        """符纸：双线边框。h：从上往下展开的比例"""
        y1 = FY0 + (FY1 - FY0) * h
        g.d.rectangle((FX0 + x_off, FY0 + y_off, FX1 + x_off, y1 + y_off), outline=1, fill=0)
        if h > 0.1:
            g.d.rectangle((FX0 + 2 + x_off, FY0 + 2 + y_off, FX1 - 2 + x_off, y1 - 2 + y_off), outline=1)
            for x in range(FX0 + 4, FX1 - 2, 3):  # 纸边抖动灰度
                g.px(x + x_off, FY0 + 1 + y_off)
                g.px(x + x_off, y1 - 1 + y_off)

    def fu(self, g: Gfx, fr: list[float], t: float, cursor: bool = True, dx: float = 0, dy: float = 0):
        """符的内容，fr = 五行代码的完成度"""
        tips = []
        # 1 符头
        f = fr[0]
        for i, s in enumerate(HEAD):
            k = clamp(f * len(HEAD) - i)
            tip = poly_partial(g, [(x + dx, y + dy) for x, y in s], k)
            if 0 < k < 1:
                tips.append(tip)
        # 2 敕令（毛笔写）
        if fr[1] > 0:
            if fr[1] >= 1:
                cvtext(g, FCX - 6 + dx, 17 + dy, "敕令")
            else:  # 毛笔逐字从上往下写（缓存字形，裁掉未写到的部分）
                for i, ch in enumerate("敕令"):
                    k = clamp(fr[1] * 2 - i)
                    if k <= 0:
                        break
                    x, y = FCX - 6 + dx, 17 + dy + i * 12
                    if k >= 1:
                        ctext(g, x, y, ch)
                        continue
                    ctext(g, -50, -50, ch)  # 确保进缓存
                    m, w = _TXT[(ch, 12)]
                    cut = max(1, int(12 * k))
                    g.img.paste(1, (int(x), int(y)), m.crop((0, 0, w, cut)))
                    bx = x + w * (0.3 + 0.4 * noise(k * 9, i))
                    g.d.rectangle((bx, y + cut - 1, bx + 1, y + cut), fill=1)
        # 3 符胆
        tip = poly_partial(g, [(x + dx, y + dy) for x, y in SPIRAL], fr[2])
        if 0 < fr[2] < 1:
            tips.append(tip)
        # 4 符脚
        for i, s in enumerate(LEGS):
            k = clamp(fr[3] * len(LEGS) - i)
            tip = poly_partial(g, [(x + dx, y + dy) for x, y in s], k)
            if 0 < k < 1:
                tips.append(tip)
        # 5 法印：方印弹下来
        if fr[4] > 0:
            s = ease_out_back(span(fr[4], 0.6, 1.0)) if fr[4] < 1 else 1
            if fr[4] >= 0.6:
                r = 5 * s
                cx, cy = FCX + 11 + dx, 22 + dy
                g.d.rectangle((cx - r, cy - r, cx + r, cy + r), outline=1, fill=0)
                if s > 0.8:
                    g.d.rectangle((cx - 3, cy - 3, cx + 3, cy + 3), outline=1)
                    g.d.line((cx - 1, cy - 3, cx - 1, cy + 3), fill=1)
                    g.d.line((cx + 1, cy - 1, cx + 3, cy - 1), fill=1)
        if cursor:
            for tp in tips:
                if tp and blink(t, 0.5, 0.6):
                    g.d.rectangle((tp[0] - 1, tp[1] - 1, tp[0] + 1, tp[1] + 1), fill=1)

    def editor(self, g: Gfx, n: float, t: float, status: str = "-- INSERT --", cursor: bool = True,
               bar: float | None = None, round_n: int = 1, w: float = 1.0):
        """右边编辑器：标签栏、行号、代码、状态栏。n = 已敲字数；w：窗口展开比例"""
        x1 = int(lerp(EX0 + 8, 127, w))
        g.d.rectangle((EX0, 0, x1, 63), outline=1, fill=0)
        if w < 1:
            return
        g.d.rectangle((EX0, 0, 127, 7), fill=1)
        tiny(g, EX0 + 3, 1, "FU.C", fill=0)
        ctext(g, 126, 0, f"第{cn_num(round_n)}道", size=8, fill=0, align="right")
        for i, y in enumerate(LINE_Y):
            tiny(g, EX0 + 3, y + 1, str(i + 1))
        g.d.line((EX0 + 7, 8, EX0 + 7, 54), fill=1)
        left = n
        cur = None
        for i, s in enumerate(self.code):
            k = int(min(left, len(s)))
            if k > 0:
                ctext(g, CODE_X, LINE_Y[i], s[:k], size=8)
            if left < len(s) and cur is None:
                cur = (CODE_X + text_width(s[:max(k, 0)], 8) + 1, LINE_Y[i])
            left -= len(s)
        if cur is None:
            cur = (CODE_X + text_width(self.code[-1], 8) + 1, LINE_Y[-1])
        if cursor and blink(t, 0.8, 0.55):
            g.d.rectangle((cur[0], cur[1], cur[0] + 1, cur[1] + 7), fill=1)
        g.d.rectangle((EX0, 55, 127, 63), fill=1)
        if bar is not None:
            tiny(g, EX0 + 3, 57, "BUILD", fill=0)
            g.d.rectangle((EX0 + 24, 57, 124, 61), outline=0)
            g.d.rectangle((EX0 + 26, 59, EX0 + 26 + (124 - EX0 - 28) * clamp(bar), 59), fill=0)
            if bar >= 1:
                g.d.rectangle((EX0 + 24, 56, 126, 62), fill=1)
                tiny(g, 124, 57, "0 ERROR", fill=0, align="right")
        elif status:
            if any(ord(c) > 127 for c in status):
                ctext(g, EX0 + 3, 56, status, size=8, fill=0)
            else:
                tiny(g, EX0 + 3, 57, status, fill=0)

    def scan(self, g: Gfx, t: float):
        """语法检查扫描线：每 6 秒扫一次符"""
        k = (t % 6.0) / 1.2
        if k < 1:
            y = FY0 + 3 + k * (FY1 - FY0 - 6)
            for x in range(FX0 + 3, FX1 - 2, 2):
                g.px(x, y)

    def mx(self, g: Gfx, fr: list[float], t: float, n_lines_lit: bool = True):
        g.mx[0, :] = True  # 标签栏
        for i, f in enumerate(fr):
            w = int(round(f * 7))
            for x in range(w):
                g.mx[1 + i, x] = True
        # 光标
        for i, f in enumerate(fr):
            if f < 1:
                g.mx_set(int(round(f * 7)), 1 + i, blink(t, 0.8, 0.55))
                break

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, e: float, cursor: bool = True):
        p = (e % self.CYCLE) / self.CYCLE
        n = self.typed(p)
        fr = self.line_fracs(n)
        self.paper(g)
        self.fu(g, fr, t, cursor)
        bar = None if p < TYPE_END else span(p, TYPE_END, BUILD_END)
        self.editor(g, n, t, bar=bar, round_n=int(e // self.CYCLE) + 1, cursor=cursor and p < TYPE_END)
        return fr, p

    def enter(self, g: Gfx, t: float):
        h = ease_out_bounce(span(t, 0.0, 1.2))
        if h > 0:
            self.paper(g, h)
        w = ease_out_back(span(t, 0.8, 1.7))
        if t >= 0.8:
            if w < 1:
                self.editor(g, 0, t, w=w)
            else:
                st = "-- INSERT --"
                k = int(clamp((t - 1.9) * 12) * len(st))
                self.editor(g, 0, t, status=st[:k], cursor=t > 2.9)
        g.mx[1:6, 0] = blink(t, 0.8, 0.55) if t > 2.9 else False
        g.mx[0, :] = h > 0.9
        if t < 2.9:
            g.mx[7, :int(clamp(t / 2.9) * 8)] = True

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, e)
            return
        fr, p = self.frame(g, t, e)
        self.scan(g, t)
        if p >= BUILD_END:  # 编译通过：符纸边缘闪光
            if blink(t, 0.5, 0.5):
                for x in range(FX0, FX1 + 1, 4):
                    g.px(x, FY0)
                    g.px(x + 2, FY1)
        self.mx(g, fr, t)
        if p >= TYPE_END:
            g.mx[7, :int(span(p, TYPE_END, BUILD_END) * 8)] = True

    def _seal_text(self, g: Gfx, k: float):
        """大字“急急如律令”盖下来"""
        s = ease_out_bounce(clamp(k))
        y = lerp(-14, 24, s)
        g.d.rectangle((6, y - 3, 121, y + 13), fill=0, outline=1)
        g.d.rectangle((8, y - 1, 119, y + 11), outline=1)
        ctext(g, 64, y, "急急如律令", align="center")

    def _renew(self, g: Gfx, k: float, e: float):
        prev = int(e // self.CYCLE)
        if k < 3.2:
            fly = ease_in(span(k, 1.4, 2.6))
            self.paper(g, 1.0, 0, -fly * 70)
            self.fu(g, [1] * 5, k, cursor=False, dy=-fly * 70)
            if 0.9 < k < 2.6:  # 符脚起火
                flame(g, FCX, FY1 - fly * 70 + 2, 18, 12 + 6 * span(k, 0.9, 1.4), k, self.seed)
            self.editor(g, self.total, k, bar=1.0, round_n=prev, cursor=False)
            if k < 1.6:
                self._seal_text(g, span(k, 0.0, 0.6))
            g.mx[:, :] = False
            if k < 1.4:
                g.mx[2:6, 1:7] = blink(k, 0.25, 0.5)
                g.mx[0, :] = g.mx[7, :] = True
                g.mx_level = 4 if k < 0.6 else 1
            else:
                for c in range(8):
                    h = int(3 + 3 * noise(k * 6 + c, self.seed))
                    for r in range(8 - h, 8):
                        g.mx[r, c] = True
            return
        # 新符纸从下面弹上来，编辑器清空
        u = ease_out_back(span(k, 3.2, 4.4))
        self.paper(g, 1.0, 0, (1 - u) * 66)
        self.editor(g, 0, k, round_n=prev + 1, status="-- INSERT --" if k > 4.2 else "NEW")
        g.mx[1:6, 0] = blink(k, 0.8, 0.55)
        g.mx[0, :] = True

    def interrupt(self, g: Gfx, t: float, e: float):
        p = (e % self.CYCLE) / self.CYCLE
        n = self.typed(p)
        fr = self.line_fracs(n)
        self.paper(g)
        self.fu(g, fr, t, cursor=False)
        cmd = ":wq"
        kk = int(clamp(t / 0.6) * len(cmd))
        self.editor(g, n, t, status=cmd[:kk] if t < 0.9 else "已保存", cursor=False,
                    round_n=int(e // self.CYCLE) + 1)
        if t > 0.9:  # 存盘图标
            k = ease_out_back(span(t, 0.9, 1.3))
            x, y = 112, 46 - (1 - k) * 4
            g.d.rectangle((x, y, x + 8, y + 7), fill=0, outline=1)
            g.d.rectangle((x + 2, y, x + 6, y + 2), fill=1)
            g.d.rectangle((x + 2, y + 4, x + 6, y + 7), outline=1)
        self.mx(g, fr, 0)
        if t > 0.9:
            g.mx[7, :] = True

    def resume(self, g: Gfx, t: float, e: float):
        p = (e % self.CYCLE) / self.CYCLE
        n = self.typed(p)
        fr = self.line_fracs(n)
        self.paper(g)
        self.fu(g, fr, t, cursor=t > 1.2)
        cmd = "VIM 符.C"
        if t < 0.9:
            kk = int(clamp(t / 0.7) * len(cmd))
            st = cmd[:kk]
        else:
            st = "-- INSERT --"
        bar = None if p < TYPE_END else span(p, TYPE_END, BUILD_END)
        if t < 0.9:
            self.editor(g, n, t, status="", cursor=False, round_n=int(e // self.CYCLE) + 1)
            ctext(g, EX0 + 3, 56, st, size=8, fill=0)
        else:
            self.editor(g, n, t, status=st, cursor=p < TYPE_END, bar=bar, round_n=int(e // self.CYCLE) + 1)
        self.mx(g, fr, t)

    def complete(self, g: Gfx, t: float, e: float):
        p = (e % self.CYCLE) / self.CYCLE
        n0 = self.typed(p)
        # 0–0.8 把剩下的代码一口气敲完；0.6–1.4 编译；1.4 0 ERROR；1.6– 盖“急急如律令”；2.4– 符燃
        n = lerp(n0, self.total, span(t, 0.0, 0.8))
        fr = self.line_fracs(n)
        burn = span(t, 2.4, 4.4)
        if burn < 1:
            yb = lerp(FY1 + 2, FY0 - 2, ease_in(burn) * 0.4 + burn * 0.6)  # 燃烧线自下而上
            self.paper(g)
            self.fu(g, fr, t, cursor=False)
            if burn > 0:
                g.d.rectangle((FX0, min(yb, FY1), FX1, FY1), fill=0)
                for x in range(FX0, FX1 - 2, 5):  # 焦边 + 火苗
                    flame(g, x + 3, yb + 1, 4, 4 + 5 * noise(t * 5 + x, self.seed), t, x)
        else:
            pass
        if burn > 0:  # 灰烬往上飘
            for j in range(18):
                a0 = rand(j, self.seed + 3)
                st = 2.4 + a0 * 2.0
                if t < st:
                    continue
                k = t - st
                x = FX0 + rand(j, self.seed + 4) * (FX1 - FX0) + math.sin(k * 3 + j) * 3
                y = FY1 - a0 * 50 - k * 14
                if y > -2 and rand(int(t * 15) + j, 5) > 0.2:
                    g.px(x, y)
        bar = span(t, 0.6, 1.4)
        self.editor(g, n, t, bar=bar if t > 0.6 else None, cursor=False, round_n=int(e // self.CYCLE) + 1)
        if t > 1.6:
            self._seal_text(g, span(t, 1.6, 2.2))
        # 点阵
        if t < 1.6:
            self.mx(g, fr, t)
            g.mx[7, :int(bar * 8)] = True
        else:
            for c in range(8):
                h = int((3 + 4 * noise(t * 6 + c, self.seed)) * (1 - span(t, 4.2, 5.2)))
                for r in range(8 - h, 8):
                    g.mx[r, c] = True
            g.mx_level = 6 if t < 2.0 else 1 + int(3 * (1 - span(t, 2.4, 4.4)))
