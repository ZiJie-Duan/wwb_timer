"""炼丹：八卦炉坐在丹灶上，炉童打扇看火候，文火武火交替，九转还丹。

入场：丹炉从天而降落在灶上（震起灰），炉童拿着蒲扇跑进来，扇子一扇，灶膛里火苗腾起。
持续：一转 10 分钟。火候按 e 推进：起火文火 → 武火 → 沐浴（文火）→ 武火 → 温养（文火）。
      武火时火舌舔着炉底、火星乱飞、炉盖咯咯跳、童子扇得飞快；文火时小火慢烧、童子慢慢扇。
      炉口丹气越冒越浓。一转满：炉盖一跳“噗”地冒出一团紫气，右侧“第几转”加一。
中断：童子放下扇子，火退成几点炭火，“封炉”。
恢复：童子猛扇几下，火重新旺起来。
圆满：火熄，炉盖冲天而起，一粒金丹升起放光，“九转丹成”。
"""
from __future__ import annotations

import math

from ..engine.anim import (blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise,
                           rand, smoothstep, span)
from ..engine.cn import cn_num
from ..engine.fx import Particles, flame, ring, smoke_wisp, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import draw_trigram
from .r4_kit import figure, glow_dot, pose

CX = 66
STOVE_Y = 46      # 灶台面
POT_Y = 34        # 炉腹中心
GROUND = 62
BOY_X = 20
RENEW = 4.0
# 火候表：(起点比例, 名, 火力 0..1)
HUOHOU = [(0.0, "文火", 0.25), (0.12, "武火", 1.0), (0.42, "沐浴", 0.2), (0.55, "武火", 1.0), (0.85, "温养", 0.3)]


def heat_at(p: float) -> tuple[float, str]:
    """一转中的进度 p → (火力, 名)；相邻两段之间 6% 平滑过渡"""
    for i, (a, name, h) in enumerate(HUOHOU):
        b = HUOHOU[i + 1][0] if i + 1 < len(HUOHOU) else 1.01
        if a <= p < b:
            prev = HUOHOU[i - 1][2] if i else h
            return lerp(prev, h, smoothstep((p - a) / 0.03)), name
    return HUOHOU[-1][2], HUOHOU[-1][1]


def stove(g: Gfx):
    """丹灶：砖砌，前面一个拱形灶门"""
    d = g.d
    d.rectangle((CX - 30, STOVE_Y, CX + 30, GROUND), outline=1, fill=0)
    d.line((CX - 32, STOVE_Y, CX + 32, STOVE_Y), fill=1)
    for r, y in enumerate(range(STOVE_Y + 4, GROUND, 4)):  # 砖缝
        d.line((CX - 30, y, CX + 30, y), fill=1)
        for x in range(CX - 30 + (r % 2) * 5, CX + 30, 10):
            d.line((x, y - 3, x, y - 1), fill=1)
    # 灶门
    d.rectangle((CX - 10, STOVE_Y + 6, CX + 10, GROUND), fill=0, outline=1)
    d.pieslice((CX - 10, STOVE_Y + 1, CX + 10, STOVE_Y + 13), 180, 360, fill=0, outline=1)
    d.rectangle((CX - 9, STOVE_Y + 7, CX + 9, GROUND - 1), fill=0)


def furnace(g: Gfx, dy: float = 0.0, lid_dy: float = 0.0, lid_rot: float = 0.0, lid: bool = True, glow: float = 0.0):
    """八卦炉：三足圆腹，双耳，炉身离卦，炉盖带钮"""
    d = g.d
    y = POT_Y + dy
    for x in (CX - 12, CX, CX + 12):  # 三足
        d.line((x, y + 8, x, STOVE_Y - 1 + dy), fill=1, width=3)
    body = (CX - 19, y - 11, CX + 19, y + 11)
    d.ellipse(body, fill=0, outline=1)
    g.shade((CX - 18, int(y + 3), CX + 18, int(y + 11)), 0.25)
    d.ellipse(body, outline=1)
    d.line((CX - 18, y - 4, CX + 18, y - 4), fill=1)  # 腰带
    d.line((CX - 16, y + 5, CX + 16, y + 5), fill=1)
    draw_trigram(g, CX - 5, int(y - 2), "离", w=11, h=1, step=2)
    for sx in (-1, 1):  # 双耳
        d.rectangle((CX + sx * 19 - (3 if sx > 0 else 0), y - 9, CX + sx * 19 + (3 if sx < 0 else 0) - sx * 0,
                     y - 8), fill=1)
        d.line((CX + sx * 22, y - 9, CX + sx * 22, y - 3), fill=1)
    d.rectangle((CX - 13, y - 13, CX + 13, y - 11), fill=1)  # 炉口
    if lid:
        ly = y - 13 + lid_dy
        c, s = math.cos(lid_rot), math.sin(lid_rot)
        pts = [(-14, 0), (-11, -4), (-5, -7), (5, -7), (11, -4), (14, 0)]
        rp = [(CX + px * c - py * s, ly + px * s + py * c) for px, py in pts]
        d.polygon(rp, fill=0, outline=1)
        kx, ky = CX - (-10) * s, ly + (-10) * c
        d.ellipse((kx - 2.5, ky - 2.5, kx + 2.5, ky + 2.5), fill=1)
        d.line((CX + (-8) * c - (-4) * s, ly + (-8) * s + (-4) * c, CX + 8 * c - (-4) * s, ly + 8 * s + (-4) * c),
               fill=1)
    if glow > 0:
        for i in range(10):
            a = i / 10 * 2 * math.pi + glow
            g.d.line((CX + math.cos(a) * 24, y + math.sin(a) * 15, CX + math.cos(a) * (24 + 5 * glow),
                      y + math.sin(a) * (15 + 4 * glow)), fill=1)


def fire(g: Gfx, heat: float, t: float, seed: int):
    """灶膛里的火：heat 0 = 几点炭，1 = 火舌冲出灶门"""
    d = g.d
    for j in range(5):  # 炭
        x = CX - 7 + j * 3.5
        if heat > 0.05 or blink(t + j * 0.31, 1.3, 0.6):
            d.rectangle((x, GROUND - 2, x + 1, GROUND - 1), fill=1)
    if heat <= 0.02:
        return
    for j, dx in enumerate((-5, 0, 5)):
        h = (4 + 9 * heat) * (0.75 + 0.25 * noise(t * 3 + j, seed + j))
        flame(g, CX + dx, GROUND - 2, 4 + 3 * heat, h, t + j * 0.4, seed + j)


def tongues(g: Gfx, heat: float, t: float, seed: int):
    """武火：火舌从炉底两侧窜上来，舔着炉腹（画在炉子前面）"""
    if heat <= 0.5:
        return
    for j, dx in enumerate((-21, -14, 14, 21)):
        h = (12 if abs(dx) > 18 else 8) * clamp((heat - 0.5) / 0.4) * (0.5 + 0.5 * noise(t * 5 + j, seed + 3))
        if h > 1.5:
            flame(g, CX + dx, STOVE_Y - 1, 5, h, t + j * 0.7, seed + 7 + j)


def boy(g: Gfx, x: float, fan: float, crouch: float = 0.0, s: float = 0.8, walk: float | None = None,
        amp: float = 1.0):
    """炉童：蹲着打蒲扇。fan = 扇子角度相位（弧度），amp = 扇幅（0 = 扇子放下不动）"""
    a = math.sin(fan) * amp - (1 - amp) * 0.9
    p = pose(lth=-35 * crouch - 4, lsh=10 * crouch - 2, rth=40 * crouch + 4, rsh=-5 * crouch + 2,
             lua=-15, lfa=40, rua=60 + 25 * a, rfa=100 + 35 * a, face=1, shw=4, hipw=2, rh=1)
    if walk is not None:
        k = math.sin(walk)
        p.update(lth=-18 * k, lsh=-18 * k, rth=18 * k, rsh=18 * k, shw=3.5, hipw=1)
    b = figure(g, p, x, GROUND, s=s)
    # 蒲扇：一片椭圆，柄在手里
    hx, hy = b.rhand
    ang = math.radians(100 + 35 * a)
    ux, uy = math.sin(ang), math.cos(ang)
    fx, fy = hx + ux * 6, hy + uy * 6
    g.d.line((hx, hy, fx, fy), fill=1)
    g.d.ellipse((fx - 3.5 + ux * 2, fy - 4.5 + uy * 2, fx + 3.5 + ux * 2, fy + 4.5 + uy * 2), fill=1)
    g.d.line((fx + ux * 2 - 2, fy + uy * 2, fx + ux * 2 + 2, fy + uy * 2), fill=0)
    return b


@register
class Furnace(Ritual):
    id = "r4.furnace"
    name = "炼丹"
    desc = "八卦炉坐在丹灶上，炉童打扇，文火武火按火候交替，一转一转炼到九转丹成"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.sparks = Particles(self.seed)
        self._t = None

    # ------------------------------------------------------------ 零件

    def phase(self, e: float) -> tuple[float, str, float]:
        p = (e % self.CYCLE) / self.CYCLE
        h, name = heat_at(p)
        return h, name, p

    _CUM: list | None = None

    def fan_phase(self, e: float, h: float = 0.0) -> float:
        """扇子相位 = 扇速（随火力，文火慢武火快）对 e 的积分；按秒预先累加，断线重连也一致"""
        cls = type(self)
        if cls._CUM is None:
            cum, acc = [0.0], 0.0
            for i in range(int(self.CYCLE)):
                acc += 2.0 + 9.0 * heat_at((i + 0.5) / self.CYCLE)[0]
                cum.append(acc)
            cls._CUM = cum
        cum = cls._CUM
        n, k = divmod(e, self.CYCLE)
        i = int(k)
        return n * cum[-1] + cum[i] + (cum[min(i + 1, len(cum) - 1)] - cum[i]) * (k - i)

    def texts(self, g: Gfx, e: float, name: str | None = None, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        nm = name if name is not None else self.phase(e)[1]
        g.vtext(2, 2, nm[:int(round(len(nm) * a))])
        r = right if right is not None else f"第{cn_num(n)}转"
        g.vtext(115, 2, r[:int(round(len(r) * a))])

    def qi(self, g: Gfx, e: float, t: float, amt: float, lid_dy: float = 0.0):
        """炉口冒的丹气：一转里越来越浓"""
        if amt <= 0:
            return
        top = POT_Y - 21 + lid_dy
        for i in range(1 + int(amt * 2.5)):
            x = CX - 9 + i * 6
            smoke_wisp(g, x, top, (top + 6) * min(1, 0.4 + amt), t, self.seed * 3 + i, sway=2.5,
                       speed=5 + i, drift=(i - 1.2) * 14, thick=1 + (amt > 0.6 and i == 1))

    def step_sparks(self, t: float, h: float):
        if self._t is None or t < self._t or t - self._t > 0.2:
            self._t = t
            return
        dt = t - self._t
        self._t = t
        if h > 0.6 and rand(int(t * 30), self.seed) < (h - 0.5):
            self.sparks.emit(CX + (rand(int(t * 31), 2) - 0.5) * 14, STOVE_Y + 6, 1, speed=30, spread=1.6, life=0.8)
        self.sparks.step(dt, gravity=25)

    def mx(self, g: Gfx, h: float, t: float, dan: float = 0.0):
        # 鼎：上 5 行；下 3 行：火
        for x in range(1, 7):
            g.mx[1, x] = True
        for y in (2, 3, 4):
            g.mx[y, 0] = g.mx[y, 7] = True
        for x in range(1, 7):
            g.mx[5, x] = True
        g.mx[0, 3] = g.mx[0, 4] = True
        if dan > 0:  # 丹：腹中一点，越炼越亮（闪烁的占空比）
            on = blink(t, 1.0, 0.25 + 0.7 * dan)
            g.mx[3, 3] = g.mx[3, 4] = on
            if dan > 0.6:
                g.mx[2, 3] = g.mx[2, 4] = g.mx[4, 3] = g.mx[4, 4] = on
        hgt = 1 + int(round(h * 2))
        for x in range(1, 7):
            k = noise(t * 6 + x * 1.7, self.seed) * hgt + 0.3
            for r in range(int(k)):
                g.mx_set(x, 7 - r)

    def scene(self, g: Gfx, t: float, e: float, h: float, boy_fan: float, rattle: float = 0.0, qi: float = 0.0,
              lid_dy: float = 0.0):
        stove(g)
        fire(g, h, t, self.seed)
        lid = -abs(math.sin(t * 23)) * 1.5 * rattle
        furnace(g, lid_dy=lid + lid_dy)
        tongues(g, h, t, self.seed)
        self.qi(g, e, t, qi, lid_dy)
        boy(g, BOY_X, boy_fan, crouch=1.0)

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        h, name, p = self.phase(e)
        if e >= self.CYCLE and k < RENEW:  # 一转满：炉盖一跳，冒一团紫气
            pop = math.sin(span(k, 0.3, 1.2) * math.pi)
            self.scene(g, t, e, max(h, 0.4), self.fan_phase(e, 0.2), qi=0.2, lid_dy=-6 * pop)
            r = span(k, 0.5, 3.0)
            if 0 < r < 1:
                ring(g, CX, POT_Y - 24, 4 + r * 26, 2, r)
                ring(g, CX, POT_Y - 24, 2 + r * 16, 3, -r)
            n = int(e // self.CYCLE)
            if k > 0.6:
                g.d.rectangle((CX - 16, 0, CX + 16, 13), fill=0)
                typewriter(g, CX, 1, f"{cn_num(n)}转", k - 0.6, cps=6, align="center")
            self.texts(g, e)
            self.mx(g, h, t, dan=1.0 if k < 2 else 0.0)
            g.mx_level = 4 if 0.5 < k < 1.0 else 1
            return
        rattle = clamp((h - 0.7) / 0.3)
        self.scene(g, t, e, h, self.fan_phase(e, h), rattle=rattle, qi=0.15 + 0.85 * p)
        self.step_sparks(t, h)
        self.sparks.draw(g)
        self.texts(g, e)
        self.mx(g, h, t, dan=p)

    def enter(self, g: Gfx, t: float):
        stove(g)
        drop = ease_out_bounce(span(t, 0, 1.2))
        furnace(g, dy=lerp(-60, 0, drop))
        if 0.45 < t < 1.4:  # 落灶扬灰
            k = span(t, 0.45, 1.4)
            for j in range(8):
                sd = -1 if j % 2 else 1
                g.px(CX + sd * (20 + k * 14 + j), STOVE_Y - 1 - math.sin(k * math.pi) * (3 + j % 3))
        h = ease_out(span(t, 3.0, 4.2)) * heat_at(0)[0]
        if t > 3.0:
            fire(g, h * (1 + 1.5 * math.sin(span(t, 3.0, 3.6) * math.pi)), t, self.seed)
        if t < 2.8:  # 童子跑进来
            x = lerp(-34, BOY_X, ease_out(span(t, 1.2, 2.6)))
            boy(g, x, 0, crouch=span(t, 2.4, 2.8), walk=t * 12 if t < 2.6 else None)
        else:  # 蹲下扇火：先猛扇几下
            boy(g, BOY_X, -(self.T["enter"] - t) * 12, crouch=1.0, amp=ease_out(span(t, 2.8, 3.1)))
        self.qi(g, 0, t, 0.15 * span(t, 3.6, 4.5))
        self.texts(g, 0, a=span(t, 3.4, 4.5))
        self.mx(g, h, t, dan=0.0)

    def interrupt(self, g: Gfx, t: float, e: float):
        h0, name, p = self.phase(e)
        k = ease_out(span(t, 0, 1.2))
        h = lerp(h0, 0, k)
        stove(g)
        fire(g, h, t, self.seed)
        furnace(g)
        tongues(g, h, t, self.seed)
        self.qi(g, e, t, (0.15 + 0.85 * p) * (1 - k))
        # 扇子越扇越慢、放下
        T = 1.2
        tt = min(t, T)
        boy(g, BOY_X, self.fan_phase(e) + (2 + 9 * h0) * (tt - tt * tt / (2 * T)), crouch=1.0, amp=1 - k)
        self.texts(g, e, right="封炉")
        self.mx(g, h, t, dan=p)

    def resume(self, g: Gfx, t: float, e: float):
        h1, name, p = self.phase(e)
        k = ease_in(span(t, 0.2, 1.6))
        flare = math.sin(span(t, 0.5, 1.4) * math.pi) * 0.6
        h = lerp(0, h1, k) + flare
        stove(g)
        fire(g, min(h, 1.2), t, self.seed)
        furnace(g)
        tongues(g, min(h, 1.2), t, self.seed)
        self.qi(g, e, t, (0.15 + 0.85 * p) * k)
        # 猛扇几下；相位倒着从 hold 的相位推，结尾正好接上
        T = self.T["resume"]
        fan = self.fan_phase(e) - (T - t) * 14
        boy(g, BOY_X, fan, crouch=1.0, amp=ease_out(span(t, 0, 0.3)))
        self.texts(g, e, right="封炉" if t < 0.6 else None)
        self.mx(g, h, t, dan=p)

    def complete(self, g: Gfx, t: float, e: float):
        h0, name, p = self.phase(e)
        h = lerp(h0, 0, ease_out(span(t, 0, 1.0)))
        stove(g)
        fire(g, h, t, self.seed)
        # 炉盖冲天：先抖，再飞
        shake = (math.sin(t * 40) * 1.5) if 0.6 < t < 1.5 else 0
        fly = ease_in(span(t, 1.5, 2.3))
        furnace(g, lid_dy=-fly * 60 + shake * 0.5 - abs(shake), lid_rot=fly * 2.5, glow=0)
        boy(g, BOY_X - ease_out(span(t, 1.5, 2.2)) * 4, self.fan_phase(e) + t * (2 + 9 * h0),
            crouch=1.0 - span(t, 1.6, 2.2) * 0.7, amp=1 - span(t, 0, 0.8))
        if t > 1.6:  # 金丹升起
            k = ease_out(span(t, 1.6, 3.2))
            y = lerp(POT_Y - 12, 12, k)
            r = 1 + 3 * k
            glow_dot(g, CX, y, r, t * 2, rays=t > 2.6)
            if t > 2.6:
                for j in range(12):
                    a = j / 12 * 2 * math.pi + t * 0.5
                    if blink(t + j * 0.21, 0.7, 0.6):
                        rr = 11 + 4 * math.sin(t * 4 + j)
                        g.d.line((CX + math.cos(a) * rr, y + math.sin(a) * rr * 0.8, CX + math.cos(a) * (rr + 4),
                                  y + math.sin(a) * (rr + 4) * 0.8), fill=1)
        if t < 1.5:
            self.texts(g, e, a=1 - span(t, 0.5, 1.5))
        if t > 3.0:
            g.vtext(115, 2, "九转丹成"[:int(clamp((t - 3.0) * 3) * 4)])
        self.mx(g, h, t, dan=1.0)
        if t > 1.6:
            g.mx[:5, :] = False
            r = (t - 1.6) * 3
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r % 5) < 0.7 or (abs(xx - 3.5) < 1 and abs(yy - 3.5) < 1):
                        g.mx[yy, xx] = True
            g.mx_level = 1 + int(5 * (1 - span(t, 1.6, 3.0)))
