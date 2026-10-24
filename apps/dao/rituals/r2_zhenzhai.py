"""镇宅符：一道符贴在宅门正中。月亮从东走到西，夜里不时有小鬼飘来，到门前被符光一照就散了；
一夜过去天亮，第二夜再守。

依据：镇宅符贴于门户、厅堂以镇邪，民间镇宅俗语“姜太公在此，百无禁忌”；
符纸用朱砂黄纸，贴符后“诸邪回避”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, \
    noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import flame, stars, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r2_common import rays

GROUND = 61
DOOR = (52, 38, 76, GROUND)
FU = (60, 40, 68, 55)
FUC = (64, 47)
LANTERN = (88, 33)
GHOST_P = 47.0           # 小鬼出没的周期
RENEW = 5.0

GHOST = [Sprite("""
  .####.
 .#....#.
 #.#..#.#
 #......#
 #..##..#
 #......#
 #......#
 #.#..#.#
 .# .# .#
"""), Sprite("""
  .####.
 .#....#.
 #.#..#.#
 #......#
 #..##..#
 #......#
 #......#
 #.#..#.#
 #. #. #.
""")]


@register
class ZhenZhai(Ritual):
    id = "r2.zhenzhai"
    name = "镇宅符"
    desc = "符贴宅门，月行中天，小鬼夜里飘来，到门前被符光一照就散；一夜一轮，天亮再守一夜"
    T = {"enter": 4.2, "interrupt": 1.5, "resume": 1.6, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.s = self.rng.randrange(1000)

    # ------------------------------------------------------------ 零件

    def house(self, g: Gfx):
        # 屋顶：飞檐
        roof = [(22, 25), (30, 28), (98, 28), (106, 25), (100, 30), (28, 30)]
        g.d.polygon([(36, 17), (92, 17), (100, 28), (28, 28)], fill=0, outline=1)
        for x in range(34, 96, 3):  # 瓦垄
            x2 = 64 + (x - 64) * 1.18
            g.d.line((x, 18, x2, 27), fill=1)
        g.d.polygon(roof, fill=1)
        g.d.line((34, 16, 94, 16), fill=1)                  # 正脊
        g.d.line((34, 15, 94, 15), fill=1)
        for sx in (33, 95):                                  # 鸱吻
            d = 1 if sx > 64 else -1
            g.d.line((sx, 15, sx + d * 2, 11), fill=1)
            g.d.line((sx + d * 2, 11, sx + d * 4, 12), fill=1)
        # 墙、柱
        g.d.rectangle((34, 30, 94, GROUND), fill=0, outline=1)
        g.d.rectangle((36, 30, 38, GROUND), fill=1)
        g.d.rectangle((90, 30, 92, GROUND), fill=1)
        # 窗（棂格）
        for x0 in (41, 79):
            g.d.rectangle((x0, 38, x0 + 8, 48), outline=1)
            g.d.line((x0 + 4, 38, x0 + 4, 48), fill=1)
            g.d.line((x0, 43, x0 + 8, 43), fill=1)
        # 门：双扇、门钉、门环
        x0, y0, x1, y1 = DOOR
        g.d.rectangle((x0 - 2, y0 - 3, x1 + 2, y1), outline=1)
        g.d.rectangle((x0, y0, x1, y1), fill=0, outline=1)
        g.d.line((64, y0, 64, y1), fill=1)
        for yy in range(y0 + 3, y1 - 2, 4):
            for xx in (x0 + 3, x0 + 7, x1 - 7, x1 - 3):
                g.px(xx, yy)
        g.d.ellipse((60, 48, 62, 50), outline=1)
        g.d.ellipse((66, 48, 68, 50), outline=1)
        # 台阶
        g.d.line((44, GROUND, 84, GROUND), fill=1)
        g.d.line((0, 63, 127, 63), fill=1)
        g.d.line((40, 62, 88, 62), fill=1)

    def fu(self, g: Gfx, glow: float = 0.0, y_off: float = 0.0, x_scale: float = 1.0):
        x0, y0, x1, y1 = FU
        cx = (x0 + x1) / 2
        hw = (x1 - x0) / 2 * x_scale
        g.d.rectangle((cx - hw, y0 + y_off, cx + hw, y1 + y_off), fill=0, outline=1)
        if x_scale > 0.6:
            yy = y0 + y_off
            for dx in (-2, 0, 2):
                g.px(cx + dx, yy + 2)
            g.d.line((cx - 2, yy + 4, cx + 2, yy + 4), fill=1)       # 敕令（简笔）
            g.d.line((cx, yy + 4, cx, yy + 8), fill=1)
            g.d.line((cx - 2, yy + 6, cx + 2, yy + 6), fill=1)
            g.d.line([(cx, yy + 9), (cx - 2, yy + 10), (cx + 2, yy + 11), (cx - 1, yy + 12), (cx + 1, yy + 14)],
                     fill=1)
        if glow > 0:
            rays(g, cx, (y0 + y1) / 2 + y_off, 9, 9 + glow * 8, 10, phase=glow * 0.5, sy=1.2)

    def lantern(self, g: Gfx, t: float, lit: float = 1.0):
        x, y = LANTERN
        sw = math.sin(t * 1.3 + self.s) * 1.2
        g.d.line((x, 30, x + sw * 0.3, y - 3), fill=1)
        cx = x + sw
        g.d.ellipse((cx - 4, y - 3, cx + 4, y + 6), fill=0, outline=1)
        g.d.line((cx - 3, y - 3, cx + 3, y - 3), fill=1)
        g.d.line((cx - 3, y + 6, cx + 3, y + 6), fill=1)
        g.d.line((cx, y + 6, cx + sw * 0.5, y + 10), fill=1)
        if lit > 0.1:
            on = noise(t * 4, self.s) > 0.25
            g.d.ellipse((cx - 2, y, cx + 2, y + 3 + on), fill=1)
            if lit > 0.6 and on:  # 灯笼的光晕
                for i in range(6):
                    a = i / 6 * 2 * math.pi + 0.3
                    g.px(cx + math.cos(a) * 8, y + 2 + math.sin(a) * 7)

    def moon(self, g: Gfx, p: float):
        x = lerp(26, 104, p)
        y = 14 - math.sin(math.pi * p) * 8
        g.d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=1)
        g.d.ellipse((x - 1, y - 5, x + 6, y + 3), fill=0)  # 弯月

    def ghost_at(self, u: float):
        """第几只小鬼、它在哪：返回 (x, y, 状态 0飘近 1被照散, k) 或 None"""
        if u < 8:
            return None
        j = int((u - 8) // GHOST_P)
        k = (u - 8) - j * GHOST_P
        dur = 9.0
        if k > dur:
            return None
        left = rand(j, self.s) < 0.5
        y0 = 30 + rand(j + 9, self.s) * 14
        if k < 6.0:  # 飘近
            p = k / 6.0
            x = lerp(-10, 36, ease_in_out(p)) if left else lerp(138, 92, ease_in_out(p))
            y = y0 + math.sin(k * 2.2) * 3
            return x, y, 0, k, left, j
        p = (k - 6.0) / 3.0
        x = 36 if left else 92
        return x - (1 if left else -1) * ease_out(p) * 20, y0 + math.sin(6 * 2.2) * 3, 1, k, left, j

    def draw_ghost(self, g: Gfx, gh, t: float):
        x, y, st, k, left, j = gh
        spr = GHOST[int(t * 4) % 2]
        if not left:
            spr = spr.flip()
        if st == 0:
            g.blit(spr, x - 5, y - 4)
            return
        p = (k - 6.0) / 3.0
        if p < 0.25:  # 被照到：抖
            g.blit(spr, x - 5 + math.sin(k * 60) * 1.5, y - 4)
        else:  # 散成点
            f = (p - 0.25) / 0.75
            for i in range(12):
                a = rand(i, j) * 2 * math.pi
                r = f * (6 + rand(i + 5, j) * 10)
                if rand(i + 20, j) > f * 0.8:
                    g.px(x + math.cos(a) * r, y + math.sin(a) * r * 0.7)

    def fu_glow(self, u: float) -> float:
        gh = self.ghost_at(u)
        if gh and gh[2] == 1:
            p = (gh[3] - 6.0) / 3.0
            return 1 - span(p, 0.2, 1.0)
        return 0.0

    def zap(self, g: Gfx, u: float):
        """符光射向小鬼"""
        gh = self.ghost_at(u)
        if gh and gh[2] == 1:
            p = (gh[3] - 6.0) / 3.0
            if p < 0.35:
                x, y = gh[0], gh[1]
                cx, cy = FUC
                for d in (-2, 0, 2):
                    g.d.line((cx + (x - cx) * 0.25, cy + d * 0.5, x + (2 if x < cx else -2), y + d), fill=1)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        left = "镇宅"
        g.vtext(3, 3, left[:int(round(a * 2))])
        r = right if right is not None else f"第{cn_num(n)}夜"
        g.vtext(114, 4 if len(r) < 4 else 2, r[:int(round(a * len(r)))])

    def mx(self, g: Gfx, u: float, t: float, glow: float = 0.0):
        g.mx[1:7, 3] = g.mx[1:7, 4] = True
        g.mx[1, 2:6] = g.mx[6, 2:6] = True
        g.mx[3, 3] = g.mx[3, 4] = False
        gh = self.ghost_at(u) if u >= 0 else None
        if gh and gh[2] == 0:
            d = int(gh[3] / 6.0 * 3)
            x = d if gh[4] else 7 - d
            if blink(t, 0.4):
                g.mx_set(x, 3 + int(t * 2) % 2)
        if glow > 0.05:
            r = (1 - glow) * 5 + 1
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - r) < 0.6:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(glow * 4)

    def night(self, g: Gfx, t: float, u: float, lit: float = 1.0):
        stars(g, t, self.s, n=16, box=(0, 0, 128, 26), twinkle=0.3)
        self.moon(g, clamp(u / self.CYCLE))
        self.house(g)
        glow = self.fu_glow(u)
        self.fu(g, glow)
        self.lantern(g, t, lit)
        gh = self.ghost_at(u)
        if gh:
            self.draw_ghost(g, gh, t)
            self.zap(g, u)
        return glow

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        stars(g, t, self.s, n=16, box=(0, 0, 128, 26), twinkle=0.3)
        self.moon(g, 0)
        self.house(g)
        lit = ease_out_back(span(t, 0.3, 0.8))
        self.lantern(g, t, lit)
        # 一道符从天上飘下，翻转着，啪地贴在门上
        if t < 2.6:
            p = span(t, 0.6, 2.4)
            y_off = lerp(-60, 0, ease_out_bounce(p)) if p < 1 else 0
            xs = abs(math.cos(p * 5 * math.pi)) if p < 0.75 else 1
            x_drift = math.sin(p * 7) * 10 * (1 - p)
            if t > 0.6:
                g.d.rectangle(FU, fill=0)
                self._fu_shift(g, x_drift, y_off, xs)
        else:
            self.fu(g, ease_out(1 - span(t, 2.6, 3.6)))
            if t < 3.0:  # 四角按实
                for cx, cy in ((FU[0], FU[1]), (FU[2], FU[1]), (FU[0], FU[3]), (FU[2], FU[3])):
                    g.d.rectangle((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
        self.texts(g, 0, a=span(t, 3.0, 4.2))
        self.mx(g, -1, t, glow=1 - span(t, 2.4, 3.6) if t > 2.4 else 0)

    def _fu_shift(self, g: Gfx, dx: float, y_off: float, xs: float):
        x0, y0, x1, y1 = FU
        cx = (x0 + x1) / 2 + dx
        hw = (x1 - x0) / 2 * max(0.15, xs)
        g.d.rectangle((cx - hw, y0 + y_off, cx + hw, y1 + y_off), fill=0, outline=1)
        if xs > 0.6:
            g.d.line((cx, y0 + y_off + 3, cx, y1 + y_off - 3), fill=1)

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, e)
            return
        glow = self.night(g, t, u)
        self.texts(g, e)
        self.mx(g, u, t, glow)

    def _renew(self, g: Gfx, t: float, u: float, e: float):
        """一夜过去：日出、天亮，转眼又入夜"""
        day = math.sin(span(u, 0, RENEW) * math.pi)
        sun_y = lerp(40, 8, day)
        if day > 0.1:
            g.d.ellipse((100 - 6, sun_y - 6, 100 + 6, sun_y + 6), fill=1)
            rays(g, 100, sun_y, 9, 9 + day * 6, 12, phase=u * 0.3)
        if day < 0.6:
            stars(g, t, self.s, n=int(16 * (1 - day / 0.6)), box=(0, 0, 128, 26), twinkle=0.3)
        if u > RENEW * 0.6:
            self.moon(g, 0)
        self.house(g)
        self.fu(g)
        self.lantern(g, t, 1 - day)
        if 1.2 < u < 2.2:  # 鸡鸣
            g.text(40, 4, "鸡鸣", size=8)
        self.texts(g, e - (u if u < RENEW / 2 else 0))
        self.mx(g, -1, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        """吹灭灯笼，宅门静静守着"""
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        lit = 1 - ease_in(span(t, 0.2, 0.8))
        stars(g, t, self.s, n=16, box=(0, 0, 128, 26), twinkle=0.3)
        self.moon(g, clamp(u / self.CYCLE))
        self.house(g)
        self.fu(g)
        self.lantern(g, t, lit)
        gh = self.ghost_at(u)
        if gh and t < 0.8:  # 小鬼趁机溜走
            x, y, st, k, left, j = gh
            gx = x + (-1 if left else 1) * ease_in(span(t, 0, 0.8)) * 40
            self.draw_ghost(g, (gx, y, 0, k, left, j), t)
        self.texts(g, e, right="暂歇")
        self.mx(g, -1, t)

    def resume(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        lit = ease_out_back(span(t, 0.4, 1.0))
        self.night(g, t, u, lit)
        if t < 0.6:  # 符先亮一下
            self.fu(g, 1 - span(t, 0, 0.6))
        self.texts(g, e)
        self.mx(g, u, t, 1 - span(t, 0, 0.6))

    def complete(self, g: Gfx, t: float, e: float):
        """符放大光，天亮，“百无禁忌”"""
        u = e % self.CYCLE
        day = ease_out(span(t, 1.2, 3.0))
        if day < 0.8:
            stars(g, t, self.s, n=int(16 * (1 - day)), box=(0, 0, 128, 26), twinkle=0.3)
        sun_y = lerp(34, 9, day)
        if t > 1.2:
            g.d.ellipse((100 - 6, sun_y - 6, 100 + 6, sun_y + 6), fill=1)
            rays(g, 100, sun_y, 9, 13, 12, phase=t * 0.3)
        self.house(g)
        glow = ease_out(span(t, 0, 0.8))
        self.fu(g, glow * (1 + 0.3 * math.sin(t * 8)))
        for j in range(2):  # 符光一圈圈扩出去
            r = ((t * 26 + j * 22) % 44) + 10
            if t < 3.0:
                for i in range(0, 48, 2):
                    a = i / 48 * 2 * math.pi
                    g.px(FUC[0] + math.cos(a) * r, FUC[1] + math.sin(a) * r * 0.8)
        self.lantern(g, t, 1 - day)
        gh = self.ghost_at(u)
        if gh and t < 1.2:
            x, y, st, k, left, j = gh
            self.draw_ghost(g, (x, y, 1, 6.0 + 3 * span(t, 0, 1.2), left, j), t)
        if t > 0.15 and t < 0.3:
            g.invert((50, 36, 79, 60))
        if t > 2.2:
            g.d.rectangle((18, 1, 74, 14), fill=0)
            typewriter(g, 46, 1, "百无禁忌", t - 2.2, cps=4, align="center")
        g.vtext(3, 3, "镇宅")
        g.vtext(114, 4, "天亮" if t > 2.0 else f"第{cn_num(int(e // self.CYCLE) + 1)}夜")
        self.mx(g, -1, t, glow=1 - span(t, 0.2, 2.0))
        if t > 2.2:
            g.mx_level = 2
