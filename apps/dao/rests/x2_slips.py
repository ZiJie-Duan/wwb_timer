"""读经：竹简（两道编绳、无标点、分章圆点）。经文：《道德经》第一、六（谷神不死）、八、十六章与第二十五章末句，
《庄子·逍遥游》藐姑射神人一段。彩蛋：段成式《酉阳杂俎》“蠹鱼三食神仙字，则化为此物，名曰脉望。
夜以规映当天中星，星使立降，可求还丹”（为了好玩简化成：吃满三回就化）。

夜读：左上一扇小窗见星，脚边一盏油灯。小道士盘坐，一手扶着左边的简卷，面前竖着展开一册竹简
（一枚枚竹简、竹节纹、上下两道编绳）。正在读的那枚简上，字一个个反白（从上往下），他一边读一边点头、张嘴；
读完一枚，竹简往右挪一格，读过的卷进右卷，左卷（他手里那卷）转一下放出新简。近处两枚看得清字，远处的简只见墨痕。
入场：竹简从左卷里“哗”地一枚枚摊开，灯点亮。
持续：每 3.6 秒读完一枚简。每 50 秒一条蠹鱼从简底爬上来，把一个字啃出个缺口，再爬下去；
      每第三回它卷成一个发光的圆环“脉望”飘出窗去，天上一颗星闪下来（小道士看呆了）。
退场：竹简卷回左卷，收圆。
点阵：竖简往右滑，读到的字是一个往下走的亮点；化脉望时是一个发亮的圆环。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import Clock, iris, label, put_arm, win

TEXT = ("道可道非常道名可名非常名无名天地之始有名万物之母故常无欲以观其妙常有欲以观其徼此两者同出而异名同谓之玄玄之又玄众妙之门"
        "〇谷神不死是谓玄牝玄牝之门是谓天地根绵绵若存用之不勤"
        "〇上善若水水善利万物而不争处众人之所恶故几于道"
        "〇致虚极守静笃万物并作吾以观复夫物芸芸各复归其根归根曰静是谓复命"
        "〇人法地地法天天法道道法自然"
        "〇藐姑射之山有神人居焉肌肤若冰雪淖约若处子不食五谷吸风饮露乘云气御飞龙而游乎四海之外"
        "〇")
TEXT = TEXT + "  " * 0
NS = (len(TEXT) + 2) // 3          # 简的枚数（一枚三字）
FLOOR = 58
DX = 18                            # 小道士（盘坐，朝右）
ROLL_L = 33                        # 左卷
X0 = 40                            # 正在读的那枚简的左边
PITCH = 15
TOP, BOT = 11, 53                  # 简的上下
ROW_Y = (14, 27, 40)               # 三个字的顶
CORDS = (26, 39)
SLIP = 3.6                         # 读一枚简的秒数
SLIDE = 0.5
WORM = 50.0


def slip_chars(j: int) -> str:
    j %= NS
    return TEXT[j * 3:j * 3 + 3]


def _scribble(seed: int) -> Sprite:
    """远处简上的墨痕：一个字大小里几笔短划"""
    p = Part(10, 10)
    for i in range(4):
        x0 = 1 + int(rand(i, seed) * 6)
        y0 = 1 + int(rand(i + 9, seed) * 7)
        if rand(i + 3, seed) < 0.5:
            p.shape("line", (x0, y0, x0 + 2 + int(rand(i + 5, seed) * 3), y0), fill=1)
        else:
            p.shape("line", (x0, y0, x0, y0 + 2 + int(rand(i + 7, seed) * 3)), fill=1)
    return p.sprite()


SCRIB = [_scribble(i) for i in range(12)]

WORM_SPR = pix.frames("""
#   #
 #.#
.###.
 ###
.###.
 ###
 # #
#   #
---
 # #
 #.#
#.###
 ###
.###.#
 ###
 # #
  #
""")


def _lamp():
    """油灯 7×9：灯盏、灯柱、底座"""
    p = Part(7, 9)
    p.shape("polygon", [(0, 0), (6, 0), (5, 2), (1, 2)], fill=1)
    p.d.line((1, 1, 5, 1), fill=0)
    p.shape("rectangle", (3, 3, 3, 6), fill=1)
    p.shape("rectangle", (1, 7, 5, 8), fill=1)
    p.px(2, 7, 0)
    return p.sprite()


LAMP = _lamp()
FLAME = pix.frames("""
 #
###
 #
---
#
##
###
 #
---
  #
 ##
###
 #
""")


@register
class Slips(Rest):
    id = "x2.slips"
    name = "读经"
    desc = "夜读竹简：小道士扶着简卷一字一字读《道德经》《庄子》，读完一枚简往右卷一格；蠹鱼啃字，三食神仙字化为脉望飘去"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.ht = 0.0
        self.j0 = self.rng.randrange(NS)
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    # ------------------------------------------------------------ 简

    def slips(self, g: Gfx, t: float, open_k: float = 1.0):
        """→ (正在读的简号, 读到第几个字 0..2, 滑动量 0..1)"""
        cur = int(t // SLIP)
        k = t % SLIP
        slide = ease_in_out(span(k, SLIP - SLIDE, SLIP))
        row = min(2, int(k / ((SLIP - SLIDE) / 3)))
        right = 122
        n_vis = int(6 * open_k) + 1
        # 背后：竹简底色区
        for p in range(-1, n_vis):
            x = X0 + (p + slide) * PITCH
            if x > right - 2 or x < ROLL_L + 2:
                continue
            j = cur - p
            w = min(PITCH - 2, right - 2 - x)
            g.d.rectangle((x, TOP, x + w, BOT), outline=1, fill=0)
            g.px(x + 3, TOP + 1), g.px(x + w - 3, BOT - 1)        # 竹节纹
            near = p in (0, 1) or (p == -1)
            for r, y in enumerate(ROW_Y):
                ch = slip_chars(self.j0 + j)[r:r + 1]
                if not ch:
                    continue
                if ch == "〇":                                    # 分章圆点
                    g.d.ellipse((x + 4, y + 3, x + 8, y + 7), fill=1)
                    continue
                if self.bitten(j, r, t):
                    continue
                if near and w >= 12:
                    continue                                      # 近处的字最后再写
                spr = SCRIB[(j * 3 + r) % len(SCRIB)]
                pix.blit(g, spr, x + 2, y + 1, outline=False)
        for y in CORDS:                                           # 编绳（扭成一节一节）
            g.d.line((ROLL_L + 3, y, right, y), fill=1)
            for x in range(ROLL_L + 4, right, 3):
                g.px(x, y, 0)
        return cur, row, slide

    def bitten(self, j: int, r: int, t: float) -> bool:
        """被蠹鱼啃掉的字（啃完以后就一直缺着，直到卷走）"""
        n = int((t - 20.0) // WORM)
        for m in range(max(0, n - 1), n + 1):
            jj, rr = self.worm_target(m)
            if jj == j and rr == r and t >= 20.0 + m * WORM + 4.5:
                return True
        return False

    def worm_target(self, m: int):
        """第 m 回蠹鱼啃的是哪枚简的哪个字：啃刚读过的第二枚（p=2）"""
        t0 = 20.0 + m * WORM
        cur = int(t0 // SLIP)
        return cur - 2, int(rand(m, self.seed) * 3)

    def rolls(self, g: Gfx, t: float, spin: float, right_x: float = 122):
        """两头的简卷：一捆竖着卷起的竹简，顶上看得见一圈圈卷纹，侧面是一根根简的边，转起来纹路移动"""
        for x, w in ((ROLL_L - 5, 8), (right_x, 7)):
            g.d.rectangle((x, TOP, x + w, BOT), fill=1)
            for i in range(3):                                   # 简边（随转动移动）
                xx = x + 1 + int((i * 3 + spin * 6) % (w - 1))
                g.d.line((xx, TOP + 2, xx, BOT - 1), fill=0)
            g.d.line((x + w, TOP + 1, x + w, BOT), fill=0)
            for y in CORDS:                                      # 编绳绕过卷
                g.d.line((x, y, x + w, y), fill=0)
                g.d.line((x, y + 1, x + w, y + 1), fill=1)
            cx = x + w / 2                                       # 顶端：卷纹（一圈圈）
            g.d.ellipse((x - 1, TOP - 3, x + w + 1, TOP + 2), fill=1)
            g.d.ellipse((cx - 3, TOP - 2, cx + 3, TOP + 1), outline=0)
            g.px(cx, TOP - 1, 0)
            g.d.ellipse((x - 1, BOT - 2, x + w + 1, BOT + 2), fill=1)
            g.d.line((x + 1, BOT + 1, x + w - 1, BOT + 1), fill=0)

    def near_text(self, g: Gfx, t: float, cur: int, row: int, slide: float):
        """正在读的简与刚读过的那枚：真字；正在读的字反白"""
        for p in (0, 1):
            x = X0 + (p + slide) * PITCH
            j = cur - p
            chars = slip_chars(self.j0 + j)
            for r, y in enumerate(ROW_Y):
                ch = chars[r:r + 1]
                if not ch or ch == "〇" or ch == " " or self.bitten(j, r, t):
                    continue
                if p == 0 and r == row and slide == 0:
                    g.d.rectangle((x + 1, y - 1, x + 12, y + 11), fill=1)
                    g.text(x + 1, y, ch, fill=0)
                else:
                    g.text(x + 1, y, ch)

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, enter: float = 1.0, close: float = 0.0):
        dt = self.clock.dt(t)
        on = enter >= 1
        e3 = enter * self.T["enter"]
        # 窗与星
        g.d.rectangle((2, 2, 24, 18), outline=1)
        g.d.line((13, 2, 13, 18), fill=1), g.d.line((2, 10, 24, 10), fill=1)
        for i, (sx, sy) in enumerate(((6, 5), (19, 7), (9, 14), (21, 15))):
            if (t * 0.7 + i * 0.4) % 3 > 0.3:
                g.px(sx, sy)
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        for x in range(-40, 168, 10):
            g.d.line((x, FLOOR + 1, x - 6, 63), fill=1)
        pix.checker(g, (0, FLOOR + 2, 128, 64), 0.25)
        # 灯
        pix.blit(g, LAMP, 2, FLOOR - 9)
        if on or e3 > 2.4:
            pix.blit(g, pix.anim(FLAME, t, 5), 4, FLOOR - 13, outline=False)
        # 简
        open_k = 1.0 if on else span(e3, 0.4, 2.2)
        open_k *= 1 - close
        tt = t if on else 0.0
        cur, row, slide = self.slips(g, tt, open_k)
        right = lerp(ROLL_L + 4, 122, open_k)
        self.rolls(g, tt, slide + (1 - open_k) * 3, right)
        if open_k < 1:   # 卷起 / 展开时把右卷外面的简盖掉
            g.d.rectangle((right + 7, TOP - 3, 127, BOT + 3), fill=0)
        # 案
        g.d.rectangle((ROLL_L - 6, BOT + 2, 126, BOT + 3), fill=1)
        g.d.line((ROLL_L - 5, BOT + 3, 125, BOT + 3), fill=0)
        for x in (ROLL_L - 4, 122):
            g.d.rectangle((x, BOT + 4, x + 1, FLOOR - 1), fill=1)
        # 蠹鱼
        wk, wn = win(t, WORM, 10.0, 20.0) if on else (None, -1)
        ring = None
        if wk is not None and open_k >= 1:
            j, r = self.worm_target(wn)
            p = cur - j
            x = X0 + (p + slide) * PITCH + 4
            ty = ROW_Y[r] + 4
            third = wn % 3 == 2
            if wk < 3.0:                          # 从简底爬上来
                y = lerp(BOT + 2, ty + 6, ease_out(span(wk, 0, 3.0)))
                pix.blit(g, WORM_SPR[int(t * 6) % 2], x, y)
            elif wk < 4.5:                        # 啃
                y = ty + 5 - (int(t * 8) % 2)
                g.d.ellipse((x - 1, ty - 1, x + 5, ty + 4), fill=0)
                pix.blit(g, WORM_SPR[0], x, y)
                if int(t * 8) % 2 == 0:            # 碎屑
                    g.px(x - 1, ty + 5), g.px(x + 6, ty + 4)
            elif not third:                       # 吃饱了爬下去
                y = lerp(ty + 6, BOT + 4, span(wk, 4.5, 7.5))
                if wk < 7.5:
                    pix.blit(g, WORM_SPR[int(t * 6) % 2].flipv(), x, y)
            else:                                 # 第三回：卷成圆环“脉望”，发光飘出窗去
                q = span(wk, 5.0, 9.0)
                rx = lerp(x + 2, 12, ease_in_out(q))
                ry = lerp(ty + 2, -6, ease_in_out(q)) + math.sin(wk * 5) * 1.5
                ring = (rx, ry)
                g.d.ellipse((rx - 3, ry - 3, rx + 3, ry + 3), outline=1)
                g.d.ellipse((rx - 1, ry - 1, rx + 1, ry + 1), outline=0)
                if int(t * 8) % 2:
                    for a in range(0, 360, 45):
                        g.px(rx + math.cos(math.radians(a + t * 90)) * 5, ry + math.sin(math.radians(a + t * 90)) * 5)
                if wk > 8.4:                      # 星使立降
                    s = 1 + int(t * 8) % 2
                    g.d.line((19 - s, 7, 19 + s, 7), fill=1), g.d.line((19, 7 - s, 19, 7 + s), fill=1)
        # 小道士：一手扶左卷，读一个字点一下头、张一下嘴
        face = "normal"
        reading = on and slide == 0
        if reading and (t % (SLIP - SLIDE) / ((SLIP - SLIDE) / 3)) % 1 < 0.35:
            face = "wow"
        if wk is not None and 5.0 < wk < 9.5 and wn % 3 == 2:
            face = "wow"
        spr, at = put_arm(ROLL_L - 2 - (DX + 2), 3 + int(round(math.sin(slide * math.pi) * 2)), "fist")
        pop = ease_out_back(span(e3, 0.0, 0.5)) if not on else 1.0
        nod = 1 if reading and (t * 3 / (SLIP - SLIDE)) % 1 < 0.25 else 0
        figure(g, DX, FLOOR + (1 - pop) * 10, t, legs="sit", arm=spr, arm_at=at, face=face, dy=nod)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 字最后写
        if open_k >= 1:
            self.near_text(g, tt, cur, row, slide)
        if ring and wk > 6.0:
            label(g, 64, 1, "脉望", align="center")
        return cur, row, slide, ring

    def mx(self, g: Gfx, t: float, cur: int, row: int, slide: float, ring):
        if ring:
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - 2.6) < 0.7:
                        g.mx[y, x] = True
            return
        off = int(slide * 2)
        for c in range(0, 8, 2):
            x = c + off
            if 0 <= x < 8:
                g.mx[:, x] = True
        x = 1 + off
        if x < 8:
            g.mx[row * 2 + 1, x] = int(t * 6) % 2 == 0
            g.mx[row * 2 + 2, x] = True

    def enter(self, g: Gfx, t: float):
        self.scene(g, t, min(t / self.T["enter"], 0.999))
        n = int(span(t, 0.4, 2.2) * 4.99)
        for c in range(n):
            g.mx[:, c * 2] = True

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.mx(g, t, *self.scene(g, t))

    def exit(self, g: Gfx, t: float):
        tt = self.ht + t
        q = t / self.T["exit"]
        out = self.scene(g, tt, close=span(q, 0, 0.6))
        self.mx(g, tt, *out)
        iris(g, span(q, 0.4, 1.0), DX + 8, 34)
