"""龟卜（灼龟观兆）。

商周龟卜：龟腹甲背面施钻凿，以荆木（楚焞）灼钻处，正面爆出“卜”形兆纹（兆干 + 兆枝），“卜”字即象其形。
爻的判法是本作约定：兆枝一道直出为阳，枝分两岔为阴，再生碎纹为变；底层用三钱法概率。

画面：龟腹甲（千里路中缝、盾纹、背光网点）从右滑入立在木架上，六个钻凿；小道士点燃荆木，
举着燃烧的荆条依次去灼：钻窝烧红闪烁、青烟直冒，“啪”的一声白圈炸开、屏幕一震、火星四溅，
裂出卜形兆纹，左上弹出“少阳”等，卦牌长出一爻。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import changing, mx_hexagram, yang
from .o_common import FLOOR, REVEAL, YAO_NAME, Base, arm, floor, tally

DAO_X = 20
MX = 86                # 千里路（中缝）
T0 = 0.85
D = 0.7
BURN = 0.38            # 每个钻窝：移过去 → 灼 → 啪
R0 = T0 + 6 * D + 0.15
PITS = [(MX - 9, 45), (MX + 9, 45), (MX - 9, 32), (MX + 9, 32), (MX - 9, 19), (MX + 9, 19)]

FLAME = pix.frames("""
 #
 ##
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
##.
 #
""")


def _shell():
    """龟腹甲 45×53（暗底亮线）：前叶（上）圆、两侧甲桥外凸、后叶（下）收窄带缺口；双线甲缘、千里路、盾纹；
    右侧背光稀网点"""
    p = Part(45, 53)
    c = 22
    pts = [(c - 9, 0), (c + 9, 0), (c + 14, 4), (c + 16, 12), (c + 22, 18), (c + 22, 32), (c + 16, 38),
           (c + 15, 46), (c + 10, 52), (c + 2, 52), (c, 49), (c - 2, 52), (c - 10, 52), (c - 15, 46), (c - 16, 38),
           (c - 22, 32), (c - 22, 18), (c - 16, 12), (c - 14, 4)]
    p.shape("polygon", pts, fill=0)
    p.d.polygon(pts, outline=1)
    inner = [(x + (2 if x < c else -2 if x > c else 0), y + (2 if y < 26 else -2)) for x, y in pts]
    p.d.polygon(inner, outline=1)
    p.d.line((c, 2, c, 49), fill=1)                       # 千里路
    for y, bow in ((8, 1), (16, -1), (28, 1), (39, -1), (46, 1)):  # 盾纹（横缝，微弯）
        p.d.line((c - 14, y + bow, c - 1, y), fill=1)
        p.d.line((c + 1, y, c + 14, y + bow), fill=1)
    for y in range(14, 40, 2):  # 右侧甲桥背光：一窄条网点
        for x in (c + 18 - (y // 2) % 2, c + 16 - (y // 2) % 2):
            if 18 <= y <= 32 or x < c + 15:
                p.px(x, y, 1)
    return p.sprite()


def _stand():
    """木架 33×9：横梁两头翘、两条腿"""
    p = Part(35, 10)
    p.shape("rectangle", (2, 0, 32, 2), fill=1)
    p.px(0, 0), p.px(1, 0), p.px(33, 0), p.px(34, 0)
    p.d.line((3, 1, 31, 1), fill=0)
    for x in (6, 27):
        p.shape("rectangle", (x, 3, x + 1, 9), fill=1)
    p.shape("rectangle", (4, 9, 30, 9), fill=1)
    return p.sprite()


SPR = {}


def spr(name):
    if not SPR:
        SPR.update(shell=_shell(), stand=_stand())
    return SPR[name]


@register
class GuijiaOmen(Base):
    id = "o.guijia"
    name = "龟卜"
    desc = "龟腹甲立在木架上，小道士举燃烧的荆条灼钻窝；烧红冒烟，啪地炸裂出卜形兆纹，六兆成卦"
    T = {"play": R0 + REVEAL}

    def init(self):
        self.side = [1 if x > MX else -1 for x, _ in PITS]

    def crack(self, g: Gfx, i: int, p: float, dx: float = 0):
        """卜形兆纹：兆干（竖）+ 兆枝（向外：阳一道直出，阴分两岔，变爻再生碎纹）"""
        x, y = PITS[i]
        x += dx
        s = self.side[i]
        v = self.lines[i]
        q = ease_out(p)
        g.d.line((x, y - 1 - 5 * q, x, y + 1 + 3 * q), fill=1)          # 兆干（亮裂纹）
        L = 9 * span(p, 0.3, 1.0)
        if L <= 0:
            return
        if yang(v):
            g.d.line((x, y - 2, x + s * L, y - 2 - L * 0.35), fill=1)
        else:
            g.d.line((x, y - 2, x + s * L * 0.55, y - 2 - L * 0.2), fill=1)
            g.d.line((x + s * L * 0.55, y - 2 - L * 0.2, x + s * L, y - 2 - L * 0.55), fill=1)
            g.d.line((x + s * L * 0.55, y - 2 - L * 0.2, x + s * L, y - 1 + L * 0.1), fill=1)
        if changing(v) and p > 0.8:
            g.d.line((x, y + 2, x - s * 3, y + 4), fill=1)
            g.d.line((x + s * 3, y - 3, x + s * 4, y - 6), fill=1)

    def pit(self, g: Gfx, i: int, state: str, t: float, dx: float = 0):
        """钻凿：椭圆钻窝（亮圈）+ 旁边的凿口；burn = 烧红闪烁"""
        x, y = PITS[i]
        x += dx
        g.d.ellipse((x - 2, y - 3, x + 2, y + 3), fill=0, outline=1)
        if state == "burn":
            if int(t * 16) % 2 == 0:
                g.d.ellipse((x - 2, y - 3, x + 2, y + 3), fill=1)
            else:
                g.d.line((x, y - 1, x, y + 1), fill=1)
        g.d.line((x + self.side[i] * 4, y - 1, x + self.side[i] * 4, y + 1), fill=1)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        floor(g, "earth")
        slide = (1 - ease_out(span(t, 0, 0.55))) * 60
        cur = int((t - T0) // D) if t >= T0 else -1
        u = (t - T0) - cur * D if cur >= 0 else 0
        cur = min(cur, 6)
        if t < R0:
            pix.blit(g, spr("stand"), MX - 17 + slide, FLOOR - 10)
            pix.blit(g, spr("shell"), MX - 22 + slide, FLOOR - 63 + 6)
            for i in range(6):
                cracked = i < cur or (i == cur and u >= BURN)
                burning = i == cur and 0.12 <= u < BURN
                self.pit(g, i, "burn" if burning else "pit", t, slide)
                if cracked:
                    p = 1.0 if i < cur else span(u, BURN, BURN + 0.16)
                    self.crack(g, i, p, slide)
        # ---------------- 小道士 + 荆条
        if t >= R0:
            k = t - R0
            daoshi(g, DAO_X, FLOOR, "bow" if 0.5 < k < 1.1 else "gongshou", t, face="happy")
        elif t < T0:  # 点火：举起荆条，火苗窜起
            h = daoshi(g, DAO_X, FLOOR, "raise", t, face="wow" if t > 0.5 else "normal")["hand"]
            tx, ty = h[0] + 4, h[1] - 6
            g.d.line((h[0], h[1] + 2, tx, ty), fill=1, width=2)
            if t > 0.45:
                fl = pix.stretch(pix.anim(FLAME, t, 12), 1, 1 + span(t, 0.45, 0.6))
                pix.blit(g, fl, tx - 1, ty - fl.h, outline=False)
                if self.hit(t, 0.45):
                    self.sparks.burst(tx, ty - 3, 10, 25, up=10, life=0.4, gravity=40)
        else:
            i = min(cur, 5)
            a, at = arm("reach") if PITS[i][1] > 35 else arm("toss") if PITS[i][1] < 25 else ("offer", None)
            if at is None:
                h = figure(g, DAO_X, FLOOR, t, arm="offer", face="normal")["hand"]
            else:
                h = figure(g, DAO_X, FLOOR, t, arm=a, arm_at=at, face="wow" if u > BURN else "normal")["hand"]
            px, py = PITS[i]
            q = ease_in_out(span(u, 0, 0.12)) if cur < 6 else 1
            prev = PITS[i - 1] if i > 0 else (h[0] + 20, h[1] - 10)
            tx = lerp(prev[0], px, q) - 3 * (1 if u < BURN else 0) - (4 if u >= BURN else 0)
            ty = lerp(prev[1], py, q) + (2 if u >= BURN else 0)
            if cur >= 6:
                tx, ty = px - 8, py + 4
            g.d.line((h[0], h[1], tx, ty), fill=1, width=2)
            fl = pix.anim(FLAME, t, 12)
            pix.blit(g, fl, tx - 1, ty - fl.h)
            if 0.12 <= u < BURN and cur < 6:  # 灼：青烟直冒
                if int(t * 12) != int((t - self.dt) * 12):
                    self.puffs.emit(px, py - 4, vy=-12, life=0.8, rmax=1.6, spread=1)
        # ---------------- 啪
        for i in range(6):
            tb = T0 + i * D + BURN
            if self.hit(t, tb):
                x, y = PITS[i]
                self.sparks.burst(x, y, 12, 35, up=6, life=0.5, gravity=60)
                pix.shake(g, t, 2.0)
            if tb < t < tb + 0.1:
                pix.shake(g, t, 1.2)
            if tb <= t < tb + 0.2:  # 一圈白光
                x, y = PITS[i]
                r = 3 + span(t, tb, tb + 0.2) * 9
                for j in range(10):
                    a = j / 10 * 2 * math.pi
                    g.px(x + math.cos(a) * r, y + math.sin(a) * r)
        self.particles(g, wind=2)
        # ---------------- 标签、卦牌、点阵
        done = 0
        for i in range(6):
            tb = T0 + i * D + BURN
            if t >= tb + 0.12:
                done = i + 1
            if tb + 0.12 <= t < min(tb + 0.12 + D, R0):
                self.pop(40, 6, YAO_NAME[self.lines[i]], t - tb - 0.12)
        if t < R0:
            gl = (t - (T0 + (done - 1) * D + BURN + 0.12)) / 0.3 if done else -1
            tally(g, self.lines, done, glint=gl)
            mx_hexagram(g, self.lines, done)
            if 0 <= cur < 6 and BURN <= u < BURN + 0.2:  # 爆裂瞬间：点阵显示“卜”
                g.mx[:] = False
                g.mx[:, 3] = True
                s = 1 if self.side[cur] > 0 else -1
                if yang(self.lines[cur]):
                    for k in range(1, 4):
                        g.mx[3 - k // 2, 3 + s * k] = True
                else:
                    for k in range(1, 4):
                        g.mx[3 - k, 3 + s * k] = True
                        g.mx[3 + k // 2, 3 + s * k] = True
                g.mx_level = 6
            elif 0 <= cur < 6 and 0.12 <= u < BURN:
                g.mx[7, int(t * 20) % 8] = True
        else:
            self.reveal(g, t, R0)
        self.flush(g)
