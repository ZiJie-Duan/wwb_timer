"""打盹冒泡：丹房里，小道士坐在蒲团上守着丹炉、手里一把团扇，扇着扇着就打起盹来，鼻涕泡一大一小。

依据：道观里看守丹炉的小道童（炼丹须昼夜看火，“文武火候”），团扇扇炉火；打盹冒鼻涕泡是漫画通用笑点（非典籍）。

入场：小道士扇着火，眨眨眼，打个大哈欠“哈”，眼皮一沉，鼻涕泡冒出来。
持续：右边三足丹炉（炉腹八卦纹、双耳、炉盖宝顶），炉下火苗跳、炉顶冒烟；后墙挂一幅太极挂轴，地上蒲团。
      他合着眼，鼻涕泡随呼吸一大一小（3.6 秒一口气）；头慢慢往下垂、垂到底猛地一点抬回来（9 秒一次）；
      团扇偶尔有气无力地扇一下。每第六口气泡泡越吹越大——“啪”破掉，他瞪眼一愣，又睡。
      小事件：一只小飞虫绕着头转，落到泡泡上，泡破（71s）；画外师父一声“咳！”——惊醒坐直、拼命扇火装认真，
      “……”，眼皮越来越重又睡过去（113s）。
退场：泡泡一破，瞪眼“！”，画面收拢。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import bang, cached, ev, iris, plate, pop, say

FLOOR = 56
MAN_X = 34
BREATH = 3.6
NOD = 9.0
EV = 160.0
FURN_X = 78


def _furnace():
    """三足丹炉 38×38：宝顶炉盖（盖上一圈镂孔）、立耳、鼓腹（中间太极、四周八卦短线）、三足兽面"""
    p = Part(38, 38)
    p.shape("rectangle", (17, 0, 20, 2), fill=1)                       # 宝顶
    p.px(18, 0, 0)
    p.shape("chord", (8, 2, 29, 14), 180, 360, fill=1)                 # 炉盖
    p.d.line((9, 8, 28, 8), fill=0)
    for x in range(12, 27, 4):                                         # 镂孔
        p.px(x, 6, 0), p.px(x + 1, 6, 0)
    p.shape("rectangle", (6, 9, 31, 10), fill=1)                       # 口沿
    p.shape("rectangle", (2, 6, 5, 13), fill=1), p.shape("rectangle", (32, 6, 35, 13), fill=1)   # 立耳
    p.px(3, 8, 0), p.px(3, 9, 0), p.px(34, 8, 0), p.px(34, 9, 0)
    p.shape("ellipse", (3, 9, 34, 32), fill=1)                         # 鼓腹
    p.d.line((5, 12, 32, 12), fill=0)
    cx, cy = 18, 21
    p.d.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=0)              # 太极
    p.d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), outline=1)
    p.d.pieslice((cx - 5, cy - 5, cx + 5, cy + 5), 90, 270, fill=1)
    p.d.ellipse((cx - 2, cy - 5, cx + 2, cy), fill=1)
    p.d.ellipse((cx - 2, cy, cx + 2, cy + 5), fill=0)
    p.px(cx, cy - 3, 0), p.px(cx, cy + 3, 1)
    for a in range(8):                                                 # 八卦短线
        ang = a * math.pi / 4
        x0, y0 = cx + math.cos(ang) * 9, cy + math.sin(ang) * 8
        x1, y1 = cx + math.cos(ang) * 11, cy + math.sin(ang) * 9.5
        p.d.line((x0, y0, x1, y1), fill=0)
    p.dither([(28, 14), (33, 20), (31, 28), (26, 31)], 0.5, 0)
    for x in (7, 17, 27):                                              # 三足（兽面足）
        p.shape("polygon", [(x, 30), (x + 4, 30), (x + 3, 37), (x + 1, 37)], fill=1)
        p.px(x + 2, 32, 0)
        p.shape("rectangle", (x - 1, 36, x + 5, 37), fill=1)
    return p.sprite()


def _scroll():
    """挂轴 14×26：天杆、挂绳、画心里一个太极、地杆两头轴"""
    p = Part(14, 26)
    p.d.line((4, 0, 7, -1), fill=1)
    p.shape("line", (3, 2, 7, 0), fill=1), p.shape("line", (10, 2, 7, 0), fill=1)
    p.shape("rectangle", (1, 2, 12, 23), fill=0)
    p.d.rectangle((1, 2, 12, 23), outline=1)
    p.d.rectangle((3, 5, 10, 20), outline=1)
    p.d.ellipse((4, 9, 9, 14), outline=1)
    p.d.pieslice((4, 9, 9, 14), 270, 450, fill=1)
    p.d.line((4, 17, 9, 17), fill=1)
    p.shape("rectangle", (0, 23, 13, 25), fill=1)
    return p.sprite()


def _cushion():
    """蒲团 26×5：扁圆，草编纹"""
    p = Part(26, 5)
    p.shape("ellipse", (0, 0, 25, 6), fill=1)
    for x in range(3, 23, 3):
        p.d.line((x, 2, x + 1, 4), fill=0)
    p.d.line((2, 4, 23, 4), fill=0)
    return p.sprite()


def _fan_arm(lift: int) -> Sprite:
    """拿团扇的手 20×16：宽袖往前，手握扇柄，圆扇面（亮边、暗面、一道扇骨、扇面上一朵云纹）。
    lift：0 扇子垂着 / 2、3 扇子扬起（扇一下）"""
    p = Part(20, 16)
    p.shape("polygon", [(0, 2), (4, 2), (9, 6), (9, 10), (2, 10), (0, 7)], fill=1)    # 袖
    p.d.line((8, 6, 8, 10), fill=0)
    p.dither([(2, 8), (8, 8), (8, 10), (2, 10)], 0.5, 0)
    p.shape("rectangle", (9, 7, 11, 9), fill=1)                                      # 手
    p.px(11, 7, 0)
    if lift:
        p.shape("line", (11, 7, 13, 4), fill=1)                                      # 扇柄
        cx, cy = 15, 1 + (3 - lift)
    else:
        p.shape("line", (11, 9, 13, 11), fill=1)
        cx, cy = 15, 11
    p.shape("ellipse", (cx - 4, cy - 4 + 3, cx + 4, cy + 4 + 3), fill=0)
    p.d.ellipse((cx - 4, cy - 1, cx + 4, cy + 7), outline=1)
    p.d.arc((cx - 2, cy + 1, cx + 2, cy + 5), 180, 360, fill=1)                      # 扇面云纹
    p.px(cx, cy + 3, 1)
    spr = p.sprite()
    spr.hand = (10, 8)
    return spr


FLAME = pix.frames("""
  #
 ##
####
#.##
---
 #
 ##
###
##.#
---
  #
 # #
 ###
#.##
""")

FLY = pix.frames("""
#.#
 #
---
. .
 #
""")


@register
class BubbleRest(Rest):
    id = "x1.bubble"
    name = "打盹冒泡"
    desc = "丹房里小道士守着丹炉打盹，鼻涕泡随呼吸一大一小，头一点一点；泡破惊醒、师父一声咳，又装认真"
    T = {"enter": 2.6, "exit": 1.2}

    # ------------------------------------------------------------ 背景

    def room(self, g: Gfx, t: float):
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        for x in range(0, 140, 14):
            g.d.line((x, FLOOR + 1, x - 6, 63), fill=1)
        pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
        pix.blit(g, cached("scroll", _scroll), 6, 4)
        pix.blit(g, cached("cush", _cushion), MAN_X - 13, FLOOR - 4)
        fx = FURN_X
        pix.blit(g, pix.anim(FLAME, t, 8), fx + 13, FLOOR - 7, outline=False)
        pix.blit(g, pix.anim(FLAME, t + 0.21, 7), fx + 22, FLOOR - 7, outline=False)
        pix.blit(g, cached("furn", _furnace), fx, FLOOR - 38)
        for i in range(3):                                      # 炉顶的烟
            k = ((t * 0.3 + i / 3) % 1)
            x = fx + 19 + math.sin(t * 0.9 + k * 6) * (1 + k * 4)
            y = FLOOR - 40 - k * 16
            r = 0.5 + math.sin(k * math.pi) * 1.4
            if k < 0.6:
                g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
            elif k < 0.85:
                g.d.ellipse((x - r, y - r, x + r, y + r), outline=1)
            else:
                g.px(x, y)

    # ------------------------------------------------------------ 状态（只依赖 t）

    def state(self, t: float):
        """返回 (面相, 头, 泡半径, 泡破的进度, 扇子抬起, 文字)"""
        cough = ev(t, EV, 113.0, 12.0)
        fly = ev(t, EV, 71.0, 9.0)
        b = t / BREATH
        n, ph = int(b), b % 1
        nod = t % NOD
        head, face, r, popk, lift, words = "up", "sleep", 0.0, None, 0, None
        r = 1.5 + math.sin(ph * math.pi) * 2.5
        if n % 6 == 5:   # 第六口气：越吹越大，啪
            r = 1.5 + ph * 7.0
            if ph > 0.82:
                popk = (ph - 0.82) / 0.18
                r = 0
                face = "wow"
        elif n % 6 == 0 and ph < 0.15 and n > 0:
            face, r = "wow", 0
        if nod > NOD - 1.6:
            head = "bow" if nod < NOD - 0.25 else "up"
            if head == "bow":
                r = 0
            else:
                face = "wow" if face == "sleep" else face
        if int(t * 0.7) % 4 == 0 and (t * 0.7) % 1 < 0.2:
            lift = 2
        if fly is not None and 5.0 <= fly < 5.6:   # 飞虫落到泡上：啪
            r, popk, face = 0, (fly - 5.0) / 0.6, "wow"
        elif fly is not None and 5.6 <= fly < 7.0:
            r, face = 0, "normal"
        if cough is not None:
            if cough < 0.5:
                popk, r, face = cough / 0.5, 0, "wow"
            elif cough < 7.0:
                r, face, head = 0, "normal" if cough < 4.5 else ("sleep" if (cough * 2) % 1 < 0.3 else "normal"), "up"
                lift = 3 if int(cough * 7) % 2 else 0
                if cough > 3.5:
                    words = "……"
            elif cough < 9.0:
                r, face, head = 0, "sleep" if (cough * 1.4) % 1 < 0.6 else "normal", "up"
                lift = 2 if int(cough * 2) % 2 else 0
            else:
                r = min(r, (cough - 9.0) * 1.5)
        return head, face, r, popk, lift, words, cough, fly

    def man(self, g: Gfx, t: float, head: str, face: str, lift: int):
        arm = cached(("fan", lift), lambda: _fan_arm(lift))
        return figure(g, MAN_X, FLOOR - 2, t, legs="sit", arm=arm, arm_at=(-2, -18), head=head, face=face)

    def nose(self):
        return MAN_X + 7, FLOOR - 2 - 34 + 13

    def hold(self, g: Gfx, t: float):
        self.draw(g, t)

    def draw(self, g: Gfx, t: float):
        self.room(g, t)
        head, face, r, popk, lift, words, cough, fly = self.state(t)
        self.man(g, t, head, face, lift)
        nx, ny = self.nose()
        if r >= 1 and head == "up":
            rr = int(round(r))
            g.d.ellipse((nx, ny - rr + 1, nx + 2 * rr, ny + rr + 1), fill=0, outline=1)
            if rr >= 3:
                g.px(nx + rr - 1, ny - rr + 3)
                g.px(nx + rr, ny - rr + 3)
        if popk is not None and popk < 1:
            pop(g, nx + 4, ny + 1, popk, 2)
        if face == "wow" and popk is not None:
            bang(g, MAN_X + 9, FLOOR - 50)
        if fly is not None:
            self.fly(g, t, fly, nx, ny)
        if cough is not None and cough < 2.0:      # 画外师父一声“咳！”
            if cough < 0.3:
                pix.shake(g, t, 1.0)
            plate(g, 3, 4, "咳！", k=span(cough, 0, 0.2))
        if words:
            say(g, MAN_X - 6, FLOOR - 54, words, 1.0)
        self.matrix(g, t, r, popk, face)

    def fly(self, g: Gfx, t: float, f: float, nx: float, ny: float):
        """小飞虫绕头转三圈，落在泡上（泡破），再飞走"""
        if f < 5.0:
            a = f * 3.2
            x = MAN_X + 2 + math.cos(a) * 14
            y = FLOOR - 42 + math.sin(a) * 6
            if f > 4.0:
                q = f - 4.0
                x, y = lerp(x, nx + 6, q), lerp(y, ny - 4, q)
        elif f < 5.6:
            x, y = nx + 6, ny - 3
        else:
            q = (f - 5.6) / 3.4
            x, y = nx + 6 + q * 70, ny - 3 - q * 30 + math.sin(q * 20) * 2
        pix.blit(g, FLY[int(t * 14) % 2], x - 1, y - 1, outline=False)

    def matrix(self, g: Gfx, t: float, r: float, popk, face: str):
        if popk is not None and popk < 1:
            rr = 2 + popk * 3
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - rr) < 0.6:
                        g.mx[y, x] = True
            g.mx_level = 4
            return
        if face in ("wow", "normal"):
            g.mx_rows([0x3C, 0x42, 0xA5, 0xA5, 0x81, 0x99, 0x42, 0x3C])
            return
        rr = max(0.6, r / 7 * 3.5)
        for y in range(8):
            for x in range(8):
                if abs(math.hypot(x - 3.5, y - 3.5) - rr) < 0.55:
                    g.mx[y, x] = True
        if rr < 1.2:
            g.mx[3:5, 3:5] = True

    # ------------------------------------------------------------ 入场 / 退场

    def enter(self, g: Gfx, t: float):
        """扇着火 → 眨眼 → 大哈欠“哈” → 眼皮一沉 → 冒泡"""
        self.room(g, t)
        if t < 0.8:
            face, lift = ("sleep" if 0.35 < t < 0.5 else "normal"), (3 if int(t * 8) % 2 else 0)
        elif t < 1.7:
            face, lift = "wow", 0
        else:
            face, lift = "sleep", 0
        self.man(g, t, "up", face, lift)
        if 0.8 <= t < 1.7:
            plate(g, MAN_X + 14, 6, "哈", k=span(t, 0.8, 1.0))
        if t > 1.9:
            nx, ny = self.nose()
            rr = int(round(span(t, 1.9, 2.6) * 3)) + 1
            g.d.ellipse((nx, ny - rr + 1, nx + 2 * rr, ny + rr + 1), fill=0, outline=1)
        self.matrix(g, t, 1.0, None, face if t < 1.7 else "sleep")
        iris(g, MAN_X + 2, FLOOR - 26, lerp(6, 150, ease_out(span(t, 0, 1.0))))

    def exit(self, g: Gfx, t: float):
        h0 = self.hold_t
        self.room(g, h0 + t)
        self.man(g, h0 + t, "up", "wow" if t > 0.2 else "sleep", 0)
        nx, ny = self.nose()
        if t < 0.35:
            pop(g, nx + 4, ny + 1, t / 0.35, 2)
        else:
            bang(g, MAN_X + 9, FLOOR - 50)
        self.matrix(g, t, 0, t / 0.35 if t < 0.35 else None, "wow")
        iris(g, MAN_X + 2, FLOOR - 24, lerp(140, 0, ease_in_out(span(t, 0.35, self.T["exit"] - 0.05))))
