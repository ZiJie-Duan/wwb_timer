"""寒江独钓：柳宗元《江雪》“千山鸟飞绝，万径人踪灭。孤舟蓑笠翁，独钓寒江雪。”

入场：雪先落下来，一叶小舟从左边滑进江心停住，蓑笠翁扬竿，钓线甩出去，浮子落水漾开一圈。
持续：千山覆雪（远山只剩山脊线），江面空阔，只有一舟一翁一竿；雪分远近三层飘落。
      雪慢慢积在斗笠和船舷上，积满了老翁抖一抖，雪簌簌落下。
      浮子不时一点一点地动；有时老翁提竿——多半是空钩（钓的是雪），偶尔钓上一尾小鱼，又放回江里。
退场：小舟悠悠划出画外，雪幕合拢。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import every, layer, peaks, poem_cols

WATER = 38           # 江岸线（远）
BX, BY = 64, 50      # 船中心（船舷）
SHAKE_P = 150.0      # 积雪 → 抖雪 一轮
BITE_P = 47.0


@register
class SnowFishing(Rest):
    id = "x3.snow"
    name = "寒江独钓"
    desc = "千山覆雪，江心一叶孤舟，蓑笠翁独钓；雪积满斗笠就抖一抖，提竿多半是空钩"
    T = {"enter": 3.4, "exit": 1.3}

    def setup(self):
        s = self.seed
        self.far = layer(peaks(128, WATER, [(24, 6, 22), (60, 12, 22), (96, 4, 24)], s + 2, 0.8), 0.0, outline=2)
        self.mid = layer(peaks(128, WATER, [(6, 16, 26), (44, 20, 22), (80, 22, 20), (118, 14, 26)], s, 1.2), 0.08,
                         outline=1, fog=10, floor=0.0, solid=True)
        # 近岸寒林：几棵落了叶的树（枝上挂雪）
        import random
        r = random.Random(s * 3 + 1)
        self.trees = []
        for tx, th in ((6, 24), (15, 30), (25, 20)):
            self.trees += self._tree(r, tx, 63, -math.pi / 2 + r.uniform(-0.1, 0.1), th * 0.45, 4)
        # 雪：三层（远小慢、近大快）
        self.flakes = [(rand(i, s) * 140, rand(i + 300, s), 0 if i < 26 else 1 if i < 40 else 2) for i in range(46)]

    def _tree(self, r, x, y, ang, ln, depth):
        x1, y1 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        out = [(x, y, x1, y1, depth)]
        if depth > 0:
            for da in (-0.5, 0.45) if depth > 1 else (-0.6, 0.0, 0.5):
                out += self._tree(r, x1, y1, ang + da + r.uniform(-0.25, 0.25), ln * r.uniform(0.55, 0.75), depth - 1)
        return out

    # ------------------------------------------------------------ 零件

    def bank(self, g: Gfx):
        pts = [(0, 52), (10, 51), (22, 53), (32, 57), (38, 63), (0, 63)]
        g.d.polygon(pts, fill=0, outline=1)
        for x0, y0, x1, y1, d in self.trees:
            g.d.line((x0, y0 - 11, x1, y1 - 11), fill=1)
            if d <= 1 and rand(int(x1 * 7 + y1), 3) < 0.5:   # 枝头的雪
                g.d.rectangle((x1 - 1, y1 - 12, x1, y1 - 11), fill=1)

    def snow(self, g: Gfx, t: float, amount: float = 1.0, wind: float = 0.0):
        for i, (x0, ph, layer_) in enumerate(self.flakes):
            if rand(i + 900, self.seed) > amount:
                continue
            sp = (5, 9, 15)[layer_]
            y = (ph * 74 + t * sp) % 74 - 6
            x = (x0 + math.sin(t * (0.5 + layer_ * 0.2) + i) * (1 + layer_) + t * (1.5 + wind) * (layer_ + 1)) % 140 - 6
            if layer_ == 2:
                g.d.rectangle((x, y, x + 1, y + 1), fill=1)
            else:
                g.px(x, y)

    def river(self, g: Gfx, t: float):
        for j in range(9):  # 江面的几道淡波
            y = WATER + 4 + j * 2.6
            x = (rand(j, 7) * 128 + t * (1 + j * 0.3)) % 150 - 20
            ln = 4 + j * 1.5
            g.d.line((x, y, x + ln, y), fill=1)
            if j > 5:
                g.d.line((x + ln + 6, y, x + ln + 8, y), fill=1)

    def boat(self, g: Gfx, bx: float, by: float, t: float, cap: float = 0.0, shake: float = 0.0,
             rod: float = 0.0, cast: float | None = None, catch: bool = False):
        """船、蓑笠翁、竿。cap 0..1 斗笠积雪；shake 抖雪的幅度；rod 提竿 0..1；cast 甩线进度（None=线在水里）"""
        bob = math.sin(t * 0.9) * 0.6
        by += bob
        # 船身：两头翘的小舟
        hull = [(bx - 22, by - 5), (bx - 15, by - 1), (bx + 15, by - 1), (bx + 21, by - 5), (bx + 16, by + 3),
                (bx - 16, by + 3)]
        g.d.polygon(hull, fill=0, outline=1)
        g.d.line((bx - 15, by + 1, bx + 15, by + 1), fill=1)
        # 倒影
        for x in range(int(bx - 18), int(bx + 18), 2):
            if rand(x + int(t * 2), 3) < 0.6:
                g.px(x, by + 6 + (x % 3 == 0))
        # 蓑衣：坐着的钟形，草茎竖线，下摆参差
        sx = bx - 9 + math.sin(shake * 40) * shake * 1.5
        top = by - 15
        cape = [(sx - 2, top), (sx + 2, top), (sx + 7, by - 1), (sx - 7, by - 1)]
        g.d.polygon(cape, fill=0, outline=1)
        for k in (-4, -1.5, 1.5, 4):
            g.d.line((sx + k * 0.35, top + 2, sx + k, by - 2), fill=1)
        # 斗笠：大而扁的尖顶，积雪从顶上往下堆白
        hat = [(sx - 10, top), (sx + 10, top), (sx, top - 6)]
        g.d.polygon(hat, fill=0, outline=1)
        if cap > 0:
            h = 1 + cap * 5
            g.d.polygon([(sx - 10 * h / 6, top - 6 + h), (sx + 10 * h / 6, top - 6 + h), (sx, top - 6)], fill=1)
        # 船舷积雪
        if cap > 0.3:
            for x in range(int(bx - 15), int(bx + 15), 2 if cap < 0.7 else 1):
                g.px(x, by - 2)
        # 钓竿
        hx, hy = sx + 6, by - 7
        ang = lerp(-0.42, -0.95, rod)
        L = 32
        tx, ty = hx + math.cos(ang) * L, hy + math.sin(ang) * L
        bend = 2 * rod
        g.d.line((hx, hy, (hx + tx) / 2 + bend * 0.3, (hy + ty) / 2 - bend, tx, ty), fill=1)
        fx, fy = bx + 38, by + 3   # 浮子
        if cast is not None:  # 甩线：浮子沿抛物线飞出去
            p = cast
            fx, fy = lerp(tx, bx + 38, p), lerp(ty, by + 3, p) - math.sin(p * math.pi) * 8
            g.d.line((tx, ty, fx, fy), fill=1)
            g.px(fx, fy)
            return tx, ty
        if rod > 0.05:  # 提竿：线出水，钩上挂着什么
            hook = (lerp(fx, tx + 2, rod * 0.7), lerp(fy, ty + 14, rod))
            g.d.line((tx, ty, hook[0], hook[1]), fill=1)
            if catch:
                swing = math.sin(t * 9) * 1.5
                g.d.polygon([(hook[0] + swing, hook[1]), (hook[0] + 2 + swing, hook[1] + 3),
                             (hook[0] + swing, hook[1] + 6), (hook[0] - 2 + swing, hook[1] + 3)], fill=1)
                g.d.line((hook[0] - 2 + swing, hook[1] + 7, hook[0] + 2 + swing, hook[1] + 7), fill=1)
            else:
                g.d.arc((hook[0] - 1, hook[1] - 1, hook[0] + 1, hook[1] + 2), 0, 180, fill=1)
        else:
            g.d.line((tx, ty, fx, fy - 1), fill=1)
            g.d.rectangle((fx, fy - 1, fx, fy), fill=1)
        return tx, ty

    def state(self, t: float):
        """按 t 算：积雪、抖雪、咬钩、提竿"""
        k = t % SHAKE_P
        cap = clamp(k / (SHAKE_P - 6))
        shake = 0.0
        if k > SHAKE_P - 6:
            q = k - (SHAKE_P - 6)
            shake = math.exp(-q * 2) * (q < 2.5)
            cap = 1 - ease_out(span(q, 0.2, 1.2))
        ev = every(t, BITE_P, 14.0, 17.0)
        bob, rod, catch, cast = 0.0, 0.0, False, None
        if ev:
            n, lt = ev
            if lt < 4:  # 浮子一点一点
                bob = (1 if int(lt * 3) % 2 else 0) * (1 if rand(n * 5 + int(lt * 3), 2) < 0.7 else 0)
            lift = rand(n, self.seed + 1) < 0.6
            if lift and 4 <= lt < 14:
                if lt < 5.0:
                    rod = ease_out_back(lt - 4)
                elif lt < 10.5:
                    rod = 1.0
                elif lt < 12.0:
                    rod = 1 - ease_in(span(lt, 10.5, 12.0))
                    cast = None
                else:
                    cast = ease_out(span(lt, 12.0, 13.4))
                catch = rand(n, self.seed + 2) < 0.3
        return cap, shake, bob, rod, catch, cast

    def poem(self, g: Gfx, t: float, k: float):
        if k <= 0:
            return
        g.d.rectangle((100, 0, 127, 62), fill=0)
        poem_cols(g, 127, 2, ("孤舟蓑笠翁", "独钓寒江雪"), k)

    def mx(self, g: Gfx, t: float, pile: float):
        for i in range(6):
            x = int(rand(i, 4) * 8)
            y = int((t * (1.5 + rand(i, 5)) + rand(i, 6) * 8) % 8)
            g.mx_set(x, y)
        h = int(pile * 2.99)
        if h:
            g.mx[8 - h:, :] = True
            if h < 3:
                for x in range(8):
                    if rand(x, int(t / 20)) < 0.4:
                        g.mx_set(x, 7 - h)

    # ------------------------------------------------------------ 阶段

    def landscape(self, g: Gfx, t: float):
        g.blit(self.far, 0, -6)
        g.blit(self.mid, 0, 0)
        g.d.line((0, WATER, 127, WATER), fill=1)
        self.river(g, t)
        self.bank(g)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        self.landscape(g, t)
        self.snow(g, t, amount=0.3 + 0.7 * span(t, 0, 1.5))
        bx = lerp(-30, BX, ease_out(span(t, 0, 2.0)))
        if t < 2.2:
            self.boat(g, bx, BY, t, rod=0.6 * span(t, 1.4, 2.2))
            # 船尾的水纹
            for j in range(3):
                g.d.line((bx - 22 - j * 6, BY + 3 + j, bx - 18 - j * 6, BY + 3 + j), fill=1)
        else:
            rod = 0.6 * (1 - ease_in(span(t, 2.2, 2.5)))
            cast = ease_out(span(t, 2.3, 3.0))
            self.boat(g, BX, BY, t, rod=rod, cast=cast if cast < 1 else None)
            if t > 3.0:  # 浮子落水漾开
                r = (t - 3.0) * 14
                g.d.ellipse((BX + 38 - r, BY + 3 - r * 0.25, BX + 38 + r, BY + 3 + r * 0.25), outline=1)
        self.poem(g, t, span(t, 1.6, T))
        self.mx(g, t, 0.0)

    def hold(self, g: Gfx, t: float):
        self.landscape(g, t)
        cap, shake, bob, rod, catch, cast = self.state(t)
        self.snow(g, t)
        self.boat(g, BX, BY + 0, t, cap=cap, shake=shake, rod=rod, catch=catch, cast=cast)
        if bob and rod == 0 and cast is None:  # 浮子被拽了一下：一圈涟漪
            g.d.ellipse((BX + 33, BY + 2, BX + 43, BY + 5), outline=1)
        if shake > 0.05:  # 抖下来的雪
            q = 1 - shake
            for j in range(10):
                a = rand(j, 8) * math.pi
                r = 4 + q * 14
                g.px(BX - 9 + math.cos(a) * r * 1.4, BY - 21 - math.sin(a) * r * 0.5 + q * q * 20)
        if t < 21:
            self.poem(g, t, 1 - span(t, 18, 21))
        else:
            ev = every(t, 180.0, 24.0, 100.0)
            if ev:
                self.poem(g, t, span(ev[1], 0, 2.5) * (1 - span(ev[1], 21, 24)))
        self.mx(g, t, cap)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        p = ease_in(t / T)
        tt = self.hold_t + t   # 接着持续阶段最后的样子
        self.landscape(g, tt)
        self.boat(g, BX + p * 110, BY, tt, cap=self.state(tt)[0], rod=0.3 * span(t, 0, 0.3))
        self.snow(g, tt, amount=1.0, wind=p * 30)
        g.fade(1 - ease_in(span(t, 0.4, T)))
        self.mx(g, t, 0.0)
        g.mx[: int(t / T * 8), :] = False
