"""小周天：静室里小道士坐在蒲团上闭目打坐，一颗光点沿督脉上行、任脉下行绕身运转（河车搬运）。

依据：内丹“河车搬运”，精气自会阴沿督脉（背）上行，过尾闾、夹脊、玉枕“三关”，到泥丸，再经印堂、鹊桥沿任脉（前）
下降，过膻中归丹田。参考 goldenelixir.com「xiao zhoutian」、Wikipedia「Microcosmic orbit」。
入场：静室渐显，小道士盘坐蒲团，双手叠放，闭目；丹田亮起一点，沉到会阴、转到尾闾。
持续：光点带尾巴沿“会阴→尾闾→夹脊→玉枕→泥丸→印堂→鹊桥→膻中→丹田”循环，一周 9 秒；过三关时关窍菱形一亮、
      迸出火星，右上角弹出关名；丹田之丹随一转（10 分钟）慢慢长大。墙上圆窗里一弯月，香炉烟缕缕；
      每隔一阵小事件：月亮被一片云遮过 / 一只飞蛾绕着香炉转。
      续：丹田一震放出两圈光，“某转”，左上“第几转”加一。
中断：光点顺任脉滑回丹田、熄灭，睁眼，“收功”。  恢复：丹田重新亮起，光点从丹田出发追到当前位置。
圆满：光点越转越快连成一道光环，三关全亮，头顶放光，闪白，“炼精化气”。
点阵：外圈 28 格是周天，光点带尾巴跑；中间 2×2 是丹田，闪烁占空比随进度变大。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, span
from ..engine.chars import Part
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import P, Clock, cached, counter, dao, label, mx_ring, orb, pop_title, ring, star

FLOOR = 58
SY = FLOOR - 3          # 坐在蒲团上
DX = 46
LOOP = 9.0
SIT = P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"), face="sleep")
SIT_OPEN = P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"))

# 周天路线（相对盘坐小道士脚底中点；背在左、面朝右），名称 / 是否关窍
ROUTE = [
    ("会阴", (0, -2), False), ("尾闾", (-9, -6), True), ("夹脊", (-10, -15), True), ("玉枕", (-11, -27), True),
    ("泥丸", (-2, -38), False), ("印堂", (10, -29), False), ("鹊桥", (11, -21), False), ("膻中", (11, -15), False),
    ("丹田", (10, -8), False), ("会阴", (0, -2), False),
]


def _seglen():
    out = [0.0]
    for i in range(len(ROUTE) - 1):
        (x0, y0), (x1, y1) = ROUTE[i][1], ROUTE[i + 1][1]
        out.append(out[-1] + math.hypot(x1 - x0, y1 - y0))
    return out


CUM = _seglen()


def route_pt(q: float):
    """q ∈ [0,1) 沿路线的位置（按弧长；路线是折线，转角处稍作圆滑）"""
    s = (q % 1.0) * CUM[-1]
    for i in range(len(CUM) - 1):
        if CUM[i] <= s <= CUM[i + 1]:
            k = (s - CUM[i]) / max(CUM[i + 1] - CUM[i], 1e-6)
            (x0, y0), (x1, y1) = ROUTE[i][1], ROUTE[i + 1][1]
            bulge = math.sin(k * math.pi) * (1.5 if i in (3, 4) else 0.6)
            nx, ny = (y1 - y0), -(x1 - x0)
            L = math.hypot(nx, ny) or 1
            return x0 + (x1 - x0) * k + nx / L * bulge, y0 + (y1 - y0) * k + ny / L * bulge
    return ROUTE[0][1]


GATE_Q = [CUM[i] / CUM[-1] for i, r in enumerate(ROUTE) if r[2]]
GATE_N = [r[0] for r in ROUTE if r[2]]
GATE_P = [r[1] for r in ROUTE if r[2]]
DANTIAN_Q = CUM[8] / CUM[-1]


def _cushion():
    """蒲团 30×6：编草的圆垫，一圈圈草纹"""
    p = Part(30, 7)
    p.shape("ellipse", (0, 0, 29, 6), fill=1)
    for x in range(3, 27, 3):
        p.px(x, 2, 0), p.px(x + 1, 4, 0)
    p.d.arc((2, 1, 27, 6), 0, 180, fill=0)
    return p.sprite()


def _window():
    """圆窗 33×33：窗框双圈、窗台"""
    p = Part(35, 35)
    p.shape("ellipse", (0, 0, 34, 34), fill=1)
    p.d.ellipse((2, 2, 32, 32), fill=0)
    p.d.ellipse((3, 3, 31, 31), outline=1)
    p.d.ellipse((4, 4, 30, 30), fill=0)
    return p.sprite()


def _censer():
    """地上的小香炉 11×9"""
    p = Part(11, 9)
    p.shape("rectangle", (0, 2, 10, 3), fill=1)
    p.shape("polygon", [(1, 4), (9, 4), (8, 7), (2, 7)], fill=1)
    p.px(1, 0), p.px(9, 0), p.shape("rectangle", (1, 0, 1, 2), fill=1), p.shape("rectangle", (9, 0, 9, 2), fill=1)
    p.d.line((2, 5, 8, 5), fill=0)
    p.shape("rectangle", (2, 8, 3, 8), fill=1), p.shape("rectangle", (7, 8, 8, 8), fill=1)
    p.dither([(6, 4), (9, 4), (8, 7), (6, 7)], 0.5, 0)
    return p.sprite()


def _scroll():
    """墙上挂轴 13×30：天杆、山水小景、地杆"""
    p = Part(13, 30)
    p.shape("rectangle", (0, 0, 12, 1), fill=1)
    p.px(6, 0, 0)
    p.d.rectangle((1, 2, 11, 27), outline=1)
    p.d.polygon([(2, 20), (5, 12), (7, 15), (9, 10), (10, 20)], fill=1)
    p.dither([(7, 15), (9, 10), (10, 20), (7, 20)], 0.5, 0)
    p.d.ellipse((3, 5, 5, 7), outline=1)
    for x in range(2, 11, 2):
        p.px(x, 23)
    p.shape("rectangle", (0, 28, 12, 29), fill=1)
    return p.sprite()


MOTH = pix.frames("""
# #
 #
---
 #
###
""")


def room(g: Gfx, t: float, e: float):
    """静室：板壁、圆窗（月、远山）、挂轴、地上香炉、蒲团"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-6, 140, 12):
        g.d.line((x, FLOOR + 1, x - 3, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    # 圆窗
    wx, wy = 84, 6
    pix.blit(g, cached(("ob", "win"), _window), wx, wy)
    cx, cy = wx + 17, wy + 17
    for x in range(cx - 12, cx + 13):
        y = cy + 6 - 3 * math.sin((x - cx) * 0.3) - 2 * math.sin((x - cx) * 0.7)
        if (x - cx) ** 2 + (y - cy) ** 2 < 12 ** 2:
            g.px(x, y)
    mx_, my = cx + 4, cy - 5
    g.d.ellipse((mx_ - 4, my - 4, mx_ + 4, my + 4), fill=1)
    g.d.ellipse((mx_ - 1, my - 6, mx_ + 6, my + 2), fill=0)     # 月牙
    # 小事件：月被云遮（按 e）
    ph = (e % 37) / 6.0
    if ph < 1 and int(e // 37) % 2 == 0:
        x = lerp(cx - 18, cx + 18, ph)
        for dx, r in ((0, 3), (4, 2), (-4, 2)):
            if (x + dx - cx) ** 2 + (my - cy) ** 2 < 11 ** 2:
                g.d.ellipse((x + dx - r, my - r + 1, x + dx + r, my + r + 1), fill=1)
        g.d.line((x - 6, my + 3, x + 6, my + 3), fill=0)
    pix.blit(g, cached(("ob", "scroll"), _scroll), 8, 8)
    pix.blit(g, cached(("ob", "censer"), _censer), 104, FLOOR - 9)
    pix.blit(g, cached(("ob", "cushion"), _cushion), DX - 15, FLOOR - 6)


@register
class Orbit(Ritual):
    id = "r4.orbit"
    name = "小周天"
    desc = "静室里小道士盘坐蒲团闭目，一颗光点沿督脉上行、任脉下行绕身运转，过尾闾夹脊玉枕三关时放亮"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()

    def smoke(self, g: Gfx, t: float, dt: float, e: float):
        if int(t * 1.6) != int((t - dt) * 1.6):
            self.puffs.emit(109, FLOOR - 11, vx=1, vy=-5, life=2.6, rmax=1.3, spread=1)
        self.puffs.step(dt, wind=math.sin(t * 0.5) * 2)
        self.puffs.draw(g)
        ph = (e % 37) / 6.0
        if ph < 1 and int(e // 37) % 2 == 1:  # 飞蛾绕着香炉
            a = ph * 4 * math.pi
            pix.blit(g, pix.anim(MOTH, t, 8), 108 + math.cos(a) * 9, FLOOR - 20 + math.sin(a) * 4, outline=False)

    def path(self, g: Gfx, lit_all: bool = False):
        """经脉：点线；三关：小菱形"""
        for j in range(0, 120, 3):
            x, y = route_pt(j / 120)
            g.px(DX + x, SY + y)
        for (x, y) in GATE_P:
            cx, cy = DX + x, SY + y
            g.d.polygon([(cx, cy - 2), (cx + 2, cy), (cx, cy + 2), (cx - 2, cy)], outline=1, fill=1 if lit_all else 0)

    def light(self, g: Gfx, t: float, q: float, tail: int = 7, step: float = 0.012):
        """光点 + 尾巴"""
        for j in range(tail, 0, -1):
            x, y = route_pt(q - j * step)
            if j < 4 or j % 2 == 0:
                g.px(DX + x, SY + y)
        x, y = route_pt(q)
        orb(g, DX + x, SY + y, 1, t)

    def dan(self, g: Gfx, t: float, prog: float, bright: float = 1.0):
        """丹田之丹（随进度变大）"""
        x, y = DX + ROUTE[8][1][0] - 3, SY + ROUTE[8][1][1]
        r = 0.6 + prog * 2.2
        if bright <= 0:
            return
        g.d.ellipse((x - r - 1, y - r - 1, x + r + 1, y + r + 1), fill=0)
        if (t * 3) % 1 < 0.5 + 0.5 * bright:
            g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
        else:
            g.d.ellipse((x - r, y - r, x + r, y + r), outline=1)

    def gate_fx(self, g: Gfx, q: float, dq: float):
        """光点过关：菱形放亮 + 火星。返回刚过的关（0–2）与过关后的秒数比例"""
        hit = None
        for i, gq in enumerate(GATE_Q):
            d = (q - gq) % 1.0
            if d < 0.12:
                x, y = GATE_P[i]
                cx, cy = DX + x, SY + y
                g.d.polygon([(cx, cy - 3), (cx + 3, cy), (cx, cy + 3), (cx - 3, cy)], fill=1)
                if d < dq:
                    self.sparks.burst(cx, cy, 8, 16, life=0.5, gravity=0)
                hit = (i, d)
        return hit

    def mx(self, g: Gfx, t: float, q: float, prog: float):
        """外圈 28 格：从下边中间（会阴）起，沿左边上行（督脉）、过顶、沿右边下行（任脉）"""
        cells = [(7, x) for x in range(3, -1, -1)] + [(y, 0) for y in range(6, 0, -1)] + \
                [(0, x) for x in range(8)] + [(y, 7) for y in range(1, 7)] + [(7, x) for x in range(7, 3, -1)]
        n = len(cells)
        i0 = int(q * n)
        for j in range(4):
            y, x = cells[(i0 - j) % n]
            if j < 2 or int(t * 8) % 2:
                g.mx[y, x] = True
        if (t * 2) % 1 < 0.2 + 0.7 * prog:
            g.mx[3:5, 3:5] = True

    def labels(self, g: Gfx, e: float, hit):
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}转" if n < 100 else f"{n}转")
        if hit and hit[1] < 0.1:
            label(g, 78, 44, GATE_N[hit[0]], 12, "left", box=True)

    def figure(self, g: Gfx, t: float, open_eyes: bool = False):
        return dao(g, DX, SY, SIT_OPEN if open_eyes else SIT, t)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        room(g, t, 0)
        self.figure(g, t, t < 2.2)
        if t > 1.5:
            self.path(g)
        if 2.2 < t < 3.4:   # 丹田亮起
            self.dan(g, t, 0.0, span(t, 2.2, 2.6))
            if abs(t - 2.2) < dt:
                self.sparks.burst(DX + 7, SY - 8, 10, 16, life=0.5, gravity=0)
        if t >= 3.4:        # 沉到会阴、转到尾闾
            q = lerp(DANTIAN_Q, 1.0 + 0.04, ease_in_out(span(t, 3.4, 5.0)))
            self.light(g, t, q % 1.0, tail=3)
        self.smoke(g, t, dt, 0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, 0.0, 0.0)
        if t > 2.4:
            label(g, 78, 44, "凝神", 12, "left", box=True)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        prog = k / self.CYCLE
        room(g, t, e)
        self.figure(g, t)
        self.path(g)
        q = (e / LOOP) % 1.0
        hit = self.gate_fx(g, q, dt / LOOP)
        self.light(g, t, q)
        self.dan(g, t, prog)
        renew = e >= self.CYCLE and k < 5.0
        if renew:
            for j in range(2):
                r = span(k, j * 0.5, 2.5 + j * 0.5) * 30
                if 0 < r < 30:
                    ring(g, DX + 7, SY - 8, r, dotted=2, ry=r * 0.6)
            if abs(k - 0.05) < dt:
                pix.flash(g)
                self.sparks.burst(DX + 7, SY - 8, 18, 30, life=0.8, gravity=10)
            if k < 0.3:
                pix.shake(g, t, 1.0)
        self.smoke(g, t, dt, e)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, q, prog)
        if renew and k > 0.4:
            n = int(e // self.CYCLE)
            counter(g, f"第{cn_num(n + 1)}转" if n < 99 else f"{n + 1}转")
            pop_title(g, 98, 44, f"{cn_num(n)}转" if n < 100 else f"{n}转", span(k, 0.4, 0.8), t)
        else:
            self.labels(g, e, hit)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        room(g, t, e)
        self.figure(g, t, t > 1.1)
        self.path(g)
        q0 = (e / LOOP) % 1.0
        # 顺路线前进到丹田（最多走一段），熄灭
        target = DANTIAN_Q if q0 <= DANTIAN_Q else DANTIAN_Q + 1
        q = lerp(q0, target, ease_in_out(span(t, 0, 0.9)))
        if t < 1.0:
            self.light(g, t, q % 1.0, tail=4)
        self.dan(g, t, k / self.CYCLE, 1 - span(t, 0.9, 1.5))
        if abs(t - 0.9) < dt:
            self.puffs.emit(DX + 7, SY - 9, vy=-4, life=0.8, rmax=2.2, spread=0)
        self.smoke(g, t, dt, e)
        self.mx(g, t, q % 1.0, k / self.CYCLE)
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}转" if n < 100 else f"{n}转")
        if t > 0.6:
            label(g, 78, 44, "收功", 12, "left", box=True)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        room(g, t, e)
        self.figure(g, t, t < 0.4)
        self.path(g)
        q1 = (e / LOOP) % 1.0
        self.dan(g, t, k / self.CYCLE, span(t, 0.3, 0.7))
        if abs(t - 0.5) < dt:
            self.sparks.burst(DX + 7, SY - 8, 10, 16, life=0.5, gravity=0)
        if t > 0.7:
            start = DANTIAN_Q
            end = q1 if q1 >= start else q1 + 1
            q = lerp(start, end, ease_in_out(span(t, 0.7, 2.0)))
            self.light(g, t, q % 1.0)
        self.smoke(g, t, dt, e)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, q1, k / self.CYCLE)
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}转" if n < 100 else f"{n}转")

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        room(g, t, e)
        self.figure(g, t, t > 4.0)
        lit = t > 2.4
        self.path(g, lit_all=lit)
        # 越转越快：转速积分
        speed = lambda tt: 1 / LOOP + 2.5 * span(tt, 0, 2.4) ** 2  # noqa: E731
        q = (e / LOOP + t / LOOP + 2.5 * (min(t, 2.4) ** 3) / (3 * 2.4 ** 2)) % 1.0
        if t < 2.4:
            self.light(g, t, q, tail=int(7 + 30 * span(t, 0.5, 2.4)), step=0.012)
        else:  # 连成光环
            for j in range(0, 120, 1 if int(t * 10) % 2 else 2):
                x, y = route_pt(j / 120)
                g.px(DX + x, SY + y)
        self.dan(g, t, 1.0)
        if t > 2.4:  # 头顶放光
            tx, ty = DX - 2, SY - 40
            for j in range(9):
                a = -math.pi + j * math.pi / 8
                r0, r1 = 3, 8 + (j % 2) * 5 + math.sin(t * 8 + j) * 1.5
                pix.dotted(g, tx + math.cos(a) * r0, ty + math.sin(a) * r0, tx + math.cos(a) * r1,
                           ty + math.sin(a) * r1, 2, int(t * 10))
            star(g, tx, ty, 2)
        if abs(t - 2.4) < dt:
            pix.flash(g)
            self.sparks.burst(DX - 2, SY - 40, 24, 36, life=1.0, gravity=10)
        if 2.4 < t < 2.7:
            pix.shake(g, t, 1.3)
        self.smoke(g, t, dt, e)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, q, 1.0)
        if t > 2.4:
            mx_ring(g, (t - 2.4) * 4 % 5)
            g.mx_level = 1 + int(6 * (1 - span(t, 2.4, 3.8)))
        if t > 2.8:
            pop_title(g, 100, 44, "炼精化气", span(t, 2.8, 3.2), t)
        else:
            n = int(e // self.CYCLE)
            counter(g, f"第{cn_num(max(n, 1))}转" if n < 100 else f"{n}转")
