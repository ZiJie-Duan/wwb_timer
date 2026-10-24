"""二进制卦：六爻就是 6 个 bit，阳 = 1、阴 = 0。计数器随计时从 坤(0) 一路加到 乾(63)，
每加一，进位像涟漪一样从上爻传到初爻；满 63 再加一就溢出回到 0——“反者道之动”。

依据：邵雍“伏羲六十四卦次序”按一分为二排列，正是 0–63 的二进制序；1701 年白晋把这张图寄给莱布尼茨，
莱布尼茨认出其与他的二进制算术一致（坤 000000 = 0，剥 000001 = 1，比 000010 = 2 …… 乾 111111 = 63，
初爻为最高位、上爻为最低位）。《道德经》第四十章：“反者道之动。”
入场：六个 0 从右边一个个移进来（移位寄存器），落成六条阴爻，右侧打出 0b000000、0、坤为地。
持续：一轮 10 分钟数完 64 卦（约 9.4 秒一卦）：变的爻开合、闪火花，右边十进制大数字、0b 串、卦名同步；
      底部 64 格进度。一轮满：乾 + 1 溢出，六爻同时翻转，“反者道之动”，“第几周”加一。
中断：HALT，时钟停，爻从上往下变成空心。
恢复：RUN，爻从下往上重新填实。
圆满：计数器飞转两圈再减速，停在本场法事的卦上，卦象闪亮，显示卦名。
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

from ..engine.anim import blink, clamp, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from .r6_common import num as cn_num
from ..engine.gfx import Gfx, _FONT_FILES, font
from ..engine.scene import Ritual, register
from ..engine.symbols import full_name, mx_hexagram
from .r6_common import ctext, tiny

LX, LW, LH = 5, 40, 5      # 爻：左 x、宽、高
LY0, LSTEP = 6, 9          # 上爻顶 y、行距
RX = 62                    # 右侧面板
FLIP = 0.7                 # 一次翻转动画（秒）
RENEW = 5.0
STEPS = 64

_BIG: dict[str, tuple] = {}


def big(g: Gfx, x: float, y: float, s: str, fill: int = 1):
    """两倍大的 12px 字（缓存）"""
    g.texts.append((s, 12))
    hit = _BIG.get(s)
    if hit is None:
        f = font(12)
        w = max(1, int(f.getlength(s)))
        m = Image.new("1", (w, 16))
        d = ImageDraw.Draw(m)
        d.fontmode = "1"
        d.text((0, -_FONT_FILES[12][1]), s, font=f, fill=1)
        hit = (m.resize((w * 2, 32), Image.NEAREST), w * 2)
        if len(_BIG) > 200:
            _BIG.clear()
        _BIG[s] = hit
    g.img.paste(fill, (int(x), int(y)), hit[0])
    return hit[1]


def bits_of(v: int) -> list[int]:
    """值 → 六爻（自初爻起），初爻为最高位"""
    return [(v >> (5 - i)) & 1 for i in range(6)]


def value_of(lines) -> int:
    return sum((1 if (x in (7, 9) or x is True or x == 1) else 0) << (5 - i) for i, x in enumerate(lines))


def line_y(i: int) -> int:
    return LY0 + (5 - i) * LSTEP


def draw_yao(g: Gfx, i: int, open_: float, solid: bool = True, dx: float = 0):
    """open_ = 中间断口的宽度比例（0 = 阳，1 = 阴）"""
    y = line_y(i)
    gap = int(round(open_ * 10))
    half = (LW - gap) // 2
    boxes = [(LX + dx, y, LX + dx + LW - 1, y + LH - 1)] if gap <= 0 else \
        [(LX + dx, y, LX + dx + half - 1, y + LH - 1), (LX + dx + LW - half, y, LX + dx + LW - 1, y + LH - 1)]
    for b in boxes:
        if solid:
            g.d.rectangle(b, fill=1)
        else:
            g.d.rectangle(b, outline=1)


@register
class BinaryGua(Ritual):
    id = "r6.binary"
    name = "二进制卦"
    desc = "六爻当 6 个 bit，计数器随计时从坤(0)数到乾(63)，进位涟漪翻爻，溢出归零“反者道之动”"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.5, "complete": 5.2}
    CYCLE = 600.0

    def setup(self):
        self.target = value_of(self.ctx.lines)

    # ------------------------------------------------------------ 零件

    def idx(self, e: float):
        """→ (当前值, 本卦已经过的秒数)"""
        k = (e % self.CYCLE) / self.CYCLE * STEPS
        v = min(STEPS - 1, int(k))
        return v, (k - v) * self.CYCLE / STEPS

    def hexa(self, g: Gfx, v: int, since: float, solid=None, flash: bool = True):
        """画卦 v；since = 变成 v 之后过了多久（< FLIP 时播放翻转动画）"""
        prev = (v - 1) % STEPS
        nb, pb = bits_of(v), bits_of(prev)
        for i in range(6):
            sol = True if solid is None else solid[i]
            if nb[i] != pb[i] and since < FLIP:
                delay = (5 - i) * 0.08          # 进位从上爻往下传
                k = ease_out_back(span(since, delay, delay + 0.3))
                op = lerp(1 - pb[i], 1 - nb[i], k)
                draw_yao(g, i, clamp(op, 0, 1.3), sol)
                if flash and 0 < k < 1:  # 火花
                    y = line_y(i) + 2
                    for j in range(5):
                        a = j / 5 * 2 * math.pi + since * 9
                        r = 4 + 6 * k
                        g.px(LX + LW / 2 + math.cos(a) * r, y + math.sin(a) * r * 0.5)
            else:
                draw_yao(g, i, 1 - nb[i], sol)
            tiny(g, LX + LW + 4, line_y(i), str(nb[i]))

    def panel(self, g: Gfx, v: int, n: int, top: str | None = None):
        big(g, RX + 2, 1, str(v))
        r = top if top is not None else f"第{cn_num(n)}周"
        ctext(g, 126, 3, r, size=8, align="right")
        bits = "".join(str(b) for b in bits_of(v))
        ctext(g, RX + 2, 31, "0b" + bits)
        ctext(g, RX + 2, 46, full_name(bits_of(v)))
        g.d.line((RX - 4, 0, RX - 4, 63), fill=1)

    def ticks(self, g: Gfx, v: int, t: float, run: bool = True):
        """底部 64 格进度"""
        for i in range(STEPS):
            if i <= v:
                g.px(RX + i, 62)
                if i % 8 == 0:
                    g.px(RX + i, 61)
        if run and blink(t, 1.0, 0.5):
            g.px(RX + v, 60)

    def mx(self, g: Gfx, v: int, t: float, run: bool = True):
        mx_hexagram(g, bits_of(v))
        g.mx[0, 7] = run and blink(t, 1.0, 0.5)
        g.mx[7, :int(v / STEPS * 8) + 1] = True

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, e: float):
        v, since = self.idx(e)
        n = int(e // self.CYCLE) + 1
        self.hexa(g, v, since if v > 0 else 99)
        self.panel(g, v, n)
        self.ticks(g, v, t)
        self.mx(g, v, t)
        if since < FLIP and v > 0:
            g.mx_level = 3

    def enter(self, g: Gfx, t: float):
        # 0.2–2.6：六个 0 依次从右移进来落成阴爻（先上爻，最后初爻）
        g.d.line((RX - 4, 0, RX - 4, 63), fill=1)
        for j in range(6):
            i = 5 - j
            st = 0.2 + j * 0.4
            k = span(t, st, st + 0.5)
            if k <= 0:
                continue
            if k < 1:
                x = lerp(128, LX + LW / 2, ease_out(k))
                tiny(g, x, line_y(i), "0")
                if k > 0.7:
                    draw_yao(g, i, 1, True, dx=0)
            else:
                draw_yao(g, i, 1)
                tiny(g, LX + LW + 4, line_y(i), "0")
            g.mx[6 - i, :] = k >= 1
            g.mx[6 - i, 3:5] = False
        a = span(t, 2.6, 3.6)
        if a > 0:
            big(g, RX + 2, 1, "0")
            s = "0b000000"
            ctext(g, RX + 2, 31, s[:int(round(a * len(s)))])
            if a > 0.6:
                ctext(g, RX + 2, 46, full_name([0] * 6))
                ctext(g, 126, 3, "第一周", size=8, align="right")
            self.ticks(g, 0, t)
            g.mx[7, 0] = True

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, k, e, t)
            return
        self.frame(g, t, e)

    def _renew(self, g: Gfx, k: float, e: float, t: float):
        n = int(e // self.CYCLE) + 1
        # 乾 → 坤：六爻同时翻
        f = ease_out_back(span(k, 0.0, 0.4))
        for i in range(6):
            draw_yao(g, i, clamp(f, 0, 1.3))
            tiny(g, LX + LW + 4, line_y(i), "0" if f > 0.5 else "1")
        if k < 0.5:
            for j in range(12):
                a = j / 12 * 2 * math.pi
                r = 10 + k * 60
                g.px(LX + LW / 2 + math.cos(a) * r, 30 + math.sin(a) * r * 0.6)
        self.panel(g, 0, n, top="OVERFLOW" if k < 2.5 else None)
        if k < 2.5:
            g.d.rectangle((RX - 4, 0, 127, 11), fill=0)
            tiny(g, 126, 4, "OVERFLOW" if blink(k, 0.3, 0.6) else "", align="right")
        self.ticks(g, 0, t)
        if 0.4 < k < 4.2:
            s = ease_out_back(span(k, 0.4, 0.8))
            h = 9 * s
            g.d.rectangle((6, 32 - h, 121, 32 + h), fill=0, outline=1)
            if s > 0.9:
                g.d.rectangle((8, 32 - h + 2, 119, 32 + h - 2), outline=1)
                ctext(g, 64, 27, "反者道之动", align="center")
        self.mx(g, 0, t)
        if k < 0.6:
            g.mx[:, :] = blink(k, 0.15, 0.5)
            g.mx_level = 5

    def interrupt(self, g: Gfx, t: float, e: float):
        v, since = self.idx(e)
        n = int(e // self.CYCLE) + 1
        hollow = span(t, 0.2, 1.1) * 6
        solid = [not (5 - i < hollow) for i in range(6)]
        self.hexa(g, v, 99, solid=solid)
        self.panel(g, v, n, top="HALT" if blink(t, 0.5, 0.7) or t > 1.1 else "")
        self.ticks(g, v, t, run=False)
        self.mx(g, v, t, run=False)
        for i in range(6):
            if not solid[i]:
                g.mx[6 - i, 1:7] = False

    def resume(self, g: Gfx, t: float, e: float):
        v, since = self.idx(e)
        n = int(e // self.CYCLE) + 1
        fill = span(t, 0.2, 1.1) * 6
        solid = [i < fill for i in range(6)]
        self.hexa(g, v, 99, solid=solid)
        self.panel(g, v, n, top="RUN" if t < 1.2 else None)
        self.ticks(g, v, t)
        self.mx(g, v, t)
        for i in range(6):
            if not solid[i]:
                g.mx[6 - i, 1:7] = False

    def complete(self, g: Gfx, t: float, e: float):
        v0, _ = self.idx(e)
        n = int(e // self.CYCLE) + 1
        total = (self.target - v0) % STEPS + 2 * STEPS
        pos = total * ease_out(span(t, 0.0, 2.8)) ** 1.0
        v = (v0 + int(pos)) % STEPS
        done = t >= 2.8
        if not done:
            self.hexa(g, v, 99, flash=False)
            self.panel(g, v, n, top="RUN")
            self.ticks(g, v, t)
            self.mx(g, v, t)
            g.mx_level = 3
            return
        # 停在本场的卦上：闪亮、框起来
        k = t - 2.8
        fl = k < 0.6 and blink(k, 0.15, 0.5)
        self.hexa(g, v, 99, flash=False)
        if fl:
            g.invert((LX - 2, LY0 - 2, LX + LW + 2, line_y(0) + LH + 2))
        g.d.rectangle((LX - 3, LY0 - 3, LX + LW + 2, line_y(0) + LH + 2), outline=1)
        self.panel(g, v, n, top="本卦")
        s = ease_out_back(span(k, 0.3, 0.8))
        if s > 0:
            g.d.rectangle((RX, 44, 127, 59), outline=1)
        for j in range(10):
            if blink(t + j * 0.17, 0.6, 0.3):
                a = rand(j, 9) * 2 * math.pi
                r = 30 + rand(j, 10) * 6
                g.px(LX + LW / 2 + math.cos(a) * r * 0.7, 30 + math.sin(a) * r * 0.9)
        self.ticks(g, v, t, run=False)
        mx_hexagram(g, bits_of(v))
        g.mx_level = 6 if k < 0.6 else 1 + int(3 * (1 - span(k, 0.6, 2.0)))
