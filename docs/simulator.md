# 网页模拟器

`web/` 是一个在浏览器里模拟整台设备的网页：OLED、数码管、点阵、开关、BOOT 键、板载灯。用途是**看程序效果、试交互**，不用接真机。网页只负责显示、拨开关，以及选择要运行的程序。

有两种程序：

- **脱机程序**（C++，`native/`）：芯片里自己运行的程序，现在是计时器 wwb timer。网页里跑的是同一份源码编成的 WebAssembly（`web/js/native.js`），没有 Python 程序运行时就由它显示。见 [offline.md](offline.md)。
- **控制器程序**（Python，`apps/`）：通过协议控制设备。在网页上运行一个 = 插入控制器，它接管设备；停止 = 拔出，脱机程序播放断开动画后回来。顶栏显示当前是“脱机程序运行中”还是“控制器接管中”。

模拟器在网页里**按固件逐条执行协议命令**（`web/js/emulator.js` 对照 `firmware/src/main.cpp` 的 `execute()` 写成），所以程序发给它的帧和发给真机的完全相同，报错也相同（比如宽度为 0 的 `OLED_RECT` 一样会回 `BAD_ARG`）。同一个程序把 `--port sim` 换成 `/dev/ttyACM0` 就能在真机上跑。

## 用法

```bash
python -m wwb.sim          # 浏览器打开 http://127.0.0.1:8765
```

网页右侧是程序列表，点 ▶ 运行，桥就以 `python -m <程序> --port sim:…` 启动它，程序的输出显示在“输出”面板。开关：点击或按 S / 空格；BOOT：按住或按住 B。

- **改动后自动重启**（默认开）：程序目录或 `host/wwb/` 里的文件一改，正在看的程序就重新运行。
- **运行 = 连接，停止 = 断开**：程序连上后约 3 秒确认、播完连接动画才开始显示；停止时播放断开动画。
- **刷新网页 / 点“重启设备” = 断电再上电**：脱机程序从头运行；网页关闭时 Python 程序暂停，网页回来后从头运行。开关位置和计时数据存在浏览器里，刷新后保留（开关拨在上面时开机 = 计时清零）。
- 也可以在终端自己运行程序，加 `--port sim` 即可（例如 `python -m wwb.showcase --port sim`）。

## 程序怎么写

每个程序是 `apps/` 下一个带 `__main__.py` 的包，可以有多个模块和任意数据文件（图片、JSON…），按普通 Python 项目组织：

```
apps/stopwatch/
  __init__.py      文档字符串：第一行是标题，其余是说明（显示在网页的程序列表里）
  __main__.py      入口
  ...              其他模块、素材
```

```python
# apps/stopwatch/__main__.py
from wwb import Font
from wwb.app import run

def main(d):                       # d 是 wwb.Device
    d.on_input(lambda ev: print(ev.name, ev.active, ev.t_us))
    while True:
        d.oled_clear(wait=False)
        d.oled_text(0, 40, "12:34", Font.LOGISOSO24_NUM, flush=True, wait=False)
        ...

run(main)                          # 解析 --port，打开设备；Ctrl+C / 停止时正常退出
```

新建的程序目录会自动出现在网页的列表里。wwb 自带的 `showcase`、`maxdemo` 也在列表中。

## 连接方式

```
Python 程序 ──TCP 8766──▶ wwb.sim ──WebSocket /ws──▶ 网页里的模拟设备
            ◀──────── 回复 / 开关事件 ─────────────
```

- 桥只转发字节，不解析命令；程序到网页方向按 USB 实测上行速度（460 KiB/s）限速，`--no-limit` 关闭。
- 新打开的页面会接管设备，旧页面断开。
- `--host 0.0.0.0` 可让局域网里的手机、平板打开网页（同时也开放了 TCP 端口）。
- 直接双击 `web/index.html` 也能打开模拟器，但没有桥就不能运行程序。

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

## 文件

```
web/index.html, style.css
web/js/proto.js       协议：COBS、CRC、帧编解码
web/js/u8g2.js        u8g2 字体解码与绘图
web/js/fonts.js       字体数据（生成文件）
web/js/emulator.js    设备模拟：命令处理 + 各外设时序
web/js/view.js        三块屏的画面
web/js/offline.js     脱机程序的运行环境（控制器接管、localStorage 存储）
web/js/native.js      脱机程序（native/build_web.py 生成）
web/js/app.js         页面逻辑、程序列表、Python 桥连接
web/tools/gen_fonts.py  重新生成 fonts.js（固件换字体时）
host/wwb/sim.py       Python 桥：网页服务、协议转发、程序启停与自动重启
host/wwb/app.py       程序入口 run(main)
apps/                 程序（每个一个包）
```
