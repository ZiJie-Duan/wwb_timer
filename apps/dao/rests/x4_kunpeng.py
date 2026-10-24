"""鲲鹏：北冥有鱼，化而为鸟。

依据：《庄子·逍遥游》“北冥有鱼，其名为鲲。鲲之大，不知其几千里也。化而为鸟，其名为鹏。鹏之背，不知其几千里也；
怒而飞，其翼若垂天之云。……鹏之徙于南冥也，水击三千里，抟扶摇而上者九万里。”
入场：海平线从中间拉开，浪纹铺满，巨大的鱼影从水下缓缓游进来。
持续：一轮 64 秒——
      鲲在水下游（水下部分是淡淡的影子），脊背不时拱出水面，翻起浪花；
      跃出海面，在半空一闪化成鹏，巨翼几乎横跨全屏，慢慢扇动，下面的海浪被拍得高高溅起（水击三千里）；
      鹏盘旋上升，越飞越小，消失在高空（抟扶摇而上者九万里）；
      一会儿一个小黑点从高空直坠入海，大浪一圈，水下又是那条鲲。
      每段配一句《逍遥游》原文。
收场：鱼影沉入深海，海面合拢成一条线。
"""
from __future__ import annotations

import math

from PIL import Image

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Bake, mx_sprite

WL = 34            # 海平面
CYCLE = 64.0


def _kun() -> Sprite:
    """鲲（朝右的巨鱼）：宽 64，高 26"""
    b = Bake(64, 26)
    body = [(58, 12), (54, 7), (44, 4), (30, 4), (18, 7), (10, 11), (8, 13), (10, 15), (18, 18), (30, 21), (44, 21),
            (54, 18)]
    b.poly([(10, 13), (0, 2), (4, 13), (0, 24)], 0.0)         # 尾鳍
    b.line([(3, 6), (8, 12)])
    b.line([(3, 20), (8, 14)])
    b.poly([(28, 5), (34, 0), (42, 4)], 0.0)                  # 背鳍
    b.poly(body, 0.0)
    b.poly([(38, 17), (34, 25), (30, 19)], 0.0)               # 胸鳍
    b.line([(50, 6), (47, 12), (50, 19)])                    # 鳃
    b.ellipse((53, 9, 56, 12), 1.0)                          # 眼
    b.point(54, 10, 0)
    b.line([(59, 14), (62, 13)])                             # 口
    for x in range(18, 46, 6):                               # 鳞纹
        for y in (9, 14):
            b.line([(x, y), (x + 2, y + 2), (x + 4, y)])
    b.line([(12, 13), (46, 13)])
    return b.sprite()


KUN = _kun()


def _rot(spr: Sprite, deg: float) -> Sprite:
    on = Image.fromarray(spr.on).rotate(deg, expand=True, resample=Image.NEAREST)
    mask = Image.fromarray(spr.mask).rotate(deg, expand=True, resample=Image.NEAREST)
    import numpy as np
    return Sprite(on=np.array(on, dtype=bool), mask=np.array(mask, dtype=bool))


KUN_UP = [KUN] + [_rot(KUN, d) for d in (20, 40, 60)]

MX_FISH = """
........
........
#..####.
.######.
.#######
#..####.
........
........
"""
MX_UP = """
#......#
##....##
.##..##.
..####..
...##...
...##...
..#..#..
........
"""
MX_DOWN = """
........
........
...##...
.######.
#.####.#
#..##..#
..#..#..
........
"""


def peng(g: Gfx, x: float, y: float, s: float, flap: float):
    """鹏（正面迎着看）：巨翼横展。(x, y) 身体中心，s 缩放（1 = 翼展约 120），flap 扇翅相位"""
    w = math.sin(flap)
    half = 60 * s
    if half < 2:
        g.px(x, y)
        g.px(x - 1, y - (1 if w > 0 else 0))
        g.px(x + 1, y - (1 if w > 0 else 0))
        return
    for side in (-1, 1):
        sh = (x + side * 4 * s, y - 2 * s)
        mid = (x + side * half * 0.5, y - 2 * s - w * 14 * s)
        tip = (x + side * half, y + 2 * s - w * 22 * s)
        # 前缘（翼弯）与后缘（羽毛锯齿）
        lead = [sh, (x + side * half * 0.25, y - 6 * s - w * 7 * s), mid, tip]
        trail = []
        n = max(3, int(9 * s))
        for i in range(n + 1):
            u = i / n
            px = lerp(tip[0], x + side * 5 * s, u)
            base = lerp(tip[1], y + 4 * s, u) + math.sin(u * math.pi) * (3 - w * 4) * s
            trail.append((px, base + (3 * s if i % 2 else 0)))
        g.d.polygon(lead + trail, fill=0, outline=1)
        if s > 0.5:   # 翼上的覆羽纹
            for k in (0.35, 0.6):
                a = (lerp(sh[0], tip[0], k), lerp(sh[1], tip[1], k) + 1 + 3 * s)
                b = (lerp(sh[0], tip[0], k + 0.12), lerp(sh[1], tip[1], k + 0.12) + 1 + 3 * s - w * 2 * s)
                g.d.line((a, b), fill=1)
    # 身体、头、尾
    g.d.ellipse((x - 5 * s, y - 5 * s, x + 5 * s, y + 9 * s), fill=0, outline=1)
    g.d.ellipse((x - 3 * s, y - 10 * s, x + 3 * s, y - 4 * s), fill=0, outline=1)
    g.d.polygon([(x - 1 * s, y - 6 * s), (x + 1 * s, y - 6 * s), (x, y - 3 * s)], fill=1)   # 喙
    if s > 0.4:
        g.px(x - 2 * s, y - 8 * s)
        g.px(x + 2 * s, y - 8 * s)
    g.d.polygon([(x - 3 * s, y + 8 * s), (x - 8 * s, y + 16 * s), (x, y + 13 * s), (x + 8 * s, y + 16 * s),
                 (x + 3 * s, y + 8 * s)], fill=0, outline=1)


@register
class KunPeng(Rest):
    id = "x4.kunpeng"
    name = "鲲鹏"
    desc = "北冥巨鲲在水下游、脊背拱出海面；跃起化为大鹏，巨翼垂天、拍起滔天浪，扶摇而上，再坠海化鲲"
    T = {"enter": 3.2, "exit": 1.3}

    def setup(self):
        self.phase0 = self.rng.choice((0.0, 8.0))

    # ------------------------------------------------------------ 海

    def sea(self, g: Gfx, t: float, storm: float = 0.0, open_: float = 1.0):
        hw = 64 * open_
        g.d.line((64 - hw, WL, 64 + hw - 1, WL), fill=1)
        if open_ < 1:
            return
        self.waves(g, t, storm)
        if storm > 0:   # 水击三千里：一簇簇浪花溅起（水珠抛物线）
            for i in range(9):
                x0 = 6 + i * 14 + rand(i, self.seed) * 6
                ph = (t * 1.3 + rand(i, 2)) % 1
                h = storm * (8 + 10 * rand(i, 5))
                for j in range(5):
                    dx = (j - 2) * 2.2 * ph * 3
                    y = WL - 1 - h * (4 * ph * (1 - ph)) * (1 - abs(j - 2) * 0.25)
                    g.px(x0 + dx, y)
                g.d.arc((x0 - 4, WL - 3 * storm, x0 + 4, WL + 1), 180, 360, fill=1)
        for i in range(2):   # 天上两笔云
            x = (rand(i, self.seed + 9) * 140 + t * 1.2) % 160 - 20
            y = 6 + i * 9
            g.d.line((x, y, x + 18, y), fill=1)
            g.d.line((x + 6, y - 2, x + 14, y - 2), fill=1)

    def waves(self, g: Gfx, t: float, storm: float = 0.0):
        for row, (y, sp, gap) in enumerate(((WL + 5, 3, 16), (WL + 12, 5, 13), (WL + 21, 8, 11))):
            off = (t * sp + row * 7) % gap
            for i in range(-1, 128 // gap + 2):
                x = i * gap + off + (row % 2) * gap / 2
                amp = 1 + storm * (4 - row) * (0.5 + 0.5 * math.sin(t * 5 + i))
                g.d.arc((x - 3, y - amp, x + 3, y + amp), 200, 340, fill=1)

    def kun(self, g: Gfx, t: float, x: float, depth: float, surf: float = 0.0):
        """鲲：depth = 鱼背在海面以下几像素（负数 = 拱出水面）。水下部分淡成影子"""
        y = WL + depth
        g.blit(KUN, x, y)
        g.fade(0.6, (0, WL + 1, 128, 64))
        self.waves(g, t)
        if depth < 1:   # 拱出水面：浪花
            for i in range(6):
                px = x + 24 + i * 4 + math.sin(t * 6 + i) * 1
                g.px(px, WL - 1 - (i % 3))

    # ------------------------------------------------------------ 一轮

    def frame(self, g: Gfx, t: float):
        k = (t + self.phase0) % CYCLE
        n = int((t + self.phase0) // CYCLE)
        text, tk = None, 0.0
        mx, mx_level = MX_FISH, 1
        if k < 26.0:                       # 鲲在水下游
            self.sea(g, t)
            x = 30 + math.sin(k * 0.12) * 16
            arch = math.sin(k * 0.5)
            depth = 5 - max(0.0, arch) * 7      # 偶尔拱出水面
            self.kun(g, t, x, depth)
            text, tk = "北冥有鱼，其名为鲲", k
        elif k < 31.0:                     # 跃起、化鹏
            self.sea(g, t, storm=span(k, 28.5, 29.5) * 0.5)
            j = k - 26.0
            if j < 2.6:
                p = j / 2.6
                spr = KUN_UP[min(3, int(p * 4))]
                cx = lerp(50, 64, p)
                cy = lerp(WL + 14, 10, ease_out(p))
                g.blit(spr, cx - spr.w / 2, cy - spr.h / 2)
                g.fade(0.6, (0, WL + 1, 128, 64))
                self.waves(g, t)
                if p > 0.3:   # 出水的水花
                    for i in range(10):
                        a = math.pi * (0.15 + 0.7 * rand(i, 2))
                        r = (p - 0.3) * 40 * (0.5 + rand(i, 3))
                        g.px(56 + math.cos(a) * r, WL - math.sin(a) * r * 0.8 + (p - 0.3) ** 2 * 60)
            else:   # 一闪：光圈，鱼变鸟
                q = (j - 2.6) / 2.4
                if q < 0.25:
                    for r in (6, 11, 16):
                        ring(g, 64, 14, r + q * 30, 2, q * 4)
                    g.d.ellipse((58, 8, 70, 20), fill=1)
                    mx_level = 8
                else:
                    peng(g, 64, lerp(12, 22, q), ease_out_back_s(span(q, 0.25, 1.0)), j * 3)
            text, tk = "化而为鸟，其名为鹏", k - 27.0
            mx = MX_UP
        elif k < 42.0:                     # 怒而飞，其翼若垂天之云；水击三千里
            j = k - 31.0
            storm = 1 - span(j, 8, 11)
            self.sea(g, t, storm=storm)
            flap = j * 2.6
            peng(g, 64, 22 + math.sin(flap) * 2, 1.0, flap)
            text, tk = ("其翼若垂天之云", j) if j < 6 else ("水击三千里", j - 6)
            mx = MX_UP if math.sin(flap) > 0 else MX_DOWN
        elif k < 52.0:                     # 抟扶摇而上者九万里
            j = k - 42.0
            self.sea(g, t)
            p = ease_in_out(span(j, 0, 7))
            s = lerp(1.0, 0.02, p)
            x = 64 + math.sin(j * 0.9) * 30 * p        # 盘旋着上升
            y = lerp(22, 4, p)
            flap = j * lerp(2.6, 6, p)
            peng(g, x, y, s, flap)
            text, tk = "抟扶摇而上者九万里", j
            mx = MX_UP if math.sin(flap) > 0 else MX_DOWN
        else:                              # 坠海、化鲲
            j = k - 52.0
            self.sea(g, t)
            if j < 1.6:
                p = ease_in(j / 1.6)
                x = 64 + math.sin(10 * 0.9) * 30
                y = lerp(4, WL, p)
                g.d.line((x, y - 3 - p * 5, x, y), fill=1)
                g.px(x - 1, y - 1)
                g.px(x + 1, y - 1)
            elif j < 5.0:                  # 大浪一圈
                q = (j - 1.6) / 3.4
                x = 64 + math.sin(10 * 0.9) * 30
                for r in (q * 50, q * 50 - 10):
                    if r > 0:
                        g.d.arc((x - r, WL - r * 0.15, x + r, WL + r * 0.15), 0, 360, fill=1)
                if q < 0.5:   # 水柱
                    h = math.sin(q / 0.5 * math.pi) * 22
                    g.d.line((x - 2, WL, x - 3, WL - h * 0.8), fill=1)
                    g.d.line((x, WL, x, WL - h), fill=1)
                    g.d.line((x + 2, WL, x + 3, WL - h * 0.8), fill=1)
                mx_level = 2
            else:                          # 水下又是鲲（接下一轮的开头）
                q = ease_out(span(j, 5.0, 12.0))
                depth = lerp(24, 5, q)
                x = 30 + (1 - q) * 20
                self.kun(g, t, x, depth)
            mx = MX_FISH
        if text:
            self.caption(g, text, tk)
        mx_sprite(g, mx)
        if mx is MX_FISH:
            g.mx[7, :] = [bool((i + int(t * 2)) % 3) for i in range(8)]
        g.mx_level = mx_level

    def caption(self, g: Gfx, text: str, tk: float):
        """字幕：海面下方，衬一块黑底"""
        from ..engine.gfx import text_width
        w = text_width(text)
        g.d.rectangle((64 - w / 2 - 2, 51, 64 + w / 2 + 1, 63), fill=0)
        typewriter(g, 64, 52, text, tk, cps=4, align="center")

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        op = ease_out(span(t, 0, 1.0))
        self.sea(g, t - T, open_=op)
        if op >= 1:
            k = self.phase0
            x0 = 30 + math.sin(k * 0.12) * 16
            depth = 5 - max(0.0, math.sin(k * 0.5)) * 7
            p = ease_out(span(t, 1.0, T))
            self.kun(g, t, lerp(-70, x0, p), lerp(14, depth, p))
            self.caption(g, "北冥有鱼，其名为鲲", (t - 1.6) * 0.6)
        mx_sprite(g, MX_FISH, dx=round((1 - op) * -8))
        g.mx[7, :] = [bool((i + int(t * 2)) % 3) for i in range(8)]

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        self.frame(g, t0)
        p = ease_in(span(t, 0, T))
        # 海面合拢：上下往中线压
        top = int(WL * p) - 1
        bot = int(64 - (64 - WL) * p) + 1
        if top >= 0:
            g.d.rectangle((0, 0, 127, top), fill=0)
        if bot <= 63:
            g.d.rectangle((0, bot, 127, 63), fill=0)
        g.d.line((64 - 64 * (1 - p), WL, 64 + 64 * (1 - p), WL), fill=1)
        g.fade(1 - span(t, T * 0.6, T))
        if p > 0.5:
            g.mx[:4, :] = False


def ease_out_back_s(p: float) -> float:
    from ..engine.anim import ease_out_back
    return ease_out_back(p, 1.2)
