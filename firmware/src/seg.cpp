#include "seg.h"

#include <driver/gpio.h>
#include <driver/gptimer.h>
#include <esp_rom_sys.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>
#include <soc/gpio_reg.h>
#include <string.h>

#include "board.h"

namespace seg {

constexpr uint32_t CLK = 1u << TM1637_CLK;
constexpr uint32_t DIO = 1u << TM1637_DIO;

static SemaphoreHandle_t busMutex;
static TaskHandle_t task;
static portMUX_TYPE stateMux = portMUX_INITIALIZER_UNLOCKED;
static Stats st;

// 期望状态（由命令写入，任务读取）
static uint8_t want[4] = {0x40, 0x40, 0x40, 0x40};  // "----"
static uint8_t brightness = 3;
static bool displayOn = true;
// 实测：CLK 上升 ≥44µs 才可靠（经电平转换器 + 模块电容），取 50 留余量；DIO 只需略早于 CLK；见 docs/benchmarks.md
static uint8_t rise = 50, fall = 2, dioRise = 5;
static uint32_t version = 1, configVersion = 1;

// ---------------------------------------------------------------- 边沿程序
// 先把一次传输要做的引脚动作和等待排成步骤，再由硬件定时器中断逐步执行。
// 等慢上升沿的几十 µs 里 CPU 是空闲的（以前是原地空转），其他外设可以同时满速运行。

enum StepOp : uint8_t { S_CLK_H, S_CLK_L, S_DIO_H, S_DIO_L, S_ACK, S_END };
struct Step {
  uint8_t op;
  uint16_t waitUs;  // 动作之后的等待
};
constexpr int MAX_STEPS = 512;
constexpr uint16_t INLINE_WAIT_US = 4;  // 不超过它的等待在中断里直接忙等，比再排一次闹钟便宜

static Step prog[MAX_STEPS];
static int progLen;
static volatile int progPos;
static volatile uint32_t acks;
static gptimer_handle_t timer;
static SemaphoreHandle_t doneSem;

// 构建程序时使用的时序（bench 时临时替换）
static uint8_t tRise, tFall, tDioRise;
static uint8_t tAckSettle = 0;  // 读 ACK 前额外等待：释放的 DIO 若没被拉住，到这时一定已升高
static bool dioHigh = true;     // 程序执行到当前位置时 DIO 的状态

static void emit(uint8_t op, uint16_t waitUs) {
  if (progLen < MAX_STEPS - 1) prog[progLen++] = {op, waitUs};
}
static void wait(uint16_t us) {
  if (us && progLen) prog[progLen - 1].waitUs += us;
}
static void clkSet(bool high) { emit(high ? S_CLK_H : S_CLK_L, high ? tRise : tFall); }
static void dioSet(bool high) {
  if (high == dioHigh) return;
  dioHigh = high;
  emit(high ? S_DIO_H : S_DIO_L, high ? tDioRise : tFall);
}

static void start() {
  dioSet(true);
  clkSet(true);
  dioSet(false);
}

static void stop() {
  clkSet(false);
  dioSet(false);
  clkSet(true);
  dioSet(true);
}

static void writeByte(uint8_t b) {
  for (int i = 0; i < 8; i++, b >>= 1) {
    clkSet(false);
    dioSet(b & 1);
    clkSet(true);
  }
  // 第 9 个时钟：释放 DIO，由 TM1637 拉低表示 ACK
  clkSet(false);
  dioSet(true);
  wait(tAckSettle);
  clkSet(true);
  emit(S_ACK, 0);
  clkSet(false);
}

static void armAlarm(gptimer_handle_t t, uint16_t us) {
  uint64_t now;
  gptimer_get_raw_count(t, &now);
  gptimer_alarm_config_t a = {};
  a.alarm_count = now + us;
  gptimer_set_alarm_action(t, &a);
}

// 定时器中断：连续执行步骤，遇到长等待就排下一次闹钟后返回
static bool onAlarm(gptimer_handle_t t, const gptimer_alarm_event_data_t *, void *) {
  for (;;) {
    const Step s = prog[progPos++];
    switch (s.op) {
      case S_CLK_H: REG_WRITE(GPIO_OUT_W1TS_REG, CLK); break;
      case S_CLK_L: REG_WRITE(GPIO_OUT_W1TC_REG, CLK); break;
      case S_DIO_H: REG_WRITE(GPIO_OUT_W1TS_REG, DIO); break;
      case S_DIO_L: REG_WRITE(GPIO_OUT_W1TC_REG, DIO); break;
      case S_ACK:
        if (REG_READ(GPIO_IN_REG) & DIO) acks = acks + 1;  // 高电平 = 没有 ACK
        break;
      default: {
        BaseType_t woken = pdFALSE;
        xSemaphoreGiveFromISR(doneSem, &woken);
        return woken == pdTRUE;
      }
    }
    if (s.waitUs == 0) continue;
    if (s.waitUs <= INLINE_WAIT_US) {
      esp_rom_delay_us(s.waitUs);
      continue;
    }
    armAlarm(t, s.waitUs);
    return false;
  }
}

// 执行已构建的程序，阻塞到完成；返回未收到 ACK 的字节数
static uint32_t run() {
  emit(S_END, 0);
  progPos = 0;
  acks = 0;
  armAlarm(timer, 2);
  xSemaphoreTake(doneSem, portMAX_DELAY);
  return acks;
}

// 只写第 first..last 位（地址自增模式）；需持有 busMutex
static uint32_t transmit(const uint8_t segs[4], int first, int last, bool withConfig, uint8_t bright, bool on) {
  progLen = 0;
  if (withConfig) {
    start(); writeByte(0x40); stop();  // 写数据，地址自增
  }
  start();
  writeByte(0xC0 | first);
  for (int i = first; i <= last; i++) writeByte(segs[i]);
  stop();
  if (withConfig) {
    start(); writeByte(on ? 0x88 | (bright & 7) : 0x80); stop();
  }
  return run();
}

static void segTask(void *) {
  uint32_t doneVersion = 0, doneConfig = 0;
  int64_t lastConfigUs = 0;
  uint8_t shown[4];
  bool shownValid = false;  // 屏上内容是否确定；出错或补发配置时整屏重写
  for (;;) {
    bool idle = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(1000)) == 0;
    for (;;) {
      uint8_t segs[4], b, r, f, dr;
      bool on;
      uint32_t v, cv;
      taskENTER_CRITICAL(&stateMux);
      memcpy(segs, want, 4);
      b = brightness;
      on = displayOn;
      v = version;
      cv = configVersion;
      r = rise;
      f = fall;
      dr = dioRise;
      taskEXIT_CRITICAL(&stateMux);

      // 空闲满 1 秒时补发配置并整屏重写，模块单独掉电重启后能自动恢复。
      // 连续刷新期间不补发（会多花约 2.5ms，挤掉高帧率下的帧）；那时若模块掉电，ACK 失败会触发重发
      int64_t now = esp_timer_get_time();
      bool withConfig = cv != doneConfig || (idle && now - lastConfigUs > 1000000);
      idle = false;
      if (v == doneVersion && !withConfig) break;

      // 每次 CLK 上升都要等慢速上升沿，字节数决定耗时，所以只写变化的那几位
      int first = 0, last = 3;
      if (shownValid && !withConfig) {
        while (first < 4 && segs[first] == shown[first]) first++;
        while (last >= first && segs[last] == shown[last]) last--;
        if (first > last) {
          doneVersion = v;
          continue;
        }
      }

      xSemaphoreTake(busMutex, portMAX_DELAY);
      tRise = r;
      tFall = f;
      tDioRise = dr;
      int64_t t0 = esp_timer_get_time();
      uint32_t fails = transmit(segs, first, last, withConfig, b, on);
      uint32_t dt = esp_timer_get_time() - t0;
      xSemaphoreGive(busMutex);

      doneVersion = v;
      memcpy(shown, segs, 4);
      shownValid = fails == 0;
      if (withConfig) {
        lastConfigUs = now;
        doneConfig = fails ? 0 : cv;  // 失败则下次重发配置
      }
      st.updates++;
      st.ackFails += fails;
      st.lastUs = dt;
      st.totalUs += dt;
    }
  }
}

void begin() {
  busMutex = xSemaphoreCreateMutex();
  gpio_config_t io = {};
  io.pin_bit_mask = CLK | DIO;
  io.mode = GPIO_MODE_INPUT_OUTPUT_OD;
  io.pull_up_en = GPIO_PULLUP_ENABLE;
  gpio_config(&io);
  REG_WRITE(GPIO_OUT_W1TS_REG, CLK | DIO);
  dioHigh = true;

  doneSem = xSemaphoreCreateBinary();
  gptimer_config_t tc = {};
  tc.clk_src = GPTIMER_CLK_SRC_DEFAULT;
  tc.direction = GPTIMER_COUNT_UP;
  tc.resolution_hz = 1000000;  // 1 tick = 1µs
  gptimer_new_timer(&tc, &timer);
  gptimer_event_callbacks_t cbs = {};
  cbs.on_alarm = onAlarm;
  gptimer_register_event_callbacks(timer, &cbs, nullptr);
  gptimer_enable(timer);
  gptimer_start(timer);

  // 优先级高于接收任务：本任务只构建步骤、等中断执行完，几乎不占 CPU；
  // 若低于接收任务，大量点阵命令涌入时每次刷新之间都要排很久
  xTaskCreate(segTask, "seg", 3072, nullptr, 6, &task);
}

static void bump(bool cfg) {
  taskENTER_CRITICAL(&stateMux);
  version++;
  if (cfg) configVersion++;
  taskEXIT_CRITICAL(&stateMux);
  st.requests++;
  xTaskNotifyGive(task);
}

void setRaw(const uint8_t segs[4]) {
  taskENTER_CRITICAL(&stateMux);
  memcpy(want, segs, 4);
  taskEXIT_CRITICAL(&stateMux);
  bump(false);
}

uint8_t encodeChar(char c) {
  static const uint8_t DIGITS[] = {0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f};
  if (c >= '0' && c <= '9') return DIGITS[c - '0'];
  switch (c) {
    case 'A': case 'a': return 0x77;
    case 'B': case 'b': return 0x7c;
    case 'C': return 0x39;
    case 'c': return 0x58;
    case 'D': case 'd': return 0x5e;
    case 'E': case 'e': return 0x79;
    case 'F': case 'f': return 0x71;
    case 'G': case 'g': return 0x3d;
    case 'H': return 0x76;
    case 'h': return 0x74;
    case 'I': case 'i': return 0x06;
    case 'J': case 'j': return 0x1e;
    case 'L': case 'l': return 0x38;
    case 'N': case 'n': return 0x54;
    case 'O': return 0x3f;
    case 'o': return 0x5c;
    case 'P': case 'p': return 0x73;
    case 'Q': case 'q': return 0x67;
    case 'R': case 'r': return 0x50;
    case 'S': case 's': return 0x6d;
    case 'T': case 't': return 0x78;
    case 'U': return 0x3e;
    case 'u': return 0x1c;
    case 'Y': case 'y': return 0x6e;
    case '-': return 0x40;
    case '_': return 0x08;
    case '=': return 0x48;
    default: return 0;
  }
}

void setText(const char *text, size_t len) {
  uint8_t out[4] = {0, 0, 0, 0}, segs[4] = {0, 0, 0, 0};
  bool colon = false;
  int n = 0;
  for (size_t i = 0; i < len; i++) {
    if (text[i] == ':') colon = true;
    else if (n < 4) out[n++] = encodeChar(text[i]);
  }
  for (int i = 0; i < n; i++) segs[4 - n + i] = out[i];  // 右对齐
  if (colon) segs[1] |= 0x80;
  setRaw(segs);
}

void config(uint8_t b, bool on, uint8_t riseUs, uint8_t fallUs, uint8_t dioRiseUs) {
  taskENTER_CRITICAL(&stateMux);
  brightness = b & 7;
  displayOn = on;
  rise = riseUs;
  fall = fallUs;
  dioRise = dioRiseUs;
  taskEXIT_CRITICAL(&stateMux);
  bump(true);
}

void getConfig(uint8_t &b, bool &on, uint8_t &riseUs, uint8_t &fallUs, uint8_t &dioRiseUs) {
  b = brightness;
  on = displayOn;
  riseUs = rise;
  fallUs = fall;
  dioRiseUs = dioRise;
}

uint64_t bench(int count, uint8_t riseUs, uint8_t fallUs, uint8_t dioRiseUs, uint8_t ackSettleUs,
               uint32_t &ackFails) {
  uint8_t segs[4];
  taskENTER_CRITICAL(&stateMux);
  memcpy(segs, want, 4);
  taskEXIT_CRITICAL(&stateMux);

  xSemaphoreTake(busMutex, portMAX_DELAY);
  tRise = riseUs;
  tFall = fallUs;
  tDioRise = dioRiseUs;
  tAckSettle = ackSettleUs;
  ackFails = 0;
  int64_t t0 = esp_timer_get_time();
  for (int i = 0; i < count; i++) ackFails += transmit(segs, 0, 3, false, 0, true);
  uint64_t dt = esp_timer_get_time() - t0;
  tAckSettle = 0;
  xSemaphoreGive(busMutex);
  bump(true);  // 自测后用正常时序重发一遍，避免屏上留下错误内容
  return dt;
}

const Stats &stats() { return st; }
void resetStats() { memset(&st, 0, sizeof st); }

}  // namespace seg
