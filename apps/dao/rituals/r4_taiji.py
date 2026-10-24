"""太极拳：湖边石台上，小道士打太极拳，身后一张点画的太极图缓缓转，手过处留下行云流水的轨迹。

依据：太极拳（杨式 / 二十四式）的起势、野马分鬃、白鹤亮翅、搂膝拗步、云手、单鞭、收势；
王宗岳《太极拳论》“太极者，无极而生，动静之机，阴阳之母也”。
入场：身后太极图的外圈一笔画出，小道士走上石台并步站立，“起势”（两臂前平举、屈膝按掌）。
持续：一遍五式（每式 120 秒），动作按 e 推进：野马分鬃左右交替、白鹤亮翅虚步上挑、搂膝拗步弓步推掌、
      云手横着走云步、单鞭勾手推掌。前手过去 1 秒的轨迹连成渐隐的点线；湖面波纹、远处小亭；
      每隔一阵一尾鱼跃出水面、或一片落叶在水上打转。续：收势、起势，左上“第几遍”加一。
中断：两臂缓缓落下，轨迹消散，“收势”。  恢复：起势，接回当前动作。
圆满：收势，太极图越转越快、收拢成一张实心太极图悬在头顶，闪白，“动静之机”。
点阵：旋转的太极。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import mx_taiji, taiji
from .r4_kit import P, Clock, cached, counter, dao, hand_pos, label, mix, pop_title, ring, seq, star

FLOOR = 56
DX = 46
FORM = 120.0
TJ = (DX, 30, 22)          # 背后太极图：中心、半径

N = P()
HOLD_DT = P(b=(120, 20, "palm"), f=(60, 160, "palm"))
BALL = P(legs="empty", b=(110, 10, "palm"), f=(20, 170, "down"))      # 抱球：上手按、下手托
QISHI = [(0, N), (1.2, P(b=(30, 10, "down"), f=(20, 0, "down"))),
         (2.4, P(legs="wide", b=(60, 30, "down"), f=(50, 20, "down"))), (3.2, P(legs="wide", b=(70, 40, "down"), f=(60, 30, "down")))]

YEMA = P(legs="bow", b=(120, 110, "down"), f=(-25, -35, "palm"))
BAIHE = P(legs="empty", b=(110, 95, "down"), f=(-60, -85, "palm"))
LOUXI = P(legs="bow", lean=6, b=(110, 100, "down"), f=(0, -5, "up"))
YUN_A = P(legs="wide", b=(120, 40, "palm"), f=(30, -100, "palm"))
YUN_B = P(legs="step", b=(140, -80, "palm"), f=(60, 150, "palm"))
DANBIAN = P(legs="bow", b=(180, 170, "hook"), f=(0, -10, "up"))

FORMS = [
    ("野马分鬃", [(0, BALL), (2.0, YEMA), (3.2, YEMA), (5.0, BALL)], True),
    ("白鹤亮翅", [(0, BALL), (2.0, BAIHE), (3.4, BAIHE), (5.0, BALL)], False),
    ("搂膝拗步", [(0, BALL), (2.2, LOUXI), (3.4, LOUXI), (5.4, BALL)], True),
    ("云手", [(0, YUN_A), (2.5, YUN_B), (5.0, YUN_A)], False),
    ("单鞭", [(0, BALL), (2.4, DANBIAN), (4.0, DANBIAN), (6.0, BALL)], False),
]


def _pavilion():
    """湖对岸的小亭 26×20：攒尖顶、翘角、宝顶、两根柱、栏杆"""
    p = Part(26, 20)
    p.shape("line", (12, 0, 12, 2), fill=1)
    p.shape("polygon", [(12, 2), (14, 2), (22, 8), (25, 7), (24, 9), (2, 9), (1, 7), (4, 8)], fill=1)
    p.d.line((5, 7, 21, 7), fill=0)
    p.dither([(14, 3), (22, 8), (14, 8)], 0.5, 0)
    p.shape("rectangle", (3, 9, 23, 10), fill=1)
    for x in (5, 20):
        p.shape("rectangle", (x, 10, x + 1, 19), fill=1)
    p.d.line((5, 15, 21, 15), fill=1)
    for x in range(8, 19, 3):
        p.d.line((x, 15, x, 18), fill=1)
    p.shape("rectangle", (2, 19, 24, 19), fill=1)
    return p.sprite()


FISH = pix.frames("""
 ##  #
####.#
 ##  #
---
  #
 ###
#####
 ###
  .
 # #
""")


def scenery(g: Gfx, t: float, e: float):
    """湖光：远山、对岸小亭、湖面波纹、石台"""
    for x in range(0, 128, 2):
        y = 30 - 5 * math.sin(x * 0.04 + 2.0) - 2 * math.sin(x * 0.15)
        g.px(x, y)
    pix.blit(g, cached(("tj", "pav"), _pavilion), 96, 21)
    g.d.line((0, 41, 127, 41), fill=1)                       # 湖岸
    for r, y in enumerate((44, 47, 51)):                     # 波纹（随时间平移，稀疏）
        off = int(t * (3 - r)) % 24
        for x in range(-24 + off + r * 9, 128, 24):
            g.d.line((x, y, x + 2 + r, y), fill=1)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)                 # 石台
    g.d.line((0, FLOOR + 1, 127, FLOOR + 1), fill=0)
    for x in range(4, 128, 16):
        g.d.line((x, FLOOR + 2, x, 63), fill=1)
    pix.checker(g, (0, FLOOR + 2, 128, 64), 0.125)
    # 小事件：鱼跃 / 落叶打转（按 e）
    slot, ph = int(e // 21), (e % 21) / 2.0
    if ph < 1:
        fx = 70 + (slot * 37) % 50
        if slot % 2 == 0:
            y = 46 - math.sin(ph * math.pi) * 12
            pix.blit(g, FISH[0 if ph < 0.5 else 1], fx + ph * 10, y)
            if ph < 0.12 or ph > 0.88:
                ring(g, fx + 3 + ph * 10, 47, 2 + (ph % 0.12) * 20, dotted=2, ry=1)
        else:
            ring(g, fx, 47, 1 + ph * 6, dotted=2, ry=(1 + ph * 6) * 0.3)
            g.px(fx + math.cos(ph * 12) * 2, 46)


def taiji_bg(g: Gfx, t: float, draw: float = 1.0, speed: float = 0.2):
    """身后点画的太极图：外圈 + S 中线 + 两个鱼眼，缓缓转"""
    cx, cy, r = TJ
    a0 = t * speed
    n = 64
    for i in range(int(n * draw)):
        if i % 2 == 0:
            a = a0 + i / n * 2 * math.pi
            g.px(cx + math.cos(a) * r, cy + math.sin(a) * r)
    if draw >= 1:
        for i in range(0, 24, 2):  # S 中线：两个半圆
            k = i / 24
            a = a0 + k * math.pi
            for s in (1, -1):
                ox, oy = cx + s * math.cos(a0) * r / 2, cy + s * math.sin(a0) * r / 2
                g.px(ox + math.cos(a + (0 if s > 0 else math.pi)) * r / 2,
                     oy + math.sin(a + (0 if s > 0 else math.pi)) * r / 2)
        for s in (1, -1):
            g.px(cx + s * math.cos(a0) * r / 2, cy + s * math.sin(a0) * r / 2)


@register
class Taiji(Ritual):
    id = "r4.taiji"
    name = "太极拳"
    desc = "湖边石台上小道士打太极拳，身后点画太极图缓缓转，手过处留下行云流水的轨迹；野马分鬃、白鹤亮翅、云手、单鞭"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 2.2, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()

    def at(self, k: float):
        i = min(int(k // FORM), 4)
        u = k - i * FORM
        name, keys, alt = FORMS[i]
        L = keys[-1][0]
        flip = alt and int(u // L) % 2 == 1
        x = DX
        if i == 3:  # 云手：横着走云步
            x = DX + math.sin(u / (L * 2) * 2 * math.pi) * 8
        return i, u, keys, L, flip, x

    def pose(self, k: float):
        i, u, keys, L, flip, x = self.at(k)
        return seq(keys, u % L), flip, x

    def trail(self, g: Gfx, k: float, fade: float = 1.0):
        """前手过去 1.2 秒的轨迹：越旧越稀"""
        pts = []
        for j in range(1, 25):
            kk = k - j * 0.05
            if kk < 0:
                break
            p, fl, x = self.pose(kk)
            pts.append(hand_pos(x, FLOOR, p, fl)["hf"])
        for j, (px, py) in enumerate(pts):
            if j / len(pts) < fade and (j < 8 or j % 2 == 0):
                g.px(px, py)

    def draw(self, g: Gfx, t: float, e: float, k: float, pose=None, trail=1.0):
        p, fl, x = self.pose(k)
        if pose is not None:
            p = pose
        taiji_bg(g, t)
        h = dao(g, x, FLOOR, p, t, flip=fl)
        if trail > 0:
            self.trail(g, k, trail)
        return h

    def texts(self, g: Gfx, e: float, i: int, u: float):
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")
        if u < 8.0:
            label(g, 124, 3, FORMS[i][0], 12, "right", box=True)

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        scenery(g, t, 5.0)
        taiji_bg(g, t, min(1.0, t / 2.0))
        if t < 2.6:
            daoshi(g, lerp(-12, DX, ease_out(span(t, 0.4, 2.6))), FLOOR, "walk", t)
        else:
            dao(g, DX, FLOOR, seq(QISHI, (t - 2.6), loop=False), t)
        if abs(t - 2.0) < dt:
            self.sparks.burst(TJ[0] + TJ[2], TJ[1], 10, 16, life=0.5, gravity=0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_taiji(g, t * 0.8)
        if t > 3.0:
            label(g, 124, 3, "起势", 12, "right", box=True)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        scenery(g, t, e)
        if e >= self.CYCLE and k < 6.0:  # 续：收势 → 起势
            taiji_bg(g, t, 1.0, 0.2 + 0.6 * math.sin(k / 6 * math.pi))
            if k < 2.5:
                dao(g, DX, FLOOR, seq([(0, N), (1.5, HOLD_DT), (2.5, HOLD_DT)], k, loop=False), t)
            else:
                dao(g, DX, FLOOR, seq(QISHI, (k - 2.5) * 3.2 / 3.5, loop=False), t)
            mx_taiji(g, t * 2)
            n = int(e // self.CYCLE) + 1
            pop_title(g, 64, 3, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍", span(k, 0.3, 0.7), t)
            return
        i, u, keys, L, flip, x = self.at(k)
        self.draw(g, t, e, k)
        mx_taiji(g, t * 0.8)
        self.texts(g, e, i, u)

    def interrupt(self, g: Gfx, t: float, e: float):
        self.clock(t)
        k = e % self.CYCLE
        scenery(g, t, e)
        p, fl, x = self.pose(k)
        q = ease_out(span(t, 0, 1.2))
        self.draw(g, t, e, k, pose=mix(p, HOLD_DT, q), trail=1 - q)
        mx_taiji(g, t * 0.8 * (1 - q))
        i = self.at(k)[0]
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")
        if t > 0.5:
            label(g, 124, 3, "收势", 12, "right", box=True)

    def resume(self, g: Gfx, t: float, e: float):
        self.clock(t)
        k = e % self.CYCLE
        scenery(g, t, e)
        p, fl, x = self.pose(k)
        if t < 1.2:
            taiji_bg(g, t)
            dao(g, DX, FLOOR, seq(QISHI, t * 3.2 / 1.2, loop=False), t)
        else:
            q = ease_in_out(span(t, 1.2, 2.2))
            taiji_bg(g, t)
            P0 = QISHI[-1][1]
            dao(g, lerp(DX, x, q), FLOOR, mix(P0, p, q), t, flip=fl and q > 0.5)
        mx_taiji(g, t * 0.8)
        i = self.at(k)[0]
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")
        label(g, 124, 3, "起势" if t < 1.2 else FORMS[i][0], 12, "right", box=True)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        scenery(g, t, e)
        cx, cy, r = TJ
        # 太极图越转越快、收拢到头顶
        q = ease_in_out(span(t, 1.0, 2.6))
        ang = t * (0.2 + 6 * span(t, 0.5, 2.0)) if t < 2.6 else 2.6 * 6.2 + (t - 2.6) * 0.6
        if t < 2.6:
            rr = lerp(r, 8, q)
            n = 48
            for i in range(n):
                if i % 2 == 0:
                    a = ang + i / n * 2 * math.pi
                    g.px(cx + math.cos(a) * rr, lerp(cy, 11, q) + math.sin(a) * rr)
        pose = seq([(0, N), (1.2, HOLD_DT), (6, HOLD_DT)], t, loop=False)
        if t > 2.6:
            pose = P(b=(120, 20, "palm"), f=(60, 160, "palm"), face="sleep" if t < 4.0 else "happy")
        dao(g, DX, FLOOR, pose, t)
        if t >= 2.6:
            g.d.ellipse((cx - 10, 1, cx + 10, 21), fill=0)
            taiji(g, cx, 11, 8, ang)
            for j in range(8):
                a = j * math.pi / 4 + t
                if (j + int(t * 6)) % 2:
                    g.px(cx + math.cos(a) * 12, 11 + math.sin(a) * 11)
        if abs(t - 2.6) < dt:
            pix.flash(g)
            self.sparks.burst(cx, 11, 24, 36, life=1.0, gravity=10)
        if 2.6 < t < 2.9:
            pix.shake(g, t, 1.2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_taiji(g, ang)
        if t > 2.6:
            g.mx_level = 1 + int(6 * (1 - span(t, 2.6, 4.0)))
        if t > 3.2:
            pop_title(g, 98, 4, "动静之机", span(t, 3.2, 3.6), t)
