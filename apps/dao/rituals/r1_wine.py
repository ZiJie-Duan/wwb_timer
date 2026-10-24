"""三献酒：露天醮坛，远山、两杆长幡迎风飘；矮供案上三只青铜爵，小道士提执壶初献、亚献、终献。

依据：祭礼三献（初献、亚献、终献），道教斋醮献供亦行三献；“酹”是把酒浇在地上致祭；
“爵”是三足、双柱、前流后尾、侧有鋬的古酒器。礼毕赞“礼成”。

入场：三只爵依次从天上落到供案上，“当”地一震、弹一下站稳；小道士走来站定，拱手；左上牌子“第一巡 初献”。
持续：一轮 600 秒分三献（第 10、200、400 秒）：小道士转身从小几上提起执壶，走到爵前，举壶倾倒，
      酒线注入、溅起酒花，爵口亮起酒面；放回执壶后对着那只爵作揖。斟满的爵口飘一缕酒香。
      长幡一直飘；隔一阵起一阵风，幡猛地扬起；每隔一阵一只仙鹤扇着翅膀飞过远山；小道士呼吸眨眼、作揖。
      续：酹酒——小道士捧起中间那只爵走到坛前，把酒浇在地上，溅起一圈酒花；另两爵的酒化作光点升空，
      “第几巡”加一，再从初献斟起。
中断：小道士拱手肃立，酒香散尽，牌子“暂歇”。  恢复：作揖，酒香复起。
圆满：三爵齐亮、放光，小道士跪拜，闪白，大字“礼成”弹出。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import FLOOR, Clock, badge, floor, hit, hold_at, mx_art, mx_burst, pose_arm, star, title, twinkles

TABLE = (62, 124, 47)          # 矮供案 x0, x1, 案面 y
CUPS = (75, 94, 113)           # 三只爵的中心
DX = 34                        # 小道士站位
STOOL_X = 14                   # 放执壶的小几
OFFER_AT = (10.0, 200.0, 400.0)
STAGES = ("初献", "亚献", "终献")
POUR = 12.0                    # 一献的表演长度
RENEW = 8.0

JUE = pix.sprite("""
       ## ##
        # #
##      # #
.##############.#
 .#############
   #.#.#.#.#.#.##
   ###########  #
   #.#.#.#.#.#.##
   ###########
    #########
    .#.#.#.#.
     #######
     #  #  #
    #   #   #
   #    #    #
""")

CRANE = pix.frames("""
  ##
 ####
#######        .
   ########  .##
     ##############
      ###.  #
      #     .
---
          ##
         ##
        ##
#######..###   .
   #############.##
     ##############
""")

BANNER_TAIL = 4


EWER_ART = """
     ##          #
    ####        ##
     ..        ##
    ####      ##
 #.######.  ##.
#  ########..#
#.##########.
#.###########
#.#.#.#.#.##.
 .##########
  .#.#.#.#.
   #######
  #########
"""
EWER_GRIP = (0, 7)
EWER_TIP = (16, 0)

# 前倾约 35° 的执壶（逐像素手画）：流口朝右下
EWER_TILT_ART = """
       ##
      ####
  #    ..#
 #   #####
 #.########.
  .#########.
  #.##########
   #.##########.
    #.#.#.#.##.##
     .#########.###
      .#.#.#.#.  ###
       #######     ##
        #####       #
"""
TILT_GRIP = (1, 4)
TILT_TIP = (20, 12)


def _ewer(ang: int):
    """执壶：ang=0 立着，其他 = 前倾倒酒。返回 (精灵, 握点)，精灵 .tip = 流口"""
    if ang == 0:
        spr = pix.sprite(EWER_ART)
        spr.tip = EWER_TIP
        return spr, EWER_GRIP
    spr = pix.sprite(EWER_TILT_ART)
    spr.tip = TILT_TIP
    return spr, TILT_GRIP


def _stool():
    """小几 13×8：几面、两条弯腿、横枨"""
    p = Part(13, 8)
    p.shape("rectangle", (0, 0, 12, 1), fill=1)
    p.d.line((1, 1, 11, 1), fill=0)
    for x in (2, 10):
        p.shape("line", (x, 2, x - 1 if x < 6 else x + 1, 7), fill=1)
    p.shape("line", (2, 5, 10, 5), fill=1)
    return p.sprite()


_P: dict = {}


def P(name, *a):
    k = (name,) + a
    if k not in _P:
        _P[k] = {"ewer": _ewer, "stool": _stool}[name](*a)
    return _P[k]


# ---------------------------------------------------------------- 背景

def altar(g: Gfx, t: float, gust: float = 0.0):
    """露天醮坛：远山（虚线山脊）、两杆长幡（飘动）、地面石砖、矮供案（案裙云纹）"""
    ridge = [(0, 30), (14, 24), (26, 28), (40, 19), (54, 26), (66, 23), (80, 29), (96, 21), (110, 27), (127, 22)]
    for (x0, y0), (x1, y1) in zip(ridge, ridge[1:]):
        pix.dotted(g, x0, y0, x1, y1, 2)
    floor(g)
    for px in (3, 124):                        # 幡
        g.d.line((px, 3, px, FLOOR), fill=1)
        g.d.rectangle((px - 2, 2, px + 2, 3), fill=1)
        g.px(px, 1)
        s = 1 if px < 64 else -1
        for i in range(26):
            y = 6 + i
            amp = (0.6 + 2.5 * gust) * (i / 26)
            off = math.sin(t * (3 + 4 * gust) - i * 0.35) * amp + gust * i * 0.25
            x = px + s * (2 + off)
            w = 4 if i < 24 else 2
            g.d.line((x, y, x + s * w, y), fill=1)
            if i % 6 == 3:
                g.d.line((x + s, y, x + s * (w - 1), y), fill=0)
    x0, x1, ty = TABLE
    g.d.rectangle((x0, ty, x1, ty + 1), fill=1)
    g.d.rectangle((x0 + 2, ty + 2, x1 - 2, FLOOR - 1), outline=1, fill=0)
    for x in range(x0 + 6, x1 - 6, 14):        # 案裙卷云纹
        g.d.arc((x, ty + 3, x + 6, ty + 9), 180, 90, fill=1)
        g.d.arc((x + 6, ty + 3, x + 12, ty + 9), 90, 0, fill=1)
    pix.checker(g, (x0 + 3, FLOOR - 3, x1 - 2, FLOOR - 1), 0.5)


def cup_top(i: int):
    return CUPS[i], TABLE[2] - JUE.h + 3


def cups(g: Gfx, full, t: float, drop=None):
    """三只爵：full[i] 0..1 酒面（爵口亮线）"""
    for i, cx in enumerate(CUPS):
        y = TABLE[2] - JUE.h
        if drop is not None:
            y = lerp(-20, y, drop[i])
        pix.blit(g, JUE, cx - 8, y)
        if full[i] > 0:
            w = int(round(5 * full[i]))
            g.d.line((cx - w, y + 4, cx + w, y + 4), fill=0)
            g.d.line((cx - w + 1, y + 4, cx + w - 1, y + 4), fill=1)
            if full[i] >= 1 and int(t * 3 + i) % 4 == 0:  # 酒面上一点暗光游走
                g.px(cx - 3 + int(t * 4 + i * 2) % 7, y + 3, 0)


def aroma(g: Gfx, t: float, i: int, k: float = 1.0):
    """酒香：一缕细细的波浪线往上飘"""
    cx, cy = cup_top(i)
    n = int(12 * k)
    for j in range(n):
        y = cy - 2 - j
        x = cx + math.sin(t * 2.5 - j * 0.45 + i) * (0.5 + j * 0.12)
        if (j + int(t * 6)) % 5 != 0:
            g.px(x, y)


def mx_jue(g: Gfx, n_full: int, pouring: bool, t: float):
    mx_art(g, """
..#..#..
########
.######.
.######.
..####..
.#.##.#.
#..#...#
""", 0, 1)
    for r in range(min(n_full, 3)):
        g.mx[4 - r, 2:6] = False
        g.mx[4 - r, 2:6] = r < n_full
    if n_full == 0:
        g.mx[3, 2:6] = False
        g.mx[4, 2:6] = False
    if pouring:
        g.mx[0, 4] = int(t * 8) % 2 == 0


# ---------------------------------------------------------------- 场景

@register
class ThreeOfferings(Ritual):
    id = "r1.wine"
    name = "三献酒"
    desc = "露天醮坛，长幡飘飘；小道士提执壶初献、亚献、终献，斟满的爵口飘酒香；一轮后捧爵酹酒于地"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 1.6, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    def level(self, e: float, i: int) -> float:
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return 0.0
        return span(k, OFFER_AT[i] + 5.0, OFFER_AT[i] + 7.0)

    def stage(self, e: float) -> int:
        k = e % self.CYCLE
        return 2 if k >= OFFER_AT[2] else (1 if k >= OFFER_AT[1] else 0)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        s = label or ((f"第{cn_num(n)}巡 " if n < 100 else f"{n}巡 ") + STAGES[self.stage(e)])
        badge(g, 12, 4, s)

    def stool(self, g: Gfx, ewer: bool = True):
        pix.blit(g, P("stool"), STOOL_X - 6, FLOOR - 8)
        if ewer:
            spr, grip = P("ewer", 0)
            pix.blit(g, spr, STOOL_X - 7, FLOOR - 9 - spr.h)

    def fx(self, g: Gfx, dt: float):
        self.sparks.step(dt)
        self.sparks.draw(g)

    def ambient(self, g: Gfx, e: float, t: float):
        """仙鹤飞过远山"""
        k = (e + self.seed * 7) % 45
        if k < 9:
            x = lerp(140, -30, k / 9)
            y = 12 + math.sin(k * 1.3) * 2
            pix.blit(g, pix.anim(CRANE, t, 3), x, y)

    def gust(self, e: float) -> float:
        k = (e + self.seed) % 37
        return span(k, 20, 21) * (1 - span(k, 23, 25))

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        altar(g, t)
        self.stool(g)
        drop = [ease_out_bounce(span(t, 0.2 + i * 0.4, 1.0 + i * 0.4)) for i in range(3)]
        cups(g, (0, 0, 0), t, drop)
        for i in range(3):
            if hit(t, 0.2 + i * 0.4 + 0.29, dt):
                pix.shake(g, t, 1.0)
                cx, _ = cup_top(i)
                self.sparks.burst(cx, TABLE[2] - 1, 8, 22, up=10, life=0.4, gravity=60)
        x = lerp(-14, DX, ease_out(span(t, 1.6, 3.6)))
        if t < 3.6:
            daoshi(g, x, FLOOR, "walk", t)
        else:
            daoshi(g, DX, FLOOR, "gongshou" if t < 4.4 else ("bow" if t < 5.1 else "idle"), t)
        self.fx(g, dt)
        if t > 3.6:
            self.counter(g, 0.0)
        mx_jue(g, 0, False, t)

    # ------------------------------------------------------------ 持续

    def pour(self, g: Gfx, t: float, u: float, i: int, dt: float):
        """u ∈ [0, POUR]：转身提壶 → 走到爵前 → 举壶倒酒 → 走回放壶 → 对爵作揖"""
        stand = CUPS[i] - 26
        spr0, grip = P("ewer", 0)
        if u < 1.0:
            h = pose_arm(g, DX, FLOOR, t, 60 if u > 0.3 else 30, flip=True)
            self.stool(g, ewer=u < 0.6)
            if u >= 0.6:
                hold_at(g, spr0, h["hand"], grip, flip=True)
            return
        self.stool(g, ewer=u >= 10.0)
        if u < 2.6:
            x = lerp(DX, stand, ease_in_out(span(u, 1.0, 2.6)))
            h = pose_arm(g, x, FLOOR, t, 30, legs="walk")
            hold_at(g, spr0, h["hand"], grip)
        elif u < 6.6:
            tilt = ease_in_out(span(u, 2.8, 3.4)) * (1 - ease_in_out(span(u, 6.0, 6.6)))
            h = daoshi(g, stand, FLOOR, "raise", t, face="happy" if u > 5.4 else "normal")
            ang = 1 if tilt > 0.5 else 0
            spr, gp = P("ewer", ang)
            hold_at(g, spr, h["hand"], gp)
            if 3.3 <= u < 6.1:  # 酒线 + 酒花
                tx = h["hand"][0] - gp[0] + spr.tip[0]
                ty = h["hand"][1] - gp[1] + spr.tip[1]
                cx, cy = cup_top(i)
                g.d.line((tx, ty + 1, tx, cy + 1), fill=1)
                if int(t * 15) % 3 == 0:
                    self.sparks.burst(tx, cy + 1, 1, 10, up=12, life=0.3, gravity=60)
        elif u < 8.4:
            x = lerp(stand, DX, ease_in_out(span(u, 6.6, 8.4)))
            h = pose_arm(g, x, FLOOR, t, 30, legs="walk", flip=True)
            hold_at(g, spr0, h["hand"], grip, flip=True)
        elif u < 10.0:
            h = pose_arm(g, DX, FLOOR, t, 60 if u > 9.0 else 30, flip=True)
            if u < 9.6:
                hold_at(g, spr0, h["hand"], grip, flip=True)
        else:
            daoshi(g, DX, FLOOR, "gongshou" if u < 11.0 else "bow", t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e, dt)
            return
        altar(g, t, self.gust(e))
        self.ambient(g, e, t)
        full = [self.level(e, i) for i in range(3)]
        cups(g, full, t)
        for i in range(3):
            if full[i] >= 1:
                aroma(g, t, i)
        pouring = False
        for i, a in enumerate(OFFER_AT):
            if a <= k < a + POUR:
                self.pour(g, t, k - a, i, dt)
                pouring = 3.3 <= k - a < 6.1
                break
        else:
            self.stool(g)
            c = (k + self.seed * 3) % 30
            if 22 <= c < 24.4:
                daoshi(g, DX, FLOOR, "gongshou" if c < 23.2 else "bow", t)
            else:
                daoshi(g, DX, FLOOR, "idle", t, face="happy" if self.gust(e) > 0.5 else "normal")
        self.fx(g, dt)
        self.counter(g, e)
        mx_jue(g, sum(1 for f in full if f >= 1), pouring, t)

    def _renew(self, g: Gfx, t: float, k: float, e: float, dt: float):
        """酹酒：捧起中间那只爵走到坛前，把酒浇在地上；另两爵的酒化作光点升起"""
        altar(g, t)
        self.stool(g)
        f = [1 - span(k, 1.0, 3.0), 1.0 if k < 2.2 else 0.0, 1 - span(k, 1.0, 3.0)]
        lifted = 1.4 <= k < 6.4
        for i, cx in enumerate(CUPS):
            if i == 1 and lifted:
                continue
            pix.blit(g, JUE, cx - 8, TABLE[2] - JUE.h)
            if f[i] > 0:
                g.d.line((cx - 4, TABLE[2] - JUE.h + 4, cx + 4, TABLE[2] - JUE.h + 4), fill=1)
        for i in (0, 2):    # 光点升起
            q = span(k, 1.0, 3.6)
            if 0 < q < 1:
                cx, cy = cup_top(i)
                for j in range(3):
                    star(g, cx + math.sin(q * 8 + j * 2) * 3, cy - q * 30 - j * 5, 1 if j == 0 else 0)
        stand = CUPS[1] - 17
        if k < 1.4:
            x = lerp(DX, stand, ease_in_out(span(k, 0.0, 1.4)))
            daoshi(g, x, FLOOR, "walk", t)
        elif k < 2.2:
            h = daoshi(g, stand, FLOOR, "raise", t)
            pix.blit(g, JUE, h["hand"][0] - 7, h["hand"][1] - 6)
        elif k < 3.4:
            x = lerp(stand, 44, ease_in_out(span(k, 2.2, 3.4)))
            h = pose_arm(g, x, FLOOR, t, 0, legs="walk", flip=True)
            pix.blit(g, JUE, h["hand"][0] - 7, h["hand"][1] - 9, flip=True)
        elif k < 5.2:   # 酹：爵口朝下，酒浇到地上
            h = pose_arm(g, 44, FLOOR, t, 30, flip=True)
            hx, hy = h["hand"]
            pix.blit(g, JUE.rot90(1) if k > 3.7 else JUE, hx - 7, hy - 9, flip=True)
            if 3.8 <= k < 5.0:
                sx = hx - 8
                g.d.line((sx, hy + 2, sx - 2, FLOOR - 1), fill=1)
                if int(t * 15) % 2 == 0:
                    self.sparks.burst(sx - 2, FLOOR - 1, 2, 18, up=14, life=0.35, gravity=70)
            if k > 4.2:   # 地上一摊酒
                w = int(span(k, 4.2, 5.0) * 6)
                g.d.line((hx - 10 - w, FLOOR + 1, hx - 6 + w, FLOOR + 1), fill=1)
        elif k < 6.4:
            x = lerp(44, stand, ease_in_out(span(k, 5.2, 6.4)))
            h = pose_arm(g, x, FLOOR, t, 0, legs="walk")
            pix.blit(g, JUE, h["hand"][0] - 7, h["hand"][1] - 9)
        elif k < 7.0:
            daoshi(g, stand, FLOOR, "bow", t)
        else:
            x = lerp(stand, DX, ease_in_out(span(k, 7.0, 8.0)))
            daoshi(g, x, FLOOR, "walk", t, flip=True)
        self.fx(g, dt)
        self.counter(g, e if k >= 5.0 else e - k - 1)
        mx_jue(g, 0 if k > 3.0 else 3, 3.8 <= k < 5.0, t)

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        altar(g, t)
        self.stool(g)
        full = [self.level(e, i) for i in range(3)]
        cups(g, full, t)
        for i in range(3):
            if full[i] >= 1:
                aroma(g, t, i, 1 - span(t, 0.2, 1.2))
        daoshi(g, DX, FLOOR, "gongshou" if t > 0.3 else "idle", t)
        self.fx(g, dt)
        self.counter(g, e, "暂歇" if t > 0.6 else None)
        mx_jue(g, sum(1 for f in full if f >= 1), False, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        altar(g, t)
        self.stool(g)
        full = [self.level(e, i) for i in range(3)]
        cups(g, full, t)
        for i in range(3):
            if full[i] >= 1:
                aroma(g, t, i, span(t, 0.4, 1.4))
        daoshi(g, DX, FLOOR, "gongshou" if t < 0.6 else ("bow" if t < 1.3 else "idle"), t)
        if hit(t, 0.6, dt):
            for i in range(3):
                if full[i] >= 1:
                    cx, cy = cup_top(i)
                    self.sparks.burst(cx, cy, 6, 14, up=8, life=0.4, gravity=20)
        self.fx(g, dt)
        self.counter(g, e)
        mx_jue(g, sum(1 for f in full if f >= 1), False, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        altar(g, t)
        self.stool(g)
        full = [max(self.level(e, i), span(t, 0.2 + i * 0.3, 0.6 + i * 0.3)) for i in range(3)]
        cups(g, full, t)
        for i in range(3):
            aroma(g, t, i)
        pose = "gongshou" if t < 1.4 else ("kneel" if t < 4.6 else "idle")
        daoshi(g, DX, FLOOR, pose, t, face="happy" if t > 4.6 else "normal")
        if t > 1.6:    # 三爵放光
            for i, cx in enumerate(CUPS):
                cy = TABLE[2] - JUE.h // 2
                for j in range(8):
                    a = -math.pi * (j + 0.5) / 8
                    r0, r1 = 9, 11 + 2 * ((int(t * 6) + j) % 2)
                    g.d.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0 - 3,
                              cx + math.cos(a) * r1, cy + math.sin(a) * r1 - 3), fill=1)
        if hit(t, 1.6, dt):
            pix.flash(g)
            for cx in CUPS:
                self.sparks.burst(cx, TABLE[2] - 12, 12, 34, up=16, life=1.0, gravity=40)
        if 1.6 < t < 1.9:
            pix.shake(g, t, 1.5)
        self.fx(g, dt)
        if t > 2.0:
            title(g, 46, 5, "礼成", t, 2.0, scale=2)
        mx_jue(g, 3, False, t)
        mx_burst(g, t, 1.6)
