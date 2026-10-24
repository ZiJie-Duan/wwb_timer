// 脱机程序在网页模拟器里的运行环境（与固件的 firmware/src/offline.cpp 对应）。
// 命令交给 web/js/offline.js 里的模拟器执行，断电保留的数据存在 localStorage
#include <emscripten.h>

#include "wwb/wwb.h"

EM_JS(int, js_exec, (int op, int flags, const uint8_t *p, int n, uint8_t *reply, int cap), {
  var r = Module.wwbExec(op, flags, HEAPU8.slice(p, p + n));
  if (typeof r === "number") return r;
  var k = Math.min(r.length, cap);
  HEAPU8.set(r.subarray(0, k), reply);
  return k;
});

EM_JS(int, js_load, (uint8_t *buf, int cap), {
  var d = Module.wwbLoad();
  if (!d) return 0;
  var k = Math.min(d.length, cap);
  HEAPU8.set(d.subarray(0, k), buf);
  return k;
});

EM_JS(void, js_save, (const uint8_t *buf, int n), { Module.wwbSave(HEAPU8.slice(buf, buf + n)); });

namespace {

class WebHost : public wwb::Host {
 public:
  int exec(uint8_t op, uint8_t flags, const uint8_t *p, size_t n, uint8_t *reply, size_t cap) override {
    return js_exec(op, flags, p, n, reply, cap);
  }
  size_t load(void *buf, size_t cap) override { return js_load((uint8_t *)buf, cap); }
  void save(const void *buf, size_t n) override { js_save((const uint8_t *)buf, n); }
};

WebHost host;
wwb::Runtime runtime(host);

}  // namespace

// 时间一律是模拟器的 µs（double 传入）
extern "C" {
EMSCRIPTEN_KEEPALIVE void wwb_begin(int sw, int boot, double now) { runtime.begin(sw, boot, (uint64_t)now); }
EMSCRIPTEN_KEEPALIVE void wwb_input(int in, int active, double t) { runtime.input((wwb::Input)in, active, (uint64_t)t); }
EMSCRIPTEN_KEEPALIVE void wwb_host_frame(double now) { runtime.hostFrame((uint64_t)now); }
EMSCRIPTEN_KEEPALIVE void wwb_release(double now) { runtime.release((uint64_t)now); }
EMSCRIPTEN_KEEPALIVE void wwb_tick(double now) { runtime.tick((uint64_t)now); }
EMSCRIPTEN_KEEPALIVE int wwb_controlled() { return runtime.controlled(); }
EMSCRIPTEN_KEEPALIVE int wwb_accepts(int op) { return runtime.accepts(op); }
// CONNECT 的回复（5 字节）写进 out
EMSCRIPTEN_KEEPALIVE int wwb_status(double now, uint8_t *out) { return runtime.status((uint64_t)now, out); }
EMSCRIPTEN_KEEPALIVE uint8_t *wwb_buffer() {
  static uint8_t buf[16];
  return buf;
}
}
