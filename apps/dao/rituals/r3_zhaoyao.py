"""照妖镜：手举宝镜照向来客，镜光扫过之处显出原形（书生→狐、女子→白骨、老翁→蛇）。
镜光随计时越照越宽，照满一轮则原形毕露、妖物逃窜，再来下一位“客人”。

依据：葛洪《抱朴子·登涉》：“万物之老者，其精悉能假托人形，以眩惑人目而常试人，唯不能于镜中易其真形耳。
是以古之入山道士，皆以明镜径九寸已上，悬于背后，则老魅不敢近人。”
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r3_kit import round_of, side_text, sleeve, sparkle

MX0, MY0 = 24, 37        # 镜心
FW, FH = 30, 42          # 来客的画框
FX0, FY0 = 86, 21        # 来客画框左上角
DISGUISE = ["书生", "女子", "老翁"]
TRUE = ["狐妖", "白骨精", "蛇妖"]
RENEW = 4.6


# ---------------------------------------------------------------- 来客像素画（用 PIL 画好缓存成数组）

def _canvas():
    on = Image.new("1", (FW, FH))
    mk = Image.new("1", (FW, FH))
    return on, mk, ImageDraw.Draw(on), ImageDraw.Draw(mk)


def _both(do, dm, kind, xy, **kw):
    """同一形状：on 画布按参数画，mask 画布填实"""
    getattr(do, kind)(xy, **kw)
    if kind == "line":
        getattr(dm, kind)(xy, fill=1, width=kw.get("width", 1))
    else:
        getattr(dm, kind)(xy, fill=1, outline=1)


def _scholar():
    on, mk, do, dm = _canvas()
    robe = [(10, 17), (20, 17), (25, 41), (5, 41)]
    _both(do, dm, "polygon", robe, fill=0, outline=1)
    do.line((12, 17, 15, 23, 18, 17), fill=1)
    _both(do, dm, "rectangle", (7, 24, 23, 29), fill=0, outline=1)     # 拢袖
    do.line((15, 24, 15, 29), fill=1)
    do.line((9, 32, 21, 32), fill=1)
    _both(do, dm, "ellipse", (10, 6, 20, 16), fill=0, outline=1)        # 头
    _both(do, dm, "rectangle", (10, 2, 20, 7), fill=1)                  # 幞头
    _both(do, dm, "line", (3, 5, 27, 5), fill=1, width=2)              # 展脚
    do.point((13, 11))
    do.point((17, 11))
    do.line((14, 14, 16, 14), fill=1)
    return on, mk


def _fox():
    on, mk, do, dm = _canvas()
    tail = [(20, 40), (26, 34), (29, 25), (28, 16), (25, 19), (24, 27), (19, 34)]
    _both(do, dm, "polygon", tail, fill=1)
    do.line((27, 17, 28, 20), fill=0)
    robe = [(10, 17), (20, 17), (24, 41), (6, 41)]
    _both(do, dm, "polygon", robe, fill=0, outline=1)
    for y in range(22, 40, 4):  # 毛
        for x in range(9, 22, 4):
            do.line((x + (y // 4) % 2, y, x + 1 + (y // 4) % 2, y + 1), fill=1)
    _both(do, dm, "line", (8, 24, 4, 29), fill=1, width=2)              # 爪
    _both(do, dm, "line", (22, 24, 26, 29), fill=1, width=2)
    _both(do, dm, "polygon", [(9, 7), (21, 7), (15, 17)], fill=0, outline=1)  # 狐脸
    _both(do, dm, "polygon", [(9, 7), (10, 0), (14, 7)], fill=1)        # 耳
    _both(do, dm, "polygon", [(16, 7), (20, 0), (21, 7)], fill=1)
    do.line((11, 10, 14, 11), fill=1)                                    # 吊梢眼
    do.line((16, 11, 19, 10), fill=1)
    do.rectangle((14, 15, 16, 16), fill=1)
    return on, mk


def _lady():
    on, mk, do, dm = _canvas()
    dress = [(11, 17), (19, 17), (27, 41), (3, 41)]
    _both(do, dm, "polygon", dress, fill=0, outline=1)
    _both(do, dm, "polygon", [(10, 18), (4, 33), (8, 34), (12, 22)], fill=0, outline=1)   # 广袖
    _both(do, dm, "polygon", [(20, 18), (26, 33), (22, 34), (18, 22)], fill=0, outline=1)
    do.line((9, 26, 21, 26), fill=1)                                     # 腰带
    do.line((15, 26, 13, 38), fill=1)
    do.line((15, 26, 18, 38), fill=1)
    _both(do, dm, "ellipse", (11, 7, 19, 16), fill=0, outline=1)
    _both(do, dm, "ellipse", (11, 0, 19, 8), fill=1)                     # 发髻
    _both(do, dm, "line", (8, 4, 22, 2), fill=1)                         # 簪
    do.line((11, 10, 10, 18), fill=1)
    do.line((19, 10, 20, 18), fill=1)
    do.point((13, 11))
    do.point((17, 11))
    do.point((15, 14))
    return on, mk


def _bones():
    on, mk, do, dm = _canvas()
    _both(do, dm, "line", (15, 15, 15, 35), fill=1, width=2)            # 脊
    for y in range(19, 31, 3):                                           # 肋
        _both(do, dm, "line", (10, y + 1, 14, y), fill=1)
        _both(do, dm, "line", (16, y, 20, y + 1), fill=1)
    _both(do, dm, "line", (10, 18, 5, 30), fill=1)                       # 臂
    _both(do, dm, "line", (20, 18, 25, 30), fill=1)
    _both(do, dm, "ellipse", (10, 33, 20, 38), fill=0, outline=1)        # 盆骨
    _both(do, dm, "line", (12, 38, 10, 41), fill=1)
    _both(do, dm, "line", (18, 38, 20, 41), fill=1)
    _both(do, dm, "ellipse", (10, 4, 20, 15), fill=1)                    # 头骨
    do.ellipse((11, 8, 14, 11), fill=0)
    do.ellipse((16, 8, 19, 11), fill=0)
    do.point((15, 12))
    do.line((12, 14, 18, 14), fill=0)
    for x in (13, 15, 17):
        do.point((x, 13))
    return on, mk


def _oldman():
    on, mk, do, dm = _canvas()
    robe = [(10, 16), (20, 16), (23, 41), (7, 41)]
    _both(do, dm, "polygon", robe, fill=0, outline=1)
    do.line((10, 28, 20, 28), fill=1)
    _both(do, dm, "line", (25, 13, 26, 41), fill=1, width=2)            # 拐杖
    _both(do, dm, "ellipse", (23, 10, 28, 15), fill=0, outline=1)
    _both(do, dm, "rectangle", (21, 21, 26, 25), fill=0, outline=1)     # 手
    _both(do, dm, "ellipse", (11, 4, 19, 13), fill=0, outline=1)        # 光头
    do.arc((12, 5, 18, 10), 200, 300, fill=1)
    _both(do, dm, "polygon", [(11, 11), (19, 11), (15, 24)], fill=1)    # 长须
    do.line((12, 8, 14, 8), fill=1)
    do.line((16, 8, 18, 8), fill=1)
    return on, mk


def _snake():
    on, mk, do, dm = _canvas()
    _both(do, dm, "ellipse", (3, 32, 27, 41), fill=0, outline=1)        # 盘身
    _both(do, dm, "ellipse", (6, 25, 24, 34), fill=0, outline=1)
    for x in range(6, 26, 4):
        do.line((x, 34, x + 2, 39), fill=1)
    for x in range(9, 22, 4):
        do.line((x, 27, x + 2, 32), fill=1)
    _both(do, dm, "line", (15, 27, 16, 11), fill=1, width=5)            # 昂起的颈
    do.line((15, 26, 16, 12), fill=0, width=3)
    for y in range(14, 26, 3):
        do.point((15, y))
    _both(do, dm, "ellipse", (9, 3, 22, 12), fill=0, outline=1)         # 头
    do.rectangle((11, 6, 12, 7), fill=1)
    do.rectangle((19, 6, 20, 7), fill=1)
    _both(do, dm, "line", (15, 12, 15, 16), fill=1)                      # 信子（往下吐）
    return on, mk


_SPRITES: dict = {}


def figure(kind: int, true: bool):
    key = (kind, true)
    if key not in _SPRITES:
        fn = [(_scholar, _fox), (_lady, _bones), (_oldman, _snake)][kind][1 if true else 0]
        on, mk = fn()
        on, mk = np.array(on, dtype=bool), np.array(mk, dtype=bool)
        _SPRITES[key] = (on, mk | on)
    return _SPRITES[key]


_GRID = np.mgrid[0:FH, 0:FW].astype(np.float32)


# ---------------------------------------------------------------- 镜

def mirror(g: Gfx, x: float, y: float, face: float = 1.0, t: float = 0.0, flash: float = 0.0):
    """手镜：face 1 = 正对，0 = 侧过去（窄椭圆）"""
    sleeve(g, x - 5, y + 21, 2.3, length=40, w0=11, w1=26, shade=0.25)
    g.d.rectangle((x - 2, y + 9, x + 2, y + 19), fill=0, outline=1)         # 镜柄
    g.d.rounded_rectangle((x - 4, y + 15, x + 4, y + 23), radius=3, fill=0, outline=1)  # 握柄的拳
    g.d.line((x - 3, y + 18, x + 3, y + 18), fill=1)
    rx = max(2.0, 11 * face)
    g.d.ellipse((x - rx, y - 11, x + rx, y + 11), fill=0, outline=1)
    if face > 0.4:
        g.d.ellipse((x - rx + 2, y - 9, x + rx - 2, y + 9), outline=1)
        # 镜面的反光：两道斜光，时明时暗地扫过
        q = (t * 0.6) % 2.0
        if q < 1.0:
            off = lerp(-6, 6, q)
            for k, ln in ((0, 4), (3, 2.5)):
                cx_, cy_ = x + (off + k) * face, y - off - k
                g.d.line((cx_ - ln * face, cy_ + ln, cx_ + ln * face, cy_ - ln), fill=1)
        else:
            g.d.line((x - 5 * face, y - 1, x - 1 * face, y - 5), fill=1)
    if flash > 0:
        for i in range(12):
            a = i / 12 * 2 * math.pi
            r0, r1 = 13, 13 + 10 * flash
            g.d.line((x + math.cos(a) * r0, y + math.sin(a) * r0, x + math.cos(a) * r1, y + math.sin(a) * r1),
                     fill=1)


@register
class DemonMirror(Ritual):
    id = "r3.zhaoyao"
    name = "照妖镜"
    desc = "手举宝镜照向来客，镜光扫过之处显出原形：书生是狐、女子是白骨、老翁是蛇；照满一轮原形毕露，妖物逃窜"
    T = {"enter": 3.6, "interrupt": 1.3, "resume": 1.5, "complete": 5.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 零件

    def guest(self, e: float) -> int:
        return (int(e // self.CYCLE) + self.seed) % 3

    def beam_ang(self, t: float) -> float:
        return math.sin(t * 0.9) * 0.22 + math.sin(t * 0.37 + 1) * 0.08 - 0.02

    def width(self, e: float) -> float:
        _, _, p = round_of(e, self.CYCLE)
        return lerp(0.05, 0.3, p)

    def beam(self, g: Gfx, ang: float, w: float, t: float, amp: float = 1.0):
        """镜光：几道点状光线 + 两条边"""
        if amp <= 0:
            return
        ox, oy = MX0 + 10, MY0
        n = 7
        for i in range(n):
            a = ang - w + 2 * w * i / (n - 1)
            edge = i in (0, n - 1)
            ln = 100 * amp
            step = 2 if edge else 5
            ph = int(t * 20) % step
            for d in range(4 + ph, int(ln), step):
                x, y = ox + math.cos(a) * d, oy + math.sin(a) * d
                if 0 <= x < 128 and 0 <= y < 64:
                    g.px(x, y)

    def visitor(self, g: Gfx, kind: int, ang: float, w: float, t: float, dx: float = 0.0, reveal: float | None = None,
                tremble: float = 0.0, bob: bool = False):
        """来客：镜光照到的部分画原形，其余画伪装"""
        d_on, d_mk = figure(kind, False)
        t_on, t_mk = figure(kind, True)
        x0 = FX0 + dx + (math.sin(t * 31) * tremble if tremble else 0)
        y0 = FY0 - (abs(math.sin(t * 8)) * 2 if bob else 0)
        if reveal is None:
            ys, xs = _GRID
            a = np.arctan2(ys + y0 - MY0, xs + x0 - (MX0 + 10))
            lit = np.abs(a - ang) <= w
        else:
            lit = np.full((FH, FW), reveal >= 1) if reveal in (0, 1) else (_GRID[0] >= FH * (1 - reveal))
        on = np.where(lit, t_on, d_on)
        mk = np.where(lit, t_mk, d_mk)
        g.blit(Sprite(on=on, mask=mk), x0, y0)
        g.d.line((FX0 - 6 + dx, 62, FX0 + FW + 4 + dx, 62), fill=1)  # 地面

    def label(self, g: Gfx, s: str, a: float = 1.0, right: bool = True):
        if right:
            k = int(round(clamp(a) * len(s)))
            g.text(126, 3, s[:k], align="right")
        side_text(g, 2, 2, "照妖", 1.0)

    def mx(self, g: Gfx, ang: float, w: float, on: bool, t: float):
        for y, row in enumerate((".##.", "#..#", "#..#", ".##.")):
            for x, ch in enumerate(row):
                if ch == "#":
                    g.mx_set(x, y + 2)
        g.mx_set(1, 6)
        g.mx_set(1, 7)
        if on:
            for x in range(4, 8):
                for k in (-1, 0, 1):
                    y = 3.5 + math.tan(ang + k * w) * (x - 2) * 1.0
                    if k == 0 or blink(t + x * 0.1, 0.4):
                        g.mx_set(x, int(round(y)))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        kind = self.guest(0)
        walk = ease_out(span(t, 0, 1.6))
        dx = lerp(50, 0, walk)
        rise = ease_out_back(span(t, 1.4, 2.4))
        my = lerp(80, MY0, rise)
        on = t > 2.6
        ang = self.beam_ang(t - self.T["enter"])
        w = self.width(0) * span(t, 2.6, 3.2)
        if on:
            self.beam(g, ang, w, t, ease_out(span(t, 2.6, 3.2)))
        self.visitor(g, kind, ang, w if on else -1, t, dx=dx, bob=walk < 1)
        mirror(g, MX0, my, t=t, flash=1 - span(t, 2.4, 2.9) if 2.4 < t < 2.9 else 0)
        self.label(g, DISGUISE[kind] + "？", span(t, 1.6, 2.4))
        self.mx(g, ang, w, on, t)

    def hold(self, g: Gfx, t: float, e: float):
        n, k, p = round_of(e, self.CYCLE)
        if n > 1 and k < RENEW:
            self._renew(g, k, e, t)
            return
        kind = self.guest(e)
        ang = self.beam_ang(e)
        w = self.width(e)
        self.beam(g, ang, w, t)
        self.visitor(g, kind, ang, w, t, tremble=0.6 * p if noise(t * 2, 3) > 0.6 else 0)
        mirror(g, MX0, MY0, t=t)
        self.label(g, DISGUISE[kind] + "？")
        self.mx(g, ang, w, True, t)

    def _renew(self, g: Gfx, k: float, e: float, t: float):
        """照满：原形毕露 → 妖物尖叫逃窜 → 下一位客人走来"""
        old = (int(e // self.CYCLE) - 1 + self.seed) % 3
        new = self.guest(e)
        if k < 1.4:
            self.beam(g, 0, 0.4 + 0.1 * math.sin(k * 20), t)
            self.visitor(g, old, 0, 1, t, reveal=1, tremble=1.5)
            mirror(g, MX0, MY0, t=t, flash=1 - span(k, 0, 1.2))
            self.label(g, TRUE[old] + "！")
            self.mx(g, 0, 0.4, True, t)
            g.mx_level = 5 if k < 0.3 else 1
        elif k < 2.6:
            f = ease_in(span(k, 1.4, 2.4))
            self.visitor(g, old, 0, 1, t, dx=f * 60, reveal=1, bob=True)
            for j in range(5):  # 逃跑扬尘
                g.px(FX0 + f * 60 - 4 - j * 3, 60 - (j % 2))
            mirror(g, MX0, MY0, t=t)
            self.label(g, TRUE[old] + "！")
            self.mx(g, 0, 0, False, t)
        else:
            walk = ease_out(span(k, 2.6, RENEW - 0.4))
            self.visitor(g, new, 0, -1, t, dx=lerp(50, 0, walk), bob=walk < 1)
            if k > RENEW - 0.5:
                self.beam(g, self.beam_ang(e), self.width(e), t, span(k, RENEW - 0.5, RENEW))
            mirror(g, MX0, MY0, t=t)
            self.label(g, DISGUISE[new] + "？", span(k, 3.0, 3.8))
            self.mx(g, 0, 0, False, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        kind = self.guest(e)
        ang = self.beam_ang(e)
        w = self.width(e)
        face = 1 - 0.8 * ease_in_out(span(t, 0, 0.7))
        amp = 1 - span(t, 0, 0.5)
        self.beam(g, ang, w, t, amp)
        self.visitor(g, kind, ang, w if amp > 0 else -1, t)
        mirror(g, MX0, MY0, face=face, t=t)
        self.label(g, "收镜" if t > 0.5 else DISGUISE[kind] + "？")
        self.mx(g, ang, w, amp > 0, t)

    def resume(self, g: Gfx, t: float, e: float):
        kind = self.guest(e)
        ang = self.beam_ang(e)
        w = self.width(e)
        face = 0.2 + 0.8 * ease_out_back(span(t, 0, 0.7))
        on = t > 0.7
        if on:
            self.beam(g, ang, w, t, ease_out(span(t, 0.7, 1.2)))
        self.visitor(g, kind, ang, w if on else -1, t)
        mirror(g, MX0, MY0, face=min(face, 1.0), t=t, flash=1 - span(t, 0.7, 1.2) if 0.7 < t < 1.2 else 0)
        self.label(g, DISGUISE[kind] + "？")
        self.mx(g, ang, w, on, t)

    def complete(self, g: Gfx, t: float, e: float):
        kind = self.guest(e)
        # 0–2：镜光转正、张满，原形自下而上显出；2–4：原形毕露、浑身发抖，“现出原形”；4–5.5：化一缕烟散去
        w0 = self.width(e)
        ang = lerp(self.beam_ang(e), 0, ease_in_out(span(t, 0, 0.8)))
        w = lerp(w0, 0.42, ease_in_out(span(t, 0.4, 1.6)))
        if t < 4.0:
            self.beam(g, ang, w, t, 1 - 0.6 * span(t, 3.0, 4.0))
            if t < 2.0:
                self.visitor(g, kind, ang, w, t, reveal=span(t, 0.8, 2.0) if t > 0.8 else None, tremble=1.0)
            else:
                self.visitor(g, kind, 0, 1, t, reveal=1, tremble=1.5)
            mirror(g, MX0, MY0, t=t, flash=span(t, 1.8, 2.4) * (1 - span(t, 3.2, 4.0)) if t > 1.8 else 0)
            if t < 2.4:
                self.label(g, TRUE[kind] + "！" if t > 1.2 else DISGUISE[kind] + "？")
            else:
                g.text(126, 3, "现出原形"[:int(clamp((t - 2.4) * 5 / 4) * 4)], align="right")
                side_text(g, 2, 2, "照妖")
            self.mx(g, ang, w, True, t)
            g.mx_level = 4 if 1.9 < t < 2.3 else 1
            return
        from ..engine.fx import smoke_wisp
        self.visitor(g, kind, 0, 1, t, reveal=1, tremble=2)
        g.fade(1 - span(t, 4.0, 4.8), (FX0 - 2, FY0 - 2, FX0 + FW + 6, 62))
        smoke_wisp(g, FX0 + 15, 58, 44 * (1 - span(t, 4.6, 5.5)), t, self.seed, sway=5)
        mirror(g, MX0, MY0, t=t)
        g.text(126, 3, "现出原形", align="right")
        side_text(g, 2, 2, "照妖")
        self.mx(g, 0, 0.3, blink(t, 0.5), t)
