"""吹龙角：法师吹响龙角（牛角号），角声一阵阵传出，天兵乘云一个个降到云头列阵，一轮满则开拔。

龙角（牛角、号角）是闾山、正一等派常用法器，开坛召营时吹角，以号令兵马、通达三界。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r3_kit import round_of, side_text, sleeve, sparkle

P0, P1, P2 = (-3, 40), (30, 66), (46, 20)    # 号角中线（贝塞尔）：吹口 → 喇叭口
HOLD_S = 0.3                                 # 手握的位置
BLAST = 10.0                                  # 吹一声的周期
BLOW = 3.2                                    # 每声吹多久
ROWS = [(31, 64), (45, 66), (59, 62)]         # 列阵：每排 (脚底 y, 起始 x)
PER_ROW = 6
N = len(ROWS) * PER_ROW
RENEW = 4.0

SOLDIER = Sprite("""
#.....
#.##..
#.##..
######
#.##.#
#.##..
#.#.#.
#.#.#.
""")


def bez(s: float):
    a = (1 - s) ** 2
    b = 2 * (1 - s) * s
    c = s * s
    x = a * P0[0] + b * P1[0] + c * P2[0]
    y = a * P0[1] + b * P1[1] + c * P2[1]
    dx = 2 * (1 - s) * (P1[0] - P0[0]) + 2 * s * (P2[0] - P1[0])
    dy = 2 * (1 - s) * (P1[1] - P0[1]) + 2 * s * (P2[1] - P1[1])
    ln = math.hypot(dx, dy) or 1
    return x, y, dx / ln, dy / ln


def _rot(x: float, y: float, a: float, ox: float, oy: float):
    c, s_ = math.cos(a), math.sin(a)
    return ox + (x - ox) * c - (y - oy) * s_, oy + (x - ox) * s_ + (y - oy) * c


def horn(g: Gfx, ang: float = 0.0, shake: float = 0.0, dy: float = 0.0):
    """牛角号：绕握处转 ang、整体下移 dy；shake 吹响时的微颤"""
    hx, hy, _, _ = bez(HOLD_S)
    left, right = [], []
    for i in range(15):
        s = i / 14
        x, y, tx, ty = bez(s)
        w = 1.5 + 7 * s ** 2
        nx, ny = -ty, tx
        y += shake * math.sin(i * 1.3)
        lx_, ly_ = _rot(x + nx * w, y + ny * w, ang, hx, hy)
        rx_, ry_ = _rot(x - nx * w, y - ny * w, ang, hx, hy)
        left.append((lx_, ly_ + dy))
        right.append((rx_, ry_ + dy))
    hy += dy
    g.d.polygon(left + right[::-1], fill=0, outline=1)
    for s in (0.22, 0.5, 0.72, 0.9):  # 角上的箍
        i = int(s * 14)
        g.d.line((left[i], right[i]), fill=1)
    # 喇叭口：椭圆
    (lx, ly), (rx, ry) = left[-1], right[-1]
    cx, cy = (lx + rx) / 2, (ly + ry) / 2
    g.d.line((lx, ly, rx, ry), fill=1)
    g.d.line(((lx + cx) / 2 + 1, (ly + cy) / 2, (rx + cx) / 2 + 1, (ry + cy) / 2), fill=1)
    # 握角的手 + 袖
    sleeve(g, hx - 2, hy + 5, 2.2, length=40, w0=12, w1=28, shade=0.25)
    g.d.rounded_rectangle((hx - 4, hy - 4, hx + 5, hy + 6), radius=3, fill=0, outline=1)
    g.d.line((hx - 3, hy - 1, hx + 3, hy - 2), fill=1)
    g.d.line((hx - 3, hy + 2, hx + 3, hy + 1), fill=1)
    return cx, cy


def mouth_dir(ang: float):
    x, y, tx, ty = bez(1.0)
    c, s_ = math.cos(ang), math.sin(ang)
    return math.atan2(tx * s_ + ty * c, tx * c - ty * s_)


def cloud_row(g: Gfx, y: float, x0: float, x1: float, t: float, seed: int = 0):
    """一排云头（脚下）"""
    x = x0
    i = 0
    while x < x1:
        r = 3 + rand(i, seed) * 2
        dx = math.sin(t * 0.8 + i) * 0.6
        g.d.arc((x + dx - r, y - r + 1, x + dx + r, y + r + 1), 180, 360, fill=1)
        x += r * 1.5
        i += 1
    g.d.line((x0 - 2, y + 2, x1 + 2, y + 2), fill=1)


@register
class DragonHorn(Ritual):
    id = "r3.longjiao"
    name = "吹龙角"
    desc = "吹响龙角，角声一阵阵荡出，天兵乘云一个个降到云头列阵；三排列满则齐齐开拔"
    T = {"enter": 3.5, "interrupt": 1.4, "resume": 1.8, "complete": 5.5}
    CYCLE = 540.0

    # ------------------------------------------------------------ 零件

    def arrive(self, k: float) -> list[float]:
        """各天兵的到达进度 0..1（每 30 秒一位，吹角之后降下）"""
        per = self.CYCLE / N
        return [clamp((k - (i * per + BLOW + 0.5)) / 1.6) for i in range(N)]

    def slot(self, i: int):
        row = i // PER_ROW
        col = i % PER_ROW
        y, x0 = ROWS[2 - row]  # 先站前排（下），再往后排
        return x0 + col * 10, y

    def army(self, g: Gfx, arr: list[float], t: float, lift: float = 0.0, raise_: float = 0.0):
        for r, (y, x0) in enumerate(ROWS):
            row = 2 - r
            if any(arr[row * PER_ROW + c] > 0 for c in range(PER_ROW)) or lift > 0:
                cloud_row(g, y + 1 - lift * (70 + r * 8), x0 - 3, x0 + PER_ROW * 10 - 2, t, r)
        for i, p in enumerate(arr):
            if p <= 0:
                continue
            x, y = self.slot(i)
            row = 2 - i // PER_ROW
            q = ease_out_bounce(p)
            yy = lerp(-12, y - 8, q) - lift * (70 + row * 8)
            g.blit(SOLDIER, x, yy)
            spear = 4 + int(raise_ * 2)
            g.d.line((x, yy - 1, x, yy - spear), fill=1)
            g.px(x - 1, yy - spear + 1)
            g.px(x + 1, yy - spear + 1)
            if p < 1:  # 驾一小朵云降下
                g.d.arc((x - 2, yy + 6, x + 8, yy + 12), 180, 360, fill=1)
                if p > 0.55:
                    sparkle(g, x + 3, y - 4, 2)

    def waves(self, g: Gfx, u: float, ang: float, cx: float, cy: float, amp: float = 1.0, dur: float = BLOW):
        """角声：从喇叭口往外荡的弧"""
        d = mouth_dir(ang)
        for j in range(8):
            age = u - j * 0.38
            if age < 0 or u - age > dur:  # 只在吹的那几秒里发出
                continue
            r = 4 + age * 30
            if r > 64 * amp + 4:
                continue
            spread = 0.75
            n = int(r * spread * 2 / 2) + 3
            for i in range(n):
                a = d - spread + i / (n - 1) * spread * 2
                if (i + j) % 2 and age > 0.8:
                    continue
                g.px(cx + math.cos(a) * r, cy + math.sin(a) * r)

    def mx(self, g: Gfx, arr: list[float], blowing: bool, t: float):
        for i, p in enumerate(arr):
            if p >= 1:
                row = i // PER_ROW
                g.mx_set(1 + i % PER_ROW, 7 - row * 2)
        if blowing:
            k = int(t * 6) % 4
            for x in range(8):
                g.mx_set(x, 1 if (x + k) % 4 < 2 else 0)
        else:
            g.mx[0, 0:2] = True

    def texts(self, g: Gfx, a: float = 1.0, s: str = "鸣角"):
        side_text(g, 2, 2, s, a)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        up = ease_out_back(span(t, 0, 1.2))
        ang = lerp(0.3, 0, up)
        u = t - 1.4
        shake = 0.5 if 0 < u < BLOW else 0
        cx, cy = horn(g, ang, shake * math.sin(t * 40), dy=lerp(40, 0, up))
        if u > 0:
            self.waves(g, u, ang, cx, cy)
        self.texts(g, span(t, 2.4, 3.3))
        self.mx(g, [0.0] * N, 0 < u < BLOW, t)

    def hold(self, g: Gfx, t: float, e: float):
        n, k, _ = round_of(e, self.CYCLE)
        if n > 1 and k < RENEW:
            # 续：满阵天兵举枪，连云带人往上开拔出画
            lift = ease_in(span(k, 0.8, 3.4))
            self.army(g, [1.0] * N, t, lift=lift, raise_=1)
            cx, cy = horn(g)
            self.texts(g, s="开拔")
            self.mx(g, [1.0 if k < 2 else 0.0] * N, False, t)
            return
        u = (k + 2.1) % BLAST  # 与入场的那一声接上
        blowing = u < BLOW
        shake = 0.5 * math.sin(t * 40) if blowing else 0
        self.army(g, self.arrive(k), t)
        cx, cy = horn(g, -0.05 * math.sin(min(u, BLOW) / BLOW * math.pi) if blowing else 0, shake)
        self.waves(g, u, 0, cx, cy)
        self.texts(g)
        self.mx(g, self.arrive(k), blowing, t)
        g.mx_level = 2 if blowing and u < 0.3 else 1

    def interrupt(self, g: Gfx, t: float, e: float):
        _, k, _ = round_of(e, self.CYCLE)
        p = ease_in_out(span(t, 0.1, 1.1))
        self.army(g, self.arrive(k), t)
        horn(g, 0.3 * p, dy=22 * p)
        self.texts(g, s="歇角" if t > 0.5 else "鸣角")
        self.mx(g, self.arrive(k), False, t)

    def resume(self, g: Gfx, t: float, e: float):
        _, k, _ = round_of(e, self.CYCLE)
        p = ease_out_back(span(t, 0, 0.9))
        ang = lerp(0.3, 0, p)
        u = t - 0.9
        self.army(g, self.arrive(k), t)
        cx, cy = horn(g, ang, 0.5 * math.sin(t * 40) if u > 0 else 0, dy=lerp(22, 0, p))
        if u > 0:
            self.waves(g, u, ang, cx, cy)
        self.texts(g)
        self.mx(g, self.arrive(k), u > 0, t)

    def complete(self, g: Gfx, t: float, e: float):
        _, k, _ = round_of(e, self.CYCLE)
        base = self.arrive(k)
        # 一声长角：余下的天兵一齐降下；然后举枪、开拔
        arr = [max(b, clamp((t - 0.6 - (i % PER_ROW) * 0.08) / 1.2)) for i, b in enumerate(base)]
        raise_ = span(t, 2.4, 2.7)
        lift = ease_in(span(t, 3.0, 4.3))
        self.army(g, arr, t, lift=lift, raise_=raise_)
        blowing = t < 3.0
        cx, cy = horn(g, 0, 0.6 * math.sin(t * 40) if blowing else 0)
        if blowing:
            self.waves(g, t, 0, cx, cy, dur=3.0)
        if t > 3.9:
            typewriter(g, 89, 44, "兵马齐至", t - 3.9, cps=6, align="center")
            self.texts(g)
        else:
            self.texts(g)
        self.mx(g, arr, blowing, t)
        g.mx_level = 1 + int(4 * span(t, 2.0, 2.4) * (1 - span(t, 2.6, 4.0)))
