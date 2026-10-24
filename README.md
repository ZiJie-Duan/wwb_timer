# wwb_timer

ESP32-C3 驱动的交互设备：1 个开关 + 0.96 寸 OLED + TM1637 四位数码管 + MAX7219 8×8 点阵。

项目分两条线：

1. **设备 API**：ESP32-C3 作为驱动器，把四个器件封装成一套高速二进制串口协议，USB 和 UART 两条通道共用。上位机（“控制器”）通过它扩展和控制设备。
2. **脱机计时器 wwb timer**：没有控制器时芯片自己运行的程序。开关拨上计时、拨下停止，时间累计断电保留，每次开关在点阵上多亮一个点；插上控制器就交给控制器，拔掉再回来。C++ 写成，同一份源码编进固件、也编成 WebAssembly 在网页模拟器里运行。见 [docs/offline.md](docs/offline.md)。

## 目录

```
firmware/            ESP32-C3 固件（PlatformIO + Arduino 3.3 / ESP-IDF 5.5）
  src/board.h        引脚分配
  src/proto.*        帧格式、操作码、COBS/CRC
  src/transport.*    USB-Serial/JTAG 与 UART1 收发层
  src/oled.*         SSD1306：帧缓冲 + 脏矩形 + 推送任务
  src/seg.*          TM1637：定时器中断驱动时序，只写变化的位
  src/matrix.*       MAX7219：硬件 SPI，旋转换算，只写变化的行
  src/io.*           开关 / BOOT 键（中断时间戳）+ 板载灯
  src/main.cpp       命令分发、INFO/STATS、设备端自测
  src/offline.*      脱机程序在芯片上的运行环境（控制器接管、NVS 存储）
native/              脱机程序（C++，芯片与网页共用）
  wwb/               框架：Device、Canvas（u8g2）、App、Runtime
  timer/             wwb timer
  web/, build_web.py 编译成 WebAssembly（web/js/native.js）
host/wwb/            上位机 Python 库
  device.py          Device 类：所有命令的 API
  protocol.py        协议常量与编解码
  bench.py           性能极限测试
  maxdemo.py         三屏同时全速演示
  showcase.py        赛博风多场景演示：开机自检、星空跃迁、四维超立方体、代码雨、等离子、频谱、故障标志
  visual.py          目测验证（时钟档位）
  cli.py             命令行
  sim.py             网页模拟器的 Python 桥：程序启停、自动重启、协议转发
  app.py             程序入口 run(main)
apps/                程序，每个一个包（stopwatch：秒表）
web/                 网页模拟器：三块屏 + 开关 + 程序列表
docs/
  hardware.md        器件、接线、供电、实测结论
  protocol.md        协议规范
  benchmarks.md      性能极限实测
  simulator.md       网页模拟器
  offline.md         脱机程序与 wwb timer
  raspberrypi.md     树莓派作上位机（GPIO 串口接 UART）
results/             跑分原始数据（JSON）
```

## 快速开始

```bash
conda activate esp32
cd ~/wwb_timer/firmware && pio run -t upload        # 编译并烧录
pip install -e ~/wwb_timer/host                      # 已装过可跳过

python -m wwb info                   # 设备信息
python -m wwb text "你好" -f 5       # OLED 写中文
python -m wwb seg 12:34              # 数码管
python -m wwb events                 # 实时打印开关事件
python -m wwb.bench                  # 跑全部性能测试
python -m wwb.maxdemo                # 三屏同时全速演示，实时显示各屏刷新率
python -m wwb.maxdemo --rate 320     # 数码管、点阵限速 320 帧/s（点阵指针一秒一圈）
python -m wwb.showcase               # 赛博风多场景演示（拨开关切场景，按 BOOT 反色）
```

## 网页模拟器（不接设备）

```bash
python -m wwb.sim                    # 打开 http://127.0.0.1:8765，在右侧选程序运行，拨开关试交互
```

没有程序运行时，网页里跑的是芯片上同一份脱机计时器（WebAssembly）；运行一个 Python 程序 = 插入控制器。
模拟器按固件逐条执行协议命令，并模拟真机的刷新时序（OLED 约 95fps、数码管只写变化的位、20ms 消抖），实测刷新数与真机误差在 1% 左右。
程序放在 `apps/<名字>/`（Python 包，入口用 `wwb.app.run(main)`），会自动出现在网页列表里，改了文件自动重启。
同一个程序加 `--port sim` 跑在模拟器上，去掉就跑在真机上。详见 [docs/simulator.md](docs/simulator.md)。

## 树莓派作上位机

树莓派的 GPIO14/15 接 ESP32 的 GPIO20/21（UART1，921600），设 `WWB_PORT=/dev/serial0` 后所有程序照常运行。见 [docs/raspberrypi.md](docs/raspberrypi.md)。

## 关键数字

| | 极限 |
|---|---|
| USB 往返 | 0.28 ms |
| OLED 整帧 / 局部 | 95 fps / 236 fps（4×96 区域） |
| 数码管 | 390 次/s 整屏，800 次/s 单位 |
| 点阵 | 约 2.7 万帧/s（批量发送） |
| 三屏同时全速 | OLED 91 fps + 数码管 666/s + 点阵 14730/s |
| 三屏同时、限速 320 | OLED 96 fps + 数码管 319.7/s + 点阵 319.7/s，零丢帧 |
| 开关事件时间戳 | µs 级（取抖动开始时刻） |

详见 [docs/benchmarks.md](docs/benchmarks.md)。

## 注意

- 开发板只用 USB 供电；外部 5V 只给模块，**不要接开发板 5V 引脚**，所有 GND 相连。见 [docs/hardware.md](docs/hardware.md)。
- 打开 `/dev/ttyACM0` 时要保持 DTR、RTS 同为有效，并关闭 HUPCL，否则会复位芯片。`wwb.Device` 已处理。

## 许可证

[MIT](LICENSE)
