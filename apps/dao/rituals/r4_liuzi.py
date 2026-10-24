"""吐纳·六字诀：侧身半身像，鼻吸口呼。吸时天地清气聚入鼻中、小腹鼓起；呼时口型随字变化，
一口长气带着“嘘呵呼呬吹嘻”的字吐出去，飘散在山前。

依据：陶弘景《养性延命录·服气疗病》“纳气有一，吐气有六……吹、呼、唏、呵、嘘、呬，皆出气也”；
后世六字诀配五脏：嘘肝、呵心、呼脾、呬肺、吹肾、嘻三焦。《庄子·刻意》“吹呴呼吸，吐故纳新”。

入场：山前雾散，人显现，两手从体侧合到小腹（丹田），第一口气吸进来。
持续：一口气 10 秒（吸 4 秒，呼 6 秒），按 e 推进。一遍六字，每字 100 秒；一遍 10 分钟，“第几遍”加一。
中断：闭口，残气散尽，两手叠于丹田，“闭息”。
恢复：深吸一口，接着练。
圆满：最后一口长气，六个字连珠吐出，“吐故纳新”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register

BREATH = 10.0
INHALE = 4.0
WORD_S = 100.0
WORDS = [("嘘", "肝"), ("呵", "心"), ("呼", "脾"), ("呬", "肺"), ("吹", "肾"), ("嘻", "三焦")]
HEAD = (38, 21)
NOSE = (50, 21)
MOUTH = (48, 27)
DANTIAN = (44, 54)


def breath_state(e: float) -> tuple[float, float]:
    """→ (吸入量 0..1, 呼气进度 -1 = 在吸, 0..1 = 呼了多少)"""
    k = e % BREATH
    if k < INHALE:
        return ease_in_out(k / INHALE), -1.0
    q = (k - INHALE) / (BREATH - INHALE)
    return 1 - ease_in_out(q), q


@register
class Liuzi(Ritual):
    id = "r4.liuzi"
    name = "六字诀"
    desc = "侧身吐纳，鼻吸清气入丹田，口呼浊气，嘘呵呼呬吹嘻六字随长气吐出，飘散在山前"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 2.0, "complete": 5.5}
    CYCLE = WORD_S * len(WORDS)

    # ------------------------------------------------------------ 零件

    def hills(self, g: Gfx):
        d = g.d
        pts = [(60, 64), (70, 54), (78, 57), (90, 47), (100, 53), (108, 50), (128, 58), (128, 64)]
        d.polygon(pts, fill=0)
        g.shade_poly(pts, 0.12)
        for i in range(3):  # 云气
            y = 40 + i * 4
            x = 70 + i * 13
            d.line((x, y, x + 10, y), fill=1)

    def person(self, g: Gfx, fill: float, mouth: str = "close", hands: float = 1.0):
        """侧身半身像（面朝右）。fill：吸入量（小腹鼓起）；hands 0 = 垂在体侧，1 = 叠在丹田"""
        d = g.d
        b = fill * 2.5
        torso = [(24, 64), (22, 44), (26, 37), (34, 33), (44, 34), (51, 39), (52, 46), (53 + b, 54), (51 + b, 64)]
        d.polygon(torso, fill=0)
        g.shade_poly(torso, 0.25)
        d.line((41, 34, 47, 44), fill=1)                           # 交领
        d.line((37, 34, 46, 46), fill=1)
        d.line((26 + b * 0.2, 49, 52 + b, 49), fill=1)             # 腰带
        # 胳膊：袖子
        hx, hy = lerp(36, DANTIAN[0] + 4 + b * 0.6, hands), lerp(62, DANTIAN[1] + 1, hands)
        arm = [(29, 38), (36, 37), (39, 47), (hx + 2, hy - 3), (hx + 2, hy + 3), (34, 53), (28, 46)]
        d.polygon(arm, fill=0, outline=1)
        d.ellipse((hx, hy - 2, hx + 4, hy + 2), fill=1)
        # 头：白的是头发（脑后、头顶、发髻），脸是黑底白描
        x, y = HEAD
        d.polygon([(34, 29), (43, 29), (43, 35), (34, 35)], fill=0, outline=1)  # 颈
        d.ellipse((x - 10, y - 11, x + 9, y + 9), fill=1)
        d.ellipse((x - 3, y - 7, x + 10, y + 10), fill=0)                       # 脸
        d.arc((x - 3, y - 7, x + 10, y + 10), 250, 110, fill=1)
        d.polygon([(x + 9, y - 3), (x + 13, y + 1), (x + 9, y + 2)], fill=0, outline=1)  # 鼻
        d.line((x + 9, y + 2, x + 9, y + 3), fill=0)
        d.arc((x - 3, y - 2, x + 2, y + 5), 90, 270, fill=1)                    # 耳
        d.ellipse((x - 12, y - 17, x - 3, y - 8), fill=1)                       # 发髻
        d.line((x - 15, y - 13, x + 1, y - 12), fill=1)                         # 簪
        d.line((x + 3, y - 2, x + 6, y - 1), fill=1)                            # 闭目
        d.line((x + 2, y - 4, x + 6, y - 4), fill=1)                            # 眉
        # 嘴（随字）
        mx, my = MOUTH
        # 脸的轮廓在嘴这里断开、按口型画
        d.rectangle((mx - 1, my - 2, mx + 3, my + 3), fill=0)
        if mouth == "close":
            d.line((mx - 3, my, mx + 1, my), fill=1)
            d.line((mx + 1, my - 2, mx + 1, my + 3), fill=1)
        elif mouth in ("呵", "open"):        # 张大口
            d.line((mx - 2, my - 1, mx + 1, my - 2), fill=1)
            d.line((mx - 2, my + 1, mx + 1, my + 3), fill=1)
        elif mouth == "呼":                  # 撮圆
            d.ellipse((mx - 1, my - 1, mx + 2, my + 2), outline=1)
        elif mouth == "吹":                  # 嘴唇向前撅
            d.line((mx, my - 1, mx + 3, my - 1), fill=1)
            d.line((mx, my + 1, mx + 3, my + 1), fill=1)
        elif mouth == "嘻":                  # 咧开
            d.line((mx - 4, my - 1, mx + 1, my - 1), fill=1)
            d.line((mx - 4, my - 1, mx - 3, my + 1), fill=1)
            d.line((mx - 3, my + 1, mx + 1, my + 1), fill=1)
        elif mouth == "呬":                  # 齿相合
            d.line((mx - 2, my - 1, mx + 1, my - 1), fill=1)
            d.line((mx - 2, my + 1, mx + 1, my + 1), fill=1)
            d.point((mx + 1, my), fill=1)
        else:                                # 嘘：两唇微合、留缝
            d.line((mx - 2, my - 1, mx + 2, my - 1), fill=1)
            d.line((mx - 2, my + 1, mx + 1, my + 2), fill=1)
        d.line((mx + 1, my + 3, mx - 1, my + 6), fill=1)           # 下巴

    def inhale_fx(self, g: Gfx, k: float, t: float, amt: float = 1.0):
        """清气从四面八方聚向鼻子"""
        nx, ny = NOSE
        for j in range(14):
            ph = (k * 1.4 + rand(j, self.seed) * 0.8) % 1.0
            if ph > k * 1.8 or amt <= 0:
                continue
            a = -0.9 + rand(j + 40, self.seed) * 1.9
            r = 70 * (1 - ease_in(ph)) + 3
            x = nx + math.cos(a) * r * 1.1
            y = ny + math.sin(a) * r * 0.55
            if 0 < r:
                g.px(x, y)
                if r > 20:
                    g.px(x + math.cos(a) * 2, y + math.sin(a) * 1)

    def exhale_fx(self, g: Gfx, q: float, word: str, t: float, big: bool = True):
        """一口长气：三道波纹从嘴里出来，字骑在气头上往右飘，然后散开"""
        mx, my = MOUTH
        head = 4 + ease_out(q) * 70
        tail = max(0.0, ease_in(q) * 70 - 6)
        for j in range(3):
            pts = []
            x = mx + 3 + tail
            while x < mx + 3 + head:
                dx = x - mx
                amp = 1 + dx * 0.08
                yy = my + (j - 1) * (2 + dx * 0.09) + math.sin(dx * 0.25 - t * 8 + j) * amp * 0.6
                pts.append((x, yy))
                x += 2
            for i, p in enumerate(pts):
                if (i + j) % 3 != 2:
                    g.px(*p)
        if word:
            fade = 1 - span(q, 0.7, 1.0)
            wx = mx + 8 + ease_out(q) * 32
            wy = my - 14 - math.sin(q * math.pi) * 4
            if fade > 0:
                g.text(wx, wy, word, scale=2 if big else 1)
                if fade < 1:
                    g.fade(fade, (int(wx), int(wy) - 1, int(wx) + 26, int(wy) + 26))

    def dan(self, g: Gfx, fill: float, t: float):
        x, y = DANTIAN
        if fill > 0.05:
            ring(g, x - 4, y - 1, 3 + fill * 5, 2, t)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        i = int((e % self.CYCLE) // WORD_S)
        w, organ = WORDS[i]
        r = right if right is not None else f"{w}字诀"
        g.vtext(115, 2, r[:int(round(len(r) * a))])
        n = int(e // self.CYCLE) + 1
        left = f"第{cn_num(n)}遍"
        g.vtext(2, 2, left[:int(round(len(left) * a))])

    def mx(self, g: Gfx, fill: float, q: float, t: float):
        r = fill * 3.6
        for y in range(8):
            for x in range(8):
                dd = max(abs(x - 3.5), abs(y - 3.5))
                if abs(dd - r) < 0.6 or dd < 0.6 + r * 0.3:
                    g.mx[y, x] = True
        if q >= 0:  # 呼：点从中间往右飞
            for j in range(3):
                k = (q * 3 + j / 3) % 1
                g.mx_set(3 + int(k * 5), 3 + (j % 2))

    # ------------------------------------------------------------ 阶段

    def word(self, e: float) -> str:
        return WORDS[int((e % self.CYCLE) // WORD_S)][0]

    def frame(self, g: Gfx, t: float, e: float):
        fill, q = breath_state(e)
        w = self.word(e)
        self.hills(g)
        self.person(g, fill, mouth=w if q >= 0 and q < 0.92 else "close")
        if q < 0:
            self.inhale_fx(g, (e % BREATH) / INHALE, t)
        else:
            self.exhale_fx(g, q, w, t)
        self.dan(g, fill, t)
        return fill, q

    def hold(self, g: Gfx, t: float, e: float):
        fill, q = self.frame(g, t, e)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < 3.0:  # 新一遍：上方提示
            typewriter(g, 72, 2, f"第{cn_num(int(e // self.CYCLE) + 1)}遍", k, cps=5, align="center")
            if k > 2.4:
                g.fade(1 - span(k, 2.4, 3.0), (50, 0, 100, 14))
        self.texts(g, e)
        self.mx(g, fill, q, t)

    def enter(self, g: Gfx, t: float):
        self.hills(g)
        hands = ease_in_out(span(t, 1.2, 2.6))
        self.person(g, 0.0, hands=hands)
        k = span(t, 0, 1.4)
        if k < 1:
            g.fade(ease_in_out(k), (16, 0, 64, 64))
        if t > 1.0:
            typewriter(g, 84, 18, "吐纳", t - 1.0, cps=4, align="center")
            if t > 3.0:
                g.fade(1 - span(t, 3.0, 4.0), (60, 16, 110, 31))
        self.texts(g, 0, a=span(t, 3.0, 4.0))
        self.mx(g, 0.0, -1, t)
        g.mx[3:5, 3:5] = blink(t, 0.6)

    def interrupt(self, g: Gfx, t: float, e: float):
        fill, q = breath_state(e)
        f2 = lerp(fill, 0.3, ease_in_out(span(t, 0, 1.0)))
        self.hills(g)
        self.person(g, f2, mouth="close")
        if q >= 0:  # 残气散尽
            self.exhale_fx(g, lerp(q, 1.0, ease_out(span(t, 0, 1.2))), self.word(e), t)
        self.texts(g, e, right="闭息")
        self.mx(g, f2, -1, t)

    def resume(self, g: Gfx, t: float, e: float):
        fill, q = breath_state(e)
        self.hills(g)
        if t < 1.4:  # 深吸一口
            k = span(t, 0, 1.4)
            f2 = lerp(0.3, 1.0, ease_in_out(k))
            self.person(g, f2, mouth="close")
            self.inhale_fx(g, k, t)
            self.dan(g, f2, t)
            self.texts(g, e, right="闭息" if t < 0.5 else None)
            self.mx(g, f2, -1, t)
        else:  # 接回 hold
            k = ease_in_out(span(t, 1.4, 2.0))
            f2 = lerp(1.0, fill, k)
            self.person(g, f2, mouth=self.word(e) if q >= 0 and q < 0.92 and k > 0.5 else "close")
            if q >= 0 and k > 0.5:
                self.exhale_fx(g, q, self.word(e), t)
            elif q < 0:
                self.inhale_fx(g, (e % BREATH) / INHALE, t)
            self.dan(g, f2, t)
            self.texts(g, e)
            self.mx(g, f2, q, t)

    def complete(self, g: Gfx, t: float, e: float):
        fill, q = breath_state(e)
        self.hills(g)
        # 先吸满（0-1.2），再一口长气把六个字连珠吐出（1.2-4.2）
        if t < 1.2:
            k = span(t, 0, 1.2)
            f2 = lerp(fill, 1.0, ease_in_out(k))
            self.person(g, f2, mouth="close")
            self.inhale_fx(g, k, t)
            self.texts(g, e, a=1 - k)
            self.mx(g, f2, -1, t)
            return
        k = span(t, 1.2, 4.2)
        self.person(g, 1 - ease_in_out(k), mouth="open" if k < 0.95 else "close")
        self.exhale_fx(g, k, "", t)
        mx_, my_ = MOUTH
        for i, (w, _) in enumerate(WORDS):  # 六字连珠
            s = span(t, 1.3 + i * 0.35, 3.3 + i * 0.35)
            if 0 < s < 1:
                x = mx_ + 6 + ease_out(s) * 52
                y = my_ - 6 + math.sin(s * math.pi * 2 + i) * 8 - s * 6
                g.text(x, y, w)
                if s > 0.6:
                    g.fade(1 - span(s, 0.6, 1.0), (int(x), int(y) - 1, int(x) + 13, int(y) + 12))
        if t > 3.6:
            typewriter(g, 84, 2, "吐故纳新", t - 3.6, cps=5, align="center")
        self.dan(g, 1 - k, t)
        self.mx(g, 1 - k, k, t)
        if t > 3.6:
            g.mx_level = 3 if t < 4.0 else 1
