"""五行生克：五枚五行令牌围成一圈，小道士剑指引气，相生流转、相克相击。

依据：五行相生（木生火、火生土、土生金、金生水、水生木），相克（木克土、土克水、水克火、火克金、金克木）；
周敦颐《太极图说》“五气顺布，四时行焉”。图式火居上（南），顺时针土、金、水、木：外圈为相生、内部五角星为相克。

画面：右边五枚圆牌，牌上逐像素画着本行的图：木（松）、火（焰，跳动）、土（垒土）、金（元宝）、水（水滴与波）；
外圈点线连成相生之环，内部点线是相克的五角星。左边小道士。
入场：小道士走来拱手，五牌依次（木火土金水）弹出，外圈相生弧画出，内部相克五角星画出，木牌翻亮。
持续：一轮分五段（木→火→土→金→水，每段 120 秒）：当令一牌反白，放出本行的小特效（木抽叶、火迸星、
      土扬尘、金闪光、水滴落）；一道带箭头的气沿外弧从当令一行流向它所生的一行（随 e），到达即换下一行当令，
      小道士剑指一点、牌子弹一下；左上“木生火”。约每 47 秒一次相克：一道光沿五角星打过去，
      被克的一牌抖动、冒烟，左上换成“金克木”。小道士平时持拂尘，隔一阵作揖。
      续：五牌沿圈转一周、五角星全亮，“五气顺布”。
中断：特效停住，五牌暗下，“暂歇”。  恢复：五牌依次亮回。
圆满：一道光绕圈两周，五牌一齐反白，收向中心合成一点，放出光芒，“五气顺布”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import daoshi, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r5_util import Clock, arm, arrow_head, cached, label, mx_ring, pop_box, rays, ring, sparkle

FLOOR = 60
DX = 20
CX, CY, R = 88, 31, 22
MR = 7                                   # 令牌半径
POS = ["火", "土", "金", "水", "木"]      # 圆上位置：从正上方顺时针
SHENG = ["木", "火", "土", "金", "水"]    # 当令次序
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
SEG = 120.0
KE_EVERY = 47.0
RENEW = 5.0

ICON_ART = {
    "木": """
    #
   ###
  #####
   ###
  #####
 #######
   .#.
    #
   ###
""",
    "火": """
    #
   ##
   ###
  ####
  ##.##
 ##...##
 ##.#.##
  #####
   ###
""",
    "土": """

    #
   ###
  #####
 ##.#.##
#########
#.#.#.#.#
#########
""",
    "金": """

   ###
  ##.##
#  ###  #
##.###.##
#########
 #######
  #####
""",
    "水": """
    #
   ###
   ###
  ##.##
  #.###
   ###

 ##  ##
#  ##  #
""",
}
FIRE2 = """
   #
    #
   ###
  ####
  ##.##
 ##...##
 ##.#.##
  #####
   ###
"""
MX_ART = {
    "木": [0x18, 0x3C, 0x7E, 0x3C, 0x7E, 0xFF, 0x18, 0x3C],
    "火": [0x10, 0x18, 0x38, 0x7C, 0x6C, 0xC6, 0xD6, 0x7C],
    "土": [0x00, 0x18, 0x3C, 0x7E, 0xFF, 0xAA, 0xFF, 0x00],
    "金": [0x00, 0x66, 0x7E, 0xFF, 0x81, 0x7E, 0x3C, 0x00],
    "水": [0x18, 0x3C, 0x66, 0x66, 0x3C, 0x00, 0x6D, 0xB6],
}


def icon(name: str, frame: int = 0) -> Sprite:
    art = FIRE2 if (name == "火" and frame % 2) else ICON_ART[name]
    return cached(("r5wx", name, frame % 2 if name == "火" else 0), lambda: Sprite(art))


def pos(name: str, rot: float = 0.0):
    a = POS.index(name) * 2 * math.pi / 5 + rot
    return CX + math.sin(a) * R, CY - math.cos(a) * R


def medal(g: Gfx, name: str, x: float, y: float, t: float, active: bool = False, s: float = 1.0,
          jit: float = 0.0, dim: bool = False):
    """令牌：双圈边，内画本行图；当令时整牌反白"""
    if s <= 0.05:
        return
    r = MR * s
    x = x + (rand(int(t * 25), 7) - 0.5) * 2 * jit
    g.d.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), fill=0)
    if active:
        g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
    else:
        g.d.ellipse((x - r, y - r, x + r, y + r), outline=1)
        if r > 3:
            g.d.ellipse((x - r + 2, y - r + 2, x + r - 2, y + r - 2), fill=0)
    if s > 0.8:
        ic = icon(name, int(t * 6))
        pix.blit(g, ic, x - ic.w / 2 + 0.5, y - ic.h / 2 + 0.5, outline=False, invert=active)
    if dim:
        g.fade(0.35, (x - r - 1, y - r - 1, x + r + 2, y + r + 2))


@register
class WuXing(Clock, Ritual):
    id = "r5.wuxing"
    name = "五行生克"
    desc = "五枚五行令牌围成相生之环、内含相克五角星；当令一行反白放特效，气沿外弧流向所生的一行，隔一阵相克一击"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.6, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)
        self.puffs = pix.Puffs(self.seed + 2)

    # ------------------------------------------------------------ 状态

    def state(self, e: float):
        """→ (轮 c, 轮内 k, 当令序号 i, 段内秒数 tau)"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        i = min(int(k // SEG), 4)
        return c, k, i, k - i * SEG

    def ke_event(self, e: float):
        """→ (攻者, 受者, 进度 0..1+)，没有时 None"""
        q = (e + 20) % KE_EVERY
        if q > 4.0:
            return None
        j = int((e + 20) // KE_EVERY)
        a = SHENG[int(rand(j, self.seed + 4) * 5)]
        return a, KE[a], q

    # ------------------------------------------------------------ 画

    def rings(self, g: Gfx, t: float, sheng: float = 1.0, ke: float = 1.0, ke_hot: tuple | None = None):
        """外圈相生（点线圆）与内部相克五角星（疏点）"""
        n = int(90 * sheng)
        for j in range(n):
            a = j / 90 * 2 * math.pi
            if j % 2 == 0:
                g.px(CX + math.sin(a) * R, CY - math.cos(a) * R)
        order = [0, 2, 4, 1, 3, 0]
        for m in range(int(5 * ke + 0.999)):
            a, b = POS[order[m]], POS[order[m + 1]]
            (x0, y0), (x1, y1) = pos(a), pos(b)
            pix.dotted(g, x0, y0, x1, y1, 3)

    def flow(self, g: Gfx, i: int, q: float, t: float):
        """气沿外弧从当令一行流向所生一行：粗点线 + 箭头"""
        a0 = POS.index(SHENG[i]) * 2 * math.pi / 5
        a1 = a0 + 2 * math.pi / 5
        m0, m1 = a0 + 0.36, a1 - 0.36
        end = lerp(m0, m1, q)
        steps = int((end - m0) * R) + 1
        for j in range(steps):
            a = m0 + j / R
            x, y = CX + math.sin(a) * R, CY - math.cos(a) * R
            g.d.rectangle((x - 1, y - 1, x, y), fill=1)
        if q > 0.02:
            x, y = CX + math.sin(end) * R, CY - math.cos(end) * R
            arrow_head(g, x, y, end, 4)
            if (t * 4) % 1 < 0.5:
                g.px(x, y, 0)

    def effect(self, g: Gfx, name: str, t: float, dt: float, x: float, y: float):
        """当令一行的小特效"""
        r = rand(int(t * 10), self.seed)
        if name == "火" and r < 0.5:
            self.sparks.burst(x, y - MR, 1, 10, up=14, life=0.6, gravity=-10)
        elif name == "水":
            q = (t * 0.9) % 1
            g.px(x, y + MR + 2 + q * 8), g.px(x, y + MR + 3 + q * 8)
            if q > 0.85:
                g.px(x - 2, y + MR + 11), g.px(x + 2, y + MR + 11)
        elif name == "金":
            sparkle(g, x + 7, y - 6, (t * 1.3) % 1)
            sparkle(g, x - 8, y + 4, (t * 1.3 + 0.5) % 1)
        elif name == "土" and r < 0.12:
            self.puffs.emit(x + (rand(int(t * 10), 3) - 0.5) * 10, y + MR, vy=-3, life=0.9, rmax=1.6)
        elif name == "木":
            q = (t * 0.6) % 1
            lx, ly = x + 6 + q * 8, y - 4 - math.sin(q * math.pi) * 6
            g.px(lx, ly), g.px(lx + 1, ly - 1)

    def actor(self, g: Gfx, e: float, t: float, tau: float, ke):
        if tau < 3.0:
            daoshi(g, DX, FLOOR, "point", t, face="wow" if tau < 1 else "normal")
            return
        if ke and 0.2 < ke[2] < 2.0:
            daoshi(g, DX, FLOOR, "gongshou", t, face="wow")
            return
        ph = e % 26
        if 16 < ph < 18.5:
            daoshi(g, DX, FLOOR, "bow" if 16.6 < ph < 17.9 else "gongshou", t)
        elif 7 < ph < 9:
            figure(g, DX, FLOOR, t, arm=arm("sky"), arm_at=(3, -25))
        else:
            daoshi(g, DX, FLOOR, "idle", t)

    def mx(self, g: Gfx, name: str, bright: bool = False):
        g.mx_rows(MX_ART[name])
        if bright:
            g.mx_level = 5

    def scene(self, g: Gfx, t: float, e: float, dt: float):
        c, k, i, tau = self.state(e)
        renew = c >= 1 and k < RENEW
        if renew:
            rot = ease_in_out(span(k, 0.3, 3.5)) * 2 * math.pi
            self.rings(g, t)
            if (t * 6) % 1 < 0.5 or k > 3.5:
                order = [0, 2, 4, 1, 3, 0]
                for m in range(5):
                    (x0, y0), (x1, y1) = pos(POS[order[m]], rot), pos(POS[order[m + 1]], rot)
                    g.d.line((x0, y0, x1, y1), fill=1)
            for name in POS:
                x, y = pos(name, rot)
                medal(g, name, x, y, t, active=k > 3.5 and name == "木")
            if 3.5 <= k < 3.57:
                pix.flash(g)
            daoshi(g, DX, FLOOR, "raise" if k < 3.5 else "gongshou", t, face="happy")
            return c, k, i, tau, renew, None
        cur = SHENG[i]
        nxt = SHENG[(i + 1) % 5]
        self.rings(g, t)
        ke = self.ke_event(e)
        if ke:                                         # 相克：光沿五角星的一边打过去
            a, b, q = ke
            (x0, y0), (x1, y1) = pos(a), pos(b)
            p = ease_in(span(q, 0.2, 0.8))
            if 0 < p < 1:
                g.d.line((x0, y0, lerp(x0, x1, p), lerp(y0, y1, p)), fill=1, width=2)
                hx, hy = lerp(x0, x1, p), lerp(y0, y1, p)
                g.d.ellipse((hx - 2, hy - 2, hx + 2, hy + 2), fill=1)
            if 0.8 <= q < 0.8 + dt:
                self.sparks.burst(x1, y1, 14, 30, up=4, life=0.5, gravity=30)
                for j in range(3):
                    self.puffs.emit(x1 + (j - 1) * 4, y1 - 3, vy=-6, life=1.0, rmax=2.2)
            if 0.8 < q < 1.4:
                ring(g, x1, y1, MR + (q - 0.8) * 20)
        self.flow(g, i, span(tau, 4.0, SEG - 2.0), t)
        for name in POS:
            x, y = pos(name)
            jit = 1.0 if (ke and ke[1] == name and 0.8 < ke[2] < 2.0) else 0.0
            pop = 1 + 0.25 * math.sin(span(tau, 0, 0.5) * math.pi) if name == cur else 1.0
            medal(g, name, x, y, t, active=name == cur, s=pop, jit=jit)
        x, y = pos(cur)
        self.effect(g, cur, t, dt, x, y)
        if tau < 0.6:
            ring(g, x, y, MR + 2 + tau * 16)
        self.actor(g, e, t, tau, ke)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        return c, k, i, tau, renew, ke

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        self.rings(g, t, sheng=span(t, 2.6, 3.6), ke=span(t, 3.6, 4.6))
        for j, name in enumerate(SHENG):
            s = ease_out_back(span(t, 1.2 + j * 0.25, 1.6 + j * 0.25))
            x, y = pos(name)
            medal(g, name, x, y, t, active=(name == "木" and t > 4.8), s=s)
        if 4.8 <= t < 4.8 + dt:
            x, y = pos("木")
            self.sparks.burst(x, y, 12, 26, life=0.5)
        if 4.8 < t < 5.4:
            x, y = pos("木")
            ring(g, x, y, MR + 2 + (t - 4.8) * 16)
        if t < 1.6:
            figure(g, lerp(-12, DX, ease_out(span(t, 0, 1.6))), FLOOR, t, legs="walk")
        else:
            daoshi(g, DX, FLOOR, "gongshou" if t < 4.6 else "point", t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 4.8:
            label(g, 5, 4, "木生火")
        self.mx(g, SHENG[min(int(span(t, 1.2, 2.45) * 5), 4)])

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, i, tau, renew, ke = self.scene(g, t, e, dt)
        if renew:
            if k > 1.0:
                label(g, 5, 4, "五气顺布")
            self.mx(g, POS[int(k * 3) % 5], k > 3.5)
            return
        if ke and 0.8 < ke[2] < 4.0:
            label(g, 5, 4, f"{ke[0]}克{ke[1]}")
            self.mx(g, ke[1], 0.8 < ke[2] < 1.2)
        else:
            label(g, 5, 4, f"{SHENG[i]}生{SHENG[(i + 1) % 5]}")
            self.mx(g, SHENG[i], tau < 0.5)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, i, tau = self.state(e)
        self.rings(g, t)
        self.flow(g, i, span(tau, 4.0, SEG - 2.0), t)
        for j, name in enumerate(POS):
            x, y = pos(name)
            medal(g, name, x, y, t, active=name == SHENG[i] and t < 0.6, dim=t > 0.3 + j * 0.15)
        daoshi(g, DX, FLOOR, "gongshou", t)
        if t > 0.3:
            label(g, 5, 4, "暂歇")
        self.mx(g, SHENG[i])

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, i, tau = self.state(e)
        self.rings(g, t)
        self.flow(g, i, span(tau, 4.0, SEG - 2.0), t)
        for j, name in enumerate(SHENG):
            x, y = pos(name)
            on = t > 0.2 + j * 0.2
            medal(g, name, x, y, t, active=name == SHENG[i] and t > 1.2, dim=not on)
            if 0.2 + j * 0.2 <= t < 0.2 + j * 0.2 + dt:
                self.sparks.burst(x, y, 5, 14, life=0.4, gravity=0)
        daoshi(g, DX, FLOOR, "point" if t < 1.3 else "idle", t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 1.0:
            label(g, 5, 4, f"{SHENG[i]}生{SHENG[(i + 1) % 5]}")
        self.mx(g, SHENG[i])

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, i, tau = self.state(e)
        self.rings(g, t, sheng=1.0 if t < 3.0 else 0.0, ke=1.0 if t < 3.0 else 0.0)
        if t < 2.0:                                      # 光绕圈两周
            a = ease_in_out(span(t, 0, 2.0)) * 4 * math.pi
            for m in range(6):
                aa = a - m * 0.12
                g.d.ellipse((CX + math.sin(aa) * R - 2, CY - math.cos(aa) * R - 2,
                             CX + math.sin(aa) * R + 2, CY - math.cos(aa) * R + 2), fill=1 if m == 0 else 0,
                            outline=1)
        gather = ease_in(span(t, 2.4, 3.2))
        for j, name in enumerate(POS):
            x, y = pos(name)
            x, y = lerp(x, CX, gather), lerp(y, CY, gather)
            medal(g, name, x, y, t, active=t > 2.0, s=1 - gather * 0.7)
        if t > 3.2:
            rays(g, CX, CY, 6, 30, 10, t * 0.4, 2)
            g.d.ellipse((CX - 4, CY - 4, CX + 4, CY + 4), fill=1)
            for j in range(2):
                ring(g, CX, CY, ((t - 3.2) * 24 + j * 14) % 28 + 5)
        if 3.2 <= t < 3.27:
            pix.flash(g)
        if 3.2 <= t < 3.2 + dt:
            self.sparks.burst(CX, CY, 30, 44, life=0.9, gravity=10)
        self.sparks.step(dt)
        self.sparks.draw(g)
        pose = "point" if t < 2.0 else ("raise" if t < 3.4 else ("bow" if 4.0 < t < 5.0 else "gongshou"))
        daoshi(g, DX, FLOOR, pose, t, face="happy" if t > 3.4 else "normal")
        if t > 3.6:
            y = pop_box(g, 30, 4, "五气顺布", t, 3.6, stars=False)
            g.text(30, y, "五气顺布", align="center")
        if t < 3.2:
            self.mx(g, POS[int(t * 4) % 5])
        else:
            mx_ring(g, (t - 3.2) * 4 % 6)
            g.mx_level = 1 + int(5 * (1 - span(t, 3.2, 4.6)))
