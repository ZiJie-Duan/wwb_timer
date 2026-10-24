// 设备模拟器：按 firmware/src/main.cpp 的 execute() 逐条实现协议命令，并模拟各外设的刷新时序，
// 让上位机程序在网页上看到的效果（包括“只保留最新一帧”、刷新率上限）与真机一致。
//
// 时序模型来自真机实测（docs/benchmarks.md）：
//   OLED  推送耗时 ≈ 200µs + 10.1µs/字节（1.1MHz），整帧约 10.5ms → 95fps；推送期间的新绘制合并到下一次
//   数码管 每次传输 ≈ 370µs + 440µs/字节（上升 50µs），只写变化的位；单独一位约 1.25ms，整屏约 2.6ms
//   点阵  命令内同步写出（31µs），视为立即生效；配置每秒补发一次（会覆盖 MX_RAW 写入的行）
//   输入  消抖 20ms 后上报，时间戳取抖动开始时刻
(function () {
  const WWB = (window.WWB = window.WWB || {});
  const P = WWB.proto, G = WWB.u8g2;
  const { Op, Flag, Err } = P;
  const W = 128, PAGES = 8;
  const FW_VERSION = "0.1.0";
  const MAX_LAG_US = 20000;  // 页面卡住很久后不补算积压的推送
  const FONT_NAMES = ["6x10", "9x15", "logisoso16", "logisoso24n", "logisoso32n", "wqy12"];
  const ARROW_UP = [0x18, 0x3c, 0x7e, 0xdb, 0x18, 0x18, 0x18, 0x18];
  const SEG_DIGITS = [0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f];
  const SEG_CHARS = {
    A: 0x77, a: 0x77, B: 0x7c, b: 0x7c, C: 0x39, c: 0x58, D: 0x5e, d: 0x5e, E: 0x79, e: 0x79, F: 0x71, f: 0x71,
    G: 0x3d, g: 0x3d, H: 0x76, h: 0x74, I: 0x06, i: 0x06, J: 0x1e, j: 0x1e, L: 0x38, l: 0x38, N: 0x54, n: 0x54,
    O: 0x3f, o: 0x5c, P: 0x73, p: 0x73, Q: 0x67, q: 0x67, R: 0x50, r: 0x50, S: 0x6d, s: 0x6d, T: 0x78, t: 0x78,
    U: 0x3e, u: 0x1c, Y: 0x6e, y: 0x6e, "-": 0x40, _: 0x08, "=": 0x48,
  };

  function segEncodeChar(c) {
    if (c >= "0" && c <= "9") return SEG_DIGITS[c.charCodeAt(0) - 48];
    return SEG_CHARS[c] || 0;
  }

  // 与 seg::setText 相同：逐字节编码，':' 点亮冒号，最多 4 位，右对齐
  function segText(bytes) {
    const out = [], segs = [0, 0, 0, 0];
    let colon = false;
    for (const b of bytes) {
      const c = String.fromCharCode(b);
      if (c === ":") colon = true;
      else if (out.length < 4) out.push(segEncodeChar(c));
    }
    out.forEach((v, i) => (segs[4 - out.length + i] = v));
    if (colon) segs[1] |= 0x80;
    return segs;
  }

  // 与 mx::rotate 相同：逻辑画面顺时针旋转 rotation×90°
  function mxRotate(rows, rotation) {
    if (rotation === 0) return rows.slice();
    const px = (r, c) => (rows[r] >> (7 - c)) & 1;
    const out = [];
    for (let r = 0; r < 8; r++) {
      let v = 0;
      for (let c = 0; c < 8; c++) {
        const on = rotation === 1 ? px(7 - c, r) : rotation === 2 ? px(7 - r, 7 - c) : px(c, 7 - r);
        if (on) v |= 0x80 >> c;
      }
      out.push(v);
    }
    return out;
  }

  const enc = new TextEncoder(), dec = new TextDecoder();
  const SSD1306_ARGS = { 0x81: 1, 0x20: 1, 0x21: 2, 0x22: 2, 0xa8: 1, 0xd3: 1, 0xd5: 1, 0xd9: 1, 0xda: 1, 0xdb: 1, 0x8d: 1,
    0x26: 6, 0x27: 6, 0x29: 5, 0x2a: 5, 0xa3: 2 };

  class Link {
    constructor(emu, name, sink) {
      this.emu = emu;
      this.name = name;
      this.sink = sink;  // (Uint8Array) => void，把设备发出的字节交给对端
      this.subscribe = 1;
      this.resetStats();
      this.reader = new P.FrameReader((f) => {
        this.rxFrames++;
        emu.dispatch(this, f);
      }, () => this.crcErrors++);
    }
    resetStats() {
      Object.assign(this, { rxBytes: 0, rxFrames: 0, crcErrors: 0, framingErrors: 0, txBytes: 0, txFrames: 0 });
    }
    // 对端发来的字节
    receive(bytes) {
      this.rxBytes += bytes.length;
      this.emu.advance();
      this.reader.push(bytes);
    }
    send(op, flags, seq, payload) {
      const data = P.encodeFrame(op, flags, seq, payload);
      this.txBytes += data.length;
      this.txFrames++;
      this.sink(data);
    }
    close() {
      this.emu.links = this.emu.links.filter((l) => l !== this);
    }
  }

  class Emulator {
    constructor() {
      this.t0 = performance.now();
      this.links = [];
      this.listeners = [];  // (kind, detail) => void；kind: frame / reboot / error
      this.offline = null;  // 脱机程序（offline.js），没有时显示固件的等待画面
      this.reset();
    }

    nowUs() {
      return Math.round((performance.now() - this.t0) * 1000);
    }

    addLink(name, sink) {
      const l = new Link(this, name, sink);
      this.links.push(l);
      return l;
    }

    on(fn) {
      this.listeners.push(fn);
    }

    emit(kind, detail) {
      for (const fn of this.listeners) fn(kind, detail);
    }

    // ---------------------------------------------------------------- 状态

    reset() {
      this.bootUs = this.nowUs();
      this.oled = {
        fb: new Uint8Array(W * PAGES),    // 设备端帧缓冲（u8g2 画布）
        ram: new Uint8Array(W * PAGES),   // 屏上显存
        dirty: null,                       // {p0, p1, c0, c1}
        awake: false,                      // 推送任务是否被唤醒（commit 唤醒，没有脏区时睡下）
        push: null,                        // 进行中的推送 {end, p0, p1, c0, c1, data}
        hz: 1100000,
        panel: { on: true, invert: false, contrast: 0xcf, allOn: false, flipX: false, flipY: false, startLine: 0, offset: 0 },
        stats: { commits: 0, pushes: 0, bytes: 0, errors: 0, lastUs: 0, totalUs: 0 },
      };
      this.seg = {
        want: [0x40, 0x40, 0x40, 0x40], brightness: 3, on: true, rise: 50, fall: 2, dioRise: 5,
        version: 1, configVersion: 1, doneVersion: 0, doneConfig: 0,
        shown: [0, 0, 0, 0], shownValid: false, shownBrightness: 3, shownOn: false,
        busy: null,
        stats: { requests: 0, updates: 0, ackFails: 0, lastUs: 0, totalUs: 0 },
      };
      this.mx = {
        logical: [0, 0, 0, 0, 0, 0, 0, 0], intensity: 1, rotation: 1, test: false, shutdown: false, spiHz: 10000000,
        reg: { rows: [0, 0, 0, 0, 0, 0, 0, 0], intensity: 0, scan: 7, shutdownOff: false, test: false, decode: 0 },
        physShown: null, nextRefresh: 0,
        stats: { frames: 0, lastUs: 0, totalUs: 0 },
      };
      const prevLevels = this.io ? this.io.inputs.map((s) => s.level) : [false, false];
      this.io = {
        debounce: 20000, led: false,
        inputs: prevLevels.map((level) => ({ level, active: level, count: 0, changedUs: this.nowUs(), burst: false, burstStart: 0, lastEdge: 0 })),
      };
      this.ops = 0;
      this.opErrors = 0;
      this.sinkBytes = 0;
      this.eventSeq = 0;
      for (const l of this.links) {
        l.subscribe = 1;
        l.resetStats();
      }
      this.mxRefreshConfig();
      if (this.offline) this.offline.begin();
      else this.drawIdle();
      this.io.led = true;  // 蓝灯常亮 = 通道就绪
    }

    // 装上脱机程序，并像开机一样从头运行
    setOffline(off) {
      this.offline = off;
      this.reset();
    }

    // 开机前的输入电平（比如开关一直拨在上面），不产生事件
    presetInput(i, level) {
      const s = this.io.inputs[i];
      s.level = s.active = level;
    }

    drawIdle() {
      const fb = this.oled.fb;
      fb.fill(0);
      G.drawUTF8(fb, G.FONTS[1], 0, 14, "wwb_timer", 1);
      G.drawUTF8(fb, G.FONTS[0], 0, 30, `fw ${FW_VERSION}  proto ${P.VERSION}`, 1);
      G.drawUTF8(fb, G.FONTS[0], 0, 44, "USB / UART 20,21", 1);
      G.drawUTF8(fb, G.FONTS[0], 0, 58, "waiting for host", 1);
      this.oledMarkAll();
      this.oledCommit();
      this.segSetRaw(segText(enc.encode("----")));
      this.mxSetFrame(ARROW_UP);
    }

    // ---------------------------------------------------------------- 时间推进

    // 把各外设的模拟推进到当前时刻。收到命令前、每个显示帧、定时器都会调用
    advance() {
      const now = this.nowUs();
      this.oledAdvance(now);
      this.segAdvance(now);
      this.ioAdvance(now);
      if (now >= this.mx.nextRefresh) this.mxRefreshConfig();
      if (this.offline) this.offline.advance(now);
    }

    // ---------------------------------------------------------------- OLED

    oledMarkDirty(p0, p1, c0, c1) {
      const d = this.oled.dirty;
      if (!d) this.oled.dirty = { p0, p1, c0, c1 };
      else {
        d.p0 = Math.min(d.p0, p0); d.p1 = Math.max(d.p1, p1);
        d.c0 = Math.min(d.c0, c0); d.c1 = Math.max(d.c1, c1);
      }
    }
    oledMarkAll() {
      this.oledMarkDirty(0, PAGES - 1, 0, W - 1);
    }
    oledDirtyPixels(x, y, w, h) {
      if (w <= 0 || h <= 0) return;
      if (x + w - 1 < 0 || x >= W || y + h - 1 < 0 || y >= 64) return;
      const cl = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
      this.oledMarkDirty(cl(y, 0, 63) >> 3, cl(y + h - 1, 0, 63) >> 3, cl(x, 0, W - 1), cl(x + w - 1, 0, W - 1));
    }
    oledCommit() {
      this.oled.stats.commits++;
      this.oled.awake = true;
      this.oledAdvance(this.nowUs());
    }
    oledPushUs(len) {
      return 200 + len * 10.1 * (1100000 / this.oled.hz);
    }
    // 与 oled.cpp 的 pushTask 相同：被唤醒后只要有脏区就继续推，推送开始时取画布快照
    oledAdvance(now) {
      const o = this.oled;
      for (;;) {
        let start = now;
        if (o.push) {
          if (now < o.push.end) return;
          const p = o.push;
          const cols = p.c1 - p.c0 + 1;
          for (let pg = p.p0, k = 0; pg <= p.p1; pg++, k++) o.ram.set(p.data.subarray(k * cols, (k + 1) * cols), pg * W + p.c0);
          o.push = null;
          o.stats.pushes++;
          start = p.end;
        }
        if (!o.awake) return;
        if (!o.dirty) {
          o.awake = false;
          return;
        }
        const { p0, p1, c0, c1 } = o.dirty;
        o.dirty = null;
        const cols = c1 - c0 + 1, data = new Uint8Array((p1 - p0 + 1) * cols);
        for (let pg = p0, k = 0; pg <= p1; pg++, k++) data.set(o.fb.subarray(pg * W + c0, pg * W + c1 + 1), k * cols);
        const dur = this.oledPushUs(data.length);
        o.push = { end: Math.max(start, now - MAX_LAG_US) + dur, p0, p1, c0, c1, data };
        o.stats.bytes += data.length;
        o.stats.lastUs = Math.round(dur);
        o.stats.totalUs += Math.round(dur);
      }
    }

    // SSD1306 命令：只模拟影响画面的那些
    oledCommand(bytes) {
      const pn = this.oled.panel;
      for (let i = 0; i < bytes.length; i++) {
        const c = bytes[i], args = bytes.subarray(i + 1, i + 1 + (SSD1306_ARGS[c] || 0));
        i += SSD1306_ARGS[c] || 0;
        if (c === 0xae || c === 0xaf) pn.on = c === 0xaf;
        else if (c === 0xa6 || c === 0xa7) pn.invert = c === 0xa7;
        else if (c === 0xa4 || c === 0xa5) pn.allOn = c === 0xa5;
        else if (c === 0x81 && args.length) pn.contrast = args[0];
        else if (c === 0xa0 || c === 0xa1) pn.flipX = c === 0xa0;  // 初始化用 A1（与 u8g2 R0 一致）
        else if (c === 0xc0 || c === 0xc8) pn.flipY = c === 0xc0;  // 初始化用 C8
        else if (c >= 0x40 && c <= 0x7f) pn.startLine = c & 0x3f;
        else if (c === 0xd3 && args.length) pn.offset = args[0] & 0x3f;
      }
    }

    // 屏上实际看到的像素（考虑反色、翻转、起始行等），返回 128×64 的 0/1 数组
    oledPixels(out) {
      const o = this.oled, pn = o.panel, ram = o.ram;
      for (let y = 0; y < 64; y++) {
        const sy = pn.flipY ? 63 - y : y;
        const ry = (sy + pn.startLine + pn.offset) & 63;
        const row = (ry >> 3) * W, bit = 1 << (ry & 7);
        for (let x = 0; x < W; x++) {
          const rx = pn.flipX ? W - 1 - x : x;
          let v = pn.allOn ? 1 : ram[row + rx] & bit ? 1 : 0;
          if (pn.invert) v ^= 1;
          out[y * W + x] = pn.on ? v : 0;
        }
      }
      return out;
    }

    // ---------------------------------------------------------------- 数码管

    segSetRaw(segs) {
      const s = this.seg;
      s.want = Array.from(segs);
      s.version++;
      s.stats.requests++;
      this.segAdvance(this.nowUs());
    }
    segTxUs(bytes, txns) {
      const k = (this.seg.rise + this.seg.fall) / 52;
      return (370 * txns + 440 * bytes) * k;
    }
    // 与 seg.cpp 的 segTask 相同：只写变化的位；配置变化时补发配置并整屏重写
    segAdvance(now) {
      const s = this.seg;
      for (;;) {
        let start = now;
        if (s.busy) {
          if (now < s.busy.end) return;
          const b = s.busy;
          s.busy = null;
          s.shown = b.segs;
          s.shownValid = true;
          if (b.withConfig) {
            s.shownBrightness = b.brightness;
            s.shownOn = b.on;
            s.doneConfig = b.cv;
          }
          start = b.end;
        }
        const withConfig = s.configVersion !== s.doneConfig;
        if (s.version === s.doneVersion && !withConfig) return;
        let first = 0, last = 3;
        if (s.shownValid && !withConfig) {
          while (first < 4 && s.want[first] === s.shown[first]) first++;
          while (last >= first && s.want[last] === s.shown[last]) last--;
          if (first > last) {
            s.doneVersion = s.version;
            continue;
          }
        }
        const bytes = last - first + 2 + (withConfig ? 2 : 0);
        const dur = this.segTxUs(bytes, withConfig ? 3 : 1);
        s.busy = { end: Math.max(start, now - MAX_LAG_US) + dur, segs: s.want.slice(), withConfig, cv: s.configVersion,
          brightness: s.brightness, on: s.on };
        s.doneVersion = s.version;
        s.stats.updates++;
        s.stats.lastUs = Math.round(dur);
        s.stats.totalUs += Math.round(dur);
      }
    }

    // ---------------------------------------------------------------- 点阵

    mxWriteConfig() {
      const m = this.mx, r = m.reg;
      r.test = m.test;
      r.decode = 0;
      r.scan = 7;
      r.intensity = m.intensity;
      r.shutdownOff = m.shutdown;
    }
    mxWriteRows(force) {
      const m = this.mx, phys = mxRotate(m.logical, m.rotation);
      let n = 0;
      for (let r = 0; r < 8; r++) {
        if (force || !m.physShown || phys[r] !== m.physShown[r]) {
          m.reg.rows[r] = phys[r];
          n++;
        }
      }
      m.physShown = phys;
      return n;
    }
    mxSetFrame(rows) {
      const m = this.mx;
      m.logical = Array.from(rows);
      const n = this.mxWriteRows(false);
      const us = 2 + n * 3.6 * (10000000 / m.spiHz);
      m.stats.frames++;
      m.stats.lastUs = Math.round(us);
      m.stats.totalUs += us;
    }
    mxRefreshConfig() {
      this.mxWriteConfig();
      this.mxWriteRows(true);
      this.mx.nextRefresh = this.nowUs() + 1000000;
    }
    mxRaw(pairs) {
      const r = this.mx.reg;
      for (let i = 0; i + 1 < pairs.length; i += 2) {
        const reg = pairs[i] & 0x0f, v = pairs[i + 1];
        if (reg >= 1 && reg <= 8) r.rows[reg - 1] = v;
        else if (reg === 0x09) r.decode = v;
        else if (reg === 0x0a) r.intensity = v & 0x0f;
        else if (reg === 0x0b) r.scan = v & 7;
        else if (reg === 0x0c) r.shutdownOff = !(v & 1);
        else if (reg === 0x0f) r.test = !!(v & 1);
      }
      this.mx.physShown = null;
    }
    // 看到的画面：模块按当前安装方向相对物理行逆时针 90°（所以 rotation=1 时逻辑画面是正的）
    mxView() {
      const r = this.mx.reg;
      if (r.test) return { rows: [255, 255, 255, 255, 255, 255, 255, 255], intensity: 15 };
      if (r.shutdownOff) return { rows: [0, 0, 0, 0, 0, 0, 0, 0], intensity: r.intensity };
      const phys = r.rows.map((v, i) => (i <= r.scan ? v : 0));
      return { rows: mxRotate(phys, 3), intensity: r.intensity };
    }

    // ---------------------------------------------------------------- 输入

    // 网页上按下开关 / BOOT：相当于引脚电平变化（level = 有效）
    setInput(i, level) {
      const s = this.io.inputs[i], now = this.nowUs();
      if (s.level === level) return;
      s.level = level;
      if (!s.burst) {
        s.burst = true;
        s.burstStart = now;
      }
      s.lastEdge = now;
    }
    ioAdvance(now) {
      this.io.inputs.forEach((s, i) => {
        if (!s.burst || now - s.lastEdge < this.io.debounce) return;
        s.burst = false;
        if (s.level === s.active) return;  // 抖了一下又回到原状态
        s.active = s.level;
        s.count++;
        s.changedUs = s.burstStart;
        const p = new Uint8Array(14);
        p[0] = i;
        p[1] = s.active ? 1 : 0;
        P.wr32(p, 2, s.count);
        P.wr64(p, 6, s.changedUs);
        this.broadcastEvent(1, Op.EV_INPUT, p);
        if (this.offline) this.offline.input(i, s.active, s.changedUs);
        this.emit("input", { input: i, active: s.active });
      });
    }
    broadcastEvent(mask, op, payload) {
      const seq = (this.eventSeq = (this.eventSeq + 1) & 0xffff);
      for (const l of this.links) if (l.subscribe & mask) l.send(op, Flag.EVENT, seq, payload);
    }

    // ---------------------------------------------------------------- JSON

    infoJson() {
      const s = this.seg, m = this.mx;
      return JSON.stringify({
        name: "wwb_timer", fw: FW_VERSION, proto: P.VERSION, chip: "simulator", rev: 0, mac: "00:00:00:00:00:00",
        cpu_mhz: 160, flash: 4194304, max_payload: P.MAX_PAYLOAD, sim: true,
        oled: { present: true, addr: 60, w: 128, h: 64, i2c_hz: this.oled.hz },
        seg: { brightness: s.brightness, on: s.on, rise_us: s.rise, fall_us: s.fall, dio_rise_us: s.dioRise },
        mx: { intensity: m.intensity, rotation: m.rotation, test: m.test, shutdown: m.shutdown, spi_hz: m.spiHz },
        io: { debounce_us: this.io.debounce, led: this.io.led },
        uart: { rx: 20, tx: 21, baud: 921600 },
        fonts: FONT_NAMES,
      });
    }

    statsJson() {
      const link = (name) => {
        const l = this.links.find((x) => x.name === name) || new Link(this, name, () => {});
        return { rx_bytes: l.rxBytes, rx_frames: l.rxFrames, crc_errors: l.crcErrors, framing_errors: l.framingErrors,
          tx_bytes: l.txBytes, tx_frames: l.txFrames, tx_dropped: 0, tx_not_connected: 0, subscribe: l.subscribe, rx_busy_us: 0 };
      };
      const o = this.oled.stats, s = this.seg.stats, m = this.mx.stats;
      return JSON.stringify({
        uptime_us: this.nowUs() - this.bootUs, heap_free: 200000, heap_min: 180000, ops: this.ops, op_errors: this.opErrors,
        sink_bytes: this.sinkBytes, usb: link("usb"), uart: link("uart"),
        oled: { commits: o.commits, pushes: o.pushes, bytes: o.bytes, errors: 0, last_us: o.lastUs, total_us: o.totalUs },
        seg: { requests: s.requests, updates: s.updates, ack_fails: 0, last_us: s.lastUs, total_us: s.totalUs },
        mx: { frames: m.frames, last_us: m.lastUs, total_us: Math.round(m.totalUs) },
        exec_us: { oled: 0, seg: 0, mx: 0, other: 0 },
      });
    }

    // ---------------------------------------------------------------- 命令分发

    dispatch(link, f) {
      if (f.flags & (Flag.RESP | Flag.EVENT)) return;
      // 控制器发来的每条命令：先让脱机程序让出设备（与固件 dispatch() 相同）
      if (this.offline) {
        if (f.op === Op.RELEASE) this.offline.release();
        else this.offline.hostFrame();
      }
      let r;
      try {
        r = this.execute(link, f.op, f.flags, f.seq, f.payload);
      } catch (e) {
        console.error(e);
        r = -Err.HW;
      }
      this.ops++;
      this.emit("frame", { link: link.name, op: f.op, len: f.payload.length, err: typeof r === "number" && r < 0 ? -r : 0 });
      if (r === null) return;  // 已在 execute 内回复
      if (typeof r === "number" && r < 0) {
        this.opErrors++;
        link.send(f.op, Flag.RESP | Flag.ERR, f.seq, new Uint8Array([-r]));
      } else if (!(f.flags & Flag.NOREPLY)) {
        link.send(f.op, Flag.RESP, f.seq, r || new Uint8Array(0));
      }
    }

    // 返回回复 payload（Uint8Array / 空）、-错误码，或 null（已回复）
    execute(link, op, flags, seq, p) {
      const n = p.length, o = this.oled;
      const u32 = (v) => { const b = new Uint8Array(4); P.wr32(b, 0, v); return b; };
      switch (op) {
        case Op.PING: return p;
        case Op.INFO: return enc.encode(this.infoJson());
        case Op.SINK: this.sinkBytes += n; return u32(this.sinkBytes);
        case Op.SOURCE: {
          if (n < 6) return -Err.BAD_LEN;
          const total = P.rd32(p, 0), chunk = P.rd16(p, 4);
          if (chunk === 0 || chunk > P.MAX_PAYLOAD) return -Err.BAD_ARG;
          const block = new Uint8Array(chunk).map((_, i) => i & 0xff);
          const t0 = performance.now();
          let sent = 0;
          while (sent < total) {
            const k = Math.min(chunk, total - sent);
            link.send(op, Flag.EVENT, seq, block.subarray(0, k));
            sent += k;
          }
          const r = new Uint8Array(8);
          P.wr32(r, 0, sent);
          P.wr32(r, 4, Math.round((performance.now() - t0) * 1000));
          return r;
        }
        case Op.STATS: return enc.encode(this.statsJson());
        case Op.STATS_RESET:
          for (const l of this.links) l.resetStats();
          o.stats = { commits: 0, pushes: 0, bytes: 0, errors: 0, lastUs: 0, totalUs: 0 };
          this.seg.stats = { requests: 0, updates: 0, ackFails: 0, lastUs: 0, totalUs: 0 };
          this.mx.stats = { frames: 0, lastUs: 0, totalUs: 0 };
          this.ops = this.opErrors = this.sinkBytes = 0;
          return new Uint8Array(0);
        case Op.REBOOT:
          link.send(op, Flag.RESP, seq, new Uint8Array(0));
          setTimeout(() => { this.reset(); this.emit("reboot"); }, 50);
          return null;
        case Op.UART_BAUD:
          if (n < 4) return -Err.BAD_LEN;
          if (P.rd32(p, 0) < 1200 || P.rd32(p, 0) > 5000000) return -Err.BAD_ARG;
          return new Uint8Array(0);
        case Op.SUBSCRIBE:
          if (n < 1) return -Err.BAD_LEN;
          link.subscribe = p[0];
          return new Uint8Array(0);
        case Op.TIME: {
          const r = new Uint8Array(8);
          P.wr64(r, 0, this.nowUs());
          return r;
        }
        case Op.BENCH: return this.bench(p);
        case Op.RELEASE: return new Uint8Array(0);

        case Op.IO_READ: {
          const r = new Uint8Array(26);
          this.io.inputs.forEach((s, i) => {
            r[i * 13] = s.active ? 1 : 0;
            P.wr32(r, i * 13 + 1, s.count);
            P.wr64(r, i * 13 + 5, s.changedUs);
          });
          return r;
        }
        case Op.IO_CONFIG:
          if (n < 4) return -Err.BAD_LEN;
          this.io.debounce = P.rd32(p, 0);
          return new Uint8Array(0);
        case Op.LED:
          if (n < 1) return -Err.BAD_LEN;
          this.io.led = !!p[0];
          return new Uint8Array(0);

        case Op.OLED_FRAME:
          if (n !== W * PAGES) return -Err.BAD_LEN;
          o.fb.set(p);
          this.oledMarkAll();
          break;
        case Op.OLED_BLIT: {
          if (n < 4) return -Err.BAD_LEN;
          const [p0, c0, pages, cols] = p;
          if (pages < 1 || cols < 1 || p0 + pages > PAGES || c0 + cols > W) return -Err.BAD_ARG;
          if (n !== 4 + pages * cols) return -Err.BAD_LEN;
          for (let i = 0; i < pages; i++) o.fb.set(p.subarray(4 + i * cols, 4 + (i + 1) * cols), (p0 + i) * W + c0);
          this.oledMarkDirty(p0, p0 + pages - 1, c0, c0 + cols - 1);
          break;
        }
        case Op.OLED_TEXT: {
          if (n < 6) return -Err.BAD_LEN;
          const x = P.rd16s(p, 0), y = P.rd16s(p, 2), font = p[4], color = p[5];
          if (font >= G.FONTS.length) return -Err.BAD_ARG;
          const f = G.FONTS[font];
          const text = dec.decode(p.subarray(6, Math.min(n, 6 + 255)));
          const w = G.drawUTF8(o.fb, f, x, y, text, color > 2 ? 1 : color);
          this.oledDirtyPixels(x, y - f.ascentA, w, f.ascentA - f.descentG + 1);
          break;
        }
        case Op.OLED_CLEAR:
          o.fb.fill(n >= 1 && p[0] ? 0xff : 0);
          this.oledMarkAll();
          break;
        case Op.OLED_RECT: {
          if (n < 9) return -Err.BAD_LEN;
          const x = P.rd16s(p, 0), y = P.rd16s(p, 2), w = P.rd16s(p, 4), h = P.rd16s(p, 6), mode = p[8];
          if (w <= 0 || h <= 0 || mode > 3) return -Err.BAD_ARG;
          const color = mode === 0 ? 0 : mode === 3 ? 2 : 1;
          if (mode === 2) G.drawFrame(o.fb, x, y, w, h, color);
          else G.drawBox(o.fb, x, y, w, h, color);
          this.oledDirtyPixels(x, y, w, h);
          break;
        }
        case Op.OLED_CMD:
          if (n < 1) return -Err.BAD_LEN;
          this.oledCommand(p);
          return new Uint8Array(0);
        case Op.OLED_CONFIG: {
          if (n < 4) return -Err.BAD_LEN;
          const hz = P.rd32(p, 0);
          // 真机：1.1MHz 以上的设定要么超时，要么花屏，见 docs/hardware.md
          if (hz < 10000 || hz > 1100000) return -Err.HW;
          o.hz = hz;
          return new Uint8Array(0);
        }
        case Op.OLED_FLUSH:
          this.oledCommit();
          return new Uint8Array(0);

        case Op.SEG_RAW:
          if (n !== 4) return -Err.BAD_LEN;
          this.segSetRaw(p);
          return new Uint8Array(0);
        case Op.SEG_TEXT:
          this.segSetRaw(segText(p));
          return new Uint8Array(0);
        case Op.SEG_CONFIG: {
          if (n < 4) return -Err.BAD_LEN;
          const s = this.seg;
          Object.assign(s, { brightness: p[0] & 7, on: !!p[1], rise: p[2], fall: p[3], dioRise: n >= 5 ? p[4] : p[2] });
          s.configVersion++;
          this.segSetRaw(s.want);
          return new Uint8Array(0);
        }

        case Op.MX_FRAME:
          if (n !== 8) return -Err.BAD_LEN;
          this.mxSetFrame(p);
          return new Uint8Array(0);
        case Op.MX_CONFIG: {
          if (n < 3) return -Err.BAD_LEN;
          const m = this.mx;
          Object.assign(m, { intensity: p[0] & 15, rotation: p[1] & 3, test: !!(p[2] & 1), shutdown: !!(p[2] & 2) });
          if (n >= 7 && P.rd32(p, 3)) m.spiHz = P.rd32(p, 3);
          this.mxWriteConfig();
          this.mxWriteRows(true);
          return new Uint8Array(0);
        }
        case Op.MX_RAW:
          if (n < 2 || n % 2) return -Err.BAD_LEN;
          this.mxRaw(p);
          return new Uint8Array(0);

        default:
          return -Err.UNKNOWN_OP;
      }
      // 落到这里的都是 OLED 绘制类命令
      if (flags & Flag.FLUSH) this.oledCommit();
      return new Uint8Array(0);
    }

    // 设备端自测：按时序模型给出估算值，便于跑通依赖它的脚本
    bench(p) {
      if (p.length < 3) return -Err.BAD_LEN;
      const target = p[0], count = P.rd16(p, 1);
      if (count < 1) return -Err.BAD_ARG;
      let r;
      if (target === 1) {
        const hz = p.length >= 7 && P.rd32(p, 3) ? P.rd32(p, 3) : this.oled.hz;
        r = { target: "oled", count, i2c_hz: hz, us: Math.round(count * (200 + 1024 * 10.1 * (1100000 / hz))), errors: 0 };
      } else if (target === 2) {
        if (p.length < 5) return -Err.BAD_LEN;
        const rise = p[3], fall = p[4], k = (rise + fall) / 52;
        r = { target: "seg", count, rise_us: rise, fall_us: fall, dio_rise_us: p.length >= 6 ? p[5] : rise,
          ack_settle_us: p.length >= 7 ? p[6] : 0, us: Math.round(count * (370 + 440 * 5) * k), ack_fails: 0 };
      } else if (target === 3) {
        if (p.length < 7) return -Err.BAD_LEN;
        const hz = P.rd32(p, 3);
        r = { target: "mx", count, spi_hz: hz, us: Math.round(count * (2 + 8 * 3.6 * (10000000 / hz))) };
      } else {
        return -Err.BAD_ARG;
      }
      r.simulated = true;
      return enc.encode(JSON.stringify(r));
    }
  }

  WWB.Emulator = Emulator;
  WWB.segText = (s) => segText(enc.encode(s));
  WWB.segEncodeChar = segEncodeChar;
})();
