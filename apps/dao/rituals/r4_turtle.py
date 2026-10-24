"""龟息：池边石上，小道士闭目调息，鼻前悬着一根鸿毛；池中石上一只老龟跟着一伸一缩。

依据：《抱朴子·释滞》“初学行炁，鼻中引炁而闭之，阴以心数至一百二十，乃以口微吐之……以鸿毛著鼻口之上，
吐炁而鸿毛不动为候也”“得胎息者，能不以鼻口嘘吸，如在胞胎之中”；《抱朴子·对俗》“仙经象龟之息”，
老龟“伸颈吞气”，千岁之龟“浮于莲叶之上”。
入场：池水起涟漪，老龟从水里爬上石头；一根鸿毛从上方飘落到小道士鼻前。
持续：一息 40 秒：引气 4 秒（龟伸颈吞气，清气点点入鼻）→ 闭气 30 秒，右上默数 1…120（龟缩颈，鸿毛静止）
      → 微吐 6 秒（鸿毛轻颤）。一轮 10 分钟里吐气越来越细，鸿毛越来越静；左上“第几息”。
      小事件：蜻蜓飞来停在荷叶上 / 一尾鱼吐个泡。续：池里开出一朵莲（一轮一朵，最多四朵），闪光。
中断：睁眼长出一口气，鸿毛被吹飞，龟缩头，“出息”。  恢复：鸿毛飘回鼻前，龟探出头。
圆满：小道士腹中现出一团蜷着的胎形光、外有光环，龟甲纹闪光放光，“如在胞胎”。
点阵：俯视的龟，头随呼吸伸缩。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, span
from ..engine.chars import Part
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import P, Clock, cached, counter, dao, label, mx_art, mx_ring, pop_title, ring, star

FLOOR = 50              # 小道士坐的石面
DX = 30
WATER = 44              # 水面
TX, TY = 98, 40         # 龟（脚底中点）
BREATH = 40.0
SIT = P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"), face="sleep")
SIT_OPEN = P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"), face="wow")
LOTUS_AT = [(70, WATER), (118, WATER - 1), (82, WATER + 6), (60, WATER + 8)]

TURTLE = pix.frames("""
          ##########
       ####.#####.####
     ###.##.#####.##.###
    ##.###.#######.###.##
   ######.#########.######   ###
  #########################.#.##
  #.#.#.#.#.#.#.#.#.#.#.#.#######
   ####    ###      ###   ###
    ##      ##       ##    ##
---
          ##########
       ####.#####.####
     ###.##.#####.##.###
    ##.###.#######.###.##
   ######.#########.######
  ##########################.
  #.#.#.#.#.#.#.#.#.#.#.#.###
   ####    ###      ###   ###
    ##      ##       ##    ##
---
          ##########            ###
       ####.#####.####         #.##
     ###.##.#####.##.###      ## ##
    ##.###.#######.###.##    ##
   ######.#########.######  ##
  ###########################
  #.#.#.#.#.#.#.#.#.#.#.#.###
   ####    ###      ###   ###
    ##      ##       ##    ##
""")

FEATHER = pix.frames("""
 # # # #
########.
  # # #
---
  # # #
########.
 # # # #
""")

DRAGONFLY = pix.frames("""
 # #
#####.
 # #
---
#   #
#####.
""")


def _rock(w, h):
    """平顶石：顶面亮、侧面网点、几道裂纹"""
    p = Part(w, h)
    p.shape("polygon", [(0, h - 1), (2, 2), (5, 0), (w - 6, 0), (w - 2, 3), (w - 1, h - 1)], fill=1)
    p.d.line((3, 2, w - 4, 2), fill=0)
    p.dither([(1, 3), (w - 2, 3), (w - 1, h - 1), (0, h - 1)], 0.5, 0)
    for x in range(6, w - 6, 9):
        p.d.line((x, 3, x + 2, h - 2), fill=0)
    return p.sprite()


def _lotus(stage):
    """莲：0 荷叶，1 花苞，2 盛开"""
    p = Part(13, 10)
    p.shape("ellipse", (0, 7, 12, 9), fill=1)          # 荷叶
    p.d.line((6, 8, 9, 7), fill=0)
    if stage >= 1:
        p.shape("line", (6, 7, 6, 4), fill=1)
    if stage == 1:
        p.shape("ellipse", (4, 0, 8, 5), fill=1)
        p.d.line((6, 1, 6, 4), fill=0)
    elif stage == 2:
        p.shape("polygon", [(2, 2), (4, 5), (8, 5), (10, 2), (8, 3), (6, 0), (4, 3)], fill=1)
        p.d.line((6, 1, 6, 4), fill=0)
        p.px(4, 4, 0), p.px(8, 4, 0)
    return p.sprite()


def willow(g: Gfx, t: float):
    """右上角垂下的柳枝（随风摆）"""
    for j, (x0, L) in enumerate(((62, 18), (70, 24), (78, 14), (56, 12))):
        sw = math.sin(t * 0.9 + j) * 2
        for i in range(L):
            k = i / L
            x = x0 + sw * k * k
            g.px(x, i)
            if i % 4 == 2:
                g.px(x - 1, i + 1), g.px(x + 1, i + 1)
    g.d.line((50, 0, 86, 0), fill=1)


def pond(g: Gfx, t: float, e: float, lotus: int, bloom_k: float = 1.0):
    """池塘：岸、水面波纹、荷叶与莲花、坐石、龟石"""
    g.d.line((56, WATER, 127, WATER), fill=1)
    for r, y in enumerate((WATER + 3, WATER + 7, WATER + 11, WATER + 16)):
        off = int(t * (2 + r)) % 16
        for x in range(56 - 16 + off + r * 5, 128, 16):
            g.d.line((x, y, x + 3, y), fill=1)
    for x in range(0, 128, 2):                                # 远山
        g.px(x, 30 - 4 * math.sin(x * 0.05 + 1.3) - 2 * math.sin(x * 0.16))
    willow(g, t)
    g.d.rectangle((0, WATER - 1, 56, 63), fill=0)
    pix.blit(g, cached(("tt", "rock", 1), lambda: _rock(40, 14)), DX - 20, FLOOR - 1)
    g.d.line((0, 63, 56, 63), fill=1)
    pix.blit(g, cached(("tt", "rock", 2), lambda: _rock(36, 8)), TX - 18, TY)
    for i, (x, y) in enumerate(LOTUS_AT):
        st = 2 if i < lotus else 0
        if i == lotus - 1 and bloom_k < 1:
            st = 1 if bloom_k < 0.5 else 2
        if i >= 2 and st == 0:
            continue
        pix.blit(g, cached(("tt", "lotus", st), lambda st=st: _lotus(st)), x - 6, y - 9)


@register
class Turtle(Ritual):
    id = "r4.turtle"
    name = "龟息"
    desc = "池边石上小道士闭目调息，鼻前悬一根鸿毛；池中老龟跟着伸颈吞气、缩颈闭气，心中默数到一百二十"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)
        self.puffs = pix.Puffs(self.seed)
        self.clock = Clock()

    def phase(self, e: float):
        """一息里第 b 秒：('in'|'hold'|'out', 本段进度)"""
        b = e % BREATH
        if b < 4:
            return "in", b / 4, b
        if b < 34:
            return "hold", (b - 4) / 30, b
        return "out", (b - 34) / 6, b

    def turtle(self, g: Gfx, t: float, ph: str, q: float, glow: bool = False):
        if ph == "in":
            fr = TURTLE[2] if 0.2 < q < 0.85 else TURTLE[0]   # 伸颈仰头吞气
        elif ph == "hold":
            fr = TURTLE[1]
        else:
            fr = TURTLE[0]
        pix.blit(g, fr, TX - 16, TY - fr.h + 1, flip=True)
        if glow:
            for j in range(10):
                a = j * math.pi / 9 + math.pi
                r = 14 + (j % 2) * 3 + math.sin(t * 8 + j) * 1.5
                pix.dotted(g, TX + math.cos(a) * 11, TY - 4 + math.sin(a) * 6, TX + math.cos(a) * r,
                           TY - 4 + math.sin(a) * (r * 0.6), 2, int(t * 10))

    def feather(self, g: Gfx, t: float, h: dict, tremble: float, dx: float = 0, dy: float = 0):
        nx, ny = h["nose"]
        wob = math.sin(t * 25) * tremble
        fr = FEATHER[1] if tremble > 0.3 and (t * 10) % 1 < 0.5 else FEATHER[0]
        pix.blit(g, fr, nx + 2 + dx, ny - 1 + wob + dy)

    def mx(self, g: Gfx, t: float, ph: str, q: float):
        out = ph == "in" or (ph == "out" and q > 0.5)
        mx_art(g, """
..####..
.#.##.#.
.######.
.#.##.#.
.######.
#.####.#
..####..
""", 0, 1)
        if out:
            g.mx[0, 3] = g.mx[0, 4] = True
            g.mx[1, 3] = g.mx[1, 4] = True
        else:
            g.mx[1, 3] = g.mx[1, 4] = (t * 2) % 1 < 0.8

    def labels(self, g: Gfx, e: float, ph: str, q: float):
        n = int(e // BREATH) + 1
        counter(g, f"第{cn_num(n)}息" if n < 100 else f"第{n}息")
        if ph == "hold":
            counter(g, f"默数{min(120, int(q * 120) + 1)}", right=True)
        else:
            counter(g, "引气" if ph == "in" else "微吐", right=True)

    def lotus_count(self, e: float) -> int:
        return min(4, int(e // self.CYCLE))

    def event(self, g: Gfx, t: float, e: float):
        """小事件：蜻蜓飞来停在荷叶上 / 鱼吐泡"""
        slot, ph = int(e // 27), (e % 27) / 8.0
        if ph >= 1:
            return
        if slot % 2 == 0:
            lx, ly = LOTUS_AT[0]
            if ph < 0.4:
                x, y = lerp(130, lx, ease_out(ph / 0.4)), lerp(18, ly - 10, ease_out(ph / 0.4)) + math.sin(ph * 30) * 2
            elif ph < 0.8:
                x, y = lx, ly - 10
            else:
                x, y = lerp(lx, -10, ease_in((ph - 0.8) / 0.2)), ly - 10 - (ph - 0.8) * 60
            fr = DRAGONFLY[0] if ph < 0.4 or ph > 0.8 or int(t * 3) % 3 == 0 else DRAGONFLY[1]
            pix.blit(g, pix.anim(DRAGONFLY, t, 12) if (ph < 0.4 or ph > 0.8) else fr, x - 3, y)
        else:
            x = 76 + (slot * 13) % 30
            for j in range(3):
                k = (ph * 2 - j * 0.3)
                if 0 < k < 1:
                    r = 1 + (j % 2)
                    g.d.ellipse((x + j * 2 - r, WATER + 4 - k * 10 - r, x + j * 2 + r, WATER + 4 - k * 10 + r), outline=1)

    def breath_fx(self, g: Gfx, t: float, h: dict, ph: str, q: float, prog: float):
        nx, ny = h["nose"]
        if ph == "in":  # 清气点点入鼻 / 入龟口
            for j in range(5):
                k = (q * 1.5 + j * 0.2) % 1
                a = j * 1.1 + 0.3
                r = (1 - k) * 16 + 2
                g.px(nx + 2 + math.cos(a) * r, ny + math.sin(a) * r * 0.6)
                g.px(TX - 16 - (1 - k) * 8, TY - 6 - math.sin(k * 3) * 4 - j * 2)
        elif ph == "out":  # 微吐：越往后越细
            n = max(1, int(4 * (1 - prog)))
            for j in range(n):
                k = (q * 2 + j * 0.25) % 1
                g.px(nx + 3 + k * 10, ny + 2 + k * 2)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        pond(g, t, 0, 0)
        # 涟漪 → 龟爬上石头
        if t < 2.0:
            r = t * 8
            ring(g, TX, WATER + 4, r, dotted=2, ry=r * 0.3)
        else:
            k = ease_out(span(t, 2.0, 3.5))
            fr = TURTLE[0] if int(t * 4) % 2 else TURTLE[1]
            pix.blit(g, fr, TX - 16 + (1 - k) * 12, TY - fr.h + 1 + (1 - k) * 8, flip=True)
        h = dao(g, DX, FLOOR, SIT_OPEN if t < 3.5 else SIT, t)
        # 鸿毛从上方飘落到鼻前
        k = ease_in_out(span(t, 2.5, 5.5))
        if t > 2.5:
            nx, ny = h["nose"]
            self.feather(g, t, h, 0.0, math.sin(k * 7) * 6 * (1 - k), -(1 - k) * 34)
        self.mx(g, t, "in", 0.5)
        if t > 5.5:
            self.labels(g, 0.0, "in", 0.0)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        prog = k / self.CYCLE
        lotus = self.lotus_count(e)
        renew = e >= self.CYCLE and k < 4.0
        pond(g, t, e, lotus, span(k, 0.3, 1.6) if renew and lotus <= 4 else 1.0)
        self.event(g, t, e)
        ph, q, b = self.phase(e)
        self.turtle(g, t, ph, q)
        h = dao(g, DX, FLOOR, SIT, t)
        trem = (1 - prog * 0.85) * (math.sin(q * math.pi) if ph == "out" else 0)
        self.feather(g, t, h, trem * 1.5)
        self.breath_fx(g, t, h, ph, q, prog)
        if renew and abs(k - 1.0) < dt and int(e // self.CYCLE) <= 4:
            x, y = LOTUS_AT[max(lotus - 1, 0)]
            pix.flash(g)
            self.sparks.burst(x, y - 6, 16, 24, up=10, life=0.8, gravity=20)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, ph, q)
        if renew and k > 1.2:
            n = int(e // BREATH) + 1
            counter(g, f"第{cn_num(n)}息" if n < 100 else f"第{n}息")
            nl = int(e // self.CYCLE)
            pop_title(g, 92, 3, f"{cn_num(nl)}轮莲开" if nl < 100 else f"{nl}轮", span(k, 1.2, 1.6), t)
        else:
            self.labels(g, e, ph, q)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        pond(g, t, e, self.lotus_count(e))
        ph, q, b = self.phase(e)
        self.turtle(g, t, "hold", 0)
        h = dao(g, DX, FLOOR, SIT_OPEN if t > 0.3 else SIT, t)
        k = ease_in(span(t, 0.3, 1.6))
        self.feather(g, t, h, 2.0 if t < 0.3 else 0, k * 70, -k * 30 + math.sin(t * 9) * 3 * k)
        if 0.3 < t < 1.0:  # 长出一口气
            nx, ny = h["nose"]
            for j in range(3):
                g.d.arc((nx + 2 + j * 4, ny - 4, nx + 6 + j * 4, ny + 4), -50, 50, fill=1)
        self.mx(g, t, "hold", 0)
        n = int(e // BREATH) + 1
        counter(g, f"第{cn_num(n)}息" if n < 100 else f"第{n}息")
        if t > 0.6:
            counter(g, "出息", right=True)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        pond(g, t, e, self.lotus_count(e))
        ph, q, b = self.phase(e)
        self.turtle(g, t, "hold" if t < 0.8 else ph, q)
        h = dao(g, DX, FLOOR, SIT, t)
        k = 1 - ease_out(span(t, 0.0, 1.6))
        self.feather(g, t, h, 0, math.sin(t * 6) * 8 * k, -k * 30)
        if abs(t - 0.8) < dt:
            self.sparks.burst(TX - 14, TY - 4, 8, 14, life=0.4, gravity=10)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, ph, q)
        self.labels(g, e, ph, q)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        pond(g, t, e, max(self.lotus_count(e), 1))
        self.turtle(g, t, "hold", 0, glow=t > 2.0)
        h = dao(g, DX, FLOOR, SIT if t < 4.2 else P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"), face="happy"), t)
        self.feather(g, t, h, 0)
        bx, by = DX + 2, FLOOR - 11
        if t > 1.0:  # 腹中胎形光：一个蜷着的小光团 + 光环
            k = ease_out(span(t, 1.0, 2.0))
            r = 2 + k * 3
            g.d.ellipse((bx - r - 1, by - r - 1, bx + r + 1, by + r + 1), fill=0)
            g.d.ellipse((bx - r, by - r, bx + r, by + r), outline=1)
            if k > 0.6:
                g.d.ellipse((bx - 2, by - 3, bx + 1, by), fill=1)       # 头
                g.d.arc((bx - 3, by - 2, bx + 3, by + 3), 300, 200, fill=1)  # 蜷着的身子
            for j in range(2):
                rr = ((t - 1.0) * 10 + j * 8) % 18 + r + 2
                ring(g, bx, by, rr, dotted=2, ry=rr * 0.8)
        if abs(t - 2.0) < dt:
            pix.flash(g)
            self.sparks.burst(TX, TY - 6, 20, 30, up=10, life=0.9, gravity=20)
        if 2.0 < t < 2.3:
            pix.shake(g, t, 1.2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, "hold", 0)
        if t > 2.0:
            mx_ring(g, (t - 2.0) * 4 % 5)
            g.mx_level = 1 + int(6 * (1 - span(t, 2.0, 3.5)))
        if t > 2.6:
            pop_title(g, 64, 3, "如在胞胎", span(t, 2.6, 3.0), t)
        else:
            n = int(e // BREATH) + 1
            counter(g, f"第{cn_num(n)}息" if n < 100 else f"第{n}息")
