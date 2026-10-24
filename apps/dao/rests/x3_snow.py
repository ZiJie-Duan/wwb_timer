"""寒江独钓：柳宗元《江雪》“千山鸟飞绝，万径人踪灭。孤舟蓑笠翁，独钓寒江雪。”

千山覆雪（远山山顶实白的雪冠、山脚网点），江面空阔，碎光稀疏；一叶小舟随波轻轻起伏，有倒影；
小道士戴斗笠、披蓑衣，坐在船尾垂钓，钓竿伸出去，浮子在水面一点一点；右岸一丛雪松。
雪分远近三层飘落（远的小而慢，近的是十字雪花、左右摇）。
持续：斗笠和船舷上的积雪慢慢变厚（150 秒一轮），积满了小道士抖一抖，雪簌簌落下。
      小事件（47s）：浮子连点几下 → 提竿：多半是空钩（钓的是雪），三成钓上一尾小鱼挂着乱扑腾，
      放回江里，重新甩线、浮子落水漾开一圈。“千山鸟飞绝”，所以这一幕刻意没有鸟。
      “独钓寒江雪”题字（80s 一次）。
入场：雪由疏到密，小舟从左边滑进来，船尾拖着水纹。  退场：小舟悠悠划出画外，风吹雪斜，画面淡出。
点阵：雪花落下，底部积雪随斗笠积雪一起变厚，抖雪时清空。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bake, every, glints, hat, mountain, pine_pad, plate, ridge, ring

WATER = 39
BOAT_Y = 51          # 船底水线
BX = 44              # 船中心
DX = BX - 8          # 小道士（船尾）
SNOWC = 150.0


def _boat():
    """小舟 40×8：船头上翘（右）、船尾略翘，船舷一道白边、木板缝，船身右半背光网点"""
    p = Part(40, 8)
    pts = [(0, 1), (3, 3), (34, 3), (39, 0), (37, 4), (33, 7), (6, 7), (2, 4)]
    p.shape("polygon", pts, fill=0)
    p.d.polygon(pts, outline=1)
    p.d.line((3, 3, 34, 3), fill=1)
    p.d.line((5, 5, 33, 5), fill=1)
    for x in range(8, 33, 6):
        p.px(x, 4, 1)
    p.dither([(20, 6), (35, 4), (33, 7), (20, 7)], 0.5, 1)
    return p.sprite()


def _cape():
    """蓑衣：盖住肩背到腰，一道道草茎、下摆参差"""
    p = Part(17, 9)
    pts = [(5, 0), (11, 0), (16, 7), (0, 7)]
    p.shape("polygon", pts, fill=1)
    for x in range(2, 15, 2):
        p.d.line((x, 3, x, 7), fill=0)
    p.d.line((4, 2, 12, 2), fill=0)
    for x in range(0, 17, 2):
        p.px(x, 8, 1)
    return p.sprite()


FISH = pix.frames("""
  #
 ###
 #.#
 ###
 ###
  #
 # #
---
  #
 ###
 #.#
 ###
 ###
  #
  ##
""")

_C: dict = {}


def parts():
    if not _C:
        far = mountain(ridge([(8, 18, 18), (34, 12, 20), (66, 22, 16), (100, 10, 22), (128, 17, 14)], 21, base=42,
                             rough=0.9, power=1.1), lit=((0.25, 1),), shade=(), cap=(20, 2), outline=1)
        mid = mountain(ridge([(10, 28, 20), (32, 32, 12), (122, 27, 16)], 23, base=50, rough=1.0, round_top=True),
                       lit=((0.5, 1), (0.25, 2)), shade=((0.125, 1),), cap=(32, 2), outline=1)
        trees = bake(lambda g: _bank(g), solid=lambda d: d.polygon([(100, 64), (108, 56), (128, 52), (128, 64)], fill=1))
        _C.update(far=far, mid=mid, boat=_boat(), hat=hat(), cape=_cape(), bank=trees,
                  pads=[pine_pad(11, 1, snow=True), pine_pad(9, 2, snow=True), pine_pad(13, 3, snow=True)])
    return _C


def _bank(g: Gfx):
    g.d.polygon([(100, 64), (108, 56), (128, 52), (128, 64)], fill=0, outline=1)
    g.d.line((108, 56, 128, 52), fill=1)
    g.d.line((109, 57, 127, 53), fill=1)  # 岸上积雪两层
    for x in range(104, 128, 3):
        g.px(x, 60 + (x % 2))


@register
class SnowFishing(Rest):
    id = "x3.snow"
    name = "寒江独钓"
    desc = "千山覆雪，小道士戴笠披蓑坐在孤舟上垂钓；雪分三层飘落、斗笠积雪渐厚抖落，浮子一点，提竿多是空钩"
    T = {"enter": 3.4, "exit": 1.3}

    def setup(self):
        self.P = parts()

    # ------------------------------------------------------------ 雪

    def snow(self, g: Gfx, t: float, layer: int, density: float = 1.0, wind: float = 0.0):
        n, sp, sway, big = ((26, 7, 1.0, False), (18, 13, 2.0, False), (9, 22, 3.0, True))[layer]
        n = int(n * density)
        for i in range(n):
            seed = layer * 100 + i
            x0 = rand(i, seed) * 140
            y = (rand(i + 7, seed) * 72 + t * sp * (0.8 + 0.4 * rand(i, seed + 1))) % 72 - 4
            x = (x0 + math.sin(t * 0.8 + i) * sway + wind * y * 0.5 + t * wind * 6) % 140 - 6
            if big:
                g.px(x, y), g.px(x - 1, y), g.px(x + 1, y), g.px(x, y - 1), g.px(x, y + 1)
            else:
                g.px(x, y)
                if layer == 1 and i % 3 == 0:
                    g.px(x + 1, y)

    # ------------------------------------------------------------ 船与人

    def boat(self, g: Gfx, t: float, bx: float, snow_k: float, rod: bool = True, oar: bool = False):
        P = self.P
        bob = round(math.sin(t * 0.9) * 0.8)
        by = BOAT_Y + bob
        for i, x in enumerate(range(int(bx) - 18, int(bx) + 20, 2)):  # 倒影：隔点
            if (x + int(t * 2)) % 4 < 2:
                g.px(x, BOAT_Y + 3 + (i % 2))
        g.d.line((bx - 14, BOAT_Y + 5, bx + 10, BOAT_Y + 5), fill=0)
        for i in range(0, 20, 4):
            g.px(bx - 12 + i + int(t * 3) % 4, BOAT_Y + 5)
        pix.blit(g, P["boat"], bx - 20, by - 7)
        if snow_k > 0.15:  # 船舷积雪
            n = int(snow_k * 14)
            for i in range(n):
                g.px(bx - 16 + i * 2 + (i % 2), by - 5)
        return by

    def angler(self, g: Gfx, t: float, x: float, by: float, snow_k: float, shake: float = 0.0, arm="offer"):
        P = self.P
        sx = round(math.sin(shake * 40) * 1) if shake > 0 else 0

        def front(g_, at):
            at(-8, -17, P["cape"])
            at(-10 + sx, -33, P["hat"])
            n = int(snow_k * 4)  # 斗笠积雪：笠顶一层层堆白
            top = by - 6 - 33
            for r in range(n):
                g_.d.line((x + sx - 1 - r * 2, top - 1 + r, x + sx + 1 + r * 2, top - 1 + r), fill=1)
            if n:
                g_.px(x + sx, top - 2)

        return figure(g, x, by - 6, t, legs="sit", arm=arm, front=front, face="sleep" if (t % 31) > 24 else "normal")

    # ------------------------------------------------------------ 钓

    def fishing(self, g: Gfx, t: float, hand, by: float):
        hx, hy = hand
        ev = every(t, 47, 12, 15)
        lt = ev[1] if ev else None
        catch = ev and rand(ev[0], self.seed) < 0.3
        lift = 0.0
        if lt is not None:
            lift = span(lt, 4.3, 5.0) * (1 - span(lt, 8.5, 9.3))
        tip = (hx + lerp(44, 32, lift), hy - lerp(10, 22, lift))
        g.d.line((hx, hy, (hx + tip[0]) / 2, (hy + tip[1]) / 2 - 1 + lift * 2, tip[0], tip[1]), fill=1)
        fx, fy = tip[0] + 3, WATER + 13
        if lt is None or lt < 4.3:
            dip = 0
            if lt is not None and 1.5 < lt < 4.3:
                dip = 1 if int(lt * 5) % 3 == 0 else 0
            g.d.line((tip[0], tip[1], fx, fy - 2), fill=1)
            g.d.rectangle((fx, fy - 2 + dip, fx + 1, fy + dip), fill=1)  # 浮子
            g.px(fx, fy - 3 + dip, 0)
            k = (t % 3.3) / 3.3
            ring(g, fx + 0.5, fy + 1, k, rmax=4, flat=0.3)
            if dip:
                ring(g, fx + 0.5, fy + 1, 0.3, rmax=3, flat=0.3)
        elif lt < 9.3:  # 提竿：线挂着（空钩 / 小鱼）
            sw = math.sin(lt * 4) * 2
            end = (tip[0] + sw, tip[1] + 14)
            g.d.line((tip[0], tip[1], end[0], end[1]), fill=1)
            if lt < 5.0:
                for i in range(5):
                    g.px(end[0] + (i - 2) * 2, end[1] + 2 + i % 2)  # 甩起的水珠
            if catch and lt < 8.6:
                f = FISH[int(lt * 6) % 2]
                pix.blit(g, f, end[0] - 2, end[1] + 1)
            else:
                g.d.arc((end[0] - 2, end[1] - 1, end[0], end[1] + 2), 0, 180, fill=1)  # 空钩
        else:  # 重新甩线
            k = span(lt, 9.3, 10.4)
            x = lerp(tip[0], fx, k)
            y = lerp(tip[1], fy, k) - math.sin(k * math.pi) * 8
            g.d.line((tip[0], tip[1], x, y), fill=1)
            g.d.rectangle((x, y - 2, x + 1, y), fill=1)
            if k >= 1:
                ring(g, fx + 0.5, fy + 1, span(lt, 10.4, 12), rmax=6, flat=0.3)
        return lt, catch

    # ------------------------------------------------------------ 合成

    def world(self, g: Gfx, t: float, bx: float = BX, density: float = 1.0, wind: float = 0.0, rod: bool = True):
        P = self.P
        self.snow(g, t, 0, density, wind)
        g.blit(P["far"], 0, 0)
        self.snow(g, t, 1, density * 0.5, wind)
        g.blit(P["mid"], 0, 0)
        g.d.rectangle((0, WATER, 127, 63), fill=0)
        for x in range(0, 128, 2):  # 对岸：一道隔点
            g.px(x, WATER)
        glints(g, 0, 128, WATER + 3, 63, t, 5, n=12, speed=1.5, far=1, near=5, blink=0.5, rows=3)
        g.blit(P["bank"], 0, 0)
        for cx, top, n in ((117, 26, 4), (104, 40, 2)):  # 岸上雪松：一层层压着雪的枝
            g.d.line((cx, top + 2, cx, top + 6 + n * 6), fill=1)
            for i in range(n):
                y = top + i * 6
                w = 4 + i * 3
                tri_ = [(cx, y), (cx + w, y + 6), (cx - w, y + 6)]
                g.d.polygon(tri_, fill=0)
                g.d.line((cx - w, y + 6, cx, y, cx + w, y + 6), fill=1)
                g.d.line((cx - w + 2, y + 5, cx, y + 1, cx + w - 2, y + 5), fill=1)
                for x in range(cx - w + 2, cx + w - 1, 2):
                    g.px(x, y + 7)
        c = t % SNOWC
        snow_k = span(c, 0, SNOWC - 8)
        shake = span(c, SNOWC - 8, SNOWC - 6) if c > SNOWC - 8 else 0
        if c > SNOWC - 6:  # 抖下来的雪簌簌落下
            k = span(c, SNOWC - 8, SNOWC - 4)
            snow_k = 0
            for i in range(10):
                g.px(bx - 8 + (i - 5) * 2.2 * (1 + k), BOAT_Y - 40 + k * k * 40 + (i % 3) * 2)
        by = self.boat(g, t, bx, snow_k)
        h = self.angler(g, t, bx - 8, by, snow_k if shake == 0 else 1, shake)
        if rod:
            self.fishing(g, t, h["hand"], by)
        self.snow(g, t, 2, density, wind)
        return snow_k

    def poem(self, g: Gfx, t: float):
        if every(t, 80, 12, 35):
            plate(g, 64, 3, "独钓寒江雪", align="center")

    def mx(self, g: Gfx, t: float, snow_k: float):
        for i in range(6):
            x = int(rand(i, 3) * 8)
            y = int((t * (1.2 + rand(i, 4)) + rand(i, 5) * 8) % 8)
            g.mx[y, (x + int(y * 0.3)) % 8] = True
        h = int(snow_k * 2.5) + 1
        g.mx[8 - h:, :] = True

    def hold(self, g: Gfx, t: float):
        k = self.world(g, t)
        self.poem(g, t)
        self.mx(g, t, k)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        tw = t - T
        bx = lerp(-24, BX, ease_out(span(t, 0, 2.6)))
        self.world(g, tw, bx, density=0.3 + 0.7 * span(t, 0, T))
        if t < 2.6:  # 船尾拖着水纹
            for i in range(4):
                x = bx - 22 - i * 5
                g.d.line((x, BOAT_Y + 2 + i % 2, x + 3, BOAT_Y + 2 + i % 2), fill=1)
        g.fade(span(t, 0, 0.8))
        self.mx(g, tw, 0)
        g.mx[: max(0, int(8 - t * 4))] = False

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        k = span(t, 0, self.T["exit"])
        self.world(g, tt, BX + ease_in_out(k) * 100, wind=k * 2, rod=True)
        g.fade(1 - span(t, 0.6, 1.3))
        self.mx(g, tt, 0)
        g.mx[: int(k * 8)] = False
