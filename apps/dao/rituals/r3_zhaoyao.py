"""照妖镜：小道士高举一面铜镜，镜光照向右边的“客人”——光照到的那一截显出原形，其余仍是伪装。

葛洪《抱朴子·登涉》：“万物之老者，其精悉能假托人形……唯不能于镜中易其真形耳。
是以古之入山道士，皆以明镜径九寸已上，悬于背后，则老魅不敢近人。”

入场：一位“客人”从右边走进来（书生、女子或老翁，按种子轮换），右上写“书生？”；小道士从左边上来，
      举起宝镜，镜面一闪，射出镜光。
持续：镜光是一束光锥，缓缓上下扫；光照到的那一截显出原形（书生是狐：尖耳、吊梢眼、大尾巴；女子是白骨；
      老翁是蛇），光扫过时客人一哆嗦。镜面不时有一道斜光扫过。一轮 600 秒，镜光从一线逐渐张开，
      越到后面原形露得越多；每隔十几秒镜子“嗡”地一亮，光锥一涨。
      续：镜光大张、原形毕露（右上写“狐妖！”），妖物惊叫一声、一溜烟逃出画外，下一位客人走进来。
中断：镜子侧过去（变成一条窄边），镜光熄灭，写“收镜”。  恢复：镜面转回，一闪，镜光重开。
圆满：镜光张满，原形自下而上全显出来，镜子放光，题“现出原形”；妖物发抖、化一缕烟散尽。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_out, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r3_kit import (FLOOR, Clock, banner, banner_text, crossed, floor, label, mx_ring, pose_arm, put,
                     rays, round_of, sparkle)

DX = 22
VX = 98                       # 客人站位
CYCLE = 600.0
RENEW = 7.0
GUISE = ["书生", "女子", "老翁"]
TRUE = ["狐妖", "白骨精", "蛇妖"]


def _spr(p: Part, ax=9, ay=31) -> Sprite:
    s = Sprite(on=np.array(p.on, bool), mask=np.array(p.mk, bool))
    s.anchor = (ax, ay)
    s.pts = {}
    return s


# ---------------------------------------------------------------- 伪装（Q 版，大头，朝左）

def _scholar() -> Sprite:
    """书生：方巾、圆脸、交领长衫、手里一把折扇"""
    p = Part(20, 32)
    p.shape("polygon", [(5, 17), (13, 17), (16, 31), (2, 31)], fill=1)          # 长衫
    p.d.line((9, 17, 6, 22), fill=0), p.d.line((9, 17, 11, 21), fill=0)          # 交领
    p.d.line((3, 26, 15, 26), fill=0)                                            # 腰带
    p.dither([(12, 22), (16, 31), (12, 31)], 0.5, 0)
    p.shape("ellipse", (2, 4, 16, 17), fill=1)                                   # 头
    p.d.chord((3, 5, 15, 14), 180, 360, fill=0)                                  # 头发
    p.d.ellipse((2, 4, 16, 17), outline=1)
    p.shape("rectangle", (3, 1, 14, 6), fill=1)                                  # 方巾
    p.d.line((3, 5, 14, 5), fill=0)
    p.shape("polygon", [(13, 3), (18, 7), (17, 10), (14, 6)], fill=1)            # 巾带
    for x in (5, 9):                                                             # 眼
        p.d.rectangle((x, 10, x + 1, 12), fill=0)
        p.px(x, 10, 1)
    p.d.line((7, 14, 8, 14), fill=0)
    p.shape("polygon", [(0, 18), (5, 20), (5, 23), (1, 23)], fill=1)              # 扇（展开）
    for x in (1, 2, 3):
        p.px(x, 21, 0)
    return _spr(p)


def _lady() -> Sprite:
    """女子：高髻插簪、长发垂背、长裙曳地、长袖"""
    p = Part(20, 32)
    p.shape("polygon", [(5, 17), (13, 17), (17, 31), (1, 31)], fill=1)           # 长裙
    p.d.line((4, 23, 14, 23), fill=0)                                            # 腰带
    p.d.line((9, 23, 8, 29), fill=0)
    p.dither([(12, 24), (17, 31), (13, 31)], 0.5, 0)
    p.shape("polygon", [(13, 9), (17, 14), (16, 24), (13, 22)], fill=0)          # 垂在背后的长发
    p.d.polygon([(13, 9), (17, 14), (16, 24), (13, 22)], outline=1)
    p.shape("ellipse", (2, 4, 16, 17), fill=1)
    p.d.chord((3, 5, 15, 13), 180, 360, fill=0)                                  # 刘海
    p.d.polygon([(12, 7), (16, 9), (16, 14), (13, 12)], fill=0)                  # 鬓发
    p.d.ellipse((2, 4, 16, 17), outline=1)
    p.d.line((5, 6, 8, 5), fill=1)                                               # 发丝高光
    p.shape("ellipse", (6, 0, 13, 6), fill=0)                                    # 高髻
    p.d.ellipse((6, 0, 13, 6), outline=1)
    p.shape("line", (11, 1, 17, 0), fill=1)                                      # 簪
    p.shape("rectangle", (16, 0, 18, 2), fill=1)                                 # 簪头小花
    p.px(17, 1, 0)
    for x in (5, 9):
        p.d.rectangle((x, 10, x + 1, 12), fill=0)
        p.px(x, 10, 1)
        p.px(x - 1, 10, 0)                                                       # 睫毛
    p.px(4, 13, 0), p.px(11, 13, 0)                                              # 腮红
    p.px(7, 14, 0)
    p.shape("polygon", [(2, 18), (6, 18), (5, 25), (1, 25)], fill=1)             # 长袖
    p.d.line((1, 24, 5, 24), fill=0)
    return _spr(p)


def _elder() -> Sprite:
    """老翁：秃顶小髻、长白胡子、弓背、拄拐"""
    p = Part(20, 32)
    p.shape("polygon", [(6, 17), (14, 16), (16, 31), (3, 31)], fill=1)
    p.d.line((4, 26, 15, 26), fill=0)
    p.dither([(12, 21), (16, 31), (12, 31)], 0.5, 0)
    p.shape("ellipse", (3, 5, 16, 17), fill=1)
    p.shape("ellipse", (9, 2, 13, 6), fill=1)                                    # 小髻
    p.d.arc((4, 7, 15, 15), 200, 340, fill=0)                                    # 额纹
    for x in (6, 10):                                                            # 眯眼
        p.d.line((x, 11, x + 1, 11), fill=0)
    p.d.line((5, 9, 7, 9), fill=0), p.d.line((9, 9, 11, 9), fill=0)              # 长眉
    p.shape("polygon", [(4, 13), (12, 13), (10, 22), (7, 25), (5, 20)], fill=1)  # 白胡子
    p.d.line((4, 13, 12, 13), fill=0)                                            # 八字须下的嘴缝
    p.d.line((5, 14, 7, 24), fill=0), p.d.line((11, 14, 9, 22), fill=0)          # 胡子两边
    p.px(8, 16, 0), p.px(8, 19, 0)
    p.px(12, 10, 0), p.px(13, 11, 0)                                             # 皱纹
    p.shape("line", (1, 31, 3, 15), fill=1)                                      # 拐杖
    p.shape("line", (3, 15, 5, 14), fill=1)
    p.shape("rectangle", (3, 18, 5, 20), fill=1)                                 # 握拐的手
    return _spr(p)


# ---------------------------------------------------------------- 原形

def _fox() -> Sprite:
    """狐：尖耳、尖嘴朝左、吊梢眼、胸前一撮毛、身后一条大尾巴翘起来"""
    p = Part(20, 32)
    p.shape("polygon", [(13, 30), (19, 22), (19, 12), (16, 9), (17, 17), (14, 25)], fill=1)   # 大尾巴
    p.d.line((18, 13, 18, 20), fill=0)
    p.dither([(14, 24), (19, 20), (19, 30), (13, 30)], 0.5, 0)
    p.shape("polygon", [(5, 17), (13, 17), (15, 31), (3, 31)], fill=1)          # 身子
    for i, x in enumerate(range(6, 12, 2)):                                     # 胸毛（锯齿）
        p.px(x, 20 + i % 2, 0), p.px(x + 1, 21 - i % 2, 0)
    p.d.line((6, 31, 6, 28), fill=0), p.d.line((11, 31, 11, 28), fill=0)
    p.shape("ellipse", (4, 6, 16, 17), fill=1)                                   # 头
    p.shape("polygon", [(5, 8), (6, 0), (9, 6)], fill=1)                         # 尖耳
    p.shape("polygon", [(11, 6), (14, 0), (15, 8)], fill=1)
    p.px(6, 4, 0), p.px(14, 4, 0)
    p.shape("polygon", [(5, 11), (0, 14), (5, 15)], fill=1)                      # 尖嘴
    p.px(0, 14, 0), p.px(1, 13, 1)
    p.d.line((5, 10, 8, 11), fill=0)                                             # 吊梢眼
    p.d.line((10, 11, 13, 9), fill=0)
    p.px(7, 11, 0), p.px(11, 11, 0)
    p.d.line((3, 15, 6, 16), fill=0)                                             # 嘴角
    return _spr(p)


def _bones() -> Sprite:
    """白骨：大头骷髅（黑眼窝、鼻孔、一排牙），脊梁、三根肋骨、盆骨、腿骨"""
    p = Part(20, 32)
    p.shape("ellipse", (3, 3, 16, 16), fill=1)                                   # 颅骨
    p.shape("rectangle", (5, 14, 13, 17), fill=1)                                # 下颌
    p.d.ellipse((4, 7, 8, 11), fill=0), p.d.ellipse((10, 7, 14, 11), fill=0)     # 眼窝
    p.px(6, 9, 1), p.px(12, 9, 1)
    p.d.polygon([(9, 12), (8, 14), (10, 14)], fill=0)                            # 鼻孔
    for x in range(5, 14, 2):                                                    # 牙
        p.px(x, 16, 0)
    p.shape("line", (9, 18, 9, 27), fill=1)                                      # 脊梁
    for i, y in enumerate((19, 22, 25)):                                         # 肋骨
        w = 5 - i
        p.shape("line", (9 - w, y + 1, 9 + w, y + 1), fill=1)
        p.px(9 - w, y + 2), p.px(9 + w, y + 2)
    p.shape("line", (4, 19, 2, 26), fill=1), p.shape("rectangle", (1, 26, 3, 27), fill=1)   # 臂骨
    p.shape("line", (14, 19, 16, 25), fill=1)
    p.shape("polygon", [(6, 27), (12, 27), (11, 29), (7, 29)], fill=1)          # 盆骨
    p.shape("line", (7, 29, 6, 31), fill=1), p.shape("line", (11, 29, 12, 31), fill=1)
    p.shape("rectangle", (4, 31, 6, 31), fill=1), p.shape("rectangle", (12, 31, 14, 31), fill=1)
    return _spr(p)


def _snake() -> Sprite:
    """蛇：昂起的头（竖瞳、信子朝左），S 形的脖子，底下盘成三圈，背上鳞纹"""
    p = Part(20, 32)
    for i, (x0, y0, x1, y1) in enumerate(((2, 25, 18, 31), (4, 20, 16, 27), (6, 16, 14, 22))):   # 盘起的身子
        p.shape("ellipse", (x0, y0, x1, y1), fill=1)
        p.d.arc((x0 + 1, y0 + 1, x1 - 1, y1 - 1), 200, 340, fill=0)
    for x in range(4, 17, 3):                                                     # 鳞纹
        p.px(x, 29, 0), p.px(x + 1, 28, 0)
    p.shape("polygon", [(9, 17), (12, 17), (12, 10), (9, 10)], fill=1)          # 脖子
    p.px(10, 13, 0), p.px(11, 15, 0)
    p.shape("ellipse", (4, 3, 14, 11), fill=1)                                   # 头
    p.shape("polygon", [(4, 6), (1, 8), (4, 10)], fill=1)
    p.d.rectangle((7, 5, 8, 7), fill=0)                                          # 竖瞳
    p.px(8, 5, 1)
    p.d.line((3, 9, 7, 9), fill=0)                                               # 嘴
    p.shape("line", (0, 9, -1, 9), fill=1)
    p.px(0, 9), p.px(0, 10), p.px(1, 9)                                          # 信子
    return _spr(p)


_SPR: dict = {}


def guise(i: int) -> Sprite:
    k = ("g", i)
    if k not in _SPR:
        _SPR[k] = (_scholar, _lady, _elder)[i]()
    return _SPR[k]


def truth(i: int) -> Sprite:
    k = ("t", i)
    if k not in _SPR:
        _SPR[k] = (_fox, _bones, _snake)[i]()
    return _SPR[k]


# ---------------------------------------------------------------- 镜子

def _mirror(w: int) -> Sprite:
    """铜镜（侧着一点，宽 w）：外圈纹饰（暗点一圈）、镜面、下面的柄与穗"""
    p = Part(max(w, 3) + 2, 22)
    h = 15
    p.shape("ellipse", (0, 0, w, h), fill=1)
    if w >= 5:
        p.d.ellipse((1, 1, w - 1, h - 1), outline=0)
        for a in range(0, 360, 40):   # 镜背纹饰（外圈一串亮点）
            x = w / 2 + math.cos(math.radians(a)) * (w / 2 - 1)
            y = h / 2 + math.sin(math.radians(a)) * (h / 2 - 1)
            p.px(int(round(x)), int(round(y)), 1)
        p.d.ellipse((2, 2, w - 2, h - 2), fill=1)
        p.d.line((w / 2 - 1, 3, w / 2 - 2, 6), fill=0)   # 镜面一道反光（暗线衬）
    p.shape("rectangle", (w // 2 - 1, h, w // 2 + 1, h + 5), fill=1)       # 柄
    p.px(w // 2, h + 2, 0)
    s = Sprite(on=np.array(p.on, bool), mask=np.array(p.mk, bool))
    s.anchor = (w // 2, h + 3)
    s.pts = {"c": (w // 2, h // 2), "face": (w, h // 2)}
    return s


def mirror_spr(w: int) -> Sprite:
    k = ("m", w)
    if k not in _SPR:
        _SPR[k] = _mirror(w)
    return _SPR[k]


MX_MIRROR = """
.###....
#...#...
#...#...
#...#...
.###....
..#.....
..#.....
"""


@register
class ZhaoyaoRitual(Ritual):
    id = "r3.zhaoyao"
    name = "照妖镜"
    desc = "小道士高举铜镜照向来客，光照到的那一截显出原形（狐、白骨、蛇）；镜光随计时越张越开，原形越露越多"
    T = {"enter": 6.0, "interrupt": 1.4, "resume": 1.6, "complete": 6.0}
    CYCLE = CYCLE

    def setup(self):
        self.base = self.seed % 3
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.clock = Clock()

    # ------------------------------------------------------------ 公用

    def who(self, e: float) -> int:
        return (self.base + int(e // CYCLE)) % 3

    def holder(self, g: Gfx, t: float, w: int = 9, face="normal", glow=False) -> tuple[int, int]:
        """小道士高举铜镜；返回镜面中心"""
        out = {}

        def prop(g2, h):
            out.update(put(g2, mirror_spr(w), h[0] + 1, h[1] + 1))
        pose_arm(g, DX, "reach", t, "fist", face=face, prop=prop)
        cx, cy = out["c"]
        if glow:
            rays(g, cx, cy, 10, 15, 10, rot=t, dash=2)
        return cx, cy

    def visitor(self, g: Gfx, i: int, x: float, band=None, shiver: float = 0.0, t: float = 0.0, full: float = 0.0):
        """客人：伪装；band=(y0, y1) 这一截换成原形；full ∈ [0,1] 原形从下往上显出的比例"""
        j = int(round(math.sin(t * 50) * shiver))
        gs, ts = guise(i), truth(i)
        ax, ay = gs.anchor
        x0, y0 = int(round(x)) - ax + j, FLOOR - ay
        pix.blit(g, gs, x0, y0)
        rows = np.zeros(gs.h, bool)
        if band:
            a, b = int(band[0]) - y0, int(band[1]) - y0
            rows[max(a, 0):max(min(b, gs.h), 0)] = True
        if full > 0:
            rows[int(round(gs.h * (1 - full))):] = True
        if rows.any():
            # 原形那几行：先把伪装擦掉，再贴原形（同一块范围）
            a = g.array()
            H, W = a.shape
            for yy in np.nonzero(rows)[0]:
                Y = y0 + yy
                if 0 <= Y < H:
                    xs = slice(max(x0, 0), min(x0 + gs.w, W))
                    a[Y, xs] = False
                    tr = ts.on[yy, max(0, -x0):max(0, -x0) + (xs.stop - xs.start)]
                    a[Y, xs.start:xs.start + len(tr)] |= tr
            g.put(a)
            ys = np.nonzero(rows)[0]   # 显形的上下沿：两道虚线
            for yy in (ys[0], ys[-1]):
                if 0 < yy < gs.h - 1:
                    pix.dotted(g, x0 - 2, y0 + yy, x0 + gs.w + 1, y0 + yy, 2, phase=int(t * 20))
        return x0, y0

    def beam(self, g: Gfx, src, ang: float, half: float, t: float):
        """镜光：一束从镜面射出的光锥（边线 + 里面几道流动的虚线）；返回在客人那里的上下范围"""
        cx, cy = src
        L = 128 - cx
        a0, a1 = math.radians(ang - half), math.radians(ang + half)
        for a in (a0, a1):
            g.d.line((cx + 3, cy, cx + math.cos(a) * L, cy + math.sin(a) * L), fill=1)
        for k in range(1, 4):
            a = a0 + (a1 - a0) * k / 4
            pix.dotted(g, cx + 6, cy, cx + math.cos(a) * L, cy + math.sin(a) * L, 3, phase=-int(t * 30) + k)
        d = VX - cx
        return cy + math.tan(a0) * d, cy + math.tan(a1) * d

    def fx(self, g: Gfx, dt: float):
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def mx(self, g: Gfx, ang: float, half: float, on: bool):
        g.mx_blit(MX_MIRROR)
        if on:
            for k in (-1, 0, 1):
                a = math.radians(ang + k * half)
                for r in range(1, 4):
                    g.mx_set(4 + int(round(math.cos(a) * r)), 2 + int(round(math.sin(a) * r * 1.5)))

    def stage(self, g: Gfx, t: float):
        floor(g)
        g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
        for x in (60, 70):   # 门框（客人从门外进来）
            pass

    def sweep(self, k: float, e: float):
        """镜光的指向与张角（k = 本轮秒数）"""
        half = lerp(2.5, 10.0, k / CYCLE)
        boost = max(0.0, 1 - abs((e % 14.0) - 7.0) / 0.6)   # 每 14 秒镜子一亮，光锥一涨
        ang = math.sin(e * 0.45) * 9 + 2
        return ang, half + boost * 4, boost

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        i = self.who(0)
        self.stage(g, t)
        vx = lerp(140, VX, ease_out(span(t, 0.0, 2.4)))
        if t <= 3.6:
            self.visitor(g, i, vx, t=t)
        if t < 2.6:
            x = lerp(-14, DX, ease_out(span(t, 0.6, 2.6)))
            if t > 0.6:
                h = daoshi(g, x, FLOOR, "walk", t)["hand"]
                put(g, mirror_spr(3), h[0], h[1] + 2)
        else:
            w = 3 + int(span(t, 2.6, 3.4) * 6)
            src = self.holder(g, t, w=w, face="wow" if t > 3.6 else "normal")
            if crossed(t, dt, 3.6):
                self.sparks.burst(src[0] + 3, src[1], 14, 30, life=0.5)
            if 3.6 <= t < 3.68:
                pix.flash(g)
            if t > 3.6:
                q = span(t, 3.6, 4.4)
                ang, half, _ = self.sweep(0, 0)
                y0, y1 = self.beam(g, src, ang, half * q, t)
                self.visitor(g, i, VX, band=(y0, y1), t=t, shiver=0.6)
        self.fx(g, dt)
        label(g, 125, 3, GUISE[i] + "？", align="right")
        self.mx(g, 0, 3, t > 3.6)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        if k >= CYCLE - RENEW:
            self.renew(g, k - (CYCLE - RENEW), t, e, dt)
            return
        i = self.who(e)
        self.stage(g, t)
        ang, half, boost = self.sweep(k, e)
        src = self.holder(g, e, face="wow" if boost > 0.5 else "normal")
        y0, y1 = self.beam(g, src, ang, half, e)
        face_y = FLOOR - 22
        shiver = 1.0 if y0 < face_y < y1 else 0.4
        self.visitor(g, i, VX, band=(y0, y1), t=e, shiver=shiver)
        if (e % 4.0) < 0.5:                   # 镜面斜光扫过
            q = (e % 4.0) / 0.5
            sparkle(g, src[0] - 2 + q * 4, src[1] - 5 + q * 10, 2)
        if boost > 0.9 and int(e * 30) % 3 == 0:
            self.sparks.burst(src[0] + 4, src[1], 2, 20, life=0.4, gravity=0)
        self.fx(g, dt)
        label(g, 125, 3, GUISE[i] + "？", align="right")
        self.mx(g, ang, half, True)

    def renew(self, g: Gfx, u: float, t: float, e: float, dt: float):
        """u ∈ [0, RENEW)：镜光大张、原形毕露 → 惊叫逃走 → 下一位客人进来"""
        i = self.who(e)
        nxt = (i + 1) % 3
        self.stage(g, t)
        if u < 4.6:
            open_ = span(u, 0.0, 0.8)
            src = self.holder(g, t, face="wow" if u < 3.0 else "happy", glow=u < 2.4)
            ang, half = 2.0, lerp(10, 26, open_)
            if u < 2.6:
                y0, y1 = self.beam(g, src, ang, half, t)
                self.visitor(g, i, VX, band=(y0, y1), t=t, shiver=2.0)
                if crossed(u, dt, 0.8):
                    self.sparks.burst(VX, FLOOR - 20, 20, 40, life=0.6)
                if 0.8 <= u < 0.88:
                    pix.flash(g)
                if 0.8 <= u < 1.4:   # 惊叫：头上一个大“！”
                    g.d.rectangle((VX + 9, FLOOR - 40, VX + 10, FLOOR - 35), fill=1)
                    g.d.rectangle((VX + 9, FLOOR - 33, VX + 10, FLOOR - 32), fill=1)
                    pix.shake(g, t, 1)
            else:   # 原形一溜烟逃出画外
                q = ease_in(span(u, 2.6, 3.6))
                x = VX + q * 50
                self.visitor(g, i, x, full=1.0, t=t)
                if int(u * 20) % 2 == 0:
                    self.puffs.emit(x - 6, FLOOR - 2, vx=-10, vy=-4, life=0.6, rmax=1.8)
        else:   # 下一位客人走进来
            src = self.holder(g, t, w=9)
            vx = lerp(140, VX, ease_out(span(u, 4.6, 6.6)))
            self.visitor(g, nxt, vx, t=t)
        self.fx(g, dt)
        label(g, 125, 3, TRUE[i] + "！" if u < 4.6 else GUISE[nxt] + "？", align="right")
        self.mx(g, 2, 12, u < 2.6)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % CYCLE
        i = self.who(e)
        self.stage(g, t)
        w = max(1, 9 - int(span(t, 0.0, 0.5) * 8))
        src = self.holder(g, t, w=w)
        on = t < 0.3
        if on:
            ang, half, _ = self.sweep(k, e)
            y0, y1 = self.beam(g, src, ang, half, t)
            self.visitor(g, i, VX, band=(y0, y1), t=t)
        else:
            self.visitor(g, i, VX, t=t)
        self.fx(g, dt)
        label(g, 125, 3, "收镜" if t > 0.5 else GUISE[i] + "？", align="right")
        self.mx(g, 0, 3, on)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % CYCLE
        i = self.who(e)
        self.stage(g, t)
        w = 1 + int(span(t, 0.0, 0.6) * 8)
        src = self.holder(g, e, w=w, face="wow" if 0.6 < t < 1.0 else "normal")
        if crossed(t, dt, 0.6):
            self.sparks.burst(src[0] + 3, src[1], 14, 30, life=0.5)
        if 0.6 <= t < 0.67:
            pix.flash(g)
        if t > 0.6:
            ang, half, _ = self.sweep(k, e)
            q = span(t, 0.6, 1.2)
            y0, y1 = self.beam(g, src, ang, half * q, e)
            self.visitor(g, i, VX, band=(y0, y1), t=e, shiver=0.6)
        else:
            self.visitor(g, i, VX, t=e)
        self.fx(g, dt)
        label(g, 125, 3, GUISE[i] + "？", align="right")
        self.mx(g, 0, 3, t > 0.6)

    def complete(self, g: Gfx, t: float, e: float):
        """镜光张满 → 原形自下而上全显 → 镜放光 → 现出原形 → 妖物发抖、化烟散尽"""
        dt = self.clock(t)
        i = self.who(e)
        self.stage(g, t)
        src = self.holder(g, t, face="wow" if t < 2.0 else "happy", glow=t > 1.6)
        ang = 2.0
        half = lerp(10, 22, span(t, 0, 0.6))
        full = span(t, 0.4, 1.6)
        gone = span(t, 3.2, 4.6)
        if gone < 1:
            self.beam(g, src, ang, half, t)
            x0, y0 = self.visitor(g, i, VX, full=full, t=t, shiver=1.5 if t > 1.6 else 0.5)
            if gone > 0:   # 化烟：从上往下抹掉，冒烟团
                cut = int(FLOOR - 32 + gone * 34)
                g.d.rectangle((VX - 12, 0, VX + 12, cut), fill=0)
                if int(t * 20) % 2 == 0:
                    self.puffs.emit(VX + (np.sin(t * 13) * 6), cut, vy=-12, life=1.0, rmax=2.2)
        if crossed(t, dt, 1.6):
            self.sparks.burst(VX, FLOOR - 16, 24, 44, up=10, life=0.8, gravity=40)
        if 1.6 <= t < 1.68:
            pix.flash(g)
        if 1.6 <= t < 2.0:
            pix.shake(g, t, 1.5)
        self.fx(g, dt)
        if t > 2.0:
            banner(g, 64, 4, "现出原形", span(t, 2.0, 2.4))
            banner_text(g, 64, 4, "现出原形", span(t, 2.0, 2.4))
        else:
            label(g, 125, 3, TRUE[i] + "！" if full > 0.5 else GUISE[i] + "？", align="right")
        self.mx(g, ang, 12, gone < 1)
        if t > 1.6:
            mx_ring(g, (t - 1.6) * 4)
            g.mx_level = 1 + int(6 * (1 - span(t, 1.6, 3.0)))
