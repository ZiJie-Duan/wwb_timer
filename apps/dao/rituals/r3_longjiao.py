"""吹龙角：山崖上，小道士双手捧起弯弯的牛角号鼓腮一吹，角声一圈圈荡上天；
天兵驾着小云一名名从天而降，在右边三排云头上列阵。

龙角（牛角号）是闾山、正一等派常用的法器，开坛召营时吹角，以号令兵马、通达三界。

入场：小道士走上山崖，捧起龙角，深吸一口气（身子一缩），鼓腮吹响第一声，角声的弧线从号口荡上天，三排云头浮现。
持续：每 10 秒吹一声：举角 → 吸气 → 鼓腮长吹（角身微颤、声弧一道道荡出、已列阵的天兵跟着一颠）→ 放下喘口气。
      一轮 540 秒，每 30 秒有一名天兵驾小云从天而降（弹跳落定、闪光），先站满前排再站后排，共 18 名。
      续：满阵天兵连云带人往上开拔出画（写“开拔”），再一名一名重新降下。
中断：号角放低，写“歇角”。  恢复：号角举回，再吹一声。
圆满：一声长角，余下的天兵一齐降下，举枪，全阵开拔升天，题“兵马齐至”。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part, daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r3_kit import FLOOR, Clock, art, banner, banner_text, crossed, label, mx_ring, pose_arm, put, sparkle

DX = 24
CYCLE = 540.0
EACH = 30.0
BLOW = 10.0
RENEW = 5.0
ROWS = [52, 37, 22]                       # 三排云头的顶面 y（前排在下）
COLS = [68 + j * 10 for j in range(6)]


def _horn() -> Sprite:
    """牛角号：沿一条弯弧（先往前、再往上）由细到粗的干净轮廓；两道金箍；号口朝上（口沿一道暗线）"""
    p = Part(24, 20)
    P0, P1, P2 = (1, 16), (16, 18), (19, 3)
    cen, rad = [], []
    for i in range(31):
        s = i / 30
        cen.append(((1 - s) ** 2 * P0[0] + 2 * (1 - s) * s * P1[0] + s * s * P2[0],
                    (1 - s) ** 2 * P0[1] + 2 * (1 - s) * s * P1[1] + s * s * P2[1]))
        rad.append(0.8 + 3.2 * s ** 1.3)
    left, right = [], []
    for i, (x, y) in enumerate(cen):
        a = cen[min(i + 1, 30)]
        b = cen[max(i - 1, 0)]
        tx, ty = a[0] - b[0], a[1] - b[1]
        n = math.hypot(tx, ty) or 1
        nx, ny = -ty / n, tx / n
        left.append((x + nx * rad[i], y + ny * rad[i]))
        right.append((x - nx * rad[i], y - ny * rad[i]))
    p.shape("polygon", left + right[::-1], fill=1)
    for i in (12, 19, 21):   # 金箍
        x, y = cen[i]
        a, b = cen[i + 1], cen[i - 1]
        tx, ty = a[0] - b[0], a[1] - b[1]
        n = math.hypot(tx, ty) or 1
        nx, ny = -ty / n, tx / n
        r = rad[i] - 0.5
        p.d.line((x + nx * r, y + ny * r, x - nx * r, y - ny * r), fill=0)
    x, y = cen[-1]
    r = rad[-1]
    p.d.line((x - r + 1, y + 1, x + r - 1, y + 1), fill=0)     # 号口
    p.shape("line", (x - r, y, x + r, y), fill=1)
    p.shape("rectangle", (0, 15, 1, 17), fill=1)               # 吹口
    for i in ():                                                 # （不加暗点）
        cx, cy = cen[i]
        lx, ly = right[i]
        p.px(int(round((cx + 2 * lx) / 3)), int(round((cy + 2 * ly) / 3)), 0)
    s = Sprite(on=np.array(p.on, bool), mask=np.array(p.mk, bool))
    s.anchor = (0, 16)
    s.pts = {"bell": (int(round(x)), int(round(y)) - 2), "mid": (12, 16)}
    return s


HORN = _horn()

SOLDIER = [art("""
   #   #
   #  ###
  ###  #
 ##### #
 #.#.# #
  ###  #
#######
#.###.##
 #####  #
 ## ##  #
 ## ##  #
""", anchor=(3, 10)), art("""
   #  ###
   #   #
  ###  #
 ##### #
 #.#.# #
  ### ##
######
#.####
 #####
 ## ##
 ## ##
""", anchor=(3, 10))]

CLOUD = art("""
 .##..##.
##########
.#.####.#.
 ........
""", anchor=(5, 0))

ROW_CLOUD = art("""
   .##.      .##.      .##.      .##.      .##.      .##.
 .######.  .######.  .######.  .######.  .######.  .######.
############################################################
#.###.####.###.####.###.####.###.####.###.####.###.####.###.
 ..........................................................
""", anchor=(0, 0))

MX_HORN = """
......#.
......##
.....##.
....##..
#..##...
####....
"""


def slot(i: int):
    r, c = divmod(i, 6)
    return COLS[c] + (2 if r == 1 else 0), ROWS[r]


@register
class LongjiaoRitual(Ritual):
    id = "r3.longjiao"
    name = "吹龙角"
    desc = "小道士在山崖上鼓腮吹龙角，角声荡上天；天兵驾小云一名名降下，在右边三排云头上列阵"
    T = {"enter": 6.0, "interrupt": 1.5, "resume": 1.8, "complete": 6.0}
    CYCLE = CYCLE

    def setup(self):
        self.sparks = pix.Sparks(self.seed)
        self.clock = Clock()
        self.arcs: list[list] = []      # [x, y, age]

    # ------------------------------------------------------------ 公用

    def ground(self, g: Gfx, t: float):
        """山崖：崖顶平台、崖壁斜下、几簇草；远处一道山脊"""
        g.d.polygon([(0, FLOOR), (46, FLOOR), (49, FLOOR + 2), (48, 61), (52, 63), (0, 63)], fill=0, outline=1)
        for a, b in (((8, FLOOR + 2), (14, 63)), ((26, FLOOR + 3), (22, 63)), ((40, FLOOR + 2), (44, 63))):
            g.d.line((a, b), fill=1)                 # 石缝
        pix.checker(g, (30, FLOOR + 3, 46, 64), 0.125)
        for x in (6, 18, 38):
            g.px(x, FLOOR - 1), g.px(x + 2, FLOOR - 1), g.px(x + 1, FLOOR - 2)
        ridge = [(54, 63), (62, 58), (72, 61), (86, 56), (100, 60), (114, 55), (128, 59)]
        for a, b in zip(ridge, ridge[1:]):
            g.d.line((a, b), fill=1)

    def rows(self, g: Gfx, t: float, show: float = 1.0, lift: float = 0.0, bump: float = 0.0):
        for r, y in enumerate(ROWS):
            if show * 3 > r:
                bob = int(round(math.sin(t * 1.1 + r) * 0.7))
                put(g, ROW_CLOUD, 62 + (2 if r == 1 else 0), y + 1 + bob - lift * (70 + r * 4))

    def soldiers(self, g: Gfx, n: int, t: float, lift: float = 0.0, bump: float = 0.0, new: int = -1,
                 newk: float = 1.0, raise_spear: bool = False):
        for i in range(n):
            x, y = slot(i)
            r = i // 6
            bob = int(round(math.sin(t * 1.1 + r) * 0.7))
            yy = y + bob - lift * (70 + r * 4) - int(round(bump * math.sin(i * 1.3 + t * 20) ** 2 * 2))
            if i == new:   # 驾小云从天而降，弹跳落定
                q = ease_out_bounce(newk)
                yy = lerp(-14, y, q)
                if newk < 1:
                    put(g, CLOUD, x, yy + 1)
            fr = SOLDIER[1 if raise_spear or (i == new and 0.6 < newk < 1) else 0]
            put(g, fr, x, yy)

    def blower(self, g: Gfx, t: float, phase: str, face: str = "normal", jitter: bool = False):
        """小道士 + 龙角。phase：rest 放在胸前 / lift 举到嘴边 / blow 鼓腮吹"""
        out = {}
        if phase == "rest":
            def prop(g2, h):
                out.update(put(g2, HORN, h[0] - 6, h[1] + 4))
            pose_arm(g, DX, "low", t, "fist", face=face, prop=prop)
            return out
        dy = 1 if phase == "lift" else 0
        j = (int(t * 30) % 2) if jitter else 0

        def prop(g2, h):
            mx, my = DX + 6, FLOOR - 19 + dy
            out.update(put(g2, HORN, mx + j, my))
            if phase == "blow":   # 鼓起的腮帮子
                g2.d.ellipse((DX + 3, FLOOR - 22 + dy, DX + 7, FLOOR - 17 + dy), fill=1, outline=0)
                g2.px(DX + 5, FLOOR - 20 + dy, 0)
        pose_arm(g, DX, "fwd", t, "fist", face=face, prop=prop, dy=dy)
        return out

    def emit(self, x, y):
        self.arcs.append([x, y, 0.0])

    def fx(self, g: Gfx, dt: float):
        keep = []
        for a in self.arcs:
            a[2] += dt
            if a[2] < 1.2:
                r = 3 + a[2] * 34
                box = (a[0] - r, a[1] - r, a[0] + r, a[1] + r)
                if a[2] > 0.8:
                    for d in range(-80, 1, 12):
                        g.px(a[0] + math.cos(math.radians(d)) * r, a[1] + math.sin(math.radians(d)) * r)
                else:
                    g.d.arc(box, -85, -5, fill=1)
                keep.append(a)
        self.arcs = keep
        self.sparks.step(dt)
        self.sparks.draw(g)

    def blow_cycle(self, g: Gfx, u: float, t: float, dt: float, face_rest="normal"):
        """一声（u = 本声已过秒数）：举角 0–0.6、吸气 0.6–1.0、长吹 1.0–4.0、放下"""
        if u < 0.6:
            return self.blower(g, t, "lift")
        if u < 1.0:
            return self.blower(g, t, "lift", face="sleep")
        if u < 4.0:
            pts = self.blower(g, t, "blow", jitter=True)
            if int((u - 1.0) * 3.2) != int((u - 1.0 - dt) * 3.2) or crossed(u, dt, 1.0):
                bx, by = pts["bell"]
                self.emit(bx, by)
                if crossed(u, dt, 1.0):
                    self.sparks.burst(bx, by, 8, 24, up=14, life=0.5, gravity=30)
            return pts
        return self.blower(g, t, "rest", face=face_rest)

    def mx(self, g: Gfx, n: int, blowing: bool, t: float):
        for i in range(n):
            r, c = divmod(i, 6)
            g.mx[7 - r * 2 - 1, 2 + c] = True
        if blowing:
            for x in range(8):
                g.mx[0, x] = (x + int(t * 10)) % 4 == 0
        g.mx[7, 0] = g.mx[6, 0] = g.mx[6, 1] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        self.ground(g, t)
        self.rows(g, t, show=span(t, 3.0, 4.8))
        if t < 2.0:
            x = lerp(-14, DX, ease_out(span(t, 0, 2.0)))
            h = daoshi(g, x, FLOOR, "walk", t)["hand"]
            put(g, HORN, h[0] - 6, h[1] + 2)
        else:
            self.blow_cycle(g, t - 2.0, t, dt)
        self.fx(g, dt)
        label(g, 3, 3, "龙角")
        self.mx(g, 0, 3.0 < t < 6.0, t)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        n, k, _ = round_of_k(e)
        if e >= CYCLE and k < RENEW:
            self.renew(g, k, t, e, dt)
            return
        cnt = count_at(k)
        new, newk = -1, 1.0
        since = k - (5 + EACH * (cnt - 1)) if cnt else 99
        if since < 1.6:
            new, newk = cnt - 1, span(since, 0, 1.2)
        u = e % BLOW
        blowing = 1.0 < u < 4.0
        self.ground(g, t)
        self.rows(g, t)
        self.soldiers(g, cnt, e, bump=1.0 if blowing else 0.0, new=new, newk=newk)
        if new >= 0 and crossed(since, dt, 1.2):
            x, y = slot(new)
            self.sparks.burst(x, y - 6, 10, 20, life=0.5)
        if new >= 0 and 1.2 <= since < 1.4:
            x, y = slot(new)
            sparkle(g, x + 4, y - 12, 3)
        self.blow_cycle(g, u, e, dt)
        self.fx(g, dt)
        label(g, 3, 3, f"天兵{cn_num(cnt)}名" if cnt else "龙角")
        self.mx(g, cnt, blowing, t)

    def renew(self, g: Gfx, k: float, t: float, e: float, dt: float):
        """满阵开拔：连云带人往上飞出画外"""
        lift = ease_in(span(k, 0.6, 3.0))
        self.ground(g, t)
        self.rows(g, t, lift=lift)
        self.soldiers(g, 18 if k < 3.0 else 0, e, lift=lift, raise_spear=True)
        if k < 3.0 and int(k * 15) % 2 == 0:
            self.sparks.burst(rand(int(k * 15), 2) * 60 + 64, 60 - lift * 40, 1, 10, life=0.5, gravity=-20)
        self.blower(g, t, "rest", face="happy")
        self.fx(g, dt)
        label(g, 3, 3, "开拔" if k < 3.4 else "龙角")
        self.mx(g, 18 if k < 3.0 else 0, False, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % CYCLE
        cnt = count_at(k)
        self.ground(g, t)
        self.rows(g, t)
        self.soldiers(g, cnt, e)
        self.blower(g, t, "rest" if t > 0.4 else "lift")
        self.fx(g, dt)
        label(g, 3, 3, "歇角" if t > 0.4 else f"天兵{cn_num(cnt)}名")
        self.mx(g, cnt, False, t)

    def resume(self, g: Gfx, t: float, e: float):
        """号角举回，“呜”地一声；最后一帧接上持续阶段同一时刻的动作"""
        dt = self.clock(t)
        k = e % CYCLE
        cnt = count_at(k)
        self.ground(g, t)
        self.rows(g, t)
        u = (e % BLOW) - self.T["resume"] + t
        self.soldiers(g, cnt, e, bump=1.0 if 0.5 < t < 1.2 or 1.0 < u < 4.0 else 0.0)
        if t < 0.5:
            self.blower(g, t, "lift")
        elif u < 0 or u >= 4.0:
            pts = self.blower(g, t, "blow" if t < 1.2 else "rest", jitter=t < 1.2)
            if crossed(t, dt, 0.5) or crossed(t, dt, 0.85):
                self.emit(*pts["bell"])
        else:
            self.blow_cycle(g, u, e, dt)
        self.fx(g, dt)
        label(g, 3, 3, f"天兵{cn_num(cnt)}名" if cnt else "龙角")
        self.mx(g, cnt, 0.5 < t < 1.2, t)

    def complete(self, g: Gfx, t: float, e: float):
        """一声长角 → 余下天兵一齐降下 → 举枪 → 全阵开拔升天 → 兵马齐至"""
        dt = self.clock(t)
        k = e % CYCLE
        cnt0 = count_at(k)
        self.ground(g, t)
        lift = ease_in(span(t, 3.4, 5.2))
        self.rows(g, t, lift=lift)
        down = span(t, 1.0, 2.2)
        for i in range(18):
            if i < cnt0 or down >= 1:
                continue
        n = cnt0 if down <= 0 else 18
        if 0 < down < 1:
            self.soldiers(g, cnt0, t, bump=1.0)
            for i in range(cnt0, 18):
                x, y = slot(i)
                q = ease_out_bounce(span(down, (i - cnt0) * 0.02, 1.0))
                yy = lerp(-14, y, q)
                put(g, CLOUD, x, yy + 1)
                put(g, SOLDIER[0], x, yy)
        else:
            self.soldiers(g, n, t, lift=lift, raise_spear=t > 2.4)
        if crossed(t, dt, 2.2):
            self.sparks.burst(94, 36, 30, 50, life=0.8, gravity=30)
        if 2.2 <= t < 2.28:
            pix.flash(g)
        if 2.2 <= t < 2.5:
            pix.shake(g, t, 1.5)
        if t < 3.4:
            self.blow_cycle(g, 1.0 + t, t, dt)
        else:
            self.blower(g, t, "rest", face="happy")
        self.fx(g, dt)
        if t > 3.0:
            banner(g, 36, 6, "兵马齐至", span(t, 3.0, 3.4))
            banner_text(g, 36, 6, "兵马齐至", span(t, 3.0, 3.4))
        else:
            label(g, 3, 3, f"天兵{cn_num(n)}名" if n else "龙角")
        self.mx(g, n if lift < 0.5 else 0, t < 3.4, t)
        if t > 2.2:
            mx_ring(g, (t - 2.2) * 4)
            g.mx_level = 1 + int(5 * (1 - span(t, 2.2, 3.6)))


def count_at(k: float) -> int:
    """本轮第 k 秒已到几名天兵（第 i 名在 5 + 30i 秒降下）"""
    return max(0, min(18, int((k - 5) // EACH) + 1)) if k >= 5 else 0


def round_of_k(e: float):
    n = int(e // CYCLE)
    return n + 1, e - n * CYCLE, (e - n * CYCLE) / CYCLE
