"""曳尾涂中：庄子钓于濮水，宁做在泥里拖着尾巴爬的活龟，也不做庙堂上供着的死龟甲。

依据：《庄子·秋水》“庄子钓于濮水……‘吾闻楚有神龟，死已三千岁矣，王巾笥而藏之庙堂之上。此龟者，宁其死为留骨而贵乎？
宁其生而曳尾于涂中乎？’……‘往矣！吾将曳尾于涂中。’”

入场：濮水、泥滩、芦苇；小道士（代庄子）坐在左边岸石上把竿一甩，浮漂落水溅起水花；泥里的乌龟从壳里探出头来。
持续：乌龟在泥滩上一步一顿地慢慢爬（四腿交替、头一伸一伸），爬到头就转身往回爬，尾巴在泥里拖出一道弯弯的痕、两边是脚印；
      小道士钓鱼，呼吸眨眼，浮漂随水一起一伏，水波流动，芦苇摇。
      hold 9 秒起每 23 秒：浮漂一沉一沉起涟漪，小道士瞪眼，猛地提竿——空钩，浮漂飞起又落回，小道士笑。
      hold 30 秒起每 37 秒：一只蜻蜓飞来停在龟头前，乌龟把头一缩，蜻蜓飞走，头再慢慢探出来。
      hold 18 秒起每 50 秒：乌龟停下，头上冒出念头——庙堂里供桌上锦巾盖着的匣子里放着龟甲；乌龟缩脖子、摇头，
      念头“啪”地破掉，上方写出“吾将曳尾于涂中”。
收场：乌龟缩进壳里，小道士收竿。
点阵：俯视的乌龟（四腿交替划动、缩头时头消失、摇头时头左右摆）；念头时是庙堂。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Clock, ev, label, mx_art, wobble

FLOOR = 58                 # 泥滩地面（乌龟脚底）
WATER_Y = 47               # 水面
XA, XB = 66, 108           # 乌龟来回爬的两端（中心 x）
SPEED = 0.8                # px/s
TURN = 3.0                 # 掉头停顿
LEG = (XB - XA) / SPEED
LOOP = 2 * (LEG + TURN)
THINK0, THINK_P, THINK_D = 18.0, 50.0, 10.0
NIBBLE0, NIBBLE_P = 9.0, 23.0
FLY0, FLY_P = 30.0, 37.0
DAO = (13, 43)             # 小道士坐的位置（脚底中点）
BOB_X = 36                 # 浮漂 x
ROD_TIP = (40, 20)

# ---------------------------------------------------------------- 乌龟（朝右；壳、头、腿、尾分开贴）

SHELL = Sprite("""
       #########
    ###.##.#.##.###
  ####.####.####.####
 #####.####.####.#####
 #.#..#....#....#....#
######.####.####.#.#.#.
######.####.####..#.#.#
######.####.####.#.#.#.
#.....................#
 ##.##.##.##.##.##.###
  ###################
""")

HEAD = dict(zip(["out", "blink", "in", "happy"], pix.frames("""
      ####
     ######
    ####.###
   ####..###
  ##########
 #######.##
######
#####
####
---
      ####
     ######
    ########
   ####..###
  ##########
 #######.##
######
#####
####
---
.##
#.#
###
---
      ####
     ######
    ###.####
   ###.#.###
  ##########
 ######..##
######
#####
####
""")))

LEGS = pix.frames("""
###
####
 ###
#.##
---
###
###
###
.##.
""")  # 前伸 / 后蹬（近侧腿）

FAR_LEG = Sprite("""
#.#
.#.
#.#
""")

TAIL = Sprite("""
 ##
###
#
""")

BOBBER = pix.frames("""
 #
 #
###
#.#
.#.
---
 #
 #
###
#.#
""")

REED = pix.frames("""
  #
 ###
 #.#
 #.#
 ###
  #     #
  #    #
  #   #
  #  #
  # #
 ## #
  ###
  ##
---
   #
  ###
  #.#
  #.#
  ###
  #     #
  #     #
  #    #
  #   #
  #  #
 ## #
  ###
  ##
""")

DRAGONFLY = pix.frames("""
 # #
######.
 # #
---
# #
######.
# #
""")

MX_TURTLE = {
    "walk0": ["   ##   ", "#  ##  #", " ###### ", " #.##.# ", " #.##.# ", " ###### ", "#  ##  #", "   #    "],
    "walk1": ["   ##   ", "   ##   ", "####### ", " #.##.# ", " #.##.# ", "########", "   ##   ", "   #    "],
    "in": ["        ", "        ", " ###### ", " #.##.# ", " #.##.# ", " ###### ", "        ", "        "],
}
MX_TEMPLE = ["   ##   ", " ###### ", "########", " #    # ", " # ## # ", " #.##.# ", " ###### ", "########"]


def _rod_arm():
    """持竿的手臂：袖子前伸，手握拳"""
    p = Part(13, 8)
    p.shape("polygon", [(0, 0), (4, 0), (10, 2), (10, 6), (2, 6), (0, 4)], fill=1)
    p.d.line((9, 2, 9, 6), fill=0)
    p.dither([(2, 4), (10, 4), (10, 6), (2, 6)], 0.5, 0)
    p.shape("rectangle", (10, 2, 12, 5), fill=1)
    p.d.line((11, 3, 12, 3), fill=0)
    spr = p.sprite()
    spr.hand = (11, 2)
    return spr


def _rock():
    """岸石 26×20：块面、裂纹、苔点"""
    p = Part(26, 20)
    p.shape("polygon", [(0, 3), (5, 0), (16, 0), (22, 3), (25, 10), (24, 19), (0, 19)], fill=1)
    p.d.line((5, 1, 16, 1), fill=0)
    p.d.line((16, 1, 21, 4), fill=0)
    p.d.line((12, 5, 9, 10), fill=0)
    p.d.line((9, 10, 11, 14), fill=0)
    p.dither([(14, 6), (22, 4), (24, 19), (16, 19)], 0.5, 0)
    p.dither([(0, 12), (12, 12), (12, 19), (0, 19)], 0.25, 0)
    p.px(4, 3, 0), p.px(7, 4, 0), p.px(19, 8, 0)
    return p.sprite()


def _temple():
    """念头里的庙堂 22×15：屋顶（檐角起翘）、两柱、供桌上锦巾盖着的匣子，匣上放龟甲"""
    p = Part(22, 15)
    p.shape("polygon", [(0, 5), (4, 2), (17, 2), (21, 5), (17, 4), (4, 4)], fill=1)
    p.shape("polygon", [(7, 2), (9, 0), (12, 0), (14, 2)], fill=1)
    p.shape("rectangle", (3, 5, 4, 14), fill=1)
    p.shape("rectangle", (17, 5, 18, 14), fill=1)
    p.shape("rectangle", (6, 11, 15, 12), fill=1)                 # 供桌
    p.shape("rectangle", (7, 13, 7, 14), fill=1)
    p.shape("rectangle", (14, 13, 14, 14), fill=1)
    p.shape("polygon", [(7, 10), (8, 8), (13, 8), (14, 10)], fill=1)   # 巾笥
    p.dither([(7, 9), (14, 9), (14, 10), (7, 10)], 0.5, 0)
    p.shape("chord", (8, 5, 13, 10), 180, 360, fill=1)            # 龟甲
    p.px(10, 6, 0), p.px(11, 7, 0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"arm": _rod_arm, "rock": _rock, "temple": _temple}[name]()
    return _PROPS[name]


# ---------------------------------------------------------------- 路径（暂停按事件扣掉，全由 t 算出）


def walk_s(t: float) -> float:
    """乌龟的“行走时间”：念头事件期间停下"""
    if t < THINK0:
        return t
    n = int((t - THINK0) // THINK_P)
    loc = (t - THINK0) - n * THINK_P
    return t - n * THINK_D - min(loc, THINK_D)


def path(s: float):
    """返回 (x, 朝右?, 在走?, 步相位 0..1)"""
    k = s % LOOP
    step = (s % 1.6) / 1.6
    if k < LEG:
        return XA + _lurch(k), True, True, step
    if k < LEG + TURN:
        return XB, k > LEG + TURN / 2, False, 0.0
    k2 = k - LEG - TURN
    if k2 < LEG:
        return XB - _lurch(k2), False, True, step
    return XA, k2 - LEG > TURN / 2, False, 0.0


def _lurch(k: float) -> float:
    """一步一顿：每 1.6 秒挪 1.6×SPEED 像素（缓入缓出）"""
    n = int(k // 1.6)
    f = (k % 1.6) / 1.6
    return (n + ease_in_out(f)) * 1.6 * SPEED


# ---------------------------------------------------------------- 画


def scenery(g: Gfx, t: float):
    # 远岸：一线堤岸、远山、两棵小树
    for x in range(54, 128, 4):
        g.px(x, 38)
    g.d.line((70, 38, 80, 31), fill=1)
    g.d.line((80, 31, 86, 34), fill=1)
    g.d.line((86, 34, 96, 27), fill=1)
    g.d.line((96, 27, 108, 35), fill=1)
    g.d.line((108, 35, 112, 33), fill=1)
    g.d.line((112, 33, 120, 38), fill=1)
    pix.checker(g, (88, 31, 104, 38), 0.125)
    # 泥滩：地面线、下面稀疏泥点、泥坑
    g.d.line((50, FLOOR, 127, FLOOR), fill=1)
    pix.checker(g, (54, FLOOR + 3, 128, 64), 0.125)
    for x, y, w in ((78, 62, 6), (116, 62, 5)):
        g.d.ellipse((x - w, y - 1, x + w, y + 1), fill=0, outline=1)
    # 水：岸坡 + 浪线流动
    g.d.line((44, WATER_Y, 52, FLOOR), fill=1)
    g.d.line((0, WATER_Y, 44, WATER_Y), fill=1)
    for row, y in enumerate(range(WATER_Y + 3, 64, 4)):
        off = int(t * (2 + row)) % 8
        for x in range(-8 + off + row * 3, 46, 9):
            if x + 4 < 44 + (y - WATER_Y) * 0.9:
                g.d.line((x, y, x + 3, y), fill=1)
                g.px(x + 4, y - 1)
    pix.blit(g, pix.anim(REED, t * 0.6, 1.3), 47, FLOOR - 4 - 13)
    pix.blit(g, pix.anim(REED, t * 0.6 + 0.4, 1.3), 121, FLOOR - 13)
    pix.blit(g, prop("rock"), -3, 42)


def trail(g: Gfx, s: float):
    """尾巴拖出的弯痕 + 两边脚印（按路径的过去位置画）"""
    for k in range(1, 70):
        x, right, moving, _ = path(s - k * 0.6)
        if s - k * 0.6 < 0:
            break
        tx = x - 12 if right else x + 12
        y = FLOOR + 1 + (1 if math.sin(tx * 0.45) > 0 else 0)
        if k < 40 or k % 2 == 0:
            g.px(tx, y)
        if k % 5 == 0:
            g.px(tx + 4, FLOOR + 3, 0)
            g.px(tx - 2, FLOOR, 0)


def turtle(g: Gfx, x: float, right: bool, step: float, moving: bool, head: str = "out", head_dx: int = 0,
           tail_sw: int = 0):
    """乌龟（脚底 FLOOR），x = 壳中心"""
    x = int(round(x))
    f = 1 if right else -1
    sw = SHELL.w

    def at(ox, oy, spr):
        px = x + ox if right else x - ox - spr.w
        pix.blit(g, spr, px, oy, flip=not right)

    lf = int(step * 2) % 2 if moving else 0
    # 远侧腿（网点）
    at(-7 + (1 - lf), FLOOR - 3, FAR_LEG)
    at(5 + lf, FLOOR - 3, FAR_LEG)
    at(-13, FLOOR - 7 + tail_sw, TAIL)
    # 头（缩进去时只露一点）
    hd = HEAD[head]
    lift = 1 if moving and step < 0.5 and head != "in" else 0
    if head == "in":
        at(sw // 2 - 2, FLOOR - 9, hd)
    else:
        stretch = 1 if moving and 0.2 < step < 0.6 else 0
        at(sw // 2 - 5 + stretch + head_dx, FLOOR - 16 - lift, hd)
    at(-sw // 2, FLOOR - 14, SHELL)
    # 近侧腿：一前一后交替
    at(-9 + (lf if moving else 0), FLOOR - 4, LEGS[lf if moving else 0])
    at(5 + ((1 - lf) if moving else 0), FLOOR - 4, LEGS[(1 - lf) if moving else 0])
    return x + f * (sw // 2 + 4), FLOOR - 14   # 头的大致位置


def angler(g: Gfx, t: float, face: str = "normal", tip_dy: float = 0.0, line_to=None):
    """小道士坐在岸石上钓鱼；返回竿梢"""
    tip = (ROD_TIP[0], ROD_TIP[1] + tip_dy)
    out = {}

    def rod(g2, at):
        pass

    h = figure(g, DAO[0], DAO[1], t, legs="sit", arm=prop("arm"), arm_at=(-3, -16), face=face)
    hx, hy = h["hand"]
    # 竿：从手里斜伸出去，梢头微弯
    mx_, my_ = lerp(hx, tip[0], 0.6), lerp(hy, tip[1], 0.6) - 1
    g.d.line((hx - 3, hy + 2, mx_, my_), fill=1)
    g.d.line((mx_, my_, tip[0], tip[1]), fill=1)
    g.d.line((hx - 3, hy + 3, hx + 2, hy), fill=1)
    out["tip"] = tip
    if line_to:
        pix.dotted(g, tip[0], tip[1], line_to[0], line_to[1], step=1)
    return tip


@register
class TurtleRest(Rest):
    id = "x4.turtle"
    name = "曳尾涂中"
    desc = "小道士坐在濮水边垂钓，乌龟在泥滩上一步一顿地爬、拖出一道尾痕；它想起庙堂里供着的龟甲，摇摇头——吾将曳尾于涂中"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    def bobber(self, g: Gfx, t: float, nib):
        """浮漂：随水起伏；咬钩时下沉、提竿时飞起；返回线的下端"""
        bob = wobble(t, 2.2, 1)
        x, y = BOB_X, WATER_Y - 3 + bob
        dip = 0
        if nib is not None:
            loc = nib
            if 0.4 < loc < 0.8 or 1.2 < loc < 1.6:
                dip = 3
            if 2.0 <= loc < 3.2:  # 提竿：浮漂飞起再落回
                q = span(loc, 2.0, 3.2)
                x = lerp(BOB_X, ROD_TIP[0] - 2, math.sin(q * math.pi) * 0.5)
                y = WATER_Y - 3 - math.sin(q * math.pi) * 18
                dip = 0
        if dip:
            for r in (3, 6):
                g.d.arc((x - r - 1, WATER_Y - 1, x + r + 1, WATER_Y + 2), 0, 180, fill=1)
        y += dip
        spr = BOBBER[1] if dip else BOBBER[0]
        pix.blit(g, spr, x - 1, y)
        return (x, y)

    def frame(self, g: Gfx, t: float, dt: float, head_force: str | None = None):
        scenery(g, t)
        s = walk_s(t)
        x, right, moving, step = path(s)
        trail(g, s)
        # 钓鱼
        nb = ev(t, NIBBLE_P, NIBBLE0, 4.0)
        nib = nb[1] if nb else None
        face = "normal"
        tip_dy = 0.0
        if nib is not None:
            if 0.4 < nib < 2.0:
                face = "wow"
                tip_dy = 2 if (0.4 < nib < 0.8 or 1.2 < nib < 1.6) else 0
            elif nib < 2.5:
                tip_dy = -6 * math.sin(span(nib, 2.0, 2.5) * math.pi / 2)
            elif nib < 4.0:
                face = "happy"
                tip_dy = -6 * (1 - span(nib, 2.5, 3.4))
        end = self.bobber(g, t, nib)
        tip = angler(g, t, face, tip_dy, line_to=(end[0], end[1]))
        if nib is not None and 2.0 <= nib < 2.0 + dt * 1.5:
            self.sparks.burst(BOB_X, WATER_Y, 10, 20, up=18, life=0.6, gravity=70)
        # 念头
        th = ev(t, THINK_P, THINK0, THINK_D + 1.5)
        head, head_dx, mode = "out", 0, "walk"
        bubble = None
        text = None
        if th:
            loc = th[1]
            if loc < THINK_D:
                mode = "think" if 1.0 < loc < 6.5 else "walk"
                if loc < 6.5:
                    head = "blink" if 2.0 < loc < 2.3 else "out"
                    bubble = loc
                elif loc < 8.5:   # 缩脖子、摇头
                    head = "in" if loc < 7.0 else ("blink" if int(loc * 6) % 2 else "out")
                    head_dx = 0 if loc < 7.0 else (1 if int(loc * 6) % 2 else -1)
                    if loc < 6.5 + dt * 1.5 and loc >= 6.5:
                        pass
                else:
                    head = "happy"
            if 6.6 < loc < THINK_D + 1.5:
                text = "吾将曳尾于涂中"
        # 蜻蜓
        fl = ev(t, FLY_P, FLY0, 6.0)
        if fl and not th:
            loc = fl[1]
            if 1.6 < loc < 4.2:
                head = "in"
            elif 4.2 <= loc < 4.6:
                head = "blink"
        if head_force:
            head = head_force
        hp = turtle(g, x, right, step, moving and not th, head, head_dx, tail_sw=1 if moving and step > 0.5 else 0)
        if fl and not th:
            loc = fl[1]
            hx, hy = hp
            if loc < 1.5:
                q = ease_out(span(loc, 0, 1.5))
                fx, fy = lerp(140, hx + 2, q), lerp(20, hy - 7, q) + math.sin(loc * 9) * 2
            elif loc < 3.5:
                fx, fy = hx + 2, hy - 7
            else:
                q = ease_in(span(loc, 3.5, 6.0))
                fx, fy = lerp(hx + 2, 150, q), lerp(hy - 7, 6, q)
            fr = DRAGONFLY[int(loc * 20) % 2] if not (1.5 <= loc < 3.5) else DRAGONFLY[0]
            pix.blit(g, fr, fx - 3, fy - 1)
        if bubble is not None:
            self.bubble(g, hp, right, bubble, dt)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if mode == "think":
            mx_art(g, MX_TEMPLE)
        else:
            self.mx_turtle(g, head, step, moving and not th, head_dx)
        return text

    def bubble(self, g: Gfx, hp, right: bool, loc: float, dt: float):
        """念头泡：三个小圈升起 → 大泡里是庙堂 → 啪地破掉"""
        hx, hy = hp
        bx = min(max(hx - 4, 28), 102)
        by = 28
        for i in range(3):
            if loc > 0.3 * i:
                cx = lerp(hx, bx, (i + 1) / 4)
                cy = lerp(hy - 3, by + 10, (i + 1) / 4)
                r = 1 + i * 0.6
                g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1, fill=0)
        if loc < 1.0:
            return
        if loc >= 6.4:
            if loc < 6.4 + dt * 1.5:
                self.sparks.burst(bx, by, 16, 30, life=0.5, gravity=10)
            return
        pop = ease_out_back(span(loc, 1.0, 1.4))
        w, h = 15 * pop, 10 * pop
        g.d.ellipse((bx - w, by - h, bx + w, by + h), fill=0, outline=1)
        g.d.ellipse((bx - w - 3, by - h + 4, bx - w + 5, by + h - 3), fill=0, outline=1)
        g.d.ellipse((bx + w - 5, by - h + 3, bx + w + 3, by + h - 4), fill=0, outline=1)
        g.d.ellipse((bx - w + 1, by - h + 1, bx + w - 1, by + h - 1), fill=0)
        if pop > 0.9:
            pix.blit(g, prop("temple"), bx - 11, by - 8, outline=False)
            if int(loc * 3) % 2 == 0:  # 龟甲上的香火灵光
                g.px(bx - 1, by - 7), g.px(bx + 2, by - 6)

    def mx_turtle(self, g: Gfx, head: str, step: float, moving: bool, head_dx: int):
        if head == "in":
            mx_art(g, MX_TURTLE["in"])
            return
        mx_art(g, MX_TURTLE["walk1" if moving and int(step * 2) % 2 else "walk0"])
        if head_dx:
            g.mx[0, :] = False
            g.mx_set(3 + (1 if head_dx > 0 else -1), 0)
            g.mx_set(4 + (1 if head_dx > 0 else -1), 0)

    # ------------------------------------------------------------ 三段

    def enter(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        scenery(g, t)
        x, right, _, _ = path(0)
        # 甩竿：竿梢从后往前划，浮漂沿弧线落水
        q = span(t, 0.4, 1.6)
        if t < 2.0:
            dy = -14 * (1 - ease_out_back(q)) if q > 0 else -14
            bx, by = ROD_TIP[0] - 1, ROD_TIP[1] - 10
            if 0 < q < 1:
                bx = lerp(ROD_TIP[0] + 6, BOB_X, q)
                by = lerp(ROD_TIP[1] - 6, WATER_Y - 3, ease_in(q)) - math.sin(q * math.pi) * 6
            elif q >= 1:
                bx, by = BOB_X, WATER_Y - 3
            angler(g, t, "normal", tip_dy=dy, line_to=(bx + 1, by))
            pix.blit(g, BOBBER[0], bx - 1, by)
            if abs(t - 1.6) < dt:
                self.sparks.burst(BOB_X, WATER_Y, 10, 18, up=16, life=0.5, gravity=70)
        else:
            end = self.bobber(g, t, None)
            angler(g, t, "happy" if t < 2.6 else "normal", line_to=end)
        turtle(g, x, right, 0, False, "in" if t < 2.3 else ("blink" if t < 2.5 else "out"))
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_art(g, MX_TURTLE["in" if t < 2.3 else "walk0"])

    def hold(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        text = self.frame(g, t, dt)
        if text:
            label(g, 126, 2, text, align="right")

    def exit(self, g: Gfx, t: float):
        h = self.hold_t + t
        scenery(g, h)
        s = walk_s(self.hold_t)
        x, right, _, _ = path(s)
        trail(g, s)
        q = span(t, 0.2, 1.0)
        bx = lerp(BOB_X, ROD_TIP[0] - 1, ease_out(q))
        by = lerp(WATER_Y - 3, ROD_TIP[1] - 4, ease_out(q))
        angler(g, h, "happy", tip_dy=-8 * ease_out(q), line_to=(bx + 1, by))
        pix.blit(g, BOBBER[0], bx - 1, by)
        turtle(g, x, right, 0, False, "in" if t > 0.25 else "blink")
        mx_art(g, MX_TURTLE["in"])
