"""掐诀：左边小道士立掌掐诀，右边一个圆形“特写框”里是他那只大号像素手，一诀一诀地结，每诀各有气象。

掐诀多用左手（右手执剑、执铃）。手型据民间道坛流传的诀谱：剑诀（食、中二指并伸，拇指压无名指和小指）、
灵官诀（中指直竖，食指屈来勾住中指第一节，拇指压住无名指和小指）、五雷诀（四指屈入掌心，拇指压在指背上如握拳）、
三山诀（握拳后依次弹出食指、小指、拇指）。

入场：小道士走上来站定，举手；特写框“啵”地弹开，一只张开的手从框底升上来，四指依次屈下，结成剑诀，指尖冒出剑气。
持续：一轮 600 秒，依次结四诀，每诀 150 秒，换诀时手指一根根屈伸过去。每诀各有气象：剑诀指尖一道光剑、流光上冲；
      灵官诀中指尖一团灵官火；五雷诀拳边雷光乱闪（框里一闪）；三山诀身后升起三座山。
      每 12 秒“一按”：手一紧，一圈光从手上荡开、火星迸出。框外一圈点状“气圈”随本诀时间合拢。
      左上写诀名，下面小字“第几遍”。四诀走完后甩手散诀（张开一抖，余气散出），再结剑诀开始下一遍。
中断：手松开、垂下沉出框外，写“松诀”。  恢复：手升回来重新结诀。
圆满：四诀快速连掐一遍，每结成一诀闪一圈光，然后握拳收诀，四周光芒放射，题“道法自然”（《道德经》）。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r3_kit import (FLOOR, Clock, banner, banner_text, crossed, hand_at, label, mx_ring, nth, pose_arm, put, rays,
                     round_of, sparkle)

DX = 20                       # 小道士
BX, BY, BR = 86, 32, 30       # 特写框
WRIST = (86, 62)              # 大手腕底
CYCLE = 600.0
EACH = 150.0
TRANS = 2.0
RENEW = 4.0
NAMES = ["剑诀", "灵官诀", "五雷诀", "三山诀"]
# 手型：(食, 中, 无名, 小) 伸展 0..1（食指 -1 = 勾住中指），拇指：out 张开 / up 贴边 / fold 压无名小指 / over 压指背
MUDRA = {
    "open": ((1, 1, 1, 1), "out"),
    "jian": ((1, 1, 0, 0), "fold"),
    "lingguan": ((-1, 1, 0, 0), "fold"),
    "wulei": ((0, 0, 0, 0), "over"),
    "sanshan": ((1, 0, 0, 1), "out"),
}
ORDER = ["jian", "lingguan", "wulei", "sanshan"]
FULL = (15, 18, 16, 12)              # 四指伸直时露出掌顶的长度
FX = (72, 78, 84, 90)                # 四指左边 x（特写框坐标）
FW = (5, 5, 5, 4)
TOP = 34                             # 掌顶（指根）y


# ---------------------------------------------------------------- 大号像素手

def _hand(L: tuple, thumb: str) -> Sprite:
    """大手（掌心朝外，四指朝上，拇指在左）：宽袖口 → 手腕 → 手掌（大鱼际隆起、掌纹、右侧阴影）→ 四指 → 拇指。
    伸直的指头：圆指尖、两道指节纹、右侧一道暗边显圆；屈起的指头：从指根往下折、盖住掌心上部，指甲朝外；
    L = 四指露出的长度（≤4 为屈起；-1 为食指勾住中指第一节）"""
    ox = -56
    p = Part(56, 64)

    def X(x):
        return x + ox

    def R(x0, y0, x1, y1, fill=1, r=2):
        p.shape("rounded_rectangle", (X(x0), y0, X(x1), y1), radius=r, fill=fill)

    def ink(x0, y0, x1, y1, v=0):
        p.d.line((X(x0), y0, X(x1), y1), fill=v)

    # 宽袖口：两道镶边，下半网点
    p.shape("polygon", [(X(66), 63), (X(70), 56), (X(100), 56), (X(104), 63)], fill=1)
    ink(70, 58, 100, 58)
    ink(69, 60, 101, 60, 1)
    p.dither([(X(67), 61), (X(103), 61), (X(104), 63), (X(66), 63)], 0.5, 0)
    # 手腕
    R(76, 50, 92, 57, r=1)
    # 手掌：上宽下窄，左下大鱼际鼓出来
    p.shape("polygon", [(X(71), TOP + 1), (X(95), TOP + 1), (X(95), TOP + 12), (X(92), TOP + 19), (X(77), TOP + 19),
                        (X(70), TOP + 14), (X(68), TOP + 9)], fill=1)
    p.d.arc((X(70), TOP + 6, X(84), TOP + 22), 190, 280, fill=0)          # 大鱼际纹
    ink(80, TOP + 9, 93, TOP + 7)                                            # 感情线
    ink(78, TOP + 13, 86, TOP + 12)                                          # 智慧线
    p.dither([(X(93), TOP + 4), (X(96), TOP + 4), (X(96), TOP + 13), (X(93), TOP + 17)], 0.5, 0)
    # 伸直的指头（先画，屈起的指头之后盖在掌上）
    curled = []
    for i in range(4):
        x0, w = FX[i], FW[i]
        x1 = x0 + w - 1
        ln = L[i]
        if i == 0 and ln == -1:      # 灵官诀：食指（之后再画，勾在中指上）
            continue
        if ln <= 4:
            curled.append(i)
            continue
        ln = int(round(ln))
        R(x0, TOP - ln, x1, TOP + 3, r=2)
        for k in (1, 2):
            y = TOP - int(ln * k / 3)
            ink(x0 + 1, y, x1 - 2, y)
        ink(x1, TOP - ln + 3, x1, TOP - 1)                                    # 右侧暗边
        p.px(X(x0 + 1), TOP - ln + 1, 0) if w >= 5 else None                  # 指尖一点高光边
    if L[0] == -1:                   # 灵官诀：食指立起一截，再勾过去搭在中指第一节上（暗线勾边，压在中指上）
        x0, x1 = FX[0], FX[0] + 4
        R(x0, TOP - 8, x1, TOP + 3)
        ink(x0 + 1, TOP - 3, x1 - 1, TOP - 3)
        hook = (X(x0), TOP - 13, X(FX[1] + 3), TOP - 8)
        p.d.rounded_rectangle((hook[0] - 1, hook[1] - 1, hook[2] + 1, hook[3] + 1), radius=2, fill=0)
        p.shape("rounded_rectangle", hook, radius=2, fill=1)
        ink(x1, TOP - 12, x1, TOP - 9)                                         # 弯折处
        p.d.arc((X(FX[1]), TOP - 13, X(FX[1] + 4), TOP - 9), 270, 90, fill=0)  # 指甲
    m = np.array(p.mk, bool)
    for i in range(3):                                                         # 指缝：伸直的两指之间挖开
        gx = X(FX[i] + FW[i])
        if not (L[0] == -1 and i == 0):
            m[:TOP, gx] = False
    p.mk = __import__("PIL.Image", fromlist=["Image"]).fromarray(m)
    p.m = __import__("PIL.ImageDraw", fromlist=["ImageDraw"]).Draw(p.mk)
    # 屈起的指头：从指根折下来盖住掌心上部，暗线勾边，指甲（暗弧）在下端
    for i in curled:
        x0, w = FX[i], FW[i]
        x1 = x0 + w - 1
        p.d.rounded_rectangle((X(x0 - 1), TOP - 3, X(x1 + 1), TOP + 9), radius=2, fill=0)
        R(x0, TOP - 2, x1, TOP + 8, r=2)
        ink(x0 + 1, TOP + 1, x1 - 1, TOP + 1)                                  # 指节
        p.d.arc((X(x0), TOP + 4, X(x1), TOP + 10), 200, 340, fill=0)          # 指甲
        p.shape("rectangle", (X(x0), TOP - 2, X(x1), TOP - 1), fill=1)        # 指背顶上一点
    # 拇指
    if thumb == "out":      # 张开：从大鱼际往左上伸出
        poly = [(X(70), TOP + 15), (X(68), TOP + 8), (X(62), TOP + 1), (X(59), TOP - 3), (X(62), TOP - 6),
                (X(67), TOP - 2), (X(73), TOP + 5)]
        p.shape("polygon", poly, fill=1)
        ink(62, TOP - 2, 65, TOP - 4)                                          # 指甲
        ink(64, TOP + 4, 67, TOP + 2)                                          # 指节纹
    elif thumb == "up":     # 贴着掌边立起
        p.d.rounded_rectangle((X(65), TOP - 7, X(71), TOP + 16), radius=3, fill=0)
        R(66, TOP - 6, 70, TOP + 15, r=2)
        ink(66, TOP + 3, 69, TOP + 3)
        ink(67, TOP - 5, 69, TOP - 5)
    elif thumb == "fold":   # 从大鱼际斜着横过掌心，指肚压在无名指、小指的指甲上
        poly = [(X(69), TOP + 15), (X(70), TOP + 9), (X(80), TOP + 5), (X(92), TOP + 3), (X(94), TOP + 6),
                (X(92), TOP + 9), (X(81), TOP + 12), (X(74), TOP + 17)]
        p.d.polygon([(x - 1 if i in (0, 1, 7) else x, y - 1 if i in (2, 3) else (y + 1 if i in (5, 6, 7) else y))
                     for i, (x, y) in enumerate(poly)], fill=0)
        p.shape("polygon", poly, fill=1)
        ink(80, TOP + 6, 80, TOP + 10)                                         # 指节纹
        p.d.arc((X(87), TOP + 3, X(95), TOP + 9), 300, 60, fill=0)            # 指甲
    elif thumb == "over":   # 五雷：拇指横压在四个指背中段
        poly = [(X(68), TOP + 12), (X(70), TOP + 4), (X(86), TOP + 2), (X(89), TOP + 5), (X(86), TOP + 8),
                (X(73), TOP + 10)]
        p.d.polygon([(x, y - 1) if i in (1, 2) else ((x, y + 1) if i in (4, 5) else (x, y)) for i, (x, y) in enumerate(poly)],
                    fill=0)
        p.shape("polygon", poly, fill=1)
        ink(78, TOP + 4, 78, TOP + 8)
        p.d.arc((X(82), TOP + 2, X(90), TOP + 8), 300, 60, fill=0)
    on = np.array(p.on, bool) & np.array(p.mk, bool)
    s = Sprite(on=on, mask=np.array(p.mk, bool))
    s.anchor = (X(86), 63)
    tips = {}
    for i in range(4):
        ln = L[i]
        tips[f"f{i}"] = (X(FX[i] + FW[i] // 2), TOP - (int(round(ln)) if ln > 4 else 2))
    tips["fist"] = (X(82), TOP + 4)
    s.pts = tips
    return s


_H: dict = {}


def hand_spr(L, thumb) -> Sprite:
    k = (tuple(int(round(v)) for v in L), thumb)
    if k not in _H:
        _H[k] = _hand(*k)
    return _H[k]


def mudra_lengths(name: str):
    ext, thumb = MUDRA[name]
    return tuple(-1 if v == -1 else lerp(3, FULL[i], v) for i, v in enumerate(ext)), thumb


def blend(a: str, b: str, q: float):
    """两诀之间：四指一根根屈伸过去（食指先动），拇指在中途换位置"""
    La, ta = mudra_lengths(a)
    Lb, tb = mudra_lengths(b)
    out = []
    for i in range(4):
        qi = ease_in_out(span(q, i * 0.12, 0.55 + i * 0.12))
        va, vb = La[i], Lb[i]
        if va == -1 or vb == -1:
            v = (-1 if qi > 0.5 else va) if vb == -1 else (vb if qi > 0.5 else 3)
            if va == -1 and qi <= 0.5:
                v = -1
        else:
            v = lerp(va, vb, qi)
        out.append(v)
    thumb = ta if q < 0.3 else ("up" if q < 0.7 else tb)
    if ta == tb:
        thumb = ta
    return tuple(out), thumb


FLAME = pix.frames("""
  #
 ##
 ###
####
#.##
#..#
 ##
---
  #
  ##
 ###
####
##.#
#..#
 ##
---
 #
 ##
###
####
#.##
#..#
 ##
""")

MX_HAND = {
    "open": (4, 4, 4, 4, True), "jian": (4, 4, 1, 1, False), "lingguan": (2, 4, 1, 1, False),
    "wulei": (1, 1, 1, 1, False), "sanshan": (4, 1, 1, 4, True),
}


@register
class ShoujueRitual(Ritual):
    id = "r3.shoujue"
    name = "掐诀"
    desc = "小道士立掌掐诀，右边特写框里一只大号像素手依次结剑诀、灵官诀、五雷诀、三山诀，各有剑气、灵火、雷光、三山"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 6.0}
    CYCLE = CYCLE

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.clock = Clock()
        self.rings: list[list] = []

    # ------------------------------------------------------------ 公用

    def bubble(self, g: Gfx, k: float = 1.0, ring: float = 0.0, t: float = 0.0):
        """特写框：双线圆框 + 从小道士手边连过来的两道虚线；ring = 外圈气圈合拢的比例"""
        r = BR * ease_out_back(k) if k < 1 else BR
        if r < 2:
            return
        h = hand_at(DX, FLOOR, "up30", t, "jian")
        hx, hy = h[0] + 2, h[1] - 3
        for a in (150, 215):
            ex, ey = BX + math.cos(math.radians(a)) * r, BY + math.sin(math.radians(a)) * r
            pix.dotted(g, hx, hy, ex, ey, 2)
        g.d.ellipse((BX - r - 1, BY - r - 1, BX + r + 1, BY + r + 1), fill=0)
        g.d.ellipse((BX - r, BY - r, BX + r, BY + r), outline=1)
        if ring > 0:
            n = 48
            for i in range(int(n * ring)):
                a = -math.pi / 2 + i / n * 2 * math.pi
                if i % 2 == 0:
                    g.px(BX + math.cos(a) * (r + 3), BY + math.sin(a) * (r + 3))

    def clip(self, g: Gfx, before: np.ndarray):
        """特写框外面的东西恢复成画框之前的样子（手和气象只在框里）"""
        a = g.array()
        ys, xs = np.mgrid[0:64, 0:128]
        inside = (xs - BX) ** 2 + (ys - BY) ** 2 <= (BR - 1) ** 2
        a[~inside] = before[~inside]
        g.put(a)

    def big_hand(self, g: Gfx, L, thumb, dy: float = 0.0, jit: int = 0):
        spr = hand_spr(L, thumb)
        return put(g, spr, WRIST[0] + jit, WRIST[1] + dy)

    def omen(self, g: Gfx, name: str, pts, t: float, e: float, power: float = 1.0):
        """各诀的气象（画在框里）"""
        if name == "jian":       # 剑气：两指尖上一道光剑，流光上冲
            x0 = pts["f0"][0] - 2
            x1 = pts["f1"][0] + 2
            ytop = BY - BR + 3
            y0 = min(pts["f0"][1], pts["f1"][1]) - 2
            cx = (x0 + x1) / 2
            g.d.line((x0, y0, x0, ytop + 6), fill=1)            # 光剑：两道刃线，顶上收成剑尖
            g.d.line((x1, y0, x1, ytop + 6), fill=1)
            g.d.line((x0, ytop + 6, cx, ytop), fill=1)
            g.d.line((x1, ytop + 6, cx, ytop), fill=1)
            for j in range(3):                                   # 流光往上冲
                q = (t * 1.2 + j / 3) % 1
                y = lerp(y0, ytop + 4, q)
                g.d.line((cx, y, cx, y - 2), fill=1)
        elif name == "lingguan":  # 灵官火：中指尖一团火
            x, y = pts["f1"]
            fr = pix.anim(FLAME, t, 8)
            pix.blit(g, pix.stretch(fr, 1.0 * power + 0.6, 1.0 * power + 0.6), x - 3, y - 13)
        elif name == "wulei":     # 雷光：拳边乱闪
            if (t * 3) % 1 < 0.35:
                from ..engine.fx import lightning
                k = int(t * 3)
                side = -1 if k % 2 else 1
                x = BX + side * 14
                lightning(g, x, BY - 20, x + side * 4, BY + 6, seed=k)
                if (t * 3) % 1 < 0.06:
                    sparkle(g, x, BY - 20, 3)
        elif name == "sanshan":   # 三山：手后升起三座山
            pass

    def mountains(self, g: Gfx, h: float):
        """三山诀：三座山（在手后面先画）"""
        if h <= 0:
            return
        base = BY + 14
        for cx, ww, hh in ((BX - 16, 14, 22), (BX, 16, 30), (BX + 16, 14, 22)):
            top = base - hh * h
            g.d.polygon([(cx - ww, base), (cx, top), (cx + ww, base)], fill=0, outline=1)
            g.d.line((cx, top, cx - 3, top + 6), fill=1)
            g.d.line((cx - 3, top + 6, cx + 2, top + 9), fill=1)

    def little(self, g: Gfx, t: float, pose: str = "jue", face: str = "normal"):
        """左边的小道士：jue 立掌掐诀 / idle 垂手 / gong 拱手"""
        if pose == "jue":
            pose_arm(g, DX, "up30", t, "jian", face=face)
        elif pose == "gong":
            daoshi(g, DX, FLOOR, "gongshou", t, face=face)
        else:
            daoshi(g, DX, FLOOR, "idle", t, face=face)

    def emit_ring(self, x, y):
        self.rings.append([x, y, 0.0])

    def fx(self, g: Gfx, dt: float):
        keep = []
        for r in self.rings:
            r[2] += dt
            if r[2] < 0.5:
                rr = 6 + r[2] * 40
                g.d.ellipse((r[0] - rr, r[1] - rr, r[0] + rr, r[1] + rr), outline=1)
                keep.append(r)
        self.rings = keep
        self.sparks.step(dt)
        self.sparks.draw(g)

    def mx(self, g: Gfx, name: str, t: float, flash: bool = False):
        a, b, c, d, th = MX_HAND[name]
        for i, h in enumerate((a, b, c, d)):
            for y in range(4 - h, 8):
                g.mx[y, 2 + i] = True
        g.mx[4:8, 2:6] = True
        if th:
            g.mx[3, 0] = g.mx[4, 1] = True
        else:
            g.mx[4, 1] = g.mx[4, 2] = True
        if name == "wulei" and (t * 3) % 1 < 0.35:
            g.mx[0, 0] = g.mx[0, 7] = g.mx[1, 7] = True
        if flash:
            g.mx[:] = True

    def names(self, g: Gfx, name: str, n: int, s: str | None = None):
        if not s:
            s = NAMES[ORDER.index(name)] if name in ORDER else "掐诀"
        label(g, 3, 3, s)
        if n:
            label(g, 4, 16, nth(n, "遍"), size=8)

    def state(self, k: float):
        """本轮第 k 秒：(诀名, 指长, 拇指, 本诀进度)"""
        i = min(int(k // EACH), 3)
        u = k - i * EACH
        name = ORDER[i]
        if i > 0 and u < TRANS:
            L, th = blend(ORDER[i - 1], name, u / TRANS)
        else:
            L, th = mudra_lengths(name)
        return name, L, th, u / EACH

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, e: float, dt: float, name: str, L, thumb, ring: float, n: int,
              pulse: float = -1.0, little: str = "jue", dy: float = 0.0, label_s: str | None = None,
              power: float = 1.0, shake_hand: int = 0, omen: bool = True, bubble_k: float = 1.0, bob: int = 0):
        self.little(g, t, little)
        before = g.array()
        self.bubble(g, bubble_k, ring, t)
        if bubble_k >= 1:
            if name == "sanshan" and omen:
                self.mountains(g, min(1.0, power))
            pts = self.big_hand(g, L, thumb, dy + bob, shake_hand)
            if omen and dy == 0:
                self.omen(g, name, pts, t, e, power)
            if 0 <= pulse < 0.3:   # 一按：一圈光从手上荡开
                fx, fy = pts["fist"]
                g.d.ellipse((fx - 6 - pulse * 40, fy - 6 - pulse * 40, fx + 6 + pulse * 40, fy + 6 + pulse * 40),
                            outline=1)
            self.fx(g, dt)
            self.clip(g, before)
            g.d.ellipse((BX - BR, BY - BR, BX + BR, BY + BR), outline=1)
        else:
            self.fx(g, dt)
        self.names(g, name, n, label_s)

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        if t < 2.0:
            x = lerp(-14, DX, ease_out(span(t, 0, 2.0)))
            daoshi(g, x, FLOOR, "walk", t)
            label(g, 3, 3, "掐诀")
            g.mx[4:8, 2:6] = True
            return
        k = span(t, 2.0, 2.5)
        rise = span(t, 2.5, 3.3)
        q = span(t, 3.4, 5.2)
        L, th = blend("open", "jian", q)
        if crossed(t, dt, 5.2):
            self.sparks.burst(BX - 6, BY - 16, 14, 30, up=10, life=0.6, gravity=30)
            self.emit_ring(BX - 6, BY - 6)
        self.frame(g, t, t, dt, "jian", L, th, 0.0, 0, little="jue" if t > 2.3 else "idle",
                   dy=(1 - ease_out(rise)) * 40, omen=t > 5.2, bubble_k=k)
        self.mx(g, "jian" if q > 0.6 else "open", t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        if k >= CYCLE - RENEW:
            self.renew(g, k - (CYCLE - RENEW), t, e, dt, n)
            return
        name, L, th, prog = self.state(k)
        u = e % 12.0
        pulse = u - 6.0 if 6.0 <= u < 6.3 else -1.0
        if crossed(u, dt, 6.0):
            self.sparks.burst(BX - 4, BY - 4, 12, 30, life=0.5, gravity=20)
        trans = int(k // EACH) > 0 and (k % EACH) < TRANS
        little = "gong" if trans else "jue"
        bob = round(math.sin(e * 1.6) * 0.8)
        self.frame(g, e, e, dt, name, L, th, prog, n, pulse=pulse, little=little, dy=0,
                   omen=not trans, power=1.0 if name != "sanshan" else min(1.0, (k % EACH) / 4.0), bob=bob)
        if trans and crossed(k % EACH, dt, TRANS - 0.05):
            self.emit_ring(BX - 4, BY - 6)
        self.mx(g, name, t, flash=0 <= pulse < 0.1)

    def renew(self, g: Gfx, u: float, t: float, e: float, dt: float, n: int):
        """甩手散诀：张开一抖，余气散出，再结剑诀"""
        if u < 1.2:
            L, th = blend("sanshan", "open", u / 1.2)
            jit = 0
        elif u < 2.4:
            L, th = mudra_lengths("open")
            jit = int(round(math.sin(u * 40) * 2))
            if int(u * 20) % 2 == 0:
                a = rand(int(u * 20), 3) * 2 * math.pi
                self.sparks.burst(BX + math.cos(a) * 10, BY - 6 + math.sin(a) * 10, 3, 40, life=0.6, gravity=10)
        else:
            L, th = blend("open", "jian", span(u, 2.4, 3.8))
            jit = 0
        self.frame(g, e, e, dt, "jian", L, th, 0.0, n, little="idle" if u < 2.4 else "jue", shake_hand=jit,
                   omen=False, label_s="散诀" if u < 2.4 else "剑诀")
        self.mx(g, "open" if u < 2.4 else "jian", t)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        name, L0, th0, prog = self.state(k)
        q = span(t, 0.0, 0.6)
        name_b = name
        L, th = blend(name, "open", q) if q < 1 else mudra_lengths("open")
        dy = ease_out(span(t, 0.6, 1.4)) * 44
        self.frame(g, t, e, dt, name_b, L, th, prog, n, little="idle" if t > 0.6 else "jue", dy=dy, omen=q < 0.2,
                   label_s="松诀" if t > 0.5 else None)
        self.mx(g, "open", t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        name, L1, th1, prog = self.state(k)
        dy = (1 - ease_out(span(t, 0.0, 0.7))) * 44
        q = span(t, 0.7, 1.6)
        if q < 1:
            L, th = blend("open", name, q) if name != "lingguan" or q > 0.5 else blend("open", "jian", q)
        else:
            L, th = L1, th1
        if crossed(t, dt, 1.6):
            self.emit_ring(BX - 4, BY - 6)
            self.sparks.burst(BX - 4, BY - 10, 12, 30, life=0.5)
        self.frame(g, t, e, dt, name, L, th, prog, n, little="jue" if t > 0.3 else "idle", dy=dy, omen=q >= 1)
        self.mx(g, name if q >= 1 else "open", t)

    def complete(self, g: Gfx, t: float, e: float):
        """四诀快速连掐（每诀 0.7 秒，结成一闪一圈光）→ 握拳收诀 → 光芒放射 → 道法自然"""
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        seq = ORDER + ["wulei"]
        if t < 3.5:
            i = min(int(t / 0.7), 4)
            u = t - i * 0.7
            a = seq[i - 1] if i > 0 else self.state(k)[0]
            b = seq[i]
            L, th = blend(a, b, span(u, 0, 0.45))
            name = b if i < 4 else "wulei"
            if crossed(u, dt, 0.45):
                self.emit_ring(BX - 4, BY - 6)
                self.sparks.burst(BX - 4, BY - 10, 10, 30, life=0.5)
            lab = NAMES[ORDER.index(name)] if i < 4 else "收诀"
            self.frame(g, t, e, dt, name, L, th, 1.0, n, little="jue", label_s=lab, omen=u > 0.45 and i < 4)
            self.mx(g, name, t, flash=0.45 <= u < 0.55)
            return
        L, th = mudra_lengths("wulei")
        self.little(g, t, "gong", face="happy")
        before = g.array()
        self.bubble(g, 1.0, 1.0, t)
        rays(g, BX - 2, BY - 2, 10, 26, 16, rot=t * 0.6, dash=2)
        self.big_hand(g, L, th)
        if crossed(t, dt, 3.5):
            self.sparks.burst(BX - 4, BY - 6, 30, 50, up=10, life=1.0, gravity=30)
        self.fx(g, dt)
        self.clip(g, before)
        g.d.ellipse((BX - BR, BY - BR, BX + BR, BY + BR), outline=1)
        if 3.5 <= t < 3.58:
            pix.flash(g)
        if 3.5 <= t < 3.9:
            pix.shake(g, t, 1.5)
        if t > 3.8:
            banner(g, 28, 4, "道法自然", span(t, 3.8, 4.2))
            banner_text(g, 28, 4, "道法自然", span(t, 3.8, 4.2))
        else:
            label(g, 3, 3, "收诀")
        self.mx(g, "wulei", t)
        mx_ring(g, (t - 3.5) * 4)
        g.mx_level = 1 + int(6 * (1 - span(t, 3.5, 4.9)))
