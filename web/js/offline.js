// 脱机程序（native/ 的 C++，编成 web/js/native.js）在模拟器里的运行环境，与固件的 offline.cpp 对应：
// 程序的命令直接交给模拟器执行；控制器（Python 程序）发来命令就接管，释放或 1.5s 没有命令就交还。
// 断电保留的数据存在 localStorage，刷新网页 / 重启设备都不会丢
(function () {
  const WWB = window.WWB;
  const { Op, Err } = WWB.proto;
  const NVS_KEY = "wwb.sim.nvs";
  const TICK_US = 16000;  // 与固件相同：约 60 帧/秒
  // 芯片上程序不能用的命令（会影响通道或耗时很长）
  const BLOCKED = new Set([Op.SOURCE, Op.REBOOT, Op.UART_BAUD, Op.SUBSCRIBE, Op.BENCH, Op.RELEASE]);

  const nvs = {
    load() {
      try {
        const s = localStorage.getItem(NVS_KEY);
        return s ? Uint8Array.from(atob(s), (c) => c.charCodeAt(0)) : null;
      } catch { return null; }
    },
    save(bytes) {
      try { localStorage.setItem(NVS_KEY, btoa(String.fromCharCode(...bytes))); } catch { /* 隐私模式等 */ }
    },
  };

  class Offline {
    static async load(emu) {
      if (typeof window.createWwbNative !== "function") return null;
      const off = new Offline(emu);
      off.mod = await window.createWwbNative({
        wwbExec: (op, flags, payload) => off.exec(op, flags, payload),
        wwbLoad: () => nvs.load(),
        wwbSave: (bytes) => nvs.save(bytes),
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

    // 模拟器每次推进时调用
    advance(now) {
      if (now < this.nextTick) return;
      this.nextTick = Math.max(this.nextTick + TICK_US, now - TICK_US);
      this.mod._wwb_tick(now);
    }
  }

  WWB.Offline = Offline;
  WWB.clearNvs = () => { try { localStorage.removeItem(NVS_KEY); } catch { /* */ } };
})();
