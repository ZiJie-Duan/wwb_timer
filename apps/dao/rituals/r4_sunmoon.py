"""采日月：小道士盘坐在云海上的孤峰顶，白天面日服日芒，夜里对月服月华。

依据：上清派“服日月芒”（《真诰》《上清握中诀》一类：面日存想日芒入口咽之，夜对月服月华）；内丹以日为离、月为坎。
入场：云海里一座孤峰升起，峰顶一团云散开，现出打坐的小道士；天边一亮，太阳从右边露头。
持续：一轮 10 分钟 = 一昼夜：前 5 分钟太阳从右边升起、划过天顶、在左边落下（日出日落时地平线泛光），
      日芒一缕缕沿点线流进口中；小道士随日转身；后 5 分钟月亮升起、群星闪烁，月华稀疏地流下。
      身上的光晕随一轮的进度越来越大；白天不时飞过一行雁，夜里偶尔一颗流星。续：天亮，左上“第几日”加一。
中断：一大片云从右边飘来遮住日（月），光线断，“云遮”。  恢复：云散开，光线重新流下来。
圆满：日月同时出现，相向而行在头顶合成一团强光，闪白，光团落进身体，周身放光，“日月合璧”。
点阵：白天是闪芒的太阳，夜里是月牙加三颗闪烁的星；圆满时日月从两边合到中间。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, span
from ..engine.chars import Part
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import P, Clock, cached, cloud_sea, counter, dao, label, mount, mx_art, mx_ring, pop_title, ring, star

PEAK_TOP = 48            # 峰顶（小道士坐的地方）
DX = 44
SIT = P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"), face="sleep")
SIT_UP = P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"))
HALF = 300.0


def _peak():
    """孤峰 56×18：峰顶平台、岩缝、阴面网点、崖边一棵小松"""
    p = Part(56, 18)
    p.shape("polygon", [(0, 17), (8, 9), (14, 5), (20, 2), (36, 2), (42, 5), (48, 11), (55, 17)], fill=1)
    p.d.line((20, 2, 36, 2), fill=1)
    p.d.line((21, 3, 35, 3), fill=0)
    for a, b in (((12, 8), (16, 12)), ((24, 6), (26, 10)), ((32, 8), (30, 13)), ((8, 13), (11, 16)), ((40, 9), (44, 14))):
        p.d.line(a + b, fill=0)
    p.dither([(36, 3), (42, 5), (48, 11), (55, 17), (36, 17), (33, 9)], 0.5, 0)
    # 崖边小松
    p.shape("line", (40, 3, 44, 0), fill=1)
    return p.sprite()


def _side_peak(w, h, n):
    p = Part(w, h)
    p.shape("polygon", [(0, h - 1), (w // 3, 2), (w // 2, 0), (w * 2 // 3, 3), (w - 1, h - 1)], fill=1)
    p.dither([(w // 2, 0), (w * 2 // 3, 3), (w - 1, h - 1), (w // 2 + 1, h - 1)], 0.5, 0)
    p.d.line((w // 3 + 1, 4, w // 3 + 3, 8), fill=0)
    return p.sprite()


SUN = pix.frames("""
  .###.
 #######
.#######.
#########
#########
#########
.#######.
 #######
  .###.
""")

MOON = pix.frames("""
  ####
 ##.###
####.###
########
#.######
###.####
 ######
  ####
""")

CLOUD_BIG = pix.frames("""
         ######
     ###########   ####
   ####################
 ########################
###########################
#.#.#.#.#.#.#.#.#.#.#.#.##
""")

CLOUDLET = pix.frames("""
  ###
#######
#.#.#.#
""")

GEESE = pix.frames("""
#.#
 #
---
 #
#.#
""")


def sky_pos(theta: float):
    """天上的弧：theta 0 = 右边地平线，pi = 左边地平线"""
    return 64 + 56 * math.cos(theta), 44 - 38 * math.sin(theta)


def landscape(g: Gfx, t: float, off: int = 0):
    """云海与群峰（孤峰最后画，压在云海上）"""
    pix.blit(g, mount(2), 94, 36 + off)
    pix.blit(g, mount(3), 2, 40 + off)
    cloud_sea(g, t, 50, speed=1.5)
    pix.blit(g, cached(("sm", "peak"), _peak), DX - 28, PEAK_TOP - 2 + off)


def stars(g: Gfx, t: float, k: float, seed: int = 3):
    """群星（k = 夜色浓度 0–1）"""
    import random
    r = random.Random(seed)
    for i in range(22):
        x, y = r.randrange(2, 126), r.randrange(2, 40)
        if r.random() < k:
            on = (t * (0.5 + r.random()) + r.random()) % 1 < 0.8
            g.px(x, y, 1 if on else 0)
            if i % 7 == 0 and on:
                g.px(x - 1, y), g.px(x + 1, y)


@register
class SunMoon(Ritual):
    id = "r4.sunmoon"
    name = "采日月"
    desc = "小道士盘坐云海孤峰顶，白天面日服日芒、夜里对月服月华，日月东升西落，一轮一昼夜"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()

    def state(self, k: float):
        """一轮第 k 秒：('sun'|'moon', theta)"""
        if k < HALF:
            return "sun", lerp(0.08, math.pi - 0.08, k / HALF)
        return "moon", lerp(0.08, math.pi - 0.08, (k - HALF) / HALF)

    def body(self, g: Gfx, t: float, x_target: float, eyes_open=False):
        flip = x_target < DX
        return dao(g, DX, PEAK_TOP, SIT_UP if eyes_open else SIT, t, flip=flip)

    def streams(self, g: Gfx, t: float, src, h: dict, kind: str, cut: float = 1.0):
        """日芒 / 月华：沿点线流进口中；cut < 1 时只画靠近源头的一段"""
        mx_, my = h["mouth"]
        sx, sy = src
        n = 3 if kind == "sun" else 2
        for j in range(n):
            off = (j - (n - 1) / 2) * 3
            x0, y0 = sx + off, sy + 4
            L = math.hypot(mx_ - x0, my - y0)
            steps = int(L / 3)
            ph = t * (6 if kind == "sun" else 3) + j
            for i in range(steps):
                q = i / max(steps, 1)
                if q > cut:
                    break
                if (i + int(ph)) % (2 if kind == "sun" else 3) == 0:
                    g.px(lerp(x0, mx_, q), lerp(y0, my, q))

    def halo(self, g: Gfx, t: float, prog: float):
        """身上的光晕：一轮里越来越大"""
        r = 14 + prog * 8
        cx, cy = DX, PEAK_TOP - 17
        n = int(10 + prog * 26)
        for i in range(n):
            a = i / n * 2 * math.pi + t * 0.3
            g.px(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.95)

    def orb(self, g: Gfx, kind: str, x: float, y: float, t: float):
        if kind == "sun":
            for j in range(8):  # 日芒（转动的光芒）
                a = j * math.pi / 4 + t * 0.6
                r0, r1 = 7, 9 + (j % 2) * 2
                pix.dotted(g, x + math.cos(a) * r0, y + math.sin(a) * r0, x + math.cos(a) * r1, y + math.sin(a) * r1, 1)
            pix.blit(g, SUN[0], x - 4, y - 4)
        else:
            pix.blit(g, MOON[0], x - 4, y - 4)
            g.d.ellipse((x - 1, y - 6, x + 6, y + 3), fill=0)   # 月牙（盈亏）

    def horizon(self, g: Gfx, kind: str, theta: float, t: float):
        """日出 / 日落：地平线泛光（网点带）"""
        if kind == "sun" and (theta < 0.35 or theta > math.pi - 0.35):
            side = 1 if theta < 0.35 else -1
            k = 1 - (min(theta, math.pi - theta) / 0.35)
            sx, sy = sky_pos(theta)
            for j, w in enumerate((30, 20, 12)):  # 霞光：几道横纹
                ww = w * (0.4 + 0.6 * k)
                pix.dotted(g, sx - ww, 47 - j * 3, sx + ww, 47 - j * 3, 2 if j else 1, j)

    def mx(self, g: Gfx, t: float, kind: str):
        if kind == "sun":
            mx_art(g, """
..####..
.######.
########
########
########
########
.######.
..####..
""" if (t * 2) % 1 < 0.5 else """
#..##..#
.######.
.######.
########
########
.######.
.######.
#..##..#
""")
        else:
            mx_art(g, """
..###...
.##.....
##......
##......
##......
.##.....
..###...
........
""")
            for x, y, ph in ((6, 1, 0.0), (5, 5, 0.33), (7, 6, 0.66)):
                g.mx[y, x] = (t * 1.3 + ph) % 1 < 0.6

    def labels(self, g: Gfx, e: float, kind: str, extra: str | None = None):
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}日" if n < 100 else f"{n}日")
        counter(g, extra or ("服日芒" if kind == "sun" else "服月华"), right=True)

    def scene(self, g: Gfx, t: float, e: float, dt: float, cloud: float = 0.0, flow: float = 1.0):
        """cloud：遮日的大云盖住的程度（0–1）；flow：光线流到哪"""
        k = e % self.CYCLE
        kind, th = self.state(k)
        night = 0.0
        if kind == "moon":
            night = min(1.0, (k - HALF) / 8.0)
        elif k > HALF - 8:
            night = 0.0
        stars(g, t, night * (1.0 - cloud * 0.5))
        sx, sy = sky_pos(th)
        self.horizon(g, kind, th, t)
        self.orb(g, kind, sx, sy, t)
        # 小事件：白天一行雁 / 夜里流星（按 e）
        ph = (e % 41) / 5.0
        if ph < 1:
            if kind == "sun":
                for j in range(4):
                    pix.blit(g, pix.anim(GEESE, t + j * 0.2, 4), lerp(-10, 140, ph) - j * 6, 12 + j * 2 + (j % 2), outline=False)
            else:
                x, y = lerp(110, 50, ph), lerp(4, 24, ph)
                g.d.line((x, y, x + 6, y - 2), fill=1)
                g.px(x - 1, y + 1)
        if cloud > 0:  # 大云遮住
            cx = lerp(150, sx - 14, ease_out(cloud))
            pix.blit(g, CLOUD_BIG[0], cx, sy - 4)
        landscape(g, t)
        self.halo(g, t, k / self.CYCLE)
        h = self.body(g, t, sx)
        if flow > 0 and cloud < 0.6:
            self.streams(g, t, (sx, sy), h, kind, flow)
        self.mx(g, t, kind)
        return kind, (sx, sy), h

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        rise = ease_out(span(t, 0.0, 2.0))
        off = int((1 - rise) * 30)
        landscape(g, t, off)
        if t > 2.0:
            self.body(g, t, 120, eyes_open=t < 3.6)
        if 1.8 < t < 3.2:  # 峰顶的云散开
            k = span(t, 1.8, 3.2)
            for s in (-1, 1):
                x = DX + s * k * 30
                pix.blit(g, CLOUD_BIG[0] if k < 0.5 else CLOUDLET[0], x - 13, PEAK_TOP - 22 - k * 4, flip=s < 0)
        if t > 3.4:  # 太阳露头
            th = lerp(-0.12, 0.08, ease_out(span(t, 3.4, 6.0)))
            sx, sy = sky_pos(th)
            self.horizon(g, "sun", 0.1, t)
            self.orb(g, "sun", sx, sy, t)
            landscape(g, t)
            if 1.8 < t < 3.2:
                k = span(t, 1.8, 3.2)
                for s in (-1, 1):
                    pix.blit(g, CLOUD_BIG[0] if k < 0.5 else CLOUDLET[0], DX + s * k * 30 - 13,
                             PEAK_TOP - 22 - k * 4, flip=s < 0)
            self.body(g, t, 120, eyes_open=t < 3.6)
            if abs(t - 3.4) < dt:
                self.sparks.burst(118, 40, 12, 20, up=10, life=0.6, gravity=10)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, "sun")
        if t > 4.0:
            self.labels(g, 0, "sun")

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < 5.0:  # 续：天亮
            kind, src, h = self.scene(g, t, e, dt, flow=span(k, 1.5, 4.0))
            if abs(k - 0.1) < dt:
                self.sparks.burst(src[0], src[1], 16, 26, life=0.8, gravity=0)
            self.sparks.step(dt)
            self.sparks.draw(g)
            n = int(e // self.CYCLE) + 1
            pop_title(g, 64, 3, f"第{cn_num(n)}日" if n < 100 else f"{n}日", span(k, 0.3, 0.7), t)
            return
        kind, src, h = self.scene(g, t, e, dt)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.labels(g, e, kind)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        q = span(t, 0.0, 1.2)
        kind, src, h = self.scene(g, t, e, dt, cloud=q, flow=1 - q)
        self.labels(g, e, kind, "云遮" if t > 0.6 else None)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        q = 1 - span(t, 0.0, 1.2)
        kind, src, h = self.scene(g, t, e, dt, cloud=q, flow=span(t, 1.0, 2.0))
        if abs(t - 1.2) < dt:
            self.sparks.burst(src[0], src[1], 14, 22, life=0.6, gravity=0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.labels(g, e, kind)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        stars(g, t, 0.6)
        q = ease_in_out(span(t, 0.3, 2.4))
        top = (DX, 10)
        sx, sy = lerp(110, top[0] + 3, q), lerp(30, top[1], q)
        mx_, my = lerp(10, top[0] - 3, q), lerp(30, top[1], q)
        if t < 2.4:
            self.orb(g, "sun", sx, sy, t)
            self.orb(g, "moon", mx_, my, t)
        landscape(g, t)
        drop = ease_in(span(t, 2.8, 3.6))
        cx, cy = top[0], lerp(top[1], PEAK_TOP - 12, drop)
        if 2.4 <= t < 3.6:  # 合成一团强光，落进身体
            r = 4 + math.sin(t * 20) * 1
            g.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=1)
            for j in range(12):
                a = j * math.pi / 6 + t * 2
                pix.dotted(g, cx + math.cos(a) * (r + 2), cy + math.sin(a) * (r + 2), cx + math.cos(a) * (r + 7),
                           cy + math.sin(a) * (r + 7), 2, int(t * 10))
        h = dao(g, DX, PEAK_TOP, SIT if t < 3.6 else P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"),
                                                          face="happy"), t)
        if t > 3.6:  # 周身放光
            for j in range(3):
                r = ((t - 3.6) * 14 + j * 8) % 24 + 6
                ring(g, DX, PEAK_TOP - 17, r, dotted=2)
        if abs(t - 2.4) < dt:
            pix.flash(g)
            self.sparks.burst(cx, cy, 24, 36, life=1.0, gravity=10)
        if abs(t - 3.6) < dt:
            self.sparks.burst(DX, PEAK_TOP - 17, 20, 30, up=10, life=0.8, gravity=20)
        if 2.4 < t < 2.7 or 3.6 < t < 3.8:
            pix.shake(g, t, 1.2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 点阵：日月从两边合到中间
        if t < 2.4:
            d = int(round(lerp(3, 0, q)))
            for yy in range(3, 5):
                for xx in (3 - d, 4 + d):
                    if 0 <= xx < 8:
                        g.mx[yy, xx] = True
        else:
            mx_ring(g, (t - 2.4) * 4 % 5)
            g.mx[3:5, 3:5] = True
            g.mx_level = 1 + int(6 * (1 - span(t, 2.4, 3.8)))
        if t > 3.0:
            pop_title(g, 96, 3, "日月合璧", span(t, 3.0, 3.4), t)
        else:
            n = int(e // self.CYCLE)
            counter(g, f"第{cn_num(max(n, 1))}日" if n < 100 else f"{n}日")
