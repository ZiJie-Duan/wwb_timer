**English** · [简体中文](benchmarks.zh-CN.md)

# Performance limits, measured

2026-10-24, firmware 0.1.0, USB connection, board `80:53:e0:b4:3e:5c`. To rerun: `python -m wwb.bench` (results are saved to `results/`).

## Methodology: don't mix the two kinds of numbers

The chip runs a single firmware: generic drivers + a serial API, **with no demo logic at all**. All tests fall into two categories:

| Category | How it is measured | What it measures | Tools |
|---|---|---|---|
| **End-to-end (host-driven)** | Python on the computer generates every frame on the fly and sends it frame by frame over USB as protocol commands; the chip only executes them. Rates are computed from the chip's `STATS` counters of frames "actually pushed to the screen" | Real capability of the whole host → USB → firmware → screen chain, i.e. the speed future host programs will get | `wwb.maxdemo`, `wwb.bench e2e`, USB link tests |
| **On-device self-test** | The host sends one `BENCH` command; the chip drives the peripheral N times locally and times it, bypassing USB | Hardware limit of a single peripheral with the current wiring (I²C/SPI clock, TM1637 timing) | `wwb.bench oled / seg / mx` |

For example, in the "capped at 320" test: each OLED frame is drawn on the computer with PIL (1KB, split into 4 `OLED_BLIT` commands), each 7-segment frame is a frame number computed on the computer and sent as 4 bytes of segment codes (`SEG_RAW`), and each dot-matrix frame is a pointer position computed on the computer and sent as 8 bytes (`MX_FRAME`).

## Summary: limits and bottlenecks at each stage

| Stage | Limit | Bottleneck | Current default |
|---|---|---|---|
| USB round trip (empty packet) | 0.28 ms, about 3600/s | USB frame scheduling | — |
| USB upstream (host→device) | about 460 KiB/s | The USB-Serial/JTAG OUT endpoint has only a single 64B buffer | — |
| USB downstream (device→host) | about 740 KiB/s | — | — |
| OLED full frame (hardware) | 95 fps @1.1MHz (a 2.6MHz setting still gets ACKs, but visibly garbles and shifts) | I²C clock + pull-up resistors | 1.1MHz |
| OLED full frame (end-to-end) | about 90 fps | Same as above (USB can deliver 420+ frames/s, the screen can only push 95) | |
| OLED partial, 4 pages × 96 columns | about 236 fps | Bytes pushed | |
| 7-segment full refresh | about 390/s (2.55 ms) | Signal rising edge about 43µs, 9 clocks per byte | CLK 50µs / fall 2µs / DIO 5µs |
| 7-segment, one digit changed | about 800/s | Same as above, only 2 bytes sent | automatic |
| Dot matrix (hardware) | 32000 frames/s @10MHz; 20MHz also looks fine | SPI clock | 10MHz |
| Dot matrix (end-to-end) | 8800 frames/s one at a time, 19800 frames/s in batches of 32 | One at a time, it's the host's send rate | |
| **Three displays at full speed** | **OLED 91 fps + 7-segment 666/s + dot matrix 14730/s** | The dot matrix gets whatever USB upstream bandwidth the OLED leaves | `python -m wwb.maxdemo` |

What the human eye can perceive is far below these numbers: the SSD1306 panel itself refreshes at about 90–110Hz, and the MAX7219 scans internally at about 800Hz. So **only the 7-segment display is truly limited** (its hardware rising edge is too slow), and the OLED just about reaches the panel refresh rate.

## Three displays at full speed (`python -m wwb.maxdemo`)

Each display is pushed at its own limiting pace: OLED at 100 frames/s (every frame rendered live on the host, showing the three displays' measured rates over the previous second), 7-segment counting at 2000/s, and all remaining bandwidth goes to the dot matrix (128 frames per round). In the same test each display is also run alone for comparison:

| | Alone | All three together | Retained |
|---|---|---|---|
| OLED (full frame, every frame fully changes) | 95.0 fps | 91.3 fps | 96% |
| 7-segment (counter, 2–3 digits change each time) | 760 /s | 666 /s | 88% |
| Dot matrix (scanning dot, 1–2 rows change per frame) | 27252 /s | 14730 /s | 54%, USB upstream already at 353 KiB/s |

Zero errors (7-segment ACK, OLED I²C and USB CRC all 0).

Optimization history (each step targets a measured bottleneck):

| Version | OLED | 7-seg | Dot matrix | Bottleneck and fix |
|---|---|---|---|---|
| First version (one command per display per round) | 84 | 231 | 406 | The test method itself: everything dragged along by the OLED full frame → each display sends at its own pace |
| Each at its own pace | 68 | 278 | 6813 | With the dot matrix off, OLED goes back to 94 → dot-matrix commands run in the high-priority RX task, while the I²C driver must return to the push task every 32 bytes to refill the FIFO and gets starved → **raise the OLED push task above the RX tasks**; **dot matrix writes only changed rows** |
| Both of the above | 94.7 | 335 | 6399 | The more dot-matrix traffic, the slower the 7-segment: while waiting for rising edges the 7-segment busy-waits the CPU (about 1.2ms each time) → **switch to executing edge by edge from a hardware timer interrupt**, leaving the CPU idle while waiting |
| Timer interrupt | 93.3 | 109–443 | 6773–14718 | The 7-segment task has low priority and queues between refreshes → **raise the 7-segment task above the RX tasks** (it only schedules steps and uses almost no CPU); the test program interleaves 7-segment commands between dot-matrix frames |
| Final | 91.3 | 666 | 14730 | Dot matrix limited by USB upstream bandwidth |

## 7-segment and dot matrix capped at 320 frames/s + OLED at full speed (`python -m wwb.maxdemo --rate 320`)

At full speed, the 7-segment and dot-matrix refresh far exceeds what the eye or the devices can show (the dot matrix just looks like a faint glow), which is pointless. So they are capped at 320 frames/s, with each frame's content made verifiable:

- The 7-segment shows the frame number: at a full 320/s the hundreds digit ticks 3.2 times per second
- The dot matrix shows a pointer that turns 1/320 of a revolution per frame: at a full 320/s it makes exactly one revolution per second

| | Target | Measured (20 s) | Sent / actually refreshed |
|---|---|---|---|
| OLED | full speed | 96.2 fps | — |
| 7-segment | 320 /s | 319.7 /s (319–321 per second) | 6386 / 6386, zero dropped frames |
| Dot matrix | 320 /s | 319.7 /s (319–321 per second) | 6386 / 6386, zero dropped frames |

Problems fixed before reaching this result:

| Symptom | Cause | Fix |
|---|---|---|
| 7-segment dropped about 10 frames per second (310/s) | Every second the device resent the configuration and rewrote the full display (about 3.9ms > the 3.1ms frame interval); when the host fell behind and sent two catch-up frames back to back, the device kept only the later one | Firmware: resend configuration only after a full 1 second idle (if the module loses power during continuous refreshing, the ACK failure triggers a resend); host: catch-up frames are spaced at least half a period apart |
| Host only sent 272/s | Per OLED frame, 2ms of host rendering + 2.2ms blocking to write 1KB stalled the tick in the same loop | Split into threads: after rendering, the OLED frame is split into 4 partial updates (only the last one pushes), each holding the serial port ≤0.6ms; the 7-segment and dot matrix are sent from a separate tick thread |

## USB link

| Packet size | Median round trip | p99 |
|---|---|---|
| 0 B | 0.278 ms | 0.735 ms |
| 64 B | 0.904 ms | 1.221 ms |
| 256 B | 1.308 ms | 1.768 ms |
| 1024 B | 3.980 ms | 4.395 ms |

Upstream: 165 KiB/s with 64B frames (2644 frames/s), 459 KiB/s with 1024B frames. Downstream 741 KiB/s.

**Tracking down the upstream bottleneck**: increasing the device-side read chunk from 512B to 2048B and the RX ring buffer from 8KB to 16KB made no difference; encoding a 1KB frame on the host takes only 0.18ms (5000+ frames/s), so that isn't the bottleneck either. Conclusion: the USB-Serial/JTAG hardware has a single-buffered OUT endpoint — each 64B packet must be read by the firmware before the next can be received, about 6400 packets/s.

**Reliability**: IDF's `usb_serial_jtag_is_connected()` falsely reports "not connected" under heavy load (22 false reports out of 74661 replies in a 4-minute stress test). Early firmware dropped replies based on it, causing occasional host timeouts; now it only counts them (`tx_not_connected` in `STATS`) and sends anyway — the same stress test has zero timeouts and zero lost packets.

**Firmware side**: USB now uses IDF's native `usb_serial_jtag` driver (Arduino's HWCDC does one queue operation per byte), and all log output is disabled (it would get mixed into the data stream).

## OLED (SSD1306, I²C)

60 consecutive full frames pushed on the device (1024B + window commands):

| I²C setting | Per frame | fps | Errors |
|---|---|---|---|
| 400 kHz | 23.76 ms | 42.1 | 0 |
| 800 kHz | 13.05 ms | 76.6 | 0 |
| 1000 kHz | 11.19 ms | 89.4 | 0 |
| **1100 kHz** | **10.49 ms** | **95.4** | **0** |
| 1150–1400 kHz | — | — | all fail (return immediately) |
| 1700–2200 kHz | — | — | all time out |
| 2300–2400 kHz | 9.55 ms | 104.7 | 0 |
| 2600–2800 kHz | 9.31 ms | 107.4 | 0 |
| ≥3500 kHz | — | — | all fail |

1.15–2.2MHz is an unusable range where the new IDF I²C driver computes its clock divider. Settings above 2.3MHz work again because the ESP32 master waits for SCL to actually go high before continuing, so the real clock is limited to about 1.2MHz by the pull-up rising edge. Every byte is ACKed, but **at the 2.6MHz setting a checkerboard visibly shows snow and misalignment** (2026-10-24) — ACK does not mean the data is correct. The default is 1.1MHz, which is the OLED limit of the current hardware.

Push overhead: at 1.1MHz the theoretical time is 8.4ms/frame, measured 10.5ms; the extra ~2ms is the gaps where the driver refills the hardware FIFO every 32 bytes.

**How to go faster**: partial updates (`OLED_BLIT`, or change only part and then `FLUSH`; the device pushes by dirty rectangle). A 4 pages × 96 columns region reaches 236 fps.

## 7-segment display (TM1637, software timing)

Key finding: **a slow rising edge produces false ACKs**. After DIO is released it relies on the pull-up resistor to rise slowly; if it hasn't risen yet when the ACK is read, the low level looks just like the TM1637 pulling ACK low. That's why, in the first sweep, shorter waits appeared "more successful" (zero failures at 1µs).

Fix: during self-test, wait an extra 150µs before reading ACK (strict ACK). Calibration: the known-reliable 50µs configuration has zero failures in strict mode; the 1µs configuration fails 100% in strict mode (false ACKs exposed).

Under strict ACK, sweeping the CLK rise wait (fall 2µs, DIO 5µs, 1500 bytes per step):

| CLK rise wait | ACK failures |
|---|---|
| 50 µs | 0 |
| 46 µs | 0 |
| 44 µs | 0 |
| 43 µs | 44–101 |
| 42 µs | 1255–1377 |
| 40 µs | 1500 |

The rise time is about 43µs; the default is 50µs (about 13% margin). Falling edge: 1µs fails, 2µs is reliable. The DIO rise wait can be pushed down to 0 (it only needs to settle before CLK rises); the default leaves 5µs.

| Timing | One full refresh | Per second |
|---|---|---|
| First version: rise/fall both 50µs | 5.53 ms | 181 |
| Fall 2µs | 2.79 ms | 358 |
| Plus DIO 5µs | 2.55 ms | 392 |
| Only changed digits sent (single digit) | about 1.25 ms | about 800 |

With normal timing (rise 50µs ≥ actual 43µs) the ACK check is trustworthy, and the firmware uses it to resend the full display on error.

**How to go faster**: hardware. Remove the filter capacitors on the module or use a stronger level-shifting scheme; once the rising edge drops to a few µs, the same code can reach thousands of refreshes per second.

## Dot matrix (MAX7219, hardware SPI)

| SPI | Per frame (8 rows) | Frames/s |
|---|---|---|
| 1 MHz | 154.7 µs | 6466 |
| 2 MHz | 86.5 µs | 11555 |
| 4 MHz | 52.1 µs | 19198 |
| 8 MHz | 34.7 µs | 28840 |
| 10 MHz | 31.1 µs | 32192 |

Visual check (`python -m wwb.visual` cycles through displaying the current MHz number while redrawing at high speed): 1–20MHz all correct. The default is the MAX7219 spec maximum of 10MHz, only 7µs per frame slower than 20MHz, leaving 2× headroom.
There is no readback (DOUT is not connected); for automatic verification, the module's DOUT could be wired through a voltage divider to a spare GPIO as a loopback.

## End-to-end (host streaming → screen)

4 seconds each, sent with `NOREPLY`, counted by the device's `STATS`:

| Scenario | Host sent | Actually on screen |
|---|---|---|
| OLED full frame | 423/s | 89.5 fps |
| OLED partial 4×96 | 901/s | 235.7 fps |
| 7-segment, last digit changes | 9143/s | 803/s |
| 7-segment, all four digits change | 9074/s | 351/s |
| Dot matrix one at a time (1MHz → 10MHz) | 8985/s | 5983/s → 8786/s (= host send rate) |
| Dot matrix in batches of 32 (1MHz → 10MHz) | — | 5940/s → 19760/s |
| All three together (one command each per round) | 407 rounds/s | OLED 88 fps / 7-segment 248/s / dot matrix 407/s |

When sending faster than the screen can refresh, the device keeps only the latest content (OLED, 7-segment), so latency does not pile up.
