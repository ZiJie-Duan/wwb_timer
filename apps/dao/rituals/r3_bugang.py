"""步罡踏斗：星夜的坛场上铺开一张罡单（透视的星图），小道士掐剑诀，按禹步一星一星地踏过去；
每踏上一星，脚下荡开一圈涟漪、星被踏亮，天上的北斗也跟着亮一颗。

步罡踏斗源于禹步，道士在铺开的罡单（星图）上按星位行步，配合掐诀念咒以“步天”。
禹步“步不相过”：前脚迈出，后脚跟上并拢。北斗七星加左辅、右弼两颗隐星为九星，对应“三步九迹”。

入场：罡单从地面铺开，九个星位逐个显现；小道士从左边走来，踏上天枢，脚下一圈涟漪。
持续：一轮 630 秒、九步，每 70 秒迈一步：蓄力下蹲 → 一跃（地上投影）→ 落到下一颗星（涟漪、火星、震屏）→
      后脚跟上并拢。两步之间他掐剑诀站定，时而剑指向天，脚下星位一明一暗。走过的罡步在罡单上连成实线。
      左上写星名与星君名。续：“回罡”，一跳一星倒退回天枢，星一颗颗熄灭。
中断：罡单上的星暗下，小道士拱手站定，写“住罡”。  恢复：脚下涟漪一圈，星位复明。
圆满：余下的星位快步踏完，九星齐亮、连成北斗，天上北斗放光，题“斗转星移”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r3_kit import Clock, banner, banner_text, crossed, label, mx_ring, pose_arm, rays, round_of, sparkle

NAMES = ["天枢", "天璇", "天玑", "天权", "玉衡", "开阳", "摇光", "辅星", "弼星"]
JUN = ["贪狼", "巨门", "禄存", "文曲", "廉贞", "武曲", "破军", "左辅", "右弼"]
MAT = [(14, 62), (114, 62), (102, 41), (26, 41)]           # 罡单（近大远小的梯形）
STAR = [(22, 59), (33, 47), (45, 57), (56, 45), (68, 55), (79, 44), (92, 54), (100, 43), (110, 58)]
SKY = [(80, 5), (78, 13), (88, 15), (90, 8), (100, 7), (109, 9), (119, 15), (112, 5), (124, 10)]
MXS = [(0, 6), (1, 3), (2, 6), (3, 3), (4, 6), (5, 2), (6, 5), (6, 1), (7, 7)]
CYCLE = 630.0
STEP = 70.0
MOVE = 1.6
RENEW = 6.0


def mat(g: Gfx, t: float, show: float = 1.0):
    """罡单：双线边框、四角云纹，里面稀网点（show < 1 时从近往远铺开）"""
    (x0, y0), (x1, _), (x2, y2), (x3, _) = MAT
    yy = lerp(y0, y2, show)
    k = (y0 - yy) / (y0 - y2)
    lx, rx = lerp(x0, x3, k), lerp(x1, x2, k)
    poly = [(x0, y0), (x1, y0), (rx, yy), (lx, yy)]
    g.d.polygon(poly, fill=0, outline=1)
    inner = [(x0 + 4, y0 - 1), (x1 - 4, y0 - 1), (rx - 3, yy + 1), (lx + 3, yy + 1)]
    if show > 0.2:
        g.d.polygon(inner, outline=1)
    for x in range(int(lx) + 6, int(rx) - 4, 8):   # 远边的回纹
        if show >= 1:
            g.px(x, yy - 0), g.px(x + 2, yy)
    g.d.line((0, 62, 127, 62), fill=1)


def star_mark(g: Gfx, x: float, y: float, state: int, t: float, i: int):
    """罡单上的星位：0 未到（压扁的小菱形）/ 1 已踏（实心星 + 一圈）/ 2 当前（闪）"""
    if state == 0:
        g.d.polygon([(x - 3, y), (x, y - 1), (x + 3, y), (x, y + 1)], fill=0, outline=1)
        if (t * 0.5 + rand(i, 2) * 7) % 7 < 0.2:
            g.px(x, y)
    else:
        g.d.ellipse((x - 5, y - 2, x + 5, y + 2), outline=1)
        g.d.polygon([(x - 3, y), (x, y - 2), (x + 3, y), (x, y + 2)], fill=1)
        g.px(x, y - 3), g.px(x, y + 3)
        if state == 2 and (t * 2) % 1 < 0.5:
            g.d.ellipse((x - 7, y - 3, x + 7, y + 3), outline=1)


def sky(g: Gfx, lit: int, t: float, seed: int, bright: bool = False):
    for i in range(14):
        x = int(rand(i, seed) * 70) + 44
        y = int(rand(i, seed + 1) * 26) + 2
        if (t * 0.6 + rand(i, seed + 2) * 5) % 5 > 0.3 and not any(abs(x - a) < 4 and abs(y - b) < 4 for a, b in SKY):
            g.px(x, y)
    for i in range(6):
        a, b = SKY[i], SKY[i + 1]
        if i + 1 < lit:
            if bright:
                g.d.line((a, b), fill=1)
            else:
                pix.dotted(g, a[0], a[1], b[0], b[1], 2)
    for i, (x, y) in enumerate(SKY):
        if i < lit:
            g.d.line((x - 1, y, x + 1, y), fill=1)
            g.d.line((x, y - 1, x, y + 1), fill=1)
            if bright and (t * 4 + i) % 2 < 1:
                sparkle(g, x, y, 2)
        else:
            g.px(x, y)


@register
class BugangRitual(Ritual):
    id = "r3.bugang"
    name = "步罡踏斗"
    desc = "星夜坛场上铺开罡单，小道士掐剑诀按禹步一星一星踏过去，落脚处涟漪荡开、星被踏亮，天上北斗随之亮起"
    T = {"enter": 6.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.8}
    CYCLE = CYCLE

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.clock = Clock()
        self.ss = self.rng.randrange(1000)
        self.ripples: list[list] = []

    # ------------------------------------------------------------ 公用

    def ripple(self, x, y, big=False):
        self.ripples.append([x, y, 0.0, big])

    def fx(self, g: Gfx, dt: float):
        keep = []
        for r in self.ripples:
            r[2] += dt
            if r[2] < 0.8:
                rr = 4 + r[2] * (30 if r[3] else 20)
                if r[2] > 0.5:
                    for a in range(0, 360, 20):
                        g.px(r[0] + math.cos(math.radians(a)) * rr, r[1] + math.sin(math.radians(a)) * rr * 0.35)
                else:
                    g.d.ellipse((r[0] - rr, r[1] - rr * 0.35, r[0] + rr, r[1] + rr * 0.35), outline=1)
                keep.append(r)
        self.ripples = keep
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    def board(self, g: Gfx, lit: int, cur: int, t: float, dim: bool = False, show: float = 1.0, nshow: int = 9):
        mat(g, t, show)
        for i in range(min(lit, 9) - 1):   # 走过的罡步连成实线
            a, b = STAR[i], STAR[i + 1]
            g.d.line((a, b), fill=1)
        for i in range(min(nshow, 9)):
            x, y = STAR[i]
            st = 0 if dim or i >= lit else (2 if i == cur else 1)
            star_mark(g, x, y, st, t, i)

    def walker(self, g: Gfx, k: float, t: float, dt: float, face: str | None = None, quick: float = 1.0):
        """按本轮秒数 k 画小道士：站在第 i 星上，或正在跳向下一星"""
        i = min(int(k // STEP), 8)
        u = k - i * STEP
        if i >= 1 and u < MOVE * quick:
            self.hop(g, i - 1, i, u / quick, t, dt)
            return
        x, y = STAR[i]
        flip = i < 8 and STAR[min(i + 1, 8)][0] < x
        v = u % 12.0      # 站定时的小动作：剑指 → 剑指向天 → 拱手
        if v < 7.0:
            pose_arm(g, x, "fwd", t, "jian", y=y, face=face or "normal", flip=flip)
        elif v < 9.5:
            pose_arm(g, x, "up30", t, "jian", y=y, face=face or "normal", flip=flip)
            if crossed(v, dt, 7.4):
                self.sparks.burst(x + 14, y - 26, 6, 16, life=0.4, gravity=10)
            if 7.4 <= v < 8.2:
                sparkle(g, x + (13 if not flip else -13), y - 27, 2)
        else:
            daoshi(g, x, y, "gongshou", t, face=face or "normal")

    def hop(self, g: Gfx, a: int, b: int, u: float, t: float, dt: float):
        """禹步一跳：下蹲蓄力 → 腾空（投影）→ 落地（涟漪、火星、震屏）→ 后脚跟上"""
        (x0, y0), (x1, y1) = STAR[a], STAR[b]
        flip = x1 < x0
        if u < 0.35:      # 蓄力
            figure(g, x0, y0, t, legs="walk", arm="gong", flip=flip, dy=1, bob=False)
            return
        if u < 0.95:      # 腾空
            q = ease_in_out((u - 0.35) / 0.6)
            x, y = lerp(x0, x1, q), lerp(y0, y1, q)
            h = math.sin(q * math.pi) * 9
            for dx in range(-3, 4, 2):   # 投影
                g.px(x + dx, y + 1)
            figure(g, x, y, 0.26, legs="walk", arm="point", flip=flip, dy=-int(h), bob=False)
            return
        if crossed(u, dt, 0.95):
            self.ripple(x1, y1)
            self.sparks.burst(x1, y1 - 2, 12, 28, up=16, life=0.6, gravity=80)
            self.puffs.emit(x1 - 6, y1 - 1, vx=-10, vy=-3, life=0.5, rmax=1.4)
            self.puffs.emit(x1 + 6, y1 - 1, vx=10, vy=-3, life=0.5, rmax=1.4)
        if u < 1.3:       # 落地：前脚着地，后脚还在后面
            if u < 1.1:
                pix.shake(g, t, 1)
            figure(g, x1, y1, 0.26, legs="walk", arm="point", flip=flip, face="wow", bob=False)
        else:             # 后脚跟上并拢
            figure(g, x1, y1, t, legs="walk" if u < 1.45 else "stand", arm="point", flip=flip, bob=False)

    def lit_of(self, k: float) -> int:
        i = min(int(k // STEP), 8)
        u = k - i * STEP
        return i + 1 if (i == 0 or u >= 0.95) else i

    def mx(self, g: Gfx, lit: int, cur: int, t: float, dim: bool = False):
        for i, (x, y) in enumerate(MXS):
            if dim:
                g.mx[y, x] = (t + i * 0.3) % 2 < 0.2
            elif i < lit:
                g.mx[y, x] = i != cur or (t * 3) % 1 < 0.6
            else:
                g.mx[y, x] = (t * 0.5 + rand(i, 4) * 6) % 6 < 0.15

    def names(self, g: Gfx, i: int):
        label(g, 3, 3, NAMES[i])
        label(g, 4, 16, JUN[i], size=8)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        sky(g, 0, t, self.ss)
        show = span(t, 0.0, 1.4)
        n = int(span(t, 1.2, 3.0) * 9.99)
        self.board(g, 0, -1, t, show=show, nshow=n)
        if t < 3.2:
            x = lerp(-14, STAR[0][0] - 8, ease_out(span(t, 1.4, 3.2)))
            if t > 1.4:
                daoshi(g, x, STAR[0][1], "walk", t)
        elif t < 4.4:
            self.hop_in(g, t - 3.2, t, dt)
        else:
            pose_arm(g, STAR[0][0], "fwd", t, "jian", y=STAR[0][1])
        if t >= 4.0:
            star_mark(g, *STAR[0], 2, t, 0)
        self.fx(g, dt)
        if t >= 4.0:
            self.names(g, 0)
        else:
            label(g, 3, 3, "罡单")
        self.mx(g, 1 if t >= 4.0 else 0, 0, t)

    def hop_in(self, g: Gfx, u: float, t: float, dt: float):
        x0, y0 = STAR[0][0] - 8, STAR[0][1]
        x1, y1 = STAR[0]
        if u < 0.3:
            figure(g, x0, y0, t, legs="walk", arm="gong", dy=1, bob=False)
        elif u < 0.8:
            q = (u - 0.3) / 0.5
            figure(g, lerp(x0, x1, q), y0, 0.26, legs="walk", arm="point", dy=-int(math.sin(q * math.pi) * 7), bob=False)
        else:
            if crossed(u, dt, 0.8):
                self.ripple(x1, y1, True)
                self.sparks.burst(x1, y1 - 2, 16, 30, up=16, life=0.6, gravity=80)
            if u < 0.95:
                pix.shake(g, t, 1)
            figure(g, x1, y1, t, legs="stand", arm="point", face="wow", bob=False)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of(e, CYCLE)
        if e >= CYCLE and k < RENEW:
            self.renew(g, k, t, dt)
            return
        lit = self.lit_of(k)
        i = min(int(k // STEP), 8)
        sky(g, lit, t, self.ss)
        self.board(g, lit, i, t)
        self.walker(g, k, e, dt)
        self.fx(g, dt)
        self.names(g, lit - 1)
        self.mx(g, lit, lit - 1, t)

    def renew(self, g: Gfx, k: float, t: float, dt: float):
        """回罡：一跳一星倒退回天枢，星一颗颗熄灭"""
        j = min(int(span(k, 0.3, 4.8) * 8.999), 8)
        f = span(k, 0.3, 4.8) * 8.999 - j
        lit = 9 - j
        sky(g, lit, t, self.ss)
        self.board(g, lit, lit - 1, t)
        if k < 4.8 and j < 8:
            a, b = 8 - j, 7 - j
            (x0, y0), (x1, y1) = STAR[a], STAR[b]
            q = ease_in_out(f)
            figure(g, lerp(x0, x1, q), lerp(y0, y1, q), 0.26, legs="walk", arm="gong", flip=x1 < x0,
                   dy=-int(math.sin(q * math.pi) * 6), bob=False)
            if f > 0.95 and int(k * 30) % 2 == 0:
                self.puffs.emit(x0, y0 - 1, vy=-5, life=0.5, rmax=1.5)
        else:
            if crossed(k, dt, 4.8):
                self.ripple(*STAR[0], True)
            daoshi(g, STAR[0][0], STAR[0][1], "gongshou" if k < 5.4 else "idle", t, face="happy")
        self.fx(g, dt)
        label(g, 3, 3, "回罡" if k < 4.8 else "复始")
        self.mx(g, lit, lit - 1, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % CYCLE
        lit = self.lit_of(k)
        i = min(int(k // STEP), 8)
        dim = t > 0.6
        sky(g, 0 if dim else lit, t, self.ss)
        self.board(g, lit, i, t, dim=dim)
        x, y = STAR[i]
        daoshi(g, x, y, "gongshou" if t > 0.3 else "idle", t)
        self.fx(g, dt)
        label(g, 3, 3, "住罡" if dim else NAMES[lit - 1])
        self.mx(g, lit, i, t, dim=dim)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % CYCLE
        lit = self.lit_of(k)
        i = min(int(k // STEP), 8)
        on = t > 0.6
        sky(g, lit if on else 0, t, self.ss)
        self.board(g, lit, i, t, dim=not on)
        x, y = STAR[i]
        if crossed(t, dt, 0.6):
            self.ripple(x, y, True)
            self.sparks.burst(x, y - 2, 12, 24, up=12, life=0.5, gravity=60)
        if 0.6 <= t < 0.66:
            pix.flash(g)
        if t < 1.2:
            figure(g, x, y, t, legs="stand", arm="point", face="wow" if on else "normal", dy=0 if t > 0.4 else 1)
        else:
            pose_arm(g, x, "fwd", t, "jian", y=y)
        self.fx(g, dt)
        self.names(g, lit - 1) if on else label(g, 3, 3, "住罡")
        self.mx(g, lit, i, t, dim=not on)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % CYCLE
        start = min(int(k // STEP), 8)
        # 快步：0.5 秒一星踏完余下的
        steps = 8 - start
        per = 0.5
        done = start + min(steps, int(t / per))
        bright = t > steps * per + 0.3
        lit = min(9, done + 1 if t >= steps * per else done + (1 if (t % per) / per >= 0.6 else 0) + 0)
        lit = max(lit, self.lit_of(k))
        sky(g, lit, t, self.ss, bright=bright)
        self.board(g, lit, -1, t)
        if bright:   # 九星连成一线：一点光沿罡步来回跑，天上北斗放光
            q = (t * 0.8) % 1
            seg = q * 8
            j = min(int(seg), 7)
            (ax, ay), (bx, by) = STAR[j], STAR[j + 1]
            f = seg - j
            sparkle(g, lerp(ax, bx, f), lerp(ay, by, f), 3)
            rays(g, 100, 9, 14, 20, 10, rot=t, dash=2)
        if t < steps * per and done < 8:
            u = (t % per) / per * MOVE
            self.hop(g, done, done + 1, u, t, dt)
        else:
            x, y = STAR[8]
            pose_arm(g, x, "up30", t, "jian", y=y, face="happy", flip=True)
        T0 = steps * per + 0.3
        if crossed(t, dt, T0):
            self.sparks.burst(100, 9, 24, 40, life=1.0, gravity=20)
            for s in STAR:
                self.ripple(s[0], s[1])
        if T0 <= t < T0 + 0.08:
            pix.flash(g)
        if T0 <= t < T0 + 0.4:
            pix.shake(g, t, 1.5)
        self.fx(g, dt)
        if t > T0 + 0.4:
            banner(g, 44, 6, "斗转星移", span(t, T0 + 0.4, T0 + 0.8))
            banner_text(g, 44, 6, "斗转星移", span(t, T0 + 0.4, T0 + 0.8))
        else:
            self.names(g, max(lit - 1, 0))
        self.mx(g, lit, -1, t)
        if t > T0:
            mx_ring(g, (t - T0) * 4)
            g.mx_level = 1 + int(5 * (1 - span(t, T0, T0 + 1.4)))
