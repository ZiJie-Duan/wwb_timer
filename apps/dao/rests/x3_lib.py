"""x3 山水与天象：本批共用的小工具（不登记场景）。

山的画法：远山 = 稀疏抖动、无轮廓；中山 = 中等抖动 + 山脊线；近山 = 黑底亮轮廓（剪影）。
山脚用“雾”：抖动浓度随离山脊的距离递减，像水墨的山腰云气。所有山层都在 setup 里预先做成 Sprite，
每帧只贴图（不做整屏 numpy），树莓派上也够快。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine.anim import clamp, noise, rand
from ..engine.gfx import BAYER4, Gfx, Sprite, text_width


def bayer(h: int, w: int) -> np.ndarray:
    return np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]


def peaks(n: int, base: float, tops, seed: int = 0, rough: float = 1.5, power: float = 1.25) -> list[float]:
    """山脊轮廓：tops = [(cx, top_y, half_width), ...]，返回每个 x 的山脊 y（越小越高）"""
    ys = []
    for x in range(n):
        y = base
        for cx, top, hw in tops:
            d = abs(x - cx) / hw
            y = min(y, top + (base - top) * d ** power)
        y += (noise(x * 0.35, seed) - 0.5) * 2 * rough + (noise(x * 0.11, seed + 7) - 0.5) * rough
        ys.append(min(y, base))
    return ys


def layer(heights, level: float, h: int = 64, outline: int = 1, fog: float = 0.0, floor: float = 0.0,
          solid: bool = False) -> Sprite:
    """山层 Sprite（宽 = len(heights)，高 h）。
    level：山脊下的抖动浓度；fog > 0：往下 fog 像素内浓度降到 floor（山腰云雾）；
    outline：山脊线（1 实线，2 隔点，0 无）；solid：山体不透明（盖住后面的东西）"""
    w = len(heights)
    ys = np.arange(h)[:, None].astype(np.float32)
    top = np.array(heights, dtype=np.float32)[None, :]
    inside = ys >= np.round(top)
    depth = ys - top
    if fog > 0:
        lv = level + (floor - level) * np.clip(depth / fog, 0, 1)
    else:
        lv = np.full_like(depth, level)
    on = inside & (bayer(h, w) < np.round(lv * 16))
    if outline:
        for x in range(w):
            y0 = int(round(heights[x]))
            yn = int(round(heights[x + 1])) if x + 1 < w else y0
            if outline == 2 and x % 2:
                continue
            for y in range(min(y0, yn), max(y0, yn) + 1) if outline == 1 else (y0,):
                if 0 <= y < h and (y == y0 or y < yn):
                    on[y, x] = True
    mask = inside.copy() if solid else on.copy()
    return Sprite(on=on, mask=mask)


def wrap_blit(g: Gfx, spr: Sprite, x: float, y: float):
    """横向循环贴图（云、星空等平移的层）"""
    x = int(round(x)) % spr.w
    g.blit(spr, x, y)
    if x > 0:
        g.blit(spr, x - spr.w, y)


_TEXT: dict = {}


def text_spr(s: str, size: int = 12, vertical: bool = False) -> tuple[Sprite, int, int]:
    """把一串字渲染成透明底的 Sprite 并缓存（PIL 每帧画字很慢，约 0.1ms/字）。返回 (sprite, dx, dy)"""
    key = (s, size, vertical)
    if key not in _TEXT:
        tmp = Gfx()
        if vertical:
            tmp.vtext(0, 0, s, size)
        else:
            tmp.text(0, 0, s, size)
        a = tmp.array()
        ys, xs = np.nonzero(a)
        if len(xs) == 0:
            _TEXT[key] = (Sprite(on=np.zeros((1, 1), bool), mask=np.zeros((1, 1), bool)), 0, 0)
        else:
            a = a[: ys.max() + 1, : xs.max() + 1]
            _TEXT[key] = (Sprite(on=a.copy(), mask=a.copy()), 0, 0)
    return _TEXT[key]


def ctext(g: Gfx, x: float, y: float, s: str, size: int = 12, align: str = "left", vertical: bool = False,
          fill: int = 1):
    """同 g.text / g.vtext，但用缓存的位图（快）。fill=0 画暗字"""
    if not s:
        return
    g.texts.append((s, size))  # 让 check 照样能查缺字
    spr, _, _ = text_spr(s, size, vertical)
    if align == "center":
        x -= text_width(s, size) / 2
    elif align == "right":
        x -= text_width(s, size)
    g.blit(spr, x, y, invert=not fill)


def vpoem(g: Gfx, x: float, y: float, s: str, k: float = 1.0, size: int = 12):
    """竖排题诗，k 0..1 为显示到第几个字（逐字缓存，逐字出现时不会每次重新渲染）"""
    n = int(round(clamp(k) * len(s)))
    step = size  # 与 g.vtext 相同：字高 + 1
    for i, ch in enumerate(s[:n]):
        ctext(g, x + (size - text_width(ch, size)) / 2, y + i * step, ch, size)


def ptext(g: Gfx, x: float, y: float, s: str, n: int | None = None, size: int = 12):
    """横排，只画前 n 个字（逐字缓存）"""
    n = len(s) if n is None else n
    for i, ch in enumerate(s[:n]):
        ctext(g, x + text_width(s[:i], size), y, ch, size)


def poem_cols(g: Gfx, x_right: float, y: float, cols, k: float = 1.0, gap: int = 2):
    """多列竖排（自右向左，像题画诗），k 为整体进度"""
    total = sum(len(c) for c in cols)
    left = int(round(clamp(k) * total))
    x = x_right - 12
    for c in cols:
        vpoem(g, x, y, c[:max(0, left)], 1.0)
        left -= len(c)
        x -= 12 + gap


def seal(g: Gfx, x: float, y: float, ch: str = "观"):
    """一方小印：亮底暗字（8px 字）"""
    g.d.rectangle((x, y, x + 9, y + 9), fill=1)
    ctext(g, x + 1, y + 2, ch, size=8, fill=0)


def every(t: float, period: float, dur: float, offset: float = 0.0):
    """按 t 定时的小事件：返回 (第几次, 事件内经过秒数) 或 None"""
    if t < offset:
        return None
    k = int((t - offset) // period)
    lt = (t - offset) - k * period
    return (k, lt) if lt < dur else None


def bird(g: Gfx, x: float, y: float, t: float, s: float = 1.0, flap: float = 6.0):
    """远处的飞鸟（一笔“人”字），翅膀扇动"""
    up = math.sin(t * flap) * 1.5 * s
    g.d.line((x - 3 * s, y - up, x, y), fill=1)
    g.d.line((x, y, x + 3 * s, y - up), fill=1)


def fog_dots(g: Gfx, x0: float, y0: float, x1: float, y1: float, t: float, seed: int, n: int = 20,
             drift: float = 2.0):
    """缓慢飘动的雾点（水汽、山岚）"""
    w, h = x1 - x0, y1 - y0
    for i in range(n):
        x = x0 + (rand(i, seed) * w + t * drift * (0.5 + rand(i + 50, seed))) % w
        y = y0 + rand(i + 100, seed) * h + math.sin(t * 0.7 + i) * 1.5
        if noise(t * 0.8 + i * 2.3, seed + i) > 0.35:
            g.px(x, y)


def text_box_w(s: str, size: int = 12) -> int:
    return text_width(s, size)


class Cloud:
    """一朵水墨云（留白）：几个椭圆叠成，外轮廓是预先算好的折线，内部挖空（盖住后面的山）。
    draw(…, a)：a < 1 时轮廓断成虚线、慢慢散掉"""

    def __init__(self, rng, w: float = 20, h: float = 9, lumps: int = 4):
        self.blobs = []
        for i in range(lumps):  # 上面一排圆鼓包（中间高、两边低）
            k = (i + 0.5) / lumps
            r = h * (0.38 + rng.random() * 0.22) * (0.65 + 0.5 * math.sin(math.pi * k))
            self.blobs.append(((k - 0.5) * w * 0.78 + rng.uniform(-1, 1), -r * 0.35 - h * 0.05, r * 1.15, r))
        self.blobs.append((0.0, h * 0.22, w * 0.5, h * 0.2))  # 平底
        self.runs = []
        for bi, (bx, by, rx, ry) in enumerate(self.blobs):
            n = max(16, int(2 * math.pi * max(rx, ry) * 0.9))
            run = []
            for j in range(n + 1):
                a = j / n * 2 * math.pi
                px, py = bx + math.cos(a) * rx, by + math.sin(a) * ry
                hidden = any(((px - cx) / max(qx - 0.6, 0.5)) ** 2 + ((py - cy) / max(qy - 0.6, 0.5)) ** 2 < 1
                             for k2, (cx, cy, qx, qy) in enumerate(self.blobs) if k2 != bi)
                if hidden:
                    if len(run) > 1:
                        self.runs.append(run)
                    run = []
                else:
                    run.append((px, py))
            if len(run) > 1:
                self.runs.append(run)
        # 鼓包里的卷纹（水墨云的勾线）：最大的两个鼓包里各一道小弧
        big = sorted(range(lumps), key=lambda i: -self.blobs[i][3])[:2]
        self.curls = [(self.blobs[i][0] + self.blobs[i][2] * 0.15, self.blobs[i][1] + self.blobs[i][3] * 0.25,
                       self.blobs[i][3] * 0.5) for i in big]

    def draw(self, g: Gfx, cx: float, cy: float, s: float = 1.0, a: float = 1.0, seed: int = 0,
             clear: bool = True):
        if a <= 0:
            return
        if clear:
            for bx, by, rx, ry in self.blobs:
                g.d.ellipse((cx + (bx - rx) * s, cy + (by - ry) * s, cx + (bx + rx) * s, cy + (by + ry) * s), fill=0)
        for ri, run in enumerate(self.runs):
            pts = [(cx + x * s, cy + y * s) for x, y in run]
            if a >= 1:
                g.d.line(pts, fill=1)
            else:
                for j in range(0, len(pts) - 1, 2):
                    if rand(ri * 97 + j, seed) < a:
                        g.d.line(pts[j:j + 3], fill=1)
        if a > 0.5 and s >= 0.6:
            for x, y, r in self.curls:
                r *= s
                g.d.arc((cx + x * s - r, cy + y * s - r, cx + x * s + r, cy + y * s + r), 200, 340, fill=1)


def halo(spr: Sprite) -> Sprite:
    """给像素画加 1 像素暗边（在抖动的山前也看得清）；返回的 Sprite 四周各大 1 像素，贴图时 x、y 各减 1"""
    on = np.pad(spr.on, 1)
    m = np.pad(spr.mask, 1)
    d = m.copy()
    d[1:, :] |= m[:-1, :]
    d[:-1, :] |= m[1:, :]
    d[:, 1:] |= m[:, :-1]
    d[:, :-1] |= m[:, 1:]
    return Sprite(on=on, mask=d)


def poly_sprite(polys, level: float, outline: int = 1, solid: bool = True, w: int = 128, h: int = 64,
                fog_y: float | None = None, fog: float = 0.0, floor: float = 0.0, strokes=()) -> Sprite:
    """多边形（山崖、礁石）做成 Sprite：内部抖动 level，可往下 fog 像素渐淡；strokes = 皴线 [(x0,y0,x1,y1)…]"""
    from PIL import Image, ImageDraw
    m = Image.new("1", (w, h))
    md = ImageDraw.Draw(m)
    for pts in polys:
        md.polygon(pts, fill=1)
    inside = np.array(m, dtype=bool)
    lv = np.full((h, w), level, dtype=np.float32)
    if fog_y is not None and fog > 0:
        ys = np.arange(h, dtype=np.float32)[:, None]
        lv = level + (floor - level) * np.clip((ys - fog_y) / fog, 0, 1) * np.ones((1, w), np.float32)
    on = inside & (bayer(h, w) < np.round(lv * 16))
    o = Image.new("1", (w, h))
    od = ImageDraw.Draw(o)
    if outline:
        for pts in polys:
            od.polygon(pts, outline=1)
    for s in strokes:
        od.line(s, fill=1)
    on |= np.array(o, dtype=bool)
    mask = (inside | on) if solid else on
    return Sprite(on=on, mask=mask)


def pine_pad(g: Gfx, x: float, y: float, w: float, sway: float = 0.0, dense: int = 2):
    """松针一簇（国画里平顶的“松盖”）：上沿一道弧，下面垂一排短针。(x, y) 为簇中心"""
    hw = w / 2
    g.d.chord((x - hw + sway, y - 3, x + hw + sway, y + 3), 180, 360, fill=0, outline=1)
    for i in range(int(w // dense) + 1):
        xx = x - hw + 1 + i * dense + sway
        if xx > x + hw - 1 + sway:
            break
        k = abs(xx - x - sway) / hw
        ln = 2 + (1 - k) * 2
        g.d.line((xx, y - 1 - (1 - k) * 1.5, xx - 0.5 + sway * 0.3, y - 1 + ln), fill=1)
