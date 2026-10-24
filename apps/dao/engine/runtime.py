"""运行：直播模式（跟随芯片计时）、画廊模式（逐个看全部场景），以及往设备输出画面。"""
from __future__ import annotations

import queue
import time

from wwb import Device
from wwb.device import image_to_frame

from .director import PHASE_NAMES, Director, Player, Step, seg_digits
from .gfx import Gfx
from .scene import LOAD_ERRORS, REGISTRY, Ctx, load_all

FPS = 30


class Output:
    """只发变化的部分；接管被打断（芯片重启等）后 invalidate() 全部重发"""

    def __init__(self, d: Device):
        self.d = d
        self.invalidate()

    def invalidate(self):
        self.oled = self.mx = self.seg = None
        self.level = -1

    def send(self, g: Gfx, seg: bytes):
        frame = image_to_frame(g.img)
        if frame != self.oled:
            self.d.oled_frame(frame)
            self.oled = frame
        mx = g.mx_bytes()
        if mx != self.mx:
            self.d.mx_frame(mx)
            self.mx = mx
        if g.mx_level != self.level:
            self.d.mx_config(intensity=max(0, min(15, int(g.mx_level))), rotation=1)
            self.level = g.mx_level
        if seg != self.seg:
            self.d.seg_raw(seg)
            self.seg = seg


def info_card(g: Gfx, ctx: Ctx, t: float):
    """按 BOOT：境界、道行、累计时间、当前法事"""
    from .anim import ease_out, span
    p = ease_out(span(t, 0, 0.25)) * (1 - span(t, 2.7, 3.0))
    if p <= 0:
        return
    h = int(52 * p)
    y0 = 32 - h // 2
    g.d.rectangle((10, y0, 117, y0 + h), fill=0, outline=1)
    if p < 0.95:
        return
    total = int(ctx.total)
    g.text(64, y0 + 4, f"境界 · {ctx.realm()}", align="center")
    g.text(64, y0 + 19, f"道行 {ctx.completed}  修行 {total // 3600}时{total // 60 % 60:02d}分", size=8,
           align="center")
    g.text(64, y0 + 32, ctx.ritual_name or "—", align="center")


def _loop(d: Device, out: Output, tick, render_overlay=None):
    """30 帧/秒主循环：tick(dt) 推进并画好 g"""
    last = time.monotonic()
    nxt = last
    while True:
        now = time.monotonic()
        dt = min(now - last, 0.2)
        last = now
        tick(dt)
        nxt += 1 / FPS
        sleep = nxt - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)
        else:
            nxt = time.monotonic()


def live(d: Device, args):
    load_all()
    g = Gfx()
    out = Output(d)
    events: queue.Queue = queue.Queue()
    d.on_timer(lambda st: events.put(("timer", st)))
    d.on_input(lambda ev: events.put(("input", ev)))
    d.subscribe(inputs=True, timer=True)
    st = d.timer()
    if st is None:
        raise SystemExit("芯片里的脱机程序不是 wwb timer，dao timer 需要它来计时")
    for mod, err in LOAD_ERRORS.items():
        print(f"场景模块导入失败，已跳过：{mod}\n{err}")
    director = Director(g, complete_after=args.complete_after, timescale=args.timescale, save=d.set_app_data)
    director.begin(st.running, st.total_ms, st.epoch, d.app_data())
    print(f"dao timer：累计 {st.total_ms / 1000 / 3600:.2f} 小时，{'计时中' if st.running else '已停止'}；"
          f"法事 {len(REGISTRY['ritual'])} 种，歇 {len(REGISTRY['rest'])} 种，起卦 {len(REGISTRY['omen'])} 种")
    state = {"poll": 0.0, "card": None, "lost": False}

    def tick(dt):
        while not events.empty():
            kind, v = events.get_nowait()
            if kind == "timer":
                director.timer(v.running, v.total_ms, v.epoch)
            elif kind == "input" and v.input == 1 and v.active:
                state["card"] = 0.0
        state["poll"] += dt
        if state["poll"] >= 1.0:  # 每秒对一次时间，顺便确认还在接管（芯片重启后要全部重发）
            state["poll"] = 0
            try:
                st = d.timer()
                if st:
                    director.timer(st.running, st.total_ms, st.epoch)
                ok = d.request(0x0D, timeout=1.0)[0] == 2
            except Exception:
                ok = False
            if not ok:
                state["lost"] = True
            elif state["lost"]:
                state["lost"] = False
                out.invalidate()
        director.frame(dt)
        if state["card"] is not None:
            state["card"] += dt
            info_card(g, director.ctx, state["card"])
            if state["card"] > 3:
                state["card"] = None
        colon = director.running and (director.total_ms % 1000) < 500 or not director.running
        out.send(g, seg_digits(director.total_ms / 1000, colon))

    _loop(d, out, tick)


# ---------------------------------------------------------------- 画廊

def gallery_acts(only: str | None = None, kinds=("special", "omen", "ritual", "rest"), seed: int = 1):
    """[(标题, 生成 Step 列表的函数)]：每个场景一幕。法事走完整流程：
    入场 → 持续（7 秒快进 1.25 轮，看得到“续香”）→ 中断 → 一个歇 → 恢复 → 持续 → 圆满"""
    load_all()
    rests = sorted(REGISTRY["rest"])
    acts = []
    for kind in kinds:
        for i, sid in enumerate(sorted(REGISTRY[kind])):
            if only and sid != only:
                continue
            cls = REGISTRY[kind][sid]

            def build(kind=kind, cls=cls, i=i):
                ctx = Ctx(total=12345, running=True, completed=7, ritual_name=cls.name if kind == "ritual" else "")
                sc = cls(seed + i, ctx)
                if kind == "ritual":
                    cyc = cls.CYCLE
                    ff, e1 = cyc * 1.25 / 7, cyc * 1.25
                    steps = [Step(sc, "enter"), Step(sc, "hold", 7.0, lambda t: t * ff),
                             Step(sc, "interrupt", efn=lambda t: e1)]
                    if rests:
                        r = REGISTRY["rest"][rests[i % len(rests)]](seed + 100 + i, ctx)
                        steps += [Step(r, "enter"), Step(r, "hold", 2.5), Step(r, "exit")]
                    return steps + [Step(sc, "resume", efn=lambda t: e1), Step(sc, "hold", 3.0, lambda t: e1 + t),
                                    Step(sc, "complete", efn=lambda t: e1 + 3)]
                if kind == "rest":
                    return [Step(sc, "enter"), Step(sc, "hold", 6.0), Step(sc, "exit")]
                return [Step(sc, "play")]

            acts.append((f"{KIND_NAMES[kind]}·{cls.name}（{sid}）", build, kind))
    return acts


KIND_NAMES = {"ritual": "法事", "rest": "歇", "omen": "起卦", "special": "特殊"}


def gallery(d: Device, args):
    g = Gfx()
    out = Output(d)
    acts = gallery_acts(args.only)
    if not acts:
        raise SystemExit(f"没有场景 {args.only}")
    events: queue.Queue = queue.Queue()
    d.on_input(lambda ev: events.put(ev))
    d.subscribe(inputs=True)
    print(f"画廊：{len(acts)} 幕（{'、'.join(f'{KIND_NAMES[k]} {sum(a[2] == k for a in acts)}' for k in KIND_NAMES if any(a[2] == k for a in acts))}）。"
          "短按 BOOT 下一幕，长按（0.8 秒）跳到下一类；开关拨下暂停", flush=True)
    player = Player(g)
    player.on_step = lambda s: print(f"    {PHASE_NAMES.get(s.phase) or '播放'}", flush=True)
    st = {"i": -1, "paused": False, "down": None}

    def start(i):
        st["i"] = i % len(acts)
        title, build, _ = acts[st["i"]]
        print(f"[{st['i'] + 1}/{len(acts)}] {title}", flush=True)
        player.go(build())

    start(0)

    def tick(dt):
        while not events.empty():
            ev = events.get_nowait()
            if ev.input == 1 and ev.active:
                st["down"] = ev.t_us
            elif ev.input == 1 and st["down"] is not None:
                held = (ev.t_us - st["down"]) / 1e6
                st["down"] = None
                if held >= 0.8:  # 长按：下一类
                    kind = acts[st["i"]][2]
                    j = st["i"]
                    while acts[j % len(acts)][2] == kind and j < st["i"] + len(acts):
                        j += 1
                    start(j)
                else:
                    start(st["i"] + 1)
            elif ev.input == 0:
                st["paused"] = not ev.active
        if not st["paused"]:
            player.advance(dt)
            if player.cur and not player.queue and player.t >= player.cur.length:
                start(st["i"] + 1)
        player.render(0.0)
        out.send(g, _seg_num(st["i"] + 1))

    _loop(d, out, tick)


def _seg_num(n: int) -> bytes:
    """数码管右对齐显示整数（画廊显示第几幕）"""
    D = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F]
    s = str(n)[-4:].rjust(4)
    return bytes(0 if c == " " else D[int(c)] for c in s)
