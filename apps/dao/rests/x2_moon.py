"""邀月：李白《月下独酌》（李白曾受道箓，自号“青莲居士”，与道士吴筠、元丹丘交游）。

“花间一壶酒，独酌无相亲。举杯邀明月，对影成三人……我歌月徘徊，我舞影零乱。”

入场：明月从右下升起，花枝从左上探进来，酒客在石上渐渐显形，月光把他的影子投在地上。
持续：每 12 秒一次：举杯向月（杯中映出一点月光）→ 仰头饮尽 → 放下；影子在地上跟着做同样的动作。
      右下角不时题一句诗。花瓣偶尔飘落，薄云慢慢掠过月面。
      每 48 秒一次彩蛋：他起身对月且歌且舞，月亮左右“徘徊”，地上的影子乱舞——“我歌月徘徊，我舞影零乱”。
退场：画面收拢成一个圆。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import cloud, typewriter
from ..engine.gfx import BAYER, Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import iris, win

MOON = (104, 15, 11)       # 月：中心、半径
FX, FY = 46, 45            # 酒客坐处：石头顶面中点
GROUND = 51
CYC = 12.0
DANCE_P, DANCE_OFF, DANCE_D = 48.0, 24.0, 12.0

SEATED = Sprite("""
      .###.
     .#####.
     #######
      #...#.
      #....#
      #..#.#
      #....#
       #..#
     .##..##.
    #........#
   #..........#
   #..........#
   #..........#
  #...........#
  #............#
 #.......#######
 #..............#
 ################
""")
STAND = Sprite("""
     .###.
    .#####.
    #######
     #...#.
     #....#
     #..#.#
     #....#
      #..#
    .##..##.
   #........#
   #........#
   #........#
   #........#
   #........#
   ##########
   #........#
   #........#
  #..........#
  #..........#
 #............#
 #............#
 ##############
""")
GOURD = Sprite("""
  .#.
  ###
 #...#
 #...#
  #.#
 #...#
#.....#
#.....#
#.....#
 #...#
  ###
""")
HEAD = Sprite("""
      .###.
     .#####.
     #######
      #...#.
      #....#
      #..#.#
      #....#
""")
LINES = ["举杯邀明月", "对影成三人", "花间一壶酒", "独酌无相亲"]


def moon(g: Gfx, x: float, y: float, r: float):
    """满月：亮面 + 几处暗斑（桂影）"""
    g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
    for dx, dy, rr in ((-4, -3, 2.2), (3, 2, 1.8), (-1, 5, 1.4), (5, -5, 1.0), (-6, 3, 1.0)):  # 暗斑
        g.d.ellipse((x + dx - rr, y + dy - rr * 0.8, x + dx + rr, y + dy + rr * 0.8), fill=0)
    for i in range(10):  # 边缘一圈抖动，月晕柔一点
        a = i / 10 * 2 * math.pi
        g.px(x + math.cos(a) * (r + 2), y + math.sin(a) * (r + 2))


def branch(g: Gfx, t: float, dx: float = 0.0):
    """左上角的花枝：一枝梅（五点小花）"""
    sw = math.sin(t * 0.7) * 0.8
    g.d.line([(dx - 2, 3), (dx + 12, 7), (dx + 24, 6 + sw), (dx + 34, 11 + sw)], fill=1, width=2)
    g.d.line([(dx + 12, 7), (dx + 18, 15 + sw)], fill=1)
    g.d.line([(dx + 24, 6 + sw), (dx + 28, 1)], fill=1)
    for fx, fy in ((dx + 18, 15 + sw), (dx + 28, 1), (dx + 34, 11 + sw), (dx + 8, 4), (dx + 22, 9 + sw)):
        g.d.ellipse((fx - 2, fy - 2, fx + 2, fy + 2), fill=0, outline=1)
        g.px(fx, fy)


@register
class Moon(Rest):
    id = "x2.moon"
    name = "邀月"
    desc = "花下独酌，举杯邀明月、对影成三人；不时起舞，月徘徊、影零乱"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0
        self.line0 = self.rng.randrange(len(LINES))

    # ------------------------------------------------------------ 动作

    def pose(self, t: float):
        """→ (状态, 参数)：("sit", 举杯程度 raise, 饮 drink) 或 ("dance", 秒数)"""
        k, n = win(t, DANCE_P, DANCE_D, DANCE_OFF)
        if k is not None:
            return "dance", k
        s = t % CYC
        lift = ease_in_out(span(s, 6.0, 7.2)) * (1 - ease_in_out(span(s, 8.5, 9.4)))
        drink = math.sin(math.pi * span(s, 8.5, 10.4))
        return "sit", (lift, drink)

    def figure(self, g: Gfx, t: float):
        """画酒客；返回脚下（影子的根）"""
        st, a = self.pose(t)
        if st == "dance":
            k = a
            up = ease_out_back(span(k, 0.0, 1.0)) * (1 - ease_in_out(span(k, DANCE_D - 1.0, DANCE_D)))
            if up < 0.5:
                return self.seated(g, 0, 0, t)
            bob = abs(math.sin(k * 3.2)) * 2
            x, y = FX - 7, FY - STAND.h + 1 - bob
            g.blit(STAND, x, y)
            for side in (-1, 1):  # 舞袖：长袖翻飞
                ph = k * 3.2 + (0 if side > 0 else 1.7)
                sx, sy = x + 7 + side * 3, y + 10
                hx = sx + side * (6 + 4 * math.sin(ph))
                hy = sy - 6 + 8 * math.cos(ph)
                g.d.line((sx, sy, hx, hy), fill=1, width=2)
                tail = [(hx, hy), (hx + side * 7, hy + 4 + 3 * math.sin(ph * 1.3)), (hx + side * 3, hy + 9)]
                g.d.polygon(tail, fill=0, outline=1)
            return FX, FY
        lift, drink = a
        return self.seated(g, lift, drink, t)

    def seated(self, g: Gfx, lift: float, drink: float, t: float):
        x, y = FX - 8, FY - SEATED.h + 1
        tilt = int(round(drink * 1.5))
        g.blit(SEATED, x, y)
        if tilt:  # 仰头：脸往后上方挪一点
            g.d.rectangle((x + 5, y, x + 12, y + 7), fill=0)
            g.blit(HEAD, x - 1, y - tilt)
        # 手臂与杯：闲时杯在膝上；举杯时伸向月亮；饮时到嘴边
        sx, sy = x + 11, y + 10
        rest = (x + 15, y + 15)
        toward = (x + 21, y + 1)
        mouth = (x + 13, y + 6 - tilt)
        if drink > 0:
            hx, hy = lerp(rest[0], mouth[0], drink), lerp(rest[1], mouth[1], drink)
        else:
            breath = math.sin(t * 1.2) * 0.5
            hx, hy = lerp(rest[0], toward[0], lift), lerp(rest[1] + breath, toward[1], lift)
        g.d.line((sx, sy, hx, hy), fill=1, width=2)
        g.d.rectangle((hx - 1, hy - 3, hx + 2, hy), fill=1)  # 杯
        if lift > 0.9 and blink(t, 0.3):  # 杯中映月
            g.px(hx, hy - 2, 0)
        g.blit(GOURD, x - 9, FY - GOURD.h + 2)
        return FX, FY

    def rock(self, g: Gfx):
        pts = [(FX - 16, GROUND), (FX - 13, FY + 1), (FX - 4, FY - 1), (FX + 10, FY), (FX + 15, GROUND)]
        g.d.polygon(pts, fill=0, outline=1)
        g.shade_poly(pts, 0.2)

    def shadow(self, g: Gfx, box, t: float, wild: float = 0.0):
        """把画好的人影投到地上：月在右上，影子向左倒在地面（抖动灰度），wild > 0 时乱舞"""
        x0, y0, x1, y1 = box
        a = g.array()
        sub = a[y0:y1, x0:x1]
        ys, xs = np.nonzero(sub)
        if len(xs) == 0:
            return
        ys = ys + y0
        xs = xs + x0
        h = FY - ys  # 离地高度
        jit = 0
        if wild > 0:
            jit = (np.sin(ys * 0.7 + t * 9) * 3 + np.sin(ys * 0.3 - t * 5) * 2) * wild
        px = (xs - h * 0.95 - 3 + jit).astype(int)
        py = (GROUND + 1 + h * 0.42).astype(int)
        ok = (px >= 0) & (px < 128) & (py >= 0) & (py < 64)
        px, py = px[ok], py[ok]
        a[py, px] |= BAYER[py, px] < 11
        px1 = np.minimum(px + 1, 127)
        a[py, px1] |= BAYER[py, px1] < 11
        g.put(a)

    # ------------------------------------------------------------ 画面

    def frame(self, g: Gfx, t: float, show=1.0, moon_y: float | None = None, bdx: float = 0.0):
        st, a = self.pose(t)
        sway = 0.0
        if st == "dance":
            sway = math.sin(a * 1.4) * 5 * span(a, 0.5, 2.0) * (1 - span(a, 10.0, 11.5))
        mx_, my_, r = MOON
        moon(g, mx_ + sway, moon_y if moon_y is not None else my_, r)
        # 薄云掠过月面
        cx = 160 - (t * 2.5 % 220)
        cloud(g, cx, my_ + 4, 26, 8, seed=self.seed + int(t * 2.5 // 220))
        branch(g, t, bdx)
        for j in range(2):  # 落花
            ph = t / 9 + j * 0.5
            k = ph % 1
            px = 14 + rand(int(ph) * 2 + j, self.seed) * 24 + math.sin(k * 9) * 4 + k * 10
            py = 8 + k * 50
            if py < GROUND:
                g.px(px, py)
                g.px(px + 1, py + (1 if int(k * 20) % 2 else 0))
        g.d.line((0, GROUND, 127, GROUND), fill=1)
        for i in range(70, 128, 11):  # 草
            g.d.line((i, GROUND - 1, i + 1, GROUND - 3), fill=1)
        self.rock(g)
        if show > 0:
            before = g.array() if show < 1 else None
            self.figure(g, t)
            self.shadow(g, (FX - 22, 12, FX + 26, FY + 1), t, wild=1.0 if st == "dance" and a > 1 else 0.0)
            if before is not None:  # 显形：抖动淡入
                after = g.array()
                m = BAYER < int(show * 16)
                g.put(np.where(m, after, before))
        # 诗
        if st == "dance":
            if 1.0 < a < 11.0:
                line = "我歌月徘徊" if a < 6 else "我舞影零乱"
                typewriter(g, 66, 53, line, (a - 1.0) % 5.0, cps=3)
        else:
            s = t % CYC
            n = int(t // CYC)
            if 6.5 < s < 11.5 and n % 2 == 0:
                typewriter(g, 66, 53, LINES[(n // 2 + self.line0) % len(LINES)], s - 6.5, cps=3)
        self.mx(g, t, st, a, sway)

    def mx(self, g: Gfx, t: float, st, a, sway: float):
        ox = int(round(sway / 3))
        for y in range(8):
            for x in range(8):
                if (x - 3.5 - ox) ** 2 + (y - 3.5) ** 2 <= 12.5:
                    g.mx[y, x] = True
        cy = int((t * 0.6) % 14) - 3  # 云影从月面掠过
        for x in range(8):
            if 0 <= cy < 8 and (x + int(t)) % 3:
                g.mx[cy, x] = False
        if st == "sit" and a[0] > 0.9:  # 举杯时月亮“眨眼”
            g.mx_level = 2

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        my = lerp(80, MOON[1], ease_out(span(t, 0.0, 1.6)))
        bdx = lerp(-40, 0, ease_out(span(t, 0.5, 1.5)))
        self.frame(g, 0.0, show=span(t, 1.4, 2.6), moon_y=my, bdx=bdx)
        if t < 1.6:
            g.mx[:] = False
            r = ease_out(span(t, 0, 1.6)) * 4
            for y in range(8):
                for x in range(8):
                    if (x - 3.5) ** 2 + (y - 3.5 - (4 - r) * 2) ** 2 <= 12.5 and y >= 8 - r * 2:
                        g.mx[y, x] = True

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.ht + t)
        iris(g, span(t, 0.0, self.T["exit"]), 80, 30)
        if t > 0.8:
            g.mx[:] = False
