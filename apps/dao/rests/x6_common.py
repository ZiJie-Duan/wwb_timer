"""x6 赛博歇的公用零件（像素风）：时钟、蒲团、坐着的小道士、电线、像素窗口、鼠标、进度条（本文件不登记场景）"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite

FLOOR = 58


class Clock:
    """由 t 推算帧间隔（t 回到 0 或跳变时给一个默认值），给 Puffs / Sparks 用"""

    def __init__(self):
        self.last = None

    def __call__(self, t: float) -> float:
        dt = 1 / 30 if self.last is None or t < self.last or t - self.last > 0.5 else t - self.last
        self.last = t
        return min(dt, 0.2)


def cyc(t: float, period: float, t0: float = 0.0) -> tuple[int, float]:
    """第几轮、本轮秒数"""
    n = math.floor((t - t0) / period)
    return n, (t - t0) - n * period


def crossed(t: float, dt: float, at: float, period: float | None = None, t0: float = 0.0) -> bool:
    """这一帧是否刚越过时刻 at（period 给定时按周期重复）"""
    if period:
        a = (t - t0 - at) / period
        b = (t - dt - t0 - at) / period
        return math.floor(a) != math.floor(b) and t - t0 >= at
    return t - dt < at <= t


# ---------------------------------------------------------------- 蒲团

def _cushion():
    """蒲团 30×6：扁圆，顶面一圈圈草编纹，侧面竖编纹，背光半边网点"""
    p = Part(30, 6)
    p.shape("ellipse", (0, 0, 29, 5), fill=1)
    p.d.arc((4, 0, 25, 3), 180, 360, fill=0)          # 顶面编纹（一圈）
    p.d.line((2, 3, 27, 3), fill=0)                   # 顶面与侧面的分界
    for x in range(3, 28, 3):                         # 侧面竖编纹
        p.px(x, 4, 0)
    p.dither([(18, 0), (30, 0), (30, 6), (18, 6)], 0.5, 0)
    p.px(7, 1), p.px(8, 1)                            # 高光
    return p.sprite()


_SPR: dict = {}


def spr(name: str, fn):
    """模块级缓存的精灵（只生成一次）"""
    s = _SPR.get(name)
    if s is None:
        s = _SPR[name] = fn()
    return s


def cushion(g: Gfx, cx: float, y: float = FLOOR):
    """蒲团：底边在 y"""
    pix.blit(g, spr("cushion", _cushion), cx - 15, y - 5)


def sit(g: Gfx, x: float, t: float, flip: bool = False, face: str = "sleep", dy: float = 0, head: str = "up",
        arm="gong", arm_at=None, front=None, behind=None) -> dict:
    """坐在蒲团上（蒲团另画，底边 FLOOR）：脚底基准在 FLOOR-3"""
    return figure(g, x, FLOOR - 3 + dy, t, legs="sit", arm=arm, arm_at=arm_at, head=head, face=face, flip=flip,
                  front=front, behind=behind)


def head_box(x: float, y: float, legs: str = "sit", flip: bool = False) -> tuple[int, int]:
    """figure 头像（17×17）的左上角屏幕坐标"""
    x, y = int(round(x)), int(round(y))
    top = {"sit": -34, "stand": -33, "walk": -33, "kneel": -31}[legs]
    ox = -8
    return (x + ox if not flip else x - ox - 17), y + top


def eye_open(g: Gfx, hx: int, hy: int, which: int = 1, flip: bool = False, look_up: bool = False):
    """在闭眼脸（face="sleep"）上睁开一只眼：which 0 = 前眼 1 = 后眼（朝右时 0 在左）"""
    ex = 8 + which * 4

    def P(c, r, v):
        g.px(hx + (c if not flip else 16 - c), hy + r, v)

    for c in range(ex - 1, ex + 3):
        P(c, 11, 1), P(c, 12, 1)
    for c in (ex, ex + 1):
        for r in (10, 11, 12):
            P(c, r, 0)
    P(ex, 10 if not look_up else 11, 1)


# ---------------------------------------------------------------- 线、窗口、鼠标、进度条

def cable(g: Gfx, pts, phase: float | None = None, gap: int = 6):
    """电线：两侧描黑、中间 1 像素白线；phase 给定时一段段暗缝流动（电流）"""
    g.d.line(pts, fill=0, width=3)
    g.d.line(pts, fill=1)
    if phase is not None:
        # 沿折线等距挖暗点
        acc = 0.0
        off = phase % gap
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            if L <= 0:
                continue
            s = (gap - (acc - off) % gap) % gap
            while s < L:
                k = s / L
                g.px(x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, 0)
                s += gap
            acc += L


def bezier(p0, p1, p2, k: float):
    u = 1 - k
    return (u * u * p0[0] + 2 * u * k * p1[0] + k * k * p2[0], u * u * p0[1] + 2 * u * k * p1[1] + k * k * p2[1])


def window(g: Gfx, x0: int, y0: int, x1: int, y1: int, icon: Sprite | None = None, shadow: bool = True):
    """Win98 式像素窗口：白色标题栏（左边小图标、右边三个按钮）、右下投影网点。返回客户区上边 y"""
    if shadow:
        pix.checker(g, (x0 + 2, y1 + 1, x1 + 2, y1 + 3), 0.5)
        pix.checker(g, (x1 + 1, y0 + 2, x1 + 3, y1 + 3), 0.5)
    g.d.rectangle((x0, y0, x1, y1), fill=0, outline=1)
    g.d.rectangle((x0, y0, x1, y0 + 8), fill=1)
    if icon is not None:
        pix.blit(g, icon, x0 + 2, y0 + 1, outline=False, invert=True)
    for i in range(3):  # 最小化 / 最大化 / 关闭
        bx = x1 - 7 - i * 7
        g.d.rectangle((bx, y0 + 2, bx + 5, y0 + 6), fill=0)
        if i == 0:
            g.d.line((bx + 1, y0 + 2, bx + 4, y0 + 5), fill=1)
            g.d.line((bx + 1, y0 + 5, bx + 4, y0 + 2), fill=1)
        elif i == 1:
            g.d.rectangle((bx + 1, y0 + 3, bx + 4, y0 + 5), outline=1)
        else:
            g.d.line((bx + 1, y0 + 5, bx + 4, y0 + 5), fill=1)
    return y0 + 9


def pbar(g: Gfx, x0: int, y0: int, x1: int, y1: int, p: float, block: int = 4):
    """Win98 进度条：凹框 + 一格一格的实心块"""
    p = clamp(p)
    g.d.rectangle((x0, y0, x1, y1), fill=0, outline=1)
    g.d.line((x0 + 1, y1 - 1, x1 - 1, y1 - 1), fill=0)
    inner = x1 - x0 - 3
    n = int(inner * p / block + 1e-6)
    for i in range(n):
        bx = x0 + 2 + i * block
        g.d.rectangle((bx, y0 + 2, bx + block - 2, y1 - 2), fill=1)


CURSOR = Sprite("""
#
##
#.#
#..#
#...#
#....#
#.....#
#..####
#.#
##
#
""")


def mx_icon(g: Gfx, rows: list[str], x: int = 0, y: int = 0):
    """点阵：字符画（# 亮）"""
    for r, ln in enumerate(rows):
        for c, ch in enumerate(ln):
            if ch == "#":
                g.mx_set(x + c, y + r)
