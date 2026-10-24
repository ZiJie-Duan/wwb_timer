"""观星：二十八宿宿轮。

依据：二十八宿分属四象——东方苍龙（角亢氐房心尾箕）、北方玄武（斗牛女虚危室壁）、
西方白虎（奎娄胃昴毕觜参）、南方朱雀（井鬼柳星张翼轸）。每宿的星官画成连线星图
（星数、形状按传统星图简化，如心宿三星、昴宿七星团、参宿十星、鬼宿中央积尸气）。

入场：星空淡入，巨大的宿轮从屏幕下方升起，指针落下。
持续：宿轮随计时转动，一轮 10 分钟转满二十八宿（“一周天”）；指针下的宿名反白、点阵显示该宿星图；
      下方显示所属四象；偶有流星。转满一周：轮缘一圈星光，“第几周天”闪动。
中断：一片云从左边飘来遮住指针与星空。
恢复：云飘走。
圆满：宿轮飞转一周，星官依次闪亮，“斗转星移”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.cn import cn_num
from ..engine.fx import stars, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r5_util import cloud_blobs, mist

NAMES = "角亢氐房心尾箕斗牛女虚危室壁奎娄胃昴毕觜参井鬼柳星张翼轸"
SIXIANG = ["东方苍龙", "北方玄武", "西方白虎", "南方朱雀"]
# 每宿星图：若干条连线（每条一串点），坐标 0..7
ASTER = [
    [[(1, 5), (6, 2)]],                                                    # 角
    [[(1, 3), (3, 1), (5, 2), (6, 5)]],                                    # 亢
    [[(1, 1), (6, 2), (5, 6), (2, 5), (1, 1)]],                            # 氐
    [[(5, 0), (4, 2), (3, 4), (3, 6)]],                                    # 房
    [[(1, 2), (3, 4), (6, 5)]],                                            # 心
    [[(1, 0), (1, 2), (2, 4), (2, 6), (4, 7), (6, 6), (7, 4), (6, 3)]],    # 尾
    [[(1, 1), (1, 5), (6, 6), (5, 2)]],                                    # 箕
    [[(0, 5), (2, 6), (4, 5), (4, 2), (6, 1), (7, 3)]],                    # 斗
    [[(2, 1), (4, 0), (6, 1)], [(4, 0), (3, 3), (3, 6), (5, 6)]],          # 牛
    [[(1, 2), (3, 1), (5, 3), (6, 6)]],                                    # 女
    [[(2, 2), (5, 5)]],                                                    # 虚
    [[(1, 5), (3, 1), (6, 4)]],                                            # 危
    [[(2, 1), (5, 6)]],                                                    # 室
    [[(4, 0), (4, 6)]],                                                    # 壁
    [[(3, 0), (5, 1), (6, 3), (6, 5), (4, 7), (2, 7), (1, 5), (1, 3), (2, 1), (3, 0)]],  # 奎
    [[(1, 5), (4, 3), (6, 1)]],                                            # 娄
    [[(2, 1), (6, 3), (2, 5), (2, 1)]],                                    # 胃
    [[(2, 2)], [(4, 1)], [(5, 3)], [(3, 4)], [(6, 5)], [(1, 5)], [(4, 6)]],  # 昴
    [[(0, 0), (2, 3), (3, 5), (5, 3), (7, 1)], [(3, 5), (3, 7)]],          # 毕
    [[(3, 2), (5, 3), (4, 5), (3, 2)]],                                    # 觜
    [[(1, 0), (3, 3), (6, 1)], [(3, 3), (4, 4), (5, 5)], [(1, 7), (4, 4)], [(5, 5), (6, 7)]],  # 参
    [[(1, 2), (3, 2), (5, 2), (7, 2)], [(0, 5), (2, 5), (4, 5), (6, 5)]],  # 井
    [[(1, 1), (6, 1), (6, 6), (1, 6), (1, 1)], [(3, 3)]],                  # 鬼
    [[(0, 3), (2, 1), (4, 1), (6, 2), (7, 4), (6, 6), (4, 7), (2, 6)]],    # 柳
    [[(0, 5), (2, 3), (4, 4), (6, 2), (7, 0)], [(4, 4), (5, 7)]],          # 星
    [[(1, 1), (3, 3), (5, 3), (6, 5)], [(3, 3), (2, 6)]],                  # 张
    [[(0, 6), (2, 4), (4, 3), (6, 4), (7, 6)], [(4, 3), (4, 0)], [(2, 4), (1, 1)], [(6, 4), (7, 1)]],  # 翼
    [[(1, 2), (6, 1), (6, 6), (1, 5), (1, 2)], [(0, 0)], [(7, 7)]],        # 轸
]
CX, CY = 64, 120
R1, R2, R3 = 104, 89, 73
SLOT = 2 * math.pi / 28
RENEW = 5.0


def polar(r: float, a: float, cy: float = CY):
    return CX + r * math.sin(a), cy - r * math.cos(a)


@register
class Xiu(Ritual):
    id = "r5.xiu"
    name = "观星"
    desc = "二十八宿宿轮随计时转过指针，一轮转满一周天；指针下的宿反白，点阵显示星图"
    T = {"enter": 3.5, "interrupt": 1.5, "resume": 1.5, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.sky = self.rng.randrange(1000)

    def rot(self, e: float) -> float:
        return (e % self.CYCLE) / self.CYCLE * 2 * math.pi

    def cur(self, e: float) -> int:
        return int((e % self.CYCLE) / self.CYCLE * 28) % 28

    # ------------------------------------------------------------ 宿轮

    def wheel(self, g: Gfx, rot: float, cy: float = CY, hi: int | None = None, t: float = 0.0, flash=None):
        d = g.d
        for r in (R1, R2, R3):
            d.arc((CX - r, cy - r, CX + r, cy + r), 180, 360, fill=1)
        d.arc((CX - R1 - 2, cy - R1 - 2, CX + R1 + 2, cy + R1 + 2), 180, 360, fill=1)
        for i in range(28):
            a0 = i * SLOT - rot
            ac = a0 + SLOT / 2
            aw = (ac + math.pi) % (2 * math.pi) - math.pi
            if abs(aw) > 0.75:
                continue
            x0, y0 = polar(R3, a0, cy)
            x1, y1 = polar(R1, a0, cy)
            d.line((x0, y0, x1, y1), fill=1)
            # 星图：切向 u、径向 v
            ux, uy = math.cos(ac), math.sin(ac)
            vx, vy = math.sin(ac), -math.cos(ac)
            bx, by = polar((R1 + R2) / 2, ac, cy)
            lit = flash(i) if flash else True

            def P(p):
                u, v = (p[0] - 3.5) * 1.7, (3.5 - p[1]) * 1.55
                return bx + ux * u + vx * v, by + uy * u + vy * v
            for chain in ASTER[i]:
                pts = [P(p) for p in chain]
                if len(pts) > 1 and lit:
                    d.line(pts, fill=1)
                for j, (px, py) in enumerate(pts):
                    if lit or blink(t + j * 0.1, 0.3):
                        d.rectangle((px - 1, py - 1, px + 1, py + 1), fill=0)
                        d.rectangle((px - 0.5, py - 0.5, px + 0.5, py + 0.5), fill=1)
                        g.px(px, py)
            # 宿名
            nx, ny = polar((R2 + R3) / 2 + 1, ac, cy)
            if i == hi:
                d.rectangle((nx - 7, ny - 7, nx + 6, ny + 6), fill=1)
                g.text(nx, ny - 5, NAMES[i], align="center", fill=0)
            else:
                g.text(nx, ny - 5, NAMES[i], align="center")

    def pointer(self, g: Gfx, y: float = 0.0, t: float = 0.0):
        d = g.d
        d.polygon([(60, 9 + y), (68, 9 + y), (64, 14 + y)], fill=1)
        d.line((64, 0, 64, 9 + y), fill=1)
        if blink(t, 1.6, 0.15):
            g.px(64, 15 + y)

    def header(self, g: Gfx, e: float, a: float = 1.0, right: str | None = None):
        left = "二十八宿"
        g.text(2, 1, left[:int(round(a * len(left)))])
        r = right if right is not None else f"{cn_num(int(e // self.CYCLE) + 1)}周天"
        r = r[:int(round(a * len(r)))]
        g.text(126, 1, r, align="right")

    def inner(self, g: Gfx, e: float, cy: float = CY):
        g.text(64, cy - 69, SIXIANG[self.cur(e) // 7], align="center")

    def meteor(self, g: Gfx, e: float):
        """流星：约每 40 秒一颗（按 e 定时）"""
        k = e % 41.0
        if k < 0.7:
            n = int(e // 41)
            x0 = 20 + rand(n, self.seed) * 70
            p = k / 0.7
            for j in range(6):
                q = p - j * 0.04
                if 0 < q < 1:
                    g.px(x0 + q * 30, 2 + q * 10)

    def mx(self, g: Gfx, i: int, t: float, lit: bool = True):
        for chain in ASTER[i]:
            for j, (x, y) in enumerate(chain):
                g.mx_set(x, y, True if lit else blink(t + j * 0.17, 0.5))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        stars(g, t, self.sky, n=int(16 * span(t, 0, 1.0)), box=(0, 0, 128, 18))
        cy = lerp(200, CY, ease_out_back(span(t, 0.3, 2.0), 1.2))
        self.wheel(g, 0.0, cy, hi=0 if t > 2.6 else None)
        self.pointer(g, -16 + 16 * ease_out(span(t, 2.0, 2.6)), t)
        self.header(g, 0, span(t, 2.4, 3.5))
        if t > 2.6:
            self.inner(g, 0)
            g.mx_level = 4 if t < 2.8 else 1
        if t > 2.0:
            self.mx(g, 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        i = self.cur(e)
        stars(g, t, self.sky, n=16, box=(0, 0, 128, 18))
        self.meteor(g, e)
        k = e % self.CYCLE
        renew = e >= self.CYCLE and k < RENEW
        self.wheel(g, self.rot(e), hi=i)
        self.pointer(g, 0, t)
        self.inner(g, e)
        if renew:  # 转满一周：轮缘一圈星光，计数闪动
            for j in range(40):
                a = (j / 40 - 0.5) * 1.6
                if blink(t + j * 0.05, 0.4, 0.5):
                    x, y = polar(R1 + 4 + (k * 8) % 6, a)
                    g.px(x, y)
            self.header(g, e, right=None if blink(k, 0.5, 0.6) else "")
            g.mx_level = 3 if k < 1.5 else 1
        else:
            self.header(g, e)
        self.mx(g, i, t)
        # 最亮的星闪一下
        ch = ASTER[i][0][len(ASTER[i][0]) // 2]
        g.mx_set(ch[0], ch[1], not blink(t, 2.0, 0.1))

    def _cloud(self, g: Gfx, x: float):
        mist(g, cloud_blobs(x, 6, 70, 18, self.seed) + cloud_blobs(x - 40, 12, 46, 14, self.seed + 1), 0.25)

    def interrupt(self, g: Gfx, t: float, e: float):
        i = self.cur(e)
        p = ease_out(span(t, 0, 1.3))
        stars(g, t, self.sky, n=16, box=(0, 0, 128, 18))
        self.wheel(g, self.rot(e), hi=i if blink(t, 0.3) or t < 0.3 else None)
        self.pointer(g, 0, t)
        self.inner(g, e)
        self.header(g, e, right="云掩" if t > 0.8 else None)
        self._cloud(g, lerp(-50, 74, p))
        self.mx(g, i, t, lit=t < 0.6)

    def resume(self, g: Gfx, t: float, e: float):
        i = self.cur(e)
        p = ease_in_out(span(t, 0, 1.3))
        stars(g, t, self.sky, n=16, box=(0, 0, 128, 18))
        self.wheel(g, self.rot(e), hi=i)
        self.pointer(g, 0, t)
        self.inner(g, e)
        self.header(g, e, right="云掩" if t < 0.6 else None)
        if p < 1:
            self._cloud(g, lerp(74, 220, p))
        self.mx(g, i, t, lit=t > 0.9)

    def complete(self, g: Gfx, t: float, e: float):
        base = self.rot(e)
        spin = ease_in_out(span(t, 0.2, 2.6))
        rot = base + spin * 2 * math.pi
        stars(g, t, self.sky, n=16, box=(0, 0, 128, 18))
        i = int((rot % (2 * math.pi)) / SLOT) % 28
        self.wheel(g, rot, hi=i if t < 2.6 else None, t=t,
                   flash=(lambda j: blink(t * 2 + j * 0.37, 0.5, 0.6)) if t > 2.6 else None)
        self.pointer(g, -16 * ease_out(span(t, 2.6, 3.2)), t)
        if t < 2.2:
            self.header(g, e, a=1 - span(t, 1.4, 2.2))
            g.text(64, CY - 69, SIXIANG[i // 7], align="center")
        if t > 2.8:
            g.d.rectangle((24, 0, 104, 15), fill=0)
            typewriter(g, 64, 2, "斗转星移", t - 2.8, cps=5, align="center")
        if t < 2.6:
            self.mx(g, i, t)
        else:
            r = (t - 2.6) * 4
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - r) < 0.8 or rand(x * 8 + y + int(t * 6) * 64, 3) < 0.15:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(4 * (1 - span(t, 2.6, 4.0)))
