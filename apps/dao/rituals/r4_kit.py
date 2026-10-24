"""r4 批（内丹·外丹·炼养功法）共用的小工具：可摆姿势的像素小人、打坐小人、光点、小字图标。

小人是 2D 骨架：每段肢体给一个“屏幕绝对角度”（度，0 = 朝下，90 = 朝右，-90 = 朝左，180 = 朝上），
姿势之间直接按数值插值，所以功法动作只要写几个关键帧。画的时候自动“落地”（最低的脚踩在 ground 上）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in_out, lerp
from ..engine.gfx import Gfx

# ------------------------------------------------------------------ 姿势

BASE = dict(
    tor=0.0,      # 躯干角：0 直立，正 = 向右倾（侧面时 = 向右弯腰）
    lua=-8.0, lfa=-4.0, rua=8.0, rfa=4.0,       # 左右上臂、前臂
    lth=-4.0, lsh=-2.0, rth=4.0, rsh=2.0,       # 左右大腿、小腿
    shw=5.0, hipw=3.0,                          # 肩、胯的半宽（侧面时调小）
    face=0.0,     # 脸朝向 -1 左 .. 0 正面 .. 1 右
    tilt=0.0,     # 头相对躯干的偏角（度）
    lift=0.0,     # 整个人离地（跳、颠）
    lh=0.0, rh=0.0,  # 手型：0 掌，1 拳，2 爪，3 剑指
    brow=0.0,     # 怒目
    wing=0.0,     # 鸟戏羽翼
)


def pose(*bases: dict, **kw) -> dict:
    """pose(SIDE, tor=30)：在 BASE 上依次叠加 bases 和关键字"""
    p = dict(BASE)
    for b in bases:
        p.update(b)
    p.update(kw)
    return p


def mirror(p: dict) -> dict:
    """左右镜像（开弓左右交替用）"""
    q = dict(p)
    for a, b in (("lua", "rua"), ("lfa", "rfa"), ("lth", "rth"), ("lsh", "rsh")):
        q[a], q[b] = -p[b], -p[a]
    q["lh"], q["rh"] = p["rh"], p["lh"]
    for n in ("tor", "face", "tilt"):
        q[n] = -p[n]
    return q


def blend(a: dict, b: dict, k: float) -> dict:
    k = clamp(k)
    return {n: lerp(a[n], b[n], k) for n in a}


def seq(keys: list, t: float, period: float, smooth=ease_in_out) -> dict:
    """在一串关键帧之间循环（首尾相接），t 秒，一圈 period 秒"""
    n = len(keys)
    u = (t % period) / period * n
    i = int(u)
    return blend(keys[i % n], keys[(i + 1) % n], smooth(u - i))


def _v(ang: float, ln: float) -> tuple[float, float]:
    r = math.radians(ang)
    return math.sin(r) * ln, math.cos(r) * ln


class Body:
    """按姿势算出关节位置。s = 缩放"""
    UA, FA, TH, SH, TOR, NECK = 8.0, 7.5, 10.0, 10.0, 13.0, 6.0

    def __init__(self, p: dict, x: float, ground: float, s: float = 1.0):
        self.p, self.s = p, s
        # 先在原点算一遍，再整体平移落地
        hip = (0.0, 0.0)
        tr = math.radians(p["tor"])
        up = (math.sin(tr), -math.cos(tr))
        perp = (math.cos(tr), math.sin(tr))
        sc = (hip[0] + up[0] * self.TOR * s, hip[1] + up[1] * self.TOR * s)
        self.neck = sc
        ha = math.radians(p["tor"] + p["tilt"])
        self.head = (sc[0] + math.sin(ha) * self.NECK * s, sc[1] - math.cos(ha) * self.NECK * s)
        sw = p["shw"] * s
        self.lsho = (sc[0] - perp[0] * sw, sc[1] - perp[1] * sw + 1)
        self.rsho = (sc[0] + perp[0] * sw, sc[1] + perp[1] * sw + 1)
        self.lhip = (hip[0] - p["hipw"] * s, hip[1])
        self.rhip = (hip[0] + p["hipw"] * s, hip[1])
        self.hip = hip

        def chain(o, a1, l1, a2, l2):
            d1 = _v(a1, l1 * s)
            j = (o[0] + d1[0], o[1] + d1[1])
            d2 = _v(a2, l2 * s)
            return j, (j[0] + d2[0], j[1] + d2[1])

        self.lelb, self.lhand = chain(self.lsho, p["lua"], self.UA, p["lfa"], self.FA)
        self.relb, self.rhand = chain(self.rsho, p["rua"], self.UA, p["rfa"], self.FA)
        self.lknee, self.lfoot = chain(self.lhip, p["lth"], self.TH, p["lsh"], self.SH)
        self.rknee, self.rfoot = chain(self.rhip, p["rth"], self.TH, p["rsh"], self.SH)
        low = max(self.lfoot[1], self.rfoot[1])
        dx, dy = x, ground - low - p["lift"] - 1
        for n in ("neck", "head", "lsho", "rsho", "lhip", "rhip", "hip", "lelb", "lhand", "relb", "rhand", "lknee",
                  "lfoot", "rknee", "rfoot"):
            v = getattr(self, n)
            setattr(self, n, (v[0] + dx, v[1] + dy))

    def draw(self, g: Gfx, robe: float = 0.5, glow: float = 0.0, outline_arms: bool = True):
        d, p, s = g.d, self.p, self.s
        w_limb = max(2, int(round(3 * s)))
        # 腿（裤）
        for hp, kn, ft in ((self.lhip, self.lknee, self.lfoot), (self.rhip, self.rknee, self.rfoot)):
            d.line((hp, kn, ft), fill=1, width=w_limb, joint="curve")
            # 鞋：朝外一点的小块
            fx, fy = ft
            out = -1 if ft[0] < self.hip[0] - 0.5 else 1 if ft[0] > self.hip[0] + 0.5 else (1 if p["face"] >= 0 else -1)
            d.rectangle((min(fx, fx + out * 3 * s), fy - 1, max(fx, fx + out * 3 * s), fy + 1), fill=1)
        # 道袍下摆：胯到两膝之间（随腿张开）
        lk, rk = self.lknee, self.rknee
        hem_l = (lerp(self.lhip[0], lk[0], 0.85) - 2 * s, lerp(self.lhip[1], lk[1], 0.85))
        hem_r = (lerp(self.rhip[0], rk[0], 0.85) + 2 * s, lerp(self.rhip[1], rk[1], 0.85))
        skirt = [(self.lhip[0] - 1 * s, self.lhip[1] - 2), (self.rhip[0] + 1 * s, self.rhip[1] - 2), hem_r, hem_l]
        d.polygon(skirt, fill=1)
        d.line((hem_l, hem_r), fill=0)
        # 躯干：肩到胯的梯形，实心
        torso = [self.lsho, self.rsho, (self.rhip[0] + 1 * s, self.rhip[1]), (self.lhip[0] - 1 * s, self.lhip[1])]
        d.polygon(torso, fill=1)
        # 腰带（黑线）+ 衣襟
        bx0, by0 = lerp(self.lsho[0], self.lhip[0], 0.75), lerp(self.lsho[1], self.lhip[1], 0.75)
        bx1, by1 = lerp(self.rsho[0], self.rhip[0], 0.75), lerp(self.rsho[1], self.rhip[1], 0.75)
        d.line((bx0, by0, bx1, by1), fill=0)
        if abs(p["tor"]) < 35 and p["shw"] > 3:
            nx, ny = self.neck
            d.line((nx - 1, ny + 1, nx + 1.5, ny + 4), fill=0)
        # 头：实心圆 + 发髻 + 簪
        hx, hy = self.head
        r = 3.6 * s
        d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=1)
        ha = math.radians(p["tor"] + p["tilt"])
        kx, ky = hx + math.sin(ha) * (r + 1.5 * s) - p["face"] * 1.2 * s, hy - math.cos(ha) * (r + 1.5 * s)
        d.ellipse((kx - 1.6 * s, ky - 1.6 * s, kx + 1.6 * s, ky + 1.6 * s), fill=1)
        d.line((kx - 3 * s, ky, kx + 3 * s, ky), fill=1)
        # 眼（黑点）：随朝向偏移
        f = p["face"]
        if abs(f) < 0.6:
            ey = hy - 0.5 * s
            for side in (-1, 1):
                ex = hx + side * 1.6 * s + f * 1.5 * s
                d.point((ex, ey), fill=0)
                if p["brow"] > 0.5:
                    d.line((ex - side * 1, ey - 2, ex + side * 0.5, ey - 1), fill=0)
        else:
            sd = 1 if f > 0 else -1
            d.point((hx + sd * 2 * s, hy - 0.5 * s), fill=0)
            d.point((hx + sd * (r + 0.6), hy + 0.5 * s), fill=1)  # 鼻尖
        # 胳膊：先描黑边再画白，叠在身体上也分得清
        for sho, elb, hd, ht in ((self.lsho, self.lelb, self.lhand, p["lh"]), (self.rsho, self.relb, self.rhand, p["rh"])):
            if outline_arms:
                d.line((sho, elb, hd), fill=0, width=w_limb + 2, joint="curve")
            d.line((sho, elb), fill=1, width=w_limb + 1)
            d.line((elb, hd), fill=1, width=w_limb, joint="curve")
            self._hand(g, hd, elb, ht)
            if p.get("wing", 0) > 0.5:  # 鸟戏：前臂下缘挂几根羽毛
                for j in range(4):
                    f = 0.15 + j * 0.28
                    ax, ay = lerp(sho[0], hd[0], f), lerp(sho[1], hd[1], f)
                    out = 1 if hd[0] >= sho[0] else -1
                    d.line((ax, ay + 2, ax + out * 1, ay + 5 + j), fill=1)
        if glow > 0:
            from ..engine.fx import ring
            ring(g, self.hip[0], self.neck[1] + 4, 20 + glow * 6, 3, glow * 2)

    def _hand(self, g: Gfx, hd, elb, kind):
        d, s = g.d, self.s
        x, y = hd
        ang = math.atan2(y - elb[1], x - elb[0])
        ux, uy = math.cos(ang), math.sin(ang)
        k = int(round(kind))
        if k == 1:  # 拳
            d.rectangle((x - 1.5 * s, y - 1.5 * s, x + 1.5 * s, y + 1.5 * s), fill=1, outline=0)
            d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
        elif k == 2:  # 虎爪：三根弯指
            for j in (-1, 0, 1):
                a = ang + j * 0.6
                d.line((x, y, x + math.cos(a) * 3 * s, y + math.sin(a) * 3 * s), fill=1)
                d.point((x + math.cos(a + 0.5) * 3.5 * s, y + math.sin(a + 0.5) * 3.5 * s), fill=1)
        elif k == 3:  # 剑指 / 八字掌：伸出食指
            d.line((x, y, x + ux * 4 * s, y + uy * 4 * s), fill=1)
            d.point((x - uy * 2, y + ux * 2), fill=1)
        elif k == 4:  # 鹿角：两根分叉
            for j in (-1, 1):
                a = ang + j * 0.55
                ex, ey = x + math.cos(a) * 5 * s, y + math.sin(a) * 5 * s
                d.line((x, y, ex, ey), fill=1)
                b = a + j * 0.9
                d.line((lerp(x, ex, 0.5), lerp(y, ey, 0.5), lerp(x, ex, 0.5) + math.cos(b) * 2.5 * s,
                        lerp(y, ey, 0.5) + math.sin(b) * 2.5 * s), fill=1)
        elif k == 5:  # 勾手：五指捏拢下垂
            d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
            d.line((x + ux * 1.5, y + 1, x + ux * 1.5, y + 4 * s), fill=1)
        else:  # 掌
            d.line((x, y, x + ux * 2.5 * s, y + uy * 2.5 * s), fill=1, width=2)


def figure(g: Gfx, p: dict, x: float, ground: float, s: float = 1.0, **kw) -> Body:
    b = Body(p, x, ground, s)
    b.draw(g, **kw)
    return b


# ------------------------------------------------------------------ 打坐小人（正面，盘腿）

def seated(g: Gfx, cx: float, base: float, s: float = 1.0, hands: str = "lap", breath: float = 0.0,
           eyes: float = 0.0, robe: float = 0.45):
    """正面盘坐：base = 坐垫底边。breath 0..1 胸腹起伏；eyes 0 闭 1 睁。返回 dict（头、三丹田位置）"""
    d = g.d
    # 蒲团
    d.ellipse((cx - 22 * s, base - 5 * s, cx + 22 * s, base + 1 * s), fill=0, outline=1)
    d.line((cx - 18 * s, base - 2 * s, cx + 18 * s, base - 2 * s), fill=1)
    # 盘起的腿：一个扁的袍摆
    knees = base - 5 * s
    legs = [(cx - 21 * s, knees), (cx - 14 * s, knees - 7 * s), (cx + 14 * s, knees - 7 * s), (cx + 21 * s, knees),
            (cx + 14 * s, knees + 2 * s), (cx - 14 * s, knees + 2 * s)]
    g.shade_poly(legs, robe)
    d.line((cx - 9 * s, knees - 3 * s, cx + 9 * s, knees - 1 * s), fill=1)  # 交叠的小腿
    # 身子（道袍）：随呼吸微微变宽
    sh = knees - 22 * s
    bw = 9 * s + breath * 1.0
    body = [(cx - bw, sh), (cx + bw, sh), (cx + 12 * s + breath, knees - 6 * s), (cx - 12 * s - breath, knees - 6 * s)]
    d.polygon(body, fill=0)
    g.shade_poly(body, robe)
    # 衣襟交领 + 腰带
    d.line((cx - 4 * s, sh, cx + 2 * s, sh + 9 * s), fill=1)
    d.line((cx + 4 * s, sh, cx - 1 * s, sh + 5 * s), fill=1)
    d.line((cx - 11 * s, knees - 9 * s, cx + 11 * s, knees - 9 * s), fill=1)
    # 袖子垂到膝上，手在腹前结印
    for side in (-1, 1):
        sl = [(cx + side * bw, sh + 1), (cx + side * (bw + 5 * s), sh + 10 * s), (cx + side * 13 * s, knees - 4 * s),
              (cx + side * 5 * s, knees - 5 * s)]
        d.polygon(sl, fill=0, outline=1)
    if hands == "lap":
        d.ellipse((cx - 5 * s, knees - 8 * s, cx + 5 * s, knees - 3 * s), fill=1, outline=1)
        d.line((cx - 3 * s, knees - 5.5 * s, cx + 3 * s, knees - 5.5 * s), fill=0)
    # 头
    hy = sh - 7 * s
    r = 5.5 * s
    d.rectangle((cx - 1.5 * s, sh - 2 * s, cx + 1.5 * s, sh), fill=1)
    d.ellipse((cx - r, hy - r, cx + r, hy + r), fill=1)
    d.ellipse((cx - 2.5 * s, hy - r - 4 * s, cx + 2.5 * s, hy - r + 1 * s), fill=1)  # 发髻
    d.line((cx - 5 * s, hy - r - 1.5 * s, cx + 5 * s, hy - r - 1.5 * s), fill=1)     # 簪
    # 眼：闭眼两道弧（短横），睁眼两点
    ey = hy
    for side in (-1, 1):
        ex = cx + side * 2.2 * s
        if eyes > 0.5:
            d.rectangle((ex - 0.5, ey - 1, ex + 0.5, ey), fill=0)
        else:
            d.line((ex - 1.2 * s, ey, ex + 1.2 * s, ey), fill=0)
    return {"head": (cx, hy), "crown": (cx, hy - r - 4 * s), "upper": (cx, hy - 1.5 * s), "middle": (cx, sh + 7 * s),
            "lower": (cx, knees - 10 * s), "knees": knees, "sh": sh, "r": r}


# ------------------------------------------------------------------ 小零件

def glow_dot(g: Gfx, x: float, y: float, r: float, t: float = 0.0, rays: bool = False):
    """发光的气团/丹：实心圆 + 外面一圈点（亮度用半径表示）"""
    d = g.d
    if r <= 0.4:
        g.px(x, y)
        return
    d.ellipse((x - r, y - r, x + r, y + r), fill=1)
    if r >= 2:
        from ..engine.fx import ring
        ring(g, x, y, r + 2, 2, t * 2)
    if rays:
        for i in range(8):
            a = i * math.pi / 4 + t
            g.d.line((x + math.cos(a) * (r + 3), y + math.sin(a) * (r + 3), x + math.cos(a) * (r + 5),
                      y + math.sin(a) * (r + 5)), fill=1)


def ground_line(g: Gfx, y: int, x0: int = 0, x1: int = 127, dots: bool = True):
    g.d.line((x0, y, x1, y), fill=1)
    if dots:
        for x in range(x0 + 3, x1, 7):
            g.px(x, y + 2)


def mx_icon(g: Gfx, art: str):
    """点阵 8×8 图标（# 亮）"""
    rows = [r for r in art.strip("\n").split("\n")]
    ind = min(len(r) - len(r.lstrip()) for r in rows if r.strip())
    for y, r in enumerate(rows[:8]):
        for x, ch in enumerate(r[ind:ind + 8]):
            g.mx[y, x] = ch == "#"


def path_point(pts: list, u: float) -> tuple[float, float]:
    """折线上按弧长取点，u 0..1"""
    segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    tot = sum(segs)
    k = (u % 1.0) * tot
    for (a, b), L in zip(zip(pts, pts[1:]), segs):
        if k <= L:
            f = k / L if L else 0
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        k -= L
    return pts[-1]
