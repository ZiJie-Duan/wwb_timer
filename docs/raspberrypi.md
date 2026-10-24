# 树莓派作上位机（UART）

上位机不一定是电脑。树莓派用 GPIO 上的硬件串口接 ESP32 的 UART1，就能运行全部 Python 程序（`wwb` 命令行、`apps/`、showcase、maxdemo）。协议、命令、控制器接管流程和 USB 完全相同，只是端口换成 `/dev/serial0`。

实测用的是 Raspberry Pi Zero 2 W（Debian 13 trixie，aarch64）。

## 接线

| 树莓派 | | ESP32-C3 |
|---|---|---|
| GPIO14 TXD（物理脚 8） | → | GPIO20（UART1 RX） |
| GPIO15 RXD（物理脚 10） | ← | GPIO21（UART1 TX） |
| GND（物理脚 6） | — | GND |

两边都是 3.3V 电平，可以直连。开发板仍用 USB 供电（见 [hardware.md](hardware.md)），**两边必须共地**。

## 树莓派系统设置

`/boot/firmware/config.txt` 末尾加：

```
enable_uart=1
dtoverlay=miniuart-bt
```

`/boot/firmware/cmdline.txt` 里删掉 `console=serial0,115200`，否则内核和登录终端会占用这个串口。然后重启。重启后 `/dev/serial0 → ttyAMA0`。

`miniuart-bt` 把 PL011 硬件串口换到 GPIO14/15，蓝牙改用 mini UART。不用 mini UART 有两个原因：

- 它的波特率跟着 GPU 核心时钟走；
- 它的 FIFO 很小，921600 波特率下容易丢字节。

如果用不到蓝牙，也可以改用 `dtoverlay=disable-bt`。用户 `pi` 默认在 `dialout` 组，不需要 sudo 就能打开串口。

## 安装

```bash
# Miniforge（conda）
curl -fsSL -o Miniforge3.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3.sh -b -p ~/miniforge3 && rm Miniforge3.sh
~/miniforge3/bin/conda init bash && exec bash

git clone https://github.com/ZiJie-Duan/wwb_timer.git ~/wwb_timer
conda create -y -n wwb python=3.12 numpy pillow pyserial websockets
conda activate wwb
pip install -e ~/wwb_timer/host
conda env config vars set WWB_PORT=/dev/serial0   # 所有程序默认用这个串口
conda deactivate && conda activate wwb
```

所有程序的 `--port` 默认值都取自环境变量 `WWB_PORT`；没设时默认 `/dev/ttyACM0`（USB）。

## 使用

```bash
conda activate wwb
python -m wwb info                   # 设备信息（约 4 秒后设备确认控制器接入）
python -m wwb text "你好" -f 5
python -m wwb.showcase               # 赛博风演示
python -m apps.stopwatch             # 在 ~/wwb_timer 下运行
```

在 Python 里用 `Device("/dev/serial0")`，或者不传端口直接 `Device()`，效果相同。

## 注意

- 波特率默认 921600，和固件一致。改波特率用 `UART_BAUD` 命令：设备先按旧波特率回复，再切到新波特率。重启后恢复 921600。
- USB 和 UART 可以同时连着，但**同一时间只应有一个控制器程序**在运行。两边的命令都算作控制器的命令，两个程序同时画屏会互相覆盖。
- UART 没有 DTR/RTS，打开或关闭串口都不会复位芯片。
- Zero 2 W 性能有限：
  - 三屏全速的 maxdemo 帧率会比电脑低，瓶颈在树莓派的 Python。
  - 921600 波特率下 OLED 整帧约 11ms。
