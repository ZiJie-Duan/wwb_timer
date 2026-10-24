"""生成 64×64 蓝噪声阈值图（void-and-cluster，Ulichney 1993）→ assets/bluenoise64.npy。只需运行一次：

    python -m apps.dao.tools.bake_noise
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

N = 64
SIGMA = 1.5


def _kernel() -> np.ndarray:
    ax = np.arange(N)
    d = np.minimum(ax, N - ax).astype(np.float64)
    g1 = np.exp(-d * d / (2 * SIGMA * SIGMA))
    return np.fft.rfft2(np.outer(g1, g1))


def _energy(bits: np.ndarray, kf) -> np.ndarray:
    return np.fft.irfft2(np.fft.rfft2(bits.astype(np.float64)) * kf, s=bits.shape)


def bake(seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    kf = _kernel()
    total = N * N
    ones = total // 10
    bits = np.zeros((N, N), bool)
    bits.flat[rng.choice(total, ones, replace=False)] = True
    # 1. 把初始点调成均匀：反复把最密集的点移到最空的地方
    while True:
        e = _energy(bits, kf)
        tight = np.argmax(np.where(bits, e, -np.inf))
        bits.flat[tight] = False
        e = _energy(bits, kf)
        void = np.argmin(np.where(bits, np.inf, e))
        if void == tight:
            bits.flat[tight] = True
            break
        bits.flat[void] = True
    rank = np.zeros((N, N), np.int32)
    proto = bits.copy()
    # 2. 去点：从最密集的开始，名次 ones-1 … 0
    b = proto.copy()
    for r in range(ones - 1, -1, -1):
        e = _energy(b, kf)
        tight = np.argmax(np.where(b, e, -np.inf))
        b.flat[tight] = False
        rank.flat[tight] = r
    # 3. 加点：往最空的地方填，名次 ones … total-1
    b = proto.copy()
    for r in range(ones, total):
        e = _energy(b, kf)
        void = np.argmin(np.where(b, np.inf, e))
        b.flat[void] = True
        rank.flat[void] = r
    return (rank * 256 // total).astype(np.uint8)


def main():
    out = Path(__file__).resolve().parent.parent / "assets" / "bluenoise64.npy"
    np.save(out, bake())
    print(out)


if __name__ == "__main__":
    main()
