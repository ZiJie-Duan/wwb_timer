"""x4 批（歇 · 仙踪与灵兽）共用的小工具，像素风。

    Clock            按 t 算 dt（t 回到 0 / 跳变时自动处理），给有状态的粒子用
    ev(t, period, start, dur)   周期小彩蛋：在第 n 次事件的 [0, dur) 内返回 (n, 本次已过秒数)，否则 None
    label(g, x, y, s)           先垫一块黑底再写字（字永远压在最上面、不被背景点穿）
    vlabel(g, x, y, s)          竖排版
    mx_art(g, rows)             8 行字符画（'#' 亮）→ 点阵
    sound_arcs(g, x, y, k, d)   声波弧（叫声、鸣唱）
    GRASS / TUFT / PEBBLE / FLOWER / CLOUD    背景小精灵（多帧的随风摆）
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.gfx import Gfx, text_width


class Clock:
    def __init__(self):
        self.last = None

    def dt(self, t: float) -> float:
        dt = 1 / 30 if self.last is None or t < self.last else min(t - self.last, 0.2)
        self.last = t
        return dt


def ev(t: float, period: float, start: float = 0.0, dur: float | None = None):
    """周期事件。t < start 时 None；否则第 n 次事件开始于 start + n·period，dur 内返回 (n, 已过秒数)"""
    if t < start:
        return None
    k = t - start
    n = int(k // period)
    loc = k - n * period
    if dur is not None and loc >= dur:
        return None
    return n, loc


def label(g: Gfx, x: float, y: float, s: str, size: int = 12, align: str = "left", pad: int = 2) -> int:
    """黑底 + 字（最后画）"""
    w = text_width(s, size)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    hgt = 11 if size == 12 else 7
    g.d.rectangle((int(x) - pad, int(y) - pad, int(x) + w + pad - 1, int(y) + hgt + pad - 1), fill=0)
    g.text(x, y, s, size)
    return w


def vlabel(g: Gfx, x: float, y: float, s: str, size: int = 12, pad: int = 2) -> int:
    step = (11 if size == 12 else 7) + 1
    hgt = len(s) * step - 1
    g.d.rectangle((int(x) - pad, int(y) - pad, int(x) + size + pad - 1, int(y) + hgt + pad - 1), fill=0)
    return g.vtext(x, y, s, size)


def mx_art(g: Gfx, rows: list[str], dx: int = 0, dy: int = 0):
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == "#":
                g.mx_set(x + dx, y + dy, True)


def sound_arcs(g: Gfx, x: float, y: float, k: float, d: int = -1, n: int = 3):
    """从 (x, y) 向 d 方向（-1 左 / 1 右）一圈圈发出的声波弧，k ∈ [0,1) 循环"""
    for i in range(n):
        r = 3 + ((k + i / n) % 1) * 9
        a0, a1 = (140, 220) if d < 0 else (-40, 40)
        g.d.arc((x - r, y - r, x + r, y + r), a0, a1, fill=1)


def sparkle(g: Gfx, x: float, y: float, r: int = 2):
    """十字闪光"""
    x, y = int(x), int(y)
    g.px(x, y)
    for i in range(1, r + 1):
        for dx, dy in ((i, 0), (-i, 0), (0, i), (0, -i)):
            g.px(x + dx, y + dy)


# ---------------------------------------------------------------- 背景小精灵

GRASS = pix.frames("""
 # #
 # #
## #
 ###
---
  # #
 # #
## #
 ###
---
 #  #
 # #
 ## #
 ###
""")

TUFT = pix.frames("""
   #   #
 # #  #
  ## # #
 # ## ##
  #####
---
    #  #
  # # #
  ## # #
 # ## ##
  #####
""")

PEBBLE = pix.frames("""
  ####
 #..###
#.#####
#######
""")

FLOWER = pix.frames("""
 # #
#.#.#
 ###
  #
 ##
  ##
""")

CLOUD = pix.frames("""
     ####
   ##....##   ##
 ##........###..#
#................#
 ################
---
   ###
 ##...######
#...........#
 ###########
""")


def tuft(g: Gfx, x: float, y: float, t: float, k: int = 0):
    """一丛草（底边在 y）"""
    spr = pix.anim(TUFT, t * 0.8 + k * 0.37, 1.5)
    pix.blit(g, spr, x - spr.w // 2, y - spr.h + 1)


def wobble(t: float, period: float, amp: float = 1.0, phase: float = 0.0) -> int:
    return int(round(math.sin((t / period + phase) * 2 * math.pi) * amp))
