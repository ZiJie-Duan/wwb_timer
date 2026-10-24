"""坐看云起：王维《终南别业》“行到水穷处，坐看云起时。偶然值林叟，谈笑无还期。”

入场：隐者拄杖从左边走上山石，坐下；山谷里第一朵云从山后冒出来（陶渊明“云无心以出岫”）。
持续：远山稀疏、近山浓、山脚隐在雾里；云一朵接一朵从山谷升起、长大、飘散；溪水流到石下就没了（水穷处）。
      小事件：倦鸟飞回远山（鸟倦飞而知还）；每隔几分钟一位林叟拄杖走来，坐下谈笑一阵再走。
退场：云海从山谷涌上来，把整幅画淹没。
"""
from __future__ import annotations

import math
import random

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x3_lib import Cloud, bird, ctext, every, halo, layer, peaks, poem_cols

SIT = Sprite("""
  ...##...
  ..####..
  ..####..
  ...##...
  ..####..
  .######.
  .######.
  ########
  ###.####
  ###.####
  ########
""")  # 背影：坐看
WALK = [Sprite("""
  ..##.
  .####
  .####
  ..##.
  .###.
  ####.
  #####
  .###.
  .###.
  .#.#.
  .#..#
  #...#
"""), Sprite("""
  ..##.
  .####
  .####
  ..##.
  .###.
  .###.
  .####
  .###.
  .###.
  ..#..
  ..##.
  ..#..
""")]
ELDER_WALK = [Sprite("""
  .###..
  #####.
  .##...
  .###..
  ####..
  #####.
  .###..
  .###..
  .#.#..
  #...#.
"""), Sprite("""
  .###..
  #####.
  .##...
  .###..
  ####..
  ####..
  .###..
  .###..
  ..#...
  .##...
""")]
ELDER_SIT = Sprite("""
  .###..
  #####.
  .##...
  .###..
  #####.
  ######
  ######
  .#####
""")

SIT, ELDER_SIT = halo(SIT), halo(ELDER_SIT)
WALK = [halo(s) for s in WALK]
ELDER_WALK = [halo(s) for s in ELDER_WALK]

ROCK = [(0, 47), (8, 44), (20, 43), (30, 45), (36, 49), (40, 54), (42, 60), (43, 64), (0, 64)]
SEAT = (24, 44)        # 隐者坐处（脚底）
STREAM = [(128, 55), (110, 56), (92, 58), (74, 59), (60, 60), (50, 61)]
POOL = (47, 61)        # 水穷处
CLOUD_P = 33.0         # 一朵云从生到散
N_CLOUD = 3
ELDER_P, ELDER_D = 240.0, 42.0


def rock_y(x: float) -> float:
    """山石顶面高度"""
    for (x0, y0), (x1, y1) in zip(ROCK, ROCK[1:]):
        if x0 <= x <= x1 and x1 > x0:
            return lerp(y0, y1, (x - x0) / (x1 - x0))
    return ROCK[0][1]


@register
class CloudRise(Rest):
    id = "x3.cloud"
    name = "坐看云起"
    desc = "隐者坐在溪水尽头的山石上，云从山谷里一朵朵升起、散开；倦鸟归山，林叟偶来谈笑"
    T = {"enter": 3.2, "exit": 1.3}

    def setup(self):
        r = self.rng
        s = self.seed
        self.far = layer(peaks(128, 44, [(14, 16, 26), (44, 7, 24), (78, 15, 26), (112, 9, 30)], s, 1.2), 0.22,
                         outline=2, fog=16, floor=0.0)
        self.mid = layer(peaks(128, 58, [(8, 30, 34), (38, 38, 20), (100, 24, 34), (128, 32, 18)], s + 3, 1.6),
                         0.5, outline=1, fog=18, floor=0.06, solid=True)
        self.clouds = [Cloud(random.Random(s * 11 + i), 22 + r.random() * 8, 10 + r.random() * 3) for i in range(N_CLOUD)]
        self.cx = [64 + r.uniform(-6, 6) for _ in range(N_CLOUD)]
        self.drift = [r.choice((-1, 1)) * r.uniform(6, 16) for _ in range(N_CLOUD)]

    # ------------------------------------------------------------ 零件

    def rock(self, g: Gfx):
        g.d.polygon(ROCK, fill=0, outline=1)
        for x0, y0, x1, y1 in ((5, 50, 9, 55), (14, 48, 12, 53), (30, 50, 34, 58), (20, 55, 24, 62),
                               (36, 56, 37, 61)):
            g.d.line((x0, y0, x1, y1), fill=1)       # 皴
        for x in range(2, 40, 3):                    # 石根暗处的苔点
            if rand(x, 3) < 0.5:
                g.px(x, 60 + rand(x, 4) * 3)

    def stream(self, g: Gfx, t: float):
        """溪水从右边山脚流来，越流越细，到石下的小潭就没了（水穷处）"""
        g.d.rectangle((44, 57, 127, 63), fill=0)
        up = [(x, y - 1.6 * (1 - i / 5)) for i, (x, y) in enumerate(STREAM)]
        lo = [(x, y + 2.2 * (1 - i / 5) + 0.5) for i, (x, y) in enumerate(STREAM)]
        g.d.line(up, fill=1)
        g.d.line(lo, fill=1)
        for j in range(5):  # 水纹短线往左流，到水穷处消失
            k = (t * 0.07 + j / 5) % 1.0
            idx = min(k * (len(STREAM) - 1), len(STREAM) - 1.001)
            i = int(idx)
            f = idx - i
            (x0, y0), (x1, y1) = STREAM[i], STREAM[i + 1]
            x, y = lerp(x0, x1, f), lerp(y0, y1, f)
            if k < 0.82:
                g.d.line((x, y, x - 3 + k * 2, y), fill=1)
        g.d.ellipse((POOL[0] - 4, POOL[1] - 1, POOL[0] + 3, POOL[1] + 1), outline=1, fill=0)

    def cloud_at(self, i: int, tc: float):
        """第 i 朵云在 tc 时的 (x, y, s, a)，没有就 None"""
        off = i * CLOUD_P / N_CLOUD
        k = math.floor((tc - off) / CLOUD_P)
        p = (tc - off) / CLOUD_P - k
        if k < 0 and tc < off - CLOUD_P:
            return None
        sd = self.seed * 7 + k
        x = self.cx[i] + (rand(k, sd) - 0.5) * 16 + self.drift[i] * ease_in_out(p) * (1 if k % 2 else -1)
        y = lerp(62, 6 + rand(k + 3, sd) * 6, ease_out(p * 1.05))
        s = lerp(0.35, 1.25, ease_out(p))
        a = clamp(p / 0.06) * (1 - span(p, 0.72, 1.0))
        return x, y, s, a, k

    def clouds_draw(self, g: Gfx, tc: float):
        order = []
        for i in range(N_CLOUD):
            c = self.cloud_at(i, tc)
            if c:
                order.append((c[2], i, c))
        for _, i, (x, y, s, a, k) in sorted(order):  # 小的（新的）在后面
            self.clouds[i].draw(g, x, y, s, a, seed=k * 13 + i, clear=a > 0.55)

    def scenery(self, g: Gfx, t: float, clouds: bool = True):
        g.blit(self.far, 0, 0)
        if clouds:
            self.clouds_draw(g, t)
        g.blit(self.mid, 0, 0)
        self.stream(g, t)
        self.rock(g)

    def hermit(self, g: Gfx, t: float):
        x, y = SEAT
        breathe = 1 if (t % 6.0) < 3.0 else 0          # 坐久了，肩头随呼吸微微起伏
        g.blit(SIT, x - 5, y - SIT.h + 2)
        if breathe:
            g.px(x - 1, y - SIT.h + 1)
            g.px(x, y - SIT.h + 1)
        g.d.line((x + 5, y - 13, x + 8, y), fill=1)       # 竹杖斜靠在身边

    def birds(self, g: Gfx, t: float):
        ev = every(t, 47.0, 10.0, 11.0)
        if ev:
            k, lt = ev
            p = lt / 10.0
            tx, ty = 30 + rand(k, 5) * 40, 12 + rand(k, 6) * 6
            x = lerp(130, tx, ease_out(p))
            y = lerp(8 + rand(k, 7) * 10, ty, p) + math.sin(lt * 2) * 2
            if p < 0.9:
                bird(g, x, y, lt, s=lerp(1.0, 0.5, p))
            if rand(k, 8) < 0.5 and p < 0.85:  # 有时是两只
                bird(g, x + 7, y + 3, lt + 0.4, s=lerp(0.9, 0.45, p))

    def elder(self, g: Gfx, t: float):
        """偶然值林叟，谈笑无还期"""
        ev = every(t, ELDER_P, ELDER_D, 95.0)
        if not ev:
            return
        k, lt = ev
        sx = 10  # 林叟坐处
        if lt < 7 or lt > ELDER_D - 7:
            back = lt > ELDER_D - 7
            q = (lt - (ELDER_D - 7)) / 7 if back else lt / 7
            x = lerp(sx, -10, q) if back else lerp(-10, sx, q)
            spr = ELDER_WALK[int(lt * 3) % 2]
            spr = spr.flip() if back else spr
            y = rock_y(max(x, 0))
            g.blit(spr, x - 4, y - spr.h + 2 + (int(lt * 3) % 2))
            sx_ = x + (-4 if back else 4)
            g.d.line((sx_, y - 9, sx_ + (-1 if back else 1), y), fill=1)  # 拄杖
            return
        y = rock_y(sx)
        talk = lt - 7
        laugh = int(talk / 2.6) % 5 == 4
        g.blit(ELDER_SIT, sx - 4, y - ELDER_SIT.h + 2 - (int(talk * 8) % 2 if laugh else 0))
        g.d.line((sx - 5, y - 10, sx - 6, y), fill=1)
        who = int(talk / 2.6) % 2
        if laugh:  # 大笑：两人头上都冒“哈”
            if int(talk * 3) % 2:
                g.d.rectangle((sx - 4, y - 21, sx + 5, y - 13), fill=0)
                g.d.rectangle((SEAT[0] - 3, SEAT[1] - 22, SEAT[0] + 6, SEAT[1] - 14), fill=0)
                ctext(g, sx - 3, y - 20, "哈", size=8)
                ctext(g, SEAT[0] - 2, SEAT[1] - 21, "哈", size=8)
        elif (talk % 2.6) < 2.0:  # 谈：两边轮流冒出“……”
            bx = sx - 1 if who == 0 else SEAT[0] - 2
            by = (y - ELDER_SIT.h - 4) if who == 0 else SEAT[1] - SIT.h - 4
            g.d.rectangle((bx - 1, by - 1, bx + 9, by + 2), fill=0)
            for d in range(int(span(talk % 2.6, 0, 0.9) * 3) + 1):
                g.d.rectangle((bx + d * 3, by, bx + d * 3 + 1, by + 1), fill=1)

    def poem(self, g: Gfx, t: float, k_in: float | None = None):
        if k_in is None:
            ev = every(t, 150.0, 26.0, 0.0)
            if not ev:
                return
            lt = ev[1]
            k = span(lt, 0, 2.0) * (1 - span(lt, 22, 26))
        else:
            k = k_in
        if k <= 0:
            return
        g.d.rectangle((99, 0, 127, 63), fill=0)
        poem_cols(g, 127, 2, ("行到水穷处", "坐看云起时"), k)

    def mx(self, g: Gfx, t: float):
        g.mx_rows([0, 0, 0, 0, 0, 0b00010000, 0b00111000, 0b11111110])
        g.mx[7, 7] = True
        g.mx[6, 7] = True
        for j in range(2):  # 小云团从山谷升起
            p = ((t / 5.0) + j * 0.5) % 1.0
            y = 6 - p * 7.5
            x = 3 + (1 if j else -1) * p * 1.5 + 1
            if y < 5:
                for dx, dy in ((0, 0), (1, 0), (1, -1), (2, 0)):
                    if not (p > 0.8 and (dx + dy + int(t * 6)) % 2):
                        g.mx_set(int(x + dx), int(y + dy))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        self.scenery(g, t - T)
        if t < 2.2:  # 行到水穷处：拄杖走来
            x = lerp(-6, SEAT[0], t / 2.2)
            spr = WALK[int(t * 5) % 2]
            y = rock_y(x)
            g.blit(spr, x - 3, y - spr.h + 2 + (int(t * 5) % 2))
            g.d.line((x + 4, y - 10, x + 5, y), fill=1)
        elif t < 2.6:  # 坐下
            sink = ease_out(span(t, 2.2, 2.6))
            g.blit(WALK[0], SEAT[0] - 3, SEAT[1] - WALK[0].h + 2 + sink * 2)
            g.d.line((SEAT[0] + 4, SEAT[1] - 10, SEAT[0] + 4 + sink * 4, SEAT[1]), fill=1)
        else:
            self.hermit(g, 0.0)
        self.poem(g, 0, k_in=span(t, 1.2, T - 0.2))
        self.mx(g, t)

    def hold(self, g: Gfx, t: float):
        self.scenery(g, t)
        self.birds(g, t)
        self.hermit(g, t)
        self.elder(g, t)
        self.poem(g, t, k_in=1.0 if t < 18 else (1 - span(t, 18, 21)) if t < 21 else None)
        self.mx(g, t)

    def exit(self, g: Gfx, t: float):
        """云海从山谷涌上来，淹没整幅画"""
        T = self.T["exit"]
        self.hold(g, self.hold_t + t)   # 接着持续阶段最后的样子
        p = ease_in(t / T) * 0.6 + ease_in_out(t / T) * 0.4
        front = lerp(66, -16, p)
        pts = [(x, front + math.sin(x * 0.13 + t * 3) * 3 + noise(x * 0.2, self.seed) * 4) for x in range(-4, 133, 3)]
        g.d.polygon(pts + [(132, 70), (-4, 70)], fill=0)
        g.d.line(pts, fill=1)
        for j in range(6):  # 云头卷纹
            x = 6 + j * 23 + noise(t, j) * 6
            y = front + 7 + (j % 2) * 6
            g.d.arc((x - 6, y - 4, x + 6, y + 4), 190, 350, fill=1)
        rows = int(round(8 - p * 9))  # 点阵也被云吞没（自下而上熄灭）
        if rows < 8:
            g.mx[max(rows, 0):, :] = False
