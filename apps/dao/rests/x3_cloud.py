"""坐看云起：王维《终南别业》“行到水穷处，坐看云起时”；陶渊明《归去来兮辞》“云无心以出岫，鸟倦飞而知还”。

入场：小道士从左边走上崖头，盘腿坐下（扬起一点土），山水淡入。
持续：远山（山脊线 + 稀网点）、中山两座夹着山谷（25% 网点、受光坡亮带）；
      像素云朵从山谷里冒出来（出岫）：小 → 中 → 大，一边升一边往右飘，到高处散成点消失（三朵错开，一朵 33 秒）；
      山脚一湾溪水碎光往左流，流到崖下就没了（水穷处）；崖头草叶摇动；天上一条长云缓缓横移。
      小道士坐看，眨眼呼吸，时而闭目一会儿。
      小事件：倦鸟两只飞回远山、落进山后（47s）；一朵小云飘到小道士跟前，他伸指一点，云“噗”地散成三小团、
      他笑一下（113s）；“坐看云起时”题在左上角（75s 一次，12 秒）。
退场：云海从山谷涌上来，把整幅画淹没。
点阵：两座小山，山谷里一团云往上冒。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bird, cloud, every, faded, glints, mountain, plate, ridge, rock, tri

LEDGE = 47          # 崖头（小道士坐的地面）
DX = 22             # 小道士
VALLEY = (80, 46)   # 出云的山谷
LIFE = 33.0

_CACHE: dict = {}


def _layers(seed: int):
    if seed not in _CACHE:
        far = mountain(ridge([(8, 26, 26), (40, 19, 24), (72, 25, 20), (100, 17, 28), (128, 24, 20)], seed,
                             base=44, rough=0.8), lit=((0.25, 2),), shade=(), outline=2)
        mid_h = ridge([(50, 37, 22), (64, 34, 14), (106, 25, 22), (124, 30, 14)], seed + 3, base=70, rough=0.8,
                      power=0.9, round_top=True)
        mid = mountain(mid_h, lit=((0.75, 1), (0.5, 3), (0.25, 3)), shade=((0.25, 1),), body=0.125, veins=3,
                       seed=seed)
        clouds = [[cloud(9, 5, seed + i * 7), cloud(14, 7, seed + i * 7 + 1), cloud(21, 10, seed + i * 7 + 2)]
                  for i in range(3)]
        long_c = cloud(34, 8, seed + 99, lumps=6)
        bank = [cloud(24 + i * 2, 12 + i, seed + 200 + i, lumps=3) for i in range(3)]
        _CACHE[seed] = dict(far=far, mid=mid, clouds=clouds, long=long_c, bank=bank, cliff=_cliff(seed),
                            tiny=cloud(10, 6, seed + 300))
    return _CACHE[seed]


def _cliff(seed: int):
    """近景崖头：黑剪影白轮廓，左边一块高石，顶面平（坐人），右边断崖；顶面受光、岩层横纹、竖裂、断面网点背光"""
    from .x3_lib import bake

    pts = [(-1, 34), (3, 33), (7, 36), (9, 42), (12, LEDGE), (42, LEDGE), (45, 49), (46, 54), (50, 58), (52, 64),
           (-1, 64)]

    def draw(g):
        g.d.polygon(pts, fill=0, outline=1)
        g.d.line((2, 34, 6, 36), fill=1)                    # 高石顶面受光
        for x in range(13, 42, 2):                          # 顶面下一行网点
            g.px(x, LEDGE + 2)
        for x0, y0, x1, y1 in ((4, 52, 9, 51), (24, 53, 30, 52), (34, 51, 37, 51), (12, 58, 17, 57),
                               (30, 59, 36, 58), (2, 61, 6, 61), (21, 62, 25, 62), (2, 41, 4, 40)):
            g.d.line((x0, y0, x1, y1), fill=1)              # 岩层短纹
            g.px(x1 + 1, y1 + 1)
        for x, y, ln in ((18, 52, 3), (8, 56, 2), (40, 55, 3), (5, 45, 3)):
            g.d.line((x, y, x + 1, y + ln), fill=1)         # 裂
        for y in range(LEDGE + 2, 64):                      # 断面背光
            x1 = 42 + (y - LEDGE) * 10 // 17
            for x in range(x1 - 3, x1):
                if (x + y) % 2 == 0:
                    g.px(x, y)
        for x in (14, 22, 31, 40):                          # 苔点
            g.px(x, LEDGE - 1)

    return bake(draw, solid=lambda d: d.polygon(pts, fill=1))


GRASS = pix.frames("""
# #
 #
---
 ##
 #
---
# #
 #
---
##
 #
""")


def mx_cloud(g: Gfx, t: float):
    for x in range(8):  # 两座小山
        h = max(0, 3 - abs(x - 1)) if x < 4 else max(0, 3 - abs(x - 6))
        for y in range(8 - h, 8):
            g.mx[y, x] = True
    g.mx[7, :] = True
    k = (t / 3.0) % 1
    y = int(round(6 - k * 7))
    for dx, dy in ((0, 0), (1, 0), (0, -1), (-1, 0)) if k < 0.7 else ((0, 0), (1, -1)):
        xx, yy = 4 + dx, y + dy
        if 0 <= yy < 8 and 0 <= xx < 8:
            g.mx[yy, xx] = True


@register
class CloudWatch(Rest):
    id = "x3.cloud"
    name = "坐看云起"
    desc = "小道士坐在崖头，看像素云朵一朵朵从山谷里冒出来、长大、升高、散去；倦鸟归山，小云飘到跟前被他一指点散"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.L = _layers(self.seed % 4)

    # ------------------------------------------------------------ 画面

    def clouds(self, g: Gfx, t: float):
        """三朵出岫的云：小→中→大，升起、右飘、散去"""
        for i in range(3):
            tt = t + i * LIFE / 3 + 4
            n = int(tt // LIFE)
            k = (tt % LIFE) / LIFE
            sz = 0 if k < 0.12 else 1 if k < 0.3 else 2
            spr = self.L["clouds"][(n + i) % 3][sz]
            drift = 8 + rand(n * 3 + i, self.seed) * 22
            x = VALLEY[0] + ease_in_out(k) * drift + math.sin(tt * 0.4) * 1.5
            y = VALLEY[1] - ease_out(k) * 40
            if k > 0.72:
                spr = faded(spr, 1 - span(k, 0.72, 1.0))
            pix.blit(g, spr, x - spr.w // 2, y - spr.h // 2)

    def world(self, g: Gfx, t: float, sit: bool = True, dx: float = DX):
        L = self.L
        lx = (t * 1.2) % 170 - 40  # 高处的长云
        ev = every(t, 47, 9, 20)  # 倦鸟归山（画在远山之前：飞进山后就被挡住）
        if ev:
            k = ev[1] / 9
            for j in range(2):
                bx = lerp(134 + j * 9, 26 + j * 6, k)
                by = lerp(8 + j * 3, 27, ease_in_out(k))
                bird(g, bx, by, ev[1], fps=7 - 3 * k, flip=True, ph=j * 0.5)
        pix.blit(g, L["long"], lx, 5)
        g.blit(L["far"], 0, 0)
        self.clouds(g, t)
        g.blit(L["mid"], 0, 0)
        # 山脚溪水：往左流到崖下就没了
        g.d.rectangle((46, 56, 127, 63), fill=0)
        g.d.line((58, 56, 127, 56), fill=1)
        for x in range(50, 58, 2):
            g.px(x, 56)
        glints(g, 54, 127, 58, 63, -t, self.seed, n=16, speed=6, far=2, near=6, blink=0.35)
        pix.blit(g, L["cliff"], 0, 0)
        for j, x in enumerate((17, 30, 41)):  # 崖头草
            gr = GRASS[int(t * 2.2 + j * 1.3) % 4]
            g.blit(gr, x, LEDGE - 2)
        if not sit:
            return
        # 小道士：坐看；时而闭目
        ev2 = every(t, 113, 14, 60)
        ph = t % 26
        pose = "meditate" if 15 < ph < 21 else "sit"
        if ev2 and 3.5 < ev2[1] < 10.5:
            lt = ev2[1]
            face = "happy" if lt > 7.4 else "wow" if lt < 5 else "normal"
            figure(g, dx, LEDGE, t, legs="sit", arm="point" if 5 < lt < 8.6 else "gong", face=face)
        else:
            daoshi(g, dx, LEDGE, pose, t)
        if ev2:
            self.tiny(g, ev2[1])

    def tiny(self, g: Gfx, lt: float):
        """一朵小云飘到跟前，被一指点散成三小团"""
        spr = self.L["tiny"]
        if lt < 8.0:
            k = ease_out(span(lt, 0, 7.0))
            x = lerp(70, DX + 21, k) + math.sin(lt * 1.4) * 1.5
            y = lerp(30, LEDGE - 21, k) + math.sin(lt * 2.1) * 1.0
            if lt > 7.6:
                spr = pix.stretch(spr, 1.3, 0.7)
            pix.blit(g, spr, x - spr.w // 2, y - spr.h // 2)
        elif lt < 13:
            k = span(lt, 8.0, 13.0)
            cx, cy = DX + 21, LEDGE - 21
            for j, (vx, vy) in enumerate(((-5, -9), (6, -11), (1, -15))):
                x, y = cx + vx * ease_out(k) * 1.4, cy + vy * ease_out(k) * 1.2
                r = 2.5 * (1 - k) + 0.6
                if k < 0.6:
                    g.d.ellipse((x - r, y - r, x + r, y + r), fill=0, outline=1)
                elif int(lt * 10 + j) % 2:
                    g.px(x, y)
            if k < 0.12:
                for a in range(0, 360, 45):
                    g.px(cx + math.cos(math.radians(a)) * 5, cy + math.sin(math.radians(a)) * 3)

    def poem(self, g: Gfx, t: float):
        ev = every(t, 75, 12, 50)
        if ev:
            plate(g, 6, 4, "坐看云起时")

    def hold(self, g: Gfx, t: float):
        self.world(g, t)
        self.poem(g, t)
        mx_cloud(g, t)

    # ------------------------------------------------------------ 进出

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        tw = t - T
        walking = t < 2.1
        self.world(g, tw, sit=not walking)
        if walking:
            x = lerp(-10, DX, ease_out(span(t, 0, 2.1)))
            daoshi(g, x, LEDGE, "walk", t)
        elif t < 2.5:  # 坐下扬起一点土
            k = span(t, 2.1, 2.5)
            for s in (-1, 1):
                g.px(DX + s * (12 + k * 5), LEDGE - 1 - k * 2)
                g.px(DX + s * (14 + k * 6), LEDGE - k * 1)
        g.fade(span(t, 0, 1.0))
        mx_cloud(g, tw)
        if t < 1.0:
            g.mx[: int(8 - t * 8)] = False

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        self.world(g, tt)
        k = ease_in_out(span(t, 0, self.T["exit"]))
        top = lerp(70, -30, k)  # 云海从下往上涌：三排云头，后面是黑的
        bank = self.L["bank"]
        for row in range(3):
            y = top + row * 14
            g.d.rectangle((0, y + 2, 127, 63), fill=0)
            for j, x in enumerate(range(-16 + row * 9, 140, 20)):
                spr = bank[(j + row) % 3]
                pix.blit(g, spr, x + math.sin(tt * 1.5 + j + row) * 2, y - spr.h + 6 + ((j + row) % 2) * 3)
        mx_cloud(g, tt)
        rows = int(k * 8)
        if rows:
            g.mx[8 - rows:] = False
