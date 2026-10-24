"""葫芦收妖：拔开葫芦塞，一团妖气（瞪着眼的黑雾）被一缕缕吸进葫芦，时而整只小鬼被扯进去；
妖气随计时越缩越小，收尽则塞口，再来一团。

葫芦是道家常见法器与“壶天”意象（《后汉书·方术传》壶公悬壶，入壶中别有天地），民间道法与小说中多以葫芦收妖、贮丹。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r3_kit import nth, rot, round_of, side_text, sparkle

GX, GY = 96, 45          # 葫芦大肚中心
GA = -0.8                # 葫芦倾角（口朝左上）
CLOUD = (34, 25)         # 妖气中心
R0, R1 = 21, 3           # 妖气起止半径
CHUNK = 15.0             # 每隔多少秒扯进一只小鬼
RENEW = 4.0

IMP = Sprite("""
 .###.
.#####.
##.#.##
#######
#.#.#.#
.#.#.#.
""")
MX_GOURD = ["...##...", "..#..#..", "...##...", "..####..", ".#....#.", ".#....#.", ".#....#.", "..####.."]


def gourd(g: Gfx, x: float = GX, y: float = GY, a: float = GA, cork: float = 1.0, glow: float = 0.0, t: float = 0.0,
          shake: float = 0.0):
    """葫芦：cork 0 = 塞子拔开（在口外），1 = 塞着"""
    x += math.sin(t * 47) * shake
    y += math.cos(t * 53) * shake * 0.6
    (tx, ty), (nx, ny) = rot([(0, -18), (0, -27)], x, y, a)
    g.d.ellipse((x - 14, y - 13, x + 14, y + 13), fill=0, outline=1)       # 大肚
    g.d.polygon(rot([(-3, -24), (3, -24), (3, -29), (-3, -29)], x, y, a), fill=0, outline=1)  # 颈
    g.d.ellipse((tx - 8, ty - 8, tx + 8, ty + 8), fill=0, outline=1)       # 小肚
    g.d.polygon(rot([(-4, -10), (4, -10), (5, -14), (-5, -14)], x, y, a), fill=0)  # 腰：盖掉两圆交线
    g.d.line(rot([(-5, -11), (5, -11)], x, y, a), fill=1, width=2)         # 腰间系绳
    # 高光与暗面
    g.d.arc((x - 10, y - 9, x + 10, y + 9), 190, 250, fill=1)
    g.d.arc((tx - 5, ty - 5, tx + 5, ty + 5), 190, 240, fill=1)
    for i in range(10):
        q = 0.2 + i * 0.12
        g.px(x + math.cos(q) * 11, y + math.sin(q) * 10)
    # 穗子：从腰间垂下，随风摆
    (kx, ky), = rot([(-5, -11)], x, y, a)
    kx -= 2
    sw = math.sin(t * 2.2) * 2
    g.d.line((kx, ky, kx + 1 + sw * 0.5, ky + 7), fill=1)
    g.d.polygon([(kx + sw * 0.5, ky + 7), (kx + 2 + sw * 0.5, ky + 7), (kx + 3 + sw, ky + 14), (kx - 1 + sw, ky + 14)],
                fill=1)
    # 塞子
    if cork >= 1:
        g.d.polygon(rot([(-2, -29), (2, -29), (3, -33), (-3, -33)], x, y, a), fill=1)
    elif cork > 0:  # 正在落下 / 飞出：塞子沿口外的轨迹
        (mx, my), = rot([(0, -33 - (1 - cork) * 18)], x, y, a)
        mx -= (1 - cork) * 10
        g.d.rectangle((mx - 2, my - 2, mx + 2, my + 2), fill=1)
    if glow > 0:
        for i in range(12):
            q = i / 12 * 2 * math.pi + t
            r0, r1 = 17, 17 + 9 * glow
            g.d.line((x + math.cos(q) * r0, y + math.sin(q) * r0, x + math.cos(q) * r1, y + math.sin(q) * r1),
                     fill=1)


def mouth(x: float = GX, y: float = GY, a: float = GA):
    return rot([(0, -31)], x, y, a)[0]


@register
class GourdCapture(Ritual):
    id = "r3.hulu"
    name = "葫芦收妖"
    desc = "拔开葫芦塞，瞪眼的妖气被一缕缕吸进葫芦，时而整只小鬼被扯进去；妖气越缩越小，收尽塞口再来一团"
    T = {"enter": 3.4, "interrupt": 1.3, "resume": 1.5, "complete": 5.5}
    CYCLE = 600.0

    # ------------------------------------------------------------ 零件

    def size(self, e: float) -> float:
        _, _, p = round_of(e, self.CYCLE)
        return lerp(R0, R1, p ** 0.8)

    def cloud(self, g: Gfx, r: float, t: float, pull: float = 1.0, cx: float = CLOUD[0], cy: float = CLOUD[1],
              angry: float = 0.0):
        """妖气：抖动灰度的雾团，朝葫芦口拉长；中间一双眼"""
        if r <= 0.5:
            return
        mx, my = mouth()
        d = math.atan2(my - cy, mx - cx)
        reach = math.hypot(mx - cx, my - cy) / 1.15
        pts = []
        n = 18
        for i in range(n):
            q = i / n * 2 * math.pi
            rr = r * (0.85 + 0.3 * noise(t * 1.5 + i * 0.7, self.seed))
            rr *= 1 + 0.9 * pull * max(0.0, math.cos(q - d)) ** 3
            rr = min(rr, reach)   # 最多拉到葫芦口
            pts.append((cx + math.cos(q) * rr * 1.2, cy + math.sin(q) * rr * 0.9))
        g.d.polygon(pts, fill=0)
        g.shade_poly(pts, 0.4)
        # 眼与嘴
        es = clamp(r / 12)
        if es > 0.2:
            ew, eh = 2 + 2 * es, 1.2 + 1.3 * es
            opened = blink(t + self.seed, 3.7, 0.94)
            look = math.cos(math.atan2(my - cy, mx - cx)) * ew * 0.4   # 眼珠斜瞟葫芦
            for sx in (-1, 1):
                ex, ey = cx + sx * (3 + 4 * es), cy - 2 * es
                g.d.ellipse((ex - ew - 1, ey - eh - 1, ex + ew + 1, ey + eh + 1), fill=0)
                if opened:
                    g.d.ellipse((ex - ew, ey - eh, ex + ew, ey + eh), fill=1)
                    g.d.rectangle((ex + look - 0.5, ey - 0.5, ex + look + 0.5 + (es > 0.6), ey + 0.5 + (es > 0.6)),
                                  fill=0)
                else:
                    g.d.line((ex - ew, ey, ex + ew, ey), fill=1)
                # 横眉（越怒越斜）
                tilt = (1.5 + angry) * es
                g.d.line((ex - ew - 1, ey - eh - 2 - (tilt if sx < 0 else 0), ex + ew + 1,
                          ey - eh - 2 - (tilt if sx > 0 else 0)), fill=0, width=2)
                g.d.line((ex - ew, ey - eh - 2 - (tilt if sx < 0 else 0), ex + ew,
                          ey - eh - 2 - (tilt if sx > 0 else 0)), fill=1)
            if es > 0.5:  # 锯齿嘴
                mw = 5 * es
                zz = [(cx - mw + i * mw / 3, cy + 4 * es + (1.5 if i % 2 else 0)) for i in range(7)]
                g.d.rectangle((cx - mw - 1, cy + 3 * es, cx + mw + 1, cy + 6 * es + 1), fill=0)
                g.d.line(zz, fill=1)

    def stream(self, g: Gfx, r: float, t: float, amp: float = 1.0, k: int = 14):
        """被吸走的妖气：一粒粒螺旋着飞进葫芦口"""
        if amp <= 0 or r <= 0.5:
            return
        mx, my = mouth()
        cx, cy = CLOUD
        d = math.atan2(my - cy, mx - cx)
        sx, sy = cx + math.cos(d) * r * 1.2, cy + math.sin(d) * r * 0.9
        px, py = -math.sin(d), math.cos(d)
        for i in range(int(k * amp)):
            s = (t * 0.9 + i / k) % 1.0
            w = math.sin(s * math.pi * 3 + i * 1.7) * (1 - s) * 5
            x = lerp(sx, mx, ease_in(s)) + px * w
            y = lerp(sy, my, ease_in(s)) + py * w
            g.px(x, y)
            if i % 3 == 0:
                g.px(x + 1, y)

    def imp(self, g: Gfx, f: float, r: float):
        """一只小鬼被扯出来、拉长、缩小、吞进口"""
        if not 0 <= f < 1 or r < 4:
            return
        cx, cy = CLOUD
        mx, my = mouth()
        q = ease_in(f)
        x, y = lerp(cx, mx, q), lerp(cy, my, q)
        if f < 0.75:
            spr = IMP if f < 0.5 else IMP.flip()
            g.blit(spr, x - 3, y - 3)
            for j in range(3):  # 拖出的尾巴
                g.px(x - (mx - cx) * 0.05 * (j + 1), y - (my - cy) * 0.05 * (j + 1))
        else:
            g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)

    def label(self, g: Gfx, e: float, a: float = 1.0, s: str | None = None):
        n = int(e // self.CYCLE) + 1
        side_text(g, 115, 2, s if s is not None else nth(n, "妖"), a)

    def mx(self, g: Gfx, p: float, t: float, cork: bool = False):
        for y, row in enumerate(MX_GOURD):
            for x, ch in enumerate(row):
                if ch == "#":
                    g.mx_set(x, y)
        h = int(round(clamp(p) * 3))
        for r in range(7, 7 - h, -1):
            g.mx[r, 2:6] = True
        if cork:
            g.mx[0, 3:5] = True
        elif blink(t, 0.4):
            g.mx_set(2 + int(t * 5) % 2, 0)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        # 葫芦落下 → 塞子弹开 → 妖气从左下冒起
        drop = ease_out_bounce(span(t, 0, 0.9))
        y = lerp(-30, GY, drop)
        cork = 1 - span(t, 1.1, 1.6)
        grow = ease_out_back(span(t, 1.6, 2.6))
        self.cloud(g, R0 * grow, t, pull=span(t, 2.4, 3.4), cy=lerp(70, CLOUD[1], grow))
        if t > 2.6:
            self.stream(g, R0, t, span(t, 2.6, 3.4))
        gourd(g, GX, y, GA, cork=cork if t < 1.6 else 0, t=t)
        if 1.1 < t < 1.4:
            sparkle(g, *mouth(GX, y), 3)
        self.label(g, 0, span(t, 2.6, 3.3))
        self.mx(g, 0, t, cork=t < 1.2)
        g.mx_level = 4 if 1.1 < t < 1.3 else 1

    def hold(self, g: Gfx, t: float, e: float):
        n, k, p = round_of(e, self.CYCLE)
        if n > 1 and k < RENEW:
            self._renew(g, k, e, t)
            return
        r = self.size(e)
        f = (k % CHUNK) / 1.3
        swallow = 1.0 <= f < 1.4
        self.cloud(g, r, t, angry=1 if f < 1 else 0)
        self.stream(g, r, t)
        self.imp(g, f, r)
        gourd(g, cork=0, t=t, shake=0.8 if swallow else 0.25)
        if swallow:
            sparkle(g, *mouth(), 3)
        self.label(g, e)
        self.mx(g, p, t)
        g.mx_level = 3 if swallow else 1

    def _renew(self, g: Gfx, k: float, e: float, t: float):
        """收尽：塞子落下塞口，葫芦一阵抖、一闪；左边地上又冒起一团新妖气，塞子再弹开"""
        cork = ease_in(span(k, 0, 0.5)) if k < 2.6 else 1 - span(k, 2.6, 3.0)
        shake = 1.5 * (1 - span(k, 0.5, 1.6)) if k > 0.5 else 0
        grow = ease_out_back(span(k, 2.0, 3.4))
        self.cloud(g, R0 * grow, t, pull=span(k, 3.0, 4.0), cy=lerp(70, CLOUD[1], grow))
        if k > 3.2:
            self.stream(g, R0, t, span(k, 3.2, 4.0))
        gourd(g, cork=cork if k < 3.0 else 0, t=t, shake=shake, glow=(1 - span(k, 1.4, 2.2)) if k > 1.0 else 0)
        self.label(g, e, s=None if k > 2.0 else nth(int(e // self.CYCLE), "妖"))
        self.mx(g, 1.0 if k < 2.0 else 0.0, t, cork=k < 3.0)
        g.mx_level = 4 if 1.0 < k < 1.4 else 1

    def interrupt(self, g: Gfx, t: float, e: float):
        _, _, p = round_of(e, self.CYCLE)
        r = self.size(e)
        cork = ease_in(span(t, 0.3, 0.8))
        pull = 1 - span(t, 0.2, 1.0)
        self.cloud(g, r, t, pull=pull)
        self.stream(g, r, t, 1 - span(t, 0, 0.5))
        gourd(g, cork=cork, t=t)
        self.label(g, e, s="塞口" if t > 0.6 else None)
        self.mx(g, p, t, cork=t > 0.8)

    def resume(self, g: Gfx, t: float, e: float):
        _, _, p = round_of(e, self.CYCLE)
        r = self.size(e)
        cork = 1 - span(t, 0.3, 0.8)
        self.cloud(g, r, t, pull=span(t, 0.6, 1.4))
        self.stream(g, r, t, span(t, 0.7, 1.4))
        gourd(g, cork=cork if t < 0.8 else 0, t=t)
        if 0.3 < t < 0.6:
            sparkle(g, *mouth(), 3)
        self.label(g, e)
        self.mx(g, p, t, cork=t < 0.3)

    def complete(self, g: Gfx, t: float, e: float):
        # 一口猛吸，妖气整团被拉成一条吞进去；塞口，猛抖，放光
        _, _, p = round_of(e, self.CYCLE)
        r0 = self.size(e)
        r = r0 * (1 - ease_in(span(t, 0.2, 2.0)))
        pull = 1 + 2 * span(t, 0, 1.2)
        if t < 2.1:
            self.cloud(g, r, t, pull=pull, angry=2)
            self.stream(g, max(r, 2), t * 1.8, 1.4)
            gourd(g, cork=0, t=t, shake=0.6 + span(t, 0.2, 2.0))
            self.label(g, e)
            self.mx(g, lerp(p, 1, span(t, 0.2, 2.0)), t)
            return
        cork = ease_in(span(t, 2.1, 2.5))
        shake = 2.0 * (1 - span(t, 2.5, 3.4)) if t > 2.5 else 0
        glow = ease_out(span(t, 3.2, 4.0))
        gourd(g, cork=cork, t=t, shake=shake, glow=glow)
        if t > 3.4:
            g.d.rectangle((6, 18, 74, 34), fill=0)
            typewriter(g, 40, 21, "邪祟尽收", t - 3.5, cps=5, align="center")
            for j in range(6):
                if blink(t + j * 0.17, 0.5, 0.3):
                    g.px(10 + rand(j, 3) * 60, 4 + rand(j, 4) * 50)
        self.label(g, e, s="收")
        self.mx(g, 1.0, t, cork=cork >= 1)
        g.mx_level = 1 + int(5 * span(t, 2.5, 2.7) * (1 - span(t, 2.7, 4.2)))
