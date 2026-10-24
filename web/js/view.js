// 三块屏、开关、BOOT 键、板载灯的画面。只负责画，状态全部来自模拟器
(function () {
  const WWB = (window.WWB = window.WWB || {});
  const SVG = "http://www.w3.org/2000/svg";
  const el = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(SVG, tag);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };

  // ---------------------------------------------------------------- OLED

  class OledView {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.pixels = new Uint8Array(128 * 64);
      this.prev = new Uint8Array(128 * 64).fill(2);
      this.grid = true;
      this.setScale(4);
      this.watchDpr();
    }
    // 按屏幕的物理像素作画：每个 OLED 像素占整数个物理像素、缝宽一致。
    // 否则在 125%/150% 缩放的屏幕上浏览器会把画布拉伸，点的大小和缝宽忽大忽小，看起来像重影
    setScale(s) {
      const dpr = window.devicePixelRatio || 1;
      this.scale = s;
      this.cell = Math.max(1, Math.round(s * dpr));
      this.gap = this.cell >= 3 ? Math.max(1, Math.round(this.cell * 0.15)) : 0;
      this.canvas.width = 128 * this.cell;
      this.canvas.height = 64 * this.cell;
      this.canvas.style.width = `${(128 * this.cell) / dpr}px`;
      this.canvas.style.height = `${(64 * this.cell) / dpr}px`;
      this.img = this.ctx.createImageData(this.canvas.width, this.canvas.height);
      this.buf = new Uint32Array(this.img.data.buffer);
      this.prev.fill(2);
    }
    // 窗口拖到另一块缩放不同的屏幕时重新适配
    watchDpr() {
      const mq = matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`);
      mq.addEventListener("change", () => {
        this.setScale(this.scale);
        this.watchDpr();
      }, { once: true });
    }
    // 屏上每个像素画成一个小方点，点之间留缝，像真实面板
    render(emu) {
      const px = emu.oledPixels(this.pixels);
      const pn = emu.oled.panel;
      const key = pn.contrast | (this.grid ? 256 : 0);
      if (key === this.prevKey && px.every((v, i) => v === this.prev[i])) return;
      this.prev.set(px);
      this.prevKey = key;
      const s = this.cell, gap = this.gap, w = 128 * s;
      // 对比度只稍微影响亮度（真实 SSD1306 也是这样）
      const k = 0.55 + 0.45 * (pn.contrast / 255);
      const lit = (255 << 24) | (Math.round(255 * k) << 16) | (Math.round(246 * k) << 8) | Math.round(232 * k);  // ABGR
      const off = this.grid ? (12 << 24) | 0xffffff : 0;
      const buf = this.buf;
      buf.fill(0);
      for (let y = 0; y < 64; y++) {
        for (let x = 0; x < 128; x++) {
          const c = px[y * 128 + x] ? lit : off;
          if (!c) continue;
          for (let dy = 0; dy < s - gap; dy++) {
            const row = (y * s + dy) * w + x * s;
            for (let dx = 0; dx < s - gap; dx++) buf[row + dx] = c;
          }
        }
      }
      this.ctx.putImageData(this.img, 0, 0);
    }
  }

  // ---------------------------------------------------------------- 数码管

  // 七段的多边形（单个数字 60×100，段宽 10）
  const SEGMENTS = {
    a: "13,4 47,4 53,10 47,16 13,16 7,10",
    b: "54,11 60,17 60,45 54,51 48,45 48,17",
    c: "54,53 60,59 60,87 54,93 48,87 48,59",
    d: "13,88 47,88 53,94 47,100 13,100 7,94",
    e: "6,53 12,59 12,87 6,93 0,87 0,59",
    f: "6,11 12,17 12,45 6,51 0,45 0,17",
    g: "13,46 47,46 53,52 47,58 13,58 7,52",
  };
  const TM_DUTY = [1, 2, 4, 10, 11, 12, 13, 14];  // TM1637 8 档亮度的脉宽（/16）

  class SegView {
    constructor(svg) {
      svg.setAttribute("viewBox", "-14 -8 330 120");
      const g = el("g", { transform: "skewX(-7) translate(10 0)" }, svg);
      this.segs = [];
      for (let d = 0; d < 4; d++) {
        const x = d * 74 + (d >= 2 ? 22 : 0);
        const dg = el("g", { transform: `translate(${x} 0)` }, g);
        const s = {};
        for (const k of "abcdefg") s[k] = el("polygon", { points: SEGMENTS[k], class: "seg" }, dg);
        this.segs.push(s);
      }
      this.colon = [el("circle", { cx: 150, cy: 32, r: 6, class: "seg" }, g), el("circle", { cx: 146, cy: 72, r: 6, class: "seg" }, g)];
      this.root = svg;
      this.key = "";
    }
    render(emu) {
      const s = emu.seg, on = s.shownOn;
      const key = s.shown.join(",") + on + s.shownBrightness;
      if (key === this.key) return;
      this.key = key;
      s.shown.forEach((v, d) => {
        [..."abcdefg"].forEach((k, bit) => this.segs[d][k].classList.toggle("on", on && !!(v & (1 << bit))));
      });
      const colon = on && !!(s.shown[1] & 0x80);
      this.colon.forEach((c) => c.classList.toggle("on", colon));
      this.root.style.setProperty("--seg-level", (0.3 + 0.7 * Math.sqrt(TM_DUTY[s.shownBrightness] / 14)).toFixed(3));
    }
  }

  // ---------------------------------------------------------------- 点阵

  class MatrixView {
    constructor(svg) {
      svg.setAttribute("viewBox", "0 0 200 200");
      el("rect", { x: 0, y: 0, width: 200, height: 200, rx: 6, class: "mx-face" }, svg);
      this.dots = [];
      for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) this.dots.push(el("circle", { cx: 16 + c * 24, cy: 16 + r * 24, r: 9.5, class: "dot" }, svg));
      }
      this.root = svg;
      this.key = "";
    }
    render(emu) {
      const v = emu.mxView();
      const key = v.rows.join(",") + "/" + v.intensity;
      if (key === this.key) return;
      this.key = key;
      v.rows.forEach((row, r) => {
        for (let c = 0; c < 8; c++) this.dots[r * 8 + c].classList.toggle("on", !!((row >> (7 - c)) & 1));
      });
      // MAX7219 亮度：脉宽 (2i+1)/32
      this.root.style.setProperty("--mx-level", (0.35 + 0.65 * Math.sqrt((2 * v.intensity + 1) / 31)).toFixed(3));
    }
  }

  WWB.views = { OledView, SegView, MatrixView };
})();
