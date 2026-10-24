"""河图洛书：龙马负图、神龟负书，小道士在河岸上一组一组地认数。

依据：《系辞上》“河出图，洛出书，圣人则之”。河图：一六居下、二七居上、三八居左、四九居右、五十居中，
奇数白点（空心）、偶数黑点（实心）；《青囊经》“一六共宗，二七同道，三八为朋，四九为友，五十同途”。
洛书：“戴九履一，左三右七，二四为肩，六八为足，以五居中”。

画面：左边河岸（土坡、草、石），小道士站在岸上；右边一条河，水面起伏。河中央浮着一方图版（双线框、四角云纹），
图版右边水里探出负图的龙马（头生一角、颈有鬃）或负书的神龟（龟甲隆起、甲片纹）。
入场：水面起波、一圈涟漪，龙马从水里探出头，图版随之升起，水珠滴落；“一”浮现。
持续：单数轮演河图（1→10，每组 60 秒），双数轮演洛书（1→9，画在九宫里，每组约 67 秒）；
      还没浮现的组只留暗点，新一组的点一颗颗弹出、放一圈波纹，小道士剑指点数；左上写对应口诀。
      其余时间：鱼跃出水面（带水花）、龙马/神龟眨眼点头、小道士作揖。
      续：一道浪从左扫过，旧图版与神兽沉下，另一位神兽负着另一张图浮起，“河图”/“洛书”。
中断：图版沉入水中一半，神兽缩回水里，水波荡漾，“暂歇”。  恢复：图版浮起，水珠滴落。
圆满：余下各组一齐浮现，河图生成之数两两相连 / 洛书纵横斜连线（皆十五），图版边框闪烁，“圣人则之”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r5_util import GRASS, Clock, cached, label, mx_ring, pop_box, ring, rock, sparkle

BANK = 52                  # 河岸地面
WY = 48                    # 水面
DX = 26
PX, PY = 72, 24            # 图版中心
PW, PH = 25, 21            # 图版半宽、半高
P = 4                      # 点距
RENEW = 5.0

# 河图：数 → 点位（格坐标，相对图心）
HETU = {
    1: [(0, 3)],
    2: [(-0.5, -3), (0.5, -3)],
    3: [(-3, -1), (-3, 0), (-3, 1)],
    4: [(3, -1.5), (3, -0.5), (3, 0.5), (3, 1.5)],
    5: [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)],
    6: [(x - 2.5, 4) for x in range(6)],
    7: [(x - 3, -4) for x in range(7)],
    8: [(-4, y - 1.5) for y in range(4)] + [(-5, y - 1.5) for y in range(4)],
    9: [(4, y - 2) for y in range(5)] + [(5, y - 1.5) for y in range(4)],
    10: [(x - 2, -2) for x in range(5)] + [(x - 2, 2) for x in range(5)],
}
# 洛书：九宫（行, 列）→ 数
LUOSHU = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]
LO_PAT = {  # 每组点在宫内的排法（格坐标，相对宫心）
    1: [(0, 0)], 2: [(-0.5, 0), (0.5, 0)], 3: [(-1, 0), (0, 0), (1, 0)],
    4: [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)],
    5: [(0, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)],
    6: [(x - 1, y - 0.5) for y in range(2) for x in range(3)],
    7: [(x - 1.5, -0.5) for x in range(4)] + [(x - 1, 0.5) for x in range(3)],
    8: [(x - 1.5, y - 0.5) for y in range(2) for x in range(4)],
    9: [(x - 1, y - 1) for y in range(3) for x in range(3)],
}
CELL_W, CELL_H = 15, 12
HE_SONG = {1: "一六共宗", 6: "一六共宗", 2: "二七同道", 7: "二七同道", 3: "三八为朋", 8: "三八为朋",
           4: "四九为友", 9: "四九为友", 5: "五十同途", 10: "五十同途"}
LO_SONG = {9: "戴九履一", 1: "戴九履一", 3: "左三右七", 7: "左三右七", 2: "二四为肩", 4: "二四为肩",
           6: "六八为足", 8: "六八为足", 5: "以五居中"}
LO_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9]


def lo_cell(n: int):
    for r, row in enumerate(LUOSHU):
        for c, v in enumerate(row):
            if v == n:
                return PX + (c - 1) * CELL_W, PY + (r - 1) * CELL_H
    raise KeyError(n)


def dots_of(kind: str, n: int, dy: float = 0.0):
    """第 n 组的点（屏幕坐标）"""
    if kind == "he":
        return [(PX + x * P, PY + y * P + dy) for x, y in HETU[n]]
    cx, cy = lo_cell(n)
    return [(cx + x * P, cy + y * P + dy) for x, y in LO_PAT[n]]


def dot(g: Gfx, x: float, y: float, odd: bool, s: float = 1.0):
    """奇数白点（空心圈）、偶数黑点（实心）；s 为弹出缩放"""
    x, y = int(round(x)), int(round(y))
    if s < 0.5:
        g.px(x, y)
        return
    g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
    if odd:
        g.px(x, y, 0)
    if s > 1.15:
        g.px(x - 2, y), g.px(x + 2, y), g.px(x, y - 2), g.px(x, y + 2)


def plate(g: Gfx, kind: str, dy: float, t: float, flash: bool = False):
    """图版：双线框，四角云纹；洛书加九宫虚线与龟甲边"""
    x0, y0, x1, y1 = PX - PW, PY - PH + dy, PX + PW, PY + PH + dy
    g.d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=0)
    g.d.rectangle((x0, y0, x1, y1), outline=1)
    if not flash:
        g.d.rectangle((x0 + 2, y0 + 2, x1 - 2, y1 - 2), outline=1)
    for cx, cy, sx, sy in ((x0 + 2, y0 + 2, 1, 1), (x1 - 2, y0 + 2, -1, 1), (x0 + 2, y1 - 2, 1, -1),
                           (x1 - 2, y1 - 2, -1, -1)):   # 角上云纹（小卷）
        g.d.rectangle((cx, cy, cx + sx * 3, cy + sy * 3), fill=0)
        g.px(cx, cy), g.px(cx + sx, cy), g.px(cx + sx * 2, cy), g.px(cx + sx * 2, cy + sy)
        g.px(cx + sx, cy + sy * 2), g.px(cx, cy + sy), g.px(cx, cy + sy * 2)
    if kind == "lo":
        for c in (-1, 1):
            x = PX + c * CELL_W / 2
            for y in range(int(y0 + 4), int(y1 - 3), 2):
                g.px(x, y)
        for r in (-1, 1):
            y = PY + r * CELL_H / 2 + dy
            for x in range(int(x0 + 4), int(x1 - 3), 2):
                g.px(x, y)


HORSE = """
           # ##
     #    ## ##
      #  #######
       ##########.#
      ####.######.##
     ##############.#
    #########.#######
   ########.. #####.#
  #######     #######
 ######        ####.#
#######        ######
#.####         ####.#
 ####.         ######
  ..           ####.#
               ######
"""


def _horse():
    """龙马头颈 18×16（朝左）：长脸、立耳、额上一角、圆眼，颈后一排鬃毛（暗缝）"""
    from ..engine.gfx import Sprite
    return Sprite(HORSE)


def _turtle():
    """神龟 30×14（朝左）：圆头、眼、嘴线，伸颈；龟甲隆起，甲片纹，甲缘一圈齿"""
    p = Part(30, 14)
    p.shape("ellipse", (7, 2, 29, 22), fill=1)                                      # 甲（下半没在水里）
    p.d.arc((9, 4, 27, 20), 180, 360, fill=0)
    for x in (13, 18, 23):                                                           # 甲片
        p.d.line((x, 5, x, 10), fill=0)
    p.d.line((10, 8, 26, 8), fill=0)
    for x in range(9, 28, 3):
        p.px(x, 12, 0)
    p.shape("polygon", [(4, 8), (9, 7), (9, 12), (4, 12)], fill=1)                  # 颈
    p.shape("ellipse", (0, 3, 7, 10), fill=1)                                       # 头
    p.d.rectangle((2, 5, 3, 6), fill=0)
    p.px(2, 5, 1)
    p.d.line((0, 8, 3, 8), fill=0)
    p.dither([(20, 8), (29, 8), (29, 14), (20, 14)], 0.5, 0)
    return p.sprite()


def horse():
    return cached(("r5hetu", "horse"), _horse)


def turtle():
    return cached(("r5hetu", "turtle"), _turtle)


def _fish(f: int):
    p = Part(9, 5)
    p.shape("ellipse", (2, 0, 8, 4), fill=1)
    p.shape("polygon", [(0, 0 + f), (3, 2), (0, 4 - f)], fill=1)
    p.px(6, 1, 0)
    p.d.line((4, 2, 5, 2), fill=0)
    return p.sprite()


def fish(f):
    return cached(("r5hetu", "fish", f), lambda: _fish(f))


def vlabel(g: Gfx, s: str):
    """左边竖排的框字（口诀）"""
    h = len(s) * 12 - 1
    g.k.rectangle((0, 0, 16, h + 6), fill=1)
    g.d.rectangle((1, 1, 15, h + 5), fill=0, outline=1)
    g.vtext(2, 4, s)


@register
class HeTu(Clock, Ritual):
    id = "r5.hetu"
    name = "河图洛书"
    desc = "河中龙马负图、神龟负书浮出水面，图版上的点按河图、洛书一组组浮现；小道士在岸上剑指点数，左上写口诀"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 1.8, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)
        self.puffs = pix.Puffs(self.seed + 2)

    # ------------------------------------------------------------ 状态

    def state(self, e: float):
        """→ (轮 c, 轮内 k, 图 kind, 已浮现的组数 n, 最新一组浮现了多久)"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        kind = "he" if c % 2 == 0 else "lo"
        total = 10 if kind == "he" else 9
        seg = (self.CYCLE - RENEW) / total
        off = RENEW if c >= 1 else 0.0
        kk = k - off
        if kk < 0:
            return c, k, kind, 0, 0.0
        n = min(int(kk // seg) + 1, total)
        return c, k, kind, n, kk - (n - 1) * seg

    # ------------------------------------------------------------ 画

    def water(self, g: Gfx, t: float, x0: int = 36):
        """水面：起伏的白线；水下几道移动的水纹、网点"""
        pts = [(x, WY + round(math.sin(x * 0.35 + t * 2.5) * 0.8)) for x in range(x0, 129, 1)]
        g.d.rectangle((x0, WY + 1, 127, 63), fill=0)
        g.d.line(pts, fill=1)
        for j, y in enumerate((52, 56, 60)):
            off = (t * (6 + j * 3) + j * 17) % 24
            for x in range(x0 + int(off) - 24, 128, 24):
                if x >= x0 + 2:
                    g.d.line((x, y, x + 6 - j, y), fill=1)
        pix.checker(g, (x0 + 2, 58, 128, 64), 0.125)

    def bank(self, g: Gfx, t: float):
        g.d.polygon([(0, BANK), (34, BANK), (42, 63), (0, 63)], fill=0)
        g.d.line((0, BANK, 34, BANK, 42, 63), fill=1)
        pix.checker(g, (0, BANK + 2, 36, 64), 0.25)
        pix.blit(g, rock(), 4, BANK - 5)
        pix.blit(g, pix.anim(GRASS, t * 0.7, 2), 33, BANK - 3)

    def beast(self, g: Gfx, kind: str, rise: float, t: float, blink: bool = False):
        """神兽：rise 0（没在水下）..1（探出）；头微微点动"""
        if rise <= 0:
            return
        bob = round(math.sin(t * 1.3) * 1)
        if kind == "he":
            spr = horse()
            x, y = 107, WY - 15 + (1 - rise) * 18 + bob
        else:
            spr = turtle()
            x, y = 98, WY - 9 + (1 - rise) * 14 + bob
        pix.blit(g, spr, x, y)
        if blink:
            ex, ey = (x + 7, y + 5) if kind == "he" else (x + 2, y + 5)
            g.d.line((ex, ey + 1, ex + 1, ey + 1), fill=0)
            g.px(ex, ey, 1), g.px(ex + 1, ey, 1)

    def diagram(self, g: Gfx, kind: str, n: int, age: float, dy: float, t: float, all_on: float = 0.0):
        """已浮现的组；未浮现的只留暗点；最新一组按 age 一颗颗弹出"""
        nums = list(range(1, 11)) if kind == "he" else LO_ORDER
        for idx, num in enumerate(nums):
            pts = dots_of(kind, num, dy)
            odd = num % 2 == 1
            if idx < n - 1 or (all_on > 0 and idx >= n):
                s = 1.0 if idx < n - 1 else ease_out_back(span(all_on, (idx - n) * 0.08, (idx - n) * 0.08 + 0.3))
                for x, y in pts:
                    dot(g, x, y, odd, s)
            elif idx == n - 1:
                for j, (x, y) in enumerate(pts):
                    s = ease_out_back(span(age, 0.6 + j * 0.15, 0.9 + j * 0.15)) * 1.0
                    if s > 0:
                        dot(g, x, y, odd, s * (1.2 if 0.95 < s < 1.05 and age < 3 else 1))
                    else:
                        g.px(x, y)
                done = 0.9 + len(pts) * 0.15
                if done < age < done + 0.8:      # 一圈波纹
                    cx = sum(p[0] for p in pts) / len(pts)
                    cy = sum(p[1] for p in pts) / len(pts)
                    ring(g, cx, cy, (age - done) * 14, (age - done) * 10)
                if age > done and (t * 2) % 1 < 0.15:   # 之后一闪一闪
                    for x, y in pts:
                        g.px(x, y, 0 if odd else 1)
            else:
                for x, y in pts:
                    if (int(x) + int(y)) % 2 == 0:
                        g.px(x, y)

    def fish_jump(self, g: Gfx, e: float, t: float):
        """约 23 秒一条鱼跃出水面（带水花）"""
        q = (e % 23) / 1.4
        if q >= 1:
            return
        i = int(e // 23)
        x0 = 33 + rand(i, self.seed) * 2
        x = x0 + q * 8
        y = WY - math.sin(q * math.pi) * 11
        spr = fish(int(t * 8) % 2)
        pix.blit(g, spr, x, y - 2)
        for j, qq in enumerate((0.05, 0.95)):
            if abs(q - qq) < 0.12:
                sx = x0 + qq * 8 + 4
                g.px(sx - 2, WY - 2), g.px(sx + 2, WY - 2), g.px(sx - 1, WY - 3), g.px(sx + 1, WY - 3)

    def actor(self, g: Gfx, e: float, t: float, age: float):
        if 0.5 < age < 3.5:
            h = daoshi(g, DX, BANK, "point", t, face="wow" if age < 1.5 else "normal")
            return
        ph = e % 21
        if 12 < ph < 14.5:
            daoshi(g, DX, BANK, "bow" if 12.6 < ph < 13.9 else "gongshou", t)
        else:
            daoshi(g, DX, BANK, "idle", t)

    def song(self, kind: str, num: int) -> str:
        return (HE_SONG if kind == "he" else LO_SONG)[num]

    def mx(self, g: Gfx, num: int, t: float):
        """骰子式点数"""
        pats = {1: [(3, 3)], 2: [(1, 1), (5, 5)], 3: [(1, 1), (3, 3), (5, 5)], 4: [(1, 1), (5, 1), (1, 5), (5, 5)],
                5: [(1, 1), (5, 1), (3, 3), (1, 5), (5, 5)], 6: [(1, 1), (5, 1), (1, 3), (5, 3), (1, 5), (5, 5)],
                7: [(1, 1), (5, 1), (1, 3), (3, 3), (5, 3), (1, 5), (5, 5)],
                8: [(1, 1), (3, 1), (5, 1), (1, 3), (5, 3), (1, 5), (3, 5), (5, 5)],
                9: [(x, y) for x in (1, 3, 5) for y in (1, 3, 5)],
                10: [(0, 1), (2, 1), (4, 1), (6, 1), (2, 3), (4, 3), (0, 5), (2, 5), (4, 5), (6, 5)]}
        for x, y in pats[num]:
            g.mx_set(x, y), g.mx_set(x + 1, y), g.mx_set(x, y + 1), g.mx_set(x + 1, y + 1)

    def scene(self, g: Gfx, t: float, e: float, dt: float):
        c, k, kind, n, age = self.state(e)
        renew = c >= 1 and k < RENEW
        self.bank(g, t)
        if renew:                          # 续：浪从左扫过，旧图沉、新图起
            prev = "lo" if kind == "he" else "he"
            q = span(k, 0.3, 2.3)
            sink = ease_in(q) * 46
            if q < 1:
                self.beast(g, prev, 1 - q, t)
                plate(g, prev, sink, t)
                self.diagram(g, prev, 10 if prev == "he" else 9, 99, sink, t)
            r = ease_out_back(span(k, 2.6, 4.4))
            if r > 0:
                self.beast(g, kind, r, t)
                plate(g, kind, (1 - r) * 46, t)
                self.diagram(g, kind, 0, 0, (1 - r) * 46, t)
            self.water(g, t)
            wx = lerp(-10, 140, span(k, 0.2, 2.2))     # 一道浪
            if 0 < span(k, 0.2, 2.2) < 1:
                g.d.line((wx - 8, WY, wx - 3, WY - 4, wx, WY - 6, wx + 2, WY - 4, wx + 1, WY - 2), fill=1)
                g.px(wx + 3, WY - 6), g.px(wx + 1, WY - 8)
            daoshi(g, DX, BANK, "gongshou" if k < 3 else "bow", t)
            return c, k, kind, n, age, renew
        self.beast(g, kind, 1.0, t, blink=(e % 5.3) < 0.15)
        plate(g, kind, 0, t)
        self.diagram(g, kind, n, age, 0, t)
        self.water(g, t)
        if 0 < age < 1.2:                                # 新一组：水珠从图版滴落
            for j in range(3):
                y = PY + PH + 2 + ease_in(span(age, j * 0.2, j * 0.2 + 0.6)) * (WY - PY - PH - 2)
                if y < WY:
                    g.px(PX - 12 + j * 12, y), g.px(PX - 12 + j * 12, y + 1)
        self.fish_jump(g, e, t)
        self.actor(g, e, t, age)
        return c, k, kind, n, age, renew

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        self.bank(g, t)
        r = ease_out_back(span(t, 1.0, 2.6))
        self.beast(g, "he", r, t)
        dy = (1 - ease_out(span(t, 1.6, 3.2))) * 46
        if t > 1.6:
            plate(g, "he", dy, t)
            self.diagram(g, "he", 1 if t > 3.2 else 0, max(0, t - 3.2), dy, t)
        self.water(g, t)
        if t < 1.6:
            ring(g, PX, WY, (t * 30) % 40, (t * 30) % 40 * 0.25)
        if 3.0 < t < 4.2:
            for j in range(3):
                y = PY + PH + 2 + ease_in(span(t, 3.0 + j * 0.2, 3.6 + j * 0.2)) * (WY - PY - PH - 2)
                if y < WY:
                    g.px(PX - 12 + j * 12, y), g.px(PX - 12 + j * 12, y + 1)
        daoshi(g, DX, BANK, "gongshou" if 1.2 < t < 2.4 else ("point" if 3.6 < t < 5.0 else "idle"), t,
               face="wow" if 1.2 < t < 2.4 else "normal")
        if t > 3.6:
            vlabel(g, "一六共宗")
        self.mx(g, 1, t) if t > 3.2 else mx_ring(g, (t * 3) % 5)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, kind, n, age, renew = self.scene(g, t, e, dt)
        if renew:
            if k > 2.4:
                vlabel(g, "河图" if kind == "he" else "洛书")
            mx_ring(g, (t * 4) % 5)
            return
        nums = list(range(1, 11)) if kind == "he" else LO_ORDER
        num = nums[max(n, 1) - 1]
        vlabel(g, self.song(kind, num))
        self.mx(g, num, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, kind, n, age = self.state(e)
        self.bank(g, t)
        q = ease_in_out(span(t, 0.1, 1.2))
        self.beast(g, kind, 1 - q, t)
        plate(g, kind, q * 20, t)
        self.diagram(g, kind, n, 99, q * 20, t)
        self.water(g, t)
        for j in range(2):
            ring(g, PX, WY, ((t * 20) + j * 12) % 30 + 6, (((t * 20) + j * 12) % 30 + 6) * 0.2)
        daoshi(g, DX, BANK, "gongshou", t)
        if t > 0.3:
            vlabel(g, "暂歇")
        nums = list(range(1, 11)) if kind == "he" else LO_ORDER
        self.mx(g, nums[max(n, 1) - 1], t)
        g.mx[: int(8 * q * 0.5), :] = False

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, kind, n, age = self.state(e)
        self.bank(g, t)
        q = 1 - ease_out_back(span(t, 0.1, 1.3))
        self.beast(g, kind, 1 - q, t)
        plate(g, kind, q * 20, t)
        self.diagram(g, kind, n, 99, q * 20, t)
        self.water(g, t)
        if 1.0 < t < 1.8:
            for j in range(3):
                y = PY + PH + 2 + ease_in(span(t, 1.0 + j * 0.15, 1.5 + j * 0.15)) * (WY - PY - PH - 2)
                if y < WY:
                    g.px(PX - 12 + j * 12, y), g.px(PX - 12 + j * 12, y + 1)
        daoshi(g, DX, BANK, "point" if t < 1.3 else "idle", t)
        nums = list(range(1, 11)) if kind == "he" else LO_ORDER
        if t > 1.0:
            vlabel(g, self.song(kind, nums[max(n, 1) - 1]))
        self.mx(g, nums[max(n, 1) - 1], t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        c, k, kind, n, age = self.state(e)
        if c >= 1 and k < RENEW:
            n = 1
        self.bank(g, t)
        self.beast(g, kind, 1.0, t, blink=2.0 < t < 2.15)
        flash = t > 2.6 and (t * 4) % 1 < 0.5
        plate(g, kind, 0, t, flash=flash)
        self.diagram(g, kind, max(n, 1), 99, 0, t, all_on=span(t, 0.2, 1.6) * 1.2)
        if t > 1.6:                                       # 连线
            q = span(t, 1.6, 2.6)
            if kind == "he":
                pairs = [(1, 6), (2, 7), (3, 8), (4, 9), (5, 10)]
                for a, b in pairs[: int(q * 5 + 0.99)]:
                    pa, pb = dots_of("he", a), dots_of("he", b)
                    ax, ay = sum(p[0] for p in pa) / len(pa), sum(p[1] for p in pa) / len(pa)
                    bx, by = sum(p[0] for p in pb) / len(pb), sum(p[1] for p in pb) / len(pb)
                    pix.dotted(g, ax, ay, bx, by, 2)
            else:
                lines = [((-1, -1), (1, 1)), ((1, -1), (-1, 1)), ((-1, 0), (1, 0)), ((0, -1), (0, 1))]
                for (c0, r0), (c1, r1) in lines[: int(q * 4 + 0.99)]:
                    pix.dotted(g, PX + c0 * CELL_W, PY + r0 * CELL_H, PX + c1 * CELL_W, PY + r1 * CELL_H, 2)
        self.water(g, t)
        if 2.6 <= t < 2.67:
            pix.flash(g)
        if 2.6 <= t < 2.6 + dt:
            self.sparks.burst(PX, PY, 30, 40, life=0.9, gravity=20)
        self.sparks.step(dt)
        self.sparks.draw(g)
        pose = "point" if t < 1.6 else ("kneel" if 2.4 < t < 4.6 else "gongshou")
        daoshi(g, DX, BANK, pose, t, face="happy" if t > 4.6 else "normal")
        if t > 3.0:
            pop = ease_out_back(span(t, 3.0, 3.4))
            if pop > 0.5:
                vlabel(g, "圣人则之")
                if int(t * 6) % 2 == 0:
                    sparkle(g, 8, 56, 0.5)
        if t > 2.6:
            mx_ring(g, (t - 2.6) * 4 % 6)
            g.mx_level = 1 + int(5 * (1 - span(t, 2.6, 4)))
        else:
            self.mx(g, 10 if kind == "he" else 9, t)
