"""听雨：温庭筠《更漏子》“梧桐树，三更雨……一叶叶，一声声，空阶滴到明”；雨打芭蕉；
《道德经》七十八章“天下莫柔弱于水，而攻坚强者莫之能胜”（檐下的滴水石被滴出一个小坑）。

侧视：左边一间小屋的檐廊（瓦顶斜下来，檐口一片瓦当、一片滴水），廊柱、木地板，墙上挂“听雨”小匾；
小道士盘坐廊下听雨，手边一盏茶冒着热气。右边院子：远山在雨里只剩一道隔点山脊，斜雨丝一阵密一阵疏，
芭蕉三片大叶被雨打得一颤一颤，地上水洼一圈圈涟漪。
持续：檐口水珠鼓起 → 落下（越落越快）→ 打在滴水石上溅起水花；风铃轻摆；小道士呼吸眨眼，时而闭目。
      小事件：端起茶盏喝一口，热气一冒（37s）；青蛙跳上石阶，鼓腮叫两声再跳走（83s）；
      远处一道闪电，满屏一闪，小道士吓一跳，随后雨急一阵（151s）；廊柱上一只蜗牛慢慢往上爬（十分钟一趟）。
退场：雨渐停，檐口最后一滴落下，画面淡出。
点阵：顶上一行檐，三列水珠落下，落地溅开。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bake, drops, every, mountain, plate, ridge, ring, splash

FLOOR = 50          # 廊下地板
DX = 40             # 小道士
TIP = (73, 17)      # 檐口滴水
STONE = (74, 57)    # 滴水石
GROUND = 58
PILLAR = 60


def _roof():
    """瓦顶（侧视）：斜坡上一垄垄筒瓦（竖肋），檐口一排圆瓦当，下面梁和一排椽头"""
    def ry(x):
        return 1 + max(0.0, (x - 24) * 11 / 48)

    def draw(g):
        g.d.polygon([(-1, -1), (24, -1), (73, 11), (73, 16), (-1, 16)], fill=0)
        g.d.line((-1, 0, 24, 0, 73, 11), fill=1)                 # 屋脊线
        for x in range(0, 72, 3):                                 # 筒瓦：竖肋
            y = ry(x)
            g.d.line((x, y + 1, x, y + 4), fill=1)
            g.px(x + 1, y + 4)
        for x in range(1, 73, 3):                                 # 檐口一排瓦当
            y = ry(x) + 5
            g.d.ellipse((x - 1, y, x + 1, y + 2), fill=1)
            g.px(x, y + 1, 0)
        g.d.line((0, 15, 66, 15), fill=1)                        # 檐下梁
        for x in range(3, 64, 6):                                 # 椽头
            g.d.rectangle((x, 12 if x > 24 else 9, x + 1, 14), fill=1)

    return bake(draw, solid=lambda d: d.polygon([(-1, -1), (24, -1), (74, 11), (74, 18), (-1, 16)], fill=1))


def _porch():
    """廊柱、地板、墙（窗格）"""
    def draw(g):
        g.d.rectangle((PILLAR, 16, PILLAR + 3, FLOOR), fill=1)       # 柱
        g.d.line((PILLAR + 2, 18, PILLAR + 2, FLOOR - 2), fill=0)
        g.d.rectangle((PILLAR - 1, FLOOR - 2, PILLAR + 4, FLOOR), fill=1)
        g.d.line((0, FLOOR, 68, FLOOR), fill=1)                    # 地板
        g.d.line((0, FLOOR + 2, 68, FLOOR + 2), fill=1)
        for x in range(2, 72, 7):
            g.px(x, FLOOR + 1)
        g.d.rectangle((0, FLOOR + 3, 68, 63), fill=0)
        for row, y in enumerate((FLOOR + 4, FLOOR + 9)):           # 台基：错缝条石
            g.d.line((0, y + 4, 68, y + 4), fill=1)
            for x in range(-6 + row * 7, 68, 14):
                g.d.line((x, y, x, y + 3), fill=1)
                g.px(x + 3, y + 1)
        g.d.line((0, FLOOR + 3, 68, FLOOR + 3), fill=0)
        g.d.line((68, FLOOR + 3, 68, 63), fill=1)
        for x in range(2, 30, 6):                                  # 墙下的窗格
            g.d.line((x, 34, x, 47), fill=1)
        g.d.rectangle((0, 33, 30, 48), outline=1)
        g.d.line((0, 40, 30, 40), fill=1)
        g.d.line((31, 18, 31, FLOOR), fill=1)                      # 墙与廊的分界柱
        g.d.line((32, 18, 32, FLOOR), fill=0)

    return bake(draw)


def _stone():
    p = Part(11, 5)
    p.shape("polygon", [(0, 4), (1, 1), (4, 0), (8, 0), (10, 2), (10, 4)], fill=0)
    p.d.polygon([(0, 4), (1, 1), (4, 0), (8, 0), (10, 2), (10, 4)], outline=1)
    p.d.line((3, 1, 7, 1), fill=1)
    p.px(5, 1, 0)                                  # 滴出的小坑
    p.dither([(7, 2), (10, 2), (10, 4), (7, 4)], 0.5, 1)
    return p.sprite()


def _cup():
    p = Part(5, 4)
    p.shape("polygon", [(0, 0), (4, 0), (3, 3), (1, 3)], fill=1)
    p.d.line((1, 1, 3, 1), fill=0)
    return p.sprite()


FROG = pix.frames("""
  ##   ##
 #.## #.#
 ########
##.####.#
#########
 ##.  .##
---
  ##   ##
 #.## #.#
 ########
##.####.#
##.....##
 #.....#
 ##.  .##
---
   ##   ##
  #.## #.#
 #########
#####.###
##    ###
#      ##
""")

SNAIL = pix.sprite("""
 .##
#.#.#
 ##.#
## ##
""")

_C: dict = {}


def parts():
    if not _C:
        _C.update(roof=_roof(), porch=_porch(), stone=_stone(), cup=_cup(),
                  far=mountain(ridge([(88, 34, 14), (104, 27, 16), (122, 31, 12)], 4, base=52, rough=1.0,
                                     round_top=True), lit=((0.25, 2),), shade=((0.125, 1),), outline=2,
                               solid=False))
        p = Part(12, 8)                                         # 端茶的手（袖子向前上举）
        p.shape("polygon", [(0, 2), (4, 1), (9, 0), (10, 4), (3, 7), (0, 6)], fill=1)
        p.d.line((8, 0, 8, 4), fill=0)
        p.dither([(1, 5), (8, 3), (8, 5), (3, 7)], 0.5, 0)
        p.shape("rectangle", (9, 0, 11, 3), fill=1)
        spr = p.sprite()
        spr.hand = (10, 0)
        _C["sip"] = spr
    return _C


def leaf(g: Gfx, x: float, y: float, ln: float, ang: float, droop: float, flip: bool = False, wd: float = 5.0):
    """芭蕉叶（像素）：叶脉从 (x, y) 弯出去（先上扬、再下垂），叶片是一道道平行侧脉（芭蕉叶的竖纹），边上有裂口"""
    s = -1 if flip else 1
    mid = []
    for i in range(14):
        k = i / 13
        a = ang - droop * k * k * 2.2
        if i == 0:
            px_, py_ = x, y
        else:
            px_ = mid[-1][0] + s * math.cos(a) * ln / 13
            py_ = mid[-1][1] - math.sin(a) * ln / 13
        mid.append((px_, py_))
    edge = []
    for i in range(1, 14):
        k = i / 13
        w_ = wd * math.sin(math.pi * min(1.0, k * 1.1)) * (0.4 + 0.6 * k ** 0.3)
        mx, my = mid[i]
        edge.append((mx + s * 1.0, my - w_))
        if i % 1 == 0 and not (i in (5, 9)):            # 侧脉（5、9 处裂开）
            g.d.line((mx, my, mx + s * 1.0, my - w_), fill=1)
    g.d.line(mid, fill=1)
    g.d.line([mid[1]] + edge, fill=1)
    g.d.line(mid[4:], fill=1)
    for i in range(4, 13, 2):                          # 叶下沿一道细边
        g.px(mid[i][0], mid[i][1] + 1)


@register
class RainListen(Rest):
    id = "x3.rain"
    name = "听雨"
    desc = "檐廊下小道士盘坐听雨：檐口水珠一滴滴落在石上溅花，芭蕉被雨打得一颤一颤；喝茶、蛙鸣、远雷，蜗牛爬柱"
    T = {"enter": 2.8, "exit": 1.2}

    def setup(self):
        self.P = parts()

    # ------------------------------------------------------------ 雨

    def rate(self, t: float) -> float:
        """雨势 0..1：缓慢起伏；打雷后急一阵"""
        r = 0.45 + 0.35 * noise(t * 0.05, self.seed)
        ev = every(t, 151, 30, 40)
        if ev and ev[1] > 1.0:
            r += 0.5 * (1 - span(ev[1], 6, 30))
        return clamp(r)

    def drip(self, g: Gfx, t: float, on: float = 1.0):
        """檐口的水珠：鼓起 → 落下 → 石上溅花"""
        per = 1.9
        k = (t % per) / per
        x, y0 = TIP[0], TIP[1] + 2
        y1 = STONE[1] - 1
        if k < 0.55:
            if on > 0:
                r = k / 0.55
                g.px(x, y0)
                if r > 0.4:
                    g.px(x, y0 + 1)
                if r > 0.8:
                    g.px(x - 1, y0 + 1), g.px(x + 1, y0 + 1), g.px(x, y0 + 2)
        elif k < 0.8:
            if on > 0:
                f = ease_in(span(k, 0.55, 0.8))
                yy = lerp(y0 + 2, y1, f)
                g.d.line((x, yy - 1 - f * 2, x, yy), fill=1)
        else:
            f = span(k, 0.8, 1.0)
            splash(g, x, y1 - 1, f)
        if k > 0.82:
            ring(g, x, y1 + 1, span(k, 0.82, 1.0), rmax=4, flat=0.3)

    def yard(self, g: Gfx, t: float, rate: float):
        g.blit(self.P["far"], 0, 0)
        g.d.line((68, GROUND, 127, GROUND), fill=1)  # 院子地面、水洼
        for x in range(76, 127, 3):
            g.px(x, GROUND + 2 + (x // 3) % 2)
        g.d.line((86, GROUND + 4, 112, GROUND + 4), fill=1)
        for i in range(3):                         # 水洼里的涟漪
            per = 1.3 + i * 0.4
            k = ((t + i * 0.7) % per) / per
            ring(g, 90 + i * 9 + int(rand(int((t + i * 0.7) // per), i) * 6), GROUND + 4, k, rmax=4, flat=0.3)
        n = int(10 + 26 * rate)
        drops(g, (70, 0, 128, GROUND), t, self.seed, n=n, speed=80, length=4, slant=0.3)
        # 芭蕉：三片大叶，被雨点打中就往下一颤
        g.d.rectangle((111, 30, 114, GROUND), fill=0, outline=1)    # 芭蕉的假茎
        for y in range(33, GROUND, 4):
            g.d.line((112, y, 113, y + 2), fill=1)
        for j, (bx, by, ln, ang, fl, wd) in enumerate(((112, 31, 28, 1.2, True, 6), (113, 32, 22, 0.9, False, 5),
                                                       (112, 37, 24, 0.5, True, 5), (114, 40, 14, 0.7, False, 4))):
            per = 2.3 + j * 0.9
            k = ((t + j * 1.1) % per) / per
            hit = math.exp(-k * 5) * math.sin(k * 20) * 0.22 * (0.5 + rate)
            droop = 0.45 + hit + math.sin(t * 0.8 + j) * 0.03
            leaf(g, bx, by, ln, ang, droop, flip=fl, wd=wd)
        for x in (76, 80, 124):                    # 地上的雨花
            per = 0.7 + (x % 5) * 0.11
            k = ((t + x * 0.13) % per) / per
            splash(g, x + int(rand(int((t + x * 0.13) / per), x) * 6), GROUND, k * 1.6)

    def chime(self, g: Gfx, t: float, gust: float):
        x, y = 52, 17
        a = math.sin(t * 2.1) * (0.12 + gust * 0.4)
        bx, by = x + math.sin(a) * 6, y + math.cos(a) * 6
        g.d.line((x, y, bx, by), fill=1)
        g.d.polygon([(bx - 2, by + 3), (bx + 2, by + 3), (bx + 1, by), (bx - 1, by)], fill=1)
        g.px(bx + math.sin(a) * 4, by + 6)
        if gust > 0.5 and int(t * 4) % 2 == 0:
            g.px(bx + 4, by - 1), g.px(bx + 5, by - 2)

    def world(self, g: Gfx, t: float, rate: float, drip: float = 1.0):
        P = self.P
        thunder = every(t, 151, 6, 40)
        bolt = thunder and 1.0 < thunder[1] < 1.35
        self.yard(g, t, rate)
        if bolt:  # 闪电：从云里劈到远山
            x = 104
            pts = [(x, 0)]
            for i in range(7):
                x += (rand(i, int(t)) - 0.5) * 10
                pts.append((x, (i + 1) * 4))
            g.d.line(pts, fill=1, width=2)
            g.d.line((pts[3][0], pts[3][1], pts[3][0] + 6, pts[3][1] + 5), fill=1)
        g.blit(P["porch"], 0, 0)
        pix.blit(g, P["stone"], STONE[0] - 5, STONE[1] - 3)
        self.drip(g, t, drip)
        # 蜗牛（十分钟爬一趟柱子）
        k = (t % 600) / 600
        g.blit(SNAIL, PILLAR - 1, lerp(FLOOR - 6, 20, k) + (int(t * 2) % 2) * 0)
        g.blit(P["roof"], 0, 0)
        self.chime(g, t, 1.0 if thunder and thunder[1] < 4 else 0.0)
        self.frog(g, t)
        # 小道士与茶
        sip = every(t, 37, 5, 12)
        wow = thunder and 1.0 < thunder[1] < 3.5
        if sip and 0.6 < sip[1] < 4.4:
            h = figure(g, DX, FLOOR, t, legs="sit", arm=P["sip"], arm_at=(-1, -18),
                       face="sleep" if 1.6 < sip[1] < 3.4 else "normal")
            hx, hy = h["hand"]
            pix.blit(g, P["cup"], hx - 2, hy - 3)
            self.steam(g, hx, hy - 4, t)
        else:
            ph = t % 23
            pose = "meditate" if 9 < ph < 16 else "sit"
            daoshi(g, DX, FLOOR, pose, t, face="wow" if wow else "normal")
            pix.blit(g, P["cup"], DX + 15, FLOOR - 4)
            self.steam(g, DX + 17, FLOOR - 5, t)
        return thunder

    def steam(self, g: Gfx, x: float, y: float, t: float):
        for i in range(2):
            k = ((t * 0.6 + i * 0.5) % 1)
            yy = y - k * 8
            xx = x + math.sin(t * 3 + i * 2 + k * 5) * 1.2 + i
            if k < 0.85:
                g.px(xx, yy)
                if k < 0.4:
                    g.px(xx, yy - 1)

    def frog(self, g: Gfx, t: float):
        ev = every(t, 83, 10, 25)
        if not ev:
            return
        lt = ev[1]
        sx, sy = STONE[0] + 2, STONE[1] - 3
        if lt < 1.0:  # 从右边跳过来
            k = span(lt, 0, 1.0)
            x = lerp(118, sx, k)
            y = lerp(GROUND, sy, k) - math.sin(k * math.pi) * 9
            pix.blit(g, FROG[2], x - 4, y - 6, flip=True)
        elif lt < 8.5:
            croak = (1.8 < lt < 2.4) or (3.0 < lt < 3.6)
            pix.blit(g, FROG[1] if croak else FROG[0], sx - 4, sy - (7 if croak else 6))
            if croak:
                for j in range(2):
                    g.d.arc((sx + 6 + j * 3, sy - 8 - j, sx + 10 + j * 3, sy - 2 + j), 300, 60, fill=1)
        else:
            k = span(lt, 8.5, 9.6)
            x = lerp(sx, 130, k)
            y = lerp(sy, GROUND, k) - math.sin(k * math.pi) * 10
            pix.blit(g, FROG[2], x - 4, y - 6)

    def mx(self, g: Gfx, t: float, rate: float = 1.0, drip: float = 1.0):
        g.mx[0, :] = True
        g.mx[1, ::2] = True
        for j, col in enumerate((1, 4, 6)):
            per = 1.3 + j * 0.37
            k = ((t + j * 0.5) % per) / per
            y = int(ease_in(k) * 8) + 1
            if drip > 0 and y < 7:
                g.mx[y, col] = True
            elif y >= 7:
                g.mx[7, col] = True
                if k > 0.9:
                    g.mx[6, max(col - 1, 0)] = g.mx[6, min(col + 1, 7)] = True

    def hold(self, g: Gfx, t: float):
        th = self.world(g, t, self.rate(t))
        plate(g, 9, 20, "听雨")
        if th and 1.0 < th[1] < 1.12:
            pix.flash(g)
        self.mx(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        tw = t - T
        self.world(g, tw, self.rate(tw) * span(t, 0.4, T))
        g.fade(span(t, 0, 1.0))
        drop = ease_out_back(span(t, 0.8, 1.8))  # 小匾落下来晃一晃
        plate(g, 9, lerp(3, 20, drop), "听雨")
        self.mx(g, tw)
        g.mx[: max(0, int(8 - t * 6))] = False

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        k = span(t, 0, self.T["exit"])
        self.world(g, tt, self.rate(tt) * (1 - k) ** 2)
        g.fade(1 - span(t, 0.5, 1.2))
        self.mx(g, tt)
        g.mx[:, : int(k * 8)] = False
