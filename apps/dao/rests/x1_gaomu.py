"""形如槁木：南郭子綦隐几而坐，仰天而嘘，一动不动。坐得久了，草长上席、藤爬上几、蘑菇冒头，
鸟来头顶筑巢、下蛋、孵出雏鸟；一声长嘘，鸟飞草伏，一切又散了——“今者吾丧我”。

依据：《庄子·齐物论》：“南郭子綦隐机而坐，仰天而嘘，荅焉似丧其耦。颜成子游立侍乎前，曰：‘何居乎？
形固可使如槁木，而心固可使如死灰乎？’……子綦曰：‘……今者吾丧我，汝知之乎？’”
又《大宗师》颜回“坐忘”：“堕肢体，黜聪明，离形去知，同于大通，此谓坐忘。”
"""
from __future__ import annotations

import math

from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, noise, rand, span
from ..engine.fx import typewriter
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Rest, register
from .x1_common import Pen, backdrop, ev, halo, iris

GROUND = 58
GROW = 150.0       # 一轮“长满”的秒数（最后一段长嘘、散去）
EXHALE = 138.0     # 长嘘的时刻
NEST = (57, 9)     # 头顶鸟巢中心
FACE = (73, 14)    # 嘴


def _bg():
    p = Pen()
    # 月洞窗（身后的大圆窗），窗棂
    p.ellipse((36, 1, 92, 57), fill=0)
    p.ellipse((39, 4, 89, 54), fill=None)
    for x in (52, 64, 76):
        p.line([(x, 4), (x, 30)], 1)
    p.line([(40, 18), (88, 18)])
    p.line([(39, 30), (89, 30)])
    # 席
    p.rect((26, GROUND - 2, 104, GROUND + 1), fill=0.5)
    p.line([(0, GROUND + 2), (128, GROUND + 2)])
    # 凭几：弯弯的几面，两条曲腿
    p.chord((22, 36, 52, 46), 180, 360, fill=0.5)
    p.line([(26, 41), (24, 48), (28, GROUND - 3)], 1, 2)
    p.line([(48, 41), (50, 48), (46, GROUND - 3)], 1, 2)
    return p.image()


def _sage(ex: float) -> Sprite:
    """隐几而坐：面朝右，仰头；左肘搭在几上。ex = 呼气时张嘴"""
    p = Pen(52, 50)
    # 盘腿
    p.ellipse((8, 38, 50, 48), fill=0.45)
    # 身子
    p.poly([(14, 40), (18, 22), (26, 17), (36, 17), (42, 24), (46, 40)], fill=0.22)
    p.line([(30, 20), (28, 40)])                      # 交领
    p.line([(36, 18), (30, 28)])
    # 搭在几上的胳膊（宽袖垂下）
    p.poly([(20, 22), (12, 30), (2, 30), (2, 34), (14, 36), (24, 30)], fill=0)
    p.line([(4, 34), (10, 40)])
    # 放在膝上的另一只手
    p.poly([(40, 26), (46, 36), (40, 38), (36, 32)], fill=0)
    # 头：仰起
    p.ellipse((22, 4, 38, 20), fill=0)
    p.ellipse((18, 2, 24, 8), fill=1)                 # 发髻
    p.line([(16, 6), (26, 0)], 0)
    p.line([(29, 9), (32, 8)])                        # 合着的眼（朝上）
    p.px(38, 9)                                       # 鼻
    # 须：顺着仰起的下巴往胸前垂
    p.poly([(31, 16), (37, 14), (40, 22), (36, 28), (33, 22)], fill=1)
    if ex:
        p.ellipse((35, 11, 38, 14), fill=0, outline=1)
    return p.sprite()


BIRD = [halo(Sprite("""
  .##....
  #.###..
  .######
  ..####.
  ...#.#.
""")), halo(Sprite("""
  ##...##
  .##.##.
  ..###..
  ..##...
""")), halo(Sprite("""
  .......
  ..###..
  .##.##.
  ##...##
"""))]

_A = {}


def _assets():
    if not _A:
        _A.update(bg=_bg(), sage=_sage(0), sage_ex=_sage(1))


@register
class GaoMu(Rest):
    id = "x1.gaomu"
    name = "形如槁木"
    desc = "南郭子綦隐几仰天而坐，纹丝不动：草上席、藤爬几、鸟来头顶筑巢孵雏；一声长嘘，鸟飞草伏，从头再来"
    T = {"enter": 3.0, "exit": 1.3}
    SX, SY = 36, GROUND - 49

    def setup(self):
        _assets()
        self._ht = 0.0

    # ------------------------------------------------------------ 长出来的东西（u = 本轮秒数）

    def grass(self, g: Gfx, u: float, wind: float = 0.0):
        for i in range(10):
            x = 28 + i * 8 + int(rand(i, self.seed) * 4)
            h = 7 * span(u, 4 + i * 4, 30 + i * 4) * (0.6 + 0.4 * rand(i + 9, self.seed))
            if h < 1:
                continue
            bend = wind * h * 0.6
            g.d.line((x, GROUND - 2, x + bend, GROUND - 2 - h), fill=1)
            g.d.line((x + 1, GROUND - 2, x + 2 + bend, GROUND - 1 - h * 0.7), fill=1)

    def vine(self, g: Gfx, u: float):
        """藤从几腿爬上几面、搭到胳膊上"""
        k = span(u, 20, 80)
        if k <= 0:
            return
        path = [(24, GROUND - 3), (22, 50), (25, 45), (22, 41), (26, 37), (32, 36), (38, 35), (42, 37)]
        n = (len(path) - 1) * k
        pts = path[: int(n) + 1]
        if int(n) < len(path) - 1:
            a, b = path[int(n)], path[int(n) + 1]
            f = n - int(n)
            pts = pts + [(lerp(a[0], b[0], f), lerp(a[1], b[1], f))]
        g.d.line(pts, fill=1)
        for j, (x, y) in enumerate(pts[1:]):
            s = 1 if j % 2 else -1
            g.d.ellipse((x + s * 2 - 1, y - 2, x + s * 2 + 1, y), fill=1)

    def mushroom(self, g: Gfx, u: float):
        k = ease_out_back(span(u, 45, 48))
        if k <= 0:
            return
        x, y = 96, GROUND - 2
        h = 5 * k
        g.d.line((x, y, x, y - h), fill=1, width=2)
        g.d.chord((x - 4 * k, y - h - 3 * k, x + 5 * k, y - h + 2 * k), 180, 360, fill=1)
        g.px(x - 1, y - h - 1, 0)

    def web(self, g: Gfx, u: float):
        """几下面结出一张蛛网"""
        k = span(u, 30, 70)
        if k <= 0:
            return
        cx, cy = 37, 50
        n = int(6 * min(1, k * 2))
        for i in range(n):
            a = math.pi * (0.1 + i * 0.16)
            g.d.line((cx, cy, cx + math.cos(a) * 9, cy - math.sin(a) * 6 + 6), fill=1)
        rings = int(3 * max(0, k * 2 - 1))
        for r in range(1, rings + 1):
            g.d.arc((cx - r * 3, cy - r * 2 + 4, cx + r * 3, cy + r * 2 + 4), 200, 340, fill=1)

    def nest(self, g: Gfx, u: float, t: float, blown: float = 0.0):
        """鸟：60 秒飞来衔枝筑巢，85 秒趴窝下蛋，115 秒孵出雏鸟"""
        twig = span(u, 64, 82)
        x, y = NEST
        if twig > 0 and blown < 1:
            for j in range(int(twig * 8)):
                a = rand(j, 3) * math.pi
                g.d.line((x - 6 + j * 1.5, y + 2 - (j % 2), x - 4 + j * 1.5 + math.cos(a) * 3, y + math.sin(a)), fill=1)
            if twig >= 1:
                g.d.arc((x - 7, y - 3, x + 7, y + 4), 0, 180, fill=1)
        if 60 <= u < 64:                   # 飞来
            k = ease_out((u - 60) / 4)
            g.blit(BIRD[1 + int(t * 8) % 2], lerp(140, x - 3, k), lerp(-6, y - 8, k))
        elif 64 <= u < 82:                 # 来回衔枝
            k = (u - 64) % 4.5 / 4.5
            bx = x - 3 + math.sin(k * math.pi) * 40
            by = y - 8 - math.sin(k * math.pi) * 6
            spr = BIRD[0] if k < 0.08 or k > 0.92 else BIRD[1 + int(t * 8) % 2]
            g.blit(spr if bx < x + 10 else spr.flip(), bx, by)
            if 0.3 < k < 0.7:
                g.d.line((bx + 6, by + 3, bx + 9, by + 2), fill=1)
        elif 82 <= u < EXHALE:             # 趴窝；蛋；雏鸟
            bob = 1 if int(t * 1.5) % 4 == 0 else 0
            if u < 112 or u > 116:
                g.blit(BIRD[0], x - 3, y - 7 - bob)
            else:                          # 起身看蛋
                g.blit(BIRD[0], x + 4, y - 9)
                g.d.ellipse((x - 2, y - 3, x + 1, y + 1), fill=1)
            if u >= 116:                   # 雏鸟探头
                if int(t * 3) % 3:
                    g.d.rectangle((x - 6, y - 4, x - 4, y - 2), fill=1)
                    g.px(x - 7, y - 3)
                if u < 121:
                    g.text(x - 18, y - 9, "啾", size=8)
        elif u >= EXHALE and blown < 1:    # 被长嘘惊飞
            k = ease_in(blown)
            for j, (dx, dy) in enumerate(((0, 0), (-6, 3))):
                if j == 1 and u - EXHALE < 0:
                    continue
                g.blit(BIRD[1 + int(t * 10) % 2], x - 3 + dx - k * 30, y - 8 + dy - k * 30)

    def mx_sprout(self, g: Gfx, u: float, t: float):
        """点阵：一棵小苗随这一轮慢慢长高，鸟来时顶上停一只"""
        h = int(span(u, 2, 100) * 6) + 1
        for y in range(7, 7 - h, -1):
            g.mx_set(3, y)
        if h >= 3:
            g.mx_set(2, 7 - h + 2)
        if h >= 5:
            g.mx_set(4, 7 - h + 3)
        if 82 <= u < EXHALE:
            g.mx_set(4, 0)
            g.mx_set(5, 0)
            g.mx_set(5, 1)

    # ------------------------------------------------------------ 阶段

    def scene(self, g: Gfx, t: float, u: float, ex: bool = False, wind: float = 0.0, blown: float = 0.0):
        g.blit(_A["sage_ex"] if ex else _A["sage"], self.SX, self.SY)
        fade = 1 - span(blown, 0.4, 1.0)
        if fade > 0:
            uu = u if blown <= 0 else EXHALE * fade
            self.vine(g, uu)
            self.web(g, uu)
            self.mushroom(g, uu)
            self.grass(g, uu, wind)
        self.nest(g, u, t, blown)

    def enter(self, g: Gfx, t: float):
        """入座：人从下面“坐”进画面，几放好，仰起头"""
        backdrop(g, _A["bg"])
        k = ease_out_bounce(span(t, 0.3, 1.4))
        g.blit(_A["sage"], self.SX, self.SY + (1 - k) * 50)
        g.d.rectangle((0, GROUND + 3, 127, 63), fill=0)
        if t > 1.6:
            a = span(t, 1.6, 2.8)
            g.vtext(112, 4, "形如槁木"[: int(a * 4 + 0.5)])
        self.mx_sprout(g, 0, t)
        if t < 0.4:
            iris(g, 64, 32, ease_out(t / 0.4) * 150, 0.8)

    def hold(self, g: Gfx, t: float):
        self._ht = t
        backdrop(g, _A["bg"])
        u = t % GROW
        blown = span(u, EXHALE + 0.5, EXHALE + 4.0)
        ex = EXHALE <= u < EXHALE + 3.5
        wind = math.sin(t * 0.7) * 0.15 + (ease_out(span(u, EXHALE, EXHALE + 1.0)) * 1.2 * (1 - blown) if u >= EXHALE else 0)
        self.scene(g, t, u, ex, wind, blown)
        if ex:  # 仰天而嘘：一道长长的气往上散
            k = u - EXHALE
            for j in range(18):
                q = j / 18
                if q > k / 1.5:
                    break
                x = FACE[0] + 2 + q * 40 + math.sin(q * 8 - k * 4) * 2
                y = FACE[1] - 2 - q * 14
                if rand(j + int(k * 6), 3) > q * 0.6:
                    g.px(x, y)
            if k > 0.6:
                g.d.rectangle((96, 0, 127, 13), fill=0)
                typewriter(g, 126, 1, "嘘——", k - 0.6, cps=3, align="right")
        if u < 16:   # 一轮开头题“形如槁木”，中段“心如死灰”，长嘘之后“吾丧我”
            a = 1.0 if t < GROW else span(u, 0, 2.0)
            g.vtext(112, 4, "形如槁木"[: int(a * 4 + 0.5)])
        elif 70 <= u < 82:
            g.vtext(112, 4, "心如死灰"[: int(span(u, 70, 72) * 4 + 0.5)])
        elif EXHALE + 4 <= u < GROW:
            g.vtext(112, 4, "吾丧我"[: int(span(u, EXHALE + 4, EXHALE + 6) * 3 + 0.5)])
        self.mx_sprout(g, u if u < EXHALE else EXHALE * (1 - blown), t)

    def exit(self, g: Gfx, t: float):
        """出定：睁眼，低下头来，画面收拢"""
        h = self._ht
        backdrop(g, _A["bg"])
        u = h % GROW
        self.scene(g, h, u)
        if t > 0.25:  # 睁眼
            x, y = self.SX + 29, self.SY + 8
            g.d.line((x, y + 1, x + 3, y), fill=0)
            g.d.rectangle((x + 1, y - 1, x + 2, y), fill=1)
        self.mx_sprout(g, min(u, EXHALE), h)
        iris(g, self.SX + 30, self.SY + 14, lerp(120, 0, ease_in_out(span(t, 0.35, self.T["exit"] - 0.05))), 0.8)
