// wwb 串口协议的 JS 实现，与 firmware/src/proto.h、host/wwb/protocol.py 一一对应。说明见 docs/protocol.md
//
// 线上：COBS(帧) + 0x00
// 帧：  op u8 | flags u8 | seq u16 | payload | crc16 u16（小端，CRC-16/CCITT-FALSE 覆盖 op..payload）
(function () {
  const WWB = (window.WWB = window.WWB || {});

  const Flag = { NOREPLY: 0x01, RESP: 0x02, EVENT: 0x04, ERR: 0x08, FLUSH: 0x10 };
  const Op = {
    PING: 0x01, INFO: 0x02, SINK: 0x03, SOURCE: 0x04, STATS: 0x05, STATS_RESET: 0x06, REBOOT: 0x07,
    UART_BAUD: 0x08, SUBSCRIBE: 0x09, BENCH: 0x0a, TIME: 0x0b, RELEASE: 0x0c, CONNECT: 0x0d,
    IO_READ: 0x10, IO_CONFIG: 0x11, LED: 0x12, EV_INPUT: 0x18,
    OLED_FRAME: 0x20, OLED_BLIT: 0x21, OLED_TEXT: 0x22, OLED_CLEAR: 0x23, OLED_RECT: 0x24, OLED_CMD: 0x25,
    OLED_CONFIG: 0x26, OLED_FLUSH: 0x2f,
    SEG_RAW: 0x30, SEG_TEXT: 0x31, SEG_CONFIG: 0x32,
    MX_FRAME: 0x40, MX_CONFIG: 0x41, MX_RAW: 0x42,
  };
  const OpName = {};
  for (const k in Op) OpName[Op[k]] = k;
  const Err = { UNKNOWN_OP: 1, BAD_LEN: 2, BAD_ARG: 3, HW: 4, NOT_READY: 5 };
  const ErrName = { 1: "UNKNOWN_OP", 2: "BAD_LEN", 3: "BAD_ARG", 4: "HW", 5: "NOT_READY" };
  const Font = { F6X10: 0, F9X15: 1, LOGISOSO16: 2, LOGISOSO24_NUM: 3, LOGISOSO32_NUM: 4, WQY12_CN: 5 };
  const VERSION = 1, MAX_PAYLOAD = 1100, HEADER = 4;

  const CRC_TABLE = new Uint16Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i << 8;
    for (let k = 0; k < 8; k++) c = c & 0x8000 ? (c << 1) ^ 0x1021 : c << 1;
    CRC_TABLE[i] = c & 0xffff;
  }
  function crc16(data, len = data.length) {
    let c = 0xffff;
    for (let i = 0; i < len; i++) c = ((c << 8) & 0xffff) ^ CRC_TABLE[((c >> 8) ^ data[i]) & 0xff];
    return c;
  }

  // 编码一帧，返回含结尾 0x00 的字节
  function encodeFrame(op, flags, seq, payload) {
    const p = payload || new Uint8Array(0);
    if (p.length > MAX_PAYLOAD) throw new Error(`payload ${p.length} > ${MAX_PAYLOAD}`);
    const raw = new Uint8Array(HEADER + p.length + 2);
    raw[0] = op;
    raw[1] = flags;
    raw[2] = seq & 0xff;
    raw[3] = (seq >> 8) & 0xff;
    raw.set(p, HEADER);
    const c = crc16(raw, HEADER + p.length);
    raw[HEADER + p.length] = c & 0xff;
    raw[HEADER + p.length + 1] = c >> 8;
    // COBS
    const out = new Uint8Array(raw.length + Math.ceil(raw.length / 254) + 2);
    let o = 1, codePos = 0, code = 1;
    for (let i = 0; i < raw.length; i++) {
      if (raw[i] === 0) {
        out[codePos] = code;
        codePos = o++;
        code = 1;
      } else {
        out[o++] = raw[i];
        if (++code === 0xff) {
          out[codePos] = code;
          codePos = o++;
          code = 1;
        }
      }
    }
    out[codePos] = code;
    out[o++] = 0;
    return out.subarray(0, o);
  }

  // 解码两个 0x00 之间的内容；格式或 CRC 错误返回 null
  function decodeFrame(enc) {
    const raw = new Uint8Array(enc.length);
    let i = 0, o = 0;
    while (i < enc.length) {
      const code = enc[i++];
      if (code === 0 || i + code - 1 > enc.length) return null;
      for (let k = 1; k < code; k++) raw[o++] = enc[i++];
      if (code !== 0xff && i < enc.length) raw[o++] = 0;
    }
    if (o < 6) return null;
    if (crc16(raw, o - 2) !== (raw[o - 2] | (raw[o - 1] << 8))) return null;
    return { op: raw[0], flags: raw[1], seq: raw[2] | (raw[3] << 8), payload: raw.slice(HEADER, o - 2) };
  }

  // 字节流 → 帧；乱码丢到下一个 0x00 即可重新同步
  class FrameReader {
    constructor(onFrame, onError) {
      this.buf = new Uint8Array(4096);
      this.len = 0;
      this.onFrame = onFrame;
      this.onError = onError || (() => {});
    }
    push(bytes) {
      for (let i = 0; i < bytes.length; i++) {
        const b = bytes[i];
        if (b === 0) {
          if (this.len) {
            const f = decodeFrame(this.buf.subarray(0, this.len));
            this.len = 0;
            if (f) this.onFrame(f);
            else this.onError();
          }
        } else if (this.len < this.buf.length) {
          this.buf[this.len++] = b;
        } else {
          this.len = this.buf.length + 1;  // 超长：丢到下一个 0x00
        }
      }
    }
  }

  // 小端读写
  const rd16 = (p, i) => p[i] | (p[i + 1] << 8);
  const rd16s = (p, i) => (rd16(p, i) << 16) >> 16;
  const rd32 = (p, i) => (p[i] | (p[i + 1] << 8) | (p[i + 2] << 16)) + p[i + 3] * 0x1000000;
  function wr16(p, i, v) { p[i] = v & 0xff; p[i + 1] = (v >> 8) & 0xff; }
  function wr32(p, i, v) { for (let k = 0; k < 4; k++) p[i + k] = Math.floor(v / 2 ** (8 * k)) & 0xff; }
  function wr64(p, i, v) { for (let k = 0; k < 8; k++) p[i + k] = Math.floor(v / 2 ** (8 * k)) & 0xff; }
  function rd64(p, i) { let v = 0; for (let k = 7; k >= 0; k--) v = v * 256 + p[i + k]; return v; }

  WWB.proto = {
    Flag, Op, OpName, Err, ErrName, Font, VERSION, MAX_PAYLOAD, HEADER,
    crc16, encodeFrame, decodeFrame, FrameReader, rd16, rd16s, rd32, rd64, wr16, wr32, wr64,
  };
})();
