"""机臂结印：一只工业机械手按 G 代码依次结手诀——剑诀、握固、掌心雷，每个诀一种效果；
舵机一节节地弯指头，结成时“咔”一下闪光。

依据：道教掐诀（结印）——行法、书符、步罡都要掐诀。
  剑诀：食指、中指并拢伸直，无名指、小指屈向掌心，拇指压住二指（剑指）。
  握固：拇指扣在无名指根，其余四指屈握（《抱朴子》“握固守一”）。
  掌心雷：雷法的掌诀，摊掌发雷。
G 代码梗：G28 回原点（恰好《道德经》第二十八章“复归于无极”），G01 直线插补，M0 暂停，M24 继续，M30 程序结束；
圆满时机械臂收回画外——《道德经》第九章“功遂身退，天之道”。
入场：机械臂从画面下方升起，G28，掌心传感器亮起，五指张开。
持续：每轮 10 分钟结 15 个诀（剑诀→握固→掌心雷循环，每个约 40 秒）：舵机逐指弯曲换诀、结成一闪，
      然后放效果——剑诀：指尖射出一道剑光、剑气弧往外飞；握固：点状气环一圈圈往拳心收；掌心雷：掌心亮“雷”字，电弧四射。
      每轮开头 G28 回原点，五指依次自检屈伸，“第几轮”加一。右侧面板：行号、G01/进度、诀名。
中断：M0，手指半松、整只手垂下一点，效果熄，“暂停”。
恢复：M24，手抬回、重新结成当前的诀。
圆满：三个诀飞快连结一遍，最后掌心雷大放电全屏一闪，手张开，M30，“功遂身退”，机械臂缩回画外。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import lightning
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r6_common import ctext, cvtext, num, tiny

PX0, PY0, PX1, PY1 = 41, 30, 69, 50     # 掌
FING = [(44, 22), (51, 25), (58, 22), (65, 16)]   # 食、中、无名、小：中心 x、伸直长度
FW = 3                                  # 指宽的一半
PANEL = 99
HOME_T = 5.0
NSEAL = 15
TRANS = 1.6

OPEN = (0, 0, 0, 0, 0.0)
JIAN = (0, 0, 1, 1, 1.0)
WOGU = (1, 1, 1, 1, 0.8)
LEI = (0, 0, 0, 0, 0.15)
REST = (0.45, 0.5, 0.55, 0.6, 0.35)
SEALS = [("剑诀", JIAN), ("握固", WOGU), ("掌心雷", LEI)]

MX_OPEN = [0b00101010, 0b00101010, 0b10101010, 0b10111110, 0b01111110, 0b00111110, 0b00111100, 0b00111100]
MX_JIAN = [0b00011000, 0b00011000, 0b00011000, 0b00011000, 0b01111100, 0b00111100, 0b00111100, 0b00111100]
MX_WOGU = [0, 0, 0b00111100, 0b01111110, 0b01111110, 0b01111110, 0b00111100, 0b00111100]
MX_ICONS = {"剑诀": MX_JIAN, "握固": MX_WOGU, "掌心雷": MX_OPEN}


def mix(a, b, k: float, stagger: bool = True):
    """两个手势插值；stagger：手指依次动（舵机感）"""
    out = []
    for i in range(5):
        kk = ease_in_out(span(k, i * 0.08, i * 0.08 + 0.6)) if stagger else ease_in_out(k)
        out.append(lerp(a[i], b[i], kk))
    return tuple(out)


def finger(g: Gfx, x: float, L: float, c: float, ox: float, oy: float):
    """一根机械手指：c=0 伸直，c=1 屈到掌心（上面只剩指节，下面压在掌上一截）"""
    up = 4 + (L - 4) * (1 - c)
    down = 12 * c
    x0, x1 = x - FW + ox, x + FW + ox
    top = PY0 - up + oy
    g.d.rectangle((x0, top, x1, PY0 + down + oy), fill=0, outline=1)
    # 关节：伸直时的指节横线 + 两侧铆点
    n = 3
    for j in range(1, n):
        y = PY0 + oy - up * j / n
        g.d.line((x0, y, x1, y), fill=1)
        g.px(x0 - 1, y)
        g.px(x1 + 1, y)
    if c > 0.3:  # 屈下来的一截：两道褶 + 指甲
        for j in (1, 2):
            y = PY0 + oy + down * j / 3
            g.d.line((x0 + 1, y, x1 - 1, y), fill=1)
        g.d.rectangle((x0 + 2, PY0 + oy + down - 3, x1 - 2, PY0 + oy + down - 2), fill=1)
    else:
        g.d.rectangle((x0 + 2, top + 1, x1 - 2, top + 2), fill=1)  # 指尖传感点
    return x + ox, top


def thumb(g: Gfx, th: float, ox: float, oy: float):
    """拇指：th=0 向左上张开，th=1 横过掌心"""
    px, py = PX0 + 2 + ox, PY1 - 5 + oy
    a = math.radians(lerp(-128, -18, th))
    L = lerp(18, 25, th)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy * FW, ux * FW
    tx, ty = px + ux * L, py + uy * L
    g.d.polygon([(px + nx, py + ny), (tx + nx, ty + ny), (tx - nx, ty - ny), (px - nx, py - ny)], fill=0, outline=1)
    mx, my = px + ux * L * 0.5, py + uy * L * 0.5
    g.d.line((mx + nx, my + ny, mx - nx, my - ny), fill=1)
    g.d.ellipse((px - 3, py - 3, px + 3, py + 3), fill=0, outline=1)
    return tx, ty


def hand(g: Gfx, pose, ox: float = 0.0, oy: float = 0.0, palm: str = "sensor", t: float = 0.0):
    """整只机械手 + 腕 + 前臂。palm：掌心画什么（sensor 传感器 / lei 雷字 / none）"""
    d = g.d
    # 前臂、腕
    d.rectangle((47 + ox, PY1 + 4 + oy, 63 + ox, 70 + oy), fill=0, outline=1)
    d.line((55 + ox, PY1 + 6 + oy, 55 + ox, 70 + oy), fill=1)
    d.rectangle((45 + ox, PY1 + oy, 65 + ox, PY1 + 4 + oy), fill=0, outline=1)
    for x in range(47, 65, 3):
        g.px(x + ox, PY1 + 2 + oy)
    # 掌
    d.rectangle((PX0 + ox, PY0 + oy, PX1 + ox, PY1 + oy), fill=0, outline=1)
    for x, y in ((PX0 + 2, PY1 - 2), (PX1 - 2, PY1 - 2)):
        g.px(x + ox, y + oy)
    cx, cy = (PX0 + PX1) / 2 + ox, (PY0 + PY1) / 2 + 2 + oy
    if palm == "sensor":
        d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), outline=1)
        g.px(cx, cy)
    elif palm == "lei":
        d.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=1)
        ctext(g, cx, cy - 6, "雷", fill=0, align="center")
    tucked = sum(pose[:4]) / 4 > 0.8
    if tucked:
        thumb(g, pose[4], ox, oy)
    tips = [finger(g, x, L, pose[i], ox, oy) for i, (x, L) in enumerate(FING)]
    if not tucked:
        thumb(g, pose[4], ox, oy)
    return tips


@register
class GcodeSeal(Ritual):
    id = "r6.gcode"
    name = "机臂结印"
    desc = "工业机械手按 G 代码依次结剑诀、握固、掌心雷，舵机逐指弯曲，每个诀放一种效果；G28 归零、M30 功遂身退"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.8, "complete": 5.2}
    CYCLE = 600.0

    def setup(self):
        self.s = self.rng.randrange(10000)

    # ------------------------------------------------------------ 调度

    def state(self, e: float):
        """→ (pose, 当前诀名 or None, 槽号 j, 本槽已过秒数 s)"""
        u = e % self.CYCLE
        slot = (self.CYCLE - HOME_T) / NSEAL
        if u < HOME_T:  # 回原点 + 五指自检
            back = ease_in_out(span(u, 0.0, 1.2))
            pose = mix(LEI if e >= self.CYCLE else OPEN, OPEN, back, stagger=False)
            pose = list(pose)
            for i in range(4):
                w = span(u, 1.4 + i * 0.6, 2.4 + i * 0.6)
                pose[i] = max(pose[i], 0.7 * math.sin(math.pi * w))
            return tuple(pose), None, -1, u
        j = min(NSEAL - 1, int((u - HOME_T) / slot))
        s = (u - HOME_T) - j * slot
        name, target = SEALS[j % 3]
        prev = OPEN if j == 0 else SEALS[(j - 1) % 3][1]
        return mix(prev, target, s / TRANS), name, j, s

    # ------------------------------------------------------------ 效果

    def effect(self, g: Gfx, name: str, tips, k: float, t: float, amt: float = 1.0):
        if amt <= 0:
            return
        if name == "剑诀":
            (x1, y1), (x2, y2) = tips[0], tips[1]
            cx, top = (x1 + x2) / 2, min(y1, y2)
            if blink(t, 0.3, 0.5):  # 指尖剑芒
                for dx, dy in ((-4, 0), (4, 0), (0, -3), (-3, -2), (3, -2)):
                    g.px(cx + dx, top + dy)
            for q in range(2):  # 剑气：新月形的弧从指尖往左飞出
                ph = (t * 0.55 + q * 0.5) % 1.0
                if ph > 0.9 or amt < 0.5:
                    continue
                r = 12 + ph * 8
                x0 = cx - 6 - ph * 70
                y0 = top + 14 + ph * 10
                for w in range(3):
                    g.d.arc((x0 - r + w, y0 - r, x0 + r + w, y0 + r), 125, 235, fill=1)
                for j in range(3):  # 拖尾
                    g.d.line((x0 + r - 2 + j * 5, y0 - 6 + j * 6, x0 + r + 2 + j * 5, y0 - 6 + j * 6), fill=1)
        elif name == "握固":
            cx, cy = 55, 36
            for q in range(3):
                ph = (t * 0.6 + q / 3) % 1.0
                r = (36 - ph * 26) * amt
                n = int(r * 1.5)
                for i in range(0, n, 2):
                    a = i / n * 2 * math.pi + ph * 2
                    x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8
                    if 0 <= x < PANEL - 4:
                        g.px(x, y)
        elif name == "掌心雷":
            cx, cy = 55, 42
            f = int(t * 12)
            n = 2 + int(2 * noise(t * 2, self.s) * amt)
            for q in range(n):
                a = -math.pi * rand(f * 3 + q, self.s) - (0.3 if q % 2 else -0.3)
                r = (24 + 20 * rand(f * 5 + q, self.s + 1)) * amt
                ex = clamp(cx + math.cos(a) * r * 1.3, 0, PANEL - 5)
                ey = clamp(cy + math.sin(a) * r, 0, 63)
                lightning(g, cx + math.cos(a) * 9, cy + math.sin(a) * 9, ex, ey, seed=f * 7 + q, jag=4, branches=1)

    def snap(self, g: Gfx, k: float):
        """结成一闪：外扩的方框（舵机到位“咔”）"""
        if 0 < k < 1:
            r = 20 + k * 22
            g.d.rectangle((55 - r, 34 - r * 0.7, 55 + r, 34 + r * 0.7), outline=1)

    def panel(self, g: Gfx, l1: str, l2: str, name: str, n: int):
        g.d.line((PANEL - 3, 0, PANEL - 3, 63), fill=1)
        tiny(g, PANEL, 1, l1)
        tiny(g, PANEL, 8, l2)
        g.d.line((PANEL, 15, 127, 15), fill=1)
        if name:
            cvtext(g, PANEL + 8, 18, name)
        ctext(g, 113, 56, f"第{num(n)}轮", size=8, align="center")

    def mx(self, g: Gfx, name: str | None, t: float, k: float = 1.0):
        icon = MX_ICONS.get(name, MX_OPEN) if k >= 0.6 else MX_OPEN
        g.mx_rows(icon)
        if name == "掌心雷" and k >= 1:
            g.mx[4, 3:5] = blink(t, 0.15, 0.5)

    # ------------------------------------------------------------ 阶段

    def frame(self, g: Gfx, t: float, e: float):
        pose, name, j, s = self.state(e)
        n = int(e // self.CYCLE) + 1
        bob = math.sin(t * 1.3 + self.s) * 0.6
        k = span(s, 0.0, TRANS)
        lei = name == "掌心雷" and k >= 1
        tips = hand(g, pose, 0, bob, palm="lei" if lei else "sensor", t=t)
        if name and k >= 1:
            self.effect(g, name, tips, k, t, amt=ease_out(span(s, TRANS, TRANS + 1.0)))
            self.snap(g, span(s, TRANS, TRANS + 0.4))
        if name is None:
            self.panel(g, "N000", "G28", "归零", n)
        else:
            self.panel(g, f"N{(j + 1) * 10:03d}", "G01" if k < 1 else f"{j + 1:02d}/{NSEAL}", name, n)
        self.mx(g, name, t, k)
        if name and TRANS <= s < TRANS + 0.3:
            g.mx_level = 4

    def enter(self, g: Gfx, t: float):
        rise = ease_out_back(span(t, 0.0, 1.4))
        oy = (1 - rise) * 60
        on = t > 1.8
        hand(g, mix(REST, OPEN, span(t, 1.0, 2.6)), 0, oy, palm="sensor" if on or blink(t, 0.15, 0.5) else "none")
        cmd = "G28"
        self.panel(g, "N000", cmd[:int(span(t, 0.3, 0.8) * 3)], "归零"[:int(span(t, 2.6, 3.4) * 2)], 1)
        g.mx_rows(MX_OPEN)
        g.mx[:max(0, int((1 - rise) * 8)), :] = False

    def hold(self, g: Gfx, t: float, e: float):
        self.frame(g, t, e)

    def interrupt(self, g: Gfx, t: float, e: float):
        pose, name, j, s = self.state(e)
        n = int(e // self.CYCLE) + 1
        k = ease_in_out(span(t, 0.0, 1.0))
        p2 = mix(pose, REST, k, stagger=False)
        oy = 6 * k
        lei = name == "掌心雷" and s >= TRANS and k < 0.5
        tips = hand(g, p2, 0, oy, palm="lei" if lei else "sensor")
        if name and s >= TRANS:
            self.effect(g, name, tips, 1.0, t, amt=1 - span(t, 0.0, 0.6))
        self.panel(g, "M0", "", "暂停" if t > 0.4 else (name or "归零"), n)
        self.mx(g, name if t < 0.5 else None, t)
        if t >= 0.5:
            g.mx_rows(MX_WOGU)
            g.mx[2:4, :] = False

    def resume(self, g: Gfx, t: float, e: float):
        pose, name, j, s = self.state(e)
        n = int(e // self.CYCLE) + 1
        k = ease_in_out(span(t, 0.2, 1.3))
        p2 = mix(REST, pose, k, stagger=True)
        oy = 6 * (1 - k)
        lei = name == "掌心雷" and s >= TRANS and k >= 1
        tips = hand(g, p2, 0, oy + (math.sin(t * 1.3 + self.s) * 0.6 if k >= 1 else 0),
                    palm="lei" if lei else "sensor")
        if name and s >= TRANS:
            self.effect(g, name, tips, 1.0, t, amt=ease_out(span(t, 1.3, 1.8)))
            self.snap(g, span(t, 1.3, 1.7))
        if t < 1.4:
            self.panel(g, "M24", "", "继续" if t < 0.7 else (name or "归零"), n)
        elif name is None:
            self.panel(g, "N000", "G28", "归零", n)
        else:
            self.panel(g, f"N{(j + 1) * 10:03d}", "G01" if s < TRANS else f"{j + 1:02d}/{NSEAL}", name, n)
        self.mx(g, name, t, 1.0 if t > 1.3 else 0.0)

    def complete(self, g: Gfx, t: float, e: float):
        pose0, name0, j, s = self.state(e)
        n = int(e // self.CYCLE) + 1
        # 0–2.4 三诀连结（0.8 秒一个），2.4–3.3 掌心雷大放电，3.3–3.8 张开，3.8– 功遂身退，手缩回画外
        seq = [JIAN, WOGU, LEI]
        names = ["剑诀", "握固", "掌心雷"]
        if t < 2.4:
            q = min(2, int(t / 0.8))
            k = (t - q * 0.8) / 0.8
            prev = pose0 if q == 0 else seq[q - 1]
            pose = mix(prev, seq[q], span(k, 0.0, 0.5))
            nm = names[q]
            tips = hand(g, pose, 0, 0, palm="lei" if q == 2 and k > 0.5 else "sensor")
            if k > 0.5:
                self.effect(g, nm, tips, 1.0, t, amt=1.0)
                self.snap(g, span(k, 0.5, 0.8))
            self.panel(g, f"N{900 + q * 10}", "G01", nm, n)
            self.mx(g, nm, t, 1.0 if k > 0.5 else 0.0)
            g.mx_level = 4 if 0.5 < k < 0.6 else 1
            return
        if t < 3.3:
            tips = hand(g, LEI, 0, 0, palm="lei")
            cx, cy = 55, 42
            for q in range(7):
                a = -math.pi * (q + 0.5) / 7 + (0.2 if q % 2 else -0.2) * 0.5
                lightning(g, cx, cy, cx + math.cos(a) * 80, cy + math.sin(a) * 60, seed=q * 13 + int(t * 10), jag=6,
                          branches=2)
            if 2.45 < t < 2.6:
                g.invert((0, 0, PANEL - 3, 64))
            self.panel(g, "N930", "M3", "掌心雷", n)
            g.mx[:, :] = blink(t, 0.1, 0.5)
            g.mx_level = 6
            return
        out = ease_in(span(t, 4.2, 5.2))
        pose = mix(LEI, OPEN, span(t, 3.3, 3.8), stagger=False)
        hand(g, pose, 0, out * 70)
        self.panel(g, "M30", "END", "", n)
        if t > 3.5:
            s2 = ease_out_back(span(t, 3.5, 3.9))
            w = 34 * s2
            g.d.rectangle((50 - w, 18, 50 + w, 33), fill=0, outline=1)
            if s2 > 0.9:
                g.d.rectangle((50 - w + 2, 20, 50 + w - 2, 31), outline=1)
                ctext(g, 50, 20, "功遂身退", align="center")
        g.mx_rows(MX_OPEN)
        sh = int(out * 8)
        if sh:
            g.mx[8 - sh:, :] = False
            g.mx[sh:, :] = g.mx[:8 - sh, :].copy()
            g.mx[:sh, :] = False
        g.mx_level = 1
