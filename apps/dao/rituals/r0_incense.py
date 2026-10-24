"""燃香（示范法事，像素风的质量标杆）。

道观供桌的侧视场景：背墙挂“道”字匾，供桌铺桌围（中间太极），桌上一尊立耳三足铜炉、左右两只烛台。
主角 Q 版小道士（engine/chars.py）。

入场：小道士从左边走进来，站定，捧香，举香过额连拜三拜；三炷香带着灵光从手里飞进香炉，
      插下时扬起香灰、屏幕一震、火星迸出，香头点亮，烟团一个个冒起。
持续：香随计时变短（一轮 10 分钟），香头明灭，烟团飘升；香灰不时掉落；烛火跳动；
      小道士呼吸眨眼，每隔一阵作个揖。一炷烧完：残香一闪熄灭，小道士再请三炷香（续香），匾下“第几炷”加一。
中断：小道士抬手一按，香头依次“噗”地熄灭。  恢复：剑指一点，一道火星飞去，香头重新点亮。
圆满：香一齐烧尽，烟团聚成一大团盘旋上升，小道士跪拜，闪白，“功德圆满”弹出，金星四溅。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import _Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, text_width
from ..engine.scene import Ritual, register

FLOOR = 58
TABLE = (58, 122, 41)      # 供桌 x0, x1, 桌面 y
CENSER_X = 90              # 香炉中心
STICK_BASE = 31            # 香插在香灰里的位置（y）
STICK_DX = (-4, 0, 4)
FULL = 16                  # 新香露出的长度
STUB = 2
DAO_X = 38                 # 小道士站的位置
RENEW = 6.0


# ---------------------------------------------------------------- 道具（像素造型，只生成一次）

def _censer():
    """立耳三足铜炉 25×14：口沿、双耳、鼓腹回纹带、右下背光网点、三足"""
    p = _Part(25, 14)
    p.shape("rectangle", (1, 0, 3, 3), fill=1)          # 左耳
    p.shape("rectangle", (21, 0, 23, 3), fill=1)        # 右耳
    p.px(2, 1, 0), p.px(22, 1, 0)                        # 耳孔
    p.shape("rectangle", (0, 3, 24, 4), fill=1)         # 口沿
    p.shape("polygon", [(2, 5), (22, 5), (23, 7), (21, 10), (3, 10), (1, 7)], fill=1)  # 炉腹
    p.d.line((3, 5, 21, 5), fill=0)                     # 口沿下的阴线
    for x in range(4, 21, 4):                           # 回纹带
        p.d.line((x, 7, x + 2, 7), fill=0)
        p.px(x, 8, 0), p.px(x + 2, 6, 0)
    p.dither([(15, 8), (22, 7), (21, 10), (12, 10)], 0.5, 0)
    for x in (5, 12, 19):                               # 三足
        p.shape("rectangle", (x, 10, x + 1, 13), fill=1)
        p.px(x - 1, 13)
        p.px(x + 2, 13)
    return p.sprite()


def _candle():
    """烛台 7×13：蜡烛 + 托盘 + 细柄 + 底座"""
    p = _Part(7, 13)
    p.shape("rectangle", (2, 0, 4, 4), fill=1)
    p.px(4, 1, 0), p.px(4, 3, 0)
    p.shape("rectangle", (0, 5, 6, 5), fill=1)
    p.shape("rectangle", (3, 6, 3, 10), fill=1)
    p.px(2, 8), p.px(4, 8)
    p.shape("polygon", [(1, 12), (5, 12), (4, 10), (2, 10)], fill=1)
    return p.sprite()


def _plaque():
    """匾 26×11：边框"""
    p = _Part(26, 11)
    p.shape("rectangle", (0, 0, 25, 10), fill=1)
    p.d.rectangle((1, 1, 24, 9), fill=0)
    p.d.rectangle((2, 2, 23, 8), outline=1)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"censer": _censer, "candle": _candle, "plaque": _plaque}[name]()
    return _PROPS[name]


FLAME = pix.frames("""
 #
 #
###
#.#
---
  #
 #
###
#.#
---
 #
  #
###
#.#
""")


def room(g: Gfx, t: float):
    """背景：地砖、踢脚、柱、匾、供桌（桌围太极）、香炉、烛台"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    for x in (2, 125):
        g.d.line((x, 0, x, FLOOR - 4), fill=1)
    pix.blit(g, prop("plaque"), 77, 2)
    g.text(90, 3, "道", size=8, align="center")
    x0, x1, ty = TABLE
    g.d.rectangle((x0, ty, x1, ty + 2), fill=1)
    g.d.line((x0 + 1, ty + 1, x1 - 1, ty + 1), fill=0)
    g.d.rectangle((x0 + 3, ty + 3, x1 - 3, FLOOR - 1), outline=1, fill=0)
    g.d.line((x0 + 3, ty + 5, x1 - 3, ty + 5), fill=1)
    pix.checker(g, (x0 + 4, ty + 6, x1 - 3, FLOOR - 1), 0.125)
    cx, cy = (x0 + x1) // 2, ty + 10
    from ..engine.symbols import taiji
    g.d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=0)
    taiji(g, cx, cy, 4, t * 0.3)
    pix.blit(g, prop("censer"), CENSER_X - 12, ty - 14)
    for k, x in enumerate((TABLE[0] + 6, TABLE[1] - 8)):
        pix.blit(g, prop("candle"), x - 3, ty - 13)
        pix.blit(g, pix.anim(FLAME, t + k * 0.37, 7), x - 1, ty - 18, outline=False)


def stick_tips(length: float):
    return [(CENSER_X + dx, STICK_BASE - length) for dx in STICK_DX]


def sticks(g: Gfx, length: float, lit, t: float):
    """炉里的三炷香：香身 + 发光的香头（明灭）"""
    L = int(round(length))
    for i, dx in enumerate(STICK_DX):
        x = CENSER_X + dx
        g.d.line((x, STICK_BASE, x, STICK_BASE - L), fill=1)
        top = STICK_BASE - L
        if lit[i] and L > 0:
            on = (t * 2.3 + i * 0.41) % 1 < 0.75
            g.k.rectangle((x - 1, top - 1, x + 1, top + 1), fill=1)
            g.d.point((x, top))
            if on:
                g.d.point((x - 1, top)), g.d.point((x + 1, top)), g.d.point((x, top - 1))


def mx_censer(g: Gfx, length: float, lit, t: float):
    g.mx[7, 1:7] = True
    g.mx[6, 1] = g.mx[6, 6] = True
    g.mx[5, 2:6] = True
    h = 1 + int(round((length - STUB) / (FULL - STUB) * 3))
    for i, col in enumerate((2, 3, 5)):
        for r in range(4, 4 - h, -1):
            g.mx[r, col] = True
        if lit[i]:
            g.mx[4 - h, col] = (t * 2.3 + i * 0.41) % 1 < 0.75


@register
class IncenseRitual(Ritual):
    id = "r.incense"
    name = "燃香"
    desc = "小道士走到供桌前捧香三拜，三炷香带着灵光飞进香炉；香随计时燃短，烟团飘升，烧完再请一炷"
    T = {"enter": 7.0, "interrupt": 1.8, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.last_t = None

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    def length(self, e: float) -> float:
        return lerp(FULL, STUB, (e % self.CYCLE) / self.CYCLE)

    def smoke(self, g: Gfx, length: float, lit, t: float, dt: float, rate: float = 1.0):
        """香头冒烟团，被风吹得左右飘"""
        wind = math.sin(t * 0.3) * 3
        for i, (x, y) in enumerate(stick_tips(length)):
            if lit[i] and rate > 0 and int((t + i * 0.27) * 3.2 * rate) != int((t + i * 0.27 - dt) * 3.2 * rate):
                self.puffs.emit(x, y - 2, vx=wind, vy=-7, life=2.4, rmax=1.6 + i * 0.2, spread=1)
        self.puffs.step(dt, wind=wind * 0.5)
        self.puffs.draw(g)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        s = label or (f"第{cn_num(n)}炷" if n < 100 else f"{n}炷")
        w = text_width(s, 8)
        g.d.rectangle((5, 2, 9 + w, 12), outline=1)
        g.text(7, 4, s, size=8)

    # ------------------------------------------------------------ 入场：走来、三拜、送香

    def _offer(self, g: Gfx, t: float, e: float, walk: bool = True):
        """t ∈ [0, 7]：走进来（0–2.2）→ 捧香三拜（2.2–4.6）→ 香飞进炉（4.6–5.6）→ 插下点亮（5.6–7）"""
        dt = self._dt(t)
        room(g, t)
        x = lerp(-12, DAO_X, ease_out(span(t, 0, 2.2))) if walk else DAO_X
        if walk and t < 2.2:
            daoshi(g, x, FLOOR, "walk", t)
            mx_censer(g, FULL, (0, 0, 0), t)
            return
        k = t - 2.2
        held = None
        if k < 2.4:  # 三拜：捧香 → 鞠躬，各 0.8 秒
            ph = (k % 0.8) / 0.8
            pose = "offer" if ph < 0.45 else "bow"
            h = daoshi(g, x, FLOOR, pose, t)
            if pose == "offer":
                held = h["hand"]
        else:
            h = daoshi(g, x, FLOOR, "offer" if t < 5.0 else "idle", t)
            held = h["hand"] if t < 4.6 else None
        if held:  # 手里三炷香（未点）
            hx, hy = held
            for j in (-2, 0, 2):
                g.d.line((hx + j, hy, hx + j + 1, hy - 9), fill=1)
        fly = span(t, 4.6, 5.6)
        if 0 < fly < 1:  # 香带着灵光沿弧线飞进炉
            hx, hy = DAO_X + 9, FLOOR - 10
            tx, ty = CENSER_X, STICK_BASE - FULL
            q = ease_in_out(fly)
            px = lerp(hx, tx, q)
            py = lerp(hy, ty, q) - math.sin(q * math.pi) * 16
            for j in (-3, 0, 3):
                g.d.line((px + j, py, px + j, py + FULL), fill=1)
            for m in range(5):  # 拖尾
                qq = max(q - m * 0.05, 0)
                g.px(lerp(hx, tx, qq), lerp(hy, ty, qq) - math.sin(qq * math.pi) * 16 + FULL, 1 if m % 2 == 0 else 0)
            if int(t * 30) % 3 == 0:
                self.sparks.burst(px, py + FULL, 1, 10, life=0.4, gravity=10)
        if t >= 5.6:
            lit = tuple(t > 5.75 + i * 0.12 for i in range(3))
            sticks(g, FULL, lit, t)
            if t < 5.6 + dt * 1.5:  # 插下：扬灰 + 火星
                self.sparks.burst(CENSER_X, STICK_BASE, 14, 26, up=18, life=0.7, gravity=70)
            if t < 5.9:
                pix.shake(g, t, 1.0)
            self.smoke(g, FULL, lit, t, dt, rate=span(t, 5.8, 7.0))
            mx_censer(g, FULL, lit, t)
            self.counter(g, e)
        else:
            mx_censer(g, FULL, (0, 0, 0), t)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def enter(self, g: Gfx, t: float):
        self._offer(g, t, 0.0)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:  # 续香：残香一闪熄灭，再请三炷
            if k < 1.0:
                dt = self._dt(t)
                room(g, t)
                sticks(g, STUB, (k < 0.5,) * 3, t)
                daoshi(g, DAO_X, FLOOR, "idle", t)
                self.smoke(g, STUB, (1, 1, 1), t, dt, rate=1 - k)
                self.counter(g, e - k - 1)
                mx_censer(g, STUB, (k < 0.5,) * 3, t)
            else:
                self._offer(g, 2.2 + (k - 1.0) * 4.8 / (RENEW - 1.0), e, walk=False)
            return
        dt = self._dt(t)
        length = self.length(e)
        room(g, t)
        sticks(g, length, (1, 1, 1), t)
        for i, (x, y) in enumerate(stick_tips(length)):  # 香灰不时掉落（按 e）
            a = ((e + i * 9.1) % 23) / 23
            if a < 0.08 and length > STUB + 1:
                g.px(x + (1 if i == 2 else -1), y + ease_in(a / 0.08) * (STICK_BASE - y - 1))
        ph = t % 20
        pose = "gongshou" if 14 < ph < 15.2 else ("bow" if 15.2 <= ph < 16.4 else "idle")
        daoshi(g, DAO_X, FLOOR, pose, t)
        self.smoke(g, length, (1, 1, 1), t, dt)
        self.counter(g, e)
        mx_censer(g, length, (1, 1, 1), t)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        length = self.length(e)
        room(g, t)
        lit = tuple(t < 0.6 + i * 0.3 for i in range(3))
        sticks(g, length, lit, t)
        for i, (x, y) in enumerate(stick_tips(length)):  # 熄灭时“噗”一小团
            if abs(t - (0.6 + i * 0.3)) < dt:
                self.puffs.emit(x, y - 1, vy=-4, life=0.8, rmax=2.5, spread=0)
        daoshi(g, DAO_X, FLOOR, "raise" if t < 1.5 else "idle", t)
        self.smoke(g, length, lit, t, dt, rate=0)
        self.counter(g, e, "暂熄")
        mx_censer(g, length, lit, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        length = self.length(e)
        room(g, t)
        h = daoshi(g, DAO_X, FLOOR, "point" if t < 1.3 else "idle", t)
        q = span(t, 0.3, 1.0)
        tips = stick_tips(length)
        if 0 < q < 1:  # 剑指一点，一颗火星沿弧线飞到香头
            hx, hy = h["hand"]
            tx, ty = tips[1]
            px, py = lerp(hx, tx, q), lerp(hy, ty, q) - math.sin(q * math.pi) * 10
            g.d.ellipse((px - 1, py - 1, px + 1, py + 1), fill=1)
            self.sparks.burst(px, py, 1, 6, life=0.3, gravity=0)
        lit = tuple(t > 1.0 + abs(i - 1) * 0.15 for i in range(3))
        if abs(t - 1.0) < dt:
            self.sparks.burst(tips[1][0], tips[1][1], 10, 20, up=10, life=0.5)
            pix.flash(g)
        sticks(g, length, lit, t)
        self.smoke(g, length, lit, t, dt, rate=span(t, 1.0, 1.8))
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        mx_censer(g, length, lit, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        length = lerp(self.length(e), 0, ease_in(span(t, 0, 1.5)))
        room(g, t)
        alive = t < 1.6
        sticks(g, length, (alive,) * 3, t)
        daoshi(g, DAO_X, FLOOR, "kneel" if 1.6 < t < 4.0 else ("gongshou" if t <= 1.6 else "idle"), t)
        if 1.2 < t < 4.0:  # 烟团聚成一大团盘旋上升
            k = span(t, 1.2, 4.0)
            cx, cy = CENSER_X + math.sin(t * 3) * 4, 26 - k * 30
            for j in range(6):
                a = t * 4 + j * 1.05
                r = 3 + k * 6
                rr = 2.5 * (1 - k) + 0.5
                x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.5
                g.d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=1)
        else:
            self.smoke(g, max(length, 0.1), (alive,) * 3, t, dt, rate=1.5 if t < 1.2 else 0)
        if abs(t - 1.6) < dt:
            pix.flash(g)
            self.sparks.burst(CENSER_X, STICK_BASE - 4, 24, 40, up=20, life=1.2, gravity=40)
        if 1.6 < t < 1.9:
            pix.shake(g, t, 1.5)
        if t > 2.0:  # “功德圆满”弹出
            pop = ease_out_back(span(t, 2.0, 2.4))
            w = text_width("功德圆满")
            y = 8 + (1 - pop) * 10
            g.k.rectangle((64 - w / 2 - 3, y - 2, 64 + w / 2 + 2, y + 12), fill=1)
            g.d.rectangle((64 - w / 2 - 3, y - 2, 64 + w / 2 + 2, y + 12), outline=1)
            g.text(64, y, "功德圆满", align="center")
            if int(t * 6) % 2 == 0:
                for sx, sy in ((64 - w / 2 - 7, y + 4), (64 + w / 2 + 6, y + 4)):
                    for ddx, ddy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                        g.d.point((sx + ddx, sy + ddy))
        self.sparks.step(dt)
        self.sparks.draw(g)
        mx_censer(g, max(length, STUB), (alive,) * 3, t)
        if t > 1.6:
            r = (t - 1.6) * 4
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - r) < 0.6:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(5 * (1 - span(t, 1.6, 3.0)))
