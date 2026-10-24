"""紫狐拜斗：野狐夜里击尾出火，戴着髑髅朝北斗下拜，想化成人形。

依据：段成式《酉阳杂俎》卷十五《诺皋记下》“旧说野狐名紫狐，夜击尾火出。将为怪，必戴髑髅拜北斗，
      髑髅不坠，则化为人矣。”
入场：夜色里北斗七星一颗颗亮起，野狐从右边草丛小跑进来，在土坡上坐下，尾巴一圈。
持续：狐狸蹲坐，大尾巴摇、耳朵抖、眨眼，旁边两点狐火飘；不时把尾巴往地上一击，溅出火星，冒起一朵狐火（夜击尾火出）。
      每 45 秒：叼起地上的髑髅戴在头上，人立起来，前爪合拢朝北斗拜三拜，每拜一下北斗亮几颗、连出斗线；
      多数时候髑髅一歪掉下来滚走，狐狸落回四脚、甩甩头；每三回里有一回髑髅不坠——一闪化成一个戴冠的书生，
      袍子后面还露着狐狸尾巴，站一会儿“噗”地一团烟又变回狐狸。
收场：狐狸一扭身窜进草丛，北斗淡去。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import flame, ring, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import art, mx_sprite

G = 56
FX = 54                   # 狐狸脚（前爪）的位置
SKULL_HOME = (74, G - 5)  # 髑髅平时躺在地上的位置（左上角）
EV0, EV_P = 15.0, 45.0
SPARK_P = 17.0
DIPPER = [(88, 15), (90, 22), (100, 24), (102, 17), (109, 12), (115, 9), (123, 10)]   # 天枢……摇光
MX_DIPPER = [(1, 2), (1, 4), (3, 5), (3, 3), (5, 2), (6, 1), (7, 1)]

SKULL = Sprite("""
 .#####.
 #.....#
 #.#.#.#
 #..#..#
 .#.#.#.
 ..###..
""")
SCHOLAR = art("""
....###....
...#####...
....#.#....
...#...#...
...#.#.#...
...#...#...
....###....
..#######..
.#.......#.
#..#...#..#
#..#...#..#
#.#.....#.#
##.......##
.#.......#.
.#...#...#.
.#...#...#.
#....#....#
#....#....#
#....#....#
###########
..##...##..
""")
MX_SKULL = """
.######.
#......#
#.##.##.
#.##.##.
#......#
.#.##.#.
..#..#..
..####..
"""
MX_MAN = """
...##...
..####..
...##...
.######.
#.####.#
..####..
..#..#..
.##..##.
"""

# 身体多边形：蹲坐 / 人立，点数相同，可以插值（相对前爪 (FX, G)，朝右）
BODY_SIT = [(-12, 0), (-17, -4), (-17, -10), (-14, -16), (-9, -20), (-4, -23), (2, -25), (4, -18), (4, -10), (5, 0)]
BODY_STAND = [(-5, -4), (-9, -8), (-9, -15), (-8, -22), (-6, -29), (-3, -33), (2, -34), (3, -28), (2, -18), (0, -8)]
HEAD_SIT, HEAD_STAND = (4, -29), (3, -38)
NECK = 6        # 颈前那个点（头和前爪绕它转）
HEAD = [(-4, -1), (-2, -4), (3, -4), (6, -2), (11, 0), (10, 1), (5, 2), (-2, 3)]
EARS = [[(-3, -3), (-2, -10), (1, -4)], [(0, -4), (3, -10), (4, -4)]]


def rot(pts, a, ox, oy):
    c, s = math.cos(a), math.sin(a)
    return [(ox + x * c - y * s, oy + x * s + y * c) for x, y in pts]


@register
class FoxDipper(Rest):
    id = "x4.fox"
    name = "紫狐拜斗"
    desc = "夜里野狐击尾出火；不时戴上髑髅人立拜北斗，髑髅多半掉下来，偶尔不坠就化成书生（还露着尾巴）"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.wisp = [(self.rng.uniform(10, 120), self.rng.uniform(26, 46), self.rng.uniform(0, 6)) for _ in range(2)]

    # ------------------------------------------------------------ 布景

    def ground(self, g: Gfx, t: float):
        g.d.line((0, G, 127, G), fill=1)
        # 残碑
        g.d.polygon([(2, G), (3, G - 18), (8, G - 20), (12, G - 17), (11, G)], fill=0, outline=1)
        g.d.line((5, G - 14, 9, G - 14), fill=1)
        g.d.line((5, G - 10, 8, G - 10), fill=1)
        for i, x in enumerate((16, 84, 92, 104, 117, 123)):          # 草
            sw = math.sin(t * 0.8 + i) * 1.2
            g.d.line((x, G, x - 1 + sw, G - 4 - i % 3), fill=1)
            g.d.line((x + 2, G, x + 3 + sw, G - 5), fill=1)

    def dipper(self, g: Gfx, t: float, lit: int = 0, link: float = 0.0, a: float = 1.0):
        """北斗：平时七个小点微闪；lit = 已被拜亮的颗数（亮的带十字），link 斗线"""
        n = int(round(a * 7))
        if link > 0:
            for i in range(min(lit, 7) - 1):
                (x0, y0), (x1, y1) = DIPPER[i], DIPPER[i + 1]
                for j in range(1, 6):
                    if rand(i * 7 + j, int(t * 3)) < link:
                        g.px(lerp(x0, x1, j / 6), lerp(y0, y1, j / 6))
            if lit >= 4:
                (x0, y0), (x1, y1) = DIPPER[0], DIPPER[3]
                for j in range(1, 6):
                    g.px(lerp(x0, x1, j / 6), lerp(y0, y1, j / 6))
        for i, (x, y) in enumerate(DIPPER[:n]):
            if i < lit:
                g.d.line((x - 2, y, x + 2, y), fill=1)
                g.d.line((x, y - 2, x, y + 2), fill=1)
            elif noise(t * 1.5 + i * 3, self.seed) > 0.2:
                g.px(x, y)
                if i in (0, 1):   # 天枢天璇略亮
                    g.px(x + 1, y)

    def wisps(self, g: Gfx, t: float):
        """飘着的两点狐火"""
        for i, (x0, y0, ph) in enumerate(self.wisp):
            x = x0 + math.sin(t * 0.21 + ph) * 18
            y = y0 + math.sin(t * 0.33 + ph * 2) * 5
            if noise(t * 0.7 + i * 9, self.seed + 4) > 0.3:
                flame(g, x, y, 3, 5, t, self.seed + i)

    # ------------------------------------------------------------ 狐狸

    def fox(self, g: Gfx, t: float, x: float = FX, stand: float = 0.0, bow: float = 0.0, look: float = 0.0,
            tail_lift: float = 0.0, skull: bool = False, shake: float = 0.0, blinking: bool = False,
            dy: float = 0.0):
        """stand 0 蹲坐 → 1 人立；bow 下拜（弧度）；look 低头看地（弧度）；tail_lift 尾巴抬起 0..1"""
        gy = G - dy
        s = ease_in_out(stand)
        body = [(x + lerp(a[0], b[0], s), gy + lerp(a[1], b[1], s)) for a, b in zip(BODY_SIT, BODY_STAND)]
        # 尾巴：从臀部向后贴地拖一大把，尾梢上卷，尾尖白
        rx, ry = body[1]
        sw = math.sin(t * 0.9) * 0.5 + (noise(t * 0.5, self.seed) - 0.5) * 0.6
        pts_top, pts_bot = [], []
        for i in range(9):
            u = i / 8
            cx = rx + 2 - u * 24
            base = lerp(ry + 2, gy - 3, min(1.0, u * 2))
            curl = max(0.0, u - 0.55) ** 2 * (30 + sw * 20) + tail_lift * u * 18
            cy = base - curl
            w = 2 + math.sin(min(u, 0.92) * math.pi) * 3.5
            pts_top.append((cx, cy - w))
            pts_bot.append((cx, min(cy + w, gy)))
        tail = pts_top + pts_bot[::-1]
        g.shade_poly(tail, 0.5)
        tip = pts_top[-2:] + pts_bot[-2:][::-1]
        g.d.polygon(tip, fill=0, outline=1)                     # 白尾尖
        g.d.polygon(body, fill=0, outline=1)
        if s > 0.3:   # 人立：后腿（大腿弧 + 小腿 + 脚掌朝前）
            hx, hy = body[1]
            g.d.arc((hx, hy - 6, hx + 10, hy + 6), 90, 250, fill=1)
            g.d.line((hx + 4, hy + 5, hx + 3, gy - 1, hx + 9, gy - 1), fill=1)
            g.d.line((hx + 7, hy + 4, hx + 7, gy - 3, hx + 12, gy - 2), fill=1)
        if s < 0.7:   # 蹲坐时的大腿弧线
            g.d.arc((x - 16, gy - 14, x - 4, gy + 2), 190, 320, fill=1)
        # 颈胸的白毛
        g.d.line((body[NECK][0] - 1, body[NECK][1] + 3, body[NECK + 1][0] - 1, body[NECK + 1][1] + 2), fill=1)
        # 前腿：蹲坐时撑地；人立时合在胸前（随下拜前倾）
        shx, shy = body[NECK]
        pivot = (shx - 2, shy + 2)
        a = bow * s + look
        if s < 0.5:
            g.d.line((x + 1, gy - 14, x + 2, gy), fill=1)
            g.d.line((x + 4, gy - 14, x + 5, gy), fill=1)
            g.d.line((x + 2, gy, x + 6, gy), fill=1)
        else:
            paws = rot([(2, 2), (8, 0), (9, -3)], a, pivot[0], pivot[1])
            g.d.line([pivot] + paws, fill=1)
        # 头：随下拜绕颈根转
        hx0, hy0 = lerp(HEAD_SIT[0], HEAD_STAND[0], s), lerp(HEAD_SIT[1], HEAD_STAND[1], s)
        hc = rot([(x + hx0 - pivot[0], gy + hy0 - pivot[1])], a, pivot[0], pivot[1])[0]
        hx, hy = hc[0] + math.sin(shake * 20) * shake * 2, hc[1]
        ha = a * 0.8
        for ear in EARS:
            g.d.polygon(rot(ear, ha, hx, hy), fill=0, outline=1)
        g.d.polygon(rot(HEAD, ha, hx, hy), fill=0, outline=1)
        ex, ey = rot([(3, -1)], ha, hx, hy)[0]
        if not blinking:
            g.px(ex, ey)
        else:
            g.d.line((ex - 1, ey, ex + 1, ey), fill=1)
        nx, ny = rot([(11, 0)], ha, hx, hy)[0]
        g.d.rectangle((nx - 1, ny - 1, nx, ny), fill=1)
        if skull:
            sx, sy = rot([(-2, -10)], ha, hx, hy)[0]
            g.blit(SKULL, sx - 2, sy)
        return hx, hy, ha

    # ------------------------------------------------------------ 击尾出火

    def spark(self, g: Gfx, t: float):
        """返回尾巴抬起程度；落下的一刻溅火星、冒一朵狐火"""
        if t < 6:
            return 0.0
        k = (t - 6) % SPARK_P
        if k > 4.5:
            return 0.0
        lift = span(k, 0, 0.6) * (1 - ease_in(span(k, 0.6, 0.8)))
        if k > 0.8:   # 火星 + 一朵狐火往上飘
            q = k - 0.8
            bx, by = FX - 36, G - 2
            for i in range(9):
                a = math.pi * (0.15 + 0.7 * rand(i, 12))
                v = 18 + rand(i, 13) * 18
                px = bx + math.cos(a) * v * q * (1 if i % 2 else -1) * 0.8
                py = by - math.sin(a) * v * q + 30 * q * q
                if q < 0.9 and py < G:
                    g.px(px, py)
            if q < 3.5:
                fy = by - 4 - q * 6
                flame(g, bx + math.sin(q * 2) * 3, fy, 4 - q * 0.6, 7 - q, t, self.seed + 7)
            if q < 2.5:
                g.text(2, 0, "夜击尾火出"[:int(q * 6) + 1])
        return lift

    # ------------------------------------------------------------ 拜斗事件

    def event(self, g: Gfx, t: float):
        """返回 fox 参数 dict，或 None（平常）"""
        if t < EV0:
            return None
        k = (t - EV0) % EV_P
        n = int((t - EV0) // EV_P)
        win = n % 3 == 2
        if k > 17.0:
            return None
        st = dict(stand=0.0, bow=0.0, look=0.0, skull=False, shake=0.0, lit=0, link=0.0, man=0.0, skull_pos=None,
                  text=None, tk=0.0, mx=None)
        if k < 2.0:                     # 低头叼起髑髅，戴上
            st["look"] = 0.7 * ease_in_out(span(k, 0, 0.8)) * (1 - ease_in_out(span(k, 1.2, 2.0)))
            if k > 1.0:
                st["skull"] = True
            else:
                st["skull_pos"] = SKULL_HOME
        elif k < 3.0:                   # 人立
            st["skull"] = True
            st["stand"] = ease_out(k - 2.0)
        elif k < 8.4:                   # 三拜
            st["skull"] = True
            st["stand"] = 1.0
            j = (k - 3.0) / 1.8
            i = int(j)
            u = j - i
            st["bow"] = math.sin(u * math.pi) * 0.55
            st["lit"] = (0, 2, 4)[min(i, 2)] + (3 if i >= 2 and u > 0.5 else 2 if u > 0.5 else 0)
            st["link"] = clamp((k - 3.0) / 5.4)
            st["text"], st["tk"] = "戴髑髅拜北斗", k - 2.0
            st["mx"] = "dipper"
        elif not win:                   # 髑髅一歪，掉下来滚回原处
            st["lit"] = 7 if k < 9.5 else 0
            st["link"] = 1.0 - span(k, 9.0, 9.6)
            st["stand"] = 1 - ease_in_out(span(k, 9.2, 10.0))
            st["shake"] = span(k, 10.2, 10.4) * (1 - span(k, 11.0, 11.4))
            q = span(k, 8.4, 10.6)
            hx, hy = FX + 1, G - 47
            x = lerp(hx, SKULL_HOME[0], q)
            y = hy + (SKULL_HOME[1] - hy) * min(1.0, q * 1.6) ** 2
            if q > 0.62:  # 落地后弹一下、滚过去
                y = SKULL_HOME[1] - abs(math.sin((q - 0.62) * 8)) * 3 * (1 - q)
            st["skull_pos"] = (x, y)
            st["mx"] = "skull"
            if k < 11.0:
                st["text"], st["tk"] = "戴髑髅拜北斗", 99
        else:                           # 髑髅不坠：化为人
            st["lit"] = 7
            st["link"] = 1.0
            if k < 9.2:
                st["skull"] = True
                st["stand"] = 1.0
                st["man"] = -span(k, 8.4, 9.2)     # 蓄光
            elif k < 15.5:
                st["man"] = 1.0
                st["link"] = 1 - span(k, 14.0, 15.5)
                st["lit"] = 7 if k < 14.5 else 0
            elif k < 16.2:
                st["man"] = 2.0 + (k - 15.5) / 0.7  # 噗一团烟
            st["text"], st["tk"] = ("髑髅不坠", k - 8.4) if k < 11.6 else ("则化为人", k - 11.6)
            st["mx"] = "man" if 9.2 <= k < 15.5 else "dipper"
            if k >= 15.5:
                st["skull_pos"] = SKULL_HOME
        return st

    # ------------------------------------------------------------ 一帧

    def frame(self, g: Gfx, t: float, x: float = FX, star_a: float = 1.0, fox_on: bool = True):
        self.ground(g, t)
        self.wisps(g, t)
        st = self.event(g, t)
        blinking = (t % 4.3) < 0.12
        if st is None:
            lift = self.spark(g, t)
            self.dipper(g, t, a=star_a)
            if fox_on:
                g.blit(SKULL, *SKULL_HOME)
                self.fox(g, t, x, tail_lift=lift, blinking=blinking)
                if not (t >= 6 and (t - 6) % SPARK_P < 2.5):
                    g.text(2, 0, "紫狐")
            self.mx_idle(g, t)
            return
        self.dipper(g, t, st["lit"], st["link"])
        man = st["man"]
        if 1.0 <= man < 2.0:            # 书生（袍后露一截狐尾）
            mx_, my_ = x - 6, G - SCHOLAR.h
            sw = math.sin(t * 2) * 1.5
            g.d.line((mx_ - 1, G - 6, mx_ - 6, G - 3 + sw, mx_ - 9, G - 8 + sw), fill=1, width=2)
            g.d.polygon([(mx_ - 9, G - 8 + sw), (mx_ - 12, G - 11 + sw), (mx_ - 8, G - 11 + sw)], fill=0, outline=1)
            g.blit(SCHOLAR, mx_, my_)
            g.d.line((mx_ + 9, my_ + 10, mx_ + 13, my_ + 8), fill=1)   # 作揖的手
        elif man >= 2.0:                # 噗：一团烟，变回狐狸
            q = man - 2.0
            self.fox(g, t, x, 0.0)
            for r in (6 + q * 10, 3 + q * 14):
                ring(g, x - 2, G - 18, r, 2, q * 3)
            if q < 0.6:
                g.d.ellipse((x - 12, G - 30, x + 8, G - 6), fill=0)
                for i in range(12):
                    a = rand(i, 3) * 2 * math.pi
                    g.px(x - 2 + math.cos(a) * 8 * (0.4 + q), G - 18 + math.sin(a) * 9 * (0.4 + q))
        else:
            self.fox(g, t, x, st["stand"], st["bow"], st["look"], 0.0, st["skull"], st["shake"], blinking)
            if man < 0:                 # 化形前的蓄光
                q = -man
                for i in range(10):
                    if blink(t + i * 0.13, 0.3, 0.5):
                        a = i / 10 * 2 * math.pi + t
                        g.px(x - 3 + math.cos(a) * (14 - q * 6), G - 22 + math.sin(a) * (18 - q * 8))
        if st["skull_pos"]:
            g.blit(SKULL, *st["skull_pos"])
        if st["text"]:
            typewriter(g, 2, 0, st["text"], st["tk"], cps=5)
        # 点阵
        m = st["mx"]
        if m == "skull":
            mx_sprite(g, MX_SKULL)
        elif m == "man":
            mx_sprite(g, MX_MAN)
            g.mx_level = 2
        else:
            self.mx_idle(g, t, st["lit"])
            if man < 0:
                g.mx_level = 1 + int(6 * -man)

    def mx_idle(self, g: Gfx, t: float, lit: int = 0):
        for i, (x, y) in enumerate(MX_DIPPER):
            if i < lit or noise(t * 1.5 + i * 3, self.seed) > 0.25:
                g.mx_set(x, y)
        if lit >= 7:
            g.mx_level = 3 if blink(t, 0.4) else 2
        # 底下一点狐火在跳
        fx = int(2 + 3 * noise(t * 0.4, self.seed + 9))
        g.mx_set(fx, 7)
        if blink(t, 0.5):
            g.mx_set(fx, 6)

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        self.ground(g, t - T)
        self.dipper(g, t - T, a=span(t, 0, 1.4))
        g.blit(SKULL, *SKULL_HOME)
        p = span(t, 0.8, 2.4)
        if p > 0:   # 小跑进来（用人立/蹲坐之间的低姿态，一颠一颠）
            x = lerp(140, FX, ease_out(p))
            hop = abs(math.sin(t * 9)) * 5 * (1 - span(p, 0.6, 1.0))
            self.fox(g, t, x, 0.0, tail_lift=0.4 * (1 - p), dy=hop)
        if t > 2.0:
            self.wisps(g, t - T)
        g.text(2, 0, "紫狐"[:int(span(t, 2.0, T) * 2 + 0.5)])
        self.mx_idle(g, t - T)
        if t < 1.4:
            g.mx[:6, :] &= False

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        p = ease_in(span(t, 0, T))
        self.ground(g, t0 + t)
        self.dipper(g, t0 + t, a=1 - span(t, 0.3, T))
        g.blit(SKULL, *SKULL_HOME)
        x = lerp(FX, 150, p)
        self.fox(g, t0 + t, x, 0.0, tail_lift=0.4 * span(t, 0, 0.3), dy=abs(math.sin(t * 9)) * 5 * span(t, 0.1, 0.4))
        self.mx_idle(g, t0 + t)
        g.fade(1 - span(t, T * 0.6, T))
