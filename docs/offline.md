# 脱机程序与 wwb timer

设备有两种状态：

- **脱机**：没有控制器时，芯片里的脱机程序驱动外设。现在的脱机程序是计时器 wwb timer（`native/timer/`）。
- **控制器接管**：上位机程序（Python，`wwb.Device`）连上后，命令要**持续 3 秒**才确认连接（防止接触不良时反复连上断开），播完连接动画后设备交给它。程序退出（发 `RELEASE`）或 1.5 秒没有任何命令，就算控制器拔出，脱机程序播放断开动画后恢复显示。**一个程序就是一次连接**：程序结束，连接就结束，即使串口还插着。

脱机程序是 C++，**同一份源码编译两次**：编进固件在芯片上运行（原生性能，不经过串口），编成 WebAssembly 在网页模拟器里运行。所以在网页上看到的就是芯片上的效果。

## wwb timer

| 操作 | 效果 |
|---|---|
| 开关拨上 | 开始计时。点阵：三个箭头冲上去，全部出画面后已有的点依次快速亮起。OLED：旧画面消散，大 ▶ 弹出、一圈波纹扩散，▶ 缩小飞进状态栏，“计时中”逐字打出，两位秒数依次从下面滑入，进度条从中间展开。数码管亮一下 |
| 开关拨下 | 停止。点阵：三个箭头落下，已有的点依次亮起，新的一个点掉进自己的格子、闪两下。OLED：大 ‖ 从上面落下、一圈波纹向里收拢，‖ 飞进状态栏，秒数从上面滑入；新点落地时次数往上滚一格，飘出“+1” |
| 停止时 | 数码管常亮；OLED 上的秒数和进度条缓慢呼吸闪烁（亮 1.8s → 渐暗 → 灭 0.4s → 渐亮） |
| 计时时 | 数码管冒号每秒闪一次；点阵上“下一个格子”跟着闪 |
| 开关在**下面**时开机 | 接着上次的累计时间 |
| 开关在**上面**时开机 | 清零（时间和点数），清零提示后直接开始计时 |

- **数码管**：`时:分`，不足 10 小时首位空白；100 小时起显示 `123h`，1000 小时起只显示小时数（这块数码管只有中间的冒号，没有小数点）。
- **OLED**：状态（计时中 / 已停止）、第几次、**秒**（时、分在数码管上），换秒时变了的那一位往上滚；底部是**一分钟进度条**（每 15 秒一个刻度）。
- **点阵**：每完成一次“开 → 关”，从左上角起多亮一个点，按行排，最多 64 个；常态亮度 1（最低档之上一档）。
- **开机**：老显示器式开机动画，亮出标题“wwb timer”。之后提示“插入控制器 / 解锁更多功能”：OLED 和点阵上插头滑进插座。每隔 10 秒重复，直到第一次拨开关或接入控制器为止；之后再也不提示，直到下次开机。
- **控制器连接**（OLED 与点阵都是插头动画）：
  - 连接中（3 秒）：插头慢慢靠近插座，插座的灯慢闪，“正在连接控制器…”加 3 秒进度条。
  - 确认：插头“咔”地插进去，火花、点阵闪一下，“控制器已连接”，数据沿线流进去，1.2 秒后淡出、交给控制器。
  - 连接中断（3 秒内断了）：插头退回去，“连接中断”，回到计时画面。
  - 断开：插头被拔出、退走，“控制器已断开”，再播一次开机的标题动画“wwb timer”，回到计时画面。
- **控制器接管期间**计时照常按开关进行（画面不显示），开关事件同时上报给控制器。
- **断电保留**：芯片存在 NVS 里（计时中每 30 秒存一次，开关拨动时立即存），网页存在 localStorage。板子没有时钟电池，断电期间不计时；计时中突然断电，最多丢最后 30 秒。

## 怎么写脱机程序

```
native/
  wwb/wwb.h, wwb.cpp   框架：Device（输出带缓存，只发变化）、Canvas（u8g2 画布）、App、Runtime（控制器接管）
  timer/timer.cpp      wwb timer
  web/main.cpp         WebAssembly 的运行环境（命令交给模拟器）
  build_web.py         编译成 web/js/native.js
firmware/src/offline.* 芯片上的运行环境（命令直接交给 execute()，存储用 NVS，约 60 帧/秒的任务）
```

程序实现 `wwb::App`，并提供 `wwb::createApp()`：

```cpp
class MyApp : public wwb::App {
  void setup(Device &d, uint64_t now) override;                      // 开机；d.input(SWITCH) 为开机时的开关状态
  void input(Device &d, Input in, bool active, uint64_t t) override;  // 开关 / BOOT 变化，t 为变化时刻 µs
  void controller(Device &d, bool attached, uint64_t now) override;  // 控制器接入 / 断开
  void frame(Device &d, uint64_t now) override;                      // 约 60 次/秒，接管期间也调用（d.visible() 为 false）
  size_t report(uint64_t now, uint8_t *out, size_t cap) override;    // 可选：给控制器的状态（协议 APP_STATE）
};
wwb::App *wwb::createApp() { return new MyApp(); }
```

- **OLED**：在 `Canvas` 上用 u8g2 的 C 接口画（`u8g2_DrawStr(c.u(), …)`，字体用 `u8g2_font_*`），然后 `d.oled(canvas)`；只发变化的区域（`OLED_BLIT`）。`fade()` 做有序抖动淡入淡出，`invert()` 反色。
- **数码管**：`d.seg(段码[4])`、`d.segConfig(亮度, 开/关)`；`wwb::segDigit()` 给数字段码。
- **点阵**：`d.mx(行[8])`（行 0 在上，bit7 在左）、`d.mxIntensity(0-15)`。
- **存储**：`d.load()` / `d.save()`，一小块二进制。
- **上报**：`report()` 返回给控制器的状态，状态变了调 `d.changed()`，订阅了的控制器会收到 `APP_STATE` 事件。wwb timer 上报计时状态（格式见 [protocol.md](protocol.md)），控制器程序（如 dao timer）据此表演，时间始终以芯片为准。
- 时间都是设备的 µs 时钟（与输入事件同一时钟）。不要用 `millis()` 之类平台函数，也不要用全局状态，模拟器重启设备时会重新 `createApp()`。

换程序：改 `firmware/platformio.ini` 的 `build_src_filter` 和 `native/build_web.py` 的参数。

## 编译

```bash
# 芯片
conda activate esp32
cd firmware && pio run -t upload

# 网页（生成 web/js/native.js，单文件，内嵌 wasm）
conda run -n emsdk python native/build_web.py
```

`emsdk` 环境：`conda create -n emsdk -c conda-forge emscripten=4.0.9`。conda-forge 的这个包带的 binaryen 是 117，而 emcc 4.0.9 需要 123，要从 [binaryen 发布页](https://github.com/WebAssembly/binaryen/releases/tag/version_123) 下载 `binaryen-version_123-x86_64-linux.tar.gz`，把 `bin/`、`lib/` 拷进环境覆盖。

## 控制器协议

```
脱机 ──任何命令──▶ 连接中 ──命令持续 3s（间隔都不超过 1s）──▶ 已确认（连接动画 1.2s）──▶ 接管
          ▲          │ 间隔超过 1s 或 RELEASE                    │ 同左                      │ RELEASE 或 1.5s 没有命令
          └──────────┴─────────────── 连接中断 ◀────────────────┘                           ▼
          └──────────────────────────────────────────────────────────────────────────── 断开（断开动画）
```

- 接管之前，控制器只能用不碰外设的命令（PING、INFO、TIME、STATS、IO_READ、SUBSCRIBE、CONNECT…）；显示类（0x2_/0x3_/0x4_）、LED、IO_CONFIG、BENCH 回 `NOT_READY`（5）。
- `CONNECT`（0x0D）查询连接状态：回 `u8 状态`（0 脱机 / 1 连接中 / 2 已接管）、`u32 距离接管还有多少 ms`。
- 进入接管时外设先恢复开机默认：OLED 清屏、正常显示、对比度 0xCF；数码管亮度 3、清空；点阵亮度 1、旋转 1、10MHz、清空；消抖 20ms。交还时同样恢复默认，脱机程序重新画全部内容。
- `wwb.Device` 打开时轮询 `CONNECT`，等到已接管才返回（约 4.2 秒，`connect=False` 可跳过）；空闲时每 0.5 秒发一次 `PING` 保持控制；`close()` 时发 `RELEASE`。状态机在 `native/wwb/wwb.cpp` 的 `Runtime` 里，芯片和网页共用。
