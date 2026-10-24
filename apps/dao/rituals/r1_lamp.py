"""长明灯：夜里的殿堂，莲花灯台上一只琉璃盏，浮芯上一朵火；小道士守灯、挑灯花、添油。

依据：宫观殿前供长明灯（五供“香、花、灯、水、果”之灯），昼夜不熄，执事随时添油、挑芯；
灯芯结出“灯花”爆开，旧俗以为吉兆。圆满句“薪尽火传”出自《庄子·养生主》“指穷于为薪，火传也，不知其尽也”。

入场：小道士举着点着的引火棒走进来，伸棒点着浮芯，火“噗”地窜起，屏幕一震、火星迸出，光晕一圈圈亮开；拱手一拜。
持续：灯油随计时变浅（一轮 10 分钟），火苗随油面下沉。火苗逐帧跳动，光晕呼吸旋转，偶尔爆一点灯花。
      每 36 秒：小道士拿灯挑挑芯，灯花“啪”地爆开；作揖；月洞窗外风起，梅枝乱摇、落叶卷进来，火苗被吹歪，
      小道士剑指一点，竹帘“唰”地落下挡风。另有飞蛾不时来绕灯。
      续：油尽火弱，小道士转身提起地上的油壶，走到灯前举壶添油，油面回升、火苗被托起，“第几盏”加一。
中断：灯挑把灯芯压低，火缩成一粒豆火，光晕收拢（长明灯不灭），牌子写“微明”。
恢复：剑指一点，一颗火星飞去，豆火“噗”地长回原样。
圆满：灯焰暴涨，放射光一圈圈转，小道士跪拜，闪白、火星四溅，“薪尽火传”弹出。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, pulse, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import (FLOOR, Clock, badge, floor, hit, hold_at, mx_burst, pose_arm, ring_dots, rot, star,
                        title)

LX = 84                 # 灯中心
RIM = 31                # 琉璃盏口沿 y
OIL_FULL, OIL_EMPTY = 34, 39
DX = 50                 # 小道士站位
JAR_X = 24              # 油缸放在身后地上
WIN = (110, 19, 10)     # 月洞窗 cx, cy, r
RENEW = 8.0

# ---------------------------------------------------------------- 精灵

FLAME = pix.frames("""
   #
   #
  ##
  ###
 ##.##
 #...#
 #...#
 ##.##
  ###
---
  #
  ##
  ##
  ###
 ##.##
 #...#
 #...#
 ##.##
  ###
---
    #
   ##
   ##
  ###
 ##.##
 #...#
 #...#
 ##.##
  ###
---
   #
  ##
  ###
 ##.##
 #...#
 #...#
 #...#
 ##.##
  ###
""")

LEAN = pix.frames("""
#
 ##
  ##
 ###.#
 #...#
 #...#
 ##.##
  ###
---
##
 ###
  ##.#
 ##..#
 #...#
 ##.##
  ###
""")

BEAN = pix.sprite("""
 #
###
#.#
###
""")

SMALL = pix.frames("""
 #
 #
##
#.#
###
---
 #
 ##
 ##
#.#
###
""")

MOTH = pix.frames("""
#. .#
##.##
 .#.
---
 ...
#####
#.#.#
""")

LEAF = pix.frames("""
##
 #
---
 #
##
---
#
##
""")


def _bowl():
    """琉璃盏 23×11：外翻口沿（联珠纹）、透明盏身（只画轮廓）、左侧高光"""
    p = Part(23, 11)
    p.shape("line", (0, 0, 22, 0), fill=1)
    p.shape("line", (1, 1, 21, 1), fill=1)
    p.d.line((3, 1, 19, 1), fill=0)
    for x in range(3, 20, 3):
        p.px(x, 1, 1)
    left = [(1, 2), (2, 5), (4, 8), (8, 10)]
    p.shape("line", left, fill=1)
    p.shape("line", [(22 - x, y) for x, y in left], fill=1)
    p.shape("line", (8, 10, 14, 10), fill=1)
    p.shape("line", (4, 3, 5, 6), fill=1)       # 琉璃高光
    p.px(18, 3), p.px(18, 4)
    return p.sprite()


def _stand():
    """莲花灯台 19×16：托盏的莲萼、两道竹节的灯柱、莲座、底足（右侧背光网点）"""
    p = Part(19, 16)
    p.shape("polygon", [(4, 0), (14, 0), (11, 3), (7, 3)], fill=1)
    p.px(6, 0, 0), p.px(9, 0, 0), p.px(12, 0, 0)
    p.px(8, 1, 0), p.px(10, 1, 0)
    p.shape("rectangle", (8, 3, 10, 11), fill=1)
    for y in (5, 8):                               # 竹节
        p.shape("rectangle", (7, y, 11, y), fill=1)
    p.px(10, 6, 0), p.px(10, 9, 0)
    p.shape("polygon", [(4, 11), (14, 11), (16, 13), (2, 13)], fill=1)
    for x in (4, 7, 10, 13):                       # 莲瓣
        p.px(x, 12, 0)
    p.shape("rectangle", (1, 14, 17, 15), fill=1)
    p.d.line((2, 14, 16, 14), fill=0)
    p.dither([(12, 11), (16, 11), (17, 15), (12, 15)], 0.5, 0)
    return p.sprite()


def _jar():
    """油缸 13×12：卷口、鼓腹、一道弦纹、右侧背光网点"""
    p = Part(13, 12)
    p.shape("ellipse", (0, 2, 12, 11), fill=1)
    p.shape("rectangle", (3, 0, 9, 2), fill=1)
    p.d.line((4, 1, 8, 1), fill=0)                  # 缸口
    p.d.line((1, 5, 11, 5), fill=0)                 # 弦纹
    p.px(3, 3, 0), p.px(3, 4, 0)
    p.dither([(8, 6), (12, 6), (12, 11), (8, 11)], 0.5, 0)
    p.shape("rectangle", (2, 11, 10, 11), fill=1)
    return p.sprite()


def ladle(g: Gfx, hx: float, hy: float, tip, tilt: float = 0.0, oil: bool = False):
    """竹油提：从手 (hx, hy) 到 tip 的长柄，柄头一只小提筒；tilt 度（顺时针倾倒）"""
    tx, ty = tip
    g.d.line((hx, hy, tx, ty), fill=1)
    cup = [(-2, -3), (2, -3), (2, 1), (1, 2), (-1, 2), (-2, 1)]
    pts = rot([(tx + x, ty + y) for x, y in cup], tilt, tx, ty)
    g.d.polygon(pts, fill=1)
    lip = rot([(tx - 1, ty - 2), (tx + 1, ty - 2)], tilt, tx, ty)
    g.d.line(lip, fill=0)
    if oil and tilt < 30:
        g.px(tx, ty - 2)
    g.d.rectangle((hx - 1, hy - 1, hx + 1, hy + 1), fill=1)
    return rot([(tx + 2, ty - 3)], tilt, tx, ty)[0]  # 倒油的口


_P: dict = {}


def P(name, *a):
    k = (name,) + a
    if k not in _P:
        _P[k] = {"bowl": _bowl, "stand": _stand, "jar": _jar}[name](*a)
    return _P[k]


# ---------------------------------------------------------------- 背景

def room(g: Gfx, t: float, blind: float = 0.0, gust: float = 0.0):
    """夜殿：梁、柱、踢脚线、月洞窗（窗外月牙和梅枝，起风时乱摇）、竹帘"""
    floor(g)
    g.d.line((0, FLOOR - 4, 127, FLOOR - 4), fill=1)
    g.d.line((0, 3, 127, 3), fill=1)
    pix.checker(g, (0, 0, 128, 3), 0.25)
    for x in (3, 124):
        g.d.rectangle((x - 1, 4, x + 1, FLOOR - 5), outline=1, fill=0)
    cx, cy, r = WIN
    g.d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), outline=1)
    g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
    # 月牙（左上）
    g.d.ellipse((cx - 7, cy - 8, cx - 1, cy - 2), fill=1)
    g.d.ellipse((cx - 5, cy - 9, cx + 1, cy - 3), fill=0)
    # 梅枝：从左下斜伸进窗，起风时摆
    sw = math.sin(t * (2 + 10 * gust)) * (0.5 + 2.5 * gust)
    br = [(cx - r + 1, cy + 7), (cx - 3, cy + 4 + sw * 0.4), (cx + 4, cy + 3 + sw), (cx + r - 1, cy - 1 + sw * 1.4)]
    g.d.line(br, fill=1)
    tw = (br[1][0] + 2, br[1][1] - 4 + sw * 0.5)
    g.d.line((br[1][0], br[1][1], *tw), fill=1)
    for bx, by in (tw, br[2], br[3], (cx - 6, cy + 6 + sw * 0.2)):
        bx, by = int(round(bx)), int(round(by))
        g.d.rectangle((bx - 1, by - 2, bx + 1, by - 1), fill=1)
        g.d.rectangle((bx - 2, by - 1, bx + 2, by), fill=1)
        g.px(bx, by - 1, 0)
    if blind > 0:  # 竹帘落下
        h = int((2 * r) * blind)
        g.d.rectangle((cx - r - 3, cy - r - 4, cx + r + 3, cy - r - 2), fill=1)
        for y in range(cy - r, cy - r + h, 2):
            hw = math.sqrt(max(r * r - (y - cy) ** 2, 0))
            g.d.line((cx - hw, y, cx + hw, y), fill=1)
        g.d.line((cx, cy - r - 2, cx, cy - r + h), fill=0)


def lamp(g: Gfx, oil_y: float, t: float, size: float = 1.0, lean: int = 0, glow: float = 1.0, pop: float = 0.0,
         lit: bool = True):
    """灯台 + 油 + 浮芯 + 火 + 光晕。size：火的大小（0 灭 / <0.45 豆火）；lean：-1 被风吹歪；pop：挑灯花的拉长"""
    pix.blit(g, P("stand"), LX - 9, FLOOR - 16)
    oy = int(round(oil_y))
    for y in range(oy + 1, RIM + 10):  # 灯油：网点
        k = (y - RIM) / 10
        hw = int(10 - k * k * 7)
        pix.checker(g, (LX - hw + 1, y, LX + hw, y + 1), 0.5)
    hw = int(10 - ((oy - RIM) / 10) ** 2 * 7)
    g.d.line((LX - hw + 1, oy, LX + hw - 1, oy), fill=1)
    gl = int(t * 5) % (2 * hw)                                   # 油面上游走的反光
    g.d.line((LX - hw + 1 + gl, oy, LX - hw + 2 + gl, oy), fill=0)
    g.d.rectangle((LX - 2, oy - 1, LX + 2, oy - 1), fill=1)       # 浮芯托
    g.px(LX, oy - 2)
    pix.blit(g, P("bowl"), LX - 11, RIM)
    fy = oy - 2
    if lit and size > 0:
        if glow > 0:
            r = (10 + 1.5 * pulse(t, 2.4)) * glow * min(size, 1.2)
            ring_dots(g, LX, fy - 4, r, 3, rot=t * 0.4)
            if glow > 0.5 and r > 6:
                ring_dots(g, LX, fy - 4, r + 3, 5, rot=-t * 0.3)
        if size < 0.45:
            pix.blit(g, BEAN, LX - 1, fy - 3)
        elif lean:
            pix.blit(g, pix.anim(LEAN, t, 10), LX - 3, fy - 8)
        elif size < 0.8:
            pix.blit(g, pix.anim(SMALL, t, 7), LX - 1, fy - 5)
        else:
            spr = pix.anim(FLAME, t + rand(int(t * 3)) * 0.2, 8)
            sy = size * (1 + pop)
            if abs(sy - 1) > 0.05:
                spr = pix.stretch(spr, 1.0, sy)
            pix.blit(g, spr, LX - 3, fy - spr.h + 1)
    return (LX, fy)


def moth(g: Gfx, e: float, fx: float, fy: float, seed: int):
    """飞蛾：每 47 秒来绕灯飞两圈"""
    k = (e + seed % 13) % 47
    if k > 7:
        return
    a = k * 2.2
    r = 13 + 2 * math.sin(k * 3)
    x, y = fx + math.cos(a) * r, fy - 4 + math.sin(a) * r * 0.6
    if k < 1.5:
        q = 1 - k / 1.5
        x, y = lerp(x, 128, q), lerp(y, 8, q)
    if k > 5.5:
        q = (k - 5.5) / 1.5
        x, y = lerp(x, 40, q), lerp(y, -6, q)
    pix.blit(g, pix.anim(MOTH, e, 12), x - 2, y - 1)


def mx_lamp(g: Gfx, oil: float, size: float, t: float, lean: int = 0):
    """点阵：灯盏 + 跳动的火；油多时盏里亮满"""
    g.mx[4, 1:7] = True
    g.mx[5, 2] = g.mx[5, 5] = True
    if oil > 0.4:
        g.mx[5, 3:5] = True
    g.mx[6, 3:5] = True
    g.mx[7, 2:6] = True
    if size <= 0:
        return
    if size < 0.45:
        g.mx[3, 3] = True
        return
    f = int(t * 8) % 3
    g.mx[3, 3:5] = True
    g.mx[2, 3 - lean:5 - lean] = True
    g.mx[1, [3, 3, 4][f] - lean] = True
    if size > 1.1 or f == 0:
        g.mx[0, [3, 4, 4][f] - lean] = True


# ---------------------------------------------------------------- 场景

@register
class EternalLamp(Ritual):
    id = "r1.lamp"
    name = "长明灯"
    desc = "夜殿里小道士守着琉璃长明灯：挑灯花、剑指落帘挡风；油随计时变浅，油尽提壶添油"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 2.0, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.leaves = []

    def oil(self, e: float) -> float:
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return lerp(OIL_EMPTY, OIL_FULL, ease_in_out(span(k, 3.4, 4.6)))
        return lerp(OIL_FULL, OIL_EMPTY, k / self.CYCLE)

    def size(self, e: float) -> float:
        p = (e % self.CYCLE) / self.CYCLE
        if e >= self.CYCLE and e % self.CYCLE < RENEW:
            return lerp(0.6, 1.0, span(e % self.CYCLE, 3.4, 4.8))
        return 1.0 - 0.4 * span(p, 0.92, 1.0)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        badge(g, 7, 6, label or (f"第{cn_num(n)}盏" if n < 100 else f"{n}盏"))

    def pot_home(self, g: Gfx, ladle_in: bool = True):
        """身后地上的油缸，竹油提插在缸里"""
        if ladle_in:
            g.d.line((JAR_X + 7, FLOOR - 13, JAR_X + 11, FLOOR - 27), fill=1)
            g.d.rectangle((JAR_X + 10, FLOOR - 28, JAR_X + 12, FLOOR - 27), fill=1)
        pix.blit(g, P("jar"), JAR_X, FLOOR - 12)

    def fx(self, g: Gfx, dt: float):
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def crackle(self, e: float, dt: float, fx: float, fy: float):
        """火苗偶尔爆一点灯花"""
        i = int(e / 3.3)
        if hit(e, i * 3.3, dt) and rand(i, self.seed) < 0.5:
            self.sparks.burst(fx, fy - 6, 2, 12, up=10, life=0.5, gravity=40)

    # ------------------------------------------------------------ 入场：举棒点灯

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        room(g, t)
        self.pot_home(g)
        x = lerp(-12, DX, ease_out(span(t, 0, 2.0)))
        lit = t >= 3.0
        size = ease_out_back(span(t, 3.0, 3.6)) if lit else 0
        fx, fy = lamp(g, OIL_FULL, t, size=max(size, 0.01) if lit else 0, glow=span(t, 3.0, 4.2), lit=lit)
        if t < 2.0:
            h = pose_arm(g, x, FLOOR, t, 30, legs="walk")
            tip = (h["hand"][0] + 6, h["hand"][1] + 6)
        elif t < 4.3:
            h = pose_arm(g, x, FLOOR, t, -30, face="wow" if 3.0 < t < 3.6 else "normal")
            q = ease_in_out(span(t, 2.0, 2.9)) - ease_in_out(span(t, 3.4, 4.2)) * 0.6
            tip = (lerp(h["hand"][0] + 7, fx - 1, q), lerp(h["hand"][1] - 4, fy, q))
        else:
            pose = "gongshou" if t < 5.1 else ("bow" if t < 5.8 else "idle")
            daoshi(g, x, FLOOR, pose, t)
            h = tip = None
        if h:  # 引火棒：细棒 + 棒头一点火
            g.d.line((h["hand"][0], h["hand"][1], tip[0], tip[1]), fill=1)
            g.d.rectangle((h["hand"][0] - 1, h["hand"][1] - 1, h["hand"][0] + 1, h["hand"][1] + 1), fill=1)
            if t < 3.5:
                pix.blit(g, pix.anim(SMALL, t, 8), tip[0] - 1, tip[1] - 5)
            elif t < 3.6:
                self.puffs.emit(tip[0], tip[1] - 2, vy=-5, life=0.7, rmax=1.6, spread=0)
        if hit(t, 3.0, dt):
            self.sparks.burst(fx, fy - 4, 16, 34, up=16, life=0.8, gravity=60)
        if 3.0 <= t < 3.3:
            pix.shake(g, t, 1.0)
        if 3.0 <= t < 4.4:  # 光晕一圈圈亮开
            ring_dots(g, fx, fy - 4, (t - 3.0) * 22, 3)
        self.crackle(t, dt, fx, fy)
        self.fx(g, dt)
        if lit:
            self.counter(g, 0.0)
        mx_lamp(g, 1.0, size if lit else 0, t)
        if hit(t, 3.0, dt) or 3.0 <= t < 3.15:
            g.mx_level = 6

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e, dt)
            return
        oil = self.oil(e)
        size = self.size(e)
        c = (e + 10) % 36            # 每 36 秒一套小事件
        gust = span(c, 25.2, 25.8) * (1 - span(c, 27.6, 28.4))
        blind = ease_out(span(c, 27.6, 28.0)) * (1 - span(c, 33.0, 35.0))
        room(g, t, blind=blind, gust=gust)
        self.pot_home(g)
        pop = 0.35 * (1 - span(c, 8.0, 8.4)) if 8.0 <= c < 8.4 else 0.0
        lean = 1 if gust > 0.3 else 0
        fx, fy = lamp(g, oil, t, size=size * (0.85 if lean else 1), lean=lean, glow=1 - 0.5 * gust, pop=pop)
        # 小道士
        if 6.0 <= c < 9.6:      # 挑灯花
            q = ease_in_out(span(c, 6.2, 7.6)) * (1 - ease_in_out(span(c, 8.8, 9.6)))
            face = "happy" if 8.1 < c < 9.4 else "normal"
            h = pose_arm(g, DX, FLOOR, t, -30 if q > 0.15 else 0, face=face)
            hx, hy = h["hand"]
            tx, ty = lerp(hx + 8, fx - 1, q), lerp(hy, fy + 1, q)
            g.d.line((hx, hy, tx, ty), fill=1)
            g.px(tx + 1, ty - 1)
            if hit(c, 8.0, dt):
                self.sparks.burst(fx, fy - 7, 12, 28, up=14, life=0.6, gravity=50)
        elif 15.0 <= c < 17.4:
            daoshi(g, DX, FLOOR, "gongshou" if c < 16.2 else "bow", t)
        elif 25.0 <= c < 29.6:  # 起风：剑指落帘
            if 26.8 <= c < 28.2:
                h = daoshi(g, DX, FLOOR, "point", t, face="wow" if c < 27.4 else "normal")
                q = span(c, 27.0, 27.6)
                if 0 < q < 1:
                    hx, hy = h["hand"]
                    cx, cy, r = WIN
                    px, py = lerp(hx, cx, q), lerp(hy, cy - r, q) - math.sin(q * math.pi) * 8
                    g.d.ellipse((px - 1, py - 1, px + 1, py + 1), fill=1)
                    self.sparks.burst(px, py, 1, 5, life=0.3, gravity=0)
            else:
                daoshi(g, DX, FLOOR, "idle", t, face="wow" if c < 26.8 else "happy")
        else:
            daoshi(g, DX, FLOOR, "idle", t)
        if gust > 0:            # 风纹 + 卷进来的叶子
            cx, cy, r = WIN
            for j in range(4):
                ph = (t * 1.6 + j * 0.27) % 1
                x = cx - 8 - ph * 60
                y = cy + 4 + j * 5 + math.sin(ph * 6 + j) * 2
                pix.dotted(g, x, y, x + 9, y, 2, j)
            for j in range(3):
                ph = (t * 0.9 + j * 0.33) % 1
                pix.blit(g, pix.anim(LEAF, t + j, 8), cx - 6 - ph * 70, cy + 2 + j * 6 + math.sin(ph * 9) * 4)
        if hit(c, 25.2, dt):
            pix.shake(g, t, 1.0)
        if hit(c, 27.6, dt):
            cx, cy, r = WIN
            self.puffs.emit(cx - r, cy + r, vx=-4, vy=-3, life=0.6, rmax=1.5)
            self.puffs.emit(cx + r, cy + r, vx=4, vy=-3, life=0.6, rmax=1.5)
        if 27.6 <= c < 27.8:
            pix.shake(g, t, 1.0)
        moth(g, e, fx, fy, self.seed)
        self.crackle(e, dt, fx, fy)
        self.fx(g, dt)
        self.counter(g, e)
        mx_lamp(g, (OIL_EMPTY - oil) / (OIL_EMPTY - OIL_FULL), size, t, lean)
        if 8.0 <= c < 8.2:
            g.mx_level = 5

    def _renew(self, g: Gfx, t: float, k: float, e: float, dt: float):
        """添油：转身从油缸里舀油 → 走到灯前 → 举油提倒油 → 走回 → 插回缸里"""
        room(g, t)
        oil = self.oil(e)
        size = self.size(e) if k > 3.2 else 0.6
        fx, fy = lamp(g, oil, t, size=size, glow=0.6 + 0.4 * span(k, 3.2, 4.8))
        mouth = (JAR_X + 6, FLOOR - 12)
        home = k < 0.8 or k >= 7.2
        self.pot_home(g, ladle_in=home)
        if k < 0.8:
            daoshi(g, DX, FLOOR, "idle", t, face="wow", flip=k > 0.4)
        elif k < 1.8:      # 转身舀油
            h = pose_arm(g, DX, FLOOR, t, 30 if k < 1.4 else 0, flip=True)
            up = ease_out(span(k, 1.3, 1.8)) * 8
            ladle(g, *h["hand"], (mouth[0], mouth[1] + 2 - up), oil=True)
            if 1.3 < k < 1.8 and int(t * 10) % 3 == 0:
                g.px(mouth[0] + 2, mouth[1] - up + 4)
        elif k < 5.0:
            x = lerp(DX, 60, ease_in_out(span(k, 1.8, 2.8)))
            if k < 2.8:
                h = pose_arm(g, x, FLOOR, t, 0, legs="walk")
                hx, hy = h["hand"]
                ladle(g, hx, hy, (hx + 6, hy - 12), oil=True)
            else:
                h = pose_arm(g, x, FLOOR, t, -30, face="happy" if k > 4.4 else "normal")
                hx, hy = h["hand"]
                reach = ease_in_out(span(k, 2.8, 3.2)) * (1 - ease_in_out(span(k, 4.7, 5.0)))
                tip = (lerp(hx + 6, LX - 4, reach), lerp(hy - 12, RIM - 5, reach))
                tilt = 110 * ease_in_out(span(k, 3.2, 3.5)) * (1 - span(k, 4.5, 4.8))
                lip = ladle(g, hx, hy, tip, tilt=tilt, oil=k < 3.2)
                if 3.4 <= k < 4.6:  # 油线
                    g.d.line((lip[0], lip[1] + 1, lip[0], oil - 1), fill=1)
                    if int(t * 10) % 2 == 0:
                        g.px(lip[0] + 1, oil - 1)
                        g.px(lip[0] - 1, oil - 1)
        elif k < 6.2:
            x = lerp(60, DX, ease_in_out(span(k, 5.0, 6.0)))
            h = pose_arm(g, x, FLOOR, t, 0, legs="walk", flip=True)
            hx, hy = h["hand"]
            ladle(g, hx, hy, (hx - 6, hy - 12))
        elif k < 7.2:      # 插回缸里
            h = pose_arm(g, DX, FLOOR, t, 0 if k < 6.6 else 30, flip=True)
            down = ease_in_out(span(k, 6.4, 7.0))
            ladle(g, *h["hand"], (mouth[0], lerp(mouth[1] - 8, mouth[1] + 2, down)))
        else:
            daoshi(g, DX, FLOOR, "idle", t, face="happy")
        if hit(k, 4.8, dt):
            self.sparks.burst(fx, fy - 6, 14, 26, up=14, life=0.7, gravity=50)
        self.crackle(e, dt, fx, fy)
        self.fx(g, dt)
        self.counter(g, e if k >= 4.8 else e - k - 1)
        mx_lamp(g, span(k, 3.4, 4.6), size, t)

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        room(g, t)
        self.pot_home(g)
        oil = self.oil(e)
        s0 = self.size(e)
        q = ease_in_out(span(t, 0.2, 0.8))
        size = lerp(s0, 0.3, span(t, 0.8, 1.3))
        fx, fy = lamp(g, oil, t, size=size, glow=lerp(1, 0.35, span(t, 0.8, 1.4)))
        h = pose_arm(g, DX, FLOOR, t, -30 if q > 0.15 else 0)
        hx, hy = h["hand"]
        back = span(t, 1.3, 1.8)
        tx, ty = lerp(hx + 8, fx - 1, q * (1 - back)), lerp(hy, fy - 1, q * (1 - back))
        g.d.line((hx, hy, tx, ty), fill=1)
        if hit(t, 1.0, dt):
            self.puffs.emit(fx, fy - 4, vy=-5, life=0.8, rmax=2, spread=0)
        self.fx(g, dt)
        self.counter(g, e, "微明" if t > 1.0 else None)
        mx_lamp(g, 0.5, size, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        room(g, t)
        self.pot_home(g)
        oil = self.oil(e)
        s0 = self.size(e)
        grow = ease_out_back(span(t, 0.9, 1.4))
        size = 0.3 if t < 0.9 else lerp(0.8, s0, grow)
        fx, fy = lamp(g, oil, t, size=size, glow=lerp(0.35, 1, span(t, 0.9, 1.6)))
        h = daoshi(g, DX, FLOOR, "point" if t < 1.5 else "idle", t)
        q = span(t, 0.3, 0.9)
        if 0 < q < 1:
            hx, hy = h["hand"]
            px, py = lerp(hx, fx, q), lerp(hy, fy - 2, q) - math.sin(q * math.pi) * 10
            g.d.ellipse((px - 1, py - 1, px + 1, py + 1), fill=1)
            self.sparks.burst(px, py, 1, 6, life=0.3, gravity=0)
        if hit(t, 0.9, dt):
            self.sparks.burst(fx, fy - 5, 14, 30, up=12, life=0.6, gravity=50)
            pix.flash(g)
        if 0.9 <= t < 1.3:
            ring_dots(g, fx, fy - 4, (t - 0.9) * 30, 3)
        self.fx(g, dt)
        self.counter(g, e, "微明" if t < 0.9 else None)
        mx_lamp(g, 0.5, size, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        room(g, t)
        self.pot_home(g)
        grow = 1 + 0.9 * ease_out(span(t, 0.2, 1.5))
        fx, fy = lamp(g, OIL_FULL + 1, t, size=grow, glow=1.3)
        pose = "gongshou" if t < 1.4 else ("kneel" if t < 4.2 else "idle")
        daoshi(g, DX, FLOOR, pose, t, face="happy" if t > 4.2 else "normal")
        if t > 1.6:  # 放射光（点线，转动）
            for j in range(12):
                a = j / 12 * 2 * math.pi + t * 0.5
                r0, r1 = 14, 17 + 3 * pulse(t + j * 0.2, 0.8)
                pix.dotted(g, fx + math.cos(a) * r0, fy - 6 + math.sin(a) * r0 * 0.8,
                           fx + math.cos(a) * r1, fy - 6 + math.sin(a) * r1 * 0.8, 2, int(t * 8))
        if hit(t, 1.6, dt):
            pix.flash(g)
            self.sparks.burst(fx, fy - 8, 30, 46, up=20, life=1.3, gravity=40)
        if 1.6 < t < 1.9:
            pix.shake(g, t, 1.5)
        self.fx(g, dt)
        if t > 2.0:
            title(g, 42, 8, "薪尽火传", t, 2.0)
        mx_lamp(g, 1.0, 1.3, t)
        mx_burst(g, t, 1.6)
