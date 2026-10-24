"""场景：法事（Ritual）、歇（Rest）、起卦（Omen）、特殊场景（Special）。

一个场景是一个类，用 @register 登记。引擎每帧先清空画布，再调用当前阶段的方法画一帧（立即模式）。
方法里的 t = 本阶段已经过的秒数；e = 本场法事累计计时秒数（来自芯片，跨暂停累加）。

法事（每场法事一个实例；同一个 seed 必须画出同样的变化，断线重连后接着演）：
    enter(g, t)          入场，t ∈ [0, T["enter"]]，最后一帧要接得上 hold
    hold(g, t, e)        持续：计时中一直播放。e 可以无限大：一轮（CYCLE 秒，如一炷香烧完）结束后
                         要有“续一根香”式的过渡，然后下一轮。这一阶段也可能是断线重连后直接进入（没有 enter）
    interrupt(g, t, e)   中断（不满 10 分钟就停了）：从 hold 的样子过渡到“暂停”的样子，然后引擎溶解进歇
    resume(g, t, e)      恢复：歇结束后回来，最后一帧要接得上 hold(e)
    complete(g, t, e)    圆满（满 10 分钟后停下）：收尾

歇（暂停时播放，一个实例只用一次）：
    enter(g, t) → hold(g, t)（t 无上限，循环播放）→ exit(g, t)（self.hold_t = 持续阶段最后的 t）

起卦（新法事开始前，三分之一的概率）：
    setup() 里算出 self.lines（6 爻，见 symbols），play(g, t) 演出起卦过程

特殊场景：开坛（程序启动）、天地重开（芯片清零）等，play(g, t)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .gfx import Gfx

REGISTRY: dict[str, dict[str, type]] = {"ritual": {}, "rest": {}, "omen": {}, "special": {}}


def register(cls):
    """类装饰器：登记场景。id 全局唯一"""
    assert cls.id, f"{cls.__name__} 缺少 id"
    assert cls.kind in REGISTRY, f"{cls.__name__}.kind 应为 ritual/rest/omen/special 之一（不要覆盖 kind 属性）"
    for kind in REGISTRY.values():
        assert cls.id not in kind, f"场景 id 重复：{cls.id}"
    REGISTRY[cls.kind][cls.id] = cls
    return cls


@dataclass
class Ctx:
    """场景能读到的全局信息（只读）"""
    total: float = 0.0           # 芯片累计计时秒数
    running: bool = False
    completed: int = 0           # 已圆满的法事场数（道行）
    lines: list = field(default_factory=lambda: [7, 7, 7, 7, 7, 7])  # 本场法事的卦
    ritual_name: str = ""        # 当前（或刚中断的）法事名
    finished: bool = False       # 歇：上一场是圆满结束的（False = 中途暂停）

    def realm(self) -> str:
        return realm(self.total)


REALMS = [(0, "凡人"), (1, "练气"), (10, "筑基"), (30, "结丹"), (80, "元婴"), (200, "化神"), (500, "炼虚"),
          (1000, "合体"), (2000, "大乘"), (5000, "渡劫")]


def realm(total_s: float) -> str:
    """按累计小时数定境界"""
    h = total_s / 3600
    name = REALMS[0][1]
    for need, n in REALMS:
        if h >= need:
            name = n
    return name


class Scene:
    kind = ""
    id = ""            # 全局唯一，如 "r.incense"
    name = ""          # 中文名，如 "燃香"
    desc = ""          # 一句话说明画面（目录与画廊用）
    T: dict[str, float] = {}

    hold_t = 0.0  # 引擎维护：持续阶段最后一帧的 t（歇的 exit 用来无缝收场）

    def __init__(self, seed: int = 0, ctx: Ctx | None = None):
        self.seed = seed
        self.rng = random.Random(seed)
        self.ctx = ctx or Ctx()
        self.setup()

    def setup(self):
        """实例创建时调用一次：用 self.rng 决定这一场的变化（香的数量、符的字……）"""


class Ritual(Scene):
    kind = "ritual"
    T = {"enter": 3.0, "interrupt": 1.5, "resume": 1.5, "complete": 4.0}
    CYCLE = 600.0  # hold 一轮的秒数

    def enter(self, g: Gfx, t: float):
        self.hold(g, t, 0.0)

    def hold(self, g: Gfx, t: float, e: float):
        raise NotImplementedError

    def interrupt(self, g: Gfx, t: float, e: float):
        self.hold(g, 0.0, e)

    def resume(self, g: Gfx, t: float, e: float):
        self.hold(g, t, e)

    def complete(self, g: Gfx, t: float, e: float):
        self.hold(g, 0.0, e)


class Rest(Scene):
    kind = "rest"
    T = {"enter": 2.5, "exit": 1.2}

    def enter(self, g: Gfx, t: float):
        self.hold(g, t)

    def hold(self, g: Gfx, t: float):
        raise NotImplementedError

    def exit(self, g: Gfx, t: float):
        self.hold(g, t)


class Omen(Scene):
    kind = "omen"
    T = {"play": 5.0}

    def setup(self):
        from .symbols import cast_coins
        self.lines = cast_coins(self.rng)

    def play(self, g: Gfx, t: float):
        raise NotImplementedError


class Special(Scene):
    kind = "special"
    T = {"play": 3.0}

    def play(self, g: Gfx, t: float):
        raise NotImplementedError


LOAD_ERRORS: dict[str, str] = {}  # 模块名 → 导入错误（一个文件出错不影响其他场景）


def load_all():
    """导入 rituals/ rests/ omens/ special/ 下的全部模块（模块导入时登记场景）"""
    import importlib
    import pkgutil
    import traceback
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent
    for sub in ("special", "omens", "rituals", "rests"):
        for m in sorted(pkgutil.iter_modules([str(base / sub)]), key=lambda m: m.name):
            name = f"apps.dao.{sub}.{m.name}"
            if m.name.startswith("_") or name in LOAD_ERRORS:
                continue
            try:
                importlib.import_module(name)
            except Exception:
                LOAD_ERRORS[name] = traceback.format_exc(limit=3)
    return REGISTRY
