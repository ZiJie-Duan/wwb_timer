"""x3 山水与天象：本批共用的像素工具（不登记场景）。

画风：清晰的 1 位像素画。远近层次全靠“规则网点 + 轮廓”：
    远山 = 一道山脊线 + 12.5% 网点；中山 = 山脊线 + 25% 网点、受光坡一条 50% 亮带；
    近景 = 黑色剪影 + 白色轮廓 + 裂纹 / 苔点（不透明，盖住后面）。
山层、礁石、松树、云朵都在模块级 / setup 里一次做成 Sprite，每帧只贴图。
所有 hold 只依赖 t（没有逐帧状态），任何时刻都能直接画；小事件用 every(t, 周期, 时长, 偏移) 排定。
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine import pix
from ..engine.anim import clamp, noise, rand
from ..engine.chars import Part
from ..engine.gfx import BAYER4, Gfx, Sprite, text_width

W, H = 128, 64


# ---------------------------------------------------------------- 时间

def every(t: float, period: float, dur: float, offset: float = 0.0):
    """按 t 定时的小事件：返回 (第几次, 事件内经过秒数) 或 None"""
    if t < offset:
        return None
    k = int((t - offset) // period)
    lt = (t - offset) - k * period
    return (k, lt) if lt < dur else None


def tri(p: float) -> float:
    """0→1→0 的三角波（p 0..1）"""
    p = clamp(p)
    return 1 - abs(2 * p - 1)


# ---------------------------------------------------------------- 网点

_PAT: dict = {}


def pattern(level: float, h: int = H, w: int = W) -> np.ndarray:
    """与屏幕对齐的规则网点（0.125 / 0.25 / 0.5 / 0.75）"""
    key = (level, h, w)
    if key not in _PAT:
        p = pix.PATTERNS[min(pix.PATTERNS, key=lambda k: abs(k - level))]
        ph, pw = p.shape
        _PAT[key] = np.tile(p, (h // ph + 1, w // pw + 1))[:h, :w]
    return _PAT[key]


def bayer_keep(h: int, w: int, k: float) -> np.ndarray:
    """有序抖动的保留掩码（k 比例的像素为 True）：精灵逐渐散开用"""
    b = np.tile(BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]
    return b < int(round(clamp(k) * 16))


# ---------------------------------------------------------------- 山

def ridge(tops, seed: int = 0, base: float = 64, rough: float = 1.0, n: int = W, power: float = 1.2,
          round_top: bool = False):
    """山脊：tops = [(cx, 顶 y, 半宽), ...]，返回每个 x 的山脊 y。round_top：圆顶陡坡（国画的峰）"""
    ys = []
    for x in range(n):
        y = base
        for cx, top, hw in tops:
            d = abs(x - cx) / hw
            if round_top:
                y = min(y, top + (base - top) * (1 - math.cos(min(d, 1.6) * math.pi / 2)) ** power)
            else:
                y = min(y, top + (base - top) * d ** power)
        y += (noise(x * 0.4, seed) - 0.5) * 2 * rough + (noise(x * 0.13, seed + 7) - 0.5) * rough
        ys.append(min(y, base))
    return ys


def mountain(heights, lit=((0.5, 2), (0.25, 2)), shade=((0.125, 2),), body: float = 0.0, outline: int = 1,
             solid: bool = True, cap: tuple | None = None, cracks: int = 0, veins: int = 0, seed: int = 0,
             h: int = H) -> Sprite:
    """一层山（宽 = len(heights)），像素画的“网点阶梯”画法：
    lit：受光坡（往右升高的坡）山脊下的网点带 [(浓度, 宽), ...]，由浓到淡；shade：背光坡的网点带；
    body：山体其余部分的网点（0 = 黑）；outline：1 实线山脊 / 2 隔点山脊 / 0 无；
    cap=(y 线, 深度)：高于 y 线的山顶积雪（实白，下沿参差）；cracks：近景裂纹条数；veins：从山顶往下的沟壑线条数"""
    w = len(heights)
    hh = np.round(np.array(heights)).astype(int)
    ys = np.arange(h)[:, None]
    inside = ys >= hh[None, :]
    on = np.zeros((h, w), bool)
    if body > 0:
        on |= inside & pattern(body, h, w)
    slope = np.zeros(w)
    slope[:-1] = hh[1:] - hh[:-1]
    slope[-1] = slope[-2] if w > 1 else 0
    # 坡向平滑一下，避免一格一格跳
    sm = np.convolve(slope, np.ones(5) / 5, mode="same")
    for x in range(w):
        bands = lit if sm[x] < -0.05 else shade
        y = max(hh[x], 0)
        for lv, bw in bands:
            y1 = min(h, y + bw)
            if y < h and lv > 0:
                on[y:y1, x] |= pattern(lv, h, w)[y:y1, x]
            y = y1
    if cap is not None:
        cy, depth = cap
        for x in range(w):
            if hh[x] < cy:
                d = int(depth + (cy - hh[x]) * 0.6) + (1 if rand(x, seed + 5) < 0.4 else 0)
                on[max(hh[x], 0):min(h, hh[x] + d), x] = True
                if hh[x] + d + 1 < h and rand(x, seed + 9) < 0.35:
                    on[hh[x] + d + 1, x] = True
    im = Image.fromarray(on)
    d = ImageDraw.Draw(im)
    if veins:
        peaks_x = [x for x in range(2, w - 2) if hh[x] <= hh[x - 1] and hh[x] <= hh[x + 1] and hh[x] < hh.max() - 4]
        peaks_x = sorted(peaks_x, key=lambda x: hh[x])[:veins]
        for i, px_ in enumerate(peaks_x):
            for s in (-1, 1):
                x, y = px_ + s * 2, hh[px_] + 3
                pts = [(x, y)]
                for j in range(3):
                    x += s * (2 + int(rand(i * 9 + j, seed) * 3))
                    y += 3 + int(rand(i * 9 + j + 50, seed) * 3)
                    pts.append((x, y))
                d.line(pts, fill=1)
    if cracks:
        for i in range(cracks):
            x = int(rand(i, seed) * (w - 6)) + 3
            y = hh[x] + 4 + int(rand(i + 40, seed) * 10)
            ln = 2 + int(rand(i + 80, seed) * 4)
            dx = 1 if rand(i + 120, seed) < 0.5 else -1
            if y + ln < h:
                d.line([(x, y), (x + dx, y + ln // 2), (x, y + ln)], fill=1)
    on = np.array(im, bool) & inside
    if outline:
        for x in range(w):
            if outline == 2 and x % 2:
                continue
            y0 = hh[x]
            yn = hh[x + 1] if x + 1 < w else y0
            yp = hh[x - 1] if x > 0 else y0
            lo = max(y0, yn - 1, yp - 1) if outline == 1 else y0
            for y in range(y0, lo + 1):
                if 0 <= y < h:
                    on[y, x] = True
    mask = inside.copy() if solid else on.copy()
    return Sprite(on=on, mask=mask)


def bake(fn, w: int = W, h: int = H, solid=None) -> Sprite:
    """用一张临时画布画东西（fn(g)），做成 Sprite。solid(d)：在掩码图上画出不透明范围（剪影）"""
    g = Gfx()
    g.clear()
    fn(g)
    on = np.array(g.img, bool)[:h, :w]
    m = Image.new("1", (W, H))
    if solid:
        solid(ImageDraw.Draw(m))
    mask = on | np.array(m, bool)[:h, :w]
    return Sprite(on=on, mask=mask)


# ---------------------------------------------------------------- 云

def _erode(m: np.ndarray) -> np.ndarray:
    e = m.copy()
    e[1:, :] &= m[:-1, :]
    e[:-1, :] &= m[1:, :]
    e[:, 1:] &= m[:, :-1]
    e[:, :-1] &= m[:, 1:]
    return e


def cloud(w: int, h: int, seed: int = 0, lumps: int | None = None, flat: bool = True) -> Sprite:
    """像素云朵：上沿一排圆鼓包、平底；白轮廓、黑心（盖住后面的山），鼓包里一道卷纹高光，底部一条网点"""
    rng = np.random.default_rng(seed)
    n = lumps or max(2, w // 7)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    m = np.zeros((h, w), bool)
    curls = []
    for i in range(n):
        k = (i + 0.5) / n
        r = (h * 0.42) * (0.75 + 0.45 * math.sin(math.pi * k)) * (0.85 + 0.3 * rng.random())
        cx = 1 + r + k * (w - 2 - 2 * r) if n > 1 else w / 2
        cy = h - 1 - r * (0.9 if flat else 1.0) - (h * 0.12) * math.sin(math.pi * k)
        cy = max(cy, r)
        m |= (xs - cx) ** 2 + (ys - cy) ** 2 <= r * r
        curls.append((cx, cy, r))
    if flat:
        bottom = int(h * 0.55)
        m[bottom:, int(w * 0.12):int(w * 0.88) + 1] = True
        m[h - 1:, :] &= np.arange(w)[None, :] > 2
        m[h - 1:, :] &= np.arange(w)[None, :] < w - 3
    edge = m & ~_erode(m)
    on = edge.copy()
    im = Image.fromarray(on)
    d = ImageDraw.Draw(im)
    for cx, cy, r in sorted(curls, key=lambda c: -c[2])[:2]:
        if r >= 3:
            rr = r - 2
            d.arc((cx - rr, cy - rr, cx + rr, cy + rr), 200, 280, fill=1)
    on = np.array(im, bool) & m
    inner = _erode(_erode(m))
    under = inner & (ys >= h - 3) & ((xs + ys) % 2 == 0)
    on |= under
    return Sprite(on=on, mask=m)


_FADED: dict = {}


def faded(spr: Sprite, k: float) -> Sprite:
    """精灵逐渐散开：只留 k 比例的亮点，黑心变透明（云散、雾散）。按 1/8 档缓存"""
    q = int(round(clamp(k) * 8))
    key = (id(spr), q)
    s = _FADED.get(key)
    if s is None:
        keep = bayer_keep(spr.h, spr.w, q / 8)
        on = spr.on & keep
        mask = on | (spr.mask & bayer_keep(spr.h, spr.w, max(0, q - 4) / 4))
        s = _FADED[key] = Sprite(on=on, mask=mask)
    return s


# ---------------------------------------------------------------- 水

def glints(g: Gfx, x0: float, x1: float, y0: float, y1: float, t: float, seed: int = 0, n: int = 24,
           speed: float = 3.0, far: int = 1, near: int = 6, blink: float = 0.4, rows: int = 2):
    """水面的碎光：近大远小的横线，缓缓漂动、一闪一闪（逐帧水波）"""
    w = x1 - x0
    for i in range(n):
        k = rand(i, seed)
        y = int(y0 + (k ** 1.3) * (y1 - y0))
        y -= (y - int(y0)) % rows
        kk = (y - y0) / max(y1 - y0, 1)
        ln = int(round(far + (near - far) * kk))
        x = x0 + (rand(i + 99, seed) * w + t * speed * (0.4 + kk)) % w
        if noise(t * 1.3 + i * 3.7, seed + i) > blink:
            g.d.line((x, y, min(x + ln, x1), y), fill=1)


def ring(g: Gfx, x: float, y: float, k: float, rmax: float = 6.0, flat: float = 0.35):
    """落水的一圈涟漪（k 0..1）：从小圈荡开，后半段变成隔点"""
    if not 0 <= k < 1:
        return
    r = 1 + k * rmax
    ry = max(1, r * flat)
    if k < 0.55:
        g.d.ellipse((x - r, y - ry, x + r, y + ry), outline=1)
    else:
        for a in range(0, 360, 30):
            if (a // 30) % 2 == 0:
                g.px(x + math.cos(math.radians(a)) * r, y + math.sin(math.radians(a)) * ry)


SPLASH = pix.frames("""
 #   #
  # #
---
#     #
 #   #
   #
---
#       #
  #   #

---
#         #


""")


def splash(g: Gfx, x: float, y: float, k: float):
    """水花（k 0..1）：一个 V 字溅起再散开"""
    if 0 <= k < 1:
        f = SPLASH[min(int(k * len(SPLASH)), len(SPLASH) - 1)]
        g.blit(f, x - f.w // 2, y - f.h)


def drops(g: Gfx, box, t: float, seed: int = 0, n: int = 30, speed: float = 70.0, length: int = 3,
          slant: float = 0.25):
    """斜雨丝：box 内的 n 道短线，按 t 往下落（无状态）"""
    x0, y0, x1, y1 = box
    hh = y1 - y0 + length * 2
    for i in range(n):
        sp = speed * (0.8 + 0.4 * rand(i, seed))
        y = y0 - length + (rand(i + 50, seed) * hh + t * sp) % hh
        x = x0 + (rand(i + 100, seed) * (x1 - x0) + (y - y0) * slant) % (x1 - x0)
        g.d.line((x, y, x - slant * length, y - length), fill=1)


# ---------------------------------------------------------------- 鸟与星

BIRD = pix.frames("""
#     #
 ## ##
   #
---

 #####
#  #  #
---

#######
   #
""")


def bird(g: Gfx, x: float, y: float, t: float, fps: float = 8.0, flip: bool = False, ph: float = 0.0):
    f = BIRD[[0, 1, 2, 1][int(t * fps + ph * 4) % 4]]
    pix.blit(g, f, x - 3, y - 1, flip=flip)


def star(g: Gfx, x: int, y: int, t: float, i: int, seed: int = 0):
    """星：多数是一个点，偶尔亮成小十字"""
    v = noise(t * 0.9 + i * 1.7, seed + i)
    if v < 0.2:
        return
    g.px(x, y)
    if v > 0.82:
        g.px(x - 1, y), g.px(x + 1, y), g.px(x, y - 1), g.px(x, y + 1)


# ---------------------------------------------------------------- 文字

def plate(g: Gfx, x: float, y: float, s: str, size: int = 12, align: str = "left", frame: bool = True):
    """文字（最后画）：先压一块黑底（带一圈细框），字放上面，保证干净"""
    w = text_width(s, size)
    hgt = 11 if size == 12 else 7
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    x, y = int(round(x)), int(round(y))
    g.d.rectangle((x - 3, y - 3, x + w + 2, y + hgt + 2), fill=0)
    if frame:
        g.d.rectangle((x - 3, y - 3, x + w + 2, y + hgt + 2), outline=1)
        for cx, cy in ((x - 3, y - 3), (x + w + 2, y - 3), (x - 3, y + hgt + 2), (x + w + 2, y + hgt + 2)):
            g.px(cx, cy, 0)
    g.text(x, y, s, size)


def vplate(g: Gfx, x: float, y: float, s: str, size: int = 12, frame: bool = True, n: int | None = None):
    """竖排题字（最后画），n：只显示前 n 个字"""
    step = (11 if size == 12 else 7) + 1
    n = len(s) if n is None else n
    hgt = len(s) * step - 1
    x, y = int(round(x)), int(round(y))
    g.d.rectangle((x - 3, y - 3, x + size + 2, y + hgt + 2), fill=0)
    if frame:
        g.d.rectangle((x - 3, y - 3, x + size + 2, y + hgt + 2), outline=1)
        for cx, cy in ((x - 3, y - 3), (x + size + 2, y - 3), (x - 3, y + hgt + 2), (x + size + 2, y + hgt + 2)):
            g.px(cx, cy, 0)
    for i, ch in enumerate(s[:n]):
        cw = text_width(ch, size)
        g.text(x + (size - cw) / 2, y + i * step, ch, size)


def plate_k(t: float, period: float, dur: float, offset: float = 0.0) -> float:
    """题字何时出现：返回 0..1 的显示进度（逐字），没有就 0"""
    ev = every(t, period, dur, offset)
    if not ev:
        return 0.0
    lt = ev[1]
    if lt > dur - 0.8:
        return -1.0  # 正在收：调用方可直接不画
    return clamp(lt / 1.6)


# ---------------------------------------------------------------- 道具

def rock(w: int, h: int, seed: int = 0, moss: bool = True) -> Sprite:
    """一块山石：黑心白轮廓，顶面一道受光边，右侧网点背光，几道裂纹、苔点"""
    rng = np.random.default_rng(seed)
    p = Part(w, h)
    pts = [(0, h - 1), (1, h // 2), (w * 0.2, 2 + rng.integers(0, 2)), (w * 0.45, 0), (w * 0.7, 1 + rng.integers(0, 2)),
           (w - 2, h * 0.4), (w - 1, h - 1)]
    p.shape("polygon", pts, fill=0)
    p.d.polygon(pts, outline=1)
    p.d.line((w * 0.2 + 1, 3, w * 0.45, 1, w * 0.68, 2), fill=1)  # 顶面受光
    p.dither([(w * 0.62, 3), (w - 2, h * 0.42), (w - 2, h - 2), (w * 0.7, h - 2)], 0.5, 1)
    for i in range(max(1, w // 8)):
        x = int(w * (0.15 + 0.6 * rng.random()))
        y = int(h * (0.35 + 0.3 * rng.random()))
        p.d.line((x, y, x + 1, y + 2, x, y + 4), fill=1)
    if moss:
        for i in range(max(2, w // 5)):
            x = int(1 + rng.random() * (w - 3))
            p.px(x, 1 if 0.2 * w < x < 0.7 * w else int(h * 0.35), 1)
    return p.sprite()


def pine_pad(w: int, seed: int = 0, snow: bool = False) -> Sprite:
    """一簇松针（像素）：扁平的一团，上沿锯齿（针尖），里面 50% 网点是针叶，底边一道实线、下面垂几根短针；
    snow：上沿压一层实白的雪"""
    h = max(4, min(7, w // 3 + 1))
    p = Part(w, h + 2)
    c = (w - 1) / 2
    for x in range(w):
        k = abs(x - c) / (c + 0.5)
        top = int(round((h - 1) * (1 - math.sqrt(max(0.0, 1 - k * k))) * 0.9)) + (x + seed) % 2
        top = min(top, h - 2)
        p.shape("line", (x, top, x, h - 1), fill=0)
        p.px(x, top, 1)
        for y in range(top + 1, h - 1):
            if (x + y) % 2 == 0:
                p.px(x, y, 1)
        if snow and top + 1 < h - 1:
            p.px(x, top + 1, 1)
    p.d.line((1, h - 1, w - 2, h - 1), fill=1)
    for x in range(1 + seed % 2, w - 1, 3):
        p.px(x, h, 1)
    return p.sprite()


def hat() -> Sprite:
    """斗笠 21×7：尖顶、宽檐、篾纹"""
    p = Part(21, 7)
    pts = [(10, 0), (20, 5), (19, 6), (1, 6), (0, 5)]
    p.shape("polygon", pts, fill=1)
    p.d.line((1, 5, 19, 5), fill=0)
    for x in (4, 8, 12, 16):
        p.d.line((10, 1, x, 4), fill=0)
    p.px(10, 0, 1)
    p.dither([(12, 1), (20, 5), (12, 5)], 0.5, 0)
    return p.sprite()


def ribbon(g: Gfx, x: float, y: float, t: float, wind: float, flip: bool = False):
    """发带：从发髻后飘出的两条短带，wind 0..1 越大越平、摆得越快"""
    s = -1 if not flip else 1
    for j, ln in enumerate((7, 6)):
        pts = []
        for i in range(ln + 1):
            k = i / ln
            dx = s * i * (0.6 + 0.4 * wind)
            dy = i * (1 - wind) * 0.9 + math.sin(t * (3 + 9 * wind) - i * 0.9 + j) * k * (0.6 + 1.2 * wind) + j
            pts.append((x + dx, y + dy))
        g.d.line(pts, fill=1)
