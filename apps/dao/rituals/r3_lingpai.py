"""令牌拍案：小道士站在法案边，抓起五雷令牌高高举起、“啪”地拍在案上——案面一震、尘起、火星迸、旗筒跳；
五营令旗随计时一面面飞来插进旗筒。

五雷令牌为长方木牌，正面刻“令”或“五雷号令”，明《上清灵宝济度大成金书》载其以雷击枣木制成。
行法时以令牌击案、调遣兵将。民间道坛与闾山法有东、南、西、北、中“五营兵马”的说法。

入场：法案上立着令牌，小道士走到案边，抓起令牌举过头，第一拍：冲击线、扬尘、震屏；桌帷上现“五营兵马”。
持续：每 10 秒拍一次案（举起 → 一顿 → 猛拍 → 余震），拍案之间令牌边框上一点灵光绕行，牌顶冒灵气。
      一轮 600 秒，东南西北中五营令旗各在一次拍案后飞来插进旗筒（桌帷上写“某营兵马到”）。
      续：五面令旗一齐飞出画外（“五营齐发”），旗筒空了，从头点兵。
中断：令牌向后倒下卧在案上，令旗垂下，写“收令”。  恢复：手把令牌扶起，灵光一闪。
圆满：连拍三下，一下比一下重，五营令旗齐到，令牌放光，令旗升天，题“五雷号令”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_back, lerp, span
from ..engine.chars import daoshi
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r3_kit import (FLOOR, Clock, art, banner, banner_text, crossed, floor, hit, mx_ring, pose_arm, put,
                     rays, rot_spr, round_of, sparkle)

DX = 30
TX0, TX1, TY = 40, 112, 40          # 法案：左右、桌面 y
PX = 50                             # 令牌立在案上的中心 x
HOLDER = 92                         # 旗筒中心 x
CYCLE = 600.0
SLAM = 10.0
YING = ["东营", "南营", "西营", "北营", "中营"]
ARRIVE = [100 + 110 * i for i in range(5)]     # 本轮第几秒那一拍之后到一营（取最近的拍）
RENEW = 6.0

def _plaque():
    """五雷令牌 15×21：拱顶、双线边框、正中阴刻一个“令”字（取 12px 字形逐像素刻上去）、底座一道"""
    import numpy as np
    from ..engine.chars import Part
    from ..engine.gfx import Sprite, _text_img
    p = Part(15, 21)
    p.shape("polygon", [(0, 3), (3, 0), (11, 0), (14, 3), (14, 20), (0, 20)], fill=1)
    p.d.line((3, 1, 11, 1), fill=0)                  # 拱顶内线
    p.px(2, 2, 0), p.px(12, 2, 0)
    p.d.line((1, 3, 1, 16), fill=0)                  # 边框
    p.d.line((13, 3, 13, 16), fill=0)
    p.d.line((1, 16, 13, 16), fill=0)
    p.d.line((0, 18, 14, 18), fill=0)                # 底座
    glyph = np.array(_text_img("令", 12, 1), bool)[:11, :11]
    for y, x in zip(*np.nonzero(glyph)):
        p.px(int(x) + 2, int(y) + 3, 0)
    p.px(7, 15, 0)
    p.dither([(11, 19), (14, 19), (14, 20), (11, 20)], 0.5, 0)
    s = Sprite(on=np.array(p.on, bool), mask=np.array(p.mk, bool))
    s.anchor = (7, 20)
    s.pts = {"grip": (0, 11), "top": (7, 0)}
    return s


PLAQUE = _plaque()

HOLD = art("""
#########
 #######
 .......
 ###.###
 ##.####
 .......
 #######
#########
""", anchor=(4, 7))

FLAG = [art("""
######
#####
###
#####
######
""", anchor=(0, 0)), art("""
#####
######
####
######
#####
""", anchor=(0, 0))]

DROOP = art("""
##
###
###
##
##
#
""", anchor=(0, 0))

BURNER = art("""
  #  #  #
  #  #  #
#.#######.#
###########
 ######.#.
 #####.#.#
  #######
  #     #
""", anchor=(5, 7))

MX_PLAQUE = """
.####.
######
#....#
#.##.#
#....#
######
"""


def table(g: Gfx, t: float, jump: float = 0.0):
    """法案：案面（两道线）、案腿、桌帷（深色，镶边、下摆流苏）"""
    j = int(round(jump))
    g.d.rectangle((TX0 - 2, TY - j, TX1 + 2, TY + 2 - j), fill=1)
    g.d.line((TX0 - 1, TY + 1 - j, TX1 + 1, TY + 1 - j), fill=0)
    g.d.rectangle((TX0, TY + 3, TX1, FLOOR - 1), fill=0, outline=1)
    g.d.line((TX0 + 2, TY + 4, TX1 - 2, TY + 4), fill=1)
    for x in range(TX0 + 2, TX1 - 1, 2):     # 流苏
        g.px(x, FLOOR - 1, 0)
    g.d.rectangle((TX0, FLOOR - 1, TX0 + 2, FLOOR), fill=1)
    g.d.rectangle((TX1 - 2, FLOOR - 1, TX1, FLOOR), fill=1)


def flags(g: Gfx, n: int, t: float, droop: bool = False, lift: float = 0.0, jump: float = 0.0, new: int = -1,
          newk: float = 1.0):
    """旗筒里的令旗（扇形插开），n = 已到几面；new 号那面正在飞来（newk 0..1）"""
    j = int(round(jump))
    base = (HOLDER, TY - 8 - j)
    tops = [(HOLDER - 14, 16), (HOLDER - 7, 12), (HOLDER, 10), (HOLDER + 7, 12), (HOLDER + 14, 16)]
    for i in range(n):
        tx, ty = tops[i]
        sx, sy = base[0] + (tx - base[0]) * 0.25, base[1]
        off = lift * (60 + i * 6)
        if i == new:
            off += (1 - ease_out_back(newk)) * 46
        ty -= off
        sy -= off
        if droop:
            ty += 3
        g.d.line((sx, sy, tx, ty), fill=1)
        g.px(tx, ty - 1)
        f = DROOP if droop else FLAG[int(t * 4 + i) % 2]
        put(g, f, tx + (0 if droop else 1), ty)
        # 各营旗面花样：东实、南网点、西空心、北一道、中十字
        if not droop:
            if i == 1:
                for yy in range(1, 4):
                    g.px(tx + 2 + yy % 2, ty + yy, 0)
            elif i == 2:
                g.d.line((tx + 2, ty + 2, tx + 3, ty + 2), fill=0)
            elif i == 3:
                g.d.line((tx + 1, ty + 2, tx + 4, ty + 2), fill=0)
            elif i == 4:
                g.px(tx + 3, ty + 1, 0), g.px(tx + 3, ty + 3, 0), g.px(tx + 2, ty + 2, 0), g.px(tx + 4, ty + 2, 0)
    put(g, HOLD, base[0], base[1] + 7)


@register
class LingpaiRitual(Ritual):
    id = "r3.lingpai"
    name = "令牌拍案"
    desc = "小道士抓起五雷令牌高举、猛拍法案，案震尘起火星迸；五营令旗随计时一面面飞来插进旗筒"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.8}
    CYCLE = CYCLE

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.clock = Clock()

    # ------------------------------------------------------------ 公用

    def arrived(self, k: float) -> int:
        return sum(1 for a in ARRIVE if k >= self.slam_after(a) + 0.6)

    @staticmethod
    def slam_after(a: float) -> float:
        """a 秒之后最近的一拍的拍下时刻"""
        return math.ceil((a - 1.4) / SLAM) * SLAM + 1.4

    def slam_pose(self, u: float):
        """一拍（u = 本拍已过秒数）→ (手臂, 令牌在手里的角度, 抬高, 表情)。1.4 秒时拍下"""
        if u < 0.5:        # 握住（令牌立在案上）
            return "reach", 0, 0, "normal"
        if u < 1.0:        # 举起
            return "up60", 0, 0, "normal"
        if u < 1.3:        # 一顿（举到最高，蓄力）
            return "up90", 0, 0, "wow"
        if u < 1.4:        # 拍下（中途帧）
            return "up30", 0, 0, "wow"
        return "reach", 0, 0, "wow" if u < 2.0 else "normal"

    def actor(self, g: Gfx, t: float, arm: str, tilt: float, face: str, plaque=True, dy=0, glow=False,
              border: float = -1.0, lying: bool = False):
        """小道士 + 手里（或立在案上）的令牌"""
        out = {}

        def prop(g2, h):
            if not plaque:
                return
            spr = rot_spr(PLAQUE, tilt)
            gx, gy = spr.pts["grip"]
            ax, ay = spr.anchor
            if arm == "reach":   # 手扶着立在案上的令牌
                x, y = PX, TY + 1 + dy
            else:
                x, y = h[0] + (ax - gx), h[1] + (ay - gy)
            out["pts"] = put(g2, spr, x, y)
            out["xy"] = (x, y)
            if 0 <= border <= 1:   # 边框上绕行的一点灵光
                bx0, by0 = x - ax + 1, y - ay + 3
                per = [(bx0 + 2 + i, by0 - 2) for i in range(9)] + [(bx0 + 12, by0 + i) for i in range(14)] + \
                      [(bx0 + 12 - i, by0 + 13) for i in range(13)] + [(bx0, by0 + 13 - i) for i in range(14)]
                p = per[int(border * len(per)) % len(per)]
                g2.px(*p, 1)
                g2.px(*per[(int(border * len(per)) + 1) % len(per)], 1)
            if glow:
                sparkle(g2, x - ax + 2, y - ay + 1, 2)
        if lying:
            pose_arm(g, DX, "low", t, "fist")
            spr = rot_spr(PLAQUE, -90)
            out["pts"] = put(g, spr, PX + 4, TY)
        else:
            pose_arm(g, DX, arm, t, "fist", face=face, prop=prop, prop_behind=False)
        return out

    def impact(self, g: Gfx, t: float, power: float = 1.0):
        """拍下的一瞬：冲击线、扬尘、火星"""
        x, y = PX, TY
        self.sparks.burst(x, y - 2, int(8 + 8 * power), 30 + 14 * power, up=16, life=0.6, gravity=90)
        for s in (-1, 1):
            self.puffs.emit(x + s * 9, y - 2, vx=s * 16 * power, vy=-3, life=0.6, rmax=1.0 + power * 0.4)

    def impact_lines(self, g: Gfx, k: float, power: float = 1.0):
        """冲击线（k 0..1）"""
        if 0 <= k < 1:
            x, y = PX, TY - 2
            r0 = 8 + k * 10 * power
            for a in (-160, -135, -110, -70, -45, -20):
                c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
                g.d.line((x + c * r0, y + s * r0 * 0.7, x + c * (r0 + 4), y + s * (r0 + 4) * 0.7), fill=1)
            hit(g, x - 10, y - 2, k)
            hit(g, x + 10, y - 2, k)

    def fx(self, g: Gfx, dt: float):
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def cloth(self, g: Gfx, s: str):
        g.text((TX0 + TX1) / 2, TY + 6, s, align="center")

    def mx(self, g: Gfx, n: int, lift: int = 0, slam: bool = False):
        g.mx_blit(MX_PLAQUE, 1, 1 - lift)
        for i in range(n):
            g.mx[0, 7] = g.mx[2, 7] = g.mx[4, 7] = g.mx[6, 7] = False
        for i, (x, y) in enumerate(((7, 1), (7, 3), (7, 5), (6, 7), (4, 7))):
            if i < n:
                g.mx[y, x] = True
        if slam:
            g.mx[7, :] = True

    def burner(self, g: Gfx, t: float, jump: float = 0.0):
        put(g, BURNER, TX1 - 8, TY - 1 - int(round(jump)))
        x = TX1 - 8
        for i in range(3):   # 三缕细烟
            yy = TY - 8 - i * 3 - (t * 4) % 3
            g.px(x - 2 + i * 2 + int(math.sin(t * 2 + i) * 1.2), yy)

    # ------------------------------------------------------------ 阶段

    def scene(self, g: Gfx, t: float, e: float, dt: float, k: float, n: int, u: float, power: float = 1.0,
              new: int = -1, newk: float = 1.0, text: str | None = None):
        """一帧：u = 本拍已过秒数（None = 不拍，只扶着令牌）"""
        floor(g)
        jump = 0.0
        if u is not None and 1.4 <= u < 1.75:
            jump = math.sin(span(u, 1.4, 1.75) * math.pi) * 2 * power
        arm, tilt, _, face = self.slam_pose(u) if u is not None else ("reach", 0, 0, "normal")
        if u is not None and crossed(u, dt, 1.4):
            self.impact(g, t, power)
        self.actor(g, e, arm, tilt, face, border=((e * 0.35) % 1) if (u is None or u > 2.2) else -1)
        table(g, t)
        self.burner(g, e, jump * 1.5)
        flags(g, n, e, jump=jump * 1.5, new=new, newk=newk)
        if u is not None and arm == "up30":   # 拍下的中途：残影
            from .r3_kit import smear
            smear(g, DX + 6, FLOOR - 26, 18, 6, -100, -10, solid=0.5)
        if u is not None and 1.4 <= u < 1.8:
            self.impact_lines(g, (u - 1.4) / 0.4, power)
        if u is not None and 1.4 <= u < 1.6:
            pix.shake(g, t, 1.0 + power * 0.6)
        if u is None or u > 2.2:   # 牌顶冒灵气
            if int(e * 2.5) != int((e - dt) * 2.5):
                self.puffs.emit(PX, TY - 23, vx=0, vy=-6, life=1.4, rmax=1.2, spread=2)
        self.fx(g, dt)
        self.cloth(g, text or "五营兵马")
        return jump

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        if t < 2.2:
            floor(g)
            x = lerp(-14, DX, ease_out(span(t, 0, 2.2)))
            daoshi(g, x, FLOOR, "walk", t)
            put(g, PLAQUE, PX, TY + 1)
            table(g, t)
            self.burner(g, t)
            flags(g, 0, t)
            self.fx(g, dt)
            self.cloth(g, "法案")
            self.mx(g, 0)
            return
        u = t - 2.2 + 0.0
        self.scene(g, t, t, dt, 0, 0, u * 1.0, power=1.2, text="五营兵马" if u > 1.4 else "法案")
        self.mx(g, 0, slam=1.4 <= u < 1.6)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n_round, k, _ = round_of(e, CYCLE)
        if e >= CYCLE and k < RENEW:
            self.renew(g, k, t, e, dt)
            return
        n = self.arrived(k)
        u = e % SLAM
        new, newk, text = -1, 1.0, None
        for i, a in enumerate(ARRIVE):   # 刚到的那营：令旗从天上飞来插进旗筒
            s = self.slam_after(a)
            if s <= k < s + 4.0:
                new, newk = i, span(k - s, 0.0, 0.6)
                n = i + 1
                text = f"{YING[i]}兵马到"
        self.scene(g, t, e, dt, k, n, u, new=new, newk=newk, text=text)
        if new >= 0 and crossed(newk, dt, 1.0) or (new >= 0 and 0.6 <= k - self.slam_after(ARRIVE[new]) < 0.6 + dt):
            tops = [(HOLDER - 14, 16), (HOLDER - 7, 12), (HOLDER, 10), (HOLDER + 7, 12), (HOLDER + 14, 16)]
            self.sparks.burst(tops[new][0] + 3, tops[new][1] + 2, 6, 18, life=0.5)
        self.mx(g, n, lift=1 if 0.5 <= u < 1.4 else 0, slam=1.4 <= u < 1.6)

    def renew(self, g: Gfx, k: float, t: float, e: float, dt: float):
        """k ∈ [0, RENEW)：五营令旗一齐飞出画外（五营齐发），旗筒空，再从头点兵"""
        floor(g)
        self.actor(g, e, "up60" if k < 2.6 else "reach", 0, "happy" if k < 3.5 else "normal", glow=k < 2.6)
        table(g, t)
        self.burner(g, e)
        lift = ease_in(span(k, 0.6, 2.4))
        flags(g, 5 if k < 2.4 else 0, e, lift=lift)
        if k < 2.4 and int(k * 20) % 2 == 0:
            for i, x in enumerate((HOLDER - 14, HOLDER - 7, HOLDER, HOLDER + 7, HOLDER + 14)):
                self.sparks.burst(x, 20 - lift * 60 + 10, 1, 8, life=0.4, gravity=-10)
        self.fx(g, dt)
        self.cloth(g, "五营齐发" if k < 3.5 else "五营兵马")
        self.mx(g, 5 if k < 2.4 else 0)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        floor(g)
        n = self.arrived(e % CYCLE)
        fall = span(t, 0.2, 0.7)
        if fall < 1:
            self.actor(g, e, "reach", -int(fall * 90 / 15) * 15 if fall > 0 else 0, "normal")
        else:
            self.actor(g, e, "low", 0, "normal", lying=True)
        if crossed(t, dt, 0.7):
            self.puffs.emit(PX + 8, TY - 2, vx=10, vy=-3, life=0.6, rmax=1.5)
            self.puffs.emit(PX - 4, TY - 2, vx=-10, vy=-3, life=0.6, rmax=1.5)
        table(g, t)
        self.burner(g, e)
        flags(g, n, e, droop=t > 0.9)
        self.fx(g, dt)
        self.cloth(g, "收令" if t > 0.7 else "五营兵马")
        self.mx(g, n)
        if t > 0.7:
            g.mx[1:7, 1:7] = False
            g.mx[5:7, 0:8] = True

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        floor(g)
        n = self.arrived(e % CYCLE)
        up = span(t, 0.3, 0.9)
        if up <= 0:
            self.actor(g, e, "low", 0, "normal", lying=True)
        else:
            self.actor(g, e, "reach", -int((1 - up) * 90 / 15) * 15, "happy" if up >= 1 else "normal",
                       glow=0.9 < t < 1.3)
        if crossed(t, dt, 0.9):
            self.sparks.burst(PX, TY - 16, 12, 24, life=0.5)
        if 0.9 <= t < 0.97:
            pix.flash(g)
        table(g, t)
        self.burner(g, e)
        flags(g, n, e, droop=t < 0.9)
        self.fx(g, dt)
        self.cloth(g, "五营兵马")
        self.mx(g, n)

    def complete(self, g: Gfx, t: float, e: float):
        """连拍三下（一下比一下重）→ 五营齐到 → 令牌放光、令旗升天 → 五雷号令"""
        dt = self.clock(t)
        if t < 3.0:
            i = min(int(t / 1.0), 2)
            u = 0.6 + (t - i * 1.0) * 1.0 if t - i * 1.0 < 0.8 else 1.4 + (t - i * 1.0 - 0.8) * 1.0
            power = 1.0 + i * 0.8
            n = min(5, self.arrived(e % CYCLE) + (i + 1) * 2)
            jump = self.scene(g, t, e, dt, 0, n, u, power=power, text=["一拍", "二拍", "三拍"][i])
            if i == 2 and 1.4 <= u < 1.48:
                pix.flash(g)
            self.mx(g, n, slam=1.4 <= u < 1.6)
            return
        floor(g)
        self.actor(g, e, "reach", 0, "happy", glow=True)
        rays(g, PX, TY - 9, 11, 17, 12, rot=t * 0.7, dash=2)
        table(g, t)
        self.burner(g, e)
        lift = ease_in(span(t, 3.4, 5.0))
        flags(g, 5, e, lift=lift)
        self.fx(g, dt)
        self.cloth(g, "五营兵马")
        if t > 3.2:
            banner(g, 64, 4, "五雷号令", span(t, 3.2, 3.6))
            banner_text(g, 64, 4, "五雷号令", span(t, 3.2, 3.6))
        self.mx(g, 5)
        mx_ring(g, (t - 3.0) * 4)
        g.mx_level = 1 + int(6 * (1 - span(t, 3.0, 4.4)))
