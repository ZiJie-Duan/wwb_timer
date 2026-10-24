# dao timer 场景制作指南

dao timer 是一个“游戏化的道家计时器”，运行在一块 ESP32-C3 小板上，由上位机（Python）驱动三块屏：

- **OLED 128×64 单色**：主画面，所有动画的主体。
- **8×8 红色点阵**：卦象、法器符号、简单动效。
- **4 位数码管**：引擎自己显示累计时间，场景不用管。

计时只认芯片：开关拨上 = 开始计时 = 开一场**法事**；拨下 = 停止 = 进入**歇**。
用户要求：画面要“非常整活”，把道教的整套文化（烧香、结印、作法、八卦、六爻、符箓、内丹、星斗……）融进去，
让每一次拨开关都有趣、充满未知感。**至少 50 种不同画面的法事、50 种不同画面的歇**，所以每个场景的画面必须明显不同，
不能只是换个字。

先读：`apps/dao/engine/scene.py`（阶段与参数的含义）、`apps/dao/rituals/r0_incense.py`（示范法事，质量标杆），
再浏览 `engine/gfx.py`、`engine/fx.py`、`engine/symbols.py`、`engine/anim.py`、`engine/cn.py` 里现成的工具。

## 场景结构

```python
from ..engine.anim import ease_out, span, ...
from ..engine.gfx import Gfx, Sprite
from ..engine.scene import Ritual, register

@register
class Talisman(Ritual):
    id = "r2.talisman"          # 全局唯一，前缀 = 你的批次
    name = "画符"                # 中文名（≤ 6 字）
    desc = "黄符展开，朱砂笔逐笔写出敕令，符文脉动，圆满时符纸自燃化灰"
    T = {"enter": 4.0, "interrupt": 1.5, "resume": 1.5, "complete": 4.5}
    CYCLE = 600.0               # 持续阶段一轮的秒数

    def setup(self): ...        # 用 self.rng 决定本场的变化（只在创建时调用一次）
    def enter(self, g, t): ...
    def hold(self, g, t, e): ...
    def interrupt(self, g, t, e): ...
    def resume(self, g, t, e): ...
    def complete(self, g, t, e): ...
```

- 每帧引擎先**清空** OLED 与点阵，再调用当前阶段方法画一整帧（立即模式）。t = 本阶段经过的秒数。
- **e = 本场法事累计计时秒数**（来自芯片，跨暂停累加，可以非常大，几天都可能）。
- 进度类的画面（香变短、炉火、月相……）**必须是 e 的函数**，这样断线重连、暂停恢复后能接上。
  t 只用于“氛围”运动（烟扭、火跳、闪烁）。
- **hold 要能无限持续**：一轮（CYCLE）结束后有一段“续”的过渡（像燃香的“吹走残香、再插一炷”），然后开始下一轮。
  轮数可以显示出来（第几炷、第几转、第几道符）。CYCLE 一般 300–1200 秒。
- **断线重连**：引擎可能不经 enter 直接调用 hold（e 任意）或 complete，场景不能依赖 enter 设置的状态。
  有状态的东西（Particles）要在 setup 里建好，或者在 hold 里惰性初始化。
- 同一个 seed 要画出同样的变化：随机只用 `self.rng`（setup 里）或 `anim.rand(i, seed)` / `noise`（确定性）。
  不要用全局 `random`。
- **阶段衔接**：enter 最后一帧 ≈ hold 第一帧；interrupt 从 hold 的样子开始，结束在“停下来”的样子；
  resume 结束 ≈ hold(e)；complete 从 hold 开始，收尾。不同场景之间引擎会自动做 0.35 秒抖动溶解。
- 开关可能在过渡中被拨回来：引擎会把当前过渡加速 3 倍播完再走新路线，场景不用处理。

### 法事（Ritual）五段

| 阶段 | 时长 | 内容 |
|---|---|---|
| enter 入场 | 2.5–5s | 开场动作：手插香、展符、起炉、请神…… |
| hold 持续 | 无限 | 随 e 推进的主体 + 氛围动效；每轮结束有“续”的过渡 |
| interrupt 中断 | 1–2s | 不满 10 分钟就停了：把这场法事“暂停”（掐香、合卷、压炉火），结束时静止 |
| resume 恢复 | 1–2.5s | 从暂停回到持续（重新点燃、展开……） |
| complete 圆满 | 3–6s | 满 10 分钟后停下：收尾的高潮（符燃尽、丹成、雷落、“功德圆满”） |

### 歇（Rest）三段

```python
@register
class Tea(Rest):
    id = "x2.tea"; name = "品茗"; desc = "..."
    T = {"enter": 2.5, "exit": 1.2}
    def enter(self, g, t): ...   # 2–4s
    def hold(self, g, t): ...    # t 无上限：循环的、安静的、耐看的画面（可能一歇就是一整夜）
    def exit(self, g, t): ...    # 1–1.5s，结束时画面基本清空或收拢
```

歇的气质：放松、留白、有趣的小细节（打盹的冒泡、茶烟、鱼咬钩），偶尔一个彩蛋（每隔几十秒发生一次的小事件）。
`self.ctx.finished` = 上一场是圆满结束的（可以更欢快），`self.ctx.ritual_name` = 刚才的法事名。

### 起卦（Omen）与特殊场景（Special）

`play(g, t)`，`T = {"play": 秒}`。起卦在 setup 里算出 `self.lines`（6 爻，6/7/8/9，见 symbols.py），
play 演出过程并在最后 1.5 秒左右展示结果（卦象、卦名 `full_name(lines)`、点阵 `mx_hexagram`）。

## 画面规范

- 128×64 很小：**主体要大、线条要干净**，宁可少而清楚。抖动灰度（`g.shade`、`g.shade_poly`）用来表现布料、山、云、烟雾的明暗。
- 中文用 `g.text(x, y, s, size=12)`（y 为字顶，字高 11）；8px 字（`size=8`）只适合数字、英文、两三个汉字。
  竖排 `g.vtext`。放大粗像素 `scale=2`。每帧最多一两行字，文字是点缀，**画面主要靠图形和动作**。
- 文字内容要地道：用真实的道教术语、咒语片段、典籍原文（《道德经》《庄子》《黄庭经》《清静经》、
  常见咒语如净心神咒、金光神咒的句子、“急急如律令”“敕令”等），**不要编造伪经文**。
- 点阵每个场景都要用起来（持续阶段不能长时间全灭）：法器图标、卦、动效。亮度 `g.mx_level` 平时 1，
  高潮瞬间可到 4–8，不要长时间高亮。
- 动作要有“演出感”：缓动（ease_out_back 弹出、ease_out_bounce 落地）、预备动作、余韵、粒子、闪光。
  参考燃香：手从画外伸进来、插香扬灰、火柴依次点燃、烟三向飘散、风吹残香。
- 现成工具：烟 `smoke_wisp`、火 `flame`、粒子 `Particles`、闪电 `lightning`、点圆 `ring`、星空 `stars`、雨 `rain`、
  云 `cloud`、祥云 `xiangyun`、逐字 `typewriter`、毛笔书写 `brush_reveal`、太极 `taiji`/`mx_taiji`、
  卦 `draw_hexagram`/`mx_hexagram`、八卦盘 `bagua_ring`、像素画 `Sprite`（`#` 亮 `.` 暗 空格透明）、
  数字 `cn_num`、干支时辰 `cn.py`。需要新的通用工具就写在**你自己的文件里**（不要改 engine/ 和别人的文件）。

- `g.text` 会缓存渲染好的字串；`g.d` 画矩形/椭圆时坐标反了会自动纠正；`fade`/`shade`/`shade_poly`/`invert` 只处理给定区域。
- 歇的 `exit` 可以读 `self.hold_t`（持续阶段最后一帧的 t），从那一帧接着收场。
- 共用零件放在 `<前缀>_common.py` 一类文件里（不登记场景也没关系，load_all 会照常导入）。
- `Sprite.flip()`/`rot90()`/`scale()` 每次都新建图像，请在模块级预先生成，不要每帧调用。
- 12px 字库没有“炁”，用“气”或手绘。

## 性能（重要）

最终跑在树莓派 Zero 2 W 上，比电脑慢 6–8 倍，要 30 帧/秒。**电脑上每帧中位 ≤ 3ms、最大 ≤ 15ms**（check 会报）。
少做整屏 numpy 运算（`g.fade`/`shade`/`array`/`put` 每次都整屏转换，一帧里别调用太多次），粒子几十个以内。

## 文件与验证

- 只在分配给你的文件里工作：`apps/dao/<rituals|rests|omens|special>/<前缀>_*.py`，一个文件可以放多个场景。
  另外写目录 `apps/dao/catalog/<前缀>.md`。**不要改** engine/、tools/、别人的文件，不要 git commit。
- 在仓库根目录 `~/wwb_timer` 下、conda 环境 esp32 里运行：

```bash
conda run -n esp32 python -m apps.dao.tools.check --prefix r2.       # 你的全部场景：异常、耗时、缺字、衔接
conda run -n esp32 python -m apps.dao.tools.preview r2.talisman --out /tmp/claude-…/scratchpad/pv
```

  预览图（PNG 联系表）**一定要用 Read 打开看**，逐个阶段检查：主体是否清楚、动作是否连贯、衔接是否跳变、
  文字是否被裁掉、点阵是否有内容。看完再改，直到满意。别的批次的文件导入失败（正在写）可以忽略。
- 字体缺字 check 会报错（GBK 字库，个别生僻字没有），换字或用图形代替。
- 不要启动模拟器、不要碰设备、不要用 pkill/killall。

## 目录（catalog）

`apps/dao/catalog/<前缀>.md`：本批每个场景一节：

```markdown
## r2.talisman 画符
- 依据：符箓派，敕令符的结构（符头三清讳、符胆、符脚）……（出处/来源链接）
- 入场：……
- 持续：……（一轮多久，续的过渡是什么）
- 中断 / 恢复 / 圆满：……
- 点阵：……
```
