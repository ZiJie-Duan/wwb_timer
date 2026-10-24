"""导演：把芯片的计时状态变成一段段场景。

时间只认芯片：本场法事已进行多久 = 芯片累计时间 − 法事开始时的累计时间。法事进度（哪场、从哪开始、
随机种子）存在芯片的控制器存储里，换一台上位机或断线重连都能接着演。

    拨上开关：歇.退场 → 法事.恢复 → 法事.持续（接着上次没做完的法事）
              或（1/3 概率起卦 →）新法事.入场 → 法事.持续
    拨下开关：法事累计 ≥ 10 分钟 → 法事.圆满 → 歇.入场 → 歇.持续（法事结束）
              否则              → 法事.中断 → 歇.入场 → 歇.持续（法事保留）

过渡动画还没播完开关又变了：当前这段加速播完（×3），然后走新的路线。不同场景之间抖动溶解 0.35 秒。
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .gfx import Gfx, dissolve
from .scene import REGISTRY, Ctx, Omen, Rest, Ritual, Scene, Special

DISSOLVE_S = 0.35
HURRY = 3.0
OMEN_CHANCE = 1 / 3
RECENT = 12  # 最近用过的法事 / 歇不再抽到


@dataclass
class Step:
    scene: Scene
    phase: str
    dur: float | None = None             # None：过渡阶段用 scene.T[phase]；hold 为无限
    efn: Callable[[float], float] | None = None  # 画廊用：t → e

    @property
    def length(self) -> float:
        if self.dur is not None:
            return self.dur
        if self.phase == "hold":
            return float("inf")
        return self.scene.T[self.phase]


def call(scene: Scene, phase: str, g: Gfx, t: float, e: float):
    fn = getattr(scene, phase)
    if isinstance(scene, Ritual) and phase != "enter":
        fn(g, t, e)
    else:
        fn(g, t)


class Player:
    """按顺序播放 Step，处理加速与溶解"""

    def __init__(self, g: Gfx):
        self.g = g
        self.cur: Step | None = None
        self.t = 0.0
        self.queue: list[Step] = []
        self.speed = 1.0
        self.prev: np.ndarray | None = None
        self.diss_t = DISSOLVE_S
        self.on_step: Callable[[Step], None] | None = None

    def go(self, steps: list[Step]):
        """立即切到 steps[0]"""
        self.queue = list(steps)
        self._next()

    def follow(self, steps: list[Step]):
        """当前是过渡阶段就加速播完再接 steps，是持续阶段就立即切"""
        if self.cur is None or self.cur.length == float("inf"):
            self.go(steps)
        else:
            self.queue = list(steps)
            self.speed = HURRY

    def _next(self):
        if not self.queue:
            return
        nxt = self.queue.pop(0)
        if self.cur is not None and nxt.scene is not self.cur.scene:
            self.prev = self.g.array()
            self.diss_t = 0.0
        self.cur, self.t, self.speed = nxt, 0.0, 1.0
        if self.on_step:
            self.on_step(nxt)

    def advance(self, dt: float):
        if self.cur is None:
            return
        self.t += dt * self.speed
        self.diss_t += dt
        while self.cur.length != float("inf") and self.t >= self.cur.length and self.queue:
            over = (self.t - self.cur.length) / max(self.speed, 1e-6)
            self._next()
            self.t = over * self.speed
        if self.cur.length != float("inf") and self.t > self.cur.length:
            self.t = self.cur.length  # 没有下一段：停在最后一帧

    def render(self, e_default: float):
        g = self.g
        g.clear()
        if self.cur is None:
            return
        s = self.cur
        e = s.efn(self.t) if s.efn else e_default
        call(s.scene, s.phase, g, min(self.t, s.length), e)
        if self.prev is not None and self.diss_t < DISSOLVE_S:
            g.put(dissolve(self.prev, g.array(), self.diss_t / DISSOLVE_S))


class Director:
    """直播模式：跟随芯片的计时状态"""

    def __init__(self, g: Gfx, complete_after: float = 600.0, timescale: float = 1.0, seed: int | None = None,
                 save: Callable[[bytes], None] | None = None, log: Callable[[str], None] = print):
        self.g = g
        self.player = Player(g)
        self.player.on_step = self._on_step
        self.complete_after = complete_after
        self.timescale = timescale
        self.rng = random.Random(seed)
        self.save_fn = save
        self.log = log
        self.ctx = Ctx()
        self.total_ms = 0.0        # 芯片累计（外推到当前）
        self.running = False
        self.epoch = 0
        self.data: dict = {}       # 存在芯片里的进度
        self.ritual: Ritual | None = None
        self.ritual_done = False
        self.rest: Rest | None = None

    # ------------------------------------------------------------ 持久化

    def _save(self):
        if self.save_fn:
            raw = json.dumps(self.data, separators=(",", ":"), ensure_ascii=False).encode()
            if len(raw) > 256:
                self.data["h"] = self.data.get("h", [])[-4:]
                raw = json.dumps(self.data, separators=(",", ":"), ensure_ascii=False).encode()
            self.save_fn(raw)

    def _recent(self, key: str, sid: str):
        h = self.data.setdefault(key, [])
        if sid in h:
            h.remove(sid)
        h.append(sid)
        del h[:-RECENT]

    # ------------------------------------------------------------ 选场景

    def _pick(self, kind: str, avoid: list[str]) -> type:
        pool = REGISTRY[kind]
        ids = [i for i in pool if i not in avoid] or list(pool)
        return pool[self.rng.choice(sorted(ids))]

    def _make_ritual(self, cls: type, seed: int, lines) -> Ritual:
        self.ctx.lines = list(lines)
        self.ctx.ritual_name = cls.name
        return cls(seed, self.ctx)

    def ritual_e(self) -> float:
        if not self.ritual:
            return 0.0
        return max(0.0, (self.total_ms - self.data.get("rs", 0)) / 1000) * self.timescale

    def _new_rest(self) -> Rest:
        if not REGISTRY["rest"]:
            return _IdleRest(0, self.ctx)
        cls = self._pick("rest", self.data.get("hr", []))
        self._recent("hr", cls.id)
        self.ctx.finished = self.ritual_done
        return cls(self.rng.randrange(1 << 30), self.ctx)

    # ------------------------------------------------------------ 路线

    def _new_ritual_path(self) -> list[Step]:
        cls = self._pick("ritual", self.data.get("h", []))
        seed = self.rng.randrange(1 << 30)
        steps = []
        omen = None
        if REGISTRY["omen"] and self.rng.random() < OMEN_CHANCE:
            ocls = self._pick("omen", self.data.get("ho", []))
            self._recent("ho", ocls.id)
            omen = ocls(self.rng.randrange(1 << 30), self.ctx)
            lines = omen.lines
            steps.append(Step(omen, "play"))
        else:
            from .symbols import cast_coins
            lines = cast_coins(self.rng)
        self.ritual = self._make_ritual(cls, seed, lines)
        self.ritual_done = False
        self.data.update(r=cls.id, sd=seed, g="".join(map(str, lines)), rs=int(self.total_ms))
        self._recent("h", cls.id)
        self._save()
        steps += [Step(self.ritual, "enter"), Step(self.ritual, "hold")]
        return steps

    def _rest_path(self, rest: Rest | None = None) -> list[Step]:
        self.rest = rest or self._new_rest()
        return [Step(self.rest, "enter"), Step(self.rest, "hold")]

    def _start_path(self) -> list[Step]:
        cur = self.player.cur
        steps: list[Step] = []
        if cur and isinstance(cur.scene, Rest) and cur.phase != "exit":
            steps.append(Step(cur.scene, "exit"))
        if self.ritual and not self.ritual_done:
            steps += [Step(self.ritual, "resume"), Step(self.ritual, "hold")]
        else:
            steps += self._new_ritual_path()
        return steps

    def _stop_path(self) -> list[Step]:
        cur = self.player.cur
        steps: list[Step] = []
        if cur and isinstance(cur.scene, Omen):
            # 起卦途中就停了：这场法事还没开始，作废
            self.ritual, self.ritual_done = None, False
            for k in ("r", "sd", "g", "rs"):
                self.data.pop(k, None)
            self._save()
            return self._rest_path()
        if cur and isinstance(cur.scene, Rest):
            return self._rest_path(cur.scene)  # 歇正在退场又停了：回到这个歇
        if self.ritual and not self.ritual_done:
            e = self.ritual_e()
            if e >= self.complete_after:
                steps.append(Step(self.ritual, "complete"))
                self._finish()
            else:
                steps.append(Step(self.ritual, "interrupt"))
        return steps + self._rest_path()

    def _finish(self):
        self.ritual_done = True
        self.data["n"] = self.data.get("n", 0) + 1
        self.ctx.completed = self.data["n"]
        for k in ("r", "sd", "g", "rs"):
            self.data.pop(k, None)
        self._save()

    def _on_step(self, s: Step):
        self.log(f"· {s.scene.name or s.scene.id}（{s.scene.id}）{PHASE_NAMES.get(s.phase, s.phase)}")

    # ------------------------------------------------------------ 输入

    def begin(self, running: bool, total_ms: float, epoch: int, data: bytes):
        """程序启动：芯片状态 + 存储的进度 → 开坛，然后接上当前状态"""
        self.running, self.total_ms, self.epoch = running, total_ms, epoch
        try:
            self.data = json.loads(data.decode()) if data else {}
        except ValueError:
            self.data = {}
        steps: list[Step] = []
        specials = REGISTRY["special"]
        fresh = not self.data
        if self.data.get("ep", epoch) != epoch:
            # 断线期间芯片清零过
            self.data = {"ep": epoch, "n": 0}
            if "s.reset" in specials:
                steps.append(Step(specials["s.reset"](self.rng.randrange(1 << 30), self.ctx), "play"))
        self.data["ep"] = epoch
        self.ctx.completed = self.data.get("n", 0)
        if fresh:
            self._save()
        if "s.boot" in specials and not steps:
            steps.append(Step(specials["s.boot"](self.rng.randrange(1 << 30), self.ctx), "play"))
        rid = self.data.get("r")
        if rid in REGISTRY["ritual"]:
            lines = [int(c) for c in self.data.get("g", "777777")]
            self.ritual = self._make_ritual(REGISTRY["ritual"][rid], self.data.get("sd", 0), lines)
            self.ritual_done = False
        elif rid:
            for k in ("r", "sd", "g", "rs"):  # 程序更新后这场法事没了
                self.data.pop(k, None)
        self._sync_ctx()
        if running:
            steps += [Step(self.ritual, "resume"), Step(self.ritual, "hold")] if self.ritual else self._new_ritual_path()
        else:
            if self.ritual and self.ritual_e() >= self.complete_after:
                steps.append(Step(self.ritual, "complete"))
                self._finish()
            steps += self._rest_path()
        self.player.go(steps)

    def timer(self, running: bool, total_ms: float, epoch: int):
        """芯片上报（或轮询到）计时状态"""
        self.total_ms = total_ms
        if epoch != self.epoch:
            self.epoch = epoch
            self.data = {"ep": epoch, "n": 0}
            self.ritual, self.ritual_done = None, False
            self.ctx.completed = 0
            self._save()
            self.running = running
            steps = []
            if "s.reset" in REGISTRY["special"]:
                steps.append(Step(REGISTRY["special"]["s.reset"](self.rng.randrange(1 << 30), self.ctx), "play"))
            steps += self._new_ritual_path() if running else self._rest_path()
            self.player.go(steps)
            return
        if running == self.running:
            return
        self.running = running
        self._sync_ctx()
        self.player.follow(self._start_path() if running else self._stop_path())

    def _sync_ctx(self):
        self.ctx.total = self.total_ms / 1000
        self.ctx.running = self.running

    def frame(self, dt: float):
        if self.running:
            self.total_ms += dt * 1000
        self._sync_ctx()
        self.player.advance(dt)
        self.player.render(self.ritual_e())


class _IdleRest(Rest):
    """还没有任何歇时的后备：缓转的太极"""
    id = "_idle"
    name = "歇"

    def hold(self, g, t):
        from .symbols import mx_taiji, taiji
        taiji(g, 64, 32, 14, t * 0.5)
        g.text(64, 50, "歇", align="center")
        mx_taiji(g, t * 0.5)


PHASE_NAMES = {"enter": "入场", "hold": "持续", "interrupt": "中断", "resume": "恢复", "complete": "圆满",
               "exit": "退场", "play": ""}


def seg_digits(total_s: float, colon: bool) -> bytes:
    """数码管 时:分（与 wwb timer 相同）：不足 10 小时首位空白，100 小时起 123h，1000 小时起只显示小时"""
    D = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]
    m = int(total_s // 60)
    h, mm = divmod(m, 60)
    if h >= 1000:
        s = str(h)[-4:]
        out = [D[int(c)] for c in s.rjust(4)[-4:]] if len(s) >= 4 else [0] * (4 - len(s)) + [D[int(c)] for c in s]
        return bytes(out)
    if h >= 100:
        return bytes([D[h // 100], D[h // 10 % 10], D[h % 10], 0x74])
    out = [D[h // 10] if h >= 10 else 0, D[h % 10], D[mm // 10], D[mm % 10]]
    if colon:
        out[1] |= 0x80
    return bytes(out)
