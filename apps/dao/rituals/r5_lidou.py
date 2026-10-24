"""礼斗：北斗七星灯。

依据：礼斗科（《清微礼斗科》等）向斗姆与南北斗星君祈福，诵《太上玄灵北斗本命延生真经》，
坛上按北斗之形布七盏灯。七星：天枢（贪狼）、天璇（巨门）、天玑（禄存）、天权（文曲）、
玉衡（廉贞）、开阳（武曲）、摇光（破军），开阳旁有辅星。

入场：星空淡入，一支引火的长烛从右上伸来，点亮天枢灯。
持续：一道星线从已亮的灯缓缓连向下一盏（一轮 10 分钟，六段），到达即点亮；左上显示刚点亮那盏的星君名。
      七灯俱亮后，七点灯焰升空化星，回到只亮天枢（“第几遍”）。
中断：从摇光往回，灯焰依次缩成星火，“暂熄”。
恢复：星火依次重新燃起。
圆满：七灯齐明，光点升空，在天上排成北斗，“消灾解厄”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.cn import cn_num
from ..engine.fx import flame, ring, stars, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register

# 灯盏位置（盏口中心），按天枢→摇光
LAMPS = [(111, 13), (114, 36), (88, 42), (78, 29), (57, 32), (41, 35), (24, 50)]
STAR = ["天枢", "天璇", "天玑", "天权", "玉衡", "开阳", "摇光"]
JUN = ["贪狼", "巨门", "禄存", "文曲", "廉贞", "武曲", "破军"]
MX_POS = [(7, 0), (7, 3), (5, 4), (4, 2), (2, 2), (1, 3), (0, 6)]
SEG = 6           # 六段星线
RENEW = 5.0


def lamp(g: Gfx, x: float, y: float, lit: float, t: float, seed: int, big: bool = False):
    """油灯（灯盏 + 灯柱 + 底座）：盏口中心 (x, y)。lit 0..1：0 = 冷灯，小于 0.15 = 星火"""
    d = g.d
    d.polygon([(x - 6, y), (x + 6, y), (x + 4, y + 3), (x - 4, y + 3)], fill=1)
    d.line((x - 4, y + 1, x + 4, y + 1), fill=0)
    d.rectangle((x - 1, y + 4, x, y + 7), fill=1)
    d.rectangle((x - 3, y + 8, x + 2, y + 9), fill=1)
    d.line((x, y - 1, x, y - 1), fill=1)  # 灯芯
    if lit >= 0.15:
        h = (11 if big else 9) * lit
        flame(g, x, y - 1, 5 if lit > 0.5 else 3, max(h, 2), t, seed)
    elif lit > 0:
        if blink(t + seed * 0.3, 0.5, 0.6):
            g.d.rectangle((x - 1, y - 2, x, y - 2), fill=1)


def dotted(g: Gfx, a, b, p: float, gap: int = 3):
    """从 a 到 b 的点线，画出前 p 比例"""
    (x0, y0), (x1, y1) = a, b
    n = int(math.hypot(x1 - x0, y1 - y0) / gap)
    for i in range(int(n * clamp(p)) + 1):
        k = i / max(n, 1)
        g.px(lerp(x0, x1, k), lerp(y0, y1, k))


def head(a, b, p):
    (x0, y0), (x1, y1) = a, b
    return lerp(x0, x1, p), lerp(y0, y1, p)


@register
class Lidou(Ritual):
    id = "r5.lidou"
    name = "礼斗"
    desc = "北斗七星灯：星线逐盏连向下一灯并点亮，七灯俱明后灯焰升空化星"
    T = {"enter": 3.8, "interrupt": 1.6, "resume": 1.8, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.sky = self.rng.randrange(1000)

    # ------------------------------------------------------------ 零件

    def state(self, e: float):
        """→ (已亮灯数 1..7, 当前段进度 0..1)"""
        k = (e % self.CYCLE) / self.CYCLE * SEG
        i = int(k)
        return min(7, i + 1), k - i

    def scene(self, g: Gfx, t: float, nlit: int, prog: float, lit_amt=None, links: int | None = None,
              big: int | None = None):
        stars(g, t, self.sky, n=18, box=(0, 0, 128, 64), twinkle=0.35)
        links = nlit - 1 if links is None else links
        dotted(g, (LAMPS[3][0], LAMPS[3][1] - 3), (LAMPS[0][0], LAMPS[0][1] - 3), 1.0, gap=7)  # 斗魁一边
        for i in range(max(links, 0), 6):  # 未连的星路：疏点
            dotted(g, (LAMPS[i][0], LAMPS[i][1] - 3), (LAMPS[i + 1][0], LAMPS[i + 1][1] - 3), 1.0, gap=7)
        for i in range(links):
            dotted(g, LAMPS[i], LAMPS[i + 1], 1.0)
        if nlit < 7 and prog > 0 and links == nlit - 1:
            a, b = LAMPS[nlit - 1], LAMPS[nlit]
            a = (a[0], a[1] - 3)
            b = (b[0], b[1] - 3)
            dotted(g, a, b, prog)
            hx, hy = head(a, b, prog)
            r = 1 + (1 if blink(t, 0.4) else 0)
            g.d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=1)
        for i, (x, y) in enumerate(LAMPS):
            amt = lit_amt[i] if lit_amt is not None else (1.0 if i < nlit else 0.0)
            lamp(g, x, y, amt, t, self.seed + i, big=(i == big))
        # 辅星（开阳旁）
        if blink(t + 0.2, 1.7, 0.8):
            g.px(LAMPS[5][0] + 4, LAMPS[5][1] - 11)

    def label(self, g: Gfx, idx: int, a: float = 1.0):
        s = JUN[idx] + "星君"
        k = int(round(a * len(s)))
        g.text(2, 2, s[:k])
        if a >= 1:
            g.text(4, 15, STAR[idx], size=8)

    def counter(self, g: Gfx, e: float, s: str | None = None):
        s = s if s is not None else f"第{cn_num(int(e // self.CYCLE) + 1)}遍"
        g.text(60, 51, s, align="center")

    def mx(self, g: Gfx, nlit: int, t: float, lit=None, prog: float = 0.0):
        for i, (x, y) in enumerate(MX_POS):
            on = lit[i] if lit is not None else i < nlit
            if on:
                g.mx_set(x, y)
            elif i == nlit and lit is None:
                g.mx_set(x, y, blink(t, 1.0, 0.2))
        if lit is None and 1 <= nlit < 7 and prog > 0:  # 星线的头
            (x0, y0), (x1, y1) = MX_POS[nlit - 1], MX_POS[nlit]
            g.mx_set(round(lerp(x0, x1, prog)), round(lerp(y0, y1, prog)))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        a = span(t, 0, 0.8)
        stars(g, t, self.sky, n=int(18 * a), twinkle=0.35)
        lit = ease_out(span(t, 2.2, 2.6))
        guide = span(t, 1.2, 2.2)
        if guide > 0:  # 星路疏点
            dotted(g, (LAMPS[3][0], LAMPS[3][1] - 3), (LAMPS[0][0], LAMPS[0][1] - 3), guide, gap=7)
            for i in range(6):
                dotted(g, (LAMPS[i][0], LAMPS[i][1] - 3), (LAMPS[i + 1][0], LAMPS[i + 1][1] - 3), guide, gap=7)
        for i, (x, y) in enumerate(LAMPS):
            if span(t, 0.2 + i * 0.12, 0.6 + i * 0.12) > 0:
                yy = y + (1 - ease_out_back(span(t, 0.2 + i * 0.12, 0.6 + i * 0.12))) * 6
                lamp(g, x, yy, lit if i == 0 else 0.0, t, self.seed + i)
        # 长烛从左下伸来点天枢灯
        if t < 3.4:
            p = ease_out(span(t, 0.9, 2.1))
            back = ease_in(span(t, 2.6, 3.4))
            tx, ty = LAMPS[0][0] + 3, LAMPS[0][1] - 5
            hx, hy = lerp(150, tx, p) + back * 50, lerp(-20, ty, p) - back * 30
            g.d.line((hx + 1, hy + 1, hx + 40, hy - 18), fill=1, width=2)
            flame(g, hx, hy, 3, 6, t, 3)
        if abs(t - 2.3) < 0.25:
            ring(g, LAMPS[0][0], LAMPS[0][1] - 5, (t - 2.05) * 30, 2)
            g.mx_level = 5
        self.label(g, 0, span(t, 2.6, 3.6))
        if t > 3.0:
            self.counter(g, 0)
        self.mx(g, 1 if t > 2.3 else 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e)
            return
        nlit, prog = self.state(e)
        seg_t = prog * self.CYCLE / SEG
        flash = nlit > 1 and seg_t < 1.0
        self.scene(g, t, nlit, prog if nlit < 7 else 0, big=nlit - 1 if flash else None)
        if flash:  # 刚点亮
            x, y = LAMPS[nlit - 1]
            ring(g, x, y - 5, 4 + seg_t * 14, 2)
            g.mx_level = 4
        if nlit == 7:
            # 七灯俱明：星线上流光
            j = int(t * 6) % 6
            q = (t * 6) % 1
            g.px(*head(LAMPS[j], LAMPS[j + 1], q))
        self.label(g, nlit - 1)
        self.counter(g, e)
        self.mx(g, nlit, t, prog=prog)

    def _renew(self, g: Gfx, t: float, k: float, e: float):
        """七焰升空化星，回到只亮天枢"""
        stars(g, t, self.sky, n=18, twinkle=0.35)
        rise = ease_in(span(k, 0.3, 2.6))
        for i, (x, y) in enumerate(LAMPS):
            relit = 1.0 if i == 0 and k > 3.6 else 0.0
            lamp(g, x, y, (1.0 - span(k, 0, 0.4)) if k < 0.4 else relit, t, self.seed + i)
            if 0.3 < k < 3.2:
                sy = y - 5 - rise * (y + 10)
                g.d.line((x, sy, x, sy + 4 * (1 - rise) + 1), fill=1)
                g.px(x - 1, sy + 1)
                g.px(x + 1, sy + 1)
        if k > 2.6 and k < 3.6:
            for i in range(7):
                if blink(t + i * 0.1, 0.3):
                    g.px(LAMPS[i][0], 3)
        if 3.4 < k < 4.0:
            ring(g, LAMPS[0][0], LAMPS[0][1] - 5, (k - 3.4) * 25, 2)
            g.mx_level = 4
        if k < 1.0:
            for i in range(6):
                dotted(g, LAMPS[i], LAMPS[i + 1], 1 - k)
        self.label(g, 0 if k > 3.6 else 6)
        self.counter(g, e)
        self.mx(g, 0, t, lit=[(k > 3.6) if i == 0 else (k < 0.6) for i in range(7)])
        if 2.2 < k < 3.6:  # 天上的北斗一闪
            self.mx(g, 7, t, lit=[blink(k + i * 0.05, 0.4, 0.7) for i in range(7)])
        if 0.3 < k < 3.4:  # 点阵：光点上升
            for i, (x, y) in enumerate(MX_POS):
                g.mx_set(x, int(y - rise * 8))

    def interrupt(self, g: Gfx, t: float, e: float):
        nlit, prog = self.state(e)
        amt = []
        for i in range(7):
            if i >= nlit:
                amt.append(0.0)
            else:
                order = nlit - 1 - i  # 从最后点亮的往回掐
                amt.append(lerp(1.0, 0.1, ease_in_out(span(t, 0.15 + order * 0.15, 0.45 + order * 0.15))))
        self.scene(g, t, nlit, prog * (1 - span(t, 0, 0.6)), amt)
        self.label(g, nlit - 1)
        self.counter(g, e, "暂熄" if t > 0.6 else None)
        self.mx(g, nlit, t, lit=[a > 0.5 or (a > 0 and blink(t, 0.6)) for a in amt])

    def resume(self, g: Gfx, t: float, e: float):
        nlit, prog = self.state(e)
        amt = []
        for i in range(7):
            if i >= nlit:
                amt.append(0.0)
            else:
                amt.append(lerp(0.1, 1.0, ease_out_back(span(t, 0.2 + i * 0.18, 0.5 + i * 0.18))))
        self.scene(g, t, nlit, prog * span(t, 1.2, 1.8), amt)
        for i in range(nlit):
            s = 0.2 + i * 0.18
            if s < t < s + 0.35:
                ring(g, LAMPS[i][0], LAMPS[i][1] - 5, (t - s) * 30, 2)
        self.label(g, nlit - 1)
        self.counter(g, e, "暂熄" if t < 0.4 else None)
        self.mx(g, nlit, t, lit=[a > 0.5 for a in amt])

    def complete(self, g: Gfx, t: float, e: float):
        nlit, _ = self.state(e)
        # 0-1.2s：星线连遍七灯，全部点亮
        chain = span(t, 0, 1.2) * 6
        for i in range(6):
            dotted(g, LAMPS[i], LAMPS[i + 1], clamp(chain - i) if t < 2.0 else 1 - span(t, 2.0, 2.4))
        amt = [1.0 if (i < nlit or chain >= i) else 0.0 for i in range(7)]
        rise = ease_in_out(span(t, 1.6, 3.2))
        if t < 2.6:
            for i, (x, y) in enumerate(LAMPS):
                lamp(g, x, y, 0.0 if t > 1.6 else amt[i], t, self.seed + i)
            if t > 1.6:  # 灯盏隐去
                g.fade(1 - span(t, 1.6, 2.6))
        stars(g, t, self.sky, n=18, twinkle=0.35)
        if t < 1.6:
            for i, (x, y) in enumerate(LAMPS):
                if amt[i]:
                    flame(g, x, y - 1, 5, 9 + 4 * span(t, 1.0, 1.6), t, self.seed + i)
        else:  # 七点灯焰升空，在天上排成北斗
            pts = []
            for i, (x, y) in enumerate(LAMPS):
                tx, ty = 20 + (x - 24) * 0.75, 5 + (y - 13) * 0.6
                sx, sy = lerp(x, tx, rise), lerp(y - 5, ty, ease_out_back(rise))
                pts.append((sx, sy))
                g.d.rectangle((sx - 1, sy, sx + 1, sy), fill=1)
                g.d.rectangle((sx, sy - 1, sx, sy + 1), fill=1)
                if t < 3.2:
                    g.d.line((sx, sy + 2, sx, sy + 2 + 6 * (1 - rise)), fill=1)
                elif blink(t + i * 0.13, 0.5, 0.4):
                    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                        g.px(sx + dx, sy + dy)
            if t > 3.2:
                for i in range(6):
                    dotted(g, pts[i], pts[i + 1], span(t, 3.2 + i * 0.08, 3.6 + i * 0.08))
                dotted(g, pts[3], pts[0], span(t, 3.7, 4.0))
        if t < 1.6:
            self.label(g, 6, 1 - span(t, 0.8, 1.6))
        if t > 3.4:
            typewriter(g, 64, 46, "消灾解厄", t - 3.4, cps=6, align="center")
        g.mx_level = 1 + int(5 * span(t, 1.2, 1.6) * (1 - span(t, 2.0, 4.0)))
        self.mx(g, 7, t, lit=[True] * 7 if t > 1.2 or blink(t, 0.2) else amt)
