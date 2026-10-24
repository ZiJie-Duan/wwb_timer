#include "transport.h"

#include <driver/uart.h>
#include <driver/usb_serial_jtag.h>
#include <esp_timer.h>
#include <string.h>

#include "board.h"

using namespace proto;

UsbTransport usbLink;
UartTransport uartLink(921600);

void Transport::send(uint8_t op, uint8_t flags, uint16_t seq, const uint8_t *payload, size_t len) {
  if (len > MAX_PAYLOAD) len = MAX_PAYLOAD;
  xSemaphoreTake(txLock, portMAX_DELAY);
  txFrame[0] = op;
  txFrame[1] = flags;
  wr16(txFrame + 2, seq);
  if (len) memcpy(txFrame + HEADER, payload, len);
  wr16(txFrame + HEADER + len, crc16(txFrame, HEADER + len));
  size_t n = cobsEncode(txFrame, HEADER + len + CRC_LEN, txEncoded);
  txEncoded[n++] = 0;
  if (!connected()) {
    txNotConnected++;  // 只记录，照常尝试写：连接检测在高负载下可能误报
  }
  if (writeAll(txEncoded, n)) {
    txBytes += n;
    txFrames++;
  } else {
    txDropped++;
  }
  xSemaphoreGive(txLock);
}

void Transport::rxLoop() {
  static uint8_t chunks[2][2048];  // 每条通道一个，放静态区避免占任务栈
  uint8_t *chunk = chunks[this == &usbLink ? 0 : 1];
  const size_t chunkSize = sizeof chunks[0];
  for (;;) {
    size_t n = read(chunk, chunkSize, pdMS_TO_TICKS(100));
    if (!n) continue;
    int64_t busyStart = esp_timer_get_time();
    rxBytes += n;
    for (size_t i = 0; i < n; i++) {
      uint8_t b = chunk[i];
      if (b != 0) {
        if (rxLen < sizeof rxBuf) rxBuf[rxLen++] = b;
        else rxOverflow = true;
        continue;
      }
      // 帧结束
      if (rxLen == 0) continue;
      size_t len = rxOverflow ? 0 : cobsDecode(rxBuf, rxLen);
      rxLen = 0;
      rxOverflow = false;
      if (len < HEADER + CRC_LEN) {
        framingErrors++;
        continue;
      }
      if (crc16(rxBuf, len - CRC_LEN) != rd16(rxBuf + len - CRC_LEN)) {
        crcErrors++;
        continue;
      }
      rxFrames++;
      dispatch(*this, rxBuf, len - CRC_LEN);
    }
    rxBusyUs += esp_timer_get_time() - busyStart;
  }
}

// ---------------------------------------------------------------- USB-Serial/JTAG

bool UsbTransport::begin() {
  usb_serial_jtag_driver_config_t cfg = {};
  cfg.tx_buffer_size = 4096;
  cfg.rx_buffer_size = 16384;
  return usb_serial_jtag_driver_install(&cfg) == ESP_OK;
}

size_t UsbTransport::read(uint8_t *buf, size_t max, TickType_t wait) {
  int n = usb_serial_jtag_read_bytes(buf, max, wait);
  return n > 0 ? n : 0;
}

bool UsbTransport::connected() { return usb_serial_jtag_is_connected(); }

bool UsbTransport::writeAll(const uint8_t *buf, size_t len) {
  while (len) {
    int n = usb_serial_jtag_write_bytes(buf, len, pdMS_TO_TICKS(50));
    if (n <= 0) return false;
    buf += n;
    len -= n;
  }
  return true;
}

// ---------------------------------------------------------------- UART1（GPIO20 RX / GPIO21 TX）

bool UartTransport::begin() {
  uart_config_t cfg = {};
  cfg.baud_rate = baud;
  cfg.data_bits = UART_DATA_8_BITS;
  cfg.parity = UART_PARITY_DISABLE;
  cfg.stop_bits = UART_STOP_BITS_1;
  cfg.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  cfg.source_clk = UART_SCLK_DEFAULT;
  if (uart_driver_install(UART_NUM_1, 8192, 4096, 0, nullptr, 0) != ESP_OK) return false;
  if (uart_param_config(UART_NUM_1, &cfg) != ESP_OK) return false;
  return uart_set_pin(UART_NUM_1, UART_TX, UART_RX, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE) == ESP_OK;
}

size_t UartTransport::read(uint8_t *buf, size_t max, TickType_t wait) {
  // 先等第一个字节，再把已到达的一次性取走，降低单字节唤醒开销
  int n = uart_read_bytes(UART_NUM_1, buf, 1, wait);
  if (n <= 0) return 0;
  size_t avail = 0;
  uart_get_buffered_data_len(UART_NUM_1, &avail);
  if (avail > max - 1) avail = max - 1;
  if (avail) n += uart_read_bytes(UART_NUM_1, buf + 1, avail, 0);
  return n;
}

void UartTransport::setBaud(uint32_t b) {
  uart_wait_tx_done(UART_NUM_1, pdMS_TO_TICKS(100));
  baud = b;
  uart_set_baudrate(UART_NUM_1, b);
}

bool UartTransport::writeAll(const uint8_t *buf, size_t len) {
  return uart_write_bytes(UART_NUM_1, buf, len) == (int)len;
}
