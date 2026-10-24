"""蝉蜕：老树干上趴着一只大蝉，一阵一阵地唱；树下小道士盘坐听蝉，听着听着打起瞌睡。

依据：《史记·屈原贾生列传》“蝉蜕于浊秽，以浮游尘埃之外”；道教以蝉蜕喻尸解——脱去旧壳，羽化而去
      （《抱朴子·论仙》“下士先死后蜕，谓之尸解仙”）。
入场：蝉振翅从右上飞来，落在树干上收翅；左上“蝉蜕于浊秽”。
持续：背面看的大蝉（凸出的复眼、前胸、帐篷状透明翅与翅脉），一阵一阵地叫：腹部抖动、两侧声波一圈圈荡开，
      歇一歇再叫；下面挂着一只空蝉蜕；树叶轻摆，地上有草。小道士盘坐，呼吸眨眼。
      每 100 秒一轮彩蛋：
        20 秒起 小道士听着听着打瞌睡（头一点一点，冒 z），40 秒一片叶子飘下来落在他头上，他“哇”地惊醒，
                愣一会儿，抬手把叶子拂掉；
        60 秒起 金蝉脱壳：老蝉张翅飞走 → 旧壳掉到地上 → 一只若虫从树根慢慢爬上来 → 背上裂开，
                嫩白的新蝉一点点钻出来、皱翅慢慢伸长、颜色变深 → 爬到高处接着唱，新的空壳留在原处；
                左上写“金蝉脱壳”。
收场：蝉张翅飞走。
点阵：唱歌时是跳动的声柱；不唱时是蝉；脱壳时是空壳 / 新蝉。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, span
from ..engine.chars import daoshi, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x4_common import TUFT, ev, label, mx_art, sound_arcs, tuft

FLOOR = 60
TX0, TX1 = 68, 96          # 树干左右
CX = 82                    # 蝉的中线
SING_Y = 9                 # 唱歌时蝉（精灵顶）的位置
SHELL_Y = 36               # 空壳（精灵顶）
DAO_X = 36
PERIOD = 100.0
DOZE = (20.0, 35.0)        # 打瞌睡 + 落叶
MOLT = (60.0, 32.0)        # 脱壳
SING_P = 9.0               # 一阵唱 5.5 秒、歇 3.5 秒

CIC = Sprite("""
 ##             ##
#..#############..#
#..######.######..#
 ##.###########.##
   .............
  ###############
 #######.#.#######
 ##.####.#.####.##
  ###############
   #.#########.#
  #..#.#####.#..#
 #...#..###..#...#
 #.#..#..#..#..#.#
 #.#...#.#.#...#.#
 #..#...###...#..#
 #..#....#....#..#
 #...#...#...#...#
  #..#...#...#..#
  #...#..#..#...#
   #..#..#..#..#
    #..#.#.#..#
     ##.# #.##
       #   #
""")


def _variants():
    """唱歌时腹部抖动的一帧；刚钻出来的新蝉（只有轮廓）；半熟（网点）"""
    on, mk = CIC.on.copy(), CIC.mask.copy()
    sing = on.copy()
    sing[11:20, 7:12] = on[11:20, 7:12] ^ (mk[11:20, 7:12] & (np.arange(9)[:, None] % 2 == 0))  # 腹部抖动
    # 新蝉：嫩白（整只亮），只留复眼、头胸分界与翅缝；半熟：翅上网点
    pale = mk.copy()
    pale[0:5] = on[0:5]
    pale[9:, 9] = False
    ys, xs = np.mgrid[0:mk.shape[0], 0:mk.shape[1]]
    half = on | (mk & ((xs + ys) % 2 == 0) & (ys > 9))
    return (Sprite(on=sing, mask=mk.copy()), Sprite(on=pale, mask=mk.copy()), Sprite(on=half, mask=mk.copy()))


CIC_SING, CIC_PALE, CIC_HALF = _variants()

SHELL = pix.frames("""
     #####
    #.###.#
 #  #######  #
  #.#######.#
 ##.##.#.##.##
#  .#.#.#.#.  #
  #.#.#.#.#.#
 #.#.#.#.#.#.#
#  #.#.#.#.#  #
   .#.#.#.#.
    #.#.#.#
    .#.#.#.
     #.#.#
      .#.
---
     #####
    #.###.#
  # ####### #
 #.#######.#
 ##.##.#.##.##
  #.#.#.#.#.#
#  #.#.#.#.#  #
 #.#.#.#.#.#.#
   #.#.#.#.#
 #  .#.#.#.  #
    #.#.#.#
    .#.#.#.
     #.#.#
      .#.
---
     #####
    #.#.#.#
 #  ##...##  #
  #.#.....#.#
 ##.#.....#.##
#  .#.....#.  #
  #.#.#.#.#.#
 #.#.#.#.#.#.#
#  #.#.#.#.#  #
   .#.#.#.#.
    #.#.#.#
    .#.#.#.
     #.#.#
      .#.
""")
NYMPH = SHELL[:2]
EMPTY = SHELL[2]

FLY = pix.frames("""
 ###           ###
#####         #####
######  ###  ######
 ######.###.######
  ######...######
  ###.#######.###
   ##.##.#.##.##
       #.#.#
       .#.#.
        #.#
---
       ##.##
   ## #######  ##
 ######.###.######
#######.#.#.#######
 ####  .###.  ####
  ##   #.#.#   ##
       .#.#.
        #.#
""")

LEAF = pix.frames("""
  ##
 #.##
#.###
 ##.#
   #
---
 ##
##.#
#.##
 #.#
  #
""")

ZZZ = pix.sprite("""
####
  #
 #
####
""")

MX_CIC = [" #    # ", "########", " ###### ", "  ####  ", " #.##.# ", "#..##..#", " #.##.# ", "  #  #  "]
MX_SHELL = ["   ##   ", "  ####  ", "## ## ##", " ###### ", "# #### #", " ###### ", "#  ##  #", "   ##   "]


def _trunk() -> Sprite:
    """老树干：两边起伏的轮廓、竖向树皮纹、一个树疤；底部树根外撇"""
    w, h = TX1 - TX0 + 13, 64
    on = np.zeros((h, w), bool)
    mk = np.zeros((h, w), bool)
    import random
    r = random.Random(7)
    lo = [6 + int(round(math.sin(y * 0.21) * 0.8 + math.sin(y * 0.07 + 1) * 0.6)) for y in range(h)]
    hi = [6 + (TX1 - TX0) + int(round(math.sin(y * 0.17 + 2) * 0.8)) for y in range(h)]
    for y in range(52, h):  # 树根外撇
        k = (y - 52) / 8
        lo[y] -= int(k * k * 6)
        hi[y] += int(k * k * 6)
    for y in range(h):
        a, b = max(lo[y], 0), min(hi[y], w - 1)
        mk[y, a:b + 1] = True
        on[y, a] = on[y, b] = True
        on[y, a + 1] = y % 5 != 0
    # 树皮纹：几条竖线，断断续续
    for i, x in enumerate((9, 12, w - 10, w - 13, 18, w - 19)):
        y = r.randrange(0, 6)
        while y < h - 4:
            ln = r.randrange(3, 9) if i < 4 else r.randrange(2, 4)
            if y < 44 and (i >= 4 or y < 40):  # 蝉趴、爬、挂壳的上半段留干净，树皮纹只在下半段
                y += 6
                continue
            xx = x + (1 if (y // 9 + i) % 3 == 0 else 0)
            on[y:min(y + ln, h), xx] = True
            y += ln + r.randrange(2, 5)
    # 树疤
    cx, cy = 14, 48
    for a in range(0, 360, 20):
        on[int(cy + math.sin(math.radians(a)) * 2.5), int(cx + math.cos(math.radians(a)) * 2)] = True
    on[cy, cx] = False
    on[np.where(~mk)] = False
    return Sprite(on=on, mask=mk)


TRUNK = _trunk()
_CROPS: dict = {}


def _crumple(spr: Sprite, wl: float) -> Sprite:
    """皱翅：头胸（前 9 行）不变，翅膀那截按 wl 压短"""
    wl = round(wl, 1)
    key = ("c", id(spr), wl)
    c = _CROPS.get(key)
    if c is None:
        from PIL import Image
        n = max(2, int(round((spr.h - 9) * wl)))
        lo_on = np.array(Image.fromarray(spr.on[9:]).resize((spr.w, n), Image.NEAREST))
        lo_mk = np.array(Image.fromarray(spr.mask[9:]).resize((spr.w, n), Image.NEAREST))
        c = _CROPS[key] = Sprite(on=np.vstack([spr.on[:9], lo_on]), mask=np.vstack([spr.mask[:9], lo_mk]))
    return c


def _crop(spr: Sprite, n: int) -> Sprite:
    """精灵只取上面 n 行（从壳里钻出来的那一截）"""
    key = (id(spr), n)
    c = _CROPS.get(key)
    if c is None:
        c = _CROPS[key] = Sprite(on=spr.on[:n].copy(), mask=spr.mask[:n].copy())
    return c


def branch(g: Gfx, t: float):
    """右上一根枝条，挂几片叶子（随风轻摆）"""
    pts = [(TX1 - 2, 15), (104, 11), (114, 8), (127, 6)]
    g.d.line(pts, fill=1)
    g.d.line([(TX1 - 2, 16), (104, 12)], fill=1)
    g.d.line([(110, 9), (116, 3), (120, 0)], fill=1)
    for i, (x, y) in enumerate(((104, 12), (112, 9), (119, 7), (126, 6), (116, 3))):
        k = int(t * 0.9 + i * 0.6) % 2
        pix.blit(g, LEAF[k], x - 2, y + 1)


@register
class Cicada(Rest):
    id = "x4.cicada"
    name = "蝉蜕"
    desc = "老树干上一只大蝉一阵阵鸣唱，树下小道士听着打瞌睡；不时演一回金蝉脱壳"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.tufts = [(8, 0), (24, 1), (54, 0), (110, 1), (122, 0)]

    # ------------------------------------------------------------ 小件

    def ground(self, g: Gfx, t: float):
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
        for i, (x, k) in enumerate(self.tufts):
            tuft(g, x, FLOOR, t, i)

    def singing(self, t: float) -> float | None:
        k = t % SING_P
        return k if k < 5.5 else None

    def cicada(self, g: Gfx, y: float, t: float, sing: bool, spr: Sprite | None = None):
        s = spr or (CIC_SING if sing and int(t * 14) % 2 else CIC)
        k = t % SING_P
        shift = 1 if (not sing and 6.6 < k < 7.6) else 0  # 歇口气时往上挪一小步
        pix.blit(g, s, CX - 9, int(y) - shift)

    def sound(self, g: Gfx, y: float, k: float):
        """两侧声波（像素弧，一圈圈往外荡）"""
        cy = y + 13
        sound_arcs(g, CX - 11, cy, (k * 1.6) % 1, -1)
        sound_arcs(g, CX + 11, cy, (k * 1.6 + 0.5) % 1, 1)

    def daoshi_draw(self, g: Gfx, t: float, cyc: float):
        """小道士：平时盘坐；打瞌睡（点头 + z）；叶落头上惊醒，拂掉"""
        d = ev(cyc, PERIOD, *DOZE)
        if not d:
            m = ev(cyc, PERIOD, *MOLT)
            face = "normal"
            if m and 13.0 < m[1] < 22.0:
                face = "wow"
            elif m and 22.0 <= m[1] < 31.0:
                face = "happy"
            daoshi(g, DAO_X, FLOOR, "sit", t, face=face)
            return None
        k = d[1]
        if k < 20.0:
            nod = (k * 0.5) % 1 > 0.7
            daoshi(g, DAO_X, FLOOR, "sleep" if nod else "meditate", t)
            if k > 1.5:  # z 一个个往右上飘
                for j in range(3):
                    q = ((k * 0.45) + j / 3) % 1
                    zx, zy = DAO_X + 9 + q * 12, FLOOR - 36 - q * 14
                    if q < 0.85:
                        pix.blit(g, ZZZ, zx, zy)
            return (DAO_X - 2, FLOOR - 36) if k > 19.0 else None
        if k < 27.0:
            face = "wow" if k < 23.0 else "normal"
            daoshi(g, DAO_X, FLOOR, "sit", t, face=face)
            return (DAO_X - 2, FLOOR - 36)
        if k < 29.0:
            figure(g, DAO_X, FLOOR, t, legs="sit", arm="raise", face="happy")
            return None
        daoshi(g, DAO_X, FLOOR, "sit", t, face="happy" if k < 32 else "normal")
        return None

    def falling_leaf(self, g: Gfx, cyc: float, t: float):
        d = ev(cyc, PERIOD, *DOZE)
        if not d:
            return
        k = d[1]
        q = span(k, 15.0, 19.0)
        if 0 < q < 1:  # 从枝头晃晃悠悠飘向小道士头顶
            x = lerp(112, DAO_X - 2, ease_in_out(q)) + math.sin(q * 14) * 4
            y = lerp(10, FLOOR - 37, q)
            pix.blit(g, LEAF[int(q * 10) % 2], x - 2, y - 2)
        elif 19.0 <= k < 27.4:
            pix.blit(g, LEAF[0], DAO_X - 4, FLOOR - 39)
        elif 27.4 <= k < 29.5:  # 拂掉：往左飞落
            q2 = span(k, 27.4, 29.5)
            pix.blit(g, LEAF[int(q2 * 8) % 2], DAO_X - 4 - q2 * 18, FLOOR - 39 + ease_in(q2) * 37)

    # ------------------------------------------------------------ 主画面

    def scene(self, g: Gfx, t: float, cyc: float, arrive: float = 1.0, leave: float = 0.0):
        """arrive：入场飞来；leave：收场飞走"""
        self.ground(g, t)
        pix.blit(g, TRUNK, TX0 - 6, 0, outline=False)
        branch(g, t)
        m = ev(cyc, PERIOD, *MOLT)
        mxk = "sing"
        text = None
        k = m[1] if m else None
        # 空壳（平时挂在下面；脱壳时掉落、换新的）
        fallen = None
        if k is None or k < 2.0:
            pix.blit(g, EMPTY, CX - 7, SHELL_Y)
        elif k < 3.4:  # 旧壳掉落、弹一下
            q = span(k, 2.0, 3.0)
            yy = lerp(SHELL_Y, FLOOR - 13, ease_in(q))
            if k > 3.0:
                yy = FLOOR - 13 - math.sin(span(k, 3.0, 3.4) * math.pi) * 3
            pix.blit(g, EMPTY, CX - 7 - q * 18, yy)
        else:
            fallen = 1.0 - span(k, 26.0, 31.0)
        if fallen:
            if fallen > 0.5 or int(t * 10) % 2:
                pix.blit(g, EMPTY, CX - 25, FLOOR - 13)
        # 蝉
        if k is None:
            if leave > 0:  # 收场：张翅飞走
                q = ease_in(leave)
                pix.blit(g, FLY[int(t * 16) % 2], CX - 9 + q * 50, SING_Y - q * 40)
                mxk = "cic"
            elif arrive < 1:
                q = ease_out(arrive)
                if arrive < 0.8:
                    pix.blit(g, FLY[int(t * 16) % 2], lerp(130, CX - 9, q), lerp(-20, SING_Y, q))
                else:
                    self.cicada(g, SING_Y, t, False)
                mxk = "cic"
            else:
                s = self.singing(t)
                self.cicada(g, SING_Y, t, s is not None)
                if s is not None:
                    self.sound(g, SING_Y, s)
                else:
                    mxk = "cic"
        else:
            mxk = "shell"
            if k < 2.0:  # 老蝉张翅飞走
                q = ease_in(span(k, 0.4, 2.0))
                if k < 0.4:
                    self.cicada(g, SING_Y, t, False)
                else:
                    pix.blit(g, FLY[int(t * 16) % 2], CX - 9 + q * 50, SING_Y - q * 40)
            elif k < 4.0:
                pass
            elif k < 12.0:  # 若虫从树根往上爬（一步一停）
                q = span(k, 4.0, 11.5)
                step = int(k * 3) % 2
                y = lerp(FLOOR - 6, SHELL_Y, ease_out(q)) - (0.5 if step else 0)
                pix.blit(g, NYMPH[step if q < 1 else 0], CX - 7, y)
            else:
                text = "金蝉脱壳"
                if k < 14.0:  # 定住，背上裂开（发光一下）
                    pix.blit(g, NYMPH[0] if k < 13.0 else EMPTY, CX - 7, SHELL_Y)
                    if 12.8 < k < 13.4:
                        for j in range(3):
                            g.px(CX - 1 + j, SHELL_Y + 1)
                        for dx, dy in ((-4, -3), (4, -3), (0, -5)):
                            g.px(CX + dx, SHELL_Y + dy)
                else:
                    pix.blit(g, EMPTY, CX - 7, SHELL_Y)
                    if k < 20.0:  # 新蝉从裂口一点点钻出来（翅还皱着、短）
                        q = ease_out(span(k, 14.0, 19.5))
                        crump = _crumple(CIC_PALE, 0.5)
                        n = int(lerp(3, crump.h, q))
                        pix.blit(g, _crop(crump, n), CX - 9, SHELL_Y + 5 - n)
                    elif k < 25.0:  # 翅膀伸长、颜色变深
                        q = span(k, 20.0, 24.0)
                        spr = _crumple(CIC_PALE if q < 0.55 else CIC_HALF, lerp(0.5, 1.0, ease_out(q)))
                        if q >= 1:
                            spr = CIC
                        top = SHELL_Y + 5 - _crumple(CIC_PALE, 0.5).h
                        pix.blit(g, spr, CX - 9, top)
                        if int(k * 5) % 3 == 0:
                            g.px(CX - 12, top + 7)
                            g.px(CX + 12, top + 9)
                    else:  # 爬到高处，接着唱
                        q = ease_in_out(span(k, 25.0, 29.5))
                        y = lerp(SHELL_Y + 5 - _crumple(CIC_PALE, 0.5).h, SING_Y, q)
                        sing = k > 29.8
                        self.cicada(g, y, t, sing)
                        if sing:
                            self.sound(g, y, k - 29.8)
                if k > 26.0:
                    text = None
            mxk = "cic" if k > 22 else "shell"
        # 小道士与落叶
        self.daoshi_draw(g, t, cyc)
        self.falling_leaf(g, cyc, t)
        # 点阵
        if mxk == "sing":
            s = self.singing(t) or 0
            for c in range(8):
                hgt = 1 + int(noise(t * 9 + c * 3.7, 5) * 7 * (0.4 + 0.6 * abs(math.sin(s * 3))))
                for r in range(8 - hgt, 8):
                    g.mx[r, c] = True
        elif mxk == "shell":
            mx_art(g, MX_SHELL)
        else:
            mx_art(g, MX_CIC)
        return text

    def enter(self, g: Gfx, t: float):
        self.scene(g, t, 0.0 - 20.0, arrive=span(t, 0, 2.6))
        label(g, 4, 3, "蝉蜕于浊秽")

    def hold(self, g: Gfx, t: float):
        tt = t + self.T["enter"]
        text = self.scene(g, tt, tt % PERIOD)
        if text:
            label(g, 4, 3, text)
        elif t < 8.0:
            label(g, 4, 3, "蝉蜕于浊秽")

    def exit(self, g: Gfx, t: float):
        tt = self.hold_t + self.T["enter"] + t
        cyc = tt % PERIOD
        m = ev(cyc, PERIOD, *MOLT)
        if m:  # 正在脱壳：停在那一刻
            tt0 = self.hold_t + self.T["enter"]
            self.scene(g, tt0, tt0 % PERIOD)
            return
        self.scene(g, tt, cyc, leave=span(t, 0.1, 1.2))
