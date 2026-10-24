"""开光点睛：新塑神像盖着红布，揭布之后，道士左手持宝镜引日光照像，右手朱笔依次点开眼、耳、鼻、口、心，
每点一处那里就“活”过来；五官齐明，神像放光。一尊开完，红布再盖上，换下一尊。

依据：台南道教开光仪（浅野春二《台南道教の開光儀について》，《國學院雜誌》116 卷 2 号，2015；所引大渊忍尔
所录咒文）：道士“左手持镜向神像，右手持笔点朱”，镜先取太阳精气；咒曰“神笔灵灵，太阳真精，点开禁忌，五官齐明……
左眼看万里，右眼看分明，左耳听远近，右耳知吉凶，鼻中七窍，孔相通”，又“开神口，食天禄……开神心，神灵通”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r2_common import brush, rays

SX = 78                      # 神像中轴
MIRROR = (30, 16)
PRELUDE = 20.0
STEP = 62.0
RENEW = 5.0
# 部位：(咒句, 目标点)
PARTS = [
    ("左眼看万里", (73, 26)),
    ("右眼看分明", (83, 26)),
    ("左耳听远近", (66, 30)),
    ("右耳知吉凶", (90, 30)),
    ("鼻中七窍", (78, 31)),
    ("开神口", (78, 36)),
    ("开神心", (78, 54)),
]
FINAL = "五官齐明"


@register
class KaiGuang(Ritual):
    id = "r2.kaiguang"
    name = "开光点睛"
    desc = "揭去红布，宝镜引日光照像，朱笔依次点开神像的眼、耳、鼻、口、心，五官齐明时神像放光"
    T = {"enter": 4.5, "interrupt": 1.5, "resume": 1.6, "complete": 5.5}
    CYCLE = PRELUDE + STEP * len(PARTS) + 146.0   # 600 秒

    def setup(self):
        self.s = self.rng.randrange(1000)
        self.variant0 = self.rng.randrange(2)

    # ------------------------------------------------------------ 状态

    def stage(self, u: float):
        """→ (已点开几处, 当前处序号 or -1, 本处经过秒数)"""
        if u < PRELUDE:
            return 0, -1, u
        i = int((u - PRELUDE) // STEP)
        k = (u - PRELUDE) - i * STEP
        if i >= len(PARTS):
            return len(PARTS), -1, u - PRELUDE - len(PARTS) * STEP
        return i + (k >= 2.4), i, k

    # ------------------------------------------------------------ 画面零件

    def statue(self, g: Gfx, opened: int, t: float, variant: int, glow: float = 0.0, open_k: float = 1.0):
        """opened = 已点开几处（按 PARTS 顺序），open_k = 最后一处睁开的进度"""
        cx = SX

        def ok(i):
            return i < opened

        def k_of(i):
            return open_k if i == opened - 1 else 1.0

        # 身：袍服与交领
        robe = [(cx - 12, 44), (cx + 12, 44), (cx + 26, 52), (cx + 30, 64), (cx - 30, 64), (cx - 26, 52)]
        g.d.polygon(robe, fill=0)
        g.shade_poly(robe, 0.25)
        g.d.line((cx - 10, 44, cx, 58), fill=0, width=3)
        g.d.line((cx + 10, 44, cx, 58), fill=0, width=3)
        g.d.line((cx - 10, 44, cx, 58), fill=1)
        g.d.line((cx + 10, 44, cx, 58), fill=1)
        # 头：耳（长垂）、脸
        for side, i in ((-1, 2), (1, 3)):
            ex = cx + side * 11
            g.d.ellipse((ex - 3, 24, ex + 3, 37), fill=0, outline=1)
            if ok(i):
                g.d.line((ex, 27, ex, 33), fill=1)
                if blink(t + i, 2.3, 0.15):
                    g.px(ex + side * 4, 26)
        g.d.ellipse((cx - 10, 15, cx + 10, 43), fill=0, outline=1)
        # 冠
        g.d.polygon([(cx - 10, 18), (cx - 8, 8), (cx - 3, 12), (cx, 5), (cx + 3, 12), (cx + 8, 8), (cx + 10, 18)],
                    fill=0, outline=1)
        g.d.line((cx - 10, 18, cx + 10, 18), fill=1)
        g.d.ellipse((cx - 2, 11, cx + 2, 15), fill=1)
        g.d.line((cx - 13, 19, cx - 10, 17), fill=1)  # 冠带
        g.d.line((cx + 13, 19, cx + 10, 17), fill=1)
        # 眉
        g.d.line((cx - 8, 22, cx - 3, 23), fill=1)
        g.d.line((cx + 3, 23, cx + 8, 22), fill=1)
        # 眼
        for side, i in ((-1, 0), (1, 1)):
            ex = cx + side * 5
            if ok(i):
                k = k_of(i)
                h = 0.5 + 1.0 * k
                g.d.polygon([(ex - 4, 26), (ex, 26 - h * 1.5), (ex + 4, 26), (ex, 26 + h)], fill=0, outline=1)
                if k > 0.5:  # 眼珠，偶尔转一下
                    look = 1 if noise(t * 0.4, i + self.s) > 0.7 else 0
                    g.d.rectangle((ex - 1 + look, 25, ex + look, 26), fill=1)
            else:
                g.d.line((ex - 3, 26, ex + 3, 26), fill=1)
                g.d.line((ex - 2, 27, ex + 2, 27), fill=1)
        # 鼻
        g.d.line((cx, 27, cx - 1, 32), fill=1)
        g.d.line((cx - 2, 32, cx + 2, 32), fill=1)
        if ok(4):
            g.px(cx - 2, 31)
            g.px(cx + 2, 31)
        # 口
        if ok(5):
            g.d.line((cx - 3, 36, cx + 3, 36), fill=1)
            g.d.line((cx - 2, 37, cx + 2, 37), fill=1)
            g.px(cx - 4, 35)
            g.px(cx + 4, 35)
        else:
            g.d.line((cx - 2, 36, cx + 2, 36), fill=1)
        # 须（老君相：三绺长须）
        if variant == 0:
            for dx in (-4, 0, 4):
                pts = [(cx + dx, 39), (cx + dx * 1.2 + math.sin(t + dx) * 0.6, 45), (cx + dx * 0.9, 51)]
                g.d.line(pts, fill=1)
        else:  # 灵官相：眉心竖目（开心光时一起亮）
            g.d.line((cx, 19, cx, 22), fill=1 if ok(6) else 0)
            if not ok(6):
                g.px(cx, 21)
        # 心
        if ok(6):
            r = 2 + (1 if blink(t, 1.2, 0.5) else 0)
            g.d.ellipse((cx - r, 54 - r, cx + r, 54 + r), fill=1)
        if glow > 0:
            rays(g, cx, 26, 18, 18 + glow * 10, 16, phase=t * 0.2, sy=1.0)

    def mirror(self, g: Gfx, face: float = 1.0, dy: float = 0.0):
        """宝镜：圆镜 + 握柄的手；face<1 时镜面侧转（收光）"""
        x, y = MIRROR[0], MIRROR[1] + dy
        rx = 7 * max(0.15, face)
        g.d.ellipse((x - rx, y - 7, x + rx, y + 7), fill=0, outline=1)
        if face > 0.5:
            g.d.ellipse((x - rx + 2, y - 5, x + rx - 2, y + 5), outline=1)
            g.d.line((x - 2, y - 3, x + 1, y - 4), fill=1)  # 镜面高光
        g.d.line((x, y + 7, x - 2, y + 15), fill=1)          # 柄
        g.d.line((x + 1, y + 7, x - 1, y + 15), fill=1)
        # 握柄的手 + 袖（往左下出画）
        g.d.ellipse((x - 5, y + 13, x + 2, y + 19), fill=0, outline=1)
        pts = [(x - 5, y + 16), (x + 1, y + 19), (x - 6, y + 48), (x - 24, y + 48)]
        g.d.polygon(pts, fill=0)
        g.shade_poly(pts, 0.25)

    def sunbeam(self, g: Gfx, t: float, a: float = 1.0):
        """日光从上方照进镜子"""
        x, y = MIRROR
        if a <= 0:
            return
        for j in range(0, y - 8, 3):
            yy = (j + int(t * 20)) % (y - 8)
            g.px(x - 8 + yy * 0.3, yy)
            g.px(x - 5 + yy * 0.3, yy + 1)

    def beam(self, g: Gfx, tx: float, ty: float, t: float, a: float = 1.0):
        """镜光照向神像某处：流动的点线 + 落点光斑"""
        x, y = MIRROR
        if a <= 0.05:
            return
        d = math.hypot(tx - x, ty - y)
        n = int(d / 3)
        for j in range(n):
            if (j + int(t * 12)) % 3 == 0 or rand(j, 4) > a:
                continue
            k = j / n
            g.px(lerp(x + 7, tx, k), lerp(y, ty, k))
        r = 3 + math.sin(t * 6)
        for i in range(8):
            ang = i / 8 * 2 * math.pi + t
            g.px(tx + math.cos(ang) * r, ty + math.sin(ang) * r)

    def texts(self, g: Gfx, s: str, n: int, a: float = 1.0, right: str | None = None):
        g.vtext(2, 2, s[:int(round(a * len(s)))])
        r = right if right is not None else f"第{cn_num(n)}尊"
        g.vtext(115, 2, r[:int(round(a * len(r)))])

    def cloth(self, g: Gfx, p: float, t: float):
        """红布：p=1 全盖，0 揭开（往右滑落）"""
        if p <= 0:
            return
        dx = (1 - p) * 60
        dy = (1 - p) * 20
        cx = SX + dx
        pts = [(cx - 4, 4 + dy), (cx + 4, 4 + dy), (cx + 16, 20 + dy), (cx + 30, 64), (cx - 30, 64), (cx - 16, 20 + dy)]
        g.d.polygon(pts, fill=0)
        g.shade_poly(pts, 0.5)
        for j in range(3):  # 褶
            g.d.line((cx - 2 + j * 2, 8 + dy, cx - 14 + j * 14, 62), fill=0)

    def mx(self, g: Gfx, opened: int, t: float, dot: bool = False):
        for side, i in ((0, 0), (5, 1)):
            if i < opened:
                g.mx[2, side + 1] = g.mx[4, side + 1] = True
                g.mx[3, side] = g.mx[3, side + 2] = True
                g.mx[3, side + 1] = blink(t + i, 1.7, 0.85)
            else:
                g.mx[3, side:side + 3] = True
        if opened > 5:
            g.mx[6, 2:6] = True
        if dot:
            g.mx[0, 3:5] = True
            g.mx_level = 5

    # ------------------------------------------------------------ 主画面

    def variant(self, e: float) -> int:
        return (self.variant0 + int(e // self.CYCLE)) % 2

    def frame(self, g: Gfx, t: float, u: float, e: float, beam_a: float = 1.0, brush_on: bool = True):
        opened, cur, k = self.stage(u)
        var = self.variant(e)
        open_k = 1.0
        if cur >= 0:
            open_k = span(k, 2.4, 3.4)
        final = u >= PRELUDE + STEP * len(PARTS)
        glow = 0.0
        if final:
            ff = (u - PRELUDE - STEP * len(PARTS)) % 5.0
            glow = 1 - span(ff, 0, 1.5)
        self.statue(g, opened, t, var, glow=glow, open_k=open_k)
        self.sunbeam(g, t, beam_a)
        self.mirror(g)
        # 镜光：从上一处扫到这一处
        if cur >= 0:
            prev = PARTS[cur - 1][1] if cur > 0 else (SX, 10)
            tgt = PARTS[cur][1]
            p = ease_in_out(span(k, 0, 1.4))
            self.beam(g, lerp(prev[0], tgt[0], p), lerp(prev[1], tgt[1], p), t, beam_a)
            text = PARTS[cur][0]
            ta = span(k, 0, 1.2)
        elif final:
            self.beam(g, SX, 26, t, beam_a)
            text, ta = FINAL, span(u - PRELUDE - STEP * len(PARTS), 0, 1.2)
        else:
            self.beam(g, SX, 10 + 2 * math.sin(t), t, beam_a * span(u, 2, 4))
            text, ta = "神笔灵灵", span(u, 0, 2.0)
        dot = False
        if cur >= 0 and brush_on and 1.2 < k < 3.4:  # 朱笔从右下来，点一下
            tx, ty = PARTS[cur][1]
            if k < 2.0:
                p = ease_out(span(k, 1.2, 2.0))
                bx, by = lerp(126, tx + 3, p), lerp(70, ty + 3, p)
            elif k < 2.4:
                q = span(k, 2.0, 2.4)
                bx, by = tx + 3 * (1 - q), ty + 3 * (1 - q)
            else:
                p = ease_in(span(k, 2.4, 3.4))
                bx, by = lerp(tx, 130, p), lerp(ty, 74, p)
            brush(g, bx, by, 0.75, 34)
            if 2.3 < k < 2.7:  # 点下去的一瞬：朱点迸光
                rays(g, tx, ty, 3, 7, 8, phase=0.3)
                dot = True
        self.texts(g, text, int(e // self.CYCLE) + 1, a=1.0)
        if ta < 1:
            g.d.rectangle((0, 2 + int(ta * len(text)) * 12, 14, 63), fill=0)
        self.mx(g, opened, t, dot)
        if glow > 0.5:
            g.mx_level = 3

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.statue(g, 0, t, self.variant(0))
        self.cloth(g, 1 - ease_in_out(span(t, 1.0, 2.0)), t)
        if t > 1.9:  # 宝镜从左下举起
            p = ease_out_back(span(t, 1.9, 2.8))
            self.mirror(g, dy=(1 - p) * 40)
        if t > 2.8:
            self.sunbeam(g, t, span(t, 2.8, 3.4))
            self.beam(g, SX, 10 + 2 * math.sin(t), t, span(t, 3.2, 4.0))
        self.texts(g, "神笔灵灵", 1, a=span(t, 2.6, 4.5))
        self.mx(g, 0, t)
        if t < 1.2:
            g.mx[:, :] = False
            g.mx[1:8, 1:7] = True  # 红布
        g.mx_level = 3 if 1.0 < t < 1.3 else 1

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, e)
            return
        self.frame(g, t, u, e)

    def _renew(self, g: Gfx, t: float, u: float, e: float):
        """红布盖上这一尊，再揭开，下一尊"""
        n = int(e // self.CYCLE) + 1
        if u < 2.5:
            self.statue(g, len(PARTS), t, self.variant(e - u - 1), glow=1 - span(u, 0, 1))
            self.cloth(g, ease_out(span(u, 0.6, 1.6)), t)
            self.texts(g, FINAL, n - 1)
        else:
            self.statue(g, 0, t, self.variant(e))
            self.cloth(g, 1 - ease_in_out(span(u, 3.0, 4.2)), t)
            self.texts(g, "神笔灵灵", n, a=span(u, 3.6, 5.0))
        self.mirror(g)
        self.sunbeam(g, t)
        self.mx(g, len(PARTS) if u < 1.6 else 0, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        """宝镜翻转收光，朱笔放下"""
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        opened, cur, k = self.stage(u)
        f = ease_in_out(span(t, 0, 1.0))
        self.statue(g, opened, t, self.variant(e))
        self.sunbeam(g, t, 1 - f)
        self.mirror(g, face=1 - f)
        if cur >= 0:
            self.beam(g, *PARTS[cur][1], t, 1 - f)
        self.texts(g, "", int(e // self.CYCLE) + 1, right="暂歇")
        self.mx(g, opened, t)

    def resume(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        f = ease_in_out(span(t, 0.2, 1.2))
        if t < 1.2:
            opened, cur, k = self.stage(u)
            self.statue(g, opened, t, self.variant(e))
            self.mirror(g, face=f)
            self.sunbeam(g, t, f)
            if cur >= 0:
                self.beam(g, *PARTS[cur][1], t, f)
            self.texts(g, "", int(e // self.CYCLE) + 1)
            self.mx(g, opened, t)
        else:
            self.frame(g, t, u, e, brush_on=False)

    def complete(self, g: Gfx, t: float, e: float):
        """余下各处一气点完，五官齐明，神像放光"""
        u = e % self.CYCLE
        opened0, cur, k = self.stage(max(u, 0))
        opened = min(len(PARTS), opened0 + int(span(t, 0, 1.6) * (len(PARTS) - opened0 + 0.99)))
        glow = ease_out(span(t, 1.8, 2.6))
        self.statue(g, opened, t, self.variant(e), glow=0)
        if t < 1.7 and opened < len(PARTS):  # 朱笔快速点过剩下的
            tx, ty = PARTS[opened][1]
            brush(g, tx + 1, ty + 1, 0.75, 34)
            rays(g, tx, ty, 3, 6, 8)
        self.mirror(g)
        self.sunbeam(g, t)
        self.beam(g, SX, 26, t)
        if t > 1.8:
            k2 = t - 1.8
            for j in range(3):
                r = ((k2 * 24 + j * 12) % 36) + 14
                rays(g, SX, 28, r, r + 4, 18, phase=j * 0.17)
            if k2 < 0.12:
                g.invert((50, 0, 108, 64))
        if t < 1.8:
            self.texts(g, "神笔灵灵", int(e // self.CYCLE) + 1)
        else:
            g.vtext(2, 2, FINAL[:int(clamp((t - 1.8) * 5, 0, 4))])
            g.vtext(115, 2, "开光")
        self.mx(g, opened, t, dot=t < 1.7)
        if t > 1.8:
            g.mx[0, :] = g.mx[7, :] = blink(t, 0.3)
            g.mx_level = 1 + int(5 * (1 - span(t, 1.8, 3.5)))
