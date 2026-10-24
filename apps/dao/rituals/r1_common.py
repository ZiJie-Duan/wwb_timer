"""r1 批（香火·供奉·科仪）共用的像素零件：任意角度的宽袖手臂、舞台、计数牌、闪星、点阵小工具。

本文件不登记场景，只被 r1_*.py 导入。画风与 r0_incense.py 一致：逐像素精灵、黑边、规则网点。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_out_back, span
from ..engine.chars import Part
from ..engine.gfx import Gfx, Sprite, text_width

FLOOR = 58


class Clock:
    """按 t 的差值算 dt（t 回到 0 或断线重连时给一帧的默认值）"""

    def __init__(self):
        self.last = None

    def __call__(self, t: float) -> float:
        dt = 1 / 30 if self.last is None or t < self.last else min(t - self.last, 0.2)
        self.last = t
        return dt


def hit(t: float, at: float, dt: float) -> bool:
    """这一帧刚好跨过 at 时刻（触发一次性的打击特效）"""
    return t - dt < at <= t


# ---------------------------------------------------------------- 手臂

# 逐像素手画的宽袖手臂（朝右）：S = 肩点，H = 手心（都算亮像素）。袖口一道暗线是镶边，下垂的袖子带网点。
_ARM_ART = {
    -60: """
        .##
        #H#
       .###
      .###
     ####.#
    ####.#
   ####.#.
  S###.#.
  ####.#
   #.#.
""",
    -30: """
           ###
          #H##
         .###
       ..###.
     #####..#
   ######.#.
  S#####.#.
  #####.#.
   #.#.#
""",
    0: """
  S###
  ######
  ########.###
  ########.H##
  ########.##.
  #########.
   #.#.#.#.
    #.#.#.
""",
    30: """
  S##
  #####
  #######
  ########
  #########.
   ########.##
    #.#.#.#.H#
     .#.#.#.##
       .#.
""",
    60: """
  S##
  ####
  #####
  ######
  #######
  .######
   #.#.##.
    #.#.#.#
     #.#..###
        .#H#
         ###
""",
}

_ARMS: dict = {}


def arm(ang: float, length: int = 0, hand: str = "fist", drape: float = 1.0) -> Sprite:
    """宽袖手臂（朝右）：ang 取最近的 -60 / -30 / 0 / 30 / 60 度（0 向前、负向上、正向下）。
    精灵 .hand = 手心、.shoulder = 肩点；-60 时画在头前面（over_head）"""
    k = min(_ARM_ART, key=lambda a: abs(a - ang))
    spr = _ARMS.get(k)
    if spr is not None:
        return spr
    rows = _ARM_ART[k].strip("\n").split("\n")
    sx = sy = hx = hy = 0
    for y, ln in enumerate(rows):
        if "S" in ln:
            sx, sy = ln.index("S"), y
        if "H" in ln:
            hx, hy = ln.index("H"), y
    art = "\n".join(ln.replace("S", "#").replace("H", "#") for ln in rows)
    # Sprite 会去掉公共缩进：按去掉的量修正坐标
    ind = min(len(ln) - len(ln.lstrip(" ")) for ln in rows if ln.strip())
    spr = Sprite(art)
    spr.shoulder = (sx - ind, sy)
    spr.hand = (hx - ind, hy)
    spr.over_head = k <= -60
    spr.raised = k < 0
    _ARMS[k] = spr
    return spr


SHOULDER = (-1, -15)  # 肩点（相对脚底中点，朝右）；站姿


def arm_at(spr: Sprite, legs: str = "stand", shoulder=None) -> tuple[int, int]:
    """手臂精灵左上角相对脚底中点的偏移（让肩点落在身上）"""
    sx, sy = shoulder or ((0, -15) if getattr(spr, "raised", False) else SHOULDER)
    return (sx - spr.shoulder[0], sy - spr.shoulder[1])


def pose_arm(g: Gfx, x: float, y: float, t: float, ang: float, legs: str = "stand", hand: str = "fist",
             length: int = 9, flip: bool = False, face: str = "normal", head: str = "up", behind=None,
             front=None, bob: bool = True, shoulder=None, drape: float = 1.0) -> dict:
    """小道士 + 一只任意角度的手臂。返回 {"hand": (x, y)}"""
    from ..engine.chars import figure
    spr = arm(ang, length, hand, drape)
    return figure(g, x, y, t, legs=legs, arm=spr, arm_at=arm_at(spr, legs, shoulder), face=face, head=head,
                  flip=flip, behind=behind, front=front, bob=bob)


# ---------------------------------------------------------------- 舞台与装饰

def floor(g: Gfx, y: int = FLOOR, tiles: bool = True, dots: float = 0.125):
    """地面线 + 透视地砖 + 稀网点"""
    g.d.line((0, y, 127, y), fill=1)
    if tiles:
        for x in range(-40, 168, 16):
            g.d.line((x, y + 1, x - 12, 63), fill=1)
    if dots:
        pix.checker(g, (0, y + 1, 128, 64), dots)


def badge(g: Gfx, x: int, y: int, s: str, size: int = 8, right: bool = False):
    """小框牌（计数、节次）：最后画"""
    w = text_width(s, size)
    hgt = 11 if size == 8 else 15
    if right:
        x -= w + 4
    g.d.rectangle((x, y, x + w + 4, y + hgt), outline=1, fill=0)
    g.text(x + 2, y + 2, s, size=size)


def title(g: Gfx, cx: float, y: float, s: str, t: float, t0: float, stars: bool = True, scale: int = 1):
    """圆满大字：弹出 + 黑底框 + 两侧闪星（最后画）；scale=2 放大成粗像素大字"""
    pop = ease_out_back(span(t, t0, t0 + 0.4))
    w = text_width(s) * scale
    h = 11 * scale
    yy = y + (1 - pop) * 10
    g.d.rectangle((cx - w / 2 - 4, yy - 3, cx + w / 2 + 3, yy + h + 2), fill=0)
    g.d.rectangle((cx - w / 2 - 3, yy - 2, cx + w / 2 + 2, yy + h + 1), outline=1, fill=0)
    if stars and int(t * 6) % 2 == 0:
        for sx in (cx - w / 2 - 8, cx + w / 2 + 7):
            star(g, sx, yy + h / 2, 2)
    g.text(cx, yy, s, align="center", scale=scale)


def star(g: Gfx, x: float, y: float, r: int = 1, v: int = 1):
    """十字闪星"""
    x, y = int(round(x)), int(round(y))
    g.px(x, y, v)
    for k in range(1, r + 1):
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            g.px(x + dx, y + dy, v)


def twinkles(g: Gfx, pts, t: float, period: float = 0.9):
    """一组位置轮流闪（大小 0 / 1 / 2 变化）"""
    for i, (x, y) in enumerate(pts):
        ph = (t / period + i * 0.37) % 1
        r = 2 if ph < 0.15 else 1 if ph < 0.35 else 0
        if ph < 0.6:
            star(g, x, y, r)


def ring_dots(g: Gfx, cx: float, cy: float, r: float, step: float = 2.5, rot: float = 0.0, sy: float = 1.0,
              a0: float = 0.0, a1: float = 2 * math.pi):
    """点状圆弧（光晕、声波、涟漪）"""
    n = max(4, int(abs(a1 - a0) * r / step))
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n + rot
        g.px(round(cx + math.cos(a) * r), round(cy + math.sin(a) * r * sy))


def mx_art(g: Gfx, art: str, x: int = 0, y: int = 0):
    """字符画写进点阵（'#' 亮，其他忽略）"""
    for j, ln in enumerate(art.strip("\n").split("\n")):
        for i, ch in enumerate(ln):
            if ch == "#":
                g.mx_set(x + i, y + j, True)


def mx_ring(g: Gfx, r: float, cx: float = 3.5, cy: float = 3.5, w: float = 0.6):
    for y in range(8):
        for x in range(8):
            if abs(math.hypot(x - cx, y - cy) - r) < w:
                g.mx[y, x] = True


def mx_burst(g: Gfx, t: float, t0: float, level: int = 6):
    """圆满：点阵一圈圈光环往外扩，亮度回落"""
    if t > t0:
        mx_ring(g, (t - t0) * 4)
        g.mx_level = 1 + int(level * (1 - span(t, t0, t0 + 1.4)))


def rot(pts, ang: float, ox: float = 0.0, oy: float = 0.0):
    """点绕 (ox, oy) 旋转 ang 度（顺时针为正，屏幕坐标）"""
    a = math.radians(ang)
    c, s_ = math.cos(a), math.sin(a)
    return [(ox + (x - ox) * c - (y - oy) * s_, oy + (x - ox) * s_ + (y - oy) * c) for x, y in pts]


def hold_at(g: Gfx, spr: Sprite, hand, grip, flip: bool = False, outline: bool = True):
    """把精灵贴在手上：grip = 精灵里握持点（朝右时的坐标）"""
    gx, gy = grip
    if flip:
        gx = spr.w - 1 - gx
    pix.blit(g, spr, hand[0] - gx, hand[1] - gy, flip=flip, outline=outline)


def fist(g: Gfx, x: float, y: float):
    """在道具上补画一个拳头（握住的手压在道具前面）"""
    x, y = int(round(x)), int(round(y))
    g.d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=0)
    g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
