"""云端上表（像素风）：小道士在露天供桌前敲笔记本，把表文“上传”给云中的南天门。

依据：斋醮中的“拜表/上表”——高功封表，奏请司表仙官、功曹使者把表文送达天庭，“上达天听”。
这里送表的功曹换成数据包（小信封），封表换成打包，断线可以“断点续传”。

入场：小道士举起一卷竖行表文，表文唰地展开，再卷起折成信封；信封飞到半空放大，“封”字大印盖下（一震）；
      信封缩小飞进笔记本屏幕，路由器天线发出 Wi-Fi 波纹，一条虚线上行链路从天线连到南天门，小信封开始往上飞。
持续：小道士一直敲键盘；进度条一轮 10 分钟走满，速率读数跳动，小信封沿链路飞进天门。
      隔一阵作个揖、跪下拜一拜；每隔一分钟左右信号掉线：信号格掉光、包停在半路闪，小道士掏出手机举过头顶晃着找信号，
      信号回来时火花一闪，包继续飞。
      一轮满：天门放光、门楣上 “200 OK”，一个打勾的回执包沿链路落回笔记本，小道士再递一封新表进去，“第几表”加一。
中断：链路中间断开，断口打 ×，在途的包掉下去，屏上 ||，“暂停”。
恢复：“断点续传”，断口接上（火花），包从断点接着飞。
圆满：进度冲到 100%，天门两扇门打开放光，闪白，两个勾“已读”，小道士跪拜，“上达天听”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx
from ..engine.scene import register
from .r6_common import R6, badge, banner, dao, glow_rays, nth, tiny

FLOOR = 58
DX = 28                       # 小道士
TABLE = (36, 94, 47)          # 供桌 x0, x1, 桌面 y
LAP = (39, 26)                # 笔记本精灵左上角
SCR = (44, 27, 66, 41)        # 屏幕显示区
ROUTER = (74, 34)
GATE = (96, 1)
P0, P1, P2 = (81.0, 31.0), (82.0, 0.0), (106.0, 15.0)   # 上行链路（二次贝塞尔）
RENEW = 6.0
LOOP = 30.0
STALL = (24.0, 27.6)          # 掉线（奇数轮）


def path(u: float):
    u = clamp(u)
    a = (1 - u) * (1 - u)
    b = 2 * u * (1 - u)
    c = u * u
    return a * P0[0] + b * P1[0] + c * P2[0], a * P0[1] + b * P1[1] + c * P2[1]


# ---------------------------------------------------------------- 道具

def _laptop():
    """笔记本 33×21：屏幕框（顶上摄像头）、铰链、键盘面（两排键）、触控板"""
    p = Part(33, 21)
    p.shape("rectangle", (4, 0, 28, 16), fill=1)
    p.d.rectangle((5, 1, 27, 15), fill=0)
    p.px(16, 0, 0)
    p.shape("polygon", [(2, 17), (30, 17), (32, 20), (0, 20)], fill=1)
    for x in range(4, 29, 2):
        p.px(x, 18, 0)
    for x in range(3, 30, 2):
        p.px(x, 19, 0) if not 13 <= x <= 19 else None
    p.d.line((14, 19, 18, 19), fill=0)
    p.dither([(26, 18), (32, 18), (32, 20), (26, 20)], 0.5, 0)
    return p.sprite()


def _router():
    """路由器 15×13：两根天线（顶上小球）、圆角机身、前面板阴线、背光网点"""
    p = Part(15, 13)
    for x in (2, 12):
        p.shape("rectangle", (x, 1, x, 6), fill=1)
        p.shape("rectangle", (x - 1, 0, x + 1, 1), fill=1)
    p.shape("rectangle", (0, 6, 14, 12), fill=1)
    p.px(0, 6, 0), p.px(14, 6, 0), p.px(0, 12, 0), p.px(14, 12, 0)
    p.d.line((1, 9, 13, 9), fill=0)
    p.d.rectangle((2, 7, 5, 7), fill=0)
    p.dither([(10, 10), (14, 10), (14, 12), (10, 12)], 0.5, 0)
    return p.sprite()


def _gate():
    """南天门 30×22：屋脊（两端鸱吻）、瓦垄、飞檐起翘、门楣匾、双柱、两扇钉门、台基"""
    p = Part(30, 22)
    p.shape("rectangle", (5, 1, 24, 3), fill=1)
    p.px(4, 0), p.px(5, 0), p.px(24, 0), p.px(25, 0)
    for x in range(7, 23, 3):
        p.d.line((x, 2, x, 3), fill=0)
    p.shape("polygon", [(0, 3), (29, 3), (27, 6), (2, 6)], fill=1)
    p.d.line((2, 5, 27, 5), fill=0)
    p.shape("rectangle", (2, 7, 27, 8), fill=1)
    p.d.line((3, 8, 26, 8), fill=0)
    p.shape("rectangle", (10, 6, 19, 11), fill=1)
    p.d.rectangle((11, 7, 18, 10), fill=0)
    p.px(13, 8), p.px(13, 9), p.px(16, 8), p.px(16, 9)
    for x in (3, 24):
        p.shape("rectangle", (x, 9, x + 2, 20), fill=1)
        p.px(x + 2, 11, 0), p.px(x + 2, 13, 0), p.px(x + 2, 15, 0), p.px(x + 2, 17, 0)
    p.shape("rectangle", (7, 12, 22, 20), fill=1)
    p.d.line((14, 12, 14, 20), fill=0)
    p.d.line((15, 12, 15, 20), fill=0)
    for y in (14, 17):
        for x in (9, 11, 18, 20):
            p.px(x, y, 0)
    p.px(13, 16, 0), p.px(16, 16, 0)
    p.shape("rectangle", (1, 20, 28, 21), fill=1)
    p.d.line((2, 21, 27, 21), fill=0)
    return p.sprite()


def _cloud(w=40, h=10, seed=1):
    """祥云：几团叠起的圆，里面卷云纹（阴线），底部网点"""
    p = Part(w, h)
    k = 0
    x = 1
    while x < w - 6:
        r = 3 + int(rand(k, seed) * 2)
        p.shape("ellipse", (x, h - 2 * r - 2, x + 2 * r + 1, h - 2), fill=1)
        x += r + 2
        k += 1
    p.shape("rectangle", (2, h - 4, w - 3, h - 2), fill=1)
    x = 4
    k = 0
    while x < w - 8:
        p.d.arc((x, h - 7, x + 5, h - 2), 180, 360 if k % 2 else 300, fill=0)
        x += 7
        k += 1
    p.dither([(0, h - 3), (w, h - 3), (w, h), (0, h)], 0.5, 0)
    return p.sprite()


def _env(big=False):
    """信封：7×5 小包 / 30×19 大信封（三角封舌、背光网点）"""
    if not big:
        p = Part(7, 5)
        p.shape("rectangle", (0, 0, 6, 4), fill=1)
        p.d.line((1, 1, 3, 3), fill=0)
        p.d.line((3, 3, 5, 1), fill=0)
        return p.sprite()
    p = Part(30, 19)
    p.shape("rectangle", (0, 0, 29, 18), fill=1)
    p.d.rectangle((1, 1, 28, 17), outline=0)
    p.d.line((2, 2, 14, 10), fill=0)
    p.d.line((15, 10, 27, 2), fill=0)
    p.d.line((2, 16, 11, 9), fill=0)
    p.d.line((27, 16, 18, 9), fill=0)
    p.dither([(2, 12), (28, 12), (28, 16), (2, 16)], 0.5, 0)
    return p.sprite()


def _receipt():
    """回执包 9×7：信封上一个勾"""
    p = Part(9, 7)
    p.shape("rectangle", (0, 0, 8, 6), fill=1)
    p.d.line((2, 3, 3, 4), fill=0)
    p.d.line((4, 3, 6, 1), fill=0)
    p.px(3, 4, 0)
    return p.sprite()


def _phone():
    p = Part(5, 8)
    p.shape("rectangle", (0, 0, 4, 7), fill=1)
    p.d.rectangle((1, 1, 3, 5), fill=0)
    p.px(2, 6, 0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"laptop": _laptop, "router": _router, "gate": _gate, "cloud": lambda: _cloud(40, 10, 1),
                        "cloud2": lambda: _cloud(18, 8, 4), "env": _env, "big": lambda: _env(True),
                        "receipt": _receipt, "phone": _phone}[name]()
    return _PROPS[name]


STARS = [(14, 6), (30, 14), (47, 4), (62, 18), (71, 7), (90, 30), (122, 30), (38, 22), (6, 18)]


# ---------------------------------------------------------------- 画面

def sky(g: Gfx, t: float):
    for i, (x, y) in enumerate(STARS):
        ph = (t * 0.7 + i * 0.37) % 1
        g.px(x, y)
        if ph < 0.15:
            g.px(x - 1, y), g.px(x + 1, y), g.px(x, y - 1), g.px(x, y + 1)
    cx = 30 + (t * 1.5) % 60                        # 一朵小云慢慢飘
    pix.blit(g, prop("cloud2"), cx, 9)


def ground(g: Gfx):
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)


def table(g: Gfx):
    """露天供桌：桌面、桌围（网点）、桌围正中一个 Wi-Fi 纹"""
    x0, x1, ty = TABLE
    g.d.rectangle((x0, ty, x1, ty + 2), fill=1)
    g.d.line((x0 + 1, ty + 1, x1 - 1, ty + 1), fill=0)
    g.d.rectangle((x0 + 3, ty + 3, x1 - 3, FLOOR - 1), outline=1, fill=0)
    pix.checker(g, (x0 + 4, ty + 4, x1 - 3, FLOOR - 1), 0.125)
    cx, cy = (x0 + x1) // 2, FLOOR - 2
    g.d.rectangle((cx - 7, ty + 4, cx + 7, FLOOR - 1), fill=0)
    for r in (2, 4, 6):
        g.d.arc((cx - r, cy - r, cx + r, cy + r), 225, 315, fill=1)
    g.px(cx, cy)


def gate(g: Gfx, t: float, glow: float = 0.0, opened: float = 0.0):
    gx, gy = GATE
    if glow > 0:
        glow_rays(g, gx + 15, gy + 14, 17, 17 + 7 * glow, 14, t * 0.5, 0.8, dashed=True)
    pix.blit(g, prop("gate"), gx, gy)
    if opened > 0:                              # 两扇门往两边开，门里放光
        w = int(round(7 * opened))
        g.d.rectangle((gx + 15 - w, gy + 12, gx + 14 + w, gy + 19), fill=1)
        for i in range(w):
            g.px(gx + 15 - w + i, gy + 12 + (i % 2), 0) if i % 3 == 0 else None
        g.d.line((gx + 15 - w - 1, gy + 12, gx + 15 - w - 1, gy + 19), fill=0)
        g.d.line((gx + 15 + w, gy + 12, gx + 15 + w, gy + 19), fill=0)
    pix.blit(g, prop("cloud"), gx - 5, gy + 18)


def link(g: Gfx, t: float, gap: float = 0.0, flow: float = 0.0, upto: float = 1.0):
    """虚线链路（流动）。gap：中间断开的半宽（0..0.08）；upto：画到哪（入场时链路从天线长出去）"""
    n = 48
    for i in range(n + 1):
        u = i / n
        if u > upto or abs(u - 0.5) < gap:
            continue
        if (i + int(flow)) % 3 == 0:
            continue
        x, y = path(u)
        g.px(x, y)


def waves(g: Gfx, t: float, x: float, y: float, on: float = 1.0, n: int = 3):
    """Wi-Fi 波纹：三道弧一圈圈往外扩"""
    if on <= 0:
        return
    for j in range(n):
        k = (t * 1.1 + j / n) % 1
        if k > on:
            continue
        r = 3 + k * 9
        g.d.arc((x - r, y - r, x + r, y + r), 228, 312, fill=1)


def screen(g: Gfx, pct: float, bars: int, rate: str, mode: str = "up", t: float = 0.0):
    """笔记本屏：信号格 + 百分比，进度条，速率"""
    x0, y0, x1, y1 = SCR
    for i in range(4):                               # 信号格
        h = i + 1
        if i < bars:
            g.d.line((x0 + 1 + i * 2, y0 + 5 - h, x0 + 1 + i * 2, y0 + 5), fill=1)
        else:
            g.px(x0 + 1 + i * 2, y0 + 5)
    if mode == "pause":
        g.d.rectangle((x0 + 9, y0 + 3, x0 + 10, y0 + 12), fill=1)
        g.d.rectangle((x0 + 13, y0 + 3, x0 + 14, y0 + 12), fill=1)
        return
    if mode == "ok":
        g.d.line((x0 + 6, y0 + 8, x0 + 9, y0 + 11), fill=1)
        g.d.line((x0 + 9, y0 + 11, x0 + 16, y0 + 4), fill=1)
        g.d.line((x0 + 6, y0 + 9, x0 + 9, y0 + 12), fill=1)
        g.d.line((x0 + 9, y0 + 12, x0 + 16, y0 + 5), fill=1)
        return
    if mode == "boot":
        tiny(g, (x0 + x1) / 2 + 1, y0 + 6, "ZIP" if int(t * 4) % 2 == 0 else "", align="center")
        return
    tiny(g, x1, y0 + 1, f"{int(pct * 100)}%", align="right")
    g.d.rectangle((x0, y0 + 7, x1, y0 + 9), outline=1)
    w = int(round((x1 - x0 - 2) * clamp(pct)))
    if w > 0:
        g.d.line((x0 + 1, y0 + 8, x0 + w, y0 + 8), fill=1)
    tiny(g, (x0 + x1) / 2 + 1, y0 + 11, rate, align="center")


def router_leds(g: Gfx, t: float, on: bool):
    x, y = ROUTER
    for i in range(3):
        if on and (t * 7 + i * 1.7) % 2 < 1.2:
            g.px(x + 8 + i * 2, y + 7)


def mx_env(g: Gfx):
    """点阵：信封"""
    g.mx_rows([0, 0xFF, 0xC3, 0xA5, 0x99, 0x81, 0xFF, 0])


def mx_up(g: Gfx, t: float, pct: float, moving: bool = True, crossed: bool = False):
    """点阵：往上滚的上传箭头 + 底行进度"""
    if crossed:
        for i in range(7):
            g.mx_set(i, i), g.mx_set(6 - i, i)
    else:
        off = int(t * 5) % 8 if moving else 0
        art = ["...#...", "..###..", ".#.#.#.", "...#...", "...#...", "...#..."]
        for r, row in enumerate(art):
            y = (r - off) % 8
            if y > 6:
                continue
            for c, ch in enumerate(row):
                if ch == "#" and (moving or int(t * 3) % 2 == 0):
                    g.mx_set(c, y)
    for c in range(8):
        if c < int(round(pct * 8)):
            g.mx_set(c, 7)


@register
class Upload(R6):
    id = "r6.upload"
    name = "云端上表"
    desc = "小道士把表文封进信封塞进笔记本，Wi-Fi 链路把小信封一个个送进云中南天门；掉线时举着手机找信号"
    T = {"enter": 7.0, "interrupt": 1.8, "resume": 2.0, "complete": 5.5}
    CYCLE = 600.0

    def pct(self, e: float) -> float:
        return (e % self.CYCLE) / self.CYCLE

    def counter(self, g: Gfx, e: float, label: str | None = None):
        badge(g, label or nth(int(e // self.CYCLE) + 1, "表"))

    def moved(self, t: float) -> float:
        """持续阶段里“包在动”的时间（扣掉掉线停住的时间）"""
        n = int(t // LOOP)
        ph = t % LOOP
        stall = (n // 2) * (STALL[1] - STALL[0])
        if n % 2 == 1:
            stall += clamp(ph - STALL[0], 0, STALL[1] - STALL[0])
        return t - stall

    def packets(self, g: Gfx, m: float, gap: float = 0.0, blink: bool = False, t: float = 0.0, speed: float = 0.22):
        for j in range(4):
            u = (m * speed + j / 4) % 1
            if gap and abs(u - 0.5) < gap + 0.04:
                continue
            if blink and int(t * 6) % 2:
                continue
            if u > 0.93:
                continue
            x, y = path(u)
            pix.blit(g, prop("env"), x - 3, y - 2)

    def stage(self, g: Gfx, t: float, glow: float = 0.0, opened: float = 0.0):
        sky(g, t)
        ground(g)
        gate(g, t, glow, opened)
        table(g)
        pix.blit(g, prop("laptop"), *LAP)
        pix.blit(g, prop("router"), *ROUTER)

    def rate(self, t: float) -> str:
        return f"{60 + int(rand(int(t * 3), self.seed) * 39)}K/S"

    def typing(self, g: Gfx, t: float, face: str = "normal"):
        q = int(t * 7) % 2
        h = dao(g, DX, FLOOR, t, angle=-8 if q else -16, face=face)
        if int(t * 7) % 5 == 0 and (t * 7) % 1 < 0.2:
            g.px(h["hand"][0] + 1, h["hand"][1] - 3)
        return h

    # ------------------------------------------------------------ 入场：展表、折封、盖印、送进笔记本

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        self.stage(g, t)
        screen_mode = None
        stamp = None
        if t < 2.6:                                   # 剑指一点，表文在半空展开 → 卷起成信封
            dao(g, DX, FLOOR, t, pose="point" if t > 0.2 else "down")
            cx, top = 52, 5
            if t < 1.6:
                L = 2 + 18 * ease_out_back(span(t, 0.3, 1.0))
            else:
                L = lerp(20, 2, ease_in(span(t, 1.6, 2.2)))
            if 0.2 < t < 0.5 and int(t * 30) % 2 == 0:
                self.sparks.burst(DX + 16, FLOOR - 16, 1, 14, life=0.4, gravity=0)
            if t < 2.2:
                g.d.rectangle((cx - 8, top - 1, cx + 8, top + 1), fill=1)          # 上轴（两端轴头）
                g.px(cx - 8, top - 1, 0), g.px(cx + 8, top + 1, 0)
                if L > 3:
                    g.d.rectangle((cx - 6, top + 2, cx + 6, top + L), fill=1)
                    g.d.line((cx - 5, top + 3, cx + 5, top + 3), fill=0)
                    for c in range(4):                                          # 竖行字（右起）
                        x = cx + 4 - c * 3
                        for yy in range(top + 5, int(top + L) - 2):
                            if rand(yy * 3 + c, 7) < 0.72:
                                g.px(x, yy, 0)
                    if L > 15:                                                  # 落款小印
                        g.d.rectangle((cx - 5, top + L - 5, cx - 3, top + L - 3), fill=0)
                    g.d.rectangle((cx - 8, top + L + 1, cx + 8, top + L + 2), fill=1)  # 下轴
                    g.px(cx - 8, top + L + 2, 0), g.px(cx + 8, top + L + 1, 0)
            else:
                pix.blit(g, prop("env"), cx - 3, top + 1)
                if abs(t - 2.2) < dt * 0.6:
                    self.puffs.emit(cx, top + 3, vy=-4, life=0.6, rmax=2.5, spread=2)
                    self.sparks.burst(cx, top + 3, 8, 20, life=0.4, gravity=10)
        elif t < 4.3:                                 # 信封飞起放大 → 盖“封” → 缩小飞进屏幕
            dao(g, DX, FLOOR, t, pose="gong" if t < 3.6 else "down", face="wow" if 3.0 < t < 3.4 else "normal")
            big = prop("big")
            if t < 3.4:
                q = ease_out_back(span(t, 2.6, 3.0))
                s = 0.3 + 0.7 * q
                cx, cy = lerp(52, 60, ease_out(span(t, 2.6, 3.0))), lerp(8, 14, ease_out(span(t, 2.6, 3.0)))
            else:
                q = ease_in(span(t, 3.4, 4.1))
                s = 1 - 0.75 * q
                cx, cy = lerp(60, (SCR[0] + SCR[2]) / 2, q), lerp(14, (SCR[1] + SCR[3]) / 2, q)
            spr = pix.stretch(big, s, s)
            if t < 4.1:
                pix.blit(g, spr, cx - spr.w / 2, cy - spr.h / 2)
            if 3.0 <= t < 3.4:
                stamp = (cx, cy, span(t, 3.0, 3.12))
                if abs(t - 3.0) < dt * 0.6:
                    self.sparks.burst(cx, cy, 14, 34, life=0.5, gravity=30)
                if t < 3.15:
                    pix.shake(g, t, 1.5)
            if abs(t - 4.1) < dt * 0.6:
                self.sparks.burst((SCR[0] + SCR[2]) / 2, (SCR[1] + SCR[3]) / 2, 10, 24, life=0.4, gravity=20)
                pix.flash(g)
            if t >= 4.1:
                screen_mode = "boot"
        else:                                         # Wi-Fi 波纹、链路长出去、第一批包
            self.typing(g, t)
            on = span(t, 4.3, 4.9)
            waves(g, t, ROUTER[0] + 7, ROUTER[1] - 1, on)
            link(g, t, flow=t * 8, upto=ease_out(span(t, 4.6, 5.4)))
            if t > 5.4:
                self.packets(g, (t - 5.4), speed=0.22)
            router_leds(g, t, True)
            screen_mode = "up"
            if abs(t - 5.4) < dt * 0.6:
                gx, gy = GATE
                self.sparks.burst(P2[0], P2[1], 10, 24, life=0.5, gravity=20)
        if screen_mode == "boot":
            screen(g, 0, 0, "", "boot", t)
        elif screen_mode == "up":
            screen(g, 0, int(clamp((t - 4.3) * 5, 0, 4)), self.rate(t), "up", t)
        self.fx(g, dt)
        if t > 4.3:
            mx_up(g, t, 0)
        else:
            mx_env(g)
        if t > 5.4:
            self.counter(g, 0)
        if stamp:                                     # “封”字大印（最后画）
            cx, cy, k = stamp
            sz = 15
            yy = cy - sz / 2 - (1 - k) * 6
            g.d.rectangle((cx - sz / 2, yy, cx + sz / 2, yy + sz), fill=0)
            g.d.rectangle((cx - sz / 2, yy, cx + sz / 2, yy + sz), outline=1)
            g.text(cx, yy + 2, "封", align="center")

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self.renew(g, t, e, k, dt)
            return
        self.stage(g, t)
        n = int(t // LOOP)
        ph = t % LOOP
        stalled = n % 2 == 1 and STALL[0] <= ph < STALL[1]
        recovered = n % 2 == 1 and STALL[1] <= ph < STALL[1] + 1.5
        m = self.moved(t)
        bars = 0 if stalled else 4
        if stalled:
            bars = max(0, 3 - int((ph - STALL[0]) * 6))
        waves(g, t, ROUTER[0] + 7, ROUTER[1] - 1, 0 if stalled else 1)
        link(g, t, flow=m * 8)
        self.packets(g, m, blink=stalled, t=t)
        router_leds(g, t, not stalled)
        if stalled:                                   # 掏手机举过头顶找信号
            sk = ph - STALL[0]
            if sk < 0.6:
                self.typing(g, t, face="wow")
            else:
                jig = int(math.sin(t * 18) * 1.5)
                h = dao(g, DX + jig, FLOOR, t, pose="raise", face="wow")
                hx, hy = h["hand"]
                pix.blit(g, prop("phone"), hx - 2, hy - 7)
                waves(g, t * 1.5, hx, hy - 8, span(sk, 1.6, 3.0), n=2)
        elif recovered:
            if abs(ph - STALL[1]) < dt * 0.6:
                self.sparks.burst(ROUTER[0] + 7, ROUTER[1] + 2, 14, 30, up=12, life=0.6)
                pix.shake(g, t, 1)
            dao(g, DX, FLOOR, t, pose="down", face="happy")
        elif 12.0 < ph < 14.8:                        # 作揖 / 每三轮跪下拜一拜
            if n % 3 == 2:
                dao(g, DX, FLOOR, t, pose="kneel" if 12.6 < ph < 14.2 else "gong")
            else:
                dao(g, DX, FLOOR, t, pose="gong" if ph < 13.2 else "bow")
        elif 18.0 < ph < 21.0:                        # 停下来看一眼进度
            dao(g, DX, FLOOR, t, pose="down")
        else:
            self.typing(g, t)
        screen(g, k / self.CYCLE, bars, "0K/S" if stalled else self.rate(t))
        self.fx(g, dt)
        mx_up(g, t, k / self.CYCLE, moving=not stalled)
        self.counter(g, e)

    def renew(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """一表送达：天门放光、200 OK，回执包落回，再递一封新表"""
        glow = 1 - span(k, 1.6, 2.2) if k < 2.2 else 0
        self.stage(g, t, glow=span(k, 0, 0.4) * glow)
        waves(g, t, ROUTER[0] + 7, ROUTER[1] - 1, 1)
        link(g, t, flow=t * 8)
        router_leds(g, t, True)
        if abs(k - 0.05) < dt * 0.6 or (k < dt * 1.5 and k > 0):
            self.sparks.burst(P2[0], P2[1], 16, 34, up=10, life=0.7, gravity=30)
        if k < 0.3:
            pix.shake(g, t, 1)
        ok_text = 0.3 < k < 2.6
        if 1.4 < k < 3.4:                             # 回执包沿链路落回
            u = 1 - ease_in_out(span(k, 1.4, 3.2))
            x, y = path(u * 0.95)
            if k < 3.2:
                pix.blit(g, prop("receipt"), x - 4, y - 3)
            else:
                pass
        if abs(k - 3.2) < dt * 0.6:
            self.sparks.burst(P0[0], P0[1] + 2, 10, 24, up=10, life=0.5)
        if k < 3.2:
            screen(g, 1.0, 4, "DONE")
            self.typing(g, t, face="happy") if k < 1.4 else dao(g, DX, FLOOR, t, pose="down", face="wow" if k < 2 else "normal")
        elif k < 4.4:
            screen(g, 0, 4, "", "ok")
            dao(g, DX, FLOOR, t, pose="bow" if k > 3.5 else "gong", face="happy")
        else:                                         # 再递一封新表进去
            q = span(k, 4.4, 5.3)
            if k < 5.3:
                h = dao(g, DX, FLOOR, t, pose="offer")
                hx, hy = h["hand"]
                pix.blit(g, prop("env"), lerp(hx, (SCR[0] + SCR[2]) / 2, ease_in(q)) - 3,
                         lerp(hy - 4, (SCR[1] + SCR[3]) / 2, ease_in(q)) - 2)
                screen(g, 0, 4, "", "boot", t)
            else:
                self.typing(g, t)
                screen(g, 0, 4, self.rate(t))
                if abs(k - 5.3) < dt * 0.6:
                    pix.flash(g)
        self.fx(g, dt)
        mx_up(g, t, 1.0 if k < 3.2 else 0)
        self.counter(g, e if k >= 3.2 else e - k - 1)
        if ok_text:
            gx, gy = GATE
            g.d.rectangle((gx + 2, gy + 30, gx + 27, gy + 38), fill=0)
            tiny(g, gx + 15, gy + 32, "200 OK", align="center")

    # ------------------------------------------------------------ 中断 / 恢复

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        self.stage(g, t)
        gap = 0.07 * ease_out(span(t, 0.2, 0.5))
        waves(g, t, ROUTER[0] + 7, ROUTER[1] - 1, 1 - span(t, 0.2, 0.8))
        link(g, t, gap=gap, flow=0)
        m = 0.0
        self.packets(g, m, gap=gap if t > 0.2 else 0)
        bx, by = path(0.5)
        if t > 0.2:                                   # 断口附近的包掉下去
            q = t - 0.2
            if by + 60 * q * q < FLOOR:
                pix.blit(g, prop("env"), bx - 3 + q * 8, by - 2 + 60 * q * q)
            if int(t * 5) % 2 == 0:
                for i in range(-2, 3):
                    g.px(bx + i, by + i), g.px(bx + i, by - i)
        if abs(t - 0.2) < dt * 0.6:
            self.sparks.burst(bx, by, 10, 26, life=0.5)
        router_leds(g, t, t < 0.4)
        dao(g, DX, FLOOR, t, pose="down" if t < 0.4 else "gong", face="wow" if t < 1.0 else "normal")
        screen(g, k / self.CYCLE, 0 if t > 0.4 else 4, "", "pause" if t > 0.4 else "up")
        self.fx(g, dt)
        mx_up(g, t, k / self.CYCLE, crossed=t > 0.3)
        self.counter(g, e, "暂停" if t > 0.3 else None)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        self.stage(g, t)
        gap = 0.07 * (1 - ease_in(span(t, 0.4, 0.9)))
        waves(g, t, ROUTER[0] + 7, ROUTER[1] - 1, span(t, 0.2, 0.9))
        link(g, t, gap=gap, flow=t * 8)
        bx, by = path(0.5)
        if gap > 0.005 and int(t * 5) % 2 == 0:
            for i in range(-2, 3):
                g.px(bx + i, by + i), g.px(bx + i, by - i)
        if abs(t - 0.9) < dt * 0.6:
            self.sparks.burst(bx, by, 14, 30, up=8, life=0.6)
            pix.shake(g, t, 1)
        if t > 0.9:
            self.packets(g, t - 0.9)
            if 0.9 < t < 1.6:                         # 断点处续上的那个包
                u = 0.5 + (t - 0.9) * 0.22
                x, y = path(u)
                pix.blit(g, prop("env"), x - 3, y - 2)
        router_leds(g, t, t > 0.3)
        if t < 1.2:
            dao(g, DX, FLOOR, t, pose="point")
        else:
            self.typing(g, t)
        screen(g, k / self.CYCLE, int(clamp(t * 4, 0, 4)), self.rate(t), "up" if t > 0.4 else "pause")
        self.fx(g, dt)
        mx_up(g, t, k / self.CYCLE, moving=t > 0.9, crossed=t < 0.6)
        if t < 1.5:
            banner(g, 40, 9, "断点续传", span(t, 0.0, 0.35), t=t)
        else:
            self.counter(g, e)

    # ------------------------------------------------------------ 圆满：天门大开

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        p0 = self.pct(e) if e % self.CYCLE > 1 else 0.6
        p = lerp(p0, 1.0, ease_in(span(t, 0, 1.3)))
        opened = ease_out(span(t, 1.4, 2.2))
        self.stage(g, t, glow=span(t, 1.4, 1.8) * (1 if t < 4.5 else 1 - span(t, 4.5, 5.5)), opened=opened)
        waves(g, t * 2, ROUTER[0] + 7, ROUTER[1] - 1, 1 if t < 1.4 else 0)
        link(g, t, flow=t * 20, upto=1.0)
        if t < 1.4:
            self.packets(g, t * 3, speed=0.4)
        if abs(t - 1.4) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst(GATE[0] + 15, GATE[1] + 15, 26, 46, up=12, life=1.1, gravity=30)
        if 1.4 < t < 1.8:
            pix.shake(g, t, 1.6)
        router_leds(g, t, True)
        if t < 1.4:
            self.typing(g, t * 1.6)
        elif t < 4.3:
            dao(g, DX, FLOOR, t, pose="kneel")
        else:
            dao(g, DX, FLOOR, t, pose="gong", face="happy")
        screen(g, p, 4, "DONE" if p >= 1 else self.rate(t), "ok" if t > 2.0 else "up")
        self.fx(g, dt)
        ticks = t > 2.2
        if ticks:                                     # 两个勾“已读”
            for i in range(2):
                if t > 2.2 + i * 0.25:
                    x0, y0 = 91 + i * 5, 34
                    g.d.line((x0, y0 + 2, x0 + 2, y0 + 4), fill=1)
                    g.d.line((x0 + 2, y0 + 4, x0 + 6, y0), fill=1)
        mx_up(g, t, p, moving=t < 1.4)
        if t > 1.4:
            g.mx[:] = False
            r = (t - 1.4) * 4
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 0) - r) < 0.7:
                        g.mx[y, x] = True
            if t > 3.0:
                g.mx_rows([0, 1, 3, 0x86, 0xCC, 0x78, 0x30, 0])
            g.mx_level = 1 + int(6 * (1 - span(t, 1.4, 2.8)))
        if t < 2.0:
            self.counter(g, e)
        if ticks:
            g.text(104, 31, "已读")
        banner(g, 40, 8, "上达天听", span(t, 2.0, 2.4), t=t)
