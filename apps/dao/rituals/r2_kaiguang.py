"""开光点睛：小道士站在脚踏上，左手举宝镜把窗外的日光引到神像上，右手朱笔依次点开眼、耳、鼻、口、心。

依据：台南道教开光仪：道士“左手持镜向神像，右手持笔点朱”，镜先取太阳精气；咒文“神笔灵灵，太阳真精，
点开禁忌，五官齐明……左眼看万里，右眼看分明，左耳听远近，右耳知吉凶，鼻中七窍，孔相通”，又“开神口，
食天禄……开神心，神灵通”；神像开光前以红布覆盖。（浅野春二《台南道教の開光儀について》引大渊忍尔所录咒文）

舞台（侧视的小殿）：左上一扇棂花窗，日光（虚线）斜照进来；右边莲台上一尊正面坐像（冠、长耳、交领袍、拢手），
两种相轮换：老君相（长须）、灵官相（眉心竖目）。小道士站在脚踏上，左手宝镜、右手朱笔。左边竖幅写当句咒文，
右边竖牌“第几尊”。
入场：红布盖着神像；小道士走来跳上脚踏，伸手一扯，红布滑落（震一下、扬尘），举起宝镜，日光入镜。
持续：一轮 600 秒开一尊：先“神笔灵灵”镜光在冠顶游移；之后 7 处各 76 秒——镜光从上一处移到这一处，
      朱笔伸过去“点”（朱点迸光、震一下、点阵顶上一闪），这里就“活”了：眼睛睁开会眨、眼珠会转，耳边闪光，
      鼻翼，开口，胸前心光一明一暗。静候时镜面闪光、光里浮尘飘动、小道士点头、换手势。
      7 处开完“五官齐明”，神像每隔几秒放一圈光。续：红布从上落下盖住，再揭开是下一尊，“第几尊”加一。
中断：宝镜放下，镜光淡去，“暂歇”。恢复：宝镜举起，镜光重新照到当前部位。
圆满：朱笔飞快点完剩下的部位，神像反白一闪、光圈层层涌出，“五官齐明”“开光”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import (ARM_C, act, arm_spr, brush, floor, hold_brush, mx_ring, ring, star4, vbox)

FLOOR = 58
DAO_X = 71
STAND = FLOOR - 8                  # 脚踏面
SX = 98                            # 神像中线
WIN = (26, 4, 44, 18)              # 窗
SUN_IN = (40, 16)                  # 日光从窗里照进来的点
INTRO = 16.0
SLOT = 76.0
RENEW = 6.0

# 部位：(咒句, 目标点, 名)
PARTS = [
    ("左眼看万里", (94, 21), "eyeL"),
    ("右眼看分明", (102, 21), "eyeR"),
    ("左耳听远近", (88, 23), "earL"),
    ("右耳知吉凶", (108, 23), "earR"),
    ("鼻中七窍", (98, 24), "nose"),
    ("开神口", (98, 27), "mouth"),
    ("开神心", (98, 37), "heart"),
]
NP = len(PARTS)
DONE = INTRO + NP * SLOT
CROWN = (98, 10)


# ---------------------------------------------------------------- 道具

def _statue_base(kind: int):
    """神像（不含五官）34×50，左上角 (SX-17, 6)：莲花冠、长耳、脸、交领袍、拢手、莲台。kind 0 老君（长须）/ 1 灵官（竖目）"""
    p = Part(34, 50)
    c = 17
    # 莲台
    p.shape("rectangle", (3, 45, 30, 49), fill=1)
    p.d.line((4, 47, 29, 47), fill=0)
    for x in range(5, 29, 4):
        p.px(x, 46, 0), p.px(x + 2, 48, 0)
    for x in range(2, 31, 5):                                  # 莲瓣
        p.shape("chord", (x - 1, 40, x + 5, 48), 180, 360, fill=1)
        p.d.arc((x, 41, x + 4, 47), 200, 340, fill=0)
    # 袍身（坐像，金身：亮面 + 黑线衣褶，右侧背光网点）
    p.shape("polygon", [(c - 10, 25), (c + 10, 25), (c + 14, 42), (c - 14, 42)], fill=1)
    p.d.line((c - 6, 25, c, 32), fill=0)                       # 交领
    p.d.line((c + 6, 25, c, 32), fill=0)
    p.d.line((c - 9, 29, c - 12, 41), fill=0)                  # 袖褶
    p.d.line((c + 9, 29, c + 12, 41), fill=0)
    p.d.line((c - 6, 36, c - 8, 41), fill=0)
    p.d.line((c + 6, 36, c + 8, 41), fill=0)
    p.dither([(c + 10, 27), (c + 14, 42), (c + 9, 42)], 0.5, 0)
    p.d.rectangle((c - 4, 34, c + 4, 39), fill=0)              # 拢手（袖口相交）
    p.d.rectangle((c - 3, 35, c + 3, 38), fill=1)
    p.d.line((c, 35, c, 38), fill=0)
    p.d.line((c - 13, 41, c + 13, 41), fill=0)
    # 头
    p.shape("rectangle", (c - 2, 23, c + 2, 25), fill=1)       # 颈
    p.shape("ellipse", (c - 8, 7, c + 8, 24), fill=1)          # 脸
    for s in (-1, 1):                                          # 长耳
        x0 = c + s * 9
        p.shape("polygon", [(x0, 11), (x0 + s * 2, 12), (x0 + s * 2, 19), (x0 + s, 21), (x0, 19)], fill=1)
        p.px(x0 + s, 14, 0), p.px(x0 + s, 15, 0)
    # 冠
    p.shape("polygon", [(c - 6, 8), (c + 6, 8), (c + 5, 1), (c - 5, 1)], fill=1)
    p.d.line((c - 5, 6, c + 5, 6), fill=0)
    p.d.rectangle((c - 1, 2, c + 1, 4), fill=0)
    p.px(c, 3, 1)
    for s in (-1, 1):
        p.shape("polygon", [(c + s * 6, 6), (c + s * 9, 3), (c + s * 9, 6)], fill=1)    # 冠翅
    # 眉
    if kind == 0:
        p.d.line((c - 6, 13, c - 3, 12), fill=0)
        p.d.line((c + 3, 12, c + 6, 13), fill=0)
        p.d.line((c - 3, 21, c - 4, 23), fill=0)              # 唇须
        p.d.line((c + 3, 21, c + 4, 23), fill=0)
        p.shape("polygon", [(c - 3, 24), (c + 3, 24), (c + 1, 32), (c, 34), (c - 1, 32)], fill=1)   # 长须
        p.d.polygon([(c - 3, 24), (c + 3, 24), (c + 1, 32), (c, 34), (c - 1, 32)], outline=0)
        p.d.line((c, 26, c, 31), fill=0)
    else:
        p.d.line((c - 6, 12, c - 2, 14), fill=0)              # 怒眉
        p.d.line((c + 2, 14, c + 6, 12), fill=0)
        p.d.line((c - 4, 22, c - 1, 21), fill=0)              # 八字胡
        p.d.line((c + 1, 21, c + 4, 22), fill=0)
    return p.sprite()


def _cloth(w: int = 36, h: int = 46):
    """红布：顶上圆、往下垂出褶，布面网点（红色），几道亮褶线，下摆一圈流苏"""
    p = Part(w, h)
    p.shape("polygon", [(8, 2), (w - 9, 2), (w - 3, 10), (w - 1, h - 3), (0, h - 3), (2, 10)], fill=1)
    p.shape("ellipse", (6, 0, w - 7, 10), fill=1)
    p.dither((1, 3, w - 2, h - 4), 0.5, 0)
    for x in (8, 14, 21, 28):
        p.d.line((x, 8, x + (x - w / 2) * 0.2, h - 4), fill=1)
    for x in range(1, w - 1, 2):
        p.px(x, h - 2), p.px(x, h - 1) if x % 4 == 1 else None
    return p.sprite()


def _mirror():
    """宝镜 8×10：圆镜（亮边、暗镜面、一道斜高光）+ 镜柄"""
    p = Part(8, 10)
    p.shape("ellipse", (0, 0, 7, 7), fill=1)
    p.d.ellipse((1, 1, 6, 6), fill=0)
    p.d.line((2, 4, 4, 2), fill=1)
    p.px(5, 5, 1)
    p.shape("rectangle", (3, 8, 4, 9), fill=1)
    return p.sprite()


def _window():
    """棂花窗 19×15：外框 + 方格棂条"""
    p = Part(19, 15)
    p.shape("rectangle", (0, 0, 18, 14), fill=1)
    p.d.rectangle((2, 2, 16, 12), fill=0)
    for x in (6, 10, 14):
        p.d.line((x, 2, x, 12), fill=1)
    for y in (5, 9):
        p.d.line((2, y, 16, y), fill=1)
    return p.sprite()


def _stool():
    p = Part(22, 8)
    p.shape("rectangle", (0, 0, 21, 2), fill=1)
    p.d.line((1, 1, 20, 1), fill=0)
    for x in (2, 18):
        p.shape("rectangle", (x, 3, x + 1, 7), fill=1)
    p.shape("line", (3, 5, 18, 5), fill=1)
    return p.sprite()


_P: dict = {}


def prop(name):
    if name not in _P:
        _P[name] = {"s0": lambda: _statue_base(0), "s1": lambda: _statue_base(1), "cloth": _cloth,
                    "mirror": _mirror, "window": _window, "stool": _stool}[name]()
    return _P[name]


@register
class KaiGuang(Ritual):
    id = "r2.kaiguang"
    name = "开光点睛"
    desc = "小道士揭去红布，左手宝镜引日光照像，右手朱笔依次点开神像的眼、耳、鼻、口、心，五官齐明时神像放光"
    T = {"enter": 6.0, "interrupt": 1.5, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.last_t = None

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    # ------------------------------------------------------------ 状态

    def state(self, u: float):
        """→ (已点开几处, 当前处 or -1, 本处秒数, 镜光照的点)"""
        if u < INTRO:
            a = u * 0.9
            return 0, -1, u, (CROWN[0] + math.sin(a) * 5, CROWN[1] + math.cos(a * 1.3) * 2)
        i = int((u - INTRO) // SLOT)
        if i >= NP:
            return NP, -1, u - DONE, (SX, 22 + math.sin(u * 0.7) * 6)
        k = u - INTRO - i * SLOT
        prev = PARTS[i - 1][1] if i else CROWN
        q = ease_in_out(span(k, 0, 3.0))
        tgt = PARTS[i][1]
        aim = (lerp(prev[0], tgt[0], q), lerp(prev[1], tgt[1], q))
        if k > 8:
            aim = (tgt[0] + math.sin(k * 0.8) * 1.5, tgt[1] + math.cos(k * 1.1) * 1.0)
        return i + (1 if k >= 4.6 else 0), i, k, aim

    # ------------------------------------------------------------ 画面零件

    def room(self, g: Gfx, t: float):
        floor(g, FLOOR)
        g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)        # 踢脚
        pix.blit(g, prop("window"), WIN[0], WIN[1])
        for x in (19, 121):                                      # 柱
            g.d.line((x, 0, x, FLOOR - 4), fill=1)
        pix.blit(g, prop("stool"), DAO_X - 10, STAND)

    def statue(self, g: Gfx, t: float, kind: int, opened: set, glow: float = 0.0):
        pix.blit(g, prop("s1" if kind else "s0"), SX - 17, 6)
        c, y0 = SX, 6
        look = int(math.sin(t * 0.37) * 1.4) if int(t) % 9 < 3 else 0
        blink = (t % 4.3) < 0.15
        for name, ex in (("eyeL", c - 4), ("eyeR", c + 4)):
            if name in opened and not blink:
                g.d.rectangle((ex - 2, y0 + 14, ex + 1, y0 + 16), fill=0)
                g.px(ex - 1 + look + (1 if look < 0 else 0), y0 + 15, 1)
            else:
                g.d.line((ex - 2, y0 + 15, ex + 1, y0 + 15), fill=0)
                g.px(ex - 2, y0 + 14, 0) if name in opened else None
        if kind == 1:  # 灵官眉心竖目：眼睛点开时一起睁
            if "eyeL" in opened and not blink:
                g.d.rectangle((c - 1, y0 + 9, c + 1, y0 + 12), fill=0)
                g.px(c, y0 + 10, 1)
            else:
                g.d.line((c, y0 + 9, c, y0 + 12), fill=0)
        g.d.line((c, y0 + 16, c, y0 + 18), fill=0)                       # 鼻梁
        if "nose" in opened:
            g.px(c - 1, y0 + 18, 0), g.px(c + 1, y0 + 18, 0)
            g.px(c - 2, y0 + 17, 0), g.px(c + 2, y0 + 17, 0)
        if "mouth" in opened:
            talk = (t % 2.6) < 0.3
            g.d.rectangle((c - 2, y0 + 20, c + 2, y0 + 21 + talk), fill=0)
            g.d.line((c - 1, y0 + 20, c + 1, y0 + 20), fill=1)
        else:
            g.d.line((c - 2, y0 + 21, c + 2, y0 + 21), fill=0)
        for name, ex, s in (("earL", c - 10, -1), ("earR", c + 10, 1)):
            if name in opened and (t * 0.7 + (s > 0) * 0.5) % 3 < 0.25:
                for j in range(3):
                    g.px(ex + s * (3 + j), y0 + 15 - j * 2)
        if "heart" in opened:
            on = (t % 2.0) < 1.2
            g.d.ellipse((c - 3, y0 + 28, c + 3, y0 + 34), fill=0)
            g.d.ellipse((c - 2, y0 + 29, c + 2, y0 + 33), outline=1, fill=1 if on else 0)
            if on:
                g.px(c, y0 + 31, 0)
        if glow > 0:
            for i in range(10):
                a = i * math.pi / 5 + t * 0.4
                r0 = 22
                r1 = r0 + 2 + 3 * glow * (0.5 + 0.5 * math.sin(t * 4 + i))
                x0, y_0 = c + math.cos(a) * r0 * 0.8, 28 + math.sin(a) * r0
                if x0 > DAO_X + 10:
                    g.d.line((x0, y_0, c + math.cos(a) * r1 * 0.8, 28 + math.sin(a) * r1), fill=1)

    def cloth(self, g: Gfx, k: float = 0.0, down: float = 1.0):
        """红布：k = 往右滑落的进度；down = 从上面落下盖住的进度"""
        spr = prop("cloth")
        x = SX - 18 + ease_in(k) * 40
        y = 4 + ease_in(k) * 20 - (1 - down) * 52
        if k > 0.5:
            spr = pix.stretch(spr, 1.0, max(0.3, 1.5 - k))
            y = FLOOR - spr.h + 1 if k >= 0.99 else y
        pix.blit(g, spr, x, y)

    def dao(self, g: Gfx, t: float, aim, tip=None, mirror: float = 1.0, x: float = DAO_X, face="normal", head="up"):
        """小道士：后手把宝镜举过头顶（mirror 0..1 举起的程度）、前手朱笔（tip 有就伸过去点，否则平端着）。返回镜心"""
        mang = lerp(0.5, -1.45, mirror)
        marm = arm_spr(mang, lerp(10, 15, mirror))
        mh = {}

        def behind(gg, at):
            at(-2 - ARM_C, -15 - ARM_C, marm)
            mh["p"] = (x - 2 - ARM_C + marm.hand[0], STAND - 15 - ARM_C + marm.hand[1])

        if tip is not None:
            hand = (min(tip[0] - 9, x + 14), max(tip[1] + 6, STAND - 30))
            h = act(g, x, STAND, t, hand_to=hand, face=face, head=head, behind=behind)["hand"]
            hold_brush(g, h, tip, past=2)
        else:
            h = act(g, x, STAND, t, hand_to=(x + 9, STAND - 11), face=face, head=head, behind=behind)["hand"]
            hold_brush(g, h, (h[0] + 6, h[1] - 3), past=4)
        mx_, my = mh["p"]
        spr = prop("mirror")
        pix.blit(g, spr, mx_ - 3, my - 9)
        return mx_ + 0.5, my - 5.5

    def beams(self, g: Gfx, t: float, mc, aim, k: float = 1.0):
        """日光：窗 → 镜（虚线）→ 照到的部位（虚线 + 光斑），光里浮尘"""
        if k <= 0:
            return
        ph = int(t * 10)
        pix.dotted(g, SUN_IN[0], SUN_IN[1], mc[0], mc[1], step=3, phase=ph)
        ex, ey = lerp(mc[0], aim[0], k), lerp(mc[1], aim[1], k)
        pix.dotted(g, mc[0], mc[1], ex, ey, step=2, phase=ph)
        if k >= 1:
            star4(g, aim[0], aim[1], big=int(t * 5) % 2 == 0)
        for j in range(3):  # 浮尘
            q = (t * 0.15 + j * 0.33) % 1
            g.px(lerp(SUN_IN[0], mc[0], q) + math.sin(t + j) * 2, lerp(SUN_IN[1], mc[1], q) + 2)

    def opened_set(self, n: int):
        return {PARTS[j][2] for j in range(min(n, NP))}

    def variant(self, e: float) -> int:
        return int(e // self.CYCLE) % 2

    def label(self, g: Gfx, s: str):
        vbox(g, 7, 22, s)

    def counter(self, g: Gfx, e: float, s: str | None = None):
        n = int(e // self.CYCLE) + 1
        vbox(g, 122, 10, s or ("第" + (cn_num(n) if n < 100 else str(n)) + "尊"))

    def mx(self, g: Gfx, t: float, opened: set, flash: bool = False):
        blink = (t % 4.3) < 0.15
        for name, x0 in (("eyeL", 1), ("eyeR", 5)):
            if name in opened and not blink:
                g.mx[2:4, x0:x0 + 2] = True
            else:
                g.mx[3, x0:x0 + 2] = True
        if "mouth" in opened:
            g.mx[6, 3:5] = True
        if "nose" in opened:
            g.mx[4, 3] = g.mx[4, 4] = True
        if flash:
            g.mx[0, 3:5] = True
            g.mx_level = 6

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        self.room(g, t)
        self.statue(g, t, 0, set())
        pull = span(t, 2.9, 3.9)
        self.cloth(g, pull)
        if 3.9 <= t < 3.9 + dt:
            pix.shake(g, t, 1.2)
            for j in range(4):
                self.puffs.emit(SX + 6 + j * 6, FLOOR - 2, vx=8, vy=-4, life=0.8, rmax=1.8)
        if t < 2.0:
            daoshi(g, lerp(-12, DAO_X - 16, ease_out(span(t, 0, 2.0))), FLOOR, "walk", t)
        elif t < 2.5:
            q = span(t, 2.0, 2.5)
            daoshi(g, lerp(DAO_X - 16, DAO_X, q), lerp(FLOOR, STAND, q) - math.sin(q * math.pi) * 7, "raise", t)
        elif t < 3.9:  # 伸手扯红布
            q = span(t, 2.5, 2.9)
            reach = (lerp(DAO_X + 8, SX - 14, q), lerp(STAND - 14, 20, q)) if t < 2.9 else \
                (lerp(SX - 14, DAO_X + 12, ease_out(span(t, 2.9, 3.3))), lerp(20, STAND - 12, span(t, 2.9, 3.3)))
            act(g, DAO_X, STAND, t, hand_to=reach, face="wow" if t > 3.0 else "normal")
        else:
            m = ease_out_back(span(t, 4.2, 5.0))
            mc = self.dao(g, t, CROWN, None, mirror=m)
            self.beams(g, t, mc, CROWN, k=span(t, 5.0, 5.8))
        self.puffs.step(dt)
        self.puffs.draw(g)
        if t > 5.0:
            self.label(g, "神笔灵灵")
        self.counter(g, 0.0)
        self.mx(g, t, set())

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            return self.renew(g, t, e, u, dt)
        kind = self.variant(e)
        n, i, k, aim = self.state(u)
        opened = self.opened_set(n)
        self.room(g, t)
        glow = 1.0 if n >= NP else 0.0
        self.statue(g, t, kind, opened, glow=glow)
        tip = None
        face = "normal"
        if i >= 0:
            tgt = PARTS[i][1]
            if 3.0 <= k < 4.6:  # 朱笔伸过去
                q = ease_in_out(span(k, 3.0, 4.2))
                tip = (lerp(DAO_X + 11, tgt[0], q), lerp(STAND - 21, tgt[1], q))
                if k > 4.2:
                    tip = (tgt[0] - (1 if k > 4.5 else 0), tgt[1])
            elif 4.6 <= k < 5.4:  # 点！收笔
                tip = (lerp(tgt[0], DAO_X + 11, ease_in(span(k, 4.8, 5.4))), lerp(tgt[1], STAND - 21, span(k, 4.8, 5.4)))
            if 4.6 <= k < 4.6 + dt:
                self.sparks.burst(tgt[0], tgt[1], 12, 26, life=0.5, gravity=30)
                pix.shake(g, t, 0.8)
            if 4.6 <= k < 5.0:
                ring(g, tgt[0], tgt[1], (k - 4.6) * 18, step=2)
            face = "happy" if 5.4 < k < 7.0 else ("wow" if 4.6 <= k < 5.0 else "normal")
        head = "bow" if i >= 0 and 30.0 < k < 31.4 else "up"
        mirror = 1.0 - (0.25 if i >= 0 and 50 < k < 52 else 0.0) * math.sin(span(k, 50, 52) * math.pi)
        mc = self.dao(g, t, aim, tip, mirror=mirror, face=face, head=head)
        self.beams(g, t, mc, aim)
        if int(t * 10) % 37 == 0:  # 镜面闪光
            star4(g, mc[0] - 2, mc[1] - 2, big=True)
        if n >= NP:
            r = ((u - DONE) % 6.0) * 10
            if r < 34:
                ring(g, SX, 28, 20 + r, step=3, sy=1.0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if i >= 0:
            self.label(g, PARTS[i][0])
        else:
            self.label(g, "五官齐明" if n >= NP else "神笔灵灵")
        self.counter(g, e)
        self.mx(g, t, opened, flash=i >= 0 and 4.6 <= k < 5.0)

    def renew(self, g: Gfx, t: float, e: float, u: float, dt: float):
        """续：红布落下盖住这一尊 → 揭开是下一尊"""
        self.room(g, t)
        swapped = u >= 2.2
        kind = self.variant(e if swapped else e - u - 1)
        self.statue(g, t, kind, self.opened_set(NP) if not swapped else set())
        if u < 3.0:
            self.cloth(g, 0.0, down=ease_out(span(u, 0.4, 1.4)))
        else:
            self.cloth(g, span(u, 3.0, 4.0))
        if 1.4 <= u < 1.4 + dt or 4.0 <= u < 4.0 + dt:
            pix.shake(g, t, 1.0)
            self.puffs.emit(SX, FLOOR - 3, vy=-3, life=0.8, rmax=2)
        if 2.4 < u < 3.0:
            act(g, DAO_X, STAND, t, hand_to=(SX - 14, 22))
        elif u < 4.4:
            mc = self.dao(g, t, CROWN, None, mirror=1 - span(u, 0, 0.5) if u < 2.4 else span(u, 3.4, 4.0))
        else:
            mc = self.dao(g, t, CROWN, None, mirror=1.0, head="bow" if u < 5.4 else "up")
            self.beams(g, t, mc, CROWN, k=span(u, 4.4, 5.0))
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.label(g, "神笔灵灵")
        self.counter(g, e if swapped else e - u - 1)
        self.mx(g, t, set() if swapped else self.opened_set(NP))

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        n, i, k, aim = self.state(u)
        opened = self.opened_set(n)
        self.room(g, t)
        self.statue(g, t, self.variant(e), opened)
        m = 1 - ease_in_out(span(t, 0.2, 1.0))
        mc = self.dao(g, t, aim, None, mirror=m, face="sleep" if t > 1.1 else "normal")
        self.beams(g, t, mc, aim, k=1 - span(t, 0.0, 0.5))
        self.label(g, "暂歇")
        self.counter(g, e)
        self.mx(g, t, opened)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        n, i, k, aim = self.state(u)
        opened = self.opened_set(n)
        self.room(g, t)
        self.statue(g, t, self.variant(e), opened)
        m = ease_out_back(span(t, 0.2, 0.9))
        mc = self.dao(g, t, aim, None, mirror=m, face="wow" if t < 0.4 else "normal")
        self.beams(g, t, mc, aim, k=span(t, 0.9, 1.6))
        if 0.9 <= t < 0.9 + dt:
            star4(g, mc[0], mc[1], big=True)
        if i >= 0:
            self.label(g, PARTS[i][0])
        else:
            self.label(g, "五官齐明" if n >= NP else "神笔灵灵")
        self.counter(g, e)
        self.mx(g, t, opened)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        n0 = self.state(u)[0]
        fast = n0 + span(t, 0.0, 2.0) * (NP - n0)
        n = int(fast)
        opened = self.opened_set(n)
        self.room(g, t)
        self.statue(g, t, self.variant(e), opened, glow=1.0 if t > 2.2 else 0.0)
        tip = None
        aim = CROWN
        if n < NP:
            tgt = PARTS[n][1]
            q = fast - n
            tip = (lerp(DAO_X + 12, tgt[0], min(q * 2, 1)), lerp(STAND - 20, tgt[1], min(q * 2, 1)))
            aim = tgt
            if int(fast * 30) != int((fast - dt * (NP - n0) / 2.0) * 30) and q > 0.5 and int(t * 30) % 3 == 0:
                self.sparks.burst(tgt[0], tgt[1], 3, 18, life=0.3)
        mc = self.dao(g, t, aim, tip, face="happy" if t > 2.4 else "normal",
                      head="bow" if 3.2 < t < 4.4 else "up")
        self.beams(g, t, mc, aim if t < 2.2 else (SX, 20))
        if 2.2 <= t < 2.2 + dt:
            pix.flash(g)
            self.sparks.burst(SX, 24, 30, 46, up=10, life=1.0, gravity=30)
        if 2.2 < t < 2.5:
            pix.shake(g, t, 1.4)
        for r in range(3):
            rr = (t - 2.2) * 24 - r * 10
            if 0 < rr < 40:
                ring(g, SX, 28, 18 + rr, step=2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.label(g, "五官齐明" if t > 2.2 else (PARTS[min(n, NP - 1)][0]))
        self.counter(g, e, "开光" if t > 2.2 else None)
        self.mx(g, t, opened, flash=t < 2.2 and int(t * 10) % 3 == 0)
        if t > 2.2:
            mx_ring(g, (t - 2.2) * 4)
            g.mx_level = 1 + int(6 * (1 - span(t, 2.2, 3.6)))
