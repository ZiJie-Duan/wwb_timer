"""写经换鹅：王羲之写《黄庭经》换山阴道士的白鹅。

《晋书·王羲之传》：山阴道士养好鹅，羲之往观，求市之；道士云“为写道德经，当举群相赠耳”，羲之欣然写毕，笼鹅而归。
后世多传为写《黄庭经》——李白《王右军》：“扫素写道经，笔精妙入神。书罢笼鹅去，何曾别主人。”

入场：宣纸从上往下展开（镇纸压住），白鹅从右边游进池塘，毛笔落到砚台上。
持续：一字一张：毛笔蘸墨，在纸上写出一个斗大的字（从上往下一笔笔显出来，笔尖跟着走），写完回砚台；
      大字淡去，缩成左边小字一列（本句已写的字，8px 竖排）。经文为《黄庭外景经》首四句，七字一句。
      池里两三只白鹅游来游去，偶尔伸颈一叫，水下鹅掌拨水。
      每写完一句盖一方“右军”朱印；每写完两句：“书罢笼鹅去”——一只竹笼从天而降罩住一只鹅提走，过一会儿又游来一只。
退场：画面收拢成一个圆。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.fx import brush_reveal, typewriter
from ..engine.gfx import Gfx, Sprite, text_width
from ..engine.scene import Rest, register
from .x2_common import iris

LINES = ["上有黄庭下关元", "后有幽阙前命门", "呼吸庐间入丹田", "玉池清水灌灵根"]
PER = 6.0                     # 一个字的秒数
PAPER = (14, 3, 66, 61)
CHAR_XY = (17, 8)
INK = (80, 9)                 # 砚台中心
POND_Y = 40                   # 水面

MX_GOOSE = Sprite("""
....##..
...###..
...#....
...#....
.######.
########
.######.
........
""")
BRUSH = Sprite("""
  .##.
  .##.
  .##.
  .##.
  .##.
  .##.
  .##.
  .##.
  .##.
 .####.
 ######
 #.##.#
 .####.
  .##.
  .#.
""")


def paper(g: Gfx, h: float = 1.0, dx: float = 0.0):
    x0, y0, x1, y1 = PAPER
    yb = y0 + (y1 - y0) * h
    g.d.rectangle((x0 + dx, y0, x1 + dx, yb), fill=0, outline=1)
    g.d.rectangle((x0 - 2 + dx, y0 - 2, x1 + 2 + dx, y0 + 1), fill=1)   # 镇纸
    g.d.line((x0 + 2 + dx, y0 + 4, x0 + 2 + dx, yb - 2), fill=1)          # 界格（朱丝栏）
    g.d.line((x1 - 2 + dx, y0 + 4, x1 - 2 + dx, yb - 2), fill=1)
    if h < 1:  # 纸卷
        g.d.rectangle((x0 - 1 + dx, yb - 1, x1 + 1 + dx, yb + 2), fill=1)


def inkstone(g: Gfx):
    x, y = INK
    g.d.rounded_rectangle((x - 11, y - 5, x + 11, y + 5), 3, fill=0, outline=1)
    g.d.ellipse((x - 7, y - 3, x + 4, y + 3), fill=1)  # 墨池
    g.d.line((x + 7, y - 3, x + 7, y + 3), fill=1)


def water(g: Gfx, t: float, gaps=()):
    for j, y in enumerate((POND_Y, POND_Y + 8, POND_Y + 16)):
        for x in range(70, 128, 6):
            xx = x + (t * (3 + j) + j * 3) % 6
            if any(a - 2 <= xx <= b + 2 for a, b in gaps) and j == 0:
                continue
            if rand(int(x / 6) + j * 31, 5) < 0.7:
                g.d.line((xx, y + math.sin(xx * 0.3 + t) * 0.6, xx + 3, y + math.sin(xx * 0.3 + t) * 0.6), fill=1)


def cage(g: Gfx, x: float, y: float):
    """竹编鹅笼：圆顶 + 竖篾 + 提手"""
    g.d.rectangle((x - 9, y - 10, x + 9, y + 4), fill=0)
    g.d.arc((x - 9, y - 16, x + 9, y - 4), 180, 360, fill=1)
    for i in range(-8, 9, 3):
        g.d.line((x + i, y - 10 + (abs(i) > 6) * 2, x + i, y + 4), fill=1)
    g.d.line((x - 9, y + 4, x + 9, y + 4), fill=1)
    g.d.line((x - 9, y - 4, x + 9, y - 4), fill=1)
    g.d.arc((x - 4, y - 21, x + 4, y - 13), 180, 360, fill=1)


@register
class Goose(Rest):
    id = "x2.goose"
    name = "写经换鹅"
    desc = "毛笔一张一个斗大的字写《黄庭经》，左边攒成一列小字；池中白鹅游弋，写完两句就笼鹅而去"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0
        self.l0 = self.rng.randrange(len(LINES))

    # ------------------------------------------------------------ 字

    def where(self, t: float):
        """→ (句号, 句中第几字, 本字已过秒数)"""
        n = int(t // PER)
        return n // 7, n % 7, t % PER

    def line(self, li: int) -> str:
        return LINES[(li + self.l0) % len(LINES)]

    # ------------------------------------------------------------ 鹅

    def geese(self, t: float):
        """→ [(x, 朝向, 是否叫)]；第 k 次笼鹅后少一只、过一会儿再游来一只"""
        out = []
        cyc = PER * 14
        k = t % cyc
        caged = k > PER * 13 + 2.6  # 被笼走了
        back = span(k, 0, 6)       # 新来的那只从右边游进来（下一轮开头）
        for i in range(3):
            if i == 2 and caged:
                continue
            ph = t * 0.05 * (1 + i * 0.3) + i * 1.7 + self.seed
            x = (84, 102, 117)[i] + math.sin(ph) * (7 - i)
            d = 1 if math.cos(ph) > 0 else -1
            if i == 2 and t > cyc and k < 6:
                x = lerp(140, x, ease_out(back))
                d = -1
            honk = (t + i * 13) % 23 < 0.8
            out.append((x, d, honk))
        return out, (k - (PER * 13 + 0.8) if PER * 13 + 0.8 < k < PER * 13 + 6.5 else None)

    def goose(self, g: Gfx, x: float, y: float, d: int, honk: bool, t: float, i: int):
        """白鹅（侧面浮水）：x 为身子中点，y 为水线"""
        D = g.d
        D.ellipse((x - 8, y - 6, x + 6, y + 2), fill=1)                          # 身
        D.polygon([(x - d * 7, y - 3), (x - d * 11, y - 8), (x - d * 5, y - 5)], fill=1)  # 翘尾
        D.arc((x - 6, y - 5, x + 3, y + 1), 200 if d > 0 else 280, 260 if d > 0 else 340, fill=0)  # 翅
        if d < 0:
            D.ellipse((x - 6, y - 6, x + 8, y + 2), fill=1)
        lean = 3 if honk else 0
        nx0, ny0 = x + d * 4, y - 4
        nx1, ny1 = x + d * (6 + lean), y - 12 + lean
        D.line([(nx0, ny0), (x + d * (7 + lean * 0.5), y - 8 + lean * 0.5), (nx1, ny1)], fill=1, width=3)  # 颈
        D.ellipse((nx1 - 2, ny1 - 3, nx1 + 3, ny1 + 1), fill=1)                  # 头
        g.px(nx1 + d * 1, ny1 - 3)                                                 # 额上的肉瘤
        g.px(nx1 + d * 1, ny1 - 2, 0)                                              # 眼
        if honk:  # 张嘴一叫
            D.line((nx1 + d * 3, ny1 - 1, nx1 + d * 6, ny1 - 3), fill=1)
            D.line((nx1 + d * 3, ny1, nx1 + d * 6, ny1 + 1), fill=1)
            for j in range(2):
                g.px(nx1 + d * (8 + j * 2), ny1 - 4 - j)
        else:
            D.line((nx1 + d * 3, ny1 - 1, nx1 + d * 5, ny1), fill=1, width=2)
        D.rectangle((x - 12, y + 1, x + 10, y + 3), fill=0)                       # 水线以下
        ph = (t * 1.5 + i) % 1  # 身后的尾波
        for k in range(2):
            r = 4 + ((ph + k * 0.5) % 1) * 10
            g.px(x - d * (8 + r), y + 1 + r * 0.2)
            g.px(x - d * (8 + r), y + 1 - r * 0.15)

    def draw_geese(self, g: Gfx, t: float, dx: float = 0.0):
        gs, cage_k = self.geese(t)
        water(g, t)
        for i, (x, d, honk) in enumerate(gs):
            x += dx
            bob = round(math.sin(t * 2 + i) * 0.6)
            y = POND_Y + bob
            if i == 2 and cage_k is not None and cage_k > 1.8:  # 被笼提起
                y -= ease_in(span(cage_k, 2.6, 5.7)) * 60
            self.goose(g, x, y, d, honk, t, i)
        if cage_k is not None:  # 书罢笼鹅去
            x = gs[2][0] + dx if len(gs) > 2 else 110
            drop = ease_out_bounce(span(cage_k, 0.0, 1.8))
            lift = ease_in(span(cage_k, 2.6, 5.7))
            cy = lerp(-24, POND_Y + 2, drop) - lift * 60
            cage(g, x, cy)
            g.d.line((x, cy - 21, x, -1), fill=1)  # 吊绳
            g.d.rectangle((68, 50, 127, 63), fill=0)
            typewriter(g, 68, 51, "书罢笼鹅去", cage_k, cps=3)
        return gs

    # ------------------------------------------------------------ 画面

    def brush_at(self, s: float, k: float):
        """笔尖位置：砚台 → 纸 → 写（跟随笔尖）→ 回砚台"""
        ix, iy = INK[0] - 2, INK[1] - 1
        cw = text_width("国", 12) * 4
        tip = (CHAR_XY[0] + cw * (0.3 + 0.4 * noise(k * 40, 0)), CHAR_XY[1] + 48 * k)
        if s < 0.6:
            p = ease_in_out(s / 0.6)
            return lerp(ix, CHAR_XY[0] + cw * 0.5, p), lerp(iy, CHAR_XY[1], p) - math.sin(p * math.pi) * 6
        if s < 4.0:
            return tip
        if s < 4.6:
            p = ease_in_out((s - 4.0) / 0.6)
            return lerp(tip[0], ix, p), lerp(tip[1], iy, p) - math.sin(p * math.pi) * 10
        return ix, iy - (2 if 4.7 < s < 5.0 else 0)  # 蘸墨

    def frame(self, g: Gfx, t: float, paper_h: float = 1.0, show_brush: bool = True, gdx: float = 0.0):
        li, ci, s = self.where(t)
        text = self.line(li)
        ch = text[ci]
        paper(g, paper_h)
        inkstone(g)
        k = span(s, 0.6, 4.0)
        if paper_h >= 1:
            fade = 1 - span(s, 5.0, 5.8)
            if k > 0 and fade > 0:
                brush_reveal(g, CHAR_XY[0], CHAR_XY[1], ch, k, size=12, scale=4)
                if fade < 1:
                    g.fade(fade, (PAPER[0] + 3, PAPER[1] + 3, PAPER[2] - 2, PAPER[3]))
            if ci == 6 and s > 4.4:  # 一句写完：盖“右军”印
                p = ease_out_bounce(span(s, 4.4, 4.9))
                sx, sy = PAPER[2] - 15, lerp(-18, PAPER[3] - 19, p)
                g.d.rectangle((sx, sy, sx + 10, sy + 16), fill=1)
                g.text(sx + 1, sy + 1, "右", size=8, fill=0)
                g.text(sx + 1, sy + 9, "军", size=8, fill=0)
        # 左边小字：本句已写好的
        done = ci + (1 if s > 5.4 else 0)
        if done:
            g.vtext(3, 3, text[:done], size=8)
            if s > 5.4 and s < 5.8:  # 新落的小字闪一下
                y = 3 + (done - 1) * 8
                g.invert((2, y - 1, 12, y + 7))
        gs = self.draw_geese(g, t, gdx)
        if show_brush:
            bx, by = self.brush_at(s, k)
            g.blit(BRUSH, bx - 3, by - BRUSH.h + 1)
        self.mx(g, t, s, k, gs)

    def mx(self, g: Gfx, t: float, s: float, k: float, gs):
        if 0.6 < s < 4.0:  # 写字：笔尖从上往下扫
            r = int(k * 8)
            for y in range(min(r, 8)):
                for x in range(8):
                    if rand(x + y * 8 + int(t // PER) * 64, 3) < 0.45:
                        g.mx[y, x] = True
            g.mx_set(int(3 + 2 * noise(k * 40, 0)), min(r, 7))
            return
        x0 = int(math.sin(t * 0.3) * 1.5)  # 鹅
        g.mx_blit(MX_GOOSE, x0, int(math.sin(t * 2) * 0.6))
        g.mx[7, :] = [(x + int(t * 3)) % 3 != 0 for x in range(8)]

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        h = ease_out(span(t, 0.0, 1.2))
        gdx = (1 - ease_out(span(t, 0.8, 2.4))) * 70
        self.frame(g, 0.0, paper_h=max(h, 0.02), show_brush=False, gdx=gdx)
        if t > 2.0:  # 笔落到砚台上
            p = ease_out_bounce(span(t, 2.0, 2.8))
            g.blit(BRUSH, INK[0] - 5, lerp(-20, INK[1] - 1 - BRUSH.h + 1, p))  # 与 brush_at(0) 同位
        if t < 2.0:
            g.mx[:] = False
            g.mx[7, :] = [x < t * 4 for x in range(8)]

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self.ht + t)
        iris(g, span(t, 0.0, self.T["exit"]), 60, 32)
        if t > 0.8:
            g.mx[:] = False
