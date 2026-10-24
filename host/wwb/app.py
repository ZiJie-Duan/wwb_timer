"""wwb 程序的统一入口：解析 --port，打开设备，调用 main(d)。apps/ 下的程序都用它：

    # apps/hello/__main__.py
    from wwb.app import run

    def main(d):
        d.seg_text("hi")
        ...

    run(main)

    python -m apps.hello                  # 真机（默认 /dev/ttyACM0）
    python -m apps.hello --port sim       # 网页模拟器（一般在网页上点“运行”即可）

收到 Ctrl+C 或 SIGTERM 时退出 main 并正常关闭设备。
"""
from __future__ import annotations

import argparse
import signal
from typing import Callable

from .device import DEFAULT_PORT, Device


def _interrupt(*_):
    raise KeyboardInterrupt


def run(main: Callable[[Device], None], description: str | None = None):
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--port", default=DEFAULT_PORT, help='串口；"sim" = 网页模拟器')
    args = ap.parse_args()
    signal.signal(signal.SIGTERM, _interrupt)
    try:
        with Device(args.port) as d:
            main(d)
    except KeyboardInterrupt:
        pass
