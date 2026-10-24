"""吹箫引凤：刘向《列仙传·萧史》“萧史善吹箫，能致孔雀、白鹤于庭……日教弄玉作凤鸣，居数年，吹似凤声，
凤凰来止其屋。公为作凤台，夫妇止其上……一旦，皆随凤凰飞去。”

高台入云：右边是凤台（飞檐瓦垄、檐角风铎、望柱栏杆、台基砖缝），台下云海慢慢流，远处几座山尖露出云头。
小道士站在栏杆后面朝左吹箫：箫斜斜地从嘴边垂下，手指按孔起落，箫声一圈圈向左荡开、越远越淡。
入场：凤台从右边移进来，云从左边飘来，小道士弹出来站定，第一道箫声荡开。
持续：每 45 秒凤凰拖着三根带“眼”的长尾羽从左边飞来，绕一圈（“吹似凤声”），落在栏杆头的望柱上歇着点头
      （“凤凰来止”），小道士眯眼一笑，再展翅往左上飞走。两次之间远处偶尔飞过一只白鹤；风铎一直轻摇。
退场：收圆。
点阵：平时是右下角往左上荡开的声波；凤凰飞时是扇翅的鸟，落下时是栖鸟。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x2_common import Clock, iris, label, put_arm, win

DECK = 50                     # 台面
DX = 98                       # 小道士（朝左）
POST_X = 68                   # 栏杆最左边的望柱（凤凰落脚处）
RAIL_TOP = 40
PERIOD = 45.0
FIRST = 8.0
EV = 18.0


# ---------------------------------------------------------------- 造型

def _phoenix(f: int):
    """飞翔的凤凰（朝右）22×16：冠羽三根、钩喙、长颈、扇翅三帧（上 / 平 / 下），翅上一道羽纹"""
    p = Part(22, 16)
    p.shape("ellipse", (5, 6, 15, 10), fill=1)                       # 身
    p.shape("polygon", [(13, 7), (16, 3), (18, 3), (17, 8)], fill=1)  # 颈
    p.shape("ellipse", (15, 1, 19, 5), fill=1)                       # 头
    p.px(17, 3, 0)
    p.shape("line", (20, 3, 21, 4), fill=1)                          # 喙
    for x0 in (15, 16, 17):                                          # 冠
        p.shape("line", (x0 + 1, 1, x0 - 1, 0), fill=1)
    p.d.line((7, 9, 13, 9), fill=0)
    wing = [[(7, 7), (13, 7), (11, 0), (4, 0)], [(6, 7), (13, 7), (8, 3), (0, 3)],
            [(6, 8), (13, 8), (10, 15), (3, 14)]][f]
    p.shape("polygon", wing, fill=1)
    a, b = wing[2], wing[3]
    p.d.line(((wing[0][0] + a[0]) // 2 + 1, (wing[0][1] + a[1]) // 2, (wing[1][0] + b[0]) // 2,
              (wing[1][1] + b[1]) // 2), fill=0)
    p.dither(wing, 0.25, 0)
    return p.sprite()


PERCH = pix.frames("""
          # #
         # #
         ###
        #####.#
        ##.##
        ###
       ###
      ###
    #######
   #########
  ##.#######
  #.##.####
   #.##.##
    ######
     #  #
    ##  ##
---

          # #
         # #
         ####
        #####.#
       ###.#
      ###
      ##
    ######
   #########
  ##.#######
  #.##.####
   #.##.##
    ######
     #  #
    ##  ##
""")


def _perched(f: int):
    """栖着的凤凰（朝右）15×16：冠羽、长颈、挺胸、收拢的翅上两道羽纹；f=1 低头点一下"""
    return PERCH[f]


def _cloud(w: int):
    """云带：三条长短不一的圆头云条叠在一起，左端一个回卷的云头"""
    p = Part(w + 6, 9)
    for y, x0, x1 in ((0, 8, w - 6), (3, 3, w), (6, 10, w - 2)):
        p.shape("ellipse", (x0, y, x0 + 2, y + 2), fill=1)
        p.shape("rectangle", (x0 + 1, y, x1 - 1, y + 2), fill=1)
        p.shape("ellipse", (x1 - 2, y, x1, y + 2), fill=1)
        p.d.line((x0 + 2, y + 1, x1 - 3, y + 1), fill=0)
    p.shape("ellipse", (0, 1, 6, 7), fill=1)                         # 云头回卷
    p.d.arc((1, 2, 5, 6), 0, 270, fill=0)
    p.px(3, 4, 1)
    return p.sprite()


def _crane(f: int):
    return pix.frames("""
 #   #
  # #
#######
    #
---
#######
  # #
 #   #
""")[f]


_P: dict = {}


def prop(name, *a):
    key = (name,) + a
    if key not in _P:
        _P[key] = {"ph": _phoenix, "perch": _perched, "cloud": _cloud, "crane": _crane}[name](*a)
    return _P[key]


@register
class Xiao(Rest):
    id = "x2.xiao"
    name = "吹箫引凤"
    desc = "高台入云，小道士倚栏吹箫，箫声荡开；凤凰拖着长尾飞来绕一圈，落在望柱上点头，再飞走"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.ht = 0.0
        self.clock = Clock()

    # ------------------------------------------------------------ 背景

    def terrace(self, g: Gfx, t: float, dx: float = 0.0):
        """凤台：飞檐、风铎、望柱栏杆、台基"""
        x0 = 62 + dx
        # 飞檐：瓦垄一排，檐角上翘
        g.d.polygon([(x0 + 6, 9), (128 + dx, 3), (128 + dx, 7), (x0 + 10, 12)], fill=1)
        for x in range(int(x0 + 12), int(128 + dx), 4):
            yy = 9 - (x - x0 - 6) * 6 / (128 + dx - x0 - 6)
            g.d.line((x, yy + 1, x - 1, yy + 4), fill=0)
        g.d.line((x0 + 6, 9, x0 + 2, 5), fill=1, width=2)              # 起翘
        g.px(x0 + 1, 4)
        g.d.line((x0 + 10, 13, 128 + dx, 8), fill=1)                  # 檐下枋
        sw = math.sin(t * 2.1) * 1.5                                  # 风铎
        g.d.line((x0 + 7, 11, x0 + 7 + sw * 0.4, 15), fill=1)
        g.d.rectangle((x0 + 6 + sw * 0.5, 15, x0 + 8 + sw * 0.5, 17), fill=1)
        g.px(x0 + 7 + sw * 0.6, 18)
        g.d.rectangle((118 + dx, 10, 121 + dx, DECK), fill=1)          # 立柱
        g.d.line((119 + dx, 12, 119 + dx, DECK - 1), fill=0)
        # 台基
        g.d.rectangle((x0, DECK, 128 + dx, 63), fill=0)
        g.d.line((x0, DECK, 128 + dx, DECK), fill=1)
        g.d.line((x0, DECK + 2, 128 + dx, DECK + 2), fill=1)
        for r, y in enumerate(range(DECK + 5, 64, 4)):
            g.d.line((x0, y, 128 + dx, y), fill=1)
            for x in range(int(x0) + (r % 2) * 5, int(128 + dx), 10):
                g.d.line((x, y + 1, x, y + 3), fill=1)
        g.d.line((x0, DECK, x0, 63), fill=1)

    def railing(self, g: Gfx, dx: float = 0.0):
        x0 = 62 + dx
        g.d.rectangle((x0, RAIL_TOP + 2, 128 + dx, RAIL_TOP + 3), fill=1)     # 寻杖
        g.d.line((x0, RAIL_TOP + 3, 128 + dx, RAIL_TOP + 3), fill=0)
        g.d.line((x0, DECK - 2, 128 + dx, DECK - 2), fill=1)                  # 地栿
        for x in range(int(x0) + 3, int(128 + dx), 4):                        # 栏板上的花瓶柱
            g.d.line((x, RAIL_TOP + 5, x, DECK - 3), fill=1)
            g.px(x - 1, RAIL_TOP + 7), g.px(x + 1, RAIL_TOP + 7)
        for px_ in (POST_X + dx, 96 + dx, 124 + dx):                         # 望柱（圆头）
            g.d.rectangle((px_ - 1, RAIL_TOP, px_ + 1, DECK - 1), fill=1)
            g.d.ellipse((px_ - 2, RAIL_TOP - 3, px_ + 2, RAIL_TOP + 1), fill=1)
            g.px(px_, RAIL_TOP + 2, 0)

    def sea(self, g: Gfx, t: float, dx: float = 0.0):
        """台下云海 + 远山尖"""
        for x, h, w in ((10, 14, 9), (34, 9, 7), (50, 12, 6)):    # 云头上露出的山尖：阳面亮、阴面网点
            g.d.polygon([(x - w, 52), (x, 52 - h), (x + w, 52)], fill=0, outline=1)
            g.d.line((x, 52 - h, x - 2, 52 - h + 4), fill=1)
            g.d.line((x - 2, 52 - h + 4, x + 1, 52 - h + 8), fill=1)
            pix.checker(g, (x + 1, 52 - h + 4, x + w - 1, 52), 0.25)
        for i, (y, w, sp) in enumerate(((46, 26, 3.0), (53, 34, 4.5), (58, 30, 6.0))):
            for j in range(3):
                x = (j * 70 + i * 23 - t * sp + dx) % 190 - 40
                pix.blit(g, prop("cloud", w), x, y - 8)

    # ------------------------------------------------------------ 吹箫的小道士

    def player(self, g: Gfx, t: float, x: float, face: str, dy: float = 0.0):
        """朝左站着吹箫：近身的手托住箫身，箫从嘴边斜垂向前下方；手指按孔起落"""
        spr, at = put_arm(7, 3, "fist")
        mouth = (x - 4, DECK - 19 + dy)
        end = (x - 16, DECK - 5 + dy)

        def flute(gg, a):
            gg.d.line((mouth[0], mouth[1], end[0], end[1]), fill=0, width=4)     # 描黑边
            gg.d.line((mouth[0], mouth[1], end[0], end[1]), fill=1, width=2)
            for kk in (0.3, 0.75):                                    # 竹节
                gg.px(lerp(mouth[0], end[0], kk) + 1, lerp(mouth[1], end[1], kk), 0)
            sw = math.sin(t * 2.3)                                    # 箫尾的穗子
            gg.d.line((end[0], end[1], end[0] - 1 + sw, end[1] + 4), fill=1)
            gg.d.rectangle((end[0] - 2 + sw, end[1] + 4, end[0] + sw, end[1] + 5), fill=1)
            for i in range(4):                                    # 指孔（随旋律开合）
                k = 0.45 + i * 0.12
                hx = lerp(mouth[0], end[0], k)
                hy = lerp(mouth[1], end[1], k)
                if (int(t * 3.3) >> i) & 1:
                    gg.px(hx, hy, 0)
            gg.d.rectangle((mouth[0] - 2, mouth[1] - 1, mouth[0], mouth[1] + 1), fill=1)   # 上手（按着上端）

        h = figure(g, x, DECK + dy, t, arm=spr, arm_at=at, flip=True, face=face, front=flute)
        return end

    def waves(self, g: Gfx, t: float, src):
        """箫声：一圈圈弧向左荡开、越远越疏"""
        for j in range(4):
            age = (t * 0.55 + j * 0.25) % 1.0
            r = 4 + age * 46
            step = 2 + int(age * 3)
            n = 0
            for a in range(140, 225, 4):
                n += 1
                if n % step:
                    continue
                aa = math.radians(a)
                g.px(src[0] + math.cos(aa) * r, src[1] + math.sin(aa) * r * 0.7)

    # ------------------------------------------------------------ 凤凰

    def phoenix(self, g: Gfx, t: float, k: float):
        """→ 状态：'fly' / 'perch' / None，以及位置"""
        if k < 4.0:                     # 从左边飞来
            q = k / 4.0
            x, y = lerp(-26, 34, q), 22 + math.sin(q * 6) * 4
            d = 1
        elif k < 7.5:                   # 绕一圈
            a = (k - 4.0) / 3.5 * 2 * math.pi
            x, y = 44 - math.cos(a) * 12, 26 - math.sin(a) * 8
            d = 1 if math.sin(a) >= 0 else -1
        elif k < 9.0:                   # 滑落到望柱上
            q = ease_out(span(k, 7.5, 9.0))
            x, y = lerp(32, POST_X - 6, q), lerp(26, RAIL_TOP - 14, q)
            d = 1
        elif k < 14.5:                  # 歇着点头
            nod = int((k - 9.0) / 0.7) % 3 == 1
            spr = prop("perch", int(nod))
            bx, by = POST_X - 7, RAIL_TOP - 16
            self.tail(g, bx + 3, by + 11, t, hang=True)
            pix.blit(g, spr, bx, by)
            return "perch", (bx, by)
        else:                           # 展翅往左上飞走
            q = span(k, 14.5, EV)
            x, y = lerp(POST_X - 6, -30, q), lerp(RAIL_TOP - 14, -12, q * q)
            d = -1
        f = int(t * 9) % 3
        self.tail(g, x + (5 if d > 0 else 17), y + 8, t, d=d)
        pix.blit(g, prop("ph", f), x, y, flip=d < 0)
        return "fly", (x, y)

    def tail(self, g: Gfx, x: float, y: float, t: float, d: int = 1, hang: bool = False):
        """三根长尾羽：波浪线，末端一个“眼”（小圆圈）"""
        for i in range(3):
            L = 15 + i * 4
            px_, py_ = x, y
            for s in range(L):
                if hang:
                    xx = x - s * 0.25 - i * 1.5 + math.sin(s * 0.4 + t * 2 + i) * 1
                    yy = y + s
                else:
                    xx = x - d * s
                    yy = y + (i - 1) * s * 0.18 + math.sin(s * 0.45 - t * 9 + i) * 1.4
                g.px(xx, yy)
                px_, py_ = xx, yy
            g.d.ellipse((px_ - 1, py_ - 1, px_ + 1, py_ + 1), outline=1)

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, enter: float = 1.0):
        dt = self.clock.dt(t)
        on = enter >= 1
        e3 = enter * self.T["enter"]
        dx = (1 - ease_out(span(e3, 0, 1.2))) * 70 if not on else 0.0
        cdx = (1 - ease_out(span(e3, 0, 1.6))) * -80 if not on else 0.0
        k, n = win(t, PERIOD, EV, FIRST) if on else (None, -1)
        self.sea(g, t, cdx)
        # 白鹤远远飞过（两次凤凰之间）
        ck = ((t - FIRST - 24.0) % PERIOD) / 9.0 if on else 2
        if 0 <= ck < 1:
            pix.blit(g, prop("crane", int(t * 4) % 2), lerp(70, -10, ck), 30 - ck * 6, outline=False)
        self.terrace(g, t, dx)
        face = "sleep" if (t % 6.0) < 2.2 else "normal"
        state = None
        if k is not None and 9.5 < k < 14.0:
            face = "happy"
        self.railing(g, dx)
        pop = ease_out_back(span(e3, 1.2, 1.7)) if not on else 1.0
        if pop > 0.05:
            end = self.player(g, t, DX + dx, face, (1 - pop) * 10)
            if (on or e3 > 2.0):
                self.waves(g, t if on else e3 - 2.0, (end[0] - 1, end[1] - 4))
        if k is not None:
            state, pos = self.phoenix(g, t, k)
        # 字
        if k is not None:
            if 1.0 < k < 7.0:
                label(g, 4, 2, "吹似凤声")
            elif 9.5 < k < 14.5:
                label(g, 4, 2, "凤凰来止")
        return state, k

    def mx(self, g: Gfx, t: float, state):
        if state == "fly":
            f = int(t * 9) % 3
            g.mx_blit(["""
#......#
##....##
.##..##.
..####..
...##...
........
........
........""", """
........
........
#......#
########
..####..
...##...
........
........""", """
........
........
...##...
..####..
.##..##.
##....##
#......#
........"""][f])
            return
        if state == "perch":
            g.mx_blit("""
....##..
...###..
...##...
..####..
.#####..
#####...
..#.#...
########""")
            return
        for j in range(3):          # 声波：从右下角往左上荡开
            r = ((t * 0.55 + j * 0.33) % 1.0) * 9
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(7 - x, 7 - y) - r) < 0.5:
                        g.mx[y, x] = True

    def enter(self, g: Gfx, t: float):
        self.scene(g, t, min(t / self.T["enter"], 0.999))
        if t > 2.0:
            self.mx(g, t - 2.0, None)
        g.mx[7, :] = True

    def hold(self, g: Gfx, t: float):
        self.ht = t
        state, k = self.scene(g, t)
        self.mx(g, t, state)

    def exit(self, g: Gfx, t: float):
        tt = self.ht + t
        state, k = self.scene(g, tt)
        self.mx(g, tt, state)
        iris(g, t / self.T["exit"], DX - 6, 34)
