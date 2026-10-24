"""x6 赛博歇（二）：屏幕上的事——太极屏保、心斋清理、坐忘、磁盘整理"""
from __future__ import annotations

import math

import numpy as np

from ..engine.anim import (blink, clamp, ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp,
                           noise, rand, span)
from ..engine.fx import ring, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from ..engine.symbols import mx_taiji, taiji
from .x6_common import CURSOR, SAGE, SAGE_H, SAGE_W, progress, sage, window


def tri(u: float) -> float:
    """三角波 0→1→0，周期 2"""
    u %= 2.0
    return u if u < 1 else 2 - u


def crt_off(g: Gfx, p: float):
    """显像管关机：画面压成一条横线，再缩成一个点（p 0..1）"""
    a = g.array()
    out = np.zeros_like(a)
    if p < 0.55:
        h = max(1.0, 64 * (1 - ease_in(p / 0.55)))
        y0 = 32 - h / 2
        for y in range(int(y0), int(y0 + h) + 1):
            if 0 <= y < 64:
                src = int((y - y0) / h * 64)
                out[y] = a[min(63, max(0, src))]
        if h < 6:  # 压扁时整行发亮
            out[int(32 - h / 2):int(32 + h / 2) + 1, 4:124] = True
        g.put(out)
    else:
        g.put(out)
        k = (p - 0.55) / 0.45
        w = 60 * (1 - ease_out(min(1, k / 0.6)))
        if k < 0.6:
            g.d.line((64 - w, 32, 64 + w, 32), fill=1)
        elif k < 0.95:
            g.d.rectangle((63, 31, 64, 32), fill=1)


# ====================================================================== 太极屏保

@register
class TaijiSaver(Rest):
    id = "x6.dvd"
    name = "太极屏保"
    desc = "DVD 屏保式的太极在黑屏里斜着弹来弹去，边走边滚；偶尔正好撞进屏幕角落——众妙之门"
    T = {"enter": 2.6, "exit": 1.2}
    R = 9
    TX, TY = 9.75, 4.5     # 横、竖各走一趟的秒数：13:6，每 58.5 秒撞一次角
    OFF = 20.0             # 第一次撞角在 t = 58.5 - 20

    def setup(self):
        self._ht = 0.0
        self.box_w = 2 * self.R + 3
        self.box_h = 2 * self.R + 3 + 11
        self.hits = 0

    def pos(self, t: float):
        lx, ly = 128 - self.box_w, 64 - self.box_h
        return tri((t + self.OFF) / self.TX) * lx, tri((t + self.OFF) / self.TY) * ly

    def since_hit(self, t: float, T: float) -> float:
        u = (t + self.OFF) / T
        return (u - math.floor(u)) * T

    def logo(self, g: Gfx, x: float, y: float):
        cx, cy = x + self.R + 1, y + self.R + 1
        ang = (x / self.R) * 0.9  # 横着走就像在滚
        taiji(g, cx, cy, self.R, ang)
        g.text(cx, y + 2 * self.R + 5, "DAO", size=8, align="center")
        return cx, cy, ang

    def corner_k(self, t: float) -> tuple[int, float]:
        P = self.TX * 13 / 13 * 6  # = 58.5
        u = t + self.OFF
        n = int(u // P)
        return n, u - n * P

    def frame(self, g: Gfx, t: float):
        x, y = self.pos(t)
        n, k = self.corner_k(t)
        if n >= 1 and k < 4.2:  # 撞角庆祝：四角闪光、文字
            if k < 0.12:
                g.d.rectangle((0, 0, 127, 63), outline=1)
            cx = 0 if tri(n * 6) < 0.5 else 127
            cy = 0 if tri(n * 13) < 0.5 else 63
            p = span(k, 0, 1.2)
            if p < 1:
                for i in range(9):
                    a = math.atan2(32 - cy, 64 - cx) + (i - 4) * 0.17
                    r0, r1 = 10 + 40 * ease_out(p), 16 + 50 * ease_out(p)
                    g.d.line((cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * r1,
                              cy + math.sin(a) * r1), fill=1)
            # 玄之又玄，众妙之门（《道德经》第一章）：角落 = 门
            # 字写在同一条边的另一头：太极正往相反方向走，不会压字
            a = 1 - span(k, 3.4, 4.2)
            tx, al = (124, "right") if cx == 0 else (4, "left")
            ty = 50 if cy == 63 else 3
            typewriter(g, tx, ty, "众妙之门", (k - 0.3) * a, cps=5, align=al)
        cxx, cyy, ang = self.logo(g, x, y)
        # 撞墙：接触点迸三道小线
        for T, horiz in ((self.TX, True), (self.TY, False)):
            d = self.since_hit(t, T)
            if d < 0.25 and t > 0.3:
                p = d / 0.25
                if horiz:
                    wx = 0 if x < 10 else 127
                    for j in (-1, 0, 1):
                        g.d.line((wx, cyy + j * 5, wx + (3 + p * 4) * (1 if wx == 0 else -1), cyy + j * 7), fill=1)
                else:
                    wy = 0 if y < 10 else 63
                    for j in (-1, 0, 1):
                        g.d.line((cxx + j * 5, wy, cxx + j * 7, wy + (3 + p * 4) * (1 if wy == 0 else -1)), fill=1)
        mx_taiji(g, ang)
        if n >= 1 and k < 1.0:  # 点阵放烟花
            r = k * 5.2
            g.mx[:] = False
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.8:
                        g.mx[yy, xx] = True
            g.mx_level = 1 + int(5 * (1 - span(k, 0, 1.0)))

    def enter(self, g: Gfx, t: float):
        if t < 0.3:  # 显像管开机：一点 → 一条线
            w = 64 * ease_out(t / 0.3)
            g.d.line((64 - w, 32, 64 + w, 32), fill=1)
        elif t < 0.55:
            h = 32 * ease_out(span(t, 0.3, 0.55))
            g.d.rectangle((0, 32 - h, 127, 32 + h), fill=1)
            g.fade(1 - span(t, 0.4, 0.55))
        elif t < 1.7:
            if blink(t - 0.55, 0.5, 0.65):
                g.text(64, 26, "无信号", align="center")
        else:
            x, y = self.pos(0)
            self.logo(g, x, y)
            g.fade(ease_out(span(t, 1.7, 2.4)))
        if t > 1.7:
            mx_taiji(g, self.pos(0)[0] / self.R * 0.9)
        else:
            g.mx[3:5, :] = t > 0.3
            g.mx[:, 3:5] = t > 0.55

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.frame(g, t)

    def exit(self, g: Gfx, t: float):
        self.frame(g, self._ht + t)
        crt_off(g, span(t, 0, 1.1))
        g.mx[:] = False
        if t < 0.8:
            g.mx[3:5, 1:7] = True
        elif t < 1.0:
            g.mx[3:5, 3:5] = True


# ====================================================================== 心斋：清理杂念

DOC = Sprite("""
#####.
#...#.#
#.....#
#.###.#
#.....#
#.###.#
#.....#
#######
""")
POOL = "名利怒忧惧贪妒愁悔躁怨惑"
EXTS = (".tmp", ".log", ".bak", ".exe", ".dll")


@register
class MindFast(Rest):
    id = "x6.xinzhai"
    name = "心斋"
    desc = "“心斋”窗口里列着名.tmp、怒.log 一类杂念文件，鼠标一个个拖进回收站，清空后只剩“唯道集虚”"
    T = {"enter": 2.5, "exit": 1.2}
    C = 72.0
    SLOT = 6.5
    REST_POS = (70, 50)
    BIN = (98, 34)       # 桶身左上角

    def setup(self):
        self._ht = 0.0

    def files(self, n: int) -> list[tuple[str, str]]:
        """第 n 轮的四个杂念"""
        out, used = [], set()
        j = 0
        while len(out) < 4:
            c = POOL[int(rand(n * 31 + j, self.seed) * len(POOL))]
            j += 1
            if c in used:
                continue
            used.add(c)
            out.append((c, EXTS[int(rand(n * 17 + j, self.seed + 5) * len(EXTS))]))
        return out

    # ------------------------------------------------------------ 零件

    def row_y(self, i: float) -> float:
        return 16 + i * 11

    def file_row(self, g: Gfx, x: float, y: float, f: tuple[str, str], sel: bool = False):
        g.blit(DOC, x, y + 1)
        g.text(x + 10, y, f[0])
        g.text(x + 23, y + 3, f[1], size=8)
        if sel:
            g.invert((int(x) - 2, int(y) - 1, int(x) + 46, int(y) + 11))

    def bin(self, g: Gfx, lid: float, full: int, shake: float = 0.0):
        x, y = self.BIN
        x += shake
        body = [(x, y), (x + 22, y), (x + 19, y + 27), (x + 3, y + 27)]
        if full >= 2:  # 纸团冒出桶口
            for j in range(min(full, 4)):
                cx = x + 5 + j * 4
                g.d.ellipse((cx - 3, y - 4 + (j % 2) * 2, cx + 3, y + 2), fill=0, outline=1)
        g.d.polygon(body, fill=0, outline=1)
        for k in (6, 11, 16):
            g.d.line((x + k, y + 4, x + k - (k - 11) * 0.15, y + 23), fill=1)
        # 盖子：铰链在左，打开时向左上翻
        a = -lid * 1.9
        hx, hy = x - 1, y - 2
        ux, uy = math.cos(a), math.sin(a)
        L = 24
        p1 = (hx + ux * L, hy + uy * L)
        g.d.line((hx, hy, p1[0], p1[1]), fill=1, width=2)
        mx_, my_ = hx + ux * L / 2 - uy * 3, hy + uy * L / 2 + ux * -3
        g.d.line((hx + ux * (L / 2 - 3), hy + uy * (L / 2 - 3), mx_ - ux * 3, my_ - uy * 3), fill=1)
        g.d.line((mx_ - ux * 3, my_ - uy * 3, mx_ + ux * 3, my_ + uy * 3), fill=1)
        g.d.line((mx_ + ux * 3, my_ + uy * 3, hx + ux * (L / 2 + 3), hy + uy * (L / 2 + 3)), fill=1)

    def state(self, u: float):
        """→ (cursor, 拖着的文件序号, 拖动位置, 已删除个数, 盖子, 桶里个数, 下落中的文件)"""
        cur = self.REST_POS
        drag = None
        dpos = None
        removed = 0
        lid = 0.0
        inbin = 0
        falling = None
        prev = self.REST_POS
        for i in range(4):
            s = 3 + i * self.SLOT
            row = (6, self.row_y(0) + 4)  # 总是拿最上面一个（下面的会往上补）
            if u < s:
                break
            if u < s + 1.2:
                cur = _lerp2(prev, row, ease_in_out(span(u, s, s + 1.2)))
                break
            removed = i
            top = (self.BIN[0] + 1, self.BIN[1] - 13)
            if u < s + 1.5:
                cur, drag, dpos = row, i, (row[0] - 4, row[1] - 4)
                break
            if u < s + 3.3:
                k = ease_in_out(span(u, s + 1.5, s + 3.3))
                p = _lerp2(row, top, k)
                cur = (p[0], p[1] - math.sin(k * math.pi) * 4)
                drag, dpos = i, (cur[0] - 4, cur[1] - 4)
                removed = i + 1
                lid = ease_out(span(u, s + 2.5, s + 3.1))
                break
            removed = i + 1
            if u < s + 3.8:
                k = span(u, s + 3.3, s + 3.8)
                cur = top
                falling = (i, top[0] + 7, top[1] + 3 + ease_in(k) * 22)
                lid = 1.0
                inbin = i
                break
            inbin = i + 1
            if u < s + 4.6:
                lid = 1 - ease_out_bounce(span(u, s + 3.8, s + 4.6))
            prev = top
            cur = top
            if i == 3:  # 鼠标回到原处，然后隐去
                cur = _lerp2(top, self.REST_POS, ease_in_out(span(u, s + 4.6, s + 6.0)))
        if u >= 3 + 4 * self.SLOT - 0.5 and u < 50:
            inbin = 4
        if u >= 50:
            removed = 4
            inbin = 4 if u < 52.2 else 0
        return cur, drag, dpos, removed, lid, inbin, falling

    def draw(self, g: Gfx, t: float, u: float, n: int, cursor: bool = True):
        cur, drag, dpos, removed, lid, inbin, falling = self.state(u)
        fs = self.files(n)
        nxt = self.files(n + 1)
        shake = 0.0
        if 50 <= u < 51:  # 清空回收站：抖一抖
            shake = math.sin(u * 60) * 1.5
        if 51 <= u < 52.2:
            lid = ease_out(span(u, 51, 51.4)) * (1 - ease_in(span(u, 51.9, 52.2)))
        # 窗口
        window(g, 0, 0, 80, 63, "心斋", size=12)
        shown = 4 - removed
        pct = removed / 4
        if u >= 56:  # 新的杂念一个个冒出来
            k = int(clamp((u - 56) / 2.5 + 1, 0, 4))
            if u >= 56 + 3 * 2.5 + 0.01:
                k = 4
            pct = 1 - k / 4
            for j in range(k):
                pop = ease_out_back(span(u, 56 + j * 2.5, 56 + j * 2.5 + 0.4))
                self.file_row(g, 4 - (1 - pop) * 30, self.row_y(j), nxt[j])
                if u - (56 + j * 2.5) < 1.0:
                    g.text(56, self.row_y(j) + 3, "叮", size=8)
        else:
            sh = 0.0
            if 0 < removed < 4 or (removed == 4 and u < 50):  # 拿走一个后，下面的往上补
                s0 = 3 + (removed - 1) * self.SLOT + 1.5
                sh = (1 - ease_out(span(u, s0, s0 + 0.4))) * 11
            for j in range(shown):
                idx = removed + j
                if drag is not None and drag == idx:
                    continue
                self.file_row(g, 4, self.row_y(j) + sh, fs[idx])
            if drag is not None and 3 + drag * self.SLOT + 1.2 <= u < 3 + drag * self.SLOT + 1.5:
                self.file_row(g, 4, self.row_y(0), fs[drag], sel=True)
            if removed == 4 and 31 < u < 56:
                a = 1 - span(u, 54.5, 56)
                typewriter(g, 40, 22, "唯道集虚", (u - 31) * a, cps=2, align="center")
                if u > 36:
                    typewriter(g, 40, 39, "虚者心斋", (u - 36) * a, cps=2, align="center")
        # 窗口标题栏右侧：虚 xx%
        g.text(72, 3, f"{int(pct * 100)}%", size=8, fill=0, align="right")
        self.bin(g, lid, inbin, shake)
        if 51.3 <= u < 53:  # 清空：一缕尘烟升起散掉
            k = span(u, 51.3, 53)
            for j in range(8):
                a = -math.pi / 2 + (rand(j, 4) - 0.5) * 1.6
                r = 4 + k * (10 + rand(j, 5) * 12)
                if rand(j + int(k * 6), 6) > k * 0.8:
                    g.px(self.BIN[0] + 11 + math.cos(a) * r, self.BIN[1] - 2 + math.sin(a) * r)
        if falling is not None:
            g.blit(DOC, falling[1], falling[2])
            # 桶身挡住落下的文件
            x, y = self.BIN
            g.d.polygon([(x, y), (x + 22, y), (x + 19, y + 27), (x + 3, y + 27)], fill=0, outline=1)
            for k in (6, 11, 16):
                g.d.line((x + k, y + 4, x + k - (k - 11) * 0.15, y + 23), fill=1)
        if drag is not None and dpos is not None:
            f = fs[drag]
            g.blit(DOC, cur[0] + 7, cur[1] + 3)  # 拖着的文件挂在鼠标右下
            g.text(cur[0] + 16, cur[1] + 2, f[0])
        if cursor and (u < 3 + 4 * self.SLOT + 1.5 or u > 69):
            g.blit(CURSOR, cur[0], cur[1])
        # 点阵：回收站
        self.mx_bin(g, lid, inbin)

    def mx_bin(self, g: Gfx, lid: float, inbin: int):
        g.mx[2:8, 1] = True
        g.mx[2:8, 6] = True
        g.mx[7, 1:7] = True
        if lid < 0.3:
            g.mx[1, 0:8] = True
            g.mx[0, 3:5] = True
        else:
            g.mx[0, 0] = g.mx[1, 1] = True
            g.mx_set(2, 0)
        for j in range(min(inbin, 4)):
            g.mx[6 - j, 2:6] = True

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        s = ease_out(span(t, 0, 0.6))
        if t < 0.6:  # 窗口从中心张开
            w, h = 4 + 36 * s, 3 + 28.5 * s
            g.d.rectangle((40 - w, 32 - h, 40 + w, 32 + h), outline=1)
            g.d.rectangle((40 - w, 32 - h, 40 + w, 32 - h + 12 * s), fill=1)
        else:
            window(g, 0, 0, 80, 63, "心斋", size=12)
            fs = self.files(0)
            for j in range(4):
                p = ease_out_back(span(t, 0.7 + j * 0.25, 1.0 + j * 0.25))
                if p > 0:
                    self.file_row(g, 4 - (1 - p) * 30, self.row_y(j), fs[j])
            g.text(72, 3, "0%", size=8, fill=0, align="right")
        self._bin_at(g, lerp(-70, 0, ease_out_bounce(span(t, 0.5, 1.4))))
        k = ease_out(span(t, 1.6, 2.5))
        g.blit(CURSOR, lerp(130, self.REST_POS[0], k), lerp(70, self.REST_POS[1], k))
        if t > 0.6:
            self.mx_bin(g, 0, 0)
        else:
            g.mx[7, 1:7] = True

    def _bin_at(self, g: Gfx, dy: float):
        bx, by = self.BIN
        self.BIN = (bx, by + dy)
        self.bin(g, 0, 0)
        self.BIN = (bx, by)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        n = int(t // self.C)
        self.draw(g, t, t - n * self.C, n)

    def exit(self, g: Gfx, t: float):
        t0 = self._ht
        n = int(t0 // self.C)
        u = t0 - n * self.C
        if t < 0.5:
            self.draw(g, t0, u, n, cursor=False)
            k = ease_in(span(t, 0, 0.5))
            yb = 63 - k * 51  # 窗口从下往上卷起
            g.d.rectangle((0, yb, 80, 63), fill=0)
            g.d.line((0, yb, 80, yb), fill=1)
            g.d.line((0, 13, 0, yb), fill=1)
            g.d.line((80, 13, 80, yb), fill=1)
        else:
            pass
        k = ease_in(span(t, 0.5, 1.2))
        if t >= 0.5:  # 窗口缩成标题栏飞走，桶沉下去
            g.d.rectangle((0, 0, 127, 63), fill=0)
            window(g, 0 + k * 20, -k * 16, 80 - k * 40, 12 - k * 16, "心斋", size=12)
            self._bin_at(g, ease_in(span(t, 0.5, 1.2)) * 40)
        self.mx_bin(g, 0, 0)


def _lerp2(a, b, k):
    return lerp(a[0], b[0], k), lerp(a[1], b[1], k)


# ====================================================================== 坐忘

# 《庄子·大宗师》：颜回先忘仁义，再忘礼乐，而后“堕肢体，黜聪明，离形去知，同于大通，此谓坐忘”
STAGES = [  # (起, 止, 名, 进度起, 进度止)
    (0, 14, "忘仁义", 1.00, 0.80),
    (14, 28, "忘礼乐", 0.80, 0.60),
    (28, 42, "堕肢体", 0.60, 0.35),
    (42, 54, "黜聪明", 0.35, 0.12),
    (54, 62, "离形去知", 0.12, 0.0),
    (62, 84, "同于大通", 0.0, 0.0),
    (84, 96, "复归于朴", 0.0, 1.0),
]


@register
class SitForget(Rest):
    id = "x6.zuowang"
    name = "坐忘"
    desc = "“坐忘”进度条从 100% 倒着走到 0%：仁义、礼乐飘走，肢体、耳目一层层散成像素，最后只剩一圈圈涟漪——同于大通"
    T = {"enter": 2.6, "exit": 1.2}
    C = 96.0
    SX, SY = 9, 27
    WIN = (56, 0, 127, 50)

    def setup(self):
        self._ht = 0.0

    def stage(self, u: float):
        for st in STAGES:
            if st[0] <= u < st[1]:
                k = (u - st[0]) / (st[1] - st[0])
                return st, k, lerp(st[3], st[4], k)
        return STAGES[0], 0.0, 1.0

    def levels(self, u: float) -> tuple[float, float]:
        """(身体, 头) 的残留比例"""
        if u >= 84:
            v = ease_in_out(span(u, 86, 92))
            return v, v
        body = lerp(1, 0.25, span(u, 28, 42)) * (1 - span(u, 54, 62)) if u >= 28 else 1.0
        head = lerp(1, 0.25, span(u, 42, 54)) * (1 - span(u, 54, 62)) if u >= 42 else 1.0
        return body, head

    def cushion(self, g: Gfx):
        g.d.ellipse((self.SX - 3, 56, self.SX + SAGE_W + 2, 63), fill=0, outline=1)

    def figure(self, g: Gfx, body: float, head: float):
        if body <= 0 and head <= 0:
            self.cushion(g)
            return
        self.cushion(g)
        sage(g, self.SX, self.SY)
        x, y = self.SX, self.SY
        if body < 1:
            g.fade(body, (x + 1, y + 15, x + SAGE_W - 1, y + 36))
        if head < 1:
            g.fade(head, (x + 8, y, x + 29, y + 15))

    def floating(self, g: Gfx, u: float):
        """忘掉的字从头顶飘走、散掉"""
        for ch, t0 in (("仁", 2.0), ("义", 7.0), ("礼", 16.0), ("乐", 21.0)):
            k = span(u, t0, t0 + 6.5)
            if 0 < k < 1:
                x = self.SX + 13 + (rand(int(t0), self.seed) - 0.5) * 12 + k * 4
                y = self.SY - 6 - ease_out(k) * 18
                g.text(x, y, ch)
                if k > 0.35:
                    g.fade(1 - span(k, 0.35, 1.0), (int(x) - 1, int(y) - 1, int(x) + 13, int(y) + 12))

    def datong(self, g: Gfx, u: float, t: float, a: float):
        """同于大通：心口一点，涟漪一圈圈荡到屏幕外，八方细线"""
        cx, cy = self.SX + SAGE_W // 2, self.SY + 20
        if a <= 0:
            return
        g.d.rectangle((cx - 1, cy - 1, cx, cy), fill=1)
        for j in range(4):
            r = ((t * 7 + j * 22) % 88) * a
            if r > 2:
                ring(g, cx, cy, r, density=2 if r < 40 else 3, phase=t * 0.1)
        for i in range(12):
            ang = i * math.pi / 6 + t * 0.03
            for d in range(8, int(120 * a), 6):
                if (d // 6 + int(t * 4)) % 3 == 0:
                    g.px(cx + math.cos(ang) * d, cy + math.sin(ang) * d * 0.8)

    def panel(self, g: Gfx, label: str, p: float, t: float):
        x0, y0, x1, y1 = self.WIN
        window(g, x0, y0, x1, y1, "坐忘", size=12)
        g.text((x0 + x1) / 2, 17, label, align="center")
        progress(g, x0 + 4, 32, x1 - 4, 39, p)
        g.text(x1 - 4, 42, f"{int(round(p * 100))}%", size=8, align="right")
        if p > 0 and blink(t, 1.0, 0.7):
            g.text(x0 + 4, 42, "卸载中", size=8)

    def mx_bar(self, g: Gfx, p: float):
        n = int(math.ceil(p * 8 - 1e-6))
        for r in range(n):
            g.mx[7 - r, 1:7] = True
        g.mx[0, 0] = g.mx[0, 7] = True

    def scene(self, g: Gfx, u: float, t: float):
        st, k, p = self.stage(u)
        body, head = self.levels(u)
        self.figure(g, body, head)
        self.floating(g, u)
        if 60 <= u < 92:  # 涟漪：62 起荡开，84 后收回
            a = ease_out(span(u, 60, 64)) * (1 - ease_in(span(u, 84, 88)))
            self.datong(g, u, t, a)
        win_a = 1 - span(u, 61, 64) if u < 84 else span(u, 90, 92)
        if win_a > 0:
            self.panel(g, st[2], p if u < 84 else ease_in_out(span(u, 92, 95.5)), t)
            if win_a < 1:
                g.fade(win_a, self.WIN[:2] + (self.WIN[2] + 1, self.WIN[3] + 1))
        if 63 < u < 86:
            a = span(u, 63, 65) * (1 - span(u, 83, 86))
            n = int(4 * a + 0.999) if a > 0 else 0
            g.vtext(112, 6, "同于大通"[:n])
        # 点阵
        if 62 <= u < 86:
            r = (t * 3) % 6
            for yy in range(8):
                for xx in range(8):
                    if abs(math.hypot(xx - 3.5, yy - 3.5) - r) < 0.7:
                        g.mx[yy, xx] = True
            g.mx[3:5, 3:5] = True
        else:
            self.mx_bar(g, p if u < 84 else ease_in_out(span(u, 92, 95.5)))

    def enter(self, g: Gfx, t: float):
        a = ease_in_out(span(t, 0, 1.4))
        self.figure(g, a, a)
        if t > 1.2:
            s = ease_out_back(span(t, 1.2, 1.8))
            x0, y0, x1, y1 = self.WIN
            if s < 1:
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                w, h = (x1 - x0) / 2 * s, (y1 - y0) / 2 * s
                if w > 2 and h > 2:
                    g.d.rectangle((cx - w, cy - h, cx + w, cy + h), outline=1, fill=0)
            else:
                self.panel(g, "忘仁义", 1.0, t)
        self.mx_bar(g, span(t, 1.2, 2.4))

    def hold(self, g: Gfx, t: float):
        self._ht = t
        self.scene(g, t % self.C, t)

    def exit(self, g: Gfx, t: float):
        self.scene(g, self._ht % self.C, self._ht + t)
        g.fade(1 - ease_in(span(t, 0, 1.1)))
        g.mx[:] = False
        self.mx_bar(g, 1 - span(t, 0, 1.0))


# ====================================================================== 归根：磁盘碎片整理

GC, GR = 24, 8              # 格子：24 列 × 8 行
GX, GY, PITCH = 4, 16, 5
NCELL = GC * GR
NDATA = 100


@register
class Defrag(Rest):
    id = "x6.defrag"
    name = "归根"
    desc = "磁盘碎片整理：散落的数据块一块块飞回左边排齐——夫物芸芸，各复归其根，归根曰静"
    T = {"enter": 2.5, "exit": 1.2}
    C = 56.0
    SCAT = 3.0            # 万物并作（打散）
    START = 4.0           # 开始整理

    def setup(self):
        self._ht = 0.0
        self._cache: dict[int, tuple] = {}

    def plan(self, n: int):
        """第 n 轮：打散后的位置、整理的时间表（缓存）"""
        if n in self._cache:
            return self._cache[n]
        import random
        rng = random.Random(self.seed * 1000 + n)
        cells = sorted(rng.sample(range(NCELL), NDATA))
        occ = [-1] * NCELL           # 格子 → 块号（块号 = 归根后的位置）
        # 块 i 打散到 cells[...]：为了“看起来乱”，打乱对应关系
        order = list(range(NDATA))
        rng.shuffle(order)
        scatter = {}
        for b, c in zip(order, cells):
            scatter[b] = c
        # 整理：目标格 k 从 0 到 NDATA-1 扫过去；k 空着就从最后面搬一块过来
        pos = dict(scatter)
        where = {c: b for b, c in pos.items()}
        tail = NCELL - 1
        events = []                  # (开始时刻, 时长, 块, 从, 到)；时长 0 = 原地确认
        tt = self.START
        settle = {}
        for k in range(NDATA):
            if k in where:
                events.append((tt, 0.07, where[k], k, k))
                settle[where[k]] = tt + 0.07
                tt += 0.07
            else:
                while tail not in where or tail <= k:
                    tail -= 1
                b = where.pop(tail)
                events.append((tt, 0.42, b, tail, k))
                where[k] = b
                settle[b] = tt + 0.42
                tt += 0.42
        res = (scatter, events, settle, tt)
        self._cache = {n: res}
        return res

    @staticmethod
    def cell_xy(c: float) -> tuple[float, float]:
        c = int(c)
        return GX + (c % GC) * PITCH, GY + (c // GC) * PITCH

    def block(self, g: Gfx, x: float, y: float, kind: int):
        """kind 1 = 已归根（实心），2 = 未整理（空心带点），3 = 正在搬（实心外框）"""
        if kind == 1:
            g.d.rectangle((x, y, x + 3, y + 3), fill=1)
        elif kind == 2:
            g.d.rectangle((x, y, x + 3, y + 3), outline=1)
        else:
            g.d.rectangle((x - 1, y - 1, x + 4, y + 4), outline=1)
            g.d.rectangle((x + 1, y + 1, x + 2, y + 2), fill=1)

    def grid(self, g: Gfx, u: float, n: int, t: float):
        scatter, events, settle, tend = self.plan(n)
        occupied = set()
        moving = []
        head = None
        if u < self.SCAT:  # 万物并作：从排好的位置飞散
            for b in range(NDATA):
                k = ease_in_out(span(u, 0.3 + rand(b, n) * 1.2, 1.8 + rand(b, n) * 1.2))
                x0, y0 = self.cell_xy(b)
                x1, y1 = self.cell_xy(scatter[b])
                lift = math.sin(k * math.pi) * (4 + rand(b + 7, n) * 8)
                self.block(g, lerp(x0, x1, k), lerp(y0, y1, k) - lift, 1 if k < 0.5 else 2)
            done = 1 - span(u, 0, self.SCAT)
            occupied = None
            self._occ = {b if u < 1.5 else scatter[b] for b in range(NDATA)}
        else:
            pos = dict(scatter)
            state = {b: 2 for b in range(NDATA)}
            done_n = 0
            for (s, d, b, c0, c1) in events:
                if u < s:
                    break
                if u < s + d:
                    head = c1
                    if c0 != c1:
                        moving.append((b, c0, c1, (u - s) / d))
                        pos.pop(b, None)
                    break
                pos[b] = c1
                state[b] = 1
                done_n += 1
            for b, c in pos.items():
                x, y = self.cell_xy(c)
                self.block(g, x, y, state[b])
            for b, c0, c1, k in moving:
                x0, y0 = self.cell_xy(c0)
                x1, y1 = self.cell_xy(c1)
                kk = ease_in_out(k)
                self.block(g, lerp(x0, x1, kk), lerp(y0, y1, kk) - math.sin(kk * math.pi) * 6, 3)
            done = done_n / NDATA
            occupied = pos
            self._occ = set(pos.values())
        # 空格子：一个小点
        if occupied is not None:
            filled = set(occupied.values())
            for c in range(NCELL):
                if c not in filled:
                    x, y = self.cell_xy(c)
                    g.px(x + 1, y + 2)
        if head is not None and blink(t, 0.2):  # 读写头
            x, y = self.cell_xy(head)
            g.d.rectangle((x - 1, y - 1, x + 4, y + 4), outline=1)
        self._head = head
        return done, tend

    def title(self, g: Gfx, u: float, tend: float, n: int):
        # 《道德经》第十六章：万物并作，吾以观复。夫物芸芸，各复归其根。归根曰静，是谓复命
        if u < self.START:
            s, k0 = "万物并作", 0.0
        elif u < tend:
            s, k0 = "吾以观复", self.START
        elif u < tend + 12:
            s, k0 = "归根曰静", tend
        else:
            s, k0 = "是谓复命", tend + 12
        if s == "万物并作":
            g.text(64, 1, s, align="center")
        else:
            typewriter(g, 64, 1, s, u - k0, cps=4, align="center")

    def footer(self, g: Gfx, p: float, t: float, busy: bool):
        progress(g, 4, 57, 100, 62, p)
        g.text(124, 56, f"{int(p * 100)}%", size=8, align="right")

    def mx(self, g: Gfx, occ, t: float, head=None):
        """点阵 = 缩小的磁盘图：每个点管 3 个格子，至少一半有数据就亮"""
        for c in occ:
            g.mx[c // GC, (c % GC) // 3] = True
        if head is not None:
            g.mx[head // GC, (head % GC) // 3] = blink(t, 0.2)

    def scene(self, g: Gfx, u: float, n: int, t: float):
        done, tend = self.grid(g, u, n, t)
        if u >= tend:  # 归根曰静：偶尔一块轻轻一闪
            j = int(t / 2.3)
            if rand(j, self.seed) < 0.6:
                c = int(rand(j + 1, self.seed) * NDATA)
                x, y = self.cell_xy(c)
                if (t / 2.3 - j) < 0.25:
                    g.d.rectangle((x, y, x + 3, y + 3), fill=0, outline=1)
        self.title(g, u, tend, n)
        busy = self.START <= u < tend
        self.footer(g, done, t, busy)
        self.mx(g, self._occ, t, self._head)

    def enter(self, g: Gfx, t: float):
        # 网格一列列扫出来，数据块从上落进左边排好
        cols = int(GC * ease_out(span(t, 0, 0.9)))
        for c in range(NCELL):
            if c % GC < cols:
                x, y = self.cell_xy(c)
                g.px(x + 1, y + 2)
        for b in range(NDATA):
            k = ease_out_bounce(span(t, 0.8 + b * 0.009, 1.4 + b * 0.009))
            if k > 0:
                x, y = self.cell_xy(b)
                g.d.rectangle((x, y - (1 - k) * 30, x + 3, y + 3 - (1 - k) * 30), fill=1)
        if t > 1.6:
            typewriter(g, 64, 1, "万物并作", (t - 1.6) * 4, cps=4, align="center")
        if t > 0.5:
            self.footer(g, 1.0, t, False)
        self.mx(g, range(int(NDATA * span(t, 0.8, 2.2))), t)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        n = int(t // self.C)
        self.scene(g, t - n * self.C, n, t)

    def exit(self, g: Gfx, t: float):
        n = int(self._ht // self.C)
        self.scene(g, self._ht - n * self.C, n, self._ht + t)
        k = ease_in(span(t, 0, 1.1))
        g.d.rectangle((0, 0, int(128 * k), 63), fill=0)  # 从左往右擦掉
        g.mx[:, :int(8 * k + 0.5)] = False
