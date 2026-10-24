"""掐诀：左手依次结剑诀、灵官诀、五雷诀、三山诀。

道士行法“手掐诀、脚踏罡、口念咒”，掐诀多用左手（右手执剑、执铃）。手型依据民间道坛流传的诀谱：
  剑诀：食指、中指并伸，拇指压住无名指、小指；
  灵官诀：中指直竖，食指屈来掐中指第一节，拇指相抵；
  五雷诀：四指屈入掌心，拇指压在四指背上，如握拳；
  三山诀：握拳后依次弹出食指、小指、拇指。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.fx import flame, lightning, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r3_kit import capsule, nth, ocapsule, round_of, side_text, sleeve, sparkle

CX = 64
LEN = (17, 21, 19, 14)          # 食、中、无名、小指伸直的长度
FX = (-9, -3, 3, 9)             # 四指根部相对掌心的 x
# 诀：四指 (伸展 0..1, 偏角)，拇指尖相对 (CX, 掌顶) 的位置
OPEN = {"f": ((1, -0.12), (1, -0.03), (1, 0.05), (1, 0.16)), "th": (-22, -2)}
SEALS = [
    ("剑诀", {"f": ((1, 0.02), (1, -0.02), (0, 0), (0, 0)), "th": (7, 7)}),
    ("灵官诀", {"f": ((0.5, 0.42), (1, 0), (0, 0), (0, 0)), "th": (-4, -9)}),
    ("五雷诀", {"f": ((0, 0), (0, 0), (0, 0), (0, 0)), "th": (6, 3)}),
    ("三山诀", {"f": ((1, -0.1), (0, 0), (0, 0), (1, 0.12)), "th": (-21, -1)}),
]
EACH = 150.0                    # 每个诀持续的秒数
MORPH = 1.4                     # 换诀的过渡秒数


def mix(a: dict, b: dict, p: float) -> dict:
    p = ease_in_out(p)
    f = tuple((lerp(fa[0], fb[0], p), lerp(fa[1], fb[1], p)) for fa, fb in zip(a["f"], b["f"]))
    th = (lerp(a["th"][0], b["th"][0], p), lerp(a["th"][1], b["th"][1], p))
    return {"f": f, "th": th}


def hand(g: Gfx, cx: float, y0: float, pose: dict, arm: bool = True):
    """左手，掌心朝外，拇指在画面左侧。y0 = 掌顶"""
    if arm:
        sleeve(g, cx + 1, y0 + 30, math.pi / 2, length=30, w0=20, w1=44, shade=0.25)
        g.d.rectangle((cx - 9, y0 + 20, cx + 10, y0 + 31), fill=0, outline=1)  # 手腕
    # 手掌
    g.d.rounded_rectangle((cx - 13, y0, cx + 13, y0 + 24), radius=5, fill=0, outline=1)
    g.d.arc((cx - 9, y0 + 8, cx + 15, y0 + 30), 200, 250, fill=1)  # 掌纹
    g.d.line((cx - 3, y0 + 13, cx + 7, y0 + 11), fill=1)
    # 四指：从小指到食指（食指盖在前面）
    for i in (3, 2, 1, 0):
        ext, tilt = pose["f"][i]
        bx, by = cx + FX[i], y0 + 4
        ln = 3 + (LEN[i] - 3) * ext
        tx, ty = bx + math.sin(tilt) * ln, by - math.cos(tilt) * ln
        ocapsule(g, bx, by, tx, ty, 7)
        if ext > 0.45:  # 指节纹
            for k in (0.42, 0.72):
                jx, jy = bx + (tx - bx) * k, by + (ty - by) * k
                g.d.line((jx - 1, jy, jx + 1, jy), fill=1)
        else:           # 屈入掌心：看得见指尖
            a = 1 - ext / 0.45
            g.d.rounded_rectangle((bx - 2, y0 + 5 + 3 * a, bx + 2, y0 + 8 + 3 * a), radius=1, outline=1, fill=0)
    # 掌顶的手指根部缝
    g.d.line((cx - 12, y0 + 4, cx + 12, y0 + 4), fill=0)
    # 拇指
    rx, ry = cx - 11, y0 + 18
    tx, ty = cx + pose["th"][0], y0 + pose["th"][1]
    mx, my = lerp(rx, tx, 0.45) - 3, lerp(ry, ty, 0.45) + 1   # 拇指根的鱼际
    ocapsule(g, rx, ry, mx, my, 9)
    ocapsule(g, mx, my, tx, ty, 7)
    g.d.ellipse((mx - 2.5, my - 2.5, mx + 2.5, my + 2.5), fill=0)
    jx, jy = lerp(mx, tx, 0.5), lerp(my, ty, 0.5)
    g.d.point((jx, jy))


@register
class HandSeal(Ritual):
    id = "r3.shoujue"
    name = "掐诀"
    desc = "左手依次结剑诀、灵官诀、五雷诀、三山诀，每诀各有气象，气圈随时间合拢"
    T = {"enter": 3.2, "interrupt": 1.4, "resume": 1.6, "complete": 5.0}
    CYCLE = EACH * 4
    Y0 = 34

    # ------------------------------------------------------------ 零件

    def pose_at(self, e: float) -> tuple[int, dict, float]:
        """→ (第几诀, 手型, 本诀进度)"""
        n, k, _ = round_of(e, self.CYCLE)
        i = min(3, int(k // EACH))
        kk = k - i * EACH
        cur = SEALS[i][1]
        if kk < MORPH and not (i == 0 and n == 1):
            prev = SEALS[i - 1][1] if i > 0 else OPEN
            return i, mix(prev, cur, kk / MORPH), kk / EACH
        return i, cur, kk / EACH

    def formed(self, e: float) -> float:
        """本诀结成后气象显现的程度"""
        n, k, _ = round_of(e, self.CYCLE)
        i = min(3, int(k // EACH))
        if i == 0 and n == 1:
            return 1.0
        return span(k - i * EACH, MORPH * 0.7, MORPH * 0.7 + 0.8)

    def aura(self, g: Gfx, i: int, t: float, a: float = 1.0, y0: float | None = None):
        """每个诀的气象（画在手前后）"""
        y0 = self.Y0 if y0 is None else y0
        if a <= 0:
            return
        if i == 0:  # 剑诀：指尖剑气直冲
            top = y0 + 4 - 24
            x = CX - 6
            tip = top - (top + 2) * a
            g.d.polygon([(x - 4, top), (x - 4, lerp(top, tip, 0.8)), (x, tip), (x + 4, lerp(top, tip, 0.8)),
                         (x + 4, top)], outline=1, fill=0)
            for j in range(3):  # 剑气流光
                yy = top - ((t * 50 + j * 11) % max(top - tip, 1))
                g.d.line((x, yy, x, yy - 4), fill=1)
            if blink(t, 0.4, 0.5):
                sparkle(g, x, tip - 1, 2)
        elif i == 1:  # 灵官诀：中指尖一团灵官火
            flame(g, CX - 3, y0 + 4 - 22, 6 * a, 11 * a, t, self.seed)
        elif i == 2:  # 五雷诀：拳上雷光
            if a > 0.5 and int(t * 8) % 3 != 0:
                s = int(t * 8)
                ang = rand(s, self.seed) * math.pi - math.pi
                r0, r1 = 15, 15 + 14 * a
                lightning(g, CX + math.cos(ang) * r0, y0 + 10 + math.sin(ang) * r0 * 0.8,
                          CX + math.cos(ang) * r1, y0 + 10 + math.sin(ang) * r1 * 0.8, s * 13 + self.seed,
                          jag=2, branches=0)
        else:  # 三山诀：身后三座山
            pass

    def mountains(self, g: Gfx, a: float, y0: float):
        if a <= 0:
            return
        base = 64
        for j, (x, h) in enumerate(((CX - 34, 22), (CX, 34), (CX + 34, 22))):
            hh = h * ease_out(clamp(a * 1.4 - j * 0.2))
            if hh <= 0:
                continue
            g.d.line((x - 18, base, x, base - hh, x + 18, base), fill=1)
            g.d.line((x - 4, base - hh + 6, x, base - hh + 3, x + 3, base - hh + 7), fill=1)

    def ring(self, g: Gfx, p: float, t: float, cy: float = 34):
        """气圈：随本诀进度合拢"""
        n = 56
        m = int(n * clamp(p))
        for j in range(m):
            a = -math.pi / 2 + j / n * 2 * math.pi
            x, y = CX + math.cos(a) * 44, cy + math.sin(a) * 27
            if j == m - 1 and blink(t, 0.5):
                sparkle(g, x, y, 1)
            else:
                g.px(x, y)

    def mx_hand(self, g: Gfx, pose: dict, lit: float = 1.0):
        g.mx[6:8, 2:7] = True
        for i, (ext, _) in enumerate(pose["f"]):
            col = 3 + i
            h = int(round(ext * 4))
            for r in range(5, 5 - h, -1):
                g.mx[r, col] = True
            if h == 0:
                g.mx[5, col] = True
        out = pose["th"][0] < -10
        if out:
            g.mx_set(1, 5)
            g.mx_set(0, 4)
        else:
            g.mx_set(1, 6)
        g.mx[7, 2:7] = True

    def labels(self, g: Gfx, i: int, e: float, a: float = 1.0, right: str | None = None):
        side_text(g, 3, 3, SEALS[i][0], a)
        n = int(e // self.CYCLE) + 1
        side_text(g, 113, 3, right if right is not None else nth(n, "遍"), a)

    def scene(self, g: Gfx, t: float, e: float, pose: dict | None = None, aura: float = 1.0, ring: bool = True,
              y0: float | None = None, right: str | None = None):
        i, p0, prog = self.pose_at(e)
        pose = pose or p0
        y0 = self.Y0 if y0 is None else y0
        if i == 3:
            self.mountains(g, aura * clamp(prog * EACH / 2.0), y0)
        if ring:
            self.ring(g, prog, t)
        hand(g, CX, y0, pose)
        a = aura * self.formed(e)
        self.aura(g, i, t, a, y0)
        self.labels(g, i, e, right=right)
        self.mx_hand(g, pose)
        if i == 2 and int(t * 8) % 3 and a > 0.5:
            g.mx_set(0, 0, blink(t, 0.25))
            g.mx_set(7, 0, not blink(t, 0.25))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        rise = ease_out_back(span(t, 0, 1.2))
        y0 = lerp(70, self.Y0, rise)
        fold = span(t, 1.5, 2.6)
        pose = mix(OPEN, SEALS[0][1], fold)
        hand(g, CX, y0, pose)
        if t > 2.6:
            self.aura(g, 0, t, ease_out(span(t, 2.6, 3.2)))
        side_text(g, 3, 3, "剑诀", span(t, 2.4, 3.0))
        side_text(g, 113, 3, nth(1, "遍"), span(t, 2.4, 3.0))
        self.mx_hand(g, pose)
        g.mx_level = 4 if 2.55 < t < 2.75 else 1

    def hold(self, g: Gfx, t: float, e: float):
        n, k, _ = round_of(e, self.CYCLE)
        if n > 1 and k < 3.0:
            self._renew(g, k, e)
            return
        self.scene(g, t, e)

    def _renew(self, g: Gfx, k: float, e: float):
        """四诀走完：甩手散诀（手张开一抖），再结剑诀"""
        if k < 1.6:
            p = span(k, 0, 0.5)
            pose = mix(SEALS[3][1], OPEN, p)
            shake = math.sin(k * 30) * 3 * (1 - span(k, 0.5, 1.6)) if k > 0.4 else 0
            hand(g, CX + shake, self.Y0 + 2 * span(k, 0, 0.5), pose)
            for j in range(6):  # 甩出的余气
                if 0.4 < k < 1.4:
                    a = rand(j, self.seed) * math.pi + math.pi
                    r = 20 + (k - 0.4) * 40
                    g.px(CX + math.cos(a) * r * 1.3, self.Y0 + 10 + math.sin(a) * r * 0.7)
            side_text(g, 3, 3, "散诀")
            side_text(g, 113, 3, nth(int(e // self.CYCLE) + 1, "遍"))
            self.mx_hand(g, pose)
        else:
            p = span(k, 1.6, 3.0)
            pose = mix(OPEN, SEALS[0][1], p)
            hand(g, CX, self.Y0 + 2 * (1 - p), pose)
            side_text(g, 3, 3, "剑诀", p * 2)
            side_text(g, 113, 3, nth(int(e // self.CYCLE) + 1, "遍"))
            self.mx_hand(g, pose)

    def interrupt(self, g: Gfx, t: float, e: float):
        i, pose, prog = self.pose_at(e)
        p = span(t, 0, 0.8)
        y0 = self.Y0 + 8 * ease_in_out(span(t, 0.5, 1.4))
        if i == 3:
            self.mountains(g, 1 - p, y0)
        self.ring(g, prog * (1 - p), t)
        cur = mix(pose, OPEN, p)
        hand(g, CX, y0, cur)
        self.aura(g, i, t, 1 - span(t, 0, 0.4), y0)
        side_text(g, 3, 3, SEALS[i][0] if t < 0.6 else "松诀")
        side_text(g, 113, 3, nth(int(e // self.CYCLE) + 1, "遍") if t < 0.6 else "暂歇")
        self.mx_hand(g, cur)

    def resume(self, g: Gfx, t: float, e: float):
        i, pose, prog = self.pose_at(e)
        y0 = self.Y0 + 8 * (1 - ease_out(span(t, 0, 0.7)))
        p = span(t, 0.5, 1.4)
        cur = mix(OPEN, pose, p)
        if i == 3:
            self.mountains(g, span(t, 1.0, 1.6) * clamp(prog * EACH / 2.0), y0)
        self.ring(g, prog * span(t, 0.8, 1.6), t)
        hand(g, CX, y0, cur)
        self.aura(g, i, t, span(t, 1.3, 1.6) * self.formed(e), y0)
        self.labels(g, i, e)
        self.mx_hand(g, cur)
        g.mx_level = 4 if 1.35 < t < 1.5 else 1

    def complete(self, g: Gfx, t: float, e: float):
        i, pose, _ = self.pose_at(e)
        # 0–2.4：四诀快速连掐一遍；2.4–3.2：握诀收于掌中；之后放光
        if t < 2.4:
            j = min(3, int(t / 0.6))
            kk = (t - j * 0.6) / 0.6
            prev = pose if j == 0 else SEALS[j - 1][1]
            cur = mix(prev, SEALS[j][1], clamp(kk / 0.4))
            if j == 3:
                self.mountains(g, clamp(kk * 2), self.Y0)
            hand(g, CX, self.Y0, cur)
            self.aura(g, j, t, clamp((kk - 0.35) * 3))
            side_text(g, 3, 3, SEALS[j][0])
            self.mx_hand(g, cur)
            g.mx_level = 5 if kk > 0.4 and kk < 0.5 else 1
            if kk > 0.4 and kk < 0.55:  # 每结成一诀闪一下
                for q in range(8):
                    a = q / 8 * 2 * math.pi
                    g.d.line((CX + math.cos(a) * 30, 34 + math.sin(a) * 20, CX + math.cos(a) * 38,
                              34 + math.sin(a) * 25), fill=1)
            return
        p = span(t, 2.4, 3.0)
        y0 = self.Y0 + 6 * ease_in_out(span(t, 2.4, 3.2))
        cur = mix(SEALS[3][1], SEALS[2][1], p)
        hand(g, CX, y0, cur)
        if t > 3.0:
            r = ease_out(span(t, 3.0, 4.2))
            for q in range(14):
                a = q / 14 * 2 * math.pi + t * 0.5
                r0, r1 = 24 + 16 * r, 28 + 22 * r
                g.d.line((CX + math.cos(a) * r0 * 1.4, 30 + math.sin(a) * r0 * 0.7, CX + math.cos(a) * r1 * 1.4,
                          30 + math.sin(a) * r1 * 0.7), fill=1)
            g.d.rectangle((CX - 30, 1, CX + 30, 14), fill=0)
            typewriter(g, CX, 2, "道法自然", t - 3.1, cps=5, align="center")
        self.mx_hand(g, cur)
        if t > 3.0:
            rr = (t - 3.0) * 4
            for y in range(8):
                for x in range(8):
                    if abs(math.hypot(x - 3.5, y - 5) - rr) < 0.7:
                        g.mx[y, x] = True
            g.mx_level = 1 + int(5 * (1 - span(t, 3.0, 4.5)))
