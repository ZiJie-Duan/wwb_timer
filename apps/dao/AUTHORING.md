# dao timer 场景制作指南（像素风）

dao timer 是一个“游戏化的道家计时器”，运行在一块 ESP32-C3 小板上，由上位机（Python）驱动三块屏：

- **OLED 128×64 单色**：主画面。
- **8×8 点阵**：图标、卦象、小动效。
- **4 位数码管**：引擎显示累计时间，场景不用管。

开关拨上 = 开一场**法事**；拨下 = **歇**。用户要求：把道教的整套文化（烧香、结印、作法、八卦、六爻、符箓、内丹、星斗……）
融进去，让每一次拨开关都有趣、充满未知感；**法事 50+、歇 50+，画面各不相同**。

## 画风（用户已确认，必须严格遵守）

**清晰、精致的 1 位像素画**，参考《元气骑士》《Minit》等像素游戏的技巧：

- **每个物件都是逐像素造型的精灵**：轮廓清楚，一眼能看出是什么；有高光点、阴线、纹样、镶边这类细节。
  可以是平面的，但要精致。**不要**简单几何拼凑（一个圆 + 一条线 = 简笔画，用户明确不要）。
- **阴影只用规则网点**（`pix.checker`、`Part.dither`），小面积、有目的地用；不要大片灰。
- **禁止使用灰度层**（`g.lum`、`engine/art.py`、`engine/rig.py` 是被否掉的“糊”风格，不要用）。
- **主角是 Q 版小道士**（`engine/chars.py`）：大部分场景由他来做（法事里作法、歇里休息），保持全作风格统一。
  也可以有道具特写的场景，但小道士至少出现在七成场景里。
- **动作要多、要有表演**：预备动作 → 动作 → 余韵；呼吸、眨眼、袖子摆动这类次要动作；
  逐帧精灵动画（火苗、水波、翅膀）；打击感：火星 `pix.Sparks`、烟团 `pix.Puffs`、震屏 `pix.shake`、
  闪白 `pix.flash`、挤压拉伸 `pix.stretch`、缓动弹出 `ease_out_back`。持续阶段要一直有东西在动，并且每隔一阵有一个小事件。
- **构图**：多数场景是侧视的小舞台（地面线 + 背景少量细节 + 主体）。主体够大、留白清楚，不要塞满。

## 文字规则（用户特别强调：不能有文字堆叠）

- 每帧最多一两处文字；文字是点缀，画面靠图形和动作。
- `g.text` 默认给字描一圈黑边。**文字放在干净的区域，并且在所有特效之后最后画**（烟、火星、粒子都不能压在字上）。
- 字与字不能重叠；字不能出屏；12px 中文字高 11，8px 只适合数字、英文和两三个汉字。
- `tools.check` 会检查：**文字重叠、文字被画面压住**都算错误，必须改到 0。
- 文字内容要地道：用真实的典籍原文、咒语、术语，不要编造。

## 场景结构

先读 `apps/dao/engine/scene.py`（阶段与参数）和示范 `apps/dao/rituals/r0_incense.py`（质量标杆），
再读 `engine/chars.py`（小道士）、`engine/pix.py`（像素工具）。

```python
@register
class Talisman(Ritual):
    id = "r2.talisman"; name = "画符"; desc = "一句话说明画面"
    T = {"enter": 5.0, "interrupt": 1.6, "resume": 1.8, "complete": 5.0}
    CYCLE = 600.0
    def setup(self): ...          # self.rng 决定变化；Puffs/Sparks 在这里建
    def enter(self, g, t): ...
    def hold(self, g, t, e): ...  # e = 本场法事累计秒数（跨暂停累加，可无限大）
    def interrupt(self, g, t, e): ...
    def resume(self, g, t, e): ...
    def complete(self, g, t, e): ...
```

- 每帧引擎先清空画布，再调用当前阶段画一整帧。t = 本阶段秒数。
- **进度类画面是 e 的函数**（香变短、符写到第几笔、丹炼到几转），断线重连、暂停恢复都能接上；t 用于氛围动作。
- **hold 无限持续**：一轮（CYCLE，300–1200 秒）结束后有一段“续”的表演（再插一炷香、再画一道符），然后下一轮。
- 断线重连时可能不经 enter 直接 hold / complete；有状态的粒子要能从空开始。用 `t` 的差值算 dt 时注意 t 会回到 0。
- 衔接：enter 最后一帧 ≈ hold；interrupt 从 hold 开始；resume 结束 ≈ hold(e)。不同场景之间引擎自动溶解。
- 法事五段：入场 3–7s、持续无限、中断 1–2s、恢复 1–2.5s、圆满 3–6s（高潮：闪白、火星、“功德圆满”之类）。
- 歇三段：`enter`（2–4s）、`hold(g, t)`（t 无上限，安静耐看，每隔几十秒一个小彩蛋）、`exit`（1–1.5s，可读 `self.hold_t`）。
  `self.ctx.finished` = 上一场是圆满结束的。
- 起卦 / 特殊场景：`play(g, t)`，起卦在 setup 里算 `self.lines`（6 爻：6/7/8/9）。

## 工具

**小道士** `engine/chars.py`

```python
from ..engine.chars import daoshi, figure, Part, arm_sprite
h = daoshi(g, x, FLOOR, "bow", t, flip=False, face="normal")   # (x, FLOOR) = 脚底中点；返回 {"hand": (x, y)}
# pose: idle walk offer gongshou bow raise point sit meditate kneel sleep；face: normal sleep happy wow
```

新动作（扫地、劈柴、抚琴、喝茶、舞剑……）用 `figure()` 拼：手臂用 `Part` 自己画（设 `spr.hand=(x, y)`），
道具在 `behind` / `front` 回调里画，或者拿返回的手的位置画在手上。约 17 宽、35 高。

**像素工具** `engine/pix.py`：`frames`（多帧字符画）、`blit`（自动描黑边）、`anim`、`stretch`、`checker`、
`Puffs`、`Sparks`、`shake`、`flash`、`dotted`。**Part**（`chars.Part`）：在小画布上用 `shape("polygon"/"rectangle"/
"ellipse"/"line", …)` 画形状、`px` 点像素、`dither` 加网点，`.sprite()` 得到精灵；道具都这样画，**在模块级生成一次缓存**。

**其他**：`g.d`（白墨 ImageDraw）、`g.k`（黑墨：压在别的东西上的黑块，比如字的底板）、`g.text`、`g.vtext`、
`symbols.py`（八卦、六十四卦、太极、`mx_hexagram`）、`cn.py`（中文数字、干支）、`anim.py`（缓动）。
点阵 `g.mx`（8×8 bool）每个场景都要用，`g.mx_level` 平时 1、高潮瞬间 4–8。

## 验证（必须做）

在仓库根目录 `~/wwb_timer`、conda 环境 esp32 里：

```bash
conda run -n esp32 python -m apps.dao.tools.check --prefix r2.     # 异常、耗时、缺字、衔接、文字堆叠：错误必须为 0
conda run -n esp32 python -m apps.dao.tools.preview r2.zhufu --out <你的目录> --cols 4 --step 0.4
```

**预览 PNG 一定要用 Read 看**，每个阶段都看：一眼能不能认出画的是什么、动作是否连贯、字有没有被压、点阵有没有内容。
细节看不清时，自己写脚本把单帧放大 6–8 倍看。不满意就改，直到达到燃香样板的水准。

只改分配给你的文件：`apps/dao/<rituals|rests|omens|special>/<前缀>_*.py` 和 `apps/dao/catalog/<前缀>.md`。
不要改 engine/、tools/、别人的文件，不要 git commit，不要启动模拟器，不要用 pkill/killall，
辅助脚本放在自己的 scratchpad 子目录（别和其他批次共用文件名）。
