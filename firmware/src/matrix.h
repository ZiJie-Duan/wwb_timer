// MAX7219 8x8 点阵（硬件 SPI，CS 手动）
// 上位机按“逻辑方向”发 8 行：行 0 在上，bit7 在左；设备按旋转设置换算成物理寄存器内容。
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace mx {

struct Stats {
  uint32_t frames;
  uint32_t lastUs;
  uint64_t totalUs;
};

void begin();
void setFrame(const uint8_t rows[8]);
void getFrame(uint8_t rows[8]);
void config(uint8_t intensity, uint8_t rotation, bool test, bool shutdown, uint32_t spiHz);
void getConfig(uint8_t &intensity, uint8_t &rotation, bool &test, bool &shutdown, uint32_t &spiHz);
void raw(const uint8_t *pairs, size_t n);  // (寄存器, 值) 对
void refreshConfig();                      // 周期调用：模块掉电重上电后恢复

uint64_t bench(int count, uint32_t spiHz);

const Stats &stats();
void resetStats();

}  // namespace mx
