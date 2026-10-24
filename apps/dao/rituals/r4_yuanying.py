"""结丹出神：正面盘坐，三丹田依次点亮——炼精化气（下丹田）、炼气化神（中丹田）、炼神还虚（上丹田），
每成一关头顶开一朵花；三花齐聚，元婴（阳神）从顶门出来坐在莲上，片刻又收回。

依据：内丹“炼精化气、炼气化神、炼神还虚”三关；下丹田脐下、中丹田膻中（绛宫）、上丹田泥丸（两眉间入内）；
“三花聚顶、五气朝元”；功成“出神”，阳神（元婴）自顶门而出（《性命圭旨》有《婴儿现形图》《出离苦海图》）。

入场：圆光一圈圈亮起，人坐定，合目，下丹田点亮。
持续：一转 10 分钟分三关（各 200 秒）：光从下丹田升到中丹田、再到眉间，所到之处越聚越亮，
      身后圆光随之增强；每过一关头顶开一朵花。一转满：元婴从顶门升起，在莲台上坐一坐，再沉回去，花谢重来。
中断：光一路退回下丹田、变暗，“归根”（《道德经》“归根曰静”）。
恢复：下丹田重新亮起，光再升到刚才那一关。
圆满：五团气从四面八方汇入身中（五气朝元），三朵花在头顶并开（三花聚顶），元婴升起放光。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, pulse, rand, span
from ..engine.cn import cn_num
from ..engine.fx import ring, typewriter, xiangyun
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register
from .r4_kit import glow_dot, seated

CX, BASE, S = 64, 62, 0.85
HEAD_Y = BASE - 34 * S
STAGES = ["炼精化气", "炼气化神", "炼神还虚"]
RENEW = 6.0
BABY = Sprite("""
   ###
  #####
  #.#.#
  #####
   ###
 #######
#.#####.#
  #####
 #######
""")


def flower(g: Gfx, x: float, y: float, k: float):
    """一朵五瓣小花，k 0..1 开放程度"""
    if k <= 0:
        return
    r = 1 + 2.2 * ease_out_back(k)
    for i in range(5):
        a = -math.pi / 2 + i * 2 * math.pi / 5
        px, py = x + math.cos(a) * r, y + math.sin(a) * r
        g.d.ellipse((px - 1.2, py - 1.2, px + 1.2, py + 1.2), fill=1)
    g.d.point((x, y), fill=0)
    g.d.line((x, y + r, x, y + r + 2), fill=1)


def lotus_seat(g: Gfx, x: float, y: float, k: float = 1.0):
    w = 8 * k
    for i in range(-2, 3):
        px = x + i * w / 2.5
        g.d.ellipse((px - 2.2 * k, y - 3 * k, px + 2.2 * k, y + 1), fill=1, outline=0)
    g.d.line((x - w, y + 1, x + w, y + 1), fill=1)


@register
class Yuanying(Ritual):
    id = "r4.yuanying"
    name = "结丹出神"
    desc = "正面盘坐，三丹田依次点亮，炼精化气、炼气化神、炼神还虚，三花聚顶，元婴自顶门出而复归"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    # ------------------------------------------------------------ 进度

    def stage(self, e: float) -> tuple[int, float]:
        """→ (第几关 0..2, 关内进度 0..1)"""
        p = (e % self.CYCLE) / self.CYCLE * 3
        i = min(2, int(p))
        return i, p - i

    # ------------------------------------------------------------ 零件

    def halo(self, g: Gfx, level: float, t: float, head):
        hx, hy = head
        for j in range(1 + int(level * 2.99)):
            r = 12 + j * 5 + pulse(t + j, 4.0)
            ring(g, hx, hy, r, 3 - (j == 0 and level > 0.6), t * 0.1 * (1 if j % 2 else -1))

    def clouds(self, g: Gfx, t: float):
        xiangyun(g, 18 + math.sin(t * 0.3) * 2, 56, 1.2)
        xiangyun(g, 110 - math.sin(t * 0.3) * 2, 56, 1.2, flip=True)

    def figure(self, g: Gfx, t: float):
        return seated(g, CX, BASE, S, breath=pulse(t, 6.0))

    def lights(self, g: Gfx, pts: dict, i: int, k: float, t: float, dim: float = 1.0):
        """三丹田的光：已过的关是稳定的亮点，当前关的光在长大；光从下往上流"""
        names = ("lower", "middle", "upper")
        for j in range(3):
            x, y = pts[names[j]]
            top = 1.6 if j == 2 else 2.4   # 眉间的光小一点，别把脸盖住
            if j < i:
                r = top * dim
            elif j == i:
                r = (0.6 + (top + 0.4) * ease_out(k)) * dim
            else:
                g.px(x, y)
                continue
            g.d.ellipse((x - r - 1.5, y - r - 1.5, x + r + 1.5, y + r + 1.5), fill=0)
            glow_dot(g, x, y, r, t)
        if i >= 1 and dim > 0.3:  # 光流：沿中线往上的点
            x0, y0 = pts["lower"]
            x1, y1 = pts[names[i]]
            for s in range(4):
                f = (t * 0.7 + s / 4) % 1.0
                yy = lerp(y0 - 4, y1 + 4, f)
                if abs(yy - pts["middle"][1]) > 3:
                    g.px(x0, yy)

    def flowers(self, g: Gfx, n: int, crown, k_last: float = 1.0, spread: float = 0.0):
        cx, cy = crown
        slots = {1: [0], 2: [-1, 1], 3: [-1, 0, 1]}.get(n, [])
        for j, sx in enumerate(slots):
            x = cx + sx * (9 + spread)
            y = cy - 6 - (3 if sx == 0 else 0)
            flower(g, x, y, k_last if j == n - 1 else 1.0)

    def texts(self, g: Gfx, e: float, left: str | None = None, a: float = 1.0):
        i, k = self.stage(e)
        l = left if left is not None else STAGES[i]
        g.vtext(2, 2, l[:int(round(len(l) * a))])
        n = int(e // self.CYCLE) + 1
        r = f"第{cn_num(n)}转"
        g.vtext(115, 2, r[:int(round(len(r) * a))])

    def mx(self, g: Gfx, i: int, k: float, t: float, dim: float = 1.0):
        rows = (6, 4, 1)
        for j in range(3):
            if j > i:
                g.mx[rows[j], 3:5] = blink(t + j, 2.0, 0.1)
                continue
            lvl = 1.0 if j < i else k
            w = 1 + int(round(lvl * 2 * dim))
            on = j < i or blink(t, 0.8, 0.3 + 0.6 * k)
            g.mx[rows[j], 4 - w:4 + w] = on
            if lvl > 0.6 and dim > 0.5:
                g.mx[rows[j] - 1, 3:5] = on
        g.mx[7, :] = True

    # ------------------------------------------------------------ 阶段

    def hold(self, g: Gfx, t: float, e: float):
        k_cyc = e % self.CYCLE
        if e >= self.CYCLE and k_cyc < RENEW:
            self._renew(g, t, e, k_cyc)
            return
        i, k = self.stage(e)
        self.clouds(g, t)
        self.halo(g, (i + k) / 3, t, (CX, HEAD_Y))
        pts = self.figure(g, t)
        self.lights(g, pts, i, k, t)
        bloom = span(k, 0.0, 0.06)
        self.flowers(g, i, pts["crown"], k_last=bloom)
        self.texts(g, e)
        self.mx(g, i, k, t)

    def _renew(self, g: Gfx, t: float, e: float, k: float):
        """一转满：元婴出顶门，坐莲片刻，复归"""
        self.clouds(g, t)
        self.halo(g, 1.0, t, (CX, HEAD_Y))
        pts = self.figure(g, t)
        self.lights(g, pts, 2, 1.0, t)
        cx, cy = pts["crown"]
        up = ease_out(span(k, 0.4, 2.0)) - ease_in(span(k, 4.0, 5.4))
        wilt = span(k, 3.6, 4.4)
        if wilt < 1:
            self.flowers(g, 2 if up > 0.05 else 3, pts["crown"], spread=up * 6)
            if wilt > 0:
                g.fade(1 - wilt, (cx - 26, 0, cx + 26, int(cy) - 1))
        if up > 0.02:
            by = lerp(cy - 4, 3, up)
            lotus_seat(g, cx, by + BABY.h, k=min(1.0, up * 1.5))
            g.blit(BABY, cx - BABY.w // 2, by)
            if 1.6 < k < 4.0:
                for j in range(8):
                    a = j / 8 * 2 * math.pi + t
                    if blink(t + j * 0.11, 0.5, 0.5):
                        g.px(cx + math.cos(a) * 9, by + 5 + math.sin(a) * 7)
            # 顶门到元婴的一缕光
            for yy in range(int(by + BABY.h + 2), int(cy), 2):
                g.px(cx, yy)
        n = int(e // self.CYCLE)
        self.texts(g, e, left="出神" if k < 4.0 else "收神")
        self.mx(g, 2, 1.0, t)
        if up > 0.3:
            g.mx[0:4, 2:6] = False
            g.mx_blit("..##..\n.####.\n..##..\n######", 1, 0)

    def enter(self, g: Gfx, t: float):
        self.clouds(g, t)
        self.halo(g, span(t, 0, 2.0), t, (CX, HEAD_Y))
        pts = self.figure(g, t)
        k = span(t, 0.0, 1.6)
        if k < 1:
            g.fade(ease_in_out(k), (CX - 24, 0, CX + 24, 64))
        if t > 2.4:
            x, y = pts["lower"]
            glow_dot(g, x, y, 0.8 * ease_out(span(t, 2.4, 3.4)), t)
        self.texts(g, 0, a=span(t, 3.4, 4.5))
        self.mx(g, 0, 0.0, t, dim=span(t, 2.4, 3.4))

    def interrupt(self, g: Gfx, t: float, e: float):
        i, k = self.stage(e)
        r = ease_in_out(span(t, 0, 1.2))
        self.clouds(g, t)
        self.halo(g, (i + k) / 3 * (1 - r), t, (CX, HEAD_Y))
        pts = self.figure(g, t)
        # 光逐关退回下丹田
        level = (i + k) * (1 - r)
        ii, kk = min(2, int(level)), level - min(2, int(level))
        self.lights(g, pts, ii, kk, t, dim=1 - 0.6 * r)
        self.flowers(g, i, pts["crown"])
        if i:
            g.fade(1 - r, (CX - 20, 0, CX + 20, int(pts["crown"][1]) - 1))
        self.texts(g, e, left="归根")
        self.mx(g, ii, kk, t, dim=1 - 0.6 * r)

    def resume(self, g: Gfx, t: float, e: float):
        i, k = self.stage(e)
        r = ease_in_out(span(t, 0.3, 2.0))
        self.clouds(g, t)
        self.halo(g, (i + k) / 3 * r, t, (CX, HEAD_Y))
        pts = self.figure(g, t)
        level = (i + k) * r
        ii, kk = min(2, int(level)), level - min(2, int(level))
        self.lights(g, pts, ii, kk, t, dim=0.4 + 0.6 * span(t, 0, 0.6))
        self.flowers(g, min(i, ii + (1 if kk > 0.99 else 0)), pts["crown"])
        self.texts(g, e, left="归根" if t < 0.5 else None)
        self.mx(g, ii, kk, t)

    def complete(self, g: Gfx, t: float, e: float):
        i, k = self.stage(e)
        self.clouds(g, t)
        self.halo(g, 1.0, t, (CX, HEAD_Y))
        pts = self.figure(g, t)
        self.lights(g, pts, 2, 1.0 if t > 1.5 else k, t)
        mid = pts["middle"]
        if t < 1.6:  # 五气朝元：五团气从五个方向汇入
            for j in range(5):
                a = -math.pi / 2 + j * 2 * math.pi / 5
                f = ease_in(span(t, 0.1 + j * 0.08, 1.4 + j * 0.04))
                r = lerp(60, 0, f)
                x, y = mid[0] + math.cos(a) * r * 1.2, mid[1] + math.sin(a) * r * 0.8
                if f < 1:
                    glow_dot(g, x, y, 2.0, t)
        if 1.3 < t < 1.8:
            ring(g, mid[0], mid[1], 4 + span(t, 1.3, 1.8) * 30, 2)
        # 三花聚顶
        if t > 1.6:
            for j in range(3):
                kk = span(t, 1.6 + j * 0.25, 2.3 + j * 0.25)
                cx, cy = pts["crown"]
                sp = ease_out(span(t, 3.0, 4.0))
                if j == 1:  # 中间那朵托着元婴升上去
                    flower(g, cx, lerp(cy - 9, 3 + BABY.h + 3, sp), kk)
                else:
                    flower(g, cx + (j - 1) * (9 + 10 * sp), cy - 6 + 4 * sp, kk)
        # 元婴升起
        if t > 3.0:
            up = ease_out(span(t, 3.0, 4.5))
            cx, cy = pts["crown"]
            by = lerp(cy - 4, 3, up)
            lotus_seat(g, cx, by + BABY.h, k=min(1.0, up * 1.5))
            g.blit(BABY, cx - BABY.w // 2, by)
            for j in range(12):
                a = j / 12 * 2 * math.pi + t * 0.5
                if blink(t + j * 0.09, 0.5, 0.6):
                    r0, r1 = 9, 12 + 2 * math.sin(t * 5 + j)
                    g.d.line((cx + math.cos(a) * r0, by + 5 + math.sin(a) * r0 * 0.8, cx + math.cos(a) * r1,
                              by + 5 + math.sin(a) * r1 * 0.8), fill=1)
        if t < 1.0:
            self.texts(g, e, a=1 - span(t, 0, 1.0))
        elif t < 2.2:
            g.vtext(2, 2, "五气朝元"[:int(clamp((t - 1.0) * 4) * 4)])
        else:
            g.vtext(2, 2, "三花聚顶"[:int(clamp((t - 2.2) * 4) * 4)])
        # 点阵
        self.mx(g, 2, 1.0, t)
        if t > 3.0:
            g.mx[0:4, :] = False
            g.mx_blit("..##..\n.####.\n..##..\n######", 1, 0)
        g.mx_level = 5 if 1.3 < t < 1.7 or 3.0 < t < 3.4 else 1
