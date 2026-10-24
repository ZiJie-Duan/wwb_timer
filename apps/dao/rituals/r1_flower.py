"""散花：一只花篮，宽袖手一朵一朵拈起花抛向空中，花在半空盛开，唱一句“散一朵，是水仙”，
随后花瓣离枝、飘飘落下，在地上越积越厚。

依据：全真道度亡科仪中的“散花”，以百花的荣枯比拟人生盛衰、劝化亡灵（香港道教音乐资料）；
《散花偈》每段以“散一朵”起句：散一朵是水仙、状元红、金海棠、风入松、是绣球、是垂杨、是雪梨、是金钱、
是芙蓉、菊花新、是紫荆（青松观陈耀庭注本，见 edwardw.bearblog.dev《Gatha of Scattering the Flowers》）。

入场：花篮落到地上，篮里冒出十一朵花，左侧“散一朵”。
持续：一轮 660 秒十一段，每 60 秒一段：手从右上伸进花篮拈起一朵，抛起，花在右上半空盛开（每段花形不同），
      右侧竖写本段花名；十秒后花瓣一片片离开、打着旋儿飘落，落地铺成花毯。花篮里的花随 e 变少，地上的花瓣变多。
      一轮结束：一阵风把满地花瓣卷起吹走，花篮里重新冒满花，再从“是水仙”散起。
中断：半空的花合拢成苞落回篮里，飘着的花瓣一齐落地，右侧“暂歇”。
恢复：一阵小风把几片花瓣从地上卷起又落下，接着散花。
圆满：篮里剩下的花一齐飞出，满屏花雨，“散花”大字。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, \
    rand, span
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import sleeve, sparkles, vreveal

VERSES = ["是水仙", "状元红", "金海棠", "风入松", "是绣球", "是垂杨", "是雪梨", "是金钱", "是芙蓉", "菊花新", "是紫荆"]
KINDS = ["narcissus", "peony", "begonia", "pine", "hydrangea", "willow", "pear", "coin", "hibiscus", "chrysanth",
         "bauhinia"]
N = len(VERSES)
STEP = 60.0
FIRST = 6.0
RENEW = 4.8
BLOOM = (82, 26)           # 花在半空开放的位置
BR = 18                    # 盛开半径
GROUND = 61
BX, RIM = 40, 45           # 花篮中心、篮口
PETALS = 10                # 每朵落下几片
FALL0 = 10.0               # 抛起后第几秒开始落瓣
# 篮口露出的花头
HEADS = [(28, 42), (36, 40), (44, 41), (52, 42), (32, 37), (40, 36), (48, 37), (25, 38), (55, 38), (36, 33), (44, 33)]


def petal_at(g: Gfx, x: float, y: float, ph: float):
    """一片花瓣（随相位翻转）"""
    if int(ph * 4) % 2:
        g.d.line((x, y, x + 2, y), fill=1)
        g.d.line((x + 1, y - 1, x + 2, y - 1), fill=1)
    else:
        g.d.line((x, y, x + 1, y + 1), fill=1)
        g.d.line((x + 1, y, x + 2, y + 1), fill=1)


def bloom(g: Gfx, cx: float, cy: float, r: float, kind: str, rot: float = 0.0):
    """一朵盛开的花，r 为半径（花苞阶段 r 小）"""
    d = g.d
    if r < 4:  # 花苞
        d.ellipse((cx - 2, cy - 3, cx + 2, cy + 2), fill=1)
        d.line((cx, cy + 2, cx, cy + 6), fill=1)
        return

    def ray(a, r0, r1):
        return (cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * r1, cy + math.sin(a) * r1)

    def round_petals(n, rr, pr, a0=0.0):
        for i in range(n):
            a = rot + a0 + i / n * 2 * math.pi
            px, py = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=0, outline=1)

    def pointed(n, r0, r1, w, a0=0.0, fill=0):
        for i in range(n):
            a = rot + a0 + i / n * 2 * math.pi
            ca, sa = math.cos(a), math.sin(a)
            pts = [(cx + ca * r0 - sa * w, cy + sa * r0 + ca * w), (cx + ca * r1, cy + sa * r1),
                   (cx + ca * r0 + sa * w, cy + sa * r0 - ca * w), (cx + ca * r0 * 0.5, cy + sa * r0 * 0.5)]
            d.polygon(pts, fill=fill, outline=1)

    if kind == "narcissus":      # 水仙：六尖瓣 + 副冠小杯
        pointed(6, r * 0.25, r, r * 0.28)
        d.ellipse((cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3), fill=0, outline=1)
        d.ellipse((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
    elif kind == "peony":        # 状元红：重瓣
        round_petals(8, r * 0.62, r * 0.38)
        round_petals(5, r * 0.32, r * 0.3, 0.3)
        d.ellipse((cx - r * 0.18, cy - r * 0.18, cx + r * 0.18, cy + r * 0.18), fill=1)
    elif kind in ("begonia", "pear"):  # 海棠 / 梨花：五圆瓣，梨花多一圈花蕊
        round_petals(5, r * 0.5, r * 0.45)
        d.ellipse((cx - r * 0.2, cy - r * 0.2, cx + r * 0.2, cy + r * 0.2), fill=0, outline=1)
        if kind == "pear":
            for i in range(8):
                a = rot + i / 8 * 2 * math.pi
                d.line(ray(a, r * 0.2, r * 0.42), fill=1)
                g.px(cx + math.cos(a) * r * 0.46, cy + math.sin(a) * r * 0.46)
        else:
            g.px(cx, cy)
    elif kind == "pine":         # 风入松：三簇松针 + 松果
        for k, (dx, dy) in enumerate(((-0.4, -0.2), (0.35, -0.35), (0.1, 0.35))):
            px, py = cx + dx * r, cy + dy * r
            for i in range(11):
                a = rot * 0.5 + i / 11 * 2 * math.pi + k
                d.line((px, py, px + math.cos(a) * r * 0.5, py + math.sin(a) * r * 0.5), fill=1)
        d.ellipse((cx - 3, cy + r * 0.55, cx + 3, cy + r * 0.55 + 7), fill=0, outline=1)
        d.line((cx - 3, cy + r * 0.55 + 3, cx + 3, cy + r * 0.55 + 3), fill=1)
    elif kind == "hydrangea":    # 绣球：一团小四瓣花
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0, outline=1)
        for i in range(-3, 4):
            for j in range(-3, 4):
                x, y = cx + i * r * 0.27 + (j % 2) * r * 0.13, cy + j * r * 0.27
                if (x - cx) ** 2 + (y - cy) ** 2 < (r * 0.85) ** 2:
                    for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        g.px(x + ddx, y + ddy)
    elif kind == "willow":       # 垂杨：一弯枝，柳丝垂下
        pts = [(cx - r + i * r / 5, cy - r * 0.6 - math.sin(i / 10 * math.pi) * r * 0.4) for i in range(11)]
        d.line(pts, fill=1)
        for i in range(1, 10):
            x, y = pts[i]
            ln = r * (0.6 + 0.6 * rand(i, 3))
            sw = math.sin(rot * 2 + i) * 2
            d.line((x, y, x + sw, y + ln), fill=1)
            g.px(x + sw * 1.2 + 1, y + ln * 0.6)
    elif kind == "coin":         # 金钱花：细瓣一圈，花心是一枚方孔钱
        for i in range(14):
            d.line(ray(rot + i / 14 * 2 * math.pi, r * 0.5, r), fill=1)
        d.ellipse((cx - r * 0.48, cy - r * 0.48, cx + r * 0.48, cy + r * 0.48), fill=1)
        h = r * 0.15
        d.rectangle((cx - h, cy - h, cx + h, cy + h), fill=0)
        d.ellipse((cx - r * 0.36, cy - r * 0.36, cx + r * 0.36, cy + r * 0.36), outline=0)
    elif kind == "hibiscus":     # 芙蓉：五大瓣带脉，长花蕊
        round_petals(5, r * 0.52, r * 0.5)
        for i in range(5):
            a = rot + i / 5 * 2 * math.pi
            d.line(ray(a, r * 0.2, r * 0.85), fill=1)
        d.line((cx, cy, cx + r * 0.4, cy - r * 0.5), fill=1)
        d.ellipse((cx + r * 0.4 - 1, cy - r * 0.5 - 1, cx + r * 0.4 + 1, cy - r * 0.5 + 1), fill=1)
    elif kind == "chrysanth":    # 菊花：两层细长瓣
        for i in range(18):
            d.line(ray(rot + i / 18 * 2 * math.pi, r * 0.3, r), fill=1)
        for i in range(10):
            d.line(ray(rot + (i + 0.5) / 10 * 2 * math.pi, r * 0.15, r * 0.6), fill=1)
        d.ellipse((cx - r * 0.2, cy - r * 0.2, cx + r * 0.2, cy + r * 0.2), fill=1)
    else:                        # 紫荆：五片窄瓣、长雄蕊
        pointed(5, r * 0.2, r, r * 0.22, fill=0)
        for i in range(5):
            a = rot + (i + 0.5) / 5 * 2 * math.pi
            d.line(ray(a, 0, r * 0.55), fill=1)
            g.px(cx + math.cos(a) * r * 0.6, cy + math.sin(a) * r * 0.6)


def basket(g: Gfx, heads: int, t: float, dy: float = 0.0, pop: float = 1.0):
    d = g.d
    y = RIM + dy
    for i in range(heads):  # 篮里的花头
        x, hy = HEADS[i]
        s = pop if pop < 1 else 1
        if s <= 0:
            continue
        hy = hy + dy + (1 - s) * 8
        rr = 2.5
        d.ellipse((x - rr, hy - rr, x + rr, hy + rr), fill=0, outline=1)
        g.px(x, hy)
        d.line((x, hy + rr, x + (1 if i % 2 else -1), hy + rr + 4), fill=1)
    # 提梁
    d.arc((BX - 20, y - 26, BX + 20, y + 10), 180, 360, fill=1)
    d.arc((BX - 18, y - 24, BX + 18, y + 8), 180, 360, fill=1)
    # 篮身：上宽下窄，编织纹
    body = [(BX - 21, y), (BX + 21, y), (BX + 15, y + 15), (BX - 15, y + 15)]
    d.polygon(body, fill=0, outline=1)
    d.line((BX - 22, y, BX + 22, y), fill=1)
    d.line((BX - 22, y + 1, BX + 22, y + 1), fill=1)
    for k in range(-20, 21, 4):
        d.line((BX + k, y + 2, BX + k * 0.72 + 2, y + 14), fill=1)
    for yy in (y + 6, y + 10):
        hw = 21 - (yy - y) * 6 / 15
        d.line((BX - hw + 1, yy, BX + hw - 1, yy), fill=1)


@register
class ScatterFlowers(Ritual):
    id = "r1.flower"
    name = "散花"
    desc = "花篮里拈花抛起，半空盛开，唱“散一朵，是水仙”；花瓣飘落铺满地，一轮后风卷花毯"
    T = {"enter": 3.6, "interrupt": 1.5, "resume": 1.6, "complete": 5.5}
    CYCLE = FIRST + STEP * N   # 666

    # ------------------------------------------------------------ 状态（e 的函数）

    def verse(self, k: float) -> tuple[int, float]:
        """→ (当前第几段（-1 = 还没开始）, 本段已过秒数)"""
        if k < FIRST:
            return -1, k - FIRST
        j = min(N - 1, int((k - FIRST) // STEP))
        return j, k - FIRST - j * STEP

    def heads(self, k: float) -> int:
        """篮里还剩几朵（被拈起那一刻少一朵）"""
        j, u = self.verse(k)
        if j < 0:
            return N
        return N - j - (1 if u >= 0 else 0)

    def petal(self, j: int, i: int):
        """第 j 朵的第 i 片：(起点 x, y, 下落速度, 漂移, 落地所需秒数, 落地 x)"""
        a = i / PETALS * 2 * math.pi + j
        x0 = BLOOM[0] + math.cos(a) * BR * 0.7
        y0 = BLOOM[1] + math.sin(a) * BR * 0.7
        v = 5 + 4 * rand(i, j * 7 + self.seed)
        drift = (rand(i + 9, j * 7 + self.seed) - 0.62) * 14  # 大多往左飘，铺满地面
        T = (GROUND - y0) / v
        return x0, y0, v, drift, T, x0 + drift * T + math.sin(T * 2 + i) * 4

    # ------------------------------------------------------------ 零件

    def carpet(self, g: Gfx, k: float, blow: float = 0.0, t: float = 0.0, hurry: float = 0.0):
        """地上的花瓣：已落地的都画出来；blow > 0 时被风卷走；hurry 让还在飘的提前落地（中断）"""
        j_now, u_now = self.verse(k)
        for j in range(max(j_now + 1, 0)):
            u = k - FIRST - j * STEP - FALL0
            for i in range(PETALS):
                x0, y0, v, drift, T, xl = self.petal(j, i)
                age = u - i * 0.45
                if age < 0 or age + hurry * T < T:
                    continue
                x = (xl % 120) + 4
                y = GROUND + 1 - (i + j) % 3 * 0.7
                if blow > 0:
                    x += ease_in(blow) * (90 + rand(i, j) * 80)
                    y -= math.sin(blow * math.pi) * (10 + rand(i + 3, j) * 25)
                petal_at(g, x, y, (j + i) * 0.13 + (t * 3 if blow > 0 else 0))
        g.d.line((0, 63, 127, 63), fill=1)

    def falling(self, g: Gfx, k: float, t: float, hurry: float = 0.0):
        j, u = self.verse(k)
        for jj in (j - 1, j):
            if jj < 0:
                continue
            uu = k - FIRST - jj * STEP - FALL0
            for i in range(PETALS):
                x0, y0, v, drift, T, xl = self.petal(jj, i)
                age = uu - i * 0.45
                if hurry > 0:
                    age += hurry * T
                if 0 <= age < T:
                    x = x0 + drift * age + math.sin(age * 2 + i) * 4
                    petal_at(g, x, y0 + v * age, age)

    def flower_now(self, g: Gfx, k: float, t: float, close: float = 0.0):
        """半空的花：抛起 → 开 → 开着轻转 → 落瓣时渐小"""
        j, u = self.verse(k)
        if j < 0 or u < 0.6 or u >= FALL0 + PETALS * 0.45:
            return
        kind = KINDS[j]
        bx, by = BLOOM
        if u < 1.4:  # 飞上去（花苞）
            q = ease_out(span(u, 0.6, 1.4))
            x0, y0 = self.pluck_xy(j)
            bloom(g, lerp(x0, bx, q), lerp(y0 - 6, by, q) - math.sin(q * math.pi) * 6, 2, kind)
            return
        r = BR * ease_out_back(span(u, 1.4, 2.4))
        if u > FALL0:  # 花瓣一片片走了，花渐小
            r *= 1 - 0.75 * span(u, FALL0, FALL0 + PETALS * 0.45)
        r *= 1 - close
        rot = t * 0.15 + math.sin(t * 0.7) * 0.1
        bloom(g, bx, by + math.sin(t * 1.1) * 1.2, max(r, 2.5), kind, rot)

    def pluck_xy(self, j: int):
        idx = N - 1 - j
        return HEADS[idx]

    def hand(self, g: Gfx, k: float):
        j, u = self.verse(k)
        nj = j + 1 if j >= 0 else 0
        un = k - FIRST - nj * STEP
        if nj < N and -1.5 <= un < 0:  # 伸向花篮
            x, y = self.pluck_xy(nj)
            p = ease_out(span(un, -1.5, -0.1))
            sleeve(g, lerp(150, x + 2, p), lerp(-30, y - 5, p), -0.7)
            return
        if j >= 0 and 0 <= u < 1.4:  # 拈起、一抛、收回
            x, y = self.pluck_xy(j)
            if u < 0.6:
                hy = y - 5 - ease_in_out(u / 0.6) * 10
                bloom(g, x - 1, hy + 6, 2, KINDS[j])
                sleeve(g, x + 2, hy, -0.7)
            else:
                p = ease_in(span(u, 0.6, 1.4))
                sleeve(g, lerp(x + 2, 150, p), lerp(y - 15, -30, p), -0.7, fist=False)

    def texts(self, g: Gfx, k: float, a: float = 1.0, right: str | None = None):
        vreveal(g, 2, 2, "散一朵", a)
        j, u = self.verse(k)
        if right is not None:
            vreveal(g, 114, 2, right, a)
        elif j >= 0 and u >= 1.4:
            vreveal(g, 114, 2, VERSES[j], min(a, span(u, 1.4, 2.6)))

    def mx(self, g: Gfx, k: float, t: float):
        j, u = self.verse(k)
        g.mx[7, :] = False
        landed = min(8, max(0, j) + (1 if j >= 0 and u > FALL0 + 4 else 0))
        g.mx[7, :landed] = True  # 地上的花瓣
        if j >= 0 and 1.4 <= u < FALL0:  # 盛开的花
            o = span(u, 1.4, 2.4)
            if o < 0.5:  # 花苞
                g.mx_rows([0, 0, 0b00011000, 0b00111100, 0b00111100, 0b00011000, 0b00011000, 0])
            else:        # 盛开：四面花瓣
                g.mx_rows([0, 0b00100100, 0b01011010, 0b00100100, 0b01011010, 0b00100100, 0b00011000, 0])
            g.mx[7, :landed] = True
            if o >= 0.5 and blink(t, 1.6, 0.5):  # 花心一闪
                g.mx_set(3, 3)
                g.mx_set(4, 3)
        elif j >= 0 and FALL0 <= u < FALL0 + 8:  # 落瓣
            for i in range(3):
                y = int((u - FALL0) * 1.5 + i * 2.3) % 7
                g.mx_set((i * 3 + 1 + int(u + i) % 2) % 8, y)
        else:  # 花篮
            g.mx_rows([0, 0, 0b00111100, 0b01000010, 0b11111111, 0b01111110, 0b00111100, 0])
            g.mx[7, :landed] = True
            if blink(t, 1.2, 0.5):
                g.mx_set(3, 3)
                g.mx_set(5, 3)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        drop = ease_out_bounce(span(t, 0, 1.0))
        g.d.line((0, 63, 127, 63), fill=1)
        pop = ease_out_back(span(t, 1.1, 2.3))
        basket(g, N if t > 1.1 else 0, t, dy=lerp(-64, 0, drop), pop=pop)
        if t > 1.1:
            sparkles(g, BX, 34, 24, 8, t, n=5, seed=self.seed)
        self.texts(g, 0, a=span(t, 2.3, 3.4))
        self.mx(g, 0, t)
        if t < 1.0:
            g.mx[:max(0, 8 - int(drop * 8)), :] = False

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        self.carpet(g, k)
        basket(g, self.heads(k), t)
        self.flower_now(g, k, t)
        self.falling(g, k, t)
        self.hand(g, k)
        self.texts(g, k)
        self.mx(g, k, t)
        j, u = self.verse(k)
        if j >= 0 and 1.4 <= u < 1.6:
            g.mx_level = 4

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """一阵风卷走满地花瓣，篮里重新冒满花"""
        blow = span(k, 0.2, 2.4)
        self.carpet(g, self.CYCLE - 0.01, blow=blow, t=t)
        if k < 2.6:  # 风
            for j in range(5):
                y = 18 + j * 9
                x0 = -40 + span(k, 0, 2.4) * 200 - j * 14
                g.d.line((x0, y, x0 + 20, y), fill=1)
                g.d.arc((x0 + 18, y - 6, x0 + 26, y), 270, 90, fill=1)
        pop = ease_out_back(span(k, 2.6, 3.8))
        basket(g, N if k > 2.6 else 0, t, pop=pop)
        vreveal(g, 2, 2, "散一朵")
        self.mx(g, 0, t)
        if k < 2.6:
            g.mx[7, :] = False
            g.mx_set(int(span(k, 0.2, 2.4) * 9), 6)

    def interrupt(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        p = ease_in(span(t, 0, 1.0))
        j, u = self.verse(k)
        self.carpet(g, k, hurry=p)
        heads = self.heads(k)
        # 半空的花合拢成苞落回篮里
        if j >= 0 and 1.4 <= u < FALL0:
            bx, by = BLOOM
            x1, y1 = self.pluck_xy(j)
            if t < 0.5:
                bloom(g, bx, by, max(2.5, BR * (1 - t / 0.5)), KINDS[j], t * 2)
            elif t < 1.1:
                q = ease_in(span(t, 0.5, 1.1))
                bloom(g, lerp(bx, x1, q), lerp(by, y1, q) - math.sin(q * math.pi) * 8, 2, KINDS[j])
            else:
                heads += 1
        basket(g, heads, t)
        self.falling(g, k, t, hurry=p)
        self.texts(g, k, right="暂歇" if t > 0.7 else None)
        self.mx(g, k, 0)

    def resume(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        self.carpet(g, k)
        basket(g, self.heads(k), t)
        # 一阵小风卷起几片花瓣
        for i in range(6):
            q = span(t, 0.1 + i * 0.08, 1.3 + i * 0.08)
            if 0 < q < 1:
                x = 20 + i * 16 + q * 20
                y = GROUND - math.sin(q * math.pi) * (14 + i * 3)
                petal_at(g, x, y, t * 3 + i)
        self.flower_now(g, k, t)
        self.falling(g, k, t)
        self.texts(g, k, right="暂歇" if t < 0.5 else None)
        self.mx(g, k, t)

    def complete(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        heads = self.heads(k)
        self.carpet(g, k)
        out = int(span(t, 0.2, 1.4) * heads + 0.999) if heads else 0
        basket(g, heads - out, t)
        # 剩下的花飞出、在空中开成一片
        for m in range(heads):
            st = 0.2 + m * 1.2 / max(heads, 1)
            q = span(t, st, st + 0.8)
            if q <= 0:
                continue
            x0, y0 = HEADS[heads - 1 - m]
            tx = 52 + rand(m, 5) * 66
            ty = 8 + rand(m, 6) * 24
            x = lerp(x0, tx, ease_out(q))
            y = lerp(y0, ty, ease_out(q)) - math.sin(q * math.pi) * 8
            r = 2 + 5 * ease_out_back(span(t, st + 0.6, st + 1.2))
            bloom(g, x, y + math.sin(t + m) * 1.5, r if r > 4 else 2, KINDS[(m * 3) % N], t * 0.3 + m)
        # 满屏花雨
        rain = span(t, 1.4, 2.0)
        for i in range(int(36 * rain)):
            sp = 8 + rand(i, 7) * 10
            y = (rand(i, 8) * 70 + (t - 1.4) * sp) % 70 - 4
            x = rand(i, 9) * 128 + math.sin(t * 2 + i) * 4
            petal_at(g, x, y, t * 2 + i)
        if t > 2.2:
            p = ease_out_back(span(t, 2.2, 2.8))
            g.d.rectangle((68, 39, 118, 62), fill=0)
            g.text(93, 40 + (1 - p) * 10, "散花", scale=2, align="center")
        else:
            self.texts(g, k, a=1 - span(t, 0.5, 1.5))
        self.mx(g, k, t)
        if t > 1.4:
            g.mx[:, :] = False
            for i in range(10):
                y = int((t * 6 + i * 2.7) % 8)
                g.mx_set(int(rand(i, 3) * 8), y)
            g.mx_level = 2 if t < 3 else 1
