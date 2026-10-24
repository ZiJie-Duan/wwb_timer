// 脱机程序（native/ 的 C++，编成 web/js/native.js）在模拟器里的运行环境，与固件的 offline.cpp 对应：
// 程序的命令直接交给模拟器执行；控制器（Python 程序）的命令持续 3s 才确认连接、播完连接动画后接管，
// 释放或 1.5s 没有命令就断开（状态机在 native/wwb/wwb.cpp 的 Runtime 里）。
// 断电保留的数据存在 localStorage，刷新网页 / 重启设备都不会丢
(function () {
  const WWB = window.WWB;
  const { Op, Err } = WWB.proto;
  const NVS_KEY = "wwb.sim.nvs";
  const CTL_KEY = "wwb.sim.ctl";  // 控制器存储（APP_DATA）
  const TICK_US = 16000;  // 与固件相同：约 60 帧/秒
  // 芯片上程序不能用的命令（会影响通道或耗时很长）
  const BLOCKED = new Set([Op.SOURCE, Op.REBOOT, Op.UART_BAUD, Op.SUBSCRIBE, Op.BENCH, Op.RELEASE, Op.CONNECT,
    Op.APP_STATE, Op.APP_DATA]);

  const store = (key) => ({
    load() {
      try {
        const s = localStorage.getItem(key);
        return s ? Uint8Array.from(atob(s), (c) => c.charCodeAt(0)) : null;
      } catch { return null; }
    },
    save(bytes) {
      try {
        if (bytes && bytes.length) localStorage.setItem(key, btoa(String.fromCharCode(...bytes)));
        else localStorage.removeItem(key);
      } catch { /* 隐私模式等 */ }
    },
  });
  const nvs = store(NVS_KEY);
  WWB.ctlStore = store(CTL_KEY);

  class Offline {
    static async load(emu) {
      if (typeof window.createWwbNative !== "function") return null;
      const off = new Offline(emu);
      off.mod = await window.createWwbNative({
        wwbExec: (op, flags, payload) => off.exec(op, flags, payload),
        wwbLoad: () => nvs.load(),
        wwbSave: (bytes) => nvs.save(bytes),
        wwbChanged: () => emu.broadcastEvent(2, Op.APP_STATE, off.report()),
      });
      return off;
    }

    constructor(emu) {
      this.emu = emu;
      this.link = { name: "app", subscribe: 0, send() {} };  // 程序自己的“通道”：只用于流量统计
      this.nextTick = 0;
    }

    exec(op, flags, payload) {
      if (BLOCKED.has(op)) return -Err.BAD_ARG;
      const r = this.emu.execute(this.link, op, flags, 0, payload);
      this.emu.emit("frame", { link: "app", op, len: payload.length, err: typeof r === "number" && r < 0 ? -r : 0 });
      return r === null ? 0 : r;
    }

    begin() {
      const io = this.emu.io.inputs, now = this.emu.nowUs();
      this.mod._wwb_begin(io[0].active ? 1 : 0, io[1].active ? 1 : 0, now);
      this.nextTick = now + TICK_US;
    }
    input(i, active, t) { this.mod._wwb_input(i, active ? 1 : 0, t); }
    hostFrame() { this.mod._wwb_host_frame(this.emu.nowUs()); }
    release() { this.mod._wwb_release(this.emu.nowUs()); }
    get controlled() { return !!this.mod._wwb_controlled(); }
    accepts(op) { return !!this.mod._wwb_accepts(op); }
    // CONNECT 的回复：u8 状态, u32 距离接管还有 ms
    status() {
      const p = this.mod._wwb_buffer(), n = this.mod._wwb_status(this.emu.nowUs(), p);
      return this.mod.HEAPU8.slice(p, p + n);
    }
    // APP_STATE 的回复：程序上报的状态
    report() {
      const p = this.mod._wwb_buffer(), n = this.mod._wwb_report(this.emu.nowUs(), p);
      return this.mod.HEAPU8.slice(p, p + n);
    }
    // 状态文字（页面顶栏用）
    get state() { return ["脱机程序运行中", "控制器连接中", "控制器接管中"][this.status()[0]]; }

    // 模拟器每次推进时调用
    advance(now) {
      if (now < this.nextTick) return;
      this.nextTick = Math.max(this.nextTick + TICK_US, now - TICK_US);
      this.mod._wwb_tick(now);
    }
  }

  WWB.Offline = Offline;
  WWB.clearNvs = () => { try { localStorage.removeItem(NVS_KEY); localStorage.removeItem(CTL_KEY); } catch { /* */ } };
})();
