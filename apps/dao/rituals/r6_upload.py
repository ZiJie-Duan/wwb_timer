"""云端上表：供桌上一台笔记本，把疏文“上传”到云上的南天门（天庭服务器），进度条跟着计时走。

依据：斋醮中的“拜表/上表”——高功封表（封表），奏请司表仙官、功曹使者把表文送达天庭，
法师步罡、存神飞神上谒，“上达天听”。这里把送表的功曹换成了数据包，把封表换成了“压缩打包”。
入场：一张表文展开，折成信封，“封”字印盖下，信封飞进笔记本；Wi-Fi 波纹发出，一条上行链路连向云中天门，
      数据包（小信封）开始沿链路往上飞。
持续：进度条随计时从 0% 走到 100%（一轮 10 分钟），速率读数跳动，链路虚线流动，笔记本屏上小进度条同步。
      一轮满：天门闪光，“200 OK”，一个回执包沿链路落回笔记本，再封下一道表，“第几表”加一。
中断：链路中间断开，在途的数据包掉下去，标签变成“暂停”，断口画 ×。
恢复：“断点续传”，断口重新接上，数据包从断点继续飞。
圆满：进度条冲到 100%，天门大放光芒，打两个勾“已读”，“上达天听”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, \
    rand, span
from .r6_common import num as cn_num
from ..engine.fx import cloud, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r6_common import glow_rays, tiny

ENV = Sprite("""
  #######
  ##...##
  #.#.#.#
  #..#..#
  #######
""")
ENV_OK = Sprite("""
  #######
  #....##
  #...#.#
  ##.#..#
  #.#...#
  #######
""")
P0, P1, P2 = (35, 31), (44, -4), (88, 27)   # 上行链路（二次贝塞尔）
GATE_X = 100
RENEW = 5.0


def bez(s: float):
    u = 1 - s
    return (u * u * P0[0] + 2 * u * s * P1[0] + s * s * P2[0], u * u * P0[1] + 2 * u * s * P1[1] + s * s * P2[1])


PATH = [bez(i / 40) for i in range(41)]


def altar(g: Gfx):
    """供桌 + 笔记本"""
    d = g.d
    d.rectangle((0, 50, 46, 52), fill=1)
    d.rectangle((3, 53, 43, 63), outline=1)
    for x in range(6, 42, 3):  # 桌帏褶
        d.line((x, 55, x, 61), fill=1) if x % 2 else None
    d.ellipse((18, 54, 28, 62), fill=0, outline=1)   # 桌帏上的太极纹
    d.arc((21, 54, 25, 58), 270, 90, fill=1)
    d.arc((21, 58, 25, 62), 90, 270, fill=1)
    d.polygon([(8, 47), (38, 47), (41, 49), (5, 49)], fill=1)  # 笔记本底座
    d.rectangle((11, 31, 35, 46), outline=1, fill=0)          # 屏幕
    d.rectangle((12, 32, 34, 45), outline=0)


def screen(g: Gfx, p: float | None, icon: str = "表"):
    g.text(23, 33, icon, size=8, align="center")
    if p is not None:
        g.d.rectangle((14, 42, 32, 43), outline=1)
        g.d.line((15, 42, 15 + 16 * clamp(p), 42), fill=1)
        g.d.line((15, 43, 15 + 16 * clamp(p), 43), fill=1)


def wifi(g: Gfx, t: float, on: float = 1.0):
    for i in range(3):
        if on <= 0:
            return
        k = (t * 1.5 - i * 0.25) % 1.0
        if k < 0.6:
            r = 3 + i * 3
            g.d.arc((35 - r, 31 - r, 35 + r, 31 + r), 230, 310, fill=1)


CLOUD = [(GATE_X - 15, 23, 5), (GATE_X - 7, 20, 6), (GATE_X + 3, 19, 7), (GATE_X + 13, 22, 5), (GATE_X + 20, 24, 4)]


def cloud_puff(g: Gfx):
    """云团：几个圆叠起来只留外轮廓，底边平"""
    d = g.d
    for x, y, r in CLOUD:
        d.ellipse((x - r, y - r, x + r, y + r), fill=1)
    for x, y, r in CLOUD:
        d.ellipse((x - r + 1, y - r + 1, x + r - 1, y + r - 1), fill=0)
    d.rectangle((GATE_X - 20, 25, GATE_X + 24, 29), fill=0)
    d.line((GATE_X - 19, 26, GATE_X + 23, 26), fill=1)
    g.d.arc((GATE_X - 4, 21, GATE_X + 2, 25), 180, 360, fill=1)   # 云里一道卷纹


def gate(g: Gfx, glow: float = 0.0, t: float = 0.0):
    """云上的南天门"""
    d = g.d
    if glow > 0:
        glow_rays(g, GATE_X, 9, 14, 14 + 14 * glow, 16, t * 0.8, 0.7)
        d.rectangle((GATE_X - 13, 0, GATE_X + 13, 18), fill=0)
    d.line((GATE_X - 15, 1, GATE_X + 15, 1), fill=1)       # 檐
    d.line((GATE_X - 13, 2, GATE_X + 13, 2), fill=1)
    g.px(GATE_X - 16, 0)
    g.px(GATE_X + 16, 0)
    d.line((GATE_X - 12, 5, GATE_X + 12, 5), fill=1)       # 额枋
    d.rectangle((GATE_X - 11, 3, GATE_X - 10, 17), fill=1)  # 柱
    d.rectangle((GATE_X + 10, 3, GATE_X + 11, 17), fill=1)
    d.rectangle((GATE_X - 6, 6, GATE_X + 6, 14), fill=1)   # 匾
    g.text(GATE_X, 7, "天", size=8, fill=0, align="center")
    if glow > 0:  # 门洞里的光
        for y in range(15, 18):
            d.line((GATE_X - 8, y, GATE_X + 8, y), fill=1 if (y + int(t * 8)) % 2 else 0)
    cloud_puff(g)


def link(g: Gfx, t: float, upto: float = 1.0, gap: float = 0.0, flow: bool = True):
    """链路虚线：从笔记本到天门，upto 画到哪；gap 中间断开的比例"""
    off = int(t * 12) % 3 if flow else 0
    n = len(PATH)
    for i in range(n):
        s = i / (n - 1)
        if s > upto:
            break
        if gap > 0 and abs(s - 0.5) < gap / 2:
            continue
        if (i + off) % 3 == 0:
            continue
        g.px(*PATH[i])
    if gap > 0:
        for s in (0.5 - gap / 2, 0.5 + gap / 2):
            x, y = bez(s)
            g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)


@register
class Upload(Ritual):
    id = "r6.upload"
    name = "云端上表"
    desc = "供桌上的笔记本把疏文上传到云中南天门，进度条随计时走满，回执落下再上一表；断线可断点续传"
    T = {"enter": 4.4, "interrupt": 1.6, "resume": 2.0, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.base_kb = 20 + self.rng.randrange(80)

    # ------------------------------------------------------------ 零件

    def prog(self, e: float) -> float:
        return (e % self.CYCLE) / self.CYCLE

    def packets(self, g: Gfx, t: float, upto: float = 1.0, freeze_t: float | None = None, fall: float = 0.0):
        tt = freeze_t if freeze_t is not None else t
        for j in range(4):
            s = (tt * 0.22 + j / 4) % 1.0
            if s > upto or s < 0.04 or s > 0.93:
                continue
            x, y = bez(s)
            if fall > 0:
                if abs(s - 0.5) > 0.3:
                    continue
                y += fall * fall * 60
                x += fall * 6
            g.blit(ENV, x - 3, y - 2)

    def hud(self, g: Gfx, e: float, t: float, label: str = "上表", p: float | None = None, speed: bool = True):
        p = self.prog(e) if p is None else p
        g.text(52, 45, label, size=8)
        tiny(g, 52 + 18, 46, f"{int(p * 100):d}%")
        if speed:
            kb = self.base_kb * (0.6 + 0.8 * noise(t * 2, self.seed))
            tiny(g, 125, 46, f"{kb:.0f}KB/S", align="right")
        g.d.rectangle((52, 55, 125, 61), outline=1)
        w = int(70 * clamp(p))
        if w > 0:
            g.d.rectangle((54, 57, 54 + w - 1, 59), fill=1)

    def title(self, g: Gfx, e: float, a: float = 1.0, n: int | None = None):
        n = int(e // self.CYCLE) + 1 if n is None else n
        s = f"第{cn_num(n)}表"
        g.text(3, 3, s[:int(round(a * len(s)))])

    def mx(self, g: Gfx, p: float, t: float, arrow: bool = True):
        if arrow:
            off = int(t * 6) % 7
            shape = ["...#....", "..###...", ".#####..", "...#....", "...#...."]
            for r, row in enumerate(shape):
                y = (r - off) % 7
                for c, ch in enumerate(row):
                    if ch == "#":
                        g.mx_set(c, y)
        else:  # 信封图标
            g.mx_rows([0, 0xFF, 0xC3, 0xA5, 0x99, 0x81, 0xFF, 0])
        g.mx[7, :int(round(clamp(p) * 8))] = True

    # ------------------------------------------------------------ 阶段

    def scene(self, g: Gfx, t: float, e: float):
        altar(g)
        gate(g)
        p = self.prog(e)
        screen(g, p)
        wifi(g, t)
        link(g, t)
        self.packets(g, t)
        self.hud(g, e, t)
        self.title(g, e)
        self.mx(g, p, t)

    def enter(self, g: Gfx, t: float):
        altar(g)
        gate(g)
        # 0–1.0 表文展开；1.0–1.6 折成信封、盖“封”；1.8–2.8 信封飞进笔记本
        if t < 1.8:
            w = ease_out(span(t, 0.0, 1.0))
            fold = ease_in_out(span(t, 1.0, 1.4))
            cx, cy = 64, 30
            hw = lerp(4, 30, w) * (1 - fold) + 14 * fold
            hh = 18 * (1 - fold) + 10 * fold
            g.d.rectangle((cx - hw, cy - hh, cx + hw, cy + hh), fill=0, outline=1)
            if fold < 0.5:
                for i in range(int(hw * 2 / 5)):  # 竖行小字
                    x = cx + hw - 4 - i * 5
                    if x > cx - hw + 2:
                        for y in range(int(cy - hh + 4), int(cy + hh - 3), 2):
                            g.px(x, y)
            else:
                g.d.line((cx - hw, cy - hh, cx, cy, cx + hw, cy - hh), fill=1)
            st = span(t, 1.3, 1.6)
            if st > 0:
                s = 2 - ease_out_bounce(st)
                r = int(6 * s)
                g.d.rectangle((cx - r, cy - r + 2, cx + r, cy + r + 2), fill=1)
                if s < 1.2:
                    g.text(cx, cy - 4, "封", fill=0, align="center")
            g.mx[1:6, 1:7] = True
            g.mx[2:5, 2:6] = fold < 0.5
        else:
            fly = ease_in(span(t, 1.8, 2.6))
            if fly < 1:
                x, y = lerp(64, 23, fly), lerp(30, 38, fly)
                s = 1 - 0.7 * fly
                g.d.rectangle((x - 14 * s, y - 10 * s, x + 14 * s, y + 10 * s), fill=0, outline=1)
                g.d.line((x - 14 * s, y - 10 * s, x, y, x + 14 * s, y - 10 * s), fill=1)
            else:
                screen(g, 0 if t > 3.6 else None)
            on = span(t, 2.6, 3.6)
            if on > 0:
                wifi(g, t)
                link(g, t, upto=ease_out(on))
            if t > 3.6:
                self.packets(g, t, upto=span(t, 3.6, 4.4))
            a = span(t, 3.4, 4.2)
            if a > 0:
                self.hud(g, 0, t, p=0)
            self.title(g, 0, a=a)
            self.mx(g, 0, t, arrow=t > 2.6)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, e, t)
            return
        self.scene(g, t, e)

    def _renew(self, g: Gfx, k: float, e: float, t: float):
        n = int(e // self.CYCLE)
        altar(g)
        gate(g, glow=ease_out(span(k, 0, 0.5)) * (1 - span(k, 1.2, 1.8)), t=t)
        if k < 1.4:
            tiny(g, GATE_X, 29, "200 OK", align="center")
        link(g, t, flow=False)
        r = span(k, 0.8, 2.6)  # 回执包落下
        if 0 < r < 1:
            x, y = bez(1 - ease_in_out(r))
            g.blit(ENV_OK, x - 3, y - 3)
        if k < 2.6:
            screen(g, 1.0)
            self.hud(g, e, t, p=1.0, label="完成", speed=False)
            self.title(g, 0, n=n)
            self.mx(g, 1.0, t, arrow=False)
            g.mx[1:5, 2:6] = blink(k, 0.3, 0.5)
            g.mx_level = 4 if k < 0.5 else 1
        else:
            st = span(k, 2.6, 3.2)  # 屏上盖“封”
            screen(g, 0, icon="封" if st < 1 or blink(k, 0.3, 0.5) else "表")
            if k > 3.8:
                wifi(g, t)
                self.packets(g, t, upto=span(k, 3.8, 5.0))
            self.hud(g, e, t, p=0, speed=k > 3.8)
            self.title(g, 0, n=n + 1)
            self.mx(g, 0, t, arrow=k > 3.8)

    def interrupt(self, g: Gfx, t: float, e: float):
        altar(g)
        gate(g)
        p = self.prog(e)
        screen(g, p)
        gap = ease_out(span(t, 0.0, 0.5)) * 0.22
        link(g, t, gap=gap, flow=t < 0.3)
        self.packets(g, 0.0, freeze_t=0.0, fall=span(t, 0.15, 0.9))
        self.packets_static = True
        if t > 0.5:
            x, y = bez(0.5)
            s = ease_out_back(span(t, 0.5, 0.8))
            r = 3 * s
            g.d.line((x - r, y - r + 4, x + r, y + r + 4), fill=1)
            g.d.line((x - r, y + r + 4, x + r, y - r + 4), fill=1)
        self.hud(g, e, t, label="暂停" if t > 0.4 else "上表", speed=t < 0.4)
        self.title(g, e)
        self.mx(g, p, 0, arrow=False)
        if t > 0.5:
            g.mx_rows([0, 0b01000010, 0b00100100, 0b00011000, 0b00011000, 0b00100100, 0b01000010, 0])
            g.mx[7, :int(round(p * 8))] = True

    def resume(self, g: Gfx, t: float, e: float):
        altar(g)
        gate(g)
        p = self.prog(e)
        screen(g, p)
        gap = 0.22 * (1 - ease_in_out(span(t, 0.9, 1.5)))
        link(g, t, gap=gap, flow=t > 1.5)
        if t < 1.5:
            g.d.rectangle((50, 30, 127, 42), fill=0)
            typewriter(g, 88, 31, "断点续传", t, cps=6, align="center")
        if t > 1.5:
            wifi(g, t)
            self.packets(g, t, upto=span(t, 1.5, 2.0))
        self.hud(g, e, t, label="暂停" if t < 1.5 else "上表", speed=t > 1.5)
        self.title(g, e)
        self.mx(g, p, t, arrow=t > 1.5)
        if t < 1.5:
            g.mx[3, 1:7] = True
            g.mx[3, 3:5] = t > 1.0

    def complete(self, g: Gfx, t: float, e: float):
        p0 = self.prog(e)
        p = lerp(p0, 1.0, ease_in_out(span(t, 0.0, 1.0)))
        altar(g)
        glow = ease_out(span(t, 1.0, 1.8))
        gate(g, glow=glow * (1 + 0.15 * math.sin(t * 7)) if glow > 0 else 0, t=t)
        screen(g, p, icon="表" if t < 1.0 else "OK")
        link(g, t, flow=t < 1.2)
        if t < 1.2:
            self.packets(g, t * 4)
        if t < 2.2:
            self.hud(g, e, t, p=p, speed=t < 1.0, label="上表" if t < 1.0 else "完成")
            self.title(g, e, a=1 - span(t, 1.4, 2.2))
        if t > 1.6:  # 两个勾：已读
            for i in range(2):
                k = span(t, 1.6 + i * 0.25, 1.9 + i * 0.25)
                if k > 0:
                    x = 86 + i * 5
                    pts = [(x, 36), (x + 2, 38), (x + 6, 32)]
                    g.d.line(pts[:2] if k < 0.4 else pts, fill=1)
            if t > 2.1:
                g.text(125, 30, "已读", align="right")
        if t > 2.2:
            g.d.rectangle((48, 42, 127, 63), fill=0)
            typewriter(g, 86, 47, "上达天听", t - 2.4, cps=5, align="center")
        self.mx(g, p, t, arrow=t < 1.0)
        if t >= 1.0:
            r = (t - 1.0) * 4
            g.mx[:7, :] = False
            for y in range(7):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 0) - r) < 0.8:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(5 * (1 - span(t, 1.0, 2.5)))
