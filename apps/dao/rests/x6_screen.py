"""x6 赛博歇（二）：屏幕——太极屏保、心斋、坐忘、归根（像素风，小道士出镜）"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from ..engine.symbols import mx_taiji, taiji
from .x6_common import FLOOR, Clock, crossed, cushion, cyc, mx_icon, pbar, sit, spr, window


def floor_line(g: Gfx, wall: bool = True):
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-30, 170, 18):
        g.d.line((x, FLOOR + 1, x - 10, 63), fill=1)
    pix.checker(g, (0, FLOOR + 2, 128, 64), 0.125)
    if wall:
        g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)


def tri(u: float) -> float:
    """三角波 0→1→0，周期 2"""
    u = u % 2.0
    return u if u < 1 else 2 - u


# ====================================================================== 太极屏保

SX0, SY0, SX1, SY1 = 57, 16, 103, 43        # 显像管可视区（含）
DAO = Sprite("""
####   ###   ###
##  # ## ## ## ##
##  # ##### ## ##
##  # ## ## ## ##
####  ## ##  ###
""")
LOGO_W, LOGO_H = 28, 9


def _tv():
    """老式显像管电视 74×44：木纹机壳、鼓起的圆角屏框、右侧旋钮与喇叭栅、底座"""
    p = Part(74, 46)
    p.shape("rounded_rectangle", (0, 0, 73, 39), radius=4, fill=1)
    p.d.rounded_rectangle((2, 2, 55, 37), radius=6, fill=0)        # 屏框
    p.d.rounded_rectangle((3, 3, 54, 36), radius=6, outline=1)
    p.d.rounded_rectangle((5, 5, 52, 34), radius=5, fill=0)
    for y in range(6, 34, 4):                                      # 机壳木纹
        p.px(1, y, 0)
    p.d.rectangle((58, 3, 71, 36), fill=0)                         # 右侧面板
    p.d.rectangle((59, 4, 70, 35), outline=1)
    for i, cy in enumerate((9, 19)):                               # 两个旋钮（带指示）
        p.d.ellipse((61, cy - 3, 68, cy + 4), outline=1)
        p.d.ellipse((63, cy - 1, 66, cy + 2), fill=1)
        p.px(64 + i, cy - 2)
    for y in range(26, 34, 2):                                     # 喇叭栅
        p.d.line((61, y, 68, y), fill=1)
    p.shape("rectangle", (6, 40, 67, 41), fill=1)                  # 底座
    p.shape("polygon", [(10, 42), (16, 42), (14, 45), (11, 45)], fill=1)
    p.shape("polygon", [(57, 42), (63, 42), (62, 45), (59, 45)], fill=1)
    p.dither([(60, 40), (68, 40), (68, 41), (60, 41)], 0.5, 0)
    return p.sprite()


TV_X, TV_Y = 52, 11


def _remote():
    p = Part(4, 7)
    p.shape("rectangle", (0, 0, 3, 6), fill=1)
    p.px(1, 1, 0), p.px(2, 3, 0), p.px(1, 3, 0)
    return p.sprite()


@register
class TaijiSaver(Rest):
    id = "x6.dvd"
    name = "太极屏保"
    desc = "小道士盘坐在老电视前，看太极屏保斜着弹来弹去；差一点进角他就探身，真撞进角落时他跳起来欢呼——众妙之门"
    T = {"enter": 2.6, "exit": 1.2}
    TX, TY = 5.5, 5.0                        # 横走一趟 5.5 秒（22 像素）、竖走一趟 5 秒（20 像素）→ 55 秒进一次角
    OFF = 15.0                               # 第一次进角在 t = 40
    X = 24

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)

    # ------------------------------------------------------------ 运动（t 的函数）

    def pos(self, t: float):
        u, v = (t + self.OFF) / self.TX, (t + self.OFF) / self.TY
        return SX0 + 1 + tri(u) * (SX1 - SX0 - LOGO_W - 1), SY0 + 1 + tri(v) * (SY1 - SY0 - LOGO_H - 1)

    def corner(self, t: float) -> float:
        """距上一次进角的秒数"""
        p = self.TX * self.TY * 2  # 55
        return (t + self.OFF) % p if t + self.OFF >= p else 1e9

    def near(self, t: float):
        """下一次撞左右墙的时刻、届时离上下墙的像素数、上一次撞墙的时刻"""
        u = (t + self.OFF) / self.TX
        nxt = (math.floor(u) + 1) * self.TX - self.OFF
        prv = math.floor(u) * self.TX - self.OFF
        return nxt, self._ydist(nxt), prv, self._ydist(prv)

    def _ydist(self, t):
        v = tri((t + self.OFF) / self.TY)
        return min(v, 1 - v) * (SY1 - SY0 - LOGO_H - 1)

    # ------------------------------------------------------------ 画

    def logo(self, g: Gfx, x: float, y: float):
        ix, iy = int(round(x)), int(round(y))
        g.d.ellipse((ix, iy, ix + 8, iy + 8), fill=0)
        taiji(g, ix + 4, iy + 4, 4, (x - SX0) / 4.0)
        g.blit(DAO, ix + 11, iy)
        g.d.ellipse((ix + 10, iy + 6, ix + 27, iy + 8), fill=1)   # 碟片
        g.d.line((ix + 17, iy + 7, ix + 20, iy + 7), fill=0)

    def tv(self, g: Gfx, glow: bool = False):
        x, y = TV_X, TV_Y
        # 兔耳天线
        g.d.line((x + 30, y, x + 20, y - 10), fill=1)
        g.d.line((x + 32, y, x + 44, y - 9), fill=1)
        g.d.rectangle((x + 19, y - 11, x + 20, y - 10), fill=1)
        g.d.rectangle((x + 44, y - 10, x + 45, y - 9), fill=1)
        g.d.ellipse((x + 27, y - 3, x + 35, y + 1), fill=1)
        pix.blit(g, spr("tv", _tv), x, y)
        if glow:  # 撞角：屏框一闪
            g.d.rounded_rectangle((x + 3, y + 3, x + 54, y + 36), radius=6, fill=1)
            g.d.rounded_rectangle((x + 5, y + 5, x + 52, y + 34), radius=5, fill=0)

    def glass(self, g: Gfx):
        """屏幕玻璃左上角的反光"""
        g.d.arc((SX0, SY0, SX0 + 14, SY0 + 12), 190, 250, fill=1)

    def wall_spark(self, g: Gfx, t: float):
        """撞墙：接触点迸三道短线（0.3 秒）"""
        nxt, dn, prv, dp = self.near(t)
        k = t - prv
        if 0 <= k < 0.3:
            x, y = self.pos(prv)
            right = x > (SX0 + SX1) / 2
            cx = SX1 - 1 if right else SX0 + 1
            cy = y + LOGO_H / 2
            s = -1 if right else 1
            r = 2 + k * 10
            for a in (-0.7, 0, 0.7):
                g.d.line((cx + s * math.cos(a) * r, cy + math.sin(a) * r,
                          cx + s * math.cos(a) * (r + 2), cy + math.sin(a) * (r + 2)), fill=1)
        vk = (t + self.OFF) / self.TY
        kv = (vk - math.floor(vk)) * self.TY
        if kv < 0.3:
            tp = math.floor(vk) * self.TY - self.OFF
            x, y = self.pos(tp)
            bottom = y > (SY0 + SY1) / 2
            cy = SY1 - 1 if bottom else SY0 + 1
            cx = x + LOGO_W / 2
            s = -1 if bottom else 1
            r = 2 + kv * 10
            for a in (-0.7, 0, 0.7):
                g.d.line((cx + math.sin(a) * r, cy + s * math.cos(a) * r,
                          cx + math.sin(a) * (r + 2), cy + s * math.cos(a) * (r + 2)), fill=1)

    def gag(self, t: float) -> float:
        """拍电视：以进角为 0 的每轮第 22 秒起，6 秒（信号花了 → 走过去拍两下 → 走回来）；返回事件内秒数或 -1"""
        c = self.corner(t)
        k = (t + self.OFF) % 55 - 22
        return k if 0 <= k < 7 and t > 5 else -1

    def watcher(self, g: Gfx, t: float, dt: float):
        """小道士：看电视的各种反应。返回 (是否在欢呼, 拍电视冲击)"""
        c = self.corner(t)
        nxt, dn, prv, dp = self.near(t)
        gk = self.gag(t)
        cushion(g, self.X)
        if c < 4.5:  # 进角：跳起来欢呼
            hop = abs(math.sin(c * 7)) * 5 * (1 - c / 4.5) if c < 3 else 0
            daoshi(g, self.X, FLOOR - 3 - hop, "raise", t, face="happy")
            return True, False
        if gk >= 0:  # 信号花了：起身走过去拍电视侧面
            if gk < 1.2:
                sit(g, self.X, t, face="wow")
            elif gk < 2.2:
                daoshi(g, lerp(self.X, 40, span(gk, 1.2, 2.2)), FLOOR - 3 if gk < 1.3 else FLOOR, "walk", t)
            elif gk < 4.4:
                hit = (gk - 2.2) % 1.1 < 0.25
                daoshi(g, 40, FLOOR, "point" if hit else "idle", t, face="wow" if hit else "normal")
                return False, hit
            elif gk < 5.6:
                daoshi(g, lerp(40, self.X, span(gk, 4.4, 5.6)), FLOOR, "walk", t, flip=True)
            else:
                sit(g, self.X, t, face="happy")
            return False, False
        # 差一点：撞墙前 1.5 秒探身（瞪眼），撞完差一点就垂头叹气
        if dn < 3.5 and nxt - t < 1.6:  # 直起身跪着往前凑
            h = figure(g, self.X + 2, FLOOR - 3, t, legs="kneel", arm="offer", face="wow")
            hx, hy = h["hand"]
            pix.blit(g, spr("remote", _remote), hx - 2, hy - 5)
        elif dp < 3.5 and 0 <= t - prv < 1.4 and t - prv < c:
            sit(g, self.X, t, face="sleep", head="bow")
            if crossed(t - prv, dt, 0.25):
                self.puffs.emit(self.X + 10, FLOOR - 22, vx=6, vy=-2, life=0.8, rmax=1.4, spread=0)
        else:
            h = sit(g, self.X, t, face="normal", arm="offer")
            hx, hy = h["hand"]
            pix.blit(g, spr("remote", _remote), hx - 2, hy - 5)
        return False, False

    def frame(self, g: Gfx, t: float, dt: float, screen: str = "saver", p: float = 1.0):
        floor_line(g)
        c = self.corner(t)
        gk = self.gag(t)
        cheer, hit = self.watcher(g, t, dt)
        if hit:
            pix.shake(g, t, 1.0)
        self.tv(g, glow=c < 1.0 and (c * 6) % 1 < 0.5)
        if screen == "saver":
            noisy = 0.3 <= gk < 4.4 and not (gk > 3.3)
            if noisy:  # 信号花了：雪花 + 一条滚动亮带
                for i in range(120):
                    x = SX0 + int(rand(i + int(t * 20) * 131, 7) * (SX1 - SX0))
                    y = SY0 + int(rand(i + int(t * 20) * 131, 9) * (SY1 - SY0))
                    g.px(x, y)
                by = SY0 + ((t * 25) % (SY1 - SY0))
                g.d.rectangle((SX0, by, SX1, min(by + 2, SY1)), fill=1)
            else:
                x, y = self.pos(t)
                self.logo(g, x, y)
                self.wall_spark(g, t)
        self.glass(g)
        if c < 4.5:  # 撞角：彩纸 / 金星
            if crossed(c, dt, 0.0) or c < dt:
                pass
            if int((t) * 6) != int((t - dt) * 6) and c < 3:
                self.sparks.burst(self.X + rand(int(t * 6), 3) * 30 - 10, 20, 4, 30, up=20, life=1.0, gravity=40)
            if c < dt * 1.5:
                self.sparks.burst(SX0 + 2, SY0 + 2, 16, 34, up=10, life=0.9, gravity=30)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if c < 0.07:
            pix.flash(g)
        if 0.6 < c < 9:  # “众妙之门” 逐字写出，停一会儿淡去
            n = min(4, int((c - 0.6) * 4) + 1)
            g.d.rectangle((2, 1, 53, 15), fill=0)       # 字的底板（彩纸不压字）
            g.text(4, 3, "众妙之门"[:n])
            if c > 7:
                g.fade(1 - span(c, 7, 9), (0, 0, 52, 16))
        # 点阵：旋转的太极；进角时一圈烟花
        if c < 2.5:
            r = c * 4
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.7:
                        g.mx[yy, xx] = True
            g.mx_level = 1 + int(5 * (1 - c / 2.5))
        else:
            x, _ = self.pos(t)
            mx_taiji(g, (x - SX0) / 4.0)

    def enter(self, g: Gfx, t: float):
        """遥控一按：显像管开机，一点拉成亮线、撑满白光再褪去，“无信号”闪两下，太极屏保淡入"""
        dt = self.clock(t)
        floor_line(g)
        cushion(g, self.X)
        h = sit(g, self.X, t, face="normal", arm="point" if t < 0.5 else "offer")
        if t >= 0.5:
            hx, hy = h["hand"]
            pix.blit(g, spr("remote", _remote), hx - 2, hy - 5)
        else:
            hx, hy = h["hand"]
            pix.blit(g, spr("remote", _remote), hx, hy - 3)
            if (t * 10) % 2 < 1:
                pix.dotted(g, hx + 5, hy - 2, TV_X - 2, hy - 6, 2)
        self.tv(g)
        cx, cy = (SX0 + SX1) / 2, (SY0 + SY1) / 2
        if 0.5 <= t < 0.7:
            g.d.rectangle((cx - 1, cy, cx + 1, cy), fill=1)
        elif 0.7 <= t < 1.0:
            w = (SX1 - SX0) / 2 * ease_out(span(t, 0.7, 1.0))
            g.d.line((cx - w, cy, cx + w, cy), fill=1)
        elif 1.0 <= t < 1.3:
            hh = (SY1 - SY0) / 2 * ease_out(span(t, 1.0, 1.3))
            g.d.rectangle((SX0, cy - hh, SX1, cy + hh), fill=1)
        elif 1.3 <= t < 1.6:
            g.d.rectangle((SX0, SY0, SX1, SY1), fill=1)
            g.fade(1 - span(t, 1.3, 1.6), (SX0, SY0, SX1 + 1, SY1 + 1))
        self.glass(g)
        if 1.6 <= t < 2.3 and (t - 1.6) % 0.35 < 0.22:
            g.text(cx, cy - 5, "无信号", align="center")
        if t >= 2.1:
            x, y = self.pos(0.0)
            self.logo(g, x, y)
            g.fade(span(t, 2.1, 2.6), (SX0, SY0, SX1 + 1, SY1 + 1))
        mx_taiji(g, t)

    def hold(self, g: Gfx, t: float):
        dt = self.clock(t)
        self.frame(g, t, dt)

    def exit(self, g: Gfx, t: float):
        """显像管关机：画面压扁成一条亮线，再缩成一点熄灭"""
        dt = self.clock(t)
        tt = self.hold_t
        floor_line(g)
        cushion(g, self.X)
        sit(g, self.X, tt + t, face="sleep" if t > 0.6 else "normal")
        self.tv(g)
        cx, cy = (SX0 + SX1) / 2, (SY0 + SY1) / 2
        if t < 0.45:
            hh = (SY1 - SY0) / 2 * (1 - ease_in(t / 0.45))
            g.d.rectangle((SX0, cy - hh, SX1, cy + hh), fill=1)
        elif t < 0.8:
            w = (SX1 - SX0) / 2 * (1 - ease_in(span(t, 0.45, 0.8)))
            g.d.line((cx - w, cy, cx + w, cy), fill=1)
        elif t < 1.0:
            g.d.rectangle((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
        self.glass(g)
        g.fade(1 - span(t, 0.9, 1.2))
        mx_taiji(g, tt)


# ====================================================================== 心斋

ZANIAN = "名利怒忧惧贪妒愁悔躁怨惑"
EXTS = (".tmp", ".log", ".bak", ".exe", ".dll")
# 每个杂念一个小图形（5×5）：名=奖章 利=方孔钱 怒=青筋 忧=雨云 惧=小鬼 贪=钱袋 妒=眼 愁=乱线 悔=裂心 躁=火 怨=乌云 惑=问号
PICTO = pix.frames("""
.###.
#####
.###.
.#.#.
#...#
---
.###.
##.##
#...#
##.##
.###.
---
##.##
#...#
.....
#...#
##.##
---
.###.
#####
.....
#.#.#
.#.#.
---
.###.
#####
#.#.#
#####
#.#.#
---
.#.#.
..#..
.###.
#####
.###.
---
.....
.###.
#.#.#
.###.
.....
---
#.#..
.#.#.
#.#.#
.#.#.
..#.#
---
##.##
####.
.#.#.
..#..
.....
---
..#..
.##..
.###.
##.##
.###.
---
.###.
#####
.###.
..#..
.#...
---
.###.
#...#
..##.
.....
..#..
""")


def _file_icon():
    """文件图标 11×13：折角、一道阴影边、中间留 5×5 画图"""
    p = Part(11, 13)
    p.shape("polygon", [(0, 0), (7, 0), (10, 3), (10, 12), (0, 12)], fill=1)
    p.d.polygon([(1, 1), (6, 1), (6, 4), (9, 4), (9, 11), (1, 11)], fill=0)
    p.d.line((7, 1, 9, 3), fill=1)
    p.d.line((10, 4, 10, 12), fill=1)
    return p.sprite()


def _bin_can():
    """回收站桶身 18×18：口沿、竖棱、循环箭头小标、背光网点"""
    p = Part(18, 18)
    p.shape("polygon", [(0, 0), (17, 0), (15, 17), (2, 17)], fill=1)
    p.d.line((1, 2, 16, 2), fill=0)
    for x in (4, 7, 10, 13):
        p.d.line((x, 4, x + (1 if x > 8 else 0) - (1 if x < 8 else 0) * 0, 15), fill=0)
    p.d.rectangle((6, 7, 11, 11), fill=1)                   # 中间留一块写循环标
    p.px(7, 10, 0), p.px(8, 8, 0), p.px(9, 8, 0), p.px(10, 10, 0), p.px(8, 10, 0), p.px(9, 10, 0)
    p.dither([(13, 3), (16, 3), (15, 17), (12, 17)], 0.5, 0)
    return p.sprite()


@register
class MindFast(Rest):
    id = "x6.xinzhai"
    name = "心斋"
    desc = "墙上一排杂念文件（名、利、怒、忧……），小道士一个个摘下来扛到回收站扔掉；清空后盘坐，题“唯道集虚，虚者心斋”；新的杂念又“叮”地冒出来"
    T = {"enter": 2.5, "exit": 1.2}
    C = 72.0
    SLOT = 8.5
    S0 = 2.0
    ICON_X = (22, 36, 50, 64)
    ICON_Y = 21
    BIN = (102, FLOOR - 18)     # 桶身左上
    TOSS_X = 86
    HOME = 58

    def setup(self):
        self.clock = Clock()
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.s = self.rng.randrange(1000)

    def files(self, n: int):
        """第 n 轮的四个杂念：[(字的序号, 扩展名)]"""
        idx = list(range(12))
        out = []
        for i in range(4):
            j = int(rand(n * 7 + i, self.s) * len(idx))
            out.append((idx.pop(j), EXTS[int(rand(n * 11 + i, self.s + 1) * 5)]))
        return out

    # ------------------------------------------------------------ 状态

    def state(self, u: float):
        """返回 dict：x, pose, flip, face, carry(i 或 None), carry_xy, gone(已扔掉的集合), lid(0..1), inbin, label"""
        st = dict(x=self.HOME, pose="idle", flip=False, face="normal", carry=None, toss=None, lid=0.0, inbin=0,
                  label=None, sit=False, shake=0.0)
        gone = set()
        prev_x = self.HOME
        for k in range(4):
            s = self.S0 + k * self.SLOT
            ix = self.ICON_X[k] + 16
            if u < s:
                break
            v = u - s
            if v >= self.SLOT:
                gone.add(k)
                st["inbin"] = k + 1
                prev_x = self.TOSS_X
                continue
            if v < 2.0:      # 走到图标跟前（朝左）
                st.update(x=lerp(prev_x, ix, ease_in_out(v / 2.0)), pose="walk", flip=ix < prev_x)
            elif v < 2.9:    # 伸手摘下
                st.update(x=ix, pose="raise" if v < 2.5 else "offer", flip=True)
                if v >= 2.5:
                    st["carry"] = k
            elif v < 5.2:    # 举着走到回收站
                q = ease_in_out((v - 2.9) / 2.3)
                st.update(x=lerp(ix, self.TOSS_X, q), pose="carry", flip=False, carry=k)
            elif v < 6.0:    # 扔：弧线进桶
                st.update(x=self.TOSS_X, pose="offer" if v < 5.5 else "idle", flip=False)
                st["toss"] = (k, span(v, 5.2, 5.9))
            else:
                st.update(x=self.TOSS_X, pose="idle", flip=False)
                if v > 7.6:
                    st["face"] = "happy"
                gone.add(k)
                st["inbin"] = k + 1
            if 4.8 <= v < 6.0:
                st["lid"] = ease_out(span(v, 4.8, 5.2))
            elif 6.0 <= v < 6.6:
                st["lid"] = 1 - ease_out_bounce(span(v, 5.95, 6.5))
                st["shake"] = 1 - span(v, 6.0, 6.6)
            if st["carry"] is not None:
                st["label"] = k
            break
        end = self.S0 + 4 * self.SLOT  # 36
        if u >= end:
            gone = {0, 1, 2, 3}
            st["inbin"] = 4
            if u < end + 2.0:   # 走回中间
                st.update(x=lerp(self.TOSS_X, self.HOME, ease_in_out((u - end) / 2.0)), pose="walk", flip=True)
            elif u < 68.5:
                st.update(x=self.HOME, sit=True, face="sleep")
            else:
                st.update(x=self.HOME, pose="idle", face="normal")
            if 52 <= u < 56:  # 回收站自己抖一抖、开盖、冒尘烟：清空
                st["shake"] = 1.0 if u < 53.5 else 0.0
                st["lid"] = ease_out(span(u, 53.4, 53.8)) * (1 - ease_out_bounce(span(u, 55, 55.8)))
                if u >= 54:
                    st["inbin"] = 0
            elif u >= 56:
                st["inbin"] = 0
        st["gone"] = gone
        return st

    def respawn(self, u: float, k: int) -> float:
        """新杂念冒出来的进度（0..1）"""
        return ease_out_back(span(u, 59 + k * 2.4, 59.5 + k * 2.4))

    # ------------------------------------------------------------ 画

    def icon(self, g: Gfx, x: float, y: float, pic: int, s: float = 1.0, label: bool = True):
        if s <= 0.05:
            return
        if s < 0.99:
            spr_ = pix.stretch(spr("file", _file_icon), s, s)
            pix.blit(g, spr_, x + 5 - spr_.w / 2, y + 6 - spr_.h / 2)
            return
        pix.blit(g, spr("file", _file_icon), x, y)
        pix.blit(g, PICTO[pic], x + 2, y + 5, outline=False)
        if label:  # 图标下面的“文件名”（虚线示意）
            pix.dotted(g, x, y + 15, x + 10, y + 15, 2)

    def bin(self, g: Gfx, lid: float, inbin: int, shake: float, t: float):
        bx, by = self.BIN
        if shake > 0:
            bx += int(math.sin(t * 50) * 1.5 * shake)
        if inbin >= 3:  # 桶口冒出纸团
            g.d.ellipse((bx + 4, by - 3, bx + 8, by + 1), fill=1)
            g.px(bx + 6, by - 2, 0), g.px(bx + 5, by - 1, 0)
        if inbin >= 4:
            g.d.ellipse((bx + 10, by - 2, bx + 13, by + 1), fill=1)
        pix.blit(g, spr("bincan", _bin_can), bx, by)
        # 盖子：铰链在右边，lid=1 时竖起来
        a = lid * math.pi * 0.55
        hx, hy = bx + 18, by - 1
        L = 19
        ex, ey = hx - math.cos(a) * L, hy - math.sin(a) * L
        nx, ny = -math.sin(a), math.cos(a)
        g.d.polygon([(hx, hy), (ex, ey), (ex - nx * 2, ey - ny * 2), (hx - nx * 2, hy - ny * 2)], fill=1, outline=0)
        g.d.line((hx, hy, ex, ey), fill=1)
        g.d.line((hx - nx * 2, hy - ny * 2, ex - nx * 2, ey - ny * 2), fill=1)
        mx_, my_ = (hx + ex) / 2 - nx * 3, (hy + ey) / 2 - ny * 3   # 把手
        g.d.rectangle((mx_ - 1, my_ - 1, mx_ + 1, my_), fill=1)

    def carry_arm(self):
        """双手举过头顶托着东西"""
        def mk():
            p = Part(9, 15)
            p.shape("polygon", [(0, 14), (3, 14), (6, 3), (4, 2)], fill=1)
            p.shape("polygon", [(2, 13), (5, 7), (5, 12), (3, 14)], fill=1)
            p.d.line((5, 8, 5, 12), fill=0)
            p.shape("rectangle", (4, 0, 7, 2), fill=1)
            s = p.sprite()
            s.hand = (5, 0)
            s.over_head = True
            return s
        return spr("carry_arm", mk)

    def desktop(self, g: Gfx, t: float):
        """墙上一块大屏：双线边框、底下任务栏（开始钮、时钟点）"""
        x0, y0, x1, y1 = 16, 16, 82, 47
        g.d.rectangle((x0, y0, x1, y1), outline=1)
        g.d.rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), outline=1)
        g.d.line((x0 + 1, y1 - 4, x1 - 1, y1 - 4), fill=1)
        g.d.rectangle((x0 + 2, y1 - 3, x0 + 8, y1 - 1), fill=1)
        g.d.line((x0 + 3, y1 - 2, x0 + 4, y1 - 2), fill=0)
        for i in range(3):
            g.px(x1 - 3 - i * 2, y1 - 2)
        if (t % 1) < 0.5:
            g.px(x1 - 9, y1 - 2)
        g.d.line((x0 + 30, y1 + 3, x0 + 36, y1 + 3), fill=1)  # 挂架
        g.d.line((x0 + 31, y1 + 3, x0 + 31, FLOOR - 4), fill=1)
        g.d.line((x0 + 35, y1 + 3, x0 + 35, FLOOR - 4), fill=1)
        g.d.line((x0 + 30, FLOOR - 4, x0 + 36, FLOOR - 4), fill=1)

    def frame(self, g: Gfx, t: float, u: float, n: int, dt: float, scale_icons: float = 1.0):
        floor_line(g)
        self.desktop(g, t)
        st = self.state(u)
        fl = self.files(n)
        nxt = self.files(n + 1)
        # 墙上的图标（已摘下的空着；清空后新的一个个“叮”地冒出来）
        for k in range(4):
            x = self.ICON_X[k]
            if k not in st["gone"] and st["carry"] != k and not (st["toss"] and st["toss"][0] == k):
                self.icon(g, x, self.ICON_Y, fl[k][0], scale_icons)
            elif u >= 58:
                sc = self.respawn(u, k)
                self.icon(g, x, self.ICON_Y, nxt[k][0], sc)
                if crossed(u, dt, 59.25 + k * 2.4):
                    self.sparks.burst(x + 5, self.ICON_Y + 6, 8, 22, life=0.4, gravity=0)
        self.bin(g, st["lid"], st["inbin"], st["shake"], t)
        if 53.6 <= u < 55 and int(u * 6) != int((u - dt) * 6):  # 清空回收站：一缕尘烟
            bx, by = self.BIN
            self.puffs.emit(bx + 9, by - 2, vy=-10, life=1.4, rmax=2.4, spread=6)
        if crossed(u, dt, self.S0 + 3 * self.SLOT + 6.0) or any(crossed(u, dt, self.S0 + k * self.SLOT + 6.0)
                                                                 for k in range(3)):
            bx, by = self.BIN
            for s_ in (-1, 1):
                self.puffs.emit(bx + 9 + s_ * 9, by - 1, vx=s_ * 8, vy=-4, life=0.5, rmax=1.4, spread=1)
        # 小道士
        x = st["x"]
        if st["sit"]:
            cushion(g, x)
            sit(g, x, t, face="wow" if 59 <= u < 60.2 else st["face"])
        elif st["pose"] == "carry":
            h = figure(g, x, FLOOR, t, legs="walk", arm=self.carry_arm(), arm_at=(1, -31), flip=st["flip"])
            hx, hy = h["hand"]
            self.icon(g, hx - 5, hy - 13, fl[st["carry"]][0], label=False)
        else:
            h = daoshi(g, x, FLOOR, st["pose"], t, flip=st["flip"], face=st["face"])
            if st["carry"] is not None:
                hx, hy = h["hand"]
                self.icon(g, hx - 5 + (-3 if st["flip"] else 3), hy - 12, fl[st["carry"]][0], label=False)
        if st["toss"]:  # 弧线飞进桶
            k, q = st["toss"]
            bx, by = self.BIN
            x0, y0 = self.TOSS_X + 4, FLOOR - 30
            x1, y1 = bx + 4, by - 2
            px = lerp(x0, x1, q)
            py = lerp(y0, y1, ease_in(q)) - math.sin(q * math.pi) * 14
            spr_ = spr("file", _file_icon) if q < 0.7 else pix.stretch(spr("file", _file_icon), 0.7, 0.7)
            pix.blit(g, spr_, px, py)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        # 字（最后画）：拿在手上时文件名；清空后两句
        if st["label"] is not None:
            k = st["label"]
            g.text(50, 1, ZANIAN[fl[k][0]] + fl[k][1], align="center")
        end = self.S0 + 4 * self.SLOT
        if end + 3 <= u < end + 10:
            m = min(4, int((u - end - 3) * 3) + 1)
            g.text(26, 1, "唯道集虚"[:m])
        elif end + 10 <= u < end + 17:
            m = min(4, int((u - end - 10) * 3) + 1)
            g.text(26, 1, "虚者心斋"[:m])
        self.mx_bin(g, st["lid"], st["inbin"])
        if 53.6 <= u < 54.2:
            g.mx_level = 4

    def mx_bin(self, g: Gfx, lid: float, inbin: int):
        if lid > 0.3:
            mx_icon(g, ["      # ", "      # ", "      # "], 0, 0)
            g.mx[0, 5:7] = True
        else:
            g.mx[1, 1:7] = True
            g.mx[0, 3:5] = True
        for y in range(2, 8):
            w = 0 if y < 7 else 1
            g.mx[y, 1 + w] = g.mx[y, 6 - w] = True
        g.mx[7, 2:6] = True
        for i in range(inbin):
            r = 6 - i
            if r >= 3:
                g.mx[r, 2:6] = True

    def enter(self, g: Gfx, t: float):
        """回收站从上面掉下来弹两下，四个杂念文件依次弹上墙，小道士走进来"""
        dt = self.clock(t)
        floor_line(g)
        self.desktop(g, t)
        fl = self.files(0)
        for k in range(4):
            self.icon(g, self.ICON_X[k], self.ICON_Y, fl[k][0], ease_out_back(span(t, 0.7 + k * 0.25, 1.1 + k * 0.25)))
        bx, by = self.BIN
        dy = -(by + 24) * (1 - ease_out_bounce(span(t, 0, 0.9)))
        self.BIN = (bx, by + dy)
        self.bin(g, 0, 0, 0, t)
        self.BIN = (bx, by)
        x = lerp(-12, self.HOME, ease_out(span(t, 0.6, 2.3)))
        daoshi(g, x, FLOOR, "walk" if t < 2.3 else "idle", t)
        self.mx_bin(g, 0, 0)

    def hold(self, g: Gfx, t: float):
        dt = self.clock(t)
        n, u = cyc(t, self.C)
        self.frame(g, t, u, n, dt)

    def exit(self, g: Gfx, t: float):
        """杂念图标一个个缩没，回收站沉下去，淡出"""
        dt = self.clock(t)
        n, u = cyc(self.hold_t, self.C)
        self.frame(g, self.hold_t + t, u, n, dt, scale_icons=1 - span(t, 0, 0.6))
        g.fade(1 - span(t, 0.5, 1.2))


# ====================================================================== 坐忘

TAIJI_ICON = Sprite("""
.###.
##..#
##.##
#..##
.###.
""")

_SCR: dict = {}


def _body(t: float, x: int):
    """把盘坐闭目的小道士画到小画布上，返回 (亮点, 轮廓范围, 消散次序)（按呼吸两种样子缓存）"""
    breath = (t * 0.7) % 1 > 0.5
    key = (breath, x)
    v = _SCR.get(key)
    if v is None:
        g2 = Gfx()
        g2.clear()
        sit(g2, x, 0.6 if breath else 0.1, face="sleep")
        on = g2.array()
        foot = on.copy()
        foot[1:, :] |= on[:-1, :]
        foot[:-1, :] |= on[1:, :]
        foot[:, 1:] |= on[:, :-1]
        foot[:, :-1] |= on[:, 1:]
        ys = np.nonzero(foot.any(axis=1))[0]
        y0, y1 = ys.min(), ys.max()
        yy, xx = np.mgrid[0:64, 0:128]
        from ..engine.gfx import BAYER_F
        neck = FLOOR - 3 - 18           # 脖子以下是“肢体”，以上是“聪明”
        base = np.where(yy >= neck, (y1 - yy) / max(1, y1 - neck) * 0.62, 0.62 + (neck - yy) / max(1, neck - y0) * 0.38)
        order = np.clip(base + (BAYER_F - 0.5) * 0.14 + 0.02, 0, 1)
        v = _SCR[key] = (on, foot, order)
    return v


@register
class SitForget(Rest):
    id = "x6.zuowang"
    name = "坐忘"
    desc = "小道士在蒲团上打坐，旁边“卸载”进度条倒着走：仁义、礼乐两字从头顶飘散，身子一层层化成像素飞走，只剩蒲团——同于大通；再聚形，复归于朴"
    T = {"enter": 2.5, "exit": 1.2}
    C = 96.0
    X = 38
    STAGES = ((4, "忘仁义"), (20, "忘礼乐"), (36, "堕肢体"), (54, "黜聪明"), (64, "离形去知"), (70, ""), (84, "复归于朴"))

    def setup(self):
        self.clock = Clock()

    # ------------------------------------------------------------ 进度（u 的函数）

    @staticmethod
    def progress(u: float) -> float:
        for a, b, pa, pb in ((0, 4, 1, 1), (4, 20, 1, .8), (20, 36, .8, .6), (36, 54, .6, .35), (54, 64, .35, .15),
                             (64, 70, .15, 0), (70, 84, 0, 0), (84, 92, 0, 1), (92, 96, 1, 1)):
            if u < b:
                return lerp(pa, pb, span(u, a, b))
        return 1.0

    @staticmethod
    def gone(u: float) -> float:
        """身子消散到哪（0 完整 … 1 全没）"""
        if u < 36:
            return 0.0
        if u < 54:
            return span(u, 36, 54) * 0.62
        if u < 64:
            return 0.62 + span(u, 54, 64) * 0.4
        if u < 84:
            return 1.05
        return 1.05 * (1 - ease_in_out(span(u, 84, 90)))

    def label(self, u: float) -> str:
        s = "忘仁义"
        for a, name in self.STAGES:
            if u >= a:
                s = name
        if u >= 92:
            s = "忘仁义"
        return s

    # ------------------------------------------------------------ 画

    def body(self, g: Gfx, t: float, L: float):
        on, foot, order = _body(t, self.X)
        a = g.array()
        alive = order >= L
        a[foot & alive & ~on] = False
        a[on & alive] = True
        g.put(a)
        if 0 < L < 1.2:  # 刚散掉的像素往右上飘走
            ys, xs = np.nonzero(on & (order < L) & (order > L - 0.14))
            for y, x in zip(ys, xs):
                k = (L - order[y, x]) / 0.14
                if k > 0.6 and (x + y) % 2:
                    continue
                dx = k * (5 + (x * 7 + y * 3) % 6)
                dy = -k * (8 + (x * 5 + y) % 7)
                g.px(x + dx, y + dy)

    def dialog(self, g: Gfx, p: float, label: str, alpha: float = 1.0):
        if alpha <= 0:
            return
        x0, y0, x1, y1 = 70, 8, 124, 40
        window(g, x0, y0, x1, y1, icon=TAIJI_ICON)
        pbar(g, x0 + 4, y0 + 24, x1 - 4, y0 + 29, p)
        if alpha < 1:
            g.fade(alpha, (x0, y0, x1 + 4, y1 + 4))
        return x0 + 4, y0 + 11

    def rings(self, g: Gfx, u: float, k: float):
        """同于大通：心口一点，一圈圈点状涟漪向外荡开，十二道虚线通向八方；k 0..1 强度"""
        cx, cy = self.X, FLOOR - 16
        if k <= 0:
            return
        g.d.rectangle((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
        for j in range(4):
            r = ((u * 9 + j * 18) % 72) * k
            if r < 3:
                continue
            n = int(r * 1.2) + 8
            for i in range(n):
                a = i / n * 2 * math.pi + j
                g.px(cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8)
        for i in range(12):
            a = i * math.pi / 6 + 0.13
            ph = int(u * 10) % 4
            r1 = 6 + 70 * k
            pix.dotted(g, cx + math.cos(a) * 6, cy + math.sin(a) * 5, cx + math.cos(a) * r1, cy + math.sin(a) * r1 * 0.8,
                       4, ph)

    def frame(self, g: Gfx, t: float, u: float, dt: float, L: float | None = None, dlg: float | None = None):
        floor_line(g)
        p = self.progress(u)
        L = self.gone(u) if L is None else L
        dk = 0.0
        if 70 <= u < 86:
            dk = ease_out(span(u, 70, 72)) * (1 - ease_in(span(u, 83, 86)))
        self.rings(g, u, dk)
        cushion(g, self.X)
        self.body(g, t, L)
        a_dlg = (1 - span(u, 69, 70.5)) if u < 80 else span(u, 83, 84.5)
        if dlg is not None:
            a_dlg = dlg
        lab = self.dialog(g, p, self.label(u), a_dlg)
        # 字：飘起来的两字、对话框里的阶段名、竖写“同于大通”
        for a, chars in ((4, "仁义"), (20, "礼乐")):
            for i, ch in enumerate(chars):
                s = a + 2 + i * 6
                if s <= u < s + 5:
                    k = (u - s) / 5
                    x = self.X - 6 + (i * 2 - 1) * 6 + math.sin(k * 6) * 2
                    y = 12 - ease_out(k) * 12
                    g.text(x, y, ch)
                    if k > 0.5:
                        g.fade(1 - span(k, 0.5, 1.0), (x - 1, y - 1, x + 14, y + 13))
        if lab and a_dlg >= 1:
            g.text(lab[0], lab[1], self.label(u))
        if dk > 0.3 and u < 83.5:
            g.d.rectangle((108, 2, 124, 54), fill=0)
            n = min(4, int((u - 72) * 2.5) + 1) if u >= 72 else 0
            if n:
                g.vtext(110, 4, "同于大通"[:n])
        # 点阵：剩余进度（亮的行数）；同于大通时一圈圈扩散的环
        if dk > 0.3:
            r = (u * 3) % 5
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.6:
                        g.mx[yy, xx] = True
            g.mx[3:5, 3:5] = True
        else:
            rows = int(round(p * 8))
            g.mx[8 - rows:, 1:7] = True
            g.mx[:, 0] = g.mx[:, 7] = True

    def enter(self, g: Gfx, t: float):
        """蒲团先出现，小道士由散点聚成形；“坐忘”对话框弹出，进度 100%"""
        dt = self.clock(t)
        L = 1.05 * (1 - ease_in_out(span(t, 0.3, 1.9)))
        self.frame(g, t, 0.0, dt, L=L, dlg=span(t, 1.7, 2.3))

    def hold(self, g: Gfx, t: float):
        dt = self.clock(t)
        n, u = cyc(t, self.C)
        self.frame(g, t, u, dt)

    def exit(self, g: Gfx, t: float):
        """整屏抖一抖，淡出"""
        dt = self.clock(t)
        n, u = cyc(self.hold_t, self.C)
        self.frame(g, self.hold_t + t, u, dt)
        pix.shake(g, t, 1.2 * (1 - span(t, 0.6, 1.2)))
        g.fade(1 - span(t, 0.4, 1.2))


# ====================================================================== 归根

GX0, GY0 = 59, 10          # 磁盘格左上
GC, GR = 15, 6             # 15 列 × 6 行，每格 4 像素
NSLOT = GC * GR
NDATA = 54


def _monitor():
    """CRT 显示器 70×48：圆角机壳、凹进去的屏、下巴上的牌子与电源灯、底座"""
    p = Part(70, 49)
    p.shape("rounded_rectangle", (0, 0, 69, 42), radius=3, fill=1)
    p.d.rounded_rectangle((2, 2, 67, 36), radius=2, fill=0)
    p.d.rectangle((3, 3, 66, 35), outline=1)
    p.d.rectangle((4, 4, 65, 34), fill=0)
    p.d.line((6, 39, 14, 39), fill=0)                   # 牌子
    for x in range(48, 60, 3):                           # 按钮
        p.px(x, 39, 0)
    p.dither([(62, 2), (69, 2), (69, 42), (62, 42)], 0.5, 0)
    p.shape("polygon", [(26, 43), (43, 43), (46, 46), (23, 46)], fill=1)
    p.shape("rectangle", (18, 47, 51, 48), fill=1)
    return p.sprite()


def _tower():
    """立式机箱 14×30：光驱位、软驱口、电源键、硬盘灯位、底部通风栅"""
    p = Part(14, 31)
    p.shape("rectangle", (0, 0, 13, 30), fill=1)
    p.d.rectangle((2, 2, 11, 5), outline=0)              # 5.25 光驱
    p.d.line((4, 4, 9, 4), fill=0)
    p.d.rectangle((2, 8, 11, 10), outline=0)             # 3.5 软驱
    p.d.line((4, 9, 8, 9), fill=0)
    p.d.ellipse((5, 14, 8, 17), fill=0)                  # 电源键
    p.px(6, 15), p.px(7, 16)
    p.px(3, 20, 0)                                       # 硬盘灯（另画亮）
    for y in range(23, 29, 2):
        p.d.line((2, y, 11, y), fill=0)
    p.dither([(11, 0), (13, 0), (13, 30), (11, 30)], 0.5, 0)
    return p.sprite()


def _cup_arm():
    """端茶的手臂（袖子 + 手），手里的茶杯另画"""
    p = Part(12, 8)
    p.shape("polygon", [(0, 0), (4, 0), (9, 3), (9, 6), (2, 7), (0, 5)], fill=1)
    p.d.line((8, 3, 8, 6), fill=0)
    p.dither([(2, 5), (9, 5), (9, 7), (2, 7)], 0.5, 0)
    p.shape("rectangle", (9, 3, 11, 5), fill=1)
    s = p.sprite()
    s.hand = (10, 2)
    return s


def _sip_arm():
    """举杯到嘴边的手臂"""
    p = Part(11, 13)
    p.shape("polygon", [(0, 12), (3, 12), (8, 4), (6, 2)], fill=1)
    p.shape("polygon", [(2, 11), (6, 6), (6, 10), (3, 12)], fill=1)
    p.d.line((6, 6, 6, 10), fill=0)
    p.shape("rectangle", (6, 0, 8, 2), fill=1)
    s = p.sprite()
    s.hand = (8, 0)
    s.over_head = True
    return s


CUP = Sprite("""
#####
#...##
#...#.#
#...##
.###.
""")


@register
class Defrag(Rest):
    id = "x6.defrag"
    name = "归根"
    desc = "小道士端着茶坐在老电脑前看磁盘碎片整理：方块一齐散开（万物并作），读写头一格格扫过去把它们搬回原位（吾以观复），最后整整齐齐（归根曰静）"
    T = {"enter": 2.6, "exit": 1.2}
    C = 56.0
    X = 16
    MON = (54, 3)
    TOWER = (32, 28)
    D0, D1 = 6.0, 45.0        # 整理的起止

    def setup(self):
        self.clock = Clock()
        self.puffs = pix.Puffs(self.seed)
        self._plan: dict = {}

    # ------------------------------------------------------------ 计划（每轮一份，缓存）

    def plan(self, n: int):
        p = self._plan.get(n)
        if p is not None:
            return p
        import random
        r = random.Random(self.seed * 7919 + n)
        scatter = r.sample(range(NSLOT), NDATA)        # 块 j 散到哪
        occ = {s: j for j, s in enumerate(scatter)}
        steps = []                                      # (种类, 块, 从, 到)
        for i in range(NDATA):
            if i in occ:
                steps.append(("ok", occ[i], i, i))
            else:
                far = max(occ)
                j = occ.pop(far)
                occ[i] = j
                steps.append(("mv", j, far, i))
        raw = [0.5 if k == "ok" else 1.2 for k, *_ in steps]
        sc = (self.D1 - self.D0) / sum(raw)
        t0 = self.D0
        timed = []
        for (k, j, a, b), d in zip(steps, raw):
            timed.append((t0, d * sc, k, j, a, b))
            t0 += d * sc
        if len(self._plan) > 4:
            self._plan.clear()
        p = self._plan[n] = (scatter, timed)
        return p

    def blocks(self, u: float, n: int):
        """返回 [(x, y, 实心?)] 与 读写头格号、进度、是否在搬"""
        scatter, timed = self.plan(n)
        out = []
        head, prog, moving = None, 1.0, False
        if u < 3.5:
            return [(self.slot_xy(j) + (True,)) for j in range(NDATA)], None, 1.0, False
        if u < self.D0:  # 一齐飞散（空心块）
            for j in range(NDATA):
                k = ease_in_out(span(u, 3.5 + (j % 9) * 0.06, 4.6 + (j % 9) * 0.06))
                ax, ay = self.slot_xy(j)
                bx, by = self.slot_xy(scatter[j])
                out.append((lerp(ax, bx, k), lerp(ay, by, k) - math.sin(k * math.pi) * 3, k < 0.02))
            return out, None, 0.0, False
        pos = {j: scatter[j] for j in range(NDATA)}
        solid = set()
        fly = None
        done = 0
        for t0, d, kind, j, a, b in timed:
            if u >= t0 + d:
                pos[j] = b
                solid.add(j)
                done += 1
                continue
            if u >= t0:
                head = b
                if kind == "mv":
                    fly = (j, a, b, (u - t0) / d)
                    moving = True
            break
        for j in range(NDATA):
            if fly and fly[0] == j:
                _, a, b, k = fly
                ax, ay = self.slot_xy(a)
                bx, by = self.slot_xy(b)
                q = ease_in_out(k)
                out.append((lerp(ax, bx, q), lerp(ay, by, q) - math.sin(q * math.pi) * 6, False))
            else:
                x, y = self.slot_xy(pos[j])
                out.append((x, y, j in solid))
        prog = done / len(timed)
        if u >= self.D1:
            head, prog = None, 1.0
        return out, head, prog, moving

    @staticmethod
    def slot_xy(i: int):
        return GX0 + (i % GC) * 4, GY0 + (i // GC) * 4

    # ------------------------------------------------------------ 画

    def desk(self, g: Gfx):
        g.d.rectangle((50, 51, 127, 52), fill=1)
        g.d.line((51, 53, 126, 53), fill=1)
        for x in (54, 121):
            g.d.rectangle((x, 54, x + 2, FLOOR - 1), fill=1)

    def frame(self, g: Gfx, t: float, u: float, n: int, dt: float, wipe: float = 0.0):
        floor_line(g)
        self.desk(g)
        bl, head, prog, moving = self.blocks(u, n)
        tx, ty = self.TOWER
        jit = 1 if moving and int(t * 20) % 2 else 0
        pix.blit(g, spr("tower", _tower), tx + jit, ty)
        if (moving or (self.D0 <= u < self.D1)) and int(t * 13) % 3:
            g.px(tx + jit + 3, ty + 20, 1)                   # 硬盘灯狂闪
        mx_, my_ = self.MON
        pix.blit(g, spr("monitor", _monitor), mx_, my_)
        # 磁盘格：空格一个暗点，碎片空心，归位实心；读写头那格闪
        for i in range(NSLOT):
            x, y = self.slot_xy(i)
            g.px(x + 1, y + 1)
        for x, y, solid in bl:
            if solid:
                g.d.rectangle((x, y, x + 2, y + 2), fill=1)
            else:
                g.d.rectangle((x, y, x + 2, y + 2), outline=1)
                g.px(x + 1, y + 1, 0)
        if head is not None and int(t * 8) % 2 == 0:
            x, y = self.slot_xy(head)
            g.d.rectangle((x - 1, y - 1, x + 3, y + 3), outline=1)
        if u >= self.D1 + 1 and int(rand(int(t * 2), self.seed) * 6) == 0:  # 归根曰静：偶尔一块轻轻一闪
            j = int(rand(int(t * 2) + 7, self.seed) * NDATA)
            x, y = self.slot_xy(j)
            g.d.rectangle((x, y, x + 2, y + 2), fill=0)
            g.px(x + 1, y + 1)
        pbar(g, GX0, 35, GX0 + 59, 40, prog)
        if wipe > 0:
            g.d.rectangle((mx_ + 4, my_ + 4, mx_ + 4 + 61 * wipe, my_ + 34), fill=0)
        # 小道士端茶看着；散开时吓一跳，整理中隔一阵抿一口，整齐后闭目
        cushion(g, self.X)
        sip = (u % 14) > 11.5 and self.D0 < u < self.D1
        scared = 3.4 < u < 5.6
        face = "wow" if scared else ("sleep" if u >= self.D1 + 1 or sip else "normal")
        if sip:
            h = sit(g, self.X, t, face=face, arm=spr("sip_arm", _sip_arm), arm_at=(1, -14))
            hx, hy = h["hand"]
            pix.blit(g, CUP, hx - 3, hy - 2)
        else:
            h = sit(g, self.X, t, face=face, arm=spr("cup_arm", _cup_arm), arm_at=(-3, -16))
            hx, hy = h["hand"]
            cy = hy - 3 - (1 if scared and int(t * 16) % 2 else 0)
            pix.blit(g, CUP, hx - 1, cy)
            if not scared and int((t + dt) * 2) != int(t * 2):  # 茶的热气
                self.puffs.emit(hx + 1, cy - 1, vy=-5, life=1.4, rmax=0.9, spread=1)
        if crossed(u, dt, 3.6):
            self.puffs.emit(hx + 1, hy - 5, vx=-3, vy=-14, life=0.6, rmax=1.4, spread=2)
            self.puffs.emit(hx + 3, hy - 5, vx=5, vy=-12, life=0.6, rmax=1.2, spread=2)
        self.puffs.step(dt)
        self.puffs.draw(g)
        # 字
        for a, b, s in ((1.5, 5.8, "万物并作"), (7.0, 13.0, "吾以观复"), (46.0, 50.8, "归根曰静"), (51.0, 55.8, "是谓复命")):
            if a <= u < b:
                m = min(4, int((u - a) * 3) + 1)
                g.text(2, 2, s[:m])
        self.mx_disk(g, bl, head, t)

    def mx_disk(self, g: Gfx, bl, head, t):
        for x, y, solid in bl:
            c = int((x - GX0) / 4) // 2
            r = 1 + int((y - GY0) / 4 + 0.5)
            if 0 <= c < 8 and 0 <= r < 8:
                g.mx[r, c] = True
        if head is not None:
            c, r = (head % GC) // 2, 1 + head // GC
            g.mx[r, c] = int(t * 8) % 2 == 0

    def enter(self, g: Gfx, t: float):
        """开机：磁盘格一列列扫出来，数据块从上面落进左边排好"""
        dt = self.clock(t)
        floor_line(g)
        self.desk(g)
        tx, ty = self.TOWER
        pix.blit(g, spr("tower", _tower), tx, ty)
        if int(t * 13) % 3:
            g.px(tx + 3, ty + 20, 1)
        mx_, my_ = self.MON
        pix.blit(g, spr("monitor", _monitor), mx_, my_)
        cols = int(span(t, 0.3, 1.1) * GC)
        for i in range(NSLOT):
            if i % GC < cols:
                x, y = self.slot_xy(i)
                g.px(x + 1, y + 1)
        bl = []
        for j in range(NDATA):
            k = ease_out_bounce(span(t, 1.0 + j * 0.022, 1.5 + j * 0.022))
            if k > 0:
                x, y = self.slot_xy(j)
                yy = lerp(GY0 - 4, y, k)
                g.d.rectangle((x, yy, x + 2, yy + 2), fill=1)
                bl.append((x, yy, True))
        pbar(g, GX0, 35, GX0 + 59, 40, span(t, 1.0, 2.4))
        cushion(g, self.X)
        h = sit(g, self.X, t, face="normal", arm=spr("cup_arm", _cup_arm), arm_at=(-3, -16))
        hx, hy = h["hand"]
        pix.blit(g, CUP, hx - 1, hy - 3)
        self.mx_disk(g, bl, None, t)

    def hold(self, g: Gfx, t: float):
        dt = self.clock(t)
        n, u = cyc(t, self.C)
        self.frame(g, t, u, n, dt)

    def exit(self, g: Gfx, t: float):
        """屏上从左往右擦掉，淡出"""
        dt = self.clock(t)
        n, u = cyc(self.hold_t, self.C)
        self.frame(g, self.hold_t + t, u, n, dt, wipe=span(t, 0, 0.8))
        g.fade(1 - span(t, 0.7, 1.2))
