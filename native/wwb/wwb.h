// wwb 脱机程序框架。
//
// 同一份程序编译两次：编进固件，没有控制器时在芯片上运行；编成 WebAssembly，在网页模拟器里运行。
// 程序通过协议命令驱动外设：芯片上直接交给固件的命令处理函数（不经过串口），网页里交给模拟器，
// 所以两边的画面、时序一致。
//
// 控制器（通过 USB / UART 发协议的上位机程序）的连接过程：
//   脱机 ──收到命令──▶ 连接中（命令须持续 3s、间隔不超过 1s）──▶ 已确认（程序播放连接动画）──▶ 接管
//   连接中断（间隔超时或 RELEASE）回到脱机；接管后 RELEASE 或 1.5s 没有命令 = 断开（程序播放断开动画）
// 接管前控制器只能用不碰外设的命令（PING、INFO、CONNECT…），显示类命令回 NOT_READY。
// 接管期间脱机程序照常收到输入与时间，但画面被屏蔽；交接时外设都恢复开机默认。
#pragma once
#include <stddef.h>
#include <stdint.h>

#include "clib/u8g2.h"
#include "proto.h"

namespace wwb {

// 运行平台（固件 / 网页模拟器）
class Host {
 public:
  virtual ~Host() = default;
  // 按设备的方式执行一条协议命令；返回回复长度，出错返回 -错误码
  virtual int exec(uint8_t op, uint8_t flags, const uint8_t *p, size_t n, uint8_t *reply, size_t cap) = 0;
  // 断电保留的数据（芯片：NVS；网页：localStorage）
  virtual size_t load(void *buf, size_t cap) = 0;
  virtual void save(const void *buf, size_t n) = 0;
  // 程序的状态变了（Device::changed）：平台把 Runtime::report 的内容作为 APP_STATE 事件发给控制器
  virtual void changed() {}
};

enum Input : uint8_t { SWITCH = 0, BOOT = 1 };

// 控制器连接事件
enum Link : uint8_t {
  LINK_CONNECTING,  // 开始收到命令，进入 3s 稳定期
  LINK_CONFIRMED,   // 稳定 3s，连接确认；Runtime::CONFIRM_US 后交给控制器
  LINK_ABORTED,     // 确认前中断
  LINK_RELEASED,    // 接管结束（程序退出或超时），设备回到脱机程序
};

// 协议 CONNECT 的回复状态
enum LinkState : uint8_t { STATE_OFFLINE = 0, STATE_CONNECTING = 1, STATE_CONTROLLED = 2 };

// OLED 画布：u8g2 全缓冲，排列与设备帧缓冲相同（8 页 × 128 列，LSB 在上）
class Canvas {
 public:
  static constexpr int W = 128, H = 64;
  Canvas();
  u8g2_t *u() { return &u8g2_; }
  uint8_t *buffer() { return buf_; }
  void clear();
  // 有序抖动：区域内只保留 level/16 的像素（0 = 全清，16 = 不变），用来做淡入淡出
  void fade(int x, int y, int w, int h, int level);
  void invert(int x, int y, int w, int h);
  void pixel(int x, int y, bool on);

 private:
  u8g2_t u8g2_;
  uint8_t buf_[W * H / 8];
};

// 程序看到的设备。输出都有缓存：内容没变就不发命令
class Device {
 public:
  explicit Device(Host &h) : host_(h) {}
  bool visible() const { return visible_; }  // 控制器接管时为 false，输出被丢弃
  bool input(Input in) const { return inputs_[in]; }

  void oled(Canvas &c);  // 推送画布（只发变化的部分）
  void seg(const uint8_t segs[4]);  // 段码，第 2 位 bit7 = 冒号
  void segConfig(uint8_t brightness, bool on);
  void mx(const uint8_t rows[8]);  // 逻辑方向：行 0 在上，bit7 在左
  void mxIntensity(uint8_t level);

  void load(void *buf, size_t cap, size_t &got) { got = host_.load(buf, cap); }
  void save(const void *buf, size_t n) { host_.save(buf, n); }
  // 程序的状态（App::report）变了，通知订阅了的控制器
  void changed() { host_.changed(); }

 private:
  friend class Runtime;
  int send(uint8_t op, const uint8_t *p, size_t n, uint8_t flags = 0);
  void invalidate();

  Host &host_;
  bool visible_ = true;
  bool inputs_[2] = {false, false};
  uint8_t oled_[Canvas::W * Canvas::H / 8];
  bool oledValid_ = false;
  uint8_t seg_[4];
  bool segValid_ = false;
  uint8_t segBrightness_ = 0;
  bool segOn_ = false, segConfigValid_ = false;
  uint8_t mx_[8];
  bool mxValid_ = false;
  uint8_t mxIntensity_ = 0;
  bool mxIntensityValid_ = false;
};

class App {
 public:
  virtual ~App() = default;
  // 开机时调用一次；d.input() 已是开机时的输入状态
  virtual void setup(Device &d, uint64_t now) = 0;
  // 输入变化（消抖后），t 为变化开始的时刻
  virtual void input(Device &d, Input in, bool active, uint64_t t) {}
  // 控制器连接过程，见 Link
  virtual void link(Device &d, Link ev, uint64_t now) {}
  // 约 60 次/秒；控制器接管时也会调用（d.visible() 为 false）
  virtual void frame(Device &d, uint64_t now) = 0;
  // 上报给控制器的状态（协议 APP_STATE），格式由程序定义；返回长度
  virtual size_t report(uint64_t now, uint8_t *out, size_t cap) { return 0; }
};

// 由程序实现，返回新的实例
App *createApp();

// 把程序、输入、控制器连接串起来。平台负责：开机调 begin，输入变化调 input，每帧调 tick，
// 控制器的每条命令先调 hostFrame（RELEASE 调 release），再用 accepts 判断能否执行。所有调用须串行
class Runtime {
 public:
  static constexpr uint64_t STABLE_US = 3000000;   // 命令持续这么久才确认连接
  static constexpr uint64_t GAP_US = 1000000;      // 连接中命令间隔超过这个就算中断
  static constexpr uint64_t CONFIRM_US = 1200000;  // 确认后播放连接动画的时间，之后交给控制器
  static constexpr uint64_t DETACH_US = 1500000;   // 接管后这么久没有命令就算断开

  explicit Runtime(Host &h) : host_(h), dev_(h) {}
  ~Runtime() { delete app_; }
  void begin(bool sw, bool boot, uint64_t now);
  void input(Input in, bool active, uint64_t t);
  void hostFrame(uint64_t now);
  void release(uint64_t now);
  void tick(uint64_t now);
  bool controlled() const { return state_ == CONTROLLED; }
  bool accepts(uint8_t op) const;  // 控制器的这条命令现在能否执行
  // CONNECT 的回复：u8 LinkState, u32 距离接管还有多少 ms
  size_t status(uint64_t now, uint8_t *out) const;
  // APP_STATE 的回复：程序的 report()
  size_t report(uint64_t now, uint8_t *out, size_t cap) const { return app_ ? app_->report(now, out, cap) : 0; }

 private:
  enum State { OFFLINE, CONNECTING, CONFIRMING, CONTROLLED };
  void resetPeripherals();
  void notify(Link ev, uint64_t now) {
    if (app_) app_->link(dev_, ev, now);
  }

  Host &host_;
  Device dev_;
  App *app_ = nullptr;
  State state_ = OFFLINE;
  uint64_t lastHostUs_ = 0, sinceUs_ = 0;
};

// 七段码
uint8_t segDigit(int d);

// 缓动
float clamp01(float x);
float easeOutCubic(float x);
float easeInOutCubic(float x);
float easeOutBack(float x);

}  // namespace wwb
