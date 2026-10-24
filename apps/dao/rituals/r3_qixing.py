"""七星剑：夜里的石坛上，小道士舞七星剑——劈、刺、挽剑花，剑气飞出；剑身里藏着一片“夜空”，
随计时一颗颗亮起北斗七星，每亮一颗，天上对应的星先降下一道光到剑上。

七星剑是道教法剑，剑身嵌北斗七星，用以召将、斩邪。北斗七星：天枢、天璇、天玑、天权、玉衡、开阳、摇光，
道经称其星君为贪狼、巨门、禄存、文曲、廉贞、武曲、破军（《北斗七星延命经》）。
圆满句“气冲斗牛”化用《晋书·张华传》：斗牛之间常有紫气，乃宝剑之精上彻于天。

入场：小道士持剑走上坛，站定，举剑过顶、一劈，剑气飞出，天上北斗七个星位淡淡显现。
持续：一轮 630 秒，每 88 秒剑身亮一颗星（天光降到剑上、闪白、火星）；其间每 10 秒一套剑招：劈、刺、剑花、
      回身再劈；每隔几秒一道流光走过剑身。左上写星名与星君名。
      续：七星齐明后剑指北斗，七颗星从剑上飞回天上，北斗一闪，剑身复暗。
中断：收剑平按，北斗暗下，写“按剑”。  恢复：举剑一挥，流光走过，北斗复明。
圆满：余下的星依次补亮，剑直指天，七道星光直射北斗，闪白震屏，北斗放光，题“气冲斗牛”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r3_kit import (FIST, FLOOR, Clock, a8, banner, banner_text, crossed, hit, hand_at, mx_ring, orient8,
                     pose_arm, put, round_of, smear, sparkle)
from .r3_kit import label as lab

DX = 30                    # 小道士站位
STARS = ["天枢", "天璇", "天玑", "天权", "玉衡", "开阳", "摇光"]
JUN = ["贪狼", "巨门", "禄存", "文曲", "廉贞", "武曲", "破军"]
SKY = [(72, 6), (70, 17), (83, 20), (86, 10), (98, 9), (109, 12), (121, 19)]   # 天上北斗（天枢 → 摇光）
MXS = [(1, 0), (0, 2), (2, 3), (3, 1), (5, 1), (6, 2), (7, 4)]                    # 点阵上的北斗
CYCLE = 630.0
LIGHT = [10 + 88 * i for i in range(7)]     # 本轮第几秒亮第 i 颗
RENEW = 6.0
MOVE = 6.0                                  # 一套剑招的周期


# ---------------------------------------------------------------- 七星剑（逐像素，8 个方向）

def _sword0() -> Sprite:
    """朝右的七星剑：剑首小环、剑柄、剑格（两端回卷）、剑身三行（上下刃亮、中间一道“夜空”暗槽）、剑尖"""
    p = Part(35, 9)
    cy = 4
    for x, y in ((1, cy - 1), (0, cy), (2, cy), (1, cy + 1), (3, cy)):     # 剑首环
        p.px(x, y)
    p.px(1, cy, 0)
    p.shape("rectangle", (4, cy - 1, 6, cy + 1), fill=1)                   # 剑柄（缠绳）
    p.px(5, cy - 1, 0), p.px(4, cy + 1, 0), p.px(6, cy + 1, 0)
    p.shape("rectangle", (7, cy - 3, 8, cy + 3), fill=1)                   # 剑格
    p.px(6, cy - 4), p.px(6, cy + 4)
    p.px(8, cy, 0)
    p.shape("rectangle", (9, cy - 1, 30, cy + 1), fill=1)                  # 剑身
    p.d.line((10, cy, 30, cy), fill=0)                                     # 暗槽
    p.shape("line", (31, cy, 33, cy), fill=1)                              # 剑尖
    p.px(31, cy - 1, 0), p.px(31, cy + 1, 0)
    p.mk.putpixel((31, cy - 1), 0), p.mk.putpixel((31, cy + 1), 0)
    s = Sprite(on=__import__("numpy").array(p.on, bool), mask=__import__("numpy").array(p.mk, bool))
    s.anchor = (5, cy)
    s.pts = {f"s{i}": (11 + 3 * i, cy) for i in range(7)}
    s.pts.update(tip=(33, cy), base=(10, cy), pommel=(1, cy + 1))
    return s


def _sword45() -> Sprite:
    """朝右上的七星剑（逐行 #.# 的斜刃）"""
    import numpy as np
    W = 27
    p = Part(W, W)
    ax, ay = 4, 22

    def P(s, k=0):
        return ax + s + k, ay - s

    for s, k in ((-4, 0), (-3, -1), (-3, 1), (-2, 0)):                      # 剑首环
        p.px(*P(s, k))
    p.px(*P(-3, 0), 0)
    for s in (-1, 0, 1):                                                   # 剑柄
        for k in (-1, 0, 1):
            p.px(*P(s, k))
    p.px(*P(0, 0), 0)
    for j in range(-3, 4):                                                 # 剑格（另一条对角线，两像素厚）
        p.px(ax + 2 + j, ay - 2 + j)
        p.px(ax + 3 + j, ay - 2 + j)
    for s in range(4, 20):                                                 # 剑身
        for k in (-1, 0, 1):
            p.px(*P(s, k), 0 if k == 0 else 1)
    p.px(*P(20, 0)), p.px(*P(21, 0)), p.px(*P(20, -1)), p.px(*P(20, 1), 1)
    s = Sprite(on=np.array(p.on, bool), mask=np.array(p.mk, bool))
    s.anchor = (ax, ay)
    s.pts = {f"s{i}": P(5 + 2 * i) for i in range(7)}
    s.pts.update(tip=P(21), base=P(4), pommel=P(-3, 0))
    return s


_SW: dict = {}


def sword_spr(ang: int) -> Sprite:
    if not _SW:
        _SW.update(orient8(_sword0(), _sword45()))
    return _SW[a8(ang)]


def draw_sword(g: Gfx, hand, ang: float, lit: int, t: float, glint: float = -1.0, flip: bool = False,
               fresh: int = -1, fist: bool = True) -> dict:
    """持剑：hand = 握点；lit = 剑身已亮星数；glint ∈ [0,1] 一道流光；fresh = 刚亮的那颗（闪）"""
    a = a8(ang)
    spr = sword_spr(a)
    pts = put(g, spr, hand[0], hand[1], flip=flip)
    # 剑穗：从剑首垂下，随时间摆
    px, py = pts["pommel"]
    sw = math.sin(t * 3.1) * 1.2
    g.d.line((px, py, px + sw, py + 3), fill=1)
    g.d.rectangle((px + sw - 1, py + 3, px + sw, py + 4), fill=1)
    g.px(px + sw * 1.3, py + 6), g.px(px + sw * 1.4 - 1, py + 6)
    for i in range(lit):
        x, y = pts[f"s{i}"]
        g.px(x, y, 1)
    if 0 <= glint <= 1:  # 流光：三像素亮段沿暗槽走
        b, tp = pts["base"], pts["tip"]
        for d in (-0.06, 0, 0.06):
            q = min(max(glint + d, 0), 1)
            g.px(lerp(b[0], tp[0], q), lerp(b[1], tp[1], q), 1)
        q = glint
        sparkle(g, lerp(b[0], tp[0], q), lerp(b[1], tp[1], q), 2, dark=False)
    if 0 <= fresh < 7 and int(t * 8) % 2 == 0:
        x, y = pts[f"s{fresh}"]
        sparkle(g, x, y, 2)
        g.px(x, y, 1)
    if fist:
        pix.blit(g, FIST, hand[0] - 1, hand[1] - 2)
    return pts


# ---------------------------------------------------------------- 剑气（月牙）

SLASH = pix.frames("""
  ##
   ##
    #
    ##
    ##
    ##
    #
   ##
  ##
---
 #
  ##
   ##
   ##
   ##
   ##
   ##
  ##
 #
""")


# ---------------------------------------------------------------- 背景

def sky(g: Gfx, lit: int, t: float, seed: int, dim: float = 1.0, nxt: int = -1, bright: bool = False):
    """夜空小星 + 远山 + 北斗（亮的画十字星并连线，未亮的是一个暗点，下一颗慢慢闪）"""
    for i in range(16):
        x = int(rand(i, seed) * 124) + 2
        y = int(rand(i, seed + 7) * 36) + 2
        if x < 44 and y < 26:
            continue
        if any(abs(x - sx) < 4 and abs(y - sy) < 4 for sx, sy in SKY):
            continue
        if (t * 0.7 + rand(i, seed + 3) * 5) % 5 > 0.4:
            g.px(x, y)
    # 远山（只勾轮廓，山脚稀网点）
    ridge = [(44, 58), (52, 47), (58, 50), (66, 42), (74, 48), (82, 44), (92, 50), (102, 41), (112, 47), (120, 44),
             (128, 49)]
    for a, b in zip(ridge, ridge[1:]):
        g.d.line((a, b), fill=1)
    for k, (sx, sy) in enumerate(SKY):
        if k < lit and dim > 0.5:
            if k + 1 < lit:
                if bright:
                    g.d.line((sx, sy, SKY[k + 1][0], SKY[k + 1][1]), fill=1)
                else:
                    pix.dotted(g, sx, sy, SKY[k + 1][0], SKY[k + 1][1], 2)
    for k, (sx, sy) in enumerate(SKY):
        if k < lit and dim > 0.5:
            g.d.rectangle((sx - 2, sy - 2, sx + 2, sy + 2), fill=0)
            g.d.line((sx - 1, sy, sx + 1, sy), fill=1)
            g.d.line((sx, sy - 1, sx, sy + 1), fill=1)
            if bright and (t * 4 + k) % 2 < 1:
                sparkle(g, sx, sy, 3)
            elif (t * 1.3 + k * 0.37) % 3 < 0.25:
                sparkle(g, sx, sy, 2)
        elif k == nxt:
            g.px(sx - 1, sy), g.px(sx + 1, sy), g.px(sx, sy - 1), g.px(sx, sy + 1)
            if (t * 2) % 1 < 0.5:
                g.px(sx, sy)
        else:   # 未亮的星位：小空心菱形（和背景小星分得开）
            g.px(sx - 1, sy), g.px(sx + 1, sy), g.px(sx, sy - 1), g.px(sx, sy + 1)


def ground(g: Gfx):
    """石坛：坛沿 + 方砖"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    g.d.line((0, FLOOR + 2, 127, FLOOR + 2), fill=1)
    for x in range(4, 128, 12):
        g.d.line((x, FLOOR + 1, x, FLOOR + 1), fill=1)
        g.d.line((x + 6, FLOOR + 3, x + 6, 63), fill=1)
    pix.checker(g, (0, FLOOR + 3, 128, 64), 0.125)


def mx_dipper(g: Gfx, lit: int, t: float, nxt: int = -1):
    for k, (x, y) in enumerate(MXS):
        if k < lit:
            g.mx[y, x] = True
        elif k == nxt:
            g.mx[y, x] = (t * 2) % 1 < 0.5
    for x, y in ((0, 7), (1, 6), (2, 5), (3, 4)):
        g.mx[y, x] = True
    g.mx[5, 0] = g.mx[7, 2] = True


# ---------------------------------------------------------------- 剑招

# 姿势：(手臂, 剑的方向, 身体位移, 弓步)
READY = ("low", -45, 0, False)
RAISE = ("up60", -135, -1, False)
CHOP = ("fwd", 0, 3, True)
PULL = ("low", 0, -2, False)
THRUST = ("fwd", 0, 5, True)
SKYP = ("up30", -45, 0, False)
UP = ("up90", -90, 0, False)
REST = ("low", 0, 0, False)


@register
class QixingRitual(Ritual):
    id = "r3.qixing"
    name = "七星剑"
    desc = "小道士夜里在石坛上舞七星剑：劈、刺、挽剑花，剑气飞出；剑身随计时亮起北斗七星，天上北斗随之连成"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 1.8, "complete": 5.5}
    CYCLE = CYCLE

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.clock = Clock()
        self.slash = None      # 飞出的剑气 [x, y, age]
        self.sky_seed = self.rng.randrange(1000)

    # ------------------------------------------------------------ 公用

    def lit_of(self, k: float) -> int:
        return sum(1 for T in LIGHT if k >= T)

    def figure(self, g: Gfx, pose, t: float, lit: int, glint=-1.0, fresh=-1, face="normal", dx=0.0, ang=None,
               behind=False):
        kind, sa, bx, wide = pose
        x = DX + bx + dx
        legs = "walk" if wide else "stand"
        tt = 0.26 if wide else t      # 弓步：取“迈开”的那一帧
        ang = sa if ang is None else ang
        prop = lambda g2, h: draw_sword(g2, h, ang, lit, t, glint, fresh=fresh, fist=not behind)  # noqa: E731
        h = pose_arm(g, x, kind, tt, "fist", legs=legs, face=face, prop=prop, prop_behind=behind)
        return h

    def fx(self, g: Gfx, dt: float):
        if self.slash:
            s = self.slash
            s[2] += dt
            s[0] += 150 * dt
            if s[0] > 132 or s[2] > 0.8:
                self.slash = None
            else:
                pix.blit(g, SLASH[int(s[2] * 10) % 2], s[0], s[1] - 4)
                if int(s[2] * 30) % 2 == 0:
                    self.sparks.burst(s[0], s[1] + (rand(int(s[2] * 30), 3) - 0.5) * 8, 1, 8, life=0.3, gravity=10)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def move(self, g: Gfx, u: float, m: int, t: float, lit: int, dt: float, glint: float):
        """一套剑招（u = 本套已过秒数）"""
        sh = (DX - 2, FLOOR - 16)
        if m in (0, 3):   # 劈：举剑 → 一劈（残影）→ 命中星、剑气飞出 → 收
            if u < 0.45:
                pose = READY if u < 0.15 else RAISE
                self.figure(g, pose, t, lit, behind=pose is RAISE)
            elif u < 1.5:
                self.figure(g, CHOP, t, lit, face="wow" if u < 0.8 else "normal")
                if u < 0.6:
                    smear(g, sh[0] + 4, sh[1] + 2, 28, 6, -140, 5, solid=0.5 if u < 0.52 else 0.2)
                if crossed(u, dt, 0.45):
                    tip = (DX + 3 + 36, FLOOR - 13)
                    self.sparks.burst(tip[0], tip[1], 10, 34, up=10, life=0.5, gravity=80)
                    self.puffs.emit(DX + 8, FLOOR - 1, vx=10, vy=-3, life=0.6, rmax=1.5)
                    self.puffs.emit(DX - 6, FLOOR - 1, vx=-10, vy=-3, life=0.6, rmax=1.5)
                    self.slash = [tip[0], FLOOR - 13, 0.0]
                if u < 0.62:
                    hit(g, DX + 3 + 38, FLOOR - 13, (u - 0.45) / 0.17)
                    pix.shake(g, t, 1.2)
            else:
                self.figure(g, READY, t, lit, glint=glint)
        elif m == 1:      # 刺：后撤蓄力 → 弓步直刺（速度线、气爆圈）→ 收
            if u < 0.5:
                self.figure(g, PULL, t, lit)
            elif u < 1.5:
                q = span(u, 0.5, 0.58)
                self.figure(g, THRUST, t, lit, dx=lerp(-6, 0, ease_out(q)), face="wow" if u < 0.9 else "normal")
                tip_x = DX + THRUST[2] + 8 + 28
                if u < 0.8:
                    for i, yy in enumerate((FLOOR - 13, FLOOR - 9, FLOOR - 20)):
                        x0 = DX - 14 + i * 3 + (u - 0.5) * 30
                        pix.dotted(g, x0, yy, x0 + 8, yy, 2, phase=i)
                if 0.55 < u < 0.9:
                    r = (u - 0.55) * 30
                    g.d.ellipse((tip_x - r * 0.5, FLOOR - 12 - r, tip_x + r * 0.5, FLOOR - 12 + r), outline=1)
                if crossed(u, dt, 0.58):
                    self.sparks.burst(tip_x, FLOOR - 12, 8, 40, life=0.35, gravity=0)
            else:
                self.figure(g, READY, t, lit, glint=glint)
        else:             # 挽剑花：剑绕手转两圈，圆形残影
            if u < 1.2:
                ang = -45 + int(u * 16) * 45
                h = hand_at(DX, FLOOR, "up30", t)
                smear(g, h[0], h[1], 26, 4, ang - 150, ang, solid=0.35)
                self.figure(g, SKYP, t, lit, ang=ang, behind=a8(ang) in (180, -135, 135))
                if int(u * 30) % 4 == 0:
                    tip = h[0] + math.cos(math.radians(ang)) * 26, h[1] + math.sin(math.radians(ang)) * 26
                    self.sparks.burst(tip[0], tip[1], 1, 10, life=0.3, gravity=20)
            else:
                self.figure(g, READY if u > 1.8 else SKYP, t, lit, glint=glint)

    def counter(self, g: Gfx, lit: int, label: str | None = None):
        """左上：星名 + 星君名（最后画）"""
        if label:
            lab(g, 3, 3, label)
        elif lit == 0:
            lab(g, 3, 3, "北斗")
        else:
            lab(g, 3, 3, STARS[lit - 1])
            lab(g, 4, 16, JUN[lit - 1], size=8)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        reveal = span(t, 3.4, 5.2)
        sky(g, 0, t, self.sky_seed, nxt=-1 if reveal < 1 else -1)
        if reveal < 1:  # 星位淡淡显现：先少后多
            for k, (sx, sy) in enumerate(SKY):
                if rand(k, 5) > reveal:
                    g.px(sx, sy, 0)
        ground(g)
        if t < 2.2:    # 持剑走上坛
            x = lerp(-14, DX, ease_out(span(t, 0, 2.2)))
            h = daoshi(g, x, FLOOR, "walk", t)["hand"]
            draw_sword(g, (h[0], h[1] - 1), -45, 0, t)
        elif t < 3.0:
            self.figure(g, READY, t, 0, glint=span(t, 2.3, 2.9))
        else:
            u = t - 3.0 + 0.0
            self.move(g, u * 0.9 if u < 0.5 else u - 0.05, 0, t, 0, dt, -1)
        self.fx(g, dt)
        self.counter(g, 0)
        mx_dipper(g, 0, t)
        if reveal < 1:
            g.mx[:4] = g.mx[:4] & (int(t * 6) % 2 == 0)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        lit = self.lit_of(k)
        glint = span((e % 3.7), 0, 0.6) if (e % 3.7) < 0.6 else -1
        if k >= CYCLE - RENEW:      # 续：七星飞回天上
            self.renew(g, k - (CYCLE - RENEW), t, dt)
            return
        # 正在亮星？
        ev = next((i for i, T in enumerate(LIGHT) if T - 1.8 <= k < T + 1.2), None)
        nxt = lit if lit < 7 else -1
        sky(g, lit, t, self.sky_seed, nxt=nxt)
        ground(g)
        if ev is not None:
            T = LIGHT[ev]
            u = k - (T - 1.8)
            sx, sy = SKY[ev]
            if u < 1.8:
                self.figure(g, SKYP, t, lit, face="wow" if u > 1.0 else "normal")
                tip = hand_at(DX, FLOOR, "up30", t)
                tip = (tip[0] + 15, tip[1] - 15)
                q = span(u, 0.6, 1.8)
                if q > 0:   # 天光从星上一节节降到剑尖
                    yy = lerp(sy, tip[1], ease_in_out(q))
                    xx = lerp(sx, tip[0], ease_in_out(q))
                    pix.dotted(g, sx, sy, xx, yy, 2, phase=int(t * 20))
                    g.d.ellipse((xx - 1, yy - 1, xx + 1, yy + 1), fill=1)
                    sparkle(g, sx, sy, 3)
            else:
                self.figure(g, SKYP, t, lit, fresh=ev, face="happy")
                if crossed(k, dt, T):
                    pass
                if u < 1.9:
                    pix.flash(g)
                if u < 2.1:
                    pix.shake(g, t, 1)
            if crossed(k, dt, T):
                h = hand_at(DX, FLOOR, "up30", t)
                self.sparks.burst(h[0] + 8, h[1] - 8, 16, 34, up=14, life=0.7, gravity=50)
        else:
            u = e % MOVE
            m = int(e // MOVE) % 4
            fresh = lit - 1 if lit and k - LIGHT[lit - 1] < 6 else -1
            if u < 2.2:
                self.move(g, u, m, t, lit, dt, glint)
            elif 3.6 <= u < 4.6 and m % 2 == 1:   # 收势：举剑直立一礼，剑尖一闪
                self.figure(g, ("up30", -90, 0, False), t, lit, fresh=fresh)
                h = hand_at(DX, FLOOR, "up30", t)
                if 3.8 <= u < 4.1:
                    sparkle(g, h[0], h[1] - 33, 3)
            else:
                self.figure(g, READY, t, lit, glint=glint, fresh=fresh)
        self.fx(g, dt)
        self.counter(g, lit)
        mx_dipper(g, lit, t, nxt)

    def renew(self, g: Gfx, u: float, t: float, dt: float):
        """u ∈ [0, RENEW)：剑指北斗 → 七星离剑飞回天上 → 北斗一闪 → 剑身复暗"""
        fly = span(u, 1.0, 3.0)
        back = [i for i in range(7) if span(u, 1.0 + i * 0.15, 2.4 + i * 0.15) >= 1]
        sky(g, 7 if u >= 3.0 and u < 4.2 else 0, t, self.sky_seed)
        for k in back:
            sx, sy = SKY[k]
            g.d.line((sx - 1, sy, sx + 1, sy), fill=1), g.d.line((sx, sy - 1, sx, sy + 1), fill=1)
        ground(g)
        if u < 3.2:
            h = hand_at(DX, FLOOR, "up30", t)
            pts = None

            def prop(g2, hh):
                nonlocal pts
                pts = draw_sword(g2, hh, -45, 7 if fly <= 0 else 0, t)
            pose_arm(g, DX, "up30", t, "fist", prop=prop, face="happy" if u > 2.5 else "normal")
            for i in range(7):  # 星从剑上沿弧线飞向天上
                q = span(u, 1.0 + i * 0.15, 2.4 + i * 0.15)
                if 0 < q < 1:
                    x0, y0 = pts[f"s{i}"]
                    sx, sy = SKY[i]
                    x = lerp(x0, sx, ease_in_out(q))
                    y = lerp(y0, sy, ease_in_out(q)) - math.sin(q * math.pi) * 8
                    sparkle(g, x, y, 1, dark=False)
                    if int(t * 30) % 3 == i % 3:
                        self.sparks.burst(x, y, 1, 6, life=0.3, gravity=0)
                elif q <= 0 and fly <= 0:
                    pass
            if crossed(u, dt, 3.0):
                self.sparks.burst(96, 13, 20, 40, life=0.9, gravity=10)
            if 3.0 <= u < 3.08:
                pix.flash(g)
        else:
            self.figure(g, READY, t, 0, glint=span(u, 4.5, 5.2) if u > 4.5 else -1)
        if 3.0 <= u < 4.2:
            r = 8 + (u - 3.0) * 30
            g.d.ellipse((96 - r, 13 - r * 0.6, 96 + r, 13 + r * 0.6), outline=1)
        self.fx(g, dt)
        self.counter(g, 0 if u > 3.0 else 7, "复始" if u > 3.0 else None)
        mx_dipper(g, 7 if u < 3.2 else 0, t)
        if 3.0 <= u < 4.0:
            mx_ring(g, (u - 3.0) * 6)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        lit = self.lit_of(e % CYCLE)
        dim = 1 - span(t, 0.4, 1.2)
        sky(g, lit, t, self.sky_seed, dim=dim)
        ground(g)
        self.figure(g, READY if t < 0.4 else REST, t, lit)
        if crossed(t, dt, 0.4):
            self.puffs.emit(DX + 14, FLOOR - 4, vx=6, vy=-4, life=0.6, rmax=1.5)
        self.fx(g, dt)
        self.counter(g, lit, "按剑" if t > 0.4 else None)
        mx_dipper(g, lit if dim > 0.5 else 0, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        lit = self.lit_of(e % CYCLE)
        on = t > 0.8
        sky(g, lit if on else 0, t, self.sky_seed, dim=1 if on else 0)
        ground(g)
        if t < 0.35:
            self.figure(g, REST, t, lit)
        elif t < 0.8:
            self.figure(g, RAISE, t, lit, behind=True)
        else:
            self.figure(g, SKYP if t < 1.3 else READY, t, lit, glint=span(t, 0.8, 1.3))
            if t < 1.0:
                smear(g, DX, FLOOR - 16, 28, 5, -170, -45, solid=0.4)
        if crossed(t, dt, 0.8):
            self.sparks.burst(DX + 20, FLOOR - 34, 12, 30, up=10, life=0.6)
        if 0.8 <= t < 0.87:
            pix.flash(g)
        self.fx(g, dt)
        self.counter(g, lit)
        mx_dipper(g, lit if on else 0, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        lit0 = self.lit_of(e % CYCLE)
        lit = min(7, lit0 + int(span(t, 0, 1.5) * (7 - lit0) + (0.999 if t >= 1.5 else 0)))
        bright = t >= 2.4
        sky(g, lit, t, self.sky_seed, bright=bright)
        ground(g)
        if t < 1.5:
            self.figure(g, SKYP, t, lit, fresh=lit - 1 if lit > lit0 else -1)
        elif t < 1.9:
            self.figure(g, READY, t, lit, face="wow")
        else:
            pts = None

            def prop(g2, hh):
                nonlocal pts
                pts = draw_sword(g2, hh, -45, 7, t, glint=span(t, 1.9, 2.3))
            pose_arm(g, DX, "up30", t, "fist", prop=prop, face="happy" if t > 2.4 else "wow")
            q = span(t, 1.9, 2.4)
            for i in range(7):  # 七道星光从剑上直射北斗
                x0, y0 = pts[f"s{i}"]
                sx, sy = SKY[i]
                if q < 1:
                    pix.dotted(g, x0, y0, lerp(x0, sx, q), lerp(y0, sy, q), 2, phase=int(t * 30))
                elif t < 3.0:
                    pix.dotted(g, x0, y0, sx, sy, 3, phase=int(t * 20))
        for i in range(lit0, lit):
            if crossed(t, dt, (i - lit0 + 1) * 1.5 / max(7 - lit0, 1) - 0.01):
                self.sparks.burst(SKY[i][0], SKY[i][1], 8, 20, life=0.5)
        if crossed(t, dt, 2.4):
            self.sparks.burst(96, 13, 30, 50, up=10, life=1.2, gravity=30)
        if 2.4 <= t < 2.5:
            pix.flash(g)
        if 2.4 <= t < 2.8:
            pix.shake(g, t, 1.5)
        self.fx(g, dt)
        if t > 2.7:
            banner(g, 88, 34, "气冲斗牛", span(t, 2.7, 3.1))
        self.counter(g, lit)
        if t > 2.7:
            banner_text(g, 88, 34, "气冲斗牛", span(t, 2.7, 3.1))
        mx_dipper(g, lit, t)
        if t > 2.4:
            mx_ring(g, (t - 2.4) * 4)
            g.mx_level = 1 + int(6 * (1 - span(t, 2.4, 3.8)))
