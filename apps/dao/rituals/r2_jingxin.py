"""净心神咒：月夜湖边，小道士盘坐在岸石的蒲团上念《净心神咒》，水面倒映远山明月，一句比一句平，终至水平如镜。

依据：《净心神咒》（正一日诵早晚课）：“太上台星，应变无停。驱邪缚魅，保命护身。智慧明净，心神安宁。
三魂永久，魄无丧倾。急急如律令。”画面取“心如止水”。

舞台：左边近岸一块大石（裂纹、草丛），石上蒲团，小道士面朝湖盘坐；岸边三根芦苇随风摆；远处两重山（山顶一座小亭）、
明月、星星；水面是水平线以上画面的像素倒影（逐行按波纹错位，起波时隔行断开），月亮倒影在右下。
入场：月亮从远山后升起，小道士走来坐上蒲团，拱手闭目，咒牌写出“净心神咒”。
持续：一遍 450 秒（开头 3.5 秒起咒 + 8 句 × 52 秒 + “急急如律令”30.5 秒）。咒句在夜空的咒牌里逐字写出，嘴一张一合；
      每句开头换一个手诀、睁眼，面前水面推开一圈涟漪；句中呼一口气（一小团白气）、点头；水波幅度随 e 从 3 像素降到 0，
      倒影一句比一句完整。小事件轮流出现：鱼跃出水（溅起水花、落水一圈涟漪）、萤火虫绕着芦苇飞、芦苇尖一滴露水落水。
      续：一阵风（风线）掠过，芦苇压弯，水面重新起波，从头再念。
中断：一朵云飘来遮住月亮，咒牌换成“暂歇”，小道士低头闭目。恢复：云飘走，月光重现，小道士抬头，咒句回来。
圆满：水波收尽，水平如镜，月亮放光（倒影里也放光），闪白一下，“心神安宁”。
点阵：上半月亮、中间水平线、下半月亮倒影（随波幅左右错动）。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, lerp, noise, rand, span
from ..engine.chars import Part, figure
from ..engine.cn import cn_num
from ..engine.fx import stars
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import boxed, cushion_spr, ring, star4
from .r2_jinguang import mouth, seated

PHRASES = ["太上台星", "应变无停", "驱邪缚魅", "保命护身", "智慧明净", "心神安宁", "三魂永久", "魄无丧倾"]
LAST = "急急如律令"
NP = len(PHRASES)
LEAD = 3.5
SLOT = 52.0
LAST_AT = LEAD + NP * SLOT
CPS = 0.6
HZ = 40                  # 水平线
W0 = 37                  # 水面左边（左边是岸石）
MOON = (108, 20)
DX = 17                  # 小道士
SIT_Y = 48
TXC = 68                 # 咒牌中线
MUDRA = ["gong", "chest", "palm", "fwd", "gong", "up", "palm", "chest"]


# ---------------------------------------------------------------- 道具

def _rock():
    """岸石 42×18：暗色石块、亮轮廓，顶面受月光（稀疏网点）、几道裂纹、背光面竖线、顶上两丛草"""
    p = Part(42, 18)
    outline = [(0, 3), (6, 1), (20, 1), (30, 2), (36, 5), (39, 11), (41, 17), (0, 17)]
    p.shape("polygon", outline, fill=0)
    p.d.line(outline + [outline[0]], fill=1)
    p.d.line((2, 4, 33, 4), fill=1)                       # 顶面前沿
    p.dither([(3, 2), (30, 2), (32, 4), (2, 4)], 0.25, 1)
    for a, b in (((10, 6), (14, 10)), ((14, 10), (12, 15)), ((24, 6), (27, 11)), ((27, 11), (31, 12)),
                 ((4, 9), (6, 14))):
        p.d.line(a + b, fill=1)
    for x in range(33, 40, 2):                            # 背光面
        p.d.line((x, 8 + (x - 33), x, 16), fill=1)
    for x in (2, 31):                                     # 草丛
        p.shape("line", (x, -1, x + 1, 1), fill=1)
        p.shape("line", (x + 3, -1, x + 2, 1), fill=1)
    return p.sprite()


def _pavilion():
    """山顶小亭 9×7：飞檐、亭柱"""
    p = Part(9, 7)
    p.shape("polygon", [(0, 3), (2, 2), (4, 0), (6, 2), (8, 3), (6, 3), (2, 3)], fill=1)
    p.shape("rectangle", (2, 4, 2, 6), fill=1)
    p.shape("rectangle", (6, 4, 6, 6), fill=1)
    p.shape("rectangle", (1, 6, 7, 6), fill=1)
    return p.sprite()


def _cloud():
    """云 26×9：三个鼓包、底边平，里面一道卷纹"""
    p = Part(26, 9)
    for box in ((0, 3, 10, 9), (6, 0, 17, 9), (14, 2, 25, 9)):
        p.shape("ellipse", box, fill=1)
    for box in ((1, 4, 9, 8), (7, 1, 16, 8), (15, 3, 24, 8)):
        p.d.ellipse(box, fill=0)
    p.d.rectangle((2, 6, 23, 7), fill=0)
    p.d.arc((9, 3, 14, 7), 180, 360, fill=1)
    return p.sprite()


FISH = pix.frames("""
  ###   #
 #.####.#
########
 ######.#
  ###   #
---
  ###  #
 #.#####
########
 ######
  ### ##
""")
FISH_DOWN = FISH[1].flipv()   # 落水时头朝下

_P: dict = {}


def prop(name):
    if name not in _P:
        _P[name] = {"rock": _rock, "pav": _pavilion, "cloud": _cloud}[name]()
    return _P[name]


@register
class JingXin(Ritual):
    id = "r2.jingxin"
    name = "净心神咒"
    desc = "月夜湖边，小道士盘坐岸石念《净心神咒》，咒句逐字写在夜空，水面倒映远山明月，波纹一句比一句平，终至水平如镜"
    T = {"enter": 4.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.0}
    CYCLE = LAST_AT + 30.5   # 450 秒

    def setup(self):
        self.s = self.rng.randrange(1000)
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)
        self.last_t = None
        def taper(x):  # 月亮那边（右）山低
            return 1.0 if x < 82 else lerp(1.0, 0.25, (x - 82) / 46)
        self.far = [HZ - 2 - (10 + 6 * noise(i * 0.05, self.s) + 3 * noise(i * 0.17, self.s + 3)) * taper(i)
                    for i in range(130)]
        self.near = [HZ - 1 - (3 + 10 * noise(i * 0.06 + 5, self.s + 1) ** 1.4) * taper(i + 10) for i in range(130)]
        self.peak = max(range(W0 + 10, 90), key=lambda i: HZ - self.near[i])
        from PIL import Image, ImageDraw
        m = Image.new("1", (128, 64))
        ImageDraw.Draw(m).polygon([(i, self.near[i] + 2) for i in range(W0 - 4, 129, 2)] + [(128, HZ - 1), (W0 - 4, HZ - 1)],
                                  fill=1)
        self.near_mask = np.array(m, bool)

    def _dt(self, t):
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    # ------------------------------------------------------------ 状态

    def slot(self, u: float):
        if u < LEAD:
            return -1, u
        if u >= LAST_AT:
            return NP, u - LAST_AT
        i = int((u - LEAD) // SLOT)
        return i, u - LEAD - i * SLOT

    def amp(self, u: float) -> float:
        """水波幅度：一遍开头 3，念到末句前 0"""
        return lerp(3.0, 0.0, ease_out(clamp((u - LEAD) / (NP * SLOT)))) if u >= LEAD else 3.0

    # ------------------------------------------------------------ 画面零件

    def sky(self, g: Gfx, t: float, moon_y: float = MOON[1], glow: float = 0.0):
        stars(g, t, self.s, n=22, box=(0, 0, 128, 28), twinkle=0.3)
        mx, my = MOON[0], moon_y
        if glow > 0:
            for i in range(12):
                a = i / 12 * 2 * math.pi + t * 0.2
                r0, r1 = 8, 8 + glow * (3 + (i % 2) * 2)
                g.d.line((mx + math.cos(a) * r0, my + math.sin(a) * r0, mx + math.cos(a) * r1,
                          my + math.sin(a) * r1), fill=1)
        # 远山（点线轮廓）
        pts = [(i, self.far[i]) for i in range(W0 - 4, 129, 3)]
        g.d.polygon(pts + [(128, HZ), (W0 - 4, HZ)], fill=0)
        for x, y in pts:
            g.px(x, y)
            g.px(x + 1, y)
        # 月亮在远山之前、近山之后
        g.d.ellipse((mx - 6, my - 6, mx + 6, my + 6), fill=1)
        for dx, dy, r in ((-2, -2, 1.5), (3, 1, 1.0), (-1, 3, 1.0)):  # 月面暗斑
            g.d.ellipse((mx + dx - r, my + dy - r, mx + dx + r, my + dy + r), fill=0)
        g.px(mx + 2, my - 3, 0)
        # 近山（实线 + 迎月坡上稀疏网点）
        pts = [(i, self.near[i]) for i in range(W0 - 4, 129, 2)]
        g.d.polygon(pts + [(128, HZ), (W0 - 4, HZ)], fill=0)
        g.d.line(pts, fill=1)
        pix.checker_mask(g, self.near_mask, 0.125)
        pk = self.peak
        pix.blit(g, prop("pav"), pk - 4, self.near[pk] - 6, outline=False)
        g.d.line((W0 - 4, HZ, 127, HZ), fill=1)

    def reflect(self, g: Gfx, A: float, t: float):
        """水面：水平线以上逐行镜像；按波纹左右错位，有波时隔行断开（水的横纹），波越大越碎"""
        a = g.array()
        ph = int(t * 3)
        for y in range(HZ + 1, 64):
            src = 2 * HZ - y
            d = (y - HZ) / (64 - HZ)
            if A > 0.6 and (y + ph) % 2:
                a[y, W0:] = False
                continue
            if A > 2.0 and (y + ph) % 4 == 0:
                a[y, W0:] = False
                continue
            sh = int(round(A * (0.4 + 0.6 * d) * math.sin(y * 1.3 + t * 2.4)))
            row = np.roll(a[src], sh)
            a[y, W0:] = row[W0:]
        g.put(a)
        n = int(A * 2.5)                      # 波光：几道短横线在水面上漂
        for j in range(n):
            y = HZ + 3 + int(rand(j, self.s) * 20)
            x = W0 + (rand(j + 50, self.s) * 90 + t * (6 + j)) % 90
            g.d.line((x, y, x + 2 + j % 3, y), fill=1)

    def ripple(self, g: Gfx, x: float, y: float, age: float, size: float = 18):
        """水面涟漪：压扁的椭圆圈，外扩变淡"""
        for j in range(2):
            r = age * size - j * 4
            if 0 < r < size:
                ry = max(r * 0.28, 0.6)
                box = (x - r, y - ry, x + r, y + ry)
                if (age * 10 + j) % 2 < 1.6:
                    g.d.ellipse(box, outline=1)
                if r > size * 0.6:  # 快散了：挖成虚线
                    for k in range(0, int(r * 2), 3):
                        g.px(x - r + k, y + ry, 0)
                        g.px(x - r + k + 1, y - ry, 0)

    def reeds(self, g: Gfx, t: float, wind: float = 0.0):
        """岸边三根芦苇（前景），蒲棒随风摆"""
        for j, (x, h) in enumerate(((W0 - 3, 17), (W0 + 1, 21), (W0 + 4, 14))):
            sway = math.sin(t * 1.3 + j * 1.7) * 1.2 + wind * (3 + j)
            bx, by = x, 52
            tx, ty = x + sway, by - h
            g.d.line((bx, by, (bx + tx) / 2 + sway * 0.2, (by + ty) / 2), fill=1)
            g.d.line(((bx + tx) / 2 + sway * 0.2, (by + ty) / 2, tx, ty), fill=1)
            g.d.rectangle((tx - 1, ty - 1, tx, ty + 3), fill=1)   # 蒲棒
            g.px(tx, ty - 3), g.px(tx, ty - 2)
            lx = bx + (sway * 0.5) + (3 if j % 2 else -3)            # 一片叶
            g.d.line((bx, by - 5 - j, lx, by - 9 - j), fill=1)

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        boxed(g, 3, 3, label or (f"第{cn_num(n)}遍" if n < 100 else f"{n}遍"))

    def verse(self, g: Gfx, s: str, k: float | None):
        """夜空里的咒牌：清黑底、框，逐字写出"""
        n = len(s)
        w = 12 * n + (n - 1)
        x0 = TXC - w / 2
        box = (x0 - 3, 1, x0 + w + 2, 16)
        g.d.rectangle(box, fill=0, outline=1)
        shown = n if k is None else min(n, int(k / CPS) + 1)
        for j, ch in enumerate(s[:shown]):
            g.text(x0 + j * 13, 4, ch)

    def mx(self, g: Gfx, A: float, t: float, moon: bool = True, glow: bool = False):
        if moon:
            g.mx[0, 3:5] = True
            g.mx[1, 2:6] = True
            g.mx[2, 3:5] = True
        g.mx[4, :] = True
        sh = int(round(A * 0.7 * math.sin(t * 2.4)))
        for y, (a, b) in ((5, (3, 5)), (6, (2, 6)), (7, (3, 5))):
            if A > 1.2 and y == 6 and int(t * 3) % 2:
                continue
            for x in range(a, b):
                g.mx_set(x + sh * (1 if y != 6 else -1), y)
        if glow:
            for x, y in ((1, 0), (6, 0), (0, 2), (7, 2)):
                g.mx[y, x] = int(t * 6) % 2 == 0

    # ------------------------------------------------------------ 一帧

    def scene(self, g: Gfx, t: float, e: float, dt: float, A: float | None = None, show_verse: bool = True,
              cloud_x: float | None = None, face_over=None, head_over=None, mudra_over=None, label=None,
              moon_glow: float = 0.0, wind: float = 0.0):
        u = e % self.CYCLE
        i, k = self.slot(u)
        renew = e >= self.CYCLE and u < LEAD
        if A is None:
            A = self.amp(u)
            if renew:
                A = lerp(0.0, 3.0, ease_out(span(u, 0.3, 1.6)))
                wind = math.sin(span(u, 0.0, 2.4) * math.pi)
        self.sky(g, t, glow=moon_glow)
        if cloud_x is not None:
            pix.blit(g, prop("cloud"), cloud_x - 13, MOON[1] - 6)
        self.reflect(g, A, t)
        # 水面上的事件（在倒影之后）
        if show_verse and i >= 0:
            if k < 4.0:  # 每句开头：面前推开一圈涟漪
                self.ripple(g, W0 + 14, 50, k / 4.0, 26)
            ev = (i + int(self.s)) % 3
            self.events(g, ev, k, t, dt)
        if renew or wind > 0:  # 风线
            for j in range(4):
                x = ((u if renew else t) * 90 + j * 37) % 170 - 30
                y = 18 + j * 9
                pix.dotted(g, x, y, x + 14, y, step=2)
        pix.blit(g, prop("rock"), 0, SIT_Y)
        pix.blit(g, cushion_spr(), DX - 12, SIT_Y - 3)
        m, face, head = "gong", "sleep", "up"
        if i >= 0 and show_verse:
            m = MUDRA[i % len(MUDRA)] if i < NP else "gong"
            if k < 1.2 or 30.0 < k < 31.5:
                face = "normal"
            if 38.0 < k < 39.4:
                head = "bow"
            if i == NP:
                face = "happy" if k > 4 else "sleep"
        if renew:
            m, face = "gong", ("wow" if 0.5 < u < 2.0 else "sleep")
        m = mudra_over or m
        face = face_over or face
        head = head_over or head
        hand = seated(g, DX, SIT_Y, t, m, face, head)
        if show_verse and i >= 0 and head == "up":
            n = len(PHRASES[i]) if i < NP else len(LAST)
            if k < n * CPS + 0.3:
                mouth(g, DX, SIT_Y, int(k / CPS * 2) % 2 == 0)
            if k < 0.3 and m != "gong":
                star4(g, hand[0], hand[1])
            if 20.0 <= k < 20.0 + dt * 1.5:  # 呼一口气
                self.puffs.emit(DX + 9, SIT_Y - 21, vx=8, vy=-2, life=1.2, rmax=1.4, spread=0)
        self.reeds(g, t, wind)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g, trail=False)
        # 文字最后画
        if label:
            self.verse(g, label, None)
        elif show_verse:
            if i < 0 or renew:
                self.verse(g, "净心神咒", None)
            elif i < NP:
                self.verse(g, PHRASES[i], k)
            else:
                self.verse(g, LAST, k)
        self.counter(g, e if not (renew and u < 1.0) else e - u - 1)
        self.mx(g, A, t, moon=cloud_x is None or abs(cloud_x - MOON[0]) > 14, glow=moon_glow > 0)
        return A

    def events(self, g: Gfx, ev: int, k: float, t: float, dt: float):
        """句中小事件：0 鱼跃（12–14.5s）/ 1 萤火虫（24–34s）/ 2 芦苇尖露水落水（44–46.5s）；另两种也会穿插"""
        # 鱼跃：每句都有一次，位置随句变化
        fx0 = 62 + (ev * 17) % 40
        q = span(k, 12.0, 13.2)
        if 0 < q < 1:
            x = fx0 + q * 14
            y = HZ + 6 - math.sin(q * math.pi) * 14
            pix.blit(g, FISH[0] if q < 0.5 else FISH_DOWN, x - 2, y - 1)
        if 12.0 <= k < 12.0 + dt * 1.5:
            self.sparks.burst(fx0, HZ + 6, 6, 18, up=14, life=0.5, gravity=60)
        if 13.2 <= k < 13.2 + dt * 1.5:
            self.sparks.burst(fx0 + 14, HZ + 6, 8, 20, up=16, life=0.6, gravity=60)
        if 13.2 < k < 16.2:
            self.ripple(g, fx0 + 14, HZ + 7, (k - 13.2) / 3.0, 12)
        if 12.0 < k < 14.0:
            self.ripple(g, fx0, HZ + 7, (k - 12.0) / 2.0, 7)
        # 萤火虫：绕着芦苇飞，一明一灭
        if 24.0 < k < 34.0 and ev != 2:
            a = (k - 24.0) * 0.9
            x = W0 + 6 + math.sin(a * 1.3) * 12 + (k - 24.0) * 2
            y = 36 + math.sin(a * 2.1) * 5
            if (k * 3) % 1 < 0.6:
                g.px(x, y)
                g.px(x + 1, y)
                g.px(x, y - 1) if (k * 6) % 1 < 0.5 else None
            if (k * 3) % 1 < 0.6:  # 水里的倒影
                g.px(x, 2 * HZ - y)
        # 露水：芦苇尖一滴落水
        q = span(k, 44.0, 44.8)
        if 0 < q < 1:
            g.px(W0 + 5, 31 + ease_in(q) * 20)
        if 44.8 < k < 47.5:
            self.ripple(g, W0 + 6, 51, (k - 44.8) / 2.7, 9)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        my = lerp(HZ + 8, MOON[1], ease_out(span(t, 0.0, 2.2)))
        self.sky(g, t, moon_y=my)
        self.reflect(g, 3.0, t)
        pix.blit(g, prop("rock"), 0, SIT_Y)
        pix.blit(g, cushion_spr(), DX - 12, SIT_Y - 3)
        if t < 1.6:  # 从左边走来
            x = lerp(-12, DX - 8, ease_out(span(t, 0.0, 1.6)))
            figure(g, x, SIT_Y + 2, t, legs="walk")
        elif t < 2.1:
            q = span(t, 1.6, 2.1)
            if q < 0.6:
                figure(g, lerp(DX - 8, DX, q), SIT_Y + 2 - math.sin(q / 0.6 * math.pi) * 6, t, arm="raise",
                       face="happy")
            else:
                seated(g, DX, SIT_Y - (1 - span(q, 0.6, 1)) * 2, t, "gong", "happy")
        else:
            seated(g, DX, SIT_Y, t, "gong", "normal" if t < 2.8 else "sleep")
        if t - dt < 2.1 <= t:
            self.puffs.emit(DX - 11, SIT_Y - 1, vx=-6, vy=-3, life=0.6, rmax=1.4)
            self.puffs.emit(DX + 11, SIT_Y - 1, vx=6, vy=-3, life=0.6, rmax=1.4)
        self.reeds(g, t)
        self.puffs.step(dt)
        self.puffs.draw(g)
        if t > 2.6:
            self.verse(g, "净心神咒", None)
        self.counter(g, 0.0)
        self.mx(g, 3.0, t, moon=my < HZ - 6)

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        self.scene(g, t, e, dt)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        cx = lerp(150, MOON[0], ease_out(span(t, 0.0, 1.2)))
        A = self.amp(e % self.CYCLE)
        self.scene(g, t, e, dt, A=A + span(t, 0.2, 1.4) * 0.8, show_verse=False, cloud_x=cx, face_over="sleep",
                   head_over="bow" if t > 0.9 else "up", mudra_over="gong", label="暂歇")

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        cx = lerp(MOON[0], -20, ease_in_out(span(t, 0.0, 1.3)))
        A = self.amp(e % self.CYCLE)
        back = t > 1.2
        self.scene(g, t, e, dt, A=A + (1 - span(t, 0.4, 1.6)) * 0.8, show_verse=back,
                   cloud_x=cx if t < 1.3 else None, face_over=None if back else ("normal" if t > 0.6 else "sleep"),
                   mudra_over=None if back else "gong", label=None if back else "暂歇")

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        A = lerp(self.amp(e % self.CYCLE), 0.0, ease_out(span(t, 0.0, 1.4)))
        glow = span(t, 1.4, 2.0)
        self.sky(g, t, glow=glow)
        self.reflect(g, A, t)
        if t > 1.4:  # 明镜里也有一圈光
            for j in range(2):
                r = (t - 1.4) * 14 - j * 6
                if 0 < r < 30:
                    ring(g, MOON[0], MOON[1], 8 + r, step=3)
        pix.blit(g, prop("rock"), 0, SIT_Y)
        pix.blit(g, cushion_spr(), DX - 12, SIT_Y - 3)
        seated(g, DX, SIT_Y, t, "gong", "happy" if t > 1.6 else "sleep", "bow" if 2.6 < t < 3.6 else "up")
        self.reeds(g, t)
        if 1.4 <= t < 1.4 + dt:
            pix.flash(g)
            self.sparks.burst(MOON[0], MOON[1], 20, 30, life=1.0, gravity=0)
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g, trail=False)
        self.verse(g, LAST if t < 1.4 else "心神安宁", None)
        self.counter(g, e)
        self.mx(g, A, t, glow=t > 1.4)
        if t > 1.4:
            g.mx_level = 1 + int(5 * (1 - span(t, 1.4, 3.0)))
