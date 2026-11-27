**English** · [简体中文](simulator.zh-CN.md)

# Web simulator

`web/` is a web page that simulates the whole device in the browser: OLED, 7-segment display, LED matrix, switch, BOOT button and on-board LED. Its purpose is to **see what a program looks like and try out interactions** without hooking up real hardware. The page only handles display, flipping the switch, and choosing which program to run.

There are two kinds of programs:

- **Offline program** (C++, `native/`): the program the chip runs on its own, currently the timer wwb timer. The page runs WebAssembly compiled from the same source (`web/js/native.js`), and it drives the display whenever no Python program is running. See [offline.md](offline.md).
- **Controller programs** (Python, `apps/`): control the device through the protocol. Running one on the page = plugging in a controller, which takes over the device; stopping it = unplugging, and the offline program comes back after playing the disconnect animation. The top bar shows whether it's currently “脱机程序运行中” (“offline program running”) or “控制器接管中” (“controller in control”).

The simulator **executes protocol commands one by one exactly as the firmware does** (`web/js/emulator.js` is written against `execute()` in `firmware/src/main.cpp`), so the frames a program sends to it are identical to those sent to real hardware, and so are the errors (e.g. an `OLED_RECT` with zero width returns `BAD_ARG` just the same). The same program runs on the real device by swapping `--port sim` for `/dev/ttyACM0`.

## Usage

```bash
python -m wwb.sim          # open http://127.0.0.1:8765 in the browser
```

The program list is on the right side of the page. Click ▶ to run one; the bridge starts it as `python -m <program> --port sim:…`, and the program's output appears in the “输出” (“Output”) panel. Switch: click it or press S / Space; BOOT: hold it down with the mouse or hold B.

- **Auto-restart on change** (on by default): whenever a file in the program's directory or in `host/wwb/` changes, the program being viewed is rerun.
- **Run = connect, stop = disconnect**: after a program connects, it takes about 3 seconds to confirm and the connect animation to finish before its output is shown; stopping plays the disconnect animation.
- **Refreshing the page / clicking “重启设备” (“restart device”) = power cycle**: the offline program starts from scratch; while the page is closed the Python program is paused, and when the page comes back it starts from scratch. The switch position and timer data are stored in the browser and survive a refresh (booting with the switch up = timer reset).
- You can also run a program yourself in a terminal; just add `--port sim` (e.g. `python -m wwb.showcase --port sim`).

## Writing a program

Each program is a package under `apps/` with a `__main__.py`. It can have multiple modules and any data files (images, JSON…), organized like an ordinary Python project:

```
apps/stopwatch/
  __init__.py      docstring: the first line is the title, the rest is the description (shown in the page's program list)
  __main__.py      entry point
  ...              other modules, assets
```

```python
# apps/stopwatch/__main__.py
from wwb import Font
from wwb.app import run

def main(d):                       # d is a wwb.Device
    d.on_input(lambda ev: print(ev.name, ev.active, ev.t_us))
    while True:
        d.oled_clear(wait=False)
        d.oled_text(0, 40, "12:34", Font.LOGISOSO24_NUM, flush=True, wait=False)
        ...

run(main)                          # parses --port, opens the device; exits cleanly on Ctrl+C / stop
```

A newly created program directory shows up in the page's list automatically. The `showcase` and `maxdemo` programs bundled with wwb are in the list too.

## How it connects

```
Python program ──TCP 8766──▶ wwb.sim ──WebSocket /ws──▶ simulated device in the page
               ◀──────── replies / switch events ─────────────
```

- The bridge only forwards bytes and doesn't parse commands; the program→page direction is rate-limited to the measured USB upstream speed (460 KiB/s); `--no-limit` turns this off.
- A newly opened page takes over the device, and the old page disconnects.
- `--host 0.0.0.0` lets phones and tablets on the LAN open the page (this also exposes the TCP port).
- You can also open the simulator by double-clicking `web/index.html`, but without the bridge it can't run programs.

## What is simulated

| Part | How it's simulated | Compared with hardware |
|---|---|---|
| OLED text | u8g2 font decoding ported to JS, font data extracted from the U8g2 sources (`web/tools/gen_fonts.py`), pixel-identical to the real device | — |
| OLED push | Frame buffer + dirty rectangles + push task, push time 200µs + 10.1µs/byte; new drawing during a push is merged into the next one | `maxdemo --rate 320`: hardware 95.7 fps, simulated 94.8 |
| OLED commands | Invert A6/A7, display on/off AE/AF, all-on A4/A5, contrast 81, flip A0/A1 C0/C8, start line 40–7F, offset D3 | `OLED_CONFIG` above 1.1MHz returns an `HW` error (real hardware would time out or garble) |
| 7-segment display | Only changed digits are written, each transfer 370µs + 440µs/byte (scaled by rise/fall time); only the latest content is kept; 8 brightness levels | Hardware 319.7/s, simulated 318.9/s; refresh counts for each showcase scene match the hardware logs |
| LED matrix | Rotation, only changed rows are written, config resent every second (overwrites rows written with `MX_RAW`), 16 brightness levels, display test, shutdown | Hardware 319.7/s, simulated 319.7/s |
| Input | Flipping the switch / pressing BOOT on the page = pin level change; reported after 20ms debounce, timestamp taken at the start of the change | Shortcuts: S / Space = switch, hold B = BOOT |
| Other commands | PING, INFO (with `"sim": true`), STATS (same fields as hardware), TIME, SUBSCRIBE, IO_READ, LED, SINK, SOURCE, REBOOT | `BENCH` gives estimates from the timing model; `UART_BAUD` only replies and has no effect |

## Limitations

- The browser can only show frames at the monitor's refresh rate (usually 60Hz); the OLED pushes internally at about 95fps, but what you see is the latest frame every 1/60 second.
- Real hardware faults aren't simulated: garbled 7-segment output from timing set too fast, I²C screen corruption, module brownouts, etc.

## Files

```
web/index.html, style.css
web/js/proto.js       protocol: COBS, CRC, frame encoding/decoding
web/js/u8g2.js        u8g2 font decoding and drawing
web/js/fonts.js       font data (generated file)
web/js/emulator.js    device emulation: command handling + per-peripheral timing
web/js/view.js        rendering of the three displays
web/js/offline.js     offline program runtime (controller takeover, localStorage storage)
web/js/native.js      offline program (generated by native/build_web.py)
web/js/app.js         page logic, program list, Python bridge connection
web/tools/gen_fonts.py  regenerates fonts.js (when the firmware changes fonts)
host/wwb/sim.py       Python bridge: web server, protocol forwarding, program start/stop and auto-restart
host/wwb/app.py       program entry point run(main)
apps/                 programs (one package each)
```
