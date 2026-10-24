"""写经换鹅：《晋书·王羲之传》山阴道士以鹅换字（传中为《道德经》，后世多传为《黄庭经》）；
李白《王右军》“扫素写道经，笔精妙入神。书罢笼鹅去，何曾别主人”。经文：《黄庭外景经》首四句
“上有黄庭下关元，后有幽阙前命门，呼吸庐间入丹田，玉池清水灌灵根”（据维基文库本）。

左边一架挂起的宣纸（上有轴杆、挂绳，下有压轴），小道士站在纸前，握一支提斗大笔；脚边小几上一方砚台。
右边池塘，柳条垂下，三只白鹅（额上肉瘤、长颈）游来游去，身后拖着水纹。
入场：宣纸从上往下展开，白鹅一只只游进池塘，小道士走到纸前。
持续：一字 6 秒：笔回砚台蘸墨 → 在纸上写出一个斗大的黑字（从上往下一行行显出，笔尖跟着走）→ 端详一下。
      写完的字攒到顶上一行（本句）。一句七字写完，在纸角盖一方“右军”小印（啪地一震）。
      池中白鹅游弋，偶尔伸颈张嘴一叫。每写完两句：“书罢笼鹅去”——竹笼从天而降罩住一只鹅提走，
      下一句开头又游来一只。
退场：收圆。
点阵：写字时是这个字的 8×8 缩影，跟着笔一行行显出；其余时间是浮水的鹅。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite, _text_img
from ..engine.scene import Rest, register
from .x2_common import Clock, arm, iris, label, shoulder_xy

LINES = ["上有黄庭下关元", "后有幽阙前命门", "呼吸庐间入丹田", "玉池清水灌灵根"]
FLOOR = 58
DX = 17                       # 小道士（站，朝右）
PAPER = (24, 17, 56, 52)      # 宣纸（含边）
CH = (28, 22)                 # 大字左上
INK = (14, 53)                # 砚台
PER = 6.0
SENT = 48.0                   # 一句：7 字 42 秒 + 盖印、笼鹅 6 秒
POND = 47                     # 水面
BRUSH = 13


# ---------------------------------------------------------------- 造型

_GLY: dict = {}


def glyph(ch: str, rows: int | None = None) -> Sprite:
    """把 12px 字放大两倍做成精灵（笔墨），rows：只要上面几行（逐行写出）"""
    key = (ch, rows)
    s = _GLY.get(key)
    if s is None:
        a = np.array(_text_img(ch, 12, 2), dtype=bool)
        if rows is not None:
            a = a.copy()
            a[rows:] = False
        s = _GLY[key] = Sprite(on=a, mask=a)
    return s


def _goose(f: int):
    """白鹅（朝左）14×12：额上肉瘤、扁嘴、S 形长颈、圆身、上翘的尾、翅上一道羽纹；
    f=0 游 / 1 伸颈张嘴叫"""
    p = Part(15, 12)
    p.shape("ellipse", (3, 6, 14, 11), fill=1)                       # 身
    p.shape("polygon", [(12, 6), (14, 4), (14, 7)], fill=1)          # 尾
    p.d.line((6, 8, 11, 8), fill=0), p.d.line((7, 9, 11, 9), fill=0)  # 翅
    p.dither((9, 9, 14, 11), 0.5, 0)
    if f == 0:
        p.shape("line", ((5, 7), (4, 5), (5, 3), (4, 1)), fill=1, width=2)   # 颈
        p.shape("ellipse", (1, 0, 5, 3), fill=1)                     # 头
        p.shape("rectangle", (0, 2, 1, 2), fill=1)                   # 嘴
        p.px(2, 0)                                                   # 肉瘤
        p.px(3, 1, 0)
    else:
        p.shape("line", ((5, 7), (3, 4), (2, 2)), fill=1, width=2)
        p.shape("ellipse", (0, 0, 4, 3), fill=1)
        p.px(1, 1, 0)
        p.shape("line", (0, 0, 0, 0), fill=1)
        p.d.line((0, 2, 1, 2), fill=0)                              # 张嘴
    return p.sprite()


def _cage():
    """竹笼 15×13：提环、竹篾编的格子"""
    p = Part(15, 14)
    p.shape("ellipse", (5, 0, 9, 4), fill=1)
    p.d.ellipse((6, 1, 8, 3), fill=0)
    p.shape("polygon", [(2, 4), (12, 4), (14, 13), (0, 13)], fill=1)
    p.d.polygon([(3, 5), (11, 5), (13, 12), (1, 12)], fill=0)
    for x in range(3, 13, 3):
        p.d.line((x, 5, x - (1 if x < 7 else -1), 12), fill=1)
    p.d.line((1, 9, 13, 9), fill=1)
    return p.sprite()


def _inkstone():
    p = Part(11, 6)
    p.shape("rectangle", (0, 2, 10, 4), fill=1)
    p.d.rectangle((2, 2, 8, 2), fill=0)
    p.px(3, 3, 0), p.px(4, 3, 0)
    p.shape("rectangle", (1, 5, 1, 5), fill=1)
    p.shape("rectangle", (9, 5, 9, 5), fill=1)
    p.shape("rectangle", (7, 0, 8, 1), fill=1)       # 墨锭
    return p.sprite()


def _seal():
    p = Part(9, 9)
    p.shape("rectangle", (0, 0, 8, 8), fill=1)
    p.d.rectangle((1, 1, 7, 7), outline=0)
    p.d.line((4, 2, 4, 6), fill=0), p.d.line((2, 4, 6, 4), fill=0)
    return p.sprite()


_P: dict = {}


def prop(name, *a):
    key = (name,) + a
    if key not in _P:
        _P[key] = {"goose": _goose, "cage": _cage, "ink": _inkstone, "seal": _seal}[name](*a)
    return _P[key]


@register
class Goose(Rest):
    id = "x2.goose"
    name = "写经换鹅"
    desc = "小道士执提斗大笔在挂起的宣纸上一字一字写《黄庭经》，池中白鹅游弋；写完两句书罢笼鹅去"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0
        self.l0 = self.rng.randrange(len(LINES))
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    def line(self, n: int) -> str:
        return LINES[(n + self.l0) % len(LINES)]

    # ------------------------------------------------------------ 写字

    def stroke(self, ch: str, q: float):
        """写到 q（0..1）：→ (显出的行数, 笔尖位置)"""
        g = glyph(ch)
        rows = [y for y in range(g.h) if g.on[y].any()]
        if not rows:
            return 0, (CH[0] + 12, CH[1] + 12)
        y0, y1 = rows[0], rows[-1]
        yr = int(lerp(y0, y1 + 1, q))
        yy = min(max(yr, y0), y1)
        xs = np.nonzero(g.on[yy])[0]
        if len(xs) == 0:
            x = 12
        else:
            ph = (q * 40) % 2
            ph = ph if ph < 1 else 2 - ph
            x = lerp(xs.min(), xs.max(), ph)
        return yr, (CH[0] + x, CH[1] + yy)

    def writer(self, g: Gfx, t: float, tip, wet: bool, walk_x: float | None = None, face: str = "normal"):
        """站着握提斗大笔：手在肩与笔尖之间，笔杆从手伸到笔尖"""
        if walk_x is not None:
            figure(g, walk_x, FLOOR, t, legs="walk", arm="down")
            return
        sx, sy = shoulder_xy(DX, FLOOR)
        vx, vy = tip[0] - sx, tip[1] - sy
        L = max(math.hypot(vx, vy), 1)
        hd = max(5.0, min(L - 7, L - BRUSH))
        hx, hy = sx + vx / L * hd, sy + vy / L * hd
        spr = arm(hx - sx, hy - sy, "fist")
        figure(g, DX, FLOOR, t, arm=spr, arm_at=(2 - spr.sh[0], -15 - spr.sh[1]), face=face)
        g.d.line((hx, hy, tip[0], tip[1]), fill=0, width=3)        # 笔杆（描黑边）
        g.d.line((hx, hy, tip[0], tip[1]), fill=1)
        ux, uy = (tip[0] - hx) / max(L - hd, 1), (tip[1] - hy) / max(L - hd, 1)
        g.d.line((tip[0] - ux * 3, tip[1] - uy * 3, tip[0], tip[1]), fill=0, width=2)   # 笔头（蘸了墨是黑的）
        if not wet:
            g.px(tip[0], tip[1], 1)

    # ------------------------------------------------------------ 池与鹅

    def pond(self, g: Gfx, t: float):
        g.d.line((60, POND - 1, 127, POND - 1), fill=1)
        for i, y in enumerate(range(POND + 2, 64, 3)):
            ph = t * (6 + i * 2)
            for x0 in range(0, 90, 14):
                x = 62 + (x0 + i * 5 + ph) % 70
                g.d.line((x, y, min(x + 2 + i % 2, 127), y), fill=1)
        g.d.polygon([(56, 63), (58, POND), (62, POND - 1), (63, 63)], fill=1)
        pix.checker(g, (57, POND + 1, 63, 64), 0.5, fill=0)
        # 柳条（从右边画外伸进来的一枝，丝丝垂下）
        g.d.line((127, 17, 112, 18), fill=1, width=2)
        g.d.line((112, 18, 96, 17), fill=1)
        for i, x in enumerate((98, 104, 110, 116, 122)):
            sw = math.sin(t * 0.9 + i) * 2
            top = 18
            for y in range(top, top + 12 + (i * 5) % 11):
                xx = x + sw * ((y - top) / 20) ** 2
                g.px(xx, y)
                if y % 4 == 2:
                    g.px(xx - 1, y + 1)

    def geese(self, g: Gfx, t: float, gone: int, caged: float = -1.0, back: int = -1, back_q: float = 1.0):
        """三只鹅（第 gone 只被笼走了，caged ≥ 0：被提起的高度）→ 被罩的那只的位置"""
        out = None
        for i in range(3):
            ph = t * 0.11 + i * 2.1
            x = 92 + math.sin(ph) * 22 + i * 3
            d = math.cos(ph)
            if i == back and back_q < 1:          # 新来的一只从右边游进来
                x += (1 - ease_out(back_q)) * 50
                d = 1
            y = POND - 8 + (i % 2) * 7
            if i == gone and caged < 0:
                continue
            honk = (t + i * 4.7) % 11 < 0.8
            if i == gone:
                out = (x, y)
                y -= caged
            bob = 1 if (t * 2 + i) % 2 < 1 else 0
            spr = prop("goose", int(honk))
            pix.blit(g, spr, x - 7, y + bob, flip=d < 0)
            if caged < 0:                                          # 尾波
                for k in range(1, 4):
                    wx = x + (8 + k * 3) * (1 if d >= 0 else -1)
                    g.px(wx, y + 10 + k // 2), g.px(wx, y + 10 - k // 2 + 1)
        return out

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, enter: float = 1.0):
        dt = self.clock.dt(t)
        on = enter >= 1
        e3 = enter * self.T["enter"]
        n = int(t // SENT) if on else 0
        k = t % SENT if on else 0.0
        sent = self.line(n)
        j = min(int(k // PER), 6)
        kk = k - j * PER
        # 地面、池
        g.d.line((0, FLOOR, 56, FLOOR), fill=1)
        pix.checker(g, (0, FLOOR + 1, 57, 64), 0.25)
        self.pond(g, t)
        # 宣纸（入场时从上往下展开）
        unroll = ease_out(span(e3, 0.0, 1.0)) if not on else 1.0
        x0, y0, x1, y1 = PAPER
        yb = lerp(y0 + 2, y1, unroll)
        for px_ in (x0 - 3, x1 + 3):                                # 屏架：两根立杆、横梁
            g.d.rectangle((px_ - 1, y0 - 3, px_, FLOOR - 1), fill=1)
            g.d.line((px_ - 3, FLOOR - 1, px_ + 2, FLOOR - 1), fill=1)
            g.d.rectangle((px_ - 2, y0 - 4, px_ + 1, y0 - 3), fill=1)
        g.d.line((x0 - 3, y0 - 2, x1 + 3, y0 - 2), fill=1)
        g.d.rectangle((x0 + 1, y0 + 1, x1 - 1, yb), fill=1)          # 纸面（白）
        g.d.rectangle((x0 - 2, y0 - 1, x1 + 2, y0), fill=1)          # 天杆
        g.d.rectangle((x0 - 2, yb, x1 + 2, yb + 1), fill=1)          # 地轴
        g.d.line((x0 - 1, yb + 1, x1 + 1, yb + 1), fill=0)
        # 字
        writing = on and 0.6 <= kk < 4.6 and k < 42
        tip = INK
        wet = True
        if on and k < 42:
            ch = sent[j]
            if kk < 0.6:                       # 蘸墨（上一个字还在纸上，慢慢淡去）
                q = span(kk, 0, 0.6)
                tip = (lerp(CH[0] + 12, INK[0], q), lerp(CH[1] + 24, INK[1] - 1, q) - math.sin(q * math.pi) * 4)
                if j > 0:
                    prev = glyph(sent[j - 1])
                    pix.blit(g, prev, CH[0], CH[1], invert=True, outline=False)
            elif kk < 4.6:
                rows, tip = self.stroke(ch, span(kk, 0.6, 4.6))
                pix.blit(g, glyph(ch, rows), CH[0], CH[1], invert=True, outline=False)
                wet = False
            else:
                pix.blit(g, glyph(ch), CH[0], CH[1], invert=True, outline=False)
                q = span(kk, 4.6, 6.0)
                tip = (lerp(CH[0] + 22, CH[0] + 12, q), lerp(CH[1] + 26, CH[1] + 30, q))
        elif on:                               # 一句写完：盖印
            pix.blit(g, glyph(sent[6]), CH[0], CH[1], invert=True, outline=False)
            if k > 43.0:
                pix.blit(g, prop("seal"), x1 - 11, y1 - 11)
            if abs(k - 43.0) < dt * 1.01:
                pix.shake(g, t, 1.2)
                self.sparks.burst(x1 - 7, y1 - 7, 8, 18, life=0.4, gravity=20)
            tip = (CH[0] + 14, CH[1] + 30)
        # 砚台小几
        g.d.rectangle((INK[0] - 6, INK[1] + 1, INK[0] + 6, INK[1] + 2), fill=1)
        g.d.line((INK[0] - 5, INK[1] + 3, INK[0] - 5, FLOOR - 1), fill=1)
        g.d.line((INK[0] + 5, INK[1] + 3, INK[0] + 5, FLOOR - 1), fill=1)
        pix.blit(g, prop("ink"), INK[0] - 5, INK[1] - 5)
        # 鹅与笼
        gone = -1
        caged = -1.0
        cage_pos = None
        if on and n % 2 == 1 and k >= 42.5:
            gone = n % 3
            caged = 0.0 if k < 44.2 else ease_in(span(k, 44.2, 47.0)) * 60
        back, back_q = -1, 1.0
        if on and n % 2 == 0 and n > 0 and k < 8.0:   # 新的一只游回来
            back, back_q = (n - 1) % 3, span(k, 0, 8.0)
        if not on:
            back, back_q = 0, span(e3, 0, 3.0)
        pos = self.geese(g, t, gone, caged, back, back_q)
        if on and n % 2 == 1 and k >= 42.5 and pos:
            drop = ease_out(span(k, 42.5, 44.0))
            cx, cy = pos
            cy = lerp(-14, cy - 4, drop) - (caged if caged > 0 else 0)
            g.d.line((cx, -1, cx, cy), fill=1)
            pix.blit(g, prop("cage"), cx - 7, cy)
            if abs(k - 44.0) < dt * 1.01:
                self.sparks.burst(cx, cy + 12, 8, 16, up=10, life=0.5, gravity=40)
        # 小道士
        if not on and e3 < 1.6:
            self.writer(g, t, tip, True, walk_x=lerp(-14, DX, ease_out(span(e3, 0.2, 1.6))))
        else:
            face = "happy" if on and (4.6 <= kk < 5.6 or 42.6 < k < 44.0) else "normal"
            self.writer(g, t, tip, wet, face=face)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 字：顶上一行（本句已写的字）；笼鹅时换成“书罢笼鹅去”
        if on:
            if n % 2 == 1 and 42.5 <= k < 47.8:
                label(g, 126, 2, "书罢笼鹅去", align="right")
            else:
                done = j + (1 if kk >= 4.6 else 0) if k < 42 else 7
                if done:
                    label(g, 126, 2, sent[:done], align="right")
        return writing, sent[j] if k < 42 else None, span(kk, 0.6, 4.6)

    def mx(self, g: Gfx, t: float, writing: bool, ch, q: float):
        if writing and ch:
            gl = glyph(ch)
            a = gl.on
            rows = int(q * 8)
            for y in range(8):
                for x in range(8):
                    if y <= rows and a[y * 3:y * 3 + 3, x * 3:x * 3 + 3].any():
                        g.mx[y, x] = True
            return
        g.mx_blit("""
.##.....
#.#.....
.##.....
..#.....
..######
..######
...####.
""", 0, 0)
        g.mx[7, :] = [((x + int(t * 3)) % 3 == 0) for x in range(8)]

    def enter(self, g: Gfx, t: float):
        self.scene(g, t, min(t / self.T["enter"], 0.999))
        g.mx[7, :] = True

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.mx(g, t, *self.scene(g, t))

    def exit(self, g: Gfx, t: float):
        tt = self.ht + t
        self.mx(g, tt, *self.scene(g, tt))
        iris(g, t / self.T["exit"], 40, 34)
