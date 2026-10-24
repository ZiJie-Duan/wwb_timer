"""枕石漱流：隐士在溪边枕着石头仰卧，斗笠盖脸、跷着二郎腿，一只手垂在水里；
溪水长流，鱼跃、落花漂过、蜻蜓停在脚尖；偶尔浪花溅上耳朵，斗笠一跳——“枕流，欲洗其耳”。

依据：《世说新语·排调》：孙子荆年少时欲隐，语王武子“当枕石漱流”，误曰“漱石枕流”。王曰：“流可枕，石可漱乎？”
孙曰：“所以枕流，欲洗其耳；所以漱石，欲砺其齿。”（“枕石漱流”遂为隐居山林的代称）
"""
from __future__ import annotations

import math

from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_bounce, lerp, noise, rand, span
from ..engine.fx import brush_reveal, cloud, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Pen, backdrop, breathe, ev, halo, iris, zzz

BANK = 45          # 岸面
WATER = 51         # 水面
HAT = (34, 37)     # 斗笠尖下方（脸）
HAND = (60, 55)    # 垂在水里的手
HIP = (74, BANK - 6)
KNEE = (86, BANK - 19)
FOOT = (100, BANK - 17)   # 跷起的脚尖


def _bg():
    p = Pen()
    # 远山（淡）
    ridge = [(0, 21), (12, 13), (24, 18), (40, 8), (56, 16), (70, 11), (86, 19), (100, 14), (128, 21)]
    p.line(ridge)
    for (x0, y0), (x1, y1) in zip(ridge, ridge[1:]):  # 山脊下一排疏点（远山的皴）
        for k in range(0, 10, 3):
            x = x0 + (x1 - x0) * k / 10
            p.px(x, y0 + (y1 - y0) * k / 10 + 3)
    # 岸：从左边伸到溪里，土坡抖动
    p.poly([(0, BANK), (96, BANK), (104, WATER), (0, WATER)], fill=0)
    p.poly([(0, BANK + 2), (96, BANK + 2), (101, WATER - 1), (0, WATER - 1)], fill=0.35, outline=None)
    p.line([(0, BANK), (96, BANK), (104, WATER)])
    # 枕石
    p.ellipse((14, BANK - 9, 34, BANK + 2), fill=0.55)
    p.arc((17, BANK - 7, 28, BANK), 200, 290)
    # 岸草
    for x in (4, 10):
        p.line([(x, BANK), (x - 2, BANK - 4)])
        p.line([(x + 1, BANK), (x + 2, BANK - 5)])
    return p.image()


def _body() -> Sprite:
    """仰卧的身子（头、腿另画）：头在左，胯在右"""
    p = Pen(46, 14)
    y0 = 13
    p.poly([(0, 5), (8, 3), (26, 3), (36, 4), (44, 6), (45, y0), (0, y0)], fill=0)
    p.line([(18, 3), (18, y0)])               # 腰带
    p.line([(20, 3), (20, y0)])
    p.line([(26, 7), (40, 8)])                # 衣褶
    p.line([(6, 9), (14, 10)])
    p.poly([(2, 6), (12, 5), (16, 8), (5, 10)], fill=0.5)   # 枕在脑后的胳膊
    return p.sprite()


def _hat() -> Sprite:
    """斗笠（竹编，盖在脸上）"""
    p = Pen(26, 11)
    p.poly([(0, 10), (13, 0), (25, 10)], fill=0.45)
    p.line([(0, 10), (25, 10)])
    for x in (6, 13, 19):
        p.line([(13, 1), (x, 9)])
    p.rect((12, 0, 14, 1), fill=1)
    return p.sprite()


DRAGONFLY = halo(Sprite("""
  ..#.#..
  ###.###
  ..###..
  ...#...
  ...#...
  ...#...
"""))
FISH = [Sprite("""
  ..##...
  .####.#
  #######
  .####.#
  ..##...
"""), Sprite("""
  ...##..
  #.####.
  #######
  #.####.
  ...##..
""")]

FLOATS = ("peach", "leaf", "gourd")

_A = {}


def _assets():
    if not _A:
        _A.update(bg=_bg(), body=_body(), hat=_hat())


@register
class ZhenLiu(Rest):
    id = "x1.zhenliu"
    name = "枕石漱流"
    desc = "溪边隐士枕石仰卧、斗笠盖脸跷着脚，手垂在水里；鱼跃、落花漂过、蜻蜓停脚尖，浪花溅耳斗笠一跳"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        _assets()
        self._ht = 0.0

    # ------------------------------------------------------------ 零件

    def water(self, g: Gfx, t: float):
        """溪水：一道道波纹从右往左流"""
        for i in range(16):
            row = i % 4
            y = WATER + 2 + row * 3
            sp = 9 + row * 3
            x = (rand(i, 7) * 150 - t * sp) % 150 - 12
            w = 4 + int(rand(i, 8) * 6)
            g.d.line((x, y, x + w, y), fill=1)
        g.d.line((0, WATER, 104, WATER), fill=1)

    def clouds(self, g: Gfx, t: float):
        for i in range(2):
            x = (i * 74 + 20 - t * (1.2 + i * 0.5)) % 170 - 22
            cloud(g, x, 5 + i * 4, 22 - i * 4, 7, seed=self.seed + i)

    def reeds(self, g: Gfx, t: float):
        """岸尖上几丛短芦苇，随风轻摆"""
        for i, (x, h) in enumerate(((104, 12), (108, 16), (112, 10), (117, 14))):
            sw = math.sin(t * 0.9 + i * 1.3) * 1.5
            pts = [(x + sw * (k / 4) ** 2 + k * 0.6, WATER + 1 - h * k / 4) for k in range(5)]
            g.d.line(pts, fill=1)
            tx, ty = pts[-1]
            if i % 2:
                g.d.line((tx, ty, tx + 2, ty - 3), fill=1, width=2)   # 芦花
            else:
                g.d.line((pts[2][0], pts[2][1], pts[2][0] + 4, pts[2][1] - 1), fill=1)  # 叶

    def hermit(self, g: Gfx, t: float, hat_dy: float = 0.0, foot: float | None = None, face: str = ""):
        g.blit(_A["body"], 30, BANK - 13)
        if breathe(t, 4.8) > 0.5:
            g.d.line((40, BANK - 11, 54, BANK - 11), fill=1)
        bob = (math.sin(t * 2.2) * 1.5) if foot is None else foot
        self.legs(g, bob)
        # 垂到水里的手（随水晃）
        sw = math.sin(t * 1.3) * 1.2
        g.d.line((60, BANK - 6, HAND[0] + sw, WATER + 2), fill=1, width=2)
        g.d.ellipse((HAND[0] - 1 + sw, WATER + 1, HAND[0] + 2 + sw, WATER + 4), fill=1)
        if int(t * 2) % 3 == 0:
            g.d.arc((HAND[0] - 5 + sw, WATER - 1, HAND[0] + 7 + sw, WATER + 3), 0, 180, fill=1)
        # 头和斗笠
        g.d.ellipse((24, BANK - 15, 36, BANK - 4), fill=0, outline=1)
        if face == "wide":
            g.d.rectangle((27, BANK - 12, 28, BANK - 11), fill=1)
            g.d.rectangle((31, BANK - 12, 32, BANK - 11), fill=1)
            g.d.ellipse((29, BANK - 8, 31, BANK - 6), outline=1)
        g.blit(_A["hat"], 17, BANK - 23 - hat_dy)

    def legs(self, g: Gfx, bob: float):
        """一条腿屈膝立着，另一条跷在膝上，脚尖一点一点"""
        foot = (FOOT[0], FOOT[1] + bob)
        for pts, w in (([HIP, KNEE, (KNEE[0] + 4, BANK - 1)], 4), ([HIP, (KNEE[0] - 1, KNEE[1] + 2), foot], 4)):
            g.d.line(pts, fill=0, width=w + 2)
            g.d.line(pts, fill=1, width=w)
            g.d.line(pts, fill=0, width=1)
        g.d.rectangle((KNEE[0] + 2, BANK - 3, KNEE[0] + 8, BANK - 1), fill=1)     # 着地的鞋
        g.d.polygon([(foot[0] - 1, foot[1] - 3), (foot[0] + 5, foot[1] - 4), (foot[0] + 5, foot[1] + 1),
                     (foot[0] - 1, foot[1] + 2)], fill=1)                          # 跷着的鞋

    def floater(self, g: Gfx, t: float, k: int, u: float):
        """漂过的东西：桃花、落叶、葫芦（从右往左）"""
        kind = FLOATS[int(rand(k, self.seed) * 3)]
        x = 134 - u * 11
        y = WATER - 1 + math.sin(u * 2.4) * 0.8
        if kind == "peach":
            for a in range(5):
                ang = a / 5 * 2 * math.pi + u * 0.5
                g.d.ellipse((x + math.cos(ang) * 2.4 - 1, y - 2 + math.sin(ang) * 1.2 - 1,
                             x + math.cos(ang) * 2.4 + 1, y - 2 + math.sin(ang) * 1.2 + 1), fill=1)
            g.px(x, y - 2, 0)
        elif kind == "leaf":
            g.d.polygon([(x - 5, y), (x, y - 3), (x + 5, y), (x, y + 1)], fill=1)
            g.d.line((x - 5, y - 1, x + 5, y - 1), fill=0)
            g.d.line((x + 5, y, x + 7, y - 2), fill=1)
        else:
            g.d.ellipse((x - 4, y - 5, x + 4, y + 2), fill=0, outline=1)
            g.d.ellipse((x - 2, y - 9, x + 2, y - 4), fill=0, outline=1)
            g.d.line((x, y - 9, x + 1, y - 11), fill=1)
            g.d.line((x - 4, y - 4, x + 4, y - 4), fill=1)
        if int(u * 3) % 2:
            g.d.line((x + 6, y + 2, x + 10, y + 2), fill=1)

    def mx_water(self, g: Gfx, t: float):
        for r, sp in ((5, 3.0), (6, 4.0), (7, 5.0)):
            off = int(t * sp)
            for x in range(8):
                g.mx[r, x] = (x + off + r) % 4 < 2

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        """斗笠从上面飘下来，盖到脸上；脚跷起来"""
        backdrop(g, _A["bg"])
        self.clouds(g, 0)
        self.water(g, t)
        self.reeds(g, t)
        k = span(t, 0.3, 2.2)
        if k < 1:  # 斗笠飘落（左右摆）
            hx = 17 + math.sin(k * 7) * 10 * (1 - k)
            hy = lerp(-14, BANK - 23, ease_in_out(k))
            g.blit(_A["body"], 30, BANK - 13)
            self.legs(g, 6 - 6 * span(t, 1.5, 2.2))
            g.d.ellipse((24, BANK - 15, 36, BANK - 4), fill=0, outline=1)
            g.d.line((27, BANK - 11, 29, BANK - 11), fill=1)
            g.d.line((31, BANK - 11, 33, BANK - 11), fill=1)
            g.d.line((60, BANK - 6, HAND[0], WATER + 2), fill=1, width=2)
            g.blit(_A["hat"], hx, hy)
        else:
            self.hermit(g, t - 2.2, hat_dy=2 * (1 - ease_out_bounce(span(t, 2.2, 2.6))))
            zzz(g, 30, BANK - 24, t - 2.4, self.seed, rise=16, drift=8, on=0.9) if t > 2.4 else None
        self.mx_water(g, t)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        backdrop(g, _A["bg"])
        self.clouds(g, t)
        ear = ev(t, 131.0, 7.0, 60.0)          # 浪花溅耳：斗笠一跳
        self.water(g, t)
        fl = ev(t, 53.0, 13.0, 8.0)            # 漂过的东西
        if fl:
            self.floater(g, t, fl[0], fl[1])
        fish = ev(t, 37.0, 2.2, 25.0)          # 鱼跃
        hat_dy, face = 0.0, ""
        if ear:
            u = ear[1]
            hat_dy = 12 * math.sin(math.pi * span(u, 0.4, 1.4)) if u < 1.4 else 0
            face = "wide" if 0.4 < u < 2.2 else ""
        self.hermit(g, t, hat_dy=hat_dy, face=face)
        self.reeds(g, t)
        if fish:
            self.fish(g, fish[0], fish[1])
        fly = ev(t, 79.0, 12.0, 40.0)          # 蜻蜓停在脚尖
        if fly:
            self.dragonfly(g, t, fly[1])
        if ear:
            self.splash(g, ear[1])
        else:
            zzz(g, 30, BANK - 24, t, self.seed, rise=16, drift=8, every=1.7)
        q = ev(t, 97.0, 10.0, 3.0)             # 题字
        if q and not ear:
            self.title(g, q[1])
        self.mx_water(g, t)
        if fish and fish[1] < 1.4:
            k = fish[1] / 1.4
            g.mx_set(int(2 + k * 4), int(4 - math.sin(k * math.pi) * 4))
            g.mx_set(int(3 + k * 4), int(4 - math.sin(k * math.pi) * 4))

    def title(self, g: Gfx, u: float):
        a = span(u, 0, 3.0)
        if u > 8.5:
            g.fade(1 - span(u, 8.5, 10.0), (110, 0, 128, 50))
            return
        g.d.rectangle((111, 0, 127, 49), fill=0)
        brush_reveal(g, 114, 2, "枕石漱流", a, vertical=True)

    def fish(self, g: Gfx, k: int, u: float):
        x0 = 70 + rand(k, self.seed + 3) * 30
        if u < 1.4:
            q = u / 1.4
            x = x0 - q * 18
            y = WATER - math.sin(q * math.pi) * 16
            g.blit(FISH[int(u * 8) % 2], x - 3, y - 2)
            if q < 0.2 or q > 0.85:  # 出水、入水的水花
                xx = x0 if q < 0.2 else x0 - 18
                for j in range(5):
                    g.px(xx - 4 + j * 2, WATER - 2 - (j % 2) * 2)
        else:  # 涟漪
            r = (u - 1.4) * 10
            g.d.ellipse((x0 - 18 - r, WATER + 1, x0 - 18 + r, WATER + 3 + r * 0.2), outline=1)

    def dragonfly(self, g: Gfx, t: float, u: float):
        fx, fy = FOOT[0] + 2, FOOT[1] - 8 + math.sin(t * 2.2) * 1.5   # 跟着脚一起晃
        if u < 3:
            q = ease_out(u / 3)
            x, y = lerp(140, fx, q), lerp(10, fy, q) + math.sin(u * 9) * 2 * (1 - q)
        elif u < 9:
            x, y = fx, fy
        else:
            q = ease_in((u - 9) / 3)
            x, y = lerp(fx, -10, q), lerp(fy, 4, q)
        spr = DRAGONFLY
        g.blit(spr, x - 3, y - 2)
        if u < 3 or u > 9:  # 翅膀扇动的残影
            if int(u * 20) % 2:
                g.d.line((x - 4, y + 1, x + 4, y + 1), fill=1)

    def splash(self, g: Gfx, u: float):
        """一个浪头溅到耳边"""
        if u < 1.3:
            for j in range(12):
                k = span(u, j * 0.03, 0.9 + j * 0.03)
                if 0 < k < 1:
                    x = 46 - j * 2 - k * 8
                    y = WATER - math.sin(k * math.pi) * (14 + j * 1.2)
                    g.d.rectangle((x, y, x + 1, y + 1), fill=1)
        if 1.0 < u < 6.5:
            g.d.rectangle((52, 0, 127, 13), fill=0)
            typewriter(g, 126, 1, "枕流欲洗其耳", u - 1.0, cps=5, align="right")

    def exit(self, g: Gfx, t: float):
        """醒来：掀开斗笠，画面收拢"""
        h = self._ht
        backdrop(g, _A["bg"])
        self.clouds(g, h)
        self.water(g, h + t)
        self.reeds(g, h + t)
        lift = ease_out(span(t, 0, 0.45))
        self.hermit(g, h, hat_dy=lift * 9, face="wide" if t > 0.25 else "")
        self.mx_water(g, h + t)
        iris(g, 30, BANK - 10, lerp(115, 0, ease_in_out(span(t, 0.4, self.T["exit"] - 0.05))), 0.8)
