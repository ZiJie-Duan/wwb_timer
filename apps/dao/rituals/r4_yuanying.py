"""结丹出神：小道士盘坐莲台，身后圆光一圈圈亮起，光从下丹田升到中丹田、再到上丹田；功成时元婴自顶门而出。

依据：内丹三关“炼精化气、炼气化神、炼神还虚”；三丹田（下丹田脐下、中丹田膻中绛宫、上丹田眉间入内泥丸）；
“五气朝元、三花聚顶”；功成出神，阳神（元婴）自顶门而出（《性命圭旨》婴儿现形、出离苦海诸图）；《道德经》“归根曰静”。
入场：静夜，莲台升起，小道士盘坐其上，身后圆光一圈亮起，下丹田点亮。
持续：一转 10 分钟分三关各 200 秒：光从下丹田升到中丹田、再到上丹田，中线有点点上行的光；身后圆光由一圈增到三圈、
      缓缓转；每过一关头顶开一朵五瓣花（闪光、火星）；右上角写当前一关。小事件：一团五行之气从远处飘来没入身中 /
      圆光一阵脉动。续（6 秒）：三花分开，元婴坐着小莲台从顶门升起，周围闪光，片刻沉回，花谢重来，
      “出神”，左上“第几转”加一。
中断：光一关关退回下丹田、变暗，花淡去，“归根”。  恢复：下丹田重新亮起，光再升到刚才那一关，花重新开。
圆满：五团气从五个方向汇入中丹田（“五气朝元”），三朵花在头顶依次开放，中间那朵托着元婴升起放光（“三花聚顶”）。
点阵：自下而上三团光代表三丹田，当前一关闪烁；出神时变成元婴图标。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import P, Clock, cached, counter, dao, label, mx_art, mx_ring, orb, pop_title, ring, star

FLOOR = 58
SY = FLOOR - 5          # 坐在莲台上
DX = 58
STAGE = 200.0
STAGES = ["炼精化气", "炼气化神", "炼神还虚"]
SIT = P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"), face="sleep")
SIT_HAPPY = P(legs="sit", b=(110, 30, "palm"), f=(70, 150, "palm"), face="happy")
HALO_C = (DX, SY - 20)
FLOWER_Y = SY - 45

def _flower(open_k):
    """五瓣花 9×9：五片圆瓣、花心一点暗、花蕊三点"""
    p = Part(9, 9)
    for j in range(5):
        a = -math.pi / 2 + j * 2 * math.pi / 5
        r = 2.4 * open_k + 0.6
        cx, cy = 4 + math.cos(a) * r, 4 + math.sin(a) * r
        p.shape("ellipse", (cx - 1.6, cy - 1.6, cx + 1.6, cy + 1.6), fill=1)
    p.shape("ellipse", (3, 3, 5, 5), fill=1)
    p.px(4, 4, 0)
    if open_k > 0.9:
        for j in range(5):
            a = -math.pi / 2 + j * 2 * math.pi / 5 + math.pi / 5
            p.px(round(4 + math.cos(a) * 2), round(4 + math.sin(a) * 2), 0)
    return p.sprite()


FLOWER = [_flower(1.0), _flower(0.8)]

BABY = pix.frames("""
    ##
   ####
  #.##.#
  ######
   #..#
   ####
 ##.##.##
  ######
 #.#.#.#.#
##########
 ########
""")


def _seat():
    """莲台 34×8：两层莲瓣、台面"""
    p = Part(34, 9)
    p.shape("rectangle", (4, 0, 29, 1), fill=1)
    for i, x in enumerate(range(1, 33, 5)):            # 上层莲瓣
        p.shape("polygon", [(x, 2), (x + 2, 5), (x + 5, 2)], fill=1)
        p.shape("polygon", [(x, 2), (x + 5, 2), (x + 4, 6), (x + 1, 6)], fill=1)
        p.px(x + 2, 4, 0)
    for x in range(3, 31, 5):                          # 下层莲瓣
        p.shape("ellipse", (x, 5, x + 5, 8), fill=1)
        p.px(x + 2, 7, 0)
    p.d.line((4, 1, 29, 1), fill=0)
    return p.sprite()


def dantian(h: dict):
    """三丹田（屏幕坐标）：下（脐下）、中（膻中）、上（印堂）"""
    bx, by = h["belly"]
    return [(bx + 3, by - 1), (bx + 3, by - 9), (h["brow"][0] - 2, h["brow"][1] - 5)]


def halo(g: Gfx, t: float, n: int, pulse: float = 0.0):
    cx, cy = HALO_C
    for i in range(n):
        r = 16 + i * 5 + pulse * 2
        m = int(r * 2.2)
        for j in range(m):
            if (j + i) % 2 == 0:
                a = j / m * 2 * math.pi + t * (0.15 if i % 2 else -0.12)
                g.px(cx + math.cos(a) * r, cy + math.sin(a) * r)


def night(g: Gfx, t: float):
    """夜空：星点、地面、两边香烛的微光"""
    import random
    r = random.Random(11)
    for i in range(16):
        x, y = r.randrange(0, 128), r.randrange(0, 40)
        if abs(x - DX) > 32 and (t * (0.4 + r.random()) + r.random()) % 1 < 0.75:
            g.px(x, y)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    for x in (14, 110):  # 两盏莲花灯
        g.d.rectangle((x - 3, FLOOR - 4, x + 3, FLOOR - 1), fill=1)
        g.d.line((x - 2, FLOOR - 3, x + 2, FLOOR - 3), fill=0)
        g.d.line((x, FLOOR - 5, x, FLOOR - 5), fill=1)
        fl = int(t * 6 + x) % 3
        g.px(x, FLOOR - 7 - (fl == 0)), g.px(x, FLOOR - 6)
        if fl == 1:
            g.px(x - 1, FLOOR - 6)


@register
class Yuanying(Ritual):
    id = "r4.yuanying"
    name = "结丹出神"
    desc = "小道士盘坐莲台，光从下丹田升到中、上丹田，身后圆光增到三圈、头顶三花开放，功成元婴自顶门升起"
    T = {"enter": 5.0, "interrupt": 1.8, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sparks = pix.Sparks(self.seed + 1)
        self.clock = Clock()

    def stage(self, k: float):
        i = min(int(k // STAGE), 2)
        return i, (k - i * STAGE) / STAGE

    def figure(self, g: Gfx, t: float, pose=None):
        pix.blit(g, cached(("yy", "seat"), _seat), DX - 17, FLOOR - 8)
        return dao(g, DX, SY, pose or SIT, t)

    def channel(self, g: Gfx, t: float, h: dict, level: float, bright: float = 1.0):
        """中线上行的光点 + 三丹田（level：0–3，光升到哪）"""
        pts = dantian(h)
        top = pts[min(int(level), 2)]
        y0 = pts[0][1]
        y1 = lerp(pts[min(int(level), 2)][1], pts[min(int(level) + 1, 2)][1], level - int(level)) if level < 3 else pts[2][1]
        x = pts[0][0]
        for j in range(4):  # 上行的光点
            q = (t * 0.8 + j * 0.25) % 1
            y = lerp(y0, y1, q)
            if y1 < y0 - 1 and bright > 0.3:
                g.px(x + (1 if j % 2 else 0), y)
        for i, (px, py) in enumerate(pts):
            lit = level >= i
            if not lit:
                g.d.polygon([(px, py - 2), (px + 2, py), (px, py + 2), (px - 2, py)], outline=1, fill=0)
                continue
            cur = int(min(level, 2.999)) == i
            if bright > 0:
                big = cur and (t * 2) % 1 < 0.5
                g.px(px, py), g.px(px - 1, py), g.px(px + 1, py), g.px(px, py - 1), g.px(px, py + 1)
                if big:
                    g.px(px - 2, py), g.px(px + 2, py), g.px(px, py - 2), g.px(px, py + 2)
                r = 1
                if cur and bright >= 1:
                    for a in range(4):
                        if (int(t * 6) + a) % 2:
                            aa = a * math.pi / 2 + math.pi / 4
                            g.px(px + math.cos(aa) * (r + 2), py + math.sin(aa) * (r + 2))

    def flowers(self, g: Gfx, t: float, n: int, spread: float = 0.0, k_new: float = 1.0):
        """头顶的花（n 朵：中、左、右）"""
        xs = [DX + 1, DX - 7 - spread * 6, DX + 9 + spread * 6]
        for i in range(n):
            fr = FLOWER[0] if (t * 2 + i * 0.3) % 1 < 0.7 else FLOWER[1]
            y = FLOWER_Y - (2 if i == 0 else 0) - spread * 4
            if i == n - 1 and k_new < 1:
                s = pix.stretch(fr, max(0.2, ease_out_back(k_new)), max(0.2, ease_out_back(k_new)))
                pix.blit(g, s, xs[i] - s.w // 2, y + 4 - s.h // 2)
            else:
                pix.blit(g, fr, xs[i] - 4, y)

    def mx(self, g: Gfx, t: float, level: float, baby: bool = False):
        if baby:
            mx_art(g, """
...##...
..####..
..#..#..
...##...
.######.
#.####.#
.######.
#.#..#.#
""")
            return
        cur = int(min(level, 2.999))
        for i, row in enumerate((6, 3, 0)):
            if level >= i:
                on = i != cur or (t * 2) % 1 < 0.6
                if on:
                    g.mx[row:row + 2, 3:5] = True
                    if i == cur:
                        g.mx[row, 2] = g.mx[row, 5] = g.mx[row + 1, 2] = g.mx[row + 1, 5] = (t * 4) % 1 < 0.5
            else:
                g.mx[row, 3] = g.mx[row + 1, 4] = (t * 0.5) % 1 < 0.1

    def labels(self, g: Gfx, e: float, i: int):
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}转" if n < 100 else f"{n}转")
        label(g, 125, 2, STAGES[i], 12, "right", box=False, pad=1)

    def qi_event(self, g: Gfx, t: float, e: float, h: dict):
        """小事件：一团五行之气从远处飘来没入身中 / 圆光脉动"""
        slot, ph = int(e // 23), (e % 23) / 4.0
        if ph >= 1:
            return 0.0
        if slot % 2 == 0:
            a = (slot * 1.3) % (2 * math.pi)
            tx, ty = dantian(h)[1]
            x, y = lerp(DX + math.cos(a) * 70, tx, ease_in(ph)), lerp(30 + math.sin(a) * 30, ty, ease_in(ph))
            orb(g, x, y, 1, t)
            if ph > 0.95:
                star(g, tx, ty, 2)
            return 0.0
        return math.sin(ph * math.pi)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        night(g, t)
        k = ease_out(span(t, 0.0, 1.6))
        pix.blit(g, cached(("yy", "seat"), _seat), DX - 17, FLOOR - 8 + (1 - k) * 12)
        if t > 1.2:
            h = dao(g, DX, SY, SIT, t)
            if t > 2.0:
                halo(g, t, 1, 0)
            if t > 3.0:
                self.channel(g, t, h, 0.0, span(t, 3.0, 3.6))
            if abs(t - 3.0) < dt:
                self.sparks.burst(*dantian(h)[0], 10, 16, life=0.5, gravity=0)
        if abs(t - 1.2) < dt:
            self.sparks.burst(DX, SY - 18, 14, 22, life=0.6, gravity=0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, 0.0)
        if t > 3.4:
            self.labels(g, 0, 0)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        night(g, t)
        if e >= self.CYCLE and k < 6.0:  # 续：元婴出神
            halo(g, t, 3, math.sin(k * 3))
            h = self.figure(g, t, SIT_HAPPY if 1.0 < k < 5.0 else SIT)
            self.channel(g, t, h, 2.0)
            spread = ease_out(span(k, 0.0, 1.0)) * (1 - span(k, 4.5, 5.5))
            self.flowers(g, t, 3 if k < 5.0 else 0, spread)
            up = ease_out(span(k, 0.8, 2.2)) * (1 - ease_in(span(k, 3.8, 5.0)))
            if up > 0.02:
                bx, by = DX + 1, lerp(FLOWER_Y + 4, 6, up)
                g.d.line((DX + 1, by + 10, DX + 1, FLOWER_Y + 4), fill=1)
                pix.blit(g, BABY[0], bx - 5, by - 4)
                if int(t * 6) % 2:
                    star(g, bx - 9, by, 1), star(g, bx + 9, by + 3, 1)
            if abs(k - 2.2) < dt:
                pix.flash(g)
                self.sparks.burst(DX + 1, 10, 20, 30, life=0.9, gravity=10)
            if 2.2 < k < 2.5:
                pix.shake(g, t, 1.0)
            self.sparks.step(dt)
            self.sparks.draw(g)
            self.mx(g, t, 2.0, baby=1.0 < k < 5.0)
            n = int(e // self.CYCLE) + 1
            counter(g, f"第{cn_num(n)}转" if n < 100 else f"{n}转")
            if 1.0 < k < 5.0:
                counter(g, "出神" if k < 3.8 else "收神", right=True)
            return
        i, q = self.stage(k)
        h_tmp = None
        pulse = 0.0
        halo_n = i + 1
        # 过关：花开 + 闪
        h = None
        halo(g, t, halo_n, 0)
        h = self.figure(g, t)
        pulse = self.qi_event(g, t, e, h)
        if pulse:
            halo(g, t + 0.5, halo_n, pulse)
        level = i + ease_in_out(min(q * 1.25, 1.0))   # 每关前 80% 时间光往上升
        self.channel(g, t, h, min(level, 2.0) if i == 2 else level)
        fk = span(k - i * STAGE, 0.0, 0.6) if i > 0 else 1.0
        self.flowers(g, t, i, 0.0, fk)
        if i > 0 and abs((k - i * STAGE) - 0.05) < dt:
            pix.flash(g)
            self.sparks.burst(*dantian(h)[i], 18, 26, life=0.8, gravity=10)
        if 0 < k - i * STAGE < 0.3 and i > 0:
            pix.shake(g, t, 1.0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, level)
        self.labels(g, e, i)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        night(g, t)
        i, q = self.stage(k)
        level = i + ease_in_out(min(q * 1.25, 1.0))
        back = ease_in_out(span(t, 0.0, 1.2))
        lv = lerp(min(level, 2.0), 0.0, back)
        halo(g, t, max(1, int(round(lerp(i + 1, 1, back)))))
        h = self.figure(g, t)
        self.channel(g, t, h, lv, 1 - span(t, 1.2, 1.8) * 0.8)
        if back < 0.5:
            self.flowers(g, t, i)
        self.mx(g, t, lv)
        n = int(e // self.CYCLE) + 1
        counter(g, f"第{cn_num(n)}转" if n < 100 else f"{n}转")
        if t > 0.5:
            counter(g, "归根", right=True)
        else:
            label(g, 125, 2, STAGES[i], 12, "right", box=False, pad=1)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        night(g, t)
        i, q = self.stage(k)
        level = i + ease_in_out(min(q * 1.25, 1.0))
        up = ease_in_out(span(t, 0.4, 1.8))
        lv = lerp(0.0, min(level, 2.0), up)
        halo(g, t, max(1, int(round(lerp(1, i + 1, up)))))
        h = self.figure(g, t)
        self.channel(g, t, h, lv, span(t, 0.0, 0.4))
        if abs(t - 0.4) < dt:
            self.sparks.burst(*dantian(h)[0], 10, 16, life=0.5, gravity=0)
        self.flowers(g, t, i if up > 0.6 else 0)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, lv)
        self.labels(g, e, i)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        night(g, t)
        halo(g, t, 3, max(0.0, math.sin(t * 4)) if t > 3.0 else 0)
        h = self.figure(g, t, SIT_HAPPY if t > 4.0 else SIT)
        mid = dantian(h)[1]
        self.channel(g, t, h, 2.0)
        if t < 2.0:  # 五气朝元：五团气从五个方向汇入中丹田
            q = ease_in(span(t, 0.2, 1.8))
            for j in range(5):
                a = -math.pi / 2 + j * 2 * math.pi / 5
                sx, sy = mid[0] + math.cos(a) * 60, mid[1] + math.sin(a) * 40
                orb(g, lerp(sx, mid[0], q), lerp(sy, mid[1], q), 1, t + j)
        if abs(t - 1.8) < dt:
            self.sparks.burst(mid[0], mid[1], 16, 24, life=0.6, gravity=0)
        if 1.8 < t < 2.0:
            pix.shake(g, t, 1.0)
        n_fl = 0 if t < 2.2 else (1 if t < 2.6 else (2 if t < 3.0 else 3))
        self.flowers(g, t, n_fl, 0.3 if t > 3.0 else 0.0, span(t, 2.2 + 0.4 * (n_fl - 1), 2.6 + 0.4 * (n_fl - 1)))
        if t > 3.2:  # 中间那朵托着元婴升起放光
            up = ease_out(span(t, 3.2, 4.4))
            bx, by = DX + 1, lerp(FLOWER_Y + 2, 8, up)
            for j in range(10):
                a = j * math.pi / 5 + t
                r1 = 10 + (j % 2) * 3
                pix.dotted(g, bx + math.cos(a) * 7, by + math.sin(a) * 7, bx + math.cos(a) * r1, by + math.sin(a) * r1,
                           2, int(t * 10))
            pix.blit(g, BABY[0], bx - 5, by - 4)
        if abs(t - 4.4) < dt:
            pix.flash(g)
            self.sparks.burst(DX + 1, 8, 24, 36, life=1.0, gravity=10)
        if 4.4 < t < 4.7:
            pix.shake(g, t, 1.2)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.mx(g, t, 2.0, baby=t > 3.2)
        if t > 4.4:
            g.mx_level = 1 + int(6 * (1 - span(t, 4.4, 5.6)))
        n = int(e // self.CYCLE)
        counter(g, f"第{cn_num(max(n, 1))}转" if n < 100 else f"{n}转")
        if 0.4 < t < 2.4:
            label(g, 125, 2, "五气朝元", 12, "right", box=False, pad=1)
        elif t >= 4.4:
            pop_title(g, 102, 3, "三花聚顶", span(t, 4.4, 4.8), t)
