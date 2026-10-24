"""dao timer：python -m apps.dao [--complete-after 秒] [--timescale 倍数]"""
from wwb.app import run

from .engine.runtime import live


def add_args(ap):
    ap.add_argument("--complete-after", type=float, default=600.0, help="一场法事累计多少秒后停下算圆满")
    ap.add_argument("--timescale", type=float, default=1.0, help="法事进度加速倍数（看效果用，不影响芯片计时）")


if __name__ == "__main__":
    run(live, "dao timer", add_args)
