"""x6 赛博歇（一）：电源与散热——充电、待机、散热"""
from __future__ import annotations

import math

from ..engine.anim import (blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp,
                           noise, pulse, rand, span)
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x6_common import SAGE_H, SAGE_W, sage


def bezier(p0, p1, p2, k: float):
    u = 1 - k
    return (u * u * p0[0] + 2 * u * k * p1[0] + k * k * p2[0], u * u * p0[1] + 2 * u * k * p1[1] + k * k * p2[1])


def spark(g: Gfx, x: float, y: float, p: float, n: int = 6, r0: float = 2, r1: float = 8, seed: int = 0):
    """一下火花：放射短线，p 0..1"""
    if not 0 < p < 1:
        return
    for i in range(n):
        a = i / n * 2 * math.pi + rand(i, seed) * 0.6
        ra, rb = r0 + (r1 - r0) * p, r0 + (r1 - r0) * min(1, p + 0.35)
        g.d.line((x + math.cos(a) * ra, y + math.sin(a) * ra, x + math.cos(a) * rb, y + math.sin(a) * rb), fill=1)


# ====================================================================== 充电

BOLT = Sprite("""
  ##
 ##
####
  ##
 ##
 #
""")
PLUG = Sprite("""
 ######
#......#####
#......#
#......#####
 ######
""")


@register
class Charge(Rest):
    id = "x6.charge"
    name = "插电"
    desc = "道士盘坐插电养气，电量充到 99% 他睁一只眼，插头自己蹦了出来——持而盈之，不如其已；浮空放电，插头再跳回插座"
    T = {"enter": 2.6, "exit": 1.2}
    C = 110.0           # 一轮：充电 0–70，拔插头 74，浮空放电，104 插回

    SX, SY = 4, 27                   # 道士左上角
    SOCK = (112, 44)                 # 插座左上角
    CABLE0 = (38, 59)                # 线从道士身后出来

    def setup(self):
        self._ht = 0.0

    # ------------------------------------------------------------ 零件

    def plug_pos(self, u: float) -> tuple[float, float, bool]:
        """插头位置（插头头部左上角）与是否插着；u = 本轮秒数"""
        home = (self.SOCK[0] - 11, self.SOCK[1] + 5)
        floor = (86, 57)
        if u < 74 or u >= 107.4:
            return home[0], home[1], True
        if u < 75.2:  # 被拔出：抛起落地
            k = span(u, 74, 75.2)
            x = lerp(home[0], floor[0], ease_out(k))
            y = lerp(home[1], floor[1], ease_out_bounce(k)) - math.sin(k * math.pi) * 8
            return x, y, False
        if u < 104:
            return floor[0], floor[1], False
        k = span(u, 104, 107.4)  # 自己一跳一跳爬回去
        hop = abs(math.sin(k * math.pi * 3)) * 4 * (1 - k * 0.5)
        return lerp(floor[0], home[0], ease_in_out(k)), lerp(floor[1], home[1], ease_in_out(k)) - hop, False

    def cable(self, g: Gfx, px: float, py: float, upto: float = 1.0):
        end = (px, py + 2)
        mid = ((self.CABLE0[0] + end[0]) / 2, 66)
        pts = [bezier(self.CABLE0, mid, end, k / 20 * upto) for k in range(21)]
        g.d.line(pts, fill=1)
        return pts

    def socket(self, g: Gfx):
        x, y = self.SOCK
        g.d.rounded_rectangle((x, y, x + 12, y + 13), radius=3, outline=1, fill=0)
        g.d.line((x + 4, y + 4, x + 4, y + 8), fill=1)
        g.d.line((x + 8, y + 4, x + 8, y + 8), fill=1)
        g.d.line((x + 6, y + 10, x + 6, y + 11), fill=1)
        g.d.line((126, 0, 126, 63), fill=1)  # 墙角
        for yy in range(2, 64, 6):
            g.px(127, yy)

    def cushion(self, g: Gfx):
        g.d.ellipse((self.SX - 3, 56, self.SX + SAGE_W + 2, 63), fill=0, outline=1)

    def battery(self, g: Gfx, level: float, charging: bool, t: float, s: float = 1.0):
        cx, cy = 99, 13
        w, h = 38 * s, 18 * s
        if s <= 0.2:
            return
        x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        g.d.rounded_rectangle((x0, y0, x1, y1), radius=max(1, int(3 * s)), outline=1, fill=0)
        g.d.rectangle((x1 + 1, cy - 4 * s, x1 + 1 + 2 * s, cy + 4 * s), fill=1)
        if s < 1:
            return
        fx = x0 + 3 + (w - 6) * level
        if level > 0.01:
            g.d.rectangle((x0 + 3, y0 + 3, fx, y1 - 3), fill=1)
            if charging:  # 流动的电：一道暗缝从左往右走
                k = (t * 0.7) % 1.0
                sx = x0 + 3 + (fx - x0 - 3) * k
                g.d.line((sx, y0 + 3, sx + 3, y1 - 3), fill=0)
        if level < 0.25 and not charging and blink(t, 1.0, 0.5):  # 低电量闪
            g.d.rectangle((x0 + 3, y0 + 3, x0 + 6, y1 - 3), fill=0)
        pct = f"{int(level * 100 + 0.5)}%"
        g.text(x1 + 3, y1 + 4, pct, size=8, align="right")
        if charging:
            g.blit(BOLT, x1 - 6 - len(pct) * 5 - 3, y1 + 4)

    def level(self, u: float) -> float:
        if u < 72:
            return (20 + 79 * (1 - (1 - min(u, 70) / 70) ** 2)) / 100
        if u < 76:
            return 0.99
        return lerp(0.99, 0.20, span(u, 76, 104))

    def lift(self, u: float, t: float) -> float:
        """浮空高度（像素）"""
        up = ease_in_out(span(u, 77, 79.5)) * (1 - ease_out_bounce(span(u, 101.5, 103.2)))
        return up * (6 + math.sin(t * 1.6) * 1.5)

    def mx_battery(self, g: Gfx, level: float, charging: bool, t: float):
        g.mx[1, 0:7] = True
        g.mx[6, 0:7] = True
        g.mx[1:7, 0] = True
        g.mx[1:7, 6] = True
        g.mx[3:5, 7] = True
        n = int(level * 5 + 0.5)
        for i in range(n):
            g.mx[2:6, 1 + i] = True
        if charging and n < 5:
            g.mx[2:6, 1 + n] = blink(t, 0.8)

    def scene(self, g: Gfx, u: float, t: float):
        lv = self.level(u)
        px, py, plugged = self.plug_pos(u)
        charging = plugged and (u < 72 or u > 107.4)
        lift = self.lift(u, t)
        self.socket(g)
        self.cushion(g)
        if lift > 0.5:  # 浮空：坐垫上一圈影子
            for i in range(3):
                g.px(self.SX + 10 + i * 4 + int(t * 3) % 4, 54)
        pts = self.cable(g, px, py)
        g.blit(PLUG, px, py) if plugged else g.blit(PLUG.flip() if u > 104 else PLUG, px, py)
        if charging:  # 电流沿线往道士身上走
            for j in range(3):
                k = 1 - ((t * 0.6 + j / 3) % 1.0)
                x, y = pts[int(k * 20)]
                g.d.rectangle((x - 1, y - 1, x, y), fill=1)
            for j in range(4):  # 气从身上升起
                k = (t * 0.35 + j / 4) % 1.0
                x = self.SX + 4 + rand(j + int(t * 0.35 + j / 4) * 7, self.seed) * (SAGE_W - 8)
                if k < 0.8:
                    g.px(x + math.sin(k * 6 + j) * 1.5, self.SY + 18 - k * 26)
        eyes = "one" if 70.4 < u < 74.2 else "closed"
        sage(g, self.SX, self.SY - lift, eyes)
        if 74 <= u < 74.5:
            spark(g, self.SOCK[0] - 1, self.SOCK[1] + 7, span(u, 74, 74.5), seed=3)
        if 107.4 <= u < 108:
            spark(g, self.SOCK[0] - 1, self.SOCK[1] + 7, span(u, 107.4, 108), seed=4)
        self.battery(g, lv, charging, t)
        # 题字：持而盈之，不如其已（《道德经》第九章）
        if 72 < u < 98:
            a = 1 - span(u, 95, 98)
            n = int(clamp((u - 72) * 3 / 4) * 4 * a + 0.999)
            g.vtext(62, 3, "持而盈之"[:n])
            if u > 75.5:
                n = int(clamp((u - 75.5) * 3 / 4) * 4 * a + 0.999)
                g.vtext(48, 3, "不如其已"[:n])
        self.mx_battery(g, lv, charging, t)
        if 74 <= u < 74.3 or 107.4 <= u < 107.7:
            g.mx_level = 4

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.socket(g)
        self.cushion(g)
        drop = ease_out_bounce(span(t, 0, 0.9))
        sage(g, self.SX, lerp(-SAGE_H, self.SY, drop), "open" if t < 1.0 else "closed")
        home = self.plug_pos(0)
        k = ease_in_out(span(t, 0.9, 1.6))
        if k > 0:
            end = (lerp(self.CABLE0[0], home[0], k), lerp(self.CABLE0[1], home[1], k) - math.sin(k * math.pi) * 10)
            self.cable(g, end[0], end[1])
            g.blit(PLUG, *end)
        spark(g, self.SOCK[0] - 1, self.SOCK[1] + 7, span(t, 1.6, 2.0), seed=4)
        s = ease_out_back(span(t, 1.6, 2.2))
        lv = 0.20
        self.battery(g, lv, t > 2.2, t, s if t < 2.2 else 1.0)
        if t > 1.6:
            self.mx_battery(g, lv, True, t)
            g.mx_level = 4 if t < 1.8 else 1
        else:
            g.mx[7, :] = True
            g.mx[6, 1:7] = drop >= 1

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.scene(g, t % self.C, t)

    def exit(self, g: Gfx, t: float):
        u = self._ht % self.C
        lv = self.level(u)
        lift = self.lift(u, self._ht)
        self.socket(g)
        self.cushion(g)
        home = self.plug_pos(u)
        k = span(t, 0, 0.35)
        px, py = home[0] - 14 * ease_out(k), home[1] + 6 * ease_out_bounce(k) - math.sin(k * math.pi) * 6
        self.cable(g, px, py)
        g.blit(PLUG, px, py)
        up = ease_in(span(t, 0.3, 1.2))
        sage(g, self.SX, self.SY - lift - up * 70, "closed")
        self.battery(g, lv, False, t, 1 - ease_in(span(t, 0.1, 0.6)))
        g.fade(1 - span(t, 0.7, 1.2))
        if t < 0.6:
            self.mx_battery(g, lv, False, t)
        else:
            g.mx[7, :] = True


# ====================================================================== 散热

FC = (31, 32)        # 风扇中心
FLAME_ICON = Sprite("""
   #
  ##
 #.##
 #..#
#.#..#
#.##.#
 #..#
""")


@register
class Cooling(Rest):
    id = "x6.fan"
    name = "散热"
    desc = "法事后机箱滚烫，太极做轴的风扇呼呼转，温度曲线慢慢落下，凉透了扇叶就停——躁胜寒，静胜热"
    T = {"enter": 2.6, "exit": 1.2}
    BASE = 34.0          # 室温
    SPIKE = 47.0         # 杂念升温的间隔

    def setup(self):
        self.t0 = 92.0 if self.ctx.finished else 81.0
        self._ang = self.rng.random() * 6.28
        self._lt = None
        self._ht = 0.0

    # ------------------------------------------------------------ 温度：t 的纯函数

    def spike_at(self, k: int) -> float:
        return 24 + k * self.SPIKE + rand(k, self.seed) * 12

    def temp(self, t: float) -> float:
        T = self.BASE + (self.t0 - self.BASE) * math.exp(-t / 14)
        k = max(0, int((t - 24) // self.SPIKE))
        for j in range(max(0, k - 2), k + 1):
            s = self.spike_at(j)
            if t > s:
                amp = 22 + rand(j + 50, self.seed) * 18
                d = t - s
                T += amp * (span(d, 0, 2.5) if d < 2.5 else math.exp(-(d - 2.5) / 9))
        return T

    def rpm(self, T: float) -> float:
        """0..1：40℃ 以下停转"""
        return clamp((T - 40) / 40) ** 0.8

    def spin(self, t: float, w: float):
        """转角累积（有状态：每帧走 dt）"""
        if self._lt is None or not 0 <= t - self._lt <= 0.5:
            dt = 1 / 30
        else:
            dt = t - self._lt
        self._lt = t
        self._ang += w * 26 * dt
        return self._ang

    # ------------------------------------------------------------ 零件

    def frame(self, g: Gfx, x: float = 0):
        cx, cy = FC[0] + x, FC[1]
        g.d.rounded_rectangle((cx - 29, cy - 29, cx + 29, cy + 29), radius=6, outline=1, fill=0)
        g.d.ellipse((cx - 27, cy - 27, cx + 27, cy + 27), outline=1)
        for dx in (-23, 23):
            for dy in (-23, 23):
                g.d.ellipse((cx + dx - 2, cy + dy - 2, cx + dx + 2, cy + dy + 2), outline=1)

    def blades(self, g: Gfx, ang: float, w: float, x: float = 0):
        cx, cy = FC[0] + x, FC[1]
        n = 5
        for i in range(n):
            a = ang + i * 2 * math.pi / n
            pts = []
            for k in range(6):  # 前缘（弯）
                r = lerp(9, 25, k / 5)
                pts.append(self._bp(cx, cy, a + 0.7 * (k / 5) ** 0.8, r))
            for k in range(5, -1, -1):  # 后缘
                r = lerp(9, 25, k / 5)
                pts.append(self._bp(cx, cy, a + 0.7 * (k / 5) ** 0.8 + lerp(0.55, 0.62, k / 5), r))
            if w > 0.55:  # 转快了：只剩轮廓，后面拖残影弧
                g.d.polygon(pts, fill=0, outline=1)
                for k in (1, 3, 5):
                    r = lerp(9, 25, k / 5)
                    a1 = a + 0.7 * (k / 5) ** 0.8
                    g.d.arc((cx - r, cy - r, cx + r, cy + r), math.degrees(a1 - 0.25 - w * 0.5), math.degrees(a1 - 0.08),
                            fill=1)
            else:
                g.d.polygon(pts, fill=1, outline=1)
        taiji_hub(g, cx, cy, ang, 7)

    @staticmethod
    def _bp(cx, cy, a, r):
        return cx + math.cos(a) * r, cy + math.sin(a) * r

    def panel(self, g: Gfx, t: float, T: float, w: float, a: float = 1.0):
        """右侧：温度、曲线、经文"""
        if a <= 0:
            return
        x0 = 68
        num = f"{int(round(T))}"
        tw = g.text(x0, 4, num, size=8, scale=2)
        g.text(x0 + tw + 1, 3, "℃", size=12)
        if self.rising(t):
            g.blit(FLAME_ICON, 121, 5 + (int(t * 8) % 2))
        # 曲线：最近 56 秒
        gx0, gy0, gx1, gy1 = 68, 22, 125, 46
        g.d.rectangle((gx0, gy0, gx1, gy1), outline=1)
        for yy in range(gy0 + 4, gy1, 6):
            for xx in range(gx0 + 2, gx1, 4):
                g.px(xx, yy)
        prev = None
        for i in range(gx1 - gx0 - 3):
            tt = t - (gx1 - gx0 - 4 - i)
            if tt < 0:
                continue
            v = self.temp(tt)
            y = gy1 - 2 - clamp((v - 30) / 80) * (gy1 - gy0 - 4)
            p = (gx0 + 2 + i, y)
            if prev:
                g.d.line((prev, p), fill=1)
            prev = p
        # 躁胜寒，静胜热（《道德经》第四十五章）
        if self.rising(t):
            s = "躁胜寒"
        elif w > 0:
            s = "静胜热"
        else:
            s = "清静"
        g.text(97, 51, s, align="center")

    def rising(self, t: float) -> bool:
        k = max(0, int((t - 24) // self.SPIKE))
        return any(0 < t - self.spike_at(j) < 4 for j in (k - 1, k) if j >= 0)

    def mx_fan(self, g: Gfx, ang: float):
        for i in range(3):  # 三叶（四叶在 8×8 上像卍字，避开）
            a = ang + i * 2 * math.pi / 3
            for r in (1.6, 2.6, 3.6):
                aa = a + r * 0.3
                g.mx_set(math.floor(4 + math.cos(aa) * r), math.floor(4 + math.sin(aa) * r))
        g.mx[3:5, 3:5] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        s = ease_out_back(span(t, 0, 0.7))
        x = lerp(-70, 0, s)
        w = ease_in(span(t, 0.6, 2.6)) * self.rpm(self.t0)
        ang = self.spin(t, w)
        self.frame(g, x)
        self.blades(g, ang, w, x)
        T = lerp(self.BASE, self.t0, ease_out(span(t, 0.8, 2.4)))
        if t > 0.8:
            self.panel(g, 0, T, w)
            if t < 2.4 and blink(t, 0.3):  # 过热警告闪
                g.invert((66, 2, 104, 20))
        self.mx_fan(g, ang)
        g.mx_level = 1 + int(3 * span(t, 0.6, 2.6))

    def hold(self, g: Gfx, t: float):
        self._ht = t
        T = self.temp(t)
        w = self.rpm(T)
        ang = self.spin(t, w)
        self.frame(g)
        self.blades(g, ang, w)
        if w <= 0:  # 停了：一粒灰尘慢慢落在扇叶上
            k = (t * 0.15) % 1.0
            g.px(FC[0] + 14 + math.sin(t) * 2, lerp(-2, 20, ease_out(k)))
        self.panel(g, t, T, w)
        self.mx_fan(g, ang)
        g.mx_level = 1 + int(w * 3)

    def exit(self, g: Gfx, t: float):
        T = self.temp(self._ht)
        w = lerp(self.rpm(T), 1.0, span(t, 0, 0.5))
        ang = self.spin(self._ht + t, w)
        x = -90 * ease_in(span(t, 0.4, 1.2))
        self.frame(g, x)
        self.blades(g, ang, w, x)
        self.panel(g, self._ht, T, w)
        g.fade(1 - span(t, 0.5, 1.2), (60, 0, 128, 64))
        self.mx_fan(g, ang)


def taiji_hub(g: Gfx, cx: float, cy: float, ang: float, r: int = 6):
    """风扇轴心的小太极（随扇叶转）：不用整屏数组，逐点画"""
    c, s = math.cos(-ang), math.sin(-ang)
    g.d.ellipse((cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1), fill=0, outline=1)
    icx, icy = int(round(cx)), int(round(cy))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r:
                continue
            u, v = dx * c - dy * s, dx * s + dy * c
            up = u * u + (v + r / 2) ** 2 <= (r / 2) ** 2
            lo = u * u + (v - r / 2) ** 2 <= (r / 2) ** 2
            white = (u > 0 and not lo) or up
            if u * u + (v + r / 2) ** 2 <= 1.2:
                white = False
            if u * u + (v - r / 2) ** 2 <= 1.2:
                white = True
            if white:
                g.img.putpixel((icx + dx, icy + dy), 1) if 0 <= icx + dx < 128 and 0 <= icy + dy < 64 else None


# ====================================================================== 待机

MOTH = (Sprite("""
#.#
.#.
"""), Sprite("""
...
###
"""))
MOON_ICON = Sprite("""
 .###
.##.
##.
##.
##.
.##.
 .###
""")
BREATH = 7.0         # 一息（秒）：吸 3、呼 4


def breath(t: float) -> float:
    """0..1：吸气升、呼气落（不对称）"""
    k = t % BREATH
    return ease_in_out(k / 3.0) if k < 3.0 else 1 - ease_in_out((k - 3.0) / 4.0)


@register
class Standby(Rest):
    id = "x6.standby"
    name = "待机"
    desc = "笔记本合上盖子进入睡眠，前沿的呼吸灯一明一暗，吐故纳新；偶尔盖子掀开一条缝偷看，飞蛾绕灯"
    T = {"enter": 3.0, "exit": 1.3}
    EV = 31.0

    LED = (93, 47)

    def setup(self):
        self._ht = 0.0
        self.stars = [(int(4 + self.rng.random() * 70), int(2 + self.rng.random() * 18)) for _ in range(9)]

    # ------------------------------------------------------------ 零件

    def laptop(self, g: Gfx, c: float, screen: float = 0.0, text: str = "", play: bool = False):
        """c = 合盖程度（0 全开，1 合上）；screen = 屏幕亮度；play：屏上是 ▶（醒来）而不是 ‖（暂停）"""
        # 底座：键盘面（打开时看得见）+ 前沿
        base = [(30, 30), (98, 30), (110, 44), (18, 44)]
        g.d.polygon(base, fill=0, outline=1)
        if c < 0.8:
            for r in range(3):
                y = 34 + r * 3
                for k in range(11):
                    x = lerp(28, 100, (k + 0.5) / 11) + (y - 30) * 0.0
                    xx = lerp(lerp(30, 18, (y - 30) / 14), lerp(98, 110, (y - 30) / 14), (k + 0.5) / 11)
                    g.d.line((xx - 1, y, xx + 2, y), fill=1)
            g.d.rectangle((54, 42, 72, 43), outline=1)
        g.d.rectangle((18, 44, 110, 50), fill=0, outline=1)
        g.d.line((20, 51, 108, 51), fill=1)
        # 盖子：铰链在后沿 y=30，远端从竖直（y≈-6）转到合上（前沿 y=44）
        a = c * math.pi / 2
        fy = 30 - math.cos(a) * 26 + math.sin(a) * 14
        sp = math.sin(a)
        lid = [(30, 30), (98, 30), (lerp(100, 110, sp), fy), (lerp(28, 18, sp), fy)]
        g.d.polygon(lid, fill=0, outline=1)
        if c < 0.6:  # 屏幕（还亮着：刚才的法事名 + 暂停号）
            x0, x1 = lid[3][0] + 4, lid[2][0] - 4
            y0, y1 = fy + 3, 27
            if y1 > y0 + 4:
                g.d.rectangle((x0, y0, x1, y1), outline=1)
                if screen > 0 and text:
                    cy = (y0 + y1) / 2
                    w = g.text((x0 + x1) / 2 - 4, cy - 5, text, align="center")
                    bx = (x0 + x1) / 2 - 4 + w / 2 + 4
                    if play:
                        g.d.polygon([(bx, cy - 4), (bx, cy + 4), (bx + 5, cy)], fill=1)
                    else:
                        g.d.rectangle((bx, cy - 4, bx + 1, cy + 4), fill=1)
                        g.d.rectangle((bx + 4, cy - 4, bx + 5, cy + 4), fill=1)
                    if screen < 1:
                        g.fade(screen, (int(x0) + 1, int(y0) + 1, int(x1), int(y1)))
        elif c >= 0.97:  # 合上：盖上贴一张“道”字贴纸
            g.d.rounded_rectangle((70, 33, 81, 41), radius=2, outline=1, fill=0)
            g.text(72, 34, "道", size=8)
        return fy

    def glow(self, g: Gfx, b: float):
        """呼吸灯：灯点 + 桌面上一圈抖动的光晕"""
        x, y = self.LED
        if b > 0.12:
            g.d.rectangle((x - 1, y, x + 1, y), fill=1)
        if b > 0.5:
            g.d.rectangle((x - 2, y - 1, x + 2, y + 1), fill=1)
            g.d.line((x - 1, y, x + 1, y), fill=0)
            g.px(x, y)
        rx, ry = 4 + b * 16, 1 + b * 3
        lv = b * 0.6
        from ..engine.gfx import BAYER4
        for yy in range(53, int(53 + ry * 2) + 1):
            for xx in range(int(x - rx), int(x + rx) + 1):
                d = ((xx - x) / rx) ** 2 + ((yy - 53) / (ry * 2)) ** 2
                if d < 1 and BAYER4[yy % 4, xx % 4] < lv * (1 - d) * 16:
                    g.px(xx, yy)

    def zz(self, g: Gfx, t: float):
        for j in range(3):
            k = ((t + j * BREATH) % (3 * BREATH)) / (3 * BREATH)
            if k > 0.85:
                continue
            x = 100 + k * 18 + math.sin(k * 8 + j) * 2
            y = 30 - k * 26
            g.text(x, y, "z" if k < 0.4 else "Z", size=8)

    def mx_breath(self, g: Gfx, b: float):
        r = 0.8 + b * 3.2
        for y in range(8):
            for x in range(8):
                if math.hypot(x - 3.5, y - 3.5) <= r:
                    g.mx[y, x] = True
        g.mx_level = 1 if b < 0.8 else 2

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        c = ease_in(span(t, 0.6, 1.6))
        if t > 1.6:  # 合上弹一下
            c = 1 - 0.06 * abs(math.sin(span(t, 1.6, 2.0) * math.pi)) * (1 - span(t, 1.6, 2.0))
        name = self.ctx.ritual_name or "法事"
        self.laptop(g, c, screen=1 - span(t, 0.2, 0.9), text=name)
        if 1.6 < t < 1.9:
            for j in range(6):
                k = span(t, 1.6, 1.9)
                g.px(18 - k * 8 - j, 44 - j % 3 + k * 4)
                g.px(110 + k * 8 + j, 44 - j % 3 + k * 4)
        b = breath(t - 2.0 + 0.0) if t > 2.0 else 0
        if t > 2.0:
            self.glow(g, ease_in_out(span(t, 2.0, 3.0)))
            g.blit(MOON_ICON, 117, 2)
        g.d.line((0, 52, 127, 52), fill=1)
        if t > 2.0:
            self.mx_breath(g, ease_in_out(span(t, 2.0, 3.0)))
        else:
            g.mx[7, :] = True
            g.mx[6, 1:7] = c > 0.5
        _ = b

    def hold(self, g: Gfx, t: float):
        self._ht = t
        b = breath(t + 1.0)  # enter 末尾 b=1 → 从吸满开始
        n = int(t // self.EV)
        k = t - n * self.EV
        kind = int(rand(n, self.seed) * 3) if n > 0 else 2
        quote = kind == 2 and 2 < k < 16
        for i, (x, y) in enumerate(self.stars):
            if quote and x < 58 and y < 18:
                continue
            if noise(t * 0.5 + i * 3.1, self.seed + i) > 0.3:
                g.px(x, y)
        g.blit(MOON_ICON, 117, 2)
        c = 1.0
        if kind == 0 and 4 < k < 12:  # 盖子掀开一条缝，偷看
            o = ease_out(span(k, 4, 5)) * (1 - ease_in(span(k, 10.6, 11.0)))
            c = 1 - o * 0.15
        fy = self.laptop(g, c)
        if c < 1:
            if 5 < k < 10.6:  # 缝里两只眼睛左右看
                look = -2 if k < 7 else 2 if k < 9 else 0
                blinking = 8.0 < k < 8.15
                for ex in (58, 68):
                    if not blinking:
                        g.d.rectangle((ex + look, fy + 2, ex + look + 1, fy + 3), fill=1)
        g.d.line((0, 52, 127, 52), fill=1)
        self.glow(g, b)
        if kind == 1 and 3 < k < 15:  # 飞蛾扑灯
            p = span(k, 3, 15)
            if p < 0.25:
                q = ease_out(p / 0.25)
                mx_, my_ = lerp(-4, self.LED[0], q), lerp(10, self.LED[1] - 10, q)
            elif p < 0.8:
                a = (p - 0.25) / 0.55 * 4 * math.pi
                mx_, my_ = self.LED[0] + math.cos(a) * 9, self.LED[1] - 7 + math.sin(a) * 4
            else:
                q = ease_in((p - 0.8) / 0.2)
                mx_, my_ = lerp(self.LED[0] + 9, 140, q), lerp(self.LED[1] - 7, -10, q)
            g.blit(MOTH[int(t * 12) % 2], mx_, my_)
        if quote:  # 吹呴呼吸，吐故纳新（《庄子·刻意》）
            a = 1 - span(k, 14, 16)
            typewriter(g, 6, 4, "吐故纳新", (k - 2) * a, cps=2)
        else:
            self.zz(g, t)
        self.mx_breath(g, b)

    def exit(self, g: Gfx, t: float):
        c = 1 - ease_out(span(t, 0, 0.7))
        g.d.line((0, 52, 127, 52), fill=1)
        self.laptop(g, c, screen=span(t, 0.3, 0.7), text=self.ctx.ritual_name or "法事", play=True)
        g.fade(1 - span(t, 0.8, 1.3))
        r = ease_out(span(t, 0, 0.8)) * 6
        for y in range(8):
            for x in range(8):
                if math.hypot(x - 3.5, y - 3.5) <= r:
                    g.mx[y, x] = True
        g.mx_level = 1 + int(3 * span(t, 0.2, 0.8))
