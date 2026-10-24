"""r2 批（符箓·咒·印）共用零件，1 位像素风。不登记场景，只被 r2_*.py 导入。

- 字形精灵 glyph / 逐行写出 glyph_reveal（画符、印文这类“画出来的字”，不算文字）
- 折线工具 polyline_part / poly_len / spiral（笔尖沿笔画走）
- 小道士的自定义手臂：arm_spr(角度, 长度) + act(...)：给出手要伸到的位置，自动选角度、长度，返回手的位置
- 道具精灵（模块级缓存）：小符 fu_spr、毛笔 brush、蜡烛 + 火苗、朱砂碟、法印、碗、蒲团……
- 小舞台：floor（地砖）、boxed（带框的计数牌，最后画）
- 点阵小图：mx_fu、mx_ring
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine import pix
from ..engine.anim import clamp, noise
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite, _FONT_FILES, font, text_width

# ================================================================ 字形精灵

_glyphs: dict[tuple, Sprite] = {}


def glyph(s: str, size: int = 12, scale: int = 1) -> Sprite:
    """把一串字渲染成精灵（缓存）：高 = 字高（12px 为 11），笔画 '#'，其余透明"""
    key = (s, size, scale)
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
        _glyphs[key] = Sprite(on=on, mask=on.copy())
    return _glyphs[key]


_cuts: dict[tuple, Sprite] = {}


def glyph_reveal(g: Gfx, x: float, y: float, s: str, k: float, size: int = 12, scale: int = 1,
                 ink: int = 1) -> tuple[float, float]:
    """自上而下“写”出字形（k 0..1），ink=0 用黑墨写在亮纸上。返回笔尖位置（正在写的那一行上的笔画处）"""
    spr = glyph(s, size, scale)
    k = clamp(k)
    if k <= 0:
        return x + spr.w / 2, y
    rows = max(1, int(round(spr.h * k)))
    if rows >= spr.h:
        g.blit(spr, x, y, invert=not ink)
        return x + spr.w / 2, y + spr.h - 1
    key = (s, size, scale, rows)
    part = _cuts.get(key)
    if part is None:
        part = Sprite(on=spr.on[:rows].copy(), mask=spr.mask[:rows].copy())
        if len(_cuts) > 600:
            _cuts.clear()
        _cuts[key] = part
    g.blit(part, x, y, invert=not ink)
    xs = np.nonzero(spr.on[rows - 1])[0]
    tip_x = x + (xs[int(len(xs) * noise(k * 9, len(s))) % len(xs)] if len(xs) else spr.w / 2)
    return tip_x, y + rows - 1


# ================================================================ 折线

def poly_len(pts) -> float:
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def polyline_part(pts, p: float):
    """折线的前 p（0..1）部分；返回（点列，末端点）"""
    if p <= 0 or len(pts) < 2:
        return [pts[0]], pts[0]
    seg = [math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    want = sum(seg) * clamp(p)
    out, acc = [pts[0]], 0.0
    for i, s in enumerate(seg):
        if acc + s >= want:
            k = (want - acc) / s if s else 0
            end = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k)
            out.append(end)
            return out, end
        acc += s
        out.append(pts[i + 1])
    return out, pts[-1]


def spiral(cx: float, cy: float, r: float, turns: float = 2.2, n: int = 28, start: float = 0.0):
    """由外向内的螺旋（符胆常见画法）"""
    pts = []
    for i in range(n + 1):
        k = i / n
        a = start + k * turns * 2 * math.pi
        rr = r * (1 - k * 0.85)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts


# ================================================================ 小道士：自定义手臂

ARM_N = 32          # 角度分档
ARM_C = 18          # 手臂精灵画布 37×37，肩在中心
SHOULDER = (0, -15)  # 肩（相对脚底中点，朝右）
_ARMS: dict = {}


def _arm(ai: int, L: int) -> Sprite:
    """宽袖手臂：袖筒从肩伸到腕、袖口外扩并镶边、袖子朝下的一侧垂下来（越平越垂），背光面网点，露手"""
    a = ai * 2 * math.pi / ARM_N
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    if ny < 0:
        nx, ny = -nx, -ny                       # n 指向下方（袖子垂的一侧）
    c = ARM_C
    p = Part(2 * c + 1, 2 * c + 1)
    S = (c + 0.5, c + 0.5)
    Wx, Wy = S[0] + ux * L, S[1] + uy * L

    def P(bx, by, du, dn):
        return (bx + ux * du + nx * dn, by + uy * du + ny * dn)

    hang = 0.5 + 2.0 * abs(ux)                    # 垂袖长度（越平越垂）
    p.shape("polygon", [P(*S, 0, -2), P(Wx, Wy, -1, -2), P(Wx, Wy, 0, -2.5), P(Wx, Wy, 0, 2.5 + hang * 0.5),
                        P(Wx, Wy, -2, 2.5 + hang), P(*S, L * 0.5, 2.5), P(*S, 0, 2)], fill=1)
    p.d.line([P(Wx, Wy, -1, -2), P(Wx, Wy, -1, 2 + hang)], fill=0)              # 袖口镶边
    p.dither([P(*S, L * 0.3, 1), P(Wx, Wy, -2, 1), P(Wx, Wy, -2, 3 + hang), P(*S, L * 0.5, 3)], 0.5, 0)
    hx, hy = Wx + ux * 1.6, Wy + uy * 1.6
    p.shape("ellipse", (hx - 1.6, hy - 1.6, hx + 1.4, hy + 1.4), fill=1)          # 手
    spr = p.sprite()
    spr.hand = (int(round(hx - 0.5)), int(round(hy - 0.5)))
    spr.over_head = uy < -0.45
    return spr


def arm_spr(ang: float, L: float = 9) -> Sprite:
    ai = int(round(ang / (2 * math.pi) * ARM_N)) % ARM_N
    L = int(clamp(round(L), 5, 15))
    key = (ai, L)
    s = _ARMS.get(key)
    if s is None:
        s = _ARMS[key] = _arm(ai, L)
    return s


def shoulder(x: float, y: float, flip: bool = False, legs: str = "stand") -> tuple[float, float]:
    """肩的屏幕位置（x, y = 脚底中点）"""
    dy = {"stand": 0, "walk": 0, "sit": -3, "kneel": 2}[legs]
    return (x - SHOULDER[0] if flip else x + SHOULDER[0], y + SHOULDER[1] + dy)


def act(g: Gfx, x: float, y: float, t: float, hand_to=None, ang: float | None = None, L: float = 9,
        flip: bool = False, legs: str = "stand", **kw) -> dict:
    """小道士 + 自定义手臂：hand_to=(hx, hy) 时自动算手臂角度和长度（伸不到就伸直指过去），
    否则用 ang（弧度，屏幕坐标，0 朝右、-pi/2 朝上）。其余参数同 figure。返回 {"hand": (x, y)}"""
    sx, sy = shoulder(x, y, flip, legs)
    if hand_to is not None:
        dx, dy = hand_to[0] - sx, hand_to[1] - sy
        ang = math.atan2(dy, dx)
        L = math.hypot(dx, dy) - 2
    if flip:
        ang = math.pi - ang
    spr = arm_spr(ang, L)
    return figure(g, x, y, t, legs=legs, arm=spr, arm_at=(SHOULDER[0] - ARM_C, SHOULDER[1] - ARM_C), flip=flip, **kw)


# ================================================================ 道具

def fu_spr(w: int = 7, h: int = 15, seed: int = 0) -> Sprite:
    """一张小黄符（亮纸、黑字）：上边一道“三清”三勾，中间一竖符文带几道横折，下面一个小螺旋符胆"""
    key = ("fu", w, h, seed)
    s = _PROPS.get(key)
    if s is None:
        p = Part(w, h)
        p.shape("rectangle", (0, 0, w - 1, h - 1), fill=1)
        cx = w // 2
        for i, x in enumerate((cx - 2, cx, cx + 2)):         # 三勾
            if 0 < x < w - 1:
                p.px(x, 1, 0), p.px(x, 2, 0)
        p.d.line((1, 4, w - 2, 4), fill=0)                    # 雨字头
        p.d.line((cx, 4, cx, h - 4), fill=0)                  # 中竖
        for k, yy in enumerate(range(6, h - 4, 2)):
            dx = 2 if (k + seed) % 2 == 0 else -2
            p.d.line((cx, yy, cx + dx, yy), fill=0)
        p.d.line((1, h - 3, w - 2, h - 3), fill=0)            # 符脚
        p.px(cx - 1, h - 2, 0), p.px(cx + 1, h - 2, 0)
        s = _PROPS[key] = p.sprite()
    return s


_PROPS: dict = {}


def _prop(name, fn):
    s = _PROPS.get(name)
    if s is None:
        s = _PROPS[name] = fn()
    return s


def brush(g: Gfx, tip_x: float, tip_y: float, ang: float, ln: float = 13, inked: bool = True):
    """毛笔：笔尖在 (tip_x, tip_y)，ang = 从笔尖指向笔杆末端的方向。先画一圈黑边再画亮笔，压在亮纸上也清楚。
    笔头（狼毫）三像素宽、尖；铜箍一道；笔杆；末端挂绳圈"""
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    ex, ey = tip_x + ux * ln, tip_y + uy * ln
    fx, fy = tip_x + ux * 5, tip_y + uy * 5
    tuft = [(tip_x, tip_y), (tip_x + ux * 3 + nx * 1.4, tip_y + uy * 3 + ny * 1.4), (fx + nx * 1.2, fy + ny * 1.2),
            (fx - nx * 1.2, fy - ny * 1.2), (tip_x + ux * 3 - nx * 1.4, tip_y + uy * 3 - ny * 1.4)]
    g.d.line((fx, fy, ex, ey), fill=0, width=3)
    g.d.line(tuft + [tuft[0]], fill=0, width=3)
    g.d.line((fx, fy, ex, ey), fill=1)                                   # 笔杆
    g.d.polygon(tuft, fill=1 if inked else 0, outline=1)                 # 笔头
    if inked:
        g.px(tip_x + ux * 2 + nx, tip_y + uy * 2 + ny, 0)                # 狼毫的一道缝
    g.d.line((fx + nx * 1.5, fy + ny * 1.5, fx - nx * 1.5, fy - ny * 1.5), fill=1)  # 铜箍
    g.px(ex + ux + nx, ey + uy + ny), g.px(ex + ux - nx, ey + uy - ny), g.px(ex + ux * 2, ey + uy * 2)  # 绳圈
    g.px(tip_x, tip_y)


def fist(g: Gfx, x: float, y: float):
    """握拳的手 3×3（压在道具上面，盖住笔杆 / 印钮）"""
    x, y = int(round(x)), int(round(y))
    g.d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=0)
    g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
    g.px(x, y, 0)


def hold_brush(g: Gfx, hand, tip, inked: bool = True, past: float = 5):
    """手握毛笔：笔从笔尖穿过手、再伸出 past 像素；最后画拳头"""
    hx, hy = hand
    tx, ty = tip
    ang = math.atan2(hy - ty, hx - tx)
    brush(g, tx, ty, ang, max(math.hypot(hx - tx, hy - ty) + past, 8), inked)
    fist(g, hx, hy)


def candle_spr() -> Sprite:
    """烛台 7×14：蜡烛（一道烛泪）+ 托盘 + 细柄（一个节）+ 喇叭底座"""
    def mk():
        p = Part(7, 14)
        p.shape("rectangle", (2, 0, 4, 5), fill=1)
        p.px(4, 1, 0), p.px(4, 2, 0), p.px(3, 0, 0)
        p.shape("rectangle", (0, 6, 6, 6), fill=1)
        p.px(0, 5), p.px(6, 5)
        p.shape("rectangle", (3, 7, 3, 11), fill=1)
        p.px(2, 9), p.px(4, 9)
        p.shape("polygon", [(1, 13), (5, 13), (4, 11), (2, 11)], fill=1)
        return p.sprite()
    return _prop("candle", mk)


FLAME = pix.frames("""
 #
 #
###
#.#
---
  #
 #
###
#.#
---
 #
 ##
###
#.#
---
#
 #
###
#.#
""")


def candle(g: Gfx, x: float, base_y: float, t: float, lit: bool = True, seed: int = 0):
    """烛台底边中点 (x, base_y)；lit 时烛火跳动"""
    pix.blit(g, candle_spr(), x - 3, base_y - 14)
    if lit:
        pix.blit(g, pix.anim(FLAME, t + seed * 0.37, 7), x - 1, base_y - 18, outline=False)
    else:
        g.px(x, base_y - 15)


def dish_spr() -> Sprite:
    """朱砂碟 11×4：碟口、里面一汪朱砂（网点）、碟足"""
    def mk():
        p = Part(11, 4)
        p.shape("polygon", [(0, 0), (10, 0), (8, 2), (2, 2)], fill=1)
        p.d.line((1, 0, 9, 0), fill=1)
        p.d.line((2, 1, 8, 1), fill=0)
        for x in range(3, 8, 2):
            p.px(x, 1, 1)
        p.shape("rectangle", (4, 3, 6, 3), fill=1)
        return p.sprite()
    return _prop("dish", mk)


def seal_spr() -> Sprite:
    """法印侧视 11×12：龟钮（龟背纹、小头）+ 印台（一道阴线）+ 印面；钮上挂一绺绶带穗子"""
    def mk():
        p = Part(11, 12)
        p.shape("ellipse", (2, 0, 8, 4), fill=1)        # 龟背
        p.px(4, 1, 0), p.px(6, 1, 0), p.px(5, 2, 0), p.px(3, 3, 0), p.px(7, 3, 0)
        p.shape("rectangle", (8, 2, 9, 3), fill=1)      # 龟头
        p.px(9, 2, 0)
        p.shape("rectangle", (3, 4, 7, 4), fill=1)      # 龟足
        p.shape("rectangle", (0, 5, 10, 11), fill=1)    # 印台
        p.d.line((1, 6, 9, 6), fill=0)
        p.d.line((1, 10, 9, 10), fill=0)
        p.dither((6, 7, 9, 9), 0.5, 0)
        return p.sprite()
    return _prop("seal", mk)


def seal_face_spr(n: int = 18) -> Sprite:
    """印文“道经师宝”（阳文，右起竖读：右列道经、左列师宝）：方框双边，字是亮的"""
    def mk():
        on = np.zeros((n, n), bool)
        on[0, :] = on[-1, :] = on[:, 0] = on[:, -1] = True
        half = (n - 2) // 2
        for ch, (cx, cy) in zip("道经师宝", ((1, 0), (1, 1), (0, 0), (0, 1))):
            gs = glyph(ch, 8)
            x0, y0 = max(1, 1 + cx * half + (half - gs.w) // 2), max(1, 1 + cy * half + (half - gs.h) // 2)
            w, h = min(gs.w, n - 1 - x0), min(gs.h, n - 1 - y0)
            on[y0:y0 + h, x0:x0 + w] |= gs.on[:h, :w]
        return Sprite(on=on, mask=np.ones_like(on))
    return _prop(("sealface", n), mk)


def bowl_spr() -> Sprite:
    """清水碗 19×9（微俯视）：碗口椭圆（里面是水）、碗身回纹一圈、圈足"""
    def mk():
        p = Part(19, 9)
        p.shape("ellipse", (0, 0, 18, 4), fill=1)
        p.d.ellipse((1, 1, 17, 3), fill=0)              # 水面（黑）
        p.shape("polygon", [(0, 2), (18, 2), (15, 7), (3, 7)], fill=1)
        p.d.ellipse((1, 1, 17, 3), fill=0)
        p.d.line((2, 4, 16, 4), fill=0)
        for x in range(4, 15, 3):                       # 回纹
            p.px(x, 5, 0), p.px(x + 1, 5, 0)
        p.dither([(12, 5), (17, 3), (15, 7), (11, 7)], 0.5, 0)
        p.shape("rectangle", (6, 8, 12, 8), fill=1)     # 圈足
        return p.sprite()
    return _prop("bowl", mk)


def cushion_spr() -> Sprite:
    """蒲团 24×5：草编的圆垫，侧面一圈一圈的编纹"""
    def mk():
        p = Part(24, 5)
        p.shape("ellipse", (0, 0, 23, 6), fill=1)
        for x in range(2, 22, 3):
            p.px(x, 2, 0), p.px(x + 1, 3, 0)
        p.d.line((2, 4, 21, 4), fill=0)
        return p.sprite()
    return _prop("cushion", mk)


def table_spr(w: int = 30, h: int = 16) -> Sprite:
    """供案（侧视）：案面带厚边、牙板一道回纹、两条腿带马蹄足"""
    def mk():
        p = Part(w, h)
        p.shape("rectangle", (0, 0, w - 1, 2), fill=1)
        p.d.line((1, 1, w - 2, 1), fill=0)
        p.shape("rectangle", (2, 3, w - 3, 5), fill=1)
        for x in range(4, w - 4, 4):
            p.px(x, 4, 0), p.px(x + 1, 4, 0)
        for x in (2, w - 5):
            p.shape("rectangle", (x, 6, x + 2, h - 2), fill=1)
            p.px(x + 1, 7, 0)
        p.shape("rectangle", (1, h - 1, 5, h - 1), fill=1)
        p.shape("rectangle", (w - 6, h - 1, w - 2, h - 1), fill=1)
        return p.sprite()
    return _prop(("table", w, h), mk)


# ================================================================ 舞台与文字

def floor(g: Gfx, y: int, phase: float = 0.0):
    """地面线 + 斜向地砖缝 + 稀疏网点（同燃香），phase 让地砖卷动"""
    g.d.line((0, y, 127, y), fill=1)
    off = int(phase) % 16
    for x in range(-40 - off, 168, 16):
        g.d.line((x, y + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, y + 1, 128, 64), 0.125)


def boxed(g: Gfx, x: float, y: float, s: str, size: int = 8, align: str = "left", pop: float = 1.0) -> tuple:
    """带框的小牌子（计数、状态）：先清黑底再画框和字。要在所有特效之后最后画。返回框"""
    w = text_width(s, size)
    hgt = 7 if size == 8 else 11
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    y += (1 - pop) * 8
    box = (x - 3, y - 3, x + w + 2, y + hgt + 2)
    g.d.rectangle(box, fill=0, outline=1)
    g.text(x, y, s, size=size)
    return box


def vbox(g: Gfx, cx: float, y: float, s: str, size: int = 8, hook: bool = True) -> tuple:
    """竖牌（竖排的计数 / 状态，像挂在墙上的木牌）：上面一根挂绳，框里竖排字。最后画"""
    step = (7 if size == 8 else 11) + 1
    w = 8 if size == 8 else 12
    h = len(s) * step - 1
    box = (cx - w / 2 - 3, y - 3, cx + w / 2 + 2, y + h + 2)
    if hook:
        g.d.line((cx - 1, y - 8, cx - 4, y - 4), fill=1)
        g.d.line((cx, y - 8, cx + 3, y - 4), fill=1)
    g.d.rectangle(box, fill=0, outline=1)
    g.vtext(cx - w / 2, y, s, size=size)
    return box


def clear_box(g: Gfx, box):
    """清出一块黑底（白墨层上直接涂黑；g.k 只遮灰度层，挡不住已画的白墨）"""
    g.d.rectangle(box, fill=0)


def rays(g: Gfx, cx: float, cy: float, r0: float, r1: float, n: int = 12, phase: float = 0.0, sy: float = 1.0,
         dash: int = 0):
    """放射光线（sy 压扁）；dash>0 时隔段画"""
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


def ring(g: Gfx, cx: float, cy: float, r: float, step: int = 2, sy: float = 1.0, phase: float = 0.0):
    """点状圆环（光圈外扩）"""
    if r <= 0.5:
        g.px(cx, cy)
        return
    n = max(8, int(2 * math.pi * r))
    for i in range(0, n, step):
        a = i / n * 2 * math.pi + phase
        g.px(round(cx + math.cos(a) * r), round(cy + math.sin(a) * r * sy))


def star4(g: Gfx, x: float, y: float, big: bool = False):
    """四角星闪（金光、灵光点）"""
    g.px(x, y)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        g.px(x + dx, y + dy)
        if big:
            g.px(x + dx * 2, y + dy * 2)


# ================================================================ 点阵

FU_MX = ["########", "#.#..#.#", "########", "#..##..#", "#.####.#", "#..##..#", "#.#..#.#", "########"]


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


def mx_ring(g: Gfx, r: float, cx: float = 3.5, cy: float = 3.5):
    for y in range(8):
        for x in range(8):
            if abs(math.hypot(x - cx, y - cy) - r) < 0.6:
                g.mx[y, x] = True
