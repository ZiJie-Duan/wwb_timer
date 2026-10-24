// wwb timer：脱机计时器（没有控制器时运行）
//
// 开关拨上 = 计时，拨下 = 停止；时间一直累计，断电保留。开关在上面时开机 = 清零。
// 数码管显示 时:分，OLED 显示秒。每完成一次“开 → 关”，点阵从左上角起多亮一个点（低亮度，最多 64 个）。
// 开机后每隔一段时间提示“插入控制器”，直到第一次拨开关或接入控制器。
// 控制器连接、确认、中断、断开各有一段插头动画；接管期间计时照常按开关进行。
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "wwb/wwb.h"

using namespace wwb;

namespace {

constexpr uint64_t MS = 1000, S = 1000000;
constexpr float PI = 3.14159265f;

// 各段动画时长
constexpr uint64_t BOOT_US = 2300 * MS;
constexpr uint64_t RESET_US = 1300 * MS;
constexpr uint64_t HINT_US = 5200 * MS;
constexpr uint64_t HINT_GAP_US = 10 * S;
constexpr uint64_t ABORT_US = 900 * MS;
constexpr uint64_t DETACH_US = 2000 * MS;
constexpr uint64_t START_US = 1200 * MS;
constexpr uint64_t STOP_US = 1500 * MS;
constexpr uint64_t FADE_IN_US = 300 * MS;
constexpr uint64_t ROLL_US = 180 * MS;      // 换秒时数字滚动
constexpr uint64_t SAVE_EVERY_US = 30 * S;  // 计时中定期保存，断电最多丢这么久

constexpr uint8_t SEG_LEVEL = 3;  // 数码管常态亮度（0-7）
constexpr uint8_t MX_DIM = 1, MX_BRIGHT = 7;
constexpr int SLOTS = 64;

constexpr uint32_t MAGIC = 0x31627777;  // "wwb1"
struct Saved {
  uint32_t magic;
  uint32_t cycles;
  uint64_t totalMs;
};

const uint8_t *const SECONDS = u8g2_font_logisoso38_tn;
const uint8_t *const SMALL = u8g2_font_logisoso16_tr;
const uint8_t *const CN = u8g2_font_wqy12_t_gb2312b;
const uint8_t *const TINY = u8g2_font_6x10_tf;

const uint8_t CHEVRON_UP[4] = {0x18, 0x3C, 0x66, 0xC3};
constexpr float CHEVRON_ROW_S = 0.03f;  // 箭头每走一行的时间
constexpr float ARROWS_S = 0.67f;       // 三个箭头全部移出画面的时间（22 行）

float sec(uint64_t us) { return us / 1e6f; }
float span(float t, float a, float b) { return clamp01((t - a) / (b - a)); }
int lerp(int a, int b, float k) { return a + (int)lroundf((b - a) * k); }

// 停止时的缓慢闪烁：亮 1.8s → 渐暗 0.5s → 灭 0.4s → 渐亮 0.5s
float breath(uint64_t since) {
  float t = fmodf(sec(since), 3.2f);
  if (t < 1.8f) return 1;
  if (t < 2.3f) return 0.5f + 0.5f * cosf((t - 1.8f) / 0.5f * PI);
  if (t < 2.7f) return 0;
  return 0.5f - 0.5f * cosf((t - 2.7f) / 0.5f * PI);
}

// ---------------------------------------------------------------- 点阵图形

void setDot(uint8_t rows[8], int r, int c) {
  if (r >= 0 && r < 8 && c >= 0 && c < 8) rows[r] |= 0x80 >> c;
}

void dots(uint8_t rows[8], uint32_t n) {
  for (uint32_t i = 0; i < n && i < SLOTS; i++) setDot(rows, i / 8, i % 8);
}

// 三个箭头依次穿过画面，t 秒；ARROWS_S 时全部移出。向下时整体上下翻转
void arrows(uint8_t rows[8], float t, bool up) {
  int y = 8 - (int)(t / CHEVRON_ROW_S);  // 第一个箭头的顶行
  for (int k = 0; k < 3; k++) {
    for (int i = 0; i < 4; i++) {
      int r = y + k * 5 + i;
      if (!up) r = 7 - r;
      if (r >= 0 && r < 8) rows[r] |= CHEVRON_UP[i];
    }
  }
}

// 插头与右边的插座。body = 插头本体左列，PLUG_IN 时插好
constexpr int PLUG_IN = 3, PLUG_NEAR = 1, PLUG_OUT = -5;
void mxPlug(uint8_t rows[8], int body, bool socket = true) {
  if (socket) {
    for (int r = 1; r <= 6; r++) setDot(rows, r, 7);
    setDot(rows, 1, 6), setDot(rows, 6, 6);
  }
  for (int c = 0; c < body; c++) setDot(rows, 3, c), setDot(rows, 4, c);  // 线
  for (int r = 2; r <= 5; r++) setDot(rows, r, body), setDot(rows, r, body + 1);
  for (int c = body + 2; c <= body + 3; c++) setDot(rows, 2, c), setDot(rows, 5, c);  // 两根插脚
}

// 插好后数据沿线流进去：线上一个暗点往右走
void mxFlow(uint8_t rows[8], float t) {
  int c = (int)(t / 0.1f) % 4;
  if (c < PLUG_IN) rows[3] &= ~(0x80 >> c), rows[4] &= ~(0x80 >> c);
}

// 时:分。100 小时起显示“123h”，1000 小时起只显示小时数（这块数码管没有小数点）
void timeSegs(uint64_t totalSec, bool colon, uint8_t out[4]) {
  uint64_t h = totalSec / 3600, m = totalSec / 60 % 60;
  if (h < 100) {
    out[0] = h >= 10 ? segDigit(h / 10) : 0;
    out[1] = segDigit(h % 10) | (colon ? 0x80 : 0);
    out[2] = segDigit(m / 10);
    out[3] = segDigit(m % 10);
  } else if (h < 1000) {
    out[0] = segDigit(h / 100), out[1] = segDigit(h / 10 % 10), out[2] = segDigit(h % 10), out[3] = 0x74;  // h
  } else {
    if (h > 9999) h = 9999;
    for (int i = 3; i >= 0; i--, h /= 10) out[i] = segDigit(h % 10);
  }
}

// ---------------------------------------------------------------- 程序

class Timer : public App {
 public:
  void setup(Device &d, uint64_t now) override;
  void input(Device &d, Input in, bool active, uint64_t t) override;
  void link(Device &d, Link ev, uint64_t now) override;
  void frame(Device &d, uint64_t now) override;

 private:
  enum Scene { NONE, BOOT, RESET, HINT, CONNECTING, CONNECTED, ABORTED, DETACH };
  enum Fx { FX_NONE, FX_START, FX_STOP };

  uint64_t totalMs(uint64_t now) const { return baseMs_ + (running_ && now > runStart_ ? (now - runStart_) / MS : 0); }
  bool blinkOn(uint64_t now) const { return totalMs(now) % 1000 < 500; }
  float breathNow(uint64_t now) const { return breath(now > stopAt_ ? now - stopAt_ : 0); }
  void save(Device &d, uint64_t now);
  void setScene(Scene s, uint64_t now) { scene_ = s, sceneAt_ = now; }
  void update(uint64_t now);

  void drawSeg(Device &d, uint64_t now);
  void drawMatrix(Device &d, uint64_t now);
  void drawOled(Device &d, uint64_t now);
  void oledTimer(uint64_t now, const char *label);
  void oledBoot(float t);
  void oledHint(float t);
  void oledLink(float t);
  void drawPlug(int bodyX);
  void drawSocket(bool lit);
  void drawSparks(float s);
  void drawFlow(int bodyX, float t);

  Canvas c_;
  bool running_ = false;
  uint64_t baseMs_ = 0;     // 不含进行中这一段的累计时间
  uint64_t runStart_ = 0;
  uint32_t cycles_ = 0;     // 完成的“开 → 关”次数
  uint64_t stopAt_ = 0;     // 停止时刻（闪烁相位从这里算起）
  uint64_t lastSave_ = 0;
  Scene scene_ = BOOT;
  uint64_t sceneAt_ = 0;
  Fx fx_ = FX_NONE;
  uint64_t fxAt_ = 0;
  bool hinting_ = false;    // 开机后、第一次拨开关前
  bool resetBoot_ = false;  // 开关在上面时开机：清零并直接开始计时
  uint64_t nextHint_ = 0;
  float linkFrom_ = 0;      // 连接中断时插头走到了哪里（0..1）
};

// ---------------------------------------------------------------- 逻辑

void Timer::setup(Device &d, uint64_t now) {
  Saved s{};
  size_t got = 0;
  d.load(&s, sizeof s, got);
  if (got == sizeof s && s.magic == MAGIC) cycles_ = s.cycles, baseMs_ = s.totalMs;
  setScene(BOOT, now);
  stopAt_ = now + 1800 * MS;  // 开机动画里数码管从这时起显示时间
  lastSave_ = now;
  if (d.input(SWITCH)) {
    resetBoot_ = true;
    baseMs_ = 0, cycles_ = 0;
    running_ = true;
    runStart_ = now + BOOT_US + RESET_US;  // 清零提示播完才开始走
    save(d, now);
  } else {
    hinting_ = true;
  }
}

void Timer::save(Device &d, uint64_t now) {
  Saved s{MAGIC, cycles_, totalMs(now)};
  d.save(&s, sizeof s);
  lastSave_ = now;
}

void Timer::input(Device &d, Input in, bool active, uint64_t t) {
  if (in != SWITCH) return;
  hinting_ = false;
  if (scene_ == HINT) setScene(NONE, t);
  if (active && !running_) {
    running_ = true;
    runStart_ = t;
    fx_ = FX_START, fxAt_ = t;
    save(d, t);
  } else if (!active && running_) {
    baseMs_ = totalMs(t);
    running_ = false;
    cycles_++;
    stopAt_ = t;
    fx_ = FX_STOP, fxAt_ = t;
    save(d, t);
  }
}

void Timer::link(Device &d, Link ev, uint64_t now) {
  switch (ev) {
    case LINK_CONNECTING:
      hinting_ = false;
      setScene(CONNECTING, now);
      break;
    case LINK_CONFIRMED:
      setScene(CONNECTED, now);
      break;
    case LINK_ABORTED:
      linkFrom_ = scene_ == CONNECTED ? 1 : scene_ == CONNECTING ? easeOutCubic(sec(now - sceneAt_) / 3) : 0;
      setScene(ABORTED, now);
      break;
    case LINK_RELEASED:
      setScene(DETACH, now);
      fx_ = FX_NONE;
      break;
  }
}

void Timer::update(uint64_t now) {
  uint64_t el = now - sceneAt_;
  if (scene_ == BOOT && el >= BOOT_US) {
    if (resetBoot_) setScene(RESET, now);
    else if (hinting_) setScene(HINT, now);
    else setScene(NONE, now);
  } else if (scene_ == RESET && el >= RESET_US) {
    setScene(NONE, now);
    fx_ = FX_START, fxAt_ = now;
  } else if (scene_ == HINT && el >= HINT_US) {
    setScene(NONE, now);
    nextHint_ = now + HINT_GAP_US;
  } else if ((scene_ == DETACH && el >= DETACH_US) || (scene_ == ABORTED && el >= ABORT_US)) {
    setScene(NONE, now);
  }
  if (scene_ == NONE && hinting_ && now >= nextHint_) setScene(HINT, now);
  if (fx_ != FX_NONE && now - fxAt_ >= (fx_ == FX_START ? START_US : STOP_US)) fx_ = FX_NONE;
}

void Timer::frame(Device &d, uint64_t now) {
  if (running_ && now - lastSave_ >= SAVE_EVERY_US) save(d, now);
  if (!d.visible()) return;
  update(now);
  drawSeg(d, now);
  drawMatrix(d, now);
  drawOled(d, now);
}

// ---------------------------------------------------------------- 数码管

void Timer::drawSeg(Device &d, uint64_t now) {
  uint8_t s[4] = {0, 0, 0, 0};
  uint8_t level = SEG_LEVEL;
  bool on = true;
  float t = sec(now - sceneAt_);
  if (scene_ == BOOT && t < 1.8f) {
    // 一条小蛇绕四位数字的外框跑两圈，然后全亮、熄灭
    static const uint8_t PATH[12][2] = {{0, 0}, {1, 0}, {2, 0}, {3, 0}, {3, 1}, {3, 2},
                                        {3, 3}, {2, 3}, {1, 3}, {0, 3}, {0, 4}, {0, 5}};
    if (t < 1.2f) {
      int head = (int)(t / 0.05f);
      for (int k = 0; k < 3 && head - k >= 0; k++) {
        const uint8_t *p = PATH[(head - k) % 12];
        s[p[0]] |= 1 << p[1];
      }
    } else if (t < 1.55f) {
      memset(s, 0xFF, 4);
      level = 7;
    }
  } else {
    bool colon = running_ ? blinkOn(now) : true;
    timeSegs(totalMs(now) / 1000, colon, s);
    if (scene_ == RESET) {
      on = t > 0.9f || (int)(t / 0.15f) % 2 == 0;
    } else if (running_) {
      if (fx_ == FX_START && now - fxAt_ < 300 * MS) level = 7;
    } else {
      float b = breathNow(now);
      if (b >= 0.85f) level = 3;
      else if (b >= 0.6f) level = 2;
      else if (b >= 0.4f) level = 1;
      else if (b >= 0.15f) level = 0;
      else on = false;
    }
  }
  d.segConfig(level, on);
  d.seg(s);
}

// ---------------------------------------------------------------- 点阵

void Timer::drawMatrix(Device &d, uint64_t now) {
  uint8_t rows[8] = {0};
  uint8_t level = MX_DIM;
  float t = sec(now - sceneAt_);

  switch (scene_) {
    case BOOT:
      // 对角线扫亮、扫灭，再把已有的点逐个点亮
      level = 4;
      for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 8; c++) {
          float k = t < 0.6f ? t / 0.6f * 15 : (t - 0.6f) / 0.6f * 15;
          if (t < 0.6f ? r + c <= k : t < 1.2f && r + c > k) setDot(rows, r, c);
        }
      }
      if (t >= 1.4f) {
        dots(rows, (uint32_t)((t - 1.4f) / 0.4f * (cycles_ < SLOTS ? cycles_ : SLOTS)));
        level = MX_DIM;
      }
      break;

    case RESET: {
      // 全亮，然后自上而下清空
      level = 6;
      int cleared = t < 0.4f ? 0 : (int)((t - 0.4f) / 0.5f * 8);
      for (int r = cleared; r < 8; r++) rows[r] = 0xFF;
      break;
    }

    case HINT:
      // 插头滑进插座，“咔”一下闪亮，数据流进去，最后自上而下消失
      level = 5;
      if (t < 1.25f) {
        mxPlug(rows, lerp(PLUG_OUT, PLUG_IN, easeOutCubic(span(t, 0.2f, 1.25f))));
      } else if (t < 1.33f) {
        memset(rows, 0xFF, 8);
        level = 9;
      } else {
        mxPlug(rows, PLUG_IN);
        mxFlow(rows, t);
      }
      if (t > 4.4f) {
        int gone = (int)((t - 4.4f) / 0.5f * 8);
        for (int r = 0; r < gone && r < 8; r++) rows[r] = 0;
        if (gone >= 8) dots(rows, cycles_), level = MX_DIM;
      }
      break;

    case CONNECTING:
      // 插头慢慢靠近，插座像心跳一样闪
      level = 4;
      mxPlug(rows, lerp(PLUG_OUT, PLUG_NEAR, easeOutCubic(t / 3)), (int)(t / 0.4f) % 2 == 0);
      break;

    case CONNECTED:
      // 插进去，闪一下，数据流进去
      level = 5;
      if (t < 0.12f) {
        mxPlug(rows, lerp(PLUG_NEAR, PLUG_IN, t / 0.12f));
      } else if (t < 0.22f) {
        memset(rows, 0xFF, 8);
        level = 9;
      } else {
        mxPlug(rows, PLUG_IN);
        mxFlow(rows, t);
      }
      break;

    case ABORTED:
      // 没插上：插头退回去
      level = 4;
      if (t < 0.6f) {
        int from = lerp(PLUG_OUT, PLUG_NEAR, linkFrom_);
        mxPlug(rows, lerp(from, PLUG_OUT, easeInOutCubic(t / 0.6f)));
      } else {
        dots(rows, cycles_);
        level = MX_DIM;
      }
      break;

    case DETACH:
      // 插头被拔出、退走，插座消失，回到点数
      level = 5;
      if (t < 0.25f) {
        mxPlug(rows, PLUG_IN);
      } else if (t < 1.2f) {
        mxPlug(rows, lerp(PLUG_IN, PLUG_OUT, easeInOutCubic(span(t, 0.25f, 0.85f))), (int)(t / 0.12f) % 2 == 0);
      } else if (t < 1.6f) {
        mxPlug(rows, PLUG_OUT);
        int gone = (int)((t - 1.2f) / 0.4f * 8);
        for (int r = 0; r < gone && r < 8; r++) rows[r] = 0;
      } else {
        dots(rows, cycles_);
        level = MX_DIM;
      }
      break;

    case NONE:
      if (fx_ == FX_START) {
        // 三个箭头冲上去，全部出画面后从中心炸开一圈，再落回点数
        float e = sec(now - fxAt_);
        const float RING = ARROWS_S + 0.3f;
        if (e < ARROWS_S) {
          level = MX_BRIGHT;
          arrows(rows, e, true);
        } else {
          dots(rows, cycles_);
          if (e < RING) {
            level = MX_BRIGHT;
            float rad = (e - ARROWS_S) / 0.3f * 6;
            for (int r = 0; r < 8; r++) {
              for (int c = 0; c < 8; c++) {
                float dist = sqrtf((r - 3.5f) * (r - 3.5f) + (c - 3.5f) * (c - 3.5f));
                if (fabsf(dist - rad) < 0.7f) setDot(rows, r, c);
              }
            }
          } else {
            level = (uint8_t)lerp(MX_BRIGHT, MX_DIM, span(e, RING, sec(START_US)));
          }
        }
      } else if (fx_ == FX_STOP) {
        // 三个箭头落下、全部出画面后，新的一个点掉进自己的格子，闪两下
        float e = sec(now - fxAt_);
        uint32_t slot = cycles_ - 1;
        const float LAND = ARROWS_S + 0.35f;
        if (e < ARROWS_S) {
          level = MX_BRIGHT;
          arrows(rows, e, false);
        } else if (slot >= SLOTS) {
          // 格子已经满了：整屏闪一下
          dots(rows, SLOTS);
          if (e < ARROWS_S + 0.2f) memset(rows, 0xFF, 8);
          level = (uint8_t)lerp(MX_BRIGHT, MX_DIM, span(e, ARROWS_S + 0.2f, sec(STOP_US)));
        } else if (e < LAND) {
          level = 4;
          dots(rows, slot);
          float k = span(e, ARROWS_S, LAND);
          setDot(rows, (int)(k * k * (slot / 8) + 0.5f), slot % 8);
        } else {
          dots(rows, slot);
          if ((int)((e - LAND) / 0.07f) % 2 == 0 || e > LAND + 0.28f) setDot(rows, slot / 8, slot % 8);
          level = (uint8_t)lerp(MX_BRIGHT, MX_DIM, span(e, LAND, sec(STOP_US)));
        }
      } else {
        dots(rows, cycles_);
        // 计时中：下一个格子跟着冒号闪
        if (running_ && cycles_ < SLOTS && blinkOn(now)) setDot(rows, cycles_ / 8, cycles_ % 8);
      }
      break;
  }
  d.mxIntensity(level);
  d.mx(rows);
}

// ---------------------------------------------------------------- OLED

void Timer::drawOled(Device &d, uint64_t now) {
  float t = sec(now - sceneAt_);
  switch (scene_) {
    case BOOT: oledBoot(t); break;
    case HINT: oledHint(t); break;
    case CONNECTING:
    case CONNECTED:
    case ABORTED:
    case DETACH: oledLink(t); break;
    case RESET: oledTimer(now, "已清零"); break;
    case NONE:
      oledTimer(now, nullptr);
      if (now - sceneAt_ < FADE_IN_US) c_.fade(0, 0, 128, 64, (int)(span(t, 0, sec(FADE_IN_US)) * 16));
      break;
  }
  d.oled(c_);
}

void Timer::oledTimer(uint64_t now, const char *label) {
  u8g2_t *u = c_.u();
  c_.clear();
  uint64_t ms = totalMs(now);
  bool blink = blinkOn(now);
  float fe = sec(now - fxAt_);

  // 状态行
  u8g2_SetDrawColor(u, 1);
  if (running_) {
    if (blink) u8g2_DrawDisc(u, 4, 6, 3, U8G2_DRAW_ALL);
    else u8g2_DrawCircle(u, 4, 6, 3, U8G2_DRAW_ALL);
  } else {
    u8g2_DrawBox(u, 1, 2, 3, 9);
    u8g2_DrawBox(u, 6, 2, 3, 9);
  }
  u8g2_SetFont(u, CN);
  u8g2_DrawUTF8(u, 12, 11, label ? label : running_ ? "计时中" : "已停止");
  char buf[32];
  snprintf(buf, sizeof buf, running_ ? "第 %u 次" : "共 %u 次", (unsigned)(running_ ? cycles_ + 1 : cycles_));
  u8g2_DrawUTF8(u, 128 - u8g2_GetUTF8Width(u, buf), 11, buf);

  // 秒（时、分在数码管上）。换秒时变了的那一位往上滚
  int secNow = (int)(ms / 1000 % 60), secPrev = (secNow + 59) % 60;
  uint64_t into = ms % 1000;
  float roll = running_ && ms >= 1000 && into < ROLL_US / MS ? easeOutCubic(into / (float)(ROLL_US / MS)) : 1;
  const int DW = 25, H = 38, UNIT_W = 12, GAP = 3;
  int x0 = (128 - (2 * DW + GAP + UNIT_W)) / 2, base = 52;
  if (fx_ == FX_START) base += lroundf((1 - easeOutBack(fe / 0.4f)) * 10);
  if (fx_ == FX_STOP) base -= lroundf((1 - easeOutCubic(fe / 0.4f)) * 6);
  bool show = !(label && sec(now - sceneAt_) < 0.9f && (int)(sec(now - sceneAt_) / 0.15f) % 2);
  if (show) {
    u8g2_SetFont(u, SECONDS);
    for (int i = 0; i < 2; i++) {
      int cur = i ? secNow % 10 : secNow / 10, prev = i ? secPrev % 10 : secPrev / 10;
      char a[2] = {(char)('0' + cur), 0}, b[2] = {(char)('0' + prev), 0};
      int x = x0 + i * DW;
      if (roll >= 1 || cur == prev) {
        u8g2_DrawStr(u, x, base, a);
        continue;
      }
      u8g2_SetClipWindow(u, x, base - H, x + DW, base + 1);
      int dy = lroundf(roll * (H + 4));
      u8g2_DrawStr(u, x, base - dy, b);
      u8g2_DrawStr(u, x, base + H + 4 - dy, a);
      u8g2_SetMaxClipWindow(u);
    }
    u8g2_SetFont(u, CN);
    u8g2_DrawUTF8(u, x0 + 2 * DW + GAP, base, "秒");
  }
  if (!running_ && !label) c_.fade(0, 13, 128, 41, (int)lroundf(breathNow(now) * 16));

  // 底部 64 格：和点阵一样，每完成一次开关多亮一格
  const float LAND = ARROWS_S + 0.35f;  // 与点阵上新点落地同步
  bool landing = fx_ == FX_STOP && cycles_ <= SLOTS;
  for (int i = 0; i < SLOTS; i++) {
    int cx = 1 + (i % 32) * 4, cy = 56 + (i / 32) * 4;
    bool fresh = landing && (uint32_t)i == cycles_ - 1;
    bool lit = (uint32_t)i < cycles_ && !(fresh && fe < LAND);
    if (running_ && (uint32_t)i == cycles_ && blink) lit = true;
    if (fresh && fe >= LAND && fe < LAND + 0.3f) {
      u8g2_DrawBox(u, cx - 1, cy - 1, 5, 5);  // 刚加上的一格先大后小
      continue;
    }
    if (lit) u8g2_DrawBox(u, cx, cy, 3, 3);
    else u8g2_DrawPixel(u, cx + 1, cy + 1);
  }
  if (landing && fe >= LAND) {
    // “+1” 从新格子上方飘起、淡出
    float k = span(fe, LAND, sec(STOP_US));
    int i = cycles_ - 1, cx = 1 + (i % 32) * 4;
    int ty = 54 - (int)(easeOutCubic(k) * 8);
    int tx = cx - 4 < 0 ? 0 : cx - 4 > 116 ? 116 : cx - 4;
    u8g2_SetFont(u, TINY);
    u8g2_SetDrawColor(u, 2);
    u8g2_DrawStr(u, tx, ty, "+1");
    u8g2_SetDrawColor(u, 1);
    c_.fade(tx, ty - 8, 13, 9, (int)((1 - span(k, 0.4f, 1)) * 16));
  }

  // 开始：一条亮带自下而上扫过；停止：自上而下
  if ((fx_ == FX_START || fx_ == FX_STOP) && fe < 0.35f) {
    int band = (int)(easeInOutCubic(fe / 0.35f) * 72);
    c_.invert(0, fx_ == FX_START ? 64 - band : band - 8, 128, 6);
  }
}

void Timer::oledBoot(float t) {
  u8g2_t *u = c_.u();
  c_.clear();
  u8g2_SetDrawColor(u, 1);
  if (t < 0.3f) {
    // 像老显示器开机：中间先亮一条线
    int w = (int)(easeOutCubic(t / 0.3f) * 128);
    u8g2_DrawHLine(u, (128 - w) / 2, 31, w);
  } else {
    u8g2_SetFont(u, SMALL);
    const char *title = "wwb timer";
    int w = u8g2_GetStrWidth(u, title);
    u8g2_DrawStr(u, (128 - w) / 2, 38, title);
    // 亮线上下张开，露出标题
    int h = (int)(easeOutCubic(span(t, 0.3f, 0.75f)) * 44);
    for (int y = 0; y < 64; y++) {
      if (y < 31 - h / 2 || y > 32 + h / 2) c_.fade(0, y, 128, 1, 0);
    }
    if (h < 40) {
      u8g2_DrawHLine(u, 0, 31 - h / 2, 128);
      u8g2_DrawHLine(u, 0, 32 + h / 2, 128);
    }
    // 下划线从左往右画出来
    int uw = (int)(easeInOutCubic(span(t, 0.75f, 1.3f)) * w);
    u8g2_DrawHLine(u, (128 - w) / 2, 44, uw);
    if (t > 1.3f) {
      u8g2_SetFont(u, TINY);
      const char *sub = "v0.3";
      u8g2_DrawStr(u, (128 - u8g2_GetStrWidth(u, sub)) / 2, 57, sub);
      c_.fade(0, 48, 128, 10, (int)(span(t, 1.3f, 1.6f) * 16));
    }
  }
  if (t > 1.9f) c_.fade(0, 0, 128, 64, (int)((1 - span(t, 1.9f, 2.3f)) * 16));
}

// ---------------------------------------------------------------- 插头动画

constexpr int SOCKET_X = 84, ICON_Y = 18;
constexpr int PLUGGED_X = SOCKET_X - 18;  // 插好时插头本体的位置
constexpr int NEAR_X = PLUGGED_X - 8;     // 连接中最终停在这里，确认后插进去
constexpr int AWAY_X = -40;

// 插头：线从左边进来，bodyX 为插头本体左边
void Timer::drawPlug(int bodyX) {
  u8g2_t *u = c_.u();
  int cy = ICON_Y;
  u8g2_SetDrawColor(u, 1);
  if (bodyX > 0) u8g2_DrawBox(u, 0, cy - 1, bodyX, 3);
  u8g2_DrawRBox(u, bodyX, cy - 7, 16, 15, 2);
  u8g2_SetDrawColor(u, 0);
  u8g2_DrawVLine(u, bodyX + 5, cy - 4, 9);
  u8g2_DrawVLine(u, bodyX + 8, cy - 4, 9);
  u8g2_SetDrawColor(u, 1);
  u8g2_DrawBox(u, bodyX + 16, cy - 4, 7, 2);
  u8g2_DrawBox(u, bodyX + 16, cy + 3, 7, 2);
}

void Timer::drawSocket(bool lit) {
  u8g2_t *u = c_.u();
  u8g2_SetDrawColor(u, 1);
  u8g2_DrawRFrame(u, SOCKET_X, ICON_Y - 11, 20, 23, 3);
  u8g2_DrawFrame(u, SOCKET_X + 3, ICON_Y - 5, 8, 4);
  u8g2_DrawFrame(u, SOCKET_X + 3, ICON_Y + 2, 8, 4);
  // 接口旁的小灯
  if (lit) u8g2_DrawDisc(u, SOCKET_X + 15, ICON_Y, 2, U8G2_DRAW_ALL);
  else u8g2_DrawCircle(u, SOCKET_X + 15, ICON_Y, 2, U8G2_DRAW_ALL);
}

// 插上那一下的火花，s 从 0 到 1
void Timer::drawSparks(float s) {
  u8g2_t *u = c_.u();
  int r0 = 4 + (int)(s * 6), r1 = 7 + (int)(s * 9);
  int cx = SOCKET_X - 1, cy = ICON_Y;
  for (int i = 0; i < 6; i++) {
    float a = (i * 60 + 30) * PI / 180;
    u8g2_DrawLine(u, cx + lroundf(cosf(a) * r0), cy + lroundf(sinf(a) * r0), cx + lroundf(cosf(a) * r1),
                  cy + lroundf(sinf(a) * r1));
  }
}

// 插好后数据沿着线流进去
void Timer::drawFlow(int bodyX, float t) {
  u8g2_t *u = c_.u();
  u8g2_SetDrawColor(u, 0);
  int phase = (int)(t * 40) % 12;
  for (int x = phase; x < bodyX - 2; x += 12) u8g2_DrawBox(u, x, ICON_Y, 3, 1);
  u8g2_SetDrawColor(u, 1);
}

void Timer::oledHint(float t) {
  u8g2_t *u = c_.u();
  c_.clear();
  const float CONTACT = 1.25f;

  // 插头滑过来、“咔”一下插进接口
  int bodyX = lerp(-30, PLUGGED_X, easeOutBack(span(t, 0.2f, CONTACT)));
  bool plugged = t >= CONTACT;
  drawSocket(plugged && (int)((t - CONTACT) / 0.25f) % 2 == 0);
  drawPlug(bodyX);
  if (plugged && t < CONTACT + 0.35f) drawSparks((t - CONTACT) / 0.35f);
  if (plugged) drawFlow(PLUGGED_X, t - CONTACT);

  // 文字：第一行逐字打出来，第二行淡入
  u8g2_SetFont(u, CN);
  const char *l1 = "插入控制器", *l2 = "解锁更多功能";
  int w1 = u8g2_GetUTF8Width(u, l1), w2 = u8g2_GetUTF8Width(u, l2);
  int n = (int)((t - 0.45f) / 0.12f);
  if (n > 0) {
    char part[32];
    int bytes = (n > 5 ? 5 : n) * 3;  // 每个汉字 3 字节
    memcpy(part, l1, bytes);
    part[bytes] = 0;
    u8g2_DrawUTF8(u, (128 - w1) / 2, 47, part);
  }
  if (t > 1.4f) {
    u8g2_DrawUTF8(u, (128 - w2) / 2, 62, l2);
    c_.fade(0, 50, 128, 14, (int)(span(t, 1.4f, 2.0f) * 16));
  }
  // 整体淡入淡出
  float a = span(t, 0, 0.25f) * (1 - span(t, sec(HINT_US) - 0.5f, sec(HINT_US)));
  c_.fade(0, 0, 128, 64, (int)(a * 16));
}

// 控制器连接中 / 已连接 / 连接中断 / 已断开
void Timer::oledLink(float t) {
  u8g2_t *u = c_.u();
  c_.clear();
  float alpha = 1;
  u8g2_SetFont(u, CN);
  auto center = [&](const char *msg, int y) { u8g2_DrawUTF8(u, (128 - u8g2_GetUTF8Width(u, msg)) / 2, y, msg); };
  switch (scene_) {
    case CONNECTING: {
      // 插头慢慢靠近，接口的灯慢闪；下面是 3 秒的稳定进度
      static const char *const TEXT[] = {"正在连接控制器", "正在连接控制器.", "正在连接控制器..", "正在连接控制器..."};
      drawSocket((int)(t / 0.4f) % 2 == 0);
      drawPlug(lerp(AWAY_X, NEAR_X, easeOutCubic(t / 3)));
      u8g2_DrawUTF8(u, (128 - u8g2_GetUTF8Width(u, TEXT[0])) / 2, 46, TEXT[(int)(t / 0.3f) % 4]);
      u8g2_DrawFrame(u, 24, 54, 80, 5);
      u8g2_DrawHLine(u, 26, 56, (int)(clamp01(t / 3) * 76));
      alpha = span(t, 0, 0.25f);
      break;
    }
    case CONNECTED: {
      // 插进去，火花，灯亮，数据流进去；然后整屏淡出，交给控制器
      drawSocket(t >= 0.15f);
      drawPlug(lerp(NEAR_X, PLUGGED_X, easeOutBack(span(t, 0, 0.15f))));
      if (t >= 0.15f && t < 0.5f) drawSparks((t - 0.15f) / 0.35f);
      if (t >= 0.15f) drawFlow(PLUGGED_X, t - 0.15f);
      center("控制器已连接", 50);
      alpha = 1 - span(t, 0.85f, sec(Runtime::CONFIRM_US));
      break;
    }
    case ABORTED: {
      // 没插上：插头退回去
      drawSocket(false);
      drawPlug(lerp(lerp(AWAY_X, NEAR_X, linkFrom_), AWAY_X, easeInOutCubic(span(t, 0.05f, 0.6f))));
      center("连接中断", 50);
      alpha = 1 - span(t, sec(ABORT_US) - 0.3f, sec(ABORT_US));
      break;
    }
    case DETACH: {
      // 插头被拔出、向左退走，接口处一个小叉
      drawSocket(false);
      drawPlug(lerp(PLUGGED_X, AWAY_X, easeInOutCubic(span(t, 0.25f, 0.85f))));
      if (t > 0.25f && t < 0.55f) {
        int cx = SOCKET_X - 4, cy = ICON_Y;
        u8g2_DrawLine(u, cx - 3, cy - 3, cx + 3, cy + 3);
        u8g2_DrawLine(u, cx - 3, cy + 3, cx + 3, cy - 3);
      }
      center("控制器已断开", 50);
      c_.fade(0, 38, 128, 16, (int)(span(t, 0.1f, 0.45f) * 16));
      alpha = 1 - span(t, sec(DETACH_US) - 0.4f, sec(DETACH_US));
      break;
    }
    default:
      break;
  }
  c_.fade(0, 0, 128, 64, (int)(alpha * 16));
}

}  // namespace

App *wwb::createApp() { return new Timer(); }
