"""烧火：斋堂的砖灶，大铁锅扣着木锅盖，烟囱冒烟。小道士坐小板凳守灶门：转身从柴堆抽一根柴塞进灶膛，
火一旺；拿吹火筒鼓腮吹三口，火苗蹿起；锅里水开，盖缝冒白汽。
彩蛋：一口倒烟扑了满脸——熏成花脸，眼冒金星，“咳咳”；水开得太猛，锅盖噗噗直跳。
左侧竖写“若烹小鲜”（《道德经》六十章：治大国，若烹小鲜）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import flame, smoke_wisp
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x5_common import bubble, daoshi, dellipse, dpoly, event, fade_box, phase

GY = 60
S0, S1, STOP = 72, 127, 34          # 灶台左右、台面
DOOR = (76, 90, 45, 57)             # 灶门 x0 x1 拱顶 底
X = 52                              # 坐的位置
SEAT = 56                           # 板凳面
P = 12.0
LX0, LX1 = 78, 110                  # 锅盖
LC = (LX0 + LX1) // 2


@register
class Cook(Rest):
    id = "x5.cook"
    name = "烧火"
    desc = "坐小板凳守灶门添柴、吹火筒吹火，锅盖冒汽；偶尔倒烟熏成花脸"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.s = self.rng.randrange(1000)
        self._ht = 0.0

    # ------------------------------------------------------------ 灶

    def stove(self, g: Gfx, t: float, fire: float, lid_hop: float = 0.0, steam: float = 1.0):
        d = g.d
        d.rectangle((S0, STOP, S1, GY), fill=0, outline=1)
        d.rectangle((S0 - 2, STOP - 2, S1 + 2, STOP), fill=1)            # 台面
        for r, y in enumerate(range(STOP + 7, GY, 7)):                   # 砖缝（疏一点）
            for x in range(S0 + 2 + (r % 2) * 7, S1 - 2, 14):
                d.line((x, y, x + 9, y), fill=1)
                d.line((x + 11, y - 3, x + 11, y - 1), fill=1)
        x0, x1, ytop, ybot = DOOR
        d.rectangle((x0, ytop + 3, x1, ybot), fill=0, outline=1)       # 灶门
        d.chord((x0, ytop, x1, ytop + 7), 180, 360, fill=0, outline=1)
        d.rectangle((x0 + 1, ytop + 3, x1 - 1, ybot - 1), fill=0)
        # 灶膛里的火
        cx = (x0 + x1) / 2
        if fire > 0:
            flame(g, cx - 2, ybot - 1, 5 + fire * 2, 4 + fire * 6, t, 1)
            flame(g, cx + 3, ybot - 1, 4 + fire, 3 + fire * 4, t + 0.3, 2)
        for j in range(4):  # 炭
            g.px(x0 + 2 + j * 3, ybot - 1)
        # 烟囱
        d.rectangle((116, 4, 123, STOP - 2), fill=0, outline=1)
        d.rectangle((114, 2, 125, 5), fill=1)
        for y in range(11, STOP - 2, 8):
            d.line((117, y, 122, y), fill=1)
        smoke_wisp(g, 119.5, 1, 6 + fire * 2, t, self.s, sway=2, speed=4, drift=-4)
        # 锅 + 木盖
        hop = lid_hop
        d.chord((LX0, STOP - 9 - hop, LX1, STOP + 5 - hop), 180, 360, fill=0, outline=1)
        d.line((LX0 + 2, STOP - 2 - hop, LX1 - 2, STOP - 2 - hop), fill=1)
        for x in (LC - 9, LC, LC + 9):
            d.line((x, STOP - 7 - hop + (1 if x != LC else 0), x, STOP - 2 - hop), fill=1)
        d.rectangle((LC - 3, STOP - 11 - hop, LC + 3, STOP - 9 - hop), fill=1)   # 盖钮
        d.line((LX0 - 2, STOP - 1, LX1 + 2, STOP - 1), fill=1)                   # 锅沿
        # 白汽
        if steam > 0:
            for i, sx in enumerate((LX0 + 2, LX1 - 3)):
                h = (7 + 6 * steam) * (0.7 + 0.3 * noise(t * 0.7 + i, 3))
                smoke_wisp(g, sx, STOP - 3 - hop, h, t, self.s + 5 + i, sway=2.5, speed=5, drift=(-1 if i == 0 else 1) * 3)

    def woodpile(self, g: Gfx, n: int):
        """身后的柴：一根根横放的劈柴"""
        for i in range(n):
            row, col = divmod(i, 3)
            x = 16 + col * 3 + row * 2
            y = GY - 3 - row * 3
            g.d.rounded_rectangle((x, y, x + 15, y + 2), radius=1, fill=0, outline=1)
            g.px(x + 15, y + 1)

    def stool(self, g: Gfx, x: float):
        g.d.rectangle((x - 6, SEAT, x + 6, SEAT + 1), fill=1)
        g.d.line((x - 5, SEAT + 2, x - 5, GY), fill=1)
        g.d.line((x + 5, SEAT + 2, x + 5, GY), fill=1)

    # ------------------------------------------------------------ 状态

    def state(self, t: float):
        n, c = phase(t, P)
        fire = 0.6 + 0.4 * noise(t * 0.5, 2)
        if 3.4 <= c < 4.4:
            fire += 0.8 * (1 - span(c, 3.6, 4.4))             # 添柴后一旺
        for b in (5.2, 6.4, 7.6):                               # 吹三口
            if b <= c < b + 1.0:
                fire += 0.9 * math.sin(span(c, b + 0.3, b + 1.0) * math.pi)
        return n, c, clamp(fire, 0, 2)

    def blowback(self, t: float):
        """倒烟：选在某一轮第三口吹的时候。返回 (发生后的秒数) 或 None"""
        n, c = phase(t, P)
        for m in (n, n - 1):
            if m >= 1 and rand(m, self.s + 3) < 0.28:
                k = (n - m) * P + c - 7.6
                if 0 <= k < 9.0:
                    return k
        return None

    # ------------------------------------------------------------ 画

    def draw(self, g: Gfx, t: float, final: float = 0.0):
        t += 8.8  # 从“守着火”那段开始，接得上入场
        n, c, fire = self.state(t)
        bb = self.blowback(t)
        ev_lid = event(t, 53.0, 4.0, self.s + 7)
        hop = 0.0
        steam = 1.0
        if ev_lid:
            k = ev_lid[1]
            hop = abs(math.sin(k * 9)) * 3 * (1 - span(k, 2.5, 4.0))
            steam = 2.0
        self.stove(g, t, fire * (1 - final), hop, steam)
        if ev_lid and hop > 1.5:
            for j in range(4):
                a = -math.pi / 2 + (j - 1.5) * 0.6
                g.px(LC + math.cos(a) * (14 + hop * 2), STOP - 8 - hop + math.sin(a) * (6 + hop))
        # 柴堆：抽一根少一根，一轮里补满（看不出来）
        pile = 6 - (1 if 1.0 <= c else 0)
        self.woodpile(g, pile)
        self.stool(g, X)
        # 人
        f, lean, look = 1, 2.0, 0.0
        hands = [None, None]
        stick = None
        tube = False
        eye = "closed" if (t % 4.3) < 0.14 else "open"
        if c < 1.0:  # 转身去抽柴
            f = -1
            q = ease_in_out(span(c, 0.1, 0.8))
            lean = 4 * q
            hands = [(lerp(X - 4, 38, q), lerp(48, GY - 5, q)), None]
        elif c < 1.6:  # 抽出来
            f = -1
            q = ease_in_out(span(c, 1.0, 1.6))
            lean = 4 * (1 - q)
            hx, hy = lerp(38, X - 4, q), lerp(GY - 5, 46, q)
            hands = [(hx, hy), None]
            stick = (hx - 6 + q * 6, hy, hx + 10 - q * 2, hy)
        elif c < 3.4:  # 转回来，把柴往灶膛里送
            q = ease_in_out(span(c, 1.8, 3.2))
            lean = 2 + 3 * q
            hx, hy = lerp(X + 4, X + 11, q), lerp(46, 52, q)
            hands = [(hx, hy), (hx - 3, hy)]
            ln = lerp(16, 6, ease_in(span(c, 2.6, 3.3)))
            stick = (hx - 2, hy, hx - 2 + ln, hy + 1.5)
        elif c < 4.8:  # 缩手
            q = ease_out(span(c, 3.4, 4.2))
            hands = [(lerp(X + 11, X + 5, q), lerp(52, 49, q)), None]
            lean = 5 - 3 * q
        elif c < 8.8:  # 拿吹火筒吹
            tube = True
            lean = 5
        else:  # 守着火，打个哈欠
            q = span(c, 9.4, 10.6)
            if 0 < q < 1:
                look = -1.2 * math.sin(q * math.pi)
                eye = "closed"
            lean = 1.5
        if final > 0:
            lean = lerp(lean, 1.5, final)
        if tube:
            puff = 0.0
            for b in (5.2, 6.4, 7.6):
                if b <= c < b + 1.0:
                    puff = math.sin(span(c, b + 0.2, b + 0.8) * math.pi)
            # 吹火筒：从嘴到灶门
            sy = SEAT - 21 + 6 * 0.6
            mx_, my_ = X + lean + 4.5, sy - 4.0
            ex, ey = DOOR[0] + 2, DOOR[3] - 4
            hands = [(lerp(mx_, ex, 0.45), lerp(my_, ey, 0.45) + 1), (lerp(mx_, ex, 0.2), lerp(my_, ey, 0.2) + 1)]
        pz = daoshi(g, X, SEAT, f, hands=hands, lean=lean, crouch=0.6, sit=True, eye=eye, look=look)
        if stick:
            g.d.line(stick, fill=1)
            g.d.line((stick[0], stick[1] + 1, stick[2], stick[3] + 1), fill=1)
        if tube:
            hx, hy = pz.head
            mx_, my_ = hx + 4, hy + 1.5
            ex, ey = DOOR[0] + 2, DOOR[3] - 4
            g.d.line((mx_, my_, ex, ey), fill=1)
            g.d.line((mx_, my_ + 1, ex, ey + 1), fill=1)
            if puff > 0.2:  # 鼓腮
                g.d.ellipse((hx + 1, hy - 0.5, hx + 3 + puff * 1.5, hy + 3), fill=1)
                for j in range(3):  # 吹出的气
                    u = (c * 3 + j / 3) % 1
                    g.px(lerp(mx_, ex, u), lerp(my_, ey, u) - 2)
        # 倒烟
        if bb is not None:
            self.soot(g, pz, bb)
        # 字
        self.text(g)
        self.mx(g, t, fire, bb)

    def soot(self, g: Gfx, pz, k: float):
        hx, hy = pz.head
        if k < 0.4:  # 一团烟从灶门扑出来
            u = ease_out(k / 0.4)
            cx, cy = lerp(DOOR[0], hx + 2, u), lerp(DOOR[3] - 6, hy, u)
            r = 3 + u * 7
            dellipse(g, (cx - r, cy - r * 0.8, cx + r, cy + r * 0.8), 0.5)
        elif k < 1.6:  # 罩住脸，慢慢散
            u = span(k, 0.4, 1.6)
            r = 10 + u * 6
            lv = 0.5 * (1 - u)
            if lv > 0.05:
                dellipse(g, (hx - r, hy - r * 0.8 - u * 4, hx + r, hy + r * 0.8 - u * 4), lv, None)
        if k >= 1.0:  # 花脸：脸上一片灰
            if k < 7.5:
                dellipse(g, (hx - 1, hy - 1, hx + 3.5, hy + 3), 0.4, None)
            if k < 3.0:  # 眼冒金星
                g.d.line((hx + 1, hy - 0.5, hx + 3, hy + 1.5), fill=1)
                g.d.line((hx + 1, hy + 1.5, hx + 3, hy - 0.5), fill=1)
                for j in range(3):
                    a = k * 6 + j * 2.1
                    g.px(hx + math.cos(a) * 7, hy - 7 + math.sin(a) * 2)
        if 1.2 < k < 3.6:
            hop = 1 if int(k * 6) % 2 else 0
            bubble(g, hx - 24, hy - 21 - hop, "咳咳")

    def text(self, g: Gfx, a: float = 1.0):
        s = "若烹小鲜"
        g.vtext(2, 2, s[:int(round(len(s) * clamp(a)))])

    def mx(self, g: Gfx, t: float, fire: float, bb):
        if bb is not None and bb < 2.0:  # 一团烟
            for y in range(8):
                for x in range(8):
                    g.mx[y, x] = math.hypot(x - 3.5, y - 3.5) < 2 + bb * 2 and (x + y + int(t * 6)) % 2 == 0
            return
        # 灶火：底下一排炭，火苗随旺度跳
        g.mx[7, :] = True
        h = 2 + fire * 2.2
        for x in range(1, 7):
            hh = h * (0.6 + 0.6 * noise(t * 6 + x * 1.7, x)) * (1 - abs(x - 3.5) / 5)
            for y in range(7, 7 - int(round(hh)) - 1, -1):
                g.mx_set(x, y)
        if fire > 1.3:
            g.mx_level = 3
            if int(t * 8) % 3 == 0:
                g.mx_set(int(2 + noise(t * 3, 5) * 4), 0)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        """抱一捆柴走来，放下、坐上板凳，划火——灶膛亮起来"""
        T = self.T["enter"]
        fire = ease_out(span(t, 2.2, T)) * 0.6
        self.stove(g, t, fire, 0.0, span(t, 2.4, T))
        self.stool(g, X)
        if t < 1.6:
            x = lerp(-14, X - 2, ease_out(span(t, 0, 1.6)))
            pz = daoshi(g, x, GY, 1, hands=[(x + 6, 44), (x + 4, 45)], step=t * 11 if t < 1.5 else None)
            for j in range(3):
                g.d.rounded_rectangle((x - 4, 41 - j * 3, x + 11, 43 - j * 3), radius=1, fill=0, outline=1)
            self.woodpile(g, 0)
        else:
            self.woodpile(g, int(min(6, (t - 1.6) * 12)))
            q = ease_in_out(span(t, 1.6, 2.2))
            if q < 1:
                # 坐下
                daoshi(g, X - 2 + q * 2, lerp(GY, SEAT, q), 1, crouch=0.6 * q, lean=2 * q, sit=q > 0.5)
            else:
                lean = 2.0 + 3 * math.sin(span(t, 2.2, 2.9) * math.pi)
                hands = [(X + 11 - 6 * span(t, 2.6, T), 51), None] if t < T - 0.1 else [None, None]
                daoshi(g, X, SEAT, 1, crouch=0.6, lean=lean, sit=True, hands=hands)
                if t < 2.7:  # 火柴一亮
                    flame(g, X + 12, 50, 3, 5, t, 4)
        self.text(g, span(t, 1.2, T - 0.3))
        self.mx(g, t, fire, None)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.draw(g, t)

    def exit(self, g: Gfx, t: float):
        self.draw(g, self._ht, final=ease_in_out(span(t, 0, 0.6)))
        fade_box(g, 1 - ease_in(span(t, 0.35, self.T["exit"])))
        if t > 0.7:
            g.mx[:] = False
            g.mx[7, :] = True
