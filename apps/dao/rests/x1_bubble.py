"""打盹冒泡：看炉的小道童抱着拂尘打瞌睡，头一点一点，鼻涕泡随呼吸一大一小；
泡泡吹太大“啪”地破了，惊醒左右看看又睡；偶尔一声“咳！”——师父来了，赶紧坐直装样子。

依据：道观里道童（小道士）看守丹炉、手执拂尘的日常；拂尘为道士常用法器，有“拂去尘缘”之意。
打盹冒鼻涕泡是漫画里的通用笑点（非典籍）。
"""
from __future__ import annotations

import math

from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import flame, smoke_wisp
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Pen, backdrop, ev, iris

HC = (58, 30)       # 头心
BREATH = 3.6        # 一呼一吸
BIG_EVERY = 6       # 第几口气吹出大泡


def _bg():
    p = Pen()
    # 右：丹炉（三足、炉盖、火口）
    p.poly([(100, 40), (124, 40), (122, 56), (102, 56)], fill=0.3)
    p.rect((98, 37, 126, 40), fill=0)
    p.chord((104, 26, 120, 40), 180, 360, fill=0)
    p.rect((110, 23, 114, 27), fill=1)
    p.rect((108, 47, 116, 53), fill=0)
    for x in (103, 112, 121):
        p.rect((x - 1, 56, x + 1, 62), fill=1)
    # 身子：肩、交领道袍
    body = [(22, 64), (30, 52), (42, 47), (74, 47), (86, 52), (94, 64)]
    p.poly(body, fill=0.25)
    p.line([(46, 47), (62, 64)])
    p.line([(70, 47), (56, 58)])
    p.line([(47, 47), (63, 64)], 0)
    # 抱在怀里的拂尘：柄斜靠左肩，尘尾垂在左边
    p.line([(40, 64), (24, 30)], 1, 2)
    p.rect((22, 27, 26, 31), fill=1)
    for i in range(9):
        a = math.radians(200 + i * 9)
        x1, y1 = 24 + math.cos(a) * 22, 29 + math.sin(a) * 4 + i * 2.6
        p.line([(24, 29), ((24 + x1) / 2 - 2, (29 + y1) / 2 + 3), (x1, y1 + 8)])
    return p.image()


def _head() -> Sprite:
    p = Pen(44, 44)
    cx, cy = 22, 24
    # 双丫髻 + 发带
    for bx in (7, 37):
        p.ellipse((bx - 6, 0, bx + 6, 12), fill=1)
        p.line([(bx - 4, 10), (bx - 7, 16)])
        p.line([(bx + 4, 10), (bx + 7, 16)])
    p.ellipse((cx - 18, cy - 17, cx + 18, cy + 17), fill=0)
    p.chord((cx - 18, cy - 17, cx + 18, cy + 17), 180, 360, fill=1)    # 头发
    p.poly([(cx - 14, cy - 2), (cx - 9, cy - 7), (cx - 3, cy - 3), (cx + 3, cy - 8), (cx + 9, cy - 3),
            (cx + 15, cy - 6), (cx + 17, cy), (cx - 17, cy)], fill=0, outline=None)   # 刘海的下沿
    p.line([(cx - 14, cy - 2), (cx - 9, cy - 7), (cx - 3, cy - 3), (cx + 3, cy - 8), (cx + 9, cy - 3), (cx + 15, cy - 6)])
    for s in (-1, 1):  # 腮红
        for k in range(3):
            p.line([(cx + s * 11 + k * 2 - 2, cy + 9), (cx + s * 11 + k * 2, cy + 7)])
    p.px(cx, cy + 6)   # 鼻
    return p.sprite()


_A = {}


def _assets():
    if not _A:
        _A.update(bg=_bg(), head=_head())


@register
class Bubble(Rest):
    id = "x1.bubble"
    name = "打盹冒泡"
    desc = "看炉的小道童抱着拂尘打瞌睡，头一点一点、鼻涕泡一大一小；泡破惊醒，师父一咳赶紧坐直"
    T = {"enter": 2.6, "exit": 1.2}

    def setup(self):
        _assets()
        self._ht = 0.0

    # ------------------------------------------------------------ 零件

    def droop(self, t: float) -> float:
        """头慢慢往下垂，垂到底猛地一点抬回来（周期 9 秒）"""
        u = t % 9.0
        if u < 8.4:
            return ease_in(u / 8.4) * 5
        return lerp(5, 0, ease_out((u - 8.4) / 0.6))

    def bubble_r(self, t: float) -> tuple[float, bool]:
        """鼻涕泡半径；第 BIG_EVERY 口气越吹越大，最后破掉（返回 (半径, 正在破)）"""
        n, u = divmod(t, BREATH)
        k = u / BREATH
        big = int(n) % BIG_EVERY == BIG_EVERY - 1
        if big:
            if k < 0.85:
                return 2 + ease_in_out(k / 0.85) * 11, False
            return 13, True
        return 1.5 + math.sin(k * math.pi) ** 2 * 4.5, False

    def furnace(self, g: Gfx, t: float):
        flame(g, 112, 52, 5, 5, t, self.seed)
        smoke_wisp(g, 112, 21, 18, t, self.seed, sway=2, speed=4, drift=4)

    def face(self, g: Gfx, t: float, dy: float, eyes: str = "shut", mouth: str = "o", look: float = 0.0):
        hx, hy = HC[0] - 22, HC[1] - 24 + dy
        g.blit(_A["head"], hx, hy)
        cx, cy = HC[0], HC[1] + dy
        for s in (-1, 1):
            ex, ey = cx + s * 8, cy + 3
            if eyes == "shut":   # ︶ 合眼
                g.d.arc((ex - 4, ey - 3, ex + 4, ey + 2), 20, 160, fill=1)
            elif eyes == "wide":  # 瞪圆
                g.d.ellipse((ex - 3, ey - 3, ex + 3, ey + 3), fill=1)
                g.d.rectangle((ex - 1 + look, ey - 1, ex + look, ey + 1), fill=0)
            else:                # 睁着（装认真）
                g.d.line((ex - 3, ey - 1, ex + 3, ey - 1), fill=1)
                g.d.rectangle((ex - 1 + look, ey, ex + look, ey + 1), fill=1)
        mx, my = cx, cy + 11
        if mouth == "o":
            g.d.ellipse((mx - 1, my - 1, mx + 1, my + 1), outline=1)
        elif mouth == "yawn":
            g.d.ellipse((mx - 3, my - 3, mx + 3, my + 3), fill=1)
            g.d.ellipse((mx - 2, my - 1, mx + 2, my + 2), fill=0)
        else:
            g.d.line((mx - 2, my, mx + 2, my), fill=1)

    def snot(self, g: Gfx, r: float, dy: float, pop: float = -1):
        """鼻涕泡：从鼻孔往右下鼓出去；pop>=0 时画破掉的水花"""
        nx, ny = HC[0] + 1, HC[1] + 7 + dy
        cx, cy = nx + 1 + r * 0.95, ny + 1 + r * 0.3
        if pop < 0:
            g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1, fill=0)
            if r > 3:  # 高光
                g.d.arc((cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2), 200, 250, fill=1)
            return
        for j in range(10):
            a = j / 10 * 2 * math.pi
            d = r * 0.6 + pop * 12
            g.px(cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8)
        if pop < 0.4:
            g.text(cx + 6, cy - 14, "啪", size=8)

    def mx_bubble(self, g: Gfx, r: float, pop: float = -1):
        if pop >= 0:
            d = 1 + pop * 4
            for j in range(8):
                a = j / 8 * 2 * math.pi
                g.mx_set(round(3.5 + math.cos(a) * d), round(3.5 + math.sin(a) * d))
            return
        rr = 0.6 + r / 13 * 3.4
        for y in range(8):
            for x in range(8):
                if abs(math.hypot(x - 3.5, y - 3.5) - rr) < 0.55:
                    g.mx[y, x] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        backdrop(g, _A["bg"])
        self.furnace(g, t)
        if t < 0.6:
            self.face(g, t, 0, "shut" if 0.35 < t < 0.45 else "open", "-", look=0)
        elif t < 1.5:     # 打个大哈欠
            self.face(g, t, -1, "shut", "yawn")
            g.text(HC[0] + 21, HC[1] + 4, "哈~", size=8)
        else:             # 眼皮一沉，泡泡冒出来
            self.face(g, t, 0, "shut", "o")
            r = 1.5 * ease_out_back(span(t, 1.9, 2.6))
            if r > 0.3:
                self.snot(g, r, 0)
        g.mx_rows([0, 0, 0x24, 0, 0, 0x18, 0, 0] if t < 1.5 else [0, 0, 0, 0x18, 0x18, 0, 0, 0])
        if t < 0.6:  # 画面从脸上展开
            iris(g, HC[0], HC[1] + 2, ease_out(t / 0.6) * 110, 0.8)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        backdrop(g, _A["bg"])
        self.furnace(g, t)
        shifu = ev(t, 113.0, 9.0, 40.0)      # 咳！师父来了
        if shifu:
            self.caught(g, t, shifu[1])
            return
        r, popping = self.bubble_r(t)
        dy = self.droop(t)
        u = (t % BREATH) / BREATH
        n = int(t // BREATH)
        just_popped = n % BIG_EVERY == 0 and n > 0 and u < 0.6    # 上一口气刚破：瞪眼左右看
        if popping:
            pk = (u - 0.85) / 0.15
            self.face(g, t, dy, "wide", "-")
            self.snot(g, 13, dy, pk)
            self.mx_bubble(g, 13, pk)
            g.mx_level = 4
        elif just_popped:
            look = -2 if u < 0.25 else 2 if u < 0.45 else 0
            self.face(g, t, dy, "wide", "-", look=look)
            g.mx_rows([0, 0x66, 0x66, 0, 0, 0x3C, 0, 0])
        else:
            self.face(g, t, dy, "shut", "o")
            self.snot(g, r, dy)
            self.mx_bubble(g, r)
        fly = ev(t, 71.0, 6.0, 15.0)         # 一只小飞虫绕着头转
        if fly and not popping:
            k = fly[1]
            a = k * 3.2
            fx = HC[0] + math.cos(a) * (26 - k * 2)
            fy = HC[1] - 4 + math.sin(a) * 14 + dy
            g.px(fx, fy)
            g.px(fx + 1, fy)
            w = int(t * 20) % 2
            g.px(fx - 1 + w, fy - 1)
            g.px(fx + 2 - w, fy - 1)

    def say(self, g: Gfx, s: str):
        """画外师父的声音（右上角，压住炉烟）"""
        g.d.rectangle((100, 0, 127, 15), fill=0)
        g.text(126, 3, s, align="right")

    def caught(self, g: Gfx, t: float, u: float):
        """师父一声咳：惊醒、坐直、睁眼装认真，慢慢又困了"""
        if u < 0.8:
            self.face(g, t, self.droop(t - u), "shut", "o")
            self.snot(g, self.bubble_r(t - u)[0], self.droop(t - u))
            self.say(g, "咳！")
            self.mx_bubble(g, 3)
            return
        if u < 1.2:
            self.face(g, t, -3, "wide", "-")
            self.snot(g, 6, -3, (u - 0.8) / 0.4)
            self.say(g, "咳！")
            g.mx_rows([0x18, 0x18, 0x18, 0x18, 0x18, 0, 0x18, 0x18])
            g.mx_level = 5
            return
        # 坐得笔直，眼珠左右瞟；然后眼皮越来越重
        heavy = span(u, 5.5, 8.6)
        dy = -2 + heavy * 2
        if heavy < 0.5:
            look = round(math.sin((u - 1.2) * 2.5) * 2)
            self.face(g, t, dy, "open", "-", look=look)
            g.mx_rows([0, 0x66, 0x66, 0, 0, 0x3C, 0, 0])
        else:
            self.face(g, t, dy, "shut", "o")
            self.snot(g, lerp(0.5, 1.5, heavy), dy)
            self.mx_bubble(g, 1.5)
        if u < 3.2:
            self.say(g, "……")

    def exit(self, g: Gfx, t: float):
        """醒了：泡泡一破，瞪眼，画面收拢"""
        h = self._ht
        backdrop(g, _A["bg"])
        self.furnace(g, h + t)
        dy = self.droop(h) * (1 - span(t, 0, 0.3))
        r = max(self.bubble_r(h)[0], 3)
        if t < 0.35:
            self.face(g, h, dy, "wide", "-")
            self.snot(g, r, dy, t / 0.35)
            self.mx_bubble(g, r, t / 0.35)
        else:
            self.face(g, h, dy, "wide", "-", look=0)
            g.text(HC[0] + 22, HC[1] - 20, "!", size=12)
            g.mx_rows([0, 0x66, 0x66, 0, 0, 0x3C, 0, 0])
        iris(g, HC[0], HC[1] + 2, lerp(110, 0, ease_in_out(span(t, 0.3, self.T["exit"] - 0.05))), 0.8)
