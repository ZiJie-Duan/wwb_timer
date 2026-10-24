"""陈抟高卧：华山石崖下，希夷先生侧身而卧（蛰龙睡），一睡百余日。

依据：《宋史·隐逸传·陈抟》：“移居华山云台观，又止少华石室，每寝处，多百余日不起。”太宗赐号“希夷先生”。
后世称“睡仙”，其睡法为侧身屈膝的“蛰龙睡”。周世宗、宋太宗都曾召他入朝。
"""
from __future__ import annotations

import math

from ..engine.anim import clamp, ease_in, ease_in_out, ease_out, ease_out_bounce, lerp, noise, rand, span
from ..engine.cn import cn_num
from ..engine.fx import stars, typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Pen, backdrop, breathe, ev, halo, iris, mx_zzz, z_glyph, zzz

SLAB = 50          # 卧石面
FX, FY = 20, SLAB - 26   # 卧像左上角
DAY = 40.0         # 画面里的“一日”
SEASON = 25        # 每季的日数
FACE = (FX + 17, FY + 6)  # 鼻尖附近（Z 从这里冒出）


def _bg():
    p = Pen()
    # 右：华山三峰（远，稀疏抖动）
    p.poly([(78, 64), (88, 38), (92, 41), (101, 15), (108, 31), (114, 25), (128, 44), (128, 64)], fill=0.13)
    p.line([(101, 15), (99, 26), (102, 36)])
    p.line([(114, 25), (112, 35)])
    # 左：石崖，顶上探出一片岩檐（石室）
    p.poly([(0, 0), (44, 0), (40, 4), (30, 6), (20, 9), (14, 14), (11, 24), (9, 36), (11, 50), (8, 64), (0, 64)],
           fill=0.4)
    p.line([(4, 18), (9, 26)])
    p.line([(2, 40), (6, 46)])
    p.line([(22, 3), (34, 3)], 0)
    # 卧石
    p.poly([(14, SLAB), (18, SLAB - 1), (94, SLAB - 1), (100, SLAB + 1), (98, SLAB + 6), (12, SLAB + 6)], fill=0.3)
    p.line([(15, SLAB), (98, SLAB)], 1)
    # 地面与草
    p.line([(0, 58), (128, 58)])
    for x in (6, 104, 118):
        p.line([(x, 58), (x - 2, 54)])
        p.line([(x + 1, 58), (x + 2, 55)])
    for i in range(12):
        p.px(int(rand(i, 41) * 128), 60 + int(rand(i, 42) * 4))
    return p.image()


def _lying(b: int) -> tuple[Sprite, list[int]]:
    """侧卧（头在左，以手支颐，屈膝）。b = 吸气时背脊抬起的像素。返回 (像素画, 每列顶端 y)"""
    p = Pen(64, 26)
    y0 = 25
    # 道袍身子：肩 → 背 → 胯（最高）→ 膝 → 脚
    p.poly([(16, 13), (24, 9 - b), (34, 7 - b), (42, 6 - b), (49, 7), (56, 11), (61, 16), (63, 21), (63, y0),
            (16, y0)], fill=0.2)
    p.line([(33, 8 - b), (31, y0)])                         # 腰带
    p.line([(35, 8 - b), (33, y0)])
    p.line([(44, 8 - b), (46, 16), (45, y0)])               # 衣褶
    p.line([(51, 9), (54, 17), (53, y0)])                   # 屈膝
    p.line([(40, 22), (50, 22)])
    p.rect((58, 20, 63, y0), fill=1)                        # 鞋
    # 搭在身上的手臂与宽袖
    p.poly([(18, 13 - b), (30, 10 - b), (40, 12 - b), (41, 18), (36, 22), (28, 21), (21, 18)], fill=0)
    p.line([(37, 14 - b), (38, 20)])
    p.line([(34, 16), (35, 21)])
    # 支颐的手臂（肘撑在石上）
    p.poly([(0, y0), (2, 18), (6, 15), (11, 17), (12, y0)], fill=0)
    p.line([(3, 21), (9, 20)])
    # 头：脸朝外，向手一侧歪
    p.ellipse((5, 3, 18, 16), fill=0)
    p.ellipse((2, 0, 9, 6), fill=1)                         # 发髻
    p.line([(0, 5), (11, 0)], 0)                            # 簪（黑线划过发髻）
    p.line([(8, 8), (10, 8)])                               # 白眉
    p.line([(13, 8), (15, 8)])
    p.line([(8, 10), (9, 11), (10, 10)])                    # 合着的眼
    p.line([(13, 10), (14, 11), (15, 10)])
    p.px(11, 12)
    # 长须垂到石上
    p.poly([(8, 13), (15, 13), (21, y0), (10, y0)], fill=1)
    p.line([(12, 16), (13, y0 - 1)], 0)
    p.line([(16, 17), (18, y0 - 1)], 0)
    spr = p.sprite()
    top = []
    for x in range(spr.w):
        col = spr.mask[:, x].nonzero()[0]
        top.append(int(col[0]) if len(col) else 99)
    return spr, top


def _sitting(yawn: bool) -> Sprite:
    """盘坐（入场用）；yawn：伸懒腰"""
    p = Pen(30, 30)
    p.poly([(4, 29), (8, 16), (22, 16), (26, 29)], fill=0.28)       # 袍
    p.ellipse((1, 24, 29, 29), fill=0.5)                             # 盘起的腿
    p.ellipse((10, 5, 20, 15), fill=0)                               # 头
    p.ellipse((13, 1, 17, 5), fill=1)                                # 发髻
    p.line([(10, 3), (20, 3)])                                       # 簪
    p.poly([(12, 13), (18, 13), (17, 22), (15, 24), (13, 22)], fill=1)  # 须
    if yawn:
        p.poly([(8, 17), (3, 8), (1, 0), (4, 0), (7, 8), (11, 16)], fill=0.6)    # 两臂上举
        p.poly([(22, 17), (27, 8), (29, 0), (26, 0), (23, 8), (19, 16)], fill=0.6)
        p.ellipse((14, 10, 16, 13), fill=0)                          # 张嘴
        p.line([(12, 9), (14, 9)])
        p.line([(16, 9), (18, 9)])
    else:
        p.poly([(8, 17), (4, 26), (14, 27), (12, 20)], fill=0.6)
        p.poly([(22, 17), (26, 26), (16, 27), (18, 20)], fill=0.6)
        p.line([(12, 9), (14, 9)])
        p.line([(16, 9), (18, 9)])
    return p.sprite()


_CR = [Sprite("""
  ........##.........
  .......###.........
  ......####.........
  .....####..........
  ##..#######........
  .###############...
  ....#########..####
  .......##..........
"""), Sprite("""
  ...................
  ##.................
  .##############....
  ....##########.####
  .....######........
  ......####.........
  .......###.........
  ........#..........
""")]
CRANE = [halo(s) for s in _CR]           # 朝左飞
CRANE_R = [s.flip() for s in CRANE]      # 朝右飞

_BG = None
_LIE: list = []


def _assets():
    global _BG, _LIE
    if _BG is None:
        _BG = _bg()
        _LIE = [_lying(0), _lying(1)]
    return _BG, _LIE


@register
class ChenTuan(Rest):
    id = "x1.chentuan"
    name = "陈抟高卧"
    desc = "华山石崖下希夷先生侧身而卧，日月轮转、四季更替，一睡百余日；仙鹤衔诏来请，被一声鼾吹走"
    T = {"enter": 3.0, "exit": 1.3}

    def setup(self):
        self.day0 = 1 + self.rng.randrange(0, 4 * SEASON)  # 从哪个季节睡起
        self._ht = 0.0
        _assets()

    # ------------------------------------------------------------ 零件

    def day(self, t: float) -> int:
        return self.day0 + int(t // DAY)

    def sky(self, g: Gfx, t: float):
        p = (t % DAY) / DAY
        if p < 0.6:  # 白天：太阳从右往左
            k = p / 0.6
            x, y = lerp(120, 50, k), 30 - math.sin(k * math.pi) * 24
            g.d.ellipse((x - 3, y - 3, x + 3, y + 3), outline=1, fill=0)
            for i in range(8):
                a = i * math.pi / 4 + t * 0.3
                g.d.line((x + math.cos(a) * 5, y + math.sin(a) * 5, x + math.cos(a) * 6.5, y + math.sin(a) * 6.5), fill=1)
        else:        # 夜：月亮与星
            k = (p - 0.6) / 0.4
            stars(g, t, self.seed, n=14, box=(46, 2, 126, 22), twinkle=0.35 + 0.3 * abs(k - 0.5))
            x, y = lerp(120, 50, k), 30 - math.sin(k * math.pi) * 24
            g.d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=1)
            g.d.ellipse((x - 1, y - 4, x + 4, y + 2), fill=0)

    def season(self, g: Gfx, t: float, dx: int = 0):
        s = ((self.day(t) - 1) // SEASON) % 4
        for i in range(14 if s != 1 else 6):
            sp = 0.6 + 0.6 * rand(i, 7)
            if s == 3:      # 冬：雪
                x = (rand(i, 3) * 140 + noise(t * 0.3 + i, 5) * 8) % 132
                y = (rand(i, 4) * 70 + t * 9 * sp) % 70 - 3
                g.px(x + dx, y)
            elif s == 2:    # 秋：落叶翻飞
                x = (rand(i, 3) * 160 - t * 7 * sp) % 150 - 10
                y = (rand(i, 4) * 70 + t * 6 * sp) % 70 - 3
                f = int(t * 3 + i) % 2
                g.d.line((x + dx, y, x + dx + 2, y + (1 if f else -1)), fill=1)
            elif s == 0:    # 春：花瓣
                x = (rand(i, 3) * 160 - t * 10 * sp) % 150 - 10
                y = (rand(i, 4) * 70 + t * 5 * sp + math.sin(t + i) * 3) % 70 - 3
                g.d.rectangle((x + dx, y, x + dx + 1, y), fill=1)
            else:           # 夏：萤火
                x = 20 + rand(i, 3) * 100 + math.sin(t * 0.7 + i * 2) * 6
                y = 50 + rand(i, 4) * 10 + math.sin(t * 1.1 + i) * 3
                if noise(t * 1.5 + i * 3, 9) > 0.55:
                    g.px(x + dx, y)
        if s == 3:  # 冬：人身上、石上积一层雪
            spr, top = _LIE[0]
            for x in range(0, spr.w, 1):
                if top[x] < 99 and (x * 7) % 5 < 3:
                    g.px(FX + x + dx, FY + top[x] - 1)
            for x in range(16, 98, 2):
                g.px(x + dx, SLAB - 2 + (x // 2) % 2)

    def counter_a(self, t: float) -> float:
        """每到天明报一次日数（入场时已经显示着，第一天不再淡入）"""
        k = t % DAY
        return (1.0 if t < DAY else span(k, 0, 0.6)) * (1 - span(k, 4.2, 5.0))

    def counter(self, g: Gfx, t: float, a: float = 1.0):
        """“第几日”：天明时在天上显出来"""
        if a <= 0:
            return
        s = f"第{cn_num(self.day(t))}日"
        n = max(1, int(round(len(s) * a)))
        g.text(86, 1, s[:n], size=12, align="center")

    def sleeper(self, g: Gfx, t: float, dx: int = 0, dy: float = 0):
        spr, _ = _LIE[1 if breathe(t) > 0.5 else 0]
        g.blit(spr, FX + dx, FY + dy)

    def mx(self, g: Gfx, t: float):
        g.mx[7, :] = True
        mx_zzz(g, t)

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        backdrop(g, _BG)
        self.sky(g, 0)
        g.mx[7, :] = True
        if t < 1.9:
            yawn = 0.55 < t < 1.5
            g.blit(_SIT_YAWN if yawn else _SIT, FX - 2, SLAB - 30)
            if yawn and t > 0.8:
                g.text(FX + 30, SLAB - 34, "哈——", size=8)
            g.mx_set(3, 6)
            g.mx_set(4, 6)
            g.mx_set(3, 5)
            g.mx_set(4, 5)
        else:
            k = span(t, 1.9, 2.4)
            self.sleeper(g, 0, dy=-4 * (1 - ease_out_bounce(k)))
            if t > 2.4:
                zzz(g, *FACE, t - 2.4, self.seed)
                mx_zzz(g, t - 2.4)
        self.season(g, 0)
        self.counter(g, 0)
        if t < 0.7:
            iris(g, 50, 40, ease_out(t / 0.7) * 150, 0.8)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        dx = 0
        snore = ev(t, 89.0, 2.6, 45.0)       # 鼾声如雷：山摇、落石
        if snore and snore[1] < 1.6:
            dx = (1 if int(snore[1] * 20) % 2 else -1)
        g.img.paste(_BG, (dx, 0))
        self.sky(g, t)
        quote = ev(t, 127.0, 9.0, 12.0)
        if quote:
            g.d.rectangle((44, 0, 127, 13), fill=0)
            typewriter(g, 46, 1, "多百余日不起", quote[1], cps=4)
        else:
            self.counter(g, t, self.counter_a(t))
        self.season(g, t, dx)
        self.sleeper(g, t, dx)
        crane = ev(t, 61.0, 10.0, 20.0)
        big = None
        if crane:
            big = self.crane(g, crane[1])
        if snore:
            u = snore[1]
            z_glyph(g, FACE[0] + 4 + u * 20, FACE[1] - 6 - u * 10, int(4 + u * 5))
            for j in range(6):  # 岩檐上震落的碎石
                k = span(u, 0.1 + j * 0.12, 0.9 + j * 0.12)
                if 0 < k < 1:
                    x, y = 20 + j * 4 + rand(j, snore[0]) * 5, 9 + ease_in(k) * (SLAB - 12)
                    g.d.rectangle((x, y, x + 1, y + 1), fill=1)
            for j in range(3):  # 声浪
                r = (u * 3 - j * 0.4) * 10
                if 3 < r < 26:
                    g.d.arc((FACE[0] - r, FACE[1] - r, FACE[0] + r, FACE[1] + r), 250, 330, fill=1)
        elif big is None:
            zzz(g, *FACE, t, self.seed)
        self.mx(g, t)
        if snore and snore[1] < 1.6:
            g.mx_level = 3

    def crane(self, g: Gfx, u: float):
        """仙鹤衔诏飞来，诏书落在枕边；一声大鼾，诏书与鹤都被吹走。返回是否在打大鼾"""
        sx, sy = 84, SLAB - 13               # 诏书落点（脚边）
        if u < 3.0:                          # 飞来
            k = ease_out(u / 3.0)
            bx, by = lerp(134, sx + 4, k), lerp(14, sy - 12, k) + math.sin(u * 5) * 2
            g.blit(CRANE[int(u * 6) % 2], bx, by)
            self.scroll(g, bx + 1, by + 7)
            return None
        if u < 6.0:                          # 诏书落下，鹤在一旁扑扇等着
            k = ease_out_bounce(span(u, 3.0, 3.8))
            self.scroll(g, sx, lerp(sy - 5, sy, k))
            g.blit(CRANE[int(u * 4) % 2], sx + 2 + math.sin(u * 2) * 3, sy - 16 + math.sin(u * 3) * 2)
            zzz(g, *FACE, u, self.seed, on=0.6)
            return None
        # 一声大鼾：吹走
        k = ease_in(span(u, 6.6, 9.5))
        z = span(u, 6.0, 7.2)
        if z < 1:
            z_glyph(g, FACE[0] - 2 + z * 6, FACE[1] - 6 - z * 6, int(5 + z * 8))
        self.scroll(g, sx + k * 60, sy - k * 50, spin=k)
        g.blit(CRANE_R[int(u * 8) % 2], sx + 2 + k * 60, sy - 16 - k * 40)
        return True

    def scroll(self, g: Gfx, x: float, y: float, spin: float = 0.0):
        """一卷诏书（黄绢、两头轴）"""
        if spin > 0:  # 翻飞时卷成一根轴
            a = spin * 12
            g.d.line((x + 5 - math.cos(a) * 5, y + 5 - math.sin(a) * 5, x + 5 + math.cos(a) * 5,
                      y + 5 + math.sin(a) * 5), fill=1, width=2)
            return
        g.d.rectangle((x, y, x + 10, y + 11), fill=0, outline=1)
        g.d.line((x - 1, y, x + 11, y), fill=1)
        g.d.line((x - 1, y + 11, x + 11, y + 11), fill=1)
        g.text(x + 2, y + 3, "诏", size=8)

    def exit(self, g: Gfx, t: float):
        """醒来：睁眼，Z 散去，画面收拢到他身上"""
        h = self._ht
        backdrop(g, _BG)
        self.sky(g, h)
        if not ev(h, 127.0, 9.0, 12.0):
            self.counter(g, h, self.counter_a(h))
        self.season(g, h)
        self.sleeper(g, h)
        ex, ey = FX + 8, FY + 10
        if t > 0.2:  # 睁眼
            for x in (ex, ex + 5):
                g.d.rectangle((x, ey - 1, x + 2, ey + 1), fill=0)
                g.d.rectangle((x + 1, ey - 1, x + 2, ey), fill=1)
        if t < 0.5:
            zzz(g, *FACE, h + t * 3, self.seed, on=1 - t * 2)
        g.mx[7, :] = True
        if t > 0.2:
            g.mx_rows([0, 0, 0x66, 0x66, 0, 0, 0, 0xFF])
        r = lerp(115, 0, ease_in_out(span(t, 0.3, self.T["exit"] - 0.05)))
        iris(g, ex + 3, ey, r, 0.8)


_SIT = _sitting(False)
_SIT_YAWN = _sitting(True)
