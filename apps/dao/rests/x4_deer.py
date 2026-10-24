"""白鹿衔芝（歇）：老松下一头 Q 版白鹿，小道士在一旁，灵芝破土，小道士采来喂鹿，鹿衔芝而立。

依据：葛洪《抱朴子·内篇·对俗》“虎及鹿、兔，皆寿千岁，寿满五百岁者，其毛色白。”
      灵芝即《抱朴子·仙药》所列之“芝”，仙药上品；白鹿是寿星、仙人的坐骑，“鹿衔灵芝”是传统的长寿图样。
画面：左边一棵老松（弯干、树皮网点、三团针叶），松下山石；白鹿侧身朝右（枝角、大眼、短尾、细腿），
      右边小道士朝左站着；远处两座小山。
入场：白鹿从左边轻步走进松下站定，抬头；右上“鹿寿千岁”。
持续：白鹿呼吸、眨眼、耳朵一抖、短尾一翘；小道士呼吸眨眼，不时拱手。
      每 23 秒：白鹿低头啃一口草（脖子放低、嚼），再抬头。
      每 31 秒：松枝上掉下一颗松果，弹两下滚到鹿脚边，鹿竖耳低头闻一闻。
      每 45 秒（从 14 秒起）：两者之间的地上冒出一株灵芝（菌柄长出、菌盖一圈圈张开、闪光）→
      小道士弯腰采起、双手捧着递过去 → 白鹿上前两步低头衔住 → 退回原地衔芝而立（右上“白鹿衔芝”）→
      灵芝化作光点沿颈飘入鹿身，鹿身一圈微光。
收场：白鹿转身小跑，往左隐进松后。
点阵：平时是鹿角（眨眼时两点）；灵芝出现后换成灵芝（自下而上长出），化光时亮度一冲并荡开一圈。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Clock, ev, label, mx_art, sparkle

FLOOR = 58
DX = 32             # 鹿身左上角 x（站定）
DY = FLOOR - 17     # 鹿身左上角 y
DAO_X = 106         # 小道士
ZX = 84             # 灵芝长出来的位置
GRAZE_S, GRAZE_P, GRAZE_D = 9.0, 23.0, 5.0
CONE_S, CONE_P, CONE_D = 20.0, 31.0, 5.0
ZHI_S, ZHI_P, ZHI_D = 14.0, 45.0, 26.0

# ---------------------------------------------------------------- 鹿（朝右）

HEAD = Sprite("""
 #   #      #   #
 #   #     #   #
  #  #  # #   #
  ## # #  #  # #
   ###  # #  ##
     #   ## ##
     ##   ###
      ######
  ##  ########
 #.##.#########
  ##############
   ######..######
    #####..#######
    #####.########.
     ##############
      ######.###.
""")

HEAD_BLINK = Sprite("""
 #   #      #   #
 #   #     #   #
  #  #  # #   #
  ## # #  #  # #
   ###  # #  ##
     #   ## ##
     ##   ###
      ######
  ##  ########
 #.##.#########
  ##############
   ##############
    ######.#######
    ######..######.
     ##############
      ######.###.
""")

HEAD_EAR = Sprite("""
 #   #      #   #
 #   #     #   #
  #  #  # #   #
  ## # #  #  # #
#  ###  # #  ##
.#   #   ## ##
 ##  ##   ###
  ##  ######
   ## ########
    ##.########
  ##############
   ######..######
    #####..#######
    #####.########.
     ##############
      ######.###.
""")

NECK = Sprite("""
 #####
######
######
#######
#######
""")

BODY = Sprite("""
       ###########
    ##################
  ######################
 ########################
##########################
##########################
##########################
 ########################
  #.#.#.#.#.#.#.#.#.#.##
    .#.#.#.#.#.#.#.#.#
""")

LEG = pix.frames("""
##
##
##
##
 ##
 ##
 ##
 ##
 #.
---
##
##
 ##
 ##
  ##
  ##
  #.
""")

TAIL = pix.frames("""
 ##
###
 ##
---
##
###
 #
""")

ZHI = pix.frames("""
 #
 #
---
  ##
 ####
  #
  #
---
   ###
 ##...##
#########
    #
    #
---
   #####
 ##.....##
#..#####..#
#.#.....#.#
 #########
     ##
     ##
    ####
""")

ZHI_SMALL = Sprite("""
 ###
#...#
#####
  #
""")

CONE = Sprite("""
 ##
#.##
##.#
 ##
""")


def _pine() -> Sprite:
    """老松 46×52：弯干（树皮网点、节疤）+ 三团扁平的针叶（短横阴线）"""
    p = Part(46, 52)
    trunk = [(6, 51), (8, 40), (6, 30), (9, 20), (13, 12), (17, 9), (19, 11), (14, 20), (12, 30), (14, 40), (13, 51)]
    p.shape("polygon", trunk, fill=1)
    p.shape("polygon", [(13, 22), (24, 17), (32, 17), (32, 19), (24, 20), (15, 25)], fill=1)  # 横枝
    p.dither([(10, 22), (14, 22), (14, 51), (10, 51)], 0.5, 0)
    for y in (27, 35, 44):
        p.d.line((8, y, 10, y - 1), fill=0)
    p.d.ellipse((8, 37, 10, 39), fill=0)            # 节疤
    p.px(9, 38, 1)
    p.shape("polygon", [(4, 51), (6, 47), (14, 47), (17, 51)], fill=1)  # 根
    for box in ((0, 3, 26, 11), (16, 0, 40, 8), (24, 12, 45, 19)):
        x0, y0, x1, y1 = box
        p.shape("ellipse", box, fill=1)
        for yy in range(y0 + 2, y1 - 1, 2):          # 针叶纹
            for xx in range(x0 + 3 + (yy % 4), x1 - 3, 4):
                p.d.line((xx, yy, xx + 1, yy), fill=0)
        p.d.line((x0 + 3, y1 - 1, x1 - 3, y1 - 1), fill=0)
    return p.sprite()


def _rock() -> Sprite:
    p = Part(20, 9)
    p.shape("polygon", [(0, 8), (2, 3), (7, 0), (13, 1), (18, 4), (19, 8)], fill=1)
    p.d.line((7, 1, 9, 5), fill=0)
    p.d.line((9, 5, 8, 8), fill=0)
    p.dither([(12, 4), (19, 7), (19, 8), (11, 8)], 0.5, 0)
    return p.sprite()


def _hills() -> Sprite:
    """远处两座小山（只有山脊线和背光坡的竖点）"""
    p = Part(44, 12)
    p.d.line((0, 11, 10, 4), fill=1)
    p.d.line((10, 4, 16, 7), fill=1)
    p.d.line((16, 7, 26, 0), fill=1)
    p.d.line((26, 0, 40, 11), fill=1)
    for x in range(28, 39, 3):
        y0 = (x - 26) * 11 // 14 + 2
        p.d.line((x, y0, x, min(y0 + 2, 11)), fill=1)
    for x in range(12, 16, 2):
        p.px(x, 7)
    on = __import__("numpy").array(p.on, bool)
    return Sprite(on=on, mask=on.copy())


_S: dict = {}


def S(name):
    if not _S:
        _S.update(pine=_pine(), rock=_rock(), hills=_hills())
    return _S[name]


# ---------------------------------------------------------------- 画鹿

def deer(g: Gfx, x: float, t: float, head="up", walk: float | None = None, tail_up=False, ear=False,
         blink=False, low: float = 0.0, chew=False, zhi=False, flip=False, breath=True):
    """x：鹿身左上角；low ∈ [0,1] 低头程度；walk：步态相位（None 站定）；返回嘴的位置"""
    x = int(round(x))
    b = 1 if breath and walk is None and (t * 0.6) % 1 < 0.5 else 0
    y = DY

    def X(ox, w=0):  # 朝左时镜像（以鹿身 26 宽为轴）
        return x + ox if not flip else x + 26 - ox - w

    def leg(ox, ph, top):
        if walk is None:
            pix.blit(g, LEG[0], X(ox, 2), top, flip=flip)
            return
        k = (walk + ph) % 1
        fr = 1 if k < 0.4 else 0
        dx = (1 if k < 0.4 else int(round(lerp(1, -1, (k - 0.4) / 0.6))))
        pix.blit(g, LEG[fr], X(ox + dx, 2), top, flip=flip)

    bob = 0 if walk is None else (1 if (walk * 2) % 1 < 0.4 else 0)
    leg(7, 0.5, y + 8 - bob)
    leg(23, 0.0, y + 8 - bob)
    pix.blit(g, TAIL[1 if tail_up else 0], X(-2, 3), y + 1 - b - bob, flip=flip)
    # 脖子 + 头：low=0 竖直抬头，low=1 前伸低头到地面
    hx = lerp(14, 21, low)
    hy = lerp(-18, -1, ease_in_out(low))
    nx0, ny0 = X(18, 0), y + 3 - bob
    hxs = X(int(round(hx)), HEAD.w)
    hys = y + int(round(hy)) - b - bob
    neck_top = (X(int(round(hx)) + 5, 0), hys + 15)
    if low > 0.05:
        g.d.polygon([(nx0 - 3, ny0), (nx0 + 3, ny0), (neck_top[0] + 3, neck_top[1]), (neck_top[0] - 3, neck_top[1])],
                    fill=1)
    pix.blit(g, BODY, X(0, BODY.w), y - b - bob, flip=flip)
    if low <= 0.05:
        pix.blit(g, NECK, X(18, NECK.w), y - 4 - b - bob, flip=flip)
    leg(4, 0.0, y + 9 - bob)
    leg(20, 0.5, y + 9 - bob)
    spr = HEAD_EAR if ear else (HEAD_BLINK if blink or chew else HEAD)
    hys += 1 if chew and int(t * 6) % 2 else 0
    pix.blit(g, spr, hxs, hys, flip=flip)
    mouth = (hxs + (15 if not flip else 1), hys + 15)
    if zhi:
        pix.blit(g, ZHI_SMALL, mouth[0] - 1 if not flip else mouth[0] - 4, mouth[1] - 3, flip=flip)
    return mouth


def scenery(g: Gfx, t: float):
    pix.blit(g, S("hills"), 66, FLOOR - 15, outline=False)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(3, 128, 9):
        g.px(x, FLOOR + 2), g.px(x + 4, FLOOR + 4)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    pix.blit(g, S("pine"), -4, FLOOR - 51)
    pix.blit(g, S("rock"), 12, FLOOR - 8)
    for x, k in ((70, 0), (96, 1), (122, 2)):
        spr = pix.anim(GRASS_FR, t * 0.7 + k * 0.4, 1.2)
        pix.blit(g, spr, x, FLOOR - spr.h)


GRASS_FR = pix.frames("""
 # #
# ##
 ##
---
  # #
 # ##
  ##
""")


def mx_antler(g: Gfx, blink: bool):
    rows = ["#.#..#.#", "#.#..#.#", ".##..##.", "..#..#..", "...##...", "..####..",
            ".#.##.#." if not blink else ".######.", "..####.."]
    mx_art(g, rows)


def mx_zhi(g: Gfx, k: float, t: float):
    rows = ["..####..", ".#....#.", "#.####.#", "#.#..#.#", ".######.", "...##...", "...##...", "..####.."]
    n = int(k * 8 + 0.999)
    for y in range(8):
        if y >= 8 - n:
            mx_art(g, [rows[y]], 0, y)


@register
class Deer(Rest):
    id = "x4.deer"
    name = "白鹿衔芝"
    desc = "老松下的 Q 版白鹿与小道士：鹿眨眼抖耳翘尾、低头啃草；灵芝破土，小道士采来喂鹿，鹿衔芝而立，化光入身"
    T = {"enter": 3.0, "exit": 1.4}

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.glow = pix.Sparks(self.seed + 1)

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, dt: float, deer_x=DX, walk=None, text=None, flip=False, events=True,
              pine_front=False):
        scenery(g, t)
        blink = (t % 3.6) < 0.14
        ear = (t % 6.1) < 0.35
        tail_up = (t % 4.7) < 0.4
        low, chew, zhi_mouth = 0.0, False, False
        dpose, dface, held = "idle", "normal", None
        mxmode, mxk = "antler", 0.0
        zstage = None    # 地上灵芝的生长阶段
        cone_xy = None
        dx = 0.0
        glow_k = None
        dao_dx, dao_walk, dao_flip = 0.0, False, True
        if events:
            zh = ev(t, ZHI_P, ZHI_S, ZHI_D)
            gz = ev(t, GRAZE_P, GRAZE_S, GRAZE_D) if not zh else None
            cn = ev(t, CONE_P, CONE_S, CONE_D) if not zh else None
            if gz:
                L = gz[1]
                low = ease_in_out(span(L, 0, 0.8)) * (1 - ease_in_out(span(L, 4.0, 4.8)))
                chew = 1.0 < L < 4.0
            if cn:
                L = cn[1]
                # 松果：从松枝落下，弹两下滚到鹿鼻子前
                if L < 0.7:
                    cx, cy = 40, lerp(22, FLOOR - 4, ease_in(L / 0.7))
                elif L < 1.6:
                    q = (L - 0.7) / 0.9
                    cx = lerp(40, 66, q)
                    cy = FLOOR - 4 - abs(math.sin(q * math.pi * 2)) * 7 * (1 - q)
                else:
                    cx, cy = 66 + min(L - 1.6, 0.5) * 4, FLOOR - 4
                cone_xy = (cx, cy)
                if 0.7 < L < 3.5:
                    ear = True
                if 2.0 < L < 3.6:
                    low = ease_in_out(span(L, 2.0, 2.5)) * (1 - ease_in_out(span(L, 3.1, 3.6))) * 0.7
            if zh:
                L = zh[1]
                # 小道士：3.0–3.6 走过去，8.6–9.4 走回来
                dao_dx = -10 * ease_in_out(span(L, 3.0, 3.6)) * (1 - ease_in_out(span(L, 8.6, 9.4)))
                dao_walk = 3.0 < L < 3.6 or 8.6 < L < 9.4
                dao_flip = not (8.6 < L < 9.4)
                if L < 3.0:                                   # 破土长大
                    zstage = min(3, int(L / 0.75))
                    mxmode, mxk = "zhi", span(L, 0, 3.0)
                    if int(L * 3) != int((L - dt) * 3):
                        self.sparks.burst(ZX, FLOOR - 6, 2, 12, up=6, life=0.6, gravity=-6)
                elif L < 4.6:                                 # 小道士走过去弯腰采
                    zstage = 3 if L < 4.0 else None
                    dpose = "bow" if L > 3.4 else "idle"
                    held = L >= 4.0
                    mxmode, mxk = "zhi", 1.0
                elif L < 8.6:                                 # 捧着递过去；鹿上前衔住
                    dpose, held, dface = "offer", True, "happy"
                    mxmode, mxk = "zhi", 1.0
                    dx = ease_in_out(span(L, 5.2, 6.6)) * 12
                    if 5.2 < L < 6.6:
                        walk = (L - 5.2) * 1.6
                    if L > 6.6:
                        low = ease_in_out(span(L, 6.6, 7.2)) * 0.45 * (1 - ease_in_out(span(L, 7.6, 8.2)))
                    if L > 7.4:
                        held, zhi_mouth = False, True
                elif L < 22.0:                                # 鹿退回原地，衔芝而立
                    zhi_mouth = True
                    dx = 12 * (1 - ease_in_out(span(L, 8.6, 10.0)))
                    if L < 10.0:
                        walk = -(L - 8.6) * 1.6
                    dpose = "gongshou" if L < 17 else "idle"
                    dface = "happy" if L < 12 else "normal"
                    mxmode, mxk = "zhi", 1.0
                    if L > 10.5:
                        text = "白鹿衔芝"
                    if L > 19.0:                              # 化作光点飘入鹿身
                        zhi_mouth = L < 19.6
                        glow_k = span(L, 19.0, 22.0)
                        mxmode = "glow"
                else:
                    glow_k = 1.0 if L < 23.0 else None
                    mxmode = "glow" if L < 23.0 else "antler"
        mouth = deer(g, deer_x + dx, t, walk=walk, tail_up=tail_up, ear=ear, blink=blink and not chew, low=low,
                     chew=chew, zhi=zhi_mouth, flip=flip)
        if cone_xy:
            pix.blit(g, CONE, cone_xy[0], cone_xy[1])
        if pine_front:  # 进出场：鹿从松树后面走出来 / 隐进松后
            pix.blit(g, S("pine"), -4, FLOOR - 51)
            pix.blit(g, S("rock"), 12, FLOOR - 8)
        if zstage is not None:
            spr = ZHI[zstage]
            pix.blit(g, spr, ZX - spr.w // 2, FLOOR - spr.h)
        h = daoshi(g, DAO_X + dao_dx, FLOOR, "walk" if dao_walk else dpose, t, flip=dao_flip, face=dface)
        if held:
            hx, hy = h["hand"]
            pix.blit(g, ZHI_SMALL, hx - 4, hy - 4)
        if glow_k is not None:  # 光点从嘴边沿脖子飘进身体，最后一圈微光
            mx_, my_ = mouth
            if glow_k < 0.7:
                for i in range(5):
                    q = (glow_k / 0.7 + i * 0.13) % 1
                    px = lerp(mx_, deer_x + 13, q) + math.sin(q * 9 + i) * 2
                    py = lerp(my_, DY + 4, q)
                    g.px(px, py)
                    if i == 0:
                        sparkle(g, px, py, 1)
            else:
                r = (glow_k - 0.7) / 0.3
                cx, cy = deer_x + 13 + dx, DY + 1
                for a in range(0, 360, 30):
                    rr = 14 + r * 6
                    g.px(cx + math.cos(math.radians(a + t * 40)) * rr, cy + math.sin(math.radians(a + t * 40)) * rr * 0.6)
        if zstage == 3 or held or zhi_mouth:  # 灵芝的小闪光
            if int(t * 3) % 2 == 0:
                if held:
                    sx, sy = h["hand"][0] - 3, h["hand"][1] - 7
                elif zhi_mouth:
                    sx, sy = mouth[0] + 4, mouth[1] - 6
                else:
                    sx, sy = ZX + 5, FLOOR - 11
                sparkle(g, sx, sy, 1)
        self.sparks.step(dt)
        self.sparks.draw(g, trail=False)
        # 点阵
        if mxmode == "zhi":
            mx_zhi(g, mxk, t)
        elif mxmode == "glow":
            mx_zhi(g, 1.0, t)
            r = (t * 3) % 4
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.6:
                        g.mx[yy, xx] = True
            g.mx_level = 6
        else:
            mx_antler(g, blink)
        if text:
            label(g, 125, 3, text, align="right")

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        q = ease_out(span(t, 0, 2.4))
        x = lerp(-40, DX, q)
        walk = t * 1.8 if t < 2.4 else None
        self.scene(g, t, dt, deer_x=x, walk=walk, text="鹿寿千岁" if t > 1.0 else None, events=False,
                   pine_front=True)

    def hold(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        self.scene(g, t, dt, text="鹿寿千岁" if t < 6.0 else None)

    def exit(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        q = ease_in(span(t, 0.2, self.T["exit"]))
        x = DX - q * 80
        self.scene(g, self.hold_t + t, dt, deer_x=x, walk=t * 3.0, flip=True, events=False,
                   pine_front=True)
