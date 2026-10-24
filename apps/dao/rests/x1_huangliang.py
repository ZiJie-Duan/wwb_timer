"""黄粱一梦：邸舍里，小道士枕着青瓷枕仰卧榻上，梦泡里走马灯演完一生，醒来锅里的黄粱还没蒸熟。

依据：唐·沈既济《枕中记》：吕翁“探囊中枕以授之，曰：‘子枕吾枕，当令子荣适如志。’”“时主人方蒸黍。”
卢生梦中“举进士，登第”，“出拥节旌，入升台辅”，“封燕国公”，“年逾八十”；“卢生欠伸而悟，见其身方偃于邸舍，
吕翁坐其傍，主人蒸黍未熟，触类如故。”后世吕翁附会为吕洞宾。

入场：小道士坐在榻上，一只宽袖从右上递来青瓷枕，枕头落在榻上一弹；他躺倒，头上冒出三个小泡、梦泡鼓起。
持续（一轮 40 秒）：左边木榻（雕花榻沿、榻腿），他枕青瓷枕仰卧、随呼吸起伏；右边砖灶，灶口火苗跳，
      釜上冒蒸汽，锅盖不时被顶得一跳；后墙一扇格子窗。梦泡里走马灯（每段 6 秒）：
      金榜展开“登第”→ 帅旗猎猎“出将”→ 乌纱帽两翅颤颤“入相”→ 元宝一个个落下摞起“封公”→ 蜡烛烧短“八十”；
      梦泡发抖、“啪”地破掉 → 他惊坐起“！”，望着灶，“黍未熟”→ 又躺回去，梦泡再起。
退场：梦泡破，他坐起“！”，画面收拢到他身上。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, _head, daoshi
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Canvas, bang, bubble, cached, iris, plate, pop, zzz

FLOOR = 58
BED_Y = 45          # 榻面
MAN_X = 8           # 后脑处
CYCLE = 40.0
SEG = 6.0
POP_AT = 30.0
LIE_AT = 36.0
BUB = (52, 17)      # 梦泡中心
BUB_R = 15
LABELS = ["登第", "出将", "入相", "封公", "八十"]
STOVE_X = 86


def _bed():
    """木榻 62×14：榻面一条亮边，榻沿雕一排如意云头（暗心亮边），四条弯腿"""
    p = Part(62, 14)
    p.shape("rectangle", (0, 0, 61, 2), fill=1)
    p.d.line((1, 1, 60, 1), fill=0)
    p.shape("rectangle", (1, 3, 60, 8), fill=0)
    p.d.rectangle((1, 3, 60, 8), outline=1)
    for x in range(5, 58, 8):                          # 如意云头
        p.d.arc((x - 2, 4, x + 2, 8), 180, 360, fill=1)
        p.px(x, 6, 1)
    for x in (2, 57):                                  # 腿：外撇的马蹄足
        p.shape("rectangle", (x, 9, x + 2, 12), fill=1)
        p.px(x - 1 if x < 30 else x + 3, 13, 1)
        p.px(x if x < 30 else x + 2, 13, 1)
    p.shape("rectangle", (29, 9, 31, 12), fill=1)
    return p.sprite()


def _pillow():
    """青瓷枕 16×6：两头微翘的长方枕，暗釉面上一道卷草纹，左上一点高光"""
    p = Part(16, 6)
    p.shape("polygon", [(0, 0), (3, 1), (12, 1), (15, 0), (15, 5), (0, 5)], fill=1)
    for x in range(2, 14, 4):                          # 卷草纹
        p.d.arc((x, 2, x + 3, 5), 180, 360, fill=0)
        p.px(x + 1, 4, 0)
    p.d.line((1, 5, 14, 5), fill=0)
    return p.sprite()


def _stove():
    """砖灶 38×24：错缝砖纹（暗底亮缝）、拱形灶门、灶台面一条亮边、烟囱在后"""
    p = Part(38, 24)
    p.shape("rectangle", (0, 2, 37, 23), fill=0)
    p.d.rectangle((0, 2, 37, 23), outline=1)
    p.d.line((0, 3, 37, 3), fill=1)
    for r, y in enumerate(range(6, 23, 3)):            # 砖缝
        p.d.line((1, y, 36, y), fill=1)
        for x in range(2 + (r % 2) * 3, 36, 6):
            p.d.line((x, y - 2, x, y - 1), fill=1)
    p.shape("rectangle", (12, 12, 25, 23), fill=0)     # 灶门
    p.d.arc((12, 9, 25, 18), 180, 360, fill=1)
    p.d.line((12, 13, 12, 23), fill=1), p.d.line((25, 13, 25, 23), fill=1)
    p.shape("rectangle", (13, 14, 24, 23), fill=0)
    p.d.line((14, 22, 23, 22), fill=1)                 # 柴
    p.d.line((15, 21, 20, 20), fill=1)
    return p.sprite()


def _pot():
    """釜 22×9：圆底大锅，暗身亮边，两只耳，口沿一道亮线"""
    p = Part(22, 9)
    p.shape("chord", (1, -6, 20, 9), 0, 180, fill=0)
    p.d.arc((1, -6, 20, 9), 0, 180, fill=1)
    p.shape("rectangle", (0, 0, 21, 1), fill=1)
    p.d.line((2, 3, 19, 3), fill=1)
    p.px(0, 2), p.px(21, 2)
    p.dither([(4, 4), (17, 4), (14, 7), (7, 7)], 0.25, 1)
    return p.sprite()


def _lid():
    """锅盖 18×4：木盖，中间提钮"""
    p = Part(18, 4)
    p.shape("rectangle", (7, 0, 10, 1), fill=1)
    p.shape("polygon", [(0, 3), (3, 1), (14, 1), (17, 3)], fill=1)
    p.d.line((3, 2, 14, 2), fill=0)
    return p.sprite()


def _quilt(breath: bool) -> Sprite:
    """被子 42×11：从下巴盖到脚，胸口隆起（吸气高 1 像素）、膝头一个包、脚头一个包；
    滚边一道暗线、被面碎花（暗点）、贴榻一侧网点"""
    p = Part(42, 11)
    b = 1 if breath else 0
    p.shape("polygon", [(0, 5), (3, 2 - b), (12, 1 - b), (17, 3), (25, 4), (29, 3), (33, 4), (36, 2), (40, 3), (41, 7),
                        (41, 10), (0, 10)], fill=1)
    p.d.line((2, 4 - b, 2, 10), fill=0)                 # 被头滚边
    p.d.line((4, 3 - b, 4, 10), fill=0)
    for i, (x, y) in enumerate(((8, 5), (14, 6), (20, 7), (11, 8), (26, 7), (31, 7), (37, 6), (23, 5), (17, 9),
                                (34, 9))):
        p.px(x, y - (b if x < 15 else 0), 0)
        if i % 2 == 0:
            p.px(x + 1, y + 1 - (b if x < 15 else 0), 0)
    p.d.line((1, 10, 40, 10), fill=0)
    p.dither([(6, 9), (40, 9), (40, 10), (6, 10)], 0.5, 0)
    return p.sprite()


def _window():
    """格子窗 22×18：窗框 + 冰裂格"""
    p = Part(22, 18)
    p.shape("rectangle", (0, 0, 21, 17), fill=0)
    p.d.rectangle((0, 0, 21, 17), outline=1)
    p.d.rectangle((2, 2, 19, 15), outline=1)
    for x in (6, 10, 15):
        p.d.line((x, 2, x, 15), fill=1)
    for y in (6, 11):
        p.d.line((2, y, 19, y), fill=1)
    p.d.rectangle((8, 7, 12, 10), fill=0, outline=1)   # 中间一个回字格
    p.px(10, 8, 1)
    return p.sprite()


SLEEVE = pix.sprite("""
      ##########
   ##############
 ###.###########
###.####.######
##.####.######.
#.####.#####..
#..##.####..
 ##..###..
  ###..
""")
"""吕翁伸来的宽袖（袖口朝左下，几道衣褶）"""

FIRE = pix.frames("""
  #
 ##  #
 ### #
#######
---
   #
 # ##
 ####
#######
---
 #
 ## #
#####
#######
""")

INGOT = pix.sprite("""
 #######
##.#####
#########
""")

HAT = pix.frames("""
       #####
      #######
#     #.....#     #
###################
#    #########    #
      #.....#
      #######
---
       #####
      #######
      #.....#
###################
     #########
      #.....#
      #######
""")

FLAG = pix.frames("""
.#.
###########
#.........###
#..###.....##
#.#...#...###
#.#...#.....##
#..###....###
#........##
##########
#
#
#
#
#
#
---
.#.
##########
#........###
#..###.....##
#.#...#....###
#.#...#......#
#..###.....##
#.........##
###########
#
#
#
#
#
#
""")

CANDLE = pix.sprite("""
###
#.#
###
""")

SMALL_FLAME = pix.frames("""
 #
###
---
#
 ##
""")


class Dream:
    """梦泡里的五段（每段 6 秒）：画在以 (cx, cy) 为中心的小框里"""

    @staticmethod
    def draw(g: Gfx, i: int, k: float, cx: int, cy: int, t: float):
        if i == 0:     # 金榜：卷轴从中间往两边展开，里面几行名字，有一行在闪
            w = int(10 * ease_out(span(k, 0, 1.2)))
            g.d.rectangle((cx - w - 1, cy - 8, cx + w + 1, cy + 6), fill=0, outline=1)
            g.d.line((cx - w - 2, cy - 9, cx - w - 2, cy + 7), fill=1)
            g.d.line((cx + w + 2, cy - 9, cx + w + 2, cy + 7), fill=1)
            for j in range(4):
                if w > 3:
                    yy = cy - 5 + j * 3
                    if j == 1 and int(t * 4) % 2:
                        g.d.rectangle((cx - w + 2, yy - 1, cx + w - 2, yy + 1), fill=1)
                    else:
                        pix.dotted(g, cx - w + 2, yy, cx + w - 2, yy, 2, j)
        elif i == 1:   # 帅旗：旗杆 + 猎猎的旗
            pix.blit(g, FLAG[int(t * 5) % 2], cx - 6, cy - 9)
        elif i == 2:   # 乌纱帽：两翅颤颤
            pix.blit(g, HAT[int(t * 6) % 2], cx - 9, cy - 4)
        elif i == 3:   # 元宝一个个落下摞起
            n = min(5, int(k / 1.0) + 1)
            spots = [(-5, 6), (5, 6), (0, 3), (-5, 0), (5, 0)]
            for j in range(n):
                dx, dy = spots[j]
                q = span(k, j * 1.0, j * 1.0 + 0.5)
                yy = lerp(cy - 14, cy + dy, ease_in(q))
                pix.blit(g, INGOT, cx + dx - 4, yy - 2)
                if j == n - 1 and 0.4 < q < 1:
                    g.px(cx + dx - 5, yy - 2), g.px(cx + dx + 5, yy - 2)
        else:          # 蜡烛烧短
            h = int(lerp(13, 3, k / SEG))
            g.d.rectangle((cx - 2, cy + 7 - h, cx + 2, cy + 7), fill=1)
            g.d.line((cx + 1, cy + 8 - h, cx + 1, cy + 6), fill=0)
            g.px(cx - 2, cy + 8 - h, 0)
            g.d.line((cx - 5, cy + 8, cx + 5, cy + 8), fill=1)
            pix.blit(g, SMALL_FLAME[int(t * 6) % 2], cx - 1, cy + 4 - h)
            for j in range(3):                       # 烛泪
                if h < 13 - j * 3:
                    g.px(cx - 3 + j * 3, cy + 7 - j)


@register
class HuangLiangRest(Rest):
    id = "x1.huangliang"
    name = "黄粱一梦"
    desc = "邸舍里小道士枕青瓷枕仰卧，梦泡里走马灯演一生（登第、出将、入相、封公、八十），梦破惊醒，灶上黄粱还没熟"
    T = {"enter": 3.4, "exit": 1.3}

    # ------------------------------------------------------------ 背景

    def room(self, g: Gfx, t: float, lid_hop: float = 0.0):
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        for x in range(4, 128, 12):                        # 地砖缝
            g.d.line((x, FLOOR + 1, x - 4, 63), fill=1)
        pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
        g.d.line((0, 34, 3, 34), fill=1), g.d.line((124, 34, 127, 34), fill=1)
        pix.blit(g, cached("win", _window), 100, 2)
        pix.blit(g, cached("bed", _bed), 2, BED_Y)
        sx = STOVE_X
        pix.blit(g, cached("stove", _stove), sx, FLOOR - 23)
        pix.blit(g, pix.anim(FIRE, t, 7), sx + 15, FLOOR - 7, outline=False)
        if int(t * 5) % 3 == 0:
            g.px(sx + 18, FLOOR - 9)
        pix.blit(g, cached("pot", _pot), sx + 3, FLOOR - 32)
        # 锅盖：每 9 秒被蒸汽顶得一跳
        hop = (t % 9.0)
        dy = -int(round(math.sin(min(hop, 0.4) / 0.4 * math.pi) * 3)) if hop < 0.4 else 0
        pix.blit(g, cached("lid", _lid), sx + 5, FLOOR - 35 + dy)
        self.steam(g, t, hop < 1.2)

    def steam(self, g: Gfx, t: float, burst: bool):
        """两缕蒸汽：小团从锅盖边冒出、往上飘、变成空心圈、散成点（只依赖 t）"""
        for j, x0 in enumerate((STOVE_X + 7, STOVE_X + 19)):
            n = 8 if burst else 6
            for i in range(n):
                k = ((t * 0.35 + i / n + j * 0.09) % 1)
                x = x0 + math.sin(t * 1.1 + k * 7 + j * 2) * (1 + k * 3)
                y = FLOOR - 37 - k * 24
                r = 0.5 + math.sin(k * math.pi) * 1.2
                if k < 0.55:
                    g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
                elif k < 0.85:
                    g.d.ellipse((x - r, y - r, x + r, y + r), outline=1)
                else:
                    g.px(x - 1, y), g.px(x + 1, y - 1)

    # ------------------------------------------------------------ 人与梦

    def sleeper(self, g: Gfx, t: float, face: str = "sleep"):
        """枕着青瓷枕、盖着被子睡：头靠在枕上（脸朝外），被子随呼吸起伏"""
        breath = (t / 3.6) % 1 < 0.5
        pix.blit(g, cached("pillow", _pillow), MAN_X - 2, BED_Y - 6)
        pix.blit(g, cached(("quilt", breath), lambda: _quilt(breath)), MAN_X + 13, BED_Y - 11)
        hd = cached(("head", face), lambda: _head(False, 0, False, "sleep" if face == "snore" else face)[0])
        pix.blit(g, hd, MAN_X - 2, BED_Y - 20)
        if face == "snore":
            g.d.rectangle((MAN_X + 8, BED_Y - 7, MAN_X + 9, BED_Y - 6), fill=0)
        return {"mouth": (MAN_X + 9, BED_Y - 6), "head": (MAN_X + 6, BED_Y - 20)}

    def sitter(self, g: Gfx, t: float, face: str = "wow"):
        """惊坐起：被子滑到腿上"""
        pix.blit(g, cached("pillow", _pillow), MAN_X - 2, BED_Y - 6)
        daoshi(g, MAN_X + 16, BED_Y, "sit", t, face=face)
        pix.blit(g, cached(("quilt", False), lambda: _quilt(False)), MAN_X + 13, BED_Y - 6)

    def dream(self, g: Gfx, k: float, t: float, grow: float = 1.0, shake: float = 0.0):
        """梦泡 + 里面的一段 + 泡边的小泡；返回当前段号"""
        cx, cy = BUB
        r = BUB_R * grow
        if shake:
            cx += int(round(math.sin(t * 40) * shake))
            r += math.sin(t * 25) * shake * 0.6
        hx, hy = MAN_X + 16, BED_Y - 19                   # 头顶冒出的小泡串，连到梦泡
        for i, rr in enumerate((1, 1, 2)):
            x, y = hx + 2 + i * 4, hy - 2 - i * 3
            g.d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=1, fill=0)
        if r < 2:
            return -1
        bubble(g, cx, cy, r)
        seg = int(k // SEG) if k < POP_AT else 4
        if grow >= 0.99 and k < POP_AT:
            Dream.draw(g, seg, k - seg * SEG, cx, cy + 1, t)
        return seg

    def hold(self, g: Gfx, t: float):
        k = t % CYCLE
        self.room(g, t)
        lab = None
        if k < POP_AT:
            h = self.sleeper(g, t)
            shake = span(k, POP_AT - 4, POP_AT) * 1.6
            seg = self.dream(g, k, t, 1.0, shake)
            if k - seg * SEG > 0.6:
                lab = LABELS[seg]
            zzz(g, h["head"][0] - 6, h["head"][1] - 1, t, n=2, period=3.0, dx=-4, dy=-10, on=0.7)
        elif k < LIE_AT:
            if k < POP_AT + 0.6:
                h = self.sleeper(g, t, face="wow")
                pop(g, BUB[0], BUB[1], span(k, POP_AT, POP_AT + 0.6), BUB_R)
            else:
                self.sitter(g, t, face="wow" if k < POP_AT + 2.0 else "normal")
                if k < POP_AT + 2.0:
                    bang(g, MAN_X + 26, BED_Y - 46)
        else:
            h = self.sleeper(g, t)
            if k < LIE_AT + 0.4:       # 躺回去扬起一点灰
                for i in range(3):
                    g.px(MAN_X + 18 + i * 10, BED_Y - 2 - span(k, LIE_AT, LIE_AT + 0.4) * 3)
            grow = ease_out_back(span(k, CYCLE - 2.5, CYCLE))
            self.dream(g, 0.0, t, grow)
            zzz(g, h["head"][0] - 6, h["head"][1] - 1, t, n=2, period=3.0, dx=-4, dy=-10, on=0.7)
        if lab:
            plate(g, BUB[0] + BUB_R + 6, 4, lab, k=span(k % SEG, 0.6, 0.9))
        if POP_AT + 2.0 <= k < LIE_AT:
            plate(g, 60, 4, "黍未熟", k=span(k, POP_AT + 2.0, POP_AT + 2.4))
        self.matrix(g, t, k)

    def matrix(self, g: Gfx, t: float, k: float):
        if POP_AT <= k < POP_AT + 2.0:
            g.mx_rows([0x18, 0x18, 0x18, 0x18, 0x18, 0x00, 0x18, 0x18])
            g.mx_level = 5
            return
        g.mx[7, 1:7] = True                              # 灶
        g.mx[6, 1] = g.mx[6, 6] = True
        g.mx[5, 0:8] = True                              # 锅沿
        g.mx[4, 1:7] = True
        g.mx[4, 2:6] = (t * 6) % 1 < 0.5 and False or g.mx[4, 2:6]
        for j, col in enumerate((2, 5)):                 # 蒸汽往上飘
            y = 3 - int(((t * 0.9 + j * 0.5) % 1) * 4)
            g.mx_set(col + (1 if (t + j) % 1 < 0.5 else 0), y)

    # ------------------------------------------------------------ 入场 / 退场

    def enter(self, g: Gfx, t: float):
        """坐在榻上 → 宽袖递来青瓷枕，落在榻上一弹 → 躺倒 → 冒小泡、梦泡鼓起"""
        self.room(g, t)
        if t < 1.8:
            daoshi(g, MAN_X + 16, BED_Y, "sit", t, face="normal")
            q = span(t, 0.0, 1.0)
            sx, sy = lerp(130, 74, ease_out(q)), lerp(-10, 12, ease_out(q))   # 吕翁的宽袖从右上伸进来
            if t > 1.3:
                sx, sy = lerp(74, 130, ease_in(span(t, 1.3, 1.8))), lerp(12, -10, ease_in(span(t, 1.3, 1.8)))
            g.d.polygon([(sx + 8, sy - 6), (sx + 40, sy - 30), (sx + 52, sy - 20), (sx + 16, sy + 2)], fill=1)
            g.d.line((sx + 14, sy - 6, sx + 42, sy - 27), fill=0)
            pix.blit(g, SLEEVE, sx - 2, sy - 6)
            if t < 1.0:
                pix.blit(g, cached("pillow", _pillow), sx - 12, sy + 3)
            else:                       # 枕头抛到榻头，落下一弹
                q2 = span(t, 1.0, 1.6)
                y = lerp(15, BED_Y - 6, ease_in(min(q2 * 1.25, 1))) - math.sin(q2 * math.pi) * 8
                if q2 > 0.8:
                    y -= math.sin((q2 - 0.8) / 0.2 * math.pi) * 2
                pix.blit(g, cached("pillow", _pillow), lerp(62, MAN_X - 2, q2), y)
        else:
            self.sleeper(g, t)
            grow = ease_out_back(span(t, 2.4, 3.4))
            self.dream(g, 0.0, t, grow)
        self.matrix(g, t, 0.0)
        iris(g, 40, 30, lerp(6, 150, ease_out(span(t, 0, 1.0))))

    def exit(self, g: Gfx, t: float):
        h0 = self.hold_t
        self.room(g, h0 + t)
        if t < 0.4:
            self.sleeper(g, h0 + t, face="wow")
            pop(g, BUB[0], BUB[1], span(t, 0, 0.4), BUB_R)
        else:
            self.sitter(g, h0 + t, face="wow")
            bang(g, MAN_X + 26, BED_Y - 46)
        self.matrix(g, h0, POP_AT + 0.5)
        iris(g, MAN_X + 16, BED_Y - 20, lerp(140, 0, ease_in_out(span(t, 0.45, self.T["exit"] - 0.05))))
