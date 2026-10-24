"""x6 赛博歇（三）：网络——问天（ping）、不争（断网小恐龙）（像素风，小道士出镜）"""
from __future__ import annotations

import math


from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x6_common import FLOOR, Clock, crossed, cushion, cyc, sit, spr


def floor_line(g: Gfx):
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-30, 170, 18):
        g.d.line((x, FLOOR + 1, x - 10, 63), fill=1)
    pix.checker(g, (0, FLOOR + 2, 128, 64), 0.125)


# ====================================================================== 问天

def _gate():
    """南天门 36×26：重檐翘角、正脊鸱吻、空匾、两根大柱（柱础）、额枋彩画"""
    p = Part(36, 26)
    p.shape("polygon", [(6, 3), (30, 3), (35, 0), (33, 5), (3, 5), (1, 0)], fill=1)      # 上檐（翘角）
    p.shape("rectangle", (10, 0, 26, 2), fill=1)                                        # 正脊
    p.px(9, 0), p.px(27, 0)
    p.d.line((5, 4, 31, 4), fill=0)
    for x in range(6, 31, 3):                                                           # 瓦当
        p.px(x, 5, 0)
    p.shape("rectangle", (7, 6, 29, 7), fill=1)
    p.shape("polygon", [(4, 9), (32, 9), (35, 7), (34, 11), (2, 11), (1, 7)], fill=1)    # 下檐
    p.d.line((4, 10, 32, 10), fill=0)
    p.shape("rectangle", (13, 12, 23, 17), fill=1)                                     # 匾
    p.d.rectangle((14, 13, 22, 16), fill=0)
    p.d.line((16, 14, 20, 14), fill=1), p.d.line((16, 15, 19, 15), fill=1)
    p.shape("rectangle", (6, 12, 30, 13), fill=1)                                      # 额枋
    p.d.line((8, 12, 11, 12), fill=0), p.d.line((25, 12, 28, 12), fill=0)
    for x in (6, 27):                                                                   # 柱
        p.shape("rectangle", (x, 12, x + 3, 23), fill=1)
        p.d.line((x + 2, 14, x + 2, 22), fill=0)
        p.shape("rectangle", (x - 1, 23, x + 4, 25), fill=1)
    return p.sprite()


def _cloud(w: int):
    """祥云一朵（宽 w）：几团圆鼓起，底边平，鼓包里一道回卷线"""
    p = Part(w, 10)
    n = max(2, w // 8)
    for i in range(n):
        cx = 4 + i * (w - 8) / max(1, n - 1)
        r = 4 if i % 2 == 0 else 3
        p.shape("ellipse", (cx - r, 8 - 2 * r, cx + r, 8), fill=1)
    p.shape("rectangle", (2, 6, w - 3, 9), fill=1)
    p.d.line((3, 8, w - 4, 8), fill=0)
    for i in range(n):
        cx = 4 + i * (w - 8) / max(1, n - 1)
        p.d.arc((cx - 2, 3, cx + 2, 7), 180, 330, fill=0)
    return p.sprite()


def _mac():
    """小电脑 18×19：一体机、圆角屏、软驱口、苹果位放个太极点、底座键盘另画"""
    p = Part(18, 19)
    p.shape("rounded_rectangle", (0, 0, 17, 18), radius=2, fill=1)
    p.d.rectangle((2, 2, 15, 11), fill=0)
    p.d.line((9, 14, 14, 14), fill=0)            # 软驱
    p.px(3, 15, 0)
    p.dither([(15, 1), (17, 1), (17, 18), (15, 18)], 0.5, 0)
    return p.sprite()


def _keyboard():
    p = Part(14, 3)
    p.shape("polygon", [(1, 0), (13, 0), (13, 2), (0, 2)], fill=1)
    for x in range(2, 13, 2):
        p.px(x, 1, 0)
    return p.sprite()


def _table():
    """小矮桌 30×12"""
    p = Part(30, 12)
    p.shape("rectangle", (0, 0, 29, 1), fill=1)
    p.d.line((1, 1, 28, 1), fill=0)
    p.shape("rectangle", (1, 2, 28, 3), fill=1)
    for x in (2, 25):
        p.shape("rectangle", (x, 4, x + 2, 11), fill=1)
        p.px(x + 1, 6, 0)
    return p.sprite()


HEART = pix.frames("""
.#.#.
#####
#####
.###.
..#..
---
.....
.#.#.
.###.
..#..
.....
""")
MX_HEART = [0x00, 0x66, 0xFF, 0xFF, 0x7E, 0x3C, 0x18, 0x00]
MX_Q = [0x3C, 0x66, 0x06, 0x0C, 0x18, 0x18, 0x00, 0x18]
PACKET = Sprite("""
###
#.#
###
""")
QMARK = Sprite("""
.###.
#...#
...#.
..#..
.....
..#..
""")


def type_arm():
    """打字：前臂平伸，手垂在键盘上"""
    def mk():
        p = Part(13, 9)
        p.shape("polygon", [(0, 0), (4, 0), (9, 3), (9, 6), (2, 7), (0, 5)], fill=1)
        p.d.line((8, 3, 8, 6), fill=0)
        p.dither([(2, 5), (9, 5), (9, 7), (2, 7)], 0.5, 0)
        p.shape("rectangle", (9, 4, 11, 7), fill=1)
        p.px(11, 7, 0)
        s = p.sprite()
        s.hand = (10, 7)
        return s
    return spr("type_arm", mk)


@register
class PingHeaven(Rest):
    id = "x6.ping"
    name = "问天"
    desc = "小道士坐在小电脑前 ping 天庭：数据包飞进云里的南天门，散了，“请求超时”；改 ping 本心，包绕一圈回到自己胸口，屏幕上一颗心开始跳——不出户，知天下"
    T = {"enter": 2.4, "exit": 1.2}
    C = 50.0
    X = 18
    GATE = (86, 3)
    PC = (42, 28)
    PINGS = (3.0, 7.4, 11.8)          # 三次 ping 天庭（各 4.4 秒）
    SELF = (21.0, 23.4, 25.8)         # 三次 ping 本心（各 2.4 秒）

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    def echo(self, n: int, i: int) -> bool:
        """上一场圆满：第一轮第三次 ping 天庭有回音"""
        return self.ctx.finished and n == 0 and i == 2

    def line(self, u: float, n: int):
        """终端这一行：(文字, 打字进度 0..1)"""
        if u < 3.0:
            return "> ping 天庭", span(u, 0.4, 2.6)
        for i, s in enumerate(self.PINGS):
            if s + 1.9 <= u < s + 4.4:
                return ("回：功德已收" if self.echo(n, i) else "请求超时。"), 1.0
            if s <= u < s + 1.9:
                return "> ping 天庭", 1.0
        if 16.2 <= u < 18.5:
            return ("丢包 66%" if self.echo(n, 2) else "丢包 100%"), 1.0
        if 18.5 <= u < 21.0:
            return "> ping 本心", span(u, 18.7, 20.6)
        for s in self.SELF:
            if s + 1.6 <= u < s + 2.4:
                return "本心 <1ms", 1.0
            if s <= u < s + 1.6:
                return "> ping 本心", 1.0
        if 28.4 <= u < 30:
            return "", 0.0
        if 30 <= u < 38:
            return "不出户", 1.0
        if 38 <= u < 48:
            return "知天下", 1.0
        return "", 0.0

    def gate_bob(self, t: float) -> int:
        return int(round(math.sin(t * 0.9) * 1.2))

    def path(self, k: float, t: float):
        """数据包：电脑天线 → 云里的南天门（弧线）"""
        x0, y0 = self.PC[0] + 9, self.PC[1] - 4
        gx, gy = self.GATE
        x1, y1 = gx + 18, gy + 20 + self.gate_bob(t)
        return lerp(x0, x1, k), lerp(y0, y1, k) - math.sin(k * math.pi) * 10

    def self_path(self, k: float):
        """ping 本心：出门绕一个小圈回到胸口"""
        x0, y0 = self.PC[0] + 9, self.PC[1] - 4
        cx, cy = self.X + 16, 26
        a = k * 2 * math.pi
        x = lerp(x0, self.X + 4, k) + math.sin(a) * 9
        y = lerp(y0, 42, k) - math.sin(a * 0.5) * 12
        return x, y

    def scenery(self, g: Gfx, t: float, open_: float = 1.0):
        gx, gy = self.GATE
        b = self.gate_bob(t)
        drift = math.sin(t * 0.4) * 2
        pix.blit(g, spr("cloud3", lambda: _cloud(30)), 64 + drift, 30 + b)
        pix.blit(g, spr("gate", _gate), gx, gy + b)
        pix.blit(g, spr("cloud5", lambda: _cloud(44)), gx - 6 - drift, gy + 22 + b)

    def desk(self, g: Gfx, t: float, screen: str, u: float, typing: bool):
        px_, py_ = self.PC
        pix.blit(g, spr("table", _table), px_ - 12, 46)
        pix.blit(g, spr("mac", _mac), px_, py_)
        pix.blit(g, spr("kbd", _keyboard), px_ - 12, 43)
        # 天线（拨号猫）
        g.d.line((px_ + 9, py_ - 1, px_ + 9, py_ - 4), fill=1)
        g.px(px_ + 8, py_ - 5), g.px(px_ + 10, py_ - 5)
        sx, sy = px_ + 3, py_ + 3
        if screen == "heart":
            beat = (u * 1.3) % 1 < 0.18 or 0.3 < (u * 1.3) % 1 < 0.45
            pix.blit(g, HEART[0 if beat else 1], sx + 4, sy + 2, outline=False)
        elif screen == "term":
            for i in range(3):
                g.d.line((sx + 1, sy + 1 + i * 2, sx + 3 + (i * 5) % 7, sy + 1 + i * 2), fill=1)
            if (t * 2) % 1 < 0.5:
                g.d.line((sx + 1, sy + 7, sx + 2, sy + 7), fill=1)

    def frame(self, g: Gfx, t: float, u: float, n: int, dt: float, wipe: float = 0.0):
        floor_line(g)
        self.scenery(g, t)
        txt, prog = self.line(u, n)
        typing = txt.startswith(">") and 0 < prog < 1
        heart = u >= 22.6
        self.desk(g, t, "heart" if heart else "term", u, typing)
        # 小道士
        cushion(g, self.X)
        face = "normal"
        if 16.2 <= u < 18.5:
            face = "sleep"            # 丢包：叹气
        elif 22.6 <= u < 30:
            face = "happy"
        elif u >= 30:
            face = "sleep"
        bob = 1 if typing and int(t * 10) % 2 else 0
        sit(g, self.X, t, face=face, arm=type_arm(), arm_at=(-3, -16 + bob), head="bow" if 16.6 <= u < 18.2 else "up")
        # 数据包飞向天庭：散成几点、冒个“?”
        for i, s in enumerate(self.PINGS):
            k = span(u, s, s + 1.3)
            if 0 < k < 1:
                x, y = self.path(ease_in_out(k), t)
                for j in range(1, 12):  # 走过的虚线轨迹
                    q = ease_in_out(k) * j / 12
                    if (j + int(t * 12)) % 2:
                        g.px(*self.path(q, t))
                pix.blit(g, PACKET, x - 1, y - 1)
            gx, gy = self.GATE
            cx, cy = gx + 18, gy + 20 + self.gate_bob(t)
            if crossed(u, dt, s + 1.3):
                self.sparks.burst(cx, cy, 6, 14, life=0.6, gravity=0)
            if s + 1.4 <= u < s + 2.6:
                if self.echo(n, i):  # 有回音：一颗金点从天门飞回来
                    k2 = span(u, s + 1.4, s + 2.4)
                    x, y = self.path(1 - ease_in_out(k2), t)
                    g.d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=1)
                    g.px(x, y - 3), g.px(x - 3, y), g.px(x + 3, y)
                else:
                    pix.blit(g, QMARK, gx - 7, gy + 12 - ease_out(span(u, s + 1.4, s + 1.8)) * 4)
        for s in self.SELF:
            k = span(u, s, s + 1.5)
            if 0 < k < 1:
                x, y = self.self_path(ease_in_out(k))
                pix.blit(g, PACKET, x - 1, y - 1)
            if crossed(u, dt, s + 1.5):
                self.sparks.burst(self.X + 4, 42, 8, 16, up=6, life=0.5, gravity=10)
        if 22.6 <= u < 30:  # 心口一颗心跳一下
            k = span(u, 22.6, 23.4)
            if k < 1:
                pix.blit(g, HEART[0], self.X + 2, 34 - k * 12)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 终端一行字（最后画）
        if txt and wipe <= 0:
            m = len(txt) if prog >= 1 else max(1, int(len(txt) * prog + 0.999)) if prog > 0 else 0
            if m:
                w = g.text(3, 2, txt[:m])
                if typing and (t * 3) % 1 < 0.6:
                    g.d.rectangle((4 + w, 11, 9 + w, 12), fill=1)
            elif (t * 2) % 1 < 0.5:
                g.d.rectangle((4, 11, 9, 12), fill=1)
        elif wipe <= 0 and (t * 2) % 1 < 0.5:
            g.d.rectangle((4, 11, 9, 12), fill=1)       # 闪烁的光标
        if wipe > 0:
            g.d.rectangle((0, 0, 127, 64 * wipe), fill=0)
            g.d.line((0, 64 * wipe, 127, 64 * wipe), fill=1)
        self.mx(g, u, t)

    def mx(self, g: Gfx, u: float, t: float):
        for s in self.PINGS:
            if s <= u < s + 1.3:  # 向上扩散的波
                k = (u - s) / 1.3
                for yy in range(8):
                    for xx in range(8):
                        if abs(math.hypot(xx - 3.5, (yy - 8) * 1.0) - k * 9) < 0.6:
                            g.mx[yy, xx] = True
                return
            if s + 1.3 <= u < s + 4.4:
                g.mx_rows(MX_Q)
                return
        if u >= 22.6:
            beat = (u * 1.3) % 1 < 0.18 or 0.3 < (u * 1.3) % 1 < 0.45
            g.mx_rows(MX_HEART if beat else [0, 0, 0x24, 0x7E, 0x3C, 0x18, 0, 0])
            return
        g.mx[7, :] = True                      # 平时：一只小电脑
        g.mx[1, 1:7] = True
        g.mx[1:6, 1] = g.mx[1:6, 6] = True
        g.mx[5, 1:7] = True
        g.mx[3, 3] = (t * 2) % 1 < 0.5

    def enter(self, g: Gfx, t: float):
        """云上的南天门从上方降下，小电脑开机，光标闪"""
        dt = self.clock(t)
        floor_line(g)
        k = ease_out_bounce(span(t, 0.0, 1.2))
        gx, gy = self.GATE
        self.GATE = (gx, gy - 40 * (1 - k))
        self.scenery(g, t)
        self.GATE = (gx, gy)
        self.desk(g, t, "term" if t > 1.0 else "", 0.0, False)
        if 0.8 < t < 1.0:
            px_, py_ = self.PC
            g.d.rectangle((px_ + 2, py_ + 2, px_ + 15, py_ + 11), fill=1)
        cushion(g, self.X)
        sit(g, self.X, t, face="normal", arm=type_arm(), arm_at=(-3, -16))
        if t > 1.4 and (t * 2) % 1 < 0.5:
            g.d.rectangle((4, 11, 9, 12), fill=1)
        self.mx(g, 0.0, t)

    def hold(self, g: Gfx, t: float):
        dt = self.clock(t)
        n, u = cyc(t, self.C)
        self.frame(g, t, u, n, dt)

    def exit(self, g: Gfx, t: float):
        """像清屏一样从上往下抹掉"""
        dt = self.clock(t)
        n, u = cyc(self.hold_t, self.C)
        self.frame(g, self.hold_t + t, u, n, dt, wipe=ease_in(span(t, 0, 1.1)))


# ====================================================================== 不争

GROUND = 52
SPEED = 13.0          # 地面后退速度（像素/秒）
DX = 40               # 道士站位

TREX = pix.frames("""
          ########
         ##.#######
         ##########
         ##########
         #####
         ########
#       #####
#      ######
##   ##########
###  ########.#
############
 ##########
  ########
   ######
    ###.##
    ##   #
    #    #
    ##   ##
---
          ########
         ##.#######
         ##########
         ##########
         #####
         ########
#       #####
#      ######
##   ##########
###  ########.#
############
 ##########
  ########
   ######
    ##.###
    #   ##
    #
    ##
""")
TREX_DEAD = pix.frames("""
          ########
         #.#.######
         ##.#######
         #.#.######
         ##########
         #########
#       #####
#      ######
##   ##########
###  ########.#
############
 ##########
  ########
   ######
    ###.##
    ##   #
    #    #
    ##   ##
""")[0]
CACTI = pix.frames("""
   ###
   ###
#  ###
## ###  #
## ###  #
## ### ##
## ### ##
###### ##
 ########
   ####
   ###
   ###
   ###
   ###
   ###
---
    ###
    ###
 #  ###
 #  ###
 ## ###  #
 ## ###  #
 ## ### ##
 ## ### ##
 ###### ##
  ########
    #####
    ###
    ###  ##
    ### ###
    ### ##.
    #######
    ###
    ###
""")
def _crane(up: bool):
    """仙鹤（朝左飞）22×13：长颈前伸、尖喙、丹顶（一个暗点）、黑尾、长腿后拖；翅膀上 / 下两帧"""
    p = Part(22, 13)
    p.shape("ellipse", (8, 5, 16, 9), fill=1)                 # 身
    p.shape("line", (4, 5, 9, 7), fill=1)                     # 颈
    p.shape("line", (4, 4, 8, 6), fill=1)
    p.shape("rectangle", (2, 3, 4, 5), fill=1)                # 头
    p.px(3, 3, 0)                                              # 丹顶
    p.shape("line", (0, 5, 2, 5), fill=1)                      # 喙
    p.shape("line", (16, 7, 21, 8), fill=1)                    # 腿
    p.shape("line", (16, 8, 21, 10), fill=1)
    p.dither([(14, 5), (17, 5), (17, 9), (14, 9)], 0.5, 0)     # 黑尾
    if up:
        p.shape("polygon", [(9, 6), (14, 6), (18, 0), (15, 0), (11, 3)], fill=1)
        p.d.line((12, 4, 16, 1), fill=0)
    else:
        p.shape("polygon", [(9, 8), (14, 8), (17, 12), (14, 12), (10, 10)], fill=1)
        p.d.line((12, 9, 15, 11), fill=0)
    return p.sprite()


RESTART = Sprite("""
 ####
#.  ##
#  ###
#
#   #
 ###
""")


def _gourd():
    """背上的葫芦 7×10：束腰、系绳、高光"""
    p = Part(7, 10)
    p.shape("ellipse", (1, 0, 5, 4), fill=1)
    p.shape("ellipse", (0, 3, 6, 9), fill=1)
    p.d.line((1, 4, 5, 4), fill=0)
    p.px(2, 6, 0), p.px(2, 1, 0)
    p.dither([(4, 5), (6, 5), (6, 9), (4, 9)], 0.5, 0)
    return p.sprite()


def _staff_arm():
    """拄杖的手臂：袖子往前斜垂，手在前下方"""
    p = Part(11, 13)
    p.shape("polygon", [(1, 0), (5, 0), (9, 9), (8, 11), (1, 11)], fill=1)
    p.d.line((2, 10, 8, 10), fill=0)
    p.dither([(5, 3), (9, 9), (7, 11), (5, 11)], 0.5, 0)
    p.shape("rectangle", (6, 10, 9, 12), fill=1)
    p.px(9, 12, 0)
    s = p.sprite()
    s.hand = (8, 11)
    return s


_WG = Gfx()


@register
class NoContend(Rest):
    id = "x6.buzheng"
    name = "不争"
    desc = "断网小恐龙的跑酷里，背葫芦拄杖的小道士慢慢走，从不跳，仙人掌直接从身上穿过；小恐龙冲上来一路跳、最后撞上仙人掌 GAME OVER——夫唯不争，故无尤"
    T = {"enter": 2.6, "exit": 1.2}
    EV = 42.0

    def setup(self):
        self.clock = Clock()
        self.s = self.rng.randrange(1000)
        self._cx: dict = {}
        self._dino: dict = {}

    # ------------------------------------------------------------ 世界（t 的函数）

    def cactus(self, i: int):
        """第 i 棵仙人掌：(世界 x, 种类)"""
        v = self._cx.get(i)
        if v is None:
            x = 80 + i * 96 + (rand(i, self.s) - 0.5) * 40
            v = self._cx[i] = (x, int(rand(i + 77, self.s) * 2))
            if len(self._cx) > 400:
                self._cx.clear()
        return v

    def visible(self, scroll: float):
        i0 = max(0, int((scroll - 120) / 96))
        for i in range(i0, i0 + 6):
            x, k = self.cactus(i)
            sx = x - scroll
            if -20 < sx < 140:
                yield i, sx, k

    def event(self, t: float):
        """每 42 秒一个事件（第 6 秒起）：(种类, 事件内秒数)；0 恐龙 1 仙鹤"""
        if t < 6:
            return None, 0.0, -1
        n, k = cyc(t - 6, self.EV)
        kind = 0 if n % 3 != 2 else 1
        dur = 36.0 if kind == 0 else 9.0
        return (kind, k, n) if k < dur else (None, 0.0, n)

    DINO_X = 80          # 恐龙跑到这里就“原地跑”（像 Chrome 里那样，世界往后退）
    DINO_V = 34.0

    def dino(self, t: float, k: float, n: int):
        """恐龙：从左边冲来、超过道士、到 DINO_X 原地跑，跳过迎面的仙人掌，撞上其中一棵。
        返回 (x, 跳起高度, 死了?, 死后秒数)"""
        key = (n, round(t - k, 3))
        plan = self._dino.get(key)
        if plan is None:
            scroll0 = SPEED * (t - k)
            ks = (self.DINO_X + 30) / self.DINO_V
            meets = []
            for i in range(max(0, int((scroll0 - 120) / 96)), int((scroll0 + 900) / 96) + 2):
                cxw, _ = self.cactus(i)
                rel = cxw - scroll0
                tk = (rel + 12) / (self.DINO_V + SPEED)        # 还在冲的时候碰上
                if not 0 < tk < ks:
                    tk = (rel - self.DINO_X - 16) / SPEED      # 原地跑时迎面来
                    if tk < ks:
                        continue
                meets.append(tk)
            meets.sort()
            doom = next((m for m in meets if m > ks + 2.5), ks + 6)
            plan = self._dino[key] = ([m for m in meets if m < doom], doom)
            if len(self._dino) > 8:
                self._dino.clear()
        jumps, doom = plan
        if k < doom:
            x = min(-30 + self.DINO_V * k, self.DINO_X)
            y = 0.0
            for tj in jumps:
                d = k - (tj - 0.3)
                if 0 <= d < 0.7:
                    y = math.sin(d / 0.7 * math.pi) * 17
            return x, y, False, 0.0
        return self.DINO_X - SPEED * (k - doom), 0.0, True, k - doom

    # ------------------------------------------------------------ 画

    def ground(self, g: Gfx, scroll: float, x0: float = 0, x1: float = 128):
        g.d.line((x0, GROUND, x1, GROUND), fill=1)
        for j in range(24):  # 地面上的小石子、凹凸
            wx = j * 23 + (j * 7) % 11
            sx = (wx - scroll) % 552 - 12
            if x0 <= sx <= x1:
                y = GROUND + 2 + (j % 3)
                g.d.line((sx, y, sx + 1 + j % 3, y), fill=1)
                if j % 4 == 0:
                    g.px(sx + 4, GROUND - 1)
                    g.px(sx + 5, GROUND - 1)
                    g.px(sx + 4, GROUND, 0)

    def clouds(self, g: Gfx, t: float):
        for j, (x0, y) in enumerate(((20, 16), (90, 22), (150, 18))):
            x = (x0 - t * 3 - j * 7) % 170 - 20
            g.d.line((x + 3, y, x + 9, y), fill=1)
            g.d.line((x + 1, y + 1, x + 2, y + 1), fill=1)
            g.d.line((x + 10, y + 1, x + 11, y + 1), fill=1)
            g.d.line((x, y + 2, x, y + 2), fill=1)
            g.d.line((x + 12, y + 2, x + 13, y + 2), fill=1)
            g.d.line((x, y + 3, x + 14, y + 3), fill=1)

    def walker(self, g: Gfx, t: float, ghost: float, walking: bool = True, face: str = "normal"):
        """背葫芦拄杖的小道士（穿过仙人掌时虚成散点、荡两圈涟漪）"""
        def back(gg, at):
            at(-12, -27, spr("gourd", _gourd))
            gg.d.line((DX - 6, GROUND - 26, DX - 2, GROUND - 22), fill=1)    # 系绳

        target = _WG if ghost > 0 else g
        if ghost > 0:
            _WG.clear()
        h = figure(target, DX, GROUND, t, legs="walk" if walking else "stand", arm=spr("staff_arm", _staff_arm),
                   arm_at=(-2, -17), face=face, behind=back)
        hx, hy = h["hand"]
        lift = math.sin(t * 8 * math.pi / 4) * 1.5 if walking else 0
        sx = hx + 2
        target.d.line((sx, hy - 10, sx + lift * 0.5, GROUND), fill=1)          # 杖
        target.d.ellipse((sx - 2, hy - 14, sx + 2, hy - 10), outline=1)       # 杖头一个圈
        target.d.line((sx - 1, hy - 1, sx + 1, hy - 1), fill=0)
        if ghost > 0:
            on = _WG.array()
            pix.checker_mask(g, on, 0.5)
            cx, cy = DX, GROUND - 17
            for j in range(2):
                r = ((ghost * 2 + j * 0.5) % 1) * 18
                if r > 2:
                    for i in range(int(r * 2)):
                        a = i / (r * 2) * 2 * math.pi
                        g.px(cx + math.cos(a) * r, cy + math.sin(a) * r * 1.2)

    def frame(self, g: Gfx, t: float, dt: float, speed_up: float = 0.0, show_score: bool = True):
        scroll = SPEED * t + speed_up
        self.clouds(g, t)
        self.ground(g, scroll)
        kind, k, n = self.event(t)
        dino = self.dino(t, k, n) if kind == 0 else None
        ghost = 0.0
        for i, sx, ck in self.visible(scroll):
            spr_ = CACTI[ck]
            pix.blit(g, spr_, sx - spr_.w // 2, GROUND + 1 - spr_.h)
            d = sx - DX
            if abs(d) < 7:
                ghost = (7 - d) / 14
        dead = bool(dino and dino[2])
        face = "wow" if dead and dino[3] < 1.2 else "normal"
        self.walker(g, t, ghost, face=face)
        dead = False
        if dino:
            x, y, dead, dk = dino
            fr = TREX_DEAD if dead else pix.anim(TREX, t, 10)
            if y > 0:
                fr = TREX[0]
            if -30 < x < 140:
                pix.blit(g, fr, x, GROUND - fr.h + 1 - y)
            if dead and dk < 0.2:
                pix.shake(g, t, 1)
        if kind == 1:  # 仙鹤（代替翼龙）扇着翅膀飞过
            x = 140 - k * 18
            y = 11 + math.sin(k * 1.3) * 1.5 - max(0.0, 64 - x) * 0.22
            pix.blit(g, spr("crane_up" if (t * 3) % 1 < 0.5 else "crane_dn",
                            (lambda: _crane(True)) if (t * 3) % 1 < 0.5 else (lambda: _crane(False))), x, y)
        # 字（最后画）
        if show_score:
            sc = int(t * 4) % 100000
            g.text(125, 2, f"无为 {sc:05d}", size=8, align="right")
        if dead and show_score:
            dk = dino[3]
            if dk < 6:
                g.d.rectangle((54, 13, 108, 33), fill=0)
                g.text(81, 15, "GAME OVER", size=8, align="center")
                pix.blit(g, RESTART, 78, 26)
            elif dk < 12:
                m = min(4, int((dk - 6) * 3) + 1)
                g.text(3, 3, "夫唯不争"[:m])
            elif dk < 18:
                m = min(3, int((dk - 12) * 3) + 1)
                g.text(3, 3, "故无尤"[:m])
        self.mx_world(g, scroll, t)
        if dead and dino[3] < 0.4:
            g.mx_level = 4

    def mx_world(self, g: Gfx, scroll: float, t: float):
        for x in range(8):
            g.mx[7, x] = (x + int(scroll / 4)) % 5 != 0
        for i, sx, ck in self.visible(scroll):
            c = int(sx / 16)
            if 0 <= c < 8:
                g.mx[4:7, c] = True
                if c > 0:
                    g.mx[5, c - 1] = True
        c = 2
        g.mx[3, c] = g.mx[4, c] = True
        step = int(t * 4) % 2
        g.mx[5, c] = True
        g.mx[6, c - 1 + step * 2] = True

    def enter(self, g: Gfx, t: float):
        """“未连接到互联网”淡去，地平线从道士脚下向两边拉开，云和计分出现"""
        dt = self.clock(t)
        if t < 1.3:
            g.text(64, 6, "未连接到互联网", align="center")
            g.fade(1 - span(t, 0.8, 1.3))
        w = ease_out(span(t, 0.9, 1.9)) * 70
        if w > 0:
            self.ground(g, 0, DX - w, DX + w)
        self.walker(g, t, 0.0, walking=t > 1.9)
        if t > 1.9:
            self.clouds(g, t)
            g.fade(span(t, 1.9, 2.6), (0, 0, 128, 20))
        if t > 2.0:
            g.text(125, 2, "无为 00000", size=8, align="right")
        self.mx_world(g, 0, t)

    def hold(self, g: Gfx, t: float):
        dt = self.clock(t)
        self.frame(g, t, dt)

    def exit(self, g: Gfx, t: float):
        """头上弹出“已连接”，画面加速卷走、淡出"""
        dt = self.clock(t)
        tt = self.hold_t
        self.frame(g, tt + t, dt, speed_up=ease_in(span(t, 0.2, 1.2)) * 120, show_score=False)
        b = ease_out_back(span(t, 0, 0.35))
        if b > 0.1:
            y = 6 + (1 - b) * 6
            g.d.rounded_rectangle((DX - 22, y - 2, DX + 22, y + 12), radius=3, fill=0, outline=1)
            g.text(DX, y, "已连接", align="center")
        g.fade(1 - span(t, 0.6, 1.2))
