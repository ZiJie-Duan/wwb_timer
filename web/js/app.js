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

  // ---------------------------------------------------------------- Python 桥与程序

  // 由 python -m wwb.sim 提供页面时自动连接；也可用 ?bridge=ws://host:port/ws 指定
  const bridgeUrl = new URLSearchParams(location.search).get("bridge") ||
    (location.protocol.startsWith("http") ? `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws` : null);
  const pill = $("bridge"), appsEl = $("apps"), autoEl = $("auto");
  let ws = null, apps = [], state = { running: null, selected: null, auto: true };

  const control = (msg) => ws && ws.readyState === 1 && ws.send(JSON.stringify(msg));
  autoEl.onchange = () => control({ cmd: "auto", on: autoEl.checked });

  function renderApps() {
    appsEl.textContent = "";
    if (!apps.length) {
      appsEl.innerHTML = '<div class="empty muted">apps/ 里还没有程序</div>';
      return;
    }
    for (const a of apps) {
      const running = state.running === a.id;
      const row = document.createElement("div");
      row.className = "app" + (running ? " running" : state.selected === a.id ? " selected" : "");
      row.innerHTML = '<div class="app-main"><div class="app-title"></div><div class="app-id"></div><div class="app-desc"></div></div><div class="app-btns"></div>';
      row.querySelector(".app-title").textContent = a.title;
      row.querySelector(".app-id").textContent = a.id + (running ? "  · 运行中" : "");
      row.querySelector(".app-desc").textContent = a.desc;
      const btns = row.querySelector(".app-btns");
      const btn = (label, cls, msg) => {
        const b = document.createElement("button");
        b.textContent = label;
        if (cls) b.className = cls;
        b.onclick = (e) => { e.stopPropagation(); control(msg); };
        btns.appendChild(b);
      };
      if (running) {
        btn("↻ 重启", "", { cmd: "restart" });
        btn("■ 停止", "", { cmd: "stop" });
      } else {
        btn("▶ 运行", "primary", { cmd: "run", id: a.id });
      }
      row.onclick = () => !running && control({ cmd: "run", id: a.id });
      appsEl.appendChild(row);
    }
  }

  function setPill(text, ok) {
    pill.textContent = text;
    pill.classList.toggle("ok", ok);
  }

  function connectBridge() {
    if (!bridgeUrl) {
      setPill("Python 桥：未连接（直接打开的文件）", false);
      appsEl.innerHTML = '<div class="empty muted">运行 <code>python -m wwb.sim</code>，再打开它给出的网址，才能选择程序</div>';
      return;
    }
    let link = null, fresh = false;
    try { ws = new WebSocket(bridgeUrl); } catch { return; }
    ws.binaryType = "arraybuffer";
    ws.onopen = () => {
      link = emu.addLink("usb", (data) => ws.readyState === 1 && ws.send(data));
      setPill("Python 桥：已连接", true);
      fresh = true;
    };
    ws.onmessage = (e) => {
      if (typeof e.data !== "string") {
        link && link.receive(new Uint8Array(e.data));
        return;
      }
      const m = JSON.parse(e.data);
      if (m.type === "apps") {
        apps = m.apps;
        $("apps-hint").textContent = `${apps.length} 个`;
        renderApps();
      } else if (m.type === "state") {
        state = m;
        autoEl.checked = m.auto;
        renderApps();
      } else if (m.type === "out") {
        if (m.replay && fresh) logEl.textContent = "";  // 重连后桥会重发最近的输出
        fresh = false;
        log(m.kind === "out" ? "user" : m.kind === "err" ? "error" : "info", m.line);
      } else if (m.type === "clients") {
        setPill(m.n ? `Python 桥：${m.n} 个程序连接中` : "Python 桥：已连接", true);
      }
    };
    ws.onclose = (e) => {
      if (link) {
        link.close();
        log("info", "Python 桥断开" + (e.reason ? `：${e.reason}` : ""));
      }
      link = null;
      setPill("Python 桥：未连接", false);
      if (e.code !== 4000) setTimeout(connectBridge, 2000);  // 4000 = 被新打开的页面顶替
    };
  }
  connectBridge();

  log("info", "模拟器已启动。S / 空格 拨开关，按住 B = BOOT");
})();
