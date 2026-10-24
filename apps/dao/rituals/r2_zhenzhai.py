"""镇宅符：夜里，小道士把一道镇宅符“啪”地贴在宅门正中，然后守在门前；小鬼一来，门上符光一射，散成点。

依据：镇宅符贴于门户以镇邪（纸符“贴在门上”），民间镇宅俗语“姜太公在此，百无禁忌”；符用朱砂黄纸。

舞台（侧视）：右边一座宅门（鸱吻、瓦垄、瓦当、额枋斗拱、两根柱、双扇门带门钉和铺首门环、门槛台阶），
檐下两盏灯笼（逐帧摇）；左边夜空（星、月亮按 e 从东往西走），小道士守在门左边，面朝外。
入场：灯笼点亮；小道士手捧一道符走到门前，一跳“啪”地拍在门正中（震屏、火星、符光一闪），四角按实，退回守位。
持续：一轮 600 秒是一夜。每 47 秒来一只小鬼（两帧飘动），从左边飘近；小道士瞧见（惊讶脸）、转身剑指，
      门上的符放光，一颗光弹划弧越过小道士头顶打中小鬼：小鬼反白、发抖，散成火星和烟团；小道士拱手。
      其间：蝙蝠飞过、小道士打哈欠、来回巡一趟；灯笼摇、星星闪。
      续：天亮——太阳升起、屋脊上一只公鸡打鸣（“鸡鸣”），小道士伸个懒腰；转眼又入夜，灯笼重新点亮，“第几夜”加一。
中断：灯笼熄灭，门前的小鬼趁机溜走，小道士坐下打盹，“暂歇”。恢复：符先亮一下，灯笼重新点亮，小道士站起来。
圆满：门上的符放大光，光圈一圈圈扩出去，太阳升起，小道士作揖，“百无禁忌”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.fx import stars
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import act, boxed, floor, fist, fu_spr, mx_ring, ring, star4

FLOOR = 58
HX, HY = 64, 4                     # 宅门精灵左上角
FU_X, FU_Y = 93, 22                # 门上的符（左上角，7×15）
FU_C = (96, 29)
GUARD = 50                         # 小道士守位
LANTERNS = (67, 124)
LEAD = 10.0
GAP = 47.0
NG = 12
RENEW = 7.0
GHOST_END = (22, 31)


# ---------------------------------------------------------------- 道具

def _house():
    """宅门 64×54"""
    p = Part(64, 54)
    p.shape("rectangle", (6, 0, 57, 2), fill=1)                     # 正脊
    p.d.line((7, 1, 56, 1), fill=0)
    for x0, s in ((3, 1), (60, -1)):                                 # 鸱吻（两端上翘）
        p.shape("rectangle", (min(x0, x0 + 2 * s), 0, max(x0, x0 + 2 * s), 2), fill=1)
        p.px(x0 - s, -1 + 1), p.px(x0, 0, 0)
    p.shape("polygon", [(6, 3), (57, 3), (63, 8), (63, 11), (0, 11), (0, 8)], fill=1)  # 屋面
    for x in range(3, 61, 3):                                        # 瓦垄
        p.d.line((x, 4 if 6 <= x <= 57 else 6, x, 9), fill=0)
    p.px(0, 7), p.px(63, 7), p.px(0, 6), p.px(63, 6)                  # 飞檐起翘
    p.d.line((0, 10, 63, 10), fill=0)
    for x in range(1, 63, 2):                                        # 瓦当
        p.px(x, 10, 1)
    p.shape("rectangle", (3, 13, 60, 15), fill=1)                    # 额枋
    p.d.line((4, 14, 59, 14), fill=0)
    for x in range(5, 60, 4):
        p.px(x, 14, 1)
    for x in (8, 20, 41, 53):                                        # 斗拱
        p.shape("rectangle", (x, 16, x + 2, 17), fill=1)
        p.px(x + 1, 17, 0)
    for x in (5, 55):                                                # 柱
        p.shape("rectangle", (x, 16, x + 3, 50), fill=1)
        p.d.line((x + 2, 18, x + 2, 48), fill=0)
        p.shape("rectangle", (x - 1, 49, x + 4, 50), fill=1)          # 柱础
    p.shape("rectangle", (12, 18, 51, 50), fill=1)                   # 门框
    for x0 in (14, 32):                                              # 两扇门
        p.d.rectangle((x0, 20, x0 + 17, 48), fill=0, outline=1)
        p.d.rectangle((x0 + 2, 22, x0 + 15, 46), outline=1)
        for y in (36, 40, 44):                                       # 门钉
            for x in range(x0 + 4, x0 + 15, 3):
                p.px(x, y)
    p.d.line((31, 20, 31, 48), fill=1)
    for cx in (27, 36):                                              # 铺首 + 门环
        p.shape("rectangle", (cx - 1, 31, cx + 1, 32), fill=1)
        p.d.ellipse((cx - 2, 32, cx + 2, 36), outline=1)
    p.shape("rectangle", (10, 49, 53, 50), fill=1)                   # 门槛
    p.d.line((11, 49, 52, 49), fill=0)
    p.shape("rectangle", (6, 51, 57, 53), fill=1)                    # 台阶
    p.d.line((7, 52, 56, 52), fill=0)
    p.dither((44, 51, 57, 53), 0.5, 0)
    return p.sprite()


GHOST = pix.frames("""
   #####
  #######
 #########
 ##..#..##
##.#.#.#.##
 ##..#..##
 #########
 ####.####
##########
 #########
 # ### ###
 #  #   #
---
   #####
  #######
 #########
 ##..#..##
##.#.#.#.##
 ##..#..##
 #########
 ####.####
##########
 #########
 ### ### #
  #   #  #
""")

BAT = pix.frames("""
#.......#
##.#.#.##
 #######
   ###
---
   .#.
  #####
 ## # ##
#       #
""")

ROOSTER = pix.frames("""
  ##
 ###.
 #.##
  ###     #
  ####   ##
  ######.##
  ########
   ######
    ####
    #  #
   ##  ##
---
  ##
 ###.#
 #.##.
  ###     #
  ####   ##
  ######.##
  ########
   ######
    ####
    #  #
   ##  ##
""")


def _lantern(lit: bool):
    """灯笼 7×11：提梁、顶盖、鼓肚灯身（竖骨）、底盖、穗子"""
    p = Part(7, 11)
    p.shape("rectangle", (2, 0, 4, 0), fill=1)
    p.shape("ellipse", (0, 1, 6, 8), fill=1)
    if lit:
        p.d.line((3, 2, 3, 7), fill=0)
        p.px(1, 4, 0), p.px(5, 4, 0), p.px(1, 5, 0), p.px(5, 5, 0)
    else:
        p.d.ellipse((1, 2, 5, 7), fill=0)
        p.d.line((3, 2, 3, 7), fill=1)
    p.shape("rectangle", (2, 8, 4, 8), fill=1)
    p.shape("line", (3, 9, 3, 10), fill=1)
    return p.sprite()


_P: dict = {}


def prop(name):
    if name not in _P:
        _P[name] = {"house": _house, "lit": lambda: _lantern(True), "dark": lambda: _lantern(False)}[name]()
    return _P[name]


@register
class ZhenZhai(Ritual):
    id = "r2.zhenzhai"
    name = "镇宅符"
    desc = "小道士把镇宅符“啪”地贴上宅门，守在门前；夜里小鬼飘来，门上符光一射散成点，天亮鸡鸣再入夜"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.last_t = None
        self.sky_seed = self.rng.randrange(100)

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    # ------------------------------------------------------------ 布景

    def night(self, g: Gfx, t: float, u: float, day: float = 0.0):
        """夜空：星星、按 u 移动的月亮；day > 0 时换成日出"""
        if day <= 0:
            stars(g, t, self.sky_seed, n=22, box=(0, 0, 64, 44))
            q = u / self.CYCLE
            mx_, my = lerp(30, 58, q), 16 - math.sin(q * math.pi) * 8
            g.d.ellipse((mx_ - 4, my - 4, mx_ + 4, my + 4), fill=1)
            g.d.ellipse((mx_ - 2, my - 5, mx_ + 5, my + 2), fill=0)
        else:
            self.sun(g, t, day)
        floor(g, FLOOR)
        self.wall(g)

    def wall(self, g: Gfx):
        """远处一道矮院墙：墙帽瓦片 + 墙身"""
        g.d.line((0, 42, 60, 42), fill=1)
        for x in range(0, 60, 3):
            g.px(x + 1, 41)
        g.d.line((0, 44, 60, 44), fill=1)
        for x in range(2, 60, 8):
            g.px(x, 46), g.px(x + 4, 49)

    def sun(self, g: Gfx, t: float, k: float):
        """日出：太阳从院墙后升起，光芒转动"""
        cy = lerp(50, 28, ease_out(min(k, 1)))
        cx = 26
        g.d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=1)
        g.d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=0)
        g.d.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=1)
        for i in range(8):
            a = i * math.pi / 4 + t * 0.5
            g.d.line((cx + math.cos(a) * 8, cy + math.sin(a) * 8, cx + math.cos(a) * (10 + (i % 2)),
                      cy + math.sin(a) * (10 + (i % 2))), fill=1)
        g.d.rectangle((0, 42, 60, FLOOR - 1), fill=0)

    def house(self, g: Gfx, t: float, lit=(True, True), fu: float = 1.0, glow: float = 0.0):
        pix.blit(g, prop("house"), HX, HY)
        if fu > 0:
            spr = fu_spr(7, 15, 2)
            if fu < 1:
                spr = pix.stretch(spr, 1.0, max(0.2, fu))
            pix.blit(g, spr, FU_X, FU_Y + (15 - spr.h) // 2)
        if glow > 0:  # 符光：四周短光芒
            n = 8
            for i in range(n):
                a = i * 2 * math.pi / n + t * 0.6
                r0, r1 = 10, 10 + 3 * glow + (int(t * 8 + i) % 2)
                g.d.line((FU_C[0] + math.cos(a) * r0, FU_C[1] + math.sin(a) * r0 * 1.2,
                          FU_C[0] + math.cos(a) * r1, FU_C[1] + math.sin(a) * r1 * 1.2), fill=1)
        for k, x in enumerate(LANTERNS):
            sway = math.sin(t * 1.6 + k * 1.3) * 1.2
            g.d.line((x, 19, x + sway * 0.5, 22), fill=1)
            spr = prop("lit" if lit[k] else "dark")
            pix.blit(g, spr, x - 3 + round(sway), 22)
            if lit[k] and int(t * 3 + k) % 5 == 0:
                g.px(x + round(sway) - 4, 26), g.px(x + round(sway) + 4, 25)

    # ------------------------------------------------------------ 小鬼

    def ghost_state(self, u: float):
        """一轮内第 u 秒：(第几只, 这只的 k 秒) 或 None"""
        if u < LEAD:
            return None
        j = int((u - LEAD) // GAP)
        if j >= NG:
            return None
        return j, (u - LEAD) - j * GAP

    def ghost_pos(self, j: int, k: float):
        q = ease_out(span(k, 0, 9.0))
        x = lerp(-12, GHOST_END[0], q)
        y = GHOST_END[1] + math.sin(k * 2.2 + j) * 2.5 - (1 - q) * 6 * math.sin(j)
        return x, y

    def draw_ghost(self, g: Gfx, x: float, y: float, t: float, hit: bool = False, shiver: bool = False):
        spr = pix.anim(GHOST, t, 4)
        if shiver:
            x += (1 if int(t * 30) % 2 else -1)
        if hit:  # 被打中：压扁一下，四周迸光
            spr = pix.stretch(spr, 1.4, 0.7)
            for a in range(8):
                ca, sa = math.cos(a * math.pi / 4), math.sin(a * math.pi / 4)
                g.d.line((x + ca * 9, y + sa * 7, x + ca * 12, y + sa * 9), fill=1)
        pix.blit(g, spr, x - spr.w / 2, y - spr.h / 2)

    def dao_guard(self, g: Gfx, t: float, k: float | None):
        """守门的小道士：k = 这只小鬼的时间（None = 平静）"""
        if k is not None:
            if 6.0 < k < 9.0:
                return daoshi(g, GUARD, FLOOR, "idle", t, flip=True, face="wow")
            if 9.0 <= k < 11.6:
                return daoshi(g, GUARD, FLOOR, "point", t, flip=True)
            if 11.6 <= k < 13.8:
                return daoshi(g, GUARD, FLOOR, "bow" if k > 12.3 else "gongshou", t, flip=True, face="happy")
            if 22.0 < k < 24.0:  # 打哈欠
                return act(g, GUARD, FLOOR, t, ang=-1.5, L=13, flip=True, face="wow")
            if 30.0 < k < 37.0:  # 来回巡一趟
                q = k - 30.0
                if q < 3.0:
                    x = lerp(GUARD, 30, ease_in_out(q / 3.0))
                    return daoshi(g, x, FLOOR, "walk", t, flip=True)
                if q < 3.4:
                    return daoshi(g, 30, FLOOR, "idle", t)
                if q < 6.4:
                    x = lerp(30, GUARD, ease_in_out((q - 3.4) / 3.0))
                    return daoshi(g, x, FLOOR, "walk", t)
                return daoshi(g, GUARD, FLOOR, "idle", t, flip=True)
        return daoshi(g, GUARD, FLOOR, "idle", t, flip=True)

    def bat(self, g: Gfx, t: float, k: float):
        if 18.0 < k < 21.0:
            q = span(k, 18.0, 21.0)
            x, y = lerp(-8, 70, q), 10 + math.sin(q * 9) * 3
            pix.blit(g, pix.anim(BAT, t, 8), x, y)

    def ghost_event(self, g: Gfx, t: float, j: int, k: float, dt: float):
        """小鬼：飘近 → 符光弹 → 打中发抖 → 散"""
        if k < 11.4:
            x, y = self.ghost_pos(j, k)
            self.draw_ghost(g, x, y, t, hit=10.6 <= k < 10.8, shiver=10.6 <= k < 11.4)
        if 10.0 <= k < 10.6:  # 光弹
            q = span(k, 10.0, 10.6)
            gx, gy = self.ghost_pos(j, 10.6)
            x = lerp(FU_C[0], gx, q)
            y = lerp(FU_C[1], gy, q) - math.sin(q * math.pi) * 22
            g.d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=1)
            g.px(x, y, 0)
            for m in range(1, 5):
                qq = max(q - m * 0.05, 0)
                g.px(lerp(FU_C[0], gx, qq), lerp(FU_C[1], gy, qq) - math.sin(qq * math.pi) * 22)
        if 10.6 <= k < 10.6 + dt:
            pix.shake(g, t, 1.0)
        if 11.4 <= k < 11.4 + dt:
            x, y = self.ghost_pos(j, 11.4)
            self.sparks.burst(x, y, 18, 30, up=6, life=0.8, gravity=20)
            for m in range(4):
                self.puffs.emit(x + (m - 1.5) * 3, y, vy=-5, life=0.9, rmax=2.0, spread=2)

    def mx(self, g: Gfx, t: float, gk=None, glow: float = 0.0):
        """点阵：门上的符（竖条带格）；小鬼靠近时左边一个闪点；符光扩散时光环"""
        g.mx[1:7, 3:5] = True
        g.mx[2, 3] = g.mx[4, 4] = g.mx[5, 3] = False
        if gk is not None:
            j, k = gk
            if k < 11.4:
                x = int(lerp(0, 1.9, span(k, 0, 9)))
                if int(t * 4) % 2 or k > 9:
                    g.mx_set(x, 3 + int(math.sin(k * 2.2) * 1.4))
            if 10.0 <= k < 11.4:
                mx_ring(g, (k - 10.0) * 4)
                g.mx_level = 4
        if glow > 0:
            mx_ring(g, (t * 4) % 5)

    def counter(self, g: Gfx, e: float, label: str | None = None, pop: float = 1.0, size: int = 8):
        n = int(e // self.CYCLE) + 1
        boxed(g, 4, 4, label or (f"第{cn_num(n)}夜" if n < 100 else f"{n}夜"), size=size, pop=pop)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        self.night(g, t, 0.0)
        lit = (t > 0.5, t > 0.8)
        stuck = t >= 3.3
        self.house(g, t, lit, fu=1.0 if stuck else 0.0, glow=1 - span(t, 3.3, 4.2) if stuck else 0)
        if 0.5 <= t < 0.5 + dt or 0.8 <= t < 0.8 + dt:
            x = LANTERNS[0] if t < 0.7 else LANTERNS[1]
            self.sparks.burst(x, 27, 5, 12, life=0.4)
        if t < 2.4:  # 捧符走到门前
            x = lerp(-12, 86, ease_out(span(t, 0, 2.4)))
            h = act(g, x, FLOOR, t, ang=-0.3, L=10, legs="walk")["hand"]
            pix.blit(g, fu_spr(5, 11, 2), h[0] - 2, h[1] - 10)
            fist(g, *h)
        elif t < 3.3:  # 一跳，拍上去
            q = span(t, 2.4, 3.3)
            y = FLOOR - math.sin(min(q / 0.8, 1) * math.pi) * 8
            h = daoshi(g, 86, y, "raise", t, face="wow")["hand"]
            if t < 3.1:
                pix.blit(g, fu_spr(5, 11, 2), h[0] - 2, h[1] - 10)
        elif t < 4.2:  # 四角按实
            q = t - 3.3
            daoshi(g, 86, FLOOR, "raise" if int(q * 8) % 2 == 0 else "point", t, face="happy")
        else:  # 退回守位
            q = span(t, 4.2, 5.6)
            x = lerp(86, GUARD, ease_in_out(q))
            daoshi(g, x, FLOOR, "walk" if q < 1 else "idle", t, flip=True)
        if 3.3 <= t < 3.3 + dt:
            pix.shake(g, t, 1.4)
            self.sparks.burst(FU_C[0], FU_C[1], 16, 30, life=0.6, gravity=30)
        if 3.3 <= t < 3.45:
            pix.shake(g, t, 1.4)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, 0.0)
        self.mx(g, t)
        if t < 3.3:
            g.mx[:] = False
            g.mx_set(int(t * 3) % 8, 6)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            return self.renew(g, t, e, u, dt)
        self.night(g, t, u)
        gk = self.ghost_state(u)
        glow = span(gk[1], 9.0, 9.6) * (1 - span(gk[1], 10.6, 11.4)) if gk else 0.0
        self.house(g, t, glow=glow)
        if gk:
            self.bat(g, t, gk[1])
            self.ghost_event(g, t, gk[0], gk[1], dt)
        self.dao_guard(g, t, gk[1] if gk else None)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        self.mx(g, t, gk)

    def renew(self, g: Gfx, t: float, e: float, u: float, dt: float):
        """续：日出鸡鸣 → 伸懒腰 → 日落、灯笼复明"""
        day = span(u, 0.0, 1.2) * (1 - span(u, 4.4, 5.4))
        if day > 0:
            self.night(g, t, 0.0, day=day)
        else:
            self.night(g, t, 0.0 if u > 5 else self.CYCLE - 1)
        lit = (u > 5.6, u > 5.8)
        self.house(g, t, lit)
        if 5.6 <= u < 5.6 + dt or 5.8 <= u < 5.8 + dt:
            self.sparks.burst(LANTERNS[0] if u < 5.7 else LANTERNS[1], 27, 5, 12, life=0.4)
        if 1.0 < u < 4.4:  # 屋脊上的公鸡
            crow = 1.4 < u < 2.6
            pix.blit(g, pix.anim(ROOSTER, t, 6) if crow else ROOSTER[0], 6, 31, flip=True)
            if crow and int(t * 6) % 2 == 0:  # 打鸣的声线
                for j in range(3):
                    g.d.line((19 + j * 3, 31 - j, 20 + j * 3, 31 - j), fill=1)
        if 2.6 < u < 4.2:
            act(g, GUARD, FLOOR, t, ang=-1.6, L=14, flip=True, face="wow" if u < 3.4 else "happy")
        else:
            daoshi(g, GUARD, FLOOR, "idle", t, flip=True, face="sleep" if 1.0 < u < 2.6 else "normal")
        self.sparks.step(dt)
        self.sparks.draw(g)
        if 1.2 < u < 4.4:
            self.counter(g, e, "鸡鸣")
        else:
            self.counter(g, e if u > 4.4 else e - u - 1)
        self.mx(g, t)
        if day > 0.3:
            g.mx[:] = False
            g.mx[5:8, 1:7] = True
            g.mx[4, 2:6] = True
            g.mx[2, 1] = g.mx[2, 6] = g.mx[1, 3] = g.mx[1, 4] = int(t * 4) % 2 == 0

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        self.night(g, t, u)
        gk = self.ghost_state(u)
        lit = (t < 0.5, t < 0.8)
        self.house(g, t, lit)
        for k, x in enumerate(LANTERNS):
            if abs(t - (0.5, 0.8)[k]) < dt:
                self.puffs.emit(x, 25, vy=-5, life=0.9, rmax=1.6, spread=0)
        if gk and gk[1] < 11.4:  # 小鬼趁机溜走
            x, y = self.ghost_pos(gk[0], gk[1])
            self.draw_ghost(g, x - ease_in(span(t, 0.2, 1.4)) * 50, y, t)
        daoshi(g, GUARD, FLOOR, "idle" if t < 0.6 else "sleep", t, flip=True)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.counter(g, e, "暂歇")
        self.mx(g, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        self.night(g, t, u)
        gk = self.ghost_state(u)
        glow = span(t, 0.0, 0.3) * (1 - span(t, 0.7, 1.1))
        lit = (t > 0.6, t > 0.8)
        self.house(g, t, lit, glow=glow)
        if 0.6 <= t < 0.6 + dt or 0.8 <= t < 0.8 + dt:
            self.sparks.burst(LANTERNS[0] if t < 0.7 else LANTERNS[1], 27, 5, 12, life=0.4)
        if 0.2 <= t < 0.2 + dt:
            pix.flash(g)
        if gk and gk[1] < 11.4:
            x, y = self.ghost_pos(gk[0], gk[1])
            self.draw_ghost(g, x - (1 - ease_out(span(t, 0.8, 1.8))) * 50, y, t)
        if t < 1.0:
            daoshi(g, GUARD, FLOOR, "sleep" if t < 0.4 else "sit", t, flip=True, face="wow" if t > 0.4 else "sleep")
        else:
            self.dao_guard(g, t, gk[1] if gk else None) if t > 1.4 else daoshi(g, GUARD, FLOOR, "idle", t, flip=True)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        self.mx(g, t, None, glow)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        gk = self.ghost_state(u)
        day = span(t, 2.2, 4.0)
        self.night(g, t, u, day=day)
        glow = span(t, 0.0, 0.6)
        self.house(g, t, glow=glow if t < 3.0 else 1 - span(t, 3.0, 4.0))
        if 0.8 <= t < 0.8 + dt:
            pix.flash(g)
            self.sparks.burst(FU_C[0], FU_C[1], 24, 40, life=1.0, gravity=20)
            if gk and gk[1] < 11.4:
                x, y = self.ghost_pos(gk[0], gk[1])
                self.sparks.burst(x, y, 18, 30, up=6, life=0.8, gravity=20)
        if 0.8 < t < 1.1:
            pix.shake(g, t, 1.5)
        if gk and gk[1] < 11.4 and t < 0.8:
            x, y = self.ghost_pos(gk[0], gk[1])
            self.draw_ghost(g, x, y, t, shiver=True, hit=t > 0.6)
        for r in range(3):  # 光圈
            rr = (t - 0.8) * 30 - r * 12
            if 0 < rr < 60:
                ring(g, FU_C[0], FU_C[1], rr, step=2, sy=0.8)
        if t < 0.8:
            daoshi(g, GUARD, FLOOR, "point", t, flip=True)
        else:
            daoshi(g, GUARD, FLOOR, "bow" if 2.4 < t < 3.8 else "gongshou", t, face="happy")
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 2.6:
            self.counter(g, e, "百无禁忌", pop=ease_out_back(span(t, 2.6, 3.0)), size=12)
        else:
            self.counter(g, e)
        self.mx(g, t, None, glow=1.0)
        if t > 0.8:
            g.mx_level = 1 + int(6 * (1 - span(t, 0.8, 2.2)))
