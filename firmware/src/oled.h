// SSD1306 128x64 I2C OLED
// 所有绘制先写入帧缓冲并记录脏矩形；独立任务把脏区域推到屏幕。
// 推送期间到达的新绘制会合并进下一次推送（只保留最新内容）。
#pragma once
#include <U8g2lib.h>
#include <stdint.h>

namespace oled {

constexpr int W = 128, H = 64, PAGES = 8;

struct Stats {
  uint32_t commits;     // 请求推送次数
  uint32_t pushes;      // 实际推送次数（commits - pushes = 被合并掉的帧）
  uint32_t bytes;       // 推送的像素数据字节
  uint32_t errors;      // I2C 错误
  uint32_t lastUs;      // 最近一次推送耗时
  uint64_t totalUs;
};

bool begin();
bool present();
uint8_t address();
uint32_t clockHz();
bool setClock(uint32_t hz);

// 调用方需在 lock()/unlock() 之间访问 fb() 与 gfx()
void lock();
void unlock();
uint8_t *fb();
U8G2 &gfx();
void markDirty(int page0, int page1, int col0, int col1);  // 闭区间
void markAllDirty();

void commit();  // 通知推送任务
bool command(const uint8_t *cmds, size_t n);

// 设备端自测：直接推整帧 count 次，返回总耗时 µs，错误数写入 errors
uint64_t bench(int count, uint32_t &errors);

const Stats &stats();
void resetStats();

}  // namespace oled
