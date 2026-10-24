"""洒净：清晨的坛场，石栏杆、远处朝阳；坛中一只净水盂，小道士手执柳枝蘸水，一甩，水珠扇形飞出、落地溅起。

依据：开坛先洒净荡秽，高功以柳枝（杨枝）蘸净水洒坛，同时诵《净天地神咒》
（“天地自然，秽炁分散……凶秽消散，道炁长存。急急如律令”）。字库没有“炁”，用“气”代替。

入场：净水盂“咚”地落到盂架上，水面一圈涟漪；小道士举着柳枝走来，柳叶一颤。
持续：每 6 秒一个动作：柳梢点进盂里（水面涟漪）→ 提起（梢头滴水）→ 举过头蓄力 → 一甩，
      九颗水珠呈扇形飞出、沿抛物线落下，飞到最高点一闪，落地溅起一圈水花。每甩四次绕到盂的另一边换个方向洒。
      一轮 600 秒念完全咒二十二句（左上牌子一句一句换）；柳叶隔一阵掉一片飘落，朝阳的光芒慢慢转。
      续：旧柳枝的叶子差不多掉光了，天上落下三滴甘露“叮”地注进盂里，柳枝重新抽出满枝新叶。
中断：小道士把柳枝横搁在盂沿上，拱手，牌子“暂歇”。  恢复：拿起柳枝，蘸水一甩。
圆满：小道士举柳枝原地一转，水珠向四面八方洒开，天边挂起一道彩虹（三道点弧），闪白，“急急如律令”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import FLOOR, Clock, badge, floor, hit, mx_art, mx_burst, pose_arm, ring_dots, star, title

BOWL_X = 64
BOWL_TOP = 41            # 盂口 y
SIDES = (46, 82)         # 小道士站在盂左边（朝右洒）/ 右边（朝左洒）
ACT = 6.0
RENEW = 7.0
GRAV = 90.0

CHANT = ["天地自然", "秽气分散", "洞中玄虚", "晃朗太元", "八方威神", "使我自然", "灵宝符命", "普告九天",
         "乾罗答那", "洞罡太玄", "斩妖缚邪", "度人万千", "中山神咒", "元始玉文", "持诵一遍", "却病延年",
         "按行五岳", "八海知闻", "魔王束首", "侍卫我轩", "凶秽消散", "道气长存"]

LEAF = pix.frames("""
#
#
---
 #
#
---
#
 #
""")


def _bowl():
    """净水盂 17×13：卷沿、鼓腹（缠枝纹一道）、盂架三足"""
    p = Part(17, 14)
    p.shape("rectangle", (1, 0, 15, 1), fill=1)
    p.d.line((3, 1, 13, 1), fill=0)
    p.shape("ellipse", (0, 1, 16, 9), fill=1)
    p.shape("rectangle", (1, 0, 15, 0), fill=1)
    for x in range(2, 15, 3):                 # 缠枝纹
        p.px(x, 5, 0), p.px(x + 1, 4, 0)
    p.d.line((2, 6, 14, 6), fill=0)
    p.dither([(10, 2), (16, 2), (16, 9), (10, 9)], 0.5, 0)
    p.shape("rectangle", (5, 9, 11, 10), fill=1)
    for x0, x1 in ((5, 2), (8, 8), (11, 14)):  # 盂架
        p.shape("line", (x0, 10, x1, 13), fill=1)
    return p.sprite()


_P: dict = {}


def P(name):
    if name not in _P:
        _P[name] = {"bowl": _bowl}[name]()
    return _P[name]


def court(g: Gfx, t: float):
    """坛场：远处朝阳（光芒慢转）、一道远山、石栏杆（望柱 + 寻杖 + 栏板）、地面"""
    sx, sy = 108, 14
    g.d.ellipse((sx - 6, sy - 6, sx + 6, sy + 6), fill=1)
    g.d.ellipse((sx - 4, sy - 4, sx + 4, sy + 4), fill=0)
    g.d.ellipse((sx - 3, sy - 3, sx + 3, sy + 3), fill=1)
    for j in range(10):
        a = j / 10 * 2 * math.pi + t * 0.15
        pix.dotted(g, sx + math.cos(a) * 9, sy + math.sin(a) * 9, sx + math.cos(a) * 12, sy + math.sin(a) * 12, 2)
    pix.dotted(g, 0, 33, 30, 28, 2)
    pix.dotted(g, 30, 28, 58, 32, 2)
    pix.dotted(g, 58, 32, 90, 26, 2)
    pix.dotted(g, 90, 26, 127, 31, 2)
    for x, h in ((6, 22), (121, 22)):                         # 两根望柱
        y0 = FLOOR - 4 - h
        g.d.rectangle((x - 2, y0, x + 2, FLOOR - 5), fill=1)
        g.d.ellipse((x - 3, y0 - 5, x + 3, y0 + 1), fill=1)
        g.px(x, y0 - 3, 0)
        g.d.line((x - 1, y0 + 3, x + 1, y0 + 3), fill=0)
        pix.checker(g, (x + 1, y0 + 4, x + 3, FLOOR - 5), 0.5, fill=0)
    for x in range(10, 120, 6):                               # 坛沿石阶的砖缝
        g.px(x, FLOOR - 2)
    g.d.line((0, FLOOR - 4, 127, FLOOR - 4), fill=1)
    floor(g)


def willow(g: Gfx, hx: float, hy: float, tx: float, ty: float, t: float, leaves: int = 10, wet: bool = False):
    """柳枝：从手到梢的弯枝，柳叶沿枝垂下、随风轻摆"""
    mx, my = (hx + tx) / 2 - (ty - hy) * 0.15, (hy + ty) / 2 + (tx - hx) * 0.15
    pts = []
    for i in range(9):
        k = i / 8
        x = (1 - k) ** 2 * hx + 2 * (1 - k) * k * mx + k * k * tx
        y = (1 - k) ** 2 * hy + 2 * (1 - k) * k * my + k * k * ty
        pts.append((x, y))
    g.d.line(pts, fill=0, width=3)
    g.d.line(pts, fill=1)
    for i in range(min(leaves, 12)):
        k = 0.25 + i / 12 * 0.75
        j = int(k * 8)
        x, y = pts[j]
        side = 1 if i % 2 else -1
        sw = math.sin(t * 3 + i) * 0.8
        g.d.line((x, y, x + side * 2 + sw, y + 3), fill=1)
        g.px(x + side * 2 + sw, y + 4)
    if wet and int(t * 8) % 3 == 0:
        g.px(tx, ty + 2)
    g.d.rectangle((hx - 1, hy - 1, hx + 1, hy + 1), fill=1)


def drops(g: Gfx, age: float, x0: float, y0: float, s: int, seed: int, n: int = 9, spread: float = 1.0,
          radial: bool = False):
    """甩出的水珠：抛物线、最高点一闪、落地溅起；age = 甩出后秒数（确定性）"""
    for j in range(n):
        if radial:
            a = j / n * 2 * math.pi
            v = 40 + rand(j, seed) * 25
            vx, vy = math.cos(a) * v, math.sin(a) * v - 35
        else:
            vx = s * (18 + rand(j, seed) * 40) * spread
            vy = -(16 + rand(j + 30, seed) * 30)
        # 落地时刻
        A, B, C = 0.5 * GRAV, vy, y0 - FLOOR
        land = (-B + math.sqrt(max(B * B - 4 * A * C, 0))) / (2 * A)
        if age < land:
            x, y = x0 + vx * age, y0 + vy * age + 0.5 * GRAV * age * age
            if abs(vy + GRAV * age) < 8:      # 最高点一闪
                star(g, x, y, 1)
            else:                             # 水珠：两像素 + 拖尾
                g.px(x, y), g.px(x, y + 1)
                g.px(x - vx * 0.03, y - (vy + GRAV * age) * 0.03)
        elif age < land + 0.3:
            x = x0 + vx * land
            k = (age - land) / 0.3
            r = 1 + k * 3
            g.px(x - r, FLOOR - 1 - k * 2)
            g.px(x + r, FLOOR - 1 - k * 2)
            g.px(x, FLOOR - 2 - k * 3)


def mx_sprinkle(g: Gfx, age: float, s: int, t: float, dew: bool = False):
    mx_art(g, """
........
........
........
........
........
.######.
..####..
...##...
""")
    if 0 <= age < 1.2:
        for j in range(3):
            x = 3.5 + s * (1 + j) * age * 2.5
            y = 4 - math.sin(min(age / 1.0, 1) * math.pi) * (2 + j)
            g.mx_set(int(round(x)), int(round(y)))
    if dew:
        g.mx[int(t * 8) % 5, 3] = True


@register
class Sprinkle(Ritual):
    id = "r1.sprinkle"
    name = "洒净"
    desc = "清晨坛场，小道士柳枝蘸净水一甩，水珠扇形飞出落地溅花，绕着净水盂换方向洒；诵净天地神咒，一轮后甘露注盂"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 3.2, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    def leaves(self, e: float) -> int:
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return 2 if k < 4.5 else int(lerp(2, 12, span(k, 4.5, 6.0)))
        return 12 - int(10 * k / self.CYCLE)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        k = e % self.CYCLE
        i = min(int(k / (self.CYCLE / len(CHANT))), len(CHANT) - 1)
        badge(g, 4, 3, label or CHANT[i], size=12)

    def bowl(self, g: Gfx, ripple: float = -1.0):
        spr = P("bowl")
        pix.blit(g, spr, BOWL_X - 8, BOWL_TOP)
        g.d.line((BOWL_X - 5, BOWL_TOP + 1, BOWL_X + 5, BOWL_TOP + 1), fill=0)
        if 0 <= ripple < 1:
            r = 2 + ripple * 6
            ring_dots(g, BOWL_X, BOWL_TOP, r, 2, sy=0.3, a0=math.pi, a1=2 * math.pi)

    def act(self, g: Gfx, t: float, u: float, a: int, e: float, dt: float):
        """一个洒水动作（u ∈ [0, 6]）。a = 第几个动作，决定方向"""
        side = (a // 4) % 2
        s = 1 if side == 0 else -1
        x = SIDES[side]
        flip = side == 1
        nl = self.leaves(e)
        mouth = (BOWL_X, BOWL_TOP + 2)
        switching = (a % 4) == 3
        if switching and u >= 3.6:   # 绕到盂的另一边
            x2 = SIDES[1 - side]
            q = ease_in_out(span(u, 3.6, 5.6))
            xx = lerp(x, x2, q)
            h = pose_arm(g, xx, FLOOR, t, 0, legs="walk" if q < 1 else "stand", flip=(not flip) if q >= 1 else flip)
            hx, hy = h["hand"]
            fs = -s if q >= 1 else s
            willow(g, hx, hy, hx + fs * 6, hy - 12, t, nl)
            self.bowl(g, -1)
            return
        if u < 1.2:        # 蘸水
            h = pose_arm(g, x, FLOOR, t, 30, flip=flip)
            hx, hy = h["hand"]
            q = ease_in_out(span(u, 0.0, 0.6))
            tip = (lerp(hx + s * 6, mouth[0], q), lerp(hy - 10, mouth[1], q))
            self.bowl(g, span(u, 0.6, 1.2) if u >= 0.6 else -1)
            willow(g, hx, hy, *tip, t, nl)
        elif u < 2.4:      # 提起，梢头滴水
            h = pose_arm(g, x, FLOOR, t, -30, flip=flip)
            hx, hy = h["hand"]
            self.bowl(g, -1)
            willow(g, hx, hy, hx + s * 7, hy - 12, t, nl, wet=True)
        elif u < 2.75:     # 举过头蓄力
            h = daoshi(g, x, FLOOR, "raise", t, flip=flip)
            hx, hy = h["hand"]
            self.bowl(g, -1)
            willow(g, hx, hy, hx - s * 8, hy - 8, t, nl, wet=True)
        elif u < 3.1:      # 甩！
            q = span(u, 2.75, 3.1)
            h = pose_arm(g, x, FLOOR, t, 0 if q < 0.5 else 30, flip=flip)
            hx, hy = h["hand"]
            self.bowl(g, -1)
            ang = lerp(-2.2, 0.4, q)
            tip = (hx + s * math.cos(ang) * 13, hy + math.sin(ang) * 13)
            willow(g, hx, hy, *tip, t, nl)
            for j in range(5):   # 挥动的弧线
                aa = lerp(-2.2, ang, j / 4)
                g.px(hx + s * math.cos(aa) * 15, hy + math.sin(aa) * 15)
        else:
            h = pose_arm(g, x, FLOOR, t, 30, flip=flip, face="happy" if u < 4.5 else "normal")
            hx, hy = h["hand"]
            self.bowl(g, -1)
            willow(g, hx, hy, hx + s * 6, hy - 11, t, nl)
        if u >= 2.95:   # 水珠
            drops(g, u - 2.95, x + s * 18, FLOOR - 30, s, self.seed + a, n=11)

    def falling_leaf(self, g: Gfx, e: float):
        k = (e + self.seed * 5) % 23
        if k < 4:
            x = 60 + math.sin(k * 3) * 8 + k * 6
            y = 18 + k * 10
            pix.blit(g, pix.anim(LEAF, k, 4), x, min(y, FLOOR - 2), outline=False)

    # ------------------------------------------------------------ 入场 / 持续

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        court(g, t)
        drop = ease_out_bounce(span(t, 0.1, 1.0))
        y = lerp(-20, BOWL_TOP, drop)
        pix.blit(g, P("bowl"), BOWL_X - 8, y)
        if hit(t, 0.48, dt):
            pix.shake(g, t, 1.0)
            self.sparks.burst(BOWL_X, BOWL_TOP, 8, 18, up=12, life=0.4, gravity=60)
        if t > 0.5:
            r = (t - 0.5) * 8
            if r < 8:
                ring_dots(g, BOWL_X, BOWL_TOP, r, 2, sy=0.3, a0=math.pi, a1=2 * math.pi)
        x = lerp(-14, SIDES[0], ease_out(span(t, 1.0, 3.2)))
        h = pose_arm(g, x, FLOOR, t, -30 if t > 3.2 else 0, legs="walk" if t < 3.2 else "stand")
        hx, hy = h["hand"]
        willow(g, hx, hy, hx + 7, hy - 12, t + (math.sin(t * 20) if 3.2 < t < 3.6 else 0), 12)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 3.2:
            self.counter(g, 0.0)
        mx_sprinkle(g, -1, 1, t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e, dt)
            return
        court(g, t)
        a = int(e // ACT)
        u = e % ACT
        self.act(g, t, u, a, e, dt)
        self.falling_leaf(g, e)
        self.counter(g, e)
        side = (a // 4) % 2
        mx_sprinkle(g, u - 2.95, 1 if side == 0 else -1, t)

    def _renew(self, g: Gfx, t: float, k: float, e: float, dt: float):
        """甘露注盂，柳枝抽新叶"""
        court(g, t)
        a = int((e - k) // ACT)
        side = (a // 4) % 2
        s = 1 if side == 0 else -1
        x = SIDES[side]
        ripple = -1.0
        for j in range(3):     # 三滴甘露
            t0 = 0.6 + j * 0.9
            q = span(k, t0, t0 + 0.7)
            if 0 < q < 1:
                y = lerp(-4, BOWL_TOP, q * q)
                g.d.ellipse((BOWL_X - 1, y - 2, BOWL_X + 1, y + 1), fill=1)
                g.px(BOWL_X, y - 3)
                pix.dotted(g, BOWL_X, 0, BOWL_X, y - 4, 3, int(t * 10))
            if hit(k, t0 + 0.7, dt):
                self.sparks.burst(BOWL_X, BOWL_TOP, 8, 18, up=14, life=0.5, gravity=60)
            if t0 + 0.7 <= k < t0 + 1.4:
                ripple = (k - t0 - 0.7) / 0.7
        self.bowl(g, ripple)
        nl = self.leaves(e)
        face = "wow" if k < 3.4 else "happy"
        h = pose_arm(g, x, FLOOR, t, -30, flip=side == 1, face=face)
        hx, hy = h["hand"]
        willow(g, hx, hy, hx + s * 7, hy - 12, t, nl)
        if hit(k, 4.5, dt):
            self.sparks.burst(hx + s * 4, hy - 8, 12, 20, life=0.5, gravity=10)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        mx_sprinkle(g, -1, s, t, dew=k < 3.5)

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def rest_branch(self, g: Gfx, t: float):
        """柳枝横搁在盂沿上"""
        willow(g, BOWL_X - 9, BOWL_TOP - 1, BOWL_X + 10, BOWL_TOP - 3, t, 8)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        court(g, t)
        a = int(e // ACT)
        side = (a // 4) % 2
        s = 1 if side == 0 else -1
        x = SIDES[side]
        self.bowl(g)
        if t < 0.7:
            h = pose_arm(g, x, FLOOR, t, 30, flip=side == 1)
            hx, hy = h["hand"]
            q = span(t, 0, 0.7)
            willow(g, hx, hy, lerp(hx + s * 6, BOWL_X + s * 10, q), lerp(hy - 11, BOWL_TOP - 3, q), t, 8)
        else:
            daoshi(g, x, FLOOR, "gongshou", t, flip=side == 1)
            self.rest_branch(g, t)
        self.counter(g, e, "暂歇" if t > 0.6 else None)
        mx_sprinkle(g, -1, s, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        court(g, t)
        a = int(e // ACT)
        side = (a // 4) % 2
        if t < 0.5:
            self.bowl(g)
            daoshi(g, SIDES[side], FLOOR, "gongshou", t, flip=side == 1)
            self.rest_branch(g, t)
        else:
            self.act(g, t, min(t - 0.5 + 0.6, 3.5), a, e, dt)
        self.counter(g, e)
        mx_sprinkle(g, t - 2.8, 1 if side == 0 else -1, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        court(g, t)
        self.bowl(g, span(t, 0.2, 0.8) if t < 0.8 else -1)
        x = SIDES[0]
        if t < 0.8:
            h = pose_arm(g, x, FLOOR, t, 30)
            hx, hy = h["hand"]
            willow(g, hx, hy, BOWL_X, BOWL_TOP + 2, t, 12)
        elif t < 1.6:      # 原地一转
            flip = int(t * 8) % 2 == 1
            h = daoshi(g, x, FLOOR, "raise", t, flip=flip)
            hx, hy = h["hand"]
            willow(g, hx, hy, hx + (6 if not flip else -6), hy - 10, t, 12)
        else:
            pose = "kneel" if 2.4 < t < 4.6 else "idle"
            daoshi(g, x, FLOOR, pose, t, face="happy")
        if t > 1.6:
            drops(g, t - 1.6, x + 4, FLOOR - 40, 1, self.seed, n=24, radial=True)
        if t > 2.2:        # 彩虹
            k = ease_out(span(t, 2.2, 3.0))
            for j in range(3):
                r = 22 + j * 4
                ring_dots(g, 94, FLOOR - 1, r, 2 + j * 0.5, a0=math.pi, a1=math.pi + math.pi * k)
        if hit(t, 1.6, dt):
            pix.flash(g)
            self.sparks.burst(x + 4, FLOOR - 40, 20, 40, life=0.8, gravity=40)
        if 1.6 < t < 1.9:
            pix.shake(g, t, 1.5)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 2.6:
            title(g, 60, 4, "急急如律令", t, 2.6)
        mx_sprinkle(g, -1, 1, t)
        mx_burst(g, t, 1.6)
