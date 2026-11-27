# Changelog

English · [简体中文](#更新记录)

## Unreleased

- All docs are bilingual, English first (`*.md`), Chinese in `*.zh-CN.md`; English wiring diagram.
- README: roomier "What it does" layout.

## v0.2.0 (2026-11-27)

First public release: build documentation, plus the offline timer and dao timer.

**Build docs**
- New [build guide](docs/build.md): BOM, wiring diagram, desk / battery power, enclosure, assembly, flashing, troubleshooting. The simplified wiring needs no level shifter.
- Enclosure Fusion 360 source in `hardware/enclosure/`.
- README with photos, demo GIF and dao timer scenes.
- Releases ship a merged firmware image, flashed at address 0 with esptool or from the browser.

**Firmware and programs**
- Offline timer wwb timer: written in C++, compiled into the firmware and to WebAssembly; switch timing, persistent across power loss, session dots on the matrix, controller connect / disconnect animations.
- Controller takeover: commands must continue for 3 s to confirm a connection; 1.5 s without commands means unplugged; the device is handed back when a program exits.
- Raspberry Pi as a UART controller (`wwb.remote`, autostart service `wwbctl`).
- dao timer: Taoist cyber timer with 55 rituals, 54 rests and 9 omens in 1-bit pixel art; reconnects after link loss, retries saves.
- Web simulator: three displays + switch + program list; opened on its own it is an online demo running only the offline timer.

**Host**
- Serial port auto-detection (`WWB_PORT` → `/dev/ttyACM0` → Espressif USB serial), no manual port on macOS or Windows.
- HUPCL also disabled on macOS so closing the port does not reset the chip.
- `platformio.ini` no longer pins the upload port.

## v0.1.0 (2026-10-24)

- ESP32-C3 device API: binary serial protocol for the OLED, TM1637, MAX7219 and switch, shared by USB and UART.
- Measured performance limits (`docs/benchmarks.md`).

---

# 更新记录

## 未发布

- 文档改为中英双语、英文优先（`*.md` 是英文，`*.zh-CN.md` 是中文）；接线图出了英文版。
- README“它能做什么”一节排版放宽。

## v0.2.0（2026-11-27）

第一个公开发布的版本：补齐复刻资料，固件加上脱机计时器和 dao timer。

**复刻资料**
- 新增[复刻指南](docs/build.md)：物料清单、接线图、桌面版 / 电池版供电、外壳、组装、刷固件、排错。简化接法不需要电平转换。
- 外壳 Fusion 360 源文件放进 `hardware/enclosure/`。
- README 加上成品照片、演示动图、dao timer 场景图。
- Release 附带合并好的固件镜像，用 esptool 或浏览器从地址 0 写入即可。

**固件与程序**
- 脱机计时器 wwb timer：C++ 写成，同一份源码编进固件、也编成 WebAssembly；开关计时、断电保存、点阵记次，控制器接入 / 断开动画。
- 控制器接管：命令持续 3 秒确认连接，1.5 秒无命令视为拔出；程序退出时交还设备。
- 树莓派通过 UART 作控制器（`wwb.remote`、开机自启服务 `wwbctl`）。
- dao timer：道家赛博计时器，55 种法事、54 种歇、9 种起卦，全部是 1 位像素风；断线重连、存档重试。
- 网页模拟器：三块屏 + 开关 + 程序列表；单独打开时作为在线演示，只运行脱机计时器。

**上位机**
- 默认串口自动识别（`WWB_PORT` → `/dev/ttyACM0` → 乐鑫 USB 串口），macOS、Windows 不用手动指定。
- macOS 上同样关闭 HUPCL，关闭串口时不复位芯片。
- `platformio.ini` 不再写死上传串口。

## v0.1.0（2026-10-24）

- ESP32-C3 设备 API：OLED、TM1637、MAX7219、开关的二进制串口协议，USB 与 UART 共用。
- 性能极限实测（`docs/benchmarks.md`）。
