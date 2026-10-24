"""wwb 性能极限测试：链路、各外设硬件极限、上位机→屏幕的端到端吞吐。

    python -m wwb.bench                 # 全部
    python -m wwb.bench link seg        # 只跑部分
结果打印成表格，并保存到 results/bench_<时间>.json
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import struct
import time
from pathlib import Path

from .device import DEFAULT_PORT, Device, DeviceError
from .protocol import BenchTarget, Flag, Op

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"


def section(title: str):
    print(f"\n== {title}")


# ------------------------------------------------------------------ 链路

def bench_link(d: Device) -> dict:
    section("USB 链路")
    out = {"ping": {}, "upload": {}, "download": {}}
    for size in (0, 64, 256, 1024):
        payload = os.urandom(size)
        rtts = []
        for _ in range(300):
            t = time.perf_counter()
            assert d.ping(payload) == payload
            rtts.append((time.perf_counter() - t) * 1e3)
        rtts.sort()
        med, p99 = statistics.median(rtts), rtts[int(len(rtts) * 0.99)]
        out["ping"][size] = {"median_ms": med, "p99_ms": p99}
        print(f"往返 {size:5d}B  中位 {med:6.3f} ms  p99 {p99:6.3f} ms")

    for size in (64, 1024):
        d.stats_reset()
        payload = bytes(range(256)) * 4
        payload = payload[:size]
        t = time.perf_counter()
        while time.perf_counter() - t < 3:
            d.sink(payload)
        total = d.sink(b"", reply=True)
        dt = time.perf_counter() - t
        out["upload"][size] = {"KiB_s": total / dt / 1024, "frames_s": total / size / dt}
        print(f"上行 帧 {size:5d}B  {total / dt / 1024:7.1f} KiB/s  {total / size / dt:7.0f} 帧/s")

    got, host_s, _ = d.source(1_000_000, 1024)
    out["download"] = {"KiB_s": got / host_s / 1024}
    print(f"下行 块  1024B  {got / host_s / 1024:7.1f} KiB/s")
    return out


# ------------------------------------------------------------------ 外设硬件极限（设备端自测）

def bench_oled_hw(d: Device) -> dict:
    section("OLED 整帧推送（设备端，I2C 时钟扫描）")
    out = {}
    for khz in (400, 800, 1000, 1100, 2400, 2600):
        try:
            r = d.bench(BenchTarget.OLED, 60, khz * 1000)
        except DeviceError as e:
            print(f"{khz:5d} kHz  不支持（{e}）")
            continue
        ms = r["us"] / r["count"] / 1e3
        ok = r["errors"] == 0
        out[khz] = {"frame_ms": ms, "fps": 1000 / ms if ok else 0, "errors": r["errors"]}
        print(f"{khz:5d} kHz  每帧 {ms:7.2f} ms  {1000 / ms if ok else 0:6.1f} fps  错误 {r['errors']}/{r['count']}")
    return out


def bench_seg_hw(d: Device) -> dict:
    section("数码管 TM1637（设备端，严格 ACK，CLK 上升等待扫描）")
    out = {}
    for rise in (50, 46, 44, 43, 42, 40):
        r = d.bench(BenchTarget.SEG, 300, rise, 2, 5, 150)
        fails, total = r["ack_fails"], r["count"] * 5
        out[rise] = {"ack_fails": fails, "bytes": total}
        print(f"CLK 上升 {rise:2d} µs  ACK 失败 {fails:4d}/{total}")
    # 正常时序（不加严格等待）下整屏 / 单位刷新耗时
    full = d.bench(BenchTarget.SEG, 300, 50, 2, 5, 0)
    out["full_update_ms"] = full["us"] / 300 / 1e3
    print(f"整屏 4 位刷新 {out['full_update_ms']:.3f} ms（{1000 / out['full_update_ms']:.0f} 次/s）")
    return out


def bench_mx_hw(d: Device) -> dict:
    section("点阵 MAX7219（设备端，SPI 时钟扫描；显示是否正确需目测）")
    out = {}
    for mhz in (1, 2, 4, 8, 10):
        r = d.bench(BenchTarget.MX, 2000, mhz * 1_000_000)
        us = r["us"] / 2000
        out[mhz] = {"frame_us": us, "fps": 1e6 / us}
        print(f"SPI {mhz:3d} MHz  每帧 {us:6.1f} µs  {1e6 / us:7.0f} 帧/s")
    return out


# ------------------------------------------------------------------ 端到端（上位机推流 → 屏幕）

def _oled_frames(n: int = 16) -> list[bytes]:
    frames = []
    for k in range(n):
        f = bytearray(1024)
        for page in range(8):
            for x in range(128):
                f[page * 128 + x] = 0xFF if (x + k * 8) % 32 < 16 else (0x81 if page in (0, 7) else 0)
        frames.append(bytes(f))
    return frames


def _stream(seconds: float, step) -> tuple[int, float]:
    n, t0 = 0, time.perf_counter()
    while time.perf_counter() - t0 < seconds:
        step(n)
        n += 1
    return n, time.perf_counter() - t0


def bench_e2e(d: Device, seconds: float = 4) -> dict:
    section(f"端到端推流（各 {seconds:g} s）")
    out = {}
    frames = _oled_frames()

    def finish():
        d.ping()  # 等设备处理完之前的所有帧
        time.sleep(0.15)  # 让推送任务把最后一帧推完
        return d.stats()

    # OLED 整帧
    d.stats_reset()
    n, dt = _stream(seconds, lambda i: d.oled_frame(frames[i % len(frames)]))
    s = finish()["oled"]
    out["oled_full"] = {"sent_fps": n / dt, "received_fps": s["commits"] / dt, "displayed_fps": s["pushes"] / dt}
    print(f"OLED 整帧     发送 {n / dt:6.0f}/s  设备收到 {s['commits'] / dt:6.0f}/s  实际上屏 {s['pushes'] / dt:6.1f} fps")

    # OLED 局部：4 页 × 96 列（大号数字区域）
    region = bytes([0xF0, 0x0F] * 192)
    d.stats_reset()
    n, dt = _stream(seconds, lambda i: d.oled_blit(2, 16, 4, 96, region if i % 2 else region[::-1]))
    s = finish()["oled"]
    out["oled_region_4x96"] = {"sent_fps": n / dt, "displayed_fps": s["pushes"] / dt}
    print(f"OLED 局部4×96 发送 {n / dt:6.0f}/s  实际上屏 {s['pushes'] / dt:6.1f} fps")

    # 数码管：只变最后一位 / 四位全变
    for label, make in (("末位变化", lambda i: bytes([0x3F, 0x3F, 0x3F, (0x06, 0x5B)[i % 2]])),
                        ("四位全变", lambda i: bytes([(0x06, 0x5B)[i % 2]] * 4))):
        d.stats_reset()
        n, dt = _stream(seconds, lambda i: d.seg_raw(make(i)))
        s = finish()["seg"]
        out[f"seg_{label}"] = {"sent_s": n / dt, "updates_s": s["updates"] / dt, "ack_fails": s["ack_fails"]}
        print(f"数码管{label}  发送 {n / dt:6.0f}/s  实际刷新 {s['updates'] / dt:6.0f}/s  ACK失败 {s['ack_fails']}")

    # 点阵：逐条发送 / 32 条一批
    rows = [bytes([1 << (i % 8)] * 8) for i in range(8)]
    d.stats_reset()
    n, dt = _stream(seconds, lambda i: d.mx_frame(rows[i % 8]))
    s = finish()["mx"]
    out["mx_single"] = {"sent_s": n / dt, "frames_s": s["frames"] / dt}
    print(f"点阵逐条      发送 {n / dt:6.0f}/s  实际刷新 {s['frames'] / dt:6.0f}/s")

    def mx_batch(i):
        with d.batch():
            for k in range(32):
                d.mx_frame(rows[(i * 32 + k) % 8])
    d.stats_reset()
    n, dt = _stream(seconds, mx_batch)
    s = finish()["mx"]
    out["mx_batch32"] = {"frames_s": s["frames"] / dt}
    print(f"点阵 32条/批  实际刷新 {s['frames'] / dt:6.0f}/s")

    # 三块屏同时推流
    def all_three(i):
        with d.batch():
            d.oled_frame(frames[i % len(frames)])
            d.seg_raw(bytes([(0x06, 0x5B)[i % 2]] * 4))
            d.mx_frame(rows[i % 8])
    d.stats_reset()
    n, dt = _stream(seconds, all_three)
    s = finish()
    out["combined"] = {"loops_s": n / dt, "oled_fps": s["oled"]["pushes"] / dt,
                       "seg_s": s["seg"]["updates"] / dt, "mx_s": s["mx"]["frames"] / dt}
    print(f"三屏同时      OLED {s['oled']['pushes'] / dt:5.1f} fps  数码管 {s['seg']['updates'] / dt:5.0f}/s  "
          f"点阵 {s['mx']['frames'] / dt:5.0f}/s")
    return out


SECTIONS = {
    "link": bench_link,
    "oled": bench_oled_hw,
    "seg": bench_seg_hw,
    "mx": bench_mx_hw,
    "e2e": bench_e2e,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sections", nargs="*", choices=[*SECTIONS, []], help="默认全部")
    ap.add_argument("--port", default=DEFAULT_PORT)
    ap.add_argument("--baud", type=int, default=921600)
    args = ap.parse_args()

    with Device(args.port, args.baud) as d:
        info = d.info()
        print(f"{info['name']} fw {info['fw']}  {args.port}")
        results = {"info": info, "port": args.port, "time": time.strftime("%Y-%m-%d %H:%M:%S")}
        for name in args.sections or SECTIONS:
            results[name] = SECTIONS[name](d)

    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"bench_{time.strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n结果已保存：{path}")


if __name__ == "__main__":
    main()
