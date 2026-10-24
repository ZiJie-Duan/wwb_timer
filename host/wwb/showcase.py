"""赛博风多场景演示：全部画面在上位机逐帧计算，经协议推到三块屏，展示这台设备的能力。

    python -m wwb.showcase                  # 循环播放，Ctrl-C 退出
    python -m wwb.showcase --seconds 120
    python -m wwb.showcase --scene warp     # 只循环一个场景
    python -m wwb.showcase --preview DIR    # 不连设备，把各场景的帧渲染成 PNG 预览

交互：拨动开关 → 切到下一个场景；按 BOOT 键 → 整屏反色（硬件反色命令）
帧率：OLED 约 95fps（整帧，拆 4 条局部更新），数码管 100/s，点阵 120/s
"""
from __future__ import annotations

import argparse
import itertools
import math
import os
import sys
import threading
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .protocol import Op

W, H = 128, 64
OLED_RATE, SEG_RATE, MX_RATE = 100, 100, 120
TRANSITION = 0.35  # 场景之间雪花过渡（秒）

# ------------------------------------------------------------------ 基础工具

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def load_font(name: str, size: int):
    path = os.path.join(FONT_DIR, name)
    return ImageFont.truetype(path, size) if os.path.exists(path) else ImageFont.load_default(size)


MONO = load_font("DejaVuSansMono.ttf", 9)
MONO_B = load_font("DejaVuSansMono-Bold.ttf", 9)
TINY = load_font("DejaVuSansMono.ttf", 8)
BIG = load_font("DejaVuSans-Bold.ttf", 30)
MID_B = load_font("DejaVuSansMono-Bold.ttf", 12)

_BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16 + 1 / 32
BAYER = np.tile(_BAYER4, (H // 4, W // 4))
BAYER8 = np.tile(_BAYER4, (2, 2))
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)


def to_frame(a: np.ndarray) -> bytes:
    """(64,128) 布尔画面 → SSD1306 帧缓冲（8 页 × 128 列，LSB 在上）"""
    return np.packbits(a.reshape(8, 8, W).transpose(0, 2, 1), axis=2, bitorder="little").tobytes()


def mx_bytes(a: np.ndarray) -> bytes:
    """(8,8) 布尔 → 点阵 8 行（bit7 在左）"""
    return np.packbits(a.astype(np.uint8), axis=1).ravel().tobytes()


class Canvas:
    def __init__(self):
        self.img = Image.new("1", (W, H))
        self.d = ImageDraw.Draw(self.img)
        self.d.fontmode = "1"

    def clear(self):
        self.d.rectangle((0, 0, W - 1, H - 1), fill=0)
        return self

    def array(self) -> np.ndarray:
        return np.array(self.img, dtype=bool)


def smooth(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def line8(a: np.ndarray, x0: float, y0: float, x1: float, y1: float):
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    for k in range(n + 1):
        x = math.floor(x0 + (x1 - x0) * k / n + 0.5)
        y = math.floor(y0 + (y1 - y0) * k / n + 0.5)
        if 0 <= x < 8 and 0 <= y < 8:
            a[y, x] = True


# ------------------------------------------------------------------ 数码管

SEG_A, SEG_B, SEG_C, SEG_D, SEG_E, SEG_F, SEG_G = (1 << i for i in range(7))
SEG_CHARS = {
    **{str(i): v for i, v in enumerate((0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F))},
    "A": 0x77, "b": 0x7C, "C": 0x39, "c": 0x58, "d": 0x5E, "E": 0x79, "e": 0x79, "F": 0x71, "G": 0x3D,
    "H": 0x76, "h": 0x74, "J": 0x1E, "L": 0x38, "n": 0x54, "o": 0x5C, "P": 0x73, "r": 0x50, "S": 0x6D,
    "t": 0x78, "U": 0x3E, "u": 0x1C, "y": 0x6E, "-": 0x40, "_": 0x08, " ": 0x00,
}


def seg(text: str, colon: bool = False) -> bytes:
    out = [SEG_CHARS.get(c, 0) for c in text[-4:].rjust(4)]
    if colon:
        out[1] |= 0x80
    return bytes(out)


def seg_noise(rng, density: float = 0.5) -> list[int]:
    return [int(sum(1 << b for b in range(7) if rng.random() < density)) for _ in range(4)]


# ------------------------------------------------------------------ 场景

class Scene:
    name = ""
    duration = 9.0

    def __init__(self):
        self.rng = np.random.default_rng()
        self.aux_rng = np.random.default_rng()  # 数码管/点阵在另一线程，用独立随机源
        self.hw_invert = False

    def oled(self, t: float, dt: float, hud: dict) -> np.ndarray:
        raise NotImplementedError

    def seg(self, t: float) -> bytes:
        return seg("    ")

    def mx(self, t: float) -> bytes:
        return bytes(8)


def scanline(a: np.ndarray, t: float, speed: float = 70):
    a[int(t * speed) % H] ^= True


class Boot(Scene):
    name, duration = "boot", 7.5
    LINES = ["> WWB//TIMER v0.1", "> usb-jtag ..... OK", "> ssd1306 1.1M . OK", "> tm1637 isr ... OK",
             "> max7219 10M .. OK", "> uart 20/21 ... OK", "> SYSTEM ONLINE"]
    CPS, PAUSE = 55, 0.12
    CHECK = np.array([[0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 1], [0, 0, 0, 0, 0, 0, 1, 0],
                      [1, 0, 0, 0, 0, 1, 0, 0], [0, 1, 0, 0, 1, 0, 0, 0], [0, 0, 1, 1, 0, 0, 0, 0],
                      [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]], bool)

    def __init__(self):
        super().__init__()
        self.c = Canvas()
        starts, t = [], 0.3
        for line in self.LINES:
            starts.append(t)
            t += len(line) / self.CPS + self.PAUSE
        self.starts, self.done_t = starts, t
        self.ring = [(0, x) for x in range(8)] + [(y, 7) for y in range(1, 8)] + \
                    [(7, x) for x in range(6, -1, -1)] + [(y, 0) for y in range(6, 0, -1)]

    def progress(self, t: float) -> float:
        return min(1.0, t / self.done_t)

    def oled(self, t, dt, hud):
        c = self.c.clear()
        d = c.d
        d.rectangle((0, 0, W - 1, 9), fill=1)
        d.text((2, 0), "WWB//TIMER  BOOT", font=MONO_B, fill=0)
        d.text((104, 0), f"{hud['oled']:3.0f}", font=MONO_B, fill=0)
        typed = []
        for line, st in zip(self.LINES, self.starts):
            if t >= st:
                typed.append(line[:int((t - st) * self.CPS)])
        for row, text in enumerate(typed[-4:]):
            y = 12 + row * 10
            d.text((1, y), text, font=MONO, fill=1)
            if row == len(typed[-4:]) - 1 and int(t * 6) % 2:
                x = 1 + int(d.textlength(text, font=MONO))
                d.rectangle((x + 1, y + 1, x + 5, y + 9), fill=1)
        p = self.progress(t)
        d.rectangle((0, 55, W - 1, 63), outline=1)
        d.rectangle((2, 57, 2 + int(123 * p), 61), fill=1)
        if t > self.done_t + 0.3 and int(t * 4) % 2 == 0:
            d.rectangle((14, 20, 113, 44), fill=0, outline=1)
            d.rectangle((16, 22, 111, 42), fill=1)
            d.text((22, 26), "ACCESS GRANTED", font=MONO_B, fill=0)
        a = c.array()
        scanline(a, t)
        return a

    def seg(self, t):
        if t > self.done_t:
            return seg("done") if int(t * 4) % 2 == 0 or t > self.done_t + 1.5 else seg("    ")
        noise = seg_noise(self.aux_rng)
        final = seg("boot")
        return bytes(final[i] if t > 0.8 + 0.5 * i else noise[i] for i in range(4))

    def mx(self, t):
        a = np.zeros((8, 8), bool)
        if t > self.done_t:
            return mx_bytes(self.CHECK if t > self.done_t + 0.4 else np.ones((8, 8), bool))
        head = int(t * 2 * 28) % 28
        for k in range(5):
            y, x = self.ring[(head - k) % 28]
            a[y, x] = True
        return mx_bytes(a)


class Warp(Scene):
    name, duration = "warp", 9.0
    N = 150
    RING = np.floor(np.maximum(abs(np.arange(8)[:, None] - 3.5), abs(np.arange(8)[None, :] - 3.5))).astype(int)

    def __init__(self):
        super().__init__()
        self.c = Canvas()
        self.xy = self.rng.uniform(-1, 1, (self.N, 2))
        self.z = self.rng.uniform(0.05, 1, self.N)

    def speed(self, t):
        return 0.12 + 2.4 * smooth((t - 0.5) / 6.3)

    def oled(self, t, dt, hud):
        if 7.0 <= t < 7.15:
            return np.ones((H, W), bool)
        if 7.15 <= t < 7.6:
            return self.rng.random((H, W)) < (7.6 - t) * 1.8
        sp = self.speed(t) * (0.15 if t > 7.6 else 1)
        self.z -= sp * dt
        dead = self.z < 0.03
        if dead.any():
            self.xy[dead] = self.rng.uniform(-1, 1, (dead.sum(), 2))
            self.z[dead] = 1.0
        c = self.c.clear()
        f = 30
        tail = np.minimum(1.0, self.z + sp * 0.05)  # 拖尾 = 最近 50ms 的运动轨迹，越快越长
        for (x, y), z0, z1 in zip(self.xy, tail, self.z):
            x0, y0 = 64 + x / z0 * f, 32 + y / z0 * f
            x1, y1 = 64 + x / z1 * f, 32 + y / z1 * f
            c.d.line((x0, y0, x1, y1), fill=1)
        c.d.line((60, 32, 68, 32), fill=1)
        c.d.line((64, 28, 64, 36), fill=1)
        c.d.rectangle((0, 54, 50, 63), fill=0)
        c.d.text((1, 54), f"WARP {sp:4.2f}", font=TINY, fill=1)
        return c.array()

    def seg(self, t):
        if 7.0 <= t < 7.6:
            return seg("8888") if int(t * 20) % 2 else seg("    ")
        return seg(f"{min(9999, int(self.speed(t) * 1000)):4d}")

    def mx(self, t):
        if 7.0 <= t < 7.4:
            return mx_bytes(np.ones((8, 8), bool))
        phase = t * 3 + 5 * smooth((t - 0.5) / 6.3) * t
        k = 3 - int(phase) % 4
        return mx_bytes((self.RING == k) | (self.RING == (k + 2) % 4) & (int(phase * 2) % 2 == 0))


TESSERACT_V = np.array(list(itertools.product([-1, 1], repeat=4)), float)
TESSERACT_E = [(i, j) for i in range(16) for j in range(i + 1, 16)
               if (TESSERACT_V[i] != TESSERACT_V[j]).sum() == 1]


class Hypercube(Scene):
    name, duration = "hypercube", 9.0
    V, E = TESSERACT_V, TESSERACT_E

    def __init__(self):
        super().__init__()
        self.c = Canvas()

    @staticmethod
    def rot(n, i, j, a):
        r = np.eye(n)
        r[i, i] = r[j, j] = math.cos(a)
        r[i, j], r[j, i] = -math.sin(a), math.sin(a)
        return r

    def project(self, t):
        v = self.V @ self.rot(4, 0, 3, t * 0.9).T @ self.rot(4, 1, 3, t * 0.55).T
        k = 1 / (3.0 - v[:, 3])
        p = v[:, :3] * k[:, None]
        p = p @ self.rot(3, 0, 2, t * 0.4).T @ self.rot(3, 1, 2, 0.35).T
        s = 1 / (4.0 - p[:, 2])
        return 64 + p[:, 0] * s * 125, 32 + p[:, 1] * s * 125, k  # 125：转动中最大正好占满屏高

    def oled(self, t, dt, hud):
        c = self.c.clear()
        x, y, k = self.project(t)
        for i, j in self.E:
            c.d.line((x[i], y[i], x[j], y[j]), fill=1)
        for xi, yi, ki in zip(x, y, k):
            if ki > 0.4:  # 只给靠近观察者（w 方向）的那一半顶点加亮点，增强纵深感
                c.d.rectangle((xi - 1, yi - 1, xi + 1, yi + 1), fill=1)
        c.d.text((0, 0), "4D//HYPERCUBE", font=TINY, fill=1)
        c.d.text((84, 55), f"XW {math.degrees(t * 0.9) % 360:3.0f}", font=TINY, fill=1)
        return c.array()

    def seg(self, t):
        return seg(f"A{int(math.degrees(t * 0.9)) % 360:3d}")

    def mx(self, t):
        a = np.zeros((8, 8), bool)
        pts = [(3.5 + 3.4 * math.cos(t * 2.2 + q * math.pi / 2), 3.5 + 3.4 * math.sin(t * 2.2 + q * math.pi / 2))
               for q in range(4)]
        for q in range(4):
            line8(a, *pts[q], *pts[(q + 1) % 4])
        return mx_bytes(a)


class Rain(Scene):
    name, duration = "rain", 9.0
    COLS, ROWS = 21, 8

    def __init__(self):
        super().__init__()
        g = self.rng.random((64, 7, 3)) < 0.5
        self.glyphs = np.concatenate([g, g[:, :, 1::-1]], axis=2)[:, :, :5]  # 左右对称的外星符号
        self.cells = self.rng.integers(0, 64, (self.ROWS, self.COLS))
        self.head = self.rng.uniform(-8, 8, self.COLS)
        self.speed = self.rng.uniform(6, 18, self.COLS)
        self.length = self.rng.integers(3, 9, self.COLS)
        self.drops = self.aux_rng.uniform(-8, 0, 8)
        self.drop_speed = self.aux_rng.uniform(8, 20, 8)
        self.c = Canvas()

    def oled(self, t, dt, hud):
        a = np.zeros((H, W), bool)
        mut = self.rng.random(self.cells.shape) < 0.04
        self.cells[mut] = self.rng.integers(0, 64, mut.sum())
        self.head += self.speed * dt
        reset = self.head - self.length > self.ROWS
        self.head[reset] = self.rng.uniform(-6, 0, reset.sum())
        self.speed[reset] = self.rng.uniform(6, 18, reset.sum())
        for col in range(self.COLS):
            h, ln, x = int(self.head[col]), self.length[col], col * 6 + 1
            for r in range(max(0, h - ln + 1), min(self.ROWS, h + 1)):
                g = self.glyphs[self.cells[r, col]]
                y = r * 8
                dist = h - r
                if dist == 0:
                    a[y:y + 8, x - 1:x + 5] = True
                    a[y:y + 7, x:x + 5] &= ~g
                else:
                    keep = self.rng.random(g.shape) > dist / ln * 0.85
                    a[y:y + 7, x:x + 5] |= g & keep
        if t > 6.3:
            c = self.c.clear()
            c.d.rectangle((14, 24, 113, 40), fill=1)
            c.d.text((19, 27), "SIGNAL ACQUIRED", font=MONO_B, fill=0)
            box = c.array()
            if int(t * 5) % 3:
                a[22:43, 12:116] = False
                a |= box
        return a

    def seg(self, t):
        noise = [SEG_CHARS[str(self.aux_rng.integers(0, 10))] for _ in range(4)]
        final = seg("2026")
        return bytes(final[i] if t > 5 + 0.45 * i else noise[i] for i in range(4))

    def mx(self, t):
        a = np.zeros((8, 8), bool)
        self.drops += self.drop_speed / MX_RATE
        for x in range(8):
            if self.drops[x] - 3 > 8:
                self.drops[x] = self.aux_rng.uniform(-6, 0)
                self.drop_speed[x] = self.aux_rng.uniform(8, 20)
            h = int(self.drops[x])
            for k in range(3):
                if 0 <= h - k < 8 and (k == 0 or (k == 1) or int(t * 30) % 2):
                    a[h - k, x] = True
        return mx_bytes(a)


class Plasma(Scene):
    name, duration = "plasma", 9.0
    SNAKE = [(0, SEG_A), (1, SEG_A), (2, SEG_A), (3, SEG_A), (3, SEG_B), (3, SEG_C),
             (3, SEG_D), (2, SEG_D), (1, SEG_D), (0, SEG_D), (0, SEG_E), (0, SEG_F)]
    Y8, X8 = np.mgrid[0:8, 0:8].astype(np.float32)

    def __init__(self):
        super().__init__()
        self.c = Canvas()
        self.c.d.rectangle((0, 54, 78, 63), fill=1)
        self.c.d.text((2, 54), "PLASMA//FIELD", font=TINY, fill=0)
        self.label = self.c.array()

    @staticmethod
    def field(x, y, t, s=1.0):
        cx, cy = 64 + 34 * math.cos(t * 0.7), 32 + 18 * math.sin(t * 1.1)
        v = (np.sin(x * 0.085 * s + t * 1.6) + np.sin(y * 0.13 * s - t * 1.2)
             + np.sin((x + y) * 0.06 * s + t * 0.9)
             + np.sin(np.sqrt((x * s - cx) ** 2 + (y * s - cy) ** 2) * 0.11 - t * 2.0))
        return (v + 4) / 8

    def oled(self, t, dt, hud):
        a = self.field(XX, YY, t) > BAYER
        a[54:64, 0:79] = self.label[54:64, 0:79]
        return a

    def seg(self, t):
        out = [0, 0, 0, 0]
        head = int(t * 24)
        for k in range(4):
            digit, bit = self.SNAKE[(head - k) % len(self.SNAKE)]
            out[digit] |= bit
        return bytes(out)

    def mx(self, t):
        return mx_bytes(self.field(self.X8 * 16, self.Y8 * 8, t * 1.3) > BAYER8)


class Spectrum(Scene):
    name, duration = "spectrum", 9.0
    BARS, BPM = 32, 120

    def __init__(self):
        super().__init__()
        self.h = np.zeros(self.BARS)
        self.peak = np.zeros(self.BARS)
        self.idx = np.arange(self.BARS)
        self.c = Canvas()
        self.c.d.text((0, 0), f"SPECTRUM {self.BPM}BPM", font=TINY, fill=1)
        self.header = self.c.array()

    def beat(self, t):
        return math.exp(-(t % (60 / self.BPM)) * 9)

    def oled(self, t, dt, hud):
        i, env = self.idx, self.beat(t)
        target = (0.22 + 0.18 * np.sin(t * 2.1 + i * 0.45) + 0.14 * np.sin(t * 5.3 + i * 1.7)
                  + 0.65 * env * np.clip(1 - i / 9, 0, 1) + 0.25 * env * (i % 7 == 3)
                  + self.rng.random(self.BARS) * 0.12) * (1 - i / 60)
        target = np.clip(target, 0, 1)
        self.h = np.maximum(target, self.h - dt * 1.6)
        self.peak = np.maximum(self.h, self.peak - dt * 0.45)
        a = self.header.copy()
        base, span = 46, 34
        for b in range(self.BARS):
            x = b * 4
            top = base - int(self.h[b] * span)
            a[top:base, x:x + 3] = True
            pk = base - int(self.peak[b] * span) - 2
            a[max(9, pk), x:x + 3] = True
            ref = int(self.h[b] * 14)
            a[base + 2:base + 2 + ref, x:x + 3] = True
        a[base + 2:, :] &= ((XX[base + 2:] + YY[base + 2:]) % 2 == 0)
        a[base, :] = True
        return a

    def seg(self, t):
        beats = int(t * self.BPM / 60)
        return seg(f"{beats:4d}", colon=self.beat(t) > 0.4)

    def mx(self, t):
        env = self.beat(t)
        a = np.zeros((8, 8), bool)
        for b in range(8):
            v = 0.3 + 0.25 * math.sin(t * 3 + b) + 0.6 * env * max(0, 1 - b / 3) + 0.15 * math.sin(t * 7.1 + b * 2)
            n = max(0, min(8, int(v * 8)))
            a[8 - n:, b] = True
        return mx_bytes(a)


class Glitch(Scene):
    name, duration = "glitch", 9.0
    W8 = np.array([[1, 0, 0, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, 0, 0, 1], [1, 0, 0, 1, 1, 0, 0, 1],
                   [1, 0, 0, 1, 1, 0, 0, 1], [1, 0, 1, 0, 0, 1, 0, 1], [1, 1, 0, 0, 0, 0, 1, 1],
                   [1, 0, 0, 0, 0, 0, 0, 1], [0, 0, 0, 0, 0, 0, 0, 0]], bool)

    def __init__(self):
        super().__init__()
        c = Canvas()
        wb = c.d.textbbox((0, 0), "WWB", font=BIG)
        c.d.text(((W - (wb[2] - wb[0])) // 2 - wb[0], 2 - wb[1]), "WWB", font=BIG, fill=1)
        tw = c.d.textlength("T I M E R", font=MID_B)
        c.d.text(((W - tw) // 2, 34), "T I M E R", font=MID_B, fill=1)
        c.d.line((4, 41, (W - tw) // 2 - 6, 41), fill=1)
        c.d.line(((W + tw) // 2 + 6, 41, W - 5, 41), fill=1)
        self.logo = c.array()
        self.c = Canvas()

    def level(self, t):
        if t > 6.2:
            return 0.0
        burst = (t * 2.7) % 1 < 0.18
        return 1.0 if burst else 0.12

    def oled(self, t, dt, hud):
        g = self.level(t)
        a = self.logo.copy()
        for _ in range(int(g * 9)):
            y0 = int(self.rng.integers(0, H - 2))
            h = int(self.rng.integers(1, 7))
            a[y0:y0 + h] = np.roll(a[y0:y0 + h], int(self.rng.integers(-14, 15)), axis=1)
        if g > 0.5:
            a |= np.roll(self.logo, 3, axis=1) & (YY % 2 == 0)
            y0, x0 = int(self.rng.integers(0, H - 8)), int(self.rng.integers(0, W - 30))
            a[y0:y0 + 6, x0:x0 + 28] ^= self.rng.random((6, 28)) < 0.5
        self.hw_invert = g > 0.5 and self.rng.random() < 0.25
        if t > 5.4:
            c = self.c.clear()
            text = "> LIMITS: PUSHED"[:int((t - 5.4) * 30)]
            c.d.text((14, 53), text, font=TINY, fill=1)
            if int(t * 6) % 2:
                x = 14 + int(c.d.textlength(text, font=TINY))
                c.d.rectangle((x + 1, 55, x + 4, 62), fill=1)
            a[50:] = c.array()[50:]
        scanline(a, t, 45)
        return a

    def seg(self, t):
        if t < 5.0:
            if self.level(t) > 0.5:
                return bytes(seg_noise(self.aux_rng, 0.4))
            return seg("-88-")
        lt = time.localtime()
        return seg(f"{lt.tm_hour:02d}{lt.tm_min:02d}", colon=int(time.time() * 2) % 2 == 0)

    def mx(self, t):
        a = self.W8.copy()
        if self.level(t) > 0.5:
            for r in range(8):
                if self.aux_rng.random() < 0.4:
                    a[r] = np.roll(a[r], int(self.aux_rng.integers(-3, 4)))
        return mx_bytes(a)


SCENES = [Boot, Warp, Hypercube, Rain, Plasma, Spectrum, Glitch]


# ------------------------------------------------------------------ 导演：场景切换与过渡

class Director:
    def __init__(self, scenes, now):
        self.scenes = scenes
        self.idx = 0
        self.scene = scenes[0]()
        self.start = now
        self.trans_start: float | None = None
        self.lock = threading.Lock()

    def skip(self, now):
        with self.lock:
            if self.trans_start is None:
                self.trans_start = now

    def update(self, now):
        """由 OLED 线程每帧调用；返回 (场景, 场景内时间, 过渡进度 0–1 或 None)"""
        with self.lock:
            t = now - self.start
            if self.trans_start is None and t >= self.scene.duration:
                self.trans_start = now
            if self.trans_start is not None:
                u = (now - self.trans_start) / TRANSITION
                if u < 1:
                    return self.scene, t, u
                self.idx = (self.idx + 1) % len(self.scenes)
                self.scene = self.scenes[self.idx]()
                self.start, self.trans_start = now, None
                t = 0.0
            return self.scene, t, None

    def peek(self, now):
        with self.lock:
            u = None if self.trans_start is None else (now - self.trans_start) / TRANSITION
            return self.scene, now - self.start, u if u is not None and u < 1 else None


# ------------------------------------------------------------------ 运行

def run(args):
    from .device import Device

    sys.setswitchinterval(0.0002)
    scenes = [s for s in SCENES if s.name == args.scene] if args.scene else SCENES
    with Device(args.port) as d:
        d.oled_config(1_100_000)
        d.mx_config(intensity=2, rotation=1, spi_hz=10_000_000)
        d.seg_config(brightness=4)
        d.stats_reset()
        t0 = time.perf_counter()
        end = t0 + args.seconds if args.seconds else float("inf")
        director = Director(scenes, t0)
        hud = {"oled": 0.0, "seg": 0.0, "mx": 0.0}
        user_invert = [False]
        stop = threading.Event()

        def on_input(ev):
            if ev.name == "switch":
                director.skip(time.perf_counter())
            elif ev.name == "boot" and ev.active:
                user_invert[0] = not user_invert[0]
        d.on_input(on_input)

        def oled_loop():
            rng = np.random.default_rng()
            last, inverted = time.perf_counter(), False
            nxt = last
            while not stop.is_set():
                now = time.perf_counter()
                if now < nxt:
                    time.sleep(max(0.0, nxt - now - 0.0002))
                    continue
                nxt = max(nxt + 1 / OLED_RATE, now + 0.5 / OLED_RATE)
                scene, t, u = director.update(now)
                dt, last = min(0.05, now - last), now
                if u is None:
                    a = scene.oled(t, dt, hud)
                    want_invert = scene.hw_invert
                else:
                    a = rng.random((H, W)) < math.sin(math.pi * u) * 0.9
                    want_invert = False
                want_invert ^= user_invert[0]
                if want_invert != inverted:
                    d.send(Op.OLED_CMD, bytes([0xA7 if want_invert else 0xA6]))
                    inverted = want_invert
                frame = to_frame(a)
                for page in range(0, 8, 2):
                    d.oled_blit(page, 0, 2, 128, frame[page * 128:(page + 2) * 128], flush=page == 6)

        def aux_loop():
            rng = np.random.default_rng()
            nseg = nmx = time.perf_counter()
            while not stop.is_set():
                now = time.perf_counter()
                scene, t, u = director.peek(now)
                if now >= nseg:
                    nseg = max(nseg + 1 / SEG_RATE, now + 0.5 / SEG_RATE)
                    d.seg_raw(bytes(seg_noise(rng, 0.5)) if u is not None else scene.seg(t))
                if now >= nmx:
                    nmx = max(nmx + 1 / MX_RATE, now + 0.5 / MX_RATE)
                    d.mx_frame(mx_bytes(rng.random((8, 8)) < 0.5) if u is not None else scene.mx(t))
                wait = min(nseg, nmx) - time.perf_counter()
                time.sleep(max(0.0, wait - 0.0002))

        threads = [threading.Thread(target=f, daemon=True) for f in (oled_loop, aux_loop)]
        for th in threads:
            th.start()
        print("场景循环中：拨开关切换场景，按 BOOT 键反色，Ctrl-C 退出")
        print("  时间   场景         OLED fps  数码管/s  点阵/s")
        prev = d.stats()
        try:
            while time.perf_counter() < end:
                time.sleep(1)
                s = d.stats()
                dt = (s["uptime_us"] - prev["uptime_us"]) / 1e6
                hud.update(oled=(s["oled"]["pushes"] - prev["oled"]["pushes"]) / dt,
                           seg=(s["seg"]["updates"] - prev["seg"]["updates"]) / dt,
                           mx=(s["mx"]["frames"] - prev["mx"]["frames"]) / dt)
                prev = s
                print(f"{time.perf_counter() - t0:6.1f}s  {director.scene.name:11s}  {hud['oled']:7.1f}  "
                      f"{hud['seg']:7.0f}  {hud['mx']:6.0f}", flush=True)
        except KeyboardInterrupt:
            pass
        finally:
            stop.set()
            for th in threads:
                th.join(timeout=1)
            d.send(Op.OLED_CMD, bytes([0xA6]))
            d.oled_clear()
            d.oled_text(22, 30, "wwb_timer", 1)
            d.oled_text(28, 46, "demo end", 0, flush=True)
            d.seg_text("----")
            d.mx_frame(bytes(8), wait=True)


def preview(args):
    """不连设备：把每个场景按时间采样渲染成放大的 PNG，便于检查构图"""
    os.makedirs(args.preview, exist_ok=True)
    hud = {"oled": 95.0, "seg": 100.0, "mx": 120.0}
    for cls in SCENES:
        sc = cls()
        times = np.linspace(0, cls.duration - 0.05, 12)
        sheet = Image.new("L", ((W * 3 + 6) * 4, (H * 3 + 6 + 30) * 3), 40)
        draw = ImageDraw.Draw(sheet)
        t_prev, cost = 0.0, []
        for n, t in enumerate(times):
            # 用 1/95 秒步长推进到 t，保证有状态的场景（星空、代码雨）和真实运行一致
            while t_prev + 1 / 95 < t:
                t_prev += 1 / 95
                sc.oled(t_prev, 1 / 95, hud)
            t0 = time.perf_counter()
            a = sc.oled(t, t - t_prev, hud)
            cost.append(time.perf_counter() - t0)
            t_prev = t
            img = Image.fromarray((a * 255).astype(np.uint8)).resize((W * 3, H * 3), Image.NEAREST)
            col, row = n % 4, n // 4
            x, y = col * (W * 3 + 6), row * (H * 3 + 36)
            sheet.paste(img, (x, y))
            segs = sc.seg(t)
            m = np.unpackbits(np.frombuffer(sc.mx(t), np.uint8)).reshape(8, 8)
            mimg = Image.fromarray((m * 255).astype(np.uint8)).resize((24, 24), Image.NEAREST)
            sheet.paste(mimg, (x + W * 3 - 26, y + H * 3 + 4))
            draw.text((x + 2, y + H * 3 + 6), f"t={t:4.1f}s seg={segs.hex()}", fill=200)
        path = os.path.join(args.preview, f"{cls.name}.png")
        sheet.save(path)
        print(f"{cls.name:10s} 渲染一帧 中位 {sorted(cost)[len(cost) // 2] * 1e3:5.2f} ms  最大 {max(cost) * 1e3:5.2f} ms  → {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--seconds", type=float, default=0, help="0 = 一直循环")
    ap.add_argument("--scene", choices=[s.name for s in SCENES])
    ap.add_argument("--preview", metavar="DIR", help="不连设备，渲染各场景预览图到 DIR")
    args = ap.parse_args()
    if args.preview:
        preview(args)
    else:
        run(args)


if __name__ == "__main__":
    main()
