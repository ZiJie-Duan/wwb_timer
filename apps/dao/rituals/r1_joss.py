"""化宝：宫观院里一座砖砌金炉（化宝炉），炉膛里火苗跳；小道士从元宝堆里拿起纸元宝，一锭锭抛进炉口。

依据：宫观设金炉（化宝炉）专门焚化金银纸、元宝、疏文；“填还受生”科仪焚化受生钱，以填还本命天库。

入场：金炉从地下升起（须弥座、拱形炉口、砖缝、两重翘角檐、葫芦顶），炉膛里“轰”地点着，
      元宝一锭锭从天上落下码成一堆；小道士走来站定。
持续：一轮 600 秒四十锭（元宝堆一层层变矮）：每 15 秒小道士转身拿一锭，举手一抛，元宝打着旋儿沿弧线飞进炉口，
      “呼”——火舌从炉口窜出、炉顶喷火星、冒一团黑烟，屏幕一震。中间穿插：拿火钳捅一捅炉膛，火苗一窜；
      一颗火星蹦到脚边，小道士吓得一跳。炉膛火苗逐帧跳动，炉顶一直冒烟。
      续：元宝烧完，新的元宝一锭接一锭从天上落下，弹跳着码回一堆，“第几炉”加一。
中断：两扇炉门（带门钉）合上，只剩门缝一线火光，牌子“封炉”。  恢复：炉门打开，火“轰”地一窜。
圆满：剩下的元宝一锭接一锭飞进炉里，炉顶火柱冲天、火星喷涌，小道士跪拜，闪白，“填还受生”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import FLOOR, Clock, badge, floor, hit, mx_art, mx_burst, pose_arm, ring_dots, title

FX = 100                 # 金炉中心
MOUTH = (100, 46)        # 炉口中心
TOP = (100, 1)           # 炉顶出烟口
DX = 56                  # 小道士
PILE_X = 27              # 元宝堆中心
N = 40                   # 一轮四十锭
EVERY = 15.0
RENEW = 7.0

INGOT = pix.sprite("""
#.  ###  .#
##.#####.##
.#########.
 .##.#.##.
   .###.
""")

FIRE = pix.frames("""
  #     #
 ##  # ##
 ### ####
#########
##.###.##
#.#.#.#.#
---
   #  #
 # ## ##
 ########
#########
###.#.###
#.#.#.#.#
---
 #    #
 ##  ###
### #####
#########
##.###.##
#.#.#.#.#
""")

TONGUE = pix.frames("""
    ##
   ###  #
  ####  ##
 ###### ###
###########
---
  #
  ##   ##
 ####  ###
 #### ####
###########
""")


def _furnace():
    """金炉 35×48：葫芦顶、攒尖顶（瓦垄、翘角）、上层小龛、腰檐、砖砌炉身（拱形炉口）、须弥座"""
    p = Part(35, 48)
    c = 17
    p.shape("ellipse", (c - 2, 0, c + 2, 3), fill=1)          # 葫芦
    p.shape("ellipse", (c - 3, 3, c + 3, 8), fill=1)
    p.d.line((c - 2, 3, c + 2, 3), fill=0)
    p.px(c - 1, 5, 0)
    p.shape("polygon", [(c, 8), (c + 13, 15), (c + 16, 13), (c + 15, 17), (c - 15, 17), (c - 16, 13), (c - 13, 15)],
            fill=1)                                            # 攒尖顶 + 翘角
    for x in range(c - 10, c + 11, 3):
        p.d.line((c, 9, x, 16), fill=0)
    p.shape("rectangle", (c - 9, 18, c + 9, 24), fill=1)      # 上层
    p.shape("rectangle", (c - 3, 19, c + 3, 24), fill=0)      # 小龛（出烟口）
    p.d.line((c - 9, 18, c + 9, 18), fill=0)
    p.shape("polygon", [(c - 15, 25), (c + 15, 25), (c + 17, 23), (c + 14, 28), (c - 14, 28), (c - 17, 23)],
            fill=1)                                            # 腰檐
    for x in range(c - 12, c + 13, 3):
        p.px(x, 26, 0)
    p.shape("rectangle", (c - 12, 29, c + 12, 42), fill=1)    # 炉身
    for y in range(31, 42, 3):                                 # 砖缝
        p.d.line((c - 12, y, c + 12, y), fill=0)
        off = 0 if (y // 3) % 2 else 3
        for x in range(c - 12 + off, c + 12, 6):
            p.px(x, y + 1, 0), p.px(x, y + 2, 0)
    p.shape("rectangle", (c - 7, 34, c + 7, 42), fill=0)      # 炉口
    p.shape("pieslice", (c - 7, 29, c + 7, 39), 180, 360, fill=0)
    p.d.arc((c - 8, 28, c + 8, 40), 180, 360, fill=1)
    p.shape("rectangle", (c - 15, 43, c + 15, 44), fill=1)    # 须弥座
    p.d.line((c - 14, 44, c + 14, 44), fill=0)
    p.shape("rectangle", (c - 13, 45, c + 13, 46), fill=1)
    for x in range(c - 12, c + 13, 4):
        p.px(x, 45, 0)
    p.shape("rectangle", (c - 16, 47, c + 16, 47), fill=1)
    p.dither([(c + 6, 29), (c + 12, 29), (c + 12, 42), (c + 8, 42)], 0.5, 0)
    return p.sprite()


_P: dict = {}


def P(name):
    if name not in _P:
        _P[name] = {"furnace": _furnace}[name]()
    return _P[name]


def yard(g: Gfx, t: float):
    """院子：后墙（墙头瓦）、一棵老松（左上）、地砖"""
    wy = 34
    g.d.line((0, wy, 127, wy), fill=1)
    for x in range(0, 128, 5):
        g.d.arc((x, wy - 3, x + 5, wy + 2), 180, 360, fill=1)
        g.px(x + 2, wy + 2)
    g.d.line((0, wy + 3, 127, wy + 3), fill=1)
    for x in range(10, 128, 22):          # 墙上几道砖缝
        g.d.line((x, wy + 8, x + 6, wy + 8), fill=1)
        g.d.line((x + 3, wy + 12, x + 9, wy + 12), fill=1)
    g.d.line((0, FLOOR - 4, 127, FLOOR - 4), fill=1)
    floor(g)
    for x, y in ((14, 8), (40, 4), (70, 12)):  # 天上几颗星
        if int(t * 0.8 + x) % 5:
            g.px(x, y)


def furnace(g: Gfx, rise: float = 1.0, fire: float = 1.0, t: float = 0.0, doors: float = 0.0, flare: float = 0.0):
    """金炉 + 炉膛火；doors 0 开 / 1 关；flare 火舌窜出炉口"""
    spr = P("furnace")
    y0 = FLOOR - spr.h + int((1 - rise) * spr.h)
    pix.blit(g, spr, FX - 17, y0)
    my = MOUTH[1] + int((1 - rise) * spr.h)
    if fire > 0 and doors < 1:
        fr = pix.anim(FIRE, t, 9)
        if fire < 0.6:
            fr = pix.stretch(fr, 1.0, max(0.4, fire))
        pix.blit(g, fr, FX - 4, my + 4 - fr.h, outline=False)
    if flare > 0:   # 火舌窜出炉口
        tg = pix.anim(TONGUE, t, 12)
        tg = pix.stretch(tg, 1.0 + flare * 0.3, 0.6 + flare * 1.0)
        pix.blit(g, tg, FX - tg.w / 2, my - 4 - tg.h * 0.8)
    if doors > 0:   # 两扇炉门（门钉），中间留一线火光
        w = int(7 * doors)
        for s in (-1, 1):
            x0 = FX - 7 if s < 0 else FX + 7 - w
            g.d.rectangle((x0, my - 9, x0 + w, my - 2 + 4), fill=1)
            g.d.rectangle((x0, my - 9, x0 + w, my - 2 + 4), outline=0)
            for yy in (my - 7, my - 4, my - 1):
                g.px(x0 + w // 2, yy, 0)
        if doors >= 1 and int(t * 5) % 2 == 0:
            g.d.line((FX, my - 8, FX, my + 1), fill=1)


def pile(g: Gfx, n: int):
    """元宝堆：n 锭（每锭精灵代表 4 锭），金字塔形码放"""
    rows = [4, 3, 2, 1]
    i = 0
    for r, cnt in enumerate(rows):
        for j in range(cnt):
            if i >= n:
                return
            x = PILE_X - cnt * 6 + j * 12 + 1
            y = FLOOR - 5 - r * 5 - 1
            pix.blit(g, INGOT, x - 5, y)
            i += 1


def spin_ingot(g: Gfx, x: float, y: float, t: float):
    """飞行中的元宝：打着旋（挤扁）"""
    sx = abs(math.cos(t * 8))
    spr = pix.stretch(INGOT, max(0.6, round(sx, 1)), 1.0)
    pix.blit(g, spr, x - spr.w / 2, y - 2)


def mx_furnace(g: Gfx, t: float, h: float = 1.0, closed: bool = False):
    mx_art(g, """
........
........
........
........
........
.######.
.#....#.
########
""")
    if closed:
        g.mx[6, 3] = int(t * 5) % 2 == 0
        return
    for x in range(2, 6):
        top = 6 - int(h * (2 + 2 * abs(math.sin(t * 8 + x * 1.9))))
        for y in range(max(top, 0), 7):
            g.mx[y, x] = True


@register
class BurnJoss(Ritual):
    id = "r1.joss"
    name = "化宝"
    desc = "小道士把纸元宝一锭锭抛进砖砌金炉，火舌窜出炉口、炉顶喷火星；捅炉膛、被火星吓一跳；一轮后天降新元宝"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 1.6, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)

    def left(self, e: float) -> int:
        """还剩几锭（四十锭计）"""
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return 0
        thrown = int(max(0.0, k - RENEW) // EVERY)
        if (k - RENEW) % EVERY >= 1.8 and k >= RENEW:
            thrown += 1
        return max(0, N - thrown)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        badge(g, 4, 3, label or (f"第{cn_num(n)}炉" if n < 100 else f"{n}炉"))

    def smoke(self, g: Gfx, t: float, dt: float, rate: float = 1.0, rise: float = 1.0):
        x, y = TOP
        if rate > 0 and int(t * 2.5 * rate) != int((t - dt) * 2.5 * rate):
            self.puffs.emit(x, y + 6, vx=2, vy=-8, life=2.6, rmax=2.0, spread=2)
        if rate > 0 and int(t * 4) != int((t - dt) * 4) and rand(int(t * 4), self.seed) < 0.5:
            self.sparks.burst(x, y + 8, 1, 10, up=18, life=0.9, gravity=-5)
        self.puffs.step(dt, wind=1.5)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def whoosh(self, t: float):
        self.sparks.burst(TOP[0], TOP[1] + 8, 14, 30, up=24, life=1.0, gravity=20)
        self.sparks.burst(MOUTH[0], MOUTH[1] - 6, 8, 26, up=10, life=0.5, gravity=40)
        self.puffs.emit(TOP[0], TOP[1] + 6, vy=-12, life=1.8, rmax=3.2, spread=0)

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        yard(g, t)
        rise = ease_out(span(t, 0.0, 1.4))
        lit = t > 1.6
        furnace(g, rise, fire=span(t, 1.6, 2.0) if lit else 0, t=t, flare=(1 - span(t, 1.6, 2.4)) if lit else 0)
        if t < 1.4:
            pix.shake(g, t, 0.8)
        if hit(t, 1.6, dt):
            self.whoosh(t)
        n = 0
        for i in range(10):   # 元宝从天上落下码成堆
            q = span(t, 2.0 + i * 0.18, 2.5 + i * 0.18)
            if q >= 1:
                n = i + 1
            elif q > 0:
                rows = [4, 3, 2, 1]
                r = 0 if i < 4 else 1 if i < 7 else 2 if i < 9 else 3
                j = i - (0, 4, 7, 9)[r]
                cnt = rows[r]
                x = PILE_X - cnt * 6 + j * 12 + 1
                y = lerp(-6, FLOOR - 6 - r * 5, ease_out_bounce(q))
                pix.blit(g, INGOT, x - 5, y)
        pile(g, n)
        x = lerp(-14, DX, ease_out(span(t, 2.4, 4.4)))
        daoshi(g, x, FLOOR, "walk" if t < 4.4 else ("gongshou" if t < 5.1 else "idle"), t)
        self.smoke(g, t, dt, rate=1.0 if lit else 0)
        if t > 1.6:
            self.counter(g, 0.0)
        mx_furnace(g, t, span(t, 1.6, 2.2))

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e, dt)
            return
        yard(g, t)
        u = (k - RENEW) % EVERY if k >= RENEW else 99
        j = int((k - RENEW) // EVERY) if k >= RENEW else -1
        nl = self.left(e)
        flare = 0.0
        if u < 3.0:
            flare = (1 - span(u, 1.8, 2.8)) if u >= 1.8 else 0
        stoke = 9.0 <= u < 11.0 and j % 3 == 1
        if stoke:
            flare = max(flare, 0.6 * (1 - span(u, 10.0, 10.8)) if u >= 10.0 else 0)
        furnace(g, 1.0, 1.0, t, flare=flare)
        pile(g, (nl + 3) // 4)
        if u < 1.8:
            self.throw(g, t, u, dt)
        elif stoke:     # 火钳捅炉膛
            q = ease_in_out(span(u, 9.2, 9.8)) * (1 - ease_in_out(span(u, 10.4, 11.0)))
            h = pose_arm(g, DX, FLOOR, t, 0)
            hx, hy = h["hand"]
            tx, ty = lerp(hx + 10, MOUTH[0] - 3, q), lerp(hy - 2, MOUTH[1] - 2, q)
            g.d.line((hx, hy, tx, ty), fill=1)
            g.d.line((hx, hy + 1, tx, ty + 1), fill=1)
            if hit(u, 10.0, dt):
                self.whoosh(t)
        elif 9.0 <= u < 11.0 and j % 3 == 2:   # 火星蹦到脚边，吓一跳
            v = u - 9.0
            if v < 0.6:
                q = v / 0.6
                g.d.ellipse((lerp(MOUTH[0] - 6, DX + 8, q) - 1, lerp(MOUTH[1], FLOOR - 1, q) - math.sin(q * math.pi) * 10 - 1,
                             lerp(MOUTH[0] - 6, DX + 8, q) + 1, lerp(MOUTH[1], FLOOR - 1, q) - math.sin(q * math.pi) * 10 + 1), fill=1)
                daoshi(g, DX, FLOOR, "idle", t)
            else:
                jump = math.sin(span(v, 0.6, 1.2) * math.pi) * 6
                daoshi(g, DX, FLOOR - jump, "raise" if v < 1.2 else "idle", t, face="wow" if v < 1.6 else "happy")
            if hit(v, 0.6, dt):
                self.sparks.burst(DX + 8, FLOOR - 1, 8, 20, up=10, life=0.4, gravity=60)
        elif 6.0 <= u < 8.4:
            daoshi(g, DX, FLOOR, "gongshou" if u < 7.2 else "bow", t)
        else:
            daoshi(g, DX, FLOOR, "idle", t)
        self.smoke(g, t, dt)
        self.counter(g, e)
        mx_furnace(g, t, 1.0 + flare)

    def throw(self, g: Gfx, t: float, u: float, dt: float):
        """u ∈ [0, 1.8]：转身拿一锭 → 举手一抛 → 元宝沿弧线飞进炉口"""
        if u < 0.6:
            h = pose_arm(g, DX, FLOOR, t, 60 if u > 0.2 else 30, flip=True)
            if u > 0.35:
                pix.blit(g, INGOT, h["hand"][0] - 5, h["hand"][1] - 5)
        elif u < 1.0:
            h = daoshi(g, DX, FLOOR, "raise", t)
            if u < 0.8:
                pix.blit(g, INGOT, h["hand"][0] - 5, h["hand"][1] - 5)
            else:
                q = span(u, 0.8, 1.8)
                self.fly(g, t, q)
        else:
            daoshi(g, DX, FLOOR, "point" if u < 1.5 else "idle", t, face="happy" if u > 1.8 else "normal")
            self.fly(g, t, span(u, 0.8, 1.8))
        if hit(u, 1.8, dt):
            self.whoosh(t)
        if 1.8 <= u < 2.0:
            pix.shake(g, t, 1.0)

    def fly(self, g: Gfx, t: float, q: float):
        if 0 < q < 1:
            sx, sy = DX + 10, FLOOR - 33
            tx, ty = MOUTH[0], MOUTH[1] - 2
            x = lerp(sx, tx, q)
            y = lerp(sy, ty, q) - math.sin(q * math.pi) * 18
            spin_ingot(g, x, y, t)
            for m in range(1, 4):   # 金光拖尾
                qq = max(q - m * 0.06, 0)
                g.px(lerp(sx, tx, qq), lerp(sy, ty, qq) - math.sin(qq * math.pi) * 18 + 2, m % 2)

    def _renew(self, g: Gfx, t: float, k: float, e: float, dt: float):
        """新元宝一锭接一锭从天上落下码成堆"""
        yard(g, t)
        furnace(g, 1.0, 1.0, t)
        n = 0
        rows = [4, 3, 2, 1]
        for i in range(10):
            q = span(k, 1.0 + i * 0.35, 1.6 + i * 0.35)
            if q >= 1:
                n = i + 1
            elif q > 0:
                r = 0 if i < 4 else 1 if i < 7 else 2 if i < 9 else 3
                j = i - (0, 4, 7, 9)[r]
                x = PILE_X - rows[r] * 6 + j * 12 + 1
                y = lerp(-6, FLOOR - 6 - r * 5, ease_out_bounce(q))
                pix.blit(g, INGOT, x - 5, y)
                g.px(x, y - 3)
            if hit(k, 1.3 + i * 0.35, dt):
                self.sparks.burst(PILE_X, FLOOR - 4, 3, 14, up=8, life=0.3, gravity=60)
        pile(g, n)
        daoshi(g, DX, FLOOR, "idle" if k < 0.8 else ("raise" if k < 4.6 else "gongshou"), t,
               face="wow" if k < 1.6 else "happy", flip=0.8 <= k < 4.6)
        self.smoke(g, t, dt, rate=0.6)
        self.counter(g, e if k >= 4.6 else e - k - 1)
        mx_furnace(g, t, 0.7)

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        yard(g, t)
        d = ease_out_bounce(span(t, 0.2, 0.9))
        furnace(g, 1.0, 1.0, t, doors=d)
        pile(g, (self.left(e) + 3) // 4)
        daoshi(g, DX, FLOOR, "point" if t < 0.9 else "gongshou", t)
        if hit(t, 0.55, dt):
            pix.shake(g, t, 1.0)
        self.smoke(g, t, dt, rate=1 - span(t, 0.4, 1.0))
        self.counter(g, e, "封炉" if t > 0.6 else None)
        mx_furnace(g, t, 1.0, closed=t > 0.6)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        yard(g, t)
        d = 1 - ease_out(span(t, 0.3, 0.8))
        flare = (1 - span(t, 0.8, 1.6)) if t > 0.8 else 0
        furnace(g, 1.0, 1.0, t, doors=d, flare=flare)
        pile(g, (self.left(e) + 3) // 4)
        daoshi(g, DX, FLOOR, "point" if t < 1.0 else "idle", t, face="wow" if 0.8 < t < 1.3 else "normal")
        if hit(t, 0.8, dt):
            self.whoosh(t)
            pix.flash(g)
        self.smoke(g, t, dt, rate=span(t, 0.8, 1.2))
        self.counter(g, e, "封炉" if t < 0.6 else None)
        mx_furnace(g, t, 1.0 + flare, closed=t < 0.5)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        yard(g, t)
        n0 = (self.left(e) + 3) // 4
        flare = 0.0
        for i in range(n0):     # 剩下的元宝一锭接一锭飞进炉里
            q = span(t, 0.3 + i * 0.15, 1.1 + i * 0.15)
            if 0 < q < 1:
                sx, sy = PILE_X, FLOOR - 8
                x = lerp(sx, MOUTH[0], q)
                y = lerp(sy, MOUTH[1] - 2, q) - math.sin(q * math.pi) * 22
                spin_ingot(g, x, y, t + i)
            if hit(t, 1.1 + i * 0.15, dt):
                self.sparks.burst(MOUTH[0], MOUTH[1] - 4, 6, 24, up=10, life=0.5, gravity=40)
        gone = sum(1 for i in range(n0) if t > 0.3 + i * 0.15)
        flare = span(t, 0.6, 1.8) * (1 - span(t, 4.2, 5.4))
        furnace(g, 1.0, 1.0, t, flare=flare * 1.4)
        pile(g, n0 - gone)
        if t > 1.8:              # 火柱冲天
            h = 26 * ease_out(span(t, 1.8, 2.4)) * (1 - span(t, 4.4, 5.4))
            for j in range(int(h)):
                y = 24 - j
                w = 3 + (j % 3 == 0) + math.sin(t * 20 + j * 0.7) * 1.5 - j * 0.06
                g.d.line((TOP[0] - w, y, TOP[0] + w, y), fill=1)
                if j % 4 == 2:
                    g.px(TOP[0], y, 0)
        daoshi(g, DX, FLOOR, "raise" if t < 1.8 else ("kneel" if t < 4.6 else "idle"), t,
               face="happy" if t > 4.6 else "normal")
        if hit(t, 2.0, dt):
            pix.flash(g)
            self.sparks.burst(TOP[0], TOP[1], 30, 46, up=20, life=1.4, gravity=30)
        if 2.0 < t < 2.4:
            pix.shake(g, t, 1.5)
        if int(t * 10) != int((t - dt) * 10) and 1.8 < t < 4.5:
            self.sparks.burst(TOP[0], TOP[1] - 10, 3, 30, up=20, life=0.8, gravity=30)
        self.smoke(g, t, dt, rate=1.5)
        if t > 2.4:
            title(g, 36, 6, "填还受生", t, 2.4)
        mx_furnace(g, t, 1.5)
        mx_burst(g, t, 2.0)
