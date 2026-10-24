"""罗盘寻龙：风水罗盘格龙、沿龙脉点穴。

依据：罗盘由方形地盘与圆形天盘组成，中央天池（磁针），外圈先天八卦、二十四山
（午丁未坤申庚酉辛戌乾亥壬子癸丑艮寅甲卯乙辰巽巳丙，南在上顺时针），地盘上两道红线（天心十道）定坐向。
形势派“寻龙点穴”：龙脉自祖山（后方玄武）起伏而下，左青龙、右白虎环抱，前有案山与水，
龙止气聚处为穴，所谓“龙真穴的”。

入场：方盘从左滑入，天盘飞转后减速，磁针乱摆后归于子午；右边群山升起。
持续：每轮（10 分钟）先转盘定一个新坐向（右上“坐子向午”），磁针摆动渐稳；
      一道点线沿龙脉从玄武山顶蜿蜒而下（随计时延伸），最后到穴处插旗、波纹（“点穴”）。
      下一轮：旗收、龙脉点线退去，转盘到下一个坐向。
中断：山间起雾，云锁龙脉，磁针静止，“雾锁”。
恢复：雾散。
圆满：穴位放光，“龙真穴的”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.symbols import XIANTIAN, bagua_ring
from .r5_util import cloud_blobs, mist, mx_line

SHAN = "午丁未坤申庚酉辛戌乾亥壬子癸丑艮寅甲卯乙辰巽巳丙"
PX, PY, PR = 32, 32, 29          # 罗盘中心与天盘半径
TURN = 30.0                      # 每轮开头转盘的秒数
ARRIVE = 25.0                    # 每轮最后的“点穴”
XUE = (97, 46)                   # 穴
VEIN = [(97, 16), (90, 21), (100, 26), (91, 31), (102, 36), (94, 41), XUE]  # 龙脉（自玄武山顶而下）
FAR = [(66, 30), (74, 24), (82, 27), (90, 17), (97, 12), (104, 17), (112, 25), (120, 21), (127, 26), (127, 50),
       (66, 50)]
LEFT = [(66, 52), (66, 34), (74, 31), (84, 38), (90, 46), (88, 52)]          # 青龙
RIGHT = [(127, 52), (127, 36), (119, 33), (110, 38), (104, 46), (106, 52)]   # 白虎
AN = [(80, 64), (90, 56), (97, 54), (104, 56), (116, 64)]                   # 案山


def vein_point(p: float):
    """龙脉折线上 p (0..1) 处的点与之前的折点"""
    seg = []
    tot = 0.0
    for a, b in zip(VEIN, VEIN[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        seg.append((a, b, L))
        tot += L
    d = clamp(p) * tot
    pts = [VEIN[0]]
    for a, b, L in seg:
        if d <= L:
            k = d / L if L else 0
            return pts, (lerp(a[0], b[0], k), lerp(a[1], b[1], k))
        d -= L
        pts.append(b)
    return pts[:-1], VEIN[-1]


@register
class Luopan(Ritual):
    id = "r5.luopan"
    name = "寻龙"
    desc = "罗盘定坐向，磁针摆定；一道点线沿龙脉从玄武山蜿蜒而下，到穴处插旗点穴"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.6, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.base = self.rng.randrange(24)

    # ------------------------------------------------------------ 坐向与转盘

    def facing(self, n: int) -> int:
        """第 n 轮（0 起）的“向”的山序号"""
        return (self.base + n * 7) % 24

    def plate_rot(self, e: float) -> float:
        n = int(e // self.CYCLE)
        k = e % self.CYCLE
        cur = -self.facing(n) * math.pi / 12
        if n == 0:
            return cur
        prev = -self.facing(n - 1) * math.pi / 12
        while cur - prev > math.pi:
            cur -= 2 * math.pi
        while prev - cur > math.pi:
            cur += 2 * math.pi
        return lerp(prev, cur, ease_in_out(span(k, 2.0, TURN * 0.6)))

    def wobble(self, e: float, t: float, amp: float = 1.0) -> float:
        k = e % self.CYCLE
        settle = math.exp(-max(k - TURN * 0.6, 0) / 8.0) if k > TURN * 0.6 else 1.0
        a = 0.5 * settle + 0.03
        return amp * a * math.sin(t * 5.3) * (0.6 + 0.4 * noise(t * 2, self.seed))

    # ------------------------------------------------------------ 画面零件

    def luopan(self, g: Gfx, rot: float, needle: float, ox: float = 0.0, spin_text: bool = True):
        d = g.d
        cx, cy = PX + ox, PY
        d.rectangle((cx - 31, 0, cx + 31, 63), outline=1)
        d.rectangle((cx - 29, 2, cx + 29, 61), outline=1)
        # 地盘四角（方中有圆）
        for sx in (-1, 1):
            for sy in (-1, 1):
                for j in range(4):
                    d.line((cx + sx * (27 - j * 2), cy + sy * 28, cx + sx * 28, cy + sy * (27 - j * 2)), fill=1)
        d.ellipse((cx - PR, cy - PR, cx + PR, cy + PR), fill=0, outline=1)
        d.ellipse((cx - 21, cy - 21, cx + 21, cy + 21), outline=1)
        # 二十四山：外缘刻度、每山一点，四正位短杠，“午”位一枚三角
        for j in range(24):
            a = rot + j * math.pi / 12
            sa, ca = math.sin(a), -math.cos(a)
            a0 = a + math.pi / 24
            d.line((cx + math.sin(a0) * 25, cy - math.cos(a0) * 25, cx + math.sin(a0) * 29,
                    cy - math.cos(a0) * 29), fill=1)
            if j == 0:
                d.polygon([(cx + sa * 27.5, cy + ca * 27.5), (cx + sa * 22.5 - ca * 2.5, cy + ca * 22.5 + sa * 2.5),
                           (cx + sa * 22.5 + ca * 2.5, cy + ca * 22.5 - sa * 2.5)], fill=1)
            elif j % 6 == 0:
                d.line((cx + sa * 22.5, cy + ca * 22.5, cx + sa * 26.5, cy + ca * 26.5), fill=1)
                d.line((cx + sa * 22.5 + ca, cy + ca * 22.5 - sa, cx + sa * 26.5 + ca, cy + ca * 26.5 - sa), fill=1)
            else:
                g.px(cx + sa * 23.5, cy + ca * 23.5)
        bagua_ring(g, cx, cy, 10.5, rot, XIANTIAN, w=7, step=2.5)
        # 天池与磁针
        d.ellipse((cx - 7.5, cy - 7.5, cx + 7.5, cy + 7.5), fill=0, outline=1)
        na = rot + needle
        ux, uy = math.sin(na), -math.cos(na)
        d.line((cx - ux * 6, cy - uy * 6, cx + ux * 6, cy + uy * 6), fill=1)
        d.polygon([(cx + ux * 6, cy + uy * 6), (cx + ux * 2 - uy * 1.5, cy + uy * 2 + ux * 1.5),
                   (cx + ux * 2 + uy * 1.5, cy + uy * 2 - ux * 1.5)], fill=1)
        g.px(cx - ux * 6 - uy, cy - uy * 6 + ux)
        g.px(cx - ux * 6 + uy, cy - uy * 6 - ux)
        # 天心十道（红线）：固定
        for k in (0, 1, 2, 3, 60, 61, 62, 63):
            g.px(cx, k)
        for k in (-31, -30, -29, 29, 30, 31):
            g.px(cx + k, cy)

    def land(self, g: Gfx, rise: float = 1.0):
        if rise <= 0:
            return
        dy = (1 - rise) * 50
        far = [(x, y + dy) for x, y in FAR]
        g.d.polygon(far, fill=0)
        g.d.line(far[:-2], fill=1)
        for i in range(3, len(FAR) - 3):  # 山脊皴笔
            x, y = far[i]
            g.d.line((x, y + 3, x - 3, y + 8), fill=1)
        for poly in (LEFT, RIGHT):
            pp = [(x, y + dy * 1.2) for x, y in poly]
            g.d.polygon(pp, fill=0)
            g.shade_poly(pp, 0.2)
        an = [(x, y + dy * 0.6) for x, y in AN]
        g.d.polygon(an, fill=0, outline=1)
        # 水（明堂前的一湾水）
        for x in range(66, 128, 2):
            y = 59 + dy + math.sin(x * 0.3) * 1.2
            if not (86 < x < 108):
                g.px(x, y)

    def vein(self, g: Gfx, p: float, t: float, recede: float = 0.0):
        pts, head = vein_point(p)
        full = pts + [head]
        # 已走过的龙脉：黑边白线（退去时随机掉点）
        if len(full) > 1:
            if recede:
                tot = 0
                for a, b in zip(full, full[1:]):
                    n = int(math.hypot(b[0] - a[0], b[1] - a[1]))
                    for i in range(n):
                        tot += 1
                        if rand(tot, 3) >= recede:
                            k = i / max(n, 1)
                            g.px(lerp(a[0], b[0], k), lerp(a[1], b[1], k))
            else:
                g.d.line(full, fill=0, width=3)
                g.d.line(full, fill=1)
        if 0 < p < 1 and not recede:
            x, y = head
            g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=0)
            if blink(t, 0.5, 0.6):
                g.d.rectangle((x - 1, y - 1, x + 1, y + 1), outline=1)
            g.px(x, y)

    def flag(self, g: Gfx, h: float, t: float):
        x, y = XUE
        if h <= 0:
            return
        top = y - 10 * h
        g.d.line((x, y, x, top), fill=1)
        wav = math.sin(t * 6) * 1
        g.d.polygon([(x + 1, top), (x + 7, top + 2 + wav), (x + 1, top + 4)], fill=1)

    def title(self, g: Gfx, n: int, a: float = 1.0, right: str | None = None):
        j = self.facing(n)
        s = right if right is not None else f"坐{SHAN[(j + 12) % 24]}向{SHAN[j]}"
        s = s[:int(round(a * len(s)))]
        g.d.rectangle((66, 0, 127, 12), fill=0)
        g.text(97, 1, s, align="center")

    def mx(self, g: Gfx, ang: float):
        ux, uy = math.sin(ang), -math.cos(ang)
        mx_line(g, 3.5 - ux * 3.5, 3.5 - uy * 3.5, 3.5 + ux * 3.5, 3.5 + uy * 3.5)
        g.mx_set(int(round(3.5 + ux * 2.5 - uy)), int(round(3.5 + uy * 2.5 + ux)))
        g.mx_set(int(round(3.5 + ux * 2.5 + uy)), int(round(3.5 + uy * 2.5 - ux)))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        slide = ease_out(span(t, 0, 0.9))
        spin = (1 - ease_out(span(t, 0.3, 2.6))) * 9.0
        rot = self.plate_rot(0) + spin
        needle = math.sin(t * 7) * 1.2 * (1 - span(t, 1.0, 3.2))
        self.land(g, ease_out_back(span(t, 0.8, 2.2)))
        self.luopan(g, rot, needle, ox=lerp(-70, 0, slide))
        self.title(g, 0, span(t, 2.6, 3.6))
        self.mx(g, rot + needle)

    def hold(self, g: Gfx, t: float, e: float):
        n = int(e // self.CYCLE)
        k = e % self.CYCLE
        rot = self.plate_rot(e)
        needle = self.wobble(e, t)
        self.land(g)
        p = span(k, TURN, self.CYCLE - ARRIVE)
        if n > 0 and k < TURN:
            # 续：上一轮的旗收起、点线退去
            self.vein(g, 1.0, t, recede=span(k, 0, 6))
            self.flag(g, 1 - span(k, 0, 1.5), t)
        else:
            self.vein(g, p, t)
        if k > self.CYCLE - ARRIVE:
            a = k - (self.CYCLE - ARRIVE)
            self.flag(g, ease_out_back(span(a, 0, 0.8)), t)
            if a < 3:
                ring(g, XUE[0], XUE[1], a * 8, 2)
                g.mx_level = 3
            elif (a % 4) < 1:
                ring(g, XUE[0], XUE[1], (a % 4) * 8, 3)
        self.luopan(g, rot, needle)
        arrived = k > self.CYCLE - ARRIVE
        self.title(g, n, right="点穴" if arrived and blink(k, 4, 0.3) else None)
        self.mx(g, rot + needle)

    def interrupt(self, g: Gfx, t: float, e: float):
        n = int(e // self.CYCLE)
        k = e % self.CYCLE
        rot = self.plate_rot(e)
        self.land(g)
        self.vein(g, span(k, TURN, self.CYCLE - ARRIVE), t)
        fog = ease_out(span(t, 0, 1.3))
        mist(g, cloud_blobs(lerp(160, 97, fog), 30, 70, 26, self.seed) +
             cloud_blobs(lerp(170, 100, fog), 48, 64, 18, self.seed + 1), 0.2 + 0.1 * fog)
        self.luopan(g, rot, self.wobble(e, t, 1 - fog))
        self.title(g, n, right="雾锁" if t > 0.7 else None)
        self.mx(g, rot)

    def resume(self, g: Gfx, t: float, e: float):
        n = int(e // self.CYCLE)
        k = e % self.CYCLE
        rot = self.plate_rot(e)
        self.land(g)
        self.vein(g, span(k, TURN, self.CYCLE - ARRIVE), t)
        fog = 1 - ease_in_out(span(t, 0.1, 1.5))
        if fog > 0:
            mist(g, cloud_blobs(lerp(-40, 97, fog), 30, 70, 26, self.seed) +
                 cloud_blobs(lerp(-50, 100, fog), 48, 64, 18, self.seed + 1), 0.3 * fog + 0.05)
        self.luopan(g, rot, self.wobble(e, t, span(t, 0.8, 1.6)) + math.sin(t * 9) * 0.3 * span(t, 0.2, 0.8)
                    * (1 - span(t, 0.8, 1.6)))
        self.title(g, n, right="雾锁" if t < 0.6 else None)
        self.mx(g, rot)

    def complete(self, g: Gfx, t: float, e: float):
        n = int(e // self.CYCLE)
        rot = self.plate_rot(e)
        self.land(g)
        self.vein(g, 1.0, t)
        self.flag(g, ease_out_back(span(t, 0, 0.8)), t)
        x, y = XUE
        if t > 0.8:
            for i in range(10):  # 穴位放光
                a = i / 10 * 2 * math.pi + t * 0.8
                r0 = 4 + ((t - 0.8) * 10 + i * 3) % 14
                g.d.line((x + math.cos(a) * r0, y + math.sin(a) * r0 * 0.7, x + math.cos(a) * (r0 + 3),
                          y + math.sin(a) * (r0 + 3) * 0.7), fill=1)
            ring(g, x, y, ((t - 0.8) * 20) % 30, 2)
        self.luopan(g, rot, self.wobble(e, t) * (1 - span(t, 0, 1)))
        if t < 1.6:
            self.title(g, n, a=1 - span(t, 0.8, 1.6))
        else:
            g.d.rectangle((66, 0, 127, 12), fill=0)
            typewriter(g, 97, 1, "龙真穴的", t - 1.6, cps=5, align="center")
        if t > 0.8:
            r = (t - 0.8) * 4 % 6
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.8:
                        g.mx[yy, xx] = True
            g.mx_set(3, 3)
            g.mx_set(4, 4)
            g.mx_set(3, 4)
            g.mx_set(4, 3)
            g.mx_level = 1 + int(4 * (1 - span(t, 0.8, 2.5)))
        else:
            self.mx(g, rot)
