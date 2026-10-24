"""放河灯：中元夜，月下江面，一只手把一盏莲花灯放进水里，灯随波漂远、越漂越小；一盏接一盏。

依据：农历七月十五中元节，道经以为“地官赦罪”之日；宫观设中元普度，夜放水灯（河灯、荷花灯）照引幽冥。
（中国非遗网“中元节”条：水灯以纸或木为底，形似荷花，上安灯盏，七月十五夜点燃放入江河任其漂流。）

入场：夜色里月亮升起、水纹铺开，手放下第一盏灯，水面荡起一圈涟漪。
持续：每 60 秒放一盏（一轮十盏 = 600 秒），灯漂 300 秒到天边，画面上同时漂着五盏、远近大小不同，
      火苗跳、倒影晃、灯随波起伏；月影在水里碎成一串。
      一轮结束：远处一只纸扎法船（中元烧法船）从左到右驶过天边，右侧“第几轮”加一。
中断：江雾从两边漫过来，灯火变暗成豆，“雾锁江”。
恢复：雾散，灯火复明。
圆满：江上所有灯的火光一齐离灯升空，化作星点，“中元普度”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import flame, ring, stars
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import sleeve, vreveal

HORIZON = 24
NEAR_Y = 56
STEP = 60.0
TRAVEL = 300.0
MOON = (100, 10)
RENEW = 9.0


def lotus_lamp(g: Gfx, x: float, y: float, s: float, t: float, seed: int, lit: float = 1.0, reflect: bool = True):
    """莲花灯：(x, y) 为吃水线中心，s 缩放（1 = 近处）"""
    d = g.d
    w = 9 * s
    if s < 0.32:  # 远处：一个小点加火
        d.line((x - 1, y, x + 1, y), fill=1)
        if lit > 0.5:
            g.px(x, y - 1)
            if blink(t + seed * 0.3, 0.7, 0.6):
                g.px(x, y - 2)
        return
    d.chord((x - w, y - 3 * s, x + w, y + 2 * s), 0, 180, fill=0, outline=1)   # 底托
    for k in (-2, -1, 0, 1, 2):  # 花瓣：尖朝上
        px = x + k * w * 0.42
        ph = (5 if k == 0 else 4 if abs(k) == 1 else 3) * s
        d.polygon([(px - 2.2 * s, y), (px, y - ph - 1), (px + 2.2 * s, y)], fill=0, outline=1)
    if lit > 0:
        if s > 0.55:
            flame(g, x, y - 5 * s, 5 * s * max(lit, 0.4), 8 * s * lit, t, seed)
        else:
            d.rectangle((x, y - 5 * s - 2, x, y - 5 * s), fill=1)
    if reflect:  # 倒影：碎光
        for j in range(int(3 + 4 * s)):
            yy = y + 3 + j * 2
            if yy >= 64:
                break
            off = math.sin(t * 2 + j * 1.3 + seed) * (1 + j * 0.4)
            if (j + int(t * 3)) % 3 != 2:
                g.px(x + off, yy)


@register
class RiverLamps(Ritual):
    id = "r1.river"
    name = "放河灯"
    desc = "中元夜放莲花灯，一盏盏随波漂远变小，五盏远近同在；一轮十盏后法船驶过天边"
    T = {"enter": 4.0, "interrupt": 1.6, "resume": 1.6, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.sky_seed = self.rng.randrange(1000)

    # ------------------------------------------------------------ 灯（全是 e 的函数）

    def lamp_xy(self, i: int, e: float, t: float):
        """第 i 盏（i 从 0 起，e_i = i*STEP）→ (x, y, s) 或 None"""
        age = e - i * STEP
        if age < 0 or age > TRAVEL:
            return None
        d = age / TRAVEL
        q = 1 - (1 - d) ** 2           # 先快后慢：近大远小
        x0 = 32 + ((i * 0.618 + rand(0, self.seed)) % 1.0) * 60   # 相邻两盏左右错开
        drift = (rand(i + 50, self.seed) - 0.5) * 30
        x = x0 + drift * q + math.sin(age * 0.05 + i) * 3
        y = lerp(NEAR_Y, HORIZON + 2, q)
        s = lerp(1.0, 0.18, q)
        y += math.sin(t * 1.6 + i * 2.1) * s * 1.2  # 随波起伏
        return x, y, s

    def lamps(self, g: Gfx, e: float, t: float, lit: float = 1.0, skip_new: bool = False):
        last = int(e // STEP)
        out = []
        for i in range(max(0, last - 5), last + 1):
            if skip_new and i == last:
                continue
            p = self.lamp_xy(i, e, t)
            if p:
                out.append((p[2], i, p))
        for s, i, (x, y, ss) in sorted(out):  # 远的先画
            lotus_lamp(g, x, y, ss, t + i, self.seed + i, lit=lit)
        return out

    # ------------------------------------------------------------ 景

    def night(self, g: Gfx, t: float, a: float = 1.0):
        mx, my = MOON
        if a > 0:
            r = 6  # 七月十五：满月
            g.d.ellipse((mx - r, my - r, mx + r, my + r), fill=1)
            for dx, dy in ((1, -2), (2, -2), (2, -1), (-3, 1), (-2, 2), (-1, 3)):  # 月面暗斑
                g.px(mx + dx, my + dy, 0)
            ring(g, mx, my, r + 3 + math.sin(t * 1.1), density=4, phase=t * 0.2)
        stars(g, t, self.sky_seed, n=int(10 * a), box=(30, 0, 92, HORIZON - 4), twinkle=0.35)
        # 远山
        pts = [(0, HORIZON)]
        for x in range(0, 129, 8):
            pts.append((x, HORIZON - 3 - 4 * noise(x * 0.07, self.sky_seed)))
        pts.append((128, HORIZON))
        g.d.line(pts[1:-1], fill=1)
        g.d.line((0, HORIZON, 127, HORIZON), fill=1)

    def water(self, g: Gfx, t: float):
        """水纹：近处长、远处短，缓缓横移"""
        for row in range(7):
            k = row / 6
            y = int(lerp(HORIZON + 3, 62, k * k))
            ln = int(2 + 6 * k)
            gap = int(20 + 18 * k)
            off = int(t * (2 + 6 * k) + row * 7) % gap
            for x in range(-gap + off, 128, gap):
                xx = x + int(rand(row * 31 + (x - off) // gap, 5) * 6)
                g.d.line((xx, y, xx + ln, y), fill=1)
        mx, _ = MOON  # 月影：一串碎光
        for j in range(6):
            y = HORIZON + 3 + j * 3
            w = 1 + j
            off = math.sin(t * 1.3 + j) * 1.5
            if (j + int(t * 2)) % 4:
                g.d.line((mx - 2 + off - w / 2, y, mx + 2 + off + w / 2, y), fill=1)

    def texts(self, g: Gfx, e: float, a: float = 1.0, left: str = "地官赦罪"):
        g.d.rectangle((0, 0, 15, len(left) * 12 + 3), fill=0)
        vreveal(g, 2, 2, left, a)
        n = int(e // self.CYCLE) + 1
        r = f"第{cn_num(n)}轮"
        g.d.rectangle((113, 63 - len(r) * 12 - 1, 127, 63), fill=0)
        vreveal(g, 115, 64 - len(r) * 12, r, a)

    def boat(self, g: Gfx, x: float, t: float):
        """法船：远处一只纸扎船，两层楼、三面帆"""
        y = HORIZON + 1 + math.sin(t * 2) * 0.5
        d = g.d
        d.polygon([(x - 12, y - 3), (x + 12, y - 3), (x + 9, y), (x - 9, y)], fill=0, outline=1)
        d.line((x - 14, y - 6, x - 12, y - 3), fill=1)   # 船头翘
        d.line((x + 14, y - 6, x + 12, y - 3), fill=1)
        d.rectangle((x - 6, y - 7, x + 4, y - 4), fill=0, outline=1)  # 楼
        d.line((x - 7, y - 8, x + 5, y - 8), fill=1)
        for mx_, h in ((-9, 9), (7, 11)):
            d.line((x + mx_, y - 3, x + mx_, y - 3 - h), fill=1)
            d.polygon([(x + mx_, y - 3 - h), (x + mx_ + 4, y - 5 - h * 0.4), (x + mx_, y - 5)], fill=0, outline=1)
        if blink(t, 0.4, 0.5):
            g.px(x - 1, y - 6)
            g.px(x + 2, y - 6)

    def placing(self, g: Gfx, i: int, u: float, t: float):
        """放灯：手托灯从画下伸来放进水里（u = 放下前后的秒数，-1.2..1.0）"""
        p = self.lamp_xy(i, i * STEP, t)
        x, y = p[0], NEAR_Y
        if u < 0:
            q = ease_out(span(u, -1.2, -0.1))
            ly = lerp(80, y, q)
            lotus_lamp(g, x, ly, 1.0, t, self.seed + i, reflect=False)
            sleeve(g, x + 2, ly + 6, 1.35, fist=False)
        else:
            q = ease_in(span(u, 0.1, 1.0))
            sleeve(g, x + 2 + q * 6, y + 6 + q * 30, 1.35, fist=False)
        if 0 <= u < 1.0:  # 涟漪
            r = 4 + u * 14
            g.d.arc((x - r, y - r * 0.25, x + r, y + r * 0.25), 0, 180, fill=1)
            if u > 0.3:
                r2 = r - 6
                g.d.arc((x - r2, y - r2 * 0.25, x + r2, y + r2 * 0.25), 0, 180, fill=1)

    def mx(self, g: Gfx, t: float, lit: float = 1.0):
        # 莲花灯
        g.mx_rows([0, 0, 0, 0, 0b01011010, 0b01111110, 0b00111100, 0])
        if lit > 0.5:
            g.mx[3, 3 + (1 if noise(t * 5, self.seed) > 0.6 else 0)] = True
            g.mx[2, 3] = blink(t, 0.5, 0.6)
        elif lit > 0:
            g.mx[3, 3] = blink(t, 1.0, 0.5)
        ph = int(t * 3) % 4  # 水波
        for x in range(8):
            g.mx[7, x] = (x + ph) % 4 < 2

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        a = span(t, 0, 1.2)
        self.night(g, t, a)
        if a < 1:
            g.fade(a, (0, 0, 128, HORIZON + 1))
        w = span(t, 0.6, 1.6)
        if w > 0:
            self.water(g, t)
            if w < 1:
                g.fade(w, (0, HORIZON + 1, 128, 64))
        u = t - 3.0
        if t > 1.8:
            if u < 0:
                self.placing(g, 0, lerp(-1.2, -0.1, span(t, 1.8, 3.0)) if t < 3.0 else 0, t)
            else:
                lotus_lamp(g, *self.lamp_xy(0, 0, t)[:2], 1.0, t, self.seed)
                self.placing(g, 0, u, t)
        self.texts(g, 0, a=span(t, 2.6, 3.8))
        self.mx(g, t, lit=1 if t > 3.0 else 0)
        if t < 1.8:
            g.mx[0:7, :] = False

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        self.night(g, t)
        self.water(g, t)
        if e >= self.CYCLE and k < RENEW:  # 法船驶过天边
            self.boat(g, lerp(-20, 150, k / RENEW), t)
        last = int(e // STEP)
        u = e - last * STEP            # 最新一盏放下了多久
        nxt_u = u - STEP                # 下一盏（负 = 还没放）
        self.lamps(g, e, t, skip_new=(u < 0))
        if u < 1.0:
            self.placing(g, last, u, t)
        elif nxt_u > -1.2:
            self.placing(g, last + 1, nxt_u, t)
        self.texts(g, e)
        self.mx(g, t)
        if u < 0.15:
            g.mx_level = 3

    def _mist(self, g: Gfx, p: float):
        """江雾：从两边漫向中间"""
        if p <= 0:
            return
        w = int(p * 70)
        g.fade(1 - 0.55 * p, (0, HORIZON + 1, 128, 64))  # 雾里水纹和灯都淡下去
        g.shade((0, HORIZON - 4, w, HORIZON + 8), 0.25 * p)  # 两岸漫来的雾带
        g.shade((128 - w, HORIZON + 14, 128, HORIZON + 24), 0.2 * p)

    def interrupt(self, g: Gfx, t: float, e: float):
        p = ease_in_out(span(t, 0, 1.4))
        self.night(g, t)
        self.water(g, t * (1 - p))
        self.lamps(g, e, t, lit=1 - 0.7 * p)
        self._mist(g, p)
        self.texts(g, e, left="雾锁江" if t > 0.9 else "地官赦罪")
        self.mx(g, t, lit=1 - p)

    def resume(self, g: Gfx, t: float, e: float):
        p = 1 - ease_in_out(span(t, 0, 1.4))
        self.night(g, t)
        self.water(g, t)
        self.lamps(g, e, t, lit=1 - 0.7 * p)
        self._mist(g, p)
        self.texts(g, e, left="雾锁江" if t < 0.5 else "地官赦罪")
        self.mx(g, t, lit=1 - p)

    def complete(self, g: Gfx, t: float, e: float):
        self.night(g, t)
        self.water(g, t)
        lamps = self.lamps(g, e, t, lit=1 - span(t, 0.8, 1.2))
        # 每盏灯的火光离灯升空，化作星点
        for s, i, (x, y, ss) in lamps:
            st = 0.8 + rand(i, 3) * 0.6
            q = span(t, st, st + 2.4)
            if q <= 0:
                continue
            tx = 20 + rand(i, 9) * 90
            ty = 2 + rand(i, 10) * 14
            xx = lerp(x, tx, ease_in_out(q)) + math.sin(q * 8 + i) * 3 * (1 - q)
            yy = lerp(y - 5 * ss, ty, ease_out(q))
            if q < 1:
                g.d.rectangle((xx - 1, yy - 1, xx, yy), fill=1)
                g.px(xx, yy + 2)
            elif blink(t + i * 0.3, 0.5, 0.7):
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    g.px(tx + dx, ty + dy)
        if t > 2.6:
            s = "中元普度"
            n = int(clamp((t - 2.6) * 4 / len(s)) * len(s))
            g.d.rectangle((0, 0, 15, 50), fill=0)
            g.vtext(2, 2, s[:n])
        else:
            self.texts(g, e, a=1 - span(t, 1.6, 2.4))
        self.mx(g, t, lit=1 - span(t, 0.8, 1.2))
        if t > 1.0:
            r = int((t - 1.0) * 4) % 8
            g.mx[:, :] = False
            for x in range(8):
                g.mx_set(x, 7 - ((r + x * 3) % 8))
            g.mx_level = 2
