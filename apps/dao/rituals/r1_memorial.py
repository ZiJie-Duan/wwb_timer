"""焚表上章：黄表横展，毛笔自右而左一字一字写出表文，钤“道经师宝”印；写满卷起，焚化，灰烬随烟升天。

依据：斋醮中的拜表（进表）科仪：高功宣表、封表，焚化以达天庭；表文常用“伏以”“诚惶诚恐，稽首顿首”
“谨表以闻”等程式语；“道经师宝”为道教法印印文。参见 daoinfo《Rituals for Sending Petitions to the Heavens》。

入场：卷着的表从上方落下，两轴向两边展开成一幅；宽袖手执毛笔伸进来。
持续：一轮 600 秒，二十个字（伏以 / 诚惶诚恐 / 稽首顿首 / 具表上奏 / 伏乞 / 谨表以闻）逐字写出，
      每字笔尖自上而下一笔写成；写完盖印。一轮结束：表从两头卷起，自下而上焚化，纸灰飘升，
      新的一幅再展开；右侧“第几表”加一。
中断：笔收走，一根镇纸落下压住表，“停笔”。
恢复：镇纸拿走，笔回来。
圆满：卷表焚化，一只仙鹤自灰烟中飞起，“上达天听”。
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, \
    rand, span
from ..engine.cn import cn_num
from ..engine.fx import flame, smoke_wisp, typewriter
from ..engine.gfx import Gfx, font
from ..engine.scene import Ritual, register
from .r1_common import sleeve, sparkles, vreveal

L0, R0 = 19, 108          # 纸左右边（两轴内侧）
TOP, BOT = 4, 60
COLS = ["伏以", "诚惶诚恐", "稽首顿首", "具表上奏", "伏乞", "谨表以闻"]
COL_X = [93, 79, 65, 51, 37, 23]
ROW_Y = [9, 21, 33, 45]
CHARS = [(ci, ri, ch) for ci, s in enumerate(COLS) for ri, ch in enumerate(s)]
WRITE0 = 3.0
WRITE_END = 520.0
PER = (WRITE_END - WRITE0) / len(CHARS)
STROKE = 2.2              # 一个字写多久
SEAL_T = 540.0
SEAL = ((44, 35, "道"), (44, 42, "经"), (37, 35, "师"), (37, 42, "宝"))
RENEW = 7.0
_glyph_cache: dict[str, Image.Image] = {}


def glyph(ch: str) -> Image.Image:
    if ch not in _glyph_cache:
        im = Image.new("1", (13, 13))
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((0, -3), ch, font=font(12), fill=1)
        _glyph_cache[ch] = im
    return _glyph_cache[ch]


def partial_char(g: Gfx, x: int, y: int, ch: str, k: float):
    """只显示字的上面 k 部分（毛笔自上而下写）"""
    g.texts.append((ch, 12))
    rows = int(round(clamp(k) * 12))
    if rows <= 0:
        return
    im = glyph(ch).crop((0, 0, 13, rows))
    g.img.paste(1, (x, y), im)


def brush(g: Gfx, bx: float, by: float, hand: bool = True):
    """毛笔：笔尖在 (bx, by)。写上半幅时笔杆斜向右下（手在字的右下方），写下半幅时斜向右上，随笔尖高度渐变"""
    ang = lerp(0.6, -0.6, clamp((by - 12) / 34))
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    head = [(bx, by), (bx + ux * 7 + nx * 2, by + uy * 7 + ny * 2), (bx + ux * 7 - nx * 2, by + uy * 7 - ny * 2)]
    g.d.polygon(head, fill=1)
    g.d.line((bx + ux * 7, by + uy * 7, bx + ux * 30, by + uy * 30), fill=1)
    g.d.line((bx + ux * 8 + nx, by + uy * 8 + ny, bx + ux * 8 - nx, by + uy * 8 - ny), fill=0)
    if hand:
        sleeve(g, bx + ux * 16, by + uy * 16, ang, level=0.25)


def crane(g: Gfx, x: float, y: float, t: float, s: float = 1.0):
    """飞鹤（朝右上）：长颈前伸、双腿后拖，翅膀扇动"""
    w = math.sin(t * 8)
    d = g.d
    d.ellipse((x - 6 * s, y - 2 * s, x + 5 * s, y + 2 * s), fill=1)                       # 身
    d.line((x + 4 * s, y - 1 * s, x + 12 * s, y - 6 * s), fill=1, width=2)             # 颈
    d.ellipse((x + 11 * s, y - 8 * s, x + 14 * s, y - 5 * s), fill=1)                  # 头
    d.line((x + 14 * s, y - 7 * s, x + 19 * s, y - 6 * s), fill=1)                     # 喙
    d.line((x - 5 * s, y, x - 17 * s, y + 3 * s), fill=1)                              # 腿
    d.line((x - 5 * s, y + 1 * s, x - 17 * s, y + 5 * s), fill=1)
    tip = (x - 3 * s, y - 15 * s * w)
    d.polygon([(x - 5 * s, y - 1 * s), (x + 3 * s, y - 1 * s), tip], fill=1)           # 翅
    for j in range(3):  # 翅尖飞羽
        d.line((tip[0] - j * 2 * s, tip[1] + j * 2 * s * (1 if w > 0 else -1),
                tip[0] - (j * 2 + 5) * s, tip[1] + (j * 2 + 1) * s * (1 if w > 0 else -1)), fill=1)


@register
class Memorial(Ritual):
    id = "r1.memorial"
    name = "焚表"
    desc = "黄表横展，毛笔逐字写出表文、钤道经师宝印；写满卷起焚化，纸灰升天，再展新表"
    T = {"enter": 4.4, "interrupt": 1.5, "resume": 1.5, "complete": 6.0}
    CYCLE = 600.0

    # ------------------------------------------------------------ 状态

    def written(self, k: float) -> tuple[int, float]:
        """→ (已写完几个字, 正在写的字进度)"""
        u = k - WRITE0
        if u < 0:
            return 0, 0.0
        i = int(u // PER)
        if i >= len(CHARS):
            return len(CHARS), 0.0
        return i, clamp((u - i * PER) / STROKE)

    def char_pos(self, i: int):
        ci, ri, ch = CHARS[i]
        return COL_X[ci], ROW_Y[ri], ch

    # ------------------------------------------------------------ 零件

    def paper(self, g: Gfx, L: float, R: float, n: int, cur: float = 0.0, seal: float = 0.0, burn_y: float = 99):
        L, R = round(L), round(R)
        d = g.d
        bot = min(BOT, burn_y)
        if R - L > 2 and bot > TOP:
            d.rectangle((L, TOP, R, bot), fill=0, outline=1)
            if R - L > 6:
                d.rectangle((L + 2, TOP + 2, R - 2, bot - 2), outline=1)
            for i in range(n + (1 if cur > 0 else 0)):
                x, y, ch = self.char_pos(i)
                if x < L + 2 or x + 12 > R - 2:
                    continue
                if i < n:
                    g.text(x, y, ch)
                else:
                    partial_char(g, x, y, ch, cur)
            if seal > 0 and 36 >= L + 2 and 51 <= R - 2:
                d.rectangle((36, 34, 51, 49), fill=1)
                for x, y, ch in SEAL:
                    g.text(x, y, ch, size=8, fill=0)
                if seal < 1:  # 刚按下：印泥晕开一圈
                    d.rectangle((35, 33, 52, 50), outline=1)
        for x in (L - 4, R + 1):  # 两轴
            d.rectangle((x, TOP - 1, x + 3, min(BOT + 1, burn_y + 1)), fill=0, outline=1)
            if burn_y > BOT:
                d.rectangle((x, TOP - 3, x + 3, TOP - 2), fill=1)
                d.rectangle((x, BOT + 2, x + 3, BOT + 3), fill=1)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        vreveal(g, 2, 4, "上章", a)
        vreveal(g, 115, 4, right if right is not None else f"第{cn_num(n)}表", a)

    def brush_at(self, k: float, t: float):
        """持续阶段笔尖的位置（e 的函数，笔尖小动作用 t）。写完退到画外"""
        n, cur = self.written(k)

        def write_pos(i, c):
            x, y, _ = self.char_pos(i)
            return x + 6 + 3.5 * math.sin(c * 23), y + c * 11

        def hover_pos(i):
            x, y, _ = self.char_pos(i)
            return x + 7, y + 5

        bob = (math.sin(t * 1.7) * 0.8, math.sin(t * 2.3) * 1.0)
        since = (k - WRITE0) - (n - 1) * PER - STROKE  # 上一字写完多久
        if n >= len(CHARS):  # 写完：笔从最后一字退出画外
            x0, y0 = write_pos(n - 1, 1.0)
            p = ease_in(span(since, 0.3, 1.8))
            return lerp(x0, 170, p), lerp(y0, 80, p)
        if 0 < cur < 1:  # 正在写：笔尖跟着字自上而下
            return write_pos(n, cur)
        hx, hy = hover_pos(n)
        if n == 0:
            return hx + bob[0], hy + bob[1]
        x0, y0 = write_pos(n - 1, 1.0)  # 从上一字收笔处移到下一字
        p = ease_in_out(span(since, 0.2, 1.6))
        return lerp(x0, hx, p) + bob[0] * p, lerp(y0, hy, p) + bob[1] * p

    def mx(self, g: Gfx, n: int, cur: float, sealed: bool, t: float):
        for i in range(n + (1 if cur > 0.5 else 0)):
            ci, ri, _ = CHARS[i]
            g.mx_set(6 - ci, 1 + ri)
        if sealed:
            g.mx[6, 0:2] = True
            g.mx[7, 0:2] = True
        elif n < len(CHARS):
            ci, ri, _ = CHARS[n]
            if blink(t, 0.5):
                g.mx_set(6 - ci, 1 + ri)

    def ash(self, g: Gfx, k: float, k0: float, y0: float):
        """纸灰：从 y0 一路飘升"""
        for j in range(14):
            st = k0 + j * 0.16
            u = k - st
            if 0 < u < 3.0:
                x = 64 + (rand(j, 7) - 0.5) * 14 + math.sin(u * 3 + j) * 4
                y = y0 - (rand(j, 8) * 30 + 10) * u * 0.8 - j
                if y > 0:
                    g.px(x, y)
                    if j % 3 == 0:
                        g.px(x + 1, y)

    def burn(self, g: Gfx, k: float, t: float, k0: float, dur: float):
        """卷起的表自下而上焚化；k0 起，dur 秒烧完。返回是否已烧完"""
        p = span(k, k0, k0 + dur)
        yb = lerp(BOT + 2, TOP, ease_in_out(p))
        if p < 1:
            if yb > TOP:
                g.d.rectangle((59, TOP, 68, yb), fill=0, outline=1)
                g.d.line((63, TOP, 63, yb), fill=1)
                g.d.rectangle((59, TOP - 3, 68, TOP - 2), fill=1)
            flame(g, 61, yb + 2, 8, 14 * (1 - 0.5 * p), t, self.seed)
            flame(g, 67, yb + 2, 6, 10, t + 1.3, self.seed + 1)
            for j in range(3):  # 焦边
                g.px(59 + j * 4, yb + 1)
        self.ash(g, k, k0 + 0.2, lerp(BOT, TOP + 6, p))
        if p > 0.2:
            smoke_wisp(g, 64, min(yb, 40), min(yb, 40), t, self.seed, sway=3, speed=8)
        return p >= 1

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        drop = ease_out_bounce(span(t, 0, 0.8))
        unroll = ease_in_out(span(t, 0.9, 2.1))
        L, R = lerp(60, L0, unroll), lerp(67, R0, unroll)
        if t < 0.9:
            g.d.rectangle((59, TOP - 1 - (1 - drop) * 70, 68, BOT + 1 - (1 - drop) * 70), fill=0, outline=1)
            g.d.line((63, TOP - (1 - drop) * 70, 63, BOT - (1 - drop) * 70), fill=1)
        else:
            self.paper(g, L, R, 0)
        if t > 2.1:
            p = ease_out(span(t, 2.1, 3.3))
            tx, ty = self.brush_at(0, t)
            brush(g, lerp(150, tx, p), lerp(-40, ty, p))
        self.texts(g, 0, a=span(t, 3.2, 4.2))
        if t > 2.1:
            g.mx[1:7, 0] = True
            g.mx[1:7, 7] = True

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        n, cur = self.written(k)
        seal = span(k, SEAL_T + 0.9, SEAL_T + 1.6)
        self.paper(g, L0, R0, n, cur, seal)
        if SEAL_T - 1 <= k < SEAL_T + 3:  # 盖印：印章落下、按、抬起
            u = k - (SEAL_T - 1)
            if u < 1.9:
                yy = lerp(-30, 49, ease_in(span(u, 0, 1.9)))
            else:
                yy = lerp(49, -30, ease_in(span(u, 2.3, 4.0)))
            g.d.rectangle((36, yy - 15, 51, yy), fill=0, outline=1)
            g.d.line((37, yy - 3, 50, yy - 3), fill=1)
            g.d.rectangle((40, yy - 27, 47, yy - 15), fill=0, outline=1)
            g.d.ellipse((38, yy - 33, 49, yy - 25), fill=0, outline=1)
            if 1.85 < u < 2.1:
                for j in range(8):
                    a = j / 8 * 2 * math.pi
                    g.px(44 + math.cos(a) * 13, 42 + math.sin(a) * 11)
        else:
            bx, by = self.brush_at(k, t)
            brush(g, bx, by)
        self.texts(g, e)
        g.mx[1:7, 0] = True
        g.mx[1:7, 7] = True
        self.mx(g, n, cur, seal > 0.5, t)
        if 0 < cur < 0.15 or abs(k - (SEAL_T + 0.9)) < 0.15:
            g.mx_level = 3

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        roll = ease_in_out(span(k, 0, 1.4))
        if k < 1.4:
            self.paper(g, lerp(L0, 60, roll), lerp(R0, 67, roll), len(CHARS), 0, 1.0)
            self.texts(g, e - k - 1)
        elif k < 4.8:
            self.burn(g, k, t, 1.4, 2.6)
            self.texts(g, e - k - 1 if k < 3 else e)
        else:
            u = ease_in_out(span(k, 4.8, 6.4))
            self.paper(g, lerp(60, L0, u), lerp(67, R0, u), 0)
            self.ash(g, k, 1.6, 30)
            if k > 6.0:
                p = ease_out(span(k, 6.0, RENEW))
                tx, ty = self.brush_at(0, t)
                brush(g, lerp(150, tx, p), lerp(-40, ty, p))
            self.texts(g, e)
        # 点阵：卷起时字一列列收拢，焚化时一团火往上烧
        if k < 1.4:
            self.mx(g, len(CHARS), 0, True, t)
            c = int(roll * 4)
            g.mx[:, :c] = False
            g.mx[:, 8 - c:] = False
        elif k < 4.8:
            h = int(span(k, 1.4, 4.0) * 8)
            for y in range(8 - h, 8):
                for x in range(2, 6):
                    g.mx[y, x] = noise(t * 8 + x * 3 + y, self.seed) > 0.35
        else:
            g.mx[1:7, 0] = True
            g.mx[1:7, 7] = True

    def interrupt(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n, cur = self.written(k)
        if 0 < cur < 1:  # 正写到一半：算写完这一笔再停
            cur = 1.0
        seal = span(k, SEAL_T + 0.9, SEAL_T + 1.6)
        self.paper(g, L0, R0, n, cur, seal)
        bx, by = self.brush_at(k, 0)
        p = ease_in(span(t, 0, 0.8))
        brush(g, lerp(bx, 160, p), lerp(by, -50, p))
        drop = ease_out_bounce(span(t, 0.6, 1.3))
        if drop > 0:  # 镇纸
            y = lerp(-10, 1, drop)
            g.d.rectangle((40, y, 88, y + 4), fill=1)
            g.d.line((42, y + 2, 86, y + 2), fill=0)
            g.d.rectangle((62, y - 2, 66, y), fill=1)
        self.texts(g, e, right="停笔" if t > 0.8 else None)
        g.mx[1:7, 0] = True
        g.mx[1:7, 7] = True
        self.mx(g, n, cur, seal > 0.5, 0)
        if drop > 0:
            g.mx[0, 1:7] = True

    def resume(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n, cur = self.written(k)
        seal = span(k, SEAL_T + 0.9, SEAL_T + 1.6)
        self.paper(g, L0, R0, n, cur, seal)
        lift = ease_in(span(t, 0, 0.6))
        y = lerp(1, -14, lift)
        if lift < 1:
            g.d.rectangle((40, y, 88, y + 4), fill=1)
            g.d.line((42, y + 2, 86, y + 2), fill=0)
            g.d.rectangle((62, y - 2, 66, y), fill=1)
        p = ease_out(span(t, 0.4, 1.5))
        bx, by = self.brush_at(k, t)
        brush(g, lerp(160, bx, p), lerp(-50, by, p))
        self.texts(g, e, right="停笔" if t < 0.4 else None)
        g.mx[1:7, 0] = True
        g.mx[1:7, 7] = True
        self.mx(g, n, cur, seal > 0.5, t)

    def complete(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n, cur = self.written(k)
        n = max(n, 1)
        seal = 1.0 if k > SEAL_T + 1 else 0.0
        roll = ease_in_out(span(t, 0, 1.0))
        if t < 1.0:
            self.paper(g, lerp(L0, 60, roll), lerp(R0, 67, roll), n, 0, seal)
            bx, by = self.brush_at(k, t)
            brush(g, bx + roll * 60, by - roll * 50)
            self.texts(g, e, a=1 - roll)
        elif t < 3.2:
            self.burn(g, t, t, 1.0, 1.8)
        if t > 2.4:  # 仙鹤自烟中飞起
            p = span(t, 2.4, 6.0)
            x = lerp(58, 104, ease_in_out(p))
            y = lerp(40, 12, ease_out(p))
            crane(g, x, y, t, s=1.2)
        if t > 3.4:
            typewriter(g, 46, 46, "上达天听", t - 3.4, cps=5, align="center")
            sparkles(g, 64, 30, 60, 28, t, n=8, seed=self.seed)
        # 点阵：火 → 鹤
        if t < 1.0:
            self.mx(g, n, 0, seal > 0, t)
        elif t < 3.2:
            for y in range(8):
                for x in range(2, 6):
                    g.mx[y, x] = y > 7 - span(t, 1.0, 2.0) * 8 and noise(t * 8 + x * 3 + y, self.seed) > 0.35
        else:
            up = int(t * 6) % 2
            g.mx_rows([0, 0, 0b00000110 if up else 0, 0b11111100 if up else 0b11111100, 0b00111000,
                       0 if up else 0b00110000, 0 if up else 0b01100000, 0])
            g.mx_level = 2
