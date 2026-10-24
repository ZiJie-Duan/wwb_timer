"""晶圆炼丹（像素风）：太上老君的八卦炉改成了光刻机，小道士拿蒲扇扇炉火，炉肚圆窗里的晶圆一颗颗芯片被曝光。

画面：右边一座八角八卦炉（三足、炉身两侧刻四卦、正中一面铆钉圆窗），炉顶是带散热片的紫外灯罩，
灯嘴伸进圆窗上沿，一道虚线光束打在当前那颗芯片上；炉底三团像素火。小道士站在左边，蒲扇一扇，炉火一窜，
风线吹过去。
入场：炉身一卦一卦亮起，灯罩落下“咔”一声，小道士走来扇火点着炉子，晶圆从左边滑进圆窗，光束对准第一颗。
持续：一轮 10 分钟按蛇形顺序曝光 37 颗芯片（每颗曝完一闪火星），右上读数“07/37”，左上“第几转”；
      小道士一直扇火；隔一阵：炉子打个嗝（灯罩跳两下、冒一大团烟、屏幕一震，小道士吓一跳）、
      或者热得拿扇子扇自己（汗珠飞出）、或者凑过去指着圆窗看。
      一轮满：一道光波扫过整片，晶圆从圆窗滑出落到小道士手里，他收起来，新晶圆滑进去，“第几转”加一。
中断：炉火熄成余烬，小道士停扇，圆窗的铁盖从上面砸下来弹两下，“封炉”。
恢复：铁盖升起，小道士猛扇，炉火“轰”地重燃。
圆满：剩下的芯片一口气曝完，整片放光、缩成一点，一颗印着“丹”字的 QFP 芯片蹦出来飞到小道士手上，
      他高举过头，闪白，“九转丹成”。
依据：外丹“九转还丹”（《抱朴子·金丹》：“九转之丹，服之三日得仙”），太上老君八卦炉（《西游记》第七回）。
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx, _text_img
from ..engine.scene import register
from ..engine.symbols import TRIGRAMS
from .r6_common import R6, badge, banner, dao, glow_rays, nth, pixsmoke, tiny

FLOOR = 58
FX = 88                  # 炉中心
B_TOP, B_BOT = 12, 45    # 炉身上下
WX, WY = FX, 28          # 圆窗中心
WR = 13                  # 窗内半径
DX = 42                  # 小道士
NOZZLE = (FX, B_TOP + 4)        # 灯嘴
RENEW = 6.0
LOOP = 30.0
N_DIE = 37
PITCH = 3


def _dies():
    """37 颗芯片：7×7 网格去掉四角各 3 格，蛇形顺序。返回 [(dx, dy)]（相对窗心，芯片 2×2 的左上角）"""
    out = []
    for r in range(7):
        row = []
        for c in range(7):
            a, b = abs(c - 3), abs(r - 3)
            if (a, b) in ((3, 3), (3, 2), (2, 3)):
                continue
            row.append(((c - 3) * PITCH - 1, (r - 3) * PITCH - 1))
        out += row if r % 2 == 0 else row[::-1]
    return out


DIES = _dies()
assert len(DIES) == N_DIE


# ---------------------------------------------------------------- 道具

def _furnace():
    """八卦炉身 52×34：八角外壳（白边）、深色炉膛面板带铁砂点、两侧四卦、上下两道带铆钉的箍、圆窗厚圈"""
    w, h = 52, B_BOT - B_TOP + 1
    p = Part(w, h)
    c = 6
    oct_ = [(c, 0), (w - 1 - c, 0), (w - 1, c), (w - 1, h - 1 - c), (w - 1 - c, h - 1), (c, h - 1), (0, h - 1 - c), (0, c)]
    p.shape("polygon", oct_, fill=1)
    inner = [(c + 1, 2), (w - 2 - c, 2), (w - 3, c + 1), (w - 3, h - 2 - c), (w - 2 - c, h - 3), (c + 1, h - 3),
             (2, h - 2 - c), (2, c + 1)]
    p.d.polygon(inner, fill=0)
    p.d.line((3, 4, w - 4, 4), fill=0)
    for x in range(4, w - 4, 4):                      # 上下两道箍：铆钉
        p.px(x, 1, 0)
        p.px(x + 2, h - 2, 0)
    # 铁砂点（炉膛面板质感）
    for y in range(4, h - 3):
        for x in range(4, w - 4):
            if (x * 7 + y * 13) % 29 == 0 and not (3 <= x <= 13 or w - 14 <= x <= w - 4):
                p.px(x, y, 1)
    # 两侧四卦
    cx, cy = w // 2, WY - B_TOP
    for (name, x0, y0) in (("乾", 4, 7), ("兑", 4, 21), ("坤", w - 13, 7), ("艮", w - 13, 21)):
        bits = TRIGRAMS[name][2]
        for i in range(3):
            y = y0 + (2 - i) * 2
            if bits[i]:
                p.d.line((x0, y, x0 + 8, y), fill=1)
            else:
                p.d.line((x0, y, x0 + 3, y), fill=1)
                p.d.line((x0 + 5, y, x0 + 8, y), fill=1)
    # 圆窗：厚白圈 + 一圈铆钉
    R = WR + 3
    p.d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=1)
    p.d.ellipse((cx - WR - 1, cy - WR - 1, cx + WR + 1, cy + WR + 1), fill=0)
    for i in range(12):
        a = i / 12 * 2 * math.pi
        p.px(round(cx + math.cos(a) * (WR + 2)), round(cy + math.sin(a) * (WR + 2)), 0)
    # 右侧背光网点（外壳白边）
    p.dither([(w - 3, c), (w, c), (w, h - c), (w - 3, h - c)], 0.5, 0)
    return p.sprite()


def _crown():
    """炉顶紫外灯罩 28×13：梯形罩、竖散热片、顶钮、左边一根小烟囱、底下灯嘴"""
    p = Part(28, 13)
    p.shape("polygon", [(4, 3), (23, 3), (27, 10), (0, 10)], fill=1)
    for x in range(6, 23, 3):                          # 散热片
        p.d.line((x, 5, x - (1 if x < 14 else -1), 9), fill=0)
    p.shape("rectangle", (11, 0, 16, 2), fill=1)       # 顶钮
    p.px(13, 1, 0), p.px(14, 1, 0)
    p.shape("rectangle", (0, 10, 27, 11), fill=1)      # 罩沿
    p.d.line((1, 11, 26, 11), fill=0)
    p.shape("rectangle", (3, 0, 5, 3), fill=1)         # 小烟囱
    p.px(4, 0, 0)
    p.dither([(20, 4), (27, 10), (20, 10)], 0.5, 0)
    return p.sprite()


def _nozzle():
    """灯嘴 7×5：倒梯形镜头，镜片一点高光"""
    p = Part(7, 5)
    p.shape("polygon", [(0, 0), (6, 0), (4, 4), (2, 4)], fill=1)
    p.d.line((1, 1, 5, 1), fill=0)
    p.px(3, 3, 0)
    return p.sprite()


def _legs():
    """三只兽足：前两只外撇、足尖带爪，后一只短"""
    hh = FLOOR - B_BOT
    p = Part(52, hh)
    for x0, s in ((5, -1), (43, 1)):
        p.shape("polygon", [(x0, 0), (x0 + 4, 0), (x0 + 3 + s, hh - 4), (x0 + 4 + s * 2, hh - 1), (x0 - 1 + s * 2, hh - 1),
                            (x0 + s, hh - 4)], fill=1)
        p.d.line((x0 + 2, 2, x0 + 2 + s, hh - 6), fill=0)
        p.px(x0 + 1 + s * 2, hh - 1, 0)
    p.shape("rectangle", (24, 0, 27, 4), fill=1)
    p.d.line((25, 2, 26, 2), fill=0)
    return p.sprite()


def _shutter():
    """封炉铁盖 33×33：圆盖、十字压条、四颗铆钉、中间提手"""
    R = 16
    p = Part(2 * R + 1, 2 * R + 1)
    p.shape("ellipse", (0, 0, 2 * R, 2 * R), fill=1)
    p.d.ellipse((2, 2, 2 * R - 2, 2 * R - 2), outline=0)
    p.d.line((R, 3, R, 2 * R - 3), fill=0)
    p.d.line((3, R, 2 * R - 3, R), fill=0)
    for dx, dy in ((-7, -7), (7, -7), (-7, 7), (7, 7)):
        p.d.rectangle((R + dx - 1, R + dy - 1, R + dx, R + dy), fill=0)
    p.d.rectangle((R - 3, R - 2, R + 3, R + 2), fill=0)
    p.d.rectangle((R - 2, R - 1, R + 2, R + 1), outline=1)
    p.dither([(R + 4, 2), (2 * R, R), (R + 4, 2 * R)], 0.5, 0)
    return p.sprite()


def _chip():
    """QFP 芯片 19×19：四边各五根引脚，白壳上反白印一个“丹”，一号脚的圆点"""
    p = Part(19, 19)
    p.shape("rectangle", (3, 3, 15, 15), fill=1)
    for i in (5, 7, 9, 11, 13):
        p.shape("line", (i, 0, i, 2), fill=1)
        p.shape("line", (i, 16, i, 18), fill=1)
        p.shape("line", (0, i, 2, i), fill=1)
        p.shape("line", (16, i, 18, i), fill=1)
    glyph = _text_img("丹", 8, 1)
    gl = glyph.crop(glyph.getbbox())
    on = np.array(p.on, bool)
    ga = np.array(gl, bool)
    oy, ox = 9 - ga.shape[0] // 2, 9 - ga.shape[1] // 2
    on[oy:oy + ga.shape[0], ox:ox + ga.shape[1]] &= ~ga
    p.on = Image.fromarray(on)
    p.d = ImageDraw.Draw(p.on)
    p.px(4, 14, 0)
    return p.sprite()


def _fan(angle: int):
    """蒲扇 21×21（锚点 = 握柄 (10, 10)）：短柄、圆扇面、包边、三根扇骨"""
    p = Part(21, 21)
    a = math.radians(angle)
    ux, uy = math.cos(a), -math.sin(a)
    ox, oy = 10, 10
    cx, cy = ox + ux * 6, oy + uy * 6
    p.shape("line", (ox, oy, ox + ux * 2.5, oy + uy * 2.5), fill=1)
    p.shape("ellipse", (cx - 4, cy - 4, cx + 4, cy + 4), fill=1)
    p.d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), outline=0)
    bx, by = ox + ux * 2.5, oy + uy * 2.5
    for da in (-0.7, 0, 0.7):
        p.d.line((bx, by, cx + math.cos(a + da) * 3, cy - math.sin(a + da) * 3), fill=0)
    p.dither([(cx, cy), (cx + 5, cy), (cx + 5, cy + 5), (cx, cy + 5)], 0.5, 0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"furnace": _furnace, "crown": _crown, "nozzle": _nozzle, "legs": _legs, "shutter": _shutter,
                        "chip": _chip}[name]()
    return _PROPS[name]


def fan_sprite(angle: float):
    key = ("fan", int(round(angle / 10)) * 10)
    if key not in _PROPS:
        _PROPS[key] = _fan(key[1])
    return _PROPS[key]


FLAME = pix.frames("""
    #
    #
   ##
   ###
  ##.#
  #..##
 ##...#
 #.#..#
 #..#.#
  #..#
   ##
---
     #
    #
   ##
  ###
  #.##
 ##..#
 #...##
 #..#.#
 #.#..#
  #..#
   ##
---
   #
   ##
    #
   ###
  ##.##
  #...#
 ##.#.#
 #..#.#
 #.#..#
  #..#
   ##
""")

EMBER = pix.frames("""
 #
#.#
---
#.
.#
""")

CHIP_MX = ["..#..#..", ".######.", "##....##", ".#.##.#.", ".#.##.#.", "##....##", ".######.", "..#..#.."]


# ---------------------------------------------------------------- 画面

def room(g: Gfx):
    """背景：地砖、踢脚、后墙一扇小窗格（丹房）、炉后墙上一道熏黑的网点"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    for x in (1, 126):
        g.d.line((x, 0, x, FLOOR - 4), fill=1)
    # 丹房小窗（左上，格子窗）
    g.d.rectangle((10, 15, 26, 29), outline=1)
    g.d.line((18, 15, 18, 29), fill=1)
    g.d.line((10, 22, 26, 22), fill=1)
    pix.checker(g, (11, 16, 18, 22), 0.125)


def fire(g: Gfx, t: float, level: float, seed: int = 0):
    """炉底三团火：level 0 = 熄（余烬），1 = 正常，>1 = 窜起来"""
    for i, x in enumerate((FX - 11, FX, FX + 11)):
        if level <= 0.05:
            pix.blit(g, pix.anim(EMBER, t + i * 0.3, 3), x - 1, FLOOR - 3, outline=False)
            continue
        spr = pix.anim(FLAME, t + i * 0.23, 8)
        sy = max(0.3, min(level, 1.8)) * (0.9 + 0.2 * rand(int(t * 8) + i, seed))
        s = pix.stretch(spr, 1.0 if level < 1.3 else 1.2, sy * 0.85)
        pix.blit(g, s, x - s.w // 2, FLOOR - s.h, outline=True)
    if level > 0.5:  # 炉底被火映亮
        for x in range(FX - 18, FX + 19, 3):
            if rand(int(t * 10) + x, seed) < 0.3 * level:
                g.px(x, B_BOT + 1)


def wafer(g: Gfx, cx: float, cy: float, done: int, cur: int | None, t: float, scale: float = 1.0,
          glow: bool = False, wave: float | None = None):
    """晶圆：白圈 + 底边平口，芯片 2×2（已曝光实心、未曝光一个点、当前一颗闪）"""
    cx, cy = int(round(cx)), int(round(cy))
    r = int(round(11 * scale))
    if r < 1:
        g.px(cx, cy)
        return
    g.d.ellipse((cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1), fill=0)
    g.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=1)
    g.d.line((cx - 3, cy + r, cx + 3, cy + r), fill=0)   # 平口
    g.d.line((cx - 3, cy + r - 1, cx + 3, cy + r - 1), fill=1)
    if scale < 0.95:
        if glow:
            g.d.ellipse((cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2), fill=1)
        elif r > 3:  # 小晶圆：芯片网格缩成网点
            m = int(r * 0.7)
            pix.checker(g, (cx - m, cy - m + 1, cx + m + 1, cy + m), 0.5)
        return
    for i, (dx, dy) in enumerate(DIES):
        x, y = cx + dx, cy + dy
        lit = i < done or glow
        if wave is not None and abs(x - wave) < 3:
            lit = True
        if i == cur and not glow:
            lit = int(t * 5) % 2 == 0
            g.d.rectangle((x - 1, y - 1, x + 2, y + 2), outline=1) if int(t * 5) % 2 else None
        if lit:
            g.d.rectangle((x, y, x + 1, y + 1), fill=1)
        else:
            g.px(x, y)


def furnace(g: Gfx, t: float, hop: float = 0.0, lit_gua: float = 1.0):
    """炉子：足、炉身、灯罩（hop：灯罩跳起几像素）、灯嘴"""
    pix.blit(g, prop("legs"), FX - 26, B_BOT)
    pix.blit(g, prop("furnace"), FX - 26, B_TOP)
    if lit_gua < 1:  # 入场：四卦还没亮的盖黑
        for k, (x0, y0) in enumerate(((FX - 22, B_TOP + 7), (FX - 22, B_TOP + 21), (FX + 13, B_TOP + 7),
                                      (FX + 13, B_TOP + 21))):
            if lit_gua * 4 <= k:
                g.d.rectangle((x0, y0, x0 + 8, y0 + 4), fill=0)
    cy = B_TOP - 12 - int(round(hop))
    pix.blit(g, prop("crown"), FX - 14, cy)
    pix.blit(g, prop("nozzle"), FX - 3, B_TOP + 1)


def beam(g: Gfx, die: int, t: float, solid: bool = False):
    """紫外光束：灯嘴 → 当前芯片，虚线流动"""
    dx, dy = DIES[die]
    x1, y1 = WX + dx + 0.5, WY + dy + 0.5
    x0, y0 = NOZZLE[0], NOZZLE[1] + 1
    if solid:
        g.d.line((x0, y0, x1, y1), fill=1)
    else:
        pix.dotted(g, x0, y0, x1, y1, 3, int(t * 12) % 3)


def readout(g: Gfx, s: str):
    """右上角读数牌"""
    g.d.rectangle((105, 2, 124, 10), fill=0)
    g.d.rectangle((105, 2, 124, 10), outline=1)
    tiny(g, 115, 4, s, align="center")


def wind(g: Gfx, t: float, strength: float):
    """扇出去的风线：几道短横线往右飘向炉火"""
    if strength <= 0:
        return
    for j in range(3):
        u = (t * 2.2 + j / 3) % 1
        x = 56 + u * 18
        y = 50 + j * 2 + math.sin(u * 6 + j) * 1
        ln = int(4 * strength * (1 - u)) + 1
        g.d.line((x, y, x + ln, y), fill=1)


def mx_wafer(g: Gfx, done: int, cur: int | None, t: float, fire_lv: float):
    cells = [(r, c) for r in range(6) for c in range(6) if (r, c) not in ((0, 0), (0, 5), (5, 0), (5, 5))]
    order = []
    for r in range(6):
        row = [rc for rc in cells if rc[0] == r]
        order += row if r % 2 == 0 else row[::-1]
    n = int(round(done / N_DIE * len(order)))
    for i, (r, c) in enumerate(order):
        if i < n:
            g.mx[r, c + 1] = True
        elif cur is not None and i == n:
            g.mx[r, c + 1] = int(t * 5) % 2 == 0
    if fire_lv > 0.05:
        for c in range(1, 7):
            g.mx[7, c] = rand(int(t * 8) * 9 + c, 1) < 0.35 + 0.3 * min(fire_lv, 1.5)
    else:
        g.mx[7, 3] = g.mx[7, 4] = int(t * 3) % 2 == 0


def mx_chip(g: Gfx):
    for y, row in enumerate(CHIP_MX):
        for x, ch in enumerate(row):
            g.mx[y, x] = ch == "#"


@register
class Wafer(R6):
    id = "r6.wafer"
    name = "晶圆炼丹"
    desc = "八卦炉改的光刻机，小道士扇炉火，圆窗里的晶圆按蛇形一颗颗曝光；九转丹成蹦出一颗印着“丹”的芯片"
    T = {"enter": 6.0, "interrupt": 1.8, "resume": 2.0, "complete": 6.0}
    CYCLE = 600.0

    def init(self):
        self.last_die = None

    def done(self, e: float) -> int:
        return min(N_DIE, int((e % self.CYCLE) / self.CYCLE * N_DIE))

    def fan(self, g: Gfx, t: float, x: float = DX, speed: float = 0.9, amp: float = 1.0, face: str = "normal",
            up: bool = False):
        """扇火（up：扇自己）。返回 (手, 是否在往下扇)"""
        ph = (t / speed) % 1
        s = math.sin(ph * 2 * math.pi)
        if up:
            a = 48 + 10 * s
        else:
            a = -22 + 16 * s * amp
        h = dao(g, x, FLOOR, t, angle=a, length=8, face=face)
        fa = (a - 10 * math.cos(ph * 2 * math.pi)) if not up else 150 + 20 * s
        f = fan_sprite(fa)
        pix.blit(g, f, h["hand"][0] - 10, h["hand"][1] - 10)
        return h, math.cos(ph * 2 * math.pi) < 0

    def counter(self, g: Gfx, n: int, label: str | None = None):
        badge(g, label or nth(n, "转"))

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        room(g)
        lv = 0.0 if t < 3.0 else min(1.6, 1.6 * span(t, 3.0, 3.3)) if t < 3.6 else lerp(1.6, 1.0, span(t, 3.6, 4.4))
        fire(g, t, lv, self.seed)
        drop = ease_out_bounce(span(t, 1.0, 1.7))
        furnace(g, t, hop=(1 - drop) * 24, lit_gua=span(t, 0.0, 1.0))
        if abs(t - 1.25) < dt * 0.6:
            pix.shake(g, t, 1.5)
            self.sparks.burst(FX, B_TOP - 1, 10, 26, up=8, life=0.5)
        if 1.25 < t < 1.45:
            pix.shake(g, t, 1.2)
        # 晶圆从左边滑进圆窗
        q = ease_out(span(t, 4.2, 5.2))
        if t > 4.2:
            wafer(g, lerp(-14, WX, q), WY, 0, 0 if t > 5.3 else None, t)
        if t > 5.3:
            beam(g, 0, t)
        if abs(t - 5.3) < dt * 0.6:
            dx, dy = DIES[0]
            self.sparks.burst(WX + dx, WY + dy, 8, 18, life=0.4, gravity=0)
        # 小道士：走来 → 扇火
        if t < 2.4:
            x = lerp(-12, DX, ease_out(span(t, 0, 2.4)))
            dao(g, x, FLOOR, t, pose="walk")
        else:
            h, down = self.fan(g, t, speed=0.45 if t < 3.6 else 0.9, face="wow" if 3.0 < t < 3.6 else "normal")
            wind(g, t, 1.0)
        if abs(t - 3.0) < dt * 0.6:
            pix.flash(g)
            for x in (FX - 11, FX, FX + 11):
                self.sparks.burst(x, FLOOR - 4, 6, 26, up=24, life=0.6)
        if 3.0 < t < 3.3:
            pix.shake(g, t, 1.2)
        self.fx(g, dt)
        mx_wafer(g, 0, 0 if t > 5.3 else None, t, lv)
        if t < 4.2:  # 晶圆还没进炉：点阵是一圈空的窗框，按四卦亮起的进度画出来
            ring = [(0, 2), (0, 3), (0, 4), (0, 5), (1, 6), (2, 7), (3, 7), (4, 7), (5, 6), (6, 5), (6, 4), (6, 3),
                    (6, 2), (5, 1), (4, 0), (3, 0), (2, 0), (1, 1)]
            for i, (r, c) in enumerate(ring):
                if i < len(ring) * span(t, 0, 1.6):
                    g.mx[r, c] = True
        if t > 5.3:
            readout(g, "00/37")
            self.counter(g, 1)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        n = int(e // self.CYCLE) + 1
        if e >= self.CYCLE and k < RENEW:
            self.renew(g, t, e, k, dt)
            return
        done = self.done(e)
        cur = min(done, N_DIE - 1)
        room(g)
        ph = t % LOOP
        loop = int(t // LOOP)
        burp = loop % 2 == 0 and 14 < ph < 17
        hot = loop % 2 == 1 and 14 < ph < 17.5
        peek = 24 < ph < 26.5
        lv = 0.75 if hot or peek else 1.0
        hop = 0.0
        if burp:
            bk = ph - 14
            hop = abs(math.sin(bk * 14)) * 3 * (1 - span(bk, 0, 1.2))
            if bk < 1.2:
                pix.shake(g, t, 0.8)
        # 扇火：往下扇的瞬间火一窜
        stroke = (t / 0.9) % 1
        if not (burp or hot or peek):
            lv = 1.0 + 0.45 * max(0.0, math.sin(stroke * 2 * math.pi + 1.0))
        fire(g, t, lv, self.seed)
        furnace(g, t, hop=hop)
        wafer(g, WX, WY, done, cur, t)
        beam(g, cur, t, solid=self.last_die is not None and self.last_die != done)
        if self.last_die is not None and done != self.last_die:   # 一颗曝完：火星
            dx, dy = DIES[min(self.last_die, N_DIE - 1)]
            self.sparks.burst(WX + dx, WY + dy, 8, 18, life=0.45, gravity=10)
        self.last_die = done
        if burp:
            bk = ph - 14
            if abs(bk - 0.1) < dt * 0.6:
                for j in range(4):
                    self.puffs.emit(FX - 10, B_TOP - 13, vx=-4, vy=-10, life=1.6, rmax=3.2, spread=3)
                self.sparks.burst(FX - 10, B_TOP - 12, 8, 24, up=14, life=0.6)
            h = dao(g, DX - (2 if bk < 1.2 else 0), FLOOR, t, angle=-40, length=8, face="wow")
            pix.blit(g, fan_sprite(-50), h["hand"][0] - 10, h["hand"][1] - 10)
        elif hot:
            # 热得满头大汗：停下喘气，汗珠一颗颗甩出去
            h = dao(g, DX, FLOOR, t, angle=-40, length=8, face="sleep" if int(t * 3) % 2 else "happy")
            pix.blit(g, fan_sprite(-50), h["hand"][0] - 10, h["hand"][1] - 10)
            hk = (ph - 14) % 0.7
            if hk < dt * 1.01:
                side = 1 if int((ph - 14) / 0.7) % 2 else -1
                self.sparks.p.append([DX + side * 7, FLOOR - 30, side * 18, -22, 0.0, 0.7, 70])
            for q in self.sparks.p:
                if q[5] == 0.7:   # 汗珠：画成 1×2 的水滴
                    g.px(q[0], q[1] - 1)
        elif peek:
            h = dao(g, DX + 2, FLOOR, t, angle=18, hand="point", face="happy")
        else:
            h, down = self.fan(g, t)
            wind(g, t, 1.0)
            if down and int(t * 30) % 5 == 0:
                self.sparks.burst(FX + (rand(int(t * 30), 3) - 0.5) * 20, FLOOR - 7, 1, 14, up=18, life=0.5,
                                  gravity=20)
        pixsmoke(g, FX - 10, B_TOP - 13 - hop, t, seed=self.seed, height=10, amount=0.7, sway=2, bits=False)
        self.fx(g, dt, wind=-2)
        mx_wafer(g, done, cur, t, lv)
        readout(g, f"{done:02d}/37")
        self.counter(g, n)

    def renew(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """一轮满：光波扫过 → 晶圆滑出落到手里 → 收好 → 新晶圆滑进去"""
        n = int(e // self.CYCLE)
        room(g)
        fire(g, t, 1.0, self.seed)
        furnace(g, t)
        if k < 1.2:
            wave = lerp(WX - 14, WX + 14, span(k, 0.1, 1.1))
            wafer(g, WX, WY, N_DIE, None, t, wave=wave)
            g.d.line((wave, WY - 12, wave, WY + 12), fill=1)
            h, _ = self.fan(g, t)
            if abs(k - 1.1) < dt * 0.6:
                self.sparks.burst(WX, WY, 14, 30, life=0.5, gravity=0)
        elif k < 3.4:
            hx, hy = DX + 9, FLOOR - 12
            q = ease_in_out(span(k, 1.2, 2.2))
            px = lerp(WX, hx + 8, q)
            py = lerp(WY, hy - 6, q) - math.sin(q * math.pi) * 8
            if k < 3.0:
                dao(g, DX, FLOOR, t, pose="offer", face="wow" if k < 2.2 else "happy")
                wafer(g, px, py, N_DIE, None, t, scale=lerp(1.0, 0.6, q), glow=False)
            else:
                dao(g, DX, FLOOR, t, pose="gong", face="happy")
            if abs(k - 2.2) < dt * 0.6:
                self.sparks.burst(hx + 8, hy - 6, 8, 18, life=0.4)
            if abs(k - 3.0) < dt * 0.6:
                self.puffs.emit(hx + 2, hy - 8, vy=-6, life=0.7, rmax=3, spread=0)
                self.sparks.burst(hx + 2, hy - 8, 10, 22, up=8, life=0.5)
        else:
            q = ease_out_back(span(k, 3.4, 4.4))
            wafer(g, lerp(140, WX, q), WY, 0, 0 if k > 4.5 else None, t)
            if k > 4.5:
                beam(g, 0, t)
            h, _ = self.fan(g, t, speed=0.6 if k > 4.4 else 0.9)
            wind(g, t, 1.0)
        self.fx(g, dt)
        mx_wafer(g, N_DIE if k < 3.4 else 0, None, t, 1.0)
        readout(g, "37/37" if k < 3.4 else "00/37")
        self.counter(g, n + (1 if k >= 2.2 else 0))

    # ------------------------------------------------------------ 中断 / 恢复

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        done = self.done(e)
        cur = min(done, N_DIE - 1)
        room(g)
        lv = 1.0 - span(t, 0.1, 0.8)
        fire(g, t, lv, self.seed)
        furnace(g, t)
        wafer(g, WX, WY, done, cur if t < 0.5 else None, t)
        if t < 0.5:
            beam(g, cur, t)
        q = span(t, 0.5, 1.4)
        if q > 0:
            sy = lerp(-40, WY - 16, ease_out_bounce(q))
            pix.blit(g, prop("shutter"), WX - 16, sy)
            if abs(q - 0.364) < dt / 0.9 * 0.6:
                pix.shake(g, t, 2)
                self.sparks.burst(WX - 14, WY + 6, 8, 24, up=10, life=0.5)
                self.sparks.burst(WX + 14, WY + 6, 8, 24, up=10, life=0.5)
        if t < 0.4:
            self.fan(g, t)
        else:
            h = dao(g, DX, FLOOR, t, angle=-40, length=8, face="normal" if t < 1.2 else "happy")
            pix.blit(g, fan_sprite(-50), h["hand"][0] - 10, h["hand"][1] - 10)
        if 0.2 < t < 0.8 and int(t * 30) % 4 == 0:
            self.puffs.emit(FX + (rand(int(t * 30), 2) - 0.5) * 20, FLOOR - 4, vy=-6, life=0.9, rmax=1.8)
        self.fx(g, dt)
        mx_wafer(g, done, None, t, lv)
        readout(g, f"{done:02d}/37")
        self.counter(g, int(e // self.CYCLE) + 1, "封炉" if t > 0.9 else None)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        done = self.done(e)
        cur = min(done, N_DIE - 1)
        room(g)
        lv = 0.0 if t < 0.8 else (1.7 if t < 1.1 else lerp(1.7, 1.0, span(t, 1.1, 1.9)))
        fire(g, t, lv, self.seed)
        furnace(g, t)
        wafer(g, WX, WY, done, cur if t > 0.7 else None, t)
        if t > 0.7:
            beam(g, cur, t)
        q = ease_in(span(t, 0.0, 0.6))
        if q < 1:
            pix.blit(g, prop("shutter"), WX - 16, lerp(WY - 16, -40, q))
        if abs(t - 0.8) < dt * 0.6:
            pix.flash(g)
            for x in (FX - 11, FX, FX + 11):
                self.sparks.burst(x, FLOOR - 4, 6, 28, up=24, life=0.6)
        if 0.8 < t < 1.1:
            pix.shake(g, t, 1.2)
        if t < 0.25:
            h = dao(g, DX, FLOOR, t, angle=-40, length=8)
            pix.blit(g, fan_sprite(-50), h["hand"][0] - 10, h["hand"][1] - 10)
        else:
            self.fan(g, t, speed=0.3 if t < 1.4 else 0.9, face="wow" if 0.8 < t < 1.2 else "normal")
            wind(g, t, 1.4 if t < 1.4 else 1.0)
        self.fx(g, dt)
        mx_wafer(g, done, cur if t > 0.7 else None, t, lv)
        readout(g, f"{done:02d}/37")
        self.counter(g, int(e // self.CYCLE) + 1, "封炉" if t < 0.4 else None)

    # ------------------------------------------------------------ 圆满

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        d0 = self.done(e)
        done = int(lerp(d0, N_DIE, span(t, 0.0, 1.4)))
        room(g)
        lv = 1.0 if t < 1.4 else (1.8 if t < 2.0 else lerp(1.8, 0.9, span(t, 2.0, 3.0)))
        fire(g, t, lv, self.seed)
        furnace(g, t, hop=abs(math.sin(t * 20)) * 2 if 1.4 < t < 1.9 else 0)
        if t < 1.4:
            cur = min(done, N_DIE - 1)
            wafer(g, WX, WY, done, cur, t)
            beam(g, cur, t, solid=True)
            if self.last_die != done:
                dx, dy = DIES[cur]
                self.sparks.burst(WX + dx, WY + dy, 3, 14, life=0.3, gravity=0)
            self.last_die = done
        elif t < 2.2:
            sc = 1 - ease_in(span(t, 1.5, 2.2))
            wafer(g, WX, WY, N_DIE, None, t, scale=sc, glow=True)
            glow_rays(g, WX, WY, 15, 15 + 6 * span(t, 1.4, 1.8), 12, t * 2, 1.0, dashed=True)
        if abs(t - 1.4) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst(WX, WY, 24, 40, up=10, life=0.9, gravity=30)
        if 1.4 < t < 1.8:
            pix.shake(g, t, 1.6)
        # 芯片蹦出来飞到小道士手上 → 高举
        hand_up = (DX + 5, FLOOR - 33)
        if 2.0 <= t < 2.8:
            q = span(t, 2.0, 2.8)
            px = lerp(WX, hand_up[0], ease_in_out(q))
            py = lerp(WY, hand_up[1] - 8, ease_in_out(q)) - math.sin(q * math.pi) * 14
            spr = pix.stretch(prop("chip"), lerp(0.4, 1, ease_out_back(min(q * 2, 1))), lerp(0.4, 1, ease_out_back(min(q * 2, 1))))
            pix.blit(g, spr, px - spr.w / 2, py - spr.h / 2)
            if int(t * 30) % 2 == 0:
                self.sparks.burst(px, py, 1, 8, life=0.3, gravity=0)
        if t < 2.6:
            if t < 1.4:
                self.fan(g, t, speed=0.3)
            else:
                h = dao(g, DX, FLOOR, t, angle=-40, length=8, face="wow")
                pix.blit(g, fan_sprite(-50), h["hand"][0] - 10, h["hand"][1] - 10)
        else:
            h = dao(g, DX, FLOOR, t, pose="raise", face="happy")
            if t >= 2.8:
                hx, hy = h["hand"]
                bob = int(abs(math.sin(t * 5)) * 2)
                pix.blit(g, prop("chip"), hx - 9, hy - 19 - bob)
                if int(t * 8) % 3 == 0:
                    glow_rays(g, hx, hy - 10, 12, 15, 8, t, 1.0)
        if abs(t - 2.8) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst(h["hand"][0], h["hand"][1] - 8, 20, 36, up=14, life=1.0, gravity=40)
        if 2.8 < t < 3.1:
            pix.shake(g, t, 1.2)
        self.fx(g, dt)
        if t < 1.4:
            mx_wafer(g, done, min(done, N_DIE - 1), t, lv)
            g.mx_level = 2
        else:
            if int(t * 4) % 2 == 0 or t < 2.8:
                mx_chip(g)
            else:
                mx_wafer(g, N_DIE, None, t, lv)
            g.mx_level = 1 + int(6 * (1 - span(t, 1.4, 3.2)))
        if t < 3.0:
            readout(g, f"{done:02d}/37")
            self.counter(g, int(e // self.CYCLE) + 1)
        banner(g, 93, 3, "九转丹成", span(t, 3.0, 3.4), t=t)
