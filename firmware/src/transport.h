// 两条物理通道（USB-Serial/JTAG、UART1）共用同一套协议与命令分发，只有收发层不同
#pragma once
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include "proto.h"

struct Transport {
  const char *name;
  uint8_t subscribe = 0x01;  // 默认上报输入事件

  // 统计
  uint32_t rxBytes = 0, rxFrames = 0, crcErrors = 0, framingErrors = 0;
  uint32_t txBytes = 0, txFrames = 0, txDropped = 0, txNotConnected = 0;
  uint64_t rxBusyUs = 0;  // 接收任务处理数据（含命令执行）的累计时间

  explicit Transport(const char *n) : name(n) { txLock = xSemaphoreCreateMutex(); }
  virtual ~Transport() = default;

  virtual bool begin() = 0;
  virtual size_t read(uint8_t *buf, size_t max, TickType_t wait) = 0;
  virtual bool connected() { return true; }

  // 组帧发送；任意任务可调用
  void send(uint8_t op, uint8_t flags, uint16_t seq, const uint8_t *payload, size_t len);

  // 接收任务主体：读字节 → COBS 分帧 → CRC 校验 → dispatch()
  void rxLoop();

  void resetStats() {
    rxBytes = rxFrames = crcErrors = framingErrors = txBytes = txFrames = txDropped = txNotConnected = 0;
    rxBusyUs = 0;
  }

 protected:
  // 写完整个缓冲区，超时返回 false
  virtual bool writeAll(const uint8_t *buf, size_t len) = 0;

 private:
  SemaphoreHandle_t txLock;
  uint8_t txFrame[proto::MAX_FRAME];
  uint8_t txEncoded[proto::MAX_ENCODED + 1];
  uint8_t rxBuf[proto::MAX_ENCODED];
  size_t rxLen = 0;
  bool rxOverflow = false;
};

struct UsbTransport : Transport {
  UsbTransport() : Transport("usb") {}
  bool begin() override;
  size_t read(uint8_t *buf, size_t max, TickType_t wait) override;
  bool connected() override;

 protected:
  bool writeAll(const uint8_t *buf, size_t len) override;
};

struct UartTransport : Transport {
  uint32_t baud;
  explicit UartTransport(uint32_t b) : Transport("uart"), baud(b) {}
  bool begin() override;
  size_t read(uint8_t *buf, size_t max, TickType_t wait) override;
  void setBaud(uint32_t b);

 protected:
  bool writeAll(const uint8_t *buf, size_t len) override;
};

extern UsbTransport usbLink;
extern UartTransport uartLink;

// 由 main.cpp 实现：处理一帧已校验的请求
void dispatch(Transport &t, const uint8_t *frame, size_t len);

// 向所有订阅了 mask 的通道广播事件
void broadcastEvent(uint8_t mask, uint8_t op, const uint8_t *payload, size_t len);
