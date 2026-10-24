"""缓动与时间工具。时间一律用秒（float）"""
from __future__ import annotations

import math


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def lerp(a: float, b: float, p: float) -> float:
    return a + (b - a) * p


def span(t: float, a: float, b: float) -> float:
    """t 在 [a, b] 里走到了哪（0..1，之外截断）。分段动画：p = span(t, 0.5, 1.2)"""
    return clamp((t - a) / (b - a)) if b > a else float(t >= b)


def ease_in(p: float) -> float:
    p = clamp(p)
    return p * p * p


def ease_out(p: float) -> float:
    p = 1 - clamp(p)
    return 1 - p * p * p


def ease_in_out(p: float) -> float:
    p = clamp(p)
    return 4 * p * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def ease_out_back(p: float, s: float = 1.70158) -> float:
    p = clamp(p) - 1
    return 1 + (s + 1) * p * p * p + s * p * p


def ease_out_bounce(p: float) -> float:
    p = clamp(p)
    n, d = 7.5625, 2.75
    if p < 1 / d:
        return n * p * p
    if p < 2 / d:
        p -= 1.5 / d
        return n * p * p + 0.75
    if p < 2.5 / d:
        p -= 2.25 / d
        return n * p * p + 0.9375
    p -= 2.625 / d
    return n * p * p + 0.984375


def ease_out_elastic(p: float) -> float:
    p = clamp(p)
    if p in (0, 1):
        return p
    return 2 ** (-10 * p) * math.sin((p * 10 - 0.75) * (2 * math.pi / 3)) + 1


def smoothstep(p: float) -> float:
    p = clamp(p)
    return p * p * (3 - 2 * p)


def pulse(t: float, period: float) -> float:
    """0..1 的正弦呼吸"""
    return 0.5 - 0.5 * math.cos(2 * math.pi * t / period)


def blink(t: float, period: float, duty: float = 0.5) -> bool:
    return (t % period) < period * duty


def _hash(i: int, seed: int) -> float:
    h = (i * 374761393 + seed * 668265263) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 0xFFFF


def noise(x: float, seed: int = 0) -> float:
    """一维平滑值噪声，0..1。烟、火、抖动用"""
    i = math.floor(x)
    f = x - i
    a, b = _hash(i, seed), _hash(i + 1, seed)
    return a + (b - a) * smoothstep(f)


def rand(i: int, seed: int = 0) -> float:
    """确定性随机数 0..1（同样的 i、seed 永远得到同样的值）"""
    return _hash(int(i), seed)
