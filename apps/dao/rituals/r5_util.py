"""r5 批（易象·星斗·雷法·风水）共用的像素小工具。不登记场景。

- Clock：按 t 的差值算 dt（t 回到 0 时重置）
- 星：sky 星空、star 十字星（会闪）
- 云：cloud_sprite 逐像素的描边云（白云 / 乌云），只生成一次
- 小道士的新手臂：ARMS[...]（指天剑指、托掌、推掌、举令旗），配 ARM_AT 偏移交给 figure()
- 地面小物：草丛、石头、松树
- 闪电 bolt、波纹、框字 label、弹出的大字 pop_title、点阵小工具
"""
from __future__ import annotations

import math
import random

from ..engine import pix
from ..engine.anim import ease_out_back, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite, text_width


class Clock:
    """混入：self._dt(t) 得到这一帧的 dt"""
    _last_t = None

    def _dt(self, t: float) -> float:
        lt = self._last_t
        dt = 1 / 30 if lt is None or t < lt else min(t - lt, 0.2)
        self._last_t = t
        return dt


_C: dict = {}


def cached(key, fn):
    v = _C.get(key)
    if v is None:
        v = _C[key] = fn()
    return v


# ---------------------------------------------------------------- 星

STAR_S = pix.frames("""
 #
###
 #
---
#.#
.#.
#.#
""")
STAR_L = pix.frames("""
  #
  #
##.##
  #
  #
---
  #
 ###
##.##
 ###
  #
""")


def star(g: Gfx, x: float, y: float, size: int = 1, on: bool = True, phase: float = 0.0, t: float = 0.0):
    """size 0 一点 / 1 小十字 / 2 大十字星（中心镂空、闪烁时变成钻石）"""
    x, y = int(round(x)), int(round(y))
    if not on:
        g.px(x, y)
        return
    if size == 0:
        g.px(x, y)
    elif size == 1:
        pix.blit(g, STAR_S[0], x - 1, y - 1, outline=False)
    else:
        fr = STAR_L[1] if (t * 1.3 + phase) % 1 < 0.18 else STAR_L[0]
        pix.blit(g, fr, x - 2, y - 2, outline=False)
        g.px(x, y, 1)


def sky(g: Gfx, seed: int, t: float, box=(0, 0, 128, 40), n: int = 40, level: float = 1.0):
    """确定性的星空：多数是一点，少数小十字；按各自节奏闪烁"""
    x0, y0, x1, y1 = box
    for i in range(int(n * level)):
        x = x0 + rand(i, seed) * (x1 - x0)
        y = y0 + rand(i, seed + 7) ** 1.3 * (y1 - y0)
        r = rand(i, seed + 3)
        tw = (t * (0.3 + r) + r * 9) % 1
        if r < 0.1:
            if tw < 0.85:
                pix.blit(g, STAR_S[0], int(x) - 1, int(y) - 1, outline=False)
            else:
                g.px(x, y)
        elif tw < 0.9:
            g.px(x, y)


def meteor(g: Gfx, x: float, y: float, k: float, dx: float = -30, dy: float = 14):
    """流星：k ∈ [0, 1] 走完；头亮、尾巴是虚线"""
    if not 0 < k < 1:
        return
    hx, hy = x + dx * k, y + dy * k
    L = 10 * math.sin(math.pi * k)
    ux, uy = -dx / math.hypot(dx, dy), -dy / math.hypot(dx, dy)
    for j in range(int(L)):
        if j < 3 or j % 2 == 0:
            g.px(hx + ux * j, hy + uy * j)
    g.px(hx + 1, hy), g.px(hx, hy + 1)


# ---------------------------------------------------------------- 云

def _cloud(w: int, h: int, seed: int, dark: bool) -> Sprite:
    """描边祥云：几个圆鼓包 + 平底；1 像素白轮廓、内部黑；鼓包里卷一道云纹（像素小漩涡）；
    底部一条网点阴影。乌云：内部整片 25% 网点、下半 50%"""
    import numpy as np
    from PIL import Image, ImageDraw
    rng = random.Random(seed)
    n = max(2, round(w / 10))
    blobs = []
    rmax = (h - 4) / 1.8
    for i in range(n):
        k = (i + 0.5) / n
        r = rmax * (0.7 + 0.3 * math.sin(math.pi * k)) * (0.88 + rng.random() * 0.12)
        cx = 3 + k * (w - 6) + (rng.random() - 0.5) * 2
        cy = h - 4 - r * 0.75
        blobs.append((cx, cy, r))
    m = Image.new("1", (w, h))
    d = ImageDraw.Draw(m)
    for cx, cy, r in blobs:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=1)
    d.rounded_rectangle((0, h - 7, w - 1, h - 1), radius=3, fill=1)
    M = np.array(m, bool)
    P = np.pad(M, 1)
    er = P[1:-1, 1:-1] & P[:-2, 1:-1] & P[2:, 1:-1] & P[1:-1, :-2] & P[1:-1, 2:]
    on = M & ~er
    inner = Image.new("1", (w, h))
    di = ImageDraw.Draw(inner)
    for j, (cx, cy, r) in enumerate(blobs):  # 云纹：小漩涡（3/4 圈 + 中心一点）
        if r < 3:
            continue
        rr = max(2.0, r * 0.5)
        sx = 1 if j % 2 else -1
        a0 = 90 if sx > 0 else -180
        di.arc((cx - rr, cy - rr + 1, cx + rr, cy + rr + 1), a0, a0 + 270, fill=1)
        di.point((int(round(cx)), int(round(cy + 1))), fill=1)
    on |= np.array(inner, bool) & er
    ys, xs = np.mgrid[0:h, 0:w]
    if dark:
        on |= er & ((xs + ys) % 2 == 0) & (ys >= h - 4)
        on |= er & ((xs % 2 == 0) & (ys % 2 == 0)) & (ys == h - 5)
    else:
        on |= er & ((xs % 2 == 0) & (ys % 2 == 0)) & (ys >= h - 3)
    return Sprite(on=on, mask=M)


def cloud_sprite(w: int, h: int, seed: int = 0, dark: bool = False) -> Sprite:
    return cached(("cloud", w, h, seed, dark), lambda: _cloud(w, h, seed, dark))


# ---------------------------------------------------------------- 小道士的新手臂

def _arm_sky():
    """剑指指天（斜向前上方），宽袖从小臂垂下"""
    p = Part(17, 14)
    p.shape("polygon", [(0, 11), (2, 13), (12, 5), (10, 3)], fill=1)         # 袖筒
    p.shape("polygon", [(3, 11), (9, 6), (9, 12), (5, 13)], fill=1)          # 垂袖
    p.d.line((9, 7, 9, 12), fill=0)
    p.dither([(5, 11), (9, 9), (9, 12), (5, 13)], 0.5, 0)
    p.shape("rectangle", (11, 2, 13, 4), fill=1)                             # 手
    p.shape("line", (13, 2, 16, 0), fill=1)                                  # 并拢的两指
    p.shape("line", (14, 3, 16, 1), fill=1)
    p.px(12, 4, 0)
    s = p.sprite()
    s.hand = (16, 0)
    return s


def _arm_palm():
    """托掌过头：掌心朝上，五指张开（接雷）"""
    p = Part(12, 18)
    p.shape("polygon", [(0, 17), (3, 17), (8, 6), (6, 5)], fill=1)
    p.shape("polygon", [(2, 15), (6, 8), (6, 14), (3, 17)], fill=1)
    p.d.line((6, 9, 6, 14), fill=0)
    p.dither([(3, 15), (6, 11), (6, 14), (3, 17)], 0.5, 0)
    p.shape("rectangle", (5, 3, 10, 5), fill=1)                               # 手掌（平托）
    p.d.line((6, 4, 9, 4), fill=0)                                            # 掌纹
    for x in (5, 7, 9):                                                       # 指尖
        p.shape("line", (x, 1, x, 2), fill=1)
    p.shape("line", (11, 3, 11, 4), fill=1)                                   # 拇指
    s = p.sprite()
    s.hand = (7, 1)
    return s


def _arm_push():
    """推掌：手臂平伸，立掌向前（掌心雷发出）"""
    p = Part(16, 11)
    p.shape("polygon", [(0, 3), (4, 3), (11, 5), (11, 8), (2, 9), (0, 7)], fill=1)
    p.d.line((10, 5, 10, 8), fill=0)
    p.dither([(2, 7), (11, 7), (11, 9), (2, 9)], 0.5, 0)
    p.shape("rectangle", (11, 2, 13, 8), fill=1)                              # 立掌（侧面）
    p.shape("rectangle", (12, 0, 13, 1), fill=1)                              # 指尖朝上
    p.px(12, 0, 0)
    p.shape("rectangle", (14, 5, 15, 6), fill=1)                              # 拇指
    p.d.line((11, 2, 11, 4), fill=0)                                          # 指缝
    s = p.sprite()
    s.hand = (14, 5)
    return s


def _arm_hold():
    """小臂端平在胸前（托物 / 拿法器），手在前方"""
    p = Part(13, 9)
    p.shape("polygon", [(0, 0), (4, 0), (9, 3), (9, 7), (2, 8), (0, 5)], fill=1)
    p.d.line((8, 3, 8, 7), fill=0)
    p.dither([(2, 6), (9, 6), (9, 8), (2, 8)], 0.5, 0)
    p.shape("rectangle", (9, 3, 11, 6), fill=1)
    p.px(11, 6, 0)
    s = p.sprite()
    s.hand = (10, 3)
    return s


ARMS_FN = {"sky": _arm_sky, "palm": _arm_palm, "push": _arm_push, "hold": _arm_hold}
ARMS_AT = {"sky": (3, -25), "palm": (6, -34), "push": (-3, -18), "hold": (-3, -16)}


def arm(kind: str) -> Sprite:
    return cached(("arm", kind), ARMS_FN[kind])


def dao(g: Gfx, x, y, kind: str, t: float, flip=False, face="normal", legs="stand", front=None, behind=None,
        head="up") -> dict:
    """用自定义手臂摆的小道士（kind ∈ ARMS_FN）"""
    ox, oy = ARMS_AT[kind]
    if legs == "kneel":
        oy += 2
    return figure(g, x, y, t, legs=legs, arm=arm(kind), arm_at=(ox, oy), face=face, flip=flip, front=front,
                  behind=behind, head=head)


# ---------------------------------------------------------------- 地面小物

GRASS = pix.frames("""
# #
#.# #
.#.#
---
 #  #
# #.#
.#.#
---
  #
# # #
.#.#.
""")


def _rock():
    p = Part(11, 6)
    p.shape("polygon", [(0, 5), (2, 1), (5, 0), (8, 1), (10, 5)], fill=1)
    p.d.line((3, 2, 6, 1), fill=0)
    p.dither([(6, 2), (10, 5), (5, 5)], 0.5, 0)
    p.px(4, 4, 0)
    return p.sprite()


def rock() -> Sprite:
    return cached(("rock",), _rock)


def _pine():
    """小松树 11×16：三层针叶、树干"""
    p = Part(11, 16)
    p.shape("polygon", [(5, 0), (8, 4), (6, 4), (9, 8), (6, 8), (10, 12), (0, 12), (4, 8), (1, 8), (4, 4), (2, 4)],
            fill=1)
    for y, a, b in ((4, 3, 7), (8, 2, 8)):
        p.d.line((a, y, b, y), fill=0)
    p.dither([(6, 2), (10, 12), (5, 12)], 0.5, 0)
    p.shape("rectangle", (4, 12, 6, 15), fill=1)
    p.px(5, 13, 0)
    return p.sprite()


def pine() -> Sprite:
    return cached(("pine",), _pine)


# ---------------------------------------------------------------- 闪电与特效

def bolt_pts(x0, y0, x1, y1, seed: int, jag: float = 4.0, n: int = 7):
    rng = random.Random(seed)
    pts = [(x0, y0)]
    for i in range(1, n):
        k = i / n
        nx, ny = -(y1 - y0), x1 - x0
        L = math.hypot(nx, ny) or 1
        o = (rng.random() - 0.5) * 2 * jag
        pts.append((x0 + (x1 - x0) * k + nx / L * o, y0 + (y1 - y0) * k + ny / L * o))
    pts.append((x1, y1))
    return pts


def bolt(g: Gfx, x0, y0, x1, y1, seed: int, thick: bool = True, jag: float = 4.0, branch: bool = True):
    """锯齿闪电：黑边 + 亮芯（粗的两像素），带一两道分叉"""
    pts = bolt_pts(x0, y0, x1, y1, seed, jag)
    w = 2 if thick else 1
    g.d.line(pts, fill=0, width=w + 2)
    g.d.line(pts, fill=1, width=w)
    if branch:
        rng = random.Random(seed * 3 + 1)
        for _ in range(2):
            i = rng.randrange(1, len(pts) - 2)
            bx, by = pts[i]
            ex = bx + (rng.random() - 0.5) * 16
            ey = by + 4 + rng.random() * 8
            bp = bolt_pts(bx, by, ex, ey, seed + i, 2, 3)
            g.d.line(bp, fill=1)


def ring(g: Gfx, cx, cy, r, ry=None, fill=1):
    ry = r if ry is None else ry
    if r >= 0.5:
        g.d.ellipse((cx - r, cy - ry, cx + r, cy + ry), outline=fill)


def rays(g: Gfx, cx, cy, r0, r1, n=8, rot=0.0, step=2):
    for i in range(n):
        a = rot + i * 2 * math.pi / n
        pix.dotted(g, cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * r1, cy + math.sin(a) * r1, step)


def sparkle(g: Gfx, x, y, k: float):
    """一颗闪光（十字由短变长再收）"""
    L = int(round(3 * math.sin(math.pi * max(0, min(k, 1)))))
    if L <= 0:
        return
    x, y = int(x), int(y)
    for d in range(1, L + 1):
        g.px(x + d, y), g.px(x - d, y), g.px(x, y + d), g.px(x, y - d)
    g.px(x, y, 0 if L > 2 else 1)


# ---------------------------------------------------------------- 字

def label(g: Gfx, x: float, y: float, s: str, size: int = 12, box: bool = True, align: str = "left"):
    """带框的标签（框画在黑底上，字最后画）"""
    w = text_width(s, size)
    hh = 11 if size == 12 else 7
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    if box:
        g.k.rectangle((x - 3, y - 3, x + w + 2, y + hh + 2), fill=1)
        g.d.rectangle((x - 3, y - 3, x + w + 2, y + hh + 2), fill=0, outline=1)
    g.text(x, y, s, size=size)
    return w


def pop_box(g: Gfx, cx: float, y: float, s: str, t: float, t0: float, stars: bool = True):
    """圆满大字：带框弹出（ease_out_back），两侧小星闪；返回 (x, y) 供最后写字"""
    pop = ease_out_back(span(t, t0, t0 + 0.4))
    w = text_width(s)
    yy = y + (1 - pop) * 10
    g.k.rectangle((cx - w / 2 - 3, yy - 2, cx + w / 2 + 2, yy + 12), fill=1)
    g.d.rectangle((cx - w / 2 - 3, yy - 2, cx + w / 2 + 2, yy + 12), fill=0, outline=1)
    if stars and int(t * 6) % 2 == 0:
        for sx in (cx - w / 2 - 7, cx + w / 2 + 6):
            pix.blit(g, STAR_S[0], sx - 1, yy + 3, outline=False)
    return yy


# ---------------------------------------------------------------- 点阵

def mx_line(g: Gfx, x0: float, y0: float, x1: float, y1: float):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        k = i / max(n, 1)
        g.mx_set(int(round(x0 + (x1 - x0) * k)), int(round(y0 + (y1 - y0) * k)))


def mx_ring(g: Gfx, r: float, w: float = 0.6):
    for y in range(8):
        for x in range(8):
            if abs(math.hypot(x - 3.5, y - 3.5) - r) < w:
                g.mx[y, x] = True


def mx_sprite(g: Gfx, art: str):
    g.mx_blit(art)


def arrow_head(g: Gfx, x: float, y: float, ang: float, s: float = 3.0):
    """箭头：尖在 (x, y)，指向 ang（弧度，0 = 向右）"""
    for da in (2.6, -2.6):
        g.d.line((x, y, x + math.cos(ang + da) * s, y + math.sin(ang + da) * s), fill=1)
