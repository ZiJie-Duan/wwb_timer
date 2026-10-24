"""x6 赛博歇（三）：网络——ping 天庭、断网小恐龙"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import cloud, typewriter
from ..engine.gfx import Gfx, Sprite, text_width
from ..engine.scene import Rest, register
from .x6_common import window

# ====================================================================== ping 天庭

HEART = Sprite("""
.##.##.
#######
#######
.#####.
..###..
...#...
""")
MX_HEART = [0x00, 0x66, 0xFF, 0xFF, 0x7E, 0x3C, 0x18, 0x00]
MX_Q = [0x3C, 0x66, 0x06, 0x0C, 0x18, 0x18, 0x00, 0x18]


@register
class PingHeaven(Rest):
    id = "x6.ping"
    name = "问天"
    desc = "终端里 ping 天庭，数据包飞进云里一去不回，请求超时；改 ping 本心，<1ms 就回来了——不出户，知天下"
    T = {"enter": 2.4, "exit": 1.2}
    C = 50.0
    ANT = (106, 47)        # 天线顶
    GATE = (106, 12)       # 南天门（云上）

    def setup(self):
        self._ht = 0.0

    # ------------------------------------------------------------ 剧本：u → 终端行

    def script(self, u: float, n: int):
        """返回 (终端行, 正在打的行, 数据包事件[(发出时刻, 去天庭?)]）"""
        heaven_ok = self.ctx.finished and n == 0
        lines = []
        typing = None
        cmd1 = "> ping 天庭"
        if u < 1.4:
            typing = (cmd1, u / 1.4)
        else:
            lines.append(cmd1)
        for j in range(3):
            t_rep = 5.0 + j * 4.0
            if u >= t_rep:
                if heaven_ok and j == 2:
                    lines.append("天庭:功德已收")
                else:
                    lines.append("请求超时。")
        if u >= 17.0:
            lines.append("丢包 100%" if not heaven_ok else "丢包 66%")
        cmd2 = "> ping 本心"
        if 18.5 <= u < 20.0:
            typing = (cmd2, (u - 18.5) / 1.5)
        elif u >= 20.0:
            lines.append(cmd2)
        for j in range(3):
            if u >= 21.2 + j * 1.2:
                lines.append("本心 <1ms")
        return lines, typing

    def packets(self, u: float):
        """(进度 0..1, 去天庭?)"""
        out = []
        for j in range(3):
            s = 1.6 + j * 4.0
            if s <= u < s + 3.6:
                out.append((span(u, s, s + 2.4), True, u - s))
        for j in range(3):
            s = 20.4 + j * 1.2
            if s <= u < s + 0.8:
                out.append((span(u, s, s + 0.8), False, u - s))
        return out

    # ------------------------------------------------------------ 零件

    def heaven(self, g: Gfx, t: float, n: int, open_: float = 0.0):
        """云上一座南天门"""
        gx, gy = self.GATE
        cloud(g, gx, gy + 9, 34, 9, seed=3)
        g.d.line((gx - 12, gy - 6, gx + 12, gy - 6), fill=1)       # 门楣
        g.d.line((gx - 14, gy - 8, gx + 14, gy - 8), fill=1)
        g.d.line((gx - 14, gy - 8, gx - 16, gy - 10), fill=1)      # 飞檐
        g.d.line((gx + 14, gy - 8, gx + 16, gy - 10), fill=1)
        for x in (gx - 9, gx + 9):                                  # 两根柱
            g.d.rectangle((x - 1, gy - 5, x, gy + 5), fill=1)
        g.d.rectangle((gx - 3, gy - 5, gx + 3, gy - 3), outline=1)  # 匾
        # 云里藏的几颗星
        for i in range(5):
            x = 80 + rand(i, 11) * 46
            y = 2 + rand(i + 9, 11) * 26
            if noise(t * 0.7 + i * 2, i) > 0.45 and not (gx - 18 < x < gx + 18 and y > gy - 10):
                g.px(x, y)

    def antenna(self, g: Gfx, t: float, pulse: float = 0.0):
        ax, ay = self.ANT
        # 小电脑
        g.d.rectangle((ax - 10, ay + 4, ax + 10, ay + 14), outline=1)
        g.d.rectangle((ax - 8, ay + 6, ax + 8, ay + 12), outline=1)
        g.d.line((ax - 6, ay + 16, ax + 6, ay + 16), fill=1)
        g.d.line((ax, ay + 14, ax, ay + 16), fill=1)
        g.d.line((ax + 8, ay + 4, ax + 12, ay - 3), fill=1)       # 天线
        g.px(ax + 12, ay - 4)
        if pulse > 0:  # 屏幕里一颗心跳
            s = 1 if pulse < 0.5 else 0
            g.blit(HEART, ax - 3, ay + 6 - s)

    def path(self, k: float):
        ax, ay = self.ANT[0] + 12, self.ANT[1] - 4
        gx, gy = self.GATE
        x = lerp(ax, gx + 2, k) + math.sin(k * math.pi * 2) * 6
        y = lerp(ay, gy + 10, k)
        return x, y

    def draw(self, g: Gfx, u: float, n: int, t: float, term_a: float = 1.0):
        lines, typing = self.script(u, n)
        quote = u >= 26.0
        # 终端
        window(g, 0, 0, 74, 63, "cmd")
        if not quote:
            shown = lines[-5:] if typing is None else lines[-4:]
            y = 12
            for s in shown:
                g.text(3, y, s, size=8)
                y += 10
            if typing is not None:
                s, k = typing
                n_ch = int(clamp(k) * len(s))
                w = g.text(3, y, s[:n_ch], size=8)
                if blink(t, 0.5):
                    g.d.rectangle((4 + w, y + 6, 7 + w, y + 7), fill=1)
            elif blink(t, 0.8) and len(shown) < 5:
                g.d.rectangle((4, y + 6, 7, y + 7), fill=1)
        else:  # cls，屏上只留一句：不出户，知天下；不窥牖，见天道（《道德经》第四十七章）
            a = 1 - span(u, self.C - 2.0, self.C - 0.3)
            typewriter(g, 37, 16, "不出户", (u - 26.5) * a, cps=2, align="center")
            typewriter(g, 37, 34, "知天下", (u - 28.5) * a, cps=2, align="center")
            if blink(t, 0.8) and a > 0.5:
                g.d.rectangle((60, 52, 63, 53), fill=1)
        # 天上、地上
        self.heaven(g, t, n)
        pk = self.packets(u)
        heart = 0.0
        for k, up, age in pk:
            if up:
                if k < 1:
                    for d in range(0, int(k * 20)):  # 走过的虚线
                        if d % 3 == 0:
                            x, y = self.path(d / 20)
                            g.px(x, y)
                    x, y = self.path(k)
                    g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
                else:  # 到了云里：散成几点，冒个问号
                    p = span(age, 2.4, 3.6)
                    gx, gy = self.GATE
                    for i in range(6):
                        a = i / 6 * 2 * math.pi
                        g.px(gx + 2 + math.cos(a) * (2 + p * 7), gy + 10 + math.sin(a) * (1 + p * 3))
                    if p < 0.8:
                        g.text(gx + 14, gy + 4 - p * 4, "?", size=8)
            else:  # 本心：出门绕一个小圈就回来
                ax, ay = self.ANT[0] + 12, self.ANT[1] - 4
                a = k * 2 * math.pi
                x, y = ax - 6 + math.cos(a) * 6, ay - math.sin(a) * 5
                g.d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=1)
                heart = 1.0 - k
        if u >= 20.4:  # 本心一直在跳
            heart = max(heart, 0.3 + 0.7 * ((u * 1.2) % 1.0 < 0.5))
        self.antenna(g, t, heart)
        # 点阵
        if any(up and k < 1 for k, up, _ in pk):
            r = (t * 4) % 5
            for yy in range(8):
                for xx in range(8):
                    d = math.hypot(xx - 3.5, (yy - 8) * 1.0)
                    if abs(d - r) < 0.6 or abs(d - r - 2.5) < 0.6:
                        g.mx[yy, xx] = True
        elif any(up for k, up, _ in pk):
            g.mx_rows(MX_Q)
        elif u >= 20.4:
            g.mx_rows(MX_HEART)
            if (u * 1.2) % 1.0 > 0.5:
                g.mx[1, :] = False
                g.mx[6, :] = False
        else:
            g.mx[7, 2:6] = True
            g.mx[6, 3:5] = True
            g.mx_set(4, 5 - int(t * 2) % 5)

    def enter(self, g: Gfx, t: float):
        k = ease_out_back(span(t, 0, 0.6))
        if t < 0.6:
            w, h = 37 * k, 31.5 * k
            if w > 2 and h > 2:
                g.d.rectangle((37 - w, 31.5 - h, 37 + w, 31.5 + h), outline=1)
        else:
            window(g, 0, 0, 74, 63, "cmd")
            if blink(t, 0.5):
                g.d.rectangle((4, 18, 7, 19), fill=1)
        a = span(t, 0.5, 1.6)
        if a > 0:
            gx, gy = self.GATE
            sx = self.GATE
            self.GATE = (gx, gy - (1 - ease_out(a)) * 30)
            self.heaven(g, t, 0)
            self.GATE = sx
        b = ease_out(span(t, 1.0, 2.0))
        if b > 0:
            ax, ay = self.ANT
            self.ANT = (ax, ay + (1 - b) * 30)
            self.antenna(g, t)
            self.ANT = (ax, ay)
        g.mx[7, 2:6] = t > 1.0
        g.mx[6, 3:5] = t > 1.2

    def hold(self, g: Gfx, t: float):
        self._ht = t
        n = int(t // self.C)
        self.draw(g, t - n * self.C, n, t)

    def exit(self, g: Gfx, t: float):
        n = int(self._ht // self.C)
        self.draw(g, self._ht - n * self.C, n, self._ht + t)
        k = ease_in(span(t, 0, 1.1))
        g.d.rectangle((0, 0, 127, int(64 * k)), fill=0)  # 像清屏一样从上往下抹掉
        if k < 1:
            g.d.line((0, int(64 * k), 127, int(64 * k)), fill=1)
        g.mx[:int(8 * k), :] = False


# ====================================================================== 不争（断网小恐龙）

WALKER = Sprite("""
       ##
      ####
     ######
      .##.
     #....#.
    #......#
    #....#.#
    #......#
  ## #.....#
 #..# #...#
 #..#..###.
  ##.#######
   #.#.#.#..#
  #.#.#.#.#..#
  #..#.#.#.#.#
  #.#.#.#.####
  #..#.#.#.#
  #.#.#.#.#.#
  #..#.#.#.#.#
 #.#.#.#.#.#.#
 #############
""")
LEGS = (Sprite("""
   ##    ##
  ##      ##
"""), Sprite("""
     ####
     ## ##
"""))
DINO = Sprite("""
         ########
        ##.#######
        ##########
        ##########
        #####
        ########
#      #####
#     #######
##   #########
############.#
###########
 #########
  #######
   ###.##
   ##   #
   #    ##
""")
DINO2 = Sprite("""
         ########
        ##.#######
        ##########
        ##########
        #####
        ########
#      #####
#     #######
##   #########
############.#
###########
 #########
  #######
   ##  ###
   #
   ##
""")
DINO_DEAD = Sprite("""
         ########
        #.#.######
        ##.#######
        #.#.######
        ##########
        #####.....
#      #####
#     #######
##   #########
############.#
###########
 #########
  #######
   ###.##
   ##   #
   #    ##
""")
CACTI = (Sprite("""
   ##
   ##  #
#  ## ##
## ####
 #####
   ##
   ##
   ##
   ##
"""), Sprite("""
  ##
  ## #
# ####
####
  ##
  ##
  ##
"""), Sprite("""
   ##   ##
#  ##   ## #
## ## # ####
 ###### ##
   #### ##
   ##   ##
   ##   ##
   ##   ##
"""))
GROUND = 54
WX = 22                 # 道士在屏幕上的位置
SPEED = 12.0            # 世界卷动（像素/秒）：慢慢走
GAP = 70.0              # 仙人掌平均间距


def crane(g: Gfx, x: float, y: float, flap: float):
    """仙鹤（代替翼龙）：长颈向前，腿拖在后，一扇一扇"""
    g.d.ellipse((x - 5, y - 2, x + 4, y + 2), fill=1)
    g.d.line((x + 3, y - 1, x + 12, y - 3), fill=1)
    g.d.rectangle((x + 12, y - 4, x + 13, y - 3), fill=1)
    g.d.line((x + 14, y - 3, x + 18, y - 2), fill=1)
    g.d.line((x - 5, y + 1, x - 15, y + 2), fill=1)
    g.d.polygon([(x - 4, y), (x + 3, y), (x - 6, y - 10 * flap)], fill=1)


@register
class NoContend(Rest):
    id = "x6.buzheng"
    name = "不争"
    desc = "断网小恐龙的跑酷里换成一个背葫芦的道士：他不跳，慢慢走，仙人掌从身上穿过去；小恐龙冲过他又撞了——夫唯不争，故无尤"
    T = {"enter": 2.6, "exit": 1.2}
    EV = 42.0

    def setup(self):
        self._ht = 0.0

    # ------------------------------------------------------------ 世界：t 的纯函数

    def cacti(self, scroll: float):
        """屏幕上的仙人掌：[(屏幕 x, 精灵, 世界 x)]"""
        out = []
        k0 = int((scroll - 20) // GAP)
        for k in range(k0, k0 + 4):
            if k < 1:
                continue
            wx = k * GAP + rand(k, self.seed) * 30
            sx = wx - scroll + WX
            spr = CACTI[int(rand(k + 99, self.seed) * 3)]
            if -16 < sx < 130:
                out.append((sx, spr, wx))
        return out

    def ground(self, g: Gfx, scroll: float):
        g.d.line((0, GROUND, 127, GROUND), fill=1)
        for i in range(14):  # 地上的小石子
            base = (i * 37 + rand(i, 5) * 20)
            x = (base - scroll) % 140 - 6
            y = GROUND + 2 + int(rand(i, 6) * 6)
            g.d.line((x, y, x + (1 if i % 3 else 2), y), fill=1)

    def clouds(self, g: Gfx, t: float):
        for i in range(2):
            x = (60 + i * 70 - t * 3) % 160 - 20
            y = 14 + i * 9
            g.d.line((x, y, x + 18, y), fill=1)
            g.d.arc((x + 2, y - 6, x + 10, y + 2), 180, 360, fill=1)
            g.d.arc((x + 8, y - 8, x + 16, y + 2), 200, 360, fill=1)

    def walker(self, g: Gfx, t: float, ghost: float = 0.0, walking: bool = True):
        x, y = WX, GROUND - WALKER.h - 2
        g.blit(WALKER, x, y)
        g.blit(LEGS[int(t * 3) % 2 if walking else 1], x + 1, y + WALKER.h)
        g.d.line((x + 14, y + 7, x + 14 + (1 if int(t * 3) % 2 else 0), GROUND), fill=1)  # 杖
        if ghost > 0:  # 仙人掌穿身而过：身子虚掉
            g.fade(1 - ghost * 0.75, (x, y, x + 16, GROUND))

    def score(self, g: Gfx, t: float):
        g.text(126, 2, f"{int(t * 3) % 100000:05d}", size=8, align="right")
        g.text(92, 2, "无为", size=8, align="right")

    # ------------------------------------------------------------ 小恐龙彩蛋

    DINO_V = 18.0  # 恐龙在屏幕上的速度

    def dino_event(self, g: Gfx, k: float, scroll: float):
        """k = 事件开始后的秒数：从左后方冲来，跳过仙人掌，超过道士，最后撞上命中注定的那一棵"""
        x = -20 + k * self.DINO_V
        y = GROUND - DINO.h
        doom = self._doom
        if doom is not None:
            sx_doom = doom - scroll + WX
            if x + 13 >= sx_doom:  # 撞上了：停在世界里，跟着地面往后退
                g.blit(DINO_DEAD, sx_doom - 13, y)
                if sx_doom - 13 > 48:
                    g.text(sx_doom - 5, y - 9, "GAME OVER", size=8, align="center")
                return True
        jump = 0.0
        for sx, spr, wx in self.cacti(scroll):
            if wx == doom:
                continue
            d = sx - x
            if -18 < d < 26:
                p = clamp((26 - d) / 44)
                jump = max(jump, math.sin(p * math.pi) * 22)
        g.blit(DINO if int(k * 8) % 2 or jump > 0 else DINO2, x, y - jump)
        return False

    def pick_doom(self, n: int):
        """第 n 次事件里恐龙会撞上的仙人掌（它前头那棵在屏幕右半边）"""
        T0 = n * self.EV + 6.0
        for kk in range(max(1, int(T0 * SPEED / GAP) - 2), int(T0 * SPEED / GAP) + 200):
            wx = kk * GAP + rand(kk, self.seed) * 30
            # 恐龙前沿追上这棵的时刻：-20 + 13 + v·k = wx - (T0 + k)·SPEED + WX
            kh = (wx - T0 * SPEED + WX + 7) / (self.DINO_V + SPEED)
            sx = wx - (T0 + kh) * SPEED + WX
            if kh > 3 and sx > 84:
                return wx
        return None

    def frame(self, g: Gfx, t: float):
        scroll = t * SPEED
        n = int(t // self.EV)
        k = t - n * self.EV - 6.0       # 每轮第 6 秒起有事
        kind = int(rand(n, self.seed) * 2) if n > 0 else 0
        self.clouds(g, t)
        self.ground(g, scroll)
        cs = self.cacti(scroll)
        ghost = 0.0
        for sx, spr, wx in cs:
            g.blit(spr, sx, GROUND - spr.h + 1)
            overlap = clamp(1 - abs((sx + spr.w / 2) - (WX + 7)) / 12)
            ghost = max(ghost, overlap)
        crashed = False
        if kind == 0 and 0 <= k < 16:  # 小恐龙
            if getattr(self, "_doom_n", None) != n:
                self._doom_n = n
                self._doom = self.pick_doom(n)
            crashed = self.dino_event(g, k, scroll)
        self.walker(g, t, ghost)
        if ghost > 0.6:  # 穿过的一瞬：两圈小涟漪
            for r in (9, 13):
                for i in range(0, 12):
                    a = i / 12 * 2 * math.pi
                    if i % 2 == int(t * 6) % 2:
                        g.px(WX + 7 + math.cos(a) * r, GROUND - 12 + math.sin(a) * r * 1.2)
        if kind == 1 and 2 < k < 12:  # 仙鹤飞过
            p = span(k, 2, 12)
            crane(g, lerp(140, -30, p), 22 + math.sin(p * 9) * 3, math.sin(t * 7))
        self.score(g, t)
        if crashed:  # 夫唯不争，故无尤（《道德经》第八章）
            k0 = self._crash_k if getattr(self, "_crash_n", None) == n else k
            if getattr(self, "_crash_n", None) != n:
                self._crash_n, self._crash_k = n, k
            a = 1 - span(k, 15, 16)
            typewriter(g, 2, 2, "夫唯不争", (k - k0 - 0.8) * a, cps=3)
            typewriter(g, 2, 15, "故无尤", (k - k0 - 2.6) * a, cps=3)
        self.mx_world(g, scroll, t)

    def mx_world(self, g: Gfx, scroll: float, t: float):
        g.mx[7, :] = True
        for sx, spr, wx in self.cacti(scroll):
            c = int((sx + 4) / 16)
            if 0 <= c < 8:
                g.mx[5:7, c] = True
                g.mx_set(c, 4)
        g.mx[3:7, 1] = True       # 道士
        g.mx[2, 1] = True
        g.mx_set(2, 6 - int(t * 3) % 2)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        # 未连接到互联网（Chrome 断网页）→ 地平线拉开 → 道士起步
        a = 1 - span(t, 1.1, 1.5)
        if a > 0:
            g.text(64, 6, "未连接到互联网", align="center")
            if a < 1:
                g.fade(a, (0, 0, 128, 20))
        w = ease_out(span(t, 0.9, 1.9))
        g.d.line((WX, GROUND, WX + (127 - WX) * w, GROUND), fill=1)
        g.d.line((WX, GROUND, WX - WX * w, GROUND), fill=1)
        x, y = WX, GROUND - WALKER.h - 2
        g.blit(WALKER, x, y)
        g.blit(LEGS[1], x + 1, y + WALKER.h)
        g.d.line((x + 14, y + 7, x + 14, GROUND), fill=1)
        if t > 1.9:
            self.score(g, 0)
            self.clouds(g, 0)
        g.mx[7, :] = w > 0.5
        g.mx[3:7, 1] = True
        g.mx[2, 1] = True

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        # 网连上了：画面加速卷走，淡出
        tt = self._ht + t + ease_in(span(t, 0, 1.1)) * 6
        self.frame(g, tt)
        g.fade(1 - span(t, 0.5, 1.2))
        if t < 0.8:
            g.d.rectangle((40, 22, 88, 36), fill=0, outline=1)
            g.text(64, 24, "已连接", align="center")
