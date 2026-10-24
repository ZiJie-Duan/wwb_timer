"""庄周梦蝶：大树下，小道士倚着树干坐着睡着了，梦里一只蝴蝶翩翩飞。

依据：《庄子·齐物论》：“昔者庄周梦为胡蝶，栩栩然胡蝶也，自喻适志与！不知周也。俄然觉，则蘧蘧然周也。
不知周之梦为胡蝶与，胡蝶之梦为周与？周与胡蝶，则必有分矣。此之谓物化。”

入场：小道士倚树坐着，头一点、惊起、再一点就睡过去；头顶冒出一串小泡，蝴蝶从泡里飞出来。
持续：大树（团团的树冠、树皮纹、树根）下倚树而眠，随呼吸点头；蝴蝶沿缓慢的曲线翩翩飞（三帧扇翅），
      一条“梦线”（流动的虚线）从他头顶连到蝴蝶；草地上三朵小花随风摇；树叶偶尔飘落。
      小事件（每 180 秒一轮）：蝴蝶落到花上歇脚、翅膀慢慢开合，“自喻适志与”（70s）；“栩栩然胡蝶也”（97s）；
      物化（150s）：蝴蝶落到他鼻尖 → 一闪 → 黑白翻转：一只大蝴蝶趴在他的位置打鼾，小小的道士扇着宽袖在飞，
      “胡蝶之梦为周与” → 再一闪回来，蝴蝶从鼻尖飞走。
退场：蝴蝶飞回头顶的梦泡里，小道士睁眼“！”（蘧蘧然周也），画面收拢。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x1_common import bang, bubble, cached, ev, iris, plate, zzz

FLOOR = 58
MAN_X = 30
EV = 180.0
FLOWERS = [(72, 50), (95, 47), (117, 51)]   # 花头位置
NOSE = (MAN_X + 6, FLOOR - 19)
HEAD_TOP = (MAN_X, FLOOR - 33)

FLY = pix.frames("""
  #   #
##.# #.##
#..###..#
#########
 ##.#.##
  ## ##
---
  #   #
 #.# #.#
 #..#..#
  #####
  ##.##
   # #
---
   # #
   ###
   ###
   ###
   ###
    #
""")
"""蝴蝶（正面）：张开 / 半合 / 合起（侧边）三帧，翅上暗斑"""

FLOWER = pix.frames("""
 # #
#.#.#
 ###
#.#.#
 # #
---
 ###
##.##
#.#.#
##.##
 ###
""")

LEAF = pix.frames("""
 ##
###
#
---
#
##
 ##
""")


def _tree():
    """大树 56×68：团团的树冠（几团叶簇，白边暗心，簇里叶子的亮笔触），粗树干带树皮纹、树根抓地"""
    p = Part(56, 68)
    blobs = [(0, 2, 22, 22), (14, 0, 38, 18), (30, 4, 54, 24), (6, 12, 30, 30), (24, 12, 48, 30)]
    for b in blobs:
        p.shape("ellipse", b, fill=0)
    for b in blobs:
        p.d.arc(b, 150, 390, fill=1)
    for b in blobs:                                    # 盖掉内部的弧，只留外轮廓
        x0, y0, x1, y1 = b
        p.d.ellipse((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=0)
    for b in blobs:
        p.d.arc(b, 160, 380, fill=1)
    m = Part(56, 68)
    for b in blobs:
        m.shape("ellipse", b, fill=1)
    import numpy as np
    mk = np.array(m.on, bool)
    on = np.array(p.on, bool)
    inner = mk.copy()
    inner[1:, :] &= mk[:-1, :]
    inner[:-1, :] &= mk[1:, :]
    inner[:, 1:] &= mk[:, :-1]
    inner[:, :-1] &= mk[:, 1:]
    on[:] = mk & ~inner                                 # 外轮廓
    for i in range(46):                                 # 叶子的亮笔触（小“ν”形）
        x, y = int(rand(i, 71) * 50) + 3, int(rand(i, 72) * 24) + 3
        if mk[y, x] and inner[y, x] and y < 27:
            on[y, x] = True
            if x + 1 < 56:
                on[y - 1, x + 1] = True
            if i % 3 == 0 and x > 0:
                on[y - 1, x - 1] = True
    from PIL import Image, ImageDraw
    p.on = Image.fromarray(on)
    p.d = ImageDraw.Draw(p.on)
    p.dither([(4, 22), (46, 22), (40, 29), (10, 29)], 0.25, 1)  # 树冠下沿的阴影里透一点光
    # 树干
    p.shape("polygon", [(11, 67), (15, 62), (16, 34), (14, 24), (19, 29), (25, 23), (24, 34), (24, 62), (29, 67)],
            fill=1)
    p.d.line((12, 67, 15, 64), fill=0), p.d.line((28, 67, 25, 64), fill=0)   # 树根
    p.d.line((19, 36, 19, 46), fill=0), p.d.line((21, 50, 21, 58), fill=0), p.d.line((21, 31, 22, 38), fill=0)
    p.d.line((18, 54, 18, 60), fill=0)
    p.dither([(22, 30), (24, 30), (24, 63), (22, 63)], 0.5, 0)
    p.d.ellipse((17, 41, 19, 44), outline=0)            # 树疤
    return p.sprite()


BIG_FLY = pix.frames("""
     #       #
      #     #
 ###   #   #   ###
#####.  ###  .#####
##..###.###.###..##
##..####.#.####..##
 ########.#.#######
  ######.###.######
   ####.#####.####
    ###.#.#.#.###
    ##.#  #  #.##
     ##       ##
---
     #       #
      #     #
       #   #
 ####.  ###  .####
##..###.###.###..##
##..####.#.####..##
 ########.#.#######
  ######.###.######
   ####.#####.####
    ###.#.#.#.###
    ##.#  #  #.##
     ##       ##
""")
"""物化时的大蝴蝶 19×12：上翅大、下翅小，翅上圆斑，触角卷起；两帧（翅膀随鼾声微微起伏）"""


MINI = pix.frames("""
   #
  ###
 #...#
 #.#.#
 #####
##.#.##
#.###.#
  ###
  # #
---
   #
  ###
 #...#
 #.#.#
 #####
 #.#.#
##.#.##
  ###
  # #
""")
"""物化时飞着的小小道士：圆头发髻、宽袖一扇一扇"""


def fly_pos(t: float):
    """蝴蝶的航线：慢慢的利萨如曲线，上下还有扑腾的小起伏"""
    x = 88 + math.sin(t * 0.23) * 28 + math.sin(t * 0.61) * 6
    y = 24 + math.sin(t * 0.37 + 1.0) * 12 + math.sin(t * 5.0) * 1.2
    return x, y


@register
class ButterflyRest(Rest):
    id = "x1.butterfly"
    name = "庄周梦蝶"
    desc = "大树下小道士倚树而眠，一条梦线连着翩翩飞的蝴蝶；蝴蝶歇在花上、落上鼻尖，一闪之间人蝶互换（物化）"
    T = {"enter": 3.2, "exit": 1.3}

    def setup(self):
        self.ph = self.rng.random() * 50

    def ground(self, g: Gfx, t: float, inv: bool = False):
        pix.blit(g, cached("tree", _tree), -4, FLOOR - 67, outline=False)
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        pix.checker(g, (0, FLOOR + 2, 128, 64), 0.125)
        for i, (x, y) in enumerate(FLOWERS):    # 花：茎随风弯、花头两帧
            sway = round(math.sin(t * 0.9 + i * 1.7) * 1.2)
            g.d.line((x, FLOOR, x + sway // 2, (FLOOR + y) // 2), fill=1)
            g.d.line((x + sway // 2, (FLOOR + y) // 2, x + sway, y + 2), fill=1)
            g.px(x - 1, FLOOR - 3), g.px(x - 2, FLOOR - 4)   # 叶
            pix.blit(g, FLOWER[i % 2], x + sway - 2, y - 2)
        for x in (52, 60, 82, 104, 124):
            g.px(x, FLOOR - 1), g.px(x + 1, FLOOR - 2), g.px(x + 2, FLOOR - 1)
        k = (t * 0.07 + 0.3) % 1                 # 落叶
        if k < 0.5:
            q = k / 0.5
            pix.blit(g, LEAF[int(t * 2) % 2], 30 + q * 24 + math.sin(t * 2) * 4, 20 + q * 36, outline=False)

    def man(self, g: Gfx, t: float, face: str = "sleep", pose: str = "sleep"):
        return daoshi(g, MAN_X, FLOOR, pose, t, face=face)

    def dream_line(self, g: Gfx, t: float, bx: float, by: float):
        """从头顶冒出的一串小泡，再一条流动的虚线连到蝴蝶"""
        hx, hy = HEAD_TOP
        for i, r in enumerate((1, 1, 2)):
            x, y = hx + 6 + i * 4, hy + 2 - i * 4 + math.sin(t * 2 + i) * 0.6
            g.d.ellipse((x - r, y - r, x + r, y + r), outline=1, fill=0)
        sx, sy = hx + 15, hy - 11
        cx, cy = (sx + bx) / 2, min(sy, by) - 10
        pts = []
        for j in range(17):
            q = j / 16
            pts.append(((1 - q) ** 2 * sx + 2 * (1 - q) * q * cx + q * q * bx,
                        (1 - q) ** 2 * sy + 2 * (1 - q) * q * cy + q * q * by + 3))
        ph = int(t * 8)
        for j in range(len(pts) - 1):
            pix.dotted(g, *pts[j], *pts[j + 1], 3, ph + j)

    def butterfly_state(self, t: float):
        """蝴蝶的位置与扇翅帧（只依赖 t）：平时飞；70s 落在花上；150s 落在鼻尖"""
        bx, by = fly_pos(t + self.ph)
        rest = ev(t, EV, 70.0, 22.0)
        nose = ev(t, EV, 146.0, 20.0)
        fr = [0, 1, 2, 1][int(t * 8) % 4]
        if rest is not None:
            fx, fy = FLOWERS[1][0], FLOWERS[1][1] - 6
            q = ease_in_out(span(rest, 0, 3)) * (1 - ease_in_out(span(rest, 19, 22)))
            bx, by = lerp(bx, fx, q), lerp(by, fy, q)
            if q > 0.98:
                fr = [0, 0, 1, 2, 2, 1][int(t * 2) % 6]   # 歇着慢慢开合
        if nose is not None:
            fx, fy = NOSE[0] + 4, NOSE[1] - 4
            q = ease_in_out(span(nose, 0, 4)) * (1 - ease_in_out(span(nose, 17, 20)))
            bx, by = lerp(bx, fx, q), lerp(by, fy, q)
            if q > 0.98:
                fr = [0, 1, 2, 1][int(t * 3) % 4]
        return bx, by, fr, rest, nose

    def hold(self, g: Gfx, t: float):
        bx, by, fr, rest, nose = self.butterfly_state(t)
        swap = nose is not None and 5.0 <= nose < 15.0
        if swap:
            self.dream(g, t, nose)
            return
        self.ground(g, t)
        self.man(g, t)
        if nose is None or nose < 4.0 or nose > 17.0:
            self.dream_line(g, t, bx, by)
        pix.blit(g, FLY[fr], bx - 4, by - 3)
        if nose is not None and 4.6 < nose < 5.0 or nose is not None and 15.0 <= nose < 15.4:
            pix.flash(g)
        if nose is None or nose > 15.0:
            zzz(g, MAN_X + 11, FLOOR - 18, t, n=2, period=3.4, dx=14, dy=-5, on=0.9) if rest is None else None
        if rest is not None and 3.0 < rest < 19.0:
            plate(g, 125, 3, "自喻适志与", k=span(rest, 3.0, 3.4), align="right")
        w = ev(t, EV, 97.0, 8.0)
        if w is not None and (rest is None or rest >= 19.0 or rest < 3.0):
            plate(g, 125, 3, "栩栩然胡蝶也", k=span(w, 0, 0.4), align="right")
        self.matrix(g, t, fr, False)

    def dream(self, g: Gfx, t: float, nose: float):
        """物化：黑白翻转——大蝴蝶趴在他的位置打鼾，小小的道士扇着袖子在飞"""
        self.ground(g, t)
        breath = int((t / 3.0) % 1 < 0.5)
        pix.blit(g, BIG_FLY[breath], MAN_X - 9, FLOOR - 13)
        zzz(g, MAN_X + 10, FLOOR - 16, t, n=2, period=3.0, dx=8, dy=-10)
        mx, my = fly_pos(t * 1.4 + self.ph)
        pix.blit(g, MINI[int(t * 6) % 2], mx - 3, my - 4)
        g.invert()
        plate(g, 64, 3, "胡蝶之梦为周与", k=span(nose, 5.6, 6.0), align="center")
        self.matrix(g, t, int(t * 6) % 3, True)

    def matrix(self, g: Gfx, t: float, fr: int, inv: bool):
        rows = {0: [0x00, 0x24, 0xDB, 0xFF, 0x7E, 0x5A, 0x66, 0x00], 1: [0x00, 0x24, 0x5A, 0x7E, 0x3C, 0x3C, 0x24, 0x00],
                2: [0x00, 0x24, 0x18, 0x18, 0x18, 0x18, 0x00, 0x00]}[fr]
        g.mx_rows(rows)
        if inv:
            g.mx[:] = ~g.mx

    def enter(self, g: Gfx, t: float):
        """倚树坐着：头一点 → 惊起 → 再一点就睡着；头顶冒泡，蝴蝶从泡里飞出来"""
        self.ground(g, t)
        if t < 0.7 or 1.0 <= t < 1.4:
            self.man(g, t, face="normal", pose="sit")
        elif t < 1.0:
            self.man(g, t, pose="sleep")
        else:
            self.man(g, t)
        if 0.7 <= t < 1.0:
            pass
        if 1.0 <= t < 1.4:
            bang(g, MAN_X + 10, FLOOR - 46)
        bx, by, fr, _, _ = self.butterfly_state(0.0)
        q = span(t, 1.8, 3.2)
        if t > 1.8:
            hx, hy = HEAD_TOP
            r = min(1.0, q * 3) * 5
            ox, oy = hx + 14, hy - 12
            if q < 0.35:
                bubble(g, ox, oy, r)
            px, py = lerp(ox, bx, ease_out(q)), lerp(oy, by, ease_out(q))
            if q > 0.3:
                self.dream_line(g, t, px, py)
                pix.blit(g, FLY[[0, 1, 2, 1][int(t * 8) % 4]], px - 4, py - 3)
        self.matrix(g, t, [0, 1, 2, 1][int(t * 8) % 4] if t > 2.3 else 2, False)
        iris(g, MAN_X + 2, FLOOR - 22, lerp(5, 150, ease_out(span(t, 0, 1.0))))

    def exit(self, g: Gfx, t: float):
        """蝴蝶飞回梦里，小道士睁眼“！”"""
        h0 = self.hold_t
        bx, by, fr, _, _ = self.butterfly_state(h0)
        self.ground(g, h0 + t)
        self.man(g, h0 + t, face="wow" if t > 0.45 else "sleep", pose="sit" if t > 0.45 else "sleep")
        q = span(t, 0.0, 0.45)
        hx, hy = HEAD_TOP
        if q < 1:
            px, py = lerp(bx, hx + 4, ease_in_out(q)), lerp(by, hy, ease_in_out(q))
            pix.blit(g, FLY[[0, 1, 2, 1][int(t * 12) % 4]], px - 4, py - 3)
        if t > 0.45:
            bang(g, MAN_X + 10, FLOOR - 46)
        self.matrix(g, t, 2, False)
        iris(g, MAN_X + 2, FLOOR - 22, lerp(140, 0, ease_in_out(span(t, 0.55, self.T["exit"] - 0.05))))
