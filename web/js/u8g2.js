// U8g2 字体解码与绘图的 JS 移植，只实现固件用到的部分：drawUTF8（透明模式）、drawBox、drawFrame。
// 帧缓冲与 SSD1306 显存一致：8 页 × 128 列，第 page*128+x 字节是 x 列的 8 个纵向像素，LSB 在上。
// 字体格式参考 U8g2 的 u8g2_font.c（u8g2_font_decode_glyph / u8g2_font_get_glyph_data）。
(function () {
  const WWB = (window.WWB = window.WWB || {});
  const W = 128, H = 64;

  function b64(s) {
    const bin = atob(s);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  class Font {
    constructor(name, data) {
      const s8 = (v) => (v << 24) >> 24;
      const word = (i) => (data[i] << 8) | data[i + 1];
      this.name = name;
      this.data = data;
      this.glyphCnt = data[0];
      this.bitsPer0 = data[2];
      this.bitsPer1 = data[3];
      this.bitsW = data[4];
      this.bitsH = data[5];
      this.bitsX = data[6];
      this.bitsY = data[7];
      this.bitsD = data[8];
      this.ascentA = s8(data[13]);
      this.descentG = s8(data[14]);
      this.posA = word(17);
      this.posa = word(19);
      this.posUnicode = word(21);
      this.cache = new Map();
    }

    // 返回字形数据起点（编码字节之后），找不到返回 -1
    glyphOffset(enc) {
      const d = this.data;
      let p = 23;
      if (enc <= 255) {
        if (enc >= 97) p += this.posa;
        else if (enc >= 65) p += this.posA;
        for (;;) {
          if (d[p + 1] === 0) return -1;
          if (d[p] === enc) return p + 2;
          p += d[p + 1];
        }
      }
      p += this.posUnicode;
      let table = p, e;
      do {
        p += (d[table] << 8) | d[table + 1];
        e = (d[table + 2] << 8) | d[table + 3];
        table += 4;
      } while (e < enc);
      for (;;) {
        e = (d[p] << 8) | d[p + 1];
        if (e === 0) return -1;
        if (e === enc) return p + 3;
        p += d[p + 2];
      }
    }

    // 解码为 { w, h, x, y, d, runs: [[lx, ly, len], ...] }（只记前景）；结果缓存
    glyph(enc) {
      let g = this.cache.get(enc);
      if (g !== undefined) return g;
      const off = this.glyphOffset(enc);
      if (off < 0) {
        this.cache.set(enc, null);
        return null;
      }
      const d = this.data;
      let ptr = off, bit = 0;
      const bits = (cnt) => {
        let v = d[ptr] >> bit;
        let end = bit + cnt;
        if (end >= 8) {
          ptr++;
          v |= d[ptr] << (8 - bit);
          end -= 8;
        }
        bit = end;
        return v & ((1 << cnt) - 1);
      };
      const sbits = (cnt) => bits(cnt) - (1 << (cnt - 1));
      const w = bits(this.bitsW), h = bits(this.bitsH);
      const x = sbits(this.bitsX), y = sbits(this.bitsY), dx = sbits(this.bitsD);
      const runs = [];
      if (w > 0) {
        let lx = 0, ly = 0;
        const len = (n, fg) => {
          let cnt = n;
          for (;;) {
            const rem = w - lx;
            const cur = cnt < rem ? cnt : rem;
            if (fg && cur > 0) runs.push(lx, ly, cur);
            if (cnt < rem) break;
            cnt -= rem;
            lx = 0;
            ly++;
          }
          lx += cnt;
        };
        for (;;) {
          const a = bits(this.bitsPer0), b = bits(this.bitsPer1);
          do {
            len(a, false);
            len(b, true);
          } while (bits(1) !== 0);
          if (ly >= h) break;
        }
      }
      g = { w, h, x, y, d: dx, runs };
      this.cache.set(enc, g);
      return g;
    }
  }

  const FONTS = (WWB.FONT_DATA || []).map(([name, data]) => new Font(name, b64(data)));

  // color：0 清除 / 1 点亮 / 2 反色
  function hline(fb, x, y, w, color) {
    if (y < 0 || y >= H) return;
    let x0 = Math.max(x, 0), x1 = Math.min(x + w, W);
    const bit = 1 << (y & 7), row = (y >> 3) * W;
    for (let i = x0; i < x1; i++) {
      if (color === 1) fb[row + i] |= bit;
      else if (color === 0) fb[row + i] &= ~bit;
      else fb[row + i] ^= bit;
    }
  }
  function vline(fb, x, y, h, color) {
    for (let i = 0; i < h; i++) hline(fb, x, y + i, 1, color);
  }

  function drawBox(fb, x, y, w, h, color) {
    for (let i = 0; i < h; i++) hline(fb, x, y + i, w, color);
  }

  // 与 u8g2_DrawFrame 相同：四条边互不重叠（反色模式下角上不会被反两次）
  function drawFrame(fb, x, y, w, h, color) {
    const xt = x;
    hline(fb, x, y, w, color);
    if (h >= 2) {
      h -= 2;
      y++;
      if (h > 0) {
        vline(fb, x, y, h, color);
        x += w - 1;
        vline(fb, x, y, h, color);
        y += h;
      }
      hline(fb, xt, y, w, color);
    }
  }

  // 透明模式（setFontMode(1)）画 UTF-8 文本，y 为基线；返回总宽度（与 drawUTF8 一致）
  function drawUTF8(fb, font, x, y, text, color) {
    let width = 0;
    for (const ch of text) {
      const cp = ch.codePointAt(0);
      if (cp > 0xffff) continue;
      const g = font.glyph(cp);
      if (!g) continue;
      if (g.w > 0) {
        const tx = x + width + g.x, ty = y - g.h - g.y;
        const r = g.runs;
        for (let i = 0; i < r.length; i += 3) hline(fb, tx + r[i], ty + r[i + 1], r[i + 2], color);
      }
      width += g.d;
    }
    return width;
  }

  function textWidth(font, text) {
    let width = 0;
    for (const ch of text) {
      const g = font.glyph(ch.codePointAt(0));
      if (g) width += g.d;
    }
    return width;
  }

  WWB.u8g2 = { W, H, FONTS, Font, drawUTF8, textWidth, drawBox, drawFrame, hline };
})();
