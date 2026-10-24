"""听雨：温庭筠《更漏子》“梧桐树，三更雨，不道离情正苦。一叶叶，一声声，空阶滴到明。”

入场：屋檐从上方压下来，第一滴水在滴水瓦尖上鼓起、落下，阶前溅起水花，雨声渐密。
持续：檐下一排瓦当、滴水，每个瓦尖按自己的节奏滴水：水珠鼓胀 → 落下 → 石阶上溅开、漾出一圈水纹；
      石阶上被滴出一个个小坑（滴水穿石，“天下莫柔弱于水，而攻坚强者莫之能胜”）。
      左边一片芭蕉被檐水打得一颤一颤（雨打芭蕉）。远山在雨里若有若无。
      小事件：青蛙跳上石阶鼓腮叫两声又跳走；远处闷雷一闪，随后雨下得急一阵；蜗牛沿匾绳慢慢往上爬。
退场：屋檐收起，雨帘落尽。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import lightning, rain
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x3_lib import ctext, ptext, every, halo, layer, peaks

EAVE = 6          # 檐口
TIP = 12          # 滴水瓦尖（水珠挂在这里）
STEP = 50         # 石阶面
DRIPS = [10, 20, 30, 40, 50, 60, 70, 80]  # 滴水位置（右边被匾挡住的不画）
LEAF_DRIP = 2     # 第 3 个滴水落在芭蕉上
LEAF_BASE = (3, 63)

FROG = [halo(Sprite("""
  .##.##.
  #######
  .#####.
  ##...##
""")), halo(Sprite("""
  .##.##.
  #######
  ######.
  .##.##.
  #.....#
"""))]


@register
class ListenRain(Rest):
    id = "x3.rain"
    name = "听雨"
    desc = "檐下滴水一声声落在空阶上，溅花、漾纹，滴出小坑；雨打芭蕉，青蛙偶来，闷雷远去"
    T = {"enter": 2.8, "exit": 1.2}

    def setup(self):
        s = self.seed
        self.hills = layer(peaks(128, 46, [(20, 30, 30), (64, 24, 26), (108, 32, 30)], s, 1.0), 0.14, outline=2,
                           fog=10, floor=0.0)
        self.period = [2.4 + rand(i, s) * 2.2 for i in range(len(DRIPS))]
        self.phase = [rand(i + 40, s) for i in range(len(DRIPS))]
        self.period[LEAF_DRIP] = 3.1

    # ------------------------------------------------------------ 零件

    def roof(self, g: Gfx, dy: float = 0.0):
        y0 = dy
        g.d.rectangle((0, y0, 127, y0 + EAVE - 1), fill=0)
        for x in range(-4, 132, 5):                       # 瓦垄
            g.d.line((x + 2, y0, x, y0 + EAVE - 2), fill=1)
        g.d.line((0, y0 + EAVE - 1, 127, y0 + EAVE - 1), fill=1)
        for i, x in enumerate(range(5, 128, 10)):        # 瓦当（圆）与滴水（三角）相间
            g.d.ellipse((x - 2, y0 + EAVE, x + 2, y0 + EAVE + 4), fill=0, outline=1)
            g.px(x, y0 + EAVE + 2)
            xd = x + 5
            g.d.polygon([(xd - 3, y0 + EAVE), (xd + 3, y0 + EAVE), (xd, y0 + TIP - 1)], fill=1)

    def plaque(self, g: Gfx, dy: float = 0.0, swing: float = 0.0):
        """匾“听雨”"""
        x0, y0 = 92 + swing, 14 + dy
        g.d.line((x0 + 5 - swing, EAVE + dy, x0 + 5, y0), fill=1)
        g.d.line((x0 + 29 - swing, EAVE + dy, x0 + 29, y0), fill=1)
        g.d.rectangle((x0, y0, x0 + 34, y0 + 18), fill=0, outline=1)
        g.d.rectangle((x0 + 2, y0 + 2, x0 + 32, y0 + 16), outline=1)
        ctext(g, x0 + 17, y0 + 4, "听雨", align="center")

    def snail(self, g: Gfx, t: float):
        """蜗牛沿匾左边的绳往上爬，十分钟爬一趟"""
        p = (t % 600.0) / 600.0
        y = lerp(30, 9, p)
        x = 96
        if p > 0.97:
            return
        g.d.ellipse((x - 3, y, x + 1, y + 4), fill=0, outline=1)
        g.px(x - 1, y + 2)
        g.d.line((x, y - 2, x, y), fill=1)  # 触角
        if int(t * 1.5) % 3:
            g.px(x - 1, y - 3)

    def steps(self, g: Gfx, t: float):
        g.d.rectangle((0, STEP, 127, 63), fill=0)
        g.d.line((0, STEP, 127, STEP), fill=1)
        g.d.line((0, 57, 127, 57), fill=1)
        for x in (24, 66, 104):
            g.d.line((x, STEP + 1, x, 56), fill=1)
        for x in (8, 46, 88, 122):
            g.d.line((x, 58, x, 63), fill=1)
        for i, x in enumerate(DRIPS):                       # 滴水穿石：每个滴点下一个小坑
            if i != LEAF_DRIP:
                g.d.line((x - 1, STEP, x + 1, STEP), fill=0)
                g.px(x, STEP + 1)
        for j in range(18):  # 石面的苔点
            g.px(rand(j, 21) * 128, 59 + rand(j, 22) * 5)

    def drip(self, g: Gfx, i: int, t: float, rate: float = 1.0):
        x = DRIPS[i]
        P = self.period[i] / rate
        k = (t / P + self.phase[i])
        n = math.floor(k)
        p = k - n
        fall_at, land_y = 0.62, STEP - 1
        if i == LEAF_DRIP:
            land_y = self.leaf_hit_y()
        if p < fall_at:  # 水珠在瓦尖慢慢鼓起来
            sz = p / fall_at
            g.px(x, TIP)
            if sz > 0.45:
                g.px(x, TIP + 1)
            if sz > 0.8:
                g.d.rectangle((x - 1 if sz > 0.92 else x, TIP + 1, x, TIP + 2), fill=1)
        ft = (p - fall_at) * P  # 下落经过的秒数
        fall_s = math.sqrt(2 * (land_y - TIP) / 260.0)
        if p >= fall_at and ft < fall_s:
            y = TIP + 0.5 * 260 * ft * ft
            g.d.line((x, y - 2, x, y), fill=1)
        # 上一滴（或这一滴）落地之后的水花、水纹
        since = ft - fall_s if p >= fall_at else (p + 1 - fall_at) * P - fall_s
        if 0 <= since < 1.0 and i != LEAF_DRIP:
            for j, (vx, vy) in enumerate(((-18, -22), (16, -26), (-9, -30), (10, -16))):
                if since < 0.32:
                    sx = x + vx * since
                    sy = land_y + vy * since + 0.5 * 260 * since * since
                    if sy <= land_y:
                        g.px(sx, sy)
            r = ease_out(since) * 9
            if since > 0.08 and r > 1:
                g.d.arc((x - r, STEP - 1.5, x + r, STEP + 1.5), 0, 360, fill=1) if since < 0.55 else None
                if since >= 0.55:
                    for a in range(0, 360, 30):
                        if rand(a + n * 7, i) < 1 - since:
                            g.px(x + math.cos(math.radians(a)) * r, STEP + math.sin(math.radians(a)) * 1.5)
        return since if i == LEAF_DRIP else None

    def leaf_hit_y(self) -> float:
        return 26.0

    def leaf(self, g: Gfx, t: float):
        """芭蕉：宽叶、横向平行叶脉、边上有被风撕开的口子；被檐水打中就一颤"""
        i = LEAF_DRIP
        P = self.period[i]
        k = t / P + self.phase[i]
        p = k - math.floor(k)
        fall_s = math.sqrt(2 * (self.leaf_hit_y() - TIP) / 260.0)
        since = (p - 0.62) * P - fall_s
        if since < 0:
            since += P
        ang = -0.12 * math.exp(-since * 3.5) * math.cos(since * 14)
        ang += (noise(t * 0.3, self.seed) - 0.5) * 0.04
        bx, by = LEAF_BASE
        ca, sa = math.cos(ang), math.sin(ang)

        def rot(px, py):
            dx, dy = px - bx, py - by
            return bx + dx * ca - dy * sa, by + dx * sa + dy * ca

        N = 16
        p0, p1, p2 = (bx + 5, by - 4), (bx + 8, by - 46), (bx + 50, by - 30)
        spine = []
        for j in range(N + 1):  # 二次贝塞尔：叶柄往上，叶片向右拱、叶尖下垂
            u = j / N
            q = ((1 - u) ** 2 * p0[0] + 2 * u * (1 - u) * p1[0] + u * u * p2[0],
                 (1 - u) ** 2 * p0[1] + 2 * u * (1 - u) * p1[1] + u * u * p2[1])
            spine.append(rot(*q))
        top, bot = [], []
        for j in range(N + 1):
            u = j / N
            wdt = 0.8 if u < 0.2 else 8.5 * math.sin(math.pi * (u - 0.2) / 0.8) ** 0.6 + 0.6
            if j in (9, 12):          # 撕裂的口子
                wdt *= 0.45
            a_, b_ = spine[max(j - 1, 0)], spine[min(j + 1, N)]
            nx, ny = b_[0] - a_[0], b_[1] - a_[1]
            ln = math.hypot(nx, ny) or 1
            px_, py_ = ny / ln, -nx / ln          # 指向叶片上侧
            sx, sy = spine[j]
            top.append((sx + px_ * wdt, sy + py_ * wdt))
            bot.append((sx - px_ * wdt * 0.7, sy - py_ * wdt * 0.7))
        nx0 = bx + 9                                           # 后面一卷还没展开的新叶
        g.d.polygon([(nx0, 63), (nx0 - 1, 40), (nx0 + 1, 24), (nx0 + 3, 40), (nx0 + 3, 63)], fill=0, outline=1)
        g.d.polygon(top + bot[::-1], fill=0, outline=1)
        for j in range(4, N - 1, 2):     # 平行侧脉：从主脉斜向叶尖方向伸到叶缘
            g.d.line((spine[j], top[min(j + 1, N)]), fill=1)
        g.d.line(spine, fill=1)
        g.d.line((bx + 2, 63, spine[0][0], spine[0][1]), fill=1)   # 芭蕉茎
        g.d.line((bx + 7, 63, spine[0][0] + 1, spine[0][1]), fill=1)
        if 0 <= since < 0.3:  # 打在叶上的水花
            for vx, vy in ((-14, -20), (12, -18), (2, -26)):
                g.px(DRIPS[i] + vx * since, self.leaf_hit_y() - 2 + vy * since + 130 * since * since)

    def frog(self, g: Gfx, t: float):
        ev = every(t, 83.0, 15.0, 37.0)
        if not ev:
            return False
        k, lt = ev
        sit_x = 40 + rand(k, 4) * 30
        y = STEP
        if lt < 1.2:  # 跳上来
            p = lt / 1.2
            x = lerp(-8, sit_x, p)
            yy = y - 6 - math.sin(p * math.pi) * 10
            g.blit(FROG[1], x, yy)
        elif lt < 13.6:
            g.blit(FROG[0], sit_x, y - 5)
            c = lt - 1.2
            if 3 < c < 4.4 or 6 < c < 7.4:  # 鼓腮
                r = 1.5 + math.sin((c % 3 - 0) * math.pi / 1.4) * 1.5
                g.d.ellipse((sit_x + 2 - r, y - 1 - r * 0.5, sit_x + 4 + r, y + r * 0.5), fill=0, outline=1)
                if int(c * 6) % 2:
                    ctext(g, sit_x + 10, y - 13, "呱", size=8)
        else:  # 跳走
            p = (lt - 13.6) / 1.4
            x = lerp(sit_x, 140, p)
            yy = y - 6 - math.sin(p * math.pi * 2 % math.pi) * 8
            g.blit(FROG[1], x, yy)
        return True

    def thunder(self, g: Gfx, t: float) -> float:
        """远雷：一闪，之后雨急一阵。返回雨势倍数"""
        ev = every(t, 151.0, 18.0, 64.0)
        if not ev:
            return 1.0
        k, lt = ev
        if lt < 0.12 or 0.22 < lt < 0.3:
            x = 30 + rand(k, 9) * 60
            lightning(g, x, 16, x + rand(k, 3) * 10 - 5, 38, seed=k * 3 + self.seed, jag=3, branches=1)
        return 1.0 + 0.8 * span(lt, 1.5, 3.5) * (1 - span(lt, 12, 18))

    def mx(self, g: Gfx, t: float, rate: float = 1.0):
        g.mx[0, :] = True
        for c, per in ((1, 1.3), (4, 1.7), (6, 1.1)):
            p = (t * rate / per + c * 0.37) % 1.0
            y = 1 + int(p * 7.5)
            if y <= 6:
                g.mx_set(c, y)
            else:
                g.mx_set(c - 1, 7)
                g.mx_set(c + 1, 7)
        for x in range(8):
            if rand(x + int(t * 3) * 8, 5) < 0.12:
                g.mx_set(x, 7)

    # ------------------------------------------------------------ 阶段

    def scene(self, g: Gfx, t: float, rate: float = 1.0, dy: float = 0.0, drips: bool = True):
        g.blit(self.hills, 0, 0)
        rain(g, t, self.seed, n=int(22 * rate), speed=110, length=3, slant=0.18, box=(0, EAVE + 2 + dy, 128, STEP))
        self.steps(g, t)
        if drips:
            for i in range(len(DRIPS)):
                self.drip(g, i, t, rate if i != LEAF_DRIP else 1.0)
        self.leaf(g, t)
        self.roof(g, dy)
        self.plaque(g, dy, swing=(noise(t * 0.4, self.seed + 3) - 0.5) * 1.2)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        dy = -(1 - ease_out(span(t, 0, 1.0))) * 30   # 屋檐从上方压下来
        rate = 0.3 + 0.7 * span(t, 0.8, T)
        g.blit(self.hills, 0, 0)
        rain(g, t, self.seed, n=int(22 * rate), speed=110, length=3, slant=0.18, box=(0, EAVE + 2 + dy, 128, STEP))
        self.steps(g, t)
        if t > 1.0:
            for i in range(len(DRIPS)):
                if t - 1.0 > i * 0.12:
                    self.drip(g, i, t, 1.0)
        self.leaf(g, t)
        self.roof(g, dy)
        self.plaque(g, dy, swing=math.sin(t * 6) * 3 * (1 - span(t, 1.0, 2.5)))
        self.mx(g, t, rate)

    def hold(self, g: Gfx, t: float):
        rate = 1.0 + 0.3 * (noise(t / 40, self.seed) - 0.5)
        g.blit(self.hills, 0, 0)
        rate *= self.thunder(g, t)
        rain(g, t, self.seed, n=int(22 * rate), speed=110 * min(rate, 1.3), length=3 + int(rate > 1.4), slant=0.18,
             box=(0, EAVE + 2, 128, STEP))
        self.steps(g, t)
        for i in range(len(DRIPS)):
            self.drip(g, i, t, 1.0)
        self.leaf(g, t)
        self.frog(g, t)
        self.roof(g)
        self.plaque(g, swing=(noise(t * 0.4, self.seed + 3) - 0.5) * 1.2)
        self.snail(g, t)
        self.poem(g, t)
        self.mx(g, t, rate)

    def poem(self, g: Gfx, t: float):
        """空阶滴到明：隔一阵在石阶上浮现一次"""
        ev = every(t, 120.0, 22.0, 6.0)
        if not ev:
            return
        lt = ev[1]
        k = span(lt, 0, 2.5) * (1 - span(lt, 19, 22))
        s = "空阶滴到明"
        n = int(round(k * len(s)))
        if n:
            g.d.rectangle((64, STEP + 1, 127, 63), fill=0)
            ptext(g, 66, STEP + 2, s, n)

    def exit(self, g: Gfx, t: float):
        """屋檐收起，雨帘落尽，画面淡去"""
        T = self.T["exit"]
        p = ease_in(t / T)
        self.scene(g, self.hold_t + t, rate=1 - p, dy=-p * 30, drips=p < 0.3)
        g.fade(1 - ease_in(span(t, 0.2, T)))
        self.mx(g, t, 1.0)
        g.mx[:int(round(p * 8)), :] = False
