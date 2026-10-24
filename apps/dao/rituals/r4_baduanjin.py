"""八段锦：小人在院子里逐式练完八段锦，每式按歌诀做出真实动作。

入场：小人从左边走进院子，站定拱手，起势。
持续：一遍八式（每式 60 秒），每式开头歌诀逐字出现；动作按 e 推进（断线重连能接上）。
      八式练完：收势、抱腹调息，右侧“第几遍”加一，再从第一式练起。
中断：放下手，两手叠放丹田“收势”。
恢复：从收势回到刚才的动作。
圆满：两手叠于丹田，周身放光，“功行圆满”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.cn import cn_num
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import blend, figure, mirror, pose, seq

GROUND = 60
CX = 64
FORM_S = 60.0
INTRO = 4.0        # 每式开头：从上一式收回、换到本式起手（歌诀出现）
RENEW = 6.0        # 一遍练完后的收势调息

N = pose(lua=-12, lfa=-8, rua=12, rfa=8)
HORSE = dict(lth=-30, lsh=-8, rth=30, rsh=8)
BELLY = pose(lua=-22, lfa=85, rua=22, rfa=-85)           # 两手叠于腹前（丹田）
SIDE = dict(shw=2.5, hipw=0.6, face=1, lth=2, lsh=0, rth=-2, rsh=0)

# 每式：关键帧（循环）、一圈秒数、歌诀、简称
FORMS = [
    ([N, BELLY, pose(lua=-35, lfa=165, rua=35, rfa=-165),
      pose(lua=-176, lfa=172, rua=176, rfa=-172, lift=2), pose(lua=-176, lfa=172, rua=176, rfa=-172, lift=2),
      pose(lua=-95, lfa=-95, rua=95, rfa=95)], 9.0, "两手托天理三焦", "托天"),
    ([pose(lua=-30, lfa=110, rua=30, rfa=-110, **HORSE),
      pose(lua=-90, lfa=-90, rua=82, rfa=-75, lh=3, rh=1, face=-1, **HORSE),
      pose(lua=-90, lfa=-90, rua=82, rfa=-75, lh=3, rh=1, face=-1, **HORSE),
      pose(lua=-30, lfa=110, rua=30, rfa=-110, **HORSE),
      pose(lua=-82, lfa=75, rua=90, rfa=90, lh=1, rh=3, face=1, **HORSE),
      pose(lua=-82, lfa=75, rua=90, rfa=90, lh=1, rh=3, face=1, **HORSE)], 10.0, "左右开弓似射雕", "开弓"),
    ([N, pose(lua=-178, lfa=-178, rua=18, rfa=75), pose(lua=-178, lfa=-178, rua=18, rfa=75), N,
      pose(lua=-18, lfa=-75, rua=178, rfa=178), pose(lua=-18, lfa=-75, rua=178, rfa=178)], 9.0, "调理脾胃须单举", "单举"),
    ([pose(lua=-22, lfa=-28, rua=22, rfa=28), pose(lua=-22, lfa=-28, rua=22, rfa=28, face=-1, tilt=-8),
      pose(lua=-22, lfa=-28, rua=22, rfa=28, face=-1, tilt=-8), pose(lua=-22, lfa=-28, rua=22, rfa=28),
      pose(lua=-22, lfa=-28, rua=22, rfa=28, face=1, tilt=8), pose(lua=-22, lfa=-28, rua=22, rfa=28, face=1, tilt=8)],
     8.0, "五劳七伤往后瞧", "后瞧"),
    ([pose(lua=-35, lfa=15, rua=35, rfa=-15, **HORSE),
      pose(tor=-28, tilt=-12, lua=-60, lfa=-5, rua=10, rfa=-20, **HORSE),
      pose(lua=-35, lfa=15, rua=35, rfa=-15, **HORSE),
      pose(tor=28, tilt=12, lua=-10, lfa=20, rua=60, rfa=5, **HORSE)], 8.0, "摇头摆尾去心火", "摆尾"),
    ([pose(lua=-10, lfa=-5, rua=10, rfa=5, **SIDE), pose(lua=178, lfa=178, rua=176, rfa=176, **SIDE),
      pose(tor=100, tilt=25, lua=-48, lfa=-52, rua=-44, rfa=-50, **SIDE),
      pose(tor=100, tilt=25, lua=-48, lfa=-52, rua=-44, rfa=-50, **SIDE),
      pose(tor=40, lua=5, lfa=-5, rua=8, rfa=-3, **SIDE)], 9.0, "两手攀足固肾腰", "攀足"),
    ([pose(lua=-35, lfa=110, rua=35, rfa=-110, lh=1, rh=1, brow=1, **HORSE),
      pose(lua=-90, lfa=-90, rua=35, rfa=-110, lh=1, rh=1, brow=1, **HORSE),
      pose(lua=-35, lfa=110, rua=35, rfa=-110, lh=1, rh=1, brow=1, **HORSE),
      pose(lua=-35, lfa=110, rua=90, rfa=90, lh=1, rh=1, brow=1, **HORSE)], 5.0, "攒拳怒目增气力", "攒拳"),
    ([pose(lua=-10, lfa=-18, rua=10, rfa=18), pose(lua=-10, lfa=-18, rua=10, rfa=18, lift=4)], 1.4,
     "背后七颠百病消", "七颠"),
]
CYCLE_S = FORM_S * len(FORMS)
TITLE_ICON = ["托", "弓", "举", "瞧", "摆", "足", "拳", "颠"]


def walk(k: float) -> dict:
    """走路：k = 步相（弧度）"""
    s = math.sin(k)
    return pose(lth=-18 * s, lsh=-18 * s - 6 * max(0, s), rth=18 * s, rsh=18 * s - 6 * max(0, -s),
                lua=14 * s, lfa=10 * s + 10, rua=-14 * s, rfa=-14 * s + 10, face=1, shw=3.5, hipw=1.2)


@register
class Baduanjin(Ritual):
    id = "r4.baduanjin"
    name = "八段锦"
    desc = "小人在院中依歌诀逐式练八段锦：托天、开弓、单举、后瞧、摆尾、攀足、攒拳、七颠"
    T = {"enter": 4.5, "interrupt": 1.5, "resume": 1.8, "complete": 5.0}
    CYCLE = CYCLE_S + RENEW

    # ------------------------------------------------------------ 动作

    def where(self, e: float):
        """→ (遍数 n≥1, 是否在收势调息, 式序号 i, 本式内秒数 u)"""
        n = int(e // self.CYCLE) + 1
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return n, True, 0, k
        k -= RENEW if e >= self.CYCLE else 0
        k = max(0.0, k)
        i = min(len(FORMS) - 1, int(k // FORM_S))
        return n, False, i, k - i * FORM_S

    def form_pose(self, i: int, u: float) -> dict:
        keys, per, _, _ = FORMS[i]
        if u < INTRO:  # 换式：从上一式的收尾（或站定）过渡到本式第一帧
            prev = N
            return blend(prev, keys[0], ease_in_out(span(u, 0.6, INTRO)))
        return seq(keys, u - INTRO, per)

    def pose_at(self, e: float) -> dict:
        n, renew, i, u = self.where(e)
        if renew:
            return blend(BELLY, N, ease_in_out(span(u, RENEW - 1.5, RENEW)))
        # 本式末尾 1.2 秒回到站定
        p = self.form_pose(i, u)
        return blend(p, N, ease_in_out(span(u, FORM_S - 1.6, FORM_S - 0.2)))

    # ------------------------------------------------------------ 画面零件

    def yard(self, g: Gfx):
        d = g.d
        d.line((0, GROUND, 127, GROUND), fill=1)
        for x in range(4, 128, 9):  # 青石板
            g.px(x, GROUND + 2)
            g.px(x + 4, GROUND + 3)

    def bow(self, g: Gfx, b, p: dict, t: float):
        for hd, pull, ua in ((b.lhand, b.rhand, p["lua"]), (b.rhand, b.lhand, p["rua"])):
            if abs(ua) < 80:
                continue
            sd = 1 if ua > 0 else -1
            draw = clamp((abs(ua) - 80) / 10)
            hx, hy = hd
            # 弓背：竖着的弧，弓弦拉到后手
            top, bot = (hx - sd * 1, hy - 9), (hx - sd * 1, hy + 9)
            g.d.arc((hx - 4 - (sd < 0) * 0, hy - 9, hx + 4, hy + 9), 270 if sd > 0 else 90, 90 if sd > 0 else 270,
                    fill=1)
            px_ = lerp(hx - sd * 4, pull[0], draw)
            g.d.line((top, (px_, pull[1]), bot), fill=1)
        # 雕：在高处盘旋
        bx = 64 + math.sin(t * 0.4) * 40
        by = 18 + math.sin(t * 0.9) * 3
        fl = 2 if int(t * 4) % 2 else -1
        g.d.line((bx - 4, by + fl, bx, by, bx + 4, by + fl), fill=1)

    def dust(self, g: Gfx, b, amt: float):
        if amt <= 0:
            return
        for fx, fy in (b.lfoot, b.rfoot):
            for j in range(3):
                r = 3 + amt * 4 + j
                g.px(fx - r, GROUND - 1 - j)
                g.px(fx + r, GROUND - 1 - j)

    def texts(self, g: Gfx, e: float, a: float = 1.0, right: str | None = None):
        n, renew, i, u = self.where(e)
        r = right if right is not None else f"第{cn_num(n)}遍"
        g.vtext(115, 3, r[:int(round(len(r) * a))])
        if renew:
            left = "收势"
        else:
            left = FORMS[i][3]
        g.vtext(2, 3, left[:int(round(len(left) * a))])
        if not renew and u < INTRO + 3.5 and a >= 1:  # 歌诀逐字出现，然后淡出
            s = FORMS[i][2]
            k = 1 - span(u, INTRO + 2.5, INTRO + 3.5)
            if k > 0:
                typewriter(g, CX, 1, s, u, cps=4, align="center")
                if k < 1:
                    g.fade(k, (20, 0, 108, 13))

    def mx(self, g: Gfx, e: float, t: float):
        """点阵：下排 8 格 = 八式进度；上面画一个缩小的小人跟着做"""
        n, renew, i, u = self.where(e)
        for x in range(8):
            g.mx[7, x] = x < i or (x == i and blink(t, 0.8, 0.6)) or renew
        b = self._last
        if b is None:
            return
        # 把小人从 OLED 坐标缩到 8×7
        ox, oy, sc = CX - 24, GROUND - 47, 7.0
        def m(pt):
            return int(round((pt[0] - ox) / sc)), int(round((pt[1] - oy) / sc))
        segs = [(b.head, b.neck), (b.neck, b.hip), (b.lsho, b.lelb), (b.lelb, b.lhand), (b.rsho, b.relb),
                (b.relb, b.rhand), (b.hip, b.lknee), (b.lknee, b.lfoot), (b.hip, b.rknee), (b.rknee, b.rfoot)]
        for a_, b_ in segs:
            (x0, y0), (x1, y1) = m(a_), m(b_)
            steps = max(abs(x1 - x0), abs(y1 - y0), 1)
            for s in range(steps + 1):
                x = round(x0 + (x1 - x0) * s / steps)
                y = round(y0 + (y1 - y0) * s / steps)
                if y < 7:
                    g.mx_set(x, y)

    def scene(self, g: Gfx, p: dict, t: float, e: float, glow: float = 0.0):
        self.yard(g)
        b = figure(g, p, CX, GROUND)
        self._last = b
        return b

    _last = None

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.yard(g)
        if t < 2.2:  # 走进来
            k = ease_out(span(t, 0, 2.2))
            x = lerp(-12, CX, k)
            p = blend(walk(t * 7), N, span(t, 1.9, 2.2))
        elif t < 3.2:  # 拱手作揖
            x = CX
            k = math.sin(span(t, 2.2, 3.2) * math.pi)
            p = blend(N, pose(lua=-25, lfa=120, rua=25, rfa=-120, lh=1, rh=1, tilt=0), k)
            p["tor"] = 0
        else:  # 起势：两臂前平举再按下
            x = CX
            k = math.sin(span(t, 3.2, 4.5) * math.pi)
            p = blend(N, pose(lua=-70, lfa=-80, rua=70, rfa=80), k)
        b = figure(g, p, x, GROUND)
        self._last = b
        if t > 2.2:
            typewriter(g, CX, 1, "八段锦", t - 2.2, cps=4, align="center")
            if t > 3.6:
                g.fade(1 - span(t, 3.6, 4.4), (20, 0, 108, 13))
        self.texts(g, 0, a=span(t, 3.4, 4.5))
        self.mx(g, 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        p = self.pose_at(e)
        b = self.scene(g, p, t, e)
        n, renew, i, u = self.where(e)
        if not renew and i == 7 and u > INTRO:  # 七颠：脚跟落地震起尘土
            ph = ((u - INTRO) % FORMS[7][1]) / FORMS[7][1]
            self.dust(g, b, 1 - span(ph, 0.0, 0.25) if ph < 0.25 else 0)
        if not renew and i == 3 and u > INTRO:  # 往后瞧：目光
            if abs(p["face"]) > 0.7:
                sd = 1 if p["face"] > 0 else -1
                hx, hy = b.head
                for j in range(4):
                    g.px(hx + sd * (7 + j * 4 + (t * 8) % 4), hy - 1 + j)
        if not renew and i == 1 and u > INTRO:  # 开弓：虚拟的弓弦 + 天上一只雕
            self.bow(g, b, p, t)
        if not renew and i == 6 and u > INTRO:  # 攒拳：出拳的风
            for hd, ua in ((b.lhand, p["lua"]), (b.rhand, p["rua"])):
                if abs(ua) > 80:
                    sd = 1 if ua > 0 else -1
                    for j in range(3):
                        g.d.line((hd[0] + sd * (4 + j), hd[1] - 3 + j * 3, hd[0] + sd * (8 + j * 2), hd[1] - 3 + j * 3),
                                 fill=1)
        if renew:  # 收势调息：丹田一团气由大到小
            hx, hy = b.hip[0], b.hip[1] - 4
            r = 2 + 6 * (1 - span(u, 0.5, RENEW - 1.5))
            ring(g, hx, hy, r + 3, 2, t)
        self.texts(g, e)
        self.mx(g, e, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        k = ease_in_out(span(t, 0, 1.2))
        p = blend(self.pose_at(e), BELLY, k)
        self.scene(g, p, t, e)
        self.texts(g, e, right="收势")
        self.mx(g, e, t)

    def resume(self, g: Gfx, t: float, e: float):
        k = ease_in_out(span(t, 0.3, 1.8))
        p = blend(BELLY, self.pose_at(e), k)
        self.scene(g, p, t, e)
        if t < 0.6:
            self.texts(g, e, right="收势")
        else:
            self.texts(g, e)
        self.mx(g, e, t)

    def complete(self, g: Gfx, t: float, e: float):
        k = ease_in_out(span(t, 0, 1.3))
        p = blend(self.pose_at(e), BELLY, k)
        self.yard(g)
        b = figure(g, p, CX, GROUND)
        self._last = b
        if t > 1.3:  # 周身放光
            gl = ease_out(span(t, 1.3, 2.5))
            hx, hy = b.hip[0], b.hip[1] - 6
            for j in range(14):
                a = j / 14 * 2 * math.pi + t * 0.6
                r0, r1 = 24, 24 + 8 * gl * (0.7 + 0.3 * math.sin(t * 5 + j))
                g.d.line((hx + math.cos(a) * r0, hy + math.sin(a) * r0 * 0.9, hx + math.cos(a) * r1,
                          hy + math.sin(a) * r1 * 0.9), fill=1)
            for j in range(10):
                if blink(t + j * 0.17, 0.6, 0.35):
                    a = rand(j, 3) * 2 * math.pi
                    r = 12 + rand(j, 4) * 18
                    g.px(hx + math.cos(a) * r, hy + math.sin(a) * r * 0.8)
        if t < 1.3:
            self.texts(g, e, a=1 - span(t, 0.3, 1.3))
        else:
            g.d.rectangle((0, 0, 127, 13), fill=0)
            typewriter(g, CX, 1, "功行圆满", t - 1.6, cps=5, align="center")
        if t < 1.3:
            self.mx(g, e, t)
        else:
            r = (t - 1.3) * 4
            for y in range(8):
                for x in range(8):
                    g.mx[y, x] = abs(math.hypot(x - 3.5, y - 3.5) - r % 6) < 0.8 or y == 7
            g.mx_level = 1 + int(5 * (1 - span(t, 1.3, 3.0)))
