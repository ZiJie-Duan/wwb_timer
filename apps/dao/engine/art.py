"""灰度美术工具：都画在 g.lum（0 黑 … 1 白）上，最后由引擎抖动成黑白点。

明暗、材质、立体感都靠这一层。常用：

    vgrad / fill / disc / poly / line          形状与渐变（抗锯齿软边）
    glow / radial / shadow / vignette           发光、阴影、暗角
    fbm(xs, ys) / noise_tex                     平滑噪声（材质、烟、火、水、云）
    smoke / fire / embers                       体积烟、火焰、火星
    Surface / lathe / sphere / torus / sheet    小型 3D：参数曲面 → 光照 → z 缓冲 → 灰度精灵（可缓存）
    capsule                                     有光照的胶囊（手指、四肢、香、笔杆）
    quad_tex                                    透视贴图（纸、桌面、八卦盘倾斜翻转）
    Layer                                       缓存一整层静态画面（背景、器物），每帧只贴一次

混合模式 mode：over（按 alpha 覆盖，默认）、max（取亮）、add（叠加发光）、mul（乘，压暗）、min（取暗）。
光照：LIGHT 是默认光的方向（左上前方）。
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from .gfx import H, W, Gfx

YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
LIGHT = np.array([-0.55, -0.6, 0.58], np.float32)
LIGHT /= np.linalg.norm(LIGHT)


# ---------------------------------------------------------------- 基础

def _box(x0, y0, x1, y1):
    x0, y0 = max(int(math.floor(x0)), 0), max(int(math.floor(y0)), 0)
    x1, y1 = min(int(math.ceil(x1)), W), min(int(math.ceil(y1)), H)
    return x0, y0, x1, y1


def blend(g: Gfx, x0: int, y0: int, val, alpha=1.0, mode: str = "over"):
    """把 val（标量或数组）按 alpha 混进 g.lum[y0:, x0:] 的同尺寸区域（数组须已裁好）"""
    L = g.L()
    if np.isscalar(val):
        if np.isscalar(alpha):
            return
        h, w = alpha.shape
    else:
        h, w = val.shape
    dst = L[y0:y0 + h, x0:x0 + w]
    if mode == "over":
        dst += (val - dst) * alpha
    elif mode == "max":
        np.maximum(dst, val * alpha if not np.isscalar(alpha) or alpha != 1 else val, out=dst)
    elif mode == "add":
        dst += val * alpha
        np.minimum(dst, 1.0, out=dst)
    elif mode == "mul":
        dst *= 1 - (1 - val) * alpha
    elif mode == "min":
        np.minimum(dst, val + (1 - alpha) * (1 - val) if not np.isscalar(alpha) else val, out=dst)
    elif mode == "screen":
        dst += (1 - dst) * val * alpha
    else:
        raise ValueError(mode)


def paste(g: Gfx, x: float, y: float, val: np.ndarray, alpha: np.ndarray | float = 1.0, mode: str = "over"):
    """贴一块灰度图（val、alpha 同形状），左上角 (x, y)，自动裁剪"""
    x, y = int(round(x)), int(round(y))
    h, w = val.shape
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    v = val[y0 - y:y1 - y, x0 - x:x1 - x]
    a = alpha if np.isscalar(alpha) else alpha[y0 - y:y1 - y, x0 - x:x1 - x]
    if np.isscalar(a):
        a = np.full(v.shape, a, np.float32)
    blend(g, x0, y0, v, a, mode)


def fill(g: Gfx, box, v: float, alpha: float = 1.0, mode: str = "over"):
    x0, y0, x1, y1 = _box(*box)
    if x1 > x0 and y1 > y0:
        blend(g, x0, y0, np.float32(v), np.full((y1 - y0, x1 - x0), alpha, np.float32), mode)


def vgrad(g: Gfx, box, v_top: float, v_bot: float, alpha: float = 1.0, mode: str = "over", gamma: float = 1.0):
    """竖直渐变"""
    x0, y0, x1, y1 = _box(*box)
    if x1 <= x0 or y1 <= y0:
        return
    bx = box[1]
    k = np.clip((YY[y0:y1, x0:x1] - bx) / max(box[3] - bx, 1e-6), 0, 1) ** gamma
    blend(g, x0, y0, v_top + (v_bot - v_top) * k, np.full(k.shape, alpha, np.float32), mode)


def hgrad(g: Gfx, box, v_left: float, v_right: float, alpha: float = 1.0, mode: str = "over"):
    x0, y0, x1, y1 = _box(*box)
    if x1 <= x0 or y1 <= y0:
        return
    k = np.clip((XX[y0:y1, x0:x1] - box[0]) / max(box[2] - box[0], 1e-6), 0, 1)
    blend(g, x0, y0, v_left + (v_right - v_left) * k, np.full(k.shape, alpha, np.float32), mode)


def disc(g: Gfx, cx: float, cy: float, rx: float, ry: float | None = None, v: float = 1.0, alpha: float = 1.0,
         soft: float = 0.8, mode: str = "over"):
    """软边椭圆（抗锯齿）"""
    ry = rx if ry is None else ry
    x0, y0, x1, y1 = _box(cx - rx - 2, cy - ry - 2, cx + rx + 2, cy + ry + 2)
    if x1 <= x0 or y1 <= y0 or rx <= 0 or ry <= 0:
        return
    dx = (XX[y0:y1, x0:x1] - cx) / rx
    dy = (YY[y0:y1, x0:x1] - cy) / ry
    d = (np.sqrt(dx * dx + dy * dy) - 1) * min(rx, ry)
    a = np.clip(0.5 - d / max(soft, 1e-3), 0, 1) * alpha
    blend(g, x0, y0, np.float32(v) if np.isscalar(v) else v, a, mode)


def radial(g: Gfx, cx: float, cy: float, r: float, v_in: float, v_out: float, ry: float | None = None,
           falloff: float = 1.0, alpha: float = 1.0, mode: str = "over"):
    """径向渐变（圆内从 v_in 到 v_out，圆外不画）"""
    ry = r if ry is None else ry
    x0, y0, x1, y1 = _box(cx - r - 1, cy - ry - 1, cx + r + 1, cy + ry + 1)
    if x1 <= x0 or y1 <= y0:
        return
    dx = (XX[y0:y1, x0:x1] - cx) / r
    dy = (YY[y0:y1, x0:x1] - cy) / ry
    k = np.sqrt(dx * dx + dy * dy)
    inside = np.clip((1 - k) * r, 0, 1)
    val = v_in + (v_out - v_in) * np.clip(k, 0, 1) ** falloff
    blend(g, x0, y0, val.astype(np.float32), (inside * alpha).astype(np.float32), mode)


def glow(g: Gfx, cx: float, cy: float, r: float, strength: float = 1.0, ry: float | None = None):
    """柔和发光（高斯，叠加）：火光、香头、法器灵光"""
    ry = r if ry is None else ry
    x0, y0, x1, y1 = _box(cx - 2.5 * r, cy - 2.5 * ry, cx + 2.5 * r, cy + 2.5 * ry)
    if x1 <= x0 or y1 <= y0:
        return
    dx = (XX[y0:y1, x0:x1] - cx) / r
    dy = (YY[y0:y1, x0:x1] - cy) / ry
    a = np.exp(-(dx * dx + dy * dy)) * strength
    blend(g, x0, y0, np.float32(1.0), a.astype(np.float32), "add")


def shadow(g: Gfx, cx: float, cy: float, rx: float, ry: float, strength: float = 0.6):
    """柔和接触阴影（压暗）"""
    x0, y0, x1, y1 = _box(cx - rx * 1.6, cy - ry * 1.6, cx + rx * 1.6, cy + ry * 1.6)
    if x1 <= x0 or y1 <= y0:
        return
    dx = (XX[y0:y1, x0:x1] - cx) / rx
    dy = (YY[y0:y1, x0:x1] - cy) / ry
    a = np.exp(-(dx * dx + dy * dy) * 1.5) * strength
    blend(g, x0, y0, np.float32(0.0), a.astype(np.float32), "over")


def vignette(g: Gfx, strength: float = 0.5, power: float = 2.0):
    """四周压暗（聚光、夜晚、回忆感）"""
    L = g.L()
    dx = (XX - 64) / 72
    dy = (YY - 32) / 40
    L *= 1 - strength * np.clip(dx * dx + dy * dy, 0, 1) ** (power / 2)


def _mask_poly(pts, x0, y0, w, h, ss: int = 2) -> np.ndarray:
    m = Image.new("L", (w * ss, h * ss))
    ImageDraw.Draw(m).polygon([((px - x0) * ss, (py - y0) * ss) for px, py in pts], fill=255)
    if ss > 1:
        m = m.resize((w, h), Image.BOX)
    return np.asarray(m, np.float32) / 255.0


def poly(g: Gfx, pts, v=1.0, alpha: float = 1.0, mode: str = "over", grad=None):
    """抗锯齿多边形。v 为标量，或 grad=(v0, v1, 方向角) 表示沿方向渐变"""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0, x1, y1 = _box(min(xs) - 1, min(ys) - 1, max(xs) + 2, max(ys) + 2)
    if x1 <= x0 or y1 <= y0:
        return
    a = _mask_poly(pts, x0, y0, x1 - x0, y1 - y0) * alpha
    if grad is not None:
        v0, v1, ang = grad
        ux, uy = math.cos(ang), math.sin(ang)
        proj = (XX[y0:y1, x0:x1] * ux + YY[y0:y1, x0:x1] * uy)
        pmin = min(px * ux + py * uy for px, py in pts)
        pmax = max(px * ux + py * uy for px, py in pts)
        val = v0 + (v1 - v0) * np.clip((proj - pmin) / max(pmax - pmin, 1e-6), 0, 1)
    else:
        val = np.float32(v)
    blend(g, x0, y0, val, a, mode)


def line(g: Gfx, x0: float, y0: float, x1: float, y1: float, w: float = 1.0, v: float = 1.0, alpha: float = 1.0,
         mode: str = "over", v1: float | None = None):
    """抗锯齿粗线（w 为直径）；v1：末端的值（沿线渐变）"""
    bx0, by0, bx1, by1 = _box(min(x0, x1) - w - 1, min(y0, y1) - w - 1, max(x0, x1) + w + 2, max(y0, y1) + w + 2)
    if bx1 <= bx0 or by1 <= by0:
        return
    px, py = XX[by0:by1, bx0:bx1], YY[by0:by1, bx0:bx1]
    dx, dy = x1 - x0, y1 - y0
    ll = dx * dx + dy * dy
    k = np.clip(((px - x0) * dx + (py - y0) * dy) / ll, 0, 1) if ll > 1e-9 else np.zeros_like(px)
    ex, ey = px - (x0 + k * dx), py - (y0 + k * dy)
    d = np.sqrt(ex * ex + ey * ey) - w / 2
    a = np.clip(0.5 - d, 0, 1) * alpha
    val = np.float32(v) if v1 is None else (v + (v1 - v) * k).astype(np.float32)
    blend(g, bx0, by0, val, a.astype(np.float32), mode)


def capsule(g: Gfx, x0: float, y0: float, x1: float, y1: float, r0: float, r1: float | None = None,
            base: float = 0.75, amb: float = 0.18, spec: float = 0.35, light=None, alpha: float = 1.0,
            rim: float = 0.0, edge: float = 0.0, hard: tuple | None = (0.15, 0.75)):
    """有光照的胶囊体（圆柱 + 两端半球）：手指、四肢、香、笔杆、剑柄。r1：末端半径（锥形）。
    edge：边缘压暗的宽度（0.3–0.6），让并排的圆柱分得开"""
    r1 = r0 if r1 is None else r1
    lt = LIGHT if light is None else light
    rm = max(r0, r1)
    bx0, by0, bx1, by1 = _box(min(x0, x1) - rm - 1, min(y0, y1) - rm - 1, max(x0, x1) + rm + 2, max(y0, y1) + rm + 2)
    if bx1 <= bx0 or by1 <= by0:
        return
    px, py = XX[by0:by1, bx0:bx1] + 0.5, YY[by0:by1, bx0:bx1] + 0.5
    dx, dy = x1 - x0, y1 - y0
    ll = dx * dx + dy * dy
    k = np.clip(((px - x0) * dx + (py - y0) * dy) / ll, 0, 1) if ll > 1e-9 else np.zeros_like(px)
    rr = r0 + (r1 - r0) * k
    ex, ey = px - (x0 + k * dx), py - (y0 + k * dy)
    d = np.sqrt(ex * ex + ey * ey)
    a = np.clip(rr - d + 0.5, 0, 1) * alpha
    nx, ny = ex / np.maximum(rr, 1e-3), ey / np.maximum(rr, 1e-3)
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    lam = np.clip(nx * lt[0] + ny * lt[1] + nz * lt[2], 0, 1)
    if hard:
        lam = np.clip((lam - hard[0]) / (hard[1] - hard[0]), 0, 1)
        lam = lam * lam * (3 - 2 * lam)
    val = amb + base * lam + spec * np.clip(2 * lam * nz - lt[2], 0, 1) ** 8
    if rim:
        val += rim * np.clip(1 - nz, 0, 1) ** 2
    if edge:  # 边缘压暗：相邻的圆柱（手指）之间留出暗缝，抖动后也分得开
        val = val * np.clip(nz / edge, 0, 1)
    blend(g, bx0, by0, np.clip(val, 0, 1).astype(np.float32), a.astype(np.float32))


# ---------------------------------------------------------------- 噪声

def _make_noise(n: int = 128, seed: int = 3) -> np.ndarray:
    """可平铺的 fbm 值噪声（n×n，0..1）"""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for cells in (4, 8, 16, 32, 64):
        grid = rng.random((cells, cells)).astype(np.float32)
        img = Image.fromarray((grid * 255).astype(np.uint8))
        # 平铺插值：先在四周补一圈再缩放
        big = np.pad(grid, 1, mode="wrap")
        im = Image.fromarray((big * 255).astype(np.uint8)).resize(((cells + 2) * n // cells, (cells + 2) * n // cells),
                                                                  Image.BICUBIC)
        arr = np.asarray(im, np.float32)[n // cells:n // cells + n, n // cells:n // cells + n] / 255.0
        out += arr * amp
        tot += amp
        amp *= 0.5
        del img
    out /= tot
    out = (out - out.min()) / (out.max() - out.min())
    return out


NOISE = _make_noise()
_NN = NOISE.shape[0]


def fbm(xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """在可平铺噪声上双线性取样（坐标单位：噪声像素；乘个系数控制粗细，加 t 让它流动）"""
    x = np.mod(xs, _NN)
    y = np.mod(ys, _NN)
    xi = x.astype(np.int32)
    yi = y.astype(np.int32)
    fx = x - xi
    fy = y - yi
    x1 = (xi + 1) % _NN
    y1 = (yi + 1) % _NN
    a = NOISE[yi, xi]
    b = NOISE[yi, x1]
    c = NOISE[y1, xi]
    d = NOISE[y1, x1]
    return (a + (b - a) * fx) + ((c + (d - c) * fx) - (a + (b - a) * fx)) * fy


def noise_tex(g: Gfx, box, scale: float = 1.0, lo: float = 0.0, hi: float = 1.0, alpha: float = 1.0,
              mode: str = "mul", ox: float = 0.0, oy: float = 0.0, sx: float = 1.0):
    """在区域里铺噪声材质（默认乘，给平面加斑驳：铜锈、石纹、纸纤维、木纹用 sx 拉伸）"""
    x0, y0, x1, y1 = _box(*box)
    if x1 <= x0 or y1 <= y0:
        return
    n = fbm(XX[y0:y1, x0:x1] * scale * sx + ox, YY[y0:y1, x0:x1] * scale + oy)
    blend(g, x0, y0, (lo + (hi - lo) * n).astype(np.float32), np.full(n.shape, alpha, np.float32), mode)


# ---------------------------------------------------------------- 烟、火

def smoke(g: Gfx, x: float, y: float, height: float, t: float, width: float = 3.0, spread: float = 14.0,
          density: float = 0.9, wind: float = 0.0, seed: int = 0, curl: float = 5.0, speed: float = 9.0,
          mode: str = "screen"):
    """体积感的一缕烟：从 (x, y) 往上，底部细而浓，越往上越宽越淡，被噪声场扭动、撕开。
    wind：越高越往旁边飘（像素）；curl：扭动幅度"""
    top = y - height
    x0, y0, x1, y1 = _box(x - spread - abs(wind) - curl - 2, top, x + spread + abs(wind) + curl + 2, y + 1)
    if x1 <= x0 or y1 <= y0:
        return
    px, py = XX[y0:y1, x0:x1], YY[y0:y1, x0:x1]
    k = np.clip((y - py) / max(height, 1), 0, 1)                 # 0 底 → 1 顶
    sy = py + t * speed
    sway = (fbm(sy * 0.08 + seed * 13.1, k * 3 + seed) - 0.5) * 2 * curl * (0.25 + k)
    cxk = x + wind * k * k + sway
    w = width * 0.5 + (spread - width * 0.5) * k ** 1.3
    dxn = (px - cxk) / np.maximum(w, 0.5)
    core = np.exp(-dxn * dxn * 2.2)
    tex = fbm(px * 0.35 + seed * 7.7, sy * 0.35)
    tex2 = fbm(px * 0.9 - seed * 3.1, sy * 0.9 + 50)
    dens = core * (0.55 + 0.9 * (tex - 0.5) + 0.35 * (tex2 - 0.5))
    dens *= density * (1 - k) ** 1.4 * np.clip(k * 12, 0, 1)
    dens = np.clip(dens, 0, 1).astype(np.float32)
    blend(g, x0, y0, np.float32(0.92), dens, mode)


def fire(g: Gfx, x: float, y: float, w: float, h: float, t: float, seed: int = 0, intensity: float = 1.0):
    """火焰：底部中心 (x, y)，噪声驱动的焰舌，内芯最亮"""
    x0, y0, x1, y1 = _box(x - w, y - h * 1.3, x + w, y + 2)
    if x1 <= x0 or y1 <= y0:
        return
    px, py = XX[y0:y1, x0:x1], YY[y0:y1, x0:x1]
    k = np.clip((y - py) / max(h, 1), 0, 1.3)
    n = fbm(px * 0.6 + seed * 9.3, py * 0.5 + t * 22)
    n2 = fbm(px * 1.3 - seed * 2.2, py * 1.1 + t * 35 + 40)
    lean = (fbm(np.float32(t * 2 + seed), np.float32(seed * 3)) - 0.5) * w * 0.8
    cx = x + lean * k * k
    half = (w / 2) * np.clip(1 - k, 0, 1) ** 0.7 * (0.75 + 0.5 * n)
    d = np.abs(px - cx) / np.maximum(half, 0.3)
    shape = np.clip(1 - d, 0, 1) * np.clip((1.05 - k) * 3 + (n2 - 0.5), 0, 1)
    heat = np.clip(shape * (1.3 - k * 0.6) * intensity, 0, 1).astype(np.float32)
    blend(g, x0, y0, np.float32(1.0), heat, "screen")


def embers(g: Gfx, x: float, y: float, t: float, n: int = 6, rise: float = 18.0, spread: float = 6.0, seed: int = 0,
           life: float = 1.6):
    """上升的火星（确定性，按 t）"""
    for i in range(n):
        ph = (t / life + i / n + seed * 0.37) % 1.0
        r = ((i * 7919 + seed * 104729) % 1000) / 1000
        ex = x + (r - 0.5) * spread + math.sin(ph * 6 + i) * 2 * ph
        ey = y - ph * rise
        b = (1 - ph) * (0.6 + 0.4 * math.sin(t * 20 + i * 3))
        if b > 0.15:
            fill(g, (ex, ey, ex + 1, ey + 1), 1.0, b, "max")


# ---------------------------------------------------------------- 3D：参数曲面 → 灰度精灵

class Sprite3D:
    """渲染好的灰度精灵：val、alpha、depth（同形状），原点 (ox, oy) = 精灵内对应世界原点的像素位置"""
    __slots__ = ("val", "alpha", "depth", "ox", "oy")

    def __init__(self, val, alpha, depth, ox, oy):
        self.val, self.alpha, self.depth, self.ox, self.oy = val, alpha, depth, ox, oy

    def draw(self, g: Gfx, x: float, y: float, mode: str = "over", alpha: float = 1.0, outline: int | None = None):
        """outline=1：轮廓画白线（墨），0：画黑线；None 不画"""
        paste(g, x - self.ox, y - self.oy, self.val, self.alpha * alpha if alpha != 1 else self.alpha, mode)
        if outline is not None:
            edge_ink(g, self.mask_at(x, y), outline)

    def mask_at(self, x: float, y: float) -> np.ndarray:
        """精灵在屏幕上的覆盖范围（整屏 bool）"""
        m = np.zeros((H, W), bool)
        x, y = int(round(x - self.ox)), int(round(y - self.oy))
        h, w = self.alpha.shape
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
        if x1 > x0 and y1 > y0:
            m[y0:y1, x0:x1] = self.alpha[y0 - y:y1 - y, x0 - x:x1 - x] > 0.5
        return m


def edge_ink(g: Gfx, mask: np.ndarray, ink: int = 1, outer: bool = False):
    """沿覆盖范围的边描一圈墨线（1 白 / 0 黑）。outer：描在外侧（剪影外轮廓）"""
    if outer:
        grown = mask | np.roll(mask, 1, 0) | np.roll(mask, -1, 0) | np.roll(mask, 1, 1) | np.roll(mask, -1, 1)
        edge = grown & ~mask
    else:
        inner = mask & np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1)
        edge = mask & ~inner
    im = Image.fromarray(edge)
    if ink:
        g.img.paste(1, (0, 0), im)
    else:
        g.cut.paste(1, (0, 0), im)


def view(points: np.ndarray, yaw: float = 0.0, pitch: float = 0.35, persp: float = 0.0):
    """世界坐标 (…,3)（x 右、y 下、z 朝观众）→ 绕竖轴转 yaw、再俯视 pitch。返回 (sx, sy, depth)。
    persp>0 时加透视（越远越小，值约为 1/视距）"""
    x, y, z = points[..., 0], points[..., 1], points[..., 2]
    cy, sy_ = math.cos(yaw), math.sin(yaw)
    x, z = x * cy + z * sy_, -x * sy_ + z * cy
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = y * cp + z * sp, -y * sp + z * cp  # 俯视：朝上的面转向观众，近处的点在屏幕上更靠下
    if persp:
        f = 1 / (1 - z * persp)
        x, y = x * f, y * f
    return x, y, z


def render_surface(P: np.ndarray, N: np.ndarray, albedo: np.ndarray | float = 0.8, yaw: float = 0.0,
                   pitch: float = 0.35, persp: float = 0.0, light=None, amb: float = 0.15, spec: float = 0.4,
                   shine: float = 16.0, two_sided: bool = False, rim: float = 0.0,
                   hard: tuple | None = (0.15, 0.75)) -> Sprite3D:
    """点云式渲染：P、N 为 (nu, nv, 3) 或 (n, 3) 的位置与法线（世界坐标），albedo 同形或标量。
    采样要足够密（相邻点投影间距 < 1 像素）才不会有洞。
    hard=(lo, hi)：明暗交界收紧（默认开；在这块黑白屏上避免大片中间灰），None 为普通 Lambert"""
    lt = LIGHT if light is None else np.asarray(light, np.float32)
    sx, sy, sz = view(P, yaw, pitch, persp)
    nx, ny, nz = view(N, yaw, pitch, 0.0)
    if two_sided:
        flip = nz < 0
        nx, ny, nz = np.where(flip, -nx, nx), np.where(flip, -ny, ny), np.where(flip, -nz, nz)
    lam = np.clip(nx * lt[0] + ny * lt[1] + nz * lt[2], 0, 1)
    if hard:  # 收紧明暗交界：受光面更亮、背光面更暗，抖动后不是一片中间灰
        lo, hi = hard
        lam = np.clip((lam - lo) / (hi - lo), 0, 1)
        lam = lam * lam * (3 - 2 * lam)
    # Blinn：半角向量（光 + 视线 z）
    hx, hy, hz = lt[0], lt[1], lt[2] + 1.0
    hn = math.sqrt(hx * hx + hy * hy + hz * hz)
    sp = np.clip((nx * hx + ny * hy + nz * hz) / hn, 0, 1) ** shine
    alb = albedo if np.isscalar(albedo) else albedo
    val = amb * alb + alb * lam + spec * sp
    if rim:
        val = val + rim * np.clip(1 - np.abs(nz), 0, 1) ** 3
    val = np.clip(val, 0, 1).astype(np.float32).ravel()
    sx, sy, sz = sx.ravel(), sy.ravel(), sz.ravel()
    xmin, ymin = math.floor(sx.min()), math.floor(sy.min())
    w = int(math.ceil(sx.max())) - xmin + 2
    h = int(math.ceil(sy.max())) - ymin + 2
    ix = np.floor(sx - xmin + 0.5).astype(np.int32)
    iy = np.floor(sy - ymin + 0.5).astype(np.int32)
    order = np.argsort(sz)  # 远 → 近，近的后写覆盖
    idx = (iy * w + ix)[order]
    vbuf = np.zeros(h * w, np.float32)
    abuf = np.zeros(h * w, np.float32)
    dbuf = np.full(h * w, -1e9, np.float32)
    vbuf[idx] = val[order]
    abuf[idx] = 1.0
    dbuf[idx] = sz[order]
    vb, ab, db = vbuf.reshape(h, w), abuf.reshape(h, w), dbuf.reshape(h, w)
    # 补单像素小洞：四邻都有而自己没有的点取邻居平均
    hole = (ab == 0)
    hole[0, :] = hole[-1, :] = False
    hole[:, 0] = hole[:, -1] = False
    if hole.any():
        nb = ab[:-2, 1:-1] + ab[2:, 1:-1] + ab[1:-1, :-2] + ab[1:-1, 2:]
        fillm = hole[1:-1, 1:-1] & (nb >= 3)
        if fillm.any():
            s = vb[:-2, 1:-1] + vb[2:, 1:-1] + vb[1:-1, :-2] + vb[1:-1, 2:]
            inner = vb[1:-1, 1:-1]
            inner[fillm] = (s / np.maximum(nb, 1))[fillm]
            ab[1:-1, 1:-1][fillm] = 1.0
    return Sprite3D(vb, ab, db, -xmin, -ymin)


def lathe_mesh(profile, nu: int = 96, nv: int | None = None, rot: float = 0.0):
    """旋转体：profile = [(y, r), …]（y 向下增加），绕竖轴一圈。返回 P, N, U(0..1 绕圈), V(0..1 沿轮廓)"""
    prof = np.asarray(profile, np.float32)
    seg = np.hypot(np.diff(prof[:, 0]), np.diff(prof[:, 1]))
    s = np.concatenate([[0], np.cumsum(seg)])
    nv = nv or max(int(s[-1] * 2.2), 8)
    ss = np.linspace(0, s[-1], nv)
    ys = np.interp(ss, s, prof[:, 0])
    rs = np.interp(ss, s, prof[:, 1])
    th = np.linspace(0, 2 * np.pi, nu, endpoint=False) + rot
    TH, YS = np.meshgrid(th, ys, indexing="xy")
    RS = np.broadcast_to(rs[:, None], TH.shape)
    P = np.stack([RS * np.sin(TH), YS, RS * np.cos(TH)], -1).astype(np.float32)
    dr = np.gradient(rs)
    dy = np.gradient(ys)
    # 轮廓切线 (dr, dy) → 法线 (dy, -dr) 在径向平面内
    nr, ny = dy, -dr
    ln = np.maximum(np.hypot(nr, ny), 1e-6)
    nr, ny = nr / ln, ny / ln
    NR = np.broadcast_to(nr[:, None], TH.shape)
    NY = np.broadcast_to(ny[:, None], TH.shape)
    N = np.stack([NR * np.sin(TH), NY, NR * np.cos(TH)], -1).astype(np.float32)
    U = ((TH - rot) / (2 * np.pi)) % 1.0
    V = np.broadcast_to((ss / s[-1])[:, None], TH.shape)
    return P, N, U, V


def torus_mesh(R: float, r: float, nu: int = 96, nv: int = 24):
    """圆环（躺平，绕竖轴）"""
    u = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    v = np.linspace(0, 2 * np.pi, nv, endpoint=False)
    U, V = np.meshgrid(u, v, indexing="xy")
    cx, cz = np.sin(U), np.cos(U)
    P = np.stack([(R + r * np.cos(V)) * cx, -r * np.sin(V), (R + r * np.cos(V)) * cz], -1).astype(np.float32)
    N = np.stack([np.cos(V) * cx, -np.sin(V), np.cos(V) * cz], -1).astype(np.float32)
    return P, N, U / (2 * np.pi), V / (2 * np.pi)


def sphere_mesh(r: float, nu: int = 96, nv: int = 48, rot: float = 0.0):
    u = np.linspace(0, 2 * np.pi, nu, endpoint=False) + rot
    v = np.linspace(0, np.pi, nv)
    U, V = np.meshgrid(u, v, indexing="xy")
    N = np.stack([np.sin(V) * np.sin(U), -np.cos(V), np.sin(V) * np.cos(U)], -1).astype(np.float32)
    return N * r, N, ((U - rot) / (2 * np.pi)) % 1.0, V / np.pi


def sheet_mesh(w: float, h: float, nu: int = 48, nv: int = 64, bend=None):
    """一张纸 / 布（在 xy 平面，中心为原点）。bend(u, v) → z 位移（u, v ∈ 0..1），做飘动、卷曲"""
    u = np.linspace(0, 1, nu)
    v = np.linspace(0, 1, nv)
    U, V = np.meshgrid(u, v, indexing="xy")
    Z = bend(U, V) if bend is not None else np.zeros_like(U)
    P = np.stack([(U - 0.5) * w, (V - 0.5) * h, Z], -1).astype(np.float32)
    du = np.gradient(P, axis=1)
    dv = np.gradient(P, axis=0)
    N = np.cross(du, dv)
    N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-6)
    N[..., 2] = np.abs(N[..., 2]) * np.sign(N[..., 2] + 1e-9)
    return P, -N, U, V


_SPRITES: dict = {}


def cached(key, make):
    """缓存渲染结果（静态器物只渲染一次；会转动的按角度量化成若干档）"""
    sp = _SPRITES.get(key)
    if sp is None:
        if len(_SPRITES) > 2500:
            _SPRITES.clear()
        sp = _SPRITES[key] = make()
    return sp


def lathe(profile, yaw: float = 0.0, pitch: float = 0.35, albedo=0.75, tex=None, nu: int = 120, key=None,
          **kw) -> Sprite3D:
    """旋转体精灵（香炉、碗、钟、灯盏、葫芦、丹炉……）。tex(U, V) → albedo 数组（纹样、铜锈）。
    key 不为 None 时缓存（同 key 只渲染一次）"""
    def make():
        P, N, U, V = lathe_mesh(profile, nu)
        alb = tex(U, V) if tex is not None else albedo
        return render_surface(P, N, alb, yaw, pitch, **kw)
    return cached(("lathe", key), make) if key is not None else make()


def sphere(r: float, yaw: float = 0.0, pitch: float = 0.3, albedo=0.8, tex=None, key=None, **kw) -> Sprite3D:
    def make():
        P, N, U, V = sphere_mesh(r, max(48, int(r * 8)), max(24, int(r * 4)))
        alb = tex(U, V) if tex is not None else albedo
        return render_surface(P, N, alb, yaw, pitch, **kw)
    return cached(("sphere", key), make) if key is not None else make()


def torus(R: float, r: float, yaw: float = 0.0, pitch: float = 0.35, albedo=0.75, key=None, **kw) -> Sprite3D:
    def make():
        P, N, U, V = torus_mesh(R, r, max(64, int(R * 10)), max(16, int(r * 10)))
        return render_surface(P, N, albedo, yaw, pitch, **kw)
    return cached(("torus", key), make) if key is not None else make()


# ---------------------------------------------------------------- 透视贴图

def _homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.asarray(A, np.float64))
    Hm = vt[-1].reshape(3, 3)
    return Hm / Hm[2, 2]


def quad_tex(g: Gfx, quad, tex: np.ndarray, alpha: float = 1.0, mode: str = "over", tex_alpha: np.ndarray | None = None):
    """把贴图 tex（灰度 [h,w]）贴到屏幕四边形 quad=[(x,y) 左上, 右上, 右下, 左下]（透视正确）"""
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    x0, y0, x1, y1 = _box(min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    if x1 <= x0 or y1 <= y0:
        return
    th, tw = tex.shape
    Hm = _homography(quad, [(0, 0), (tw, 0), (tw, th), (0, th)])
    px, py = XX[y0:y1, x0:x1] + 0.5, YY[y0:y1, x0:x1] + 0.5
    d = Hm[2, 0] * px + Hm[2, 1] * py + Hm[2, 2]
    u = (Hm[0, 0] * px + Hm[0, 1] * py + Hm[0, 2]) / d
    v = (Hm[1, 0] * px + Hm[1, 1] * py + Hm[1, 2]) / d
    inside = (u >= 0) & (u < tw) & (v >= 0) & (v < th)
    ui = np.clip(u, 0, tw - 1).astype(np.int32)
    vi = np.clip(v, 0, th - 1).astype(np.int32)
    val = tex[vi, ui]
    a = inside.astype(np.float32) * alpha
    if tex_alpha is not None:
        a *= tex_alpha[vi, ui]
    blend(g, x0, y0, val.astype(np.float32), a, mode)


@lru_cache(maxsize=64)
def text_tex(s: str, size: int = 12, pad: int = 1, vertical: bool = False) -> np.ndarray:
    """文字 → 灰度贴图（白字黑底），用于贴在纸上、符上、牌匾上（会跟着透视变形）"""
    from .gfx import Gfx as _G
    g = _G()
    if vertical:
        h = g.vtext(pad, pad, s, size)
        w = size + pad * 2
        hh = h + pad * 2
    else:
        w = g.text(pad, pad, s, size) + pad * 2
        hh = size + pad * 2
    return np.asarray(g.img, np.float32)[:hh, :w].copy()


class Layer:
    """缓存整屏静态背景（只缓存灰度层）：首次调用 draw_fn(g) 在空白画布上画好，以后每帧整层复制（几微秒）"""

    def __init__(self, draw_fn):
        self.fn = draw_fn
        self.val = None

    def draw(self, g: Gfx):
        if self.val is None:
            tmp = Gfx()
            tmp.L()
            self.fn(tmp)
            self.val = tmp.lum.copy()
        np.copyto(g.L(), self.val)
