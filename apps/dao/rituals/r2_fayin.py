"""盖法印：俯视的案头。法印（道经师宝）蘸印泥、压在文书上，一张张盖好叠到右边。

依据：正一派常用法印“道经师宝”（道、经、师三宝），文书、符箓画毕须“敕符盖印”；
印文四字按古印读法右起竖读：道经 / 师宝。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r2_common import glyph, rays

BOX = (17, 48)                 # 印泥盒（俯视）
REST = (17, 16)                # 法印放在盒子上方
SHEET = (36, 6, 92, 60)        # 文书
IMP = 30                       # 印面边长
IMP_C = (61, 36)               # 盖印位置（印面中心）
PILE_X = 100                   # 右边叠放
PILE_Y = 18
PERIOD = 40.0                  # 一张
RENEW = 4.0


def _imprint() -> Sprite:
    """印文：阳文方印，外框 2 像素，右起竖读 道经 / 师宝"""
    on = np.zeros((IMP, IMP), dtype=bool)
    on[:2, :] = on[-2:, :] = on[:, :2] = on[:, -2:] = True
    cells = (("道", 15, 3), ("经", 15, 16), ("师", 3, 3), ("宝", 3, 16))
    for ch, x, y in cells:
        spr = glyph(ch)
        h, w = spr.on.shape
        on[y:y + h, x:x + min(w, 12)] |= spr.on[:, :12]
    mask = np.ones_like(on)
    return Sprite(on=on, mask=mask)


IMPRINT = _imprint()
IMPRINT2 = IMPRINT.scale(2)


@register
class FaYin(Ritual):
    id = "r2.fayin"
    name = "盖法印"
    desc = "俯视案头：道经师宝印蘸朱红印泥，重重压在文书上，一张张盖好叠起；圆满时大印当空落下"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.5, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.tassel = self.rng.random() * 6

    # ------------------------------------------------------------ 零件

    def box(self, g: Gfx, lid: float = 0.0, dx: float = 0.0):
        x, y = BOX[0] + dx, BOX[1]
        g.d.ellipse((x - 13, y - 13, x + 13, y + 13), outline=1, fill=0)
        g.d.ellipse((x - 10, y - 10, x + 10, y + 10), outline=1)
        for yy in range(-8, 9, 2):  # 印泥（朱红）用细横纹表现
            w = int(math.sqrt(max(0, 81 - yy * yy)))
            g.d.line((x - w, y + yy, x + w, y + yy), fill=1)
        if lid > 0:  # 盒盖从上方盖下
            ly = lerp(y - 40, y, ease_out(lid))
            g.d.ellipse((x - 13, ly - 13, x + 13, ly + 13), outline=1, fill=0)
            g.d.ellipse((x - 9, ly - 9, x + 9, ly + 9), outline=1)
            g.d.ellipse((x - 3, ly - 3, x + 3, ly + 3), fill=1)

    def sheet_marks(self, g: Gfx, idx: int, dx: float = 0, dy: float = 0):
        """文书上的字：右起竖行，短笔画"""
        x0, y0, x1, y1 = SHEET
        for c in range(6):
            cx = x1 - 6 - c * 8 + dx
            n = 5 + int(rand(idx * 7 + c, 11) * 5)
            for j in range(n):
                yy = y0 + 5 + j * 5 + dy
                if yy > y1 - 5 + dy:
                    break
                r = rand(idx * 31 + c * 9 + j, 12)
                if r < 0.35:
                    g.d.line((cx - 1, yy, cx + 1, yy + 1), fill=1)
                elif r < 0.7:
                    g.d.line((cx, yy - 1, cx, yy + 2), fill=1)
                    g.px(cx - 1, yy)
                else:
                    g.d.line((cx - 1, yy + 1, cx + 1, yy - 1), fill=1)
                    g.px(cx + 1, yy + 2)

    def sheet(self, g: Gfx, idx: int, stamped: bool, dx: float = 0, dy: float = 0, shine: float = -1):
        x0, y0, x1, y1 = SHEET
        g.d.rectangle((x0 + dx, y0 + dy, x1 + dx, y1 + dy), fill=0, outline=1)
        g.d.line((x0 + 2 + dx, y1 + 1 + dy, x1 + 1 + dx, y1 + 1 + dy), fill=1)  # 纸的厚度
        g.d.line((x1 + 1 + dx, y0 + 2 + dy, x1 + 1 + dx, y1 + 1 + dy), fill=1)
        self.sheet_marks(g, idx, dx, dy)
        if stamped:
            ix, iy = IMP_C[0] - IMP // 2 + dx, IMP_C[1] - IMP // 2 + dy
            g.blit(IMPRINT, ix, iy)
            if 0 <= shine <= 1:  # 印泥未干的反光：一道斜光扫过印面
                k = shine * (IMP * 2 + 8) - 4
                for d in (0, 1):
                    xa, ya = ix + k - d, iy
                    pts = [(xa - j, ya + j) for j in range(IMP)]
                    pts = [(x, y) for x, y in pts if ix + 2 <= x < ix + IMP - 2 and iy + 2 <= y < iy + IMP - 2]
                    if len(pts) > 1:
                        g.d.line((pts[0], pts[-1]), fill=0 if d else 1)

    def pile(self, g: Gfx, n: int, dx: float = 0, tie: float = 0.0):
        if n <= 0:
            return
        x0, y0, x1, y1 = SHEET
        layers = min(n, 6)
        for i in range(layers - 1, -1, -1):
            ox = PILE_X + dx + i * 1.5 - (layers - 1) * 1.5
            oy = PILE_Y + i * 1 - (layers - 1)
            g.d.rectangle((ox, oy, ox + (x1 - x0), oy + (y1 - y0)), fill=0, outline=1)
        top_dx = PILE_X - x0 + dx - (layers - 1) * 1.5
        top_dy = PILE_Y - y0 - (layers - 1)
        self.sheet_marks(g, 999, top_dx, top_dy)
        g.blit(IMPRINT, IMP_C[0] - IMP // 2 + top_dx, IMP_C[1] - IMP // 2 + top_dy)
        if tie > 0:  # 扎起来：一道红绳
            yy = 33 + top_dy
            g.d.rectangle((PILE_X + dx - 10, yy - 1, PILE_X + dx + 40, yy + 1), fill=1)
            g.d.line((PILE_X + dx + 4, yy - 6, PILE_X + dx + 8, yy + 6), fill=1)

    def seal(self, g: Gfx, x: float, y: float, h: float, rock: float = 0.0):
        """俯视的法印：h = 离纸高度（0..1.5），越高越大、影子越偏"""
        if h > 0.05:  # 影子
            sx, sy = x + h * 7, y + h * 7
            hw = IMP / 2
            g.d.rectangle((sx - hw, sy - hw, sx + hw, sy + hw), fill=0)
            for yy in range(int(sy - hw), int(sy + hw), 2):
                for xx in range(int(sx - hw) + (yy // 2) % 2, int(sx + hw), 3):
                    g.px(xx, yy)
        s = 1 + h * 0.22
        x += rock
        hw = IMP / 2 * s
        g.d.rectangle((x - hw, y - hw, x + hw, y + hw), fill=0, outline=1)
        bw = hw - 3 * s
        g.d.rectangle((x - bw, y - bw, x + bw, y + bw), outline=1)
        for cx, cy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):  # 斜角棱
            g.d.line((x + cx * hw, y + cy * hw, x + cx * bw, y + cy * bw), fill=1)
        # 印钮：龟钮（俯视）——四足、龟首、甲背六角纹
        r = 6 * s
        for lx, ly in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            fx, fy = x + lx * r * 0.95, y + ly * r * 0.8
            g.d.ellipse((fx - 1.5 * s, fy - 1.5 * s, fx + 1.5 * s, fy + 1.5 * s), fill=1)
        g.d.ellipse((x - 2 * s, y - r - 3.5 * s, x + 2 * s, y - r + 0.5 * s), fill=1, outline=1)  # 龟首
        g.d.line((x, y + r * 0.8, x, y + r * 0.8 + 3 * s), fill=1)  # 尾
        g.d.ellipse((x - r, y - r * 0.85, x + r, y + r * 0.85), fill=0, outline=1)
        hx = r * 0.45
        g.d.polygon([(x - hx, y), (x - hx / 2, y - hx * 0.8), (x + hx / 2, y - hx * 0.8), (x + hx, y),
                     (x + hx / 2, y + hx * 0.8), (x - hx / 2, y + hx * 0.8)], outline=1)
        for a in (0, 1, 2, 3, 4, 5):
            ang = a * math.pi / 3
            g.d.line((x + math.cos(ang) * hx, y + math.sin(ang) * hx * 0.9, x + math.cos(ang) * r,
                      y + math.sin(ang) * r * 0.85), fill=1)
        # 绶带穗子：从印钮垂下，随动作摆
        sw = math.sin(self.tassel + h * 3) * 3
        pts = [(x + r * 0.6, y), (x + r + 4 + sw * 0.4, y + 4), (x + r + 6 + sw, y + 10), (x + r + 5 + sw * 1.2, y + 15)]
        g.d.line(pts, fill=1)
        g.d.line((pts[-1][0] - 1, pts[-1][1], pts[-1][0] + 1, pts[-1][1] + 3), fill=1)

    def count_text(self, g: Gfx, n: int, a: float = 1.0):
        s = cn_num(n) + "印" if n else "法印"
        if a > 0:
            g.text(114, 2, s[:max(0, int(round(len(s) * a)))], align="center")

    def mx_seal(self, g: Gfx, full: bool = True):
        g.mx[0, :] = g.mx[7, :] = True
        g.mx[:, 0] = g.mx[:, 7] = True
        if full:
            for y, x in ((2, 2), (2, 5), (5, 2), (5, 5), (2, 4), (3, 5), (4, 2), (5, 3)):
                g.mx[y, x] = True

    # ------------------------------------------------------------ 一张的过程

    def step(self, g: Gfx, t: float, k: float, idx: int, pile_n: int):
        """一张：k = 本张经过的秒数"""
        bx, by = BOX
        cx, cy = IMP_C
        self.box(g)
        stamped = k >= 4.7
        slide_in = k < 1.2
        if k >= PERIOD - 1.5:  # 盖好的这张滑到右边
            p = ease_in_out(span(k, PERIOD - 1.5, PERIOD))
            self.pile(g, pile_n)
            self.sheet(g, idx, True, dx=p * (PILE_X - SHEET[0]), dy=p * (PILE_Y - SHEET[1]))
        else:
            self.pile(g, pile_n)
            dy = (1 - ease_out(span(k, 0, 1.2))) * 64 if slide_in else 0
            self.sheet(g, idx, stamped, dy=dy, shine=((k - 6.8) % 7) / 1.2 if k > 6.8 else -1)
        # 印的位置与高度
        rock = 0.0
        rx, ry = REST
        if k < 1.2:
            x, y, h = rx, ry, 0.0
        elif k < 1.8:  # 提起，挪到印泥上
            p = ease_in_out(span(k, 1.2, 1.8))
            x, y, h = rx, lerp(ry, by, p), math.sin(p * math.pi) * 0.7
        elif k < 2.9:  # 蘸印泥：按两下
            x, y = bx, by
            h = abs(math.sin((k - 1.8) / 1.1 * 2 * math.pi)) * 0.5
        elif k < 3.9:  # 提起，移到纸上
            p = ease_in_out(span(k, 2.9, 3.9))
            x, y = lerp(bx, cx, p), lerp(by, cy, p)
            h = 0.6 + math.sin(p * math.pi) * 0.6 + p * 0.4
        elif k < 4.3:  # 落印
            x, y = cx, cy
            h = 1.0 * (1 - ease_in(span(k, 3.9, 4.3)))
        elif k < 5.0:  # 压住，左右摇一摇
            x, y, h = cx, cy, 0.0
            rock = math.sin((k - 4.3) * 18) * (1 - span(k, 4.3, 5.0))
        elif k < 5.7:  # 提起，露出印文
            x, y = cx, cy
            h = ease_out(span(k, 5.0, 5.7)) * 1.2
        elif k < 6.8:
            p = ease_in_out(span(k, 5.7, 6.8))
            x, y = lerp(cx, rx, p), lerp(cy, ry, p)
            h = 1.2 * (1 - p)
        else:
            x, y, h = rx, ry, 0.0
        if 4.3 <= k < 4.7:  # 落印的震动线
            f = span(k, 4.3, 4.7)
            for i in range(8):
                a = i / 8 * 2 * math.pi + 0.4
                r0 = IMP / 2 + 3 + f * 6
                g.d.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * (r0 + 4),
                          cy + math.sin(a) * (r0 + 4)), fill=1)
        if 5.0 <= k < 5.9:  # 印文显出时一圈光
            f = span(k, 5.0, 5.9)
            rays(g, cx, cy, IMP / 2 + 2 + f * 4, IMP / 2 + 5 + f * 8, 12, phase=0.2)
        self.seal(g, x, y, h, rock)
        self.mx_seal(g, full=k >= 5.0 or k < 0.5)
        if 4.3 <= k < 4.6:
            g.mx_level = 6
        return x, y, h

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dx = -40 * (1 - ease_out(span(t, 0, 0.9)))
        self.box(g, lid=1 - ease_in_out(span(t, 1.6, 2.3)), dx=dx)
        dy = (1 - ease_out_back(span(t, 0.5, 1.5))) * 64
        self.sheet(g, 0, False, dy=dy)
        if t > 2.3:  # 法印从上方（镜头外）落到盒上方
            p = span(t, 2.3, 3.4)
            h = 1.5 * (1 - ease_out(p))
            yy = lerp(-30, REST[1], ease_out(p))
            self.seal(g, REST[0], yy, h)
            if 3.3 < t < 3.7:
                rays(g, REST[0], REST[1], 18, 22, 10)
        self.count_text(g, 0, span(t, 3.0, 4.0))
        self.mx_seal(g, full=t > 3.4)
        g.mx_level = 4 if 3.3 < t < 3.5 else 1

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        n_round = int(e // self.CYCLE)
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, n_round)
            return
        uu = u - (RENEW if e >= self.CYCLE else 0)
        i = int(uu // PERIOD)
        k = uu - i * PERIOD
        idx = n_round * 20 + i
        self.step(g, t, k, idx, i)
        self.count_text(g, i + (k >= 4.7))

    def _renew(self, g: Gfx, t: float, u: float, n_round: int):
        """一卷盖完：右边那叠扎起红绳、推出画外，换一叠新纸"""
        n = int((self.CYCLE - RENEW) // PERIOD)
        self.box(g)
        tie = span(u, 0.2, 0.9)
        dx = ease_in(span(u, 1.0, 2.2)) * 40
        self.pile(g, n, dx=dx, tie=tie)
        dy = (1 - ease_out(span(u, 2.4, 3.6))) * 64
        self.sheet(g, n_round * 20, False, dy=dy)
        self.seal(g, REST[0], REST[1], 0)
        self.count_text(g, n if u < 2.2 else 0)
        self.mx_seal(g)
        g.mx_level = 3 if u < 0.9 else 1

    def _paused(self, g: Gfx, e: float, lid: float, t: float):
        u = e % self.CYCLE
        n_round = int(e // self.CYCLE)
        uu = max(0.0, u - (RENEW if e >= self.CYCLE else 0))
        i = int(uu // PERIOD)
        k = uu - i * PERIOD
        stamped = 4.7 <= k < PERIOD - 1.5
        self.pile(g, i)
        self.sheet(g, n_round * 20 + i, stamped)
        self.box(g, lid=lid)
        return i, k

    def _seal_pos(self, e: float):
        """暂停时印在哪：盖印动作中途就停在原处，否则在盒子上方"""
        u = e % self.CYCLE
        uu = max(0.0, u - (RENEW if e >= self.CYCLE else 0))
        k = uu % PERIOD
        if 1.2 <= k < 6.8:
            return IMP_C if 3.9 <= k < 5.7 else BOX
        return REST

    def interrupt(self, g: Gfx, t: float, e: float):
        """印放回原处，印泥盒盖上"""
        i, k = self._paused(g, e, 0.0, t)
        lid = ease_out_back(span(t, 0.6, 1.2))
        if lid > 0:
            self.box(g, lid=lid)
        sx0, sy0 = self._seal_pos(e)
        p = ease_in_out(span(t, 0, 0.6))
        self.seal(g, lerp(sx0, REST[0], p), lerp(sy0, REST[1], p), math.sin(p * math.pi) * 0.6 if (sx0, sy0) != REST else 0)
        self.count_text(g, i + (4.7 <= k < PERIOD))
        self.mx_seal(g, full=t < 0.6 or blink(t, 0.4))

    def resume(self, g: Gfx, t: float, e: float):
        i, k = self._paused(g, e, 0.0, t)
        lid = 1 - ease_in_out(span(t, 0, 0.6))
        if lid > 0:
            self.box(g, lid=lid)
        sx1, sy1 = self._seal_pos(e)
        p = ease_in_out(span(t, 0.7, 1.5))
        self.seal(g, lerp(REST[0], sx1, p), lerp(REST[1], sy1, p), math.sin(p * math.pi) * 0.6 if (sx1, sy1) != REST else 0)
        self.count_text(g, i + (4.7 <= k < PERIOD))
        self.mx_seal(g, full=t > 0.6)

    def complete(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        uu = max(0.0, u - (RENEW if e >= self.CYCLE else 0))
        i = int(uu // PERIOD)
        n_round = int(e // self.CYCLE)
        fade = 1 - span(t, 1.0, 1.8)
        if t < 1.8:
            if fade > 0.5:
                self.box(g)
                self.pile(g, i)
                self.sheet(g, n_round * 20 + i, True)
            # 法印腾空而起
            p = ease_in(span(t, 0, 1.4))
            self.seal(g, lerp(REST[0], 64, p), lerp(REST[1], 32, p), p * 1.5)
            self.count_text(g, i)
            self.mx_seal(g)
            return
        # 一方大印从天落下，压在正中
        k = span(t, 1.8, 2.4)
        cx, cy = 64, 32
        if k < 1:
            s = 1 + (1 - ease_in(k)) * 1.2
            hw = IMP * s
            for j in range(3):  # 大印压下：几层方框收拢
                q = hw + j * 6 * (1 - k)
                g.d.rectangle((cx - q, cy - q + 2, cx + q, cy + q + 2), outline=1)
            g.text(cx, 26, "敕", align="center", scale=1)
        else:
            shake = math.sin(t * 50) * 2 * (1 - span(t, 2.4, 2.8))
            g.blit(IMPRINT2, cx - IMP + shake, cy - IMP + 2)
            f = t - 2.4
            for j in range(2):
                r = ((f * 30 + j * 20) % 40) + IMP + 2
                rays(g, cx, cy, r, r + 4, 16, phase=j * 0.2)
            if f < 0.15:
                g.invert()
        g.mx_level = 1 + int(6 * (1 - span(t, 2.4, 3.6))) if t > 2.4 else 1
        self.mx_seal(g, full=t > 2.4)
        if t > 2.4:
            g.mx[3:5, 3:5] = blink(t, 0.4)
