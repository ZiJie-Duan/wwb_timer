**English** · [简体中文](hardware.zh-CN.md)

# wwb_timer hardware notes

An interactive device driven by an ESP32-C3: 1 switch + 0.96" OLED + 4-digit 7-segment display + 8×8 LED matrix, plus one spare UART.
This document records the parts, wiring, power and measured results. Performance data is in [benchmarks.md](benchmarks.md); the communication protocol is in [protocol.md](protocol.md).

## 1. Parts

| Part | Model / spec | Verified |
|---|---|---|
| MCU | ESP32-C3 Super Mini, chip ESP32-C3FN4 (QFN32, rev v0.4), 4MB embedded flash, 160MHz single-core RISC-V | Read out with esptool |
| OLED | 0.96" white, 4-pin I²C | Driver **SSD1306 128×64**, address **0x3C** (confirmed 2026-10-19 by drawing a border with both the SSD1306 and SH1106 drivers and comparing) |
| 7-segment display | TM1637, 0.56" 4-digit red, with colon | The colon is bit7 of digit 2's segment byte; not standard I²C, needs bit-banged timing |
| LED matrix | Single MAX7219 8×8 | Device count 1; the module's IN side is connected, OUT side left unconnected |
| Switch | Plain 2-pin mechanical switch | Internal pull-up; closed (on) = low |
| On-board | Blue LED (GPIO8, active low), BOOT button (GPIO9, low when pressed) | Exposed through the firmware API |

There are two boards: the 2026-10-19 first test used MAC `80:53:e0:b4:3e:40`; the one in use since 2026-10-24 is `80:53:e0:b4:3e:5c` (visible under `/dev/serial/by-id/`). Both are wired identically.

## 2. GPIO assignment

All numbers below are **GPIO numbers** (the numbers used in code), not header pin order. Defined in `firmware/src/board.h`.

| Peripheral | Peripheral pin | GPIO | Purpose |
|---|---|---|---|
| OLED | SDA | 0 | I²C data |
| OLED | SCL | 1 | I²C clock |
| TM1637 | DIO | 3 | Bidirectional data (open-drain) |
| TM1637 | CLK | 4 | Clock (open-drain) |
| Switch | One side | 5 | Input, internal pull-up; other side to GND |
| MAX7219 | DIN | 6 | SPI MOSI |
| MAX7219 | CLK | 7 | SPI SCK |
| On-board LED | — | 8 | Active low |
| BOOT button | — | 9 | Low when pressed |
| MAX7219 | CS/LOAD | 10 | Latch (rising edge) |
| UART | Peer TX → | 20 | ESP32 RX |
| UART | Peer RX ← | 21 | ESP32 TX |

The strapping functions of GPIO2/8/9 are avoided (8 and 9 are only used after boot). All I²C/SPI/UART pins are set explicitly in code rather than relying on library defaults.

## 3. Power and logic levels

The ESP32-C3's GPIOs are 3.3V logic; the TM1637 and MAX7219 are powered at 5V.

| Part | Supply | Signals |
|---|---|---|
| ESP32-C3 | **USB power only** | 3.3V |
| OLED | 3.3V (board's 3V3) | SDA/SCL pulled up to 3.3V |
| TM1637 | External 5V | CLK, DIO through a level shifter; DIO must be bidirectional |
| MAX7219 | External 5V | DIN, CLK, CS through a 3.3V→5V level shifter |
| Switch | No supply needed | GPIO5 ↔ GND |

Development wiring (since 2026-10-19): **external 5V feeds only the modules and the level shifter's high side, not the board's 5V pin**; the board is powered over USB; all grounds are tied together. This way USB can stay plugged in for debugging without two 5V supplies back-feeding into each other.

Why: the MAX7219 requires a high level ≥3.5V; the TM1637's high threshold is 0.7×VDD, which is also 3.5V at 5V supply, so driving them directly from 3.3V isn't guaranteed to meet spec.

**The finished unit inside the enclosure** runs on battery instead: 18650 → CD42 charge/discharge boost module (5V) → rocker switch on the side → 5V bus (board 5V pin, 7-segment display, LED matrix, level shifter high side). The power distribution and level shifting are soldered onto a hand-etched copper-clad board, with no schematic kept. A simplified wiring for building your own (no level shifter needed) is in [build.md](build.md).

The level shifter's model wasn't recorded. Its **rising edge on the TM1637 lines measures about 43µs** (see below), which indicates a pull-up-resistor type (e.g. a BSS138 design), combined with the filter capacitors on the 7-segment module.

## 4. Measured results (affecting driver parameters)

| Item | Result | Source |
|---|---|---|
| Matrix orientation | The current mounting needs a **90° clockwise rotation** (firmware default `rotation = 1`; on 2026-10-24 the user reported digits 1–20 all readable); on 2026-10-19 it was upright at 0°, the mounting changed afterwards | User visual check |
| TM1637 rising edge | After releasing CLK, wait **≥44µs** to be reliable; 50µs is used; 2µs is enough for the falling edge; DIO only needs to lead CLK slightly (5µs) | Strict ACK sweep |
| TM1637 ACK | When the rising edge is too slow, a released DIO that hasn't risen yet also reads low and **is mistaken for an ACK**; judging whether timing is reliable requires a "strict ACK" (wait an extra 150µs before reading ACK) | Found 2026-10-24 |
| OLED I²C | 1.1MHz with zero errors (about 95fps full frame), the current limit; settings of 1.15–2.2MHz fall into an unusable range of the driver's clock divider; 2.3–2.8MHz settings get ACKs but **visibly show garbled, shifted output** | Clock sweep + visual check |
| MAX7219 SPI | 1–20MHz all visually correct; default 10MHz (spec maximum), 31µs per frame | Clock sweep + visual check |
| USB upstream | Caps at about 400 KiB/s: the USB-Serial/JTAG OUT endpoint has a single 64B buffer, and the next packet can only be received after the firmware reads it out | Larger read chunks made no difference |

### Possible hardware speedups

- **TM1637**: remove the filter capacitors on CLK/DIO on the module, or replace the level shifter with a stronger pull-up / push-pull design; the rising edge could drop from about 43µs to a few µs, making refresh about 10× faster.
- **OLED**: adding 2.2kΩ pull-ups on SDA/SCL may allow stable operation at a higher I²C clock.

## 5. Building and flashing

- Firmware: `cd firmware && pio run -t upload` (finds the serial port automatically; add `--upload-port` if it can't); you can also use the merged image from Releases, see [build.md](build.md#6-flashing-the-firmware).
- Default serial port for the host side: the `WWB_PORT` environment variable; otherwise `/dev/ttyACM0`; otherwise auto-detect a USB serial port with Espressif's VID (0x303A) (macOS, Windows).
- On Linux the user must be in the `dialout` group to open the serial port.
