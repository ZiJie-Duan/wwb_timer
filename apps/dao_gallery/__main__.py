from wwb.app import run

from apps.dao.engine.runtime import gallery


def add_args(ap):
    ap.add_argument("--only", help="只看这个场景 id")


run(gallery, "dao timer 画廊", add_args)
