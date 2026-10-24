"""摇帝钟：小道士高举帝钟（三清铃）摇响，声波一圈圈荡开；右边九级云阶通到天门，一团声光随计时一级级往上走。

帝钟又名三清铃、法铃，铜制，柄端作三叉（“山”字形，象征三清），摇铃召神驱邪。
九重天见《楚辞·天问》“圜则九重”。圆满句“声闻于天”出自《诗经·小雅·鹤鸣》。

入场：小道士走上来，举铃一摇，第一声荡开，九级云阶从下到上一级级浮现，天门在顶上显出。
持续：铃一阵一阵地摇（摆到两头“叮”一声、声波弧荡开、铃舌甩动），歇口气再摇；每 12 秒一次“重铃”：
      举高、猛摇，声波大、屏幕一震、火星。一轮 540 秒，每 60 秒声光跳上一级云阶，左上写“几重天”。
      续：天门打开，一道光落回铃上，九级云阶从上到下依次暗下，天门再关上，声光回到第一级。
中断：摆动渐停，另一只手托住铃口，写“止铃”。  恢复：手撤开，摆幅渐大，“叮”一声，声波荡开。
圆满：急摇，声光一口气冲上天门，天门大开放光，闪白，题“声闻于天”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r3_kit import (FLOOR, Clock, art, banner, banner_text, crossed, dim_spr, floor, hand_at, label, mx_ring,
                     pose_arm, put, rays, round_of, shear_spr, sparkle)

DX = 22
CYCLE = 540.0
LAYER = 60.0
RENEW = 6.0
STEPS = [(56 + i * 7, 54 - i * 5) for i in range(9)]    # 九级云阶（左端 x, 顶面 y）
GATE_X, GATE_Y = 105, 0

BELL = art("""
  #  #  #
  #  #  #
  #######
    .#.
    ###
    #.#
    ###
    .#.
   #####
  #######
  #######
  #.#.#.#
  #######
  ####.#.
 #####.#.#
 ######.#.
#########.#
.#########.
""", anchor=(5, 5), lip=(5, 17), body=(5, 10))

GATE = art("""
#       #       #
 ###############
#################
 #.#.#.#.#.#.#.#
   ###########
   #..#####..#
   ###########
   ##       ##
   ##       ##
   ##       ##
   ##       ##
   ##       ##
   ##       ##
  ####     ####
""", anchor=(0, 0))

DOOR = art("""
###
#.#
###
#.#
###
#.#
""", anchor=(0, 0))

STEP = art("""
    ##   ##
  ###########
 #####.#######
###.#####.#####
 .............
""", anchor=(0, 1))

PALM = art("""
 ####
######
######
#####
""", anchor=(2, 0))

MX_BELL = ["""
...#....
..###...
...#....
..###...
.#####..
.#####..
#######.
...#....
""", """
....#...
...###..
...#....
..###...
.#####..
.#####..
.######.
..#.....
""", """
..#.....
.###....
...#....
..###...
.#####..
.#####..
#######.
....#...
"""]


def bell_k(t: float, amp: float = 0.2, period: float = 0.56) -> float:
    """铃的摆动（错切量）"""
    return amp * math.sin(2 * math.pi * t / period)


def draw_bell(g: Gfx, hand, k: float, lag: float, glow: bool = False):
    """帝钟：错切表示摆动；铃舌比铃身慢半拍（lag 为铃舌的错切量）"""
    kq = round(k * 10) / 10
    spr = shear_spr(BELL, kq)
    pts = put(g, spr, hand[0], hand[1] - 1)
    lx, ly = pts["lip"]
    tx = lx - lag * 10
    g.d.line((lx, ly - 2, tx, ly + 2), fill=1)          # 铃舌
    g.d.rectangle((tx - 1, ly + 2, tx + 1, ly + 3), fill=1)
    if glow:
        sparkle(g, pts["body"][0] - 4, pts["body"][1] - 2, 2)
    return pts


def waves(g: Gfx, x: float, y: float, age: float, big: bool = False):
    """一声的声波：两道弧从铃口向右荡开（重铃时更大、更远，弧变成虚线散掉）"""
    reach = 44 if big else 24
    for j in range(2):
        r = 4 + age * (56 if big else 34) - j * 6
        if r < 3 or r > reach:
            continue
        a = 50 if r < 14 else 38
        box = (x - r, y - r, x + r, y + r)
        if r > reach * 0.7:   # 快散了：虚线
            for d in range(-a, a + 1, 8):
                g.px(x + math.cos(math.radians(d)) * r, y + math.sin(math.radians(d)) * r)
        else:
            g.d.arc(box, -a, a, fill=1)


def stair(g: Gfx, reached: int, t: float, dim_top: int = 9, gate_open: float = 0.0):
    """九级云阶 + 天门（reached = 已点亮的级数；dim_top 以上暗）"""
    for i, (x, y) in enumerate(STEPS):
        bob = int(round(math.sin(t * 1.3 + i * 0.8) * 0.6))
        spr = STEP if i < reached and i < dim_top else dim_spr(STEP)
        put(g, spr, x, y + bob)
    put(g, GATE, GATE_X, GATE_Y)
    # 门扇：关着的两扇带门钉；开时往两边收窄、门里放光
    w = int(round(3 * (1 - gate_open)))
    if w > 0:
        for dx in (5, 9 - (3 - w) + 0):
            pass
        pix.blit(g, DOOR, GATE_X + 5, GATE_Y + 7, outline=False)
        pix.blit(g, DOOR, GATE_X + 9, GATE_Y + 7, outline=False)
        if gate_open > 0:
            g.d.rectangle((GATE_X + 5 + w, GATE_Y + 7, GATE_X + 11 - w, GATE_Y + 12), fill=0)
    if gate_open > 0.3:
        cx = GATE_X + 8
        for yy in range(GATE_Y + 7, GATE_Y + 13):
            if (yy + int(t * 10)) % 2 == 0:
                g.d.line((cx - 1, yy, cx + 1, yy), fill=1)


def orb_pos(layer: float):
    i = int(layer)
    f = layer - i
    a = STEPS[min(i, 8)]
    if f <= 0 or i >= 8:
        return a[0] + 7, a[1] - 4
    b = STEPS[i + 1]
    q = ease_in_out(f)
    return lerp(a[0] + 7, b[0] + 7, q), lerp(a[1] - 4, b[1] - 4, q) - math.sin(q * math.pi) * 6


def orb(g: Gfx, x: float, y: float, t: float):
    """声光：带十字芒的小光团"""
    r = 2 + (int(t * 6) % 2)
    g.d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=0)
    g.d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=1)
    g.px(x, y, 0)
    g.d.line((x - r - 2, y, x - 4, y), fill=1)
    g.d.line((x + 4, y, x + r + 2, y), fill=1)
    g.d.line((x, y - r - 2, x, y - 4), fill=1)


@register
class DizhongRitual(Ritual):
    id = "r3.dizhong"
    name = "摇帝钟"
    desc = "小道士高举帝钟摇响，声波荡开；一团声光随计时沿九级云阶一级级上升，到天门开"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = CYCLE

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.clock = Clock()
        self.rings: list[list] = []     # [x, y, age, big]

    # ------------------------------------------------------------ 公用

    def ring(self, x, y, big=False):
        self.rings.append([x, y, 0.0, big])
        if big:
            self.sparks.burst(x, y, 10, 30, up=10, life=0.5, gravity=60)

    def fx(self, g: Gfx, dt: float):
        keep = []
        for r in self.rings:
            r[2] += dt
            if r[2] < (1.0 if r[3] else 0.7):
                waves(g, r[0], r[1], r[2], r[3])
                keep.append(r)
        self.rings = keep
        self.sparks.step(dt)
        self.sparks.draw(g)

    def shaker(self, g: Gfx, t: float, dt: float, amp: float, period: float = 0.56, kind: str = "reach",
               face: str = "normal", ring: bool = True, big: bool = False, glow: bool = False):
        """小道士摇铃：手随铃左右小抖，摆到两头敲响一声"""
        k = bell_k(t, amp, period)
        lag = bell_k(t - period * 0.18, amp * 1.3, period)
        h0 = hand_at(DX, FLOOR, kind, t)
        jig = int(round(k * 3))
        pts = None

        def prop(g2, h):
            nonlocal pts
            pts = draw_bell(g2, (h[0] + jig, h[1]), k, lag, glow)
        pose_arm(g, DX, kind, t, "fist", face=face, prop=prop)
        if ring and amp > 0.05:
            ph = (t / period) % 1
            ph0 = ((t - dt) / period) % 1
            for edge in (0.25, 0.75):
                if ph0 < edge <= ph or (edge == 0.25 and ph < ph0 and ph >= edge):
                    lx, ly = pts["lip"]
                    hard = big and not any(r[3] and r[2] < 0.5 for r in self.rings)
                    self.ring(lx + 4, ly - 4, hard)
                    if hard:
                        pix.shake(g, t, 1)
        if amp > 0.05:   # 两侧的抖动线
            lx, ly = pts["lip"]
            side = 1 if k > 0 else -1
            if abs(k) > amp * 0.7:
                for j in range(2):
                    g.d.line((lx + side * (8 + j * 2), ly - 6 + j * 2, lx + side * (8 + j * 2), ly - 4 + j * 2), fill=1)
        return pts, h0

    def layer_of(self, k: float) -> float:
        """声光在第几级（含两级之间跳的过程，跳 1.2 秒）"""
        i = min(int(k // LAYER), 8)
        f = span(k - i * LAYER, 0, 1.2) if i > 0 else 1.0
        return i - 1 + f if i > 0 and f < 1 else i

    def mx(self, g: Gfx, t: float, amp: float, reached: int):
        k = bell_k(t, amp)
        f = 0 if abs(k) < amp * 0.4 or amp < 0.05 else (1 if k > 0 else 2)
        g.mx_blit(MX_BELL[f])
        if amp > 0.05 and abs(k) > amp * 0.7:
            g.mx[2 + int(t * 8) % 3, 7] = True
        for i in range(min(reached, 8)):
            pass

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        floor(g)
        show = int(span(t, 2.4, 4.6) * 9.99)
        for i in range(show):
            put(g, STEP if i == 0 else dim_spr(STEP), *STEPS[i])
        if t > 4.6:
            pop = ease_out_back(span(t, 4.6, 5.2))
            put(g, GATE, GATE_X, GATE_Y - (1 - pop) * 8)
            pix.blit(g, DOOR, GATE_X + 5, GATE_Y - (1 - pop) * 8 + 7, outline=False)
            pix.blit(g, DOOR, GATE_X + 9, GATE_Y - (1 - pop) * 8 + 7, outline=False)
        if t < 2.0:
            x = lerp(-14, DX, ease_out(span(t, 0, 2.0)))
            h = daoshi(g, x, FLOOR, "walk", t)["hand"]
            put(g, BELL, h[0] + 1, h[1] - 8)
            amp = 0.0
        else:
            amp = 0.2 * span(t, 2.0, 2.6)
            self.shaker(g, t - 2.0, dt, amp)
        if t > 2.4:
            x, y = orb_pos(0)
            orb(g, x, y - (1 - span(t, 2.4, 3.0)) * 6, t)
        self.fx(g, dt)
        label(g, 3, 3, "一重天" if t > 2.4 else "帝钟")
        self.mx(g, t, amp, 0)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        if k >= CYCLE - RENEW:
            self.renew(g, k - (CYCLE - RENEW), t, dt)
            return
        floor(g)
        layer = self.layer_of(k)
        reached = int(layer) + 1
        stair(g, reached, t)
        # 摇铃节奏：摇 2.2 秒、歇 1.2 秒；每 12 秒一次重铃
        u = e % 12.0
        big = 8.6 < u < 10.2
        if big:
            if u < 9.0:         # 预备：举高、屏住
                self.shaker(g, e, dt, 0.0, face="normal", ring=False)
            else:
                self.shaker(g, e, dt, 0.3, period=0.4, face="wow", big=True)
            amp = 0.3
        else:
            v = u % 3.4
            amp = 0.2 if v < 2.2 else 0.2 * max(0, 1 - (v - 2.2) * 3)
            self.shaker(g, e, dt, amp)
        x, y = orb_pos(layer)
        orb(g, x, y, t)
        i = int(k // LAYER)
        if i > 0 and crossed(k - i * LAYER, dt, 1.2):    # 落上新一级：闪、火星
            self.sparks.burst(x, y + 3, 14, 26, up=10, life=0.6, gravity=60)
        if i > 0 and 1.2 <= k - i * LAYER < 1.4:
            sparkle(g, x, y, 5)
        self.fx(g, dt)
        label(g, 3, 3, f"{cn_num(min(int(layer + 0.5), 8) + 1)}重天")
        self.mx(g, e, amp, reached)

    def renew(self, g: Gfx, u: float, t: float, dt: float):
        """u ∈ [0, RENEW)：天门开 → 光落回铃上 → 云阶由上到下暗 → 门关，声光回第一级"""
        floor(g)
        op = span(u, 0.3, 1.2) * (1 - span(u, 4.6, 5.4))
        dim_top = 9 - int(span(u, 2.6, 4.4) * 8.99)
        stair(g, 9, t, dim_top=max(dim_top, 1), gate_open=op)
        pts, _ = self.shaker(g, t, dt, 0.0 if u < 4.4 else 0.2 * span(u, 4.4, 5.0), face="happy" if u > 1.6 else "normal",
                             glow=1.6 < u < 2.6)
        q = span(u, 1.0, 1.8)
        if 0 < q:   # 光从门里落到铃上
            gx, gy = GATE_X + 8, GATE_Y + 10
            bx, by = pts["body"]
            yy = lerp(gy, by - 4, ease_in_out(q))
            xx = lerp(gx, bx, ease_in_out(q))
            if u < 2.6:
                pix.dotted(g, gx, gy, xx, yy, 2, phase=int(t * 20))
                g.d.ellipse((xx - 2, yy - 2, xx + 2, yy + 2), fill=1)
        if crossed(u, dt, 1.8):
            bx, by = pts["body"]
            self.sparks.burst(bx, by, 16, 30, life=0.6)
        if 1.8 <= u < 1.87:
            pix.flash(g)
        layer = 8 if u < 2.0 else max(0.0, (dim_top - 1))
        x, y = orb_pos(min(layer, 8))
        if u < 1.8 or u > 4.4:
            orb(g, *orb_pos(8 if u < 1.8 else 0), t)
        self.fx(g, dt)
        label(g, 3, 3, "天门开" if 0.3 < u < 4.6 else ("九重天" if u <= 0.3 else "一重天"))
        self.mx(g, t, 0.2, 9)
        if op > 0.5:
            mx_ring(g, (u * 4) % 5)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        floor(g)
        k = e % CYCLE
        layer = self.layer_of(k)
        stair(g, int(layer) + 1, t)
        amp = 0.2 * max(0.0, 1 - t / 0.9)
        pts, _ = self.shaker(g, e + t, dt, amp)
        if t > 0.7:   # 另一只手托住铃口
            lx, ly = pts["lip"]
            put(g, PALM, lx, ly + 1 - int(4 * (1 - span(t, 0.7, 1.0))))
        orb(g, *orb_pos(layer), t)
        self.fx(g, dt)
        label(g, 3, 3, "止铃" if t > 0.7 else f"{cn_num(min(int(layer + 0.5), 8) + 1)}重天")
        self.mx(g, e + t, amp, 0)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        floor(g)
        k = e % CYCLE
        layer = self.layer_of(k)
        stair(g, int(layer) + 1, t)
        amp = 0.2 * span(t, 0.4, 1.2)
        pts, _ = self.shaker(g, e + t, dt, amp, face="happy" if t > 1.2 else "normal")
        if t < 0.4:
            lx, ly = pts["lip"]
            put(g, PALM, lx, ly + 1 + int(6 * span(t, 0, 0.4)))
        if crossed(t, dt, 0.6):
            lx, ly = pts["lip"]
            self.ring(lx + 4, ly - 4, True)
        orb(g, *orb_pos(layer), t)
        self.fx(g, dt)
        label(g, 3, 3, f"{cn_num(min(int(layer + 0.5), 8) + 1)}重天")
        self.mx(g, e + t, amp, 0)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        floor(g)
        k = e % CYCLE
        start = self.layer_of(k)
        layer = lerp(start, 8, ease_in_out(span(t, 0.3, 2.0)))
        op = span(t, 2.0, 2.6)
        stair(g, int(layer) + 1, t, gate_open=op)
        if op > 0.5:
            rays(g, GATE_X + 8, GATE_Y + 9, 12, 20, 10, rot=t * 0.8, dash=2)
        fast = t < 2.4
        self.shaker(g, t, dt, 0.3 if fast else 0.2, period=0.3 if fast else 0.6, kind="reach",
                    face="wow" if fast else "happy", big=fast)
        x, y = orb_pos(layer) if t < 2.0 else (GATE_X + 8, GATE_Y + 10 - span(t, 2.0, 2.8) * 8)
        if t < 2.0 and int(t * 30) % 2 == 0:
            self.sparks.burst(x, y, 1, 10, life=0.4, gravity=20)
        orb(g, x, y, t)
        if crossed(t, dt, 2.2):
            self.sparks.burst(GATE_X + 8, GATE_Y + 8, 30, 46, up=10, life=1.0, gravity=40)
        if 2.2 <= t < 2.3:
            pix.flash(g)
        if 2.2 <= t < 2.6:
            pix.shake(g, t, 1.5)
        self.fx(g, dt)
        if t > 2.6:
            banner(g, 66, 24, "声闻于天", span(t, 2.6, 3.0))
            banner_text(g, 66, 24, "声闻于天", span(t, 2.6, 3.0))
        else:
            label(g, 3, 3, f"{cn_num(min(int(layer + 0.5), 8) + 1)}重天")
        self.mx(g, t, 0.3, 9)
        if t > 2.2:
            mx_ring(g, (t - 2.2) * 4)
            g.mx_level = 1 + int(6 * (1 - span(t, 2.2, 3.6)))
