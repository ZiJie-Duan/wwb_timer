"""令牌拍案：法师执五雷令牌拍击法案发号施令，东南西北中五营兵马的令旗一面面应令而至。

令牌（五雷令牌）木制长方，正面刻“令”或“五雷号令”，明《上清灵宝济度大成金书》载其以雷击枣木制成。
行法时以令牌击案，调遣兵将；民间道坛与闾山法有“五营兵马”（东南西北中五营）的说法。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r3_kit import nth, round_of, sleeve, sparkle

CX = 64
TOP = 51                  # 案面
CW, CH = 26, 32           # 令牌宽高
SLAM = 20.0               # 每隔多少秒拍一次
FLAGS = [("东", 3, 0), ("南", 19, 0), ("西", 109, 0), ("北", 125, 0), ("中", 64, 1)]
ARRIVE = [i * 120 + 31.05 for i in range(5)]   # 本轮内各营到达时刻
RENEW = 4.0


def slam_pose(u: float) -> tuple[float, float, float]:
    """一拍之内（u 秒）：→ (令牌离案高度, 手的进出 0..1, 冲击 0..1)"""
    hand = span(u, 0, 0.4) * (1 - span(u, 1.5, 2.0))
    if u < 0.4:
        return 0.0, ease_out(hand), 0.0
    if u < 0.9:
        return 14 * ease_out(span(u, 0.4, 0.9)), 1.0, 0.0
    if u < 1.02:
        return 14 * (1 - ease_in(span(u, 0.9, 1.02))), 1.0, 0.0
    return 0.0, ease_in_out(hand), 1 - span(u, 1.02, 1.6)


def ling(g: Gfx, x: float, cy: float):
    """手写粗笔“令”字（像素字体放大太糊）"""
    w = 2
    g.d.line((x - 9, cy - 3, x, cy - 10), fill=1, width=w)        # 撇
    g.d.line((x, cy - 10, x + 9, cy - 3), fill=1, width=w)        # 捺
    g.d.line((x - 1, cy - 6, x + 1, cy - 4), fill=1, width=w)     # 点
    g.d.line((x - 6, cy, x + 5, cy), fill=1, width=w)             # 横撇：横
    g.d.line((x + 5, cy, x - 1, cy + 6), fill=1, width=w)         #        撇
    g.d.line((x - 1, cy + 7, x + 1, cy + 9), fill=1, width=w)    # 点


class Card:
    """令牌：底边中点 (x, y)，h 为可见高度比例（1 = 立起，接近 0 = 卧倒）"""

    @staticmethod
    def draw(g: Gfx, x: float, y: float, h: float = 1.0, tilt: float = 0.0, glow: float = 0.0, shine: float = -1.0):
        hh = max(3, CH * h)
        x0, x1 = x - CW / 2, x + CW / 2
        y1 = y
        y0 = y - hh
        top = [(x0 + 3 + tilt, y0 + 3 * h), (x0 + 7 + tilt, y0), (x1 - 7 + tilt, y0), (x1 - 3 + tilt, y0 + 3 * h)]
        pts = [(x0, y1), (x0 + tilt, y0 + 5 * h)] + top + [(x1 + tilt, y0 + 5 * h), (x1, y1)]
        g.d.polygon(pts, fill=0, outline=1)
        if h > 0.6:
            g.d.polygon([(x0 + 3, y1 - 3), (x0 + 3 + tilt, y0 + 6 * h), (x1 - 3 + tilt, y0 + 6 * h),
                         (x1 - 3, y1 - 3)], outline=1)
            ling(g, x + tilt / 2, y0 + 18 * h)
            if 0 <= shine <= 1:  # 一点灵光沿令牌边框走过
                per = [(x0, y1 - 1), (x0, y0 + 5 * h), (x0 + 7, y0), (x1 - 7, y0), (x1, y0 + 5 * h), (x1, y1 - 1)]
                segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(per, per[1:])]
                d = shine * sum(segs)
                for (a, b), ln in zip(zip(per, per[1:]), segs):
                    if d <= ln:
                        f = d / ln
                        sparkle(g, a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, 2)
                        break
                    d -= ln
        else:  # 卧倒的令牌：只看到侧面一条
            g.d.line((x0 + 2, y0 + 1, x1 - 2, y0 + 1), fill=1)


def table(g: Gfx, dy: float = 0.0, text: str = "五营兵马"):
    y = TOP + dy
    g.d.rectangle((14, y, 114, y + 2), fill=1)
    g.d.rectangle((18, y + 3, 110, max(64, y + 6)), fill=0, outline=1)   # 案围（桌帷）
    g.d.line((18, y + 5, 110, y + 5), fill=1)
    for x in list(range(22, 36, 4)) + list(range(94, 108, 4)):  # 桌帷两角的回纹
        g.d.rectangle((x, y + 8, x + 2, y + 10), outline=1)
    g.text(CX, y + 6, text, size=8, align="center")


def flag(g: Gfx, x: float, base: float, ch: str, t: float, wave: float = 1.0, h: int = 30, seed: float = 0,
         left: bool = False):
    """令旗：杆 + 方旗面（反白写营名）+ 飘动的燕尾；left = 旗面朝左"""
    top = base - h
    sd = -1 if left else 1
    g.d.line((x, base, x, top - 1), fill=1)
    g.d.rectangle((x - 1, top - 3, x + 1, top - 2), fill=1)          # 杆头
    x0 = x + sd
    g.d.rectangle((min(x0, x0 + sd * 11), top, max(x0, x0 + sd * 11), top + 10), fill=1)
    g.text(x0 + sd * 6 - 3.5, top + 2, ch, size=8, fill=0)
    # 燕尾：随风起伏
    k1 = math.sin(t * 5 + seed) * 1.5 * wave + 2 * (1 - wave)
    k2 = math.sin(t * 5 + seed - 1.2) * 1.5 * wave + 3 * (1 - wave)
    xe = x0 + sd * 11
    g.d.polygon([(xe, top), (xe + sd * 6, top + k1), (xe + sd * 3, top + 5 + k2 * 0.5), (xe + sd * 6, top + 10 + k2),
                 (xe, top + 10)], fill=1)


@register
class CommandToken(Ritual):
    id = "r3.lingpai"
    name = "令牌拍案"
    desc = "执五雷令牌拍案发令，案震尘起；东南西北中五营令旗一面面应令而至，一轮满则五营齐发"
    T = {"enter": 3.4, "interrupt": 1.5, "resume": 1.6, "complete": 5.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 零件

    def arrived(self, k: float) -> list[float]:
        """各营令旗的到达进度（0..1）"""
        return [clamp((k - a) / 1.2) for a in ARRIVE]

    def flags(self, g: Gfx, arr: list[float], t: float, wave: float = 1.0, lift: float = 0.0, dy: float = 0.0):
        for i, (ch, x, center) in enumerate(FLAGS):
            p = arr[i]
            if p <= 0:
                continue
            q = ease_out_back(p)
            if center:
                base, h = 18 + dy, 18
            else:
                base, h = TOP + dy, 32 if i % 2 else 38
            rise = (1 - q) * (h + 14) + lift * (70 + i * 6)
            flag(g, x - (8 if center else 0), base - rise, ch, t, wave, h, i * 1.3, left=(i in (2, 3)))

    def hand(self, g: Gfx, x: float, y: float, a: float):
        """从右上方伸来捏住令牌顶的手；a 0..1 为伸入程度"""
        if a <= 0:
            return
        hx, hy = lerp(x + 60, x + 4, a), lerp(y - 40, y - 3, a)
        sleeve(g, hx + 6, hy - 4, -0.6, length=60, w0=12, w1=30, shade=0.25)
        g.d.rounded_rectangle((hx - 5, hy - 5, hx + 7, hy + 4), radius=3, fill=0, outline=1)
        g.d.line((hx - 4, hy - 1, hx + 1, hy - 1), fill=1)
        g.d.line((hx - 4, hy + 2, hx + 1, hy + 2), fill=1)

    def impact(self, g: Gfx, s: float, power: float = 1.0):
        """拍下的冲击：两侧震波线 + 扬尘"""
        if s <= 0:
            return
        f = 1 - s
        for side in (-1, 1):
            for j in range(3):
                x0 = CX + side * (CW / 2 + 3 + f * 16 * power + j * 4)
                y0 = TOP - 3 - j * 4
                g.d.line((x0, y0, x0 + side * 4 * power, y0 - 2 - j), fill=1)
        for j in range(8):
            a = math.pi + rand(j, 3) * math.pi
            r = f * (10 + 14 * rand(j, 4)) * power
            g.px(CX + math.cos(a) * r * 1.6, TOP - 1 + math.sin(a) * r * 0.4)

    def panel_text(self, k: float) -> str:
        for i, a in enumerate(ARRIVE):
            if 0 <= k - a < 5:
                return f"{FLAGS[i][0]}营兵马到"
        return "五营兵马"

    def mx(self, g: Gfx, arr: list[float], lift: float, shock: float, t: float):
        g.mx[1, 3:5] = True
        g.mx[2:7, 2] = True
        g.mx[2:7, 5] = True
        g.mx[6, 2:6] = True
        g.mx_set(3, 3)
        g.mx_set(4, 4)
        if lift > 0.3:  # 令牌被提起
            g.mx[:] = False
            g.mx[0, 3:5] = True
            g.mx[1:5, 2] = True
            g.mx[1:5, 5] = True
            g.mx[4, 2:6] = True
        g.mx[7, :] = True
        for i, (x, y) in enumerate(((0, 2), (1, 4), (6, 4), (7, 2), (0, 0))):
            if arr[i] >= 1:
                if i == 4:
                    g.mx_set(7, 0)
                g.mx_set(x, y)
        if shock > 0.6:
            g.mx[7, :] = blink(t, 0.1)
            g.mx_set(1, 6)
            g.mx_set(6, 6)

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, e: float, k: float, arr: list[float], u: float | None, text: str | None = None,
              wave: float = 1.0, h: float = 1.0):
        lift, hand, shock = slam_pose(u) if u is not None else (0.0, 0.0, 0.0)
        dy = 1 if shock > 0.85 else 0
        self.flags(g, arr, t, wave, dy=dy)
        table(g, dy, text if text is not None else self.panel_text(k))
        self.impact(g, shock)
        shine = (k % 7.0) / 1.2 if k % 7.0 < 1.2 and lift == 0 else -1
        Card.draw(g, CX, TOP - lift + dy, h, shine=shine)
        for j in range(4):  # 令牌上袅袅的灵气
            q = (t * 0.5 + j / 4) % 1.0
            g.px(CX - 9 + j * 6 + math.sin(t * 2 + j) * 2, TOP - CH - 2 - q * 14 + dy - lift)
        self.hand(g, CX, TOP - lift - CH + dy, hand)
        self.mx(g, arr, lift / 14, shock, t)
        g.mx_level = 5 if shock > 0.85 else 1

    def enter(self, g: Gfx, t: float):
        # 手持令牌从上方落下立于案上（第一拍），旗还没来
        tab = ease_out(span(t, 0, 0.6))
        if t < 1.0:
            y = lerp(-10, TOP - 14, ease_out(span(t, 0.2, 1.0)))
        elif t < 1.14:
            y = lerp(TOP - 14, TOP, ease_in(span(t, 1.0, 1.14)))
        else:
            y = TOP
        shock = 1 - span(t, 1.14, 1.8) if t > 1.14 else 0
        table(g, (1 - tab) * 14 + (1 if 0 < shock and shock > 0.85 else 0), "五营兵马" if t > 2.0 else "")
        self.impact(g, shock)
        if t > 0.2:
            Card.draw(g, CX, y)
        hand = 1 - span(t, 1.6, 2.4)
        if t > 0.2:
            self.hand(g, CX, y - CH, ease_out(span(t, 0.2, 0.5)) * hand if t < 0.5 else hand)
        arr = [0.0] * 5
        self.mx(g, arr, 0, shock, t)
        g.mx_level = 5 if shock > 0.85 else 1

    def hold(self, g: Gfx, t: float, e: float):
        n, k, _ = round_of(e, self.CYCLE)
        if n > 1 and k < RENEW:
            # 续：五营领令齐发（令旗飞起出画），案上只剩令牌，随即重新点兵
            lift = ease_in(span(k, 0.3, 2.0))
            self.flags(g, [1.0] * 5, t, 1.0, lift=lift)
            table(g, 0, "五营齐发" if k < 3.0 else "五营兵马")
            Card.draw(g, CX, TOP, glow=1 - span(k, 0, 1.5))
            self.mx(g, [1.0 if k < 1.5 else 0.0] * 5, 0, 0, t)
            return
        u = (k - 10) % SLAM
        self.frame(g, t, e, k, self.arrived(k), u)

    def interrupt(self, g: Gfx, t: float, e: float):
        _, k, _ = round_of(e, self.CYCLE)
        arr = self.arrived(k)
        p = ease_out_bounce(span(t, 0.2, 1.0))
        wave = 1 - span(t, 0, 1.0)
        self.flags(g, arr, t, wave)
        table(g, 0, "收令暂歇" if t > 0.5 else self.panel_text(k))
        Card.draw(g, CX, TOP, 1 - 0.92 * p)
        self.mx(g, arr, 0, 0, t)

    def resume(self, g: Gfx, t: float, e: float):
        _, k, _ = round_of(e, self.CYCLE)
        arr = self.arrived(k)
        p = ease_out_back(span(t, 0.2, 1.0))
        wave = span(t, 0.6, 1.6)
        self.flags(g, arr, t, wave)
        table(g, 0, self.panel_text(k))
        Card.draw(g, CX, TOP, lerp(0.08, 1, clamp(p)))
        self.hand(g, CX, TOP - CH, ease_out(span(t, 0, 0.3)) * (1 - span(t, 1.0, 1.6)))
        self.mx(g, arr, 0, 0, t)

    def complete(self, g: Gfx, t: float, e: float):
        # 三拍（越拍越重），五营令旗齐亮飞升，令牌放光：五雷号令
        _, k, _ = round_of(e, self.CYCLE)
        arr = [max(a, clamp((t - 2.6) / 0.8)) for a in self.arrived(k)]
        if t < 2.7:
            j = min(2, int(t / 0.9))
            u = (t - j * 0.9)
            lift = 12 * ease_out(span(u, 0, 0.55)) * (1 - ease_in(span(u, 0.55, 0.66)))
            shock = 1 - span(u, 0.66, 0.9) if u > 0.66 else 0
            dy = (1 + j) if shock > 0.8 else 0
            self.flags(g, arr, t, dy=dy)
            table(g, dy, ["一拍", "二拍", "三拍"][j])
            self.impact(g, shock, 1 + j * 0.4)
            Card.draw(g, CX, TOP - lift + dy)
            self.hand(g, CX, TOP - lift - CH + dy, 1.0)
            self.mx(g, arr, lift / 14, shock, t)
            g.mx_level = 3 + 2 * j if shock > 0.8 else 1
            return
        glow = ease_out(span(t, 2.7, 3.6))
        lift = ease_in(span(t, 3.4, 5.0))
        self.flags(g, arr, t, lift=lift)
        table(g, 0, "五雷号令")
        Card.draw(g, CX, TOP, glow=glow * (1 + 0.15 * math.sin(t * 8)))
        self.hand(g, CX, TOP - CH, 1 - span(t, 2.7, 3.2))
        for j in range(6):
            if blink(t + j * 0.13, 0.5, 0.3):
                g.px(30 + rand(j, 9) * 70, 4 + rand(j, 10) * 30)
        self.mx(g, arr, 0, 0, t)
        rr = (t - 2.7) * 4
        for yy in range(8):
            for xx in range(8):
                if abs(math.hypot(xx - 3.5, yy - 3.5) - rr) < 0.7:
                    g.mx[yy, xx] = True
        g.mx_level = 1 + int(6 * (1 - span(t, 2.7, 4.2)))
