import math
import threading
import time

from wwb import Font
from wwb.app import run

IDLE = bytes([0x00, 0x3C, 0x42, 0x5A, 0x5A, 0x42, 0x3C, 0x00])  # 停着时点阵显示一个圆


def hand(angle: float) -> bytes:
    """从中心指向 angle（弧度，0 = 正上方，顺时针）的指针"""
    rows = bytearray(8)
    for k in range(9):
        x = math.floor(3.5 + k * 0.5 * math.sin(angle) + 0.5)
        y = math.floor(3.5 - k * 0.5 * math.cos(angle) + 0.5)
        if 0 <= x < 8 and 0 <= y < 8:
            rows[y] |= 0x80 >> x
    return bytes(rows)


def main(d):
    lock = threading.Lock()
    running, acc, since = False, 0, 0

    def on_input(ev):
        nonlocal running, acc, since
        with lock:
            if ev.name == "switch":
                if ev.active and not running:
                    running, since = True, ev.t_us
                elif not ev.active and running:
                    running, acc = False, acc + ev.t_us - since
                print(f"开关{'开' if ev.active else '关'}  t={ev.t_us / 1e6:.3f}s", flush=True)
            elif ev.active:
                acc = 0
                if running:
                    since = ev.t_us
                print("清零", flush=True)

    d.on_input(on_input)
    print("拨开关开始 / 暂停，按 BOOT 清零", flush=True)
    period, nxt = 1 / 60, time.perf_counter()
    while True:
        now = d.time_us()
        with lock:
            us = acc + (now - since if running else 0)
            on = running
        cs, s, m = us // 10_000 % 100, us // 1_000_000 % 60, us // 60_000_000 % 100

        d.oled_clear(wait=False)
        d.oled_text(0, 9, "STOPWATCH", Font.F6X10, wait=False)
        d.oled_rect(92, 0, 36, 11, 1 if on else 2, wait=False)
        d.oled_text(97, 9, "RUN" if on else "STOP", Font.F6X10, 0 if on else 1, wait=False)
        d.oled_text(2, 52, f"{m:02}:{s:02}", Font.LOGISOSO32_NUM, wait=False)
        d.oled_text(97, 52, f".{cs:02}", Font.LOGISOSO16, wait=False)
        bar = round(128 * (us % 60_000_000) / 60_000_000)
        if bar > 0:  # 宽度为 0 时设备会报 BAD_ARG
            d.oled_rect(0, 58, bar, 6, wait=False)
        d.oled_flush(wait=False)

        colon = not on or us % 1_000_000 < 500_000
        d.seg_text(f"{m:02}{':' if colon else ''}{s:02}")
        d.mx_frame(hand(2 * math.pi * (us % 1_000_000) / 1_000_000) if on or us else IDLE)

        nxt = max(nxt + period, time.perf_counter())
        time.sleep(max(0.0, nxt - time.perf_counter()))


run(main)
