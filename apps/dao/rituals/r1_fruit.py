"""供果：神龛前的供桌上一只高脚果盘，小道士一颗一颗把寿桃、蜜橘码成果塔；麻雀来偷吃，被剑指吓飞。

依据：五供（香、花、灯、水、果）之果；道教供献也称“五献”，汉典引道士语“五献皆圆满，奉上众真前”。
供果常用桃（寿）、橘（吉），码成塔形（底四、三、二、塔尖一颗带叶寿桃）。

入场：神龛帐幔、供桌、烛台渐次就位，高脚果盘“咚”地落在桌上弹两下；小道士提着果篮走来放在身后，拱手。
持续：一轮 600 秒，每 60 秒放一颗：转身从篮里拿果 → 走到桌前 → 托手一送，果子跳上果塔，落下时压扁一弹、
      闪一下 → 拱手 → 走回。共十颗（桃橘由 seed 定，塔尖是带叶寿桃）。烛火跳动，帐幔流苏轻摆。
      每隔一阵一只麻雀跳上桌角，啄啄脑袋想偷果，小道士吃一惊，剑指一点，麻雀扑棱棱飞走；作揖。
      续：神明享供——果子从塔尖起一颗颗化作光点升起，小道士跪拜，盘空了再从第一颗放起，“第几盘”加一。
中断：一只纱罩从上方落下罩住果塔（弹两下），牌子“暂歇”。  恢复：纱罩被提起飞走，果塔一闪。
圆满：没放满的果子一颗接一颗跳上去补齐，塔尖寿桃放光，小道士跪拜，闪白，“五献皆圆满”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import FLOOR, Clock, badge, floor, hit, mx_burst, pose_arm, ring_dots, star, title, twinkles

TABLE = (60, 124, 41)       # 供桌 x0, x1, 桌面 y
PX = 92                     # 果盘中心
PLATE_Y = 35                # 盘面 y
DX = 36                     # 小道士站位
STAND_X = 70                # 放果时站的位置
BASKET_X = 14
STEP = 60.0
PLACE = 8.0                 # 每段第 8 秒开始放果（避开“续”的表演）
RENEW = 7.0

# 果塔里十颗的位置（底四、三、二、一），相对盘面中心；塔尖是寿桃
SLOTS = [(-12, 0), (-4, 0), (4, 0), (12, 0), (-8, -6), (0, -6), (8, -6), (-4, -12), (4, -12), (0, -18)]

CANDLE_FLAME = pix.frames("""
 #
 #
###
#.#
---
  #
 #
###
#.#
---
 #
##
###
#.#
""")

SPARROW = pix.frames("""
  .##.
 ##.###
.######.
 .####
  #  #
---
  .##.
 ##.###
.######.
 .####
  #  #
---
     .
  .##.
 ##.###.
.######
 .####
  #  #
""")

SPARROW_PECK = pix.sprite("""
     .
  .###.
 ##.####
.#####..
 .###
  #  #
""")

SPARROW_FLY = pix.frames("""
#.  .#
.#..#.
 .###.
.#####.
 ##.##
---
 .###.
.#####.
##.#.##
#.  .#
""")


PEACH = pix.sprite("""
##  #
.#####
 ##.##
 ##.###
####.###
####.###
###.###.
.##.##.#
 .###.#.
  .#.#.
""")

ORANGE = pix.sprite("""
   #.##
  ######
 ########
##.######
#.######.
#######.#
.#####.#.
 .#.#.#.
""")

SMALL_PEACH = pix.sprite("""
   #
  ###
 ##.##
###.###
###.###
##.###.
.##.#.#
 .#.#.
""")


def _plate():
    """高脚果盘 33×8：盘沿联珠、盘腹（右侧背光）、细柄、圈足"""
    rows = [
        "#################################",
        "#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#.#",
        " ##########################.#.#. ",
        "   #####################.#.#.#   ",
        "        ##############.#.        ",
        "             ###.#               ",
        "             ##.##               ",
        "          ###########            ",
    ]
    return pix.sprite("\n".join(rows))


def _basket():
    """果篮 17×7（篮里堆着果子）"""
    p = Part(17, 9)
    for x in (2, 6, 10):
        p.shape("ellipse", (x, 0, x + 5, 5), fill=1)
        p.px(x + 1, 2, 0)
    p.shape("polygon", [(0, 3), (16, 3), (14, 8), (2, 8)], fill=1)
    p.d.line((1, 4, 15, 4), fill=0)
    for x in range(3, 15, 3):
        p.d.line((x, 5, x + 1, 7), fill=0)
    return p.sprite()


def _cover():
    """纱罩 27×22：竹骨圆顶 + 纱网网点 + 顶钮"""
    p = Part(27, 23)
    p.shape("rectangle", (12, 0, 14, 2), fill=1)
    p.shape("ellipse", (0, 2, 26, 40), fill=1)
    p.dither((1, 3, 25, 22), 0.25, 0)
    p.dither((2, 4, 24, 22), 0.5, 0)
    for x in (6, 13, 20):
        p.d.line((13, 3, x, 22), fill=1)
    p.shape("rectangle", (0, 21, 26, 22), fill=1)
    return p.sprite()


_P: dict = {}


def P(name):
    if name not in _P:
        _P[name] = {"peach": lambda: PEACH, "orange": lambda: ORANGE, "speach": lambda: SMALL_PEACH, "plate": _plate,
                    "basket": _basket, "cover": _cover}[name]()
    return _P[name]


def slot_xy(i: int):
    dx, dy = SLOTS[i]
    if i == 9:
        return PX + dx - 4, PLATE_Y - 10 + dy + 7
    return PX + dx - 4, PLATE_Y - 8 + dy


# ---------------------------------------------------------------- 背景

def shrine(g: Gfx, t: float):
    """神龛：顶上帐幔（波浪边 + 流苏）、两侧束起的帐子、供桌（桌围回纹）、两只烛台"""
    floor(g)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    g.d.rectangle((0, 0, 127, 2), fill=1)
    for x in range(0, 128, 8):       # 波浪边帐幔
        g.d.chord((x, -3, x + 8, 6), 0, 180, fill=1)
        g.d.arc((x + 1, -2, x + 7, 4), 0, 180, fill=0)
        if abs(x + 4 - PX) > 12:
            sw = round(math.sin(t * 1.6 + x * 0.3) * 0.6)
            g.d.line((x + 4 + sw, 7, x + 4 + sw, 9), fill=1)
            g.px(x + 3 + sw, 9), g.px(x + 5 + sw, 9)
    x0, x1, ty = TABLE
    g.d.rectangle((x0, ty, x1, ty + 2), fill=1)
    g.d.line((x0 + 1, ty + 1, x1 - 1, ty + 1), fill=0)
    g.d.rectangle((x0 + 3, ty + 3, x1 - 3, FLOOR - 1), outline=1, fill=0)
    for x in range(x0 + 6, x1 - 5, 6):     # 回纹带
        g.d.line((x, ty + 5, x + 3, ty + 5), fill=1)
        g.d.line((x + 3, ty + 5, x + 3, ty + 7), fill=1)
        g.d.line((x + 1, ty + 7, x + 3, ty + 7), fill=1)
    pix.checker(g, (x0 + 4, ty + 9, x1 - 3, FLOOR - 1), 0.125)
    for k, x in enumerate((x0 + 4, x1 - 4)):
        g.d.rectangle((x - 1, ty - 9, x + 1, ty - 3), fill=1)
        g.px(x + 1, ty - 7, 0)
        g.d.rectangle((x - 3, ty - 2, x + 3, ty - 2), fill=1)
        g.d.rectangle((x - 2, ty - 1, x + 2, ty - 1), fill=1)
        pix.blit(g, pix.anim(CANDLE_FLAME, t + k * 0.37, 7), x - 1, ty - 14, outline=False)


def pyramid(g: Gfx, n: float, kinds, t: float, land_i: int = -1, land_k: float = 1.0, glow=None):
    """盘 + 已码好的果子（n 颗）。land_i 正在跳上来的那颗：land_k 0..1"""
    pix.blit(g, P("plate"), PX - 16, PLATE_Y)
    for i in range(int(n)):
        x, y = slot_xy(i)
        spr = P("peach") if i == 9 else P(kinds[i])
        if glow is not None and glow[i] <= 0:
            continue
        if glow is not None and glow[i] < 1:   # 化作光点：缩小
            s = max(0.2, glow[i])
            spr = pix.stretch(spr, s, s)
            x += (1 - s) * 3
            y += (1 - s) * 4
        pix.blit(g, spr, x, y)


def hop(g: Gfx, i: int, kinds, q: float, sx: float, sy: float):
    """第 i 颗从 (sx, sy) 沿弧线跳到位置上；落地压扁再弹回"""
    tx, ty = slot_xy(i)
    spr = P("peach") if i == 9 else P(kinds[i])
    if q < 0.7:
        k = q / 0.7
        x, y = lerp(sx, tx, k), lerp(sy, ty, k) - math.sin(k * math.pi) * 14
        pix.blit(g, spr, x, y)
    else:
        k = (q - 0.7) / 0.3
        sq = 1 - 0.35 * math.sin(k * math.pi)
        s2 = pix.stretch(spr, 2 - sq, sq)
        pix.blit(g, s2, tx - (s2.w - spr.w) / 2, ty + spr.h - s2.h)


def mx_fruit(g: Gfx, n: int, t: float, cover: bool = False, blink_last: bool = True):
    """点阵：盘 + 果塔，最新一颗闪"""
    g.mx[7, 1:7] = True
    g.mx[6, 3:5] = True
    cells = [(5, 0), (5, 2), (5, 4), (5, 6), (4, 1), (4, 3), (4, 5), (3, 2), (3, 4), (1, 3)]
    for i in range(min(n, 10)):
        y, x = cells[i]
        on = not (blink_last and i == n - 1 and int(t * 3) % 2)
        g.mx[y, x] = g.mx[y, x + 1] = on
        if i == 9:
            g.mx[2, 3:5] = on
    if cover:
        g.mx[0, 1:7] = True
        g.mx[1:6, 0] = g.mx[1:6, 7] = True


# ---------------------------------------------------------------- 场景

@register
class FruitOffering(Ritual):
    id = "r1.fruit"
    name = "供果"
    desc = "小道士一颗颗把寿桃蜜橘托上高脚果盘码成果塔，麻雀来偷吃被剑指吓飞；一轮后神明享供，果化光点升起"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 1.6, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.kinds = ["orange" if self.rng.random() < 0.5 else "speach" for _ in range(9)] + ["peach"]

    def count(self, e: float) -> int:
        """已经放好的颗数（e 的函数）"""
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return 0
        return min(10, int(k / STEP) + (1 if k % STEP >= PLACE + 3.0 else 0))

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        badge(g, 4, 5, label or (f"第{cn_num(n)}盘" if n < 100 else f"{n}盘"))

    def basket(self, g: Gfx, full: bool = True):
        pix.blit(g, P("basket"), BASKET_X - 8, FLOOR - 9)

    def fx(self, g: Gfx, dt: float):
        self.sparks.step(dt)
        self.sparks.draw(g)

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        shrine(g, t)
        drop = ease_out_bounce(span(t, 0.2, 1.2))
        y = lerp(-12, PLATE_Y, drop)
        pix.blit(g, P("plate"), PX - 16, y)
        if hit(t, 0.62, dt):
            pix.shake(g, t, 1.0)
            self.sparks.burst(PX, PLATE_Y + 6, 8, 20, up=10, life=0.4, gravity=60)
        if t < 2.8:
            x = lerp(-14, DX, ease_out(span(t, 0.8, 2.8)))
            h = pose_arm(g, x, FLOOR, t, 30, legs="walk" if t < 2.8 else "stand")
            pix.blit(g, P("basket"), h["hand"][0] - 8, h["hand"][1] - 2)
        elif t < 3.4:
            self.basket(g)
            daoshi(g, DX, FLOOR, "idle", t, flip=True)
        else:
            self.basket(g)
            pose = "gongshou" if t < 4.2 else ("bow" if t < 4.9 else "idle")
            daoshi(g, DX, FLOOR, pose, t)
        if 2.8 <= t < 2.9:
            self.sparks.burst(BASKET_X, FLOOR - 4, 6, 14, up=8, life=0.3, gravity=60)
        self.fx(g, dt)
        if t > 3.4:
            self.counter(g, 0.0)
        mx_fruit(g, 0, t)

    # ------------------------------------------------------------ 持续

    def place(self, g: Gfx, t: float, u: float, i: int, dt: float):
        """u ∈ [0, 5]：拿果 → 走到桌前 → 托手一送（果子跳上塔）→ 拱手 → 走回。画小道士与手里的果"""
        spr = P("peach") if i == 9 else P(self.kinds[i])
        if u < 0.9:
            h = pose_arm(g, DX, FLOOR, t, 60 if u > 0.25 else 30, flip=True)
            if u > 0.55:
                pix.blit(g, spr, h["hand"][0] - spr.w // 2, h["hand"][1] - spr.h)
        elif u < 1.9:
            x = lerp(DX, STAND_X, ease_in_out(span(u, 0.9, 1.9)))
            h = pose_arm(g, x, FLOOR, t, 0, legs="walk", hand="open")
            pix.blit(g, spr, h["hand"][0] - spr.w // 2, h["hand"][1] - spr.h)
        elif u < 3.0:
            h = daoshi(g, STAND_X, FLOOR, "raise" if u < 2.6 else "offer", t)
            if u < 2.3:
                pix.blit(g, spr, h["hand"][0] - spr.w // 2, h["hand"][1] - spr.h)
            else:
                hop(g, i, self.kinds, span(u, 2.3, 3.0), STAND_X + 8, FLOOR - 40)
        elif u < 3.8:
            daoshi(g, STAND_X, FLOOR, "gongshou", t, face="happy")
        elif u < 4.8:
            x = lerp(STAND_X, DX, ease_in_out(span(u, 3.8, 4.8)))
            daoshi(g, x, FLOOR, "walk", t, flip=True)
        else:
            daoshi(g, DX, FLOOR, "idle", t)
        if hit(u, 3.0, dt):
            x, y = slot_xy(i)
            self.sparks.burst(x + 3, y + 3, 10, 22, up=10, life=0.5, gravity=50)

    def sparrow(self, g: Gfx, t: float, v: float):
        """麻雀（v ∈ [0, 6]）：跳上桌角 → 啄 → 被吓飞。返回小道士该做的动作"""
        land = (110, TABLE[2] - 5)
        if v < 0.8:
            q = ease_out(v / 0.8)
            x, y = lerp(132, land[0], q), lerp(10, land[1], q) - math.sin(q * math.pi) * 6
            pix.blit(g, pix.anim(SPARROW_FLY, t, 12), x, y)
        elif v < 3.9:
            peck = int(v * 3) % 2 == 0 and v > 1.4
            x = land[0] - int(span(v, 1.0, 2.2) * 2)
            pix.blit(g, SPARROW_PECK if peck else SPARROW[0], x, land[1] - (1 if peck else 0))
        else:
            q = ease_in(span(v, 3.9, 5.2))
            x, y = lerp(land[0] - 2, 140, q), lerp(land[1], -12, q)
            pix.blit(g, pix.anim(SPARROW_FLY, t, 14), x, y)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e, dt)
            return
        shrine(g, t)
        self.basket(g)
        i = int(k / STEP)
        u = k % STEP
        n = self.count(e)
        placing = i < 10 and PLACE <= u < PLACE + 5.0
        pyramid(g, n, self.kinds, t)
        odd = (i + self.seed) % 2
        if placing:
            self.place(g, t, u - PLACE, i, dt)
        else:
            c = u - (30 if odd else 40)
            if 0 <= c < 6:   # 麻雀
                self.sparrow(g, t, c)
                v = c
                if 1.6 <= v < 2.4:
                    daoshi(g, DX, FLOOR, "idle", t, face="wow")
                elif 2.4 <= v < 4.2:
                    h = daoshi(g, DX, FLOOR, "point", t)
                    q = span(v, 2.6, 3.9)
                    if 0 < q < 1:
                        hx, hy = h["hand"]
                        tx, ty = 110, TABLE[2] - 3
                        px, py = lerp(hx, tx, q), lerp(hy, ty, q) - math.sin(q * math.pi) * 12
                        g.d.ellipse((px - 1, py - 1, px + 1, py + 1), fill=1)
                        self.sparks.burst(px, py, 1, 5, life=0.3, gravity=0)
                    if 3.85 <= v < 3.95:
                        self.sparks.burst(111, TABLE[2] - 3, 8, 20, life=0.4, gravity=20)
                else:
                    daoshi(g, DX, FLOOR, "idle", t, face="happy" if v >= 4.2 else "normal")
            elif 52 <= u < 54.4:
                daoshi(g, DX, FLOOR, "gongshou" if u < 53.2 else "bow", t)
            else:
                daoshi(g, DX, FLOOR, "idle", t)
        if n >= 10:    # 供满：塔尖闪光
            tx, ty = slot_xy(9)
            twinkles(g, [(tx - 6, ty + 2), (tx + 13, ty), (tx - 3, ty - 4), (tx + 10, ty + 9)], t, 1.0)
        self.fx(g, dt)
        self.counter(g, e)
        mx_fruit(g, n, t)
        if placing and 3.0 <= u - PLACE < 3.2:
            g.mx_level = 5

    def _renew(self, g: Gfx, t: float, k: float, e: float, dt: float):
        """神明享供：果子从塔尖起化作光点升起"""
        shrine(g, t)
        self.basket(g)
        glow = []
        for i in range(10):
            j = 9 - i
            glow.append(1 - span(k, 0.6 + j * 0.35, 1.0 + j * 0.35))
        pyramid(g, 10, self.kinds, t, glow=glow)
        for i in range(10):     # 升起的光点
            j = 9 - i
            q = span(k, 0.9 + j * 0.35, 2.6 + j * 0.35)
            if 0 < q < 1:
                x, y = slot_xy(i)
                yy = y + 3 - q * 40
                star(g, x + 3 + math.sin(q * 9 + i) * 2, yy, 1 if q < 0.7 else 0)
        pose = "kneel" if 0.5 < k < 5.2 else "idle"
        daoshi(g, DX, FLOOR, pose, t, face="happy" if k > 5.2 else "normal")
        if hit(k, 4.5, dt):
            self.sparks.burst(PX, PLATE_Y - 4, 12, 22, up=8, life=0.6, gravity=20)
        self.fx(g, dt)
        self.counter(g, e if k > 4.5 else e - k - 1)
        mx_fruit(g, sum(1 for v in glow if v > 0), t, blink_last=False)
        if 1 < k < 4.5:
            g.mx_set(int(k * 3) % 8, int(7 - (k * 8) % 8))

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        shrine(g, t)
        self.basket(g)
        n = self.count(e)
        pyramid(g, n, self.kinds, t)
        daoshi(g, DX, FLOOR, "gongshou" if t > 0.3 else "idle", t)
        drop = ease_out_bounce(span(t, 0.2, 1.1))
        cy = lerp(-24, PLATE_Y - 21, drop)
        pix.blit(g, P("cover"), PX - 13, cy)
        if hit(t, 0.62, dt):
            pix.shake(g, t, 1.0)
        self.fx(g, dt)
        self.counter(g, e, "暂歇" if t > 0.6 else None)
        mx_fruit(g, n, t, cover=t > 0.6, blink_last=False)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        shrine(g, t)
        self.basket(g)
        n = self.count(e)
        pyramid(g, n, self.kinds, t)
        daoshi(g, DX, FLOOR, "raise" if t < 0.9 else "idle", t, face="happy" if t > 0.9 else "normal")
        q = ease_in(span(t, 0.3, 1.1))
        pix.blit(g, P("cover"), PX - 13 + q * 30, lerp(PLATE_Y - 21, -30, q))
        if hit(t, 0.5, dt):
            self.sparks.burst(PX, PLATE_Y - 8, 12, 24, up=6, life=0.5, gravity=30)
        self.fx(g, dt)
        self.counter(g, e)
        mx_fruit(g, n, t, cover=t < 0.5)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        shrine(g, t)
        self.basket(g)
        n0 = self.count(e)
        missing = list(range(n0, 10))
        done = n0
        for j, i in enumerate(missing):   # 补齐：一颗接一颗跳上去
            t0 = 0.2 + j * 0.16
            q = span(t, t0, t0 + 0.5)
            if q >= 1:
                done = i + 1
            elif q > 0:
                hop(g, i, self.kinds, q, BASKET_X, FLOOR - 12)
        pyramid(g, done, self.kinds, t)
        pose = "raise" if t < 1.6 else ("kneel" if t < 4.6 else "idle")
        daoshi(g, DX, FLOOR, pose, t, face="happy" if t > 4.6 else "normal")
        tx, ty = slot_xy(9)
        if t > 1.8:   # 塔尖放光
            for j in range(10):
                a = j / 10 * 2 * math.pi + t * 0.6
                pix.dotted(g, tx + 4 + math.cos(a) * 8, ty + 4 + math.sin(a) * 8,
                           tx + 4 + math.cos(a) * 12, ty + 4 + math.sin(a) * 12, 2, int(t * 6))
        if hit(t, 1.9, dt):
            pix.flash(g)
            self.sparks.burst(tx + 4, ty + 4, 26, 40, up=12, life=1.1, gravity=40)
        if 1.9 < t < 2.2:
            pix.shake(g, t, 1.5)
        self.fx(g, dt)
        if t > 2.3:
            title(g, 37, 12, "五献皆圆满", t, 2.3)
        mx_fruit(g, done, t, blink_last=False)
        mx_burst(g, t, 1.9)
