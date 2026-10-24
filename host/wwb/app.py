"""wwb 程序的统一入口：解析 --port，打开设备，调用 main(d)。apps/ 下的程序都用它：

    # apps/hello/__main__.py
    from wwb.app import run

    def main(d):
        d.seg_text("hi")
        ...

    run(main)

    python -m apps.hello                  # 真机（默认 /dev/ttyACM0）
    python -m apps.hello --port sim       # 网页模拟器（一般在网页上点“运行”即可）

收到 Ctrl+C、SIGTERM 或 SIGHUP 时退出 main 并正常关闭设备。
"""
from __future__ import annotations

import argparse
import signal
import time
from typing import Callable

from .device import DEFAULT_PORT, Device


def _interrupt(*_):
    raise KeyboardInterrupt


def run(main: Callable, description: str | None = None, add_args: Callable | None = None, **defaults):
    """add_args(ap)：程序自己的命令行参数，这时 main(d, args)；defaults 覆盖参数默认值"""
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--port", default=DEFAULT_PORT, help='串口；"sim" = 网页模拟器')
    if add_args:
        add_args(ap)
    ap.set_defaults(**defaults)
    args = ap.parse_args()
    signal.signal(signal.SIGTERM, _interrupt)
    signal.signal(signal.SIGHUP, _interrupt)  # 远程运行时 ssh 断开
    try:
        waiting = False
        while True:  # 设备没接上就一直等（常驻服务开机时设备可能还没连），接上就开始
            try:
                d = Device(args.port)
            except (TimeoutError, OSError) as e:
                if not waiting:
                    print(f"等待设备连接（{args.port}）：{e}", flush=True)
                    waiting = True
                time.sleep(2)
                continue
            if waiting:
                print("设备已连接", flush=True)
            with d:
                main(d, args) if add_args else main(d)
            break
    except KeyboardInterrupt:
        pass
