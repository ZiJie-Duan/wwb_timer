"""代码符箓（像素风）：小道士在工位上敲代码，每敲完一行，右边的笔式绘图仪就在黄符纸上画出符的对应一部分。

画面：左边小道士站在办公桌前敲键盘；桌上一台 CRT 显示器（屏幕朝外），编辑器里一行行短代码，行号、光标、状态栏；
右边一台立式 XY 绘图仪（两根立柱、顶梁两头电机、横梁带笔架），夹着一张竖长的符纸。
符的结构取自符箓的常见格式：符头（三勾，象三清）→ 敕令 → 符胆 → 符脚，末了盖法印；
“急急如律令”本是汉代公文结语，后为道教咒语、符文的通用结尾。

入场：符纸从上面落进绘图仪、弹两下；显示器开机，横线一闪展开成编辑器，状态栏“-INSERT-”；小道士走到桌前开敲。
持续：一轮 10 分钟。五行代码各占一段：先一个字一个字敲出来（键盘咔嗒、迸小火星），回车后绘图仪笔架跑过去，
      按行扫描把这一部分画到符上（法印是“啪”地盖下去的）；最后状态栏 BUILD 进度条，0 ERR，符纸边缘闪光。
      每 6 秒一道扫描线扫过符纸（语法检查）；小道士看绘图时会伸剑指指点；每 30 秒端起茶杯喝一口；
      隔一轮来一次 ERR：状态栏反色闪，小道士一惊，一巴掌拍在键盘上（震屏、火星），状态栏 OK。
      一轮满：“急急如律令”弹出，符纸下端起火、烧着往上飞走，新符纸从上面落下，编辑器清空，“第几道”加一。
中断：状态栏敲出“:WQ”，屏上弹出软盘存盘图标，“已保存”，小道士收手。
恢复：状态栏敲“VIM FU.C”，屏幕刷新，回到 -INSERT- 接着敲。
圆满：剩下的代码一口气敲完、绘图仪飞快画完、编译 0 ERR，闪白，符纸放光，“急急如律令”，符从下往上燃尽化灰飘散。
点阵：第一行标签栏，下面五行是五行代码的缩略图（随字数变长），光标闪；编译时底行进度条；圆满时火焰。
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_bounce, lerp, rand, span
from ..engine.chars import Part
from ..engine.gfx import Gfx, Sprite, _FONT_FILES, font
from ..engine.scene import register
from .r6_common import R6, badge, banner, dao, glow_rays, nth, rise, tiny

FLOOR = 58
DAO_X = 17
DESK = (22, 94, 49)            # 桌 x0, x1, 桌面 y
MON = (40, 11)                 # 显示器左上角
SCR = (45, 14, 85, 40)         # 屏幕内框（含）
ROWS = (16, 22, 28)            # 代码行 y
STATUS_Y = 34                  # 状态栏顶
PAPER = (100, 9)               # 符纸左上角
PW, PH = 21, 48
PARK = (110, 0)                # 笔架停靠处（顶梁下）
TYPE_FR = 0.4                  # 每段里打字占的比例
SEG = 0.16                     # 每行一段（一轮的比例）
BUILD0, BUILD1 = 0.80, 0.97
RENEW = 6.0
LOOP = 30.0

CODES = [
    ["$SUDO FU", "CHI LING", "DAN -9", "JIAO", "SEAL"],
    ["IMPORT FU", "CHI()", "DAN(9)", "JIAO()", "SEAL()"],
    ["FU(){", "CHI();", "DAN(9);", "JIAO();", "SEAL;}"],
]


# ---------------------------------------------------------------- 道具（像素造型，只生成一次）

def _monitor():
    """CRT 显示器 51×38：圆角外壳、凹进去的屏框、下沿散热槽与电源灯、右侧背光网点、颈、底座"""
    p = Part(51, 38)
    p.shape("rectangle", (1, 0, 49, 33), fill=1)
    p.shape("rectangle", (0, 1, 50, 32), fill=1)
    p.d.rectangle((4, 2, 46, 30), fill=0)            # 屏框凹槽（阴线）
    p.d.rectangle((5, 3, 45, 29), fill=1)            # 屏幕玻璃（之后在上面画黑底）
    p.d.rectangle((5, 3, 45, 29), fill=0)
    p.px(5, 3, 1), p.px(45, 3, 1), p.px(5, 29, 1), p.px(45, 29, 1)   # 屏幕圆角
    for x in range(6, 19, 3):                        # 散热槽
        p.d.line((x, 31, x + 1, 31), fill=0)
    p.d.rectangle((42, 31, 44, 32), fill=0)          # 电源灯
    p.px(43, 31, 1)
    p.dither([(47, 2), (50, 2), (50, 32), (47, 32)], 0.5, 0)
    p.d.line((1, 33, 49, 33), fill=0)
    p.shape("rectangle", (20, 34, 30, 35), fill=1)   # 颈
    p.shape("rectangle", (14, 36, 36, 37), fill=1)   # 底座
    p.d.line((15, 37, 35, 37), fill=0)
    p.dither([(28, 34), (36, 34), (36, 37), (28, 37)], 0.5, 0)
    return p.sprite()


def _keyboard():
    """键盘 16×4（斜看）：键帽一格格、空格键、右侧网点"""
    p = Part(16, 4)
    p.shape("polygon", [(1, 0), (15, 0), (15, 3), (0, 3)], fill=1)
    for x in range(2, 15, 2):
        p.px(x, 1, 0)
    for x in range(1, 15, 2):
        p.px(x, 2, 0)
    p.d.line((5, 3, 10, 3), fill=0)
    return p.sprite()


def _desk():
    """办公桌 73×9：桌面厚边、两条腿、抽屉（拉手）、网点阴影"""
    w = DESK[1] - DESK[0] + 1
    p = Part(w, FLOOR - DESK[2])
    p.shape("rectangle", (0, 0, w - 1, 1), fill=1)
    p.d.line((1, 1, w - 2, 1), fill=0)
    p.shape("rectangle", (2, 2, 4, FLOOR - DESK[2] - 1), fill=1)
    p.shape("rectangle", (w - 5, 2, w - 3, FLOOR - DESK[2] - 1), fill=1)
    p.shape("rectangle", (w - 26, 2, w - 6, 6), fill=1)      # 抽屉
    p.d.rectangle((w - 25, 3, w - 7, 5), outline=0)
    p.d.line((w - 18, 4, w - 14, 4), fill=0)
    p.dither([(w - 25, 5), (w - 6, 5), (w - 6, 6), (w - 25, 6)], 0.5, 0)
    p.px(3, 4, 0), p.px(w - 4, 4, 0)
    return p.sprite()


def _cup():
    """茶杯 5×4（带把）"""
    p = Part(5, 4)
    p.shape("rectangle", (0, 0, 3, 3), fill=1)
    p.d.line((0, 1, 3, 1), fill=0)
    p.px(4, 1), p.px(4, 2)
    return p.sprite()


def _carriage():
    """绘图仪笔架 7×8：滑块（螺丝孔）+ 笔杆 + 笔尖"""
    p = Part(7, 8)
    p.shape("rectangle", (0, 0, 6, 3), fill=1)
    p.px(1, 1, 0), p.px(5, 1, 0)
    p.d.line((1, 3, 5, 3), fill=0)
    p.shape("rectangle", (2, 4, 4, 5), fill=1)
    p.shape("line", (3, 6, 3, 7), fill=1)
    return p.sprite()


def _floppy():
    """软盘 11×11：标签、金属滑盖、写保护口"""
    p = Part(11, 11)
    p.shape("polygon", [(0, 0), (9, 0), (10, 1), (10, 10), (0, 10)], fill=1)
    p.d.rectangle((3, 0, 7, 3), fill=0)
    p.d.rectangle((5, 1, 6, 2), fill=1)
    p.d.rectangle((2, 6, 8, 10), fill=0)
    p.d.line((3, 7, 7, 7), fill=1)
    p.d.line((3, 9, 6, 9), fill=1)
    return p.sprite()


def _talisman():
    """完整的符（21×48）：返回 (纸面 on, 墨迹 ink)。墨 = 暗像素。
    符头三勾 → 敕 → 令 → 符胆回纹 → 符脚（左）+ 法印（右）"""
    p = Part(PW, PH)
    p.shape("rectangle", (0, 0, PW - 1, PH - 1), fill=1)
    ink = np.zeros((PH, PW), bool)
    ink_d = Part(PW, PH)
    d = ink_d.d
    for x in (5, 10, 15):                                    # 符头：三勾
        d.point((x, 1), fill=1)
        d.line((x, 3, x, 6), fill=1)
        d.point((x - 1, 6), fill=1)
        d.point((x - 2, 5), fill=1)
    d.line((3, 7, 17, 7), fill=1)
    d.fontmode = "1"
    off = _FONT_FILES[12][1]
    for ch, y in (("敕", 9), ("令", 21)):                     # 敕令
        d.text((5, y - off), ch, font=font(12), fill=1)
    sx, sy = 6, 33                                           # 符胆：方回纹
    d.rectangle((sx, sy, sx + 8, sy + 6), outline=1)
    d.line((sx + 2, sy + 2, sx + 6, sy + 2), fill=1)
    d.line((sx + 6, sy + 2, sx + 6, sy + 4), fill=1)
    d.line((sx + 4, sy + 4, sx + 6, sy + 4), fill=1)
    d.line((sx + 2, sy + 2, sx + 2, sy + 4), fill=1)
    d.line((7, 41, 7, 46), fill=1)                           # 符脚
    d.line((4, 42, 10, 42), fill=1)
    d.line((3, 44, 6, 44), fill=1)
    d.line((7, 46, 9, 47), fill=1)
    d.point((5, 46), fill=1)
    ink |= np.array(ink_d.on, bool)
    seal = np.zeros((PH, PW), bool)                          # 法印：实心方印，阳文回字
    seal[39:46, 12:19] = True
    seal[40, 13:18] = False
    seal[44, 13:18] = False
    seal[40:45, 13] = False
    seal[40:45, 17] = False
    seal[42, 15] = False
    return ink, seal


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"monitor": _monitor, "keyboard": _keyboard, "desk": _desk, "cup": _cup,
                        "carriage": _carriage, "floppy": _floppy}[name]()
    return _PROPS[name]


_FU: dict = {}


def fu_parts():
    """五部分的墨迹像素（按绘图仪的蛇形扫描排好序）"""
    if not _FU:
        ink, seal = _talisman()
        ranges = [(0, 8), (8, 32), (32, 40), (40, 48)]
        parts = []
        for k, (y0, y1) in enumerate(ranges):
            pts = []
            for y in range(y0, y1):
                xs = [x for x in range(PW) if ink[y, x] and not (k == 3 and x >= 12)]
                pts += [(x, y) for x in (xs if y % 2 == 0 else xs[::-1])]
            parts.append(pts)
        parts.append([(x, y) for y in range(PH) for x in range(PW) if seal[y, x]])
        _FU["parts"] = parts
        _FU["seal"] = seal
    return _FU["parts"]


_PAPER_CACHE: dict = {}


def paper_sprite(revealed: tuple, burn: float = 0.0) -> Sprite:
    """符纸（白）+ 已画出的墨（暗）。revealed = 每部分已画的像素数；burn：从下往上烧掉的比例"""
    key = (revealed, round(burn, 2))
    s = _PAPER_CACHE.get(key)
    if s is not None:
        return s
    parts = fu_parts()
    on = np.ones((PH, PW), bool)
    mask = np.ones((PH, PW), bool)
    for k, n in enumerate(revealed):
        if k == 4:
            if n:
                on[_FU["seal"]] = False
            continue
        for x, y in parts[k][:n]:
            on[y, x] = False
    on[0, 3:5] = False            # 夹子印
    on[0, 16:18] = False
    if burn > 0:
        edge = PH - burn * PH
        for x in range(PW):
            e = edge + math.sin(x * 1.3) * 1.5 + (x % 3)
            for y in range(PH):
                if y > e:
                    mask[y, x] = on[y, x] = False
                elif y > e - 2 and (x + y) % 2 == 0:
                    on[y, x] = False          # 焦边
    s = Sprite(on=on, mask=mask)
    if len(_PAPER_CACHE) > 400:
        _PAPER_CACHE.clear()
    _PAPER_CACHE[key] = s
    return s


FLAME = pix.frames("""
 #
 ##
###
#.#
---
  #
 ##
 ##
###
---
 #
 #
###
##.
""")


# ---------------------------------------------------------------- 进度（全是 e 的函数）

def state(k: float, C: float, codes):
    """一轮里的进度：k = 本轮秒数。返回 dict：line 当前行、typed 各行已敲字数、rev 各部分已画像素、
    phase type/plot/build/done、q 本段进度、pen 笔尖位置（纸面坐标）、b 编译进度"""
    parts = fu_parts()
    p = k / C
    typed = [0] * 5
    rev = [0] * 5
    out = {"phase": "done", "line": 4, "q": 1.0, "b": 1.0, "pen": None, "stamp": None}
    for i in range(5):
        a = i * SEG
        if p < a:
            break
        u = (p - a) / SEG
        if u >= 1:
            typed[i] = len(codes[i])
            rev[i] = len(parts[i])
            continue
        out["line"] = i
        out["q"] = u
        if u < TYPE_FR:
            out["phase"] = "type"
            typed[i] = min(len(codes[i]), int(u / (TYPE_FR * 0.92) * (len(codes[i]) + 1)))
            prev = parts[i - 1][-1] if i > 0 and parts[i - 1] else None
            if prev and u < 0.03:
                out["pen"] = (lerp(prev[0], PARK[0] - PAPER[0], u / 0.03), lerp(prev[1], PARK[1] - PAPER[1], u / 0.03))
        else:
            out["phase"] = "plot"
            typed[i] = len(codes[i])
            q = (u - TYPE_FR) / (1 - TYPE_FR)
            first = parts[i][0]
            if i == 4:   # 法印：笔架移过去，啪地盖下
                tgt = (15, 42)
                if q < 0.2:
                    out["pen"] = (lerp(PARK[0] - PAPER[0], tgt[0], ease_in_out(q / 0.2)),
                                  lerp(PARK[1] - PAPER[1], tgt[1], ease_in_out(q / 0.2)))
                else:
                    rev[i] = 1
                    out["pen"] = tgt if q < 0.35 else (lerp(tgt[0], PARK[0] - PAPER[0], span(q, 0.35, 0.5)),
                                                       lerp(tgt[1], PARK[1] - PAPER[1], span(q, 0.35, 0.5)))
                    out["stamp"] = (q - 0.2) * (1 - TYPE_FR) * SEG * C   # 盖下后过了几秒
            elif q < 0.06:
                out["pen"] = (lerp(PARK[0] - PAPER[0], first[0], ease_in_out(q / 0.06)),
                              lerp(PARK[1] - PAPER[1], first[1], ease_in_out(q / 0.06)))
            else:
                n = int(span(q, 0.06, 1.0) * len(parts[i]))
                rev[i] = n
                out["pen"] = parts[i][max(n - 1, 0)]
        break
    if p >= BUILD0:
        typed = [len(c) for c in codes]
        rev = [len(pp) for pp in parts]
        rev[4] = 1
        out["phase"] = "build" if p < BUILD1 else "done"
        out["b"] = span(p, BUILD0, BUILD1)
        out["line"] = 4
    out["typed"] = typed
    out["rev"] = tuple(rev)
    return out


# ---------------------------------------------------------------- 画面

def room(g: Gfx, t: float):
    """背景：地砖、踢脚、墙上一扇小窗、办公桌、绘图仪立柱与顶梁"""
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 94, FLOOR - 3), fill=1)
    pix.blit(g, prop("desk"), DESK[0], DESK[2])
    for x in (95, 124):                                       # 绘图仪立柱
        g.d.rectangle((x, 5, x + 1, FLOOR - 1), fill=1)
        g.d.line((x - 1, FLOOR - 1, x + 2, FLOOR - 1), fill=1)
        for y in range(10, FLOOR - 2, 4):
            g.px(x + 1, y, 0)
    g.d.rectangle((94, 3, 126, 5), fill=1)                    # 顶梁 + 两头电机
    g.d.line((95, 4, 125, 4), fill=0)
    for x in (93, 122):
        g.d.rectangle((x, 1, x + 4, 7), fill=1)
        g.d.rectangle((x + 1, 2, x + 3, 6), outline=0)
        g.px(x + 2, 4, 1 if int(t * 3) % 2 else 0)
    g.d.line((PAPER[0] + 3, 6, PAPER[0] + 4, PAPER[1]), fill=1)   # 夹子
    g.d.line((PAPER[0] + 17, 6, PAPER[0] + 16, PAPER[1]), fill=1)


def monitor(g: Gfx, on: float = 1.0):
    """显示器（on：开机进度，<1 时是一道横线从中间展开）"""
    pix.blit(g, prop("monitor"), *MON)
    if 0 < on < 1:
        x0, y0, x1, y1 = SCR
        cy = (y0 + y1) // 2
        h = int((y1 - y0) / 2 * ease_out(span(on, 0.3, 1.0)))
        w = int((x1 - x0) / 2 * ease_out(span(on, 0, 0.3)))
        cx = (x0 + x1) // 2
        g.d.rectangle((cx - w, cy - h, cx + w, cy + h), fill=1)
    if on >= 1:
        g.px(MON[0] + 43, MON[1] + 31, 1)


def status(g: Gfx, s: str, inv: bool = False):
    """状态栏：白条黑字（inv：黑条白字）"""
    x0, _, x1, y1 = SCR
    if not inv:
        g.d.rectangle((x0, STATUS_Y, x1, y1), fill=1)
        tiny(g, x0 + 2, STATUS_Y + 1, s, fill=0)
    else:
        g.d.rectangle((x0, STATUS_Y, x1, y1), outline=1)
        tiny(g, x0 + 2, STATUS_Y + 1, s)


def code_view(g: Gfx, codes, typed, line: int, t: float, cursor: bool = True):
    """编辑器：最近三行（行号 + 代码），光标闪"""
    first = max(0, line - 2)
    x0 = SCR[0] + 1
    for r, i in enumerate(range(first, min(first + 3, 5))):
        y = ROWS[r]
        tiny(g, x0, y, str(i + 1))
        g.px(x0 + 4, y + 1), g.px(x0 + 4, y + 3)
        s = codes[i][:typed[i]]
        tiny(g, x0 + 6, y, s)
        if cursor and i == line and int(t * 2.5) % 2 == 0:
            cx = x0 + 6 + len(s) * 4
            if cx + 2 <= SCR[2]:
                g.d.rectangle((cx, y, cx + 2, y + 4), fill=1)


def keyboard(g: Gfx, press: int | None = None):
    pix.blit(g, prop("keyboard"), 25, DESK[2] - 4)
    if press is not None:
        g.px(27 + press * 2, DESK[2] - 3, 0)
        g.px(28 + press * 2, DESK[2] - 3, 0)


def cup(g: Gfx, at=None, t: float = 0.0):
    """茶杯：在桌上（at=None）或手里；冒两缕热气"""
    x, y = at if at else (44, DESK[2] - 4)
    pix.blit(g, prop("cup"), x - 2, y)
    for j in range(2):
        u = (t * 0.8 + j * 0.5) % 1
        g.px(x - 1 + j * 2 + round(math.sin(u * 6 + j) * 0.7), y - 2 - int(u * 5))


def plotter_pen(g: Gfx, pen, t: float, busy: bool):
    """横梁 + 笔架（pen 为纸面坐标；None = 停靠）"""
    if pen is None:
        px, py = PARK
    else:
        px, py = PAPER[0] + pen[0], PAPER[1] + pen[1]
    ix, iy = int(round(px)), int(round(py))
    by = iy + 5                      # 横梁在笔尖下方（笔朝上画，已画的墨不被挡住）
    g.d.rectangle((94, by - 1, 126, by + 2), fill=0)
    g.d.rectangle((95, by, 125, by + 1), fill=1)
    g.d.line((97, by + 1, 123, by + 1), fill=0)
    pix.blit(g, _carriage_up(), ix - 3, iy)
    if busy and int(t * 12) % 2 == 0:
        g.px(ix + 1, iy - 1)
        g.px(ix - 1, iy - 1)


_CU = []


def _carriage_up():
    if not _CU:
        _CU.append(prop("carriage").flipv())
    return _CU[0]


def scanline(g: Gfx, t: float, top: int = PAPER[1], h: int = PH):
    """每 6 秒一道扫描线扫过符纸（反色一行）"""
    u = (t % 6.0) / 0.9
    if u < 1:
        y = int(top + u * h)
        g.invert((PAPER[0], y, PAPER[0] + PW, y + 1))


def mx_code(g: Gfx, codes, typed, line: int, t: float, b: float | None = None):
    g.mx[0, 0:3] = True
    g.mx[0, 4] = True
    for i in range(5):
        n = int(round(typed[i] / max(len(codes[i]), 1) * 7))
        for x in range(n):
            g.mx[1 + i, x] = True
        if i == line and n < 8 and int(t * 2.5) % 2 == 0:
            g.mx[1 + i, min(n, 7)] = True
    if b is not None:
        for x in range(int(round(b * 8))):
            g.mx[7, x] = True


def mx_fire(g: Gfx, t: float):
    for x in range(8):
        h = 2 + int(rand(x * 5 + int(t * 10), 7) * 5)
        for y in range(8 - h, 8):
            g.mx[y, x] = True
        if h < 7 and rand(x + int(t * 10), 9) > 0.6:
            g.mx[7 - h - 1, x] = True


@register
class CodeFu(R6):
    id = "r6.codefu"
    name = "代码符箓"
    desc = "小道士在工位上敲代码，每敲完一行，右边的绘图仪就在符纸上画出一部分；编译 0 ERR，急急如律令"
    T = {"enter": 5.5, "interrupt": 1.6, "resume": 1.8, "complete": 5.5}
    CYCLE = 600.0

    def init(self):
        self.codes = CODES[self.rng.randrange(len(CODES))]
        self.last_key = None

    def counter(self, g: Gfx, e: float, label: str | None = None):
        badge(g, label or nth(int(e // self.CYCLE) + 1, "道"))

    def typing(self, g: Gfx, t: float, typed_total: int, speed: float = 7.0, face: str = "normal"):
        """敲键盘：手臂两档上下交替；字数一变就咔嗒一下迸火星"""
        up = int(t * speed) % 2 == 0
        h = dao(g, DAO_X, FLOOR, t, angle=-18 if up else -30, face=face)
        if typed_total != self.last_key:
            if self.last_key is not None:
                self.sparks.burst(h["hand"][0] + 1, DESK[2] - 4, 4, 16, up=14, life=0.3, gravity=50)
            self.last_key = typed_total
        return None if up else (int(t * speed * 3.7) % 6)

    def scene(self, g: Gfx, t: float, e: float, st, dt: float, act: str | None = None, act_t: float = 0.0,
              paper_dy: float = 0.0, burn: float = 0.0, flames: bool = False):
        """一帧的通用部分：房间、桌上设备、符纸、绘图仪、小道士；返回 None"""
        room(g, t)
        monitor(g)
        # 符纸
        if burn < 1:
            pix.blit(g, paper_sprite(st["rev"], burn), PAPER[0], PAPER[1] + paper_dy)
            if flames:
                edge = PAPER[1] + paper_dy + PH - burn * PH
                for j, x in enumerate(range(PAPER[0] + 1, PAPER[0] + PW - 2, 5)):
                    pix.blit(g, pix.anim(FLAME, t + j * 0.21, 9), x, edge - 4 + (j % 2), outline=False)
                self.sparks.burst(PAPER[0] + 3 + rand(int(t * 30), 2) * (PW - 6), edge - 2, 1, 10, up=20,
                                  life=0.8, gravity=-10)
        if st.get("stamp") is not None and st["stamp"] < 0.35:
            pix.shake(g, t, 1.2)
            if st["stamp"] < 0.05:
                self.sparks.burst(PAPER[0] + 15, PAPER[1] + 42, 10, 26, up=6, life=0.4)
        scanline(g, t) if burn == 0 and paper_dy == 0 else None
        busy = st["phase"] == "plot"
        plotter_pen(g, st["pen"] if busy or st["pen"] else None, t, busy)
        # 屏幕
        typed = st["typed"]
        line = st["line"]
        code_view(g, self.codes, typed, line, t)
        tot = sum(typed)
        press = None
        if act == "type":
            press = self.typing(g, t, tot, 7.0)
        elif act == "fast":
            press = self.typing(g, t, tot, 14.0, face="wow")
        elif act == "watch":
            if (t % 10) < 4.5:
                dao(g, DAO_X, FLOOR, t, angle=12, hand="point", face="happy")
            else:
                dao(g, DAO_X, FLOOR, t, pose="down")
        elif act == "tea":
            if act_t < 0.5 or act_t > 2.5:
                dao(g, DAO_X, FLOOR, t, angle=-25)
                cup(g, None, t)
            else:
                h = dao(g, DAO_X, FLOOR, t, angle=35, face="happy" if act_t > 1.4 else "sleep")
                cup(g, (h["hand"][0] + 1, h["hand"][1] - 2), t)
        elif act == "slap":
            if act_t < 1.3:
                dao(g, DAO_X, FLOOR, t, angle=-30 if act_t < 0.9 else 30, face="wow")
            else:
                h = dao(g, DAO_X, FLOOR, t, angle=-30, hand="open", face="normal")
                if act_t - 1.3 < dt * 1.2:
                    self.sparks.burst(h["hand"][0], DESK[2] - 3, 14, 34, up=20, life=0.5)
                if act_t < 1.6:
                    pix.shake(g, t, 2.0)
        elif act == "bow":
            dao(g, DAO_X, FLOOR, t, pose="bow")
        elif act == "gong":
            dao(g, DAO_X, FLOOR, t, pose="gong", face="happy")
        elif act == "down":
            dao(g, DAO_X, FLOOR, t, pose="down")
        if act != "tea":
            cup(g, None, t)
        keyboard(g, press)
        return press

    def screen_status(self, g: Gfx, st, t: float, err: str | None = None):
        if err:
            status(g, err, inv=int(t * 4) % 2 == 0)
        elif st["phase"] == "type":
            status(g, "-INSERT-")
        elif st["phase"] == "plot":
            status(g, "PLOT " + "." * (int(t * 3) % 4))
        elif st["phase"] == "build":
            status(g, "BUILD")
            x0, _, x1, _ = SCR
            y = ROWS[2] + 1
            g.d.rectangle((x0 + 2, ROWS[2] - 1, x1 - 2, ROWS[2] + 5), fill=0)
            g.d.rectangle((x0 + 2, y, x1 - 2, y + 3), outline=1)
            g.d.rectangle((x0 + 3, y + 1, x0 + 3 + (x1 - x0 - 6) * st["b"], y + 2), fill=1)
        else:
            status(g, "0 ERR")

    # ------------------------------------------------------------ 入场

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        st = state(0.0, self.CYCLE, self.codes)
        room(g, t)
        on = span(t, 1.6, 2.6)
        monitor(g, on)
        drop = ease_out_bounce(span(t, 0.2, 1.4))
        pix.blit(g, paper_sprite((0, 0, 0, 0, 0)), PAPER[0], PAPER[1] - (1 - drop) * 60)
        plotter_pen(g, None, t, False)
        if t >= 2.6:
            code_view(g, self.codes, [0] * 5, 0, t)
            status(g, "-INSERT-" if t > 3.0 else "VIM FU.C"[:int(span(t, 2.6, 3.0) * 8)])
        if t < 3.4:
            x = lerp(-12, DAO_X, ease_out(span(t, 0.6, 3.2)))
            dao(g, x, FLOOR, t, pose="walk" if t < 3.2 else "down")
            cup(g, None, t)
            keyboard(g)
        elif t < 4.3:
            dao(g, DAO_X, FLOOR, t, pose="gong", face="happy")
            cup(g, None, t)
            keyboard(g)
        else:
            cup(g, None, t)
            press = self.typing(g, t, 0)
            keyboard(g, press)
        if abs(t - 1.4) < dt * 0.6:
            pix.shake(g, t, 1)
        self.fx(g, dt)
        mx_code(g, self.codes, [0] * 5, 0, t)
        if t > 2.6:
            self.counter(g, 0)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < RENEW:
            self.renew(g, t, e, k, dt)
            return
        st = state(k, self.CYCLE, self.codes)
        ph = t % LOOP
        err_on = int(t // LOOP) % 2 == 1 and 23.0 < ph < 27.0
        act = "type" if st["phase"] == "type" else "watch"
        act_t = 0.0
        if 18.0 < ph < 21.0:
            act, act_t = "tea", ph - 18.0
        elif err_on:
            act, act_t = "slap", ph - 23.0
        self.scene(g, t, e, st, dt, act, act_t)
        err = None
        if err_on:
            err = "ERR 1" if ph - 23.0 < 1.3 else "OK"
        self.screen_status(g, st, t, err)
        if st["phase"] == "done":                  # 0 ERR：符纸边缘闪光
            if int(t * 4) % 2 == 0:
                for y in range(PAPER[1], PAPER[1] + PH, 3):
                    g.px(PAPER[0] - 2, y), g.px(PAPER[0] + PW + 1, y + 1)
        self.fx(g, dt)
        mx_code(g, self.codes, st["typed"], st["line"], t, st["b"] if st["phase"] in ("build", "done") else None)
        self.counter(g, e)

    def renew(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """续符：急急如律令 → 符纸下端起火、往上飞走 → 新符纸落下，编辑器清空"""
        full = state(self.CYCLE - 0.01, self.CYCLE, self.codes)
        blank = state(0.0, self.CYCLE, self.codes)
        if k < 3.6:
            burn = 0.55 * span(k, 1.4, 3.6)
            fly = ease_in(span(k, 2.6, 3.6)) * 70
            act = "bow" if 0.6 < k < 1.8 else "gong"
            self.scene(g, t, e, full, dt, act, paper_dy=-fly, burn=burn, flames=k > 1.4)
            status(g, "0 ERR")
            self.fx(g, dt)
            mx_fire(g, t) if k > 1.4 else mx_code(g, self.codes, full["typed"], 4, t, 1.0)
            if 0.4 < k < 0.7:
                pix.shake(g, t, 1.5)
            if k < 0.2:
                self.counter(g, e - k - 1)
            banner(g, 72, 2, "急急如律令", span(k, 0.2, 0.5), t=t)
            return
        drop = ease_out_bounce(span(k, 3.6, 4.6))
        st = dict(blank)
        room(g, t)
        monitor(g)
        pix.blit(g, paper_sprite((0, 0, 0, 0, 0)), PAPER[0], PAPER[1] - (1 - drop) * 60)
        plotter_pen(g, None, t, False)
        code_view(g, self.codes, [0] * 5, 0, t)
        status(g, "-INSERT-")
        if k < 5.0:
            dao(g, DAO_X, FLOOR, t, pose="gong", face="happy")
            keyboard(g)
        else:
            keyboard(g, self.typing(g, t, 0))
        cup(g, None, t)
        if abs(k - 4.6) < dt * 0.6:
            pix.shake(g, t, 1)
        self.fx(g, dt)
        mx_code(g, self.codes, [0] * 5, 0, t)
        self.counter(g, e)

    # ------------------------------------------------------------ 中断 / 恢复

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        st = state(e % self.CYCLE, self.CYCLE, self.codes)
        st = dict(st, phase="type" if st["phase"] == "plot" else st["phase"])
        self.scene(g, t, e, st, dt, "type" if t < 0.8 else "down")
        s = ":WQ"[:int(span(t, 0.05, 0.6) * 3) + (1 if t > 0.05 else 0)]
        status(g, s if t < 0.9 else "SAVED")
        if t > 0.8:                                   # 存盘图标弹出
            k = span(t, 0.8, 1.05)
            fl = pix.stretch(prop("floppy"), 0.4 + 0.6 * k if k < 1 else 1, 0.4 + 0.6 * k if k < 1 else 1)
            cx, cy = (SCR[0] + SCR[2]) // 2, ROWS[1] + 2
            g.d.rectangle((cx - 9, cy - 8, cx + 9, cy + 8), fill=0)
            g.d.rectangle((cx - 9, cy - 8, cx + 9, cy + 8), outline=1)
            pix.blit(g, fl, cx - fl.w // 2, cy - fl.h // 2)
        self.fx(g, dt)
        mx_code(g, self.codes, st["typed"], st["line"], t)
        if t > 0.9:
            g.mx[0, 5:8] = True
        self.counter(g, e)
        if t > 0.9:
            rise(g, 66, 2, "已保存", t - 0.9, life=2.0, size=8, dist=0)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        st = state(e % self.CYCLE, self.CYCLE, self.codes)
        act = "type" if t < 1.2 or st["phase"] == "type" else "watch"
        self.scene(g, t, e, st, dt, act)
        if t < 1.0:
            status(g, "VIM FU.C"[:int(span(t, 0.05, 0.8) * 8)])
        else:
            self.screen_status(g, st, t)
        if 1.0 < t < 1.3:                              # 屏幕刷新：一道亮线从上往下
            y = int(lerp(SCR[1], SCR[3], span(t, 1.0, 1.3)))
            g.d.line((SCR[0], y, SCR[2], y), fill=1)
        self.fx(g, dt)
        mx_code(g, self.codes, st["typed"], st["line"], t)
        self.counter(g, e)

    # ------------------------------------------------------------ 圆满

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k0 = e % self.CYCLE
        kc = lerp(k0, self.CYCLE * 0.999, ease_in_out(span(t, 0.0, 1.5)))
        st = state(kc, self.CYCLE, self.codes)
        if t < 1.5:
            st = dict(st, phase="plot" if st["phase"] == "type" else st["phase"])
            self.scene(g, t, e, st, dt, "fast")
            self.screen_status(g, dict(st, phase="build", b=span(t, 0.6, 1.5)) if t > 0.6 else st, t)
            pix.shake(g, t, 0.5)
            self.fx(g, dt)
            mx_code(g, self.codes, st["typed"], st["line"], t, span(t, 0.6, 1.5))
            self.counter(g, e)
            return
        done = state(self.CYCLE * 0.999, self.CYCLE, self.codes)
        burn = ease_in(span(t, 2.6, 4.6))
        if t < 2.6:
            if int(t * 8) % 2 == 0:
                glow_rays(g, PAPER[0] + PW / 2, PAPER[1] + PH / 2, 14, 18 + 4 * span(t, 1.5, 2.0), 12, t, 1.6,
                          dashed=True)
        self.scene(g, t, e, done, dt, "bow" if 2.0 < t < 3.6 else "gong", burn=burn, flames=2.6 < t < 4.6)
        if 2.6 < t < 4.8 and int(t * 15) % 2 == 0:     # 化灰飘散
            edge = PAPER[1] + PH - burn * PH
            self.puffs.emit(PAPER[0] + 4 + rand(int(t * 15), 3) * 13, edge, vx=2, vy=-10, life=1.4, rmax=1.4)
        status(g, "0 ERR")
        if abs(t - 1.5) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst(PAPER[0] + PW / 2, PAPER[1] + PH / 2, 24, 44, up=10, life=0.9)
        if 1.5 < t < 1.9:
            pix.shake(g, t, 1.8)
        self.fx(g, dt, wind=3)
        if t > 2.6:
            mx_fire(g, t)
            g.mx_level = 2 + int(4 * (1 - span(t, 2.6, 4.6)))
        else:
            mx_code(g, self.codes, done["typed"], 4, t, 1.0)
            g.mx_level = 6 if t < 1.9 else 2
        banner(g, 72, 2, "急急如律令", span(t, 1.8, 2.2), t=t)
