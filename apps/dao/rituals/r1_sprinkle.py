"""洒净：宽袖手执柳枝，蘸净水盂里的法水，一甩一甩洒向四方，水珠划弧落下闪光；左侧逐句念《净天地神咒》。

依据：科仪开坛先“洒净”（荡秽）：高功以柳枝（或杨枝）蘸净水洒坛，诵《净天地神咒》：
“天地自然，秽炁分散。洞中玄虚，晃朗太玄。八方威神，使我自然。灵宝符命，普告九天。乾罗答那，洞罡太玄。
斩妖缚邪，杀鬼万千。中山神咒，元始玉文。持诵一遍，却病延年。按行五岳，八海知闻。魔王束首，侍卫我轩。
凶秽消散，道炁长存。急急如律令。”（字库无“炁”，以“气”代）

入场：净水盂落在画面里，宽袖手执柳枝从右边伸来，第一句咒出现。
持续：每 6 秒一个动作：蘸水 → 提起 → 一甩，十二颗水珠成扇形飞出、划抛物线落下（方向轮流变）。
      一轮 600 秒念完全咒二十二句（左侧竖排本句）；柳叶每甩几下掉一片，盂里的水慢慢浅下去。
      一轮结束：旧枝收回，天降甘露把盂注满，手换一枝新柳再来。
中断：柳枝横放在盂沿上，手收走。
恢复：手回来拿起柳枝。
圆满：柳枝绕手一转，水珠四面八方洒开，满屏闪光，“急急如律令”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, \
    rand, span
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import sleeve, sparkles

MANTRA = ["天地自然", "秽气分散", "洞中玄虚", "晃朗太玄", "八方威神", "使我自然", "灵宝符命", "普告九天",
          "乾罗答那", "洞罡太玄", "斩妖缚邪", "杀鬼万千", "中山神咒", "元始玉文", "持诵一遍", "却病延年",
          "按行五岳", "八海知闻", "魔王束首", "侍卫我轩", "凶秽消散", "道气长存"]
BCX, RIM, BBOT = 82, 44, 56   # 净水盂
BHW = 15
WATER_FULL, WATER_LOW = 46, 52
PERIOD = 6.0
FLICK = 2.45
LEAVES = 11
TWIG = 28
GRAV = 70.0
GROUND = 63
RENEW = 6.0
# 动作关键帧：(时刻, 手 x, 手 y, 枝角度)。枝角度：0 = 向右，π = 向左，π/2 = 向下
REST = (106, 24, 2.55)
KEYS = [(0.0, *REST), (0.4, *REST), (1.3, 104, 30, 2.42), (1.7, 104, 30, 2.42), (2.2, 110, 17, 3.55),
        (2.45, 96, 20, 2.8), (2.7, 98, 22, 2.65), (4.2, *REST), (PERIOD, *REST)]
DIRS = (-2.3, -1.9, -2.7)  # 水珠飞出的方向（左上、上、左）


def pose(u: float):
    """动作周期内 u 秒时的 (手 x, 手 y, 枝角)"""
    for (t0, x0, y0, a0), (t1, x1, y1, a1) in zip(KEYS, KEYS[1:]):
        if t0 <= u <= t1:
            p = (u - t0) / (t1 - t0) if t1 > t0 else 1
            p = ease_in(p) if t0 == 2.2 else ease_in_out(p)
            return lerp(x0, x1, p), lerp(y0, y1, p), lerp(a0, a1, p)
    return REST


def twig_pts(hx: float, hy: float, ang: float, n: int = 8):
    """柳枝主干：从手里伸出，梢头下垂"""
    pts = []
    for i in range(n + 1):
        s = i / n * TWIG
        pts.append((hx + math.cos(ang) * s, hy + math.sin(ang) * s + (s / TWIG) ** 2 * 5))
    return pts


def willow(g: Gfx, hx: float, hy: float, ang: float, leaves: int, t: float, seed: int, wet: bool = False):
    pts = twig_pts(hx, hy, ang)
    g.d.line(pts, fill=1)
    for j in range(leaves):  # 柳叶：沿枝挂下，细长
        s = 0.25 + 0.75 * (j + 0.5) / LEAVES
        i = min(int(s * 8), 7)
        f = s * 8 - i
        x = lerp(pts[i][0], pts[i + 1][0], f)
        y = lerp(pts[i][1], pts[i + 1][1], f)
        sw = (noise(t * 1.5 + j, seed) - 0.5) * 2
        ln = 5 + (j % 3)
        g.d.line((x, y + 1, x + sw, y + ln), fill=1)
        g.px(x + sw * 1.2 + (1 if j % 2 else -1), y + ln + 1)
    tip = pts[-1]
    if wet:
        g.px(tip[0], tip[1] + 2)
    return tip


def bowl(g: Gfx, level: float, t: float, ripple: float = 0.0):
    d = g.d
    wy = lerp(WATER_FULL, WATER_LOW, level)
    d.chord((BCX - BHW, RIM - 12, BCX + BHW, BBOT), 0, 180, fill=0, outline=1)
    # 水：抖动
    hw = BHW * math.sqrt(max(0.0, 1 - ((wy - (RIM - 12 + BBOT) / 2) / ((BBOT - RIM + 12) / 2)) ** 2)) - 1
    poly = [(BCX - hw, wy)]
    for i in range(9):
        a = math.pi * i / 8
        x = BCX - math.cos(a) * (BHW - 1)
        y = (RIM - 12 + BBOT) / 2 + math.sin(a) * ((BBOT - RIM + 12) / 2 - 1)
        if y > wy:
            poly.append((x, y))
    poly.append((BCX + hw, wy))
    if len(poly) >= 3:
        g.shade_poly(poly, 0.3, outline=None)
    d.line((BCX - hw, wy, BCX + hw, wy), fill=1)
    if ripple > 0:  # 蘸水的涟漪
        r = (1 - ripple) * 10 + 2
        d.line((BCX - 4 - r, wy - 1, BCX - 4 - r + 3, wy - 1), fill=1)
        d.line((BCX - 4 + r - 3, wy - 1, BCX - 4 + r, wy - 1), fill=1)
    d.line((BCX - BHW - 2, RIM, BCX + BHW + 2, RIM), fill=1)          # 口沿
    d.rectangle((BCX - 5, BBOT, BCX + 5, BBOT + 2), fill=0, outline=1)  # 足
    d.line((BCX - 9, BBOT + 4, BCX + 9, BBOT + 4), fill=1)
    d.line((BCX - 7, BBOT + 3, BCX + 7, BBOT + 3), fill=1)
    for x in (-9, -3, 3, 9):  # 莲瓣纹
        d.arc((BCX + x - 3, RIM + 1, BCX + x + 3, RIM + 7), 0, 180, fill=1)


@register
class Sprinkle(Ritual):
    id = "r1.sprinkle"
    name = "洒净"
    desc = "柳枝蘸净水，一甩一甩洒向四方，水珠划弧闪光；左侧逐句念净天地神咒"
    T = {"enter": 3.6, "interrupt": 1.6, "resume": 1.6, "complete": 5.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 状态

    def leaves(self, k: float) -> int:
        return LEAVES - int(clamp(k / self.CYCLE) * (LEAVES - 3))

    def level(self, k: float) -> float:
        return clamp(k / self.CYCLE)

    def phrase(self, k: float) -> int:
        return min(len(MANTRA) - 1, int(k / self.CYCLE * len(MANTRA)))

    # ------------------------------------------------------------ 零件

    def drops(self, g: Gfx, t: float, x0: float, y0: float, m: int, age: float, n: int = 12, spread: float = 1.3,
              base: float | None = None, speed: float = 80):
        """第 m 甩的水珠，甩出 age 秒后"""
        if age < 0 or age > 3.0:
            return
        d0 = DIRS[m % 3] if base is None else base
        for i in range(n):
            a = d0 + (rand(i, m * 13 + self.seed) - 0.5) * spread
            v = speed * (0.6 + 0.6 * rand(i + 40, m * 13 + self.seed))
            x = x0 + math.cos(a) * v * age
            y = y0 + math.sin(a) * v * age + 0.5 * GRAV * age * age
            if y >= GROUND:  # 落地：一点闪
                tl = age - self.land_time(y0, math.sin(a) * v)
                if tl < 0.35:
                    xx = x0 + math.cos(a) * v * (age - tl)
                    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, -1)):
                        g.px(xx + dx * (1 + tl * 6), GROUND - 1 + dy * (1 + tl * 4))
                continue
            g.px(x, y)
            g.px(x - math.cos(a) * 0.8, y - 1)  # 水珠拖一点尾
            vy = math.sin(a) * v + GRAV * age
            if abs(vy) < 12 and i % 2 == 0:  # 抛物线顶点：一闪
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    g.px(x + dx * 2, y + dy * 2)

    @staticmethod
    def land_time(y0: float, vy: float) -> float:
        # y0 + vy t + 0.5 g t² = GROUND
        a, b, c = 0.5 * GRAV, vy, y0 - GROUND
        disc = b * b - 4 * a * c
        return (-b + math.sqrt(max(disc, 0))) / (2 * a)

    def mantra(self, g: Gfx, k: float, a: float = 1.0):
        i = self.phrase(k)
        since = k - i * self.CYCLE / len(MANTRA)
        cur = MANTRA[i]
        typed = 1.0 if i == 0 else clamp(since / 1.2)  # 第一句入场时已写出
        n = int(typed * 4 * clamp(a) + 1e-6)
        g.vtext(2, 2, cur[:n])

    def falling_leaf(self, g: Gfx, k: float, t: float):
        """柳叶掉落：每次少一片叶时，一片叶从枝上飘到地上（e 定时）"""
        per = self.CYCLE / (LEAVES - 3)
        u = k % per
        if k < per or u > 3.0:
            return
        x = 74 - u * 6 + math.sin(u * 4) * 3
        y = 30 + u * 11
        if y < GROUND:
            g.d.line((x, y, x + 2 + math.sin(u * 5), y + 2), fill=1)

    def mx(self, g: Gfx, t: float, phase: float, level: float):
        g.mx[7, 2:6] = True
        g.mx[6, 1:7] = True
        if level < 0.6:
            g.mx[5, 1:7] = True
        u = phase
        if 0.5 < u < 1.6:  # 枝点进水
            g.mx[4, 4] = True
            g.mx[3, 5] = True
        elif FLICK <= u < FLICK + 1.6:  # 水珠飞起、落下
            a = u - FLICK
            for i, dx in enumerate((-2, 0, 2)):
                x = 3.5 + dx * a * 1.6
                y = 4 - 6 * a + 6 * a * a
                g.mx_set(round(x), round(y))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        drop = ease_out_bounce(span(t, 0, 0.9))
        g_off = lerp(-60, 0, drop)
        if drop > 0:
            # 先画到临时位置：整体平移太麻烦，盂直接画在落点，入场时上面盖黑
            bowl(g, 0, t)
            if drop < 1:
                g.d.rectangle((BCX - BHW - 3, 0, BCX + BHW + 3, 63), fill=0)
                d = g.d
                y = RIM + g_off
                d.chord((BCX - BHW, y - 12, BCX + BHW, y + BBOT - RIM), 0, 180, fill=0, outline=1)
                d.line((BCX - BHW - 2, y, BCX + BHW + 2, y), fill=1)
        p = ease_out(span(t, 0.9, 2.2))
        hx, hy, ang = REST
        hx, hy = lerp(160, hx, p), lerp(10, hy, p)
        willow(g, hx, hy, ang + (1 - p) * 0.4, LEAVES, t, self.seed)
        sleeve(g, hx + 3, hy, -0.15)
        self.mantra(g, 0, a=span(t, 2.2, 3.4))
        self.mx(g, t, 0, 0)
        if t < 0.9:
            g.mx[5:, :] = False

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        lv = self.level(k)
        u = t % PERIOD
        m = int(t // PERIOD)
        hx, hy, ang = pose(u)
        rip = 1 - span(u, 1.2, 2.0) if u > 1.2 else 0
        self.mantra(g, k)
        bowl(g, lv, t, ripple=rip)
        self.falling_leaf(g, k, t)
        tip = willow(g, hx, hy, ang, self.leaves(k), t, self.seed, wet=1.7 < u < FLICK)
        sleeve(g, hx + 3, hy, -0.15)
        # 这一甩、上一甩的水珠
        for mm, age in ((m, u - FLICK), (m - 1, u + PERIOD - FLICK)):
            if mm >= 0:
                fx, fy, fa = pose(FLICK)
                tp = twig_pts(fx, fy, fa)[-1]
                self.drops(g, t, tp[0], tp[1], mm, age)
        self.mx(g, t, u, lv)

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """换一枝新柳；天降甘露注满净水盂"""
        fill = ease_in_out(span(k, 1.2, 3.6))
        lv = 1 - fill
        self.mantra(g, self.CYCLE - 1 if k < 1.0 else 0, a=1 if k < 1.0 else span(k, 3.6, 4.8))
        if 1.0 < k < 3.8:  # 甘露：三道细流从天而降
            for j, x in enumerate((76, 82, 88)):
                for y in range(0, int(lerp(WATER_LOW, WATER_FULL, fill)) - 1):
                    if (y + int(t * 50) + j * 3) % 6 < 2:
                        g.px(x + math.sin(y * 0.2 + j) * 0.8, y)
        bowl(g, lv, t, ripple=(k * 2) % 1 if 1.2 < k < 3.6 else 0)
        hx, hy, ang = REST
        if k < 1.2:
            p = ease_in(span(k, 0, 1.2))
            x, y = lerp(hx, 160, p), lerp(hy, 0, p)
            willow(g, x, y, ang, 3, t, self.seed)
            sleeve(g, x + 3, y, -0.15)
        elif k > 3.6:
            p = ease_out(span(k, 3.6, RENEW))
            x, y = lerp(160, hx, p), lerp(0, hy, p)
            willow(g, x, y, ang + (1 - p) * 0.4, LEAVES, t, self.seed)
            sleeve(g, x + 3, y, -0.15)
        self.mx(g, t, 0, lv)
        if 1.0 < k < 3.8:
            g.mx[0:5, 3] = [((y + int(t * 10)) % 3 == 0) for y in range(5)]

    def interrupt(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        lv = self.level(k)
        self.mantra(g, k)
        bowl(g, lv, t)
        hx, hy, ang = REST
        p = ease_in_out(span(t, 0, 0.9))
        lay = (BCX + 18, RIM - 2, math.pi + 0.08)  # 横放在盂沿上
        x, y, a = lerp(hx, lay[0], p), lerp(hy, lay[1], p), lerp(ang, lay[2], p)
        willow(g, x, y, a, self.leaves(k), t * (1 - p), self.seed)
        if t < 0.9:
            sleeve(g, x + 3, y, -0.15)
        else:
            q = ease_in(span(t, 0.9, 1.5))
            sleeve(g, lerp(x + 3, 170, q), lerp(y, -10, q), -0.15, fist=False)
        self.mx(g, 0, 0, lv)

    def resume(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        lv = self.level(k)
        self.mantra(g, k)
        bowl(g, lv, t)
        hx, hy, ang = REST
        lay = (BCX + 18, RIM - 2, math.pi + 0.08)
        if t < 0.6:
            q = ease_out(span(t, 0, 0.6))
            willow(g, *lay, self.leaves(k), 0, self.seed)
            sleeve(g, lerp(170, lay[0] + 3, q), lerp(-10, lay[1], q), -0.15, fist=False)
        else:
            p = ease_in_out(span(t, 0.6, 1.6))
            x, y, a = lerp(lay[0], hx, p), lerp(lay[1], hy, p), lerp(lay[2], ang, p)
            willow(g, x, y, a, self.leaves(k), t, self.seed)
            sleeve(g, x + 3, y, -0.15)
        self.mx(g, t, 0, lv)

    def complete(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        lv = self.level(k)
        hx, hy, ang = REST
        bowl(g, lv, t, ripple=1 - span(t, 0.6, 1.2) if t > 0.6 else 0)
        if t < 1.0:  # 蘸水
            u = 0.4 + t * 1.3
        else:
            u = None
        if u is not None:
            x, y, a = pose(min(u, 1.6))
        else:  # 绕手一转
            q = ease_in_out(span(t, 1.0, 2.4))
            x, y = lerp(104, 100, q), lerp(30, 24, q)
            a = 2.42 + q * 2 * math.pi
        tip = willow(g, x, y, a, self.leaves(k), t, self.seed)
        sleeve(g, x + 3, y, -0.15)
        if t > 1.0:
            for j in range(6):  # 绕的一圈里分六次洒出
                t0 = 1.2 + j * 0.2
                if t > t0:
                    qq = ease_in_out(span(t0, 1.0, 2.4))
                    aa = 2.42 + qq * 2 * math.pi
                    tp = twig_pts(lerp(104, 100, qq), lerp(30, 24, qq), aa)[-1]
                    self.drops(g, t, tp[0], tp[1], 100 + j, t - t0, n=6, spread=1.2, base=aa - 0.3, speed=55)
        if t > 2.6:
            sparkles(g, 64, 30, 64, 32, t, n=14, seed=self.seed)
            g.d.rectangle((0, 0, 30, 63), fill=0)
            vt = "急急如律令"
            n = int(clamp((t - 2.6) * 4 / len(vt)) * len(vt))
            g.vtext(4, 2, vt[:n])
        else:
            self.mantra(g, k)
        self.mx(g, t, 0, lv)
        if t > 1.2:
            g.mx[0:5, :] = False
            for j in range(8):
                a = j / 8 * 2 * math.pi + t
                r = (t - 1.2) * 3 % 4
                g.mx_set(round(3.5 + math.cos(a) * r), round(3 + math.sin(a) * r))
