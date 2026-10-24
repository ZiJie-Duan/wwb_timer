"""煮茶：陆羽《茶经·五之煮》三沸，卢仝《走笔谢孟谏议寄新茶》七碗茶歌。

小道士盘坐在风炉前（陆羽风炉：鼎形三足、炉身铸卦、炉门见火），炉上一口方耳铁鍑；面前一只茶托放茶碗。
右边背墙一扇月洞窗，窗里竹子摇。
入场：小道士走进来坐下，风炉从地里弹起，鍑落到炉上一震，炉门“呼”地起火、火星迸出。
持续（一碗 40 秒）：摇蒲扇扇火（火随扇子一鼓一鼓）、鍑里鱼目小泡 → 二沸：舀出一瓢水放一边，
      拿竹筴环激汤心（水面打旋），茶则投末 → 三沸腾波鼓浪：大泡、溅沫、热气最盛，小道士吓一跳
      → 把那瓢水倒回去止沸，水面浮起沫饽 → 舀一瓢斟进茶碗 → 捧碗喝，题本碗的诗句（一碗喉吻润……）。
      七碗一循环；第七碗彩蛋：“两腋习习清风生”，一阵清风横穿画面，热气全被吹斜，小道士飘起来。
      另外每 23 秒炉里“哔剥”一声蹦出一颗火星。
退场：画面收成一个圆。
点阵：小锅冒泡（三沸时泡最密）；喝茶时是冒热气的茶碗。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x2_common import Clock, iris, label, put_arm, typed, wisp

FLOOR = 57
DX = 24                       # 小道士（盘坐）脚底中点
SX = 57                       # 风炉中心
STOVE_TOP = FLOOR - 17        # 风炉顶
POT_TOP = STOVE_TOP - 10      # 鍑口
WATER = (SX, POT_TOP + 3)     # 水面中心
BOWL = (39, FLOOR - 1)        # 茶碗底中点
CYC = 40.0
LINES = ["一碗喉吻润", "两碗破孤闷", "三碗搜枯肠", "四碗发轻汗", "五碗肌骨清", "六碗通仙灵", "两腋习习清风生"]
WIN_C = (101, 32)             # 月洞窗


# ---------------------------------------------------------------- 道具

def _stove():
    """陆羽风炉 23×17：宽缘、鼓身、拱形炉门（里面画火）、左右两格铸巽☴坎☵卦、兽蹄三足"""
    p = Part(23, 17)
    p.shape("rectangle", (0, 0, 22, 1), fill=1)                       # 宽缘
    p.d.line((2, 0, 20, 0), fill=1)
    p.shape("polygon", [(1, 2), (21, 2), (22, 5), (21, 10), (19, 12), (3, 12), (1, 10), (0, 5)], fill=1)
    p.d.line((1, 2, 21, 2), fill=0)                                   # 缘下阴线
    p.shape("ellipse", (8, 4, 14, 10), fill=0)                        # 拱门
    p.shape("rectangle", (8, 7, 14, 12), fill=0)
    p.d.arc((7, 3, 15, 11), 180, 360, fill=1)
    for x0, lines in ((2, (False, False, True)), (16, (True, False, True))):   # 巽、坎
        p.shape("rectangle", (x0, 4, x0 + 4, 10), fill=0)
        for i, broken in enumerate(lines):
            y = 5 + i * 2
            p.d.line((x0 + 1, y, x0 + 3, y), fill=1)
            if broken:
                p.px(x0 + 2, y, 0)
    p.dither([(19, 3), (23, 3), (23, 12), (18, 12)], 0.5, 0)
    p.shape("rectangle", (2, 12, 20, 13), fill=1)                     # 底沿
    p.d.line((3, 13, 19, 13), fill=0)
    for x in (2, 10, 18):                                             # 兽蹄三足
        p.shape("rectangle", (x, 14, x + 2, 15), fill=1)
        p.shape("rectangle", (x - 1, 16, x + 3, 16), fill=1)
        p.px(x + 1, 15, 0)
    return p.sprite()


def _pot():
    """铁鍑 25×13：方耳（带孔）、宽沿（口里是暗的水面）、鼓腹一道凸弦纹、脐"""
    p = Part(25, 13)
    p.shape("chord", (1, -3, 23, 14), 0, 180, fill=1)                 # 鼓腹
    p.d.line((3, 9, 21, 9), fill=0)                                   # 凸弦纹
    for x in range(5, 20, 3):
        p.px(x, 10, 0)
    p.dither([(16, 5), (24, 5), (24, 12), (14, 12)], 0.5, 0)
    p.shape("rectangle", (10, 11, 14, 12), fill=1)                    # 脐
    p.px(12, 12, 0)
    p.d.arc((2, 1, 22, 8), 0, 180, fill=0)                            # 沿下阴线
    p.shape("ellipse", (2, 1, 22, 6), fill=1)                         # 宽沿
    p.shape("ellipse", (5, 2, 19, 5), fill=0)                         # 水面
    for x in (0, 20):                                                 # 方耳
        p.shape("rectangle", (x, 0, x + 4, 3), fill=1)
        p.d.rectangle((x + 1, 1, x + 3, 1), fill=0)
    p.px(6, 1, 1), p.px(7, 1, 1)                                      # 口沿高光
    return p.sprite()


def _bowl():
    """茶碗 9×6：口沿、斜壁、圈足 + 茶托"""
    p = Part(11, 6)
    p.shape("polygon", [(1, 0), (9, 0), (8, 2), (6, 3), (4, 3), (2, 2)], fill=1)
    p.d.line((2, 1, 8, 1), fill=0)
    p.px(3, 2, 0)
    p.shape("rectangle", (4, 4, 6, 4), fill=1)
    p.shape("rectangle", (0, 5, 10, 5), fill=1)
    p.px(1, 4), p.px(9, 4)
    return p.sprite()


def _bowl_tilt():
    """往右倒的茶碗 9×8（碗口朝右下）"""
    p = Part(9, 8)
    p.shape("polygon", [(2, 0), (8, 6), (6, 7), (2, 6), (0, 3), (0, 1)], fill=1)
    p.d.line((3, 1, 7, 5), fill=0)
    p.shape("rectangle", (0, 2, 0, 4), fill=1)
    return p.sprite()


def _cup(full: bool):
    """瓢（半个葫芦）6×4"""
    p = Part(6, 4)
    p.shape("rectangle", (0, 0, 5, 0), fill=1)
    p.shape("polygon", [(0, 1), (5, 1), (4, 3), (1, 3)], fill=1)
    if not full:
        p.d.line((1, 1, 4, 1), fill=0)
    else:
        p.px(2, 0, 0)
    p.px(4, 2, 0)
    return p.sprite()


def _fan(k: int):
    """蒲扇 9×9：扇面 + 叶脉 + 柄；k=0 扬起，1 扇下"""
    p = Part(10, 10)
    if k == 0:
        p.shape("ellipse", (3, 0, 9, 6), fill=1)
        p.shape("line", (0, 9, 4, 5), fill=1)
        for a in (0, 1, 2):
            p.d.line((5, 4, 4 + a * 2, 1), fill=0)
    else:
        p.shape("ellipse", (3, 3, 9, 9), fill=1)
        p.shape("line", (0, 5, 4, 6), fill=1)
        for a in (0, 1, 2):
            p.d.line((5, 6, 8, 4 + a * 2), fill=0)
    return p.sprite()


def _scoop():
    """茶则（量茶末的小匙）7×3"""
    p = Part(8, 3)
    p.shape("line", (0, 2, 3, 2), fill=1)
    p.shape("polygon", [(3, 0), (7, 0), (7, 2), (3, 2)], fill=1)
    p.d.line((4, 1, 6, 1), fill=0)
    return p.sprite()


_P: dict = {}


def prop(name):
    if name not in _P:
        _P.update(stove=_stove(), pot=_pot(), bowl=_bowl(), cup0=_cup(False), cup1=_cup(True),
                  fan0=_fan(0), fan1=_fan(1), scoop=_scoop(), fan_tuck=_fan(0).flip(), bowl_tilt=_bowl_tilt())
    return _P[name]


FIRE = pix.frames("""
  #
 ##
 ###
#.##
#..#
---
 #
 ##
###
##.#
#..#
---
  #
  ##
 ###
##.#
#..#
""")
FIRE_BIG = pix.frames("""
  #
 ##  #
 ###.#
####.#
#.#..#
#....#
---
 #
 ##
###  #
##.#.#
#.#..#
#....#
---
   #
#  ##
#.###
##.###
#..#.#
#....#
""")
LEAF = pix.frames("""
##
 ###
  ##
---
 ##
###
 #
""")


# ---------------------------------------------------------------- 动作关键帧（k 秒：手相对肩的位置、道具、瓢的方向）

# (时刻, dx, dy, 道具, 瓢角度)。道具不用时：扇子、竹筴、茶则别在腰带上，瓢斜插在鍑里，碗放在茶托上
WAIST = (4, 7)
LADLE_GRIP = (13, -11)
KEYS = [
    (0.0, 12, 6, "fan", 0), (8.5, 12, 6, "fan", 0),
    (9.0, *WAIST, "fan", 0), (9.05, *WAIST, None, 0),
    (9.6, *LADLE_GRIP, None, 0), (9.65, *LADLE_GRIP, "ladle", -1.2),
    (10.2, 15, -6, "ladle", 0), (10.5, 15, -4, "ladle", 0), (10.8, 15, -6, "ladle_f", 0),
    (11.5, 5, -2, "ladle_f", 1.0), (11.6, 5, -2, "pourb", 1.0), (12.3, 5, -2, "ladle", 1.0),
    (12.9, *LADLE_GRIP, "ladle", -1.2), (12.95, *LADLE_GRIP, None, 0),
    (13.4, *WAIST, None, 0), (13.45, *WAIST, "stick", 0),
    (14.0, 14, -9, "stick", 0), (16.4, 14, -9, "stick", 0),
    (16.9, *WAIST, "stick", 0), (16.95, *WAIST, "scoop", 0),
    (17.5, 15, -12, "scoop", 0), (18.5, 15, -12, "scoop", 0),
    (19.0, *WAIST, "scoop", 0), (19.05, *WAIST, None, 0), (19.5, 8, 9, None, 0), (24.0, 8, 9, None, 0),
    (24.6, 10, 12, None, 0), (24.65, 10, 12, "bowlw", 0),
    (25.3, 14, -11, "bowlw", 0), (25.4, 14, -11, "pourw", 0), (26.1, 14, -11, "bowl", 0),
    (26.8, 10, 12, "bowl", 0), (26.85, 10, 12, None, 0),
    (27.4, *LADLE_GRIP, None, 0), (27.45, *LADLE_GRIP, "ladle", -1.2),
    (28.0, 15, -6, "ladle", 0), (28.2, 15, -4, "ladle", 0), (28.4, 15, -6, "ladle_f", 0),
    (29.0, 5, -2, "ladle_f", 1.0), (29.1, 5, -2, "pourb", 1.0), (29.8, 5, -2, "ladle", 1.0),
    (30.4, *LADLE_GRIP, "ladle", -1.2), (30.45, *LADLE_GRIP, None, 0),
    (31.0, 10, 12, None, 0), (31.05, 10, 12, "tea", 0),
    (31.8, 5, 0, "tea", 0), (36.2, 5, 0, "tea", 0),
    (36.9, 10, 12, "tea", 0), (36.95, 10, 12, None, 0),
    (37.5, *WAIST, None, 0), (37.55, *WAIST, "fan", 0), (38.2, 12, 6, "fan", 0), (40.0, 12, 6, "fan", 0),
]
DRINK = (31.8, 36.2)
POEM = (32.0, 39.6)


def hand_at(k: float):
    for i in range(len(KEYS) - 1):
        t0, x0, y0, tool0, a0 = KEYS[i]
        t1, x1, y1, tool1, a1 = KEYS[i + 1]
        if t0 <= k < t1:
            q = ease_in_out((k - t0) / (t1 - t0))
            return lerp(x0, x1, q), lerp(y0, y1, q), tool0, lerp(a0, a1, q)
    return KEYS[-1][1], KEYS[-1][2], KEYS[-1][3], 0


def bowl_state(k: float) -> str:
    """茶托上的碗：empty / water（盛着出的那瓢水）/ tea"""
    if 11.9 <= k < 24.65:
        return "water"
    if 29.5 <= k < 31.05:
        return "tea"
    return "empty"


def stage(k: float) -> int:
    """1 一沸（鱼目）/ 2 二沸（连珠）/ 3 三沸（鼓浪）/ 4 止沸育华（沫饽）"""
    return 1 if k < 9.6 else 2 if k < 19 else 3 if k < 25.6 else 4


@register
class Tea(Rest):
    id = "x2.tea"
    name = "煮茶"
    desc = "小道士盘坐风炉前摇扇煮茶：鱼目、连珠、鼓浪三沸，出水、环激、投末、止沸，斟一碗捧着喝，一碗一句七碗茶歌"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.ht = 0.0

    # ------------------------------------------------------------ 背景

    def room(self, g: Gfx, t: float, wind: float = 0.0):
        g.d.line((0, FLOOR, 127, FLOOR), fill=1)
        for x in range(-40, 168, 12):                       # 竹席
            g.d.line((x, FLOOR + 1, x - 8, 63), fill=1)
        pix.checker(g, (0, FLOOR + 2, 128, 64), 0.25)
        g.d.line((0, FLOOR - 4, 127, FLOOR - 4), fill=1)    # 踢脚线
        cx, cy = WIN_C
        g.d.ellipse((cx - 17, cy - 15, cx + 17, cy + 15), outline=1)   # 月洞窗：双圈
        g.d.ellipse((cx - 15, cy - 13, cx + 15, cy + 13), outline=1)
        g.d.ellipse((cx - 14, cy - 12, cx + 14, cy + 12), fill=0)
        sway = math.sin(t * 0.9) * 1.2 + wind * 3
        for i, bx in enumerate((cx - 6, cx + 5)):            # 窗里两竿竹
            for y in range(cy - 11, cy + 12):
                xx = bx + (cy + 12 - y) * sway * 0.04
                g.px(xx, y)
                if (y - cy + i * 3) % 7 == 0:
                    g.px(xx - 1, y), g.px(xx + 1, y)
            for j in range(3):                               # 竹叶
                ly = cy - 9 + j * 6 + i * 2
                lx = bx + (cy + 12 - ly) * sway * 0.04 + (2 if j % 2 == 0 else -5)
                spr = pix.anim(LEAF, t * 0.6 + i + j * 0.5, 1.5)
                pix.blit(g, spr, lx, ly, flip=j % 2 == 1, outline=False)
        g.d.line((cx - 14, cy + 12, cx + 14, cy + 12), fill=1)   # 窗台

    def stove(self, g: Gfx, t: float, fire: float, dy: float = 0.0):
        pix.blit(g, prop("stove"), SX - 11, STOVE_TOP + dy)
        if fire > 0:
            fr = FIRE_BIG if fire > 1.2 else FIRE
            spr = pix.anim(fr, t, 8)
            pix.blit(g, spr, SX - spr.w // 2, STOVE_TOP + 12 - spr.h + dy, outline=False)

    def pot(self, g: Gfx, k: float, t: float, dy: float = 0.0, foam: float = 0.0):
        st = stage(k)
        jig = 1 if st == 3 and int(t * 10) % 3 == 0 else 0
        x0, y0 = SX - 12, POT_TOP + dy - jig
        pix.blit(g, prop("pot"), x0, y0)
        wx, wy = SX, y0 + 3
        if st == 1:          # 鱼目：零星小泡
            for i in range(3):
                if rand(int(t * 3) + i * 7, self.seed) < 0.6:
                    g.px(wx - 6 + int(rand(int(t * 3) * 3 + i, self.seed) * 12), wy + (i % 2))
        elif st == 2:        # 连珠：沿边一串
            ph = int(t * 6)
            for i in range(10):
                a = (i / 10) * 2 * math.pi + ph * 0.3
                if (i + ph) % 3:
                    g.px(wx + math.cos(a) * 7, wy + 0.5 + math.sin(a) * 1.2)
        elif st == 3:        # 鼓浪：水面拱起，大泡冒出口沿
            for i in range(3):
                ph = (t * 1.7 + i * 0.37) % 1
                bx = wx - 5 + i * 5 + int(rand(int(t * 1.7 + i * 0.37) + i, self.seed) * 3)
                by = wy - ph * 4
                r = 1 + (ph > 0.5)
                if ph < 0.85:
                    g.d.ellipse((bx - r, by - r, bx + r, by + r), outline=1)
            for x in range(wx - 7, wx + 8, 2):
                g.px(x, wy - (1 if (x + int(t * 12)) % 4 < 2 else 0))
        if foam > 0:         # 沫饽：水面浮一层白花
            n = int(foam * 7)
            for i in range(-n, n + 1):
                g.px(wx + i, wy + (i % 2))
                if abs(i) < n - 2 and i % 2 == 0:
                    g.px(wx + i, wy + 1 - (i % 2))

    def ladle(self, g: Gfx, hx, hy, ang: float, full: bool, tilt: bool = False):
        """瓢：柄从手伸出 10 像素，ang=0 指向右（伸进鍑），1 指向右下（茶碗）"""
        ux, uy = math.cos(ang * 0.7), math.sin(ang * 0.7)
        ex, ey = hx + ux * 10, hy + uy * 10
        g.d.line((hx + ux, hy + uy, ex, ey), fill=1)
        cup = prop("cup1" if full else "cup0")
        if tilt:
            cup = cup.rot90(-1)
        pix.blit(g, cup, ex - 1, ey - 1)
        return ex + 2, ey + 3

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, enter: float = 1.0):
        """enter：入场进度 0..1（1 = 正常）。返回点阵用的状态"""
        dt = self.clock.dt(t)
        e3 = enter * self.T["enter"]
        on = enter >= 1
        k = t % CYC if on else 0.0
        n = int(t // CYC) if on else 0
        seventh = n % 7 == 6
        st = stage(k)
        dx, dy, tool, ang = hand_at(k) if on else (12, 6, "fan", 0)
        drinking = DRINK[0] <= k < DRINK[1]
        windk = span(k, 31.5, 32.5) * (1 - span(k, 38.0, 39.5)) if seventh and on else 0.0
        self.room(g, t, windk)

        # 风炉、火（扇一下火鼓一下）
        fanning = tool == "fan"
        flap = int(t * 3.2) % 2 if fanning else 0
        rise = ease_out_back(span(e3, 0.2, 0.9)) if not on else 1.0
        sdy = (1 - rise) * 22
        fire = 0.0 if e3 < 1.5 else (1.6 if (fanning and flap == 1) or st == 3 else 1.0)
        self.stove(g, t, fire, sdy)
        drop = span(e3, 0.8, 1.3) if not on else 1.0
        if drop > 0:
            foam = span(k, 25.6, 26.6) * (1 - span(k, 38.0, 39.9)) if on else 0.0
            pdy = -(1 - ease_out(drop)) * 30 + sdy
            if not tool or not tool.startswith("ladle") and tool != "pourb":   # 瓢斜插在鍑里
                g.d.line((SX - 6, POT_TOP + 1 + pdy, SX + LADLE_GRIP[0] - 31 + 1, POT_TOP + pdy - 5), fill=1)
                g.d.line((SX - 6, POT_TOP + 2 + pdy, SX + LADLE_GRIP[0] - 31 + 1, POT_TOP + pdy - 4), fill=0)
            self.pot(g, k, t, pdy, foam)
            if not tool or not tool.startswith("ladle") and tool != "pourb":
                g.d.line((SX - 7, POT_TOP + 2 + pdy, SX - 4, POT_TOP + pdy), fill=1)
        if not on and abs(e3 - 1.3) < dt * 1.5:
            self.sparks.burst(SX, STOVE_TOP, 10, 22, up=6, life=0.5, gravity=40)
            pix.shake(g, t, 1.0)
        if not on and abs(e3 - 1.55) < dt * 1.5:
            self.sparks.burst(SX, STOVE_TOP + 8, 12, 26, up=20, life=0.7, gravity=60)

        # 热气（三沸最盛），被清风吹斜
        if drop >= 1:
            hgt = {1: 7, 2: 11, 3: 16, 4: 10}[st]
            for i, ox in enumerate((-5, 0, 5)):
                wisp(g, SX + ox, POT_TOP - 2, hgt - abs(ox) // 3, t + i * 0.7, self.seed + i, lean=-14 * windk)
        # 哔剥：炉门蹦出火星
        if on and abs((t % 23) - 11) < dt * 1.01:
            self.sparks.burst(SX + 2, STOVE_TOP + 9, 6, 24, up=24, life=0.8, gravity=80)
        if st == 3 and int(t * 30) % 9 == 0:                 # 三沸溅沫
            self.sparks.burst(SX + (rand(int(t * 30), self.seed) - 0.5) * 12, POT_TOP, 2, 14, up=16, life=0.4,
                              gravity=60)

        # 茶碗（不在手里时放在茶托上）
        bs = bowl_state(k) if on else "empty"
        in_hand = tool in ("bowl", "bowlw", "pourw", "tea")
        if not in_hand:
            pix.blit(g, prop("bowl"), BOWL[0] - 5, BOWL[1] - 5)
            if bs != "empty":
                wisp(g, BOWL[0], BOWL[1] - 7, 6 if bs == "tea" else 4, t, self.seed + 9, amp=1.0, lean=-8 * windk)

        # 小道士
        if not on and e3 < 1.2:
            x = lerp(-14, DX, ease_out(span(e3, 0, 1.2)))
            figure(g, x, FLOOR, t, legs="walk", arm="down")
            hand = None
        else:
            face = "normal"
            if 19.3 < k < 20.8:
                face = "wow"
            elif drinking:
                face = "sleep" if (k - DRINK[0]) % 2.2 < 1.5 else "happy"
            elif windk > 0.5:
                face = "happy"
            if fanning:
                dy += -2 if flap == 0 else 1
            if not on:   # 刚坐下：手先放在膝上，再从腰间抽出扇子
                q = span(e3, 1.4, 2.6)
                dx, dy = lerp(8, 12, q), lerp(9, 6, q)
                tool = "fan" if q > 0.5 else None
            spr, at = put_arm(dx, dy, "fist", over=in_hand and dy < 6)
            float_dy = -int(round(2.5 * windk + math.sin(t * 3) * windk))
            pop = ease_out_back(span(e3, 1.2, 1.5)) if not on else 1.0
            tucked = tool != "fan" and (on or e3 > 2.0)

            def front(gg, at_):
                if tucked:     # 扇子别在腰带上
                    pix.blit(gg, prop("fan_tuck"), DX - 15, FLOOR - 25 + float_dy)

            hd = figure(g, DX, FLOOR + (1 - pop) * 3, t, legs="sit", arm=spr, arm_at=at, face=face, dy=float_dy,
                        behind=front)
            hand = hd["hand"]
        if hand:
            hx, hy = hand
            if tool == "fan":
                pix.blit(g, prop("fan0" if flap == 0 else "fan1"), hx, hy - 8)
            elif tool in ("ladle", "ladle_f", "pourb"):
                pour = tool == "pourb"
                cx, cy = self.ladle(g, hx, hy, ang, tool == "ladle_f" or pour, tilt=pour)
                if pour:               # 水柱
                    for i in range(0, 7):
                        if (i + int(t * 20)) % 3:
                            g.px(cx, cy + i)
            elif tool == "stick":      # 竹筴：在汤心画圈
                a = t * 7
                tx, ty = WATER[0] + math.cos(a) * 4, WATER[1] + math.sin(a) * 1
                g.d.line((hx + 1, hy, tx, ty), fill=1)
                for i in range(6):     # 漩涡
                    aa = a - i * 0.7
                    g.px(WATER[0] + math.cos(aa) * (6 - i * 0.6), WATER[1] + 0.5 + math.sin(aa) * 1.3)
            elif tool == "scoop":
                pix.blit(g, prop("scoop"), hx, hy - 2)
                if 17.6 < k < 18.5:    # 投末
                    for i in range(5):
                        yy = ((k * 25 + i * 3) % 11)
                        g.px(hx + 7 + (i % 2), hy + 1 + yy)
            elif in_hand:
                if tool == "pourw":    # 把那瓢水倒回去止沸
                    pix.blit(g, prop("bowl_tilt"), hx - 1, hy - 4)
                    for i in range(7):
                        if (i + int(t * 20)) % 3:
                            g.px(hx + 7, hy + 4 + i)
                else:
                    pix.blit(g, prop("bowl"), hx - 4, hy - 3)
                    if tool in ("bowlw", "tea") and not drinking:
                        wisp(g, hx + 1, hy - 5, 4, t, self.seed + 4, amp=0.8)
                    if drinking and (k - DRINK[0]) % 2.2 >= 1.5:
                        wisp(g, hx + 2, hy - 4, 6, t, self.seed + 4, amp=0.8, lean=-8 * windk)

        # 清风（第七碗）
        if windk > 0:
            for i in range(9):
                y = 6 + i * 5 + (i % 3)
                x = 128 - ((t * 70 + i * 37) % 170)
                ln = 6 + (i % 3) * 4
                if (i * 7) % 3 or windk > 0.6:
                    pix.dotted(g, x, y, x + ln * windk, y, step=2, phase=i)
        self.sparks.step(dt)
        self.sparks.draw(g)

        # 字：本碗诗句（右上，喝茶时逐字显出）
        if on and POEM[0] <= k < POEM[1]:
            label(g, 126, 2, typed(LINES[n % 7], k - POEM[0], 3), align="right")
        return st, ("bowl" if in_hand else tool), k, windk

    def mx(self, g: Gfx, t: float, st: int, tool, windk: float):
        g.mx[7, 1:7] = True
        g.mx[6, 0:8] = True
        g.mx[5, 1:7] = True
        if tool == "bowl" or windk > 0:      # 茶碗冒热气
            g.mx[5:8, :] = False
            g.mx[7, 2:6] = True
            g.mx[6, 1:7] = True
            g.mx[5, 0:8] = True
            for c in (2, 5):
                for r in range(4):
                    if (r + int(t * 5) + c) % 4 < 2:
                        g.mx[r, c + (1 if (r + int(t * 2)) % 2 else 0)] = True
            if windk > 0:
                for r in (0, 2):
                    g.mx[r, :] = False
                    g.mx[r, int(t * 12 + r) % 8] = True
                    g.mx[r, int(t * 12 + r + 1) % 8] = True
            return
        n = {1: 1, 2: 3, 3: 6, 4: 2}[st]
        for i in range(n):
            ph = (t * (1.5 + st * 0.6) + i * 0.37) % 1
            c = 1 + int(rand(int(t * (1.5 + st * 0.6) + i * 0.37) + i * 11, 3) * 6)
            r = 4 - int(ph * 5)
            if 0 <= r <= 4:
                g.mx[r, c] = True

    def enter(self, g: Gfx, t: float):
        q = min(t / self.T["enter"], 0.999)
        st, tool, k, w = self.scene(g, t, q)
        self.mx(g, t, 1, None, 0)
        if t * 1.0 < 1.5:
            g.mx[0:5, :] = False

    def hold(self, g: Gfx, t: float):
        self.ht = t
        st, tool, k, w = self.scene(g, t)
        self.mx(g, t, st, tool, w)

    def exit(self, g: Gfx, t: float):
        tt = self.ht + t
        st, tool, k, w = self.scene(g, tt)
        self.mx(g, tt, st, tool, w)
        iris(g, t / self.T["exit"], DX + 10, FLOOR - 20)
        if t > self.T["exit"] * 0.6:
            g.mx[:] = False
            g.mx[3:5, 3:5] = True
