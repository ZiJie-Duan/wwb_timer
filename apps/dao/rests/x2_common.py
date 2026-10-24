"""x2 批（琴棋书画、茶与酒）共用的小工具：事件窗口、退场收拢、常用小物件。不登记场景。"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, noise, rand
from ..engine.gfx import Gfx, Sprite


def win(t: float, period: float, dur: float, offset: float = 0.0):
    """周期事件：每 period 秒（从 offset 起）发生一次、持续 dur 秒。
    → (k, n)：k = 本次事件已过的秒数（不在事件中为 None），n = 第几次（从 0 起）"""
    if t < offset:
        return None, -1
    k = (t - offset) % period
    n = int((t - offset) // period)
    return (k if k < dur else None), n


def iris(g: Gfx, p: float, cx: float = 64, cy: float = 32):
    """退场：画面向 (cx, cy) 收成一个圆后消失（p 0..1）。只做一次整屏运算"""
    if p <= 0:
        return
    import numpy as np
    r = (1 - ease_in(p)) * 80
    a = g.array()
    ys, xs = _GRID
    out = (xs - cx) ** 2 + ((ys - cy) * 1.6) ** 2 > r * r
    a[out] = False
    g.put(a)
    if 2 < r < 75:
        n = max(12, int(r * 3))
        for i in range(0, n, 2):
            ang = i / n * 2 * math.pi
            g.px(cx + math.cos(ang) * r, cy + math.sin(ang) * r / 1.6)


def _grid():
    import numpy as np
    return np.mgrid[0:64, 0:128].astype(np.float32)


_GRID = _grid()


def steam(g: Gfx, x: float, y: float, h: float, t: float, seed: int, n: int = 2, spread: float = 4.0,
          sway: float = 2.0, drift: float = 0.0):
    """茶烟/酒气：几缕细烟，断续上升；drift：被风吹向一边"""
    from ..engine.fx import smoke_wisp
    for i in range(n):
        smoke_wisp(g, x + (i - (n - 1) / 2) * spread, y, h * (0.7 + 0.3 * noise(t * 0.5 + i, seed + i)), t,
                   seed * 3 + i, sway=sway, speed=4.0, drift=(i - (n - 1) / 2) * 3 + drift)


def pine(g: Gfx, x: float, y: float, s: float = 1.0, flip: bool = False, t: float = 0.0, seed: int = 0):
    """松枝（芥子园式）：从画外 (x, y) 伸出一根虬枝，枝上几簇向上张开的扇形松针，随风轻摆"""
    d = -1 if flip else 1
    sway = (noise(t * 0.4, seed) - 0.5) * 2
    pts = [(x, y), (x + d * 9 * s, y + 4 * s), (x + d * 18 * s, y + 3 * s), (x + d * 27 * s, y + 7 * s)]
    g.d.line(pts, fill=1, width=2)
    g.d.line((pts[1][0], pts[1][1], pts[1][0] + d * 3 * s, pts[1][1] + 8 * s), fill=1)
    clumps = [(pts[1][0] + d * 3 * s, pts[1][1] + 8 * s, 0.8), (pts[2][0], pts[2][1] - 1, 1.0),
              (pts[3][0], pts[3][1] - 1, 0.9)]
    for i, (cx, cy, k) in enumerate(clumps):
        cx += sway * (i + 1) * 0.5
        r = 7 * s * k
        for j in range(9):  # 扇形针叶：向上张开
            a = math.pi * (1.05 + 0.9 * j / 8)
            g.d.line((cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7), fill=1)
        g.d.line((cx - r, cy, cx + r, cy), fill=1)


def mx_icon(g: Gfx, art: str, x: int = 0, y: int = 0):
    g.mx_blit(Sprite(art), x, y)


def lerp_pts(a, b, p):
    return [(ax + (bx - ax) * p, ay + (by - ay) * p) for (ax, ay), (bx, by) in zip(a, b)]


def jitter(i: int, seed: int, amp: float = 1.0) -> float:
    return (rand(i, seed) - 0.5) * 2 * amp


def clamp01(x):
    return clamp(x)


FIST = Sprite("""
  ..#####.....
  .#.....##...
  #.###....#..
  #.....#..#..
  #.###..#..#.
  #.....#...#.
  #.###.....#.
  #.........#.
  .#.......#..
  ..#######...
""")


def sleeve_hand(g: Gfx, fx: float, fy: float, side: int = 1):
    """道袍宽袖 + 拳（同燃香的手）：(fx, fy) 为拳心，袖子伸向右上方画外（side=-1 则伸向左上）"""
    s = side

    def P(x, y):
        return (fx + s * x, fy + y)

    wrist = [P(4, -3), P(12, -8), P(14, -2), P(6, 4)]
    g.d.polygon(wrist, fill=0, outline=1)
    sleeve = [P(10, -10), P(30, -34), P(70, -34), P(70, 2), P(22, 8), P(14, 2)]
    g.d.polygon(sleeve, fill=0)
    g.shade_poly(sleeve, 0.25)
    g.d.line(P(13, -9) + P(18, 5), fill=1)
    g.d.line(P(15, -11) + P(20, 6), fill=1)
    g.d.line(P(34, -20) + P(60, -6), fill=0)
    g.blit(FIST if s > 0 else FIST_L, fx - 6, fy - 5)


FIST_L = FIST.flip()
