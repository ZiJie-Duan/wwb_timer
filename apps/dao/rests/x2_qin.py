"""抚琴：仲尼式七弦琴（项、腰两处内收，岳山、龙龈，十三徽），《列子·汤问》伯牙鼓琴，陶渊明无弦琴。

月下松边，小道士坐在琴桌后，琴横在面前（略俯视：七根弦从岳山往龙龈收拢，十三徽嵌在近身一侧）。
右手在岳山边勾挑，左手在徽位上按弦、吟猱（小幅揉动）或抬起弹散音；被弹的弦振成梭形，余音渐弱，
每一声飘起一个小音符。桌角一只小香炉一缕烟，琴穗轻摆，松针偶尔落下。
一句八声、句间停顿（11 秒一句）。每 40 秒一个典故，三种轮换：
  高山（背后升起群山，“峨峨兮若泰山”）/ 流水（水纹从琴下流过，“洋洋兮若江河”）/
  无弦（弦一根根隐去，手照弹不误，“但识琴中趣”“何劳弦上声”）。
入场：琴从左边滑上琴桌，七根弦一根根张上（每根一颤），小道士从琴后坐起，抬手。
退场：手收回，收圆。
点阵：七行 = 七弦，被弹的弦跳动；左右两列是琴的两头。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from .x2_common import NOTE, Clock, arm, crop_below, iris, label, shoulder_xy, win

QX, QY = 14, 41               # 琴面精灵左上角
QW = 68
YS = QX + 59                  # 岳山（弦的右端）
LY = QX + 3                   # 龙龈（弦的左端）
DX, DF = 63, 54               # 小道士（坐在琴后靠琴头一侧，面朝左看着左手；脚底被琴挡住）
TABLE_Y = QY + 19
PHRASE, NOTES = 11.0, 8
HUI = [1 / 8, 1 / 6, 1 / 5, 1 / 4, 1 / 3, 2 / 5, 1 / 2, 3 / 5, 2 / 3, 3 / 4, 4 / 5, 5 / 6, 7 / 8]
EVENT = 40.0
PLUCK_X = YS - 5


def sy(i: int, x: float) -> float:
    """第 i 根弦（0 = 离人最远的一弦，画在最下）在 x 处的 y：岳山端间距 2，龙龈端收拢"""
    a = (x - LY) / (YS - LY)
    j = 6 - i
    return lerp(QY + 4 + j * 1.5, QY + 3 + j * 2, a)


def hui_x(f: float) -> float:
    return YS - f * (YS - LY)


# ---------------------------------------------------------------- 道具

def _qin():
    """琴 68×19：琴面（项、腰内收）、岳山、龙龈、十三徽、侧板（网点）、焦尾"""
    p = Part(QW, 19)
    face = [(0, 3), (20, 2), (22, 3), (27, 3), (29, 1), (52, 1), (54, 2), (56, 2), (57, 0), (66, 0), (67, 1),
            (67, 16), (66, 17), (57, 17), (56, 16), (54, 16), (52, 17), (29, 17), (27, 16), (22, 16), (20, 17), (0, 16)]
    p.shape("polygon", face, fill=1)
    inner = [(x + (1 if x < 33 else -1), y + (1 if y < 9 else -1)) for x, y in face]
    p.d.polygon(inner, fill=0)
    p.d.rectangle((59, 1, 60, 16), fill=1)          # 岳山
    p.d.line((61, 2, 61, 15), fill=0)
    p.d.line((3, 4, 3, 14), fill=1)                  # 龙龈
    for f in HUI:                                    # 十三徽（嵌在近身一侧）
        x = round(59 - f * 56)
        p.px(x, 2)
    p.px(31, 2, 1), p.px(31, 1, 0)                   # 第七徽大一点
    p.d.line((63, 3, 63, 14), fill=1)                # 承露、额
    p.px(65, 8), p.px(65, 9)
    p.shape("rectangle", (1, 17, 66, 18), fill=1)    # 侧板
    p.dither((1, 17, 66, 18), 0.5, 0)
    p.d.line((0, 17, 1, 17), fill=1)
    p.shape("rectangle", (0, 15, 2, 18), fill=1)     # 焦尾
    p.px(1, 17, 0)
    return p.sprite()


def _censer():
    """桌角小香炉 9×7"""
    p = Part(9, 7)
    p.shape("rectangle", (0, 1, 8, 1), fill=1)
    p.px(0, 0), p.px(8, 0)
    p.shape("polygon", [(1, 2), (7, 2), (6, 5), (2, 5)], fill=1)
    p.d.line((2, 3, 6, 3), fill=0)
    p.dither((5, 2, 8, 5), 0.5, 0)
    p.shape("rectangle", (2, 6, 2, 6), fill=1)
    p.shape("rectangle", (6, 6, 6, 6), fill=1)
    return p.sprite()


def _pine():
    """右边一棵松：虬干 + 三簇扇形松针（团块，边缘锯齿）+ 树皮鳞纹"""
    p = Part(40, 52)
    p.shape("polygon", [(30, 51), (36, 51), (35, 40), (33, 30), (34, 20), (31, 12), (28, 14), (31, 21),
                        (29, 30), (31, 40)], fill=1)
    p.shape("line", (31, 20, 18, 14), fill=1, width=2)
    p.shape("line", (33, 30, 24, 28), fill=1, width=2)
    for y in range(16, 50, 4):
        p.px(32 + (y // 4) % 2, y, 0)
        p.px(33 - (y // 4) % 2, y + 2, 0)
    p.dither([(34, 12), (40, 12), (40, 51), (34, 51)], 0.5, 0)
    for cx, cy, r in ((14, 11, 9), (30, 7, 8), (23, 25, 7)):     # 松针团：平展的一片，上缘针尖、下面阴影
        p.shape("ellipse", (cx - r, cy - 3, cx + r, cy + 3), fill=1)
        for i in range(-r + 1, r, 2):
            p.px(cx + i, cy - 4 + (i // 2) % 2)
            p.px(cx + i + 1, cy + (1 if abs(i) < r - 2 else 0), 0)
        p.d.line((cx - r + 2, cy + 2, cx + r - 2, cy + 2), fill=0)
        p.dither((cx - r, cy + 3, cx + r, cy + 4), 0.5, 0)
        p.shape("line", (cx - r + 3, cy + 4, cx + r - 3, cy + 4), fill=1)
        p.dither((cx - r, cy + 4, cx + r, cy + 4), 0.5, 0)
    return p.sprite()


_P: dict = {}


def prop(name):
    if not _P:
        _P.update(qin=_qin(), censer=_censer(), pine=_pine())
    return _P[name]


MOUNT = [(0, 0), (8, -10), (13, -7), (20, -19), (25, -15), (31, -24), (37, -16), (43, -20), (50, -9), (56, -12),
         (64, 0)]


@register
class Qin(Rest):
    id = "x2.qin"
    name = "抚琴"
    desc = "月下松边，小道士坐在琴后抚七弦琴，右手勾挑、左手按徽吟猱，弦振音飘；不时高山、流水、无弦琴"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.ht = 0.0
        self.ev0 = self.rng.randrange(3)
        self.clock = Clock()
        self.notes: list[list[float]] = []   # 飘起的音符 x, y, age
        self.last_n = -1

    # ------------------------------------------------------------ 旋律（确定性）

    def note(self, n: int):
        """第 n 个音 → (时刻, 弦, 徽位 f 或 None = 散音)"""
        ph, j = divmod(n, NOTES)
        tt = ph * PHRASE + 0.6 + j * 1.05 + (rand(n, self.seed) - 0.5) * 0.35
        s = int(rand(n + 99, self.seed) * 7)
        f = None if rand(n + 7, self.seed) < 0.3 else HUI[4 + int(rand(n + 13, self.seed) * 6)]
        return tt, s, f

    def cur(self, t: float):
        """(上一个音, 下一个音)，各为 (n, 时刻, 弦, 徽)"""
        ph = int(t // PHRASE)
        prev = nxt = None
        for n in range(max(0, (ph - 1) * NOTES), (ph + 2) * NOTES):
            tt, s, f = self.note(n)
            if tt <= t:
                prev = (n, tt, s, f)
            else:
                nxt = (n, tt, s, f)
                break
        return prev, nxt

    # ------------------------------------------------------------ 画面

    def sky(self, g: Gfx, t: float):
        g.d.ellipse((80, 2, 90, 12), fill=1)                        # 月
        g.d.ellipse((83, 1, 92, 10), fill=0)
        for i, (x, y) in enumerate(((60, 5), (70, 14), (8, 20), (30, 24), (46, 17))):
            if (t * 0.7 + i * 0.31) % 3 > 0.25:
                g.px(x, y)
        g.d.line((0, 61, 127, 61), fill=1)
        pix.checker(g, (0, 62, 128, 64), 0.25)

    def mountains(self, g: Gfx, k: float):
        """高山：背后升起群山"""
        rise = ease_out(span(k, 0, 2.5)) * (1 - span(k, 11, 13))
        if rise <= 0:
            return
        base = 44
        pts = [(4 + x * 1.0, base + y * rise) for x, y in MOUNT]
        g.d.polygon(pts, fill=0, outline=1)
        for (x0, y0), (x1, y1) in zip(pts[1:-2:2], pts[2:-1:2]):
            g.d.line((x0, y0, x0 + 3, y0 + 8 * rise), fill=1)
        pts2 = [(70 + x * 0.7, base + y * rise * 0.8) for x, y in MOUNT]
        g.d.polygon(pts2, fill=0, outline=1)

    def water(self, g: Gfx, k: float, t: float):
        """流水：琴下水纹流过"""
        a = span(k, 0, 1.5) * (1 - span(k, 11, 13))
        if a <= 0:
            return
        for r, y in enumerate((30, 34, 38)):
            for x in range(0, 128, 1):
                ph = (x + t * (14 + r * 5)) * 0.32 + r
                if math.sin(ph * 0.5) > 1 - 2 * a and (x + r) % 2 == 0:
                    g.px(x, y + round(math.sin(ph) * 1.2))

    def strings(self, g: Gfx, t: float, prev, vis: float, slide: float = 0.0, n_strings: int = 7):
        amp = 0.0
        if prev:
            amp = 1.6 * math.exp(-(t - prev[1]) * 1.8)
        for i in range(n_strings):
            if vis < 1 and rand(i, 5) > vis:
                continue
            x0, x1 = LY + 1 + slide, YS - 1 + slide
            if prev and prev[2] == i and amp > 0.25:
                xp = hui_x(prev[3]) + slide if prev[3] else x0
                sign = 1 if int(t * 30) % 2 else -1
                for x in range(int(x0), int(x1) + 1):
                    off = 0
                    if x > xp:
                        off = amp * math.sin(math.pi * (x - xp) / (x1 - xp)) * sign
                    g.px(x, round(sy(i, x - slide) + off))
            else:
                g.d.line((x0, sy(i, x0 - slide), x1, sy(i, x1 - slide)), fill=1)

    def hands(self, g: Gfx, t: float, prev, nxt, lift: float = 0.0):
        """小道士面朝左：近身的左手按徽（往前伸），身后的右手在岳山边勾挑。
        → ((左手精灵, x, y), (右手精灵, x, y))，x, y 为精灵左上角"""
        sx, sy_ = shoulder_xy(DX, DF, "sit", flip=True)
        sy_ += 2                      # 肩放低一点，手臂不挡脸
        # 右手：在岳山边，跟着要弹的弦；弹的一瞬间勾一下
        tgt = nxt if nxt and (not prev or nxt[1] - t < 0.45) else prev
        ry = sy(tgt[2], PLUCK_X) if tgt else sy(3, PLUCK_X)
        if prev and t - prev[1] < 0.12:
            ry += -2 + (t - prev[1]) / 0.12 * 2
        elif nxt and nxt[1] - t < 0.45 and prev:
            q = ease_in_out(1 - (nxt[1] - t) / 0.45)
            ry = lerp(sy(prev[2], PLUCK_X), sy(nxt[2], PLUCK_X), q) - 1
        rx = PLUCK_X - (1 if prev and t - prev[1] < 0.12 else 0)
        # 左手：按在徽位上（吟猱：小幅揉），散音时抬起歇在第六徽上方
        if prev and prev[3] is None:
            lx, ly = hui_x(HUI[5]), sy(prev[2], hui_x(HUI[5])) - 4
        else:
            f = prev[3] if prev else HUI[6]
            lx = hui_x(f) + (round(math.sin(t * 18)) if prev and t - prev[1] < 0.8 else 0)
            ly = sy(prev[2] if prev else 3, lx)
        if nxt and prev and nxt[1] - t < 0.4 and nxt[3] is not None:
            q = ease_in_out(1 - (nxt[1] - t) / 0.4)
            lx = lerp(lx, hui_x(nxt[3]), q)
            ly = lerp(ly, sy(nxt[2], hui_x(nxt[3])), q)
        rx, ry = lerp(rx, sx + 4, lift), lerp(ry, sy_ + 13, lift)
        lx, ly = lerp(lx, sx - 5, lift), lerp(ly, sy_ + 13, lift)
        la = arm(lx - sx, ly - sy_, "open")
        ra = arm(rx - (sx + 1), ry - (sy_ - 1), "open")
        return (la, sx - la.sh[0], sy_ - la.sh[1]), (ra, sx + 1 - ra.sh[0], sy_ - 1 - ra.sh[1])

    def scene(self, g: Gfx, t: float, enter: float = 1.0, lift: float = 0.0):
        dt = self.clock.dt(t)
        on = enter >= 1
        e3 = enter * self.T["enter"]
        prev, nxt = self.cur(t) if on else (None, None)
        k, en = win(t, EVENT, 14.0, 20.0)
        kind = (en + self.ev0) % 3 if k is not None and on else -1
        self.sky(g, t)
        if kind == 0:
            self.mountains(g, k)
        elif kind == 1:
            self.water(g, k, t)
        pix.blit(g, prop("pine"), 90, 9)
        # 小道士（琴后）
        rise = ease_out_back(span(e3, 0.9, 1.5)) if not on else 1.0
        dfy = DF + (1 - rise) * 30
        (la, lax, lay), (ra, rax, ray) = self.hands(g, t, prev, nxt,
                                                    max(lift, 1 - span(e3, 2.0, 2.9)) if not on else lift)
        ray += dfy - DF
        lay += dfy - DF
        pix.blit(g, ra, rax, ray)
        face = "sleep" if (prev and t - prev[1] < 0.6 and kind != 2) or (kind == 2 and k > 3) else "normal"
        figure(g, DX, dfy, t, legs="sit", arm=None, face=face, head="up", flip=True)
        # 琴桌、琴
        slide = (1 - ease_out(span(e3, 0, 0.9))) * -90 if not on else 0.0
        g.d.rectangle((QX - 6, TABLE_Y, QX + QW + 26, TABLE_Y + 1), fill=1)
        g.d.line((QX - 5, TABLE_Y + 1, QX + QW + 25, TABLE_Y + 1), fill=0)
        for x in (QX - 4, QX + QW + 22):
            g.d.rectangle((x, TABLE_Y + 2, x + 1, 61), fill=1)
        pix.blit(g, prop("qin"), QX + slide, QY)
        # 琴穗（挂在琴头下，轻摆）
        sw = math.sin(t * 1.4) * 1.2
        hx = QX + QW - 3 + slide
        g.d.line((hx, QY + 18, hx + sw * 0.4, QY + 20), fill=1)
        g.d.rectangle((hx - 1 + sw * 0.5, TABLE_Y - 1, hx + 1 + sw * 0.5, TABLE_Y), fill=1)
        # 桌角香炉 + 一缕烟
        cx = QX + QW + 12
        pix.blit(g, prop("censer"), cx - 4, TABLE_Y - 7)
        from .x2_common import wisp
        wisp(g, cx, TABLE_Y - 9, 16, t, self.seed, amp=1.6, speed=5)
        # 弦（入场时一根根张上）
        if on:
            vis = 1.0
            if kind == 2:
                vis = 1 - span(k, 0.5, 3.0) + span(k, 11.5, 13.5)
            self.strings(g, t, prev, vis)
        else:
            nstr = int(span(e3, 1.0, 2.1) * 7.99)
            self.strings(g, e3, (0, 1.0 + (nstr - 1) * 0.157, nstr - 1, None) if nstr else None, 1.0, slide, nstr)
        # 手（身后右手露在琴面上的那截；左手在最前）
        cr = crop_below(ra, QY - ray)
        if cr is not None:
            pix.blit(g, cr, rax, ray + ra.h - cr.h)
        pix.blit(g, la, lax, lay)
        # 音符
        if prev and prev[0] != self.last_n:
            self.last_n = prev[0]
            if t - prev[1] < 0.3:
                self.notes.append([PLUCK_X + 4, sy(prev[2], PLUCK_X) - 8, 0.0, prev[0] % 2])
        keep = []
        for q in self.notes:
            q[2] += dt
            if q[2] < 3.0:
                keep.append(q)
                x = q[0] + math.sin(q[2] * 2.5 + q[3]) * 2 + q[2] * 3
                y = q[1] - q[2] * 9
                if q[2] < 2.2 or int(q[2] * 10) % 2:
                    pix.blit(g, NOTE[int(q[3])], x, y)
        self.notes = keep
        # 字
        if kind == 0 and 2.0 < k < 11.5:
            label(g, 4, 2, "峨峨兮若泰山")
        elif kind == 1 and 2.0 < k < 11.5:
            label(g, 4, 2, "洋洋兮若江河")
        elif kind == 2 and 3.5 < k < 12.5:
            label(g, 4, 2, "但识琴中趣" if k < 8 else "何劳弦上声")
        return prev, kind

    def mx(self, g: Gfx, t: float, prev, kind):
        """七行 = 七弦（细弦用隔点），左右两列是琴的两头；被弹的弦整行亮、上下跳"""
        g.mx[:7, 0] = True
        g.mx[:7, 7] = True
        g.mx[7, :] = True
        vis = 7
        if kind == 2:
            return
        for i in range(vis):
            r = 6 - i
            if prev and prev[2] == i and t - prev[1] < 1.0:
                rr = r + (1 if int(t * 14) % 2 and r < 6 else 0)
                g.mx[rr, 1:7] = True
            else:
                for c in range(1, 7):
                    g.mx[r, c] = (c + r) % 2 == 0

    def enter(self, g: Gfx, t: float):
        self.scene(g, t, min(t / self.T["enter"], 0.999))
        n = int(span(t, 1.0, 2.1) * 7.99)
        g.mx[:, 0] = g.mx[:, 7] = t > 0.9
        for i in range(n):
            g.mx[6 - i, 1:7] = True

    def hold(self, g: Gfx, t: float):
        self.ht = t
        prev, kind = self.scene(g, t)
        self.mx(g, t, prev, kind)

    def exit(self, g: Gfx, t: float):
        q = t / self.T["exit"]
        prev, kind = self.scene(g, self.ht + t, lift=span(q, 0, 0.5))
        self.mx(g, self.ht + t, prev, kind)
        iris(g, span(q, 0.25, 1.0), DX, 36)
