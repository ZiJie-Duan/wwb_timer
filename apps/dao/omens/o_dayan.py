"""大衍筮法（蓍草揲卦）。

《周易·系辞上》：“大衍之数五十，其用四十有九。分而为二以象两，挂一以象三，揲之以四以象四时，归奇于扐以象闰。”
三变成一爻：每变去 挂一 + 两把余数，三变后剩 36/32/28/24，除四得 9/8/7/6。十八变成卦（按真实算法，
分二用正态分布模拟手分）。

画面：小道士盘坐案前，案上五十根蓍草一根根立起；第一变逐步演示，顶上打出对应的系辞原句：
取一根化作灵光飞入卦牌（太极不用）→ 剑指一划，分成两把 → 右把取一根挂到手上 →
两把四根一组“啪啪”跳起消失 → 余数飞回手里（归奇），右上角记 49-5=44。
其余十七变快进：蓍草成批跳起消失，每三变成一爻，卦牌上长出一爻，弹出“九·老阳”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, lerp, rand, span
from ..engine.chars import figure
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import mx_hexagram
from .o_common import FLOOR, REVEAL, YAO_NAME, YAO_NUM, Base, floor, star4, tally

DAO_X = 13
X0, DX = 31, 2          # 第 i 根蓍草的 x（49 根）
TOP = 48                # 案面
SH = 14                 # 蓍草高
QUOTES = [(0.0, "大衍之数五十"), (0.65, "其用四十有九"), (1.15, "分而为二以象两"), (1.6, "挂一以象三"),
          (2.0, "揲之以四以象四时"), (3.15, "归奇于扐以象闰")]
DETAIL = 3.65           # 第一变演示结束
FAST = 0.1              # 快进时每变
R0 = DETAIL + 17 * FAST + 0.3


def change_done(c: int) -> float:
    return DETAIL - 0.15 if c == 0 else DETAIL + (c - 1) * FAST + 0.7 * FAST


def line_done(li: int) -> float:
    return change_done(li * 3 + 2)


def one_change(n: int, rng) -> tuple[int, int, int, int]:
    """一变：返回 (左把数, 左余, 右余, 变后数)"""
    left = int(round(rng.gauss(n / 2, n / 9)))
    left = max(2, min(n - 3, left))
    right = n - left - 1  # 挂一（取自右把）
    rl = left % 4 or 4
    rr = right % 4 or 4
    return left, rl, rr, n - 1 - rl - rr


def stalk(g: Gfx, x: float, y: float, i: int, h: int = SH):
    """一根蓍草：细茎，顶端略歪，中段一个节（暗点）"""
    x, y = int(round(x)), int(round(y))
    top = y - h + int(rand(i, 7) * 2)
    g.d.line((x, top, x, y - 1), fill=1)
    g.px(x, top + 4 + (i % 2) * 3, 0)


def table(g: Gfx):
    """几案：案面（阴线）、牙板云头、弯腿"""
    g.d.rectangle((27, TOP, 127, TOP + 2), fill=1)
    g.d.line((28, TOP + 1, 126, TOP + 1), fill=0)
    g.d.line((30, TOP + 4, 124, TOP + 4), fill=1)
    for x in range(36, 124, 12):
        g.d.arc((x - 3, TOP + 3, x + 3, TOP + 7), 0, 180, fill=1)
    for x, s in ((31, -1), (123, 1)):
        g.d.line((x, TOP + 3, x, FLOOR - 2), fill=1, width=2)
        g.d.line((x, FLOOR - 1, x + s * 2, FLOOR - 1), fill=1)
    pix.checker(g, (33, TOP + 8, 122, FLOOR), 0.125)


@register
class DayanOmen(Base):
    id = "o.dayan"
    name = "大衍筮"
    desc = "小道士盘坐案前揲蓍：五十取一，分二挂一，揲四归奇，系辞逐句打出；十八变快进成卦"
    T = {"play": R0 + REVEAL}

    def init(self):
        self.changes = []  # 18 个 (变前数, 左把, 左余, 右余, 变后数)
        self.lines = []
        for _ in range(6):
            n = 49
            for _ in range(3):
                left, rl, rr, m = one_change(n, self.rng)
                self.changes.append((n, left, rl, rr, m))
                n = m
            self.lines.append(n // 4)
        # 第一变后留在案上的蓍草（四根一组的那些）在收拢后的序号
        n0, left, rl, rr, n1 = self.changes[0]
        kept = [i for i in range(left - rl)] + [i for i in range(left + 1, left + 1 + (n0 - left - 1 - rr))]
        self.rank = {i: r for r, i in enumerate(kept)}

    def quote(self, t: float):
        t0, s = [q for q in QUOTES if t >= q[0]][-1]
        m = int(min(1.0, (t - t0) * 18 / len(s)) * len(s))
        if m:
            self.say(74, 2, s[:m], align="center")

    # ------------------------------------------------------------ 第一变（逐步）
    def detail(self, g: Gfx, t: float):
        n0, left, rl, rr, n1 = self.changes[0]
        right = n0 - left
        appear = span(t, 0.05, 0.6)
        split = ease_in_out(span(t, 1.2, 1.5))
        hang = ease_in_out(span(t, 1.65, 1.95))
        gl, gr = (left - rl) // 4, (right - 1 - rr) // 4
        n_groups = gl + gr
        g_t0, g_t1 = 2.05, 3.05
        per = (g_t1 - g_t0) / max(n_groups, 1)
        back = ease_in_out(span(t, 3.15, 3.5))
        hand = (DAO_X + 10, FLOOR - 15)
        # 太极：第 50 根化作灵光飞入卦牌
        if appear > 0 and t < 1.15:
            q = span(t, 0.65, 1.1)
            x, y = lerp(X0 - 2, 11, ease_in_out(q)), lerp(TOP, 14, ease_in_out(q)) - math.sin(q * math.pi) * 6
            if q < 1:
                stalk(g, x, y, 99)
                if q > 0:
                    star4(g, x, y - SH - 1, 1 + int(t * 12) % 2)
            if self.hit(t, 1.1):
                self.sparks.burst(11, 10, 10, 25, life=0.4, gravity=10)
        for i in range(49):
            if i / 49 > appear:
                break
            x = X0 + i * DX
            y = TOP
            is_left = i < left
            if not is_left:
                x += split * 4
            else:
                x -= split * 1
            if i == left:  # 挂一：右把第一根飞到手上
                if hang > 0:
                    if hang < 1:
                        x, y = lerp(x, hand[0], hang), lerp(TOP, hand[1], hang) - math.sin(hang * math.pi) * 8
                    else:
                        continue
            # 揲四：第 k 组在 g_t0 + k*per 跳起消失
            if is_left:
                k = i // 4 if i < gl * 4 else None
            else:
                j = i - left - 1
                k = gl + j // 4 if 0 <= j < gr * 4 else None
            if k is not None:  # 四根一组跳一下（数过），留在案上
                tk = g_t0 + k * per
                if tk <= t < tk + 0.16:
                    y -= math.sin(span(t, tk, tk + 0.16) * math.pi) * 6
                if self.hit(t, tk) and (i % 4 == 0 if is_left else (i - left - 1) % 4 == 0):
                    self.sparks.burst(x + 3, TOP - SH - 4, 3, 16, life=0.25, gravity=20)
                if t >= 3.5:  # 收拢成一把，接快进
                    rank = self.rank.get(i, 0)
                    x = lerp(x, X0 + rank * DX, ease_in_out(span(t, 3.5, DETAIL)))
            else:
                rem = not (i == left)
                if rem and back > 0 and t >= g_t1:  # 余数归奇：飞回手里
                    if back >= 1:
                        continue
                    x, y = lerp(x, hand[0], back), lerp(TOP, hand[1], back) - math.sin(back * math.pi) * 10
            stalk(g, x, y, i)
        held = (1 if hang >= 1 else 0) + ((rl + rr) if back >= 1 else 0)
        if self.hit(t, 3.5):
            self.sparks.burst(hand[0], hand[1] - 6, 8, 25, life=0.4, gravity=30)
        if t >= 3.3:
            s = f"{n0}-{n0 - n1}={n1}"
            self.say(124, 22, s[:int((t - 3.3) * 30)], size=8, align="right")
        # 小道士：手的动作
        if 1.1 < t < 1.5:
            figure(g, DAO_X, FLOOR, t, legs="sit", arm="point")
        elif 1.95 < t < 3.1:
            figure(g, DAO_X, FLOOR, t, legs="sit", arm="offer", face="normal")
        else:
            figure(g, DAO_X, FLOOR, t, legs="sit", arm="offer" if t > 0.6 else "gong",
                   face="happy" if t > 3.5 else "normal")
        if held:
            for k in range(min(held, 5)):
                g.d.line((hand[0] + k - 1, hand[1] - 9, hand[0] + k - 2, hand[1]), fill=1)

    # ------------------------------------------------------------ 快进
    def fast(self, g: Gfx, t: float):
        c = min(17, 1 + int((t - DETAIL) / FAST))
        q = span((t - DETAIL) % FAST, 0, FAST * 0.7) if c < 17 else 1.0
        n0, left, rl, rr, n1 = self.changes[c]
        if t >= R0 - 0.3:
            n0 = n1 = self.changes[17][4]
            q = 1
        shown = int(lerp(n0, n1, q))
        for i in range(shown):
            stalk(g, X0 + i * DX, TOP, i)
        for i in range(shown, n0):  # 本变去掉的那几根往上跳
            y = TOP - q * 4
            if q < 1:
                stalk(g, X0 + i * DX, y, i)
        if q < 0.2 and int(t * 30) % 2 == 0:
            self.sparks.burst(X0 + n1 * DX + 4, TOP - SH, 2, 20, life=0.25, gravity=20)
        self.say(124, 22, f"{n0}-{n0 - n1}={n1}", size=8, align="right")
        ph = int(t * 16) % 2
        figure(g, DAO_X, FLOOR + 0, t, legs="sit", arm="offer", dy=-ph)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        floor(g, "tile")
        table(g)
        if t < DETAIL:
            self.detail(g, t)
        elif t < R0:
            self.fast(g, t)
        else:
            k = t - R0
            figure(g, DAO_X, FLOOR, t, legs="sit", arm="gong", head="bow" if 0.5 < k < 1.1 else "up", face="happy")
        if t < R0:
            if t < DETAIL:
                self.quote(t)
            for li in range(6):  # 一爻成：弹出“九·老阳”
                tl = line_done(li)
                if tl <= t < min(tl + 0.3, R0 - 0.05):
                    v = self.lines[li]
                    self.pop(76, 3, f"{YAO_NUM[v]}·{YAO_NAME[v]}", t - tl)
        self.particles(g)
        if t < R0:
            dn = sum(1 for li in range(6) if line_done(li) <= t)
            gl = (t - line_done(dn - 1)) / 0.25 if dn else -1
            tally(g, self.lines, dn, y=0, glint=gl)
            mx_hexagram(g, self.lines, dn)
            # 底行：余数长度条（49 根 → 8 点）
            if t < DETAIL:
                n = 49 if t < 3.5 else self.changes[0][4]
            else:
                c = min(17, int((t - DETAIL) / FAST))
                n = self.changes[c][4]
            for x in range(int(n / 49 * 8 + 0.5)):
                g.mx[7, x] = True
        else:
            self.reveal(g, t, R0)
        self.flush(g)
