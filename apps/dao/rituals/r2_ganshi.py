"""辰州赶尸：月夜山路，小道士戴斗笠、高举摄魂铃走在前面，两位额前贴着黄符的“客人”平伸双臂一蹦一跳跟着。

依据：湘西民间传说“赶尸”（与“放蛊”“辰州符”并称湘西三大谜）：尸体“头戴高筒毡帽，额上压着几张书写着符咒的
黄纸垂在脸上”，赶尸匠“不打灯笼，手中摇着一个摄魂铃”；义庄为旧时停放灵柩的处所。属民俗传说，非正统科仪，
画面取诙谐的味道。

舞台（侧视、横向卷动）：月亮、星星、远山（慢）、松树（快）、路面石子与草、地上的薄雾。
入场：雾里先传来铃声（声波），小道士从左边走进来，两位客人一前一后跳进来，雾散。
持续：背景按 e 卷动（一程 600 秒，每 150 秒路过一块里程石）。客人一蹦一跳（起跳拉长、落地压扁、扬尘），
      额前的黄符随跳动掀起；小道士迈步，每 2 秒摇一下铃（铃身摆、声波一圈圈）。
      每 30 秒一个小事件：乌鸦飞过“呱”；一阵风把后面那位的黄符整张掀起，小道士回身伸手按回去；萤火虫。
      续：路过一座义庄（屋檐、亮灯的门、灯笼、匾），“第几程”加一。
中断：小道士一手按住铃，客人落地站定扬起一点尘，“暂歇”。恢复：举铃连摇三声，客人重新起跳。
圆满：路边出现“故里”人家，门里的光洒出来，三人停下，小道士放下铃作揖，“魂归故里”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.chars import Part
from ..engine.cn import cn_num
from ..engine.fx import stars
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import act, boxed, fist, mx_ring, ring

FLOOR = 58
DAO_X = 94
GUESTS = (30, 58)            # 两位客人
SPEED = 7.0                  # 卷动速度（像素/秒）
RING = 2.0                   # 摇铃周期
HOP = 0.9                    # 跳一下的周期
RENEW = 9.0
MILE = 150.0


# ---------------------------------------------------------------- 精灵

def _guest(lift: int):
    """客人 16×30（朝右）：顶珠圆帽（帽箍）、帽檐下垂着黄符（lift=1 被风掀起）、青白的脸、
    平伸的双臂（亮袖、垂手），深色长袍（亮边、领口、腰带），并拢的脚"""
    p = Part(16, 30)
    p.shape("rectangle", (5, 0, 6, 1), fill=1)              # 顶珠
    p.shape("ellipse", (2, 1, 10, 9), fill=1)               # 圆帽
    p.d.line((3, 5, 9, 5), fill=0)                          # 帽箍
    p.px(4, 3, 0)
    p.shape("rectangle", (0, 7, 12, 8), fill=1)             # 帽檐
    p.d.line((1, 8, 11, 8), fill=0)
    p.shape("rectangle", (3, 9, 9, 13), fill=1)             # 脸
    p.d.line((7, 11, 8, 11), fill=0)                        # 闭着的眼
    p.px(3, 13, 0)
    if lift:  # 黄符被风掀起：翻到帽檐上
        p.shape("rectangle", (8, 3, 14, 6), fill=1)
        p.d.rectangle((8, 3, 14, 6), outline=0)
        p.px(10, 4, 0), p.px(12, 5, 0)
    else:     # 黄符垂在脸前：黑边隔开、两道符文
        p.shape("rectangle", (9, 8, 13, 16), fill=0)
        p.d.rectangle((10, 9, 12, 15), fill=1)
        p.px(11, 10, 0), p.px(11, 12, 0), p.px(11, 14, 0)
    p.shape("polygon", [(2, 14), (9, 14), (11, 28), (1, 28)], fill=1)   # 深色长袍：亮边
    p.d.polygon([(3, 15), (8, 15), (10, 27), (2, 27)], fill=0)
    p.dither([(3, 19), (10, 19), (10, 27), (2, 27)], 0.4, 1)
    p.d.line((4, 15, 6, 18), fill=1)                        # 领口
    p.d.line((2, 21, 10, 21), fill=1)                       # 腰带
    p.d.line((2, 22, 10, 22), fill=0)
    p.shape("rectangle", (6, 14, 15, 18), fill=0)           # 平伸的手臂（黑边隔开）
    p.d.rectangle((7, 15, 14, 17), fill=1)
    p.d.line((12, 15, 12, 17), fill=0)                      # 袖口
    p.shape("rectangle", (13, 18, 15, 20), fill=1)          # 垂着的手
    p.px(14, 20, 0)
    p.shape("rectangle", (3, 29, 9, 29), fill=1)            # 并拢的脚
    return p.sprite()


def _hat():
    """斗笠 21×6：竹编的尖顶大笠，编纹、帽檐、系带"""
    p = Part(21, 6)
    p.shape("polygon", [(10, 0), (20, 4), (0, 4)], fill=1)
    for x in range(3, 18, 3):
        p.px(x, 3, 0)
    p.px(8, 2, 0), p.px(12, 2, 0)
    p.shape("rectangle", (0, 4, 20, 4), fill=1)
    p.px(5, 5), p.px(15, 5)
    return p.sprite()


BELL = pix.frames("""
  #
 ###
 #.#
#...#
#####
  #
---
   #
  ###
 #..#
#...#
####
 #
---
 #
 ###
 #..#
 #...#
  ####
     #
""")

PINE = pix.sprite("""
     #
    ###
   #.#.#
    ###
   #####
  #.#.#.#
   #####
  #######
 #.#.#.#.#
  #######
 #########
#.#.#.#.#.#
     #
     #
     #
""")

CROW = pix.frames("""
#.   .#
 ##.##
  ###.#
   #
---
  .#.
 #####.#
#  #
""")

MILESTONE = pix.sprite("""
 #####
#.....#
#.###.#
#.....#
#.#.#.#
#.....#
#.###.#
#.....#
#######
""")


def _house(kind: str):
    """路边的屋 40×30：屋顶瓦垄、飞檐、门（亮灯）、门边灯笼、门楣上的匾（字另画）"""
    p = Part(40, 30)
    p.shape("polygon", [(4, 0), (35, 0), (39, 6), (0, 6)], fill=1)
    for x in range(5, 36, 3):
        p.d.line((x, 1, x, 4), fill=0)
    p.px(0, 5), p.px(39, 5)
    p.shape("rectangle", (3, 7, 36, 8), fill=1)
    p.d.line((4, 8, 35, 8), fill=0)
    for x in (4, 34):
        p.shape("rectangle", (x, 9, x + 1, 29), fill=1)
    p.shape("rectangle", (14, 14, 25, 29), fill=1)       # 亮灯的门
    p.d.line((19, 14, 19, 29), fill=0)
    p.d.rectangle((15, 15, 18, 28), outline=0)
    p.d.rectangle((20, 15, 24, 28), outline=0)
    if kind == "home":                                   # 故里人家：窗也亮着
        p.shape("rectangle", (28, 14, 32, 18), fill=1)
        p.d.line((30, 14, 30, 18), fill=0)
        p.d.line((28, 16, 32, 16), fill=0)
    p.shape("rectangle", (6, 13, 9, 18), fill=1)         # 灯笼
    p.d.line((7, 12, 7, 12), fill=1)
    p.d.line((6, 15, 9, 15), fill=0)
    return p.sprite()


_P: dict = {}


def prop(name):
    if name not in _P:
        _P[name] = {"g0": lambda: _guest(0), "g1": lambda: _guest(1), "hat": _hat,
                    "yizhuang": lambda: _house("yi"), "home": lambda: _house("home")}[name]()
    return _P[name]


@register
class GanShi(Ritual):
    id = "r2.ganshi"
    name = "辰州赶尸"
    desc = "月夜山路卷动，戴斗笠的小道士高举摄魂铃在前，两位额贴黄符的客人平伸双臂一蹦一跳跟着走"
    T = {"enter": 6.0, "interrupt": 1.5, "resume": 1.8, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.last_t = None
        self.sky_seed = self.rng.randrange(100)

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    # ------------------------------------------------------------ 布景

    def scenery(self, g: Gfx, t: float, w: float, fog: float = 0.3):
        """w = 走过的路程（像素）"""
        stars(g, t, self.sky_seed, n=20, box=(0, 0, 128, 30))
        g.d.ellipse((104, 3, 114, 13), fill=1)              # 满月
        g.px(107, 6, 0), g.px(110, 9, 0), g.px(108, 10, 0)
        prev = None
        for x in range(0, 129, 2):                          # 远山（慢）
            wx = x + w * 0.15
            y = 30 + noise(wx * 0.035, 7) * 12 + noise(wx * 0.12, 8) * 3
            if prev:
                g.d.line((prev[0], prev[1], x, y), fill=1)
            if int(wx) % 6 < 2:
                g.px(x, y + 3)
            prev = (x, y)
        span_ = 220
        for i in range(4):                                  # 松树（快）
            base = i * 55 + rand(i, 3) * 20
            x = (base - w) % span_ - 30
            pix.blit(g, PINE, x, FLOOR - 15 - (i % 2) * 2)
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)            # 路
        for i in range(24):                                 # 石子、草
            x = (i * 23 + rand(i, 5) * 15 - w * 1.0) % 140 - 6
            y = FLOOR + 2 + int(rand(i, 6) * 4)
            if i % 3 == 0:
                g.px(x, FLOOR - 1), g.px(x + 1, FLOOR - 2), g.px(x + 2, FLOOR - 1)
            else:
                g.px(x, y)
                if i % 4 == 1:
                    g.px(x + 1, y)
        m = (w // (MILE * SPEED))                            # 里程石
        mx_ = (m + 1) * MILE * SPEED - w + 20
        if mx_ < 140:
            pix.blit(g, MILESTONE, mx_, FLOOR - 9)
        if fog > 0:                                         # 薄雾
            for j in range(3):
                y = 49 + j * 3
                x0 = (t * (2 + j) * 3 + j * 40) % 160 - 40
                ln = int(28 * fog)
                pix.dotted(g, x0, y, x0 + ln, y, step=2 + j % 2)
                pix.dotted(g, x0 + 70, y + 1, x0 + 70 + ln * 0.7, y + 1, step=3)

    def house(self, g: Gfx, x: float, kind: str, glow: float = 0.0, t: float = 0.0):
        spr = prop(kind)
        pix.blit(g, spr, x, FLOOR - 30)
        if glow > 0:  # 门里洒出来的光
            for j in range(4):
                pix.dotted(g, x + 15 + j * 3, FLOOR - 1, x + 6 + j * 7, FLOOR + 5, step=2, phase=int(t * 6))

    def plaque(self, g: Gfx, bx: float):
        """门楣上的匾（名字写在左上的牌子上，免得被人挡住）"""
        if bx + 15 < 0 or bx > 127:
            return
        g.d.rectangle((bx, FLOOR - 25, bx + 15, FLOOR - 20), fill=0, outline=1)
        for x in range(int(bx) + 3, int(bx) + 13, 3):
            g.px(x, FLOOR - 23), g.px(x + 1, FLOOR - 22)

    # ------------------------------------------------------------ 角色

    def guest(self, g: Gfx, x: float, t: float, phase: float, hopping: bool = True, lift: bool = False):
        """一位客人：hopping 时按 HOP 周期跳，落地压扁、扬尘"""
        spr = prop("g1" if lift else "g0")
        if not hopping:
            pix.blit(g, spr, x - 8, FLOOR - spr.h)
            return 0.0
        p = ((t + phase) % HOP) / HOP
        if p < 0.12:      # 蹲（压扁）
            s = pix.stretch(spr, 1.15, 0.87)
            pix.blit(g, s, x - s.w / 2, FLOOR - s.h)
            return 0.0
        if p < 0.7:       # 起跳拉长
            q = (p - 0.12) / 0.58
            yy = math.sin(q * math.pi) * 7
            s = pix.stretch(spr, 0.9, 1.1) if q < 0.35 else spr
            pix.blit(g, s, x - s.w / 2, FLOOR - s.h - yy)
            return yy
        pix.blit(g, spr, x - 8, FLOOR - spr.h)
        return 0.0

    def landed(self, t: float, phase: float, dt: float) -> bool:
        p0 = ((t - dt + phase) % HOP) / HOP
        p1 = ((t + phase) % HOP) / HOP
        return p1 < p0 or (p0 < 0.7 <= p1)

    def dao(self, g: Gfx, t: float, walking: bool = True, ring_t: float | None = None, x: float = DAO_X,
            flip: bool = False, hand_to=None, bell: bool = True):
        """小道士：斗笠、高举摄魂铃；ring_t = 距上次摇铃的秒数（铃摆 + 声波）"""
        hat = prop("hat")

        def front(gg, at):
            at(-10, -36 - (int(t * 8) % 2 if walking else 0) * 0, hat)

        legs = "walk" if walking else "stand"
        if hand_to is not None:
            h = act(g, x, FLOOR, t, hand_to=hand_to, legs=legs, flip=flip, front=front)["hand"]
            return h
        from ..engine.chars import figure
        bob = ring_t is not None and ring_t < 0.4 and int(ring_t * 20) % 2
        if bell:
            h = figure(g, x, FLOOR, t, legs=legs, arm="raise", flip=flip, front=front)["hand"]
            h = (h[0] + (1 if bob else 0), h[1] + 1)
        else:
            h = act(g, x, FLOOR, t, ang=0.2, L=9, legs=legs, flip=flip, front=front)["hand"]
        if bell:
            fr = 0
            if ring_t is not None and ring_t < 0.6:
                fr = (1, 2, 1, 0)[int(ring_t * 8) % 4]
            b = BELL[fr]
            pix.blit(g, b, h[0] - 2, h[1] - 1)
            fist(g, *h)
            if ring_t is not None and ring_t < 1.2:  # 声波
                for j in range(3):
                    r = ring_t * 18 - j * 5
                    if 1 < r < 14:
                        a0, a1 = -50, 50
                        g.d.arc((h[0] + 1 - r, h[1] + 4 - r, h[0] + 1 + r, h[1] + 4 + r), a0, a1, fill=1)
        return h

    def mx(self, g: Gfx, t: float, hop: float, lift: bool = False, ringing: bool = False):
        """点阵：一个平伸双臂的小人随跳动上下；符掀起时多一点；摇铃时右上角声波"""
        dy = -int(round(hop / 3.5))
        body = ["..##....", "..##....", ".#####..", "..##.#..", "..##....", "..##....", ".#..#...", "........"]
        for y, row in enumerate(body):
            for x, c in enumerate(row):
                if c == "#":
                    g.mx_set(x, y + dy + 1)
        if lift:
            g.mx_set(4, dy)
        if ringing:
            g.mx_set(7, 0), g.mx_set(6, 1), g.mx_set(7, 2)

    def counter(self, g: Gfx, e: float, label: str | None = None, size: int = 8, pop: float = 1.0):
        n = int(e // self.CYCLE) + 1
        boxed(g, 4, 4, label or (f"第{cn_num(n)}程" if n < 100 else f"{n}程"), size=size, pop=pop)

    # ------------------------------------------------------------ 阶段

    def scene(self, g: Gfx, t: float, e: float, dt: float, w: float, walking: bool = True, fog: float = 0.3,
              extra=None):
        """持续时的一帧：布景、客人、小道士、事件。返回（客人跳的高度, 掀符, 是否摇铃）"""
        self.scenery(g, t, w, fog)
        if extra:
            extra()
        k = e % 30.0
        gust = 18.0 < k < 22.0
        lift_back = gust and k < 21.2
        hop0 = self.guest(g, GUESTS[0], t, 0.0, walking, lift=lift_back)
        hop1 = self.guest(g, GUESTS[1], t, HOP * 0.5, walking, lift=gust and 18.6 < k < 19.4)
        for i, ph in enumerate((0.0, HOP * 0.5)):
            if walking and self.landed(t, ph, dt):
                self.puffs.emit(GUESTS[i] - 3, FLOOR - 1, vx=-5, vy=-3, life=0.5, rmax=1.2, spread=1)
                self.puffs.emit(GUESTS[i] + 3, FLOOR - 1, vx=5, vy=-3, life=0.5, rmax=1.2, spread=1)
        rt = e % RING
        if gust and 19.4 < k < 21.4:  # 回身把后面那位的黄符按回去
            q = span(k, 19.4, 20.0)
            tgt = (GUESTS[0] + 10, FLOOR - 24 - hop0)
            x = lerp(DAO_X, GUESTS[1] + 14, ease_in_out(span(k, 19.4, 19.9)))
            x = lerp(x, DAO_X, ease_in_out(span(k, 20.8, 21.4)))
            if k < 20.8:
                self.dao(g, t, walking, x=x, flip=True,
                         hand_to=(lerp(x - 6, GUESTS[1] + 6, q), lerp(FLOOR - 20, FLOOR - 26, q)))
            else:
                self.dao(g, t, walking, rt, x=x)
        else:
            self.dao(g, t, walking, rt)
        if gust:  # 风线
            for j in range(4):
                xx = 128 - ((k - 18.0) * 90 + j * 23) % 160
                pix.dotted(g, xx, 20 + j * 7, xx + 14, 20 + j * 7, step=2)
        if 8.0 < k < 11.0:  # 乌鸦
            q = span(k, 8.0, 11.0)
            cx, cy = lerp(140, -10, q), 16 + math.sin(q * 7) * 3
            pix.blit(g, pix.anim(CROW, t, 6), cx, cy)
            if 9.0 < k < 9.6:
                g.d.line((cx - 3, cy - 2, cx - 6, cy - 4), fill=1)
                g.d.line((cx - 3, cy, cx - 7, cy), fill=1)
        if 24.0 < k < 29.0:  # 萤火
            for j in range(3):
                fx = 20 + j * 30 + math.sin(t * 1.3 + j) * 6
                fy = 40 + math.cos(t * 1.7 + j * 2) * 5
                if int(t * 4 + j) % 3:
                    g.px(fx, fy)
        self.puffs.step(dt)
        self.puffs.draw(g)
        return hop0, lift_back, rt < 0.6

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        fog = 1.0 - span(t, 4.0, 6.0) * 0.7
        self.scenery(g, t, (t - self.T["enter"]) * SPEED, fog)
        rt = t % RING
        xd = lerp(-12, DAO_X, ease_out(span(t, 0.5, 3.0)))
        if t > 0.5:
            self.dao(g, t, True, rt, x=xd)
        for i, (x1, t0) in enumerate(((GUESTS[1], 1.6), (GUESTS[0], 2.4))):
            if t > t0:
                x = lerp(-10, x1, ease_out(span(t, t0, t0 + 2.4)))
                ph = HOP * 0.5 if i == 0 else 0.0
                self.guest(g, x, t, ph)
                if self.landed(t, ph, dt):
                    self.puffs.emit(x, FLOOR - 1, vy=-3, life=0.5, rmax=1.2)
        if t < 0.6:  # 雾里的铃声
            for j in range(3):
                r = (t * 20 - j * 4)
                if r > 0:
                    g.d.arc((6 - r, 30 - r, 6 + r, 30 + r), -45, 45, fill=1)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.counter(g, 0.0)
        self.mx(g, t, 0.0, ringing=rt < 0.6)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        w = e * SPEED
        extra = None
        if e >= self.CYCLE and u < RENEW:  # 续：路过义庄
            hx = 130 - u * SPEED * 2.2

            def extra():
                self.house(g, hx, "yizhuang", glow=1, t=t)
                self.plaque(g, hx + 12)
        hop, lift, ringing = self.scene(g, t, e, dt, w, extra=extra)
        if e >= self.CYCLE and 1.0 < u < RENEW - 1.0:
            self.counter(g, e, "路过义庄")
        else:
            self.counter(g, e)
        self.mx(g, t, hop, lift, ringing)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        w = e * SPEED + min(t, 0.3) * SPEED
        self.scenery(g, t, w)
        land = t > 0.25
        for i, x in enumerate(GUESTS):
            self.guest(g, x, t, i * HOP * 0.5, hopping=not land)
            if 0.25 <= t < 0.25 + dt:
                self.puffs.emit(x - 3, FLOOR - 1, vx=-6, vy=-4, life=0.7, rmax=1.6)
                self.puffs.emit(x + 3, FLOOR - 1, vx=6, vy=-4, life=0.7, rmax=1.6)
        self.dao(g, t, walking=t < 0.3, ring_t=None, bell=t < 0.6)
        if t >= 0.6:  # 铃按在胸前
            pass
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.counter(g, e, "暂歇")
        self.mx(g, t, 0.0)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        w = e * SPEED - max(0.0, 1.8 - t) * SPEED * 0
        walking = t > 1.2
        self.scenery(g, t, e * SPEED - (1.8 - t) * SPEED * (t > 1.2))
        rt = (t % 0.4) if t < 1.2 else (e % RING)
        for i, x in enumerate(GUESTS):
            self.guest(g, x, t, i * HOP * 0.5, hopping=walking)
        self.dao(g, t, walking, rt)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.counter(g, e)
        self.mx(g, t, 0.0, ringing=rt < 0.3)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        stop = 2.6
        tt = min(t, stop)
        w = e * SPEED + tt * SPEED
        walking = t < stop
        hx = lerp(132, 89, ease_out(span(t, 0, stop)))

        def extra():
            self.house(g, hx, "home", glow=span(t, stop, stop + 0.6), t=t)
            self.plaque(g, hx + 12)

        self.scenery(g, t, w, fog=0.3 * (1 - span(t, stop, stop + 1)))
        extra()
        for i, x in enumerate(GUESTS):
            self.guest(g, x, t, i * HOP * 0.5, hopping=walking)
            if stop <= t < stop + dt:
                self.puffs.emit(x, FLOOR - 1, vy=-4, life=0.7, rmax=1.6)
        if t < stop:
            self.dao(g, t, True, e % RING, x=lerp(DAO_X, 79, span(t, 0.6, stop)))
        else:
            from ..engine.chars import daoshi
            bow = 3.2 < t < 4.6
            daoshi(g, 79, FLOOR, "bow" if bow else "gongshou", t, face="happy")
            pix.blit(g, prop("hat"), 79 - 10 + (2 if bow else 0), FLOOR - 36 + (3 if bow else 0))
        if stop <= t < stop + dt:
            self.sparks.burst(hx + 20, FLOOR - 8, 16, 30, up=8, life=0.8, gravity=30)
        if t > stop:
            for r in range(2):
                rr = (t - stop) * 16 - r * 8
                if 0 < rr < 26:
                    ring(g, hx + 20, FLOOR - 8, rr, step=2, sy=0.6)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > stop + 0.4:
            self.counter(g, e, "魂归故里", size=12, pop=ease_out_back(span(t, stop + 0.4, stop + 0.8)))
        else:
            self.counter(g, e, "故里" if t > 1.0 else None)
        self.mx(g, t, 0.0)
        if t > stop:
            mx_ring(g, (t - stop) * 4)
            g.mx_level = 1 + int(5 * (1 - span(t, stop, stop + 1.5)))
