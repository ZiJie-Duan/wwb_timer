// 页面：模拟器 + 画面 + Python 桥 + 脚本编辑器
(function () {
  const WWB = window.WWB;
  const P = WWB.proto;
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* 隐私模式等 */ } },
  };

  const emu = new WWB.Emulator();
  const oled = new WWB.views.OledView($("oled"));
  const seg = new WWB.views.SegView($("seg"));
  const matrix = new WWB.views.MatrixView($("matrix"));

  // ---------------------------------------------------------------- 控制台

  const logEl = $("log");
  let last = null;
  function log(kind, ...args) {
    const text = args.map((a) => (typeof a === "object" ? JSON.stringify(a) : String(a))).join(" ");
    const t = new Date();
    const ts = `${String(t.getMinutes()).padStart(2, "0")}:${String(t.getSeconds()).padStart(2, "0")}.${String(t.getMilliseconds()).padStart(3, "0")}`;
    // 连续相同的消息合并成一行并计数（比如每帧都出错时）
    if (last && last.kind === kind && last.text === text && last.el.isConnected) {
      last.n++;
      last.el.textContent = `${ts}  ${text}  ×${last.n}`;
      return;
    }
    const line = document.createElement("div");
    line.className = "line " + kind;
    line.textContent = `${ts}  ${text}`;
    last = { kind, text, el: line, n: 1 };
    logEl.appendChild(line);
    while (logEl.childElementCount > 500) logEl.firstChild.remove();
    logEl.scrollTop = logEl.scrollHeight;
  }
  $("clear-log").onclick = () => (logEl.textContent = "");

  // ---------------------------------------------------------------- 画面与时序

  function frameLoop() {
    emu.advance();
    oled.render(emu);
    seg.render(emu);
    matrix.render(emu);
    $("led").classList.toggle("on", emu.io.led);
    const pn = emu.oled.panel;
    $("oled-state").textContent = [!pn.on && "关显示", pn.invert && "反色", pn.allOn && "全亮", pn.contrast !== 0xcf && `对比度 ${pn.contrast}`].filter(Boolean).join(" · ");
    requestAnimationFrame(frameLoop);
  }
  requestAnimationFrame(frameLoop);
  setInterval(() => emu.advance(), 2);  // 页面不刷新时（后台标签）也按时推进推送与消抖

  $("scale").value = store.get("wwb.sim.scale") || "4";
  oled.setScale(+$("scale").value);
  $("scale").onchange = () => { oled.setScale(+$("scale").value); store.set("wwb.sim.scale", $("scale").value); };
  $("grid").onchange = () => (oled.grid = $("grid").checked);
  $("reboot").onclick = () => { emu.reset(); log("info", "设备已重启"); };
  emu.on((kind) => kind === "reboot" && log("info", "设备收到 REBOOT，已重启"));

  // ---------------------------------------------------------------- 开关 / BOOT

  const sw = $("switch"), boot = $("boot");
  function setSwitch(on) {
    emu.setInput(0, on);
    sw.setAttribute("aria-pressed", on);
    sw.classList.toggle("on", on);
    $("switch-state").textContent = on ? "开" : "关";
  }
  function setBoot(down) {
    emu.setInput(1, down);
    boot.classList.toggle("down", down);
    $("boot-state").textContent = down ? "按下" : "松开";
  }
  sw.onclick = () => setSwitch(!emu.io.inputs[0].level);
  boot.addEventListener("pointerdown", (e) => { boot.setPointerCapture(e.pointerId); setBoot(true); });
  boot.addEventListener("pointerup", () => setBoot(false));
  boot.addEventListener("pointercancel", () => setBoot(false));
  const typing = () => ["TEXTAREA", "INPUT", "SELECT"].includes(document.activeElement?.tagName);
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { stopScript(); return; }
    if (typing() || e.ctrlKey || e.metaKey || e.altKey) return;
    if ((e.key === "s" || e.key === "S" || e.key === " ") && !e.repeat) { e.preventDefault(); setSwitch(!emu.io.inputs[0].level); }
    if ((e.key === "b" || e.key === "B") && !e.repeat) setBoot(true);
  });
  window.addEventListener("keyup", (e) => { if (e.key === "b" || e.key === "B") setBoot(false); });
  window.addEventListener("blur", () => emu.io.inputs[1].level && setBoot(false));

  // ---------------------------------------------------------------- 统计

  const traffic = new Map();  // "link op" → {count, err}
  emu.on((kind, d) => {
    if (kind !== "frame") return;
    const k = `${d.link} ${d.op}`;
    const t = traffic.get(k) || { link: d.link, op: d.op, count: 0, err: 0, bytes: 0 };
    t.count++;
    t.bytes += d.len;
    if (d.err) t.err++;
    traffic.set(k, t);
  });
  let prevStats = null;
  setInterval(() => {
    const s = JSON.parse(emu.statsJson());
    if (prevStats) {
      const dt = (s.uptime_us - prevStats.uptime_us) / 1e6;
      if (dt > 0) {
        const r = (a, b) => ((a - b) / dt).toFixed(0);
        $("rates").textContent = `OLED ${r(s.oled.pushes, prevStats.oled.pushes)} fps · 数码管 ${r(s.seg.updates, prevStats.seg.updates)}/s · 点阵 ${r(s.mx.frames, prevStats.mx.frames)}/s`;
      }
    }
    prevStats = s;
    const rows = [...traffic.values()].sort((a, b) => a.link.localeCompare(b.link) || a.op - b.op);
    const body = $("traffic").tBodies[0];
    body.textContent = "";
    if (!rows.length) {
      body.innerHTML = '<tr><td class="muted">最近 1 秒没有命令</td></tr>';
    } else {
      for (const t of rows) {
        const tr = body.insertRow();
        tr.innerHTML = `<td>${t.link}</td><td>${P.OpName[t.op] || "0x" + t.op.toString(16)}</td><td class="num">${t.count}/s</td>` +
          `<td class="num muted">${(t.bytes / 1024).toFixed(1)} KiB/s</td><td class="${t.err ? "err" : "muted"}">${t.err ? t.err + " 错误" : ""}</td>`;
      }
    }
    traffic.clear();
  }, 1000);

  // ---------------------------------------------------------------- Python 桥

  // 由 python -m wwb.sim 提供页面时自动连接；也可用 ?bridge=ws://host:port/ws 指定
  const bridgeUrl = new URLSearchParams(location.search).get("bridge") ||
    (location.protocol.startsWith("http") ? `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws` : null);
  const pill = $("bridge");
  let bridgeClients = 0;
  function connectBridge() {
    if (!bridgeUrl) {
      pill.textContent = "Python 桥：未启用（直接打开的文件）";
      return;
    }
    let ws;
    try { ws = new WebSocket(bridgeUrl); } catch { return; }
    ws.binaryType = "arraybuffer";
    let link = null;
    ws.onopen = () => {
      link = emu.addLink("usb", (data) => ws.readyState === 1 && ws.send(data));
      pill.textContent = "Python 桥：已连接";
      pill.classList.add("ok");
      log("info", "已连接 Python 桥", bridgeUrl);
    };
    ws.onmessage = (e) => {
      if (typeof e.data === "string") {
        const m = JSON.parse(e.data);
        if (m.clients !== undefined) {
          // 两边同时画会互相覆盖：Python 程序连上时停掉网页脚本
          if (m.clients > bridgeClients && current) {
            stopScript();
            log("info", "Python 程序已连接，网页脚本已停止");
          }
          bridgeClients = m.clients;
          pill.textContent = m.clients ? `Python 桥：${m.clients} 个程序` : "Python 桥：已连接，等程序";
          if (m.note) log("info", m.note);
        }
        return;
      }
      link && link.receive(new Uint8Array(e.data));
    };
    ws.onclose = (e) => {
      if (link) {
        link.close();
        log("info", "Python 桥断开" + (e.reason ? `：${e.reason}` : ""));
      }
      link = null;
      pill.textContent = "Python 桥：未连接";
      pill.classList.remove("ok");
      if (e.code !== 4000) setTimeout(connectBridge, 2000);  // 4000 = 被新打开的页面顶替
    };
  }
  connectBridge();

  // ---------------------------------------------------------------- 脚本

  const code = $("code"), select = $("examples");
  WWB.EXAMPLES.forEach((ex, i) => select.add(new Option(ex.name, i)));
  select.add(new Option("（我的脚本）", "mine"));
  const saved = store.get("wwb.sim.code");
  code.value = saved ?? WWB.EXAMPLES[0].code;
  const idx = WWB.EXAMPLES.findIndex((e) => e.code === code.value);
  select.value = idx >= 0 ? String(idx) : "mine";
  select.onchange = () => {
    if (select.value === "mine") return;
    const isExample = WWB.EXAMPLES.some((e) => e.code === code.value);
    if (!isExample && code.value.trim() && !confirm("用示例替换编辑器里的内容？")) {
      select.value = "mine";
      return;
    }
    code.value = WWB.EXAMPLES[+select.value].code;
    store.set("wwb.sim.code", code.value);
    runScript();
  };
  code.addEventListener("input", () => {
    store.set("wwb.sim.code", code.value);
    if (!WWB.EXAMPLES.some((e) => e.code === code.value)) select.value = "mine";
  });
  code.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      runScript();
    } else if (e.key === "Tab" && !e.shiftKey) {
      e.preventDefault();
      document.execCommand("insertText", false, "  ");
    }
  });
  $("run").onclick = runScript;
  $("stop").onclick = stopScript;

  const STOP = Symbol("stop");
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  const PARAMS = ["dev", "sleep", "frame", "pacer", "now", "canvas", "toFrame", "mx", "segText", "Font", "Op", "Flag", "log"];
  let current = null;

  function stopScript() {
    if (!current) return;
    current.stop();
  }

  // 脚本里第几行（Function 构造的函数体前面多了 2 行）
  function scriptLine(err) {
    const m = /<anonymous>:(\d+):(\d+)/.exec(err.stack || "") || /Function:(\d+):(\d+)/.exec(err.stack || "");
    return m ? ` （第 ${m[1] - 2} 行）` : "";
  }

  function runScript() {
    if (current) current.stop(true);
    let fn;
    try {
      fn = new AsyncFunction(...PARAMS, code.value);
    } catch (e) {
      log("error", "语法错误：" + e.message);
      return;
    }
    let abort;
    const cancelled = new Promise((_, rej) => (abort = () => rej(STOP)));
    cancelled.catch(() => {});
    const run = { stopped: false };
    const dev = new WWB.Device(emu, { onError: (e) => !run.stopped && log("error", e.message) });
    const guard = (p) => Promise.race([p, cancelled]);
    const t0 = performance.now();
    run.stop = (restarting) => {
      if (run.stopped) return;
      run.stopped = true;
      abort();
      dev.close();
      if (current === run) current = null;
      $("run-state").textContent = restarting ? "" : "已停止";
      $("stop").disabled = true;
    };
    current = run;
    $("stop").disabled = false;
    $("run-state").textContent = "运行中";

    const api = {
      dev,
      sleep: (ms) => guard(new Promise((r) => setTimeout(r, ms))),
      frame: () => guard(new Promise((r) => requestAnimationFrame(r))),
      // 返回一个按固定频率等待的函数；落后时不补帧
      pacer: (hz) => {
        const period = 1000 / hz;
        let next = performance.now();
        return () => {
          next = Math.max(next + period, performance.now());
          return guard(new Promise((r) => setTimeout(r, Math.max(0, next - performance.now()))));
        };
      },
      now: () => (performance.now() - t0) / 1000,
      canvas: WWB.makeCanvas,
      toFrame: WWB.toFrame,
      mx: (...rows) => WWB.mxRows(rows.length === 1 && Array.isArray(rows[0]) ? rows[0] : rows),
      segText: WWB.segText,
      Font: P.Font, Op: P.Op, Flag: P.Flag,
      log: (...a) => log("user", ...a),
    };
    const ex = WWB.EXAMPLES.find((e) => e.code === code.value);
    log("info", `运行：${ex ? ex.name : "我的脚本"}`);
    fn(...PARAMS.map((k) => api[k])).then(
      () => { if (!run.stopped) { log("info", "脚本结束"); run.stop(); } },
      (e) => {
        if (e === STOP || run.stopped) return;
        log("error", (e && e.message ? e.message : String(e)) + scriptLine(e));
        run.stop();
      },
    );
  }

  log("info", "模拟器已启动。Ctrl+Enter 运行脚本；S / 空格 拨开关，按住 B = BOOT");
  runScript();
})();
