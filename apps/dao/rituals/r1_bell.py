"""鸣钟：钟架上一口大钟，左边绳吊撞木，一下一下撞钟，声波一圈圈荡开；“紧十八、慢十八、不紧不慢又十八”，
两遍一百零八响。

依据：宫观殿堂“金钟玉磬”，“鸣钟以集众、动神”（daoinfo《Bells》引《太真科》）；丛林晨钟暮鼓通行
一百零八杵之法：“紧十八，慢十八，不紧不慢又十八”，两遍凑成一百零八。道观以钟板“开静”“止静”。

入场：大钟从上落到钟架上晃两下，撞木被拉开。
持续：一轮 600 秒 = 两遍（紧 3 秒 / 慢 8 秒 / 不紧不慢 5 秒 各十八杵）共一百零八响，撞时间完全由 e 决定。
      撞上那一刻钟身一震、声波荡开、点阵一闪；右侧竖写响数。百零八响后余音二十余秒，撞木慢慢拉满，
      下一轮第一杵（“续”）。
中断：撞木停在钟边，余音散尽，“止静”。
恢复：“开静”，撞木荡开撞一杵，接上节奏。
圆满：连撞三记重杵，声波满屏，“琳琅振响 / 十方肃清”（《度人经》）。
"""
from __future__ import annotations

import bisect
import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, span
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import arc_dots, mx_ring, vreveal

BX, BY0, BY1 = 72, 9, 51       # 钟：中心 x，钟顶、钟口
SEC = (("紧十八", 3.0), ("慢十八", 8.0), ("不紧不慢", 5.0))
FIRST = 2.0                    # 一轮第一杵在第几秒


def _schedule():
    times, labels = [], []
    s = FIRST
    for rep in range(2):
        for lab, iv in SEC:
            for _ in range(18):
                times.append(s)
                labels.append(lab)
                s += iv
    return times, labels


STRIKES, LABELS = _schedule()          # 108 杵（本轮内的秒数）


def bell_hw(y: float) -> float:
    k = clamp((y - BY0) / (BY1 - BY0))
    return 13 + 2 * k + 5 * k ** 4


def bell(g: Gfx, dx: float = 0.0, dy: float = 0.0, glow: float = 0.0):
    d = g.d
    cx = BX + dx
    y0, y1 = BY0 + dy, BY1 + dy
    top = y0 + 6
    left, right = [], []
    for i in range(15):
        y = top + (y1 - top) * i / 14
        hw = bell_hw(y - dy)
        left.append((cx - hw, y))
        right.append((cx + hw, y))
    d.pieslice((cx - 13, y0, cx + 13, top + 6), 180, 360, fill=0, outline=1)   # 圆顶
    d.polygon(left + right[::-1], fill=0)
    d.line(left, fill=1)
    d.line(right, fill=1)
    d.line((cx - 13, top, cx + 13, top), fill=1)
    w1 = bell_hw(BY1)
    d.rectangle((cx - w1 - 1, y1 - 2, cx + w1 + 1, y1), fill=0, outline=1)  # 钟唇
    # 纽（蒲牢）
    d.arc((cx - 5, y0 - 7, cx + 5, y0 + 3), 180, 360, fill=1)
    d.line((cx - 5, y0 - 2, cx - 5, y0), fill=1)
    d.line((cx + 5, y0 - 2, cx + 5, y0), fill=1)
    # 上半：四道纵带，带间三排乳钉；中间腰带；下半撞座莲花
    for yy in (top + 3, top + 18):
        hw = bell_hw(yy - dy) - 1
        d.line((cx - hw, yy, cx + hw, yy), fill=1)
    hw = bell_hw(top + 20 - dy) - 1
    d.line((cx - hw, top + 20, cx + hw, top + 20), fill=1)
    for x in (-7, 0, 7):
        d.line((cx + x, top + 3, cx + x, top + 18), fill=1)
    for row in range(3):
        for x in (-11, -4, 3, 10):
            g.px(cx + x + 1, top + 6 + row * 4)
    lx = cx - 9
    d.ellipse((lx - 3, top + 27, lx + 3, top + 33), outline=1)
    g.px(lx, top + 30)
    rx = cx + 9  # 右边也一个撞座
    d.ellipse((rx - 3, top + 27, rx + 3, top + 33), outline=1)
    g.px(rx, top + 30)
    if glow > 0:
        g.shade((int(cx - 15), int(top + 22), int(cx + 2), int(y1 - 3)), 0.25 * glow)


def frame(g: Gfx):
    d = g.d
    d.rectangle((14, 0, 104, 2), fill=1)          # 横梁
    d.line((14, 3, 104, 3), fill=0)
    d.rectangle((BX - 1, 2, BX + 1, BY0 - 6), fill=1)  # 吊钩


def log(g: Gfx, off: float):
    """撞木：两根绳吊着；off = 离接触位置的偏移（负 = 拉开）"""
    lift = off * off / 70
    rest1 = BX - bell_hw(31) - 1      # 静止时木头右端
    x1 = rest1 + off
    x0 = x1 - 30
    y = 31 - lift
    for ax in (rest1 - 25, rest1 - 7):  # 吊绳，从梁上吊下
        g.d.line((ax, 2, ax + off, y - 2), fill=1)
    g.d.rectangle((x0, y - 2, x1, y + 2), fill=0, outline=1)
    g.d.line((x0 + 2, y, x1 - 4, y), fill=1)
    g.d.rectangle((x1 - 2, y - 2, x1, y + 2), fill=1)
    g.d.rectangle((x0, y - 1, x0 + 1, y + 1), fill=1)


@register
class TempleBell(Ritual):
    id = "r1.bell"
    name = "鸣钟"
    desc = "撞木撞大钟，紧十八慢十八不紧不慢又十八，两遍一百零八响，声波荡开"
    T = {"enter": 3.6, "interrupt": 1.6, "resume": 2.0, "complete": 5.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 状态（e 的函数）

    def state(self, e: float):
        """→ (本轮已撞几杵, 上一杵的绝对时间, 下一杵的绝对时间, 段名)"""
        base = e - e % self.CYCLE
        k = e - base
        i = bisect.bisect_right(STRIKES, k)  # 已撞几杵
        if i == 0:
            prev = base - self.CYCLE + STRIKES[-1] if e >= self.CYCLE else base + FIRST - 3.0
            label = LABELS[-1] if e >= self.CYCLE else "起钟"
        else:
            prev = base + STRIKES[i - 1]
            label = LABELS[i - 1]
        nxt = base + STRIKES[i] if i < len(STRIKES) else base + self.CYCLE + FIRST
        if i >= len(STRIKES):
            label = "余音"
        return i, prev, nxt, label

    def offset(self, e: float) -> float:
        _, prev, nxt, _ = self.state(e)
        L = nxt - prev
        u = (e - prev) / L
        amp = clamp(L * 1.6, 5, 13)
        return -amp * math.sin(math.pi * clamp(u)) ** 0.8

    # ------------------------------------------------------------ 零件

    def waves(self, g: Gfx, since: float, strong: float = 1.0):
        """声波：撞后 since 秒，弧从钟两侧荡开"""
        if since < 0 or since > 3.2:
            return
        for j in range(3):
            r = 24 + (since - j * 0.25) * 34
            if r < 24 or since - j * 0.25 > 2.6:
                continue
            step = 2 if since < 1.2 else 3
            arc_dots(g, BX, 30, r, -0.75, 0.75, step=step)
            if strong > 1:
                arc_dots(g, BX, 30, r, math.pi - 0.45, math.pi + 0.2, step=step + 1)

    def texts(self, g: Gfx, n: int, label: str, a: float = 1.0):
        s = cn_num(n) if n else ""
        if s:
            g.d.rectangle((112, 0, 127, min(63, len(s) * 12 + 4)), fill=0)
            vreveal(g, 114, 2, s, a)
        short = {"紧十八": "紧杵", "慢十八": "慢杵", "不紧不慢": "平杵", "起钟": "起钟", "余音": "余音"}
        g.d.rectangle((0, 38, 14, 63), fill=0)
        vreveal(g, 2, 39, short.get(label, label), a)

    def mx(self, g: Gfx, since: float, t: float):
        g.mx_rows([0b00011000, 0b00111100, 0b00111100, 0b01111110, 0b01111110, 0b11111111, 0, 0b00011000])
        if 0 <= since < 0.6:
            g.mx_level = 6 if since < 0.12 else 2
            r = 4 + since * 8
            g.mx[6, :] = False
            for x in range(8):
                if abs(abs(x - 3.5) - r * 0.6) < 0.8:
                    g.mx[6, x] = True
        if 0 <= since < 0.25 and int(since * 30) % 2:  # 钟一震
            g.mx[:, 1:] = g.mx[:, :-1].copy()
            g.mx[:, 0] = False

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        frame(g)
        drop = ease_out_bounce(span(t, 0, 1.1))
        sway = math.sin(t * 9) * 1.5 * (1 - span(t, 1.1, 2.2)) if t > 1.1 else 0
        bell(g, dx=sway, dy=lerp(-70, 0, drop))
        # 撞木从左边荡进来，再被拉到持续阶段 e=0 的位置
        off0 = self.offset(0.0)
        if t < 1.6:
            off = lerp(-60, off0 - 4, ease_out(span(t, 0.4, 1.6)))
        else:
            off = lerp(off0 - 4, off0, ease_in_out(span(t, 1.6, 3.0)))
        log(g, off)
        self.texts(g, 0, "起钟", a=span(t, 2.4, 3.4))
        self.mx(g, -1, t)
        if t < 1.1:
            n = int(span(t, 0, 1.1) * 8)
            g.mx[n:, :] = False

    def hold(self, g: Gfx, t: float, e: float):
        n, prev, nxt, label = self.state(e)
        since = e - prev if (n or e >= self.CYCLE) else 99.0  # 第一杵之前没有“上一杵”
        off = self.offset(e)
        shake = math.sin(since * 70) * 1.2 * (1 - span(since, 0, 0.5)) if 0 <= since < 0.5 else 0
        frame(g)
        self.waves(g, since)
        bell(g, dx=shake)
        log(g, off)
        if n == 0 and e >= self.CYCLE:
            n_show, lab = 108, "余音"
        else:
            n_show, lab = n, label
        if n == 0 and since > 1.0 and e >= self.CYCLE:  # 新一轮：起钟
            lab = "起钟"
        self.texts(g, n_show, lab)
        self.mx(g, since, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        n, prev, nxt, label = self.state(e)
        since = e - prev if (n or e >= self.CYCLE) else 99.0
        off0 = self.offset(e)
        off = lerp(off0, -1.5, ease_in_out(span(t, 0, 1.0)))
        frame(g)
        self.waves(g, since + t * 1.5)
        bell(g)
        log(g, off)
        self.texts(g, n, "止静" if t > 0.7 else label)
        self.mx(g, -1, t)
        g.mx[7, :] = False

    def resume(self, g: Gfx, t: float, e: float):
        n, prev, nxt, label = self.state(e)
        frame(g)
        # 拉开 → 撞一杵（t=1.0）→ 荡到 hold(e) 的位置
        off_h = self.offset(e)
        if t < 1.0:
            off = -1.5 - 10 * math.sin(math.pi * span(t, 0, 1.0)) ** 0.8
            since = -1
        else:
            since = t - 1.0
            off = lerp(0, off_h, ease_in_out(span(t, 1.0, 2.0)))
        shake = math.sin(since * 70) * 1.2 * (1 - span(since, 0, 0.5)) if 0 <= since < 0.5 else 0
        self.waves(g, since)
        bell(g, dx=shake)
        log(g, off)
        self.texts(g, n, "开静" if t < 1.6 else label)
        self.mx(g, since, t)

    def complete(self, g: Gfx, t: float, e: float):
        hits = (0.5, 1.5, 2.5)
        last = max([h for h in hits if t >= h] + [-9])
        since = t - last
        # 撞木：每记之间拉开再撞
        if t < hits[0]:
            off = lerp(self.offset(e), -12, ease_in_out(span(t, 0, hits[0])))
            if t > hits[0] - 0.2:
                off = lerp(-12, 0, span(t, hits[0] - 0.2, hits[0]))
        elif t < hits[-1]:
            u = (t - last) / 1.0
            off = -12 * math.sin(math.pi * u) ** 0.8
        else:
            off = -3 * math.sin(math.pi * clamp((t - hits[-1]) / 1.6))
        frame(g)
        for h in hits:
            s = t - h
            if 0 <= s < 3.2:
                self.waves(g, s, strong=2)
        shake = math.sin(since * 70) * 1.6 * (1 - span(since, 0, 0.6)) if 0 <= since < 0.6 else 0
        bell(g, dx=shake, glow=ease_out(span(t, 2.5, 3.2)) * (1 - span(t, 4.5, 5.5)))
        log(g, off)
        g.d.rectangle((0, 38, 14, 63), fill=0)
        g.d.rectangle((112, 0, 127, 63), fill=0)
        vreveal(g, 114, 2, "琳琅振响", span(t, 2.6, 3.6))
        vreveal(g, 2, 14, "十方肃清", span(t, 3.6, 4.6))
        self.mx(g, since, t)
        if t > 2.6:
            mx_ring(g, (t - 2.6) * 3 % 5, 3.5, 3.5)
