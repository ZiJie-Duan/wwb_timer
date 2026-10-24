// TM1637 四位数码管（开漏 + 上拉；时序由硬件定时器中断逐边沿执行，等待期间不占 CPU）
// 经电平转换器时上升沿靠上拉电阻、很慢，下降沿是主动拉低、很快，所以两种边沿分开设等待时间。
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace seg {

struct Stats {
  uint32_t requests;  // 请求刷新次数
  uint32_t updates;   // 实际刷新次数
  uint32_t ackFails;  // 未收到 ACK 的字节数
  uint32_t lastUs;
  uint64_t totalUs;
};

void begin();
void setRaw(const uint8_t segs[4]);
void setText(const char *text, size_t len);
// riseUs：CLK 释放后等待；dioRiseUs：DIO 释放后等待（只需赶在 CLK 升起前到位）；fallUs：拉低后等待
void config(uint8_t brightness, bool on, uint8_t riseUs, uint8_t fallUs, uint8_t dioRiseUs);
void getConfig(uint8_t &brightness, bool &on, uint8_t &riseUs, uint8_t &fallUs, uint8_t &dioRiseUs);

// 设备端自测：用指定时序刷新 count 次，返回总耗时 µs。
// 上升沿很慢时，释放后的 DIO 还没升起来也会读成低电平，被误判为 ACK；
// ackSettleUs 在读 ACK 前额外等待，使 ACK 判定可信（“严格 ACK”）
uint64_t bench(int count, uint8_t riseUs, uint8_t fallUs, uint8_t dioRiseUs, uint8_t ackSettleUs,
               uint32_t &ackFails);

const Stats &stats();
void resetStats();

uint8_t encodeChar(char c);

}  // namespace seg
