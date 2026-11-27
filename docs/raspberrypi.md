**English** · [简体中文](raspberrypi.zh-CN.md)

# Raspberry Pi as the host (UART)

The host doesn't have to be a computer. A Raspberry Pi connected to the ESP32's UART1 through the hardware serial port on its GPIO header can run all the Python programs (the `wwb` CLI, `apps/`, showcase, maxdemo). Programs are written on the computer and pushed over WiFi to run on the Pi with `python -m wwb.remote`. The protocol, commands and controller takeover flow are exactly the same as over USB; only the port changes to `/dev/serial0`.

Tested on a Raspberry Pi Zero 2 W (Debian 13 trixie, aarch64).

## Wiring

| Raspberry Pi | | ESP32-C3 |
|---|---|---|
| GPIO14 TXD (physical pin 8) | → | GPIO20 (UART1 RX) |
| GPIO15 RXD (physical pin 10) | ← | GPIO21 (UART1 TX) |
| GND (physical pin 6) | — | GND |

Both sides are 3.3V logic and can be connected directly. The dev board is still powered over USB (see [hardware.md](hardware.md)); **the two sides must share ground**.

## Raspberry Pi system setup

Append to the end of `/boot/firmware/config.txt`:

```
enable_uart=1
dtoverlay=miniuart-bt
```

Remove `console=serial0,115200` from `/boot/firmware/cmdline.txt`; otherwise the kernel and the login console will occupy this serial port. Then reboot. After rebooting, `/dev/serial0 → ttyAMA0`.

`miniuart-bt` moves the PL011 hardware UART to GPIO14/15 and switches Bluetooth to the mini UART. There are two reasons not to use the mini UART:

- its baud rate follows the GPU core clock;
- its FIFO is tiny and easily drops bytes at 921600 baud.

If you don't need Bluetooth, you can use `dtoverlay=disable-bt` instead. The user `pi` is in the `dialout` group by default, so it can open the serial port without sudo.

## Installation (the Pi only needs a runtime)

Development and testing all happen on the computer (you can try things in the web simulator first). The Pi only runs things: the computer syncs the code over, and the Pi drives the device over UART.

```bash
# Run once on the Pi: Miniforge + a conda environment with just the dependencies
curl -fsSL -o Miniforge3.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3.sh -b -p ~/miniforge3 && rm Miniforge3.sh
~/miniforge3/bin/conda create -y -n wwb python=3.12 pyserial numpy pillow
```

Set up ssh public-key login from the computer (`ssh-copy-id pi@raspberrypi.local`). It's also recommended to turn off the Pi's WiFi power saving; otherwise latency jumps to several hundred milliseconds after it's been idle for a while:

```bash
sudo nmcli con modify <connection-name> 802-11-wireless.powersave 2
```

## Usage (run on the computer)

```bash
conda activate esp32
python -m wwb.remote apps.stopwatch          # sync host/wwb and apps/, run on the Pi
python -m wwb.remote wwb.showcase --seconds 30
python -m wwb.remote wwb info                # the CLI works too
python -m wwb.remote --sync                  # sync only
```

- The first sync transfers all the code; after that rsync only sends changed files.
- The program's output is shown live on the computer.
- Ctrl+C stops the program on the Pi, and the program sends `RELEASE` as usual to hand back the device.
- If ssh disconnects, the program receives SIGHUP and likewise exits cleanly.

`wwb.remote` is configured entirely through environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `WWB_REMOTE` | Target machine | `pi@raspberrypi.local` |
| `WWB_REMOTE_DIR` | Code directory on the Pi | `~/wwb_timer` |
| `WWB_REMOTE_PYTHON` | Python on the Pi | `~/miniforge3/envs/wwb/bin/python` |
| `WWB_REMOTE_PORT` | Serial port on the Pi | `/dev/serial0` |

When running on the Pi:
- `PYTHONPATH` points to the synced `host/`, so no `pip install` is needed;
- `WWB_PORT` is set to the serial port, so every program uses it by default. A program's `--port` default comes from `WWB_PORT`, falling back to `/dev/ttyACM0` when unset.

## Resident program (start on boot)

On the Pi, the systemd user service `wwb.service` keeps one program resident (e.g. dao timer). It restarts automatically 3 seconds after a crash, and when stopped the program hands back the device as usual.

```bash
# On the computer
python -m wwb.remote --deploy apps.dao       # sync code, set as the resident program and start it
python -m wwb.remote --deploy                # after code changes: sync and restart the resident program
python -m wwb.remote --svc status            # status, resident program, recent logs
python -m wwb.remote --svc logs -f           # follow logs
python -m wwb.remote --svc stop | start | restart | enable | disable

# On the Pi (--deploy installs ~/.local/bin/wwbctl)
wwbctl status
wwbctl use apps.dao_fast                     # switch the resident program
wwbctl logs -f
```

While the resident program is running, temporarily running another program with `wwb.remote` stops it first and starts it again afterwards (the serial port can only serve one program at a time).
To have it run on boot without anyone logged in, run `sudo loginctl enable-linger pi` once.

## Notes

- The baud rate defaults to 921600, matching the firmware. Change it with the `UART_BAUD` command: the device replies at the old baud rate first, then switches to the new one. It reverts to 921600 after a reboot.
- USB and UART can be connected at the same time, but **only one controller program should be running at a time**. Commands from either side count as controller commands, and two programs drawing at once will overwrite each other.
- UART has no DTR/RTS, so opening or closing the serial port never resets the chip.
- The Zero 2 W has limited performance:
  - Measured showcase on the Zero 2 W: OLED about 120–160 fps, matrix about 120 fps; the bottleneck is Python rendering on the Pi.
  - At 921600 baud, a full OLED frame takes about 11ms.
