"""把一个场景渲染成联系表（PNG），不需要设备：

    python -m apps.dao.tools.preview r.incense            # → /tmp/dao_preview/r.incense-*.png
    python -m apps.dao.tools.preview r.incense --out DIR --cols 6 --step 0.25

每个阶段一张图：按 step 秒取样的帧（OLED 放大 2 倍，右边是点阵），标注阶段与 t（持续阶段还标 e）。
持续阶段取几段：e=0 起、e=半轮、一轮结束前后（看“续香”）、很久以后（e=10 轮+）。
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..engine.director import call
from ..engine.gfx import Gfx
from ..engine.scene import REGISTRY, Ctx, Omen, Rest, Ritual, load_all

DT = 1 / 30
OLED_S = 2
MX_CELL = 6


def frame_tile(g: Gfx, label: str) -> Image.Image:
    w = 128 * OLED_S + 8 + 8 * MX_CELL
    tile = Image.new("RGB", (w, 64 * OLED_S + 14), (40, 40, 48))
    oled = g.img.convert("L").resize((128 * OLED_S, 64 * OLED_S), Image.NEAREST)
    tile.paste(Image.merge("RGB", (oled.point(lambda v: v * 0.55), oled.point(lambda v: v * 0.85), oled)), (0, 14))
    d = ImageDraw.Draw(tile)
    x0 = 128 * OLED_S + 8
    lv = min(1.0, 0.75 + g.mx_level / 15 * 0.25)
    for y in range(8):
        for x in range(8):
            c = (int(255 * lv), int(70 * lv), int(50 * lv)) if g.mx[y, x] else (45, 14, 14)
            d.ellipse((x0 + x * MX_CELL + 1, 14 + y * MX_CELL + 1, x0 + x * MX_CELL + MX_CELL - 1,
                       14 + y * MX_CELL + MX_CELL - 1), fill=c)
    d.text((2, 1), label, fill=(220, 220, 220), font=_label_font())
    return tile


_lf = None


def _label_font():
    global _lf
    if _lf is None:
        from ..engine.gfx import FONT_DIR
        _lf = ImageFont.truetype(str(FONT_DIR / "fusion-pixel-12px-zh_hans-gbk.ttf"), 12)
    return _lf


def sheet(tiles: list[Image.Image], cols: int) -> Image.Image:
    if not tiles:
        return Image.new("RGB", (10, 10))
    tw, th = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new("RGB", (cols * (tw + 4), rows * (th + 4)), (15, 15, 18))
    for i, t in enumerate(tiles):
        img.paste(t, ((i % cols) * (tw + 4), (i // cols) * (th + 4)))
    return img


def run_phase(sc, phase: str, length: float, step: float, efn=None, label: str = "", g: Gfx | None = None,
              t0: float = 0.0):
    """以 30 帧/秒推进（有状态的场景要逐帧走），每 step 秒取一帧；t0：从这个 t 开始（看很久以后的样子）"""
    g = g or Gfx()
    tiles = []
    n = int(round(length / DT))
    every = max(1, int(round(step / DT)))
    for i in range(n + 1):
        t = t0 + min(i * DT, length)
        e = efn(t) if efn else 0.0
        g.clear()
        call(sc, phase, g, t, e)
        if i % every == 0 or i == n:
            lab = f"{label or phase} t={t:.2f}" + (f" e={e:.0f}s" if isinstance(sc, Ritual) and phase != "enter" else "")
            tiles.append(frame_tile(g, lab))
    return tiles


def preview(sid: str, out: Path, cols: int = 6, step: float = 0.25, seed: int = 1) -> list[Path]:
    load_all()
    cls = next((k[sid] for k in REGISTRY.values() if sid in k), None)
    if cls is None:
        raise SystemExit(f"没有场景 {sid}")
    import random
    from ..engine.symbols import cast_coins
    ctx = Ctx(total=4321, running=True, completed=3, ritual_name=cls.name, lines=cast_coins(random.Random(seed)))
    sc = cls(seed, ctx)
    out.mkdir(parents=True, exist_ok=True)
    pages: list[tuple[str, list]] = []
    if isinstance(sc, Ritual):
        cyc = sc.CYCLE
        pages.append(("1-enter", run_phase(sc, "enter", sc.T["enter"], step)))
        hold = []
        for e0, lab in ((0, "持续 e=0 起"), (cyc / 2, "半轮"), (cyc - 2, "一轮结束→续"), (cyc * 10 + 5, "十轮后")):
            hold += run_phase(sc, "hold", 4.0 if e0 != cyc - 2 else 8.0, step * 2, lambda t, e0=e0: e0 + t, lab)
        pages.append(("2-hold", hold))
        ei = cyc * 0.4
        pages.append(("3-interrupt", run_phase(sc, "interrupt", sc.T["interrupt"], step, lambda t: ei)))
        pages.append(("4-resume", run_phase(sc, "resume", sc.T["resume"], step, lambda t: ei)))
        pages.append(("5-complete", run_phase(sc, "complete", sc.T["complete"], step, lambda t: cyc * 1.1)))
    elif isinstance(sc, Rest):
        pages.append(("1-enter", run_phase(sc, "enter", sc.T["enter"], step)))
        pages.append(("2-hold", run_phase(sc, "hold", 6.0, step * 2)
                      + run_phase(sc, "hold", 4.0, step * 2, label="hold(1小时后)", t0=3600.0)))
        pages.append(("3-exit", run_phase(sc, "exit", sc.T["exit"], step)))
    else:
        pages.append(("play", run_phase(sc, "play", sc.T["play"], step)))
    paths = []
    for name, tiles in pages:
        p = out / f"{sid}-{name}.png"
        sheet(tiles, cols).save(p)
        paths.append(p)
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--out", default="/tmp/dao_preview")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--step", type=float, default=0.25, help="取样间隔秒")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    for sid in a.ids:
        for p in preview(sid, Path(a.out), a.cols, a.step, a.seed):
            print(p)


if __name__ == "__main__":
    main()
