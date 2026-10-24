from wwb.app import run

from apps.dao.engine.runtime import gallery


def add_args(ap):
    ap.add_argument("--only", help="只看这个场景 id")


run(gallery, "dao 新画风样板", add_args, only="r.incense")
