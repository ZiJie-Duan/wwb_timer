**English** · [简体中文](offline.zh-CN.md)

# Offline program and wwb timer

The device has two states:

- **Offline**: with no controller attached, the offline program in the chip drives the peripherals. The current offline program is the timer wwb timer (`native/timer/`).
- **Controller takeover**: once a host program (Python, `wwb.Device`) connects, commands must **continue for 3 seconds** before the connection is confirmed (so a flaky contact doesn't connect and disconnect repeatedly); after the connect animation plays, the device is handed over to it. When the program exits (sends `RELEASE`) or no command arrives for 1.5 seconds, the controller counts as unplugged; the offline program plays the disconnect animation and resumes its display. **One program is one connection**: when the program ends, the connection ends, even if the serial cable is still plugged in.

The offline program is C++, and **the same source is compiled twice**: into the firmware to run on the chip (native performance, not going through the serial port), and into WebAssembly to run in the web simulator. So what you see in the browser is exactly what the chip does.

## wwb timer

| Action | Effect |
|---|---|
| Switch up | Start timing. Matrix: three arrows shoot upward; once fully off-screen, the existing dots light up one by one in quick succession. OLED: the old screen dissolves, a big ▶ pops out with a ripple spreading outward, the ▶ shrinks and flies into the status bar, “计时中” (“timing”) is typed out character by character, the two seconds digits slide in from below one after the other, and the progress bar unfolds from the middle. The 7-segment display flashes once |
| Switch down | Stop. Matrix: three arrows fall down, the existing dots light up one by one, and a new dot drops into its cell and blinks twice. OLED: a big ‖ drops from above with a ripple contracting inward, the ‖ flies into the status bar, and the seconds slide in from above; as the new dot lands, the count rolls up by one and a “+1” floats out |
| While stopped | The 7-segment display stays lit; the seconds and progress bar on the OLED slowly breathe (on 1.8s → fade out → off 0.4s → fade in) |
| While timing | The 7-segment colon blinks once per second; the "next cell" on the matrix blinks along |
| Power on with the switch **down** | Continue from the previous accumulated time |
| Power on with the switch **up** | Reset (time and dot count); after the reset notice, timing starts immediately |

- **7-segment display**: `hours:minutes`, with the first digit blank below 10 hours; from 100 hours it shows `123h`, and from 1000 hours only the hour count (this display has only the middle colon, no decimal points).
- **OLED**: status (计时中 “timing” / 已停止 “stopped”), the session number, and **seconds** (hours and minutes are on the 7-segment display); when the second changes, the digit that changed rolls upward. At the bottom is a **one-minute progress bar** (a tick every 15 seconds).
- **Matrix**: each completed "on → off" lights one more dot, starting from the top-left and filling row by row, up to 64; normal brightness is 1 (one step above the lowest).
- **Boot**: an old-monitor-style boot animation reveals the title “wwb timer”. Then a hint “插入控制器 / 解锁更多功能” (“plug in a controller / unlock more features”) is shown: a plug slides into a socket on both the OLED and the matrix. It repeats every 10 seconds until the switch is flipped for the first time or a controller connects; after that it is never shown again until the next power-on.
- **Controller connection** (plug animation on both the OLED and the matrix):
  - Connecting (3 seconds): the plug slowly approaches the socket, the socket's light blinks slowly, “正在连接控制器…” (“connecting to controller…”) plus a 3-second progress bar.
  - Confirmed: the plug clicks in, sparks fly, the matrix flashes once, “控制器已连接” (“controller connected”), data flows in along the cable, and after 1.2 seconds it fades out and hands over to the controller.
  - Connection interrupted (dropped within the 3 seconds): the plug backs off, “连接中断” (“connection interrupted”), and it returns to the timer screen.
  - Disconnected: the plug is pulled out and backs away, “控制器已断开” (“controller disconnected”), the boot title animation “wwb timer” plays again, and it returns to the timer screen.
- **During controller takeover**, timing still follows the switch as usual (not shown on screen), and switch events are also reported to the controller.
- **Persistence across power loss**: the chip stores to NVS (every 30 seconds while timing, and immediately when the switch is flipped); the web page stores to localStorage. The board has no RTC battery, so no time is counted while powered off; a sudden power loss while timing loses at most the last 30 seconds.

## Writing an offline program

```
native/
  wwb/wwb.h, wwb.cpp   framework: Device (buffered output, sends only changes), Canvas (u8g2 canvas), App, Runtime (controller takeover)
  timer/timer.cpp      wwb timer
  web/main.cpp         WebAssembly runtime (passes commands to the simulator)
  build_web.py         compiles to web/js/native.js
firmware/src/offline.* on-chip runtime (commands go straight to execute(), storage in NVS, ~60 fps task)
```

A program implements `wwb::App` and provides `wwb::createApp()`:

```cpp
class MyApp : public wwb::App {
  void setup(Device &d, uint64_t now) override;                      // boot; d.input(SWITCH) is the switch state at boot
  void input(Device &d, Input in, bool active, uint64_t t) override;  // switch / BOOT change, t is the change time in µs
  void controller(Device &d, bool attached, uint64_t now) override;  // controller attached / detached
  void frame(Device &d, uint64_t now) override;                      // ~60 times/s, also called during takeover (d.visible() is false)
  size_t report(uint64_t now, uint8_t *out, size_t cap) override;    // optional: state for the controller (protocol APP_STATE)
};
wwb::App *wwb::createApp() { return new MyApp(); }
```

- **OLED**: draw on a `Canvas` with u8g2's C API (`u8g2_DrawStr(c.u(), …)`, fonts from `u8g2_font_*`), then `d.oled(canvas)`; only the changed region is sent (`OLED_BLIT`). `fade()` does ordered-dither fade in/out, `invert()` inverts colors.
- **7-segment display**: `d.seg(segments[4])`, `d.segConfig(brightness, on/off)`; `wwb::segDigit()` gives the segment byte for a digit.
- **Matrix**: `d.mx(rows[8])` (row 0 at the top, bit7 on the left), `d.mxIntensity(0-15)`.
- **Storage**: `d.load()` / `d.save()`, a small binary blob.
- **Reporting**: `report()` returns the state for the controller; call `d.changed()` when the state changes, and subscribed controllers receive an `APP_STATE` event. wwb timer reports its timing state (format in [protocol.md](protocol.md)), and controller programs (such as dao timer) perform based on it, with the chip always being the source of truth for time.
- All times are the device's µs clock (the same clock as input events). Don't use platform functions like `millis()`, and don't use global state: when the simulator restarts the device it calls `createApp()` again.

To switch programs: change `build_src_filter` in `firmware/platformio.ini` and the arguments in `native/build_web.py`.

## Building

```bash
# Chip
conda activate esp32
cd firmware && pio run -t upload

# Web (generates web/js/native.js, a single file with embedded wasm)
conda run -n emsdk python native/build_web.py
```

`emsdk` environment: `conda create -n emsdk -c conda-forge emscripten=4.0.9`. The binaryen bundled with this conda-forge package is version 117, but emcc 4.0.9 needs 123: download `binaryen-version_123-x86_64-linux.tar.gz` from the [binaryen release page](https://github.com/WebAssembly/binaryen/releases/tag/version_123) and copy its `bin/` and `lib/` into the environment, overwriting the existing files.

## Controller protocol

```
Offline ──any command──▶ Connecting ──commands for 3s (no gap over 1s)──▶ Confirmed (connect animation 1.2s)──▶ Takeover
          ▲          │ gap over 1s or RELEASE                        │ same as left               │ RELEASE or no command for 1.5s
          └──────────┴─────────────── Interrupted ◀─────────────────┘                            ▼
          └──────────────────────────────────────────────────────────────────────────── Disconnected (disconnect animation)
```

- Before takeover, the controller may only use commands that don't touch the peripherals (PING, INFO, TIME, STATS, IO_READ, SUBSCRIBE, CONNECT…); display commands (0x2_/0x3_/0x4_), LED, IO_CONFIG and BENCH return `NOT_READY` (5).
- `CONNECT` (0x0D) queries the connection state: replies `u8 state` (0 offline / 1 connecting / 2 taken over) and `u32 ms remaining until takeover`.
- On entering takeover, the peripherals are first reset to their power-on defaults: OLED cleared, normal display, contrast 0xCF; 7-segment brightness 3, cleared; matrix brightness 1, rotation 1, 10MHz, cleared; debounce 20ms. On hand-back the defaults are restored the same way, and the offline program redraws everything.
- `wwb.Device` polls `CONNECT` on open and only returns once taken over (about 4.2 seconds; `connect=False` skips this); while idle it sends a `PING` every 0.5 seconds to keep control; `close()` sends `RELEASE`. The state machine lives in `Runtime` in `native/wwb/wwb.cpp`, shared by the chip and the web page.
