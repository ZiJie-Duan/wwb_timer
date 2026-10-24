"""五行生克：五行轮转。

依据：五行相生（木生火、火生土、土生金、金生水、水生木）沿外圈顺时针；相克（木克土、土克水、水克火、
火克金、金克木）为内部五角星。周敦颐《太极图说》“阳变阴合，而生水火木金土，五气顺布，四时行焉”。
图式按传统：火居上（南），顺时针土、金、水、木。

入场：五行依次（木火土金水）弹出，外圈相生弧线画一圈，内部相克五角星画出。
持续：一轮 10 分钟分五段，每段一行当令（反白、放出本行特效：木抽叶、火跳焰、土落尘、金闪光、水滴落），
      一道光沿外弧从当令一行流向它所生的一行（随计时推进），到达即换下一行当令；右边“木生火”。
      约每 47 秒一次相克：一道光沿五角星的一条边打过去，被克的一行抖动，左边“金克木”。
      一轮满：五行沿圈转一周，五角星全亮，“五气顺布”。
中断：光停住，五行暗下，“暂歇”。
恢复：五行亮回，光继续流。
圆满：光绕圈两周，五行一齐反白，收向中心合成一点放光，“五气顺布”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import flame, ring, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r5_util import arrow_head

CX, CY, R = 64, 33, 24
NR = 8                      # 节点半径
POS = "火土金水木"           # 从正上方顺时针
SEQ = "木火土金水"           # 相生次序（一轮从木起）
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
KE_PERIOD = 47.0
RENEW = 5.0
MX_ICON = {
    "木": Sprite("""
        ...##...
        ..####..
        .######.
        ...##...
        ..####..
        .######.
        ########
        ...##...
    """),
    "火": Sprite("""
        ...#....
        ...##...
        ..###.#.
        ..#####.
        .######.
        .###.##.
        .##..##.
        ..####..
    """),
    "土": Sprite("""
        ........
        ...##...
        ..####..
        .######.
        ########
        ........
        ########
        ........
    """),
    "金": Sprite("""
        ........
        ..####..
        #.####.#
        ########
        .######.
        ..####..
        ........
        ........
    """),
    "水": Sprite("""
        ........
        .##..##.
        #..##..#
        ........
        .##..##.
        #..##..#
        ........
        ........
    """),
}


def node_xy(el: str, rot: float = 0.0, r: float = R):
    a = POS.index(el) * 2 * math.pi / 5 + rot
    return CX + math.sin(a) * r, CY - math.cos(a) * r


@register
class Wuxing(Ritual):
    id = "r5.wuxing"
    name = "五行生克"
    desc = "五行轮转：当令一行反白放特效，光沿外弧流向所生一行；不时一道相克之光打过五角星"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.5, "complete": 5.0}
    CYCLE = 600.0

    def setup(self):
        self.ke_seed = self.rng.randrange(1000)

    def seg(self, e: float):
        k = e % self.CYCLE
        L = self.CYCLE / 5
        i = min(int(k // L), 4)
        return i, (k - i * L) / L, k - i * L

    # ------------------------------------------------------------ 零件

    def node(self, g: Gfx, el: str, x: float, y: float, active: bool = False, s: float = 1.0, dim: bool = False):
        r = NR * s
        if r < 1:
            return
        if active:
            g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
            if s > 0.6:
                g.text(x + 0.5, y - 5, el, align="center", fill=0)
        else:
            g.d.ellipse((x - r, y - r, x + r, y + r), fill=0, outline=1)
            if s > 0.6:
                g.text(x + 0.5, y - 5, el, align="center")
            if dim:
                g.d.ellipse((x - r + 1, y - r + 1, x + r - 1, y + r - 1), outline=0)

    def arc_pts(self, a_el: str, b_el: str, p: float = 1.0, rot: float = 0.0, n: int = 24):
        a0 = POS.index(a_el) * 2 * math.pi / 5 + rot
        da = 2 * math.pi / 5
        # 去掉两端被节点盖住的部分
        cut = (NR + 2) / R
        s0, s1 = a0 + cut, a0 + da - cut
        out = []
        for i in range(n + 1):
            k = i / n
            if k > p:
                break
            a = lerp(s0, s1, k)
            out.append((CX + math.sin(a) * R, CY - math.cos(a) * R, a))
        return out

    def wheel(self, g: Gfx, rot: float = 0.0, flow: tuple | None = None, star: float = 0.0, t: float = 0.0):
        """外圈相生弧（点线），flow=(起行, 进度) 的那段画实线带箭头；内部相克五角星"""
        for el in POS:
            for x, y, a in self.arc_pts(el, SHENG[el], 1.0, rot, 12):
                g.px(x, y)
        if flow:
            el, p = flow
            pts = self.arc_pts(el, SHENG[el], p, rot, 24)
            if len(pts) > 1:
                g.d.line([(x, y) for x, y, a in pts], fill=1, width=2)
                x, y, a = pts[-1]
                arrow_head(g, x + math.cos(a) * 1, y + math.sin(a) * 1, a, 4)
        # 相克五角星：疏点；star>0 时全亮
        for el in POS:
            (x0, y0), (x1, y1) = node_xy(el, rot, R - NR - 1), node_xy(KE[el], rot, R - NR - 1)
            n = int(math.hypot(x1 - x0, y1 - y0))
            stepn = 1 if star > 0 and blink(t, 0.2, 0.7) else 4
            for i in range(0, n, stepn):
                g.px(lerp(x0, x1, i / n), lerp(y0, y1, i / n))

    def effect(self, g: Gfx, el: str, x: float, y: float, t: float):
        """当令一行的特效"""
        if el == "火":
            flame(g, x, y - NR - 1, 7, 9, t, 5)
        elif el == "水":
            for j in range(3):
                q = (t * 1.2 + j / 3) % 1
                xx = x - 4 + j * 4
                yy = y + NR + 1 + ease_in(q) * 10
                g.d.line((xx, yy, xx, yy + 1), fill=1)
        elif el == "木":
            for j in range(5):
                q = (t * 0.6 + j / 5) % 1
                a = j * 1.3 + q * 1.5
                rr = NR + 2 + q * 7
                if q < 0.85:
                    px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
                    g.d.line((px, py, px + 1, py - 1), fill=1)
        elif el == "金":
            for j in range(4):
                if blink(t * 1.3 + j * 0.27, 0.6, 0.3):
                    a = rand(j + int(t * 1.3 + j * 0.27) * 7, 4) * 2 * math.pi
                    rr = NR + 4
                    px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
                    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                        g.px(px + dx, py + dy)
        elif el == "土":
            for j in range(6):
                q = (t * 0.8 + j / 6) % 1
                xx = x - 6 + rand(j, 11) * 12
                g.px(xx, y + NR + 1 + q * 8)

    def ke_event(self, e: float):
        """→ (攻者, 被克者, 进度 0..1) 或 None；按 e 定时"""
        k = e % KE_PERIOD
        if k > 2.5 or e < KE_PERIOD:
            return None
        n = int(e // KE_PERIOD)
        a = POS[int(rand(n, self.ke_seed) * 5) % 5]
        return a, KE[a], k / 2.5

    def sides(self, g: Gfx, left: str, right: str, a: float = 1.0):
        g.vtext(2, 4, left[:int(round(a * len(left)))])
        g.vtext(114, 4, right[:int(round(a * len(right)))])

    # ------------------------------------------------------------ 阶段

    def scene(self, g: Gfx, t: float, e: float, flow_p: float | None = None, dim: float = 1.0):
        i, p, sec = self.seg(e)
        cur = SEQ[i]
        ke = self.ke_event(e)
        self.wheel(g, 0.0, (cur, p if flow_p is None else flow_p))
        if ke:
            a, b, q = ke
            (x0, y0), (x1, y1) = node_xy(a, 0, R - NR - 1), node_xy(b, 0, R - NR - 1)
            hq = ease_in_out(clamp(q * 1.6))
            g.d.line((x0, y0, lerp(x0, x1, hq), lerp(y0, y1, hq)), fill=1, width=2)
            if q > 0.6:
                vx, vy = node_xy(b)
                ring(g, vx, vy, NR + 2 + (q - 0.6) * 20, 2)
        for el in POS:
            x, y = node_xy(el)
            if ke and el == ke[1] and ke[2] > 0.6:
                x += math.sin(t * 50) * 1.5
            pop = ease_out_back(span(sec, 0, 1.0)) if el == cur and sec < 1.0 and e > 1 else 1.0
            self.node(g, el, x, y, active=el == cur, s=pop)
        x, y = node_xy(cur)
        self.effect(g, cur, x, y, t)
        if ke:
            left = f"{ke[0]}克{ke[1]}"
        else:
            left = "五行"
        self.sides(g, left, f"{cur}生{SHENG[cur]}")
        g.mx_blit(MX_ICON[cur])
        if ke and ke[2] > 0.6:
            g.mx_level = 3
        if dim < 1:
            g.fade(dim, (16, 0, 112, 64))

    def enter(self, g: Gfx, t: float):
        for j, el in enumerate(SEQ):
            q = span(t, 0.2 + j * 0.25, 0.6 + j * 0.25)
            if q > 0:
                x, y = node_xy(el)
                self.node(g, el, x, y, active=(el == "木" and t > 3.2), s=ease_out_back(q))
        draw = span(t, 1.6, 2.8)
        for el in (POS if draw > 0 else ""):
            pts = self.arc_pts(el, SHENG[el], draw, 0, 12)
            for x, y, a in pts:
                g.px(x, y)
        star = span(t, 2.4, 3.4)
        for el in POS:
            (x0, y0), (x1, y1) = node_xy(el, 0, R - NR - 1), node_xy(KE[el], 0, R - NR - 1)
            n = int(math.hypot(x1 - x0, y1 - y0))
            for i in range(0, int(n * star), 4):
                g.px(lerp(x0, x1, i / n), lerp(y0, y1, i / n))
        if t > 3.2:
            x, y = node_xy("木")
            ring(g, x, y, NR + (t - 3.2) * 20, 2)
            g.mx_level = 4 if t < 3.4 else 1
        self.sides(g, "五行", "木生火", span(t, 2.8, 3.8))
        idx = min(4, int(span(t, 0.2, 1.45) * 5))
        g.mx_blit(MX_ICON[SEQ[idx]])

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k)
            return
        self.scene(g, t, e)

    def _renew(self, g: Gfx, t: float, k: float):
        rot = ease_in_out(span(k, 0.3, 3.5)) * 2 * math.pi
        self.wheel(g, rot, None, star=1.0 if 0.3 < k < 3.5 else 0.0, t=t)
        for el in POS:
            x, y = node_xy(el, rot)
            self.node(g, el, x, y, active=(el == "木" and k > 3.5))
        if k > 3.5:
            x, y = node_xy("木")
            ring(g, x, y, NR + (k - 3.5) * 16, 2)
        self.sides(g, "五气" if k < 3.5 else "五行", "顺布" if k < 3.5 else "木生火")
        if k < 3.5:
            g.mx_blit(MX_ICON[POS[int(k * 4) % 5]])
            g.mx_level = 2
        else:
            g.mx_blit(MX_ICON["木"])

    def interrupt(self, g: Gfx, t: float, e: float):
        i, p, sec = self.seg(e)
        self.scene(g, t * (1 - span(t, 0, 1.0)), e, dim=1 - 0.6 * span(t, 0.2, 1.2))
        g.d.rectangle((112, 0, 127, 63), fill=0)
        g.vtext(114, 4, "暂歇" if t > 0.6 else f"{SEQ[i]}生{SHENG[SEQ[i]]}")

    def resume(self, g: Gfx, t: float, e: float):
        i, p, sec = self.seg(e)
        self.scene(g, t, e, dim=0.4 + 0.6 * span(t, 0.2, 1.2))
        if t < 0.5:
            g.d.rectangle((112, 0, 127, 63), fill=0)
            g.vtext(114, 4, "暂歇")

    def complete(self, g: Gfx, t: float, e: float):
        i, p, sec = self.seg(e)
        merge = ease_in(span(t, 2.4, 3.4))
        if t < 2.4:
            # 光绕圈两周
            loop = span(t, 0, 2.2) * 2 * 5 + i
            j = int(loop) % 5
            el = POS[(POS.index(SEQ[i]) + int(loop) - i) % 5]
            self.wheel(g, 0.0, (el, loop % 1), t=t)
            for x_el in POS:
                x, y = node_xy(x_el)
                lit = t > 1.6 or x_el == el
                self.node(g, x_el, x, y, active=lit)
            self.sides(g, "五行", f"{SEQ[i]}生{SHENG[SEQ[i]]}", 1 - span(t, 1.6, 2.4))
            g.mx_blit(MX_ICON[el])
        else:
            for x_el in POS:
                x, y = node_xy(x_el, merge * 1.5, R * (1 - merge))
                self.node(g, x_el, x, y, active=True, s=1 - merge * 0.6)
            if t > 3.4:
                r = 4 + (t - 3.4) * 10
                g.d.ellipse((CX - 4, CY - 4, CX + 4, CY + 4), fill=1)
                for k in range(12):
                    a = k / 12 * 2 * math.pi + t
                    g.d.line((CX + math.cos(a) * (r * 0.5 + 5), CY + math.sin(a) * (r * 0.5 + 5),
                              CX + math.cos(a) * (r + 6), CY + math.sin(a) * (r + 6)), fill=1)
            g.vtext(2, 4, "五气"[:int(span(t, 2.4, 3.2) * 2 + 0.99)])
            g.vtext(114, 4, "顺布"[:int(span(t, 3.0, 3.8) * 2 + 0.99)])
            rr = (t - 2.4) * 3
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - rr % 6) < 0.8:
                        g.mx[yy, xx] = True
            g.mx_level = 1 + int(4 * (1 - span(t, 3.4, 4.6)))
