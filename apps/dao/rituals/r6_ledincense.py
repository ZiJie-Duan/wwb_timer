"""赛博烧香：USB 供电的电子香炉，三根 LED 香随计时一格格熄灭，香头冒出“数字烟”（像素块与 0/1）。

入场：USB 线从右边插进炉身，火花一闪，炉上小屏开机，LED 香自下而上逐格点亮，香头依次亮起，数字烟升起。
持续：LED 香随计时一格格变短（一轮 10 分钟），炉屏显示剩余电量；偶尔信号毛刺（画面错位一下）。
      一炷烧完：炉屏 0% 闪“LOW”，然后充电重新开机，再点三炷。右侧“第几炷”加一。
中断：一根手指按下炉身电源键，LED 自上而下熄灭成空心，烟散，炉屏“ZZZ”，右侧“待机”。
恢复：再按电源键，LED 逐格亮回原来的长度，烟再起。
圆满：LED 跑马灯“超频”，三炷香头喷出一大股 0/1 升天，炉身放光，“心存帝前”。
文字取自道教《祝香咒》：“道由心学，心假香传。香焚玉炉，心存帝前。”
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from .r6_common import num as cn_num, vlabel
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r6_common import bitsmoke, glow_rays, tiny

CX = 64
RIM = 44
STICK_X = (55, 63, 71)   # LED 香左边 x（宽 3）
SEG = 3                  # 每格 2 亮 1 暗
NSEG = 9                 # 满长格数
FULL = NSEG * SEG
RENEW = 5.0
PLUG_X = 87              # 插头插好的位置（炉身右侧）
PLUG_Y = 50

PLUG = Sprite("""
  ..#######
  ##########
  #.#########
  ##########
  ..#######
""")
FINGER = Sprite("""
  #...#
  #...#
  #...#
  #...#
  #...#
  #...#
  ##..##
  #....#
  #....#
  #....#
  .#..#.
  ..##..
""")
BTN_X = 84               # 右耳 = 电源键


def censer(g: Gfx, glow: float = 0.0):
    """电子香炉：鼎形炉身 + 小屏 + 电路走线"""
    d = g.d
    d.rectangle((42, RIM - 6, 45, RIM), outline=1)
    d.rectangle((83, RIM - 6, 86, RIM), outline=1)
    d.line((40, RIM, 88, RIM), fill=1)
    d.polygon([(42, RIM + 1), (86, RIM + 1), (80, 57), (48, 57)], outline=1, fill=0)
    d.rectangle((54, 47, 74, 55), outline=1)                 # 小屏
    for x0, sgn in ((52, -1), (76, 1)):                      # 走线 + 过孔
        d.line((x0, 49, x0 + sgn * 4, 49, x0 + sgn * 6, 51), fill=1)
        d.line((x0, 53, x0 + sgn * 2, 53, x0 + sgn * 4, 55), fill=1)
        g.px(x0 + sgn * 6, 52)
    d.rectangle((84, RIM - 4, 85, RIM - 2), fill=1)          # 右耳里的电源键
    for x in (52, 64, 76):
        d.rectangle((x - 1, 58, x, 62), fill=1)
    if glow > 0:
        glow_rays(g, CX, 50, 28, 28 + 10 * glow, 14, glow * 1.5, 0.6)


def cable(g: Gfx, px: float, py: float):
    """USB 线：插头 (px, py) 往右，再弯下去出画面"""
    x0 = px + 10
    g.d.line((x0, py + 2, x0 + 10, py + 2), fill=1)
    g.d.arc((x0 + 2, py + 2, x0 + 18, py + 30), 270, 360, fill=1)
    g.d.line((x0 + 18, py + 16, x0 + 18, 64), fill=1)
    g.blit(PLUG, px, py)


@register
class LedIncense(Ritual):
    id = "r6.ledincense"
    name = "赛博烧香"
    desc = "USB 电子香炉插电开机，三根 LED 香一格格燃短，香头冒出 0/1 数字烟，没电了充电再续"
    T = {"enter": 4.4, "interrupt": 1.6, "resume": 1.8, "complete": 4.8}
    CYCLE = 600.0

    def setup(self):
        self.glitch_seed = self.rng.randrange(1000)

    # ------------------------------------------------------------ 零件

    def segs(self, e: float) -> float:
        """剩余格数（带小数：最上一格渐暗）"""
        p = (e % self.CYCLE) / self.CYCLE
        return lerp(NSEG, 1, p)

    def sticks(self, g: Gfx, segs: float, t: float, lit=(1, 1, 1), on: float = 1.0, smoke: float = 1.0,
               glitch: float = 0.0):
        """segs：剩余格数；on：亮起比例（0..1 自下而上，中断/恢复用；暗的格子画成空心）"""
        n = int(math.ceil(segs - 1e-6))
        frac = segs - (n - 1)
        for i, x in enumerate(STICK_X):
            gx = x + (2 if glitch and i == 1 else 0)
            for s in range(n):
                y1 = RIM - 1 - s * SEG
                y0 = y1 - 1
                lit_seg = s < on * n
                if s == n - 1 and lit_seg and frac < 1 and noise(t * 4 + i, self.seed) > frac + 0.2:
                    lit_seg = False  # 最上一格快灭时闪
                if lit_seg:
                    g.d.rectangle((gx, y0, gx + 2, y1), fill=1)
                else:
                    g.d.rectangle((gx, y0, gx + 2, y1), outline=1)
                    g.px(gx + 1, y0, 0)
            top = RIM - 1 - n * SEG
            if lit[i] and n > 0 and on >= 1:
                b = noise(t * 3 + i * 7, self.seed + i) > 0.3
                g.d.rectangle((gx, top - 1, gx + 2, top + 1), fill=1)   # LED 香头
                if b:
                    for dx, dy in ((-2, -2), (4, -2), (-2, 2), (4, 2), (1, -3)):
                        g.px(gx + dx, top + dy)
                if smoke > 0:
                    bitsmoke(g, gx + 1, top - 3, (top - 3) * 0.92, t, self.seed * 5 + i, n=3, speed=7 + i,
                             sway=5.0 + i * 1.5, drift=(i - 1) * 12, amount=smoke)

    def screen(self, g: Gfx, s: str, inv: bool = False):
        if inv:
            g.d.rectangle((55, 48, 73, 54), fill=1)
        tiny(g, 64, 49, s, fill=0 if inv else 1, align="center")

    def battery(self, e: float) -> str:
        p = (e % self.CYCLE) / self.CYCLE
        return f"{int(round(100 * (1 - p)))}%"

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        left = "心假香传"
        k = int(round(a * len(left)))
        g.vtext(3, 4, left[:k])
        n = int(e // self.CYCLE) + 1
        r = right if right is not None else vlabel(n, "炷")
        g.vtext(113, 4, r[:max(0, int(round(a * len(r))))])

    def mx(self, g: Gfx, segs: float, t: float, lit=(1, 1, 1), on: float = 1.0, smoke: bool = True):
        g.mx[7, :] = True
        h = max(1, int(round(segs / NSEG * 5)))
        for i, col in enumerate((1, 3, 5)):
            for r in range(6, 6 - h, -1):
                if (6 - r) < on * h:
                    g.mx[r, col] = g.mx[r, col + 1] = True
            tip = 6 - h
            if lit[i] and on >= 1 and tip >= 0:
                g.mx[tip, col] = g.mx[tip, col + 1] = blink(t + i * 0.37, 0.9, 0.75)
                if smoke and tip > 0:
                    sy = tip - 1 - int((t * 3 + i * 0.7) % max(tip, 1))
                    g.mx_set(col + int(t * 2 + i) % 2, sy)

    # ------------------------------------------------------------ 开机（入场与续香共用）

    def _boot(self, g: Gfx, t: float, e: float, plugged: bool = False):
        """t ∈ [0, 4.4]：0.2–1.3 插线，1.3 火花，1.5–3.0 逐格点亮，3.0–3.6 香头，3.6– 烟"""
        censer(g)
        if plugged or t >= 1.3:
            cable(g, PLUG_X, PLUG_Y - 2)
        else:
            p = ease_out(span(t, 0.2, 1.3))
            cable(g, lerp(140, PLUG_X, p), PLUG_Y - 2)
        if 1.3 <= t < 1.6 and not plugged:  # 火花
            k = span(t, 1.3, 1.6)
            for j in range(6):
                a = j / 6 * 2 * math.pi + 0.3
                r0, r1 = 2 + k * 4, 4 + k * 7
                g.d.line((PLUG_X + math.cos(a) * r0, PLUG_Y + math.sin(a) * r0, PLUG_X + math.cos(a) * r1,
                          PLUG_Y + math.sin(a) * r1), fill=1)
        g.mx[7, :] = True
        if t < 1.3:
            return
        fill = span(t, 1.5, 3.0)
        lit = tuple(t > 3.0 + i * 0.2 for i in range(3))
        if t < 1.5:
            self.screen(g, "", inv=True)
        elif fill < 1:
            self.screen(g, "BOOT" if blink(t, 0.4, 0.7) else "")
        else:
            self.screen(g, "100%")
        segs = NSEG * fill
        if segs > 0:
            self.sticks(g, max(segs, 0.01), t, lit, smoke=ease_out(span(t, 3.6, 4.4)))
        self.mx(g, max(segs, 0.01), t, lit, smoke=t > 3.6)
        g.mx_level = 4 if (1.3 <= t < 1.5) or any(abs(t - (3.0 + i * 0.2)) < 0.07 for i in range(3)) else 1

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self._boot(g, t, 0.0)
        self.texts(g, 0, a=span(t, 2.6, 4.2))

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, e)
            return
        segs = self.segs(e)
        censer(g)
        cable(g, PLUG_X, PLUG_Y - 2)
        gk = (e + self.glitch_seed) % 23.0
        glitch = gk < 0.18
        self.sticks(g, segs, t, glitch=glitch)
        if glitch:  # 信号毛刺：一条扫描线错位
            y = 10 + int(rand(int(e / 23), self.seed) * 30)
            g.d.line((40, y, 88, y), fill=1)
            g.d.line((48, y + 2, 70, y + 2), fill=0)
        bat = self.battery(e)
        low = segs < 1.8
        self.screen(g, bat if not low or blink(t, 0.6, 0.6) else "LOW")
        self.texts(g, e)
        self.mx(g, segs, t)

    def _renew(self, g: Gfx, k: float, e: float):
        """一炷耗尽：0% 闪 LOW，充电重开机"""
        if k < 1.2:
            censer(g)
            cable(g, PLUG_X, PLUG_Y - 2)
            self.sticks(g, 1.0, k, lit=(0, 0, 0), on=0.0)
            self.screen(g, "0%" if blink(k, 0.4, 0.5) else "LOW", inv=k > 0.8)
            self.texts(g, e - k - 1)
            g.mx[7, :] = True
            if blink(k, 0.4, 0.5):
                g.mx[6, 1:3] = g.mx[6, 3:5] = g.mx[6, 5:7] = True
            return
        self._boot(g, 1.3 + (k - 1.2) * (4.4 - 1.3) / (RENEW - 1.2), e, plugged=True)
        self.texts(g, e)

    def interrupt(self, g: Gfx, t: float, e: float):
        segs = self.segs(e)
        censer(g)
        cable(g, PLUG_X, PLUG_Y - 2)
        press = span(t, 0.0, 0.45)
        if t < 1.2:
            fy = lerp(-14, RIM - 18, ease_out(press)) + (1 if 0.45 < t < 0.6 else 0)
        else:
            fy = lerp(RIM - 18, -14, ease_in(span(t, 1.2, 1.6)))
        g.blit(FINGER, BTN_X - 2, fy)
        off = span(t, 0.5, 1.1)
        on = 1 - off
        lit = (on >= 1,) * 3
        self.sticks(g, segs, t, lit=lit, on=on, smoke=1 - ease_out(span(t, 0.3, 1.2)))
        self.screen(g, self.battery(e) if t < 0.9 else ("ZZZ"[:1 + int(t * 4) % 3]))
        self.texts(g, e, right="待机")
        self.mx(g, segs, t, lit, on=on, smoke=False)
        if t > 1.1:
            g.mx[7, :] = False
            g.mx[7, 7] = blink(t, 0.8, 0.3)
            g.mx[7, :7] = True

    def resume(self, g: Gfx, t: float, e: float):
        segs = self.segs(e)
        censer(g)
        cable(g, PLUG_X, PLUG_Y - 2)
        if t < 0.7:
            p = ease_out(span(t, 0.0, 0.35))
            g.blit(FINGER, BTN_X - 2, lerp(-14, RIM - 18, p) + (1 if 0.35 < t < 0.5 else 0))
        elif t < 1.1:
            g.blit(FINGER, BTN_X - 2, lerp(RIM - 18, -14, ease_in(span(t, 0.7, 1.1))))
        on = span(t, 0.45, 1.1)
        lit = tuple(t > 1.1 + i * 0.12 for i in range(3))
        self.sticks(g, segs, t, lit=lit, on=on, smoke=ease_out(span(t, 1.2, 1.8)))
        self.screen(g, "ON" if t < 1.1 else self.battery(e))
        self.texts(g, e)
        self.mx(g, segs, t, lit, on=on, smoke=t > 1.2)
        g.mx_level = 4 if any(abs(t - (1.1 + i * 0.12)) < 0.05 for i in range(3)) else 1

    def complete(self, g: Gfx, t: float, e: float):
        segs0 = self.segs(e)
        glow = ease_out(span(t, 2.2, 3.2)) * (1 + 0.2 * math.sin(t * 6)) if t > 2.2 else 0
        censer(g, glow=glow)
        cable(g, PLUG_X, PLUG_Y - 2)
        # 0–1.2 充满到满格（超频），1.2–2.2 跑马灯 + 喷发，之后香消失化光
        segs = lerp(segs0, NSEG, ease_in_out(span(t, 0.0, 1.0)))
        if t < 2.2:
            n = int(math.ceil(segs))
            self.sticks(g, segs, t, smoke=1.0 if t < 1.2 else 0.0)
            band = (t * 30) % (n + 3)
            for x in STICK_X:  # 跑马灯：一段暗带往上跑
                for s in range(n):
                    if abs(s - band) < 1:
                        y1 = RIM - 1 - s * SEG
                        g.d.rectangle((x, y1 - 1, x + 2, y1), fill=0)
        if 1.2 <= t < 3.4:  # 0/1 像烟花一样从三个香头喷开
            k = t - 1.2
            for j in range(30):
                i = j % 3
                st = rand(j, self.seed + 40) * 0.8
                if k < st:
                    continue
                kk = k - st
                a = -math.pi / 2 + (rand(j, self.seed + 41) - 0.5) * 2.6
                v = 38 + 30 * rand(j, self.seed + 42)
                d = v * kk * (1 - 0.3 * kk)
                x = STICK_X[i] + math.cos(a) * d
                y = RIM - FULL - 4 + math.sin(a) * d * 0.8 + 14 * kk * kk
                if kk > 1.3 or (kk > 0.8 and rand(int(t * 20) + j, 9) < (kk - 0.8) * 2):
                    continue
                tiny(g, x, y, "1" if rand(j, self.seed + 43) > 0.5 else "0")
        if t < 2.2:
            self.screen(g, "MAX" if blink(t, 0.3, 0.6) else "100%")
        else:
            self.screen(g, "OK", inv=True)
        if t < 2.0:
            self.texts(g, e, a=1 - span(t, 1.0, 2.0))
        if t > 2.4:
            typewriter(g, CX, 6, "心存帝前", t - 2.4, cps=5, align="center")
        g.mx[7, :] = True
        if t < 1.2:
            self.mx(g, segs, t)
        else:  # 点阵：0/1 往上冲
            for c in range(8):
                for r in range(7):
                    if rand(c * 13 + int((t * 12 - r * 0.0) + c * 3 + r) // 3, 77) > 0.55 and \
                            ((r + int(t * 12)) % 3 == c % 3):
                        g.mx[r, c] = True
            g.mx_level = 1 + int(5 * (1 - span(t, 1.2, 3.0)))
