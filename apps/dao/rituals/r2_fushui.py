"""化符入水：夜里院中，小道士一手拈着一道黄符横在清水碗上方，符从末端慢慢烧向指尖，符灰一片片落进碗里。

依据：符水——纸符“烧成灰与水一起吞服”；水咒“北方壬癸水……云雨须臾至……百病消除”；
治鲠等法“伸直中指和食指……在碗中水面写符”。北方壬癸属水，夜空画北斗。

舞台（侧视）：北斗七星、院墙瓦檐；左边小道士，中间三足架上一只清水碗，右边小几上烛台与一叠黄符。
入场：小道士拿着新符走到烛台前，把符的一头伸进烛火——“呼”地着了，火星一溅，再走回碗前。
持续：一轮 600 秒烧一道：符头在指尖、符脚朝外，火苗在符脚那头逐帧跳动，焦边往指尖退（随 e），
      烟团一路往上飘；每 9 秒一片符灰从焦边打着旋落进碗里，水面泛起一圈扁涟漪，碗里漂的灰越来越多；
      每 30 秒一个小事件：上前半步、另一只手剑指在水面画讳（“北方壬癸水”），或凑近吹一口气让火苗一窜。
      烧到最后剩指尖一角，松手落水，剑指画讳，一碗符水放光。续：走到小几前拈一道新符、烛上点着、回到碗前，“第几道”加一。
中断：把符提起来甩两下，火灭成一缕烟，“暂歇”。恢复：剑指一点，火星飞到符脚，重新烧起来。
圆满：剩下的符“呼”地烧完，大块灰落水，最后一角落下溅起水花，一碗符水放光，水气升腾，“百病消除”。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r2_common import (act, boxed, candle, fist, floor, fu_spr, ring, star4,
                        table_spr, vbox)

FLOOR = 58
DAO_X = 36
HAND = (DAO_X + 12, 38)          # 拈符的手
BOWL_X, BOWL_Y = 49, 44           # 碗（左上角，27×12）
WATER = (62, 46)                  # 水面中心
TAB_X, TAB_Y = 90, 50             # 矮几
CANDLE_X = 104
STACK_X = 93                      # 小几上的一叠黄符
LIGHT_X = 70                      # 点符时站的位置
FULL, STUB = 21, 3
FW = 9                            # 符纸宽
RENEW = 9.0
END = 585.0                       # 烧完（轮内）
ASH_EVERY = 9.0
CNT_X = 121
DIPPER = [(70, 9), (76, 7), (82, 9), (87, 12), (90, 18), (98, 19), (100, 13)]  # 北斗：天枢…摇光（斗口朝左）

FLAME = pix.frames("""
  #
  ##
 ###
#####
##.##
#...#
 #.#
---
 #
 ##
 ###
####
##.##
#...#
 #.#
---
   #
  #
 ###
 ####
##.##
#...#
 #.#
""")


# ---------------------------------------------------------------- 道具

_P: dict = {}


def paper(L: int, t: float) -> Sprite:
    """横拈的符（符头在左、靠指尖；符脚朝右）烧剩 L 列：右边两列焦黑（网点），焦边参差（随时间抖）"""
    L = max(1, min(FULL, int(L)))
    fr = int(t * 6) % 3
    key = ("paper", L, fr)
    s = _P.get(key)
    if s is None:
        base = fu_spr(FW, FULL).rot90(1)                    # 21×9，符头朝左
        on = base.on[:, :L].copy()
        mk = base.mask[:, :L].copy()
        if L < FULL:
            for y in range(FW):
                if L >= 2 and (y + fr) % 2 == 0:
                    on[y, L - 2] = False
                on[y, L - 1] = (y + fr) % 3 == 0
                if rand(y * 7 + fr, 3) < 0.35 and L > 2:
                    mk[y, L - 1] = on[y, L - 1] = False
        s = _P[key] = Sprite(on=on, mask=mk)
        if len(_P) > 200:
            _P.clear()
    return s


def _bowl() -> Sprite:
    """清水大碗 27×12（微俯视）：碗口一圈厚沿、里面一汪黑水、碗身一道回纹带、高光两点、背光网点、圈足"""
    p = Part(27, 12)
    p.shape("polygon", [(0, 2), (26, 2), (24, 6), (20, 10), (6, 10), (2, 6)], fill=1)
    p.shape("ellipse", (0, 0, 26, 5), fill=1)
    p.d.ellipse((2, 1, 24, 4), fill=0)                  # 水面
    p.d.line((3, 6, 23, 6), fill=0)                     # 回纹带上下两道
    p.d.line((5, 8, 21, 8), fill=0)
    for x in range(5, 22, 4):
        p.px(x, 7, 0), p.px(x + 1, 7, 0)
    p.dither([(17, 7), (25, 4), (20, 10), (16, 10)], 0.5, 0)
    p.px(6, 9, 0)
    p.shape("rectangle", (9, 11, 17, 11), fill=1)       # 圈足
    return p.sprite()


def _stand() -> Sprite:
    """碗下的木托 21×2：一道托板、三只短脚"""
    p = Part(21, 2)
    p.shape("rectangle", (1, 0, 19, 0), fill=1)
    for x in (2, 10, 18):
        p.px(x, 1)
    return p.sprite()


def _hills() -> Sprite:
    """远山 128×14：只画山脊一线，脊下一行稀点"""
    p = Part(128, 14)
    pts = [(0, 10), (10, 6), (18, 9), (30, 2), (44, 9), (56, 5), (70, 11), (84, 4), (96, 9), (108, 3), (120, 8), (127, 6)]
    p.shape("line", pts, fill=1)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for x in range(x0, x1, 3):
            y = y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1)
            p.px(x, int(y) + 2 + (x % 2))
    return p.sprite()


def prop(name):
    if name not in _P:
        _P[name] = {"stand": _stand, "bowl": _bowl, "hills": _hills}[name]()
    return _P[name]


def mx_draw(g: Gfx, L: float, lit: bool, t: float, ash: float | None = None, ripple: float | None = None, glow=False):
    """点阵：上面一道横符（越烧越短、末端火点闪），下面一只碗；落灰时一点往下掉，涟漪时水线向两边散"""
    n = 1 + int(round((L - STUB) / (FULL - STUB) * 5)) if L > 0 else 0
    for x in range(1, 1 + n):
        g.mx[2, x] = True
        g.mx[3, x] = x % 2 == 1
    if lit and n:
        g.mx[1, min(n + 1, 7)] = (t * 5) % 1 < 0.6
        g.mx[2, min(n + 1, 7)] = True
        if (t * 1.3) % 1 < 0.3:
            g.mx[0, min(n, 7)] = True
    g.mx[5, 0] = g.mx[5, 7] = True
    g.mx[6, 1] = g.mx[6, 6] = True
    g.mx[7, 2:6] = True
    if ash is not None:
        g.mx[3 + min(int(ash * 3), 2), 4] = True
    if ripple is not None:
        r = int(ripple * 3)
        g.mx[5, max(3 - r, 1)] = g.mx[5, min(4 + r, 6)] = True
    if glow:
        g.mx[5, 1:7] = True
        g.mx[4, 2] = g.mx[4, 5] = (t * 4) % 1 < 0.5


@register
class FuShui(Ritual):
    id = "r2.fushui"
    name = "化符入水"
    desc = "夜里院中，小道士拈一道黄符在清水碗上方，符从末端慢慢烧向指尖，符灰打着旋落进碗里泛起涟漪，隔一阵剑指在水面画讳"
    T = {"enter": 6.5, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.last_t = None
        self.fired: set = set()

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    def once(self, key) -> bool:
        if key in self.fired:
            return False
        if len(self.fired) > 200:
            self.fired.clear()
        self.fired.add(key)
        return True

    @staticmethod
    def burn(u: float) -> float:
        """轮内 u 秒时符剩下的长度"""
        return lerp(FULL, STUB, span(u, RENEW, END))

    # ------------------------------------------------------------ 舞台

    def stage(self, g: Gfx, t: float, lit: bool = True, stack: int = 3):
        for i in range(len(DIPPER) - 1):  # 北斗：星与星之间的虚线
            (x0, y0), (x1, y1) = DIPPER[i], DIPPER[i + 1]
            pix.dotted(g, x0, y0, x1, y1, step=3)
        pix.dotted(g, *DIPPER[3], *DIPPER[0], step=3)
        for i, (x, y) in enumerate(DIPPER):
            g.px(x, y)
            if (t * 0.7 + i * 0.37) % 3 > 0.3:
                star4(g, x, y)
        for i in range(12):  # 疏星
            x, y = int(rand(i, 5) * 112), int(rand(i, 6) * 22)
            if (t * 0.5 + rand(i, 7) * 9) % 4 > 0.6 and not (60 < x < 104 and y < 20) and not (y < 18 and x < 64):
                g.px(x, y)
        pix.blit(g, prop("hills"), 0, 28, outline=False)
        floor(g, FLOOR)
        pix.blit(g, table_spr(24, FLOOR - TAB_Y), TAB_X, TAB_Y)
        candle(g, CANDLE_X, TAB_Y, t, lit)
        for i in range(stack):  # 小几上一叠黄符
            g.d.line((STACK_X + (i % 2), TAB_Y - 1 - i, STACK_X + 7 + (i % 2), TAB_Y - 1 - i), fill=1)
        pix.blit(g, prop("stand"), BOWL_X + 3, BOWL_Y + 12)
        pix.blit(g, prop("bowl"), BOWL_X, BOWL_Y)

    def water(self, g: Gfx, u: float, t: float, burnt: float, glow: float = 0.0):
        """水面：漂着的灰（随烧掉的比例变多）、水光一闪一闪、落灰的涟漪（按 u 算，不用状态）"""
        cx, cy = WATER
        for j in range(int(burnt * 9)):
            x = cx + (rand(j, 21) - 0.5) * 18 + math.sin(t * 0.4 + j) * 1.2
            g.px(x, cy - 0.5 + (j % 2))
        gx = cx - 8 + (t * 3) % 16
        g.px(gx, cy - 1)
        for j in range(int(span(u, RENEW, END) * (END - RENEW) / ASH_EVERY) + 1):
            land = RENEW + j * ASH_EVERY + 5.4
            r = (u - land) / 1.6
            if 0 < r < 1:
                self.ripple(g, cx + (rand(j, 33) - 0.5) * 6, r)
        if glow > 0:
            for i in range(3):
                x = cx - 6 + i * 6 + math.sin(t * 3 + i) * 1.5
                if (t * 4 + i) % 1 < glow:
                    g.px(x, cy - 1), g.px(x, cy)

    def ripple(self, g: Gfx, x: float, r: float, big: float = 1.0):
        rx = 1 + r * 9 * big
        ry = max(0.5, rx * 0.22)
        n = int(rx * 4) + 6
        for i in range(0, n, 2):
            a = i / n * 2 * math.pi
            px, py = x + math.cos(a) * rx, WATER[1] + math.sin(a) * ry
            if abs(px - WATER[0]) < 11 - abs(py - WATER[1]) * 3:
                g.px(px, py)

    def flakes(self, g: Gfx, u: float, L: float):
        """正在往下掉的符灰（打着旋）"""
        for j in range(int(span(u, RENEW, END) * (END - RENEW) / ASH_EVERY) + 1):
            t0 = RENEW + j * ASH_EVERY + 4.0
            k = (u - t0) / 1.4
            if 0 <= k < 1:
                x0 = HAND[0] + 1 + self.burn(t0)
                x = lerp(x0, WATER[0] + (rand(j, 33) - 0.5) * 6, k) + math.sin(k * 9) * 1.5
                y = lerp(HAND[1] + 1, WATER[1] - 1, ease_in(k))
                if int(k * 8) % 2:
                    g.px(x, y), g.px(x + 1, y)
                else:
                    g.px(x, y), g.px(x, y + 1)
                return k
        return None

    def fu(self, g: Gfx, hand, L: float, t: float, lit: bool, dt: float, flare: float = 1.0, smoke: float = 1.0):
        """拈着的符 + 末端的火苗 + 烟团"""
        hx, hy = hand
        spr = paper(int(round(L)), t if lit else 0)
        pix.blit(g, spr, hx + 1, hy - 4)
        ex, ey = hx + 1 + spr.w, hy - 4
        if lit:
            f = pix.anim(FLAME, t, 8)
            if flare != 1.0:
                f = pix.stretch(f, flare, flare)
            pix.blit(g, f, ex - f.w // 2 - 1, ey + 4 - f.h)
            if smoke > 0 and int(t * 2.6) != int((t - dt) * 2.6):
                self.puffs.emit(ex - 1, ey - 5, vx=-3, vy=-8, life=2.0, rmax=1.6, spread=1)
        fist(g, hx, hy)
        g.px(hx + 1, hy - 1)                                  # 拈符的两指
        return ex, ey

    # ------------------------------------------------------------ 状态

    def state(self, u: float) -> dict:
        """轮内 u 秒：小道士站位、手、符长、是否着火、事件"""
        S = dict(x=DAO_X, hand=HAND, L=self.burn(u), lit=True, face="normal", pose=None, jz=None, flare=1.0,
                 drop=None, glow=0.0, phrase=False)
        if u >= END:  # 最后一角落水 → 剑指画讳 → 符水放光
            f = u - END
            S["L"] = STUB
            if f < 0.8:
                S["hand"] = (HAND[0], HAND[1] - 2 * math.sin(f / 0.8 * math.pi))
            else:
                S.update(lit=False, L=0, hand=None, drop=f - 0.8)
                S["pose"] = "idle"
                if 2.2 < f < 7.0:
                    S["pose"] = None
                    S["x"] = DAO_X + 6 * span(f, 2.2, 2.6)
                    a = (f - 2.6) * 4
                    r = 4 * span(f, 2.6, 3.0)
                    S["jz"] = (WATER[0] - 4 + math.cos(a) * r, WATER[1] - 1 + math.sin(a) * r * 0.3)
                    S["trail"] = (a, r)
                    S["phrase"] = True
                elif f >= 7.0:
                    S["pose"] = "gongshou" if f < 11 else ("bow" if f < 12.4 else "idle")
                    S["face"] = "happy"
                S["glow"] = span(f, 4.0, 6.0)
            return S
        ph = (u - RENEW) % 30 if u >= RENEW else -1
        if 12.0 < ph < 16.0:                      # 闭目念水咒：三点灵光绕碗转，水面泛光
            S["face"] = "sleep"
            S["orbit"] = ph - 12.0
            S["phrase"] = True
            S["glow"] = 0.3 if 12.5 < ph < 15.5 else 0.0
        elif 24.0 < ph < 25.6:                    # 凑近吹一口气，火苗一窜
            S["face"] = "wow"
            S["flare"] = 1 + 0.5 * math.sin(span(ph, 24.3, 25.3) * math.pi)
            S["blow"] = ph - 24.0
        elif 6.0 < ph < 7.0:
            S["face"] = "happy"
        if u < RENEW:
            S["phrase"] = True
        return S

    # ------------------------------------------------------------ 画

    def draw_state(self, g: Gfx, t: float, u: float, S: dict, dt: float, stack: int = 3):
        self.stage(g, t, stack=stack)
        burnt = 1 - (S["L"] - STUB) / (FULL - STUB) if S["L"] > 0 else 1.0
        self.water(g, u, t, burnt, S["glow"])
        ash = self.flakes(g, u, S["L"]) if u < END else None
        if S["drop"] is not None:  # 最后一角落水
            k = S["drop"] / 0.6
            if k < 1:
                pix.blit(g, paper(STUB, 0), HAND[0] + 1, lerp(HAND[1] - 3, WATER[1] - 2, ease_in(k)))
            r = (S["drop"] - 0.6) / 1.8
            if 0 < r < 1:
                self.ripple(g, WATER[0] - 6, r, 1.2)
                self.ripple(g, WATER[0] - 6, max(r - 0.3, 0), 1.2)
            if S["drop"] > 0.6 and self.once(("splash", round((u - S["drop"]) * 10))):
                self.sparks.burst(WATER[0] - 6, WATER[1] - 1, 8, 18, up=14, life=0.5, gravity=80)
        if S["glow"] > 0.5:  # 符水放光：碗口上方几道光、水气升起
            for i in range(5):
                x = WATER[0] - 8 + i * 4
                h = 2 + ((int(t * 6) + i) % 3)
                g.d.line((x, BOWL_Y - 2, x, BOWL_Y - 2 - h), fill=1) if i % 2 == int(t * 3) % 2 else None
            if int(t * 1.5) != int((t - dt) * 1.5):
                self.puffs.emit(WATER[0] + (rand(int(t), 9) - 0.5) * 10, BOWL_Y - 3, vx=0, vy=-5, life=1.6, rmax=1.4)
        if S["pose"]:
            daoshi(g, S["x"], FLOOR, S["pose"], t, face=S["face"])
        else:
            if S["hand"] is None:
                if S["jz"]:  # 剑指在水面画讳
                    jx, jy = S["jz"]
                    h = act(g, S["x"], FLOOR, t, hand_to=(WATER[0] - 6, 36), face=S["face"])["hand"]
                    g.d.rectangle((h[0] - 1, h[1] + 1, h[0] + 2, h[1] + 5), fill=0)
                    g.d.line((h[0], h[1] + 1, h[0], h[1] + 4), fill=1)        # 剑指朝下：食指、中指
                    g.d.line((h[0] + 1, h[1] + 1, h[0] + 1, h[1] + 4), fill=1)
                    pix.dotted(g, h[0] + 0.5, h[1] + 6, jx, jy - 1, step=2, phase=int(t * 12))
                    if S.get("trail"):
                        a0, r = S["trail"]
                        for j in range(12):
                            aa = a0 - j * 0.35
                            g.px(WATER[0] - 4 + math.cos(aa) * r, WATER[1] + math.sin(aa) * r * 0.3)
                    if int(t * 4) % 2:
                        star4(g, jx + 2, jy - 2)
                else:
                    daoshi(g, S["x"], FLOOR, "idle", t)
            else:
                h = act(g, S["x"], FLOOR, t, hand_to=S["hand"], face=S["face"])["hand"]
                self.fu(g, h, S["L"], t, S["lit"], dt, flare=S["flare"])
        if S.get("orbit") is not None:  # 三点灵光绕碗
            k = S["orbit"]
            for j in range(3):
                a = k * 2.4 + j * 2.09
                r = 15 * min(k * 2, 1, (4 - k) * 2)
                if r > 1:
                    star4(g, WATER[0] + math.cos(a) * r, WATER[1] + 2 + math.sin(a) * r * 0.35, big=j == int(k * 3) % 3)
        if S.get("blow") is not None:
            b = S["blow"]
            for j in range(3):
                q = b * 1.4 - j * 0.2
                if 0 < q < 1:
                    g.px(S["x"] + 8 + q * 6, 33 + j + q * 2)
            if 0.4 < b < 0.5 and self.once(("blow", round(u))):
                ex = HAND[0] + 1 + S["L"]
                self.sparks.burst(ex, HAND[1] - 5, 6, 16, up=10, life=0.5, gravity=30)
        self.puffs.step(dt, wind=math.sin(t * 0.3) * 2)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        rip = None
        for j in range(int(span(u, RENEW, END) * (END - RENEW) / ASH_EVERY) + 1):
            r = (u - (RENEW + j * ASH_EVERY + 5.4)) / 1.6
            if 0 < r < 1:
                rip = r
        mx_draw(g, S["L"], S["lit"], t, ash=ash, ripple=rip, glow=S["glow"] > 0.5)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        vbox(g, CNT_X, 10, label or ("第" + (cn_num(n) if n < 100 else str(n)) + "道"))

    def phrase(self, g: Gfx, s: str = "北方壬癸水"):
        g.text(3, 5, s)

    # ------------------------------------------------------------ 点符（入场 / 续）

    def light(self, g: Gfx, t: float, k: float, e: float, dt: float, from_x: float = DAO_X):
        """k ∈ [0, 6.5]：走到小几（0–1.2）→ 拈符（1.2–1.8）→ 伸进烛火（1.8–2.4）→ 着火（2.8）→ 走回（3.4–5.2）→ 放到碗上（5.2–6.5）"""
        self.stage(g, t, stack=3 if k < 1.6 else 2)
        self.water(g, 0, t, 0.0 if from_x != DAO_X else 0.0)
        lit = k >= 2.8
        if k < 1.2:
            x = lerp(from_x, LIGHT_X + 12, ease_in_out(span(k, 0, 1.2)))
            daoshi(g, x, FLOOR, "walk" if k < 1.15 else "idle", t)
        elif k < 1.8:
            q = span(k, 1.2, 1.6)
            hand = (lerp(LIGHT_X + 20, STACK_X + 2, ease_out(q)), lerp(46, TAB_Y - 3, ease_out(q)))
            hand = act(g, LIGHT_X + 12, FLOOR, t, hand_to=hand)["hand"]
            if k > 1.6:
                self.fu(g, hand, FULL, t, False, dt)
        elif k < 3.4:
            q = ease_in_out(span(k, 1.8, 2.4))
            x = lerp(LIGHT_X + 12, LIGHT_X, q)
            hand = (lerp(STACK_X + 2, LIGHT_X + 12, q), lerp(TAB_Y - 3, 37, q))
            hand = act(g, x, FLOOR, t, hand_to=hand, face="wow" if 2.6 < k < 3.2 else "normal")["hand"]
            self.fu(g, hand, FULL, t, lit, dt)
            if 2.8 <= k < 2.8 + dt * 1.5 and self.once(("ignite", round(e), round(t))):
                self.sparks.burst(hand[0] + 1 + FULL, hand[1] - 3, 12, 22, up=12, life=0.6, gravity=40)
                self.puffs.emit(hand[0] + FULL, hand[1] - 6, vy=-6, life=0.8, rmax=2.2, spread=0)
        else:
            q = ease_in_out(span(k, 3.4, 5.2))
            x = lerp(LIGHT_X, DAO_X, q)
            hand = (x + 12, lerp(37, HAND[1], ease_out(span(k, 4.6, 5.6))))
            if k < 5.2:
                hand = act(g, x, FLOOR, t, hand_to=hand, legs="walk")["hand"]
            else:
                hand = act(g, x, FLOOR, t, hand_to=hand, face="happy" if k > 5.8 else "normal")["hand"]
            self.fu(g, hand, FULL, t, True, dt)
        self.puffs.step(dt, wind=math.sin(t * 0.3) * 2)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_draw(g, FULL if k > 1.6 else 0, lit, t)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        if t < 1.0:  # 走进来
            self.stage(g, t)
            self.water(g, 0, t, 0.0)
            daoshi(g, lerp(-12, DAO_X, ease_out(span(t, 0, 1.0))), FLOOR, "walk", t)
            mx_draw(g, 0, False, t)
        else:
            self.light(g, t, (t - 1.0) * 6.5 / 5.5, 0.0, dt)
        self.counter(g, 0.0)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            k = u / RENEW * 6.5
            self.light(g, t, k, e, dt)
            self.counter(g, e if k > 2.8 else e - u - 1)
            return
        S = self.state(u)
        self.draw_state(g, t, u, S, dt)
        if S["phrase"]:
            self.phrase(g)
        self.counter(g, e)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        S = dict(self.state(u if not (e >= self.CYCLE and u < RENEW) else RENEW))
        S.update(jz=None, flare=1.0, phrase=False, x=DAO_X)
        S.pop("blow", None)
        if S["hand"] is not None and S["L"] > 0:
            shake = math.sin(span(t, 0.2, 0.9) * 4 * math.pi) * 3 if t < 0.9 else 0
            S["hand"] = (HAND[0], HAND[1] - 6 * ease_out(span(t, 0, 0.3)) + shake + 6 * span(t, 1.0, 1.4))
            S["lit"] = t < 0.7
            S["face"] = "sleep" if t > 1.2 else "normal"
            if 0.7 <= t < 0.7 + dt * 1.5 and self.once(("out", round(e))):
                ex = HAND[0] + 1 + S["L"]
                self.puffs.emit(ex, S["hand"][1] - 4, vy=-6, life=1.2, rmax=2.0, spread=0)
        self.draw_state(g, t, u, S, dt)
        self.counter(g, e, "暂歇")

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        S = dict(self.state(u))
        S.update(phrase=False)
        if S["hand"] is not None and S["L"] > 0 and S["lit"]:
            ex, ey = HAND[0] + 1 + S["L"], HAND[1] - 3
            q = span(t, 0.3, 1.0)
            S["lit"] = t >= 1.0
            S["face"] = "normal" if t < 1.0 else "happy"
            self.draw_state(g, t, u, S, dt)
            if 0 < q < 1:
                star4(g, lerp(CANDLE_X, ex, q), lerp(TAB_Y - 17, ey, q) - math.sin(q * math.pi) * 12, big=True)
            if 1.0 <= t < 1.0 + dt * 1.5 and self.once(("relit", round(e))):
                self.sparks.burst(ex, ey, 12, 22, up=12, life=0.6, gravity=40)
                pix.flash(g)
        else:
            self.draw_state(g, t, u, S, dt)
        self.counter(g, e)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        L0 = self.burn(u) if RENEW <= u < END else FULL if u < RENEW else STUB
        S = dict(self.state(RENEW + 1))
        S.update(phrase=False, jz=None)
        L = lerp(L0, STUB, ease_in(span(t, 0, 1.4)))
        S["L"] = L
        S["flare"] = 1.5 if t < 1.4 else 1.0
        if t >= 1.4:
            S["drop"] = t - 1.4
            S.update(lit=False, L=0, hand=None, pose="gongshou" if t < 3.0 else ("bow" if t < 4.4 else "gongshou"),
                     face="happy")
            S["glow"] = span(t, 2.0, 2.6)
        self.draw_state(g, t, END + (t if t >= 1.4 else 0), S, dt)
        if t < 1.4 and int(t * 10) % 3 == 0:  # 大块灰落水
            x = HAND[0] + 1 + L
            self.sparks.burst(x, HAND[1], 2, 8, life=0.6, gravity=60)
        if 2.0 <= t < 2.0 + dt * 1.5 and self.once(("cflash", round(e))):
            pix.flash(g)
            self.sparks.burst(WATER[0], WATER[1] - 2, 24, 36, up=16, life=1.0, gravity=30)
        if t > 2.0:
            for j in range(3):
                r = (t - 2.0) * 16 - j * 7
                if r > 0:
                    ring(g, WATER[0], WATER[1] - 2, 10 + r, step=2, sy=0.45)
            g.mx_level = 1 + int(6 * (1 - span(t, 2.0, 3.6)))
        if t > 2.4:
            boxed(g, 4, 6, "百病消除", size=12, pop=ease_out_back(span(t, 2.4, 2.8)))
        self.counter(g, e, "符成" if t > 2.0 else None)
