"""挥拂尘：静室里，小道士执拂尘一下下挥扫，一阵风把满屋浮尘卷出窗外；月洞窗里的太极随之由暗转明。

拂尘（麈尾、云帚）是道士随身法器，取“拂去尘埃、清净自守”之意。文字取《太上老君说常清静经》
“人能常清静，天地悉皆归”。

入场：一阵风把尘埃从左边吹进来，蒙住月洞窗里的太极；小道士执拂尘走进来，拂尘尾一甩一甩。
持续：每 6 秒挥一下：举起（尾巴垂在后面）→ 横扫（尾巴滞后、甩开，扫出一道弧）→ 回落（尾巴往前一甩）→ 搭回臂上。
      每一扫荡出一阵风，被轮到的浮尘飞出画外，地上扬起一小团灰。一轮 600 秒，46 粒浮尘逐渐拂净，
      太极由暗（网点）转明、缓缓转动。窗角一张蛛网到半轮时被扫掉。左上写“常清静”。
      续：一阵风从左边刮来，浮尘重新飞进屋，太极复暗。
中断：拂尘搭回臂上，写“暂歇”。  恢复：抬手一抖，尾巴甩开。
圆满：连扫两下，余尘一扫而光，太极全亮、快转、放光，题“天地悉皆归”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import daoshi
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import mx_taiji, taiji
from .r3_kit import (FLOOR, Clock, banner, banner_text, crossed, floor, hand_at, label, mx_ring, pose_arm, rays,
                     round_of, smear)

DX = 30
CYCLE = 600.0
SWEEP = 6.0
NDUST = 46
WIN = (96, 24, 17)          # 月洞窗：圆心 x, y, 半径
RENEW = 5.0

# 一挥的关键帧：(时刻, 手臂, 柄的角度)
KEYS = [(0.0, "low", -70), (0.35, "up30", -95), (0.55, "up30", -100), (0.62, "fwd", -10), (0.7, "low", 40),
        (0.85, "dn", 70), (1.4, "dn", 60), (1.8, "low", -70)]


def handle_angle(u: float) -> tuple[str, float]:
    for (t0, a0, h0), (t1, a1, h1) in zip(KEYS, KEYS[1:]):
        if t0 <= u < t1:
            q = (u - t0) / (t1 - t0)
            q = ease_in(q) if t1 - t0 < 0.1 else ease_in_out(q)
            return (a0 if q < 0.5 else a1), lerp(h0, h1, q)
    return KEYS[-1][1], KEYS[-1][2]


def tail_angle(u: float) -> float:
    """马尾：慢的时候被重力拉向下（90°）；挥得快时拖在柄转动方向的后面（柄角 - 90°，带滞后），
    挥完余势未消还会往前一甩，再慢慢垂下"""
    def h(x):
        return handle_angle(max(x, 0))[1]
    speed = max(abs(h(u - d) - h(u - d - 0.04)) / 0.04 for d in (0.0, 0.08, 0.16, 0.24))
    w = min(1.0, speed / 500)
    trail = h(u - 0.08) - 90
    d = ((trail - 90 + 180) % 360) - 180
    return 90 + d * w


def fuchen(g: Gfx, hand, ang: float, tang: float, t: float, fling: float = 0.0):
    """拂尘：柄（两像素粗、顶端圆钮、扎口一圈）+ 五缕马尾（往下垂、末端散开）"""
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    hx, hy = hand
    tip = (hx + c * 9, hy + s * 9)
    end = (hx - c * 3, hy - s * 3)
    g.d.line((end, tip), fill=1, width=2)
    g.d.rectangle((end[0] - 1, end[1] - 1, end[0] + 1, end[1] + 1), fill=1)
    # 扎口
    g.d.rectangle((tip[0] - 1.5, tip[1] - 1.5, tip[0] + 1.5, tip[1] + 1.5), fill=1)
    g.px(tip[0], tip[1], 0)
    strands = []
    for j, sp in enumerate((-12, -6, 0, 6, 12)):
        L = 15 + (j % 2) * 2 + fling * 3
        a = math.radians(tang + sp * (1 + fling * 0.6))
        pts = [tip]
        for k in range(1, 4):   # 三节，越往后越往下坠
            seg = L / 3
            aa = a + math.radians(12 * k * (1 if math.cos(a) > 0 else -1)) * (1 - fling)
            x, y = pts[-1]
            pts.append((x + math.cos(aa) * seg, y + math.sin(aa) * seg + k * 0.6 * (1 - fling)))
        strands.append((pts, a))
    for pts, a in strands:   # 先描一圈黑边，马尾和身体分得开
        g.d.line(pts, fill=0, width=3)
    for pts, a in strands:
        g.d.line(pts, fill=1)
        ex, ey = pts[-1]
        g.px(ex + math.cos(a) * 1.5, ey + math.sin(a) * 1.5 + 1)
    g.d.rectangle((tip[0] - 1.5, tip[1] - 1.5, tip[0] + 1.5, tip[1] + 1.5), fill=1)
    g.px(tip[0], tip[1], 0)
    return tip


def dust_pos(i: int, seed: int):
    x = 46 + rand(i, seed) * 78
    y = 4 + rand(i, seed + 1) * 48
    return x, y


def clear_time(i: int, seed: int) -> float:
    """第 i 粒尘在本轮第几秒被扫走（落在某一扫的扫出时刻）"""
    n = int(CYCLE / SWEEP) - 2
    order = sorted(range(NDUST), key=lambda j: rand(j, seed + 5))
    rank = order.index(i)
    sweep = 1 + int(rank * n / NDUST)
    return sweep * SWEEP + 0.62


@register
class FuchenRitual(Ritual):
    id = "r3.fuchen"
    name = "挥拂尘"
    desc = "小道士执拂尘一下下挥扫，一阵阵风把满屋浮尘卷出画外；月洞窗里的太极随计时由暗转明"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 1.6, "complete": 5.5}
    CYCLE = CYCLE

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()
        self.ds = self.rng.randrange(1000)
        self.ct = [clear_time(i, self.ds) for i in range(NDUST)]

    # ------------------------------------------------------------ 背景

    def room(self, g: Gfx, t: float, clean: float, spin: float = 0.0, web: bool = True):
        """静室：地面、踢脚线、月洞窗（窗棂 + 太极；蒙尘时只留网点）、窗下一张矮几"""
        floor(g)
        g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
        cx, cy, r = WIN
        g.d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), outline=1)
        g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
        taiji(g, cx, cy, 11, spin)
        level = 0.3 + 0.7 * clean
        if level < 1:
            g.fade(level, (cx - 12, cy - 12, cx + 13, cy + 13))
        for a in range(0, 360, 30):   # 窗沿一圈小窗棂
            c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
            g.d.line((cx + c * (r - 2), cy + s * (r - 2), cx + c * r, cy + s * r), fill=1)
        if web:   # 窗角蛛网
            x0, y0 = cx + 6, cy - r + 3
            for k in range(3):
                g.d.line((x0, y0, x0 + 7 - k * 3, y0 + k * 3 + 1), fill=1)
            g.d.arc((x0 - 4, y0 - 4, x0 + 4, y0 + 4), 0, 90, fill=1)
        # 矮几 + 香炉
        g.d.rectangle((84, FLOOR - 12, 110, FLOOR - 11), fill=1)
        g.d.line((86, FLOOR - 10, 86, FLOOR - 4), fill=1)
        g.d.line((108, FLOOR - 10, 108, FLOOR - 4), fill=1)
        g.d.rectangle((93, FLOOR - 16, 100, FLOOR - 13), fill=1)
        g.d.line((94, FLOOR - 15, 99, FLOOR - 15), fill=0)
        g.px(96, FLOOR - 18 - (int(t * 3) % 3)), g.px(97, FLOOR - 21 - (int(t * 3 + 1) % 3))

    def dust(self, g: Gfx, k: float, t: float, back: float = 1.0):
        """浮尘：未扫的轻轻飘；刚扫的被风卷出画外（按 k 算，断线重连也接得上）。back < 1：被风吹回来的过程"""
        left = 0
        for i in range(NDUST):
            x, y = dust_pos(i, self.ds)
            ct = self.ct[i]
            if back < 1:
                q = span(back, rand(i, 9) * 0.5, rand(i, 9) * 0.5 + 0.5)
                if q <= 0:
                    continue
                x = lerp(-6, x, ease_out(q))
                y = y + math.sin(q * 6 + i) * 3 * (1 - q)
            elif k >= ct:
                f = k - ct
                if f > 1.6:
                    continue
                x += f * f * 70 + f * 20
                y -= f * 18 * (0.5 + rand(i, 3))
                if x > 130:
                    continue
            else:
                left += 1
                x += math.sin(t * 0.7 + i) * 1.5
                y += math.sin(t * 0.5 + i * 1.7) * 1.2
            big = rand(i, 4) > 0.75
            if big:
                g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=0)
                g.px(x, y), g.px(x + 1, y), g.px(x, y + 1)
            else:
                g.px(x, y)
        return left

    def wind(self, g: Gfx, f: float, y0: float = 30):
        """一阵风：三道虚线弧往右卷"""
        if 0 <= f < 1:
            for j in range(3):
                x = 40 + f * 90 + j * 6
                yy = y0 + (j - 1) * 9
                pix.dotted(g, x, yy, x + 14, yy - 2, 2, phase=j)
                g.d.arc((x + 10, yy - 6, x + 18, yy + 2), 270, 90, fill=1)

    def mx(self, g: Gfx, k: float, sweep: float = -1):
        for i in range(NDUST):
            if k < self.ct[i]:
                x, y = dust_pos(i, self.ds)
                g.mx_set(int((x - 46) / 78 * 8), int((y - 4) / 48 * 8))
        if 0 <= sweep < 1:
            col = int(sweep * 8)
            g.mx[:, min(col, 7)] = True
        else:
            g.mx[5:8, 0] = True
            g.mx[4, 0] = g.mx[7, 1] = True

    # ------------------------------------------------------------ 小道士

    def actor(self, g: Gfx, t: float, u: float | None, face="normal", t_for_fig=None):
        """u = 本挥已过秒数；None = 搭在臂上静持"""
        if u is None:
            arm, ang = "low", -70
            tang = 95 + math.sin(t * 1.3) * 4
        else:
            arm, ang = handle_angle(u)
            tang = tail_angle(u)
        fling = 1.0 if u is not None and 0.6 <= u < 0.95 else 0.0
        tip = [None]

        def prop(g2, h):
            tip[0] = fuchen(g2, h, ang, tang, t, fling)
        behind = u is not None and arm == "up30"
        pose_arm(g, DX, arm, t if t_for_fig is None else t_for_fig, "fist", face=face, prop=prop,
                 prop_behind=behind)
        return tip[0]

    def swing(self, g: Gfx, u: float, t: float, dt: float, k: float, power: float = 1.0):
        """一挥的特效：扫过的残影、风、地上扬灰"""
        if 0.55 <= u < 0.78:
            h = hand_at(DX, FLOOR, "fwd", t)
            smear(g, h[0] - 4, h[1] - 6, 24, 3, -110, 20 + (u - 0.55) * 100, solid=0.3)
        if crossed(u, dt, 0.62):
            self.puffs.emit(DX + 18, FLOOR - 1, vx=26, vy=-6, life=0.9, rmax=2)
            self.puffs.emit(DX + 10, FLOOR - 1, vx=16, vy=-3, life=0.7, rmax=1.5)
        self.wind(g, (u - 0.6) / 1.2, 26)

    # ------------------------------------------------------------ 阶段

    def clean_of(self, k: float) -> float:
        return sum(1 for c in self.ct if k >= c + 0.6) / NDUST

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        back = span(t, 0.0, 2.6)
        self.room(g, t, 1 - back * 0.999)
        self.dust(g, 0, t, back if back < 1 else 1.0)
        self.wind(g, span(t, 0.0, 1.6) * 1.0 if t < 1.6 else -1, 30)
        if t < 2.8:
            x = lerp(-14, DX, ease_out(span(t, 0.8, 2.8)))
            h = daoshi(g, x, FLOOR, "walk", t)["hand"]
            fuchen(g, (h[0], h[1] - 2), -70, 95 + math.sin(t * 6) * 15, t)
        else:
            u = (t - 3.4) if t > 3.4 else None
            self.actor(g, t, u)
            if u is not None:
                self.swing(g, u, t, dt, 0)
        self.puffs.step(dt)
        self.puffs.draw(g)
        label(g, 3, 3, "常清静")
        self.mx(g, 0, (t - 4.0) / 0.4 if 4.0 < t < 4.4 else -1)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, p = round_of(e, CYCLE)
        if e >= CYCLE and k < RENEW:
            self.renew(g, k, t, e, dt)
            return
        clean = self.clean_of(k)
        spin = e * 0.15 * clean
        self.room(g, t, clean, spin, web=k < CYCLE / 2)
        if CYCLE / 2 <= k < CYCLE / 2 + 2:   # 蛛网被风卷走
            cx, cy, r = WIN
            f = k - CYCLE / 2
            g.d.line((cx + 6 + f * 30, cy - r + 3 - f * 8, cx + 12 + f * 34, cy - r + 6 - f * 10), fill=1)
        self.dust(g, k, t)
        u = e % SWEEP
        uu = u if u < 2.0 else None
        self.actor(g, e, uu, face="wow" if uu is not None and 0.6 < uu < 0.9 else "normal")
        if uu is not None:
            self.swing(g, uu, e, dt, k)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        label(g, 3, 3, "常清静")
        self.mx(g, k, (u - 0.55) / 0.4 if 0.55 < u < 0.95 else -1)

    def renew(self, g: Gfx, k: float, t: float, e: float, dt: float):
        """k ∈ [0, RENEW)：一阵风从左边刮来，浮尘重新飞进屋，太极复暗"""
        back = span(k, 0.4, 3.6)
        self.room(g, t, 1 - ease_in_out(back), e * 0.15)
        self.dust(g, 0, t, back if back < 1 else 1.0)
        for j in range(3):   # 大风
            f = span(k, 0.2 + j * 0.3, 2.0 + j * 0.3)
            if 0 < f < 1:
                x = -20 + f * 160
                y = 12 + j * 14
                pix.dotted(g, x, y, x + 22, y, 2, phase=j)
                pix.dotted(g, x + 6, y + 3, x + 18, y + 3, 3)
        self.actor(g, e, None, face="wow" if k < 3.0 else "normal")
        self.puffs.step(dt)
        self.puffs.draw(g)
        label(g, 3, 3, "风又起" if k < 3.6 else "常清静")
        self.mx(g, 0)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % CYCLE
        clean = self.clean_of(k)
        self.room(g, t, clean, e * 0.15 * clean, web=k < CYCLE / 2)
        self.dust(g, k, t)
        self.actor(g, t, None, face="normal")
        self.puffs.step(dt)
        self.puffs.draw(g)
        label(g, 3, 3, "暂歇" if t > 0.4 else "常清静")
        self.mx(g, k)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % CYCLE
        clean = self.clean_of(k)
        self.room(g, t, clean, e * 0.15 * clean, web=k < CYCLE / 2)
        self.dust(g, k, t)
        u = t * 1.1 if t < 1.6 else None
        self.actor(g, t, u, face="happy" if t > 1.0 else "normal")
        if u is not None:
            self.swing(g, u, t, dt, k)
        self.puffs.step(dt)
        self.puffs.draw(g)
        label(g, 3, 3, "常清静")
        self.mx(g, k, (u - 0.55) / 0.4 if u is not None and 0.55 < u < 0.95 else -1)

    def complete(self, g: Gfx, t: float, e: float):
        """连扫两下 → 余尘一扫而光 → 太极全亮快转放光 → 天地悉皆归"""
        dt = self.clock(t)
        k = e % CYCLE
        # 余下的尘：在两扫里全部扫走
        kk = k if t < 0.6 else (CYCLE if t > 1.6 else k)
        clean = self.clean_of(kk) if t < 1.6 else 1.0
        spin = e * 0.15 + (t ** 2) * 1.2
        bright = t > 1.8
        self.room(g, t, clean if t < 1.6 else min(1.0, 0.6 + span(t, 1.6, 2.2)), spin, web=False)
        if bright:
            rays(g, WIN[0], WIN[1], 12, 15, 12, rot=-t, dash=0)
        if t < 1.6:
            for i in range(NDUST):   # 剩下的尘全被卷走
                if k < self.ct[i]:
                    x, y = dust_pos(i, self.ds)
                    f = max(0.0, t - 0.6 - rand(i, 6) * 0.3)
                    x += f * f * 120 + f * 40
                    y -= f * 20 * rand(i, 3)
                    if x < 130:
                        g.px(x, y)
        u = (t * 1.6) % 1.8 if t < 2.2 else None
        self.actor(g, t, u, face="wow" if t < 2.2 else "happy")
        if u is not None:
            self.swing(g, u, t, dt, k, 1.5)
        if crossed(t, dt, 1.9):
            self.sparks.burst(WIN[0], WIN[1], 24, 40, life=1.0, gravity=20)
        if 1.9 <= t < 1.98:
            pix.flash(g)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 2.4:
            banner(g, 40, 4, "天地悉皆归", span(t, 2.4, 2.8))
            banner_text(g, 40, 4, "天地悉皆归", span(t, 2.4, 2.8))
        else:
            label(g, 3, 3, "常清静")
        if t < 1.8:
            self.mx(g, kk if t < 0.6 else CYCLE, ((t * 1.6) % 1.8 - 0.55) / 0.4)
        elif t < 3.0:
            mx_ring(g, (t - 1.8) * 4)
            g.mx_level = 6
        else:
            mx_taiji(g, t * 2)
