"""在树莓派上运行程序：电脑上开发，运行时把代码同步过去，由树莓派经 UART 驱动设备。

    python -m wwb.remote apps.stopwatch          # 同步 host/wwb、apps/ 后在树莓派上运行
    python -m wwb.remote wwb.showcase --seconds 30
    python -m wwb.remote wwb info                # 命令行也一样
    python -m wwb.remote --sync                  # 只同步
    python -m wwb.remote --deploy apps.dao       # 同步并设为常驻程序（开机自启，崩溃重启）
    python -m wwb.remote --deploy                # 同步并重启常驻程序（代码更新后）
    python -m wwb.remote --svc status            # 常驻服务：status / start / stop / restart / logs [-f] / enable / disable

输出实时传回本机；Ctrl+C 停止树莓派上的程序（程序照常发 RELEASE 交还设备）。
常驻程序在运行时，临时运行别的程序会先停掉常驻程序，结束后再启动它（串口只能一个程序用）。
用 ssh 公钥登录，复用同一条连接，rsync 只传有改动的文件。树莓派那边只需要 conda 环境（pyserial、numpy、pillow），
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
# 复用同一条 ssh 连接（保持 10 分钟）：树莓派上一次握手约 0.7s，同步加运行要连好几次
SSH = ["ssh", "-o", "ControlMaster=auto", "-o", "ControlPath=~/.ssh/cm-wwb-%r@%h:%p", "-o", "ControlPersist=10m"]


def sync():
    subprocess.run([*SSH, TARGET, f"mkdir -p {DIR}/host"], check=True)
    for path in SYNC:
        dest = f"{TARGET}:{DIR}/{Path(path).parent.as_posix()}/".replace("/./", "/")
        subprocess.run(["rsync", "-az", "--delete", "--exclude", "__pycache__", "-e", shlex.join(SSH), str(ROOT / path), dest],
                       check=True)


def run(module: str, args: list[str]) -> int:
    cmd = (f"cd {DIR} && WWB_PORT={shlex.quote(PORT)} PYTHONPATH=host "
           f"exec {PYTHON} -u -m {shlex.quote(module)} {shlex.join(args)}")
    # -tt：分配终端，Ctrl+C 作为 SIGINT 送到树莓派上的程序；ssh 断开时程序收到 SIGHUP
    return subprocess.run([*SSH, "-tt", "-o", "LogLevel=QUIET", TARGET, cmd]).returncode


def svc(args: list[str], tty: bool = False) -> int:
    """在树莓派上执行 python -m wwb.svc ..."""
    cmd = f"cd {DIR} && WWB_PORT={shlex.quote(PORT)} PYTHONPATH=host exec {PYTHON} -m wwb.svc {shlex.join(args)}"
    return subprocess.run([*SSH, *(["-tt", "-o", "LogLevel=QUIET"] if tty else []), TARGET, cmd]).returncode


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    if argv[0] == "--svc":
        sys.exit(svc(argv[1:], tty=argv[1:2] == ["logs"]))
    sync()
    if argv[0] == "--sync":
        print(f"已同步到 {TARGET}:{DIR}")
        return
    if argv[0] == "--deploy":
        sys.exit(svc(["use", *argv[1:]]) if len(argv) > 1 else svc(["restart"]))
    paused = svc(["active"]) == 0
    if paused:
        print("（常驻程序已暂停，结束后恢复）")
        svc(["stop"])
    try:
        code = run(argv[0], argv[1:])
    except KeyboardInterrupt:  # Ctrl+C 已经送到树莓派，这里等 ssh 自己结束即可
        code = 130
    finally:
        if paused:
            svc(["start"])
    sys.exit(code)


if __name__ == "__main__":
    main()
