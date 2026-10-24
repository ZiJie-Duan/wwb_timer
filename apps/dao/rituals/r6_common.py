"""r6 赛博道法：本批共用的小工具（不登记场景）。像素风（见 AUTHORING.md）。

tiny(g, x, y, s)        3×5 点阵小字（数字、大写字母、常用符号）：屏幕读数、终端、G 代码
bitsmoke(...)           “数字烟”：2 像素台阶的 8 位烟，顶上飘 0/1
arm(angle, ...)         小道士的自定义手臂（任意角度的宽袖手臂，带袖口、网点阴影、手），给 figure() 用
dao(g, x, y, t, ...)    用 arm() 摆姿势的小道士（打字、举手机、扇火、拧旋钮……）
R6                      本批法事基类：puffs / sparks / bits（0/1 粒子）/ dt
badge / banner / rise   文字：左上角计数牌、弹出横幅、上飘小字（都要在所有特效之后最后画）
"""
from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image

from ..engine import pix
from ..engine.anim import clamp, ease_out_back, noise, rand, span
from ..engine.chars import Part, figure
from ..engine.gfx import Gfx, Sprite, text_width
from ..engine.scene import Ritual

_F = {
    "0": "### #.# #.# #.# ###", "1": ".#. ##. .#. .#. ###", "2": "### ..# ### #.. ###",
    "3": "### ..# ### ..# ###", "4": "#.# #.# ### ..# ..#", "5": "### #.. ### ..# ###",
    "6": "### #.. ### #.# ###", "7": "### ..# ..# .#. .#.", "8": "### #.# ### #.# ###",
    "9": "### #.# ### ..# ###",
    "A": ".#. #.# ### #.# #.#", "B": "##. #.# ##. #.# ##.", "C": ".## #.. #.. #.. .##",
    "D": "##. #.# #.# #.# ##.", "E": "### #.. ##. #.. ###", "F": "### #.. ##. #.. #..",
    "G": ".## #.. #.# #.# .##", "H": "#.# #.# ### #.# #.#", "I": "### .#. .#. .#. ###",
    "J": "..# ..# ..# #.# .#.", "K": "#.# #.# ##. #.# #.#", "L": "#.. #.. #.. #.. ###",
    "M": "#.# ### ### #.# #.#", "N": "##. #.# #.# #.# #.#", "O": ".#. #.# #.# #.# .#.",
    "P": "##. #.# ##. #.. #..", "Q": ".#. #.# #.# ##. .##", "R": "##. #.# ##. #.# #.#",
    "S": ".## #.. .#. ..# ##.", "T": "### .#. .#. .#. .#.", "U": "#.# #.# #.# #.# ###",
    "V": "#.# #.# #.# #.# .#.", "W": "#.# #.# ### ### #.#", "X": "#.# #.# .#. #.# #.#",
    "Y": "#.# #.# .#. .#. .#.", "Z": "### ..# .#. #.. ###",
    "%": "#.# ..# .#. #.. #.#", ".": "... ... ... ... .#.", ":": "... .#. ... .#. ...",
    "-": "... ... ### ... ...", "+": "... .#. ### .#. ...", "/": "..# ..# .#. #.. #..",
    "=": "... ### ... ### ...", "(": ".#. #.. #.. #.. .#.", ")": ".#. ..# ..# ..# .#.",
    "<": "..# .#. #.. .#. ..#", ">": "#.. .#. ..# .#. #..", "_": "... ... ... ... ###",
    "#": "#.# ### #.# ### #.#", "!": ".#. .#. .#. ... .#.", "?": "##. ..# .#. ... .#.",
    "[": "##. #.. #.. #.. ##.", "]": ".## ..# ..# ..# .##", ",": "... ... ... .#. #..",
    "*": "... #.# .#. #.# ...", "^": ".#. #.# ... ... ...", "'": ".#. .#. ... ... ...",
    "|": ".#. .#. .#. .#. .#.", "$": ".## ##. .#. .## ##.", "~": "... .## ##. ... ...",
    " ": "... ... ... ... ...",
}
_MASK: dict[str, Image.Image] = {}
for _k, _v in _F.items():
    _a = np.array([[c == "#" for c in row] for row in _v.split()], dtype=bool)
    _MASK[_k] = Image.fromarray(_a)
_MASK["{"] = _MASK["("]
_MASK["}"] = _MASK[")"]


def tiny_w(s: str) -> int:
    return max(0, len(s) * 4 - 1)


def tiny(g: Gfx, x: float, y: float, s: str, fill: int = 1, align: str = "left") -> int:
    """3×5 小字；y 为字顶。返回宽度"""
    w = tiny_w(s)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    x, y = int(round(x)), int(round(y))
    for i, ch in enumerate(s.upper()):
        m = _MASK.get(ch)
        if m is not None and ch != " ":
            g.img.paste(fill, (x + i * 4, y), m)
    return w



def bitsmoke(g: Gfx, x: float, y: float, height: float, t: float, seed: int = 0, n: int = 3, speed: float = 7.0,
             sway: float = 3.0, drift: float = 0.0, amount: float = 1.0):
    """数字烟：一缕量化成 2 像素台阶的“8 位烟”，往上越来越碎，顶上飘出几个 0/1。amount 0..1 控制高度/浓度"""
    if height <= 2 or amount <= 0:
        return
    hh = height * amount
    for i in range(0, int(hh), 2):
        k = i / max(height, 1)
        ph = (i + t * speed) * 0.12
        dx = (noise(ph, seed) - 0.5) * 2 * sway * (0.3 + k) + math.sin(ph * 1.7 + seed) * sway * 0.4 * k
        xx = int(round((x + dx + drift * k * k) / 2) * 2)
        yy = int(y - i)
        if k > 0.45 and rand(int(i + t * speed), seed) < (k - 0.45) * 2.0:
            continue
        if k < 0.3:
            g.d.line((xx, yy - 1, xx, yy), fill=1)
        else:
            g.d.rectangle((xx, yy - 1, xx + 1, yy), fill=1)
    for j in range(n):  # 飘起来的 0/1
        ph = (t * speed / height * 0.8 + j / n + rand(j, seed) * 0.3) % 1.0
        if ph < 0.35 or ph * height > hh + 4:
            continue
        cyc = int(t * speed / height * 0.8 + j / n + rand(j, seed) * 0.3)
        if ph > 0.8 and rand(int(t * 10) + j, seed) < (ph - 0.8) * 4:
            continue
        k = ph
        side = 1 if (cyc + j) % 2 else -1
        xx = x + drift * k * k + side * (3 + 4 * k) + (noise(k * 4, seed + j) - 0.5) * 4
        tiny(g, int(xx) - 1, int(y - k * height) - 2, "1" if rand(cyc * 7 + j, seed) > 0.5 else "0")


def pixsmoke(g: Gfx, x: float, y: float, t: float, seed: int = 0, height: float = 24, amount: float = 1.0,
             rate: float = 0.45, n: int = 7, sway: float = 3.0, drift: float = 0.0, bits: bool = True):
    """8 位像素烟（无状态，按 t 算）：香头一段细烟柱，往上变成 2×2、3×3 的方块，再变空心、碎成单点；
    bits：有几块在半空变成 0/1。amount 0..1 控制浓淡（烟起 / 烟散）"""
    if amount <= 0:
        return
    for i in range(1, 5):                                  # 细烟柱
        if i <= 4 * amount:
            g.px(x + round(math.sin(t * 3 + i * 0.9 + seed) * 0.6 * (i > 2)), y - i)
    for j in range(n):
        u = t * rate + j / n + rand(j, seed) * 0.08
        ph = u % 1.0
        cyc = int(u)
        if rand(cyc * 13 + j, seed) > amount or ph * height < 4:
            continue
        k = ph
        xx = x + math.sin(k * 5 + cyc * 1.7 + seed + j) * sway * k + drift * k * k
        yy = y - 3 - k * height
        ix, iy = int(round(xx)), int(round(yy))
        if bits and k > 0.5 and rand(cyc * 7 + j, seed + 3) < 0.3:
            if k < 0.9:
                tiny(g, ix - 1, iy - 2, "1" if rand(cyc + j, seed) < 0.5 else "0")
            continue
        if k < 0.25:
            g.d.rectangle((ix, iy, ix + 1, iy + 1), fill=1)
        elif k < 0.55:
            g.d.rectangle((ix - 1, iy - 1, ix + 1, iy + 1), fill=1)
        elif k < 0.75:
            g.d.rectangle((ix - 1, iy - 1, ix + 1, iy + 1), outline=1)
        elif k < 0.92:
            g.px(ix - 1, iy), g.px(ix + 1, iy - 1)
        elif int(t * 10 + j) % 2:
            g.px(ix, iy)


def glow_rays(g: Gfx, cx: float, cy: float, r0: float, r1: float, n: int = 12, phase: float = 0.0, sy: float = 1.0,
              dashed: bool = False):
    """放射光芒（dashed：虚线光芒，更“像素”）"""
    for i in range(n):
        a = i / n * 2 * math.pi + phase
        x0, y0 = cx + math.cos(a) * r0, cy + math.sin(a) * r0 * sy
        x1, y1 = cx + math.cos(a) * r1, cy + math.sin(a) * r1 * sy
        if dashed:
            pix.dotted(g, x0, y0, x1, y1, 2)
        else:
            g.d.line((x0, y0, x1, y1), fill=1)


def mx_bar(g: Gfx, col: int, h: int, bottom: int = 6):
    for r in range(bottom, bottom - h, -1):
        g.mx_set(col, r)


def num(n: int) -> str:
    """轮数：一百以内用中文数字，再大用阿拉伯数字"""
    from ..engine.cn import cn_num
    return cn_num(n) if n < 100 else str(n)


def nth(n: int, unit: str) -> str:
    """“第十二炷”；过百改成“432炷”"""
    return f"第{num(n)}{unit}" if n < 100 else f"{n}{unit}"


# ---------------------------------------------------------------- 小道士的自定义手臂

SHOULDER = (0, -14)      # 肩在脚底中点坐标系里的位置（朝右）
_C = 15                  # 手臂画布 31×31，肩在 (15, 15)
_ARMS: dict = {}


def _arm(angle: int, length: int, hand: str) -> Sprite:
    """宽袖手臂（照内置袖子的造型）：粗袖筒从肩伸向 angle，袖口下垂成袖兜，腕处一道镶边阴线，下半网点阴影，露出手。
    angle：0 = 水平向前，正 = 向上，负 = 向下（度）。hand：fist 握 / open 张掌（向上）/ point 剑指"""
    p = Part(2 * _C + 1, 2 * _C + 1)
    a = math.radians(angle)
    ux, uy = math.cos(a), -math.sin(a)
    nx, ny = -uy, ux
    if ny < 0 or (ny == 0 and nx < 0):
        nx, ny = -nx, -ny                                # 法向朝下一侧
    sx, sy = _C, _C
    wx, wy = sx + ux * length, sy + uy * length          # 腕
    hang = 3.5 * clamp((angle + 70) / 80)                 # 袖兜下垂量（手往下指时不垂）
    poly = [(sx - nx * 3 - ux * 1, sy - ny * 3 - uy * 1), (wx - nx * 2.5, wy - ny * 2.5),
            (wx + nx * 2.5, wy + ny * 2.5 + hang), (wx + nx * 2.5 - ux * 3, wy + ny * 2.5 + hang + 0.5),
            (sx + nx * 3.5, sy + ny * 3.5)]
    p.shape("polygon", poly, fill=1)
    p.shape("ellipse", (sx - 3, sy - 3, sx + 3, sy + 3), fill=1)          # 圆肩
    # 下半网点阴影（背光的袖兜）
    p.dither([(sx + nx * 1.8, sy + ny * 1.8), (wx + nx * 1.2, wy + ny * 1.2), (wx + nx * 3, wy + ny * 3 + hang),
              (wx + nx * 3 - ux * 3, wy + ny * 3 + hang + 1), (sx + nx * 4, sy + ny * 4)], 0.5, 0)
    # 袖口镶边：腕处一道阴线
    cx0, cy0 = wx - ux * 1.0, wy - uy * 1.0
    p.d.line((cx0 - nx * 2, cy0 - ny * 2, cx0 + nx * 2.5, cy0 + ny * 2.5 + hang), fill=0)
    # 手
    hx, hy = wx + ux * 1.6, wy + uy * 1.6
    rx, ry = int(round(hx)), int(round(hy))
    if hand == "open":       # 张掌：掌心朝上
        p.shape("rectangle", (rx - 1, ry - 1, rx + 2, ry + 1), fill=1)
        p.shape("rectangle", (rx + 2, ry - 2, rx + 3, ry - 1), fill=1)
        p.px(rx - 1, ry - 2)
        p.px(rx + 1, ry, 0)
        tip = (rx + 1, ry - 2)
    elif hand == "point":    # 剑指：食中二指并拢伸直
        p.shape("rectangle", (rx - 1, ry - 1, rx + 1, ry + 1), fill=1)
        tx, ty = hx + ux * 4.5, hy + uy * 4.5
        p.shape("line", (rx, ry - 1, tx, ty - 1), fill=1)
        p.shape("line", (rx, ry, tx, ty), fill=1)
        tip = (int(round(tx)), int(round(ty - 0.5)))
    else:                    # 握拳
        p.shape("rectangle", (rx - 1, ry - 1, rx + 1, ry + 2), fill=1)
        p.px(rx + 1, ry, 0)
        tip = (rx + 1, ry)
    spr = p.sprite()
    spr.hand = tip
    return spr


def arm(angle: float, length: int = 9, hand: str = "fist") -> Sprite:
    """自定义手臂精灵（按 5° 缓存）。spr.hand = 手在精灵里的位置。配合 figure(arm=..., arm_at=ARM_AT)"""
    key = (int(round(angle / 5)) * 5, length, hand)
    s = _ARMS.get(key)
    if s is None:
        s = _ARMS[key] = _arm(*key)
        if key[0] > 35:
            s.over_head = True
    return s


ARM_AT = (SHOULDER[0] - _C, SHOULDER[1] - _C)


def dao(g: Gfx, x: float, y: float, t: float, angle: float | None = None, length: int = 9, hand: str = "fist",
        pose: str | None = None, flip: bool = False, face: str = "normal", head: str = "up", legs: str = "stand",
        bob: bool = True, front=None, behind=None) -> dict:
    """小道士。angle 给了就用自定义手臂（angle 度、length 长、hand 手型）；否则 pose 用内置动作
    （down / offer / gong / raise / point，或 daoshi 的 bow / kneel / sit……）。返回 {"hand": (x, y)}"""
    from ..engine.chars import daoshi
    if angle is None:
        if pose in (None, "down", "offer", "gong", "raise", "point"):
            return figure(g, x, y, t, legs=legs, arm=pose or "down", head=head, face=face, flip=flip, bob=bob,
                          behind=behind, front=front)
        return daoshi(g, x, y, pose, t, flip=flip, face=face, bob=bob)
    return figure(g, x, y, t, legs=legs, arm=arm(angle, length, hand), arm_at=ARM_AT, head=head, face=face,
                  flip=flip, bob=bob, behind=behind, front=front)


# ---------------------------------------------------------------- 粒子：0/1

class Bits:
    """飞溅的 0/1（3×5 小字粒子，带重力）"""

    def __init__(self, seed: int = 0):
        self.p: list[list] = []
        self.rng = random.Random(seed)

    def burst(self, x, y, n=6, speed=30.0, up=10.0, life=0.9, gravity=40.0):
        for _ in range(n):
            a = self.rng.random() * 2 * math.pi
            v = speed * (0.4 + self.rng.random() * 0.8)
            self.p.append([x, y, math.cos(a) * v, math.sin(a) * v - up, 0.0, life * (0.6 + self.rng.random() * 0.6),
                           gravity, "1" if self.rng.random() < 0.5 else "0"])

    def step(self, dt):
        keep = []
        for q in self.p:
            q[4] += dt
            if q[4] < q[5]:
                q[3] += q[6] * dt
                q[0] += q[2] * dt
                q[1] += q[3] * dt
                keep.append(q)
        self.p = keep

    def draw(self, g: Gfx):
        for x, y, vx, vy, age, life, grav, ch in self.p:
            if age > life * 0.75 and int(age * 20) % 2:
                continue
            g.d.rectangle((x - 2, y - 1, x + 2, y + 5), fill=0)
            tiny(g, x - 1, y, ch)

    def clear(self):
        self.p.clear()


class R6(Ritual):
    """本批法事基类：self.puffs / self.sparks / self.bits，self._dt(t) 求帧间隔（t 回零时安全）"""

    def setup(self):
        self.puffs = pix.Puffs(self.seed)
        self.sparks = pix.Sparks(self.seed + 1)
        self.bits = Bits(self.seed + 2)
        self.last_t = None
        self.init()

    def init(self):
        """子类的 setup"""

    def _dt(self, t: float) -> float:
        dt = 1 / 30 if self.last_t is None or t < self.last_t else min(t - self.last_t, 0.2)
        self.last_t = t
        return dt

    def fx(self, g: Gfx, dt: float, wind: float = 0.0):
        """推进并画全部粒子"""
        self.puffs.step(dt, wind)
        self.puffs.draw(g)
        self.sparks.step(dt)
        self.sparks.draw(g)
        self.bits.step(dt)
        self.bits.draw(g)


# ---------------------------------------------------------------- 文字（都在最后画）

def badge(g: Gfx, s: str, x: int = 3, y: int = 2, align: str = "left"):
    """计数牌：细框里一行 8px 字（“第几炷”）"""
    w = text_width(s, 8)
    if align == "right":
        x -= w + 4
    g.d.rectangle((x - 1, y - 1, x + w + 5, y + 11), fill=0)
    g.d.rectangle((x, y, x + w + 4, y + 10), outline=1)
    g.text(x + 2, y + 2, s, size=8)


def banner(g: Gfx, cx: float, y: float, s: str, k: float, size: int = 12, stars: bool = True, t: float = 0.0):
    """弹出横幅：k = 弹出进度 0..1（ease_out_back 从下面弹上来），黑底白框，两边闪星"""
    if k <= 0:
        return
    pop = ease_out_back(k)
    w = text_width(s, size)
    hh = 11 if size == 12 else 7
    yy = y + (1 - pop) * 8
    x0, x1 = cx - w / 2 - 3, cx + w / 2 + 2
    g.d.rectangle((x0 - 1, yy - 3, x1 + 1, yy + hh + 3), fill=0)
    g.d.rectangle((x0, yy - 2, x1, yy + hh + 2), outline=1)
    if stars and int(t * 6) % 2 == 0:
        for sx in (x0 - 4, x1 + 4):
            sy = yy + hh / 2
            for ddx, ddy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                g.px(sx + ddx, sy + ddy)
    g.text(cx, yy, s, size=size, align="center")


def rise(g: Gfx, x: float, y: float, s: str, age: float, life: float = 1.2, size: int = 8, dist: float = 10):
    """上飘小字（“功德+1”）：age 0..life，往上飘，最后闪两下消失"""
    if not 0 <= age < life:
        return
    k = age / life
    if k > 0.75 and int(age * 16) % 2:
        return
    g.text(x, y - dist * (1 - (1 - k) ** 2), s, size=size, align="center")
