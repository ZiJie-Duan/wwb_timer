"""壶中天：散市了，卖药的老翁一跳钻进挂在肆头的葫芦里睡觉。葫芦随鼾声一鼓一鼓、葫芦口冒 Z，
壶身开一扇小圆窗，里面另有日月星辰；偶尔打个嗝蹦一下，楼上的费长房探出头来偷看。

依据：《后汉书·方术列传·费长房》：“市中有老翁卖药，悬一壶于肆头，及市罢，辄跳入壶中。市人莫之见，
唯长房于楼上睹见之。”后长房随翁入壶，“唯见玉堂严丽，旨酒甘肴盈衍其中”。成语“悬壶济世”“壶中日月”出此。
"""
from __future__ import annotations

import math

from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Pen, backdrop, breathe, ev, halo, iris, z_glyph

PIV = (64, 7)      # 挂绳在檐下的点
STREET = 60


def _bg():
    p = Pen()
    # 屋檐（瓦）横贯上方
    p.poly([(0, 0), (128, 0), (128, 5), (0, 5)], fill=0.5)
    p.line([(0, 6), (128, 6)])
    for x in range(2, 128, 6):
        p.arc((x - 3, 3, x + 3, 9), 0, 180)
    # 右上：楼上的窗（费长房在这里）
    p.rect((100, 12, 124, 30), fill=0)
    p.line([(112, 12), (112, 30)])
    p.line([(100, 31), (124, 31)])
    # 左：药幡
    p.line([(10, 7), (10, 44)])
    p.rect((11, 10, 25, 36), fill=0)
    p.line([(11, 36), (14, 40), (18, 36), (22, 40), (25, 36)])
    # 摊子：桌、药包
    p.rect((30, 54, 98, 57), fill=0.5)
    p.line([(33, 57), (33, STREET)])
    p.line([(95, 57), (95, STREET)])
    for x in (36, 46, 82, 90):
        p.poly([(x, 54), (x + 3, 49), (x + 6, 54)], fill=0.6)
        p.px(x + 3, 48)
    p.line([(0, STREET), (128, STREET)])
    for i in range(14):
        p.px(int(rand(i, 5) * 128), STREET + 2 + int(rand(i, 6) * 2))
    return p.image()


def _old_man(f: int) -> Sprite:
    """壶公：白须老翁，拄杖（f = 走路的帧）"""
    p = Pen(12, 16)
    p.ellipse((3, 0, 8, 5), fill=0)
    p.poly([(4, 4), (7, 4), (6, 8)], fill=1)               # 须
    p.poly([(3, 5), (8, 5), (9, 13), (2, 13)], fill=0.4)   # 袍
    p.line([(10, 3), (10, 15)])                             # 杖
    p.line([(8, 7), (10, 8)])
    if f:
        p.line([(4, 13), (3, 15)])
        p.line([(7, 13), (8, 15)])
    else:
        p.line([(5, 13), (5, 15)])
        p.line([(6, 13), (7, 15)])
    return halo(p.sprite())


PEEK = halo(Sprite("""
  ..####..
  .######.
  ########
  #......#
  #.#..#.#
  #......#
  .#....#.
  ..####..
"""))

def _gourd(s: int) -> Sprite:
    """葫芦（s = 鼓起几像素）：抖动灰度的壶身、腰绳、高光"""
    p = Pen(34, 42)
    c = 16
    R, r = 12 + s, 6 + s * 0.5
    p.ellipse((c - R, 25 - R, c + R, 25 + R), fill=0.3)
    p.ellipse((c - r, 9 - r, c + r, 9 + r), fill=0.3)
    p.rect((c - 3, 14, c + 3, 17), fill=0.3, outline=None)
    p.line([(c - 4, 15), (c + 4, 15)], 1, 2)                # 腰绳
    p.line([(c + 3, 16), (c + 6, 23)])
    p.line([(c + 4, 16), (c + 2, 23)])
    p.arc((c - r + 2, 9 - r + 2, c + r - 2, 9 + r - 2), 195, 250)          # 高光
    p.arc((c - R + 3, 25 - R + 3, c + R - 3, 25 + R - 3), 190, 240)
    p.arc((c - R + 4, 25 - R + 4, c + R - 4, 25 + R - 4), 195, 230)
    return p.sprite()


_A = {}


def _assets():
    if not _A:
        _A.update(bg=_bg(), man=[_old_man(0), _old_man(1)], gourd=[_gourd(0), _gourd(1), _gourd(2)])


@register
class HuGong(Rest):
    id = "x1.hugong"
    name = "壶中天"
    desc = "散市后卖药老翁跳进肆头的葫芦里睡觉：葫芦随鼾一鼓一鼓，圆窗里另有日月；打嗝蹦跳、楼上长房偷看"
    T = {"enter": 3.4, "exit": 1.3}

    def setup(self):
        _assets()
        self._ht = 0.0

    # ------------------------------------------------------------ 葫芦

    def at(self, d: float, th: float) -> tuple[float, float]:
        """挂绳下 d 像素处（随摆角 th）"""
        return PIV[0] + math.sin(th) * d, PIV[1] + math.cos(th) * d

    def gourd(self, g: Gfx, t: float, th: float, swell: float = 0.0, hop: float = 0.0, window: float = 1.0,
              cork: float = 0.0):
        """葫芦：上小下大，腰系红绳，下肚开一扇圆窗（壶中天地）。返回 (壶口, 肚心)"""
        dy = -hop
        sx, sy = self.at(10, th)
        g.d.line((PIV[0], PIV[1], sx, sy + dy), fill=1)
        ox = math.sin(th) * 26
        spr = _A["gourd"][min(2, max(0, int(round(swell))))]
        gx, gy = PIV[0] + ox - 16, PIV[1] + 11 + dy
        g.blit(spr, gx, gy)
        cx, cy = PIV[0] + math.sin(th) * 11, PIV[1] + 10 + dy - cork * 5     # 塞子
        g.d.rectangle((cx - 2, cy - 1, cx + 2, cy + 2), fill=1)
        bx, by = gx + 16, gy + 25
        if window > 0:
            self.inner(g, t, bx, by + 1, 7 * window)
        return (gx + 16, gy), (bx, by)

    def inner(self, g: Gfx, t: float, cx: float, cy: float, rr: float):
        """圆窗里的壶中天：日月轮转、小殿、星"""
        g.d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=0, outline=1)
        if rr < 4:
            return
        day = (t % 30) < 15
        a = (t % 15) / 15 * math.pi
        ox, oy = cx - math.cos(a) * (rr - 3), cy - math.sin(a) * (rr - 3) + 1
        if day:
            g.d.ellipse((ox - 1.5, oy - 1.5, ox + 1.5, oy + 1.5), fill=1)
        else:
            g.d.ellipse((ox - 1.5, oy - 1.5, ox + 1.5, oy + 1.5), fill=1)
            g.d.ellipse((ox - 0.5, oy - 2, ox + 2.5, oy + 1), fill=0)
            for i in range(3):
                if noise(t * 2 + i * 5, 3) > 0.4:
                    g.px(cx - 4 + i * 4, cy - 4 + (i % 2) * 2)
        # 小殿：屋顶 + 两柱
        g.d.polygon([(cx - 5, cy + 2), (cx, cy - 1), (cx + 5, cy + 2)], fill=1)
        g.d.line((cx - 3, cy + 2, cx - 3, cy + 5), fill=1)
        g.d.line((cx + 3, cy + 2, cx + 3, cy + 5), fill=1)
        g.d.line((cx - rr + 2, cy + 5, cx + rr - 2, cy + 5), fill=1)

    def snore_z(self, g: Gfx, mouth, t: float, on: float = 1.0):
        """葫芦口冒出的 Z（随呼气）"""
        for j in range(3):
            k = int(t // 1.6) - j
            p = (t - k * 1.6) / 4.8
            if not 0 <= p < 1 or rand(k, 5) > on:
                continue
            s = int(2 + p * 4)
            z_glyph(g, mouth[0] + 5 + p * 24, mouth[1] + 2 - p * 9 - s + math.sin(t * 2 + k) * 1.5, s)

    def mx_gourd(self, g: Gfx, swell: float, t: float):
        big = swell > 0.5
        g.mx_rows([0x10, 0x38, 0x38, 0x10, 0x7C if big else 0x38, 0xFE if big else 0x7C, 0xFE if big else 0x7C,
                   0x7C if big else 0x38])
        z = int(t / 0.8) % 3
        g.mx_set(6 + (z > 1), 1 - min(z, 1))

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        backdrop(g, _A["bg"])
        g.text(18, 13, "药", align="center")
        th = 0.0
        if t < 1.4:   # 老翁拄杖走到摊前
            k = t / 1.4
            x = lerp(-10, 44, k)
            g.blit(_A["man"][int(t * 6) % 2], x, STREET - 16 + (int(t * 6) % 2) * 0)
            self.gourd(g, t, 0.0, window=0)
            g.mx_rows([0x10, 0x38, 0x38, 0x10, 0x38, 0x7C, 0x7C, 0x38])
        elif t < 2.2:  # 纵身一跳，缩进葫芦口
            k = (t - 1.4) / 0.8
            mouth = (PIV[0], PIV[1] + 11)
            x = lerp(44, mouth[0] - 5, k)
            y = lerp(STREET - 16, mouth[1] - 6, k) - math.sin(k * math.pi) * 18
            if k < 0.85:
                sz = 1 - k * 0.6
                spr = _A["man"][0]
                if sz > 0.7:
                    g.blit(spr, x, y)
                else:
                    g.d.ellipse((x + 3, y + 3, x + 3 + 6 * sz, y + 3 + 8 * sz), fill=1)
            squash = 2 * math.sin(span(t, 2.0, 2.2) * math.pi)
            self.gourd(g, t, 0.0, swell=squash, window=0)
            g.mx_rows([0x10, 0x38, 0x38, 0x10, 0x38, 0x7C, 0x7C, 0x38])
        else:          # 葫芦一晃，圆窗亮起，打起鼾来
            k = t - 2.2
            th = math.sin(k * 5) * 0.12 * (1 - span(k, 0, 1.2))
            win = ease_out_back(span(k, 0.3, 0.9))
            mouth, _ = self.gourd(g, t, th, swell=breathe(t) * 1.5, window=win)
            if k > 0.8:
                self.snore_z(g, mouth, k - 0.8, on=0.8)
            self.mx_gourd(g, breathe(t), t)
        if t < 0.5:
            iris(g, 64, 32, ease_out(t / 0.5) * 150, 0.6)

    def sway(self, t: float) -> float:
        return math.sin(t * 0.55) * 0.05 + (noise(t * 0.2, self.seed) - 0.5) * 0.04

    def hold(self, g: Gfx, t: float):
        self._ht = t
        backdrop(g, _A["bg"])
        th = self.sway(t)
        hop, cork = 0.0, 0.0
        hic = ev(t, 41.0, 1.6, 17.0)       # 打嗝：一蹦，塞子跳起
        if hic:
            u = hic[1]
            hop = 5 * math.sin(math.pi * span(u, 0, 0.5)) if u < 0.5 else 1.5 * math.sin(math.pi * span(u, 0.5, 0.8))
            cork = math.sin(math.pi * span(u, 0, 0.9))
            th += math.sin(u * 9) * 0.06 * (1 - u / 1.6)
        swell = breathe(t) * 1.6
        mouth, belly = self.gourd(g, t, th, swell=swell, hop=hop, cork=cork)
        if hic and hic[1] < 1.2:
            g.text(mouth[0] + 9, mouth[1] - 9, "嗝")
            g.mx_level = 3
        else:
            self.snore_z(g, mouth, t)
        g.text(18, 13, "药", align="center")
        peek = ev(t, 67.0, 9.0, 35.0)      # 楼上的费长房探头偷看
        if peek:
            self.peek(g, peek[1])
        txt = ev(t, 89.0, 8.0, 60.0)
        if txt and not peek:
            g.d.rectangle((70, 36, 127, 50), fill=0)
            typewriter(g, 126, 38, "壶中日月长", txt[1], cps=4, size=8, align="right")
        self.mx_gourd(g, swell / 1.6, t)

    def peek(self, g: Gfx, u: float):
        """窗里冒出半个脑袋，眼珠跟着葫芦转"""
        up = ease_out(span(u, 0.3, 1.2)) * (1 - ease_in(span(u, 7.8, 8.8)))
        if up <= 0:
            return
        x, y = 108, 31 - up * 9
        g.blit(PEEK, x - 1, y - 1)
        g.d.rectangle((99, 31, 125, 34), fill=0)    # 窗台挡住下半
        g.d.line((100, 31, 124, 31), fill=1)
        if up > 0.8 and 2.0 < u < 7.5:
            typewriter(g, 126, 35, "唯长房睹见", u - 2.0, cps=4, size=8, align="right")
            if 2.0 < u < 2.8:
                g.text(119, 14, "!", size=8)

    def exit(self, g: Gfx, t: float):
        """醒了：塞子崩开，老翁从壶口跳出来，画面收拢"""
        h = self._ht
        backdrop(g, _A["bg"])
        th = self.sway(h) + math.sin(t * 14) * 0.05 * (1 - span(t, 0, 0.6))
        mouth, belly = self.gourd(g, h + t, th, swell=1.6 * (1 - span(t, 0, 0.3)), cork=span(t, 0, 0.3),
                                  window=1 - span(t, 0.2, 0.5))
        if t > 0.2:
            k = span(t, 0.2, 0.8)
            x = lerp(mouth[0] - 5, 80, k)
            y = lerp(mouth[1] - 10, STREET - 16, k) - math.sin(k * math.pi) * 14
            g.blit(_A["man"][0], x, y)
        g.mx_rows([0x10, 0x38, 0x38, 0x10, 0x38, 0x7C, 0x7C, 0x38])
        g.text(18, 13, "药", align="center")
        iris(g, 70, 36, lerp(130, 0, ease_in_out(span(t, 0.45, self.T["exit"] - 0.05))), 0.8)
