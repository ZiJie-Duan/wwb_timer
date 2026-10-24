"""龟息：岸边打坐的人与池中石上的老龟同息。鼻前一根鸿毛，人引气、闭气默数、再微微吐出，
鸿毛几乎不动；老龟伸颈吞气、缩颈闭息。

依据：《抱朴子·释滞》“初学行炁，鼻中引炁而闭之，阴以心数至一百二十，乃以口微吐之……
以鸿毛著鼻口之上，吐炁而鸿毛不动为候也”；“得胎息者，能不以鼻口嘘吸，如在胞胎之中”。
《抱朴子·对俗》“知龟鹤之遐寿，故效其道引以增年”，又见老龟“伸颈吞气”。

入场：池水泛起涟漪，老龟从水里爬上石头；鸿毛从上方飘落到人的鼻前。
持续：一息约 40 秒：引气（龟伸颈）→ 闭气，头边默数 1…120（龟缩颈）→ 微吐（鸿毛轻颤）。
      一轮 10 分钟里吐气越来越细，鸿毛越来越静。一轮满：池里开出一朵莲（最多四朵），
      龟浮于莲叶之上（《抱朴子》千岁之龟“浮于莲叶之上”）。
中断：人睁眼长出一口气，鸿毛被吹飞，龟缩进壳里，“出息”。
恢复：鸿毛飘回鼻前，龟探出头来。
圆满：人腹中一团光蜷成胎形，龟壳放光，“如在胞胎”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register

INHALE, HOLD, EXHALE = 4.0, 30.0, 6.0
BREATH = INHALE + HOLD + EXHALE
WATER = 55
# 侧身打坐的人（面朝右）：坐标在 (0,0) 为坐垫底中心的局部系里
PX, PY = 30, 54
HEAD = (3, -36)
BODY = [(-4, -28), (2, -29), (5, -25), (6, -18), (8, -12), (10, -7), (4, -5), (-9, -5), (-10, -10), (-9, -18),
        (-7, -25)]
LEGS = [(-11, -5), (-6, -9), (8, -10), (17, -8), (20, -4), (17, -1), (-11, -1)]
ARM = [(-3, -26), (1, -26), (3, -17), (15, -10), (14, -7), (2, -12), (-4, -19)]
NOSE = (PX + 12, PY - 33)
TURTLE = (100, 46)   # 龟壳中心底


def breath(e: float) -> tuple[str, float]:
    """→ (阶段 in/hold/out, 阶段内进度 0..1)"""
    k = e % BREATH
    if k < INHALE:
        return "in", k / INHALE
    if k < INHALE + HOLD:
        return "hold", (k - INHALE) / HOLD
    return "out", (k - INHALE - HOLD) / EXHALE


def _tp(pts, dx=0.0, dy=0.0):
    return [(PX + x + dx, PY + y + dy) for x, y in pts]


@register
class TurtleBreath(Ritual):
    id = "r4.turtle"
    name = "龟息"
    desc = "岸边打坐的人鼻前放一根鸿毛，引气闭气默数一百二十再微吐，池中老龟伸颈吞气、缩颈闭息"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 2.0, "complete": 5.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 零件

    def pond(self, g: Gfx, t: float, e: float, lotus: int = 0, bloom: float = 1.0):
        d = g.d
        d.line((0, WATER, 22, WATER), fill=1)   # 岸
        d.line((0, WATER - 1, 52, WATER - 1), fill=1)
        for i in range(5):  # 水纹
            y = WATER + 2 + i * 2
            x0 = (i * 23 + t * (3 + i)) % 140 - 20
            d.line((x0, y, x0 + 8 + i * 2, y), fill=1)
        # 石头
        rock = [(76, 52), (86, 47), (116, 47), (124, 53), (126, 60), (72, 60)]
        d.polygon(rock, fill=0)
        g.shade_poly(rock, 0.2)
        # 芦苇
        for i, x in enumerate((122, 126)):
            sw = math.sin(t * 0.8 + i) * 1.5
            d.line((x, 60, x + sw, 30 + i * 5), fill=1)
            d.ellipse((x + sw - 1, 30 + i * 5, x + sw + 1, 35 + i * 5), fill=1)
        # 莲（一轮一朵）
        for j in range(min(lotus, 4)):
            x = 52 + j * 9
            k = bloom if j == lotus - 1 else 1.0
            self.lotus(g, x, WATER + 3 + (j % 2) * 2, k)

    def lotus(self, g: Gfx, x: float, y: float, k: float):
        d = g.d
        d.ellipse((x - 5, y, x + 5, y + 2), fill=0, outline=1)  # 荷叶
        if k <= 0:
            return
        h = 5 * ease_out(k)
        open_ = ease_out_back(span(k, 0.4, 1.0))
        d.polygon([(x - 1, y), (x, y - h), (x + 1, y)], fill=1)
        for sd in (-1, 1):
            d.polygon([(x, y), (x + sd * (1 + 3 * open_), y - h * 0.8), (x + sd * (1 + 1 * open_), y)], fill=1)

    def person(self, g: Gfx, eyes_open: bool = False, glow: float = 0.0):
        d = g.d
        d.ellipse((PX - 15, PY - 3, PX + 22, PY + 2), fill=0, outline=1)  # 蒲团
        d.polygon(_tp(LEGS), fill=0)
        g.shade_poly(_tp(LEGS), 0.3)
        d.line((PX - 2, PY - 4, PX + 13, PY - 6), fill=1)
        d.polygon(_tp(BODY), fill=0)
        g.shade_poly(_tp(BODY), 0.3)
        d.line((PX + 0, PY - 28, PX + 4, PY - 20), fill=1)                # 交领
        d.polygon(_tp(ARM), fill=0, outline=1)
        d.line((PX + 2, PY - 16, PX + 12, PY - 9), fill=1)                # 袖褶
        hx, hy = PX + HEAD[0], PY + HEAD[1]
        d.rectangle((hx - 3, hy + 3, hx + 1, hy + 8), fill=0, outline=1)       # 颈
        d.ellipse((hx - 6, hy - 6, hx + 5, hy + 5), fill=1)                    # 头发
        d.ellipse((hx - 1, hy - 3, hx + 6, hy + 6), fill=0)                    # 脸
        d.arc((hx - 1, hy - 3, hx + 6, hy + 6), 250, 110, fill=1)
        d.polygon([(hx + 5, hy - 1), (hx + 8, hy + 2), (hx + 5, hy + 2)], fill=0, outline=1)  # 鼻
        d.ellipse((hx - 6, hy - 10, hx - 1, hy - 5), fill=1)                   # 发髻
        d.line((hx - 8, hy - 8, hx + 1, hy - 8), fill=1)
        if eyes_open:
            d.rectangle((hx + 2, hy, hx + 3, hy), fill=1)
        else:
            d.line((hx + 1, hy, hx + 3, hy + 1), fill=1)
        d.line((hx + 3, hy + 4, hx + 4, hy + 4), fill=1)                       # 嘴
        if glow > 0:  # 腹中胎形：一团蜷着的光
            cx, cy = PX + 1, PY - 13
            r = 2 + 3 * glow
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0, outline=1)
            d.ellipse((cx - r * 0.5, cy - r * 0.6, cx + r * 0.3, cy), fill=1)
            d.arc((cx - r * 0.7, cy - r * 0.3, cx + r * 0.7, cy + r * 0.7), 300, 160, fill=1)

    def feather(self, g: Gfx, x: float, y: float, tilt: float):
        """鸿毛：一根弯弯的细羽，羽轴 + 两侧蓬松的羽丝（根部贴在鼻下）"""
        a0 = math.radians(4 + tilt)
        L = 9
        prev = (x, y)
        for k in range(1, L + 1):
            a = a0 - k * 0.04
            px, py = x + math.cos(a) * k, y + math.sin(a) * k
            g.d.line((prev, (px, py)), fill=1)
            prev = (px, py)
            if k >= 3:
                w = 2.0 * math.sin((k - 2) / (L - 1) * math.pi) + 0.5
                nx, ny = -math.sin(a), math.cos(a)
                g.d.line((px, py, px - nx * w + math.cos(a) * 1.5, py - ny * w + math.sin(a) * 1.5), fill=1)
                if k % 2:
                    g.d.line((px, py, px + nx * w + math.cos(a) * 1.5, py + ny * w + math.sin(a) * 1.5), fill=1)

    def turtle(self, g: Gfx, neck: float, t: float, glow: float = 0.0, dx: float = 0.0, dy: float = 0.0):
        """老龟（面朝左）：壳、颈（neck 0 缩 .. 1 伸）、四足、尾"""
        d = g.d
        bx, by = TURTLE[0] + dx, TURTLE[1] + dy
        # 足
        for fx in (bx - 10, bx + 9):
            d.rectangle((fx - 2, by - 1, fx + 2, by + 2), fill=1)
        d.line((bx + 15, by - 2, bx + 18, by), fill=1)  # 尾
        # 颈与头
        L = 2 + 10 * neck
        nx, ny = bx - 14 - L, by - 4 - neck * 3
        d.line((bx - 13, by - 3, nx + 2, ny + 1), fill=1, width=3)
        d.ellipse((nx - 3, ny - 2, nx + 3, ny + 3), fill=1)
        d.point((nx - 1, ny), fill=0)
        # 壳：半椭圆，龟甲纹
        shell = (bx - 15, by - 14, bx + 15, by + 4)
        d.chord(shell, 180, 360, fill=0, outline=1)
        d.line((bx - 15, by - 5, bx + 15, by - 5), fill=1)
        d.line((bx - 16, by - 4, bx + 16, by - 4), fill=1)
        for i, (cx, cy) in enumerate(((bx - 7, by - 10), (bx + 1, by - 11), (bx + 9, by - 9), (bx - 2, by - 7),
                                       (bx + 6, by - 7))):
            hexa = [(cx - 3, cy), (cx - 1.5, cy - 2), (cx + 1.5, cy - 2), (cx + 3, cy), (cx + 1.5, cy + 2),
                    (cx - 1.5, cy + 2)]
            d.polygon(hexa, outline=1, fill=1 if glow > 0 and blink(t + i * 0.2, 0.6, 0.5) else 0)
        if glow > 0:
            for j in range(10):
                a = math.pi + j / 9 * math.pi
                r0, r1 = 18, 18 + 6 * glow * (0.6 + 0.4 * math.sin(t * 6 + j))
                d.line((bx + math.cos(a) * r0, by - 5 + math.sin(a) * r0 * 0.7, bx + math.cos(a) * r1,
                        by - 5 + math.sin(a) * r1 * 0.7), fill=1)

    def neck_at(self, e: float) -> float:
        ph, k = breath(e)
        if ph == "in":
            return ease_out(k)
        if ph == "hold":
            return 1 - ease_in_out(span(k, 0, 0.12))
        return 0.15 * math.sin(k * math.pi)

    def tilt_at(self, e: float, t: float) -> float:
        """鸿毛的颤动：吐气时略动，一轮里越来越静"""
        ph, k = breath(e)
        p = (e % self.CYCLE) / self.CYCLE
        if ph == "out":
            amp = lerp(10, 1.5, p)
            return math.sin(k * math.pi) * amp * (0.6 + 0.4 * math.sin(t * 13))
        if ph == "in":
            return -math.sin(k * math.pi) * lerp(4, 1, p)
        return 0.0

    def count(self, g: Gfx, e: float):
        ph, k = breath(e)
        if ph != "hold":
            return
        n = min(120, 1 + int(k * 120))
        g.text(PX - 14, PY - 50, str(n), size=8)

    def texts(self, g: Gfx, e: float, left: str | None = None, a: float = 1.0):
        ph, k = breath(e)
        l = left if left is not None else {"in": "引气", "hold": "闭气", "out": "微吐"}[ph]
        g.vtext(2, 2, l[:int(round(len(l) * a))])
        n = int(e // BREATH) + 1
        r = f"第{cn_num(n)}息"
        g.text(126, 1, r[:int(round(len(r) * a))], align="right")

    def mx(self, g: Gfx, neck: float, t: float):
        """点阵：龟的俯视图，头随呼吸伸缩"""
        art = ["........", "........", "..####..", ".######.", "########", ".######.", "..####..", ".#....#."]
        for y, row in enumerate(art):
            for x, ch in enumerate(row):
                g.mx[y, x] = ch == "#"
        g.mx[3, 2] = g.mx[3, 5] = g.mx[5, 2] = g.mx[5, 5] = False   # 甲纹
        g.mx[1, 3] = g.mx[1, 4] = neck > 0.3
        g.mx[0, 3] = g.mx[0, 4] = neck > 0.7

    # ------------------------------------------------------------ 阶段

    def lotus_n(self, e: float) -> int:
        return int(e // self.CYCLE)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        n = self.lotus_n(e)
        bloom = span(k, 0.5, 3.5) if (e >= self.CYCLE and k < 4.0) else 1.0
        self.pond(g, t, e, lotus=n, bloom=bloom)
        neck = self.neck_at(e)
        self.turtle(g, neck, t)
        self.person(g)
        self.feather(g, *NOSE, self.tilt_at(e, t))
        self.count(g, e)
        if e >= self.CYCLE and k < 4.0 and bloom < 1:  # 开莲的闪光
            x = 52 + (min(n, 4) - 1) * 9
            for j in range(6):
                if blink(t + j * 0.13, 0.4, 0.5):
                    a = j / 6 * 2 * math.pi
                    g.px(x + math.cos(a) * 7, WATER + math.sin(a) * 4)
        self.texts(g, e)
        self.mx(g, neck, t)

    def enter(self, g: Gfx, t: float):
        self.pond(g, t, 0)
        rip = span(t, 0, 1.5)
        if rip < 1:
            ring(g, 100, WATER + 3, 3 + rip * 20, 2)
        # 龟从水里爬上石头
        k = ease_out(span(t, 0.6, 2.4))
        self.turtle(g, 0.6 * k, t, dx=lerp(-28, 0, k), dy=lerp(16, 0, k))
        g.d.rectangle((70, WATER + 6, 128, 63), fill=0) if k < 0.5 else None
        self.person(g)
        # 鸿毛从上方飘落
        f = ease_out(span(t, 1.8, 4.3))
        fx = NOSE[0] + math.sin(t * 3) * 6 * (1 - f)
        fy = lerp(-10, NOSE[1], f)
        self.feather(g, fx, fy, math.sin(t * 4) * 25 * (1 - f))
        self.texts(g, 0, a=span(t, 3.4, 4.5))
        self.mx(g, 0.6 * k, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        self.pond(g, t, e, lotus=self.lotus_n(e))
        neck = lerp(self.neck_at(e), -0.2, ease_in(span(t, 0, 0.6)))
        self.turtle(g, max(0.0, neck), t)
        self.person(g, eyes_open=t > 0.3)
        # 一口长气把鸿毛吹飞
        k = ease_in(span(t, 0.3, 1.5))
        fx, fy = NOSE[0] + k * 70, NOSE[1] - math.sin(k * math.pi) * 12 + k * 6
        if k < 1:
            self.feather(g, fx, fy, k * 300)
        if 0.3 < t < 1.0:
            for j in range(3):
                y = NOSE[1] + 2 + j * 2
                x0 = NOSE[0] + 2 + span(t, 0.3, 1.0) * 16
                g.d.line((x0, y, x0 + 6, y), fill=1)
        self.texts(g, e, left="出息")
        self.mx(g, 0.0, t)

    def resume(self, g: Gfx, t: float, e: float):
        self.pond(g, t, e, lotus=self.lotus_n(e))
        k = ease_out(span(t, 0.8, 2.0))
        self.turtle(g, lerp(0.0, self.neck_at(e), k), t)
        self.person(g, eyes_open=t < 0.5)
        f = ease_out(span(t, 0, 1.6))
        fx = NOSE[0] + math.sin(t * 3) * 6 * (1 - f)
        fy = lerp(-10, NOSE[1], f)
        self.feather(g, fx, fy, lerp(math.sin(t * 4) * 25, self.tilt_at(e, t), f))
        if t > 1.6:
            self.count(g, e)
        self.texts(g, e, left="出息" if t < 0.6 else None)
        self.mx(g, lerp(0.0, self.neck_at(e), k), t)

    def complete(self, g: Gfx, t: float, e: float):
        self.pond(g, t, e, lotus=max(1, self.lotus_n(e)))
        gl = ease_out(span(t, 1.0, 2.5))
        self.turtle(g, lerp(self.neck_at(e), 1.0, span(t, 0, 0.8)), t, glow=gl)
        self.person(g, glow=ease_out(span(t, 0.5, 2.0)))
        self.feather(g, *NOSE, 0)
        if t > 1.5:
            ring(g, PX + 1, PY - 13, 8 + 3 * math.sin(t * 3), 2, t)
        if t < 1.0:
            self.texts(g, e, a=1 - span(t, 0, 1.0))
        if t > 2.5:
            typewriter(g, 70, 2, "如在胞胎", t - 2.5, cps=5, align="center")
        self.mx(g, 1.0, t)
        if t > 1.0:
            for y in range(1, 7):
                for x in range(1, 7):
                    if g.mx[y, x] is False or not g.mx[y, x]:
                        g.mx[y, x] = blink(t + (x + y) * 0.07, 0.5, 0.5) and (x + y) % 2 == 0
            g.mx_level = 3 if 1.0 < t < 1.6 else 1
