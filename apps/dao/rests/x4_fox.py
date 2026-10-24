"""紫狐拜斗：野狐夜里击尾出火，戴髑髅拜北斗，髑髅不坠就化成人。

依据：段成式《酉阳杂俎》卷十五《诺皋记下》“旧说野狐名紫狐，夜击尾火出。将为怪，必戴髑髅拜北斗，髑髅不坠，则化为人矣。”

入场：夜空里北斗七星一颗颗亮起，野狐从右边一颠一颠地跑进来，在残碑前坐下，面前地上躺着一个髑髅。
持续：狐狸蹲坐，大尾巴贴地一摇一摇、眨眼、呼吸；两团狐火在草间飘；星星微闪。
      hold 6 秒起每 17 秒：尾巴高高扬起往地上一拍，火星四溅，冒起一团新的狐火飘上去，右上“夜击尾火出”。
      hold 15 秒起每 45 秒：低头叼起髑髅顶在头上，人立起来，前爪合拢朝北斗拜三拜，每拜一下北斗多亮几颗、连出斗线
      （右上“戴髑髅拜北斗”）；多数时候髑髅一歪掉下来滚回原处，狐狸落回四脚、甩甩头；每三回有一回髑髅不坠——
      “噗”一团烟，化成一个小道士（袍子后面露着狐狸尾巴），朝北斗作揖，写出“髑髅不坠”“则化为人”，再“噗”地变回狐狸。
收场：狐狸转身一颠一颠窜出画面，北斗淡去。
点阵：北斗七星（微闪，拜亮后常亮）+ 底下一点跳动的狐火；髑髅掉落时是髑髅，化人时是小人。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Clock, ev, label, mx_art, sparkle, tuft

FLOOR = 58
FX = 80                      # 狐狸身子中线
SKULL_AT = (58, FLOOR - 6)   # 地上髑髅的左上角
STRIKE0, STRIKE_P, STRIKE_D = 6.0, 17.0, 5.5
WORSHIP0, WORSHIP_P = 15.0, 45.0
DIPPER = [(13, 7), (10, 16), (22, 20), (25, 11), (35, 9), (44, 11), (52, 18)]   # 天枢 … 摇光
MX_DIPPER = [(1, 0), (0, 3), (3, 4), (3, 1), (5, 1), (6, 2), (7, 4)]
SKY = [(4, 30), (31, 27), (60, 4), (70, 18), (86, 10), (94, 25), (108, 4), (122, 16), (117, 30), (46, 30), (3, 3)]


def _rim(art: str) -> Sprite:
    """字符画 → 精灵，外沿一圈强制为亮（网点毛色也有干净的白轮廓）"""
    s = Sprite(art)
    m = s.mask
    inner = m.copy()
    inner[1:] &= m[:-1]
    inner[:-1] &= m[1:]
    inner[:, 1:] &= m[:, :-1]
    inner[:, :-1] &= m[:, 1:]
    on = s.on | (m & ~inner)
    return Sprite(on=on, mask=m.copy())


# ---------------------------------------------------------------- 狐狸（朝左；部件分开贴）

HEAD = _rim("""
 ###         ###
 #..#       #..#
 #...#     #...#
 #.#.#.#.#.#.#.#
#.#.#.#.#.#.#.#.#
.###.######.####.
#.#..#####..###.#
 ###############
######..#########
  ####.########
    #.##.####
      #####
       ###
""")

HEAD_BLINK = _rim("""
 ###         ###
 #..#       #..#
 #...#     #...#
 #.#.#.#.#.#.#.#
#.#.#.#.#.#.#.#.#
.###############.
#.#..#####..###.#
 ###############
######..#########
  ####.########
    #.##.####
      #####
       ###
""")

HEAD_HAPPY = _rim("""
 ###         ###
 #..#       #..#
 #...#     #...#
 #.#.#.#.#.#.#.#
#.#.#.#.#.#.#.#.#
.##.######.#####.
#..#.####.#.###.#
 ###############
######..#########
  ####.########
    #.##.####
      #####
       ###
""")

BODY = _rim("""
    #####.#
   #####.#.#
  #######.#.#
  ######.#.#.
 ########.#.#.
 #######.#.#.#
 ########.#.#.#
 #######.#.#.#.
 ########.#.#.#
 ####.##.#.#.#.
#####.##..#.#.#
#####.##.#.#.#.
#####.###.#.#.#
#####.##.#####.
##.#.######.##
""")

TAIL = [_rim(a) for a in ("""
     ###
    #####
    ######
    #######
     ######
     #.#.#.#
     .#.#.#.
     #.#.#.#
     .#.#.#.
    .#.#.#.#
   .#.#.#.#
  .#.#.#.#
 .#.#.#.#
.#.#.#.#
#.#.#.
""", """
       ###
      #####
      ######
      #######
       ######
       #.#.#.#
      #.#.#.#
      .#.#.#.
      #.#.#.#
    .#.#.#.#
   .#.#.#.#
  .#.#.#.#
 .#.#.#.#
.#.#.#.#
#.#.#.
""")]  # 大尾巴竖在身后，尾尖白、往上卷，两帧左右摇

TAIL_UP = _rim("""
   ##
  #####
  #####
  ######
  #.#.#.
  .#.#.#
 .#.#.#.
 #.#.#.
 .#.#.#
.#.#.#.
#.#.#.
.#.#.#
#.#.#
.#.#
""")

TAIL_SLAM = _rim("""
                ###
      .#.#.#.#.#####
 .#.#.#.#.#.#.######
.#.#.#.#.#.#.#.###
 .#.#.#.#.#.
""")

STAND = _rim("""
   ####.#.
  ######.#.
  #####.#.#
 #######.#.#
####.##.#.#.
#.###.##.#.#
#####.#.#.#.
 ###.###.#.#
 ######.#.#.
 #######.#.#
 ######.#.#.
 #######.#.#
 ######.#.#.
  ####.#.#.#
  ####..#.#.
  ####.#.#.
 #####.####
###.#####.##
""")

RUN = [_rim(a) for a in ("""
     ##.#.#.#.#.
   #####.#.#.#.#.#
  #####.#.#.#.#.#.#
  ######.#.#.#.#.#.
   ####.#.#.#.#.#.
    ####      ####
  ####          ####
####              ##
##
""", """
     ##.#.#.#.#.
   #####.#.#.#.#.#
  #####.#.#.#.#.#.#
  ######.#.#.#.#.#.
   ####.#.#.#.#.#.
     ####   ####
      ########
       #####
        ###
""")]

SKULL = Sprite("""
 #####
#######
#..#..#
###.###
 #####
 #.#.#
""")

FIRE = pix.frames("""
   #
   ##
  #.#
 #..##
 #...#
#..#..#
#.###.#
#.....#
 #...#
  ###
---
    #
   ##
  #.#
 #..#
 #...#
#..#.#
#.###.#
#.....#
 #...#
  ###
---
  #
  ##
  #.#
 ##..#
 #...#
#.#..#
#.###.#
#.....#
 #...#
  ###
""")

FIRE_S = pix.frames("""
 #
#.#
 #
---
#
 #
#.#
 #
""")


def _stele():
    """残碑 15×24：断口斜裂、碑额云纹、碑文（点）、裂缝、苔点、碑座"""
    p = Part(15, 24)
    p.shape("polygon", [(2, 5), (6, 2), (8, 4), (11, 0), (12, 1), (12, 20), (2, 20)], fill=1)
    p.d.line((3, 7, 11, 7), fill=0)
    for x in (4, 7, 10):                                  # 碑文三列
        for y in range(9, 19, 2):
            if not (x == 10 and y > 14):
                p.px(x, y, 0)
    p.d.line((9, 5, 8, 9), fill=0)                       # 裂缝
    p.d.line((8, 9, 9, 12), fill=0)
    p.dither([(11, 1), (12, 1), (12, 20), (11, 20)], 0.5, 0)
    p.shape("rectangle", (0, 20, 14, 23), fill=1)        # 碑座
    p.d.line((1, 21, 13, 21), fill=0)
    p.px(3, 22, 0), p.px(7, 22, 0), p.px(11, 22, 0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"stele": _stele}[name]()
    return _PROPS[name]


def night(g: Gfx, t: float, lit: int = 0, link: float = 0.0, fade: float = 1.0):
    """夜空：碎星、北斗（lit = 拜亮的颗数，link = 斗线连出的比例）、残碑、草地"""
    for i, (x, y) in enumerate(SKY):
        if fade > 0.3 and (t * 0.7 + i * 0.37) % 1 < 0.85:
            g.px(x, y)
    n = len(DIPPER)
    if link > 0:
        segs = list(zip(DIPPER[:-1], DIPPER[1:])) + [(DIPPER[3], DIPPER[0])]
        k = link * len(segs)
        for i, (a, b) in enumerate(segs):
            q = min(max(k - i, 0), 1)
            if q > 0:
                pix.dotted(g, a[0], a[1], lerp(a[0], b[0], q), lerp(a[1], b[1], q), step=2)
    for i, (x, y) in enumerate(DIPPER):
        if fade < (i + 1) / n:
            continue
        on = i < lit
        tw = (t * 0.9 + i * 0.29) % 1
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):  # 北斗：常亮的小十字
            g.px(x + dx, y + dy)
        if on or tw < 0.12:  # 闪 / 拜亮：长芒
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                g.px(x + dx, y + dy)
        if on and (t * 2 + i * 0.5) % 1 < 0.5:
            for dx, dy in ((3, 0), (-3, 0), (0, 3), (0, -3), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                g.px(x + dx, y + dy)
    pix.blit(g, prop("stele"), 104, FLOOR - 23)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-3, 130, 7):
        g.px(x, FLOOR + 2), g.px(x + 3, FLOOR + 4)
    tuft(g, 8, FLOOR, t, 0)
    tuft(g, 40, FLOOR, t, 1)
    tuft(g, 122, FLOOR, t, 0)


def wisps(g: Gfx, t: float):
    """两团狐火在草间飘"""
    for i, (cx, cy, ax, ay, sp) in enumerate(((30, 44, 10, 4, 0.31), (118, 30, 6, 6, 0.23))):
        x = cx + math.sin(t * sp * 2 * math.pi) * ax
        y = cy + math.sin(t * sp * 1.7 * 2 * math.pi + i) * ay
        pix.blit(g, pix.anim(FIRE, t + i * 0.3, 6), x - 3, y - 5, outline=False)


def fox_sit(g: Gfx, t: float, tail: str = "rest", head_dx: int = 0, head_dy: int = 0, face: str = "normal",
            x: int = FX):
    """蹲坐的狐狸。tail：rest / up / slam；返回头的左上角"""
    bob = 1 if (t * 0.6) % 1 < 0.5 else 0
    if tail == "up":
        pix.blit(g, TAIL_UP, x + 3, FLOOR - 4 - TAIL_UP.h)
    elif tail == "slam":
        pix.blit(g, TAIL_SLAM, x + 2, FLOOR - TAIL_SLAM.h + 1)
    else:
        tl = TAIL[int(t * 0.9) % 2]
        pix.blit(g, tl, x + 2, FLOOR - tl.h)
    pix.blit(g, BODY, x - 7, FLOOR - BODY.h + 1)
    hd = HEAD_HAPPY if face == "happy" else HEAD_BLINK if (face == "blink" or t % 4.1 < 0.15) else HEAD
    hx, hy = x - 10 + head_dx, FLOOR - BODY.h - 10 + bob + head_dy
    pix.blit(g, hd, hx, hy)
    return hx, hy


def fox_stand(g: Gfx, t: float, bow: float = 0.0, skull: bool = True, wob: int = 0):
    """人立：前爪合拢；bow ∈ [0,1] 拜下去的程度"""
    pix.blit(g, TAIL[int(t * 0.9) % 2], FX + 1, FLOOR - TAIL[0].h)
    pix.blit(g, STAND, FX - 6 - int(bow * 1), FLOOR - STAND.h + 1)
    hx = FX - 9 - int(round(bow * 3))
    hy = FLOOR - STAND.h - 11 + int(round(bow * 4))
    pix.blit(g, HEAD_BLINK if bow > 0.6 else HEAD, hx, hy)
    if skull:
        pix.blit(g, SKULL, hx + 5 + wob, hy - 3)
    return hx, hy


def fox_run(g: Gfx, x: float, t: float, flip: bool = False):
    """跑（默认朝左），x = 身子中线"""
    k = int(t * 8) % 2
    x = int(round(x))
    bob = 0 if k else -2
    body = RUN[k]
    by = FLOOR - body.h + 1 + bob
    if not flip:
        pix.blit(g, TAIL_SLAM, x + 7, by - 1)
        pix.blit(g, body, x - 10, by)
        pix.blit(g, HEAD, x - 18, by - 9)
    else:
        pix.blit(g, TAIL_SLAM, x - 7 - TAIL_SLAM.w, by - 1, flip=True)
        pix.blit(g, body, x + 10 - body.w, by, flip=True)
        pix.blit(g, HEAD, x + 18 - HEAD.w, by - 9, flip=True)


def fox_tail_behind(g, at):
    """化成人时袍子后面露出来的狐狸尾巴"""
    tl = pix.flipped(TAIL[1])
    at(-tl.w + 1, -tl.h - 1, tl)


MX_PERSON = ["   ##   ", "  ####  ", "  ####  ", "   ##   ", " ###### ", "#.####.#", "  ####  ", "  #  #  "]
MX_SKULL = [" ###### ", "########", "#..##..#", "#..##..#", "########", " ##..## ", "  ####  ", "  #  #  "]


@register
class FoxRest(Rest):
    id = "x4.fox"
    name = "紫狐拜斗"
    desc = "夜里野狐坐在残碑前，击尾出火；顶着髑髅人立拜北斗，髑髅不坠就噗地化成一个露着尾巴的小道士"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.k0 = self.rng.randrange(3)   # 第几回成功（每三回一回）

    # ------------------------------------------------------------ 拜斗事件

    def worship(self, t: float):
        """返回 (n, loc, success, dur) 或 None"""
        e = ev(t, WORSHIP_P, WORSHIP0)
        if e is None:
            return None
        n, loc = e
        ok = (n + self.k0) % 3 == 2
        dur = 17.0 if ok else 12.0
        return (n, loc, ok, dur) if loc < dur else None

    def strike(self, t: float):
        e = ev(t, STRIKE_P, STRIKE0, STRIKE_D)
        if e is None:
            return None
        n, loc = e
        t0 = t - loc
        if self.worship(t0) or self.worship(t0 + 3.0) or self.worship(t):
            return None
        return e

    def frame(self, g: Gfx, t: float, dt: float):
        """hold 的一帧（除文字外）；返回 (文字, 点阵模式)"""
        w = self.worship(t)
        lit, link = 0, 0.0
        if w:
            _, loc, ok, dur = w
            bows = int(span(loc, 2.2, 7.0) * 3 + 0.25) if loc > 2.2 else 0
            lit = [0, 3, 5, 7][min(bows, 3)]
            link = span(loc, 6.0, 7.5) * (1 - span(loc, dur - 2.0, dur))
            if loc > dur - 2.0:
                lit = 0 if loc > dur - 1.0 else lit
        night(g, t, lit, link)
        wisps(g, t)
        text, mode = None, "dipper"
        if w:
            text, mode = self.draw_worship(g, t, dt, *w)
        else:
            s = self.strike(t)
            pix.blit(g, SKULL, *SKULL_AT)
            if s:
                n, loc = s
                tail = "up" if 0.2 < loc < 0.7 else "slam" if 0.7 <= loc < 1.0 else "rest"
                fox_sit(g, t, tail, face="blink" if 0.6 < loc < 1.0 else "normal")
                tip = (FX + 20, FLOOR - 3)
                if abs(loc - 0.7) < dt * 0.99 or (loc >= 0.7 and loc - dt < 0.7):
                    self.sparks.burst(*tip, 14, 30, up=20, life=0.6, gravity=60)
                if 0.7 <= loc < 0.9:
                    pix.shake(g, t, 1.0)
                if loc > 0.8:  # 新狐火：从尾尖冒起、摇摇晃晃飘上去
                    q = span(loc, 0.8, STRIKE_D)
                    fx = tip[0] + math.sin(loc * 3) * 3 - q * 6
                    fy = tip[1] - 4 - ease_out(q) * 34
                    fr = FIRE if q < 0.75 else FIRE_S
                    pix.blit(g, pix.anim(fr, loc, 6), fx - 3, fy - 5, outline=False)
                if 0.8 < loc < 3.6:
                    text = "夜击尾火出"
            else:
                fox_sit(g, t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.puffs.step(dt)
        self.puffs.draw(g)
        return text, mode, lit

    def draw_worship(self, g: Gfx, t: float, dt: float, n: int, loc: float, ok: bool, dur: float):
        sx, sy = SKULL_AT
        if loc < 1.6:  # 低头叼起髑髅，顶到头上
            if loc < 1.0:
                q = ease_in_out(span(loc, 0.0, 0.8))
                pix.blit(g, SKULL, sx, sy)
                fox_sit(g, t, head_dx=-int(q * 14), head_dy=int(q * 9))
            else:
                q = ease_out(span(loc, 1.0, 1.6))
                hx, hy = fox_sit(g, t, head_dx=-int((1 - q) * 14), head_dy=int((1 - q) * 9))
                pix.blit(g, SKULL, hx + 5, hy - 3)
            return None, "dipper"
        if loc < 2.2:  # 人立起来（拉伸）
            q = span(loc, 1.6, 2.2)
            fox_stand(g, t, bow=0.0)
            if q < 0.3:
                pix.shake(g, t, 0.6)
            return None, "dipper"
        text = "戴髑髅拜北斗" if loc < 8.0 else None
        if loc < 7.0:  # 三拜
            ph = ((loc - 2.2) % 1.6) / 1.6
            bow = math.sin(span(ph, 0.25, 0.85) * math.pi)
            fox_stand(g, t, bow=bow)
            return text, "dipper"
        if loc < 8.0:  # 屏息：髑髅晃两晃
            wob = int(round(math.sin(loc * 18) * (1 if loc > 7.4 else 0)))
            fox_stand(g, t, wob=wob)
            return text, "dipper"
        if not ok:  # 髑髅掉下来滚回去
            if loc < 8.6:
                q = span(loc, 8.0, 8.6)
                hx, hy = fox_stand(g, t, skull=False)
                x = lerp(hx + 5, hx + 1, q)
                y = lerp(hy - 3, FLOOR - 6, ease_in(q))
                pix.blit(g, SKULL if int(loc * 10) % 2 else SKULL.flip(), x, y)
                return None, "skull"
            q = ease_out(span(loc, 8.6, 10.0))
            x = lerp(FX - 10, sx, q)
            if loc < 10.0:
                pix.blit(g, SKULL if int(loc * 8) % 2 else pix.flipped(SKULL), x, sy - (1 if int(loc * 8) % 2 else 0))
            else:
                pix.blit(g, SKULL, sx, sy)
            shake = int(round(math.sin(loc * 30))) if 9.2 < loc < 10.2 else 0
            fox_sit(g, t, head_dx=shake, face="blink" if 9.2 < loc < 10.2 else "normal")
            if 8.6 <= loc < 8.6 + dt * 1.5:
                self.sparks.burst(FX - 6, FLOOR - 2, 6, 14, up=6, life=0.4, gravity=40)
            return None, "skull" if loc < 10.0 else "dipper"
        # 成：噗——化成小道士（露着狐狸尾巴），作揖；再噗地变回来
        back = dur - 2.5
        if abs(loc - 8.0) < dt * 1.5 or abs(loc - back) < dt * 1.5:
            for i in range(9):
                a = i / 9 * 2 * math.pi
                self.puffs.emit(FX + math.cos(a) * 8, FLOOR - 16 + math.sin(a) * 10, vx=math.cos(a) * 8,
                                vy=-4, life=1.0, rmax=3.0, spread=2)
        if loc < 8.25:
            pix.flash(g)
        if loc < back:
            k = loc - 8.0
            pose = "bow" if 2.5 < k % 4.0 < 3.3 else "gong"
            figure(g, FX - 1, FLOOR, t, arm="gong", head="bow" if pose == "bow" else "up",
                   face="happy" if 1.0 < k < 2.5 else "normal", flip=True, behind=fox_tail_behind)
            s = "髑髅不坠" if k < 3.4 else "则化为人"
            return (s if k > 0.5 else None), "person"
        pix.blit(g, SKULL, sx, sy)
        fox_sit(g, t, face="happy" if loc < back + 1.2 else "normal")
        return None, "dipper"

    def mx(self, g: Gfx, t: float, mode: str, lit: int):
        if mode == "person":
            mx_art(g, MX_PERSON)
            return
        if mode == "skull":
            mx_art(g, MX_SKULL)
            return
        for i, (x, y) in enumerate(MX_DIPPER):
            g.mx_set(x, y, i < lit or (t * 1.3 + i * 0.29) % 1 > 0.2)
        g.mx_set(1 + int(t * 3) % 2, 7 - int(t * 5) % 2)
        if lit >= 7:
            g.mx_level = 4

    # ------------------------------------------------------------ 三段

    def enter(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        night(g, t, 0, 0, fade=span(t, 0, 1.4))
        pix.blit(g, SKULL, *SKULL_AT)
        if t < 0.8:
            pass
        elif t < 2.4:
            fox_run(g, lerp(150, FX, ease_out(span(t, 0.8, 2.4))), t)
        else:
            k = t - 2.4
            fox_sit(g, t, head_dy=-1 if k < 0.2 else 0, face="happy" if k < 0.4 else "normal")
        n = int(span(t, 0, 1.4) * 7)
        for i, (x, y) in enumerate(MX_DIPPER[:n]):
            g.mx_set(x, y)

    def hold(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        text, mode, lit = self.frame(g, t, dt)
        self.mx(g, t, mode, lit)
        if text:
            label(g, 126, 2, text, align="right")

    def exit(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        night(g, self.hold_t + t, 0, 0, fade=1 - span(t, 0.2, 1.2))
        pix.blit(g, SKULL, *SKULL_AT)
        if t < 0.25:
            fox_sit(g, self.hold_t + t, face="happy")
        else:
            fox_run(g, lerp(FX, 160, ease_in(span(t, 0.25, 1.2))), t, flip=True)
        for i, (x, y) in enumerate(MX_DIPPER):
            g.mx_set(x, y, (i + 1) / 7 > span(t, 0.2, 1.2))
