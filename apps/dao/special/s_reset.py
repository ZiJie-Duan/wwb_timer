"""天地重开：芯片清零时播放，约 5.6 秒。

依据：《道德经》二十五章“有物混成，先天地生”；《三五历纪》“天地混沌如鸡子，盘古生其中……
阳清为天，阴浊为地”。

画面：白光满屏（清零）→ 网点褪去 → 混沌如鸡子：一只大蛋，里面气点打着旋，小道士蜷坐其中酣睡，
左右竖排“有物混成”“先天地生” → 小道士惊醒，抽出一柄大斧高举 → 一斧劈下：闪白、狂震、裂纹横贯，
蛋分上下：上半轻清飞升化作满天星斗，下半重浊下沉化作群山大地，火星四溅；小道士双手撑天（盘古），
左右竖排“阳清为天”“阴浊为地” → 星辰闪烁、祥云飘过，顶上两倍大的毛笔字写出“天地重开”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, lerp, noise, rand, span
from ..engine.chars import figure
from ..engine.fx import stars, xiangyun
from ..engine.gfx import Gfx, text_image
from ..engine.scene import Special, register
from ..omens.o_common import FLOOR, Stage, arm, floor, star4

CX, CY, RX, RY = 64, 30, 22, 27
FADE = 0.45
WAKE = 2.1
RAISE = 2.4
CUT = 2.8
SPLIT = (2.8, 3.7)
TITLE = (3.95, 4.9)
RIDGE = [(0, 47), (10, 42), (20, 45), (32, 38), (44, 44), (54, 41), (64, 46), (76, 40), (90, 45), (102, 37),
         (116, 43), (128, 40)]
N = 70


def ridge_y(x: float) -> float:
    for (x0, y0), (x1, y1) in zip(RIDGE, RIDGE[1:]):
        if x0 <= x <= x1:
            return lerp(y0, y1, (x - x0) / (x1 - x0))
    return 45


def crack_pts(dy: float = 0.0):
    """横贯蛋身的裂纹（锯齿）"""
    pts = []
    for k in range(9):
        x = CX - RX + k * RX * 2 / 8
        y = CY + (2 if k % 2 else -2) + dy
        pts.append((x, y))
    return pts


def axe(g: Gfx, hx: float, hy: float, up: bool):
    """大斧：斧柄 + 月牙斧刃（刃口一道亮边）"""
    if up:  # 高举：柄向上，刃朝前
        g.d.line((hx, hy + 2, hx + 1, hy - 10), fill=1, width=2)
        bx, by = hx + 2, hy - 10
        g.d.polygon([(bx, by - 3), (bx + 7, by - 6), (bx + 9, by), (bx + 7, by + 5), (bx, by + 3)], fill=1)
        g.d.line((bx + 1, by - 2, bx + 1, by + 2), fill=0)
        g.d.arc((bx + 3, by - 6, bx + 11, by + 6), 290, 70, fill=0)
    else:   # 劈下：柄向前下，刃朝下
        g.d.line((hx - 2, hy - 1, hx + 10, hy + 2), fill=1, width=2)
        bx, by = hx + 10, hy + 2
        g.d.polygon([(bx - 3, by), (bx - 6, by + 7), (bx, by + 9), (bx + 5, by + 7), (bx + 3, by)], fill=1)
        g.d.line((bx - 2, by + 1, bx + 2, by + 1), fill=0)


@register
class Reset(Stage, Special):
    id = "s.reset"
    name = "天地重开"
    desc = "混沌如鸡子，小道士蜷睡其中；惊醒抽斧一劈，蛋分上下：轻清上升为满天星，重浊下沉为群山，小道士撑天，书“天地重开”"
    T = {"play": 5.6}

    def setup(self):
        self.stage_init()
        r = self.rng
        self.dots = [(r.random() * 2 * math.pi, 4 + r.random() * 16, 0.8 + r.random() * 1.6, r.random() < 0.5)
                     for _ in range(N)]

    def egg_shell(self, g: Gfx, dy_top: float = 0.0, dy_bot: float = 0.0, split: bool = False):
        """蛋壳：双线 + 几处斑点；split 时分成上下两半各自平移"""
        box = (CX - RX, CY - RY, CX + RX, CY + RY)
        inner = (CX - RX + 2, CY - RY + 2, CX + RX - 2, CY + RY - 2)
        if not split:
            g.d.ellipse(box, outline=1)
            g.d.ellipse(inner, outline=1)
            for a in (0.6, 2.2, 4.0, 5.2):
                g.px(CX + math.cos(a) * (RX - 1), CY + math.sin(a) * (RY - 1))
            return
        for top, dy in ((True, dy_top), (False, dy_bot)):
            b = (box[0], box[1] + dy, box[2], box[3] + dy)
            ib = (inner[0], inner[1] + dy, inner[2], inner[3] + dy)
            a0, a1 = (180, 360) if top else (0, 180)
            g.d.chord(b, a0, a1, fill=0, outline=1)
            g.d.arc(ib, a0, a1, fill=1)
            pts = crack_pts(dy)
            g.d.line(pts, fill=1)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        # ---------------- 白光满屏 → 网点褪去
        if t < FADE:  # 白光满屏，中间一个黑洞张开（光圈）
            g.d.rectangle((0, 0, 127, 63), fill=1)
            r = ease_in(span(t, 0.12, FADE)) * 80
            if r > 0:
                g.d.ellipse((CX - r, CY - r * 0.8, CX + r, CY + r * 0.8), fill=0)
        split = span(t, SPLIT[0], SPLIT[1])
        world = span(t, SPLIT[0] + 0.3, SPLIT[1] + 0.3)
        # ---------------- 新天地：星辰、群山、祥云
        if world > 0:
            n = int(28 * world)
            stars(g, t, seed=11, n=n, box=(0, 0, 128, 36))
            rise = (1 - ease_out(world)) * 18
            pts = [(x, y + rise) for x, y in RIDGE] + [(128, FLOOR), (0, FLOOR)]
            g.d.polygon(pts, fill=0, outline=1)
            for (x0, y0), (x1, y1) in zip(RIDGE, RIDGE[1:]):  # 山的阴面：几道短斜线
                if y1 < y0:
                    for k in range(2):
                        sx = x1 + 2 + k * 3
                        g.d.line((sx, y1 + rise + 3 + k * 2, sx + 2, y1 + rise + 7 + k * 2), fill=1)
            floor(g, "earth")
            if t > TITLE[0]:
                for k, (x0, y0, sp) in enumerate(((10, 34, 5), (96, 31, 4))):
                    xiangyun(g, (x0 + (t - TITLE[0]) * sp) % 140 - 6, y0, 0.7, flip=k == 1)
        # ---------------- 混沌之卵
        if t < SPLIT[1] + 0.1:
            shake_egg = (math.sin(t * 60) * 1 if WAKE < t < CUT else 0)
            if split <= 0:
                g.d.ellipse((CX - RX + shake_egg, CY - RY, CX + RX + shake_egg, CY + RY), fill=0)
            else:
                pass
            # 气点：打旋（醒来后越转越急）；劈开后清者上升、浊者下沉
            spd = 1 + 3 * span(t, WAKE, CUT)
            for a0, r, w, light in self.dots:
                if split <= 0:
                    a = a0 + t * w * spd * (1.5 - r / 20)
                    x = CX + math.cos(a) * r + shake_egg
                    y = CY - 4 + math.sin(a) * r * 1.15
                else:
                    a = a0 + CUT * w * spd * (1.5 - r / 20)
                    x = CX + math.cos(a) * r * (1 + split * 1.5)
                    y0 = CY - 4 + math.sin(a) * r * 1.15
                    y = y0 - ease_in(split) * 60 if light else y0 + ease_in(split) * 30
                if 0 <= y < 64:
                    g.px(x, y)
            if split <= 0:
                self.egg_shell(g)
            else:
                self.egg_shell(g, -ease_in(split) * 70, ease_in(split) * 40, split=True)
        # ---------------- 小道士（盘古）
        stand_y = CY + RY - 3
        if t < WAKE:
            figure(g, CX, stand_y, t, legs="sit", arm="gong", head="bow", face="sleep")
            if int(t * 2) % 2 == 0 and t > 0.6:  # 鼾声小泡
                r = 1 + (t * 2) % 1 * 2
                g.d.ellipse((CX + 9, stand_y - 33 - r * 2, CX + 9 + r, stand_y - 33 - r), outline=1)
        elif t < RAISE:
            hop = math.sin(span(t, WAKE, WAKE + 0.2) * math.pi) * 3
            figure(g, CX, stand_y - hop, t, legs="sit", arm="gong", face="wow")
        elif t < CUT:  # 高举大斧
            h = figure(g, CX - 4, stand_y, t, arm="raise", face="normal", bob=False)["hand"]
            axe(g, h[0], h[1], True)
        elif t < SPLIT[1]:  # 劈下 → 撑天
            land = stand_y + (FLOOR - stand_y) * ease_in(span(t, CUT + 0.2, CUT + 0.5))
            if t < CUT + 0.3:
                a, at = arm("reach")
                h = figure(g, CX - 4, land, t, arm=a, arm_at=at, face="wow", bob=False)["hand"]
                axe(g, h[0], h[1], False)
            else:
                figure(g, CX, land, t, arm="raise", face="wow")
                figure(g, CX, land, t, arm="raise", face="wow", flip=True)
        else:
            if t < TITLE[0] + 0.4:
                figure(g, CX, FLOOR, t, arm="raise", face="happy")
                figure(g, CX, FLOOR, t, arm="raise", face="happy", flip=True)
            else:
                figure(g, CX, FLOOR, t, arm="gong", face="happy", head="bow" if t > TITLE[1] + 0.2 else "up")
        # ---------------- 劈
        if self.hit(t, CUT):
            pix.flash(g)
            for x, y in crack_pts()[1:-1:2]:
                self.sparks.burst(x, y, 6, 40, life=0.6, gravity=40)
        if CUT <= t < CUT + 0.35:
            pix.shake(g, t, 3 * (1 - span(t, CUT, CUT + 0.35)))
        if CUT - 0.05 <= t < CUT + 0.1:  # 斧光：一道横光
            q = span(t, CUT - 0.05, CUT + 0.05)
            g.d.line((CX - RX - 6, CY, CX - RX - 6 + (RX * 2 + 12) * q, CY), fill=1, width=2)
        if self.hit(t, SPLIT[0] + 0.55):
            self.puffs.emit(CX - 14, FLOOR - 2, vx=-14, vy=-5, life=0.6, rmax=2)
            self.puffs.emit(CX + 14, FLOOR - 2, vx=14, vy=-5, life=0.6, rmax=2)
            pix.shake(g, t, 1.5)
        self.particles(g)
        # ---------------- 字（最后画）
        if FADE <= t < CUT:
            self.say_v(5, 7, "有物混成")
            self.say_v(111, 7, "先天地生")
        elif SPLIT[0] + 0.2 <= t < TITLE[0]:
            self.say_v(5, 7, "阳清为天")
            self.say_v(111, 7, "阴浊为地")
        self.flush(g)
        if t >= TITLE[0]:
            p = span(t, *TITLE)
            x0 = 64 - (4 * 24 + 6) / 2
            g.d.rectangle((x0 - 3, 0, x0 + 4 * 26 + 2, 24), fill=0)  # 字的黑底
            for i, ch in enumerate("天地重开"):  # 毛笔逐字写：写完的字用 g.text，正在写的字自上而下露出、笔尖跟着走
                k = min(1.0, max(0.0, (p - i / 4) * 4))
                if k <= 0:
                    break
                cx = x0 + i * 26
                if k >= 1:
                    g.text(cx, 1, ch, scale=2)
                else:
                    gl = text_image(ch, 12, 2)
                    cut = max(1, int(24 * k))
                    g.img.paste(1, (int(cx), 1), gl.crop((0, 0, gl.width, cut)))
                    tip = cx + 24 * (0.3 + 0.4 * noise(p * 40, i))
                    g.d.rectangle((tip, cut - 1, tip + 1, cut), fill=1)
            if p >= 1 and int(t * 5) % 2 == 0:
                star4(g, x0 - 7, 6, 2)
                star4(g, x0 + 4 * 26 + 6, 18, 2)
        # ---------------- 点阵
        if t < FADE:
            g.mx[:] = True if t < 0.2 else False
            if t >= 0.2:
                for y in range(8):
                    for x in range(8):
                        g.mx[y, x] = rand(x + y * 8, int(t * 20)) < 1 - span(t, 0.2, FADE)
        elif t < CUT:  # 混沌：噪点旋转
            for y in range(8):
                for x in range(8):
                    g.mx[y, x] = noise(t * 6 + x * 0.7 + y * 1.3, x * 8 + y) > 0.62
        elif t < SPLIT[1]:
            k = span(t, CUT, SPLIT[1])
            for y in range(8):
                for x in range(8):
                    if y < 4:
                        g.mx[y, x] = rand(x + y * 8, int(t * 12)) < 0.5 * (1 - k) + 0.1
                    else:
                        g.mx[y, x] = rand(x + y * 8, int(t * 12) + 5) < 0.5 + k * 0.5
        else:
            g.mx[5:8] = True
            for i in range(6):
                x, y = int(rand(i, 3) * 8), int(rand(i, 4) * 4)
                g.mx[y, x] = noise(t * 2 + i, i) > 0.35
        g.mx_level = 8 if CUT <= t < CUT + 0.15 else 1
