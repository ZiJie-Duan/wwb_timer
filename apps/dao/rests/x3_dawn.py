"""紫气东来：《列仙传》“老子西游，关令尹喜望见有紫气浮关，而老子果乘青牛而过也。”

入场：天将明，太阳从东边的云海里一点点升起，光芒散开，几缕“紫气”从日边向西流向关楼。
持续：云海三层，远慢近快地翻滚；群峰露出云海，西边山坳里一座关楼（函谷关）。
      太阳的光芒缓缓转动，紫气一缕缕从东往西流进关门。
      小事件：每隔几分钟，一位老者骑青牛从东边山脊慢慢走来，进了关门（“紫气东来”四字浮现）；
      偶有一行飞鸟掠过日前；日光不时一亮（光芒伸长）。
退场：日光大盛，画面从西往东褪去，最后只剩太阳收成一点。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x3_lib import bird, ctext, every, halo, layer, peaks, poly_sprite, vpoem

SUN = (104, 20)
SUN_R = 7
GATE = (30, 31)        # 关楼底中
RIDGE = [(36, 33), (48, 35), (60, 34), (72, 37), (84, 36), (96, 39), (110, 38), (130, 40)]  # 老子走的山脊
OX_P, OX_D = 300.0, 46.0

OX = halo(Sprite("""
  ....##.......
  ...####......
  ....##.......
  ...####......
  ..######.....
  #.######.....
  ############.
  .###########.
  ..##########.
  ..#.#....#.#.
  ..#.#....#.#.
"""))  # 骑牛的老者（朝左走：牛头、牛角在左）


def ridge_y(x: float) -> float:
    for (x0, y0), (x1, y1) in zip(RIDGE, RIDGE[1:]):
        if x0 <= x <= x1:
            return lerp(y0, y1, (x - x0) / (x1 - x0))
    return RIDGE[0][1] if x < RIDGE[0][0] else RIDGE[-1][1]


@register
class PurpleQi(Rest):
    id = "x3.dawn"
    name = "紫气东来"
    desc = "云海日出，群峰浮在云上，紫气从日边流进西边的关楼；偶见老者骑青牛过关"
    T = {"enter": 3.4, "exit": 1.4}

    def setup(self):
        s = self.seed
        self.far = layer(peaks(128, 44, [(70, 22, 16), (88, 28, 14), (122, 26, 16)], s, 0.8), 0.15, outline=2,
                         fog=10, floor=0.0)
        near_l = [(0, 46), (0, 14), (6, 12), (12, 16), (18, 22), (24, 28), (36, 33), (48, 35), (60, 34), (72, 37),
                  (84, 36), (96, 39), (110, 38), (128, 40), (128, 46)]
        self.near = poly_sprite([near_l], 0.3, fog_y=14, fog=24, floor=0.0,
                                strokes=[(6, 16, 8, 28), (14, 20, 12, 32), (52, 37, 50, 42)])
        self.peak2 = poly_sprite([[(40, 46), (46, 30), (52, 24), (56, 26), (62, 36), (66, 46)]], 0.45, fog_y=26,
                                 fog=16, floor=0.0, strokes=[(52, 26, 50, 34)])

    # ------------------------------------------------------------ 零件

    def sun(self, g: Gfx, t: float, y: float, flare: float = 0.0, r: float = SUN_R):
        x = SUN[0]
        rot = t * 0.08
        for i in range(12):  # 光芒：长短相间，缓缓转动
            a = rot + i * math.pi / 6
            r0 = r + 3
            r1 = r + (8 if i % 2 else 5) + flare * 8 + math.sin(t * 1.3 + i) * 1
            for k in range(int(r0), int(r1), 2):
                g.px(x + math.cos(a) * k, y + math.sin(a) * k)
        g.d.ellipse((x - r - 1, y - r - 1, x + r + 1, y + r + 1), fill=0)
        g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)

    def qi(self, g: Gfx, t: float, reach: float = 1.0, sun_y: float = SUN[1]):
        """紫气：三缕从日边往西流进关门的波带（虚线往西流动）"""
        x0, x1 = SUN[0] - SUN_R - 4, GATE[0] + 2
        for k, off in enumerate((-5, 0, 5)):
            prev = None
            for i in range(0, 64):
                s = i / 63
                if s > reach:
                    break
                x = lerp(x0, x1, s)
                y = lerp(sun_y + off * 0.6, GATE[1] - 9 + off * 0.3, s * s) + math.sin(s * 9 + t * 1.2 + k * 2) * 2.2 * (1 - s * 0.5)
                on = ((s * 40 + t * 4 + k * 3) % 4) < 2.4
                if on and prev is not None:
                    g.d.line((prev[0], prev[1], x, y), fill=1)
                prev = (x, y) if on else None

    def gate(self, g: Gfx):
        """关楼：城台 + 门洞 + 两重檐"""
        x, y = GATE
        g.d.rectangle((x - 9, y - 7, x + 9, y + 3), fill=0, outline=1)       # 城台
        g.d.chord((x - 3, y - 5, x + 3, y + 5), 180, 360, fill=1)            # 门洞（亮：紫气从这里进去）
        g.d.rectangle((x - 3, y, x + 3, y + 3), fill=1)
        for xx in range(x - 9, x + 10, 3):                                   # 垛口
            g.d.rectangle((xx, y - 9, xx + 1, y - 8), fill=1)
        g.d.rectangle((x - 5, y - 14, x + 5, y - 9), fill=0, outline=1)       # 楼身
        g.d.line((x - 2, y - 13, x - 2, y - 10), fill=1)
        g.d.line((x + 2, y - 13, x + 2, y - 10), fill=1)
        g.d.polygon([(x - 9, y - 13), (x - 6, y - 15), (x + 6, y - 15), (x + 9, y - 13)], fill=0, outline=1)
        g.d.polygon([(x - 7, y - 17), (x - 4, y - 20), (x + 4, y - 20), (x + 7, y - 17)], fill=0, outline=1)
        g.d.line((x - 4, y - 17, x + 4, y - 17), fill=1)

    def sea(self, g: Gfx, t: float, rows=(0, 1, 2)):
        """云海：一排排鼓起的云头，远小慢、近大快；下面挖空盖住山脚"""
        for r in rows:
            base = (44, 51, 60)[r]
            w = (13, 20, 30)[r]
            h = (3.5, 6.0, 9.0)[r]
            sp = (1.2, 2.6, 4.5)[r]
            shift = t * sp + r * 13
            n0 = int(shift // w)
            off = shift - n0 * w
            g.d.rectangle((0, base, 127, 63), fill=0)
            for i in range(-1, 128 // w + 2):
                x = i * w - off
                idx = i + n0                       # 跟着云头走的编号，形状不会突变
                bump = h * (0.55 + 0.75 * rand(idx * 3 + r * 101, self.seed))
                ww = w * (0.8 + 0.5 * rand(idx * 5 + r * 7, self.seed))
                g.d.chord((x, base - bump, x + ww, base + bump), 180, 360, fill=0)
                g.d.arc((x, base - bump, x + ww, base + bump), 180, 360, fill=1)
                if r > 0 and rand(idx + r * 31, self.seed + 8) < 0.6:  # 云头卷纹
                    cx = x + ww * 0.5
                    rr = bump * 0.45
                    g.d.arc((cx - rr, base - bump * 0.55 - rr * 0.6, cx + rr, base - bump * 0.55 + rr * 0.6), 160, 380,
                            fill=1)

    def laozi(self, g: Gfx, t: float) -> bool:
        ev = every(t, OX_P, OX_D, 120.0)
        if not ev:
            return False
        k, lt = ev
        walk = 38.0
        p = clamp(lt / walk)
        x = lerp(132, GATE[0] + 4, p)
        y = ridge_y(x)
        if p < 1:
            step = int(lt * 2) % 2
            g.blit(OX, x - 6, y - OX.h + 1 + 0)
            if step:  # 迈步
                g.d.rectangle((x - 4, y - 1, x + 6, y), fill=0)
                g.px(x - 3, y)
                g.px(x + 4, y)
        return True

    def ox_text(self, g: Gfx, t: float, k_in: float | None = None):
        if k_in is None:
            ev = every(t, OX_P, OX_D, 120.0)
            if not ev:
                return
            k_in = span(ev[1], 34, 37) * (1 - span(ev[1], OX_D - 3, OX_D))
        if k_in > 0:
            g.d.rectangle((0, 0, 14, 49), fill=0)
            vpoem(g, 1, 2, "紫气东来", k_in)

    def birds(self, g: Gfx, t: float):
        ev = every(t, 59.0, 9.0, 23.0)
        if not ev:
            return
        k, lt = ev
        for i in range(3):
            x = lerp(-10, 140, lt / 9.0) - i * 7
            y = 14 + i * 3 + math.sin(lt * 1.5 + i) * 1.5
            bird(g, x, y, lt + i * 0.5, s=0.9)

    def mx(self, g: Gfx, t: float, rise: float = 1.0, flare: float = 0.0):
        g.mx[7, :] = True
        cy = lerp(8.5, 4.5, rise)
        for y in range(7):
            for x in range(8):
                d = math.hypot(x - 3.5, y - cy)
                if d < 2.2:
                    g.mx[y, x] = True
                elif rise > 0.6 and 3.0 < d < 3.8 + flare * 2:
                    a = math.atan2(y - cy, x - 3.5) - t * 0.4
                    if math.cos(a * 4) > 0.5:
                        g.mx[y, x] = True

    def flare(self, t: float) -> float:
        ev = every(t, 43.0, 3.0, 11.0)
        return math.sin(ev[1] / 3.0 * math.pi) if ev else 0.0

    # ------------------------------------------------------------ 阶段

    def picture(self, g: Gfx, t: float, sun_y: float = SUN[1], reach: float = 1.0, flare: float = 0.0):
        if sun_y < 44:
            self.sun(g, t, sun_y, flare)
        g.blit(self.far, 0, 0)
        self.sea(g, t, rows=(0,))
        g.blit(self.peak2, 0, 0)
        g.blit(self.near, 0, 0)
        self.gate(g)
        self.qi(g, t, reach, sun_y)
        self.sea(g, t, rows=(1, 2))

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        rise = ease_out(span(t, 0, 2.4))
        sun_y = lerp(50, SUN[1], rise)
        self.picture(g, t, sun_y, reach=ease_in_out(span(t, 1.8, T)))
        self.ox_text(g, t, span(t, 2.0, T))
        self.mx(g, t, rise)

    def hold(self, g: Gfx, t: float):
        fl = self.flare(t)
        self.picture(g, t, flare=fl)
        self.birds(g, t)
        self.laozi(g, t)
        if t < 18:
            self.ox_text(g, t, 1 - span(t, 15, 18))
        else:
            self.ox_text(g, t)
        self.mx(g, t, 1.0, fl)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        p = t / T
        self.picture(g, self.hold_t + t, flare=ease_out(span(p, 0, 0.5)) * 1.5)
        x = lerp(-10, 140, ease_in(span(p, 0.1, 0.8)))       # 从西往东褪去
        if x > 0:
            g.d.rectangle((0, 0, x, 63), fill=0)
        if p > 0.6:  # 最后太阳收成一点
            r = SUN_R * (1 - ease_in(span(p, 0.6, 1.0)))
            g.d.rectangle((0, 0, 127, 63), fill=0)
            if r > 0.5:
                g.d.ellipse((SUN[0] - r, SUN[1] - r, SUN[0] + r, SUN[1] + r), fill=1)
        self.mx(g, t, 1 - span(p, 0.5, 1.0), 1.0)
        if p > 0.8:
            g.mx[:] = False
