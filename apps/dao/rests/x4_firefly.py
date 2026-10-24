"""腐草为萤：夏夜草边，小道士盘坐看萤火；一只大萤火虫在眼前扑翅飞，尾灯一明一灭。

依据：《礼记·月令》季夏之月“腐草为萤”（七十二候之一，古人以为萤由腐草化生）；《易·说卦》“离为火”。
入场：草叶从地面长起，萤火从腐草堆里一只只亮起、飞上来，右边竖排“腐草为萤”。
持续：弯月、几颗星、远山一线；草叶随风摆；十二只小萤火各自游荡、呼吸般明灭（最亮时带十字光芒）；
      大萤火虫（扑翅三帧、尾灯明灭带光晕）在画面中间慢慢绕飞；小道士盘坐，呼吸眨眼，萤火飞近时笑一下。
      每 60 秒一轮三个彩蛋：
        2 秒起  一只萤火落到草尖上，草被压弯，它在那儿慢慢闪，再飞走；
        12 秒起 小道士举起手指，大萤火虫飞过来停在指尖（他先“哇”再笑），扑两下翅，尾灯闪几回，飞走；
        40 秒起 小萤火聚成 ☲ 离卦三爻，同一爻之间连出光点，下面写“离为火”，定住后散开。
收场：萤火一齐往上飞散、熄灭。
点阵：几点萤火跟着画面游动，底行是草；萤火停在指尖时是一只萤火虫（尾灯闪）；聚卦时是离卦。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, span
from ..engine.chars import daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x4_common import ev, mx_art, sparkle, vlabel, label

FLOOR = 61
DAO_X = 20
N = 12
HEAP_X = 100            # 腐草堆
PERIOD = 60.0
LAND = (2.0, 7.0)       # 落草尖
FINGER = (12.0, 12.0)   # 落指尖
LI = (40.0, 16.0)       # 聚成离卦
# ☲：上阳、中阴、下阳（每爻 4 只萤火）
LI_Y = (6, 13, 20)
LI_X = (78, 104)
LI_PTS = [(78, 6), (86, 6), (95, 6), (104, 6),
          (78, 13), (86, 13), (96, 13), (104, 13),
          (78, 20), (86, 20), (95, 20), (104, 20)]

# 大萤火虫（侧视，头朝右）：翅上扬 / 翅平 / 翅下扇；尾灯另画在左端
FF = pix.frames("""
    ###      #    #
   #   #      #  #
  #     #      ##
  #      #  ######
   #     # ########
    ##### ##.####.#
     #######..###.#
    ########.######
    #########.####
     .#.#.#.#.###
      #.#.#.#.#
      #   #   #
---
              #    #
               #  #
                ##
            ######
 #######   ########
#       ## #.####.#
 ##############.###.#
    ########..######
    #########.####
     .#.#.#.#.###
      #.#.#.#.#
      #   #   #
---
              #    #
               #  #
                ##
            ######
           ########
     ##### #.####.#
    #######..###.#
    ########.######
    #########.####
     .#.#.#.#.###
      #.#.#.#.#
      #   #   #
""")
WING_SEQ = (0, 1, 2, 1)

MOON = pix.sprite("""
   ###
  ##.
 ##.
 ##.
 ##.
 ###.
  ####
   ###
""")

LANTERN_ON = pix.sprite("""
 ##
####
 ##
""")
LANTERN_OFF = pix.sprite("""
 ..
#..#
 ..
""")

# 大萤火虫（侧视，头朝右）：翅上扬 / 翅平 / 翅下扇；尾灯另画在左端
FF = pix.frames("""
    ###      #    #
   #   #      #  #
  #     #      ##
  #      #  ######
   #     # ########
    ##### ##.####.#
     #######..###.#
    ########.######
    #########.####
     .#.#.#.#.###
      #.#.#.#.#
      #   #   #
---
              #    #
               #  #
                ##
            ######
 #######   ########
#       ## #.####.#
 ##############.###.#
    ########..######
    #########.####
     .#.#.#.#.###
      #.#.#.#.#
      #   #   #
---
              #    #
               #  #
                ##
            ######
           ########
     ##### #.####.#
    #######..###.#
    ########.######
    #########.####
     .#.#.#.#.###
      #.#.#.#.#
      #   #   #
""")
WING_SEQ = (0, 1, 2, 1)

MOON = pix.sprite("""
   ###
  ##.
 ##.
 ##.
 ##.
 ###.
  ####
   ###
""")

LANTERN_ON = pix.sprite("""
 ##
###
 ##
""")
LANTERN_OFF = pix.sprite("""
 #.
#..
 #.
""")

# 腐草堆：一团枯草（网点）+ 几根折断的草茎
HEAP = pix.sprite("""
      #    #
   #   #  #   #
    #  ## # ##
  #  #.#.##.#   #
   ##.#.#.#.#.##
 ##.#.#.#.#.#.#.##
#.#.#.#.#.#.#.#.#.#
""")

MX_LI = ["########", "", "", "###..###", "", "", "########", ""]

def _ff_mx(g: Gfx, on: bool):
    rows = ["  #   # ", "   # #  ", "  ####  ", " #.##.# ", "  ####  ", "  ####  "]
    mx_art(g, rows)
    if on:
        mx_art(g, ["  ####  ", "   ##   "], 0, 6)
    else:
        mx_art(g, ["   ##   "], 0, 6)


@register
class Firefly(Rest):
    id = "x4.firefly"
    name = "腐草为萤"
    desc = "夏夜草边，小道士盘坐看萤；大萤火虫扑翅绕飞、落在他指尖，小萤火不时聚成离卦"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        r = self.rng
        self.ph = [r.random() * 10 for _ in range(N)]
        self.rate = [0.35 + r.random() * 0.35 for _ in range(N)]
        self.home = [(36 + r.random() * 84, 8 + r.random() * 34) for _ in range(N)]
        self.stars = [(int(r.random() * 128), int(r.random() * 24), r.random() * 5) for _ in range(9)]
        self.blades = []
        x = 0
        while x < 128:
            near = abs(x - DAO_X) < 13
            hmax = 5 if near else (7 if x > 106 else 13)
            self.blades.append((x, 3 + r.random() * (hmax - 3), (r.random() - 0.5) * 6, r.random() * 6))
            x += 3 + int(r.random() * 4)
        self.seed2 = self.seed * 7 + 3

    # ------------------------------------------------------------ 小件

    def sky(self, g: Gfx, t: float):
        pix.blit(g, MOON, 6, 3)
        for i, (x, y, p) in enumerate(self.stars):
            k = (t * 0.4 + p) % 5
            if k < 4.6:
                g.px(x, y)
            if 2.0 < k < 2.3:
                sparkle(g, x, y, 1)
        # 远山一线
        pts = []
        for x in range(0, 129, 4):
            y = 44 + 4 * math.sin(x * 0.05 + 1.3) + 2 * math.sin(x * 0.13)
            pts.append((x, y))
        g.d.line(pts, fill=1)
        for x in range(0, 128, 8):
            y = 44 + 4 * math.sin(x * 0.05 + 1.3) + 2 * math.sin(x * 0.13)
            g.px(x + 2, y + 3)

    def blade_tip(self, i: int, t: float, grow: float = 1.0, press: float = 0.0):
        x, h, lean, ph = self.blades[i]
        sway = math.sin(t * 1.3 + ph) * 1.2 + math.sin(t * 0.47 + ph * 2) * 0.8
        hh = h * grow
        return x + (lean + sway) * grow + press * 2, FLOOR + 2 - hh + press * 3

    def grass(self, g: Gfx, t: float, grow: float = 1.0, press_i: int = -1, press: float = 0.0):
        g.d.line((0, 63, 127, 63), fill=1)
        pix.blit(g, HEAP, HEAP_X - 9, 57)
        for i, (x, h, lean, ph) in enumerate(self.blades):
            tx, ty = self.blade_tip(i, t, grow, press if i == press_i else 0.0)
            mx, my = x + (tx - x) * 0.35, 63 - (63 - ty) * 0.55
            g.d.line([(x, 63), (mx, my), (tx, ty)], fill=1)
            if h > 6:  # 长叶片：下半截两像素宽
                g.d.line([(x + 1, 63), (mx + 1, my + 1)], fill=1)

    def small_pos(self, i: int, t: float):
        hx, hy = self.home[i]
        s = self.seed2 + i * 13
        x = hx + (noise(t * 0.12 + i * 3.1, s) - 0.5) * 34
        y = hy + (noise(t * 0.15 + i * 1.7, s + 1) - 0.5) * 18 + math.sin(t * 2 + i) * 1
        return clamp(x, 32, 124), clamp(y, 4, 50)

    def small_lit(self, i: int, t: float) -> float:
        """0 灭，1 亮，2 最亮"""
        k = (t * self.rate[i] + self.ph[i]) % 1
        if k < 0.12 or 0.42 < k < 0.48:
            return 2
        if k < 0.5:
            return 1
        return 0

    def draw_small(self, g: Gfx, x: float, y: float, lv: float):
        if lv <= 0:
            return
        if lv >= 2:
            sparkle(g, x, y, 2)
        else:
            sparkle(g, x, y, 1) if (x * 7 + y) % 3 == 0 else g.px(x, y)

    def hero_path(self, t: float):
        x = 80 + 24 * math.sin(t * 0.19) + 6 * math.sin(t * 0.53)
        y = 30 + 9 * math.sin(t * 0.31 + 1) + math.sin(t * 3.1) * 1.2
        vx = 24 * 0.19 * math.cos(t * 0.19) + 6 * 0.53 * math.cos(t * 0.53)
        return x, y, vx < 0

    def hero(self, g: Gfx, x: float, y: float, t: float, flip: bool, flap: bool = True, glow: float | None = None):
        """(x, y) = 身体中心；flip=True 朝左"""
        fr = FF[WING_SEQ[int(t * 16) % 4]] if flap else FF[2]
        sx, sy = int(round(x - 10)), int(round(y - 7))
        pix.blit(g, fr, sx, sy, flip=flip)
        on = glow if glow is not None else ((t % 2.4) < 1.5)
        lx = sx if not flip else sx + fr.w - 4
        ly = sy + 7
        pix.blit(g, LANTERN_ON if on else LANTERN_OFF, lx, ly, flip=flip)
        if on:  # 尾灯光芒：十字光线一伸一缩
            cx, cy = lx + 1.5 + (-2 if not flip else 2), ly + 1
            r = 2 + int(t * 4) % 2
            for i in range(1, r + 1):
                g.px(cx - i if not flip else cx + i, cy)
                g.px(cx, cy - 2 - i)
                g.px(cx, cy + 2 + i)
        return on

    # ------------------------------------------------------------ 主画面

    def scene(self, g: Gfx, t: float, grow: float = 1.0, rise: float = 1.0, scatter: float = 0.0):
        """grow：草长出（入场）；rise：萤火从草堆飞出的进度；scatter：收场往上飞散"""
        self.sky(g, t)
        cyc = t % PERIOD
        land = ev(cyc, PERIOD, *LAND)
        fing = ev(cyc, PERIOD, *FINGER)
        li = ev(cyc, PERIOD, *LI)
        # 草（落草尖时压弯一根）
        press_i, press = -1, 0.0
        land_i = int(t // PERIOD) % N
        bi = 6 + int(t // PERIOD) * 5 % max(len(self.blades) - 20, 1)
        if land and scatter == 0:
            k = land[1]
            press_i = bi
            press = span(k, 1.4, 2.0) * (1 - span(k, 5.6, 6.2))
        self.grass(g, t, grow, press_i, press)
        # 小道士
        hand = None
        near = False
        if fing:
            k = fing[1]
            up = 0.6 < k < 10.8
            face = "wow" if 1.0 < k < 3.0 else ("happy" if up else "normal")
            if up:
                hand = figure(g, DAO_X, FLOOR, t, legs="sit", arm="raise", face=face)["hand"]
            else:
                daoshi(g, DAO_X, FLOOR, "sit", t)
        # 小萤火
        pts = []
        for i in range(N):
            x, y = self.small_pos(i, t)
            lv = self.small_lit(i, t)
            if rise < 1:  # 从草堆飞出
                q = clamp(rise * 1.6 - i * 0.05)
                x = lerp(HEAP_X + (i % 5 - 2) * 3, x, ease_out(q))
                y = lerp(58, y, ease_out(q))
                lv = lv if q > 0.05 else 0
            if li and scatter == 0:
                k = li[1]
                q = ease_in_out(span(k, 0, 3.0)) * (1 - ease_in_out(span(k, 12.5, 15.5)))
                tx, ty = LI_PTS[i]
                x, y = lerp(x, tx, q), lerp(y, ty, q)
                if q > 0.95:
                    lv = 2 if (k * 2 + i * 0.15) % 1.6 < 0.25 else 1
            if land and scatter == 0 and i == land_i:
                k = land[1]
                tx, ty = self.blade_tip(bi, t, 1.0, press)
                q = ease_in_out(span(k, 0, 1.5)) * (1 - ease_in_out(span(k, 5.5, 7.0)))
                x, y = lerp(x, tx, q), lerp(y, ty - 1, q)
                if q > 0.9:
                    lv = 2 if k % 1.2 < 0.15 else (1 if k % 1.2 < 0.7 else 0)
            if scatter:
                y -= ease_in(scatter) * (50 + i * 3)
                x += (i % 3 - 1) * scatter * 8
                lv = lv if scatter < 0.4 + (i % 5) * 0.12 else 0
            pts.append((x, y, lv))
            self.draw_small(g, x, y, lv)
            if abs(x - DAO_X - 4) < 16 and 20 < y < 40 and lv:
                near = True
        if li and scatter == 0:  # 同一爻的萤火之间连成光条：☲
            k = li[1]
            grow_k = span(k, 3.0, 4.6) * (1 - span(k, 12.0, 13.0))
            if grow_k > 0:
                x0, x1 = LI_X
                for row, segs in ((0, [(x0, x1)]), (1, [(x0, 88), (94, x1)]), (2, [(x0, x1)])):
                    y = LI_Y[row]
                    for a, b in segs:
                        e = a + (b - a) * grow_k
                        g.d.rectangle((a, y, e, y + 1), fill=1)
                    gx = x0 + int((k * 14 + row * 9) % (x1 - x0 + 10))  # 一道暗光滑过
                    g.d.line((gx, y, gx, y + 1), fill=0)
        if not fing or not (0.6 < fing[1] < 10.8):
            if not fing:
                daoshi(g, DAO_X, FLOOR, "sit", t, face="happy" if near else "normal")
        # 大萤火虫
        hx, hy, flip = self.hero_path(t)
        flap, glow = True, None
        if li and scatter == 0:  # 聚卦时大萤火虫让到左边飞
            q = ease_in_out(span(li[1], 0, 2.5)) * (1 - ease_in_out(span(li[1], 13.0, 15.5)))
            hx = lerp(hx, 54 + 6 * math.sin(t * 0.7), q)
            hy = lerp(hy, 22 + 4 * math.sin(t * 0.9), q)
        if fing:
            k = fing[1]
            if hand:
                ax, ay = hand[0] + 5, hand[1] - 5
                q1 = ease_in_out(span(k, 1.0, 3.2))
                q2 = ease_in_out(span(k, 9.0, 11.0))
                if q2 > 0:
                    hx, hy = lerp(ax, hx, q2), lerp(ay, hy, q2) - math.sin(q2 * math.pi) * 6
                    flip = False
                else:
                    hx, hy = lerp(hx, ax, q1), lerp(hy, ay, q1) - math.sin(q1 * math.pi) * 8
                    flip = True
                    if q1 >= 1:
                        sit = k - 3.2
                        flap = (4.0 < sit < 4.6)        # 停着扑两下翅
                        glow = (sit % 1.3) < 0.75
            elif k >= 10.8:
                pass
        if scatter:
            hy -= ease_in(scatter) * 50
        if rise < 1:
            q = ease_out(clamp(rise * 1.3 - 0.3))
            hx, hy = lerp(HEAP_X - 4, hx, q), lerp(56, hy, q)
        lit = self.hero(g, hx, hy, t, flip, flap, glow)
        if fing and hand and 3.2 < fing[1] < 9.0 and int(t * 4) % 3 == 0:
            sparkle(g, hand[0] + 6, hand[1] - 10, 1)
        # 点阵
        g.mx[:] = False
        if fing and hand and 3.0 < fing[1] < 9.2:
            _ff_mx(g, lit)
        elif li and 2.5 < li[1] < 13.5:
            mx_art(g, MX_LI)
        else:
            for x, y, lv in pts[:6]:
                if lv:
                    g.mx_set(int((x - 32) / 96 * 8), int((y - 4) / 48 * 7))
            g.mx_set(int((hx - 32) / 96 * 8), int((hy - 4) / 48 * 7), lit)
            for c in range(8):
                if (c + int(t * 1.3)) % 3 != 0:
                    g.mx[7, c] = True
        # 文字（最后画）
        if li and 4.0 < li[1] < 12.0 and scatter == 0:
            label(g, 91, 27, "离为火", align="center")
        return pts

    def enter(self, g: Gfx, t: float):
        grow = ease_out(span(t, 0, 1.4))
        rise = span(t, 0.8, 3.0)
        self.scene(g, t, grow=grow, rise=rise)
        if t > 1.5:
            vlabel(g, 114, 4, "腐草为萤")

    def hold(self, g: Gfx, t: float):
        self.scene(g, t + self.T["enter"])
        if t < 9.0:
            vlabel(g, 114, 4, "腐草为萤")

    def exit(self, g: Gfx, t: float):
        self.scene(g, self.hold_t + self.T["enter"] + t, scatter=span(t, 0, 1.1))
