"""金光神咒：小道士盘坐蒲团持诵《金光神咒》，每念一句换一个手诀，身后金光一层层长出来。

依据：道教八大神咒之一《金光神咒》（正一日诵早晚课本）：“天地玄宗，万炁本根。广修亿劫，证吾神通……
金光速现，覆护真人。”（《太上三洞神咒》卷一作“万气之根”“惟吾独尊”）。12px 字库无“炁”，手绘像素字；
“五炁腾腾”按通行异文作“五气腾腾”。

舞台（侧视静室）：地砖、护墙线，小道士盘坐蒲团（左），右边地上一只小香炉一炷香；右上一块咒牌逐字写出当前一句，
左上“第几遍”。
入场：小道士走来、一屁股坐上蒲团（扬起两小团尘），拱手闭目，胸前一点灵光亮起。
持续：一遍 574 秒（开头 3 秒起咒 + 26 句 × 21 秒 + “急急如律令”25 秒）。每句开头换一个手诀（拱手 / 剑指向天 /
      剑指向前 / 托掌 / 胸前掐诀），手上一闪；字一个个写出时嘴一张一合；句中点头、睁眼看一眼再闭上；
      光点从金光边缘飘出。金光随句数长：光芒由 6 道到 24 道、由短变长、虚线向外流动，三分之一出头光，过半出身光。
      特定句：“役使雷霆”剑指向天，一道闪电劈下；“鬼妖丧胆”“精怪亡形”右边飘来一只小鬼，剑指一道金光射去，
      小鬼发抖、炸成火星；“内有霹雳”近处霹雳、震屏；“雷神隐名”远处闷雷闪；“金光速现”闪白、光环冲出。
      续：金光收回身中一闪，“第几遍”加一，从头再念。
中断：金光一道道缩回，咒牌换成“暂歇”，小道士低头。恢复：一睁眼（惊），金光重新长到当前的亮度。
圆满：举手向天，金光暴涨、闪白，光环一圈圈涌出把全身罩住，“金光速现”“覆护真人”。
点阵：太阳，光芒长度随金光等级、转动；“金光速现”与圆满时爆开。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.cn import cn_num
from ..engine.fx import lightning
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r2_common import act, boxed, cushion_spr, floor, ring, star4, table_spr

FLOOR = 58
DX = 38                  # 小道士
SIT_Y = FLOOR - 2        # 盘坐时的“脚底”
CY = SIT_Y - 22          # 金光中心（胸口偏上）
HEAD = (DX, SIT_Y - 25)  # 头中心
CENSER_X = 90
TOP = FLOOR - 12        # 供案面
LEAD = 3.0
SLOT = 21.0
PHRASES = ["天地玄宗", "万炁本根", "广修亿劫", "证吾神通", "三界内外", "惟道独尊", "体有金光", "覆映吾身",
           "视之不见", "听之不闻", "包罗天地", "养育群生", "受持万遍", "身有光明", "三界侍卫", "五帝司迎",
           "万神朝礼", "役使雷霆", "鬼妖丧胆", "精怪亡形", "内有霹雳", "雷神隐名", "洞慧交彻", "五气腾腾",
           "金光速现", "覆护真人"]
LAST = "急急如律令"
NP = len(PHRASES)
LAST_AT = LEAD + NP * SLOT
CPS = 0.55               # 每字秒数
BOLT = {17: "near", 20: "big", 21: "far"}
GHOST = {18: 0, 19: 1}
BURST = 24               # 金光速现
MUDRA = ["gong", "up", "fwd", "palm", "chest"]

# 12px 字库没有“炁”（上“无”下“灬”）：手绘一个 12×11 的像素字
QI = Sprite("""
 #########

###########
    # #
   #  #
  #   #   #
##    #####

 # #  #  #
#   #  #  #
""")


# ---------------------------------------------------------------- 小道士：盘坐 + 手诀（与 r2_jingxin 共用）

def fingers(g: Gfx, hand, ang: float, n: int = 3):
    """剑指：食中二指并拢伸出 n 像素（先描黑边）"""
    hx, hy = hand
    ux, uy = math.cos(ang), math.sin(ang)
    ex, ey = hx + ux * (n + 1), hy + uy * (n + 1)
    g.d.line((hx + ux, hy + uy, ex, ey), fill=0, width=3)
    g.d.line((hx + ux, hy + uy, ex, ey), fill=1)


def seated(g: Gfx, x: float, y: float, t: float, mudra: str = "gong", face: str = "sleep", head: str = "up",
           flip: bool = False) -> tuple[float, float]:
    """盘坐 + 手诀。mudra：gong 拱手 / up 剑指向天 / fwd 剑指向前 / palm 托掌 / chest 胸前掐诀 / raise 举手。
    返回手（指尖）的位置"""
    if mudra in ("gong", "raise"):
        return figure(g, x, y, t, legs="sit", arm="gong" if mudra == "gong" else "raise", face=face, head=head,
                      flip=flip)["hand"]
    s = -1 if flip else 1
    ang, L = {"up": (-1.25, 9), "fwd": (-0.12, 10), "palm": (0.45, 8), "chest": (-0.4, 6)}[mudra]
    h = act(g, x, y, t, ang=ang, L=L, legs="sit", face=face, head=head, flip=flip)["hand"]
    a = ang if not flip else math.pi - ang
    if mudra in ("up", "fwd"):
        fingers(g, h, a, 3)
        return h[0] + math.cos(a) * 4, h[1] + math.sin(a) * 4
    if mudra == "palm":  # 托掌：掌心朝上，拇指翘起
        g.px(h[0] + 2 * s, h[1] - 2)
        return h
    g.px(h[0] + s, h[1] - 2), g.px(h[0] - s, h[1] - 2)  # 掐诀：两指尖
    return h


def mouth(g: Gfx, x: float, y: float, open_: bool, flip: bool = False):
    """念咒时张嘴（盘坐的头：嘴在头顶下 14 行）"""
    if open_:
        mx = x + 2 if not flip else x - 3
        g.d.rectangle((mx, y - 34 + 14, mx + 1, y - 34 + 15), fill=0)


# ---------------------------------------------------------------- 道具

def _censer():
    """小香炉 13×8：口沿、两侧环耳、鼓腹一道回纹（背光网点）、三足"""
    p = Part(15, 8)
    p.shape("rectangle", (1, 0, 13, 1), fill=1)
    p.d.line((2, 1, 12, 1), fill=0)
    p.shape("polygon", [(2, 2), (12, 2), (13, 4), (11, 6), (3, 6), (1, 4)], fill=1)
    p.d.ellipse((0, 2, 2, 4), outline=1)
    p.m.ellipse((0, 2, 2, 4), outline=1)
    p.d.ellipse((12, 2, 14, 4), outline=1)
    p.m.ellipse((12, 2, 14, 4), outline=1)
    for x in (4, 7, 10):
        p.px(x, 4, 0), p.px(x + 1, 3, 0)
    p.dither([(9, 5), (13, 4), (11, 6), (8, 6)], 0.5, 0)
    for x in (3, 7, 11):
        p.px(x, 7)
    return p.sprite()


GHOST_FR = pix.frames("""
   #####
  #######
 #########
 ##..#..##
 ##..#..##
 #########
 ###...###
###########
 #########
 #########
 ## ### ##
 #   #   #
---
   #####
  #######
 #########
 ##..#..##
 ##..#..##
 #########
 ###...###
###########
 #########
 #########
 ### ### #
  #   #  #
""")
GHOST_WOW = pix.sprite("""
   #####
  #######
 #########
 #.#.#.#.#
 ##.###.##
 #.#.#.#.#
 ####.####
####...####
 ####.####
 #########
 # # # # #
 #  #  #
""")


def _lectern():
    """经案 15×10：小案上摊开一卷经（两页、中缝下凹、页上两行字），案腿带马蹄足"""
    p = Part(15, 10)
    p.shape("polygon", [(0, 1), (6, 2), (7, 3), (8, 2), (14, 1), (14, 4), (8, 5), (7, 6), (6, 5), (0, 4)], fill=1)
    for x in (1, 3, 5, 9, 11, 13):
        p.px(x, 2 + (x in (5, 9)), 0)
    for x in (2, 4, 10, 12):
        p.px(x, 4 - (x in (2, 12)) * 0, 0)
    p.shape("rectangle", (0, 7, 14, 7), fill=1)
    for x in (1, 12):
        p.shape("rectangle", (x, 8, x + 1, 9), fill=1)
    return p.sprite()


def _window():
    """月洞窗 21×21：圆框 + 冰裂纹窗棂"""
    p = Part(21, 21)
    p.shape("ellipse", (0, 0, 20, 20), fill=1)
    p.d.ellipse((2, 2, 18, 18), fill=0)
    for a, b in (((10, 2), (10, 18)), ((2, 10), (18, 10)), ((4, 5), (16, 15)), ((10, 6), (15, 10))):
        p.d.line(a + b, fill=1)
    p.mk = p.on.copy()
    return p.sprite()


_P: dict = {}


def _get(name):
    if name not in _P:
        _P[name] = {"censer": _censer, "lectern": _lectern, "window": _window}[name]()
    return _P[name]


def censer_spr():
    return _get("censer")


def stage(g: Gfx, t: float):
    floor(g, FLOOR)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)          # 护墙线
    for x in range(6, 128, 12):
        g.px(x, FLOOR - 5)
    pix.blit(g, _get("window"), 104, 21, outline=False)
    pix.blit(g, table_spr(30, 12), CENSER_X - 15, FLOOR - 12)
    pix.blit(g, censer_spr(), CENSER_X - 7, TOP - 8)
    g.d.line((CENSER_X, TOP - 9, CENSER_X, TOP - 16), fill=1)  # 一炷香
    if (t * 2.1) % 1 < 0.8:
        g.px(CENSER_X, TOP - 17)
    pix.blit(g, _get("lectern"), DX + 13, FLOOR - 10)


def mx_sun(g: Gfx, level: float, t: float, burst: float = 0.0):
    """点阵太阳：中间 2×2，八个方向的光芒（长度随金光等级，正斜两组交替转动）"""
    g.mx[3:5, 3:5] = True
    n = 3 if burst > 0 else 1 + int(level * 2.2)
    rot = int(t * 2) % 2
    for i in range(8):
        if burst <= 0 and i % 2 != rot:
            continue
        a = i / 8 * 2 * math.pi
        dx, dy = round(math.cos(a)), round(math.sin(a))
        for r in range(n):
            g.mx_set(int(math.floor(3.5 + dx * (1.5 + r))), int(math.floor(3.5 + dy * (1.5 + r))))


@register
class JinGuang(Ritual):
    id = "r2.jinguang"
    name = "金光神咒"
    desc = "小道士盘坐蒲团诵《金光神咒》，每句换一个手诀，咒牌逐字写出，身后像素金光一层层长出；雷霆、小鬼、金光速现各有一出"
    T = {"enter": 4.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = LAST_AT + 25.0   # 574 秒一遍

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.s = self.rng.randrange(1000)
        self.last_t = None

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    # ------------------------------------------------------------ 状态

    def slot(self, u: float):
        """(句号 i（-1 = 起咒，NP = 急急如律令），本句秒数 k)"""
        if u < LEAD:
            return -1, u
        if u >= LAST_AT:
            return NP, u - LAST_AT
        i = int((u - LEAD) // SLOT)
        return i, u - LEAD - i * SLOT

    def level(self, u: float) -> float:
        """金光等级 0..1：随句数一层层长"""
        return lerp(0.1, 1.0, clamp((u - LEAD) / (SLOT * (NP - 1)))) if u >= LEAD else span(u, 0.5, LEAD) * 0.1

    def pose(self, i: int, k: float, t: float):
        """(手诀, 表情, 头)"""
        if i < 0:
            return "gong", "sleep", "up"
        if i == NP:
            return ("raise" if k < 6 else "gong"), ("happy" if k > 3 else "sleep"), "up"
        m = MUDRA[i % len(MUDRA)]
        if i in BOLT and i != 21:
            m = "up"
        if i in GHOST:
            m = "fwd"
        if i == BURST:
            m = "raise"
        face, head = "sleep", "up"
        if k < 0.5 or 13.0 < k < 14.6:  # 换手诀时、句中睁眼看一眼
            face = "normal"
        if i in GHOST and 3.0 < k < 8.0 or i in BOLT and 2.6 < k < 5:
            face = "wow" if i != 21 else "normal"
        if i == BURST and 2.4 < k < 6:
            face = "wow"
        if 8.0 < k < 9.2 and i not in GHOST:  # 点头
            head = "bow"
        return m, face, head

    # ------------------------------------------------------------ 画面零件

    def aura(self, g: Gfx, level: float, t: float, boost: float = 0.0):
        """身后金光：光芒（虚线向外流）、头光、身光、光点"""
        lv = clamp(level + boost)
        if lv <= 0.005:
            return
        n = 6 + int(lv * 9) * 2
        r1 = 12 + lv * 22 + boost * 8
        for i in range(n):
            a = t * 0.12 + i / n * 2 * math.pi
            ca, sa = math.cos(a), math.sin(a)
            rr = r1 if i % 2 == 0 else r1 * 0.72
            off = (t * 10 + i * 2) % 5
            r = 11 + off
            while r < rr:
                r2 = min(r + 2, rr)
                g.d.line((DX + ca * r, CY + sa * r, DX + ca * r2, CY + sa * r2), fill=1)
                r += 5
            if lv > 0.15 and i % 2 == 0 and (int(t * 3) + i) % 5 == 0:
                star4(g, DX + ca * (rr + 2), CY + sa * (rr + 2))
        if lv > 0.34:  # 头光
            ring(g, HEAD[0], HEAD[1], 11, step=1)
        if lv > 0.5:  # 身光
            ring(g, DX, CY + 4, 19 + math.sin(t * 2) * 0.6, step=2, phase=t * 0.3)

    def write(self, g: Gfx, s: str, k: float, label=None):
        """右上咒牌：先清黑底、画框，再逐字写出（炁用手绘字）"""
        n = len(s)
        w = 12 * n + (n - 1)
        x0 = 125 - w
        g.d.rectangle((x0 - 3, 1, 127, 16), fill=0)
        g.d.rectangle((x0 - 3, 1, 127, 16), outline=1)
        shown = n if k is None else min(n, int(k / CPS) + 1)
        for j, ch in enumerate(s[:shown]):
            x = x0 + j * 13
            if ch == "炁":
                g.blit(QI, x, 5)
            else:
                g.text(x, 4, ch)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        boxed(g, 4, 4, label or (f"第{cn_num(n)}遍" if n < 100 else f"{n}遍"))

    def ghost(self, g: Gfx, k: float, which: int, t: float, dt: float, hand):
        """小鬼：从右边飘来（3–5.5s）→ 金光射中发抖（5.5–6.6s）→ 炸散"""
        if k < 3.0 or k > 6.6:
            return
        gy = (17 if which == 0 else 24) + math.sin(t * 3) * 2
        gx = lerp(132, 64, ease_out(span(k, 3.0, 5.0)))
        if k < 5.5:
            pix.blit(g, pix.anim(GHOST_FR, t, 4), gx, gy)
        else:
            q = span(k, 5.5, 5.9)
            hx, hy = hand
            tx, ty = lerp(hx, gx, q), lerp(hy, gy + 6, q)
            g.d.line((hx, hy, tx, ty), fill=0, width=4)
            g.d.line((hx, hy, tx, ty), fill=1, width=2)
            for m in range(3):
                pq = ((t * 3 + m / 3) % 1) * q
                star4(g, lerp(hx, gx, pq), lerp(hy, gy + 6, pq))
            jit = (int(t * 30) % 2) * 2 - 1 if q >= 1 else 0
            pix.blit(g, GHOST_WOW, gx + jit, gy)
        if k + dt >= 6.6 > k:
            self.sparks.burst(gx + 5, gy + 6, 22, 34, life=0.7, gravity=20)
            self.puffs.emit(gx + 5, gy + 6, vy=-4, life=0.8, rmax=3, spread=2)

    def bolt(self, g: Gfx, kind: str, k: float, t: float, dt: float):
        if not 3.0 <= k < 3.8:
            return
        on = int((k - 3.0) * 15) % 3 != 2
        seed = self.s + int(t // 50)
        if kind == "far":
            if on:
                lightning(g, 30, 0, 18, 14, seed, jag=3, branches=1)
            return
        if on:
            lightning(g, 64, 0, 66, FLOOR, seed, jag=5, branches=2, width=1 if kind == "near" else 2)
        if k - dt < 3.0:
            self.sparks.burst(66, FLOOR - 1, 16 if kind == "big" else 10, 40, up=25, life=0.6, gravity=90)
        if kind == "big" and k < 3.25:
            pix.shake(g, t, 2.0)
        elif k < 3.15:
            pix.shake(g, t, 1.0)

    def censer_smoke(self, dt: float, t: float):
        if int(t * 1.6) != int((t - dt) * 1.6):
            self.puffs.emit(CENSER_X, TOP - 18, vx=math.sin(t * 0.4) * 2, vy=-7, life=2.0, rmax=1.4, spread=0)

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, e: float, dt: float, aura_k: float = 1.0, verse: bool = True,
              mudra_over=None, face_over=None, head_over=None, label=None):
        u = e % self.CYCLE
        i, k = self.slot(u)
        renew = e >= self.CYCLE and u < LEAD
        stage(g, t)
        level = self.level(u)
        boost = 0.0
        if i == BURST and k > 2.4:
            boost = 0.6 * (1 - span(k, 3.0, 9.0))
        if renew:  # 续：金光收回身中
            level = lerp(1.0, 0.0, ease_in(span(u, 0.0, 1.2)))
        self.aura(g, level * aura_k, t, boost * aura_k)
        if renew and 1.2 <= u < 1.2 + 0.6:
            ring(g, DX, CY, (u - 1.2) * 40, step=2)
        if i == BURST and 2.4 < k < 4.0:
            for j in range(3):
                r = (k - 2.4) * 45 - j * 10
                if r > 0:
                    ring(g, DX, CY, r, step=2)
        pix.blit(g, cushion_spr(), DX - 12, FLOOR - 5)
        m, face, head = self.pose(i, k, t)
        if renew:
            m, face, head = "gong", "sleep", ("bow" if 0.6 < u < 2.0 else "up")
        m = mudra_over or m
        face = face_over or face
        head = head_over or head
        hand = seated(g, DX, SIT_Y, t, m, face, head)
        if verse and (u < LEAD and not renew or renew and u > 1.2):  # 胸前一点灵光
            star4(g, DX + 3, CY + 7, big=int(t * 8) % 2 == 0)
        chanting = verse and 0 <= i and k < CPS * (len(PHRASES[i]) if i < NP else 5) + 0.3
        if chanting and head == "up":
            mouth(g, DX, SIT_Y, int(k / CPS * 2) % 2 == 0)
        if 0 <= i and k < 0.35 and m != "gong" and verse:  # 换手诀：手上一闪
            star4(g, hand[0], hand[1], big=k < 0.18)
        if i in BOLT and verse:
            self.bolt(g, BOLT[i], k, t, dt)
        if i in GHOST and verse:
            self.ghost(g, k, GHOST[i], t, dt, hand)
        if verse and i >= 0 and int(k) % 7 == 4 and (k % 1) < 0.02 + dt:  # 光点飘出
            a = rand(int(u), self.s) * 2 * math.pi
            r = 12 + level * 20
            self.sparks.burst(DX + math.cos(a) * r, CY + math.sin(a) * r, 2, 6, up=6, life=1.0, gravity=-4)
        if i == BURST and k - dt < 2.4 <= k:
            pix.flash(g)
        if i == BURST and 2.4 < k < 2.8:
            pix.shake(g, t, 1.5)
        self.censer_smoke(dt, t)
        self.puffs.step(dt, wind=0.5)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g, trail=False)
        # 文字（最后画）
        if label:
            self.write(g, label, None)
        elif verse:
            if i < 0 or renew:
                self.write(g, "金光神咒", None)
            elif i < NP:
                self.write(g, PHRASES[i], k)
            else:
                self.write(g, LAST, k)
        self.counter(g, e if not (renew and u < 1.2) else e - u - 1)
        mx_sun(g, level * aura_k, t, burst=1.0 if (i == BURST and 2.4 < k < 4) else 0.0)
        if i == BURST and 2.4 < k < 3.4:
            g.mx_level = 6
        return hand

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        stage(g, t)
        pix.blit(g, cushion_spr(), DX - 12, FLOOR - 5)
        if t < 1.8:
            x = lerp(-14, DX - 14, ease_out(span(t, 0, 1.8)))
            figure(g, x, FLOOR, t, legs="walk")
        elif t < 2.3:  # 一跳坐上蒲团
            q = span(t, 1.8, 2.3)
            x = lerp(DX - 14, DX, q)
            if q < 0.6:
                figure(g, x, FLOOR - math.sin(q / 0.6 * math.pi) * 8, t, arm="raise", face="happy")
            else:
                seated(g, DX, SIT_Y - (1 - span(q, 0.6, 1)) * 3, t, "gong", "happy")
        else:
            seated(g, DX, SIT_Y, t, "gong", "normal" if t < 2.9 else "sleep")
        if t - dt < 2.3 <= t:
            self.puffs.emit(DX - 12, FLOOR - 2, vx=-8, vy=-3, life=0.6, rmax=1.6)
            self.puffs.emit(DX + 12, FLOOR - 2, vx=8, vy=-3, life=0.6, rmax=1.6)
            pix.shake(g, t, 0.8)
        if t > 3.0:  # 胸前一点灵光
            star4(g, DX + 1, CY + 6, big=int(t * 8) % 2 == 0)
        self.censer_smoke(dt, t)
        self.puffs.step(dt, wind=0.5)
        self.puffs.draw(g)
        if t > 2.6:
            self.write(g, "金光神咒", None)
        self.counter(g, 0.0)
        mx_sun(g, 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        self.scene(g, t, e, dt)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        q = span(t, 0.0, 1.0)
        self.scene(g, t, e, dt, aura_k=1 - ease_in_out(q), verse=False, mudra_over="gong",
                   face_over="sleep", head_over="bow" if t > 0.8 else "up", label="暂歇")

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        q = ease_out(span(t, 0.3, 1.5))
        face = "wow" if 0.2 < t < 0.8 else None
        if t < 0.3:
            self.scene(g, t, e, dt, aura_k=0, verse=False, mudra_over="gong", face_over="sleep", label="暂歇")
        else:
            self.scene(g, t, e, dt, aura_k=q, verse=t > 1.2, face_over=face,
                       label=None if t > 1.2 else "暂歇")
        if 0.3 <= t < 0.3 + dt:
            self.sparks.burst(DX, CY, 10, 20, life=0.5, gravity=0)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        u = e % self.CYCLE
        stage(g, t)
        lv = lerp(self.level(u), 1.0, ease_out(span(t, 0, 1.2)))
        boost = 0.5 * span(t, 0.8, 1.2) * (1 - span(t, 3.5, 5.5) * 0.6)
        self.aura(g, lv, t, boost)
        if t > 1.2:  # 光环一圈圈涌出
            for j in range(4):
                r = ((t - 1.2) * 30 - j * 9)
                if 0 < r < 70:
                    ring(g, DX, CY, r, step=2)
        if t > 2.0:  # 金光罩住全身
            g.d.ellipse((DX - 16, CY - 18, DX + 16, FLOOR - 1), outline=1)
        pix.blit(g, cushion_spr(), DX - 12, FLOOR - 5)
        m = "raise" if 0.3 < t < 2.5 else "gong"
        seated(g, DX, SIT_Y, t, m, "wow" if 1.0 < t < 2.0 else ("happy" if t >= 2.0 else "sleep"),
               "bow" if 3.6 < t < 4.6 else "up")
        if 1.2 <= t < 1.2 + dt:
            pix.flash(g)
            self.sparks.burst(DX, CY, 30, 50, up=10, life=1.1, gravity=30)
        if 1.2 < t < 1.5:
            pix.shake(g, t, 1.5)
        self.censer_smoke(dt, t)
        self.puffs.step(dt, wind=0.5)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g, trail=False)
        self.write(g, "金光速现" if t < 3.0 else "覆护真人", None)
        self.counter(g, e)
        mx_sun(g, 1.0, t, burst=1.0 if t > 1.2 else 0.0)
        if t > 1.2:
            g.mx_level = 1 + int(6 * (1 - span(t, 1.2, 3.0)))
