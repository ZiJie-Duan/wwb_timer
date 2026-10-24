// wwb 串口协议：帧格式、操作码与编解码。完整说明见 docs/protocol.md
//
// 线上：COBS(帧) + 0x00
// 帧：  op u8 | flags u8 | seq u16 | payload ... | crc16 u16
//       多字节一律小端；crc16 = CRC-16/CCITT-FALSE，覆盖 op..payload
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace proto {

constexpr uint8_t VERSION = 1;
constexpr size_t HEADER = 4;
constexpr size_t CRC_LEN = 2;
constexpr size_t MAX_PAYLOAD = 1100;  // 足够放一整帧 OLED（1024B）
constexpr size_t MAX_FRAME = HEADER + MAX_PAYLOAD + CRC_LEN;
constexpr size_t MAX_ENCODED = MAX_FRAME + MAX_FRAME / 254 + 2;

enum Flag : uint8_t {
  F_NOREPLY = 0x01,  // 请求：成功时不回复（出错仍回复）
  F_RESP    = 0x02,  // 设备回复
  F_EVENT   = 0x04,  // 设备主动上报
  F_ERR     = 0x08,  // 回复为错误，payload = 错误码
  F_FLUSH   = 0x10,  // OLED 操作：执行后立即推送到屏幕
};

enum Op : uint8_t {
  // 系统
  OP_PING        = 0x01,  // 原样回显 payload
  OP_INFO        = 0x02,  // → JSON
  OP_SINK        = 0x03,  // 丢弃 payload，回复 u32 累计字节（测上行吞吐）
  OP_SOURCE      = 0x04,  // u32 总字节, u16 块大小 → 若干 EVENT 数据帧 + 最终回复（测下行吞吐）
  OP_STATS       = 0x05,  // → JSON
  OP_STATS_RESET = 0x06,
  OP_REBOOT      = 0x07,
  OP_UART_BAUD   = 0x08,  // u32 baud；先按旧波特率回复再切换
  OP_SUBSCRIBE   = 0x09,  // u8 掩码 bit0=输入事件 bit1=脱机程序状态；作用于发出该请求的通道
  OP_BENCH       = 0x0A,  // u8 目标, ... → JSON（设备端自测外设极限）
  OP_TIME        = 0x0B,  // → u64 设备时间 µs
  OP_RELEASE     = 0x0C,  // 控制器释放设备，脱机程序立即恢复显示（否则 1.5s 没有命令才算断开）
  OP_CONNECT     = 0x0D,  // → u8 状态(0=脱机 1=连接中 2=已接管), u32 距离接管还有 ms；见 docs/offline.md
  OP_APP_STATE   = 0x0E,  // → 脱机程序的状态（计时器格式见 docs/protocol.md）；订阅 bit1 后变化时主动上报
  OP_APP_DATA    = 0x0F,  // 控制器存储（断电保留，≤256B）：u8 0 → 读出；u8 1, 数据 → 写入

  // 输入 / 板载灯
  OP_IO_READ     = 0x10,  // → 每个输入 13B：u8 状态 u32 次数 u64 最近变化µs；顺序 开关(1=开启)、BOOT(1=按下)
  OP_IO_CONFIG   = 0x11,  // u32 消抖 µs
  OP_LED         = 0x12,  // u8 0/1
  EV_INPUT       = 0x18,  // 事件：u8 输入(0=开关 1=BOOT) u8 状态 u32 次数 u64 时刻µs

  // OLED（SSD1306 128x64，帧缓冲按页排列：8 页 × 128 列，每字节纵向 8 像素，LSB 在上）
  OP_OLED_FRAME  = 0x20,  // 1024B 整帧
  OP_OLED_BLIT   = 0x21,  // u8 页起 u8 列起 u8 页数 u8 列数, 数据（页数×列数）
  OP_OLED_TEXT   = 0x22,  // i16 x, i16 y, u8 字体, u8 颜色, UTF-8 文本
  OP_OLED_CLEAR  = 0x23,  // [u8 颜色]
  OP_OLED_RECT   = 0x24,  // i16 x,y,w,h, u8 模式(0=填充清除 1=填充 2=边框 3=反色)
  OP_OLED_CMD    = 0x25,  // SSD1306 原始命令字节
  OP_OLED_CONFIG = 0x26,  // u32 I2C 时钟 Hz
  OP_OLED_FLUSH  = 0x2F,

  // 数码管 TM1637
  OP_SEG_RAW     = 0x30,  // 4B 段码（第 2 位 bit7 = 冒号）
  OP_SEG_TEXT    = 0x31,  // 文本，':' 点亮冒号，右对齐
  OP_SEG_CONFIG  = 0x32,  // u8 亮度0-7, u8 开/关, u8 CLK上升等待µs, u8 下降等待µs, [u8 DIO上升等待µs]

  // 点阵 MAX7219
  OP_MX_FRAME    = 0x40,  // 8B，逻辑行 0=上，bit7=左；设备按旋转设置输出
  OP_MX_CONFIG   = 0x41,  // u8 亮度0-15, u8 旋转0-3(×90°顺时针), u8 标志 bit0=测试 bit1=关断, u32 SPI Hz
  OP_MX_RAW      = 0x42,  // (寄存器, 值) 对
};

enum Err : uint8_t {
  E_UNKNOWN_OP = 1,
  E_BAD_LEN    = 2,
  E_BAD_ARG    = 3,
  E_HW         = 4,
  E_NOT_READY  = 5,  // 控制器连接还没确认，不能操作外设
};

enum BenchTarget : uint8_t {
  BENCH_OLED = 1,  // u16 帧数, u32 I2C Hz → 整帧推送耗时
  BENCH_SEG  = 2,  // u16 次数, u8 CLK上升µs, u8 下降µs, [u8 DIO上升µs, u8 读ACK前等待µs] → 耗时与 ACK 失败数
  BENCH_MX   = 3,  // u16 次数, u32 SPI Hz → 刷新耗时
};

uint16_t crc16(const uint8_t *data, size_t len);

// out 至少 len + len/254 + 1 字节；返回编码长度（不含结尾 0x00）
size_t cobsEncode(const uint8_t *in, size_t len, uint8_t *out);

// 原地解码；返回解码长度，格式错误返回 0
size_t cobsDecode(uint8_t *buf, size_t len);

inline uint16_t rd16(const uint8_t *p) { return p[0] | (p[1] << 8); }
inline uint32_t rd32(const uint8_t *p) { return p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24); }
inline void wr16(uint8_t *p, uint16_t v) { p[0] = v; p[1] = v >> 8; }
inline void wr32(uint8_t *p, uint32_t v) { for (int i = 0; i < 4; i++) p[i] = v >> (8 * i); }
inline void wr64(uint8_t *p, uint64_t v) { for (int i = 0; i < 8; i++) p[i] = v >> (8 * i); }

}  // namespace proto
