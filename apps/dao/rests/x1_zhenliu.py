"""枕石漱流：溪边，小道士头枕一块圆石仰卧，斗笠盖脸，跷着腿，一只手垂进溪水里。

依据：《世说新语·排调》：孙子荆年少时欲隐，语王武子“当枕石漱流”，误曰“漱石枕流”。王曰：“流可枕，石可漱乎？”
孙曰：“所以枕流，欲洗其耳；所以漱石，欲砺其齿。”

入场：小道士躺在岸上，一顶斗笠左右飘摆着从天上落下，正好盖在脸上一弹；一膝立起，另一只脚跷上去。
持续：远山虚线、两朵小云慢飘；岸边一排卵石、芦苇随风摇；他枕石仰卧、斗笠盖脸，跷起的脚尖一点一点；
      垂进水里的手随水晃、一圈圈涟漪；溪水三层波纹从右往左流。
      小事件（每 150 秒一轮）：鱼跃出水划个弧落回去（37s）；水面漂过桃花 / 落叶 / 小葫芦（53s，每轮换一样）；
      蜻蜓飞来停在跷起的脚尖上跟着一起晃，再飞走（79s）；“枕石漱流”竖写（97s）；
      浪花溅上耳边，斗笠一跳、露出瞪圆的眼，“枕流欲洗其耳”（131s）。
退场：掀开斗笠，睁眼，画面收拢。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x1_common import cached, ev, iris, plate, supine, vplate

BANK = 41           # 岸面
WATER = 48          # 水面
MAN_X = 30
EV = 150.0


def _hat():
    """斗笠 26×9：扁圆锥，竹篾编纹（放射暗线 + 一圈横篾）、笠顶小尖、笠沿一道亮边、背光网点"""
    p = Part(26, 9)
    p.shape("polygon", [(0, 8), (3, 6), (10, 2), (13, 0), (16, 2), (23, 6), (25, 8)], fill=1)
    for x in (3, 7, 11, 15, 19, 23):
        p.d.line((13, 1, x, 7), fill=0)
    p.d.line((6, 5, 20, 5), fill=0)
    p.d.line((1, 8, 24, 8), fill=1)
    p.dither([(14, 2), (24, 7), (14, 7)], 0.25, 0)
    p.px(13, 0, 1)
    return p.sprite()


def _stone():
    """枕头石 16×8：圆滚滚的卵石，左上高光，右下网点阴影，一道裂纹"""
    p = Part(16, 8)
    p.shape("ellipse", (0, 0, 15, 9), fill=1)
    p.dither([(7, 3), (16, 3), (16, 8), (5, 8)], 0.5, 0)
    p.d.line((3, 2, 5, 1), fill=0)
    p.px(10, 4, 0), p.px(11, 5, 0)
    return p.sprite()


def _bank():
    """溪岸 128×20：岸面一道亮线，岸壁（暗）上几块卵石、几丛草，底下接水"""
    p = Part(128, 20)
    p.shape("rectangle", (0, 0, 127, WATER - BANK), fill=0)
    p.d.line((0, 0, 127, 0), fill=1)
    p.dither([(0, 1), (128, 1), (128, 3), (0, 3)], 0.5, 1)
    for x in (8, 22, 90, 104, 118):                      # 岸上的小草
        p.d.line((x, 0, x - 1, -3), fill=1), p.d.line((x + 1, 0, x + 2, -2), fill=1)
    return p.sprite()


def _arm():
    """垂进水里的手 7×12：宽袖顺着岸垂下（袖口镶边），小臂伸进水里"""
    p = Part(7, 12)
    p.shape("polygon", [(0, 0), (4, 0), (6, 7), (1, 7)], fill=1)
    p.d.line((1, 6, 6, 6), fill=0)
    p.dither([(3, 1), (6, 6), (4, 6)], 0.5, 0)
    p.shape("rectangle", (2, 7, 4, 11), fill=1)
    return p.sprite()


REED = pix.frames("""
 #
 #
###
#.#
###
 #   #
 #  #
 # #
## 
 #
 #
 #
---
  #
  #
 ###
 #.#
 ###
 #    #
 #   #
 #  #
 ##
 #
 #
 #
""")

CLOUD_S = pix.sprite("""
   ####
 ##....##  ##
#........##..#
 ##############
""")

FISH = pix.frames("""
 ###  #
#.####
 ###  #
---
  #
 ###
 #.#
 ###
 ###
 # #
""")

DRAGONFLY = pix.frames("""
## ##
 ###########
## ##
---
 # #
 ###########
 # #
""")

FLOATS = [pix.sprite("""
 # #
#.#.#
 ###
"""), pix.sprite("""
 ##
####.
 ##
"""), pix.sprite("""
 #
###
 #
###
###
""")]
"""水上漂的：桃花 / 落叶 / 小葫芦"""

FOOT = pix.sprite("""
 ##
####
 #.
""")


@register
class ZhenLiuRest(Rest):
    id = "x1.zhenliu"
    name = "枕石漱流"
    desc = "溪边小道士枕石仰卧，斗笠盖脸、跷着脚，一只手垂进流水里；鱼跃、漂花、蜻蜓停脚尖，浪花溅耳斗笠一跳"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.float0 = self.rng.randrange(3)

    # ------------------------------------------------------------ 景

    def scenery(self, g: Gfx, t: float):
        # 远山（虚线勾）
        pts = [(0, 30), (14, 20), (24, 24), (40, 12), (54, 22), (66, 18), (82, 26), (98, 14), (114, 22), (127, 18)]
        for a, b in zip(pts, pts[1:]):
            pix.dotted(g, *a, *b, 2, 0)
        for i, (x0, y) in enumerate(((20, 6), (80, 10))):
            x = (x0 + t * (1.2 + i * 0.5)) % 160 - 20
            pix.blit(g, CLOUD_S, x, y)
        self.willow(g, t)
        for i, x in enumerate((4, 10, 106, 113, 121)):     # 芦苇
            pix.blit(g, REED[int(t * 0.8 + i * 0.4) % 2], x - 1, BANK - 12 - (i % 2) * 2)
        pix.blit(g, cached("bank", _bank), 0, BANK)

    def willow(self, g: Gfx, t: float):
        """右上角探出一枝垂柳：枝条垂下随风摆，枝上一串叶点"""
        g.d.line((127, 0, 112, 3), fill=1), g.d.line((127, 1, 112, 4), fill=1)
        g.d.line((118, 2, 96, 6), fill=1)
        for i, (x0, y0, ln) in enumerate(((124, 1, 18), (116, 3, 24), (108, 5, 20), (100, 6, 14), (112, 4, 12))):
            sw = math.sin(t * 0.8 + i * 0.9)
            for j in range(ln):
                q = j / ln
                x = x0 + sw * q * q * 4 - q * 2
                y = y0 + j
                g.px(x, y)
                if j % 3 == 1:
                    g.px(x - 1, y + 1)

    def water(self, g: Gfx, t: float):
        """三层波纹从右往左流（越近越快），深处网点"""
        for row, (y, sp, gap, ln) in enumerate(((WATER + 2, 6, 16, 5), (WATER + 6, 10, 20, 7), (WATER + 10, 15, 24, 9))):
            off = (t * sp) % gap
            for i in range(-1, 128 // gap + 2):
                x = i * gap - off + (row * 7)
                g.d.line((x, y, x + ln, y), fill=1)
                if row == 2:
                    g.px(x + ln + 2, y)
        pix.checker(g, (0, WATER + 12, 128, 64), 0.125)

    def ripples(self, g: Gfx, t: float, x: float, y: float, period: float = 2.0, n: int = 2):
        for i in range(n):
            k = ((t / period) + i / n) % 1
            r = 1 + k * 7
            if k < 0.85:
                g.d.ellipse((x - r, y - r * 0.35, x + r, y + r * 0.35), outline=1)

    # ------------------------------------------------------------ 人

    def man(self, g: Gfx, t: float, hat_dy: float = 0.0, face: str = "sleep", foot: bool = True):
        h = supine(g, MAN_X, BANK, t, face=face, knee=True, arm="none")
        pix.blit(g, cached("stone", _stone), MAN_X - 3, BANK - 6)
        sway = math.sin(t * 1.3) * 1.0
        pix.blit(g, cached("arm", _arm), MAN_X + 20 + sway, BANK - 3)
        hx, hy = MAN_X + 23 + sway, WATER + 1
        bob = 0
        if foot:   # 跷着的脚：搭在膝头上，一点一点
            bob = 1 if (t * 1.6) % 1 < 0.5 else 0
            kx, ky = h["knee"]
            pix.blit(g, FOOT, kx + 1, ky - 3 - bob)
        # 斗笠盖在脸上（随呼吸微动）
        breath = 1 if (t / 3.6) % 1 < 0.5 else 0
        pix.blit(g, cached("hat", _hat), MAN_X - 1, BANK - 17 - breath - hat_dy)
        h["hand_in"] = (hx, hy)
        h["toe2"] = (h["knee"][0] + 3, h["knee"][1] - 4 - bob)
        return h

    # ------------------------------------------------------------ 事件

    def fish(self, g: Gfx, f: float):
        """鱼跃：从水里窜出、划个弧落回去，前后两圈涟漪"""
        x0, x1 = 118, 92
        if f < 1.4:
            q = f / 1.4
            x = lerp(x0, x1, q)
            y = WATER + 2 - math.sin(q * math.pi) * 16
            fr = FISH[0] if 0.3 < q < 0.7 else FISH[1]
            pix.blit(g, fr, x - 3, y - 2, flip=True)
            if q < 0.3:
                for j in range(3):
                    g.px(x0 + j * 2 - 2, WATER - 2 - q * 10 + j)
        if f < 0.8:
            self.ripples(g, f, x0, WATER + 2, 0.8, 1)
        if 1.3 < f < 3.0:
            self.ripples(g, f, x1, WATER + 2, 1.7, 1)
            if f < 1.7:
                for j in range(4):
                    g.px(x1 - 4 + j * 3, WATER - 1 - (f - 1.3) * 12 + abs(j - 1.5) * 2)

    def floater(self, g: Gfx, t: float, f: float):
        """漂过的东西：从右边顺水漂到左边，上下浮"""
        kind = (int(t // EV) + self.float0) % 3
        x = lerp(132, -8, f / 14.0)
        y = WATER + 4 + math.sin(f * 2.4) * 1
        pix.blit(g, FLOATS[kind], x, y - FLOATS[kind].h + 1)

    def dragonfly(self, g: Gfx, t: float, f: float, toe):
        tx, ty = toe
        if f < 2.5:
            q = ease_out(f / 2.5)
            x, y = lerp(140, tx, q), lerp(10, ty - 2, q) + math.sin(f * 8) * 2 * (1 - q)
            fr = DRAGONFLY[int(t * 20) % 2]
        elif f < 9.0:
            x, y = tx, ty - 2
            fr = DRAGONFLY[0] if int(f * 2) % 5 else DRAGONFLY[1]
        else:
            q = ease_in((f - 9.0) / 2.0)
            x, y = lerp(tx, 120, q), lerp(ty - 2, -10, q)
            fr = DRAGONFLY[int(t * 20) % 2]
        pix.blit(g, fr, x - 2, y - 1)

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        self.scenery(g, t)
        self.water(g, t)
        splash = ev(t, EV, 131.0, 8.0)
        hat_dy, face = 0.0, "sleep"
        if splash is not None and 0.6 < splash < 6.0:
            hat_dy = 6 * math.sin(min(span(splash, 0.6, 1.2), 1) * math.pi / 2) * (1 - span(splash, 5.0, 6.0))
            face = "wow"
        h = self.man(g, t, hat_dy, face)
        hx, hy = h["hand_in"]
        self.ripples(g, t, hx, hy + 1, 2.2, 2)
        f = ev(t, EV, 37.0, 3.0)
        if f is not None:
            self.fish(g, f)
        f = ev(t, EV, 53.0, 14.0)
        if f is not None:
            self.floater(g, t, f)
        f = ev(t, EV, 79.0, 11.0)
        if f is not None:
            self.dragonfly(g, t, f, h["toe2"])
        if splash is not None and splash < 1.4:    # 浪花溅到耳边
            for j in range(6):
                q = splash / 1.4
                x = MAN_X + 4 + j * 2 - q * 6
                y = WATER - math.sin(q * math.pi) * (10 + j * 2)
                g.px(x, y)
                if j % 2:
                    g.px(x + 1, y)
        w = ev(t, EV, 97.0, 9.0)
        if w is not None:
            vplate(g, 114, 4, "枕石漱流", n=int(w / 0.4) + 1)
        if splash is not None and 1.0 < splash < 7.0:
            plate(g, 64, 3, "枕流欲洗其耳", k=span(splash, 1.0, 1.3), align="center")
        self.matrix(g, t, ev(t, EV, 37.0, 3.0))

    def matrix(self, g: Gfx, t: float, fish=None):
        for row, (y, sp) in enumerate(((3, 2.0), (5, 3.0), (7, 4.5))):
            off = int(t * sp)
            for x in range(8):
                if (x + off + row) % 4 < 2:
                    g.mx[y, x] = True
        if fish is not None and fish < 1.4:
            q = fish / 1.4
            x = int(lerp(7, 0, q))
            y = int(round(3 - math.sin(q * math.pi) * 3))
            g.mx_set(x, y), g.mx_set(x + 1, y)
            g.mx_level = 3

    def enter(self, g: Gfx, t: float):
        """斗笠飘摆着落下，盖在脸上一弹；腿跷起来"""
        self.scenery(g, t)
        self.water(g, t)
        q = span(t, 0.2, 2.0)
        h = supine(g, MAN_X, BANK, t, face="sleep" if t > 1.9 else "open", knee=t > 2.3, arm="none")
        pix.blit(g, cached("stone", _stone), MAN_X - 3, BANK - 6)
        pix.blit(g, cached("arm", _arm), MAN_X + 20, BANK - 3)
        hx = lerp(70, MAN_X + 2, ease_in_out(q)) + math.sin(q * math.pi * 3) * 10 * (1 - q)
        hy = lerp(-8, BANK - 17, q)
        if q >= 1:
            hy -= math.sin(span(t, 2.0, 2.3) * math.pi) * 2
        hat = cached("hat", _hat)
        if q < 1 and int(t * 6) % 2:   # 飘摆时斜一斜
            hat = pix.stretch(hat, 0.9, 1.0)
        pix.blit(g, hat, hx - 3, hy)
        if t > 2.5:
            pix.blit(g, FOOT, h["knee"][0] + 1, h["knee"][1] - 3)
        self.matrix(g, t)
        iris(g, MAN_X + 20, BANK - 8, lerp(6, 150, ease_out(span(t, 0, 1.0))))

    def exit(self, g: Gfx, t: float):
        h0 = self.hold_t
        self.scenery(g, h0 + t)
        self.water(g, h0 + t)
        lift = ease_out(span(t, 0, 0.45)) * 14
        h = self.man(g, h0 + t, lift, "open" if t > 0.3 else "sleep")
        self.matrix(g, h0 + t)
        ex, ey = h["eye"]
        iris(g, ex, ey, lerp(140, 0, ease_in_out(span(t, 0.45, self.T["exit"] - 0.05))))
