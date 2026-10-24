"""卧数星斗：夜里躺在山坡上数星星，先数北斗七星（天枢、天璇、天玑、天权、玉衡、开阳、摇光），一颗颗连成斗；
再往下数，越数越慢，数着数着睡着了。一颗流星划过，惊醒，从头再数。北斗慢慢转，偶尔看见开阳旁的辅星。

依据：北斗七星（天枢至摇光）；道教《太上玄灵北斗本命延生真经》奉北斗七星君（贪狼、巨门、禄存、文曲、廉贞、武曲、破军）；
开阳旁的小星为“辅星”（Alcor），民间有“见辅星者长寿”之说；《鹖冠子·环流》：“斗柄东指，天下皆春。”
"""
from __future__ import annotations

import math

from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import stars, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Pen, backdrop, breathe, ev, iris, zzz

NAMES = ("天枢", "天璇", "天玑", "天权", "玉衡", "开阳", "摇光")
DIPPER = ((0, 0), (0, 8), (9, 11), (11, 4), (18, 2), (25, 1), (32, 5))   # 斗勺四星 + 斗柄三星
_DC = (sum(x for x, _ in DIPPER) / 7, sum(y for _, y in DIPPER) / 7)
CENTER = (46, 22)
HEAD = (106, 45)
CYCLE = 100.0
SEVEN = 3.0                    # 每数一颗北斗星
EXTRA = (2.0, 2.4, 2.9, 3.5, 4.3)   # 再往下数，越数越慢（八、九、十、十一、十二）
T_EXTRA = 7 * SEVEN
T_SLEEP = T_EXTRA + sum(EXTRA) + 1.5
T_METEOR = 88.0


def _bg():
    p = Pen()
    # 远处道观屋脊（飞檐）
    p.poly([(2, 52), (8, 49), (30, 49), (36, 52), (33, 53), (5, 53)], fill=0)
    p.line([(2, 52), (0, 50)])
    p.line([(36, 52), (38, 50)])
    p.rect((7, 54, 31, 60), fill=0.25)
    p.rect((17, 46, 21, 49), fill=1)
    # 山坡
    p.poly([(0, 64), (0, 60), (30, 58), (60, 54), (90, 50), (128, 48), (128, 64)], fill=0)
    p.line([(0, 60), (30, 58), (60, 54), (90, 50), (128, 48)])
    for i in range(16):
        x = int(rand(i, 11) * 128)
        y = 60 - x * 0.09 + 2 + int(rand(i, 12) * 4)
        p.px(x, y)
    for x in (40, 66, 74):
        y = 60 - x * 0.09
        p.line([(x, y), (x - 1, y - 3)])
        p.line([(x + 1, y), (x + 2, y - 3)])
    return p.image()


def _lying(awake: bool) -> Sprite:
    """仰卧，脸朝天，一只手枕在头下，一膝立起；头在右"""
    p = Pen(50, 16)
    y0 = 15
    p.poly([(4, y0), (4, 11), (12, 4), (16, 10), (30, 8), (37, 9), (37, y0)], fill=0.22)   # 身、立膝
    p.line([(12, 4), (10, y0)])
    p.rect((1, 12, 5, y0), fill=1)                                                    # 鞋
    p.line([(24, 8), (24, y0)])                                                       # 腰带
    p.poly([(33, 11), (46, 11), (47, y0), (33, y0)], fill=0.6)                        # 枕在头下的手臂
    p.ellipse((35, 2, 46, 13), fill=0)                                                # 头
    p.ellipse((45, 4, 49, 9), fill=1)                                                 # 发髻（朝右）
    p.px(39, 1)                                                                       # 鼻尖朝天
    if awake:
        p.rect((40, 4, 41, 5), fill=1)
    else:
        p.line([(39, 5), (42, 5)])
    return p.sprite()


_A = {}


def _assets():
    if not _A:
        _A.update(bg=_bg(), awake=_lying(True), sleep=_lying(False))


@register
class Stars(Rest):
    id = "x1.stars"
    name = "卧数星斗"
    desc = "夜卧山坡数星星：先数北斗七星连成斗，再越数越慢睡着；流星划过惊醒再数，北斗缓缓转、偶见辅星"
    T = {"enter": 2.8, "exit": 1.2}

    def setup(self):
        _assets()
        self._ht = 0.0
        self.rot0 = self.rng.random() * 2 * math.pi

    # ------------------------------------------------------------ 北斗

    def dipper_pts(self, t: float) -> list[tuple[float, float]]:
        a = self.rot0 + t * 2 * math.pi / 900      # 一刻钟转一圈（斗柄慢慢转向）
        c, s = math.cos(a), math.sin(a)
        out = []
        for x, y in DIPPER:
            dx, dy = (x - _DC[0]) * 1.15, (y - _DC[1]) * 1.15
            out.append((CENTER[0] + dx * c - dy * s, CENTER[1] + dx * s + dy * c))
        return out

    def dipper(self, g: Gfx, t: float, counted: int, fresh: float = 1.0, lines: float = 1.0):
        """画北斗：数过的星亮成十字，连线（虚线）"""
        pts = self.dipper_pts(t)
        for i in range(min(counted, 7) - 1):
            if lines <= 0:
                break
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            n = int(math.hypot(x1 - x0, y1 - y0) / 2)
            k = 1.0 if i < counted - 2 else fresh
            for j in range(1, int(n * k)):
                if j % 2 == 0 and rand(j + i * 31, 5) < lines:
                    g.px(lerp(x0, x1, j / n), lerp(y0, y1, j / n))
        if counted >= 7 and lines > 0:  # 斗勺闭合
            (x0, y0), (x1, y1) = pts[3], pts[0]
            n = int(math.hypot(x1 - x0, y1 - y0) / 2)
            for j in range(1, n):
                if j % 2 == 0 and rand(j + 999, 5) < lines:
                    g.px(lerp(x0, x1, j / n), lerp(y0, y1, j / n))
        for i, (x, y) in enumerate(pts):
            if i < counted:
                big = (i == counted - 1 and fresh < 1) or noise(t * 2 + i, 9) > 0.8
                g.d.rectangle((x, y, x + 1, y + 1), fill=1)
                if big:
                    for d in (2, 3):
                        g.px(x - d + 1, y)
                        g.px(x + d, y)
                        g.px(x, y - d + 1)
                        g.px(x, y + d)
            elif noise(t * 1.5 + i * 3, 4) > 0.25:
                g.px(x, y)

    def mx_dipper(self, g: Gfx, t: float, counted: int):
        pts = self.dipper_pts(t)
        for i, (x, y) in enumerate(pts):
            if i < counted or blink(t + i * 0.3):
                g.mx_set(round((x - CENTER[0]) / 5.2 + 3.5), round((y - CENTER[1]) / 5.2 + 3.5))

    # ------------------------------------------------------------ 数星

    def phase(self, t: float):
        """→ (阶段, 已数到几, 当前这颗的进度 0..1)"""
        u = t % CYCLE
        if u < T_EXTRA:
            n = int(u // SEVEN) + 1
            return "seven", n, (u % SEVEN) / SEVEN
        if u < T_SLEEP - 1.5:
            v = u - T_EXTRA
            for k, d in enumerate(EXTRA):
                if v < d:
                    return "extra", 8 + k, v / d
                v -= d
        if u < T_SLEEP:
            return "drowsy", 12, (u - (T_SLEEP - 1.5)) / 1.5
        if u < T_METEOR:
            return "sleep", 12, 0.0
        return "woke", 12, (u - T_METEOR) / (CYCLE - T_METEOR)

    def rising_num(self, g: Gfx, n: int, k: float, slow: float = 0.0):
        """从头上冒出的数字（像 Z 一样往上飘）"""
        s = cn_num(n)
        x = HEAD[0] - 6 - k * 14
        y = HEAD[1] - 10 - k * 16
        if k < 0.85 or int(k * 40) % 2:
            g.text(x, y, s, size=8, align="center")

    def extra_star(self, g: Gfx, n: int, cyc: int, a: float = 1.0):
        """“八”以后随便数的星星（每轮位置不同）"""
        for m in range(8, n + 1):
            x = 70 + rand(m + cyc * 13, self.seed) * 54
            y = 4 + rand(m + cyc * 13 + 50, self.seed) * 30
            g.d.rectangle((x, y, x + 1, y + 1), fill=1)
            if m == n and a < 1:
                r = 3 * (1 - a)
                g.d.line((x - r, y, x + r + 1, y), fill=1)
                g.d.line((x, y - r, x, y + r + 1), fill=1)

    def point(self, g: Gfx):
        """抬手指天"""
        g.d.line((98, 46, 94, 35), fill=0, width=4)
        g.d.line((98, 46, 94, 35), fill=1, width=2)
        g.d.line((94, 35, 93, 32), fill=1)

    def meteor(self, g: Gfx, u: float):
        """一颗流星从右上划向左下（u 0..1.2）"""
        k = ease_in(span(u, 0, 0.9))
        x, y = lerp(130, 60, k), lerp(2, 30, k)
        for j in range(12):
            g.px(x + j * 2, y - j * 0.8)
        g.d.rectangle((x - 1, y - 1, x, y), fill=1)

    # ------------------------------------------------------------ 阶段

    def sky(self, g: Gfx, t: float):
        stars(g, t, self.seed, n=26, box=(0, 0, 128, 44), twinkle=0.35)

    def enter(self, g: Gfx, t: float):
        backdrop(g, _A["bg"])
        a = span(t, 0.4, 2.6)
        stars(g, t, self.seed, n=int(26 * a), box=(0, 0, 128, 44), twinkle=0.35)
        self.dipper(g, t, 0)
        g.blit(_A["awake"], HEAD[0] - 41, HEAD[1] - 8)
        if t > 2.0:
            self.point(g)
        self.mx_dipper(g, t, 0)
        if t < 0.6:
            iris(g, 64, 32, ease_out(t / 0.6) * 150, 0.6)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        backdrop(g, _A["bg"])
        self.sky(g, t)
        ph, n, k = self.phase(t)
        cyc = int(t // CYCLE)
        u = t % CYCLE
        counted = min(n, 7)
        fade = 1.0
        if ph == "woke":                       # 醒来后旧的连线慢慢散掉
            fade = 1 - span(k, 0.4, 1.0)
        self.dipper(g, t, counted, fresh=ease_out(k * 1.6) if ph == "seven" else 1.0, lines=fade)
        if ph != "seven":
            self.extra_star(g, n if ph == "extra" else 12, cyc, k if ph == "extra" else 1.0)
        awake = ph in ("seven", "extra") or (ph == "woke" and k > 0.08)
        g.blit(_A["awake" if awake else "sleep"], HEAD[0] - 41, HEAD[1] - 8)
        if ph in ("seven", "extra"):
            self.rising_num(g, n, k)
            if ph == "seven" and k < 0.6:   # 手指着正在数的那颗
                self.point(g)
                g.d.rectangle((86, 0, 127, 13), fill=0)
                g.text(126, 1, NAMES[n - 1], align="right")
        elif ph == "drowsy":
            if int(k * 6) % 2 == 0:
                g.text(HEAD[0] - 20, HEAD[1] - 26, "十二…", size=8)
        elif ph == "sleep":
            zzz(g, HEAD[0] - 1, HEAD[1] - 8, u - T_SLEEP, self.seed, rise=18, drift=-12)
            fu = ev(t, 233.0, 9.0, 50.0)          # 辅星
            if fu and counted >= 6:
                x, y = self.dipper_pts(t)[5]
                if noise(t * 4, 2) > 0.3:
                    g.px(x + 3, y - 2)
                if fu[1] > 1.5:
                    typewriter(g, x + 5, y - 10, "辅星", fu[1] - 1.5, cps=3, size=8)
        if T_METEOR - 0.6 < u < T_METEOR + 0.6:
            self.meteor(g, u - (T_METEOR - 0.6))
        if ph == "woke" and k < 0.35:
            g.text(HEAD[0] - 2, HEAD[1] - 22, "!", size=12)
        self.mx_dipper(g, t, counted)
        if ph == "woke" and k < 0.1:
            g.mx_level = 4

    def exit(self, g: Gfx, t: float):
        """起身前最后一眼：北斗七星一齐亮起连成斗，人睁眼，画面收拢到他身上"""
        h = self._ht
        backdrop(g, _A["bg"])
        self.sky(g, h + t)
        ph, n, _ = self.phase(h)
        lit = 7 if t > 0.2 else min(n, 7)
        self.dipper(g, h, lit, fresh=1.0, lines=span(t, 0.2, 0.5))
        awake = t > 0.15 or ph in ("seven", "extra", "woke")
        g.blit(_A["awake"] if awake else _A["sleep"], HEAD[0] - 41, HEAD[1] - 8)
        if awake:
            self.point(g)
        self.mx_dipper(g, h, lit)
        if 0.2 < t < 0.5:
            g.mx_level = 4
        iris(g, HEAD[0] - 4, HEAD[1] - 4, lerp(120, 0, ease_in_out(span(t, 0.45, self.T["exit"] - 0.05))), 0.8)


def blink(t: float) -> bool:
    return (t % 1.2) < 0.6
