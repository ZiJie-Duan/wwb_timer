"""把脱机程序编译成 WebAssembly，生成 web/js/native.js（单文件，内嵌 wasm）。

    conda run -n emsdk python native/build_web.py [程序目录，默认 native/timer]

需要 Emscripten（emcc）和 U8g2 源码（在 firmware/ 里 pio run 过一次就会下载）。
u8g2 的库文件编译一次后缓存在 native/build/；字体只取程序里用到的那些（u8g2_fonts.c 有 40MB）。
"""
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"
CLIB = ROOT / "firmware/.pio/libdeps/c3/U8g2/src/clib"
BUILD = NATIVE / "build"
OUT = ROOT / "web/js/native.js"
SKIP = {"u8g2_fonts.c", "u8g2_d_setup.c", "u8g2_d_memory.c"}  # 字体另取；setup 表引用全部显示驱动
CFLAGS = ["-O2", "-ffunction-sections", "-fdata-sections"]
EXPORTS = ["_wwb_begin", "_wwb_input", "_wwb_host_frame", "_wwb_release", "_wwb_tick", "_wwb_controlled"]


def run(cmd):
    r = subprocess.run(cmd)
    if r.returncode:
        sys.exit(f"失败：{' '.join(map(str, cmd[:3]))} …")


def compile_u8g2() -> list[Path]:
    objs = []
    jobs = []
    (BUILD / "u8g2").mkdir(parents=True, exist_ok=True)
    for src in sorted(CLIB.glob("*.c")):
        if src.name in SKIP or src.name.startswith("mui"):
            continue
        obj = BUILD / "u8g2" / (src.stem + ".o")
        objs.append(obj)
        if not obj.exists() or obj.stat().st_mtime < src.stat().st_mtime:
            jobs.append(["emcc", *CFLAGS, "-c", str(src), "-o", str(obj)])
    if jobs:
        print(f"编译 u8g2：{len(jobs)} 个文件")
        with ThreadPoolExecutor() as ex:
            list(ex.map(run, jobs))
    return objs


def extract_fonts(sources: list[Path]) -> Path:
    names = sorted({m for s in sources for m in re.findall(r"\bu8g2_font_\w+", s.read_text())})
    text = (CLIB / "u8g2_fonts.c").read_text(encoding="latin-1")
    out = ['#include "u8g2.h"\n']
    for name in names:
        m = re.search(r"const uint8_t %s\[(\d+)\][^=]*=\s*((?:\"(?:[^\"\\]|\\.)*\"\s*)+);" % name, text)
        if not m:
            sys.exit(f"u8g2 里没有字体 {name}")
        out.append(f"const uint8_t {name}[{m.group(1)}] = {m.group(2)};\n")
    path = BUILD / "fonts.c"
    path.write_text("".join(out), encoding="latin-1")
    print("字体：" + ", ".join(n[len("u8g2_font_"):] for n in names))
    return path


def main():
    if not shutil.which("emcc"):
        sys.exit("找不到 emcc：conda run -n emsdk python native/build_web.py")
    if not CLIB.exists():
        sys.exit("找不到 U8g2 源码：先在 firmware/ 里运行一次 pio run")
    app = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else NATIVE / "timer"
    sources = [*sorted(app.glob("*.cpp")), NATIVE / "wwb/wwb.cpp", NATIVE / "web/main.cpp"]
    objs = compile_u8g2()
    fonts = BUILD / "fonts.o"
    run(["emcc", *CFLAGS, f"-I{CLIB}", "-c", str(extract_fonts(sources)), "-o", str(fonts)])
    OUT.parent.mkdir(exist_ok=True)
    run([
        "emcc", "-O2", "-std=c++17", "-fno-exceptions", "-fno-rtti",
        f"-I{NATIVE}", f"-I{CLIB.parent}", f"-I{ROOT / 'firmware/src'}",
        *map(str, sources), str(fonts), *map(str, objs),
        "-sMODULARIZE=1", "-sEXPORT_NAME=createWwbNative", "-sSINGLE_FILE=1", "-sENVIRONMENT=web",
        "-sFILESYSTEM=0", f"-sEXPORTED_FUNCTIONS={','.join(EXPORTS)}", "-Wl,--gc-sections",
        "-o", str(OUT),
    ])
    OUT.write_text(f"// 由 native/build_web.py 从 {app.relative_to(ROOT)} 生成，不要手改\n" + OUT.read_text())
    print(f"→ {OUT.relative_to(ROOT)}（{OUT.stat().st_size // 1024} KiB）")


if __name__ == "__main__":
    main()
