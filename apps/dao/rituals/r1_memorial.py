"""焚表：经堂里一架表屏，挂着一幅白表；小道士执大笔一字一字写表文，写满钤印，卷起焚化上达。

依据：斋醮中的拜表（进表）科仪：写表、宣表、封表，焚化以达天庭；表文自右而左竖写，
常用程式语“伏以”“诚惶诚恐，稽首顿首”，结尾“谨表以闻”；“道经师宝”是道教法印的印文。

入场：卷着的表从表屏横杆上“唰”地垂下展开，小道士执笔走来，笔尖一点，墨星一闪。
持续：一轮 600 秒写二十字（四行，每行五字），自右而左、自上而下：小道士每写一行就往左挪一步，
      写字时按字的高低抬手、举笔，笔尖一笔一笔地点出字形（逐像素显现）；写完一字收笔，
      隔一阵对着墨迹吹一口气（嘟嘴、气流），或者拱手。烛火跳动。
      续：写满后小道士举起法印“咚”地钤在表尾（道经师宝），表从下往上烧起来，火舌、纸灰、火星往上飘，
      小道士跪拜；烧尽后横杆上垂下一幅新表，“第几表”加一。
中断：小道士把笔挂到表屏的笔钩上，拱手，牌子“停笔”。  恢复：取下笔，笔尖一点，墨星一闪。
圆满：法印钤上，整幅表燃起金火，纸灰聚成一只仙鹤扇着翅膀飞走，小道士跪拜，闪白，“谨表以闻”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.chars import daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import FLOOR, Clock, badge, floor, hit, mx_burst, pose_arm, star, title

PAPER = (66, 17, 97, 50)            # 表纸 x0, y0, x1, y1
COLS = (90, 83, 76, 69)             # 四行字（自右而左）的左边 x
ROWS = (20, 26, 32, 38, 44)         # 每行五字的上边 y
FIRST = 12.0                        # 第一字开始的秒数
PER = 28.0                          # 每字
WRITE = 4.0                         # 落笔写字的时长
RENEW = 9.0
SEAL = (69, 44)

GLYPHS = [
    "#####\n..#..\n#####\n..#..\n.###.",
    "..#..\n#####\n.#.#.\n#...#\n..#..",
    "#.#.#\n#####\n#.#.#\n#####\n#.#.#",
    "####.\n#..#.\n####.\n#..##\n####.",
    "#...#\n.#.#.\n..#..\n.#.#.\n#...#",
    ".#...\n#####\n.#.#.\n.####\n.#..#",
    "##.##\n.#.#.\n#####\n..#..\n#####",
    "#.###\n#..#.\n#.###\n#.#.#\n#.###",
    "..#..\n.###.\n#.#.#\n..#..\n.#.#.",
    "#####\n#...#\n#.#.#\n#...#\n#####",
]

SEAL_ART = pix.sprite("""
#######
#.#.#.#
##.#.##
#.###.#
##.#.##
#.#.#.#
#######
""")

FLAME = pix.frames("""
 #
###
#.#
---
  #
 ##
#.#
---
#
##
#.#
""")

CRANE = pix.frames("""
#.     .#
##.   .##
 ##. .##
  #####...
 .#####.##
   .#.   #
---
   ...
.#######.
#########.#
  .###.  ##
""")


def glyph_pts(i: int, seed: int):
    """第 i 字的笔画像素（按书写顺序）"""
    art = GLYPHS[int(rand(i, seed) * len(GLYPHS))]
    pts = []
    for y, ln in enumerate(art.split("\n")):
        for x, ch in enumerate(ln):
            if ch == "#":
                pts.append((x, y))
    # 先横后竖：按行优先，奇数行反过来，像一笔笔来回写
    return pts


def cell(i: int):
    return COLS[i // 5], ROWS[i % 5]


def stand_x(i: int) -> float:
    return COLS[i // 5] - 22


# ---------------------------------------------------------------- 背景与零件

def hall(g: Gfx, t: float):
    """经堂：背墙一排经柜格子、地面、左边烛台、表屏（横杆、立柱宝珠顶、底座）"""
    floor(g)
    g.d.line((0, FLOOR - 4, 127, FLOOR - 4), fill=1)
    for x in range(104, 128, 8):                       # 右边经柜格子
        for y in range(6, 44, 9):
            g.d.rectangle((x, y, x + 6, y + 7), outline=1)
            g.d.line((x + 2, y + 2, x + 4, y + 2), fill=1)
    g.d.line((102, 4, 127, 4), fill=1)
    g.d.line((102, 4, 102, FLOOR - 4), fill=1)
    x = 12                                             # 烛台
    g.d.rectangle((x - 1, 38, x + 1, 44), fill=1)
    g.px(x + 1, 40, 0)
    g.d.rectangle((x - 3, 45, x + 3, 45), fill=1)
    g.d.line((x, 46, x, FLOOR - 3), fill=1)
    g.d.rectangle((x - 3, FLOOR - 2, x + 3, FLOOR - 1), fill=1)
    pix.blit(g, pix.anim(FLAME, t, 7), x - 1, 34, outline=False)
    x0, y0, x1, y1 = PAPER                             # 表屏
    for px in (x0 - 3, x1 + 3):
        g.d.line((px, y0 - 4, px, FLOOR - 1), fill=1)
        g.d.ellipse((px - 1, y0 - 7, px + 1, y0 - 5), fill=1)
        g.d.rectangle((px - 3, FLOOR - 2, px + 3, FLOOR - 1), fill=1)
    g.d.rectangle((x0 - 4, y0 - 4, x1 + 4, y0 - 3), fill=1)
    g.d.line((x0 - 3, y0 - 3, x1 + 3, y0 - 3), fill=0)
    g.d.line((x0 - 3, y1 + 4, x1 + 3, y1 + 4), fill=1)


def paper(g: Gfx, top: float, bottom: float):
    """白表（双线边框），从 top 到 bottom 显示（展开 / 焚烧）"""
    x0, y0, x1, y1 = PAPER
    if bottom <= top:
        return
    g.d.rectangle((x0, top, x1, bottom), fill=1)
    g.d.line((x0 + 1, top, x0 + 1, bottom), fill=0)
    g.d.line((x1 - 1, top, x1 - 1, bottom), fill=0)
    if top <= y0 + 1:
        g.d.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill=0)
    if bottom >= y1 - 1:
        g.d.line((x0 + 1, y1 - 1, x1 - 1, y1 - 1), fill=0)
    g.d.rectangle((x0 - 1, bottom + 1, x1 + 1, bottom + 2), fill=1)   # 下轴


def ink(g: Gfx, n_done: int, cur: int, prog: float, seed: int, upto: float = 99):
    """写好的字（黑墨）+ 正在写的字的前 prog 部分"""
    for i in range(min(n_done + 1, 20)):
        gx, gy = cell(i)
        if gy > upto:
            continue
        pts = glyph_pts(i, seed)
        k = len(pts) if i < n_done else int(len(pts) * prog)
        for x, y in pts[:k]:
            g.px(gx + x, gy + y, 0)


def brush(g: Gfx, hx: float, hy: float, tx: float, ty: float):
    """大笔：笔杆（描黑边）+ 笔头 + 墨尖"""
    g.d.line((hx, hy, tx, ty), fill=0, width=3)
    g.d.line((hx, hy, tx, ty), fill=1)
    dx, dy = tx - hx, ty - hy
    n = math.hypot(dx, dy) or 1
    ux, uy = dx / n, dy / n
    bx, by = tx - ux * 3, ty - uy * 3
    g.d.ellipse((bx - 1, by - 1, bx + 1, by + 1), fill=1)
    g.px(tx, ty, 0)
    g.px(tx - ux, ty - uy, 1)
    g.d.rectangle((hx - 1, hy - 1, hx + 1, hy + 1), fill=1)


def writer(g: Gfx, x: float, t: float, row: int, tip, face: str = "normal", walk: bool = False):
    """按字的高低抬手：上两行举手、中两行斜举、最下一行平伸；笔尖落在 tip"""
    if walk:
        h = pose_arm(g, x, FLOOR, t, -30, legs="walk")
    elif row <= 1:
        h = daoshi(g, x, FLOOR, "raise", t, face=face)
    elif row <= 3:
        h = pose_arm(g, x, FLOOR, t, -30, face=face)
    else:
        h = pose_arm(g, x, FLOOR, t, 0, face=face)
    hx, hy = h["hand"]
    if tip is None:
        tip = (hx + 4, hy - 12)
    brush(g, hx, hy, *tip)
    return h


def mx_memo(g: Gfx, n_done: int, cur: int, t: float):
    """点阵：四行字（自右而左），写好的亮，正在写的闪"""
    for i in range(min(n_done + 1, 20)):
        c, r = i // 5, i % 5
        on = i < n_done or int(t * 4) % 2 == 0
        x = 6 - c * 2
        g.mx[1 + r, x] = on
        g.mx[1 + r, x + 1] = on and i < n_done
    g.mx[0, :] = True


def mx_fire(g: Gfx, t: float, h: float):
    for x in range(8):
        top = 7 - int(h * (3 + 3 * abs(math.sin(t * 9 + x * 1.7))))
        for y in range(max(top, 0), 8):
            g.mx[y, x] = True


# ---------------------------------------------------------------- 场景

@register
class BurnMemorial(Ritual):
    id = "r1.memorial"
    name = "焚表"
    desc = "小道士执大笔在表屏上一字字写表文，写满钤“道经师宝”印，表从下往上焚化；圆满时纸灰化鹤飞去"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 1.8, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)
        self.puffs = pix.Puffs(self.seed + 1)

    def progress(self, e: float):
        """(写好的字数, 当前字, 当前字的进度 0..1, 当前字已过秒数)"""
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            return 0, 0, 0.0, -1.0
        if k < FIRST:
            return 0, 0, 0.0, k - FIRST
        i = int((k - FIRST) // PER)
        if i >= 20:
            return 20, 19, 1.0, 99.0
        u = (k - FIRST) % PER
        return i, i, span(u, 1.0, 1.0 + WRITE), u

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int(e // self.CYCLE) + 1
        badge(g, 4, 4, label or (f"第{cn_num(n)}表" if n < 100 else f"{n}表"))

    def fx(self, g: Gfx, dt: float):
        self.puffs.step(dt)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self.clock(t)
        hall(g, t)
        x0, y0, x1, y1 = PAPER
        un = ease_out_bounce(span(t, 0.2, 1.2))
        paper(g, y0, lerp(y0, y1, un))
        if hit(t, 0.75, dt):
            pix.shake(g, t, 1.0)
        x = lerp(-14, stand_x(0), ease_out(span(t, 1.0, 3.2)))
        if t < 3.2:
            writer(g, x, t, 2, None, walk=True)
        else:
            q = ease_in_out(span(t, 3.4, 4.0)) * (1 - ease_in_out(span(t, 4.3, 4.9)))
            h = pose_arm(g, x, FLOOR, t, -30)
            hx, hy = h["hand"]
            gx, gy = cell(0)
            tip = (lerp(hx + 4, gx + 2, q), lerp(hy - 12, gy + 2, q))
            brush(g, hx, hy, *tip)
            if hit(t, 4.0, dt):
                self.sparks.burst(gx + 2, gy + 2, 8, 18, life=0.4, gravity=30)
        self.fx(g, dt)
        if t > 1.2:
            self.counter(g, 0.0)
        mx_memo(g, 0, 0, t)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self._renew(g, t, k, e, dt)
            return
        hall(g, t)
        x0, y0, x1, y1 = PAPER
        paper(g, y0, y1)
        n, cur, prog, u = self.progress(e)
        ink(g, n, cur, prog, self.seed)
        if n >= 20:   # 写完了，等着钤印（一轮最后几秒）
            daoshi(g, stand_x(19), FLOOR, "gongshou", t, face="happy")
        elif u < 0:
            writer(g, stand_x(0), t, 2, None)
        else:
            row = cur % 5
            prev_x = stand_x(cur - 1) if cur > 0 else stand_x(0)
            x = lerp(prev_x, stand_x(cur), ease_in_out(span(u, 0.0, 0.9)))
            gx, gy = cell(cur)
            pts = glyph_pts(cur, self.seed)
            if u < 0.9 and prev_x != stand_x(cur):
                writer(g, x, t, 2, None, walk=True)
            elif u < 1.0 + WRITE + 0.3:
                j = min(int(len(pts) * prog), len(pts) - 1)
                px, py = pts[j]
                lift = 0 if 1.0 <= u < 1.0 + WRITE else 1
                jig = math.sin(t * 25) * 0.6 if lift == 0 else 0
                tip = (gx + px + 1 + jig, gy + py - lift * 3)
                writer(g, x, t, row, tip)
                if hit(u, 1.0 + WRITE, dt):
                    self.sparks.burst(gx + 2, gy + 2, 4, 10, life=0.3, gravity=20)
            else:
                v = u - (1.0 + WRITE)
                c = (cur + self.seed) % 2
                if c == 0 and 9 <= v < 12:      # 对墨迹吹一口气
                    writer(g, x, t, 2, None, face="wow")
                    for j in range(3):
                        ph = (t * 3 + j * 0.33) % 1
                        pix.dotted(g, x + 9 + ph * 10, FLOOR - 26 + j * 2, x + 12 + ph * 10, FLOOR - 26 + j * 2, 2)
                elif c == 1 and 10 <= v < 12.4:
                    daoshi(g, x, FLOOR, "gongshou" if v < 11.2 else "bow", t)
                else:
                    writer(g, x, t, 2, None, face="happy" if v < 1.5 else "normal")
        self.fx(g, dt)
        self.counter(g, e)
        mx_memo(g, n, cur, t)

    def burn(self, g: Gfx, t: float, q: float, dt: float, golden: bool = False, n: int = 20):
        """表从下往上烧：q 0..1 烧到哪；火舌、纸灰、火星"""
        x0, y0, x1, y1 = PAPER
        edge = lerp(y1, y0, q)
        paper(g, y0, edge)
        ink(g, n, n, 0.0, self.seed, upto=edge - 5)
        if 0 < q < 1:
            g.d.line((x0, edge, x1, edge), fill=0)
            for x in range(x0, x1 + 1, 4):   # 火舌
                fr = FLAME[(int(t * 10) + x) % 3]
                pix.blit(g, fr, x - 1 + (x // 4) % 2, edge - 2 + ((x * 7) % 3) - 1, outline=False)
            if int(t * 30) % 2 == 0:
                self.sparks.burst(lerp(x0, x1, rand(int(t * 30))), edge, 2, 12, up=20, life=0.8, gravity=-10)
            if int(t * 30) % 5 == 0:
                self.puffs.emit(lerp(x0, x1, rand(int(t * 30) + 7)), edge - 3, vy=-10, life=1.4, rmax=1.6)
        if golden and 0 < q < 1:
            for j in range(6):
                a = t * 3 + j
                g.px((x0 + x1) / 2 + math.cos(a) * 20, edge + math.sin(a) * 6)

    def seal(self, g: Gfx, t: float, q: float, dt: float, x: float):
        """法印：举起 → “咚”地钤下；q 0..1"""
        sx, sy = SEAL
        if q <= 0:
            return
        if q < 0.6:
            h = daoshi(g, x, FLOOR, "raise", t)
            hx, hy = h["hand"]
            px, py = lerp(hx, sx, ease_in(q / 0.6)), lerp(hy - 8, sy, ease_in(q / 0.6))
            g.d.rectangle((px, py, px + 6, py + 6), fill=1)
            g.d.rectangle((px + 2, py - 3, px + 4, py - 1), fill=1)
        elif q < 1:
            pose_arm(g, x, FLOOR, t, 0)
        if q >= 0.6:
            pix.blit(g, SEAL_ART, sx, sy, outline=False, invert=True)

    def _renew(self, g: Gfx, t: float, k: float, e: float, dt: float):
        """钤印 → 从下往上焚化 → 新表垂下"""
        hall(g, t)
        x = stand_x(19)
        if k < 1.6:
            paper(g, PAPER[1], PAPER[3])
            ink(g, 20, 19, 1.0, self.seed)
            self.seal(g, t, span(k, 0.0, 1.2), dt, x)
            if hit(k, 0.72, dt):
                pix.shake(g, t, 1.0)
                self.sparks.burst(SEAL[0] + 3, SEAL[1] + 3, 10, 20, life=0.4, gravity=30)
            if k >= 1.2:
                daoshi(g, x, FLOOR, "idle", t)
        elif k < 7.0:
            q = span(k, 1.8, 6.6)
            self.burn(g, t, q, dt)
            if lerp(PAPER[3], PAPER[1], q) > SEAL[1] + 7:
                pix.blit(g, SEAL_ART, SEAL[0], SEAL[1], outline=False, invert=True)
            daoshi(g, x, FLOOR, "kneel" if 2.0 < k < 6.6 else "idle", t)
        else:
            un = ease_out_bounce(span(k, 7.0, 8.2))
            paper(g, PAPER[1], lerp(PAPER[1], PAPER[3], un))
            x2 = lerp(x, stand_x(0), ease_in_out(span(k, 7.4, 9.0)))
            writer(g, x2, t, 2, None, walk=k > 7.4, face="happy")
        self.fx(g, dt)
        self.counter(g, e if k >= 7.0 else e - k - 1)
        if 1.8 < k < 7.0:
            mx_fire(g, t, 1 - span(k, 1.8, 6.6) * 0.7)
        else:
            mx_memo(g, 20 if k < 1.8 else 0, 0, t)

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def hook(self, g: Gfx):
        """搁在表屏左柱笔钩上的笔"""
        hx = PAPER[0] - 3
        g.d.line((hx, 30, hx + 2, 30), fill=1)
        g.d.line((hx + 2, 31, hx + 2, 45), fill=0, width=3)
        g.d.line((hx + 2, 31, hx + 2, 45), fill=1)
        g.d.ellipse((hx + 1, 42, hx + 3, 45), fill=1)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        hall(g, t)
        paper(g, PAPER[1], PAPER[3])
        n, cur, prog, u = self.progress(e)
        ink(g, n, cur, prog, self.seed)
        x = stand_x(min(cur, 19))
        if t < 0.7:
            q = span(t, 0.0, 0.7)
            h = pose_arm(g, x, FLOOR, t, -30)
            hx, hy = h["hand"]
            brush(g, hx, hy, hx + 4 - q * 2, hy - 12 + q * 4)
        else:
            daoshi(g, x, FLOOR, "gongshou", t)
            self.hook(g)
        self.fx(g, dt)
        self.counter(g, e, "停笔" if t > 0.6 else None)
        mx_memo(g, n, cur, t)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        hall(g, t)
        paper(g, PAPER[1], PAPER[3])
        n, cur, prog, u = self.progress(e)
        ink(g, n, cur, prog, self.seed)
        x = stand_x(min(cur, 19))
        if t < 0.6:
            daoshi(g, x, FLOOR, "gongshou", t)
            self.hook(g)
        else:
            h = pose_arm(g, x, FLOOR, t, -30)
            hx, hy = h["hand"]
            tip = (hx + 4, hy - 12)
            brush(g, hx, hy, *tip)
            if hit(t, 0.9, dt):
                self.sparks.burst(tip[0], tip[1], 10, 20, up=6, life=0.5, gravity=30)
                pix.flash(g)
        self.fx(g, dt)
        self.counter(g, e, "停笔" if t < 0.6 else None)
        mx_memo(g, n, cur, t)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        hall(g, t)
        x = stand_x(19)
        if t < 1.4:
            paper(g, PAPER[1], PAPER[3])
            n, cur, prog, u = self.progress(e)
            ink(g, max(n, 0), cur, prog, self.seed)
            self.seal(g, t, span(t, 0.0, 1.2), dt, x)
            if t >= 1.2:
                daoshi(g, x, FLOOR, "idle", t)
            if hit(t, 0.72, dt):
                pix.shake(g, t, 1.0)
        else:
            q = span(t, 1.4, 3.0)
            self.burn(g, t, q, dt, golden=True, n=self.progress(e)[0])
            daoshi(g, x, FLOOR, "kneel" if t < 5.0 else "idle", t, face="happy" if t > 5.0 else "normal")
        if t > 2.6:    # 纸灰化鹤飞去
            q = span(t, 2.6, 6.0)
            cx = lerp((PAPER[0] + PAPER[2]) / 2, 150, ease_in(q))
            cy = lerp(PAPER[1] + 6, -10, q) + math.sin(t * 5) * 2
            pix.blit(g, pix.anim(CRANE, t, 4), cx - 5, cy - 3)
            if int(t * 20) % 2 == 0:
                g.px(cx - 8 - rand(int(t * 20)) * 6, cy + 4)
        if hit(t, 3.0, dt):
            pix.flash(g)
            self.sparks.burst((PAPER[0] + PAPER[2]) / 2, PAPER[1] + 4, 26, 40, up=14, life=1.2, gravity=30)
        if 3.0 < t < 3.3:
            pix.shake(g, t, 1.5)
        self.fx(g, dt)
        if t > 3.4:
            title(g, 32, 8, "谨表以闻", t, 3.4)
        if 1.4 < t < 3.0:
            mx_fire(g, t, 1.0)
        else:
            mx_memo(g, 20, 19, t)
        mx_burst(g, t, 3.0)
