"""示波太极（像素风）：小道士把示波器探头夹在自己的发髻上，拧着旋钮，用自己的“气”在 X-Y 模式下画出一幅太极。

画面：右边工作台上一台老式 CRT 示波器（提手、左侧旋钮面板：电源键、两颗 V/DIV 小旋钮、CH1/CH2 两个 BNC 口、
一颗大 TIME/DIV 旋钮；右侧圆角屏幕带点状刻度格），探头线从 CH1 口弯到小道士头顶的发髻上。
CH1 = sin、CH2 = cos，李萨如图形正好是一个圆。
入场：小道士走来，把探头夹上发髻（火花一闪），按下电源键，屏幕一道亮线横扫开机，格点亮起，亮点出现开始绕圈。
持续：一轮 10 分钟分四段——无极：电子束绕圈，余辉越拖越长成整圆；太极：亮点画出 S 形分界；
      生阳：两只鱼眼出现，阳鱼被扫描线一行行填亮（行距越来越密）；两仪：完整太极图，越转越快。
      小道士一直拧大旋钮（指针跟着转）；隔一阵：噪声爆发（轨迹乱抖，小道士一惊，一巴掌拍在机壳上，震屏火星，
      轨迹恢复干净），或者他闭目深吸一口气（圆跟着呼吸胀缩）。
      一轮满：太极急转、缩成一个亮点（归一），再从亮点涨回一个圆，“第几周”加一。
中断：STOP，电子束停住、余辉一点点暗下去，小道士松手拱手。  恢复：RUN，余辉亮回，电子束接着走。
圆满：太极补完、急转、闪白，从屏幕里浮出来放大，整个房间淡下去，下方“一阴一阳之谓道”。
依据：周敦颐《太极图说》“无极而太极……分阴分阳，两仪立焉”；《易·系辞上》“一阴一阳之谓道”。
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import _taiji_mask, mx_taiji, taiji
from .r6_common import R6, badge, banner, dao, glow_rays, nth, tiny

FLOOR = 58
BENCH = (50, 127, 44)         # 工作台 x0, x1, 台面 y
SC = (54, 6, 124, 43)         # 示波器外壳
SCX, SCY = 98, 25             # 屏幕中心
R = 12                        # 圆 / 太极半径
KNOB = (61, 37)               # 大 TIME/DIV 旋钮
JACK = (61, 26)               # CH1
DX = 47
STAGE = ("无极", "太极", "生阳", "两仪")
RENEW = 6.0
LOOP = 30.0
OMEGA = 2.2                   # 电子束角速度


# ---------------------------------------------------------------- 道具

def _scope():
    """示波器 71×38：外壳（圆角、右侧网点阴影、底脚）、提手、左面板（电源键、两颗小旋钮、两个 BNC 口、大旋钮座）、
    右侧屏幕的凹框（屏幕本身另画）"""
    w, h = SC[2] - SC[0] + 1, SC[3] - SC[1] + 1
    p = Part(w, h)
    p.shape("rectangle", (0, 1, w - 1, h - 3), fill=1)
    p.shape("rectangle", (1, 0, w - 2, h - 2), fill=1)
    p.d.rectangle((2, 2, w - 3, h - 4), fill=0)
    p.d.rectangle((3, 3, w - 4, h - 5), outline=1)
    # 面板与屏幕之间的分隔
    p.d.line((19, 3, 19, h - 5), fill=1)
    p.d.line((20, 3, 20, h - 5), fill=0)
    # 电源键
    p.d.rectangle((5, 5, 9, 8), outline=1)
    p.px(7, 6), p.px(7, 7)
    # 两颗小旋钮（V/DIV）
    p.d.ellipse((11, 4, 16, 9), outline=1)
    p.px(13, 5), p.px(14, 5)
    # 两个 BNC 口：外圈、卡口、芯
    for cx in (JACK[0] - SC[0], JACK[0] - SC[0] + 8):
        cy = JACK[1] - SC[1]
        p.d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), outline=1)
        p.px(cx, cy)
        p.px(cx - 4, cy), p.px(cx + 4, cy)
    # 两个小标识点（CH1 / CH2 下面一短一长）
    p.d.line((5, 24, 7, 24), fill=1)
    p.d.line((12, 24, 16, 24), fill=1)
    # 大旋钮的刻度圈
    kx, ky = KNOB[0] - SC[0], KNOB[1] - SC[1]
    for i in range(10):
        a = math.pi * 0.75 + i / 9 * math.pi * 1.5
        p.px(round(kx + math.cos(a) * 6), round(ky + math.sin(a) * 6))
    # 右侧网点阴影 + 底脚
    p.dither([(w - 3, 2), (w, 2), (w, h - 2), (w - 3, h - 2)], 0.5, 0)
    p.shape("rectangle", (4, h - 2, 9, h - 1), fill=1)
    p.shape("rectangle", (w - 10, h - 2, w - 5, h - 1), fill=1)
    return p.sprite()


def _handle():
    """提手 52×6"""
    p = Part(52, 6)
    p.shape("rectangle", (0, 2, 3, 5), fill=1)
    p.shape("rectangle", (48, 2, 51, 5), fill=1)
    p.shape("rectangle", (2, 0, 49, 1), fill=1)
    p.d.line((4, 1, 47, 1), fill=0)
    p.px(1, 4, 0), p.px(50, 4, 0)
    return p.sprite()


def _knob(step: int):
    """大旋钮 9×9：滚花外圈 + 指针（step 0..7 八个角度）"""
    p = Part(9, 9)
    p.shape("ellipse", (0, 0, 8, 8), fill=1)
    for i in range(8):
        a = i / 8 * 2 * math.pi + step * 0.2
        p.px(round(4 + math.cos(a) * 4), round(4 + math.sin(a) * 4), 0)
    p.d.ellipse((2, 2, 6, 6), fill=0)
    a = -math.pi / 2 + step / 8 * 2 * math.pi
    p.d.line((4, 4, 4 + math.cos(a) * 3, 4 + math.sin(a) * 3), fill=1)
    return p.sprite()


def _clip():
    """探头鳄鱼夹 6×4（夹在发髻上）"""
    p = Part(6, 4)
    p.shape("polygon", [(0, 0), (5, 1), (5, 3), (0, 3)], fill=1)
    p.d.line((1, 2, 4, 2), fill=0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        if name.startswith("knob"):
            _PROPS[name] = _knob(int(name[4:]))
        else:
            _PROPS[name] = {"scope": _scope, "handle": _handle, "clip": _clip}[name]()
    return _PROPS[name]


def _yang_rows():
    """阳鱼的扫描行：{行: [(x0, x1), ...]}（相对屏幕中心，太极角度 0）"""
    n = 2 * R + 3
    white, inside = _taiji_mask(n, R, n / 2, n / 2, 0.0)
    rows = {}
    for y in range(n):
        xs = np.nonzero(white[y])[0]
        if len(xs) == 0:
            continue
        segs, start, prev = [], xs[0], xs[0]
        for x in xs[1:]:
            if x != prev + 1:
                segs.append((start, prev))
                start = x
            prev = x
        segs.append((start, prev))
        rows[y] = segs
    return rows, n


YANG, YN = _yang_rows()


# ---------------------------------------------------------------- 画面

def room(g: Gfx):
    """背景：地砖、踢脚、墙上一卷太极挂轴（空白画心）、工作台（台面、抽屉、台腿）"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    g.d.line((1, 0, 1, FLOOR - 4), fill=1)
    x0, x1, ty = BENCH
    g.d.rectangle((x0, ty, x1, ty + 2), fill=1)
    g.d.line((x0 + 1, ty + 1, x1 - 1, ty + 1), fill=0)
    g.d.rectangle((x0 + 2, ty + 3, x0 + 4, FLOOR - 1), fill=1)       # 台腿
    g.d.rectangle((x1 - 4, ty + 3, x1 - 2, FLOOR - 1), fill=1)
    g.d.rectangle((x0 + 30, ty + 3, x1 - 10, ty + 8), outline=1)     # 抽屉
    g.d.line((x0 + 46, ty + 5, x0 + 52, ty + 5), fill=1)
    pix.checker(g, (x0 + 5, ty + 3, x1 - 4, FLOOR - 1), 0.125)


def graticule(g: Gfx, on: float = 1.0):
    """屏幕：凹框里的黑屏、点状刻度格、中心十字刻度"""
    x0, y0, x1, y1 = SCX - 21, SCY - 15, SCX + 21, SCY + 15
    g.d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=0)
    g.d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), outline=1)
    if on <= 0:
        return
    for x in range(SCX - 20, SCX + 21, 10):          # 大格：每 10 像素一点
        for y in range(SCY - 10, SCY + 11, 10):
            if on >= 1 or rand(x * 7 + y, 1) < on:
                g.px(x, y)
    if on >= 1:                                       # 中心轴：每 5 像素一道短刻度
        for i in range(-20, 21, 5):
            g.px(SCX + i, SCY)
        for i in range(-15, 16, 5):
            g.px(SCX, SCY + i)


def label(g: Gfx, x: float, y: float, s: str, align: str = "left"):
    """屏幕角上的读数（黑底，免得被刻度点压住）"""
    w = len(s) * 4 - 1
    x0 = x if align == "left" else x - w
    g.d.rectangle((x0 - 1, y - 1, x0 + w, y + 5), fill=0)
    tiny(g, x0, y, s)


def scope(g: Gfx, knob: int):
    pix.blit(g, prop("handle"), SC[0] + 9, SC[1] - 5)
    pix.blit(g, prop("scope"), SC[0], SC[1])
    pix.blit(g, prop(f"knob{knob % 8}"), KNOB[0] - 4, KNOB[1] - 4, outline=False)


def power_led(g: Gfx, on: bool):
    if on:
        g.d.rectangle((SC[0] + 6, SC[1] + 6, SC[0] + 8, SC[1] + 7), fill=1)


def cable(g: Gfx, head):
    """探头线：CH1 口 → 弯一道弧 → 发髻上的鳄鱼夹"""
    hx, hy = head
    x0, y0 = JACK
    pts = []
    for i in range(13):
        k = i / 12
        cx, cy = (x0 + hx) / 2 - 2, min(y0, hy) - 12
        x = (1 - k) ** 2 * x0 + 2 * (1 - k) * k * cx + k * k * hx
        y = (1 - k) ** 2 * y0 + 2 * (1 - k) * k * cy + k * k * hy
        pts.append((x, y))
    g.d.line(pts, fill=1)
    pix.blit(g, prop("clip"), hx - 2, hy - 2)


def s_point(s: float, r: float):
    """S 形分界上的点（s 0..1，从顶到底）"""
    if s < 0.5:
        ph = -math.pi / 2 - math.pi * 2 * s
        return SCX + r / 2 * math.cos(ph), SCY - r / 2 + r / 2 * math.sin(ph)
    ph = -math.pi / 2 + math.pi * (2 * s - 1)
    return SCX + r / 2 * math.cos(ph), SCY + r / 2 + r / 2 * math.sin(ph)


def circ(a: float, r: float, noise: float = 0.0, t: float = 0.0, i: int = 0):
    x, y = SCX + math.cos(a) * r, SCY + math.sin(a) * r
    if noise:
        x += (rand(int(t * 30) * 97 + i, 5) - 0.5) * noise * 2
        y += (rand(int(t * 30) * 89 + i, 6) - 0.5) * noise * 2
    return x, y


def orbit(g: Gfx, head: float, tail: float, r: float = R, noise: float = 0.0, t: float = 0.0, fade: float = 1.0,
          beam: bool = True):
    """电子束绕圈：head 角，tail 余辉弧长（弧度）；越往后越稀（像素的“余辉”）。fade 0..1 整体余辉亮度"""
    n = max(2, int(tail * r * 1.6))
    for i in range(n):
        back = i / max(n - 1, 1)
        if back > fade:
            break
        if back > 0.6 and i % 2:
            continue
        if back > 0.85 and i % 4:
            continue
        x, y = circ(head - i / (r * 1.6), r, noise, t, i)
        g.px(x, y)
        if back < 0.12:  # 刚扫过的一段更亮（2 像素粗）
            x2, y2 = circ(head - i / (r * 1.6), r - 1, noise, t, i)
            g.px(x2, y2)
    if beam:
        x, y = circ(head, r, noise, t, 999)
        g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
        g.px(x - 2, y), g.px(x + 2, y), g.px(x, y - 2), g.px(x, y + 2)


def s_curve(g: Gfx, upto: float, r: float = R):
    for i in range(int(upto * 40) + 1):
        x, y = s_point(i / 40, r)
        g.px(x, y)


def eyes(g: Gfx, k: float):
    """两只鱼眼：阳鱼（右上）里一个暗眼、阴鱼（左下）里一个亮眼；k 0..1 长出来"""
    rr = 2 * k
    if rr < 0.5:
        return
    g.d.ellipse((SCX - rr, SCY - R / 2 - rr, SCX + rr, SCY - R / 2 + rr), outline=1)
    g.d.ellipse((SCX - rr, SCY + R / 2 - rr, SCX + rr, SCY + R / 2 + rr), fill=1)


def yang_fill(g: Gfx, p: float, t: float):
    """扫描线一行行把阳鱼填亮：先隔 4 行、再隔 2 行、最后每行；返回扫描行 y（画扫描亮线）"""
    ox, oy = int(round(SCX - YN / 2)), int(round(SCY - YN / 2))
    passes = ((4, 0.0, 0.34), (2, 0.34, 0.67), (1, 0.67, 1.0))
    scan = None
    for step, a, b in passes:
        q = span(p, a, b)
        if q <= 0:
            continue
        lim = q * YN
        for y, segs in YANG.items():
            if y % step:
                continue
            if y > lim:
                if q < 1 and scan is None:
                    scan = oy + y
                break
            for x0, x1 in segs:
                g.d.line((ox + x0, oy + y, ox + x1, oy + y), fill=1)
    if scan is not None:  # 正在扫的那一行：一道亮线扫过
        sx = SCX - R + (t * 60) % (2 * R)
        g.d.line((sx - 3, scan, sx + 3, scan), fill=1)
    # 阳鱼里的暗眼要挖出来
    g.d.ellipse((SCX - 2, SCY - R / 2 - 2, SCX + 2, SCY - R / 2 + 2), fill=0)
    g.d.ellipse((SCX - 2, SCY - R / 2 - 2, SCX + 2, SCY - R / 2 + 2), outline=1)


def mx_wave(g: Gfx, t: float, amp: float):
    for x in range(8):
        y = 3.5 + amp * math.sin((x + t * 6) * 0.8)
        g.mx_set(x, int(round(y)))


@register
class Scope(R6):
    id = "r6.scope"
    name = "示波太极"
    desc = "小道士把示波器探头夹在发髻上拧旋钮，X-Y 模式下的李萨如圆一段段长成太极：无极、太极、生阳、两仪"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 6.0}
    CYCLE = 600.0

    def stage(self, k: float) -> int:
        return min(3, int(k / (self.CYCLE / 4)))

    def angle3(self, k3: float) -> float:
        """两仪段太极的转角（越转越快）"""
        return 0.3 * k3 + 0.5 * (1.7 / 150) * k3 * k3

    def screen(self, g: Gfx, k: float, t: float, noise: float = 0.0, rscale: float = 1.0, fade: float = 1.0,
               beam: bool = True, head: float | None = None):
        """按本轮进度 k 画屏幕上的图形"""
        st = self.stage(k)
        Q = self.CYCLE / 4
        r = R * rscale
        hd = k * OMEGA if head is None else head
        if st == 0:
            tail = lerp(0.6, 2 * math.pi, min(k / Q * 1.15, 1.0))
            orbit(g, hd, tail, r, noise, t, fade, beam)
        elif st == 1:
            orbit(g, hd, 2 * math.pi, r, noise, t, fade, beam=False)
            p = (k - Q) / Q
            s_curve(g, p, r)
            if beam:
                x, y = s_point(p, r)
                g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
        elif st == 2:
            orbit(g, hd, 2 * math.pi, r, noise, t, fade, beam=False)
            s_curve(g, 1.0, r)
            p = (k - 2 * Q) / Q
            eyes(g, span(p, 0.0, 0.08))
            if p > 0.08:
                yang_fill(g, span(p, 0.08, 1.0), t)
        else:
            a = self.angle3(k - 3 * Q)
            taiji(g, SCX, SCY, r, a)
            if noise:
                for i in range(int(noise * 10)):
                    g.px(SCX + (rand(int(t * 30) * 13 + i, 2) - 0.5) * 2 * R, SCY + (rand(int(t * 30) * 17 + i, 3) - 0.5) * 2 * R)

    def mx(self, g: Gfx, k: float, t: float, amp_k: float = 1.0):
        st = self.stage(k)
        if st < 3:
            mx_wave(g, t, (1.0 + st * 0.9) * amp_k)
        else:
            mx_taiji(g, self.angle3(k - 3 * self.CYCLE / 4))

    def dao_knob(self, g: Gfx, t: float, face: str = "normal", turn: bool = True):
        """小道士拧大旋钮：手臂伸到旋钮上，一拧一拧；返回旋钮指针档"""
        step = int(t / 0.7) if turn else 0
        wig = 2 if step % 2 else -1
        dao(g, DX, FLOOR, t, angle=24 + wig, length=11, face=face)
        return step

    def head(self):
        return (DX + 2, FLOOR - 32)

    def counter(self, g: Gfx, n: int, label: str | None = None):
        badge(g, label or nth(n, "周"))

    def stage_text(self, g: Gfx, k: float):
        g.text(4, 16, STAGE[self.stage(k)], size=12)

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        room(g)
        on = t > 3.0
        scope(g, 0)
        power_led(g, on)
        graticule(g, span(t, 3.4, 4.2) if on else 0)
        if 3.0 < t < 3.6:  # 开机：一道亮线横扫
            q = span(t, 3.0, 3.4)
            hw = int(20 * ease_out(q))
            yy = SCY
            g.d.line((SCX - hw, yy, SCX + hw, yy), fill=1)
            if t > 3.4:
                g.d.line((SCX - 20, yy - 1, SCX + 20, yy + 1), fill=1)
        if t > 4.4:
            orbit(g, (t - 6.0) * OMEGA, min(0.6, (t - 4.4) * 1.2), R * ease_out_back(span(t, 4.4, 5.0)), t=t)
        # 小道士：走来 → 举手夹探头 → 按电源 → 拧旋钮
        if t < 2.0:
            x = lerp(-12, DX, ease_out(span(t, 0, 2.0)))
            dao(g, x, FLOOR, t, pose="walk")
            # 探头线还挂在 CH1 口上垂着
            g.d.line((JACK[0], JACK[1], JACK[0] - 3, JACK[1] + 8, JACK[0] - 4, BENCH[2] - 1), fill=1)
            pix.blit(g, prop("clip"), JACK[0] - 7, BENCH[2] - 4)
        elif t < 2.9:
            h = dao(g, DX, FLOOR, t, pose="raise", face="wow" if t > 2.5 else "normal")
            if t < 2.5:
                hx, hy = h["hand"]
                cable(g, (hx, hy))
            else:
                cable(g, self.head())
            if abs(t - 2.5) < dt * 0.6:
                self.sparks.burst(*self.head(), 10, 24, up=10, life=0.5)
                pix.shake(g, t, 1.2)
        else:
            if t < 3.4:
                dao(g, DX, FLOOR, t, angle=lerp(-10, 30, span(t, 2.9, 3.1)), length=11, hand="point",
                    face="happy")
            else:
                self.dao_knob(g, t, face="happy" if t > 4.4 else "normal")
            cable(g, self.head())
        if abs(t - 3.0) < dt * 0.6:
            self.sparks.burst(SC[0] + 7, SC[1] + 6, 6, 16, life=0.4)
        self.fx(g, dt)
        if t > 3.4:
            mx_wave(g, t, 1.0 * span(t, 3.4, 4.4))
        else:
            g.mx[3, :] = [x <= t * 2.5 for x in range(8)]
        if t > 4.4:
            self.counter(g, 1)
            self.stage_text(g, 0)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        n = int(e // self.CYCLE) + 1
        if e >= self.CYCLE and k < RENEW:
            self.renew(g, t, e, k, dt)
            return
        room(g)
        ph = t % LOOP
        loop = int(t // LOOP)
        noisy = loop % 2 == 1 and 18 < ph < 21.5
        nk = ph - 18
        breath = loop % 2 == 0 and 18 < ph < 23
        bk = ph - 18
        noise = 0.0
        if noisy:
            noise = 3.0 if nk < 1.6 else 3.0 * (1 - span(nk, 1.6, 2.0))
        rs = 1.0 + (0.22 * math.sin(math.pi * span(bk, 0, 5)) if breath else 0.0)
        slapping = noisy and 0.6 < nk < 2.4
        breathing = breath and 0.4 < bk < 4.6
        knob_step = int(t / 0.7) if not (slapping or breathing) else 0
        scope(g, knob_step)
        power_led(g, True)
        graticule(g)
        self.screen(g, k, t, noise=noise, rscale=rs)
        # 小道士（画在示波器前面）
        if slapping:
            slap = span(nk, 1.2, 1.6)
            a = lerp(40, 5, ease_in(slap)) if nk < 1.6 else 8
            dao(g, DX - 1, FLOOR, t, angle=a, length=9, hand="open", face="wow" if nk < 1.6 else "normal")
        elif breathing:
            dao(g, DX, FLOOR, t, pose="gong", face="sleep")
        else:
            self.dao_knob(g, t, face="wow" if noisy else "normal")
        cable(g, self.head())
        label(g, SCX - 19, SCY - 13, "X-Y")
        if noisy and nk < 1.6 and int(t * 6) % 2:
            label(g, SCX + 19, SCY - 13, "!", align="right")
        if noisy and abs(nk - 1.6) < dt * 0.6:   # 拍机壳：震屏 + 火星
            self.sparks.burst(SC[0] + 1, SC[1] + 26, 12, 30, up=10, life=0.5)
            pix.shake(g, t, 2)
        if noisy and 1.6 < nk < 1.9:
            pix.shake(g, t, 1.2)
        if breath and 0.4 < bk < 4.6 and int(t * 30) % 10 == 0:  # 吸气：几点灵气往发髻上聚
            hx, hy = self.head()
            self.sparks.burst(hx, hy - 4, 1, 10, up=6, life=0.6, gravity=-10)
        self.fx(g, dt)
        self.mx(g, k, t, rs)
        self.counter(g, n)
        self.stage_text(g, k)

    def renew(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """一轮满：太极急转 → 缩成一点（归一）→ 涨回一个圆"""
        n = int(e // self.CYCLE)
        room(g)
        scope(g, int(t / 0.7) if k > 2.6 else 0)
        power_led(g, True)
        graticule(g)
        a0 = self.angle3(self.CYCLE / 4)
        if k < 2.6:
            spin = a0 + 30 * k * k
            r = R * (1 - ease_in(span(k, 1.4, 2.6)))
            if r >= 1.5:
                taiji(g, SCX, SCY, r, spin)
            else:
                g.d.rectangle((SCX - 1, SCY - 1, SCX + 1, SCY + 1), fill=1)
            dao(g, DX, FLOOR, t, pose="gong" if k < 1.4 else "bow")
            cable(g, self.head())
            if abs(k - 2.6) < dt * 0.6:
                pix.flash(g)
                self.sparks.burst(SCX, SCY, 16, 30, life=0.6, gravity=0)
            if 2.6 > k > 2.2:
                glow_rays(g, SCX, SCY, 3, 3 + 8 * span(k, 2.2, 2.6), 8, k, 1.0, dashed=True)
            mx_taiji(g, spin) if r > 4 else g.mx_set(3, 3)
        else:
            rr = R * ease_out_back(span(k, 2.8, 3.6))
            if k < 2.8:
                g.d.rectangle((SCX - 1, SCY - 1, SCX + 1, SCY + 1), fill=1)
                glow_rays(g, SCX, SCY, 3, 6, 8, k * 3, 1.0)
            else:
                orbit(g, k * OMEGA, 0.6, rr, t=t)
            self.dao_knob(g, t, face="happy")
            cable(g, self.head())
            mx_wave(g, t, span(k, 2.8, 4.0))
        label(g, SCX - 19, SCY - 13, "X-Y")
        self.fx(g, dt)
        if k < 2.6:
            self.counter(g, n)
        else:
            self.counter(g, n + 1)
            g.text(4, 16, "归一" if k < 4.0 else STAGE[0], size=12)

    # ------------------------------------------------------------ 中断 / 恢复

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        room(g)
        scope(g, int(t / 0.7) if t < 0.4 else 0)
        power_led(g, True)
        graticule(g)
        fade = 1 - span(t, 0.3, 1.5) * 0.85
        head = (k + min(t, 0.3)) * OMEGA
        self.screen(g, k, t, fade=fade, head=head, beam=True)
        if t < 0.4:
            self.dao_knob(g, t)
        else:
            dao(g, DX, FLOOR, t, pose="gong" if t > 0.7 else "down")
        cable(g, self.head())
        label(g, SCX - 19, SCY - 13, "X-Y")
        if t > 0.3 and int(t * 4) % 2 == 0:
            label(g, SCX + 20, SCY - 13, "STOP", align="right")
        self.fx(g, dt)
        if self.stage(k) < 3:
            mx_wave(g, 0.3, 1.0 + self.stage(k) * 0.9)
        else:
            self.mx(g, k, 0)
        self.counter(g, int(e // self.CYCLE) + 1, "暂停" if t > 0.3 else None)
        self.stage_text(g, k)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        room(g)
        scope(g, int(t / 0.7) if t >= 0.6 else 0)
        power_led(g, True)
        graticule(g)
        fade = 0.15 + 0.85 * span(t, 0.6, 1.4)
        if t < 0.6:
            self.screen(g, k, t, fade=0.15, head=k * OMEGA)
        else:
            self.screen(g, k, t, fade=fade)
        if t < 0.6:
            dao(g, DX, FLOOR, t, pose="gong")
        else:
            self.dao_knob(g, t, face="happy" if t < 1.4 else "normal")
        cable(g, self.head())
        if abs(t - 0.6) < dt * 0.6:
            self.sparks.burst(SCX, SCY, 8, 20, life=0.4, gravity=0)
            pix.shake(g, t, 1)
        label(g, SCX - 19, SCY - 13, "X-Y")
        if 0.6 < t < 1.4:
            label(g, SCX + 20, SCY - 13, "RUN", align="right")
        elif t <= 0.6 and int(t * 4) % 2 == 0:
            label(g, SCX + 20, SCY - 13, "STOP", align="right")
        self.fx(g, dt)
        self.mx(g, k, t)
        self.counter(g, int(e // self.CYCLE) + 1, "暂停" if t < 0.6 else None)
        self.stage_text(g, k)

    # ------------------------------------------------------------ 圆满

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        room(g)
        scope(g, int(t * 3) if t < 2.4 else 0)
        power_led(g, True)
        graticule(g)
        a = self.angle3(k - 3 * self.CYCLE / 4) if self.stage(k) == 3 else 0.0
        if t < 1.2:  # 补完：剩下的阶段一口气走完
            p = span(t, 0, 1.2)
            if self.stage(k) < 3:
                kk = lerp(k, 3 * self.CYCLE / 4, p)
                self.screen(g, kk, t * 3)
            else:
                taiji(g, SCX, SCY, R, a + t * 3)
        label(g, SCX - 19, SCY - 13, "X-Y")
        if t < 2.4:
            self.dao_knob(g, t * 2, face="wow" if t > 1.2 else "normal")
            cable(g, self.head())
        cx, cy, r = SCX, SCY, R
        spin = a + 3.6 + 22 * span(t, 1.2, 2.4) ** 2 + 6 * max(0.0, t - 2.4)
        if t >= 2.4:  # 房间淡成黑，太极从屏幕里浮出来放大；小道士跪拜
            g.fade(1 - span(t, 2.4, 3.0))
            q = ease_in_out(span(t, 2.4, 3.4))
            cx, cy, r = lerp(SCX, 90, q), lerp(SCY, 36, q), lerp(R, 14, q)
            g.d.line((0, FLOOR, 127, FLOOR), fill=1)
            if t > 3.0:
                pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
            dao(g, DX - 8, FLOOR, t, pose="kneel" if t < 4.9 else "gong", face="happy")
        if t >= 1.2:
            g.d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), fill=0)
            taiji(g, cx, cy, r, spin)
        if t >= 3.4:
            glow_rays(g, cx, cy, r + 4, r + 8, 16, t * 0.8, 1.0, dashed=True)
        if abs(t - 2.4) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst(SCX, SCY, 24, 44, up=10, life=1.0, gravity=20)
        if 2.4 < t < 2.8:
            pix.shake(g, t, 1.6)
        self.fx(g, dt)
        mx_taiji(g, spin if t >= 1.2 else a)
        g.mx_level = 2 if t < 2.4 else 1 + int(6 * (1 - span(t, 2.4, 3.8)))
        if t < 2.4:
            self.counter(g, int(e // self.CYCLE) + 1)
            self.stage_text(g, 3 * self.CYCLE / 4 if t > 0.6 else k)
        banner(g, 64, 3, "一阴一阳之谓道", span(t, 3.4, 3.8), t=t, stars=False)
