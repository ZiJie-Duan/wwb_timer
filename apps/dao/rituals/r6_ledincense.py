"""赛博烧香（像素风）：供桌上一只插电的电子香炉，三根 LED 香随计时一格格变短，香头冒“数字烟”。

小道士从左边走进来，捡起地上的电源线，转身插进墙上的插座——电火花一闪、屏幕一震，炉肚上的小屏 BOOT，
三根 LED 香自下而上逐格点亮，香头亮起，数字烟升起。
持续：LED 香随计时变短（一轮 10 分钟），炉屏显示剩余电量；小道士低头看手机，隔一阵敲手机上的“电子木鱼”，
      “功德+1”往上飘；再对着香炉作个揖；每隔一阵香炉信号毛刺（画面错位、屏显 ERR），小道士拿手机一指“遥控重启”。
      一轮烧完：炉屏 0% 闪 LOW，小道士扫码“续费”，三根新香逐格亮起，“第几炷”加一。
中断：手机一指，LED 自上而下熄成空心管，炉屏 OFF，“待机”。  恢复：再一指，LED 逐格亮回，香头一闪重燃。
圆满：炉屏 MAX 超频，LED 跑马灯飞速燃尽，香头喷出一大股 0/1，闪白，小道士跪拜，“心存帝前”。
文字取自道教《祝香咒》：“道由心学，心假香传。香焚玉炉，心存帝前。”
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx
from ..engine.scene import register
from .r6_common import R6, badge, banner, dao, glow_rays, nth, pixsmoke, rise, tiny

FLOOR = 58
TABLE = (60, 122, 45)          # 供桌 x0, x1, 桌面 y
CX = 88                        # 香炉中心
C_TOP = TABLE[2] - 20          # 香炉精灵顶
BASE = C_TOP + 5               # LED 香插进炉口的位置
STICK_DX = (-7, 0, 7)
FULL = 15
STUB = 3
DAO_X = 36
SOCKET = (6, 39)               # 墙上插座左上角
PLUG_TIP = (15, 43)            # 插头插好时插头尾巴的位置
PORT = (CX - 18, C_TOP + 11)   # 炉身左侧的 USB 口
RENEW = 6.0
LOOP = 24.0                    # 小道士的动作循环


# ---------------------------------------------------------------- 道具（像素造型，只生成一次）

def _censer():
    """电子香炉 37×20：立耳（右耳带电源指示灯孔）、口沿、鼓腹、肚上一块 LCD、两侧 PCB 走线与过孔、三足"""
    p = Part(37, 20)
    p.shape("rectangle", (2, 0, 6, 5), fill=1)        # 左耳
    p.shape("rectangle", (30, 0, 34, 5), fill=1)      # 右耳
    p.d.rectangle((3, 1, 5, 3), fill=0)
    p.d.rectangle((31, 1, 33, 3), fill=0)
    p.shape("rectangle", (0, 5, 36, 6), fill=1)       # 口沿
    p.d.line((1, 6, 35, 6), fill=0)
    p.shape("polygon", [(2, 7), (34, 7), (36, 10), (33, 16), (3, 16), (0, 10)], fill=1)  # 炉腹
    p.d.rectangle((10, 8, 26, 15), fill=0)            # LCD 窗
    p.d.line((11, 15, 25, 15), fill=1)
    p.px(10, 8, 1), p.px(26, 8, 1)
    for sx in (1, -1):                                # 两侧 PCB 走线 + 过孔
        x0 = 8 if sx > 0 else 28
        p.d.line((x0, 9, x0 - 4 * sx, 9), fill=0)
        p.d.line((x0 - 4 * sx, 9, x0 - 4 * sx, 11), fill=0)
        p.d.line((x0, 12, x0 - 2 * sx, 14), fill=0)
        vx = min(x0 - 5 * sx, x0 - 4 * sx)
        p.d.rectangle((vx, 12, vx + 1, 13), fill=0)
        p.px(vx + (0 if sx > 0 else 1), 12, 1)
    p.dither([(29, 12), (36, 10), (33, 16), (28, 16)], 0.5, 0)
    p.d.rectangle((0, 10, 1, 11), fill=0)             # USB 口
    for x in (5, 17, 30):                             # 三足（兽足：上粗下尖、外撇）
        p.shape("rectangle", (x, 16, x + 2, 17), fill=1)
        p.shape("rectangle", (x, 18, x + 1, 19), fill=1)
        p.px(x - 1, 19)
    return p.sprite()


def _socket():
    """墙上的五孔插座 10×10：圆角面板、两孔斜插 + 接地孔"""
    p = Part(10, 10)
    p.shape("rectangle", (0, 1, 9, 8), fill=1)
    p.shape("rectangle", (1, 0, 8, 9), fill=1)
    p.d.rectangle((1, 1, 8, 8), outline=0)
    p.px(3, 3, 0), p.px(6, 3, 0)            # 两极
    p.px(2, 4, 0), p.px(7, 4, 0)
    p.d.line((4, 6, 5, 6), fill=0)          # 接地
    p.dither([(6, 6), (8, 6), (8, 8), (6, 8)], 0.5, 0)
    return p.sprite()


def _plug():
    """电源插头 6×5（插好时露在外面的部分，朝右接线）"""
    p = Part(6, 5)
    p.shape("rectangle", (0, 0, 4, 4), fill=1)
    p.shape("rectangle", (5, 1, 5, 3), fill=1)
    p.d.line((1, 1, 1, 3), fill=0)
    p.px(3, 2, 0)
    return p.sprite()


def _plug_loose():
    """手里 / 地上的插头 8×5：两只插脚朝前"""
    p = Part(8, 5)
    p.shape("rectangle", (3, 0, 7, 4), fill=1)
    p.shape("line", (0, 1, 2, 1), fill=1)
    p.shape("line", (0, 3, 2, 3), fill=1)
    p.d.line((5, 1, 5, 3), fill=0)
    return p.sprite()


def _phone():
    """手机 5×8：竖着拿，屏幕黑、顶上听筒"""
    p = Part(5, 8)
    p.shape("rectangle", (0, 0, 4, 7), fill=1)
    p.d.rectangle((1, 1, 3, 5), fill=0)
    p.px(2, 6, 0)
    return p.sprite()


def _qr():
    """墙上的“扫码上香”二维码海报 19×21：三个定位角 + 伪随机码点，挂绳，底边胶带"""
    p = Part(19, 21)
    p.shape("rectangle", (0, 2, 18, 20), fill=1)
    p.d.rectangle((1, 3, 17, 19), fill=0)
    for x, y in ((2, 4), (12, 4), (2, 14)):
        p.d.rectangle((x, y, x + 4, y + 4), outline=1)
        p.d.rectangle((x + 2, y + 2, x + 2, y + 2), fill=1)
    for y in range(4, 19):
        for x in range(2, 17):
            if (x < 8 and y < 10) or (x > 10 and y < 10) or (x < 8 and y > 12):
                continue
            if rand(x * 31 + y * 7, 5) < 0.5:
                p.px(x, y)
    p.shape("line", (6, 2, 9, 0), fill=1)
    p.shape("line", (12, 2, 9, 0), fill=1)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"censer": _censer, "socket": _socket, "plug": _plug, "plug_loose": _plug_loose,
                        "phone": _phone, "qr": _qr}[name]()
    return _PROPS[name]


MUYU = pix.frames("""
 ##
####
#..#
---
 ##
####
####
""")


# ---------------------------------------------------------------- 画面

def room(g: Gfx, t: float, plugged: bool):
    """背景：地砖、踢脚、柱、插座、二维码海报、供桌（桌围中间一个电源标志）"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    for x in (1, 126):
        g.d.line((x, 0, x, FLOOR - 4), fill=1)
    pix.blit(g, prop("qr"), 106, 1)
    pix.blit(g, prop("socket"), *SOCKET)
    x0, x1, ty = TABLE
    g.d.rectangle((x0, ty, x1, ty + 2), fill=1)
    g.d.line((x0 + 1, ty + 1, x1 - 1, ty + 1), fill=0)
    g.d.rectangle((x0 + 3, ty + 3, x1 - 3, FLOOR - 1), outline=1, fill=0)
    g.d.line((x0 + 3, ty + 5, x1 - 3, ty + 5), fill=1)
    pix.checker(g, (x0 + 4, ty + 6, x1 - 3, FLOOR - 1), 0.125)
    cx, cy = (x0 + x1) // 2, ty + 8
    g.d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=0)          # 桌围上的电源标志 ⏻
    g.d.arc((cx - 3, cy - 3, cx + 3, cy + 3), 300, 240, fill=1)
    g.d.line((cx, cy - 4, cx, cy), fill=1)
    if plugged and int(t * 2) % 2:
        g.d.arc((cx - 5, cy - 5, cx + 5, cy + 5), 0, 360, fill=1)


def cord(g: Gfx, end, plugged: bool):
    """电源线：炉身 USB 口 → 沿桌面 → 桌角垂下 → 地上 → 插头（插座里 / 手里 / 地上）"""
    px, py = PORT
    pts = [(px - 1, py), (px - 3, py + 2), (px - 4, TABLE[2] - 1), (TABLE[0] - 1, TABLE[2] - 1),
           (TABLE[0] - 3, TABLE[2] + 3), (TABLE[0] - 3, FLOOR - 3), (TABLE[0] - 6, FLOOR - 1)]
    ex, ey = end
    if ey >= FLOOR - 4:               # 插头躺在地上
        pts.append((ex + 8, FLOOR - 1))
        g.d.line(pts, fill=1)
        pix.blit(g, prop("plug_loose"), ex, FLOOR - 5)
        return
    # 地上一段，然后往上弯到插头（插座里或手里），中间下垂
    fx = min(ex + 12, TABLE[0] - 8)
    pts.append((fx, FLOOR - 1))
    sag = []
    for i in range(1, 9):
        k = i / 8
        sag.append((lerp(fx, ex, k), lerp(FLOOR - 1, ey, k) + math.sin(k * math.pi) * 2))
    g.d.line(pts + sag, fill=1)


def sticks(g: Gfx, length: float, lit: float, t: float, hollow: bool = False, glitch: bool = False,
           chase: float | None = None):
    """三根 LED 香：亮的部分是一摞 3×2 的发光格（格间一道暗缝），没亮的是虚线描的空管；香头一颗 LED 明灭。
    lit：亮到多高（0..length，从下往上）；chase：跑马灯相位（圆满超频）"""
    L = int(round(length))
    for i, dx in enumerate(STICK_DX):
        x = CX + dx
        top = BASE - L
        if L <= 0:
            continue
        g.d.rectangle((x - 2, top - 1, x + 2, BASE), fill=0)        # 管子外沿留黑（压在烟上也清楚）
        for r in range(L):
            y = BASE - 1 - r
            on = r < lit
            if chase is not None:
                on = int(r / 3 + chase + i) % 3 != 0
            if glitch:
                on = on and rand(int(t * 20) * 31 + r // 3 + i * 7, 3) > 0.35
            if on:
                if r % 3 != 2:
                    g.d.line((x - 1, y, x + 1, y), fill=1)
                else:
                    g.px(x - 1, y), g.px(x + 1, y)
            elif r % 2 == 0:
                g.px(x - 1, y), g.px(x + 1, y)
        if lit < L - 0.5 or chase is not None:
            g.px(x, top - 1) if lit < L - 0.5 else None
        if not hollow and lit >= L - 0.5 and chase is None:   # 香头 LED：菱形一明一暗
            on = (t * 2.3 + i * 0.41) % 1 < 0.7
            g.d.line((x - 1, top - 1, x + 1, top - 1), fill=1)
            g.px(x, top - 2)
            if on:
                g.px(x, top - 3)
                g.px(x - 2, top - 1), g.px(x + 2, top - 1)


def lcd(g: Gfx, s: str, blink: bool = False, t: float = 0.0):
    """炉肚小屏（13×5 的显示区）"""
    if blink and int(t * 4) % 2:
        return
    tiny(g, CX, C_TOP + 9, s, align="center")


def power_led(g: Gfx, on: bool):
    """右耳的电源指示灯"""
    if on:
        x = CX - 18 + 31
        g.d.rectangle((x, C_TOP + 1, x + 2, C_TOP + 3), fill=1)
        g.px(x + 1, C_TOP + 2, 0)


def tips(length: float):
    return [(CX + dx, BASE - int(round(length)) - 3) for dx in STICK_DX]


def mx_led(g: Gfx, length: float, lit: float, t: float, hollow: bool = False):
    """点阵：炉身 + 三根 LED 香柱（按格亮），香头闪"""
    g.mx[7, 1:7] = True
    g.mx[6, 1] = g.mx[6, 6] = True
    g.mx[5, 1:7] = True
    h = int(round(length / FULL * 5))
    hl = int(round(lit / FULL * 5))
    for i, col in enumerate((2, 4, 6)):
        c = col - (1 if i == 2 else 0) if col == 6 else col
        for r in range(h):
            y = 4 - r
            if y < 0:
                break
            g.mx[y, c] = (r < hl) or (hollow and r % 2 == 0)
        if not hollow and hl >= h and h > 0 and 4 - h >= 0:
            g.mx[4 - h, c] = (t * 2.3 + i * 0.41) % 1 < 0.7


def glitch_band(g: Gfx, t: float, seed: int = 0):
    """信号毛刺：几条横带左右错位"""
    a = g.array()
    for j in range(3):
        y0 = int(rand(int(t * 15) * 3 + j, seed) * 40)
        hh = 2 + int(rand(int(t * 15) * 5 + j, seed + 1) * 4)
        sh = int((rand(int(t * 15) * 7 + j, seed + 2) - 0.5) * 10)
        a[y0:y0 + hh] = np.roll(a[y0:y0 + hh], sh, axis=1)
    g.put(a)


@register
class LedIncense(R6):
    id = "r6.ledincense"
    name = "赛博烧香"
    desc = "小道士把电子香炉插上电，三根 LED 香逐格点亮、冒数字烟；他低头敲电子木鱼“功德+1”，烧完扫码续费"
    T = {"enter": 7.0, "interrupt": 1.8, "resume": 2.0, "complete": 5.5}
    CYCLE = 600.0

    def init(self):
        self.taps = -1

    def length(self, e: float) -> float:
        return lerp(FULL, STUB, (e % self.CYCLE) / self.CYCLE)

    def smoke(self, g: Gfx, length: float, t: float, amount: float = 1.0):
        if amount <= 0:
            return
        for i, (x, y) in enumerate(tips(length)):
            pixsmoke(g, x, y - 1, t + i * 0.83, seed=self.seed * 3 + i, height=max(y - 2, 6), amount=amount,
                     drift=math.sin(t * 0.3 + i) * 3 - 1)

    def phone(self, g: Gfx, hand, screen: str = "", t: float = 0.0, beam=None):
        """手里的手机（屏幕：木鱼 / 二维码 / 亮）"""
        hx, hy = hand
        pix.blit(g, prop("phone"), hx - 2, hy - 6)
        if screen == "muyu":
            pix.blit(g, pix.anim(MUYU, t, 4), hx - 2, hy - 4, outline=False)
        elif screen == "qr":
            for yy in range(3):
                for xx in range(3):
                    if rand(xx * 3 + yy + int(t * 3), 9) < 0.55:
                        g.px(hx - 1 + xx, hy - 5 + yy)
        elif screen == "on":
            g.d.rectangle((hx - 1, hy - 5, hx + 1, hy - 1), fill=1)
        if beam is not None:          # 遥控：一道虚线红外飞到炉身
            k, (tx, ty) = beam
            if 0 < k < 1:
                x1, y1 = lerp(hx + 2, tx, k), lerp(hy - 4, ty, k)
                pix.dotted(g, hx + 2, hy - 4, x1, y1, 3, int(k * 9))
                g.d.rectangle((x1 - 1, y1 - 1, x1 + 1, y1 + 1), fill=1)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        badge(g, label or nth(int(e // self.CYCLE) + 1, "炷"))

    # ------------------------------------------------------------ 入场：捡线、插电、开机

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        plugged = t >= 3.8
        room(g, t, plugged)
        # 小道士：走进来 → 低头捡插头 → 转身走到插座 → 插 → 回身
        if t < 2.0:
            x = lerp(-12, 44, ease_out(span(t, 0, 2.0)))
            end = (44, FLOOR)
            cord(g, end, False)
            sticks(g, FULL, 0, t, hollow=True)
            pix.blit(g, prop("censer"), CX - 18, C_TOP)
            dao(g, x, FLOOR, t, pose="walk")
        elif t < 2.6:
            cord(g, (44, FLOOR) if t < 2.3 else (49, FLOOR - 12), False)
            sticks(g, FULL, 0, t, hollow=True)
            pix.blit(g, prop("censer"), CX - 18, C_TOP)
            if t < 2.3:
                dao(g, 44, FLOOR, t, pose="bow")
            else:
                h = dao(g, 44, FLOOR, t, angle=-20)
                pix.blit(g, _flipped_plug(), h["hand"][0] - 2, h["hand"][1] - 2)
        elif t < 3.8:
            q = ease_in_out(span(t, 2.6, 3.4))
            x = lerp(44, 30, q)
            reach = span(t, 3.4, 3.8)
            sticks(g, FULL, 0, t, hollow=True)
            pix.blit(g, prop("censer"), CX - 18, C_TOP)
            if t < 3.4:
                h = dao(g, x, FLOOR, t, angle=-15, flip=True, legs="walk")
            else:
                h = dao(g, x + 2 - reach * 2, FLOOR, t, angle=lerp(-10, 0, reach), flip=True, face="wow")
            hx, hy = h["hand"]
            cord(g, (hx + 3, hy), False)
            pix.blit(g, prop("plug_loose"), hx - 6, hy - 2)
        else:
            cord(g, PLUG_TIP, True)
            pix.blit(g, prop("plug"), PLUG_TIP[0] - 6, PLUG_TIP[1] - 2)
            if t < 3.8 + dt * 1.5:          # 插上：电火花 + 闪白 + 震屏
                self.sparks.burst(PLUG_TIP[0] - 5, PLUG_TIP[1], 16, 40, up=10, life=0.5, gravity=60)
                pix.flash(g)
            if t < 4.1:
                pix.shake(g, t, 1.5)
            # 开机：BOOT → 逐格点亮 → 香头亮起
            fill = span(t, 4.4, 5.8) * FULL
            booted = t > 4.0
            sticks(g, FULL, fill, t, hollow=fill < FULL)
            pix.blit(g, prop("censer"), CX - 18, C_TOP)
            power_led(g, booted)
            if 4.0 < t < 4.4:
                lcd(g, "BOOT", blink=True, t=t)
            elif t >= 4.4:
                lcd(g, f"{int(fill / FULL * 100)}%")
            if abs(t - 5.8) < dt * 0.6:
                for x, y in tips(FULL):
                    self.sparks.burst(x, y, 6, 22, up=12, life=0.5)
                pix.shake(g, t, 1)
            self.smoke(g, FULL, t, amount=span(t, 5.8, 7.0))
            # 小道士：回身 → 拱手 → 掏出手机
            if t < 4.8:
                q = ease_in_out(span(t, 3.9, 4.8))
                dao(g, lerp(30, DAO_X, q), FLOOR, t, pose="walk" if t > 4.1 else "down", face="happy")
            elif t < 6.3:
                dao(g, DAO_X, FLOOR, t, pose="gong" if t < 5.8 else "down", face="happy" if t > 5.8 else "normal")
            else:
                h = dao(g, DAO_X, FLOOR, t, angle=-35)
                self.phone(g, h["hand"])
        self.fx(g, dt)
        mx_led(g, FULL, span(t, 4.4, 5.8) * FULL if t > 4.4 else 0, t, hollow=t < 5.8)
        if t >= 5.8:
            self.counter(g, 0)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self.renew(g, t, e, k, dt)
            return
        L = self.length(e)
        room(g, t, True)
        cord(g, PLUG_TIP, True)
        pix.blit(g, prop("plug"), PLUG_TIP[0] - 6, PLUG_TIP[1] - 2)
        ph = t % LOOP
        glitch_on = int(t // LOOP) % 2 == 1 and 18.5 < ph < 22.5
        gk = ph - 18.5
        glitching = glitch_on and gk < 1.6
        sticks(g, L, L, t, glitch=glitching)
        pix.blit(g, prop("censer"), CX - 18, C_TOP)
        power_led(g, True)
        if glitching:
            lcd(g, "ERR", blink=True, t=t)
        elif glitch_on and gk < 3.0:
            lcd(g, "OK")
        else:
            lcd(g, f"{int(round(100 * (1 - k / self.CYCLE)))}%")
        self.smoke(g, L, t, amount=0.4 if glitching else 1.0)
        # 小道士
        tap_text = None
        if 9.0 < ph < 15.0:                       # 敲电子木鱼
            n = int((ph - 9.0) / 0.75)
            q = ((ph - 9.0) % 0.75) / 0.75
            h = dao(g, DAO_X, FLOOR, t, angle=-5 + (6 if q < 0.25 else 0), face="happy")
            self.phone(g, h["hand"], "muyu", 2 * q)
            if n != self.taps and q < 0.25:
                self.taps = n
                self.sparks.burst(h["hand"][0], h["hand"][1] - 6, 3, 12, up=8, life=0.3, gravity=20)
            tap_text = (q * 0.75, h["hand"])
        elif 15.0 <= ph < 17.6:                   # 作揖
            dao(g, DAO_X, FLOOR, t, pose="gong" if ph < 15.8 else "bow")
        elif glitch_on and 1.4 < gk < 3.0:        # 遥控重启
            h = dao(g, DAO_X, FLOOR, t, angle=12, face="normal")
            q = span(gk, 1.4, 2.0)
            self.phone(g, h["hand"], "on", t, beam=(q, (CX - 9, C_TOP + 11)))
            if abs(gk - 2.0) < dt * 0.6:
                self.sparks.burst(CX, C_TOP + 9, 8, 26, up=10, life=0.45)
                pix.shake(g, t, 1)
        else:
            h = dao(g, DAO_X, FLOOR, t, angle=-35, face="wow" if glitching else "normal")
            self.phone(g, h["hand"])
        self.fx(g, dt)
        if glitching and int(t * 15) % 3 != 0:
            glitch_band(g, t, self.seed)
        mx_led(g, L, L if not glitching else L * rand(int(t * 10), 2), t)
        self.counter(g, e)
        if tap_text:
            age, (hx, hy) = tap_text
            rise(g, 64, 28, "功德+1", age, life=0.72, dist=8)

    def renew(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """续香：0% LOW → 扫码续费 → 新香逐格亮起"""
        room(g, t, True)
        cord(g, PLUG_TIP, True)
        pix.blit(g, prop("plug"), PLUG_TIP[0] - 6, PLUG_TIP[1] - 2)
        n_old = int(e // self.CYCLE)
        if k < 2.6:
            sticks(g, STUB, STUB if k < 1.2 and int(k * 6) % 2 == 0 else 0, t, hollow=True)
            pix.blit(g, prop("censer"), CX - 18, C_TOP)
            power_led(g, int(k * 4) % 2 == 0)
            lcd(g, "0%" if int(k * 2) % 2 == 0 else "LOW")
            if k < 1.2:
                h = dao(g, DAO_X, FLOOR, t, angle=-35, face="wow")
                self.phone(g, h["hand"])
            else:
                h = dao(g, DAO_X, FLOOR, t, angle=10)
                self.phone(g, h["hand"], "qr", t)
                if abs(k - 2.2) < dt * 0.6:
                    self.sparks.burst(h["hand"][0], h["hand"][1] - 4, 8, 20, up=10, life=0.4)
            self.fx(g, dt)
            mx_led(g, STUB, 0, t, hollow=True)
            self.counter(g, n_old * self.CYCLE - 1)
            if k > 2.2:
                rise(g, 64, 26, "续费成功", k - 2.2, life=1.4, dist=6)
            return
        fill = span(k, 2.8, 4.4) * FULL
        sticks(g, FULL, fill, t, hollow=fill < FULL)
        pix.blit(g, prop("censer"), CX - 18, C_TOP)
        power_led(g, True)
        lcd(g, f"{int(fill / FULL * 100)}%")
        if abs(k - 4.4) < dt * 0.6:
            for x, y in tips(FULL):
                self.sparks.burst(x, y, 6, 22, up=12, life=0.5)
        if 4.4 < k < 4.7:
            pix.shake(g, t, 1)
        self.smoke(g, FULL, t, amount=span(k, 4.4, RENEW))
        if k < 4.6:
            h = dao(g, DAO_X, FLOOR, t, angle=-35, face="happy")
            self.phone(g, h["hand"])
        elif k < 5.6:
            dao(g, DAO_X, FLOOR, t, pose="gong", face="happy")
        else:
            h = dao(g, DAO_X, FLOOR, t, angle=-35)
            self.phone(g, h["hand"])
        self.fx(g, dt)
        mx_led(g, FULL, fill, t, hollow=fill < FULL)
        self.counter(g, e)
        if k < 3.6:
            rise(g, 64, 26, "续费成功", k - 2.2, life=1.4, dist=6)

    # ------------------------------------------------------------ 中断 / 恢复

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        L = self.length(e)
        room(g, t, True)
        cord(g, PLUG_TIP, True)
        pix.blit(g, prop("plug"), PLUG_TIP[0] - 6, PLUG_TIP[1] - 2)
        lit = L * (1 - ease_in(span(t, 0.7, 1.4)))
        sticks(g, L, lit, t, hollow=lit < L)
        pix.blit(g, prop("censer"), CX - 18, C_TOP)
        power_led(g, t < 0.7)
        if t >= 0.7:
            lcd(g, "OFF")
        else:
            lcd(g, f"{int(round(100 * (1 - (e % self.CYCLE) / self.CYCLE)))}%")
        if abs(t - 0.7) < dt * 0.6:
            for x, y in tips(L):
                self.puffs.emit(x, y - 1, vy=-5, life=0.8, rmax=2.2, spread=0)
        self.smoke(g, L, t, amount=1 - span(t, 0.7, 1.2))
        if t < 0.25:
            h = dao(g, DAO_X, FLOOR, t, angle=-35)
            self.phone(g, h["hand"])
        elif t < 1.3:
            h = dao(g, DAO_X, FLOOR, t, angle=12)
            self.phone(g, h["hand"], "on", t, beam=(span(t, 0.3, 0.7), (CX - 9, C_TOP + 11)))
        else:
            h = dao(g, DAO_X, FLOOR, t, angle=-35)
            self.phone(g, h["hand"])
        self.fx(g, dt)
        mx_led(g, L, lit, t, hollow=lit < L)
        self.counter(g, e, "待机" if t > 0.7 else None)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        L = self.length(e)
        room(g, t, True)
        cord(g, PLUG_TIP, True)
        pix.blit(g, prop("plug"), PLUG_TIP[0] - 6, PLUG_TIP[1] - 2)
        lit = L * ease_out(span(t, 0.7, 1.4))
        sticks(g, L, lit, t, hollow=lit < L)
        pix.blit(g, prop("censer"), CX - 18, C_TOP)
        power_led(g, t >= 0.6)
        if t < 0.6:
            lcd(g, "OFF")
        elif t < 0.9:
            lcd(g, "ON", blink=True, t=t)
        else:
            lcd(g, f"{int(round(100 * (1 - (e % self.CYCLE) / self.CYCLE)))}%")
        if abs(t - 1.4) < dt * 0.6:
            for x, y in tips(L):
                self.sparks.burst(x, y, 6, 22, up=12, life=0.5)
            pix.flash(g)
        if 1.4 < t < 1.65:
            pix.shake(g, t, 1)
        self.smoke(g, L, t, amount=span(t, 1.4, 2.0))
        if 0.15 < t < 1.2:
            h = dao(g, DAO_X, FLOOR, t, angle=12)
            self.phone(g, h["hand"], "on", t, beam=(span(t, 0.2, 0.6), (CX - 9, C_TOP + 11)))
        else:
            h = dao(g, DAO_X, FLOOR, t, angle=-35, face="happy" if t > 1.4 else "normal")
            self.phone(g, h["hand"])
        self.fx(g, dt)
        mx_led(g, L, lit, t, hollow=lit < L)
        self.counter(g, e, "待机" if t < 0.6 else None)

    # ------------------------------------------------------------ 圆满：超频燃尽，0/1 冲天

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        L0 = self.length(e)
        L = lerp(L0, 0, ease_in(span(t, 0.2, 1.6)))
        room(g, t, True)
        cord(g, PLUG_TIP, True)
        pix.blit(g, prop("plug"), PLUG_TIP[0] - 6, PLUG_TIP[1] - 2)
        if t < 1.6:
            sticks(g, L, L, t, chase=t * 14)
            if int(t * 30) % 2 == 0:              # 香头喷 0/1
                for x, y in tips(L):
                    self.bits.burst(x, y, 1, 26, up=26, life=0.9, gravity=30)
            pix.shake(g, t, 0.6)
        pix.blit(g, prop("censer"), CX - 18, C_TOP)
        power_led(g, True)
        if t < 1.6:
            lcd(g, "MAX", blink=True, t=t)
        else:
            lcd(g, "100")
        if abs(t - 1.6) < dt * 0.6:                # 闪白：一大股 0/1 冲天
            pix.flash(g)
            self.bits.burst(CX, BASE - 2, 14, 46, up=36, life=1.6, gravity=30)
            self.sparks.burst(CX, BASE - 2, 26, 44, up=24, life=1.2, gravity=40)
        if 1.6 < t < 2.0:
            pix.shake(g, t, 1.8)
        if 1.6 < t < 4.5:
            glow_rays(g, CX, C_TOP + 9, 19, 19 + 8 * span(t, 1.6, 2.4), 14, t * 0.6, 0.55, dashed=True)
        if t < 1.6:
            h = dao(g, DAO_X, FLOOR, t, angle=-35, face="wow")
            self.phone(g, h["hand"])
        elif t < 4.2:
            dao(g, DAO_X, FLOOR, t, pose="kneel")
        else:
            dao(g, DAO_X, FLOOR, t, pose="gong", face="happy")
        self.fx(g, dt)
        mx_led(g, max(L, 1), max(L, 1) if t < 1.6 else 0, t)
        if t > 1.6:
            r = (t - 1.6) * 4
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - r) < 0.6:
                        g.mx[y, x] = True
            for j in range(5):                       # 0/1 往上冲
                u = (t * 1.6 + j * 0.37) % 1
                g.mx_set(int(rand(j * 7 + int(t * 1.6 + j * 0.37), 4) * 6) + 1, int(4 - u * 5))
            g.mx_level = 1 + int(6 * (1 - span(t, 1.6, 3.0)))
        else:
            g.mx_level = 3
        badge(g, nth(int(e // self.CYCLE) + 1, "炷")) if t < 2.0 else None
        banner(g, 44, 6, "心存帝前", span(t, 2.0, 2.4), t=t)


_FP = None


def _flipped_plug():
    global _FP
    if _FP is None:
        _FP = prop("plug_loose").flip()
    return _FP
