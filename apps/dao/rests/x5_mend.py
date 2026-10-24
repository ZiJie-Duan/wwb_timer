"""补衲（像素风）：夜里，窗格外一弯月，灯台上一盏油灯，光晕一圈圈；一只飞蛾绕着灯打转。
小道士盘坐蒲团，道袍搭在膝上，当中一块补丁。一大轮 40 秒：先把针举到灯前眯眼穿线——线头戳偏两次才穿进（一闪）；
然后一针一针：针扎下去、从下一针冒出来、拉着线划一道长弧再落回，补丁四周的针脚一针针多起来；
缝完低头咬断线头，双手把道袍举起来对着灯照一照（补丁边一闪），满意地眯眼一笑，放下，换一处再补。
彩蛋：约每 29 秒飞蛾一头扑向灯火，火苗猛地一跳，飞蛾晕乎乎地绕开。
左侧竖写“大成若缺”（《道德经》四十五章：大成若缺，其用不弊）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import Clock, cyc, event, fade_out, keys, scroll, worker

FLOOR = 56
TEXT_X = 3
DX = 46
LAMP = (84, 33)          # 灯芯
BIG = 40.0
NST = 13
ST0, ST = 6.0, 2.0       # 第一针开始、每针

FLAME = pix.frames("""
  #
 ###
 ###
#.#.#
 #.#
---
  #
  ##
 ###
 #.##
 #.#
---
 #
 ##
 ###
##.#
 #.#
""")
BIG_FLAME = pix.frames("""
   #
  ##
  ###
 ####
 ##.##
##..##
 #..#
---
  #
  ##
 ###
 ####
##.##
#..##
 #..#
""")

LAMPSTAND = Sprite("""
#.......#
 #######
   ###
    #
    #
    #
   #.#
    #
    #
    #
    #
   ###
 #######
#########
""")

MOTH = pix.frames("""
#.#
 #
---
.#.
###
""")

CUSHION = Sprite("""
  ##########
 #.#.#.#.#.##
##############
 ############
""")


def patch_points():
    """补丁一圈针脚的位置（相对补丁左上角，补丁 9×5）"""
    pts = []
    for x in range(0, 9, 2):
        pts.append((x, -1))
    for y in range(1, 5, 2):
        pts.append((9, y))
    for x in range(8, -1, -2):
        pts.append((x, 5))
    for y in range(3, 0, -2):
        pts.append((-1, y))
    return pts[:NST]


PTS = patch_points()


@register
class Mend(Rest):
    id = "x5.mend"
    name = "补衲"
    desc = "夜里油灯下盘坐补衲衣：眯眼穿针、一针一针拉长线，咬断线头举起来对灯一照——大成若缺"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()

    # ------------------------------------------------ 屋里

    def room(self, g: Gfx, t: float, flare: float = 0.0, light: float = 1.0):
        # 窗：格子窗，窗外一弯月、两颗星
        wx0, wy0, wx1, wy1 = 100, 6, 124, 30
        g.d.rectangle((wx0, wy0, wx1, wy1), outline=1)
        g.d.ellipse((108, 10, 118, 20), fill=1)
        g.d.ellipse((111, 8, 121, 18), fill=0)
        for x, y in ((104, 24), (120, 25)):
            if int(t * 1.3 + x) % 4:
                g.px(x, y)
        for x in (108, 116):
            g.d.line((x, wy0, x, wy1), fill=1)
        g.d.line((wx0, 18, wx1, 18), fill=1)
        g.d.rectangle((wx0 - 2, wy1 + 1, wx1 + 2, wy1 + 2), fill=1)
        # 地面：一道线、几块砖
        g.d.line((19, FLOOR, 127, FLOOR), fill=1)
        for x in range(23, 128, 12):
            g.d.line((x, FLOOR + 1, x - 2, 63), fill=1)
        # 灯台与灯火、光晕
        lx, ly = LAMP
        pix.blit(g, LAMPSTAND, lx - 4, ly + 2)
        fr = pix.anim(BIG_FLAME if flare > 0 else FLAME, t, 7)
        pix.blit(g, fr, lx - fr.w // 2, ly - fr.h + 2, outline=False)
        if light > 0:
            r = 11 + math.sin(t * 2.3) * 1 + flare * 4
            for a in range(0, 360, 20):  # 光晕：一圈点，慢慢转
                rad = math.radians(a + t * 15)
                g.px(lx + math.cos(rad) * r, ly - 2 + math.sin(rad) * r * 0.9)
            if light > 0.5:
                r2 = r + 5
                for a in range(10, 360, 30):
                    rad = math.radians(a - t * 10)
                    g.px(lx + math.cos(rad) * r2, ly - 2 + math.sin(rad) * r2 * 0.9)

    def lap(self, g: Gfx, x: int, raise_k: float = 0.0, done: int = 0, flash: bool = False):
        """膝上的道袍：一块布从膝上垂到地，当中补丁 + 一圈针脚"""
        dy = -int(raise_k * 16)
        x0, y0 = x - 4 + int(raise_k * 8), FLOOR - 9 + dy
        bot = FLOOR - 1 + dy if raise_k else FLOOR - 1
        g.d.polygon([(x0, y0 + 1), (x0 + 5, y0), (x0 + 11, y0 + 1), (x0 + 17, y0), (x0 + 20, y0 + 1),
                     (x0 + 21, bot), (x0 - 2, bot)], fill=1)
        g.d.polygon([(x0 + 17, y0 + 1), (x0 + 23, y0 + 3), (x0 + 27, bot + 1), (x0 + 19, bot + 1)], fill=1)  # 垂下的袖子
        g.d.line((x0 + 20, bot - 1, x0 + 26, bot - 1), fill=0)      # 袖口镶边
        pix.checker(g, (x0 + 21, y0 + 4, x0 + 27, bot - 1), 0.5, fill=0)
        g.d.line((x0 + 1, y0 + 2, x0 + 4, bot - 1), fill=0)         # 交领
        g.d.line((x0 + 17, y0 + 2, x0 + 18, bot - 1), fill=0)       # 衣褶
        px, py = x0 + 7, y0 + 2
        g.d.rectangle((px, py, px + 8, py + 4), fill=0, outline=1)  # 补丁
        g.d.line((px + 2, py + 2, px + 6, py + 2), fill=1)
        for i in range(done):
            sx, sy = PTS[i]
            g.px(px + sx, py + sy, 0 if not flash else 1)
        if flash:
            g.d.rectangle((px - 1, py - 1, px + 9, py + 5), outline=1)
        return px, py

    # ------------------------------------------------ 主循环

    def frame(self, g: Gfx, t: float, text_k: float = 1.0):
        self.clock.tick(t)
        n, k = cyc(t, BIG)
        moth = event(t, 29.0, 4.0, 77)
        flare = 1.0 if moth and 1.2 < moth[1] < 2.0 else 0.0
        self.room(g, t, flare)
        pix.blit(g, CUSHION, DX - 7, FLOOR - 4)
        hand, face, head, needle, thread, done, raise_k = self.state(k)
        flash = 34.6 < k < 35.2
        px, py = 0, 0

        def tool(gg, h1, h2):
            nonlocal px, py
            px, py = self.lap(gg, DX + 6, raise_k, done, flash)
            if needle and h1:
                gg.d.line((h1[0], h1[1], h1[0] + 3, h1[1] - 3), fill=1)   # 针
            if thread and h1 and done < NST + 1:
                i = min(done, NST - 1)
                sx, sy = PTS[i if done < NST else NST - 1]
                tx, ty = px + sx, py + sy
                mx, my = (tx + h1[0]) / 2, min(ty, h1[1]) - 4
                pts = [(lerp(lerp(tx, mx, q), lerp(mx, h1[0], q), q), lerp(lerp(ty, my, q), lerp(my, h1[1], q), q))
                       for q in (i / 6 for i in range(7))]
                pix.dotted(gg, pts[0][0], pts[0][1], pts[3][0], pts[3][1], step=1)
                pix.dotted(gg, pts[3][0], pts[3][1], pts[6][0], pts[6][1], step=1)

        worker(g, DX, FLOOR, t, hand=hand, hand2=(hand[0] - 2, hand[1]) if raise_k > 0 else None, legs="sit",
               face=face, head=head, tool=tool, behind_head=False)
        if k < ST0:  # 穿针：线头凑近针眼，戳偏两下才进
            self.threading(g, k, hand)
        if moth:
            self.moth(g, moth[1], t)
        else:
            self.moth(g, None, t)
        self.matrix(g, t, k, done, raise_k)
        scroll(g, TEXT_X, "大成若缺", k=text_k, side="left")

    def state(self, k: float):
        """→ (手, 表情, 头, 拿针, 有线, 已缝针数, 举起)"""
        rest = (DX + 10, FLOOR - 12)
        if k < ST0:  # 举针到灯前
            hand = keys(k, [(0, rest), (0.8, (DX + 14, FLOOR - 24)), (5.2, (DX + 14, FLOOR - 24)), (6.0, rest)])
            return hand, ("sleep" if 1.0 < k < 5.0 else "normal"), "up", True, k > 4.6, 0, 0.0
        if k < ST0 + NST * ST:
            i = int((k - ST0) / ST)
            q = ((k - ST0) % ST) / ST
            sx, sy = PTS[i]
            tx, ty = DX + 2 + 7 + sx, FLOOR - 9 + 2 + sy
            if q < 0.3:   # 扎下去
                hand = keys(q, [(0, (tx + 2, ty - 5)), (0.3, (tx + 1, ty - 1))])
            elif q < 0.75:  # 拉线：一道长弧
                hand = keys(q, [(0.3, (tx + 1, ty - 1)), (0.55, (tx + 10, ty - 14)), (0.75, (tx + 13, ty - 10))],
                            ease=ease_out)
            else:
                nx, ny = PTS[min(i + 1, NST - 1)]
                hand = keys(q, [(0.75, (tx + 13, ty - 10)), (1.0, (DX + 2 + 7 + nx + 2, FLOOR - 9 + 2 + ny - 5))])
            return hand, "normal", "bow" if q < 0.3 else "up", True, True, i + (q > 0.3), 0.0
        k2 = k - (ST0 + NST * ST)
        if k2 < 2.0:  # 低头咬断线头
            return (DX + 7, FLOOR - 18), "normal", "bow" if 0.5 < k2 < 1.6 else "up", True, k2 < 1.0, NST, 0.0
        if k2 < 6.0:  # 举起来对着灯照
            r = span(k2, 2.0, 2.6) - span(k2, 5.4, 6.0)
            return (DX + 12 + int(r * 8), FLOOR - 12 - int(r * 16)), ("happy" if 3.0 < k2 < 5.4 else "normal"), "up", False, \
                False, NST, ease_in_out(r)
        return rest, "normal", "up", False, False, NST if k2 < 7.0 else 0, 0.0

    def threading(self, g: Gfx, k: float, hand):
        """针眼前一根线头：戳偏两次，第三次穿过（一闪）"""
        hx, hy = hand
        ex, ey = hx + 3, hy - 3
        if k < 1.0:
            return
        tries = [(1.2, 2.2, -2), (2.4, 3.4, 2), (3.6, 4.6, 0)]
        for a, b, off in tries:
            if a <= k < b:
                q = span(k, a, b)
                d = 6 * (1 - math.sin(q * math.pi))
                g.d.line((ex + 2 + d, ey + off * math.sin(q * math.pi), ex + 7 + d, ey + 1), fill=1)
                if off and 0.45 < q < 0.6:  # 戳偏了
                    g.px(ex + 1, ey + off - 1)
        if 4.6 <= k < 4.9:  # 穿进去了：一闪
            for dx, dy in ((0, -2), (0, 2), (-2, 0), (2, 0)):
                g.px(ex + dx, ey + dy)

    def moth(self, g: Gfx, q, t: float):
        lx, ly = LAMP
        if q is not None and q < 3.0:
            if q < 1.2:  # 一头扑向火
                a = t * 3
                r = lerp(14, 2, q / 1.2)
            else:  # 晕乎乎地绕开
                a = t * 7
                r = lerp(3, 14, span(q, 1.2, 3.0))
            x, y = lx + math.cos(a) * r, ly - 4 + math.sin(a) * r * 0.6
        else:
            a = t * 2.1
            x, y = lx + math.cos(a) * 14, ly - 6 + math.sin(a * 1.7) * 6
        pix.blit(g, pix.anim(MOTH, t, 10), x - 1, y - 1)

    def matrix(self, g: Gfx, t: float, k: float, done: int, raise_k: float):
        """点阵：补丁一圈针脚随针数一格格亮起，中间一上一下的针；举起来照时整块亮"""
        ring = [(x, 0) for x in range(1, 7)] + [(7, y) for y in range(1, 7)] + [(x, 7) for x in range(6, 0, -1)] + \
               [(0, y) for y in range(6, 0, -1)]
        for i in range(min(done * 2, len(ring))):
            if i % 2 == 0:
                g.mx_set(*ring[i])
        if raise_k > 0.3:
            for y in range(2, 6):
                for x in range(2, 6):
                    g.mx_set(x, y)
            g.mx_level = 3
            return
        ny = 2 + int(abs(math.sin(t * math.pi / ST)) * 3)
        g.mx_set(4, ny), g.mx_set(4, ny + 1)
        g.mx_set(3, 3), g.mx_set(3, 4)

    def enter(self, g: Gfx, t: float):
        """黑屋里一根火柴凑近油灯，灯亮，屋里渐渐亮起来"""
        self.clock.tick(t)
        lit = t > 1.4
        self.room(g, t, 0.0, light=span(t, 1.4, 2.6) if lit else 0)
        if not lit:  # 灯还没点：盖掉火苗
            lx, ly = LAMP
            g.d.rectangle((lx - 3, ly - 6, lx + 3, ly + 1), fill=0)
            g.px(lx, ly)
        pix.blit(g, CUSHION, DX - 7, FLOOR - 4)
        hand = keys(t, [(0, (DX + 10, FLOOR - 12)), (0.8, (LAMP[0] - 5, LAMP[1] + 1)), (1.6, (LAMP[0] - 5, LAMP[1] + 1)),
                        (2.4, (DX + 10, FLOOR - 12))])

        def tool(gg, h1, h2):
            self.lap(gg, DX + 6)
            if 0.4 < t < 1.8 and h1:
                gg.d.line((h1[0], h1[1], h1[0] + 4, h1[1] - 1), fill=1)
                if int(t * 12) % 2:
                    gg.px(h1[0] + 5, h1[1] - 2)
        worker(g, DX, FLOOR, t, hand=hand, legs="sit", tool=tool, face="happy" if t > 2.0 else "normal")
        if not lit:
            g.fade(0.35 + span(t, 0, 1.4) * 0.3)
        self.matrix(g, t, 0, 0, 0)
        scroll(g, TEXT_X, "大成若缺", k=span(t, 1.0, 2.8), side="left")

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.hold_t + t)
        fade_out(g, span(t, 0.1, self.T["exit"]))
