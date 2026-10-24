"""三屏同时运行：OLED 全速，数码管与点阵可限速，测同时运行时各自的实际刷新率与稳定性。

    python -m wwb.maxdemo                      # 数码管、点阵也全速（压力测试）
    python -m wwb.maxdemo --rate 320           # 数码管、点阵限速 320 帧/s（可目测验证）
    其他：--seconds 30  --mx-batch 128  --no-oled --no-seg --no-mx

OLED：小球 + 扫描条动画，顶部实时显示上一秒三块屏的实际刷新数
限速模式：
  数码管显示帧序号，每帧 +1 —— 跑满 320/s 时百位每秒跳 3.2 下
  点阵显示一根指针，每帧转 1/320 圈 —— 跑满 320/s 时正好一秒一圈
全速模式：数码管计数器、点阵光点逐格扫描（远超器件与人眼能呈现的速度）
每秒在终端打印一行，结束时打印汇总并保存到 results/
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import threading
import time

from PIL import Image, ImageDraw

from .bench import RESULTS_DIR
from .device import DEFAULT_PORT, Device, image_to_frame

DIGITS = (0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F)
OLED_RATE = 100        # 略高于 OLED 极限（约 95fps），保证设备每次推送都有新帧
SEG_FULL_RATE = 2000   # 全速模式：远高于数码管极限，保证每次刷完都有新数据


def seg_counter(n: int) -> bytes:
    return bytes(DIGITS[(n // 10 ** (3 - i)) % 10] for i in range(4))


def mx_dot(i: int) -> bytes:
    rows = bytearray(8)
    rows[(i // 8) % 8] = 0x80 >> (i % 8)
    return bytes(rows)


def mx_hand(angle: float) -> bytes:
    """从中心指向 angle（弧度，0 = 正上方，顺时针）的指针"""
    rows = bytearray(8)
    for k in range(9):
        r = k * 0.5
        x = math.floor(3.5 + r * math.sin(angle) + 0.5)  # 不用 round：它是银行家舍入，指针会歪
        y = math.floor(3.5 - r * math.cos(angle) + 0.5)
        if 0 <= x < 8 and 0 <= y < 8:
            rows[y] |= 0x80 >> x
    return bytes(rows)


def oled_frame(t: float, rates: tuple[float, float, float], target: int) -> bytes:
    img = Image.new("1", (128, 64))
    d = ImageDraw.Draw(img)
    oled, seg, mx = rates
    goal = f"/{target}" if target else ""
    d.text((0, 0), f"OLED {oled:5.1f} fps", fill=1)
    d.text((0, 10), f"SEG  {seg:5.0f}{goal} /s", fill=1)
    d.text((0, 20), f"MX   {mx:5.0f}{goal} /s", fill=1)
    x = int((t % 1.0) * 128)  # 扫描条：每秒扫过全屏宽一次
    d.rectangle((x, 34, x + 3, 63), fill=1)
    bx = abs(((t * 90) % 232) - 116) + 2  # 小球在下半屏弹跳
    by = 36 + abs(((t * 70) % 44) - 22)
    d.ellipse((bx - 5, by - 5, bx + 5, by + 5), fill=1)
    d.rectangle((0, 32, 127, 63), outline=1)
    return image_to_frame(img)


class Pacer:
    """按固定频率给出“该发了”。落后时补发以保住平均速率，但两次之间至少隔半个周期，
    否则补发的两帧挤在一起，设备只保留后一帧（数码管、OLED 都是只保留最新内容）"""

    def __init__(self, rate: float, t0: float):
        self.period = 1 / rate
        self.next = t0

    def due(self, now: float) -> bool:
        if now < self.next:
            return False
        self.next = max(self.next + self.period, now + self.period / 2)
        return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default=DEFAULT_PORT)
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--rate", type=int, default=0, help="数码管与点阵限速（帧/s），0 = 全速")
    ap.add_argument("--mx-batch", type=int, default=128, help="全速模式下每轮发送的点阵帧数")
    ap.add_argument("--no-oled", action="store_true")
    ap.add_argument("--no-seg", action="store_true")
    ap.add_argument("--no-mx", action="store_true")
    args = ap.parse_args()
    paced = args.rate > 0
    sys.setswitchinterval(0.0002)  # 线程间尽快切换，减少节拍抖动

    with Device(args.port) as d:
        d.stats_reset()
        t0 = time.perf_counter()
        end = t0 + args.seconds
        rates = [0.0, 0.0, 0.0]
        history = []

        def oled_loop():
            """OLED：渲染后拆成 4 条 2 页的局部更新发出，最后一条才推送，单次占用串口不超过约 0.6ms"""
            p = Pacer(OLED_RATE, time.perf_counter())
            while (now := time.perf_counter()) < end:
                if not p.due(now):
                    time.sleep(max(0.0, p.next - now - 0.0002))
                    continue
                frame = oled_frame(now - t0, tuple(rates), args.rate)
                for page in range(0, 8, 2):
                    d.oled_blit(page, 0, 2, 128, frame[page * 128:(page + 2) * 128], flush=page == 6)

        def stats_loop():
            prev = d.stats()
            nxt = t0 + 1
            print("  时间   OLED fps  数码管/s   点阵/s   上行KiB/s")
            while nxt < end:
                time.sleep(max(0.0, nxt - time.perf_counter()))
                s = d.stats()
                dt = (s["uptime_us"] - prev["uptime_us"]) / 1e6
                rates[:] = [(s["oled"]["pushes"] - prev["oled"]["pushes"]) / dt,
                            (s["seg"]["updates"] - prev["seg"]["updates"]) / dt,
                            (s["mx"]["frames"] - prev["mx"]["frames"]) / dt]
                kib = (s["usb"]["rx_bytes"] - prev["usb"]["rx_bytes"]) / dt / 1024
                history.append({"oled_fps": rates[0], "seg_s": rates[1], "mx_s": rates[2], "upload_KiB_s": kib})
                print(f"{nxt - t0:6.1f}s  {rates[0]:8.1f}  {rates[1]:8.1f}  {rates[2]:8.1f}  {kib:9.1f}", flush=True)
                prev = s
                nxt += 1

        threads = [threading.Thread(target=stats_loop, daemon=True)]
        if not args.no_oled:
            threads.append(threading.Thread(target=oled_loop, daemon=True))
        for t in threads:
            t.start()

        # 本线程：数码管 + 点阵
        seg_n = mx_n = 0
        seg_p = Pacer(args.rate if paced else SEG_FULL_RATE, t0)
        mx_p = Pacer(args.rate, t0) if paced else None
        while (now := time.perf_counter()) < end:
            if paced:
                if not args.no_seg and seg_p.due(now):
                    seg_n += 1
                    d.seg_raw(seg_counter(seg_n))
                if not args.no_mx and mx_p.due(now):
                    mx_n += 1
                    d.mx_frame(mx_hand(2 * math.pi * mx_n / args.rate))
                wait = min(seg_p.next, mx_p.next) - time.perf_counter()
                if wait > 0.0004:
                    time.sleep(wait - 0.0003)
                else:
                    time.sleep(0)  # 让出 GIL
            else:
                with d.batch():
                    for k in range(1 if args.no_mx else args.mx_batch):
                        # 数码管穿插在点阵帧之间发，批量再大也能按节奏喂到
                        if k % 8 == 0 and not args.no_seg and seg_p.due(time.perf_counter()):
                            seg_n += 1
                            d.seg_raw(seg_counter(seg_n))
                        if not args.no_mx:
                            mx_n += 1
                            d.mx_frame(mx_dot(mx_n))
                if args.no_mx:
                    time.sleep(0.0002)
        for t in threads:
            t.join()

        s = d.stats()
        steady = history[2:] or history  # 去掉起步的头两秒
        summary = {k: statistics.mean(h[k] for h in steady) for k in steady[0]}
        for k in ("seg_s", "mx_s"):
            summary[k + "_min"] = min(h[k] for h in steady)
            summary[k + "_max"] = max(h[k] for h in steady)
        summary.update(rate=args.rate, seg_sent=seg_n, seg_updates=s["seg"]["updates"], mx_sent=mx_n,
                       mx_frames=s["mx"]["frames"], seg_ack_fails=s["seg"]["ack_fails"],
                       oled_errors=s["oled"]["errors"], usb_crc_errors=s["usb"]["crc_errors"])
        print("\n稳定段平均：OLED {oled_fps:.1f} fps | 数码管 {seg_s:.1f}/s（{seg_s_min:.0f}–{seg_s_max:.0f}）"
              " | 点阵 {mx_s:.1f}/s（{mx_s_min:.0f}–{mx_s_max:.0f}）| 上行 {upload_KiB_s:.0f} KiB/s".format(**summary))
        print(f"发出 / 实际刷新：数码管 {seg_n} / {s['seg']['updates']}   点阵 {mx_n} / {s['mx']['frames']}")
        print(f"错误：数码管 ACK {summary['seg_ack_fails']}  OLED {summary['oled_errors']}  USB CRC {summary['usb_crc_errors']}")

        RESULTS_DIR.mkdir(exist_ok=True)
        path = RESULTS_DIR / f"maxdemo_{time.strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps({"summary": summary, "per_second": history}, ensure_ascii=False, indent=2))
        print(f"已保存：{path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
