"""wwb 串口协议的上位机实现，与 firmware/src/proto.h 一一对应。完整说明见 docs/protocol.md

线上：COBS(帧) + 0x00
帧：  op u8 | flags u8 | seq u16 | payload | crc16 u16（小端，CRC-16/CCITT-FALSE 覆盖 op..payload）
"""
from __future__ import annotations

import binascii
import struct
from dataclasses import dataclass
from enum import IntEnum, IntFlag

VERSION = 1
MAX_PAYLOAD = 1100


class Flag(IntFlag):
    NOREPLY = 0x01
    RESP = 0x02
    EVENT = 0x04
    ERR = 0x08
    FLUSH = 0x10


class Op(IntEnum):
    PING = 0x01
    INFO = 0x02
    SINK = 0x03
    SOURCE = 0x04
    STATS = 0x05
    STATS_RESET = 0x06
    REBOOT = 0x07
    UART_BAUD = 0x08
    SUBSCRIBE = 0x09
    BENCH = 0x0A
    TIME = 0x0B
    RELEASE = 0x0C

    IO_READ = 0x10
    IO_CONFIG = 0x11
    LED = 0x12
    EV_INPUT = 0x18

    OLED_FRAME = 0x20
    OLED_BLIT = 0x21
    OLED_TEXT = 0x22
    OLED_CLEAR = 0x23
    OLED_RECT = 0x24
    OLED_CMD = 0x25
    OLED_CONFIG = 0x26
    OLED_FLUSH = 0x2F

    SEG_RAW = 0x30
    SEG_TEXT = 0x31
    SEG_CONFIG = 0x32

    MX_FRAME = 0x40
    MX_CONFIG = 0x41
    MX_RAW = 0x42


class Err(IntEnum):
    UNKNOWN_OP = 1
    BAD_LEN = 2
    BAD_ARG = 3
    HW = 4


class BenchTarget(IntEnum):
    OLED = 1
    SEG = 2
    MX = 3


class Font(IntEnum):
    F6X10 = 0
    F9X15 = 1
    LOGISOSO16 = 2
    LOGISOSO24_NUM = 3
    LOGISOSO32_NUM = 4
    WQY12_CN = 5


def crc16(data: bytes) -> int:
    """CRC-16/CCITT-FALSE（多项式 0x1021，初值 0xFFFF）；crc_hqx 是同一算法的 C 实现"""
    return binascii.crc_hqx(data, 0xFFFF)


def cobs_encode(data: bytes) -> bytes:
    out = bytearray()
    for block in data.split(b"\x00"):
        while len(block) >= 254:
            out.append(0xFF)
            out += block[:254]
            block = block[254:]
        out.append(len(block) + 1)
        out += block
    return bytes(out)


def cobs_decode(data: bytes) -> bytes:
    out = bytearray()
    i, n = 0, len(data)
    while i < n:
        code = data[i]
        i += 1
        if code == 0 or i + code - 1 > n:
            raise ValueError("bad COBS block")
        out += data[i:i + code - 1]
        i += code - 1
        if code != 0xFF and i < n:
            out.append(0)
    return bytes(out)


@dataclass
class Frame:
    op: int
    flags: int
    seq: int
    payload: bytes


def encode_frame(op: int, flags: int, seq: int, payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload {len(payload)} > {MAX_PAYLOAD}")
    body = struct.pack("<BBH", op, flags, seq & 0xFFFF) + payload
    body += struct.pack("<H", crc16(body))
    return cobs_encode(body) + b"\x00"


def decode_frame(encoded: bytes) -> Frame:
    """encoded 为两个 0x00 之间的内容。格式或 CRC 错误时抛 ValueError"""
    raw = cobs_decode(encoded)
    if len(raw) < 6:
        raise ValueError("frame too short")
    if crc16(raw[:-2]) != struct.unpack_from("<H", raw, len(raw) - 2)[0]:
        raise ValueError("crc mismatch")
    op, flags, seq = struct.unpack_from("<BBH", raw)
    return Frame(op, flags, seq, raw[4:-2])
