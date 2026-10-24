"""求签（六十四卦签）。

庙里求签：跪在蒲团上，双手捧签筒前倾摇动，签子哗哗作响，其中一支越探越高，“啪”地跳出落地。
用“六十四卦签”的做法：签号 1–64 即文王卦序，只出本卦，无变爻。
画面：小道士跪拜 → 摇筒（筒身竹节、签条抖动、声线）→ 一支签跳出翻落、弹两下 →
签子带着灵光立起放大，签身上刻着签号 → 揭晓卦象。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.chars import Part, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import HEXAGRAMS
from .o_common import FLOOR, REVEAL, Base, arm, blit_center, floor, lines_of, rotated, speed_lines, star4

DAO_X = 22
SHAKE = (0.65, 2.8)
POP, LAND = 2.8, 3.25
BIG = 3.75
R0 = 5.1
N_STICK = 7
PICK = 4
STICK_X = 90


def _tube():
    """签筒 11×19：口沿、两道竹节、贴签纸、右侧背光网点、圆底"""
    p = Part(11, 19)
    p.shape("rectangle", (0, 0, 10, 1), fill=1)
    p.d.line((1, 1, 9, 1), fill=0)
    p.shape("rectangle", (1, 2, 9, 17), fill=1)
    p.shape("rectangle", (2, 18, 8, 18), fill=1)
    for y in (6, 13):                         # 竹节：微微鼓出 + 一道阴线
        p.px(0, y), p.px(10, y)
        p.d.line((1, y + 1, 9, y + 1), fill=0)
    p.d.rectangle((3, 8, 6, 12), fill=0)      # 签纸
    p.px(4, 9), p.px(5, 9), p.px(4, 11)
    p.dither((7, 2, 9, 17), 0.5, 0)
    p.d.line((2, 3, 2, 5), fill=0)            # 高光边的竹纹
    return p.sprite()


def _stick():
    """落地的签 23×3：签头一段黑漆（暗）"""
    p = Part(23, 3)
    p.shape("rectangle", (0, 0, 22, 2), fill=1)
    p.d.line((1, 1, 17, 1), fill=0)
    p.shape("rectangle", (18, 0, 22, 2), fill=1)
    p.px(19, 1, 0), p.px(21, 1, 0)
    return p.sprite()


def _big():
    """放大的签 15×50：圆头、签头漆带（网点）、刻字框"""
    p = Part(15, 50)
    p.shape("rounded_rectangle", (0, 0, 14, 49), 5, fill=1)
    p.d.line((2, 9, 12, 9), fill=0)
    p.dither((1, 1, 13, 8), 0.5, 0)
    p.d.rectangle((2, 11, 12, 47), outline=0)
    p.px(3, 12, 0), p.px(11, 12, 0), p.px(3, 46, 0), p.px(11, 46, 0)
    p.d.line((13, 12, 13, 46), fill=0)
    return p.sprite()


def _cushion():
    p = Part(26, 5)
    p.shape("ellipse", (0, 0, 25, 4), fill=1)
    p.d.line((3, 2, 22, 2), fill=0)
    p.dither((14, 0, 25, 4), 0.5, 0)
    return p.sprite()


SPR = {}


def spr(name):
    if not SPR:
        SPR.update(tube=_tube(), stick=_stick(), big=_big(), cushion=_cushion())
    return SPR[name]


def window(g: Gfx):
    """背墙上的圆窗（冰裂纹窗格）"""
    cx, cy, r = 98, 22, 15
    g.d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), outline=1)
    g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
    for (x0, y0), (x1, y1) in (((-15, -2), (-4, -6)), ((-4, -6), (3, -15)), ((-4, -6), (6, 2)), ((6, 2), (15, -3)),
                               ((6, 2), (2, 15)), ((-4, -6), (-9, 12)), ((6, 2), (12, 10)), ((3, -15), (10, -8))):
        g.d.line((cx + x0, cy + y0, cx + x1, cy + y1), fill=1)
    g.d.line((0, 44, 127, 44), fill=1)  # 墙裙
    for x in range(8, 128, 24):
        g.d.line((x, 45, x, 47), fill=1)


@register
class QianOmen(Base):
    id = "o.qian"
    name = "求签"
    desc = "小道士跪在蒲团上摇签筒，签子哗哗抖动，一支跳出翻落；立起放大现出签号，第几签即第几卦"
    T = {"play": R0 + REVEAL}

    def init(self):
        self.n = self.rng.randint(1, 64)
        name, up, lo = HEXAGRAMS[self.n - 1]
        self.lines = lines_of(up, lo)
        self.lens = [7 + int(rand(k, self.seed) * 5) for k in range(N_STICK)]

    def tube(self, g: Gfx, px: float, py: float, deg: float, t: float, rise: float, picked: bool):
        """签筒：底部在 (px, py)，deg 为前倾角（正 = 向右倾）。先画签条，再画筒"""
        a = math.radians(deg)
        ux, uy = math.sin(a), -math.cos(a)           # 筒轴（向上）
        vx, vy = math.cos(a), math.sin(a)            # 横向
        mx, my = px + ux * 18, py + uy * 18          # 筒口
        jig = t > SHAKE[0] and t < SHAKE[1]
        for k in range(N_STICK):
            if k == PICK and picked:
                continue
            off = (k - (N_STICK - 1) / 2) * 1.3
            L = self.lens[k] + (noise(t * 14, k) * 2.5 if jig else 0)
            if k == PICK:
                L += rise * 12
            bx, by = mx + vx * off, my + vy * off
            ex, ey = bx + ux * L + vx * off * 0.25, by + uy * L + vy * off * 0.25
            g.d.line((bx, by, ex, ey), fill=1)
            if k == PICK and rise > 0.2:  # 被摇出的那支：签头漆带 + 微光
                g.d.rectangle((ex - 1, ey - 1, ex + 1, ey + 1), fill=1)
                if int(t * 10) % 2 == 0:
                    star4(g, ex + 3, ey - 3, 1)
        s = rotated(spr("tube"), -deg, 5)
        cx, cy = px + ux * 9.5, py + uy * 9.5
        blit_center(g, s, cx, cy)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        if t < BIG:
            window(g)
        floor(g, "tile")
        pix.blit(g, spr("cushion"), DAO_X - 13, FLOOR - 4)
        # ---------------- 小道士 + 签筒
        shaking = SHAKE[0] <= t < SHAKE[1]
        deg = 0.0
        if shaking:
            ramp = span(t, SHAKE[0], SHAKE[0] + 0.3)
            deg = (20 + math.sin((t - SHAKE[0]) * 2 * math.pi * 3.2) * 10) * ramp
        elif SHAKE[1] <= t < POP + 0.25:
            deg = lerp(48, 0, ease_out(span(t, POP, POP + 0.25)))  # 最后一下猛顿
        rise = ease_in(span(t, 1.1, SHAKE[1]))
        picked = t >= POP
        a, at = arm("lift")
        if t < 0.45:  # 先跪拜，签筒立在身前
            figure(g, DAO_X, FLOOR, t, legs="kneel", arm="gong", head="bow" if t > 0.12 else "up")
            self.tube(g, DAO_X + 17, FLOOR - 1, 0, t, 0, False)
        elif t < R0:
            put_down = t > LAND + 0.2
            if not put_down:
                face = "wow" if POP <= t < LAND + 0.2 else "normal"
                h = figure(g, DAO_X, FLOOR, t, legs="kneel", arm=a, arm_at=(at[0] + 1, at[1] - 2 + (1 if shaking and int(t * 20) % 2 else 0)),
                           face=face, bob=not shaking)["hand"]
                self.tube(g, h[0] + 3, h[1] + 3, deg, t, rise, picked)
                if shaking:
                    speed_lines(g, h[0] + 9, h[1] - 12, 1, t)
            else:
                bowing = BIG + 0.5 < t < BIG + 0.9
                figure(g, DAO_X, FLOOR, t, legs="kneel", arm="gong", head="bow" if bowing else "up",
                       face="happy" if t > BIG else "wow")
                self.tube(g, 7, FLOOR - 1, 0, t, 0, True)
        else:
            figure(g, DAO_X, FLOOR, t, legs="kneel", arm="gong", head="bow" if 0.4 < t - R0 < 1.0 else "up",
                   face="happy")
            self.tube(g, 7, FLOOR - 1, 0, t, 0, True)
        # ---------------- 跳出的签
        if POP <= t < BIG + 0.4:
            q = span(t, POP, LAND)
            sx0, sy0 = DAO_X + 36, FLOOR - 50
            if q < 1:
                x = lerp(sx0, STICK_X, q)
                y = lerp(sy0, FLOOR - 2, ease_in(q)) - math.sin(q * math.pi) * 10
                blit_center(g, rotated(spr("stick"), 70 + q * 560, 15), x, y)
            else:
                b = t - LAND
                h = 0
                if b < 0.14:
                    h = math.sin(b / 0.14 * math.pi) * 5
                elif b < 0.24:
                    h = math.sin((b - 0.14) / 0.1 * math.pi) * 2
                deg2 = 12 if b < 0.14 else 0
                grow = span(t, BIG - 0.3, BIG + 0.1)
                if grow <= 0:
                    blit_center(g, rotated(spr("stick"), deg2, 6), STICK_X, FLOOR - 2 - h)
                    if b > 0.3 and int(t * 8) % 2 == 0:  # 灵光
                        star4(g, STICK_X - 12 + rand(int(t * 8), 3) * 24, FLOOR - 6 - rand(int(t * 8), 5) * 6, 1)
                else:  # 立起：横签转竖、飞升
                    s = rotated(spr("stick"), 90 * ease_out(grow), 15)
                    blit_center(g, s, STICK_X, lerp(FLOOR - 2, 30, ease_out(grow)))
            if self.hit(t, LAND):
                self.impact(g, STICK_X, FLOOR - 1, 1.2)
                pix.shake(g, t, 2.0)
            elif LAND < t < LAND + 0.1:
                pix.shake(g, t, 1.0)
        if t >= POP and self.hit(t, POP):
            self.sparks.burst(DAO_X + 36, FLOOR - 50, 8, 30, up=10, life=0.4, gravity=60)
        big_on = BIG <= t < R0
        if big_on:  # 放大的签，刻着签号
            p = ease_out_back(span(t, BIG, BIG + 0.3))
            s = pix.stretch(spr("big"), max(p, 0.1), max(p, 0.1))
            bx, by = STICK_X, 31 + round(math.sin((t - BIG) * 4))
            blit_center(g, s, bx, by)
            if self.hit(t, BIG):
                pix.flash(g)
                self.sparks.burst(bx, by, 16, 40, life=0.6, gravity=20)
            if p > 0.95:
                for j in range(6):  # 一圈放射光
                    ang = j / 6 * math.pi * 2 + t * 1.5
                    r0 = 30 + (t * 20 + j * 3) % 6
                    g.px(bx + math.cos(ang) * r0 * 0.8, by + math.sin(ang) * r0 * 0.9)
                num = cn_num(self.n)
                self.say_v(bx - 6, by - 18 + (3 - len(num)) * 6, num)
        self.particles(g)
        # ---------------- 点阵
        if t < R0:
            if t < POP:  # 前倾摇动的签筒
                sh = 1 if shaking and math.sin((t - SHAKE[0]) * 2 * math.pi * 3.2) > 0 else 0
                for r in range(3, 8):
                    c = 2 + sh * (7 - r) // 3
                    g.mx[r, c] = g.mx[r, c + 3] = True
                g.mx[7, 2 + sh: 6 + sh] = True
                for k, c in enumerate((3, 4)):
                    g.mx[2 - (1 if k == 1 and rise > 0.5 else 0), c + sh] = True
            elif t < BIG:
                g.mx[6, 1:7] = True
                g.mx[6, 6] = int(t * 8) % 2 == 0
            else:
                g.mx[0:8, 3:5] = True
                g.mx[1:3, 3:5] = False
                g.mx[0, 3] = g.mx[0, 4] = True
            g.mx_level = 6 if LAND <= t < LAND + 0.1 or BIG <= t < BIG + 0.15 else 1
        else:
            self.reveal(g, t, R0)
        self.flush(g)
