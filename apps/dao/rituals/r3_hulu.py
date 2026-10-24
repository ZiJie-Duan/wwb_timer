"""葫芦收妖：小道士双手托着大葫芦，葫芦口对准左边一团瞪眼的妖气；妖气被拉长、一粒粒螺旋着吸进葫芦，
不时有小鬼被整只扯出来吞进去，葫芦一抖、口上一闪。

葫芦是道家常见法器，也是“壶天”意象的来源（《后汉书·方术传》中壶公悬壶，壶中别有天地）。
民间道法与小说中常以葫芦收妖、贮丹。

入场：左边地上冒起一团瞪着眼的妖气（横眉、眼珠斜瞟、锯齿嘴）；小道士托着葫芦从右边走进来，站定一举，
      塞子“啵”地弹开飞走，口上一闪。
持续：妖气朝葫芦口被拉长、晃动，一粒粒螺旋着吸进去（每粒进口时口上一亮）；每 15 秒有一只小鬼被整只扯出来、
      拉长、吞进口，葫芦一抖、闪光、火星。一轮 600 秒，妖气从大团缩到只剩一双眼。右上写“第几妖”。
      续：塞子落回塞口，葫芦猛抖、放光；左边又冒出一团新妖气，塞子再弹开。
中断：塞子落回塞口，吸力停止，妖气松了口气，写“塞口”。  恢复：塞子弹开，再吸。
圆满：猛吸一口，整团妖气被拉成一条吞进去，塞口，葫芦剧烈抖动后放光，题“邪祟尽收”。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r3_kit import (FLOOR, Clock, art, banner, banner_text, crossed, floor, hit, label, mx_ring, pose_arm, put,
                     rays, round_of, sparkle)

DX = 100                 # 小道士（朝左）
MON = (26, 34)           # 妖气中心
CYCLE = 600.0
IMP = 15.0
RENEW = 6.0


def _gourd() -> Sprite:
    """横托的大葫芦 22×14：大肚在右、小肚在左、口朝左；腰上一道红绳（暗）、肚上高光弧、下半网点"""
    p = Part(23, 15)
    p.shape("ellipse", (8, 0, 22, 14), fill=1)       # 大肚
    p.shape("ellipse", (2, 3, 10, 11), fill=1)       # 小肚
    p.shape("rectangle", (0, 5, 3, 9), fill=1)       # 口
    p.d.line((0, 5, 0, 9), fill=0)                   # 口沿
    p.px(0, 6, 1), p.px(0, 8, 1)
    p.d.line((9, 3, 9, 11), fill=0)                  # 腰绳
    p.d.line((10, 2, 10, 12), fill=0)
    p.px(9, 7, 1), p.px(10, 7, 1)
    p.d.arc((11, 2, 19, 10), 200, 260, fill=0)       # 高光弧（暗线勾出亮面）
    p.dither([(11, 12), (22, 10), (22, 15), (11, 15)], 0.5, 0)
    p.px(15, 0, 0), p.px(16, 0, 0)
    s = Sprite(on=np.array(p.on, bool), mask=np.array(p.mk, bool))
    s.anchor = (15, 12)
    s.pts = {"mouth": (0, 7), "knot": (9, 11)}
    return s


GOURD = _gourd()

PLUG = art("""
.#.
###
#.#
###
""", anchor=(1, 2))


def _monster(f: int, s: float) -> Sprite:
    """妖气（按大小 s 直接画，不缩放）：头顶两只尖角的一团雾，斜吊的怒眼眶、锯齿牙的大嘴，底下三条雾尾（两帧摆）"""
    def P(x, y):
        return (round(x * s), round(y * s))
    W, H = round(21 * s) + 2, round(20 * s) + 3
    p = Part(W, H)
    p.shape("ellipse", P(0, 3) + P(20, 16), fill=1)                          # 身子
    for x0, x1, tip in ((2, 7, 3), (13, 18, 17)):                            # 两只尖角
        tx = tip + (1 if f else 0)
        p.shape("polygon", [P(x0, 6), P(tx, 0), P(x1, 5)], fill=1)
    for i, x in enumerate((4, 10, 16)):                                      # 雾尾
        sw = 2 if (i + f) % 2 else -2
        p.shape("polygon", [P(x - 3, 14), P(x + 3, 14), P(x + sw, 19)], fill=1)
    if s >= 0.5:
        p.d.polygon([P(3, 7), P(8, 9), P(8, 11), P(3, 11)], fill=0)          # 左眼眶（外高内低：怒）
        p.d.polygon([P(17, 7), P(12, 9), P(12, 11), P(17, 11)], fill=0)
        p.d.rectangle(P(6, 13) + P(14, 14), fill=0)                           # 嘴
        for x in range(5, 16, 2):                                            # 锯齿牙
            p.px(*P(x + 0.5, 13), 1) if s >= 0.8 else None
        if s >= 0.8:
            for x in range(6, 15, 2):
                p.px(*P(x + 0.5, 14), 1)
        eyes = (P(6, 10), P(15, 10))
    else:                                                                    # 只剩一双眼
        p.d.rectangle(P(4, 8) + P(8, 11), fill=0)
        p.d.rectangle(P(12, 8) + P(16, 11), fill=0)
        eyes = (P(7, 10), P(13, 10))
    for x, y in ((15, 13), (17, 11), (13, 15), (16, 15)):                    # 背光一侧几个暗点
        if s >= 0.8:
            p.on.putpixel(P(x, y), 0)
    sp = Sprite(on=np.array(p.on, bool), mask=np.array(p.mk, bool))
    sp.anchor = (W // 2, round(19 * s))
    sp.pts = {"e0": eyes[0], "e1": eyes[1], "c": P(19, 10)}
    sp.er = 2 if s >= 0.5 else 1
    return sp


_MON: dict = {}


def monster_spr(f: int, s: float) -> Sprite:
    k = (f, round(min(max(s, 0.25), 1.0) * 10) / 10)
    if k not in _MON:
        _MON[k] = _monster(*k)
    return _MON[k]


IMP_S = art("""
#   #
#.#.#
#####
#.#.#
.###.
#####
 # #
""", anchor=(2, 3))

MX_GOURD = """
..##....
.####...
..##....
.####...
######..
######..
.####...
"""


class _Scale:
    _c: dict = {}

    @classmethod
    def get(cls, spr: Sprite, sx: float, sy: float) -> Sprite:
        sx, sy = round(sx, 1), round(sy, 1)
        key = (id(spr), sx, sy)
        v = cls._c.get(key)
        if v is None:
            v = pix.stretch(spr, sx, sy)
            ax, ay = spr.anchor
            v.anchor = (int(round(ax * sx)), int(round(ay * sy)))
            v.pts = {k: (int(round(x * sx)), int(round(y * sy))) for k, (x, y) in spr.pts.items()}
            cls._c[key] = v
        return v


@register
class HuluRitual(Ritual):
    id = "r3.hulu"
    name = "葫芦收妖"
    desc = "小道士托着大葫芦对准一团瞪眼的妖气，妖气被拉长、一粒粒螺旋吸进葫芦，小鬼被整只扯进去；随计时妖气越缩越小"
    T = {"enter": 6.0, "interrupt": 1.4, "resume": 1.6, "complete": 6.0}
    CYCLE = CYCLE

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.clock = Clock()

    # ------------------------------------------------------------ 公用

    def holder(self, g: Gfx, t: float, shake: float = 0.0, plug: str = "off", plug_k: float = 1.0,
               face: str = "normal", glow: bool = False) -> tuple[int, int]:
        """小道士（朝左）托葫芦；返回葫芦口。plug：off 已飞走 / in 塞着 / pop 正弹开（plug_k）/ back 正落回"""
        j = (int(t * 40) % 3 - 1) * shake
        out = {}

        def prop(g2, h):
            pts = put(g2, GOURD, h[0] + 2 + j, h[1] + 1)
            out.update(pts)
            kx, ky = pts["knot"]   # 腰绳垂下的穗子
            sw = math.sin(t * 2.3) * 1.5
            g2.d.line((kx, ky + 1, kx + sw, ky + 5), fill=1)
            g2.d.rectangle((kx + sw - 1, ky + 5, kx + sw + 1, ky + 7), fill=1)
        pose_arm(g, DX, "low", t, "fist", flip=True, face=face, prop=prop)
        mx, my = out["mouth"]
        mx += 2
        if plug == "in":
            put(g, PLUG, mx - 3, my)
        elif plug in ("pop", "back"):
            q = plug_k if plug == "pop" else 1 - plug_k
            x = mx - 3 - q * 14
            y = my - math.sin(min(q, 1) * math.pi * 0.9) * 18 - q * 4
            if q < 1:
                put(g, PLUG, x, y)
        if glow:
            rays(g, out["mouth"][0] + 12, out["mouth"][1], 13, 18, 12, rot=t, dash=2)
        return mx - 1, my

    def ground(self, g: Gfx, t: float):
        floor(g)
        # 远处荒坟、枯树（妖气从这里冒出来）
        g.d.arc((26, FLOOR - 6, 46, FLOOR + 6), 180, 360, fill=1)        # 荒坟
        g.d.rectangle((34, FLOOR - 12, 38, FLOOR - 6), fill=0, outline=1)  # 断碑
        g.px(36, FLOOR - 10), g.px(36, FLOOR - 8)
        tree = [((5, FLOOR), (5, FLOOR - 20)), ((5, FLOOR - 12), (1, FLOOR - 17)), ((5, FLOOR - 16), (10, FLOOR - 23)),
                ((10, FLOOR - 23), (13, FLOOR - 22)), ((1, FLOOR - 17), (0, FLOOR - 19))]
        for a, b in tree:                                                 # 枯树
            g.d.line((a, b), fill=1)

    def monster(self, g: Gfx, size: float, t: float, pull: float, mouth, calm: bool = False, wob: float = 1.0):
        """妖气：size 0..1；pull 0..1 被吸的程度（整团朝葫芦口歪过去、晃）"""
        if size <= 0.05:
            return None
        spr = monster_spr(int(t * 4) % 2, size)
        x = MON[0] + pull * (3 + math.sin(t * 9) * wob) + math.sin(t * 1.7) * 1.5
        y = MON[1] + 10 + math.sin(t * 2.3) * 1.2
        pts = put(g, spr, x, y)
        er = spr.er if hasattr(spr, "er") else monster_spr(0, size).er
        for k in ("e0", "e1"):   # 眼珠斜瞟葫芦口
            ex, ey = pts[k]
            dx = -1 if calm else 0
            g.d.rectangle((ex + dx - 1, ey - 1, ex + dx, ey), fill=1) if er >= 2 else g.px(ex + dx, ey - 1)
        cx, cy = pts["c"]
        return cx, cy

    def suck(self, g: Gfx, t: float, src, mouth, n: int = 5):
        """妖气一粒粒螺旋着吸进葫芦口（纯按时间算）"""
        sx, sy = src
        mx, my = mouth
        for i in range(n):
            q = ((t * 0.8 + i / n) % 1)
            qq = ease_in(q)
            a = q * 8 + i
            r = (1 - qq) * 7
            x = lerp(sx, mx, qq) + math.cos(a) * r
            y = lerp(sy, my, qq) + math.sin(a) * r * 0.7
            g.px(x, y)
            g.px(x - math.cos(a) * 1.2, y - math.sin(a) * 0.9)
        # 两道弯弯的妖气流，一节节往口里走
        for j in range(2):
            for i in range(0, 40):
                f = i / 40
                if (i + int(t * 24)) % 4 >= 2:
                    continue
                x = lerp(sx + 4, mx, f)
                y = lerp(sy + (j * 2 - 1) * 3, my, f) + math.sin(f * 7 + t * 5 + j * 2) * 3 * (1 - f)
                g.px(x, y)
        # 口上的吸气线
        for j in range(3):
            q = (t * 3 + j / 3) % 1
            x = mx - 4 - (1 - q) * 10
            pix.dotted(g, x, my - 4 + j * 4, x + 3, my - 1 + j, 1)

    def imp(self, g: Gfx, u: float, src, mouth, dt: float):
        """一只小鬼被整只扯出来、拉长、吞进口（u = 0..1.4）"""
        if u >= 1.4:
            return
        sx, sy = src
        mx, my = mouth
        if u < 0.4:      # 扯出来：从妖气里冒头、挣扎
            q = u / 0.4
            put(g, IMP_S, sx + 6 * q, sy - 8 * q + math.sin(u * 40) * 1)
            return
        q = ease_in(min((u - 0.4) / 0.6, 1))
        x, y = lerp(sx + 6, mx, q), lerp(sy - 8, my, q) - math.sin(q * math.pi) * 6
        spr = pix.stretch(IMP_S, 1 + q * 1.6, max(1 - q * 0.6, 0.3))
        spr.anchor = (spr.w // 2, spr.h // 2)
        spr.pts = {}
        if q < 1:
            put(g, spr, x, y)
        if crossed(u, dt, 1.0):
            self.sparks.burst(mx, my, 14, 30, life=0.5, gravity=40)

    def fx(self, g: Gfx, dt: float):
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def mx(self, g: Gfx, fill: float, open_: bool, t: float):
        g.mx_blit(MX_GOURD)
        h = int(round(fill * 4))
        for r in range(7 - h, 7):
            for x in range(8):
                if g.mx[r, x]:
                    g.mx[r, x] = (x + r) % 2 == 0
        if open_:
            g.mx[0, 2] = g.mx[0, 3] = (t * 6) % 1 < 0.5
        else:
            g.mx[0, 2] = g.mx[0, 3] = True

    def size_of(self, k: float) -> float:
        """妖气分档缩小：一大团 → 中 → 小 → 只剩一双眼（每档换的时候“噗”一下）"""
        return (1.0, 0.8, 0.6, 0.4)[min(int(k / CYCLE * 4), 3)]

    def counter(self, g: Gfx, n: int, s: str | None = None):
        label(g, 125, 3, s or (f"第{cn_num(n)}妖" if n < 100 else f"{n}妖"), align="right")

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        self.ground(g, t)
        grow = ease_out_back(span(t, 0.2, 1.4))
        if t < 1.4 and int(t * 10) % 2 == 0:
            self.puffs.emit(MON[0] + (rand(int(t * 10), 1) - 0.5) * 16, FLOOR - 2, vy=-10, life=0.8, rmax=2.5)
        mouth = (DX - 30, FLOOR - 13)
        if t < 3.2:
            x = lerp(140, DX, ease_out(span(t, 1.0, 3.2)))
            h = daoshi(g, x, FLOOR, "walk", t, flip=True)["hand"]
            put(g, GOURD, h[0] + 2, h[1] + 1)
            self.monster(g, grow, t, 0.0, mouth)
        elif t < 4.0:
            mouth = self.holder(g, t, plug="in", face="normal")
            self.monster(g, 1.0, t, 0.0, mouth)
        else:
            k = span(t, 4.0, 4.6)
            mouth = self.holder(g, t, plug="pop", plug_k=k, face="wow" if t < 4.6 else "normal")
            if crossed(t, dt, 4.0):
                self.sparks.burst(mouth[0], mouth[1], 10, 26, life=0.4)
            if 4.0 <= t < 4.3:
                hit(g, mouth[0] - 2, mouth[1], (t - 4.0) / 0.3)
            pull = span(t, 4.4, 5.4)
            src = self.monster(g, 1.0, t, pull, mouth)
            if pull > 0 and src:
                self.suck(g, t, src, mouth, n=int(6 * pull))
        self.fx(g, dt)
        self.counter(g, 1)
        self.mx(g, 0, t > 4.0, t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, p = round_of(e, CYCLE)
        if e >= CYCLE and k < RENEW:
            self.renew(g, k, t, e, dt, n)
            return
        self.ground(g, t)
        u = e % IMP
        shake = 1.0 if 1.0 <= u < 1.4 else 0.0
        mouth = self.holder(g, e, shake=shake, face="wow" if 0.9 <= u < 1.6 else "normal")
        size = self.size_of(k)
        src = self.monster(g, size, e, 1.0, mouth, wob=2.0 if u < 1.0 else 1.0)
        if src:
            self.suck(g, e, src, mouth)
            self.imp(g, u, src, mouth, dt)
        if 1.0 <= u < 1.1:
            sparkle(g, mouth[0] - 1, mouth[1], 4)
        if 1.0 <= u < 1.2:
            pix.shake(g, t, 1)
        self.fx(g, dt)
        self.counter(g, n)
        self.mx(g, k / CYCLE, True, t)

    def renew(self, g: Gfx, k: float, t: float, e: float, dt: float, n: int):
        """塞子落回 → 葫芦猛抖放光 → 新妖气冒出 → 塞子再弹开"""
        self.ground(g, t)
        if k < 0.5:
            plug, pk = "back", span(k, 0, 0.5)
        elif k < 4.2:
            plug, pk = "in", 1.0
        else:
            plug, pk = "pop", span(k, 4.2, 4.8)
        mouth = self.holder(g, t, shake=1.5 if 0.5 <= k < 2.0 else 0.0, plug=plug, plug_k=pk,
                            face="happy" if k < 3.0 else "normal", glow=1.0 <= k < 2.4)
        if crossed(k, dt, 0.5):
            self.sparks.burst(mouth[0], mouth[1], 12, 24, life=0.5)
        if 1.0 <= k < 1.07:
            pix.flash(g)
        grow = ease_out_back(span(k, 2.6, 3.8))
        if 2.4 < k < 3.6 and int(k * 10) % 2 == 0:
            self.puffs.emit(MON[0] + (rand(int(k * 10), 1) - 0.5) * 16, FLOOR - 2, vy=-10, life=0.8, rmax=2.5)
        pull = span(k, 4.6, 5.6)
        src = self.monster(g, grow, t, pull, mouth)
        if pull > 0 and src:
            self.suck(g, t, src, mouth, n=int(6 * pull))
        self.fx(g, dt)
        self.counter(g, n if k > 2.4 else n - 1, "收妖" if k < 2.4 else None)
        self.mx(g, 1.0 if k < 2.4 else 0.0, plug in ("pop", "off"), t)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        self.ground(g, t)
        mouth = self.holder(g, t, plug="back", plug_k=span(t, 0.0, 0.5))
        if crossed(t, dt, 0.5):
            self.sparks.burst(mouth[0], mouth[1], 8, 18, life=0.4)
        pull = 1 - span(t, 0.3, 0.9)
        src = self.monster(g, self.size_of(k), t, pull, mouth, calm=t > 0.9)
        if src and pull > 0.3:
            self.suck(g, t, src, mouth, n=int(6 * pull))
        self.fx(g, dt)
        self.counter(g, n, "塞口" if t > 0.5 else None)
        self.mx(g, k / CYCLE, False, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        self.ground(g, t)
        if t < 0.3:
            mouth = self.holder(g, t, plug="in")
        else:
            mouth = self.holder(g, t, plug="pop", plug_k=span(t, 0.3, 0.9), face="wow" if t < 0.8 else "normal")
        if crossed(t, dt, 0.3):
            self.sparks.burst(mouth[0], mouth[1], 10, 26, life=0.4)
        if 0.3 <= t < 0.6:
            hit(g, mouth[0] - 2, mouth[1], (t - 0.3) / 0.3)
        pull = span(t, 0.5, 1.2)
        src = self.monster(g, self.size_of(k), e, pull, mouth, calm=t < 0.5)
        if src and pull > 0:
            self.suck(g, e, src, mouth, n=int(6 * pull))
        self.fx(g, dt)
        self.counter(g, n)
        self.mx(g, k / CYCLE, t > 0.3, t)

    def complete(self, g: Gfx, t: float, e: float):
        """猛吸：妖气被拉成一条吞进去 → 塞口 → 葫芦剧抖 → 放光 → 邪祟尽收"""
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        self.ground(g, t)
        if t < 2.0:
            plug, pk = "off", 1.0
        elif t < 2.4:
            plug, pk = "back", span(t, 2.0, 2.4)
        else:
            plug, pk = "in", 1.0
        mouth = self.holder(g, t, shake=2.0 if 2.4 <= t < 3.4 else (0.6 if t < 2.0 else 0.0), plug=plug, plug_k=pk,
                            face="wow" if t < 3.4 else "happy", glow=t >= 3.4)
        if t < 2.0:   # 整团妖气被拉成长条吞进去
            q = ease_in(span(t, 0.2, 1.9))
            size = self.size_of(k)
            x0 = lerp(MON[0] - 8 * size, mouth[0], q)
            y0 = MON[1]
            mx, my = mouth
            for i in range(14):
                f = i / 13
                x = lerp(x0, mx, f)
                y = lerp(y0, my, f) + math.sin(t * 20 + i) * (1 - f) * 2
                r = max(0.5, (1 - f) * 4 * size * (1 - q * 0.6))
                g.d.ellipse((x - r - 1, y - r - 1, x + r + 1, y + r + 1), fill=0)
                g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
            if q < 0.85:   # 拖在最后的妖脸，越拉越小
                spr = monster_spr(int(t * 8) % 2, max(0.4, size * (1 - q * 0.7)))
                pts = put(g, spr, x0 - 2, y0 + 8)
                for kk in ("e0", "e1"):
                    ex, ey = pts[kk]
                    g.px(ex + 1, ey - 1)
            if int(t * 30) % 2 == 0:
                self.sparks.burst(mx, my, 2, 16, life=0.3)
        if crossed(t, dt, 2.4):
            self.sparks.burst(mouth[0], mouth[1], 16, 30, life=0.5)
        if crossed(t, dt, 3.4):
            self.sparks.burst(mouth[0] + 12, mouth[1], 30, 46, up=10, life=1.0, gravity=40)
        if 3.4 <= t < 3.48:
            pix.flash(g)
        if 2.4 <= t < 3.4:
            pix.shake(g, t, 1.2)
        self.fx(g, dt)
        if t > 3.6:
            banner(g, 40, 8, "邪祟尽收", span(t, 3.6, 4.0))
            banner_text(g, 40, 8, "邪祟尽收", span(t, 3.6, 4.0))
        else:
            self.counter(g, n)
        self.mx(g, 1.0 if t > 2.0 else span(t, 0, 2.0), t < 2.0, t)
        if t > 3.4:
            mx_ring(g, (t - 3.4) * 4)
            g.mx_level = 1 + int(6 * (1 - span(t, 3.4, 4.8)))
