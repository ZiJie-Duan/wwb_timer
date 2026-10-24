"""机臂结印（像素风）：小道士比划手诀，旁边的工业机械臂照着 G 代码一节节弯指头学——剑诀、握固、掌心雷。

依据：道教掐诀（结印）——行法、书符、步罡都要掐诀。
  剑诀：食指、中指并拢伸直，无名指、小指屈向掌心，拇指压住二指（剑指）。
  握固：拇指扣在无名指根，其余四指屈握（《抱朴子》“握固守一”）。
  掌心雷：雷法的掌诀，摊掌发雷。
G 代码梗：G28 回原点（恰好《道德经》第二十八章“复归于无极”），G01 直线插补，G04 停留，M0 暂停，M24 继续，
M30 程序结束；圆满时机械臂收回画外——《道德经》第九章“功遂身退，天之道”。

入场：小道士走到控制柜前按下绿色启动键，屏幕 G28，机械臂从画面下方弹起回原点，五指挨个屈伸自检，
      再伸到工位张开手掌，“咔”一圈方框波纹。
持续：每轮 10 分钟结 15 个诀（剑诀→握固→掌心雷循环，每个约 40 秒）：小道士先比划，机械手先张开、
      再一根根舵机弯指头学着结（屏幕 G01），结成“咔”地方框波纹、震屏、诀名弹出；然后放效果——
      剑诀：剑气月牙一道道往左上飞；握固：点状气环一圈圈收进拳心；掌心雷：掌心发光，上方亮“雷”字，电弧四射。
      其间小道士点头作揖、再比划一遍；隔一个诀舵机抽风（小指乱抖、冒火花、屏显 ERR），小道士拍一下控制柜才好。
      每轮开头 G28 回原点、五指自检，“第几轮”加一。屏幕：行号 N07、指令、底下 15 格进度。
中断：小道士拍下按钮，屏幕 M0，手指半松、整只手臂耷拉下来，“暂停”。
恢复：M24，手臂弹回工位，手指重新一根根结成当前的诀。
圆满：三个诀飞快连结一遍，掌心雷大放电全屏一闪，手张开，M30，机械臂收拢后滑出画外，“功遂身退”。
"""
from __future__ import annotations

import math

from ..engine import pix
from ..engine.anim import ease_in, ease_in_out, ease_out, ease_out_back, lerp, rand, span
from ..engine.chars import Part
from ..engine.fx import lightning, ring
from ..engine.gfx import Gfx, text_width
from ..engine.scene import register
from .r6_common import R6, badge, banner, dao, glow_rays, nth, tiny

FLOOR = 58
DAO_X = 15
CAB = (29, 25)                 # 控制柜左上角
J1 = (110, 45)                 # 机械臂底座转台
L1, L2 = 23, 20
WORK = (82, 39)                # 工位（腕）
HOME = (100, 30)               # 原点
DROOP = (88, 56)
START = 6.0                    # 每轮前 6 秒：G28 回原点
NSEAL = 15
SEAL_T = (600.0 - START) / NSEAL

# 手势：(拇指, 食, 中, 无名, 小)；0 伸直 / 1 半屈 / 2 屈进掌心 / 3 拇指扣在拳里
OPEN = (0, 0, 0, 0, 0)
JIAN = (2, 0, 0, 2, 2)
WOGU = (3, 2, 2, 2, 2)
RELAX = (1, 1, 1, 1, 1)
SEALS = [("剑诀", JIAN), ("握固", WOGU), ("掌心雷", OPEN)]
ORDER = (1, 2, 3, 4, 0)        # 舵机动作顺序：食、中、无名、小、拇指


# ---------------------------------------------------------------- 道具

_HANDS: dict = {}
FING_X = (5, 9, 13, 17)        # 食、中、无名、小（每根 3 像素宽）
FING_L = (9, 10, 9, 7)
HW, HH = 23, 26                # 手的精灵尺寸；腕在底边中点


def hand_sprite(st):
    """机械手 23×26（掌心朝外、手指朝上）：每根手指三节（关节销钉暗点、指尖圆角）；掌心一圈传感器；
    拇指在左；腕部法兰带螺栓。st = (拇指, 食, 中, 无名, 小)"""
    st = tuple(st)
    s = _HANDS.get(st)
    if s is not None:
        return s
    p = Part(HW, HH)
    p.shape("rectangle", (4, 11, 20, 21), fill=1)                # 掌
    p.px(4, 21, 0), p.px(20, 21, 0)
    p.d.line((20, 12, 20, 20), fill=0)                            # 掌侧阴线
    p.d.ellipse((9, 13, 15, 19), outline=0)                       # 掌心传感器
    p.px(12, 16, 0), p.px(12, 15, 1)
    p.shape("rectangle", (7, 22, 17, 25), fill=1)                # 腕部法兰
    p.d.line((7, 23, 17, 23), fill=0)
    for x in (8, 12, 16):
        p.px(x, 25, 0)
    for k, (x, L) in enumerate(zip(FING_X, FING_L)):
        f = st[k + 1]
        if f == 0:                                                # 伸直：三节
            top = 11 - L
            p.shape("rectangle", (x, top, x + 2, 10), fill=1)
            p.px(x, top, 0), p.px(x + 2, top, 0)
            for jy in (top + L // 3, top + 2 * L // 3):
                p.px(x + 1, jy, 0)
            p.px(x + 1, 10, 0)
        elif f == 1:                                              # 半屈：两节立着，指尖朝前勾（短而粗）
            top = 11 - L // 2 - 1
            p.shape("rectangle", (x, top, x + 2, 10), fill=1)
            p.d.line((x, top + 1, x + 2, top + 1), fill=0)
            p.px(x + 1, 10, 0)
        else:                                                     # 屈进掌心：只剩指节，掌上看得见蜷着的指尖
            p.shape("rectangle", (x, 9, x + 2, 10), fill=1)
            p.px(x, 9, 0), p.px(x + 2, 9, 0)
            p.d.line((x, 12, x + 2, 12), fill=0)
            p.d.line((x, 15, x + 2, 15), fill=0)
            p.px(x + 3, 13, 0), p.px(x + 3, 14, 0)
    th = st[0]
    if th == 0:                                                   # 拇指张开（斜向左上）
        p.shape("polygon", [(4, 15), (4, 19), (0, 13), (0, 10), (2, 10)], fill=1)
        p.px(0, 10, 0)
        p.px(2, 14, 0)
    elif th == 1:
        p.shape("rectangle", (1, 13, 4, 18), fill=1)
        p.px(1, 13, 0)
        p.px(2, 16, 0)
    elif th == 2:                                                 # 拇指横压在掌上（压住无名、小指）
        p.d.line((4, 16, 19, 16), fill=0)
        p.d.line((4, 20, 19, 20), fill=0)
        p.shape("rectangle", (1, 17, 19, 19), fill=1)
        p.px(19, 17, 0), p.px(19, 19, 0)
        p.px(10, 18, 0)
    else:                                                         # 扣在拳里，只露一点
        p.shape("rectangle", (2, 14, 4, 18), fill=1)
        p.d.line((4, 14, 4, 18), fill=0)
    s = _HANDS[st] = p.sprite()
    return s


def _cabinet():
    """控制柜 23×33：屏幕框、屏下一排指示灯、绿色启动键、急停蘑菇头、散热格栅、脚轮"""
    p = Part(23, 33)
    p.shape("rectangle", (0, 0, 22, 18), fill=1)                 # 屏幕框
    p.d.rectangle((2, 2, 20, 16), fill=0)
    p.px(0, 0, 0), p.px(22, 0, 0)
    p.shape("rectangle", (1, 19, 21, 30), fill=1)                # 柜体
    p.d.line((1, 19, 21, 19), fill=0)
    p.d.ellipse((3, 21, 7, 25), fill=0)                           # 启动键
    p.d.ellipse((4, 22, 6, 24), fill=1)
    p.d.rectangle((10, 22, 12, 24), fill=0)                       # 小钮
    p.px(11, 23, 1)
    p.d.rectangle((14, 22, 16, 24), fill=0)
    for x in range(4, 19, 2):                                    # 格栅
        p.d.line((x, 27, x, 29), fill=0)
    p.dither([(18, 20), (21, 20), (21, 30), (18, 30)], 0.5, 0)
    p.shape("rectangle", (17, 17, 21, 18), fill=1)               # 急停座
    p.shape("ellipse", (16, 13, 22, 17), fill=1)                 # 急停蘑菇头
    p.d.line((17, 16, 21, 16), fill=0)
    p.px(18, 14, 0)
    for x in (3, 17):                                            # 脚轮
        p.shape("ellipse", (x, 30, x + 3, 32), fill=1)
        p.px(x + 1, 31, 0)
    return p.sprite()


def _pedestal():
    """机械臂底座 22×12：梯形座、警示斜纹、四颗地脚螺栓"""
    p = Part(22, 12)
    p.shape("polygon", [(4, 0), (17, 0), (19, 7), (2, 7)], fill=1)
    for x in range(3, 20, 3):                                    # 黄黑斜纹（1 位：亮暗相间）
        p.d.line((x, 6, x + 3, 2), fill=0)
    p.d.line((3, 1, 18, 1), fill=0)
    p.shape("rectangle", (0, 8, 21, 11), fill=1)
    p.d.line((1, 9, 20, 9), fill=0)
    for x in (2, 7, 14, 19):
        p.px(x, 10, 0)
    return p.sprite()


_PROPS: dict = {}


def prop(name):
    if name not in _PROPS:
        _PROPS[name] = {"cab": _cabinet, "ped": _pedestal}[name]()
    return _PROPS[name]


MX_ICON = {
    OPEN: [0b01010100, 0b01010101, 0b01010101, 0b11010101, 0b01111111, 0b01111111, 0b00111110, 0b00111110],
    JIAN: [0b00010100, 0b00010100, 0b00010100, 0b00010100, 0b01111110, 0b11111110, 0b00111110, 0b00111110],
    WOGU: [0b00000000, 0b00000000, 0b01111110, 0b01010101, 0b01111111, 0b11111110, 0b00111110, 0b00111110],
    RELAX: [0b00000000, 0b00101010, 0b01010101, 0b01010101, 0b01111111, 0b01111110, 0b00111110, 0b00111110],
}


# ---------------------------------------------------------------- 画面

def room(g: Gfx):
    g.d.line((0, FLOOR, 127, FLOOR), fill=1)
    for x in range(-40, 168, 16):
        g.d.line((x, FLOOR + 1, x - 12, 63), fill=1)
    pix.checker(g, (0, FLOOR + 1, 128, 64), 0.125)
    g.d.line((0, FLOOR - 3, 127, FLOOR - 3), fill=1)
    for x in range(56, 128, 8):                                  # 墙上的安全围栏（虚线）
        g.px(x, 30)
    g.d.line((CAB[0] + 22, FLOOR - 1, J1[0] - 10, FLOOR - 1), fill=1)   # 地上的线缆
    g.d.line((CAB[0] + 22, FLOOR - 2, CAB[0] + 24, FLOOR - 2), fill=1)


def cabinet(g: Gfx, l1: str, l2: str, prog: int, t: float, lit: bool = True, cursor: bool = False):
    """控制柜 + 屏幕（两行 G 代码 + 15 格进度）"""
    x, y = CAB
    pix.blit(g, prop("cab"), x, y)
    if not lit:
        return
    tiny(g, x + 4, y + 4, l1)
    w = tiny(g, x + 4, y + 10, l2)
    if cursor and int(t * 3) % 2 == 0:
        g.d.line((x + 5 + w, y + 14, x + 7 + w, y + 14), fill=1)
    for i in range(NSEAL):
        if i < prog or (i == prog and int(t * 2) % 2 == 0):
            g.px(x + 4 + i, y + 16 - 1)
    g.px(x + 15, y + 23, int(t * 2) % 2)                          # 运行灯


def ik(w, j1=J1):
    """两节臂的逆解：返回肘的位置（肘朝上）"""
    dx, dy = w[0] - j1[0], w[1] - j1[1]
    d = max(4.0, min(math.hypot(dx, dy), L1 + L2 - 0.5))
    base = math.atan2(dy, dx)
    a = math.acos(max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d))))
    e1 = (j1[0] + math.cos(base + a) * L1, j1[1] + math.sin(base + a) * L1)
    e2 = (j1[0] + math.cos(base - a) * L1, j1[1] + math.sin(base - a) * L1)
    return e1 if e1[1] < e2[1] else e2


def link(g: Gfx, a, b, w: int):
    """一节臂：黑边 → 白身 → 中间一道暗槽，两头铆钉"""
    g.d.line((a, b), fill=0, width=w + 2)
    g.d.line((a, b), fill=1, width=w)
    k = 0.2
    g.d.line((lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[0], b[0], 1 - k), lerp(a[1], b[1], 1 - k)), fill=0)


def joint(g: Gfx, c, r: int, motor: float | None = None):
    """关节：舵机圆盘（暗圈 + 中心点）；motor 给角度时多画一个侧挂的电机壳"""
    x, y = c
    if motor is not None:
        mx_, my_ = x + math.cos(motor) * (r + 2), y + math.sin(motor) * (r + 2)
        g.d.rectangle((mx_ - 3, my_ - 3, mx_ + 3, my_ + 3), fill=0)
        g.d.rectangle((mx_ - 2, my_ - 2, mx_ + 2, my_ + 2), fill=1)
        g.px(mx_, my_, 0)
    g.d.ellipse((x - r - 1, y - r - 1, x + r + 1, y + r + 1), fill=0)
    g.d.ellipse((x - r, y - r, x + r, y + r), fill=1)
    g.d.ellipse((x - r + 2, y - r + 2, x + r - 2, y + r - 2), outline=0)
    g.px(x, y, 1)


def robot(g: Gfx, w, st, slide: float = 0.0, rise: float = 0.0, jitter: float = 0.0, t: float = 0.0):
    """整台机械臂：底座 → 转台 → 大臂 → 肘（电机）→ 小臂 → 腕 → 手。slide 往右滑出，rise 从下面升起的偏移"""
    ox, oy = slide, rise
    j1 = (J1[0] + ox, J1[1] + oy)
    wx, wy = w[0] + ox, w[1] + oy
    if jitter:
        wx += math.sin(t * 60) * jitter
    el = ik((wx, wy), j1)
    pix.blit(g, prop("ped"), j1[0] - 11, j1[1] + 2)
    # 线缆：沿两节臂外侧，略垂
    pts = []
    for (a, b) in ((j1, el), (el, (wx, wy))):
        for i in range(6):
            k = i / 5
            nx, ny = -(b[1] - a[1]), (b[0] - a[0])
            ln = math.hypot(nx, ny) or 1
            pts.append((lerp(a[0], b[0], k) + nx / ln * 4, lerp(a[1], b[1], k) + ny / ln * 4 + math.sin(k * math.pi) * 1.5))
    link(g, j1, el, 6)
    link(g, el, (wx, wy), 5)
    g.d.line(pts, fill=1)
    joint(g, j1, 6, motor=math.pi * 0.95)
    joint(g, el, 5, motor=-math.pi * 0.25)
    joint(g, (wx, wy + 1), 4)
    spr = hand_sprite(st)
    hx, hy = wx - HW // 2, wy - HH + 1
    pix.blit(g, spr, hx, hy)
    return hx, hy


def blend(a, b, p: float):
    """手势 a → b：按 ORDER 一根根换（每根先半屈再到位）"""
    out = list(a)
    n = len(ORDER)
    for j, f in enumerate(ORDER):
        q = p * n - j
        if a[f] == b[f] or q <= 0:
            continue
        out[f] = b[f] if q >= 1 else 1
    return tuple(out)


def selftest(p: float):
    """自检：五指依次屈伸一遍（一道波）"""
    out = [0] * 5
    for j, f in enumerate(ORDER):
        q = p * 6 - j
        if 0 < q < 1:
            out[f] = 2 if 0.3 < q < 0.7 else 1
            if f == 0 and out[f] == 2:
                out[f] = 3
    return tuple(out)


def ripple(g: Gfx, cx: float, cy: float, k: float):
    """结成时“咔”的方框波纹"""
    if not 0 < k < 1:
        return
    r = 8 + k * 18
    for rr in (r, r - 4):
        if rr > 6:
            g.d.rectangle((cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8), outline=1)
    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        g.d.line((cx + dx * (r + 2), cy + dy * (r * 0.8 + 2), cx + dx * (r + 5), cy + dy * (r * 0.8 + 4)), fill=1)


def crescent(g: Gfx, x: float, y: float, s: float = 1.0):
    """剑气月牙（开口朝右下，往左上飞）+ 尾迹"""
    r = 6 * s
    g.d.chord((x - r, y - r, x + r, y + r), 110, 290, fill=0)
    g.d.arc((x - r, y - r, x + r, y + r), 120, 280, fill=1, width=2)
    g.d.arc((x - r + 2, y - r + 1, x + r + 2, y + r + 1), 140, 260, fill=0)
    for i in range(3):
        g.px(x + 6 + i * 3, y + 3 + i * 2)


def name_text(g: Gfx, s: str, k: float):
    """诀名（左上，计数牌下面）：带黑底，弹出"""
    if k <= 0:
        return
    y = 14 + (1 - ease_out_back(min(k, 1))) * 4
    w = text_width(s)
    g.d.rectangle((2, y - 2, 4 + w + 2, y + 12), fill=0)
    g.text(4, y, s)


@register
class GCode(R6):
    id = "r6.gcode"
    name = "机臂结印"
    desc = "小道士比划手诀，旁边的工业机械臂照着 G 代码一节节弯指头学：剑诀放剑气、握固收气环、掌心雷电弧四射"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 2.0, "complete": 5.5}
    CYCLE = 600.0

    def init(self):
        self.last_k = None

    # ------------------------------------------------------------ 进度

    def seal_at(self, k: float):
        """k（本轮秒数）→ (第几个诀 s, 诀内秒数 u)；k < START 时 s = -1"""
        if k < START:
            return -1, k
        s = min(int((k - START) // SEAL_T), NSEAL - 1)
        return s, k - START - s * SEAL_T

    def pose_at(self, s: int, u: float, glitch: bool = True):
        """机械手在第 s 个诀、u 秒时的手势"""
        if s < 0:
            return OPEN
        prev = SEALS[(s - 1) % 3][1] if s > 0 else OPEN
        cur = SEALS[s % 3][1]
        if u < 1.8:
            return blend(prev, OPEN, u / 1.8)
        if u < 5.0:
            return blend(OPEN, cur, (u - 1.8) / 3.2)
        if glitch and s % 2 == 1 and 27.0 < u < 29.6:             # 舵机抽风：一根手指乱抖
            st = list(cur)
            st[4] = 1 if int(u * 12) % 2 else (0 if cur[4] else 2)      # 小指乱抖
            return tuple(st)
        return cur

    def dao_demo(self, g: Gfx, kind: int, t: float, face: str = "normal"):
        """小道士比划手诀：剑诀 = 剑指，握固 = 握拳前举，掌心雷 = 摊掌前推"""
        if kind == 0:
            return dao(g, DAO_X, FLOOR, t, pose="point", face=face)
        if kind == 1:
            return dao(g, DAO_X, FLOOR, t, angle=15, hand="fist", face=face)
        return dao(g, DAO_X, FLOOR, t, angle=20, hand="open", face=face)

    def effect(self, g: Gfx, kind: int, u: float, t: float, hx: float, hy: float, power: float = 1.0):
        """结成后的效果（u 从结成起算）"""
        cx, cy = hx + 12, hy + 16
        if kind == 0:                     # 剑气月牙往左上飞
            for j in range(3):
                q = ((u * 0.7) + j / 3) % 1
                if u * 0.7 + j / 3 < 1 and q < 0.05:
                    continue
                x = lerp(hx + 8, hx - 40, ease_in(q))
                y = lerp(hy - 2, hy - 28, ease_in(q))
                if y > -8:
                    crescent(g, x, y, 0.8 + q * 0.5)
            g.px(hx + 10, hy - 1), g.px(hx + 11, hy - 3)
        elif kind == 1:                   # 点状气环收进拳心
            for j in range(2):
                q = ((u * 0.8) + j / 2) % 1
                ring(g, cx, cy - 2, 22 * (1 - q) + 3, density=2, phase=q * 3)
            if (u * 0.8) % 0.5 < 0.08:
                g.d.rectangle((cx - 1, cy - 3, cx + 1, cy - 1), fill=1)
        else:                             # 掌心雷
            g.d.ellipse((cx - 1, cy - 1, cx + 1, cy + 1), fill=1)
            if int(t * 8) % 2:
                g.d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), outline=1)
                g.d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), outline=0)
            step = int(t * 15)
            for j in range(int(2 + 2 * power)):
                a = rand(step * 5 + j, 3) * math.pi * 1.2 - 0.1   # 往两侧和下方
                ln = (10 + 10 * rand(step * 3 + j, 4)) * power
                lightning(g, cx, cy, cx + math.cos(a) * ln * (1 if j % 2 else -1), cy + abs(math.sin(a)) * ln * 0.7,
                          seed=step * 9 + j, jag=2.5, branches=1)

    def lei_text(self, g: Gfx, hx: float, hy: float, k: float):
        """掌心雷：手上方亮一个“雷”字（黑底虚框）"""
        if k <= 0:
            return
        cx = hx + 11
        y = hy - 14 + (1 - ease_out_back(min(k, 1))) * 3
        g.d.rectangle((cx - 9, y - 3, cx + 9, y + 13), fill=0)
        pix.dotted(g, cx - 9, y - 3, cx + 9, y - 3, 2)
        pix.dotted(g, cx - 9, y + 13, cx + 9, y + 13, 2)
        g.text(cx, y, "雷", align="center")

    def counter(self, g: Gfx, e: float, label: str | None = None):
        badge(g, label or nth(int(e // self.CYCLE) + 1, "轮"))

    def mx(self, g: Gfx, st, t: float, palm: bool = False, bright: bool = False):
        rows = MX_ICON.get(st)
        if rows is None:
            straight = sum(1 for f in st[1:] if f == 0)
            rows = MX_ICON[RELAX] if st.count(1) >= 3 else MX_ICON[OPEN if straight >= 3 else JIAN if st[1] == 0 else WOGU]
        g.mx_rows(rows)
        if palm:
            g.mx[5, 3] = g.mx[5, 4] = int(t * 8) % 2 == 0
        if bright:
            g.mx_level = 6

    # ------------------------------------------------------------ 入场：按启动键，机械臂弹起，自检

    def enter(self, g: Gfx, t: float):
        dt = self._dt(t)
        room(g)
        booted = t >= 1.8
        cabinet(g, "G28" if booted else "", "HOME" if booted and t < 4.2 else ("OK" if t >= 4.6 else ""), 0, t,
                lit=booted, cursor=booted and t < 4.6)
        rise = 40 * (1 - ease_out_back(span(t, 1.8, 2.8)))
        if t < 4.2:
            w, st = HOME, selftest(span(t, 2.8, 4.2))
        else:
            w = (lerp(HOME[0], WORK[0], ease_in_out(span(t, 4.2, 4.6))), lerp(HOME[1], WORK[1], ease_in_out(span(t, 4.2, 4.6))))
            st = OPEN
        if t >= 1.8:
            hx, hy = robot(g, w, st, rise=rise, t=t)
            if abs(t - 2.5) < dt * 0.6:
                self.sparks.burst(J1[0], J1[1] - 2, 10, 24, up=12, life=0.5)
            if 2.4 < t < 2.6:
                pix.shake(g, t, 1)
            ripple(g, hx + 12, hy + 13, span(t, 4.6, 5.0))
            if abs(t - 4.6) < dt * 0.6:
                pix.shake(g, t, 1)
        if t < 1.4:
            dao(g, lerp(-12, DAO_X, ease_out(span(t, 0, 1.4))), FLOOR, t, pose="walk")
        elif t < 2.0:
            dao(g, DAO_X, FLOOR, t, angle=-5, hand="point")
            if abs(t - 1.8) < dt * 0.6:
                self.sparks.burst(CAB[0] + 5, CAB[1] + 23, 6, 14, up=6, life=0.3)
        elif t < 4.6:
            dao(g, DAO_X, FLOOR, t, face="wow" if t < 3.0 else "normal")
        else:
            dao(g, DAO_X, FLOOR, t, face="happy")
        self.fx(g, dt)
        self.mx(g, st if t >= 1.8 else RELAX, t, bright=4.6 <= t < 4.9)
        if t < 1.8:
            g.mx_rows([0, 0, 0, 0b00011000, 0b00011000, 0, 0, 0] if int(t * 3) % 2 else [0] * 8)
        if t >= 4.6:
            self.counter(g, 0)

    # ------------------------------------------------------------ 持续

    def hold(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        k = e % self.CYCLE
        if e >= self.CYCLE and k < START:
            self.renew(g, t, e, k, dt)
            self.last_k = k
            return
        room(g)
        s, u = self.seal_at(k)
        kind = s % 3 if s >= 0 else -1
        st = self.pose_at(s, u)
        moving = s >= 0 and u < 5.0
        locked = s >= 0 and u >= 5.0
        glitch = s % 2 == 1 and 27.0 < u < 29.6
        if s < 0:
            l2 = "OK"
        elif moving:
            l2 = "G01"
        elif glitch:
            l2 = "ERR"
        elif u < 7.0:
            l2 = "OK"
        else:
            l2 = "G04"
        cabinet(g, f"N{s + 1:02d}" if s >= 0 else "G28", l2, max(s, 0), t, cursor=moving)
        wob = math.sin(t * 1.3) * 1.0 if locked else 0.0
        hx, hy = robot(g, (WORK[0], WORK[1] + wob), st, jitter=0.6 if moving and int(t * 6) % 2 else 0, t=t)
        if locked and u < 36.0 and not glitch:
            self.effect(g, kind, u - 5.0, t, hx, hy)
        if s >= 0:
            ripple(g, hx + 12, hy + 13, span(u, 5.0, 5.4))
        # 结成的一瞬
        if s >= 0 and self.last_k is not None and self.last_k < k - u + 5.0 <= k:
            self.sparks.burst(hx + 12, hy + 8, 10, 26, up=12, life=0.5)
            for c in (J1, ik((WORK[0], WORK[1] + wob))):
                self.sparks.burst(c[0], c[1], 3, 12, up=6, life=0.3)
        if glitch and int(u * 4) % 2 == 0 and int(u * 30) % 4 == 0:
            self.sparks.burst(hx + 18, hy + 6, 2, 16, up=8, life=0.3)
        self.last_k = k
        # 小道士
        if s >= 0 and u < 5.6:
            self.dao_demo(g, kind, t, face="happy" if u > 5.0 else "normal")
        elif glitch and u < 28.4:
            dao(g, DAO_X, FLOOR, t, face="wow")
        elif glitch:
            dao(g, DAO_X, FLOOR, t, angle=-5, hand="open")
            if abs(u - 28.6) < dt * 0.6:
                self.sparks.burst(CAB[0] + 4, CAB[1] + 22, 5, 14, up=6, life=0.3)
                pix.shake(g, t, 1)
        elif s >= 0 and 18.0 < u < 20.6:
            dao(g, DAO_X, FLOOR, t, pose="gong" if u < 18.8 else "bow")
        elif s >= 0 and 11.0 < u < 13.0:                             # 跟着再比划一下
            self.dao_demo(g, kind, t)
        else:
            dao(g, DAO_X, FLOOR, t)
        self.fx(g, dt)
        if s >= 0 and 5.0 <= u < 5.2:
            pix.shake(g, t, 1.2)
        self.mx(g, st, t, palm=locked and kind == 2, bright=s >= 0 and 5.0 <= u < 5.4)
        self.counter(g, e)
        if s >= 0 and 5.0 <= u < 11.0:
            name_text(g, SEALS[kind][0], span(u, 5.0, 5.3))
        elif locked and kind == 2 and u < 36.0:
            self.lei_text(g, hx, hy, span(u, 11.0, 11.3))

    def renew(self, g: Gfx, t: float, e: float, k: float, dt: float):
        """每轮开头：G28 回原点 → 五指自检 → 回工位"""
        room(g)
        last = SEALS[(NSEAL - 1) % 3][1]
        if k < 1.2:
            q = ease_in_out(span(k, 0, 1.2))
            w = (lerp(WORK[0], HOME[0], q), lerp(WORK[1], HOME[1], q))
            st = blend(last, OPEN, span(k, 0, 1.0))
        elif k < 3.6:
            w, st = HOME, selftest(span(k, 1.2, 3.6))
        else:
            q = ease_in_out(span(k, 3.6, 4.6))
            w = (lerp(HOME[0], WORK[0], q), lerp(HOME[1], WORK[1], q))
            st = OPEN
        cabinet(g, "G28", "HOME" if k < 4.6 else "OK", 0 if k > 1.2 else NSEAL, t, cursor=k < 4.6)
        hx, hy = robot(g, w, st, t=t)
        ripple(g, hx + 12, hy + 13, span(k, 4.6, 5.0))
        if abs(k - 4.6) < dt * 0.6:
            self.sparks.burst(hx + 12, hy + 8, 8, 22, up=10, life=0.5)
        if 4.6 < k < 4.8:
            pix.shake(g, t, 1)
        if 1.0 < k < 3.2:
            dao(g, DAO_X, FLOOR, t, pose="gong" if k < 1.8 else "bow")
        else:
            dao(g, DAO_X, FLOOR, t, face="happy" if k > 4.6 else "normal")
        self.fx(g, dt)
        self.mx(g, st, t, bright=4.6 < k < 4.9)
        self.counter(g, e if k > 1.2 else e - k - 1)

    # ------------------------------------------------------------ 中断 / 恢复

    def interrupt(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        room(g)
        k = e % self.CYCLE
        s, u = self.seal_at(k)
        cur = self.pose_at(s, u, glitch=False)
        st = blend(cur, RELAX, span(t, 0.3, 0.9))
        q = ease_out_back(span(t, 0.4, 1.2), 2.5)
        w = (lerp(WORK[0], DROOP[0], q), lerp(WORK[1], DROOP[1], q))
        cabinet(g, f"N{max(s, 0) + 1:02d}", "M0" if t > 0.3 else "G04", max(s, 0), t)
        robot(g, w, st, t=t)
        if abs(t - 1.0) < dt * 0.6:
            self.puffs.emit(w[0], w[1] + 2, vy=-4, life=0.8, rmax=2, spread=4)
        if t < 0.5:
            dao(g, DAO_X, FLOOR, t, angle=-5, hand="open")
            if abs(t - 0.3) < dt * 0.6:
                self.sparks.burst(CAB[0] + 4, CAB[1] + 22, 5, 14, up=6, life=0.3)
        else:
            dao(g, DAO_X, FLOOR, t, pose="gong" if t > 1.0 else "down")
        self.fx(g, dt)
        self.mx(g, st, t)
        self.counter(g, e, "暂停" if t > 0.3 else None)

    def resume(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        room(g)
        k = e % self.CYCLE
        s, u = self.seal_at(k)
        cur = self.pose_at(s, u, glitch=False)
        q = ease_out_back(span(t, 0.3, 1.0))
        w = (lerp(DROOP[0], WORK[0], q), lerp(DROOP[1], WORK[1], q))
        st = RELAX if t < 1.0 else blend(RELAX, cur, span(t, 1.0, 1.7))
        cabinet(g, f"N{max(s, 0) + 1:02d}", "M24" if t < 1.7 else "OK", max(s, 0), t, cursor=t < 1.7)
        hx, hy = robot(g, w, st, t=t)
        ripple(g, hx + 12, hy + 13, span(t, 1.7, 2.0))
        if abs(t - 1.7) < dt * 0.6:
            self.sparks.burst(hx + 12, hy + 8, 8, 22, up=10, life=0.4)
        if 1.7 < t < 1.85:
            pix.shake(g, t, 1)
        if t < 0.4:
            dao(g, DAO_X, FLOOR, t, angle=-5, hand="open")
            if abs(t - 0.2) < dt * 0.6:
                self.sparks.burst(CAB[0] + 4, CAB[1] + 22, 5, 14, up=6, life=0.3)
        elif s >= 0 and t > 1.0:
            self.dao_demo(g, s % 3, t)
        else:
            dao(g, DAO_X, FLOOR, t)
        self.fx(g, dt)
        self.mx(g, st, t, bright=1.7 < t < 1.9)
        self.counter(g, e, "暂停" if t < 0.3 else None)

    # ------------------------------------------------------------ 圆满：三诀连结，掌心雷，功遂身退

    def complete(self, g: Gfx, t: float, e: float):
        dt = self._dt(t)
        room(g)
        seq = [OPEN, JIAN, WOGU, OPEN]
        if t < 1.8:
            j = min(int(t / 0.6), 2)
            q = (t - j * 0.6) / 0.6
            st = blend(seq[j], seq[j + 1], span(q, 0, 0.6))
            kind = j
        else:
            st = OPEN
            kind = 2
        slide = 70 * ease_in(span(t, 3.6, 4.8))
        if t < 3.0:
            w = WORK
        else:
            qq = ease_in_out(span(t, 3.0, 3.6))
            w = (lerp(WORK[0], HOME[0], qq), lerp(WORK[1], HOME[1] + 6, qq))
        l2 = "G01" if t < 1.8 else ("G04" if t < 2.6 else "M30")
        cabinet(g, "N99", l2, NSEAL, t, cursor=t < 2.6)
        hx, hy = robot(g, w, st, slide=slide, jitter=0.8 if 1.8 < t < 2.6 else 0, t=t)
        if t < 1.8:
            ripple(g, hx + 12, hy + 13, ((t % 0.6) - 0.36) / 0.24)
            self.effect(g, kind, (t % 0.6) * 2, t, hx, hy)
        elif t < 2.6:
            self.effect(g, 2, t, t, hx, hy, power=2.2)
            glow_rays(g, hx + 12, hy + 16, 6, 6 + 10 * span(t, 1.8, 2.2), 12, t, 1.0, dashed=True)
        if abs(t - 2.2) < dt * 0.6:
            pix.flash(g)
            self.sparks.burst(hx + 12, hy + 16, 30, 50, up=16, life=1.0, gravity=50)
        if 2.2 < t < 2.6:
            pix.shake(g, t, 2)
        if t < 1.8:
            self.dao_demo(g, min(int(t / 0.6), 2), t)
        elif t < 2.6:
            self.dao_demo(g, 2, t, face="wow")
        elif t < 4.2:
            dao(g, DAO_X, FLOOR, t, pose="gong" if t < 3.0 else "bow")
        else:
            dao(g, DAO_X, FLOOR, t, face="happy")
        self.fx(g, dt)
        self.mx(g, st if t < 3.6 else OPEN, t, palm=1.8 < t < 2.6, bright=1.8 < t < 2.6)
        if 2.2 <= t < 2.4:
            g.mx[:] = True
            g.mx_level = 8
        if t > 4.8:
            g.mx_rows([0, 0b00100100, 0b00100100, 0, 0b01000010, 0b00111100, 0, 0])   # 笑脸：功成
        if t < 2.0:
            self.counter(g, e)
        banner(g, 64, 6, "功遂身退", span(t, 3.0, 3.4), t=t)
