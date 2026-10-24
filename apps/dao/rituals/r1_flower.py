"""散花：坛前院子里，小道士从花篮里拈花，一朵一朵抛上半空，花“嘭”地盛开，花瓣打着旋儿飘落铺满地。

依据：全真道科仪里的“散花”，以百花荣枯比拟人生盛衰，借此劝化、解冤。《散花偈》每段以“散一朵”起句：
是水仙、状元红、金海棠、风入松、是绣球、是垂杨、是雪梨、是金钱、是芙蓉、菊花新、是紫荆（青松观注本）。
圆满句“香花供养”是斋醮供养的常用语。

入场：小道士提着花篮走进院子，放下篮子（篮里冒出一朵朵花），拱手一拜。
持续：一轮 660 秒 = 十一段，每段 60 秒散一朵：伸手进篮拈花 → 蓄力 → 一抛，花苞沿弧线飞上半空，
      “嘭”地盛开（每段一种花形，左上牌子写花名），花在空中轻轻转、闪光，十几秒后花瓣一片片离开，
      打着旋儿飘落，落地后铺成花毯（随 e 变厚）。段与段之间：小道士每隔一阵抓一把花瓣往前一撒；
      作揖；一只蝴蝶飞来停在花篮上，扇两下翅膀又飞走。篮里的花随 e 变少。
      续：一阵风把满地花瓣卷成一股旋风吹走，篮里的花一朵朵重新冒出来。
中断：半空的花合拢成苞落回篮里，飘着的花瓣一齐落地，小道士拱手；牌子“收花”。
恢复：小道士再拈一朵抛上去，花重新开。
圆满：小道士把整篮花往天上一扬，十一朵花在半空一齐盛开，满屏花雨，闪白，“香花供养”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import FLOOR, Clock, hit, mx_art, mx_burst, pose_arm, ring_dots, star, title, twinkles, badge

DX = 36                 # 小道士
BX = 52                 # 花篮中心
SKY = (90, 17)          # 花在半空盛开的位置
SEG = 60.0
RENEW = 7.0

# 《散花偈》十一种花：名、花瓣数、瓣形、层数、花心
FLOWERS = [
    ("水仙", 6, "point", 1, "cup"), ("状元红", 8, "round", 2, "dot"), ("金海棠", 5, "round", 1, "dot"),
    ("风入松", 12, "thin", 1, "cone"), ("绣球", 0, "ball", 1, "dot"), ("垂杨", 7, "droop", 1, "dot"),
    ("雪梨", 5, "round", 1, "stamen"), ("金钱", 10, "point", 1, "coin"), ("芙蓉", 5, "wide", 2, "dot"),
    ("菊花", 16, "thin", 2, "dot"), ("紫荆", 5, "point", 1, "stamen"),
]

PETAL = pix.frames("""
##
 #
---
#.
##
---
###
---
#
#
""")

BUTTERFLY = pix.frames("""
##.##
###.###
 ##.##
  # #
---
  .
 #####
 ##.##
  # #
""")

CLOUD = pix.sprite("""
     ####
   ##....##   ###
  #..###...###...#
 #..#...#.......#.#
 #...##.........#..##
  ##.............. ..#
    ###############.#
""")


def _bloom(kind: int, rot: float = 0.0):
    """逐像素花朵 23×23（按《散花偈》的花选形）：亮瓣、瓣间暗缝、瓣脉、花心另画"""
    name, n, shape, layers, core = FLOWERS[kind]
    p = Part(23, 23)
    c = 11
    if shape == "ball":   # 绣球：一团小四瓣花
        p.shape("ellipse", (1, 1, 21, 21), fill=1)
        for i in range(12):
            a = i * 2.4 + rot
            r = 2 + (i * 5) % 8
            x, y = round(c + math.cos(a) * r), round(c + math.sin(a) * r)
            p.d.line((x - 1, y, x + 1, y), fill=0)
            p.d.line((x, y - 1, x, y + 1), fill=0)
            p.px(x, y, 1)
        p.dither([(14, 14), (21, 12), (21, 21), (12, 21)], 0.5, 0)
        return p.sprite()
    for layer in range(layers):
        L = 10.5 if layer == 0 else 6.5
        off = rot + (math.pi / n if layer else 0)
        for i in range(n):
            a = off + i / n * 2 * math.pi
            ux, uy = math.cos(a), math.sin(a)
            if shape == "droop":   # 垂杨：一丝丝往下垂的柳条
                pts = [(c, c)]
                for j in range(1, 6):
                    r = j * 2
                    pts.append((c + ux * r, c + uy * r * 0.6 + j * j * 0.3))
                p.shape("line", pts, fill=1)
                for x, y in pts[2::2]:
                    p.px(round(x) + 1, round(y), 1)
                continue
            w = {"point": 3.2, "round": 3.6, "thin": 1.0, "wide": 4.8}[shape] * (L / 10.5)
            nx, ny = -uy, ux
            tipw = 0 if shape in ("point", "thin") else w * 0.9
            pts = [(c + nx * 1, c + ny * 1), (c + ux * L * 0.55 + nx * w, c + uy * L * 0.55 + ny * w),
                   (c + ux * L + nx * tipw * 0.5, c + uy * L + ny * tipw * 0.5),
                   (c + ux * L - nx * tipw * 0.5, c + uy * L - ny * tipw * 0.5),
                   (c + ux * L * 0.55 - nx * w, c + uy * L * 0.55 - ny * w), (c - nx * 1, c - ny * 1)]
            p.shape("polygon", pts, fill=1)
            if shape != "thin":    # 瓣脉
                p.d.line((c + ux * 4, c + uy * 4, c + ux * (L - 3), c + uy * (L - 3)), fill=0)
        if shape in ("round", "wide", "point"):  # 瓣间暗缝
            for i in range(n):
                b = off + (i + 0.5) / n * 2 * math.pi
                p.d.line((c + math.cos(b) * 3, c + math.sin(b) * 3, c + math.cos(b) * L, c + math.sin(b) * L), fill=0)
    if core == "coin":    # 金钱花：花心是一枚方孔钱
        p.shape("ellipse", (c - 4, c - 4, c + 4, c + 4), fill=0)
        p.d.ellipse((c - 4, c - 4, c + 4, c + 4), outline=1)
        p.d.rectangle((c - 1, c - 1, c + 1, c + 1), outline=1)
    elif core == "cup":   # 水仙：副冠
        p.shape("ellipse", (c - 3, c - 3, c + 3, c + 3), fill=0)
        p.d.ellipse((c - 3, c - 3, c + 3, c + 3), outline=1)
        p.d.ellipse((c - 1, c - 1, c + 1, c + 1), fill=1)
    elif core == "stamen":  # 长蕊
        p.shape("ellipse", (c - 2, c - 2, c + 2, c + 2), fill=0)
        for i in range(5):
            a = rot + i / 5 * 2 * math.pi + 0.3
            p.d.line((c, c, c + math.cos(a) * 4, c + math.sin(a) * 4), fill=0)
            p.px(round(c + math.cos(a) * 5), round(c + math.sin(a) * 5), 0)
        p.px(c, c, 1)
    elif core == "cone":  # 风入松：针叶簇中间一颗松果
        p.shape("ellipse", (c - 3, c - 4, c + 3, c + 4), fill=1)
        p.d.ellipse((c - 3, c - 4, c + 3, c + 4), outline=0)
        for y in (-2, 0, 2):
            p.d.line((c - 2, c + y, c + 2, c + y), fill=0)
            p.px(c - 1 + (y % 4 == 0), c + y, 1)
    else:
        p.shape("ellipse", (c - 3, c - 3, c + 3, c + 3), fill=0)
        p.d.ellipse((c - 3, c - 3, c + 3, c + 3), outline=1)
        p.px(c, c, 1), p.px(c - 1, c - 1, 1), p.px(c + 1, c + 1, 1)
    return p.sprite()


def _bud():
    p = Part(5, 7)
    p.shape("ellipse", (0, 0, 4, 5), fill=1)
    p.d.line((2, 1, 2, 4), fill=0)
    p.shape("line", (2, 5, 2, 6), fill=1)
    return p.sprite()


def _basket():
    """花篮 19×12（不含提梁）：口沿、编织纹、篮脚；右侧背光"""
    p = Part(19, 12)
    p.shape("rectangle", (0, 0, 18, 1), fill=1)
    p.shape("polygon", [(1, 2), (17, 2), (15, 10), (3, 10)], fill=1)
    for y in range(3, 10):                     # 编织纹：交错的短暗线
        for x in range(2 + (y % 2) * 2, 17, 4):
            p.d.line((x, y, x + 1, y), fill=0)
    p.d.line((2, 2, 16, 2), fill=0)
    p.shape("rectangle", (4, 11, 6, 11), fill=1)
    p.shape("rectangle", (12, 11, 14, 11), fill=1)
    p.dither([(13, 3), (16, 3), (15, 10), (12, 10)], 0.5, 0)
    return p.sprite()


_P: dict = {}


def P(name, *a):
    k = (name,) + a
    if k not in _P:
        _P[k] = {"bloom": _bloom, "bud": _bud, "basket": _basket}[name](*a)
    return _P[k]


def bloom(kind: int, t: float):
    """慢慢转的花：三档角度循环"""
    return P("bloom", kind, round((int(t * 2) % 3) * 0.35, 2))


# ---------------------------------------------------------------- 背景

def yard(g: Gfx, t: float):
    """院子：瓦檐矮墙（筒瓦一列、瓦当、墙身一道砖缝）、地砖；天上两朵祥云慢慢飘"""
    for i, (x0, y) in enumerate(((10, 4), (60, 9))):
        x = (x0 + t * (1.2 + i * 0.5)) % 170 - 30
        pix.blit(g, CLOUD, x, y)
    wy = 42
    g.d.line((0, wy, 127, wy), fill=1)
    for x in range(0, 128, 5):           # 筒瓦 + 瓦当
        g.d.arc((x, wy - 3, x + 5, wy + 2), 180, 360, fill=1)
        g.px(x + 2, wy + 2)
    g.d.line((0, wy + 3, 127, wy + 3), fill=1)
    for x in range(8, 128, 24):          # 墙上漏窗（小方格花窗）
        g.d.rectangle((x, wy + 6, x + 6, wy + 10), outline=1)
        g.px(x + 3, wy + 8)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)


def basket(g: Gfx, n: int, t: float):
    """花篮 + 提梁 + 篮口露出的花（n 朵）"""
    x0, y0 = BX - 9, FLOOR - 12
    g.d.arc((x0 + 2, y0 - 12, x0 + 16, y0 + 6), 180, 360, fill=1)  # 提梁
    g.d.arc((x0 + 3, y0 - 11, x0 + 15, y0 + 5), 180, 360, fill=1)
    for i in range(min(n, 11)):
        fx = x0 + 2 + (i * 7) % 15
        fy = y0 - 2 - (i % 3) * 2 + (1 if int(t * 1.5 + i) % 4 == 0 else 0)
        g.d.rectangle((fx, fy, fx + 2, fy + 2), fill=1)
        g.px(fx + 1, fy + 1, 0)
        g.px(fx + 1, fy - 1)
    pix.blit(g, P("basket"), x0, y0)


def carpet(g: Gfx, n: int, seed: int):
    """地上的花瓣（n 片，位置确定）：铺在地砖上，带黑边"""
    for i in range(min(n, 140)):
        x = 60 + rand(i, seed) * 64
        y = FLOOR + 1 + int(rand(i + 400, seed) * 3)
        pix.blit(g, PETAL[i % 3], x, y)


def falling(g: Gfx, t: float, x0: float, y0: float, n: int, t0: float, dur: float, seed: int, gap: float = 0.6,
            spread: float = 1.0):
    """从 (x0, y0) 依次离开、打着旋儿飘落的花瓣（时间 t 的确定函数）"""
    for i in range(n):
        k = (t - t0 - i * gap) / dur
        if 0 <= k < 1:
            x = x0 + (rand(i, seed) - 0.5) * 14 * spread + math.sin(k * 7 + i) * 4 - k * 6
            y = lerp(y0, FLOOR - 2, ease_in(k) * 0.4 + k * 0.6)
            pix.blit(g, pix.anim(PETAL, t + i * 0.3, 6), x, y, outline=False)


def mx_flower(g: Gfx, open_: float, n: int, t: float):
    """点阵：花篮 + 篮上一朵花（open_ 0 苞 / 1 开）"""
    mx_art(g, """
........
........
........
........
.#....#.
########
.######.
..####..
""")
    if open_ <= 0:
        g.mx[3, 3:5] = n > 0
        return
    if open_ < 0.5:
        g.mx[1:4, 3:5] = True
        return
    on = int(t * 4) % 2
    mx_art(g, """
.#.#.#..
..###...
.##.##..
..###...
.#.#.#..
""", 1, 0)
    g.mx[2, 4] = bool(on)


# ---------------------------------------------------------------- 场景

@register
class ScatterFlowers(Ritual):
    id = "r1.flower"
    name = "散花"
    desc = "小道士从花篮里拈花抛上半空，花“嘭”地盛开（散花偈十一种花），花瓣打旋飘落铺满地；一轮后旋风卷走花毯"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 3.4, "complete": 5.5}
    CYCLE = SEG * 11

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    def seg(self, e: float) -> int:
        return int((e % self.CYCLE) // SEG)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        badge(g, 5, 3, label or FLOWERS[self.seg(e)][0], size=12)

    def toss(self, g: Gfx, t: float, u: float, kind: int, dt: float, face_t: float = None) -> float:
        """u ∈ [0, 3]：拈花 → 蓄力 → 抛 → 盛开。画小道士与飞行的花；返回花开程度（0 未开）"""
        if u < 1.2:            # 伸手进篮
            h = pose_arm(g, DX, FLOOR, t, 60 if u < 0.9 else 30)
            if u >= 0.7:
                pix.blit(g, P("bud"), h["hand"][0] - 2, h["hand"][1] - 6)
            return 0.0
        if u < 1.7:            # 蓄力：手收回胸前、身子一沉
            h = pose_arm(g, DX, FLOOR, t, 30, bob=False)
            pix.blit(g, P("bud"), h["hand"][0] - 2, h["hand"][1] - 6)
            return 0.0
        h = daoshi(g, DX, FLOOR, "raise" if u < 2.6 else "idle", t, face="happy" if u > 2.6 else "normal")
        q = span(u, 1.7, 2.6)
        if q < 1:
            sx, sy = DX + 10, FLOOR - 32
            x = lerp(sx, SKY[0], ease_out(q))
            y = lerp(sy, SKY[1], q) - math.sin(q * math.pi) * 10
            pix.blit(g, P("bud"), x - 2, y - 3)
            if int(t * 30) % 2 == 0:
                g.px(x - 4 * (1 - q), y + 4)
            return 0.0
        if hit(u, 2.6, dt):
            self.sparks.burst(SKY[0], SKY[1], 14, 30, life=0.6, gravity=20)
        return 1.0

    def sky_flower(self, g: Gfx, t: float, kind: int, age: float, size: float = 1.0):
        """半空的花：弹开 → 轻轻浮动、闪光 → 凋（缩小）"""
        if age < 0 or age > 19.5:
            return
        pop = ease_out_back(span(age, 0, 0.4))
        wilt = 1 - 0.85 * span(age, 13, 19.5)
        s = max(0.2, pop * wilt * size)
        spr = bloom(kind, t)
        if abs(s - 1) > 0.05:
            spr = pix.stretch(spr, s, s)
        x, y = SKY[0], SKY[1] + math.sin(t * 1.3) * 1.5
        pix.blit(g, spr, x - spr.w / 2, y - spr.h / 2)
        if age < 0.5:
            ring_dots(g, x, y, 4 + age * 30, 3)
        if 0.4 < age < 13:
            twinkles(g, [(x - 12, y - 6), (x + 11, y - 3), (x - 8, y + 9), (x + 9, y + 9)], t, 1.1)

    def scene(self, g: Gfx, t: float, e: float, dt: float, petals_on_ground: int):
        yard(g, t)
        carpet(g, petals_on_ground, self.seed)

    def ground_count(self, e: float) -> int:
        k = e % self.CYCLE
        return int(k / SEG) * 12 + int(max(0, min((k % SEG - 13) / 0.7, 9)))

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        yard(g, t)
        if t < 2.4:   # 提着花篮走进来
            x = lerp(-14, DX, ease_out(span(t, 0, 2.2)))
            h = pose_arm(g, x, FLOOR, t, 30 if t < 2.2 else 60, legs="walk" if t < 2.2 else "stand")
            hx, hy = h["hand"]
            bx, by = hx - 1, hy + 2
            g.d.arc((bx - 6, by - 2, bx + 6, by + 8), 180, 360, fill=1)
            p = P("basket")
            pix.blit(g, pix.stretch(p, 0.7, 0.7), bx - 6, by + 3)
        else:
            n = int(span(t, 2.4, 3.8) * 11)
            basket(g, n, t)
            if 2.4 <= t < 3.8 and int(t * 30) % 4 == 0:
                self.sparks.burst(BX + rand(int(t * 30)) * 14 - 7, FLOOR - 15, 2, 14, up=10, life=0.4, gravity=30)
            pose = "idle" if t < 4.0 else ("gongshou" if t < 4.7 else ("bow" if t < 5.3 else "idle"))
            daoshi(g, DX, FLOOR, pose, t, face="happy" if 2.6 < t < 4.0 else "normal")
        if hit(t, 2.4, dt):
            pix.shake(g, t, 1.0)
            self.sparks.burst(BX, FLOOR - 1, 8, 20, up=12, life=0.4, gravity=60)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 3.0:
            self.counter(g, 0.0)
        mx_flower(g, 0, 1, t)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e, dt)
            return
        seg = self.seg(e)
        u = k % SEG
        kind = seg
        yard(g, t)
        carpet(g, self.ground_count(e), self.seed)
        left = 11 - seg - (1 if u >= 0.8 else 0)
        # 蝴蝶：每 40 秒来停一次花篮
        self.butterfly(g, e)
        basket(g, left, t)
        opened = 0.0
        if u < 3.0:
            opened = self.toss(g, t, u, kind, dt)
        elif (u % 20) < 1.6 and u > 20:   # 抓一把花瓣往前撒（第 20、40 秒）
            v = u % 20
            pose_arm(g, DX, FLOOR, t, 60 if v < 0.5 else (0 if v < 1.0 else -30))
        elif 52.0 <= u < 54.4:
            daoshi(g, DX, FLOOR, "gongshou" if u < 53.2 else "bow", t)
        else:
            daoshi(g, DX, FLOOR, "idle", t)
        for t0 in (20.7, 40.7):  # 撒出去的花瓣
            if t0 <= u < t0 + 3.5:
                falling(g, u, DX + 24, FLOOR - 30, 7, t0, 2.6, self.seed + seg + int(t0), gap=0.06, spread=1.6)
        if u > 20:             # 空中零星飘着的花瓣
            for i in range(3):
                ph = (e * 0.09 + i / 3) % 1
                x = 70 + i * 20 + math.sin(e * 0.8 + i * 2) * 5 - ph * 10
                pix.blit(g, pix.anim(PETAL, e + i, 5), x, ph * 50 - 4, outline=False)
        if u >= 2.6:
            self.sky_flower(g, t, kind, u - 2.6)
            opened = 1.0
        falling(g, u, SKY[0], SKY[1], 9, 13.0, 4.5, self.seed + seg * 7, gap=0.7)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        mx_flower(g, opened if u < 19 else 0, left, t)
        if 2.6 <= u < 2.8:
            g.mx_level = 6

    def butterfly(self, g: Gfx, e: float):
        k = (e + self.seed * 3) % 40
        if 20 <= k < 28:
            v = k - 20
            land = (BX + 3, FLOOR - 19)
            if v < 2:
                q = ease_out(v / 2)
                x, y = lerp(130, land[0], q), lerp(10, land[1], q) + math.sin(v * 8) * 3
            elif v < 6:
                x, y = land
            else:
                q = ease_in((v - 6) / 2)
                x, y = lerp(land[0], -10, q), lerp(land[1], 0, q) + math.sin(v * 8) * 3
            fr = int(e * (12 if not (2 <= v < 6) else 2.5)) % 2
            pix.blit(g, BUTTERFLY[fr], x - 3, y - 2)

    def _renew(self, g: Gfx, t: float, k: float, e: float, dt: float):
        """旋风卷走花毯，篮里的花一朵朵重新冒出来"""
        yard(g, t)
        gone = span(k, 0.6, 3.0)
        n = int(11 * 12 * (1 - gone))
        carpet(g, n, self.seed)
        if 0.3 < k < 4.2:   # 旋风：花瓣绕着一根漏斗往上卷，往右移走
            cx0 = 70 + (k - 0.3) * 16
            grow_h = 44 * ease_out(span(k, 0.3, 1.4))
            for j in range(5):         # 漏斗的风纹
                y = FLOOR - 4 - j * 9
                if FLOOR - y > grow_h + 4:
                    continue
                r = 3 + j * 2.5
                a0 = k * 9 + j
                ring_dots(g, cx0 + math.sin(y * 0.2 + k * 3) * 2, y, r, 2, rot=a0, sy=0.35, a0=0, a1=math.pi * 1.2)
            for i in range(30):
                h = (i / 30) * grow_h
                a = k * 9 + i * 0.9
                r = 3 + h * 0.28
                x = cx0 + math.cos(a) * r + math.sin(h * 0.2 + k * 3) * 2
                y = FLOOR - 3 - h + math.sin(a) * r * 0.3
                pix.blit(g, PETAL[i % 4], x, y, outline=False)
        grow = int(span(k, 3.5, 6.0) * 11)
        basket(g, grow, t)
        if 3.5 < k < 6.0 and int(k * 30) % 7 == 0:
            self.sparks.burst(BX + rand(int(k * 30)) * 14 - 7, FLOOR - 16, 3, 12, up=8, life=0.4, gravity=20)
        face = "wow" if k < 3.5 else "happy"
        pose = "idle" if k < 6.0 else "gongshou"
        daoshi(g, DX, FLOOR, pose, t, face=face)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        mx_flower(g, 0, grow, t)
        for i in range(8):
            if (k * 4 + i) % 3 < 1 and k < 4:
                g.mx_set(i, int(7 - (k * 6 + i) % 8))

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        seg = self.seg(e)
        u = (e % self.CYCLE) % SEG
        yard(g, t)
        carpet(g, self.ground_count(e) + 3, self.seed)
        left = 11 - seg - 1
        basket(g, left + (1 if t > 1.2 else 0), t)
        daoshi(g, DX, FLOOR, "gongshou" if t > 0.3 else "idle", t)
        q = ease_in(span(t, 0.5, 1.2))
        if t < 0.5 and u >= 2.6:
            self.sky_flower(g, t, seg, 5.0, size=1 - t * 1.4)
        elif t < 1.2 and u >= 2.6:  # 合拢成苞，落回篮里
            x, y = lerp(SKY[0], BX, q), lerp(SKY[1], FLOOR - 16, q) - math.sin(q * math.pi) * 6
            pix.blit(g, P("bud"), x - 2, y - 3)
        if hit(t, 1.2, dt):
            self.sparks.burst(BX, FLOOR - 14, 6, 14, up=8, life=0.4, gravity=40)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e, "收花" if t > 0.6 else None)
        mx_flower(g, 0, left, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        seg = self.seg(e)
        yard(g, t)
        carpet(g, self.ground_count(e), self.seed)
        basket(g, 11 - seg - (1 if t >= 0.8 else 0), t)
        opened = self.toss(g, t, min(t, 2.99), seg, dt)
        if t >= 2.6:
            self.sky_flower(g, t, seg, t - 2.6)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        mx_flower(g, opened, 1, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        yard(g, t)
        carpet(g, int(40 + 80 * span(t, 1.5, 5.0)), self.seed)
        basket(g, 0 if t > 1.2 else 11, t)
        if t < 0.8:
            h = pose_arm(g, DX, FLOOR, t, 60)
        elif t < 1.2:
            h = pose_arm(g, DX, FLOOR, t, 30, bob=False)
        else:
            daoshi(g, DX, FLOOR, "raise" if t < 2.6 else ("kneel" if t < 4.6 else "idle"), t, face="happy")
        # 十一朵花飞上去，在半空排成一道弧一齐盛开
        for i in range(11):
            q = span(t, 1.2 + i * 0.05, 2.0 + i * 0.05)
            tx = 12 + i * 10.4 + math.sin(t * 1.5 + i) * 1
            ty = 18 - math.sin(i / 10 * math.pi) * 8 + (i % 2) * 8 + math.cos(t * 1.2 + i) * 1
            if 0 < q < 1:
                x, y = lerp(BX, tx, ease_out(q)), lerp(FLOOR - 16, ty, q) - math.sin(q * math.pi) * 10
                pix.blit(g, P("bud"), x - 2, y - 3)
            elif q >= 1:
                pop = ease_out_back(span(t, 2.0 + i * 0.05, 2.4 + i * 0.05))
                sc = 0.6 * pop + 0.01
                spr = pix.stretch(bloom(i, t + i * 0.3), sc, sc)
                pix.blit(g, spr, tx - spr.w / 2, ty - spr.h / 2)
        if t > 2.2:            # 满屏花雨
            for i in range(30):
                ph = (t * 0.35 + rand(i, 5)) % 1
                x = rand(i + 50, 5) * 128 + math.sin(t * 2 + i) * 4
                y = ph * 70 - 6
                pix.blit(g, PETAL[(i + int(t * 6)) % 4], x, y, outline=False)
        if hit(t, 2.0, dt):
            pix.flash(g)
            self.sparks.burst(64, 16, 30, 50, life=1.0, gravity=30)
        if 2.0 < t < 2.3:
            pix.shake(g, t, 1.5)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 2.6:
            title(g, 90, 33, "香花供养", t, 2.6)
        mx_flower(g, 1.0, 1, t)
        mx_burst(g, t, 2.0)
