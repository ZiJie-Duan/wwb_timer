"""丹青：画诀取传为王维的《山水论》“远山无石，隐隐如眉；远水无波……远树无枝，远人无目”；
画成题宗炳“澄怀观道，卧以游之”（《宋书·隐逸传》）；点睛彩蛋取张彦远《历代名画记》张僧繇画龙“每云点睛即飞去……
须臾雷电破壁，两龙乘云腾去上天”。

墙上挂一幅横披（绫子镶边、两头画轴），小道士站在左边捏剑指，一支毛笔自己飞起来在画上走（道士作画，笔随指走），
笔尖拖一串墨星。
入场：画轴从左往右展开，笔从笔洗里弹起来。
持续（一幅 48 秒）：远山（虚线，“远山无石”“隐隐如眉”）→ 主峰勾勒 → 一笔笔披麻皴 → 飞瀑 → 近处一棵松（“远树无枝”）
      → 远水（“远水无波”）→ 渔舟（“远人无目”）→ 飞鸟 → 题“溪山”钤印（啪）。
      画成后画中“活了”：瀑布流、渔舟漂、松针摆、鸟扇翅，下方题“澄怀观道”“卧以游之”；然后画轴卷起，再展开新纸。
      每第三幅把渔舟飞鸟换成云中一条龙（无睛），最后笔点双睛——白光一闪、一道闪电、震屏，
      龙破纸而出向右上飞走，只留空云（“点睛即飞去”）。小道士吓得张大嘴。
退场：画轴卷起，收圆。
点阵：上下两行是画轴，中间像画一样逐列“画”出一座山；龙飞时是游动的龙身。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import Clock, iris, label, put_arm

FLOOR = 58
DX = 15                        # 小道士（站，朝右）
FX0, FY0, FX1, FY1 = 30, 4, 126, 46     # 画（含镶边）
IX, IY = FX0 + 4, FY0 + 4      # 画心左上
IW, IH = FX1 - FX0 - 8, FY1 - FY0 - 8   # 88 × 34
CYC = 48.0


def _line(pts):
    """折线 → 按笔顺排好的像素列表"""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) or 1
        for i in range(n):
            p = (round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n))
            if not out or out[-1] != p:
                out.append(p)
    out.append((round(pts[-1][0]), round(pts[-1][1])))
    return out


# 画面（画心坐标）：(开始, 结束, 种类, 数据, 画诀)
FAR = [(1, 16), (8, 11), (14, 13), (21, 8), (28, 12), (34, 10)]
FAR2 = [(54, 11), (62, 6), (70, 9), (78, 7), (86, 10)]
PEAK = [(16, 33), (22, 22), (26, 13), (31, 4), (35, 8), (38, 6), (42, 14), (45, 20), (50, 33)]
CUN = [[(27, 14), (25, 21)], [(30, 9), (28, 18)], [(33, 8), (32, 16)], [(36, 10), (36, 18)], [(39, 9), (41, 17)],
       [(24, 24), (22, 30)], [(29, 21), (28, 29)], [(42, 18), (44, 26)], [(34, 19), (34, 27)]]
FALL = [(40, 12), (40, 27)]
PINE = [(9, 33), (10, 27), (8, 22), (10, 17), (8, 12)]
PADS = [(5, 13, 5), (12, 18, 5), (5, 23, 4), (13, 26, 4)]
WATER = [[(56, 26), (64, 26)], [(68, 28), (78, 28)], [(58, 30), (70, 30)], [(74, 24), (84, 24)], [(80, 31), (86, 31)]]
BOAT = (66, 22)
BIRDS = [(60, 4), (66, 7)]
DRAGON = [(46 + i * 1.0, 20 + math.sin(i * 0.25) * 6) for i in range(0, 32, 2)]
CLOUDS = [(56, 25, 6), (70, 21, 7), (82, 26, 5), (62, 6, 4)]

PLAN = [
    (2.0, 4.0, "dot", [FAR, FAR2], "远山无石"),
    (4.0, 6.0, "dot2", None, "隐隐如眉"),
    (6.0, 10.0, "line", [PEAK], None),
    (10.0, 14.0, "line", CUN, None),
    (14.0, 16.5, "line", [FALL], None),
    (16.5, 20.5, "pine", None, "远树无枝"),
    (20.5, 23.5, "line", WATER, "远水无波"),
    (23.5, 26.5, "boat", None, "远人无目"),
    (26.5, 28.5, "birds", None, None),
    (28.5, 30.5, "title", None, None),
]
DPLAN = PLAN[:6] + [
    (20.5, 24.0, "clouds", None, None),
    (24.0, 29.0, "dragon", None, None),
    (29.0, 30.5, "title", None, None),
]
ALIVE = (31.0, 45.0)
DOT_EYE = 33.0                 # 点睛（龙那一幅）

_PIX: dict = {}


def pixels(key, pts):
    if key not in _PIX:
        _PIX[key] = _line(pts)
    return _PIX[key]


BRUSH = Sprite("""
    .#
   .#.
  .#.
 ##.
###
##
#
""")

BOAT_SPR = Sprite("""
   #
   ##
  ###
#######
 #####
""")

DRAGON_HEAD = Sprite("""
 #   #
  # #
 #####.#
#######.#
###..####
 ########
  ### ##
 ##    ##
""")


def _seal():
    p = Part(5, 5)
    p.shape("rectangle", (0, 0, 4, 4), fill=1)
    p.d.line((2, 1, 2, 3), fill=0)
    p.d.line((1, 2, 3, 2), fill=0)
    return p.sprite()


SEAL = _seal()


@register
class Paint(Rest):
    id = "x2.paint"
    name = "丹青"
    desc = "小道士捏剑指驱笔作画：远山、皴峰、飞瀑、松、渔舟一笔笔画出，画成后画中活了；每三幅画一条龙，点睛即破纸飞去"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.ht = 0.0
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    # ------------------------------------------------------------ 画

    def painting(self, g: Gfx, k: float, t: float, dragon: bool, alive: bool, flown: float):
        """在画心里画到 k 秒的样子 → 笔尖位置（画心坐标，None = 没在画）"""
        plan = DPLAN if dragon else PLAN
        tip = None
        ox, oy = IX, IY

        def P(x, y, v=1):
            if 0 <= x < IW and 0 <= y < IH:
                g.px(ox + x, oy + y, v)

        for t0, t1, kind, data, _ in plan:
            if k < t0:
                break
            q = span(k, t0, t1)
            if kind in ("dot", "dot2"):
                lines = [FAR, FAR2] if kind == "dot" else [[(x, y + 5) for x, y in FAR2[1:]]]
                tot = sum(len(pixels((kind, i), ln)) for i, ln in enumerate(lines))
                n = int(q * tot)
                for i, ln in enumerate(lines):
                    ps = pixels((kind, i), ln)
                    for j, (x, y) in enumerate(ps[:n]):
                        if j % 2 == 0:
                            P(x, y)
                    if 0 < n < len(ps):
                        tip = ps[n]
                    n -= len(ps)
                    if n <= 0:
                        break
            elif kind == "line":
                tot = sum(len(pixels(("l", t0, i), ln)) for i, ln in enumerate(data))
                n = int(q * tot)
                for i, ln in enumerate(data):
                    ps = pixels(("l", t0, i), ln)
                    if ln is FALL and k >= ALIVE[0] and alive:       # 瀑布流动
                        for j, (x, y) in enumerate(ps):
                            if (j + int(t * 12)) % 4:
                                P(x, y), P(x + 1, y)
                        P(38, 28), P(42, 28), P(39, 29), P(41, 29)
                        continue
                    for x, y in ps[:max(n, 0)]:
                        P(x, y)
                        if ln is FALL:
                            P(x + 1, y)
                    if 0 < n < len(ps):
                        tip = ps[n]
                    n -= len(ps)
            elif kind == "pine":
                ps = pixels("pine", PINE)
                n = int(span(q, 0, 0.4) * len(ps))
                for x, y in ps[:n]:
                    P(x, y), P(x + 1, y)
                if q < 0.4:
                    tip = ps[min(n, len(ps) - 1)]
                sway = round(math.sin(t * 1.5)) if alive and k >= ALIVE[0] else 0
                for i, (cx, cy, r) in enumerate(PADS):
                    a = span(q, 0.4 + i * 0.15, 0.55 + i * 0.15)
                    if a <= 0:
                        continue
                    rr = int(r * a)
                    for x in range(-rr, rr + 1):
                        P(cx + x + sway, cy - (1 if abs(x) < rr - 1 else 0))
                        if x % 2 == 0:
                            P(cx + x + sway, cy - 2)
                        P(cx + x + sway, cy)
                    if a < 1:
                        tip = (cx + rr, cy)
            elif kind == "boat":
                drift = math.sin((k - ALIVE[0]) * 0.4) * 3 if alive and k >= ALIVE[0] else 0
                if q > 0.3:
                    g.blit(BOAT_SPR, ox + BOAT[0] + drift, oy + BOAT[1])
                if q < 1:
                    tip = (BOAT[0] + 3, BOAT[1] + 2)
            elif kind == "birds":
                for i, (bx, by) in enumerate(BIRDS):
                    if q > 0.3 + i * 0.35:
                        f = int(t * 4 + i) % 2 if alive and k >= ALIVE[0] else 0
                        dx_ = ((k - ALIVE[0]) * 1.2) % 20 if alive and k >= ALIVE[0] else 0
                        P(bx - 2 + dx_, by - f), P(bx - 1 + dx_, by), P(bx + dx_, by + 1), P(bx + 1 + dx_, by)
                        P(bx + 2 + dx_, by - f)
                if q < 1:
                    tip = BIRDS[min(int(q * 2), 1)]
            elif kind == "clouds":                                  # 云：两道云带，左头一个回卷
                for i, (cx, cy, r) in enumerate(CLOUDS):
                    a = span(q, i * 0.22, i * 0.22 + 0.3)
                    if a <= 0:
                        continue
                    xe = cx - r + 2 * r * a
                    g.d.line((ox + cx - r, oy + cy, ox + xe, oy + cy), fill=1)
                    if a > 0.4:
                        g.d.line((ox + cx - r + 3, oy + cy - 2, ox + min(xe, cx + r - 2), oy + cy - 2), fill=1)
                    g.d.ellipse((ox + cx - r - 3, oy + cy - 3, ox + cx - r, oy + cy), outline=1)
                    g.px(ox + cx - r - 1, oy + cy - 1)
                    if a < 1:
                        tip = (xe, cy)
            elif kind == "dragon":
                if flown > 0:
                    continue
                n = int(q * len(DRAGON))
                self.dragon(g, ox, oy, DRAGON[:max(n, 0)], t if alive else 0, k >= DOT_EYE + 0.5)
                if q < 1:
                    tip = DRAGON[min(n, len(DRAGON) - 1)]
            elif kind == "title":                                   # 题款、钤印（字在 scene 最后写）
                if q > 0.1:
                    self.title = True
                if q > 0.6:
                    g.blit(SEAL, ox + IW - 8, oy + 18)
                if q < 0.6:
                    tip = (IW - 16, 3 + q * 20)
        return tip

    def dragon(self, g: Gfx, ox, oy, pts, t, eyes: bool, scale: float = 1.0):
        """龙：粗身子（两像素）带鳞点、背鳍，龙头在最前；eyes=点了睛"""
        if len(pts) < 2:
            return
        wav = [(x, y + math.sin(t * 3 + i * 0.5) * 1.0 * (1 if t else 0)) for i, (x, y) in enumerate(pts)]
        for (x0, y0), (x1, y1) in zip(wav, wav[1:]):
            g.d.line((ox + x0, oy + y0, ox + x1, oy + y1), fill=1, width=3)
        for i, (x, y) in enumerate(wav[1:-1]):
            if i % 2 == 0:
                g.px(ox + x, oy + y, 0)
                g.px(ox + x, oy + y - 2)                           # 背鳍
        for i in (3, 9):                                           # 爪
            if i < len(wav):
                x, y = wav[i]
                g.d.line((ox + x, oy + y + 1, ox + x - 1, oy + y + 4), fill=1)
                g.px(ox + x - 2, oy + y + 4), g.px(ox + x, oy + y + 4)
        if len(wav) == len(DRAGON):
            hx, hy = wav[-1]
            g.blit(DRAGON_HEAD, ox + hx - 1, oy + hy - 5)
            if eyes:
                g.px(ox + hx + 2, oy + hy - 2, 1)
                g.px(ox + hx + 3, oy + hy - 2, 1)

    def frame(self, g: Gfx, open_q: float):
        """横披：绫子镶边（双线 + 网点）、两头画轴；open_q 展开到哪"""
        x1 = lerp(FX0 + 4, FX1, open_q)
        g.d.rectangle((FX0, FY0, x1, FY1), fill=1)
        g.d.rectangle((FX0 + 2, FY0 + 2, x1 - 2, FY1 - 2), fill=0)
        g.d.rectangle((FX0 + 3, FY0 + 3, x1 - 3, FY1 - 3), outline=1)
        pix.checker(g, (FX0 + 1, FY0 + 1, x1, FY0 + 2), 0.5, fill=0)
        pix.checker(g, (FX0 + 1, FY1 - 1, x1, FY1), 0.5, fill=0)
        for x in (FX0 - 2, x1):                                    # 轴头
            g.d.rectangle((x, FY0 - 2, x + 2, FY1 + 2), fill=1)
            g.d.line((x + 1, FY0 - 1, x + 1, FY1 + 1), fill=0)
            g.d.rectangle((x, FY0 - 3, x + 2, FY0 - 3), fill=1)
            g.d.rectangle((x, FY1 + 3, x + 2, FY1 + 3), fill=1)
        g.d.line(((FX0 + FX1) // 2, 0, FX0 + 10, FY0 - 1), fill=1)     # 挂绳
        g.d.line(((FX0 + FX1) // 2, 0, FX1 - 10, FY0 - 1), fill=1)
        return x1

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, enter: float = 1.0, close: float = 0.0):
        dt = self.clock.dt(t)
        on = enter >= 1
        e3 = enter * self.T["enter"]
        n = int(t // CYC) if on else 0
        k = t % CYC if on else 0.0
        dragon = n % 3 == 2
        # 地面
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        for x in range(-40, 168, 10):
            g.d.line((x, FLOOR + 1, x - 6, 63), fill=1)
        pix.checker(g, (0, FLOOR + 2, 128, 64), 0.25)
        # 画轴开合：0–2 展开，45–47 卷起
        if on:
            open_q = ease_out(span(k, 0, 2.0)) * (1 - ease_in(span(k, 45.0, 47.0)))
        else:
            open_q = ease_out(span(e3, 0.2, 2.0))
        open_q *= 1 - close
        x1 = self.frame(g, open_q)
        flown = span(k, DOT_EYE + 2.0, DOT_EYE + 6.0) if dragon and on else 0.0
        tip = None
        self.title = False
        if on and open_q > 0 and k >= 2.0:
            tip = self.painting(g, k, t, dragon, True, flown)
            if open_q < 1:                                        # 卷起：卷轴外面的画盖掉，轴头重画
                g.d.rectangle((x1 + 3, 0, FX1 + 4, FY1 + 4), fill=0)
                g.d.rectangle((x1, FY0 - 2, x1 + 2, FY1 + 2), fill=1)
                g.d.line((x1 + 1, FY0 - 1, x1 + 1, FY1 + 1), fill=0)
                tip = None
        # 点睛：闪白、闪电、龙破纸而出
        if dragon and on and DOT_EYE <= k < DOT_EYE + 6.0:
            if k < DOT_EYE + 1.0:
                tip = DRAGON[-1][0] + 2 + (k - DOT_EYE > 0.5), DRAGON[-1][1] - 2
            if abs(k - (DOT_EYE + 1.5)) < dt * 1.01:
                pix.flash(g)
            if DOT_EYE + 1.4 < k < DOT_EYE + 2.2:
                pix.shake(g, t, 2.0)
                xs = [100, 95, 104, 97, 108]
                pts = [(xs[i], i * 12) for i in range(5)]
                g.d.line(pts, fill=1, width=2)
            if flown > 0:                                         # 龙飞出画外
                q = flown ** 1.6
                ox, oy = IX - q * 60, IY - q * 70
                self.dragon(g, ox, oy, DRAGON, t * 2, True)
        # 小道士：捏剑指驱笔；点睛时吓一跳
        face = "normal"
        if dragon and on and DOT_EYE + 1.4 < k < DOT_EYE + 5.0:
            face = "wow"
        elif on and ALIVE[0] < k < ALIVE[1]:
            face = "happy" if (k % 6) < 3 else "normal"
        pointing = tip is not None
        if pointing:
            sx, sy = DX + 2, FLOOR - 15
            ax, ay = IX + tip[0] - sx, IY + tip[1] - sy
            L = max(math.hypot(ax, ay), 1)
            spr, at = put_arm(ax / L * 12, ay / L * 12, "pinch")
        else:
            spr, at = "down", None
        pop = ease_out_back(span(e3, 0.0, 0.5)) if not on else 1.0
        figure(g, DX, FLOOR + (1 - pop) * 10, t, arm=spr, arm_at=at, face=face)
        # 飞笔（笔尖拖墨星）
        if on and tip is not None and open_q >= 1:
            bx, by = IX + tip[0], IY + tip[1]
            pix.blit(g, BRUSH, bx, by - BRUSH.h + 1)
            if int(t * 30) % 4 == 0 and not (tip[0] > IW - 26 and tip[1] < 20):
                self.sparks.burst(bx + 2, by - 2, 1, 8, life=0.35, gravity=10)
        elif on and open_q < 1 or not on:                         # 笔歇在笔洗上
            pix.blit(g, BRUSH, 24, FLOOR - 16 + (0 if on else (1 - ease_out_back(span(e3, 1.6, 2.4))) * 10))
        g.d.rectangle((20, FLOOR - 8, 30, FLOOR - 1), fill=1)       # 笔洗（小几上）
        g.d.rectangle((22, FLOOR - 7, 28, FLOOR - 5), fill=0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 字：题款（画展开时才写）、画下的画诀
        if self.title and open_q >= 1:
            g.vtext(IX + IW - 9, IY + 1, "溪山", size=8)
        if on:
            plan = DPLAN if dragon else PLAN
            s = None
            for t0, t1, kind, data, saying in plan:
                if saying and t0 <= k < t1 + 0.6:
                    s = saying
            if ALIVE[0] <= k < ALIVE[1]:
                if dragon:
                    s = "点睛即飞去" if k > DOT_EYE + 1.0 else None
                else:
                    s = "澄怀观道" if k < 38.0 else "卧以游之"
            if s:
                label(g, (FX0 + FX1) // 2 + 6, FY1 + 4, s, align="center")
        return k, dragon, flown, open_q

    def mx(self, g: Gfx, t: float, k: float, dragon: bool, flown: float, open_q: float):
        if 0 < flown < 1:
            for x in range(8):
                y = 3.5 + math.sin(x * 0.9 - t * 8) * 2.5
                g.mx_set(x, int(round(y)))
                g.mx_set(x, int(round(y)) + 1)
            return
        g.mx[0, :int(open_q * 8)] = True
        g.mx[7, :int(open_q * 8)] = True
        cols = int(span(k, 2.0, 30.0) * 8)
        h = [2, 3, 5, 6, 4, 3, 4, 2]
        for x in range(min(cols, 8)):
            for y in range(7 - h[x], 7):
                g.mx[y, x] = (y == 7 - h[x]) or (x + y) % 2 == 0

    def enter(self, g: Gfx, t: float):
        out = self.scene(g, t, min(t / self.T["enter"], 0.999))
        self.mx(g, t, *out)

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.mx(g, t, *self.scene(g, t))

    def exit(self, g: Gfx, t: float):
        tt = self.ht + t
        q = t / self.T["exit"]
        out = self.scene(g, tt, close=ease_in(span(q, 0, 0.6)))
        self.mx(g, tt, *out)
        iris(g, span(q, 0.4, 1.0), 64, 30)
