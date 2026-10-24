"""太极化生：伏羲六十四卦次序图（加一倍法）。

依据：《系辞上》“易有太极，是生两仪，两仪生四象，四象生八卦”；邵雍《观物外篇》
“一分为二，二分为四，四分为八，八分为十六，十六分为三十二，三十二分为六十四”。
朱熹《周易本义》卷首的“伏羲六十四卦次序图”：最下一层一阳一阴，每层在上一层之上各生一奇一偶，
六层而成六十四卦，自左至右为乾、夬、大有……至坤。周敦颐《太极图说》“动极而静”“静极复动”。

入场：无极一圈画出，化为旋转的太极，太极一分为二：第一层（阳 | 阴）从中间长出。
持续：一轮 10 分钟，每六分之一轮长出一层（块从下一层“生”出来），一道光沿最上层从左扫到右；
      点阵显示被扫到那一列的卦画。六十四卦长成后，扫到哪一卦，上方就写哪一卦的卦名，
      本场法事的卦那一列上方有记号，扫到时一闪。一轮满：六层自上而下落回太极，再一分为二。
中断：动极而静：扫光停住，诸层淡下去。
恢复：静极复动：诸层亮回，扫光继续。
圆满：从下往上逐层翻亮，本场之卦从它那一列升起、放大到中央，“生生之谓易”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_out, ease_out_back, lerp, span
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import full_name, mx_hexagram, mx_taiji, taiji, yang

PHRASE = ["一分为二", "二分为四", "四分为八", "八分为十六", "十六分为三十二", "三十二分为六十四"]
TOP = 50          # 第一层底边
LH = 5            # 层高
STEP = 6          # 层距
TJ = (64, 57)     # 太极
GROW = 3.0        # 一层长出（秒，按 e）
RENEW = 5.0


def layer_y(k: int) -> int:
    """第 k 层（1..6）的底边 y"""
    return TOP - (k - 1) * STEP


def block_yang(j: int) -> bool:
    return j % 2 == 0


def draw_block(g: Gfx, x0: float, y1: float, w: float, h: float, is_yang: bool):
    """一块：阳实，阴空（太窄时阴只留上下两点）"""
    if h <= 0:
        return
    x1 = x0 + w - 2
    y0 = y1 - h + 1
    if w >= 4:
        if is_yang:
            g.d.rectangle((x0, y0, x1, y1), fill=1)
        else:
            g.d.rectangle((x0, y0, x1, y1), outline=1)
    else:
        if is_yang:
            g.d.line((x0, y0, x0, y1), fill=1)
        else:
            g.px(x0, y0)
            g.px(x0, y1)


@register
class Liangyi(Ritual):
    id = "r5.liangyi"
    name = "太极化生"
    desc = "伏羲六十四卦次序图：太极一分为二，层层加一倍长到六十四卦，扫光逐卦报名"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.5, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.col = 0
        for i, v in enumerate(self.ctx.lines[:6]):
            if not yang(v):
                self.col |= 1 << (5 - i)

    # ------------------------------------------------------------ 状态

    def stage(self, e: float):
        """→ (层数 1..6, 本层进度 0..1, 本层已过秒数)"""
        k = e % self.CYCLE
        seg = self.CYCLE / 6
        s = min(int(k // seg), 5)
        return s + 1, (k - s * seg) / seg, k - s * seg

    def col_lines(self, j: int, k: int) -> list[int]:
        """第 k 层第 j 块所在列的爻（自下而上，7/8）"""
        return [7 if ((j >> (k - i)) & 1) == 0 else 8 for i in range(1, k + 1)]

    # ------------------------------------------------------------ 画面

    def layers(self, g: Gfx, n: int, grow: float = 1.0, drop: float = 0.0, scan: int | None = None,
               dim: float = 1.0):
        """画 n 层；最上一层按 grow 长出；drop：落回太极（0..1）"""
        for k in range(1, n + 1):
            nb = 1 << k
            w = 128 / nb
            y1 = layer_y(k)
            if drop > 0:  # 自上而下依次落下
                order = (6 - k) / 6
                q = ease_in(clamp((drop - order * 0.5) / 0.5))
                y1 = lerp(y1, TJ[1] + 20, q)
            for j in range(nb):
                h = LH
                if k == n and grow < 1:
                    q = clamp(grow * 1.6 - (j / nb) * 0.6)
                    h = int(round(LH * ease_out_back(q)))
                    h = max(0, min(h, LH + 1))
                draw_block(g, j * w, y1, w, h, block_yang(j))
            if scan is not None and k == n and drop <= 0:  # 扫光：上方一个小三角指着
                x = scan * w + (w - 1) / 2 - 0.5
                y = y1 - LH - 1
                g.d.polygon([(x - 2, y - 2), (x + 2, y - 2), (x, y)], fill=1)
        if drop <= 0:  # 还没长出的层：疏点虚线
            for k in range(n + 1, 7):
                y1 = layer_y(k) - 2
                for x in range(1 + k % 2 * 2, 128, 6):
                    g.px(x, y1)
        if dim < 1:
            g.fade(dim, (0, layer_y(n) - LH, 128, TOP + 1))

    def mark(self, g: Gfx, t: float, n: int):
        """本场之卦：最上层上方一个小三角"""
        if n < 6:
            return
        x = self.col * 2 + 0.5
        y = layer_y(6) + 2
        g.d.polygon([(x - 2, y + 3), (x + 2, y + 3), (x, y + 1)], fill=1 if blink(t, 1.0, 0.7) else 0, outline=1)

    def base(self, g: Gfx, angle: float, labels: bool = True):
        taiji(g, TJ[0], TJ[1], 5.5, angle)
        if labels:
            g.text(18, 52, "阳")
            g.text(98, 52, "阴")

    def phrase(self, g: Gfx, s: str, a: float = 1.0):
        s = s[:int(round(a * len(s)))]
        g.text(64, 1, s, align="center")

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        cx, cy = TJ
        if t < 1.0:  # 无极：一圈画出
            p = ease_out(span(t, 0, 1.0))
            pts = [(cx + math.sin(a / 40 * 2 * math.pi * p) * 6.5, cy - math.cos(a / 40 * 2 * math.pi * p) * 6.5)
                   for a in range(41)]
            g.d.line(pts, fill=1)
            self.phrase(g, "易有太极", span(t, 0.2, 1.0))
            g.mx_level = 1
            g.mx[3:5, 3:5] = True
            return
        ang = (t - 1.0) ** 2 * 3
        self.base(g, ang, labels=t > 3.0)
        if t < 1.4:
            ring(g, cx, cy, 6 + (t - 1.0) * 30, 2)
        split = span(t, 1.8, 3.2)
        if split > 0:
            w = 64 * ease_out_back(split)
            y1 = layer_y(1)
            g.d.rectangle((64 - w, y1 - LH + 1, 64 - 2, y1), fill=1)
            g.d.rectangle((64, y1 - LH + 1, 64 + w - 2, y1), outline=1)
        if t < 2.6:
            self.phrase(g, "易有太极")
        else:
            self.phrase(g, PHRASE[0], span(t, 2.8, 3.6))
        if split > 0:
            mx_hexagram(g, [7], 1)
            g.mx[7, :] = True
        else:
            mx_taiji(g, ang)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k)
            return
        n, prog, sec = self.stage(e)
        grow = span(sec, 0, GROW) if n > 1 else 1.0
        nb = 1 << n
        scan = min(int(prog * nb), nb - 1) if grow >= 1 else None
        self.base(g, t * 0.8)
        self.layers(g, n, grow, scan=scan)
        self.mark(g, t, n)
        if n == 6 and scan is not None:
            lines = self.col_lines(scan, 6)
            hit = scan == self.col
            if hit and blink(t, 0.4, 0.5):
                g.invert((0, 0, 128, 13))
            self.phrase(g, full_name(lines))
            if hit:
                g.mx_level = 3
        else:
            self.phrase(g, PHRASE[n - 1])
        j = scan if scan is not None else 0
        mx_hexagram(g, self.col_lines(j, n), n)
        g.mx[7, :] = True
        if grow < 1:
            g.mx_level = 3

    def _renew(self, g: Gfx, t: float, k: float):
        """六层自上而下落回太极，太极急转放光，再一分为二"""
        drop = span(k, 0, 2.2)
        spin = 1 + 6 * (1 - abs(k - 2.4) / 1.2) if 1.2 < k < 3.6 else 1
        self.base(g, t * 0.8 * spin + k * 3)
        if k < 2.4:
            self.layers(g, 6, 1.0, drop=drop)
        elif k < 3.4:
            ring(g, TJ[0], TJ[1], 7 + (k - 2.4) * 24, 2)
            g.mx_level = 4
        else:
            self.layers(g, 1, span(k, 3.4, 4.6))
        self.phrase(g, "易有太极" if 2.0 < k < 3.6 else PHRASE[0] if k >= 3.6 else PHRASE[5])
        g.mx[7, :] = True
        if k < 2.4:
            mx_hexagram(g, self.col_lines(63, 6), int(6 * (1 - drop)))
        else:
            mx_taiji(g, k * 4)

    def interrupt(self, g: Gfx, t: float, e: float):
        n, prog, sec = self.stage(e)
        nb = 1 << n
        scan = min(int(prog * nb), nb - 1)
        ang_spd = 0.8 * (1 - span(t, 0, 1.2))
        self.base(g, 0.8 * min(t, 0.6) * ang_spd)
        dim = 1 - 0.6 * span(t, 0.2, 1.2)
        self.layers(g, n, 1.0, scan=scan if t < 0.4 or blink(t, 0.3) else None, dim=dim)
        self.mark(g, t, n)
        self.phrase(g, "动极而静" if t > 0.5 else PHRASE[n - 1])
        mx_hexagram(g, self.col_lines(scan, n), n)
        g.mx[7, :] = True

    def resume(self, g: Gfx, t: float, e: float):
        n, prog, sec = self.stage(e)
        nb = 1 << n
        scan = min(int(prog * nb), nb - 1)
        self.base(g, t * 0.8 * span(t, 0, 1.0))
        self.layers(g, n, 1.0, scan=scan if t > 1.0 else None, dim=0.4 + 0.6 * span(t, 0.2, 1.2))
        self.mark(g, t, n)
        if t < 1.0:
            self.phrase(g, "静极复动")
        elif n == 6:
            self.phrase(g, full_name(self.col_lines(scan, 6)))
        else:
            self.phrase(g, PHRASE[n - 1])
        mx_hexagram(g, self.col_lines(scan, n), n)
        g.mx[7, :] = True

    def complete(self, g: Gfx, t: float, e: float):
        n = 6
        self.base(g, t * (0.8 + 4 * span(t, 0, 1.5)))
        self.layers(g, n, 1.0)
        self.mark(g, t, n)
        # 逐层翻亮
        for k in range(1, 7):
            s = 0.3 + (k - 1) * 0.22
            if s < t < s + 0.5:
                y1 = layer_y(k)
                g.invert((0, y1 - LH, 128, y1 + 1))
        if t < 1.6:
            self.phrase(g, full_name(self.ctx.lines), 1 - span(t, 1.0, 1.6))
        else:
            typewriter(g, 64, 1, "生生之谓易", t - 1.6, cps=5, align="center")
        if t > 1.6:  # 本场之卦从它那一列升起，放大到中央
            g.fade(1 - 0.75 * span(t, 1.6, 2.2), (0, 13, 128, TOP + 1))
            p = ease_out_back(span(t, 1.8, 2.6))
            cx = lerp(self.col * 2 + 0.5, 64, p)
            w = int(lerp(2, 26, p)) // 2 * 2
            x0 = int(cx - w / 2)
            g.d.rectangle((x0 - 3, 15, x0 + w + 2, 43), fill=0, outline=1 if p > 0.5 else 0)
            from ..engine.symbols import draw_hexagram
            draw_hexagram(g, x0, 18, self.ctx.lines, w=max(w, 2), h=2, step=4)
        mx_hexagram(g, self.ctx.lines, 6)
        g.mx[7, :] = True
        g.mx_level = 1 + (4 if 0.3 < t < 2.0 and blink(t, 0.25) else 0)
