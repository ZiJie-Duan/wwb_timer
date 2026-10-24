"""刘海戏金蟾（歇）：小道士扮刘海，竹竿挑着一串方孔钱逗三足金蟾。

依据：刘海蟾（刘操，号海蟾子），全真道奉为北五祖之一；民间传说他以钱串为饵钓出三足金蟾，
      “刘海戏金蟾，步步钓金钱”为明清吉祥图样。
画面：左边小道士双手握竹竿（竹节），竿梢垂下一串方孔铜钱，像钟摆一样晃；右边一块平石上坐着正脸的 Q 版
      三足金蟾（两只鼓眼、大笑嘴、腮红、额头铜钱纹、身上疣点；左右两只前脚，第三只后脚在肚子底下露出脚趾），
      地上散着两枚铜钱，天上一朵云。
入场：小道士扛着竿从左边走进来站定；金蟾从右边三跳蹦到石上坐好；左上“刘海戏金蟾”。
持续：钱串摆，金蟾眼珠跟着钱转、眨眼，喉囊一鼓一鼓；一只小飞虫在它面前绕圈，每 11 秒金蟾吐舌头一卷
      （三回里有一回卷到，咕嘟咽下、眯眼笑，过一会儿又飞来一只）。
      每 30 秒（从 16 秒起）：小道士把竿一挑，金蟾蹲低蓄力、一跃咬住最下面的铜钱，挂在钱串上被悠两下
      （钱串闪光），松口落回石上压扁、扬起尘土、再弹两下；左上换成“步步钓金钱”。
收场：金蟾往右两跳跳出画面，小道士转身扛竿追过去。
点阵：金蟾的正脸（眨眼、喉囊鼓起时下巴变大）；钓钱时是一枚方孔钱，闪光时加亮。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import CLOUD, Clock, ev, label, mx_art, sparkle

FLOOR = 60
DAO_X = 22
TX, TY = 82, FLOOR - 19     # 金蟾身体左上角（坐在石上）
TIP = (93, 8)               # 竿梢
STRING = 21                 # 钱串长
BITE_S, BITE_P, BITE_D = 16.0, 30.0, 7.0
TONGUE_S, TONGUE_P = 5.0, 11.0

# ---------------------------------------------------------------- 精灵


class _Grid:
    def __init__(self, w, h):
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


def _body(mouth="smile") -> Sprite:
    """正脸金蟾的头身 28×15：大笑嘴、腮红网点、鼻孔、额头铜钱纹、疣点"""
    b = _Grid(28, 15)
    b.rows({0: (5, 22), 1: (3, 24), 2: (1, 26), 3: (1, 26), 4: (0, 27), 5: (0, 27), 6: (0, 27), 7: (0, 27), 8: (0, 27),
            9: (0, 27), 10: (0, 27), 11: (1, 26), 12: (1, 26), 13: (3, 24), 14: (5, 22)})
    if mouth == "smile":
        b.pts([(2, 6), (3, 7), (4, 7)] + [(x, 8) for x in range(5, 23)] + [(23, 7), (24, 7), (25, 6)], ".")
    elif mouth == "open":     # 张嘴（吐舌、咬钱）
        b.pts([(2, 6), (3, 7), (4, 7)] + [(x, 8) for x in range(5, 23)] + [(23, 7), (24, 7), (25, 6)], ".")
        b.rows({9: (8, 19), 10: (10, 17)}, ".")
    elif mouth == "gulp":     # 咕嘟：嘴抿成一条小弧
        b.pts([(x, 8) for x in range(9, 19)] + [(8, 7), (19, 7)], ".")
    b.pts([(12, 4), (15, 4)], ".")
    b.pts([(3, 4), (5, 4), (4, 5), (22, 4), (24, 4), (23, 5)], ".")
    for p in [(1, 9), (26, 9), (7, 11), (20, 11), (3, 12), (24, 12), (10, 13), (17, 13), (8, 1), (19, 1)]:
        b.pts([p], ".")
    b.pts([(12, 1), (13, 1), (14, 1), (15, 1), (11, 2), (16, 2), (13, 2), (14, 2)], ".")
    return b.sprite()


def _eye(px=1, py=1, shut=False, happy=False) -> Sprite:
    """鼓眼 7×6：眼珠 2×2（px 0–3 左右，py 0–2 上下），右上一点高光"""
    e = _Grid(7, 6)
    e.rows({0: (2, 5), 1: (1, 6), 2: (0, 6), 3: (0, 6), 4: (0, 6), 5: (1, 5)})
    if shut:
        e.pts([(1, 3), (2, 4), (3, 4), (4, 4), (5, 3)], ".")
    elif happy:
        e.pts([(1, 4), (2, 3), (3, 2), (4, 3), (5, 4)], ".")
    else:
        x0, y0 = 1 + px, 1 + py
        e.pts([(x0, y0), (x0 + 1, y0), (x0, y0 + 1), (x0 + 1, y0 + 1)], ".")
        e.pts([(x0 + 1, y0)])
    return e.sprite()


LEG = Sprite("""
  ###
 ###
###
#####
#.#.#
""")

HIND = Sprite("""
 ###
#####
#.#.#
""")

COIN = Sprite("""
 ###
#####
##.##
#####
 ###
""")

GCOIN = Sprite("""
 ####
##..##
 ####
""")

FLY = pix.frames("""
# #
 #
---
 #
 #
""")


def _sac(k: int) -> Sprite:
    """喉囊：从嘴下鼓出来的白泡（三档）"""
    w, h = (8, 4) if k == 0 else ((10, 5) if k == 1 else (12, 6))
    p = Part(w, h)
    p.shape("ellipse", (0, 0, w - 1, h - 1), fill=1)
    p.px(2, 1, 0)
    p.px(w - 3, h - 2, 0)
    return p.sprite()


def _stone() -> Sprite:
    p = Part(38, 5)
    p.shape("polygon", [(0, 4), (3, 0), (34, 0), (37, 4)], fill=1)
    p.d.line((4, 1, 33, 1), fill=0)
    p.dither([(20, 2), (37, 2), (37, 4), (20, 4)], 0.5, 0)
    p.d.line((12, 2, 13, 4), fill=0)
    return p.sprite()


_S: dict = {}


def S(key):
    if not _S:
        for m in ("smile", "open", "gulp"):
            _S[("body", m)] = _body(m)
        for px in range(4):
            for py in range(3):
                _S[("eye", px, py)] = _eye(px, py)
        _S["shut"] = _eye(shut=True)
        _S["happy"] = _eye(happy=True)
        for k in range(3):
            _S[("sac", k)] = _sac(k)
        _S["stone"] = _stone()
    return _S[key]


# ---------------------------------------------------------------- 画

def toad(g: Gfx, x: float, y: float, look=(0.0, 0.0), mouth="smile", eyes="open", sac=None, squash=0.0,
         dangle=False):
    """x, y：头身左上角。look：眼珠朝向（-1..1）。squash>0 压扁（蓄力/落地），<0 拉长（起跳）"""
    x, y = int(round(x)), int(round(y))
    sq = int(round(squash * 3))
    leg_dy = 0 if not dangle else 3
    pix.blit(g, HIND, x + 12, y + 14 + leg_dy)
    pix.blit(g, S(("body", mouth)), x, y + max(sq, 0))
    if sac is not None:
        spr = S(("sac", sac))
        pix.blit(g, spr, x + 14 - spr.w // 2, y + 9 + max(sq, 0))
    spread = max(sq, 0)
    pix.blit(g, LEG, x - 2 - spread, y + 11 + leg_dy + max(sq, 0) // 2)
    pix.blit(g, LEG, x + 25 + spread, y + 11 + leg_dy + max(sq, 0) // 2, flip=True)
    ey = y - 4 + max(sq, 0) + (min(sq, 0))  # 拉长时眼睛更高
    if eyes == "open":
        px = max(0, min(3, int(round(1.5 + look[0] * 1.5))))
        py = max(0, min(2, int(round(1 + look[1]))))
        e = S(("eye", px, py))
    else:
        e = S(eyes)
    pix.blit(g, e, x + 1, ey)
    pix.blit(g, e, x + 20, ey)
    return (x + 14, y + 9 + max(sq, 0))    # 嘴


def pole_and_coins(g: Gfx, hand, tip, ang: float, coins=True):
    """竹竿（竹节）+ 钱串（钟摆）。返回最下面那枚钱的中心"""
    hx, hy = hand
    tx, ty = tip
    g.d.line((hx - 3, hy + 2, tx, ty), fill=1)
    g.d.line((hx - 3, hy + 3, tx, ty + 1), fill=1)
    n = 6
    for i in range(1, n):  # 竹节
        q = i / n
        nx, ny = lerp(hx - 3, tx, q), lerp(hy + 2, ty, q)
        g.px(nx, ny + 2, 1), g.px(nx - 1, ny + 2, 1)
    ex = tx + math.sin(ang) * STRING
    ey = ty + math.cos(ang) * STRING
    g.d.line((tx, ty, ex, ey), fill=1)
    if coins:
        for d in (STRING - 10, STRING - 5, STRING):
            cx = tx + math.sin(ang) * d
            cy = ty + math.cos(ang) * d
            pix.blit(g, COIN, cx - 2, cy - 2)
    return ex, ey


def scenery(g: Gfx, t: float):
    pix.blit(g, CLOUD[0], (t * 1.5 + 30) % 170 - 30, 3)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(2, 128, 7):
        g.px(x, FLOOR + 2)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    pix.blit(g, S("stone"), TX - 5, FLOOR - 4)
    pix.blit(g, GCOIN, 52, FLOOR - 3)
    pix.blit(g, GCOIN, 64, FLOOR - 2)
    for x, k in ((44, 0), (120, 1), (8, 2)):
        spr = pix.anim(GRASS_FR, t * 0.6 + k * 0.5, 1.2)
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


def mx_toad(g: Gfx, blink: bool, sac: bool):
    rows = ["##....##", "##....##" if not blink else "........", ".######.", "#.####.#", "#......#", ".######.",
            "#.####.#", "##.##.##"]
    if sac:
        rows[5] = "########"
        rows[6] = "########"
    mx_art(g, rows)


def mx_coin(g: Gfx):
    mx_art(g, ["..####..", ".######.", "###..###", "##....##", "##....##", "###..###", ".######.", "..####.."])


@register
class Toad(Rest):
    id = "x4.toad"
    name = "刘海戏金蟾"
    desc = "小道士扮刘海挑着一串铜钱逗正脸的三足金蟾：眼珠跟钱转、喉囊鼓、吐舌卷虫；一挑竿，金蟾一跃咬住铜钱悠两下"
    T = {"enter": 3.0, "exit": 1.4}

    def setup(self):
        self.clock = Clock()
        self.dust = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)

    def swing(self, t: float, big: float = 0.0) -> float:
        return 0.22 * math.sin(t * 2 * math.pi / 2.4) + big * 0.45 * math.sin(t * 2 * math.pi / 1.5)

    def scene(self, g: Gfx, t: float, dt: float, dao_x=DAO_X, dao_pose="offer", dao_flip=False, toad_xy=None,
              events=True, text=None, toad_on=True):
        scenery(g, t)
        blink = (t % 3.3) < 0.13
        sac_k = None
        k = t % 3.1
        if k < 0.9:
            sac_k = min(2, int(math.sin(k / 0.9 * math.pi) * 3))
        tip = (TIP[0] + int(round(dao_x - DAO_X)), TIP[1])
        big = 0.0
        tx, ty = toad_xy or (TX, TY)
        mouth, eyes, squash, dangle = "smile", "shut" if blink else "open", 0.0, False
        hanging = False
        dface = "normal"
        mxmode = "toad"
        bt = ev(t, BITE_P, BITE_S, BITE_D) if events else None
        if bt:
            L = bt[1]
            lift = ease_out(span(L, 0.0, 0.5)) * (1 - ease_in_out(span(L, 4.2, 5.2)))
            tip = (TIP[0] + int(lift * 2), TIP[1] - int(round(lift * 5)))
            big = span(L, 2.0, 2.4) * (1 - span(L, 4.0, 4.6))
            sac_k = None
            mxmode = "coin" if 1.6 < L < 4.6 else "toad"
            dface = "happy" if 2.0 < L < 6.0 else "normal"
            if L < 0.8:
                squash = 0.0
            elif L < 1.4:                       # 蹲低蓄力
                squash = ease_out(span(L, 0.8, 1.2)) * 1.0
            elif L < 2.0:                       # 起跳：拉长，冲向最下面那枚钱
                squash = -1.0
            elif L < 4.4:                       # 咬住、挂着悠
                hanging = True
                dangle = True
            elif L < 5.2:                       # 松口下落
                squash = -0.7
                dangle = True
            elif L < 5.5:                       # 落地压扁
                squash = 1.0
            else:
                squash = 0.0
        ang = self.swing(t, big)
        dpose = dao_pose
        h = daoshi(g, dao_x, FLOOR, dpose, t, flip=dao_flip, face=dface)
        end = pole_and_coins(g, h["hand"], tip, ang)
        look = (max(-1, min(1, (end[0] - (tx + 14)) / 10)), -1.0)
        if bt:
            L = bt[1]
            if 1.4 <= L < 2.0:                  # 空中：从石上弧线飞向钱
                q = ease_out(span(L, 1.4, 2.0))
                ex, ey = end
                tx = lerp(TX, ex - 14, q)
                ty = lerp(TY, ey - 9, q)
                mouth = "open"
            elif hanging:                       # 挂在钱串上，跟着摆
                tx, ty = end[0] - 14, end[1] - 9
                mouth = "open"
                eyes = "happy"
                if int(L * 8) % 3 == 0:
                    self.sparks.burst(end[0] + (int(L * 37) % 9 - 4), end[1] - 10, 1, 10, life=0.4, gravity=0)
            elif 4.4 <= L < 5.2:                # 落回石上
                q = ease_in(span(L, 4.4, 5.2))
                sx, sy = end[0] - 14, end[1] - 9
                tx, ty = lerp(sx, TX, q), lerp(sy, TY, q)
                eyes = "shut"
            elif L >= 5.2:
                hop = abs(math.sin(span(L, 5.5, 6.6) * math.pi * 2)) * 3 * (1 - span(L, 5.5, 6.6))
                ty = TY - hop
                if abs(L - 5.2) < dt * 1.5:
                    for s in (-1, 1):
                        self.dust.emit(TX + 14 + s * 14, FLOOR - 4, vx=s * 10, vy=-4, life=0.7, rmax=2.0)
                    pix.shake(g, t, 1.0)
                if L < 5.6:
                    eyes = "shut"
        # 小飞虫 + 吐舌
        tg = ev(t, TONGUE_P, TONGUE_S, None) if events and not bt else None
        fly_on = True
        fx = tx + 14 + math.sin(t * 2.3) * 16
        fy = ty - 10 + math.sin(t * 3.7) * 5
        tongue = None
        if tg:
            n, L = tg
            caught = n % 3 == 2
            if caught and L > 0.35:
                fly_on = L > 7.0          # 吃掉了，过一会儿又飞来一只
                if not fly_on and L < 1.4:
                    mouth, eyes = "gulp", "happy"
                if L > 7.0:                # 从左上飞回来
                    q = ease_out(span(L, 7.0, 9.0))
                    fx, fy = lerp(-4, fx, q), lerp(10, fy, q)
            if L < 0.35:
                q = math.sin(L / 0.35 * math.pi)
                tongue = q
                mouth = "open"
                if not caught and L > 0.12:  # 虫子一躲
                    fy -= 6 * span(L, 0.12, 0.35)
                    fx += 4 * span(L, 0.12, 0.35)
        mpos = toad(g, tx, ty, look, mouth, eyes, None if (hanging or bt and bt[1] < 6) else sac_k, squash, dangle) \
            if toad_on else (tx + 14, ty + 9)
        if hanging or (bt and 1.8 < bt[1] < 2.0):  # 最下面那枚铜钱叼在嘴里
            pix.blit(g, COIN, end[0] - 2, end[1] - 2)
        if tongue is not None:
            mx_, my_ = mpos
            ex, ey = lerp(mx_, fx, tongue), lerp(my_, fy, tongue)
            g.d.line((mx_, my_, ex, ey), fill=1)
            g.d.line((mx_ + 1, my_, ex + 1, ey), fill=1)
            g.d.ellipse((ex - 1, ey - 1, ex + 1, ey + 1), fill=1)
        if fly_on and toad_on:
            pix.blit(g, FLY[int(t * 18) % 2], fx - 1, fy - 1, outline=False)
        self.dust.step(dt)
        self.dust.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if bt and 5.6 < bt[1]:
            text = "步步钓金钱"
        if mxmode == "coin":
            mx_coin(g)
            if bt and 2.0 < bt[1] < 4.4 and int(t * 6) % 2 == 0:
                g.mx_level = 5
        else:
            mx_toad(g, eyes == "shut", sac_k is not None and sac_k >= 1)
        if text:
            label(g, 3, 3, text)
        return h

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        dx = lerp(-16, DAO_X, ease_out(span(t, 0, 1.8)))
        # 金蟾三跳：从 140 蹦到 TX
        hops = [(0.6, 140, 118), (1.3, 118, 98), (2.0, 98, TX)]
        tx, ty = 150, TY
        for a, x0, x1 in hops:
            if t >= a:
                q = span(t, a, a + 0.6)
                tx = lerp(x0, x1, q)
                ty = TY - math.sin(q * math.pi) * 9
        self.scene(g, t, dt, dao_x=dx, dao_pose="walk" if t < 1.8 else "offer", toad_xy=(tx, ty), events=False,
                   text="刘海戏金蟾" if t > 1.2 else None)

    def hold(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        self.scene(g, t, dt, text="刘海戏金蟾" if t < 6.0 else None)

    def exit(self, g: Gfx, t: float):
        dt = self.clock.dt(t)
        tt = self.hold_t + t
        x = TX
        y = TY
        for a, x0, x1 in ((0.0, TX, TX + 26), (0.5, TX + 26, TX + 60)):
            if t >= a:
                q = span(t, a, a + 0.5)
                x = lerp(x0, x1, q)
                y = TY - math.sin(q * math.pi) * 10
        dx = DAO_X + ease_in(span(t, 0.4, 1.4)) * 30
        self.scene(g, tt, dt, dao_x=dx, dao_pose="walk" if t > 0.4 else "offer", toad_xy=(x, y), events=False)
