#include "wwb.h"

#include <string.h>

#include <initializer_list>

namespace wwb {

using namespace proto;

// ---------------------------------------------------------------- 画布

Canvas::Canvas() {
  // 不能用 u8g2_Setup_ssd1306_128x64_noname_f：它的缓冲区是全局静态的，与固件 OLED 驱动共用
  u8g2_SetupDisplay(&u8g2_, u8x8_d_ssd1306_128x64_noname, u8x8_cad_empty, u8x8_byte_empty, u8x8_dummy_cb);
  u8g2_SetupBuffer(&u8g2_, buf_, 8, u8g2_ll_hvline_vertical_top_lsb, U8G2_R0);
  u8g2_SetFontMode(&u8g2_, 1);
  clear();
}

void Canvas::clear() { memset(buf_, 0, sizeof buf_); }

void Canvas::pixel(int x, int y, bool on) {
  if (x < 0 || x >= W || y < 0 || y >= H) return;
  uint8_t &b = buf_[(y >> 3) * W + x];
  if (on) b |= 1 << (y & 7);
  else b &= ~(1 << (y & 7));
}

void Canvas::fade(int x, int y, int w, int h, int level) {
  static const uint8_t BAYER[4][4] = {{0, 8, 2, 10}, {12, 4, 14, 6}, {3, 11, 1, 9}, {15, 7, 13, 5}};
  if (level >= 16) return;
  for (int yy = y < 0 ? 0 : y; yy < y + h && yy < H; yy++) {
    for (int xx = x < 0 ? 0 : x; xx < x + w && xx < W; xx++) {
      if (BAYER[yy & 3][xx & 3] >= level) buf_[(yy >> 3) * W + xx] &= ~(1 << (yy & 7));
    }
  }
}

void Canvas::invert(int x, int y, int w, int h) {
  for (int yy = y < 0 ? 0 : y; yy < y + h && yy < H; yy++) {
    for (int xx = x < 0 ? 0 : x; xx < x + w && xx < W; xx++) buf_[(yy >> 3) * W + xx] ^= 1 << (yy & 7);
  }
}

// ---------------------------------------------------------------- 设备

int Device::send(uint8_t op, const uint8_t *p, size_t n, uint8_t flags) {
  uint8_t reply[8];
  return host_.exec(op, flags, p, n, reply, sizeof reply);
}

void Device::invalidate() { oledValid_ = segValid_ = segConfigValid_ = mxValid_ = mxIntensityValid_ = false; }

void Device::oled(Canvas &c) {
  if (!visible_) return;
  const uint8_t *fb = c.buffer();
  constexpr int W = Canvas::W, PAGES = Canvas::H / 8;
  int p0 = PAGES, p1 = -1, c0 = W, c1 = -1;
  if (oledValid_) {
    for (int p = 0; p < PAGES; p++) {
      for (int x = 0; x < W; x++) {
        if (fb[p * W + x] == oled_[p * W + x]) continue;
        if (p < p0) p0 = p;
        p1 = p;
        if (x < c0) c0 = x;
        if (x > c1) c1 = x;
      }
    }
    if (p1 < 0) return;
  } else {
    p0 = 0, p1 = PAGES - 1, c0 = 0, c1 = W - 1;
  }
  memcpy(oled_, fb, sizeof oled_);
  oledValid_ = true;
  int pages = p1 - p0 + 1, cols = c1 - c0 + 1;
  if (pages == PAGES && cols == W) {
    send(OP_OLED_FRAME, fb, sizeof oled_, F_FLUSH);
    return;
  }
  uint8_t buf[4 + W * PAGES];
  buf[0] = p0, buf[1] = c0, buf[2] = pages, buf[3] = cols;
  for (int i = 0; i < pages; i++) memcpy(buf + 4 + i * cols, fb + (p0 + i) * W + c0, cols);
  send(OP_OLED_BLIT, buf, 4 + pages * cols, F_FLUSH);
}

void Device::seg(const uint8_t segs[4]) {
  if (!visible_ || (segValid_ && !memcmp(seg_, segs, 4))) return;
  memcpy(seg_, segs, 4);
  segValid_ = true;
  send(OP_SEG_RAW, segs, 4);
}

void Device::segConfig(uint8_t brightness, bool on) {
  if (!visible_ || (segConfigValid_ && brightness == segBrightness_ && on == segOn_)) return;
  segBrightness_ = brightness, segOn_ = on, segConfigValid_ = true;
  const uint8_t p[5] = {brightness, on, 50, 2, 5};  // 时序同固件默认值，见 docs/hardware.md
  send(OP_SEG_CONFIG, p, sizeof p);
}

void Device::mx(const uint8_t rows[8]) {
  if (!visible_ || (mxValid_ && !memcmp(mx_, rows, 8))) return;
  memcpy(mx_, rows, 8);
  mxValid_ = true;
  send(OP_MX_FRAME, rows, 8);
}

void Device::mxIntensity(uint8_t level) {
  if (!visible_ || (mxIntensityValid_ && level == mxIntensity_)) return;
  mxIntensity_ = level, mxIntensityValid_ = true;
  const uint8_t p[7] = {level, 1, 0, 0, 0, 0, 0};  // 旋转 1 = 当前安装方向；SPI 时钟不变
  send(OP_MX_CONFIG, p, sizeof p);
}

// ---------------------------------------------------------------- 运行时

void Runtime::begin(bool sw, bool boot, uint64_t now) {
  delete app_;
  dev_.inputs_[SWITCH] = sw;
  dev_.inputs_[BOOT] = boot;
  dev_.visible_ = true;
  dev_.invalidate();
  controlled_ = false;
  app_ = createApp();
  app_->setup(dev_, now);
}

void Runtime::input(Input in, bool active, uint64_t t) {
  dev_.inputs_[in] = active;
  if (app_) app_->input(dev_, in, active, t);
}

// 外设恢复开机默认，让接管的控制器、或回来的脱机程序都从同一个已知状态开始
void Runtime::resetPeripherals() {
  uint8_t reply[8];
  auto exec = [&](uint8_t op, std::initializer_list<uint8_t> p) { host_.exec(op, 0, p.begin(), p.size(), reply, 8); };
  exec(OP_OLED_CLEAR, {0});
  exec(OP_OLED_FLUSH, {});
  exec(OP_OLED_CMD, {0xA6, 0xAF, 0xA4, 0x81, 0xCF, 0xA1, 0xC8, 0x40, 0xD3, 0x00});
  exec(OP_SEG_CONFIG, {3, 1, 50, 2, 5});
  exec(OP_SEG_RAW, {0, 0, 0, 0});
  exec(OP_MX_CONFIG, {1, 1, 0, 0x80, 0x96, 0x98, 0x00});  // 10MHz
  exec(OP_MX_FRAME, {0, 0, 0, 0, 0, 0, 0, 0});
  exec(OP_IO_CONFIG, {0x20, 0x4E, 0, 0});  // 消抖 20ms
  dev_.invalidate();
}

void Runtime::setControlled(bool on, uint64_t now) {
  controlled_ = on;
  dev_.visible_ = !on;
  resetPeripherals();
  if (app_) app_->controller(dev_, on, now);
}

void Runtime::hostFrame(uint64_t now) {
  lastHostUs_ = now;
  if (!controlled_) setControlled(true, now);
}

void Runtime::release(uint64_t now) {
  if (controlled_) setControlled(false, now);
}

void Runtime::tick(uint64_t now) {
  if (controlled_ && now - lastHostUs_ > DETACH_US) setControlled(false, now);
  if (app_) app_->frame(dev_, now);
}

// ---------------------------------------------------------------- 工具

uint8_t segDigit(int d) {
  static const uint8_t DIGITS[] = {0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f};
  return d >= 0 && d <= 9 ? DIGITS[d] : 0;
}

float clamp01(float x) { return x < 0 ? 0 : x > 1 ? 1 : x; }
float easeOutCubic(float x) {
  x = 1 - clamp01(x);
  return 1 - x * x * x;
}
float easeInOutCubic(float x) {
  x = clamp01(x);
  return x < 0.5f ? 4 * x * x * x : 1 - (-2 * x + 2) * (-2 * x + 2) * (-2 * x + 2) / 2;
}
float easeOutBack(float x) {
  x = clamp01(x) - 1;
  return 1 + 2.70158f * x * x * x + 1.70158f * x * x;
}

}  // namespace wwb
