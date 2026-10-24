"""太极化生：小道士静坐观想，太极一分为二，层层加一倍，长成伏羲六十四卦次序图。

依据：《系辞上》“易有太极，是生两仪，两仪生四象，四象生八卦”；邵雍《观物外篇》
“一分为二，二分为四，四分为八，八分为十六，十六分为三十二，三十二分为六十四”；
朱熹《周易本义》卷首“伏羲六十四卦次序图”（加一倍法，自左至右乾、夬、大有……坤）；
周敦颐《太极图说》“动极而静”“静极复动”；《系辞上》“生生之谓易”。

画面：左下小道士在蒲团上打坐，面前悬着一枚转动的太极；上方是次序图（最下一层一阳一阴，每层在上一层之上各生一奇一偶）。
入场：太极一圈画出、转起来，放一圈光；第一层从太极里生出（阳实 | 阴空），“易有太极”。
持续：一轮分六段（每段 100 秒）：段首小道士双手上举，一道气从太极升起，新的一层从左到右一块块弹出，右下写邵雍的句子；
      其余时间静坐（呼吸、偶尔睁眼），太极慢转、隔一阵放一圈光；一个小三角沿最上层从左扫到右。
      六十四卦长成后，扫到哪一卦，右下就画出那一卦、写它的全名（“山风蛊”），本场之卦那一列有闪烁记号。
      续：六层自上而下落回太极，太极急转、闪光，再一分为二。
中断：动极而静——太极停转，诸层暗下，小道士合目，“动极而静”。
恢复：静极复动——诸层亮回，太极复转，“静极复动”。
圆满：诸层自下而上逐层翻亮，本场之卦从它那一列升起、放大到中央，“生生之谓易”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import figure
from ..engine.gfx import Gfx, text_width
from ..engine.scene import Ritual, register
from ..engine.symbols import draw_hexagram, full_name, mx_hexagram, mx_taiji, taiji, yang
from .r5_util import Clock, label, pop_box, ring

PHRASE = ["一分为二", "二分为四", "四分为八", "八分为十六", "十六分为三十二", "三十二分为六十四"]
FLOOR = 63
DX = 16
TJ = (39, 47)             # 太极
TR = 7
L1 = 27                   # 第一层底边
LH, STEP = 3, 4           # 层高、层距
SEG = 100.0
RENEW = 5.0
GROW = 4.0                # 一层长出（秒）


def layer_bottom(k: int) -> int:
    return L1 - (k - 1) * STEP


def col_lines(col: int, n: int = 6):
    """第 col 列（0..63，乾在左）自下而上的 n 爻（True = 阳）"""
    return [not ((col >> (5 - i)) & 1) for i in range(n)]


def draw_layer(g: Gfx, k: int, prog: float = 1.0, t: float = 0.0, pop_from: float | None = None):
    """第 k 层（1..6）：2^k 块，阳实阴空；prog = 从左到右长出的比例（带弹出）"""
    n = 2 ** k
    w = 128 / n
    yb = layer_bottom(k)
    for j in range(n):
        q = (prog * n - j)
        if q <= 0:
            continue
        s = ease_out_back(min(q * 1.5, 1.0))
        h = max(1, round(LH * s))
        x0 = round(j * w)
        x1 = round((j + 1) * w) - 2 if w >= 4 else round(j * w)
        y0 = yb - h + 1
        is_yang = j % 2 == 0
        if is_yang:
            g.d.rectangle((x0, y0, x1, yb), fill=1)
        elif w >= 5:
            g.d.rectangle((x0, y0, x1, yb), outline=1)
            if w >= 12:
                g.d.line((x0 + 2, y0 + 1, x1 - 2, y0 + 1), fill=0)
        else:
            g.px(x0, y0), g.px(x0, yb)
            if w >= 4:
                g.px(x1, y0), g.px(x1, yb)


def ghost_layer(g: Gfx, k: int):
    """还没长出的层：一道疏点"""
    yb = layer_bottom(k) - 1
    for x in range(0, 128, 4):
        g.px(x, yb)


@register
class Liangyi(Clock, Ritual):
    id = "r5.liangyi"
    name = "太极化生"
    desc = "小道士静坐观想，面前太极一分为二，层层加一倍长成伏羲六十四卦次序图；扫到哪一卦，右下就画出那一卦"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 1.6, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.col = 0
        for i, v in enumerate(self.ctx.lines[:6]):
            if not yang(v):
                self.col |= 1 << (5 - i)
        self.sparks = pix.Sparks(self.seed + 1)

    # ------------------------------------------------------------ 状态（按 e）

    def stage(self, e: float):
        """→ (轮 c, 轮内 k, 已有层数 n, 正在长的层的进度 p（1 = 长完）, 本段秒数 tau)"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        seg = min(int(k // SEG), 5)
        tau = k - seg * SEG
        start = RENEW if (c >= 1 and seg == 0) else 0.0
        if c == 0 and seg == 0:
            return c, k, 1, 1.0, tau          # 第一层在入场时长好了
        p = span(tau, start + 1.0, start + 1.0 + GROW)
        return c, k, seg + 1, p, tau

    def scan(self, e: float, n: int, tau: float) -> float:
        """扫光位置 0..1（沿最上层）"""
        if n < 6:
            return (tau % 25) / 25
        return (tau % 96) / 96

    # ------------------------------------------------------------ 画

    def chart(self, g: Gfx, n: int, p: float, t: float, dim: float = 1.0):
        for k in range(1, 7):
            if k < n or (k == n and p >= 1):
                draw_layer(g, k, 1.0, t)
            elif k == n:
                draw_layer(g, k, p, t)
            else:
                ghost_layer(g, k)
        if dim < 1:
            g.fade(dim, (0, 0, 128, L1 + 1))

    def marker(self, g: Gfx, x: float, n: int, t: float):
        y = layer_bottom(n) - LH - 1
        g.d.polygon([(x - 2, y - 3), (x + 2, y - 3), (x, y - 1)], fill=1)

    def seat(self, g: Gfx, t: float, pose: str = "meditate", face: str | None = None):
        """蒲团 + 打坐（meditate 合目 / sit 睁眼 / up 双手上举）"""
        g.d.ellipse((DX - 12, FLOOR - 4, DX + 12, FLOOR), fill=1)
        g.d.line((DX - 10, FLOOR - 2, DX + 10, FLOOR - 2), fill=0)
        pix.checker(g, (DX - 9, FLOOR - 1, DX + 10, FLOOR), 0.5, 0)
        if pose == "up":
            return figure(g, DX, FLOOR - 3, t, legs="sit", arm="raise", face=face or "happy")
        return figure(g, DX, FLOOR - 3, t, legs="sit", arm="gong", face=face or ("sleep" if pose == "meditate" else "normal"))

    def taiji(self, g: Gfx, ang: float, r: float = TR, glow: float = 0.0):
        x, y = TJ
        y = y + math.sin(ang * 0.3) * 1.0
        g.d.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), fill=0)
        taiji(g, x, y, r, ang)
        if glow > 0:
            ring(g, x, y, r + 3 + glow * 12)

    def qi(self, g: Gfx, k: int, q: float, t: float):
        """一道气从太极升到第 k 层（波浪虚线，往上流）"""
        x0, y0 = TJ[0], TJ[1] - TR - 2
        y1 = layer_bottom(k) + 1
        for j in range(0, int((y0 - y1) * q), 2):
            y = y0 - j
            x = x0 + math.sin(j * 0.4 - t * 10) * 2
            g.px(x, y)

    def big_hex(self, g: Gfx, col: int, n: int = 6, x: int = 104, y: int = 37, mark: bool = False):
        lines = col_lines(col)
        g.d.rectangle((x - 3, y - 3, x + 22, y + 24), fill=0, outline=1)
        draw_hexagram(g, x, y, [7 if v else 8 for v in lines], w=20, h=2, step=4, count=n)
        if mark:
            g.d.rectangle((x - 3, y - 3, x + 22, y + 24), outline=1)
            g.px(x - 5, y + 10), g.px(x - 5, y + 12)

    def mx(self, g: Gfx, col: int, n: int, t: float):
        mx_hexagram(g, [7 if v else 8 for v in col_lines(col)], n)
        g.mx[7, :] = True

    # ------------------------------------------------------------ 主画面

    def scene(self, g: Gfx, t: float, e: float, dt: float):
        c, k, n, p, tau = self.stage(e)
        renew = c >= 1 and k < RENEW
        ang = t * 0.8
        if renew:                                      # 续：六层落回太极，再一分为二
            q = span(k, 0, 3.0)
            self.chart_fall(g, q, t)
            ang = t * 0.8 + ease_in_out(span(k, 0, 4)) * 20
            self.taiji(g, ang, TR, glow=span(k, 3.0, 4.0) if k < 4 else 0)
            if 3.0 <= k < 3.07:
                pix.flash(g)
            self.seat(g, t, "up" if k < 3.5 else "sit")
            return c, k, 0, 0.0, tau, renew
        self.chart(g, n, p, t)
        growing = 0 < p < 1 or (tau < 6.0 and not (c == 0 and k < SEG))
        glow = ((e % 17) / 1.0) if (e % 17) < 1.0 else 0
        self.taiji(g, ang, TR, glow)
        if growing:
            self.qi(g, n, span(tau, (RENEW if c >= 1 and n == 1 else 0) + 0.2, (RENEW if c >= 1 and n == 1 else 0) + 1.0), t)
            self.seat(g, t, "up")
        else:
            ph = e % 30
            self.seat(g, t, "sit" if 20 < ph < 23 else "meditate")
        sx = self.scan(e, n, tau) * 128
        if n < 6:
            self.marker(g, sx, n, t)
        else:
            col = min(int(sx / 2), 63)
            self.marker(g, col * 2 + 1, n, t)
            g.invert((col * 2, layer_bottom(6) - LH + 1, col * 2 + 1, L1 + 1))
            if (t * 3) % 1 < 0.6:                          # 本场之卦那一列
                x = self.col * 2
                g.d.line((x, L1 + 2, x + 1, L1 + 2), fill=1)
        return c, k, n, p, tau, renew

    def chart_fall(self, g: Gfx, q: float, t: float):
        """六层自上而下依次化开：每层淡去，化作几颗光点飞回太极"""
        for kk in range(6, 0, -1):
            a = (6 - kk) / 7
            f = span(q, a, a + 0.3)
            if f >= 1:
                continue
            draw_layer(g, kk, 1.0, t)
            if f > 0:
                yb = layer_bottom(kk)
                g.fade(1 - f, (0, yb - LH, 128, yb + 1))
                for j in range(5):
                    sx = 12 + j * 26
                    x = lerp(sx, TJ[0], ease_in(f))
                    y = lerp(yb - 1, TJ[1], ease_in(f))
                    g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)


    def caption(self, g: Gfx, n: int, p: float, tau: float, e: float, renew: bool):
        """右下：长层时写邵雍的句子；六十四卦长成后画出扫到的卦并写名"""
        if renew:
            return
        if n < 6 or (n == 6 and p < 1) or tau < 8:
            s = PHRASE[n - 1]
            size = 12 if len(s) <= 5 else 8
            w = text_width(s, size)
            x = 126 - w
            y = 50 if size == 12 else 53
            g.k.rectangle((x - 3, y - 3, 127, 63), fill=1)
            g.text(x, y, s, size=size)
            return
        col = min(int(self.scan(e, 6, tau) * 64), 63)
        self.big_hex(g, col, 6, 104, 36, mark=col == self.col and (e * 3) % 1 < 0.5)
        name = full_name([7 if v else 8 for v in col_lines(col)])
        g.text(98 - text_width(name), 44, name)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        x, y = TJ
        if t < 1.2:                                    # 无极：一圈画出
            g.d.arc((x - TR, y - TR, x + TR, y + TR), -90, -90 + 360 * span(t, 0, 1.2), fill=1)
        else:
            self.taiji(g, t * 2 - 2.4, TR * ease_out_back(span(t, 1.2, 1.6)), glow=span(t, 1.6, 2.4) if t < 2.4 else 0)
        for kk in range(2, 7):
            ghost_layer(g, kk) if t > 2.4 else None
        if t > 2.6:
            self.qi(g, 1, span(t, 2.6, 3.2), t)
            draw_layer(g, 1, span(t, 3.0, 4.2), t)
        self.seat(g, t, "up" if 2.4 < t < 4.4 else "meditate")
        if 1.6 <= t < 1.6 + dt:
            self.sparks.burst(x, y, 12, 26, life=0.5, gravity=0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 1.8:
            g.k.rectangle((70, 47, 127, 63), fill=1)
            g.text(126, 50, "易有太极", align="right")
        if t < 1.2:
            g.mx[7, :] = True
            g.mx[6, : int(8 * span(t, 0, 1.2))] = True
        else:
            mx_taiji(g, t * 2)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, n, p, tau, renew = self.scene(g, t, e, dt)
        self.caption(g, n, p, tau, e, renew)
        if renew:
            mx_taiji(g, t * 6)
            return
        col = min(int(self.scan(e, n, tau) * (2 ** n)), 2 ** n - 1) << (6 - n)
        self.mx(g, col, n if p >= 1 else max(n - 1, 0), t)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, n, p, tau, renew = self.stage(e) + (False,)
        n = max(n, 1)
        self.chart(g, n, max(p, 0.0), t, dim=1 - 0.75 * span(t, 0.2, 1.2))
        self.taiji(g, 0.8 * ease_out(span(t, 0, 1.0)) + t * 0.0, TR)
        self.seat(g, t, "meditate")
        label(g, 70, 50, "动极而静")
        mx_hexagram(g, [7] * 6, n)
        g.mx[7, :] = True

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, n, p, tau = self.stage(e)
        self.chart(g, n, p, t, dim=0.25 + 0.75 * span(t, 0.2, 1.2))
        self.taiji(g, ease_in(span(t, 0, 1.0)) * 0.8 + t * 0.8, TR, glow=span(t, 0.3, 1.0) if t < 1.0 else 0)
        self.seat(g, t, "up" if 0.3 < t < 1.2 else "meditate")
        label(g, 70, 50, "静极复动")
        mx_taiji(g, t * 3)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        flip = span(t, 0.2, 2.0) * 6                     # 自下而上逐层翻亮
        for kk in range(1, 7):
            draw_layer(g, kk, 1.0, t)
            if kk - 1 < flip < kk + 0.5:
                g.invert((0, layer_bottom(kk) - LH, 128, layer_bottom(kk) + 1))
        x = self.col * 2
        g.invert((x, layer_bottom(6) - LH + 1, x + 1, L1 + 1))
        self.taiji(g, t * 3, TR, glow=span(t, 2.0, 2.8) if 2.0 < t < 2.8 else 0)
        self.seat(g, t, "up" if t < 4.0 else "sit", face="happy")
        if t > 2.2:                                      # 本场之卦升起、放大到中央
            g.fade(1 - 0.85 * span(t, 2.2, 2.8), (0, 0, 128, L1 + 1))
            q = ease_out_back(span(t, 2.2, 3.0))
            cx = lerp(x, 88, q)
            cy = lerp(L1, 16, q)
            w = lerp(2, 22, q)
            lines = self.ctx.lines
            g.d.rectangle((cx - w / 2 - 3, cy - 3 - 12 * q, cx + w / 2 + 3, cy + 12 * q + 3), fill=0, outline=1)
            draw_hexagram(g, cx - w / 2, cy - 12 * q, lines, w=max(int(w), 2), h=2, step=max(1, int(4 * q)))
        if 2.2 <= t < 2.27:
            pix.flash(g)
        if t > 3.2:
            g.k.rectangle((0, 0, 128, 0), fill=1)
            s = "生生之谓易"
            yy = pop_box(g, 88, 40, s, t, 3.2, stars=False)
            g.text(88, yy, s, align="center")
        if t < 2.2:
            mx_hexagram(g, [7 if v else 8 for v in col_lines(self.col)], int(flip))
        else:
            mx_hexagram(g, self.ctx.lines, 6)
            g.mx_level = 1 + int(6 * (1 - span(t, 2.2, 3.5)))
        g.mx[7, :] = True
