"""燃香：示范法事（其他法事照这个结构写）。

入场：一只手（宽袖）握着三炷香从右上方伸来，插进香炉，手收回；火柴划着，依次点燃三炷香，青烟升起。
持续：香随计时慢慢变短（一轮 10 分钟），香头明灭，三缕烟扭着上升，偶尔落一截香灰。
      一炷烧完：一口气吹走残香，手再插上三炷新香点燃（“再加一根香”），右侧“第几炷”加一。
中断：手指依次掐灭香头，烟散尽，右侧变成“暂熄”。
恢复：火柴重新点燃香头，烟再起。
圆满：一口气吹过，烟被吹弯、残香吹散，香炉放光，“功德圆满”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import flame, smoke_wisp
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register

CX = 64          # 香炉中心
RIM = 46         # 香灰面
STICK_X = (57, 64, 71)
FULL = 24        # 新香露出香灰的长度
STUB = 3         # 烧完剩下的
RENEW = 5.0      # 续香过渡（秒）

FIST = Sprite("""
  ..#####.....
  .#.....##...
  #.###....#..
  #.....#..#..
  #.###..#..#.
  #.....#...#.
  #.###.....#.
  #.........#.
  .#.......#..
  ..#######...
""")
PINCH = Sprite("""
  .##...##.
  .##...##.
  .##...##.
  ..##.##..
  ...#.#...
""")


def censer(g: Gfx, glow: float = 0.0):
    """三足鼎式香炉"""
    d = g.d
    d.rectangle((44, RIM - 6, 47, RIM), outline=1)          # 双耳
    d.rectangle((81, RIM - 6, 84, RIM), outline=1)
    d.line((42, RIM, 86, RIM), fill=1)                       # 口沿
    d.polygon([(44, RIM + 1), (84, RIM + 1), (78, 57), (50, 57)], outline=1, fill=0)
    for x in range(50, 79, 4):                               # 腹部回纹
        d.line((x, 50, x + 2, 50), fill=1)
        d.point((x, 52))
        d.point((x + 2, 52))
    d.line((51, 54, 77, 54), fill=1)
    for x in (54, 64, 74):                                   # 三足
        d.rectangle((x - 1, 58, x, 62), fill=1)
    if glow > 0:  # 圆满时炉身放光：放射线
        for i in range(12):
            a = i / 12 * 2 * math.pi + glow * 1.5
            r0, r1 = 26, 26 + 10 * glow
            d.line((CX + math.cos(a) * r0, 50 + math.sin(a) * r0 * 0.6, CX + math.cos(a) * r1,
                    50 + math.sin(a) * r1 * 0.6), fill=1)


def sleeve_fist(g: Gfx, fx: float, fy: float, sticks: bool = True, length: float = FULL):
    """道袍宽袖 + 握香的拳；(fx, fy) 为拳心。sticks：拳里握着三炷香"""
    if sticks:
        for dx in (-7, 0, 7):
            g.d.line((fx + dx * 0.9, fy - 8, fx + dx, fy - 6 + length), fill=1)
    # 手腕、袖子（抖动灰度 = 布料），袖口一道镶边
    g.d.polygon([(fx + 4, fy - 3), (fx + 12, fy - 8), (fx + 14, fy - 2), (fx + 6, fy + 4)], fill=0, outline=1)
    sleeve = [(fx + 10, fy - 10), (fx + 30, fy - 34), (fx + 70, fy - 34), (fx + 70, fy + 2), (fx + 22, fy + 8),
              (fx + 14, fy + 2)]
    g.d.polygon(sleeve, fill=0)
    g.shade_poly(sleeve, 0.25)
    g.d.line((fx + 13, fy - 9, fx + 18, fy + 5), fill=1)
    g.d.line((fx + 15, fy - 11, fx + 20, fy + 6), fill=1)
    g.d.line((fx + 34, fy - 20, fx + 60, fy - 6), fill=0)  # 衣褶
    g.blit(FIST, fx - 6, fy - 5)


def match(g: Gfx, x: float, y: float, t: float, lit: bool = True):
    """火柴：头在 (x, y)，杆向右下"""
    g.d.line((x + 1, y + 1, x + 14, y + 10), fill=1)
    g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
    if lit:
        flame(g, x, y - 1, 5, 9, t, 3)


@register
class IncenseRitual(Ritual):
    id = "r.incense"
    name = "燃香"
    desc = "插香、点火，香随计时燃短，烧完吹散再续一炷"
    T = {"enter": 4.2, "interrupt": 1.6, "resume": 1.8, "complete": 4.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 画面零件

    def length(self, e: float) -> float:
        p = (e % self.CYCLE) / self.CYCLE
        return lerp(FULL, STUB, p)

    def sticks(self, g: Gfx, length: float, lit: tuple = (1, 1, 1), t: float = 0.0, smoke: float = 1.0,
               drop_x: float = 0.0):
        for i, x in enumerate(STICK_X):
            x += drop_x * (i + 1)
            top = RIM - length
            g.d.line((x, RIM - 1, x, top), fill=1)
            if lit[i]:
                on = noise(t * 3 + i * 7, self.seed + i) > 0.35
                g.d.rectangle((x - 1 if on else x, top - 1, x + (1 if on else 0), top), fill=1)
                if smoke > 0:
                    smoke_wisp(g, x, top - 3, (top - 3) * smoke, t, self.seed * 7 + i, sway=3.0 + i, speed=5.0,
                               drift=(i - 1) * 6)

    def ash(self, g: Gfx, e: float, length: float):
        """不时落下一截香灰（按 e 定时，断线重连也一致）"""
        top = RIM - length
        for i, x in enumerate(STICK_X):
            period = 17 + i * 3
            k = (e + i * 5.3) % period
            if k < 1.0 and length > STUB + 1:
                y = top + ease_in(k) * (RIM - top - 1)
                g.px(x + (1 if i % 2 else -1) * k * 2, y)
        # 炉口积灰
        heap = int(clamp((e % self.CYCLE) / self.CYCLE) * 10)
        for j in range(heap):
            g.px(52 + rand(j, self.seed) * 24, RIM - 1)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        left = "心香一炷"
        k = int(round(a * len(left)))
        g.vtext(3, 4, left[:k])
        r = right if right is not None else f"第{cn_num(n)}炷"
        g.vtext(113, 4, r[:max(0, int(round(a * len(r))))])

    def mx(self, g: Gfx, length: float, lit: tuple, t: float, smoke: bool = True):
        g.mx[7, 1:7] = True
        h = 1 + int(round((length - STUB) / (FULL - STUB) * 4))
        for i, col in enumerate((2, 4, 6)):
            if length <= 0:
                continue
            for r in range(6, 6 - h, -1):
                g.mx[r, col] = True
            tip = 6 - h
            if lit[i] and tip >= 0:
                g.mx[tip, col] = blink(t + i * 0.37, 0.8, 0.7)
                if smoke:
                    sy = tip - 1 - int((t * 2 + i * 0.6) % max(tip, 1))
                    if 0 <= sy < tip:
                        g.mx_set(col + (1 if int(t + i) % 2 else 0), sy)

    def mx_censer(self, g: Gfx):
        g.mx[7, 1:7] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self._plant(g, t, 0.0)
        self.texts(g, 0, a=span(t, 2.3, 4.0))

    def _plant(self, g: Gfx, t: float, e: float):
        """插香、点火（入场与续香共用）；t ∈ [0, 4.2]"""
        censer(g)
        lit = tuple(t > 2.6 + i * 0.3 for i in range(3))
        insert = span(t, 1.3, 1.7)
        if t < 1.7:  # 手握香落下、插进去
            p = ease_out(span(t, 0, 1.3))
            fy_end = RIM + 6 - FULL  # 香脚正好插到香灰面
            fx, fy = lerp(112, 64, p), lerp(-40, fy_end - 4, p) + 4 * ease_in_out(insert)
            sleeve_fist(g, fx, fy)
            if insert > 0:  # 插进香灰的瞬间扬起一点灰
                for j in range(6):
                    a = rand(j, 5) * math.pi
                    r = insert * 6
                    g.px(CX + math.cos(a) * r * 2 - 4, RIM - 1 - math.sin(a) * r)
            g.mx[7, 1:7] = True
            if insert >= 1:
                self.mx(g, FULL, (0, 0, 0), t)
            return
        self.sticks(g, FULL, lit, t, smoke=ease_out(span(t, 3.4, 4.2)))
        if t < 2.3:  # 手松开收回
            p = ease_in(span(t, 1.7, 2.3))
            sleeve_fist(g, lerp(64, 120, p), lerp(RIM + 6 - FULL, -30, p), sticks=False)
        elif t < 3.9:  # 火柴从左边来，依次点燃
            k = span(t, 2.3, 3.6)
            if k < 0.25:
                mx_, my_ = lerp(-10, STICK_X[0] - 2, ease_out(k / 0.25)), lerp(40, RIM - FULL - 2, ease_out(k / 0.25))
            else:
                j = min(2, int((k - 0.25) / 0.25))
                mx_, my_ = STICK_X[j] - 2, RIM - FULL - 2
            out = span(t, 3.6, 3.9)
            match(g, mx_ - out * 40, my_ + out * 20, t, lit=out < 0.5)
        self.mx(g, FULL, lit, t, smoke=t > 3.4)
        g.mx_level = 4 if any(abs(t - (2.6 + i * 0.3)) < 0.08 for i in range(3)) else 1

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, e)
            return
        length = self.length(e)
        censer(g)
        self.sticks(g, length, (1, 1, 1), t)
        self.ash(g, e, length)
        self.texts(g, e)
        self.mx(g, length, (1, 1, 1), t)

    def _renew(self, g: Gfx, k: float, e: float):
        """一炷烧完：吹走残香，再插三炷新香"""
        if k < 1.2:
            censer(g)
            p = ease_in(k / 1.2)
            for i, x in enumerate(STICK_X):  # 残香与灰被吹向右边
                xx = x + p * (60 + i * 15)
                g.d.line((xx, RIM - 1 - p * 6, xx + p * 3, RIM - STUB - p * 8), fill=1)
            for j in range(4):  # 风
                y = 20 + j * 7
                x0 = -30 + k / 1.2 * 170 - j * 10
                g.d.line((x0, y, x0 + 18, y), fill=1)
            self.texts(g, e - k - 1)
            self.mx_censer(g)
        else:
            self._plant(g, (k - 1.2) * 4.2 / (RENEW - 1.2), e)
            self.texts(g, e)

    def interrupt(self, g: Gfx, t: float, e: float):
        length = self.length(e)
        censer(g)
        T = self.T["interrupt"]
        lit = []
        for i in range(3):
            lit.append(t < 0.25 + i * 0.3)
        smoke = 1 - ease_out(span(t, 0.2, T))
        self.sticks(g, length, (1, 1, 1), t, smoke=smoke)
        # 已掐灭的香头盖掉
        for i, x in enumerate(STICK_X):
            if not lit[i]:
                top = RIM - length
                g.d.rectangle((x - 1, top - 1, x + 1, top), fill=0)
                g.d.line((x, top + 1, x, top - 1), fill=1)
        j = min(2, int(t / 0.3))
        if t < 1.1:  # 手指依次去掐
            x = STICK_X[j]
            y = RIM - length - 7 + (2 if (t % 0.3) > 0.12 else 0)
            g.blit(PINCH, x - 4, y)
        self.texts(g, e, right="暂熄")
        self.mx(g, length, tuple(lit), t, smoke=False)

    def resume(self, g: Gfx, t: float, e: float):
        length = self.length(e)
        censer(g)
        lit = tuple(t > 0.45 + i * 0.3 for i in range(3))
        self.sticks(g, length, lit, t, smoke=ease_out(span(t, 1.0, 1.8)))
        top = RIM - length
        if t < 1.5:
            k = span(t, 0, 1.3)
            if k < 0.3:
                mx_, my_ = lerp(-10, STICK_X[0] - 2, ease_out(k / 0.3)), lerp(40, top - 2, ease_out(k / 0.3))
            else:
                j = min(2, int((k - 0.3) / 0.23))
                mx_, my_ = STICK_X[j] - 2, top - 2
            out = span(t, 1.3, 1.5)
            match(g, mx_ - out * 40, my_ + out * 20, t, lit=out < 0.5)
        self.texts(g, e)
        self.mx(g, length, lit, t)

    def complete(self, g: Gfx, t: float, e: float):
        length = self.length(e)
        if t < 2.2:
            self.texts(g, e, a=1 - span(t, 1.2, 2.2))
        censer(g, glow=ease_out(span(t, 2.0, 3.0)) * (1 + 0.2 * math.sin(t * 6)) if t > 2.0 else 0)
        wind = span(t, 0, 1.0)
        if t < 2.0:
            fly = ease_in(span(t, 0.8, 2.0))
            for i, x in enumerate(STICK_X):  # 香被吹弯、吹走
                top = RIM - length
                bend = wind * 6
                xx = x + fly * (70 + i * 12)
                g.d.line((xx, RIM - 1 - fly * 10, xx + bend, top - fly * 14), fill=1)
                if t < 0.8:
                    smoke_wisp(g, x + bend, top - 3, (top - 3) * (1 - wind), t, self.seed * 7 + i, sway=3 + wind * 10)
            for j in range(5):
                y = 12 + j * 7
                x0 = -40 + wind * 180 - j * 12
                g.d.line((x0, y, x0 + 22, y), fill=1)
        if t > 2.2:
            from ..engine.fx import typewriter
            typewriter(g, CX, 10, "功德圆满", t - 2.2, cps=5, align="center")
            for j in range(8):  # 闪光
                if blink(t + j * 0.13, 0.5, 0.3):
                    a = rand(j, 9) * 2 * math.pi
                    r = 20 + rand(j, 10) * 20
                    g.px(CX + math.cos(a) * r * 1.3, 32 + math.sin(a) * r * 0.5)
        g.mx[7, 1:7] = True
        if t > 2.0:
            r = (t - 2.0) * 3
            for y in range(7):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, (y - 7) * 1.2) - r) < 0.7:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(4 * (1 - span(t, 2.0, 3.5)))
        else:
            self.mx(g, length * (1 - span(t, 0.8, 1.6)), (t < 0.5,) * 3, t, smoke=False)
