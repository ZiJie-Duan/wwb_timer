// 编辑器里的示例脚本。脚本是一个 async 函数体，可直接使用：
//   dev           设备 API（与 Python 的 wwb.Device 同名同参）
//   sleep(ms)     等待；frame() 等下一个显示帧；pacer(hz) 返回按固定频率等待的函数
//   now()         脚本开始以来的秒数
//   canvas()      128×64 绘图画布（Canvas 2D），画完用 dev.oled_frame(画布) 推上去
//   mx(...)       8 个 "#..#...." 字符串 → 点阵 8 字节
//   segText(s)    文本 → 数码管 4 字节段码
//   Font, Op, Flag, log(...)
(function () {
  const WWB = (window.WWB = window.WWB || {});

  WWB.EXAMPLES = [
    {
      name: "秒表：开关开始/暂停，BOOT 清零",
      code: `// 秒表：拨开关 = 开始 / 暂停，按 BOOT = 清零
// 计时用事件里的设备时间戳 t_us（抖动开始的时刻），不受 20ms 消抖延迟影响
let running = false, acc = 0, since = 0;

dev.on_input(ev => {
  if (ev.name === "switch") {
    if (ev.active && !running) { running = true; since = ev.t_us; }
    if (!ev.active && running) { running = false; acc += ev.t_us - since; }
    log(\`开关 \${ev.active ? "开" : "关"}  t=\${(ev.t_us / 1e6).toFixed(3)}s\`);
  } else if (ev.active) {
    acc = 0;
    if (running) since = ev.t_us;
    log("清零");
  }
});

// 点阵：一根每秒转一圈的指针
function hand(angle) {
  const rows = new Array(8).fill(0);
  for (let k = 0; k <= 8; k++) {
    const x = Math.floor(3.5 + k * 0.5 * Math.sin(angle) + 0.5);
    const y = Math.floor(3.5 - k * 0.5 * Math.cos(angle) + 0.5);
    if (x >= 0 && x < 8 && y >= 0 && y < 8) rows[y] |= 0x80 >> x;
  }
  return rows;
}

const tick = pacer(60);
while (true) {
  const t = await dev.time_us();
  const us = acc + (running ? t - since : 0);
  const cs = Math.floor(us / 1e4) % 100, s = Math.floor(us / 1e6) % 60, m = Math.floor(us / 6e7) % 100;
  const p2 = n => String(n).padStart(2, "0");

  dev.oled_clear();
  dev.oled_text(0, 9, "STOPWATCH", Font.F6X10);
  dev.oled_rect(92, 0, 36, 11, running ? 1 : 2);
  dev.oled_text(97, 9, running ? "RUN" : "STOP", Font.F6X10, running ? 0 : 1);
  dev.oled_text(2, 52, \`\${p2(m)}:\${p2(s)}\`, Font.LOGISOSO32_NUM);
  dev.oled_text(97, 52, "." + p2(cs), Font.LOGISOSO16);
  const bar = Math.round(128 * (us % 6e7) / 6e7);   // 一分钟走满
  if (bar > 0) dev.oled_rect(0, 58, bar, 6);           // 宽度为 0 时设备会报 BAD_ARG
  dev.oled_flush();

  // 运行时冒号每秒闪一下
  const colon = !running || (us % 1e6) < 5e5;
  dev.seg_text(\`\${p2(m)}\${colon ? ":" : ""}\${p2(s)}\`);
  dev.mx_frame(running || us ? hand(2 * Math.PI * (us % 1e6) / 1e6) : mx(
    "........", "..####..", ".#....#.", ".#.##.#.", ".#.##.#.", ".#....#.", "..####..", "........"));
  await tick();
}`,
    },
    {
      name: "弹球：Canvas 画图 → OLED 整帧",
      code: `// 用 Canvas 2D 画图，再整帧推到 OLED（相当于 Python 里 PIL 画图 + dev.oled_frame）
// 设备按真机时序模拟：整帧推送约 10.5ms，所以 OLED 最多约 95 帧/秒，多发的帧会被合并
const g = canvas();
const balls = Array.from({ length: 5 }, (_, i) => ({
  x: 20 + i * 20, y: 10 + i * 8, vx: 1.2 + i * 0.3, vy: 0.9 + i * 0.2, r: 3 + i,
}));
const tick = pacer(100);   // 100 帧/s，略高于 OLED 极限，保证每次推送都有新帧
let n = 0;
while (true) {
  g.fillStyle = "#000"; g.fillRect(0, 0, 128, 64);
  g.strokeStyle = g.fillStyle = "#fff";
  g.strokeRect(0.5, 0.5, 127, 63);
  for (const b of balls) {
    b.x += b.vx; b.y += b.vy;
    if (b.x < b.r + 1 || b.x > 127 - b.r) b.vx = -b.vx;
    if (b.y < b.r + 1 || b.y > 63 - b.r) b.vy = -b.vy;
    g.beginPath(); g.arc(b.x, b.y, b.r, 0, Math.PI * 2); g.fill();
  }
  g.fillText(\`frame \${n++}\`, 4, 3);
  dev.oled_frame(g);

  // 数码管显示帧号，点阵显示第一个球的位置
  dev.seg_text(String(n % 10000));
  const b = balls[0], rows = new Array(8).fill(0);
  rows[Math.min(7, Math.floor(b.y / 8))] = 0x80 >> Math.min(7, Math.floor(b.x / 16));
  dev.mx_frame(rows);
  await tick();
}`,
    },
    {
      name: "字体与绘图命令",
      code: `// 设备端绘图命令：文字（6 种 u8g2 字体，含中文）、矩形、反色、对比度
// 按 BOOT 切换整屏反色（SSD1306 命令 A7/A6），拨开关切换对比度
dev.oled_clear();
// y 是基线；各字体的高度：6x10 约 7、9x15 约 10、中文 12、logisoso16/24/32 即其字号
dev.oled_text(0, 8, "6x10 Hello", Font.F6X10);
dev.oled_text(0, 22, "9x15 Hi", Font.F9X15);
dev.oled_text(68, 22, "中文12点阵", Font.WQY12_CN);
dev.oled_text(0, 41, "Ag16", Font.LOGISOSO16);
dev.oled_text(60, 50, "24", Font.LOGISOSO24_NUM);
dev.oled_text(92, 63, "32", Font.LOGISOSO32_NUM);
dev.oled_rect(0, 46, 20, 18, 2);   // 边框
dev.oled_rect(4, 50, 12, 10, 1);   // 填充
dev.oled_rect(24, 46, 32, 18, 1);
dev.oled_text(31, 59, "inv", Font.F6X10, 2);   // 反色文字
dev.oled_flush();

dev.seg_text("FONT");
dev.mx_frame(mx("#.#.#.#.", ".#.#.#.#", "#.#.#.#.", ".#.#.#.#", "#.#.#.#.", ".#.#.#.#", "#.#.#.#.", ".#.#.#.#"));

let inverted = false;
dev.on_input(ev => {
  if (ev.name === "boot" && ev.active) { inverted = !inverted; dev.oled_cmd(inverted ? 0xA7 : 0xA6); }
  if (ev.name === "switch") dev.oled_contrast(ev.active ? 0x10 : 0xCF);
});
log("按 BOOT 反色，拨开关切换对比度");
await new Promise(() => {});   // 保持运行，等事件`,
    },
    {
      name: "点阵与数码管动画",
      code: `// 点阵：跳动的心 + 滚动文字；数码管：倒计时 + 亮度呼吸
const HEART = mx("........", ".##.##..", "#######.", "#######.", ".#####..", "..###...", "...#....", "........");
const SMALL = mx("........", "........", ".##.##..", ".#####..", "..###...", "...#....", "........", "........");
const FONT = { // 5 列字形，按列存（bit0 在上）
  W: [0x7f, 0x20, 0x18, 0x20, 0x7f], B: [0x7f, 0x49, 0x49, 0x49, 0x36], " ": [0, 0, 0, 0, 0],
  T: [0x01, 0x01, 0x7f, 0x01, 0x01], I: [0x00, 0x41, 0x7f, 0x41, 0x00], M: [0x7f, 0x02, 0x0c, 0x02, 0x7f],
  E: [0x7f, 0x49, 0x49, 0x49, 0x41], R: [0x7f, 0x09, 0x19, 0x29, 0x46],
};
const cols = [];
for (const ch of "WWB TIMER  ") cols.push(...FONT[ch], 0);

dev.oled_clear();
dev.oled_text(0, 12, "matrix + 7seg demo", Font.F6X10);
dev.oled_text(0, 30, "开关：心跳 / 滚动字", Font.WQY12_CN, 1, { flush: true });

let scroll = false;
dev.on_input(ev => { if (ev.name === "switch") scroll = ev.active; });

const tick = pacer(30);
let n = 0, count = 600;
while (true) {
  const t = now();
  if (scroll) {
    const off = Math.floor(t * 12);
    const rows = new Array(8).fill(0);
    for (let x = 0; x < 8; x++) {
      const c = cols[(off + x) % cols.length];
      for (let y = 0; y < 7; y++) if (c >> y & 1) rows[y] |= 0x80 >> x;
    }
    dev.mx_frame(rows);
  } else {
    const beat = t % 1 < 0.15 || (t % 1 > 0.3 && t % 1 < 0.42);
    dev.mx_frame(beat ? HEART : SMALL);
    dev.mx_config(beat ? 6 : 1, 1);
  }
  if (n++ % 3 === 0) {
    count = Math.max(0, count - 1);
    dev.seg_text(\`\${String(Math.floor(count / 10)).padStart(3, " ")}\${count % 10}\`);
  }
  dev.seg_config(Math.round(3.5 + 3.5 * Math.sin(t * 3)));
  await tick();
}`,
    },
    {
      name: "空白模板",
      code: `// 在这里写动画 / 交互。Ctrl+Enter 运行，Esc 停止
dev.oled_clear();
dev.oled_text(0, 20, "hello", Font.F9X15, 1, { flush: true });
dev.seg_text("12:34");
dev.mx_frame(mx("...##...", "..####..", ".######.", "##.##.##", "...##...", "...##...", "...##...", "...##..."));

dev.on_input(ev => log(ev.name, ev.active ? "on" : "off", ev.t_us));

while (true) {
  await frame();
}`,
    },
  ];
})();
