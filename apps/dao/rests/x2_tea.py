"""煮茶：陆羽《茶经·五之煮》的三沸，卢仝《七碗茶歌》。

入场：风炉从下方升起，铁鍑落在炉上一弹，炉门里“噗”地起火，茶碗与瓢从右边滑进来。
持续：一碗一轮（40 秒）：一沸鱼目 → 二沸连珠：一只宽袖的手伸来，“出水一瓢”，再拿竹筴“环激汤心”、投茶末
      → 三沸腾波鼓浪 → 把舀出的那瓢水倒回去止沸、“育其华”（水面浮起沫饽）→ 舀一瓢斟进茶碗，手收回
      → 碗上茶烟袅袅，左侧竖写本碗的那句诗。七碗一循环；第七碗“唯觉两腋习习清风生”：一阵清风横穿画面。
退场：画面收拢成一个圆。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.fx import flame, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Rest, register
from ..engine.symbols import draw_trigram
from .x2_common import iris, sleeve_hand, steam

CX, RIM = 52, 25          # 鍑的口沿中心
RX, RY = 19, 4
BOWL = (104, 52)          # 茶碗口沿中心
CYC = 40.0
HANDLE = 20               # 瓢柄长
BOWL_LINES = ["一碗喉吻润", "两碗破孤闷", "三碗搜枯肠", "四碗发轻汗", "五碗肌骨清", "六碗通仙灵", "七碗吃不得"]
STAGE = ["一沸", "二沸", "三沸"]
OFF = (150.0, -30.0)       # 手在画外

# 瓢的姿势：(瓢心 x, y, 柄方向)；柄端就是手握的地方
REST = (74, 57, -1.05)
DIP = (CX - 4, RIM, -0.75)
OVER_POT = (CX + 8, RIM - 9, -0.35)
OVER_BOWL = (BOWL[0] - 8, 40, -0.55)


def stove(g: Gfx, dy: float = 0.0, fire: float = 1.0, t: float = 0.0, seed: int = 0):
    """陆羽风炉：鼎形三足，炉门里看得见火；炉身铸巽（风）、坎（水）二卦（风炉“坎上巽下离于中”）"""
    d = g.d
    top = 35 + dy
    x = CX
    body = [(x - 18, top), (x + 18, top), (x + 15, top + 20), (x - 15, top + 20)]
    d.polygon(body, fill=0, outline=1)
    d.line((x - 18, top + 2, x + 18, top + 2), fill=1)
    for fx in (x - 11, x, x + 11):  # 三足
        d.rectangle((fx - 1, top + 21, fx + 1, top + 26), fill=1)
    d.line((x - 15, top + 20, x + 15, top + 20), fill=1)
    d.rectangle((x - 7, top + 10, x + 7, top + 18), fill=0, outline=1)   # 拱形炉门
    d.arc((x - 7, top + 5, x + 7, top + 15), 180, 360, fill=1)
    d.rectangle((x - 6, top + 10, x + 6, top + 10), fill=0)
    if fire > 0:
        flame(g, x, top + 18, 7 * fire + 2, 10 * fire + 1, t, seed)
        if fire > 0.6:
            flame(g, x - 4, top + 18, 3, 5 * fire, t + 3, seed + 1)
            flame(g, x + 4, top + 18, 3, 5 * fire, t + 7, seed + 2)
    draw_trigram(g, x - 15, int(top + 6), "巽", w=5, h=1, step=2)
    draw_trigram(g, x + 11, int(top + 6), "坎", w=5, h=1, step=2)


def fu(g: Gfx, dy: float = 0.0):
    """鍑（煮茶的锅）：口沿椭圆 + 下半圆的肚 + 两耳"""
    d = g.d
    cy = RIM + dy
    d.chord((CX - RX, cy - 12, CX + RX, cy + 12), 0, 180, fill=0, outline=1)
    d.line((CX - RX + 2, cy + 5, CX + RX - 2, cy + 5), fill=1)
    for i in range(CX - RX + 5, CX + RX - 4, 3):  # 腹部铸纹
        g.px(i, cy + 7)
        g.px(i + 1, cy + 8)
    d.rectangle((CX - RX - 3, cy - 2, CX - RX, cy), outline=1)  # 两耳
    d.rectangle((CX + RX, cy - 2, CX + RX + 3, cy), outline=1)
    d.ellipse((CX - RX, cy - RY, CX + RX, cy + RY), fill=0, outline=1)


def ladle(g: Gfx, x: float, y: float, ang: float, water: bool = False):
    """瓢：圆瓢 + 长柄。(x, y) 瓢心，ang 柄的方向（弧度，0 = 向右，负 = 向上）"""
    ux, uy = math.cos(ang), math.sin(ang)
    g.d.line((x + ux * 4, y + uy * 4, x + ux * HANDLE, y + uy * HANDLE), fill=1, width=2)
    g.d.ellipse((x - 4, y - 3, x + 4, y + 3), fill=1)
    if not water:  # 空瓢：瓢里是暗的
        g.d.ellipse((x - 2, y - 1, x + 2, y + 1), fill=0)


def bowl(g: Gfx, fill: float = 0.0, dx: float = 0.0):
    bx, by = BOWL[0] + dx, BOWL[1]
    d = g.d
    d.line((bx - 13, 61, bx + 13, 61), fill=1)          # 茶托
    d.line((bx - 11, 60, bx + 11, 60), fill=1)
    d.rectangle((bx - 4, 57, bx + 4, 59), fill=1)        # 圈足
    d.chord((bx - 11, by - 8, bx + 11, by + 7), 0, 180, fill=0, outline=1)
    d.ellipse((bx - 11, by - 2, bx + 11, by + 2), fill=0, outline=1)
    if fill > 0:  # 茶汤面 + 沫饽
        w = 9 * min(1.0, fill * 1.4)
        g.d.ellipse((bx - w, by - 1, bx + w, by + 1), fill=1)
        for i in range(5):
            g.px(bx - 6 + i * 3, by, 0)


def _mv(a, b, p, hop: float = 6.0):
    p = ease_in_out(p)
    return lerp(a[0], b[0], p), lerp(a[1], b[1], p) - math.sin(p * math.pi) * hop, lerp(a[2], b[2], p)


def _hand_of(pose):
    x, y, a = pose
    return x + math.cos(a) * HANDLE, y + math.sin(a) * HANDLE


@register
class Tea(Rest):
    id = "x2.tea"
    name = "煮茶"
    desc = "风炉铁鍑，鱼目、连珠、鼓浪三沸，宽袖的手出水、环激、投茶、斟一碗，竖写七碗茶歌"
    T = {"enter": 3.0, "exit": 1.2}

    def setup(self):
        self.n0 = self.rng.randrange(7)  # 从第几碗开始
        self.ht = 0.0

    # ------------------------------------------------------------ 水面

    def bubbles(self, g: Gfx, t: float, stage: int):
        """一沸鱼目（散泡）、二沸连珠（沿边一圈）、三沸鼓浪（水面翻起、溅沫）"""
        cy = RIM
        if stage == 0:
            n, life = 4, 1.6
            for j in range(n):
                ph = t + j * life / n
                b = int(ph / life) * n + j
                age = (ph % life) / life
                a = rand(b, self.seed) * 2 * math.pi
                r = 0.25 + rand(b + 7, self.seed) * 0.6
                x, y = CX + math.cos(a) * RX * r * 0.85, cy + math.sin(a) * RY * r * 0.7
                if age < 0.75:
                    rr = 1 + (age > 0.3)
                    g.d.ellipse((x - rr, y - rr * 0.7, x + rr, y + rr * 0.7), outline=1)
                elif age < 0.9:
                    g.px(x, y - 2)
        elif stage == 1:
            for j in range(22):  # 连珠：沿锅边一圈小泡，向上翻涌
                a = j / 22 * 2 * math.pi + t * 0.6
                wob = 1 if noise(t * 5 + j, self.seed) > 0.5 else 0
                x, y = CX + math.cos(a) * (RX - 3), cy + math.sin(a) * (RY - 1.2) - wob
                g.px(x, y)
                if j % 3 == 0:
                    g.px(x + 1, y)
        else:
            amp = 1.5 + 1.2 * math.sin(t * 9)
            prev = None
            for i in range(-RX + 2, RX - 1):
                yy = cy - abs(math.sin(i * 0.5 + t * 8)) * amp * (1 - (i / RX) ** 2)
                if prev:
                    g.d.line((prev[0], prev[1], CX + i, yy), fill=1)
                prev = (CX + i, yy)
            for j in range(8):  # 溅沫
                ph = t * 1.7 + rand(j, self.seed + 3)
                k = ph % 1.0
                x = CX + (rand(j + int(ph) * 9, self.seed) - 0.5) * RX * 1.6
                y = cy - 2 - math.sin(k * math.pi) * (5 + rand(j, 4) * 6)
                g.px(x, y)

    def whirl(self, g: Gfx, t: float):
        """环激汤心：水面一个旋涡"""
        rot = t * 7
        for j in range(3):
            pts = []
            for i in range(14):
                a = rot + j * 2.1 + i * 0.32
                r = (1 - i / 14) * (RX - 3)
                pts.append((CX + math.cos(a) * r, RIM + math.sin(a) * r * 0.22))
            g.d.line(pts, fill=1)

    def froth(self, g: Gfx, t: float, level: float):
        """沫饽：水面上细细的白沫（抖动灰度），偶尔冒个小泡"""
        if level <= 0:
            return
        pts = [(CX + math.cos(a / 16 * 2 * math.pi) * (RX - 3), RIM + math.sin(a / 16 * 2 * math.pi) * (RY - 1.5))
               for a in range(16)]
        g.shade_poly(pts, 0.25 * level, outline=None)
        for j in range(3):
            ph = t * 0.6 + j * 0.33
            if ph % 1 < 0.25:
                a = rand(int(ph) * 3 + j, 11) * 6.28
                x, y = CX + math.cos(a) * 9, RIM + math.sin(a) * 1.5
                g.d.ellipse((x - 1, y - 1, x + 1, y + 1), outline=1, fill=0)

    # ------------------------------------------------------------ 手与瓢

    def action(self, s: float):
        """一轮里的动作 → dict(ladle=(x,y,ang), water, pour, hand=(x,y)|None, sticks=bool)"""
        A = dict(ladle=REST, water=False, pour=None, hand=None, sticks=False)
        rest_hand = _hand_of(REST)
        if s < 9.6 or s >= 28.6:
            return A
        if s < 10.4:  # 手伸进来，握住瓢柄
            A["hand"] = _mv(OFF + (0,), rest_hand + (0,), (s - 9.6) / 0.8, 0)[:2]
            return A
        if s < 11.3:  # 舀出一瓢
            A["ladle"] = _mv(REST, DIP, (s - 10.4) / 0.9)
        elif s < 12.3:
            A["ladle"] = _mv(DIP, REST, s - 11.3)
            A["water"] = True
        elif s < 16.6:  # 放下瓢（盛着水），换竹筴环激汤心，再撒茶末
            A["water"] = True
            rot = s * 7
            cxh, cyh = CX + 10 + math.cos(rot) * 3, RIM - 22 + math.sin(rot) * 1
            if s < 12.8:
                A["hand"] = _mv(rest_hand + (0,), (cxh, cyh, 0), (s - 12.3) / 0.5, 4)[:2]
            elif s < 15.2:
                A["hand"] = (cxh, cyh)
                A["sticks"] = True
            else:  # 抬手撒茶末
                p = span(s, 15.2, 15.6)
                A["hand"] = (lerp(cxh, CX + 14, p), lerp(cyh, RIM - 28, p))
                A["powder"] = span(s, 15.4, 16.6)
            return A
        elif s < 21.0:  # 三沸：手退到画外等着
            A["water"] = True
            if s < 17.4:
                A["hand"] = _mv((CX + 14, RIM - 28, 0), OFF + (0,), (s - 16.6) / 0.8, 0)[:2]
            elif s > 20.2:
                A["hand"] = _mv(OFF + (0,), rest_hand + (0,), (s - 20.2) / 0.8, 0)[:2]
            return A
        elif s < 21.7:  # 拿起那瓢水，倒回去止沸
            A["ladle"] = _mv(REST, OVER_POT, (s - 21.0) / 0.7)
            A["water"] = True
        elif s < 22.7:
            x, y, a = OVER_POT
            A["ladle"] = (x, y, a + 0.5 * ease_out(span(s, 21.7, 22.0)))
            A["pour"] = "pot"
        elif s < 23.6:  # 再舀一瓢茶汤
            x, y, a = OVER_POT
            A["ladle"] = _mv((x, y, a + 0.5), DIP, (s - 22.7) / 0.9, 2)
        elif s < 24.8:
            A["ladle"] = _mv(DIP, OVER_BOWL, (s - 23.6) / 1.2, 8)
            A["water"] = True
        elif s < 26.6:  # 斟进茶碗
            x, y, a = OVER_BOWL
            A["ladle"] = (x, y, a + 0.4 * ease_out(span(s, 24.8, 25.2)))
            A["pour"] = "bowl"
        elif s < 27.8:
            x, y, a = OVER_BOWL
            A["ladle"] = _mv((x, y, a + 0.4), REST, (s - 26.6) / 1.2, 4)
        else:  # 手松开，收回
            A["hand"] = _mv(rest_hand + (0,), OFF + (0,), (s - 27.8) / 0.8, 0)[:2]
            return A
        A["hand"] = _hand_of(A["ladle"])
        return A

    def draw_action(self, g: Gfx, s: float):
        A = self.action(s)
        x, y, a = A["ladle"]
        ladle(g, x, y, a, A["water"])
        if A["pour"] == "pot":
            for k in range(0, int(RIM - 1 - y), 2):
                g.px(x - 4 + math.sin(k + s * 30) * 0.6, y + 2 + k)
        elif A["pour"] == "bowl":
            g.d.line((x - 4, y + 2, BOWL[0] - 2, BOWL[1] - 1), fill=1)
            g.px(BOWL[0] + (s * 37 % 5) - 2, BOWL[1] - 2)
        if A.get("powder"):
            k = A["powder"]
            for j in range(8):  # 茶末落进汤心
                fall = (k * 2 + j / 8) % 1
                if k < 0.8 or fall > 0.5:
                    g.px(CX + 6 - rand(j, 3) * 8 * fall, lerp(RIM - 24, RIM - 1, ease_in(fall)))
        if A["hand"]:
            hx, hy = A["hand"]
            if A["sticks"]:  # 竹筴
                g.d.line((hx - 1, hy + 2, CX - 1 + (hx - CX - 10), RIM), fill=1)
                g.d.line((hx + 1, hy + 2, CX + 1 + (hx - CX - 10), RIM), fill=1)
            sleeve_hand(g, hx, hy)

    # ------------------------------------------------------------ 画面

    def scene(self, g: Gfx, t: float, wind: float = 0.0):
        """持续阶段的一帧；t 为持续阶段秒数"""
        n = (int(t // CYC) + self.n0) % 7
        s = t % CYC
        fire = 1.0 if s < 21.7 else lerp(1.0, 0.45, span(s, 21.7, 23.0))
        if s > 36:
            fire = lerp(0.45, 1.0, span(s, 36, 40))
        g.d.line((0, 62, 127, 62), fill=1)    # 席面
        stove(g, 0, fire, t, self.seed)
        fu(g)
        if s < 10:
            self.bubbles(g, t, 0)
        elif s < 12.8:
            self.bubbles(g, t, 1)
        elif s < 16.6:
            self.whirl(g, t)
            if s > 15.8:
                g.d.ellipse((CX - 2, RIM - 1, CX + 2, RIM + 1), fill=1)
        elif s < 22.0:
            self.bubbles(g, t, 2)
        else:
            self.froth(g, t, span(s, 22.0, 23.5) * (1 - span(s, 37, 40) * 0.6))
            if s > 37:
                self.bubbles(g, t, 0)
        heat = 0.35 if s < 10 else 0.6 if s < 16.6 else 1.0 if s < 22 else 0.4
        steam(g, CX, RIM - 5, 8 + 16 * heat, t, self.seed, n=1 + int(heat * 2.5), spread=9, sway=3, drift=wind * 30)
        poured = span(s, 25.0, 26.5)
        drink = span(s, 38.6, 39.8)  # 一轮最后，碗里的茶被喝掉
        bowl(g, poured * (1 - drink))
        if 26.5 < s < 39:
            steam(g, BOWL[0], BOWL[1] - 4, 16, t, self.seed + 5, n=2, spread=5, sway=1.5, drift=wind * 30)
        # 左侧竖排：三沸之名，或本碗之诗
        if s < 22.0:
            st = 0 if s < 10 else 1 if s < 16.6 else 2
            k = s - (0, 10, 16.6)[st]
            g.vtext(3, 3, STAGE[st][:1 + int(k * 3)])
        elif s > 27.5 and n < 6:
            line = BOWL_LINES[n]
            g.vtext(3, 3, line[:int(clamp((s - 27.5) * 2.5, 0, len(line)))])
        self.draw_action(g, s)
        self.mx(g, t, s)

    def mx(self, g: Gfx, t: float, s: float):
        if s < 26.5:  # 小锅冒泡
            g.mx_rows([0, 0, 0, 0x81, 0xFF, 0x7E, 0x3C, 0x42])
            rate = 2 if s < 10 else 5 if s < 22 else 1.5
            for j in range(3):
                ph = t * rate * 0.5 + j / 3
                x = 1 + int(rand(int(ph) * 3 + j, self.seed) * 6)
                g.mx_set(x, 2 - int((ph % 1) * 3))
        else:  # 茶碗冒烟
            g.mx_rows([0, 0, 0, 0, 0xFF, 0x7E, 0x3C, 0x7E])
            for j in range(2):
                x = 2 + j * 3
                for y in range(4):
                    if (y + int(t * 3) + j) % 3 != 0:
                        g.mx_set(x + (1 if (y + int(t * 2)) % 2 else 0), y)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        up = ease_out_back(span(t, 0.0, 1.0))
        drop = ease_out_bounce(span(t, 0.7, 1.5))
        g.d.line((0, 62, 127 * ease_out(span(t, 0, 0.6)), 62), fill=1)
        fire = ease_out_back(span(t, 1.6, 2.2)) if t > 1.6 else 0
        stove(g, (1 - up) * 30, fire, t, self.seed)
        if t > 0.7:
            fu(g, -(1 - drop) * 36)
        if 1.6 < t < 1.95:  # 起火的火星
            for j in range(8):
                a = -math.pi * rand(j, 2)
                r = (t - 1.6) * 50
                g.px(CX + math.cos(a) * r, 52 + math.sin(a) * r * 0.6)
        slide = ease_out(span(t, 1.3, 2.4))
        bowl(g, 0, (1 - slide) * 50)
        x, y, a = REST
        ladle(g, x + (1 - slide) * 70, y, a)
        if t > 2.2:
            steam(g, CX, RIM - 5, (8 + 16 * 0.35) * ease_out(span(t, 2.2, 3.0)), t, self.seed, n=1, spread=9, sway=3)
            self.bubbles(g, t, 0)
        if t > 2.4:
            g.vtext(3, 3, STAGE[0][:1])
        g.mx_rows([0, 0, 0, 0x81, 0xFF, 0x7E, 0x3C, 0x42] if t > 0.7 else [0, 0, 0, 0, 0, 0, 0, 0xFF])
        if t > 1.6:
            g.mx_level = 4 if t < 1.95 else 1
            g.mx_set(3, 2, blink(t, 0.6))

    def hold(self, g: Gfx, t: float):
        self.ht = t
        n = (int(t // CYC) + self.n0) % 7
        s = t % CYC
        wind = 0.0
        if n == 6 and 29 < s < 38.5:  # 第七碗：两腋习习清风生
            wind = math.sin(math.pi * span(s, 29, 38.5)) ** 0.5
        self.scene(g, t, wind)
        if wind > 0:
            k = s - 29
            for j in range(6):
                y = 18 + j * 7
                x0 = ((k * 55 + rand(j, 6) * 128) % 190) - 40
                ln = 10 + rand(j, 8) * 14
                g.d.line((x0, y, x0 + ln, y), fill=1)
                g.d.arc((x0 + ln - 3, y - 4, x0 + ln + 3, y), 270, 90, fill=1)
            g.d.rectangle((16, 0, 127, 14), fill=0)
            typewriter(g, 18, 2, "唯觉两腋习习清风生", k - 0.6, cps=3)

    def exit(self, g: Gfx, t: float):
        self.scene(g, self.ht + t * 0.3, 0.0)
        iris(g, span(t, 0.0, self.T["exit"]), CX, 40)
        if t > 0.6:
            g.mx[:] = False
            g.mx_rows([0, 0, 0, 0, 0xFF, 0x7E, 0x3C, 0x7E] if t < 1.0 else [0, 0, 0, 0, 0, 0, 0x3C, 0])
