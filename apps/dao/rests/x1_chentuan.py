"""陈抟高卧：华山石室的岩檐下，小道士学希夷先生侧身支颐而卧（蛰龙睡），一睡就是百余日。

依据：《宋史·隐逸传·陈抟》：“移居华山云台观，又止少华石室，每寝处，多百余日不起。”太宗赐号“希夷先生”；
后世称“睡仙”，其睡法为侧身屈膝的“蛰龙睡”。周世宗、宋太宗都曾召他入朝。

入场：小道士坐在卧石上，张大嘴打个哈欠，往旁边一倒，侧卧支颐，扬起一点尘土，Z 冒起来。
持续：岩檐、石壁、卧石、远处华山三峰。40 秒为“一日”：太阳从右往左走，入夜换弯月和星，天明时右上写“第几日”；
      每 3 日换一季：春落花、夏萤火、秋落叶、冬下雪。他随呼吸起伏、一直冒 Z。
      小事件（每 150 秒一轮）：仙鹤衔诏飞来，诏书落在脚边，鹤站着等——一声大鼾把诏书和鹤一起吹飞（61s）；
      鼾声如雷，山摇，岩檐落下碎石（100s）；“多百余日不起”逐字竖写出来（127s）。
退场：睁眼，Z 散去，画面收拢到他脸上。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x1_common import CRANE_STAND, cached, crane_fly, ev, iris, plate, recline, twinkle, vplate, zzz

SLAB = 50          # 卧石面
MAN_X = 14
DAY = 40.0
SEASON_DAYS = 3
EV = 150.0


def _rock():
    """整屏的石头：左边石壁、顶上岩檐（下沿垂着石乳和草）、卧石、地面、远处华山三峰"""
    p = Part(128, 64)
    # 石壁 + 岩檐（暗心白边）
    p.shape("polygon", [(0, 0), (86, 0), (82, 3), (73, 5), (62, 7), (50, 8), (38, 9), (28, 11), (19, 14), (14, 19),
                        (11, 28), (9, 40), (9, 50), (6, 58), (0, 58)], fill=0)
    p.d.line([(86, 0), (82, 3), (73, 5), (62, 7), (50, 8), (38, 9), (28, 11), (19, 14), (14, 19), (11, 28), (9, 40),
              (9, 50), (6, 58)], fill=1)
    p.dither([(80, 1), (73, 4), (50, 7), (28, 10), (19, 13), (14, 18), (11, 27), (9, 40), (8, 48), (5, 48), (6, 40),
              (8, 27), (11, 17), (16, 11), (26, 8), (48, 5), (72, 2), (82, 0)], 0.25, 1)
    p.d.line([(78, 0), (72, 3), (61, 5), (49, 6), (37, 7), (27, 9), (18, 12), (12, 18), (9, 27), (7, 40), (7, 49)],
             fill=0)                                                    # 边沿内侧一道暗线，让亮边更利落
    for pts in (((30, 2), (36, 5), (44, 4)), ((56, 1), (60, 4)), ((3, 12), (6, 20), (4, 26)), ((2, 36), (5, 44)),
                ((14, 4), (20, 7))):
        p.d.line(pts, fill=1)
    for x, y, n in ((44, 9, 3), (58, 8, 2), (24, 12, 2), (70, 6, 2)):   # 石乳
        p.d.line((x, y, x, y + n), fill=1)
    for x, y in ((33, 10), (66, 7), (17, 16)):                          # 垂下的草
        p.d.line((x, y, x - 1, y + 3), fill=1), p.d.line((x + 1, y, x + 2, y + 2), fill=1)
    # 卧石：上面一道亮面，前脸暗，带几道石纹
    p.shape("polygon", [(10, SLAB), (78, SLAB), (82, SLAB + 3), (79, 58), (8, 58)], fill=0)
    p.d.line((10, SLAB, 78, SLAB), fill=1)
    p.d.line((11, SLAB + 1, 77, SLAB + 1), fill=1)
    p.d.line([(78, SLAB), (82, SLAB + 3), (79, 58)], fill=1)
    p.dither([(11, SLAB + 2), (79, SLAB + 2), (79, SLAB + 3), (11, SLAB + 3)], 0.5, 1)
    for x0, x1, y in ((16, 26, 54), (40, 46, 55), (60, 72, 54)):
        p.d.line((x0, y, x1, y), fill=1)
    # 地面
    p.shape("line", (0, 58, 127, 58), fill=1)
    p.dither([(0, 60), (128, 60), (128, 64), (0, 64)], 0.25, 1)
    # 华山三峰（远，只勾线）：西峰、中峰、东峰，峰上一棵小松
    p.d.line([(80, 58), (86, 44), (90, 46), (98, 20), (101, 24), (104, 30), (108, 26), (112, 18), (116, 30),
              (122, 36), (127, 40)], fill=1)
    for pts in (((98, 20), (97, 30), (99, 40)), ((112, 18), (111, 28)), ((101, 24), (103, 34)), ((88, 46), (87, 52))):
        p.d.line(pts, fill=1)
    p.d.line((110, 21, 108, 23), fill=1), p.d.line((110, 21, 112, 23), fill=1)
    return p.sprite()


SUN = pix.frames("""
  # # #
   ###
 #.###.#
 #######
 #.###.#
   ###
  # # #
---
   # #
 # ### #
  .###.
 #######
  .###.
 # ### #
   # #
""")

MOON = pix.sprite("""
  ###
 ##.
##.
##.
##.
 ##.
  ###
""")

SCROLL = pix.frames("""
#.###.#
#.###.#
---
 #
###
 #
.#.
 #
###
 #
""")

PETAL = pix.frames("""
 #
#.#
 #
---
#
 #
""")

LEAF = pix.frames("""
 ##
###
#
---
#
##
 ##
---
##
 ##
  #
""")

PEBBLE = pix.sprite("""
##
##
""")


def drift(i: int, t: float, seed: int, fall: float, x0: float = 20, x1: float = 128, y0: float = 6):
    """确定性飘落：第 i 片从上面落到地面（只依赖 t）"""
    period = 64.0 / fall
    ph = rand(i, seed) * period
    k = ((t + ph) % period) / period
    x = x0 + rand(i, seed + 1) * (x1 - x0) + math.sin(t * 1.3 + i) * 3 - k * 10
    return x, y0 + k * 52


@register
class ChenTuanRest(Rest):
    id = "x1.chentuan"
    name = "陈抟高卧"
    desc = "华山石室岩檐下，小道士侧身支颐而卧（蛰龙睡），日月轮转、四季更替，仙鹤衔诏来也被一声大鼾吹走"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.season0 = self.rng.randrange(4)

    # ------------------------------------------------------------ 天

    def sky(self, g: Gfx, t: float):
        k = (t % DAY) / DAY
        if k < 0.6:   # 白天：太阳从右往左
            q = k / 0.6
            x, y = lerp(122, 78, q), 24 - math.sin(q * math.pi) * 18
            pix.blit(g, pix.anim(SUN, t, 2), x - 3, y - 3)
        else:         # 夜里：弯月 + 星
            q = (k - 0.6) / 0.4
            x, y = lerp(122, 80, q), 22 - math.sin(q * math.pi) * 14
            pix.blit(g, MOON, x - 2, y - 3)
            for i in range(9):
                sx, sy = 74 + int(rand(i, 3) * 52), 3 + int(rand(i, 4) * 16)
                if abs(sx - x) > 4 or abs(sy - y) > 5:
                    twinkle(g, sx, sy, t, i, big=i % 4 == 0)
        return k

    def season(self, g: Gfx, t: float, night: bool):
        s = (int(t // (DAY * SEASON_DAYS)) + self.season0) % 4
        if s == 0:      # 春：落花
            for i in range(5):
                x, y = drift(i, t, 21, 6.0)
                pix.blit(g, pix.anim(PETAL, t + i, 2), x, y, outline=False)
        elif s == 1:    # 夏：萤火（夜里）/ 飞虫
            for i in range(3 if night else 0):
                x = 40 + i * 25 + math.sin(t * 0.5 + i * 2) * 10
                y = 38 + math.sin(t * 0.8 + i) * 6
                if (t * 0.6 + i * 0.33) % 1 < 0.5:
                    g.px(x, y), g.px(x + 1, y), g.px(x, y + 1), g.px(x - 1, y), g.px(x, y - 1)
        elif s == 2:    # 秋：落叶
            for i in range(4):
                x, y = drift(i, t, 31, 5.0)
                pix.blit(g, pix.anim(LEAF, t * 0.7 + i, 3), x, y, outline=False)
        else:           # 冬：雪
            for i in range(14):
                x, y = drift(i, t, 41, 4.0, 14, 128, 8)
                g.px(x, y)
                if i % 3 == 0:
                    g.px(x + 1, y), g.px(x, y + 1), g.px(x - 1, y), g.px(x, y - 1)
        return s

    # ------------------------------------------------------------ 画面

    def stage(self, g: Gfx, t: float, shake: float = 0.0):
        k = self.sky(g, t)
        pix.blit(g, cached("rock", _rock), 0, 0, outline=False)
        return k

    def hold(self, g: Gfx, t: float):
        self.draw(g, t)

    def draw(self, g: Gfx, t: float, awake: float = 0.0):
        k = self.stage(g, t)
        night = k >= 0.6
        thunder = ev(t, EV, 100.0, 3.2)
        crane = ev(t, EV, 61.0, 11.0)
        blow = crane is not None and crane > 7.0
        face = "sleep"
        if awake > 0:
            face = "normal"
        elif thunder is not None or blow:
            face = "wow" if (thunder or 0) % 0.6 < 0.3 or blow else "sleep"
        h = recline(g, MAN_X, SLAB, t, face=face)
        if crane is not None:
            self.crane_event(g, t, crane, h)
        if thunder is not None:
            self.thunder(g, t, thunder, h)
        s = self.season(g, t, night)
        if awake <= 0:
            big = thunder is not None
            zzz(g, h["mouth"][0] + 3, h["mouth"][1] - 4, t, n=3 if not big else 4, period=2.6 if not big else 1.2,
                dx=20 if not big else 28, dy=-12)
        self.words(g, t, k, thunder)
        self.matrix(g, t, h, crane, thunder)
        return h

    def crane_event(self, g: Gfx, t: float, c: float, h: dict):
        """仙鹤衔诏飞来 → 诏书落在脚边 → 站着等、点脚 → 大鼾一吹，诏书和鹤一起飞走"""
        lx, ly = 106, 58  # 鹤落脚处
        sx, sy = 72, SLAB  # 诏书落处
        if c < 2.5:       # 飞来：从右上滑下
            q = ease_out(c / 2.5)
            x, y = lerp(140, lx + 2, q), lerp(6, ly - 22, q)
            crane_fly(g, x, y, t, flip=True)
            pix.blit(g, SCROLL[0], x - 13, y + 1)
        elif c < 7.0:     # 站着等；诏书从嘴里掉到脚边
            pix.blit(g, CRANE_STAND[int(t * 2) % 2], lx - 6, ly - 20, flip=True)
            q = span(c, 2.5, 3.1)
            if q < 1:
                pix.blit(g, SCROLL[1 if int(c * 8) % 2 else 0], lerp(lx - 9, sx, q), lerp(ly - 18, sy - 2, ease_in(q)))
            else:
                pix.blit(g, SCROLL[0], sx, sy - 2)
        else:             # 大鼾：一股风从嘴里冲出去，诏书翻滚着飞走，鹤被吹得往后飞
            q = span(c, 7.0, 11.0)
            mx, my = h["mouth"]
            for i in range(4):   # 风线
                a = (q * 3 + i * 0.25) % 1
                y = my - 6 + i * 4
                x0 = mx + 4 + a * 80
                g.d.line((x0, y, x0 + 10, y), fill=1)
                g.px(x0 + 13, y)
            pix.blit(g, SCROLL[1 if int(c * 10) % 2 else 0], sx + ease_in(q) * 70, sy - 2 - math.sin(q * 3) * 18)
            crane_fly(g, lx + ease_in(q) * 60, ly - 18 - q * 30, t * 2, flip=True)

    def thunder(self, g: Gfx, t: float, c: float, h: dict):
        """鼾声如雷：山摇、声浪一圈圈、岩檐落下碎石"""
        if c < 1.6:
            pix.shake(g, t, 1.2)
        mx, my = h["mouth"]
        for j in range(3):   # 声浪：嘴前一道道 ）
            r = (c * 10 + j * 4) % 12 + 4
            if c < 2.4:
                g.d.arc((mx + 2 - r, my - 2 - r, mx + 2 + r, my - 2 + r), 300, 360, fill=1)
        for i in range(4):
            x = 30 + i * 13
            y0 = 10
            y = y0 + (c - i * 0.2) ** 2 * 30
            if 0 < c - i * 0.2 and y < SLAB - 2:
                pix.blit(g, PEBBLE, x, y)

    def words(self, g: Gfx, t: float, k: float, thunder):
        """字（最后画）：天明时右上“第几日”；每轮 127 秒竖写“多百余日不起”"""
        dk = t % DAY
        day = int(t // DAY) + 1
        w = ev(t, EV, 127.0, 9.0)
        if dk < 3.5 and t > 1.0 and w is None:
            s = f"第{cn_num(day)}日" if day < 100 else f"{day}日"
            plate(g, 125, 3, s, size=12, k=span(dk, 0, 0.3), align="right")
        if w is not None:
            n = int(w / 0.45) + 1             # 竖写两行，从右往左读
            vplate(g, 114, 4, "多百余", n=min(n, 3))
            if n > 3:
                vplate(g, 99, 4, "日不起", n=n - 3)

    def matrix(self, g: Gfx, t: float, h: dict, crane, thunder):
        g.mx[7, :] = True                      # 卧石
        g.mx[6, 0:5] = True                    # 侧卧的人
        g.mx[5, 0:2] = True
        g.mx[4, 0] = g.mx[4, 1] = True
        b = (t / 3.6) % 1 < 0.5
        g.mx[5, 2] = b
        k = (t / 2.6) % 1
        zx, zy = 2 + int(k * 4), 3 - int(k * 3)
        for a, c in ((0, 0), (1, 0), (1, 1), (0, 2), (1, 2)):
            g.mx_set(zx + a, zy + c - 1)
        if thunder is not None and thunder < 1.6:
            g.mx_level = 6

    # ------------------------------------------------------------ 入场 / 退场

    def enter(self, g: Gfx, t: float):
        """坐在卧石上打哈欠 → 一倒侧卧，扬起尘土 → Z 冒起"""
        self.stage(g, 0.0)
        if t < 1.6:
            yawn = 0.3 < t < 1.3
            daoshi(g, MAN_X + 16, SLAB, "sit", t, face="wow" if yawn else "normal")
            if yawn:
                g.text(MAN_X + 28, 18, "哈", size=12)
        else:
            h = recline(g, MAN_X, SLAB, t, face="sleep")
            q = span(t, 1.6, 2.3)
            if q < 1:   # 落下扬起的尘土
                for i in range(5):
                    x = MAN_X + 10 + i * 9 + q * (i - 2) * 3
                    y = SLAB - 2 - q * 4 - (i % 2)
                    if q < 0.7:
                        g.d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=1)
                    else:
                        g.px(x, y)
            if t > 2.3:
                zzz(g, h["mouth"][0] + 2, h["mouth"][1] - 4, t, on=span(t, 2.3, 3.0) * 1.2, dx=16, dy=-18)
        self.season(g, 0.0, False)
        self.matrix(g, t, {}, None, None)
        iris(g, MAN_X + 18, SLAB - 16, lerp(6, 150, ease_out(span(t, 0.0, 1.2))))

    def exit(self, g: Gfx, t: float):
        h0 = self.hold_t
        k = self.stage(g, h0)
        h = recline(g, MAN_X, SLAB, h0, face="normal" if t > 0.25 else "sleep")
        self.season(g, h0 + t, k >= 0.6)
        if t < 0.5:
            zzz(g, h["mouth"][0] + 2, h["mouth"][1] - 4, h0 + t * 3, on=1 - t * 2, dx=16, dy=-18)
        g.mx[7, :] = True
        if t > 0.25:
            g.mx_rows([0x00, 0x66, 0x66, 0x00, 0x00, 0x42, 0x3C, 0xFF])
        ex, ey = h["eye"]
        iris(g, ex + 2, ey, lerp(140, 0, ease_in_out(span(t, 0.3, self.T["exit"] - 0.05))))
