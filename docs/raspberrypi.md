# 树莓派作上位机（UART）

上位机不一定是电脑。树莓派用 GPIO 上的硬件串口接 ESP32 的 UART1，就能运行全部 Python 程序（`wwb` 命令行、`apps/`、showcase、maxdemo）。程序在电脑上写，用 `python -m wwb.remote` 通过 WiFi 推送到树莓派上运行。协议、命令、控制器接管流程和 USB 完全相同，只是端口换成 `/dev/serial0`。

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

## 安装（树莓派上只需要运行环境）

开发和测试都在电脑上做（可以先在网页模拟器里跑）。树莓派只负责运行：电脑把代码同步过去，它通过 UART 驱动设备。

```bash
# 树莓派上执行一次：Miniforge + 只含依赖的 conda 环境
curl -fsSL -o Miniforge3.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh
bash Miniforge3.sh -b -p ~/miniforge3 && rm Miniforge3.sh
~/miniforge3/bin/conda create -y -n wwb python=3.12 pyserial numpy pillow
```

电脑上配好 ssh 公钥登录（`ssh-copy-id pi@raspberrypi.local`）。另外建议关掉树莓派的 WiFi 省电，否则空闲一会儿后延迟会跳到几百毫秒：

```bash
sudo nmcli con modify <连接名> 802-11-wireless.powersave 2
```

## 使用（在电脑上执行）

```bash
conda activate esp32
python -m wwb.remote apps.stopwatch          # 同步 host/wwb 和 apps/，在树莓派上运行
python -m wwb.remote wwb.showcase --seconds 30
python -m wwb.remote wwb info                # 命令行也可以
python -m wwb.remote --sync                  # 只同步
```

- 第一次同步会传全部代码，以后 rsync 只传有改动的文件。
- 程序的输出实时显示在电脑上。
- Ctrl+C 会停止树莓派上的程序，程序照常发 `RELEASE` 交还设备。
- ssh 断开时，程序会收到 SIGHUP，同样正常退出。

`wwb.remote` 的配置都用环境变量：

| 变量 | 作用 | 默认值 |
|---|---|---|
| `WWB_REMOTE` | 目标机器 | `pi@raspberrypi.local` |
| `WWB_REMOTE_DIR` | 树莓派上的代码目录 | `~/wwb_timer` |
| `WWB_REMOTE_PYTHON` | 树莓派上的 Python | `~/miniforge3/envs/wwb/bin/python` |
| `WWB_REMOTE_PORT` | 树莓派上的串口 | `/dev/serial0` |

树莓派上运行时：
- `PYTHONPATH` 指向同步过去的 `host/`，不需要 `pip install`；
- `WWB_PORT` 设成串口，所有程序默认就用它。程序的 `--port` 默认值取自 `WWB_PORT`，没设时为 `/dev/ttyACM0`。

## 注意

- 波特率默认 921600，和固件一致。改波特率用 `UART_BAUD` 命令：设备先按旧波特率回复，再切到新波特率。重启后恢复 921600。
- USB 和 UART 可以同时连着，但**同一时间只应有一个控制器程序**在运行。两边的命令都算作控制器的命令，两个程序同时画屏会互相覆盖。
- UART 没有 DTR/RTS，打开或关闭串口都不会复位芯片。
- Zero 2 W 性能有限：
  - 实测 showcase 在 Zero 2 W 上 OLED 约 120–160 帧/s、点阵约 120 帧/s，瓶颈是树莓派上的 Python 渲染。
  - 921600 波特率下 OLED 整帧约 11ms。
