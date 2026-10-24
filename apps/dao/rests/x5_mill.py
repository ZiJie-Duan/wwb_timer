"""推磨：磨豆浆。石磨架在木台上，磨杠横伸出来，小道士推着磨杠绕磨一圈又一圈（转到后面时被磨挡住、
人显得远一点）；上扇磨盘的纹路随着转，豆浆从磨嘴流进木桶，桶里慢慢满起来。
满了：停下来提走满桶、换个空桶回来。彩蛋：一只小老鼠溜过来叼走一粒掉在地上的豆子。
相传豆腐始于淮南王刘安（李时珍《本草纲目》：“豆腐之法，始于汉淮南王刘安”）。
左侧竖写“周行而不殆”（《道德经》二十五章：独立而不改，周行而不殆）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import daoshi, dpoly, fade_box, phase

GY = 60
CX = 70              # 磨的轴
RW = 30              # 磨杠长（人绕的半径）
REV = 7.0            # 一圈几秒
FILL = 56.0          # 一桶接满要推多久（秒）
SWAP = 8.0           # 换桶
BIG = FILL + SWAP
BUCKET = (100, 110)  # 桶左右
SPOUT = (97, 50)
MOUSE = [Sprite("""
..##...
.####.#
######.
.#..#..
"""), Sprite("""
..##...
.####.#
######.
#....#.
""")]


@register
class Mill(Rest):
    id = "x5.mill"
    name = "推磨"
    desc = "推着磨杠绕石磨一圈圈走，豆浆流进木桶，满了换桶；小老鼠来偷豆子"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.s = self.rng.randrange(1000)
        self._ht = 0.0

    # ------------------------------------------------------------ 磨

    def stand(self, g: Gfx):
        d = g.d
        d.rectangle((CX - 26, 48, CX + 26, 50), fill=1)          # 台面
        for x in (CX - 23, CX + 22):
            d.rectangle((x, 51, x + 1, GY - 1), fill=1)          # 腿
        d.line((CX - 23, 56, CX + 23, 56), fill=1)              # 横撑

    def mill(self, g: Gfx, ang: float):
        d = g.d
        # 磨盘（接浆的槽）+ 磨嘴
        d.rectangle((CX - 22, 44, CX + 22, 47), fill=0, outline=1)
        d.polygon([(CX + 22, 44), (SPOUT[0], 46), (SPOUT[0], 48), (CX + 22, 47)], fill=0, outline=1)
        # 下扇
        d.rectangle((CX - 16, 38, CX + 16, 44), fill=0, outline=1)
        for j in range(4):
            g.px(CX - 12 + j * 8, 41)
        # 上扇：转起来时竖纹横着走
        d.rectangle((CX - 16, 30, CX + 16, 37), fill=0, outline=1)
        d.line((CX - 16, 37, CX + 16, 37), fill=1)
        for j in range(6):
            a = ang + j * math.pi / 3
            if math.sin(a) > 0.1:   # 只画朝向我们的一面
                x = CX + 15 * math.cos(a)
                d.line((x, 31, x, 36), fill=1)
        # 磨眼里的豆子
        d.ellipse((CX - 5, 27, CX + 5, 31), fill=0, outline=1)
        for j in range(5):
            g.px(CX - 3 + j * 1.5, 28 + (j % 2))

    def pole(self, g: Gfx, ang: float):
        """磨杠：从上扇边上横伸出去。返回杠头 (x, y, z)"""
        z = math.sin(ang)
        ex = CX + RW * math.cos(ang)
        ey = 34 + 3 * z
        sx_ = CX + 16 * math.cos(ang)
        g.d.line((sx_, 34 + 1.5 * z, ex, ey), fill=1)
        g.d.line((sx_, 35 + 1.5 * z, ex, ey + 1), fill=1)
        return ex, ey, z

    def bucket(self, g: Gfx, level: float, x0: float = BUCKET[0], y_off: float = 0.0):
        x1 = x0 + (BUCKET[1] - BUCKET[0])
        top = 51 + y_off
        g.d.polygon([(x0, top), (x1, top), (x1 - 1, GY - 1 + y_off), (x0 + 1, GY - 1 + y_off)], fill=0, outline=1)
        g.d.line((x0, top + 3, x1, top + 3), fill=1)
        g.d.line((x0 + 1, GY - 3 + y_off, x1 - 1, GY - 3 + y_off), fill=1)
        if level > 0:  # 浆面（从桶口看进去的一道）
            y = lerp(GY - 3, top + 1, clamp(level)) + y_off
            g.d.line((x0 + 2, y, x1 - 2, y), fill=1)
            if level > 0.98:
                g.px(x0 - 1, top + 2)
        # 提梁
        g.d.arc((x0 + 1, top - 5, x1 - 1, top + 3), 180, 360, fill=1)

    # ------------------------------------------------------------ 人

    def pusher(self, g: Gfx, ang: float, t: float, walking: bool = True, front_layer: bool = True):
        """按杠头位置画人；z>0 在磨前（画在磨后面调用），z<0 在磨后"""
        ex, ey, z = self.pole_end(ang)
        if (z >= 0) != front_layer:
            return None
        f = -1 if z > 0 else 1                      # 前半圈往左走，后半圈往右走
        s = 1.0 + 0.06 * z
        gy = GY - 4.5 * (1 - z)
        x = ex - f * 7
        lean = 3.0
        hands = [(ex, ey + 0.5), (ex - f * 2, ey + 1)]
        eye = "closed" if (t % 4.0) < 0.14 else "open"
        return daoshi(g, x, gy, f, hands=hands, lean=lean, s=s, step=t * 7 if walking else None, eye=eye)

    @staticmethod
    def pole_end(ang: float):
        z = math.sin(ang)
        return CX + RW * math.cos(ang), 34 + 3 * z, z

    # ------------------------------------------------------------ 主画面

    def angle(self, t: float) -> float:
        """磨转了多少（换桶时不转）：按“推了多久”算"""
        big, k = phase(t, BIG)
        pushed = big * FILL + min(k, FILL)
        return -math.pi / 2 + pushed * 2 * math.pi / REV + math.pi   # t=0 时人在正前方

    def draw(self, g: Gfx, t: float, final: float = 0.0):
        big, k = phase(t, BIG)
        ang = self.angle(t)
        level = clamp(k / FILL) if k < FILL else 1.0
        swapping = k >= FILL
        self.text(g)
        g.d.line((15, GY, 127, GY), fill=1)
        # 后面的人（被磨挡住）
        if not swapping:
            self.pusher(g, ang, t, front_layer=False)
            if math.sin(ang) < 0:
                self.pole(g, ang)
        self.stand(g)
        self.mill(g, ang)
        if swapping or math.sin(ang) >= 0:
            self.pole(g, ang)
        # 豆浆从磨嘴流下
        flowing = not swapping
        if flowing:
            for j in range(4):
                y = 49 + ((t * 18 + j * 3) % 10)
                if y < lerp(GY - 3, 52, level):
                    g.px(SPOUT[0] + 1 + (j % 2) * 0.5, y)
        if swapping:
            self.swap(g, t, k - FILL, final)
        else:
            self.bucket(g, level)
            self.pusher(g, ang, t, front_layer=True)
        self.mouse(g, t)
        self.mx(g, ang, level, swapping)

    def swap(self, g: Gfx, t: float, k: float, final: float):
        """桶满了：松开磨杠，提起满桶走出右边，提个空桶回来放好，回到杠头"""
        ex, ey, z = self.pole_end(self.angle(t))
        x_pole = ex + 7
        if k < 1.0:  # 走到桶边
            x = lerp(x_pole, BUCKET[0] - 6, ease_in_out(k))
            self.bucket(g, 1.0)
            daoshi(g, x, GY, 1, step=t * 9 if k < 0.95 else None)
            return
        if k < 3.4:  # 提着满桶出去
            q = span(k, 1.4, 3.4)
            x = lerp(BUCKET[0] - 6, 140, ease_in(q))
            crouch = math.sin(span(k, 1.0, 1.4) * math.pi) * 0.5
            hx, hy = x + 8, GY - 12 + crouch * 4
            bx = BUCKET[0] if k < 1.3 else hx - 5
            daoshi(g, x, GY, 1, hands=[(hx, hy), None], crouch=crouch, lean=1, step=t * 9 if k > 1.4 else None)
            self.bucket(g, 1.0, bx, (hy + 4 - 51) if k >= 1.3 else 0)
            return
        if k < 6.0:  # 提着空桶回来
            q = span(k, 3.6, 6.0)
            x = lerp(140, BUCKET[1] + 6, ease_out(q))
            hx, hy = x - 8, GY - 12
            if k >= 3.6:
                daoshi(g, x, GY, -1, hands=[(hx, hy), None], lean=1, step=t * 9 if q < 0.95 else None)
                self.bucket(g, 0.0, hx - 5, hy + 4 - 51)
            return
        # 放下、回杠头
        q = ease_in_out(span(k, 6.0, 6.5))
        self.bucket(g, 0.0, lerp(BUCKET[1] + 6 - 8 - 5, BUCKET[0], q), lerp(GY - 12 + 4 - 51, 0, q))
        x = lerp(BUCKET[1] + 6, x_pole, ease_in_out(span(k, 6.5, SWAP - 0.4)))
        q = ease_in_out(span(k, SWAP - 0.4, SWAP))
        hands = [(lerp(x - 1, ex, q), lerp(49, ey + 0.5, q)), (lerp(x + 1, ex + 2, q), lerp(50, ey + 1, q))]
        daoshi(g, x, GY, -1, hands=hands, lean=3 * q, step=t * 9 if k < SWAP - 0.45 else None)

    def mouse(self, g: Gfx, t: float):
        from .x5_common import event
        ev = event(t, 43.0, 7.0, self.s + 3)
        bean = (CX - 10, GY - 1)
        if not ev or rand(ev[0], self.s + 8) < 0.0:
            g.px(*bean)  # 地上一粒掉下的豆子
            return
        k = ev[1]
        if k < 2.5:  # 从左边溜进来
            x = lerp(-8, bean[0] - 7, ease_out(k / 2.5))
            g.px(*bean)
            g.blit(MOUSE[int(k * 10) % 2], x, GY - 4)
        elif k < 3.5:  # 闻一闻、叼起来
            g.blit(MOUSE[0], bean[0] - 7 + (1 if int(k * 6) % 2 else 0), GY - 4)
            if k < 3.0:
                g.px(*bean)
        else:  # 叼着跑
            x = lerp(bean[0] - 7, -10, ease_in(span(k, 3.5, 5.0)))
            m = MOUSE[int(k * 12) % 2].flip()
            g.blit(m, x, GY - 4)
            g.px(x, GY - 3)

    def text(self, g: Gfx, a: float = 1.0):
        s = "周行而不殆"
        g.vtext(2, 1, s[:int(round(len(s) * clamp(a)))])

    def mx(self, g: Gfx, ang: float, level: float, swapping: bool):
        # 俯看石磨：一圈 + 转动的磨杠 + 磨眼
        for y in range(8):
            for x in range(8):
                r = math.hypot(x - 3.5, y - 3.5)
                if 2.6 < r < 3.6:
                    g.mx[y, x] = True
        g.mx_set(3, 3)
        g.mx_set(4, 4)
        ca, sa = math.cos(ang), math.sin(ang)
        for rr in (2.0, 3.2, 4.3):
            g.mx_set(int(round(3.5 + ca * rr)), int(round(3.5 + sa * rr)))
        if swapping:
            g.mx_level = 1

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        """走过来握住磨杠，石磨吱呀一声转起来"""
        T = self.T["enter"]
        ang = self.angle(0)
        ex, ey, z = self.pole_end(ang)
        self.text(g, span(t, 1.2, T - 0.3))
        g.d.line((15, GY, 127, GY), fill=1)
        self.stand(g)
        self.mill(g, ang)
        self.pole(g, ang)
        self.bucket(g, 0.0)
        x_end = ex + 7
        x = lerp(-12, x_end, ease_out(span(t, 0, T - 0.6)))
        if t < T - 0.6:
            daoshi(g, x, GY, 1, step=t * 9)
        else:
            q = ease_in_out(span(t, T - 0.6, T))
            hands = [(lerp(x_end + 2, ex, q), lerp(48, ey + 0.5, q)), (lerp(x_end, ex + 2, q), lerp(49, ey + 1, q))]
            daoshi(g, x_end, GY, -1, hands=hands, lean=3 * q)
        self.mouse(g, 0.0)
        self.mx(g, ang, 0, False)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.draw(g, t)

    def exit(self, g: Gfx, t: float):
        self.draw(g, self._ht)
        fade_box(g, 1 - ease_in(span(t, 0.15, self.T["exit"])))
        if t > 0.6:
            g.mx[:] = False
            g.mx_set(3, 3)
            g.mx_set(4, 4)
