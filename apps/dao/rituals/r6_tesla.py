"""雷法除虫：特斯拉线圈作五雷正法，电弧噼啪，爬过来的 bug（程序里的“精怪”）一靠近就被雷劈成灰。

依据：雷法（五雷正法）是宋以后神霄、清微等派的核心法术，役使雷霆以驱邪；
《金光神咒》：“役使雷霆，鬼妖丧胆，精怪亡形。”这里把精怪换成了软件 bug。
入场：线圈通电，次级线圈从下往上一圈圈亮起，顶上的放电环出现，第一道电弧蹿出。
持续：顶环不停冒出细小电弧；bug（地上爬的、空中飞的）从右边过来，到了雷区就被一道长电弧劈中，炸成星点；
      右侧蓄能条随计时充满（一轮 10 分钟），上方计数“斩几只”。
      一轮满：蓄能爆满，五道巨雷同时劈下全屏一闪，蓄能清零，“第几雷”加一。
中断：断电，电弧缩回顶环，零星火花渐熄，bug 原地僵住，“断电”。
恢复：嗡的一声，顶环闪烁，电弧重新长出来。
圆满：蓄能冲满，万雷齐发劈中所有 bug，全屏闪白，线圈放光，“精怪亡形”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_out, ease_out_back, lerp, noise, rand, span
from .r6_common import num as cn_num
from ..engine.fx import lightning, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r6_common import ctext, cvtext, glow_rays, tiny

TX, TY = 40, 21          # 放电顶环中心
ZAP_X = 74               # 雷区边界
FLOOR = 61
BAR_X0, BAR_Y0, BAR_X1, BAR_Y1 = 119, 24, 125, 60
INTERVAL = 19.0
RENEW = 5.0

BUG = [Sprite("""
  .#..#.
  ..##..
  ######
  .####.
  #.##.#
"""), Sprite("""
  #....#
  .#..#.
  ..##..
  ######
  .####.
  .#..#.
""")]
FLY = [Sprite("""
  ##.##
  .###.
  ..#..
"""), Sprite("""
  .....
  #####
  ..#..
""")]
BUG = [b.scale(2) for b in BUG]
FLY = [b.scale(2) for b in FLY]
BOLT = ["...##...", "..##....", ".##.....", "#####...", "..##....", ".##.....", "##......", "#......."]


def coil(g: Gfx, lit: float = 1.0, glow: float = 0.0, t: float = 0.0):
    """特斯拉线圈：底座、次级线圈（绕线）、放电顶环"""
    d = g.d
    if glow > 0:
        glow_rays(g, TX, TY, 18, 18 + 12 * glow, 16, t * 0.7, 0.8)
    d.rectangle((26, 56, 54, 63), outline=1, fill=0)
    tiny(g, 30, 58, "HV")
    g.px(49, 59)
    g.px(51, 59)
    d.rectangle((35, 28, 45, 55), outline=1, fill=0)
    n = int(lit * 13)
    for i in range(13):
        y = 54 - i * 2
        if i < n:
            d.line((36, y, 44, y), fill=1)
    d.ellipse((TX - 16, TY - 5, TX + 16, TY + 6), outline=1, fill=0)
    d.ellipse((TX - 12, TY - 2, TX + 12, TY + 3), outline=1)
    d.line((TX, TY - 5, TX, TY - 8), fill=1)   # 尖端


@register
class Tesla(Ritual):
    id = "r6.tesla"
    name = "雷法除虫"
    desc = "特斯拉线圈作五雷正法，电弧噼啪，爬近的 bug 一只只被雷劈碎；蓄能满时五雷齐落"
    T = {"enter": 3.6, "interrupt": 1.5, "resume": 1.8, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.s = self.rng.randrange(10000)

    # ------------------------------------------------------------ bug 调度（e 的函数）

    def bug(self, i: int):
        """第 i 只 bug：(出生 e, 速度, 是否会飞, 劈中 e)"""
        born = i * INTERVAL + rand(i, self.s) * 8
        fly = rand(i, self.s + 1) > 0.62
        v = 2.2 + rand(i, self.s + 2) * 1.6 + (1.5 if fly else 0)
        zap = born + (132 - ZAP_X) / v
        return born, v, fly, zap

    def bug_pos(self, i: int, e: float):
        born, v, fly, zap = self.bug(i)
        x = 132 - (e - born) * v
        if fly:
            y = 34 + 8 * math.sin((e - born) * 1.3 + i)
        else:
            y = FLOOR - 11
        return x, y

    def bugs(self, g: Gfx, e: float, t: float, frozen: bool = False, kill_all: float | None = None):
        """画在场的 bug、劈中的电弧与碎屑；返回本帧是否有雷劈下"""
        zapping = False
        i0 = max(0, int((e - 45) / INTERVAL))
        for i in range(i0, int(e / INTERVAL) + 2):
            born, v, fly, zap = self.bug(i)
            if e < born:
                continue
            if kill_all is not None and e < zap and e >= kill_all:
                zap = kill_all  # 圆满：全部劈中
            if e < zap:
                x, y = self.bug_pos(i, e)
                if x > 128:
                    continue
                fr = 0 if frozen else int(t * (8 if fly else 5)) % 2
                g.blit((FLY if fly else BUG)[fr], x, y)
                continue
            k = e - zap
            if k > 1.2:
                continue
            x, y = self.bug_pos(i, zap)
            if k < 0.25:  # 劈下的电弧
                lightning(g, TX + 14, TY, x + 6, y + 4, seed=i * 31 + int(t * 20), jag=5, branches=1)
                zapping = True
            for j in range(8):  # 碎屑
                a = j / 8 * 2 * math.pi + i
                r = 2 + k * 14
                if rand(j + int(k * 10), i) > k * 0.8:
                    px, py = x + 6 + math.cos(a) * r, y + 4 + math.sin(a) * r * 0.7 + k * k * 8
                    g.d.rectangle((px, py, px + 1, py + 1), fill=1)
        return zapping

    def kills(self, e: float) -> int:
        """本轮已劈中的 bug 数"""
        c0 = e - (e % self.CYCLE)
        n = 0
        for i in range(max(0, int((c0 - 45) / INTERVAL)), int(e / INTERVAL) + 2):
            z = self.bug(i)[3]
            if c0 <= z <= e:
                n += 1
        return n

    # ------------------------------------------------------------ 零件

    def arcs(self, g: Gfx, t: float, amt: float = 1.0, reach: float = 1.0):
        """顶环四周冒出的细电弧（随时间闪烁）"""
        if amt <= 0:
            return
        f = int(t * 14)
        n = 2 + int(2.5 * amt * noise(t * 3, self.s))
        for j in range(n):
            a = -math.pi - 0.35 + (math.pi + 0.7) * rand(f * 5 + j, self.s)
            sx, sy = TX + math.cos(a) * 16, TY + math.sin(a) * 5
            r = (6 + 16 * rand(f * 3 + j, self.s + 1)) * reach
            ex, ey = sx + math.cos(a) * r, sy + math.sin(a) * r * 0.8
            lightning(g, sx, sy, ex, ey, seed=f * 13 + j, jag=3, branches=1 if r > 15 else 0)

    def bar(self, g: Gfx, p: float, t: float):
        g.d.rectangle((BAR_X0 - 3, BAR_Y0 - 8, 127, 63), fill=0)
        g.d.rectangle((BAR_X0, BAR_Y0, BAR_X1, BAR_Y1), outline=1)
        h = int((BAR_Y1 - BAR_Y0 - 3) * clamp(p))
        if h > 0:
            g.d.rectangle((BAR_X0 + 2, BAR_Y1 - 1 - h, BAR_X1 - 2, BAR_Y1 - 2), fill=1)
        tiny(g, BAR_X0 - 1, BAR_Y0 - 7, "KV")

    def hud(self, g: Gfx, e: float, right: str | None = None, kills: int | None = None):
        n = int(e // self.CYCLE) + 1
        s = right if right is not None else f"第{cn_num(n)}雷"
        ctext(g, 126, 1, s, align="right")
        k = self.kills(e) if kills is None else kills
        tiny(g, 112, 18, f"BUG-{k:02d}", align="right")
        cvtext(g, 3, 4, "五雷正法")

    def mx(self, g: Gfx, p: float, t: float, zap: bool = False, flicker: bool = True):
        for r, row in enumerate(BOLT):
            for c, ch in enumerate(row):
                if ch == "#" and (not flicker or noise(t * 6 + r, 3) > 0.25):
                    g.mx[r, c] = True
        h = int(round(clamp(p) * 8))
        g.mx[8 - h:, 7] = True
        if zap:
            g.mx_level = 5

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        coil(g, lit=span(t, 0.3, 1.8))
        if t > 1.8:
            self.arcs(g, t, amt=span(t, 1.8, 3.0), reach=ease_out_back(span(t, 1.8, 2.6)))
        if 1.8 < t < 2.1:
            lightning(g, TX + 15, TY, 100, FLOOR, seed=7, jag=6)
            g.mx_level = 5
        a = span(t, 2.2, 3.4)
        if a > 0:
            n = 1
            ctext(g, 126, 1, f"第{cn_num(n)}雷"[:int(round(a * 3))], align="right")
            cvtext(g, 3, 4, "五雷正法"[:int(round(a * 4))])
            self.bar(g, 0, t)
            tiny(g, 112, 18, "BUG-00", align="right")
        self.mx(g, 0, t, flicker=t > 1.8)
        if t < 1.8:
            g.mx[:, :] = False
            g.mx[8 - int(span(t, 0.3, 1.8) * 8):, 3] = True

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, e, t)
            return
        p = k / self.CYCLE
        coil(g)
        self.arcs(g, t, amt=0.6 + 0.6 * p)
        zap = self.bugs(g, e, t)
        self.bar(g, p, t)
        self.hud(g, e)
        self.mx(g, p, t, zap)

    def _big(self, g: Gfx, k: float, seed: int, n: int = 5):
        """五道巨雷"""
        for j in range(n):
            x = 64 + j * 14 + rand(j, seed) * 6
            lightning(g, TX + 14, TY - 2, x, FLOOR, seed=seed * 7 + j + int(k * 12), jag=7, branches=2, width=1)

    def _renew(self, g: Gfx, k: float, e: float, t: float):
        coil(g, glow=1 - span(k, 0.3, 1.5), t=t)
        if k < 0.9:
            self._big(g, k, int(e // self.CYCLE))
        self.bugs(g, e, t, kill_all=e - k)
        self.arcs(g, t, amt=span(k, 1.5, 4.0))
        self.bar(g, 1 - ease_in(span(k, 0.5, 3.0)), t)
        if k < 0.9:
            self.hud(g, e - k - 1)
        else:
            self.hud(g, e, kills=0 if k > 3.0 else None)
        if 0.1 < k < 0.22:
            g.invert()
        self.mx(g, 1 - span(k, 0.5, 3.0), t, zap=k < 0.9)
        if k < 0.9:
            g.mx[:, :] = blink(k, 0.12, 0.5)

    def interrupt(self, g: Gfx, t: float, e: float):
        p = (e % self.CYCLE) / self.CYCLE
        coil(g, lit=1 - span(t, 0.0, 0.8))
        self.arcs(g, t, amt=1 - span(t, 0.0, 0.6), reach=1 - ease_in(span(t, 0.0, 0.6)))
        if 0.6 < t < 1.3:  # 零星火花
            for j in range(3):
                if rand(int(t * 15) + j, self.s) > 0.5 + span(t, 0.6, 1.3) * 0.5:
                    a = rand(j + int(t * 15), 2) * math.pi * 2
                    g.px(TX + math.cos(a) * 16, TY + math.sin(a) * 5)
        self.bugs(g, e, t, frozen=True)
        self.bar(g, p, t)
        self.hud(g, e, right="断电" if t > 0.3 else None)
        self.mx(g, p, t, flicker=False)
        g.mx[:7, :7] &= t < 0.6

    def resume(self, g: Gfx, t: float, e: float):
        p = (e % self.CYCLE) / self.CYCLE
        coil(g, lit=span(t, 0.0, 0.8))
        if t < 0.8 and blink(t, 0.16, 0.5):  # 顶环闪烁
            g.d.ellipse((TX - 14, TY - 3, TX + 14, TY + 4), outline=1)
        self.arcs(g, t, amt=span(t, 0.6, 1.6), reach=ease_out_back(span(t, 0.6, 1.4)))
        self.bugs(g, e, t, frozen=t < 1.0)
        self.bar(g, p, t)
        self.hud(g, e, right="通电" if t < 1.2 else None)
        self.mx(g, p, t, flicker=t > 0.8)
        if t < 0.8:
            g.mx[:7, :7] = False

    def complete(self, g: Gfx, t: float, e: float):
        p0 = (e % self.CYCLE) / self.CYCLE
        p = lerp(p0, 1.0, ease_in(span(t, 0.0, 1.0)))
        coil(g, glow=ease_out(span(t, 1.0, 1.6)) * (1 + 0.15 * math.sin(t * 7)) if t > 1.0 else 0, t=t)
        if t < 1.0:
            self.arcs(g, t, amt=1 + p, reach=0.8 + 0.6 * p)
        self.bugs(g, e, t, kill_all=e if t >= 1.0 else None) if t < 1.0 else self.bugs(g, e + (t - 1.0), t,
                                                                                       kill_all=e)
        if 1.0 <= t < 1.8:
            self._big(g, t, 99, n=6)
        if 1.0 < t < 1.12:
            g.invert()
        self.bar(g, p, t)
        if t < 2.2:
            self.hud(g, e)
        if t > 2.0:
            g.d.rectangle((60, 30, 116, 50), fill=0)
            typewriter(g, 88, 34, "精怪亡形", t - 2.2, cps=5, align="center")
            cvtext(g, 3, 4, "五雷正法")
        self.mx(g, p, t, zap=1.0 <= t < 1.8)
        if 1.0 <= t < 1.8:
            g.mx[:, :] = blink(t, 0.1, 0.5)
        g.mx_level = 6 if 1.0 <= t < 1.8 else 1 + int(3 * (1 - span(t, 1.8, 3.5)))
