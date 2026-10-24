"""网页模拟器的 Python 桥：提供模拟器网页，并把 Python 程序的协议字节转给网页里的模拟设备。

    python -m wwb.sim                 # 打开 http://127.0.0.1:8765
    python -m wwb.showcase --port sim # 另开终端：任何 wwb 程序加 --port sim / Device("sim") 即可

    Python 程序 ──TCP 8766──▶ 本桥 ──WebSocket /ws──▶ 网页（模拟器按固件逐条执行命令）
               ◀── 回复 / 开关事件 ───────────────────

桥只转发字节，不解析命令；为了与真机行为接近，程序到网页方向按 USB 实测上行速度（约 460 KiB/s）限速。
没有打开网页时，桥暂停读取程序发来的数据（程序的写入会阻塞，请求会超时）。
同一时刻只有一个网页充当设备，新打开的页面会接管；可以同时连多个程序（回复广播给所有程序）。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import webbrowser
from http import HTTPStatus
from pathlib import Path

from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

WEB = Path(__file__).resolve().parents[2] / "web"
USB_UPLOAD = 460 * 1024  # 真机 USB 上行实测上限，字节/s


class Bridge:
    def __init__(self, rate: float):
        self.rate = rate
        self.browser: ServerConnection | None = None
        self.page_ready = asyncio.Event()
        self.clients: set[asyncio.StreamWriter] = set()

    # ------------------------------------------------------------ 网页

    def serve_file(self, conn: ServerConnection, request: Request) -> Response | None:
        path = request.path.split("?", 1)[0]
        if path == "/ws":
            return None  # 交给 WebSocket 握手
        f = (WEB / (path.lstrip("/") or "index.html")).resolve()
        if not f.is_relative_to(WEB) or not f.is_file():
            return conn.respond(HTTPStatus.NOT_FOUND, "not found\n")
        body = f.read_bytes()
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        headers = Headers([("Content-Type", ctype), ("Content-Length", str(len(body))), ("Cache-Control", "no-cache")])
        return Response(200, "OK", headers, body)

    async def notify(self, note: str | None = None):
        if self.browser:
            try:
                await self.browser.send(json.dumps({"clients": len(self.clients), "note": note}))
            except ConnectionClosed:
                pass

    async def on_browser(self, ws: ServerConnection):
        old, self.browser = self.browser, ws
        self.page_ready.set()
        if old:
            await old.close(4000, "另一个页面已接管")
        print(f"网页已连接（{ws.remote_address[0]}）", flush=True)
        await self.notify()
        try:
            async for msg in ws:
                if isinstance(msg, bytes):
                    for w in list(self.clients):
                        w.write(msg)
        except ConnectionClosed:
            pass
        finally:
            if self.browser is ws:
                self.browser = None
                self.page_ready.clear()
                print("网页已断开", flush=True)

    # ------------------------------------------------------------ Python 程序

    async def on_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.clients.add(writer)
        print(f"程序已连接（共 {len(self.clients)} 个）", flush=True)
        await self.notify("Python 程序已连接")
        loop = asyncio.get_running_loop()
        buf = bytearray()
        next_t = loop.time()
        try:
            while data := await reader.read(4096):
                buf += data
                end = buf.rfind(0)
                if end < 0:
                    continue
                chunk = bytes(buf[:end + 1])  # 只转发完整的帧，多个程序的帧不会交错
                del buf[:end + 1]
                if not self.browser:
                    # 没有网页时先不读，程序那边写满缓冲后会阻塞，等网页打开再继续
                    print("等待模拟器网页打开……", flush=True)
                    await self.page_ready.wait()
                try:
                    await self.browser.send(chunk)
                except (ConnectionClosed, AttributeError):
                    pass
                if self.rate:
                    next_t = max(next_t, loop.time()) + len(chunk) / self.rate
                    if next_t - loop.time() > 0.002:
                        await asyncio.sleep(next_t - loop.time())
        except (ConnectionError, OSError):
            pass
        finally:
            self.clients.discard(writer)
            writer.close()
            print(f"程序已断开（剩 {len(self.clients)} 个）", flush=True)
            await self.notify("Python 程序已断开")


async def run(args):
    bridge = Bridge(0 if args.no_limit else USB_UPLOAD)
    tcp = await asyncio.start_server(bridge.on_client, args.host, args.tcp_port)
    async with serve(bridge.on_browser, args.host, args.http_port, process_request=bridge.serve_file,
                     max_size=None, compression=None):
        url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '') else args.host}:{args.http_port}/"
        print(f"模拟器网页：{url}")
        print(f"程序连接：Device(\"sim\") 或 --port sim（TCP {args.host}:{args.tcp_port}）")
        print("Ctrl+C 退出", flush=True)
        if args.open:
            webbrowser.open(url)
        async with tcp:
            await tcp.serve_forever()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1", help="监听地址；0.0.0.0 可让局域网里的其他设备打开网页")
    ap.add_argument("--http-port", type=int, default=8765)
    ap.add_argument("--tcp-port", type=int, default=8766)
    ap.add_argument("--open", action="store_true", help="启动后用浏览器打开")
    ap.add_argument("--no-limit", action="store_true", help="不按 USB 上行速度限速")
    args = ap.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
