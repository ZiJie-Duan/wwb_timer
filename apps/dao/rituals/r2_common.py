"""r2 批（符箓·咒语·法印）共用的小零件：字形缓存与逐笔显现、符纸、毛笔、剑指手、点阵小图。

不登记场景，只被 r2_*.py 导入。
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine.anim import clamp, noise, rand
from ..engine.gfx import Gfx, Sprite, _FONT_FILES, font

_glyphs: dict[tuple, Sprite] = {}


def glyph(s: str, size: int = 12, scale: int = 1, invert: bool = False) -> Sprite:
    """把一串字渲染成 Sprite（缓存）。高 = 字高（12px 为 11），亮笔画 '#'，其余透明"""
    key = (s, size, scale, invert)
    if key not in _glyphs:
        f = font(size)
        off, hh = _FONT_FILES[size][1], _FONT_FILES[size][2]
        w = max(1, int(f.getlength(s)))
        im = Image.new("1", (w, hh))
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((0, -off), s, font=f, fill=1)
        on = np.array(im, dtype=bool)
        if scale > 1:
            on = on.repeat(scale, 0).repeat(scale, 1)
        if invert:
            _glyphs[key] = Sprite(on=on, mask=np.ones_like(on))
        else:
            _glyphs[key] = Sprite(on=on, mask=on.copy())
    return _glyphs[key]


_cuts: dict[tuple, Sprite] = {}


def glyph_reveal(g: Gfx, x: float, y: float, s: str, k: float, size: int = 12, scale: int = 1,
                 fill: int = 1) -> tuple[float, float]:
    """自上而下“写”出字（k 0..1），返回笔尖位置（扫描线上、笔画所在处）"""
    spr = glyph(s, size, scale)
    k = clamp(k)
    if k <= 0:
        return x + spr.w / 2, y
    rows = max(1, int(round(spr.h * k)))
    if rows >= spr.h:
        g.blit(spr, x, y, invert=not fill)
        return x + spr.w / 2, y + spr.h
    key = (s, size, scale, rows)
    part = _cuts.get(key)
    if part is None:
        part = Sprite(on=spr.on[:rows].copy(), mask=spr.mask[:rows].copy())
        if len(_cuts) > 400:
            _cuts.clear()
        _cuts[key] = part
    g.blit(part, x, y, invert=not fill)
    row = spr.on[rows - 1]
    xs = np.nonzero(row)[0]
    if len(xs):
        tip_x = x + xs[int(len(xs) * noise(k * 9, len(s))) % len(xs)]
    else:
        tip_x = x + spr.w / 2
    return tip_x, y + rows


def polyline_part(pts, p: float):
    """折线的前 p（0..1）部分；返回（点列，末端点）"""
    if p <= 0 or len(pts) < 2:
        return [pts[0]], pts[0]
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    total = sum(seg)
    want = total * clamp(p)
    out = [pts[0]]
    acc = 0.0
    for i, s in enumerate(seg):
        if acc + s >= want:
            k = (want - acc) / s if s else 0
            end = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k)
            out.append(end)
            return out, end
        acc += s
        out.append(pts[i + 1])
    return out, pts[-1]


def poly_len(pts) -> float:
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def spiral(cx: float, cy: float, r: float, turns: float = 2.2, n: int = 28, start: float = 0.0):
    """由外向内的螺旋（符胆常见画法）"""
    pts = []
    for i in range(n + 1):
        k = i / n
        a = start + k * turns * 2 * math.pi
        rr = r * (1 - k * 0.85)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts


def paper(g: Gfx, x0: float, y0: float, x1: float, y1: float, edge: bool = True, tone: bool = False):
    """黄符纸：黑底亮边，内侧一圈细点纹（纸的毛边）；tone：纸面再铺一层很淡的点（纸色）"""
    g.d.rectangle((x0, y0, x1, y1), fill=0, outline=1)
    if tone and x1 - x0 > 6 and y1 - y0 > 6:  # 纸面纤维：固定位置的稀疏短点
        w, h = x1 - x0 - 4, y1 - y0 - 4
        for i in range(int(w * h / 60)):
            g.px(x0 + 2 + rand(i, 71) * w, y0 + 2 + rand(i, 72) * h)
    if edge and x1 - x0 > 8 and y1 - y0 > 8:
        for yy in range(int(y0) + 2, int(y1) - 1, 2):
            g.px(x0 + 1, yy)
            g.px(x1 - 1, yy + 1)


def brush(g: Gfx, x: float, y: float, ang: float = -0.5, ln: float = 30, ink: bool = True):
    """毛笔：笔尖在 (x, y)；ang = 笔杆方向（弧度，从笔尖指向笔杆末端，-pi/2 为正上）"""
    ux, uy = math.cos(ang), math.sin(ang)
    tx, ty = -uy, ux
    # 笔头（狼毫）：笔尖到 7 像素处渐宽
    tuft = [(x, y), (x + ux * 7 + tx * 2.2, y + uy * 7 + ty * 2.2), (x + ux * 8, y + uy * 8),
            (x + ux * 7 - tx * 2.2, y + uy * 7 - ty * 2.2)]
    g.d.polygon(tuft, fill=1 if ink else 0, outline=1)
    # 笔杆（双线）+ 笔帽环
    bx, by = x + ux * 8, y + uy * 8
    ex, ey = x + ux * ln, y + uy * ln
    g.d.line((bx + tx, by + ty, ex + tx, ey + ty), fill=1)
    g.d.line((bx - tx, by - ty, ex - tx, ey - ty), fill=1)
    g.d.line((bx + tx * 1.5, by + ty * 1.5, bx - tx * 1.5, by - ty * 1.5), fill=1)
    g.d.line((ex + tx, ey + ty, ex - tx, ey - ty), fill=1)
    # 挂绳圈
    g.d.ellipse((ex + ux * 2 - 1.5, ey + uy * 2 - 1.5, ex + ux * 2 + 1.5, ey + uy * 2 + 1.5), outline=1)


# 剑指（食指中指并拢伸直，其余握起）：指尖朝上，(0,0) 为指尖
JIANZHI = Sprite("""
  .##.
  #..#
  #..#
  #..#
  #..#
  #..#.
  #..##.
  #...##.
  #.....#
  #.##..#
  #.....#
  #.##..#
  .#....#
  .#...#.
  .#####.
""")


# 剑指（横向，指尖朝左）：(0, 3) 附近为指尖
JIANZHI_L = Sprite("""
        .#######.
   .#####.......#.
  #.............#.
  .#####........#.
  #.............#.
   .#####.......#.
        #.###...#.
        #.......#.
         #######.
""")


def point_hand(g: Gfx, x: float, y: float, shade: float = 0.25):
    """剑指从右边伸来：指尖在 (x, y)，袖子往右下出画"""
    hx, hy = x, y - 3
    wx, wy = hx + 15, hy + 4
    pts = [(wx - 1, wy - 5), (wx + 30, wy - 11), (wx + 46, wy + 18), (wx - 1, wy + 7)]
    g.d.polygon(pts, fill=0)
    g.shade_poly(pts, shade)
    g.d.line((wx, wy - 5, wx + 3, wy + 7), fill=1)
    g.d.line((wx + 2, wy - 6, wx + 5, wy + 7), fill=1)
    g.blit(JIANZHI_L, hx, hy)


def sleeve(g: Gfx, x: float, y: float, w: float = 14, h: float = 30, dirx: float = 1.0, shade: float = 0.25):
    """从手腕 (x, y) 往下的宽袖：dirx=1 往右下展开，-1 往左下"""
    pts = [(x - 3 * dirx, y), (x + 5 * dirx, y), (x + (w + 6) * dirx, y + h), (x - 8 * dirx, y + h)]
    g.d.polygon(pts, fill=0)
    g.shade_poly(pts, shade)
    g.d.line((x - 3 * dirx, y + 2, x + 6 * dirx, y + 2), fill=1)


def mx_fu(g: Gfx, rows: float = 8.0, blink_row: int | None = None):
    """点阵上的一张小符：纸边两列 + 符文逐行写出（rows 0..8）"""
    pat = ["..####..", ".#.##.#.", "..####..", ".##..##.", "..#..#..", "...##...", "..#.##..", ".##..#.."]
    n = int(rows)
    for y in range(8):
        g.mx[y, 0] = g.mx[y, 7] = True
        if y < n:
            for x in range(8):
                if pat[y][x] == "#":
                    g.mx[y, x] = True
    if blink_row is not None and 0 <= blink_row < 8:
        g.mx[blink_row, 3] = g.mx[blink_row, 4] = True


def rays(g: Gfx, cx: float, cy: float, r0: float, r1: float, n: int = 12, phase: float = 0.0, sy: float = 1.0,
         dash: int = 0):
    """放射光线（sy 压扁），dash>0 时隔段画"""
    for i in range(n):
        a = phase + i / n * 2 * math.pi
        ca, sa = math.cos(a), math.sin(a) * sy
        if dash:
            k = r0
            while k < r1:
                k2 = min(k + dash, r1)
                g.d.line((cx + ca * k, cy + sa * k, cx + ca * k2, cy + sa * k2), fill=1)
                k += dash * 2
        else:
            g.d.line((cx + ca * r0, cy + sa * r0, cx + ca * r1, cy + sa * r1), fill=1)


def arm(g: Gfx, x: float, y: float, ang: float, length: float = 60, w0: float = 5, w1: float = 15,
        shade: float = 0.25):
    """宽袖手臂：手腕在 (x, y)，往 ang 方向（弧度，指向画外）伸展、越往外袖口越宽；袖口一道镶边"""
    ux, uy = math.cos(ang), math.sin(ang)
    tx, ty = -uy, ux
    cx, cy = x + ux * 4, y + uy * 4           # 袖口
    ex, ey = x + ux * length, y + uy * length
    pts = [(cx + tx * w0 * 1.6, cy + ty * w0 * 1.6), (ex + tx * w1, ey + ty * w1), (ex - tx * w1, ey - ty * w1),
           (cx - tx * w0 * 1.6, cy - ty * w0 * 1.6)]
    g.d.polygon([(x + tx * w0, y + ty * w0), (cx + tx * w0, cy + ty * w0), (cx - tx * w0, cy - ty * w0),
                 (x - tx * w0, y - ty * w0)], fill=0, outline=1)  # 手腕
    g.d.polygon(pts, fill=0)
    g.shade_poly(pts, shade)
    k = 3
    g.d.line((cx + tx * w0 * 1.6, cy + ty * w0 * 1.6, cx - tx * w0 * 1.6, cy - ty * w0 * 1.6), fill=1)
    g.d.line((cx + ux * k + tx * w0 * 1.8, cy + uy * k + ty * w0 * 1.8, cx + ux * k - tx * w0 * 1.8,
              cy + uy * k - ty * w0 * 1.8), fill=1)
    # 衣褶
    g.d.line((cx + ux * 12 + tx * 2, cy + uy * 12 + ty * 2, cx + ux * 30 + tx * 5, cy + uy * 30 + ty * 5), fill=0)
