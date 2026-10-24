"""常驻服务：让上位机（树莓派）开机就运行一个程序（如 dao timer），崩溃自动重启。

在树莓派上（systemd 用户服务 wwb.service）：

    python -m wwb.svc use apps.dao             # 设定常驻程序（可带参数），并启动
    python -m wwb.svc start | stop | restart
    python -m wwb.svc status                   # 运行状态、常驻程序、最近日志
    python -m wwb.svc logs [-f]                # 日志（-f 持续跟随）
    python -m wwb.svc enable | disable         # 开机自启 开 / 关
    python -m wwb.svc uninstall

安装后也可以直接用 wwbctl（~/.local/bin/wwbctl）代替 python -m wwb.svc。
电脑上：python -m wwb.remote --svc status（同样的子命令，通过 ssh 执行）。

开机自启需要用户服务在没登录时也运行：sudo loginctl enable-linger $USER（use 时会提示）。
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

UNIT = "wwb.service"
UNIT_DIR = Path.home() / ".config" / "systemd" / "user"
ROOT = Path(__file__).resolve().parents[2]  # 仓库（同步过来的）根目录
WRAPPER = Path.home() / ".local" / "bin" / "wwbctl"


def systemctl(*args, check=False) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], check=check)


def unit_text(module: str, args: list[str]) -> str:
    port = os.environ.get("WWB_PORT", "/dev/serial0")
    cmd = shlex.join([sys.executable, "-u", "-m", module, *args])
    return f"""[Unit]
Description=wwb 常驻程序 {module}
After=network.target

[Service]
WorkingDirectory={ROOT}
Environment=PYTHONPATH={ROOT / 'host'}
Environment=WWB_PORT={port}
ExecStart={cmd}
Restart=always
RestartSec=3
# 停止时发 SIGTERM，程序发 RELEASE 交还设备
KillSignal=SIGTERM
TimeoutStopSec=5

[Install]
WantedBy=default.target
"""


def current() -> str:
    p = UNIT_DIR / UNIT
    if not p.exists():
        return "（未设定）"
    for ln in p.read_text().splitlines():
        if ln.startswith("ExecStart="):
            parts = shlex.split(ln[len("ExecStart="):])
            return " ".join(parts[3:]) if len(parts) > 3 else ln
    return "?"


def linger_ok() -> bool:
    user = os.environ.get("USER", "")
    return Path(f"/var/lib/systemd/linger/{user}").exists()


def install_wrapper():
    WRAPPER.parent.mkdir(parents=True, exist_ok=True)
    WRAPPER.write_text(f"#!/bin/sh\nPYTHONPATH={ROOT / 'host'} exec {sys.executable} -m wwb.svc \"$@\"\n")
    WRAPPER.chmod(0o755)


def cmd_use(a):
    UNIT_DIR.mkdir(parents=True, exist_ok=True)
    (UNIT_DIR / UNIT).write_text(unit_text(a.module, a.args))
    install_wrapper()
    systemctl("daemon-reload", check=True)
    systemctl("enable", UNIT, check=True)
    systemctl("restart", UNIT, check=True)
    print(f"常驻程序：{a.module} {' '.join(a.args)}（已启动，开机自启）")
    if not linger_ok():
        print("提示：要在未登录时也开机运行，执行一次 sudo loginctl enable-linger $USER")


def cmd_status(a):
    print(f"常驻程序：{current()}")
    print(f"开机自启：{'是' if subprocess.run(['systemctl', '--user', 'is-enabled', '--quiet', UNIT]).returncode == 0 else '否'}"
          f"{'' if linger_ok() else '（未开启 linger，需登录后才运行）'}")
    systemctl("--no-pager", "--lines=0", "status", UNIT)
    subprocess.run(["journalctl", "--user-unit", UNIT, "--no-pager", "-n", "8", "-o", "short-iso"])


def cmd_logs(a):
    # 用户日志常常没有落盘；从系统日志按用户服务取（pi 在 adm 组，可读）
    args = ["journalctl", "--user-unit", UNIT, "--no-pager", "-n", str(a.lines), "-o", "short-iso"]
    if a.follow:
        args.append("-f")
    subprocess.run(args)


def cmd_simple(name):
    def f(a):
        r = systemctl(name, UNIT)
        if r.returncode == 0:
            print({"start": "已启动", "stop": "已停止", "restart": "已重启", "enable": "已开启开机自启",
                   "disable": "已关闭开机自启"}[name])
        sys.exit(r.returncode)
    return f


def cmd_active(a):
    """供 wwb.remote 用：服务在运行时退出码 0"""
    sys.exit(subprocess.run(["systemctl", "--user", "is-active", "--quiet", UNIT]).returncode)


def cmd_uninstall(a):
    systemctl("disable", "--now", UNIT)
    (UNIT_DIR / UNIT).unlink(missing_ok=True)
    systemctl("daemon-reload")
    print("已卸载常驻服务")


def main():
    ap = argparse.ArgumentParser(prog="wwbctl", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("use", help="设定常驻程序并启动")
    p.add_argument("module")
    p.add_argument("args", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_use)
    for name in ("start", "stop", "restart", "enable", "disable"):
        sub.add_parser(name).set_defaults(fn=cmd_simple(name))
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("logs")
    p.add_argument("-f", "--follow", action="store_true")
    p.add_argument("-n", "--lines", type=int, default=40)
    p.set_defaults(fn=cmd_logs)
    sub.add_parser("active").set_defaults(fn=cmd_active)
    sub.add_parser("uninstall").set_defaults(fn=cmd_uninstall)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
