"""六字诀：小道士站在山崖上对着云海吐纳，一口气一个字：嘘、呵、呼、呬、吹、嘻。

依据：陶弘景《养性延命录·服气疗病》“纳气有一，吐气有六。纳气一者谓吸也，吐气六者谓吹、呼、唏、呵、嘘、呬，皆出气也”；
后世六字诀配脏腑：嘘肝、呵心、呼脾、呬肺、吹肾、嘻三焦（按健身气功六字诀的顺序与动作）。《庄子·刻意》“吹呴呼吸，吐故纳新”。
入场：云海翻涌，小道士走上崖头，两手从体侧合到丹田，“吐纳”。
持续：一口气 10 秒：鼻吸 4 秒（两手捧到胸前，清气从四面聚进鼻中，丹田一圈光）→ 口呼 6 秒（按字做动作：
      嘘穿掌、呵捧掌下按、呼两臂外撑、呬立掌前推、吹两臂环抱下落、嘻两手上分；口型随字变，三道气浪吐出，
      放大的字骑在气头上飘向云海，“噗”地散开）。每字 100 秒，一遍六字 10 分钟。云海里不时飞过一只鹤。
      续：拱手一揖，上方“第几遍”。
中断：闭口，残气散尽，“闭息”。  恢复：深吸一口（清气聚入），接回当前这一口气。
圆满：吸满后一口长气，六个字连珠吐出，云海翻开一道光，“吐故纳新”。
点阵：方框随吸气由中心扩到满屏、呼气收回，呼气时几个点从中间飞向右边。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import P, Clock, cached, counter, dao, label, mix, pop_title, ring, seq, star

FLOOR = 56
DX = 34
BREATH = 10.0
INHALE = 4.0
SEG = 100.0
CHARS = "嘘呵呼呬吹嘻"
ORGAN = "肝心脾肺肾焦"
MOUTH = {"嘘": "flat", "呵": "open", "呼": "o", "呬": "flat", "吹": "o", "嘻": "smile"}

HOLD_DT = P(b=(120, 20, "palm"), f=(60, 160, "palm"))
CHEST = P(b=(130, -40, "palm"), f=(50, -140, "palm"), face="sleep")
EXHALE = {
    "嘘": P(legs="wide", b=(120, 0, "palm"), f=(0, -5, "palm"), face="wow"),
    "呵": P(legs="wide", b=(150, 160, "down"), f=(30, 20, "down")),
    "呼": P(legs="wide", b=(165, 130, "palm"), f=(15, 50, "palm")),
    "呬": P(legs="wide", b=(20, 10, "up"), f=(0, 0, "up")),
    "吹": P(legs="horse", b=(140, 150, "palm"), f=(40, 30, "palm")),
    "嘻": P(legs="wide", b=(-150, -160, "palm"), f=(-30, -20, "palm"), face="happy"),
}


def _crag():
    """崖头 74×12：岩面、裂纹、崖边垂下的石棱，右端一丛小松"""
    p = Part(74, 14)
    p.shape("polygon", [(0, 0), (64, 0), (70, 3), (73, 8), (68, 13), (0, 13)], fill=1)
    p.d.line((0, 1, 64, 1), fill=0)
    for x, y, w in ((8, 4, 7), (26, 6, 9), (44, 3, 6), (56, 8, 6), (14, 9, 5)):
        p.d.line((x, y, x + w, y), fill=0)
        p.px(x + w + 1, y + 1, 0)
    p.d.line((66, 4, 69, 9), fill=0)
    p.dither([(60, 2), (73, 8), (68, 13), (58, 13)], 0.5, 0)
    return p.sprite()


MOUNTS = {
    1: (46, 26, [(0, 25), (6, 18), (9, 19), (15, 10), (18, 11), (23, 0), (27, 6), (30, 5), (35, 13), (38, 12), (45, 25)],
        [(23, 0), (27, 6), (30, 5), (35, 13), (38, 12), (45, 25), (29, 25), (25, 12)],
        [((14, 13), (17, 16)), ((8, 20), (11, 22)), ((20, 5), (21, 9)), ((18, 15), (20, 19))]),
    2: (30, 18, [(0, 17), (5, 11), (8, 12), (13, 3), (15, 0), (19, 6), (22, 5), (29, 17)],
        [(15, 0), (19, 6), (22, 5), (29, 17), (18, 17), (16, 8)], [((10, 8), (12, 11)), ((5, 14), (7, 16))]),
    3: (23, 13, [(0, 12), (6, 6), (9, 7), (12, 0), (16, 5), (22, 12)],
        [(12, 0), (16, 5), (22, 12), (14, 12), (13, 5)], [((7, 8), (9, 10))]),
}


def _peak(n):
    """远峰：逐顶点勾的山脊，阳面亮、阴面网点，阳面几道岩缝"""
    w, h, outline, shade, cracks = MOUNTS[n]
    p = Part(w, h)
    p.shape("polygon", outline, fill=1)
    p.dither(shade, 0.5, 0)
    for a, b in cracks:
        p.d.line(a + b, fill=0)
    return p.sprite()


CLOUD = pix.frames("""
    ####
  ########  ##
 ##############
################
 #.#.#.#.#.#.##
""")

CRANE_FLY = pix.frames("""
##       ##
 ##     ##
  ###.####.###
     ####
---
     ####
  #########.###
 ##   #
##
""")


def valley(g: Gfx, t: float, e: float):
    """云海与远峰（崖下）"""
    pix.blit(g, cached(("lz", "peak", 3), lambda: _peak(3)), 62, 34)
    pix.blit(g, cached(("lz", "peak", 1), lambda: _peak(1)), 74, 22)
    pix.blit(g, cached(("lz", "peak", 2), lambda: _peak(2)), 102, 30)
    # 云海：两层云带横向漂（只在崖外）
    for j, (y, sp) in enumerate(((43, 2.0), (49, 3.2))):
        off = (t * sp + j * 23) % 40
        for x in range(-40, 140, 40):
            if x + off > 50:
                pix.blit(g, CLOUD[0], x + off, y)
    g.d.rectangle((0, 55, 127, 63), fill=0)
    pix.checker(g, (60, 56, 128, 64), 0.25)
    # 鹤飞过（按 e）
    ph = (e % 31) / 9.0
    if ph < 1:
        pix.blit(g, pix.anim(CRANE_FLY, t, 3), lerp(134, 50, ph), 20 + math.sin(ph * 5) * 3, flip=True)


def crag(g: Gfx):
    pix.blit(g, cached(("lz", "crag"), _crag), -2, FLOOR)


@register
class Liuzi(Ritual):
    id = "r4.liuzi"
    name = "六字诀"
    desc = "小道士站在山崖上对着云海吐纳，鼻吸清气，口呼一字：嘘呵呼呬吹嘻，放大的字骑着气浪飘向云海"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 2.2, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()

    def breath(self, k: float):
        """一遍里第 k 秒 → (第几字, 本口气第几秒)"""
        i = min(int(k // SEG), 5)
        b = (k - i * SEG) % BREATH
        return i, b

    def pose(self, i: int, b: float):
        ch = CHARS[i]
        ex = EXHALE[ch]
        if b < INHALE:
            q = ease_in_out(b / INHALE)
            p = mix(HOLD_DT, CHEST, q) if b < INHALE * 0.9 else CHEST
        else:
            q = ease_in_out(span(b, INHALE, INHALE + 2.0))
            back = ease_in_out(span(b, BREATH - 1.2, BREATH))
            p = mix(mix(CHEST, ex, q), HOLD_DT, back)
            if b < BREATH - 1.0:
                p["mouth"] = MOUTH[ch]
                if p["face"] == "sleep":
                    p["face"] = "normal"
        return p

    def inhale_fx(self, g: Gfx, t: float, h: dict, k: float):
        """清气从四面聚进鼻中（k ∈ [0,1]）"""
        nx, ny = h["nose"]
        for j in range(7):
            a = j * 0.9 + 0.4
            q = (k * 2 + j * 0.13) % 1
            r = (1 - q) * 26 + 2
            x, y = nx + math.cos(a) * r, ny + math.sin(a) * r * 0.7
            g.px(x, y)
            if q < 0.6:
                g.px(x + math.cos(a), y + math.sin(a) * 0.7)
        if 0.6 < k:  # 丹田一圈光
            r = (k - 0.6) / 0.4 * 7
            ring(g, DX + 1, FLOOR - 9, r + 1, dotted=2, ry=(r + 1) * 0.5)

    def exhale_fx(self, g: Gfx, t: float, h: dict, k: float, ch: str):
        """三道气浪 + 骑在气头上的大字（k ∈ [0,1]）。字最后画（返回字的位置）"""
        mx_, my = h["mouth"]
        for j in range(3):
            q = k * 1.4 - j * 0.18
            if 0 < q < 1:
                r = 4 + q * 30
                cx = mx_ + q * 20
                g.d.arc((cx - r * 0.3, my - r * 0.5, cx + r * 0.3, my + r * 0.5), -50, 50, fill=1)
        return None

    def draw(self, g: Gfx, t: float, e: float, dt: float, k: float, word: bool = True):
        i, b = self.breath(k)
        ch = CHARS[i]
        p = self.pose(i, b)
        h = dao(g, DX, FLOOR, p, t)
        word_at = None
        if b < INHALE:
            self.inhale_fx(g, t, h, b / INHALE)
        else:
            q = (b - INHALE) / (BREATH - INHALE)
            self.exhale_fx(g, t, h, q, ch)
            if word and q < 0.92:
                x = lerp(h["mouth"][0] + 22, 100, ease_out(q / 0.92))
                y = lerp(h["mouth"][1] - 22, 6, ease_out(q / 0.92)) + math.sin(q * 9) * 2
                word_at = (x, y)
            if word and abs(q - 0.92) < dt / (BREATH - INHALE):  # 字散开
                for j in range(5):
                    self.puffs.emit(100 + (j - 2) * 4, 17, vx=(j - 2) * 5, vy=-3, life=0.9, rmax=2.4)
                self.sparks.burst(100, 17, 10, 18, life=0.6, gravity=0)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        return i, b, word_at

    def mx(self, g: Gfx, t: float, b: float):
        if b < INHALE:
            r = ease_out(b / INHALE) * 3.5
        else:
            r = (1 - ease_in(span(b, INHALE, BREATH))) * 3.5
            for j in range(2):
                x = int(((b - INHALE) * 4 + j * 2) % 4) + 4
                g.mx[3 + j, x] = True
        r0 = int(round(r))
        lo, hi = max(3 - r0, 0), min(4 + r0, 7)
        for x in range(lo, hi + 1):
            g.mx[lo, x] = g.mx[hi, x] = True
        for y in range(lo, hi + 1):
            g.mx[y, lo] = g.mx[y, hi] = True

    def texts(self, g: Gfx, e: float, i: int, b: float, word_at, k_in_seg: float):
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")
        if word_at:
            label(g, word_at[0], word_at[1], CHARS[i], 12, "center", box=False, pad=1, scale=2)
        elif k_in_seg < INHALE:
            label(g, 72, 3, f"{CHARS[i]}字诀", 12, "center", box=True)
        elif b < INHALE:
            counter(g, f"{CHARS[i]}·{ORGAN[i]}", right=True)

    # ------------------------------------------------------------ 阶段

    def scene(self, g, t, e):
        valley(g, t, e)
        crag(g)

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        self.scene(g, t, 0)
        if t < 2.4:
            daoshi(g, lerp(-12, DX, ease_out(span(t, 0, 2.4))), FLOOR, "walk", t)
        else:
            dao(g, DX, FLOOR, mix(P(), HOLD_DT, ease_in_out(span(t, 2.4, 4.0))), t)
        if 3.0 < t:
            ring(g, DX + 1, FLOOR - 9, 1 + (t - 3.0) * 6 % 8, dotted=2, ry=(1 + (t - 3.0) * 6 % 8) * 0.5)
        self.mx(g, t, 0.0)
        if t > 3.0:
            pop_title(g, 72, 3, "吐纳", span(t, 3.0, 3.4), t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        self.scene(g, t, e)
        if e >= self.CYCLE and k < 5.0:  # 续：拱手一揖
            from ..engine.chars import daoshi as ds
            ds(g, DX, FLOOR, "gongshou" if k < 1.5 or k > 3.5 else "bow", t)
            self.mx(g, t, 0.0)
            n = int(e // self.CYCLE) + 1
            pop_title(g, 72, 3, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍", span(k, 0.3, 0.7), t)
            return
        i, b, word_at = self.draw(g, t, e, dt, k)
        self.mx(g, t, b)
        self.texts(g, e, i, b, word_at, k - i * SEG)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        self.scene(g, t, e)
        i, b = self.breath(k)
        q = ease_out(span(t, 0, 1.0))
        p = mix(self.pose(i, b), HOLD_DT, q)
        p["mouth"] = None
        if t > 0.4:
            p["face"] = "sleep"
        h = dao(g, DX, FLOOR, p, t)
        if t < 0.3:
            self.puffs.emit(h["mouth"][0] + 3, h["mouth"][1], vx=8, vy=-2, life=0.8, rmax=2)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.mx(g, t, b * (1 - q))
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")
        if t > 0.5:
            label(g, 72, 3, "闭息", 12, "center", box=True)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        self.scene(g, t, e)
        i, b = self.breath(k)
        if t < 1.4:
            h = dao(g, DX, FLOOR, mix(HOLD_DT, CHEST, ease_in_out(t / 1.4)), t)
            self.inhale_fx(g, t, h, t / 1.4)
        else:
            q = ease_in_out(span(t, 1.4, 2.2))
            dao(g, DX, FLOOR, mix(CHEST, self.pose(i, b), q), t)
        self.mx(g, t, min(t / 1.4, 1) * INHALE * 0.99)
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}遍" if n < 100 else f"{n}遍")

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        self.scene(g, t, e)
        if t < 1.5:  # 吸满
            h = dao(g, DX, FLOOR, mix(HOLD_DT, CHEST, ease_in_out(t / 1.5)), t)
            self.inhale_fx(g, t, h, t / 1.5)
            word = None
        else:
            q = ease_in_out(span(t, 1.5, 2.3))
            p = mix(CHEST, P(legs="wide", b=(170, 175, "palm"), f=(10, 5, "palm")), q)
            p["mouth"] = "open" if t < 4.2 else None
            if t > 4.2:
                p["face"] = "happy"
            h = dao(g, DX, FLOOR, p, t)
            word = None
            if t < 4.4:
                self.exhale_fx(g, t, h, ((t - 1.5) / 1.2) % 1, "")
                j = int((t - 1.5) / 0.45)
                if j < 6:  # 六字连珠：每个字飞 0.45 秒，前一个字散开后下一个才出来
                    q2 = ((t - 1.5) % 0.45) / 0.45
                    word = (CHARS[j], lerp(h["mouth"][0] + 10, 110, q2), lerp(h["mouth"][1] - 12, 12, q2))
                    if q2 > 0.9 and int((t - dt - 1.5) / 0.45) == j and ((t - dt - 1.5) % 0.45) / 0.45 <= 0.9:
                        self.sparks.burst(110, 18, 8, 16, life=0.5, gravity=0)
        if t > 4.2:  # 云海翻开一道光
            k = span(t, 4.2, 5.0)
            for j in range(5):
                x = 92 + (j - 2) * 6 * k
                pix.dotted(g, 92, 30, x, 54, 2, int(t * 10))
        if abs(t - 4.2) < dt:
            pix.flash(g)
            self.sparks.burst(92, 34, 24, 34, up=10, life=1.0, gravity=20)
        if 4.2 < t < 4.5:
            pix.shake(g, t, 1.2)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, (t / 1.5) * INHALE if t < 1.5 else INHALE + (t - 1.5) / 3 * 6)
        if t > 4.2:
            g.mx[:] = False
            from .r4_kit import mx_ring
            mx_ring(g, (t - 4.2) * 4 % 5)
            g.mx_level = 1 + int(6 * (1 - span(t, 4.2, 5.5)))
        if word:
            label(g, word[1], word[2], word[0], 12, "center", box=False, pad=1)
        if t > 4.4:
            pop_title(g, 72, 3, "吐故纳新", span(t, 4.4, 4.8), t)
