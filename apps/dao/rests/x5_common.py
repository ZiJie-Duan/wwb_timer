"""x5 道观日常（像素风）共用零件：会干活的小道士、旋转道具、确定性事件、竖写题字。

worker()：在 engine.chars.figure 上拼出干活的小道士——手臂按“肩 → 手”的屏幕角度现场取精灵（宽袖下垂、
袖口镶边、背光网点、露手），可以一只手或两只手（后手画在身后），道具画在身前 / 身后；
behind_head=True 时举过头顶的手臂和道具画在头后面，只从头顶露出拳头和道具。
rotate() / blit_rot()：把“柄朝右画”的道具精灵（斧、锄、瓮）绕握点转到任意角度。
所有精灵按角度 / 长度量化后只生成一次（pix 的描边、翻转缓存按对象 id 存，不要每帧新建精灵）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, rand
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite

# ---------------------------------------------------------------- 手臂

_ARMS: dict = {}


def limb(ang: float, ln: int) -> tuple[Sprite, int]:
    """宽袖手臂：从肩 (R, R) 朝屏幕角 ang（度，0 = 右，90 = 下）伸出 ln 像素到手。返回 (精灵, R)；spr.hand 为手"""
    a = int(round(ang / 10.0)) * 10 % 360
    ln = int(clamp(round(ln), 5, 24))
    key = (a, ln)
    v = _ARMS.get(key)
    if v is None:
        R = ln + 5
        p = Part(2 * R + 1, 2 * R + 1)
        r = math.radians(a)
        ux, uy = math.cos(r), math.sin(r)
        nx, ny = -uy, ux                       # 法向；朝下的一侧是袖子下垂的一侧
        if ny < 0 or (abs(ny) < 1e-6 and nx < 0):
            nx, ny = -nx, -ny
        sx, sy = R, R
        cl = ln - 2                                          # 袖口离肩
        wx, wy = sx + ux * cl, sy + uy * cl
        hx, hy = sx + ux * ln, sy + uy * ln                  # 手
        P = lambda x, y: (int(round(x)), int(round(y)))  # noqa: E731
        # 手（先画，袖口压在手腕上）
        p.shape("line", (P(wx, wy), P(hx, hy)), fill=1, width=2)
        ix, iy = P(hx, hy)
        p.shape("rectangle", (ix - 1, iy - 1, ix + 1, iy), fill=1)
        # 袖筒：肩处 3 像素，往袖口渐宽
        droop = 1.5 + 2.0 * abs(ux)                          # 手臂越平，宽袖垂得越多
        tube = [P(sx - nx * 1.2, sy - ny * 1.2), P(wx - nx * 1.6, wy - ny * 1.6),
                P(wx + nx * 1.6, wy + ny * 1.6), P(sx + nx * 1.4, sy + ny * 1.4)]
        p.shape("polygon", tube, fill=1)
        flap = [P(wx - ux * 4 + nx * 1.4, wy - uy * 4 + ny * 1.4), P(wx + nx * 1.6, wy + ny * 1.6),
                P(wx - ux * 0.5 + nx * (1.6 + droop), wy - uy * 0.5 + ny * (1.6 + droop) + droop * 0.6)]
        p.shape("polygon", flap, fill=1)                     # 垂下来的袖口
        p.shape("ellipse", (sx - 2, sy - 2, sx + 1, sy + 1), fill=1)  # 肩头
        p.dither(flap, 0.5, 0)                               # 袖里背光
        # 袖口镶边：一道暗线
        cx, cy = wx - ux * 1, wy - uy * 1
        p.d.line((P(cx - nx * 1, cy - ny * 1), P(cx + nx * 1, cy + ny * 1)), fill=0)
        spr = p.sprite()
        spr.hand = (ix, iy)
        v = _ARMS[key] = (spr, R)
    return v


SHOULDER = {"stand": (1, -15), "walk": (1, -15), "kneel": (3, -12), "sit": (1, -18)}
BACK_SH = {"stand": (-2, -15), "walk": (-2, -15), "kneel": (0, -12), "sit": (-2, -18)}


def shoulder(x: float, floor: float, t: float, legs: str = "stand", flip: bool = False, back: bool = False,
             bob: bool = True, dy: int = 0) -> tuple[int, int]:
    """肩在屏幕上的位置（跟 figure 的呼吸、走路起伏一致）"""
    sx, sy = (BACK_SH if back else SHOULDER)[legs]
    lift = 1 if bob and legs == "stand" and (t * 0.7) % 1 > 0.5 else 0
    bounce = (int(t * 8) % 4) % 2 if legs == "walk" else 0
    x, floor = int(round(x)), int(round(floor)) + dy
    return (x - sx if flip else x + sx), floor + sy + lift - bounce


def arm_spr(sh, hand, ln: int | None = None, maxl: int = 16):
    """从肩 sh 朝 hand 的手臂精灵：→ (精灵, 左上 x, y, 实际手的位置)"""
    dx, dy = hand[0] - sh[0], hand[1] - sh[1]
    d = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx)) if d > 0.5 else 90
    L = ln if ln is not None else int(clamp(round(d), 6, maxl))
    spr, R = limb(ang, L)
    x0, y0 = sh[0] - R, sh[1] - R
    return spr, x0, y0, (x0 + spr.hand[0], y0 + spr.hand[1])


def arm_to(g: Gfx, sh, hand, ln: int | None = None) -> tuple[int, int]:
    """从肩 sh 朝 hand 画一只手臂（长度默认 = 距离，夹在 6–13）。返回实际手的位置"""
    spr, x0, y0, h = arm_spr(sh, hand, ln)
    pix.blit(g, spr, x0, y0)
    return h


FIST = Sprite("""
###
#.#
###
""")


def worker(g: Gfx, x: float, floor: float, t: float, hand=None, hand2=None, legs: str = "stand",
           head: str = "up", face: str = "normal", flip: bool = False, tool=None, back_tool=None,
           bob: bool = True, dy: int = 0, ln: int | None = None, ln2: int | None = None, fist: bool = False,
           front=None, behind_head: bool = False) -> dict:
    """干活的小道士。hand = 前手的目标（屏幕坐标），hand2 = 后手的目标（画在身后，常用于双手握柄）；
    None 时前手自然下垂。behind_head：前手和道具也画在身体后面（举过头顶时只从头顶露出手和道具）。tool(g, h1, h2)：道具，画在身体前、前手下面；back_tool：画在身体后面。
    返回 {"hand": 前手, "hand2": 后手, "sh": 前肩}"""
    out = {}
    sh1 = shoulder(x, floor, t, legs, flip, False, bob, dy)
    sh2 = shoulder(x, floor, t, legs, flip, True, bob, dy)
    mx = 23 if behind_head else 16
    a1 = arm_spr(sh1, hand, ln, mx) if hand is not None else None
    a2 = arm_spr(sh2, hand2, ln2, mx) if hand2 is not None else None
    if a1:
        out["hand"] = a1[3]
    if a2:
        out["hand2"] = a2[3]

    def _arm1(gg):
        if tool:
            tool(gg, out.get("hand"), out.get("hand2"))
        if a1:
            pix.blit(gg, a1[0], a1[1], a1[2])
            if fist:
                pix.blit(gg, FIST, a1[3][0] - 1, a1[3][1] - 1)

    def _behind(gg, at):
        if a2:
            pix.blit(gg, a2[0], a2[1], a2[2])
        if back_tool:
            back_tool(gg, out.get("hand"), out.get("hand2"))
        if behind_head:
            _arm1(gg)

    def _front(gg, at):
        if not behind_head:
            _arm1(gg)
        if front:
            front(gg, at)

    r = figure(g, x, floor, t, legs=legs, arm=("down" if hand is None else None), head=head, face=face,
               flip=flip, bob=bob, dy=dy, behind=_behind, front=_front)
    if hand is None:
        out["hand"] = r.get("hand")
    out["sh"] = sh1
    return out


# ---------------------------------------------------------------- 旋转道具

_ROT: dict = {}


def rotate(spr: Sprite, deg: float, px: float, py: float, step: int = 10) -> tuple[Sprite, int, int]:
    """把一个“柄朝右画”的道具精灵绕 (px, py)（握点）转到屏幕角 deg（0 = 右，90 = 下）。
    最近邻反向映射，按 step 度缓存。返回 (精灵, 握点在新精灵里的 x, y)"""
    import numpy as np
    d = int(round(deg / step)) * step % 360
    key = (id(spr), d, px, py)
    v = _ROT.get(key)
    if v is None:
        r = math.radians(d)
        c, s_ = math.cos(r), math.sin(r)
        R = int(math.ceil(max(math.hypot(x - px, y - py) for x in (0, spr.w) for y in (0, spr.h)))) + 1
        n = 2 * R + 1
        ys, xs = np.mgrid[0:n, 0:n]
        dx, dy = xs - R, ys - R
        sx = np.rint(dx * c + dy * s_ + px).astype(int)       # 反向旋转回原图
        sy = np.rint(-dx * s_ + dy * c + py).astype(int)
        ok = (sx >= 0) & (sx < spr.w) & (sy >= 0) & (sy < spr.h)
        on = np.zeros((n, n), bool)
        mk = np.zeros((n, n), bool)
        on[ok] = spr.on[sy[ok], sx[ok]]
        mk[ok] = spr.mask[sy[ok], sx[ok]]
        v = _ROT[key] = (Sprite(on=on, mask=mk), R, R)
    return v


def blit_rot(g: Gfx, spr: Sprite, x: float, y: float, deg: float, px: float, py: float, outline: bool = True):
    """把道具的握点 (px, py) 放在屏幕 (x, y)，转到 deg"""
    r, ox, oy = rotate(spr, deg, px, py)
    pix.blit(g, r, x - ox, y - oy, outline=outline)


def tip(x: float, y: float, deg: float, along: float, side: float = 0.0):
    """道具上的一点：从握点沿柄 along、沿法向（柄朝右时的“下方”）side"""
    r = math.radians(deg)
    return x + math.cos(r) * along - math.sin(r) * side, y + math.sin(r) * along + math.cos(r) * side


# ---------------------------------------------------------------- 时间

def keys(t: float, ks, ease=None):
    """关键帧插值：ks = [(时刻, 值), ...]（值为数或元组），段内用 ease（默认 ease_in_out）"""
    from ..engine.anim import ease_in_out
    ease = ease or ease_in_out
    if t <= ks[0][0]:
        return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t < t1:
            k = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            if isinstance(v0, tuple):
                return tuple(a + (b - a) * k for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * k
    return ks[-1][1]


def arc_pt(p0, p1, k: float, h: float):
    """抛物线：从 p0 到 p1，顶点高出 h"""
    return (p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k - 4 * h * k * (1 - k))


class Clock:
    """有状态粒子用的 dt（t 回跳或大跳时重置）与“跨过某时刻”判定"""
    _last = None

    def tick(self, t: float) -> float:
        last = self._last
        self._last = t
        if last is None or t < last or t - last > 0.5:
            self._prev = None
            return 1 / 30
        self._prev = last
        return t - last

    def crossed(self, t: float, at: float) -> bool:
        """本帧（上一帧 t → 这一帧 t）跨过了 at"""
        p = getattr(self, "_prev", None)
        return p is not None and p < at <= t


def cyc(t: float, period: float) -> tuple[int, float]:
    n = int(t // period)
    return n, t - n * period


def event(t: float, period: float, dur: float, seed: int, skip: float = 0.0):
    """约每 period 秒一次、持续 dur 秒的小事件（确定性）。返回 (第几次, 事件内秒数) 或 None"""
    n, k = cyc(t, period)
    if rand(n, seed) < skip:
        return None
    start = 4 + rand(n, seed + 7) * max(period - dur - 8, 0)
    if start <= k < start + dur:
        return n, k - start
    return None


# ---------------------------------------------------------------- 小精灵

SWEAT = pix.frames("""
 #
###
###
 #
""")[0]

BANG = Sprite("""
.#.
.#.
.#.
...
.#.
""")

NOTE = Sprite("""
 .##
 .#.#
 .#
##.
##
""")

STARS = pix.frames("""
#   .
   ###
     .
---
  #
 ###   #
  #
""")


def mark(g: Gfx, spr: Sprite, x: float, y: float):
    """头上的小标记（感叹号、音符）：描黑边"""
    pix.blit(g, spr, x, y)


# ---------------------------------------------------------------- 题字

def scroll(g: Gfx, x: int, s: str, y: int = 3, k: float = 1.0, side: str = "left"):
    """竖写题字（每帧最后画）：先压一条黑底，再写字；k 0..1 = 已经写出来的比例（逐字出现）。
    x = 字列左边；side = 字列在屏幕哪一边（另一边画一道点线和画面隔开）"""
    n = len(s)
    shown = int(n * clamp(k) + 0.999)
    if shown <= 0:
        return
    hgt = n * 12 - 1
    g.d.rectangle((x - 2, y - 2, x + 13, y + hgt + 2), fill=0)
    edge = x + 14 if side == "left" else x - 3
    for yy in range(y - 1, y + hgt + 2, 2):  # 一道点线，把字列和画面分开
        g.px(edge, yy)
    g.vtext(x, y, s[:shown])


def fade_out(g: Gfx, k: float):
    """退场：有序网点淡出（k 0→1 由亮到暗）"""
    if k > 0:
        g.fade(1 - clamp(k))


__all__ = ["rotate", "blit_rot", "tip", "limb", "shoulder", "arm_to", "arm_spr", "keys", "arc_pt", "worker", "Clock",
           "cyc", "event", "SWEAT", "BANG", "NOTE", "STARS", "mark", "scroll", "fade_out", "FIST"]
