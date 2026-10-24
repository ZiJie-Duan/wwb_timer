"""观星：小道士在观星台上守着浑仪，一宿一宿地看过二十八宿。

依据：二十八宿分属四象——东方苍龙（角亢氐房心尾箕）、北方玄武（斗牛女虚危室壁）、
西方白虎（奎娄胃昴毕觜参）、南方朱雀（井鬼柳星张翼轸）。每宿的星官画成连线星图
（星数、形状按传统星图简化，如心宿三星、昴宿七星团、参宿十星、鬼宿中央积尸气）。
浑仪：子午环、地平环、赤道环、窥管，龙柱托起，十字底座。

画面：左边观星台（石栏），台上一架浑仪，小道士站在旁边；右边夜空里是当前这一宿的星官，远山。
入场：星空淡入，小道士走上台，浑仪的环转起来，第一宿“角”的星一颗颗亮起、连线。
持续：一轮 10 分钟看完二十八宿（一周天），每宿约 21 秒：星官从东边淡入、一颗颗点亮连线，慢慢往西移，
      然后淡出换下一宿。小道士的动作随之：剑指指认 → 转动浑仪对准（窥管指向星官）→ 展卷记录 → 静立；
      左上写宿名与所属四象，底下 28 个刻度标出走到第几宿。约 41 秒一颗流星。
      续（一周天满）：浑仪急转，满天星斗绕极一圈拖出星轨，“几周天”。
中断：云从左边飘来遮住星空，“云掩”。  恢复：云向右飘走。
圆满：浑仪飞转，四象依次闪现（苍龙、玄武、白虎、朱雀），小道士作揖，“斗转星移”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r5_util import STAR_S, Clock, arm, cached, cloud_sprite, label, meteor, mx_ring, pop_box, sky, sparkle, star

NAMES = "角亢氐房心尾箕斗牛女虚危室壁奎娄胃昴毕觜参井鬼柳星张翼轸"
SIXIANG = ["东方苍龙", "北方玄武", "西方白虎", "南方朱雀"]
# 每宿星图：若干条连线（每条一串点），坐标 0..7
ASTER = [
    [[(1, 5), (6, 2)]],                                                    # 角
    [[(1, 3), (3, 1), (5, 2), (6, 5)]],                                    # 亢
    [[(1, 1), (6, 2), (5, 6), (2, 5), (1, 1)]],                            # 氐
    [[(5, 0), (4, 2), (3, 4), (3, 6)]],                                    # 房
    [[(1, 2), (3, 4), (6, 5)]],                                            # 心
    [[(1, 0), (1, 2), (2, 4), (2, 6), (4, 7), (6, 6), (7, 4), (6, 3)]],    # 尾
    [[(1, 1), (1, 5), (6, 6), (5, 2)]],                                    # 箕
    [[(0, 5), (2, 6), (4, 5), (4, 2), (6, 1), (7, 3)]],                    # 斗
    [[(2, 1), (4, 0), (6, 1)], [(4, 0), (3, 3), (3, 6), (5, 6)]],          # 牛
    [[(1, 2), (3, 1), (5, 3), (6, 6)]],                                    # 女
    [[(2, 2), (5, 5)]],                                                    # 虚
    [[(1, 5), (3, 1), (6, 4)]],                                            # 危
    [[(2, 1), (5, 6)]],                                                    # 室
    [[(4, 0), (4, 6)]],                                                    # 壁
    [[(3, 0), (5, 1), (6, 3), (6, 5), (4, 7), (2, 7), (1, 5), (1, 3), (2, 1), (3, 0)]],  # 奎
    [[(1, 5), (4, 3), (6, 1)]],                                            # 娄
    [[(2, 1), (6, 3), (2, 5), (2, 1)]],                                    # 胃
    [[(2, 2)], [(4, 1)], [(5, 3)], [(3, 4)], [(6, 5)], [(1, 5)], [(4, 6)]],  # 昴
    [[(0, 0), (2, 3), (3, 5), (5, 3), (7, 1)], [(3, 5), (3, 7)]],          # 毕
    [[(3, 2), (5, 3), (4, 5), (3, 2)]],                                    # 觜
    [[(1, 0), (3, 3), (6, 1)], [(3, 3), (4, 4), (5, 5)], [(1, 7), (4, 4)], [(5, 5), (6, 7)]],  # 参
    [[(1, 2), (3, 2), (5, 2), (7, 2)], [(0, 5), (2, 5), (4, 5), (6, 5)]],  # 井
    [[(1, 1), (6, 1), (6, 6), (1, 6), (1, 1)], [(3, 3)]],                  # 鬼
    [[(0, 3), (2, 1), (4, 1), (6, 2), (7, 4), (6, 6), (4, 7), (2, 6)]],    # 柳
    [[(0, 5), (2, 3), (4, 4), (6, 2), (7, 0)], [(4, 4), (5, 7)]],          # 星
    [[(1, 1), (3, 3), (5, 3), (6, 5)], [(3, 3), (2, 6)]],                  # 张
    [[(0, 6), (2, 4), (4, 3), (6, 4), (7, 6)], [(4, 3), (4, 0)], [(2, 4), (1, 1)], [(6, 4), (7, 1)]],  # 翼
    [[(1, 2), (6, 1), (6, 6), (1, 5), (1, 2)], [(0, 0)], [(7, 7)]],        # 轸
]
FLOOR = 50                 # 观星台台面
DX = 40                    # 小道士
AX, AY, AR = 15, 29, 8     # 浑仪球心与半径
SKY_X, SKY_Y, SC = 68, 3, 6.0   # 星官图左上角与缩放
SLOT = 600.0 / 28


def mansion_pts(i):
    """第 i 宿：[(连线点列表), ...] → 屏幕坐标（未加漂移）"""
    return [[(SKY_X + x * SC, SKY_Y + y * SC) for x, y in chain] for chain in ASTER[i]]


def bright(i):
    """每宿最亮的一颗：第一条连线的第一颗"""
    return ASTER[i][0][0]


def armillary(g: Gfx, spin: float, aim: float = 0.0):
    """浑仪：十字底座、龙柱、子午环（双线）、地平环、随 spin 转动的赤道环、斜插的极轴、窥管（指向 aim 弧度）"""
    cx, cy, r = AX, AY, AR
    # 底座与柱
    g.d.rectangle((cx - 9, FLOOR - 2, cx + 9, FLOOR - 1), fill=1)
    g.d.line((cx - 8, FLOOR - 1, cx + 8, FLOOR - 1), fill=0)
    g.px(cx - 9, FLOOR), g.px(cx + 9, FLOOR)
    g.d.rectangle((cx - 1, cy + r + 1, cx + 1, FLOOR - 3), fill=1)
    for y in range(cy + r + 2, FLOOR - 3, 2):          # 柱上盘龙：交错的鳞点
        g.px(cx + (1 if (y // 2) % 2 else -1), y, 0)
    g.d.polygon([(cx - 4, cy + r + 1), (cx + 4, cy + r + 1), (cx + 2, cy + r + 3), (cx - 2, cy + r + 3)], fill=1)
    # 背面的半个赤道环（暗，虚线）
    tilt = 0.55

    def ring_pts(phase, radius, front):
        out = []
        for k in range(0, 48):
            a = k / 48 * 2 * math.pi
            x3, y3, z3 = math.cos(a) * radius, 0.0, math.sin(a) * radius
            # 赤道面绕 x 轴倾斜，再绕竖轴转 spin
            y3, z3 = y3 * math.cos(tilt) - z3 * math.sin(tilt), y3 * math.sin(tilt) + z3 * math.cos(tilt)
            c, s = math.cos(phase), math.sin(phase)
            x3, z3 = x3 * c - z3 * s, x3 * s + z3 * c
            out.append((cx + x3, cy + y3, z3))
        return [(x, y) for x, y, z in out if (z >= 0) == front]
    for x, y in ring_pts(spin, r - 1, False)[::2]:
        g.px(x, y)
    # 子午环（双线）与地平环
    g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
    g.d.ellipse((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), outline=1)
    for a in range(0, 360, 30):                        # 环上刻度
        x, y = cx + math.cos(math.radians(a)) * (r + 1), cy + math.sin(math.radians(a)) * (r + 1)
        g.px(x, y)
    g.d.ellipse((cx - r - 3, cy - 2, cx + r + 3, cy + 2), outline=1)
    # 极轴（斜）
    ax, ay = math.sin(0.5) * (r + 4), -math.cos(0.5) * (r + 4)
    g.d.line((cx - ax, cy - ay, cx + ax, cy + ay), fill=1)
    g.d.rectangle((cx + ax - 1, cy + ay - 1, cx + ax + 1, cy + ay + 1), fill=1)
    # 前面的半个赤道环
    pts = ring_pts(spin, r - 1, True)
    for x, y in pts:
        g.px(x, y)
    # 窥管：从球心穿出，指向 aim
    tx, ty = math.cos(aim) * (r + 5), math.sin(aim) * (r + 5)
    g.d.line((cx - tx * 0.6, cy - ty * 0.6, cx + tx, cy + ty), fill=0, width=3)
    g.d.line((cx - tx * 0.6, cy - ty * 0.6, cx + tx, cy + ty), fill=1)
    g.d.rectangle((cx + tx - 1, cy + ty - 1, cx + tx + 1, cy + ty + 1), fill=1)
    g.d.rectangle((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
    g.px(cx, cy, 0)


def terrace(g: Gfx):
    """观星台：台面、石栏（望柱 + 栏板网点）、台身砖缝"""
    g.d.rectangle((0, FLOOR, 56, FLOOR + 1), fill=1)
    g.d.line((0, FLOOR + 1, 56, FLOOR + 1), fill=0)
    g.d.rectangle((0, FLOOR + 2, 54, 63), fill=0, outline=1)
    for y in range(FLOOR + 4, 64, 3):
        for x in range((y // 3 % 2) * 4 + 2, 54, 8):
            g.d.line((x, y, x + 5, y), fill=1)
    g.d.line((56, FLOOR, 56, 63), fill=1)


def mountains(g: Gfx):
    pts = [(56, 54), (66, 49), (74, 52), (86, 45), (98, 51), (108, 47), (118, 52), (128, 49)]
    g.d.line(pts, fill=1)
    from PIL import Image, ImageDraw
    import numpy as np
    m = Image.new("1", (128, 64))
    ImageDraw.Draw(m).polygon(pts + [(128, 64), (56, 64)], fill=1)
    mk = np.array(m, bool)
    mk[:56, :] &= False
    g.k.polygon(pts + [(128, 64), (56, 64)], fill=1)
    pix.checker_mask(g, mk & (np.arange(64)[:, None] > 52) & (np.arange(64)[:, None] < 58), 0.25)
    g.d.rectangle((57, 58, 127, 63), fill=0)


@register
class Xiu(Clock, Ritual):
    id = "r5.xiu"
    name = "观星"
    desc = "观星台上小道士守着浑仪，二十八宿一宿一宿从东边升起：指认、转仪对准、展卷记录；一轮看满一周天"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 1.6, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sk = self.rng.randrange(1000)

    def cur(self, e: float):
        """→ (第几宿, 本宿内秒数)"""
        k = e % self.CYCLE
        i = min(int(k / SLOT), 27)
        return i, k - i * SLOT

    # ------------------------------------------------------------ 画

    def mansion(self, g: Gfx, i: int, tau: float, t: float, lit: float = 1.0):
        """当前一宿：淡入时星一颗颗点亮（弹出）、连线画出；中段慢慢西移；末尾淡出"""
        drift = lerp(6, -6, tau / SLOT)
        fade_in = span(tau, 0.2, 2.0)
        fade_out = 1 - span(tau, SLOT - 1.4, SLOT - 0.2)
        k = min(fade_in, fade_out) * lit
        if k <= 0:
            return
        chains = mansion_pts(i)
        allp = [p for ch in chains for p in ch]
        n = len(allp)
        shown = int(round(k * n + 0.49))
        for ch in chains:                          # 连线：疏点虚线
            for (x0, y0), (x1, y1) in zip(ch, ch[1:]):
                L = math.hypot(x1 - x0, y1 - y0)
                for j in range(int(L * min(1, k * 1.5))):
                    if j % 2 == 0:
                        g.px(x0 + drift + (x1 - x0) * j / L, y0 + (y1 - y0) * j / L)
        bx, by = bright(i)
        for j, (x, y) in enumerate(allp):
            if j >= shown:
                continue
            pop = ease_out_back(span(tau, 0.2 + j * 0.12, 0.5 + j * 0.12)) if fade_in < 1 else 1
            big = abs(x - (SKY_X + bx * SC)) < 0.1 and abs(y - (SKY_Y + by * SC)) < 0.1
            g.k.rectangle((x + drift - 2, y - 2, x + drift + 2, y + 2), fill=1)
            if pop < 0.5:
                g.px(x + drift, y)
            else:
                star(g, x + drift, y, 2 if big else 1, True, j * 0.3, t)

    def ticks(self, g: Gfx, i: int, t: float, all_flash: bool = False):
        """底部 28 个刻度：走过的实、当前的高而闪"""
        for j in range(28):
            x = 60 + j * 2.4
            if all_flash:
                h = 2 if (t * 8 + j * 0.2) % 1 < 0.5 else 1
            elif j == i:
                h = 3 if (t * 2) % 1 < 0.7 else 2
            else:
                h = 1 if j < i else 0
            g.d.line((x, 62, x, 62 - h), fill=1)
        g.d.line((58, 62, 127, 62), fill=1)

    def caption(self, g: Gfx, i: int):
        g.text(4, 3, NAMES[i] + "宿")
        g.text(31, 5, SIXIANG[i // 7][2:], size=8)

    def actor(self, g: Gfx, tau: float, t: float, i: int):
        """一宿之内：指认 → 转仪 → 记录 → 静立"""
        if 2.0 < tau < 5.5:
            h = figure(g, DX, FLOOR, t, arm=arm("sky"), arm_at=(3, -25), face="wow" if tau < 3.2 else "normal")
            return
        if 6.0 < tau < 9.0:   # 转身扶住浑仪转动
            return figure(g, DX, FLOOR, t, arm="offer", flip=True)
        if 10.0 < tau < 16.0:  # 展卷记录：左手托卷、右手提笔（手微动）
            h = figure(g, DX, FLOOR, t, arm=arm("hold"), arm_at=(-3, -16 - (1 if (t * 5) % 1 < 0.5 else 0)))
            hx, hy = h["hand"]
            g.d.rectangle((hx - 2, hy + 1, hx + 4, hy + 3), fill=1)    # 卷
            g.d.line((hx - 1, hy + 2, hx + 3, hy + 2), fill=0)
            g.px(hx - 3, hy + 2), g.px(hx + 5, hy + 2)
            g.d.line((hx + 2, hy - 4, hx + 1, hy), fill=1)             # 笔
            return
        if 17.0 < tau < 18.5:
            return daoshi(g, DX, FLOOR, "gongshou", t)
        return daoshi(g, DX, FLOOR, "idle", t)

    def aim(self, tau: float, i: int):
        """窥管方向：转仪时从上一宿转到这一宿"""
        bx, by = bright(i)
        tx, ty = SKY_X + bx * SC, SKY_Y + by * SC
        a1 = math.atan2(ty - AY, tx - AX)
        pb = bright((i - 1) % 28)
        a0 = math.atan2(SKY_Y + pb[1] * SC - AY, SKY_X + pb[0] * SC - AX)
        return lerp(a0, a1, ease_in_out(span(tau, 6.0, 9.0)))

    def mx(self, g: Gfx, i: int, t: float, k: float = 1.0):
        for ch in ASTER[i]:
            for x, y in ch:
                g.mx_set(x, y, True)
        bx, by = bright(i)
        if (t * 1.5) % 1 < 0.2:
            g.mx_set(bx, by, False)

    def scene(self, g: Gfx, t: float, e: float, lit: float = 1.0, cover: float | None = None):
        i, tau = self.cur(e)
        c = int(e // self.CYCLE)
        k = e % self.CYCLE
        sky(g, self.sk, t, (56, 0, 128, 46), 18)
        m = (e % 41) / 1.3
        if m < 1:
            meteor(g, 100 + rand(int(e // 41), 3) * 24, 2, m, -28, 14)
        mountains(g)
        renew = c >= 1 and k < 5.0
        if renew:
            self.trails(g, k, t)
        self.mansion(g, i, tau, t, lit)
        if cover is not None:                 # 云（在台与人后面）
            self.cloud_cover(g, cover)
        terrace(g)
        spin = t * 0.6 + (k * 3 if renew else 0) + (span(tau, 6, 9) * 3 if 6 < tau < 9 else 0)
        armillary(g, spin, self.aim(tau, i))
        if renew:
            h = daoshi(g, DX, FLOOR, "raise", t, face="happy")
        else:
            self.actor(g, tau, t, i)
        self.ticks(g, i, t, renew)
        return i, tau, renew, c

    def trails(self, g: Gfx, k: float, t: float):
        """一周天：满天星绕北极（右上）划出一段弧形星轨"""
        px, py = 120, 4
        sweep = ease_in_out(span(k, 0.3, 3.5)) * 1.4
        for j in range(18):
            r = 8 + rand(j, 77) * 46
            a0 = rand(j, 78) * math.pi * 0.6 + math.pi * 0.45
            for s in range(int(sweep * r)):
                a = a0 + s / r
                x, y = px + math.cos(a) * r, py + math.sin(a) * r
                if x > 56 and y < 46 and s % 2 == 0:
                    g.px(x, y)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self._dt(t)
        sky(g, self.sk, t, (56, 0, 128, 46), 26, span(t, 0, 1.5))
        mountains(g)
        tau = lerp(0.0, 2.0, span(t, 2.5, 5.0))
        if t > 2.5:
            self.mansion(g, 0, tau, t)
        terrace(g)
        armillary(g, t * 0.6 + ease_out(span(t, 1.5, 3.0)) * 6, self.aim(0.0, 0))
        x = lerp(-12, DX, ease_out(span(t, 0, 2.0)))
        if t < 2.0:
            figure(g, x, FLOOR, t, legs="walk")
        else:
            daoshi(g, DX, FLOOR, "gongshou" if t < 3.0 else "idle", t)
        self.ticks(g, 0, t)
        if t > 3.0:
            self.caption(g, 0)
        self.mx(g, 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        self._dt(t)
        i, tau, renew, c = self.scene(g, t, e)
        if renew:
            label(g, 5, 4, f"{cn_num(c + 1)}周天" if c < 99 else f"{c + 1}周天")
        else:
            self.caption(g, i)
        self.mx(g, i, t)
        if renew:
            mx_ring(g, (t * 4) % 5)

    def cloud_cover(self, g: Gfx, x: float):
        for j, (dx, dy, w, h) in enumerate(((0, 2, 50, 18), (30, 18, 44, 16), (-10, 30, 40, 14))):
            pix.blit(g, cloud_sprite(w, h, 40 + j), x + dx, dy)

    def interrupt(self, g: Gfx, t: float, e: float):
        self._dt(t)
        x = lerp(-80, 58, ease_out(span(t, 0, 1.2)))
        i, tau, renew, c = self.scene(g, t, e, cover=x)
        if t > 0.6:
            label(g, 5, 4, "云掩")
        else:
            self.caption(g, i)
        self.mx(g, i, t)
        g.mx[:, : int(8 * span(t, 0, 1.2))] = False
        g.mx[0, :] = True

    def resume(self, g: Gfx, t: float, e: float):
        self._dt(t)
        x = lerp(58, 140, ease_in(span(t, 0.2, 1.4)))
        i, tau, renew, c = self.scene(g, t, e, cover=x)
        if t > 1.2:
            self.caption(g, i)
        self.mx(g, i, t)
        g.mx[:, int(8 * span(t, 0.2, 1.4)):] = False

    def complete(self, g: Gfx, t: float, e: float):
        self._dt(t)
        i, tau = self.cur(e)
        sky(g, self.sk, t, (56, 0, 128, 46), 18)
        mountains(g)
        q = int(span(t, 0.3, 3.5) * 4)                    # 四象依次闪现
        quad = min(q, 3)
        if t < 3.5:
            j = quad * 7 + int((t * 7) % 7)
            self.mansion(g, j, 3.0, t)
        else:
            self.trails(g, (t - 3.5) * 2, t)
        terrace(g)
        armillary(g, t * 0.6 + ease_in_out(span(t, 0, 3.5)) * 30, t * 2)
        pose = "raise" if t < 3.5 else ("bow" if t < 4.6 else "gongshou")
        daoshi(g, DX, FLOOR, pose, t, face="wow" if t < 3.5 else "happy")
        self.ticks(g, 27, t, all_flash=True)
        if 3.5 <= t < 3.57:
            pix.flash(g)
        if t < 3.5:
            label(g, 5, 4, SIXIANG[quad])
        if t > 3.6:
            y = pop_box(g, 64, 4, "斗转星移", t, 3.6)
            g.text(64, y, "斗转星移", align="center")
        if t < 3.5:
            self.mx(g, quad * 7 + int((t * 7) % 7), t)
        else:
            mx_ring(g, (t - 3.5) * 4 % 6)
            g.mx_level = 1 + int(5 * (1 - span(t, 3.5, 5)))
