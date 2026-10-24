"""祈雨：小道士登坛摇令旗，云聚龙行，甘霖落下，旱田返青。

依据：雷法的职能之一是祈雨禳旱（神霄派《神霄紫书》目录有“三十六雷部”“祈雨止雨法”）；民间祈雨以龙王为主神，
龙行云中、云行雨施；“风调雨顺”为醮坛常见祝语。

画面：左边一座小法坛，小道士站在坛上举令旗；右边一片旱田，烈日当空。
入场：烈日弹出、光芒转动，田里裂纹一道道裂开，热气蒸腾；小道士登坛举旗，“祈雨”。
持续：一轮一场雨（10 分钟）：头一分钟小道士连连摇旗，云从两边聚拢遮住太阳；龙在云间穿行（约 40 秒一趟，
      小道士剑指相迎）；雨由疏到密，落地溅起水花；裂纹弥合、积起水洼（雨点打出涟漪），禾苗随 e 长高、长叶、抽穗低垂。
      云里不时闷雷一闪。
      续：最后 40 秒雨收，龙升入云，云开日出，挂一道虹，禾穗随风摆，小道士作揖；
      下一场开头田土复干、禾苗缩回、裂纹重现，“第几场”。
中断：雨收住，龙隐入云中，“雨歇”。  恢复：龙从云里探出头，雨又下起来。
圆满：龙腾空而去，云开日出，彩虹横天，禾苗长满，“风调雨顺”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part, daoshi, figure
from ..engine.cn import cn_num
from ..engine.gfx import Gfx
from ..engine.scene import Ritual, register
from .r5_util import Clock, arm, bolt, cached, cloud_sprite, label, pop_box, ring

FLOOR = 52                     # 田面
ALTAR = (3, 37, 49)            # 法坛 x0, x1, 坛面 y
DX = 20
SUN = (104, 12)
PLANTS = [50 + i * 13 for i in range(6)]


def _cracks():
    """龟裂：从几个裂点向外分叉的折线（确定性）；每段带“出现顺序”"""
    import random
    rng = random.Random(5)
    segs = []
    for cx in (52, 70, 88, 106, 122):
        cy = 57 + rng.randrange(-2, 3)
        for a in range(4):
            ang = a * math.pi / 2 + rng.random() * 0.8
            x, y = cx, cy
            for j in range(4):
                nx = x + math.cos(ang) * (3 + rng.random() * 2)
                ny = y + math.sin(ang) * (2 + rng.random() * 1.5)
                ny = min(max(ny, FLOOR + 2), 63)
                segs.append(((x, y, nx, ny), j / 4))
                x, y = nx, ny
                ang += (rng.random() - 0.5) * 1.4
    return segs


CRACKS = _cracks()


# ---------------------------------------------------------------- 道具

DRAGON_HEAD = """
            #  #
             # #
       ####   ##
    ##########.#
  ######..#####.#
 ##############.##
#..#############
#.........####
 #.#.#..######
  ######### #
"""


def _dragon_head():
    """龙头 16×12（朝左）：上翘的长吻、张口獠牙、圆眼、鹿角、颈后鬃毛"""
    from ..engine.gfx import Sprite
    return Sprite(DRAGON_HEAD)


def head_spr():
    return cached(("r5qiyu", "head"), _dragon_head)


def _flag(frame: int):
    """令旗 9×7：三角旗面，镶边，中间一点；frame 飘动"""
    p = Part(9, 7)
    if frame == 0:
        p.shape("polygon", [(0, 0), (8, 1), (5, 3), (8, 5), (0, 6)], fill=1)
    else:
        p.shape("polygon", [(0, 0), (7, 0), (6, 3), (8, 6), (0, 6)], fill=1)
    p.d.line((1, 1, 1, 5), fill=0)
    p.px(3, 3, 0)
    return p.sprite()


def flag_spr(i):
    return cached(("r5qiyu", "flag", i), lambda: _flag(i))


# ---------------------------------------------------------------- 景

def sun(g: Gfx, t: float, k: float = 1.0):
    """烈日：实心圆 + 一圈暗环 + 转动的光芒（长短相间）"""
    if k <= 0:
        return
    x, y = SUN
    r = 6 * ease_out_back(k)
    g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
    if r > 3:
        g.d.ellipse((x - r + 2, y - r + 2, x + r - 2, y + r - 2), outline=0)
    for i in range(12):
        a = t * 0.4 + i * math.pi / 6
        r0, r1 = r + 3, r + (7 if i % 2 == 0 else 5)
        g.d.line((x + math.cos(a) * r0, y + math.sin(a) * r0, x + math.cos(a) * r1, y + math.sin(a) * r1), fill=1)


def altar(g: Gfx):
    """法坛：两层石台，台面一道暗线，台身回纹点"""
    x0, x1, y = ALTAR
    g.d.rectangle((x0 - 2, y, x1 + 2, y + 1), fill=1)
    g.d.line((x0 - 1, y + 1, x1 + 1, y + 1), fill=0)
    g.d.rectangle((x0, y + 2, x1, 63), fill=0, outline=1)
    for x in range(x0 + 3, x1 - 2, 4):
        g.px(x, y + 4), g.px(x + 1, y + 5)
    pix.checker(g, (x0 + 1, 58, x1, 63), 0.25)


def field(g: Gfx, dry: float, wet: float, t: float, rain: float):
    """田：田面一道线，土层网点（干时亮、湿时暗）；dry = 龟裂显露程度，wet = 水洼大小"""
    g.d.line((ALTAR[1] + 3, FLOOR, 127, FLOOR), fill=1)
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.5 if dry > 0.3 else 0.25)
    for (x0, y0, x1, y1), order in CRACKS:
        if dry > order:
            g.d.line((x0, y0, x1, y1), fill=0, width=2 if order < 0.3 else 1)
    if wet > 0:              # 水洼：白水面 + 下沿暗线；雨点打出涟漪
        for i, x in enumerate((60, 86, 112)):
            w = wet * (5 + i)
            g.d.rectangle((x - w, FLOOR + 1, x + w, FLOOR + 2), fill=1)
            g.d.line((x - w + 1, FLOOR + 3, x + w - 1, FLOOR + 3), fill=0)
            g.px(x - w + 2, FLOOR + 1, 0)
            if rain > 0.2:
                q = (t * 1.7 + i * 0.37) % 1
                rx = x + (rand(int(t * 1.7 + i * 0.37), i) - 0.5) * w
                if q < 0.6:
                    g.d.ellipse((rx - 1 - q * 4, FLOOR - 1, rx + 1 + q * 4, FLOOR + 1), outline=1)


def plant(g: Gfx, x: int, h: float, t: float, i: int):
    """一株禾：h 0..1。小芽 → 主秆两叶 → 分蘖两短秆 → 抽穗：穗从秆顶拱起、向右垂下，谷粒左右交错"""
    if h <= 0.02:
        return
    sway = math.sin(t * 1.3 + i * 0.9) * (0.4 + h * 0.8)
    H = 2 + int(round(13 * h))
    tx, ty = x + sway, FLOOR - 1 - H
    g.d.line((x, FLOOR - 1, tx, ty), fill=1)
    if h > 0.4:                                   # 分蘖：两根短秆
        for d in (-1, 1):
            hh = H * 0.55
            g.d.line((x, FLOOR - 1, x + d * 2 + sway * 0.5, FLOOR - 1 - hh), fill=1)
    for j, (fy, d) in enumerate(((0.3, -1), (0.5, 1), (0.72, -1))):   # 叶：向外拱起再垂下
        if h < 0.12 + j * 0.2:
            continue
        mx, my = x + sway * fy, FLOOR - 1 - H * fy
        L = 2 + int(2 * h)
        g.d.line((mx, my, mx + d * L, my - 2, mx + d * (L + 1), my - 1), fill=1)
        g.px(mx + d * (L + 2), my)
    if h > 0.7:                                   # 穗：秆顶向右拱起后垂下，谷粒成串（左右交错、两像素宽）
        k = span(h, 0.7, 1.0)
        g.px(tx, ty - 1), g.px(tx + 1, ty - 2), g.px(tx + 2, ty - 2), g.px(tx + 3, ty - 1)
        for j in range(int(round(1 + 4 * k))):
            gx, gy = tx + 4, ty + j
            g.px(gx, gy)
            g.px(gx + (1 if j % 2 == 0 else -1), gy)
        g.px(tx + 2, ty - 1)


def rain(g: Gfx, t: float, amt: float, seed: int, x0: int = 0):
    """雨丝（斜向两像素）+ 落地水花；确定性，按 t 算"""
    n = int(60 * amt)
    for i in range(n):
        x = x0 + rand(i, seed) * (128 - x0)
        sp = 70 + rand(i, seed + 1) * 30
        ph = rand(i, seed + 2) * 80
        y = (t * sp + ph) % 72 - 8
        xx = x - (y + 8) * 0.25
        if y < FLOOR - 2:
            if y > 16:
                g.d.line((xx, y, xx - 1, y + 2), fill=1)
        elif y < FLOOR + 4:     # 水花：一个小冠
            g.px(xx - 1, FLOOR - 1), g.px(xx + 1, FLOOR - 1), g.px(xx - 2, FLOOR - 2), g.px(xx + 2, FLOOR - 2)


def heat(g: Gfx, t: float, k: float):
    """热气：田上方几道扭动的虚线"""
    if k <= 0:
        return
    for i, x in enumerate((58, 78, 98, 118)):
        for j in range(int(10 * k)):
            y = FLOOR - 3 - j * 2 - (t * 6 % 2)
            g.px(x + math.sin(t * 3 + j * 0.8 + i) * 1.5, y)


CLOUD_SET = [(-4, 0, 40, 13, 31), (30, -2, 50, 17, 32), (76, -1, 56, 17, 33), (58, 6, 30, 12, 34)]


def clouds(g: Gfx, t: float, cover: float, layer: int):
    """cover 0..1：云从两边聚拢；layer 0 = 后排，1 = 前排（压住龙身）"""
    for i, (x, y, w, h, seed) in enumerate(CLOUD_SET):
        if (i == 3) != (layer == 1):
            continue
        side = -1 if x + w / 2 < 64 else 1
        off = side * (1 - ease_out(cover)) * 90
        dx = math.sin(t * 0.25 + i * 1.7) * 2
        pix.blit(g, cloud_sprite(w, h, seed, dark=cover > 0.7), x + off + dx, y)


def dragon(g: Gfx, hx: float, hy: float, t: float, length: int = 50, amp: float = 6.0, up: float = 0.0):
    """龙：头在 (hx, hy)（精灵左上角）朝左，身子向右后方 S 形起伏；白身黑鳞（交错的小弧）、背鳍、两对爪、尾鬣。
    up：身子向后上方扬起（升天）"""
    pts = []
    for s in range(length):
        x = hx + 15 + s
        y = hy + 6 + amp * math.sin(s * 0.13 - t * 2.6) * min(1, s / 10) - up * s * 0.7
        pts.append((x, y))

    def rad(s):
        return 3.2 * (1 - (s / length) ** 1.5 * 0.8)
    for s in range(length - 1, -1, -1):
        x, y = pts[s]
        r = rad(s) + 1
        g.d.ellipse((x - r, y - r, x + r, y + r), fill=0)
    for s in range(length - 1, -1, -1):
        x, y = pts[s]
        r = rad(s)
        g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
    for s in range(3, length - 8, 3):         # 鳞：交错的小弧
        x, y = pts[s]
        o = 1 if (s // 3) % 2 else -1
        g.px(x, y + o, 0), g.px(x + 1, y + o + 1, 0), g.px(x - 1, y + o + 1, 0)
    for s in range(2, length - 6, 3):         # 背鳍（锯齿）
        x, y = pts[s]
        r = rad(s)
        g.px(x, y - r - 1), g.px(x + 1, y - r - 2)
    for s in (12, 34):                        # 爪：腿 + 三趾
        if s >= length - 4:
            continue
        x, y = pts[s]
        g.d.line((x, y + 2, x - 2, y + 6), fill=1)
        g.d.line((x - 4, y + 6, x, y + 6), fill=1)
        g.px(x - 4, y + 7), g.px(x - 2, y + 7)
    x, y = pts[-1]                            # 尾鬣
    g.d.line((x, y, x + 3, y - 3), fill=1)
    g.d.line((x, y, x + 4, y), fill=1)
    g.d.line((x, y, x + 3, y + 2), fill=1)
    pix.blit(g, head_spr(), hx, hy)
    w = math.sin(t * 4) * 1.5                 # 龙须
    g.d.line((hx, hy + 6, hx - 4, hy + 8 + w, hx - 8, hy + 7 + w * 1.5), fill=1)
    g.d.line((hx + 1, hy + 9, hx - 3, hy + 12 + w), fill=1)


@register
class QiYu(Clock, Ritual):
    id = "r5.qiyu"
    name = "祈雨"
    desc = "小道士登坛摇令旗，云从两边聚拢遮住烈日，龙在云间穿行，雨落旱田，禾苗随计时长高抽穗；一场雨后云开挂虹"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    def setup(self):
        self.sk = self.rng.randrange(1000)

    # ------------------------------------------------------------ 状态（全按 e）

    def state(self, e: float):
        c, k = int(e // self.CYCLE), e % self.CYCLE
        cover = span(k, 4, 60) * (1 - span(k, 575, 592))
        rain_amt = span(k, 30, 120) * (1 - span(k, 556, 572))
        grow = span(k, 60, 556)
        if c >= 1 and k < 4:         # 新一场：田土复干，禾苗缩回
            grow = 1 - ease_in_out(span(k, 0.0, 3.0))
        dry = 1 - span(k, 60, 200)
        if c >= 1 and k < 4:
            dry = span(k, 1.0, 3.5)
        wet = span(k, 120, 240) * (1 - span(k, 572, 600))
        bow = span(k, 572, 600)
        return dict(c=c, k=k, cover=cover, rain=rain_amt, grow=grow, dry=dry, wet=wet, rainbow=span(k, 582, 590))

    # ------------------------------------------------------------ 画

    def bg(self, g: Gfx, s, t: float):
        sun(g, t, 1 - span(s["cover"], 0.6, 0.95))
        if s["rainbow"] > 0:
            self.rainbow(g, s["rainbow"])

    def rainbow(self, g: Gfx, k: float):
        """虹：三道同心弧（实、虚、实），从左往右画出"""
        cx, cy = 76, 64
        end = 180 + 180 * ease_out(k)
        for j, r in enumerate((46, 43, 40)):
            if j == 1:
                for a in range(180, int(end), 4):
                    g.px(cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r)
            else:
                g.d.arc((cx - r, cy - r, cx + r, cy + r), 180, end, fill=1)

    def dragon_pass(self, g: Gfx, e: float, t: float, s):
        """龙在云间：约 40 秒一趟，从右往左游过（8 秒）"""
        if s["cover"] < 0.8:
            return None
        k = s["k"]
        if k > 565:
            q = span(k, 565, 580)        # 升入云中
            if q < 1:
                dragon(g, lerp(50, 70, q), lerp(18, -30, ease_in(q)), t, up=q)
            return None
        ph = (k - 40) % 40
        if 0 <= ph < 8:
            q = ph / 8
            hx = lerp(130, 34, ease_in_out(min(q / 0.8, 1)))
            hy = 18 + math.sin(q * math.pi * 2) * 2 - ease_in(span(q, 0.65, 1.0)) * 40
            dragon(g, hx, hy, t, up=span(q, 0.65, 1.0) * 0.6)
            return hx
        return None

    def actor(self, g: Gfx, e: float, t: float, s, dragon_x):
        """小道士：聚云时连连摇旗；龙来时剑指相迎；平时持旗，隔一阵摇两下、作个揖"""
        k = s["k"]
        y = ALTAR[2]
        if k > 586:
            pose = "bow" if (k - 586) % 5 < 1.5 else "gongshou"
            daoshi(g, DX, y, pose, t, face="happy")
            return
        if dragon_x is not None and 30 < dragon_x < 128:
            h = figure(g, DX, y, t, arm=arm("sky"), arm_at=(3, -25), face="wow" if dragon_x > 80 else "happy")
            return
        wave = k < 60 or (e % 20) < 2.2
        if (e % 20) > 15 and (e % 20) < 17 and k >= 60:
            daoshi(g, DX, y, "gongshou", t)
            return
        up = wave and (t * 3) % 1 < 0.5
        if up:
            h = daoshi(g, DX, y, "raise", t)
        else:
            h = figure(g, DX, y, t, arm=arm("sky"), arm_at=(3, -25)) if wave else daoshi(g, DX, y, "raise", t)
        hx, hy = h["hand"]
        g.d.line((hx, hy - 9, hx, hy + 3), fill=1)    # 旗杆
        g.px(hx, hy - 10)
        pix.blit(g, flag_spr(int(t * (8 if wave else 3)) % 2), hx + 1, hy - 9)

    def mx(self, g: Gfx, s, t: float):
        if s["cover"] < 0.5 or s["rainbow"] > 0.5:
            g.mx_rows([0x24, 0x00, 0x18, 0xBD, 0x3C, 0x18, 0x00, 0x24] if (t * 2) % 1 < 0.5 else
                      [0x00, 0x42, 0x18, 0x3C, 0x3C, 0x18, 0x42, 0x00])
            return
        g.mx[0, 1:7] = True
        g.mx[1, :] = True
        for i in range(int(8 * s["rain"])):
            x = int(rand(i, 3) * 8)
            y = 2 + int((t * 6 + rand(i, 4) * 5) % 4)
            g.mx_set(x, y)
        h = int(round(s["grow"] * 3))
        for x in (1, 3, 5, 7):
            for r in range(h):
                g.mx_set(x, 7 - r)
        g.mx[7, :] = True

    def frame(self, g: Gfx, t: float, e: float, s, show_dragon=True, rain_mul=1.0):
        self.bg(g, s, t)
        clouds(g, t, s["cover"], 0)
        dx = self.dragon_pass(g, e, t, s) if show_dragon else None
        clouds(g, t, s["cover"], 1)
        if s["cover"] > 0.9 and (e % 31) < 0.15:     # 云里闷雷
            bolt(g, 70, 8, 84, 13, int(e // 31), thick=False, jag=2, branch=False)
        heat(g, t, 1 - span(s["cover"], 0.2, 0.6) if s["dry"] > 0.5 else 0)
        altar(g)
        field(g, s["dry"], s["wet"], t, s["rain"])
        for i, x in enumerate(PLANTS):
            plant(g, x, s["grow"] * (0.85 + 0.15 * rand(i, 9)), t, i)
        rain(g, t, s["rain"] * rain_mul, self.seed, 40)
        return dx

    # ------------------------------------------------------------ 阶段

    def enter(self, g: Gfx, t: float):
        self._dt(t)
        sun(g, t, span(t, 0.0, 0.8))
        altar(g)
        field(g, span(t, 0.8, 2.6), 0, t, 0)
        heat(g, t, span(t, 1.8, 3.0))
        if t < 2.2:
            figure(g, lerp(-12, DX, ease_out(span(t, 0, 1.6))), lerp(FLOOR, ALTAR[2], span(t, 1.4, 1.8)), t,
                   legs="walk" if t < 1.6 else "stand")
        else:
            s = self.state(0.0)
            self.actor(g, 0.0 + (t - 5.5), t, s, None)
        if 1.0 <= t < 2.6:   # 裂开时一点震动
            if int(t * 8) % 3 == 0:
                pix.shake(g, t, 0.6)
        if t > 2.6:
            label(g, 6, 4, "祈雨")
        self.mx(g, self.state(0.0), t)

    def hold(self, g: Gfx, t: float, e: float):
        self._dt(t)
        s = self.state(e)
        dx = self.frame(g, t, e, s)
        self.actor(g, e, t, s, dx)
        if s["c"] >= 1 and s["k"] < 5:
            label(g, 6, 4, f"第{cn_num(s['c'] + 1)}场" if s["c"] < 99 else f"{s['c'] + 1}场")
        elif s["k"] < 3 and s["c"] == 0:
            label(g, 6, 4, "祈雨")
        self.mx(g, s, t)

    def interrupt(self, g: Gfx, t: float, e: float):
        self._dt(t)
        s = self.state(e)
        self.frame(g, t, e, s, show_dragon=False, rain_mul=1 - span(t, 0, 0.8))
        k = s["k"]
        ph = (k - 40) % 40
        if s["cover"] > 0.8 and 40 <= k <= 565 and ph < 8 and t < 0.9:   # 正在穿行的龙一甩尾，隐入云中
            q = ph / 8
            hx = lerp(130, 34, ease_in_out(min(q / 0.8, 1)))
            hy = 18 + math.sin(q * math.pi * 2) * 2 - ease_in(span(q, 0.65, 1.0)) * 40
            dragon(g, hx, hy - ease_in(span(t, 0, 0.9)) * 40, t, up=span(t, 0, 0.9))
            clouds(g, t, s["cover"], 1)
        daoshi(g, DX, ALTAR[2], "gongshou", t)
        if t > 0.4:
            label(g, 64, 26, "雨歇", align="center")
        self.mx(g, dict(s, rain=s["rain"] * (1 - span(t, 0, 0.8))), t)

    def resume(self, g: Gfx, t: float, e: float):
        self._dt(t)
        s = self.state(e)
        self.frame(g, t, e, s, show_dragon=False, rain_mul=span(t, 0.8, 1.6))
        if s["cover"] > 0.8 and t < 1.6:     # 龙从云里探出头
            q = ease_out_back(span(t, 0.1, 0.8)) - ease_in(span(t, 1.2, 1.6))
            dragon(g, 60, lerp(-14, 14, q), t, length=30, up=-0.2)
            clouds(g, t, s["cover"], 1)
        h = daoshi(g, DX, ALTAR[2], "raise", t)
        hx, hy = h["hand"]
        g.d.line((hx, hy - 9, hx, hy + 3), fill=1)
        pix.blit(g, flag_spr(int(t * 8) % 2), hx + 1, hy - 9)
        self.mx(g, s, t)

    def complete(self, g: Gfx, t: float, e: float):
        self._dt(t)
        s = self.state(e)
        cover = s["cover"] * (1 - ease_in_out(span(t, 1.6, 3.2)))
        rain_amt = s["rain"] * (1 - span(t, 0.0, 1.6))
        grow = lerp(s["grow"], 1.0, ease_in_out(span(t, 1.0, 3.5)))
        wet = max(s["wet"], span(t, 0, 1.0) * 0.6) * (1 - span(t, 3.0, 5.0) * 0.5)
        sun(g, t, span(t, 2.8, 3.6))
        if t > 3.2:
            self.rainbow(g, span(t, 3.2, 4.4))
        clouds(g, t, cover, 0)
        if t < 2.2:                         # 龙腾空而去
            q = span(t, 0.2, 2.2)
            dragon(g, lerp(80, 40, q), lerp(14, -40, ease_in(q)), t, up=q)
        clouds(g, t, cover, 1)
        altar(g)
        field(g, 0, wet, t, rain_amt)
        for i, x in enumerate(PLANTS):
            plant(g, x, grow * (0.85 + 0.15 * rand(i, 9)), t, i)
        rain(g, t, rain_amt, self.seed, 40)
        pose = "raise" if t < 2.2 else ("bow" if 3.4 < t < 4.4 else "gongshou")
        h = daoshi(g, DX, ALTAR[2], pose, t, face="happy" if t > 3 else "wow")
        if pose == "raise":
            hx, hy = h["hand"]
            g.d.line((hx, hy - 9, hx, hy + 3), fill=1)
            pix.blit(g, flag_spr(int(t * 8) % 2), hx + 1, hy - 9)
        if 2.8 <= t < 2.87:
            pix.flash(g)
        if t > 3.8:
            y = pop_box(g, 52, 4, "风调雨顺", t, 3.8)
            g.text(52, y, "风调雨顺", align="center")
        self.mx(g, dict(s, cover=cover, rain=rain_amt, grow=grow, rainbow=span(t, 3.2, 4.4)), t)
