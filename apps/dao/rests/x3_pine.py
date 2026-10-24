"""松风：《梁书·陶弘景传》（《太平御览》卷九五三引）“特爱松风，庭院皆植松，每闻其响，欣然为乐。”
陶弘景是茅山上清派宗师。出处：<https://ctext.org/taiping-yulan/953>

崖头一株老松：主干扭着长上去（树皮一块块鳞纹），一枝长臂探向山谷，枝上一簇簇平顶松盖；
松下小道士盘坐听风，发带往后飘。远处山谷里远山、一线瀑布。
持续：平时微风，松盖轻轻摇，离树根越远摆得越多；每 31 秒一阵大风（2 秒起风、9 秒落定）：
      风线成群从右往左掠过、松盖整排被压弯再回弹、松针被吹落飘走、小道士的发带飘平。
小事件：松果从长臂上掉下，在石上弹两下滚到小道士脚边，他吓一跳（73s）；
        一只松鼠沿长臂跑出来，蹲在枝头啃一会儿再跑回去（117s）；“特爱松风”题字（140s 一次）。
入场：一阵风从右边吹进来，老松由静到动。  退场：风止，画面淡出。
点阵：“松涛”波形，振幅与速度随风势，大风时加粗。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_out, lerp, noise, rand, span
from ..engine.chars import daoshi
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bake, bird, every, mountain, pine_pad, plate, ribbon, ridge

GROUND = 54
DX = 48
ROOT = (16, GROUND)
# 枝干：主干 + 长臂（点 = (x, y, 离根的柔度)）
TRUNK = [(16, 54, 0), (12, 46, 0), (16, 37, 0.05), (12, 28, 0.1), (17, 19, 0.2), (21, 10, 0.3)]
ARM = [(15, 30, 0.05), (26, 22, 0.25), (38, 17, 0.45), (50, 14, 0.65), (62, 13, 0.8), (74, 10, 0.95), (86, 11, 1.0)]
LOW = [(13, 42, 0.05), (6, 36, 0.3), (1, 33, 0.45)]
PADS = [(21, 6, 17, 0.35), (9, 13, 13, 0.25), (28, 15, 13, 0.3), (40, 11, 15, 0.5), (54, 9, 17, 0.7),
        (66, 9, 13, 0.85), (78, 6, 15, 1.0), (89, 8, 11, 1.1), (3, 29, 13, 0.5), (47, 4, 11, 0.6)]


def _ground():
    pts = [(-1, GROUND), (70, GROUND), (74, 57), (77, 64), (-1, 64)]

    def draw(g):
        g.d.polygon(pts, fill=0, outline=1)
        g.d.line((0, GROUND + 1, 69, GROUND + 1), fill=0)
        for x in range(2, 68, 2):
            g.px(x, GROUND + 2)
        for x0, y0, ln in ((6, 58, 6), (24, 60, 5), (40, 57, 7), (56, 61, 6), (66, 58, 3)):
            g.d.line((x0, y0, x0 + ln, y0), fill=1)
        pix.checker(g, (70, 57, 77, 64), 0.25)
        for x in (8, 30, 38, 62):  # 草
            g.px(x, GROUND - 1), g.px(x + 1, GROUND - 2), g.px(x + 2, GROUND - 1)

    return bake(draw, solid=lambda d: d.polygon(pts, fill=1))


_C: dict = {}


def parts():
    if not _C:
        far = mountain(ridge([(96, 30, 22), (118, 24, 22)], 41, base=64, rough=0.9, power=0.9, round_top=True),
                       lit=((0.5, 1), (0.25, 2), (0.125, 2)), shade=((0.125, 2),), outline=1, veins=2, seed=4)
        far2 = mountain(ridge([(84, 36, 18), (108, 30, 20), (128, 34, 12)], 42, base=64, rough=0.6, round_top=True),
                        lit=((0.25, 1),), shade=(), outline=2)
        _C.update(far=far, far2=far2, ground=_ground(),
                  pads={w: pine_pad(w, w) for w in (11, 13, 15, 17)})
    return _C


SQUIRREL = pix.frames("""
##
# #  .
#  ####
 ######
 #  # #
---
 ##
#  # .
#  ####
 ######
  # #
---
##   .
 # ####
 #######
  ## ##
""")


def wind(t: float) -> float:
    """风势 0..1：微风 + 每 31 秒一阵大风（2 秒起、9 秒落）"""
    w = 0.12 + 0.08 * noise(t * 0.3, 5)
    k = t % 31
    if k < 11:
        w += ease_out(span(k, 0, 2)) * (1 - span(k, 2, 11)) * 0.9
    return clamp(w)


def sway(t: float, flex: float) -> tuple[float, float]:
    """离根柔度 flex 处的位移（风从右往左吹）"""
    w = wind(t)
    dx = -w * 6 * flex + math.sin(t * (1.2 + w * 4) + flex * 2) * (0.5 + 2.5 * w) * flex
    dy = w * 1.5 * flex * flex
    return dx, dy


@register
class PineWind(Rest):
    id = "x3.pine"
    name = "松风"
    desc = "崖头老松一枝长臂探向山谷，松下小道士盘坐听风；大风时松盖整排压弯回弹、松针飘落；松果落下、松鼠出来啃果"
    T = {"enter": 2.6, "exit": 1.2}

    def setup(self):
        self.P = parts()

    def tree(self, g: Gfx, t: float, wt=None):
        P = self.P

        def pts(chain):
            out = []
            for x, y, f in chain:
                dx, dy = sway(t, f)
                out.append((x + dx, y + dy))
            return out

        tr = pts(TRUNK)
        g.d.line(tr, fill=1, width=5)
        g.d.line(tr, fill=0, width=3)
        for i, (x, y) in enumerate(tr[:-1]):  # 树皮鳞纹
            nx, ny = tr[i + 1]
            for k in (0.3, 0.7):
                px_, py_ = lerp(x, nx, k), lerp(y, ny, k)
                g.px(px_ - 1 + (i % 2), py_), g.px(px_ + (i % 2), py_ - 1)
        for chain, wd in ((ARM, 3), (LOW, 2)):
            p = pts(chain)
            g.d.line(p, fill=1, width=wd)
            if wd > 2:
                g.d.line(p, fill=0, width=1)
                for x, y in p[1:-1]:
                    g.px(x, y - 1)
        w = wind(t)
        for i, (x, y, wd, f) in enumerate(PADS):
            dx, dy = sway(t + i * 0.13, f)
            spr = P["pads"][min(P["pads"], key=lambda k: abs(k - wd))]
            if w > 0.5 and f > 0.4:  # 大风时压扁一点
                spr = pix.stretch(spr, 1.0 + 0.1, 0.8)
            pix.blit(g, spr, x - spr.w // 2 + dx, y - spr.h // 2 + dy)
        return w

    def gust_lines(self, g: Gfx, t: float, w: float):
        n = int(max(0, w - 0.25) * 14)
        for i in range(n):
            sp = 70 + rand(i, 3) * 40
            y = 4 + rand(i, 4) * 46
            x = 140 - ((t * sp + rand(i, 5) * 200) % 200)
            ln = 6 + int(rand(i, 6) * 8)
            if i % 3 == 0:  # 带卷头的风线
                g.d.line((x, y, x + ln, y), fill=1)
                g.d.arc((x - 3, y - 3, x + 1, y + 1), 90, 270, fill=1)
            else:
                for j in range(0, ln, 2):
                    g.px(x + j, y)
        for i in range(int(w * 10)):  # 被吹落的松针
            k = ((t * 0.6 + rand(i, 7)) % 1)
            x0 = 30 + rand(i, 8) * 60
            x = x0 - k * 70 * w
            y = 18 + rand(i, 9) * 8 + k * 30 + math.sin(t * 8 + i) * 2
            g.d.line((x, y, x + 1, y + (1 if i % 2 else -1)), fill=1)

    def cone(self, g: Gfx, t: float):
        """松果落下弹两下停在石上；随后松鼠从树根跑出来，叼起松果跑回去"""
        ev = every(t, 73, 16, 25)
        if not ev:
            return None
        lt = ev[1]
        x0, y0 = 72, 14
        end = 66.0
        if lt < 1.2:
            k = ease_in(lt / 1.2)
            x, y = x0 - lt * 2, lerp(y0, GROUND - 2, k)
        elif lt < 3.0:
            k = span(lt, 1.2, 3.0)
            hop = abs(math.sin(k * math.pi * 2)) * (1 - k) * 8
            x, y = lerp(x0 - 2.4, end, k), GROUND - 2 - hop
        else:
            x, y = end, GROUND - 2
        # 松鼠：5–8.5 跑过去，8.5–11 蹲着啃，11–14 叼着跑回树根
        sq = None
        if 5 < lt < 14:
            if lt < 8.5:
                sx, run, fl = lerp(18, end - 6, span(lt, 5, 8.5)), True, False
            elif lt < 11:
                sx, run, fl = end - 6, False, False
            else:
                sx, run, fl = lerp(end - 6, 14, span(lt, 11, 14)), True, True
            spr = SQUIRREL[int(lt * 10) % 2] if run else (SQUIRREL[2] if int(lt * 3) % 3 else SQUIRREL[0])
            sq = (spr, sx, fl)
            if lt > 11:
                x, y = sx - 1, GROUND - 6
        if lt < 14:
            g.d.ellipse((x - 1, y - 2, x + 1, y + 1), fill=1)
            g.px(x, y - 1, 0), g.px(x, y + 1, 0)
        if sq:
            spr, sx, fl = sq
            pix.blit(g, spr, sx - 3, GROUND - spr.h, flip=fl)
        return lt

    def cranes(self, g: Gfx, t: float):
        ev = every(t, 117, 9, 50)
        if ev:
            k = ev[1] / 9
            for j in range(2):
                bird(g, lerp(132, 70, k) + j * 8, 30 + j * 2 + math.sin(k * 5 + j) * 2, ev[1], fps=4, flip=True,
                     ph=j * 0.5)

    def world(self, g: Gfx, t: float):
        P = self.P
        g.blit(P["far2"], 0, 0)
        g.blit(P["far"], 0, 0)
        for y in range(36, 62):  # 远处一线瀑布
            if (y + int(t * 20)) % 3:
                g.px(107, y)
        g.blit(P["ground"], 0, 0)
        w = self.tree(g, t)
        self.cranes(g, t)
        ev = every(t, 73, 16, 25)
        wow = ev is not None and 1.2 < ev[1] < 3.6
        ph = t % 26
        pose = "sit" if (wow or 18 < ph < 24) else "meditate"
        daoshi(g, DX, GROUND, pose, t, face="wow" if wow else "normal")
        ribbon(g, DX - 3, GROUND - 31, t, w)
        self.cone(g, t)
        self.gust_lines(g, t, w)
        return w

    def mx(self, g: Gfx, t: float, w: float):
        amp = 0.8 + w * 2.6
        for x in range(8):
            y = 3.5 + math.sin(x * 0.9 + t * (2 + w * 6)) * amp
            yi = int(round(y))
            if 0 <= yi < 8:
                g.mx[yi, x] = True
                if w > 0.5 and yi + 1 < 8:
                    g.mx[yi + 1, x] = True

    def hold(self, g: Gfx, t: float):
        w = self.world(g, t)
        if every(t, 140, 12, 60):
            plate(g, 102, 49, "特爱松风", align="center")
        self.mx(g, t, w)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        tw = t - T
        w = self.world(g, tw)
        g.fade(span(t, 0, 0.8))
        if t > 1.0:
            plate(g, 102, 49, "特爱松风", align="center")
        self.mx(g, tw, w)

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        w = self.world(g, tt)
        g.fade(1 - span(t, 0.2, 1.2))
        self.mx(g, tt, w * (1 - span(t, 0, 1.2)))
