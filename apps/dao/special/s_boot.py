"""开坛：程序启动（控制器接管）时播放，约 3.5 秒。

夜空星点闪烁，远山一线；小道士踩着一朵祥云从左上飞来（身后拖一串灵光），到场一跃而下，
“咚”地单膝落地：闪白、震屏、尘土与火星四溅；起身拱手，身后一轮光环放射旋转。
右边“dao timer”一个字母一个字母砸下来（每个落点一粒火星），横线划出，
再写出境界（ctx.realm()）与道行（ctx.completed），小道士作揖，右下角落一枚“道”字印。
点阵：一点闪烁 → 落地一圈扩散 → 旋转太极。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_out, ease_out_back, lerp, span
from ..engine.chars import Part, daoshi, figure
from ..engine.fx import stars
from ..engine.gfx import Gfx, text_width
from ..engine.scene import Special, register
from ..engine.symbols import mx_taiji
from ..omens.o_common import FLOOR, Stage, floor, star4

DAO_X = 26
ARRIVE = 0.95        # 祥云到位
JUMP = (1.0, 1.32)   # 跃下 → 落地
TITLE = 1.55
REALM = 2.2
DAOXING = 2.55
SEAL = 2.95
TX = 54              # 右侧文字左边


def _cloud():
    """祥云 30×10：三个云头 + 两个回卷 + 向后的云尾"""
    p = Part(32, 11)
    for box in ((4, 2, 13, 9), (10, 0, 21, 9), (18, 2, 27, 9), (24, 4, 31, 10)):
        p.shape("ellipse", box, fill=1)
    p.shape("polygon", [(0, 9), (6, 6), (8, 10)], fill=1)
    p.d.arc((8, 3, 14, 9), 180, 450, fill=0)       # 回卷
    p.d.arc((19, 3, 25, 9), 180, 450, fill=0)
    p.px(11, 6, 0), p.px(22, 6, 0)
    p.d.line((5, 10, 30, 10), fill=0)
    p.dither((15, 7, 31, 9), 0.5, 0)
    return p.sprite()


def _seal():
    p = Part(15, 15)
    p.shape("rectangle", (0, 0, 14, 14), fill=1)
    p.d.rectangle((1, 1, 13, 13), outline=0)
    p.px(0, 0, 0), p.px(14, 14, 0), p.px(14, 0, 0)
    return p.sprite()


SPR = {}


def spr(n):
    if not SPR:
        SPR.update(cloud=_cloud(), seal=_seal())
    return SPR[n]


def ridge(g: Gfx):
    pts = [(0, 46), (12, 40), (22, 43), (34, 36), (46, 42), (52, 44)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        pix.dotted(g, x0, y0, x1, y1, 2)


@register
class Boot(Stage, Special):
    id = "s.boot"
    name = "开坛"
    desc = "小道士踩祥云飞来一跃落地，闪白震屏火星四溅，身后光环旋转；dao timer 逐字砸下，写出境界、道行，落印"
    T = {"play": 3.5}

    def setup(self):
        self.stage_init()

    def play(self, g: Gfx, t: float):
        self.tick(t)
        stars(g, t, seed=3, n=14, box=(0, 0, 50, 30))
        ridge(g)
        floor(g, "stone")
        land = JUMP[1]
        # ---------------- 光环（落地后，身后旋转的放射光）
        if t > land:
            p = ease_out_back(span(t, land, land + 0.35))
            cx, cy = DAO_X, FLOOR - 18
            r0, r1 = 15 * p, 18 * p
            for j in range(16):
                a = j / 16 * 2 * math.pi + t * 0.8
                long = j % 2 == 0
                rr = r1 + (4 if long else 0)
                g.d.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0,
                          cx + math.cos(a) * rr, cy + math.sin(a) * rr), fill=1)
            if p > 0.5:
                g.d.ellipse((cx - r0, cy - r0, cx + r0, cy + r0), outline=1)
                g.d.ellipse((cx - r0 + 1, cy - r0 + 1, cx + r0 - 1, cy + r0 - 1), fill=0)
        # ---------------- 祥云 + 小道士
        if t < JUMP[0]:
            q = ease_out(span(t, 0, ARRIVE))
            x = lerp(-30, DAO_X - 6, q)
            y = lerp(37, 40, q) - math.sin(q * math.pi) * 2 + math.sin(t * 6) * 1.2
            for k in range(6):  # 灵光拖尾
                tx = x - 18 - k * 7
                ty = y + 5 + math.sin(t * 6 + k) * 2
                if (k + int(t * 20)) % 3 != 0:
                    g.px(tx, ty)
                if k % 2 == 0 and q < 0.98:
                    pix.dotted(g, tx - 5, ty, tx, ty, 2, int(t * 20))
            daoshi(g, x + 2, y, "idle", t, face="happy" if q > 0.9 else "normal")
            pix.blit(g, spr("cloud"), x - 15, y - 2)
        else:
            # 云飘走
            q = span(t, JUMP[0], JUMP[0] + 0.8)
            if q < 1:
                cxx, cyy = lerp(DAO_X - 21, -40, ease_in(q)), lerp(38, 14, q)
                pix.blit(g, spr("cloud"), cxx, cyy)
            if t < land:  # 跃下：先往上一窜，再落下
                k = span(t, JUMP[0], land)
                y = lerp(40, FLOOR, k) - math.sin(k * math.pi) * 12
                x = lerp(DAO_X - 4, DAO_X, k)
                daoshi(g, x, y, "raise", t, face="wow")
            elif t < land + 0.2:  # 单膝落地
                figure(g, DAO_X, FLOOR, t, legs="kneel", arm="point", face="normal")
            elif t < SEAL - 0.1:
                daoshi(g, DAO_X, FLOOR, "gongshou", t, face="happy" if t > TITLE else "normal")
            else:
                daoshi(g, DAO_X, FLOOR, "bow" if t < SEAL + 0.4 else "gongshou", t, face="happy")
        if self.hit(t, land):
            pix.flash(g)
            for s in (-1, 1):
                for k in range(2):
                    self.puffs.emit(DAO_X + s * (8 + k * 5), FLOOR - 2, vx=s * 18, vy=-6, life=0.6, rmax=2.2,
                                    spread=1)
            self.sparks.burst(DAO_X, FLOOR - 2, 18, 45, up=20, life=0.7, gravity=80)
        if land < t < land + 0.25:
            pix.shake(g, t, 2.5 * (1 - span(t, land, land + 0.25)))
        if land <= t < land + 0.3:  # 地面冲击波
            r = span(t, land, land + 0.3) * 40
            for s in (-1, 1):
                x = DAO_X + s * r
                g.d.line((x, FLOOR - 1, x + s * 4, FLOOR - 1), fill=1)
        # ---------------- 标题：字母一个个砸下来
        title = "dao timer"
        if t >= TITLE:
            self.clear(TX - 2, 0, TX + text_width(title) + 2, 17)
            x = TX
            for i, ch in enumerate(title):
                ti = TITLE + i * 0.045
                w = text_width(ch)
                if ch != " " and t >= ti:
                    q = span(t, ti, ti + 0.12)
                    y = 4 - (1 - ease_in(q)) * 4
                    self.say(x, y, ch, plate=False)
                    if self.hit(t, ti + 0.12):
                        self.sparks.burst(x + w / 2, 15, 3, 20, up=10, life=0.3, gravity=60)
                x += w
            p = ease_out(span(t, TITLE + 0.45, TITLE + 0.75))
            if p > 0:
                w = text_width(title)
                g.d.line((TX, 19, TX + (w + 14) * p, 19), fill=1)
                g.d.line((TX, 21, TX + (w + 14) * p * 0.7, 21), fill=1)
            if self.hit(t, TITLE + 0.42):
                pix.shake(g, t, 1.0)
        if t >= REALM:
            s = f"境界 {self.ctx.realm()}"
            m = int(min(1, (t - REALM) * 16 / len(s)) * len(s))
            self.say(TX, 26, s[:m])
        if t >= DAOXING:
            s = f"道行 {self.ctx.completed}"
            m = int(min(1, (t - DAOXING) * 16 / len(s)) * len(s))
            self.say(TX, 41, s[:m])
        if t >= SEAL:  # 落印：从大到小“啪”地盖下
            q = span(t, SEAL, SEAL + 0.15)
            s = pix.stretch(spr("seal"), 1 + (1 - q) * 0.8, 1 + (1 - q) * 0.8)
            pix.blit(g, s, 118 - s.w / 2, 52 - s.h / 2)
            if q >= 1:
                g.text(118, 48, "道", size=8, fill=0, align="center")
            if self.hit(t, SEAL + 0.15):
                pix.shake(g, t, 1.5)
                self.sparks.burst(118, 52, 8, 30, life=0.4, gravity=30)
        self.particles(g)
        if t < ARRIVE and int(t * 10) % 3 == 0:
            star4(g, 120, 6, 1)
        self.flush(g)
        # ---------------- 点阵
        if t < land:
            k = int(t * 10) % 2
            g.mx[3:5, 3:5] = k == 0
            g.mx[3 + k, 3 + k] = True
        elif t < land + 0.35:
            r = span(t, land, land + 0.35) * 6
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 3.5) - r) < 0.7:
                        g.mx[y, x] = True
        else:
            mx_taiji(g, (t - land) * 3)
        g.mx_level = 8 if land <= t < land + 0.12 else 3 if t < land + 0.3 and t > land else 1
