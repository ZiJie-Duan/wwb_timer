"""青牛西去（歇）：小道士骑着 Q 版青牛，慢悠悠往西走。

依据：刘向《列仙传·老子》“老子西游，关令尹喜望见有紫气浮关，而老子果乘青牛而过也”；
      《史记·老子韩非列传》“乃著书上下篇，言道德之意五千余言而去，莫知其所终”。
画面：侧视的小路，远山、松树、云、路边的草和石子向右缓缓后退（视差）。青牛是正脸大头的 Q 版牛
      （弯角、横耳、大眼带高光、宽鼻头），身披鞍毯，四条短腿对角交替迈步，身子一颠一颠，
      尾巴摆、葫芦晃；小道士盘坐在鞍毯上，呼吸、眨眼。
入场：青牛驮着小道士从右边走进来。
持续：一直在走；一只苍蝇绕着牛屁股飞，尾巴每隔几秒狠狠一甩，苍蝇吓开又飞回。
      每 27 秒：小道士展开竹简读，左上逐字写出一句《道德经》（十句轮换），读完卷起，开心地点头。
      每 40 秒：路边一丛嫩草来到嘴边，青牛停步低头啃草（嚼、草变短，碎草飞），远景也停下，吃完抬头接着走。
      每 33 秒：青牛仰头“哞”一声（闭眼张嘴、声波），小道士吓一跳。
      每 53 秒：一只蝴蝶飞来落在牛角上扇翅，青牛对眼看它，过一会儿蝴蝶飞走。
收场：青牛加快脚步往西（左）走出画面。
点阵：牛脸（弯角、眨眼、哞时张嘴）；读经时是展开的竹简（逐片亮）；啃草时是一丛草。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite, text_width
from ..engine.scene import Rest, register
from .x4_common import CLOUD, Clock, ev, label, mx_art, sound_arcs

FLOOR = 61          # 地面线
BX = 50             # 牛身左上角 x（静止时）
BY = FLOOR - 20     # 牛身左上角 y
SPEED = 5.0         # 走路时远景后退的速度 px/s
STRIDE = 10.0       # 一个步态周期走的距离

# 吃草事件：每 GRAZE_P 秒一次，从 GRAZE_S 开始，持续 GRAZE_D（0–0.8 减速、8.2–9 起步）
GRAZE_S, GRAZE_P, GRAZE_D = 18.0, 40.0, 9.0
READ_S, READ_P, READ_D = 6.0, 27.0, 13.0
MOO_S, MOO_P, MOO_D = 31.0, 33.0, 2.2
FLY_S, FLY_P, FLY_D = 44.0, 53.0, 14.0

LINES = ["上善若水", "道法自然", "大巧若拙", "知足不辱", "见素抱朴", "大音希声", "柔弱胜刚强", "少私寡欲",
         "天长地久", "大器晚成"]

# ---------------------------------------------------------------- 精灵

class _Grid:
    """按行填充的小画格（生成字符画精灵用）"""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [[" "] * w for _ in range(h)]

    def rows(self, d, c="#"):
        for y, (a, b) in d.items():
            for x in range(a, b + 1):
                self.g[y][x] = c

    def pts(self, ps, c="#"):
        for x, y in ps:
            self.g[y][x] = c

    def sprite(self):
        return Sprite("\n".join("".join(r) for r in self.g))


def _head(eyes="open", mouth="shut") -> Sprite:
    """正脸 Q 版牛头 23×19：粗月牙弯角、头顶一撮毛、横耳、大眼高光、腮红、宽鼻头两个鼻孔"""
    h = _Grid(23, 19)
    h.rows({4: (7, 15), 5: (5, 17), 6: (4, 18), 7: (3, 19), 8: (3, 19), 9: (3, 19), 10: (3, 19), 11: (3, 19),
            12: (3, 19), 13: (3, 19), 14: (3, 19), 15: (3, 19), 16: (4, 18), 17: (5, 17), 18: (7, 15)})
    horn = [(5, 5), (6, 5), (3, 4), (4, 4), (5, 4), (2, 3), (3, 3), (4, 3), (1, 2), (2, 2), (3, 2), (1, 1), (2, 1),
            (1, 0)]
    h.pts(horn + [(22 - x, y) for x, y in horn])
    h.pts([(10, 3), (11, 2), (12, 3), (11, 3)])           # 头顶一撮毛
    h.rows({7: (0, 2), 8: (0, 2)})
    h.rows({7: (20, 22), 8: (20, 22)})
    h.pts([(1, 8), (21, 8), (3, 7), (19, 7), (3, 8), (19, 8)], ".")
    h.pts([(5, 12), (6, 11), (7, 11), (15, 11), (16, 11), (17, 12), (4, 13), (18, 13)], ".")   # 口鼻轮廓
    h.pts([(8, 14), (14, 14)], ".")                       # 鼻孔
    eye = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2), (1, 2)]
    for ex in (7, 14):
        if eyes == "open":
            h.pts([(ex + x, 7 + y) for x, y in eye], ".")
            h.pts([(ex, 7)])
        elif eyes == "shut":                              # 闭眼 ︶
            h.pts([(ex, 9), (ex + 1, 9), (ex - 1 if ex == 7 else ex + 2, 8)], ".")
        elif eyes == "happy":                             # 笑眼 ^
            h.pts([(ex - 1, 9), (ex, 8), (ex + 1, 8), (ex + 2, 9)], ".")
        elif eyes == "cross":                             # 对眼：眼珠挤到内上角
            d = 1 if ex == 7 else 0
            h.pts([(ex + d, 7), (ex + d, 8), (ex + (0 if d else 1), 7)], ".")
    if mouth == "open":                                   # 哞：张大嘴
        h.rows({15: (9, 13), 16: (10, 12)}, ".")
        h.pts([(11, 17)], ".")
    elif mouth == "chew":
        h.pts([(10, 16), (12, 15)], ".")
    elif mouth == "chew2":
        h.pts([(10, 15), (12, 16)], ".")
    else:
        h.rows({16: (10, 12)}, ".")
    return h.sprite()


def _heads() -> dict:
    return {"open": _head(), "blink": _head("shut"), "happy": _head("happy"), "moo": _head("shut", "open"),
            "chew": _head("shut", "chew"), "chew2": _head("shut", "chew2"), "cross": _head("cross")}


BODY = Sprite("""
      ###########
    #############...................
   ##############.#################.###
  ####.##########.#...............#.###.##
 ####.###########.#.#############.#.####.##
 ####.###########.#.#..##..##..##.#.#####.##
#####.###########.#.#...#...#...#.#.######.##
######.##########.#.#############.#.######.##
#################.#...............#.######.##
#################.#################.#####.###
#################...................#########
##################.#.#.#.#.#.#.#.#.##########
 ###.###.###.###.###.###.###.###.###.###.###
  #.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#
   #.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#
     .#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.

""")

LEG = pix.frames("""
####
####
####
####
####
####
#.##
---
####
####
####
 ####
 #.##
""")

LEG_FAR = pix.frames("""
#.#.
.#.#
#.#.
.#.#
#.#.
.#.#
#.##
---
#.#.
.#.#
#.#.
 #.#.
 #.##
""")

TAIL = pix.frames("""
##
 #
 #
 #
 #
 #
 ##
 ###
 ##
---
##
 #
  #
  #
  #
  #
  ##
  ###
  ##
---
###
   ##
     ##
       ####
       #####
        ##
""")

GOURD = Sprite("""
  #
 ###
 #.#
 ###
  #
 ###
#####
##.##
#####
 ###
""")

FLY = pix.frames("""
# #
 #
---
 #
 #
""")

BUTTERFLY = pix.frames("""
##   ##
### ###
 #####
 ## ##
---
 ## ##
  ###
  ###
   #
---
   ##
  ###
   ##
   #
""")

PINE = Sprite("""
   #
  ###
   #
 #####
  ###
#######
 #####
   #
   #
""")


def _scroll_arm() -> Sprite:
    """读经的手臂：袖子前伸，两手捧着展开的竹简（朝右画，figure 会翻转）"""
    p = Part(22, 14)
    p.shape("polygon", [(0, 5), (4, 5), (10, 8), (10, 12), (2, 12), (0, 10)], fill=1)
    p.d.line((9, 8, 9, 12), fill=0)
    p.dither([(2, 10), (10, 10), (10, 12), (2, 12)], 0.5, 0)
    p.shape("rectangle", (10, 8, 12, 11), fill=1)
    p.shape("rectangle", (12, 0, 21, 9), fill=1)          # 竹简
    for x in range(13, 21, 2):
        p.d.line((x, 1, x, 8), fill=0)
    p.d.line((12, 2, 21, 2), fill=0)                       # 编绳
    p.d.line((12, 7, 21, 7), fill=0)
    for x in range(14, 21, 2):                             # 字（一片一个小点）
        p.px(x, 4, 0) if x % 4 else p.px(x, 5, 0)
    spr = p.sprite()
    spr.hand = (12, 9)
    return spr


def _far_hills() -> Sprite:
    """远山（256 宽可循环）：山脊线 + 背光坡的竖排点"""
    W = 256
    import numpy as np
    on = np.zeros((22, W), bool)
    mk = np.zeros((22, W), bool)
    hs = []
    for x in range(W):
        a = x / W * 2 * math.pi
        h = 10 + 5 * math.sin(a * 2 + 0.6) + 3 * math.sin(a * 5 + 1.3) + 1.5 * math.sin(a * 11)
        hs.append(int(round(h)))
    for x in range(W):
        y = hs[x]
        on[y, x] = mk[y, x] = True
        nx = hs[(x + 1) % W]
        if abs(nx - y) > 1:  # 陡处补线
            for yy in range(min(y, nx), max(y, nx)):
                on[yy, x] = mk[yy, x] = True
        if nx > y and x % 2 == 0:  # 背光坡：竖排点
            for yy in range(y + 2, min(y + 7, 21), 2):
                on[yy, x] = mk[yy, x] = True
    return Sprite(on=on, mask=mk)


_S: dict = {}


def S(name):
    if name not in _S:
        _S.update(_heads())
        _S["scroll"] = _scroll_arm()
        _S["hills"] = _far_hills()
    return _S[name]


# ---------------------------------------------------------------- 走路距离（吃草时停下）

def _lost(L: float) -> float:
    """一次吃草窗口里，从开始到 L 秒“少走”的时间"""
    if L < 0.8:
        return L * L / 1.6
    if L < 8.2:
        return 0.4 + (L - 0.8)
    L = min(L, GRAZE_D)
    return 7.8 + (L - 8.2) - (L - 8.2) ** 2 / 1.6


def walk_time(t: float) -> float:
    """按走路折算的时间（吃草停下的时间扣掉）"""
    if t < GRAZE_S:
        return t
    k = t - GRAZE_S
    n = int(k // GRAZE_P)
    return t - n * _lost(GRAZE_D) - _lost(k - n * GRAZE_P)


def speed(t: float) -> float:
    e = ev(t, GRAZE_P, GRAZE_S, GRAZE_D)
    if not e:
        return 1.0
    L = e[1]
    return 1 - L / 0.8 if L < 0.8 else (0.0 if L < 8.2 else (L - 8.2) / 0.8)


# ---------------------------------------------------------------- 背景

def scenery(g: Gfx, dist: float, t: float):
    """远山（0.15×）、松（0.4×）、云、地面与路边小物（1×）"""
    hills = S("hills")
    off = int(dist * 0.15) % 256
    for k in (-256, 0):
        pix.blit(g, hills, off + k, FLOOR - 36, outline=False)
    for i in range(2):  # 两朵云，自己也慢慢飘
        cx = (dist * 0.08 + t * 1.2 + i * 70 + 20) % 200 - 36
        pix.blit(g, CLOUD[i], cx, 4 + i * 9, outline=True)
    off = dist * 0.4
    for i in range(6):  # 远处几棵松
        x = (i * 47 + 13 * (i % 3) + off) % 282 - 20
        pix.blit(g, PINE, x, FLOOR - 21 - (i % 2) * 2)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-8, 136, 8):  # 路面的车辙小点
        xx = int(x + dist) % 136 - 4
        g.px(xx, FLOOR + 2)
        g.px(xx + 3, FLOOR + 1)
    for i in range(10):  # 路边的石子、草丛、小花
        wx = i * 31 + (i * 7) % 11
        x = (wx + dist) % 310 - 20
        kind = (i * 5) % 3
        if kind == 0:
            pix.blit(g, pix.anim(TUFT_FR, t + i * 0.3, 1.2), x, FLOOR - 4)
        elif kind == 1:
            pix.blit(g, PEBBLE_S, x, FLOOR - 2)
        else:
            pix.blit(g, FLOWER_S, x, FLOOR - 5)


TUFT_FR = pix.frames("""
 # # #
# ## #
 ####
---
  # # #
 # ## #
  ####
""")
PEBBLE_S = Sprite("""
 ###
##.##
""")
FLOWER_S = Sprite("""
#.#
 #
 #
 #
""")

GRAZE_GRASS = pix.frames("""
 #   #   #
 #   #  #
  # #  # #
#  # # # #
 # # # ##
 ## ## # #
  ######
---
 #      #
  #  # # #
 # # # ##
 ## ## # #
  ######
---
  #  #  #
 # ## ##
  #####
""")

STALK = pix.frames("""
  ###
 # # #
#  #  #
#  #   #
  #
---
  ###
 # # #
#  #  #
   #
---
  ##
 # #
""")


# ---------------------------------------------------------------- 牛与小道士

def ox_and_rider(g: Gfx, bx: float, phase: float, t: float, head="open", head_dy=0, tail=0, rider_arm="down",
                 rider_face="normal", gourd_sw=0.0, rider_dy=0):
    """phase：步态（距离 / STRIDE），控制四条腿与身子的颠"""
    bx = int(round(bx))
    q = phase % 1
    bob = 1 if (q * 2) % 1 < 0.3 else 0
    by = BY + bob

    def leg_at(sprs, x0, ph, top):
        k = (phase + ph) % 1
        if k < 0.35:   # 抬腿：短一截、向前（左）伸
            pix.blit(g, sprs[1], bx + x0 - 1 - (1 if k > 0.15 else 0), top)
        else:          # 着地：随身子前进往后滑
            slide = int(round(lerp(-1, 1, (k - 0.35) / 0.65)))
            pix.blit(g, sprs[0], bx + x0 + slide, top)

    leg_top = BY + 13
    leg_at(LEG_FAR, 11, 0.5, leg_top - 1)
    leg_at(LEG_FAR, 38, 0.0, leg_top - 1)
    pix.blit(g, TAIL[tail], bx + 42, by + 3)
    pix.blit(g, BODY, bx, by)
    leg_at(LEG, 4, 0.0, leg_top)
    leg_at(LEG, 31, 0.5, leg_top)
    # 葫芦挂在鞍毯右下，随步子晃
    sw = int(round(gourd_sw))
    gx, gy = bx + 37, by + 5
    g.d.line((gx, gy, gx + sw, gy + 3), fill=1)
    pix.blit(g, GOURD, gx + sw - 2, gy + 3)
    # 小道士盘坐在鞍毯上（朝左）
    arm = S("scroll") if rider_arm == "scroll" else rider_arm
    figure(g, bx + 26, by + 2 + rider_dy, t, legs="sit", arm=arm,
           arm_at=(-3, -21) if rider_arm == "scroll" else None, face=rider_face, flip=True)
    # 头（最后画，压在身子前面）
    pix.blit(g, S(head), bx - 14, by - 6 + head_dy)
    return bx, by


def mx_ox(g: Gfx, mode: str, t: float, k: float = 0.0):
    if mode == "read":
        n = int(k * 8)
        g.mx[1, :] = g.mx[6, :] = True
        for x in range(0, min(n, 8)):
            g.mx[2:6, x] = x % 2 == 0
        g.mx[3, :] |= [x < n for x in range(8)]
        return
    if mode == "grass":
        rows = ["..#..#..", ".#.#.#.#", ".#.##.#.", "#..##.#.", ".#.####.", "..####..", "########", "........"]
        if int(t * 3) % 2:
            rows[0] = ".#....#."
        mx_art(g, rows)
        return
    rows = ["#......#", "##....##", ".######.", "###..###", ".######.", "#.#..#.#", ".######.", "..####.."]
    if mode == "blink":
        rows[3] = "########"
    rows[3] = rows[3] if mode != "blink" else "########"
    if mode == "open":
        rows[3] = "##.##.##"
    if mode == "moo":
        rows[3] = "########"
        rows[6] = ".##..##."
        rows[7] = "..#..#.."
    mx_art(g, rows)


@register
class QingNiu(Rest):
    id = "x4.qingniu"
    name = "青牛西去"
    desc = "小道士骑着正脸大头的 Q 版青牛慢慢往西走，远山松云后退；读《道德经》、停下啃草、哞一声、蝴蝶落牛角"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.clock = Clock()
        self.bits = pix.Sparks(self.seed)
        self.line0 = self.rng.randrange(len(LINES))

    # ------------------------------------------------------------ 状态（全按 t 算）

    def state(self, t: float):
        wt = walk_time(t)
        dist = wt * SPEED
        st = dict(dist=dist, phase=dist / STRIDE, head="open", head_dy=0, tail=0, arm="down", face="normal",
                  mx="open", mxk=0.0, read=None, graze=None, moo=None, fly=None, stalk=None)
        if (t % 4.3) < 0.15:
            st["head"], st["mx"] = "blink", "blink"
        st["tail"] = int(t * 1.6) % 2
        st["head_dy"] = 0
        r = ev(t, READ_P, READ_S, READ_D)
        if r:
            n, L = r
            st["read"] = (n, L)
            if 0.6 < L < READ_D - 0.6:
                st["arm"] = "scroll"
                st["mx"], st["mxk"] = "read", span(L, 0.6, 3.0)
            if READ_D - 1.6 < L < READ_D - 0.4:
                st["face"] = "happy"
        gz = ev(t, GRAZE_P, GRAZE_S, GRAZE_D)
        if gz:  # 停下 → 低头咬一口 → 嚼（嘴边挂着草）→ 再咬一口 → 嚼 → 抬头走
            n, L = gz
            st["graze"] = (n, L)
            dip = max(span(L, 0.8, 1.1) - span(L, 1.3, 1.7), span(L, 4.0, 4.3) - span(L, 4.5, 4.9))
            st["head_dy"] = int(round(ease_in_out(dip) * 4))
            for a, b in ((1.4, 3.9), (4.7, 7.9)):
                if a < L < b:
                    st["head"] = "chew" if int(L * 4) % 2 == 0 else "chew2"
                    st["stalk"] = min(2, int((L - a) / (b - a) * 3))
                    st["mx"] = "grass"
            if st["arm"] != "scroll":
                st["face"] = "happy"
        mo = ev(t, MOO_P, MOO_S, MOO_D)
        if mo and not gz:
            n, L = mo
            st["moo"] = L
            if 0.3 < L < 1.9:
                st["head"], st["mx"] = "moo", "moo"
                st["head_dy"] = -1
                st["face"] = "wow"
        fl = ev(t, FLY_P, FLY_S, FLY_D)
        if fl:
            st["fly"] = fl[1]
            if 4.0 < fl[1] < 10.5 and st["head"] == "open" and not gz:
                st["head"] = "cross"
        return st

    def draw(self, g: Gfx, t: float, bx: float, st: dict, dt: float, text: bool = True):
        dist = st["dist"]
        scenery(g, dist, t)
        # 嫩草丛：上一丛（吃剩的草茬，向右退出画面）与下一丛（从左边迎上来，停步时正好在嘴下）
        if t >= GRAZE_S - 30:
            n0 = int((t - GRAZE_S) // GRAZE_P) if t >= GRAZE_S else -1
            for n in (n0, n0 + 1):
                if n < 0:
                    continue
                gx = BX - 3 + dist - walk_time(GRAZE_S + n * GRAZE_P + 0.8) * SPEED
                if -8 < gx < 136:
                    L = t - (GRAZE_S + n * GRAZE_P)
                    eat = 0 if L < 1.1 else (1 if L < 4.3 else 2)
                    spr = GRAZE_GRASS[eat]
                    pix.blit(g, pix.anim(GRAZE_GRASS[eat:eat + 1], 0), gx - spr.w // 2, FLOOR - spr.h)
        step = st["phase"]
        sw = math.sin(step * 2 * math.pi) * 1.2
        tail = st["tail"]
        swat = (t % 7.0) < 0.5
        if swat:
            tail = 2
        bx, by = ox_and_rider(g, bx, step, t, st["head"], st["head_dy"], tail, st["arm"], st["face"], sw)
        if st["stalk"] is not None:  # 嘴角挂着的草，越嚼越短
            spr = STALK[st["stalk"]]
            jig = int(t * 8) % 2
            pix.blit(g, spr, bx - 3 - spr.w // 2 + jig, by - 6 + 16 + st["head_dy"])
            gz = st["graze"]
            if gz and int(gz[1] * 4) != int((gz[1] - dt) * 4) and int(gz[1] * 4) % 3 == 0:
                self.bits.burst(bx - 6, by + 10, 1, 10, up=8, life=0.5, gravity=50)
        # 苍蝇：绕着牛屁股飞；尾巴一甩就被吓开，再慢慢飞回
        k = t % 7.0
        away = ease_out(span(k, 0.1, 0.6)) * (1 - ease_in_out(span(k, 0.6, 3.0)))
        fx = bx + 52 + math.sin(t * 5.1) * 4 + away * 18
        fy = by + 3 + math.sin(t * 7.3) * 3 - away * 14
        pix.blit(g, FLY[int(t * 20) % 2], fx, fy, outline=False)
        if swat and k < 0.15:
            g.px(bx + 54, by + 2), g.px(bx + 56, by + 5)
        # 蝴蝶落牛角
        fl = st["fly"]
        if fl is not None:
            hx, hy = bx - 14 + 2, by - 6 + st["head_dy"] - 2   # 左角尖
            if fl < 4.0:
                q = ease_out(fl / 4.0)
                x = lerp(-6, hx, q)
                y = lerp(14, hy, q) + math.sin(fl * 6) * 3 * (1 - q)
                fr = int(fl * 10) % 2
            elif fl < 10.5:
                x, y = hx, hy
                fr = 0 if int(fl * 2) % 3 else 2
            else:
                q = ease_in(span(fl, 10.5, FLY_D))
                x = lerp(hx, hx - 20, q) + math.sin(fl * 5) * 2
                y = lerp(hy, -8, q)
                fr = int(fl * 10) % 2
            pix.blit(g, BUTTERFLY[fr], x - 3, y - 4)
        mo = st["moo"]
        if mo is not None and 0.3 < mo < 1.9:
            sound_arcs(g, bx - 15, by + 8 + st["head_dy"], (mo * 1.5) % 1, d=-1)
        self.bits.step(dt)
        self.bits.draw(g, trail=False)
        mx_ox(g, st["mx"], t, st["mxk"])
        rd = st["read"]
        if text and rd and 1.4 < rd[1] < READ_D - 0.5:
            s = LINES[(rd[0] + self.line0) % len(LINES)]
            n = min(len(s), int((rd[1] - 1.4) * 2.5) + 1)
            label(g, 3, 3, s[:n])

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        q = ease_out(span(t, 0, self.T["enter"]))
        bx = lerp(140, BX, q)
        st = self.state(0.0)
        st["phase"] = -(140 - bx) / STRIDE
        st["head"] = "blink" if (t % 4.3) < 0.15 else "open"
        st["mx"] = st["head"]
        self.draw(g, t, bx, st, dt)

    def hold(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        self.draw(g, t, BX, self.state(t), dt)

    def exit(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        t0 = self.hold_t
        st = self.state(t0)
        q = ease_in(span(t, 0, self.T["exit"]))
        bx = BX - q * 110
        st["phase"] += t * 1.6
        st["head"], st["head_dy"], st["graze"], st["moo"], st["fly"] = "happy", 0, None, None, None
        st["face"], st["arm"], st["read"] = "happy", "down", None
        self.draw(g, t0 + t, bx, st, dt, text=False)
