"""鸣钟：钟楼里一口铜钟，吊着的撞木由小道士拉绳撞钟；“紧十八，慢十八，不紧不慢又十八”，两遍一百零八响。

依据：宫观“金钟玉磬”，钟用来集众、动神（daoinfo《Bells》引《太真科》）；寺观撞钟通行一百零八下，
口诀“紧十八，慢十八，不紧不慢又十八”，两遍合成一百零八；道观以钟板“开静”“止静”。
圆满句“琳琅振响”出自《度人经》“琳琅振响，十方肃清”。

入场：大钟从梁上落下晃两下，撞木荡进来；小道士走来拉住绳，牌子“起钟”。
持续：一轮 600 秒：开头 6 秒“起钟”（拱手、拉满），随后两遍（紧杵 3 秒 / 慢杵 8 秒 / 平杵 5 秒，各十八杵）
      共一百零八响，每一杵的时刻完全由 e 算出。小道士拉绳把撞木往后拽（身子后仰），一松手撞木荡回去，
      “咚”——钟身一震、往后一晃，声波弧一圈圈荡开，屏幕一震，点阵一闪；梁上的小鸟每响都被吓得一跳。
      牌子写当前节奏与响数。一百零八响后十几秒余音：钟慢慢停摆，小道士拱手。
      续：下一轮开头“起钟”——作揖，再把撞木拉满。
中断：小道士抱住撞木，钟声渐歇，牌子“止静”。  恢复：“开静”，拉开一撞，接上原来的节奏。
圆满：连撞三记重杵，声波满屏、钟身发亮，小道士跪拜，闪白，“琳琅振响”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_bounce, lerp, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import FLOOR, Clock, badge, floor, hit, mx_art, mx_burst, pose_arm, ring_dots, title

BX, BY = 101, 13           # 钟：顶部挂钩中心
LOG_Y = 35                # 撞木静止高度
LOG_X = 60                # 撞木静止时左端
DX = 38                   # 小道士
BEAM_Y = 8
START = 6.0               # 每轮开头“起钟”的秒数
TEMPO = (("紧杵", 3.0), ("慢杵", 8.0), ("平杵", 5.0))


def _times():
    out, t = [], START
    for _ in range(2):
        for name, iv in TEMPO:
            for _ in range(18):
                out.append((t, name, iv))
                t += iv
    return out


STRIKES = _times()        # 108 杵：(时刻, 节奏名, 间隔)
END = STRIKES[-1][0]

BIRD = pix.frames("""
 .##.
.####.##
 .####.
  #  #
---
 .##.
.####.##
.#####
  #  #
""")

BIRD_FLY = pix.sprite("""
#.  .#
.#..#.
.####.##
 .####.
""")


def _bell():
    """铜钟 27×30：蒲牢钮、钟肩、乳钉三排、两道弦纹、撞座（莲花）、波浪钟口；右侧背光网点"""
    p = Part(27, 31)
    p.shape("ellipse", (10, 0, 16, 5), fill=1)          # 钮
    p.d.ellipse((12, 1, 14, 3), fill=0)
    p.shape("polygon", [(6, 6), (20, 6), (22, 9), (22, 24), (25, 28), (1, 28), (4, 24), (4, 9)], fill=1)
    p.shape("ellipse", (4, 4, 22, 11), fill=1)          # 钟肩
    p.d.line((5, 11, 21, 11), fill=0)
    p.d.line((5, 13, 21, 13), fill=0)
    for r, y in enumerate((15, 18, 21)):               # 乳钉
        for x in range(7 if r % 2 == 0 else 8, 20, 3):
            p.px(x, y, 0)
    p.d.line((4, 23, 22, 23), fill=0)
    p.d.ellipse((6, 24, 10, 27), outline=0)            # 撞座
    p.px(8, 25, 0)
    for x in range(1, 26, 3):                          # 波浪钟口
        p.shape("ellipse", (x - 1, 27, x + 1, 29), fill=1)
    p.dither([(17, 8), (22, 9), (22, 24), (25, 28), (17, 28)], 0.5, 0)
    p.px(7, 8, 0), p.px(6, 9, 0)                        # 高光边
    return p.sprite()


def _log():
    """撞木 28×6：圆木、两道铁箍、木纹、钝头"""
    p = Part(28, 6)
    p.shape("rectangle", (1, 0, 25, 5), fill=1)
    p.shape("ellipse", (23, 0, 27, 5), fill=1)
    p.shape("ellipse", (0, 0, 3, 5), fill=1)
    for x in (6, 19):
        p.d.line((x, 0, x, 5), fill=0)
        p.d.line((x + 2, 0, x + 2, 5), fill=0)
    p.d.line((9, 2, 16, 2), fill=0)
    p.d.line((11, 3, 14, 3), fill=0)
    p.dither((1, 4, 26, 5), 0.5, 0)
    return p.sprite()


_P: dict = {}


def P(name):
    if name not in _P:
        _P[name] = {"bell": _bell, "log": _log}[name]()
    return _P[name]


def tower(g: Gfx):
    """钟楼：横梁（梁头云纹）、两根立柱、柱础、地面"""
    floor(g)
    g.d.rectangle((60, BEAM_Y, 125, BEAM_Y + 2), fill=1)
    g.d.line((61, BEAM_Y + 1, 124, BEAM_Y + 1), fill=0)
    g.d.arc((56, BEAM_Y - 1, 62, BEAM_Y + 5), 90, 270, fill=1)
    for x in (74, 122):
        g.d.rectangle((x - 1, BEAM_Y + 3, x + 1, FLOOR - 3), fill=1)
        g.px(x, BEAM_Y + 6, 0)
        g.d.rectangle((x - 3, FLOOR - 2, x + 3, FLOOR - 1), fill=1)
        pix.checker(g, (x - 2, FLOOR - 2, x + 4, FLOOR), 0.5, fill=0)


def bell(g: Gfx, sway: float, glow: bool = False):
    """钟 + 挂钩；sway：钟身摆动像素"""
    spr = P("bell")
    x = BX - 13 + round(sway)
    g.d.line((BX, BEAM_Y + 3, BX + round(sway * 0.3), BY), fill=1)
    pix.blit(g, spr, x, BY, invert=glow)


def log_and_ropes(g: Gfx, d: float):
    """撞木（d：离静止位置的水平位移，负 = 往后拉）+ 两根吊绳"""
    lift = d * d / 70
    x = LOG_X + d
    y = LOG_Y - lift
    for ax in (LOG_X + 5, LOG_X + 22):
        g.d.line((ax, BEAM_Y + 3, ax + d, y), fill=1)
    pix.blit(g, P("log"), x, y - 2)
    return (x, y)


def waves(g: Gfx, age: float, power: float = 1.0):
    """声波：两侧一圈圈往外荡的点状弧"""
    if age < 0 or age > 2.0:
        return
    cx, cy = BX, BY + 18
    for j in range(3):
        r = 16 + (age * 26 + j * 7) * power
        if r > 70:
            continue
        step = 2 if age < 0.8 else 3
        ring_dots(g, cx, cy, r, step, a0=-0.6, a1=0.6, sy=0.9)
        if r < 34:
            ring_dots(g, cx, cy, r, step, a0=math.pi - 0.5, a1=math.pi + 0.5, sy=0.9)


def mx_bell(g: Gfx, hit_age: float, t: float):
    off = 0
    if 0 <= hit_age < 0.4:
        off = (1 if int(hit_age * 20) % 2 else -1)
    mx_art(g, """
...##...
..####..
.######.
.######.
.######.
########
""", off, 0)
    if 0 <= hit_age < 0.8:
        r = int(hit_age * 5)
        g.mx[7, max(0, 3 - r):min(8, 5 + r)] = True
    if 0 <= hit_age < 0.15:
        g.mx_level = 7


# ---------------------------------------------------------------- 场景

@register
class BellRing(Ritual):
    id = "r1.bell"
    name = "鸣钟"
    desc = "小道士拉绳撞钟：紧十八、慢十八、不紧不慢又十八，两遍一百零八响，钟身一震声波荡开，梁上小鸟吓一跳"
    T = {"enter": 5.0, "interrupt": 1.8, "resume": 2.4, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    def state(self, e: float):
        """(撞木位移 d, 上一杵后的秒数, 已撞几杵, 节奏名)"""
        k = e % self.CYCLE
        if k < START:
            if k < START - 0.5:
                d = -16 * ease_in_out(span(k, 3.0, START - 0.5))
            else:
                d = -16 + 16 * ease_in(span(k, START - 0.5, START))
            return d, 99.0, 0, "起钟"
        if k >= END:
            age = k - END
            d = -2 * math.exp(-age) * math.sin(age * 6)
            return d, age, 108, "余音"
        lo, hi = 0, len(STRIKES) - 1
        while lo < hi:   # 最后一个 ≤ k 的杵
            mid = (lo + hi + 1) // 2
            if STRIKES[mid][0] <= k:
                lo = mid
            else:
                hi = mid - 1
        ts, name, iv = STRIKES[lo]
        tau = k - ts
        A = 7 + iv * 1.6
        p = tau / iv
        if p < 0.12:
            d = 2.5 * math.sin(p / 0.12 * math.pi)       # 撞上后反弹一下
        elif p < 0.78:
            d = -A * ease_in_out(span(p, 0.15, 0.78))    # 往后拉
        else:
            d = -A * (1 - ease_in(span(p, 0.78, 1.0)))   # 松手荡回去
        return d, tau, lo + 1, name

    def counter(self, g: Gfx, e: float, label: str | None = None):
        if label is None:
            d, age, n, name = self.state(e)
            label = name if n == 0 or name == "余音" else f"{name} {cn_num(n)}"
        badge(g, 4, 4, label)

    def puller(self, g: Gfx, t: float, d: float, log_xy, face: str = "normal"):
        """小道士拉绳：撞木越往后，身子越往后仰（往左挪），手攥绳"""
        x = DX + d * 0.35
        ang = 0 if d < -6 else -30
        h = pose_arm(g, x, FLOOR, t, ang, face=face)
        hx, hy = h["hand"]
        lx, ly = log_xy
        g.d.line((hx, hy, lx, ly + 1), fill=1)
        g.d.rectangle((hx - 1, hy - 1, hx + 1, hy + 1), fill=1)

    def bird(self, g: Gfx, age: float, t: float):
        bx, by = 108, BEAM_Y - 4
        if 0 <= age < 0.7:
            hop = math.sin(age / 0.7 * math.pi) * 6
            pix.blit(g, BIRD_FLY, bx - 1, by - hop)
        else:
            pix.blit(g, BIRD[int(t * 0.7) % 2], bx, by)

    def frame(self, g: Gfx, t: float, d: float, age: float, dt: float, power: float = 1.0, face: str = "normal",
              glow: bool = False):
        tower(g)
        sway = 0.0
        if 0 <= age < 3:
            sway = 1.6 * power * math.exp(-age * 1.5) * math.sin(age * 9)
        bell(g, sway, glow)
        lx = log_and_ropes(g, d)
        self.puller(g, t, d, lx, face=face)
        waves(g, age, power)
        self.bird(g, age, t)
        if 0 <= age < 0.25:
            pix.shake(g, t, 1.0 * power)
        if 0 <= age < dt * 1.5:
            self.sparks.burst(BX - 12, BY + 25, int(6 * power), 22, up=4, life=0.4, gravity=40)
        self.sparks.step(dt)
        self.sparks.draw(g)

    # ------------------------------------------------------------ 入场 / 持续

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        tower(g)
        drop = ease_out_bounce(span(t, 0.1, 1.0))
        y_off = lerp(-40, 0, drop)
        spr = P("bell")
        sway = 2 * math.exp(-max(t - 1.0, 0) * 2) * math.sin(t * 8) if t > 1.0 else 0
        g.d.line((BX, BEAM_Y + 3, BX, BY + y_off), fill=1)
        pix.blit(g, spr, BX - 13 + round(sway), BY + y_off)
        if hit(t, 0.48, dt):
            pix.shake(g, t, 1.5)
        swing = ease_out(span(t, 0.8, 2.2))
        d = lerp(-34, 0, swing) + (3 * math.sin((t - 2.2) * 5) * math.exp(-(t - 2.2) * 2) if t > 2.2 else 0)
        lx = log_and_ropes(g, d)
        if t < 3.2:
            x = lerp(-14, DX, ease_out(span(t, 1.4, 3.2)))
            daoshi(g, x, FLOOR, "walk", t)
        else:
            self.puller(g, t, 0, lx)
        self.bird(g, 99, t)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 3.2:
            self.counter(g, 0.0, "起钟")
        mx_bell(g, 99, t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        d, age, n, name = self.state(e)
        face = "happy" if 0.2 < age < 0.8 and name in ("慢杵", "平杵") else "normal"
        if k < 3.0:      # 起钟：拱手、作揖
            tower(g)
            bell(g, 0)
            lx = log_and_ropes(g, 0)
            daoshi(g, DX, FLOOR, "gongshou" if k < 1.6 else "bow", t)
            self.bird(g, 99, t)
        elif name == "余音":
            if age > 6:   # 余音里拱手
                tower(g)
                bell(g, 0)
                log_and_ropes(g, d)
                daoshi(g, DX, FLOOR, "gongshou" if (age % 8) < 5 else "idle", t, face="happy")
                self.bird(g, 99, t)
            else:
                self.frame(g, t, d, age, dt, face="happy")
        else:
            self.frame(g, t, d, age, dt, face=face)
        self.counter(g, e)
        mx_bell(g, age, t)

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        d0, age, n, name = self.state(e)
        d = lerp(d0, 0, ease_out(span(t, 0.0, 0.8)))
        self.frame(g, t, d, age + t if age < 50 else 99, dt)
        self.counter(g, e, "止静" if t > 0.5 else None)
        mx_bell(g, 99, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        d1, age1, n, name = self.state(e)
        if t < 1.4:       # 开静：拉开一撞
            d = -18 * ease_in_out(span(t, 0.1, 1.1)) * (1 - ease_in(span(t, 1.1, 1.4)))
            age = 99
        else:
            age = t - 1.4
            d = lerp(2.5 * math.sin(min(age / 0.3, 1) * math.pi), d1, span(t, 1.7, 2.4))
        self.frame(g, t, d, age, dt)
        self.counter(g, e, "开静" if t < 1.8 else None)
        mx_bell(g, age, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        hits = (1.0, 2.1, 3.2)
        prev = max([h for h in hits if h <= t], default=None)
        nxt = min([h for h in hits if h > t], default=None)
        if nxt is not None:
            start = prev if prev is not None else 0.0
            p = span(t, start + 0.1, nxt)
            d = -22 * ease_in_out(span(p, 0, 0.75)) * (1 - ease_in(span(p, 0.75, 1.0)))
        else:
            d = 2 * math.exp(-(t - 3.2)) * math.sin((t - 3.2) * 6)
        age = t - prev if prev is not None else 99
        if t < 3.6:
            self.frame(g, t, d, age, dt, power=1.6, glow=0 <= age < 0.12)
        else:
            tower(g)
            bell(g, 1.2 * math.exp(-(t - 3.2) * 1.5) * math.sin((t - 3.2) * 9))
            log_and_ropes(g, d)
            daoshi(g, DX, FLOOR, "kneel" if t < 5.4 else "idle", t, face="happy" if t > 5.4 else "normal")
            waves(g, age, 1.6)
            self.bird(g, age, t)
            self.sparks.step(dt)
            self.sparks.draw(g)
        for h in hits:
            if hit(t, h, dt):
                self.sparks.burst(BX, BY + 15, 14, 34, life=0.7, gravity=20)
        if hit(t, 3.2, dt):
            pix.flash(g)
        if t > 3.5:
            title(g, 31, 4, "琳琅振响", t, 3.5)
        mx_bell(g, age, t)
        mx_burst(g, t, 3.2)
