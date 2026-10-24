"""庄周梦蝶：庄子倚树而眠，梦里化作一只蝴蝶，栩栩然飞来飞去；偶尔物化——画面翻转，换成蝴蝶在睡、小小的庄周在飞。

依据：《庄子·齐物论》：“昔者庄周梦为胡蝶，栩栩然胡蝶也，自喻适志与！不知周也。俄然觉，则蘧蘧然周也。
不知周之梦为胡蝶与，胡蝶之梦为周与？周与胡蝶，则必有分矣。此之谓物化。”
"""
from __future__ import annotations

import math

from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Pen, backdrop, breathe, ev, halo, iris, zzz

GROUND = 58
HEAD = (33, 28)      # 头（左上角）
NOSE = (43, 35)
FLOWERS = ((92, 40), (110, 46), (121, 38))   # 花心

FLY = [halo(Sprite(s)) for s in ("""
  #.....#
  ##...##
  ###.###
  #######
  .##.##.
  .#...#.
""", """
  .......
  ##...##
  ###.###
  .#####.
  .##.##.
  .......
""", """
  .......
  .......
  .##.##.
  ..###..
  ..#.#..
  .......
""")]
# 点阵上的蝴蝶（两帧）
MX_FLY = ["""
#......#
##.#.###
###.####
.######.
..####..
.##..##.
.#....#.
........
""", """
........
........
.##.###.
..####..
..####..
..#..#..
........
........
"""]


def _bg(tree: bool = True):
    p = Pen()
    if tree:
        _tree(p)
    _meadow(p)
    if not tree:  # 物化后的世界：一朵大花托着睡着的蝴蝶
        p.line([(104, 48), (102, GROUND)])
        p.line([(103, 54), (98, 50)])
        p.chord((92, 40, 116, 54), 0, 180, fill=0.5)
    return p.image()


def _tree(p: Pen):
    # 树冠
    p.blob([(-10, -12, 36, 16), (14, -14, 54, 10), (-6, 2, 24, 22), (30, -4, 56, 16), (40, -6, 64, 8)], fill=0.3)
    for x, y in ((8, 6), (22, 2), (36, 8), (48, 2), (14, 14)):
        p.arc((x - 3, y - 2, x + 3, y + 2), 200, 340)
    # 树干（人靠在右侧）
    p.poly([(10, GROUND), (13, 40), (14, 18), (18, 12), (22, 16), (22, 40), (26, GROUND)], fill=0.55)
    p.line([(17, 22), (16, 36)], 0)
    p.line([(20, 30), (21, 44)], 0)
    p.line([(22, 30), (30, 22), (36, 20)])  # 一根树枝


def _meadow(p: Pen):
    # 地面、草
    p.line([(0, GROUND), (128, GROUND)])
    for x in (4, 60, 72, 84, 98, 116):
        p.line([(x, GROUND), (x - 2, GROUND - 4)])
        p.line([(x + 1, GROUND), (x + 3, GROUND - 3)])
    # 花
    for i, (x, y) in enumerate(FLOWERS):
        p.line([(x, y + 2), (x + (1 if i % 2 else -1), GROUND)])
        p.line([(x, GROUND - 5), (x + 3, GROUND - 8)])
        for a in range(5):
            ang = a / 5 * 2 * math.pi + i
            p.ellipse((x + math.cos(ang) * 2.6 - 1.5, y + math.sin(ang) * 2.6 - 1.5,
                       x + math.cos(ang) * 2.6 + 1.5, y + math.sin(ang) * 2.6 + 1.5), fill=0)
        p.px(x, y)
    for i in range(10):
        p.px(int(rand(i, 3) * 128), GROUND + 2 + int(rand(i, 4) * 5))


def _body() -> Sprite:
    """倚树而坐（面朝右，屈膝，两手笼袖搭在膝上）"""
    p = Pen(34, 30)
    y0 = 29
    p.poly([(0, 4), (8, 2), (13, 8), (16, 14), (26, 12), (31, 16), (33, y0), (0, y0)], fill=0)
    p.line([(17, 16), (16, y0)])                      # 小腿
    p.rect((29, y0 - 3, 33, y0), fill=1)              # 鞋
    p.poly([(5, 6), (11, 6), (20, 12), (25, 17), (18, 21), (8, 16)], fill=0.45)   # 笼袖
    p.line([(4, 19), (12, 21)])                       # 衣褶
    p.line([(3, 24), (13, 25)])
    p.line([(21, 22), (28, 22)])
    return p.sprite()


def _head(awake: bool) -> Sprite:
    p = Pen(14, 14)
    p.ellipse((1, 2, 12, 13), fill=0)
    p.ellipse((0, 0, 5, 5), fill=1)          # 发髻
    p.line([(4, 3), (11, 3), (12, 5)])        # 发际
    if awake:
        p.rect((5, 7, 6, 8), fill=1)
        p.rect((9, 7, 10, 8), fill=1)
    else:
        p.line([(5, 8), (7, 8)])
        p.line([(9, 8), (11, 8)])
    p.px(8, 11)
    return p.sprite()


def _tiny_zhou(f: int) -> Sprite:
    """物化后：小小的庄周扇着宽袖在飞"""
    p = Pen(15, 12)
    p.ellipse((5, 0, 9, 4), fill=0)
    p.px(7, 0)
    p.poly([(5, 5), (9, 5), (10, 11), (4, 11)], fill=0)
    if f:
        p.poly([(5, 5), (0, 1), (1, 6)], fill=1)
        p.poly([(9, 5), (14, 1), (13, 6)], fill=1)
    else:
        p.poly([(5, 5), (0, 9), (2, 10)], fill=1)
        p.poly([(9, 5), (14, 9), (12, 10)], fill=1)
    return halo(p.sprite())


def _big_fly() -> Sprite:
    """物化后：张着翅膀趴在花上睡觉的大蝴蝶（俯视）"""
    p = Pen(44, 30)
    c = 22
    for sgn in (-1, 1):
        X = lambda x: c + sgn * x  # noqa: E731
        p.poly([(X(1), 12), (X(6), 2), (X(15), 0), (X(21), 3), (X(20), 10), (X(12), 15)], fill=0.35)   # 前翅
        p.poly([(X(1), 15), (X(12), 15), (X(17), 20), (X(13), 27), (X(6), 28), (X(2), 22)], fill=0.6)  # 后翅
        p.ellipse((X(13) - 3, 4, X(13) + 3, 10), fill=0)                                            # 眼斑
        p.px(X(13), 7)
        p.line([(X(2), 13), (X(19), 5)])                                                           # 翅脉
        p.line([(c + sgn * 3, 2), (c + sgn * 7, -3)])
    p.rect((c - 1, 6, c + 1, 26), fill=1)                                                           # 身
    p.ellipse((c - 3, 1, c + 3, 7), fill=0)                                                         # 头
    p.line([(c - 2, 4), (c - 1, 5)])                                                                # 闭眼
    p.line([(c + 1, 5), (c + 2, 4)])
    return p.sprite()


_A = {}


def _assets():
    if not _A:
        _A.update(bg=_bg(), bg2=_bg(False), body=_body(), sleep=_head(False), awake=_head(True),
                  tiny=[_tiny_zhou(0), _tiny_zhou(1)], big=_big_fly())
    return _A


@register
class Butterfly(Rest):
    id = "x1.butterfly"
    name = "庄周梦蝶"
    desc = "庄子倚树而眠，梦中化蝶翩翩飞舞、落花上歇脚；偶尔物化，黑白翻转成蝴蝶在睡、小庄周在飞"
    T = {"enter": 3.2, "exit": 1.3}

    def setup(self):
        _assets()
        self._ht = 0.0

    # ------------------------------------------------------------ 零件

    def fly_pos(self, t: float) -> tuple[float, float]:
        """蝴蝶的飞行路线（慢悠悠的利萨如曲线 + 噪声）"""
        x = 86 + math.sin(t * 0.23 + self.seed) * 30 + (noise(t * 0.5, self.seed) - 0.5) * 14
        y = 26 + math.sin(t * 0.37 + 1) * 13 + (noise(t * 0.6, self.seed + 5) - 0.5) * 8
        return x, y

    def wing(self, t: float, rate: float = 7.0) -> int:
        return [0, 1, 2, 1][int(t * rate) % 4]

    def zhuang(self, g: Gfx, t: float, awake: bool = False, nod: float = 0.0):
        A = _A
        g.blit(A["body"], 22, GROUND - 30)
        by = 1 if breathe(t, 4.6) > 0.5 else 0
        g.blit(A["awake"] if awake else A["sleep"], HEAD[0] + nod * 2, HEAD[1] + by + nod * 3)

    def thread(self, g: Gfx, fx: float, fy: float, t: float, a: float = 1.0):
        """梦的细线：从头顶到蝴蝶，虚线、轻轻飘"""
        x0, y0 = HEAD[0] + 8, HEAD[1] - 1
        n = 22
        for i in range(2, n - 1):
            if (i + int(t * 6)) % 3 or rand(i, 7) > a:
                continue
            k = i / n
            x = lerp(x0, fx, k)
            y = lerp(y0, fy, k) - math.sin(k * math.pi) * 10 + math.sin(t * 2 + k * 6) * 1.5
            g.px(x, y)

    def mx_fly(self, g: Gfx, t: float, rate: float = 3.0):
        g.mx_blit(MX_FLY[int(t * rate) % 2])

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        backdrop(g, _A["bg"])
        if t < 1.4:  # 打两个盹，头垂下去
            if t < 0.9:   # 头一点，惊醒抬起
                droop = 0.6 * ease_in_out(span(t, 0.2, 0.6)) * (1 - ease_out(span(t, 0.6, 0.8)))
            else:         # 再一点，就睡过去了
                droop = ease_in_out(span(t, 0.9, 1.4))
            self.zhuang(g, 0, awake=t < 0.9, nod=droop - 1)
            g.mx_rows([0, 0, 0, 0, 0, 0, 0x7E, 0xFF])
        else:
            self.zhuang(g, 0)
            k = span(t, 1.4, 3.2)           # 头顶冒出一只蝴蝶，飞到航线上
            if k < 0.3:
                r = ease_out_back(k / 0.3) * 4
                g.d.ellipse((HEAD[0] + 8 - r, HEAD[1] - 4 - r, HEAD[0] + 8 + r, HEAD[1] - 4 + r), outline=1)
            else:
                q = ease_in_out((k - 0.3) / 0.7)
                tx, ty = self.fly_pos(0)
                x = lerp(HEAD[0] + 6, tx, q)
                y = lerp(HEAD[1] - 8, ty, q) - math.sin(q * math.pi) * 12
                g.blit(FLY[self.wing(t)], x - 4, y - 3)
                self.thread(g, x, y, t, q)
            self.mx_fly(g, t)
            if t > 1.6:
                zzz(g, NOSE[0], NOSE[1] - 6, t - 1.6, self.seed, rise=16, drift=6, on=0.8)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        wu = ev(t, 150.0, 13.0, 50.0)       # 物化
        if wu:
            self.wuhua(g, wu[1], t)
            return
        backdrop(g, _A["bg"])
        self.zhuang(g, t)
        zzz(g, NOSE[0], NOSE[1] - 6, t, self.seed, rise=16, drift=6, every=1.8)
        rest = ev(t, 70.0, 14.0, 22.0)      # 落在花上歇一会
        x, y = self.fly_pos(t)
        if rest:
            fx, fy = FLOWERS[rest[0] % 3]
            fy -= 4
            u = rest[1]
            if u < 2.5:
                q = ease_in_out(u / 2.5)
                x, y = lerp(x, fx, q), lerp(y, fy, q)
                f = self.wing(t)
            elif u < 11.5:
                ex, ey = self.fly_pos(t)
                x, y = fx, fy
                f = 2 if (u % 2.6) < 1.8 else 1           # 停着，翅膀慢慢开合
                if u > 4:
                    typewriter(g, 122, 2, "自喻适志与", u - 4, cps=4, align="right")
            else:
                q = ease_in_out((u - 11.5) / 2.5)
                ex, ey = self.fly_pos(t)
                x, y = lerp(fx, ex, q), lerp(fy, ey, q)
                f = self.wing(t)
        else:
            f = self.wing(t)
            y += math.sin(t * 7) * 1.2
        g.blit(FLY[f], x - 4, y - 3)
        self._fly = (x, y)
        self.thread(g, x, y, t, 0.5 if rest else 1.0)
        if not rest and ev(t, 97.0, 9.0, 3.0):
            typewriter(g, 122, 2, "栩栩然胡蝶也", ev(t, 97.0, 9.0, 3.0)[1], cps=4, align="right")
        self.mx_fly(g, t, 1.0 if rest and 2.5 < rest[1] < 11.5 else 3.0)

    def wuhua(self, g: Gfx, u: float, t: float):
        """物化：蝴蝶落到鼻尖 → 一闪 → 黑白翻转，大蝴蝶在花上睡、小庄周在飞 → 一闪回来"""
        A = _A
        if u < 2.5 or u > 11.5:
            backdrop(g, A["bg"])
            self.zhuang(g, t)
            if u < 2.5:  # 飞向鼻尖
                sx, sy = self.fly_pos(t - u)
                q = ease_in_out(u / 2.3)
                x, y = lerp(sx, NOSE[0] + 2, q), lerp(sy, NOSE[1] - 4, q) - math.sin(q * math.pi) * 8
                g.blit(FLY[self.wing(t) if q < 1 else 2], x - 4, y - 3)
            else:        # 回来了，接着飞
                q = ease_in_out(span(u, 11.5, 13.0))
                ex, ey = self.fly_pos(t)
                x, y = lerp(NOSE[0] + 2, ex, q), lerp(NOSE[1] - 4, ey, q)
                g.blit(FLY[self.wing(t)], x - 4, y - 3)
            self.mx_fly(g, t)
            flash = 2.3 < u < 2.5 or 11.5 < u < 11.7
            if flash:
                g.invert()
                g.mx[:] = True
                g.mx_level = 6
            return
        # 翻转的世界
        backdrop(g, A["bg2"])
        bx, by = 82, 18 + int(breathe(t, 3.8) > 0.5)
        g.blit(A["big"], bx, by)
        zzz(g, bx + 26, by + 2, u, 3, rise=12, drift=6, s0=1, s1=3)
        k = u - 2.5
        tx = 50 + math.sin(k * 0.8) * 26
        ty = 26 + math.sin(k * 1.3) * 10
        g.blit(A["tiny"][int(k * 5) % 2], tx - 7, ty - 6)
        typewriter(g, 2, 2, "胡蝶之梦为周与", k - 1.0, cps=4)
        g.invert()
        g.mx[:] = True
        g.mx_blit(MX_FLY[0 if int(k * 1.2) % 2 else 1].replace("#", "x").replace(".", "#").replace("x", "."))

    def exit(self, g: Gfx, t: float):
        """醒来：蝴蝶飞回头里，庄周睁眼（蘧蘧然周也），画面收拢"""
        h = self._ht
        backdrop(g, _A["bg"])
        awake = t > 0.55
        self.zhuang(g, h, awake=awake)
        sx, sy = getattr(self, "_fly", None) or self.fly_pos(h)
        q = ease_in(span(t, 0, 0.55))
        if q < 1:
            x = lerp(sx, HEAD[0] + 7, q)
            y = lerp(sy, HEAD[1] + 2, q) - math.sin(q * math.pi) * 8
            g.blit(FLY[self.wing(t)], x - 4, y - 3)
            self.mx_fly(g, t)
        else:
            g.mx_rows([0, 0x66, 0x66, 0, 0, 0x42, 0x3C, 0])
            g.text(HEAD[0] + 15, HEAD[1] - 3, "!", size=12)
        iris(g, HEAD[0] + 7, HEAD[1] + 7, lerp(110, 0, ease_in_out(span(t, 0.6, self.T["exit"] - 0.05))), 0.8)
