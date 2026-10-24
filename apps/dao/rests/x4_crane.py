"""鹤归华表：丁令威学道成仙，化鹤归辽，停在城门华表柱上。

依据：《搜神后记》卷一“丁令威，本辽东人，学道于灵虚山。后化鹤归辽，集城门华表柱。时有少年，举弓欲射之，
鹤乃飞，徘徊空中而言曰：‘有鸟有鸟丁令威，去家千年今始归。城郭如故人民非，何不学仙冢累累。’遂高上冲天。”
（原文的少年举弓，这里换成小道士路过仰望——不画射箭。）

入场：鹤从右上方扇着翅膀划一道弧飞来，落到华表顶上，落地一蹲、收翅站定。
持续：华表（承露盘、云板、龙鳞柱、须弥座）上立着丹顶鹤，右边远处城墙与城楼，左边冢累累，云慢慢飘。
      鹤一直有小动作：呼吸、眨眼、回头、梳羽、单脚独立、仰头长鸣（声波）。
      hold 12 秒起每 50 秒：小道士从右边走来，抬头看见鹤，惊喜地一指；鹤低头看他、一蹲腾空，绕着城楼盘旋，
      空中逐字写出诗的一句（四句轮换）；小道士仰头挥手；鹤滑翔落回柱顶，小道士拱手一揖，走开。
收场：鹤展翅冲天而去（遂高上冲天）；若正在空中，就从那里直接向上冲走。
点阵：鹤头（丹顶、眨眼，长鸣时张嘴、有声线）；飞的时候是上下扇动的翅膀。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx, text_width
from ..engine.scene import Rest, register
from .x4_common import CLOUD, PEBBLE, Clock, ev, label, mx_art, sound_arcs, tuft

FLOOR = 60
PX, PY = 30, 36          # 华表柱顶（鹤脚）
DX = 54                  # 小道士站的位置
EV0, EV_P, EV_D = 12.0, 50.0, 24.0
POEM = ["有鸟有鸟丁令威", "去家千年今始归", "城郭如故人民非", "何不学仙冢累累"]
CIRCLE = (92, 26, 22, 4)  # 盘旋：中心 x, y，半径 rx, ry

# ---------------------------------------------------------------- 鹤（朝右；部件分开贴，自动黑边分开）

BODY = pix.frames("""
         ######
      ###########
    ##############
  .#.#.###########
 .#.#.#.#.....####
.#.#.#.#.#######
 .#.#.#.#######
  .#.#.#####
   .#.#.
    .#.
""")[0]

# 脖子 + 头（15 行，最下两行接在胸前）：up 立 / blink 眨眼 / call 仰头张嘴 / look 回头 / preen 梳羽 / down 低头看
NECK = dict(zip(["up", "blink", "call", "look", "preen", "down"], pix.frames("""
       #.#
      #####
      #.######
      #########
       ##
       ##
       #.
       ##
      #.
      ##
      #.
      ##
      ##
     ###
     ####
---
       #.#
      #####
      ########
      #########
       ##
       ##
       #.
       ##
      #.
      ##
      #.
      ##
      ##
     ###
     ####
---
          #
      #  #
     #.###
    #####
    ##.#
    ####
     ##
     #.
     ##
     #.
     ##
     #.
     ##
     ###
     ####
---
    #.#
   #####
######.#
 ########
    ##
    ##
    .#
    ##
     .#
     ##
     .#
     ##
     ##
     ###
     ####
---




      ###
     ##.##
    ##   ##
  ##.#    #.
  #.##    ##
   .#    ##
         ##
        ###
       ####
       #####
---
       #.#
      #####
      #.###
      ######
       ## ##
       ##   #
       #.
       ##
      #.
      ##
      #.
      ##
      ##
     ###
     ####
""")))
NECK_DX = {"up": 0, "blink": 0, "call": 1, "look": 1, "preen": -2, "down": 0}

LEGS = pix.frames("""
  #  #
  #  #
  #  #
  ## ##
   #  #
   #  #
   #  #
   #  #
   #  #
  ######
---
  #  #
  #  ##
  #   ##
  ##   #
   #
   #
   #
   #
   #
  ###
---
  #  #
  ## ##
   #  #
  ## ##
  #  #
  #  #
 ######
""")  # 两脚 / 单脚独立 / 下蹲

FLY_BODY = pix.frames("""
                            #.#
                           #####
                     #.#.#.###.#####
          ######################
#    .#.#.#.################
####.#.#.#.##.......###
 ####.#.#.##########
 #     #.#
""")[0]

WING = pix.frames("""
  #.#
  .#.#.
   .#.#.#
   #.#.#.#
    #.#.#.##
    .#.#.####
     #..######
      #########
      #..#######
       ##########
        #..#######
         #########
           #######
---
         #############
    .#.#.#############
#.#.#.#.####.##.#####
 #.#.#.#.#.##.###
   .#.#.####
      .#.
---
           #######
         #..######
        #########
       #..######
      #########
     #..#####
    #.#.#.#.
   #.#.#.#
   .#.#.
  .#.#
  #.
""")  # 上 / 平 / 下（黑色的初级飞羽用网点）

WXY = [(2, -9), (-1, 1), (2, 4)]  # 各帧翅膀左上角相对机身左上角

# ---------------------------------------------------------------- 华表、城郭、冢


def _huabiao():
    """华表 22×25：承露盘、云板（两端卷云）、龙鳞柱、须弥座"""
    p = Part(22, 25)
    p.shape("polygon", [(5, 0), (16, 0), (14, 2), (7, 2)], fill=1)      # 承露盘
    p.d.line((6, 1, 15, 1), fill=0)
    p.shape("rectangle", (8, 3, 13, 23), fill=1)                         # 柱身
    p.d.line((8, 3, 13, 3), fill=0)
    for y in range(10, 20, 3):                                           # 龙鳞（小弧）
        for x in (9, 11):
            p.px(x, y + (x == 11), 0), p.px(x + 1, y + 1 + (x == 11), 0)
    p.dither([(12, 4), (13, 4), (13, 23), (12, 23)], 0.5, 0)             # 背光
    p.shape("rectangle", (1, 5, 20, 7), fill=1)                          # 云板
    p.d.line((3, 6, 18, 6), fill=0)
    for x, d in ((0, 1), (21, -1)):                                      # 两端卷云
        p.shape("ellipse", (x - 1 if d > 0 else x - 3, 3, x + 3 if d > 0 else x + 1, 7), fill=1)
        p.px(x + d, 5, 0)
    p.shape("rectangle", (6, 21, 15, 22), fill=1)                       # 须弥座
    p.shape("rectangle", (4, 23, 17, 24), fill=1)
    p.d.line((7, 22, 14, 22), fill=0)
    for x in range(5, 17, 2):
        p.px(x, 24, 0)
    return p.sprite()


def _gate():
    """城楼 30×16：两重檐、檐角起翘、柱间门窗"""
    p = Part(30, 16)
    p.shape("polygon", [(0, 6), (4, 3), (25, 3), (29, 6), (25, 5), (4, 5)], fill=1)   # 上檐
    p.shape("polygon", [(9, 3), (12, 0), (17, 0), (20, 3)], fill=1)                    # 屋顶
    p.shape("rectangle", (5, 6, 24, 9), fill=1)
    for x in range(7, 24, 4):
        p.shape("rectangle", (x, 7, x + 1, 9), fill=0)
    p.shape("polygon", [(1, 12), (4, 10), (25, 10), (28, 12), (25, 11), (4, 11)], fill=1)  # 下檐
    p.shape("rectangle", (4, 12, 25, 15), fill=1)
    p.dither([(4, 12), (25, 12), (25, 15), (4, 15)], 0.5, 0)
    p.px(14, 1, 0), p.px(15, 1, 0)
    return p.sprite()


def _mound():
    """坟冢 13×7：土丘 + 小碑"""
    p = Part(13, 9)
    p.shape("chord", (0, 3, 12, 14), 180, 360, fill=1)
    p.dither([(0, 3), (12, 3), (12, 9), (0, 9)], 0.25, 0)
    p.shape("rectangle", (5, 1, 7, 6), fill=1)
    p.px(5, 1, 0), p.px(7, 1, 0)
    p.px(6, 3, 0)
    p.px(6, 4, 0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"huabiao": _huabiao, "gate": _gate, "mound": _mound}[name]()
    return _PROPS[name]


def scenery(g: Gfx, t: float):
    # 云
    for i, (y, sp, k) in enumerate(((5, 1.3, 0), (15, 0.8, 1))):
        x = 140 - ((t * sp + i * 70) % 190)
        pix.blit(g, CLOUD[k], x, y, outline=False)
    # 城墙（远景）：墙垛、砖缝网点
    wy = 46
    g.d.rectangle((66, wy, 127, FLOOR - 1), fill=0)
    g.d.line((66, wy, 127, wy), fill=1)
    for x in range(66, 128, 6):
        g.d.rectangle((x, wy - 3, x + 2, wy - 1), outline=1)
    pix.checker(g, (67, wy + 2, 128, FLOOR - 1), 0.125)
    g.d.line((66, wy, 66, FLOOR), fill=1)
    pix.blit(g, prop("gate"), 88, wy - 17)
    # 城门洞
    g.d.chord((95, wy + 3, 107, wy + 20), 180, 360, fill=0, outline=1)
    g.d.rectangle((96, wy + 9, 106, FLOOR - 1), fill=0)
    g.d.line((95, wy + 9, 95, FLOOR - 1), fill=1)
    g.d.line((107, wy + 9, 107, FLOOR - 1), fill=1)
    # 冢累累
    for x, y in ((2, FLOOR - 8), (13, FLOOR - 6)):
        pix.blit(g, prop("mound"), x, y)
    # 地面
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-4, 132, 9):
        g.px(x, FLOOR + 2), g.px(x + 4, FLOOR + 3)
    tuft(g, 44, FLOOR, t, 0)
    tuft(g, 118, FLOOR, t, 1)
    pix.blit(g, PEBBLE[0], 52, FLOOR - 3)
    pix.blit(g, prop("huabiao"), PX - 11, PY)


def draw_crane(g: Gfx, x: float, y: float, neck: str = "up", legs: int = 0, flip: bool = False):
    """站着的鹤（朝右），(x, y) = 落脚点。legs：0 两脚 / 1 单脚独立 / 2 下蹲"""
    x, y = int(round(x)), int(round(y))
    L = LEGS[legs]
    sq = 10 - L.h

    def at(ox, oy, spr):
        px = x + ox if not flip else x - ox - spr.w
        pix.blit(g, spr, px, y + oy, flip=flip)

    at(-3, -L.h, L)
    at(-10, -18 + sq, BODY)
    nk = NECK[neck]
    at(-3 + NECK_DX[neck], -15 - nk.h + sq, nk)  # 按底边对齐（字符画开头的空行会被去掉）


def draw_fly(g: Gfx, x: float, y: float, t: float, flip: bool = False, flap: float = 7.0, glide: bool = False):
    """飞的鹤，(x, y) ≈ 身体中心；朝右，flip 朝左"""
    i = 1 if glide else [0, 1, 2, 1][int(t * flap) % 4]
    x, y = int(round(x)), int(round(y))
    bx, by = x - 16, y - 4
    w = WING[i]
    wx, wy = WXY[i]
    if flip:
        pix.blit(g, FLY_BODY, 2 * x - bx - FLY_BODY.w, by, flip=True)
        pix.blit(g, w, 2 * x - (bx + wx) - w.w, by + wy, flip=True)
    else:
        pix.blit(g, FLY_BODY, bx, by)
        pix.blit(g, w, bx + wx, by + wy)
    return i


MX_HEAD = {
    "up": ["  ###   ", " ##.##  ", " #.#####", " ####   ", "  ##    ", "  ##    ", "   ##   ", "  ####  "],
    "blink": ["  ###   ", " ##.##  ", " ###### ", " ####   ", "  ##    ", "  ##    ", "   ##   ", "  ####  "],
    "call": ["     ## ", "   ### #", " ##.#   ", " ####   ", "  ##    ", "  ##    ", "   ##   ", "  ####  "],
}
MX_FLY = [["#      #", "##    ##", " ##  ## ", "  ####  ", "  ####  ", "   ##   ", "        ", "        "],
          ["        ", "        ", "#      #", "########", "  ####  ", "   ##   ", "        ", "        "],
          ["        ", "        ", "        ", "  ####  ", "########", "##    ##", "#      #", "        "]]


@register
class CraneRest(Rest):
    id = "x4.crane"
    name = "鹤归华表"
    desc = "丹顶鹤立在华表顶上梳羽长鸣；小道士路过仰望，鹤腾空绕城楼盘旋，空中写出丁令威的诗，再落回柱顶"
    T = {"enter": 3.2, "exit": 1.4}

    def setup(self):
        self.clock = Clock()
        self.poem0 = self.rng.randrange(4)

    # ------------------------------------------------------------ 鹤站着时的小动作（按 t）

    def idle_pose(self, t: float):
        """返回 (neck, legs)：一个 32 秒的小循环，叠加眨眼"""
        k = t % 32
        if 4 < k < 7.5:
            return ("look" if k < 7 else "up"), 0
        if 11 < k < 15:
            return ("preen" if int((k - 11) * 3) % 3 != 2 else "look"), 0
        if 18 < k < 26:
            return "up", 1
        if 27.5 < k < 30:
            return ("call" if (k - 27.5) % 0.8 < 0.55 else "up"), 0
        return ("blink" if t % 3.3 < 0.15 else "up"), 0

    def calling(self, t: float) -> bool:
        k = t % 32
        return 27.5 < k < 30 and (k - 27.5) % 0.8 < 0.55

    # ------------------------------------------------------------ 事件：小道士来、鹤盘旋写诗

    def flight(self, loc: float):
        """事件中鹤的位置：返回 (x, y, mode, flip)；mode = stand / fly / glide / crouch"""
        if loc < 5.0:
            return PX, PY, "stand", False
        if loc < 5.5:
            return PX, PY, "crouch", False
        cx, cy, rx, ry = CIRCLE
        if loc < 7.0:  # 腾空：从柱顶斜升到盘旋圈的左端
            q = ease_out(span(loc, 5.5, 7.0))
            return lerp(PX, cx - rx, q), lerp(PY - 14, cy, q) - math.sin(q * math.pi) * 6, "fly", False
        if loc < 16.0:  # 盘旋：从左端出发顺时针绕 1.5 圈
            a = math.pi + (loc - 7.0) / 9.0 * 3 * math.pi
            x, y = cx + math.cos(a) * rx, cy + math.sin(a) * ry
            return x, y, "fly", math.sin(a) > 0
        if loc < 18.5:  # 滑翔落回（从右端）
            q = ease_in_out(span(loc, 16.0, 18.5))
            return lerp(cx + rx, PX, q), lerp(cy, PY - 14, q), "glide", True
        return PX, PY, "stand", False

    def scene(self, g: Gfx, t: float, dt: float, show_crane: bool = True):
        """画一帧 hold（t = hold 时间）；返回点阵用的状态"""
        scenery(g, t)
        e = ev(t, EV_P, EV0, EV_D)
        cx_state = ("stand", PX, PY)
        text = None
        if e is None:
            neck, legs = self.idle_pose(t)
            if show_crane:
                draw_crane(g, PX, PY, neck, legs)
                if self.calling(t):
                    sound_arcs(g, PX + 9, PY - 28, (t * 1.5) % 1, d=1, n=2)
            return {"mode": "stand", "neck": neck}, None
        n, loc = e
        # 小道士
        if loc < 3.0:
            daoshi(g, lerp(140, DX, ease_out(span(loc, 0, 3.0))), FLOOR, "walk", loc, flip=True)
        elif loc < 5.5:
            daoshi(g, DX, FLOOR, "point" if loc > 3.6 else "idle", loc, flip=True, face="wow")
        elif loc < 16.0:
            pose = "raise" if 8.5 < loc < 12 and int(loc * 3) % 2 == 0 else "idle"
            daoshi(g, DX, FLOOR, pose, loc, flip=loc < 7.0, face="happy")
        elif loc < 20.5:
            daoshi(g, DX, FLOOR, "bow" if 18.8 < loc < 20 else "gongshou" if loc > 18.5 else "idle", loc, flip=True)
        else:
            daoshi(g, lerp(DX, 140, ease_in(span(loc, 20.5, EV_D))), FLOOR, "walk", loc)
        x, y, mode, flip = self.flight(loc)
        neck = "up"
        if mode in ("stand", "crouch"):
            neck = "down" if 4.0 < loc < 5.5 else ("blink" if loc % 3.3 < 0.15 else "up")
            if loc > 18.5:
                neck = "look" if 19 < loc < 20.2 else neck
            if mode == "crouch" or 18.5 <= loc < 18.8:  # 起跳前一蹲 / 落地一蹲
                draw_crane(g, x, y, neck, 2)
            else:
                draw_crane(g, x, y, neck, 0)
            if 3.6 < loc < 4.4:  # 小道士惊喜：头上一个“！”
                g.d.rectangle((DX + 9, 18, DX + 10, 22), fill=1)
                g.d.rectangle((DX + 9, 24, DX + 10, 25), fill=1)
        else:
            draw_fly(g, x, y, loc, flip=flip, glide=mode == "glide")
        if 7.0 < loc < 16.5:
            text = (POEM[(self.poem0 + n) % 4], loc - 7.0)
        return {"mode": mode, "neck": neck, "loc": loc}, text

    def poem(self, g: Gfx, text):
        if not text:
            return
        s, k = text
        n = min(len(s), int(k * 2.2) + 1)
        w = text_width(s)
        x0 = 126 - w
        label(g, x0, 2, s[:n])

    def mx(self, g: Gfx, st: dict, t: float):
        if st["mode"] in ("fly", "glide"):
            i = 1 if st["mode"] == "glide" else [0, 1, 2, 1][int(t * 7) % 4]
            mx_art(g, MX_FLY[i])
            return
        nk = st["neck"]
        mx_art(g, MX_HEAD["call" if nk == "call" else "blink" if nk == "blink" else "up"])
        if nk == "call":
            g.mx_set(7, 1 + int(t * 6) % 3)

    # ------------------------------------------------------------ 三段

    def enter(self, g: Gfx, t: float):
        self.clock.dt(t)
        scenery(g, t)
        if t < 2.2:  # 从右上方划弧飞来
            q = ease_out(span(t, 0, 2.2))
            x = lerp(150, PX + 2, q)
            y = lerp(4, PY - 14, q) - math.sin(q * math.pi) * 4
            draw_fly(g, x, y, t, flip=True, glide=q > 0.8)
            mx_art(g, MX_FLY[[0, 1, 2, 1][int(t * 7) % 4]])
        else:
            k = t - 2.2
            if k < 0.35:
                draw_crane(g, PX, PY, "up", 2)
            else:
                draw_crane(g, PX, PY, "look" if k < 0.7 else "up", 0)
            mx_art(g, MX_HEAD["up"])

    def hold(self, g: Gfx, t: float):
        self.clock.dt(t)
        st, text = self.scene(g, t, 0)
        self.mx(g, st, t)
        self.poem(g, text)

    def exit(self, g: Gfx, t: float):
        """展翅冲天：站着就一蹲起飞；在空中就从那里直接往上冲"""
        h = self.hold_t
        e = ev(h, EV_P, EV0, EV_D)
        x, y, mode = PX, PY - 14, "stand"
        if e is not None:
            x, y, mode, _ = self.flight(e[1])
        scenery(g, h + t)
        if e is not None and 3.0 <= e[1] < 20.5:  # 小道士还在：仰头目送
            daoshi(g, DX, FLOOR, "raise" if t > 0.4 else "idle", h + t, flip=True, face="wow")
        if mode in ("stand", "crouch"):
            if t < 0.3:
                draw_crane(g, PX, PY, "up", 2)
                mx_art(g, MX_HEAD["up"])
                return
            x, y = PX, PY - 14
        q = ease_in(span(t, 0.0 if mode not in ("stand", "crouch") else 0.3, self.T["exit"]))
        draw_fly(g, x + q * 24, y - q * 60, t, flap=11)
        mx_art(g, MX_FLY[[0, 1, 2, 1][int(t * 11) % 4]])
        g.mx_level = 1 + int(5 * q)
