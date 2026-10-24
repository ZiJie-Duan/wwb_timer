"""金光神咒：道人盘坐持诵，《金光神咒》一句句浮现，身后金光随着诵念一层层亮起来。

依据：道教八大神咒之一《金光神咒》（正一日诵早晚课本）：“天地玄宗，万炁本根……金光速现，覆护真人。”
早晚课本作“万炁本根”“广修亿劫”“惟道独尊”，《太上三洞神咒》作“万气之根”。字库无“炁”的 12px 字形，
“五炁腾腾”按通行异文写作“五气腾腾”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import lightning, ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from ..engine.gfx import Sprite
from .r2_common import rays

# 字库 12px 没有“炁”（上“无”下“灬”），手绘一个 12px 格子的
QI = Sprite("""
 #########
     #
############
    # #
   #  #
  #   #   #
 #     ###
##
 #  #  #  #
#   #   #  #
""")

PHRASES = ["天地玄宗", "万炁本根", "广修亿劫", "证吾神通", "三界内外", "惟道独尊", "体有金光", "覆映吾身",
           "视之不见", "听之不闻", "包罗天地", "养育群生", "受持万遍", "身有光明", "三界侍卫", "五帝司迎",
           "万神朝礼", "役使雷霆", "鬼妖丧胆", "精怪亡形", "内有霹雳", "雷神隐名", "洞慧交彻", "五气腾腾",
           "金光速现", "覆护真人"]
# 12px 字库没有“炁”：第二句用 8px 的炁替换显示（见 phrase_text）
SLOT = 21.0
LAST = "急急如律令"
CX, HY = 34, 20          # 道人中心、头部中心
RENEW = 3.0
TX = 98                  # 右侧文字中心


@register
class JinGuang(Ritual):
    id = "r2.jinguang"
    name = "金光神咒"
    desc = "道人盘坐诵《金光神咒》，咒句逐字浮现，身后金光一层层亮起；念到“金光速现”光芒大放，一遍念完再起一遍"
    T = {"enter": 3.5, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = SLOT * len(PHRASES) + 28.0   # 574 秒一遍

    def setup(self):
        self.s = self.rng.randrange(1000)

    # ------------------------------------------------------------ 零件

    def daoist(self, g: Gfx, glow: float = 0.0, eyes_open: bool = False):
        cx = CX
        g.d.ellipse((cx - 23, 56, cx + 23, 63), fill=0, outline=1)       # 蒲团
        for x in range(cx - 18, cx + 19, 4):
            g.px(x, 59)
            g.px(x + 2, 61)
        g.d.ellipse((cx - 22, 47, cx + 22, 59), fill=0, outline=1)       # 盘起的腿
        robe = [(cx - 6, 28), (cx + 6, 28), (cx + 14, 36), (cx + 19, 52), (cx - 19, 52), (cx - 14, 36)]
        g.d.polygon(robe, fill=0)
        g.shade_poly(robe, 0.25)
        g.d.line((cx - 6, 28, cx, 38), fill=0, width=3)                  # 交领
        g.d.line((cx + 6, 28, cx - 1, 39), fill=0, width=3)
        g.d.line((cx - 6, 28, cx, 38), fill=1)
        g.d.line((cx + 6, 28, cx - 1, 39), fill=1)
        g.d.line((cx - 13, 36, cx - 9, 46), fill=1)                      # 两袖
        g.d.line((cx + 13, 36, cx + 9, 46), fill=1)
        g.d.ellipse((cx - 8, 43, cx + 8, 51), fill=0, outline=1)         # 拱手于丹田
        g.d.line((cx - 4, 47, cx + 4, 47), fill=1)
        g.d.rectangle((cx - 2, 26, cx + 2, 29), fill=0, outline=1)       # 颈
        g.d.ellipse((cx - 6, 12, cx + 6, 27), fill=0, outline=1)         # 头
        g.d.ellipse((cx - 3, 6, cx + 3, 12), fill=1)                     # 发髻
        g.d.line((cx - 6, 9, cx + 6, 8), fill=1)                         # 簪
        g.d.line((cx - 6, 14, cx + 6, 14), fill=1)                       # 发际
        if eyes_open:
            g.d.rectangle((cx - 4, 18, cx - 2, 19), fill=1)
            g.d.rectangle((cx + 2, 18, cx + 4, 19), fill=1)
        else:
            g.d.line((cx - 4, 19, cx - 2, 19), fill=1)
            g.d.line((cx + 2, 19, cx + 4, 19), fill=1)
        g.d.line((cx, 21, cx, 22), fill=1)
        g.d.line((cx - 1, 24, cx + 1, 24), fill=1)
        if glow > 0:  # 眉心一点光
            g.px(cx, 16)

    def aura(self, g: Gfx, level: float, t: float):
        """身后金光：level 0..1"""
        if level <= 0.01:
            return
        n = 8 + int(level * 10) * 2
        r1 = 15 + level * 21
        ph = t * 0.15
        for i in range(n):
            a = ph + i / n * 2 * math.pi
            ca, sa = math.cos(a), math.sin(a)
            # 光往外流动：虚线相位随 t 走
            off = (t * 14 + i * 3) % 6
            r = 13 + off
            while r < r1:
                r2 = min(r + 3, r1)
                g.d.line((CX + ca * r, HY + 6 + sa * r * 0.95, CX + ca * r2, HY + 6 + sa * r2 * 0.95), fill=1)
                r += 6
        if level > 0.25:  # 头光
            ring(g, CX, HY, 10 + math.sin(t * 2) * 0.5, 1)
        if level > 0.55:  # 身光
            for i in range(0, 64, 2):
                a = i / 64 * 2 * math.pi + t * 0.3
                g.px(CX + math.cos(a) * 25, 38 + math.sin(a) * 25)

    def phrase_text(self, g: Gfx, s: str, y: int, n: int | None = None):
        """居中写一句（4 字），n = 显示几个字；炁字用 8px 放在 12px 的格子里"""
        n = len(s) if n is None else n
        w = 12 * len(s) + (len(s) - 1)
        x0 = TX - w / 2
        for i, ch in enumerate(s[:n]):
            x = x0 + i * 13
            if ch == "炁":
                g.blit(QI, x, y + 1)
            else:
                g.text(x, y, ch)

    def counter(self, g: Gfx, n: int):
        g.text(TX, 51, f"第{cn_num(n)}遍", align="center")

    def prev_text(self, g: Gfx, s: str):
        """上一句：8px 小字，放在上面"""
        g.text(TX, 8, s, size=8, align="center")

    def level(self, u: float) -> float:
        i = u / SLOT
        return clamp(i / (len(PHRASES) - 2)) ** 0.8

    def mx_sun(self, g: Gfx, level: float, t: float, burst: float = 0.0):
        g.mx[3:5, 3:5] = True
        r = 1.5 + level * 2.5 + burst * 3
        for i in range(8):
            a = i / 8 * 2 * math.pi + t * 0.8
            for k in range(2, int(r) + 1):
                if (k + int(t * 4)) % 2 == 0 or k <= 2:
                    g.mx_set(round(3.5 + math.cos(a) * k), round(3.5 + math.sin(a) * k))

    def fx(self, g: Gfx, idx: int, k: float, t: float):
        """有些句子有专门的小特效。k = 本句经过秒数"""
        if idx in (17, 20, 21):  # 雷霆、霹雳
            for j in range(3):
                t0 = 2.5 + j * 5.5 + rand(idx * 3 + j, self.s) * 2
                if t0 < k < t0 + 0.25:
                    x = 4 + rand(idx * 7 + j, self.s) * 50
                    lightning(g, x, 0, x + 6, 10 + rand(j, idx) * 6, seed=idx * 10 + j, jag=3, branches=1)
                    g.mx_level = 6
        if idx in (18, 19):  # 鬼妖丧胆：一只小鬼从左边探头，被金光照散
            p = span(k, 2, 7)
            if 0 < p < 1:
                x = lerp(-8, 6, ease_out(min(p * 1.6, 1)))
                y = 36 + math.sin(k * 3) * 2
                if p < 0.7:
                    g.d.ellipse((x - 3, y - 4, x + 3, y + 2), fill=0, outline=1)
                    g.d.polygon([(x - 3, y), (x + 3, y), (x + 2, y + 5), (x, y + 3), (x - 2, y + 5)], outline=1)
                    g.px(x - 1, y - 2)
                    g.px(x + 1, y - 2)
                else:
                    for j in range(8):
                        f = (p - 0.7) / 0.3
                        a = j / 8 * 2 * math.pi
                        g.px(x + math.cos(a) * f * 8, y + math.sin(a) * f * 6)
        if idx == 24 and k < 2.0:  # 金光速现
            r = k * 40
            rays(g, CX, HY + 6, r, r + 8, 20, phase=0.1)
            if k < 0.12:
                g.invert()

    # ------------------------------------------------------------ 阶段

    def body(self, g: Gfx, t: float, u: float, e: float, aura: float | None = None, text_a: float = 1.0):
        lv = self.level(u) if aura is None else aura
        self.aura(g, lv, t)
        self.daoist(g, glow=lv)
        idx = int(u // SLOT)
        if idx < len(PHRASES):
            k = u - idx * SLOT
            n = int(clamp(k / 0.4, 0, 4))
            if text_a > 0:
                if idx > 0:
                    self.prev_text(g, PHRASES[idx - 1])
                self.phrase_text(g, PHRASES[idx], 26, n if text_a >= 1 else 4)
                if text_a < 1:
                    g.fade(text_a, (TX - 26, 6, TX + 27, 38))
                if k < 1.8 and n < 4:  # 新字下的一点光
                    x = TX - 25.5 + n * 13 + 6
                    g.d.line((x - 3, 39, x + 3, 39), fill=1)
            self.fx(g, idx, k, t)
        else:
            k = u - len(PHRASES) * SLOT
            if text_a > 0:
                self.prev_text(g, PHRASES[-1])
                typewriter(g, TX - 2, 26, LAST, k, cps=3, align="center")
                if text_a < 1:
                    g.fade(text_a, (TX - 33, 6, TX + 34, 38))
        self.counter(g, int(e // self.CYCLE) + 1)
        return lv

    def enter(self, g: Gfx, t: float):
        # 道人从光里显出：先一圈光收拢，再显人
        p = span(t, 0, 1.6)
        if p < 1:
            r = lerp(40, 4, ease_in(p))
            ring(g, CX, 36, r, 2, phase=t)
            ring(g, CX, 36, r * 0.6, 3, phase=-t)
        if t > 1.2:
            self.daoist(g)
            if t < 1.9:
                g.fade(span(t, 1.2, 1.9), (0, 0, 70, 64))
        if t > 2.0:
            self.phrase_text(g, PHRASES[0], 26, int(clamp((t - 2.6) / 0.4 + 1, 0, 4)) if t > 2.6 else 0)
            self.counter(g, 1)
        g.mx[3:5, 3:5] = t > 1.2
        if t > 1.6:
            self.mx_sun(g, 0, t)

    def hold(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            self._renew(g, t, u, e)
            return
        lv = self.body(g, t, u, e)
        idx = int(u // SLOT)
        self.mx_sun(g, lv, t, burst=1.0 if idx == 24 and (u - idx * SLOT) < 2 else 0.0)

    def _renew(self, g: Gfx, t: float, u: float, e: float):
        """一遍念完：金光收回身中，再从头念"""
        p = ease_in(span(u, 0, 1.4))
        self.aura(g, 1 - p, t)
        self.daoist(g, glow=1 - p)
        if 1.2 < u < 1.6:  # 收光一闪
            rays(g, CX, HY, 4, 10, 8)
        n = int(e // self.CYCLE) + 1
        if u < 1.5:
            g.text(TX - 2, 26, LAST, align="center")
            g.fade(1 - span(u, 0.4, 1.5), (TX - 34, 26, TX + 33, 38))
            self.counter(g, n - 1)
        else:
            self.counter(g, n)
            k = u - 1.5
            if k > 0.6:
                self.phrase_text(g, PHRASES[0], 26, int(clamp((k - 0.6) / 0.4 + 1, 0, 4)))
            if blink(u, 0.3):  # 计数刚加一
                g.d.line((TX - 12, 61, TX + 12, 61), fill=1)
        self.mx_sun(g, 1 - p, t)
        g.mx_level = 4 if 1.2 < u < 1.6 else 1

    def interrupt(self, g: Gfx, t: float, e: float):
        """收功：金光淡去，咒句隐去"""
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        lv0 = self.level(u)
        f = ease_in_out(span(t, 0, 1.2))
        self.body(g, t, u, e, aura=lv0 * (1 - f), text_a=1 - f)
        if t > 1.0:
            g.text(TX, 26, "暂歇"[:int(clamp((t - 1.0) * 6, 0, 2))], align="center")
        g.mx[3:5, 3:5] = True
        if t < 1.0:
            self.mx_sun(g, lv0 * (1 - f), t)

    def resume(self, g: Gfx, t: float, e: float):
        u = e % self.CYCLE
        if e >= self.CYCLE and u < RENEW:
            u = RENEW
        lv0 = self.level(u)
        f = ease_out(span(t, 0.3, 1.8))
        if t < 0.3:  # 睁眼一瞬
            self.daoist(g, eyes_open=True)
            self.counter(g, int(e // self.CYCLE) + 1)
        else:
            self.body(g, t, u, e, aura=lv0 * f, text_a=span(t, 0.6, 1.6))
        self.mx_sun(g, lv0 * f, t)

    def complete(self, g: Gfx, t: float, e: float):
        """金光速现，覆护真人"""
        k = t
        lv = lerp(0.6, 1.0, span(k, 0, 0.8))
        self.aura(g, lv, t * 3)
        if k > 0.8:  # 金光一圈圈涌出，罩住全身
            for j in range(3):
                r = ((k * 30 + j * 16) % 48) + 12
                rays(g, CX, HY + 6, r, r + 5, 18, phase=j * 0.17 + k * 0.1)
        self.daoist(g, glow=1)
        if 1.6 < k < 1.75:
            g.invert()
        if k < 1.6:
            g.text(TX, 26, "金光速现", align="center")
        else:
            self.prev_text(g, "金光速现")
            typewriter(g, TX, 30, "覆护真人", k - 1.8, cps=4, align="center")
        self.counter(g, int(e // self.CYCLE) + 1)
        self.mx_sun(g, 1.0, t * 2, burst=span(k, 1.6, 2.4) * (1 - span(k, 3.5, 5.0)))
        g.mx_level = 1 + int(6 * (span(k, 1.4, 1.7) * (1 - span(k, 1.8, 3.5))))
