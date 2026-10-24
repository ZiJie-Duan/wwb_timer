"""掌心雷：小道士托掌引雷，推掌发雷，击散邪祟。

依据：雷法（五雷法、五雷正法、掌心雷）为宋代以来神霄、清微等派的法术，道士以掌心雷驱邪；震卦为雷（☳）。

画面：乌云压顶的山岗。左边小道士，右边一团飘忽的邪祟（黑气团，白描边，怒目、尾巴摇摆）。
入场：乌云从天上压下来，闷雷在云里闪；小道士抬手托掌，一道小雷落进掌心；地上冒出一团黑气，邪祟现形。
持续：一轮五雷，每 2 分钟一雷：小道士托掌过头 → 一道雷劈进掌心（闪白、震屏、火星）→ 收掌蓄力 → 推掌，
      一道横雷从掌心打出，邪祟被劈散成烟团（再闪、再震）；右下角五个震卦依次点亮。
      两雷之间：云里闷闪、远处落雷、掌心噼啪跳电；50 秒后邪祟又从黑气里冒出来，往前凑时小道士剑指一点把它逼退。
      续（一轮最后 6 秒）：五雷齐发，五道雷一齐落地，连闪两下，“轰”，云散又聚，五卦归零。
中断：小道士收掌拱手，乌云退回天上，电光熄灭，“暂收”。
恢复：托掌引雷，云又压下来，一道小雷落进掌心。
圆满：一道粗雷劈进掌心，推掌发出巨雷，冲击波一圈圈扩散，云开见月，“急急如律令”。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r5_util import GRASS, Clock, bolt, cached, cloud_sprite, dao, label, pop_box, ring, rock, sky, sparkle

FLOOR = 58
DX = 28                     # 小道士
GX, GY = 98, 34             # 邪祟中心
SEG = 120.0
ST = [6.0 + i * SEG for i in range(5)]    # 一轮里五雷的时刻
RENEW_AT = 594.0
CLOUDS = [(-8, -3, 44, 16, 11), (30, -5, 60, 20, 12), (84, -3, 52, 17, 13)]


def _ghost(frame: int) -> Sprite:
    """邪祟 18×20：圆头、飘摇的尾巴、两只小爪；内部 25% 网点，白描边；怒目、锯齿嘴"""
    from PIL import Image, ImageDraw
    w, h = 18, 20
    m = Image.new("1", (w, h))
    d = ImageDraw.Draw(m)
    d.ellipse((3, 0, 14, 11), fill=1)
    sway = (-1, 0, 1, 0)[frame % 4]
    d.polygon([(3, 6), (14, 6), (13 + sway, 12), (10 + sway, 16), (12 + sway * 2, 19), (7 + sway, 15),
               (5, 11)], fill=1)
    arm = (0, 1, 0, -1)[frame % 4]
    d.polygon([(4, 8), (0, 10 + arm), (1, 11 + arm), (5, 10)], fill=1)       # 爪
    d.polygon([(13, 8), (17, 9 - arm), (17, 10 - arm), (13, 10)], fill=1)
    M = np.array(m, bool)
    P = np.pad(M, 1)
    er = P[1:-1, 1:-1] & P[:-2, 1:-1] & P[2:, 1:-1] & P[1:-1, :-2] & P[1:-1, 2:]
    ys, xs = np.mgrid[0:h, 0:w]
    on = (M & ~er) | (er & (xs % 2 == 0) & (ys % 2 == 0) & (ys > 7))
    for ex in (6, 10):                         # 眼：白眼、黑瞳、怒眉
        on[4:6, ex:ex + 2] = True
        on[5, ex + (1 if ex == 6 else 0)] = False
    on[3, 5] = on[3, 12] = True
    on[2, 4] = on[2, 13] = True
    for i, x in enumerate(range(6, 12)):       # 锯齿嘴
        on[8 + (i % 2), x] = True
    return Sprite(on=on, mask=M)


def ghost_frames():
    return cached(("r5leifa", "ghost"), lambda: [_ghost(i) for i in range(4)])


ZHEN = pix.frames("""
##.##
.....
##.##
.....
#####
""")


def clouds(g: Gfx, t: float, drop: float, flick: bool = False):
    """乌云：drop 往下压的像素数；flick 云里闷闪（云底网点反白）"""
    for i, (x, y, w, h, seed) in enumerate(CLOUDS):
        dx = math.sin(t * 0.3 + i * 2.1) * 2
        pix.blit(g, cloud_sprite(w, h, seed, dark=True), x + dx, y + drop + i % 2)
    if flick:
        g.invert((0, 0, 128, int(10 + drop)))


HILLS = [(0, 50), (10, 46), (22, 49), (34, 44), (50, 48), (62, 45), (78, 49), (92, 43), (106, 47), (118, 45),
         (128, 49)]


def ground(g: Gfx, t: float):
    """远山（一道描边山脊，下半网点）、地面、草、石"""
    g.d.line(HILLS, fill=1)
    pts = HILLS + [(128, FLOOR), (0, FLOOR)]
    from PIL import Image, ImageDraw
    m = Image.new("1", (128, 64))
    ImageDraw.Draw(m).polygon(pts, fill=1)
    mk = np.array(m, bool)
    mk[:, :] &= np.arange(64)[:, None] > 51
    pix.checker_mask(g, mk, 0.125)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.25)
    g.d.line((0, FLOOR + 3, 127, FLOOR + 3), fill=0)
    for i, x in enumerate((6, 48, 70, 118)):
        pix.blit(g, pix.anim(GRASS, t * 0.8 + i * 0.4, 2), x, FLOOR - 4)
    pix.blit(g, rock(), 56, FLOOR - 5)
    pix.blit(g, rock(), 110, FLOOR - 5, flip=True)


@register
class LeiFa(Clock, Ritual):
    id = "r5.leifa"
    name = "掌心雷"
    desc = "乌云压顶，小道士托掌引雷入掌心，推掌发出横雷劈散邪祟；一轮五雷，第五雷后五雷齐发"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)
        self.puffs = pix.Puffs(self.seed + 2)
        self.sk = self.rng.randrange(1000)

    # ------------------------------------------------------------ 时间线

    def last_strike(self, e: float):
        """→ (轮内秒数 k, 第几雷 i（-1 = 本轮还没打）, 距该雷的秒数)"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        i = -1
        for j, s in enumerate(ST):
            if k >= s:
                i = j
        return k, i, (k - ST[i]) if i >= 0 else None

    def ghost_alpha(self, e: float) -> float:
        """邪祟在不在：被劈后 50 秒从黑气里升起；续之后到下一轮开头也不在"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        k_, i, since = self.last_strike(e)
        if k >= RENEW_AT - 10:
            return 0.0
        if i < 0:
            return 1.0 if c == 0 else span(k, 0.0, 3.0)
        if since < 3.0:
            return 1.0 if since < 2.45 else 0.0
        if i == 4:
            return 0.0
        return span(since, 50.0, 53.0)

    def charge(self, e: float) -> float:
        """两雷之间云越压越低（0..1）"""
        k, i, since = self.last_strike(e)
        if since is None:
            return span(k, 0, ST[0])
        return span(since, 4, SEG)

    # ------------------------------------------------------------ 画

    def ghost(self, g: Gfx, t: float, a: float, x: float = GX, y: float = GY, shake: float = 0.0):
        if a <= 0:
            return
        fr = pix.anim(ghost_frames(), t, 5)
        if a < 1:  # 从地上的黑气里升起：由扁到圆
            s = pix.stretch(fr, 1.0 + (1 - a) * 0.6, max(0.1, ease_out_back(a)))
            gy = FLOOR - 1 - s.h
            pix.blit(g, s, x - s.w / 2, lerp(gy, y - fr.h / 2, a))
            pix.checker(g, (x - 10, FLOOR - 2, x + 10, FLOOR), 0.5)
            return
        bob = math.sin(t * 2.2) * 2
        jx = (rand(int(t * 20), 5) - 0.5) * 2 * shake
        pix.blit(g, fr, x - fr.w / 2 + jx, y - fr.h / 2 + bob)

    def crackle(self, g: Gfx, hx: float, hy: float, t: float, n: int = 2):
        """掌心噼啪：几道短小的折线电花"""
        for j in range(n):
            if rand(int(t * 15) * 3 + j, self.seed) < 0.6:
                a = rand(int(t * 15) * 5 + j, self.seed + 1) * math.pi * 2
                x0, y0 = hx + math.cos(a) * 2, hy + math.sin(a) * 2
                x1, y1 = hx + math.cos(a) * 6, hy + math.sin(a) * 6
                mx, my = (x0 + x1) / 2 + math.sin(a) * 2, (y0 + y1) / 2 - math.cos(a) * 2
                g.d.line((x0, y0, mx, my, x1, y1), fill=1)

    def indicators(self, g: Gfx, n: int, t: float, blink_last: bool = False):
        """右下角五个震卦（已发的雷亮，未发的只剩暗框）"""
        x0 = 87
        g.k.rectangle((x0 - 3, FLOOR - 1, 127, 63), fill=1)
        g.d.rectangle((x0 - 3, FLOOR - 1, 128, 64), outline=1)
        for i in range(5):
            x = x0 + i * 8
            if i < n and not (blink_last and i == n - 1 and (t * 6) % 1 < 0.5):
                pix.blit(g, ZHEN[0], x, FLOOR + 1, outline=False)
            else:
                g.px(x + 2, FLOOR + 3)

    def strike(self, g: Gfx, tau: float, t: float, dt: float, big: bool = False):
        """一次掌心雷（tau 从 0 起）。返回是否画过小道士"""
        if tau < 1.0:                              # 托掌引雷
            h = dao(g, DX, FLOOR, "palm", t, face="normal")
            hx, hy = h["hand"]
            if tau > 0.4:
                self.crackle(g, hx, hy, t, 2)
            return h
        if tau < 2.0:
            h = dao(g, DX, FLOOR, "palm", t, face="wow")
            hx, hy = h["hand"]
            if tau < 1.25:
                bolt(g, hx + 6, 8, hx, hy - 1, int(t * 10) + self.seed, thick=True, jag=4)
            if 1.0 <= tau < 1.0 + dt:
                self.sparks.burst(hx, hy, 18, 40, up=10, life=0.6, gravity=60)
            if 1.0 <= tau < 1.07:
                pix.flash(g)
            if tau < 1.3:
                pix.shake(g, t, 1.5)
            self.crackle(g, hx, hy, t, 4)
            ring(g, hx, hy, (tau - 1.0) * 14 % 7 + 1)
            return h
        if tau < 2.4:                              # 收掌蓄力
            h = daoshi(g, DX - 1, FLOOR, "gongshou", t, face="normal")
            self.crackle(g, h["hand"][0], h["hand"][1], t, 3)
            return h
        h = dao(g, DX + 1, FLOOR, "push", t, face="wow" if tau < 3.2 else "normal")
        hx, hy = h["hand"]
        if tau < 2.7:                              # 横雷
            bolt(g, hx + 1, hy, GX - 4, GY, int(t * 12) + self.seed * 7, thick=True, jag=3)
            bolt(g, hx + 1, hy + 1, GX - 4, GY + 1, int(t * 12) + self.seed * 7, thick=True, jag=3, branch=False)
            if tau < 2.47:
                pix.flash(g)
            pix.shake(g, t, 2.0)
        if 2.4 <= tau < 2.4 + dt:
            self.sparks.burst(GX, GY, 26, 46, up=8, life=0.8, gravity=40)
            for j in range(6):
                self.puffs.emit(GX + (j - 2.5) * 3, GY + (j % 3) * 3 - 3, vx=(j - 2.5) * 5, vy=-6, life=1.4,
                                rmax=3.0, spread=2)
        if 2.4 < tau < 3.0:
            ring(g, GX, GY, (tau - 2.4) * 40)
        return h

    def ambient(self, g: Gfx, e: float, t: float, drop: float):
        """云里闷闪、远处落雷"""
        e = e + 4.5
        i = int(e // 9)
        if (e % 9) < 0.18 and rand(i, self.seed) < 0.7:
            x = 20 + rand(i, self.seed + 3) * 80
            bolt(g, x, 6 + drop, x + 18, 9 + drop, i, thick=False, jag=2, branch=False)
        j = int((e + 7) // 23)
        if ((e + 7) % 23) < 0.25:
            x = 112 + rand(j, self.seed + 9) * 12
            bolt(g, x, 12 + drop, x - 4, FLOOR - 1, j * 7, thick=False, jag=3, branch=True)

    def scene(self, g: Gfx, t: float, e: float, dt: float):
        k, i, since = self.last_strike(e)
        drop = 4 * self.charge(e)
        ground(g, t)
        clouds(g, t, drop)
        self.ambient(g, e, t, drop)
        ga = self.ghost_alpha(e)
        drawn = False
        if since is not None and since < 4.0:
            self.ghost(g, t, ga)
            self.strike(g, since, t, dt)
            drawn = True
        elif k >= RENEW_AT:
            self.renew(g, k - RENEW_AT, t, dt)
            drawn = True
        else:
            # 邪祟往前凑 → 剑指逼退（每 30 秒一次，邪祟在场时）
            q = (e % 30) / 30
            push = 0.0
            if ga >= 1 and 0.55 < q < 0.75:
                push = math.sin(span(q, 0.55, 0.75) * math.pi)
            gx = GX - push * 16 * (1 if q < 0.68 else span(0.75 - q, 0, 0.07))
            self.ghost(g, t, ga, gx, shake=1.0 if 0.66 < q < 0.72 else 0.0)
            if ga >= 1 and 0.64 < q < 0.72:
                h = daoshi(g, DX, FLOOR, "point", t, face="normal")
                pix.dotted(g, h["hand"][0] + 2, h["hand"][1], gx - 9, GY, 2, int(t * 20))
            else:
                ph = e % 16
                pose = "gongshou" if 9 < ph < 12 else "idle"
                h = daoshi(g, DX, FLOOR, pose, t)
                if pose == "gongshou" and rand(int(t * 4), self.seed) < 0.5:
                    self.crackle(g, h["hand"][0], h["hand"][1], t, 1)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        n = 5 if k >= RENEW_AT else i + 1
        self.indicators(g, n, t, blink_last=since is not None and since < 3)
        self.mx(g, t, since is not None and 1.0 <= since < 1.2 or since is not None and 2.4 <= since < 2.6)
        if k >= RENEW_AT and 1.0 < k - RENEW_AT < 4.0:
            kk = k - RENEW_AT
            pop = ease_out_back(span(kk, 1.0, 1.3))
            g.text(64, 14 + (1 - pop) * 8, "轰", align="center", scale=2)

    def renew(self, g: Gfx, kk: float, t: float, dt: float):
        """五雷齐发：五道雷一齐落地，闪两下，云散又聚"""
        h = dao(g, DX, FLOOR, "palm", t, face="wow" if kk < 3 else "happy")
        hx, hy = h["hand"]
        self.crackle(g, hx, hy, t, 3)
        if 1.0 <= kk < 1.5:
            for j in range(5):
                x = 46 + j * 18
                bolt(g, x + 4, 6, x, FLOOR - 1, j * 13 + int(kk * 8), thick=True, jag=4)
            pix.shake(g, t, 2.5)
        for ft in (1.0, 1.3):
            if ft <= kk < ft + 0.07:
                pix.flash(g)
        if 1.0 <= kk < 1.0 + dt:
            for j in range(5):
                self.sparks.burst(46 + j * 18, FLOOR - 1, 8, 30, up=20, life=0.6, gravity=80)
                self.puffs.emit(46 + j * 18, FLOOR - 3, vy=-4, life=1.2, rmax=3.0)

    def mx(self, g: Gfx, t: float, hit: bool):
        if hit:
            g.mx[:] = True
            g.mx_level = 8
            return
        for r, bits in enumerate(((1, 1, 0, 0, 0, 0, 1, 1), (1, 1, 0, 0, 0, 0, 1, 1), (1, 1, 1, 1, 1, 1, 1, 1))):
            for x in range(8):
                g.mx[2 + r * 2, x] = bool(bits[x])
        for x in range(8):  # 顶行：云中蓄电
            g.mx[0, x] = rand(int(t * 8) * 8 + x, self.seed) < 0.3

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        ground(g, t)
        drop = lerp(-22, 0, ease_out(span(t, 0, 1.6)))
        tt = t - self.T["enter"]          # 与持续阶段 t=0 对上相位（云漂、鬼影起伏）
        clouds(g, tt, drop, flick=1.8 < t < 1.9)
        ga = span(t, 3.4, 5.4)
        self.ghost(g, tt, ga)
        if t < 2.2 or t > 5.0:
            h = daoshi(g, DX, FLOOR, "gongshou" if 1.4 < t < 2.2 else "idle", t)
        else:
            h = dao(g, DX, FLOOR, "palm", t, face="wow" if 2.9 < t < 3.6 else "normal")
            hx, hy = h["hand"]
            if 2.9 <= t < 3.1:
                bolt(g, hx + 5, 8, hx, hy - 1, 77, thick=False, jag=3)
            if 2.9 <= t < 2.9 + dt:
                self.sparks.burst(hx, hy, 12, 30, up=8, life=0.5)
            if t > 2.9:
                self.crackle(g, hx, hy, t, 2)
        if 2.9 <= t < 3.2:
            pix.shake(g, t, 1)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.indicators(g, 0, t)
        self.mx(g, t, 2.9 <= t < 3.1)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        self.scene(g, t, e, dt)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k, i, since = self.last_strike(e)
        ground(g, t)
        up = ease_in(span(t, 0.2, 1.4))
        clouds(g, t, 4 * self.charge(e) - up * 24)
        ga = self.ghost_alpha(e) * (1 - span(t, 0.2, 1.0))
        if ga > 0:
            self.ghost(g, t, 1.0, GX, GY + up * 6)
            g.fade(1 - span(t, 0.2, 1.0), (GX - 12, 0, GX + 12, FLOOR))
        daoshi(g, DX, FLOOR, "gongshou", t)
        self.indicators(g, i + 1, t)
        if t > 0.3:
            label(g, 64, 20, "暂收", align="center")
        self.mx(g, t, False)
        g.mx[0, :] = False

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k, i, since = self.last_strike(e)
        ground(g, t)
        drop = lerp(-24, 4 * self.charge(e), ease_out_back(span(t, 0, 1.0)))
        clouds(g, t, drop)
        self.ghost(g, t, self.ghost_alpha(e) * span(t, 0.8, 1.8))
        if t < 1.5:
            h = dao(g, DX, FLOOR, "palm", t, face="wow" if 0.9 < t < 1.3 else "normal")
            hx, hy = h["hand"]
            if 0.9 <= t < 1.1:
                bolt(g, hx + 5, 8 + drop, hx, hy - 1, 91, thick=False, jag=3)
                pix.shake(g, t, 1)
            if 0.9 <= t < 0.9 + dt:
                self.sparks.burst(hx, hy, 14, 30, up=8, life=0.5)
                pix.flash(g)
            if t > 0.9:
                self.crackle(g, hx, hy, t, 3)
        else:
            daoshi(g, DX, FLOOR, "idle", t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.indicators(g, i + 1, t)
        self.mx(g, t, 0.9 <= t < 1.1)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        part = ease_in_out(span(t, 2.6, 4.0))
        if part > 0:
            sky(g, self.sk, t, (0, 0, 128, 40), 30, part)
            mx_, my_ = 104, 10                         # 月
            g.d.ellipse((mx_ - 5, my_ - 5, mx_ + 5, my_ + 5), fill=1)
            g.d.ellipse((mx_ - 3, my_ - 6, mx_ + 6, my_ + 3), fill=0)
        ground(g, t)
        for i, (x, y, w, h, seed) in enumerate(CLOUDS):   # 云向两边散开
            dx = (-1 if x + w / 2 < 64 else 1) * part * 110
            pix.blit(g, cloud_sprite(w, h, seed, dark=True), x + dx, y + 2 - part * 6)
        ga = self.ghost_alpha(e)
        if t < 1.6:
            self.ghost(g, t, max(ga, 1.0), shake=1.0 if t > 0.8 else 0.0)
        if t < 1.0:
            h = dao(g, DX, FLOOR, "palm", t)
            self.crackle(g, h["hand"][0], h["hand"][1], t, 3)
        elif t < 1.4:
            h = dao(g, DX, FLOOR, "palm", t, face="wow")
            hx, hy = h["hand"]
            bolt(g, hx + 8, 0, hx, hy - 1, int(t * 15), thick=True, jag=5)
            bolt(g, hx - 6, 0, hx, hy - 1, int(t * 15) + 3, thick=False, jag=4)
            pix.shake(g, t, 2)
            if 1.0 <= t < 1.07:
                pix.flash(g)
            self.crackle(g, hx, hy, t, 5)
        elif t < 3.0:
            h = dao(g, DX + 1, FLOOR, "push", t, face="wow")
            hx, hy = h["hand"]
            if t < 2.0:
                bolt(g, hx + 1, hy - 1, 127, GY - 2, int(t * 15) * 3, thick=True, jag=4)
                bolt(g, hx + 1, hy + 1, 127, GY + 6, int(t * 15) * 5, thick=False, jag=5)
                pix.shake(g, t, 2.5)
            if 1.6 <= t < 1.67:
                pix.flash(g)
            if 1.6 <= t < 1.6 + dt:
                self.sparks.burst(GX, GY, 40, 60, up=10, life=1.0, gravity=30)
                for j in range(8):
                    self.puffs.emit(GX + (j - 4) * 3, GY, vx=(j - 4) * 6, vy=-8, life=1.6, rmax=3.5)
            for j in range(3):  # 冲击波
                r = (t - 1.6 - j * 0.2) * 70
                if 0 < r < 120:
                    ring(g, hx, hy, r, r * 0.6)
        else:
            daoshi(g, DX, FLOOR, "gongshou" if t < 4.5 else "idle", t, face="happy")
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.indicators(g, 5, t, blink_last=False)
        if t > 3.4:
            y = pop_box(g, 64, 6, "急急如律令", t, 3.4)
            g.text(64, y, "急急如律令", align="center")
        hit = 1.0 <= t < 1.2 or 1.6 <= t < 1.8
        self.mx(g, t, hit)
        if t > 1.8:
            g.mx[:] = False
            from .r5_util import mx_ring
            mx_ring(g, (t - 1.8) * 4 % 6)
            g.mx_level = 1 + int(5 * (1 - span(t, 1.8, 3.5)))
