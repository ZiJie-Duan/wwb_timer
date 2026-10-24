"""扫叶：银杏树下，小道士用竹扫帚一下一下把落叶扫成一堆；叶子不停地落。
约每 72 秒一阵风把整堆叶子卷走——他愣了一下，笑了：“损之又损，以至于无为”（《道德经》四十八章）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import daoshi, dellipse, dpoly, event, fade_box, phase

GY = 57            # 地面
DX = 44            # 道士站位
P = 2.0            # 一扫的周期
BX0, BX1 = 60, 80  # 扫帚头推的起止
PILE = 90          # 叶堆中心
C = 72.0           # 大轮：扫 60 秒 + 风 12 秒
SWEEP_END = 60.0
FALL_DT = 2.7      # 平均几秒落一片
TRUNK_X = 108

LEAVES = [Sprite("#.#\n.#."), Sprite("##.\n.##"), Sprite(".#.\n#.#"), Sprite(".##\n##.")]
FALLING = [Sprite("#.#\n###\n.#."), Sprite("##.\n###\n..#"), Sprite(".#.\n###\n#.#"), Sprite(".##\n###\n#..")]
GINKGO = Sprite("#.#\n###\n.#.")


def stroke(k: float) -> tuple[float, float]:
    """一扫：k 0..1 → (扫帚头 x, 抬起高度)。前 45% 贴地推，后面抬起拉回"""
    if k < 0.45:
        return lerp(BX0, BX1, ease_in_out(k / 0.45)), 0.0
    q = (k - 0.45) / 0.55
    return lerp(BX1, BX0, ease_in_out(q)), math.sin(q * math.pi) * 3


@register
class Sweep(Rest):
    id = "x5.sweep"
    name = "扫叶"
    desc = "银杏树下扫落叶，叶子扫成堆又被风卷走——损之又损，以至于无为"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.s = self.rng.randrange(1000)
        self._ht = 0.0

    # ------------------------------------------------------------ 叶子（全是 t 的函数）

    def _leaf(self, cyc: int, i: int):
        """第 cyc 大轮第 i 片：(开始落的时刻, 落多久, 起点 x, 落点 x)"""
        sd = self.s + cyc * 131
        t0 = i * FALL_DT + rand(i, sd) * 1.8
        dur = 4.5 + rand(i + 50, sd) * 2.5
        x0 = 80 + rand(i + 100, sd) * 44
        x1 = 52 + rand(i + 200, sd) * 46
        return t0, dur, x0, x1

    def _broom_at(self, k: float) -> tuple[float, float]:
        if k >= SWEEP_END:
            return BX0, 0.0
        if self._paused(k):
            return BX0, 0.0
        return stroke((k % P) / P)

    def _pause_win(self, cyc: int) -> tuple[float, float]:
        """本大轮里叶子落头上的那段停顿（对齐到扫的周期）"""
        n = 9 + int(rand(cyc, self.s + 7) * 8)
        return n * P, n * P + 4 * P

    def _paused(self, k: float, cyc: int | None = None) -> bool:
        a, b = self._pause_win(self._cyc if cyc is None else cyc)
        return a <= k < b

    def leaves(self, g: Gfx, t: float, gust: float = -1.0) -> int:
        """画所有叶子，返回已进堆的片数。gust ≥ 0：风起后的秒数"""
        cyc, k = phase(t, C)
        self._cyc = cyc
        piled = 0
        bx, lift = self._broom_at(k)
        pushing = k < SWEEP_END and not self._paused(k) and (k % P) / P < 0.45
        flying = []
        for i in range(int(SWEEP_END / FALL_DT) + 1):
            t0, dur, x0, x1 = self._leaf(cyc, i)
            if t0 >= SWEEP_END - 2 or k < t0:
                continue
            u = (k - t0) / dur
            if u < 1:  # 正在飘落
                if gust >= 0:
                    flying.append((x1, GY - 30 * (1 - u), i))
                    continue
                y = lerp(10 + rand(i, cyc) * 8, GY - 1, u)
                x = lerp(x0, x1, u) + math.sin(k * 2.2 + i) * 4 * (1 - u)
                g.blit(FALLING[int(k * 5 + i) % 4], x - 1, y - 1)
                continue
            # 已落地：在扫帚路线上的会被推进堆里
            tl = t0 + dur
            x = x1
            if x1 <= BX1 + 1:
                # 落地后第一个“推”经过它的时刻
                n = math.ceil(tl / P)
                while self._paused(n * P) and n * P < SWEEP_END:
                    n += 1
                ts = n * P
                if ts < SWEEP_END and k >= ts:
                    kk = (k - ts) / P
                    if kk >= 0.45 or k >= ts + P:
                        piled += 1
                        continue
                    hx, _ = stroke(kk)
                    x = max(x1, hx + 2)
                    if not pushing:
                        piled += 1
                        continue
            else:
                piled += 1
                continue
            if gust >= 0:
                flying.append((x, GY - 1, i))
            else:
                g.px(x, GY - 1)
                g.px(x + 1, GY - 1)
                g.px(x + (i % 2), GY - 2)
        self._flying = flying
        return piled

    def pile(self, g: Gfx, n: int, blow: float = 0.0):
        """叶堆：n 片，blow 0..1 被风削掉"""
        m = n * (1 - blow)
        if m < 0.5:
            return
        w = 4 + m * 0.5
        h = 1.5 + m * 0.3
        cx = PILE + blow * 6
        dome = [(cx + math.cos(a / 10 * math.pi) * w, GY - math.sin(a / 10 * math.pi) * h) for a in range(11)]
        dpoly(g, dome, 0.3)
        g.d.line((cx - w - 1, GY, cx + w + 1, GY), fill=1)
        for j in range(int(m * 0.8)):  # 堆上露出一片片叶形
            a = rand(j, self.s + 3)
            x = cx - w * 0.8 + a * w * 1.6
            top = GY - h * math.sqrt(max(0.0, 1 - ((x - cx) / w) ** 2))
            g.blit(FALLING[j % 4], x - 1, top - 1 + rand(j + 9, self.s) * 2)

    # ------------------------------------------------------------ 场景

    def tree(self, g: Gfx, t: float, wind: float = 0.0):
        d = g.d
        d.polygon([(TRUNK_X - 7, GY), (TRUNK_X - 3, GY - 6), (TRUNK_X - 2, 14), (TRUNK_X + 3, 14), (TRUNK_X + 4, GY - 7),
                   (TRUNK_X + 9, GY)], fill=0, outline=1)
        for j, y in enumerate(range(20, GY - 4, 6)):  # 树皮
            xx = TRUNK_X - 1 + (j % 3)
            d.line((xx, y, xx + 1, y + 3), fill=1)
        d.line((TRUNK_X - 2, 26, TRUNK_X - 14, 14), fill=1)   # 枝
        d.line((TRUNK_X - 2, 27, TRUNK_X - 13, 15), fill=1)
        d.line((TRUNK_X + 3, 22, TRUNK_X + 12, 12), fill=1)
        # 树冠：底下一层淡淡的抖动，上面一片片扇形银杏叶，随风轻摆
        dellipse(g, (TRUNK_X - 38, -6, TRUNK_X + 26, 18), 0.12, None)
        dellipse(g, (TRUNK_X - 26, 2, TRUNK_X + 10, 22), 0.12, None)
        for j in range(56):
            a = rand(j, 77) * 2 * math.pi
            rr = math.sqrt(rand(j + 300, 77))
            x = TRUNK_X - 6 + math.cos(a) * rr * 30
            y = 7 + math.sin(a) * rr * 9
            if y < -1:
                continue
            sway = (noise(t * 0.8 + j * 0.3, 5) - 0.5) * 2 + wind * 3 * rr
            g.blit(GINKGO, x + sway, y)

    def flagstones(self, g: Gfx):
        g.d.line((0, GY, 127, GY), fill=1)
        for x in (8, 37, 66, 95, 124):
            g.d.line((x, GY + 2, x, 63), fill=1)
        g.d.line((0, 61, 127, 61), fill=0)
        for x in range(0, 128, 2):
            g.px(x, 63)

    def figure(self, g: Gfx, k: float, t: float, bx: float, lift: float, look: float = 0.0, eye: str | None = None,
               shake: float = 0.0, bob: float = 0.0, bow: float = 0.0):
        """道士 + 扫帚：扫帚头在 (bx, GY-lift)"""
        hx, hy = bx, GY - lift
        # 扫帚柄方向：从帚头指向道士肩后上方
        ang = math.atan2((GY - 30) - hy, (DX - 6) - hx)
        L = 34
        tx, ty = hx + math.cos(ang) * L, hy + math.sin(ang) * L
        lean = 1.5 + (bx - BX0) / (BX1 - BX0) * 2 + bow
        p_low = (lerp(hx, tx, 0.42), lerp(hy, ty, 0.42))
        p_up = (lerp(hx, tx, 0.7), lerp(hy, ty, 0.7))
        if eye is None:
            eye = "closed" if (t % 4.3) < 0.15 else "open"
        # 柄在身前：先画人（远手握上面）再画柄，最后近手压在柄上
        daoshi(g, DX + shake, GY, 1, hands=[p_low, p_up], lean=lean, eye=eye, look=look, head_dy=bob)
        g.d.line((hx, hy - 2, tx, ty), fill=1)
        g.d.rectangle((p_low[0] - 1, p_low[1] - 1, p_low[0] + 1, p_low[1] + 1), fill=1)
        # 帚头：一大把散开的竹枝（扇形），着地时往前拖
        jx, jy = hx + math.cos(ang) * 10, hy + math.sin(ang) * 10
        drag = 2 if lift == 0 else -1
        fan = [(jx, jy), (hx + 7 + drag, hy), (hx - 6 + drag, hy)]
        dpoly(g, fan, 0.35)
        for j in range(5):
            g.d.line((jx, jy, hx - 6 + drag + j * 3.2, hy), fill=1)
        g.d.line((jx - 1, jy + 1, jx + 2, jy + 1), fill=1)

    def text(self, g: Gfx, s: str, a: float = 1.0):
        n = int(round(len(s) * clamp(a)))
        g.d.rectangle((0, 0, 14, 63), fill=0)
        g.vtext(2, 1, s[:n])

    # ------------------------------------------------------------ 阶段

    def draw(self, g: Gfx, t: float, pose_override=None):
        cyc, k = phase(t, C)
        self._cyc = cyc
        gust = k - (SWEEP_END + 1.0) if k >= SWEEP_END + 1.0 else -1.0
        wind = 0.0
        if k >= SWEEP_END:
            wind = span(k, SWEEP_END + 0.5, SWEEP_END + 1.5) * (1 - span(k, SWEEP_END + 5, SWEEP_END + 7))
        self.flagstones(g)
        self.tree(g, t, wind)
        piled = self.leaves(g, t, gust)
        total_piled = piled
        blow = 0.0
        if gust >= 0:
            blow = ease_in(span(gust, 0.0, 1.6))
        self.pile(g, total_piled, blow)
        # 风：几道风线 + 叶子被卷走
        if k >= SWEEP_END + 0.5 and k < SWEEP_END + 7:
            w = k - SWEEP_END - 0.5
            for j in range(4):
                y = 22 + j * 9
                x0 = -30 + w * 70 - j * 14
                if 16 < x0 < 140:
                    g.d.line((x0, y, x0 + 16, y), fill=1)
                    g.d.arc((x0 + 12, y - 4, x0 + 20, y + 4), 270, 90, fill=1)
        if gust >= 0:
            for j in range(int(total_piled * 0.9) + len(self._flying)):
                if j < len(self._flying):
                    sx, sy, sd = self._flying[j]
                else:
                    sx, sy, sd = PILE + (rand(j, self.s) - 0.5) * 12, GY - 2, j + 40
                q = gust - rand(sd, self.s + 1) * 0.8
                if q < 0:
                    g.px(sx, sy)
                    continue
                x = sx + q * (40 + rand(sd, 3) * 50) + q * q * 10
                y = sy - math.sin(min(q * 1.6, math.pi)) * (14 + rand(sd, 4) * 22) - q * 4
                if x < 130:
                    g.blit(LEAVES[int(q * 8 + sd) % 4], x, y)
        # 道士
        if pose_override is not None:
            pose_override()
        else:
            self.dao(g, t, k)
        # 文字
        if k >= SWEEP_END + 3.5 and k < C - 0.6:
            self.text(g, "以至于无为", span(k, SWEEP_END + 3.5, SWEEP_END + 5.0))
        else:
            self.text(g, "损之又损")
        self.mx(g, t, k, total_piled, blow)

    def dao(self, g: Gfx, t: float, k: float):
        if k >= SWEEP_END:  # 风来：停手、抬头看叶子飞走，然后眯眼笑
            w = k - SWEEP_END
            look = -1.5 * span(w, 1.0, 1.6) * (1 - span(w, 4.0, 4.6))
            eye = "closed" if 4.2 < w < 9.5 else None
            bob = 0.0
            if 4.5 < w < 9.5:
                bob = 0.5 * (math.sin(w * 7) > 0)  # 笑得一抖一抖
            self.figure(g, k, t, BX0, 0, look=look, eye=eye, bob=bob)
            if 4.4 < w < 6.0:
                from .x5_common import note
                note(g, DX + 8, 22 - (w - 4.4) * 4)
            return
        a, b = self._pause_win(self._cyc)
        if a <= k < b:  # 一片叶子落在发髻上：停下，晃晃脑袋
            w = k - a
            shake = math.sin(w * 30) * 1.2 if 4.2 < w < 5.0 else 0.0
            look = -1.0 if w < 4.2 else 0.0
            self.figure(g, k, t, BX0, 0, look=look, shake=shake)
            hx, hy = DX + 1.5 + 0.8 + shake, GY - 21 - 4.8 - 4 - 3.2 - 1
            if w < 2.0:  # 飘下来
                q = ease_out(w / 2.0)
                g.blit(FALLING[int(w * 6) % 4], lerp(hx + 14, hx, q) + math.sin(w * 5) * 3 * (1 - q), lerp(-4, hy - 1, q))
            elif w < 4.6:
                g.blit(FALLING[0], hx + (shake if w > 4.2 else 0), hy - 1)
                if 2.0 < w < 3.2:  # 一愣
                    g.d.line((hx + 8, hy - 6, hx + 8, hy - 3), fill=1)
                    g.px(hx + 8, hy - 1)
            elif w < 6.5:  # 甩掉
                q = (w - 4.6) / 1.9
                g.blit(LEAVES[int(w * 8) % 4], hx - q * 10, hy + ease_in(q) * (GY - hy - 1))
            elif w < 8:
                g.px(hx - 10, GY - 1)
            return
        bx, lift = stroke((k % P) / P)
        self.figure(g, k, t, bx, lift)

    def mx(self, g: Gfx, t: float, k: float, piled: int, blow: float):
        # 一片银杏叶从上往下飘，底下是叶堆
        h = int(round(clamp(piled / 20) * 3 * (1 - blow)))
        for r in range(h):
            w = 2 + r * 2 if r < 2 else 6
            for x in range(4 - w // 2, 4 + w // 2):
                g.mx[7 - r, x] = True
        if h == 0:
            g.mx[7, 2:6] = True
        q = (t % 3.0) / 3.0
        y = int(q * (7 - max(h, 1)))
        x = int(3 + math.sin(t * 2.6) * 2.4)
        g.mx_set(x, y)
        g.mx_set(x + 1, y)
        g.mx_set(x, y - 1 if int(t * 3) % 2 else y + 1)
        if k >= SWEEP_END + 1 and k < SWEEP_END + 3:  # 风：一行行横扫
            r = int((k - SWEEP_END - 1) * 8) % 8
            g.mx[r, :] = True

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        if t >= T - 0.8:
            # 放下扫帚，过渡到 hold(0)
            q = ease_out(span(t, T - 0.8, T))

            def pose():
                ht = lerp(14, 0, q)
                self.figure(g, 0, t, lerp(DX + 4, BX0, q), ht)
            self.draw_static(g, t, pose)
            self.text(g, "损之又损", span(t, 1.6, T - 0.6))
            return

        def pose():
            # 扛着扫帚走进来
            p = ease_out(span(t, 0, T - 0.8))
            x = lerp(-14, DX, p)
            stp = t * 9 if p < 0.98 else None
            hand = (x + 5, GY - 17)
            pz = daoshi(g, x, GY, 1, hands=[hand, (x + 2, GY - 20)], step=stp, lean=1)
            # 扫帚扛在肩上，帚头在身后
            g.d.line((x + 9, GY - 23, x - 16, GY - 13), fill=1)
            for j in range(6):
                g.d.line((x - 16, GY - 13, x - 24, GY - 15 + j * 1.6), fill=1)
            g.d.rectangle((hand[0] - 1, hand[1] - 1, hand[0] + 1, hand[1] + 1), fill=1)
        self.draw_static(g, t, pose)
        self.text(g, "损之又损", span(t, 1.6, T - 0.6))

    def draw_static(self, g: Gfx, t: float, pose):
        """入场：树和地先在，叶子开始落（hold 从 t=0 接上）"""
        self.flagstones(g)
        self.tree(g, t)
        self.pile(g, 0)
        pose()
        self.mx(g, t, 0, 0, 0)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.draw(g, t)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        k0 = self._ht % C
        bx, lift = self._broom_at(k0)
        q = ease_in_out(span(t, 0, 0.5))

        def pose():  # 扫帚停下，躬身一礼
            self.figure(g, k0, self._ht, lerp(bx, BX0, q), lerp(lift, 0, q), eye="closed" if t > 0.3 else None,
                        bob=1.0 * ease_out(span(t, 0.3, 0.7)), bow=2.5 * ease_out(span(t, 0.3, 0.7)))
        self.draw(g, self._ht, pose)
        fade_box(g, 1 - ease_in(span(t, 0.4, T)))
        if t > 0.5:
            g.mx[:] = False
            g.mx[7, 2:6] = True
