"""掌心雷：五雷法引雷入掌。

依据：雷法（五雷法、五雷正法、掌心雷）为宋代以来神霄、清微等派的法术，取雷霆行天地中气之意，
道士以掌心雷驱邪；雷部之首为九天应元雷声普化天尊。震卦（☳）为雷。

入场：乌云从两边涌来，一只手掌从下方托起，掌心逐笔写出“雷”字，指尖跳起电花。
持续：一轮 10 分钟分五雷：每两分钟一道雷落进掌心，左边五个震卦（☳）依次点亮；
      两道雷之间云越压越低、电花越来越密、云里闷闪。第五雷是大雷：满屏一闪，“轰”，云散再聚，五卦归零。
中断：五指握拳，乌云退回天上，电花熄灭，“暂收”。
恢复：拳头张开，云又压下来。
圆满：一道大雷劈进掌心，满屏闪白，掌心放出冲击波，云开见天，“急急如律令”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import brush_reveal, lightning, ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import draw_trigram, mx_trigram
from .r5_util import cloud_blobs, mist

HX, HY = 63, 47        # 掌心
STRIKES = 5
RENEW = 5.0


def hand(g: Gfx, dy: float = 0.0, curl: float = 0.0):
    """仰掌（掌心朝外）。curl 0..1：五指握起成拳"""
    d = g.d
    y = dy
    # 袖口
    sleeve = [(46, 64 + y), (50, 58 + y), (77, 58 + y), (81, 64 + y)]
    d.polygon(sleeve, fill=0, outline=1)
    d.line((48, 61 + y, 79, 61 + y), fill=1)
    # 掌
    d.rounded_rectangle((52, 42 + y, 74, 59 + y), 4, fill=1)
    # 四指：curl 时缩短并在掌上方弯成指节
    fingers = [(53, 26), (58, 22), (63, 23), (68, 28)]
    c = ease_in_out(curl)
    for i, (x, top) in enumerate(fingers):
        t2 = lerp(top, 39, c)
        d.rounded_rectangle((x, t2 + y, x + 4, 46 + y), 2, fill=1)
    for i, (x, top) in enumerate(fingers[:-1]):  # 指缝
        t2 = lerp(top, 39, c)
        d.line((x + 5, max(t2, lerp(fingers[i + 1][1], 39, c)) + 1 + y, x + 5, 42 + y), fill=0)
    if curl > 0.5:
        d.line((53, 44 + y, 72, 44 + y), fill=0)
        for x in (55, 60, 65, 70):
            g.px(x, 41 + y, 0)
    # 拇指
    tip = (lerp(45, 55, c), lerp(37, 45, c))
    d.line((54, 53 + y, tip[0], tip[1] + y), fill=1, width=5)
    d.ellipse((tip[0] - 2.5, tip[1] - 2.5 + y, tip[0] + 2.5, tip[1] + 2.5 + y), fill=1)
    d.line((52, 47 + y, 55, 51 + y), fill=0)


@register
class Leifa(Ritual):
    id = "r5.leifa"
    name = "掌心雷"
    desc = "乌云压顶，雷一道道落进掌心，五雷聚满引下大雷，满屏一闪“轰”"
    T = {"enter": 4.2, "interrupt": 1.5, "resume": 1.6, "complete": 5.0}
    CYCLE = 600.0

    # ------------------------------------------------------------ 状态

    def state(self, e: float):
        """→ (已落几雷 0..4, 距下一雷的进度 0..1, 上一雷落下后过了几秒)"""
        k = e % self.CYCLE
        L = self.CYCLE / STRIKES
        n = min(int(k // L), STRIKES - 1)
        return n, (k - n * L) / L, k - n * L

    # ------------------------------------------------------------ 零件

    def clouds(self, g: Gfx, low: float, t: float, spread: float = 0.0, flash: float = 0.0):
        """乌云：low 0..1 越压越低；spread 0..1 向两边退开"""
        y = lerp(4, 11, low)
        drift = math.sin(t * 0.3) * 3
        bl = []
        for i, (cx, w) in enumerate(((20, 56), (64, 64), (108, 56))):
            off = (cx - 64) * spread * 1.6
            bl += cloud_blobs(cx + off + drift * (1 if i % 2 else -1), y - spread * 20, w, 16 + 6 * low, 40 + i)
        level = 0.18 + 0.25 * low + flash * 0.5
        mist(g, bl, min(level, 0.9))

    def marks(self, g: Gfx, n: int, t: float, a: float = 1.0):
        """左边五个震卦：已落的雷点亮"""
        for i in range(STRIKES):
            y = 60 - i * 10 - 8
            if i >= int(round(a * STRIKES)):
                continue
            if i < n:
                draw_trigram(g, 2, y, "震", w=10, h=1, step=3)
            else:
                for k in range(3):
                    for x in range(2, 12, 3):
                        g.px(x, y + k * 3)

    def sparks(self, g: Gfx, t: float, dens: float, dy: float = 0.0):
        """指尖电花：dens 0..1"""
        tips = [(55, 24), (60, 20), (65, 21), (70, 26)]
        for i, (x, y) in enumerate(tips):
            if noise(t * 6 + i * 3.1, 7) < 0.35 + 0.5 * dens:
                continue
            s = int(t * 12 + i)
            pts = [(x, y + dy)]
            for j in range(3):
                pts.append((x + (rand(s * 5 + j, i) - 0.5) * 8, y - 2 - j * 3 + dy))
            g.d.line(pts, fill=1)

    def bolt(self, g: Gfx, n: int, seed: int, width: int = 1, x0: float | None = None):
        x0 = x0 if x0 is not None else 20 + rand(n, seed) * 88
        lightning(g, x0, 10, 60, 20, seed=seed * 31 + n, jag=5, branches=2, width=width)

    def label(self, g: Gfx, s: str = "掌心雷", a: float = 1.0):
        g.d.rectangle((113, 20, 127, 63), fill=0)
        g.vtext(114, 26, s[:int(round(a * len(s)))])

    def seal(self, g: Gfx, dy: float = 0.0, p: float = 1.0):
        """掌心的“雷”字（黑字）"""
        if p >= 1:
            g.text(HX - 6, 46 + dy, "雷", fill=0)
        elif p > 0:
            before = g.array()
            g.text(HX - 6, 46 + dy, "雷", fill=0)
            after = g.array()
            cut = int(46 + dy + 12 * p)
            after[cut:, :] = before[cut:, :]
            g.put(after)

    def mx_zhen(self, g: Gfx, t: float, dens: float = 0.0):
        mx_trigram(g, "震")
        if dens > 0 and noise(t * 5, 3) > 1 - dens * 0.6:
            g.mx[0, int(rand(int(t * 10), 4) * 8)] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.clouds(g, 0.0, t, spread=1 - ease_out(span(t, 0, 1.6)))
        dy = (1 - ease_out_back(span(t, 0.8, 2.0))) * 40
        hand(g, dy)
        self.seal(g, dy, span(t, 2.2, 3.2))
        if t > 3.2:
            self.sparks(g, t, 0.2)
        if 3.4 < t < 3.7:
            self.bolt(g, 0, 99, x0=40)
            g.mx_level = 5
        self.marks(g, 0, t, span(t, 2.6, 3.6))
        self.label(g, a=span(t, 2.8, 4.0))
        self.mx_zhen(g, t)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        n, p, since = self.state(e)
        strike = n > 0 and since < 0.5
        inner = noise(t * 1.3, 5) > 0.82 - 0.2 * p  # 云里闷闪
        self.clouds(g, p, t, flash=1.0 if strike and since < 0.15 else (0.4 if inner else 0))
        if strike:
            self.bolt(g, int(e // self.CYCLE) * 10 + n, 17, width=1)
        if inner and p > 0.3 and blink(t, 0.25):
            lightning(g, 10 + rand(int(t * 2), 8) * 100, 6, 10 + rand(int(t * 2) + 1, 8) * 100, 16,
                      seed=int(t * 2), jag=3, branches=0)
        hand(g)
        self.seal(g)
        if strike or since < 1.5 and n > 0:
            ring(g, HX, HY, 12 + since * 18, 2)
        self.sparks(g, t, p)
        self.marks(g, n, t)
        self.label(g)
        self.mx_zhen(g, t, p)
        if strike:
            g.mx[:] = True if since < 0.12 else g.mx
            g.mx_level = 6 if since < 0.15 else 3

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """第五雷：大雷劈下，满屏一闪，“轰”，云散再聚"""
        spread = ease_out(span(k, 0.6, 2.0)) * (1 - ease_in_out(span(k, 2.6, 4.5)))
        self.clouds(g, 1 - span(k, 0, 2.0), t, spread=spread, flash=1.0 if k < 0.2 else 0)
        hand(g)
        self.seal(g)
        if k < 0.6:
            self.bolt(g, int(e // self.CYCLE), 23, width=2, x0=64)
        if k < 2.4:
            for j in range(3):
                ring(g, HX, HY, 10 + (k * 40 + j * 12) % 60, 2)
        self.marks(g, STRIKES if k < 2.6 else 0, t)
        if 0.3 < k < 2.8:
            g.d.rectangle((14, 4, 50, 34), fill=0)
            g.text(32, 6, "轰", scale=2, align="center")
        self.label(g)
        if k < 0.12:
            g.invert()
        mx_trigram(g, "震")
        if k < 0.5:
            g.mx[:] = True
            g.mx_level = 8
        elif k < 2.0:
            g.mx_level = 3

    def interrupt(self, g: Gfx, t: float, e: float):
        n, p, since = self.state(e)
        curl = ease_in_out(span(t, 0, 0.9))
        self.clouds(g, p * (1 - curl), t, spread=ease_out(span(t, 0.2, 1.4)) * 0.6)
        hand(g, 0, curl)
        if curl < 0.5:
            self.seal(g)
        if t < 0.4:
            self.sparks(g, t, p * (1 - t / 0.4))
        self.marks(g, n, t)
        self.label(g, "暂收" if t > 0.7 else "掌心雷")
        mx_trigram(g, "震")

    def resume(self, g: Gfx, t: float, e: float):
        n, p, since = self.state(e)
        curl = 1 - ease_out_back(span(t, 0.1, 0.9))
        back = ease_in_out(span(t, 0.2, 1.4))
        self.clouds(g, p * back, t, spread=(1 - back) * 0.6)
        hand(g, 0, clamp(curl))
        if curl < 0.5:
            self.seal(g)
        if t > 0.9:
            self.sparks(g, t, p)
            if t < 1.2:
                ring(g, HX, HY, 10 + (t - 0.9) * 50, 2)
        self.marks(g, n, t)
        self.label(g, "暂收" if t < 0.5 else "掌心雷")
        self.mx_zhen(g, t, p if t > 0.9 else 0)

    def complete(self, g: Gfx, t: float, e: float):
        n, p, since = self.state(e)
        hit = 1.0
        if t < 2.2:
            self.clouds(g, 1.0 if t > 0.3 else p, t, spread=ease_out(span(t, 1.2, 2.2)),
                        flash=1.0 if 0.9 < t < 1.05 else 0)
        hand(g)
        self.seal(g)
        if t < 0.9:
            self.sparks(g, t, 1.0)
            self.marks(g, int(span(t, 0, 0.8) * (STRIKES - n)) + n, t)
        if 0.9 < t < 1.5:
            self.bolt(g, 7, 41, width=2, x0=60)
        if t > 0.9:
            for j in range(4):  # 冲击波
                r = (t - 0.9) * 45 - j * 10
                if 0 < r < 90:
                    ring(g, HX, HY, r, 2 if j else 1)
        if t > 2.4:
            g.d.rectangle((0, 0, 127, 15), fill=0)
            typewriter(g, 64, 2, "急急如律令", t - 2.4, cps=5, align="center")
        self.label(g)
        if 0.9 < t < 1.02:
            g.invert()
        mx_trigram(g, "震")
        if 0.9 < t < 1.5:
            g.mx[:] = True
            g.mx_level = 8
        elif t > 1.5:
            r = (t - 1.5) * 4 % 6
            g.mx[:] = False
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.8:
                        g.mx[yy, xx] = True
            g.mx_level = 1 + int(3 * (1 - span(t, 1.5, 3.0)))
