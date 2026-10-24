"""喂鸡：竹篱笆前，小道士端着瓢，抓一把谷子扬出去，谷粒成弧落地；三只母鸡一只公鸡跑过来一粒粒啄。
彩蛋：公鸡伸脖子打鸣；公鸡偶尔定住不动，像木头雕的——“望之似木鸡”（《庄子·达生》纪渻子为王养斗鸡：
“几矣。鸡虽有鸣者，已无变矣，望之似木鸡矣，其德全矣”）。左侧平时竖写“鸡犬相闻”（《道德经》八十章）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import daoshi, event, fade_box, phase

GY = 58
FB = 44          # 篱笆脚
X = 26
P = 11.0
THROW = 1.5      # 撒出的时刻
LAND = 2.1
SPEED = 16.0
PECK = 0.7
NG = 12          # 一把几粒

HEN = Sprite("""
.........##.
........####
........#.##
.##.....###.
.###...####.
.##########.
..#########.
..########..
....####....
....#..#....
""")
HEN_PECK = Sprite("""
............
............
.##.........
.###........
.#######....
.#########..
..#########.
..######.###
....####.#.#
....#..#....
""")
COCK = Sprite("""
.........#.#.
........####.
........#.###
##......###..
#.#....####..
#..#..#####..
.#.#########.
..#########..
...#######...
....#####....
.....#..#....
.....#..#....
""")
COCK_CROW = Sprite("""
..........#.#
.........####
.........#.##
##.......###.
#.#.....###.#
#..#...####..
.#.#########.
..#########..
...#######...
....#####....
.....#..#....
.....#..#....
""")
COCK_PECK = Sprite("""
.............
.............
##...........
#.#..........
#..########..
.#.#########.
..##########.
...#######.#.
....#####.###
.....#..#.#.#
.....#..#....
.....#..#....
""")
SPRITES = {}


def spr(name: str, f: int) -> Sprite:
    key = (name, f)
    if key not in SPRITES:
        base = {"hen": HEN, "henp": HEN_PECK, "cock": COCK, "cockc": COCK_CROW, "cockp": COCK_PECK}[name]
        SPRITES[key] = base if f > 0 else base.flip()
    return SPRITES[key]


@register
class Hens(Rest):
    id = "x5.hens"
    name = "喂鸡"
    desc = "扬一把谷子，母鸡公鸡跑来一粒粒啄；公鸡打鸣，偶尔呆立如木鸡"
    T = {"enter": 3.0, "exit": 1.3}
    NH = 4  # 0..2 母鸡，3 公鸡

    def setup(self):
        self.s = self.rng.randrange(1000)
        self._ht = 0.0
        self._cache: dict[int, tuple] = {}

    # ------------------------------------------------------------ 计划（每轮确定性算一遍并缓存）

    def home(self, h: int) -> tuple[float, float]:
        return 60 + h * 16, GY

    def start(self, n: int, h: int) -> float:
        """第 n 轮开始时每只鸡在哪（上一轮最后一秒多它们会溜达过去）"""
        if n <= 0:
            return self.home(h)[0]
        return 54 + h * 17 + (rand(n * 5 + h, self.s + 21) - 0.5) * 12

    def grains(self, n: int):
        """第 n 轮撒出去的谷粒落点"""
        out = []
        for i in range(NG):
            x = 52 + rand(i, self.s + n * 17) * 64
            y = GY - 1 - rand(i + 40, self.s + n * 17) * 3
            out.append((x, y))
        return out

    def plan(self, n: int):
        """→ 每只鸡的路线：[(到达时刻, 离开时刻, x, 啄的谷粒下标或 -1)]，以及每粒谷的被啄时刻"""
        if n in self._cache:
            return self._cache[n]
        gr = self.grains(n)
        starts = [self.start(n, h) for h in range(self.NH)]
        # 分配：每粒给最近的鸡（按 x）
        owner = [min(range(self.NH), key=lambda h: abs(starts[h] - gx) + h * 3) for gx, _ in gr]
        routes, eaten = [], [P * 2] * NG
        for h in range(self.NH):
            mine = sorted([i for i in range(NG) if owner[i] == h], key=lambda i: abs(gr[i][0] - starts[h]))
            t0 = LAND + 0.2 + h * 0.15 + rand(h, self.s + n) * 0.4
            x = starts[h]
            route = [(0.0, t0, x, -1)]
            for i in mine:
                gx = gr[i][0] + (-5 if gr[i][0] > x else 5)  # 停在谷粒旁边，嘴够得着
                arr = t0 + abs(gx - x) / SPEED
                dep = arr + PECK
                if dep > P - 1.6:
                    break
                route.append((arr, dep, gx, i))
                eaten[i] = arr + PECK * 0.5
                x, t0 = gx, dep
            routes.append(route)
        res = (routes, eaten)
        if len(self._cache) > 6:
            self._cache.clear()
        self._cache[n] = res
        return res

    def hen_at(self, n: int, c: float, h: int):
        """→ (x, 朝向, 状态 walk/peck/idle)"""
        routes, _ = self.plan(n)
        route = routes[h]
        prev_x = route[0][2]
        prev_dep = route[0][1]
        face = 1 if (h % 2) else -1
        for arr, dep, x, i in route[1:]:
            if c < arr:  # 在路上
                u = span(c, prev_dep, arr)
                face = 1 if x > prev_x else -1
                if c < prev_dep:
                    return prev_x, face, "idle"
                return lerp(prev_x, x, u), face, "walk"
            if c < dep:
                face = 1 if x > prev_x else -1
                return x, face, "peck"
            prev_x, prev_dep = x, dep
            face = 1 if x > route[0][2] else -1
        # 一轮快完：溜达到下一轮的起点
        nx = self.start(n + 1, h)
        if c > P - 1.4 and abs(nx - prev_x) > 0.5:
            u = ease_in_out(span(c, P - 1.4, P))
            return lerp(prev_x, nx, u), (1 if nx > prev_x else -1), ("walk" if u < 1 else "idle")
        return prev_x, face, "idle"

    # ------------------------------------------------------------ 画

    def fence(self, g: Gfx):
        """院子后面的竹篱笆（远一点：脚在 FB），前面是空的鸡场"""
        for x in range(40, 128, 7):
            top = 26 + (x // 7) % 2 * 2
            g.d.line((x, top, x, FB), fill=1)
        g.d.line((38, 31, 127, 31), fill=1)
        g.d.line((38, 39, 127, 39), fill=1)
        for x in range(43, 128, 14):   # 绑绳
            g.px(x, 30)
            g.px(x, 38)
        g.d.line((14, FB, 127, FB), fill=1)
        for i in range(10):  # 场上几处草茎
            x = 40 + rand(i, 51) * 86
            y = FB + 3 + rand(i, 52) * 8
            g.px(x, y)
        g.d.line((0, GY, 127, GY), fill=1)

    def chicken(self, g: Gfx, n: int, c: float, h: int, t: float, frozen, crow: float):
        if frozen is not None and h == 3:  # 定在开始发呆的那一刻；最后一秒走回自己的路线
            nf, cf = phase(frozen, P)
            x, face, st = self.hen_at(nf, cf, h)
            back = span(t - frozen, 10.0, 11.0)
            if back > 0:
                x2, f2, _ = self.hen_at(n, c, h)
                face = 1 if x2 > x else -1
                x = lerp(x, x2, ease_in_out(back))
                frozen = None
                st = "walk"
        else:
            x, face, st = self.hen_at(n, c, h)
        cock = h == 3
        bob = 0
        if frozen is not None and cock:
            st = "statue"
        if st == "walk":
            bob = 1 if int(c * 8 + h) % 2 else 0
            name = "cock" if cock else "hen"
        elif st == "peck":
            name = ("cockp" if cock else "henp") if (c * 4 + h) % 1 < 0.5 else ("cock" if cock else "hen")
        elif st == "statue":
            name = "cock"
        else:
            # 闲着：偶尔啄地、偶尔左右看
            k = noise(t * 0.8 + h * 5, self.s + h)
            name = ("cockp" if cock else "henp") if k > 0.7 else ("cock" if cock else "hen")
            if noise(t * 0.3 + h * 9, self.s + 30) > 0.62:
                face = -face
            if cock and crow > 0:
                name = "cockc"
        sp = spr(name, face)
        g.blit(sp, x - sp.w // 2, GY - sp.h - bob)
        return x, face, sp

    def thrower(self, g: Gfx, c: float, t: float, final: float = 0.0):
        """撒谷：远手端瓢在腰前，近手抓一把——一扬"""
        bowl = (X + 5, GY - 13)
        if c < 0.8:
            q = ease_in_out(span(c, 0.1, 0.8))
            hand = (lerp(X + 7, bowl[0] + 1, q), lerp(GY - 10, bowl[1] - 1, q))
            lean = 1.5 * q
        elif c < THROW:  # 往后蓄
            q = ease_in_out(span(c, 0.8, 1.2))
            hand = (lerp(bowl[0] + 1, X - 2, q), lerp(bowl[1] - 1, GY - 12, q))
            lean = 1.5 - 2 * q
        elif c < 2.2:  # 一扬
            q = ease_out(span(c, THROW, THROW + 0.25))
            hand = (lerp(X - 2, X + 14, q), lerp(GY - 12, GY - 27, q))
            lean = -0.5 + 3 * q
        else:
            q = ease_in_out(span(c, 2.2, 3.0))
            hand = (lerp(X + 14, X + 7, q), lerp(GY - 27, GY - 10, q))
            lean = 2.5 * (1 - q)
        if final > 0:
            hand = (lerp(hand[0], X + 7, final), lerp(hand[1], GY - 10, final))
        eye = "closed" if (t % 4.4) < 0.14 else "open"
        pz = daoshi(g, X, GY, 1, hands=[hand, (bowl[0] - 1, bowl[1] + 2)], lean=lean, eye=eye)
        # 瓢：半个葫芦
        bx, by = bowl[0] + lean, bowl[1]
        g.d.chord((bx - 6, by - 4, bx + 4, by + 4), 0, 180, fill=0, outline=1)
        g.d.line((bx - 6, by, bx + 4, by), fill=1)
        g.d.line((bx - 6, by, bx - 10, by - 2), fill=1)
        for j in range(3):
            g.px(bx - 3 + j * 2, by - 1)
        return pz

    def draw(self, g: Gfx, t: float, final: float = 0.0):
        n, c = phase(t, P)
        self.fence(g)
        # 谷粒：飞行中 / 地上（被啄掉就没了）
        gr = self.grains(n)
        _, eaten = self.plan(n)
        for i, (gx, gy) in enumerate(gr):
            if c < THROW:
                continue
            if c < LAND + rand(i, self.s) * 0.3:
                u = span(c, THROW + 0.05, LAND + rand(i, self.s) * 0.3)
                x = lerp(X + 14, gx, u)
                y = lerp(GY - 28, gy, u) - math.sin(u * math.pi) * (10 + rand(i + 3, self.s) * 8)
                g.px(x, y)
            elif c < eaten[i]:
                g.px(gx, gy)
        # 上一轮没吃完的也在（下一把落地时被“盖住”）
        if n > 0:
            pg = self.grains(n - 1)
            _, pe = self.plan(n - 1)
            for i, (gx, gy) in enumerate(pg):
                if pe[i] > P and c < LAND:
                    g.px(gx, gy)
        ev_frz = event(t, 61.0, 12.0, self.s + 4)
        ev_crow = event(t + 25, 37.0, 2.6, self.s + 5)
        crow = 0.0
        if ev_crow and not ev_frz:
            crow = 1.0
        frozen = (t - (ev_frz[1] - 1.0)) if (ev_frz is not None and ev_frz[1] > 1.0) else None
        cock_xy = None
        for h in range(self.NH):
            x, face, sp = self.chicken(g, n, c, h, t, frozen if h == 3 else None, crow)
            if h == 3:
                cock_xy = (x, face, sp)
        pz = self.thrower(g, c, t, final)
        # 扬手时手里撒出的一蓬
        if THROW - 0.05 < c < THROW + 0.2:
            hx, hy = pz.near
            for j in range(5):
                g.px(hx + 2 + j, hy - 1 - (j % 2))
        # 公鸡打鸣：声波
        if crow > 0 and cock_xy:
            x, face, sp = cock_xy
            k = ev_crow[1]
            hx, hy = x + face * 6, GY - sp.h - 1
            for r in range(3):
                rr = 3 + r * 3 + (k * 8) % 3
                g.d.arc((hx - rr, hy - rr, hx + rr, hy + rr), -60 if face > 0 else 120, 0 if face > 0 else 180, fill=1)
        if frozen is not None and cock_xy:  # 定住：头上三个点，慢慢出现
            x, face, sp = cock_xy
            k = ev_frz[1]
            for j in range(min(3, int((k - 1.0) * 1.5))):
                g.px(x - 2 + j * 3, GY - sp.h - 4)
        if ev_frz and frozen is not None and ev_frz[1] > 2.5:
            self.text(g, "望之似木鸡", span(ev_frz[1], 2.5, 3.5))
        else:
            self.text(g, "鸡犬相闻")
        self.mx(g, t, n, c, crow, frozen is not None)

    def text(self, g: Gfx, s: str, a: float = 1.0):
        g.d.rectangle((0, 0, 14, 63), fill=0)
        g.vtext(2, 1, s[:int(round(len(s) * clamp(a)))])

    def mx(self, g: Gfx, t: float, n: int, c: float, crow: float, frozen: bool):
        # 一只鸡：啄米时头一点一点；打鸣时伸脖子
        x, face, st = self.hen_at(n, c, 0)
        peck = (st == "peck" and (c * 4) % 1 < 0.5) or (st == "idle" and noise(t * 0.8, self.s) > 0.7)
        body = ["00000000", "00000000", "00000000", "10001110", "11011110", "11111110", "01111100", "00101000"]
        for y, row in enumerate(body):
            for xx, ch in enumerate(row):
                if ch == "1":
                    g.mx_set(xx, y)
        if crow > 0:
            g.mx_set(6, 1)
            g.mx_set(6, 2)
            g.mx_set(7, 0)
            g.mx_set(5, 0)
        elif peck:
            g.mx_set(7, 5)
            g.mx_set(7, 6)
        else:
            g.mx_set(6, 2)
            g.mx_set(5, 2)
            g.mx_set(7, 3)
        if frozen:
            g.mx_level = 1
        g.mx_set(1, 7)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        """端着瓢走出来，鸡从画外一只只跑进来"""
        T = self.T["enter"]
        self.fence(g)
        for h in range(self.NH):
            hx = self.home(h)[0]
            st = 0.3 + h * 0.35
            u = ease_out(span(t, st, st + 1.4))
            x = lerp(140 + h * 10, hx, u)
            name = ("cock" if h == 3 else "hen")
            sp = spr(name, -1 if u < 1 else (1 if h % 2 else -1))
            bob = 1 if (u < 1 and int(t * 8 + h) % 2) else 0
            g.blit(sp, x - sp.w // 2, GY - sp.h - bob)
        x = lerp(-12, X, ease_out(span(t, 0, 1.8)))
        bowl = (x + 5, GY - 13)
        daoshi(g, x, GY, 1, hands=[(x + 7, GY - 10), (bowl[0] - 1, bowl[1] + 2)], step=t * 11 if t < 1.7 else None)
        g.d.chord((bowl[0] - 6, bowl[1] - 4, bowl[0] + 4, bowl[1] + 4), 0, 180, fill=0, outline=1)
        g.d.line((bowl[0] - 6, bowl[1], bowl[0] + 4, bowl[1]), fill=1)
        g.d.line((bowl[0] - 6, bowl[1], bowl[0] - 10, bowl[1] - 2), fill=1)
        self.text(g, "鸡犬相闻", span(t, 1.2, T - 0.3))
        self.mx(g, t, 0, 0, 0, False)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.draw(g, t)

    def exit(self, g: Gfx, t: float):
        self.draw(g, self._ht, final=ease_in_out(span(t, 0, 0.5)))
        fade_box(g, 1 - ease_in(span(t, 0.35, self.T["exit"])))
        if t > 0.7:
            g.mx[:] = False
            g.mx[7, 1:7] = True
