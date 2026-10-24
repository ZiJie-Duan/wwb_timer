"""采药：悬崖半腰一块石台，小道士背着竹篓，拿药锄在石缝里刨药，连根拔起，往肩后一甩丢进背篓。
崖顶一棵老松探出身子，脚下是云海，远峰露尖；云一团团飘过。
彩蛋：偶尔一团厚云整个把他吞没——“云深不知处”；偶尔石缝里长的是一朵灵芝，闪着光。
贾岛《寻隐者不遇》：松下问童子，言师采药去。只在此山中，云深不知处。
入场：云散开露出人；收场：云合拢。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import cloud
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x5_common import daoshi, dpoly, event, fade_box, phase

LEDGE = 46
X = 82
P = 9.0
SPOTS = [(37, -1.0), (29, 0.0), (42, 0.6)]   # 石缝的 y，人要抬手（负）/ 蹲（正）
HERB = Sprite("""
.#.#.
#.#.#
.###.
..#..
..#..
""")
LINGZHI = Sprite("""
.#####.
#######
.#...#.
...#...
...#...
""")


def wall_x(y: float) -> float:
    """崖壁左边缘"""
    return 94 + 2.5 * math.sin(y * 0.33) + 1.5 * math.sin(y * 0.9 + 1)


@register
class Herbs(Rest):
    id = "x5.herbs"
    name = "采药"
    desc = "悬崖石台上背篓刨药，云海翻涌，偶尔一团云把人吞没——云深不知处"
    T = {"enter": 3.0, "exit": 1.5}

    def setup(self):
        self.s = self.rng.randrange(1000)
        self._ht = 0.0

    # ------------------------------------------------------------ 景

    def backdrop(self, g: Gfx, t: float):
        # 远峰
        for cx, h, w in ((14, 22, 13), (34, 14, 10), (56, 18, 12)):
            g.d.polygon([(cx - w, 56), (cx - 2, 56 - h), (cx + 1, 56 - h + 2), (cx + w, 56)], fill=0, outline=1)
            g.d.line((cx - 2, 56 - h, cx - 4, 56 - h * 0.5), fill=1)
        # 云海：几道起伏的线向左缓缓流
        for j in range(3):
            y = 52 + j * 4
            pts = []
            for x in range(0, 82, 4):
                pts.append((x, y + math.sin((x + t * (4 + j * 2)) * 0.12 + j) * 1.5))
            g.d.rectangle((0, y - 1, 80, y + 4), fill=0)
            g.d.line(pts, fill=1)
        # 远远一只鹤（小 v）
        bx = 70 - (t * 3 + 30) % 110
        g.d.line((bx - 2, 18, bx, 20, bx + 2, 18), fill=1)

    def cliff(self, g: Gfx, t: float):
        edge = [(wall_x(y), y) for y in range(0, LEDGE + 1, 3)]
        wall = edge + [(128, LEDGE), (128, 0)]
        dpoly(g, wall, 0.07, None)
        g.d.line(edge, fill=1)
        # 石台 + 下面的崖
        drop = [(66, LEDGE), (wall_x(LEDGE), LEDGE), (128, LEDGE), (128, 64), (72, 64), (70, 56), (64, 50)]
        dpoly(g, drop, 0.07, None)
        g.d.line((64, LEDGE, 128, LEDGE), fill=1)
        g.d.line((64, LEDGE, 64, 50), fill=1)
        g.d.line((64, 50, 70, 56, 72, 64), fill=1)
        for y0, x0 in ((10, 104), (22, 112), (34, 106), (54, 92)):  # 裂纹
            g.d.line((x0, y0, x0 + 3, y0 + 5, x0 + 1, y0 + 9), fill=1)
        # 崖顶老松，探向云海
        sway = (noise(t * 0.5, 3) - 0.5) * 1.5
        g.d.line((104, 2, 96, 6, 86, 7 + sway * 0.3, 78, 5 + sway * 0.5), fill=1)
        g.d.line((104, 3, 96, 7, 86, 8 + sway * 0.3), fill=1)
        for cx, cy, w in ((80, 4, 9), (90, 3, 7), (73, 8, 6)):
            cy += sway * 0.5
            g.d.ellipse((cx - w, cy - 2, cx + w, cy + 2), fill=0, outline=1)
            for k in range(-w + 2, w - 1, 3):
                g.px(cx + k, cy)

    # ------------------------------------------------------------ 草药

    def herb_state(self, t: float, j: int):
        """石缝 j 上的草药：(长到多少 0..1, 是不是灵芝)。被采了之后慢慢长回来"""
        n, c = phase(t, P)
        # 最近一次采 j 的轮
        m = n - ((n - j) % 3)
        if m == n and c < 3.4:
            m -= 3
        if m < 0:
            return 1.0, self.lingzhi(j if j >= 0 else 0, j)
        since = (n - m) * P + c - 3.4
        nxt = m + 3
        return clamp(since / (2 * P)), self.lingzhi(nxt, j)

    def lingzhi(self, n: int, j: int) -> bool:
        return rand(n, self.s + 11) < 0.25

    def draw_herb(self, g: Gfx, j: int, grow: float, lz: bool, t: float, dx: float = 0, dy: float = 0):
        y, _ = SPOTS[j]
        x = wall_x(y) - 4
        if grow <= 0.05:
            return
        spr = LINGZHI if lz else HERB
        if grow < 1:
            h = max(1, int(spr.h * grow))
            g.d.line((x + 1, y, x + 1, y - h), fill=1)
            if grow > 0.5:
                g.px(x, y - h)
                g.px(x + 2, y - h)
            return
        g.blit(spr, x - spr.w // 2 + 1 + dx, y - spr.h + dy)
        if lz and (t * 2 + j) % 1.6 < 0.5:  # 灵芝闪光
            g.px(x - 4 + dx, y - 6 + dy)
            g.px(x + 5 + dx, y - 3 + dy)
            g.px(x + 1 + dx, y - 8 + dy)

    # ------------------------------------------------------------ 人

    def basket(self, g: Gfx, bx: float, by: float, n: int):
        """背篓：上口 (bx, by)，里面露出 n 株药"""
        for i in range(min(n, 5)):
            hx = bx - 3 + i * 1.6
            g.d.line((hx, by, hx - 1 + (i % 2) * 2, by - 3 - (i % 3)), fill=1)
            g.px(hx - 2 + (i % 2) * 4, by - 4 - (i % 3))
        pts = [(bx - 5, by), (bx + 3, by), (bx + 2, by + 12), (bx - 4, by + 12)]
        g.d.polygon(pts, fill=0, outline=1)
        for k in range(3, 12, 3):  # 竹编
            g.d.line((bx - 4.8 + k * 0.07, by + k, bx + 2.8 - k * 0.07, by + k), fill=1)
        for k in (-2, 1):
            g.d.line((bx + k, by + 1, bx + k, by + 11), fill=1)

    def picker(self, g: Gfx, t: float, n: int, c: float, final: float = 0.0):
        j = n % 3
        sy_, cr = SPOTS[j]
        spot = (wall_x(sy_) - 3, sy_ - 2)
        crouch = max(0.0, cr) * math.sin(span(c, 0, 0.6) * math.pi / 2) * (1 - span(c, 4.6, 5.4))
        lean = 2.0
        look = 0.0
        eye = "closed" if (t % 3.9) < 0.14 else "open"
        f = 1
        hoe = None
        hand = None
        far = None
        held = None
        picks = n + (1 if c >= 4.4 else 0)
        if c < 0.6:  # 抬锄
            q = ease_in_out(c / 0.6)
            hand = (lerp(X + 6, spot[0] - 5, q), lerp(LEDGE - 12, spot[1] - 6, q))
            hoe = (hand, lerp(1.2, -0.6, q))
        elif c < 3.0:  # 刨三下
            k = ((c - 0.6) / 0.8) % 1
            dig = math.sin(k * math.pi) if k < 0.5 else 0
            hit = k < 0.25
            hand = (spot[0] - 6 + (1 - k) * 0, spot[1] - 5 + (0 if hit else -3 * math.sin((k - 0.25) / 0.75 * math.pi)))
            hoe = (hand, -0.6 + (0.9 if hit else 0.9 * (1 - math.sin((k - 0.25) / 0.75 * math.pi))))
            if k < 0.3:  # 碎石
                for i in range(3):
                    g.px(spot[0] - 1 - k * 10 * (i + 1) * 0.5, spot[1] + 1 - k * 8 + k * k * 30 * (i % 2))
        elif c < 3.4:  # 放下锄，伸手抓住
            q = ease_in_out(span(c, 3.0, 3.4))
            hand = (lerp(spot[0] - 6, spot[0] - 2, q), lerp(spot[1] - 5, spot[1] - 2, q))
            far = (X + 2, LEDGE - 12)
            hoe = ((X + 3, LEDGE - 11), 1.4)
        elif c < 4.0:  # 连根拔起
            q = ease_out(span(c, 3.4, 4.0))
            hand = (spot[0] - 2 - q * 4, spot[1] - 2 - q * 6)
            held = hand
            hoe = ((X + 3, LEDGE - 11), 1.4)
            lean = 2 - q * 3
        elif c < 4.4:  # 往肩后一甩
            q = ease_in(span(c, 4.0, 4.4))
            hand = (lerp(spot[0] - 6, X - 2, q), lerp(spot[1] - 8, LEDGE - 30, q))
            if q < 0.6:
                held = hand
            hoe = ((X + 3, LEDGE - 11), 1.4)
            lean = -1 - q
        else:  # 站着歇口气，回头望云
            q = span(c, 4.4, 5.0)
            hand = (lerp(X - 2, X + 4, q), lerp(LEDGE - 30, LEDGE - 11, ease_out(q)))
            hoe = ((X + 3, LEDGE - 11), 1.4)
            if 5.6 < c < 8.2:
                f = -1
                look = -0.5
            lean = 0
        if final > 0:
            hand = (lerp(hand[0], X + 4, final), lerp(hand[1], LEDGE - 11, final))
        # 背篓在背后（f=1 时在左边）
        sy = LEDGE - (21 - 6 * crouch)
        self.basket(g, X - f * 6 + lean * f * 0.5, sy + 1, picks)
        # 被甩出去的药草在空中
        if 4.2 <= c < 4.8:
            u = span(c, 4.2, 4.8)
            x = lerp(X - 2, X - 7, u)
            y = lerp(LEDGE - 30, sy - 1, u) - math.sin(u * math.pi) * 6
            g.blit(HERB, x - 2, y - 3)
        pz = daoshi(g, X, LEDGE, f, hands=[hand if f == 1 else (X - 4, LEDGE - 11), far], crouch=crouch, lean=lean,
                    eye=eye, look=look)
        if hoe and f == 1:
            (hx, hy), a = hoe
            ex, ey = hx + math.cos(a) * 11, hy + math.sin(a) * 11
            g.d.line((hx - math.cos(a) * 3, hy - math.sin(a) * 3, ex, ey), fill=1)
            # 锄刃：垂直于柄，朝下
            nx, ny = -math.sin(a), math.cos(a)
            if ny < 0:
                nx, ny = -nx, -ny
            g.d.polygon([(ex - math.cos(a), ey - math.sin(a)), (ex + nx * 5 - math.cos(a) * 1.5, ey + ny * 5 - math.sin(a) * 1.5),
                         (ex + nx * 5 + math.cos(a) * 2, ey + ny * 5 + math.sin(a) * 2), (ex + math.cos(a), ey + math.sin(a))],
                        fill=1)
            g.d.rectangle((hx - 1, hy - 1, hx + 1, hy + 1), fill=1)
        if held:
            hx, hy = held
            lz = self.herb_state(t, j)[1] if c < 3.4 else self.lingzhi(n, j)
            spr = LINGZHI if lz else HERB
            g.blit(spr, hx - spr.w // 2, hy - spr.h)
            g.d.line((hx, hy, hx - 1, hy + 3), fill=1)   # 根须
            g.d.line((hx, hy, hx + 1, hy + 4), fill=1)
        return pz

    # ------------------------------------------------------------ 云

    def drift_clouds(self, g: Gfx, t: float):
        for i in range(3):
            sp = 3 + i * 1.5
            span_w = 200
            cx = 150 - ((t * sp + i * 70 + self.s) % span_w)
            cy = 22 + i * 9 + math.sin(t * 0.3 + i) * 2
            if cx < 70:
                cloud(g, cx, cy, 22 - i * 3, 7, seed=i + 3)

    def cover(self, g: Gfx, cov: float, t: float, seed: int = 0):
        """厚云盖过来：cov 0..1 = 盖住的程度（从左往右推）"""
        if cov <= 0:
            return
        front = -40 + cov * 190
        for k in range(9):
            cx = front - k * 22 + math.sin(t * 0.8 + k) * 2
            for row in range(3):
                cy = 10 + row * 20 + (k % 2) * 6
                if cx > -30:
                    cloud(g, cx, cy, 34, 18, seed=seed + k * 3 + row)
        if front - 170 > 0:
            g.d.rectangle((0, 0, front - 170, 63), fill=0)

    def text(self, g: Gfx, s: str, a: float = 1.0):
        n = int(round(len(s) * clamp(a)))
        g.d.rectangle((0, 0, 13, 63), fill=0)
        g.vtext(1, 1, s[:n])

    # ------------------------------------------------------------ 阶段

    def draw(self, g: Gfx, t: float, final: float = 0.0):
        n, c = phase(t, P)
        self.backdrop(g, t)
        self.drift_clouds(g, t)
        self.cliff(g, t)
        for j in range(3):
            if j == n % 3 and 3.4 <= c:
                continue
            gr, lz = self.herb_state(t, j)
            self.draw_herb(g, j, gr, lz, t)
        self.picker(g, t, n, c, final)
        ev = event(t, 47.0, 9.0, self.s + 1)
        cov = 0.0
        if ev:
            k = ev[1]
            cov = ease_in_out(span(k, 0, 3.0)) * (1 - ease_in_out(span(k, 6.0, 9.0)))
            self.cover(g, cov, t, ev[0])
        self.text(g, "云深不知处" if cov > 0.5 else "只在此山中")
        self.mx(g, t, n, c, cov)

    def mx(self, g: Gfx, t: float, n: int, c: float, cov: float):
        if cov > 0.6:  # 云：一团团流过
            for y in range(8):
                for x in range(8):
                    g.mx[y, x] = noise(x * 0.5 + t * 1.5 + y * 0.3, y) > 0.55
            return
        j = n % 3
        lz = self.lingzhi(n, j) if c >= 3.4 else self.herb_state(t, j)[1]
        if lz:  # 灵芝
            g.mx_rows([0b00111100, 0b01111110, 0b11111111, 0b01011010, 0b00011000, 0b00011000, 0b00011000, 0])
            if 3.4 <= c < 4.4:
                g.mx_level = 5
        else:  # 一株草药，被拔起时往上走、露出根
            up = int(ease_out(span(c, 3.4, 4.0)) * 2) if 3.4 <= c < 4.4 else 0
            spr = ["01011010", "10100101", "01011010", "00111100", "00011000", "00011000"]
            for r, row in enumerate(spr):
                for x, ch in enumerate(row):
                    if ch == "1":
                        g.mx_set(x, r + 1 - up)
            if up:
                g.mx_set(3, 7 - up + 1)
                g.mx_set(4, 7)
            else:
                g.mx[7, :] = True

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        self.draw(g, 0.0)
        cov = 1 - ease_in_out(span(t, 0.2, T - 0.2))
        # 云散开：从右往左退
        if cov > 0:
            self.cover(g, cov, t, 99)
        self.text(g, "只在此山中", span(t, 1.5, T - 0.2))

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.draw(g, t)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        self.draw(g, self._ht, final=ease_in_out(span(t, 0, 0.4)))
        self.cover(g, ease_in_out(span(t, 0.0, T * 0.8)), self._ht + t, 77)
        if t < 0.25:
            self.text(g, "只在此山中")
        else:
            self.text(g, "云深不知处", span(t, 0.25, 0.9))
        fade_box(g, 1 - ease_in(span(t, T * 0.7, T)))
