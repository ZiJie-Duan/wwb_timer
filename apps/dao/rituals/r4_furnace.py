"""炼丹：丹房里一座砖砌丹灶，灶上八卦炉（炉腹离卦为火），小道士跪在灶前摇蒲扇看火。

外丹烧炼讲“火候”：文火、武火、沐浴（停火慢养）、温养；丹砂烧之成水银，积变又还成丹砂，故名“还丹”，九转为上
（《抱朴子·内篇·金丹》）。
入场：炉盖“哐”地落在炉口扬起灰；小道士走来跪下，猛扇几下，灶门里“轰”地起火。
持续：一转 10 分钟，火候按 e 推进：文火 → 武火 → 沐浴 → 武火 → 温养（右上角写当前火候）。武火时火舌从灶门窜出、
      舔着炉腹，火星乱飞，炉盖咯咯跳，扇子扇得飞快；炉顶丹气越冒越浓。每隔 20 秒一个小事件：
      添一块炭（火星迸起）/ 擦汗 / 炉盖一跳“噗”出一团气。
      续：炉盖跳起，放出两圈丹气，上方“某转”，左上“第几转”加一。
中断：扇子越扇越慢放下，火退成几点炭火，“封炉”。  恢复：猛扇，火一下窜高（震屏）再落到当前火候。
圆满：火熄，炉身发抖，炉盖冲天飞走（闪白），一粒金丹升起放光，小道士举手惊喜，“九转丹成”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import P, Clock, cached, counter, dao, label, mx_art, mx_ring, orb, pop_title, ring, star, ticked

FLOOR = 58
STOVE = (60, 101, 43)       # 灶 x0, x1, 灶面 y
FX = 81                     # 炉中心
BODY_Y = 17                 # 炉身精灵顶
LID_Y = 13                  # 炉盖精灵顶
DOOR = (64, 75)             # 灶门 x0, x1
DAO_X = 41


# ---------------------------------------------------------------- 道具

def _lid():
    """炉盖 31×11：葫芦钮、穹顶上一圈出气孔、瓦棱、盖沿"""
    p = Part(31, 11)
    p.shape("ellipse", (13, 0, 17, 3), fill=1)          # 葫芦钮
    p.px(14, 1, 0)
    p.shape("rectangle", (14, 3, 16, 4), fill=1)
    p.shape("polygon", [(5, 9), (8, 6), (12, 5), (18, 5), (22, 6), (25, 9)], fill=1)  # 穹顶
    p.d.line((12, 5, 18, 5), fill=1)
    for x in (9, 13, 17, 21):                            # 出气孔
        p.px(x, 7, 0)
    p.d.line((10, 6, 12, 6), fill=0)
    p.shape("rectangle", (3, 9, 27, 10), fill=1)        # 盖沿
    p.d.line((4, 10, 26, 10), fill=0)
    p.dither([(20, 6), (25, 9), (19, 9)], 0.5, 0)
    return p.sprite()


def _body():
    """炉身 31×26：立耳、口沿、鼓腹；腹中圆牌离卦 ☲，左右乾 ☰、坤 ☷；腹下火纹；三只兽足"""
    p = Part(31, 26)
    for x0 in (2, 25):                                   # 立耳（口沿上的拱形耳）
        p.shape("rectangle", (x0, 0, x0 + 3, 7), fill=1)
        p.d.rectangle((x0 + 1, 1, x0 + 2, 4), fill=0)
    p.shape("rectangle", (1, 6, 29, 8), fill=1)          # 口沿
    p.d.line((2, 8, 28, 8), fill=0)
    p.shape("polygon", [(2, 9), (28, 9), (30, 12), (30, 15), (27, 19), (23, 21), (7, 21), (3, 19),
                        (0, 15), (0, 12)], fill=1)       # 鼓腹
    p.d.line((3, 10, 9, 10), fill=0)                     # 高光边下的阴线（衬出高光）
    p.d.ellipse((10, 9, 20, 19), fill=0)                 # 圆牌
    p.d.ellipse((10, 9, 20, 19), outline=1)
    p.d.line((13, 11, 17, 11), fill=1)                   # ☲ 离：上实
    p.d.line((13, 14, 14, 14), fill=1), p.d.line((16, 14, 17, 14), fill=1)   # 中虚
    p.d.line((13, 17, 17, 17), fill=1)                   # 下实
    for y in (11, 13, 15):                               # ☰ 乾（左）
        p.d.line((3, y + 1, 7, y + 1), fill=0)
    for y in (11, 13, 15):                               # ☷ 坤（右）
        p.d.line((23, y + 1, 24, y + 1), fill=0), p.d.line((26, y + 1, 27, y + 1), fill=0)
    for x in range(5, 26, 4):                            # 腹下火纹（云雷纹）
        p.px(x, 19, 0), p.px(x + 1, 20, 0), p.px(x + 2, 19, 0)
    p.dither([(22, 9), (30, 12), (30, 15), (27, 19), (24, 21), (21, 19)], 0.5, 0)
    for x in (5, 14, 23):                                # 三足：兽蹄
        p.shape("rectangle", (x, 21, x + 2, 24), fill=1)
        p.shape("rectangle", (x - 1, 24, x + 3, 25), fill=1)
        p.px(x + 2, 22, 0)
    return p.sprite()


def _stove():
    """丹灶 42×15：砖砌，灶面压一道石沿，灶门是拱形"""
    p = Part(42, 15)
    p.shape("rectangle", (0, 0, 41, 14), fill=1)
    p.d.line((0, 2, 41, 2), fill=0)
    for r, y in enumerate(range(5, 15, 3)):              # 砖缝
        p.d.line((0, y, 41, y), fill=0)
        for x in range(2 + (r % 2) * 3, 41, 6):
            p.d.line((x, y - 2, x, y - 1), fill=0)
    p.d.line((1, 1, 40, 1), fill=0)
    p.dither([(34, 3), (41, 3), (41, 14), (34, 14)], 0.5, 0)
    # 灶门（拱）
    d0, d1 = DOOR[0] - STOVE[0], DOOR[1] - STOVE[0]
    p.d.rectangle((d0 - 2, 4, d1 + 2, 14), fill=1)
    p.d.chord((d0, 4, d1, 11), 180, 360, fill=0)
    p.d.rectangle((d0, 7, d1, 14), fill=0)
    p.d.arc((d0 - 1, 3, d1 + 1, 12), 180, 360, fill=0)
    return p.sprite()


def _fan():
    """蒲扇 9×9（两帧：扇面朝上 / 朝下）"""
    out = []
    for up in (True, False):
        p = Part(9, 10)
        if up:
            p.shape("ellipse", (1, 0, 8, 7), fill=1)
            for k in range(3):
                p.d.line((4, 7, 2 + k * 2, 1), fill=0)
            p.shape("line", (4, 7, 3, 9), fill=1, width=2)
        else:
            p.shape("ellipse", (1, 2, 8, 9), fill=1)
            for k in range(3):
                p.d.line((4, 2, 2 + k * 2, 8), fill=0)
            p.shape("line", (4, 2, 3, 0), fill=1, width=2)
        p.d.ellipse((1, 0 if up else 2, 8, 7 if up else 9), outline=1)
        out.append(p.sprite())
    return out


def _gourd():
    """墙上挂的药葫芦 7×12"""
    p = Part(7, 13)
    p.shape("line", (3, 0, 3, 2), fill=1)
    p.shape("ellipse", (1, 2, 5, 6), fill=1)
    p.shape("ellipse", (0, 5, 6, 12), fill=1)
    p.d.line((1, 6, 5, 6), fill=0)
    p.px(2, 8, 0), p.px(4, 10, 0)
    p.dither([(4, 7), (6, 7), (6, 12), (4, 12)], 0.5, 0)
    return p.sprite()


def _coal():
    p = Part(4, 3)
    p.shape("polygon", [(0, 1), (1, 0), (3, 0), (3, 2), (0, 2)], fill=1)
    p.px(1, 1, 0), p.px(2, 2, 0)
    return p.sprite()


def prop(name):
    return cached(("furnace", name), {"lid": _lid, "body": _body, "stove": _stove, "fan": _fan,
                                      "gourd": _gourd, "coal": _coal}[name])


FLAME_S = pix.frames("""
  #  #
 ## ##
 #####
##.###
#....#
---
 #
 ##  #
 ### #
######
#.#..#
---
    #
 #  ##
 # ###
######
#..#.#
""")

FLAME_L = pix.frames("""
   #
   ##   #
  ###  ##
 ##### ##
 ########
##.##.###
#...#...#
---
     #
 #   ##
 ##  ###
 ### ###
 ########
###.#.###
#.......#
---
  #
  ##  #
 ###  ##
 #### ###
#########
##.#..###
#.......#
""")

TONGUE = pix.frames("""
 #
##
##
#.
---
#
##
.#
##
---
 #
 #
##
#.
""")

EMBER = pix.frames("""
# . #
---
. # .
""")

SCHEDULE = [(0, "文火", 1.0), (150, "武火", 2.0), (300, "沐浴", 0.35), (360, "武火", 2.0), (480, "温养", 0.7)]


def fire_at(k: float):
    """一转内第 k 秒：(火候名, 火力)，交界处 6 秒平滑"""
    name, pw = SCHEDULE[0][1], SCHEDULE[0][2]
    prev = pw
    for s, n, w in SCHEDULE:
        if k >= s:
            prev, name, pw = pw, n, w
            start = s
    q = min(1.0, (k - start) / 6.0) if start > 0 else 1.0
    return name, lerp(prev, pw, q)


def room(g: Gfx, t: float):
    """丹房：地砖、踢脚、墙上挂药葫芦与小窗"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    g.d.line((2, 14, 2, FLOOR - 4), fill=1)
    g.d.line((125, 14, 125, FLOOR - 4), fill=1)
    # 小窗（直棂）
    g.d.rectangle((108, 22, 121, 36), outline=1)
    for x in range(111, 120, 3):
        g.d.line((x, 23, x, 35), fill=1)
    g.d.line((107, 37, 122, 37), fill=1)
    # 药葫芦挂在钉上
    sw = round(math.sin(t * 1.1) * 0.6)
    g.px(16, 16)
    pix.blit(g, prop("gourd"), 13 + sw, 17)


@register
class Furnace(Ritual):
    id = "r4.furnace"
    name = "炼丹"
    desc = "小道士跪在丹灶前摇蒲扇看火，八卦炉随火候文武变化冒丹气；十分钟一转，九转丹成金丹冲天"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()
        self.ev0 = self.rng.randrange(3)

    # ------------------------------------------------------------ 画面零件

    def furnace(self, g: Gfx, t: float, power: float, lid_dy: float = 0.0, shake: float = 0.0, lid=True):
        sx = round(math.sin(t * 40) * shake) if shake else 0
        pix.blit(g, prop("body"), FX - 15 + sx, BODY_Y)
        if lid:
            pix.blit(g, prop("lid"), FX - 15 + sx, LID_Y - lid_dy)

    def fire(self, g: Gfx, t: float, power: float):
        """灶门里的火 + 武火时窜出的火舌"""
        d0, d1 = DOOR
        cx = (d0 + d1) // 2
        if power < 0.25:
            pix.blit(g, pix.anim(EMBER, t, 3), cx - 2, FLOOR - 2, outline=False)
            return
        fr = FLAME_L if power > 1.3 else FLAME_S
        spr = pix.anim(fr, t, 8 if power > 1.3 else 5)
        pix.blit(g, spr, cx - spr.w // 2, FLOOR - spr.h, outline=False)
        if power > 1.3:  # 火舌舔炉腹（炉足之间）
            for i, x in enumerate((FX - 6, FX + 3)):
                spr = pix.anim(TONGUE, t + i * 0.23, 9)
                pix.blit(g, spr, x, STOVE[2] - spr.h)

    def fanner(self, g: Gfx, t: float, rate: float, event: str | None = None, ek: float = 0.0):
        """跪着扇火的小道士。rate：每秒扇几下（0 = 放下）"""
        if event == "wipe":   # 擦汗
            up = 0.25 < ek < 0.8
            pose = P(legs="kneel", b=(100, 90, "palm"), f=(-50, -150, "palm") if up else (60, 40, "palm"),
                     face="happy" if up else "normal")
            h = dao(g, DAO_X, FLOOR, pose, t)
            if 0.4 < ek < 0.9:  # 汗珠甩出
                k = span(ek, 0.4, 0.9)
                g.px(DAO_X - 6 - k * 6, FLOOR - 30 + k * k * 14)
                g.px(DAO_X - 6 - k * 6, FLOOR - 31 + k * k * 14)
            return h
        if event == "coal":   # 添炭：伸手向前一抛
            k = ek
            pose = P(legs="kneel", lean=10 if k < 0.4 else 0, b=(100, 90, "palm"),
                     f=(20, 0, "palm") if k < 0.35 else (10, -20, "palm"))
            h = dao(g, DAO_X, FLOOR, pose, t)
            if 0.2 < k < 0.45:
                q = span(k, 0.2, 0.45)
                cx, cy = lerp(h["hf"][0], (DOOR[0] + DOOR[1]) / 2, q), lerp(h["hf"][1], FLOOR - 4, q) - math.sin(q * 3.14) * 8
                pix.blit(g, prop("coal"), cx - 2, cy - 1)
            return h
        ph = (t * rate) % 1 if rate > 0 else 0.5
        a2 = -25 + 50 * (0.5 + 0.5 * math.sin(ph * 2 * math.pi)) if rate > 0 else 60
        pose = P(legs="kneel", b=(100, 90, "palm"), f=(35 if rate > 0 else 70, a2, "fist"),
                 face="normal" if rate < 2.5 else "angry")
        h = dao(g, DAO_X, FLOOR, pose, t)
        fx, fy = h["hf"]
        fan = prop("fan")[0 if a2 < 0 else 1]
        pix.blit(g, fan, fx - 2, fy - (8 if a2 < 0 else 1))
        if rate > 0 and a2 > 15:  # 扇出的风
            for j in range(3):
                pix.dotted(g, fx + 8, fy + 2 + j * 2, fx + 13, fy + 4 + j * 2, 2, int(t * 12) + j)
        return h

    def smoke(self, g: Gfx, t: float, dt: float, power: float, dense: float):
        """炉顶葫芦钮边冒丹气"""
        rate = (0.8 + dense * 2.5) * (0.4 + 0.6 * min(power, 1.5))
        if int(t * rate) != int((t - dt) * rate):
            self.puffs.emit(FX + 2, LID_Y - 1, vx=2, vy=-6, life=2.2, rmax=1.4 + dense, spread=2)
        if power > 1.3 and self.sparks is not None and int(t * 9) != int((t - dt) * 9):
            self.sparks.burst((DOOR[0] + DOOR[1]) / 2, FLOOR - 7, 1, 14, up=16, life=0.6, gravity=30)
        self.puffs.step(dt, wind=math.sin(t * 0.4) * 1.5)
        self.puffs.draw(g)

    def mx(self, g: Gfx, t: float, power: float, prog: float):
        mx_art(g, """
...##...
.######.
#.####.#
.#....#.
.#....#.
..####..
""")
        r = 3 + int(prog * 1.99)
        g.mx[3:5, 3:5] = False
        if (t * (1 + prog * 3)) % 1 < 0.3 + prog * 0.7:
            g.mx[3, 3] = g.mx[4, 4] = True
            if prog > 0.5:
                g.mx[3, 4] = g.mx[4, 3] = True
        hgt = 0 if power < 0.25 else (1 if power < 1.3 else 2)
        for c in range(1, 7):
            hh = hgt if (int(t * 7) + c * 3) % 4 else max(0, hgt - 1)
            for rr in range(8 - hh, 8):
                g.mx[rr, c] = True
        if power < 0.25:
            g.mx[7, 2] = (t * 2) % 1 < 0.5
            g.mx[7, 5] = (t * 2 + 0.5) % 1 < 0.5
        return r

    def labels(self, g: Gfx, e: float, tag: str | None):
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}转" if n < 100 else f"{n}转")
        if tag:
            counter(g, tag, right=True)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        room(g, t)
        pix.blit(g, prop("stove"), STOVE[0], STOVE[2])
        # 炉盖从上方落下，弹一下
        drop = span(t, 0.0, 0.7)
        if drop < 1:
            lid_dy = (1 - ease_in(drop)) * 30
        else:
            b = span(t, 0.7, 1.1)
            lid_dy = math.sin(b * math.pi) * 3 if b < 1 else 0
        self.furnace(g, t, 0, lid_dy)
        if abs(t - 0.7) < dt:
            self.sparks.burst(FX - 10, LID_Y + 10, 6, 16, up=6, life=0.5, gravity=40)
            self.sparks.burst(FX + 10, LID_Y + 10, 6, 16, up=6, life=0.5, gravity=40)
        if 0.7 < t < 0.95:
            pix.shake(g, t, 1.0)
        # 走来、跪下、扇
        power = 0.0
        if t < 2.6:
            if t >= 0.8:
                x = lerp(-12, DAO_X, ease_out(span(t, 0.8, 2.6)))
                daoshi(g, x, FLOOR, "walk" if t < 2.5 else "idle", t)
        elif t < 3.0:
            daoshi(g, DAO_X, FLOOR, "kneel", t)
        else:
            rate = 3.2 if t < 4.4 else 1.6
            self.fanner(g, t, rate)
            power = 0 if t < 4.0 else (2.0 if t < 4.8 else lerp(2.0, 1.0, span(t, 4.8, 6.0)))
            if 3.3 < t < 4.0:
                pix.blit(g, pix.anim(EMBER, t, 4), (DOOR[0] + DOOR[1]) // 2 - 2, FLOOR - 2, outline=False)
        if power > 0:
            self.fire(g, t, power)
        if abs(t - 4.0) < dt:  # 轰地起火
            self.sparks.burst((DOOR[0] + DOOR[1]) / 2, FLOOR - 5, 16, 30, up=20, life=0.7, gravity=50)
            self.puffs.emit((DOOR[0] + DOOR[1]) / 2, FLOOR - 9, vy=-8, life=0.8, rmax=3, spread=4)
        if 4.0 < t < 4.3:
            pix.shake(g, t, 1.2)
        if t > 4.2:
            self.smoke(g, t, dt, power, 0.0)
        else:
            self.puffs.step(dt)
            self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, power, 0.0)
        self.labels(g, 0.0, "文火" if t > 4.2 else None)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        name, power = fire_at(k)
        prog = k / self.CYCLE
        room(g, t)
        pix.blit(g, prop("stove"), STOVE[0], STOVE[2])
        renew = e >= self.CYCLE and k < 6.0
        # 小事件：每 20 秒一个（按 e，重连不乱）
        slot = int(e // 20)
        ek = (e % 20) / 2.5
        event = None
        if ek < 1 and not renew and k > 8:
            event = ("coal", "wipe", "lid")[(slot + self.ev0) % 3]
        # 炉盖：武火咯咯跳；“噗”事件跳高；续的时候跳得最高
        lid_dy = 0.0
        if power > 1.5 and (t * 6) % 1 < 0.3:
            lid_dy = 1
        if event == "lid":
            lid_dy = math.sin(min(ek / 0.5, 1) * math.pi) * 4
        if renew:
            lid_dy = max(0.0, math.sin(min(k / 1.2, 1) * math.pi) * 10)
        self.furnace(g, t, power, lid_dy, shake=0.6 if power > 1.5 else 0)
        self.fire(g, t, power)
        rate = 0.8 + power * 1.1
        self.fanner(g, t, rate, event if event in ("coal", "wipe") else None, ek)
        if event == "coal" and abs(ek - 0.45) < dt / 2.5:
            self.sparks.burst((DOOR[0] + DOOR[1]) / 2, FLOOR - 6, 12, 26, up=18, life=0.6, gravity=50)
        if event == "lid" and abs(ek - 0.25) < dt / 2.5:
            for j in range(4):
                self.puffs.emit(FX + (j - 1.5) * 4, LID_Y + 8, vx=(j - 1.5) * 4, vy=-5, life=1.2, rmax=2.2)
        self.smoke(g, t, dt, power, prog)
        tag = name
        if renew:  # 续：两圈丹气 + “某转”
            for j in range(2):
                q = span(k, 0.6 + j * 0.5, 3.6 + j * 0.5)
                if 0 < q < 1:
                    ring(g, FX, LID_Y + 2 - q * 10, 4 + q * 16, dotted=2, ry=(4 + q * 16) * 0.4)
            if abs(k - 0.6) < dt:
                pix.flash(g)
                self.sparks.burst(FX, LID_Y + 4, 20, 34, up=14, life=0.9, gravity=30)
            if 0.6 < k < 0.9:
                pix.shake(g, t, 1.2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, power, prog)
        if renew and k > 1.2:
            n = int(e // self.CYCLE)
            pop_title(g, 60, 2, f"{cn_num(n)}转丹气" if n < 100 else f"{n}转丹气", span(k, 1.2, 1.6), t)
        else:
            self.labels(g, e, tag)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        _, p0 = fire_at(k)
        q = span(t, 0.0, 1.3)
        power = lerp(p0, 0.1, ease_out(q))
        room(g, t)
        pix.blit(g, prop("stove"), STOVE[0], STOVE[2])
        self.furnace(g, t, power)
        self.fire(g, t, power)
        rate = lerp(0.8 + p0 * 1.1, 0.0, q) if q < 0.9 else 0
        self.fanner(g, t, rate)
        self.smoke(g, t, dt, power * (1 - q), k / self.CYCLE * (1 - q))
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, power, k / self.CYCLE)
        self.labels(g, e, "封炉" if t > 0.6 else fire_at(k)[0])

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        name, p0 = fire_at(k)
        room(g, t)
        pix.blit(g, prop("stove"), STOVE[0], STOVE[2])
        if t < 0.6:
            power = 0.1
        else:
            power = lerp(2.4, p0, ease_out(span(t, 0.9, 2.0)))
        self.furnace(g, t, power, 2 if 0.6 < t < 0.9 else 0, shake=0.6 if power > 1.5 else 0)
        self.fire(g, t, power)
        self.fanner(g, t, 3.4 if t < 1.2 else 0.8 + p0 * 1.1)
        if abs(t - 0.6) < dt:
            self.sparks.burst((DOOR[0] + DOOR[1]) / 2, FLOOR - 5, 18, 32, up=20, life=0.8, gravity=50)
        if 0.6 < t < 0.9:
            pix.shake(g, t, 1.3)
        self.smoke(g, t, dt, power, k / self.CYCLE * span(t, 0.6, 2.0))
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, power, k / self.CYCLE)
        self.labels(g, e, name if t > 0.6 else "封炉")

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        room(g, t)
        pix.blit(g, prop("stove"), STOVE[0], STOVE[2])
        power = lerp(2.0, 0.0, span(t, 0.0, 1.0))
        shake = 1.0 if 1.0 < t < 2.0 else 0
        lid_on = t < 2.0
        self.furnace(g, t, power, (t * 12 % 1 < 0.5) * 2 if shake else 0, shake, lid=lid_on)
        self.fire(g, t, power)
        if not lid_on:  # 炉盖冲天飞走（打着转）
            q = span(t, 2.0, 2.8)
            if q < 1:
                pix.blit(g, prop("lid"), FX - 15 + q * 20, LID_Y - ease_in(q) * 50)
        if abs(t - 2.0) < dt:
            pix.flash(g)
            self.sparks.burst(FX, LID_Y + 8, 26, 44, up=20, life=1.0, gravity=40)
            for j in range(5):
                self.puffs.emit(FX + (j - 2) * 4, LID_Y + 8, vx=(j - 2) * 6, vy=-6, life=1.4, rmax=3)
        if 2.0 < t < 2.4:
            pix.shake(g, t, 1.6)
        # 小道士：先扇，后站起举手惊喜
        if t < 1.0:
            self.fanner(g, t, 1.0)
        elif t < 2.2:
            self.fanner(g, t, 0)
        else:
            dao(g, DAO_X, FLOOR, P(b=(-120, -110, "palm"), f=(-60, -70, "palm"), face="wow" if t < 3.2 else "happy"), t)
        # 金丹升起放光
        pill = None
        if t > 2.2:
            q = ease_out(span(t, 2.2, 3.6))
            px, py = FX, lerp(LID_Y + 8, 11, q)
            pill = (px, py)
            for j in range(8):  # 旋转的光芒
                a = j * math.pi / 4 + t * 1.5
                r0, r1 = 5, 9 + (j % 2) * 4 + math.sin(t * 6 + j) * 1.5
                pix.dotted(g, px + math.cos(a) * r0, py + math.sin(a) * r0, px + math.cos(a) * r1,
                           py + math.sin(a) * r1, 2, int(t * 10))
            g.d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=0)
            g.d.ellipse((px - 2, py - 2, px + 2, py + 2), fill=1)
            g.px(px - 1, py - 1, 0)
            if int(t * 4) % 2:
                star(g, px + 6, py - 6, 1)
        self.smoke(g, t, dt, power, 0.6) if t < 2.0 else (self.puffs.step(dt), self.puffs.draw(g))
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 点阵：金丹放光
        if t < 2.0:
            self.mx(g, t, power, 1.0)
        else:
            mx_ring(g, (t - 2.0) * 4 % 5)
            g.mx[3:5, 3:5] = True
            g.mx_level = 1 + int(6 * (1 - span(t, 2.0, 3.5)))
        if t > 3.0:
            pop_title(g, 32, 3, "九转丹成", span(t, 3.0, 3.4), t)
        else:
            n = int(e // self.CYCLE)
            counter(g, f"第{cn_num(max(n, 1))}转" if n < 100 else f"{n}转")
