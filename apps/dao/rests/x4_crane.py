"""鹤归华表：丁令威学道成仙，化鹤归辽，停在城门华表柱上。

依据：《搜神后记》卷一“丁令威，本辽东人，学道于灵虚山。后化鹤归辽，集城门华表柱。时有少年，举弓欲射之，
鹤乃飞，徘徊空中而言曰：‘有鸟有鸟丁令威，去家千年今始归。城郭如故人民非，何不学仙冢累累。’遂高上冲天。”
入场：一只鹤从右上方划一道弧飞来，落在华表顶上，收翅、转身站定。
持续：鹤立华表，远处城郭；鹤会梳理羽毛、回头、单脚独立、仰头长鸣（声波）。
      每 60 秒：一个少年从右边走来举弓，鹤腾空在城头上盘旋，空中逐字写出诗的一句（四句轮换），少年放下弓走开，鹤落回柱顶。
收场：鹤展翅冲天而去（“遂高上冲天”）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Bake, mx_sprite, sound_arcs

PX, PY = 30, 29      # 华表柱顶（鹤脚站的位置）
GROUND = 61
EV0, EV_P = 20.0, 60.0
POEM = ["有鸟有鸟丁令威", "去家千年今始归", "城郭如故人民非", "何不学仙冢累累"]


def _huabiao() -> Sprite:
    """华表：承露盘 + 柱身（盘龙纹）+ 云板 + 须弥座。宽 28，高 32，顶端 = 柱顶"""
    b = Bake(28, 32)
    b.poly([(5, 29), (23, 29), (23, 31), (5, 31)], 0.0)            # 座
    b.poly([(8, 26), (20, 26), (21, 29), (7, 29)], 0.0)
    b.poly([(11, 3), (17, 3), (17, 26), (11, 26)], 0.0)            # 柱身
    for y in range(13, 26, 4):                                     # 盘龙纹（斜纹）
        b.line([(12, y + 2), (16, y)])
    b.poly([(0, 7), (27, 7), (27, 10), (0, 10)], 0.0)              # 云板
    b.line([(0, 7), (2, 5), (4, 6)])
    b.line([(27, 7), (25, 5), (23, 6)])
    b.point(2, 8)
    b.point(25, 8)
    b.poly([(6, 0), (22, 0), (20, 3), (8, 3)], 0.0)                # 承露盘
    return b.sprite()


HUABIAO = _huabiao()
YOUTH = Sprite("""
  .###.
 #.#..#
 ##...#
  #...#
  .###.
  ..#..
 .#####.
 #.###.#
 ..###..
 ..###..
 .#####.
 .#...#.
 .#...#.
 .#...#.
 ##...##
""")

MX_HEAD = """
...##...
..####..
..#.#...
..######
..##....
...#....
...#....
..###...
"""
MX_UP = """
........
#......#
.#....#.
..#..#..
...##...
...##...
........
........
"""
MX_DOWN = """
........
........
...##...
..####..
.#.##.#.
#......#
........
........
"""


def crane_stand(g: Gfx, x: float, y: float, face: int = 1, pose: str = "up", k: float = 0.0, one_leg: bool = False,
                crouch: float = 0.0):
    """站立的鹤：脚在 (x, y)。pose: up 平常 / preen 梳羽 / call 仰头鸣 / look 低头看。k 0..1 姿势进度"""
    f = face
    cy = y - 11 + crouch * 3
    bx = x - 2 * f
    # 黑尾（三级飞羽垂在身后）
    for j in range(3):
        g.d.line((bx - 4 * f, cy - 2 + j, bx - (10 + j) * f, cy + 1 + j * 2), fill=1)
    # 身体
    g.d.ellipse((bx - 7, cy - 4, bx + 7, cy + 4), fill=0, outline=1)
    g.d.line((bx - 3 * f, cy - 1, bx + 3 * f, cy - 2), fill=1)       # 翅缘
    # 腿
    g.d.line((x - 1, cy + 4, x - 1, y), fill=1)
    g.d.line((x - 3, y, x + 1, y), fill=1)
    if one_leg:
        g.d.line((x + 1, cy + 4, x + 3, cy + 7, x + 1, cy + 8), fill=1)
    else:
        g.d.line((x + 1, cy + 4, x + 2, y), fill=1)
        g.d.line((x + 1, y, x + 4, y), fill=1)
    # 颈与头
    nx0, ny0 = bx + 5 * f, cy - 2
    if pose == "preen":       # 低头伸进背羽里梳理
        hx, hy = bx + lerp(6, -1, k) * f, lerp(cy - 14, cy - 6, k)
        mid = (bx + 9 * f, cy - 10)
        beak = (-f * 3, 3)
    elif pose == "call":      # 仰头向天
        hx, hy = bx + lerp(6, 8, k) * f, lerp(cy - 14, cy - 16, k)
        mid = (bx + 7 * f, cy - 8)
        beak = (f * lerp(5, 2, k), lerp(0, -5, k))
    elif pose == "look":      # 低头看下面
        hx, hy = bx + lerp(6, 10, k) * f, lerp(cy - 14, cy - 9, k)
        mid = (bx + 10 * f, cy - 9)
        beak = (f * 3, lerp(0, 4, k))
    else:
        hx, hy = bx + 6 * f, cy - 14
        mid = (bx + 9 * f, cy - 8)
        beak = (f * 5, 1)
    pts = []
    for i in range(7):        # 二次曲线的 S 颈
        u = i / 6
        px = (1 - u) ** 2 * nx0 + 2 * (1 - u) * u * mid[0] + u * u * hx
        py = (1 - u) ** 2 * ny0 + 2 * (1 - u) * u * mid[1] + u * u * hy
        pts.append((px, py))
    g.d.line(pts, fill=1, width=2)
    g.d.ellipse((hx - 2, hy - 2, hx + 2, hy + 1), fill=1)
    g.px(hx + f, hy - 3)                                             # 丹顶
    g.px(hx, hy - 3)
    g.px(hx + f, hy - 1, 0)                                          # 眼
    g.d.line((hx + 2 * f, hy, hx + 2 * f + beak[0], hy + beak[1]), fill=1)


def crane_fly(g: Gfx, x: float, y: float, flap: float, face: int = 1, s: float = 1.0):
    """飞翔的鹤：身体中心 (x, y)，flap 为扇翅相位（弧度），s 缩放"""
    f = face
    w = math.sin(flap)
    up = -1 if w >= 0 else 1
    span_ = 15 * s * abs(w) + 3 * s
    # 远侧翅（翅膀抬起时在身后露出一点）
    if w > 0.3:
        g.d.line((x - 1 * f * s, y - 2, x + 2 * f * s, y - span_ * 0.8, x - 3 * f * s, y - span_ * 0.7), fill=1)
    g.d.ellipse((x - 6 * s, y - 2 * s, x + 5 * s, y + 2 * s), fill=0, outline=1)
    g.d.line((x + 4 * f * s, y - 1, x + 13 * f * s, y - 3 * s), fill=1, width=2 if s >= 0.8 else 1)   # 直颈前伸
    hx, hy = x + 13 * f * s, y - 3 * s
    g.d.rectangle((hx - 1, hy - 1, hx + 1, hy + 1), fill=1)
    g.px(hx, hy - 2)
    g.d.line((hx + 1 * f, hy, hx + 5 * f * s, hy + 1), fill=1)                                   # 喙
    g.d.line((x - 5 * f * s, y + 1, x - 15 * f * s, y + 2 * s), fill=1)                          # 长腿后拖
    # 近侧翅：前缘、翅尖黑羽（实心）、后缘锯齿
    tip = (x - 2 * f * s, y + up * span_)
    lead = [(x + 3 * f * s, y - 1), (x + 2 * f * s, y + up * span_ * 0.6), tip]
    trail = [(x - 6 * f * s, y + up * span_ * 0.8), (x - 5 * f * s, y + up * span_ * 0.4), (x - 4 * f * s, y)]
    g.d.polygon(lead + trail, fill=0, outline=1)
    g.d.polygon([tip, (x - 6 * f * s, y + up * span_ * 0.8), (x - 3 * f * s, y + up * span_ * 0.65)], fill=1)


@register
class CraneReturns(Rest):
    id = "x4.crane"
    name = "鹤归华表"
    desc = "仙鹤立在城门华表上梳羽长鸣；少年举弓，鹤便腾空盘旋吟出丁令威的诗，再落回柱顶"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.poem0 = self.rng.randrange(4)

    # ------------------------------------------------------------ 布景

    def city(self, g: Gfx):
        """远处的城郭：垛口城墙 + 城门楼（细线）"""
        y = 47
        g.d.line((72, y, 127, y), fill=1)
        for x in range(74, 128, 6):
            g.d.rectangle((x, y - 2, x + 2, y), fill=1)
        g.d.line((72, y, 72, GROUND), fill=1)
        g.d.line((72, 54, 127, 54), fill=1)
        # 城门楼
        g.d.rectangle((92, 40, 112, 46), fill=0, outline=1)
        g.d.polygon([(87, 41), (117, 41), (111, 36), (93, 36)], fill=0, outline=1)
        g.d.line((99, 36, 105, 36), fill=1)
        g.d.line((102, 33, 102, 36), fill=1)
        g.d.arc((97, 49, 107, 63), 180, 360, fill=1)  # 城门洞
        g.d.line((97, 56, 97, GROUND), fill=1)
        g.d.line((107, 56, 107, GROUND), fill=1)
        # 城外的坟冢（冢累累）
        for i, x in enumerate((82, 120)):
            g.d.arc((x - 4, 57, x + 4, 65), 180, 360, fill=1)

    def scenery(self, g: Gfx, t: float):
        g.d.line((0, GROUND, 127, GROUND), fill=1)
        self.city(g)
        for i in range(2):  # 远云
            x = (rand(i, self.seed) * 160 + t * (1.5 + i)) % 170 - 30
            y = 8 + i * 11
            g.d.line((x, y, x + 16, y), fill=1)
            g.d.line((x + 5, y - 2, x + 12, y - 2), fill=1)
        g.blit(HUABIAO, PX - 14, PY)

    # ------------------------------------------------------------ 鹤的日常

    def idle(self, t: float):
        """返回 (pose, k, face, one_leg)"""
        face = 1 if int((t + 9) // 23) % 3 != 2 else -1
        one_leg = int((t + 4) // 31) % 2 == 1
        k = (t + 3) % 17
        if k < 3.0:
            return "preen", span(k, 0, 0.6) * (1 - span(k, 2.4, 3.0)), face, one_leg
        k = (t + 11) % 29
        if k < 2.6:
            return "call", span(k, 0, 0.4) * (1 - span(k, 2.1, 2.6)), face, False
        return "up", 0.0, face, one_leg

    def calling(self, t: float) -> float:
        k = (t + 11) % 29
        return (k - 0.4) / 1.7 if 0.4 < k < 2.1 else -1

    # ------------------------------------------------------------ 少年举弓事件

    def event(self, t: float):
        if t < EV0:
            return None, 0
        n = int((t - EV0) // EV_P)
        return (t - EV0) % EV_P, n

    def youth(self, g: Gfx, k: float):
        if k > 12:
            return
        if k < 2:
            x = lerp(130, 54, ease_out(k / 2))
        elif k < 9:
            x = 54
        else:
            x = lerp(54, 132, ease_in((k - 9) / 3))
        walk = (k < 2 or k > 9) and int(k * 6) % 2
        y = GROUND - 15 - (1 if walk else 0)
        g.blit(YOUTH, x, y)
        if 2 < k < 7.5:   # 举弓：斜指柱顶的鹤
            r = span(k, 2, 2.6)
            ax, ay = x, y + 7 - r * 4
            dx, dy = -0.8, -0.6                      # 指向左上
            nx, ny = -dy, dx
            g.d.line((x + 1, y + 7, ax, ay), fill=1)   # 手臂
            pts = [(ax + nx * 6 * c + dx * 3 * (1 - c * c), ay + ny * 6 * c + dy * 3 * (1 - c * c))
                   for c in (-1, -0.5, 0, 0.5, 1)]
            g.d.line(pts, fill=1)                         # 弓
            g.d.line((pts[0], pts[-1]), fill=1)           # 弦
            g.d.line((ax + 2, ay + 1, ax + dx * 8, ay + dy * 8), fill=1)   # 箭

    def flight(self, k: float):
        """事件中鹤的位置：返回 (x, y, flap, face) 或 None（在柱上）"""
        if k < 3.0 or k >= 15.5:
            return None
        if k < 4.0:      # 起飞：斜向上
            p = ease_in(k - 3.0)
            return PX + p * 14, PY - 12 - p * 10, k * 14, 1
        if k < 13.0:     # 盘旋（椭圆）
            a = (k - 4.0) / 9.0 * 2 * math.pi * 1.5
            cx, cy = 74, 22
            x = cx + math.cos(a - math.pi * 0.85) * 44
            y = cy + math.sin(a - math.pi * 0.85) * 9
            face = 1 if -math.sin(a - math.pi * 0.85) > 0 else -1
            return x, y, k * 9, face
        p = ease_in_out((k - 13.0) / 2.5)  # 落回柱顶
        a = 9.0 / 9.0 * 2 * math.pi * 1.5 - math.pi * 0.85
        sx, sy = 74 + math.cos(a) * 44, 22 + math.sin(a) * 9
        return lerp(sx, PX, p), lerp(sy, PY - 12, p), k * (9 - 4 * p), -1 if sx > PX else 1

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        self.scenery(g, t)
        k, n = self.event(t)
        fl = self.flight(k) if k is not None else None
        if k is not None:
            self.youth(g, k)
        if fl:
            x, y, flap, face = fl
            crane_fly(g, x, y, flap, face)
            if 4.2 < k < 13.5:
                line = POEM[(self.poem0 + n) % 4]
                typewriter(g, 64, 1, line, k - 4.2, cps=1.6, align="center")
            mx_sprite(g, MX_UP if math.sin(flap) > 0 else MX_DOWN)
            return
        if k is not None and k < 3.0:   # 少年来了：鹤低头看，然后下蹲准备起飞
            pose, pk = "look", span(k, 1.0, 1.6)
            crouch = span(k, 2.5, 3.0)
            crane_stand(g, PX, PY, 1, pose, pk, False, crouch)
        elif k is not None and k < 17.0:  # 刚落下：收翅、整理
            crane_stand(g, PX, PY, -1 if k < 16 else 1, "up", 0, False, 1 - span(k, 15.5, 16.2))
        else:
            pose, pk, face, one = self.idle(t)
            crane_stand(g, PX, PY, face, pose, pk, one)
            c = self.calling(t)
            if c >= 0:
                hx = PX - 2 * face + 9 * face
                sound_arcs(g, hx + 2 * face, PY - 30, c % 1, n=3, gap=3, right=face > 0, spread=0.8)
                g.mx_level = 2
        mx_sprite(g, MX_HEAD)
        if (t % 5.1) < 0.15:
            g.mx[2, 4] = True
        c = self.calling(t)
        if c >= 0:
            for i in range(3):
                if int(c * 6) % 3 >= i:
                    g.mx_set(5 + i, 1 + i)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        self.scenery(g, t - T)
        if t < 2.2:   # 从右上飞来，绕一个弧落到柱顶
            p = ease_out(span(t, 0, 2.2))
            x = lerp(140, PX, p) + math.sin(p * math.pi) * 6
            y = lerp(-8, PY - 12, p) - math.sin(p * math.pi) * 10
            crane_fly(g, x, y, t * 10 * (1 - 0.5 * p), -1)
            mx_sprite(g, MX_UP if math.sin(t * 10 * (1 - 0.5 * p)) > 0 else MX_DOWN)
        else:         # 落定、收翅、转身
            crane_stand(g, PX, PY, -1 if t < 2.6 else 1, "up", 0, False, 1 - span(t, 2.2, 2.8))
            mx_sprite(g, MX_HEAD)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        self.scenery(g, t0 + t)
        k, n = self.event(t0)
        fl = self.flight(k) if k is not None else None
        if k is not None:
            self.youth(g, k)
        p = ease_in(span(t, 0, T))
        if fl:            # 正在天上：直接往高处冲
            x0, y0 = fl[0], fl[1]
            p = ease_in(span(t, 0, T))
        elif t < 0.25:
            crane_stand(g, PX, PY, 1, "up", 0, False, span(t, 0, 0.25))
            mx_sprite(g, MX_HEAD)
            g.fade(1 - span(t, T * 0.5, T))
            return
        else:
            x0, y0 = PX, PY - 12
            p = ease_in(span(t, 0.25, T))
        # 遂高上冲天
        x = x0 + p * 50
        y = y0 - p * 60
        crane_fly(g, x, y, t * 16, 1, s=1 - 0.4 * p)
        mx_sprite(g, MX_UP if math.sin(t * 16) > 0 else MX_DOWN, dy=-int(p * 6))
        g.fade(1 - span(t, T * 0.5, T))
