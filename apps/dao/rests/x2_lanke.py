"""烂柯：任昉《述异记》王质观棋。

“信安郡石室山，晋时王质伐木至，见童子数人棋而歌，质因听之。童子以一物与质，如枣核，质含之，不觉饥。
俄顷，童子谓曰：‘何不去？’质起视，斧柯烂尽。既归，无复时人。”

入场：石枰与两个梳双髻的童子从地里升起，樵夫扛着斧子从左边走来，把斧子拄在身边。
持续：一局一轮（96 秒）。童子你一子我一子下棋（每 2 秒一手，落子有火星）；天上日月飞快轮转（山中一日，世上一年），
      樵夫的胡子越长越长，斧柄一点点朽烂、长出蘑菇。中途童子递给樵夫一颗“枣核”。
      局终：斧柄烂断、斧头落地，樵夫一惊；童子问“何不去”，题“斧柯烂尽”；樵夫拾起斧头走了，
      童子收子，又一位年轻樵夫走来，拄斧观棋——下一局。
退场：画面收拢成一个圆。
"""
from __future__ import annotations

import math
import random

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import iris

GROUND = 60
CYC = 96.0
PLAY_END = 72.0     # 落子到此为止
STEP = 3.0          # 每手棋秒数
COLS, ROWS = 9, 5
BACK_Y, FRONT_Y = 36, 52
BACK_X, FRONT_X = (46, 84), (36, 94)
WZ_X = 3            # 樵夫站的位置（精灵左边）
AXE_X = 22

WOODMAN = Sprite("""
        ...
      ..###..
    .#########.
   #############
      #......#
      #......##
      #....#..#
      #.......#
       #.....#
       .#####.
      #.......#
     #.........#
    #...........#
    #..#........#
    #..#........#
    #..#........#
    #...#.......#
    #...##......#
    #...........#
    #############
    #...........#
    #...........#
    #...........#
    #...........#
    #...........#
    #############
      #.#   #.#
      #.#   #.#
      #.#   #.#
     ##.#  ##.#
     ####  ####
""")
WALK = Sprite("""
      #.#    #.#
      #.#   #.#
     #.#    #.#
    ##.#   ##.#
    ####   ####
""")
BUNDLE = Sprite("""
   #   #   #
  ### ### ###
  #.# #.# #.#
  #.#.#.#.#.#
  #.#.#.#.#.#
  #.#.#.#.#.#
  ###.###.###
  #.#######.#
  ###########
""")
KID = Sprite("""
 .##.     .##.
#....#   #....#
#....#####....#
 .##.......##.
   #........#
   #........#
   #.....#..#
   #........#
   #......#.#
    #......#
     ######
   ##......##
  #..........#
 #............#
 #............#
 #............#
 #............#
""")
AXE_HEAD = Sprite("""
 ####
 #..##
 #...#
 #..##
 ####
""")

WOODMAN_L, BUNDLE_L, WALK_L, KID_R = WOODMAN.flip(), BUNDLE.flip(), WALK.flip(), KID.flip()
AXE_DOWN = AXE_HEAD.rot90(-1)


def pad(g: Gfx, cx: float, cy: float, w: float, h: float):
    """一团松针：压扁的椭圆，抖动灰度 + 上沿轮廓"""
    pts = [(cx + math.cos(a / 12 * 2 * math.pi) * w, cy + math.sin(a / 12 * 2 * math.pi) * h * (0.6 if a < 6 else 1))
           for a in range(12)]
    g.d.polygon(pts, fill=0)
    g.shade_poly(pts, 0.45, outline=None)
    g.d.line(pts[6:] + pts[:1], fill=1)


def tree(g: Gfx, t: float, seed: int):
    """右边一棵老松：虬干 + 几团平展的松针"""
    d = g.d
    d.line([(119, GROUND), (118, 46), (121, 34), (117, 22), (119, 10), (116, 0)], fill=1, width=3)
    d.line([(118, 33), (108, 27)], fill=1, width=2)
    d.line([(118, 19), (106, 12)], fill=1, width=2)
    sway = (noise(t * 0.3, seed) - 0.5) * 1.6
    pad(g, 106 + sway, 26, 10, 4)
    pad(g, 104 + sway * 1.3, 11, 12, 4)
    pad(g, 124, 4, 8, 3)
    for i in range(3):  # 树皮鳞纹
        g.px(118, 52 - i * 12, 0)
        g.px(119, 44 - i * 12, 0)


def board_xy(c: float, r: float):
    """棋盘交点 (c, r) → 屏幕坐标（透视：后窄前宽）"""
    k = r / (ROWS - 1)
    y = lerp(BACK_Y + 2, FRONT_Y - 2, k)
    x0 = lerp(BACK_X[0] + 3, FRONT_X[0] + 3, k)
    x1 = lerp(BACK_X[1] - 3, FRONT_X[1] - 3, k)
    return lerp(x0, x1, c / (COLS - 1)), y


def board(g: Gfx, dy: float = 0.0):
    d = g.d
    top = [(BACK_X[0], BACK_Y + dy), (BACK_X[1], BACK_Y + dy), (FRONT_X[1], FRONT_Y + dy), (FRONT_X[0], FRONT_Y + dy)]
    d.polygon(top, fill=0, outline=1)
    d.rectangle((FRONT_X[0], FRONT_Y + dy, FRONT_X[1], FRONT_Y + 4 + dy), fill=0, outline=1)  # 枰的厚度
    for x in range(FRONT_X[0] + 3, FRONT_X[1] - 1, 4):
        g.px(x, FRONT_Y + 2 + dy)
    d.polygon([(FRONT_X[0] + 6, FRONT_Y + 5 + dy), (FRONT_X[1] - 6, FRONT_Y + 5 + dy), (FRONT_X[1] - 2, GROUND),
               (FRONT_X[0] + 2, GROUND)], fill=0, outline=1)  # 石墩
    g.shade((FRONT_X[0] + 4, FRONT_Y + 6 + dy, FRONT_X[1] - 3, GROUND), 0.15)
    for r in range(ROWS):  # 棋盘线
        x0, y = board_xy(0, r)
        x1, _ = board_xy(COLS - 1, r)
        d.line((x0, y + dy, x1, y + dy), fill=1)
    for c in range(COLS):
        xa, ya = board_xy(c, 0)
        xb, yb = board_xy(c, ROWS - 1)
        d.line((xa, ya + dy, xb, yb + dy), fill=1)


def stone(g: Gfx, x: float, y: float, black: bool):
    x, y = int(round(x)), int(round(y))
    if black:
        g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
        g.d.line((x - 2, y, x + 2, y), fill=1)
    else:
        g.d.rectangle((x - 2, y - 1, x + 2, y + 1), fill=0)
        g.d.rectangle((x - 1, y - 2, x + 1, y + 2), fill=0)
        g.d.line((x - 1, y - 2, x + 1, y - 2), fill=1)
        g.d.line((x - 1, y + 2, x + 1, y + 2), fill=1)
        g.d.line((x - 2, y - 1, x - 2, y + 1), fill=1)
        g.d.line((x + 2, y - 1, x + 2, y + 1), fill=1)


@register
class Lanke(Rest):
    id = "x2.lanke"
    name = "烂柯"
    desc = "王质观仙童下棋，日月飞转、胡子渐长，斧柄烂尽落地，童子问何不去，换一位樵夫再观一局"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0
        self._orders: dict[int, list] = {}

    def order(self, game: int) -> list:
        if game not in self._orders:
            pts = [(c, r) for c in range(COLS) for r in range(ROWS)]
            random.Random(self.seed * 1000 + game).shuffle(pts)
            if len(self._orders) > 4:
                self._orders.clear()
            self._orders[game] = pts
        return self._orders[game]

    # ------------------------------------------------------------ 人物

    def woodman(self, g: Gfx, x: float, beard: float = 0.0, walk: float = -1.0, jump: float = 0.0,
                face_left: bool = False, eat: bool = False):
        """樵夫：斗笠、背柴；beard 0..1 胡子长度；walk ≥ 0 时迈步"""
        y = GROUND - WOODMAN.h + 1 - jump
        if walk >= 0:
            y -= abs(math.sin(walk * math.pi * 2)) * 1.5
        w = WOODMAN.w
        spr = WOODMAN_L if face_left else WOODMAN
        g.blit(BUNDLE_L if face_left else BUNDLE, x + (w - 7 if face_left else -5), y + 9)
        g.blit(spr, x, y)
        if walk >= 0 and int(walk * 2) % 2:
            g.d.rectangle((x + 3, y + 26, x + w - 3, y + 30), fill=0)
            g.blit(WALK_L if face_left else WALK, x + (1 if not face_left else w - WALK.w - 1), y + 26)
        if beard > 0:  # 胡子：从下巴垂下，越来越长（白须，盖在衣服上）
            bx = x + (w - 13 if face_left else 12)
            ln = beard * 17
            for i in range(int(ln) + 1):
                hw = 1.6 * (1 - 0.6 * i / max(ln, 1))
                cx = bx + math.sin(i * 0.5 + 1) * 0.7
                g.d.line((cx - hw - 1, y + 8 + i, cx + hw + 1, y + 8 + i), fill=0)
                g.d.line((cx - hw, y + 8 + i, cx + hw, y + 8 + i), fill=1)
        if eat:
            g.d.line((x + 12, y + 7, x + 13, y + 7), fill=0)

    KID_X = (43, 78)
    KID_Y = BACK_Y - 13

    def kid(self, g: Gfx, left: bool, dy: float = 0.0):
        """梳双髻的童子，坐在石枰后面（下半身被石枰挡住）"""
        x = self.KID_X[0 if left else 1]
        g.blit(KID if left else KID_R, x, self.KID_Y + dy)

    def arm(self, g: Gfx, left: bool, reach: float, target):
        """童子伸手落子：reach 0..1"""
        x = self.KID_X[0 if left else 1]
        sx, sy = (x + 12, self.KID_Y + 12) if left else (x + 2, self.KID_Y + 12)
        if reach <= 0 or not target:
            return
        tx, ty = target
        ex, ey = lerp(sx, tx, reach), lerp(sy, ty - 1, reach) - math.sin(reach * math.pi) * 3
        g.d.line((sx, sy, ex, ey), fill=1, width=2)
        g.d.rectangle((ex - 1, ey - 1, ex + 1, ey), fill=1)

    def axe(self, g: Gfx, rot: float, fallen: float = -1.0, gone: bool = False):
        """斧：rot 0..1 斧柄朽烂程度；fallen ≥ 0 时斧头掉落的进度"""
        if gone:
            return
        x = AXE_X
        top = 41
        if fallen < 0:
            for i in range(GROUND - top):  # 斧柄：越烂缺的点越多，还长出蘑菇
                y = GROUND - 1 - i
                if rand(i, self.seed) < rot * 0.55:
                    continue
                g.px(x, y)
                if rand(i + 50, self.seed) > rot * 1.2:
                    g.px(x + 1, y)
            if rot > 0.35:
                mh = (rot - 0.35) * 6
                g.d.pieslice((x - 5, GROUND - 3 - mh, x - 1, GROUND + 1 - mh), 180, 360, fill=1)
                g.d.line((x - 3, GROUND - 1 - mh, x - 3, GROUND), fill=1)
            if rot > 0.6:
                g.d.pieslice((x + 2, GROUND - 11, x + 6, GROUND - 7), 180, 360, fill=1)
            g.blit(AXE_HEAD, x - 1, top - 2)
        else:  # 斧柄烂成灰，斧头落地
            p = ease_out_bounce(fallen)
            hy = lerp(top - 2, GROUND - 4, p)
            g.blit(AXE_DOWN if fallen > 0.4 else AXE_HEAD, x - 1, hy)
            for j in range(10):  # 碎屑
                k = clamp(fallen * 1.5 - rand(j, 4) * 0.3)
                g.px(x + (rand(j, 5) - 0.5) * 8 * k, lerp(top + j * 2, GROUND, ease_in(k)))

    def sky(self, g: Gfx, t: float):
        """日月飞快轮转：一日 10 秒（山中方一日，世上已一年）"""
        ph = (t / 10.0) % 1.0
        k = (ph % 0.5) / 0.5
        x = lerp(88, 6, k)
        y = 19 - math.sin(k * math.pi) * 15
        g.d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=1)
        if ph < 0.5:  # 日
            for i in range(8):
                a = i * math.pi / 4 + t
                g.px(x + math.cos(a) * 5, y + math.sin(a) * 5)
        else:  # 月 + 几颗星
            g.d.ellipse((x - 1, y - 4, x + 5, y + 2), fill=0)
            for i in range(6):
                sx, sy = 8 + rand(i, 3) * 84, 2 + rand(i, 4) * 14
                if noise(t * 2 + i, 7) > 0.4:
                    g.px(sx, sy)

    def leaves(self, g: Gfx, t: float):
        for j in range(2):  # 松针飘落
            ph = t / 7 + j * 0.5
            k = ph % 1
            x = 104 + rand(int(ph) * 2 + j, self.seed) * 18 - k * 30
            y = 14 + k * 46
            if y < GROUND - 1:
                g.d.line((x, y, x + 1 + math.sin(k * 20), y + 1), fill=1)

    def ground(self, g: Gfx):
        g.d.line((0, GROUND + 1, 127, GROUND + 1), fill=1)
        for i in range(0, 128, 9):  # 草
            gx = i + rand(i, 3) * 5
            g.d.line((gx, GROUND, gx - 1, GROUND - 2), fill=1)

    # ------------------------------------------------------------ 一局

    def frame(self, g: Gfx, t: float):
        game = int(t // CYC)
        s = t % CYC
        order = self.order(game)
        nmax = int(PLAY_END / STEP)
        placed = min(nmax, int((s - 2.0) / STEP) + 1) if s >= 2.0 else 0
        shown = int(placed * (1 - span(s, 84, 90)))
        talk = 74.5 < s < 84.5
        if not talk:
            self.sky(g, t)
        tree(g, t, self.seed)
        self.leaves(g, t)
        self.ground(g)
        self.kid(g, True)
        self.kid(g, False)
        board(g)
        for i in range(shown):
            c, r = order[i]
            x, y = board_xy(c, r)
            stone(g, x, y, i % 2 == 0)
        # 落子：先伸手，落下时一点火星，再收手
        if 2.0 - 0.7 <= s < PLAY_END + 0.4:
            k = (s - 2.0) % STEP
            nxt = placed
            if nxt < nmax and k > STEP - 0.7:
                reach = math.sin(span(k, STEP - 0.7, STEP) * math.pi * 0.5)
                self.arm(g, nxt % 2 == 0, reach, board_xy(*order[nxt]))
            elif placed > 0 and k < 0.4:
                i = placed - 1
                tgt = board_xy(*order[i])
                self.arm(g, i % 2 == 0, 1 - span(k, 0.0, 0.4), tgt)
                if k < 0.2:
                    for a in range(4):
                        ang = a * math.pi / 2 + 0.8
                        g.px(tgt[0] + math.cos(ang) * 4, tgt[1] + math.sin(ang) * 3)
        # 枣核：左边童子抛给樵夫一颗，樵夫含着
        jj = span(s, 30.0, 31.2)
        if 0 < jj < 1:
            sx, sy = self.KID_X[0] + 2, self.KID_Y + 10
            ex, ey = WZ_X + 13, GROUND - WOODMAN.h + 8
            x, y = lerp(sx, ex, jj), lerp(sy, ey, jj) - math.sin(jj * math.pi) * 14
            g.d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=1)
        # 樵夫 + 斧
        rot = clamp(s / PLAY_END)
        if s < 72:
            self.woodman(g, WZ_X, rot, eat=31.2 < s < 33.5 and int(s * 5) % 2 == 0)
            self.axe(g, rot)
        elif s < 84.5:
            jump = 4 * math.sin(span(s, 72.4, 73.0) * math.pi)
            self.woodman(g, WZ_X, 1.0, jump=jump)
            self.axe(g, 1.0, fallen=span(s, 72.0, 73.2))
            if 72.4 < s < 75:  # 一惊
                g.d.line((WZ_X + 18, 22, WZ_X + 18, 26), fill=1)
                g.px(WZ_X + 18, 28)
        elif s < 89:  # 拾起斧头，转身回家
            k = span(s, 85.0, 89)
            self.woodman(g, WZ_X - ease_in(k) * 30, 1.0, walk=s * 1.5 if k > 0 else -1, face_left=k > 0)
            self.axe(g, 1.0, fallen=1.0, gone=k > 0)
        else:  # 下一位樵夫走来，拄斧
            k = ease_out(span(s, 89, 93))
            self.woodman(g, lerp(-20, WZ_X, k), 0.0, walk=s * 1.5 if k < 1 else -1)
            if s > 93:
                self.axe(g, 0.0)
            else:
                g.blit(AXE_HEAD, lerp(-20, WZ_X, k) + 14, GROUND - 20)
        # 字
        if 74.5 < s < 79.5:  # 童子：何不去？
            bx0, by0, bx1, by1 = 18, 2, 60, 18
            g.d.rounded_rectangle((bx0, by0, bx1, by1), 4, fill=0, outline=1)
            g.d.polygon([(46, by1), (52, by1), (50, self.KID_Y + 2)], fill=0, outline=1)
            g.d.line((47, by1, 51, by1), fill=0)
            typewriter(g, bx0 + 3, by0 + 3, "何不去", s - 74.5, cps=4)
        elif 79.5 < s < 84.5:
            typewriter(g, 50, 3, "斧柯烂尽", s - 79.5, cps=4, align="center")
        self.mx(g, s, order, shown)

    def mx(self, g: Gfx, s: float, order, shown):
        if 72 <= s < 84.5:  # 斧
            g.mx_rows([0x00, 0x1C, 0x3E, 0x7C, 0x18, 0x10, 0x10, 0x10] if s < 73 else
                      [0, 0, 0, 0, 0, 0, 0xE0, 0xFF])
            return
        for i in range(shown):  # 小棋盘（只显示前 8 列）
            c, r = order[i]
            if c < 8:
                g.mx_set(c, r + 2, True if i % 2 == 0 else blink(s + i * 0.3, 2.0, 0.85))
        if shown and blink(s, 0.5):
            c, r = order[shown - 1]
            if c < 8:
                g.mx_set(c, r + 2, False)
        g.mx[0, :] = [blink(s / 10 + x / 8, 1.0, 0.5) for x in range(8)]  # 顶行：日月流转

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        if t > 1.8:
            self.sky(g, 0.0) if t > 2.4 else None
        if t > 1.2:
            tree(g, t, self.seed)
        g.d.line((0, GROUND + 1, 127 * ease_out(span(t, 0, 0.6)), GROUND + 1), fill=1)
        if t > 0.6:
            self.ground(g)
        for left, t0 in ((True, 1.0), (False, 1.2)):
            k = ease_out_back(span(t, t0, t0 + 0.6))
            if k > 0:
                self.kid(g, left, dy=(1 - k) * 16)
        rise = ease_out_back(span(t, 0.2, 1.1))
        if t > 0.2:
            board(g, (1 - rise) * 30)
        if t > 1.4:
            k = ease_out(span(t, 1.4, 2.6))
            self.woodman(g, lerp(-20, WZ_X, k), 0.0, walk=t * 1.5 if k < 1 else -1)
            if t > 2.6:
                self.axe(g, 0.0)
            else:
                g.blit(AXE_HEAD, lerp(-20, WZ_X, k) + 14, GROUND - 20)
        g.d.rectangle((0, GROUND + 2, 127, 63), fill=0)
        g.mx[0, :] = [x <= t * 3 for x in range(8)]

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.ht + t * 0.3)
        iris(g, span(t, 0.0, self.T["exit"]), 60, 42)
        if t > 0.7:
            g.mx[:] = False
