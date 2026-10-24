"""通用特效：烟、火、粒子、雷电、波纹、星空、雨、云、逐字显现。

函数式的（smoke_wisp、flame、stars、rain…）只依赖时间 t，任何时刻都能直接画；
Particles 有状态，要每帧 step(dt)。
"""
from __future__ import annotations

import math
import random

from .anim import clamp, noise, rand
from .gfx import Gfx, text_width


def smoke_wisp(g: Gfx, x: float, y: float, height: float, t: float, seed: int = 0, sway: float = 4.0,
               speed: float = 6.0, fade_top: bool = True, thick: int = 1, drift: float = 0.0):
    """一缕青烟：从 (x, y) 往上 height 像素，随时间扭动上升；顶端渐散（隔点）。drift：越往上越往旁边飘"""
    prev = None
    n = int(height)
    for i in range(n):
        yy = y - i
        k = i / max(height, 1)
        ph = (i + t * speed) * 0.12
        dx = (noise(ph, seed) - 0.5) * 2 * sway * (0.3 + k) + math.sin(ph * 1.7 + seed) * sway * 0.4 * k
        xx = x + dx + drift * k * k
        if fade_top and k > 0.55 and rand(int(i + t * speed), seed) < (k - 0.55) * 2.2:
            prev = None
            continue
        if prev is not None and abs(prev - xx) > 1.2:
            g.d.line((prev, yy + 1, xx, yy), fill=1, width=thick)
        else:
            ix, iy = int(round(xx)), int(round(yy))
            g.d.rectangle((ix, iy, ix + thick - 1, iy), fill=1)
        prev = xx


def flame(g: Gfx, x: float, y: float, w: float, h: float, t: float, seed: int = 0, hollow: bool = False):
    """跳动的火苗：底部中心 (x, y)，宽 w 高 h"""
    hh = h * (0.8 + 0.35 * noise(t * 7, seed))
    lean = (noise(t * 5, seed + 9) - 0.5) * w * 0.8
    pts = []
    steps = 8
    for i in range(steps + 1):  # 右侧自下而上
        k = i / steps
        ww = w / 2 * math.sin(math.pi * (0.15 + 0.85 * (1 - k))) * (1 - k * 0.3)
        pts.append((x + ww + lean * k * k, y - hh * k))
    for i in range(steps, -1, -1):  # 左侧自上而下
        k = i / steps
        ww = w / 2 * math.sin(math.pi * (0.15 + 0.85 * (1 - k))) * (1 - k * 0.3)
        pts.append((x - ww + lean * k * k, y - hh * k))
    if hollow:
        g.d.polygon(pts, outline=1)
    else:
        g.d.polygon(pts, fill=1)
        if h >= 8:  # 内焰挖空
            g.d.ellipse((x - w * 0.15 + lean * 0.2, y - hh * 0.45, x + w * 0.15 + lean * 0.2, y - hh * 0.1), fill=0)


class Particles:
    """简单粒子：emit 后每帧 step(dt) + draw(g)"""

    def __init__(self, seed: int = 0):
        self.p: list[list[float]] = []  # x, y, vx, vy, life, age, size
        self.rng = random.Random(seed)

    def emit(self, x: float, y: float, n: int = 1, speed: float = 20, angle: float = -math.pi / 2,
             spread: float = math.pi / 3, life: float = 1.0, size: int = 1):
        for _ in range(n):
            a = angle + (self.rng.random() - 0.5) * spread
            v = speed * (0.5 + self.rng.random() * 0.7)
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v, life * (0.6 + self.rng.random() * 0.6), 0.0, size])

    def step(self, dt: float, gravity: float = 0.0, drag: float = 0.0, wind: float = 0.0):
        keep = []
        for q in self.p:
            q[5] += dt
            if q[5] >= q[4]:
                continue
            q[2] += wind * dt
            q[3] += gravity * dt
            if drag:
                f = max(0.0, 1 - drag * dt)
                q[2] *= f
                q[3] *= f
            q[0] += q[2] * dt
            q[1] += q[3] * dt
            keep.append(q)
        self.p = keep

    def draw(self, g: Gfx, flicker: bool = True):
        for q in self.p:
            k = q[5] / q[4]
            if flicker and k > 0.6 and self.rng.random() < (k - 0.6) * 2:
                continue
            s = int(q[6])
            if s <= 1:
                g.px(q[0], q[1])
            else:
                g.d.rectangle((q[0], q[1], q[0] + s - 1, q[1] + s - 1), fill=1)

    def __len__(self):
        return len(self.p)


def lightning(g: Gfx, x0: float, y0: float, x1: float, y1: float, seed: int, jag: float = 6.0,
              branches: int = 2, width: int = 1):
    """一道闪电：折线从 (x0,y0) 到 (x1,y1)，带分叉。同一 seed 形状相同，换 seed 就是新的一道"""
    rng = random.Random(seed)

    def bolt(ax, ay, bx, by, depth):
        n = max(3, int(math.hypot(bx - ax, by - ay) / 6))
        pts = [(ax, ay)]
        for i in range(1, n):
            k = i / n
            pts.append((ax + (bx - ax) * k + (rng.random() - 0.5) * jag * 2, ay + (by - ay) * k + (rng.random() - 0.5) * jag))
        pts.append((bx, by))
        g.d.line(pts, fill=1, width=width)
        if depth > 0:
            for _ in range(branches):
                i = rng.randrange(1, len(pts) - 1)
                px, py = pts[i]
                ang = math.atan2(by - ay, bx - ax) + (rng.random() - 0.5) * 1.6
                ln = math.hypot(bx - ax, by - ay) * 0.35
                bolt(px, py, px + math.cos(ang) * ln, py + math.sin(ang) * ln, depth - 1)

    bolt(x0, y0, x1, y1, 1 if branches else 0)


def ring(g: Gfx, cx: float, cy: float, r: float, density: int = 2, phase: float = 0.0):
    """点状圆环（density=1 实线，2 隔一点，3 隔两点）"""
    if r <= 0:
        return
    n = max(8, int(2 * math.pi * r))
    for i in range(n):
        if i % density:
            continue
        a = i / n * 2 * math.pi + phase
        g.px(round(cx + math.cos(a) * r), round(cy + math.sin(a) * r))


def stars(g: Gfx, t: float, seed: int = 0, n: int = 30, box=(0, 0, 128, 64), twinkle: float = 0.25):
    """固定位置、随机闪烁的星星"""
    x0, y0, x1, y1 = box
    for i in range(n):
        x = x0 + int(rand(i, seed) * (x1 - x0))
        y = y0 + int(rand(i + 999, seed) * (y1 - y0))
        if noise(t * 2 + i * 3.7, seed + i) > twinkle:
            g.px(x, y)
            if rand(i + 77, seed) < 0.08 and noise(t * 3 + i, seed) > 0.8:  # 偶尔一颗亮星闪出十字
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    g.px(x + dx, y + dy)


def rain(g: Gfx, t: float, seed: int = 0, n: int = 40, speed: float = 90, length: int = 4, slant: float = 0.3,
         box=(0, 0, 128, 64)):
    x0, y0, x1, y1 = box
    hgt = y1 - y0
    for i in range(n):
        x = x0 + rand(i, seed) * (x1 - x0)
        y = (rand(i + 500, seed) * hgt + t * speed * (0.7 + 0.6 * rand(i + 9, seed))) % (hgt + length) + y0 - length
        xx = x + (y - y0) * slant
        g.d.line((xx, y, xx + length * slant, y + length), fill=1)


def cloud(g: Gfx, cx: float, cy: float, w: float, h: float, seed: int = 0, fill: int = 0, outline: int = 1):
    """一朵祥云/云团：几个椭圆叠成，fill=0 时内部挖空只留轮廓"""
    rng = random.Random(seed)
    blobs = []
    n = 4
    for i in range(n):
        k = (i + 0.5) / n
        bw = w * (0.35 + rng.random() * 0.2)
        bh = h * (0.6 + rng.random() * 0.4) * math.sin(math.pi * (0.2 + 0.6 * k)) + h * 0.2
        bx = cx - w / 2 + k * w
        blobs.append((bx - bw / 2, cy - bh / 2, bx + bw / 2, cy + bh / 2))
    blobs.append((cx - w / 2, cy - h * 0.15, cx + w / 2, cy + h / 2))
    for b in blobs:
        g.d.ellipse(b, fill=1)
    if not fill:
        for b in blobs:
            g.d.ellipse((b[0] + 1, b[1] + 1, b[2] - 1, b[3] - 1), fill=0)


def xiangyun(g: Gfx, x: float, y: float, s: float = 1.0, flip: bool = False):
    """祥云纹（卷云）：一个回卷的螺旋 + 尾巴"""
    pts = []
    turns = 1.6
    for i in range(40):
        k = i / 39
        a = k * turns * 2 * math.pi
        r = (1 - k) * 5 * s + 0.5
        pts.append((x + (math.cos(a) * r) * (-1 if flip else 1), y + math.sin(a) * r))
    g.d.line(pts, fill=1)
    tail = 10 * s
    g.d.line((x + (-5 * s if not flip else 5 * s), y, x + (-5 * s - tail if not flip else 5 * s + tail), y + 2 * s),
             fill=1)


def typewriter(g: Gfx, x: float, y: float, s: str, t: float, cps: float = 8.0, size: int = 12, align: str = "left",
               cursor: bool = False) -> bool:
    """逐字显现；返回是否已显示完"""
    n = int(clamp(t * cps / max(len(s), 1)) * len(s))
    shown = s[:n]
    if align != "left":
        full = text_width(s, size)
        x = x - full / 2 if align == "center" else x - full
    g.text(x, y, shown, size)
    if cursor and n < len(s) and int(t * 4) % 2 == 0:
        cx = x + text_width(shown, size)
        g.d.rectangle((cx + 1, y + size - 3, cx + 4, y + size - 2), fill=1)
    return n >= len(s)


_GLYPHS: dict = {}


def _glyph(ch: str, size: int, scale: int):
    """单字的字形遮罩（PIL '1'），缓存"""
    from PIL import Image, ImageDraw
    from .gfx import _FONT_FILES, font
    key = (ch, size, scale)
    img = _GLYPHS.get(key)
    if img is None:
        off = _FONT_FILES[size][1]
        w = max(1, text_width(ch, size))
        hh = _FONT_FILES[size][2] + 2
        img = Image.new("1", (w, hh))
        d = ImageDraw.Draw(img)
        d.fontmode = "1"
        d.text((0, -off), ch, font=font(size), fill=1)
        if scale > 1:
            img = img.resize((w * scale, hh * scale), Image.NEAREST)
        _GLYPHS[key] = img
    return img


def brush_reveal(g: Gfx, x: float, y: float, s: str, p: float, size: int = 12, scale: int = 1, vertical: bool = False):
    """毛笔书写：每个字从上到下“写”出来，笔尖跟着走。p 0..1 为整串的进度"""
    from .gfx import _FONT_FILES
    n = len(s)
    if n == 0:
        return
    g.texts.append((s, size))
    ch_h = (_FONT_FILES[size][2] + 1) * scale
    per = 1 / n
    cx, cy = int(round(x)), int(round(y))
    for i, ch in enumerate(s):
        k = clamp((p - i * per) / per)
        if k <= 0:
            break
        glyph = _glyph(ch, size, scale)
        cw = glyph.width
        bb = glyph.getbbox()
        if bb and k >= 1:  # 写完的字登记范围（文字堆叠检查；正在写的字有笔尖，不登记）
            g.text_boxes.append((ch, cx + bb[0], cy + bb[1], cx + bb[2], cy + bb[3], cx, cy, size, scale))
        if k >= 1:
            g.img.paste(1, (cx, cy), glyph)
        else:
            cut = max(1, int(glyph.height * k))
            g.img.paste(1, (cx, cy), glyph.crop((0, 0, cw, cut)))
            tip = cx + cw * (0.3 + 0.4 * noise(p * 40, i))
            g.d.rectangle((tip, cy + cut - 2, tip + 1, cy + cut - 1), fill=1)
        if vertical:
            cy += ch_h
        else:
            cx += cw + scale
