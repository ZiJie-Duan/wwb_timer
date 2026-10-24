"""濠梁观鱼：《庄子·秋水》“庄子与惠子游于濠梁之上。庄子曰：‘鯈鱼出游从容，是鱼之乐也。’惠子曰：‘子非鱼，安知鱼之乐？’
庄子曰：‘子非我，安知我不知鱼之乐？’……庄子曰：‘请循其本……我知之濠上也。’”
原文：<https://zh.wikisource.org/zh-hans/%E8%8E%8A%E5%AD%90/%E7%A7%8B%E6%B0%B4>

濠水上一道石梁（“梁”是平桥）：桥面条石、两根桥墩、栏杆；小道士（庄子）在左边扶栏看鱼，
戴冠的惠子在右边。桥下一池清水，水面波纹逐帧流动，左边几片荷叶、一枝荷苞，水底水草摇摆、沙点。
五尾鯈鱼（尖头、前粗后细，尾巴随游速摆）沿各自平滑的路线从容游动，穿过桥墩后面。
两人的辩论一来一回浮在桥上空处：庄子的话靠左、惠子的话靠右（短句，取原文）。
小事件：鱼浮上来吐个泡（19s）；一片落叶飘下落水，鱼都凑过去啄，叶子一颤一颤（61s）；
        蜻蜓飞来落在荷苞上歇一会再飞走（89s）；一尾鱼跃出水面再落回去，庄子笑（43s）。
入场：桥从上方落下来，水面的波纹渐渐平了，鱼从四边游进来。  退场：鱼一摆尾往四面散开，水纹荡开，画面淡出。
点阵：一尾小鱼来回游，吐泡。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_out, lerp, noise, rand, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bake, every, plate, ring, splash

DECK = 36          # 桥面
SURF = 43          # 水面
ZX, HX = 22, 108   # 庄子、惠子
PIERS = (34, 92)
LINES = [(0, "是鱼之乐也"), (1, "子非鱼"), (1, "安知鱼之乐"), (0, "子非我"), (0, "请循其本"), (0, "我知之濠上")]


def _bridge():
    def draw(g):
        g.d.rectangle((0, DECK, 127, DECK + 4), fill=0, outline=1)       # 桥面条石
        for x in range(10, 128, 14):
            g.d.line((x, DECK + 1, x, DECK + 3), fill=1)
        g.d.line((0, DECK + 2, 127, DECK + 2), fill=0)
        for x in range(3, 128, 7):
            g.px(x, DECK + 3)
        for px_ in PIERS:                                                  # 桥墩
            g.d.rectangle((px_, DECK + 5, px_ + 6, 63), fill=0, outline=1)
            for j, y in enumerate(range(DECK + 10, 64, 6)):
                g.d.line((px_ + 1, y, px_ + 5, y), fill=1)
                g.px(px_ + 2 + (j % 2) * 2, y + 3)
    return bake(draw, solid=lambda d: (d.rectangle((0, DECK, 127, DECK + 4), fill=1),
                                        [d.rectangle((p, DECK + 5, p + 6, 63), fill=1) for p in PIERS]))


def _rail():
    def draw(g):
        g.d.line((0, DECK - 7, 127, DECK - 7), fill=1)                  # 扶手
        g.d.line((0, DECK - 6, 127, DECK - 6), fill=1)
        for x in range(4, 128, 12):                                      # 望柱
            g.d.rectangle((x, DECK - 9, x + 2, DECK - 1), fill=1)
            g.px(x + 1, DECK - 8, 0)
        for x in range(10, 128, 12):                                     # 栏板花
            g.d.line((x - 2, DECK - 3, x, DECK - 5, x + 2, DECK - 3), fill=1)
    return bake(draw)


def _cap():
    """惠子的冠（盖住发髻）"""
    p = Part(11, 6)
    p.shape("rectangle", (2, 0, 8, 5), fill=1)
    p.d.line((3, 2, 7, 2), fill=0)
    p.shape("line", (0, 4, 10, 4), fill=1)
    p.px(5, 0, 0)
    return p.sprite()


FISH = pix.frames("""
   ##
 #####  #
##.######
 ###### #
   ##
---
   ##
 ##### #
##.#####
 ##### #
   ##
---
   ##   #
 #######
##.####
 #######
   ##   #
""")

LEAF = pix.frames("""
 ##
####
 #.
---
##
 ##.
  ##
""")

FLY = pix.frames("""
# #
.#.
 #
 #
 #
---

###
 #
 #
 #
""")

_C: dict = {}


def parts():
    if not _C:
        _C.update(bridge=_bridge(), rail=_rail(), cap=_cap())
    return _C


@register
class FishJoy(Rest):
    id = "x3.fish"
    name = "濠梁观鱼"
    desc = "濠水石梁上，小道士（庄子）扶栏看鱼、戴冠的惠子在旁；五尾鯈鱼从容游动，两人一来一回辩“鱼之乐”"
    T = {"enter": 2.6, "exit": 1.2}

    def setup(self):
        self.P = parts()
        r = self.rng
        self.fish = [(r.uniform(0.04, 0.09) * (1 if i % 2 else -1), r.random(), 47 + i * 3.0, r.uniform(0.3, 0.7),
                      r.random() * 6) for i in range(5)]

    def fish_pos(self, i: int, t: float, scatter: float = 0.0):
        sp, ph, y0, wob, ph2 = self.fish[i]
        u = (ph + t * sp) % 1
        x = -14 + u * 156 if sp > 0 else 142 - u * 156
        y = y0 + math.sin(t * wob + ph2) * 2.2
        lf = every(t, 61, 12, 30)  # 落叶：鱼都凑过去
        if lf and 3 < lf[1] < 10 and i < 4:
            k = span(lf[1], 3, 5) * (1 - span(lf[1], 8.5, 10))
            tx, ty = 70 + (i - 1.5) * 6, SURF + 3 + (i % 2) * 2
            x, y = lerp(x, tx, k), lerp(y, ty, k)
        if scatter:
            a = i * 1.3 + 0.4
            x += math.cos(a) * scatter * 60
            y += math.sin(a) * scatter * 10
        return x, y, sp > 0

    def water(self, g: Gfx, t: float, calm: float = 1.0, scatter: float = 0.0):
        g.d.rectangle((0, SURF, 127, 63), fill=0)
        for x in range(0, 128):  # 水面：流动的波纹
            if (x + int(t * 4)) % 6 < 4:
                y = SURF + (1 if (x + int(t * 4)) % 12 < 6 else 0) * calm
                g.px(x, y)
        for x in range(1, 128, 4):  # 水底沙点
            g.px(x + (x // 4) % 2, 62)
        for j, x in enumerate((14, 56, 70, 116)):  # 水草
            for i in range(6):
                sw = math.sin(t * 1.3 + j + i * 0.5) * (i / 6) * 2
                g.px(x + sw, 62 - i * 1.5)
        for i in range(5):
            x, y, right = self.fish_pos(i, t, scatter)
            fr = FISH[int(t * (5 + i)) % 3]
            pix.blit(g, fr, x - 4, y - 2, flip=not right)
        bu = every(t, 19, 3.5, 6)  # 吐泡
        if bu:
            x, y, right = self.fish_pos(0, t - bu[1])
            x += 5 if right else -5
            k = bu[1] / 3.5
            for j in range(3):
                q = k * 1.4 - j * 0.2
                if 0 < q < 1:
                    yy = lerp(y - 2, SURF + 1, q)
                    g.d.ellipse((x - 1, yy - 1, x + 1, yy + 1), outline=1)
            if k > 0.75:
                ring(g, x, SURF, span(k, 0.75, 1), rmax=5, flat=0.3)

    def lotus(self, g: Gfx, t: float):
        for x, w in ((6, 9), (20, 7), (118, 9)):  # 荷叶：浮在水面上的扁椭圆，有一个缺口
            g.d.ellipse((x - w // 2, SURF - 1, x + w // 2, SURF + 2), fill=0, outline=1)
            g.d.line((x, SURF, x + 2, SURF + 1), fill=0)
            g.d.line((x, SURF + 3, x, SURF + 5), fill=1)
        bx = 13
        g.d.line((bx, SURF, bx, SURF - 3), fill=1)     # 荷苞
        g.d.polygon([(bx - 1, SURF - 3), (bx, SURF - 6), (bx + 1, SURF - 3)], fill=1)
        return (bx, SURF - 6)

    def dragonfly(self, g: Gfx, t: float, bud):
        ev = every(t, 89, 12, 40)
        if not ev:
            return
        lt = ev[1]
        bx, by = bud
        if lt < 3:
            k = ease_out(lt / 3)
            x, y = lerp(-6, bx, k), lerp(20, by - 5, k) + math.sin(lt * 9) * 1.5
            f = FLY[int(t * 20) % 2]
        elif lt < 9:
            x, y = bx, by - 5
            f = FLY[0] if int(lt * 2) % 4 else FLY[1]
        else:
            k = ease_in(span(lt, 9, 12))
            x, y = lerp(bx, 60, k), lerp(by - 5, 2, k)
            f = FLY[int(t * 20) % 2]
        g.blit(f, x - 1, y)

    def leaf(self, g: Gfx, t: float):
        ev = every(t, 61, 12, 30)
        if not ev:
            return
        lt = ev[1]
        if lt < 3:
            k = lt / 3
            x, y = 64 + math.sin(lt * 3) * 8 + k * 6, lerp(-3, SURF - 2, k)
            g.blit(LEAF[int(lt * 4) % 2], x - 2, y)
        else:
            x = 70 + math.sin(lt * 7) * 0.5 * (lt < 10)
            g.d.line((x - 2, SURF - 1, x + 2, SURF - 1), fill=1)
            g.px(x, SURF - 2)
            ring(g, x, SURF, span(lt, 3, 4.5), rmax=6, flat=0.3)
            if 5 < lt < 9 and int(lt * 4) % 2:
                ring(g, x, SURF, 0.3, rmax=3, flat=0.3)

    def jump(self, g: Gfx, t: float):
        ev = every(t, 43, 3, 12)
        if not ev:
            return None
        lt = ev[1]
        x0 = 58
        if lt < 1.1:
            k = lt / 1.1
            x = x0 + k * 16
            y = SURF - math.sin(k * math.pi) * 14
            spr = FISH[0]
            pix.blit(g, spr.rot90(1 if k < 0.5 else 3) if 0.3 < k < 0.7 else spr, x - 4, y - 3)
        splash(g, x0, SURF, span(lt, 0, 0.5))
        splash(g, x0 + 16, SURF, span(lt, 1.1, 1.7))
        ring(g, x0 + 16, SURF + 1, span(lt, 1.1, 2.8), rmax=7, flat=0.3)
        return lt

    def people(self, g: Gfx, t: float, laugh: bool):
        k = (t % 70)
        idx = int(k // 9) if k < 54 else -1
        talking = idx if (idx >= 0 and k - idx * 9 < 6) else -1
        spk = LINES[talking][0] if talking >= 0 else None
        z_point = spk == 0 and talking == 0
        figure(g, ZX, DECK, t, arm="point" if z_point else ("gong" if spk == 0 else "down"),
               face="happy" if laugh or talking == 5 else "normal", head="up")
        P = self.P

        def cap(g_, at):
            at(-5, -36 + (1 if (t * 0.7) % 1 > 0.5 else 0), P["cap"])

        figure(g, HX, DECK, t + 1.7, arm="gong" if spk == 1 else "down", flip=True, front=cap)
        return talking

    def words(self, g: Gfx, talking: int):
        if talking < 0:
            return
        who, s = LINES[talking]
        if who == 0:
            x = 36
            plate(g, x, 4, s)
            g.d.polygon([(x - 3, 9), (x - 7, 11), (x - 3, 12)], fill=1)
        else:
            x = 94
            plate(g, x, 4, s, align="right")
            g.d.polygon([(x + 2, 9), (x + 6, 11), (x + 2, 12)], fill=1)

    def world(self, g: Gfx, t: float, calm: float = 1.0, scatter: float = 0.0, deck_dy: float = 0.0):
        P = self.P
        self.water(g, t, calm, scatter)
        bud = self.lotus(g, t)
        self.leaf(g, t)
        lt = self.jump(g, t)
        g.blit(P["bridge"], 0, deck_dy)
        pix.blit(g, P["bridge"], 0, deck_dy, outline=False)
        talking = self.people(g, t, lt is not None and lt > 0.6) if deck_dy == 0 else -1
        g.blit(P["rail"], 0, deck_dy)
        self.dragonfly(g, t, bud)
        return talking

    def mx(self, g: Gfx, t: float):
        k = (t * 0.25) % 2
        x = int(k * 6) if k < 1 else int((2 - k) * 6)
        right = k < 1
        y = 4 + int(math.sin(t * 1.5) * 1.5)
        for dx, dy in ((0, 0), (1, 0), (2, 0), (1, -1), (1, 1)):
            xx = x + (dx if right else 2 - dx)
            if 0 <= xx < 8 and 0 <= y + dy < 8:
                g.mx[y + dy, xx] = True
        tx = x - 1 if right else x + 3
        if 0 <= tx < 8:
            g.mx[y - 1 if int(t * 4) % 2 else y + 1, tx] = True
        b = (t * 0.8) % 3
        if b < 1.5:
            g.mx[int(3 - b * 2), 6 if not right else 1] = True
        g.mx[7, ::2] = True

    def hold(self, g: Gfx, t: float):
        talking = self.world(g, t)
        self.words(g, talking)
        self.mx(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        tw = t - T
        dy = -(1 - ease_out(span(t, 0, 1.4))) * 50
        self.water(g, tw, calm=1 + (1 - span(t, 0, T)) * 2, scatter=(1 - ease_out(span(t, 0.5, T))))
        self.lotus(g, tw)
        g.blit(self.P["bridge"], 0, dy)
        if t > 1.4:
            self.people(g, tw, False)
        g.blit(self.P["rail"], 0, dy)
        g.fade(span(t, 0, 0.6))
        self.mx(g, tw)

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + t
        k = span(t, 0, self.T["exit"])
        self.world(g, tt, calm=1 + k * 3, scatter=ease_in(k))
        ring(g, 64, SURF + 6, k, rmax=40, flat=0.25)
        g.fade(1 - span(t, 0.5, 1.2))
        self.mx(g, tt)
        g.mx[:, : int(k * 8)] = False
