"""挑水：小道士肩挑扁担两只木桶，走在山道上（横向卷动：远山、松树、石碑、小木桥依次经过）。
扁担随步子一颤一颤，水桶前后晃，偶尔泼出一滴。彩蛋：一只青蛙从前桶里跳出来；一只小鸟落在扁担头上搭一段顺风车。
左侧竖写“上善若水”（《道德经》第八章：上善若水，水善利万物而不争）。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import daoshi, event, fade_box

X = 58          # 道士在屏幕上的位置
V = 9.0         # 走路速度（像素/秒）
STEP_W = 4.6    # 步频（弧度/秒）
LAND = 300      # 地标间距（世界坐标）

FROG = [Sprite("""
.##.##.
#.###.#
.#####.
##...##
"""), Sprite("""
.##.##.
#.###.#
#######
##...##
""")]
FROG_JUMP = Sprite("""
..##.##.
..#.###.#
.#######.
#.......#
""")
BIRD = [Sprite("""
.##..
####.
.###.
..#..
"""), Sprite("""
#...#
.#.#.
..#..
""")]


def ground_y(wx: float) -> float:
    return 56.5 + 2.2 * math.sin(wx * 0.013) + 1.2 * math.sin(wx * 0.037 + 1.0)


def pine(g: Gfx, x: float, base: float, h: float):
    g.d.line((x, base, x, base - h), fill=1)
    for j in range(3):
        y = base - h + j * h * 0.28
        w = 3 + j * 2.5
        g.d.polygon([(x, y - 2), (x - w, y + h * 0.3), (x + w, y + h * 0.3)], fill=0, outline=1)


def bucket(g: Gfx, cx: float, top: float, ang: float, slosh: float):
    """木桶：上口中心 (cx, top)，ang 摆角"""
    c, s = math.cos(ang), math.sin(ang)

    def p(x, y):
        return cx + x * c - y * s, top + x * s + y * c
    body = [p(-5, 0), p(5, 0), p(4, 8), p(-4, 8)]
    g.d.polygon(body, fill=0, outline=1)
    g.d.line((*p(-4.7, 2.5), *p(4.7, 2.5)), fill=1)   # 箍
    g.d.line((*p(-4.2, 6), *p(4.2, 6)), fill=1)
    g.d.line((*p(-5, 0), *p(5, 0)), fill=1)
    # 水面一闪
    if slosh > 0.5:
        g.px(*p(-2 + slosh * 2, -1))


@register
class Water(Rest):
    id = "x5.water"
    name = "挑水"
    desc = "肩挑两桶水走在山道上，远山松树缓缓后退；青蛙从桶里跳出，小鸟落上扁担"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.s = self.rng.randrange(1000)
        self._ht = 0.0

    # ------------------------------------------------------------ 背景

    def scenery(self, g: Gfx, sc: float, t: float):
        # 远山（视差 0.2）
        ridge = []
        for x in range(-4, 136, 8):
            wx = x + sc * 0.2
            ridge.append((x, 18 + 12 * noise(wx * 0.025, self.s) + 3 * noise(wx * 0.09, self.s + 1)))
        g.d.line(ridge, fill=1)
        # 山脊下一层稀疏的点（远山的体积）
        for j, (x, y) in enumerate(ridge[:-1]):
            if j % 2 == 0:
                g.px(x + 3, y + 4)
            g.px(x + 6, y + 9 + (j % 3))
        # 云一缕
        cx = 140 - ((sc * 0.1 + 40) % 190)
        g.d.line((cx, 12, cx + 18, 12), fill=1)
        g.d.line((cx + 6, 10, cx + 22, 10), fill=1)
        # 中景松树（视差 0.55）
        m = sc * 0.55
        i0 = int((m - 20) // 64)
        for i in range(i0, i0 + 4):
            wx = i * 64 + rand(i, self.s) * 30
            x = wx - m
            if -12 < x < 140:
                pine(g, x, 43, 7 + rand(i + 7, self.s) * 5)
        # 地面
        pts = [(x, ground_y(x + sc)) for x in range(0, 132, 4)]
        bridge = self.bridge_span(sc)
        g.d.rectangle((0, 50, 127, 63), fill=0)
        g.d.line(pts, fill=1)
        for i in range(int((sc - 10) // 17), int((sc + 140) // 17) + 1):  # 石子、草
            wx = i * 17 + rand(i, self.s + 3) * 12
            x = wx - sc
            y = ground_y(wx)
            if bridge and bridge[0] - 2 < x < bridge[1] + 2:
                continue
            if rand(i, self.s + 4) < 0.5:
                g.d.ellipse((x - 2, y + 2, x + 2, y + 4), outline=1)
            else:
                g.d.line((x, y, x - 1, y - 2), fill=1)
                g.d.line((x + 1, y, x + 2, y - 3), fill=1)
        # 地标
        self.landmark(g, sc, t)

    def bridge_span(self, sc: float):
        """如果当前地标是小木桥，返回桥的屏幕区间"""
        for i in range(int((sc - 60) // LAND), int((sc + 160) // LAND) + 1):
            if i % 3 == 1:
                wx = i * LAND + 140
                return wx - sc, wx - sc + 26
        return None

    def landmark(self, g: Gfx, sc: float, t: float):
        for i in range(int((sc - 60) // LAND), int((sc + 160) // LAND) + 1):
            wx = i * LAND + 140
            x = wx - sc
            if not -40 < x < 150:
                continue
            kind = i % 3
            if kind == 0:  # 石碑：灵泉
                y = ground_y(wx + 7)
                g.d.rectangle((x - 1, y - 2, x + 15, y), fill=1)
                g.d.rectangle((x + 1, y - 28, x + 13, y - 2), fill=0, outline=1)
                g.d.arc((x + 1, y - 32, x + 13, y - 24), 180, 360, fill=1)
                g.vtext(x + 1, y - 26, "灵泉", gap=0)
            elif kind == 1:  # 小溪 + 木桥
                y = ground_y(wx)
                y2 = ground_y(wx + 26)
                g.d.rectangle((x, y - 1, x + 26, 63), fill=0)
                g.d.line((x - 1, y - 1, x + 27, y2 - 1), fill=1)       # 桥板
                g.d.line((x - 1, y, x + 27, y2), fill=1)
                for px in (x + 3, x + 13, x + 23):
                    g.d.line((px, y + 1, px, 63), fill=1)
                for j in range(3):  # 流水
                    yy = y + 4 + j * 2
                    ph = (t * 6 + j * 3) % 6
                    for xx in range(int(x + 1), int(x + 26), 6):
                        g.d.line((xx + ph, yy, xx + ph + 2, yy), fill=1)
            else:  # 一块大石头 + 草
                y = ground_y(wx + 8)
                g.d.polygon([(x, y), (x + 3, y - 7), (x + 10, y - 9), (x + 16, y - 4), (x + 18, y)], fill=0, outline=1)
                g.d.line((x + 5, y - 5, x + 8, y - 6), fill=1)
                g.d.line((x + 19, y, x + 21, y - 4), fill=1)

    # ------------------------------------------------------------ 人、扁担、水桶

    def carrier(self, g: Gfx, t: float, sc: float, x: float, walking: bool = True, look_back: bool = False,
                eye: str | None = None):
        stp = t * STEP_W if walking else None
        gy = ground_y(x + sc)
        bob = abs(math.sin(t * STEP_W)) * 1.2 if walking else 0.0
        sway = math.sin(t * STEP_W * 0.5 - 0.8) * 0.13 if walking else 0.0
        flex = math.sin(t * STEP_W * 2 - 1.2) * 1.3 if walking else 0.0   # 扁担的颤
        if eye is None:
            eye = "closed" if (t % 3.9) < 0.14 else "open"
        sy = gy - 21 - (1 - bob) * 0  # daoshi 的肩
        pole_y = gy - 22 + bob * 0.5
        front, back = x + 22, x - 21
        sag = 2.2 + flex
        pts = [(back, pole_y + sag), (x - 8, pole_y + sag * 0.3), (x, pole_y), (x + 8, pole_y + sag * 0.3),
               (front, pole_y + sag)]
        # 后桶（在人后面）
        bt = pole_y + sag + 7
        bx = back + math.sin(sway) * 7
        g.d.line((back, pole_y + sag, bx - 4, bt), fill=1)
        g.d.line((back, pole_y + sag, bx + 4, bt), fill=1)
        bucket(g, bx, bt, sway, noise(t * 3, 1))
        pz = daoshi(g, x, gy, 1, hands=[(x + 9, pole_y + sag * 0.35 + 0.5), None], step=stp, lean=1.0, eye=eye,
                    look=-1 if look_back else 0)
        g.d.line(pts, fill=1)
        g.d.line([(px, py + 1) for px, py in pts[1:4]], fill=1)
        g.d.rectangle((x + 8, pole_y + sag * 0.35, x + 10, pole_y + sag * 0.35 + 1.5), fill=1)  # 近手压在扁担上
        ft = pole_y + sag + 7
        fx = front + math.sin(sway * 0.8 + 0.4) * 7
        g.d.line((front, pole_y + sag, fx - 4, ft), fill=1)
        g.d.line((front, pole_y + sag, fx + 4, ft), fill=1)
        bucket(g, fx, ft, sway * 0.8 + 0.4 * (sway != 0) * 0, noise(t * 3, 2))
        self._front = (fx, ft)
        self._back = (back, pole_y + sag)
        self._pz = pz
        # 偶尔泼出一滴
        if walking:
            n = int(t * STEP_W / math.pi)
            k = (t * STEP_W / math.pi) - n
            if rand(n, self.s) < 0.3:
                side = fx if rand(n + 1, self.s) < 0.6 else bx
                g.px(side + 5 - k * 3, ft + k * k * 16)
        return pz, sway

    # ------------------------------------------------------------ 彩蛋

    def frog(self, g: Gfx, t: float, sc: float, ev):
        """青蛙从前桶跳出 → 落在路上 → 被甩到身后"""
        n, k = ev
        if k < 1.0:  # 在桶口探头
            fx, ft = self._front
            if int(k * 6) % 2:
                g.blit(FROG[0], fx - 2, ft - 3)
            else:
                g.blit(FROG[0], fx - 2, ft - 2)
            return False
        jump_from = self._front
        land_wx = getattr(self, "_frog_land", None)
        if land_wx is None or getattr(self, "_frog_n", -1) != n:
            # 落点（世界坐标）在前方 18 像素处：按事件开始时刻算，保持确定性
            t_jump = t - (k - 1.0)
            land_wx = (X + 40) + t_jump * V
            self._frog_land, self._frog_n = land_wx, n
        u = span(k, 1.0, 1.7)
        lx = land_wx - sc
        ly = ground_y(land_wx) - 4
        if u < 1:
            x = lerp(jump_from[0], lx, u)
            y = lerp(jump_from[1] - 3, ly, u) - math.sin(u * math.pi) * 14
            g.blit(FROG_JUMP, x - 3, y)
        else:  # 蹲在路上，鼓腮，再跳两下
            hop = (k - 1.7) % 2.0
            if hop < 0.4:
                y = ly - math.sin(hop / 0.4 * math.pi) * 5
                g.blit(FROG_JUMP, lx - 3 - hop * 8, y)
            else:
                g.blit(FROG[int(k * 3) % 2], lx - 3 - min(hop, 0.4) * 8, ly)
        return 1.0 <= k < 2.2

    def bird(self, g: Gfx, t: float, ev):
        n, k = ev
        bx, by = self._back
        if k < 1.2:  # 飞来
            u = ease_out(k / 1.2)
            x, y = lerp(-8, bx, u), lerp(8, by - 4, u) - math.sin(u * math.pi) * 6
            g.blit(BIRD[1 if int(k * 8) % 2 else 0], x - 2, y)
        elif k < 7.0:  # 站在扁担头上，偶尔啄一下
            peck = 1 if (k % 1.7) < 0.15 else 0
            g.blit(BIRD[0], bx - 2, by - 4 + peck)
        else:  # 飞走
            u = ease_in(span(k, 7.0, 8.5))
            g.blit(BIRD[1 if int(k * 8) % 2 else 0], bx - 2 + u * 40, by - 4 - u * 30)

    # ------------------------------------------------------------ 阶段

    def text(self, g: Gfx, a: float = 1.0):
        g.d.rectangle((0, 0, 14, 63), fill=0)
        s = "上善若水"
        g.vtext(2, 2, s[:int(round(len(s) * clamp(a)))])

    def mx(self, g: Gfx, t: float, sway: float):
        # 水桶剖面：桶壁 + 晃动的水面
        for y in range(2, 8):
            g.mx_set(0, y)
            g.mx_set(7, y)
        g.mx[7, :] = True
        tilt = sway * 14
        for x in range(1, 7):
            lvl = 3.5 + (x - 3.5) * tilt * 0.35 + math.sin(t * 5 + x) * 0.3
            yy = int(round(lvl))
            g.mx_set(x, yy)
            for y in range(yy + 1, 7):
                if (x + y + int(t * 4)) % 3 == 0:
                    g.mx_set(x, y)

    def scene(self, g: Gfx, t: float, sc: float, x: float = X, walking: bool = True):
        self.scenery(g, sc, t)
        ev_f = event(t, 47.0, 9.0, self.s + 1)
        ev_b = event(t + 20, 71.0, 8.5, self.s + 2)
        surprised = False
        pz, sway = self.carrier(g, t, sc, x, walking, eye="closed" if ev_f and 2.2 < ev_f[1] < 4 else None)
        if ev_f and walking:
            if self.frog(g, t, sc, ev_f):
                surprised = True
        if ev_b and walking:
            self.bird(g, t, ev_b)
        if surprised:
            hx, hy = pz.head
            g.d.line((hx + 3, hy - 13, hx + 3, hy - 10), fill=1)
            g.px(hx + 3, hy - 8)
        self.text(g)
        self.mx(g, t, sway)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        p = span(t, 0, T)
        x = lerp(-26, X, ease_out(p) * 0.4 + p * 0.6)
        self.scenery(g, 0, t)
        self.carrier(g, t, 0, x, True)
        self.text(g, span(t, 1.2, T - 0.3))
        self.mx(g, t, math.sin(t * STEP_W * 0.5 - 0.8) * 0.13)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        # 入场是人走进画面（背景不动），持续阶段镜头跟着走：从 t=0 起背景缓缓后退
        sc = V * t
        self.scene(g, t, sc)

    def exit(self, g: Gfx, t: float):
        t0 = self._ht
        # 收住脚步：停下、放平扁担
        self.scenery(g, V * t0, t0)
        self.carrier(g, t0 + t * 0.3, V * t0, X, walking=t < 0.3, eye="closed" if t > 0.4 else None)
        self.text(g)
        self.mx(g, t0, 0)
        fade_box(g, 1 - ease_in(span(t, 0.3, self.T["exit"])))
        if t > 0.7:
            g.mx[:] = False
