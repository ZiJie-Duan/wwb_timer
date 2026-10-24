"""读经：竹简从右往左展开，一枚一枚读下去；蠹鱼偷吃字，吃够三回化为“脉望”。

经文按竹简原貌不加标点，依次是《道德经》第一、六、八、十六、二十五章（节选）与《庄子·逍遥游》藐姑射神人一段。
彩蛋出自段成式《酉阳杂俎》：“蠹鱼三食神仙字，则化为此物，名曰脉望。夜以规映当天中星，星使立降，可求还丹。”

入场：左边的简卷从右往左滚过来，竹简一枚枚摊开。
持续：竹简缓缓向右移（读过的卷进右边的简卷，左边的卷继续放出新简），正读到的那个字反白，
      从上往下、从右往左一字一字读。两卷随之转动。
      每 50 秒一条蠹鱼从简下爬上来啃掉一个字（留下一个缺口）再爬走；每第三回它卷成一个发光的圆环——
      脉望，向上飘去，天上一颗星一闪。
退场：左卷滚回来，把竹简重新卷起。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import ring
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import win

TEXT = ("道可道非常道名可名非常名无名天地之始有名万物之母故常无欲以观其妙常有欲以观其徼此两者同出而异名同谓之玄玄之又玄众妙之门"
        "〇谷神不死是谓玄牝玄牝之门是谓天地根绵绵若存用之不勤"
        "〇上善若水水善利万物而不争处众人之所恶故几于道"
        "〇致虚极守静笃万物并作吾以观复夫物芸芸各复归其根归根曰静是谓复命"
        "〇人法地地法天天法道道法自然"
        "〇藐姑射之山有神人居焉肌肤若冰雪淖约若处子不食五谷吸风饮露乘云气御飞龙而游乎四海之外"
        "〇")
ROWS = 4
PITCH = 13
SEC = 4.0                 # 读一枚简的秒数
ROW_Y = [10, 22, 34, 46]
LROLL, RROLL = 9, 119     # 两卷的中心 x
READ_X = 64               # 读到的位置
EV_P = 50.0

WORM = Sprite("""
.#...#.
..#.#..
.#####.
#.#.#.#
.#####.
#.#.#.#
.#####.
#.#.#.#
..###..
..#.#..
.#.#.#.
#..#..#
""")
WORM_DN = WORM.flipv()


def roll(g: Gfx, cx: float, ang: float, r: float = 8.0):
    """简卷：竖着的一卷（俯视成椭圆端面 + 螺旋）"""
    g.d.rectangle((cx - r, 2, cx + r, 62), fill=0)
    g.d.line((cx - r, 2, cx - r, 62), fill=1)
    g.d.line((cx + r, 2, cx + r, 62), fill=1)
    for y in (6, 59):  # 编绳勒出的两道
        g.d.line((cx - r, y, cx + r, y), fill=1)
    for k in range(1, 4):  # 卷身上的竹简缝，随转动移动
        x = cx - r + ((k * 2 * r / 4 + ang * 6) % (2 * r))
        g.d.line((x, 8, x, 57), fill=1)
    g.d.ellipse((cx - r, 0, cx + r, 4), fill=0, outline=1)
    g.d.arc((cx - r + 3, 1, cx + r - 3, 3), 0, 360, fill=1)


def mx_slips(g: Gfx, s: float, row: int):
    """点阵：三根竖简向右滑，当前字的位置亮点下移"""
    off = int((s % 1) * 3)
    for c in range(8):
        if (c - off) % 3 == 0:
            g.mx[1:7, c] = True
    c = 4
    g.mx[:, 3] = False
    g.mx[:, 5] = False
    g.mx[1:7, c] = True
    g.mx_set(c, 1 + row * 2 if row < 3 else 7, False)
    g.mx[0, :] = True
    g.mx[7, :] = True


@register
class Slips(Rest):
    id = "x2.slips"
    name = "读经"
    desc = "竹简展开，一字一字读《道德经》《庄子》；蠹鱼啃字，三食神仙字化为脉望飘去"
    T = {"enter": 2.8, "exit": 1.3}

    def setup(self):
        self.ht = 0.0
        self.base = self.rng.choice([0, 15, 21, 27, 36])  # 从哪一章读起（简号）

    # ------------------------------------------------------------ 简

    def S(self, t: float) -> float:
        """已读过的简数（连续）"""
        return self.base + t / SEC

    def slip_x(self, i: int, S: float) -> float:
        """第 i 枚简的左边 x：S 增大时简向右移，正读的简在 READ_X"""
        return READ_X - 6 + (S - i) * PITCH

    def char(self, i: int, r: int) -> str:
        return TEXT[(i * ROWS + r) % len(TEXT)]

    def slips(self, g: Gfx, S: float, lo: float = LROLL + 8, hi: float = RROLL - 8, holes=(), read=True):
        i0 = int(S - (hi - READ_X + 6) / PITCH) - 1
        i1 = int(S + (READ_X - 6 - lo) / PITCH) + 2
        cur = int(math.floor(S))
        row = int((S - cur) * ROWS)
        for i in range(i0, i1 + 1):
            x = self.slip_x(i, S)
            if x + 12 < lo or x > hi:
                continue
            xr = round(x)
            g.d.line((xr, 2, xr + 11, 2), fill=1)
            g.d.line((xr, 62, xr + 11, 62), fill=1)
            for y in range(3, 62, 3):  # 竹简边（虚线，像竹纹）
                g.px(xr + 12, y)
            for r in range(ROWS):
                ch = self.char(i, r)
                if (i, r) in holes:
                    k = holes[(i, r)]
                    if k >= 1:
                        g.d.ellipse((xr + 3, ROW_Y[r] + 2, xr + 9, ROW_Y[r] + 8), outline=1)  # 啃出的缺口
                        continue
                if ch == "〇":  # 章末：一个圆点（简上的分章符）
                    g.d.ellipse((xr + 3, ROW_Y[r] + 3, xr + 8, ROW_Y[r] + 8), fill=1)
                    continue
                g.text(xr + 1, ROW_Y[r], ch)
                if (i, r) in holes:  # 正在被啃：一点点缺
                    k = holes[(i, r)]
                    for j in range(int(k * 14)):
                        g.d.rectangle((xr + 2 + rand(j, 3) * 8, ROW_Y[r] + rand(j, 4) * 9,
                                       xr + 4 + rand(j, 3) * 8, ROW_Y[r] + 2 + rand(j, 4) * 9), fill=0)
                if read and i == cur and r == row:
                    g.invert((xr, ROW_Y[r] - 1, xr + 12, ROW_Y[r] + 11))
        # 编绳：两道横贯
        for y in (6, 59):
            g.d.line((lo, y, hi, y), fill=1)
            g.d.line((lo, y + 1, hi, y + 1), fill=0)
        # 左右压一点阴影：卷边
        g.d.rectangle((0, 0, lo - 1, 63), fill=0)
        g.d.rectangle((hi + 1, 0, 127, 63), fill=0)
        return row

    # ------------------------------------------------------------ 蠹鱼

    def worm_event(self, t: float):
        """→ (k, n, 目标简, 目标行)；不在事件中 k 为 None"""
        k, n = win(t, EV_P, 11.0, offset=14.0)
        if n < 0:
            return None, n, 0, 0
        t0 = 14.0 + n * EV_P
        S0 = self.S(t0)
        i = int(S0) + 3  # 事件开始时左边第三枚简（够时间留在画面里）
        r = 1 + int(rand(n, self.seed) * 3)
        return k, n, i, r

    def holes(self, t: float):
        """被啃掉的字：{(简, 行): 进度}（最近两次事件）"""
        out = {}
        _, n, _, _ = self.worm_event(t)
        for m in range(max(0, n - 1), n + 1):
            t0 = 14.0 + m * EV_P
            if t < t0:
                continue
            S0 = self.S(t0)
            i = int(S0) + 3
            r = 1 + int(rand(m, self.seed) * 3)
            out[(i, r)] = clamp((t - t0 - 4.0) / 3.0)
        return out

    def worm(self, g: Gfx, t: float, S: float):
        k, n, i, r = self.worm_event(t)
        if k is None:
            return None
        x = self.slip_x(i, S) + 4
        ty = ROW_Y[r] + 11
        mai = n % 3 == 2  # 第三回：化为脉望

        def bug(spr, bx, by):
            g.d.rectangle((bx - 1, by - 1, bx + spr.w, by + spr.h), fill=0)
            g.blit(spr, bx, by)

        if k < 4.0:  # 从简下爬上来
            y = lerp(66, ty, ease_out(k / 4.0))
            wig = int(k * 6) % 2
            bug(WORM, x + wig - 1, y)
            return "crawl"
        if k < 7.0:  # 啃
            y = ty - 1 + (1 if int(k * 8) % 2 else 0)
            bug(WORM, x - 1, y)
            for j in range(3):  # 碎屑
                g.px(x + rand(int(k * 5) + j, 9) * 6 - 1, y + 4 + rand(int(k * 5) + j, 8) * 4)
            return "eat"
        p = (k - 7.0) / 4.0
        if not mai:  # 吃饱了，慢慢爬走
            bug(WORM_DN, x - 1, lerp(ty, 66, ease_in(p)))
            return "crawl"
        # 脉望：卷成发光的圆环，向上飘去，天中一星一闪
        cy = lerp(ty + 2, -10, ease_in(span(p, 0.3, 1.0)))
        rr = lerp(2, 6, ease_out(span(p, 0, 0.3)))
        g.d.ellipse((x + 1 - rr - 1, cy - rr - 1, x + 1 + rr + 1, cy + rr + 1), fill=0)
        g.d.ellipse((x + 1 - rr, cy - rr, x + 1 + rr, cy + rr), outline=1)
        ring(g, x + 1, cy, rr + 3 + math.sin(t * 9), density=3, phase=t * 3)
        if p > 0.15:
            g.d.rectangle((x + 10, cy - 7, x + 34, cy + 6), fill=0)
            g.text(x + 11, cy - 6, "脉望")
        if p > 0.75:  # 星使立降
            sx, sy = x + 30, 4
            ln = 3 + 3 * math.sin((p - 0.75) * 12)
            g.d.line((sx - ln, sy, sx + ln, sy), fill=1)
            g.d.line((sx, sy - ln, sx, sy + ln), fill=1)
        return "mai"

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, lo: float = LROLL + 8, read: bool = True):
        S = self.S(t)
        row = self.slips(g, S, lo=lo, holes=self.holes(t), read=read)
        roll(g, lo - 8, -S)
        roll(g, RROLL, -S)
        st = self.worm(g, t, S)
        mx_slips(g, S, row)
        if st == "mai":
            g.mx[:] = False
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - 2.6) < 0.7:
                        g.mx[y, x] = True
            g.mx_level = 3 if blink(t, 0.4) else 1
        elif st:
            g.mx_set(int(t * 3) % 8, 7, False)

    def enter(self, g: Gfx, t: float):
        p = ease_in_out(span(t, 0.0, 2.2))
        lo = lerp(RROLL - 8, LROLL + 8, p)
        self.frame(g, 0.0, lo=lo, read=t > 2.4)
        if t < 2.2:
            g.mx[:] = False
            n = int(p * 8)
            for c in range(8 - n, 8):
                if c % 2 == 0:
                    g.mx[1:7, c] = True

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        p = ease_in_out(span(t, 0.0, self.T["exit"]))
        lo = lerp(LROLL + 8, RROLL - 8, p)
        self.frame(g, self.ht + t, lo=lo, read=False)
        if p > 0.95:
            g.d.rectangle((0, 0, 127, 63), fill=0)
            roll(g, RROLL, 0)
        g.mx[:] = False
        for c in range(int(p * 8), 8):
            if c % 2 == 0:
                g.mx[1:7, c] = True
