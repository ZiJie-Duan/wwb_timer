"""化宝：金炉（焚化炉）里火正旺，一只手从一堆元宝里拿起一锭抛进炉口，火一窜，火星与纸灰从炉顶飘出。

依据：宫观设“金炉”“化宝炉”专焚金银纸、元宝、疏文；“填还受生”科仪焚化受生钱以填还本命天库。

入场：金炉从下升起，炉门里的火“轰”地点着；左边一堆元宝一锭锭落下码好。
持续：一轮 600 秒十锭，每 50 秒一只手从左上伸到元宝堆，拿起最上一锭，抛物线抛进炉口；
      落进去时火苗一窜、点阵一亮，炉顶冒出火星与纸灰。元宝堆随 e 变少。
      一轮结束：一锭锭新元宝从天而降、弹跳着码回一堆，右侧“第几炉”加一。
中断：两扇炉门合上，只剩门缝里一线火光，“封炉”。
恢复：炉门打开，火一窜。
圆满：剩下的元宝一锭接一锭飞进炉里，大火冲天，火星喷涌，“填还受生”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, \
    rand, span
from ..engine.cn import cn_num
from ..engine.fx import flame
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r1_common import sleeve, sparkles, vreveal

INGOT = Sprite("""
    .###.
 #..#####..#
##.........##
.###########.
 .#########.
   .#####.
""")
FX = 74                      # 金炉中心
MOUTH = (FX, 47)             # 炉口中心
N = 10
STEP = 50.0
FIRST = 8.0
RENEW = 5.0
# 元宝堆：底四、三、二、一（从顶往下拿）；(x, y) = 元宝左上角 + (0, 4)
PILE = ([(0 + i * 12, 61) for i in range(4)] + [(6 + i * 12, 56) for i in range(3)] + [(12 + i * 12, 51) for i in range(2)]
        + [(18, 46)])


def furnace(g: Gfx):
    """金炉：须弥座、炉身、拱形炉口、两重檐、葫芦顶"""
    d = g.d
    d.rectangle((FX - 24, 59, FX + 24, 63), fill=0, outline=1)       # 座
    d.line((FX - 22, 61, FX + 22, 61), fill=1)
    d.rectangle((FX - 19, 28, FX + 19, 58), fill=0, outline=1)       # 炉身
    d.line((FX - 17, 30, FX - 17, 57), fill=1)
    d.line((FX + 17, 30, FX + 17, 57), fill=1)
    # 拱形炉口
    d.rectangle((FX - 10, 42, FX + 10, 58), fill=0, outline=1)
    d.pieslice((FX - 10, 34, FX + 10, 50), 180, 360, fill=0, outline=1)
    d.line((FX - 9, 42, FX + 9, 42), fill=0)
    # 匾“金炉”
    d.rectangle((FX - 9, 30, FX + 9, 38), fill=1)
    g.text(FX, 31, "金炉", size=8, fill=0, align="center")
    # 两重檐（翘角）
    d.polygon([(FX - 27, 27), (FX + 27, 27), (FX + 19, 20), (FX - 19, 20)], fill=0, outline=1)
    d.line((FX - 27, 27, FX - 30, 23), fill=1)
    d.line((FX + 27, 27, FX + 30, 23), fill=1)
    for x in range(FX - 22, FX + 23, 4):
        d.line((x, 21, x - 2, 26), fill=1)
    d.rectangle((FX - 13, 14, FX + 13, 19), fill=0, outline=1)
    d.polygon([(FX - 18, 14), (FX + 18, 14), (FX + 11, 9), (FX - 11, 9)], fill=0, outline=1)
    d.line((FX - 18, 14, FX - 20, 11), fill=1)
    d.line((FX + 18, 14, FX + 20, 11), fill=1)
    for x in (-8, -3, 2, 7):  # 烟窗
        d.rectangle((FX + x, 15, FX + x + 2, 18), fill=1)
    d.ellipse((FX - 3, 4, FX + 3, 9), fill=0, outline=1)             # 葫芦顶
    d.ellipse((FX - 2, 1, FX + 2, 5), fill=0, outline=1)


def doors(g: Gfx, door: float):
    """两扇炉门：door 0 = 开，1 = 关"""
    d = g.d
    if door > 0:
        w = 10 * door
        d.rectangle((FX - 10, 42, FX - 10 + w, 58), fill=0, outline=1)
        d.rectangle((FX + 10 - w, 42, FX + 10, 58), fill=0, outline=1)
        for yy in (46, 51, 56):  # 门钉
            for xx in (FX - 10 + w * 0.5, FX + 10 - w * 0.5):
                g.px(xx, yy)


def fire(g: Gfx, t: float, seed: int, boost: float = 0.0, door: float = 0.0):
    """炉口里的火：几条火舌，boost 时窜高"""
    if door >= 1:
        return
    for i, dx in enumerate((-5, 0, 5)):
        h = 9 + 4 * noise(t * 3 + i, seed) + boost * (10 + i * 2)
        flame(g, FX + dx, 58, 6, h, t + i * 0.4, seed + i)
    furnace_mouth_frame(g)


@register
class BurnTreasure(Ritual):
    id = "r1.joss"
    name = "化宝"
    desc = "金炉火旺，手从元宝堆拿一锭抛进炉口，火窜星飞；元宝化尽，新的一堆从天而降"
    T = {"enter": 3.8, "interrupt": 1.4, "resume": 1.4, "complete": 5.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 状态

    def left(self, k: float) -> int:
        """堆里还剩几锭"""
        thrown = 0 if k < FIRST else min(N, int((k - FIRST) // STEP) + 1)
        return N - thrown

    def toss(self, k: float):
        """→ (第几锭, 抛出后秒数) 或 None。抓起 0-0.6，飞 0.6-1.4，落进炉 1.4"""
        if k < FIRST - 1.0:
            return None
        j = int((k - FIRST + 1.0) // STEP)
        u = k - (FIRST + j * STEP) + 1.0
        if j < N and 0 <= u < 4.5:
            return j, u
        return None

    # ------------------------------------------------------------ 零件

    def pile(self, g: Gfx, n: int, drop=None):
        for i in range(n):
            x, y = PILE[i]
            dy = 0 if drop is None else drop(i)
            if dy < -70:
                continue
            g.blit(INGOT, x, y - 5 + dy)

    def sparks(self, g: Gfx, t: float, n: int = 6, power: float = 1.0):
        """炉顶飘出的火星与纸灰"""
        for j in range(n):
            ph = (t * (0.5 + 0.3 * rand(j, 3)) + rand(j, 4)) % 1.0
            x = FX + (rand(j, 5) - 0.5) * 10 + math.sin(ph * 6 + j) * 4 * power + ph * 10
            y = 4 - ph * 30 * power
            if y > -1 and ph < 0.15 * (1 + power):
                g.px(x, y + 3)
                if j % 2:
                    g.px(x + 1, y + 3)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        vreveal(g, 114, 4, right if right is not None else f"第{cn_num(n)}炉", a)

    def toss_draw(self, g: Gfx, j: int, u: float, t: float):
        """抓起、抛进炉；返回窜火强度"""
        idx = N - 1 - j                      # 从堆顶拿
        px, py = PILE[idx]
        boost = 0.0
        if u < 0.6:  # 手伸来抓
            p = ease_out(span(u, 0, 0.6))
            hx, hy = lerp(-30, px + 6, p), lerp(-10, py - 10, p)
            sleeve(g, hx, hy, math.pi + 0.7)
            if u > 0.45:
                g.blit(INGOT, px, py - 5 - (u - 0.45) * 20)
        elif u < 1.4:  # 抛物线飞进炉口
            q = (u - 0.6) / 0.8
            x0, y0 = px + 6, py - 8
            x1, y1 = MOUTH
            x = lerp(x0, x1, q)
            y = lerp(y0, y1, q) - math.sin(q * math.pi) * 22
            g.blit(INGOT, x - 6, y - 3)
            p = 1 - ease_in(span(u, 0.6, 1.2))
            sleeve(g, lerp(-30, px + 6, p), lerp(-10, py - 14, p), math.pi + 0.7, fist=False)
        if 1.4 <= u < 4.5:
            boost = ease_out(span(u, 1.4, 1.6)) * (1 - ease_in(span(u, 1.8, 3.2)))
        return boost

    def mx(self, g: Gfx, t: float, boost: float, door: float = 0.0):
        g.mx_rows([0, 0, 0, 0, 0, 0, 0b01111110, 0b11111111])
        if door >= 1:
            g.mx[5, 3:5] = blink(t, 1.2, 0.8)
            return
        h = 3 + boost * 3
        for x in range(1, 7):
            hh = int(h * (0.5 + noise(t * 4 + x * 1.7, self.seed)))
            for y in range(6 - hh, 6):
                g.mx_set(x, y)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        g_y = lerp(64, 0, ease_out_back(span(t, 0, 1.0)))
        if t < 1.0:
            # 炉从下面升起：先画好再整体下移（用一块黑盖住，省一次整屏运算）
            furnace(g)
            a = g.array()
            import numpy as np
            shift = int(round(g_y))
            if shift > 0:
                b = np.zeros_like(a)
                b[shift:, :] = a[:64 - shift, :]
                g.put(b)
        else:
            furnace(g)
            if t > 1.1:
                fire(g, t, self.seed, boost=0.6 * (1 - span(t, 1.5, 2.2)))
        self.pile(g, N, drop=lambda i: -80 * (1 - ease_out_bounce(span(t, 1.4 + i * 0.12, 1.9 + i * 0.12))))
        self.texts(g, 0, a=span(t, 2.8, 3.6))
        self.mx(g, t, 0.0, door=0 if t > 1.1 else 1)
        if t < 1.1:
            g.mx[:5, :] = False

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        n = self.left(k)
        tos = self.toss(k)
        boost = 0.0
        furnace(g)
        lifted = 1 if tos and 0.45 <= tos[1] < 1.0 else 0  # 已拿在手上、还没算进“抛出”
        self.pile(g, n - lifted)
        if tos:
            boost = self.toss_draw(g, tos[0], tos[1], t)
        fire(g, t, self.seed, boost=boost)
        self.sparks(g, t, n=6 + int(boost * 10), power=1 + boost)
        self.texts(g, e)
        self.mx(g, t, boost)
        if tos and 1.4 <= tos[1] < 1.55:
            g.mx_level = 5

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """新元宝从天而降，弹跳着码成一堆"""
        furnace(g)
        fire(g, t, self.seed)
        self.pile(g, N, drop=lambda i: -80 * (1 - ease_out_bounce(span(k, 0.6 + i * 0.25, 1.3 + i * 0.25))))
        self.sparks(g, t)
        self.texts(g, e if k > 1.5 else e - k - 1)
        self.mx(g, t, 0)
        landed = sum(1 for i in range(N) if k > 1.3 + i * 0.25)
        g.mx[0, :] = False
        if landed < N and blink(t, 0.2):
            g.mx_set(int(rand(int(k * 4), 3) * 8), 0)

    def interrupt(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        door = ease_out_bounce(span(t, 0.1, 1.0))
        furnace(g)
        fire(g, t, self.seed, door=door)
        doors(g, door)
        if door >= 1:
            g.d.line((FX, 43, FX, 57), fill=0)
            if blink(t, 0.3, 0.7):
                for y in range(44, 58, 2):
                    g.px(FX, y)
        self.pile(g, self.left(k))
        self.texts(g, e, right="封炉" if t > 0.7 else None)
        self.mx(g, t, 0, door=1 if door >= 1 else 0)

    def resume(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        door = 1 - ease_in_out(span(t, 0.1, 0.7))
        boost = ease_out(span(t, 0.6, 0.8)) * (1 - span(t, 0.8, 1.4))
        furnace(g)
        fire(g, t, self.seed, boost=boost, door=door)
        doors(g, door)
        self.pile(g, self.left(k))
        self.sparks(g, t, power=1 + boost)
        self.texts(g, e, right="封炉" if t < 0.4 else None)
        self.mx(g, t, boost, door=1 if door >= 0.95 else 0)

    def complete(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n = max(self.left(k), 4)
        # 剩下的一锭接一锭飞进炉
        furnace(g)
        flying = []
        for i in range(n):
            st = 0.2 + (n - 1 - i) * 0.22
            q = span(t, st, st + 0.6)
            if q <= 0:
                continue
            flying.append(i)
            if q < 1:
                x0, y0 = PILE[i][0] + 6, PILE[i][1] - 4
                x = lerp(x0, MOUTH[0], q)
                y = lerp(y0, MOUTH[1], q) - math.sin(q * math.pi) * 20
                g.blit(INGOT, x - 6, y - 3)
        self.pile(g, n, drop=lambda i: -999 if i in flying else 0)
        boost = ease_out(span(t, 0.8, 1.6)) * (1 - 0.5 * span(t, 4.0, 5.5))
        fire(g, t, self.seed, boost=boost * 1.4)
        self.sparks(g, t, n=6 + int(boost * 18), power=1 + boost * 1.5)
        if t > 1.6:
            sparkles(g, FX, 14, 50, 14, t, n=12, seed=self.seed)
            g.d.rectangle((0, 0, 42, 13), fill=0)
            s = "填还受生"
            m = int(clamp((t - 2.2) * 4 / len(s)) * len(s))
            g.text(2, 1, s[:m])
        else:
            self.texts(g, e, a=1 - span(t, 0.2, 1.0))
        self.mx(g, t, boost)
        if 0.8 < t < 2.0:
            g.mx_level = 3 + int(3 * blink(t, 0.2))


def furnace_mouth_frame(g: Gfx):
    """窜火时重描炉口边框（火在框上面会盖住框）"""
    d = g.d
    d.line((FX - 10, 42, FX - 10, 58), fill=1)
    d.line((FX + 10, 42, FX + 10, 58), fill=1)
    d.arc((FX - 10, 34, FX + 10, 50), 180, 360, fill=1)
