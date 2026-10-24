"""目测验证：循环切换点阵 SPI 时钟与 OLED I²C 时钟，持续高速重绘，看哪一档开始显示出错。

    python -m wwb.visual [--minutes 10]

点阵：显示当前 SPI 的 MHz 数字（1/2/4/8/10/16/20），最下一行是一条横线（也用来确认方向）。
OLED：上方写当前 I²C 设定和点阵档位，下半屏是 1 像素棋盘格；出错时会出现雪花或错位。
"""
from __future__ import annotations

import argparse
import time

from PIL import Image, ImageDraw

from .device import DEFAULT_PORT, Device, image_to_frame

FONT3X5 = {
    "0": (7, 5, 5, 5, 7), "1": (2, 6, 2, 2, 7), "2": (7, 1, 7, 4, 7), "4": (5, 5, 7, 1, 1),
    "6": (7, 4, 7, 5, 7), "8": (7, 5, 7, 5, 7),
}

MX_STEPS_MHZ = (1, 2, 4, 8, 10, 16, 20)
OLED_STEPS_KHZ = (1100, 2600)


def matrix_number(n: int) -> bytes:
    text = str(n)
    rows = [0] * 8
    cols = [2] if len(text) == 1 else [0, 4]
    for ch, c in zip(text, cols):
        for r, bits in enumerate(FONT3X5[ch]):
            rows[1 + r] |= bits << (5 - c)
    rows[7] = 0xFF
    return bytes(rows)


def oled_test_frame(label: str) -> bytes:
    img = Image.new("1", (128, 64))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 127, 63), outline=1)
    draw.text((4, 4), label, fill=1)
    for y in range(32, 62):
        for x in range(2, 126):
            if (x + y) % 2 == 0:
                img.putpixel((x, y), 1)
    return image_to_frame(img)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=DEFAULT_PORT)
    ap.add_argument("--minutes", type=float, default=10)
    ap.add_argument("--step", type=float, default=5, help="每档停留秒数")
    args = ap.parse_args()

    with Device(args.port) as d:
        end = time.time() + args.minutes * 60
        try:
            while time.time() < end:
                for i, mhz in enumerate(MX_STEPS_MHZ):
                    khz = OLED_STEPS_KHZ[i % len(OLED_STEPS_KHZ)]
                    d.oled_config(khz * 1000)
                    d.mx_config(intensity=1, rotation=1, spi_hz=mhz * 1_000_000)
                    label = f"I2C {khz}k  MX {mhz}MHz"
                    frame = oled_test_frame(label)
                    print(f"{time.strftime('%H:%M:%S')}  {label}", flush=True)
                    rows = matrix_number(mhz)
                    t0 = time.time()
                    while time.time() - t0 < args.step:
                        d.oled_frame(frame)
                        d.mx_frame(rows)
                        d.ping()  # 限速：等设备处理完再发下一轮
        finally:
            d.oled_config(1_100_000)
            d.mx_config(intensity=1, rotation=1, spi_hz=10_000_000)


if __name__ == "__main__":
    main()
