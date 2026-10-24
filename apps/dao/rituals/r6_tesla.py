"""雷法除虫（像素风）：特斯拉线圈作五雷正法，小道士执法剑指挥雷霆，爬过来的 bug（程序里的“精怪”）一靠近就被劈成灰。

依据：雷法（五雷正法）是宋以后神霄、清微等派的核心法术，役使雷霆以驱邪；
《金光神咒》：“役使雷霆，鬼妖丧胆，精怪亡形。”这里把精怪换成了软件 bug，雷劈 = debug。

入场：小道士提剑走进来，举剑一指，线圈底座的开关“咔”地合上，次级绕线自下而上一圈圈亮起，
      顶环一闪，第一道雷劈到地上（闪白、震屏、火星），细电弧开始在顶环四周噼啪。
持续：每 12 秒一只 bug 从右边爬来（地上的甲虫、空中扑腾的飞蛾，偶尔一只大甲虫），小道士剑尖一指，
      一道长电弧劈中，闪白、震屏，bug 炸成碎屑、地上留一点焦痕冒烟，右上“BUG”计数加一；
      空档里小道士举剑“引雷入剑”（顶环一道电弧接到剑尖，火花顺剑身乱窜）或收剑拱手；右侧 KV 蓄能条一轮 10 分钟充满。
      一轮满：小道士举剑，五道巨雷接连劈下、全屏反色，蓄能清零，“第几雷”加一。
中断：开关跳闸，电弧缩回顶环，绕线自上而下熄灭，bug 原地僵住，“断电”。
恢复：开关合上，绕线逐圈亮回，顶环闪烁，电弧重新长出来。
圆满：蓄能冲满，四只 bug 同时现身，万雷齐发一齐劈中，闪白震屏，线圈放光，“精怪亡形”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part
from ..engine.fx import lightning
from ..engine.gfx import Gfx
from ..engine.scene import register
from .r6_common import R6, badge, banner, dao, glow_rays, nth, pixsmoke, tiny, tiny_w

FLOOR = 58
CX = 82                 # 线圈中心
TORUS_Y = 10            # 顶环精灵顶
SEC_TOP, SEC_BOT = 18, 45   # 次级线圈
BASE_Y = 42             # 底座精灵顶（含初级线圈）
DAO_X = 24
P = 12.0                # 每只 bug 的周期
CRAWL0, STRIKE = 5.0, 9.0   # 本周期里 bug 出现 / 被劈的时刻
RENEW = 5.0
BAR = (121, 16, 125, 53)    # KV 蓄能条


# ---------------------------------------------------------------- 道具

def _torus():
    """放电顶环 27×9：扁圆环，顶上看得见中间的孔，侧面一道反光、下半网点阴影"""
    p = Part(27, 9)
    p.shape("ellipse", (0, 0, 26, 8), fill=1)
    p.d.ellipse((8, 1, 18, 4), fill=0)
    p.d.arc((8, 1, 18, 5), 0, 180, fill=1)
    p.d.line((3, 5, 6, 6), fill=0)
    p.d.line((20, 6, 23, 5), fill=0)
    p.dither([(2, 6), (24, 6), (22, 8), (4, 8)], 0.5, 0)
    p.px(4, 2, 0), p.px(5, 2, 0)            # 高光边上的一道暗缝（显出圆管）
    return p.sprite()


def _base():
    """底座 27×16：初级线圈（扁平螺旋，三圈）、托板、电源箱（散热格栅、开关盒、四颗螺栓）、脚"""
    p = Part(27, 16)
    p.shape("ellipse", (0, 0, 26, 5), fill=1)
    p.d.ellipse((1, 1, 25, 4), fill=0)
    p.d.ellipse((4, 1, 22, 4), outline=1)
    p.d.ellipse((8, 2, 18, 3), outline=1)
    p.d.line((10, 2, 16, 2), fill=0)
    p.shape("rectangle", (2, 5, 24, 6), fill=1)            # 托板
    p.d.line((3, 6, 23, 6), fill=0)
    p.shape("rectangle", (1, 7, 25, 14), fill=1)           # 电源箱
    p.d.rectangle((3, 9, 14, 12), fill=0)                  # 格栅
    for x in range(4, 14, 2):
        p.d.line((x, 10, x, 11), fill=1)
    p.d.rectangle((17, 8, 23, 13), fill=0)                 # 开关盒
    p.d.rectangle((18, 9, 22, 12), outline=1)
    for x, y in ((2, 8), (24, 8), (2, 13), (24, 13)):
        p.px(x, y, 0)
    p.dither([(15, 13), (25, 13), (25, 14), (15, 14)], 0.5, 0)
    for x in (2, 22):
        p.shape("rectangle", (x, 15, x + 2, 15), fill=1)
    return p.sprite()


def _sign():
    """墙上的高压警示牌 11×10：三角框里一道闪电"""
    p = Part(11, 10)
    p.shape("polygon", [(5, 0), (10, 9), (0, 9)], fill=1)
    p.d.polygon([(5, 2), (8, 8), (2, 8)], fill=0)
    p.d.line((6, 3, 4, 6), fill=1)
    p.d.line((4, 6, 6, 6), fill=1)
    p.d.line((6, 6, 5, 8), fill=1)
    return p.sprite()


def _fu():
    """墙上贴的雷符 7×17：符纸 + 符头三勾 + 竖笔 + 符脚"""
    p = Part(7, 17)
    p.shape("rectangle", (0, 0, 6, 16), fill=1)
    p.d.line((1, 2, 5, 2), fill=0)
    p.px(2, 1, 0), p.px(4, 1, 0)
    p.d.line((3, 4, 3, 12), fill=0)
    p.d.line((1, 6, 5, 6), fill=0)
    p.d.line((1, 9, 5, 8), fill=0)
    p.d.line((2, 13, 1, 15), fill=0)
    p.d.line((4, 13, 5, 15), fill=0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"torus": _torus, "base": _base, "sign": _sign, "fu": _fu}[name]()
    return _PROPS[name]


def _beetle(f: int):
    """甲虫 13×9（朝左爬）：圆甲壳（中缝、斑点、背光网点）、小头、触角、三条腿交替迈步"""
    p = Part(13, 9)
    p.shape("ellipse", (3, 0, 12, 7), fill=1)
    p.d.line((5, 2, 8, 1), fill=0)
    p.d.line((8, 1, 11, 3), fill=0)
    p.px(6, 4, 0), p.px(9, 3, 0), p.px(10, 5, 0)
    p.dither([(4, 5), (12, 5), (11, 7), (5, 7)], 0.5, 0)
    p.shape("ellipse", (0, 3, 4, 6), fill=1)
    p.px(1, 4, 0)
    p.shape("line", (1, 3, 0, 0), fill=1)
    p.shape("line", (2, 3, 3, 1), fill=1)
    for k, x in enumerate((4, 7, 10)):
        d = 1 if (k + f) % 2 else -1
        p.shape("line", (x, 7, x + d, 8), fill=1)
    return p.sprite()


def _moth(f: int):
    """飞蛾 11×8：毛茸茸的身子、两片带眼斑的翅膀（上下扇）、触角"""
    p = Part(11, 8)
    if f == 0:
        p.shape("polygon", [(5, 4), (0, 0), (1, 4)], fill=1)
        p.shape("polygon", [(5, 4), (10, 0), (9, 4)], fill=1)
        p.px(2, 2, 0), p.px(8, 2, 0)
    else:
        p.shape("polygon", [(5, 3), (0, 6), (2, 7)], fill=1)
        p.shape("polygon", [(5, 3), (10, 6), (8, 7)], fill=1)
        p.px(2, 6, 0), p.px(8, 6, 0)
    p.shape("ellipse", (4, 2, 6, 7), fill=1)
    p.px(5, 4, 0)
    p.shape("line", (4, 2, 3, 0), fill=1)
    p.shape("line", (6, 2, 7, 0), fill=1)
    return p.sprite()


BEETLE = [_beetle(0), _beetle(1)]
MOTH = [_moth(0), _moth(1)]


# ---------------------------------------------------------------- 画面

def room(g: Gfx):
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 12):
        g.d.line((x, FLOOR + 1, x - 8, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    pix.blit(g, prop("fu"), 44, 14)
    g.d.line((47, 11, 47, 13), fill=1)
    pix.blit(g, prop("sign"), 56, 26)


def secondary(g: Gfx, lit: float, t: float, flicker: bool = False):
    """次级线圈：细密的绕线（每两行一圈）。lit 0..1：从下往上亮到哪；没亮的绕线只剩虚点"""
    x0, x1 = CX - 3, CX + 3
    g.d.rectangle((x0 - 1, SEC_TOP, x1 + 1, SEC_BOT), fill=0)
    n = SEC_BOT - SEC_TOP
    for i in range(n + 1):
        y = SEC_BOT - i
        on = i <= lit * n
        if flicker and rand(int(t * 20) + i // 4, 5) < 0.3:
            on = False
        g.px(x0, y), g.px(x1, y)
        if y % 2 == 0:
            if on:
                g.d.line((x0, y, x1, y), fill=1)
                if (x1 - 1 + y // 2) % 2:
                    g.px(x1 - 1, y, 0)
            else:
                g.px(x0 + 2, y), g.px(x0 + 4, y)
        elif on:
            g.px(x0 + 1, y)


def coil(g: Gfx, lit: float, t: float, on: bool, flicker: bool = False):
    secondary(g, lit, t, flicker)
    pix.blit(g, prop("base"), CX - 13, BASE_Y)
    pix.blit(g, prop("torus"), CX - 13, TORUS_Y)
    sx, sy = CX - 13 + 20, BASE_Y + 10             # 开关
    if on:
        g.d.line((sx, sy + 1, sx + 1, sy - 2), fill=1)
        g.px(sx - 1, sy - 1, int(t * 3) % 2)
    else:
        g.d.line((sx, sy - 1, sx + 1, sy + 2), fill=1)
    if flicker and int(t * 15) % 2:
        g.d.ellipse((CX - 13, TORUS_Y, CX + 13, TORUS_Y + 8), outline=1)
        pix.checker(g, (CX - 11, TORUS_Y + 1, CX + 12, TORUS_Y + 8), 0.5, fill=0)


def ambient_arcs(g: Gfx, t: float, scale: float, seed: int = 0, n: int = 3):
    """顶环四周噼啪的细电弧（每 2 帧换一次形）"""
    if scale <= 0.05:
        return
    step = int(t * 15)
    for j in range(n):
        r = rand(step * 7 + j, seed)
        if r < 0.15:
            continue
        a = math.pi + rand(step * 13 + j * 5, seed + 1) * math.pi * 1.3 - 0.15   # 偏上半边
        x0 = CX + math.cos(a) * 13
        y0 = TORUS_Y + 4 + math.sin(a) * 4
        ln = (5 + 9 * rand(step * 3 + j, seed + 2)) * scale
        x1 = x0 + math.cos(a) * ln
        y1 = y0 + math.sin(a) * ln * 0.9 - 2
        lightning(g, x0, y0, x1, y1, seed=step * 11 + j, jag=2.0, branches=1 if r > 0.6 else 0)


def bolt(g: Gfx, x0, y0, x1, y1, seed, width: int = 1):
    """一道长雷：先描黑边再画白芯"""
    lightning(g, x0, y0, x1, y1, seed=seed, jag=5.0, branches=2, width=width)


def sword(g: Gfx, hx: float, hy: float, ang: float, t: float, sparks: bool = False):
    """法剑：剑身（两像素宽、剑尖一点）、剑格、剑柄、剑穗随风摆"""
    a = math.radians(ang)
    ux, uy = math.cos(a), -math.sin(a)
    nx, ny = -uy, ux
    tip = (hx + ux * 16, hy + uy * 16)
    g.d.line((hx + ux * 2, hy + uy * 2, tip[0], tip[1]), fill=0, width=4)
    g.d.line((hx + ux * 2, hy + uy * 2, hx + ux * 14, hy + uy * 14), fill=1, width=2)
    g.px(round(tip[0]), round(tip[1]))
    gx, gy = hx + ux * 2.5, hy + uy * 2.5
    g.d.line((gx - nx * 3, gy - ny * 3, gx + nx * 3, gy + ny * 3), fill=1)
    g.d.line((hx - ux * 2, hy - uy * 2, hx, hy), fill=1)
    px_, py_ = hx - ux * 3, hy - uy * 3
    g.d.rectangle((px_ - 1, py_ - 1, px_ + 1, py_ + 1), fill=1)
    sw = math.sin(t * 4) * 1.5
    g.d.line((px_, py_ + 1, px_ + sw * 0.5, py_ + 3, px_ + sw, py_ + 5), fill=1)
    g.px(px_ + sw - 1, py_ + 6), g.px(px_ + sw + 1, py_ + 6)
    if sparks:   # 火花顺剑身乱窜
        for j in range(3):
            k = (t * 3 + j / 3) % 1
            sx, sy = hx + ux * (3 + k * 12), hy + uy * (3 + k * 12)
            o = (rand(int(t * 20) + j, 4) - 0.5) * 6
            g.px(sx + nx * o, sy + ny * o)
            g.px(sx + nx * o * 0.5, sy + ny * o * 0.5)
    return tip


def bug_pos(i: int, u: float, kind: str, seed: int):
    """第 i 只 bug 在本周期 u 秒时的位置（左上角）"""
    q = span(u, crawl0(i), STRIKE)
    if kind == "moth":
        x = lerp(132, 104, ease_out(q))
        y = 24 + math.sin(u * 5 + i) * 4 + rand(i, seed) * 6
        return x, y
    x = lerp(132, 102, q)
    return x, FLOOR - (18 if kind == "big" else 9)


def crawl0(i: int) -> float:
    return CRAWL0 if i == 0 else 3.0


def bug_kind(i: int, seed: int) -> str:
    if i % 6 == 5:
        return "big"
    return "moth" if rand(i * 3 + 1, seed) < 0.45 else "beetle"


def draw_bug(g: Gfx, kind: str, x: float, y: float, clock: float):
    if kind == "moth":
        pix.blit(g, pix.anim(MOTH, clock, 9), x, y)
    elif kind == "big":
        pix.blit(g, _big(int(clock * 3) % 2), x, y)
    else:
        pix.blit(g, pix.anim(BEETLE, clock, 5), x, y)


_BIG: dict = {}


def _big(i: int):
    if i not in _BIG:
        _BIG[i] = BEETLE[i].scale(2)
    return _BIG[i]


def bug_center(kind: str, x: float, y: float):
    if kind == "moth":
        return x + 5, y + 4
    if kind == "big":
        return x + 14, y + 7
    return x + 7, y + 4


def hud(g: Gfx, charge: float, count: int, t: float, blink: bool = False):
    """右边 KV 蓄能条 + 右上 BUG 计数（3×5 小字，黑底）"""
    x0, y0, x1, y1 = BAR
    g.d.rectangle((x0 - 1, y0 - 8, x1 + 1, y1 + 1), fill=0)
    tiny(g, x0 - 1, y0 - 7, "KV")
    g.d.rectangle((x0, y0, x1, y1), outline=1)
    h = int((y1 - y0 - 2) * max(0.0, min(charge, 1.0)))
    if h > 0 and not (blink and int(t * 6) % 2):
        g.d.rectangle((x0 + 2, y1 - 1 - h, x1 - 2, y1 - 2), fill=1)
    for y in range(y0 + 4, y1, 6):
        g.px(x0 - 1, y)
    s = f"BUG{min(count, 999):03d}"
    w = tiny_w(s)
    g.d.rectangle((126 - w - 2, 0, 127, 8), fill=0)
    tiny(g, 126 - w, 2, s)


def mx_bolt(g: Gfx, charge: float, t: float, on: bool = True, full: bool = False):
    """点阵：闪电图标（偶尔闪一下）+ 右列蓄能"""
    if full:
        g.mx[:] = True
        return
    rows = [0b00011000, 0b00110000, 0b01100000, 0b01111000, 0b00011000, 0b00110000, 0b01100000, 0b01000000]
    if on and rand(int(t * 12), 8) > 0.12:
        g.mx_rows(rows)
    elif not on:   # 断电：只剩虚的轮廓
        g.mx_rows([r & (0x55 if y % 2 else 0xAA) for y, r in enumerate(rows)])
    h = int(round(charge * 8))
    for r in range(8):
        g.mx[r, 7] = r >= 8 - h


@register
class Tesla(R6):
    id = "r6.tesla"
    name = "雷法除虫"
    desc = "小道士执法剑指挥特斯拉线圈，爬来的 bug 一靠近就被一道电弧劈成碎屑；蓄满五雷齐落"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def init(self):
        self.last_k = None

    def charge(self, e: float) -> float:
        return (e % self.CYCLE) / self.CYCLE

    def kills(self, e: float) -> int:
        """本周期之前累计 + 本周期已劈的数量"""
        per = int((self.CYCLE - STRIKE) // P) + 1
        k = e % self.CYCLE
        now = int((k - STRIKE) // P) + 1 if k >= STRIKE else 0
        return int(e // self.CYCLE) * per + now

    def counter(self, g: Gfx, e: float, label: str | None = None):
        badge(g, label or nth(int(e // self.CYCLE) + 1, "雷"))

    def idle_dao(self, g: Gfx, t: float, face: str = "normal"):
        h = dao(g, DAO_X, FLOOR, t, angle=-20, face=face)
        sword(g, h["hand"][0], h["hand"][1], 62, t)

    def point_dao(self, g: Gfx, t: float, target, face: str = "normal", sparks: bool = False):
        hx0, hy0 = DAO_X + 10, FLOOR - 16
        ang = math.degrees(math.atan2(-(target[1] - hy0), target[0] - hx0))
        h = dao(g, DAO_X, FLOOR, t, angle=max(-15, min(30, ang)), face=face)
        return sword(g, h["hand"][0], h["hand"][1], ang, t, sparks)

    def raise_dao(self, g: Gfx, t: float, face: str = "normal", sparks: bool = False):
        h = dao(g, DAO_X, FLOOR, t, pose="raise", face=face)
        return sword(g, h["hand"][0] - 1, h["hand"][1] + 1, 88, t, sparks)

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        room(g)
        on = t >= 2.2
        lit = ease_out(span(t, 2.2, 3.4))
        coil(g, lit, t, on, flicker=3.1 < t < 3.4)
        if abs(t - 2.2) < dt * 0.6:
            self.sparks.burst(CX + 7, BASE_Y + 9, 10, 26, up=12, life=0.4)
        if 2.2 < t < 2.4:
            pix.shake(g, t, 1)
        if t >= 3.4:
            ambient_arcs(g, t, span(t, 3.6, 5.0), self.seed)
        if 3.4 <= t < 3.75:                       # 第一道雷劈到地上
            bolt(g, CX - 12, TORUS_Y + 5, 58, FLOOR - 1, int(t * 30), width=2 if t < 3.55 else 1)
            if t < 3.47:
                pix.flash(g)
            pix.shake(g, t, 2)
        if abs(t - 3.4) < dt * 0.6:
            self.sparks.burst(58, FLOOR - 1, 18, 40, up=26, life=0.7, gravity=70)
        if t > 3.4:
            pixsmoke(g, 58, FLOOR - 1, t, self.seed, height=10, amount=1 - span(t, 4.0, 5.0), n=4, bits=False)
            g.px(57, FLOOR + 1), g.px(59, FLOOR + 1), g.px(58, FLOOR + 2)
        if t < 1.6:
            x = lerp(-12, DAO_X, ease_out(span(t, 0, 1.6)))
            h = dao(g, x, FLOOR, t, pose="walk")
            sword(g, h["hand"][0], h["hand"][1], -60, t)
        elif t < 3.0:
            self.raise_dao(g, t, sparks=2.0 < t < 2.4)
        elif t < 4.2:
            self.raise_dao(g, t, face="wow")
        else:
            self.idle_dao(g, t, face="happy")
        self.fx(g, dt)
        if t >= 3.6:
            hud(g, 0, 0, t)
        mx_bolt(g, 0, t, on=t > 2.2, full=3.4 <= t < 3.6)
        if 3.4 <= t < 3.8:
            g.mx_level = 8
        if t >= 3.6:
            self.counter(g, 0)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self.renew(g, t, e, k, dt)
            self.last_k = k
            return
        room(g)
        coil(g, 1, t, True)
        ambient_arcs(g, t, 1, self.seed)
        i = int(k // P)
        u = k - i * P
        kind = bug_kind(i, self.seed)
        bx, by = bug_pos(i, u, kind, self.seed)
        cx_, cy_ = bug_center(kind, bx, by)
        struck = STRIKE <= u
        # 劈中的一瞬（跨过 STRIKE 时触发一次碎屑）
        if self.last_k is not None and self.last_k < i * P + STRIKE <= k and k - self.last_k < 1:
            n = 30 if kind == "big" else 18
            self.sparks.burst(cx_, cy_, n, 42, up=22, life=0.8, gravity=70)
            self.puffs.emit(cx_, cy_, vy=-6, life=0.9, rmax=3 if kind == "big" else 2, spread=2)
        self.last_k = k
        if crawl0(i) <= u < STRIKE:
            draw_bug(g, kind, bx, by, e)
        if struck and u < STRIKE + 0.35:            # 长电弧
            bolt(g, CX + 12, TORUS_Y + 4, cx_, cy_, i * 31 + int(u * 30), width=2 if u < STRIKE + 0.15 else 1)
        if struck and u < STRIKE + 2.5:              # 焦痕 + 小烟
            fx_ = bug_center(kind, *bug_pos(i, STRIKE - 0.01, kind, self.seed))[0]
            if kind != "moth":
                g.px(fx_ - 1, FLOOR + 1), g.px(fx_ + 1, FLOOR + 1), g.px(fx_, FLOOR + 2)
                pixsmoke(g, fx_, FLOOR - 1, t, self.seed + i, height=10, amount=1 - span(u, STRIKE + 1, STRIKE + 2.5),
                         n=4, bits=False)
        # 小道士
        ev = i % 4
        if 7.4 <= u < STRIKE + 0.5:                  # 剑指 bug
            self.point_dao(g, t, (cx_, cy_), face="wow" if u > STRIKE else "normal")
        elif ev == 0 and 10.0 <= u < 11.8:           # 引雷入剑
            tip = self.raise_dao(g, t, sparks=True)
            if 10.3 < u < 11.4:
                lightning(g, CX - 12, TORUS_Y + 3, tip[0], tip[1], seed=int(t * 15), jag=3.0, branches=1)
        elif ev == 2 and 10.0 <= u < 11.6:           # 收剑拱手
            dao(g, DAO_X, FLOOR, t, pose="gong" if u < 10.6 else "bow", face="happy")
        else:
            self.idle_dao(g, t, face="happy" if STRIKE + 0.5 <= u < STRIKE + 1.5 else "normal")
        self.fx(g, dt)
        flashing = struck and u < STRIKE + 0.1
        if flashing and int((u - STRIKE) * 30) in (0, 2):
            pix.flash(g)
        if struck and u < STRIKE + 0.3:
            pix.shake(g, t, 2 if kind == "big" else 1.2)
        hud(g, self.charge(e), self.kills(e), t)
        mx_bolt(g, self.charge(e), t, full=flashing)
        if struck and u < STRIKE + 0.4:
            g.mx_level = 6
        self.counter(g, e)

    def renew(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """一轮满：五道巨雷接连劈下，蓄能清零"""
        room(g)
        coil(g, 1, t, True)
        ambient_arcs(g, t, 1.4, self.seed, n=4)
        xs = (46, 60, 98, 110, 70)
        for j, x in enumerate(xs):
            t0 = 0.8 + j * 0.3
            if t0 <= k < t0 + 0.3:
                bolt(g, x + 6, 0, x, FLOOR - 1, j * 17 + int(k * 30), width=2)
            if self.last_k is not None and self.last_k < t0 <= k:
                self.sparks.burst(x, FLOOR - 1, 14, 36, up=24, life=0.7, gravity=70)
            if k >= t0:
                g.px(x - 1, FLOOR + 1), g.px(x + 1, FLOOR + 1), g.px(x, FLOOR + 2)
                pixsmoke(g, x, FLOOR - 1, t + j, self.seed + j, height=9, amount=1 - span(k, t0 + 1.5, RENEW), n=3,
                         bits=False)
        if k < 2.6:
            self.raise_dao(g, t, face="wow" if k > 0.8 else "normal", sparks=k < 0.8)
        elif k < 3.8:
            dao(g, DAO_X, FLOOR, t, pose="gong", face="happy")
        else:
            self.idle_dao(g, t)
        self.fx(g, dt)
        hit = any(0.8 + j * 0.3 <= k < 0.8 + j * 0.3 + 0.07 for j in range(5))
        if hit:
            pix.flash(g)
        if 0.8 < k < 2.4:
            pix.shake(g, t, 1.8)
        charge = 1.0 if k < 0.8 else 1 - ease_in(span(k, 0.8, 2.3))
        hud(g, charge, self.kills(e), t, blink=k < 0.8)
        mx_bolt(g, charge, t, full=hit)
        g.mx_level = 6 if 0.8 < k < 2.3 else 1
        self.counter(g, e if k > 1.6 else e - k - 1)

    # ------------------------------------------------------------ 中断 / 恢复

    def _bug_static(self, g: Gfx, e: float):
        k = e % self.CYCLE
        i = int(k // P)
        u = k - i * P
        kind = bug_kind(i, self.seed)
        if crawl0(i) <= u < STRIKE:
            bx, by = bug_pos(i, u, kind, self.seed)
            draw_bug(g, kind, bx, by, e)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        room(g)
        on = t < 0.3
        coil(g, 1 - ease_in(span(t, 0.4, 1.2)), t, on)
        ambient_arcs(g, t, 1 - span(t, 0.3, 1.0), self.seed)
        if abs(t - 0.3) < dt * 0.6:
            self.sparks.burst(CX + 7, BASE_Y + 9, 8, 20, up=10, life=0.4)
            self.puffs.emit(CX, TORUS_Y + 2, vy=-5, life=0.9, rmax=2.5, spread=6)
        if 0.3 < t < 1.2 and rand(int(t * 20), 6) < 0.4:          # 零星火花渐熄
            a = rand(int(t * 20), 7) * math.pi * 2
            g.px(CX + math.cos(a) * 14, TORUS_Y + 4 + math.sin(a) * 5)
        self._bug_static(g, e)
        self.idle_dao(g, t, face="wow" if 0.3 < t < 1.2 else "normal")
        self.fx(g, dt)
        hud(g, self.charge(e), self.kills(e), t)
        mx_bolt(g, self.charge(e), t, on=t < 0.3 or (t < 1.0 and int(t * 10) % 2 == 0))
        self.counter(g, e, "断电" if t > 0.3 else None)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        room(g)
        on = t >= 0.3
        coil(g, ease_out(span(t, 0.3, 1.0)), t, on, flicker=1.0 < t < 1.3)
        if abs(t - 0.3) < dt * 0.6:
            self.sparks.burst(CX + 7, BASE_Y + 9, 10, 24, up=12, life=0.4)
        if 1.0 < t < 1.2:
            pix.shake(g, t, 1)
        ambient_arcs(g, t, span(t, 1.2, 1.8), self.seed)
        self._bug_static(g, e)
        if 0.2 < t < 1.3:
            self.raise_dao(g, t, sparks=t > 1.0)
        else:
            self.idle_dao(g, t)
        self.fx(g, dt)
        hud(g, self.charge(e), self.kills(e), t)
        mx_bolt(g, self.charge(e), t, on=t > 0.3)
        self.counter(g, e, "断电" if t < 0.3 else None)

    # ------------------------------------------------------------ 圆满：万雷齐发

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        room(g)
        coil(g, 1, t, True)
        ambient_arcs(g, t, 1 + span(t, 0, 1.4), self.seed, n=4 if t < 1.4 else 3)
        bugs = [("beetle", 98, FLOOR - 9), ("big", 106, FLOOR - 18), ("moth", 96, 22), ("moth", 108, 30)]
        STR = 1.4
        for j, (kind, x, y) in enumerate(bugs):
            cx_, cy_ = bug_center(kind, x, y)
            if t < STR:
                drop = ease_out_back(span(t, 0.2 + j * 0.2, 0.5 + j * 0.2))
                if drop > 0:
                    draw_bug(g, kind, x + (1 - drop) * 30, y, t)
            elif t < STR + 0.4:
                bolt(g, CX + 12 if j != 2 else CX + 8, TORUS_Y + 4, cx_, cy_, j * 13 + int(t * 30),
                     width=2 if t < STR + 0.2 else 1)
            if self.last_k is not None and self.last_k < STR <= t:
                self.sparks.burst(cx_, cy_, 22, 44, up=22, life=0.9, gravity=70)
                self.puffs.emit(cx_, cy_, vy=-6, life=1.0, rmax=2.5, spread=2)
        self.last_k = t
        if t > STR:
            for x in (104, 117):
                pixsmoke(g, x, FLOOR - 1, t + x, self.seed + x, height=12, amount=1 - span(t, 3.0, 5.0), n=4,
                         bits=False)
        if STR < t < 4.6:
            glow_rays(g, CX, TORUS_Y + 4, 15, 15 + 8 * span(t, STR, STR + 0.8), 14, t * 0.5, 0.6, dashed=True)
        if t < 3.2:
            self.raise_dao(g, t, face="wow" if t > STR else "normal", sparks=t < STR)
        else:
            self.idle_dao(g, t, face="happy")
        self.fx(g, dt)
        if STR <= t < STR + 0.07 or STR + 0.13 <= t < STR + 0.2:
            pix.flash(g)
        if STR < t < STR + 0.6:
            pix.shake(g, t, 2.2)
        charge = min(1.0, self.charge(e) + ease_in(span(t, 0, 1.2)))
        n_add = 4 if t >= STR else 0
        hud(g, charge, self.kills(e) + n_add, t, blink=1.0 < t < STR)
        mx_bolt(g, charge, t, full=STR <= t < STR + 0.3)
        g.mx_level = 1 + int(6 * (1 - span(t, STR, 3.0))) if t >= STR else 2
        if t < 2.0:
            self.counter(g, e)
        banner(g, 46, 6, "精怪亡形", span(t, 2.2, 2.6), t=t)
