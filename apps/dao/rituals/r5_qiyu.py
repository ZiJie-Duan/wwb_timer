"""祈雨：云聚龙行，甘霖落下，旱田返青。

依据：道教祈雨属雷法的职能之一（神霄派《神霄紫书》目录有“三十六雷部”“祈雨止雨法”，宋元以后雷法道士为地方禳旱），
民间祈雨以龙王为主神，龙行云中、云行雨施；“风调雨顺”为醮坛常见祝语。

入场：烈日弹出、光芒四射，旱田上裂纹一道道裂开。
持续：一轮 10 分钟为一场雨：先云从两边聚拢、遮住太阳，一条龙在云间穿行；雨由疏到密，雨点在地上溅起；
      田里裂纹渐渐弥合，禾苗随计时长高、抽穗。一场下完：云开日出，挂一道虹，禾穗低垂；
      之后田土复干，裂纹重现，“第几场”加一。
中断：雨收住，龙隐入云中，“雨歇”。
恢复：龙从云里探出，雨又下起来。
圆满：龙腾空而去，云开日出，彩虹横天，“风调雨顺”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import rain, ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r5_util import cloud_blobs, mist

GROUND = 52
SEED_X = [22 + i * 9 for i in range(10)]
SUN = (100, 11)
RENEW = 6.0


def crack_lines(seed: int):
    """旱田裂纹（若干条折线，带分叉）"""
    out = []
    for i in range(7):
        x = 18 + i * 13 + (rand(i, seed) - 0.5) * 6
        y = GROUND + 2 + rand(i + 50, seed) * 3
        pts = [(x, y)]
        for j in range(4):
            x += 2 + rand(i * 7 + j, seed + 1) * 4
            y += (rand(i * 7 + j, seed + 2) - 0.35) * 5
            y = min(max(y, GROUND + 2), 62)
            pts.append((x, y))
        out.append(pts)
        bx, by = pts[2]
        out.append([(bx, by), (bx - 2, by + 3), (bx - 1, by + 6)])
    return out


@register
class Qiyu(Ritual):
    id = "r5.qiyu"
    name = "祈雨"
    desc = "烈日旱田，云聚龙行，雨由疏到密，裂纹弥合、禾苗长高抽穗；一场下完云开挂虹"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.6, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.cracks = crack_lines(self.seed)

    # ------------------------------------------------------------ 状态（p = 本场进度）

    def p(self, e: float) -> float:
        return (e % self.CYCLE) / self.CYCLE

    @staticmethod
    def gather(p):
        return ease_in_out(span(p, 0.0, 0.12))

    @staticmethod
    def rainy(p):
        return span(p, 0.1, 0.25)

    @staticmethod
    def wet(p):
        return span(p, 0.12, 0.5)

    @staticmethod
    def grow(p):
        return span(p, 0.25, 0.95)

    # ------------------------------------------------------------ 零件

    def sun(self, g: Gfx, t: float, a: float = 1.0):
        if a <= 0:
            return
        x, y = SUN
        r = 5 * a
        g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
        for i in range(8):
            ang = i / 8 * 2 * math.pi + t * 0.3
            r0, r1 = r + 2, r + 4 + 2 * (blink(t + i * 0.1, 0.8))
            g.d.line((x + math.cos(ang) * r0, y + math.sin(ang) * r0, x + math.cos(ang) * r1,
                      y + math.sin(ang) * r1), fill=1)

    def shimmer(self, g: Gfx, t: float, a: float):
        """旱地上蒸腾的热气"""
        if a <= 0.3:
            return
        for j in range(4):
            x0 = 28 + j * 22 + (j % 2) * 5
            ph = (t * 0.7 + j * 0.37) % 1
            for i in range(0, 12, 2):
                y = GROUND - 3 - i - ph * 8
                if rand(i + j * 20, int(t * 4)) < a * 0.9:
                    g.px(x0 + math.sin(y * 0.6 + t * 3 + j) * 1.5, y)

    def ground(self, g: Gfx, wet: float, crack_draw: float = 1.0):
        g.d.line((0, GROUND, 127, GROUND), fill=1)
        dry = 1 - wet
        for i, pts in enumerate(self.cracks):
            k = clamp(dry * 1.4 - i * 0.04) * crack_draw
            n = int(round(k * (len(pts) - 1)))
            if n >= 1:
                g.d.line(pts[:n + 1], fill=1)
        if wet > 0.3:  # 水洼
            for i in range(5):
                x = 16 + rand(i, self.seed + 9) * 90
                y = GROUND + 4 + rand(i + 3, self.seed + 9) * 7
                w = 3 + 5 * wet
                g.d.line((x - w, y, x + w, y), fill=1)

    def seedlings(self, g: Gfx, h: float, t: float, sway: float = 0.4):
        if h <= 0.02:
            return
        for i, x in enumerate(SEED_X):
            hh = h * (11 + rand(i, self.seed) * 3)
            lean = math.sin(t * 1.5 + i * 0.7) * sway * (hh / 12)
            top = (x + lean, GROUND + 3 - hh)
            g.d.line((x, GROUND + 3, top[0], top[1]), fill=1)
            if hh > 4:  # 两片叶
                my = GROUND + 3 - hh * 0.45
                g.d.line((x + lean * 0.4, my, x + lean * 0.4 - 3, my - 3), fill=1)
                g.d.line((x + lean * 0.5, my - 2, x + lean * 0.5 + 3, my - 5), fill=1)
            if h > 0.75:  # 抽穗、低垂
                droop = span(h, 0.75, 1.0)
                for j in range(3):
                    g.px(top[0] + 1 + j * droop, top[1] + j * droop * 1.2 - (1 - droop) * j)

    def dragon(self, g: Gfx, t: float, appear: float = 1.0, lift: float = 0.0, speed: float = 1.0):
        """云间穿行的龙：空心的 S 形身子（上下两道轮廓、鳞纹、背鳍、两爪）+ 龙头（角、须、眼）"""
        if appear <= 0:
            return
        s = t * 24 * speed
        segs = 22
        pts = []
        for i in range(segs):
            u = s - i * 3.2
            x = (u % 210) - 40
            y = 30 - lift + math.sin(u * 0.085) * 6 + (1 - appear) * -45
            pts.append((x, y))
        body = [pts[0]]
        for i in range(1, segs):  # 跨屏幕边缘时断开
            if abs(pts[i][0] - pts[i - 1][0]) > 20:
                break
            body.append(pts[i])
        n = len(body)
        up, lo = [], []
        for i in range(n):
            x0, y0 = body[max(i - 1, 0)]
            x1, y1 = body[min(i + 1, n - 1)]
            L = math.hypot(x1 - x0, y1 - y0) or 1
            nx, ny = -(y1 - y0) / L, (x1 - x0) / L
            r = lerp(3.4, 0.6, i / segs)
            x, y = body[i]
            up.append((x + nx * r, y + ny * r))
            lo.append((x - nx * r, y - ny * r))
        if n > 1:
            g.d.polygon(up + lo[::-1], fill=0)
            g.d.line(up, fill=1)
            g.d.line(lo, fill=1)
            for i in range(2, n - 4, 2):  # 鳞
                x, y = body[i]
                g.px(x, y)
                g.px(x - 1, y - 1)
            for i in range(2, n - 5, 3):  # 背鳍：朝上的小刺
                x, y = up[i]
                g.d.line((x, y, x - 1, y - 3), fill=1)
            for i in (4, 11):  # 爪
                if i < n:
                    x, y = lo[i]
                    g.d.line((x, y, x - 2, y + 4), fill=1)
                    g.d.line((x - 2, y + 4, x + 1, y + 5), fill=1)
        hx, hy = pts[0]
        g.d.polygon([(hx - 3, hy - 4), (hx + 3, hy - 4), (hx + 9, hy - 1), (hx + 9, hy + 1), (hx + 4, hy + 1),
                     (hx + 8, hy + 3), (hx + 2, hy + 4), (hx - 3, hy + 3)], fill=0, outline=1)
        g.d.rectangle((hx + 1, hy - 2, hx + 2, hy - 1), fill=1)  # 眼
        g.d.line((hx - 2, hy - 4, hx - 7, hy - 9), fill=1)  # 角
        g.d.line((hx - 5, hy - 7, hx - 7, hy - 6), fill=1)
        g.d.line((hx + 9, hy, hx + 14, hy + 3 + math.sin(t * 4) * 1.5), fill=1)  # 须
        g.d.line((hx + 8, hy - 1, hx + 13, hy - 5 + math.cos(t * 4) * 1.5), fill=1)

    def clouds(self, g: Gfx, gather: float, t: float, part: float = 0.0):
        bl = []
        drift = t * 1.5
        for i, (cx, w) in enumerate(((10, 50), (48, 56), (86, 56), (122, 50))):
            side = -1 if cx < 64 else 1
            off = side * (1 - gather) * 90 + side * part * 80
            bl += cloud_blobs(cx + off + math.sin(drift * 0.2 + i) * 3, 6 + (i % 2) * 3, w, 18, 60 + i)
        mist(g, bl, 0.12 + 0.18 * gather)

    def front_cloud(self, g: Gfx, gather: float, t: float, part: float = 0.0):
        """压在龙身上的几朵云（龙穿云而过）"""
        if gather <= 0.3:
            return
        x = 40 + math.sin(t * 0.15) * 10
        off = part * 120
        mist(g, cloud_blobs(x - off, 17, 26, 9, 77) + cloud_blobs(96 + off, 16, 22, 8, 78), 0.2)

    def rainbow(self, g: Gfx, a: float):
        if a <= 0:
            return
        for j, r in enumerate((44, 48, 52)):
            n = int(140 * a)
            for i in range(n):
                ang = math.pi + i / 140 * math.pi
                if (i + j) % (j + 1) == 0:
                    g.px(64 + math.cos(ang) * r * 1.25, GROUND + 2 + math.sin(ang) * r)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        g.d.rectangle((0, 28, 14, 52), fill=0)
        g.vtext(2, 29, "祈雨"[:int(round(a * 2))])
        full = right if right is not None else f"第{cn_num(n)}场"
        r = full[:int(round(a * len(full)))]
        y0 = 52 - len(full) * 12
        g.d.rectangle((113, y0 - 1, 127, 52), fill=0)
        g.vtext(114, y0, r)

    def mx(self, g: Gfx, t: float, rainy: float, sun: float, grow: float):
        if sun > 0.5 and rainy <= 0:
            g.mx_rows([0x00, 0x18, 0x7E, 0x3C, 0x3C, 0x7E, 0x18, 0x00])  # 日
            if blink(t, 1.0):
                g.mx_rows([0x99, 0x5A, 0x3C, 0x7E, 0x7E, 0x3C, 0x5A, 0x99])
            return
        g.mx[0, 1:7] = True
        g.mx[1, 0:8] = True
        if rainy > 0:
            n = int(2 + rainy * 6)
            for i in range(n):
                x = int(rand(i, 3) * 8)
                y = 2 + int((t * 6 + rand(i, 4) * 6) % 6)
                g.mx_set(x, y)
        if grow > 0:
            h = int(round(grow * 4))
            for x in (1, 4, 6):
                for y in range(7, 7 - h, -1):
                    g.mx_set(x, y)

    # ------------------------------------------------------------ 阶段

    def scene(self, g: Gfx, t: float, e: float, rain_mul: float = 1.0, dragon_appear: float | None = None,
              right: str | None = None):
        p = self.p(e)
        gather, rainy, wet, grow = self.gather(p), self.rainy(p), self.wet(p), self.grow(p)
        self.sun(g, t, 1 - span(gather, 0.4, 0.9))
        self.shimmer(g, t, 1 - gather * 2)
        self.clouds(g, gather, t)
        r = rainy * rain_mul
        if r > 0:
            rain(g, t, self.seed, n=int(6 + 34 * r), speed=80, length=3, slant=0.15, box=(0, 18, 128, GROUND))
            for i in range(int(8 * r)):  # 溅起的水花
                ph = (t * 3 + rand(i, 5)) % 1
                if ph < 0.3:
                    x = rand(i + int(t * 3 + rand(i, 5)) * 13, 6) * 128
                    g.px(x - 1, GROUND - 1)
                    g.px(x + 1, GROUND - 1)
        app = span(p, 0.08, 0.14) if dragon_appear is None else dragon_appear
        self.dragon(g, t, app)
        self.front_cloud(g, gather, t)
        self.ground(g, wet)
        self.seedlings(g, grow, t)
        self.texts(g, e, right)
        self.mx(g, t, r, 1 - gather, grow)

    def enter(self, g: Gfx, t: float):
        self.sun(g, t, ease_out_back(span(t, 0, 0.8)))
        self.ground(g, 0.0, crack_draw=span(t, 0.6, 2.4))
        self.shimmer(g, t, span(t, 1.6, 3.0))
        self.texts(g, 0, a=span(t, 2.4, 3.6))
        g.mx_level = 1
        self.mx(g, t, 0, 1, 0)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        self.scene(g, t, e)

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """一场下完：云开日出挂虹（0-3.5s），之后田土复干（3.5-6s）"""
        part = ease_in_out(span(k, 0, 2.0))
        dry = span(k, 3.6, 5.6)
        self.sun(g, t, ease_out_back(span(k, 1.0, 2.0)))
        self.rainbow(g, span(k, 1.4, 2.6) * (1 - span(k, 3.4, 4.0)))
        if part < 1:
            self.clouds(g, 1.0, t, part=part)
            self.dragon(g, t, 1.0, lift=part * 40)
            self.front_cloud(g, 1.0, t, part=part)
        self.ground(g, 1 - dry)
        self.seedlings(g, 1.0 - dry, t, sway=0.8)
        if k < 1.0:
            rain(g, t, self.seed, n=int(40 * (1 - k)), speed=80, length=3, slant=0.15, box=(0, 18, 128, GROUND))
        self.texts(g, e if k > 3.6 else e - k - 1)
        self.mx(g, t, 0, 1 if k > 1.0 else 0, 1 - dry)

    def interrupt(self, g: Gfx, t: float, e: float):
        p = self.p(e)
        stop = ease_out(span(t, 0, 0.8))
        self.scene(g, t, e, rain_mul=1 - stop, dragon_appear=span(p, 0.08, 0.14) * (1 - ease_in(span(t, 0.2, 1.3))),
                   right="雨歇" if t > 0.6 else None)

    def resume(self, g: Gfx, t: float, e: float):
        p = self.p(e)
        self.scene(g, t, e, rain_mul=ease_in(span(t, 0.6, 1.6)),
                   dragon_appear=span(p, 0.08, 0.14) * ease_out(span(t, 0, 1.0)), right="雨歇" if t < 0.5 else None)

    def complete(self, g: Gfx, t: float, e: float):
        p = self.p(e)
        gather = self.gather(p)
        part = ease_in_out(span(t, 0.8, 2.6))
        self.sun(g, t, ease_out_back(span(t, 2.0, 3.0)))
        self.rainbow(g, span(t, 2.4, 3.8))
        if part < 1:
            self.clouds(g, max(gather, 0.5), t, part=part)
            self.dragon(g, t, 1.0, lift=ease_in(span(t, 0.2, 2.0)) * 50, speed=1.6)
        self.ground(g, max(self.wet(p), span(t, 0, 2.0)))
        self.seedlings(g, max(self.grow(p), ease_out(span(t, 1.0, 3.0))), t, sway=0.8)
        if t < 1.2:
            rain(g, t, self.seed, n=int(40 * (1 - t / 1.2)), speed=80, length=3, slant=0.15, box=(0, 18, 128, GROUND))
        if t > 3.0:
            g.d.rectangle((24, 30, 104, 44), fill=0)
            typewriter(g, 64, 32, "风调雨顺", t - 3.0, cps=5, align="center")
        if t < 2.0:
            self.texts(g, e, a=1 - span(t, 1.2, 2.0))
        self.mx(g, t, 0, 1 if t > 2.0 else 0, 1.0)
        if 2.0 < t < 3.0:
            g.mx_level = 4
