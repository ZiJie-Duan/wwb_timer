"""鲲鹏：北冥有鱼，化而为鸟。

依据：《庄子·逍遥游》“北冥有鱼，其名为鲲。鲲之大，不知其几千里也。化而为鸟，其名为鹏。鹏之背，不知其几千里也；
      怒而飞，其翼若垂天之云。……鹏之徙于南冥也，水击三千里，抟扶摇而上者九万里。”
入场：海平线从中间向两边拉开，浪纹一行行铺开，水下的鲲影慢慢显出来；左上“北冥有鱼”。
持续：一轮 60 秒——
      0–18 秒  鲲（鲤形大鱼：钝圆大头、圆鳞、长背鳍、叉尾三帧摆动）在水下慢慢游（水下部分是网点影子，浪纹压在上面），
               不时拱出水面，背鳍划开浪花；左上“北冥有鱼”；
      18–23 秒 摆尾蓄力，破水跃出（身子先昂头、再放平），水花溅起；
      23.5 秒  半空一闪，光圈荡开，化成鹏（弹出）；
      24–38 秒 鹏展开巨翼几乎横跨全屏，慢慢扇动（四帧），每扇一下海面一排水花溅起；下方字幕“化而为鸟”“其翼若垂天之云”；
      38–50 秒 鹏盘旋上升，越飞越小（大 → 中 → 小 → 一点），“抟扶摇而上”；
      50–60 秒 一个小黑点从高空直坠入海，水柱冲起、一圈圈水纹、屏幕一震，水下又是那条鲲。
      浪纹一直在流，云慢慢飘。
收场：上下两道黑幕向海平线合拢。
点阵：鱼（尾巴摆）/ 扇翅的鸟；化鹏与坠海时亮度一冲并荡开一圈。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import CLOUD, Clock, label, mx_art, sparkle

WL = 36            # 海平面
CYCLE = 60.0
LEAP0, APEX = 18.0, 23.5
FALL_X = 34


# ---------------------------------------------------------------- 鲲

def _kun_body() -> Sprite:
    """鲲身（不含尾、背鳍）50×21，朝右：鲤形，钝圆大头、圆鳞、胸鳍"""
    p = Part(50, 21)
    p.shape("ellipse", (6, 1, 49, 19), fill=1)
    p.shape("polygon", [(0, 7), (10, 4), (10, 16), (0, 13)], fill=1)
    p.dither([(2, 14), (48, 14), (48, 20), (2, 20)], 0.5, 0)          # 腹部背光
    for y in range(3, 18):                                              # 鳃盖
        p.px(37 - int(round(3 * math.sin((y - 3) / 14 * math.pi))), y, 0)
    for row, y in enumerate((5, 9)):                                    # 圆鳞
        for x in range(10 + (row % 2) * 3, 32, 6):
            p.px(x + 1, y - 1, 0), p.px(x, y, 0), p.px(x + 1, y + 1, 0)
    for x in range(8, 34, 2):                                           # 侧线
        p.px(x, 12, 0)
    p.d.rectangle((41, 6, 43, 9), fill=0)                               # 眼
    p.px(41, 6, 1)
    p.px(44, 7, 0)
    p.d.line((46, 12, 49, 12), fill=0)                                  # 嘴
    p.px(45, 11, 0)
    p.shape("line", [(47, 13), (48, 16), (46, 19)], fill=1)             # 须
    p.shape("polygon", [(34, 13), (28, 19), (31, 20), (37, 15)], fill=1)  # 胸鳍
    p.d.line((33, 15, 30, 19), fill=0)
    return p.sprite()


DORSAL = pix.sprite("""
        ##
      ####
    ##.#.##
  ##.#.#.##
 #.#.#.#.###
################
""")

TAIL = pix.frames("""
###
 ####
  #.###
   #.###
     ####
     ####
   #.###
  #.###
 ####
###
---

 ###
  ####
   #.###
     ####
     ####
   #.###
  ####
 ###

---
  #
  ###
   #.###
    #.###
     ####
     ####
   #.####
  #.###
 ####
###
#
""")


def _compose(tail_i: int) -> Sprite:
    """整条鲲（尾 + 背鳍 + 身）合成一个精灵 62×27；部件之间有黑描边"""
    from ..engine.gfx import Gfx
    g = Gfx()
    g.clear()
    body = _kun_body()
    tl = TAIL[tail_i]
    pix.blit(g, DORSAL, 18, 1)
    pix.blit(g, tl, 2, 15 - tl.h // 2 + 1)
    pix.blit(g, body, 10, 5)
    a = g.array()[0:27, 0:62]
    # 不透明范围：亮像素膨胀一圈（描边也算进去）
    m = a.copy()
    m[1:] |= a[:-1]
    m[:-1] |= a[1:]
    m[:, 1:] |= a[:, :-1]
    m[:, :-1] |= a[:, 1:]
    return Sprite(on=a, mask=m)


def _shear(spr: Sprite, k: float) -> Sprite:
    """按列错位（昂头 / 低头）：x 越往右（头）抬得越高"""
    h, w = spr.h, spr.w
    pad = int(abs(k) * w) + 1
    on = np.zeros((h + 2 * pad, w), bool)
    mk = np.zeros((h + 2 * pad, w), bool)
    for x in range(w):
        dy = pad - int(round((x - w / 2) * k))
        on[dy:dy + h, x] = spr.on[:, x]
        mk[dy:dy + h, x] = spr.mask[:, x]
    s = Sprite(on=on, mask=mk)
    s.pad = pad
    return s


def _ghost(spr: Sprite) -> Sprite:
    """水下的影子：只剩一圈虚线轮廓 + 眼睛"""
    def erode(m):
        e = m.copy()
        e[1:] &= m[:-1]
        e[:-1] &= m[1:]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        return e
    inner = erode(spr.mask)            # 去掉黑描边那一圈
    edge = inner & ~erode(inner)
    ys, xs = np.mgrid[0:spr.h, 0:spr.w]
    on = edge | (inner & (xs % 4 == 0) & (ys % 4 == 2))
    return Sprite(on=on, mask=on.copy())


KUN = [_compose(i) for i in range(3)]
KUN_GHOST = [_ghost(s) for s in KUN]
for _g in KUN_GHOST:  # 影子里也看得见眼睛
    _g.on[11:15, 51:54] = True
    _g.mask[11:15, 51:54] = True
    _g.on[11, 51] = False
    _g.__init__(on=_g.on, mask=_g.mask)
KUN_UP = [_shear(s, 0.35) for s in KUN]
KUN_UP_GHOST = [_ghost(s) for s in KUN_UP]
_CLIP: dict = {}


def _clip_top(spr: Sprite, n: int) -> Sprite | None:
    """只取精灵上面 n 行（露出水面的部分）"""
    if n <= 0:
        return None
    if n >= spr.h:
        return spr
    key = (id(spr), n)
    c = _CLIP.get(key)
    if c is None:
        c = _CLIP[key] = Sprite(on=spr.on[:n].copy(), mask=spr.mask[:n].copy())
    return c


# ---------------------------------------------------------------- 鹏

def _peng(L: int, ang: float) -> Sprite:
    """鹏（正面略仰视）：翼展约 2L；ang>0 翅上扬。锚点 .anchor = 身体中心"""
    from PIL import Image, ImageDraw
    W = 2 * L + 10
    H = int(L * 0.9) + 26
    cx, cy = W // 2, int(L * 0.45) + 7
    on, mk = Image.new("1", (W, H)), Image.new("1", (W, H))
    d, m = ImageDraw.Draw(on), ImageDraw.Draw(mk)

    def both(fn, *a, fill=1):
        getattr(d, fn)(*a, fill=fill)
        getattr(m, fn)(*a, fill=1)

    big = L > 30
    depth = max(3, L * 0.26)
    for side in (1, -1):
        lead, trail = [], []
        n = 24
        for i in range(n + 1):
            s = i / n
            a1 = ang * 0.5 + (ang * 0.9) * max(s - 0.4, 0) / 0.6
            x = s * L
            y = -math.sin(ang * 0.5) * min(s, 0.4) * L - (math.sin(a1) * (s - 0.4) * L if s > 0.4 else 0)
            y -= 2 * math.sin(s * math.pi) * (L / 30)
            lead.append((cx + side * (x + 4), cy + y))
            dep = depth * (1 - 0.55 * s)
            if s > 0.55 and L > 15 and int((s - 0.55) * n) % 2 == 0:
                dep += 3 if big else 2
            trail.append((cx + side * (x + 4), cy + y + dep + 2))
        both("polygon", lead + trail[::-1])
        if big:  # 覆羽线、飞羽分界、羽片
            d.line([(px, py + 3) for px, py in lead[2:-3]], fill=0)
            d.line([(lx, ly + (ty - ly) * 0.55) for (lx, ly), (tx, ty) in zip(lead[1:-2], trail[1:-2])], fill=0)
            for i in range(2, n - 1, 2):
                lx, ly = lead[i]
                tx, ty = trail[i]
                d.line((tx, ly + (ty - ly) * 0.6 + 1, tx, ty - 1), fill=0)
        elif L > 15:
            d.line([(lx, ly + (ty - ly) * 0.5) for (lx, ly), (tx, ty) in zip(lead[2:-3], trail[2:-3])], fill=0)
    tl = max(4, L * 0.35)  # 尾羽扇
    both("polygon", [(cx - 3, cy + 6), (cx + 3, cy + 6), (cx + tl * 0.5, cy + 6 + tl), (cx - tl * 0.5, cy + 6 + tl)])
    if big:
        for j in (-2, 0, 2):
            d.line((cx + j * 0.6, cy + 9, cx + j * tl / 6, cy + 5 + tl), fill=0)
    bw, bh = max(3, L * 0.13), max(4, L * 0.2)  # 身
    both("ellipse", (cx - bw, cy - 2, cx + bw, cy + bh + 2))
    if big:
        d.line((cx - bw + 1, cy + bh * 0.6, cx + bw - 1, cy + bh * 0.6), fill=0)
        for yy in range(int(cy + 1), int(cy + bh), 2):
            d.point((cx - 1 + (yy % 4) // 2, yy), fill=0)
    hr = max(2, L * 0.09)  # 头（侧向右）、短钩喙、冠羽
    hx, hy = cx + 1, cy - 3 - hr
    both("ellipse", (hx - hr, hy - hr, hx + hr, hy + hr))
    bl = max(2, hr * 0.9)
    if big:  # 钩喙：上喙尖往下弯
        both("polygon", [(hx + hr - 1, hy - 2), (hx + hr + bl - 1, hy - 1), (hx + hr + bl, hy + 1),
                         (hx + hr + bl - 1, hy + 3), (hx + hr + bl - 2, hy + 1), (hx + hr - 1, hy + 2)])
        d.line((hx + hr, hy + 1, hx + hr + bl - 3, hy + 1), fill=0)
    else:
        both("polygon", [(hx + hr - 1, hy - 1), (hx + hr + bl, hy), (hx + hr + bl, hy + 1), (hx + hr - 1, hy + 1)])
    if big:
        d.rectangle((hx + 1, hy - 2, hx + 2, hy - 1), fill=0)
        d.point((hx + 1, hy - 2), fill=1)
        both("line", [(hx - hr + 1, hy - hr), (hx - hr - 3, hy - hr - 3), (hx - hr - 5, hy - hr - 2)])
        both("line", [(hx - hr + 2, hy - hr - 1), (hx - hr - 1, hy - hr - 5)])
    s = Sprite(on=np.array(on, bool), mask=np.array(mk, bool))
    s.anchor = (cx, cy)
    return s


ANGS = (0.45, 0.15, -0.3, 0.15)     # 上扬、平、下扇、平
PENG = [_peng(52, a) for a in ANGS]
PENG_M = [_peng(22, a) for a in ANGS]
PENG_S = [_peng(9, a) for a in ANGS]

WAVE = pix.frames("""
 ##
#  #
---
 ###
#   #
---
  ##
##  ##
""")

SPLASH = pix.frames("""
  #   #
#  # #  #
 # ### #
  #####
---
 #  #  #
  # # #
#  ###  #
 #######
---
#   #   #
 #  #  #
  # # #
 ### ###
""")

COLUMN = pix.sprite("""
  # # #
 #.###.#
  #####
 #.###.#
  #####
 ##.#.##
  #####
 ##.#.##
 #######
##.###.##
#########
""")

MX_FISH = [
    ["        ", "  ####  ", "#######.", " #######", "#######.", "  ####  ", "        ", "        "],
    ["        ", "  ####  ", " ######.", "########", " ######.", "  ####  ", "        ", "        "],
]
MX_BIRD = [
    ["#      #", "##    ##", " ##  ## ", "  ####  ", "   ##   ", "  ####  ", "        ", "        "],
    ["        ", "        ", "### ####", " ###### ", "   ##   ", "  ####  ", "        ", "        "],
    ["        ", "        ", "   ##   ", " ###### ", "## ## ##", "#  ##  #", "  ####  ", "        "],
    ["        ", "        ", "### ####", " ###### ", "   ##   ", "  ####  ", "        ", "        "],
]


@register
class KunPeng(Rest):
    id = "x4.kunpeng"
    name = "鲲鹏"
    desc = "北冥大鱼在水下游、拱出水面，跃出化为巨鹏，展翼垂天、水击三千里，扶摇而上，又坠海化鲲"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        r = self.rng
        self.sparks = pix.Sparks(self.seed)
        self.clock = Clock()
        self.waves = []
        for row, (y, sp, gap) in enumerate(((WL + 3, 2.0, 11), (WL + 7, 3.5, 13), (WL + 12, 5.0, 15),
                                            (WL + 18, 7.0, 17), (WL + 25, 9.0, 19))):
            for x in range(0, 128 + gap, gap):
                self.waves.append((x + r.random() * gap * 0.6, y, sp, min(row, 2), gap))
        self.clouds = [(r.random() * 160, 3 + r.random() * 14, 0.6 + r.random() * 0.8, i % 2) for i in range(3)]
        self.stars = [(int(r.random() * 128), int(r.random() * 30)) for _ in range(6)]
        self.flap_last = -1

    # ------------------------------------------------------------ 背景

    def sky(self, g: Gfx, t: float, open_k: float = 1.0):
        for x, y in self.stars:
            if (x + int(t * 0.7)) % 5:
                g.px(x, y)
        for x, y, sp, k in self.clouds:
            cx = (x + t * sp) % 180 - 30
            pix.blit(g, CLOUD[k], cx, y)
        half = 64 * open_k
        g.d.line((64 - half, WL, 64 + half, WL), fill=1)

    def sea(self, g: Gfx, t: float, open_k: float = 1.0, rough: float = 0.0):
        for x, y, sp, k, gap in self.waves:
            span_w = 128 + gap * 2
            xx = (x - t * sp) % span_w - gap
            if abs(xx - 64) > 64 * open_k + 4:
                continue
            yy = y + (math.sin(t * 2 + x * 0.3) * rough * 1.5 if rough else 0)
            fr = WAVE[(k + int(t * 1.5 + x)) % 3 if rough else k]
            pix.blit(g, fr, xx, yy, outline=False)

    # ------------------------------------------------------------ 鲲

    def kun_x(self, c: float) -> float:
        """鲲的头部中心 x：54 秒在坠海点出现，慢慢往右游，18 秒到跃出点"""
        k = c - 54 if c >= 50 else c + 6
        return FALL_X + k * 1.4

    def kun(self, g: Gfx, x: float, top: float, t: float, i: int | None = None, up: bool = False):
        """水面以上画实身，水面以下只画虚线轮廓（影子）"""
        i = int(t * 3) % 3 if i is None else i
        s, gh = (KUN_UP[i], KUN_UP_GHOST[i]) if up else (KUN[i], KUN_GHOST[i])
        sx, top = int(x - s.w / 2), int(round(top))
        pix.blit(g, gh, sx, top, outline=False)
        above = _clip_top(s, WL + 1 - top)
        if above is not None:
            pix.blit(g, above, sx, top)
            g.d.line((sx - 2, WL, sx + s.w + 2, WL), fill=1)

    def swim(self, g: Gfx, c: float, t: float, fade: float = 1.0):
        x = self.kun_x(c)
        # 拱出水面：6–9、12–14.5 秒，背鳍划开水面
        rise = max(math.sin(span(c, 6.0, 9.0) * math.pi), math.sin(span(c, 12.0, 14.5) * math.pi)) if c < 18 else 0
        top = WL + 6 - rise * 9
        if c >= 50:
            top += 4 * (1 - span(c, 54, 60))
        self.kun(g, x, top, t)
        if fade < 1:
            pix.checker(g, (0, WL + 1, 128, 64), 0.75 if fade < 0.5 else 0.5, fill=0)
        if rise > 0.5 and int(t * 10) % 3 == 0:
            self.sparks.burst(x + 2, WL, 2, 14, up=12, life=0.5, gravity=50)
        if rise > 0.3:  # 背鳍两侧的浪花
            for dx in (-14, 12):
                pix.blit(g, WAVE[int(t * 6) % 3], x + dx, WL - 1, outline=False)
        return x, top

    # ------------------------------------------------------------ 主画面

    def scene(self, g: Gfx, t: float, open_k: float = 1.0, enter: bool = False):
        dt = self.clock.dt(t)
        c = t % CYCLE
        rough = 0.0
        cap = None           # (文字, 位置)
        mxk, flash = "fish", 0.0
        self.sky(g, t, open_k)
        peng_draw = None
        if enter:
            x, top = self.swim(g, 0.0 + t * 0.2, t, fade=open_k)
            cap = ("北冥有鱼", "tl")
        elif c < LEAP0 or c >= 54.0:
            self.swim(g, c, t)
            if c < 17.0:
                cap = ("北冥有鱼", "tl") if c < 9.0 else ("其名为鲲", "tl")
        elif c < APEX:  # 摆尾蓄力，破水跃出
            x0 = self.kun_x(LEAP0)
            q = span(c, 19.5, APEX)
            if q <= 0:
                wig = int(c * 10) % 3
                self.kun(g, x0 + math.sin(c * 20) * 0.6, WL + 6, t, i=wig)
                if int(c * 8) % 2 == 0:
                    self.sparks.burst(x0 - 22, WL, 1, 10, up=8, life=0.4, gravity=40)
            else:
                xx = lerp(x0, 66, q)
                yy = lerp(WL + 6, 5, ease_out(q))
                up = q < 0.75
                pad = KUN_UP[0].pad if up else 0
                self.kun(g, xx, yy - pad, t, i=int(t * 6) % 3, up=up)
                if q < 0.25:
                    pix.blit(g, SPLASH[min(int(q * 12), 2)], x0 - 5, WL - 4)
                if abs(c - 19.5) < dt * 1.5:
                    self.sparks.burst(x0, WL, 24, 40, up=30, life=1.0, gravity=60)
                    pix.shake(g, t, 1.0)
        elif c < 38.0:  # 化鹏、展翼、水击三千里
            k = c - APEX
            if k < 0.25:
                pix.flash(g)
                mxk, flash = "ring", 1.0
            pop = ease_out_back(span(k, 0.0, 0.8))
            fr = int(k / 0.35) % 4 if k < 3 else int((k - 3) / 0.45) % 4
            spr = PENG[fr]
            bob = (2 if fr == 0 else (-1 if fr == 2 else 0))
            cx, cy = 64, 24 + bob
            if pop < 1:
                s2 = pix.stretch(spr, max(pop, 0.1), max(pop, 0.1))
                pix.blit(g, s2, cx - s2.w / 2, cy - spr.anchor[1] * pop)
            else:
                peng_draw = (spr, cx, cy)
            if k < 1.2:  # 光圈荡开
                r = k * 60
                for j in range(24):
                    a = j * math.pi / 12
                    g.px(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.7)
            # 每扇一下（下扇帧）海面溅一排水花
            if fr == 2 and self.flap_last != 2 and k > 1:
                for x in range(8, 128, 16):
                    self.sparks.burst(x + (t * 7) % 8, WL + 1, 3, 18, up=22, life=0.7, gravity=70)
            self.flap_last = fr
            rough = 1.0
            mxk = "bird" if k > 0.6 else "ring"
            if k > 0.6:
                cap = ("化而为鸟", "bc") if k < 5.5 else ("其翼若垂天之云", "bc")
        elif c < 50.0:  # 盘旋上升，越来越小
            k = c - 38.0
            q = k / 12.0
            ang = k * 1.6
            cx = 64 + math.sin(ang) * lerp(16, 5, q)
            cy = lerp(24, -6, ease_in(q)) + math.cos(ang) * 3
            if k < 3.0:
                spr = PENG[int(k / 0.45) % 4]
            elif k < 6.5:
                spr = PENG_M[int(k / 0.3) % 4]
            elif k < 10.0:
                spr = PENG_S[int(k / 0.2) % 4]
            else:
                spr = None
                g.d.rectangle((cx - 1, cy, cx, cy), fill=1)
            if spr is not None:
                peng_draw = (spr, cx, cy)
            rough = clamp(1 - k / 4)
            mxk = "bird"
            cap = ("抟扶摇而上", "bc")
        else:  # 50–54：坠海、水柱、水纹
            k = c - 50.0
            if k < 2.5:
                y = lerp(-2, WL, ease_in(span(k, 0.8, 2.5)))
                if k > 0.8:
                    g.d.rectangle((FALL_X, y - 2, FALL_X + 1, y), fill=1)
                    g.px(FALL_X, y - 5), g.px(FALL_X + 1, y - 8)
                elif int(k * 6) % 2:
                    g.px(FALL_X, 0)
                mxk = "dot"
            else:
                kk = k - 2.5
                if kk < 1.2:  # 水柱冲起又落下
                    hgt = math.sin(span(kk, 0, 1.2) * math.pi)
                    s2 = pix.stretch(COLUMN, 1.0, max(0.2, hgt * 2.0))
                    pix.blit(g, s2, FALL_X - s2.w / 2 + 1, WL - s2.h + 2)
                if abs(kk) < dt * 1.5:
                    self.sparks.burst(FALL_X, WL - 2, 26, 40, up=35, life=1.1, gravity=70)
                    mxk, flash = "ring", 1.0
                if kk < 0.4:
                    pix.shake(g, t, 1.5)
                for j in range(3):  # 一圈圈水纹（虚线椭圆）
                    r = (kk - j * 0.6) * 18
                    if 2 < r < 46:
                        n = int(r * 1.2) + 8
                        for i2 in range(n):
                            a = i2 * 2 * math.pi / n
                            g.px(FALL_X + math.cos(a) * r, WL + 4 + math.sin(a) * r * 0.24)
                rough = 1 - span(kk, 0, 1.5)
                mxk = "ring" if kk < 0.8 else "fish"
        self.sea(g, t, open_k, rough)
        if peng_draw:
            spr, cx, cy = peng_draw
            pix.blit(g, spr, cx - spr.anchor[0], cy - spr.anchor[1])
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 点阵
        if mxk == "fish":
            mx_art(g, MX_FISH[int(t * 3) % 2])
            g.mx[7, :] = [(i + int(t * 2)) % 3 == 0 for i in range(8)]
        elif mxk == "bird":
            fr = int(t / 0.4) % 4
            mx_art(g, MX_BIRD[fr])
        elif mxk == "dot":
            g.mx_set(3, min(int((c - 50.8) / 1.7 * 7), 7) if c > 50.8 else 0)
            g.mx[7, :] = True
        else:
            r = (c % 1.0) * 6
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.7:
                        g.mx[yy, xx] = True
            g.mx[3:5, 3:5] = True
        if flash:
            g.mx_level = 8
        return cap

    def caption(self, g: Gfx, cap):
        if not cap:
            return
        s, pos = cap
        if pos == "tl":
            label(g, 4, 3, s)
        else:
            label(g, 64, 51, s, align="center")

    def enter(self, g: Gfx, t: float):
        k = ease_out(span(t, 0, 2.2))
        cap = self.scene(g, t, open_k=k, enter=True)
        if t > 1.2:
            self.caption(g, cap)

    def hold(self, g: Gfx, t: float):
        cap = self.scene(g, t + 0.6)
        self.caption(g, cap)

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + 0.6 + t
        self.scene(g, tt)
        k = ease_in(span(t, 0, 1.1))
        top = int(WL * k)
        bot = int(WL + (64 - WL) * (1 - k))
        g.d.rectangle((0, 0, 127, top), fill=0)
        g.d.rectangle((0, bot, 127, 63), fill=0)
        g.d.line((0, WL, 127, WL), fill=1)
