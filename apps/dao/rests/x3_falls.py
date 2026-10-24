"""观瀑：李白《望庐山瀑布》“日照香炉生紫烟，遥看瀑布挂前川。飞流直下三千尺，疑是银河落九天。”

入场：崖口先渗出水来，水头一路坠下，砸进深潭，水雾腾起。
持续：两边山崖夹着一挂瀑布，水线一道道往下冲（越往下越快）；潭底水雾翻涌、飞沫四溅，潭面水纹一圈圈荡开；
      远处香炉峰顶飘着烟云；左下礁石上一人负手仰观。
      小事件：水雾里出一道虹（几十秒后淡去）；一片落叶从崖口翻下来，在潭里打转漂走；燕子穿过水雾。
退场：水断了，最后一截水尾落进潭里，水雾散去。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x3_lib import Cloud, bird, ctext, every, halo, layer, peaks, pine_pad, poem_cols, poly_sprite

LIP = 11                 # 崖口
POOL = 50                # 潭面
FX0, FX1 = 56, 72        # 瀑布左右边（崖口处）
G = 140.0                # 水的“重力”（像素/秒²）
LEFT = [(0, 0), (12, 0), (18, 3), (25, 4), (31, 7), (38, 7), (44, 10), (50, 10), (55, 11), (56, 24), (53, 36),
        (55, 50), (0, 50)]
RIGHT = [(73, 11), (79, 9), (86, 9), (92, 5), (99, 4), (106, 0), (128, 0), (128, 50), (74, 50), (76, 38), (73, 26)]
ROCK = [(0, 55), (6, 51), (16, 50), (25, 53), (30, 58), (31, 64), (0, 64)]

GAZER = halo(Sprite("""
  .##..
  ####.
  .##..
  .##..
  ###..
  ####.
  .###.
  .###.
  .###.
  .#.#.
  .#.#.
"""))


def fall_x(y: float, side: int) -> float:
    """瀑布在 y 处的左右边（水离开崖口后略往外鼓）"""
    k = clamp((y - LIP) / (POOL - LIP))
    if side < 0:
        return FX0 - 1.5 * math.sin(k * 2.2) - k * 1
    return FX1 + 1.5 * math.sin(k * 2.2) + k * 1


@register
class WatchFalls(Rest):
    id = "x3.falls"
    name = "观瀑"
    desc = "两崖夹一挂瀑布直落深潭，水雾翻涌、潭纹荡开；礁石上有人仰观，水雾里偶尔出虹"
    T = {"enter": 2.6, "exit": 1.3}

    def setup(self):
        s = self.seed
        self.far = layer(peaks(128, 18, [(64, 1, 14), (42, 7, 14), (90, 5, 14)], s, 0.6), 0.2, outline=2,
                         fog=9, floor=0.0)
        # 斧劈皴：顺着崖势的长短裂线；崖顶受光（抖动），往下转暗
        strokes_l = [(14, 4, 12, 14), (12, 14, 15, 22), (36, 9, 33, 18), (33, 18, 35, 26), (48, 12, 50, 22),
                     (22, 30, 20, 40), (42, 32, 45, 42), (8, 38, 10, 46)]
        strokes_r = [(84, 12, 82, 20), (82, 20, 84, 28), (110, 4, 107, 14), (107, 14, 109, 22), (96, 30, 94, 40),
                     (118, 28, 120, 38), (80, 38, 82, 46)]
        for x, y in ((6, 8), (20, 6), (28, 12), (40, 14), (88, 12), (100, 8), (116, 10), (124, 16)):  # 苔点
            strokes_l.append((x, y, x + 1, y))
        self.cliffs = poly_sprite([LEFT, RIGHT], 0.4, fog_y=0, fog=24, floor=0.07, strokes=strokes_l + strokes_r)
        self.rock = poly_sprite([ROCK], 0.0, strokes=[(8, 55, 12, 60), (18, 54, 22, 62)])
        self.cols = [FX0 + 1.5 + i * (FX1 - FX0 - 3) / 7 for i in range(8)]
        self.mist = [Cloud(__import__("random").Random(s * 5 + i), 16, 7) for i in range(3)]

    # ------------------------------------------------------------ 零件

    def water(self, g: Gfx, t: float, top: float = LIP, bottom: float = POOL):
        """瀑布：两道边线 + 一道道下冲的水线。top/bottom：有水的一段"""
        if bottom <= top:
            return
        ys = [y for y in range(int(top), int(bottom) + 1, 2)]
        if len(ys) < 2:
            ys = [top, bottom]
        left = [(fall_x(y, -1), y) for y in ys]
        right = [(fall_x(y, 1), y) for y in ys]
        g.d.polygon(left + right[::-1], fill=0)
        g.d.line(left, fill=1)
        g.d.line(right, fill=1)
        for i, x0 in enumerate(self.cols):
            sp = 0.6 + rand(i, self.seed) * 0.5
            for j in range(6):  # 每一列的水线段：随时间下落（自由落体，越往下越快）
                ph = (t * sp * 0.9 + j / 6 + rand(i * 7 + j, 3) * 0.1) % 1.0
                d = (POOL - LIP) * ph * ph
                y = LIP + d
                ln = 3 + ph * 9
                if y + ln < top or y > bottom:
                    continue
                k = clamp((y - LIP) / (POOL - LIP))
                x = lerp(x0, (fall_x(y, -1) + fall_x(y, 1)) / 2 + (x0 - (FX0 + FX1) / 2) * 1.25, k)
                g.d.line((x, max(y, top), x, min(y + ln, bottom)), fill=1)
        # 崖口的水沿：一道弧形高光
        if top <= LIP + 1:
            g.d.line((FX0, LIP - 1, FX1, LIP - 1), fill=1)

    def splash(self, g: Gfx, t: float, power: float = 1.0):
        """潭底：水雾团、飞沫"""
        if power <= 0:
            return
        cx = (FX0 + FX1) / 2
        for i, c in enumerate(self.mist):
            p = (t / 4.0 + i / 3) % 1.0
            x = cx + (i - 1) * 9 + math.sin(t * 0.7 + i) * 3
            y = POOL - 1 - p * 14
            c.draw(g, x, y, 0.45 + p * 0.5, a=(1 - p) * power * 1.4, seed=int(t / 4.0 + i / 3) * 3 + i,
                   clear=p < 0.5 and power > 0.6)
        n = int(26 * power)
        for j in range(n):  # 飞沫：抛物线
            ph = (t * 1.4 + rand(j, 8)) % 1.0
            vx = (rand(j, 9) - 0.5) * 50
            vy = -18 - rand(j, 10) * 22
            tt = ph * 0.9
            x = cx + (rand(j, 11) - 0.5) * 12 + vx * tt
            y = POOL + vy * tt + 0.5 * 70 * tt * tt
            if y <= POOL:
                g.px(x, y)

    def pool(self, g: Gfx, t: float):
        g.d.rectangle((0, POOL + 1, 127, 63), fill=0)
        g.d.line((0, POOL, 127, POOL), fill=1)
        cx = (FX0 + FX1) / 2
        for j in range(4):  # 潭纹：从瀑布脚往两边荡开
            p = (t * 0.35 + j / 4) % 1.0
            y = POOL + 2 + p * 11
            w = 10 + p * 60
            for side in (-1, 1):
                x0 = cx + side * (8 + p * 18)
                x1 = x0 + side * (6 + p * 14)
                if rand(j + int(t * 0.35 + j / 4) * 4, 2 + side) < 0.9:
                    g.d.line((x0, y, x1, y), fill=1)
        for x in (88, 100, 112):  # 潭中小石
            g.d.arc((x - 4, POOL + 6, x + 4, POOL + 10), 180, 360, fill=1)

    def pine(self, g: Gfx, t: float):
        """崖口一棵探身的松"""
        sw = (noise(t * 0.5, 4) - 0.5) * 1.5
        g.d.line((40, 11, 44, 6, 50, 4), fill=1)
        g.d.line((41, 11, 45, 7, 49, 5), fill=1)
        g.d.line((44, 6, 42, 2), fill=1)
        pine_pad(g, 52 + sw, 4, 11, sw * 0.3)
        pine_pad(g, 41 + sw * 0.6, 2, 8, sw * 0.2)

    def gazer(self, g: Gfx, t: float):
        x, y = 15, 50
        g.blit(GAZER, x - 1, y - GAZER.h + 1)

    def incense_smoke(self, g: Gfx, t: float):
        """香炉峰顶的烟云（日照香炉生紫烟）"""
        for i in range(3):
            x = 60 + i * 3 + math.sin(t * 0.3 + i) * 2
            for j in range(5):
                yy = 1 - j * 1.0 + (t * 1.5 + i) % 1 + 2
                xx = x + math.sin(t * 0.8 + j * 0.9 + i) * 2 + j * 1.2
                if noise(t + j * 0.7 + i * 3, 5) > 0.35 and yy >= 0:
                    g.px(xx, yy)

    def rainbow(self, g: Gfx, t: float):
        """水雾里的虹：三道同心弧，从左往右“画”出来，再从左往右淡去"""
        ev = every(t, 130.0, 26.0, 50.0)
        if not ev:
            return
        lt = ev[1]
        a0 = 200 + 140 * (ease_in(span(lt, 20, 26)))
        a1 = 200 + 140 * ease_out(span(lt, 0, 3.5))
        if a1 <= a0:
            return
        cx, cy = 64, POOL + 8
        for r, dotted in ((27, False), (24, True), (21, False)):
            if dotted:
                for ang in range(int(a0), int(a1), 5):
                    g.px(cx + math.cos(math.radians(ang)) * r * 1.3, cy + math.sin(math.radians(ang)) * r)
            else:
                g.d.arc((cx - r * 1.3, cy - r, cx + r * 1.3, cy + r), a0, a1, fill=1)

    def leaf(self, g: Gfx, t: float):
        ev = every(t, 53.0, 16.0, 21.0)
        if not ev:
            return
        k, lt = ev
        x0 = FX0 + 3 + rand(k, 4) * (FX1 - FX0 - 6)
        fall = math.sqrt(2 * (POOL - LIP) / G)
        if lt < 0.6:  # 漂到崖口
            x, y = x0 - (0.6 - lt) * 10, LIP - 1
        elif lt < 0.6 + fall:
            ft = lt - 0.6
            x, y = x0 + math.sin(ft * 20) * 1.5, LIP + 0.5 * G * ft * ft
        else:  # 在潭里打转漂走
            ft = lt - 0.6 - fall
            x = x0 + ft * 5 + math.sin(ft * 2) * 3
            y = POOL + 3 + min(ft, 3) * 2
        flip = int(lt * 8) % 2
        g.d.line((x - 1, y - flip, x + 1, y + flip), fill=1)
        g.px(x, y)
        if x > 128:
            return

    def swallow(self, g: Gfx, t: float):
        ev = every(t, 71.0, 3.0, 33.0)
        if not ev:
            return
        k, lt = ev
        p = lt / 3.0
        x = lerp(-6, 134, p)
        y = 40 + math.sin(p * math.pi * 2) * 6 - p * 10
        bird(g, x, y, lt, s=1.0, flap=14)

    def mx(self, g: Gfx, t: float, power: float = 1.0, top: float = 0.0, bottom: float = 8.0):
        g.mx[:, 0] = True
        g.mx[1:, 1] = True
        g.mx[:, 7] = True
        g.mx[2:, 6] = True
        for c in (3, 4):  # 水柱：一点点往下冲
            for j in range(3):
                y = ((t * 7 + j * 2.6 + c * 1.3) % 8)
                if top <= y < bottom:
                    g.mx_set(c, int(y))
            if top <= 0.5 and bottom >= 6:
                g.mx_set(c, 0)
        if power > 0.3:
            for x in (2, 5):
                if int(t * 6 + x) % 3:
                    g.mx_set(x, 7 - int(t * 6 + x) % 2)

    def poem(self, g: Gfx, t: float, k: float):
        if k <= 0:
            return
        g.d.rectangle((100, 0, 127, 50), fill=0)
        poem_cols(g, 127, 3, ("飞流直下", "三千尺"), k)

    # ------------------------------------------------------------ 阶段

    def base(self, g: Gfx, t: float):
        g.blit(self.far, 0, 0)
        self.incense_smoke(g, t)
        g.blit(self.cliffs, 0, 0)
        self.pine(g, t)

    def enter(self, g: Gfx, t: float):
        self.base(g, t)
        self.pool(g, t)
        g.blit(self.rock, 0, 0)
        self.gazer(g, t)
        ft = t - 0.4
        bottom = LIP + 0.5 * G * max(ft, 0) ** 2 if ft > 0 else LIP + 1
        self.water(g, t, LIP, min(bottom, POOL))
        hit = t - 0.4 - math.sqrt(2 * (POOL - LIP) / G)
        if hit > 0:
            self.splash(g, t, power=ease_out(span(hit, 0, 1.2)))
            if hit < 0.25:  # 砸进潭里的一圈水花
                for i in range(10):
                    a = math.pi + i / 9 * math.pi
                    r = hit * 60
                    g.px(64 + math.cos(a) * r, POOL + math.sin(a) * r * 0.5)
        self.poem(g, t, span(t, 1.0, 2.6))
        self.mx(g, t, power=clamp(hit), top=0, bottom=clamp(ft * 6, 0, 8) if ft > 0 else 1)

    def hold(self, g: Gfx, t: float):
        self.base(g, t)
        self.rainbow(g, t)
        self.pool(g, t)
        self.water(g, t)
        self.splash(g, t)
        self.leaf(g, t)
        g.blit(self.rock, 0, 0)
        self.gazer(g, t)
        self.swallow(g, t)
        pk = 1.0 if t < 16 else 1 - span(t, 16, 19) if t < 19 else None
        if pk is None:
            ev = every(t, 160.0, 22.0, 90.0)
            pk = span(ev[1], 0, 2) * (1 - span(ev[1], 19, 22)) if ev else 0
        self.poem(g, t, pk)
        self.mx(g, t)

    def exit(self, g: Gfx, t: float):
        """水断：水尾落下，水雾散去，画面淡出"""
        T = self.T["exit"]
        tt = self.hold_t + t   # 氛围动效接着持续阶段最后的样子
        self.base(g, tt)
        self.pool(g, tt)
        top = LIP + 0.5 * G * t * t
        self.water(g, tt, min(top, POOL), POOL)
        self.splash(g, tt, power=1 - span(t, 0.3, T))
        g.blit(self.rock, 0, 0)
        self.gazer(g, tt)
        g.fade(1 - ease_in(span(t, 0.35, T)))
        self.mx(g, t, power=1 - t / T, top=t / T * 9, bottom=8)
        g.mx[: int(t / T * 8), :] = False
