"""放河灯：中元夜，满月当空、远山如墨；小道士在江边石阶上跪下，一盏盏把莲花灯放进水里，灯顺水漂向天边。

依据：农历七月十五中元节，道经以为“地官赦罪”之日，宫观设中元普度；当夜放水灯（河灯、荷花灯），
中元也有烧法船的习俗（中国非遗网“中元节”）。七月十五是满月。

入场：夜空、满月、远山、江面渐显，江心荡开几圈涟漪；小道士走到江边石阶上，对江拱手作揖。
持续：每 60 秒放一盏（一轮十盏 = 600 秒）：转身从灯篮里取灯 → 跪下 → 双手送灯入水（涟漪一圈圈）→ 起身作揖。
      每盏用 300 秒漂到天边，一路先快后慢、越漂越小越高，同时漂着五盏；灯火逐帧跳动，水里倒影碎成几段，
      灯随波轻轻起伏。水纹缓缓横移，月影在水里碎成一串；隔一阵一条鱼跃出水面“扑通”溅起水花，萤火虫一闪一闪。
      续：远处一只纸扎法船（两层楼、风帆、窗里亮灯）从左到右驶过天边，小道士拱手，“第几盏”从头数起。
中断：江雾从两岸漫来，水上的灯暗成一点，牌子“暂歇”。  恢复：小道士剑指一点，雾散，灯火一盏盏复明。
圆满：江上每盏灯的火光离开灯，升空化作星点，满月放光，小道士跪拜，闪白，“中元普度”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, lerp, rand, span
from ..engine.chars import daoshi
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r1_common import Clock, badge, hit, mx_art, mx_burst, pose_arm, ring_dots, star, title

BANK = 54                # 石阶顶面（小道士站的地面）
HORIZON = 27
DX = 24                  # 小道士
BASKET_X = 7
DROP = (42, 58)          # 放灯入水的位置
EVERY = 60.0
LIFE = 300.0
RENEW = 8.0
MOON = (104, 10)

LOTUS = pix.sprite("""
  #  .  #
  #.#.#.#
 ##.#.#.##
#.##.#.##.#
.#########.
 ..#####..
""")

LOTUS_MID = pix.sprite("""
# # #
.###.
 ###
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

FISH = pix.frames("""
  .##.
.######.#
 .####.##
  .##.
""")

BOAT = pix.sprite("""
        #
       ###      #
    .#######.  ###
    .#.#.#.#.  #.#
  ..#########..###
  .#.#.##.#.#.#####
 ####################
  ##################
   .##############.
""")


def scene_bg(g: Gfx, t: float, show: float = 1.0):
    """夜空：满月（月面暗斑）、星星、远山剪影、江面水纹、月影、前景石阶"""
    mx, my = MOON
    g.d.ellipse((mx - 7, my - 7, mx + 7, my + 7), fill=1)
    for x, y in ((-3, -2), (2, 1), (-1, 3), (3, -3)):
        g.px(mx + x, my + y, 0)
    g.px(mx - 2, my - 2, 0)
    for i in range(14):
        x, y = rand(i, 3) * 128, rand(i + 20, 3) * 18
        if abs(x - mx) < 10 and abs(y - my) < 10:
            continue
        if (t * 0.7 + rand(i + 40, 3)) % 1 < 0.8:
            g.px(x, y)
    ridge = [(0, 24), (12, 19), (22, 22), (36, 16), (50, 22), (60, 20), (74, 24), (88, 20), (100, 23), (114, 18),
             (127, 22)]
    g.d.polygon(ridge + [(127, HORIZON), (0, HORIZON)], fill=0)
    g.d.line(ridge, fill=1)
    for x in range(2, 128, 4):                        # 山脚一抹雾（稀点）
        g.px(x + (x // 4) % 2 * 2, HORIZON - 2)
    g.d.line((0, HORIZON, 127, HORIZON), fill=1)
    for row in range(8):                              # 水纹：越近越长越稀
        y = HORIZON + 3 + row * 4 + row * row // 5
        if y > 63:
            break
        L = 1 + row
        gap = 15 + row * 4
        off = int(t * (1.5 + row * 0.5)) + row * 7
        for x in range(-gap, 128 + gap, gap):
            xx = (x + off) % (128 + gap) - gap
            g.d.line((xx, y, xx + L, y), fill=1)
    for j in range(6):                                # 月影
        y = HORIZON + 3 + j * 4
        w = 3 + j + int(math.sin(t * 2 + j) * 1.5)
        x = mx + math.sin(t * 1.3 + j * 1.7) * 1.5
        pix.dotted(g, x - w, y, x + w, y, 2, j)
    # 前景左下的石阶
    pts = [(0, BANK), (32, BANK), (34, BANK + 1), (34, BANK + 4), (38, BANK + 5), (38, 63), (0, 63)]
    g.d.polygon(pts, fill=0)
    g.d.line(pts[:-1], fill=1)
    for x in range(5, 32, 9):
        g.d.line((x, BANK + 1, x, BANK + 3), fill=1)
    g.d.line((0, BANK + 4, 33, BANK + 4), fill=1)
    pix.checker(g, (1, BANK + 5, 37, 64), 0.25)


def lamp_pos(age: float, lane: int):
    """放下后 age 秒的位置与大小（0..1，1 = 近处）"""
    a = min(age / LIFE, 1.0) ** 0.7
    x = lerp(DROP[0], 100 + lane * 9, a) + math.sin(age * 0.05 + lane) * 4 * (1 - a)
    y = lerp(DROP[1], HORIZON + 2, a) + math.sin(age * 1.7 + lane) * (1.2 * (1 - a))
    return x, y, 1 - a


def river_lamp(g: Gfx, x: float, y: float, size: float, t: float, lit: float = 1.0, seed: int = 0):
    """莲花灯：近处是带瓣的大灯，远了变成小灯、光点；倒影碎光"""
    fl = pix.anim(FLAME, t + seed * 0.37, 8)
    if size > 0.55:
        pix.blit(g, LOTUS, x - 5, y - 4)
        if lit > 0.5:
            pix.blit(g, fl, x - 1, y - 8, outline=False)
        elif lit > 0:
            g.px(x, y - 5)
        for j in range(3):   # 倒影
            if (int(t * 6) + j + seed) % 3:
                w = 2 - j // 2
                g.d.line((x - w + (j % 2), y + 3 + j * 2, x + w, y + 3 + j * 2), fill=1)
    elif size > 0.25:
        pix.blit(g, LOTUS_MID, x - 2, y - 2)
        if lit > 0.5:
            g.px(x, y - 3), g.px(x, y - 4)
            if int(t * 5 + seed) % 2:
                g.px(x - 1, y - 3)
        if (int(t * 6) + seed) % 2:
            g.d.line((x - 1, y + 3, x + 1, y + 3), fill=1)
    else:
        g.px(x, y)
        if lit > 0.5:
            g.px(x, y - 1)
            if (int(t * 4) + seed) % 3:
                g.px(x, y + 2)


def basket(g: Gfx, n: int):
    """灯篮（篮里露出几盏灯的瓣尖）"""
    x0 = BASKET_X - 6
    g.d.arc((x0 + 1, BANK - 14, x0 + 11, BANK - 2), 180, 360, fill=1)
    g.d.arc((x0 + 2, BANK - 13, x0 + 10, BANK - 3), 180, 360, fill=1)
    for i in range(min(n, 3)):
        g.px(x0 + 3 + i * 3, BANK - 8)
        g.px(x0 + 2 + i * 3, BANK - 7), g.px(x0 + 4 + i * 3, BANK - 7)
    g.d.polygon([(x0, BANK - 6), (x0 + 12, BANK - 6), (x0 + 10, BANK - 1), (x0 + 2, BANK - 1)], fill=1)
    for x in range(x0 + 2, x0 + 11, 2):
        g.px(x, BANK - 4, 0)


def mx_river(g: Gfx, t: float, lit: bool = True):
    mx_art(g, """
........
........
........
.#.##.#.
.######.
..####..
""")
    if lit:
        f = int(t * 8) % 3
        g.mx[1, 3:5] = True
        g.mx[0, (3, 4, 4)[f]] = True
        g.mx[2, 3:5] = True
    for x in range(8):
        g.mx[7, x] = (x + int(t * 3)) % 4 < 2


@register
class RiverLanterns(Ritual):
    id = "r1.river"
    name = "放河灯"
    desc = "中元夜满月下，小道士在江边跪下一盏盏放莲花灯，灯顺水漂向天边越来越小；鱼跃、萤火；一轮后纸扎法船驶过天边"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def setup(self):
        self.clock = Clock()
        self.sparks = pix.Sparks(self.seed)

    def placed(self, e: float):
        """江上漂着的灯：[(放下后秒数, 序号)]（e 的函数；序号决定航道）"""
        out = []
        n = int((e - 2.6) // EVERY) if e >= 2.6 else -1
        for i in range(max(0, n - 5), n + 1):
            age = e - (i * EVERY + 2.6)
            if 0 <= age < LIFE:
                out.append((age, i))
        return out

    def counter(self, g: Gfx, e: float, label: str | None = None):
        n = int((e % self.CYCLE) // EVERY) + 1
        badge(g, 4, 3, label or f"第{cn_num(n)}盏")

    def lamps(self, g: Gfx, e: float, t: float, lit: float = 1.0):
        for age, i in sorted(self.placed(e), key=lambda a: -a[0]):
            x, y, s = lamp_pos(age, i % 3)
            river_lamp(g, x, y, s, t, lit, seed=i)

    def ambient(self, g: Gfx, e: float, t: float, dt: float):
        k = (e + self.seed * 11) % 41      # 鱼跃
        if k < 1.4:
            q = k / 1.1
            fx = 80 + (self.seed % 3) * 8
            if q < 1:
                x, y = fx + q * 14, 44 - math.sin(q * math.pi) * 10
                spr = FISH[0] if q < 0.5 else FISH[0].flipv()
                pix.blit(g, spr, x - 4, y - 2)
            if hit(k, 0.0, dt) or hit(k, 1.1, dt):
                self.sparks.burst(fx + (14 if k > 0.5 else 0), 44, 8, 18, up=14, life=0.5, gravity=70)
            if k > 1.1:
                ring_dots(g, fx + 14, 45, 2 + (k - 1.1) * 14, 2, sy=0.3)
        for j in range(2):                  # 萤火虫
            ph = e * 0.3 + j * 3.1
            x = 20 + j * 22 + math.sin(ph) * 10
            y = 40 + math.cos(ph * 1.3) * 4
            if int(e * 2 + j) % 3:
                g.px(x, y)

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        """夜色渐显 → 小道士走到江边 → 对江拱手、作揖"""
        dt = self.clock(t)
        scene_bg(g, t)
        g.fade(span(t, 0.0, 1.6))
        basket(g, 3)
        if t < 3.4:
            x = lerp(-12, DX, ease_out(span(t, 1.0, 3.4)))
            daoshi(g, x, BANK, "walk", t)
        else:
            daoshi(g, DX, BANK, "gongshou" if t < 4.4 else ("bow" if t < 5.2 else "idle"), t)
        for j in range(3):     # 江面一圈圈亮开的涟漪
            r = (t - 1.5 - j * 0.5) * 14
            if 0 < r < 40:
                ring_dots(g, 84, 44, r, 3, sy=0.25)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 3.4:
            self.counter(g, 0.0)
        mx_river(g, t)

    def place(self, g: Gfx, t: float, u: float, dt: float):
        """u ∈ [0, 4]：转身取灯 → 跪下 → 送灯入水（涟漪）→ 起身作揖"""
        if u < 1.0:
            h = pose_arm(g, DX, BANK, t, 60 if u > 0.3 else 30, flip=True)
            if u > 0.6:
                river_lamp(g, h["hand"][0], h["hand"][1] + 3, 1.0, t)
        elif u < 2.6:
            q = ease_in_out(span(u, 1.6, 2.4))
            h = pose_arm(g, DX, BANK, t, 30 if q < 0.5 else 60, legs="kneel", shoulder=(0, -14))
            if u < 2.4:
                hx, hy = h["hand"]
                lx, ly = lerp(hx + 1, DROP[0], q), lerp(hy + 3, DROP[1], q)
                river_lamp(g, lx, ly, 1.0, t)
        elif u < 3.4:
            pose_arm(g, DX, BANK, t, 30, legs="kneel", shoulder=(0, -14), face="happy")
        else:
            daoshi(g, DX, BANK, "gongshou" if u < 3.9 else "bow", t)
        if u >= 2.4:   # 涟漪
            a = u - 2.4
            for j in range(3):
                r = 2 + (a - j * 0.25) * 9
                if 0 < r < 16:
                    ring_dots(g, DROP[0], DROP[1] + 2, r, 2, sy=0.3)
        if hit(u, 2.4, dt):
            self.sparks.burst(DROP[0], DROP[1] + 1, 6, 12, up=8, life=0.4, gravity=50)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        k = e % self.CYCLE
        scene_bg(g, t)
        if e >= self.CYCLE and k < RENEW:     # 续：法船驶过天边
            q = span(k, 0.0, RENEW)
            bx = lerp(-24, 132, q)
            by = HORIZON - 8 + math.sin(t * 1.5) * 0.5
            pix.blit(g, BOAT, bx - 10, by - 1)
            for wx in (bx - 5, bx - 1, bx + 3):     # 窗里的灯
                if int(t * 3 + wx) % 3:
                    g.px(wx, by + 3)
            pix.dotted(g, bx - 12, HORIZON + 1, bx + 10, HORIZON + 1, 2, int(t * 6))
        basket(g, 3)
        self.lamps(g, e, t)
        self.ambient(g, e, t, dt)
        u = k % EVERY
        if u < 4.0:
            self.place(g, t, u, dt)
        elif e >= self.CYCLE and k < RENEW:
            daoshi(g, DX, BANK, "gongshou" if k < 6 else "bow", t)
        else:
            c = (u + self.seed * 3) % 30
            if 20 <= c < 22.4:
                daoshi(g, DX, BANK, "gongshou" if c < 21.2 else "bow", t)
            else:
                daoshi(g, DX, BANK, "idle", t, face="happy" if 4.0 <= u < 6.0 else "normal")
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e)
        mx_river(g, t)

    # ------------------------------------------------------------ 中断 / 恢复 / 圆满

    def mist(self, g: Gfx, t: float, amt: float):
        """江雾：几条稀疏的点状雾带从两岸往江心漫，只在水面上"""
        if amt <= 0:
            return
        for j in range(4):
            y = HORIZON + 2 + j * 7
            w = 50 * amt + j * 4
            ph = int(t * 6) + j * 3
            pix.dotted(g, 40, y, 40 + w, y, 3, ph)
            pix.dotted(g, 127 - w, y + 3, 127, y + 3, 3, ph + 1)
            if amt > 0.5:
                pix.dotted(g, 44, y + 1, 44 + w * 0.6, y + 1, 4, ph)

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        scene_bg(g, t)
        basket(g, 3)
        lit = 1 - span(t, 0.6, 1.4)
        self.lamps(g, e, t, lit=1.0 if lit > 0.5 else 0.3)
        daoshi(g, DX, BANK, "gongshou" if t > 0.3 else "idle", t)
        self.mist(g, t, ease_out(span(t, 0.0, 1.6)))
        self.counter(g, e, "暂歇" if t > 0.8 else None)
        mx_river(g, t, lit=lit > 0.5)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        scene_bg(g, t)
        basket(g, 3)
        relit = t > 1.0
        self.lamps(g, e, t, lit=1.0 if relit else 0.3)
        h = daoshi(g, DX, BANK, "point" if t < 1.3 else "idle", t)
        self.mist(g, t, 1 - ease_in(span(t, 0.3, 1.4)))
        if hit(t, 1.0, dt):
            for age, i in self.placed(e):
                x, y, s = lamp_pos(age, i % 3)
                self.sparks.burst(x, y - 3, 4, 10, up=6, life=0.4, gravity=10)
            pix.flash(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.counter(g, e, "暂歇" if t < 0.6 else None)
        mx_river(g, t, lit=relit)

    def complete(self, g: Gfx, t: float, e: float):
        dt = self.clock(t)
        scene_bg(g, t)
        basket(g, 3)
        rise = span(t, 0.6, 3.0)
        self.lamps(g, e, t, lit=1.0 if rise <= 0 else 0.3)
        for age, i in self.placed(e):    # 灯火离开灯，升空化作星点
            x, y, s = lamp_pos(age, i % 3)
            q = span(t, 0.6 + i % 3 * 0.15, 3.0 + i % 3 * 0.15)
            if 0 < q:
                yy = lerp(y - 5, 4 + (i * 7) % 16, ease_in_out(q))
                xx = x + math.sin(q * 6 + i) * 3 * (1 - q)
                if q < 1:
                    g.d.ellipse((xx - 1, yy - 1, xx + 1, yy + 1), fill=1)
                    g.px(xx, yy + 3)
                else:
                    star(g, xx, yy, 1 if int(t * 4 + i) % 2 else 0)
        if t > 2.4:   # 满月放光
            for j in range(12):
                a = j / 12 * 2 * math.pi + t * 0.3
                pix.dotted(g, MOON[0] + math.cos(a) * 10, MOON[1] + math.sin(a) * 10,
                           MOON[0] + math.cos(a) * 14, MOON[1] + math.sin(a) * 14, 2)
        daoshi(g, DX, BANK, "kneel" if 1.0 < t < 4.6 else "idle", t, face="happy" if t > 4.6 else "normal")
        if hit(t, 3.0, dt):
            pix.flash(g)
            self.sparks.burst(MOON[0], MOON[1], 24, 40, life=1.2, gravity=10)
        self.sparks.step(dt)
        self.sparks.draw(g)
        if t > 3.2:
            title(g, 46, 6, "中元普度", t, 3.2)
        mx_river(g, t)
        mx_burst(g, t, 3.0)
