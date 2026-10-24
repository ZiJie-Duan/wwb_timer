"""礼斗：小道士在斗坛前点七星灯、朝拜北斗。

依据：礼斗科（如《清微礼斗科》）向斗姆与南北斗星君祈福消灾，诵《太上玄灵北斗本命延生真经》；
北斗七星天枢、天璇、天玑、天权、玉衡、开阳、摇光，对应贪狼、巨门、禄存、文曲、廉贞、武曲、破军七星君。

画面：夜里的斗坛。右边长供桌铺星纹桌围，桌上一排七盏莲花灯；天上北斗七星（斗魁在右）。
入场：小道士举着引火烛走进来，向天一揖，走到第一盏灯前点亮——灯焰“噗”地蹿起，天枢星随之亮起。
持续：每 84 秒小道士走去点下一盏灯，天上对应的星亮起、一道星线从上一颗星连过来；回到原位作揖、跪拜；
      流星偶尔划过，灯焰跳动、飘起火星。七灯俱明后，星线上有流光。
      续：七朵灯焰化作光球升上天，北斗一闪，灯盏复暗，小道士再点第一盏，“第几遍”。
中断：小道士抬手，灯从最后一盏起依次熄灭（一小团烟），星光暗下，“暂熄”。
恢复：剑指一点，火星依次飞进灯里，灯重新燃起。
圆满：余下的灯一齐燃起，七焰升天，北斗大放光明、连成斗形，小道士跪拜，“消灾解厄”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r5_util import STAR_S, Clock, arm, cached, label, meteor, mx_ring, pop_box, ring, sky, sparkle, star

FLOOR = 60
TOP = 46                       # 桌面
TX0, TX1 = 44, 127             # 供桌左右
LX = [51 + i * 12 for i in range(7)]   # 七盏灯中心
HOME = 22
STARS = [(121, 4), (124, 17), (104, 20), (96, 12), (80, 14), (68, 16), (55, 25)]
NAME = ["天枢", "天璇", "天玑", "天权", "玉衡", "开阳", "摇光"]
JUN = ["贪狼", "巨门", "禄存", "文曲", "廉贞", "武曲", "破军"]
MX_POS = [(7, 0), (7, 3), (5, 4), (4, 2), (2, 2), (1, 3), (0, 6)]
SEG = 84.0
RENEW = 3.0
SPEED = 24.0


# ---------------------------------------------------------------- 道具

def _lamp():
    """莲花灯 9×10：莲瓣灯盏、束腰灯柱、圆座"""
    p = Part(9, 10)
    for x in (0, 2, 6, 8):                     # 莲瓣尖
        p.px(x, 1)
    p.px(1, 0), p.px(7, 0)
    p.shape("polygon", [(0, 2), (8, 2), (7, 4), (6, 5), (2, 5), (1, 4)], fill=1)
    p.px(2, 3, 0), p.px(6, 3, 0), p.px(4, 4, 0)   # 瓣缝
    p.shape("rectangle", (4, 6, 4, 7), fill=1)
    p.shape("rectangle", (3, 7, 5, 7), fill=1)
    p.shape("polygon", [(1, 9), (7, 9), (6, 8), (2, 8)], fill=1)
    p.px(5, 9, 0)
    return p.sprite()


FLAME = pix.frames("""
 #
 #
###
#.#
 #
---
  #
 #
###
#.#
 #
---
 #
 ##
###
#.#
 #
---
#
 #
###
#.#
 #
""")
FLAME_BIG = pix.frames("""
  #
  #
 ###
 ###
##.##
 #.#
  #
---
   #
  #
 ###
 ###
##.##
 #.#
  #
""")


def _taper():
    """引火烛：细长白烛，烛身一道暗线"""
    p = Part(2, 11)
    p.shape("rectangle", (0, 0, 1, 10), fill=1)
    p.d.line((1, 2, 1, 9), fill=0)
    return p.sprite()


def lamp_spr():
    return cached(("r5lidou", "lamp"), _lamp)


def stage(g: Gfx, t: float, seed: int, sky_level: float = 1.0):
    """夜空、地砖、斗坛（桌围上绣七星，下缘流苏）"""
    sky(g, seed, t, (0, 0, 128, 40), 34, sky_level)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for i, x in enumerate(range(-8, 136, 14)):           # 地砖
        g.d.line((x, FLOOR + 1, x, 63), fill=1)
    pix.checker(g, (0, FLOOR + 2, 128, 64), 0.125)
    # 供桌：桌面、桌围（上缘一道网点镶边，中间绣北斗，下缘流苏）
    g.d.rectangle((TX0, TOP, TX1, TOP + 2), fill=1)
    g.d.line((TX0 + 1, TOP + 1, TX1 - 1, TOP + 1), fill=0)
    g.d.rectangle((TX0 + 2, TOP + 3, TX1 - 2, FLOOR - 1), fill=0, outline=1)
    pix.checker(g, (TX0 + 3, TOP + 4, TX1 - 2, TOP + 6), 0.5)
    g.d.line((TX0 + 2, TOP + 6, TX1 - 2, TOP + 6), fill=1)
    for i, x in enumerate(range(TX0 + 4, TX1 - 2, 2)):    # 流苏
        if i % 2 == 0:
            g.d.line((x, FLOOR - 3, x, FLOOR - 2), fill=1)
    pts = [(int(70 + (sx - 55) * 0.55), int(TOP + 8 + (sy - 4) * 0.12)) for sx, sy in STARS]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        g.d.line((x0, y0, x1, y1), fill=1)
    g.d.line((*pts[3], *pts[0]), fill=1)
    for x, y in pts:
        g.d.rectangle((x - 1, y, x + 1, y), fill=1)
        g.d.rectangle((x, y - 1, x, y + 1), fill=1)
    for i, x in enumerate(LX):
        pix.blit(g, lamp_spr(), x - 4, TOP - 10)


def flame(g: Gfx, x: int, k: float, t: float, i: int, big: bool = False):
    """灯焰：k = 亮度（0 灭，0..1 刚点着拉伸弹起，1 正常）"""
    if k <= 0:
        g.px(x, TOP - 10)
        return
    fr = pix.anim(FLAME_BIG, t * 1.3 + i * 0.23, 6)
    s = pix.stretch(fr, 1.0, 0.4 + 0.6 * ease_out_back(min(k, 1)))
    pix.blit(g, s, x - s.w // 2, TOP - 9 - s.h, outline=False)
    if k >= 1 and (t * 0.9 + i * 0.37) % 1 < 0.5:   # 灯晕：两侧微光点
        y = TOP - 13
        g.px(x - 4, y), g.px(x + 4, y), g.px(x, y - 7)


@register
class LiDou(Clock, Ritual):
    id = "r5.lidou"
    name = "礼斗"
    desc = "斗坛前小道士举烛点七星灯，每点一盏，天上北斗便亮一颗、连一段星线；七灯俱明后灯焰升天"
    T = {"enter": 7.0, "interrupt": 1.8, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sk = self.rng.randrange(1000)
        self.sparks = pix.Sparks(self.seed + 3)
        self.puffs = pix.Puffs(self.seed + 4)
        self.embers = pix.Sparks(self.seed + 5)

    # ------------------------------------------------------------ 时间线

    def ev_start(self, c: int, k: int) -> float:
        """第 c 轮点第 k 盏灯的开始时间（轮内秒数）"""
        return (RENEW if (c >= 1 and k == 0) else 0.0) + k * SEG

    def walk_time(self, k: int) -> float:
        return (LX[k] - 10 - HOME) / SPEED

    def lit_at(self, c: int, k: int) -> float:
        """第 k 盏灯点亮的时刻（轮内）"""
        if c == 0 and k == 0:
            return -1.0
        return self.ev_start(c, k) + self.walk_time(k) + 0.6

    def lamps(self, e: float):
        """→ (各灯亮度 0..1+, 已亮的盏数, 本轮序号, 轮内秒数)"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        out = []
        for i in range(7):
            if c >= 1 and k < RENEW:          # 续：上一轮七灯全亮，正在升空
                out.append(1.0 if k < 0.6 else 0.0)
                continue
            a = self.lit_at(c, i)
            out.append(0.0 if k < a else min((k - a) / 0.35, 1.0) + 0.001)
        n = sum(1 for v in out if v > 0)
        return out, n, c, k

    def actor(self, g: Gfx, e: float, t: float):
        """小道士：按 e 找到正在进行的点灯事件，否则在原位行礼"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        for i in range(7):
            if c == 0 and i == 0:
                continue
            s = self.ev_start(c, i)
            tau = k - s
            tw = self.walk_time(i)
            if 0 <= tau < 2 * tw + 2.0:
                return self.light_event(g, i, tau, t)
        return self.routine(g, t, e)

    def light_event(self, g: Gfx, i: int, tau: float, t: float):
        tw = self.walk_time(i)
        stand = LX[i] - 10
        if tau < tw:
            x = HOME + SPEED * tau
            h = figure(g, x, FLOOR, t, legs="walk", arm=arm("hold"), arm_at=(-3, -16))
            self.taper(g, h["hand"], t, 0.0)
        elif tau < tw + 1.4:
            q = tau - tw
            reach = ease_out(span(q, 0.0, 0.45)) - ease_in_out(span(q, 1.0, 1.4))
            h = figure(g, stand, FLOOR, t, arm=arm("hold"), arm_at=(-3, -16 - round(reach * 2)))
            self.taper(g, h["hand"], t, reach)
            if abs(q - 0.6) < 1 / 30 + 1e-6 or (0.6 <= q < 0.6 + 1 / 30):
                self.sparks.burst(LX[i], TOP - 13, 10, 22, up=14, life=0.6, gravity=50)
        elif tau < 2 * tw + 1.4:
            x = stand - SPEED * (tau - tw - 1.4)
            h = figure(g, x, FLOOR, t, legs="walk", arm=arm("hold"), arm_at=(-3, -16), flip=True)
            self.taper(g, h["hand"], t, 0.0, flip=True)
        else:
            daoshi(g, HOME, FLOOR, "gongshou", t)

    def taper(self, g: Gfx, hand, t: float, reach: float, flip: bool = False):
        hx, hy = hand
        spr = cached(("r5lidou", "taper"), _taper)
        lean = int(round(reach * 3)) * (-1 if flip else 1)
        x = hx - 1 + lean
        y = hy - 9 - int(round(reach * 2))
        pix.blit(g, spr, x, y)
        if lean:
            pass
        fr = pix.anim(FLAME, t, 9)
        pix.blit(g, fr, x - 1 + (1 if not flip else 0), y - 5, outline=False)

    def routine(self, g: Gfx, t: float, e: float):
        """原位：站立 → 拱手 → 跪拜（叩首两次）→ 拱手 → 站立，20 秒一回"""
        ph = (e + 7) % 20
        if 9 < ph < 10.5 or 15 < ph < 16:
            return daoshi(g, HOME, FLOOR, "gongshou", t)
        if 10.5 <= ph <= 15:
            q = ph - 10.5
            if (q % 2.2) < 1.3:
                return daoshi(g, HOME, FLOOR, "kneel", t)
            return figure(g, HOME, FLOOR, t, legs="kneel", arm="gong")
        return daoshi(g, HOME, FLOOR, "idle", t)

    # ------------------------------------------------------------ 天上

    def dipper(self, g: Gfx, lit, t: float, link_prog=None, flow: float | None = None, glow=None):
        """北斗：未亮的星是一点；亮的星是十字（天枢、天璇、天玑、天权、玉衡、开阳、摇光）；
        link_prog[i] = 第 i 段星线（i → i+1）画到哪"""
        segs = [(i, i + 1) for i in range(6)] + [(3, 0)]
        for a, b in segs:
            p = 1.0 if (lit[a] > 0 and lit[b] > 0) else 0.0
            if link_prog is not None and (a, b) != (3, 0):
                p = link_prog[a]
            if p <= 0:
                continue
            (x0, y0), (x1, y1) = STARS[a], STARS[b]
            L = math.hypot(x1 - x0, y1 - y0)
            for j in range(int(L * p)):
                if j > 2 and j < L - 2 and (j + int(t * 6)) % 3 == 0:
                    g.px(x0 + (x1 - x0) * j / L, y0 + (y1 - y0) * j / L)
            if flow is not None and p >= 1:
                q = (flow + a * 0.13) % 1
                g.px(x0 + (x1 - x0) * q, y0 + (y1 - y0) * q)
        for i, (x, y) in enumerate(STARS):
            big = glow is not None and glow[i]
            if lit[i] > 0 or big:
                star(g, x, y, 2, True, i * 0.37, t)
                if big or (t * 0.8 + i * 0.29) % 1 < 0.5:
                    for a in range(4):
                        aa = a * math.pi / 2 + math.pi / 4
                        g.px(x + round(math.cos(aa) * 4), y + round(math.sin(aa) * 4))
            else:
                g.k.rectangle((x - 2, y - 2, x + 2, y + 2), fill=1)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    g.px(x + dx, y + dy)

    def links(self, e: float, lamps):
        """星线进度：灯亮后 1 秒内从上一颗星画到这一颗"""
        c, k = int(e // self.CYCLE), e % self.CYCLE
        out = []
        for i in range(6):
            if lamps[i + 1] <= 0 or lamps[i] <= 0:
                out.append(0.0)
                continue
            a = self.lit_at(c, i + 1)
            out.append(span(k, a, a + 1.0) if not (c >= 1 and k < RENEW) else 1.0)
        return out

    # ------------------------------------------------------------ 公用

    def ambient(self, g: Gfx, e: float, t: float, lamps, dt: float):
        """流星、灯上飘火星"""
        m = (e % 37) / 1.2
        if m < 1:
            meteor(g, 40 + rand(int(e // 37), self.seed) * 40, 3, m, -26, 12)
        for i, v in enumerate(lamps):
            if v > 0 and rand(int((t + i * 0.31) * 3), self.seed + i) < 0.04 * dt * 30:
                self.embers.burst(LX[i], TOP - 14, 1, 4, up=10, life=1.0, gravity=-4)
        self.embers.step(dt)
        self.embers.draw(g, trail=False)

    def lamps_draw(self, g: Gfx, lamps, t: float):
        for i, v in enumerate(lamps):
            flame(g, LX[i], v, t, i)
            if 0 < v < 1:  # 刚点着：一圈光
                ring(g, LX[i], TOP - 13, 2 + v * 7)

    def caption(self, g: Gfx, n: int, e: float, k: float):
        """左上：最后点亮那盏灯的星名与星君；续时“第几遍”"""
        c = int(e // self.CYCLE)
        if c >= 1 and k < RENEW + 2.5:
            s = f"第{cn_num(c + 1)}遍" if c < 99 else f"{c + 1}遍"
            label(g, 5, 4, s)
            return
        if n <= 0:
            return
        i = n - 1
        g.k.rectangle((2, 1, 59, 17), fill=1)
        g.d.rectangle((2, 1, 59, 17), outline=1)
        g.px(31, 9)
        g.text(5, 4, NAME[i])
        g.text(33, 4, JUN[i])

    def mx(self, g: Gfx, lamps, t: float, nxt: int | None = None):
        n = sum(1 for v in lamps if v > 0)
        for i, (x, y) in enumerate(MX_POS):
            on = lamps[i] > 0
            if i == nxt and not on:
                on = (t * 2) % 1 < 0.5
            if n == 0 and i != nxt:   # 全暗时：北斗轮廓一颗颗轮流微闪
                on = int(t * 4) % 7 == i
            g.mx_set(x, y, on)

    def frame(self, g: Gfx, t: float, e: float, dt: float):
        lamps, n, c, k = self.lamps(e)
        stage(g, t, self.sk)
        self.dipper(g, lamps, t, self.links(e, lamps), flow=(t * 0.25) if n == 7 else None)
        self.lamps_draw(g, lamps, t)
        if c >= 1 and k < RENEW:
            self.renew_fx(g, k, t)
            daoshi(g, HOME, FLOOR, "raise" if k < 1.8 else "idle", t, face="happy")
        else:
            self.actor(g, e, t)
        self.ambient(g, e, t, lamps, dt)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.caption(g, n, e, k)
        self.mx(g, lamps, t, n if n < 7 else None)
        if c >= 1 and k < RENEW:
            for x, y in MX_POS:
                g.mx_set(x, y, True)
            if 1.6 <= k < 2.2:
                g.mx_level = 6

    def renew_fx(self, g: Gfx, k: float, t: float):
        """续：七朵灯焰化光球升天，到星位一闪"""
        q = span(k, 0.5, 1.6)
        if 0 < q < 1:
            for i, (sx, sy) in enumerate(STARS):
                x = lerp(LX[i], sx, ease_in_out(q))
                y = lerp(TOP - 14, sy, ease_in_out(q)) - math.sin(q * math.pi) * 6
                g.d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=1)
                g.px(x, y + 3), g.px(x, y + 5)
        if 1.6 <= k < 1.75:
            pix.flash(g)
        if 1.6 <= k < 2.4:
            for i, (sx, sy) in enumerate(STARS):
                sparkle(g, sx, sy, span(k, 1.6, 2.4))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        lv = span(t, 0, 1.5)
        lamps = [0.0] * 7
        if t > 5.1:
            lamps[0] = min((t - 5.1) / 0.35, 1) + 0.001
        stage(g, t, self.sk, lv)
        self.dipper(g, lamps, t)
        self.lamps_draw(g, lamps, t)
        stand = LX[0] - 10
        if t < 2.0:                    # 举烛走进来
            x = lerp(-12, HOME, span(t, 0, 2.0))
            h = figure(g, x, FLOOR, t, legs="walk", arm=arm("hold"), arm_at=(-3, -16))
            self.taper(g, h["hand"], t, 0.0)
        elif t < 3.2:                  # 向天一揖
            daoshi(g, HOME, FLOOR, "bow" if 2.4 < t < 3.0 else "gongshou", t)
        elif t < 3.2 + self.walk_time(0):
            x = HOME + SPEED * (t - 3.2)
            h = figure(g, x, FLOOR, t, legs="walk", arm=arm("hold"), arm_at=(-3, -16))
            self.taper(g, h["hand"], t, 0.0)
        else:
            tau = t - 3.2
            self.light_event(g, 0, tau, t)
        if 5.1 <= t < 5.1 + dt:
            self.sparks.burst(LX[0], TOP - 13, 12, 24, up=14, life=0.6, gravity=50)
            pix.shake(g, t, 1)
        if 5.1 <= t < 5.25:
            ring(g, STARS[0][0], STARS[0][1], (t - 5.1) * 60)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 5.3:
            self.caption(g, 1, 0.0, 99)
        self.mx(g, lamps, t, 0 if t < 5.1 else 1)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        self.frame(g, t, e, dt)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        lamps, n, c, k = self.lamps(e)
        lit_idx = [i for i, v in enumerate(lamps) if v > 0]
        out = {}
        for j, i in enumerate(reversed(lit_idx)):
            tt = 0.4 + j * 0.15
            out[i] = tt
            if t >= tt:
                lamps[i] = 0.0
            if abs(t - tt) < dt / 2 + 1e-6 or (tt <= t < tt + dt):
                self.puffs.emit(LX[i], TOP - 13, vy=-5, life=0.8, rmax=2.0, spread=0)
        stage(g, t, self.sk, 1 - 0.5 * span(t, 0.4, 1.4))
        self.dipper(g, lamps, t)
        self.lamps_draw(g, lamps, t)
        daoshi(g, HOME, FLOOR, "raise" if t < 1.4 else "idle", t)
        self.puffs.step(dt)
        self.puffs.draw(g)
        if t > 0.3:
            label(g, 5, 4, "暂熄")
        self.mx(g, lamps, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        lamps, n, c, k = self.lamps(e)
        lit_idx = [i for i, v in enumerate(lamps) if v > 0]
        stage(g, t, self.sk, 0.5 + 0.5 * span(t, 0.3, 1.5))
        h = daoshi(g, HOME, FLOOR, "point" if t < 1.6 else "idle", t)
        for j, i in enumerate(lit_idx):
            t0 = 0.25 + j * 0.16
            q = span(t, t0, t0 + 0.45)
            if 0 < q < 1:  # 火星沿弧线飞去
                hx, hy = h["hand"]
                px, py = lerp(hx, LX[i], q), lerp(hy, TOP - 12, q) - math.sin(q * math.pi) * 12
                g.d.ellipse((px - 1, py - 1, px + 1, py + 1), fill=1)
                g.px(px - 2, py + 1)
            if t < t0 + 0.45:
                lamps[i] = 0.0
            else:
                lamps[i] = min((t - t0 - 0.45) / 0.35, 1) + 0.001
            if t0 + 0.45 <= t < t0 + 0.45 + dt:
                self.sparks.burst(LX[i], TOP - 13, 6, 16, up=10, life=0.5, gravity=40)
        self.dipper(g, lamps, t, self.links(e, lamps) if t > 1.9 else None)
        self.lamps_draw(g, lamps, t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.caption(g, n, e, 99)
        self.mx(g, lamps, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        lamps, n, c, k = self.lamps(e)
        if c >= 1 and k < RENEW:
            lamps = [1.0] * 7
        un = [i for i, v in enumerate(lamps) if v <= 0]
        for j, i in enumerate(un):     # 余下的灯一齐燃起
            t0 = 0.2 + j * 0.12
            lamps[i] = 0.0 if t < t0 else min((t - t0) / 0.35, 1) + 0.001
            if t0 <= t < t0 + dt:
                self.sparks.burst(LX[i], TOP - 13, 5, 14, up=10, life=0.5, gravity=40)
        rise = span(t, 1.8, 3.0)
        glow = [rise >= 1] * 7
        stage(g, t, self.sk, 1.0)
        if rise <= 0:
            self.dipper(g, lamps, t)
            self.lamps_draw(g, lamps, t)
        else:
            self.dipper(g, [1.0] * 7, t, flow=t * 0.4, glow=glow)
            for i in range(7):
                flame(g, LX[i], 0.0, t, i)
            if rise < 1:
                for i, (sx, sy) in enumerate(STARS):
                    q = ease_in_out(rise)
                    x = lerp(LX[i], sx, q)
                    y = lerp(TOP - 14, sy, q) - math.sin(q * math.pi) * 8
                    g.d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=1)
                    pix.dotted(g, x, y + 2, x, y + 8, 2)
        pose = "gongshou" if t < 1.6 else ("kneel" if t < 5.0 else "idle")
        daoshi(g, HOME, FLOOR, pose, t, face="happy" if t > 5.0 else "normal")
        if 3.0 <= t < 3.0 + dt:
            pix.flash(g)
            for sx, sy in STARS:
                self.sparks.burst(sx, sy, 4, 18, life=0.8, gravity=10)
        if 3.0 < t < 3.3:
            pix.shake(g, t, 1.5)
        if t > 3.0:
            for i, (sx, sy) in enumerate(STARS):
                sparkle(g, sx, sy - 0, ((t - 3.0) * 1.5 + i * 0.3) % 1)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 3.4:
            y = pop_box(g, 30, 4, "消灾解厄", t, 3.4)
            g.text(30, y, "消灾解厄", align="center")
        # 点阵
        for i, (x, y) in enumerate(MX_POS):
            g.mx_set(x, y, lamps[i] > 0 or rise > 0)
        if t > 3.0:
            from .r5_util import mx_line
            for a, b in [(i, i + 1) for i in range(6)] + [(3, 0)]:
                mx_line(g, *MX_POS[a], *MX_POS[b])
            g.mx_level = 1 + int(6 * (1 - span(t, 3.0, 4.5)))
