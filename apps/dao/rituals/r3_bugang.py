"""步罡踏斗：俯视罡单，一双云履按禹步依次踏上北斗七星与辅、弼二星（三步九迹），踏到哪颗哪颗亮。

步罡踏斗源于“禹步”，道士在铺开的罡单（星图）上按星位行步，配合掐诀念咒，以“步天”通神。
禹步之法“步不相过”：前脚迈出，后脚跟上并拢，再迈下一步。北斗七星：天枢、天璇、天玑、天权、玉衡、开阳、摇光，
星君名贪狼、巨门、禄存、文曲、廉贞、武曲、破军；加左辅、右弼二隐星合为九星，对应“三步九迹”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import ring, stars, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r3_kit import round_of, side_text, sparkle

POS = [(10, 11), (8, 37), (31, 46), (35, 21), (54, 16), (73, 21), (78, 6), (94, 42), (100, 23)]
#       天枢     天璇     天玑      天权      玉衡      开阳      辅        摇光      弼
NAMES = [("天枢", "贪狼"), ("天璇", "巨门"), ("天玑", "禄存"), ("天权", "文曲"), ("玉衡", "廉贞"), ("开阳", "武曲"),
         ("辅星", "左辅"), ("摇光", "破军"), ("弼星", "右弼")]
EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (3, 4), (4, 5), (5, 7)]   # 北斗连线（辅、弼不连）
MXP = [(1, 0), (0, 4), (2, 6), (3, 2), (4, 1), (5, 2), (5, 0), (7, 6), (7, 3)]
SOLE = [(0.5, -7), (2.5, -6), (3.5, -2.5), (3, 1), (2.5, 5), (1, 7), (-1, 7), (-2.5, 5), (-2.5, 1), (-3, -2.5),
        (-2, -6)]
STEP_ANIM = 1.6
RENEW = 4.0


def foot(g: Gfx, x: float, y: float, lifted: float = 0.0, left: bool = True):
    """一只云履（俯视，脚尖朝上）。lifted 0..1：抬起时放大并在地上留影"""
    s = 1 + 0.25 * lifted
    sx = 1 if left else -1
    if lifted > 0.05:  # 地上的影子
        for px, py in SOLE:
            g.px(x + px * sx + 1, y + py + 2)
    ox, oy = x - lifted, y - lifted * 4
    pts = [(ox + px * s * sx, oy + py * s) for px, py in SOLE]
    g.d.polygon(pts, fill=1, outline=1)
    # 鞋口与云头纹（挖暗）
    g.d.ellipse((ox - 1.5 * s + 0.5 * sx, oy + 0 * s, ox + 1.5 * s + 0.5 * sx, oy + 5 * s), fill=0)
    g.d.line((ox - 1 * s, oy - 4 * s, ox + 1 * s, oy - 4 * s), fill=0)


@register
class PaceDipper(Ritual):
    id = "r3.bugang"
    name = "步罡踏斗"
    desc = "俯视罡单，一双云履按禹步依次踏上北斗七星与辅弼二星，踏到哪颗哪颗亮，九迹走完回罡再起"
    T = {"enter": 3.6, "interrupt": 1.3, "resume": 1.5, "complete": 5.5}
    CYCLE = 630.0
    STEP = 630.0 / 9

    # ------------------------------------------------------------ 零件

    def where(self, e: float) -> tuple[int, float]:
        """→ (当前站在 / 正走向第几星, 这一步的动画秒数)"""
        _, k, _ = round_of(e, self.CYCLE)
        j = min(8, int(k // self.STEP))
        return j, k - j * self.STEP

    def board(self, g: Gfx, lit: int, t: float, show: float = 1.0, glow_cur: int = -1, path: int | None = None):
        """罡单：星位 + 北斗连线；lit = 已踏亮几颗；path = 已走过的路径画实线"""
        stars(g, t, seed=3, n=14, box=(0, 0, 108, 64), twinkle=0.45)
        path = lit if path is None else path
        for a, b in EDGES:
            if b >= show * 9 or a >= show * 9:
                continue
            (x0, y0), (x1, y1) = POS[a], POS[b]
            n = int(math.hypot(x1 - x0, y1 - y0) / 3)
            for i in range(1, n):
                g.px(lerp(x0, x1, i / n), lerp(y0, y1, i / n))
        for j in range(1, min(path, 9)):  # 走过的罡步：实线
            (x0, y0), (x1, y1) = POS[j - 1], POS[j]
            g.d.line((x0, y0, x1, y1), fill=1)
        for j, (x, y) in enumerate(POS):
            if j >= show * 9:
                break
            r = 3 if j not in (6, 8) else 2
            if j < lit:
                g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
                if noise(t * 1.5 + j * 2.1, 4) > 0.78 or j == glow_cur:
                    sparkle(g, x, y, r + 2)
            else:
                g.d.ellipse((x - r, y - r, x + r, y + r), fill=0, outline=1)

    def feet(self, g: Gfx, j: int, u: float, prev: int | None = None):
        """站在第 j 星（u < STEP_ANIM 时正从上一星迈过来）"""
        left_leads = j % 2 == 0
        x1, y1 = POS[j]
        p_ = prev if prev is not None else max(j - 1, 0)
        x0, y0 = POS[p_] if j > 0 or prev is not None else (POS[0][0] - 14, 70)
        lead_p = ease_in_out(span(u, 0, 0.7))
        trail_p = ease_in_out(span(u, 0.8, 1.4))
        lead_lift = math.sin(lead_p * math.pi)
        trail_lift = math.sin(trail_p * math.pi)
        lx, ly = lerp(x0, x1, lead_p), lerp(y0, y1, lead_p)
        tx, ty = lerp(x0, x1, trail_p), lerp(y0, y1, trail_p)
        dl = -4 if left_leads else 4
        foot(g, tx - dl, ty + 1, trail_lift, left=not left_leads)
        foot(g, lx + dl, ly + 1, lead_lift, left=left_leads)
        if 0.7 <= u < 1.3:  # 落脚激起一圈
            ring(g, x1, y1, 4 + (u - 0.7) * 16, 2)

    def label(self, g: Gfx, j: int, a: float = 1.0, override: tuple | None = None):
        top, bot = override or NAMES[j]
        side_text(g, 114, 2, top, a)
        side_text(g, 114, 38, bot, a)
        if a >= 1:
            g.d.line((116, 30, 124, 30), fill=1)

    def mx(self, g: Gfx, lit: int, cur: int, t: float):
        for j, (x, y) in enumerate(MXP):
            if j < lit and j != cur:
                g.mx_set(x, y)
            elif j == cur:
                g.mx_set(x, y, blink(t, 0.8, 0.6))
            else:  # 未踏的星：偶尔一闪
                g.mx_set(x, y, blink(t + j * 0.37, 2.2, 0.12))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self.board(g, 1 if t > 3.0 else 0, t, show=span(t, 0, 1.6), path=0)
        if t > 1.4:
            u = (t - 1.4) / 2.0 * STEP_ANIM
            self.feet(g, 0, u)
        self.label(g, 0, span(t, 2.6, 3.4))
        self.mx(g, 1 if t > 3.0 else 0, 0, t)
        g.mx_level = 4 if 2.9 < t < 3.1 else 1

    def hold(self, g: Gfx, t: float, e: float):
        n, k, _ = round_of(e, self.CYCLE)
        if n > 1 and k < RENEW:
            self._renew(g, k, t)
            return
        j, u = self.where(e)
        landed = u >= 0.7 or (j == 0)
        lit = j + (1 if landed else 0)
        self.board(g, lit, t, glow_cur=j if landed and u < 3 else -1)
        if j == 0 and n == 1:
            u = max(u, STEP_ANIM)
        self.feet(g, j, u)
        self.label(g, j)
        self.mx(g, lit, j, t)
        g.mx_level = 4 if 0.7 <= u < 0.9 else 1

    def _renew(self, g: Gfx, k: float, t: float):
        """九迹走完：回罡 —— 双脚一跳一星倒着退回天枢，星一颗颗熄灭"""
        p = span(k, 0.2, RENEW - 0.4)
        f = p * 8
        i = min(7, int(f))
        frac = f - i
        a, b = 8 - i, 7 - i
        lit = b + 1 if frac > 0.6 else a + 1
        self.board(g, lit, t, path=lit)
        x0, y0 = POS[a]
        x1, y1 = POS[b]
        q = ease_in_out(frac)
        hop = math.sin(q * math.pi)
        x, y = lerp(x0, x1, q), lerp(y0, y1, q)
        foot(g, x - 4, y + 1, hop, True)
        foot(g, x + 4, y + 1, hop, False)
        self.label(g, 0, override=("回罡", "复始"))
        self.mx(g, lit, -1, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        j, u = self.where(e)
        lit = j + 1 if u >= 0.7 or j == 0 else j
        u = max(u, STEP_ANIM)
        self.board(g, lit, t)
        g.fade(1 - 0.45 * span(t, 0.2, 1.1), (0, 0, 108, 64))
        self.feet(g, j, u)
        self.label(g, j, override=("住罡", "暂歇") if t > 0.5 else None)
        self.mx(g, lit, -1, t)

    def resume(self, g: Gfx, t: float, e: float):
        j, u = self.where(e)
        lit = j + 1 if u >= 0.7 or j == 0 else j
        uu = max(u, STEP_ANIM)
        self.board(g, lit, t)
        if t < 1.0:
            g.fade(0.55 + 0.45 * span(t, 0, 1.0), (0, 0, 108, 64))
        self.feet(g, j, uu)
        if 0.6 < t < 1.2:
            x, y = POS[j]
            ring(g, x, y, 4 + (t - 0.6) * 20, 2)
        self.label(g, j)
        self.mx(g, lit, j, t)

    def complete(self, g: Gfx, t: float, e: float):
        j0, u = self.where(e)
        j0 = j0 + (1 if u >= 0.7 or j0 == 0 else 0) - 1
        left = 8 - j0
        if t < 2.4 and left > 0:
            # 余下的星位快步踏完
            per = 2.4 / left
            i = min(left - 1, int(t / per))
            j = j0 + 1 + i
            uu = (t - i * per) / per * STEP_ANIM
            lit = j + (1 if uu >= 0.7 else 0)
            self.board(g, lit, t, glow_cur=j)
            self.feet(g, j, uu)
            self.label(g, j)
            self.mx(g, lit, j, t)
            g.mx_level = 4 if 0.7 <= uu < 1.0 else 1
            return
        # 九星齐亮，北斗绕天枢转动：斗转星移
        r = -ease_in_out(span(t, 2.4, 4.0)) * 0.25
        cx, cy = 54, 26
        pts = []
        for x, y in POS:
            dx, dy = x - cx, y - cy
            pts.append((cx + dx * math.cos(r) - dy * math.sin(r), cy + dx * math.sin(r) + dy * math.cos(r)))
        stars(g, t, seed=3, n=14, box=(0, 0, 108, 64), twinkle=0.45)
        for a, b in EDGES:
            g.d.line((pts[a], pts[b]), fill=1)
        for jj, (x, y) in enumerate(pts):
            rr = 3 if jj not in (6, 8) else 2
            g.d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=1)
            if blink(t + jj * 0.11, 0.4, 0.5):
                sparkle(g, x, y, rr + 2)
        if t > 3.0:
            g.d.rectangle((58, 48, 110, 62), fill=0)
            typewriter(g, 84, 50, "斗转星移", t - 3.0, cps=5, align="center")
        side_text(g, 114, 2, "九迹")
        side_text(g, 114, 38, "圆满")
        g.d.line((116, 30, 124, 30), fill=1)
        for x, y in MXP:
            g.mx_set(x, y)
        g.mx_level = 1 + int(5 * (1 - span(t, 2.4, 4.0)))
