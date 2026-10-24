"""小周天：侧身盘坐的人，一粒光点沿督脉上行、任脉下行，周而复始（河车搬运）。

入场：打坐的人从虚空中显现，闭目；丹田亮起一点，沉到会阴，转到尾闾准备起程。
持续：光点沿“尾闾→夹脊→玉枕→泥丸→鹊桥→膻中→丹田→会阴”循环，一周 9 秒，过三关时关窍一闪、
      旁边冒出关名。丹田的丹随 e 慢慢长大（一转 10 分钟）；一转满时丹田一震放出一圈光，“第几转”加一。
中断：光点顺任脉滑回丹田，熄灭，“收功”。
恢复：丹田重新亮起，光点从会阴转到当前位置接上。
圆满：光点越转越快连成一圈光环，头顶放光，“炼精化气”。
"""
from __future__ import annotations

import math

from ..engine.anim import blink, clamp, ease_in, ease_in_out, ease_out, lerp, noise, pulse, rand, span
from ..engine.cn import cn_num
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r4_kit import glow_dot, path_point

PERIOD = 9.0      # 一周天秒数
RENEW = 4.0

# 侧身盘坐（面朝右）
HEAD = (64, 13)
BODY = [(58, 21), (67, 21), (69, 27), (70, 34), (71, 41), (73, 47), (66, 52), (52, 53), (50, 47), (51, 38), (53, 29),
        (55, 24)]
LEGS = [(50, 53), (56, 47), (78, 45), (92, 46), (98, 51), (95, 56), (72, 58), (50, 58)]
ARM = [(58, 24), (63, 24), (67, 36), (88, 45), (90, 49), (84, 50), (64, 44), (57, 32)]
CUSHION = (40, 55, 102, 63)

# 周天路线（从尾闾起，督脉上行，任脉下行）
PATH = [(54, 50), (54, 44), (55, 38), (56, 31), (58, 25), (58, 15), (63, 7), (69, 10), (68, 16), (66, 23), (66, 30),
        (67, 37), (66, 44), (60, 50), (54, 50)]
# 关窍：名、路线上的位置（0..1）、坐标、标签放哪
GATES = [("尾闾", 0.0, (54, 50), (20, 43)), ("夹脊", 0.12, (56, 31), (20, 25)), ("玉枕", 0.28, (58, 15),
                                                                                (22, 9))]
DANTIAN = (64, 41)
SEAL_U = 0.88     # 丹田在路线上的大致位置


def path_len() -> list[float]:
    acc = [0.0]
    for a, b in zip(PATH, PATH[1:]):
        acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return [v / acc[-1] for v in acc]


_ACC = path_len()
# 关窍在路线上的位置按折点算准：尾闾 = 第 0 点，夹脊 = 第 3 点，玉枕 = 第 5 点；丹田 = 第 12 点
GATES = [(nm, _ACC[i], xy, lab) for (nm, _, xy, lab), i in zip(GATES, (0, 3, 5))]
SEAL_U = _ACC[12]


def u_of_index(i: int) -> float:
    return _ACC[i]


@register
class Orbit(Ritual):
    id = "r4.orbit"
    name = "小周天"
    desc = "侧身盘坐的人，一粒光点沿督脉上行、任脉下行，过尾闾夹脊玉枕三关，丹田之丹随时日渐长"
    T = {"enter": 4.5, "interrupt": 1.6, "resume": 2.0, "complete": 5.0}
    CYCLE = 600.0

    # ------------------------------------------------------------ 零件

    def body(self, g: Gfx, breath: float = 0.0):
        """内经图式的侧身剪影：黑底白描，经脉是虚线"""
        d = g.d
        d.ellipse(CUSHION, fill=0, outline=1)
        d.line((CUSHION[0] + 6, CUSHION[1] + 4, CUSHION[2] - 6, CUSHION[1] + 4), fill=1)
        d.polygon(LEGS, fill=0, outline=1)
        d.line((60, 52, 80, 50), fill=1)                       # 叠着的小腿
        d.line((84, 53, 92, 53), fill=1)
        b = [(x + (breath if x > 62 and y > 26 else 0), y) for x, y in BODY]
        d.polygon(b, fill=0, outline=1)
        d.line((61, 22, 66, 31), fill=1)                       # 交领
        d.polygon(ARM, fill=0, outline=1)
        d.line((66, 40, 80, 46), fill=1)                       # 袖褶
        hx, hy = HEAD
        d.ellipse((hx - 6, hy - 7, hx + 6, hy + 6), fill=0, outline=1)
        d.polygon([(hx + 5, hy - 2), (hx + 8, hy + 1), (hx + 5, hy + 2)], fill=0, outline=1)  # 鼻
        d.ellipse((hx - 5, hy - 12, hx, hy - 7), fill=1)       # 发髻
        d.line((hx - 8, hy - 10, hx + 2, hy - 9), fill=1)      # 簪
        d.line((hx + 2, hy - 1, hx + 4, hy), fill=1)           # 闭着的眼
        d.line((hx + 4, hy + 4, hx + 5, hy + 4), fill=1)       # 嘴
        d.line((hx - 3, hy + 6, hx - 3, hy + 9), fill=1)       # 颈后
        # 经脉：虚线
        for i, (a, b2) in enumerate(zip(PATH, PATH[1:])):
            n = max(1, int(math.hypot(b2[0] - a[0], b2[1] - a[1]) / 2))
            for k in range(n):
                if k % 2 == 0:
                    f = k / n
                    g.px(lerp(a[0], b2[0], f), lerp(a[1], b2[1], f))

    def gates(self, g: Gfx, u: float, t: float, show_labels: bool = True):
        for name, gu, (x, y), (lx, ly) in GATES:
            dist = (u - gu) % 1.0
            hot = dist < 0.08
            r = 2 if hot else 1
            g.d.polygon([(x - r, y), (x, y - r), (x + r, y), (x, y + r)], fill=0 if not hot else 1, outline=1)
            if show_labels and dist < 0.2:
                k = 1 - span(dist, 0.12, 0.2)
                g.text(lx, ly, name)
                g.d.line((lx + 26, ly + 5, x - 4, y), fill=1)
                if k < 1:
                    g.fade(k, (lx, ly - 1, x - 3, ly + 12))

    def dot(self, g: Gfx, u: float, t: float, tail: int = 6, size: float = 2.0):
        for j in range(tail, 0, -1):
            x, y = path_point(PATH, u - j * 0.012)
            if j % 2 == 0 or j < 3:
                g.px(x, y)
        x, y = path_point(PATH, u)
        glow_dot(g, x, y, size + 0.6 * math.sin(t * 9), t)

    def dan(self, g: Gfx, e: float, t: float, scale: float = 1.0):
        p = (e % self.CYCLE) / self.CYCLE
        r = (1.0 + 3.5 * p) * scale
        x, y = DANTIAN
        if r < 0.5:
            return
        g.d.ellipse((x - r - 2, y - r - 2, x + r + 2, y + r + 2), fill=0)
        g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
        if r > 2.5:
            ring(g, x, y, r + 2 + pulse(t, 2.0), 2, t)

    def texts(self, g: Gfx, e: float, right: str | None = None, a: float = 1.0):
        n = int(e // self.CYCLE) + 1
        r = right if right is not None else f"第{cn_num(n)}转"
        g.vtext(115, 2, r[:int(round(len(r) * a))])
        left = "河车"
        g.vtext(2, 2, left[:int(round(len(left) * a))])

    def mx(self, g: Gfx, u: float | None, e: float, t: float, dan: float | None = None):
        """点阵：外圈 28 格是周天，光点带尾巴跑；中间 2×2 是丹田"""
        ringc = [(x, 0) for x in range(8)] + [(7, y) for y in range(1, 8)] + [(x, 7) for x in range(6, -1, -1)] + \
                [(0, y) for y in range(6, 0, -1)]
        # 路线起点（尾闾）对应左下角，上行 = 左边往上：把环转一下
        start = ringc.index((0, 6))
        order = ringc[start:] + ringc[:start]
        order = order[::-1]  # 逆着排 → 从左下沿左边往上
        order = [order[-1]] + order[:-1]
        if u is not None:
            i = int((u % 1.0) * 28)
            for j in range(4):
                x, y = order[(i - j) % 28]
                g.mx[y, x] = j == 0 or blink(t + j * 0.1, 0.3, 0.5)
        p = (e % self.CYCLE) / self.CYCLE if dan is None else dan
        on = blink(t, 1.2, 0.3 + 0.65 * p)
        for x, y in ((3, 3), (4, 3), (3, 4), (4, 4)):
            g.mx[y, x] = on if p < 0.5 or (x, y) == (3, 4) else on or (x + y) % 2 == 0

    # ------------------------------------------------------------ 阶段

    def u(self, e: float) -> float:
        return (e / PERIOD) % 1.0

    def hold(self, g: Gfx, t: float, e: float):
        k = e % self.CYCLE
        u = self.u(e)
        self.body(g, pulse(e, PERIOD))
        if e >= self.CYCLE and k < RENEW:  # 一转满：丹田一震
            shake = math.sin(k * 30) * (1 - span(k, 0, 1.0)) * 1.2
            x, y = DANTIAN
            r = 4.5 * (1 - ease_in(span(k, 0.3, 1.2))) + 1.0 * ease_out(span(k, 1.2, RENEW))
            g.d.ellipse((x - r + shake, y - r, x + r + shake, y + r), fill=1)
            rr = span(k, 0.3, 2.5)
            if 0 < rr < 1:
                ring(g, x, y, 4 + rr * 40, 2, rr)
                ring(g, x, y, 2 + rr * 26, 3, -rr)
            self.gates(g, u, t, show_labels=False)
            self.dot(g, u, t)
            n = int(e // self.CYCLE)
            if k > 0.6:
                typewriter(g, 2, 50, f"{cn_num(n)}转", k - 0.6, cps=6)
            self.texts(g, e)
            self.mx(g, u, e, t, dan=1.0 if k < 1.2 else 0.0)
            g.mx_level = 4 if 0.3 < k < 0.8 else 1
            return
        self.dan(g, e, t)
        self.gates(g, u, t)
        self.dot(g, u, t)
        self.texts(g, e)
        self.mx(g, u, e, t)

    def enter(self, g: Gfx, t: float):
        self.body(g)
        k = span(t, 0, 1.6)
        if k < 1:
            g.fade(ease_in_out(k))
        if t > 1.6:
            x, y = DANTIAN
            a = span(t, 1.6, 2.3)
            if t < 2.6:  # 丹田亮起一点
                glow_dot(g, x, y, 0.5 + 2 * ease_out(a), t)
            else:  # 沉到会阴，转到尾闾
                uu = lerp(SEAL_U, 1.0, ease_in_out(span(t, 2.6, 4.5)))
                self.dot(g, uu, t, tail=int(5 * span(t, 2.6, 3.2)))
            self.dan(g, 0, t, scale=span(t, 2.6, 3.5))
        self.gates(g, 0.95, t, show_labels=False)
        self.texts(g, 0, a=span(t, 3.4, 4.5))
        self.mx(g, lerp(SEAL_U, 1.0, span(t, 2.6, 4.5)) if t > 2.6 else None, 0, t, dan=span(t, 1.6, 2.3) * 0.2)

    def interrupt(self, g: Gfx, t: float, e: float):
        u0 = self.u(e)
        self.body(g, pulse(e, PERIOD))
        k = ease_in_out(span(t, 0, 1.0))
        # 顺着路线往前走到丹田（如果已经过了丹田就绕到下一圈的丹田）
        target = SEAL_U if u0 <= SEAL_U else SEAL_U + 1
        u = lerp(u0, target, k)
        self.dan(g, e, t, scale=1 - span(t, 1.0, 1.6) * 0.4)
        self.gates(g, u, t, show_labels=False)
        if t < 1.3:
            self.dot(g, u, t, tail=int(5 * (1 - k)), size=1.5 * (1 - span(t, 0.9, 1.3)))
        self.texts(g, e, right="收功")
        self.mx(g, u if t < 1.1 else None, e, t)

    def resume(self, g: Gfx, t: float, e: float):
        u1 = self.u(e)
        self.body(g, pulse(e, PERIOD))
        self.dan(g, e, t, scale=0.6 + 0.4 * span(t, 0, 0.6))
        x, y = DANTIAN
        if t < 0.6:
            glow_dot(g, x, y, 0.5 + 2 * ease_out(span(t, 0, 0.6)), t)
            u = None
        else:  # 从丹田出发，追到当前位置
            start = SEAL_U if u1 >= SEAL_U else SEAL_U - 1
            u = lerp(start, u1, ease_in_out(span(t, 0.6, 2.0)))
            self.dot(g, u, t, tail=int(5 * span(t, 0.6, 1.0)))
        self.gates(g, u if u is not None else SEAL_U, t, show_labels=t > 1.6)
        self.texts(g, e, right="收功" if t < 0.6 else None)
        self.mx(g, u, e, t)

    def complete(self, g: Gfx, t: float, e: float):
        self.body(g, 0)
        # 光点加速：相位 = ∫速度
        sp = 1 / PERIOD + 2.2 * span(t, 0, 2.2) ** 2
        u = self.u(e) + t / PERIOD + 2.2 * (t ** 3 / 3 / 2.2 ** 2 if t < 2.2 else 2.2 / 3 + (t - 2.2))
        if t < 2.0:
            self.dan(g, e, t)
            self.gates(g, u, t, show_labels=False)
            self.dot(g, u, t, tail=5 + int(20 * span(t, 0.5, 2.0)))
        else:  # 连成光环
            g.d.line(PATH, fill=1, width=2 if t > 2.4 else 1)
            x, y = DANTIAN
            r = 4.5 + 1.5 * math.sin(t * 5)
            g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
            gl = ease_out(span(t, 2.4, 3.4))
            hx, hy = HEAD
            for j in range(14):  # 头顶放光
                a = -math.pi / 2 + (j - 6.5) / 14 * math.pi * 1.4 + 0.05 * math.sin(t * 3)
                r0, r1 = 14, 14 + 12 * gl * (0.7 + 0.3 * math.sin(t * 7 + j))
                g.d.line((hx + math.cos(a) * r0, hy - 2 + math.sin(a) * r0, hx + math.cos(a) * r1,
                          hy - 2 + math.sin(a) * r1), fill=1)
            for (nm, gu, (gx, gy), _) in GATES:
                g.d.ellipse((gx - 2, gy - 2, gx + 2, gy + 2), fill=1)
        if t < 1.2:
            self.texts(g, e, a=1 - span(t, 0.2, 1.2))
        if t > 2.8:
            g.vtext(115, 2, "炼精化气"[:int(clamp((t - 2.8) * 3) * 4)])
        if t < 2.0:
            self.mx(g, u, e, t)
        else:
            for x in range(8):
                g.mx[0, x] = g.mx[7, x] = g.mx[x, 0] = g.mx[x, 7] = True
            on = blink(t, 0.4)
            g.mx[3:5, 3:5] = on
            g.mx_level = 1 + int(5 * (1 - span(t, 2.0, 3.5)))
