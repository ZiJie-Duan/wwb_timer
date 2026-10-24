"""太极拳：小人在一张缓缓转动的太极图前打拳，两手划过的轨迹留下行云流水般的点线。

入场：太极图的外圈一笔画出来，小人并步站立，“起势”——两臂平举、屈膝下按。
持续：一遍五式（每式 120 秒）：野马分鬃、白鹤亮翅、搂膝拗步、云手、单鞭；动作按 e 推进，
      手的轨迹（前一秒多的位置）画成渐隐的点；云手时人横着走云步。一遍练完“收势、起势”，第几遍加一。
中断：两臂缓缓落下，“收势”。
恢复：“起势”，接回刚才的动作。
圆满：收势后人影淡去，背后太极图变实、旋转渐停，“动静之机”（王宗岳《太极拳论》）。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, span
from ..engine.cn import cn_num
from ..engine.fx import ring
from ..engine.gfx import Gfx, dissolve
from ..engine.scene import Ritual, register
from ..engine.symbols import mx_taiji, taiji
from .r4_kit import Body, blend, figure, mirror, pose, seq

GROUND = 61
CX = 64
TJ = (64, 31)     # 背景太极图中心
TJ_R = 27
FORM_S = 120.0
INTRO = 3.0
RENEW = 5.0

LOW = dict(lth=-22, lsh=-6, rth=22, rsh=6)                    # 屈膝
BOWL = dict(lth=-38, lsh=-4, rth=14, rsh=-2)                  # 左弓步（屏幕左）
STAND = pose(lua=-10, lfa=-6, rua=10, rfa=6, lth=-3, lsh=-1, rth=3, rsh=1)
BALL = pose(LOW, lua=-40, lfa=95, rua=30, rfa=-120)           # 抱球：左手在胸前、右手在腹前


def _ma():  # 野马分鬃
    a = pose(BOWL, lua=-115, lfa=-125, rua=30, rfa=45, face=-1)
    return [BALL, a, a, mirror(BALL), mirror(a), mirror(a)]


def _he():  # 白鹤亮翅
    a = pose(lth=-6, lsh=-14, rth=14, rsh=4, lua=-25, lfa=-55, rua=150, rfa=170, face=-1)
    return [BALL, a, a, a, BALL]


def _lou():  # 搂膝拗步
    a = pose(BOWL, lua=-15, lfa=-35, rua=-75, rfa=-90, face=-1)
    return [pose(LOW, lua=-30, lfa=-10, rua=60, rfa=150), a, a, mirror(pose(LOW, lua=-30, lfa=-10, rua=60, rfa=150)),
            mirror(a), mirror(a)]


def _yun():  # 云手
    a = pose(LOW, tor=-6, lua=-50, lfa=140, rua=20, rfa=-80, face=-1)
    return [a, mirror(a)]


def _bian():  # 单鞭
    a = pose(BOWL, lua=-92, lfa=-88, rua=95, rfa=92, rh=5, face=-1)
    return [BALL, a, a, a]


FORMS = [(_ma(), 9.0, "野马分鬃"), (_he(), 8.0, "白鹤亮翅"), (_lou(), 9.0, "搂膝拗步"), (_yun(), 5.0, "云手"),
         (_bian(), 10.0, "单鞭")]
ROUND = FORM_S * len(FORMS)


@register
class Taiji(Ritual):
    id = "r4.taiji"
    name = "太极拳"
    desc = "小人在缓转的太极图前打太极拳，野马分鬃、白鹤亮翅、搂膝拗步、云手、单鞭，双手留下行云流水的轨迹"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 2.0, "complete": 5.5}
    CYCLE = ROUND + RENEW

    # ------------------------------------------------------------ 动作

    def where(self, e: float):
        n = int(e // self.CYCLE) + 1
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return n, True, 0, k
        if e >= self.CYCLE:
            k -= RENEW
        i = min(len(FORMS) - 1, int(k // FORM_S))
        return n, False, i, k - i * FORM_S

    def pose_at(self, e: float) -> tuple[dict, float]:
        """→ (姿势, 人的 x)"""
        n, renew, i, u = self.where(e)
        if renew:  # 收势 → 起势
            k = math.sin(span(u, 0.5, RENEW - 0.5) * math.pi)
            return blend(STAND, pose(LOW, lua=-80, lfa=-85, rua=80, rfa=85), k), CX
        keys, per, _ = FORMS[i]
        if u < INTRO:
            p = blend(STAND, keys[0], ease_in_out(span(u, 0.3, INTRO)))
        else:
            p = seq(keys, u - INTRO, per)
        p = blend(p, STAND, ease_in_out(span(u, FORM_S - 2.0, FORM_S - 0.2)))
        x = CX
        if i == 3 and u > INTRO:  # 云步：横着走三步再走回来
            w = (u - INTRO) / (per * 3)
            tri = abs((w % 2) - 1)  # 1 → 0 → 1
            x = CX + (tri - 0.5) * 2 * 18 * clamp(span(u, INTRO, INTRO + 2) * span(u, FORM_S, FORM_S - 3))
        return p, x

    # ------------------------------------------------------------ 画面零件

    def backdrop(self, g: Gfx, e: float, draw: float = 1.0):
        """背景太极：点状外圈 + S 形中线 + 两只鱼眼，缓缓转"""
        cx, cy = TJ
        rot = e * 0.12
        n = int(90 * draw)
        for i in range(n):
            if i % 2:
                continue
            a = rot + i / 90 * 2 * math.pi
            g.px(cx + math.cos(a) * TJ_R, cy + math.sin(a) * TJ_R)
        if draw >= 1:
            for i in range(0, 40, 2):  # S 形：两个半圆
                a = i / 40 * math.pi
                for sgn in (-1, 1):
                    r = TJ_R / 2
                    ox, oy = cx + sgn * math.cos(rot) * r, cy + sgn * math.sin(rot) * r
                    aa = rot + a + (0 if sgn > 0 else math.pi)
                    g.px(ox + math.cos(aa) * r, oy + math.sin(aa) * r)

    def trails(self, g: Gfx, e: float, amt: float = 1.0):
        """两手走过的路：往回取 16 个时刻的手位连成线，越旧越稀（行云流水）"""
        if amt <= 0:
            return
        n = int(16 * amt)
        prev = None
        for k in range(0, n + 1):
            p, x = self.pose_at(max(0.0, e - k * 0.17))
            b = Body(p, x, GROUND)
            cur = (b.lhand, b.rhand)
            if prev is not None:
                for (x0, y0), (x1, y1) in zip(prev, cur):
                    if k < 7:
                        g.d.line((x0, y0 + 1, x1, y1 + 1), fill=1)
                    elif k % 2 == 0:
                        g.px(x1, y1 + 1)
            prev = cur

    def texts(self, g: Gfx, e: float, a: float = 1.0, left: str | None = None):
        n, renew, i, u = self.where(e)
        l = left if left is not None else ("收势" if renew and u < RENEW / 2 else "起势" if renew else FORMS[i][2])
        g.vtext(2, 2, l[:int(round(len(l) * a))])
        r = f"第{cn_num(n)}遍"
        g.vtext(115, 2, r[:int(round(len(r) * a))])

    def ground(self, g: Gfx):
        g.d.line((22, GROUND, 106, GROUND), fill=1)
        for x in (18, 110):
            g.px(x, GROUND)

    def mx(self, g: Gfx, e: float):
        mx_taiji(g, e * 0.6)

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float, e: float):
        self.backdrop(g, e)
        self.ground(g)
        p, x = self.pose_at(e)
        self.trails(g, e)
        figure(g, p, x, GROUND)
        self.texts(g, e)
        self.mx(g, e)

    def enter(self, g: Gfx, t: float):
        self.backdrop(g, 0, draw=ease_in_out(span(t, 0, 1.6)))
        self.ground(g)
        if t < 2.0:
            p = blend(pose(lth=0, lsh=0, rth=0, rsh=0, hipw=1.5), STAND, ease_in_out(span(t, 1.4, 2.0)))
        else:  # 起势：两臂前平举（正面看是往两边抬），屈膝按掌
            k = math.sin(span(t, 2.0, 4.3) * math.pi)
            p = blend(STAND, pose(LOW, lua=-80, lfa=-85, rua=80, rfa=85), k)
        figure(g, p, CX, GROUND)
        if t > 2.0:
            g.vtext(2, 2, "起势"[:int(clamp((t - 2.0) * 3) * 2)])
        self.texts(g, 0, a=span(t, 3.6, 4.5)) if t > 3.6 else None
        self.mx(g, 0)
        if t < 1.6:
            g.mx[:] = False
            for k in range(int(span(t, 0, 1.6) * 28)):
                ringc = [(x, 0) for x in range(2, 6)] + [(6, 1), (7, 2), (7, 3), (7, 4), (7, 5), (6, 6)] + \
                        [(x, 7) for x in range(5, 1, -1)] + [(1, 6), (0, 5), (0, 4), (0, 3), (0, 2), (1, 1)]
                x, y = ringc[k % len(ringc)]
                g.mx[y, x] = True

    def interrupt(self, g: Gfx, t: float, e: float):
        self.backdrop(g, e)
        self.ground(g)
        p, x = self.pose_at(e)
        k = ease_in_out(span(t, 0, 1.4))
        figure(g, blend(p, STAND, k), lerp(x, CX, k), GROUND)
        self.trails(g, e, 1 - k)
        self.texts(g, e, left="收势")
        self.mx(g, e)

    def resume(self, g: Gfx, t: float, e: float):
        self.backdrop(g, e)
        self.ground(g)
        p, x = self.pose_at(e)
        if t < 1.0:
            k = math.sin(span(t, 0, 1.0) * math.pi)
            q = blend(STAND, pose(LOW, lua=-80, lfa=-85, rua=80, rfa=85), k)
            figure(g, q, CX, GROUND)
            self.texts(g, e, left="起势")
        else:
            k = ease_in_out(span(t, 1.0, 2.0))
            figure(g, blend(STAND, p, k), lerp(CX, x, k), GROUND)
            self.trails(g, e, k)
            self.texts(g, e)
        self.mx(g, e)

    def complete(self, g: Gfx, t: float, e: float):
        p, x = self.pose_at(e)
        k = ease_in_out(span(t, 0, 1.4))
        fill = ease_in_out(span(t, 1.6, 3.0))
        # 太极图先转快再渐停：相位 = e·0.12 + 一段缓出的追加
        rot = e * 0.12 + 3.0 * ease_out(span(t, 1.4, 5.5))
        if fill < 1:  # 收势的人
            self.backdrop(g, rot / 0.12)
            self.ground(g)
            figure(g, blend(p, STAND, k), lerp(x, CX, k), GROUND)
            self.trails(g, e, 1 - k)
            if t < 1.4:
                self.texts(g, e, left="收势")
        if fill > 0:  # 人影溶进一张实心的太极图
            a = g.array() if fill < 1 else None
            g.d.rectangle((0, 0, 127, 63), fill=0)
            taiji(g, TJ[0], TJ[1], TJ_R, angle=rot)
            ring(g, TJ[0], TJ[1], TJ_R + 4, 3, -rot)
            self.ground(g)
            if a is not None:
                g.put(dissolve(a, g.array(), fill))
        if t > 3.0:
            g.vtext(115, 2, "动静之机"[:int(clamp((t - 3.0) * 3) * 4)])
        mx_taiji(g, rot * 5)
        g.mx_level = 4 if 2.8 < t < 3.3 else 1
