"""扶乩（扶鸾）。

沙盘铺细沙，桃木乩笔呈 Y 形：两岔由正副鸾生扶着，中间一根笔尖在沙上书写。乩笔先自行颤动（乩动），再降笔书写。
本作：小道士扶住乩笔一岔，另一岔无人自起、灵光缭绕（仙真扶鸾）；乩笔先在沙上空画圈颤动，
“降笔”一圈光点一闪，然后在沙上自下而上划出六道沟（阴爻中间提笔），变爻旁补画 ○（老阳）或 ×（老阴），
沙粒四溅；写完提笔，沙上的卦就是揭晓的卦，右侧竖排乩示卦名。
变爻记法用六爻纳甲的通行记号：老阳“○”（重）、老阴“×”（交）。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, lerp, noise, span
from ..engine.chars import Part, daoshi, figure
from ..engine.gfx import Gfx
from ..engine.scene import register
from ..engine.symbols import yang
from .o_common import FLOOR, RHH, RHS, RHW, REVEAL, Base, floor, star4, yao

DAO_X = 16
TX0, TY0, TX1, TY1 = 38, 17, 98, 50      # 沙盘外框
LX, LY = 53, 21                            # 第一爻（上爻）左上：与揭晓版式一致
DOWN = 1.45                                # 降笔
W0 = 1.6                                   # 开始写
PER = 0.56
R0 = W0 + 6 * PER + 0.45


def LYi(i):
    return LY + (5 - i) * RHS


def _sand():
    """沙纹：不规则的细点（固定），只在沙盘里"""
    import random
    r = random.Random(5)
    p = Part(TX1 - TX0 - 8, TY1 - TY0 - 7)
    for _ in range(40):
        x, y = r.randrange(p.w), r.randrange(p.h)
        p.px(x, y, 1)
        if r.random() < 0.3:
            p.px(x + 1, y, 1)
    return p.sprite()


SPR = {}


def tray(g: Gfx):
    """沙盘（俯视略斜）：梯形木框（双线、四角包铜），细沙，前沿露出一条木板侧面，下面是架子"""
    if "sand" not in SPR:
        SPR["sand"] = _sand()
    I = 4  # 上沿内收
    outer = [(TX0 + I, TY0), (TX1 - I, TY0), (TX1, TY1), (TX0, TY1)]
    g.d.polygon(outer, fill=1)
    g.d.polygon([(TX0 + I + 2, TY0 + 2), (TX1 - I - 2, TY0 + 2), (TX1 - 2, TY1 - 2), (TX0 + 2, TY1 - 2)], fill=0)
    g.d.line((TX0 + I + 1, TY0 + 1, TX1 - I - 1, TY0 + 1), fill=0)
    g.blit(SPR["sand"], TX0 + 4, TY0 + 4)
    for x, y in ((TX0 + I, TY0), (TX1 - I - 1, TY0), (TX0, TY1 - 1), (TX1 - 1, TY1 - 1)):
        g.d.rectangle((x, y, x + 1, y + 1), fill=0)
        g.px(x + (1 if x < 64 else 0), y + (1 if y < 30 else 0))
    # 前沿侧面（木纹网点）
    g.d.rectangle((TX0, TY1 + 1, TX1, TY1 + 4), fill=1)
    pix.checker(g, (TX0 + 1, TY1 + 2, TX1, TY1 + 4), 0.5, 0)
    g.d.line((TX0, TY1 + 1, TX1, TY1 + 1), fill=1)
    # 架
    for x in (TX0 + 4, TX1 - 5):
        g.d.line((x, TY1 + 5, x, FLOOR - 1), fill=1, width=2)
    g.d.line((TX0 + 6, FLOOR - 4, TX1 - 7, FLOOR - 4), fill=1)
    pix.checker(g, (TX0 + 7, FLOOR - 3, TX1 - 7, FLOOR), 0.25)


def circle_mark(g: Gfx, x: int, y: int, p: float):
    """○：一个 5×5 的小圈（p 画到几分）"""
    pts = [(2, 0), (3, 0), (4, 1), (4, 2), (4, 3), (3, 4), (2, 4), (1, 4), (0, 3), (0, 2), (0, 1), (1, 0)]
    for k in range(int(len(pts) * p)):
        g.px(x + pts[k][0], y + pts[k][1])


def cross_mark(g: Gfx, x: int, y: int, p: float):
    for k in range(int(10 * p)):
        a = k % 5
        if k < 5:
            g.px(x + a, y + a)
        else:
            g.px(x + 4 - a, y + a)


@register
class FujiOmen(Base):
    id = "o.fuji"
    name = "扶乩"
    desc = "小道士扶起桃木乩笔，另一岔灵光自起；乩笔颤动降笔，在沙盘上自下而上划出六爻，沙粒四溅，乩示卦名"
    T = {"play": R0 + REVEAL}

    def init(self):
        self.mark = [9 if v == 9 else 6 if v == 6 else 0 for v in self.lines]

    def tip_at(self, t: float):
        """笔尖位置 (x, y, 落笔?)"""
        if t < 0.5:
            return 70, TY1 - 6, True       # 乩笔斜搁在沙盘上
        if t < DOWN:  # 乩动：悬空画圈，越转越急
            k = t - 0.5
            a = k * (6 + k * 10)
            r = 6 + noise(t * 3) * 4
            return 66 + math.cos(a) * r, 33 + math.sin(a) * r * 0.6 - 2, False
        if t < W0:
            q = span(t, DOWN, W0)
            return lerp(66, LX, q), lerp(31, LYi(0) + 1, q), False
        if t < W0 + 6 * PER:
            i = int((t - W0) / PER)
            k = (t - W0 - i * PER) / PER
            y = LYi(i) + 1
            if k < 0.62:  # 划沟（阴爻中间提笔）
                q = ease_in_out(k / 0.62)
                x = LX + q * (RHW - 1)
                down = yang(self.lines[i]) or not (0.4 < q < 0.6)
                return x, y, down
            if k < 0.8 and self.mark[i]:  # 补记 ○ ×
                q = (k - 0.62) / 0.18
                return LX + RHW + 3 + math.cos(q * 6.3) * 2, y + math.sin(q * 6.3) * 2, True
            q = span(k, 0.8 if self.mark[i] else 0.62, 1.0)  # 换行
            ny = LYi(i + 1) + 1 if i < 5 else LYi(5) - 6
            return lerp(LX + RHW, LX, q), lerp(y, ny, q), False
        q = ease_out(span(t, W0 + 6 * PER, R0))
        return lerp(LX, 80, q), lerp(LYi(5) - 6, 6, q), False

    def written(self, g: Gfx, t: float):
        for i in range(6):
            t0 = W0 + i * PER
            if t < t0:
                break
            k = min(1.0, (t - t0) / (PER * 0.62))
            if k <= 0:
                continue
            y = LYi(i)
            w = int(ease_in_out(k) * RHW)
            if yang(self.lines[i]):
                g.d.rectangle((LX, y, LX + w - 1, y + RHH - 1), fill=1)
            else:
                yao(g, LX, y, RHW, RHH, self.lines[i])
                g.d.rectangle((LX + w, y, LX + RHW, y + RHH - 1), fill=0)
            if self.mark[i] and t > t0 + PER * 0.62:
                p = span(t, t0 + PER * 0.62, t0 + PER * 0.8)
                (circle_mark if self.mark[i] == 9 else cross_mark)(g, LX + RHW + 2, y - 1, p)

    def rod(self, g: Gfx, hand, tip, t: float):
        """Y 形乩笔：从手里的一岔，经分叉处到笔头，笔尖下垂；另一岔向上翘，灵光缭绕"""
        hx, hy = hand
        tx, ty, down = tip
        lift = 0 if down else 3
        top = (tx, ty - 7 - lift)
        fork = (lerp(hx, top[0], 0.45), lerp(hy, top[1], 0.45) - 3)
        g.d.line((hx, hy, fork[0], fork[1]), fill=1, width=2)
        other = (fork[0] + 2, fork[1] - 12)
        g.d.line((fork[0], fork[1], other[0], other[1]), fill=1, width=2)
        g.d.line((fork[0], fork[1], top[0], top[1]), fill=1, width=2)
        g.d.line((top[0], top[1], tx, ty - lift), fill=1)
        g.d.rectangle((top[0] - 1, top[1] - 1, top[0] + 1, top[1] + 1), fill=1)
        ph = (t * 2) % 1
        star4(g, other[0] + math.cos(t * 7) * 3, other[1] - 2 + math.sin(t * 7) * 2, 1 + int(ph * 2))
        if int(t * 6) % 2:
            g.px(other[0] - 3, other[1] + 2)

    def play(self, g: Gfx, t: float):
        self.tick(t)
        floor(g, "tile")
        tray(g)
        self.written(g, min(t, R0))
        tip = self.tip_at(min(t, R0 - 0.001)) if t < R0 else None
        # 小道士
        if t < R0:
            if t < 0.45:
                daoshi(g, DAO_X, FLOOR, "bow" if 0.1 < t < 0.4 else "gongshou", t)
                g.d.line((DAO_X + 12, FLOOR - 4, 70, TY1 - 5), fill=1, width=2)  # 乩笔斜靠着
            else:
                trem = (noise(t * 20) - 0.5) * 2 if t < DOWN else 0
                h = figure(g, DAO_X, FLOOR, t, arm="offer", face="wow" if t < W0 else "normal",
                           dy=int(round(trem)))["hand"]
                self.rod(g, h, tip, t)
            if tip and tip[2] and W0 <= t < W0 + 6 * PER and int(t * 30) % 2 == 0:  # 沙粒四溅
                self.sparks.burst(tip[0], tip[1], 2, 14, up=10, life=0.3, gravity=60)
            if self.hit(t, DOWN):  # 降笔：光点一圈
                pix.flash(g)
                self.sparks.burst(66, 31, 18, 40, life=0.6, gravity=0)
            if DOWN < t < DOWN + 0.15:
                pix.shake(g, t, 1.5)
            for i in range(6):  # 每一笔落下：一点火星
                if self.hit(t, W0 + i * PER):
                    self.sparks.burst(LX, LYi(i) + 1, 5, 20, up=8, life=0.35, gravity=50)
                    pix.shake(g, t, 0.7)
            if t < DOWN and t > 0.5:  # 乩动时一圈光点跟着笔
                for j in range(4):
                    a = t * 9 + j * 1.57
                    g.px(tip[0] + math.cos(a) * 5, tip[1] - 9 + math.sin(a) * 3)
        else:
            k = t - R0
            daoshi(g, DAO_X, FLOOR, "bow" if 0.6 < k < 1.2 else "gongshou", t, face="happy")
        self.particles(g)
        # 点阵
        if t < R0:
            n = 0 if t < W0 else min(6, int((t - W0) / PER + 0.62))
            from ..engine.symbols import mx_hexagram
            mx_hexagram(g, self.lines, n)
            if tip:
                if t < DOWN:
                    a = t * 10
                    g.mx[int(3.5 + math.sin(a) * 3), int(3.5 + math.cos(a) * 3)] = True
                else:
                    g.mx[7, max(0, min(7, int((tip[0] - LX) / RHW * 8)))] = True
            g.mx_level = 6 if DOWN <= t < DOWN + 0.15 else 1
        else:
            self.reveal(g, t, R0, hx=LX, hy=LY, nx=110, ny=16, num=False, slam=False, vname=True, mark=False)
        self.flush(g)
