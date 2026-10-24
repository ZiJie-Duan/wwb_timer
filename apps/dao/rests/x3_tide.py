"""观潮：钱塘江潮。苏轼《催试官考较戏作》“八月十八潮，壮观天下无”；潘阆《酒泉子》“弄潮儿向涛头立，手把红旗旗不湿”。

视角：站在江边鱼鳞石塘上，隔江远望。左边月轮山上一座六和塔，对岸远山一抹。
入场：石塘从下面升上来，看潮的人一个个探出头。
持续：平时江面平静，细浪由远及近一行行漂动。约每 75 秒来一次潮：
      先是天边一道白线（一线潮），斜斜横过江面，越来越近、越来越高，潮头卷着白沫从右往左推过去；
      潮头扫到石塘，浪花溅过塘顶，近处的人往后一缩；潮过之后江面翻涌，慢慢才平下去，水位涨了一截。
      每次潮的大小不同；有时潮头上站着一个弄潮儿，手里的旗子在风里翻（“手把红旗旗不湿”）；
      天上偶尔掠过江鸥；题句（八月十八潮 / 壮观天下无 / 弄潮儿向涛头立）在天上浮现。
退场：最后一道大潮从右边漫过整幅画面，只剩白沫退去。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, smoothstep, span
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x3_lib import bird, every, layer, peaks, poly_sprite, ptext

FAR = 24             # 对岸 / 天水线
DIKE = 52            # 石塘顶
P = 75.0             # 潮的周期
ARRIVE = 16.0        # 一轮里第几秒天边出现潮线
CROSS = 26.0         # 潮头从右到左扫过画面用的秒数
HILL = [(0, FAR), (0, 13), (8, 11), (16, 9), (26, 12), (36, 18), (46, 22), (52, FAR)]
PAGODA = (17, 10)    # 塔基


@register
class WatchTide(Rest):
    id = "x3.tide"
    name = "观潮"
    desc = "站在钱塘江石塘上看潮：一线潮从天边斜推过来，潮头卷沫扫过、浪花溅上塘顶；有时潮头立着弄潮儿"
    T = {"enter": 2.8, "exit": 1.3}

    def setup(self):
        s = self.seed
        self.far = layer(peaks(128, FAR, [(78, 17, 20), (104, 15, 22), (128, 18, 16)], s, 0.8), 0.18, outline=2,
                         fog=5, floor=0.0)
        self.hill = poly_sprite([HILL], 0.35, fog_y=10, fog=14, floor=0.05)
        r = self.rng
        self.crowd = []
        x = 3.0
        while x < 124:  # 看潮的人：头、肩，有的打伞、有的骑在大人肩上
            kind = r.random()
            self.crowd.append((x, 0 if kind < 0.75 else 1 if kind < 0.88 else 2))
            x += r.uniform(5.5, 9.5)

    # ------------------------------------------------------------ 潮

    def tide(self, t: float):
        """返回 (第几潮, 潮头近端 x, 潮高, 是否有弄潮儿, 潮过后的时间)"""
        k = math.floor(t / P)
        lt = t - k * P
        H = 8 + 7 * rand(k, self.seed)
        surfer = rand(k, self.seed + 3) < 0.35
        s = (lt - ARRIVE) / CROSS
        X = lerp(170, -60, s) if s > 0 else 999
        return k, X, H, surfer, lt - ARRIVE

    def front(self, u: float, X: float) -> tuple[float, float]:
        """潮头线上的点：u=0 近端（石塘），u=1 远端（天水线）"""
        return X + 46 * u, DIKE - 1 - (DIKE - 1 - FAR) * u

    def wave(self, g: Gfx, t: float, X: float, H: float, surfer: bool):
        if X > 200 or X < -80:
            return
        top, base = [], []
        for i in range(13):
            u = i / 12
            x, y = self.front(u, X)
            h = H * (1 - u) ** 1.3 + 0.8
            top.append((x + 2 * (1 - u), y - h))
            base.append((x + 6 + 8 * (1 - u), y))
        g.d.polygon(top + base[::-1], fill=0)
        # 潮头：一道白练（2 像素粗的亮浪脊）+ 上面飞起的白沫
        g.d.line(top, fill=1, width=2)
        for i in range(12):
            (x0, y0), (x1, y1) = top[i], top[i + 1]
            for j in range(3):
                q = (j + 0.5) / 3
                if noise(t * 6 + i * 3.1 + j, 7) > 0.35:
                    g.px(lerp(x0, x1, q) + (noise(t * 4 + i + j, 2) - 0.5) * 3,
                         lerp(y0, y1, q) - 2 - rand(i * 3 + j + int(t * 8), 1) * 2 * (1 - i / 12))
        # 浪的正面：一道道往下泻的水纹（近处密、远处疏）
        for i in range(0, 12):
            if i > 6 and i % 2:
                continue
            (tx, ty), (bx, by) = top[i], base[i]
            sh = (t * 3 + i * 0.7) % 1.0
            g.d.line((tx + 1 + sh, ty + 2, lerp(tx, bx, 0.6) + sh, by - 1), fill=1)
        # 近端卷浪（翻下来的浪舌）
        nx, ny = top[0]
        g.d.arc((nx - 3, ny - 2, nx + 5, ny + 6), 180, 300, fill=1)
        if surfer:
            self.surfer(g, t, X, H)

    def surfer(self, g: Gfx, t: float, X: float, H: float):
        """弄潮儿：立在潮头上，手举旗子，旗在风里翻"""
        x, y = self.front(0.32, X)
        h = H * (0.68 ** 1.3) + 0.8
        x, y = x + 2, y - h - 1
        g.d.rectangle((x - 1, y - 6, x + 1, y - 2), fill=1)  # 身
        g.d.rectangle((x - 1, y - 8, x, y - 7), fill=1)      # 头
        g.px(x - 1, y - 1)
        g.px(x + 1, y - 1)
        g.d.line((x + 1, y - 5, x + 3, y - 12), fill=1)    # 旗杆
        f = int(t * 6) % 2
        g.d.polygon([(x + 3, y - 12), (x + 9, y - 11 + f), (x + 3, y - 8)], fill=1)

    def chop(self, g: Gfx, t: float, X: float, since: float, H: float):
        """江面：平时细浪；潮头身后翻涌（离潮头越远、过去越久越平）"""
        for j in range(9):
            y = FAR + 3 + j * (j + 2) * 0.33
            if y >= DIKE - 1:
                break
            n = 4 + j
            for i in range(n):
                x = (rand(i + j * 20, 4) * 140 + t * (1 + j * 0.4)) % 140 - 6
                ln = 1 + j * 0.6
                # 这一点在潮头的哪一侧
                u = clamp((DIKE - 1 - y) / (DIKE - 1 - FAR))
                fx = X + 46 * u
                rough = 0.0
                if x > fx:
                    dist = x - fx
                    rough = H / 10 * math.exp(-dist / 70) + 0.25 * clamp(1 - (since - 30) / 25) * (since > 0)
                if rough > 0.15:
                    yy = y - abs(math.sin(t * 3 + i + j)) * rough * 2
                    g.d.line((x, yy, x + ln + rough * 3, yy), fill=1)
                    if rough > 0.5 and (i + int(t * 4)) % 3 == 0:
                        g.px(x + 1, yy - 1)
                elif (i + j) % 3 == 0:
                    g.d.line((x, y, x + ln, y), fill=1)

    def spray(self, g: Gfx, t: float, X: float, H: float):
        """潮头扫过石塘：浪花溅过塘顶"""
        if not -10 < X < 140:
            return
        n = int(6 + H * 1.5)
        for j in range(n):
            ph = (t * 1.6 + rand(j, 3)) % 1.0
            x0 = X + 2 + rand(j, 4) * 12
            vx = -6 - rand(j, 5) * 14
            vy = -14 - rand(j, 6) * H * 2.2
            tt = ph * 1.1
            x = x0 + vx * tt
            y = DIKE - 1 + vy * tt + 0.5 * 40 * tt * tt
            if y < DIKE + 2:
                g.px(x, y)

    # ------------------------------------------------------------ 岸

    def pagoda(self, g: Gfx):
        """六和塔：七层（外看十三层檐，这里画七层）"""
        x, y = PAGODA
        for i in range(7):
            w = 6 - i * 0.6
            yb = y - i * 3
            g.d.rectangle((x - w + 1, yb - 2, x + w - 1, yb), fill=0, outline=1)
            g.d.line((x - w - 1, yb - 2, x + w + 1, yb - 2), fill=1)   # 檐
            g.px(x - w - 1, yb - 3)
            g.px(x + w + 1, yb - 3)
        g.d.line((x, y - 21, x, y - 24), fill=1)  # 塔刹

    def dike(self, g: Gfx, t: float, X: float, H: float, dy: float = 0.0, heads: float = 1.0):
        y0 = DIKE + dy
        g.d.rectangle((0, y0, 127, y0 + 12), fill=0)
        g.d.line((0, y0, 127, y0), fill=1)
        for row in range(3):  # 鱼鳞石塘：错缝条石
            yy = y0 + 3 + row * 4
            g.d.line((0, yy, 127, yy), fill=1)
            for x in range(-(row % 2) * 6, 128, 12):
                g.d.line((x, yy - 3, x, yy), fill=1)
        for i, (x, kind) in enumerate(self.crowd):  # 看潮的人
            pop = ease_out_back(clamp(heads * 1.6 - i * 0.04))
            if pop <= 0:
                continue
            duck = 2 if (X - 4 < x < X + 14 and H > 7) else 0     # 浪花溅过来，往后一缩
            stretch = 1 if (0 < X - x < 40) else 0                 # 潮快到了，伸长脖子
            hy = y0 - 4 + (1 - pop) * 6 + duck - stretch
            g.d.rectangle((x - 2, y0 - 1, x + 2, y0 - 1), fill=1)   # 肩
            g.d.rectangle((x - 1, hy, x + 1, hy + 2), fill=1)       # 头
            if kind == 1:   # 伞
                g.d.chord((x - 5, hy - 5, x + 5, hy + 1), 180, 360, fill=0, outline=1)
                g.d.line((x, hy - 2, x, hy), fill=1)
            elif kind == 2:  # 骑在肩上的小孩
                g.d.rectangle((x - 1, hy - 3, x, hy - 2), fill=1)
                if 0 < X - x < 40 and int(t * 3) % 2:
                    g.px(x + 2, hy - 4)                                # 招手

    def gulls(self, g: Gfx, t: float):
        ev = every(t, 41.0, 8.0, 9.0)
        if ev:
            k, lt = ev
            x = lerp(-8, 136, lt / 8.0)
            y = 8 + rand(k, 3) * 8 + math.sin(lt * 1.3) * 2
            bird(g, x, y, lt, s=1.0, flap=5)

    def caption(self, g: Gfx, t: float, k: int, surfer: bool, since: float):
        lines = ["八月十八潮", "壮观天下无"]
        s = "弄潮儿向涛头立" if surfer else lines[k % 2]
        a = span(since, 4, 6) * (1 - span(since, 22, 25)) if since > 0 else 0.0
        if k == 0 and t < 14:
            s, a = lines[0], 1 - span(t, 11, 14)
        n = int(round(a * len(s)))
        if n:
            from ..engine.gfx import text_width
            x = 126 - text_width(s)
            g.d.rectangle((x - 2, 0, 127, 13), fill=0)
            ptext(g, x, 1, s, n)

    def mx(self, g: Gfx, t: float, X: float, H: float):
        g.mx[7, :] = True
        for x in range(8):  # 平时：细浪
            if noise(t * 1.5 + x * 0.8, 3) > 0.55:
                g.mx_set(x, 6)
        if -60 < X < 170:  # 潮头从右往左推过点阵
            cx = (X + 20) / 128 * 8
            h = int(2 + H / 3)
            for x in range(8):
                d = x - cx
                if -0.5 < d < 1.5:
                    for y in range(7 - h, 7):
                        g.mx_set(x, y)
                elif 1.5 <= d < 4:
                    g.mx_set(x, 6 - int(abs(math.sin(t * 4 + x)) * 2))
            if 0 <= cx < 8:
                g.mx_set(int(cx), 6 - h)
                g.mx_set(int(cx) - 1, 6 - h + int(t * 6) % 2)

    # ------------------------------------------------------------ 阶段

    def picture(self, g: Gfx, t: float, dy: float = 0.0, heads: float = 1.0):
        k, X, H, surfer, since = self.tide(t)
        g.blit(self.far, 0, 0)
        g.blit(self.hill, 0, 0)
        self.pagoda(g)
        g.d.line((0, FAR, 127, FAR), fill=1)
        self.gulls(g, t)
        self.chop(g, t, X, since, H)
        self.wave(g, t, X, H, surfer)
        self.dike(g, t, X, H, dy, heads)
        self.spray(g, t, X, H)
        return k, X, H, surfer, since

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        dy = (1 - ease_out(span(t, 0, 1.0))) * 14
        k, X, H, surfer, since = self.picture(g, t - T, dy=dy, heads=span(t, 0.9, T))
        n = int(round(span(t, 1.4, T) * 5))
        if n:
            from ..engine.gfx import text_width
            x = 126 - text_width("八月十八潮")
            g.d.rectangle((x - 2, 0, 127, 13), fill=0)
            ptext(g, x, 1, "八月十八潮", n)
        self.mx(g, t, X, H)

    def hold(self, g: Gfx, t: float):
        k, X, H, surfer, since = self.picture(g, t)
        self.caption(g, t, k, surfer, since)
        self.mx(g, t, X, H)

    def exit(self, g: Gfx, t: float):
        """最后一道大潮从右边漫过整幅画面"""
        T = self.T["exit"]
        tt = self.hold_t + t
        self.picture(g, tt)
        p = ease_in(t / T)
        X = lerp(130, -70, p)
        H = 30
        pts = [(X + 46 * (i / 12) + math.sin(i + t * 8) * 2, (DIKE + 12) - (DIKE + 12) * (i / 12)) for i in range(13)]
        g.d.polygon(pts + [(200, 0), (200, 70)], fill=0)
        g.d.line(pts, fill=1, width=3)
        for i in range(0, 12):  # 潮头卷下来的水纹
            x, y = pts[i]
            g.d.line((x + 3, y - 1, x + 8, y + 3), fill=1)
        for j in range(30):  # 白沫
            x = pts[0][0] + rand(j, 1) * 50 + (noise(t * 5 + j, 2) - 0.5) * 6
            y = rand(j, 2) * 64
            if x > X + 46 * (1 - y / 64) and rand(j + int(t * 10), 3) < 1 - p:
                g.px(x, y)
        self.mx(g, tt, X, H / 3)
        cols = int(round(p * 8))
        if cols:
            g.mx[:, 8 - cols:] = False
