"""形如槁木：月洞窗前，小道士学南郭子綦凭几而坐、闭目坐忘，一动不动，身边慢慢长出东西，鸟在他头上做了窝。

依据：《庄子·齐物论》：“南郭子綦隐机而坐，仰天而嘘，荅焉似丧其耦。颜成子游立侍乎前，曰：‘何居乎？
形固可使如槁木，而心固可使如死灰乎？’……子綦曰：‘……今者吾丧我，汝知之乎？’”；《大宗师》“坐忘”。

入场：月洞窗、草席、凭几先出现，小道士从下面“坐”进画面一弹，右边竖写“形如槁木”。
持续（一轮 150 秒）：身后大月洞窗（砖砌窗框、窗外一枝梅、一弯月），小道士凭几坐忘，只有呼吸。身边慢慢长东西：
      草从席边冒出、藤从几腿爬上几面、几下结一张蛛网（小蜘蛛垂丝上下）、席角冒出一朵蘑菇；
      60 秒一只小鸟飞来，来回衔枝在他头顶筑巢，趴窝、起身看蛋、雏鸟探头“啾”；90 秒竖写“心如死灰”。
      138 秒他仰天长嘘一口气——一道长气往上散，鸟惊飞，草被吹伏，长出来的一切散掉，“吾丧我”，下一轮重新长。
退场：出定睁眼，画面收拢到脸上。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x1_common import cached, iris, say, twinkle, vplate

FLOOR = 56
MAN_X = 44
GATE = (44, 28, 25)        # 月洞窗中心、半径
CYCLE = 150.0
BIRD_IN = 60.0
SHU = 138.0                # 长嘘
TABLE_X = 60               # 凭几


def _gate():
    """月洞窗 54×54：砖砌圆框（两道亮圈夹一圈砖缝）"""
    p = Part(54, 54)
    p.shape("ellipse", (0, 0, 53, 53), fill=1)
    p.d.ellipse((4, 4, 49, 49), fill=0)
    p.d.ellipse((1, 1, 52, 52), outline=0)
    for a in range(0, 360, 15):                     # 砖缝
        r0, r1 = 23, 26
        ang = math.radians(a)
        p.d.line((26.5 + math.cos(ang) * r0, 26.5 + math.sin(ang) * r0, 26.5 + math.cos(ang) * r1,
                  26.5 + math.sin(ang) * r1), fill=0)
    m = Part(54, 54)
    m.shape("ellipse", (0, 0, 53, 53), fill=1)
    m.d.ellipse((4, 4, 49, 49), fill=0)
    import numpy as np
    ring = np.array(m.on, bool)
    from PIL import Image, ImageDraw
    p.mk = Image.fromarray(ring)
    p.m = ImageDraw.Draw(p.mk)
    return p.sprite()


def _plum():
    """窗外一枝梅 30×20：曲折的枝，几朵五瓣小花和花苞"""
    p = Part(30, 20)
    p.shape("line", [(0, 19), (8, 13), (12, 14), (20, 6), (29, 2)], fill=1, width=1)
    p.shape("line", [(12, 14), (16, 17)], fill=1)
    p.shape("line", [(20, 6), (19, 0)], fill=1)
    for x, y in ((8, 11), (21, 4), (27, 1), (16, 16), (18, 0)):
        p.shape("ellipse", (x - 2, y - 2, x + 2, y + 2), fill=1)
        p.px(x, y, 0)
    for x, y in ((4, 15), (13, 12), (25, 3)):
        p.px(x, y - 1)
    return p.sprite()


def _table():
    """凭几 24×10：弯弧的几面（两头下卷），两条曲足"""
    p = Part(24, 10)
    p.shape("polygon", [(0, 2), (2, 0), (21, 0), (23, 2), (21, 3), (2, 3)], fill=1)
    p.d.line((2, 2, 21, 2), fill=0)
    for x in (3, 18):
        p.shape("polygon", [(x, 3), (x + 3, 3), (x + 2, 9), (x + 4, 9), (x + 4, 10), (x - 1, 10), (x, 9)], fill=1)
        p.px(x + 1, 6, 0)
    return p.sprite()


def _mat():
    """草席 46×4：编织纹（斜线）、两头包边"""
    p = Part(46, 4)
    p.shape("rectangle", (0, 0, 45, 3), fill=1)
    for x in range(2, 44, 3):
        p.d.line((x, 1, x + 1, 2), fill=0)
    p.d.line((0, 0, 0, 3), fill=0)
    return p.sprite()


def _deadtree():
    """槁木 20×44：枯树干（裂纹、树洞），几根光秃的枝"""
    p = Part(20, 44)
    p.shape("polygon", [(6, 43), (8, 30), (7, 18), (9, 10), (11, 18), (12, 30), (15, 43)], fill=1)
    p.shape("line", [(8, 20), (3, 12), (1, 13)], fill=1)
    p.shape("line", [(4, 14), (4, 9)], fill=1)
    p.shape("line", [(11, 24), (17, 16), (19, 17)], fill=1)
    p.shape("line", [(16, 17), (17, 12)], fill=1)
    p.shape("line", [(9, 10), (10, 3), (12, 0)], fill=1)
    p.d.line((10, 26, 10, 36), fill=0), p.d.line((9, 38, 9, 42), fill=0)
    p.d.ellipse((8, 30, 10, 33), fill=0)
    p.dither([(11, 22), (12, 30), (14, 42), (11, 42)], 0.5, 0)
    return p.sprite()


BIRD = pix.frames("""
  ##
 #.##
#####.
 ####
  # #
---
 #   #
  # #
 ####.
#####
  ##
---
  ##
 #.##
######.
 #####
""")
"""小鸟：站 / 飞（翅上扬）/ 趴窝"""

NEST = pix.frames("""
  #  #
#.##.#
---
 # ## #
#.#..#.#
 ######
---
 # #  # #
#.#.##.#.#
##########
 ########
""")

CHICK = pix.frames("""
 ##
#.##.
 ##
---
 ##
#.###
 ##
""")

MUSHROOM = pix.sprite("""
 ####
#.##.#
######
  ##
  ##
""")


@register
class GaoMuRest(Rest):
    id = "x1.gaomu"
    name = "形如槁木"
    desc = "月洞窗前小道士凭几坐忘、一动不动：草长、藤爬、蛛网结起，小鸟在他头上筑巢孵蛋；一声长嘘，万物散去"
    T = {"enter": 3.0, "exit": 1.3}

    # ------------------------------------------------------------ 景

    def room(self, g: Gfx, t: float):
        cx, cy, r = GATE
        pix.blit(g, cached("plum", _plum), cx - 24, cy - 18)
        for i in range(6):
            x = cx - 18 + int(rand(i, 81) * 36)
            y = cy - 20 + int(rand(i, 82) * 18)
            if math.hypot(x - cx, y - cy) < r - 6:
                twinkle(g, x, y, t, i)
        g.d.ellipse((cx + 8, cy - 18, cx + 13, cy - 13), fill=1)  # 月
        g.d.ellipse((cx + 6, cy - 19, cx + 11, cy - 14), fill=0)
        pix.blit(g, cached("gate", _gate), cx - 26, cy - 26, outline=False)
        for i, (x0, y0) in enumerate(((cx - 16, cy - 7), (cx - 3, cy - 14), (cx + 3, cy - 17))):   # 梅瓣飘落
            q = ((t + i * 3.7) % 9.0) / 9.0
            if q < 0.75:
                q /= 0.75
                x = x0 + q * 14 + math.sin(t * 2.2 + i) * 2
                y = y0 + q * (FLOOR - 4 - y0)
                g.px(x, y), g.px(x + 1, y)
                if int(t * 4 + i) % 2:
                    g.px(x, y - 1)
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        pix.checker(g, (0, FLOOR + 2, 128, 64), 0.125)
        pix.blit(g, cached("dead", _deadtree), 98, FLOOR - 43)
        pix.blit(g, cached("mat", _mat), MAN_X - 23, FLOOR - 3)
        pix.blit(g, cached("table", _table), TABLE_X, FLOOR - 13)

    # ------------------------------------------------------------ 慢慢长出来的东西（只依赖这一轮的 k 秒）

    def growth(self, g: Gfx, k: float, t: float, blow: float):
        """blow 0..1：长嘘吹散（草伏倒、东西淡出）"""
        fade = 1 - blow
        if fade <= 0:
            return
        # 草：席两边冒出来
        gh = span(k, 8, 60) * 5
        for i, x in enumerate((MAN_X - 26, MAN_X - 24, MAN_X + 26, TABLE_X + 26, 22, 88)):
            hgt = int(gh * (0.6 + rand(i, 91) * 0.6))
            if hgt <= 0:
                continue
            lean = blow * 5 + math.sin(t * 0.7 + i) * 0.6
            g.d.line((x, FLOOR, x + lean, FLOOR - hgt), fill=1)
            g.d.line((x + 1, FLOOR, x + 1 + lean * 1.3, FLOOR - hgt + 1), fill=1)
        # 藤：从几腿爬上几面再搭过去，节上长叶
        vl = span(k, 15, 100)
        pts = [(TABLE_X + 4, FLOOR), (TABLE_X + 3, FLOOR - 5), (TABLE_X + 5, FLOOR - 10), (TABLE_X + 9, FLOOR - 14),
               (TABLE_X + 15, FLOOR - 15), (TABLE_X + 21, FLOOR - 14)]
        n = vl * (len(pts) - 1)
        for j in range(int(n)):
            if blow > 0 and rand(j, 92) < blow:
                continue
            g.d.line((pts[j], pts[j + 1]), fill=1)
            lx, ly = pts[j + 1]
            g.px(lx - 1, ly - 1), g.px(lx - 2, ly - 1), g.px(lx - 1, ly - 2)
        # 蛛网：几下面，先拉辐丝，再一圈圈
        wk = span(k, 30, 75)
        if wk > 0:
            cx, cy = TABLE_X + 12, FLOOR - 6
            for a in range(5):
                if wk * 5 > a and rand(a, 93) >= blow:
                    ang = math.pi + a * math.pi / 4
                    g.d.line((cx, cy, cx + math.cos(ang) * 7, cy - abs(math.sin(ang)) * 6), fill=1) if a else None
            for ring in range(1, 4):
                if wk > 0.4 + ring * 0.18 and rand(ring, 94) >= blow:
                    g.d.arc((cx - ring * 2, cy - ring * 2, cx + ring * 2, cy + ring * 2), 180, 360, fill=1)
            sy = cy - 6 + 4 + math.sin(t * 0.9) * 2           # 小蜘蛛垂丝
            if blow < 0.5:
                g.d.line((cx + 4, FLOOR - 13, cx + 4, sy), fill=1)
                g.px(cx + 3, sy + 1), g.px(cx + 4, sy + 1), g.px(cx + 5, sy + 1), g.px(cx + 4, sy + 2)
        # 蘑菇
        mk = span(k, 70, 85)
        if mk > 0 and blow < 0.6:
            s = pix.stretch(MUSHROOM, 1.0, max(0.3, mk))
            pix.blit(g, s, MAN_X - 30, FLOOR - s.h)

    def bird(self, g: Gfx, k: float, t: float, blow: float):
        """小鸟：衔枝来回三趟 → 巢一点点高 → 趴窝 → 起身看蛋 → 雏鸟探头；长嘘时惊飞。返回 (巢阶段, 叫)"""
        hx, hy = MAN_X, FLOOR - 36                     # 头顶
        nest = -1
        chirp = False
        if k < BIRD_IN:
            return nest, chirp
        b = k - BIRD_IN
        if b < 24:                                     # 衔枝：三趟，每趟 8 秒
            trip, q = int(b // 8), (b % 8) / 8
            nest = trip - 1 if q < 0.5 else trip
            if q < 0.4:
                x, y = lerp(140, hx + 2, ease_out(q / 0.4)), lerp(4, hy - 4, ease_out(q / 0.4))
                fr = BIRD[1 if int(t * 8) % 2 else 2]
            elif q < 0.6:
                x, y, fr = hx + 2, hy - 4, BIRD[0]
            else:
                q2 = (q - 0.6) / 0.4
                x, y = lerp(hx + 2, 140, ease_in(q2)), lerp(hy - 4, 0, ease_in(q2))
                fr = BIRD[1 if int(t * 8) % 2 else 2]
            if 0 <= nest:
                pix.blit(g, NEST[min(nest, 2)], hx - 5, hy - 2 - NEST[min(nest, 2)].h + 3)
            if q < 0.5:
                g.d.line((x + 6, y + 1, x + 10, y), fill=1)   # 嘴里叼的枝
            pix.blit(g, fr, x, y - 3)
            return nest, chirp
        nest = 2
        if blow > 0:                                   # 惊飞
            q = ease_in(blow)
            pix.blit(g, NEST[2], hx - 5, hy - 2 - NEST[2].h + 3 + q * 10)
            pix.blit(g, BIRD[1 if int(t * 10) % 2 else 2], hx + q * 80, hy - 7 - q * 40)
            return nest, chirp
        pix.blit(g, NEST[2], hx - 5, hy - NEST[2].h + 1)
        c = b - 24
        if c < 20 or c > 50:                           # 趴窝
            pix.blit(g, BIRD[2], hx - 3, hy - NEST[2].h - 2)
        elif c < 30:                                   # 起身看蛋
            pix.blit(g, BIRD[0], hx + 2, hy - NEST[2].h - 5)
            g.d.ellipse((hx - 3, hy - NEST[2].h - 1, hx, hy - NEST[2].h + 2), fill=1)
        else:                                          # 雏鸟探头
            pix.blit(g, BIRD[0], hx + 3, hy - NEST[2].h - 5)
            pix.blit(g, CHICK[int(t * 3) % 2], hx - 3, hy - NEST[2].h - 2)
            chirp = (c % 4) < 1.2
        return nest, chirp

    def shu(self, g: Gfx, k: float):
        """长嘘：一道长气从嘴里往上散，打着旋"""
        q = span(k, SHU, SHU + 4)
        mx, my = MAN_X + 8, FLOOR - 21
        for i in range(14):
            a = i / 13
            if a > q * 1.4:
                break
            x = mx + 3 + a * 26 + math.sin(a * 9 - k * 6) * 3
            y = my - a * 34
            g.px(x, y)
            if i % 2:
                g.px(x + 1, y)
        if q > 0.2:
            for j in range(3):
                yy = 40 - j * 10 - q * 8
                g.d.line((10 + j * 6, yy, 24 + j * 6, yy), fill=1)

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        k = t % CYCLE
        blow = span(k, SHU + 0.8, SHU + 6.0)
        self.room(g, t)
        face = "sleep"
        if SHU <= k < SHU + 4.5:
            face = "wow"
        h = daoshi(g, MAN_X, FLOOR - 1, "meditate", t, face=face)
        self.growth(g, k, t, blow)
        nest, chirp = self.bird(g, k, t, blow)
        if SHU <= k < SHU + 5:
            self.shu(g, k)
        if chirp:
            say(g, MAN_X + 12, 3, "啾", 1.0, size=8)
        w = span(k, 90, 91.8)
        if 90 <= k < 100:
            vplate(g, 116, 4, "心如死灰", n=int(w * 4) + 1)
        if SHU + 2 <= k < CYCLE - 0.5:
            vplate(g, 116, 4, "吾丧我", n=int(span(k, SHU + 2, SHU + 3.2) * 3) + 1)
        self.matrix(g, t, k, nest, blow)

    def matrix(self, g: Gfx, t: float, k: float, nest: int, blow: float):
        """一棵小苗随这一轮慢慢长高；鸟在巢时顶上停一只；长嘘后缩回去"""
        hgt = int(span(k, 0, 120) * 5 * (1 - blow)) + 1
        g.mx[7, :] = True
        for y in range(7, 7 - hgt - 1, -1):
            g.mx_set(3, y)
        if hgt >= 3:
            g.mx_set(2, 7 - hgt + 1), g.mx_set(4, 7 - hgt + 2)
        if hgt >= 5:
            g.mx_set(1, 7 - hgt + 2), g.mx_set(5, 7 - hgt + 3)
        if nest >= 2 and blow == 0:
            g.mx_set(3, 0), g.mx_set(4, 0), g.mx_set(4, 1)

    def enter(self, g: Gfx, t: float):
        """月洞窗、席、几先出来，小道士从下面“坐”进画面一弹，右边竖写“形如槁木”"""
        self.room(g, t)
        q = span(t, 0.4, 1.4)
        dy = (1 - ease_out_back(q)) * 40
        daoshi(g, MAN_X, FLOOR - 1 + dy, "meditate", t)
        if t > 1.6:
            vplate(g, 116, 4, "形如槁木", n=int(span(t, 1.6, 2.6) * 4) + 1)
        self.matrix(g, 0.0, 0.0, -1, 0)
        iris(g, MAN_X, 30, lerp(6, 150, ease_out(span(t, 0, 0.9))))

    def exit(self, g: Gfx, t: float):
        h0 = self.hold_t
        k = h0 % CYCLE
        blow = span(k, SHU + 0.8, SHU + 6.0)
        self.room(g, h0 + t)
        daoshi(g, MAN_X, FLOOR - 1, "sit", h0 + t, face="normal" if t > 0.3 else "sleep")
        self.growth(g, k, h0, blow)
        self.bird(g, k, h0, blow)
        self.matrix(g, h0, k, -1, blow)
        iris(g, MAN_X + 2, FLOOR - 22, lerp(140, 0, ease_in_out(span(t, 0.4, self.T["exit"] - 0.05))))
