"""曲水流觞：王羲之《兰亭集序》“引以为流觞曲水，列坐其次……一觞一咏，亦足以畅叙幽情”；
赋诗句取王羲之《兰亭诗》“仰视碧天际，俯瞰渌水滨……寓目理自陈”；“罚酒三觥”为兰亭修禊诗不成者罚酒的旧说。

暮春山阴：一条清溪从远处山脚弯弯曲曲流到眼前，小道士跽坐在近岸，对岸、弯里远远还坐着两位雅士；右边修竹摇曳。
入场：溪水从远处一路流进画面，小道士与两位雅士依次弹出坐定。
持续：羽觞（两耳椭圆杯）每 8 秒放下一只，顺水漂流打转；每第三只停在小道士面前的回水里：
      他伸手取觞、举杯仰饮，然后多半提笔在膝前纸上赋诗（左上角逐字写出一句），
      约三成作不出——“罚酒三觥”，连饮三杯、晕乎乎摇晃。放回空杯，杯子接着漂走。
      远处雅士也不时举杯；水纹一直流，竹叶沙沙，偶尔一对燕子掠过。
退场：收圆。
点阵：S 形溪流（流动的点）上漂着觞。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import TUFT, Clock, iris, label, put_arm, typed

DX, DF = 31, 47               # 小道士（跽坐，朝右）
SCH = (118, 41)               # 雅士（跽坐，朝左）
# 溪水中心线（略俯视的地面上一道 S 形）：从远处右上流进来，弯到左边，再折回右下，从画面下沿流出
PATH = [(134, 17), (110, 19), (84, 23), (62, 28), (48, 33), (46, 38), (56, 42), (76, 45), (94, 49), (100, 54),
        (92, 59), (74, 63), (64, 70)]
WIDTH = (4, 10)
BANK = 48
SPEED = 9.0                   # 杯子顺水的速度（像素/秒）
SPAWN = 8.0
STOP_X = 47                   # 回水处（小道士面前，弯里）
POEMS = ["仰视碧天际", "俯瞰渌水滨", "寓目理自陈", "一觞一咏", "畅叙幽情"]
EV_DRINK, EV_FINE = 9.5, 11.5
T0 = 18.0                     # 时间偏移：一开场水里就有杯子


def _arc():
    out, s = [0.0], 0.0
    for (x0, y0), (x1, y1) in zip(PATH, PATH[1:]):
        s += math.hypot(x1 - x0, y1 - y0)
        out.append(s)
    return out


ARC = _arc()
LEN = ARC[-1]


def at(s: float):
    """溪中心线上弧长 s 处 → (x, y, 宽度比例 0..1)"""
    s = max(0.0, min(s, LEN))
    for i in range(len(PATH) - 1):
        if s <= ARC[i + 1]:
            k = (s - ARC[i]) / max(ARC[i + 1] - ARC[i], 1e-6)
            x = lerp(PATH[i][0], PATH[i + 1][0], k)
            y = lerp(PATH[i][1], PATH[i + 1][1], k)
            return x, y, s / LEN
    return PATH[-1][0], PATH[-1][1], 1.0


def _stop_s():
    best, bs = 1e9, 0.0
    s = 0.0
    while s < LEN:
        x, y, _ = at(s)
        if abs(x - STOP_X) < best and 34 < y < 40:
            best, bs = abs(x - STOP_X), s
        s += 0.5
    return bs


S_STOP = _stop_s()


def band(s_max: float = LEN):
    """溪水的两岸折线（左岸 = 远岸，右岸 = 近岸）与水面多边形"""
    left, right = [], []
    s = 0.0
    while s <= s_max:
        x, y, k = at(s)
        x2, y2, _ = at(min(s + 1.5, LEN))
        x1, y1, _ = at(max(s - 1.5, 0))
        tx, ty = x2 - x1, y2 - y1
        n = math.hypot(tx, ty) or 1
        nx, ny = -ty / n, tx / n
        w = lerp(WIDTH[0], WIDTH[1], k) / 2
        left.append((x + nx * w, y + ny * w * 0.8))
        right.append((x - nx * w, y - ny * w * 0.8))
        s += 3.0
    return left, right


BAND = band()

LEAVES = pix.frames("""
  #
 ##  #
###.##
 # ###
---
  #  #
 ## ##
###.##
#   #
""")

CUP = pix.frames("""
#.###.#
 #####
---
 .###.
##.#.##
 .###.
""")


def _paper():
    p = Part(10, 3)
    p.shape("polygon", [(1, 0), (9, 0), (8, 2), (0, 2)], fill=1)
    p.px(3, 1, 0), p.px(5, 1, 0), p.px(6, 1, 0)
    return p.sprite()


def _cap():
    """雅士的纶巾 14×8（朝左）：暗色头巾裹住发髻，白边，两根巾带往后飘"""
    p = Part(16, 8)
    p.shape("ellipse", (2, 0, 12, 8), fill=1)
    p.d.ellipse((3, 1, 11, 7), fill=0)
    p.d.line((4, 4, 10, 4), fill=1)
    p.shape("rectangle", (1, 6, 13, 7), fill=1)
    return p.sprite()


def _beard():
    p = Part(5, 6)
    p.shape("polygon", [(0, 0), (4, 0), (3, 3), (2, 5), (1, 3)], fill=1)
    p.px(2, 1, 0), p.px(2, 2, 0)
    return p.sprite()


_P: dict = {}


def prop(name, *a):
    key = (name,) + a
    if key not in _P:
        _P[key] = {"paper": _paper, "cap": _cap, "beard": _beard}[name](*a)
    return _P[key]


@register
class Liushang(Rest):
    id = "x2.liushang"
    name = "曲水流觞"
    desc = "清溪蜿蜒，羽觞顺水漂流打转，停在小道士面前他就取觞饮酒、提笔赋诗，作不出就罚酒三觥"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    # ------------------------------------------------------------ 杯子与事件（全由 t 决定）

    def cups(self, t: float):
        """→ [(x, y, frame)] 正在漂的杯子；以及当前事件 (k, i, penalty) 或 None"""
        out, ev = [], None
        i0 = max(0, int((t - LEN / SPEED - 20) // SPAWN))
        for i in range(i0, int(t // SPAWN) + 1):
            age = t - i * SPAWN
            s = age * SPEED
            if i % 3 == 2:
                t_stop = S_STOP / SPEED
                pen = rand(i, self.seed) < 0.3
                dur = EV_FINE if pen else EV_DRINK
                if age >= t_stop:
                    k = age - t_stop
                    if k < dur:
                        ev = (k, i, pen)
                        if k < 0.9 or k > dur - 0.6:      # 停在回水里打转 / 放回去
                            x, y, _ = at(S_STOP)
                            out.append((x, y, int(t * 2) % 2))
                        continue
                    s = S_STOP + (k - dur) * SPEED
            if 0 <= s < LEN:
                x, y, _ = at(s)
                out.append((x, y + (1 if int(age * 1.5) % 2 else 0) * 0, int(age * 1.2 + i) % 2))
        return out, ev

    # ------------------------------------------------------------ 画面

    def land(self, g: Gfx, t: float, grow: float = 1.0):
        """远山、地面（零星草点）、S 形溪水（暗水面 + 亮岸线 + 顺流的水纹）、岸边卵石"""
        ridge = [(64, 14), (72, 8), (78, 11), (90, 3), (100, 9), (110, 5), (120, 10), (128, 8)]
        g.d.line(ridge, fill=1)
        g.d.line((90, 5, 87, 10), fill=1), g.d.line((110, 7, 108, 11), fill=1)
        g.d.line((0, 14, 127, 14), fill=1)                       # 地平
        for i in range(60):                                      # 地上的草点
            x = int(rand(i, 31) * 127)
            y = 16 + int(rand(i, 32) * 47)
            g.px(x, y)
            if i % 3 == 0:
                g.px(x + 1, y - 1)
        left, right = BAND if grow >= 1 else band(LEN * grow)
        if len(left) > 1:
            g.d.polygon(left + right[::-1], fill=0)
            g.d.line(left, fill=1)
            g.d.line(right, fill=1)
        # 水纹：顺水流动的短划
        smax = LEN * grow
        for j in range(26):
            ss = (j * 8.3 + t * SPEED * 0.9) % LEN
            if ss > smax - 2:
                continue
            x, y, k = at(ss)
            x2, y2, _ = at(min(ss + 2, LEN))
            off = (rand(j, 4) - 0.5) * lerp(WIDTH[0], WIDTH[1], k) * 0.5
            g.d.line((x, y + off, x2, y2 + off), fill=1)
        for x, y, w in ((40, 30, 4), (62, 50, 5), (104, 44, 3), (82, 56, 4)):   # 岸边卵石
            g.d.ellipse((x, y, x + w, y + 2), fill=1)
            g.d.line((x + 1, y + 2, x + w - 1, y + 2), fill=0)
        for x, y in ((24, 52), (66, 36), (114, 56), (8, 60)):
            pix.blit(g, TUFT[(x // 5) % 3], x, y, outline=False)
        self.bamboo(g, t)

    def bamboo(self, g: Gfx, t: float):
        """修竹：左边三竿（两像素粗，竹节一圈），竹叶一簇簇随风摆"""
        sway = math.sin(t * 0.8)
        for i, (x, top) in enumerate(((5, 2), (11, 9), (17, 16))):
            for y in range(top, BANK + 6):
                k = (BANK + 6 - y) / BANK
                xx = round(x + sway * 2 * k * k + i * 0.3)
                g.px(xx, y), g.px(xx + 1, y)
                if (y - top) % 7 == 3:
                    g.px(xx - 1, y), g.px(xx + 2, y), g.px(xx + 1, y + 1, 0)
            for j in range(3):
                ly = top + 3 + j * 9
                k = (BANK - ly) / BANK
                lx = x + sway * 2 * k * k
                spr = pix.anim(LEAVES, t * 0.5 + i * 0.7 + j * 0.3, 1.2)
                pix.blit(g, spr, lx + (1 if j % 2 else -6), ly, flip=j % 2 == 1, outline=False)

    def drink_pose(self, k: float, pen: bool):
        """事件 k 秒时手的位置（相对肩）、拿着什么、脸"""
        # 0–0.9 伸手取觞；0.9–1.6 举到嘴边；1.6–3.0 仰饮；3.0–3.5 放下
        cup_x, cup_y = STOP_X - (DX + 2), (at(S_STOP)[1] - 1) - (DF - 13)
        mouth = (4, -3)
        knee = (8, 8)
        if k < 0.9:
            q = ease_in_out(span(k, 0, 0.9))
            return lerp(knee[0], cup_x, q), lerp(knee[1], cup_y, q), None, "normal"
        if k < 1.6:
            q = ease_in_out(span(k, 0.9, 1.6))
            return lerp(cup_x, mouth[0], q), lerp(cup_y, mouth[1], q), "cup", "normal"
        if k < 3.0:
            return mouth[0], mouth[1] - (1 if k > 2 else 0), "cup", "sleep"
        if k < 3.5:
            q = ease_in_out(span(k, 3.0, 3.5))
            return lerp(mouth[0], 9, q), lerp(mouth[1], 9, q), "cup", "happy"
        end = EV_FINE if pen else EV_DRINK
        if not pen:       # 提笔赋诗（3.5–8.5），再把空杯放回水里
            if k < end - 1.0:
                wob = math.sin(k * 9) * 1.5
                return 10 + wob, 10 + (1 if int(k * 6) % 2 else 0), "brush", "normal"
        else:             # 作不出：罚酒三觥（3.5–10），一杯一仰头
            if k < end - 1.0:
                kk = (k - 3.5) % 2.2
                q = ease_in_out(span(kk, 0, 0.6)) * (1 - ease_in_out(span(kk, 1.5, 2.1)))
                return lerp(9, mouth[0], q), lerp(9, mouth[1], q), "horn", ("sleep" if q > 0.8 else "wow")
        q = ease_in_out(span(k, end - 1.0, end - 0.5))
        return lerp(9, cup_x, q), lerp(9, cup_y, q), "cup" if k < end - 0.6 else None, "happy"

    def scene(self, g: Gfx, t: float, enter: float = 1.0):
        dt = self.clock.dt(t)
        on = enter >= 1
        e3 = enter * self.T["enter"]
        self.land(g, t, 1.0 if on else span(e3, 0, 1.6) + 0.001)
        cups, ev = self.cups(t + T0) if on else ([], None)
        for x, y, fr in cups:
            pix.blit(g, CUP[fr], x - 3, y - 2)
        # 对面的雅士（纶巾、长须），隔一阵举杯自饮
        pop = ease_out_back(span(e3, 1.5, 1.9)) if not on else 1.0
        if pop > 0.05:
            q = (t + 5.0) % 19.0
            lift = ease_in_out(span(q, 0, 0.6)) * (1 - ease_in_out(span(q, 2.2, 2.8)))
            spr, at_ = put_arm(lerp(7, 4, lift), lerp(8, -3, lift), "fist", over=lift > 0.5)
            sx, sy = SCH

            def deco(gg, a):
                pix.blit(gg, prop("cap"), sx - 8, sy + (1 - pop) * 10 - 33, flip=True)
                pix.blit(gg, prop("beard"), sx - 6, sy + (1 - pop) * 10 - 16)

            h = figure(g, sx, sy + (1 - pop) * 10, t + 1.3, legs="kneel", arm=spr, arm_at=at_, flip=True,
                       face="sleep" if 0.8 < q < 2.2 else "normal", front=deco)
            hx, hy = h["hand"]
            pix.blit(g, CUP[0], hx - 3, hy - 2)
        # 燕子（偶尔一对掠过）
        bk = (t % 37) / 4.0
        if bk < 1:
            for j in range(2):
                bx = lerp(135, -10, bk) + j * 9
                by = 10 + j * 3 + math.sin(bk * 9 + j) * 2
                wing = int(t * 8 + j) % 2
                g.d.line((bx - 2, by - wing, bx, by), fill=1)
                g.d.line((bx, by, bx + 2, by - wing), fill=1)
        # 小道士
        face, tool = "normal", None
        dx, dy = 8, 8
        if ev:
            dx, dy, tool, face = self.drink_pose(ev[0], ev[2])
        sway_x = 0
        if ev and ev[2] and 4.0 < ev[0] < EV_FINE - 0.5:      # 罚酒：晕乎乎摇晃
            sway_x = round(math.sin(ev[0] * 4) * 1.4)
        pop = ease_out_back(span(e3, 0.9, 1.3)) if not on else 1.0
        if pop > 0.05:
            spr, at_ = put_arm(dx, dy, "pinch" if tool == "brush" else "fist", over=tool in ("cup", "horn") and dy < 2)

            def front(gg, a):
                if tool == "brush" or (ev and not ev[2] and 3.5 <= ev[0] < EV_DRINK):
                    pix.blit(gg, prop("paper"), DX + 7 + sway_x, DF - 3)

            h = figure(g, DX + sway_x, DF + (1 - pop) * 10, t, legs="kneel", arm=spr, arm_at=at_, face=face,
                       behind=front)
            hx, hy = h["hand"]
            if tool == "cup":
                pix.blit(g, CUP[0], hx - 3, hy - 2)
            elif tool == "horn":     # 觥：牛角形的大酒器
                g.d.line((hx - 1, hy - 2, hx + 4, hy - 4), fill=1, width=2)
                g.d.line((hx + 4, hy - 4, hx + 6, hy - 7), fill=1)
                g.px(hx - 2, hy - 2)
            elif tool == "brush":    # 笔
                g.d.line((hx + 1, hy - 4, hx + 1, hy + 2), fill=1)
                g.px(hx + 1, hy + 3)
        # 醉了：头上转小星
        if ev and ev[2] and 5.5 < ev[0] < EV_FINE - 0.6:
            for j in range(3):
                a = t * 4 + j * 2.1
                g.px(DX + math.cos(a) * 7, DF - 36 + math.sin(a) * 2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 字
        if ev:
            k, i, pen = ev
            if not pen and 3.6 <= k < EV_DRINK - 0.2:
                label(g, 30, 1, typed(POEMS[(i // 3) % len(POEMS)], k - 3.8, 1.6))
            elif pen and 3.6 <= k < EV_FINE - 0.4:
                label(g, 30, 1, "罚酒三觥")
        return cups, ev

    def mx(self, g: Gfx, t: float, cups):
        pts = [(1, 0), (2, 0), (3, 1), (4, 1), (5, 2), (6, 2), (6, 3), (5, 4), (4, 4), (3, 5), (2, 5), (1, 6),
               (2, 7), (3, 7), (4, 7), (5, 7), (6, 7)]
        for j, (x, y) in enumerate(pts):
            if (j - int(t * 4)) % 3:
                g.mx[y, x] = True
        for x, y, fr in cups:
            s = 0
            best = 1e9
            for j, (px_, py_) in enumerate(pts):
                X, Y = 64 + (px_ - 3.5) * 16, 26 + py_ * 4.2
                d = abs(X - x) + abs(Y - y)
                if d < best:
                    best, s = d, j
            x8, y8 = pts[s]
            g.mx[y8, x8] = int(t * 6) % 2 == 0
            if x8 + 1 < 8:
                g.mx[y8, x8 + 1] = True

    def enter(self, g: Gfx, t: float):
        self.scene(g, t, min(t / self.T["enter"], 0.999))
        self.mx(g, t, [])

    def hold(self, g: Gfx, t: float):
        self.ht = t
        cups, ev = self.scene(g, t)
        self.mx(g, t, cups)

    def exit(self, g: Gfx, t: float):
        tt = self.ht + t
        cups, ev = self.scene(g, tt)
        self.mx(g, tt, cups)
        iris(g, t / self.T["exit"], DX + 8, 34)
