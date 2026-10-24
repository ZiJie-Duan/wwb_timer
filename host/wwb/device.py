"""wwb 设备的上位机 API。USB 与 UART 在上位机看来都是串口，用法完全相同：

    from wwb import Device
    with Device("/dev/ttyACM0") as d:          # USB
        d.seg_text("12:34")
    with Device("/dev/ttyUSB0", baud=921600) as d:   # UART（GPIO20/21）
        ...
"""
from __future__ import annotations

import contextlib
import json
import queue
import struct
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable

import serial

from .protocol import BenchTarget, Err, Flag, Frame, Op, decode_frame, encode_frame


class DeviceError(RuntimeError):
    def __init__(self, op: int, code: int):
        name = Err(code).name if code in Err._value2member_map_ else str(code)
        super().__init__(f"{Op(op).name if op in Op._value2member_map_ else hex(op)}: {name}")
        self.op, self.code = op, code


@dataclass
class InputEvent:
    input: int        # 0 = 开关，1 = BOOT 键
    active: bool      # 开关：开启（闭合）；BOOT：按下
    count: int
    t_us: int         # 设备时刻（esp_timer µs）

    @property
    def name(self) -> str:
        return ("switch", "boot")[self.input] if self.input < 2 else str(self.input)


@dataclass
class InputState:
    active: bool
    count: int
    changed_us: int


class _Pending:
    __slots__ = ("event", "frame")

    def __init__(self):
        self.event = threading.Event()
        self.frame: Frame | None = None


def image_to_frame(img) -> bytes:
    """PIL 图像（会转成 128x64 单色）→ OLED 帧缓冲（8 页 × 128 列，每字节纵向 8 像素，LSB 在上）"""
    if img.size != (128, 64) or img.mode != "1":
        img = img.convert("1").resize((128, 64))
    try:
        import numpy as np
    except ImportError:
        px = img.load()
        out = bytearray(1024)
        for page in range(8):
            for x in range(128):
                v = 0
                for bit in range(8):
                    if px[x, page * 8 + bit]:
                        v |= 1 << bit
                out[page * 128 + x] = v
        return bytes(out)
    # (64,128) → (8 页, 8 行, 128 列)，按行加权 1<<行 合成每列一个字节
    a = np.asarray(img, dtype=np.uint8).reshape(8, 8, 128)
    return (a * (1 << np.arange(8, dtype=np.uint8))[None, :, None]).sum(axis=1, dtype=np.uint8).tobytes()


class Device:
    def __init__(self, port: str = "/dev/ttyACM0", baud: int = 921600, timeout: float = 2.0):
        self.timeout = timeout
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baud
        self.ser.timeout = 0.05
        # USB-Serial/JTAG：RTS=1 且 DTR=0 会复位芯片，保持两线同为有效
        self.ser.dtr = True
        self.ser.rts = True
        self.ser.open()
        self._no_hupcl()

        self._seq = 0
        self._seq_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._batch: bytearray | None = None
        self._pending: dict[int, _Pending] = {}
        self._pending_lock = threading.Lock()
        self._input_callbacks: list[Callable[[InputEvent], None]] = []
        self.events: queue.Queue[InputEvent] = queue.Queue()
        self._source_q: queue.Queue[Frame] = queue.Queue()
        self.rx_errors = 0
        self._stop = False
        self._reader = threading.Thread(target=self._read_loop, name="wwb-rx", daemon=True)
        self._reader.start()

    # ------------------------------------------------------------ 连接

    def _no_hupcl(self):
        """关闭串口时不拉低 DTR/RTS，避免 USB-Serial/JTAG 复位芯片"""
        if sys.platform.startswith("linux"):
            import termios
            attrs = termios.tcgetattr(self.ser.fd)
            attrs[2] &= ~termios.HUPCL
            termios.tcsetattr(self.ser.fd, termios.TCSANOW, attrs)

    def close(self):
        self._stop = True
        self._reader.join(timeout=1)
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _read_loop(self):
        buf = bytearray()
        while not self._stop:
            try:
                chunk = self.ser.read(self.ser.in_waiting or 1)
            except (serial.SerialException, OSError):
                if self._stop:
                    return
                time.sleep(0.1)
                continue
            if not chunk:
                continue
            buf += chunk
            while True:
                end = buf.find(0)
                if end < 0:
                    break
                encoded = bytes(buf[:end])
                del buf[:end + 1]
                if not encoded:
                    continue
                try:
                    frame = decode_frame(encoded)
                except ValueError:
                    self.rx_errors += 1  # 开机日志等非协议数据
                    continue
                self._route(frame)

    def _route(self, f: Frame):
        if f.flags & Flag.EVENT:
            if f.op == Op.EV_INPUT:
                inp, active, count, t = struct.unpack_from("<BBIQ", f.payload)
                ev = InputEvent(inp, bool(active), count, t)
                self.events.put(ev)
                for cb in list(self._input_callbacks):
                    cb(ev)
            elif f.op == Op.SOURCE:
                self._source_q.put(f)
            return
        if f.flags & Flag.RESP:
            with self._pending_lock:
                p = self._pending.pop(f.seq, None)
            if p:
                p.frame = f
                p.event.set()

    def _next_seq(self) -> int:
        with self._seq_lock:
            self._seq = (self._seq + 1) & 0xFFFF
            return self._seq

    # ------------------------------------------------------------ 基础收发

    def send(self, op: int, payload: bytes = b"", flags: int = Flag.NOREPLY) -> int:
        """发出请求不等回复（默认带 NOREPLY）。用于高速推流"""
        seq = self._next_seq()
        data = encode_frame(op, flags, seq, payload)
        with self._write_lock:
            if self._batch is not None:
                self._batch += data
            else:
                self.ser.write(data)
        return seq

    @contextlib.contextmanager
    def batch(self):
        """块内的 send() 先攒起来，退出时一次写出（多条命令共用 USB 传输）。块内不要调用 request()"""
        with self._write_lock:
            self._batch = bytearray()
        try:
            yield self
        finally:
            with self._write_lock:
                data, self._batch = self._batch, None
                if data:
                    self.ser.write(data)

    def request(self, op: int, payload: bytes = b"", flags: int = 0, timeout: float | None = None) -> bytes:
        """发出请求并等待回复，返回回复 payload；设备报错时抛 DeviceError"""
        seq = self._next_seq()
        p = _Pending()
        with self._pending_lock:
            self._pending[seq] = p
        data = encode_frame(op, flags & ~Flag.NOREPLY, seq, payload)
        with self._write_lock:
            self.ser.write(data)
        if not p.event.wait(self.timeout if timeout is None else timeout):
            with self._pending_lock:
                self._pending.pop(seq, None)
            raise TimeoutError(f"{Op(op).name}: no reply")
        f = p.frame
        if f.flags & Flag.ERR:
            raise DeviceError(op, f.payload[0] if f.payload else 0)
        return f.payload

    def on_input(self, callback: Callable[[InputEvent], None]):
        """注册输入事件回调（在接收线程中调用，勿阻塞）"""
        self._input_callbacks.append(callback)

    # ------------------------------------------------------------ 系统

    def ping(self, payload: bytes = b"") -> bytes:
        return self.request(Op.PING, payload)

    def info(self) -> dict:
        return json.loads(self.request(Op.INFO))

    def stats(self) -> dict:
        return json.loads(self.request(Op.STATS))

    def stats_reset(self):
        self.request(Op.STATS_RESET)

    def time_us(self) -> int:
        return struct.unpack("<Q", self.request(Op.TIME))[0]

    def reboot(self):
        self.request(Op.REBOOT)

    def set_uart_baud(self, baud: int):
        """修改设备 UART 波特率（若当前就走 UART，之后需用新波特率重新打开）"""
        self.request(Op.UART_BAUD, struct.pack("<I", baud))

    def subscribe(self, inputs: bool = True):
        self.request(Op.SUBSCRIBE, bytes([1 if inputs else 0]))

    def sink(self, payload: bytes, reply: bool = False) -> int | None:
        if reply:
            return struct.unpack("<I", self.request(Op.SINK, payload))[0]
        self.send(Op.SINK, payload)
        return None

    def source(self, total: int, chunk: int = 1024, timeout: float = 30) -> tuple[int, float, float]:
        """让设备发回 total 字节，返回 (收到字节, 上位机耗时 s, 设备耗时 s)"""
        while not self._source_q.empty():
            self._source_q.get_nowait()
        t0 = time.perf_counter()
        r = self.request(Op.SOURCE, struct.pack("<IH", total, chunk), timeout=timeout)
        host_s = time.perf_counter() - t0
        got = 0
        while not self._source_q.empty():
            got += len(self._source_q.get_nowait().payload)
        sent, dev_us = struct.unpack("<II", r)
        return got, host_s, dev_us / 1e6

    def bench(self, target: BenchTarget, count: int, *args) -> dict:
        """设备端外设自测。OLED: (i2c_hz)；SEG: (rise_us, fall_us[, dio_rise_us, ack_settle_us])；MX: (spi_hz)"""
        payload = struct.pack("<BH", target, count)
        if target == BenchTarget.OLED:
            payload += struct.pack("<I", args[0] if args else 0)
        elif target == BenchTarget.SEG:
            payload += bytes([args[0], args[1], args[2] if len(args) > 2 else args[0], args[3] if len(args) > 3 else 0])
        elif target == BenchTarget.MX:
            payload += struct.pack("<I", args[0])
        return json.loads(self.request(Op.BENCH, payload, timeout=60))

    # ------------------------------------------------------------ 输入 / 灯

    def io_read(self) -> dict[str, InputState]:
        r = self.request(Op.IO_READ)
        out = {}
        for i, name in enumerate(("switch", "boot")):
            active, count, t = struct.unpack_from("<BIQ", r, i * 13)
            out[name] = InputState(bool(active), count, t)
        return out

    def io_config(self, debounce_us: int):
        self.request(Op.IO_CONFIG, struct.pack("<I", debounce_us))

    def led(self, on: bool):
        self.request(Op.LED, bytes([1 if on else 0]))

    # ------------------------------------------------------------ OLED

    def _oled(self, op: int, payload: bytes, flush: bool, wait: bool):
        flags = Flag.FLUSH if flush else 0
        if wait:
            self.request(op, payload, flags)
        else:
            self.send(op, payload, flags | Flag.NOREPLY)

    def oled_frame(self, frame, flush: bool = True, wait: bool = False):
        """整帧：1024 字节帧缓冲或 PIL 图像"""
        data = frame if isinstance(frame, (bytes, bytearray, memoryview)) else image_to_frame(frame)
        self._oled(Op.OLED_FRAME, bytes(data), flush, wait)

    def oled_blit(self, page: int, col: int, pages: int, cols: int, data: bytes, flush: bool = True,
                  wait: bool = False):
        self._oled(Op.OLED_BLIT, bytes([page, col, pages, cols]) + bytes(data), flush, wait)

    def oled_text(self, x: int, y: int, text: str, font: int = 0, color: int = 1, flush: bool = False,
                  wait: bool = True):
        """y 为基线；color 0 清除 / 1 点亮 / 2 反色"""
        self._oled(Op.OLED_TEXT, struct.pack("<hhBB", x, y, font, color) + text.encode(), flush, wait)

    def oled_clear(self, color: int = 0, flush: bool = False, wait: bool = True):
        self._oled(Op.OLED_CLEAR, bytes([color]), flush, wait)

    def oled_rect(self, x: int, y: int, w: int, h: int, mode: int = 1, flush: bool = False, wait: bool = True):
        """mode 0 清除填充 / 1 填充 / 2 边框 / 3 反色"""
        self._oled(Op.OLED_RECT, struct.pack("<hhhhB", x, y, w, h, mode), flush, wait)

    def oled_flush(self, wait: bool = True):
        self._oled(Op.OLED_FLUSH, b"", False, wait)

    def oled_cmd(self, *cmds: int):
        """直接发 SSD1306 命令，如对比度 oled_cmd(0x81, 0x7F)、反色 oled_cmd(0xA7)"""
        self.request(Op.OLED_CMD, bytes(cmds))

    def oled_contrast(self, value: int):
        self.oled_cmd(0x81, value & 0xFF)

    def oled_config(self, i2c_hz: int):
        self.request(Op.OLED_CONFIG, struct.pack("<I", i2c_hz))

    # ------------------------------------------------------------ 数码管

    def seg_raw(self, segs: bytes, wait: bool = False):
        """4 字节段码（bit0=a … bit6=g，第 2 位 bit7 = 冒号）"""
        (self.request if wait else self.send)(Op.SEG_RAW, bytes(segs))

    def seg_text(self, text: str, wait: bool = False):
        (self.request if wait else self.send)(Op.SEG_TEXT, text.encode())

    def seg_config(self, brightness: int = 3, on: bool = True, rise_us: int = 50, fall_us: int = 2,
                   dio_rise_us: int | None = None):
        """rise_us：CLK 上升等待；dio_rise_us：DIO 上升等待（默认同 rise_us）；fall_us：下降等待"""
        dio = rise_us if dio_rise_us is None else dio_rise_us
        self.request(Op.SEG_CONFIG, bytes([brightness, 1 if on else 0, rise_us, fall_us, dio]))

    # ------------------------------------------------------------ 点阵

    def mx_frame(self, rows: bytes, wait: bool = False):
        """8 字节，逻辑方向：行 0 在上，bit7 在左"""
        (self.request if wait else self.send)(Op.MX_FRAME, bytes(rows))

    def mx_config(self, intensity: int = 1, rotation: int = 1, test: bool = False, shutdown: bool = False,
                  spi_hz: int = 0):
        """rotation：顺时针 ×90°（当前安装方向用 1）；spi_hz=0 保持不变（默认 10MHz）"""
        flags = (1 if test else 0) | (2 if shutdown else 0)
        self.request(Op.MX_CONFIG, bytes([intensity, rotation, flags]) + struct.pack("<I", spi_hz))

    def mx_raw(self, *pairs: tuple[int, int]):
        self.request(Op.MX_RAW, bytes(b for p in pairs for b in p))
