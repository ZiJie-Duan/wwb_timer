"""蝉蜕：树干上一只蝉在唱，下面留着一只空壳；每隔一阵，看一回金蝉脱壳。

依据：《史记·屈原贾生列传》“蝉蜕于浊秽，以浮游尘埃之外”；道教以“蝉蜕”比喻尸解——
      脱去旧壳，羽化而去（《抱朴子·论仙》“下士先死后蜕，谓之尸解仙”）。
入场：树干从下往上显出来，蝉从右上方飞来，落在树干上收翅，开唱。
持续：蝉一阵一阵地叫（腹部鼓动、两侧声波、点阵上是跳动的声柱），歇一歇再叫。树叶轻摆。
      每 80 秒演一回脱壳：老蝉振翅飞走 → 旧壳掉落 → 一只若虫从树根慢慢爬上来 → 背上裂开，
      嫩白的新蝉一点点钻出、翅膀展开变硬 → 新蝉爬到高处接着唱，空壳留在原处。
收场：蝉振翅飞走，留下空壳与树干，画面收拢。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import Bake, mx_sprite, sound_arcs

CX = 64
SING_Y = 7           # 蝉（贴图顶）唱歌的位置
SHELL_Y = 44         # 空壳的位置
EV0, EV_P = 30.0, 80.0


def _trunk() -> Sprite:
    b = Bake(44, 64)
    b.poly([(2, 63), (5, 40), (4, 20), (7, 0), (37, 0), (40, 22), (39, 44), (42, 63)], 0.0)
    import random
    r = random.Random(3)
    for x, y0, y1 in ((8, 2, 22), (34, 8, 30), (9, 40, 60), (35, 44, 62), (12, 28, 36), (31, 52, 58)):   # 树皮纵纹（只在两边）
        b.line([(x + math.sin(y * 0.2) * 1.0, y) for y in range(y0, y1 + 1, 3)])
    return b.sprite()


def _adult(pale: bool = False, wing: float = 1.0) -> Sprite:
    """背面看的蝉（头朝上）：宽 23，高 32。pale：刚脱壳的嫩蝉；wing：翅膀展开程度"""
    b = Bake(23, 32)
    lvl = 0.25 if pale else 0.0
    wl = 8 + 15 * wing         # 翅长
    for s in (-1, 1):          # 两片前翅（帐篷形，覆在腹上）
        base = (11 + s * 1, 13)
        pts = [base, (11 + s * 9, 15), (11 + s * 10, 15 + wl * 0.55), (11 + s * 7, 13 + wl), (11 + s * 1, 13 + wl * 0.85)]
        b.poly(pts, lvl)
        if wing > 0.6:   # 翅脉
            b.line([(11 + s * 2, 15), (11 + s * 8, 13 + wl * 0.9)])
            b.line([(11 + s * 5, 15), (11 + s * 9, 15 + wl * 0.5)])
            b.line([(11 + s * 3, 13 + wl * 0.55), (11 + s * 9, 13 + wl * 0.6)])
    b.poly([(3, 7), (19, 7), (17, 13), (5, 13)], lvl)          # 前胸
    b.line([(7, 9), (11, 11), (15, 9)])
    b.poly([(6, 12), (16, 12), (14, 17), (8, 17)], 0.5 if not pale else 0.25)   # 中胸（深色）
    b.ellipse((4, 1, 18, 8), lvl)                             # 头
    b.ellipse((0, 2, 5, 7), 1.0)                              # 复眼
    b.ellipse((17, 2, 22, 7), 1.0)
    b.point(11, 3)
    b.point(10, 4)
    b.point(12, 4)
    return b.sprite()


SHELL_ART = """
##.............##
.#...#######...#.
.#..#.......#..#.
..##.##...##.##..
....#.......#....
...#....#....#...
#.#.....#.....#.#
.##....#.#....##.
...#...#.#...#...
...#....#....#...
....#.......#....
#..#.........#..#
.##.#########.##.
....#.......#....
....#########....
.....#.....#.....
.....#######.....
......#...#......
.......###.......
"""


def _nymph(shell: bool = False) -> Sprite:
    """若虫 / 蝉蜕（背面，头朝上，大钩状前足）：宽 17，高 19。shell：空壳（背上裂开，透亮）；否则身体是深褐色（抖动）"""
    rows = []
    for y, ln in enumerate(SHELL_ART.strip("\n").split("\n")):
        i0, i1 = ln.find("#"), ln.rfind("#")
        out = []
        for x, ch in enumerate(ln):
            if x < i0 or x > i1:
                out.append(" ")
            elif ch == "." and not shell and 2 <= y <= 17 and 4 <= x <= 12 and (x + y) % 2 == 0:
                out.append("#")
            else:
                out.append(ch)
        rows.append("".join(out))
    art = "\n".join(rows)
    if not shell:   # 若虫背上没有裂口
        art_rows = art.split("\n")
        for y in (5, 6, 7, 8, 9):
            r = list(art_rows[y])
            r[8] = "#" if (8 + y) % 2 == 0 else "."
            if y in (7, 8):
                r[7] = "#" if (7 + y) % 2 == 0 else "."
                r[9] = "#" if (9 + y) % 2 == 0 else "."
            art_rows[y] = "".join(r)
        art = "\n".join(art_rows)
    return Sprite(art)


TRUNK = _trunk()
ADULT = _adult()
SHELL = _nymph(True)
NYMPH = _nymph(False)
PALE = [_adult(True, w) for w in (0.0, 0.25, 0.5, 0.75, 1.0)]

MX_CICADA = """
#.####.#
.######.
..####..
.##..##.
.##..##.
.##..##.
..#..#..
........
"""


def flying(g: Gfx, x: float, y: float, t: float, face: int = 1):
    """飞着的蝉（侧上方看）：身体 + 振翅的两对翅（交替两个位置 = 嗡嗡的残影）"""
    up = int(t * 20) % 2
    for s in (-1, 1):   # 上下两片翅：振动的两个位置
        a = (0.35 if up else 0.9)
        ex, ey = x - 6 * face, y + s * (4 + 9 * math.sin(a))
        g.d.polygon([(x + 1 * face, y), (ex + 3 * face, ey), (ex - 4 * face, ey + s * 1), (x - 3 * face, y)],
                    fill=0, outline=1)
    g.d.ellipse((x - 5, y - 3, x + 5, y + 3), fill=1)
    g.d.ellipse((x + 3 * face - 2, y - 3, x + 3 * face + 2, y + 3), fill=0, outline=1)   # 头与复眼
    g.px(x + 5 * face, y - 2)
    g.px(x + 5 * face, y + 2)


@register
class Cicada(Rest):
    id = "x4.cicada"
    name = "蝉蜕"
    desc = "树上一只蝉一阵阵地叫，下面挂着空壳；每隔一阵演一回金蝉脱壳：若虫爬上来，裂背羽化，新蝉爬高再唱"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.sing_p = self.rng.choice((9.0, 11.0, 13.0))

    # ------------------------------------------------------------ 零件

    def leaves(self, g: Gfx, t: float):
        """右上角伸进来的一枝，几片叶子轻摆"""
        g.d.line((84, 12, 98, 8, 112, 9), fill=1)
        for i, (x, y) in enumerate(((92, 9), (100, 8), (108, 9))):
            sw = math.sin(t * 0.9 + i) * 1.5
            tip = (x + 3 + sw, y + 11)
            g.d.polygon([(x, y), (x + 4 + sw * 0.5, y + 5), tip, (x - 1 + sw * 0.5, y + 6)], fill=0, outline=1)
            g.d.line((x, y + 1, tip[0] - 1, tip[1] - 2), fill=1)

    def singing(self, t: float) -> float:
        """唱歌的强度（0 = 歇着），一阵一阵"""
        k = t % self.sing_p
        on = self.sing_p * 0.6
        if k > on:
            return 0.0
        return span(k, 0, 0.5) * (1 - span(k, on - 0.5, on))

    def sing_fx(self, g: Gfx, t: float, y: float, s: float):
        if s <= 0:
            return
        k = (t * 2.2) % 1
        sound_arcs(g, CX + 13, y + 20, k, n=3, gap=4, right=True, spread=0.7)
        sound_arcs(g, CX - 13, y + 20, k, n=3, gap=4, right=False, spread=0.7)
        if int(t * 16) % 2:   # 腹部鼓膜一抖
            g.d.line((CX - 1, y + 21, CX + 1, y + 21), fill=1)

    def mx_sing(self, g: Gfx, t: float, s: float):
        if s <= 0:
            mx_sprite(g, MX_CICADA)
            return
        for x in range(8):   # 声柱
            h = int(1 + s * 7 * noise(t * 9 + x * 1.7, self.seed + x))
            for y in range(8 - h, 8):
                g.mx[y, x] = True

    # ------------------------------------------------------------ 脱壳事件

    def event(self, t: float):
        if t < EV0:
            return -1.0, 0
        return (t - EV0) % EV_P, int((t - EV0) // EV_P)

    def draw(self, g: Gfx, t: float, text_a: float = 1.0):
        g.blit(TRUNK, CX - 22, 0)
        self.leaves(g, t)
        k, n = self.event(t)
        if text_a > 0:
            s = "蝉蜕于浊秽"
            g.vtext(2, 2, s[:int(round(text_a * len(s)))])
        if k < 0 or k >= 34:      # 平常：上面的蝉唱，下面挂着空壳
            g.blit(SHELL, CX - 8, SHELL_Y)
            g.blit(ADULT, CX - 11, SING_Y)
            s = self.singing(t)
            self.sing_fx(g, t, SING_Y, s)
            self.mx_sing(g, t, s)
            return
        # ---- 脱壳的一回 ----
        sing = 0.0
        if k < 3.0:     # 老蝉振翅飞走（往右上）
            p = ease_in(k / 3.0)
            g.blit(SHELL, CX - 8, SHELL_Y)
            if k < 0.6:
                g.blit(ADULT, CX - 11, SING_Y)
            else:
                flying(g, CX + p * 80, SING_Y + 14 - p * 30 + math.sin(k * 8) * 2, t)
                sing = 1.0
        elif k < 5.0:   # 旧壳掉落
            p = (k - 3.0) / 2.0
            y = SHELL_Y + ease_in(p) * 30
            g.blit(SHELL, CX - 8 + p * 6, y)
        elif k < 15.0:  # 若虫从树根爬上来
            p = (k - 5.0) / 10.0
            y = lerp(66, SHELL_Y, ease_out(p))
            wob = math.sin(k * 6) * 0.6
            g.blit(NYMPH, CX - 8 + wob, y)
        elif k < 17.0:  # 停住，背上裂开
            g.blit(NYMPH, CX - 8, SHELL_Y)
            split = span(k, 15.5, 16.8)
            if split > 0:
                g.d.line((CX, SHELL_Y + 4, CX, SHELL_Y + 4 + split * 6), fill=0)
                g.d.line((CX - 1, SHELL_Y + 4, CX - 1, SHELL_Y + 4 + split * 6), fill=1)
                g.d.line((CX + 1, SHELL_Y + 4, CX + 1, SHELL_Y + 4 + split * 6), fill=1)
        elif k < 26.0:  # 嫩蝉钻出、翅膀展开
            p = ease_out(span(k, 17.0, 21.0))
            y = lerp(SHELL_Y + 6, SHELL_Y - 26, p)
            w = span(k, 20.0, 25.0)
            spr = PALE[min(4, int(w * 4.99))]
            g.blit(SHELL, CX - 8, SHELL_Y)
            # 还没完全钻出来时，下半截被壳遮住
            g.blit(spr, CX - 11, y)
            if p < 1:
                cut = SHELL_Y + 10
                g.d.rectangle((CX - 11, cut, CX + 11, y + 32), fill=0)
                g.blit(SHELL, CX - 8, SHELL_Y)
            if 21.5 < k < 26.0:
                g.vtext(115, 15, "金蝉脱壳"[:int(clamp((k - 21.5) * 3, 0, 4))])
        else:           # 翅膀变硬变深，爬到高处
            p = ease_in_out(span(k, 27.0, 33.0))
            y = lerp(SHELL_Y - 26, SING_Y, p)
            g.blit(SHELL, CX - 8, SHELL_Y)
            g.blit(ADULT if k > 26.6 else PALE[4], CX - 11, y)
            if k < 30:
                g.vtext(115, 15, "金蝉脱壳")
        mx_sprite(g, MX_CICADA)
        if sing:
            self.mx_sing(g, t, 1.0)

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float):
        self.draw(g, t)

    def enter(self, g: Gfx, t: float):
        T = self.T["enter"]
        reveal = ease_out(span(t, 0, 1.2))
        g.blit(TRUNK, CX - 22, 64 - reveal * 64)
        if t > 0.6:
            self.leaves(g, t)
            g.blit(SHELL, CX - 8, SHELL_Y + (1 - reveal) * 64)
        if t < 2.2:   # 从右上飞来
            p = ease_out(span(t, 0.8, 2.2))
            if p > 0:
                flying(g, lerp(140, CX, p), lerp(-6, SING_Y + 14, p), t, -1)
            mx_sprite(g, MX_CICADA)
        else:
            g.blit(ADULT, CX - 11, SING_Y)
            s = span(t, 2.6, T)
            self.sing_fx(g, t, SING_Y, s)
            self.mx_sing(g, t, s * 0.6)
        g.vtext(2, 2, "蝉蜕于浊秽"[:int(span(t, 1.2, T) * 5 + 0.5)])

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        t0 = self.hold_t
        k, n = self.event(t0)
        g.blit(TRUNK, CX - 22, 0)
        self.leaves(g, t0 + t)
        if 3.0 <= k < 5.0:
            pass
        elif not (5.0 <= k < 15.0):
            g.blit(SHELL, CX - 8, SHELL_Y)
        p = ease_in(span(t, 0.2, T))
        if 3.0 <= k < 26.0:   # 正在脱壳：画面就这样淡出
            pass
        elif t < 0.2:
            g.blit(ADULT, CX - 11, SING_Y)
        else:
            flying(g, CX + p * 80, SING_Y + 14 - p * 30, t0 + t)
        g.vtext(2, 2, "蝉蜕于浊秽"[:int(round((1 - span(t, 0, 0.8)) * 5))])
        mx_sprite(g, MX_CICADA)
        g.fade(1 - span(t, T * 0.55, T))
