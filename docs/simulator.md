# 网页模拟器

`web/` 是一个在浏览器里模拟整台设备的网页：OLED、数码管、点阵、开关、BOOT 键、板载灯。用来设计动画和交互细节，不用接真机。

模拟器在网页里**按固件逐条执行协议命令**（`web/js/emulator.js` 对照 `firmware/src/main.cpp` 的 `execute()` 写成），所以发给它的帧和发给真机的帧完全相同，报错也相同（比如宽度为 0 的 `OLED_RECT` 一样会回 `BAD_ARG`）。

## 两种用法

### 1. 网页脚本（不需要 Python）

打开页面，在右侧编辑器写脚本，Ctrl+Enter 运行，Esc 停止。脚本是一个 async 函数体，`dev` 的方法与 Python `wwb.Device` 同名同参，关键字参数写成最后的 `{…}`：

```js
dev.oled_clear();
dev.oled_text(0, 40, "12:34", Font.LOGISOSO24_NUM, 1, { flush: true });
dev.seg_text("12:34");
dev.mx_frame(mx("...##...", "..####..", ".######.", "##.##.##", "...##...", "...##...", "...##...", "...##..."));
dev.on_input(ev => log(ev.name, ev.active, ev.t_us));

const tick = pacer(100);          // 按 100 帧/s 等待
const g = canvas();               // 128×64 Canvas 2D，画完 dev.oled_frame(g)
while (true) { /* … */ await tick(); }
```

其他可用的：`sleep(ms)`、`frame()`（等下一个显示帧）、`now()`（秒）、`segText(s)`、`toFrame(画布)`、`Font`、`Op`、`Flag`、`log(...)`。编辑器里有几个示例（秒表、弹球、字体、点阵动画），内容自动保存在浏览器里。

页面可以直接双击 `web/index.html` 打开，也可以由下面的桥提供。

### 2. Python 程序

```bash
python -m wwb.sim                          # 终端 1：启动桥，浏览器打开 http://127.0.0.1:8765
python -m wwb.showcase --port sim          # 终端 2：任何 wwb 程序加 --port sim
```

```python
from wwb import Device
with Device("sim") as d:                   # 与 Device("/dev/ttyACM0") 用法完全相同
    d.seg_text("12:34")
```

```
Python 程序 ──TCP 8766──▶ wwb.sim ──WebSocket /ws──▶ 网页里的模拟设备
            ◀──────── 回复 / 开关事件 ─────────────
```

- 桥只转发字节，不解析命令；程序到网页方向按 USB 实测上行速度（460 KiB/s）限速，`--no-limit` 关闭。
- 网页没打开时，桥暂停读取，程序的写入会阻塞、请求会超时；打开网页后自动继续。
- Python 程序连上时，网页脚本会自动停止，免得两边同时画。
- 新打开的页面会接管设备，旧页面断开。
- `--host 0.0.0.0` 可让局域网里的手机、平板打开网页（同时也开放了 TCP 端口）。

## 模拟了什么

| 部分 | 模拟方式 | 与真机对比 |
|---|---|---|
| OLED 文字 | u8g2 字体解码移植到 JS，字体数据从 U8g2 源码提取（`web/tools/gen_fonts.py`），逐像素与真机一致 | — |
| OLED 推送 | 帧缓冲 + 脏矩形 + 推送任务，推送耗时 200µs + 10.1µs/字节；推送期间的新绘制合并到下一次 | `maxdemo --rate 320`：真机 95.7 fps，模拟 94.8 |
| OLED 命令 | 反色 A6/A7、开关显示 AE/AF、全亮 A4/A5、对比度 81、翻转 A0/A1 C0/C8、起始行 40–7F、偏移 D3 | 1.1MHz 以上的 `OLED_CONFIG` 回 `HW` 错误（真机会超时或花屏） |
| 数码管 | 只写变化的位，每次传输 370µs + 440µs/字节（随上升/下降时间缩放）；只保留最新内容；亮度 8 档 | 真机 319.7/s，模拟 318.9/s；showcase 各场景的刷新数与真机日志一致 |
| 点阵 | 旋转、只写变化的行、每秒补发配置（会覆盖 `MX_RAW` 写的行）、亮度 16 档、显示测试、关断 | 真机 319.7/s，模拟 319.7/s |
| 输入 | 网页上拨开关 / 按 BOOT = 引脚电平变化；20ms 消抖后上报，时间戳取变化开始时刻 | 快捷键：S / 空格 = 开关，按住 B = BOOT |
| 其他命令 | PING、INFO（带 `"sim": true`）、STATS（字段与真机相同）、TIME、SUBSCRIBE、IO_READ、LED、SINK、SOURCE、REBOOT | `BENCH` 按时序模型给估算值；`UART_BAUD` 只回复不生效 |

## 限制

- 浏览器只能按显示器刷新率（通常 60Hz）显示画面，OLED 内部按约 95fps 推送，但你看到的是每 1/60 秒的最新画面。
- 不模拟真机的硬件故障：时序设得太快导致的数码管乱码、I²C 花屏、模块掉电等。
- 页面在后台标签时浏览器会降低定时器频率，网页脚本会变慢；Python 程序驱动时不受影响（命令到达时就推进模拟）。

## 文件

```
web/index.html, style.css
web/js/proto.js       协议：COBS、CRC、帧编解码
web/js/u8g2.js        u8g2 字体解码与绘图
web/js/fonts.js       字体数据（生成文件）
web/js/emulator.js    设备模拟：命令处理 + 各外设时序
web/js/client.js      网页脚本用的 Device API
web/js/view.js        三块屏的画面
web/js/examples.js    示例脚本
web/js/app.js         页面逻辑、Python 桥连接、脚本运行
web/tools/gen_fonts.py  重新生成 fonts.js（固件换字体时）
host/wwb/sim.py       Python 桥
```
