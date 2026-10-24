"""wwb 命令行：python -m wwb <命令> ...（或安装后直接 wwb <命令>）

  info / stats / ping
  text "你好" [-x 0 -y 12 -f 5]     OLED 写字（-f 字体编号，见 info 里的 fonts）
  clear
  seg 12:34                         数码管
  mx 18 3c 7e db 18 18 18 18        点阵 8 行（十六进制）
  mxcfg --intensity 1 --rotation 1 --spi 4000000
  io                                读开关 / BOOT 键
  events                            持续打印输入事件（Ctrl-C 退出）
  led on|off
  reboot
"""
from __future__ import annotations

import argparse
import json
import time

from .device import Device


def main():
    ap = argparse.ArgumentParser(prog="wwb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--baud", type=int, default=921600)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info")
    sub.add_parser("stats")
    sub.add_parser("ping")
    p = sub.add_parser("text")
    p.add_argument("text")
    p.add_argument("-x", type=int, default=0)
    p.add_argument("-y", type=int, default=12)
    p.add_argument("-f", "--font", type=int, default=0)
    p.add_argument("--keep", action="store_true", help="不先清屏")
    sub.add_parser("clear")
    p = sub.add_parser("seg")
    p.add_argument("text")
    p = sub.add_parser("mx")
    p.add_argument("rows", nargs=8)
    p = sub.add_parser("mxcfg")
    p.add_argument("--intensity", type=int, default=1)
    p.add_argument("--rotation", type=int, default=1)
    p.add_argument("--spi", type=int, default=0)
    sub.add_parser("io")
    sub.add_parser("events")
    p = sub.add_parser("led")
    p.add_argument("state", choices=["on", "off"])
    sub.add_parser("reboot")
    args = ap.parse_args()

    with Device(args.port, args.baud) as d:
        if args.cmd == "info":
            print(json.dumps(d.info(), ensure_ascii=False, indent=2))
        elif args.cmd == "stats":
            print(json.dumps(d.stats(), ensure_ascii=False, indent=2))
        elif args.cmd == "ping":
            t = time.perf_counter()
            d.ping()
            print(f"{(time.perf_counter() - t) * 1e3:.3f} ms")
        elif args.cmd == "text":
            if not args.keep:
                d.oled_clear()
            d.oled_text(args.x, args.y, args.text, args.font, flush=True)
        elif args.cmd == "clear":
            d.oled_clear(flush=True)
        elif args.cmd == "seg":
            d.seg_text(args.text, wait=True)
        elif args.cmd == "mx":
            d.mx_frame(bytes(int(r, 16) for r in args.rows), wait=True)
        elif args.cmd == "mxcfg":
            d.mx_config(args.intensity, args.rotation, spi_hz=args.spi)
        elif args.cmd == "io":
            for name, s in d.io_read().items():
                print(f"{name:6s} {'ON ' if s.active else 'OFF'}  次数 {s.count}  最近变化 {s.changed_us / 1e6:.3f}s")
        elif args.cmd == "events":
            print("等待输入事件（Ctrl-C 退出）")
            try:
                while True:
                    ev = d.events.get()
                    print(f"{ev.t_us / 1e6:12.6f}s  {ev.name:6s} {'ON ' if ev.active else 'OFF'}  #{ev.count}")
            except KeyboardInterrupt:
                pass
        elif args.cmd == "led":
            d.led(args.state == "on")
        elif args.cmd == "reboot":
            d.reboot()


if __name__ == "__main__":
    main()
