"""松风：《梁书·陶弘景传》“特爱松风，庭院皆植松，每闻其响，欣然为乐。有时独游泉石，望见者以为仙人。”
（陶弘景，南朝茅山上清派宗师，号华阳隐居。）

入场：一阵风从左边吹进来，老松的枝叶由静到动，松针簌簌，树下的隐者闭目侧耳。
持续：崖上一株老松，主干扭转，一枝长臂探向山谷（像迎客松），枝头一簇簇平顶的松盖。
      平时微风，松盖轻轻起伏；每隔一阵起一阵大风：风线成群掠过，松盖整排压弯、回弹，松针被吹散。
      远山、远处一线瀑布在雾里。
      小事件：松果从枝头掉下，在石上弹两下滚到隐者脚边；风大时隐者衣袖飘起；“特爱松风”的题字隔一阵浮现。
      点阵：一道随风势起伏的“松涛”波形。
退场：风止，松针落定，画面淡去。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_out, ease_out_bounce, lerp, noise, rand, span, smoothstep
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x3_lib import every, halo, layer, peaks, pine_pad, poly_sprite, vpoem

CLIFF = [(0, 46), (12, 45), (24, 46), (34, 49), (40, 54), (43, 64), (0, 64)]
BASE = (22, 46)
TRUNK = [(22, 46), (20, 40), (24, 33), (21, 26), (26, 19), (33, 14), (42, 11)]
# 枝：从主干第几个点出发，后面的点（相对坐标）
BRANCHES = [
    (2, [(10, -2), (24, -5), (40, -3), (56, -7), (68, -8)]),     # 探向山谷的长臂
    (3, [(-8, -3), (-15, -6), (-19, -9)]),
    (5, [(10, -4), (22, -6), (32, -6)]),
    (4, [(-6, -4), (-10, -9)]),
]
PADS = [  # (枝号, 枝上第几点, 宽) ；枝号 -1 = 主干
    (0, 4, 20), (0, 3, 15), (0, 2, 13), (0, 1, 10), (1, 2, 13), (1, 1, 9), (2, 2, 16), (2, 1, 11), (3, 1, 10),
    (-1, 6, 13), (-1, 5, 10),
]
SAGE = (34, 49)
SIT = halo(Sprite("""
  .##..
  ####.
  .##..
  ###..
  ####.
  #####
  ######
"""))


@register
class PineWind(Rest):
    id = "x3.pine"
    name = "松风"
    desc = "崖上老松探出长臂，平时微风轻摇，一阵大风过来松盖整排压弯回弹；松下隐者闭目听松，松果偶落"
    T = {"enter": 2.6, "exit": 1.2}

    def setup(self):
        s = self.seed
        self.far = layer(peaks(128, 46, [(78, 14, 22), (112, 8, 26)], s, 1.0, power=1.4), 0.14, outline=2,
                         fog=14, floor=0.0)
        self.mid = layer(peaks(128, 62, [(58, 44, 30), (104, 34, 34)], s + 4, 1.6, power=1.5), 0.4, outline=1,
                         fog=16, floor=0.0, solid=True)
        self.cliff = poly_sprite([CLIFF], 0.0, strokes=[(6, 48, 9, 55), (16, 50, 14, 58), (28, 52, 32, 60),
                                                        (36, 56, 37, 62), (8, 60, 12, 63)])

    # ------------------------------------------------------------ 风

    def wind(self, t: float) -> float:
        """0..1：平时 0.15–0.3 的微风，每隔一阵一场大风"""
        w = 0.18 + 0.12 * noise(t * 0.25, self.seed)
        ev = every(t, 31.0, 9.0, 6.0)
        if ev:
            k, lt = ev
            peak = 0.75 + 0.25 * rand(k, self.seed)
            w += peak * smoothstep(span(lt, 0, 2.0)) * (1 - smoothstep(span(lt, 4.5, 9.0)))
        return clamp(w, 0, 1.2)

    def sway(self, t: float, w: float, k: float) -> tuple[float, float]:
        """离树根越远 k 越大，摆得越多：返回 (dx, dy)"""
        osc = math.sin(t * (2.2 + w * 2) + k * 2.5) * (0.6 + w * 1.6)
        lean = w * 4.0
        return (osc + lean) * k, (abs(osc) * 0.4 + lean * 0.3) * k

    # ------------------------------------------------------------ 零件

    def pine(self, g: Gfx, t: float, w: float):
        bx, by = BASE
        # 主干（粗，带树皮裂纹）
        pts = []
        for i, (x, y) in enumerate(TRUNK):
            k = (i / (len(TRUNK) - 1)) ** 2 * 0.35
            dx, dy = self.sway(t, w, k)
            pts.append((x + dx, y + dy))
        for i in range(len(pts) - 1):
            wd = 4 if i < 2 else 3 if i < 4 else 2
            g.d.line((pts[i], pts[i + 1]), fill=1, width=wd)
        for i in range(1, len(pts) - 2):  # 树皮：暗色的鳞纹
            x, y = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
            g.px(x, y, 0)
            g.px(pts[i][0] - 1, pts[i][1] + 1, 0)
        g.d.line((bx - 4, by, bx - 1, by - 3), fill=1)    # 根
        g.d.line((bx + 5, by + 1, bx + 1, by - 3), fill=1)
        ends = {}
        for bi, (root, rel) in enumerate(BRANCHES):
            rx, ry = pts[root]
            prev = (rx, ry)
            chain = []
            L = len(rel)
            for j, (ox, oy) in enumerate(rel):
                k = 0.25 + (j + 1) / L * (0.9 if bi == 0 else 0.6)
                dx, dy = self.sway(t + bi * 0.3, w, k)
                p = (TRUNK[root][0] + ox + dx, TRUNK[root][1] + oy + dy)
                g.d.line((prev, p), fill=1, width=2 if j < L / 2 else 1)
                chain.append(p)
                prev = p
            ends[bi] = chain
        ends[-1] = pts
        for bi, j, wd in PADS:
            x, y = ends[bi][j]
            pine_pad(g, x, y - 2, wd, sway=w * 1.2 * (1 if bi in (0, 2, -1) else 0.6))

    def wind_lines(self, g: Gfx, t: float, w: float):
        n = int(1 + w * 9)
        for i in range(n):
            sp = 50 + rand(i, 5) * 40
            x = (rand(i, 6) * 220 + t * sp * (0.4 + w)) % 220 - 50
            y = 6 + rand(i, 7) * 40
            ln = 8 + rand(i, 8) * 12 * (0.5 + w)
            pts = [(x + u, y + math.sin(u * 0.35 + t * 3 + i) * 1.2) for u in range(0, int(ln), 2)]
            if len(pts) > 1:
                g.d.line(pts, fill=1)
                ex, ey = pts[-1]
                g.d.arc((ex - 2, ey - 3, ex + 2, ey + 1), 270, 90, fill=1) if i % 3 == 0 else None

    def needles(self, g: Gfx, t: float, w: float):
        """大风吹落的松针（每根是一小撇）"""
        if w < 0.5:
            return
        n = int((w - 0.5) * 24)
        for i in range(n):
            ph = (t * (0.4 + rand(i, 3) * 0.3) + rand(i, 4)) % 1.0
            x = 40 + rand(i, 5) * 60 + ph * 70
            y = 8 + rand(i, 6) * 26 + ph * 18 + math.sin(ph * 12 + i) * 2
            g.d.line((x, y, x + 2, y + (1 if i % 2 else -1)), fill=1)

    def falls_far(self, g: Gfx, t: float):
        x = 106
        for y in range(18, 34):
            if (y + int(t * 10)) % 3:
                g.px(x, y)

    def sage(self, g: Gfx, t: float, w: float):
        x, y = SAGE
        g.blit(SIT, x - 3, y - SIT.h + 2)
        if w > 0.55:  # 衣袖、发带被风吹起
            fl = math.sin(t * 14) * 1.5
            g.d.line((x - 2, y - 4, x - 6 - w * 3, y - 4 + fl), fill=1)
            g.d.line((x - 1, y - 7, x - 5 - w * 3, y - 8 - fl), fill=1)

    def cone(self, g: Gfx, t: float):
        """松果：从长臂的枝头落下，在石上弹两下，滚到隐者脚边"""
        ev = every(t, 73.0, 12.0, 44.0)
        if not ev:
            return
        k, lt = ev
        x0, y0 = 46, 34
        if lt < 1.4:
            p = lt / 1.4
            x = x0 - p * 8
            y = lerp(y0, 50, ease_out_bounce(p))
        elif lt < 3.0:
            p = (lt - 1.4) / 1.6
            x = x0 - 8 - ease_out(p) * 2
            y = 50
        else:
            x, y = x0 - 10, 50
            if lt > 10:
                if int(lt * 6) % 2:
                    return
        g.d.ellipse((x - 1, y - 2, x + 1, y + 1), fill=1)
        g.px(x, y - 1, 0)

    def poem(self, g: Gfx, t: float, k: float):
        if k > 0:
            g.d.rectangle((113, 0, 127, 50), fill=0)
            vpoem(g, 115, 2, "特爱松风", k)

    def mx(self, g: Gfx, t: float, w: float):
        for x in range(8):  # 松涛波形
            a = 0.6 + w * 2.6
            y = 3.5 + math.sin(x * 0.85 - t * (2.5 + w * 3)) * a
            g.mx_set(x, int(round(y)))
            if w > 0.6:
                g.mx_set(x, int(round(y)) + 1)
        g.mx[7, :] = True

    # ------------------------------------------------------------ 阶段

    def picture(self, g: Gfx, t: float, w: float):
        g.blit(self.far, 0, 0)
        g.blit(self.mid, 0, 0)
        self.falls_far(g, t)
        self.wind_lines(g, t, w)
        g.blit(self.cliff, 0, 0)
        self.pine(g, t, w)
        self.needles(g, t, w)
        self.sage(g, t, w)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        w = self.wind(0) * ease_out(span(t, 0.3, 1.8)) + 0.6 * math.sin(span(t, 0.3, T) * math.pi)
        self.picture(g, t - T, w)
        self.poem(g, t, span(t, 1.0, T))
        self.mx(g, t, w)

    def hold(self, g: Gfx, t: float):
        w = self.wind(t)
        self.picture(g, t, w)
        self.cone(g, t)
        if t < 16:
            self.poem(g, t, 1 - span(t, 13, 16))
        else:
            ev = every(t, 140.0, 22.0, 60.0)
            if ev:
                self.poem(g, t, span(ev[1], 0, 2.0) * (1 - span(ev[1], 19, 22)))
        self.mx(g, t, w)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        tt = self.hold_t + t   # 接着持续阶段最后的样子
        w = self.wind(tt) * (1 - span(t, 0, 0.6))
        self.picture(g, tt, w)
        g.fade(1 - ease_in(span(t, 0.2, T)))
        self.mx(g, t, w)
        g.mx[:, : int(t / T * 8)] = False
