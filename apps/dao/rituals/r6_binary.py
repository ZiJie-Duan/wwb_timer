"""二进制卦（像素风）：小道士在一台“牛郎星 8800”式的拨码面板前拨开关数数，墙边的 CRT 上显示对应的卦。

六爻就是 6 个 bit，阳 = 1、阴 = 0。依据：邵雍“伏羲六十四卦次序”按一分为二排列，正是 0–63 的二进制序；
1701 年白晋把伏羲卦图寄给莱布尼茨，莱布尼茨认出它与二进制算术一致（坤 000000 = 0、剥 000001 = 1、比 = 2……乾 = 63，
初爻为最高位、上爻为最低位）。《道德经》第四十章：“反者道之动。”

画面：桌上一台长长的拨码面板（左端十进制小读数窗、RUN 灯、RUN/HALT 开关；右边六个拨杆开关，上面一排指示灯，
按三个一组分成下卦、上卦），右边一台 CRT 显示卦名、0B 串和六条爻；墙上挂一幅先天太极小轴。
入场：小道士走到面板左端，拨上 RUN（火星、震一下），指示灯自检一闪，CRT 开机，六条阴爻从右边一条条“移位”进来，
      0B000000、“坤”，小道士走到初爻开关前拱手。
持续：一轮 10 分钟数完 64 卦（约 9.4 秒一卦）：每一卦小道士先走到最右的上爻开关，从右往左一个个拨——
      进位要连拨好几个时就一路小跑；每拨一下“咔”地迸火星、指示灯变、CRT 上那条爻开合（阳爻中间裂开 / 阴爻合拢）并闪一下。
      拨完了他看屏、指一指、拱拱手；RUN 灯一直跟着时钟闪。
      一轮满：乾 + 1 溢出，他从右到左一口气把六个开关全拨下，屏上 OVERFLOW 闪、整屏反色一震，“反者道之动”，“第几周”加一。
中断：小道士跑到左端把 RUN 拨成 HALT，RUN 灯灭，屏上 HALT，爻从上往下变成空心。
恢复：拨回 RUN，爻从下往上重新填实，他走回原来的开关前。
圆满：计数器飞转两圈、越转越慢，停在本场法事的卦（ctx.lines）上：闪白、震屏、卦象框起，“本卦”。
点阵：当前卦（mx_hexagram），右上角时钟点闪，底行 64 卦进度。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, span
from ..engine.chars import Part
from ..engine.gfx import Gfx, text_width
from ..engine.scene import register
from ..engine.symbols import HEXAGRAMS, hexagram, mx_hexagram, taiji, yang
from .r6_common import R6, badge, banner, dao, nth, tiny

FLOOR = 58
TABLE_Y = 48
PANEL = (3, 31)                # 面板左上角（82×17）
SW_X = tuple(31 + i * 10 for i in range(6))   # 六个开关 x（左 = 初爻 MSB，右 = 上爻 LSB）
LED_Y = 35
SW_Y = 42                      # 开关底座 y
RUN_X = 21                     # RUN/HALT 开关（上面是 RUN 灯）
LAMP_X = 21
CRT = (86, 3)                  # CRT 左上角（42×45）
SCR = (89, 6, 124, 42)         # 屏幕内框
BAR_X, BAR_W = 90, 31
BAR_Y0 = 26                    # 上爻顶 y
STEP = 600.0 / 64
RENEW = 6.0
SPEED = 42.0                   # 走路速度 像素/秒
FLIP_DT = 0.55


def stand_x(i: int) -> float:
    """拨第 i 个开关时小道士站的位置"""
    return SW_X[i] - 12


RUN_STAND = RUN_X - 12


def bits_of(v: int):
    """数值 → 六爻（初爻在前，初爻 = 最高位）"""
    return [(v >> (5 - i)) & 1 for i in range(6)]


def hex_name(v: int) -> str:
    return hexagram([bool(b) for b in bits_of(v)])[1]


def trailing_ones(m: int) -> int:
    c = 0
    while m & 1 and c < 6:
        c += 1
        m >>= 1
    return c


# ---------------------------------------------------------------- 道具（像素造型，只生成一次）

def _panel():
    """拨码面板 82×17：亮边框（圆角）、顶上散热格栅、黑面板；读数窗、RUN 灯座与开关座；
    六个开关座与指示灯座，中间一道竖隔线把下卦、上卦分开；右端网点阴影"""
    w, h = 82, 17
    p = Part(w, h)
    p.shape("rectangle", (0, 1, w - 1, h - 1), fill=1)
    p.shape("rectangle", (1, 0, w - 2, h - 1), fill=1)
    p.d.rectangle((2, 2, w - 3, h - 2), fill=0)
    for x in range(4, w - 4, 3):                        # 顶上格栅
        p.px(x, 0, 0)
    p.d.rectangle((3, 3, 13, 10), outline=1)            # 读数窗
    p.px(3, 3, 0), p.px(13, 3, 0), p.px(3, 10, 0), p.px(13, 10, 0)
    for x in list(SW_X) + [RUN_X]:
        lx = x - PANEL[0]
        p.d.rectangle((lx - 1, SW_Y - PANEL[1], lx + 1, SW_Y - PANEL[1] + 1), fill=1)   # 开关座
        p.px(lx, SW_Y - PANEL[1], 0)
        p.d.rectangle((lx - 1, LED_Y - PANEL[1] - 1, lx + 1, LED_Y - PANEL[1] + 1), outline=1)  # 灯座
    dx = (SW_X[2] + SW_X[3]) // 2 - PANEL[0]
    p.d.line((dx, 3, dx, h - 3), fill=1)               # 下卦 | 上卦
    lx = RUN_X - PANEL[0] + 5
    p.d.line((lx, 3, lx, h - 3), fill=1)
    p.dither([(1, 14), (w - 2, 14), (w - 2, 16), (1, 16)], 0.5, 0)
    return p.sprite()


def _crt():
    """CRT 42×45：圆角外壳、屏框阴线、下沿两只旋钮与散热槽、右侧网点、两只脚"""
    p = Part(42, 45)
    p.shape("rectangle", (1, 0, 40, 42), fill=1)
    p.shape("rectangle", (0, 1, 41, 41), fill=1)
    p.d.rectangle((2, 2, 39, 40), fill=0)
    p.px(2, 2, 1), p.px(39, 2, 1), p.px(2, 40, 1), p.px(39, 40, 1)
    for x in (6, 12):                                   # 旋钮
        p.d.ellipse((x - 2, 40, x + 2, 44), fill=1)
    p.shape("ellipse", (4, 40, 8, 44), fill=1)
    p.shape("ellipse", (10, 40, 14, 44), fill=1)
    p.px(6, 41, 0), p.px(12, 43, 0)
    for x in range(18, 32, 3):
        p.d.line((x, 41, x, 42), fill=0)
    p.dither([(40, 3), (41, 3), (41, 40), (40, 40)], 0.5, 0)
    p.d.rectangle((35, 41, 37, 42), fill=0)             # 电源灯座
    p.shape("rectangle", (4, 43, 7, 44), fill=1)
    p.shape("rectangle", (34, 43, 37, 44), fill=1)
    return p.sprite()


def _table():
    """长桌 126×10：厚桌面、三条腿、横撑"""
    p = Part(126, FLOOR - TABLE_Y)
    p.shape("rectangle", (0, 0, 125, 1), fill=1)
    p.d.line((1, 1, 124, 1), fill=0)
    for x in (3, 62, 120):
        p.shape("rectangle", (x, 2, x + 2, FLOOR - TABLE_Y - 1), fill=1)
        p.px(x + 2, 4, 0), p.px(x + 2, 6, 0)
    p.shape("line", (5, 6, 120, 6), fill=1)
    return p.sprite()


def _scroll():
    """墙上小轴 21×20：上下轴杆、挂绳、裱边（中间画太极）"""
    p = Part(21, 20)
    p.shape("line", (6, 2, 10, 0), fill=1)
    p.shape("line", (14, 2, 10, 0), fill=1)
    p.shape("rectangle", (0, 2, 20, 3), fill=1)
    p.shape("rectangle", (2, 4, 18, 17), fill=1)
    p.d.rectangle((3, 5, 17, 16), fill=0)
    p.shape("rectangle", (0, 18, 20, 19), fill=1)
    p.px(0, 19, 0), p.px(20, 19, 0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"panel": _panel, "crt": _crt, "table": _table, "scroll": _scroll}[name]()
    return _PROPS[name]


# ---------------------------------------------------------------- 画面

def room(g: Gfx, t: float):
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    pix.blit(g, prop("scroll"), 50, 4)
    taiji(g, 60, 14, 4, t * 0.4)
    pix.blit(g, prop("table"), 1, TABLE_Y)


def panel(g: Gfx, bits, t: float, run: bool, dec: int | None, levers=None, leds=None):
    """面板：指示灯（亮 = 实心 + 两侧光点）、拨杆（lever 0..1，1 = 朝上）、读数、RUN 灯与开关"""
    pix.blit(g, prop("panel"), *PANEL)
    for i, x in enumerate(SW_X):
        on = bits[i] if leds is None else leds[i]
        if on:
            g.d.rectangle((x - 1, LED_Y - 1, x + 1, LED_Y + 1), fill=1)
        lv = bits[i] if levers is None else levers[i]
        lever(g, x, lv)
    lever(g, RUN_X, 1.0 if run else 0.0)
    if run and int(t * 4) % 2 == 0:
        g.d.rectangle((LAMP_X - 1, LED_Y - 1, LAMP_X + 1, LED_Y + 1), fill=1)
    if dec is not None:
        tiny(g, PANEL[0] + 9, PANEL[1] + 5, f"{dec:02d}", align="center")


def lever(g: Gfx, x: int, up: float):
    """拨杆：从底座伸出，up 1 朝上（2 像素杆 + 横头），0 朝下"""
    y = SW_Y
    if up >= 0.5:
        hh = 1 if up < 0.9 else 2
        g.d.line((x, y - 1, x, y - hh), fill=1)
        g.d.line((x - 1, y - hh - 1, x + 1, y - hh - 1), fill=1)
    else:
        hh = 1 if up > 0.1 else 2
        g.d.line((x, y + 2, x, y + 1 + hh), fill=1)
        g.d.line((x - 1, y + 2 + hh, x + 1, y + 2 + hh), fill=1)


def crt(g: Gfx, on: float = 1.0):
    pix.blit(g, prop("crt"), *CRT)
    if 0 < on < 1:
        x0, y0, x1, y1 = SCR
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        w = int((x1 - x0) / 2 * ease_out(span(on, 0, 0.4)))
        h = int((y1 - y0) / 2 * ease_out(span(on, 0.4, 1)))
        g.d.rectangle((cx - w, cy - h, cx + w, cy + max(h, 0)), fill=1)
    if on >= 1:
        g.d.point((CRT[0] + 36, CRT[1] + 41))


def bar_y(i: int) -> int:
    return BAR_Y0 + (5 - i) * 3


def bars(g: Gfx, bits, gaps=None, hollow=None, flash=None, dx=None):
    """CRT 上的六爻：阳实阴断（gap 0..1 = 中缝张开程度），hollow：空心，dx：从右边滑进来的偏移"""
    for i in range(6):
        y = bar_y(i)
        x0 = BAR_X + (dx[i] if dx else 0)
        if x0 > SCR[2]:
            continue
        x1 = min(x0 + BAR_W - 1, SCR[2] - 1)
        gp = gaps[i] if gaps else (0.0 if bits[i] else 1.0)
        half = int(round(gp * 3))
        cx = x0 + BAR_W // 2
        if hollow and hollow[i]:
            g.d.rectangle((x0, y, x1, y + 1), outline=1)
            g.d.line((x0 + 1, y, x1 - 1, y), fill=1)
            for x in range(x0 + 1, x1, 2):
                g.px(x, y + 1, 0)
            if half:
                g.d.rectangle((cx - half, y, cx + half, y + 1), fill=0)
            continue
        g.d.rectangle((x0, y, x1, y + 1), fill=1)
        if half:
            g.d.rectangle((cx - half, y, cx + half, y + 1), fill=0)
        if flash and flash[i]:
            g.d.line((x0 - 2, y - 1, x1 + 2, y - 1), fill=1) if flash[i] > 0.5 else None
            g.d.line((x0 - 2, y + 2, x1 + 2, y + 2), fill=1) if flash[i] > 0.5 else None
            g.px(x0 - 2, y), g.px(x1 + 2, y + 1)


def readout(g: Gfx, s: str, blink: bool = False, t: float = 0.0):
    """CRT 上 0B 串那一行"""
    if blink and int(t * 4) % 2:
        return
    tiny(g, (SCR[0] + SCR[2]) / 2 + 1, 19, s, align="center")


def name_text(g: Gfx, v: int):
    g.text((SCR[0] + SCR[2]) / 2 + 1, 7, hex_name(v), align="center")


def mx_state(g: Gfx, bits, t: float, n: int, run: bool = True):
    mx_hexagram(g, [bool(b) for b in bits])
    if run:
        g.mx[0, 7] = int(t * 4) % 2 == 0
    for x in range(int(round(n / 64 * 8))):
        g.mx[7, x] = True


# ---------------------------------------------------------------- 一卦的排程（全是 e 的函数）

def plan(n: int):
    """数到第 n 卦（n ≥ 1）：从哪走来、拨哪些开关、什么时候拨。返回 (起点 x, [(拨的时刻, 开关, 新值)], 终点 x)"""
    m = n - 1
    c = trailing_ones(m) + 1
    if m >= 1:
        prev = stand_x(5 - trailing_ones(m - 1))
    else:
        prev = stand_x(0)
    t0 = 0.3 + abs(stand_x(5) - prev) / SPEED
    flips = [(t0 + j * FLIP_DT + 0.2, 5 - j, 0 if j < c - 1 else 1) for j in range(c)]
    return prev, flips, stand_x(5 - c + 1)


def step_state(n: int, s: float):
    """第 n 卦开始后 s 秒：bits、小道士 x / 动作（walk / flip+角度 / idle）、各爻的开合与闪光"""
    if n == 0:
        return {"bits": bits_of(0), "x": stand_x(0), "act": "idle", "gaps": None, "flash": None, "done": 0.0}
    prev, flips, end = plan(n)
    old = bits_of(n - 1)
    bits = list(old)
    gaps = [0.0 if b else 1.0 for b in old]
    flash = [0.0] * 6
    t0 = 0.3 + abs(stand_x(5) - prev) / SPEED
    act, ang, x = "idle", 0.0, prev
    if s < 0.3:
        x = prev
    elif s < t0:
        x = lerp(prev, stand_x(5), (s - 0.3) / max(t0 - 0.3, 1e-3))
        act = "walk"
    else:
        x = stand_x(5)
        for j, (tf, i, nb) in enumerate(flips):
            if s >= tf - 0.2:
                x = stand_x(i) if s < tf + 0.35 or j == len(flips) - 1 else lerp(stand_x(i), stand_x(i - 1),
                                                                                  span(s, tf + 0.15, tf + 0.35))
                if s < tf + 0.15:
                    act, ang = "flip", (lerp(-20, 20, span(s, tf - 0.2, tf)) if nb else lerp(20, -20, span(s, tf - 0.2, tf)))
                elif s < tf + 0.35 and j < len(flips) - 1:
                    act = "walk"
                else:
                    act, ang = "idle", 0.0
            if s >= tf:
                bits[i] = nb
                k = span(s, tf, tf + 0.25)
                gaps[i] = (1 - k) if nb else k
                flash[i] = 1 - span(s, tf, tf + 0.3)
    done = s - (flips[-1][0] + 0.4)
    return {"bits": bits, "x": x, "act": act, "ang": ang, "gaps": gaps, "flash": flash, "flips": flips,
            "done": done}


@register
class BinaryGua(R6):
    id = "r6.binary"
    name = "二进制卦"
    desc = "小道士在拨码面板上一个个拨开关数数，CRT 上的卦从坤（000000）数到乾（111111），溢出归零——反者道之动"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def init(self):
        self.flipped = set()

    def counter(self, g: Gfx, e: float):
        badge(g, nth(int(e // self.CYCLE) + 1, "周"))

    def daoshi(self, g: Gfx, x: float, t: float, act: str, ang: float = 0.0, face: str = "normal"):
        if act == "walk":
            return dao(g, x, FLOOR, t, pose="walk")
        if act == "flip":
            return dao(g, x, FLOOR, t, angle=ang, face="happy" if ang > 0 else "normal")
        return dao(g, x, FLOOR, t, pose=act if act in ("gong", "bow", "point", "raise", "down") else "down",
                   face=face)

    def idle_act(self, t: float, done: float) -> tuple[str, str]:
        ph = t % 16
        if done < 0:
            return "down", "normal"
        if done < 1.4:
            return "point", "happy"
        if 6.0 < ph < 8.0:
            return "gong", "happy"
        if 12.0 < ph < 13.5:
            return "point", "normal"
        return "down", "normal"

    def click(self, g: Gfx, key, x: int, y: int):
        """拨一下：火星（每次只迸一回）"""
        if key not in self.flipped:
            self.flipped.add(key)
            if len(self.flipped) > 64:
                self.flipped = {key}
            self.sparks.burst(x, y, 6, 22, up=14, life=0.35, gravity=60)

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        room(g, t)
        run = t >= 1.9
        test = 2.0 < t < 2.6 and int(t * 8) % 2 == 0
        panel(g, bits_of(0), t, run, 0 if t > 2.6 else None, leds=[test] * 6)
        crt(g, span(t, 2.2, 2.8) if t < 2.8 else 1.0)
        if t >= 2.8:            # 移位寄存器：六条阴爻从右边一条条移进来
            dx = [max(0, int((1 - ease_out(span(t, 2.9 + i * 0.25, 3.2 + i * 0.25))) * 40)) for i in range(6)]
            bars(g, [0] * 6, dx=dx)
            nshown = sum(1 for i in range(6) if t > 3.2 + i * 0.25)
            readout(g, "0B" + "0" * nshown)
        if t < 1.5:
            self.daoshi(g, lerp(-12, RUN_STAND, ease_out(span(t, 0, 1.5))), t, "walk")
        elif t < 2.3:
            ang = lerp(-20, 20, span(t, 1.6, 1.9))
            h = self.daoshi(g, RUN_STAND, t, "flip", ang)
            if t >= 1.9:
                self.click(g, ("run", 0), RUN_X, SW_Y - 2)
            if 1.9 < t < 2.1:
                pix.shake(g, t, 1.2)
        elif t < 4.6:
            self.daoshi(g, RUN_STAND, t, "down", face="normal")
        elif t < 5.1:
            self.daoshi(g, lerp(RUN_STAND, stand_x(0), span(t, 4.6, 5.1)), t, "walk")
        else:
            self.daoshi(g, stand_x(0), t, "gong" if t < 5.7 else "down", face="happy")
        self.fx(g, dt)
        mx_state(g, bits_of(0), t, 0, run) if t > 2.6 else g.mx_rows([0, 0, 0, 0x18, 0x18, 0, 0, 0])
        self.counter(g, 0)
        if t > 4.5:
            name_text(g, 0)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self.overflow(g, t, e, k, dt)
            return
        n = min(int(k // STEP), 63)
        s = k - n * STEP
        st = step_state(n, s)
        room(g, t)
        panel(g, st["bits"], t, True, sum(b << (5 - i) for i, b in enumerate(st["bits"])),
              levers=self.levers(st, s))
        crt(g)
        bars(g, st["bits"], st["gaps"], flash=st["flash"])
        readout(g, "0B" + "".join(map(str, st["bits"])))
        if st["act"] == "idle":
            act, face = self.idle_act(t, st["done"])
            self.daoshi(g, st["x"], t, act, face=face)
        else:
            self.daoshi(g, st["x"], t, st["act"], st.get("ang", 0.0))
        for tf, i, nb in st.get("flips") or []:
            if tf <= s < tf + 0.3:
                self.click(g, (int(e // STEP), i), SW_X[i], SW_Y - 2)
                if i == 5 - len(st["flips"]) + 1:
                    pix.shake(g, t, 0.6)
        self.fx(g, dt)
        v = sum(b << (5 - i) for i, b in enumerate(st["bits"]))
        mx_state(g, st["bits"], t, n + 1)
        self.counter(g, e)
        name_text(g, v)

    def levers(self, st, s):
        """拨杆在拨的那一下有中间态"""
        lv = [float(b) for b in st["bits"]]
        for tf, i, nb in st.get("flips") or []:
            if tf - 0.1 <= s < tf:
                lv[i] = 0.5 + (0.25 if nb else -0.25) * -1
        return lv

    def overflow(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """续：乾 + 1 溢出，从右到左一口气全拨下，OVERFLOW，反者道之动"""
        room(g, t)
        bits = [1] * 6
        gaps = [0.0] * 6
        flash = [0.0] * 6
        x, act, ang = stand_x(5), "idle", 0.0
        for j in range(6):
            i = 5 - j
            tf = 0.5 + j * 0.38
            if k >= tf - 0.18:
                x = stand_x(i) if k < tf + 0.1 or j == 5 else lerp(stand_x(i), stand_x(i - 1), span(k, tf + 0.1, tf + 0.2))
                act = "flip" if k < tf + 0.1 else ("walk" if j < 5 else "idle")
                ang = lerp(20, -20, span(k, tf - 0.18, tf))
            if k >= tf:
                bits[i] = 0
                gaps[i] = span(k, tf, tf + 0.25)
                flash[i] = 1 - span(k, tf, tf + 0.3)
                if k < tf + 0.3:
                    self.click(g, ("of", int(e // self.CYCLE), i), SW_X[i], SW_Y - 2)
        panel(g, bits, t, True, sum(b << (5 - i) for i, b in enumerate(bits)))
        crt(g)
        bars(g, bits, gaps, flash=flash)
        over = k > 2.9
        readout(g, "OVERFLOW" if over else "0B" + "".join(map(str, bits)), blink=over and k < 4.0, t=t)
        if act == "idle":
            if k < 0.4:
                act = "down"
            else:
                act = "bow" if 3.4 < k < 4.8 else ("down" if k < 3.4 else "gong")
            self.daoshi(g, x, t, act, face="wow" if 2.9 < k < 3.4 else "normal")
        else:
            self.daoshi(g, x, t, act, ang)
        if abs(k - 2.9) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst((SCR[0] + SCR[2]) / 2, 30, 20, 40, up=10, life=0.8)
        if 2.9 < k < 3.3:
            pix.shake(g, t, 1.8)
        self.fx(g, dt)
        mx_state(g, bits, t, 0)
        if k > 2.9:
            g.mx_level = 1 + int(5 * (1 - span(k, 2.9, 3.6)))
        if k < 3.1 or k > 5.6:
            self.counter(g, e if k > 5.6 else e - k - 1)
        else:
            banner(g, 44, 3, "反者道之动", span(k, 3.1, 3.5), t=t)
        name_text(g, sum(b << (5 - i) for i, b in enumerate(bits)))

    # ------------------------------------------------------------ 中断 / 恢复

    def frozen(self, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return bits_of(0), stand_x(0), 0
        n = min(int(k // STEP), 63)
        st = step_state(n, k - n * STEP)
        return st["bits"], st["x"], n

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        bits, x0, n = self.frozen(e)
        room(g, t)
        halt = t >= 0.85
        panel(g, bits, t, not halt, sum(b << (5 - i) for i, b in enumerate(bits)))
        crt(g)
        hollow = [t > 0.9 + (5 - i) * 0.1 for i in range(6)]
        bars(g, bits, hollow=hollow)
        readout(g, "HALT" if halt else "0B" + "".join(map(str, bits)), blink=halt and t < 1.3, t=t)
        if t < 0.6:
            self.daoshi(g, lerp(x0, RUN_STAND, ease_in_out(span(t, 0, 0.6))), t, "walk")
        elif t < 1.0:
            self.daoshi(g, RUN_STAND, t, "flip", lerp(20, -20, span(t, 0.65, 0.85)))
            if halt:
                self.click(g, ("halt", round(e, 2)), RUN_X, SW_Y - 2)
        else:
            self.daoshi(g, RUN_STAND, t, "down")
        self.fx(g, dt)
        mx_state(g, bits, t, n + 1, run=not halt)
        if halt:
            g.mx[0, 7] = False
        self.counter(g, e)
        name_text(g, sum(b << (5 - i) for i, b in enumerate(bits)))

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        bits, x1, n = self.frozen(e)
        room(g, t)
        run = t >= 0.3
        panel(g, bits, t, run, sum(b << (5 - i) for i, b in enumerate(bits)))
        crt(g)
        hollow = [t < 0.4 + i * 0.1 for i in range(6)]
        bars(g, bits, hollow=hollow)
        readout(g, "RUN" if 0.3 < t < 1.1 else ("HALT" if t <= 0.3 else "0B" + "".join(map(str, bits))))
        if t < 0.5:
            self.daoshi(g, RUN_STAND, t, "flip", lerp(-20, 20, span(t, 0.05, 0.3)))
            if run:
                self.click(g, ("run", round(e, 2)), RUN_X, SW_Y - 2)
            if 0.3 < t < 0.45:
                pix.shake(g, t, 1)
        elif t < 1.7 and abs(x1 - RUN_STAND) > 1:
            q = span(t, 0.6, 1.6)
            self.daoshi(g, lerp(RUN_STAND, x1, ease_in_out(q)), t, "walk" if q < 1 else "down")
        else:
            self.daoshi(g, x1, t, "down")
        self.fx(g, dt)
        mx_state(g, bits, t, n + 1, run=run)
        self.counter(g, e)
        name_text(g, sum(b << (5 - i) for i, b in enumerate(bits)))

    # ------------------------------------------------------------ 圆满：飞转，停在本卦

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        bits0, x0, n = self.frozen(e)
        start = sum(b << (5 - i) for i, b in enumerate(bits0))
        target_bits = [1 if yang(v) else 0 for v in self.ctx.lines]
        target = sum(b << (5 - i) for i, b in enumerate(target_bits))
        total = 128 + (target - start) % 64
        q = ease_out(span(t, 0.0, 3.2))
        v = (start + int(round(total * q))) % 64
        bits = bits_of(v)
        stopped = t >= 3.2
        room(g, t)
        panel(g, bits, t, True, v)
        crt(g)
        bars(g, bits)
        if stopped and (int(t * 3) % 2 == 0 or t > 4.4):   # 框起本卦：左右两道方括号
            for x, d in ((BAR_X - 3, 1), (BAR_X + BAR_W + 2, -1)):
                g.d.line((x, BAR_Y0 - 1, x, bar_y(0) + 1), fill=1)
                g.d.line((x, BAR_Y0 - 1, x + d * 2, BAR_Y0 - 1), fill=1)
                g.d.line((x, bar_y(0) + 1, x + d * 2, bar_y(0) + 1), fill=1)
        readout(g, "0B" + "".join(map(str, bits)))
        if t < 3.2:
            self.daoshi(g, x0 if t > 0.4 else x0, t, "raise" if int(t * 3) % 2 == 0 else "point", face="wow")
            if int(t * 30) % 4 == 0 and t < 2.0:
                self.sparks.burst(SW_X[int(t * 17) % 6], SW_Y - 2, 2, 14, up=10, life=0.3)
        else:
            self.daoshi(g, x0, t, "bow" if 3.6 < t < 4.8 else "gong", face="happy")
        if abs(t - 3.2) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst((SCR[0] + SCR[2]) / 2, 33, 26, 44, up=12, life=1.0)
        if 3.2 < t < 3.6:
            pix.shake(g, t, 1.8)
        self.fx(g, dt)
        mx_state(g, bits, t, 64)
        g.mx_level = 6 if 3.2 < t < 3.8 else 2
        name_text(g, v)
        if stopped:
            banner(g, 27, 4, "本卦", span(t, 3.4, 3.8), t=t)
