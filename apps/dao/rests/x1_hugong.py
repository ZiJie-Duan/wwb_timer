"""壶中天：散了市，小道士学壶公纵身跳进肆头挂着的大葫芦，在壶里睡大觉，葫芦肚上的圆窗里别有天地。

依据：《后汉书·方术列传·费长房》：“市中有老翁卖药，悬一壶于肆头，及市罢，辄跳入壶中。市人莫之见，
唯长房于楼上睹见之。”长房随翁入壶，“唯见玉堂严丽，旨酒甘肴盈衍其中”。“悬壶济世”“壶中日月长”出此。

入场：小道士从左边走到药摊前，蹲一下、纵身一跳，越缩越小钻进葫芦口；葫芦一晃，肚上的圆窗亮起来，开始打鼾。
持续：屋檐瓦当、檐下横杆上挂着大葫芦（腰系红绳、垂穗、背光网点），药摊上药包、捣药臼，右边“药”字幌子随风摆，
      右上是酒楼的窗。葫芦随风微摆、随鼾声一鼓一鼓，葫芦口往外冒 Z；肚上圆窗里是壶中天地：
      小小的玉堂、日月轮转（15 秒换一次昼夜）、星。
      小事件（每 150 秒一轮）：打个嗝，葫芦一蹦，口里冒出一个泡“嗝”（41s）；楼上费长房（也是小道士）推窗探头偷看，
      “！”，“唯长房睹见”（67s）；“壶中日月长”（89s）。
退场：葫芦一抖，小道士从壶口“噗”地跳出来，落到街上，画面收拢。
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, _head, daoshi
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import bang, cached, ev, iris, plate, twinkle, zzz

FLOOR = 60
BEAM_Y = 13
HANG_X = 60         # 葫芦挂点
GOURD_TOP = 18      # 葫芦口顶（不摆时）
EV = 150.0
DAYN = 15.0


def _gourd():
    """大葫芦 34×40：上小下大两个肚，腰上系红绳打结、垂两缕穗；葫芦口一圈；右侧背光网点；
    下肚正中一扇圆窗（暗，外一圈亮框）"""
    p = Part(34, 40)
    p.shape("rectangle", (15, 0, 19, 3), fill=1)                  # 口
    p.d.line((15, 1, 19, 1), fill=0)
    p.shape("ellipse", (9, 2, 25, 18), fill=1)                    # 上肚
    p.shape("ellipse", (0, 14, 33, 39), fill=1)                   # 下肚
    p.shape("rectangle", (12, 15, 22, 18), fill=1)
    p.dither([(20, 4), (25, 10), (22, 16), (19, 10)], 0.5, 0)
    p.dither([(25, 17), (33, 26), (31, 35), (24, 38), (28, 27)], 0.5, 0)
    p.d.line((11, 16, 23, 16), fill=0)                            # 腰绳
    p.d.line((11, 17, 23, 17), fill=0)
    p.px(17, 16, 1)
    p.shape("line", (16, 18, 13, 23), fill=0), p.shape("line", (18, 18, 20, 23), fill=0)   # 穗
    p.px(12, 24, 0), p.px(21, 24, 0)
    p.d.line((12, 6, 12, 10), fill=0)                             # 上肚弧线
    p.d.arc((3, 18, 13, 36), 150, 210, fill=0)                    # 下肚弧线
    cx, cy, r = 17, 28, 9
    p.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0)         # 圆窗
    p.d.ellipse((cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1), outline=1)
    return p.sprite()


WIN = (17, 28, 7)   # 圆窗在葫芦里的中心与内半径

PALACE = pix.sprite("""
     #
 #########
#..#####..#
  #.....#
  #.#.#.#
  #.#.#.#
 #########
""")
"""壶里的玉堂：攒尖顶起翘、三开间、台基"""


def _eave():
    """屋檐 74×13：筒瓦一垄垄（亮），瓦当一排圆点，檐口一道暗边，檐下一根横杆伸出来挂葫芦"""
    p = Part(74, 13)
    p.shape("polygon", [(0, 0), (70, 0), (73, 7), (0, 7)], fill=0)
    for x in range(2, 70, 4):
        p.shape("rectangle", (x, 0, x + 1, 6), fill=1)
    p.shape("rectangle", (0, 7, 73, 8), fill=1)
    for x in range(3, 72, 4):                                     # 瓦当
        p.d.ellipse((x - 1, 8, x + 1, 10), fill=1)
        p.px(x, 9, 0)
    p.px(73, 6, 1), p.px(73, 5, 1)
    return p.sprite()


def _stall():
    """药摊 44×16：案板（亮面 + 暗前脸、两条腿），上面三个药包（纸包十字绳）、一只捣药臼带杵"""
    p = Part(44, 16)
    p.shape("rectangle", (0, 6, 43, 8), fill=1)
    p.d.line((1, 7, 42, 7), fill=0)
    p.shape("rectangle", (2, 9, 41, 11), fill=0)
    p.d.rectangle((2, 9, 41, 11), outline=1)
    p.shape("rectangle", (3, 12, 5, 15), fill=1), p.shape("rectangle", (38, 12, 40, 15), fill=1)
    for x in (4, 12):                                             # 药包
        p.shape("polygon", [(x, 5), (x + 2, 1), (x + 5, 1), (x + 7, 5)], fill=1)
        p.d.line((x + 3, 1, x + 3, 5), fill=0), p.d.line((x + 1, 3, x + 6, 3), fill=0)
        p.px(x + 3, 0, 1)
    p.shape("polygon", [(21, 5), (22, 3), (26, 3), (27, 5)], fill=1)
    p.d.line((24, 3, 24, 5), fill=0)
    p.shape("polygon", [(32, 0), (40, 0), (39, 5), (33, 5)], fill=1)   # 臼
    p.d.line((33, 2, 39, 2), fill=0)
    p.shape("line", (35, 0, 38, -4), fill=1)
    p.shape("line", (37, -1, 41, -6), fill=1, width=2)              # 杵
    return p.sprite()


def _banner():
    """幌子 16×26：竿头、横挑、布幌（亮框暗心，留空写“药”），下摆三条飘带"""
    p = Part(16, 26)
    p.shape("rectangle", (0, 0, 15, 1), fill=1)
    p.shape("rectangle", (1, 2, 14, 19), fill=0)
    p.d.rectangle((1, 2, 14, 19), outline=1)
    for x in (2, 7, 12):
        p.shape("polygon", [(x, 20), (x + 2, 20), (x + 2, 24), (x + 1, 25), (x, 24)], fill=1)
    return p.sprite()


def _tower():
    """酒楼一角 34×24：楼檐（起翘）、木板墙、一扇支摘窗（可推开）"""
    p = Part(34, 24)
    p.shape("polygon", [(0, 6), (34, 6), (34, 3), (4, 3), (0, 1)], fill=1)
    p.d.line((2, 5, 33, 5), fill=0)
    p.shape("rectangle", (2, 7, 33, 23), fill=0)
    for x in range(5, 34, 5):
        p.d.line((x, 8, x, 23), fill=1)
    p.d.rectangle((9, 10, 25, 21), fill=0, outline=1)             # 窗框
    return p.sprite()


def _shutter(open_k: float) -> Sprite:
    """支摘窗的窗扇 17×12：格子；open_k 推开的程度（0 关 → 1 支起来）"""
    h = max(2, int(round(12 * (1 - open_k * 0.75))))
    p = Part(17, h)
    p.shape("rectangle", (0, 0, 16, h - 1), fill=1)
    p.d.rectangle((1, 1, 15, h - 2), fill=0)
    for x in (5, 11):
        p.d.line((x, 1, x, h - 2), fill=1)
    if h > 5:
        p.d.line((1, h // 2, 15, h // 2), fill=1)
    return p.sprite()


def _sprite_of(draw, w: int, h: int) -> Sprite:
    """把一段画法（在 w×h 的临时画布上）拍成精灵：外面透明，里面（含暗部）不透明"""
    g = Gfx()
    g.clear()
    draw(g)
    on = g.array()[:h, :w]
    im = Image.fromarray(~on)
    ImageDraw.floodfill(im, (0, 0), 0)
    inside = np.array(im, bool) | on
    return Sprite(on=on.copy(), mask=inside)


def man_sprite(pose: str, face: str = "normal") -> Sprite:
    def draw(g):
        daoshi(g, 12, 37, pose, 0.0, face=face, bob=False)
    return cached(("man", pose, face), lambda: _sprite_of(draw, 26, 38))


@register
class HuGongRest(Rest):
    id = "x1.hugong"
    name = "壶中天"
    desc = "散了市，小道士纵身跳进肆头挂的大葫芦里睡觉，葫芦随鼾声一鼓一鼓，肚上圆窗里日月轮转；楼上有人偷看"
    T = {"enter": 3.4, "exit": 1.3}

    # ------------------------------------------------------------ 景

    def street(self, g: Gfx, t: float, peek=None):
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        for x in range(0, 140, 10):                              # 石板路
            g.d.line((x, FLOOR + 1, x - 3, 63), fill=1)
        pix.blit(g, cached("tower", _tower), 94, 0)
        k = 0.0
        if peek is not None:
            k = span(peek, 0, 0.6) * (1 - span(peek, 7.4, 8.0))
        if k > 0.05:   # 费长房探头
            hd = cached(("ph", peek is not None and 0.8 < peek < 2.4),
                        lambda: _head(False, 0, False, "wow" if peek is not None and 0.8 < peek < 2.4 else "normal")[0])
            pix.blit(g, hd, 108 - 0, 22 - int(k * 9), flip=True)
            g.d.rectangle((103, 22, 119, 23), fill=1)
        sh = cached(("sh", round(k, 1)), lambda: _shutter(round(k, 1)))
        pix.blit(g, sh, 103, 10)
        pix.blit(g, cached("eave", _eave), 0, 0)
        g.d.line((0, BEAM_Y, HANG_X + 8, BEAM_Y), fill=1)          # 横杆
        g.d.line((0, BEAM_Y + 1, HANG_X + 8, BEAM_Y + 1), fill=1)
        g.d.line((HANG_X + 8, BEAM_Y, HANG_X + 9, BEAM_Y + 1), fill=1)
        pix.blit(g, cached("stall", _stall), 2, FLOOR - 16)
        sway = math.sin(t * 1.1) * 1.5                           # 幌子随风摆
        pix.blit(g, cached("banner", _banner), 100 + sway, 30)
        g.d.line((99, 30, 116, 30), fill=1)
        g.d.line((116, 26, 116, FLOOR), fill=1)                  # 竿
        self._sway = sway

    def label(self, g: Gfx, ir=None):
        """幌子上的“药”（每帧最后画）；ir=(cx, cy, r)：圆形收拢时字不完整在圈里就不画"""
        sway = getattr(self, "_sway", 0.0)
        if ir is not None:
            cx, cy, r = ir
            if any(math.hypot(x - cx, y - cy) > r - 2 for x in (101 + sway, 115 + sway) for y in (33, 48)):
                return
        g.d.rectangle((102 + sway, 33, 113 + sway, 48), fill=0)
        g.text(101 + 7.5 + sway, 35, "药", align="center")

    def gourd(self, g: Gfx, t: float, hop: float = 0.0, bump: float = 0.0, lit: float = 1.0):
        """挂着的葫芦：随风摆（整体平移，绳子斜），随鼾声一鼓一鼓；返回 (口 x, 口 y, 窗心 x, 窗心 y)"""
        sway = math.sin(t * 0.8) * 2.0
        breath = (t / 3.6) % 1
        puff = math.sin(breath * math.pi) if breath < 0.5 else 0.0
        spr = cached("gourd", _gourd)
        sx = 1.0 + (round(puff * 0.08 * 10) / 10 if puff > 0.3 else 0) + bump * 0.1
        s2 = pix.stretch(spr, sx, 1.0)
        gx = HANG_X + sway - s2.w / 2
        gy = GOURD_TOP - hop
        g.d.line((HANG_X, BEAM_Y + 1, HANG_X + sway, gy), fill=1)   # 红绳
        pix.blit(g, s2, gx, gy)
        wx, wy = gx + WIN[0] * sx, gy + WIN[1] - 3
        self.window(g, t, wx, wy, lit)
        return HANG_X + sway, gy, wx, wy

    def window(self, g: Gfx, t: float, cx: float, cy: float, lit: float):
        """圆窗里的壶中天地：小殿（屋顶、两柱）、日月轮转、星"""
        if lit <= 0:
            return
        cx, cy = int(round(cx)), int(round(cy))
        day = (t // DAYN) % 2 == 0
        k = (t % DAYN) / DAYN
        ax = cx - 5 + int(k * 10)                                  # 日月从左往右走一道弧
        ay = cy - 2 - int(math.sin(k * math.pi) * 3)
        if day:
            g.d.rectangle((ax - 1, ay - 1, ax + 1, ay + 1), fill=1)
            if int(t * 2) % 2:
                g.px(ax, ay - 3), g.px(ax - 3, ay), g.px(ax + 3, ay)
        else:
            g.px(ax, ay - 1), g.px(ax - 1, ay), g.px(ax - 1, ay + 1), g.px(ax, ay + 2)
            for i, (dx, dy) in enumerate(((-4, -3), (4, -4), (3, -1), (-2, -5))):
                if (t * 0.7 + i * 0.3) % 1 < 0.7:
                    g.px(cx + dx, cy + dy)
        pix.blit(g, PALACE, cx - 5, cy + 1, outline=False)
        g.d.line((cx - 7, cy + 7, cx + 7, cy + 7), fill=1)

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        peek = ev(t, EV, 67.0, 8.0)
        self.street(g, t, peek)
        hic = ev(t, EV, 41.0, 4.0)
        hop = 0.0
        if hic is not None and hic < 0.5:
            hop = math.sin(hic / 0.5 * math.pi) * 4
            if hic < 0.15:
                pix.shake(g, t, 1.0)
        mx, my, wx, wy = self.gourd(g, t, hop)
        if hic is not None and 0.2 < hic < 3.0:   # 口里冒出一个泡
            r = min(1.0, (hic - 0.2) * 3) * 4
            bx, by = mx + 2, my - 6 - (hic - 0.2) * 3
            g.d.ellipse((bx - r, by - r, bx + r, by + r), fill=0, outline=1)
            if r > 3:
                g.px(bx - 1, by - 2)
        else:
            zzz(g, mx + 3, my + 1, t, n=3, period=2.6, dx=24, dy=-3)
        if peek is not None and 0.8 < peek < 2.4:
            bang(g, 98, 12)
        if hic is not None and 0.4 < hic < 3.0:
            plate(g, 38, 22, "嗝", k=span(hic, 0.4, 0.6), align="center")
        if peek is not None and 2.0 < peek < 8.0:
            plate(g, 34, 18, "唯长房睹见", k=span(peek, 2.0, 2.3), align="center")
        w = ev(t, EV, 89.0, 8.0)
        if w is not None:
            plate(g, 34, 18, "壶中日月长", k=span(w, 0, 0.4), align="center")
        self.label(g)
        self.matrix(g, t)

    def matrix(self, g: Gfx, t: float, bump: float = 0.0):
        breath = (t / 3.6) % 1
        wide = breath < 0.5 and math.sin(breath * math.pi) > 0.3 or bump > 0
        g.mx_rows([0x18, 0x18, 0x3C, 0x3C, 0x18, 0x7E if not wide else 0xFF, 0x7E if not wide else 0xFF, 0x3C])
        k = (t / 2.6) % 1
        g.mx_set(4 + int(k * 3), 1 - int(k * 2))

    def enter(self, g: Gfx, t: float):
        """走到摊前 → 一蹲 → 纵身一跳，越缩越小钻进葫芦口 → 葫芦一晃，圆窗亮起"""
        self.street(g, 0.0)
        mx, my = HANG_X, GOURD_TOP
        x = lerp(-10, 50, ease_out(span(t, 0, 1.3)))
        if t < 1.3:
            daoshi(g, x, FLOOR, "walk", t)
            self.gourd(g, 0.0, lit=0)
        elif t < 1.7:
            spr = man_sprite("idle")
            s = pix.stretch(spr, 1.2, 0.8)                     # 蹲：压扁
            self.gourd(g, 0.0, lit=0)
            pix.blit(g, s, 50 - s.w / 2, FLOOR - s.h)
        elif t < 2.5:
            q = span(t, 1.7, 2.5)
            sc = lerp(1.0, 0.15, ease_out(q))
            spr = man_sprite("raise")
            s = pix.stretch(spr, max(sc * 0.9, 0.1), max(sc * 1.15, 0.1))
            px = lerp(50, mx, q)
            py = lerp(FLOOR, my + 3, ease_in_out(q)) - math.sin(q * math.pi) * 8
            self.gourd(g, 0.0, lit=0)
            pix.blit(g, s, px - s.w / 2, py - s.h)
        else:
            q = span(t, 2.5, 3.4)
            self.gourd(g, 0.0 + math.sin(q * 12) * (1 - q) * 3, bump=(1 - q), lit=1 if q > 0.4 else 0)
            if q < 0.3:
                for i in range(5):
                    a = i * 1.25
                    g.px(mx + math.cos(a) * (3 + q * 20), my - 2 + math.sin(a) * (2 + q * 10))
        r = lerp(6, 150, ease_out(span(t, 0, 1.0)))
        self.label(g, (50, 36, r))
        self.matrix(g, t, 1 if 2.5 < t < 3.0 else 0)
        iris(g, 50, 36, r)

    def exit(self, g: Gfx, t: float):
        """葫芦一抖，小道士“噗”地从壶口跳出来，落到街上"""
        h0 = self.hold_t
        self.street(g, h0)
        q = span(t, 0.15, 0.8)
        mx, my, wx, wy = self.gourd(g, h0 + (math.sin(t * 40) * 0.2 if t < 0.15 else 0), bump=1 if t < 0.3 else 0)
        if q > 0:
            sc = lerp(0.2, 1.0, ease_out(q))
            spr = man_sprite("raise" if q < 1 else "idle", "happy")
            s = pix.stretch(spr, max(sc, 0.1), max(sc, 0.1))
            px = lerp(mx, 40, q)
            py = lerp(my + 4, FLOOR, ease_in(q)) - math.sin(q * math.pi) * 4
            pix.blit(g, s, px - s.w / 2, py - s.h)
        if 0.15 < t < 0.4:
            for i in range(6):
                a = i * 1.05
                g.px(mx + math.cos(a) * (3 + (t - 0.15) * 30), my - 2 + math.sin(a) * (2 + (t - 0.15) * 14))
        r = lerp(140, 0, ease_in_out(span(t, 0.8, self.T["exit"] - 0.03)))
        self.label(g, (40, FLOOR - 18, r))
        self.matrix(g, t, 1)
        iris(g, 40, FLOOR - 18, r)
