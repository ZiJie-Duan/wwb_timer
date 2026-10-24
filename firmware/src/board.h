// ESP32-C3 Super Mini 引脚分配，均为 GPIO 编号。接线与电平说明见 docs/hardware.md
#pragma once

constexpr int OLED_SDA = 0;
constexpr int OLED_SCL = 1;

constexpr int TM1637_DIO = 3;
constexpr int TM1637_CLK = 4;

constexpr int SWITCH_PIN   = 5;  // 内部上拉，闭合（开启）= 低电平
constexpr int BOOT_BTN_PIN = 9;  // 板载 BOOT 键，按下 = 低电平
constexpr int LED_PIN      = 8;  // 板载蓝灯，低电平亮

constexpr int MATRIX_DIN = 6;
constexpr int MATRIX_CLK = 7;
constexpr int MATRIX_CS  = 10;

constexpr int UART_RX = 20;
constexpr int UART_TX = 21;

constexpr const char *FW_VERSION = "0.1.0";
