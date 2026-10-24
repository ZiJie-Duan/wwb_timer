# wwb_timer

ESP32-C3 驱动的交互设备：1 个开关 + 0.96 寸 OLED + TM1637 四位数码管 + MAX7219 8×8 点阵。

项目分两条线：

1. **设备 API**（本阶段）：ESP32-C3 作为驱动器，把四个器件封装成一套高速二进制串口协议，USB 和 UART 两条通道共用。上位机通过它扩展和控制设备。
2. **计时器程序**（待定）：基于上面这套 API 实现。

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
host/wwb/            上位机 Python 库
  device.py          Device 类：所有命令的 API
  protocol.py        协议常量与编解码
  bench.py           性能极限测试
  maxdemo.py         三屏同时全速演示
  visual.py          目测验证（时钟档位）
  cli.py             命令行
docs/
  hardware.md        器件、接线、供电、实测结论
  protocol.md        协议规范
  benchmarks.md      性能极限实测
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
```

```python
from wwb import Device, Font

with Device("/dev/ttyACM0") as d:                 # UART：Device("/dev/ttyUSB0", baud=921600)
    d.oled_clear()
    d.oled_text(0, 40, "12:34.56", Font.LOGISOSO24_NUM, flush=True)
    d.seg_text("12:34")
    d.mx_frame(bytes([0x18, 0x3C, 0x7E, 0xDB, 0x18, 0x18, 0x18, 0x18]))
    d.on_input(lambda ev: print(ev.name, ev.active, ev.t_us))
```

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
