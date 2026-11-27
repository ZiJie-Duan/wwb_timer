**English** · [简体中文](protocol.zh-CN.md)

# wwb serial protocol v1

The device wraps the switch, OLED, 7-segment display and dot matrix into a single set of binary commands. **USB and UART use exactly the same protocol and command handling**; only the physical layer differs:

| Channel | Device side | Host side | Parameters |
|---|---|---|---|
| USB | ESP32-C3 built-in USB-Serial/JTAG | something like `/dev/ttyACM0` | baud rate is irrelevant |
| UART | UART1, GPIO20 = RX, GPIO21 = TX | USB-to-TTL adapter (3.3V levels) or Raspberry Pi `/dev/serial0` ([raspberrypi.md](raspberrypi.md)) | default 921600 8N1, changeable with `UART_BAUD`, up to 5M |

Both channels can be used at the same time: a reply goes back on the channel the request came from; events are sent according to each channel's subscription settings.

Reference implementation: device side `firmware/src/proto.h` + `main.cpp`, host side `host/wwb/`.

## 1. Framing

```
Wire:  COBS(frame) 0x00 COBS(frame) 0x00 ...
Frame: op u8 | flags u8 | seq u16 | payload (0–1100 B) | crc16 u16
```

- All multi-byte fields are **little-endian**.
- `crc16` = CRC-16/CCITT-FALSE (polynomial 0x1021, init 0xFFFF, no reflection, no final XOR), covering `op..payload`. In Python: `binascii.crc_hqx(data, 0xFFFF)`.
- After COBS encoding a frame contains no 0x00, so 0x00 is the frame boundary; on garbage or a partial frame, discard up to the next 0x00 to resync. At boot the ROM prints startup messages over USB; the host simply drops them as CRC failures.
- Payload is at most 1100 bytes, enough for a full OLED frame (1024B).

### flags

| Bit | Name | Direction | Meaning |
|---|---|---|---|
| 0x01 | NOREPLY | request | No reply on success (errors are still replied). Used for high-rate streaming, rate-limited by USB/serial flow control itself |
| 0x02 | RESP | reply | Reply from the device; `op` and `seq` match the request |
| 0x04 | EVENT | event | Unsolicited report from the device |
| 0x08 | ERR | reply | Error; payload = 1-byte error code |
| 0x10 | FLUSH | request | OLED drawing commands: push to the screen right after executing |

### Error codes

| Code | Name | Meaning |
|---|---|---|
| 1 | UNKNOWN_OP | Unknown opcode |
| 2 | BAD_LEN | Wrong payload length |
| 3 | BAD_ARG | Argument out of range |
| 4 | HW | Peripheral not responding (e.g. OLED I²C failure) |
| 5 | NOT_READY | Controller connection not yet confirmed (must be steady for 3 seconds after connecting); peripherals cannot be driven |

## 2. Commands

The payload column lists fields in order; the reply column gives the reply payload (empty if none).

### System 0x0_

| op | Name | payload | Reply |
|---|---|---|---|
| 0x01 | PING | anything | echoed back |
| 0x02 | INFO | — | JSON: firmware version, chip, MAC, current configuration of each peripheral, font list |
| 0x03 | SINK | anything | u32 total bytes received (measures upstream throughput) |
| 0x04 | SOURCE | u32 total bytes, u16 chunk size | First sends a number of EVENT frames (op=0x04, payload is data), then replies with u32 bytes sent, u32 device time in µs |
| 0x05 | STATS | — | JSON: per-channel RX/TX counters, CRC errors, requested/actual refresh counts and timings for each peripheral |
| 0x06 | STATS_RESET | — | |
| 0x07 | REBOOT | — | Reboots after replying |
| 0x08 | UART_BAUD | u32 baud | Replies at the old baud rate, then switches |
| 0x09 | SUBSCRIBE | u8 mask (bit0 = input events, bit1 = offline app state) | Applies to the channel the request came from; by default both channels subscribe to input events |
| 0x0A | BENCH | see below | JSON: on-device peripheral self-test results |
| 0x0B | TIME | — | u64 device time in µs (same clock as event timestamps) |
| 0x0C | RELEASE | — | The controller releases the device; the offline app resumes the displays immediately |
| 0x0D | CONNECT | — | u8 connection state (0 offline / 1 connecting / 2 taken over), u32 ms remaining until takeover |
| 0x0E | APP_STATE | — | Offline app state (format below); after subscribing to bit1, it is reported as an event whenever it changes |
| 0x0F | APP_DATA | u8 0 → read; u8 1 + data (≤256B, empty = clear) → write | Controller storage: kept in chip flash (NVS), survives power loss, separate from the offline app's data. Don't write it frequently |

**Controller and offline app**: when no host is attached, the offline app (the timer) on the chip drives the peripherals. Host requests must **continue for 3 seconds** (at most 1 second apart) before the connection is confirmed; then a 1.2-second connect animation plays and the host takes over. Until then, display commands return `NOT_READY`; poll the state with `CONNECT`. After takeover, sending `RELEASE` or **1.5 seconds without any request** hands control back to the offline app, so an idle controller must send requests periodically. `wwb.Device` handles all of this automatically (waits for takeover on open, sends `PING` every 0.5 seconds, `RELEASE` on close). See [offline.md](offline.md).

**The chip is the source of truth for timing**: the offline timer wwb timer keeps counting while a controller has taken over. `APP_STATE` returns 24 bytes:

```
u8 kind (1 = timer)  u8 flags (bit0 = running)  u16 0
u32 reset count (+1 each time it boots with the switch up and resets)  u32 completed "on → off" count
u64 total ms (including the segment in progress)  u32 ms in current segment (0 when stopped)
```

On start, stop and reset the chip reports an `APP_STATE` event (requires subscribing to bit1). In `wwb.Device`: `timer()` reads the state,
`on_timer(callback)` + `subscribe(timer=True)` receives events, `app_data()` / `set_app_data()` read and write controller storage.
dao timer (`apps/dao`) works exactly this way: all time comes from the chip and ritual progress is kept in controller storage, so it picks up seamlessly after switching hosts or reconnecting.

**BENCH**: `u8 target, u16 count, args…`. Drives a peripheral repeatedly on the device itself and times it, bypassing USB, to measure the peripheral's own limits.

| Target | Args | Notes |
|---|---|---|
| 1 OLED | u32 I²C Hz (0 = current) | Pushes full frames; restores the original clock afterwards |
| 2 SEG | u8 CLK rise µs, u8 fall µs, [u8 DIO rise µs, u8 wait before reading ACK µs] | Writes 4 digits; `ack_fails` is the number of bytes with no ACK. When judging timing reliability, give the wait before reading ACK enough time (150), otherwise a slow rising edge produces false ACKs |
| 3 MX | u32 SPI Hz | Writes 8 rows |

### Inputs and onboard LED 0x1_

| op | Name | payload | Reply |
|---|---|---|---|
| 0x10 | IO_READ | — | 13B per input: u8 state, u32 change count, u64 last change time µs; order is switch (1 = on/closed), BOOT (1 = pressed) |
| 0x11 | IO_CONFIG | u32 debounce µs (default 20000) | |
| 0x12 | LED | u8 0/1 | At boot the LED stays lit to indicate both channels are ready |
| 0x18 | EV_INPUT (event) | u8 input (0 switch / 1 BOOT), u8 state, u32 count, u64 time µs | — |

Inputs use an edge interrupt to record **the moment bouncing starts**, and once debounce confirms the change it is reported with that timestamp, so event timestamps are not affected by the debounce delay and can be used directly for timing.

### OLED 0x2_ (SSD1306 128×64)

Framebuffer layout: 8 pages × 128 columns; byte `page*128 + x` holds column `x`, rows `page*8 .. page*8+7`, **LSB on top**.

All drawing goes into a framebuffer on the device and records a dirty rectangle; the push task only sends the dirty region to the screen. New drawing that arrives while a push is in progress is merged into the next push (only the latest image is kept), so the host can send as fast as it likes without caring about screen speed; `commits - pushes` in `STATS` is the number of merged frames.

| op | Name | payload | Notes |
|---|---|---|---|
| 0x20 | OLED_FRAME | 1024B | Full frame |
| 0x21 | OLED_BLIT | u8 start page, u8 start column, u8 page count, u8 column count, data | Partial update; data is page-ordered (pages × columns bytes). Partial pushes are faster |
| 0x22 | OLED_TEXT | i16 x, i16 y (baseline), u8 font, u8 color, UTF-8 text | Color 0 clear / 1 set / 2 invert |
| 0x23 | OLED_CLEAR | [u8 color] | |
| 0x24 | OLED_RECT | i16 x, y, w, h, u8 mode | 0 fill clear / 1 fill / 2 outline / 3 invert |
| 0x25 | OLED_CMD | SSD1306 command bytes | e.g. contrast `81 xx`, invert `A7`, display off `AE` |
| 0x26 | OLED_CONFIG | u32 I²C Hz | Default 1.1MHz, the current hardware limit; higher settings garble the display |
| 0x2F | OLED_FLUSH | — | Push |

Drawing commands (FRAME/BLIT/TEXT/CLEAR/RECT) with the `FLUSH` flag push immediately after executing; without it they only modify the framebuffer, so you can draw several things and then issue a single `OLED_FLUSH`.

Font IDs: 0 `6x10`, 1 `9x15`, 2 `logisoso16`, 3 `logisoso24` (digits only), 4 `logisoso32` (digits only), 5 `wqy12` (includes common Chinese characters).

### 7-segment display 0x3_ (TM1637)

| op | Name | payload | Notes |
|---|---|---|---|
| 0x30 | SEG_RAW | 4B segment codes | bit0=a … bit6=g; bit7 of digit 2 (index 1) = colon |
| 0x31 | SEG_TEXT | text | Digits, some letters, `-` `_` `=`; `:` lights the colon; right-aligned |
| 0x32 | SEG_CONFIG | u8 brightness 0–7, u8 on/off, u8 CLK rise µs, u8 fall µs, [u8 DIO rise µs] | Default 3 / on / 50 / 2 / 5 |

Refreshing is done by a dedicated task, with timing executed edge by edge from a hardware timer interrupt (the CPU is idle while waiting for slow rising edges); likewise only the latest content is kept, and **only the digits that changed are written** (a single-digit change needs just 2 bytes, about 2.3× faster than a full refresh). After a full 1 second idle it automatically resends the configuration and rewrites the whole display; if an ACK fails during continuous refreshing, the next refresh also resends it, so the module recovers automatically after being power-cycled on its own.

When pushing at a fixed frame rate, frames must arrive further apart than one refresh takes (about 1.3ms for a single digit), otherwise the device keeps only the later frame.

### Dot matrix 0x4_ (MAX7219)

| op | Name | payload | Notes |
|---|---|---|---|
| 0x40 | MX_FRAME | 8B | Logical orientation: byte 0 is the top row, bit7 is leftmost; the device converts according to the rotation setting |
| 0x41 | MX_CONFIG | u8 brightness 0–15, u8 rotation 0–3 (×90° clockwise), u8 flags (bit0 display test, bit1 shutdown), [u32 SPI Hz] | Default 1 / 1 / 0 / 10MHz |
| 0x42 | MX_RAW | (register, value) pairs | Writes MAX7219 registers directly |

MX_FRAME is written out synchronously during command handling, writing only rows that differ from last time (about 31µs for a full frame at 10MHz); configuration registers are automatically resent once per second.

## 3. Concurrency model (device side)

```
USB RX task ─────┐                       ┌─ OLED push task (priority 7, I²C interrupt-driven)
(priority 5)     ├─ dispatch() (mutex) ──┼─ 7-seg task (priority 6, timing run edge by edge from hardware timer interrupt)
UART RX task ────┤                       └─ dot matrix: SPI written synchronously inside the command, changed rows only
Offline app task ┘ (priority 4, ~60 fps, calls execute() directly for commands)
Input interrupt → input task (priority 6) → event broadcast + handed to offline app
```

Display commands only update the "desired state" and wake the corresponding task, then return immediately; the peripherals refresh in parallel without blocking each other.
The OLED and 7-segment tasks have higher priority than the RX tasks but use almost no CPU (they spend most of their time waiting on hardware), so they keep running at full speed even when a flood of commands arrives. For measurements see "Three displays at full speed" in benchmarks.md.

## 4. Examples

PING, seq = 1, empty payload:

```
Frame:      01 00 01 00 45 C1        (crc16(01 00 01 00) = 0xC145, written little-endian)
COBS+0x00:  02 01 02 01 03 45 C1 00
```

Python:

```python
from wwb import Device, Font
with Device("/dev/ttyACM0") as d:
    d.oled_clear()
    d.oled_text(0, 30, "12:34.56", Font.LOGISOSO24_NUM, flush=True)
    d.seg_text("12:34")
    d.mx_frame(bytes([0x18, 0x3C, 0x7E, 0xDB, 0x18, 0x18, 0x18, 0x18]))
    d.on_input(lambda ev: print(ev))
```
