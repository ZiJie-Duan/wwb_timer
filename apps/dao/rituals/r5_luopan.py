"""寻龙：小道士托着罗盘翻山越岭寻龙脉，走走停停，立向、点穴。

依据：罗盘由方形地盘与圆形天盘组成，中央天池磁针，盘上有先天八卦与二十四山（壬子癸丑艮寅甲卯乙辰巽巳丙午丁未坤申庚酉辛戌乾亥，
子在北），地盘红线（天心十道）定坐向；形势派“寻龙点穴”：龙脉起伏而来，龙止气聚处为穴，“龙真穴的”。

画面：横卷的山野——远处连绵的山（有一道气沿山脊流动，是龙脉），近处起伏的山岗、松、石、草；小道士双手托罗盘往右走，
地势高他就爬坡、低就下坡。
持续：一轮六站（每站 100 秒）：走 55 秒（山景横移）→ 停下举盘：右上弹出罗盘特写，天盘转动、磁针乱摆后渐稳，
      左上写出坐向（“坐子向午”）；他抬头看山、伸手指点；然后收盘再走。第六站是穴：
      地上隆起一座圆丘，他插下令旗，穴上放光、一圈圈气纹，“点穴”。
      续：下一轮开头拔起令旗，接着赶路。
中断：浓雾从右边涌来罩住群山，磁针停摆，“雾锁”。  恢复：雾向左散去，磁针轻颤。
圆满：插旗点穴，光芒四射、气纹扩散，“龙真穴的”。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r5_util import GRASS, Clock, cached, cloud_sprite, label, pine, pop_box, rays, ring, rock

SHAN = "子癸丑艮寅甲卯乙辰巽巳丙午丁未坤申庚酉辛戌乾亥壬"   # 二十四山，从北（子）起顺时针
GUA8 = ["坎", "艮", "震", "巽", "离", "坤", "兑", "乾"]          # 后天八卦方位（北起顺时针）
DX = 34                    # 小道士在屏幕上的位置
STATION = 100.0
WALK = 55.0
SPEED = 6.0
LX, LY, LR = 105, 20, 17   # 罗盘特写


HOLE = 6 * WALK * SPEED      # 每轮的穴在世界坐标里相隔这么远（第 n 个穴在 n*HOLE + 84）


def hole_x(xw: float) -> float:
    n = max(1, round((xw - 84) / HOLE))
    return n * HOLE + 84


def ground_y(xw: float) -> float:
    """近岗：两道正弦叠加；穴处隆起一座圆丘"""
    y = 55 + 3.5 * math.sin(xw / 23) + 1.5 * math.sin(xw / 9.1 + 1)
    return y - 13 * math.exp(-((xw - hole_x(xw)) / 10) ** 2)


def far_y(xw: float) -> float:
    """远山山脊（锯齿峰）"""
    i = math.floor(xw / 18)
    f = xw / 18 - i
    h0 = 18 + rand(i, 3) * 16
    h1 = 18 + rand(i + 1, 3) * 16
    peak = 1 - abs(f - 0.5) * 2
    return 48 - lerp(h0, h1, f) * 0.6 - peak * 6


def luopan_face(g: Gfx, dial: float, needle: float, k: float = 1.0, glow: bool = False):
    """罗盘特写：方地盘（双边框、四角钉）、天盘三圈：二十四山刻度、八卦、天池磁针；天心十道两条线。
    dial：天盘转角；needle：磁针偏离正北的角度（弧度）"""
    if k <= 0:
        return
    s = ease_out_back(k)
    R = LR * s
    x0, y0, x1, y1 = LX - R - 2, LY - R - 2, LX + R + 2, LY + R + 2
    g.d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=0)
    g.d.rectangle((x0, y0, x1, y1), outline=1)
    g.d.rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), outline=1)
    pix.checker(g, (x0 + 1, y0 + 1, x1, y0 + 2), 0.5)
    if R < 6:
        return
    for cx, cy in ((x0 + 4, y0 + 4), (x1 - 4, y0 + 4), (x0 + 4, y1 - 4), (x1 - 4, y1 - 4)):
        g.px(cx, cy)
    r1, r2, r3, r4 = R - 2, R * 0.72, R * 0.46, R * 0.3
    g.d.ellipse((LX - r1, LY - r1, LX + r1, LY + r1), fill=0, outline=1)
    g.d.ellipse((LX - r2, LY - r2, LX + r2, LY + r2), outline=1)
    g.d.ellipse((LX - r3, LY - r3, LX + r3, LY + r3), outline=1)
    for i in range(24):                         # 二十四山：刻度，正四方加长
        a = dial + i * math.pi / 12 - math.pi / 2
        rr = r2 + (r1 - r2) * (0.2 if i % 2 else 0.5)
        g.d.line((LX + math.cos(a) * rr, LY + math.sin(a) * rr, LX + math.cos(a) * r1, LY + math.sin(a) * r1), fill=1)
        if i % 6 == 0:
            g.px(LX + math.cos(a + 0.13) * (r1 - 2), LY + math.sin(a + 0.13) * (r1 - 2))
    for i, name in enumerate(GUA8):             # 八卦：三道短线（阳实阴断）
        a = dial + i * math.pi / 4 - math.pi / 2
        from ..engine.symbols import TRIGRAMS
        bits = TRIGRAMS[name][2]
        ux, uy = math.cos(a), math.sin(a)
        tx, ty = -uy, ux
        for j, b in enumerate(bits):
            rr = r3 + 1 + j * 1.6
            px, py = LX + ux * rr, LY + uy * rr
            if b:
                g.d.line((px - tx * 1.5, py - ty * 1.5, px + tx * 1.5, py + ty * 1.5), fill=1)
            else:
                g.px(px - tx * 1.5, py - ty * 1.5), g.px(px + tx * 1.5, py + ty * 1.5)
    g.d.ellipse((LX - r4, LY - r4, LX + r4, LY + r4), fill=0, outline=1)   # 天池
    a = needle - math.pi / 2
    nx, ny = math.cos(a) * (r4 - 1), math.sin(a) * (r4 - 1)
    g.d.polygon([(LX + nx, LY + ny), (LX - ny * 0.3, LY + nx * 0.3), (LX + ny * 0.3, LY - nx * 0.3)], fill=1)
    g.d.line((LX, LY, LX - nx, LY - ny), fill=1)
    g.px(LX, LY, 0)
    for i in range(int(x0 + 3), int(x1 - 2), 2):   # 天心十道（红线）
        if abs(i - LX) > r4:
            g.px(i, LY)
    for j in range(int(y0 + 3), int(y1 - 2), 2):
        if abs(j - LY) > r4:
            g.px(LX, j)
    if glow:
        pix.checker(g, (x0 + 3, y0 + 3, x1 - 2, y0 + 4), 0.5)


def tiny_luopan(g: Gfx, hx: float, hy: float):
    """手上托着的罗盘（侧面）：方盘 + 圆盘一线 + 中心针点"""
    g.d.rectangle((hx - 5, hy - 2, hx + 3, hy - 1), fill=1)
    g.d.line((hx - 4, hy - 3, hx + 2, hy - 3), fill=1)
    g.px(hx - 1, hy - 4)
    g.px(hx - 4, hy - 1, 0), g.px(hx + 2, hy - 1, 0)


@register
class LuoPan(Clock, Ritual):
    id = "r5.luopan"
    name = "寻龙"
    desc = "小道士托罗盘翻山寻龙脉，山景横移；每站停下举盘，罗盘特写里天盘转动、磁针渐稳，定出坐向；最后插旗点穴"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)

    # ------------------------------------------------------------ 时间线

    def where(self, e: float):
        """→ (轮 c, 站 st, 站内 tau, 世界横移 S)"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        st = min(int(k // STATION), 5)
        tau = k - st * STATION
        w = min(tau, WALK) * SPEED
        if c >= 1 and st == 0:            # 续：先收旗（4 秒），再赶路（稍快一点补上）
            w = max(0.0, min(tau, WALK) - 4.0) / (WALK - 4.0) * WALK * SPEED
        S = (c * 6 + st) * WALK * SPEED + w
        return c, st, tau, S

    def mountain(self, c: int, st: int) -> int:
        """这一站的“坐”山（0..23）"""
        return int(rand(c * 7 + st, self.seed + 11) * 24)

    def needle(self, tau: float, t: float, settle_from: float) -> float:
        q = tau - settle_from
        if q < 0:
            return math.sin(t * 9) * 0.6
        return math.sin(q * 7) * 0.9 * math.exp(-q * 0.9) + math.sin(t * 13) * 0.02

    # ------------------------------------------------------------ 景

    def land(self, g: Gfx, S: float, t: float):
        """远山（视差 0.3）+ 龙脉气流 + 近岗（随 S 横移，穴处有圆丘）+ 草木石"""
        F = S * 0.3
        pts = [(x, far_y(x + F)) for x in range(0, 129, 2)]
        g.d.line(pts, fill=1)
        mk = np.zeros((64, 128), bool)
        sh = np.zeros((64, 128), bool)
        for x in range(128):                        # 山体淡网点，背光坡（右坡）加密
            y = int(far_y(x + F))
            if far_y(x + 1 + F) > far_y(x + F):
                sh[y + 1:y + 5, x] = True
        pix.checker_mask(g, sh, 0.5)
        for j in range(6):                          # 龙脉：一串气点沿山脊流动
            x = (t * 14 + j * 5) % 150 - 10
            if 0 <= x < 128:
                g.px(x, far_y(x + F) - 2)
        # 近岗
        top = [(x, ground_y(x + S)) for x in range(0, 129)]
        g.d.polygon(top + [(128, 64), (0, 64)], fill=0)
        g.d.line(top, fill=1)
        mk = np.zeros((64, 128), bool)
        for x, y in top:
            if x < 128:
                mk[int(y) + 2:, x] = True
        pix.checker_mask(g, mk, 0.25)
        base = int(S // 16)
        for i in range(base - 1, base + 10):        # 草木石：世界坐标上的固定位置
            xw = i * 16 + rand(i, 5) * 8
            x = xw - S
            if not -12 < x < 132:
                continue
            y = ground_y(xw)
            r = rand(i, 6)
            if abs(xw - hole_x(xw)) < 16:
                continue
            if r < 0.18:
                pix.blit(g, pine(), x - 5, y - 15)
            elif r < 0.3:
                pix.blit(g, rock(), x - 5, y - 4)
            elif r < 0.75:
                pix.blit(g, pix.anim(GRASS, t * 0.7 + r * 3, 2), x - 2, y - 3)

    still = False

    def walker(self, g: Gfx, S: float, t: float, walking: bool, pose: str = "offer"):
        y = ground_y(DX + S)
        walking = walking and not self.still
        if walking:
            h = figure(g, DX, y, t, legs="walk", arm="offer")
            tiny_luopan(g, *h["hand"])
            return h
        h = daoshi(g, DX, y, pose, t)
        if pose == "offer":
            tiny_luopan(g, h["hand"][0], h["hand"][1] - 1)
        return h

    def station(self, g: Gfx, c: int, st: int, tau: float, S: float, t: float, dt: float):
        """站内：走 → 停下举盘看向 → 收盘；第六站点穴"""
        hole = st == 5
        self.land(g, S, t)
        if c >= 1 and st == 0 and tau < 4:            # 续：举手一招，令旗拔起、飞回手里
            h = daoshi(g, DX, ground_y(DX + S), "raise" if tau < 3 else "idle", t, face="happy")
            q = span(tau, 0.8, 2.2)
            if q <= 0:
                self.flag(g, 1.0, t, S)
            elif q < 1:
                hx, hy = h["hand"]
                fx = lerp(84, hx, ease_in_out(q))
                fy = lerp(ground_y(S + 84) - 16, hy, ease_in_out(q)) - math.sin(q * math.pi) * 10
                g.d.line((fx, fy, fx, fy + 12), fill=1)
                g.d.polygon([(fx + 1, fy), (fx + 7, fy + 2), (fx + 1, fy + 5)], fill=1)
            if 2.2 <= tau < 2.6:
                from .r5_util import sparkle
                sparkle(g, h["hand"][0], h["hand"][1], span(tau, 2.2, 2.6))
            return None
        if tau < WALK:
            self.walker(g, S, t, True)
            return None
        q = tau - WALK
        if hole:
            return self.dig(g, q, S, t, dt)
        if q < 34:
            pose = "point" if 18 < q < 24 else "offer"
            self.walker(g, S, t, False, pose)
            k = span(q, 0.3, 1.0) * (1 - span(q, 32, 34))
            return k, q
        self.walker(g, S, t, False, "gongshou" if q < 40 else "idle")
        return None

    def flag(self, g: Gfx, k: float, t: float, S: float):
        """穴上的令旗（插在最近的穴丘顶上）"""
        if k <= 0:
            return
        hx = hole_x(S + 84)
        x = hx - S
        y = ground_y(hx)
        top = y - 16 * ease_out_back(k)
        g.d.line((x, y, x, top), fill=1)
        fr = int(t * 4) % 2
        pts = [(x + 1, top), (x + 9, top + 2 + fr), (x + 6, top + 4), (x + 9, top + 6 - fr), (x + 1, top + 7)]
        g.d.polygon(pts, fill=1)
        g.px(x + 3, top + 3, 0)

    def dig(self, g: Gfx, q: float, S: float, t: float, dt: float):
        """第六站：走到穴前，插旗、放光"""
        if q < 3:
            self.walker(g, S, t, False, "offer")
        elif q < 4.2:
            daoshi(g, DX, ground_y(DX + S), "raise", t)
        else:
            daoshi(g, DX, ground_y(DX + S), "gongshou" if q % 12 < 2 else "idle", t, face="happy" if q < 9 else "normal")
        if q >= 4.0:
            self.flag(g, span(q, 4.0, 4.4), t, S)
        cy = ground_y(S + 84)
        if 4.0 <= q < 4.0 + dt:
            self.sparks.burst(84, cy, 16, 30, up=16, life=0.7, gravity=60)
        if 4.0 <= q < 4.3:
            pix.shake(g, t, 1.2)
        if q > 4.4:                                   # 穴上气纹一圈圈
            for j in range(2):
                r = ((t * 6 + j * 6) % 12)
                g.d.arc((84 - r * 1.6, cy - r * 0.5, 84 + r * 1.6, cy + r * 0.5), 180, 360, fill=1)
        return ("hole", q)

    def mx(self, g: Gfx, needle: float, t: float):
        a = needle - math.pi / 2
        for j in range(-3, 4):
            x, y = 3.5 + math.cos(a) * j, 3.5 + math.sin(a) * j
            g.mx_set(int(round(x)), int(round(y)))
        x, y = 3.5 + math.cos(a) * 3.5, 3.5 + math.sin(a) * 3.5
        tx, ty = -math.sin(a), math.cos(a)
        g.mx_set(int(round(x - math.cos(a) * 1.5 + tx)), int(round(y - math.sin(a) * 1.5 + ty)))
        g.mx_set(int(round(x - math.cos(a) * 1.5 - tx)), int(round(y - math.sin(a) * 1.5 - ty)))

    def scene(self, g: Gfx, t: float, e: float, dt: float):
        c, st, tau, S = self.where(e)
        r = self.station(g, c, st, tau, S, t, dt)
        self.sparks.step(dt)
        self.sparks.draw(g)
        nd = self.needle(tau - WALK, t, 1.0) if r and r[0] != "hole" else math.sin(t * 2) * 0.15
        if r and r[0] != "hole":
            k, q = r
            m = self.mountain(c, st)
            dial = (m * math.pi / 12) * ease_in_out(span(q, 0.5, 3.0)) + (1 - span(q, 0.5, 3.0)) * t * 2
            luopan_face(g, -dial, self.needle(q, t, 1.0), k)
            if q > 3.0 and k > 0.9:
                zuo, xiang = SHAN[m], SHAN[(m + 12) % 24]
                label(g, 6, 4, f"坐{zuo}向{xiang}")
        elif r and r[0] == "hole" and r[1] > 4.4 and (t * 1.5) % 1 < 0.7:
            label(g, 6, 4, "点穴")
        self.mx(g, nd, t)
        return c, st, tau, S

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        self.land(g, 0.0, t)
        if t < 2.0:
            x = lerp(-14, DX, ease_out(span(t, 0, 2.0)))
            h = figure(g, x, ground_y(x), t, legs="walk", arm="offer")
            tiny_luopan(g, *h["hand"])
        else:
            h = daoshi(g, DX, ground_y(DX), "offer", t)
            tiny_luopan(g, h["hand"][0], h["hand"][1] - 1)
        k = span(t, 2.0, 2.6) * (1 - span(t, 4.4, 5.0))
        q = t - 2.0
        luopan_face(g, -(t * 3 - ease_out(span(t, 2, 4)) * t * 3), self.needle(q, t, 0.8), k)
        if 3.4 < t < 4.6:
            label(g, 6, 4, "寻龙")
        self.mx(g, self.needle(q, t, 0.8), t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        self.scene(g, t, e, dt)

    def fog(self, g: Gfx, x: float):
        for j, (dx, dy, w, h) in enumerate(((0, 24, 56, 16), (36, 36, 60, 18), (-6, 44, 50, 16), (24, 8, 50, 16))):
            pix.blit(g, cloud_sprite(w, h, 60 + j), x + dx, dy)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        self.still = True
        c, st, tau, S = self.scene(g, t, e, dt)
        self.still = False
        self.fog(g, lerp(130, 10, ease_out(span(t, 0, 1.3))))
        if t > 0.6:
            label(g, 6, 4, "雾锁")
        g.mx[:] = False
        self.mx(g, 0.0, 0.0)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        self.still = t < 1.2
        c, st, tau, S = self.scene(g, t, e, dt)
        self.still = False
        self.fog(g, lerp(10, -130, ease_in(span(t, 0.2, 1.6))))
        g.mx[:] = False
        self.mx(g, math.sin(t * 20) * 0.3 * (1 - span(t, 0.5, 1.8)), t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, st, tau, S = self.where(e)
        target = math.ceil((S - 1e-6) / HOLE) * HOLE    # 一路疾行到前方的穴
        S = lerp(S, target, ease_in_out(span(t, 0, 1.2)))
        self.land(g, S, t)
        cy = ground_y(S + 84)
        if t > 1.6:
            rays(g, 84, cy - 6, 12, 40, 12, t * 0.3, 2)
            for j in range(3):
                r = ((t - 1.6) * 20 + j * 10) % 36
                ring(g, 84, cy, r * 1.5, r * 0.5)
        self.flag(g, span(t, 1.4, 1.8), t, S)
        if t < 1.2:
            h = figure(g, DX, ground_y(DX + S), t * 2, legs="walk", arm="offer")
            tiny_luopan(g, *h["hand"])
        elif t < 1.4:
            h = daoshi(g, DX, ground_y(DX + S), "offer", t)
            tiny_luopan(g, h["hand"][0], h["hand"][1] - 1)
        elif t < 2.2:
            daoshi(g, DX, ground_y(DX + S), "raise", t)
        else:
            daoshi(g, DX, ground_y(DX + S), "bow" if 3.0 < t < 4.0 else "gongshou", t, face="happy")
        if 1.4 <= t < 1.4 + dt:
            self.sparks.burst(84, cy, 24, 40, up=18, life=0.9, gravity=50)
        if 1.4 <= t < 1.47:
            pix.flash(g)
        if 1.4 < t < 1.7:
            pix.shake(g, t, 1.5)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 2.4:
            y = pop_box(g, 40, 4, "龙真穴的", t, 2.4)
            g.text(40, y, "龙真穴的", align="center")
        if t > 1.4:
            from .r5_util import mx_ring
            mx_ring(g, (t - 1.4) * 4 % 6)
            g.mx_level = 1 + int(5 * (1 - span(t, 1.4, 3)))
        else:
            self.mx(g, 0.0, t)
