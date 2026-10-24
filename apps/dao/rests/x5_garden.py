"""抱瓮灌园：《庄子·天地》汉阴丈人“凿隧而入井，抱瓮而出灌”，子贡劝他用桔槔，他说“有机械者必有机事……
吾非不知，羞而不为也”。左边一口井，井边立着桔槔（吊杆）——小道士偏不用，每趟都抱着瓦瓮下井舀水，
走到菜畦里一棵棵浇。菜慢慢长大；浇过的菜叶一挺。彩蛋：风吹得桔槔吱呀晃荡，他看一眼，摇摇头——“羞而不为”；
一只蝴蝶飞来停在菜上。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import daoshi, dpoly, event, fade_box, phase, sweat

GY = 58
WELL = (16, 32)      # 井栏左右
WELL_TOP = 47
XW = 40              # 在井边站的位置
PLANTS = (66, 82, 98)
TRIP = 16.0
BUTTERFLY = [Sprite("##.##\n.###.\n##.##"), Sprite(".#.#.\n.###.\n.#.#.")]


def jar(g: Gfx, cx: float, cy: float, ang: float = 0.0, water: bool = False):
    """瓦瓮：鼓腹小口。中心 (cx, cy)，ang 倾斜（正 = 口朝右倒）"""
    c, s = math.cos(ang), math.sin(ang)
    pts = []
    prof = [(-2, -6), (-3, -5), (-5, -3), (-5.5, 0), (-5, 3), (-3.5, 5), (3.5, 5), (5, 3), (5.5, 0), (5, -3), (3, -5),
            (2, -6)]
    for x, y in prof:
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    g.d.polygon(pts, fill=0, outline=1)
    # 肩上一圈纹
    a, b = (-4.5, -3.5), (4.5, -3.5)
    g.d.line((cx + a[0] * c - a[1] * s, cy + a[0] * s + a[1] * c, cx + b[0] * c - b[1] * s, cy + b[0] * s + b[1] * c),
             fill=1)
    mouth = (cx + 6.5 * s, cy - 6.5 * c)  # 口（局部 (0,-6.5)）
    if water:
        g.px(*mouth)
    return mouth


CABBAGE = [Sprite("""
#...#
.#.#.
..#..
..#..
"""), Sprite("""
##...##
#.#.#.#
.##.##.
...#...
...#...
"""), Sprite("""
....###....
..##...##..
.#..#.#..#.
#...#.#...#
#....#....#
.#.......#.
..#######..
"""), Sprite("""
......###......
...###...###...
..#...#.#...#..
.#...#...#...#.
#....#...#....#
#.....#.#.....#
.#.....#.....#.
..##.......##..
....#######....
""")]


def cabbage(g: Gfx, x: float, k: float, perk: float = 0.0, seed: int = 0):
    """一棵菜：k 0..1 由苗到大棵（四个样子）；perk 浇水后叶子一挺。返回顶端 y"""
    spr = CABBAGE[min(3, int(k * 4))]
    top = GY - spr.h - round(perk)
    g.blit(spr, x - spr.w // 2, top)
    return top


@register
class Garden(Rest):
    id = "x5.garden"
    name = "抱瓮灌园"
    desc = "井边桔槔不用，抱着瓦瓮下井舀水，一棵棵浇菜——有机械者必有机事"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.s = self.rng.randrange(1000)
        self.k0 = 0.12 + self.rng.random() * 0.1    # 菜一开始多大
        self._ht = 0.0

    # ------------------------------------------------------------ 场景零件

    def well(self, g: Gfx):
        d = g.d
        x0, x1 = WELL
        d.rectangle((x0, WELL_TOP, x1, GY), fill=0, outline=1)
        d.rectangle((x0 - 1, WELL_TOP - 2, x1 + 1, WELL_TOP), fill=1)
        for r, y in enumerate(range(WELL_TOP + 3, GY, 3)):  # 砌石
            d.line((x0, y, x1, y), fill=1)
            for x in range(x0 + 2 + (r % 2) * 3, x1, 6):
                d.line((x, y - 2, x, y), fill=1)
        d.rectangle((x0 + 2, WELL_TOP - 1, x1 - 2, WELL_TOP), fill=0)  # 井口

    def shadoof(self, g: Gfx, t: float, swing: float = 0.0):
        """桔槔：立柱 + 横杆（左端坠石，右端吊绳桶垂在井口上）"""
        px, py = 6, 20
        g.d.line((px, GY, px, py), fill=1)
        g.d.line((px + 1, GY, px + 1, py + 2), fill=1)
        g.d.line((px - 3, GY, px + 4, GY), fill=1)
        a = 0.28 + math.sin(t * 0.7) * 0.02 + swing
        ux, uy = math.cos(a), math.sin(a)
        rx, ry = px + ux * 22, py + uy * 22         # 右端
        lx, ly = px - ux * 9, py - uy * 9           # 左端
        g.d.line((lx, ly, rx, ry), fill=1)
        g.d.ellipse((lx - 3, ly - 1, lx + 2, ly + 4), fill=1)   # 坠石
        g.d.rectangle((px - 1, py - 1, px + 1, py + 1), fill=1)
        # 吊绳和小桶
        bob = math.sin(t * 1.3) * swing * 20
        bx, by = rx + bob, ry + 13
        g.d.line((rx, ry, bx, by), fill=1)
        g.d.rectangle((bx - 2, by, bx + 2, by + 4), fill=0, outline=1)

    def beds(self, g: Gfx):
        g.d.line((0, GY, 127, GY), fill=1)
        for x in PLANTS:
            g.d.arc((x - 10, GY - 2, x + 10, GY + 3), 180, 360, fill=1)
        for i in range(6):
            x = 50 + rand(i, 61) * 60
            g.px(x, GY + 2 + (i % 3))

    # ------------------------------------------------------------ 状态

    def growth(self, t: float, i: int) -> float:
        """第 i 棵菜长到多大：随浇水次数长，十几趟后长成"""
        trips = t / TRIP
        return clamp(self.k0 + trips * (0.07 + 0.01 * i))

    def trip(self, t: float):
        """→ (X, f, crouch, lean, step, jar 状态, 浇第几棵/None, 浇的进度)"""
        n, c = phase(t, TRIP)
        X, f, crouch, lean, step = XW, -1, 0.0, 0.0, None
        jar_state = "chest"
        pour = None
        pu = 0.0
        if c < 2.0:  # 井边：蹲下把瓮伸进井里，舀满提上来
            q = math.sin(span(c, 0, 2.0) * math.pi)
            crouch, lean = 0.7 * q, 4 * q
            jar_state = ("dip", q)
        elif c < 2.6:  # 转身
            f = 1
        elif c < 9.6:
            f = 1
            # 三段：走 → 浇
            stops = [(2.6, 5.0, XW, PLANTS[0] - 15), (6.0, 6.8, PLANTS[0] - 15, PLANTS[1] - 15),
                     (7.8, 8.6, PLANTS[1] - 15, PLANTS[2] - 15)]
            pours = [(5.0, 6.0), (6.8, 7.8), (8.6, 9.6)]
            for (a, b, x0, x1) in stops:
                if c >= a:
                    X = lerp(x0, x1, ease_in_out(span(c, a, b)))
                    if c < b:
                        step = c * 11
            for i, (a, b) in enumerate(pours):
                if a <= c < b:
                    pour, pu = i, span(c, a, b)
        elif c < 13.6:  # 回井边
            f = -1
            X = lerp(PLANTS[2] - 15, XW, ease_in_out(span(c, 10.0, 13.6)))
            if 10.0 <= c < 13.6:
                step = c * 11
            jar_state = "empty"
        else:
            jar_state = "empty"
        return n, c, X, f, crouch, lean, step, jar_state, pour, pu

    # ------------------------------------------------------------ 画

    def draw(self, g: Gfx, t: float, final: float = 0.0):
        n, c, X, f, crouch, lean, step, js, pour, pu = self.trip(t)
        ev_sh = None
        if c >= 13.6 and rand(n, self.s + 5) < 0.45 and n > 0:
            ev_sh = c - 13.6     # 这一趟回来：风吹桔槔，他看一眼，摇头
        swing = 0.0
        if ev_sh is not None:
            swing = math.sin(ev_sh * 4.0) * 0.22 * (1 - span(ev_sh, 1.6, 2.4))
        self.beds(g)
        self.well(g)
        self.shadoof(g, t, swing)
        # 菜
        tops = []
        for i, x in enumerate(PLANTS):
            k = self.growth(t, i)
            perk = 0.0
            # 浇过之后 1.5 秒内叶子一挺
            pe = [(6.0, 0), (7.8, 1), (9.6, 2)][i]
            dt = c - pe[0]
            if 0 <= dt < 2.0:
                perk = math.sin(span(dt, 0, 2.0) * math.pi) * 1.4
            tops.append(cabbage(g, x, k, perk, i))
            if 0 <= dt < 0.8:  # 闪一下
                g.px(x - 6, tops[-1] - 3 - dt * 4)
                g.px(x + 6, tops[-1] - 2 - dt * 4)
        # 人
        eye = "closed" if (t % 4.1) < 0.14 else "open"
        look, shake = 0.0, 0.0
        if ev_sh is not None:
            look = -1.5 if 0.3 < ev_sh < 1.4 else 0.0
            if 1.4 < ev_sh < 2.1:
                shake = math.sin(ev_sh * 28) * 1.2
            eye = "closed" if ev_sh > 2.1 else eye
        hands = [None, None]
        jx, jy, ja = X + f * 6, GY - 15, 0.0
        water = js != "empty"
        if isinstance(js, tuple):  # 下井舀水
            q = js[1]
            jx, jy = lerp(X - 6, WELL[0] + 9, q), lerp(GY - 15, WELL_TOP + 8, q)
            hands = [(jx + 3, jy - 3), (jx + 5, jy - 2)]
        elif pour is not None:  # 倾瓮
            tilt = math.sin(pu * math.pi)
            ja = tilt * 1.3
            jx, jy = X + 7 + tilt * 2, GY - 16 + tilt * 2
            lean = 2 * tilt
            hands = [(jx - 2, jy + 3), (jx - 4, jy - 3)]
        else:
            hands = [(jx + f * 1, jy + 2), (jx - f * 1, jy + 3)]
        if final > 0:  # 收场：放下瓮
            jy = lerp(jy, GY - 6, final)
            hands = [(jx, lerp(jy + 2, GY - 9, final)), None]
        pz = daoshi(g, X + shake, GY, f, hands=hands, crouch=crouch, lean=lean, step=step, eye=eye, look=look,
                    draw_far=True)
        # 瓮在怀里（抱瓮：画在人前面，近手压在瓮上）
        if isinstance(js, tuple) and js[1] > 0.55:
            # 瓮在井口以下，看不见，只露出手和一截绳
            g.d.rectangle((WELL[0] + 2, WELL_TOP - 1, WELL[1] - 2, WELL_TOP), fill=0)
        else:
            mouth = jar(g, jx, jy, ja * f, water)
            g.d.rectangle((hands[0][0] - 1, hands[0][1] - 1, hands[0][0] + 1, hands[0][1] + 1), fill=1)
            if pour is not None and 0.2 < pu < 0.85:  # 水流成弧落到菜根
                tx = PLANTS[pour] - 2
                prev = None
                for j in range(13):
                    u = j / 12
                    x = lerp(mouth[0] + 1, tx, u)
                    y = mouth[1] + u * u * (GY - 3 - mouth[1]) - math.sin(u * math.pi) * 2
                    if prev and (j + int(t * 15)) % 5:
                        g.d.line((*prev, x, y), fill=1)
                    prev = (x, y)
                for j in range(3):  # 溅起
                    a = rand(j + int(t * 10), 3) * math.pi
                    g.px(tx + math.cos(a) * 4, GY - 2 - math.sin(a) * 2)
            if isinstance(js, tuple) and js[1] < 0.55 and c > 1.0:  # 刚提上来：滴水
                g.px(jx + 2, jy + 6 + (c * 20) % 6)
        if c >= 13.6 and ev_sh is None and 14.2 < c < 15.4:
            sweat(g, pz.head[0] - 3, pz.head[1] - 2, span(c, 14.2, 15.0))
        # 蝴蝶
        ev_b = event(t, 53.0, 11.0, self.s + 3)
        if ev_b:
            self.butterfly(g, ev_b, tops)
        # 字
        if ev_sh is not None and ev_sh > 1.2:
            self.text(g, "羞而不为", span(ev_sh, 1.2, 1.9))
        else:
            self.text(g, "抱瓮灌园")
        self.mx(g, t, pour, pu, c)

    def butterfly(self, g: Gfx, ev, tops):
        n, k = ev
        i = int(rand(n, self.s + 9) * 3)
        tx, ty = PLANTS[i], tops[i] - 3
        if k < 3.0:  # 飞来
            u = ease_out(k / 3.0)
            x = lerp(130, tx, u) + math.sin(k * 5) * 4 * (1 - u)
            y = lerp(14, ty, u) + math.sin(k * 7) * 3 * (1 - u)
            g.blit(BUTTERFLY[int(k * 10) % 2], x - 2, y - 1)
        elif k < 8.0:  # 停在菜上，翅膀偶尔合一下
            g.blit(BUTTERFLY[1 if (k % 1.6) < 0.25 else 0], tx - 2, ty - 1)
        else:  # 飞走
            u = ease_in(span(k, 8.0, 11.0))
            g.blit(BUTTERFLY[int(k * 10) % 2], tx - 2 + u * 50, ty - 1 - u * 40 + math.sin(k * 6) * 3)

    def text(self, g: Gfx, s: str, a: float = 1.0):
        g.vtext(115, 2, s[:int(round(len(s) * clamp(a)))])

    def mx(self, g: Gfx, t: float, pour, pu: float, c: float):
        # 一棵苗：浇水时上面落水滴、苗一挺
        k = clamp(0.3 + t / TRIP * 0.1)
        h = 2 + int(k * 3)
        g.mx[7, 1:7] = True
        for y in range(7 - h, 7):
            g.mx_set(3, y)
        top = 7 - h
        perk = pour is not None and pu > 0.4
        g.mx_set(2, top + (0 if perk else 1))
        g.mx_set(1, top + (0 if perk else 1) - (1 if k > 0.6 else 0))
        g.mx_set(4, top)
        g.mx_set(5, top - (1 if k > 0.6 else 0))
        if pour is not None and 0.2 < pu < 0.9:
            for j in range(2):
                y = int((t * 8 + j * 2) % max(top - 1, 1))
                g.mx_set(4 + j * 2 - 1, y)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        """抱着空瓮从右边走过菜畦，来到井边（落在 hold(0)：在井边面朝井）"""
        T = self.T["enter"]
        self.beds(g)
        self.well(g)
        self.shadoof(g, t)
        tops = [cabbage(g, x, self.growth(0, i)) for i, x in enumerate(PLANTS)]
        X = lerp(140, XW, ease_out(span(t, 0, T)))
        jx, jy = X - 6, GY - 15
        hands = [(jx - 1, jy + 2), (jx + 1, jy + 3)]
        daoshi(g, X, GY, -1, hands=hands, step=t * 11 if t < T - 0.25 else None)
        jar(g, jx, jy)
        g.d.rectangle((hands[0][0] - 1, hands[0][1] - 1, hands[0][0] + 1, hands[0][1] + 1), fill=1)
        self.text(g, "抱瓮灌园", span(t, 1.0, T - 0.3))
        self.mx(g, t, None, 0, 0)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.draw(g, t)

    def exit(self, g: Gfx, t: float):
        self.draw(g, self._ht, final=ease_in_out(span(t, 0, 0.5)))
        fade_box(g, 1 - ease_in(span(t, 0.35, self.T["exit"])))
        if t > 0.7:
            g.mx[:] = False
            g.mx[7, 1:7] = True
