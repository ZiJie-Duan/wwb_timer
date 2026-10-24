"""供果：供桌上一只高脚果盘，一只手一颗一颗码上鲜果，码成宝塔，塔尖一颗寿桃；两旁花瓶插花。

依据：五供（香、花、灯、水、果），道教又称“五献”；《汉典》引道士语：“五献皆圆满，奉上众真前”。
供果常用桃（长寿）、橘（吉）、石榴等，码成塔形。

入场：果盘从上方落到供桌，手放下第一颗果。
持续：一轮 600 秒，每 54 秒手从右上伸来放一颗（共十颗：四、三、二、一，最上是寿桃），花枝轻摇，
      偶尔飘落一片花瓣。供满后寿桃闪光。一轮结束：果子从上到下化作光点升起（神明享供），再放第一颗；
      桌围上“第几盘”加一。
中断：一只纱罩从上落下罩住果盘。
恢复：纱罩提起离去。
圆满：果塔放光、果子依次轻跳，“五献皆圆满”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, \
    rand, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import rays, sleeve, sparkles

TABLE = 48
# 果塔：底四、三、二、顶一（寿桃）
SLOTS = [(49, 34), (59, 34), (69, 34), (79, 34), (54, 26), (64, 26), (74, 26), (59, 18), (69, 18), (64, 10)]
R = 5
STEP = 54.0
RENEW = 5.0
VASES = (19, 109)
MX_SLOTS = [(0, 6), (2, 6), (4, 6), (6, 6), (1, 5), (3, 5), (5, 5), (2, 4), (4, 4), (3, 3)]


def orange(g: Gfx, x: float, y: float, r: float = R):
    x, y = round(x), round(y)
    g.d.ellipse((x - r, y - r, x + r, y + r), fill=0, outline=1)
    g.px(x, y - r - 1)
    g.d.line((x + 1, y - r - 1, x + 3, y - r - 2), fill=1)  # 小叶
    g.px(x - 2, y - 2)
    g.px(x - 3, y - 1)
    g.px(x + 2, y + 2)  # 橘皮麻点
    g.px(x - 1, y + 3)


def peach(g: Gfx, x: float, y: float, r: float = R, big: bool = False):
    x, y = round(x), round(y)
    g.d.ellipse((x - r, y - r + 1, x + r, y + r), fill=0, outline=1)
    g.d.polygon([(x - 2, y - r + 2), (x + 1, y - r - 2), (x + 3, y - r + 2)], fill=0, outline=1)  # 桃尖
    g.d.line((x + 1, y - r - 1, x - 1, y + r - 2), fill=1)  # 桃缝
    g.d.line((x - 2, y - r + 1, x - r - 2, y - r - 1), fill=1)  # 叶
    g.d.line((x - 3, y - r + 2, x - r - 1, y - r + 1), fill=1)
    if big:
        g.d.line((x + 3, y - r + 1, x + r + 2, y - r - 1), fill=1)
        g.d.line((x + 3, y - r + 2, x + r + 1, y - r + 1), fill=1)
        for dx, dy in ((-3, 1), (-2, 3), (-4, 3), (-3, 5), (3, 2), (4, 4)):  # 红晕
            g.px(x + dx, y + dy)


def plate(g: Gfx, dy: float = 0):
    d = g.d
    y = 39 + dy
    d.polygon([(41, y), (87, y), (80, y + 4), (48, y + 4)], fill=0, outline=1)
    d.line((44, y + 2, 84, y + 2), fill=1)
    d.rectangle((61, y + 5, 67, y + 7), fill=0, outline=1)
    d.polygon([(54, y + 9), (74, y + 9), (69, y + 8), (59, y + 8)], fill=0, outline=1)


def table(g: Gfx, label: str):
    d = g.d
    d.line((0, TABLE, 127, TABLE), fill=1)
    d.line((0, TABLE + 2, 127, TABLE + 2), fill=1)
    g.shade((0, TABLE + 3, 128, 64), 0.18)
    for x in range(6, 128, 16):  # 桌围流苏纹
        d.line((x, TABLE + 3, x + 4, TABLE + 7), fill=1)
        d.line((x + 8, TABLE + 7, x + 12, TABLE + 3), fill=1)
    if label:
        w = len(label) * 12 + 6
        d.rectangle((64 - w // 2, TABLE + 3, 64 + w // 2, 64), fill=0, outline=1)
        g.text(64, TABLE + 5, label, align="center")


def vase(g: Gfx, x: int, t: float, seed: int):
    d = g.d
    d.ellipse((x - 8, 34, x + 8, TABLE), fill=0, outline=1)
    d.rectangle((x - 3, 29, x + 3, 35), fill=0, outline=1)
    d.line((x - 5, 29, x + 5, 29), fill=1)
    d.line((x - 7, 39, x + 7, 39), fill=1)  # 瓶身花带
    d.line((x - 7, 43, x + 7, 43), fill=1)
    for k in range(-6, 7, 3):
        g.px(x + k, 41)
    tips = []
    for i, (dx, h) in enumerate(((-7, 16), (0, 22), (7, 13))):
        sway = (noise(t * 0.6 + i * 3, seed + i) - 0.5) * 3
        bx, by = x + dx + sway, 29 - h
        d.line((x + i - 1, 29, (x + bx) / 2, (29 + by) / 2 + 2, bx, by), fill=1)
        lx, ly = (x + bx) / 2, (29 + by) / 2 + 3
        d.polygon([(lx, ly), (lx + (4 if i != 1 else -4), ly - 3), (lx + (2 if i != 1 else -2), ly)], fill=1)  # 叶
        # 花：圆朵 + 花心
        d.ellipse((bx - 2.5, by - 2.5, bx + 2.5, by + 2.5), fill=0, outline=1)
        g.px(bx, by)
        if i == 1:  # 花苞
            d.ellipse((bx + 3, by + 5, bx + 5, by + 7), fill=1)
        tips.append((bx, by))
    return tips


@register
class FruitOffering(Ritual):
    id = "r1.fruit"
    name = "供果"
    desc = "供桌高脚盘，手一颗颗码上鲜果成塔、塔尖寿桃；供满神享化光，再供一盘"
    T = {"enter": 3.8, "interrupt": 1.6, "resume": 1.6, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.kinds = [self.rng.random() < 0.5 for _ in range(9)] + [True]

    def fruit(self, g: Gfx, i: int, x: float, y: float, r: float = R):
        if i == 9:
            peach(g, x, y, r + 1, big=True)
        elif self.kinds[i]:
            peach(g, x, y, r)
        else:
            orange(g, x, y, r)

    def count(self, k: float) -> int:
        return min(10, int(k // STEP) + 1)

    def scene(self, g: Gfx, t: float, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        table(g, label if label is not None else f"第{cn_num(n)}盘")
        tips = []
        for x in VASES:
            tips += vase(g, x, t, self.seed + x)
        plate(g)
        return tips

    def pile(self, g: Gfx, n: int, scale=None, dy=None):
        for i in range(n):
            x, y = SLOTS[i]
            s = 1.0 if scale is None else scale(i)
            if s <= 0:
                continue
            yy = y + (0 if dy is None else dy(i))
            self.fruit(g, i, x, yy, max(1, round(R * s)))

    def petal(self, g: Gfx, t: float, tips):
        """每 17 秒一片花瓣从花上飘落"""
        k = t % 17
        if k > 4 or not tips:
            return
        j = int(t // 17) % len(tips)
        bx, by = tips[j]
        y = by + k * (TABLE - by) / 4
        x = bx + math.sin(k * 3) * 3 + k * (2 if bx < 64 else -2)
        g.px(x, y)
        g.px(x + 1, y)

    def mx(self, g: Gfx, n: int, t: float, newest: int | None = None):
        g.mx[7, 1:7] = True
        for i in range(n):
            x, y = MX_SLOTS[i]
            if i == newest and not blink(t, 0.3):
                continue
            g.mx_set(x, y)
            g.mx_set(x + 1, y)

    def hand_with(self, g: Gfx, i: int, p: float, holding: bool):
        """手把第 i 颗果从右上送到位（p 0 = 画外，1 = 到位）"""
        x, y = SLOTS[i]
        q = ease_out(p) if holding else p
        hx, hy = lerp(150, x + 2, q), lerp(-30, y - 9, q)
        if holding:
            self.fruit(g, i, hx - 2, hy + 9)
        sleeve(g, hx, hy, -0.85)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        table(g, "")
        for x in VASES:
            vase(g, x, t, self.seed + x)
        drop = ease_out_bounce(span(t, 0, 0.9))
        plate(g, dy=lerp(-50, 0, drop))
        if 1.0 <= t < 2.2:
            self.hand_with(g, 0, span(t, 1.0, 2.2), True)
        elif t >= 2.2:
            self.pile(g, 1, dy=lambda i: -2 * (1 - ease_out_bounce(span(t, 2.2, 2.5))))
            if t < 3.2:
                self.hand_with(g, 0, 1 - ease_in(span(t, 2.3, 3.2)), False)
        if t > 2.8:
            w = span(t, 2.8, 3.6)
            s = "第一盘"[:int(round(w * 3))]
            if s:
                g.d.rectangle((43, TABLE + 3, 85, 64), fill=0, outline=1)
                g.text(64, TABLE + 5, s, align="center")
        self.mx(g, 1 if t > 2.2 else 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        tips = self.scene(g, t, e)
        n = self.count(k)
        nxt = n  # 下一颗
        land = k - (n - 1) * STEP  # 最新一颗放下多久了
        dy = None
        if n > 1 and land < 0.35:
            dy = lambda i: (-2 * (1 - ease_out_bounce(land / 0.35)) if i == n - 1 else 0)
        self.pile(g, n, dy=dy)
        if n == 10:
            x, y = SLOTS[9]
            sparkles(g, x, y - 2, 14, 10, t, n=5, seed=self.seed)
        if nxt < 10:  # 送下一颗
            due = nxt * STEP
            if due - 1.4 <= k < due:
                self.hand_with(g, nxt, span(k, due - 1.4, due - 0.2), True)
        if n > 1 and land < 0.9:
            self.hand_with(g, n - 1, 1 - ease_in(span(land, 0.05, 0.9)), False)
        self.petal(g, t, tips)
        self.mx(g, n, t, n - 1 if land < 2 else None)

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """神明享供：果子从上到下化作光点升起；再放第一颗"""
        self.scene(g, t, e, label=None if k > 2.6 else f"第{cn_num(int(e // self.CYCLE))}盘")

        def sc(i):
            start = (9 - i) * 0.2
            return 1 - ease_in(span(k, start, start + 0.6))

        if k < 2.8:
            self.pile(g, 10, scale=sc)
            for i in range(10):
                start = (9 - i) * 0.2
                q = span(k, start + 0.2, start + 1.2)
                if 0 < q < 1:
                    x, y = SLOTS[i]
                    for j in range(3):
                        g.px(x - 3 + j * 3 + math.sin(q * 6 + j) * 1.5, y - q * 30 - j * 3)
        if 2.6 <= k < 3.8:
            self.hand_with(g, 0, span(k, 2.6, 3.8), True)
        elif k >= 3.8:
            self.pile(g, 1, dy=lambda i: -2 * (1 - ease_out_bounce(span(k, 3.8, 4.1))))
            self.hand_with(g, 0, 1 - ease_in(span(k, 3.9, RENEW)), False)
        n = 10 if k < 1.0 else (1 if k >= 3.8 else 0)
        self.mx(g, n, t)
        if k < 2.6:
            g.mx[:7] = False
            r = int(k / 2.6 * 7)
            for i, (x, y) in enumerate(MX_SLOTS):
                if sc(i) > 0:
                    g.mx_set(x, y)
                    g.mx_set(x + 1, y)
                elif y - r >= 0:
                    g.mx_set(x, y - r)

    def _cover(self, g: Gfx, dy: float):
        """纱罩：半椭圆网罩，顶上一个提钮"""
        cx, cy, rx, ry = 64, 44 + dy, 29, 40
        if cy + 0 < -2:
            return
        for y in range(int(cy - ry), int(cy) + 1, 3):
            if not 0 <= y < 64:
                continue
            hw = rx * math.sqrt(max(0.0, 1 - ((y - cy) / ry) ** 2))
            off = (y // 3) % 2
            for x in range(int(cx - hw) + 1 + off, int(cx + hw), 3):
                g.px(x, y)
        g.d.arc((cx - rx, cy - ry, cx + rx, cy + ry), 180, 360, fill=1)
        g.d.line((cx - rx - 1, cy, cx + rx + 1, cy), fill=1)
        g.d.ellipse((cx - 2, cy - ry - 4, cx + 2, cy - ry), fill=0, outline=1)
        g.d.line((cx, cy - ry, cx, cy - 2), fill=1)  # 罩骨

    def interrupt(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        self.scene(g, t, e, label="暂歇" if t > 0.9 else None)
        n = self.count(k)
        self.pile(g, n)
        self._cover(g, lerp(-90, 0, ease_out_bounce(span(t, 0.1, 1.2))))
        self.mx(g, n, t)
        if t > 0.6:
            g.mx[0:7, 0] = True
            g.mx[0:7, 7] = True
            g.mx[0, :] = True

    def resume(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        self.scene(g, t, e, label="暂歇" if t < 0.6 else None)
        n = self.count(k)
        self.pile(g, n)
        p = ease_in(span(t, 0.2, 1.2))
        self._cover(g, lerp(-2 * math.sin(span(t, 0, 0.2) * math.pi), -100, p))
        self.mx(g, n, t)

    def complete(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n = self.count(k)
        label = "" if t > 1.4 else None
        self.scene(g, t, e, label=label)
        if t > 1.6:
            g.d.rectangle((31, TABLE + 3, 97, 64), fill=0, outline=1)
            typewriter(g, 64, TABLE + 5, "五献皆圆满", t - 1.6, cps=4, align="center")
        add = int(span(t, 0, 1.2) * (10 - n) + 0.999) if n < 10 else 0
        m = min(10, n + add)

        def dy(i):
            ph = t - 1.5 - i * 0.12
            return -3 * abs(math.sin(ph * 4)) if 0 < ph < 0.8 else 0

        self.pile(g, m, dy=dy)
        top = SLOTS[m - 1]
        glow = ease_out(span(t, 0.6, 1.6))
        if glow > 0:
            rays(g, top[0], top[1], 9 + glow * 2, 9 + glow * 8, n=10, rot=t * 0.6, a0=-math.pi - 0.3, a1=0.3)
        sparkles(g, 64, 24, 40, 20, t, n=12, seed=self.seed)
        self.mx(g, m, t)
        if 0.6 < t < 2.0:
            g.mx_level = 4 if blink(t, 0.3) else 2
