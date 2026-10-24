"""采日精月华：山巅上一个打坐的人，太阳从左边升起划过天空，光芒一缕缕流进他口中；
日落之后月亮升起、群星闪烁，再采月华。一昼夜为一轮。

依据：上清派“服日月芒”之法（《真诰》、《上清握中诀》等），面日而坐、闭目存想日芒入口，咽之；
夜则对月服月华。内丹家亦以日为离（火）、月为坎（水）。

入场：群山从云海里升起，人坐在峰顶，东边天际泛白，太阳露头。
持续：一轮 10 分钟 = 一昼夜：前半日行（日出→中天→日落，光线流入人口），后半月行（月升→月落，满天星）。
      人身上的光晕随采得的精华慢慢变亮。天亮时“第几日”加一。
中断：一片云飘过来遮住日（月），光线断了，“云遮”。
恢复：云散开，光线重新流下来。
圆满：日月同时出现，相向而行在头顶合成一团光，光团落进人的身子，“日月合璧”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, noise, pulse, rand, span
from ..engine.cn import cn_num
from ..engine.fx import cloud, ring, stars, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register

SAGE = Sprite("""
       #
      ###
     #####
     #.#.#
     #####
      #.#
    #######
   ##.###.##
   #.#####.#
  ##.#####.##
  ###.###.###
 ######.######
###############
 #############
""")
SX, SY = 64, 46          # 人坐的位置（峰顶）
MOUTH = (SX, SY - 10)
HORIZON = 54


def sky_pos(p: float) -> tuple[float, float]:
    """日月在天上的位置：p 0 = 东边地平线，0.5 = 中天，1 = 西边"""
    x = lerp(12, 116, p)
    y = HORIZON - 4 - 39 * math.sin(math.pi * p)
    return x, y


@register
class SunMoon(Ritual):
    id = "r4.sunmoon"
    name = "采日月"
    desc = "山巅打坐，日出东方光芒流入口中，日落月升再采月华，一昼夜一轮"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 零件

    def day(self, e: float) -> tuple[bool, float, float]:
        """→ (白天?, 日/月在天上的进度 0..1, 一轮的进度 0..1)"""
        p = (e % self.CYCLE) / self.CYCLE
        if p < 0.5:
            return True, p * 2, p
        return False, (p - 0.5) * 2, p

    def hills(self, g: Gfx, rise: float = 1.0):
        d = g.d
        dy = (1 - rise) * 30
        back = [(0, 64), (0, 54 + dy), (12, 47 + dy), (24, 53 + dy), (34, 50 + dy), (44, 58 + dy), (84, 58 + dy),
                (96, 49 + dy), (108, 54 + dy), (120, 46 + dy), (128, 50 + dy), (128, 64)]
        d.polygon(back, fill=0)
        g.shade_poly(back, 0.07)
        # 主峰：一块高耸的石峰，峰顶平台坐人；右侧背光（抖动），几道石纹
        main = [(30, 64), (44, 56 + dy), (52, SY + 3 + dy), (56, SY + dy), (72, SY + dy), (76, SY + 3 + dy),
                (86, 55 + dy), (100, 64)]
        d.polygon(main, fill=0, outline=1)
        g.shade_poly([(66, SY + 2 + dy), (72, SY + dy), (76, SY + 3 + dy), (86, 55 + dy), (100, 64), (70, 64)], 0.25,
                     outline=None)
        d.line((56, SY + 4 + dy, 52, 58 + dy), fill=1)
        d.line((60, SY + 6 + dy, 58, 63 + dy), fill=1)
        for i in range(4):  # 云海
            y = 59 + (i % 2) * 3 + dy * 0.3
            x = (i * 37 + 10) % 128
            d.line((x, y, x + 14, y), fill=0)
            d.line((x, y + 1, x + 14, y + 1), fill=1)

    def sage(self, g: Gfx, glow: float, t: float, dy: float = 0.0):
        g.blit(SAGE, SX - SAGE.w // 2, SY - SAGE.h + 1 + dy)
        if glow > 0.05:
            r = 9 + glow * 4 + pulse(t, 3.0) * 1.5
            ring(g, SX, SY - 7 + dy, r + 2, 3 if glow < 0.5 else 2, t * 0.4)

    def sun(self, g: Gfx, x: float, y: float, t: float, r: float = 6):
        g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
        for i in range(8):
            a = i * math.pi / 4 + t * 0.3
            l0, l1 = r + 2, r + 4 + (i % 2) * 2
            g.d.line((x + math.cos(a) * l0, y + math.sin(a) * l0, x + math.cos(a) * l1, y + math.sin(a) * l1), fill=1)

    def moon(self, g: Gfx, x: float, y: float, r: float = 6):
        g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
        g.d.ellipse((x - r + 3, y - r - 2, x + r + 3, y + r - 2), fill=0)

    def beams(self, g: Gfx, x: float, y: float, t: float, amt: float = 1.0, sparse: bool = False):
        """日芒（月华）一缕缕从日月流进口中"""
        if amt <= 0:
            return
        mx_, my_ = MOUTH
        dx, dy = mx_ - x, my_ - y
        L = math.hypot(dx, dy)
        if L < 12:
            return
        ux, uy = dx / L, dy / L
        nx, ny = -uy, ux
        n = 3 if sparse else 5
        for j in range(n):
            off = (j - (n - 1) / 2) * (2.2 if sparse else 1.8)
            for k in range(3):
                s = ((t * (0.35 if sparse else 0.5) + j * 0.23 + k / 3) % 1.0)
                if s > amt:
                    continue
                w = off * (1 - s)  # 越近越收拢
                px = x + ux * (8 + s * (L - 10)) + nx * w
                py = y + uy * (8 + s * (L - 10)) + ny * w
                g.d.line((px, py, px + ux * (2 if sparse else 3), py + uy * (2 if sparse else 3)), fill=1)

    def horizon_glow(self, g: Gfx, k: float, left: bool):
        """日出日落时天边泛光"""
        if k <= 0:
            return
        x0 = 0 if left else 64
        g.shade((x0, HORIZON - 10, x0 + 64, HORIZON - 2), 0.12 * k)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        is_day, s, p = self.day(e)
        n = int(e // self.CYCLE) + 1
        left = "采日精" if is_day else "采月华"
        g.vtext(2, 2, left[:int(round(len(left) * a))])
        r = right if right is not None else f"第{cn_num(n)}日"
        g.vtext(115, 2, r[:int(round(len(r) * a))])

    def mx(self, g: Gfx, e: float, t: float):
        is_day, s, p = self.day(e)
        if is_day:
            g.mx[2:6, 2:6] = True
            g.mx[2, 2] = g.mx[2, 5] = g.mx[5, 2] = g.mx[5, 5] = False
            k = int(t * 2) % 2
            for x, y in (((3, 0), (4, 0), (0, 3), (0, 4), (7, 3), (7, 4), (3, 7), (4, 7)) if k else
                         ((1, 1), (6, 1), (1, 6), (6, 6))):
                g.mx[y, x] = True
        else:
            for y, row in enumerate(("..###...", ".##.....", "##......", "##......", "##......", ".##.....",
                                     "..###...", "........")):
                for x, ch in enumerate(row):
                    g.mx[y, x] = ch == "#"
            for i, (x, y) in enumerate(((6, 1), (5, 4), (7, 6))):
                g.mx[y, x] = blink(t + i * 0.43, 1.3, 0.5)

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, e: float, cover: float = 0.0):
        """画一整帧（不含字）；cover：云遮住日月的程度 0..1"""
        is_day, s, p = self.day(e)
        if not is_day:
            stars(g, t, self.seed, n=26, box=(16, 0, 112, 44))
        edge = 1 - span(min(s, 1 - s), 0.0, 0.12)  # 日出日落
        self.horizon_glow(g, edge if is_day else edge * 0.4, s < 0.5)
        x, y = sky_pos(s)
        if is_day:
            self.sun(g, x, y, t, r=6 + edge * 1.5)
        else:
            self.moon(g, x, y)
        self.hills(g)
        amt = (1 - edge) * (1 - cover)
        self.beams(g, x, y, t, amt, sparse=not is_day)
        glow = 0.3 + 0.7 * p
        self.sage(g, glow * (0.5 + 0.5 * amt), t)
        if cover > 0:  # 云从右边飘来遮住
            cx = lerp(160, x, ease_out(cover))
            cloud(g, cx, y + 1, 44, 22, self.seed + 3, fill=0)
        return is_day, s, p

    def hold(self, g: Gfx, t: float, e: float):
        self.frame(g, t, e)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < 3.0:  # 天亮，新的一日
            typewriter(g, 64, 2, f"第{cn_num(int(e // self.CYCLE) + 1)}日", k, cps=5, align="center")
            if k > 2.4:
                g.fade(1 - span(k, 2.4, 3.0), (40, 0, 90, 14))
        self.texts(g, e)
        self.mx(g, e, t)

    def enter(self, g: Gfx, t: float):
        rise = ease_out(span(t, 0, 1.6))
        self.horizon_glow(g, span(t, 1.4, 3.0), True)
        if t > 2.4:  # 太阳从东边露头
            x, y = sky_pos(0)
            k = ease_out(span(t, 2.4, 4.5))
            self.sun(g, x, lerp(HORIZON + 6, y, k), t, r=7.5)
        self.hills(g, rise)
        if t > 1.4:  # 人现身（一团云散开）
            k = span(t, 1.4, 2.4)
            self.sage(g, 0.3 * span(t, 3.0, 4.5), t)
            if k < 1:
                g.fade(ease_in(k), (SX - 8, SY - 14, SX + 8, SY + 1))
                for j in range(8):
                    a = j / 8 * 2 * math.pi
                    r = 4 + k * 12
                    g.px(SX + math.cos(a) * r, SY - 5 + math.sin(a) * r * 0.6)
        self.texts(g, 0, a=span(t, 3.4, 4.5))
        self.mx(g, 0, t)
        if t < 2.4:
            g.mx[:] = False
            g.mx[7, :] = True
            g.mx[6, 2:6] = t > 1.4

    def interrupt(self, g: Gfx, t: float, e: float):
        self.frame(g, t, e, cover=ease_in_out(span(t, 0, 1.3)))
        self.texts(g, e, right="云遮")
        self.mx(g, e, t)
        k = span(t, 0.6, 1.3)
        for y in range(8):
            for x in range(8):
                if (x + y) % 2 and rand(x * 8 + y, 5) < k:
                    g.mx[y, x] = False

    def resume(self, g: Gfx, t: float, e: float):
        self.frame(g, t, e, cover=1 - ease_in_out(span(t, 0.2, 1.6)))
        self.texts(g, e, right="云遮" if t < 0.5 else None)
        self.mx(g, e, t)

    def complete(self, g: Gfx, t: float, e: float):
        is_day, s, p = self.day(e)
        # 日月同时出现，往中天走，合成一团
        k = ease_in_out(span(t, 0.3, 2.4))
        sun0 = sky_pos(s) if is_day else sky_pos(0.15)
        moon0 = sky_pos(s) if not is_day else sky_pos(0.85)
        top = (SX, 12)
        sx_, sy_ = lerp(sun0[0], top[0] - 3, k), lerp(sun0[1], top[1], k)
        mx_, my_ = lerp(moon0[0], top[0] + 3, k), lerp(moon0[1], top[1], k)
        stars(g, t, self.seed, n=int(26 * span(t, 0, 1.0)), box=(16, 0, 112, 44))
        fall = ease_in(span(t, 2.6, 3.4))
        if t < 2.6:
            self.sun(g, sx_, sy_, t, r=6)
            if not is_day or t > 0.3:
                self.moon(g, mx_, my_)
            if t > 2.2:  # 合璧闪光
                r = 8 + span(t, 2.2, 2.6) * 8
                g.d.ellipse((top[0] - r, top[1] - r, top[0] + r, top[1] + r), fill=1)
        elif t < 3.4:  # 光团落进身子
            y = lerp(top[1], SY - 6, fall)
            r = 8 * (1 - fall) + 2
            g.d.ellipse((SX - r, y - r, SX + r, y + r), fill=1)
            for j in range(10):
                a = j / 10 * 2 * math.pi + t
                g.d.line((SX + math.cos(a) * (r + 2), y + math.sin(a) * (r + 2), SX + math.cos(a) * (r + 6),
                          y + math.sin(a) * (r + 6)), fill=1)
        self.hills(g)
        glow = 1.0 if t > 3.4 else 0.6
        self.sage(g, glow, t)
        if t > 3.4:  # 周身放光
            gl = ease_out(span(t, 3.4, 4.2))
            for j in range(16):
                a = j / 16 * 2 * math.pi + t * 0.3
                r0, r1 = 12, 12 + 14 * gl * (0.6 + 0.4 * math.sin(t * 5 + j))
                g.d.line((SX + math.cos(a) * r0, SY - 6 + math.sin(a) * r0 * 0.8, SX + math.cos(a) * r1,
                          SY - 6 + math.sin(a) * r1 * 0.8), fill=1)
            typewriter(g, 64, 2, "日月合璧", t - 3.6, cps=5, align="center")
        if t < 1.2:
            self.texts(g, e, a=1 - span(t, 0.2, 1.2))
        # 点阵：日、月各在一边，合到中间
        c = int(round(lerp(0, 3, k)))
        g.mx[3:5, c:c + 2] = True
        g.mx[3:5, 6 - c:8 - c] = True
        if t > 2.4:
            r = (t - 2.4) * 4
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - r % 6) < 0.7:
                        g.mx[y, x] = True
        g.mx_level = 6 if 2.3 < t < 2.8 else 1
