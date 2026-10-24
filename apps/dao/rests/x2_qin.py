"""抚琴：七弦古琴（仲尼式），十三徽，左按右弹。

入场：古琴从左边滑入，七根弦一根一根张上（每根“叮”一下，点阵对应一行亮起），两只宽袖的手从下方抬起。
持续：右手勾挑、左手在徽位上按弦并“吟猱”（小幅揉动）；被弹的弦振动成一道模糊的梭形，余音渐弱；
      每弹一声，一个音名（宫商角徵羽）从琴上飘起、慢慢散去。一句八声，句间停顿，琴穗轻摆。
      每 40 秒一个小典故，三种轮换：
        高山：背后升起群山，“峨峨兮若泰山”（《列子·汤问》伯牙鼓琴，志在高山）；
        流水：一道道水纹流过，“洋洋兮若江河”；
        无弦：弦一根根隐去，手照弹不误，“但识琴中趣，何劳弦上声”（《晋书·陶潜传》）。
退场：手收回，琴弦隐去，画面收拢。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x2_common import iris, win

HEAD_X, TAIL_X = 112, 12        # 岳山（琴头）、龙龈（琴尾）
TOP, BOT = 22, 48               # 琴面上下沿
NOTE_NAMES = "宫商角徵羽"
# 十三徽：弦长的 1/8 1/6 1/5 1/4 1/3 2/5 1/2 3/5 2/3 3/4 4/5 5/6 7/8（从岳山量起）
HUI = [1 / 8, 1 / 6, 1 / 5, 1 / 4, 1 / 3, 2 / 5, 1 / 2, 3 / 5, 2 / 3, 3 / 4, 4 / 5, 5 / 6, 7 / 8]
PHRASE = 11.0                    # 一句的长度（秒）
NOTES = 8
EVENT = 40.0

FINGER = Sprite("""
  .##.
  #..#
  #..#.##.
 .#..#..#
.##..#..##
#..#.#..#.#
#.........#
#.........#
.#.......#
 .#.....#.
  .#####.
""")

FINGER_L = FINGER.flip()


def string_y(i: int, x: float) -> float:
    """第 i 弦（0 = 一弦，离演奏者最远）在 x 处的 y：琴头处弦距宽，琴尾收拢（透视）"""
    k = (x - TAIL_X) / (HEAD_X - TAIL_X)
    return lerp(29 + i * 2.0, 26 + i * 3.0, k)


def hui_x(f: float) -> float:
    return HEAD_X - (HEAD_X - TAIL_X) * f


def qin_body(g: Gfx, dx: float = 0.0):
    """琴身：仲尼式，项、腰两处内收；侧板抖动阴影；岳山、龙龈、十三徽、琴穗"""
    d = g.d
    top = [(4, TOP + 2), (10, TOP), (36, TOP), (39, TOP + 2), (46, TOP + 2), (49, TOP), (104, TOP), (107, TOP + 2),
           (110, TOP + 2), (113, TOP), (122, TOP), (125, TOP + 3)]
    bot = [(125, BOT - 2), (122, BOT), (113, BOT), (110, BOT - 2), (107, BOT - 2), (104, BOT), (49, BOT),
           (46, BOT - 2), (39, BOT - 2), (36, BOT), (10, BOT), (4, BOT - 2)]
    pts = [(x + dx, y) for x, y in top + bot]
    d.polygon(pts, fill=0, outline=1)
    side = [(x + dx, y + 3) for x, y in bot[::-1]] + [(x + dx, y) for x, y in bot]
    g.shade_poly(side, 0.3)
    d.line((HEAD_X + dx, TOP + 2, HEAD_X + dx, BOT - 2), fill=1, width=2)      # 岳山
    d.line((TAIL_X + dx, TOP + 3, TAIL_X + dx, BOT - 3), fill=1)               # 龙龈
    for f in HUI:                                                               # 徽：靠演奏者一侧
        x = hui_x(f) + dx
        d.point((x, BOT - 2))
        if f in (1 / 2,):
            d.rectangle((x - 1, BOT - 3, x, BOT - 2), fill=1)


def tassel(g: Gfx, t: float, dx: float = 0.0):
    """琴头垂下的琴穗，轻轻摆动"""
    sw = math.sin(t * 1.3) * 1.5
    x0 = 118 + dx
    g.d.line((x0, BOT + 3, x0 + sw * 0.5, BOT + 7), fill=1)
    g.d.rectangle((x0 - 1 + sw * 0.5, BOT + 7, x0 + 1 + sw * 0.5, BOT + 8), fill=1)
    for j in range(-1, 2):
        g.d.line((x0 + sw * 0.5 + j, BOT + 9, x0 + sw + j * 1.5, 63), fill=1)


@register
class Qin(Rest):
    id = "x2.qin"
    name = "抚琴"
    desc = "七弦古琴，左按右弹，弦振余音，音名飘起；不时高山、流水、无弦琴"
    T = {"enter": 3.2, "exit": 1.3}

    def setup(self):
        self.ht = 0.0
        self.ev0 = self.rng.randrange(3)

    # ------------------------------------------------------------ 旋律（确定性）

    def note(self, n: int):
        """第 n 个音 → (时刻, 弦, 徽位 f 或 None = 散音)"""
        ph, j = divmod(n, NOTES)
        base = ph * PHRASE
        tt = base + 0.6 + j * 1.05 + (rand(n, self.seed) - 0.5) * 0.4
        s = int(rand(n + 99, self.seed) * 7)
        f = None if rand(n + 7, self.seed) < 0.3 else HUI[3 + int(rand(n + 13, self.seed) * 8)]
        return tt, s, f

    def recent(self, t: float, back: int = 3):
        """最近弹过的几个音：[(n, 时刻, 弦, 徽)]（时刻 ≤ t）"""
        ph = int(t // PHRASE)
        out = []
        for n in range(max(0, (ph - 1) * NOTES), (ph + 1) * NOTES):
            tt, s, f = self.note(n)
            if tt <= t:
                out.append((n, tt, s, f))
        return out[-back:]

    def next_note(self, t: float):
        ph = int(t // PHRASE)
        for n in range(ph * NOTES, (ph + 2) * NOTES):
            tt, s, f = self.note(n)
            if tt > t:
                return n, tt, s, f
        return None

    # ------------------------------------------------------------ 画面

    def strings(self, g: Gfx, t: float, vis: float = 1.0, dx: float = 0.0):
        """七弦：被弹的弦振成梭形，余音渐弱。vis < 1 时弦一根根隐去（无弦琴）"""
        amp = [0.0] * 7
        for n, tt, s, f in self.recent(t, 4):
            a = 1.4 * math.exp(-(t - tt) * 1.4)
            amp[s] = max(amp[s], a)
        for i in range(7):
            if vis < 1 and rand(i, 5) > vis:
                continue
            x0, x1 = TAIL_X + 1 + dx, HEAD_X - 1 + dx
            a = amp[i]
            if a < 0.5:
                g.d.line((x0, string_y(i, x0 - dx), x1, string_y(i, x1 - dx)), fill=1)
            else:  # 振动：上下两道包络
                up, lo = [], []
                for k in range(13):
                    x = lerp(x0, x1, k / 12)
                    e = math.sin(math.pi * k / 12) * a * (0.7 + 0.3 * math.sin(t * 40 + k))
                    y = string_y(i, x - dx)
                    up.append((x, y - e))
                    lo.append((x, y + e))
                g.d.line(up, fill=1)
                g.d.line(lo, fill=1)
        return amp

    def hands(self, g: Gfx, t: float, lift: float = 0.0):
        """右手在岳山附近勾挑，左手在徽位上按弦、吟猱。lift 0..1：手抬离（入场/退场）"""
        rec = self.recent(t, 1)
        nxt = self.next_note(t)
        # 右手：在下一音的弦上方等待，弹的瞬间往里一勾
        if rec and nxt:
            _, t0, s0, f0 = rec[-1]
            _, t1, s1, f1 = nxt
            p = ease_in_out(span(t, t0 + 0.15, t1 - 0.15))
            ry = lerp(string_y(s0, 100), string_y(s1, 100), p)
            pluck = math.exp(-(t - t0) * 9)
            lx_from = hui_x(f0) if f0 else 34
            lx_to = hui_x(f1) if f1 else 34
            lx = lerp(lx_from, lx_to, ease_in_out(span(t, t1 - 0.5, t1 - 0.1)))
            press = (f0 is not None) and p < 0.8
            ly = string_y(s0 if p < 0.5 else s1, lx) - (0 if press else 3)
            if press:  # 吟：按弦的指头小幅揉动
                lx += math.sin(t * 9) * 1.2 * math.exp(-(t - t0) * 0.8)
        else:
            ry, pluck, lx, ly = string_y(3, 100), 0.0, 60, string_y(3, 60) - 3
        rx = 100 - pluck * 3
        ry += lift * 30 - pluck * 2
        ly += lift * 30
        self.hand(g, rx, ry, right=True)
        self.hand(g, lx, ly, right=False)

    def hand(self, g: Gfx, x: float, y: float, right: bool):
        """宽袖从画面下方伸来，指尖在 (x, y)"""
        s = 1 if right else -1
        cx, cy = x + s * 2, y + 9
        sleeve = [(cx - 7, cy), (cx + 7, cy), (cx + s * 18 + 13, 66), (cx + s * 18 - 13, 66)]
        g.d.polygon(sleeve, fill=0)
        g.shade_poly(sleeve, 0.25)
        g.d.line((cx - 7, cy + 1, cx + 7, cy + 1), fill=1)
        g.d.line((cx - 7, cy + 3, cx + 7 + s * 2, cy + 3), fill=1)
        spr = FINGER if right else FINGER_L
        g.blit(spr, x - (3 if right else spr.w - 4), y - 1)

    def notes_up(self, g: Gfx, t: float):
        """每弹一声，一个音名从琴上飘起散去"""
        for n, tt, s, f in self.recent(t, 3):
            k = (t - tt) / 3.0
            if k >= 1:
                continue
            x = (hui_x(f) if f else 70) + 6 + math.sin(k * 5 + n) * 3
            y = TOP - 4 - k * 22
            ch = NOTE_NAMES[(s + (n % 2)) % 5]
            g.text(x, y - 7, ch, size=8)
            if k > 0.6:  # 渐散
                g.fade(1 - (k - 0.6) / 0.4 * 0.8, (int(x) - 1, int(y) - 8, int(x) + 10, int(y) + 1))

    def event(self, g: Gfx, t: float, layer: str):
        """每 40 秒一个典故。layer="bg" 画背景（山、水）并返回弦的可见度；"fg" 画字并返回是否有字"""
        k, n = win(t, EVENT, 13.0, offset=18.0)
        if k is None:
            return 1.0 if layer == "bg" else False
        kind = (n + self.ev0) % 3
        fade = span(k, 0, 2.0) * (1 - span(k, 11.0, 13.0))
        if layer == "fg":
            if kind == 2:
                if k <= 1.5:
                    return False
                line, kk = ("但识琴中趣", k - 1.5) if k < 7.0 else ("何劳弦上声", k - 7.0)
            else:
                if k <= 2.0 or k > 12.0:
                    return False
                line, kk = ("峨峨兮若泰山" if kind == 0 else "洋洋兮若江河"), k - 2.0
            w = len(line) * 12
            g.d.rectangle((64 - w / 2 - 2, 0, 64 + w / 2 + 1, 13), fill=0)
            typewriter(g, 64, 1, line, kk, cps=3, align="center")
            return True
        if kind == 0:  # 高山：背后升起群山
            rise = ease_out(fade)
            hs = [0, 9, 5, 13, 7, 11, 4, 12, 6, 0]
            xs = [0, 12, 22, 36, 50, 62, 76, 92, 108, 127]
            peaks = [(x, TOP - h * rise) for x, h in zip(xs, hs)]
            g.shade_poly(peaks + [(127, TOP), (0, TOP)], 0.2, outline=None)
            g.d.line(peaks, fill=1)
            return 1.0
        if kind == 1:  # 流水：一道道水纹流过
            for j in range(2):
                y = 14 + j * 4
                cut = fade * 140
                pts = [(x, y + math.sin(x * 0.15 + t * 3 + j * 2) * 1.5) for x in range(0, 128, 4) if x < cut]
                if len(pts) > 1:
                    g.d.line(pts, fill=1)
            return 1.0
        return 1 - fade  # 无弦琴：弦一根根隐去

    def frame(self, g: Gfx, t: float, lift: float = 0.0, vis: float = 1.0):
        v = self.event(g, t, "bg") * vis
        qin_body(g)
        tassel(g, t)
        amp = self.strings(g, t, v)
        if not self.event(g, t, "fg"):
            self.notes_up(g, t)
        self.hands(g, t, lift)
        self.mx(g, t, amp, v)

    def mx(self, g: Gfx, t: float, amp, vis: float = 1.0):
        """点阵：七行 = 七弦；振动的弦点点跳动"""
        for i in range(7):
            if vis < 1 and rand(i, 5) > vis:
                continue
            r = i + 1
            for x in range(8):
                on = True
                if amp[i] > 0.5:
                    on = (x + int(t * 20)) % 2 == 0 or amp[i] < 0.9 and x % 3
                g.mx[r, x] = on
        g.mx[1:8, 0] = True   # 龙龈、岳山：弦全隐去时也留着琴的两头
        g.mx[1:8, 7] = True
        rec = self.recent(t, 1)
        if rec and t - rec[-1][1] < 0.15:
            g.mx_level = 3

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dx = (1 - ease_out(span(t, 0.0, 1.0))) * -140
        qin_body(g, dx)
        tassel(g, t, dx)
        n = int(clamp((t - 1.0) / 0.18, 0, 7))
        for i in range(n):  # 弦一根根张上
            x0, x1 = TAIL_X + 1, HEAD_X - 1
            tt = 1.0 + (i + 1) * 0.18
            a = 2.0 * math.exp(-(t - tt) * 4)
            if a > 0.5:
                g.d.line((x0, string_y(i, x0) - a, x1, string_y(i, x1) - a), fill=1)
                g.d.line((x0, string_y(i, x0) + a, x1, string_y(i, x1) + a), fill=1)
            else:
                g.d.line((x0, string_y(i, x0), x1, string_y(i, x1)), fill=1)
            g.mx[i + 1, :] = True
        if t > 2.3:
            self.hands(g, 0.0, lift=1 - ease_out(span(t, 2.3, 3.2)))
        if n and t - (1.0 + n * 0.18) < 0.08:
            g.mx_level = 3

    def hold(self, g: Gfx, t: float):
        self.ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        T = self.T["exit"]
        self.frame(g, self.ht + t, lift=ease_in(span(t, 0, 0.6)), vis=1 - span(t, 0.3, 0.9))
        iris(g, span(t, 0.5, T), 64, 38)
