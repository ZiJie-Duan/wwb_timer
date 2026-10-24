"""检查场景：异常、渲染耗时、缺字、空白画面、阶段衔接。不需要设备：

    python -m apps.dao.tools.check                 # 全部场景
    python -m apps.dao.tools.check r.incense s.tea # 指定场景
    python -m apps.dao.tools.check --prefix r1.    # 某一批

耗时预算（电脑上，树莓派 Zero 2 W 约慢 6-8 倍，要保证 30 帧/秒）：每帧中位 ≤ 3ms、最大 ≤ 15ms。
衔接：阶段交接处前后两帧的差异（不同像素 / 亮像素），> 0.6 提示可能跳变。
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
import traceback

import numpy as np

from ..engine.director import call
from ..engine.gfx import FONT_DIR, Gfx, _FONT_FILES
from ..engine.scene import LOAD_ERRORS, REGISTRY, Ctx, Rest, Ritual, load_all

DT = 1 / 30
MEDIAN_MS, MAX_MS = 3.0, 15.0
_cmaps: dict[int, set] = {}


def cmap(size: int) -> set:
    if size not in _cmaps:
        try:
            from fontTools.ttLib import TTFont
            _cmaps[size] = set(TTFont(str(FONT_DIR / _FONT_FILES[size][0]))["cmap"].getBestCmap())
        except ImportError:
            _cmaps[size] = set()
    return _cmaps[size]


class Probe:
    def __init__(self):
        self.g = Gfx()
        self.times: list[float] = []
        self.missing: set[str] = set()
        self.blank_runs: dict[str, float] = {}
        self.text_issues: dict[str, int] = {}
        self.mx_dark: dict[str, float] = {}

    def frame(self, sc, phase, t, e, tag) -> np.ndarray:
        g = self.g
        g.clear()
        t0 = time.perf_counter()
        call(sc, phase, g, t, e)
        self.times.append((time.perf_counter() - t0) * 1000)
        for s, size in g.texts:
            cm = cmap(size)
            if cm:
                self.missing |= {c for c in s if ord(c) not in cm and c not in "\n"}
        a = g.array()
        self._texts(g, a)
        if not a.any():
            self.blank_runs[tag] = self.blank_runs.get(tag, 0) + DT
        if not g.mx.any():
            self.mx_dark[tag] = self.mx_dark.get(tag, 0) + DT
        return a

    def _texts(self, g, a):
        """文字堆叠：字与字的范围相交；字的范围里有不属于字的亮点（被别的画面压住）；字出屏"""
        from ..engine.gfx import _text_img
        if g.invert_all:
            return  # 闪白的一帧整屏反色，不查
        ox, oy = g.offset
        boxes = [(b[0], b[1] + ox, b[2] + oy, b[3] + ox, b[4] + oy, b[5] + ox, b[6] + oy, b[7], b[8])
                 for b in g.text_boxes]
        for i in range(len(boxes)):
            s1, x0, y0, x1, y1 = boxes[i][:5]
            for j in range(i + 1, len(boxes)):
                s2, u0, v0, u1, v1 = boxes[j][:5]
                if x0 < u1 and u0 < x1 and y0 < v1 and v0 < y1:
                    k = f"文字重叠：「{s1}」与「{s2}」"
                    self.text_issues[k] = self.text_issues.get(k, 0) + 1
            if x0 < 0 or y0 < 0 or x1 > 128 or y1 > 64:
                k = f"文字出屏：「{s1}」"
                self.text_issues[k] = self.text_issues.get(k, 0) + 1
                continue
            ix, iy, size, scale = boxes[i][5:]
            glyph = np.array(_text_img(s1, size, scale), dtype=bool)
            region = a[y0:y1, x0:x1].copy()
            gy0, gx0 = y0 - iy, x0 - ix
            gl = glyph[gy0:gy0 + region.shape[0], gx0:gx0 + region.shape[1]]
            stray = int((region & ~gl).sum()) if gl.shape == region.shape else 0
            if stray > 2:
                k = f"文字被画面压住：「{s1}」"
                self.text_issues[k] = self.text_issues.get(k, 0) + 1

    def run(self, sc, phase, length, efn=None, tag=None):
        first = last = None
        n = int(round(length / DT))
        for i in range(n + 1):
            t = min(i * DT, length)
            a = self.frame(sc, phase, t, efn(t) if efn else 0.0, tag or phase)
            if first is None:
                first = a
            last = a
        return first, last


def diff(a: np.ndarray, b: np.ndarray) -> float:
    lit = max(int(a.sum()), int(b.sum()), 1)
    return float((a ^ b).sum()) / lit


def check(cls) -> tuple[list[str], list[str], str]:
    errors, warns = [], []
    import random
    from ..engine.symbols import cast_coins
    ctx = Ctx(total=5000, running=True, completed=2, ritual_name=cls.name, lines=cast_coins(random.Random(7)))
    p = Probe()
    try:
        for seed in (1, 2, 3):
            sc = cls(seed, ctx)
            if isinstance(sc, Ritual):
                cyc = sc.CYCLE
                if cyc < 60:
                    warns.append(f"CYCLE={cyc} 太短")
                _, enter_last = p.run(sc, "enter", sc.T["enter"])
                hold_first, _ = p.run(sc, "hold", 2.0, lambda t: t)
                if seed == 1 and diff(enter_last, hold_first) > 0.6:
                    warns.append(f"入场→持续 跳变 {diff(enter_last, hold_first):.2f}")
                for e0 in (cyc / 3, cyc - 1.5, cyc * 7 + 0.5, 86400 * 3 + 0.25):
                    p.run(sc, "hold", 3.0, lambda t, e0=e0: e0 + t, "hold")
                ei = cyc * 0.37
                h_at, _ = p.run(sc, "hold", 0.0, lambda t: ei, "hold")
                int_first, _ = p.run(sc, "interrupt", sc.T["interrupt"], lambda t: ei)
                if seed == 1 and diff(h_at, int_first) > 0.6:
                    warns.append(f"持续→中断 跳变 {diff(h_at, int_first):.2f}")
                _, res_last = p.run(sc, "resume", sc.T["resume"], lambda t: ei)
                h2, _ = p.run(sc, "hold", 0.5, lambda t: ei + t, "hold")
                if seed == 1 and diff(res_last, h2) > 0.6:
                    warns.append(f"恢复→持续 跳变 {diff(res_last, h2):.2f}")
                p.run(sc, "complete", sc.T["complete"], lambda t: cyc * 1.3)
                # 断线重连：没有 enter 直接 hold / complete
                fresh = cls(seed + 10, ctx)
                p.run(fresh, "hold", 1.0, lambda t: cyc * 2.5 + t, "hold")
                fresh = cls(seed + 20, ctx)
                p.run(fresh, "complete", fresh.T["complete"], lambda t: 700)
                for k in ("enter", "interrupt", "resume", "complete"):
                    if not 0.3 <= sc.T[k] <= 10:
                        warns.append(f"T[{k}]={sc.T[k]} 不在 0.3–10 秒")
            elif isinstance(sc, Rest):
                _, el = p.run(sc, "enter", sc.T["enter"])
                hf, _ = p.run(sc, "hold", 8.0)
                if seed == 1 and diff(el, hf) > 0.6:
                    warns.append(f"入场→持续 跳变 {diff(el, hf):.2f}")
                for i in range(600):  # 定时小事件：0–300 秒每 0.5 秒抽一帧
                    p.frame(sc, "hold", 8.0 + i * 0.5, 0.0, "hold-sample")
                for t0 in (95.0, 3600.0, 86400.0 * 2):  # 播了很久以后，再退场
                    n = int(2.0 / DT)
                    for i in range(n):
                        p.frame(sc, "hold", t0 + i * DT, 0.0, "hold")
                p.run(sc, "exit", sc.T["exit"])
                fresh = cls(seed + 10, ctx)
                p.run(fresh, "hold", 1.0, tag="hold")
            else:
                p.run(sc, "play", sc.T["play"])
                if sc.kind == "omen":
                    lines = getattr(sc, "lines", None)
                    if not (isinstance(lines, list) and len(lines) == 6 and all(v in (6, 7, 8, 9) for v in lines)):
                        errors.append(f"self.lines 不合法：{lines}")
                    if seed == 1 and not 4 <= sc.T["play"] <= 9:
                        warns.append(f"T[play]={sc.T['play']} 不在 4–9 秒")
    except Exception:
        errors.append(traceback.format_exc(limit=4).strip().splitlines()[-1])
        errors.append(traceback.format_exc(limit=6))
    if p.missing:
        errors.append("字体缺字：" + "".join(sorted(p.missing)))
    for k, n in sorted(p.text_issues.items()):
        (errors if k.startswith("文字重叠") or k.startswith("文字被") else warns).append(f"{k}（{n} 帧）")
    if p.times:
        med, mx = statistics.median(p.times), max(p.times)
        if med > MEDIAN_MS:
            warns.append(f"渲染中位 {med:.2f}ms > {MEDIAN_MS}")
        if mx > MAX_MS:
            warns.append(f"渲染最大 {mx:.1f}ms > {MAX_MS}")
        perf = f"{med:5.2f}/{mx:5.1f}ms"
    else:
        perf = "-"
    for tag, s in p.blank_runs.items():
        if tag == "hold" and s > 1.0:
            warns.append(f"持续阶段有 {s:.1f}s 全黑")
    for tag, s in p.mx_dark.items():
        if tag == "hold" and s > 3.0:
            warns.append(f"持续阶段点阵 {s:.1f}s 全灭")
    if not cls.name:
        warns.append("缺少 name")
    if not cls.desc:
        warns.append("缺少 desc")
    return errors, warns, perf


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--prefix", default="")
    a = ap.parse_args()
    load_all()
    bad = 0
    total = 0
    for mod, err in LOAD_ERRORS.items():
        fname = mod.rsplit(".", 1)[-1]  # 如 r2_zhufu；前缀 r2. 对应文件名 r2_
        if a.prefix and not fname.startswith(a.prefix.rstrip(".").replace(".", "_")):
            continue
        print(f"✗ 导入失败 {mod}\n    " + err.strip().replace("\n", "\n    "))
        bad += 1
    for kind in ("special", "omen", "ritual", "rest"):
        for sid in sorted(REGISTRY[kind]):
            if a.ids and sid not in a.ids:
                continue
            if a.prefix and not sid.startswith(a.prefix):
                continue
            total += 1
            cls = REGISTRY[kind][sid]
            errors, warns, perf = check(cls)
            mark = "✗" if errors else "!" if warns else "✓"
            print(f"{mark} {kind:7s} {sid:24s} {cls.name:8s} {perf}")
            for e in errors:
                print("    错误：" + e)
            for w in warns:
                print("    提示：" + w)
            bad += bool(errors)
    print(f"共 {total} 个场景，{bad} 个有错误；法事 {len(REGISTRY['ritual'])}，歇 {len(REGISTRY['rest'])}，"
          f"起卦 {len(REGISTRY['omen'])}，特殊 {len(REGISTRY['special'])}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
