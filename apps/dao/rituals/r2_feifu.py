"""飞符：坛上一叠黄符，每隔一阵飞起一道，绕着中央的“敕”字符胆盘旋成阵；九道齐了，
一齐化作流光直上九霄（飞符召将），再起新阵。

依据：飞符召将——符箓“上奏天庭、召请神将”；符命“符到奉行”（“急急如律令”宋人释作“符到奉行”）。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import ring, stars, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import glyph, rays

CX, CY = 64, 30
RX, RY = 44, 12
STACK = (64, 55)
LEAD = 3.0
EVERY = 58.0
NFU = 9
LAUNCH = 2.2
RENEW = 4.0
SLOTS = [(i * 4) % NFU for i in range(NFU)]   # 新符依次占的位置（错开）


@register
class FeiFu(Ritual):
    id = "r2.feifu"
    name = "飞符"
    desc = "坛上黄符一道道飞起，绕“敕”字符胆盘旋成阵；九符齐聚，化作流光直上九霄，再起新阵"
    T = {"enter": 3.5, "interrupt": 1.6, "resume": 1.8, "complete": 5.0}
    CYCLE = LEAD + NFU * EVERY + 15.0   # 540 秒

    def setup(self):
        self.s = self.rng.randrange(1000)

    # ------------------------------------------------------------ 零件

    def n_joined(self, u: float) -> tuple[int, float]:
        """已入阵几道、正在飞起的那道的进度（0..1，-1 表示没有）"""
        if u < LEAD:
            return 0, -1.0
        k = (u - LEAD) / EVERY
        n = min(NFU, int(k) + 1)
        p = ((u - LEAD) - (n - 1) * EVERY) / LAUNCH
        if n == NFU and (u - LEAD) - (NFU - 1) * EVERY > LAUNCH:
            return NFU, -1.0
        if p >= 1:
            return n, -1.0
        return n - 1, p

    def spin(self, t: float, u: float) -> float:
        n, _ = self.n_joined(u)
        return t * (0.45 + 0.05 * n)

    def orbit_pt(self, slot: int, phase: float):
        a = phase + slot / NFU * 2 * math.pi
        return CX + math.cos(a) * RX, CY + math.sin(a) * RY, math.sin(a)

    def fu(self, g: Gfx, x: float, y: float, depth: float, t: float, i: int, flip: float | None = None):
        s = 0.75 + 0.25 * depth
        fl = abs(math.cos(t * 2.5 + i * 1.3)) if flip is None else flip
        w = max(1.0, 7 * s * (0.35 + 0.65 * fl))
        h = 14 * s
        x0, y0, x1, y1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
        g.d.rectangle((x0, y0, x1, y1), fill=0, outline=1)
        if depth > -0.2 and w > 4:  # 正面朝外的才看得清符文
            g.d.line((x, y0 + 2, x, y1 - 2), fill=1)
            g.d.line((x - 1, y0 + 3, x + 1, y0 + 3), fill=1)
            g.d.line((x - 1, y1 - 4, x + 1, y1 - 3), fill=1)
        elif w > 3:
            g.px(x, y)

    def core(self, g: Gfx, t: float, power: float = 1.0, flash: float = 0.0):
        r = 9 + flash * 2
        g.d.ellipse((CX - r, CY - r, CX + r, CY + r), fill=0)
        n = 24
        for i in range(n):  # 转动的虚线圈
            if (i + int(t * 6)) % 3:
                a = i / n * 2 * math.pi
                g.px(CX + math.cos(a) * r, CY + math.sin(a) * r)
        if power > 0.3:
            g.blit(glyph("敕"), CX - 6, CY - 5)
        else:
            g.d.ellipse((CX - 2, CY - 2, CX + 2, CY + 2), outline=1)
        if flash > 0:
            rays(g, CX, CY, r + 2, r + 2 + flash * 8, 12, phase=t)

    def altar(self, g: Gfx, stack_n: int):
        x, y = STACK
        g.d.rectangle((x - 18, y + 2, x + 18, y + 4), fill=1)
        g.d.line((x - 15, y + 5, x - 15, 63), fill=1)
        g.d.line((x + 15, y + 5, x + 15, 63), fill=1)
        g.d.line((x - 15, 61, x + 15, 61), fill=1)
        for j in range(stack_n):  # 一叠符（平放）
            g.d.line((x - 6 + (j % 2), y + 1 - j, x + 6 + (j % 2), y + 1 - j), fill=1)

    def texts(self, g: Gfx, n: int, right: str | None = None, a: float = 1.0):
        left = "飞符召将"
        g.vtext(2, 4, left[:int(round(a * 4))])
        r = right if right is not None else (cn_num(n) + "符" if n else "起阵")
        g.vtext(114, 4, r[:int(round(a * len(r)))])

    def mx(self, g: Gfx, n: int, phase: float, flash: bool = False):
        g.mx[3:5, 3:5] = True
        for i in range(n):
            a = phase + SLOTS[i] / NFU * 2 * math.pi
            g.mx_set(round(3.5 + math.cos(a) * 3.6), round(3.5 + math.sin(a) * 2.6))
        if flash:
            g.mx[2:6, 2:6] = True

    def formation(self, g: Gfx, t: float, u: float, n: int, launch: float, phase: float, pull: float = 0.0,
                  to=None):
        """画阵：先画后面的符，再画符胆，再画前面的符。pull>0 时符被拉向 to（x, y）"""
        items = []
        for i in range(n):
            x, y, d = self.orbit_pt(SLOTS[i], phase)
            if pull > 0:
                tx, ty = to
                x, y = lerp(x, tx, pull), lerp(y, ty, pull)
            items.append((d, x, y, i, None))
        if launch >= 0:
            i = n
            ex, ey, ed = self.orbit_pt(SLOTS[i], phase)
            p = ease_in_out(launch)
            sx, sy = STACK[0], STACK[1] - 2
            x = lerp(sx, ex, p) + math.sin(p * math.pi) * 18 * (1 if SLOTS[i] % 2 else -1)
            y = lerp(sy, ey, p) - math.sin(p * math.pi) * 22
            items.append((ed if p > 0.8 else 1.0, x, y, i, abs(math.cos(p * 6 * math.pi))))
            for j in range(5):  # 尾迹
                q = max(0.0, p - j * 0.05)
                g.px(lerp(sx, ex, q) + math.sin(q * math.pi) * 18 * (1 if SLOTS[i] % 2 else -1),
                     lerp(sy, ey, q) - math.sin(q * math.pi) * 22 + 5)
        items.sort(key=lambda it: it[0])
        for d, x, y, i, fl in items:
            if d < 0:
                self.fu(g, x, y, d, t, i, fl)
        return [it for it in items if it[0] >= 0]

    def path(self, g: Gfx, phase: float):
        """轨道：淡淡的点线椭圆，点随阵转动"""
        n = 56
        for j in range(n):
            if j % 4 == 0:
                a = phase * 0.5 + j / n * 2 * math.pi
                g.px(CX + math.cos(a) * RX, CY + math.sin(a) * RY)

    def scene(self, g: Gfx, t: float, u: float, e: float):
        n, launch = self.n_joined(u)
        phase = self.spin(t, u)
        stars(g, t, self.s, n=10, twinkle=0.35)
        self.path(g, phase)
        self.altar(g, NFU - n - (launch >= 0))
        front = self.formation(g, t, u, n, launch, phase)
        flash = 1 - span(launch, 0.85, 1.0) if launch > 0.85 else 0.0
        if n == NFU and launch < 0:  # 九符齐聚：符胆有节律地放光
            k = (u - LEAD - (NFU - 1) * EVERY - LAUNCH) % 3.0
            flash = max(flash, 1 - span(k, 0, 0.8))
        self.core(g, t, 1.0, flash)
        for d, x, y, i, fl in front:
            self.fu(g, x, y, d, t, i, fl)
        if n == NFU and launch < 0:  # 阵成：环上一圈光点
            for j in range(18):
                a = phase * 1.5 + j / 18 * 2 * math.pi
                if (j + int(t * 8)) % 3 == 0:
                    g.px(CX + math.cos(a) * (RX + 4), CY + math.sin(a) * (RY + 3))
        self.texts(g, n)
        self.mx(g, n, phase, flash > 0.5)
        if flash > 0.5:
            g.mx_level = 3

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        stars(g, t, self.s, n=10, twinkle=0.35)
        p = ease_out_back(span(t, 0, 0.8))
        # 坛与一叠符从下升起
        dy = (1 - p) * 20
        x, y = STACK
        g.d.rectangle((x - 18, y + 2 + dy, x + 18, y + 4 + dy), fill=1)
        g.d.line((x - 15, y + 5 + dy, x - 15, 63), fill=1)
        g.d.line((x + 15, y + 5 + dy, x + 15, 63), fill=1)
        for j in range(NFU):
            g.d.line((x - 6 + (j % 2), y + 1 - j + dy, x + 6 + (j % 2), y + 1 - j + dy), fill=1)
        if t > 0.8:  # 符胆：一点光从坛上升起，展开成圈
            k = span(t, 0.8, 2.2)
            yy = lerp(STACK[1] - 10, CY, ease_out(k))
            if k < 1:
                g.d.ellipse((CX - 2, yy - 2, CX + 2, yy + 2), fill=1)
                for j in range(4):
                    g.px(CX + rand(j + int(t * 20), 3) * 4 - 2, yy + 4 + j * 2)
            else:
                r = ease_out_back(span(t, 2.2, 2.8))
                if r > 0.9:
                    self.core(g, t, 1.0, 1 - span(t, 2.4, 3.2))
                else:
                    ring(g, CX, CY, 9 * r, 1)
        if t > 2.6:  # 轨道一闪
            for j in range(0, 60, 3):
                a = j / 60 * 2 * math.pi
                if rand(j, 4) < span(t, 2.6, 3.5):
                    g.px(CX + math.cos(a) * RX, CY + math.sin(a) * RY)
        self.texts(g, 0, a=span(t, 2.2, 3.5))
        g.mx[3:5, 3:5] = t > 2.2
        g.mx_level = 4 if 2.2 < t < 2.5 else 1

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, e)
            return
        self.scene(g, t, u, e)

    def _renew(self, g: Gfx, t: float, u: float, e: float):
        """九符依次化作流光，直上九霄"""
        stars(g, t, self.s, n=10, twinkle=0.35)
        self.altar(g, NFU if u > 3.0 else 0)
        phase = t * 0.9
        self.core(g, t, 1.0, 1 - span(u, 2.8, 3.6) if u > 2.8 else 0.4)
        for i in range(NFU):
            x, y, d = self.orbit_pt(SLOTS[i], phase)
            t0 = i * 0.25
            k = span(u, t0, t0 + 0.6)
            if k <= 0:
                self.fu(g, x, y, d, t, i)
            elif k < 1:  # 拉成一道竖直的光
                top = lerp(y, -20, ease_in(k))
                g.d.line((x, y + 5 - k * 10, x, top), fill=1)
                g.d.line((x + 1, y + 5 - k * 10, x + 1, top + 6), fill=1)
        if 2.4 < u < 2.7:  # 天上回应一道光
            rays(g, 64, -6, 6, 26, 9, phase=math.pi * 0.05)
            g.mx_level = 6
        self.texts(g, 0 if u > 3.0 else NFU, right="召将" if 1.0 < u < 3.0 else None)
        self.mx(g, NFU - min(NFU, int(u / 0.25)), phase, 2.4 < u < 2.7)

    def interrupt(self, g: Gfx, t: float, e: float):
        """符阵收落，一道道回到坛上"""
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        n, launch = self.n_joined(u)
        if launch >= 0:
            n += 1
        phase = self.spin(0, u) + t * 0.45 * (1 - span(t, 0, 1.2))
        pull = ease_in_out(span(t, 0.1, 1.3))
        stars(g, t, self.s, n=10, twinkle=0.35)
        landed = int(n * span(t, 1.1, 1.4))
        self.altar(g, NFU - n + landed)
        front = self.formation(g, t, u, n, -1, phase, pull=pull, to=(STACK[0], STACK[1] - 4))
        self.core(g, t, 1 - span(t, 0.6, 1.4))
        if t < 1.3:
            for d, x, y, i, fl in front:
                self.fu(g, x, y, d, t, i, fl)
        self.texts(g, n, right="落符")
        g.mx[3:5, 3:5] = True
        if t < 1.0:
            self.mx(g, n, phase)

    def resume(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        n, launch = self.n_joined(u)
        phase = self.spin(t, u)
        pull = 1 - ease_out(span(t, 0.4, 1.8))
        stars(g, t, self.s, n=10, twinkle=0.35)
        self.altar(g, NFU - n - (launch >= 0) if t > 0.4 else NFU - n - (launch >= 0) + n)
        front = self.formation(g, t, u, n, launch if t > 1.2 else -1, phase, pull=pull,
                               to=(STACK[0], STACK[1] - 4)) if t > 0.4 else []
        self.core(g, t, span(t, 0, 0.6), 1 - span(t, 0.2, 0.8))
        for d, x, y, i, fl in front:
            self.fu(g, x, y, d, t, i, fl)
        self.texts(g, n)
        self.mx(g, n if t > 0.4 else 0, phase)

    def complete(self, g: Gfx, t: float, e: float):
        """符阵合一，化作一道光柱冲天：符到奉行"""
        u = e % self.CYCLE
        n, launch = self.n_joined(u)
        n = max(n, 1)
        phase = t * (0.9 + t)
        stars(g, t, self.s, n=10, twinkle=0.35)
        self.altar(g, max(0, NFU - n - int(span(t, 0, 0.5 + 0.06 * NFU) * (NFU - n + 0.99))))
        pull = ease_in(span(t, 0.7, 1.5))
        if t < 1.5:  # 坛上剩下的符一齐飞起入阵，九符合一
            self.core(g, t, 1.0, span(t, 0.8, 1.5))
            for i in range(NFU):
                x, y, d = self.orbit_pt(SLOTS[i], phase)
                if i >= n:
                    k = ease_out(span(t, 0.06 * (i - n), 0.5 + 0.06 * (i - n)))
                    if k <= 0:
                        continue
                    x, y = lerp(STACK[0], x, k), lerp(STACK[1] - 2, y, k)
                x, y = lerp(x, CX, pull), lerp(y, CY, pull)
                self.fu(g, x, y, d, t, i)
        else:
            k = t - 1.5
            w = 1 + 2 * (1 - span(k, 0.4, 2.5))
            top = lerp(CY, -10, ease_out(span(k, 0, 0.4)))
            g.d.rectangle((CX - w, top, CX + w, CY), fill=1)  # 光柱
            for side in (-1, 1):  # 两侧往上流的光
                for j in range(6):
                    y0 = CY - ((k * 60 + j * 8) % 48)
                    xx = CX + side * (w + 3)
                    g.d.line((xx, y0, xx, y0 - 4), fill=1)
            self.core(g, t, 1.0, 1 - span(k, 0, 1.0))
            for j in range(10):  # 光柱两旁上升的光点
                yy = CY - ((k * 50 + j * 9) % 40)
                g.px(CX + (12 + rand(j, 5) * 8) * (1 if j % 2 else -1), yy)
            if k < 0.12:
                g.invert()
            if k > 0.8:
                g.d.rectangle((CX - 30, 40, CX + 30, 53), fill=0)
                typewriter(g, CX, 41, "符到奉行", k - 0.8, cps=5, align="center")
        self.texts(g, n, right="召将")
        g.mx[3:5, 3:5] = True
        if t > 1.5:
            col = int((t - 1.5) * 12)
            for y in range(max(0, 4 - col), 5):
                g.mx[y, 3] = g.mx[y, 4] = True
            g.mx_level = 1 + int(6 * (1 - span(t, 1.5, 3.0)))
        else:
            self.mx(g, n, phase)
