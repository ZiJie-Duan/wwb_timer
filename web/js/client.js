// 网页脚本用的设备 API，方法名、参数顺序与 host/wwb/device.py 的 Device 一致（Python 的关键字参数在这里写成最后的 {…}）。
// 每条命令都编码成协议帧字节交给模拟器的一条通道，回复和事件也走协议帧回来，与真机走的是同一套协议。
(function () {
  const WWB = (window.WWB = window.WWB || {});
  const P = WWB.proto;
  const { Op, Flag } = P;
  const enc = new TextEncoder(), dec = new TextDecoder();

  class DeviceError extends Error {
    constructor(op, code) {
      super(`${P.OpName[op] || op}: ${P.ErrName[code] || code}`);
      this.op = op;
      this.code = code;
    }
  }

  const bytes = (...parts) => {
    const out = [];
    for (const p of parts) {
      if (typeof p === "number") out.push(p & 0xff);
      else for (const b of p) out.push(b);
    }
    return new Uint8Array(out);
  };
  const le16 = (v) => [v & 0xff, (v >> 8) & 0xff];
  const le32 = (v) => { const b = new Uint8Array(4); P.wr32(b, 0, v); return b; };

  class Device {
    // emu：WWB.Emulator；linkName 决定 STATS 里记在哪条通道（网页脚本默认记在 uart）
    constructor(emu, { linkName = "uart", onError } = {}) {
      this.seq = 0;
      this.pending = new Map();
      this.inputCallbacks = [];
      this.onError = onError || ((e) => console.warn(e));
      this.reader = new P.FrameReader((f) => this._route(f));
      this.link = emu.addLink(linkName, (data) => queueMicrotask(() => this.reader.push(data)));
      this.closed = false;
    }

    close() {
      this.closed = true;
      this.link.close();
      for (const p of this.pending.values()) p.reject(new Error("closed"));
      this.pending.clear();
    }

    _route(f) {
      if (this.closed) return;
      if (f.flags & Flag.EVENT) {
        if (f.op === Op.EV_INPUT) {
          const p = f.payload;
          const ev = { input: p[0], name: ["switch", "boot"][p[0]], active: !!p[1], count: P.rd32(p, 2), t_us: P.rd64(p, 6) };
          for (const cb of this.inputCallbacks.slice()) {
            try { cb(ev); } catch (e) { this.onError(e); }
          }
        }
        return;
      }
      if (!(f.flags & Flag.RESP)) return;
      const p = this.pending.get(f.seq);
      if (p) {
        this.pending.delete(f.seq);
        if (f.flags & Flag.ERR) p.reject(new DeviceError(f.op, f.payload[0]));
        else p.resolve(f.payload);
      } else if (f.flags & Flag.ERR) {
        // NOREPLY 命令出错时设备仍会回复
        this.onError(new DeviceError(f.op, f.payload[0]));
      }
    }

    _nextSeq() {
      return (this.seq = (this.seq + 1) & 0xffff);
    }

    // ------------------------------------------------------------ 基础收发

    send(op, payload = new Uint8Array(0), flags = Flag.NOREPLY) {
      if (this.closed) throw new Error("device closed");
      const seq = this._nextSeq();
      this.link.receive(P.encodeFrame(op, flags, seq, payload));
      return seq;
    }

    request(op, payload = new Uint8Array(0), flags = 0, timeout = 2000) {
      if (this.closed) return Promise.reject(new Error("device closed"));
      const seq = this._nextSeq();
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          this.pending.delete(seq);
          reject(new Error(`${P.OpName[op]}: no reply`));
        }, timeout);
        this.pending.set(seq, {
          resolve: (v) => { clearTimeout(timer); resolve(v); },
          reject: (e) => { clearTimeout(timer); reject(e); },
        });
        this.link.receive(P.encodeFrame(op, flags & ~Flag.NOREPLY, seq, payload));
      });
    }

    on_input(cb) {
      this.inputCallbacks.push(cb);
    }

    // ------------------------------------------------------------ 系统

    async ping(payload = new Uint8Array(0)) { return this.request(Op.PING, payload); }
    async info() { return JSON.parse(dec.decode(await this.request(Op.INFO))); }
    async stats() { return JSON.parse(dec.decode(await this.request(Op.STATS))); }
    async stats_reset() { await this.request(Op.STATS_RESET); }
    async time_us() { return P.rd64(await this.request(Op.TIME), 0); }
    async reboot() { await this.request(Op.REBOOT); }
    async subscribe(inputs = true) { await this.request(Op.SUBSCRIBE, bytes(inputs ? 1 : 0)); }

    // ------------------------------------------------------------ 输入 / 灯

    async io_read() {
      const r = await this.request(Op.IO_READ), out = {};
      ["switch", "boot"].forEach((name, i) => {
        out[name] = { active: !!r[i * 13], count: P.rd32(r, i * 13 + 1), changed_us: P.rd64(r, i * 13 + 5) };
      });
      return out;
    }
    io_config(debounce_us) { return this.request(Op.IO_CONFIG, le32(debounce_us)); }
    led(on) { this.send(Op.LED, bytes(on ? 1 : 0)); }

    // ------------------------------------------------------------ OLED
    // 绘制类命令默认不等回复（出错时会在控制台报告）；{wait: true} 时返回 Promise

    _oled(op, payload, flush, wait) {
      const flags = flush ? Flag.FLUSH : 0;
      if (wait) return this.request(op, payload, flags);
      this.send(op, payload, flags | Flag.NOREPLY);
    }

    // 整帧：1024 字节帧缓冲，或 canvas / 2D 上下文（自动二值化）
    oled_frame(frame, { flush = true, wait = false } = {}) {
      const data = frame instanceof Uint8Array || Array.isArray(frame) ? frame : WWB.toFrame(frame);
      return this._oled(Op.OLED_FRAME, Uint8Array.from(data), flush, wait);
    }
    oled_blit(page, col, pages, cols, data, { flush = true, wait = false } = {}) {
      return this._oled(Op.OLED_BLIT, bytes(page, col, pages, cols, data), flush, wait);
    }
    // y 为基线；color 0 清除 / 1 点亮 / 2 反色
    oled_text(x, y, text, font = 0, color = 1, { flush = false, wait = false } = {}) {
      return this._oled(Op.OLED_TEXT, bytes(le16(x), le16(y), font, color, enc.encode(String(text))), flush, wait);
    }
    oled_clear(color = 0, { flush = false, wait = false } = {}) {
      return this._oled(Op.OLED_CLEAR, bytes(color), flush, wait);
    }
    // mode 0 清除填充 / 1 填充 / 2 边框 / 3 反色
    oled_rect(x, y, w, h, mode = 1, { flush = false, wait = false } = {}) {
      return this._oled(Op.OLED_RECT, bytes(le16(x), le16(y), le16(w), le16(h), mode), flush, wait);
    }
    oled_flush() { this.send(Op.OLED_FLUSH); }
    // 直接发 SSD1306 命令，如对比度 oled_cmd(0x81, 0x7F)、反色 oled_cmd(0xA7)
    oled_cmd(...cmds) { this.send(Op.OLED_CMD, bytes(cmds)); }
    oled_contrast(v) { this.oled_cmd(0x81, v); }
    oled_config(i2c_hz) { return this.request(Op.OLED_CONFIG, le32(i2c_hz)); }

    // ------------------------------------------------------------ 数码管

    // 4 字节段码（bit0=a … bit6=g，第 2 位 bit7 = 冒号）
    seg_raw(segs) { this.send(Op.SEG_RAW, Uint8Array.from(segs)); }
    seg_text(text) { this.send(Op.SEG_TEXT, enc.encode(String(text))); }
    seg_config(brightness = 3, on = true, rise_us = 50, fall_us = 2, dio_rise_us = null) {
      this.send(Op.SEG_CONFIG, bytes(brightness, on ? 1 : 0, rise_us, fall_us, dio_rise_us ?? rise_us));
    }

    // ------------------------------------------------------------ 点阵

    // 8 字节，逻辑方向：行 0 在上，bit7 在左；也可以传 8 个 "#..#...." 字符串
    mx_frame(rows) { this.send(Op.MX_FRAME, Uint8Array.from(WWB.mxRows(rows))); }
    mx_config(intensity = 1, rotation = 1, test = false, shutdown = false, spi_hz = 0) {
      this.send(Op.MX_CONFIG, bytes(intensity, rotation, (test ? 1 : 0) | (shutdown ? 2 : 0), le32(spi_hz)));
    }
    mx_raw(...pairs) { this.send(Op.MX_RAW, bytes(pairs.flat())); }
  }

  // 画布 → OLED 帧缓冲：亮度 ≥ threshold 的像素点亮
  WWB.toFrame = function (src, threshold = 128) {
    const ctx = src.getImageData ? src : src.getContext("2d");
    const img = ctx.getImageData(0, 0, 128, 64).data, out = new Uint8Array(1024);
    for (let y = 0; y < 64; y++) {
      const row = (y >> 3) * 128, bit = 1 << (y & 7);
      for (let x = 0; x < 128; x++) {
        const i = (y * 128 + x) * 4;
        if ((img[i] * 0.299 + img[i + 1] * 0.587 + img[i + 2] * 0.114) * (img[i + 3] / 255) >= threshold) out[row + x] |= bit;
      }
    }
    return out;
  };

  // 128×64 的绘图画布，黑底、白色画笔、关闭平滑
  WWB.makeCanvas = function () {
    const c = typeof OffscreenCanvas !== "undefined" ? new OffscreenCanvas(128, 64) : Object.assign(document.createElement("canvas"), { width: 128, height: 64 });
    const ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, 128, 64);
    ctx.fillStyle = ctx.strokeStyle = "#fff";
    ctx.font = "10px monospace";
    ctx.textBaseline = "top";
    return ctx;
  };

  // 8 个字符串（'#'/'1'/'X' 为亮）或 8 个数字 → 8 字节
  WWB.mxRows = function (rows) {
    return Array.from(rows, (r) => (typeof r === "string" ? [...r.padEnd(8, ".")].slice(0, 8).reduce((v, ch, i) => v | ("#1Xx@*".includes(ch) ? 0x80 >> i : 0), 0) : r & 0xff));
  };

  WWB.Device = Device;
  WWB.DeviceError = DeviceError;
})();
