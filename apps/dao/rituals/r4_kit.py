"""r4 共用零件（像素风）：会练功的小道士 + 文字牌 + 小特效。

小道士沿用 engine/chars.py 的头、袍子画法与比例，但手臂、腿、上身俯仰都可以摆：
    P(legs="horse", crouch=2, b=(a1, a2, "palm"), f=(a1, a2, "fist"), lean=10, head="up", face="normal")
    dao(g, x, FLOOR, P, t)          # (x, FLOOR) = 两脚中点；朝右，flip=True 朝左；返回各点屏幕坐标
手臂角度：0 朝前（右）、90 向下、-90 向上、180 朝后；a1 上臂、a2 小臂（绝对角度）。
b = 远侧（后面那只）手臂，f = 近侧手臂。手型：palm 掌 / fist 拳 / sword 剑指 / claw 虎爪 / horn 鹿角 /
hook 猿钩 / up 立掌（指尖朝上）/ wing 鸟翅（袖子展开成羽）。
姿势在模块级用关键帧定义，seq(keys, t) 在关键帧之间插值（角度就近插值，再按 8° 量化后缓存精灵）。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in_out, lerp
from ..engine.chars import Part, _feet, _head, _kneel_legs, _sit_legs
from ..engine.gfx import Gfx, Sprite, text_width

_C: dict = {}


def cached(key, fn):
    v = _C.get(key)
    if v is None:
        v = _C[key] = fn()
    return v


# ---------------------------------------------------------------- 头：表情 / 口型 / 眉

def head(face="normal", blink=False, bow=False, mouth=None, brow=False) -> Sprite:
    """chars 的头，外加口型（六字诀）和怒目的眉"""
    def mk():
        f = face if face in ("normal", "sleep", "happy", "wow") else "normal"
        spr = _head(blink, 0, bow, f)[0]
        if bow or (mouth is None and not brow and face == f):
            return spr
        on, mk_ = spr.on.copy(), spr.mask.copy()
        ex = 8
        if face == "angry":  # 怒目：圆眼 + 压低的眉
            on[10:13, ex:ex + 2] = False
            on[10:13, ex + 4:ex + 6] = False
            on[11, ex] = on[11, ex + 4] = True
        if brow or face == "angry":
            for x, y in ((ex - 1, 8), (ex, 9), (ex + 1, 9), (ex + 4, 9), (ex + 5, 9), (ex + 6, 8)):
                on[y, x] = False
        if mouth:
            on[14, ex + 2:ex + 4] = True     # 擦掉原来的嘴
            if mouth == "o":      # 呼 / 吹：圆口
                on[13:16, ex + 2:ex + 4] = False
                on[14, ex + 2] = on[14, ex + 3] = True
                on[14, ex + 2] = False
            elif mouth == "open":  # 呵：张大口
                on[13:16, ex + 1:ex + 5] = False
            elif mouth == "flat":  # 嘘 / 呬：抿开（齿间出气）
                on[14, ex + 1:ex + 5] = False
            elif mouth == "smile":  # 嘻
                on[14, ex + 1:ex + 5] = False
                on[13, ex] = on[13, ex + 5] = False
                on[15, ex + 2:ex + 4] = False
            elif mouth == "dot":
                on[14, ex + 3] = False
        return Sprite(on=on, mask=mk_)
    return cached(("head", face, blink, bow, mouth, brow), mk)


# ---------------------------------------------------------------- 手臂（逐像素生成，缓存）

def _q(a, step=8):
    return int(round(a / step)) * step


def arm(a1: float, a2: float, hand: str = "palm", L1: float = 5, L2: float = 5, ext: int = 0) -> Sprite:
    """一只手臂精灵：上臂 + 宽袖小臂 + 手。.sh = 肩在精灵里的坐标，.hand = 手的坐标"""
    a1, a2 = _q(a1), _q(a2)
    if a1 < -30:            # 举过肩：Q 版手臂拉长，手才够得到头顶
        L1, L2 = L1 + 2, L2 + 3
    L1, L2 = L1 + ext // 2, L2 + ext - ext // 2
    return cached(("arm", a1, a2, hand, L1, L2), lambda: _arm(a1, a2, hand, L1, L2))


def _arm(a1, a2, hand, L1, L2):
    M = 9
    r1, r2 = math.radians(a1), math.radians(a2)
    sx, sy = 0.0, 0.0
    ex, ey = L1 * math.cos(r1), L1 * math.sin(r1)
    wx, wy = ex + L2 * math.cos(r2), ey + L2 * math.sin(r2)
    ux, uy = math.cos(r2), math.sin(r2)          # 小臂方向
    hx, hy = wx + ux * 2.2, wy + uy * 2.2           # 手心
    xs = [sx, ex, wx, hx]
    ys = [sy, ey, wy, hy]
    x0, y0 = math.floor(min(xs)) - M, math.floor(min(ys)) - M
    w, h = math.ceil(max(xs)) - x0 + M + 1, math.ceil(max(ys)) - y0 + M + 1
    p = Part(w, h)
    S = lambda x, y: (x - x0, y - y0)  # noqa: E731
    # 上臂（袖筒）
    p.shape("line", [S(sx, sy), S(ex, ey)], fill=1, width=4)
    p.shape("ellipse", (S(sx, sy)[0] - 2, S(sx, sy)[1] - 2, S(sx, sy)[0] + 2, S(sx, sy)[1] + 2), fill=1)
    p.shape("ellipse", (S(ex, ey)[0] - 2, S(ex, ey)[1] - 2, S(ex, ey)[0] + 2, S(ex, ey)[1] + 2), fill=1)
    # 小臂 + 宽袖：袖子朝重力方向垂下，越靠袖口越宽
    p.shape("line", [S(ex, ey), S(wx, wy)], fill=1, width=4)
    nx, ny = -uy, ux                                  # 小臂法线
    if ny < 0:
        nx, ny = -nx, -ny                             # 取朝下的一侧
    droop = max(0.0, ny) * (1 - abs(uy) * 0.55)       # 小臂越平，袖子垂得越多
    if hand == "wing":
        droop = 1.0
    depth = 1.5 + 3.2 * droop
    if depth > 1.6:
        pts = []
        for k in (0.15, 0.5, 1.0):
            px, py = ex + (wx - ex) * k, ey + (wy - ey) * k
            d = 1.5 + (depth - 1.5) * k
            pts.append((px + nx * (d + 1), py + max(ny, 0.6) * (d + 1)))
        poly = [S(ex, ey), S(wx, wy)] + [S(*q) for q in reversed(pts)]
        p.shape("polygon", poly, fill=1)
    if hand == "wing":  # 鸟翅：袖下挂一排羽
        for k in (0.0, 0.33, 0.66, 1.0):
            bx, by = sx + (wx - sx) * k, sy + (wy - sy) * k
            p.shape("line", [S(bx, by), S(bx - ux * 1, by + 6 - k * 2)], fill=1, width=2)
    # 袖口镶边（垂直于小臂的一道暗线）
    cx, cy = wx - ux * 1.2, wy - uy * 1.2
    p.d.line([S(cx - nx * 1.5, cy - ny * 1.5), S(cx + nx * (depth + 0.5), cy + ny * (depth + 0.5))], fill=0)
    # 背光面网点（袖子下半）
    if depth > 1.6:
        poly2 = [S(ex + nx * 1.5, ey + ny * 1.5), S(wx + nx * 1.5, wy + ny * 1.5)] + \
                [S(wx + nx * (depth + 2), wy + max(ny, 0.6) * (depth + 2)), S(ex + nx * 3, ey + ny * 3)]
        p.dither(poly2, 0.5, 0)
    # 手
    _hand(p, S(hx, hy), ux, uy, hand)
    spr = p.sprite()
    spr.sh = S(sx, sy)
    spr.hand = tuple(int(round(v)) for v in S(hx + ux * 1.5, hy + uy * 1.5))
    return spr


def _hand(p: Part, c, ux, uy, kind):
    cx, cy = c
    rx, ry = int(round(cx)), int(round(cy))
    if kind == "wing":
        p.shape("rectangle", (rx - 1, ry - 1, rx + 1, ry + 1), fill=1)
        return
    if kind in ("palm", "fist", "claw", "horn", "hook", "sword", "up", "down"):
        p.shape("rectangle", (rx - 1, ry - 1, rx + 1, ry + 1), fill=1)
    fx, fy = rx + int(round(ux * 2)), ry + int(round(uy * 2))   # 指尖方向
    if kind == "palm":
        p.px(fx, fy)
        p.px(rx + int(round(ux)) - int(round(uy)), ry + int(round(uy)) + int(round(ux)))
    elif kind == "fist":
        p.shape("rectangle", (rx - 1, ry - 1, rx + 2, ry + 2), fill=1)
        p.px(rx + 1, ry, 0), p.px(rx, ry + 1, 0)                 # 指节
    elif kind == "sword":
        p.shape("line", [(rx, ry), (rx + int(round(ux * 5)), ry + int(round(uy * 5)))], fill=1, width=1)
        p.shape("line", [(rx + int(round(-uy)), ry + int(round(ux))),
                         (rx + int(round(ux * 4 - uy)), ry + int(round(uy * 4 + ux)))], fill=1)
    elif kind == "claw":  # 虎爪：五指张开弯曲
        for k in (-1, 0, 1):
            ox, oy = int(round(-uy * k * 1.6)), int(round(ux * k * 1.6))
            p.px(fx + ox, fy + oy)
            p.px(fx + ox + int(round(ux)) + int(round(uy * 0.7)), fy + oy + int(round(uy)) - int(round(ux * 0.7)))
    elif kind == "horn":  # 鹿角：拇指外撑，食指小指伸直，中指无名指弯
        for k in (-1, 1):
            ox, oy = int(round(-uy * k * 1.5)), int(round(ux * k * 1.5))
            p.shape("line", [(fx + ox, fy + oy), (fx + ox * 2 + int(round(ux * 2)), fy + oy * 2 + int(round(uy * 2)))],
                    fill=1)
    elif kind == "hook":  # 猿钩：五指撮拢、腕下屈
        p.px(rx + int(round(ux * 2)), ry + 2)
        p.px(rx + int(round(ux * 2)), ry + 3)
    elif kind == "up":    # 立掌：指尖朝上
        p.shape("rectangle", (rx, ry - 4, rx + 1, ry), fill=1)
        p.px(rx - 1, ry - 2, 1)
    elif kind == "down":  # 按掌：掌心朝下、指尖朝前
        p.shape("rectangle", (rx - 1, ry, rx + 3, ry + 1), fill=1)


# ---------------------------------------------------------------- 身体

_TORSO = [(-3, -18), (3, -18), (5, -12), (5.4, -11)]  # 右半（相对脚底中点，朝右）
WAIST = (0, -11)


def _rot(px, py, ang, ox=0.0, oy=-11.0):
    a = math.radians(ang)
    dx, dy = px - ox, py - oy
    return ox + dx * math.cos(a) - dy * math.sin(a), oy + dx * math.sin(a) + dy * math.cos(a)


def body(lean: int, breath: bool, skirt: str = "stand") -> Sprite:
    """袍子（上身可以俯仰 lean 度；下摆按腿型张开）。.o = 脚底中点在精灵里的坐标"""
    lean = _q(lean, 6)
    return cached(("body", lean, breath, skirt), lambda: _body(lean, breath, skirt))


def _body(lean, breath, skirt):
    W_, H_ = 44, 34
    ox, oy = 22, 31
    p = Part(W_, H_)
    S = lambda x, y: (x + ox, y + oy)  # noqa: E731
    top = -18 + (1 if breath else 0)
    up = [(-5.4, -11), (-5, -12), (-3, top), (3, top), (5, -12), (5.4, -11)]
    up = [S(*_rot(x, y, lean)) for x, y in up]
    hem = {"stand": 7, "horse": 8, "bow": 8, "tiptoe": 7, "kneel": 7}.get(skirt, 7)
    bot = -4 if skirt != "kneel" else -2
    sk = [(-5.4, -11), (5.4, -11), (hem, bot), (-hem, bot)]
    if skirt == "bow":
        sk = [(-5.4, -11), (5.4, -11), (9, bot), (-6, bot)]
    p.shape("polygon", [S(*q) for q in sk], fill=1)
    p.shape("polygon", up, fill=1)
    # 交领（右衽）
    a = S(*_rot(-1, top, lean))
    b = S(*_rot(3, -13, lean))
    p.d.line([a, b], fill=0)
    # 腰带与结
    p.d.line([S(*_rot(-5, -11, lean * 0.5)), S(*_rot(5, -11, lean * 0.5))], fill=0)
    k = S(*_rot(0, -11, lean * 0.5))
    p.px(int(k[0]), int(k[1]), 1), p.px(int(k[0]), int(k[1]) + 1, 0), p.px(int(k[0]) - 1, int(k[1]) + 1, 0)
    # 下摆镶边
    p.d.line([S(-hem + 0.5, bot - 2), S(hem - 0.5, bot - 2)], fill=0)
    if skirt in ("horse", "bow"):  # 马步 / 弓步：前后襟分开
        p.d.line([S(0, bot - 1), S(0, bot - 5)], fill=0)
        p.px(int(S(0, 0)[0]), int(S(0, bot)[1]), 0)
    # 背光面
    p.dither([S(5, -9), S(hem, bot), S(hem - 2, bot), S(3, -9)], 0.5, 0)
    spr = p.sprite()
    spr.o = (ox, oy)
    spr.neck = _rot(0, top, lean)
    spr.sb = _rot(-3, top + 2, lean)     # 远侧肩
    spr.sf = _rot(2, top + 2, lean)      # 近侧肩
    return spr


def legs(kind: str) -> Sprite:
    """腿与鞋。.o = 脚底中点在精灵里的坐标"""
    return cached(("legs", kind), lambda: _legs(kind))


def _shoe(p: Part, x, y, flip=False, tip=False):
    """圆头布鞋 5×3（tip：踮脚，只剩鞋尖着地）"""
    if tip:
        p.shape("polygon", [(x, y - 3), (x + 2, y - 3), (x + 4, y), (x + 1, y)], fill=1)
        return
    p.shape("ellipse", (x, y - 2, x + 4, y), fill=1)
    p.px(x + (0 if flip else 4), y, 0)


def _legs(kind):
    W_, H_ = 34, 18
    ox, oy = 17, 17
    p = Part(W_, H_)
    S = lambda x, y: (x + ox, y + oy)  # noqa: E731

    def leg(hip, knee, foot, tip=False):
        p.shape("line", [S(*hip), S(*knee)], fill=1, width=3)
        p.shape("line", [S(*knee), S(*foot)], fill=1, width=3)
        fx, fy = S(*foot)
        _shoe(p, int(fx) - 2, int(fy), tip=tip)

    if kind == "stand":
        _shoe(p, *[int(v) for v in S(-6, 0)])
        _shoe(p, *[int(v) for v in S(2, 0)])
    elif kind == "tiptoe":   # 提踵
        _shoe(p, *[int(v) for v in S(-6, 0)], tip=True)
        _shoe(p, *[int(v) for v in S(2, 0)], tip=True)
        p.shape("rectangle", S(-5, -5) + S(-4, -3), fill=1)
        p.shape("rectangle", S(3, -5) + S(4, -3), fill=1)
    elif kind == "horse":    # 马步：两脚开立，屈膝外撑
        leg((-3, -6), (-9, -4), (-10, 0))
        leg((3, -6), (9, -4), (10, 0))
    elif kind == "wide":     # 开步站立
        leg((-3, -6), (-6, -3), (-7, 0))
        leg((3, -6), (6, -3), (7, 0))
    elif kind == "bow":      # 弓步（右腿在前屈膝，左腿在后蹬直）
        leg((3, -6), (10, -5), (10, 0))
        leg((-3, -6), (-8, -3), (-12, 0))
    elif kind == "bowl":     # 反弓步（左腿在前）——身体后坐
        leg((-3, -6), (-10, -5), (-10, 0))
        leg((3, -6), (7, -3), (10, 0))
    elif kind == "empty":    # 虚步：前脚尖点地
        leg((-3, -6), (-5, -3), (-5, 0))
        leg((3, -6), (8, -3), (9, 0), tip=True)
    elif kind == "knee":     # 提膝（右膝提到腰）
        _shoe(p, *[int(v) for v in S(-4, 0)])
        p.shape("rectangle", S(-3, -5) + S(-1, -1), fill=1)
        p.shape("line", [S(2, -9), S(9, -10)], fill=1, width=4)
        p.shape("line", [S(9, -10), S(9, -4)], fill=1, width=3)
        _shoe(p, *[int(v) for v in S(8, -2)], tip=True)
    elif kind == "back":     # 后撩腿（左腿向后上抬）
        _shoe(p, *[int(v) for v in S(0, 0)])
        p.shape("rectangle", S(1, -5) + S(3, -1), fill=1)
        p.shape("line", [S(-3, -7), S(-13, -10)], fill=1, width=3)
        p.shape("polygon", [S(-13, -12), S(-16, -9), S(-15, -8), S(-12, -10)], fill=1)
    elif kind == "step":     # 侧行一步（云手）
        leg((-3, -6), (-5, -3), (-6, 0))
        leg((3, -6), (4, -3), (4, 0))
    elif kind == "single":   # 独立（左脚着地，右脚尖虚点身旁）
        _shoe(p, *[int(v) for v in S(-3, 0)])
        p.shape("rectangle", S(-2, -5) + S(0, -1), fill=1)
        p.shape("line", [S(3, -6), S(5, -2)], fill=1, width=3)
        _shoe(p, *[int(v) for v in S(4, 0)], tip=True)
    p.d.line([S(-1, -9), S(1, -9)], fill=1)
    spr = p.sprite()
    spr.o = (ox, oy)
    return spr


FRONT_LEGS = {"knee"}
SKIRT = {"horse": "horse", "bow": "bow", "bowl": "bow", "wide": "horse", "tiptoe": "tiptoe", "kneel": "kneel"}
CROUCH = {"horse": 3, "bow": 2, "bowl": 2, "wide": 1, "empty": 1, "step": 1, "knee": 0, "back": 0}


class P(dict):
    """一个姿势（可插值的字典）"""

    def __init__(self, legs="stand", b=(100, 90, "palm"), f=(80, 90, "palm"), lean=0, crouch=None, rise=0,
                 head="up", face="normal", mouth=None, flip_head=False, **kw):
        super().__init__(legs=legs, b=tuple(b), f=tuple(f), lean=lean,
                         crouch=CROUCH.get(legs, 0) if crouch is None else crouch, rise=rise,
                         head=head, face=face, mouth=mouth, flip_head=flip_head, **kw)


def _angmix(a, b, k):
    d = (b - a + 180) % 360 - 180
    return a + d * k


def mix(p: P, q: P, k: float) -> P:
    out = P()
    for key in set(p) | set(q):
        a, b = p.get(key), q.get(key)
        if key in ("b", "f"):
            out[key] = (_angmix(a[0], b[0], k), _angmix(a[1], b[1], k), a[2] if k < 0.5 else b[2])
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
            out[key] = a + (b - a) * k
        else:
            out[key] = a if k < 0.5 else b
    return out


def seq(keys, t: float, loop: bool = True) -> P:
    """keys = [(时刻, 姿势), ...]（最后一个时刻 = 循环长度）；在关键帧之间缓动插值"""
    T = keys[-1][0]
    if loop:
        t = t % T
    else:
        t = min(max(t, 0.0), T)
    for i in range(len(keys) - 1):
        t0, p0 = keys[i]
        t1, p1 = keys[i + 1]
        if t0 <= t <= t1:
            k = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return mix(p0, p1, ease_in_out(k))
    return keys[-1][1]


def dao(g: Gfx, x: float, y: float, pose: P, t: float = 0.0, flip: bool = False, bob: bool = True,
        front=None, behind=None) -> dict:
    """画一个练功的小道士。返回屏幕坐标：hb / hf 两只手、head 头心、belly 丹田、chest、brow、mouth、top 头顶"""
    x, y = int(round(x)), int(round(y))
    lg = pose["legs"]
    breath = bob and (t * 0.7) % 1 > 0.5 and lg not in ("sit", "kneel")
    yb = y - int(round(pose["crouch"])) - int(round(pose["rise"]))
    sgn = -1 if flip else 1

    def at(ox, oy, spr, base_y=yb):
        """以 (ox, oy)（相对 (x, base_y)，朝右坐标）贴精灵左上角"""
        px = x + ox if not flip else x - ox - spr.w + 1
        pix.blit(g, spr, px, base_y + oy, flip=flip)

    def pt(ox, oy, base_y=yb):
        return (x + sgn * ox, base_y + oy)

    lean = pose["lean"]
    if lg == "sit":
        bd = body(lean, bob and (t * 0.7) % 1 > 0.5, "kneel")
        yb = y + 2
    elif lg == "kneel":
        bd = body(lean, False, "kneel")
        yb = y + 2
    else:
        bd = body(lean, breath, SKIRT.get(lg, "stand"))
    out = {}
    if behind:
        behind(g, at, pt)
    b1, b2, bh = pose["b"][:3]
    f1, f2, fh = pose["f"][:3]
    sb = bd.sb
    sf = bd.sf
    armb = arm(b1, b2, bh, ext=pose.get("ext", 0))
    armf = arm(f1, f2, fh, ext=pose.get("ext", 0))
    over = False                  # 手臂一律画在头后面（举过头时不挡脸）
    b_over = b1 < -30 and not pose["flip_head"]   # 远侧手臂举过头：压在后脑勺上（不挡脸），看得清

    def draw_back_arm():
        at(int(round(sb[0])) - armb.sh[0], int(round(sb[1])) - armb.sh[1], armb)
        out["hb"] = pt(int(round(sb[0])) - armb.sh[0] + armb.hand[0], int(round(sb[1])) - armb.sh[1] + armb.hand[1])

    if not b_over:
        draw_back_arm()
    # 腿
    if lg == "sit":
        at(-11, -5, cached(("sitlegs",), _sit_legs), y)
    elif lg == "kneel":
        at(-9, -5, cached(("kneellegs",), _kneel_legs), y)
    elif lg not in FRONT_LEGS:
        L = legs(lg)
        at(-L.o[0], -L.o[1], L, y - int(round(pose["rise"])))
    at(-bd.o[0], -bd.o[1], bd)
    if lg in FRONT_LEGS:  # 提膝：腿压在袍子前面
        L = legs(lg)
        at(-L.o[0], -L.o[1], L, y - int(round(pose["rise"])))
    # 头
    hd = pose["head"]
    nx, ny = bd.neck
    blink = pose["face"] == "normal" and (t % 3.7) < 0.12
    if hd == "bow":
        hs = head(bow=True)
        hx, hy = nx - 8 + 2, ny - 13 + 3
    else:
        hs = head(pose["face"], blink, False, pose["mouth"], False)
        hx, hy = nx - 8 + max(0, lean - 10) * 0.12, ny - 15 + max(0, lean - 10) * 0.25
        if hd == "tilt":
            hy += 1
    if pose["flip_head"]:  # 往后瞧：头转向身后
        hs_draw = hs.flip()
        hs_draw = cached(("hflip", pose["face"], blink, pose["mouth"]), lambda: hs.flip())
        hx -= 1
    else:
        hs_draw = hs

    def draw_front_arm():
        at(int(round(sf[0])) - armf.sh[0], int(round(sf[1])) - armf.sh[1], armf)
        out["hf"] = pt(int(round(sf[0])) - armf.sh[0] + armf.hand[0], int(round(sf[1])) - armf.sh[1] + armf.hand[1])

    if not over:
        draw_front_arm()
    at(int(round(hx)), int(round(hy)), hs_draw)
    if over:
        draw_front_arm()
    if b_over:
        draw_back_arm()
    if front:
        front(g, at, pt)
    hx_c = hx + 8.5
    out["head"] = pt(hx_c, hy + 9)
    out["top"] = pt(hx_c, hy)
    out["brow"] = pt(hx_c + 3, hy + 9)
    out["mouth"] = pt(hx_c + 2 if not pose["flip_head"] else hx_c - 4, hy + 14)
    out["nose"] = pt(hx_c + 7 if not pose["flip_head"] else hx_c - 8, hy + 12)
    out["chest"] = pt(*_rot(0, -14, lean))
    out["belly"] = pt(0, -8)
    out["neck"] = pt(nx, ny)
    return out


# ---------------------------------------------------------------- 文字牌（最后画，底板挖黑，不和画面堆叠）

def label(g: Gfx, x: float, y: float, s: str, size: int = 12, align: str = "left", box: bool = True,
          pad: int = 2, scale: int = 1) -> tuple:
    """带黑底板（可选边框）的文字。返回底板范围"""
    w = text_width(s, size) * scale
    hgt = (11 if size == 12 else 7) * scale
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    x, y = int(round(x)), int(round(y))
    bx = (x - pad - 1, y - pad - 1, x + w + pad, y + hgt + pad)
    g.d.rectangle(bx, fill=0)
    if box:
        g.d.rectangle(bx, outline=1)
    g.text(x, y, s, size=size, scale=scale)
    return bx


def counter(g: Gfx, s: str, x: int = 4, y: int = 3, right: bool = False):
    """角上的小牌（第几转 / 第几遍），8px"""
    w = text_width(s, 8)
    if right:
        x = 127 - x - w - 4
    g.d.rectangle((x, y - 2, x + w + 3, y + 8), fill=0, outline=1)
    g.text(x + 2, y, s, size=8)


def pop_title(g: Gfx, cx: float, y: float, s: str, k: float, t: float):
    """圆满时弹出的大字牌：缓动弹出 + 两边闪星"""
    from ..engine.anim import ease_out_back
    pop = ease_out_back(min(max(k, 0.0), 1.0))
    yy = y + (1 - pop) * 10
    w = text_width(s)
    bx = label(g, cx, yy, s, 12, "center", True, 2)
    if int(t * 6) % 2 == 0:
        for sx, sy in ((bx[0] - 4, yy + 5), (bx[2] + 4, yy + 5)):
            star(g, sx, sy, 1)
    return bx


# ---------------------------------------------------------------- 小特效

def star(g: Gfx, x: float, y: float, size: int = 1):
    """十字闪星：size 1 = 5 像素十字，2 = 带斜角的大星"""
    x, y = int(round(x)), int(round(y))
    g.px(x, y)
    for d in range(1, size + 1):
        g.px(x - d, y), g.px(x + d, y), g.px(x, y - d), g.px(x, y + d)
    if size >= 2:
        g.px(x - 1, y - 1, 0) if False else None
        for d in (1,):
            g.px(x - d, y - d), g.px(x + d, y + d), g.px(x + d, y - d), g.px(x - d, y + d)
        g.px(x - 3, y), g.px(x + 3, y), g.px(x, y - 3), g.px(x, y + 3)


def orb(g: Gfx, x: float, y: float, r: int = 1, t: float = 0.0):
    """发光的气团：实心小圆 + 一圈闪烁的光点"""
    x, y = int(round(x)), int(round(y))
    g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
    k = int(t * 8) % 2
    rr = r + 2
    for i in range(8):
        if (i + k) % 2 == 0:
            a = i * math.pi / 4
            g.px(x + round(math.cos(a) * rr), y + round(math.sin(a) * rr))


def ring(g: Gfx, x: float, y: float, r: float, dotted: int = 0, ry: float | None = None):
    ry = r if ry is None else ry
    if r < 0.5:
        g.px(x, y)
        return
    if not dotted:
        g.d.ellipse((x - r, y - ry, x + r, y + ry), outline=1)
        return
    n = max(8, int(r * 6.3 / dotted))
    for i in range(n):
        a = i / n * 2 * math.pi
        g.px(x + math.cos(a) * r, y + math.sin(a) * ry)


class Clock:
    """帧间 dt（t 回到 0 时重置）"""

    def __init__(self):
        self.last = None

    def __call__(self, t: float) -> float:
        dt = 1 / 30 if self.last is None or t < self.last else min(t - self.last, 0.2)
        self.last = t
        return dt


def ticked(t: float, dt: float, period: float, phase: float = 0.0) -> bool:
    """t 跨过 period 的整数倍（定时事件）"""
    return int((t + phase) / period) != int((t + phase - dt) / period) and t - dt >= 0


def mx_art(g: Gfx, art: str, x: int = 0, y: int = 0):
    rows = [r for r in art.strip("\n").split("\n")]
    for j, r in enumerate(rows):
        for i, ch in enumerate(r.strip()):
            if ch == "#" and 0 <= y + j < 8 and 0 <= x + i < 8:
                g.mx[y + j, x + i] = True


def mx_ring(g: Gfx, r: float):
    for yy in range(8):
        for xx in range(8):
            if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.6:
                g.mx[yy, xx] = True


def grass(g: Gfx, x: int, y: int, t: float = 0.0, k: int = 0):
    """一小簇草（随风轻摆）"""
    s = 1 if math.sin(t * 1.3 + x * 0.7) > 0.6 else 0
    for i, (dx, hgt) in enumerate(((0, 3), (2, 4), (4, 2))):
        g.d.line((x + dx, y, x + dx + (s if i == 1 else 0), y - hgt), fill=1)


def lerp_pt(a, b, k):
    return (lerp(a[0], b[0], k), lerp(a[1], b[1], k))


__all__ = ["P", "dao", "seq", "mix", "arm", "head", "label", "counter", "pop_title", "star", "orb", "ring",
           "Clock", "ticked", "mx_art", "mx_ring", "grass", "cached", "lerp_pt", "np"]


# ---------------------------------------------------------------- 特殊姿势：俯身攀足（逐像素整身精灵）

def fold_sprite() -> Sprite:
    """俯身攀足：腿直立，上身折到腿前，头朝下，两手攀住脚尖。.o = 脚底中点"""
    def mk():
        p = Part(30, 26)
        # 腿（直）+ 鞋
        p.shape("rectangle", (9, 13, 12, 23), fill=1)
        p.d.line((10, 15, 10, 22), fill=0)
        p.shape("ellipse", (8, 22, 14, 25), fill=1)
        p.px(8, 25, 0)
        # 袍子下摆：从后腰垂下盖住大腿
        p.shape("polygon", [(4, 8), (12, 8), (13, 17), (3, 18)], fill=1)
        p.d.line((4, 16, 12, 16), fill=0)
        p.dither([(3, 12), (7, 12), (7, 18), (3, 18)], 0.5, 0)
        # 上身：从腰拱起、向前下折
        p.shape("polygon", [(5, 9), (6, 4), (11, 1), (17, 2), (21, 6), (20, 10), (9, 12)], fill=1)
        p.d.line((7, 3, 7, 11), fill=0)                  # 腰带
        p.px(6, 7, 1), p.px(5, 8, 0)
        p.d.line((16, 3, 19, 8), fill=0)                 # 交领
        p.dither([(9, 10), (20, 10), (20, 11), (9, 12)], 0.5, 0)
        # 手臂（垂到脚尖）
        p.shape("line", [(18, 7), (17, 21)], fill=1, width=4)
        p.shape("polygon", [(15, 13), (19, 13), (21, 21), (14, 21)], fill=1)
        p.d.line((14, 20, 21, 20), fill=0)
        p.shape("rectangle", (15, 22, 18, 24), fill=1)
        p.px(18, 24, 0)
        spr = p.sprite()
        # 头倒挂在腿前：头顶（发髻）朝下
        hd = head(bow=True).rot90(2)
        on, mk_ = spr.on.copy(), spr.mask.copy()
        H_, W_ = on.shape
        big_on = np.zeros((H_ + 2, W_ + 2), bool)
        big_mk = np.zeros((H_ + 2, W_ + 2), bool)
        big_on[:H_, :W_], big_mk[:H_, :W_] = on, mk_
        hx, hy = 12, 6
        hm = hd.mask
        # 头外描一圈黑边再贴上（和身体分开）
        grow = np.pad(hm, 1)
        g2 = grow.copy()
        g2[1:, :] |= grow[:-1, :]
        g2[:-1, :] |= grow[1:, :]
        g2[:, 1:] |= grow[:, :-1]
        g2[:, :-1] |= grow[:, 1:]
        oy0, ox0 = hy - 1, hx - 1
        sub_on = big_on[oy0:oy0 + g2.shape[0], ox0:ox0 + g2.shape[1]]
        sub_on[g2[:sub_on.shape[0], :sub_on.shape[1]]] = False
        big_mk[oy0:oy0 + g2.shape[0], ox0:ox0 + g2.shape[1]] |= g2[:sub_on.shape[0], :sub_on.shape[1]]
        reg = big_on[hy:hy + hd.h, hx:hx + hd.w]
        m = hm[:reg.shape[0], :reg.shape[1]]
        reg[m] = hd.on[:reg.shape[0], :reg.shape[1]][m]
        s2 = Sprite(on=big_on, mask=big_mk)
        s2.o = (11, 25)
        return s2
    return cached(("fold",), mk)


def fold(g: Gfx, x: float, y: float, flip: bool = False):
    s = fold_sprite()
    px = x - s.o[0] if not flip else x + s.o[0] - s.w + 1
    pix.blit(g, s, px, y - s.o[1], flip=flip)


# ---------------------------------------------------------------- 院子背景（八段锦 / 五禽戏 / 太极 / 六字诀共用）

def _pine():
    """院墙外的松树 34×32：虬曲的干、四层平展的针叶团（顶边针尖、底边一道暗线和一排网点）"""
    p = Part(34, 32)
    p.shape("polygon", [(15, 31), (19, 31), (18, 25), (20, 18), (17, 11), (15, 12), (17, 18), (15, 25)], fill=1)
    p.d.line((17, 20, 18, 26), fill=0)
    p.shape("line", (18, 18, 26, 15), fill=1, width=2)
    p.shape("line", (16, 12, 9, 9), fill=1, width=2)
    p.shape("line", (16, 23, 8, 20), fill=1, width=2)
    for cx, cy, w in ((10, 7, 8), (25, 13, 7), (17, 3, 6), (7, 18, 6)):
        p.shape("ellipse", (cx - w, cy - 2, cx + w, cy + 3), fill=1)
        for k in range(-w + 1, w, 2):                     # 针尖
            p.px(cx + k, cy - 3)
        p.d.line((cx - w + 2, cy + 2, cx + w - 2, cy + 2), fill=0)
        for k in range(-w + 2, w - 1, 2):
            p.px(cx + k, cy + 3, 0)
        p.px(cx - w + 2, cy - 1, 0), p.px(cx - w + 4, cy, 0)
    return p.sprite()


def _moon_gate():
    """月洞窗 15×15：圆框 + 冰裂纹窗棂"""
    p = Part(15, 15)
    p.shape("ellipse", (0, 0, 14, 14), fill=1)
    p.d.ellipse((2, 2, 12, 12), fill=0)
    for a, b in (((7, 2), (7, 12)), ((2, 7), (12, 7)), ((4, 4), (7, 7)), ((10, 10), (7, 7))):
        p.d.line(a + b, fill=1)
    return p.sprite()


def courtyard(g: Gfx, t: float, floor: int = 58, pine_x: int = 96, wall: bool = True, window_x: int = 8):
    """道观院子：石板地、院墙（瓦檐 + 月洞窗）、墙外一棵松、远山"""
    g.d.line((0, floor, 127, floor), fill=1)
    for x in range(-8, 140, 22):                          # 石板缝
        g.d.line((x, floor + 2, x - 4, 63), fill=1)
    pix.checker(g, (0, floor + 2, 128, 64), 0.125)
    if wall:
        wy = floor - 20
        for x in range(0, 128, 2):                        # 远山（点线）
            y = wy - 8 - 5 * math.sin(x * 0.045 + 1.0) - 2 * math.sin(x * 0.13)
            g.px(x, y)
        pix.blit(g, cached(("pine",), _pine), pine_x, wy - 29)
        g.d.rectangle((0, wy, 127, wy + 1), fill=1)       # 瓦檐：筒瓦一垄一垄
        for x in range(0, 128, 3):
            g.px(x, wy - 1)
        g.d.line((0, wy + 2, 127, wy + 2), fill=0)
        for x in range(1, 128, 3):
            g.px(x, wy + 2)
        g.d.line((0, wy + 4, 127, wy + 4), fill=1)
        g.d.line((0, floor - 3, 127, floor - 3), fill=1)  # 墙脚
        if window_x is not None:
            pix.blit(g, cached(("moongate",), _moon_gate), window_x, wy + 6)


BIRD = pix.frames("""
#   #
 # #
  #
---
 ###
# # #
  #
""")


def bird(g: Gfx, x: float, y: float, t: float):
    pix.blit(g, pix.anim(BIRD, t, 5), x - 2, y - 1, outline=False)


def leaf_fall(g: Gfx, x0: float, y0: float, k: float, floor: int = 58):
    """一片松针 / 叶子飘落（k ∈ [0,1]）"""
    if 0 <= k < 1:
        x = x0 + math.sin(k * 9) * 4 - k * 6
        y = y0 + k * (floor - y0)
        g.px(x, y), g.px(x + (1 if int(k * 9) % 2 else -1), y + 1)


def hand_pos(x: float, y: float, pose: P, flip: bool = False) -> dict:
    """不画，只算两只手的屏幕坐标（画手的轨迹用）"""
    x, y = int(round(x)), int(round(y))
    lg = pose["legs"]
    yb = y - int(round(pose["crouch"])) - int(round(pose["rise"]))
    if lg in ("sit", "kneel"):
        yb = y + 2
        bd = body(pose["lean"], False, "kneel")
    else:
        bd = body(pose["lean"], False, SKIRT.get(lg, "stand"))
    sgn = -1 if flip else 1
    out = {}
    for key, s in (("hb", bd.sb), ("hf", bd.sf)):
        a1, a2, hd = pose["b" if key == "hb" else "f"][:3]
        spr = arm(a1, a2, hd, ext=pose.get("ext", 0))
        ox = int(round(s[0])) - spr.sh[0] + spr.hand[0]
        oy = int(round(s[1])) - spr.sh[1] + spr.hand[1]
        if flip:
            ox = int(round(s[0])) - spr.sh[0]
            ox = -(ox + spr.w - 1) + (spr.w - 1 - spr.hand[0])
            out[key] = (x + ox, yb + oy)
        else:
            out[key] = (x + ox, yb + oy)
    return out


# ---------------------------------------------------------------- 远峰 / 云海（六字诀、采日月共用）

MOUNTS = {
    1: (46, 26, [(0, 25), (6, 18), (9, 19), (15, 10), (18, 11), (23, 0), (27, 6), (30, 5), (35, 13), (38, 12), (45, 25)],
        [(23, 0), (27, 6), (30, 5), (35, 13), (38, 12), (45, 25), (29, 25), (25, 12)],
        [((14, 13), (17, 16)), ((8, 20), (11, 22)), ((20, 5), (21, 9)), ((18, 15), (20, 19))]),
    2: (30, 18, [(0, 17), (5, 11), (8, 12), (13, 3), (15, 0), (19, 6), (22, 5), (29, 17)],
        [(15, 0), (19, 6), (22, 5), (29, 17), (18, 17), (16, 8)], [((10, 8), (12, 11)), ((5, 14), (7, 16))]),
    3: (23, 13, [(0, 12), (6, 6), (9, 7), (12, 0), (16, 5), (22, 12)],
        [(12, 0), (16, 5), (22, 12), (14, 12), (13, 5)], [((7, 8), (9, 10))]),
}


def mount(n: int) -> Sprite:
    """远峰：逐顶点勾的山脊，阳面亮、阴面网点，阳面几道岩缝"""
    def mk():
        w, h, outline, shade, cracks = MOUNTS[n]
        p = Part(w, h)
        p.shape("polygon", outline, fill=1)
        p.dither(shade, 0.5, 0)
        for a, b in cracks:
            p.d.line(a + b, fill=0)
        return p.sprite()
    return cached(("mount", n), mk)


def cloud_sea(g: Gfx, t: float, y: int, x0: int = 0, x1: int = 128, speed: float = 2.0):
    """云海：连绵的云头（顶边一串圆鼓包，下面网点），缓缓横移"""
    off = (t * speed) % 10
    for x in range(int(x0 - 10 + off), x1 + 10, 10):
        yy = y + (2 if (x // 10) % 2 else 0)
        g.d.ellipse((x - 6, yy - 3, x + 6, yy + 3), fill=1)
    g.d.rectangle((x0, y + 1, x1, 63), fill=1)
    pix.checker(g, (x0, y + 2, x1, 64), 0.5, fill=0)
    pix.checker(g, (x0, y + 4, x1, 64), 0.75, fill=0)
    for x in range(int(x0 - 10 + off), x1 + 10, 10):   # 云头下沿的暗线
        yy = y + (2 if (x // 10) % 2 else 0)
        g.d.arc((x - 6, yy - 3, x + 6, yy + 3), 20, 160, fill=0)
