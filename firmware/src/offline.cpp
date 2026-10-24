#include "offline.h"

#include <Preferences.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>

#include "wwb/wwb.h"

namespace offline {

namespace {

class FirmwareHost : public wwb::Host {
 public:
  int exec(uint8_t op, uint8_t flags, const uint8_t *p, size_t n, uint8_t *reply, size_t cap) override {
    return deviceExec(op, flags, p, n, reply, cap);
  }
  size_t load(void *buf, size_t cap) override {
    Preferences prefs;
    if (!prefs.begin("wwb", true)) return 0;  // 第一次开机还没有这个命名空间
    size_t n = prefs.getBytesLength("app") ? prefs.getBytes("app", buf, cap) : 0;
    prefs.end();
    return n;
  }
  void save(const void *buf, size_t n) override {
    Preferences prefs;
    prefs.begin("wwb", false);
    prefs.putBytes("app", buf, n);
    prefs.end();
  }
};

struct Event {
  uint8_t in;
  bool active;
  uint64_t t;
};

FirmwareHost host;
wwb::Runtime *runtime;
QueueHandle_t events;

void task(void *) {
  TickType_t last = xTaskGetTickCount();
  for (;;) {
    Event e;
    execLock();
    while (xQueueReceive(events, &e, 0)) runtime->input((wwb::Input)e.in, e.active, e.t);
    runtime->tick(esp_timer_get_time());
    execUnlock();
    vTaskDelayUntil(&last, pdMS_TO_TICKS(16));  // 约 60 帧/秒，与网页模拟器相同
  }
}

}  // namespace

void begin() {
  events = xQueueCreate(16, sizeof(Event));
  runtime = new wwb::Runtime(host);
  execLock();
  runtime->begin(io::get(io::SWITCH).active, io::get(io::BOOT).active, esp_timer_get_time());
  execUnlock();
  xTaskCreate(task, "offline", 8192, nullptr, 4, nullptr);
}

void input(io::Input in, const io::State &s) {
  Event e{(uint8_t)in, s.active, s.changedUs};
  xQueueSend(events, &e, 0);
}

void hostFrame() {
  if (runtime) runtime->hostFrame(esp_timer_get_time());
}

void release() {
  if (runtime) runtime->release(esp_timer_get_time());
}

bool controlled() { return runtime && runtime->controlled(); }

bool accepts(uint8_t op) { return !runtime || runtime->accepts(op); }

size_t status(uint8_t *out) {
  if (!runtime) return out[0] = wwb::STATE_CONTROLLED, proto::wr32(out + 1, 0), 5;
  return runtime->status(esp_timer_get_time(), out);
}

}  // namespace offline
