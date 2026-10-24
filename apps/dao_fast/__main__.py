from wwb.app import run

from apps.dao.__main__ import add_args
from apps.dao.engine.runtime import live

run(live, "dao timer 快进", add_args, timescale=30.0)
