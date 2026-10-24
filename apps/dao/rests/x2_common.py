"""x2 批（琴棋书画、茶与酒）共用的小工具（像素风）。不登记场景。

    Clock                    算 dt（t 回到 0 也不出错）
    win(t, period, dur, off) 周期事件窗口
    iris(g, p)               退场：画面收成一个圆
    arm(dx, dy, hand)        小道士的“万向手臂”：肩到手的位移 (dx, dy)，画宽袖 + 手（缓存）
    put_arm(dx, dy, ...)     → figure() 用的 (arm 精灵, arm_at)
    far_arm(...)             另一只手（在 figure 的 behind 回调里画，躲在身后）
    wisp(g, x, y, h, t)      一缕像素热气 / 茶烟（断续上升的波浪线）
    label / vlabel           字：先铺黑底板再写（最后画，保证不被压住）
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import clamp, ease_in, rand
from ..engine.chars import Part
from ..engine.gfx import Gfx, Sprite, text_width

# 肩（相对脚底中点，朝右，站姿）；figure 会再按腿型加偏移（盘坐 -3、跪 +2、站时呼吸 +1）
SHOULDER = (2, -15)
LEG_DY = {"stand": 0, "walk": 0, "sit": -3, "kneel": 2}


class Clock:
    def __init__(self):
        self.last = None

    def dt(self, t: float) -> float:
        dt = 1 / 30 if self.last is None or t < self.last else min(t - self.last, 0.2)
        self.last = t
        return dt


def win(t: float, period: float, dur: float, offset: float = 0.0):
    """周期事件：每 period 秒（从 offset 起）发生一次、持续 dur 秒。
    → (k, n)：k = 本次事件已过的秒数（不在事件中为 None），n = 第几次（从 0 起）"""
    if t < offset:
        return None, -1
    k = (t - offset) % period
    n = int((t - offset) // period)
    return (k if k < dur else None), n


_GRID = np.mgrid[0:64, 0:128].astype(np.float32)


def iris(g: Gfx, p: float, cx: float = 64, cy: float = 32):
    """退场：画面向 (cx, cy) 收成一个圆后消失（p 0..1），圆边是一圈虚点"""
    if p <= 0:
        return
    r = (1 - ease_in(p)) * 80
    a = g.array()
    ys, xs = _GRID
    a[(xs - cx) ** 2 + ((ys - cy) * 1.6) ** 2 > r * r] = False
    g.put(a)
    if 2 < r < 75:
        boxes = [b[1:5] for b in g.text_boxes]
        n = max(12, int(r * 3))
        for i in range(0, n, 2):
            ang = i / n * 2 * math.pi
            x, y = cx + math.cos(ang) * r, cy + math.sin(ang) * r / 1.6
            if any(x0 - 1 <= x <= x1 and y0 - 1 <= y <= y1 for x0, y0, x1, y1 in boxes):
                continue                      # 圈边不压字
            g.px(x, y)


# ---------------------------------------------------------------- 手臂

_ARMS: dict = {}


def arm(dx: int, dy: int, hand: str = "fist", over: bool = False) -> Sprite:
    """宽袖手臂：肩在精灵的 .sh，手在 .hand（= 肩 + (dx, dy)）。
    hand：fist 握拳（拿东西）/ open 张开 / pinch 捏笔（拇指与食指捏住，手背朝外）
    over=True：画在头的前面（手举到嘴边、头顶时用）"""
    dx, dy = int(round(dx)), int(round(dy))
    key = (dx, dy, hand, over)
    s = _ARMS.get(key)
    if s is not None:
        return s
    L = max(math.hypot(dx, dy), 1.0)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux                       # 垂直方向，取朝下的一边（袖子往下垂）
    if ny < 0 or (ny == 0 and nx < 0):
        nx, ny = -nx, -ny
    pad = 7
    w, h = abs(dx) + pad * 2 + 1, abs(dy) + pad * 2 + 1
    sx, sy = pad + max(0, -dx), pad + max(0, -dy)
    hx, hy = sx + dx, sy + dy
    p = Part(w, h)
    cl = max(L - 2.5, 1.0)                 # 袖口位置
    cx, cy = sx + ux * cl, sy + uy * cl
    droop = 1.5 + min(L, 14) * 0.12        # 宽袖下垂
    poly = [(sx - nx * 1.6, sy - ny * 1.6), (sx + nx * 2.2, sy + ny * 2.2),
            (cx + nx * 3.0, cy + ny * 3.0 + droop), (cx + nx * 3.0, cy + ny * 3.0),
            (cx - nx * 2.0, cy - ny * 2.0)]
    p.shape("polygon", [(round(x), round(y)) for x, y in poly], fill=1)
    p.shape("ellipse", (sx - 2, sy - 2, sx + 2, sy + 2), fill=1)     # 肩头圆一点
    # 袖口镶边（暗线）
    p.d.line((round(cx - nx * 2.0), round(cy - ny * 2.0), round(cx + nx * 3.0), round(cy + ny * 3.0 + droop)), fill=0)
    # 背光面：只在袖子下缘一窄条加网点
    mx, my = sx + ux * L * 0.3, sy + uy * L * 0.3
    p.dither([(round(mx + nx * 1.5), round(my + ny * 1.5)), (round(cx + nx * 2.0), round(cy + ny * 2.0)),
              (round(cx + nx * 4), round(cy + ny * 4 + droop)), (round(mx + nx * 4), round(my + ny * 4))], 0.5, 0)
    # 手
    ex, ey = hx + ux * 0.5, hy + uy * 0.5
    if hand == "open":
        p.shape("ellipse", (round(ex - 1.5), round(ey - 1), round(ex + 1.5), round(ey + 1)), fill=1)
        p.px(round(ex + ux * 2), round(ey + uy * 2))
    else:
        p.shape("rectangle", (round(hx - 1), round(hy - 1), round(hx + 1), round(hy + 1)), fill=1)
        if hand == "pinch":
            p.px(round(hx), round(hy - 1), 0)
        else:
            p.px(round(hx + (1 if ux >= 0 else -1)), round(hy), 0)     # 指缝
    s = p.sprite()
    s.sh = (sx, sy)
    s.hand = (hx, hy)
    s.over_head = over
    _ARMS[key] = s
    return s


def put_arm(dx, dy, hand="fist", over=False, shoulder=SHOULDER):
    """→ (精灵, arm_at)，直接传给 figure(arm=…, arm_at=…)"""
    s = arm(dx, dy, hand, over)
    return s, (shoulder[0] - s.sh[0], shoulder[1] - s.sh[1])


def far_arm(g: Gfx, x: float, y: float, dx, dy, legs: str = "stand", hand: str = "fist", flip: bool = False,
            lift: int = 0):
    """另一只手（身后那只）：直接画在屏幕上，(x, y) 同 figure 的脚底点。返回手的屏幕坐标"""
    s = arm(dx, dy, hand)
    ox = SHOULDER[0] + 1 - s.sh[0]
    oy = SHOULDER[1] - 1 - s.sh[1] + LEG_DY.get(legs, 0) + lift
    x, y = int(round(x)), int(round(y))
    if flip:
        pix.blit(g, s, x - ox - s.w, y + oy, flip=True)
        return (x - ox - s.hand[0] - 1 + 1, y + oy + s.hand[1])
    pix.blit(g, s, x + ox, y + oy)
    return (x + ox + s.hand[0], y + oy + s.hand[1])


def shoulder_xy(x, y, legs="stand", flip=False):
    sx = SHOULDER[0]
    return (x - sx if flip else x + sx, y + SHOULDER[1] + LEG_DY.get(legs, 0))


# ---------------------------------------------------------------- 热气、文字

def wisp(g: Gfx, x: float, y: float, h: int, t: float, seed: int = 0, amp: float = 1.4, speed: float = 7.0,
         lean: float = 0.0):
    """一缕像素热气：断续的小段沿正弦摆动往上走，顶端稀疏。lean：越往上越偏（被风吹）"""
    for i in range(int(h)):
        if (i - t * speed + seed * 5) % 7 >= 4:
            continue
        k = i / max(h, 1)
        if k > 0.6 and rand(int(i - t * speed), seed) < (k - 0.6) * 2.2:
            continue
        xx = x + math.sin(i * 0.38 - t * 2.1 + seed) * amp * (0.3 + k) + lean * k * k
        g.px(xx, y - i)


def plate(g: Gfx, box, frame: bool = False):
    x0, y0, x1, y1 = box
    g.d.rectangle((x0, y0, x1, y1), fill=0)
    if frame:
        g.d.rectangle((x0, y0, x1, y1), outline=1)


def label(g: Gfx, x: float, y: float, s: str, size: int = 12, align: str = "left", frame: bool = False,
          pad: int = 2) -> int:
    """铺黑底板再写字（最后画）"""
    if not s:
        return 0
    w = text_width(s, size)
    if align == "center":
        x0 = x - w / 2
    elif align == "right":
        x0 = x - w
    else:
        x0 = x
    hh = 11 if size == 12 else 7
    plate(g, (x0 - pad, y - pad, x0 + w + pad - 1, y + hh + pad - 1), frame)
    g.text(x0, y, s, size=size)
    return w


def vlabel(g: Gfx, x: float, y: float, s: str, size: int = 12, frame: bool = False, pad: int = 2) -> int:
    if not s:
        return 0
    step = (11 if size == 12 else 7) + 1
    hgt = len(s) * step - 1
    plate(g, (x - pad, y - pad, x + size + pad - 1, y + hgt + pad - 1), frame)
    return g.vtext(x, y, s, size=size)


def typed(s: str, k: float, cps: float = 4.0) -> str:
    """逐字显出：k 秒时显示的前缀"""
    if k <= 0:
        return ""
    return s[:min(len(s), int(k * cps) + 1)]


def jitter(i: int, seed: int, amp: float = 1.0) -> float:
    return (rand(i, seed) - 0.5) * 2 * amp


def clamp01(x):
    return clamp(x)


# ---------------------------------------------------------------- 常用小景物（精灵）

TUFT = pix.frames("""
 # #
# ##
---
  # #
 # #
---
#  #
 ##
""")

ROCK = Sprite("""
   ......
  .####..#.
 .#####.###.
.######..###.
.####.####.##.
.###.######.##
""")


def _rock(w: int, h: int, seed: int = 0) -> Sprite:
    """石头：圆顶块面 + 顶面高光 + 右侧网点 + 一两道裂纹"""
    p = Part(w, h)
    p.shape("polygon", [(0, h - 1), (1, h // 3), (w // 4, 1), (w * 3 // 5, 0), (w - 2, h // 4), (w - 1, h - 1)], fill=1)
    p.d.line((2, h // 3 + 1, w // 4 + 1, 2), fill=0)
    p.d.line((w * 3 // 5 - 1, 1, w // 4 + 2, 2), fill=0)
    p.d.line((w // 2, h // 3, w // 2 + 2, h - 3), fill=0)
    p.dither([(w // 2 + 2, 0), (w, 0), (w, h), (w // 2 + 3, h)], 0.5, 0)
    p.d.line((0, h - 1, w - 1, h - 1), fill=1)
    return p.sprite()


_ROCKS: dict = {}


def rock(w: int, h: int) -> Sprite:
    if (w, h) not in _ROCKS:
        _ROCKS[(w, h)] = _rock(w, h)
    return _ROCKS[(w, h)]


def mx_clear(g: Gfx):
    g.mx[:] = False


_CROPS: dict = {}


def crop_below(spr: Sprite, r0: int) -> Sprite | None:
    """精灵只留第 r0 行以下（缓存；画“露在前景物上面的那截手”用）"""
    r0 = max(0, int(r0))
    if r0 >= spr.h:
        return None
    if r0 == 0:
        return spr
    key = (id(spr), r0)
    c = _CROPS.get(key)
    if c is None:
        c = Sprite(on=spr.on[r0:].copy(), mask=spr.mask[r0:].copy())
        _CROPS[key] = (c, spr)    # 同时持有原精灵，防止 id 被复用
        return c
    return c[0]


NOTE = pix.frames("""
 ##
 # #
 #
##
##
---
 #
 ##
 # #
##
##
""")
