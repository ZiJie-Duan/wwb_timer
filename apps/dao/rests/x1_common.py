"""x1（睡与梦）共用：躺着的小道士（仰卧、侧卧支颐）、Z、梦泡、圆形收拢、定时事件、文字小工具。

只给 x1_*.py 用（不登记场景）。全是清晰的 1 位像素画：部件用 Part 逐像素造型，模块级缓存。
所有 hold 只依赖 t（无逐帧状态），任何时刻都能直接画；exit 读 self.hold_t 从最后一帧接着演。

    supine(g, x, y, t, face, knee, arm)   仰卧：头在左（发髻朝左、脸朝上），身体向右；(x, y) = 后脑着地点
    recline(g, x, y, t, face)             侧卧支颐（陈抟“蛰龙睡”）：肘撑地，头靠在手上，身体向右、屈膝
    zzz(g, x, y, t)                       冒 Z（三个由小到大的像素 Z 往右上飘）
    iris(g, cx, cy, r)                    圆形收拢（外面涂黑，边上一圈亮线）
    ev(t, period, start, dur)             周期小事件：返回事件内的时间或 None
    plate(g, x, y, s)                     带边框底板的字（先清底，最后画）
"""
from __future__ import annotations

import math

import numpy as np

from ..engine import pix
from ..engine.anim import clamp, ease_out_back, span
from ..engine.chars import Part, _head, arm_sprite
from ..engine.gfx import H, W, Gfx, Sprite, text_width

_C: dict = {}
HB = 10


def cached(key, fn):
    v = _C.get(key)
    if v is None:
        v = _C[key] = fn()
    return v


# ---------------------------------------------------------------- 仰面的头（侧面像：发髻朝左、脸朝上）

def _head_up(face: str = "sleep") -> Sprite:
    """仰面的头 19×15（侧脸像）：发髻朝左（簪竖穿），头发盖住头顶和枕地的后脑，脸朝上、下巴朝右；
    一只耳朵、一只眼、鼻尖小凸起、腮红网点。face：sleep 合眼 / snore 合眼张嘴 / open 睁眼 / wow 瞪眼张嘴 / happy 笑眼"""
    p = Part(19, 15)
    p.shape("ellipse", (0, 4, 6, 10), fill=0)            # 发髻（在后面）
    p.d.ellipse((0, 4, 6, 10), outline=1)
    p.px(1, 6, 1), p.px(1, 7, 1), p.px(2, 5, 1)          # 发髻高光
    cx, cy, r = 11.0, 7.0, 7.4
    for y in range(15):
        for x in range(3, 19):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                hb = HB if y <= 9 else HB + (y - 9) * 1.5  # 发际线：竖直往下，到后颈斜向右下
                p.px(x, y, 1 if (d > r - 1.0 or x >= hb) else 0)
    for x, y in ((13, 1), (14, 1), (13, 2), (14, 2), (13, 3), (13, 7), (13, 8)):  # 刘海（发际线锯齿）
        p.px(x, y, 0)
    p.px(6, 3, 1), p.px(5, 4, 1), p.px(5, 5, 1)          # 发丝高光
    p.px(8, 11, 1), p.px(9, 12, 1)
    for y in (2, 3, 11, 12):                             # 簪
        p.px(2, y, 1)
    p.px(12, 9, 1), p.px(12, 10, 1), p.px(11, 10, 1)        # 耳朵
    ex, ey = 15, 4
    if face in ("sleep", "snore"):
        p.px(ex - 1, ey, 0), p.px(ex, ey + 1, 0), p.px(ex + 1, ey + 1, 0), p.px(ex + 2, ey, 0)
        p.px(ex - 1, ey - 1, 0)
    elif face == "happy":
        p.px(ex - 1, ey + 1, 0), p.px(ex, ey, 0), p.px(ex + 1, ey, 0), p.px(ex + 2, ey + 1, 0)
    else:
        p.d.rectangle((ex, ey - 1, ex + 1, ey + 1), fill=0)
        p.px(ex + 1, ey - 1, 1)
        if face == "wow":
            p.d.rectangle((ex - 1, ey - 1, ex + 2, ey + 2), fill=0)
            p.px(ex, ey - 1, 1)
    p.px(15, 7, 0), p.px(17, 7, 0)                       # 腮红
    p.px(18, 4, 1)                                       # 鼻尖
    if face in ("snore", "wow"):                         # 张嘴
        p.d.rectangle((16, 9, 17, 11), fill=0)
    else:
        p.d.line((16, 10, 17, 10), fill=0)
    return p.sprite()


def head_up(face: str = "sleep") -> Sprite:
    return cached(("head_up", face), lambda: _head_up(face))


# ---------------------------------------------------------------- 拼装：部件之间自动描 1 像素黑边

class Canvas:
    """把几个部件（Part / Sprite）拼成一个精灵；后贴的部件外围描 1 像素黑边，把前面的切开"""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.on = np.zeros((h, w), bool)
        self.mask = np.zeros((h, w), bool)

    def add(self, spr, x: int, y: int, outline: bool = True):
        if isinstance(spr, Part):
            spr = spr.sprite()
        m = np.zeros((self.h + 2, self.w + 2), bool)
        on = np.zeros_like(m)
        ys, xs = slice(max(0, y), min(self.h, y + spr.h)), slice(max(0, x), min(self.w, x + spr.w))
        sy, sx = slice(ys.start - y, ys.stop - y), slice(xs.start - x, xs.stop - x)
        m[ys.start + 1:ys.stop + 1, xs.start + 1:xs.stop + 1] = spr.mask[sy, sx]
        on[ys.start + 1:ys.stop + 1, xs.start + 1:xs.stop + 1] = spr.on[sy, sx]
        if outline:
            gr = m.copy()
            gr[1:, :] |= m[:-1, :]
            gr[:-1, :] |= m[1:, :]
            gr[:, 1:] |= m[:, :-1]
            gr[:, :-1] |= m[:, 1:]
            ring = (gr & ~m)[1:-1, 1:-1] & self.mask
            self.on[ring] = False
        m, on = m[1:-1, 1:-1], on[1:-1, 1:-1]
        self.mask |= m
        self.on[m] = on[m]
        return self

    def sprite(self) -> Sprite:
        return Sprite(on=self.on.copy(), mask=self.mask.copy())


# ---------------------------------------------------------------- 仰卧

def _sup_torso(breath: bool) -> Part:
    """仰卧的上身 17×10：胸口隆起（吸气时高 1 像素）、交领、腰带与结、贴地一侧网点"""
    p = Part(17, 10)
    b = 1 if breath else 0
    p.shape("polygon", [(0, 4), (3, 1 - b), (12, 1 - b), (15, 3), (16, 5), (16, 9), (0, 9)], fill=1)
    p.d.line((2, 2 - b, 5, 6), fill=0)                # 交领
    p.d.line((5, 6, 3, 9), fill=0)
    p.d.line((13, 2, 13, 9), fill=0)                  # 腰带
    p.px(14, 5, 0), p.px(14, 6, 0), p.px(13, 5, 1)    # 结
    p.d.line((1, 9, 12, 9), fill=0)                   # 贴地一侧的阴线
    return p


def _sup_legs(knee: bool) -> Part:
    """仰卧的下身 18×14：平放时袍摆到脚、鞋尖朝天；knee=True 时一膝立起，袍子撑成个小帐篷"""
    p = Part(18, 14)
    if knee:
        p.shape("polygon", [(0, 8), (6, 1), (9, 1), (14, 12), (14, 13), (0, 13)], fill=1)
        p.d.line((7, 2, 4, 13), fill=0)               # 膝头往下的褶
        p.d.line((9, 3, 9, 4), fill=0)
        p.dither([(8, 2), (14, 12), (14, 13), (9, 13), (9, 4)], 0.5, 0)
        p.shape("ellipse", (12, 10, 17, 13), fill=1)  # 立着那条腿的鞋（踩地）
        p.d.line((13, 13, 16, 13), fill=0)
        p.px(16, 11, 0)
    else:
        p.shape("polygon", [(0, 5), (8, 6), (13, 7), (13, 13), (0, 13)], fill=1)
        p.d.line((11, 7, 11, 13), fill=0)             # 下摆镶边
        p.d.line((3, 10, 9, 10), fill=0)              # 两腿之间的褶
        p.shape("ellipse", (12, 3, 16, 10), fill=1)   # 鞋尖朝天
        p.d.line((13, 9, 15, 9), fill=0)
        p.px(14, 5, 0)
    return p


def _sup_foot2() -> Part:
    """屈膝时另一条平放的腿伸出来的鞋 5×7（鞋尖朝天）"""
    p = Part(5, 7)
    p.shape("ellipse", (0, 0, 4, 6), fill=1)
    p.d.line((1, 5, 3, 5), fill=0)
    p.px(3, 2, 0)
    return p


def _sup_arm() -> Part:
    """搭在肚子上的手臂 15×9：小臂平放、宽袖往地上垂，袖口镶边，露出手"""
    p = Part(15, 9)
    p.shape("polygon", [(0, 1), (3, 0), (10, 0), (11, 1), (11, 4), (9, 8), (4, 8), (2, 5), (0, 4)], fill=1)
    p.d.line((10, 1, 10, 4), fill=0)                  # 袖口
    p.d.line((10, 4, 8, 8), fill=0)
    p.dither([(5, 5), (10, 4), (8, 8), (5, 8)], 0.5, 0)
    p.shape("rectangle", (11, 1, 13, 3), fill=1)      # 手
    p.px(13, 1, 0), p.px(12, 3, 0)
    return p


def _supine(face: str, breath: bool, knee: bool, arm: str) -> Sprite:
    c = Canvas(48, 16)
    c.add(_sup_legs(knee), 28, 2)
    if knee:
        c.add(_sup_foot2(), 42, 8)
    c.add(_sup_torso(breath), 14, 6)
    if arm == "belly":
        c.add(_sup_arm(), 18, 4 - (1 if breath else 0))
    c.add(head_up(face), 0, 1)
    return c.sprite()


def supine(g: Gfx, x: float, y: float, t: float = 0.0, face: str = "sleep", knee: bool = False,
           arm: str = "belly", breath: bool | None = None, flip: bool = False) -> dict:
    """仰卧的小道士。(x, y) = 后脑着地处（头左端、地面 y）。长约 48、高 16（不算举起的手）。
    arm：belly 搭在肚子上 / raise 一只手指天 / none 不画（自己画，比如垂进水里）
    返回 {"mouth", "eye", "hand", "knee", "toe", "chest", "nose"}（屏幕坐标）"""
    x, y = int(round(x)), int(round(y))
    if breath is None:
        breath = (t / 3.6) % 1 < 0.5
    spr = cached(("sup", face, breath, knee, arm), lambda: _supine(face, breath, knee, arm))
    pix.blit(g, spr, x if not flip else x - spr.w, y - 16, flip=flip)

    def P(dx, dy):
        return (x + dx, y + dy) if not flip else (x - dx, y + dy)

    out = {"mouth": P(17, -7), "nose": P(18, -12), "eye": P(14, -13), "chest": P(22, -11 - breath),
           "knee": P(35, -15 if knee else -10), "toe": P(44, -9 if not knee else -7), "hand": P(31, -10)}
    if arm == "raise":
        spr = arm_sprite("raise")
        ax, ay = 19, -10 - spr.h + 1
        pix.blit(g, spr, x + ax if not flip else x - ax - spr.w, y + ay, flip=flip)
        out["hand"] = P(ax + spr.hand[0], ay + spr.hand[1])
    return out


# ---------------------------------------------------------------- 侧卧支颐（陈抟蛰龙睡）

def _rec_body(breath: bool) -> Part:
    """侧卧的身子 38×12：肩低、胯最高、腿往右收细，脚在右；腰带、下摆镶边、贴地一道阴线"""
    p = Part(38, 12)
    b = 1 if breath else 0
    p.shape("polygon", [(0, 1), (4, 1 - b), (13, 2 - b), (19, 0 - b), (24, 0), (29, 3), (34, 5), (34, 11), (0, 11)],
            fill=1)
    p.d.line((14, 2 - b, 14, 11), fill=0)              # 腰带
    p.px(15, 4, 0), p.px(15, 5, 0), p.px(14, 4, 1)
    p.d.line((31, 4, 31, 11), fill=0)                  # 下摆镶边
    p.d.line((21, 7, 29, 7), fill=0)                   # 两腿之间的褶
    p.d.line((1, 11, 30, 11), fill=0)                  # 贴地的阴线
    p.dither([(22, 8), (30, 8), (30, 10), (22, 10)], 0.5, 0)
    p.shape("ellipse", (31, 5, 37, 11), fill=1)        # 鞋
    p.d.line((32, 10, 36, 10), fill=0)
    p.px(36, 7, 0)
    return p


def _rec_arm() -> Part:
    """搭在身上的那只手 19×7：宽袖从肩顺到胯，袖口垂向地面，手搭在胯上"""
    p = Part(19, 7)
    p.shape("polygon", [(0, 2), (4, 0), (13, 0), (15, 1), (15, 4), (12, 6), (5, 6), (1, 4)], fill=1)
    p.d.line((14, 1, 14, 4), fill=0)                   # 袖口
    p.d.line((14, 4, 12, 6), fill=0)
    p.shape("rectangle", (15, 1, 17, 3), fill=1)       # 手
    p.px(17, 1, 0), p.px(16, 3, 0)
    return p


def _rec_prop() -> Part:
    """支颐的手臂 11×13：肘撑地，小臂斜上去，手掌托着下巴；宽袖从小臂垂到地上"""
    p = Part(11, 13)
    p.shape("polygon", [(0, 12), (5, 2), (8, 2), (4, 12)], fill=1)     # 小臂（袖筒）
    p.shape("polygon", [(4, 6), (8, 6), (9, 12), (2, 12)], fill=1)     # 垂下的袖子
    p.d.line((4, 7, 6, 12), fill=0)
    p.dither([(6, 8), (9, 9), (9, 12), (7, 12)], 0.5, 0)
    p.shape("rectangle", (5, 0, 9, 2), fill=1)                          # 手掌（托腮）
    p.px(9, 0, 0), p.d.line((6, 1, 8, 1), fill=0)
    return p


def _recline(face: str, breath: bool) -> Sprite:
    c = Canvas(52, 30)
    c.add(_rec_prop(), 3, 17)
    c.add(_rec_body(breath), 11, 18)
    c.add(_rec_arm(), 14, 17 - (1 if breath else 0))
    blink = face == "blink"
    f = "normal" if blink else face
    c.add(_head(blink, 0, False, f)[0], 0, 1)
    return c.sprite()


def recline(g: Gfx, x: float, y: float, t: float = 0.0, face: str = "sleep", breath: bool | None = None) -> dict:
    """侧卧支颐。(x, y) = 画面左端、地面 y。长约 50、高 30。
    face：sleep / normal / blink / happy / wow。返回 {"mouth", "eye", "head", "hand", "hip", "toe"}"""
    x, y = int(round(x)), int(round(y))
    if breath is None:
        breath = (t / 3.6) % 1 < 0.5
    spr = cached(("rec", face, breath), lambda: _recline(face, breath))
    pix.blit(g, spr, x, y - 30)
    return {"mouth": (x + 10, y - 15), "eye": (x + 10, y - 18), "head": (x + 8, y - 29), "hand": (x + 32, y - 12),
            "hip": (x + 35, y - 13), "toe": (x + 49, y - 5)}


# ---------------------------------------------------------------- Z、梦泡、星星

Z_SPR = pix.frames("""
####
  #
 #
####
---
#####
   #
  #
 #
#####
---
######
    #
   #
  #
 #
######
""")


def zzz(g: Gfx, x: float, y: float, t: float, n: int = 3, period: float = 3.0, on: float = 1.0, dx: float = 14,
        dy: float = -16):
    """冒 Z：每个 Z 从 (x, y) 出发往右上飘、由小变大，飘到头消失（只依赖 t）"""
    for i in range(n):
        k = ((t / period) + i / n) % 1.0
        if k > on:
            continue
        sx = x + dx * k + math.sin((t + i) * 2.2) * 1.2
        sy = y + dy * k
        spr = Z_SPR[min(int(k * 3), 2)]
        pix.blit(g, spr, sx, sy - spr.h)


def mx_z(g: Gfx, t: float, x0: int = 3, y0: int = 0):
    """点阵：一个小 Z 往上飘（3×3），配一个小点"""
    k = (t / 3.0) % 1
    yy = y0 + 3 - int(k * 4)
    for (a, b) in ((0, 0), (1, 0), (2, 0), (1, 1), (0, 2), (1, 2), (2, 2)):
        g.mx_set(x0 + a, yy + b)


SPARK = pix.frames("""
 #
###
 #
---
  #
  #
##.##
  #
  #
""")


def twinkle(g: Gfx, x, y, t, seed=0, big=False):
    """一颗会闪的星：大部分时间一个点，偶尔闪成十字"""
    k = (t * 0.5 + seed * 0.37) % 1
    if k < 0.08 and big:
        pix.blit(g, SPARK[1], x - 2, y - 2, outline=False)
    elif k < 0.16:
        pix.blit(g, SPARK[0], x - 1, y - 1, outline=False)
    else:
        g.px(x, y)


def bubble(g: Gfx, cx, cy, r, shine: bool = True):
    """梦泡 / 鼻涕泡：黑底白圈，左上一个高光弧（像素圆）"""
    r = max(1, int(round(r)))
    g.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=0, outline=1)
    if shine and r >= 3:
        g.px(cx - r + 2, cy - r + 2)
        if r >= 5:
            g.px(cx - r + 2, cy - r + 3), g.px(cx - r + 3, cy - r + 2)


def pop(g: Gfx, cx, cy, k: float, r: float = 6):
    """泡破：八个方向的短线向外散开（k 0..1）"""
    rr = r + k * 5
    for a in range(8):
        ang = a * math.pi / 4
        x0, y0 = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
        if k < 0.6:
            g.d.line((x0, y0, cx + math.cos(ang) * (rr + 2), cy + math.sin(ang) * (rr + 2)), fill=1)
        else:
            g.px(x0, y0)


# ---------------------------------------------------------------- 圆形收拢

_YY, _XX = np.mgrid[0:H, 0:W]


def iris(g: Gfx, cx: float, cy: float, r: float):
    """圆形收拢：半径 r 之外涂黑，边上一圈亮线（r ≥ 140 时不做）"""
    if r >= 140:
        return
    a = g.array()
    d2 = (_XX - cx) ** 2 + (_YY - cy) ** 2
    a[d2 > r * r] = False
    if r > 1:
        a[(d2 <= r * r) & (d2 > (r - 1) * (r - 1))] = True
    g.put(a)


# ---------------------------------------------------------------- 时间与文字

def ev(t: float, period: float, start: float, dur: float):
    """周期小事件：t ≥ start 起每 period 秒一次、持续 dur 秒；返回事件内的时间（秒）或 None"""
    if t < start:
        return None
    k = (t - start) % period
    return k if k < dur else None


def plate(g: Gfx, x: float, y: float, s: str, size: int = 12, k: float = 1.0, frame: bool = True,
          align: str = "left"):
    """带边框底板的字：先把底板涂黑（盖住背景）再画框和字。k < 1 时从下面弹上来。最后画"""
    w = text_width(s, size)
    hgt = 11 if size == 12 else 7
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    yy = y + (1 - ease_out_back(clamp(k))) * 6
    x0, y0, x1, y1 = x - 3, yy - 3, x + w + 2, yy + hgt + 2
    g.d.rectangle((x0, y0, x1, y1), fill=0, outline=1 if frame else 0)
    if frame:
        g.px(x0, y0, 0), g.px(x1, y0, 0), g.px(x0, y1, 0), g.px(x1, y1, 0)
    g.text(x, yy, s, size=size)
    return (x0, y0, x1, y1)


def vplate(g: Gfx, x: float, y: float, s: str, n: int | None = None, size: int = 12):
    """竖写（毛笔题字）：先清出一条竖的黑底，再逐字写出 n 个字"""
    n = len(s) if n is None else max(0, min(n, len(s)))
    if n <= 0:
        return
    step = (11 if size == 12 else 7) + 1
    g.d.rectangle((x - 2, y - 2, x + size + 1, y + n * step + 1), fill=0)
    g.vtext(x, y, s[:n], size=size)


def say(g: Gfx, x: float, y: float, s: str, k: float, size: int = 12):
    """一闪而过的字：不带框，先清底；k 0..1 弹出"""
    w = text_width(s, size)
    hgt = 11 if size == 12 else 7
    yy = y + (1 - ease_out_back(clamp(k))) * 4
    g.d.rectangle((x - 2, yy - 2, x + w + 1, yy + hgt + 1), fill=0)
    g.text(x, yy, s, size=size)


def bang(g: Gfx, x: float, y: float):
    """头上的“！”（像素）"""
    g.d.rectangle((x - 1, y - 1, x + 3, y + 9), fill=0)
    g.d.rectangle((x, y, x + 2, y + 5), fill=1)
    g.d.rectangle((x, y + 7, x + 2, y + 8), fill=1)


def mx_face(g: Gfx, awake: bool = True):
    """点阵：一张小脸（醒 = 睁眼，睡 = 合眼）"""
    rows = [0x3C, 0x42, 0xA5, 0x81, 0xA5, 0x99, 0x42, 0x3C] if awake else \
        [0x3C, 0x42, 0x81, 0xE7, 0x81, 0x99, 0x42, 0x3C]
    g.mx_rows(rows)


__all__ = ["cached", "head_up", "supine", "recline", "zzz", "mx_z", "twinkle", "bubble", "pop", "iris", "ev", "plate",
           "vplate", "say", "bang", "mx_face", "SPARK", "Z_SPR", "span"]


# ---------------------------------------------------------------- 共用的小动物、云

def _crane(wing: int) -> Sprite:
    """仙鹤飞（朝右）22×15：长颈前伸、长喙、长腿往后拖；翅膀 0 上扬 / 1 平展 / 2 下压，翅尖黑羽；丹顶一个暗点"""
    p = Part(22, 15)
    p.shape("ellipse", (5, 6, 12, 9), fill=1)                # 身子
    p.shape("line", (11, 7, 15, 5), fill=1, width=2)          # 脖子
    p.shape("rectangle", (15, 3, 17, 5), fill=1)              # 头
    p.px(16, 3, 0)                                            # 丹顶
    p.shape("line", (18, 5, 21, 6), fill=1)                   # 喙
    p.shape("line", (5, 8, 0, 9), fill=1)                     # 腿
    p.shape("line", (5, 7, 1, 7), fill=1)
    p.px(0, 8, 1)
    if wing == 0:
        p.shape("polygon", [(7, 6), (11, 6), (6, 0), (3, 0)], fill=1)
        p.d.line((4, 1, 6, 3), fill=0)
        p.px(4, 0, 0)
    elif wing == 1:
        p.shape("polygon", [(6, 6), (11, 6), (4, 3), (0, 3)], fill=1)
        p.d.line((1, 4, 4, 4), fill=0)
    else:
        p.shape("polygon", [(7, 8), (11, 8), (6, 14), (3, 14)], fill=1)
        p.d.line((4, 13, 6, 11), fill=0)
        p.px(4, 14, 0)
    p.px(6, 8, 0), p.px(7, 9, 0)                              # 尾羽（黑）
    return p.sprite()


CRANE_FLY = [_crane(0), _crane(1), _crane(2)]


def _crane_stand(lift: bool) -> Sprite:
    """仙鹤站（朝右）13×20：长腿、S 形颈、丹顶、黑尾；lift=True 时一只脚抬起"""
    p = Part(13, 20)
    p.shape("ellipse", (0, 7, 9, 12), fill=1)                # 身子
    p.shape("polygon", [(0, 9), (0, 12), (3, 12)], fill=1)
    p.d.line((1, 11, 4, 12), fill=0)                          # 黑尾羽
    p.dither([(0, 10), (4, 10), (4, 12), (0, 12)], 0.5, 0)
    p.d.line((2, 9, 6, 9), fill=0)                            # 翼缘
    p.shape("line", (8, 8, 9, 3), fill=1, width=2)            # 脖子
    p.shape("rectangle", (8, 1, 10, 3), fill=1)               # 头
    p.px(9, 1, 0)                                             # 丹顶
    p.shape("line", (11, 2, 12, 3), fill=1)                   # 喙
    p.shape("line", (4, 12, 4, 19), fill=1)                   # 腿
    if lift:
        p.shape("line", (6, 12, 7, 16), fill=1)
        p.shape("line", (7, 16, 6, 17), fill=1)
    else:
        p.shape("line", (6, 12, 6, 19), fill=1)
        p.px(7, 19, 1)
    p.px(3, 19, 1), p.px(5, 19, 1)
    return p.sprite()


CRANE_STAND = [_crane_stand(False), _crane_stand(True)]


def _cloud(w: int = 34) -> Sprite:
    """祥云 w×12：几团圆拼成，白底；云头两个暗线卷（卷云纹），底边平、底下一道暗线和一排网点"""
    p = Part(w, 12)
    for x0, y0, x1, y1 in ((0, 4, 10, 11), (6, 1, 17, 11), (14, 0, 25, 11), (21, 3, w - 1, 11)):
        p.shape("ellipse", (x0, y0, x1, y1), fill=1)
    p.shape("rectangle", (4, 8, w - 4, 11), fill=1)
    for cx, cy, r in ((11, 6, 3), (19, 5, 3)):               # 卷：一圈弧 + 中心点
        p.d.arc((cx - r, cy - r, cx + r, cy + r), 200, 520, fill=0)
        p.px(cx, cy, 0)
    p.d.arc((24, 5, 30, 11), 180, 300, fill=0)
    p.d.line((3, 9, w - 4, 9), fill=0)
    p.dither([(2, 10), (w - 2, 10), (w - 2, 11), (2, 11)], 0.5, 0)
    return p.sprite()


CLOUD = _cloud()


def crane_fly(g: Gfx, x: float, y: float, t: float, flip: bool = False, fps: float = 5.0):
    fr = CRANE_FLY[[0, 1, 2, 1][int(t * fps) % 4]]
    pix.blit(g, fr, x - fr.w // 2, y - fr.h // 2, flip=flip)
