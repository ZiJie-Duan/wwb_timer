// 输入（拨动开关、BOOT 键）与板载灯
// 边沿中断记下抖动开始的时刻，消抖确认后以该时刻上报，时间戳精度 µs 级。
#pragma once
#include <stdint.h>

namespace io {

enum Input : uint8_t { SWITCH = 0, BOOT = 1, COUNT = 2 };

struct State {
  bool active;        // 开关：开启（闭合）；BOOT：按下
  uint32_t count;     // 状态变化次数
  uint64_t changedUs; // 最近一次变化时刻（esp_timer µs）
};

void begin();
State get(Input in);
void setDebounceUs(uint32_t us);
uint32_t debounceUs();
void setLed(bool on);
bool led();

// 每次确认的状态变化都会调用（在 io 任务中）
using Callback = void (*)(Input in, const State &s);
void onChange(Callback cb);

}  // namespace io
