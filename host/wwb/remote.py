"""在树莓派上运行程序：电脑上开发，运行时把代码同步过去，由树莓派经 UART 驱动设备。

    python -m wwb.remote apps.stopwatch          # 同步 host/wwb、apps/ 后在树莓派上运行
    python -m wwb.remote wwb.showcase --seconds 30
    python -m wwb.remote wwb info                # 命令行也一样
    python -m wwb.remote --sync                  # 只同步

输出实时传回本机；Ctrl+C 停止树莓派上的程序（程序照常发 RELEASE 交还设备）。
用 ssh 公钥登录，rsync 只传有改动的文件。树莓派那边只需要 conda 环境（pyserial、numpy、pillow），
不用安装 wwb：运行时 PYTHONPATH 指向同步过去的 host/。

环境变量：
  WWB_REMOTE         ssh 目标，默认 pi@raspberrypi.local
  WWB_REMOTE_DIR     树莓派上的目录，默认 wwb_timer（相对 home）
  WWB_REMOTE_PYTHON  树莓派上的 Python，默认 ~/miniforge3/envs/wwb/bin/python
  WWB_REMOTE_PORT    树莓派上的串口，默认 /dev/serial0
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 仓库根目录
TARGET = os.environ.get("WWB_REMOTE", "pi@raspberrypi.local")
DIR = os.environ.get("WWB_REMOTE_DIR", "wwb_timer")
PYTHON = os.environ.get("WWB_REMOTE_PYTHON", "~/miniforge3/envs/wwb/bin/python")
PORT = os.environ.get("WWB_REMOTE_PORT", "/dev/serial0")
SYNC = ["host/wwb", "apps"]  # 运行需要的全部代码


def sync():
    subprocess.run(["ssh", TARGET, f"mkdir -p {DIR}/host"], check=True)
    for path in SYNC:
        dest = f"{TARGET}:{DIR}/{Path(path).parent.as_posix()}/".replace("/./", "/")
        subprocess.run(["rsync", "-az", "--delete", "--exclude", "__pycache__", str(ROOT / path), dest], check=True)


def run(module: str, args: list[str]) -> int:
    cmd = (f"cd {DIR} && WWB_PORT={shlex.quote(PORT)} PYTHONPATH=host "
           f"exec {PYTHON} -u -m {shlex.quote(module)} {shlex.join(args)}")
    # -tt：分配终端，Ctrl+C 作为 SIGINT 送到树莓派上的程序；ssh 断开时程序收到 SIGHUP
    return subprocess.run(["ssh", "-tt", "-o", "LogLevel=QUIET", TARGET, cmd]).returncode


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    sync()
    if argv[0] == "--sync":
        print(f"已同步到 {TARGET}:{DIR}")
        return
    try:
        sys.exit(run(argv[0], argv[1:]))
    except KeyboardInterrupt:  # Ctrl+C 已经送到树莓派，这里等 ssh 自己结束即可
        pass


if __name__ == "__main__":
    main()
