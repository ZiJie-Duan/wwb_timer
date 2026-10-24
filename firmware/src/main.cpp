// wwb_timer 设备固件：把开关、OLED、数码管、点阵封装成一套串口 API
// USB-Serial/JTAG 与 UART1 两条通道共用 dispatch()，协议见 docs/protocol.md
// 没有控制器时由脱机程序（native/，见 offline.cpp）驱动外设；控制器一发命令就接管

#include <Arduino.h>
#include <esp_chip_info.h>
#include <esp_flash.h>
#include <esp_log.h>
#include <esp_mac.h>
#include <esp_system.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

#include "board.h"
#include "io.h"
#include "matrix.h"
#include "offline.h"
#include "oled.h"
#include "proto.h"
#include "seg.h"
#include "transport.h"

using namespace proto;

static SemaphoreHandle_t execMutex;  // 可重入：控制器命令里会再执行脱机程序让出设备时的复位命令
static uint8_t reply[MAX_PAYLOAD];
static uint32_t opsExecuted = 0, opsFailed = 0, sinkBytes = 0;
static uint64_t execUs[4];  // 命令执行耗时：OLED / 数码管 / 点阵 / 其他

static const uint8_t *const FONTS[] = {
  u8g2_font_6x10_tf,
  u8g2_font_9x15_tf,
  u8g2_font_logisoso16_tr,
  u8g2_font_logisoso24_tn,
  u8g2_font_logisoso32_tn,
  u8g2_font_wqy12_t_gb2312b,
};
static const char *const FONT_NAMES[] = {"6x10", "9x15", "logisoso16", "logisoso24n", "logisoso32n", "wqy12"};
constexpr int FONT_COUNT = sizeof FONTS / sizeof FONTS[0];

// ---------------------------------------------------------------- JSON 输出

struct Json {
  char *buf;
  size_t cap, len = 0;
  Json(char *b, size_t c) : buf(b), cap(c) {}
  void add(const char *fmt, ...) __attribute__((format(printf, 2, 3))) {
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf + len, cap - len, fmt, ap);
    va_end(ap);
    if (n > 0) len = len + n < cap ? len + n : cap - 1;
  }
};

static size_t infoJson(char *out, size_t cap) {
  esp_chip_info_t chip;
  esp_chip_info(&chip);
  uint8_t mac[6];
  esp_read_mac(mac, ESP_MAC_WIFI_STA);
  uint32_t flash = 0;
  esp_flash_get_size(nullptr, &flash);
  uint8_t sb, sr, sf, sd, mi, mr;
  bool son, mt, ms;
  uint32_t mhz;
  seg::getConfig(sb, son, sr, sf, sd);
  mx::getConfig(mi, mr, mt, ms, mhz);

  Json j(out, cap);
  j.add("{\"name\":\"wwb_timer\",\"fw\":\"%s\",\"proto\":%d,\"chip\":\"ESP32-C3\",\"rev\":%d,", FW_VERSION, VERSION,
        chip.revision);
  j.add("\"mac\":\"%02x:%02x:%02x:%02x:%02x:%02x\",\"cpu_mhz\":%d,\"flash\":%lu,\"max_payload\":%u,", mac[0], mac[1],
        mac[2], mac[3], mac[4], mac[5], getCpuFrequencyMhz(), (unsigned long)flash, (unsigned)MAX_PAYLOAD);
  j.add("\"oled\":{\"present\":%s,\"addr\":%d,\"w\":%d,\"h\":%d,\"i2c_hz\":%lu},", oled::present() ? "true" : "false",
        oled::address(), oled::W, oled::H, (unsigned long)oled::clockHz());
  j.add("\"seg\":{\"brightness\":%d,\"on\":%s,\"rise_us\":%d,\"fall_us\":%d,\"dio_rise_us\":%d},", sb,
        son ? "true" : "false", sr, sf, sd);
  j.add("\"mx\":{\"intensity\":%d,\"rotation\":%d,\"test\":%s,\"shutdown\":%s,\"spi_hz\":%lu},", mi, mr,
        mt ? "true" : "false", ms ? "true" : "false", (unsigned long)mhz);
  j.add("\"io\":{\"debounce_us\":%lu,\"led\":%s},", (unsigned long)io::debounceUs(), io::led() ? "true" : "false");
  j.add("\"uart\":{\"rx\":%d,\"tx\":%d,\"baud\":%lu},", UART_RX, UART_TX, (unsigned long)uartLink.baud);
  j.add("\"fonts\":[");
  for (int i = 0; i < FONT_COUNT; i++) j.add("%s\"%s\"", i ? "," : "", FONT_NAMES[i]);
  j.add("]}");
  return j.len;
}

static void linkJson(Json &j, Transport &t) {
  j.add("\"%s\":{\"rx_bytes\":%lu,\"rx_frames\":%lu,\"crc_errors\":%lu,\"framing_errors\":%lu,"
        "\"tx_bytes\":%lu,\"tx_frames\":%lu,\"tx_dropped\":%lu,\"tx_not_connected\":%lu,\"subscribe\":%d,"
        "\"rx_busy_us\":%llu}",
        t.name, (unsigned long)t.rxBytes, (unsigned long)t.rxFrames, (unsigned long)t.crcErrors,
        (unsigned long)t.framingErrors, (unsigned long)t.txBytes, (unsigned long)t.txFrames,
        (unsigned long)t.txDropped, (unsigned long)t.txNotConnected, t.subscribe, (unsigned long long)t.rxBusyUs);
}

static size_t statsJson(char *out, size_t cap) {
  const auto &o = oled::stats();
  const auto &s = seg::stats();
  const auto &m = mx::stats();
  Json j(out, cap);
  j.add("{\"uptime_us\":%llu,\"heap_free\":%lu,\"heap_min\":%lu,\"ops\":%lu,\"op_errors\":%lu,\"sink_bytes\":%lu,",
        (unsigned long long)esp_timer_get_time(), (unsigned long)esp_get_free_heap_size(),
        (unsigned long)esp_get_minimum_free_heap_size(), (unsigned long)opsExecuted, (unsigned long)opsFailed,
        (unsigned long)sinkBytes);
  linkJson(j, usbLink);
  j.add(",");
  linkJson(j, uartLink);
  j.add(",\"oled\":{\"commits\":%lu,\"pushes\":%lu,\"bytes\":%lu,\"errors\":%lu,\"last_us\":%lu,\"total_us\":%llu},",
        (unsigned long)o.commits, (unsigned long)o.pushes, (unsigned long)o.bytes, (unsigned long)o.errors,
        (unsigned long)o.lastUs, (unsigned long long)o.totalUs);
  j.add("\"seg\":{\"requests\":%lu,\"updates\":%lu,\"ack_fails\":%lu,\"last_us\":%lu,\"total_us\":%llu},",
        (unsigned long)s.requests, (unsigned long)s.updates, (unsigned long)s.ackFails, (unsigned long)s.lastUs,
        (unsigned long long)s.totalUs);
  j.add("\"mx\":{\"frames\":%lu,\"last_us\":%lu,\"total_us\":%llu},", (unsigned long)m.frames,
        (unsigned long)m.lastUs, (unsigned long long)m.totalUs);
  j.add("\"exec_us\":{\"oled\":%llu,\"seg\":%llu,\"mx\":%llu,\"other\":%llu}}", (unsigned long long)execUs[0],
        (unsigned long long)execUs[1], (unsigned long long)execUs[2], (unsigned long long)execUs[3]);
  return j.len;
}

// ---------------------------------------------------------------- OLED 绘制辅助

static int clampi(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

// 像素矩形 → 脏页/列；需持有 oled::lock
static void dirtyPixels(int x, int y, int w, int h) {
  if (w <= 0 || h <= 0) return;
  int x0 = clampi(x, 0, oled::W - 1), x1 = clampi(x + w - 1, 0, oled::W - 1);
  int y0 = clampi(y, 0, oled::H - 1), y1 = clampi(y + h - 1, 0, oled::H - 1);
  if (x + w - 1 < 0 || x >= oled::W || y + h - 1 < 0 || y >= oled::H) return;
  oled::markDirty(y0 / 8, y1 / 8, x0, x1);
}

// ---------------------------------------------------------------- 输入事件

static void onInput(io::Input in, const io::State &s) {
  uint8_t p[14];
  p[0] = in;
  p[1] = s.active;
  wr32(p + 2, s.count);
  wr64(p + 6, s.changedUs);
  broadcastEvent(0x01, EV_INPUT, p, sizeof p);
  offline::input(in, s);
}

void broadcastEvent(uint8_t mask, uint8_t op, const uint8_t *payload, size_t len) {
  static uint16_t eventSeq = 0;
  uint16_t seq = ++eventSeq;
  for (Transport *t : {(Transport *)&usbLink, (Transport *)&uartLink}) {
    if (t->subscribe & mask) t->send(op, F_EVENT, seq, payload, len);
  }
}

// ---------------------------------------------------------------- 命令分发

// 返回回复长度；出错时返回 -错误码
static int execute(Transport &t, uint8_t op, uint8_t flags, uint16_t seq, const uint8_t *p, size_t n) {
  switch (op) {
    case OP_PING:
      memcpy(reply, p, n);
      return n;

    case OP_INFO:
      return infoJson((char *)reply, sizeof reply);

    case OP_SINK:
      sinkBytes += n;
      wr32(reply, sinkBytes);
      return 4;

    case OP_SOURCE: {
      if (n < 6) return -E_BAD_LEN;
      uint32_t total = rd32(p);
      size_t chunk = rd16(p + 4);
      if (chunk == 0 || chunk > MAX_PAYLOAD) return -E_BAD_ARG;
      for (size_t i = 0; i < chunk; i++) reply[i] = i;
      int64_t t0 = esp_timer_get_time();
      uint32_t sent = 0;
      while (sent < total) {
        size_t k = total - sent < chunk ? total - sent : chunk;
        t.send(OP_SOURCE, F_EVENT, seq, reply, k);
        sent += k;
      }
      wr32(reply, sent);
      wr32(reply + 4, esp_timer_get_time() - t0);
      return 8;
    }

    case OP_STATS:
      return statsJson((char *)reply, sizeof reply);

    case OP_STATS_RESET:
      usbLink.resetStats();
      uartLink.resetStats();
      oled::resetStats();
      seg::resetStats();
      mx::resetStats();
      opsExecuted = opsFailed = sinkBytes = 0;
      memset(execUs, 0, sizeof execUs);
      return 0;

    case OP_REBOOT:
      t.send(op, F_RESP, seq, nullptr, 0);
      vTaskDelay(pdMS_TO_TICKS(50));
      esp_restart();
      return 0;

    case OP_UART_BAUD: {
      if (n < 4) return -E_BAD_LEN;
      uint32_t baud = rd32(p);
      if (baud < 1200 || baud > 5000000) return -E_BAD_ARG;
      t.send(op, F_RESP, seq, nullptr, 0);  // 先用旧波特率回复
      uartLink.setBaud(baud);
      return INT32_MIN;  // 已回复
    }

    case OP_SUBSCRIBE:
      if (n < 1) return -E_BAD_LEN;
      t.subscribe = p[0];
      return 0;

    case OP_TIME:
      wr64(reply, esp_timer_get_time());
      return 8;

    case OP_RELEASE:  // 已在 dispatch() 里处理
      return 0;

    case OP_CONNECT:
      return offline::status(reply);

    case OP_BENCH: {
      if (n < 3) return -E_BAD_LEN;
      int count = rd16(p + 1);
      if (count < 1) return -E_BAD_ARG;
      Json j((char *)reply, sizeof reply);
      if (p[0] == BENCH_OLED) {
        uint32_t hz = n >= 7 ? rd32(p + 3) : 0, prev = oled::clockHz();
        if (hz && hz != prev && !oled::setClock(hz)) return -E_BAD_ARG;
        uint32_t errors;
        uint64_t us = oled::bench(count, errors);
        if (hz && hz != prev) oled::setClock(prev);
        j.add("{\"target\":\"oled\",\"count\":%d,\"i2c_hz\":%lu,\"us\":%llu,\"errors\":%lu}", count,
              (unsigned long)(hz ? hz : prev), (unsigned long long)us, (unsigned long)errors);
      } else if (p[0] == BENCH_SEG) {
        if (n < 5) return -E_BAD_LEN;
        uint8_t dioRise = n >= 6 ? p[5] : p[3];
        uint8_t settle = n >= 7 ? p[6] : 0;
        uint32_t fails;
        uint64_t us = seg::bench(count, p[3], p[4], dioRise, settle, fails);
        j.add("{\"target\":\"seg\",\"count\":%d,\"rise_us\":%d,\"fall_us\":%d,\"dio_rise_us\":%d,"
              "\"ack_settle_us\":%d,\"us\":%llu,\"ack_fails\":%lu}",
              count, p[3], p[4], dioRise, settle, (unsigned long long)us, (unsigned long)fails);
      } else if (p[0] == BENCH_MX) {
        if (n < 7) return -E_BAD_LEN;
        uint32_t hz = rd32(p + 3);
        uint64_t us = mx::bench(count, hz);
        j.add("{\"target\":\"mx\",\"count\":%d,\"spi_hz\":%lu,\"us\":%llu}", count, (unsigned long)hz,
              (unsigned long long)us);
      } else {
        return -E_BAD_ARG;
      }
      return j.len;
    }

    // ---- 输入 / 灯
    case OP_IO_READ: {
      for (int i = 0; i < io::COUNT; i++) {
        io::State s = io::get((io::Input)i);
        uint8_t *q = reply + i * 13;
        q[0] = s.active;
        wr32(q + 1, s.count);
        wr64(q + 5, s.changedUs);
      }
      return 13 * io::COUNT;
    }

    case OP_IO_CONFIG:
      if (n < 4) return -E_BAD_LEN;
      io::setDebounceUs(rd32(p));
      return 0;

    case OP_LED:
      if (n < 1) return -E_BAD_LEN;
      io::setLed(p[0]);
      return 0;

    // ---- OLED
    case OP_OLED_FRAME:
      if (n != oled::W * oled::PAGES) return -E_BAD_LEN;
      oled::lock();
      memcpy(oled::fb(), p, n);
      oled::markAllDirty();
      oled::unlock();
      break;

    case OP_OLED_BLIT: {
      if (n < 4) return -E_BAD_LEN;
      int p0 = p[0], c0 = p[1], pages = p[2], cols = p[3];
      if (pages < 1 || cols < 1 || p0 + pages > oled::PAGES || c0 + cols > oled::W) return -E_BAD_ARG;
      if (n != 4 + (size_t)pages * cols) return -E_BAD_LEN;
      oled::lock();
      for (int i = 0; i < pages; i++) memcpy(oled::fb() + (p0 + i) * oled::W + c0, p + 4 + i * cols, cols);
      oled::markDirty(p0, p0 + pages - 1, c0, c0 + cols - 1);
      oled::unlock();
      break;
    }

    case OP_OLED_TEXT: {
      if (n < 6) return -E_BAD_LEN;
      int x = (int16_t)rd16(p), y = (int16_t)rd16(p + 2), font = p[4], color = p[5];
      if (font >= FONT_COUNT) return -E_BAD_ARG;
      char text[256];
      size_t len = n - 6 < sizeof text - 1 ? n - 6 : sizeof text - 1;
      memcpy(text, p + 6, len);
      text[len] = 0;
      oled::lock();
      U8G2 &g = oled::gfx();
      g.setFont(FONTS[font]);
      g.setFontMode(1);
      g.setDrawColor(color);
      int w = g.drawUTF8(x, y, text);
      dirtyPixels(x, y - g.getAscent(), w, g.getAscent() - g.getDescent() + 1);
      oled::unlock();
      break;
    }

    case OP_OLED_CLEAR:
      oled::lock();
      memset(oled::fb(), n >= 1 && p[0] ? 0xFF : 0x00, oled::W * oled::PAGES);
      oled::markAllDirty();
      oled::unlock();
      break;

    case OP_OLED_RECT: {
      if (n < 9) return -E_BAD_LEN;
      int x = (int16_t)rd16(p), y = (int16_t)rd16(p + 2), w = (int16_t)rd16(p + 4), h = (int16_t)rd16(p + 6);
      int mode = p[8];
      if (w <= 0 || h <= 0 || mode > 3) return -E_BAD_ARG;
      oled::lock();
      U8G2 &g = oled::gfx();
      g.setDrawColor(mode == 0 ? 0 : mode == 3 ? 2 : 1);
      if (mode == 2) g.drawFrame(x, y, w, h);
      else g.drawBox(x, y, w, h);
      dirtyPixels(x, y, w, h);
      oled::unlock();
      break;
    }

    case OP_OLED_CMD:
      if (n < 1) return -E_BAD_LEN;
      if (!oled::command(p, n)) return -E_HW;
      return 0;

    case OP_OLED_CONFIG:
      if (n < 4) return -E_BAD_LEN;
      if (!oled::setClock(rd32(p))) return -E_HW;
      return 0;

    case OP_OLED_FLUSH:
      oled::commit();
      return 0;

    // ---- 数码管
    case OP_SEG_RAW:
      if (n != 4) return -E_BAD_LEN;
      seg::setRaw(p);
      return 0;

    case OP_SEG_TEXT:
      seg::setText((const char *)p, n);
      return 0;

    case OP_SEG_CONFIG:
      if (n < 4) return -E_BAD_LEN;
      seg::config(p[0], p[1], p[2], p[3], n >= 5 ? p[4] : p[2]);
      return 0;

    // ---- 点阵
    case OP_MX_FRAME:
      if (n != 8) return -E_BAD_LEN;
      mx::setFrame(p);
      return 0;

    case OP_MX_CONFIG:
      if (n < 3) return -E_BAD_LEN;
      mx::config(p[0], p[1], p[2] & 1, p[2] & 2, n >= 7 ? rd32(p + 3) : 0);
      return 0;

    case OP_MX_RAW:
      if (n < 2 || n % 2) return -E_BAD_LEN;
      mx::raw(p, n);
      return 0;

    default:
      return -E_UNKNOWN_OP;
  }

  // 落到这里的都是 OLED 绘制类命令
  if (flags & F_FLUSH) oled::commit();
  return 0;
}

void dispatch(Transport &t, const uint8_t *frame, size_t len) {
  uint8_t op = frame[0], flags = frame[1];
  uint16_t seq = rd16(frame + 2);
  if (flags & (F_RESP | F_EVENT)) return;  // 忽略回环回来的设备帧

  execLock();
  // 控制器的每条命令都算一次“在线”；连接确认（3s 稳定）之前不能碰外设
  if (op == OP_RELEASE) offline::release();
  else offline::hostFrame();
  int64_t t0 = esp_timer_get_time();
  int r = offline::accepts(op) ? execute(t, op, flags, seq, frame + HEADER, len - HEADER) : -E_NOT_READY;
  int group = (op & 0xF0) == 0x20 ? 0 : (op & 0xF0) == 0x30 ? 1 : (op & 0xF0) == 0x40 ? 2 : 3;
  execUs[group] += esp_timer_get_time() - t0;
  opsExecuted++;
  if (r == INT32_MIN) {
    // 已在 execute 内回复
  } else if (r < 0) {
    opsFailed++;
    uint8_t code = -r;
    t.send(op, F_RESP | F_ERR, seq, &code, 1);
  } else if (!(flags & F_NOREPLY)) {
    t.send(op, F_RESP, seq, reply, r);
  }
  execUnlock();
}

void execLock() { xSemaphoreTakeRecursive(execMutex, portMAX_DELAY); }
void execUnlock() { xSemaphoreGiveRecursive(execMutex); }

int deviceExec(uint8_t op, uint8_t flags, const uint8_t *p, size_t n, uint8_t *out, size_t cap) {
  switch (op) {  // 这些命令针对通道或耗时很长，程序不能用
    case OP_SOURCE: case OP_REBOOT: case OP_UART_BAUD: case OP_SUBSCRIBE: case OP_BENCH: case OP_RELEASE:
    case OP_CONNECT:
      return -E_BAD_ARG;
  }
  execLock();
  int r = execute(usbLink, op, flags, 0, p, n);
  if (r > 0) memcpy(out, reply, (size_t)r < cap ? r : cap);
  execUnlock();
  return r == INT32_MIN ? 0 : r;
}

// ---------------------------------------------------------------- 启动

static void rxTask(void *arg) { static_cast<Transport *>(arg)->rxLoop(); }

static void housekeepingTask(void *) {
  for (;;) {
    vTaskDelay(pdMS_TO_TICKS(1000));
    mx::refreshConfig();
  }
}

void setup() {
  esp_log_level_set("*", ESP_LOG_NONE);  // 日志会混进 USB 数据流，全部关闭
  execMutex = xSemaphoreCreateRecursiveMutex();
  crc16(nullptr, 0);  // 预生成查表

  io::begin();
  io::onChange(onInput);
  seg::begin();
  mx::begin();
  oled::begin();
  offline::begin();

  bool usbOk = usbLink.begin();
  bool uartOk = uartLink.begin();
  if (usbOk) xTaskCreate(rxTask, "rx_usb", 4096, &usbLink, 5, nullptr);
  if (uartOk) xTaskCreate(rxTask, "rx_uart", 4096, &uartLink, 5, nullptr);
  xTaskCreate(housekeepingTask, "house", 2048, nullptr, 2, nullptr);

  io::setLed(usbOk && uartOk);  // 蓝灯常亮 = 两条通道都就绪
}

void loop() { vTaskDelete(nullptr); }
