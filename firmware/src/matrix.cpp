#include "matrix.h"

#include <Arduino.h>
#include <SPI.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <soc/gpio_reg.h>
#include <string.h>

#include "board.h"

namespace mx {

constexpr uint32_t CS = 1u << MATRIX_CS;

static SemaphoreHandle_t mutex;
static Stats st;
static uint8_t logical[8];
static uint8_t intensity = 1;
static uint8_t rotation = 1;  // 按当前安装方向需顺时针转 90°
static bool testMode = false, shutdownMode = false;
static uint8_t physShown[8];
static bool physValid = false;  // 模块上的内容是否确定；配置补发时整屏重写
static uint32_t spiHz = 10000000;  // 规格上限 10MHz；实测 20MHz 也能正确显示，见 docs/benchmarks.md

static inline void write(uint8_t reg, uint8_t val) {
  REG_WRITE(GPIO_OUT_W1TC_REG, CS);
  SPI.transfer16((reg << 8) | val);
  REG_WRITE(GPIO_OUT_W1TS_REG, CS);  // 上升沿锁存
}

static inline bool px(const uint8_t *rows, int r, int c) { return rows[r] >> (7 - c) & 1; }

// 逻辑画面顺时针旋转 rotation×90° 后的物理行
static void rotate(const uint8_t *in, uint8_t *out) {
  if (rotation == 0) {
    memcpy(out, in, 8);
    return;
  }
  for (int r = 0; r < 8; r++) {
    uint8_t v = 0;
    for (int c = 0; c < 8; c++) {
      bool on;
      switch (rotation) {
        case 1: on = px(in, 7 - c, r); break;
        case 2: on = px(in, 7 - r, 7 - c); break;
        default: on = px(in, c, 7 - r); break;
      }
      if (on) v |= 0x80 >> c;
    }
    out[r] = v;
  }
}

// 需持有 mutex 且已 beginTransaction
static void writeConfig() {
  write(0x0F, testMode);
  write(0x09, 0);           // 不译码
  write(0x0B, 7);           // 扫描 8 行
  write(0x0A, intensity);
  write(0x0C, !shutdownMode);
}

// 只写变化的行（force 时全写），省下的 SPI 时间留给其他外设
static void writeRows(bool force = false) {
  uint8_t phys[8];
  rotate(logical, phys);
  for (int r = 0; r < 8; r++) {
    if (force || !physValid || phys[r] != physShown[r]) write(r + 1, phys[r]);
  }
  memcpy(physShown, phys, 8);
  physValid = true;
}

void begin() {
  mutex = xSemaphoreCreateMutex();
  pinMode(MATRIX_CS, OUTPUT);
  REG_WRITE(GPIO_OUT_W1TS_REG, CS);
  SPI.begin(MATRIX_CLK, -1, MATRIX_DIN, -1);
  memset(logical, 0, 8);
  refreshConfig();
}

void setFrame(const uint8_t rows[8]) {
  xSemaphoreTake(mutex, portMAX_DELAY);
  memcpy(logical, rows, 8);
  int64_t t0 = esp_timer_get_time();
  SPI.beginTransaction(SPISettings(spiHz, MSBFIRST, SPI_MODE0));
  writeRows();
  SPI.endTransaction();
  uint32_t dt = esp_timer_get_time() - t0;
  st.frames++;
  st.lastUs = dt;
  st.totalUs += dt;
  xSemaphoreGive(mutex);
}

void getFrame(uint8_t rows[8]) { memcpy(rows, logical, 8); }

void config(uint8_t in, uint8_t rot, bool test, bool shutdown, uint32_t hz) {
  xSemaphoreTake(mutex, portMAX_DELAY);
  intensity = in & 0x0F;
  rotation = rot & 3;
  testMode = test;
  shutdownMode = shutdown;
  if (hz) spiHz = hz;
  SPI.beginTransaction(SPISettings(spiHz, MSBFIRST, SPI_MODE0));
  writeConfig();
  writeRows(true);
  SPI.endTransaction();
  xSemaphoreGive(mutex);
}

void getConfig(uint8_t &in, uint8_t &rot, bool &test, bool &shutdown, uint32_t &hz) {
  in = intensity;
  rot = rotation;
  test = testMode;
  shutdown = shutdownMode;
  hz = spiHz;
}

void raw(const uint8_t *pairs, size_t n) {
  xSemaphoreTake(mutex, portMAX_DELAY);
  SPI.beginTransaction(SPISettings(spiHz, MSBFIRST, SPI_MODE0));
  for (size_t i = 0; i + 1 < n; i += 2) write(pairs[i], pairs[i + 1]);
  physValid = false;  // 原始写入可能改了显示行
  SPI.endTransaction();
  xSemaphoreGive(mutex);
}

void refreshConfig() {
  xSemaphoreTake(mutex, portMAX_DELAY);
  SPI.beginTransaction(SPISettings(spiHz, MSBFIRST, SPI_MODE0));
  writeConfig();
  writeRows(true);
  SPI.endTransaction();
  xSemaphoreGive(mutex);
}

uint64_t bench(int count, uint32_t hz) {
  xSemaphoreTake(mutex, portMAX_DELAY);
  SPI.beginTransaction(SPISettings(hz, MSBFIRST, SPI_MODE0));
  int64_t t0 = esp_timer_get_time();
  for (int i = 0; i < count; i++) writeRows(true);
  uint64_t dt = esp_timer_get_time() - t0;
  SPI.endTransaction();
  xSemaphoreGive(mutex);
  return dt;
}

const Stats &stats() { return st; }
void resetStats() { memset(&st, 0, sizeof st); }

}  // namespace mx
