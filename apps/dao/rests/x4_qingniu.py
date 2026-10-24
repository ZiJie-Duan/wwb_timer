"""青牛西去：老子骑青牛慢慢西行，牛走走停停，人读他的五千言。

依据：刘向《列仙传·老子》“老子西游……而老子果乘青牛而过也”；《史记·老子韩非列传》“老子修道德……
      于是老子乃著书上下篇，言道德之意五千余言而去，莫知其所终”。画面只看一人一牛的动作细节（不画关楼与日出）。
入场：青牛驮着老子从右边慢慢走进来。
持续：青牛原地慢步（四腿交替、颠步），远山与地面向右缓缓后退，牛背挂的葫芦随步子一晃一晃；
      一只苍蝇绕着牛屁股飞，尾巴每隔几秒狠狠一甩，苍蝇吓开又飞回。
      每 41 秒：路边一丛草移到嘴下，青牛停步低头啃草（嚼、草变短），再抬头接着走（地面跟着停、走）；
      每 26 秒：老子展开一卷竹简读，垂目点头，左上逐字写出一句《道德经》（十句轮换），读完卷起；
      不时捋须；青牛不时低头“哞”一声。
收场：青牛加快脚步向西（左）走出画面。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, noise, pulse, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Bake, mx_sprite, sound_arcs

G = 57          # 地面
OX = 50         # 牛（局部原点）的屏幕 x：头在左
SPEED = 6.0     # 地面后退速度 px/s
STEP = 1.3      # 一步的秒数


def _ox_body() -> Sprite:
    """牛身 + 头（朝左，水牛样的弯角），不含腿和尾巴。宽 46，高 24，y=20 附近是腿根"""
    b = Bake(46, 24)
    body = [(13, 8), (17, 5), (22, 5), (27, 7), (35, 7), (40, 6), (43, 9), (44, 14), (42, 19), (36, 21), (28, 22),
            (20, 21), (15, 19), (12, 15)]
    b.poly(body, 0.0)
    b.shade_lines = None
    for y in range(9, 20, 2):                               # 青色：背上一层稀疏的灰
        for x in range(18 + (y // 2) % 2 * 2, 42, 4):
            if b.mask.getpixel((x, y)) and not b.on.getpixel((x, y)):
                b.point(x, y)
    b.line([(18, 9), (17, 14), (20, 20)])                   # 肩胛
    b.line([(39, 10), (37, 15), (39, 19)])                  # 胯
    head = [(14, 9), (9, 8), (5, 11), (2, 16), (1, 20), (2, 23), (6, 23), (9, 20), (12, 18), (14, 15)]
    b.poly(head, 0.0)
    b.line([(4, 18), (5, 22)])                              # 宽鼻口
    b.point(2, 19)                                          # 鼻孔
    b.line([(9, 9), (6, 7), (4, 4), (5, 1), (9, 0)], width=2)   # 近侧大弯角（向上向后弯成月牙）
    b.line([(9, 0), (11, 1)])
    b.line([(12, 9), (12, 6), (14, 3), (17, 2)])               # 远侧角
    b.poly([(12, 11), (17, 11), (18, 13), (13, 14)], 0.0)    # 耳
    b.ellipse((5, 11, 8, 14), 1.0)                          # 眼
    b.point(6, 12, 0)
    return b.sprite()


LAOZI = Sprite("""
  .......###.......
  ......#####......
  .....#.....#.....
  ....#.......#....
  ...#.........#...
  ...#.##...##.#...
  ...#.........#...
  ...#..#...#..#...
  ...#....#....#...
  ....#.#####.#....
  .....#######.....
  ...##.#####.##...
  ..#...#####...#..
  .#.....###.....#.
  .#.....###..#..#.
  #.#.....#....#..#
  #..###.....###..#
  #.#...#####...#.#
  #...............#
  #..#.........#..#
  #...............#
  ##..#.......#..##
  #################
""")


OX_BODY = _ox_body()
OX_HEAD = Sprite(on=OX_BODY.on[:, :12].copy(), mask=OX_BODY.mask[:, :12].copy())
MX_OX = """
#......#
##....##
.######.
.#.##.#.
.######.
..####..
..#..#..
...##...
"""
MX_SLIPS = """
........
########
#.#.#.#.
#.#.#.#.
#.#.#.#.
#.#.#.#.
########
........
"""
MX_GRAZE = """
........
#......#
##....##
.######.
.#.##.#.
.######.
..####..
#.#..#.#
"""
LINES = ["道可道，非常道", "上善若水", "致虚极，守静笃", "大音希声", "知足不辱", "道法自然", "柔弱胜刚强",
         "少私寡欲", "大巧若拙", "为而不争"]
GRAZE_P, GRAZE_A, GRAZE_B = 41.0, 2.0, 11.0     # 每 41 秒停下吃草：k∈[A, B] 停住
READ_P = 26.0


@register
class QingNiu(Rest):
    id = "x4.qingniu"
    name = "青牛西去"
    desc = "老子骑青牛慢慢西行：牛走走停停低头啃草、甩尾赶蝇、哞一声；老子展开竹简读《道德经》、捋须，牛背挂的葫芦一晃一晃"
    T = {"enter": 3.2, "exit": 1.3}

    def setup(self):
        self.moo_p = self.rng.choice((19.0, 23.0, 27.0))
        self.line0 = self.rng.randrange(len(LINES))
        self.lost_full = self._lost(GRAZE_P)

    # ------------------------------------------------------------ 走走停停

    def walk_w(self, k: float) -> float:
        """一个吃草周期里的行走速度系数（0 = 停住）"""
        return 1 - span(k, GRAZE_A - 1.0, GRAZE_A) + span(k, GRAZE_B, GRAZE_B + 1.0)

    def _lost(self, k: float) -> float:
        """0..k 里因停步少走的时间（数值积分）"""
        k = min(k, GRAZE_B + 1.0)
        if k <= GRAZE_A - 1.0:
            return 0.0
        n = 24
        h = k / n
        return sum((1 - self.walk_w((i + 0.5) * h)) * h for i in range(n))

    def offset(self, t: float) -> float:
        n, k = divmod(t, GRAZE_P)
        return SPEED * (t - n * self.lost_full - self._lost(k))

    def graze(self, t: float) -> float:
        """低头程度 0..1"""
        k = t % GRAZE_P
        return ease_in_out(span(k, GRAZE_A, GRAZE_A + 1.2)) * (1 - ease_in_out(span(k, GRAZE_B - 1.5, GRAZE_B - 0.3)))

    # ------------------------------------------------------------ 布景

    def mountains(self, g: Gfx, off: float):
        """远山：随 off 慢慢右移（视差 1/5）"""
        prev = None
        for x in range(0, 129, 2):
            u = (x - off * 0.2) / 26.0
            h = noise(u, self.seed + 3) * 12 + noise(u * 2.3, self.seed + 4) * 5
            y = 44 - h
            if prev is not None:
                g.d.line((x - 2, prev, x, y), fill=1)
            prev = y

    def ground(self, g: Gfx, off: float):
        g.d.line((0, G, 127, G), fill=1)
        for i in range(10):   # 草丛与石子，随 off 右移循环
            x = (rand(i, self.seed) * 160 + off) % 160 - 16
            y = G + 2 + int(rand(i + 30, self.seed) * 5)
            if i % 3 == 0:
                g.d.line((x, y, x + 2, y - 2), fill=1)
                g.d.line((x + 2, y, x + 3, y - 3), fill=1)
            else:
                g.d.line((x, y, x + 2 + i % 3, y), fill=1)

    def tuft(self, g: Gfx, t: float, off: float):
        """路边一丛草：随地面移到牛嘴下，被啃短，再移走"""
        n, k = divmod(t, GRAZE_P)
        stop_off = SPEED * ((n * GRAZE_P + GRAZE_A) - n * self.lost_full - self._lost(GRAZE_A))
        x = OX + 3 + (off - stop_off)
        if not -10 < x < 135:
            return
        eaten = span(k, GRAZE_A + 1.5, GRAZE_B - 2.0)
        h = 7 * (1 - 0.7 * eaten)
        for j, dx in enumerate((-3, -1, 1, 3)):
            sw = math.sin(t * 1.3 + j) * 0.8
            g.d.line((x + dx, G, x + dx * 1.6 + sw, G - h * (0.7 + 0.3 * (j % 2))), fill=1)

    # ------------------------------------------------------------ 牛与老子

    def ox(self, g: Gfx, x: float, t: float, walk: float = 1.0, moo: float = 0.0, stroke: float = 0.0,
           graze: float = 0.0, read: float = 0.0):
        """牛 + 老子。x = 牛头左端；walk 0 = 站定；graze 低头吃草；read 竹简展开程度"""
        x = round(x)
        ph = t / STEP * 2 * math.pi
        bob = round(math.sin(ph * 2) * 0.6 * walk)
        top = G - 32 + bob          # 牛身贴图顶端
        root = top + 19             # 腿根
        # 一只苍蝇绕着牛屁股飞；尾巴不时狠狠一甩，苍蝇吓开再飞回来
        sk = (t + 3) % 6.5
        swat = math.sin(span(sk, 0, 0.7) * math.pi)
        fa = t * 2.3
        fly_r = 6 + swat * 12
        fx_, fy_ = x + 46 + math.cos(fa) * fly_r, top + 6 + math.sin(fa * 1.7) * 4 - swat * 6
        g.px(fx_, fy_)
        g.px(fx_ + (1 if int(t * 14) % 2 else -1), fy_ - 1)
        # 尾巴：平时轻摆，甩蝇时扬起
        sw = math.sin(t * 2.1) * 2 + noise(t * 1.3, self.seed) * 2
        tx, ty = x + 43, top + 10
        if swat > 0.05:
            ex, ey = tx + 4 + swat * 8, ty + 11 - swat * 12
            g.d.line((tx, ty, tx + 3 + swat * 3, ty + 4 - swat * 3, ex, ey), fill=1)
            g.d.rectangle((ex - 1, ey - 1, ex + 1, ey + 1), fill=1)
        else:
            g.d.line((tx, ty, tx + 2, ty + 5, tx + 2 + sw, ty + 11), fill=1)
            g.d.rectangle((tx + 1 + sw, ty + 11, tx + 3 + sw, ty + 13), fill=1)
        g.blit(OX_BODY, x, top)
        dy = round(max(3 * moo, 8 * graze))
        if dy > 0:  # 低头（哞 / 吃草）：头往下沉
            g.d.rectangle((x, top, x + 11, top + 23), fill=0)
            g.blit(OX_HEAD, x - round(2 * graze), top + dy)
            hx = x - round(2 * graze)
            if moo > 0.6:  # 张嘴
                g.d.line((hx + 1, top + 21 + dy, hx + 4, top + 22 + dy), fill=0)
            if graze > 0.9 and int(t * 4) % 2:   # 嚼
                g.d.line((hx + 1, top + 21 + dy, hx + 5, top + 22 + dy), fill=0)
                g.d.line((hx + 2, top + 22 + dy, hx + 4, top + 23 + dy), fill=1)
        # 腿：前后两对交替摆动；近侧粗、远侧细
        for lx, phase, far in ((15, 0, 1), (37, math.pi, 1), (19, math.pi, 0), (34, 0, 0)):
            sw = math.sin(ph + phase) * 3 * walk
            lift = max(0.0, -math.cos(ph + phase)) * 2 * walk
            kx = x + lx + sw * 0.4
            fx, fy = x + lx + sw, G - lift
            if far:
                g.d.line((kx, root, fx, fy - 1), fill=1)
                g.d.line((fx, fy, fx + 1, fy), fill=1)
            else:
                g.d.polygon([(kx - 1, root - 2), (kx + 3, root - 2), (kx + 2, root + 6), (fx + 2, fy - 2), (fx + 1, fy - 1),
                             (fx, fy - 1), (fx - 1, fy - 2), (kx - 1, root + 6)], fill=0, outline=1)
                g.d.rectangle((fx - 1, fy - 1, fx + 2, fy), fill=1)   # 蹄
        # 牛背上挂的葫芦（随步子晃）
        ga = math.sin(ph + 0.6) * 0.5 * walk + math.sin(t * 1.1) * 0.08
        gx0, gy0 = x + 31, top + 8
        gx1, gy1 = gx0 + math.sin(ga) * 5, gy0 + math.cos(ga) * 5
        g.d.line((gx0, gy0, gx1, gy1), fill=1)
        g.d.ellipse((gx1 - 2, gy1, gx1 + 2, gy1 + 3), fill=1)
        g.d.ellipse((gx1 - 3, gy1 + 3, gx1 + 3, gy1 + 9), fill=0, outline=1)
        # 老子：坐在牛背中段，随牛颠；读经时低一点头
        nod = 1 if read > 0.9 and int(t / 1.7) % 2 else 0
        lx, ly = x + 17, top - 16
        g.blit(LAOZI, lx, ly)
        if nod:
            g.d.line((lx + 6, ly + 5, lx + 11, ly + 5), fill=1)   # 垂目
            g.d.line((lx + 7, ly + 7, lx + 10, ly + 7), fill=0)
        if stroke > 0 and read <= 0:  # 捋须：一只手沿胡须往下
            hy = ly + 11 + stroke * 7
            g.d.rectangle((lx + 10, hy, lx + 12, hy + 1), fill=1)
            g.d.line((lx + 13, hy, lx + 14, ly + 13), fill=1)
        if read > 0:   # 双手展开一卷竹简（向左拉开）
            w = round(4 + 14 * read)
            cx, cy = lx + 9, ly + 19
            x0, x1 = cx - w, cx + 3
            g.d.rectangle((x0, cy - 3, x1, cy + 3), fill=0, outline=1)
            for xx in range(x0 + 2, x1, 2):
                g.d.line((xx, cy - 2, xx, cy + 2), fill=1)
            g.d.rectangle((x0 - 2, cy - 4, x0, cy + 4), fill=1)     # 卷起的一头
            g.d.rectangle((x0 - 1, cy - 1, x0 + 1, cy + 1), fill=1)  # 左手
            g.d.rectangle((x1 - 1, cy - 1, x1 + 1, cy + 1), fill=1)  # 右手

    # ------------------------------------------------------------ 时间表

    def moo(self, t: float) -> float:
        k = t % self.moo_p
        if t < self.moo_p * 0.5 or self.graze(t) > 0:
            return 0.0
        return span(k, 0, 0.4) * (1 - span(k, 1.6, 2.0))

    def stroke(self, t: float) -> float:
        k = (t + 7) % 31
        return span(k, 0, 1.2) if k < 1.6 else 0.0

    def read(self, t: float):
        """竹简展开程度、这次读到第几句、句内时间"""
        if t < 5:
            return 0.0, 0, 0.0
        k = (t - 5) % READ_P
        n = int((t - 5) // READ_P)
        if k > 11:
            return 0.0, n, 0.0
        return ease_out(span(k, 0, 1.2)) * (1 - ease_in(span(k, 9.8, 11.0))), n, k - 1.4

    def mx(self, g: Gfx, t: float, moo: float, graze: float, read: float):
        if read > 0.5:
            mx_sprite(g, MX_SLIPS)
            col = int(t * 1.5) % 4
            for y in range(2, 6):
                g.mx[y, col * 2] = True
                g.mx[y, col * 2 + 1] = blink(t, 0.6)
            return
        if graze > 0.5:
            mx_sprite(g, MX_GRAZE)
            if int(t * 4) % 2:
                g.mx[7, 3] = g.mx[7, 4] = True
            return
        mx_sprite(g, MX_OX)
        if (t % 4.3) < 0.15:  # 眨眼
            g.mx[3, 2] = g.mx[3, 5] = True
        if moo > 0.6:
            g.mx[7, 2:6] = True
            g.mx[6, 2:6] = False

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float):
        off = self.offset(t)
        k = t % GRAZE_P
        walk = self.walk_w(k)
        gz = self.graze(t)
        m = self.moo(t)
        rd, n, rk = self.read(t)
        self.mountains(g, off)
        self.ground(g, off)
        self.tuft(g, t, off)
        self.ox(g, OX, t, walk, m, self.stroke(t), gz, rd)
        if m > 0.3:  # 哞——（先挖一块黑底，免得和远山线混在一起）
            q = (t % self.moo_p) / 2.0
            hx, hy = OX - 16, G - 22
            g.d.rectangle((hx - 1, hy - 1, hx + 12, hy + 11), fill=0)
            g.text(hx, hy, "哞")
            sound_arcs(g, OX - 1, G - 12, q, n=2, gap=3, right=False, spread=0.6)
        if rd > 0.8 and rk > 0:
            typewriter(g, 2, 0, LINES[(self.line0 + n) % len(LINES)], rk, cps=3)
        self.mx(g, t, m, gz, rd)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        p = ease_out(span(t, 0, T))
        x = lerp(132, OX, p)
        self.mountains(g, 0)
        self.ground(g, 0)
        self.ox(g, x, t - T, walk=1.0)
        mx_sprite(g, MX_OX, dx=round((1 - p) * 8))

    def hold(self, g: Gfx, t: float):
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        p = span(t, 0, T) ** 1.6
        off = self.offset(t0)
        self.mountains(g, off)
        self.ground(g, off)
        self.ox(g, lerp(OX, -60, p), t0 + t * 1.6, walk=1.0)
        mx_sprite(g, MX_OX, dx=-round(p * 8))
        g.fade(1 - span(t, T * 0.75, T))
