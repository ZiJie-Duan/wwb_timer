// 脱机程序（native/ 里的 C++ 程序）在芯片上的运行环境：没有控制器时由它驱动外设
#pragma once
#include <stddef.h>
#include <stdint.h>

#include "io.h"

namespace offline {

void begin();                                  // 外设初始化之后调用
void input(io::Input in, const io::State &s);  // 输入变化（io 任务中调用）
// 以下须持有命令锁（execLock）
void hostFrame();  // 控制器发来一条命令
void release();    // 控制器发来 RELEASE
bool controlled();

}  // namespace offline

// 由 main.cpp 实现：在设备内部执行一条协议命令（程序用的那部分命令），返回回复长度或 -错误码
int deviceExec(uint8_t op, uint8_t flags, const uint8_t *p, size_t n, uint8_t *reply, size_t cap);
// 命令锁（可重入）：串行化控制器命令与脱机程序
void execLock();
void execUnlock();
