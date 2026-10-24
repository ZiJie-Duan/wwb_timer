"""白鹿衔芝：千岁白鹿在松下，灵芝破土，鹿低头衔起。

依据：葛洪《抱朴子·内篇·对俗》“虎及鹿、兔，皆寿千岁，寿满五百岁者，其毛色白。”
      灵芝是《抱朴子·仙药》里的“芝”，仙药上品；白鹿常作寿星、仙人的坐骑，“鹿衔灵芝”是传统的长寿图样。
入场：松树与山石先显出来，白鹿从右边轻步走进松下站定，抬头。
持续：白鹿静立，耳朵不时抖一下、短尾一翘、偶尔低头啃草、眨眼。
      每 45 秒：鹿前的地上冒出一株灵芝（菌盖一圈圈长开、闪光），鹿低头把它衔起，抬头衔着站一会儿，
      最后灵芝化作一圈光点散入鹿身，鹿身微微放光。
收场：白鹿抬头，小跑着往左隐进松林，画面收拢。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Bake, mx_sprite

G = 58
NECK = (55, 37)      # 颈根
ZX = 43              # 灵芝长出来的位置
EV0, EV_P = 14.0, 45.0


def _pine() -> Sprite:
    """左边的老松：弯干 + 三层针叶团。宽 40，高 58"""
    b = Bake(40, 58)
    trunk = [(10, 57), (13, 44), (11, 32), (15, 20), (19, 10), (22, 10), (18, 21), (15, 33), (18, 45), (17, 57)]
    b.poly(trunk, 0.0)
    for y in (24, 36, 48):                                       # 树皮鳞纹
        b.line([(13, y), (15, y + 2)])
    b.line([(15, 26), (5, 20)])                                  # 横枝
    b.line([(17, 15), (30, 12)])

    def clump(cx, cy, w, h):
        """一簇松针：扁圆的顶 + 从枝头放射的针叶"""
        pts = [(cx + math.cos(math.pi * i / 10) * w, cy - math.sin(math.pi * i / 10) * h) for i in range(11)]
        b.poly(pts, 0.0)
        for i in range(1, 10):
            a = math.pi * i / 10
            b.line([(cx + math.cos(a) * w * 0.25, cy - 1), (cx + math.cos(a) * (w - 2), cy - math.sin(a) * (h - 2))])
    clump(6, 21, 7, 5)
    clump(30, 13, 9, 5)
    clump(19, 6, 8, 5)
    return b.sprite()


def _rock() -> Sprite:
    b = Bake(26, 16)
    b.poly([(0, 15), (3, 6), (9, 1), (16, 2), (22, 7), (25, 15)], 0.0)
    b.line([(9, 1), (11, 7), (8, 15)])
    b.line([(16, 2), (17, 8)])
    b.line([(4, 9), (7, 10)])
    return b.sprite()


PINE = _pine()
ROCK = _rock()

MX_ANTLER = """
#.#..#.#
.##..##.
..#..#..
..####..
..#..#..
...##...
...##...
........
"""
MX_ZHI = """
..####..
.######.
########
.#.##.#.
...##...
...#....
...##...
........
"""


def rot(pts, phi, ox, oy):
    c, s = math.cos(phi), math.sin(phi)
    return [(ox + x * c - y * s, oy + x * s + y * c) for x, y in pts]


SKULL = [(4, -3), (0, -3), (-5, -2), (-9, 0), (-9, 2), (-5, 3), (2, 3), (5, 1)]
EAR = [(3, -3), (8, -6), (6, -2)]
ANTLER = [[(2, -3), (3, -8), (6, -13), (9, -15)], [(3, -8), (0, -11)], [(5, -11), (3, -15)], [(6, -13), (7, -18)]]


def lingzhi(g: Gfx, x: float, y: float, p: float = 1.0, glow: float = 0.0):
    """灵芝：(x, y) 为菌柄根部，p 0..1 生长"""
    if p <= 0:
        return
    sh = 7 * clamp(p * 1.6)
    g.d.line((x, y, x + 1, y - sh * 0.6, x, y - sh), fill=1)
    cp = clamp((p - 0.3) / 0.7)
    if cp > 0:
        w, h = 6 * cp, 4 * cp
        cx, cy = x, y - sh
        g.d.chord((cx - w, cy - h, cx + w, cy + h), 180, 360, fill=0, outline=1)
        if cp > 0.6:   # 菌盖的同心云纹
            g.d.arc((cx - w + 2, cy - h + 2, cx + w - 2, cy + h - 2), 200, 340, fill=1)
            g.px(cx, cy - 1)
    if glow > 0:
        for i in range(5):
            if blink(glow * 3 + i * 0.37, 0.9, 0.5):
                a = rand(i, 3) * 2 * math.pi
                r = 7 + rand(i, 4) * 5
                px, py = x + math.cos(a) * r, y - sh + math.sin(a) * r * 0.7
                g.px(px, py)
                if rand(i, 5) > 0.5:
                    g.px(px - 1, py)
                    g.px(px + 1, py)
                    g.px(px, py - 1)
                    g.px(px, py + 1)


def deer(g: Gfx, x: float, t: float, graze: float = 0.0, ear: float = 0.0, tail: float = 0.0, step: float = 0.0,
         hold_zhi: bool = False, blinking: bool = False, glow: float = 0.0, face: int = 1, seed: int = 0):
    """白鹿（朝左）。x = 平移量；graze 0 抬头 → 1 嘴到地面；step 走路的相位（0 = 站定）"""
    def X(v):
        return x + v
    bob = abs(math.sin(step * math.pi)) * 1.0 if step else 0
    # 腿：前腿一对、后腿一对（远侧的细）
    legs = ((54, 0.0, 1), (58, math.pi, 0), (72, math.pi, 1), (76, 0.0, 0))
    for lx, p0, near in legs:
        sw = math.sin(step * math.pi * 2 + p0) * 3 if step else 0
        top = 43 - bob
        kx = X(lx) + sw * 0.4
        fx = X(lx) + sw
        hock = 1 if lx > 65 else -1   # 后腿有反关节
        g.d.line((X(lx), top, kx + hock, 51, fx, G - 1), fill=1)
        if near:
            g.d.line((X(lx) + 1, top, kx + hock + 1, 51), fill=1)
        g.d.line((fx - 1, G, fx + 1, G), fill=1)
    # 身体
    by = -bob
    g.d.ellipse((X(50), 33 + by, X(80), 46 + by), fill=0, outline=1)
    g.d.line((X(56), 44 + by, X(74), 44 + by), fill=0)
    for i in range(5):  # 背上的淡斑（白鹿的毛，稀疏的点）
        g.px(X(58 + i * 4), 37 + by + (i % 2))
    # 尾巴
    tl = 3 + tail * 2
    g.d.line((X(79), 36 + by, X(81), 36 + by - tl), fill=1)
    g.d.line((X(80), 36 + by, X(82), 36 + by - tl + 1), fill=1)
    # 颈 + 头：颈根 NECK，头随 graze 从上方转到地面
    nx, ny = X(NECK[0]), NECK[1] + by
    a = lerp(-2.1, -3.7, ease_in_out(graze))          # 颈的方向（弧度，0 = 向右）
    ln = lerp(13, 15, graze)
    hx, hy = nx + math.cos(a) * ln, ny + math.sin(a) * ln * 1.0 + (graze * 2)
    phi = lerp(0.15, -0.95, ease_in_out(graze))       # 头的朝向：0 = 嘴朝左
    nk = [(nx - 4, ny + 3), (nx + 3, ny - 2), (hx + 3, hy - 1), (hx - 1, hy + 3)]
    g.d.polygon(nk, fill=0, outline=1)
    g.d.polygon([(nx - 3, ny + 2), (nx + 2, ny - 1), (hx + 2, hy - 1), (hx, hy + 2)], fill=0)
    # 鹿角（在头后面先画）
    for br in ANTLER:
        g.d.line(rot(br, phi, hx, hy), fill=1)
        g.d.line(rot([(px + 2, py) for px, py in br], phi, hx, hy), fill=1)
    skull = rot(SKULL, phi, hx, hy)
    g.d.polygon(skull, fill=0, outline=1)
    # 耳朵：不时一抖
    e = [(3, -3), (8 - ear * 2, -6 - ear * 2), (6, -2)]
    g.d.polygon(rot(e, phi, hx, hy), fill=0, outline=1)
    ex, ey = rot([(-2, -1)], phi, hx, hy)[0]
    if not blinking:
        g.px(ex, ey)
        g.px(ex + 1, ey)
    nx_, ny_ = rot([(-9, 1)], phi, hx, hy)[0]
    g.px(nx_, ny_)
    if hold_zhi:   # 嘴里衔着灵芝：菌柄横在嘴里，菌盖朝前下
        mx_, my_ = rot([(-7, 3)], phi, hx, hy)[0]
        g.d.line((mx_ + 2, my_, mx_ - 3, my_ + 2), fill=1)
        g.d.chord((mx_ - 9, my_ - 1, mx_ - 1, my_ + 7), 90, 270, fill=0, outline=1)
        g.d.arc((mx_ - 7, my_ + 1, mx_ - 3, my_ + 5), 110, 250, fill=1)
    if glow > 0:   # 鹿身放光：一圈光点
        for i in range(10):
            if rand(i + int(t * 6), seed) < glow:
                a = rand(i, 11) * 2 * math.pi
                g.px(X(65) + math.cos(a) * (18 + rand(i, 12) * 4), 38 + math.sin(a) * 10)
    return hx, hy, phi


@register
class WhiteDeer(Rest):
    id = "x4.deer"
    name = "白鹿衔芝"
    desc = "千岁白鹿立在老松下抖耳啃草；灵芝破土发光，鹿低头衔起，灵芝化光入鹿身"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ear_p = self.rng.uniform(4.5, 7.0)

    # ------------------------------------------------------------ 布景

    def scenery(self, g: Gfx, t: float, a: float = 1.0):
        g.d.line((0, G, 127, G), fill=1)
        g.blit(PINE, 0, G - 57)
        g.blit(ROCK, 88, G - 15)
        for i, gx in enumerate((32, 46, 84, 108, 118)):   # 草丛
            sw = math.sin(t * 0.8 + i) * 1
            g.d.line((gx, G, gx - 1 + sw, G - 4), fill=1)
            g.d.line((gx + 2, G, gx + 3 + sw, G - 5), fill=1)
        if a > 0:
            s = "鹿寿千岁"
            g.vtext(114, 2, s[:int(round(a * len(s)))])

    # ------------------------------------------------------------ 日常 + 事件

    def state(self, t: float):
        """返回 dict：graze, zhi_p, zhi_glow, hold, absorb, glow"""
        st = dict(graze=0.0, zhi=0.0, zglow=0.0, hold=False, absorb=-1.0, glow=0.0)
        k = (t + 6) % 23            # 平常：偶尔低头啃草
        if k < 4.0:
            st["graze"] = ease_in_out(span(k, 0, 1.0)) * (1 - ease_in_out(span(k, 3.0, 4.0))) * 0.9
        if t >= EV0:
            k = (t - EV0) % EV_P
            if k < 22:
                st["graze"] = 0.0
            if k < 3.0:            # 灵芝破土、长开
                st["zhi"] = ease_out(span(k, 0, 2.5))
                st["zglow"] = k
            elif k < 5.5:          # 鹿低头去衔
                st["zhi"] = 1.0
                st["zglow"] = k
                st["graze"] = ease_in_out(span(k, 3.0, 4.6))
                if k > 4.8:
                    st["zhi"] = 0.0
                    st["hold"] = True
                    st["graze"] = 1 - ease_in_out(span(k, 4.8, 5.5)) * 0.0
            elif k < 7.0:          # 衔着抬起头
                st["hold"] = True
                st["graze"] = 1 - ease_in_out(span(k, 5.5, 7.0))
            elif k < 19.0:         # 衔芝而立
                st["hold"] = True
            elif k < 21.0:         # 灵芝化光入鹿身
                st["absorb"] = (k - 19.0) / 2.0
                st["glow"] = 1.0
            elif k < 24.0:
                st["glow"] = 1 - (k - 21.0) / 3.0
        return st

    def mx(self, g: Gfx, t: float, st):
        if st["zhi"] > 0 or st["hold"] or st["absorb"] >= 0:
            mx_sprite(g, MX_ZHI)
            if st["zhi"] > 0 and st["zhi"] < 1:      # 自下而上长出来
                g.mx[:int(7 - st["zhi"] * 7), :] = False
            if st["absorb"] >= 0:
                g.mx_level = 1 + int(6 * math.sin(st["absorb"] * math.pi))
                if st["absorb"] > 0.5:
                    g.mx[:] = False
                    r = (st["absorb"] - 0.5) * 10
                    for y in range(8):
                        for x in range(8):
                            if abs(math.hypot(x - 3.5, y - 3.5) - r) < 0.7:
                                g.mx[y, x] = True
            return
        mx_sprite(g, MX_ANTLER)
        if st["glow"] > 0 and blink(t, 0.4):
            g.mx[7, :] = True

    def draw(self, g: Gfx, t: float, x: float = 0.0, step: float = 0.0, text: float = 1.0, st=None):
        st = st or self.state(t)
        self.scenery(g, t, text)
        k = (t % self.ear_p)
        ear = 1.0 if k < 0.25 else 0.0
        tail = 1.0 if (t + 2) % 9.0 < 0.4 else 0.0
        blinking = (t % 3.7) < 0.12
        if st["zhi"] > 0:
            lingzhi(g, ZX, G, st["zhi"], st["zglow"])
        hx, hy, phi = deer(g, x, t, st["graze"], ear, tail, step, st["hold"], blinking, st["glow"], seed=self.seed)
        if st["absorb"] >= 0:   # 衔着的灵芝缩成光点，沿颈飘进身体
            p = st["absorb"]
            mx_, my_ = rot([(-11, 5)], phi, hx, hy)[0]
            for i in range(6):
                q = clamp(p * 1.3 - i * 0.05)
                px = lerp(mx_, 65 + x, q) + math.sin(q * 6 + i) * 3
                py = lerp(my_, 40, q) + math.cos(q * 5 + i) * 3
                g.px(px, py)
                if i % 2 == 0:
                    g.px(px + 1, py)
            if p < 0.3:
                g.d.chord((mx_ - 3, my_ - 3, mx_ + 3, my_ + 3), 180, 360, fill=0, outline=1)
        self.mx(g, t, st)

    def hold(self, g: Gfx, t: float):
        self.draw(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        p = span(t, 0.2, 2.4)
        x = lerp(70, 0, ease_out(p))
        step = t * 1.3 if p < 1 else 0.0
        st = dict(graze=0.0, zhi=0.0, zglow=0.0, hold=False, absorb=-1.0, glow=0.0)
        self.draw(g, t, x, step, span(t, 1.4, T), st)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        st = self.state(t0)
        st["graze"] *= 1 - span(t, 0, 0.3)
        p = ease_in(span(t, 0.15, T))
        # 小跑着往左，隐进松林
        x = -p * 110
        self.scenery(g, t0 + t, 1 - span(t, 0, 0.6))
        hx, hy, phi = deer(g, x, t0 + t, st["graze"], 0, 1.0, t * 3 if p > 0 else 0, st["hold"], False, 0.0,
                           seed=self.seed)
        self.mx(g, t0 + t, st)
        g.fade(1 - span(t, T * 0.6, T))
