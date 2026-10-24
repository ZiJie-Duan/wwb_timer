"""化符入水：手拈一道符在碗上方燃烧，符灰一片片落进清水，碗里泛起涟漪；一道烧尽，剑指在水面画符，再续一道。

依据：符水之法——符烧成灰和水吞服；水咒“北方壬癸水……百病消除”；
治鲠符等以剑指（中指、食指）“在碗中水面写符”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import flame, ring, smoke_wisp, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r2_common import JIANZHI, arm, glyph, rays

JIANZHI_D = JIANZHI.flipv()

BX, BY = 64, 46          # 碗口中心
FX0, FX1 = 58, 70        # 符纸左右
FTOP, FBOT, FEND = 11, 38, 16  # 符纸上沿、新符下沿、烧到最后剩的下沿
CANDLE = (100, 40)       # 烛芯
LEAD = 6.0               # 每轮开头：点符
END = 560.0              # 烧完的时刻（轮内）
RENEW = 6.5

PINCH = Sprite("""
   .####.
  .#....#.
  #..##..#
  #.#..#.#
  .#....#.
   #.##.#
   #.##.#
    #..#
""")


def _water_y(x: float) -> float:
    return BY


@register
class FuShui(Ritual):
    id = "r2.fushui"
    name = "化符入水"
    desc = "手拈黄符在烛上点着，悬在清水碗上慢慢烧尽，符灰落水泛起涟漪；一道烧完以剑指在水面画符，再化一道"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 2.2, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.s = self.rng.randrange(1000)

    # ------------------------------------------------------------ 零件

    def bowl(self, g: Gfx, glow: float = 0.0):
        g.d.chord((36, 30, 92, 62), 0, 180, fill=0, outline=1)
        g.d.rectangle((55, 59, 73, 62), fill=0, outline=1)
        g.d.chord((36, 30, 92, 62), 0, 180, outline=1)
        g.d.ellipse((36, 42, 92, 50), fill=0, outline=1)
        g.d.ellipse((40, 43, 88, 49), outline=1)
        for i in range(9):  # 碗身一圈点纹
            a = math.pi * (0.15 + 0.7 * i / 8)
            g.px(BX + math.cos(a) * 24, 47 + math.sin(a) * 11)
        if glow > 0:
            rays(g, BX, BY, 30, 30 + glow * 10, 14, phase=glow, sy=0.5)

    def ripples(self, g: Gfx, drops):
        """drops: [(age 秒, x)]：水面涟漪（压扁的椭圆）"""
        for age, x in drops:
            if 0 <= age < 2.2:
                r = 2 + age * 10
                if r > 22:
                    continue
                ry = r * 0.22
                d = 1 if age < 0.6 else 2
                n = max(8, int(r * 4))
                for i in range(0, n, d):
                    a = i / n * 2 * math.pi
                    px, py = x + math.cos(a) * r, BY + math.sin(a) * ry
                    if (px - BX) ** 2 / 23 ** 2 + (py - BY) ** 2 / 2.8 ** 2 < 1:
                        g.px(px, py)

    def ash_floating(self, g: Gfx, p: float, t: float):
        """水面漂着的符灰：越烧越多"""
        n = int(p * 18)
        for i in range(n):
            a = rand(i, self.s) * 2 * math.pi + t * 0.05 * (1 if i % 2 else -1)
            r = 0.2 + 0.8 * rand(i + 40, self.s)
            g.px(BX + math.cos(a) * r * 20, BY + math.sin(a) * r * 2.4)

    def candle(self, g: Gfx, t: float, lit: float = 1.0):
        x, y = CANDLE
        g.d.rectangle((x - 4, y + 2, x + 4, 62), outline=1, fill=0)
        g.d.line((x - 6, 62, x + 6, 62), fill=1)
        g.d.line((x + 2, y + 3, x + 2, y + 7), fill=1)
        g.d.line((x, y + 2, x, y), fill=1)
        if lit > 0.05:
            flame(g, x, y, 5 * lit, 10 * lit, t, self.s + 1)

    def fu(self, g: Gfx, x: float, top: float, bot: float, burning: bool, t: float, full: float = FBOT):
        """一道符：上沿 top，下沿（烧到的地方）bot；字随符纸位置固定，下半烧掉的部分不画"""
        w = FX1 - FX0
        if bot <= top + 1:
            return
        g.d.rectangle((x, top, x + w, bot), fill=0, outline=1)
        # 符文（坐标相对上沿）：三勾、敕、螺旋
        for j, cx in enumerate((x + 3, x + 6, x + 9)):
            g.d.line([(cx, top + 2), (cx + 1, top + 3), (cx, top + 5)], fill=1)
        if top + 7 < bot:
            spr = glyph("敕")
            g.blit(spr, x + 1, top + 7)  # 先画整字，再把烧掉的部分抹掉
        sp = []
        for i in range(20):
            k = i / 19
            a = k * 4 * math.pi
            sp.append((x + w / 2 + math.cos(a) * 3.5 * (1 - k * 0.8), top + 22 + math.sin(a) * 3.2 * (1 - k * 0.8)))
        g.d.line(sp, fill=1)
        if bot + 1 < top + 27:
            g.d.rectangle((x - 1, bot + 1, x + w + 1, top + 27), fill=0)  # 抹掉已烧掉的
        if burning:
            # 焦边：锯齿 + 一条暗带
            for xx in range(int(x), int(x + w) + 1):
                jag = noise(xx * 0.7 + t * 2, self.s) * 3
                g.d.line((xx, bot - jag, xx, bot), fill=1 if (xx + int(t * 8)) % 3 else 0)
            for i in range(3):  # 火苗沿着焦边
                fx = x + 2 + i * (w - 4) / 2
                flame(g, fx, bot + 2, 5, 7 + 3 * noise(t * 3 + i, self.s), t + i * 0.3, self.s + i)
        else:
            g.d.line((x, bot, x + w, bot), fill=1)

    def hand(self, g: Gfx, x: float, top: float):
        """拈符的手：两指捏住符的上沿，袖子往右上出画"""
        hx, hy = x + 3, top - 6
        arm(g, hx + 7, hy + 2, -0.45, 70, 4, 14)
        g.blit(PINCH, hx, hy)

    def burn_y(self, u: float) -> float:
        p = clamp((u - LEAD) / (END - LEAD))
        return lerp(FBOT, FEND, p)

    def drops(self, u: float):
        """按 e 定时的落灰：(年龄, x)"""
        out = []
        if u < LEAD:
            return out
        period = 9.0
        j = int((u - LEAD) // period)
        for jj in (j - 1, j):
            if jj < 0:
                continue
            t0 = LEAD + jj * period + rand(jj, self.s) * 4
            age = u - t0
            x = FX0 + 2 + rand(jj + 99, self.s) * (FX1 - FX0 - 4)
            out.append((age, x))
        return out

    def falling_ash(self, g: Gfx, u: float, bot: float):
        """一片符灰从焦边飘落：落到水面时（age=0）起涟漪"""
        rip = []
        for age, x in self.drops(u):
            fall = 1.6
            if -fall < age < 0:
                k = 1 + age / fall
                yy = lerp(bot + 2, BY, ease_in(k))
                xx = x + math.sin(k * 6 + x) * 2
                g.d.rectangle((xx, yy, xx + 1, yy), fill=1)
            elif age >= 0:
                rip.append((age, x))
        self.ripples(g, rip)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        left = "北方壬癸水"
        g.vtext(2, 2, left[:int(round(a * len(left)))])
        r = right if right is not None else f"第{cn_num(n)}道"
        g.vtext(115, 2, r[:int(round(a * len(r)))])

    def mx(self, g: Gfx, u: float, t: float, p: float):
        g.mx_rows([0, 0, 0, 0, 0b11111111, 0b01000010, 0b00111100, 0b00011000])
        # 符在上方（越烧越短）
        h = int(round((1 - p) * 3)) + 1
        for y in range(0, h):
            g.mx[y, 3] = g.mx[y, 4] = True
        if blink(t, 0.25):
            g.mx_set(3 + int(t * 4) % 2, h)
        for age, x in self.drops(u):  # 落灰：涟漪向两边散开
            if 0 <= age < 0.9:
                d = int(age * 4)
                g.mx[4, max(0, 3 - d)] = False
                g.mx[4, min(7, 4 + d)] = False

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, u: float, e: float, burning: bool = True, fx: float = FX0, ftop: float = FTOP):
        p = clamp((u - LEAD) / (END - LEAD))
        bot = self.burn_y(u)
        self.texts(g, e)
        self.candle(g, t)
        self.bowl(g)
        self.ash_floating(g, p, t)
        self.fu(g, fx, ftop, bot, burning, t)
        self.falling_ash(g, u, bot)
        self.hand(g, fx, ftop)
        if burning:
            smoke_wisp(g, fx + 6, ftop - 2, 10, t, self.s, sway=3, drift=-8)
        return p

    def light_sequence(self, g: Gfx, t: float, k: float, e: float):
        """新符入场、在烛上点着、移回碗上方（k 0..LEAD）"""
        self.texts(g, e)
        self.candle(g, t)
        self.bowl(g)
        cx, cy = CANDLE
        if k < 1.6:  # 从右上方来到烛火上方
            p = ease_out(span(k, 0, 1.6))
            x, top = lerp(110, cx - 6, p), lerp(-40, cy - 31, p)
        elif k < 3.2:  # 点着，烧起来
            x, top = cx - 6, cy - 31
        else:  # 回到碗上方
            p = ease_in_out(span(k, 3.2, 4.8))
            x, top = lerp(cx - 6, FX0, p), lerp(cy - 31, FTOP, p) - math.sin(p * math.pi) * 4
        lit = k > 2.2
        bot = top + (FBOT - FTOP)
        self.fu(g, x, top, bot, lit, t)
        self.hand(g, x, top)
        if 1.6 < k < 2.4:  # 符角凑近烛火
            g.px(x + 6, bot + 1)
        p_mx = 0
        g.mx_rows([0, 0, 0, 0, 0b11111111, 0b01000010, 0b00111100, 0b00011000])
        for y in range(4):
            g.mx[y, 3] = g.mx[y, 4] = True
        if lit:
            g.mx_set(3 + int(t * 4) % 2, 4 if blink(t, 0.25) else 3)
        g.mx_level = 4 if 2.2 < k < 2.5 else 1

    def enter(self, g: Gfx, t: float):
        if t < 1.2:  # 碗与烛先出现
            self.bowl(g)
            p = ease_out_back(span(t, 0, 1.0))
            g.d.rectangle((CANDLE[0] - 4, 62 - p * 20, CANDLE[0] + 4, 62), outline=1)
            ring(g, BX, BY, span(t, 0.3, 1.2) * 20, 2)
            g.mx_rows([0, 0, 0, 0, 0b11111111, 0b01000010, 0b00111100, 0b00011000])
            return
        k = (t - 1.2) / (self.T["enter"] - 1.2) * LEAD
        self.light_sequence(g, t, k, 0.0)
        g.d.rectangle((0, 0, 15, 63), fill=0)
        self.texts(g, 0, a=span(t, 2.5, 4.5))

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, e)
            return
        if e >= self.CYCLE:
            uu = u
        else:
            uu = u
        if uu < LEAD and e < self.CYCLE:
            self.light_sequence(g, t, LEAD, e)
            return
        if u >= END:  # 烧尽：只剩手指捏着的一角，余烟
            self.texts(g, e)
            self.candle(g, t)
            self.bowl(g)
            self.ash_floating(g, 1.0, t)
            self.hand(g, FX0, FTOP)
            g.d.rectangle((FX0, FTOP, FX1, FTOP + 4), fill=0, outline=1)
            smoke_wisp(g, FX0 + 6, FTOP + 6, 12 * (1 - span(u, END, END + 20)), t, self.s, sway=3)
            self.ripples(g, [((u - END) % 6, BX - 6 + rand(int((u - END) // 6), 3) * 12)])
            self.mx(g, u, t, 1.0)
            return
        p = self.frame(g, t, u, e)
        self.mx(g, u, t, p)

    def _renew(self, g: Gfx, t: float, u: float, e: float):
        """一道烧尽：手松开，残角落水；剑指在水面画符；再点一道"""
        if u < 3.0:
            self.texts(g, e)
            self.candle(g, t)
            self.bowl(g, glow=span(u, 2.2, 3.0) * (1 - span(u, 2.6, 3.0)))
            self.ash_floating(g, 1.0, t)
            if u < 0.8:  # 残角飘落
                yy = lerp(FTOP, BY - 2, ease_in(u / 0.8))
                g.d.rectangle((FX0 + 3, yy, FX1 - 3, yy + 2), fill=1)
                self.hand(g, FX0 + u * 40, FTOP - u * 30)
            else:
                self.ripples(g, [(u - 0.8, BX)])
            if 0.9 < u < 2.8:  # 剑指在水面上画一道螺旋
                k = span(u, 0.9, 2.6)
                pts = []
                for i in range(int(k * 30) + 1):
                    a = i / 30 * 3 * math.pi
                    pts.append((BX + math.cos(a) * (18 - i * 0.5), BY + math.sin(a) * (2.5 - i * 0.06)))
                if len(pts) > 1:
                    g.d.line(pts, fill=1)
                fx, fy = pts[-1]
                hy = fy - 16 - 2 * (1 - span(u, 0.9, 1.2)) * 10
                arm(g, fx + 2, hy + 3, -1.0, 60, 4, 14)
                g.blit(JIANZHI_D, fx - 1, hy)
            self.mx(g, -1, t, 1.0)
            g.mx_level = 3 if 2.2 < u < 2.8 else 1
            return
        self.light_sequence(g, t, (u - 3.0) / (RENEW - 3.0) * LEAD, e)

    def interrupt(self, g: Gfx, t: float, e: float):
        """甩灭：手把符提起抖两下，火灭成烟"""
        u = max(e % self.CYCLE, LEAD + 0.01)
        if e >= self.CYCLE:
            u = max(u, RENEW)
        lift = ease_out(span(t, 0, 0.5)) * 6
        shake = math.sin(t * 30) * 3 * (1 - span(t, 0.2, 1.0)) if t < 1.0 else 0
        p = clamp((u - LEAD) / (END - LEAD))
        bot = self.burn_y(u) - lift
        self.texts(g, e, right="暂歇")
        self.candle(g, t)
        self.bowl(g)
        self.ash_floating(g, p, t)
        self.fu(g, FX0 + shake, FTOP - lift, bot, t < 0.6, t)
        self.hand(g, FX0 + shake, FTOP - lift)
        if t > 0.5:
            smoke_wisp(g, FX0 + 6, bot - 1, 18 * (1 - span(t, 0.8, 1.6) * 0.7), t, self.s, sway=4)
        g.mx_rows([0, 0, 0, 0, 0b11111111, 0b01000010, 0b00111100, 0b00011000])
        g.mx[0:2, 3:5] = True

    def resume(self, g: Gfx, t: float, e: float):
        """移到烛火上重新点着，再回到碗上方"""
        u = max(e % self.CYCLE, LEAD + 0.01)
        if e >= self.CYCLE:
            u = max(u, RENEW)
        p = clamp((u - LEAD) / (END - LEAD))
        bot0 = self.burn_y(u)
        cx, cy = CANDLE
        h = bot0 - FTOP
        if t < 0.8:
            k = ease_in_out(span(t, 0, 0.8))
            x, top = lerp(FX0, cx - 6, k), lerp(FTOP - 6, cy - h - 2, k)
        elif t < 1.3:
            x, top = cx - 6, cy - h - 2
        else:
            k = ease_in_out(span(t, 1.3, 2.2))
            x, top = lerp(cx - 6, FX0, k), lerp(cy - h - 2, FTOP, k)
        lit = t > 1.0
        self.texts(g, e)
        self.candle(g, t)
        self.bowl(g)
        self.ash_floating(g, p, t)
        self.fu(g, x, top, top + h, lit, t)
        self.hand(g, x, top)
        self.mx(g, u, t, p)
        g.mx_level = 4 if 1.0 < t < 1.2 else 1

    def complete(self, g: Gfx, t: float, e: float):
        u = max(e % self.CYCLE, LEAD)
        p0 = clamp((u - LEAD) / (END - LEAD))
        p = lerp(p0, 1, ease_in(span(t, 0, 1.4)))
        bot = lerp(FBOT, FEND, p)
        self.candle(g, t)
        glow = span(t, 2.0, 2.6)
        self.bowl(g, glow=0)
        self.ash_floating(g, max(p, 0.5), t)
        if t < 1.4:
            self.texts(g, e)
            self.fu(g, FX0, FTOP, bot, True, t)
            self.hand(g, FX0, FTOP)
            for i in range(3):  # 大块的灰一齐落
                k = ((t * 1.5 + i * 0.33) % 1)
                g.d.rectangle((FX0 + 2 + i * 4, lerp(bot, BY, ease_in(k)), FX0 + 3 + i * 4, lerp(bot, BY, ease_in(k))),
                              fill=1)
        elif t < 2.0:  # 最后一角落水
            k = span(t, 1.4, 2.0)
            yy = lerp(FTOP, BY - 2, ease_in(k))
            g.d.rectangle((FX0 + 3, yy, FX1 - 3, yy + 2), fill=1)
            self.hand(g, FX0 + k * 50, FTOP - k * 40)
            self.texts(g, e)
        if t >= 2.0:  # 一碗符水放光
            k = t - 2.0
            g.d.ellipse((41, 44, 87, 48), fill=0)
            for j in range(3):
                r = ((k * 12 + j * 7) % 21) + 1
                n = 24
                for i in range(n):
                    a = i / n * 2 * math.pi
                    g.px(BX + math.cos(a) * r, BY + math.sin(a) * r * 0.12)
            rays(g, BX, BY - 4, 32, 36 + 6 * math.sin(k * 5), 14, phase=k * 0.2, sy=0.55)
            for i in range(3):  # 水气升起
                smoke_wisp(g, BX - 10 + i * 10, BY - 4, 14 + 6 * span(t, 2.0, 3.0), t, self.s + i, sway=2.5)
            if k < 0.15:
                g.invert((36, 40, 93, 63))
            typewriter(g, BX, 4, "百病消除", t - 2.6, cps=5, align="center")
        g.mx_rows([0, 0, 0, 0, 0b11111111, 0b01000010, 0b00111100, 0b00011000])
        if t >= 2.0:
            r = (t - 2.0) * 4
            for y in range(5):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, (y - 4) * 1.4) - r) < 0.7:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(5 * (1 - span(t, 2.0, 3.5)))
        else:
            h = int(round((1 - p) * 3)) + 1 if t < 1.4 else 0
            for y in range(h):
                g.mx[y, 3] = g.mx[y, 4] = True
