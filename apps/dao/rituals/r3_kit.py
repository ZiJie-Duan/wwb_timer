"""r3 批次（手诀·法器·步罡）共用的像素工具。不登记场景，只被 r3_*.py 导入。

    arm(kind, hand) / pose_arm(g, x, kind, t, hand, prop=...)
                             小道士的自定义手臂（逐像素造型的道袍袖 + 小拳 / 剑指 / 立掌）：
                             low 腰前 / fwd 平伸 / dn 前下 / reach 斜上远伸 / up30 斜上 / up60 举起 / up90 直举；
                             prop(g, 手) 画手里的法器（prop_behind=True 画在身后）；hand_at 预先算出手的位置
    put(g, spr, x, y)        按精灵的锚点（spr.anchor）贴，返回标记点（spr.pts）的屏幕坐标
    orient8 / a8             由朝右、朝右上两张精灵翻转出 8 个方向（剑之类的长兵器）
    rot_spr / shear_spr / dim_spr   绕锚点旋转、错切摆动（铃）、只留网点的“暗”版本
    smear / hit / sparkle / rays    挥击残影（月牙）、命中星、十字闪光、放射光
    banner / banner_text / label    圆满题字的底板与字、角落小字（先清出黑底再写）
    Clock / crossed / round_of / nth / mx_ring / floor
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine import pix
from ..engine.anim import clamp
from ..engine.chars import Part, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, Sprite

FLOOR = 58
SHOULDER = (-2, -16)
SHOULDERS = {"up60": (4, -16), "up90": (6, -16)}   # 站姿时肩膀相对脚底中点（朝右）


# ---------------------------------------------------------------- 可旋转部件

_C: dict = {}


def cached(key, fn):
    v = _C.get(key)
    if v is None:
        v = _C[key] = fn()
    return v


def put(g: Gfx, spr: Sprite, x: float, y: float, flip: bool = False, outline: bool = True):
    """按锚点贴精灵；返回 {标记名: 屏幕坐标}"""
    ax, ay = spr.anchor
    if flip:
        ox = int(round(x)) - (spr.w - 1 - ax)
    else:
        ox = int(round(x)) - ax
    oy = int(round(y)) - ay
    pix.blit(g, spr, ox, oy, flip=flip, outline=outline)
    out = {}
    for k, (px, py) in spr.pts.items():
        out[k] = (ox + (spr.w - 1 - px if flip else px), oy + py)
    return out


def _xf(spr: Sprite, op: str) -> Sprite:
    """变换精灵并同步锚点、标记点。op：r90（逆时针 90°）/ r270 / r180 / fh（左右翻）/ fv（上下翻）"""
    w, h = spr.w, spr.h

    def m(p):
        x, y = p
        return {"r90": (y, w - 1 - x), "r270": (h - 1 - y, x), "r180": (w - 1 - x, h - 1 - y),
                "fh": (w - 1 - x, y), "fv": (x, h - 1 - y)}[op]
    s = {"r90": lambda: spr.rot90(1), "r270": lambda: spr.rot90(3), "r180": lambda: spr.rot90(2),
         "fh": spr.flip, "fv": spr.flipv}[op]()
    s.anchor = m(spr.anchor)
    s.pts = {k: m(v) for k, v in spr.pts.items()}
    return s


def orient8(base0: Sprite, base45: Sprite) -> dict[int, Sprite]:
    """由朝右（0°）与朝右上（-45°）两张精灵得到 8 个方向：键为角度（屏幕坐标，顺时针为正）"""
    return {0: base0, -90: _xf(base0, "r90"), 180: _xf(base0, "r180"), 90: _xf(base0, "r270"),
            -45: base45, -135: _xf(base45, "fh"), 45: _xf(base45, "fv"), 135: _xf(_xf(base45, "fh"), "fv")}


def a8(ang: float) -> int:
    """角度就近取 8 方向之一"""
    k = int(round((ang % 360) / 45)) % 8 * 45
    return k - 360 if k > 180 else k


# ---------------------------------------------------------------- 手臂（道袍宽袖 + 手）

# 手臂造型表（朝右；同 chars 里 offer / raise 的画法：袖子平底下垂、袖口一道阴线、下沿网点）
#   名字: (宽, 高, 肩点, 袖子多边形, 袖口阴线, 网点区, 手的方块, 是否画在头前面)
ARMS = {
    "fwd": (14, 9, (1, 0), [(0, 0), (4, 0), (10, 3), (10, 7), (2, 7), (0, 5)], (9, 3, 9, 7),
            [(2, 5), (10, 5), (10, 7), (2, 7)], (10, 3), False),
    "low": (13, 12, (1, 0), [(0, 0), (4, 0), (10, 5), (8, 9), (2, 9), (0, 6)], (9, 5, 7, 9),
            [(2, 7), (9, 7), (8, 9), (2, 9)], (9, 7), False),
    "dn": (11, 15, (1, 0), [(0, 0), (4, 0), (8, 7), (7, 11), (1, 11), (0, 6)], (7, 8, 6, 11),
           [(1, 9), (8, 9), (7, 11), (1, 11)], (6, 11), False),
    "up30": (15, 11, (1, 6), [(0, 5), (3, 3), (10, 0), (12, 4), (10, 9), (3, 10), (0, 9)], (10, 1, 11, 5),
             [(2, 8), (11, 6), (10, 9), (3, 10)], (12, 0), False),
    "reach": (18, 11, (1, 6), [(0, 5), (3, 3), (13, 0), (15, 4), (13, 9), (3, 10), (0, 9)], (13, 1, 14, 5),
              [(2, 8), (14, 6), (13, 9), (3, 10)], (15, 0), False),
    "up60": (10, 16, (1, 15), [(0, 15), (3, 15), (8, 3), (6, 1)], (6, 7, 6, 12),
             [(3, 13), (6, 9), (6, 12), (3, 15)], (6, 0), True),
    "up90": (9, 19, (3, 18), [(2, 18), (5, 18), (5, 3), (3, 3)], (6, 8, 6, 14),
             [(5, 11), (8, 11), (8, 15), (5, 16)], (3, 0), True),
}
ARM_KEYS = {"reach": -25, "fwd": 0, "low": 35, "dn": 60, "up30": -30, "up60": -65, "up90": -90}


def _arm(kind: str, hand: str) -> Sprite:
    w, h, hook, poly, cuff, dith, (hx, hy), over = ARMS[kind]
    p = Part(w + 4, h + 4)
    p.shape("polygon", poly, fill=1)
    if kind in ("up60", "up90"):   # 举手：细袖筒 + 从小臂垂下的宽袖
        if kind == "up60":
            sl = [(2, 13), (6, 6), (6, 12), (3, 15)]
        else:
            sl = [(4, 7), (6, 8), (7, 15), (5, 17), (4, 17)]
        p.shape("polygon", sl, fill=1)
    p.d.line(cuff, fill=0)
    p.dither(dith, 0.5, 0)
    p.shape("rectangle", (hx, hy, hx + 2, hy + 2), fill=1)
    hand_pt = (hx + 1, hy + 1)
    ux, uy = math.cos(math.radians(ARM_KEYS[kind])), math.sin(math.radians(ARM_KEYS[kind]))
    if hand == "fist":       # 握拳：圆角小拳
        cx, cy = (hx + 2, hy + 2) if uy > -0.3 else (hx + 2, hy)
        p.on.putpixel((cx, cy), 0)
        p.mk.putpixel((cx, cy), 0)
    elif hand == "jian":     # 剑指：食中二指并伸
        x0, y0 = hx + 1 + ux * 1.5, hy + 1 + uy * 1.5
        for o in (-0.5, 0.5):
            p.shape("line", [(x0 - uy * o, y0 + ux * o), (x0 + ux * 4 - uy * o, y0 + uy * 4 + ux * o)], fill=1)
        hand_pt = (int(round(x0 + ux * 4)), int(round(y0 + uy * 4)))
    elif hand == "open":     # 立掌：四指并拢朝上
        p.shape("rectangle", (hx, hy - 2, hx + 1, hy), fill=1)
        p.px(hx + 2, hy - 1, 1)
        p.px(hx + 1, hy, 0)
    on = np.array(p.on, bool)
    mk = np.array(p.mk, bool)
    s = Sprite(on=on, mask=mk)
    s.anchor = hook
    s.hand = hand_pt
    s.pts = {"hand": hand_pt}
    s.over = over
    return s


def arm(kind: str, hand: str = "fist") -> Sprite:
    return cached(("arm", kind, hand), lambda: _arm(kind, hand))


def hand_at(x: float, y: float, kind: str, t: float, hand: str = "fist", legs: str = "stand", flip: bool = False,
            bob: bool = True, dy: int = 0) -> tuple[int, int]:
    """预先算出 pose_arm 画出来的手在哪（道具要画在身体后面时用）"""
    spr = arm(kind, hand)
    ax, ay = spr.anchor
    sx, sy = SHOULDERS.get(kind, SHOULDER)
    ox, oy = sx - ax, sy - ay
    x, y = int(round(x)), int(round(y)) + dy
    lift = 1 if bob and (t * 0.7) % 1 > 0.5 and legs == "stand" else 0
    bounce = (int(t * 8) % 4) % 2 if legs == "walk" else 0
    oy += lift - bounce if legs in ("stand", "walk") else (-3 if legs == "sit" else 2 if legs == "kneel" else 0)
    hx, hy = spr.hand
    return (x + ox + hx if not flip else x - ox - hx, y + oy + hy)


def pose_arm(g: Gfx, x: float, kind: str, t: float, hand: str = "fist", y: float = FLOOR,
             flip: bool = False, legs: str = "stand", face: str = "normal", head: str = "up", dy: int = 0,
             behind=None, front=None, bob: bool = True, over=None, prop=None, prop_behind: bool = False
             ) -> tuple[float, float]:
    """小道士 + 一只自定义手臂（kind 见 ARMS：fwd low dn up30 up60 up90）；返回手（握点）的屏幕坐标。
    prop(g, (hx, hy))：手里的道具；prop_behind=True 画在身体后面（举过头顶、越过脸的时候）"""
    spr = arm(kind, hand)
    spr.over_head = spr.over if over is None else over
    ax, ay = spr.anchor
    sx, sy = SHOULDERS.get(kind, SHOULDER)
    hp = hand_at(x, y, kind, t, hand, legs, flip, bob, dy)
    bh = behind
    if prop and prop_behind:
        def bh(g2, at):
            if behind:
                behind(g2, at)
            prop(g2, hp)
    out = figure(g, x, y, t, legs=legs, arm=spr, arm_at=(sx - ax, sy - ay), head=head,
                 face=face, flip=flip, behind=bh, front=front, bob=bob, dy=dy)
    if prop and not prop_behind:
        prop(g, out["hand"])
    return out["hand"]


FIST = Sprite("""
.##.
####
#.##
.##.
""")


# ---------------------------------------------------------------- 特效

HIT = pix.frames("""
   #
   #
## # ##
   #
   #
---
#     #
 #   #
   #
 #   #
#     #
---
   #
 #   #
#     #
 #   #
   #
---
#     #

   .

#     #
""")


def hit(g: Gfx, x: float, y: float, k: float):
    """命中星：k ∈ [0,1)"""
    if 0 <= k < 1:
        f = HIT[min(int(k * 4), 3)]
        pix.blit(g, f, x - 3, y - 2, outline=k < 0.5)


def smear(g: Gfx, cx: float, cy: float, r: float, w: float, a0: float, a1: float, solid: float = 0.45):
    """挥击残影（月牙）：以 (cx, cy) 为心、外半径 r，从 a0 扫到 a1（度，a1 为刀头一侧）。
    头部最宽 w，尾部收成一条线；靠头部 solid 的部分实心，尾部网点"""
    if abs(a1 - a0) < 1:
        return
    n = max(6, int(abs(a1 - a0) / 5))
    outer, inner = [], []
    for i in range(n + 1):
        k = i / n
        a = math.radians(a0 + (a1 - a0) * k)
        ww = 0.5 + (w - 0.5) * (k ** 1.5)
        outer.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        inner.append((cx + math.cos(a) * (r - ww), cy + math.sin(a) * (r - ww)))
    m = Image.new("1", (128, 64))
    d = ImageDraw.Draw(m)
    cut = int(n * (1 - solid))
    d.polygon(outer[cut:] + inner[cut:][::-1], fill=1)
    head = np.array(m, bool)
    m2 = Image.new("1", (128, 64))
    ImageDraw.Draw(m2).polygon(outer[:cut + 1] + inner[:cut + 1][::-1], fill=1)
    tail = np.array(m2, bool) & ~head
    ys, xs = np.mgrid[0:64, 0:128]
    a = g.array()
    a[head] = True
    a[tail & ((xs + ys) % 2 == 0)] = True
    a[tail & ((xs + ys) % 2 == 1)] = False
    g.put(a)


def label(g: Gfx, x: float, y: float, s: str, size: int = 12, align: str = "left"):
    """角落的小字：先清出一块黑底（粒子、星点不会钻进字里），再写字"""
    from ..engine.gfx import text_width
    w = text_width(s, size)
    x0 = x - (w / 2 if align == "center" else w if align == "right" else 0)
    h = 11 if size == 12 else 7
    g.d.rectangle((x0 - 1, y - 1, x0 + w, y + h), fill=0)
    g.text(x, y, s, size=size, align=align)


def sparkle(g: Gfx, x: float, y: float, r: int = 2, dark: bool = True):
    """十字闪光（带黑边，压在亮处也清楚）"""
    if dark:
        g.d.rectangle((x - 1, y - r - 1, x + 1, y + r + 1), fill=0)
        g.d.rectangle((x - r - 1, y - 1, x + r + 1, y + 1), fill=0)
    g.d.line((x - r, y, x + r, y), fill=1)
    g.d.line((x, y - r, x, y + r), fill=1)


def rays(g: Gfx, x: float, y: float, r0: float, r1: float, n: int = 8, rot: float = 0.0, dash: int = 0):
    for i in range(n):
        a = rot + i * 2 * math.pi / n
        if dash:
            pix.dotted(g, x + math.cos(a) * r0, y + math.sin(a) * r0, x + math.cos(a) * r1, y + math.sin(a) * r1, dash)
        else:
            g.d.line((x + math.cos(a) * r0, y + math.sin(a) * r0, x + math.cos(a) * r1, y + math.sin(a) * r1), fill=1)


def banner(g: Gfx, cx: float, y: float, s: str, k: float, size: int = 12, box: bool = True):
    """“功德圆满”式弹出题字的底板（字本身请在最后用 text 画）。k = 弹出进度 0..1"""
    from ..engine.anim import ease_out_back
    from ..engine.gfx import text_width
    w = text_width(s, size)
    yy = y + (1 - ease_out_back(k)) * 10
    if box:
        h = 11 if size == 12 else 7
        g.k.rectangle((cx - w / 2 - 3, yy - 2, cx + w / 2 + 2, yy + h + 1), fill=1)
        g.d.rectangle((cx - w / 2 - 4, yy - 3, cx + w / 2 + 3, yy + h + 2), fill=0)
        g.d.rectangle((cx - w / 2 - 3, yy - 2, cx + w / 2 + 2, yy + h + 1), outline=1)
        for px, py in ((cx - w / 2 - 3, yy - 2), (cx + w / 2 + 2, yy - 2), (cx - w / 2 - 3, yy + h + 1),
                       (cx + w / 2 + 2, yy + h + 1)):
            g.px(px, py, 0)
    return yy


def banner_text(g: Gfx, cx: float, y: float, s: str, k: float, size: int = 12):
    from ..engine.anim import ease_out_back
    g.text(cx, y + (1 - ease_out_back(k)) * 10, s, size=size, align="center")


# ---------------------------------------------------------------- 时间 / 文字 / 点阵

class Clock:
    """逐帧 dt（t 回到 0 或跳变时重置）"""

    def __init__(self):
        self.last = None

    def __call__(self, t: float) -> float:
        dt = 1 / 30 if self.last is None or t < self.last else min(t - self.last, 0.2)
        self.last = t
        return dt


def crossed(t: float, dt: float, at: float) -> bool:
    """这一帧刚好越过 at 时刻"""
    return t - dt < at <= t


def round_of(e: float, cycle: float) -> tuple[int, float, float]:
    """→ (第几轮 1.., 本轮已过秒数 k, 本轮进度 p 0..1)"""
    n = int(e // cycle)
    k = e - n * cycle
    return n + 1, k, clamp(k / cycle)


def nth(n: int, unit: str) -> str:
    return f"第{cn_num(n)}{unit}" if n < 100 else f"{n}{unit}"


def mx_ring(g: Gfx, r: float, cx: float = 3.5, cy: float = 3.5):
    for yy in range(8):
        for xx in range(8):
            if abs(math.hypot(xx - cx, yy - cy) - r) < 0.6:
                g.mx[yy, xx] = True


# ---------------------------------------------------------------- 舞台

def floor(g: Gfx, y: int = FLOOR, tiles: bool = True, phase: int = 0):
    """地面线 + 透视地砖 + 稀网点"""
    g.d.line((0, y, 127, y), fill=1)
    if tiles:
        for x in range(-40 + phase, 168, 16):
            g.d.line((x, y + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, y + 1, 128, 64), 0.125)


# ---------------------------------------------------------------- 精灵变换

def rot_spr(spr: Sprite, deg: float) -> Sprite:
    """绕锚点旋转（顺时针为正，最近邻）；按 5° 取整缓存。锚点、标记点一起转"""
    d = int(round(deg / 5.0)) * 5
    if d == 0:
        return spr
    key = ("rot", id(spr), d)
    v = _C.get(key)
    if v is not None:
        return v
    ax, ay = getattr(spr, "anchor", (spr.w // 2, spr.h // 2))
    R = int(math.hypot(max(ax, spr.w - ax), max(ay, spr.h - ay))) + 2
    S = 2 * R + 1

    def big(a):
        im = Image.new("1", (S, S))
        im.paste(Image.fromarray(a), (R - ax, R - ay))
        return im.rotate(-d, resample=Image.NEAREST, center=(R, R))
    on = np.array(big(spr.on), bool)
    mk = np.array(big(spr.mask), bool)
    ys, xs = np.nonzero(mk)
    x0, y0 = xs.min(), ys.min()
    s = Sprite(on=on[y0:ys.max() + 1, x0:xs.max() + 1].copy(), mask=mk[y0:ys.max() + 1, x0:xs.max() + 1].copy())
    c, si = math.cos(math.radians(d)), math.sin(math.radians(d))

    def m(p):
        dx, dy = p[0] - ax, p[1] - ay
        return (int(round(R + dx * c - dy * si)) - x0, int(round(R + dx * si + dy * c)) - y0)
    s.anchor = (R - x0, R - y0)
    s.pts = {k: m(v) for k, v in getattr(spr, "pts", {}).items()}
    _C[key] = s
    return s


def dim_spr(spr: Sprite, level: float = 0.5) -> Sprite:
    """“暗”的版本：亮像素只留网点（未到达、熄灭的东西）"""
    key = ("dim", id(spr), level)
    v = _C.get(key)
    if v is None:
        ys, xs = np.mgrid[0:spr.h, 0:spr.w]
        pat = ((xs + ys) % 2 == 0) if level >= 0.5 else ((xs % 2 == 0) & (ys % 2 == 0))
        v = Sprite(on=spr.on & pat, mask=spr.mask.copy())
        v.anchor = getattr(spr, "anchor", (0, 0))
        v.pts = getattr(spr, "pts", {})
        _C[key] = v
    return v


def art(s: str, anchor=None, **pts) -> Sprite:
    """字符画精灵 + 锚点 / 标记点（直接给坐标）"""
    spr = Sprite(s)
    spr.anchor = anchor or (spr.w // 2, spr.h // 2)
    spr.pts = dict(pts)
    return spr


def shear_spr(spr: Sprite, k: float) -> Sprite:
    """横向错切：锚点以下第 y 行右移 (y - 锚点y) × k（钟、铃摆动用，比旋转干净）"""
    kk = round(k, 2)
    if kk == 0:
        return spr
    key = ("shear", id(spr), kk)
    v = _C.get(key)
    if v is not None:
        return v
    ax, ay = getattr(spr, "anchor", (spr.w // 2, 0))
    offs = [int(round((y - ay) * kk)) for y in range(spr.h)]
    lo, hi = min(min(offs), 0), max(max(offs), 0)
    W = spr.w + hi - lo
    on = np.zeros((spr.h, W), bool)
    mk = np.zeros((spr.h, W), bool)
    for y, o in enumerate(offs):
        on[y, o - lo:o - lo + spr.w] = spr.on[y]
        mk[y, o - lo:o - lo + spr.w] = spr.mask[y]
    v = Sprite(on=on, mask=mk)
    v.anchor = (ax - lo + offs[ay] if 0 <= ay < spr.h else ax - lo, ay)
    v.pts = {n: (p[0] - lo + (offs[p[1]] if 0 <= p[1] < spr.h else 0), p[1]) for n, p in getattr(spr, "pts", {}).items()}
    for attr in ("er",):
        if hasattr(spr, attr):
            setattr(v, attr, getattr(spr, attr))
    _C[key] = v
    return v
