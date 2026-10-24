"""骨架：有立体感的手（手掌 + 五指各三节 + 拇指 + 道袍宽袖），画在灰度层上。

    hand(g, wx, wy, ang, s=1.0, curl=0.0, thumb=0.0, spread=0.0, sleeve=1.0, side=1)

    (wx, wy)  手腕位置；ang 手指方向（弧度，0 朝右、π/2 朝下）
    s         大小（1 ≈ 手长 20 像素）
    curl      四指弯曲：0 张开、1 握拳；也可以是 4 个值的列表（食、中、无名、小指）分别弯
    thumb     拇指：0 张开、1 扣在食指上
    spread    手指张开的角度
    side      手心朝哪边：1 = 方向的右手侧（屈指向这边），-1 反过来（左右手 / 翻面）
    sleeve    袖子长度系数（0 不画）；sleeve_ang 袖子方向（默认与手指相反）

返回各指尖坐标 {"index": (x,y), …, "palm": (x,y)}，方便手里拿东西（香、笔、剑、铃）。
"""
from __future__ import annotations

import math

from . import art
from .gfx import Gfx

# 手指：名、在掌缘上的位置（0 拇指侧 … 1 小指侧）、三节长度、粗细
FINGERS = [
    ("index", 0.13, (4.0, 2.7, 2.2), 1.3),
    ("middle", 0.38, (4.4, 3.0, 2.4), 1.38),
    ("ring", 0.63, (4.1, 2.8, 2.2), 1.3),
    ("little", 0.87, (3.2, 2.2, 1.9), 1.12),
]
BEND = (1.25, 1.55, 1.05)  # 握拳时三个关节各弯多少（弧度）


def _rot(x, y, a):
    c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c


def sleeve_shape(g: Gfx, wx, wy, back, s, length=1.0, flare=1.0, tone=0.3, trim=True, sway: float = 0.0):
    """道袍宽袖：挂在小臂下、受重力下垂的一兜布。back = 小臂方向（从手腕指向手肘，弧度）。
    上沿贴着小臂，下摆垂成弧；竖向垂褶的亮棱、下摆与袖口的镶边。sway：下摆摆动（-1..1）"""
    if length <= 0:
        return
    ux, uy = math.cos(back), math.sin(back)
    L = 20 * s * length
    w0 = 3.4 * s
    drop = 7 * s * flare
    top, hem = [], []
    for k in range(9):
        q = k / 8
        ax, ay = wx + ux * L * q, wy + uy * L * q          # 小臂上的点
        top.append((ax, ay - w0 * 0.6))
        d = w0 + drop * math.sin(math.pi * min(q * 1.25, 1)) ** 0.8
        hem.append((ax + sway * 3 * s * q, ay + d))
    pts = top + hem[::-1]
    art.poly(g, pts, grad=(tone * 1.3, tone * 0.35, math.pi / 2))
    # 垂褶：从小臂往下摆的亮棱
    for q, v in ((0.22, 0.75), (0.45, 0.6), (0.7, 0.5)):
        i = int(q * 8)
        (x0, y0), (x1, y1) = top[i], hem[i]
        art.line(g, x0, y0 + 1.5 * s, x1 - 1.5 * s, y1 - 1, 0.8, tone * 2.4 * v, 0.9)
    if trim:
        art.line(g, *hem[0], *hem[1], 1.0, 0.9)
        for i in range(1, 8):
            art.line(g, *hem[i], *hem[i + 1], 1.0, 0.85)
        art.line(g, top[0][0], top[0][1], hem[0][0], hem[0][1], 1.2, 1.0)  # 袖口


def hand(g: Gfx, wx: float, wy: float, ang: float, s: float = 1.0, curl=0.0, thumb: float = 0.0,
         spread: float = 0.0, side: int = 1, sleeve: float = 1.0, sleeve_ang: float | None = None,
         skin: float = 1.0, sleeve_tone: float = 0.22, flare: float = 1.0, under=None, outline: bool = True):
    """under(g)：在手指之下、手掌之上画的东西（手里握的香、笔杆，被手指盖住）"""
    import numpy as np
    curls = list(curl) if isinstance(curl, (list, tuple)) else [curl] * 4
    sa = ang + math.pi if sleeve_ang is None else sleeve_ang
    sleeve_shape(g, wx, wy, sa, s, sleeve, flare, sleeve_tone)
    # 手画在单独的一层上，合上去时描一圈暗边，和袖子、背景分开
    hg = Gfx()
    hl = hg.L()
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy * side, dx * side          # 手心一侧（屈指方向）
    plen, pw = 8.0 * s, 4.4 * s
    kx, ky = wx + dx * plen, wy + dy * plen  # 指根中心
    lit = (px * art.LIGHT[0] + py * art.LIGHT[1]) < 0  # 手背一侧受光
    # 手掌：扁平的掌面，横向渐变表现厚度；掌根圆
    palm = [(wx - px * pw * 0.8, wy - py * pw * 0.8), (wx + px * pw * 0.7, wy + py * pw * 0.7),
            (kx + px * pw * 1.0 + dx * s, ky + py * pw * 1.0 + dy * s),
            (kx - px * pw * 1.0 + dx * s, ky - py * pw * 1.0 + dy * s)]
    ga = math.atan2(-py, -px) if lit else math.atan2(py, px)
    art.poly(hg, palm, grad=(skin, skin * 0.45, ga))
    art.disc(hg, wx, wy, pw * 0.5, v=skin * 0.7)
    tips = {}
    bases = []
    for name, pos, segs, thick in FINGERS:
        o = (pos - 0.5) * 2 * pw * 0.92
        bases.append((kx - px * o, ky - py * o))
    for i in range(4):  # 指节：掌缘上一排小圆凸
        art.disc(hg, bases[i][0] - dx * 0.6 * s, bases[i][1] - dy * 0.6 * s, FINGERS[i][3] * s * 1.05,
                 v=skin * 0.95, alpha=0.9)
    if under:
        under(hg)
    order = sorted(range(4), key=lambda i: -FINGERS[i][1]) if side > 0 else range(4)
    for i in order:
        name, pos, segs, thick = FINGERS[i]
        c = max(0.0, min(1.0, curls[i]))
        a = ang + (pos - 0.5) * spread * side * -1
        x, y = bases[i]
        for j, ln in enumerate(segs):
            a += BEND[j] * c * side
            nx_, ny_ = x + math.cos(a) * ln * s, y + math.sin(a) * ln * s
            r = (thick - j * 0.14) * s
            art.capsule(hg, x, y, nx_, ny_, r, r * 0.9, base=skin * (0.85 + 0.06 * (3 - i) / 3), amb=0.1,
                        spec=0.35, edge=0.5)
            x, y = nx_, ny_
        tips[name] = (x, y)
        if c < 0.55:  # 指甲
            art.disc(hg, x - math.cos(a) * 0.9 * s, y - math.sin(a) * 0.9 * s, 0.75 * s, v=1.0, alpha=0.7)
    tb = (wx - px * pw * 0.6 + dx * 2.0 * s, wy - py * pw * 0.6 + dy * 2.0 * s)
    ta = ang - (0.8 - 1.5 * thumb) * side
    x, y = tb
    for j, ln in enumerate((3.8, 3.1)):
        nx_, ny_ = x + math.cos(ta) * ln * s, y + math.sin(ta) * ln * s
        r = (1.6 - j * 0.22) * s
        art.capsule(hg, x, y, nx_, ny_, r, r * 0.9, base=skin, amb=0.12, spec=0.35, edge=0.5)
        x, y = nx_, ny_
        ta += (0.35 + 0.6 * thumb) * side
    tips["thumb"] = (x, y)
    tips["palm"] = ((wx + kx) / 2 + px * pw * 0.3, (wy + ky) / 2 + py * pw * 0.3)
    tips["knuckle"] = (kx, ky)
    cov = hl > 0.004
    L = g.L()
    np.copyto(L, hl, where=cov)
    if outline:
        grown = cov | np.roll(cov, 1, 0) | np.roll(cov, -1, 0) | np.roll(cov, 1, 1) | np.roll(cov, -1, 1)
        L[grown & ~cov] = 0.0
    return tips
