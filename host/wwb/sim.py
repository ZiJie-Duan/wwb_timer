"""网页模拟器的 Python 桥：提供模拟器网页，管理要测试的程序，并把程序的协议字节转给网页里的模拟设备。

    python -m wwb.sim                 # 打开 http://127.0.0.1:8765，在网页右侧选程序运行

    Python 程序 ──TCP 8766──▶ 本桥 ──WebSocket /ws──▶ 网页（模拟器按固件逐条执行命令）
               ◀── 回复 / 开关事件 ───────────────────

程序列表：apps/ 下每个带 __main__.py 的目录（标题与说明取自 __init__.py 的文档字符串），加上 wwb 自带的演示。
网页上点“运行”时，桥以 python -m apps.<名字> --port sim:… 启动它，输出转到网页；
网页关闭时程序暂停，网页重新打开（或刷新）后从头运行，因为新网页相当于一台刚开机的设备；
程序目录或 host/wwb 里的文件有改动时自动重启（可在网页上关掉）。也可以在终端自己运行程序，加 --port sim 即可。

桥只转发协议字节，不解析命令；程序到网页方向按 USB 实测上行速度（约 460 KiB/s）限速。
没有打开网页时，桥暂停读取程序发来的数据（程序的写入会阻塞，请求会超时）。
同一时刻只有一个网页充当设备，新打开的页面会接管。
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import collections
import json
import mimetypes
import os
import signal
import sys
import webbrowser
from http import HTTPStatus
from pathlib import Path

from websockets.asyncio.server import ServerConnection, serve
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
APPS = ROOT / "apps"
LIB = ROOT / "host" / "wwb"
USB_UPLOAD = 460 * 1024  # 真机 USB 上行实测上限，字节/s

BUILTIN = [
    {"id": "wwb.showcase", "title": "赛博风演示",
     "desc": "七个场景循环：开机自检、星空跃迁、四维超立方体、代码雨、等离子、频谱、故障标志。拨开关切场景，按 BOOT 反色。",
     "args": [], "dir": LIB},
    {"id": "wwb.maxdemo", "title": "三屏刷新极限",
     "desc": "OLED 全速，数码管与点阵各 320 帧/s：数码管是帧号，点阵指针一秒一圈。OLED 顶部显示实际刷新数。",
     "args": ["--rate", "320", "--seconds", "86400"], "dir": LIB},
]


def discover() -> list[dict]:
    apps = []
    if APPS.is_dir():
        for p in sorted(APPS.iterdir()):
            if not (p / "__main__.py").is_file():
                continue
            doc = ""
            init = p / "__init__.py"
            if init.is_file():
                try:
                    doc = ast.get_docstring(ast.parse(init.read_text(encoding="utf-8"))) or ""
                except SyntaxError:
                    doc = "（__init__.py 有语法错误）"
            title, _, desc = doc.strip().partition("\n")
            apps.append({"id": f"apps.{p.name}", "title": title.strip() or p.name, "desc": desc.strip(), "args": [], "dir": p})
    return apps + BUILTIN


def snapshot(dirs) -> dict[str, float]:
    """目录下所有文件的修改时间，用来发现改动"""
    out = {}
    for d in dirs:
        for root, subdirs, files in os.walk(d):
            subdirs[:] = [s for s in subdirs if s != "__pycache__" and not s.startswith(".")]
            for f in files:
                p = os.path.join(root, f)
                try:
                    out[p] = os.stat(p).st_mtime
                except OSError:
                    pass
    return out


class Runner:
    """一次只运行一个程序"""

    def __init__(self, bridge: "Bridge", tcp_port: int):
        self.bridge = bridge
        self.tcp_port = tcp_port
        self.apps = discover()
        self.proc: asyncio.subprocess.Process | None = None
        self.app: dict | None = None   # 最近运行的程序（结束后仍保留，改动时可以重新拉起）
        self.auto = True
        self.resume = False            # 网页关闭时停掉的程序，网页回来后重新运行
        self.stamp: dict = {}
        self.lines: collections.deque = collections.deque(maxlen=300)
        # 启动 / 停止串行执行：否则两次启动交错（点“运行”的同时文件改动触发重启）会漏停旧程序，
        # 两个程序同时画同一块屏，画面来回闪
        self.lock = asyncio.Lock()

    def find(self, app_id: str) -> dict | None:
        return next((a for a in self.apps if a["id"] == app_id), None)

    def state(self) -> dict:
        return {"type": "state", "running": self.app["id"] if self.proc and self.app else None,
                "selected": self.app["id"] if self.app else None, "auto": self.auto}

    def app_list(self) -> dict:
        return {"type": "apps", "apps": [{k: a[k] for k in ("id", "title", "desc")} for a in self.apps]}

    async def out(self, line: str, kind: str = "out"):
        self.lines.append((line, kind))
        await self.bridge.send({"type": "out", "line": line, "kind": kind})

    async def start(self, app: dict, reason: str = ""):
        async with self.lock:
            await self._start(app, reason)

    async def _start(self, app: dict, reason: str):
        await self._stop(quiet=True)
        self.app = app
        self.stamp = snapshot([app["dir"], LIB])
        cmd = [sys.executable, "-u", "-m", app["id"], "--port", f"sim:127.0.0.1:{self.tcp_port}", *app["args"]]
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONPATH": os.pathsep.join([str(ROOT), os.environ.get("PYTHONPATH", "")])}
        proc = await asyncio.create_subprocess_exec(*cmd, cwd=ROOT, env=env, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.STDOUT, start_new_session=True)
        self.proc = proc
        print(f"运行 {app['id']}（pid {proc.pid}）{reason}", flush=True)
        await self.out(f"▶ {app['title']}（{app['id']}）{reason}", "info")
        await self.bridge.send(self.state())
        asyncio.create_task(self.pump(proc))

    async def pump(self, proc):
        async for raw in proc.stdout:
            await self.out(raw.decode(errors="replace").rstrip("\r\n"))
        code = await proc.wait()
        if self.proc is proc:  # 自己结束的（不是被停止或重启）
            self.proc = None
            await self.out(f"程序结束，退出码 {code}", "info" if code == 0 else "err")
            await self.bridge.send(self.state())

    async def stop(self, quiet: bool = False):
        async with self.lock:
            await self._stop(quiet)

    async def _stop(self, quiet: bool):
        proc, self.proc = self.proc, None
        if not proc or proc.returncode is not None:
            return
        proc.send_signal(signal.SIGINT)  # wwb.app 收到后正常关闭设备
        try:
            await asyncio.wait_for(proc.wait(), 2)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        if not quiet:
            await self.out("■ 已停止", "info")
            await self.bridge.send(self.state())

    # 刷新或重新打开网页等于换了一台刚开机的设备，程序也要从头运行，否则它会等不到回复而超时
    async def page_gone(self):
        if self.proc:
            self.resume = True  # 先置位：刷新时新网页可能在旧程序停完之前就连上
            print("网页关闭，程序已暂停", flush=True)
            await self.stop(quiet=True)

    async def page_back(self):
        if self.app and (self.resume or self.proc):
            self.resume = False
            await self.start(self.app, "（网页已连接，从头运行）")

    async def control(self, msg: dict):
        cmd = msg.get("cmd")
        self.resume = False
        if cmd == "run":
            app = self.find(msg.get("id", ""))
            if app:
                await self.start(app)
        elif cmd == "restart" and self.app:
            await self.start(self.app, "（重启）")
        elif cmd == "stop":
            await self.stop()
        elif cmd == "auto":
            self.auto = bool(msg.get("on"))
            await self.bridge.send(self.state())

    async def watch(self):
        """每 0.5 秒检查一次：程序列表有无变化；当前程序的文件改了就重启"""
        while True:
            await asyncio.sleep(0.5)
            apps = discover()
            if [(a["id"], a["title"], a["desc"]) for a in apps] != [(a["id"], a["title"], a["desc"]) for a in self.apps]:
                self.apps = apps
                await self.bridge.send(self.app_list())
            if self.app and self.auto:
                now = snapshot([self.app["dir"], LIB])
                if now != self.stamp:
                    changed = sorted({p for p in now.keys() | self.stamp.keys() if now.get(p) != self.stamp.get(p)})
                    self.stamp = now
                    await asyncio.sleep(0.2)  # 等编辑器把一批文件写完
                    app = self.find(self.app["id"]) or self.app
                    names = "、".join(os.path.relpath(p, ROOT) for p in changed[:3]) + ("……" if len(changed) > 3 else "")
                    await self.start(app, f"（{names} 有改动，自动重启）")


class Bridge:
    def __init__(self, rate: float):
        self.rate = rate
        self.browser: ServerConnection | None = None
        self.page_ready = asyncio.Event()
        self.clients: set[asyncio.StreamWriter] = set()
        self.runner: Runner | None = None

    async def send(self, msg: dict):
        if self.browser:
            try:
                await self.browser.send(json.dumps(msg, ensure_ascii=False))
            except ConnectionClosed:
                pass

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

    async def on_browser(self, ws: ServerConnection):
        old, self.browser = self.browser, ws
        self.page_ready.set()
        if old:
            await old.close(4000, "另一个页面已接管")
        print(f"网页已连接（{ws.remote_address[0]}）", flush=True)
        r = self.runner
        await self.send(r.app_list())
        await self.send(r.state())
        for line, kind in r.lines:
            await self.send({"type": "out", "line": line, "kind": kind, "replay": True})
        await self.send({"type": "clients", "n": len(self.clients)})
        await r.page_back()
        try:
            async for msg in ws:
                if isinstance(msg, bytes):
                    for w in list(self.clients):
                        w.write(msg)
                else:
                    await r.control(json.loads(msg))
        except ConnectionClosed:
            pass
        finally:
            if self.browser is ws:
                self.browser = None
                self.page_ready.clear()
                print("网页已断开", flush=True)
                await r.page_gone()

    # ------------------------------------------------------------ 程序的协议连接

    async def on_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.clients.add(writer)
        await self.send({"type": "clients", "n": len(self.clients)})
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
            await self.send({"type": "clients", "n": len(self.clients)})


async def run(args):
    bridge = Bridge(0 if args.no_limit else USB_UPLOAD)
    bridge.runner = Runner(bridge, args.tcp_port)
    tcp = await asyncio.start_server(bridge.on_client, args.host, args.tcp_port)
    async with serve(bridge.on_browser, args.host, args.http_port, process_request=bridge.serve_file,
                     max_size=None, compression=None):
        url = f"http://{'127.0.0.1' if args.host in ('0.0.0.0', '') else args.host}:{args.http_port}/"
        print(f"模拟器网页：{url}")
        print(f"程序：{len(bridge.runner.apps)} 个（apps/ 与 wwb 自带演示），在网页上选择运行")
        print(f"终端运行的程序加 --port sim 也会连到这里（TCP {args.host}:{args.tcp_port}）")
        print("Ctrl+C 退出", flush=True)
        if args.open:
            webbrowser.open(url)
        watcher = asyncio.create_task(bridge.runner.watch())
        try:
            async with tcp:
                await tcp.serve_forever()
        finally:
            watcher.cancel()
            await bridge.runner.stop(quiet=True)


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
