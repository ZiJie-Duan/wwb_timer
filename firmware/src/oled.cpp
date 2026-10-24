#include "oled.h"

#include <driver/i2c_master.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>
#include <string.h>

#include "board.h"

namespace oled {

// 只用 u8g2 在内存里画图；它的整帧缓冲排列与 SSD1306 显存一致（按页、每字节纵向 8 像素）
class Canvas : public U8G2 {
 public:
  Canvas() { u8g2_Setup_ssd1306_i2c_128x64_noname_f(&u8g2, U8G2_R0, u8x8_byte_empty, u8x8_dummy_cb); }
};

static Canvas canvas;
static SemaphoreHandle_t fbMutex, busMutex;
static TaskHandle_t task;
static i2c_master_bus_handle_t bus;
static i2c_master_dev_handle_t dev;
static uint8_t addr = 0;
static uint32_t hz = 1100000;  // 实测 1.1MHz 零错误、约 95fps；更高设定会落入驱动分频的不可用区间，见 docs/benchmarks.md
static Stats st;

// 脏矩形（页、列，闭区间）；page0 > page1 表示无
static int dPage0 = PAGES, dPage1 = -1, dCol0 = W, dCol1 = -1;

// 推送缓冲：首字节留给 I2C 控制字节 0x40（后续为显存数据）
static uint8_t txBuf[1 + W * PAGES];
static uint8_t benchBuf[1 + W * PAGES];

static bool i2cWrite(const uint8_t *buf, size_t len) {
  return i2c_master_transmit(dev, buf, len, 200) == ESP_OK;
}

static bool addDevice(uint32_t speed) {
  i2c_device_config_t cfg = {};
  cfg.dev_addr_length = I2C_ADDR_BIT_LEN_7;
  cfg.device_address = addr;
  cfg.scl_speed_hz = speed;
  return i2c_master_bus_add_device(bus, &cfg, &dev) == ESP_OK;
}

static bool sendCommands(const uint8_t *cmds, size_t n) {
  uint8_t buf[32];
  buf[0] = 0x00;  // 控制字节：后续均为命令
  while (n) {
    size_t k = n > sizeof buf - 1 ? sizeof buf - 1 : n;
    memcpy(buf + 1, cmds, k);
    if (!i2cWrite(buf, k + 1)) return false;
    cmds += k;
    n -= k;
  }
  return true;
}

// 设置写入窗口后一次性写入 buf[1..len]；buf[0] 留给控制字节。需持有 busMutex
static bool pushRegion(int p0, int p1, int c0, int c1, uint8_t *buf, size_t len) {
  const uint8_t win[] = {0x21, (uint8_t)c0, (uint8_t)c1, 0x22, (uint8_t)p0, (uint8_t)p1};
  if (!sendCommands(win, sizeof win)) return false;
  buf[0] = 0x40;
  return i2cWrite(buf, len + 1);
}

static void pushTask(void *) {
  for (;;) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    for (;;) {
      xSemaphoreTake(fbMutex, portMAX_DELAY);
      if (dPage0 > dPage1) {
        xSemaphoreGive(fbMutex);
        break;
      }
      int p0 = dPage0, p1 = dPage1, c0 = dCol0, c1 = dCol1;
      dPage0 = PAGES; dPage1 = -1; dCol0 = W; dCol1 = -1;
      int cols = c1 - c0 + 1;
      const uint8_t *src = canvas.getBufferPtr();
      size_t len = 0;
      for (int p = p0; p <= p1; p++, len += cols) memcpy(txBuf + 1 + len, src + p * W + c0, cols);
      xSemaphoreGive(fbMutex);

      xSemaphoreTake(busMutex, portMAX_DELAY);
      int64_t t0 = esp_timer_get_time();
      bool ok = pushRegion(p0, p1, c0, c1, txBuf, len);
      uint32_t dt = esp_timer_get_time() - t0;
      xSemaphoreGive(busMutex);

      st.pushes++;
      st.bytes += len;
      st.lastUs = dt;
      st.totalUs += dt;
      if (!ok) st.errors++;
    }
  }
}

static bool initPanel() {
  static const uint8_t seq[] = {
    0xAE,              // 关显示
    0xD5, 0xF0,        // 内部振荡器调到最高，提高面板刷新率
    0xA8, 0x3F,        // 64 行
    0xD3, 0x00,        // 无偏移
    0x40,              // 起始行 0
    0x8D, 0x14,        // 电荷泵开
    0x20, 0x00,        // 水平寻址
    0xA1, 0xC8,        // 段重映射 + 行扫描反向（与 u8g2 R0 方向一致）
    0xDA, 0x12,
    0x81, 0xCF,        // 对比度
    0xD9, 0xF1,
    0xDB, 0x40,
    0x2E,              // 关滚动
    0xA4, 0xA6,        // 按显存显示、正常（非反色）
    0xAF,              // 开显示
  };
  return sendCommands(seq, sizeof seq);
}

bool begin() {
  fbMutex = xSemaphoreCreateMutex();
  busMutex = xSemaphoreCreateMutex();
  canvas.clearBuffer();
  // 优先级高于接收任务：I2C 驱动每 32 字节要回到本任务补一次 FIFO，被命令处理压住时总线会空等。
  // 本任务几乎不占 CPU（大部分时间阻塞在 I2C 完成信号上），提高优先级不会饿死别的任务
  xTaskCreate(pushTask, "oled", 4096, nullptr, 7, &task);

  i2c_master_bus_config_t cfg = {};
  cfg.i2c_port = I2C_NUM_0;
  cfg.sda_io_num = (gpio_num_t)OLED_SDA;
  cfg.scl_io_num = (gpio_num_t)OLED_SCL;
  cfg.clk_source = I2C_CLK_SRC_DEFAULT;
  cfg.glitch_ignore_cnt = 7;
  cfg.flags.enable_internal_pullup = true;
  if (i2c_new_master_bus(&cfg, &bus) != ESP_OK) return false;
  for (uint8_t a : {0x3C, 0x3D}) {
    if (i2c_master_probe(bus, a, 50) == ESP_OK) {
      addr = a;
      break;
    }
  }
  if (!addr || !addDevice(hz)) {
    addr = 0;
    return false;
  }
  bool ok = initPanel();
  markAllDirty();
  commit();
  return ok;
}

bool present() { return addr != 0; }
uint8_t address() { return addr; }
uint32_t clockHz() { return hz; }

bool setClock(uint32_t newHz) {
  if (!addr) return false;
  xSemaphoreTake(busMutex, portMAX_DELAY);
  i2c_master_bus_rm_device(dev);
  bool ok = addDevice(newHz);
  if (ok) hz = newHz;
  else addDevice(hz);
  xSemaphoreGive(busMutex);
  return ok;
}

void lock() { xSemaphoreTake(fbMutex, portMAX_DELAY); }
void unlock() { xSemaphoreGive(fbMutex); }
uint8_t *fb() { return canvas.getBufferPtr(); }
U8G2 &gfx() { return canvas; }

void markDirty(int page0, int page1, int col0, int col1) {
  if (page0 < dPage0) dPage0 = page0;
  if (page1 > dPage1) dPage1 = page1;
  if (col0 < dCol0) dCol0 = col0;
  if (col1 > dCol1) dCol1 = col1;
}

void markAllDirty() { markDirty(0, PAGES - 1, 0, W - 1); }

void commit() {
  if (!addr) return;
  st.commits++;
  xTaskNotifyGive(task);
}

bool command(const uint8_t *cmds, size_t n) {
  if (!addr) return false;
  xSemaphoreTake(busMutex, portMAX_DELAY);
  bool ok = sendCommands(cmds, n);
  xSemaphoreGive(busMutex);
  return ok;
}

uint64_t bench(int count, uint32_t &errors) {
  errors = 0;
  if (!addr) return 0;
  lock();
  memcpy(benchBuf + 1, canvas.getBufferPtr(), W * PAGES);
  unlock();
  xSemaphoreTake(busMutex, portMAX_DELAY);
  int64_t t0 = esp_timer_get_time();
  for (int i = 0; i < count; i++) {
    if (!pushRegion(0, PAGES - 1, 0, W - 1, benchBuf, W * PAGES)) errors++;
  }
  uint64_t dt = esp_timer_get_time() - t0;
  xSemaphoreGive(busMutex);
  return dt;
}

const Stats &stats() { return st; }
void resetStats() { memset(&st, 0, sizeof st); }

}  // namespace oled
